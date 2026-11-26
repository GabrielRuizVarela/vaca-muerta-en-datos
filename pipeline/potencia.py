"""Potencia del eje: cuantos eventos harian falta para separar un eje de 93 grados de uno de 67,5 grados.

Se corre despues de pipeline.costo:  uv run python -m pipeline.potencia

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ninguna cifra de potencia; no se cambia despues de ver resultados).
Fuente: docs/proceso/investigacion-fase3.md, secciones 3.2 y 4 (regla de parada del eje).

Pregunta: el eje de mayor merma de la cuenca es 93 grados (IC 95% 70 a 122) y el SHmax publicado es 67,5 grados (25,5 grados de
diferencia). Con mas eventos del mismo tipo, cuando un IC 95% del eje excluiria el otro valor con potencia de 80%?

Muestra de partida: los eventos del eje de la cuenca, los mismos de pipeline.costo.tabla_anisotropia (EVENTOS_SQL, distancia de 0,3 a
menos de 1 km, efectos fijos de area, controles km y log de la edad, caida = control menos indice acotados a [0, 2]).

Simulacion (todo con semillas fijas derivadas de costo.SEMILLA):
  1. Ajustar el modelo real: caida = efectos fijos de area + km + log edad + a cos 2r + b sin 2r. Guardar los residuos de cada
     evento y la amplitud R = sqrt(a^2 + b^2) observada.
  2. Mundo con eje verdadero TH0 en {67,5, 93,0}: caida simulada = parte de controles y efectos de area del ajuste real +
     R cos(2 (rumbo - TH0)) + residuo. La amplitud R es la observada (escenario principal).
  3. Escalar la muestra por M veces los pads hijo: se sortean con reemplazo M * (pads reales) pads hijo; cada pad sorteado trae
     sus filas completas (rumbo, area, km, edad) y el vector de residuos de ese pad (los residuos de un pad se mueven juntos).
     Cada copia sorteada es un pad distinto para el remuestreo del IC (clave unica por sorteo).
  4. En cada corrida: eje y IC 95% de percentiles por pads hijo con costo.eje_con_intervalo (reps = REPS_IC, reps_perm = 0).
     La corrida "separa" si el IC excluye el otro valor (si TH0 = 93, excluye 67,5; si TH0 = 67,5, excluye 93). El IC es el arco
     axial desde ic_bajo hasta ic_alto pasando por el eje estimado.
  5. Potencia(M) = promedio de la fraccion de corridas que separan en los dos mundos. M en MULTIPLOS = (1, 1,5, 2, 2,5, 3, 4),
     N_CORRIDAS = 200 por (M, TH0), REPS_IC = 200.
  6. Sensibilidad (se informa, no entra en el veredicto): lo mismo con la amplitud R / 2, porque la amplitud ajustada es siempre
     positiva y la del maximo de un eje estimado tiene sesgo hacia arriba.
  7. Cuenta analitica de referencia: error estandar del eje = (ancho del IC real / 2) / 1,96; error estandar necesario para
     separar 25,5 grados con 80% de potencia a 95% = 25,5 / (1,96 + 0,84); n necesario = n real * (EE real / EE necesario)^2.
  8. Calendario: eventos por ano de la muestra de partida segun el ano de la fractura del hijo en 2025 y en 2026 (2026 llevado a
     ano completo con los meses que tiene el dato). Anos hasta M80 = (M80 - 1) * n real / (eventos por ano, media de 2025 y 2026
     llevado a ano completo).

M80 es el menor M de la grilla con potencia >= 0,80, con interpolacion lineal de la potencia entre puntos de la grilla; si ninguno
llega a 0,80 hasta M = 4, M80 es "mas de 4".

Veredicto (se publican todos los resultados, favorables o no):
  * "no separable": M80 > 2,0 (o mas de 4). Dispara la primera pata de la regla de parada del eje: el proyecto declara que la
    direccion no se separa del SHmax con este dato y deja de presentarla como hallazgo.
  * "alcanzable con 1,5 a 2 veces": 1,5 < M80 <= 2,0. No dispara la regla.
  * "alcanzable pronto": M80 <= 1,5. No dispara la regla.
  * Si la potencia a M = 1 es de 0,80 o mas, el eje ya se separaba (no se espera; se informa).

Que NO prueba:
  * Supone que los eventos nuevos se parecen a los actuales (mismas areas, misma amplitud, mismo ruido). Loma Campana aporta 694 de
    los 1.734 eventos; el desarrollo futuro puede cambiar el reparto.
  * No dice si el eje es real: dice si este tipo de dato podria separarlo del SHmax, aunque lo fuera.
  * Solo mira el eje de la cuenca, no los de las areas.
"""
from __future__ import annotations

