"""Replicacion por operador del corte de agua (D2) contra sus propios controles, con placebos de dos colas (ronda 4, S5).

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla, y el plan que
nombra (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto de la regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-27, ronda 4 de docs/plan-siguiente-nivel.md). Este commit trae la regla, las constantes y
las firmas. Antes de fijarla no se calculo el ATT_W de ningun operador con solo sus propios controles, ni ningun placebo de D2
por operador, ni el extremo bajo del IC del placebo de fechas de ningun operador del petroleo. Si algo resulta ambiguo al
calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocen D2 (ATT_W de la muestra completa, sus placebos y su veredicto) y los cortes de D6
(pipeline.causal_profundo): con todos los controles, los tratados de YPF solos dan 17,5 puntos porcentuales (IC 11,6 a 24,5,
255 tratados) y sin YPF la suba da 7,1 (IC -0,6 a 18,1, 129 tratados); los otros operadores con el minimo son Pluspetrol,
Tecpetrol y Vista, y sacar cualquiera de ellos deja la suba sobre cero. Tambien se conocen las siete lecturas del petroleo de
pipeline.replicacion_operadores (regla de19052): 5 de 7, con la brecha puntual y el extremo alto del IC de cada placebo de fechas.

Por que. Fable, en la pasada sobre la copia publica 2c2ae47 (S5 7,5), noto que la replicacion por operador mide solo el
petroleo, que el agua, el unico resultado con lectura causal, depende de YPF (D6) y que el placebo de la replicacion del
petroleo es de una cola: los placebos de Vista (+7,5) y Pluspetrol (+12,4) no se leen.

A. Agua: D2 operador por operador, con sus propios controles.
Datos y marco: los de pipeline.causal.main, sin cambios. D = causal.cargar(con); coh = causal.cohortes(D); las celdas cel_pri,
cel_ff y cel_fd y los sorteos W se arman en el mismo orden y con la misma semilla que en causal.main (el mismo camino que
cota_rr_condicional._entradas_reales), asi que W es el mismo de D2.
  * Operadores medidos: los de D6, es decir los que tienen MIN_TRATADOS_OPERADOR o mas tratados en cel_pri, con o sin dW
    (la cuenta de causal_profundo._cortes_operador, con el operador de cada pozo en D["operador"]). Es un conjunto fijo,
    elegido por conteo y no por resultado.
  * Celdas propias de X: cada celda de cel_pri con solo los tratados de X y solo los controles de X (celdas_propias). Se
    descarta la celda que se queda sin tratados o con menos de causal.MIN_CONTROLES_CELDA controles, como en
    causal._celdas_sin_operador. Lo mismo con cel_ff y cel_fd para los placebos de X.
  * ATT_W de X y su IC 95%: como causal.diseno_d2, con causal._valores_agua(D, celdas, 0), causal._preparar y
    causal._bootstrap_prep(D, prep, W) sobre las celdas propias de X.
  * Placebos de X, los tres de la regla de D2, sobre las celdas propias: previo (_valores_agua con k = -2 sobre las celdas
    propias de cel_pri), fecha falsa (k = 0 sobre las de cel_ff) y distancia falsa (k = 0 sobre las de cel_fd). Un placebo
    rompe con causal.rompe(est, ic_bajo, ic_alto, causal.UMBRAL_ROTURA_AGUA): su IC excluye el cero, de cualquier lado, y su
    valor absoluto llega al umbral. Es de dos colas. El placebo de cierre no se corre por operador: usa otros eventos (meses
    cerrados) y la regla de D2 lo lee contra el ATT_W de la muestra completa.
  * Lectura de X (lectura_operador_agua):
      - "no se pudo medir: ..." si el ATT_W de X tiene menos de MIN_TRATADOS_MEDIR tratados con dW, o si el ATT_W, su IC o
        alguno de los tres placebos no tiene valor; cuenta en n con su motivo;
      - "no se replica: rompe el placebo <nombre>" si rompe alguno de los tres (se nombran todos los que rompen);
      - "se replica" si no rompe ninguno y el IC 95% del ATT_W de X queda entero sobre cero (ic_bajo > 0);
      - "no se replica: el IC 95% no queda entero sobre cero" en otro caso.
    Que el ic_bajo pase tambien UMBRAL_AGUA_PP (el umbral del veredicto de D2) se publica como dato, sin lectura.
  * Familia: "Se replica en k de n operadores: <operador> (<lectura>); ...", con n todos los operadores medidos (los que no se
    pudieron medir incluidos) y k los que se replican, en orden de mas a menos tratados en cel_pri (empate: por nombre). No hay
    promedio, peso ni estimacion conjunta. Se publica cualquiera sea k, tambien k = 0.

B. Petroleo: lectura de dos colas del placebo de fechas, despues de ver las cifras.
Las siete lecturas de pipeline.replicacion_operadores se fijaron en de19052 con un placebo de una cola, y sus cifras se
conocen. Esta lectura se fija despues de verlas, asi que es post hoc: no cambia el 5 de 7 de la regla de de19052, que sigue
siendo la cifra que se cita, y se publica al lado con esa etiqueta.
  * Por operador del petroleo, el mismo placebo de fechas de replicacion_operadores (mismos eventos, misma semilla
    SEMILLA_FECHAS, mismo placebo.brecha_ic), leyendo tambien su ic_bajo.
  * Dos colas: el placebo rompe si su IC 95% excluye el cero de cualquier lado. Un operador "se replica con dos colas" si se
    replica por la regla de de19052 y su placebo de fechas no rompe con dos colas.
  * Familia post hoc: "Con el placebo de dos colas, se replica en k2 de n operadores: ...", con la misma n.

Que se publica:
  * mart_replicacion_operadores_agua: una fila por operador del agua (COLS_REP_AGUA) y una fila de familia (COLS_FAM_AGUA);
  * mart_replicacion_operadores_dos_colas: una fila por operador del petroleo (COLS_DOS_COLAS) y una fila de familia;
  * la pagina wiki/hallazgos/replicacion_operadores_agua.md, con la tabla del agua, la frase, la seccion post hoc del
    petroleo con su etiqueta y lo que no prueba;
  * en un PR de texto aparte, la frase del agua por operador en la pregunta de validez externa del README y del paper, con sus
    claims. La portada la agrega solo si k es 0 o k es n.

Validacion fijada antes de leer cifras reales (tests/test_replicacion_operadores_agua.py, sin warehouse):
  * celdas_propias, sobre celdas sinteticas con dos operadores, deja solo los tratados y los controles de X y descarta la
    celda con menos de causal.MIN_CONTROLES_CELDA controles;
  * lectura_operador_agua: un ATT_W con IC sobre cero y placebos limpios da "se replica"; un placebo previo de +3 con IC
    entero sobre cero (rompe por arriba) da "no se replica" aunque el ATT_W pase, y uno de -3 con IC entero bajo cero tambien;
    menos de MIN_TRATADOS_MEDIR tratados da "no se pudo medir";
  * la familia cuenta a los que no se pudieron medir en n, como pipeline.familia;
  * la lectura de dos colas del petroleo: un placebo con IC 2 a 9 rompe con dos colas y no con una.

Que no prueba: dentro de un operador cambian el area y el ano, asi que el ATT_W por operador no separa al operador de su area.
k de n es un recuento, no una prueba conjunta: cada operador se lee a 95% por separado, sin ajuste por comparaciones multiples.
Con solo sus propios controles, un operador chico pierde celdas, y su IC es mas ancho que el del corte de D6.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np

from pipeline import causal, causal_profundo, placebo, replicacion_operadores as ro
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g, _pts

# ---- regla fijada (no cambiar despues de ver cifras) ----
MIN_TRATADOS_OPERADOR = causal.MIN_TRATADOS_OPERADOR   # 50: los operadores de D6
MIN_TRATADOS_MEDIR = 50        # tratados con dW en las celdas propias de X para leerlo
UMBRAL_ROTURA_AGUA = causal.UMBRAL_ROTURA_AGUA         # 2 puntos porcentuales, de dos colas (causal.rompe)
UMBRAL_AGUA_PP = causal.UMBRAL_AGUA_PP                 # el umbral del veredicto de D2; aca es dato
PLACEBOS_AGUA = ("previo", "fecha_falsa", "distancia_falsa")
K_PREVIO = -2
LECTURAS_AGUA = ("se replica", "no se replica", "no se pudo medir")

COLS_REP_AGUA = [("operador", "varchar"), ("n_tratados_d2", "integer"), ("n_tratados", "integer"),
                 ("n_controles", "integer"), ("att_w", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
                 ("pasa_umbral_d2", "boolean"),
                 ("previo", "double"), ("previo_ic_bajo", "double"), ("previo_ic_alto", "double"),
                 ("fecha_falsa", "double"), ("fecha_falsa_ic_bajo", "double"), ("fecha_falsa_ic_alto", "double"),
                 ("distancia_falsa", "double"), ("distancia_falsa_ic_bajo", "double"),
                 ("distancia_falsa_ic_alto", "double"), ("rotos", "varchar"), ("se_replica", "boolean"),
                 ("lectura", "varchar")]
COLS_FAM_AGUA = [("k", "integer"), ("n", "integer"), ("frase", "varchar")]
COLS_DOS_COLAS = [("operador", "varchar"), ("placebo_brecha", "double"), ("placebo_ic_bajo", "double"),
                  ("placebo_ic_alto", "double"), ("rompe_dos_colas", "boolean"), ("se_replica_de19052", "boolean"),
                  ("se_replica_dos_colas", "boolean"), ("lectura", "varchar")]
PAGINA = Path("wiki/hallazgos/replicacion_operadores_agua.md")
COMMIT_REGLA = "b1479a8"     # el commit que fijo la regla; lo fija el commit que corre con datos reales


def _nan(x) -> bool:
    return x is None or bool(np.isnan(x))


def _nombre(placebo_: str) -> str:
    """El nombre de un placebo como se escribe en la pagina."""
    return placebo_.replace("_", " ")


def celdas_propias(D: dict, celdas_: list[dict], op: str) -> list[dict]:
    """Celdas con solo los tratados y solo los controles del operador `op`."""
    out = []
    for ce in celdas_:
        mt = D["operador"][ce["tratados"]] == op
        mc = D["operador"][ce["controles"]] == op
        t, c = ce["tratados"][mt], ce["controles"][mc]
        if not len(t) or len(c) < causal.MIN_CONTROLES_CELDA:
            continue
        out.append({**ce, "tratados": t, "controles": c, "base_t": ce["base_t"][mt], "base_c": ce["base_c"][mc]})
    return out


def lectura_operador_agua(n_tratados: int, att: float, ic_bajo: float, ic_alto: float,
                          placebos: dict[str, tuple[float, float, float]]) -> tuple[bool | None, str, list[str]]:
    """(se_replica o None si no se pudo medir, lectura, placebos que rompen) segun la regla A."""
    if n_tratados < MIN_TRATADOS_MEDIR:
        pozos = "tratado" if n_tratados == 1 else "tratados"
        motivo = f"{_g(n_tratados)} {pozos} con dW en las celdas propias, menos de {MIN_TRATADOS_MEDIR}"
        return None, f"no se pudo medir: {motivo}", []
    for nombre, x in (("el ATT_W", att), ("su IC", ic_bajo), ("su IC", ic_alto)):
        if _nan(x):
            return None, f"no se pudo medir: {nombre} no tiene valor", []
    for nombre in PLACEBOS_AGUA:
        if any(_nan(x) for x in placebos[nombre]):
            return None, f"no se pudo medir: el placebo {_nombre(nombre)} no tiene valor", []
    rotos = [_nombre(nombre) for nombre in PLACEBOS_AGUA if causal.rompe(*placebos[nombre], UMBRAL_ROTURA_AGUA)]
    if rotos:
        return False, "no se replica: rompe el placebo " + ", ".join(rotos), rotos
    if ic_bajo > 0:
        return True, "se replica", []
    return False, "no se replica: el IC 95% no queda entero sobre cero", []


def lectura_familia_agua(resultados: list[tuple[str, bool | None, str]]) -> dict:
    """k, n y la frase de la familia del agua."""
    k = sum(1 for _, r, _ in resultados if r is True)
    n = len(resultados)
    lista = "; ".join(f"{op} ({lec})" for op, _, lec in resultados)
    frase = f"Se replica en {k} de {n} operadores" + (": " + lista if n else "") + "."
    return {"k": k, "n": n, "frase": frase}


def rompe_dos_colas(ic_bajo: float, ic_alto: float) -> bool | None:
    """El placebo del petroleo rompe con dos colas si su IC 95% excluye el cero."""
    if _nan(ic_bajo) or _nan(ic_alto):
        return None
    return bool(ic_bajo > 0 or ic_alto < 0)


def _entradas(con) -> tuple[dict, list[dict], list[dict], list[dict], np.ndarray]:
    """D, cel_pri, cel_ff, cel_fd y W, con el orden de construccion y la semilla de causal.main (los mismos sorteos de D2)."""
    D = causal.cargar(con)
    coh = causal.cohortes(D)
    rng = np.random.default_rng(causal.SEMILLA_CAUSAL)
    cel_pri = causal.celdas(D, coh, causal.H_CORTO, False)
    cel_s1 = causal.celdas(D, coh, causal.H_CORTO, True)
    trat_ff, g_ff = causal._cohorte_falsa_fecha(D, coh)
    cel_ff = causal.celdas(D, coh, causal.H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = causal._cohorte_falsa_distancia(D, coh, causal.H_CORTO)
    cel_fd = causal.celdas(D, coh, causal.H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = causal._cohorte_nunca_tratados(D, coh)
    cel_nt = causal.celdas(D, coh, causal.H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    cel_d1b = causal.celdas_d1b(D, coh)
    wells = []
    for grupo in [cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b]:
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = causal._pesos_bloques(D, wells, causal.REPS, rng)
    return D, cel_pri, cel_ff, cel_fd, W


def _estimar(D: dict, cel: list[dict], k: int, W: np.ndarray) -> dict | None:
    """El estimador de D2 (dW en el mes k) sobre `cel`; None si no hay celdas."""
    if not cel:
        return None
    vt, vc = causal._valores_agua(D, cel, k)
    return causal._bootstrap_prep(D, causal._preparar(cel, vt, vc), W)


def _terna(r: dict | None) -> tuple[float, float, float]:
    nan = float("nan")
    return (float(r["est"]), float(r["ic_bajo"]), float(r["ic_alto"])) if r else (nan, nan, nan)


def calcular_agua(con) -> tuple[list[tuple], tuple]:
    """Filas de COLS_REP_AGUA y la fila de COLS_FAM_AGUA (parte A)."""
    D, cel_pri, cel_ff, cel_fd, W = _entradas(con)
    trat = causal_profundo._tratados(cel_pri)
    ops, cuentas = np.unique(D["operador"][trat].astype(str), return_counts=True) if len(trat) else ([], [])
    medidos = [(str(op), int(c)) for op, c in zip(ops, cuentas) if c >= MIN_TRATADOS_OPERADOR]
    medidos.sort(key=lambda t: (-t[1], t[0]))
    filas, resultados = [], []
    for op, n_d2 in medidos:
        c_pri, c_ff, c_fd = (celdas_propias(D, c, op) for c in (cel_pri, cel_ff, cel_fd))
        r = _estimar(D, c_pri, 0, W)
        pl = {"previo": _terna(_estimar(D, c_pri, K_PREVIO, W)), "fecha_falsa": _terna(_estimar(D, c_ff, 0, W)),
              "distancia_falsa": _terna(_estimar(D, c_fd, 0, W))}
        att, bajo, alto = _terna(r)
        n_t, n_c = (r["n_tratados"], r["n_controles"]) if r else (0, 0)
        se_replica, lec, rotos = lectura_operador_agua(n_t, att, bajo, alto, pl)
        pasa = None if _nan(bajo) else bool(bajo > UMBRAL_AGUA_PP)
        filas.append((op, n_d2, n_t, n_c, att, bajo, alto, pasa, *pl["previo"], *pl["fecha_falsa"], *pl["distancia_falsa"],
                      ", ".join(rotos), se_replica, lec))
        resultados.append((op, se_replica, lec))
    fam = lectura_familia_agua(resultados)
    return filas, (fam["k"], fam["n"], fam["frase"])


def calcular_dos_colas(con) -> tuple[list[tuple], tuple]:
    """Filas de COLS_DOS_COLAS y la fila de COLS_FAM_AGUA (parte B, post hoc): el placebo de fechas del petroleo con dos colas."""
    filas19, _ = ro.calcular(con)
    d = placebo.cargar(con)
    mf = placebo.marco(d, d["hijo_mes"] + ro.DESPLAZAMIENTO_PLACEBO, solo_reales=True)
    ops = np.array([r[0] or "" for r in con.execute("select operador from int_pozo_ubicacion order by pozo_id").fetchall()])
    ops_mf = ops[mf["padre"]]
    filas, resultados = [], []
    for f in filas19:
        op, brecha_ro, ic_alto_ro, rep19, lec19 = f[0], f[7], f[8], f[11], f[12]
        mkf = ops_mf == op
        pl = placebo.brecha_ic(mf["idx"][1][mkf], mf["banda"][mkf], mf["clave"][mkf], placebo.REPS_BOOT, ro.SEMILLA_FECHAS)
        same = lambda a, b: (_nan(a) and _nan(b)) or a == b
        assert same(pl["brecha"], brecha_ro) and same(pl["ic_alto"], ic_alto_ro), f"el placebo de {op} no coincide"
        rompe = rompe_dos_colas(pl["ic_bajo"], pl["ic_alto"])
        if rep19 is None:
            rep2, lec = None, lec19
        elif rep19 is False:
            rep2, lec = False, lec19
        elif rompe is None:
            rep2, lec = None, "no se pudo medir: el IC del placebo de fechas no tiene valor"
        elif rompe:
            rep2, lec = False, "no se replica con dos colas: el placebo de fechas da brecha de un lado"
        else:
            rep2, lec = True, "se replica con dos colas"
        filas.append((op, pl["brecha"], pl["ic_bajo"], pl["ic_alto"], rompe, rep19, rep2, lec))
        resultados.append((op, rep2, lec))
    k, n = sum(1 for _, r, _ in resultados if r is True), len(resultados)
    frase = (f"Con el placebo de dos colas, se replica en {k} de {n} operadores"
             + (": " + "; ".join(f"{op} ({lec})" for op, _, lec in resultados) if n else "") + ".")
    return filas, (k, n, frase)


def _si_no(x: bool | None) -> str:
    return "n/d" if x is None else ("sí" if x else "no")


def pagina_replicacion_operadores_agua(filas: list[tuple], fam: tuple, filas2: list[tuple], fam2: tuple) -> str:
    L = ["# Replicación del corte de agua por operador", "",
         "Se mide el corte de agua de D2 (ATT_W, en puntos porcentuales) operador por operador, con solo los tratados "
         "y solo los controles de ese operador en cada celda, y con sus propios placebos. Es la pregunta de "
         "[replicacion_operadores.md](replicacion_operadores.md) aplicada al agua, el único resultado con lectura causal, "
         "que en D6 ([causal_profundo.md](causal_profundo.md)) depende de YPF.", "",
         "## Cómo se lee", "",
         f"La regla se fijó en el commit `{COMMIT_REGLA}` (2026-11-27), antes de calcular ninguna de estas cifras; el "
         "texto y las constantes están en `pipeline/replicacion_operadores_agua.py` y en `docs/reglas-fijadas.md`. "
         f"Se miden los operadores con {causal.MIN_TRATADOS_OPERADOR} o más tratados en las celdas de D2. Un operador se "
         "replica si ninguno de sus tres placebos (previo, fecha falsa y distancia falsa, sobre sus celdas propias) rompe "
         "y el IC 95% de su ATT_W queda entero sobre cero. Un placebo rompe si su IC excluye el cero, de cualquier lado, "
         f"y su valor absoluto llega a {_g(UMBRAL_ROTURA_AGUA)} puntos (dos colas). No se pudo medir con menos de "
         f"{MIN_TRATADOS_MEDIR} tratados con dW o con algún valor faltante. Si el extremo bajo del IC pasa además "
         f"{_g(UMBRAL_AGUA_PP)} puntos (el umbral del veredicto de D2) se publica como dato, sin lectura.", "",
         f"**{fam[2]}**", "",
         "| Operador | Tratados en D2, con o sin dW | Tratados / controles propios | ATT_W (puntos) | IC 95% | Pasa el umbral de D2 "
         "| Placebo previo (IC) | Placebo fecha falsa (IC) | Placebo distancia falsa (IC) | Lectura |",
         "| --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- |"]
    if any(r[18] is None for r in filas):
        L[-2:-2] = ["Donde no se pudo medir, la tabla no muestra el ATT_W, su IC ni los placebos: salen de muy pocos pozos. "
                    "Quedan en `mart_replicacion_operadores_agua`.", ""]
    for (op, n_d2, n_t, n_c, att, lo, hi, pasa, p, plo, phi, f, flo, fhi, d, dlo, dhi, _rotos, _rep, lec) in filas:
        if _rep is None:   # no se pudo medir: las cifras de pocos pozos quedan en el mart, no en la tabla
            L.append(f"| {op} | {_g(n_d2)} | {_g(n_t)} / {_g(n_c)} | n/d | n/d | n/d | n/d | n/d | n/d | {lec} |")
            continue
        L.append(f"| {op} | {_g(n_d2)} | {_g(n_t)} / {_g(n_c)} | {_g(att, 1)} | {_g(lo, 1)} a {_g(hi, 1)} | {_si_no(pasa)} "
                 f"| {_g(p, 1)} ({_g(plo, 1)} a {_g(phi, 1)}) | {_g(f, 1)} ({_g(flo, 1)} a {_g(fhi, 1)}) "
                 f"| {_g(d, 1)} ({_g(dlo, 1)} a {_g(dhi, 1)}) | {lec} |")
    k19, n19 = sum(1 for r in filas2 if r[5] is True), len(filas2)   # la cuenta de de19052, de la corrida
    L += ["", "## Petróleo: el placebo de fechas leído con dos colas (post hoc)", "",
          "Esta lectura se fijó después de ver las cifras: el placebo de fechas de "
          "[replicacion_operadores.md](replicacion_operadores.md) se leía de una cola, y sus extremos ya se conocían. "
          f"No cambia el {_g(k19)} de {_g(n19)} de la regla de `de19052`, que sigue siendo la cifra que se cita; se publica al lado, con "
          "esta etiqueta. Con dos colas el placebo rompe si su IC 95% excluye el cero de cualquier lado.", "",
          f"**{fam2[2]}**", "",
          "| Operador | Placebo de fechas (puntos) | IC 95% | Rompe con dos colas | Se replica (de19052) "
          "| Se replica con dos colas | Lectura |",
          "| --- | ---: | --- | --- | --- | --- | --- |"]
    for op, b, lo, hi, rompe, r19, r2, lec in filas2:
        L.append(f"| {op} | {_pts(b)} | {_pts(lo)} a {_pts(hi)} | {_si_no(rompe)} | {_si_no(r19)} | {_si_no(r2)} | {lec} |")
    L += ["", "## Qué no prueba", "",
          "- Dentro de un operador cambian el área y el año, así que el ATT_W por operador no separa al operador de su área.",
          "- k de n es un recuento, no una prueba conjunta: cada operador se lee a 95% por separado, "
          "sin ajuste por comparaciones múltiples.",
          "- Con solo sus propios controles, un operador chico pierde celdas, y su IC es más ancho que el del corte de D6.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    """Escribe los cuatro marts y la pagina."""
    con = duckdb.connect(str(path))
    filas, fam = calcular_agua(con)
    filas2, fam2 = calcular_dos_colas(con)
    _escribir(con, "mart_replicacion_operadores_agua", COLS_REP_AGUA, filas)
    _escribir(con, "mart_replicacion_operadores_agua_familia", COLS_FAM_AGUA, [fam])
    _escribir(con, "mart_replicacion_operadores_dos_colas", COLS_DOS_COLAS, filas2)
    _escribir(con, "mart_replicacion_operadores_dos_colas_familia", COLS_FAM_AGUA, [fam2])
    PAGINA.parent.mkdir(parents=True, exist_ok=True)
    PAGINA.write_text(pagina_replicacion_operadores_agua(filas, fam, filas2, fam2), encoding="utf-8")
    for r in filas:
        print(f"[replicacion_operadores_agua] {r[0]:<28} d2={r[1]} propios={r[2]}/{r[3]} "
              f"att_w={r[4]:+.1f} IC {r[5]:+.1f} a {r[6]:+.1f} previo={r[8]:+.1f} ff={r[11]:+.1f} fd={r[14]:+.1f} -> {r[19]}")
    print(f"[replicacion_operadores_agua] {fam[2]}")
    for r in filas2:
        print(f"[dos_colas] {r[0]:<28} placebo={100 * r[1]:+.1f} IC {100 * r[2]:+.1f} a {100 * r[3]:+.1f} -> {r[7]}")
    print(f"[dos_colas] {fam2[2]}")
    print(f"escrito 4 marts ({len(filas)} operadores del agua, {len(filas2)} del petroleo) y {PAGINA}")


if __name__ == "__main__":
    main()
