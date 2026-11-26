"""Cota de Rambachan y Roth (2023), magnitudes relativas, sobre una serie de eventos (porcion F).

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porcion F de docs/plan-siguiente-nivel.md). Este commit trae la regla, las
constantes, el conjunto identificado, el intervalo y el veredicto. No se calculo ninguna cifra con esta cota antes de
fijarla. Si algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian las cifras publicadas de D1 (pretendencia de -2,5, -3,6 y -6,3 en los meses -3 a -1,
M* simplificado de 0,62) y de D2 (13,8 con 447 tratados, promedio de los meses 0 y 1 de 9,5 en D3).

Reemplaza, en el texto, al M* simplificado de pipeline.causal (m_estrella, que suma |b(-1)| a los dos lados y compara con
el IC alto). El veredicto de D1 ya fijado no cambia: sigue usando m_estrella y queda como registro.

Marco. Una serie de eventos estima beta(e) contra la base (meses -6 a -4 de g, que vale cero). Sin anticipacion,
beta(e) = tau(e) + delta(e), con delta el sesgo por tendencias no paralelas; en los meses previos tau = 0 y
delta(-k) = beta(-k). Los previos son PREVIOS (e = -3, -2, -1).

Magnitudes relativas, Delta^RM(Mbar). Saltos previos: s(-3) = b(-3) - 0 (contra la base, como en m_estrella),
s(-2) = b(-2) - b(-3), s(-1) = b(-1) - b(-2); m = max |s|. Cada salto posterior, delta(0) - delta(-1), delta(1) - delta(0),
..., vale en valor absoluto a lo sumo Mbar m.

Conjunto identificado (exacto, cerrado): para theta = media de tau(e) sobre un conjunto de meses E (e >= 0; un mes solo es
E = {e}), delta(e) = b(-1) + la suma de e + 1 saltos, asi que
    theta en [l(beta) - b(-1) - c(E) Mbar m, l(beta) - b(-1) + c(E) Mbar m],   c(E) = media de (e + 1) sobre E,
con l(beta) la media de beta(e) sobre E. Para ATT(1): c = 2. Para la media de los meses 0 y 1: c = 1,5.

Inferencia (fijada; no es la prueba condicional e hibrida de Andrews, Roth y Pakes que usa el paquete de Rambachan y Roth):
intervalo de union por bootstrap. Con los sorteos de bloques del diseno (los mismos para beta y para los previos), cada
sorteo r da lo_r y hi_r del conjunto identificado; el intervalo es [percentil 2,5 de lo_r, percentil 97,5 de hi_r]. Cubre el
conjunto identificado, y por eso el parametro, con al menos 95% de probabilidad asintotica (cada extremo falla a lo sumo
2,5%): es conservador. El max de m no es suave cuando dos saltos previos empatan; se declara como limite. No se agrega
ninguna dependencia nueva.

Que se publica, para cada diseno y estimando (D1 ATT(1); D2 tau_W(1) y la media de tau_W(0) y tau_W(1) con las celdas de D2,
H = H_CORTO, dW por mes como en D5 pero con la base y las celdas de D2; E ATT(1) cuando exista su mart):
  * la grilla GRILLA_MBAR con el conjunto identificado y el intervalo de cada Mbar;
  * el Mbar de quiebre: el menor Mbar en [0, MBAR_MAX] con intervalo que contiene cero, por biseccion (el intervalo crece
    con Mbar); 0 si ya lo contiene con Mbar = 0; "mayor que MBAR_MAX" si no lo contiene en MBAR_MAX. Con dos decimales.
  * El estimando de maximo de D2 (dW = max(W(g), W(g+1)) - base) no es lineal en tau y no lleva esta cota; el texto lo dice.

Veredicto (`veredicto_rr`), en este orden:
  * "sin dato": falta algun previo.
  * "resiste Mbar = 1": quiebre de M_MIN o mas (saltos posteriores tan grandes como el mayor previo no alcanzan para cero).
  * "resiste solo con Mbar menor que 1": quiebre mayor que cero y menor que M_MIN.
  * "no resiste ni con Mbar = 0": quiebre cero (el efecto menos la pretendencia del mes -1 no se distingue de cero).

Lo que no dice: supone que los meses previos no tienen efecto (sin anticipacion); con anticipacion, restar b(-1) achica un
efecto del mismo signo que la pretendencia y la cota es conservadora en ese caso, no en el contrario.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.causal import M_MIN, PERCENTILES_IC
from pipeline.costo import _escribir

# ---- regla fijada (no cambiar despues de ver cifras) ----
PREVIOS = (-3, -2, -1)
GRILLA_MBAR = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
MBAR_MAX = 2.0
TOL_BISECCION = 1e-4

V_RR_SIN_DATO = "sin dato"
V_RR_RESISTE = "resiste Mbar = 1"
V_RR_PARCIAL = "resiste solo con Mbar menor que 1"
V_RR_NO = "no resiste ni con Mbar = 0"


def m_previo(b3: np.ndarray | float, b2: np.ndarray | float, b1: np.ndarray | float) -> np.ndarray:
    """Mayor salto previo en valor absoluto, contra la base y entre meses previos consecutivos."""
    b3, b2, b1 = (np.asarray(x, float) for x in (b3, b2, b1))
    return np.maximum.reduce([np.abs(b3), np.abs(b2 - b3), np.abs(b1 - b2)])


def c_meses(meses: tuple[int, ...]) -> float:
    """c(E) = media de (e + 1) sobre los meses posteriores E."""
    if not meses or min(meses) < 0:
        raise ValueError("los meses del estimando son posteriores (e >= 0)")
    return float(np.mean([e + 1 for e in meses]))


def conjunto(l_beta, b3, b2, b1, mbar: float, meses: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Extremos del conjunto identificado de theta (por sorteo si los argumentos son vectores)."""
    centro = np.asarray(l_beta, float) - np.asarray(b1, float)
    media = c_meses(meses) * mbar * m_previo(b3, b2, b1)
    return centro - media, centro + media