import concurrent.futures
import math

import duckdb
import numpy as np

from pipeline import costo
from pipeline.ingest import DATA
from pipeline.placebo import _g, _pts

MULTIPLOS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
N_CORRIDAS = 200
REPS_IC = 200
EJES_VERDADEROS = (67.5, 93.0)
EJE_CUENCA = 93.0
SHMAX = 67.5
DIFERENCIA_EJES = 25.5

# Semillas: todo deriva de costo.SEMILLA. Para la corrida j del punto (mi, ti), con mi indice en MULTIPLOS y ti
# indice en EJES_VERDADEROS, el sorteo de pads usa SEMILLA + 1_000_000 * mi + 10_000 * ti + j y el bootstrap del IC
# usa esa misma semilla mas DESPLAZA_IC. Los dos escenarios comparten semillas (numeros aleatorios comunes) y el
# resultado no depende del orden de llegada de los trabajos en paralelo.
SEMILLA = costo.SEMILLA
DESPLAZA_IC = 500_000

COLS_POTENCIA = [("escenario", "varchar"), ("multiplo", "double"), ("eje_verdadero", "double"),
                 ("corridas", "integer"), ("separa", "integer"), ("potencia", "double")]
COLS_RESUMEN = [("escenario", "varchar"), ("n_real", "integer"), ("pads_real", "integer"), ("m80", "double"),
                ("m80_texto", "varchar"), ("n_requerido_analitico", "double"), ("eventos_por_anio", "double"),
                ("anios_hasta_m80", "double"), ("veredicto", "varchar")]


def muestra_eje(filas: list[dict]) -> dict:
    """La muestra del eje de la cuenca: los mismos eventos de costo.tabla_anisotropia, en arreglos."""
    km = costo._arr(filas, "km_min")
    sel = (km >= costo.KM_MIN_EJE) & (km < 1)
    f = [x for x, s in zip(filas, sel) if s]
    area = np.array([x["area"] for x in f])
    ev = {"km": costo._arr(f, "km_min"), "edad": costo._arr(f, "edad_meses")}
    idx = np.clip(costo._arr(f, "indice"), 0, 2)
    ctl = np.clip(costo._arr(f, "indice_control"), 0, 2)
    return {"caida": ctl - idx, "rumbo": costo._arr(f, "rumbo_eje"), "ctrl": costo._controles_eje(ev),
            "grupo": np.unique(area, return_inverse=True)[1], "clave": np.array([str(x["pad_hijo"]) for x in f]),
            "mes": [x["mes_frac"] for x in f]}


def ajuste_real(caida, ctrl, rumbo, grupo=None) -> dict:
    """Ajusta el modelo con eje y descompone cada caida en parte de controles y area, parte axial y residuo."""
    caida = np.asarray(caida, dtype=float)
    ctrl = np.asarray(ctrl, dtype=float)
    r = np.radians(np.asarray(rumbo, dtype=float))
    theta, R, beta = costo.ajustar_eje(caida, ctrl, rumbo, grupo)
    cos2, sin2 = np.cos(2 * r), np.sin(2 * r)
    axial = beta[-2] * cos2 + beta[-1] * sin2
    base = np.column_stack([ctrl, cos2, sin2]) if np.size(ctrl) else np.column_stack([cos2, sin2])
    if grupo is None:
        resid = caida - np.column_stack([np.ones(len(caida)), base]) @ beta
    else:
        grupo = np.asarray(grupo)
        n_g = int(grupo.max()) + 1
        cnt = np.maximum(np.bincount(grupo, minlength=n_g), 1)

        def cen(a):
            return a - (np.bincount(grupo, a, n_g) / cnt)[grupo]

        resid = cen(caida) - np.column_stack([cen(base[:, j]) for j in range(base.shape[1])]) @ beta
    return {"theta": theta, "amplitud": R, "beta": beta, "control": caida - axial - resid, "residuos": resid}


def simular(rng, muestra: dict, ajuste: dict, M: float, TH0: float, R: float) -> dict:
    """Sortea M veces los pads hijo con reemplazo y arma la caida del mundo con eje verdadero TH0.

    Cada pad sorteado trae sus filas completas (rumbo, grupo, controles, parte de controles y residuos) y recibe una
    clave unica, asi el bootstrap del IC lo trata como un pad distinto.
    """
    clave = np.asarray(muestra["clave"])
    pads = np.unique(clave)
    por_pad = [np.flatnonzero(clave == p) for p in pads]
    pick = rng.integers(0, len(pads), int(round(M * len(pads))))
    filas = np.concatenate([por_pad[i] for i in pick])
    rumbo = np.asarray(muestra["rumbo"], dtype=float)[filas]
    caida = (np.asarray(ajuste["control"], dtype=float)[filas]
             + R * np.cos(2 * (np.radians(rumbo) - math.radians(TH0)))
             + np.asarray(ajuste["residuos"], dtype=float)[filas])
    return {"caida": caida, "ctrl": np.asarray(muestra["ctrl"], dtype=float)[filas], "rumbo": rumbo,
            "clave": np.repeat(np.arange(len(pick)), [len(por_pad[i]) for i in pick]),
            "grupo": np.asarray(muestra["grupo"])[filas]}


def separa(res: dict, otro: float) -> bool:
    """True si el arco del IC (de ic_bajo a ic_alto pasando por el eje, modulo 180) no contiene el otro valor."""
    if res["ancho_ic"] >= 180:
        return False
    sb = float(costo._dif_axial(res["ic_bajo"], res["eje"]))
    sa = float(costo._dif_axial(res["ic_alto"], res["eje"]))
    so = float(costo._dif_axial(otro, res["eje"]))
    return not (min(sb, sa, 0.0) <= so <= max(sb, sa, 0.0))


def _otro(TH0: float) -> float:
    return SHMAX if abs(TH0 - EJE_CUENCA) < abs(TH0 - SHMAX) else EJE_CUENCA


def _una_corrida(muestra, ajuste, M, TH0, R, s_sim, s_ic, reps_ic) -> bool:
    sim = simular(np.random.default_rng(s_sim), muestra, ajuste, M, TH0, R)
    res = costo.eje_con_intervalo(sim["caida"], sim["ctrl"], sim["rumbo"], sim["clave"], grupo=sim["grupo"],
                                  reps=reps_ic, reps_perm=0, semilla=s_ic)
    return separa(res, _otro(TH0))


def potencia(muestra: dict, ajuste: dict, M: float, TH0: float, R: float, corridas: int = N_CORRIDAS,
             reps_ic: int = REPS_IC, semilla: int | None = None) -> float:
    """Fraccion de corridas que separan el eje estimado del otro valor, en el mundo con eje verdadero TH0."""
    if semilla is None:
        base = SEMILLA + 1_000_000 * MULTIPLOS.index(float(M)) + 10_000 * EJES_VERDADEROS.index(float(TH0))
    else:
        base = int(semilla)
    ok = sum(_una_corrida(muestra, ajuste, M, TH0, R, base + j, base + DESPLAZA_IC + j, reps_ic)
             for j in range(corridas))
    return ok / corridas