def intervalo(l_beta_r, b3_r, b2_r, b1_r, mbar: float, meses: tuple[int, ...]) -> tuple[float, float]:
    """Intervalo de union: percentil bajo de lo_r y percentil alto de hi_r sobre los sorteos."""
    lo, hi = conjunto(l_beta_r, b3_r, b2_r, b1_r, mbar, meses)
    return float(np.percentile(lo, PERCENTILES_IC[0])), float(np.percentile(hi, PERCENTILES_IC[1]))


def _contiene_cero(iv: tuple[float, float]) -> bool:
    return iv[0] <= 0 <= iv[1]


def quiebre(l_beta_r, b3_r, b2_r, b1_r, meses: tuple[int, ...]) -> float:
    """Menor Mbar en [0, MBAR_MAX] con intervalo que contiene cero; inf si no lo contiene en MBAR_MAX."""
    def iv(mbar: float) -> tuple[float, float]:
        return intervalo(l_beta_r, b3_r, b2_r, b1_r, mbar, meses)
    if _contiene_cero(iv(0.0)):
        return 0.0
    if not _contiene_cero(iv(MBAR_MAX)):
        return float("inf")
    a, b = 0.0, MBAR_MAX
    while b - a > TOL_BISECCION:
        c = (a + b) / 2
        if _contiene_cero(iv(c)):
            b = c
        else:
            a = c
    return b


def veredicto_rr(hay_previos: bool, mbar_quiebre: float) -> str:
    if not hay_previos:
        return V_RR_SIN_DATO
    if mbar_quiebre >= M_MIN:
        return V_RR_RESISTE
    if mbar_quiebre > 0:
        return V_RR_PARCIAL
    return V_RR_NO