def _punto(job: tuple) -> tuple:
    """Una celda (M, TH0) de la grilla, para el pozo de procesos. Devuelve (mi, ti, separa, corridas)."""
    muestra, ajuste, mi, ti, M, TH0, R, corridas, reps_ic = job
    base = SEMILLA + 1_000_000 * mi + 10_000 * ti
    ok = sum(_una_corrida(muestra, ajuste, M, TH0, R, base + j, base + DESPLAZA_IC + j, reps_ic)
             for j in range(corridas))
    return mi, ti, ok, corridas


def m80(potencias: list[tuple]) -> tuple[float | None, str]:
    """Menor M de la grilla con potencia >= 0,80, con interpolacion lineal; (None, "mas de 4") si ninguno llega."""
    for k, (M, p) in enumerate(potencias):
        if p >= 0.80:
            if k == 0:
                return float(M), f"{_g(float(M), 2)} veces"
            M0, p0 = potencias[k - 1]
            v = M0 + (0.80 - p0) * (M - M0) / (p - p0)
            return float(v), f"{_g(float(v), 2)} veces"
    return None, "mas de 4"


def veredicto(m: float | None) -> str:
    if m is None or m > 2.0:
        return "no separable"
    if m > 1.5:
        return "alcanzable con 1,5 a 2 veces"
    return "alcanzable pronto"


def n_analitico(n_real: int, ancho_ic: float, diferencia: float = DIFERENCIA_EJES) -> float:
    """Cuenta analitica de referencia: eventos necesarios para separar la diferencia con 80% de potencia."""
    ee_real = (ancho_ic / 2) / 1.96
    ee_nec = diferencia / (1.96 + 0.84)
    return n_real * (ee_real / ee_nec) ** 2


def calendario(meses: list) -> dict:
    """Ritmo de eventos por ano: media de 2025 y 2026, con 2026 llevado a ano completo por sus meses con dato."""
    anios = [m.year if hasattr(m, "year") else int(str(m)[:4]) for m in meses]
    mes_n = [m.month if hasattr(m, "month") else int(str(m)[5:7]) for m in meses]
    n25 = sum(1 for a in anios if a == 2025)
    m25 = len({m for a, m in zip(anios, mes_n) if a == 2025})
    n26 = sum(1 for a in anios if a == 2026)
    m26 = len({m for a, m in zip(anios, mes_n) if a == 2026})
    n26_anual = n26 * 12 / m26 if m26 else 0
    return {"n2025": n25, "meses2025": m25, "n2026": n26, "meses2026": m26, "n2026_anual": n26_anual,
            "eventos_por_anio": (n25 + n26_anual) / 2}


def _ic_real(con) -> dict | None:
    try:
        fila = con.execute("select eje_grados, ic_bajo, ic_alto, ancho_ic from mart_anisotropia_area "
                           "where area = 'Cuenca'").fetchone()
    except duckdb.CatalogException:  # pipeline.costo todavia no corrio: no hay intervalo real que comparar
        return None
    if fila is None:
        return None
    return {"eje": fila[0], "ic_bajo": fila[1], "ic_alto": fila[2], "ancho_ic": fila[3]}


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    muestra = muestra_eje(costo._filas(con, costo.EVENTOS_SQL))
    n_real = len(muestra["caida"])
    pads_real = len(np.unique(muestra["clave"]))
    ajuste = ajuste_real(muestra["caida"], muestra["ctrl"], muestra["rumbo"], muestra["grupo"])
    R = float(ajuste["amplitud"])
    ic = _ic_real(con)
    if ic is None:  # sin el mart de costo, el IC real se calcula igual que alla
        r = costo.eje_con_intervalo(muestra["caida"], muestra["ctrl"], muestra["rumbo"], muestra["clave"],
                                    grupo=muestra["grupo"])
        ic = {"eje": r["eje"], "ic_bajo": r["ic_bajo"], "ic_alto": r["ic_alto"], "ancho_ic": r["ancho_ic"]}
    escenarios = [("principal", R), ("amplitud_media", R / 2)]
    base_muestra = {k: muestra[k] for k in ("rumbo", "ctrl", "grupo", "clave")}
    base_ajuste = {k: ajuste[k] for k in ("control", "residuos")}
    jobs = [(base_muestra, base_ajuste, mi, ti, M, TH0, Rsc, N_CORRIDAS, REPS_IC)
            for _esc, Rsc in escenarios for mi, M in enumerate(MULTIPLOS)
            for ti, TH0 in enumerate(EJES_VERDADEROS)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
        puntos = list(ex.map(_punto, jobs))
    meta = [(esc, M, TH0) for esc, _Rsc in escenarios for M in MULTIPLOS for TH0 in EJES_VERDADEROS]
    filas_eje = [(esc, float(M), float(TH0), int(n), int(ok), ok / n)
                 for (esc, M, TH0), (_mi, _ti, ok, n) in zip(meta, puntos)]
    curvas = {esc: [(M, sum(r[5] for r in filas_eje if r[0] == esc and r[1] == M) / 2) for M in MULTIPLOS]
              for esc, _Rsc in escenarios}
    m80s = {esc: m80(curva) for esc, curva in curvas.items()}
    ver = veredicto(m80s["principal"][0])
    n_req = n_analitico(n_real, ic["ancho_ic"])
    epa = calendario(muestra["mes"])["eventos_por_anio"]
    filas_res = [(esc, n_real, pads_real, m80s[esc][0], m80s[esc][1], n_req, epa,
                  (m80s[esc][0] - 1) * n_real / epa if m80s[esc][0] is not None else None, ver)
                 for esc, _Rsc in escenarios]
    costo._escribir(con, "mart_potencia_eje", COLS_POTENCIA, filas_eje)
    costo._escribir(con, "mart_potencia_resumen", COLS_RESUMEN, filas_res)
    print(f"[potencia] muestra n={n_real} pads={pads_real} eje={ic['eje']:.1f} "
          f"IC {ic['ic_bajo']:.1f} a {ic['ic_alto']:.1f} R={R:.4f}")
    for esc, _Rsc in escenarios:
        for M in MULTIPLOS:
            ps = [r[5] for r in filas_eje if r[0] == esc and r[1] == M]
            print(f"[potencia] {esc:<14} M={M:3.1f} potencia={sum(ps) / 2:.3f} "
                  f"(TH0 67,5: {ps[0]:.3f}; TH0 93: {ps[1]:.3f})")
    for esc, _Rsc in escenarios:
        print(f"[potencia] M80 {esc}: {m80s[esc][1]}")
    a = m80s["principal"][0]
    anos = f"{(a - 1) * n_real / epa:.1f} anos" if a is not None else "sin fecha (M80 supera 4)"
    print(f"[potencia] veredicto: {ver}; analitico n={n_req:.0f} (M={n_req / n_real:.2f}); "
          f"{epa:.0f} eventos por ano; {anos}")
    if curvas["principal"][0][1] >= 0.80:
        print("[potencia] aviso: con M = 1 la potencia ya llega a 0,80, el eje ya se separaba")
    con.close()


def pagina_potencia(con) -> str:
    """Pagina de wiki/hallazgos/potencia.md (se devuelve, no se escribe a disco)."""
    res = {r[0]: r for r in con.execute(
        "select escenario, n_real, pads_real, m80, m80_texto, n_requerido_analitico, eventos_por_anio, "
        "anios_hasta_m80, veredicto from mart_potencia_resumen").fetchall()}
    det = con.execute("select escenario, multiplo, potencia from mart_potencia_eje").fetchall()
    prom = {}
    for esc, M, p in det:
        prom.setdefault((esc, M), []).append(p)
    cal = calendario(muestra_eje(costo._filas(con, costo.EVENTOS_SQL))["mes"])
    eje, bajo, alto = con.execute("select eje_grados, ic_bajo, ic_alto from mart_anisotropia_area "
                                  "where area = 'Cuenca'").fetchone()
    _esc, n_real, pads_real, m80v, m80t, n_req, epa, anos, ver = res["principal"]
    m80_frase = f"{m80t} la muestra actual" if m80v is not None else "mas de 4 veces la muestra actual"
    L = ["# Potencia del eje", "",
         "## Resumen", "",
         f"El eje de mayor merma de la cuenca es {_g(eje, 1)} grados (IC 95% de {_g(bajo, 1)} a {_g(alto, 1)}), "
         f"con {_g(n_real)} eventos en {_g(pads_real)} pads hijo, y el SHmax publicado es {_g(SHMAX, 1)} grados. "
         f"Para separar un valor del otro con 80% de potencia harian falta {m80_frase} "
         f"(escenario principal). Veredicto: {ver}.",
         "", "## Potencia por multiplo", "",
         "Fraccion de corridas que separan, en %, promediada sobre los dos mundos (eje verdadero 67,5 o 93,0):",
         "",
         "| Veces la muestra (M) | Escenario principal | Amplitud media |",
         "| ---: | ---: | ---: |"]
    for M in MULTIPLOS:
        p1 = sum(prom[("principal", M)]) / len(prom[("principal", M)])
        p2 = sum(prom[("amplitud_media", M)]) / len(prom[("amplitud_media", M)])
        L.append(f"| {_g(M, 1)} | {_pts(p1)} | {_pts(p2)} |")
    L += ["", "## Cuenta analitica y calendario", "",
          f"La cuenta analitica de referencia pide {_g(n_req)} eventos (M = {_g(n_req / n_real, 2)}).",
          f"El ritmo actual es de {_g(epa)} eventos por ano: media de {_g(cal['n2025'])} eventos en 2025 "
          f"({_g(cal['meses2025'])} meses) y {_g(cal['n2026'])} en 2026 ({_g(cal['meses2026'])} meses, "
          f"llevado a ano completo: {_g(cal['n2026_anual'])})."]
    if anos is None:
        L.append("Como M80 supera 4 veces la muestra, a este ritmo no hay fecha.")
    else:
        L.append(f"A ese ritmo, juntar M80 veces la muestra llevaria {_g(anos, 1)} anos.")
    L += ["", "## Regla fijada antes de correr", "",
          "La regla se fijo el 2026-11-16, antes de calcular ninguna cifra de potencia, y no se cambia con los "
          "resultados:",
          "",
          "* Se parte de los eventos del eje de la cuenca (distancia de 0,3 a menos de 1 km, efectos fijos de area, "
          "controles de km y log de la edad, caida acotada a [0, 2]).",
          "* Se ajusta el modelo con el eje y se guardan la parte de controles y area, los residuos y la amplitud R.",
          "* Se simulan dos mundos, con eje verdadero 67,5 o 93,0: controles mas R cos(2 (rumbo menos TH0)) mas "
          "residuo.",
          "* Cada corrida sortea con reemplazo M veces los pads hijo; cada copia trae sus filas y residuos juntos y "
          "vale como un pad nuevo.",
          "* En cada corrida se estima eje e IC 95% por pads (200 remuestreos, sin permutacion); separa si el IC "
          "excluye el otro valor.",
          "* La potencia es el promedio sobre los dos mundos; grilla M en (1, 1,5, 2, 2,5, 3, 4), 200 corridas por "
          "punto.",
          "* La sensibilidad con R/2 solo se informa; el veredicto usa el escenario principal.",
          "* M80 interpola linealmente el primer cruce de 80%; si no cruza hasta M = 4, es mas de 4.",
          "* Veredicto: M80 mayor a 2 (o mas de 4) declara la direccion no separable del SHmax; hasta 1,5 es pronto, "
          "en el medio lleva de 1,5 a 2 veces.",
          "* Todas las semillas derivan de 20261115 por (multiplo, mundo, corrida); se publican todos los "
          "resultados.",
          "", "## Que no prueba", "",
          "* Supone que los eventos nuevos se parecen a los actuales (mismas areas, misma amplitud, mismo ruido); "
          "Loma Campana aporta 694 de los 1.734 eventos y el desarrollo futuro puede cambiar el reparto.",
          "* No dice si el eje es real: dice si este tipo de dato podria separarlo del SHmax, aunque lo fuera.",
          "* Solo mira el eje de la cuenca, no los de las areas.",
          ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