# ---- porcion F: conexion con D1 y D2, mart y pagina (el calculo de arriba no cambia) ----
COLS_COTA_RR = [
    ("diseno", "varchar"), ("estimando", "varchar"), ("fila", "varchar"), ("mbar", "double"),
    ("conj_bajo", "double"), ("conj_alto", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
    ("quiebre", "double"), ("veredicto", "varchar"), ("l_beta", "double"), ("b3", "double"), ("b2", "double"),
    ("b1", "double"), ("m", "double"), ("n_tratados", "integer"), ("sorteos", "integer"), ("motivo", "varchar"),
]
MOTIVO_MAYOR = "mayor que MBAR_MAX"
PAGINA = Path("wiki/hallazgos/cota_rr.md")
COMMIT_REGLA = "857d434"
TOL_IGUALDAD_D1 = 1e-9


def armar_estimando(diseno: str, nombre: str, meses: tuple[int, ...], l_pt: float, l_vals: np.ndarray,
                    previos_pt: tuple[float, float, float], previos_vals: np.ndarray, n_tratados: int) -> dict:
    """Filas de mart (grilla y quiebre) y datos de un estimando.

    `l_vals` es (R,), `previos_vals` es (R, 3) con b(-3), b(-2), b(-1). Se descarta el sorteo donde falte cualquiera de
    los cuatro valores; el punto de cada valor sale de la estimacion con la muestra completa."""
    l_vals = np.asarray(l_vals, float)
    previos_vals = np.asarray(previos_vals, float).reshape(len(l_vals), 3)
    ok = ~(np.isnan(l_vals) | np.isnan(previos_vals).any(axis=1))
    descartados = int((~ok).sum())
    hay_previos = bool(np.all(np.isfinite(previos_pt))) and bool(np.isfinite(l_pt))
    b3, b2, b1 = previos_pt
    base = (diseno, nombre)
    comunes = (float(l_pt), float(b3), float(b2), float(b1))
    if not hay_previos or not ok.any():
        v = veredicto_rr(False, float("nan"))
        fila = (*base, "quiebre", None, None, None, None, None, None, v, *comunes, None, n_tratados, int(ok.sum()),
                "falta algun previo o ningun sorteo completo")
        return {"diseno": diseno, "estimando": nombre, "filas": [fila], "descartados": descartados, "quiebre": None,
                "veredicto": v, "m": None, "sorteos": int(ok.sum())}
    m = float(m_previo(b3, b2, b1))
    lv, p3, p2, p1 = l_vals[ok], previos_vals[ok, 0], previos_vals[ok, 1], previos_vals[ok, 2]
    sorteos = int(ok.sum())
    filas = []
    for mbar in GRILLA_MBAR:
        lo, hi = conjunto(l_pt, b3, b2, b1, mbar, meses)
        ic = intervalo(lv, p3, p2, p1, mbar, meses)
        filas.append((*base, "grilla", float(mbar), float(lo), float(hi), ic[0], ic[1], None, None,
                      *comunes, m, n_tratados, sorteos, None))
    q = quiebre(lv, p3, p2, p1, meses)
    v = veredicto_rr(True, q)
    inf = not np.isfinite(q)
    filas.append((*base, "quiebre", None, None, None, None, None, None if inf else float(q), v, *comunes, m,
                  n_tratados, sorteos, MOTIVO_MAYOR if inf else None))
    return {"diseno": diseno, "estimando": nombre, "filas": filas, "descartados": descartados, "quiebre": q,
            "veredicto": v, "m": m, "sorteos": sorteos}


def media_meses(puntos: list[float], sorteos: list[np.ndarray]) -> tuple[float, np.ndarray]:
    """Media de varios meses: el punto es la media de los puntos; cada sorteo, la media de sus valores (nan si falta uno)."""
    return float(np.mean(puntos)), np.mean(np.column_stack(sorteos), axis=1)


def _estimandos_d1(r: dict) -> list[dict]:
    from pipeline.causal import E_SERIE
    ix = {e: E_SERIE.index(e) for e in E_SERIE}
    prev = tuple(float(r["est"][ix[e]]) for e in PREVIOS)
    pv = np.column_stack([r["vals"][:, ix[e]] for e in PREVIOS])
    return [armar_estimando("D1", "ATT(1)", (1,), float(r["est"][ix[1]]), r["vals"][:, ix[1]], prev, pv,
                            int(r["n_tratados"][ix[1]]))]


def _estimandos_d2(D: dict, cel_pri: list[dict], W: np.ndarray) -> list[dict]:
    from pipeline import causal_profundo
    from pipeline.causal import MIN_MESES_W_BASE, _panel_promedio
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    por_mes = {}
    for e in (*PREVIOS, 0, 1):
        vt, vc = causal_profundo.valores_dw_mes(D, cel_pri, e, base_w)
        por_mes[e] = causal_profundo.estimar_valores(D, cel_pri, W, vt, vc)
    prev = tuple(float(por_mes[e]["est"]) for e in PREVIOS)
    pv = np.column_stack([np.asarray(por_mes[e]["vals"], float) for e in PREVIOS])
    out = []
    for nombre, meses in (("tau_W(1)", (1,)), ("media tau_W(0,1)", (0, 1))):
        l_pt, l_vals = media_meses([float(por_mes[e]["est"]) for e in meses],
                                   [np.asarray(por_mes[e]["vals"], float) for e in meses])
        n = int(min(por_mes[e]["n_tratados"] for e in meses))
        out.append(armar_estimando("D2", nombre, meses, l_pt, l_vals, prev, pv, n))
    return out


def _fmt(x, dec: int = 2) -> str:
    from pipeline.placebo import _g
    return _g(float(x), dec)


def pagina_cota_rr(filas: list[tuple], e_apilado: tuple | None = None) -> str:
    """Pagina de wiki a partir de las filas de `mart_cota_rr`. `e_apilado` = (quiebre, veredicto de la cota, veredicto de E)
    leido de `mart_apilado` cuando existe: la regla pide la cota de E ATT(1) "cuando exista su mart"."""
    cols = [c[0] for c in COLS_COTA_RR]
    reg = [dict(zip(cols, f)) for f in filas]
    orden: list[tuple[str, str]] = []
    for x in reg:
        if (x["diseno"], x["estimando"]) not in orden:
            orden.append((x["diseno"], x["estimando"]))
    L = ["# Cota de Rambachan y Roth: cuánto sesgo hace falta para borrar el efecto", "",
         "Página generada por `pipeline/cota_rr.py`, regla fijada en el commit " + COMMIT_REGLA + " antes de calcular.", "",
         "La cota pregunta qué tan grande tendría que ser la violación de tendencias paralelas después del tratamiento, "
         "medida contra el mayor salto entre meses que ya se ve antes del tratamiento, para que el efecto deje de "
         "distinguirse de cero. Mbar es esa razón: con Mbar = 1 el sesgo puede saltar de un mes al siguiente tanto como "
         "el mayor salto previo; con Mbar = 0 no puede saltar. El conjunto identificado es el rango del efecto "
         "compatible con esa violación; el intervalo agrega la incertidumbre del bootstrap por bloques de 5 km "
         "(unión de los percentiles 2,5 y 97,5 de los extremos, conservador). El Mbar de quiebre es el menor Mbar "
         "con intervalo que contiene cero. Unidades: puntos de producción en D1 y puntos porcentuales de corte de agua en D2.", ""]
    for d, nom in orden:
        g = [x for x in reg if x["diseno"] == d and x["estimando"] == nom and x["fila"] == "grilla"]
        q = next(x for x in reg if x["diseno"] == d and x["estimando"] == nom and x["fila"] == "quiebre")
        L += [f"## {d}, {nom}", ""]
        if not g:
            L += [f"Sin dato: {q['motivo']}. Veredicto: **{q['veredicto']}**.", ""]
            continue
        L += [f"Efecto estimado {_fmt(q['l_beta'], 1)}; previos b(-3) = {_fmt(q['b3'], 1)}, b(-2) = {_fmt(q['b2'], 1)}, "
              f"b(-1) = {_fmt(q['b1'], 1)}; mayor salto previo m = {_fmt(q['m'], 1)}; {q['n_tratados']} tratados, "
              f"{q['sorteos']} sorteos completos.", "",
              "| Mbar | Conjunto identificado | Intervalo |", "|---|---|---|"]
        for x in g:
            L.append(f"| {_fmt(x['mbar'], 2)} | {_fmt(x['conj_bajo'], 1)} a {_fmt(x['conj_alto'], 1)} | "
                     f"{_fmt(x['ic_bajo'], 1)} a {_fmt(x['ic_alto'], 1)} |")
        qtxt = f"{MOTIVO_MAYOR.replace('MBAR_MAX', _fmt(MBAR_MAX, 2))}" if q["quiebre"] is None else _fmt(q["quiebre"], 2)
        L += ["", f"Mbar de quiebre: {qtxt}. Veredicto: **{q['veredicto']}**.", ""]
    if e_apilado is not None:
        qe, ve, vd = e_apilado
        qtxt = f"{MOTIVO_MAYOR.replace('MBAR_MAX', _fmt(MBAR_MAX, 2))}" if qe is None else _fmt(qe, 2)
        L += ["## E, ATT(1)", "",
              "La cota del estimador apilado la calcula `pipeline.stacked` con esta misma regla (c = 2) y queda en "
              "`mart_apilado` (fila `E_detalle`, `cota_quiebre`).", "",
              f"Mbar de quiebre: {qtxt}. Veredicto: **{ve}**. El veredicto de E es «{vd}», así que la cota no cambia lo que se "
              "publica del petróleo.", ""]
    L += ["## Lo que queda como estaba", "",
          "El veredicto de D1 ya fijado, que usa el M* simplificado de `pipeline/causal.py`, no cambia con esta cota y "
          "queda como registro. Esta cota lo reemplaza en el texto, no en lo que se fijó.", "",
          "El estimando de máximo de D2 (W(g) o W(g+1), el mayor, menos la base) no es lineal en el efecto y no lleva esta "
          "cota.", "",
          "## Lo que no dice", "",
          "Supone que los meses previos no tienen efecto (sin anticipación). Con anticipación, restar b(-1) achica un "
          "efecto del mismo signo que la pretendencia y la cota es conservadora en ese caso, no en el contrario. El "
          "intervalo no es la prueba condicional e híbrida del paquete de Rambachan y Roth: es la unión de bootstrap fijada "
          "en la regla, y el máximo de los saltos previos no es suave cuando dos empatan.", ""]
    return "\n".join(L)


def _imprimir(e: dict) -> None:
    print(f"\n== {e['diseno']} {e['estimando']}  (sorteos usados {e['sorteos']}, descartados por nan {e['descartados']})")
    for f in e["filas"]:
        d = dict(zip((c[0] for c in COLS_COTA_RR), f))
        if d["fila"] == "grilla":
            print(f"  Mbar {d['mbar']:.2f}: conjunto [{d['conj_bajo']:.3f}, {d['conj_alto']:.3f}]  "
                  f"IC [{d['ic_bajo']:.3f}, {d['ic_alto']:.3f}]")
        else:
            print(f"  punto {d['l_beta']:.3f}  previos {d['b3']:.3f} {d['b2']:.3f} {d['b1']:.3f}  m {d['m']}")
            print(f"  quiebre {d['quiebre']}  ({d['motivo']})  veredicto: {d['veredicto']}")


def main(path=None) -> None:
    """Calcula la cota para D1 y D2 con los sorteos de `pipeline.causal.main`, escribe `mart_cota_rr` y la pagina."""
    import duckdb

    from pipeline import causal as c
    path = path or c.DATA / "warehouse.duckdb"
    con = duckdb.connect(str(path), read_only=True)
    D = c.cargar(con)
    coh = c.cohortes(D)
    rng = np.random.default_rng(c.SEMILLA_CAUSAL)
    # mismo orden de construccion y de sorteos que pipeline.causal.main (lineas 1250-1267)
    cel_pri = c.celdas(D, coh, c.H_CORTO, False)
    cel_s1 = c.celdas(D, coh, c.H_CORTO, True)
    trat_ff, g_ff = c._cohorte_falsa_fecha(D, coh)
    cel_ff = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = c._cohorte_falsa_distancia(D, coh, c.H_CORTO)
    cel_fd = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = c._cohorte_nunca_tratados(D, coh)
    cel_nt = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    cel_d1b = c.celdas_d1b(D, coh)
    wells = []
    for grupo in [cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b]:
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = c._pesos_bloques(D, wells, c.REPS, rng)

    r1 = c.bootstrap(D, cel_pri, c.E_SERIE, W)
    ests = _estimandos_d1(r1) + _estimandos_d2(D, cel_pri, W)

    # D1: el punto y el IC de ATT(1) son los del mart de causal (misma semilla, mismos sorteos)
    i1 = c.E_SERIE.index(1)
    ref = con.execute("select valor, ic_bajo, ic_alto from mart_causal_veredicto where diseno = 'D1'").fetchone()
    mio = (float(r1["est"][i1]), float(r1["ic_bajo"][i1]), float(r1["ic_alto"][i1]))
    dif = max(abs(a - b) for a, b in zip(mio, ref))
    print(f"igualdad D1 ATT(1) con mart_causal_veredicto: punto {mio[0]!r} vs {ref[0]!r}, IC {mio[1]!r} a {mio[2]!r} "
          f"vs {ref[1]!r} a {ref[2]!r}; diferencia maxima {dif:.3e}")
    if not dif < TOL_IGUALDAD_D1:
        raise SystemExit(f"D1 ATT(1) no coincide con mart_causal_veredicto (dif {dif:.3e}): se detiene")
    con.close()

    filas = [f for e in ests for f in e["filas"]]
    for e in ests:
        _imprimir(e)
    con = duckdb.connect(str(path))
    _escribir(con, "mart_cota_rr", COLS_COTA_RR, filas)
    e_apilado = None
    if con.execute("select count(*) from information_schema.tables where table_name = 'mart_apilado'").fetchone()[0]:
        q = con.execute("select valor, veredicto from mart_apilado where diseno = 'E_detalle' and resultado = 'cota_quiebre'").fetchone()
        v = con.execute("select veredicto from mart_apilado where diseno = 'E' and resultado = 'ATT(1)'").fetchone()
        if q and v:
            e_apilado = (q[0], q[1], v[0])
    txt = pagina_cota_rr(con.execute("select * from mart_cota_rr order by rowid").fetchall(), e_apilado)
    con.close()
    PAGINA.parent.mkdir(parents=True, exist_ok=True)
    PAGINA.write_text(txt, encoding="utf-8")
    print(f"\nescrito mart_cota_rr ({len(filas)} filas) y {PAGINA}")


if __name__ == "__main__":
    main()
