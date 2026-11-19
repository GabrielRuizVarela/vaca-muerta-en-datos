"""Machine check of the numbers quoted in README.md, docs/verificacion.md and the wiki finding pages.

Each Claim names a file, a regex with one number group (Spanish format: thousands with dots, decimals
with comma, or a number word such as "cinco") and a function that computes the real value from the
warehouse, the committed reports or the code. The check passes when |document - computed| <= tolerance
(half a unit of the last digit the document prints, or a stated rounding for "unos ...").

  uv run python -m pipeline.claims          # exit 1 on any FAIL
  uv run python -m pipeline.claims --rapido # skip the claims that run a subprocess

Estados: PASS, FAIL (number differs, or the sentence no longer matches the pattern), SKIP (the claim
needs the warehouse and data/warehouse.duckdb is absent).
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb

from pipeline.cuencas import COLORADO, WYOMING

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
WAREHOUSE_CO = ROOT / "data" / "colorado" / "warehouse.duckdb"
EPS = 1e-9

_PALABRAS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
             "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
             "quince": 15, "dieciséis": 16, "dieciseis": 16, "veinte": 20}


@dataclass(frozen=True)
class Claim:
    id: str
    fichero: str                      # relative to the repo root
    patron: str                       # regex with exactly one number group, searched with re.S
    valor_fn: Callable                # valor_fn(con) -> float; con is None when requiere_wh is False and no warehouse
    tolerancia: float = 0.5
    formato: str = "{:,.0f}"          # how the computed value is shown in the report
    requiere_wh: bool = True          # SKIP when the warehouse file is absent
    lento: bool = False               # runs a subprocess; skipped with --rapido
    almacen: str = "vm"               # "vm" (data/warehouse.duckdb), the id of a basin (data/<id>/warehouse.duckdb, pipeline/cuencas.py) or "familia" (all of them)
    opcional: bool = False            # SKIP instead of FAIL when the sentence is not in the text (it appears only in one reading of the data)


@dataclass
class Resultado:
    claim: Claim
    estado: str                       # PASS | FAIL | SKIP
    documento: float | None = None
    calculado: float | None = None
    detalle: str = ""


def parse_numero(s: str) -> float:
    """Spanish number to float: '1.234,5' -> 1234.5, '10,7' -> 10.7, '93' -> 93, '-960' -> -960, 'cinco' -> 5."""
    t = s.strip().lower()
    if t in _PALABRAS:
        return float(_PALABRAS[t])
    return float(t.replace(".", "").replace(",", "."))


def extraer(texto: str, patron: str) -> float | None:
    """The number captured by the first match of patron in texto, or None when the sentence is gone."""
    m = re.search(patron, texto, re.S)
    if not m:
        return None
    return parse_numero(m.group(1))


def fmt(c: Claim, v: float) -> str:
    return c.formato.format(v).replace(",", "_").replace(".", ",").replace("_", ".")


def evaluar(c: Claim, texto: str, con, lentos: bool = True, con_co=None, con_alm: dict | None = None) -> Resultado:
    if c.lento and not lentos:
        return Resultado(c, "SKIP", detalle="lento (--rapido)")
    if c.almacen == "familia":
        from pipeline.familia import FAMILIA
        cons = {i: (con_co if i == "colorado" else (con_alm or {}).get(i)) for i, _ in FAMILIA}
        con = cons if all(v is not None for v in cons.values()) else None
    elif c.almacen != "vm":
        con = (con_alm or {}).get(c.almacen, con_co if c.almacen == "colorado" else None)
    if c.requiere_wh and con is None:
        return Resultado(c, "SKIP", detalle=f"sin data/{c.almacen}/warehouse.duckdb" if c.almacen != "vm" else "sin data/warehouse.duckdb")
    doc = extraer(texto, c.patron)
    if doc is None and c.opcional:
        return Resultado(c, "SKIP", detalle="la frase no esta en este texto (depende de la lectura de los datos)")
    if doc is None:
        return Resultado(c, "FAIL", detalle="la frase ya no coincide con el patron (cambio el texto o el numero dejo de estar)")
    calc = float(c.valor_fn(con))
    ok = abs(doc - calc) <= c.tolerancia + EPS
    return Resultado(c, "PASS" if ok else "FAIL", doc, calc, "" if ok else f"documento {fmt(c, doc)} contra calculado {fmt(c, calc)}")


def verificar(claims: list[Claim] | None = None, raiz: Path | None = None, wh: Path | None = None, lentos: bool = True,
              wh_co: Path | None = None, wh_alm: dict[str, Path] | None = None) -> list[Resultado]:
    claims = CLAIMS if claims is None else claims
    raiz = ROOT if raiz is None else raiz
    wh = (raiz / "data" / "warehouse.duckdb") if wh is None else wh
    wh_co = (raiz / "data" / "colorado" / "warehouse.duckdb") if wh_co is None else wh_co
    con = duckdb.connect(str(wh), read_only=True) if wh.exists() else None
    con_co = duckdb.connect(str(wh_co), read_only=True) if wh_co.exists() else None
    con_alm: dict = {}
    pedidos = {c.almacen for c in claims}
    if "familia" in pedidos:
        from pipeline.familia import FAMILIA
        pedidos |= {i for i, _ in FAMILIA}
    for a in sorted(pedidos - {"vm", "colorado", "familia"}):
        p = (wh_alm or {}).get(a) or (raiz / "data" / a / "warehouse.duckdb")
        if p.exists():
            con_alm[a] = duckdb.connect(str(p), read_only=True)
    try:
        textos: dict[str, str | None] = {}
        out = []
        for c in claims:
            if c.fichero not in textos:
                p = raiz / c.fichero
                textos[c.fichero] = p.read_text(encoding="utf-8") if p.exists() else None
            if textos[c.fichero] is None:
                out.append(Resultado(c, "FAIL", detalle=f"no existe {c.fichero}"))
                continue
            out.append(evaluar(c, textos[c.fichero], con, lentos, con_co, con_alm))
        return out
    finally:
        for k in con_alm.values():
            k.close()
        if con is not None:
            con.close()
        if con_co is not None:
            con_co.close()


# ---------------------------------------------------------------- value functions

def _dq() -> dict:
    return json.loads((ROOT / "data" / "dq_report.json").read_text(encoding="utf-8"))


def _eval(split: str) -> dict:
    return json.loads((ROOT / "agente" / "eval" / "resultados" / f"{split}.json").read_text(encoding="utf-8"))


def _ev_ok(split: str) -> float:
    return float(sum(1 for f in _eval(split)["filas"] if f["correcto"]))


def _ev_n(split: str) -> float:
    return float(len(_eval(split)["filas"]))


def _n_ops(_con) -> float:
    from agente.ops import REGISTRO
    return float(len(REGISTRO))


def _hipotesis(_con) -> float:
    """Distinct hypotheses evaluated under the newest data signature in the (append-only) ledger."""
    from pipeline.hallazgos import RENOMBRADAS, leer_ledger
    rows = leer_ledger(ROOT / "wiki" / "hallazgos" / "ledger.csv")
    if not rows:
        return 0.0
    ultima = rows[-1]["sha_datos"]
    # una hipotesis renombrada cuenta una vez: el id viejo sigue en el ledger (solo agrega filas)
    return float(len({r["id"] for r in rows if r["sha_datos"] == ultima} - set(RENOMBRADAS.values())))


def _eventos_cercanos(con) -> float:
    return float(con.execute("select count(*) from int_interferencia_evento where banda = 'cercano'").fetchone()[0])


def _cuenca(col: str) -> Callable:
    return lambda con: con.execute(f"select {col} from mart_anisotropia_area where area = 'Cuenca'").fetchone()[0]


def _brecha_mes1(con) -> float:
    """Median near-parent index minus median control index at month 1, all ages, in points (positive = loss)."""
    from agente.ops import ArgsBrecha, interferencia_brecha
    return -100 * interferencia_brecha(con, ArgsBrecha(k=1))["valor"]


def _brecha_anio(anio: int) -> Callable:
    return lambda con: -100 * con.execute("select brecha_mes_1 from mart_interferencia_anual where anio = ?", [anio]).fetchone()[0]


def _carga_anual(col: str, factor: float = 100.0, veredicto: str | None = None, estadistico: str = "2026") -> Callable:
    """A column of the pre-registered 2026 test (mart_carga_anual_prueba). With `veredicto`, nan unless the stored verdict is
    that one, so the claim fails when the document prints a verdict the rule no longer gives. `estadistico` picks the row:
    "2026" is the test, "2025_2026" the pooled figure the rule publishes as descriptive, without a verdict."""
    def f(con):
        v, ver = con.execute(f"select {col}, veredicto from mart_carga_anual_prueba where estadistico = ?", [estadistico]).fetchone()
        return float("nan") if veredicto and ver != veredicto else factor * v
    return f


W_ANUAL = "wiki/hallazgos/carga_anual.md"


def _carga_anual_perfil(muestra: str, anio: int, col: str, factor: float = 1.0) -> Callable:
    """A cell of the yearly profile of the 2026 test page (mart_carga_anual)."""
    return lambda con: factor * con.execute(f"select {col} from mart_carga_anual where muestra = ? and anio = ?",
                                            [muestra, anio]).fetchone()[0]


def _claims_carga_anual() -> list[Claim]:
    """Every number of the 2026 test page (wiki/hallazgos/carga_anual.md): the test, its operator guard, the bootstrap
    resamples that entered the interval, the pooled descriptive figure and the yearly profile of both samples."""
    s, d1 = r"-?\d+,\d+", "{:.1f}"
    J = "2025_2026"   # the pooled row; the default row of _carga_anual is the test itself
    cab = r"antig.edad constante\): "
    jun = r"D con 2025 y 2026 juntos: "
    cl = [
        _c("carga_anual_d@wiki", W_ANUAL, cab + SIG + r" puntos, IC 95 %", _carga_anual("d"), 0.05, d1),
        _c("carga_anual_ic_bajo@wiki", W_ANUAL, cab + s + r" puntos, IC 95 % \[" + SIG + ", " + s + r"\]",
           _carga_anual("ic_bajo"), 0.05, d1),
        _c("carga_anual_ic_alto@wiki", W_ANUAL, cab + s + r" puntos, IC 95 % \[" + s + ", " + SIG + r"\]",
           _carga_anual("ic_alto"), 0.05, d1),
        _c("carga_anual_n@wiki", W_ANUAL, r"Eventos cercanos de 2026 con el mes 1 medido: (\d+)\.", _carga_anual("n_cercanos", 1), 0),
        _c("carga_anual_bloques@wiki", W_ANUAL, r"Bloques de 5 km en total: (\d+)\.", _carga_anual("n_bloques", 1), 0),
        _c("carga_anual_reps@wiki", W_ANUAL, r"Remuestras del bootstrap con D definido: (\d+) de \d+\.",
           _carga_anual("reps_validas", 1), 0),
        _c("carga_anual_d_ypf@wiki", W_ANUAL, r"D_YPF = " + SIG + r" puntos", _carga_anual("d_ypf"), 0.05, d1),
        _c("carga_anual_n_ypf@wiki", W_ANUAL, r"puntos con (\d+) eventos cercanos de YPF en 2026", _carga_anual("n_ypf", 1), 0),
        _c("carga_anual_juntos_d@wiki", W_ANUAL, jun + SIG + r" puntos", _carga_anual("d", estadistico=J), 0.05, d1),
        _c("carga_anual_juntos_ic_bajo@wiki", W_ANUAL, jun + s + r" puntos, IC 95 % \[" + SIG + ", " + s + r"\]",
           _carga_anual("ic_bajo", estadistico=J), 0.05, d1),
        _c("carga_anual_juntos_ic_alto@wiki", W_ANUAL, jun + s + r" puntos, IC 95 % \[" + s + ", " + SIG + r"\]",
           _carga_anual("ic_alto", estadistico=J), 0.05, d1),
        _c("carga_anual_juntos_n@wiki", W_ANUAL, r"\] \((\d+) cercanos, \d+ bloques", _carga_anual("n_cercanos", 1, estadistico=J), 0),
        _c("carga_anual_juntos_bloques@wiki", W_ANUAL, r"\] \(\d+ cercanos, (\d+) bloques", _carga_anual("n_bloques", 1, estadistico=J), 0),
        _c("carga_anual_juntos_reps@wiki", W_ANUAL, r"bloques, (\d+) de \d+ remuestras con D definido",
           _carga_anual("reps_validas", 1, estadistico=J), 0),
    ]
    cols = [("hijos", "hijos", 1, 0, "{:.0f}"), ("cercanos", "eventos_cercanos", 1, 0, "{:.0f}"),
            ("controles", "eventos_control", 1, 0, "{:.0f}"), ("bloques", "bloques_5km", 1, 0, "{:.0f}"),
            ("brecha", "brecha", 100, 0.05, d1), ("ic_bajo", "ic_bajo", 100, 0.05, d1), ("ic_alto", "ic_alto", 100, 0.05, d1)]
    for muestra in ("constante", "completa"):
        for anio in range(2019, 2027):
            pre = rf"\| {anio} \| {muestra} \| "
            for nom, col, factor, tol, fm in cols:
                celdas = [("(" + (r"\d+" if c[2] == 1 else s) + ")") if c[0] == nom else (r"\d+" if c[2] == 1 else s) for c in cols]
                cl.append(_c(f"carga_anual_perfil_{muestra}_{anio}_{nom}@wiki", W_ANUAL, pre + r" \| ".join(celdas) + r" \|",
                             _carga_anual_perfil(muestra, anio, col, factor), tol, fm))
    return cl


def _diferido(operador: str | None = None) -> Callable:
    def f(con):
        q = "select sum(petroleo_diferido_bbl) / 1e6 from mart_interferencia_diferida"
        if operador:
            return con.execute(q + " where operador = ?", [operador]).fetchone()[0]
        return con.execute(q).fetchone()[0]
    return f


def _rango_bbl(variante: str, tope: str | None = None) -> Callable:
    """Barriles de una variante de mart_diferido_rango. Con `tope`, el minimo con esa otra variante: el texto solo coincide si
    la variante no supera al tope (sin duplicar <= original, cota inferior <= cota superior)."""
    def f(con):
        d = dict(con.execute("select variante, diferido_bbl from mart_diferido_rango").fetchall())
        return min(d[variante], d[tope]) if tope else d[variante]
    return f


def _rango_mbbl(variante: str) -> Callable:
    return lambda con: _rango_bbl(variante)(con) / 1e6


def _evento_mediana(con) -> float:
    """Mediana por evento a 24 meses de toda la cuenca, acotada a [P25, P75]: el texto solo coincide si el orden es el correcto."""
    p25, med, p75 = con.execute("select p25_bbl, mediana_bbl, p75_bbl from mart_diferido_operador where operador = 'TODAS'").fetchone()
    return min(max(med, p25), p75)


def _evento_mediana_signo(con) -> float:
    """La mediana que imprime la pagina junto a la palabra 'debajo' o 'encima' de cero; nan si la palabra no es la del signo
    de la mediana del warehouse (el claim falla)."""
    med = con.execute("select mediana_bbl from mart_diferido_operador where operador = 'TODAS'").fetchone()[0]
    m = re.search(r"mediana por evento a 24 meses \((-?[\d.]+) barriles\) queda por (debajo|encima) de cero",
                  (ROOT / W_DIF).read_text(encoding="utf-8"))
    if not m or (m.group(2) == "debajo") != (med < 0):
        return float("nan")
    return parse_numero(m.group(1))


def _operador_mediana(operador: str) -> Callable:
    return lambda con: con.execute("select mediana_bbl from mart_diferido_operador where operador = ?", [operador]).fetchone()[0]


def _pads(clave: str) -> Callable:
    from pipeline import pads
    return lambda con: pads.cifras(con)[clave]


def _rob_n() -> Callable:
    return lambda con: con.execute("select count(*) from mart_robustez_eje where grupo <> 'completa'").fetchone()[0]


def _rob_definidos(con) -> float:
    from pipeline.costo import ANCHO_MAX
    return con.execute("select count(*) from mart_robustez_eje where grupo <> 'completa' and ancho_ic < ?", [ANCHO_MAX]).fetchone()[0]


def _rob_indefinidos(con) -> float:
    from pipeline.costo import ANCHO_MAX
    return con.execute("select count(*) from mart_robustez_eje where grupo <> 'completa' and ancho_ic >= ?", [ANCHO_MAX]).fetchone()[0]


def _rob_p_alto(con) -> float:
    from pipeline.costo import P_EJE_COSTO
    return con.execute("select count(*) from mart_robustez_eje where grupo <> 'completa' and p_perm >= ?", [P_EJE_COSTO]).fetchone()[0]


def _rob_alternativas(con) -> float:
    return con.execute("select count(*) - 1 from mart_robustez_costo").fetchone()[0]


def _coef_desvio(con) -> float:
    return con.execute("select coef from mart_robustez_costo where especificacion = 'Muestra completa'").fetchone()[0]


def _shmax(_con) -> float:
    from pipeline.robustez import SHMAX
    return SHMAX


def _prod_kbbl(con) -> float:
    from agente.ops import ArgsProduccion, produccion_vm
    return produccion_vm(con, ArgsProduccion())["valor"]


def _ypf_pct(con) -> float:
    from agente.ops import ArgsProduccion, ArgsRanking, produccion_vm, ranking_operadores
    total = produccion_vm(con, ArgsProduccion())["valor"]
    ypf = next(r["petroleo_kbbl_d"] for r in ranking_operadores(con, ArgsRanking())["filas"] if r["operador"] == "YPF")
    return 100 * ypf / total


def _diseno(cohorte: int, campo: str) -> Callable:
    def f(con):
        from agente.ops import ArgsDiseno, diseno_cohorte
        return diseno_cohorte(con, ArgsDiseno(cohorte=cohorte, grupo="YPF"))["filas"][0][campo]
    return f


def _pretrend_descontada(tabla: str) -> Callable:
    """Month-1 gap minus the pre-trend gap at month -1, in points (positive = additional loss)."""
    def f(con):
        b = dict(con.execute(f"select k, brecha from {tabla} where k in (-1, 1)").fetchall())
        return -100 * (b[1] - b[-1])
    return f


def _fechas_falsas(agg: str) -> Callable:
    return lambda con: 100 * con.execute(
        f"select {agg}(brecha_mes1) from mart_placebo_fechas where desplazamiento_meses <> 0").fetchone()[0]


def _permutacion(col: str) -> Callable:
    return lambda con: 100 * con.execute(f"select {col} from mart_placebo_permutacion").fetchone()[0]


def _pretrend_ic(col: str) -> Callable:
    return lambda con: -100 * con.execute(
        f"select {col} from mart_placebo_pretrend_base_original where k = 1").fetchone()[0]


def _desc_ref_k1(con) -> float:
    """Oil-volume gap at month 1 with the headline base (months -3 to -1), in points."""
    return 100 * con.execute("select brecha from mart_descomposicion_k where panel = 'petroleo_base_original' and k = 1").fetchone()[0]


def _desc_n_bandas_cercanas(con) -> float:
    return con.execute("select sum(n_banda) from mart_descomposicion_distancia "
                       "where km_hasta <= 1 and banda <> '0 a 1' and base = '-6 a -4'").fetchone()[0]


def _desc_n_k1(con) -> float:
    return con.execute("select n_near from mart_descomposicion_k where panel = 'petroleo' and k = 1").fetchone()[0]


def _desc_anillo(col: str) -> Callable:
    """Far-ring (5 to 10 km) against 2 to 5 km at month 1, in points."""
    return lambda con: 100 * con.execute(
        f"select {col} from mart_descomposicion_distancia where km_desde = 5 and km_hasta = 10 and control like '2 a 5%'").fetchone()[0]


def _desc_cabecera(con) -> float:
    """All parents under 1 km against the 5 to 10 km ring, headline base (months -3 to -1), in points."""
    return 100 * con.execute("select brecha from mart_descomposicion_distancia where banda = '0 a 1' and base = '-3 a -1'").fetchone()[0]


def _desc_anillo_abs(con) -> float:
    return abs(_desc_anillo("brecha")(con))


def _desc_adit(col: str, variante: str = "con_cerrados") -> Callable:
    """Share (percent) from the additive decomposition at month 1."""
    return lambda con: 100 * con.execute(f"select {col} from mart_descomposicion_aditiva where variante = ? and k = 1", [variante]).fetchone()[0]


def _desc_cierres(col: str) -> Callable:
    return lambda con: 100 * con.execute(f"select {col} from mart_descomposicion_cierres").fetchone()[0]


def _holdout_eje(modelo: str) -> Callable:
    return lambda con: con.execute("select eje from mart_validacion_holdout where modelo like ?", [modelo + "%"]).fetchone()[0]


def _costo_cv_r2(modelo: str) -> Callable:
    return lambda con: con.execute("select r2 from mart_costo_cv where modelo = ?", [modelo]).fetchone()[0]


def _diferido_bbl(operador: str | None = None) -> Callable:
    return lambda con: 1e6 * _diferido(operador)(con)


def _sitio(patron: str) -> Callable:
    """The number the committed dashboard prints (site/index.html, rendered by pipeline.report), so the README claim
    holds only while both surfaces say the same thing."""
    def f(_con):
        v = extraer((ROOT / S).read_text(encoding="utf-8"), patron)
        if v is None:
            raise RuntimeError(f"site/index.html ya no contiene {patron}")
        return v
    return f


def _pretrend_k(k: int) -> Callable:
    """Pre-trend gap of the clean base (months -6 to -4) at month k, in points (negative = near parents below)."""
    return lambda con: 100 * con.execute("select brecha from mart_placebo_pretrend where k = ?", [k]).fetchone()[0]


def _brecha_k_original(k: int) -> Callable:
    """Oil gap at month k with the headline base (months -3 to -1), in points."""
    return lambda con: 100 * con.execute(
        "select brecha from mart_descomposicion_k where panel = 'petroleo_base_original' and k = ?", [k]).fetchone()[0]


def _banda_brecha(banda: str) -> Callable:
    """Month-1 gap of a distance band against the 5 to 10 km ring (clean base), in points."""
    return lambda con: 100 * con.execute(
        "select brecha from mart_descomposicion_distancia where banda = ? and base = '-6 a -4' and control like '5 a 10%'",
        [banda]).fetchone()[0]


def _bandas_cercanas(agg: str) -> Callable:
    """min / max of the gaps of the bands that end at 1 km or less (without the pooled row), in points."""
    return lambda con: 100 * con.execute(
        f"select {agg}(brecha) from mart_descomposicion_distancia "
        "where km_hasta <= 1 and banda <> '0 a 1' and base = '-6 a -4'").fetchone()[0]


def _km(col: str, banda: str) -> Callable:
    return lambda con: con.execute(f"select {col} from mart_descomposicion_distancia where banda = ? and base = '-6 a -4'",
                                   [banda]).fetchone()[0]


def _n_intervalos(con) -> float:
    """Intervals the decomposition page prints: one per row of its three tables."""
    return float(sum(con.execute(f"select count(*) from {t}").fetchone()[0] for t in
                     ("mart_descomposicion_k", "mart_descomposicion_aditiva", "mart_descomposicion_distancia")))


def _permutaciones(con) -> float:
    return float(con.execute("select n_perm from mart_placebo_permutacion").fetchone()[0])


def _n_controles(_con) -> float:
    return float(len(_dq()["checks"]))


def _n_tests(_con) -> float:
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    m = re.search(r"(\d+) tests? collected", r.stdout) or re.search(r"(\d+) tests?", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    if not m:
        raise RuntimeError("no pude contar los tests: " + (r.stdout + r.stderr)[-300:])
    return float(m.group(1))


# ---------------------------------------------------------------- the claims

R = "README.md"
D = "docs/verificacion.md"
S = "site/index.html"
W_INT = "wiki/hallazgos/interferencia.md"
W_ROB = "wiki/hallazgos/robustez.md"
W_DES = "wiki/hallazgos/descomposicion.md"
W_DIF = "wiki/hallazgos/diferido.md"
W_SINC = "wiki/hallazgos/sincronia.md"
W_DEC = "wiki/hallazgos/decision_operador.md"
W_POT = "wiki/hallazgos/potencia_dosis.md"
W_LIM = "wiki/hallazgos/limites.md"
CASO = "docs/caso-interferencia.md"
DQ = "data/dq_report.json"
N = r"([\d.]+)"          # integer with thousands dots
DEC = r"(\d+,\d+)"       # decimal with comma
NEG = r"(-\d+,\d+)"      # negative decimal with comma
SIG = r"(-?\d+,\d+)"     # decimal with comma, either sign


def _c(id, fichero, patron, fn, tol=0.5, formato="{:,.0f}", wh=True, lento=False, almacen="vm", opcional=False) -> Claim:
    return Claim(id, fichero, patron, fn, tol, formato, wh, lento, almacen, opcional)


W_CO = "wiki/hallazgos/colorado_datos.md"


def _co(clave: str) -> Callable:
    return lambda con: con.execute("select valor from mart_co_conciliacion where clave = ?", [clave]).fetchone()[0]


def _claims_colorado() -> list[Claim]:
    """Cifras de la pagina del Colorado contra su warehouse; se saltan (SKIP) sin data/colorado/warehouse.duckdb."""
    out = []
    filas = [("Pozo-mes (formaciones y sidetracks sumados)", "prod_pozo_mes"), ("Pozos con producción", "prod_pozos"),
             ("Archivo de pozos de ECMC", "pozos_archivo"), ("Pozos con producción horizontales", "pozos_prod_horizontales"),
             ("Pads (ubicaciones a menos de 50 m)", "pads"), ("Divulgaciones de FracFocus en Colorado", "ff_divulgaciones"),
             ("Hijos (regla fijada)", "hijos")]
    for etiqueta, clave in filas:
        out.append(_c(f"co_{clave}@colorado", W_CO, r"\| " + re.escape(etiqueta) + r" \| " + N + r" \|", _co(clave), almacen="colorado"))
    tabla = [("Regla fijada, solo padres horizontales \\(corte principal\\)", "regla_horizontales"),
             ("Regla fijada, todos los padres", "regla_todos"), ("Método de la memoria, todos los padres", "memoria_todos")]
    for etiqueta, base in tabla:
        out.append(_c(f"co_{base}_cercanos@colorado", W_CO, r"\| " + etiqueta + r" \| [\d.]+ \| " + N + r" \|", _co(f"ev_{base}_cercanos"),
                      almacen="colorado"))
        out.append(_c(f"co_{base}_controles@colorado", W_CO, r"\| " + etiqueta + r" \| [\d.]+ \| [\d.]+ \| " + N + r" \|",
                      _co(f"ev_{base}_controles"), almacen="colorado"))
    return out


W_WY = "wiki/hallazgos/wyoming_datos.md"
PTS_W = r"(-?\d+,\d+)"


def _claims_wyoming() -> list[Claim]:
    """Cifras de la pagina de datos de Wyoming contra su warehouse; se saltan (SKIP) sin data/wyoming/warehouse.duckdb."""
    from pipeline.wyoming.build import FILAS_ETAPAS, FILAS_HIJOS, FILAS_POZOS
    filas = [(re.escape(e), k) for e, k in FILAS_ETAPAS + FILAS_POZOS + FILAS_HIJOS]
    out = []
    for etiqueta, clave in filas:
        out.append(_c(f"wy_{clave}@wyoming", W_WY, r"\| " + etiqueta + r" \| " + N + r" \|", _co(clave), almacen="wyoming"))
    for etiqueta, base in [("Regla fijada, solo padres horizontales \\(corte principal\\)", "regla_horizontales"),
                           ("Regla fijada, todos los padres", "regla_todos")]:
        out.append(_c(f"wy_{base}_cercanos@wyoming", W_WY, r"\| " + etiqueta + r" \| [\d.]+ \| " + N + r" \|", _co(f"ev_{base}_cercanos"),
                      almacen="wyoming"))
        out.append(_c(f"wy_{base}_controles@wyoming", W_WY, r"\| " + etiqueta + r" \| [\d.]+ \| [\d.]+ \| " + N + r" \|",
                      _co(f"ev_{base}_controles"), almacen="wyoming"))
    # hijos de las dos tablas de eventos, intermedios, hijos con padre cercano, tabla por anio y conteos de fecha
    out.append(_c("wy_regla_hijos@wyoming", W_WY, r"\| Regla fijada, solo padres horizontales \(corte principal\) \| " + N + r" \|", _co("hijos"), almacen="wyoming"))
    out.append(_c("wy_todos_hijos@wyoming", W_WY, r"\| Regla fijada, todos los padres \| " + N + r" \|", _co("hijos"), almacen="wyoming"))
    for id_, patron, clave in [
            ("interm_h", r"fuera de la brecha\), regla fijada: " + N + r" con padres horizontales", "ev_regla_horizontales_intermedios"),
            ("interm_t", r"con padres horizontales y " + N + r" con todos", "ev_regla_todos_intermedios"),
            ("hijos_padre_h", r"Hijos con al menos un padre cercano con base válida: " + N + r" \(padres horizontales\)", "hijos_con_padre_cercano_regla_horizontales"),
            ("hijos_padre_t", r"\(padres horizontales\) y " + N + r" \(todos\)", "hijos_con_padre_cercano_regla_todos"),
            ("sin_dias_texto", r"se toman como desconocidos: " + N + r" pozo-mes", "prod_pozo_mes_sin_dias_validos"),
            ("fuera_texto", r"- " + N + r" pozos con producción no están en los encabezados: no tienen", "pozos_prod_fuera_del_archivo"),
            ("tiempo_hijos", r"Entre los " + N + r" hijos, el mes de FIRSTCOMP", "hijos"),
            ("tiempo_mismo", r"es el del primer petróleo en " + N + r", el primer petróleo es posterior", "hijos_terminacion_mes_primer_petroleo"),
            ("tiempo_posterior", r"el primer petróleo es posterior en " + N + r" y anterior", "hijos_primer_petroleo_posterior"),
            ("tiempo_anterior", r"y anterior en " + N + r"\.", "hijos_primer_petroleo_anterior"),
            ("720921_dias", r"producción empieza en [\d-]+, " + N + r" días antes", "dias_720921")]:
        out.append(_c(f"wy_{id_}@wyoming", W_WY, patron, _co(clave) if clave != "dias_720921" else
                      (lambda con: float(con.execute("select dias_desde_primer_petroleo from co_hijo where pozo_id = 720921").fetchone()[0])),
                      almacen="wyoming"))
    anios = [r[0] for r in [(2018,), (2019,), (2020,), (2021,), (2022,), (2023,), (2024,)]]
    for a_ in anios:
        for j_, (corte, col) in enumerate([("horizontales", "cercanos"), ("horizontales", "controles"), ("todos", "cercanos"), ("todos", "controles")]):
            previas = [r"[\d.]+"] * j_
            patron = r"\| " + str(a_) + r" \| " + r" \| ".join(previas + [N]) + r" \|"
            out.append(_c(f"wy_anio{a_}_{corte}_{col}@wyoming", W_WY, patron,
                          (lambda con, a_=a_, corte=corte, col=col: float(con.execute(
                              f"select coalesce(sum({col}), 0) from mart_co_eventos_anio where anio = {a_} and corte = '{corte}'").fetchone()[0])),
                          almacen="wyoming"))
    # la correccion de lectura de FIRSTCOMP: cifras de antes de la correccion, fijas, en la pagina de replicacion
    W_RW = str(WYOMING.pagina.relative_to(ROOT))
    for id_, patron, valor, fm, tol in [
            ("antes_hijos", r"Antes de la corrección: " + N + r" hijos", 1177, "{:,.0f}", 0),
            ("antes_cercanos", r"hijos, " + N + r" eventos cercanos", 356, "{:,.0f}", 0),
            ("antes_controles", r"eventos cercanos y " + N + r" controles, brecha", 2291, "{:,.0f}", 0),
            ("antes_brecha", r"brecha del mes 1 de " + PTS_W + r" puntos \(IC por bloques de 5 km: -?\d+,\d+ a", -2.5, "{:.1f}", 0.05),
            ("antes_ic_bajo", r"\(IC por bloques de 5 km: " + PTS_W + r" a -?\d+,\d+\), brecha previa", -5.3, "{:.1f}", 0.05),
            ("antes_ic_alto", r"\(IC por bloques de 5 km: -?\d+,\d+ a " + PTS_W + r"\), brecha previa", 3.0, "{:.1f}", 0.05),
            ("antes_previa", r"brecha previa de " + PTS_W + r" y valor", -12.1, "{:.1f}", 0.05),
            ("antes_valor", r"y valor " + PTS_W + r"; tampoco", 0.096, "{:.3f}", 0.0005)]:
        out.append(_c(f"wy_{id_}@wyoming", W_RW, patron, (lambda _con, v=valor: float(v)), tol, fm, wh=False, almacen="wyoming"))
    return out


W_FM = "wiki/hallazgos/fuentes_mundo.md"


def _fm(clave: str) -> Callable:
    """Recuento de la auditoria de fuentes, leido de data/fuentes_mundo.json (no necesita ningun warehouse)."""
    def f(_con):
        from pipeline.fuentes_mundo import cargar, recuentos
        return float(recuentos(cargar())[clave])
    return f


W_MB = "wiki/hallazgos/mapa_base.md"


def _mb(clave: str) -> Callable:
    """Recuento del mapa base del mundo 4D, leido de data/base_mapa.json (no necesita ningun warehouse)."""
    def f(_con):
        from pipeline.base_mapa import DESTINO, recuentos
        return float(recuentos(json.loads(DESTINO.read_text(encoding="utf-8")))[clave])
    return f


def _claims_mapa_base() -> list[Claim]:
    pats = [("cols", r"una grilla de " + N + r" por \d+ celdas"), ("filas", r"una grilla de \d+ por " + N + r" celdas"),
            ("cota_min", r"con cotas de " + N + r" a "), ("cota_max", r"con cotas de [\d.]+ a " + N + r" m sobre el nivel"),
            ("rios", r"- " + N + r" ríos y arroyos con nombre"),
            ("agua_con_nombre", r"- " + N + r" cuerpos de agua con nombre"), ("embalses", r"\(" + N + r" embalses"),
            ("lagos", r"embalses, " + N + r" lagos"), ("cauces", r"lagos y " + N + r" cauces anchos"),
            ("agua_sin_nombre", r"cauces anchos\) y " + N + r" contornos sin nombre"),
            ("limites", r"- " + N + r" límites entre provincias"),
            ("localidades", r"- " + N + r" localidades, de una lista fija"),
            ("bloques", r"- " + N + r" concesiones de explotación de"),
            ("operadoras", r"concesiones de explotación de " + N + r" empresas operadoras")]
    return [_c(f"mb_{k}@mapa_base", W_MB, pat, _mb(k), 0, wh=False) for k, pat in pats]


def _claims_fuentes_mundo() -> list[Claim]:
    pats = [("total", r"Se auditaron " + N + r" jurisdicciones"), ("entran", r"jurisdicciones\. " + N + r" entran al estudio"),
            ("por_pozo_con_fractura", r"Por nivel: " + N + r" publican produccion por pozo con fecha de fractura o terminacion"),
            ("por_pozo_sin_fractura", r"o terminacion, " + N + r" por pozo sin esa fecha"),
            ("por_lease_o_campo", r"sin esa fecha, " + N + r" por lease, campo o instalacion"),
            ("solo_totales", r"instalacion, " + N + r" solo totales"),
            ("nada_publico", r"solo totales, " + N + r" nada publico o de pago"),
            ("registro_de_fractura", r"de pago, " + N + r" es un registro de fracturas"),
            ("no_verificado", r"sin petroleo y " + N + r" no se pudieron verificar")]
    return [_c(f"fm_{k}@fuentes_mundo", W_FM, pat, _fm(k), wh=False) for k, pat in pats]


W_REP = "wiki/hallazgos/replicacion.md"


def _rep_sql(sql: str, factor: float = 1.0) -> Callable:
    return lambda con: factor * con.execute(sql).fetchone()[0]


def _celdas_rep(tipos: list[str], objetivo: int, parte: str = "") -> str:
    """Regex de las celdas de una fila de tabla de la pagina de replicacion; captura la celda `objetivo` (o su limite `lo`/`hi`)."""
    out = []
    for i, t in enumerate(tipos):
        if t == "par":
            a, b = r"-?\d+,\d+", r"-?\d+,\d+"
            if i == objetivo:
                a, b = ("(" + a + ")", b) if parte == "lo" else (a, "(" + b + ")")
            out.append(a + " a " + b)
        else:
            rx = {"n": r"[\d.]+", "p": r"-?\d+,\d+"}[t]
            out.append("(" + rx + ")" if i == objetivo else rx)
    return r" \| ".join(out) + r" \|"


# Frases de la pagina de replicacion que solo existen en una de las dos lecturas de los datos (por dia producido menor o no, la
# regla se sostiene o no). En Colorado estan fijas y se exigen; en otra cuenca, si la frase no esta, el claim se salta.
_REP_DEPENDEN_DE_LA_LECTURA = {
    "rep_res_dia_brecha", "rep_res_dia_bajo", "rep_res_dia_alto", "rep_res_dia_pct", "rep_res_dia_prin", "rep_res_dia_ev_dia",
    "rep_res_dia_ev_prin", "rep_rob_dia_brecha_texto", "rep_rob_dia_pct", "rep_rob_dia_ev_dia", "rep_rob_dia_ev_prin", "rep_cierre_mes6"}


def _claims_replicacion(cuenca=None) -> list[Claim]:
    """Cada cifra de la pagina de replicacion de una cuenca (Colorado por defecto) y, solo en Colorado, de las frases que la citan;
    se saltan (SKIP) sin el warehouse de la cuenca."""
    from pipeline.replicacion import ROTULOS_ROBUSTEZ, rotulos_recuentos
    cuenca = cuenca or COLORADO
    es_co = cuenca.id == COLORADO.id
    W_REP = str(cuenca.pagina.relative_to(ROOT))
    out = []
    PTS_ = r"(-?\d+,\d+)"
    V = f"from {cuenca.tabla_veredicto} where k = 1"

    def add(id_, fichero, patron, fn, tol=0.05, fmt_="{:.1f}"):
        out.append(_c(id_ + "@" + cuenca.id, fichero, patron, fn, tol, fmt_, almacen=cuenca.id,
                      opcional=not es_co and id_ in _REP_DEPENDEN_DE_LA_LECTURA))

    # resumen
    add("rep_res_brecha", W_REP, r"base de los meses -3 a -1\): " + PTS_ + r" puntos\. IC", _rep_sql(f"select 100 * brecha {V}"))
    add("rep_res_pad_bajo", W_REP, r"por pads hijo: " + PTS_ + r" a -?\d+,\d+; por", _rep_sql(f"select 100 * ic_bajo_pad {V}"))
    add("rep_res_pad_alto", W_REP, r"por pads hijo: -?\d+,\d+ a " + PTS_ + r"; por", _rep_sql(f"select 100 * ic_alto_pad {V}"))
    add("rep_res_blq_bajo", W_REP, r"por bloques de 5 km: " + PTS_ + r" a -?\d+,\d+ \(", _rep_sql(f"select 100 * ic_bajo_bloque {V}"))
    add("rep_res_blq_alto", W_REP, r"por bloques de 5 km: -?\d+,\d+ a " + PTS_ + r" \(", _rep_sql(f"select 100 * ic_alto_bloque {V}"))
    add("rep_res_bloques", W_REP, r"\(" + N + r" bloques\)", _rep_sql("select bloques from mart_replicacion_serie where base = 'original' and k = 1"), 0, "{:,.0f}")
    add("rep_res_previa", W_REP, r"base de los meses -6 a -4\): " + PTS_ + r" puntos \(IC", _rep_sql(f"select 100 * brecha_previa_limpia {V}"))
    add("rep_res_previa_bajo", W_REP, r"\(IC 95% por bloques de 5 km: " + PTS_ + r" a -?\d+,\d+\)\.", _rep_sql(f"select 100 * ic_bajo_previa_bloque {V}"))
    add("rep_res_previa_alto", W_REP, r"\(IC 95% por bloques de 5 km: -?\d+,\d+ a " + PTS_ + r"\)\.", _rep_sql(f"select 100 * ic_alto_previa_bloque {V}"))
    add("rep_res_valor", W_REP, r"Valor de la hipótesis: " + PTS_ + r", el mayor", _rep_sql(f"select valor {V}"), 0.0005, "{:.3f}")
    add("rep_res_valor_ic", W_REP, r"por bloques, " + PTS_ + r", y la diferencia", _rep_sql(f"select ic_alto_bloque {V}"), 0.0005, "{:.3f}")
    add("rep_res_valor_dif", W_REP, r"previa menos mes 1\), " + PTS_ + r"; se replica",
        _rep_sql(f"select abs(brecha_previa_limpia) - abs(brecha) {V}"), 0.0005, "{:.3f}")
    ev = "select valor from mart_replicacion_recuentos where clave = "
    add("rep_res_cercanos", W_REP, r"Eventos con dato al mes 1: " + N + r" cercanos", _rep_sql(ev + "'eventos_cercanos_con_mes1'"), 0, "{:,.0f}")
    add("rep_res_controles", W_REP, r"cercanos y " + N + r" controles, de", _rep_sql(ev + "'eventos_controles_con_mes1'"), 0, "{:,.0f}")
    add("rep_res_pads", W_REP, r"controles, de " + N + r" pads hijo", _rep_sql(ev + "'pads_hijo_usados'"), 0, "{:,.0f}")
    add("rep_res_bloques_usados", W_REP, r"pads hijo y " + N + r" bloques de 5 km\.", _rep_sql(ev + "'bloques_5km_usados'"), 0, "{:,.0f}")
    add("rep_mes6_texto", W_REP, r"Al mes 6 la brecha es de " + PTS_ + r" puntos",
        _rep_sql("select 100 * brecha from mart_replicacion_serie where base = 'original' and k = 6"))
    # tabla de brechas por mes
    tipos = ["n", "n", "p", "par", "par", "n"]
    cols = ["n_cercanos", "n_controles", "100 * brecha", "100 * ic_bajo_pad", "100 * ic_alto_pad", "100 * ic_bajo_bloque", "100 * ic_alto_bloque", "bloques"]
    objetivos = [(0, ""), (1, ""), (2, ""), (3, "lo"), (3, "hi"), (4, "lo"), (4, "hi"), (5, "")]
    for base, rotulo, ks in (("original", "Meses -3 a -1", (1, 6)), ("limpia", "Meses -6 a -4", tuple(range(-3, 4)))):
        for k in ks:
            pre = r"\| " + rotulo + r" \| " + str(k) + r" \| "
            for col, (obj, parte) in zip(cols, objetivos):
                n_cell = col in ("n_cercanos", "n_controles", "bloques")
                add(f"rep_serie_{base}_k{k}_{col.split()[-1]}", W_REP, pre + _celdas_rep(tipos, obj, parte),
                    _rep_sql(f"select {col} from mart_replicacion_serie where base = '{base}' and k = {k}"),
                    0 if n_cell else 0.05, "{:,.0f}" if n_cell else "{:.1f}")
    # placebo
    tp = ["n", "p", "par", "p"]
    colp = ["n_cercanos", "100 * brecha_mes1", "100 * ic_bajo", "100 * ic_alto", "100 * brecha_real"]
    objp = [(0, ""), (1, ""), (2, "lo"), (2, "hi"), (3, "")]
    for d in (-12, 12):
        pre = r"\| " + str(d) + r" \| "
        for col, (obj, parte) in zip(colp, objp):
            n_cell = col == "n_cercanos"
            add(f"rep_placebo_d{d}_{col.split()[-1]}", W_REP, pre + _celdas_rep(tp, obj, parte),
                _rep_sql(f"select {col} from mart_replicacion_placebo where desplazamiento_meses = {d}"),
                0 if n_cell else 0.05, "{:,.0f}" if n_cell else "{:.1f}")
    # robustez
    tr = ["n", "n", "p", "par", "par", "p"]
    colr = ["n_cercanos", "n_controles", "100 * brecha_mes1", "100 * ic_bajo_pad", "100 * ic_alto_pad", "100 * ic_bajo_bloque",
            "100 * ic_alto_bloque", "100 * brecha_previa_limpia"]
    objr = [(0, ""), (1, ""), (2, ""), (3, "lo"), (3, "hi"), (4, "lo"), (4, "hi"), (5, "")]
    for corte, rotulo in ROTULOS_ROBUSTEZ.items():
        pre = r"\| " + re.escape(rotulo) + r" \| "
        for col, (obj, parte) in zip(colr, objr):
            n_cell = col in ("n_cercanos", "n_controles")
            add(f"rep_rob_{corte}_{col.split()[-1]}", W_REP, pre + _celdas_rep(tr, obj, parte),
                _rep_sql(f"select {col} from mart_replicacion_robustez where corte = '{corte}'"),
                0 if n_cell else 0.05, "{:,.0f}" if n_cell else "{:.1f}")
    # recuentos
    for clave, rotulo in rotulos_recuentos(cuenca).items():
        add(f"rep_rec_{clave}", W_REP, r"\| " + re.escape(rotulo) + r" \| " + N + r" \|", _rep_sql(ev + f"'{clave}'"), 0, "{:,.0f}")
    rob_ = "from mart_replicacion_robustez where corte = "
    ser_ = "from mart_replicacion_serie where base = "
    PCT_SQL = ("select 100 * (1 - abs(d.brecha_mes1) / abs(p.brecha_mes1)) from mart_replicacion_robustez d, mart_replicacion_robustez p "
               "where d.corte = 'por_dia_producido' and p.corte = 'principal'")
    DIA = rob_ + "'por_dia_producido'"
    # pagina: resumen (barrera baja, dia producido), robustez y cierre
    add("rep_res_k1_prev", W_REP, r"la brecha del mes -1 \(" + PTS_ + r", IC 95%", _rep_sql(f"select 100 * brecha_previa_limpia {V}"))
    k2 = lambda col: _rep_sql(f"select 100 * {col} {ser_}'limpia' and k = -2")   # noqa: E731
    add("rep_res_k2_brecha", W_REP, r"la del mes -2 \(" + PTS_ + r", IC:", k2("brecha"))
    add("rep_res_k2_bajo", W_REP, r"la del mes -2 \(-?\d+,\d+, IC: " + PTS_ + r" a", k2("ic_bajo_bloque"))
    add("rep_res_k2_alto", W_REP, r"la del mes -2 \(-?\d+,\d+, IC: -?\d+,\d+ a " + PTS_ + r"\)", k2("ic_alto_bloque"))
    add("rep_res_dia_brecha", W_REP, r"Medida por día producido, la brecha del mes 1 es de " + PTS_ + r" puntos", _rep_sql(f"select 100 * brecha_mes1 {DIA}"))
    add("rep_res_dia_bajo", W_REP, r"Medida por día producido, la brecha del mes 1 es de -?\d+,\d+ puntos \(IC 95% por bloques de 5 km: " + PTS_ + r" a",
        _rep_sql(f"select 100 * ic_bajo_bloque {DIA}"))
    add("rep_res_dia_alto", W_REP, r"Medida por día producido, la brecha del mes 1 es de -?\d+,\d+ puntos \(IC 95% por bloques de 5 km: -?\d+,\d+ a " + PTS_ + r"\)",
        _rep_sql(f"select 100 * ic_alto_bloque {DIA}"))
    add("rep_res_dia_pct", W_REP, r"puntos \(IC 95% por bloques de 5 km: -?\d+,\d+ a -?\d+,\d+\), cerca de (\d+)% menor", _rep_sql(PCT_SQL), 0.5, "{:.0f}")
    add("rep_res_dia_prin", W_REP, r"menor en valor absoluto que los " + PTS_ + r" de la medida principal", _rep_sql(f"select 100 * brecha_mes1 {rob_}'principal'"))
    add("rep_res_dia_ev_dia", W_REP, r"eventos cercanos \(" + N + r" frente a", _rep_sql(f"select n_cercanos {DIA}"), 0, "{:,.0f}")
    add("rep_res_dia_ev_prin", W_REP, r"eventos cercanos \([\d.]+ frente a " + N + r"\)", _rep_sql(f"select n_cercanos {rob_}'principal'"), 0, "{:,.0f}")
    add("rep_rob_dia_brecha_texto", W_REP, r"La brecha por día producido es de " + PTS_ + r" puntos", _rep_sql(f"select 100 * brecha_mes1 {DIA}"))
    add("rep_rob_dia_pct", W_REP, r"puntos, cerca de (\d+)% menor que la principal", _rep_sql(PCT_SQL), 0.5, "{:.0f}")
    add("rep_rob_dia_ev_dia", W_REP, r"con " + N + r" eventos cercanos frente a", _rep_sql(f"select n_cercanos {DIA}"), 0, "{:,.0f}")
    add("rep_rob_dia_ev_prin", W_REP, r"eventos cercanos frente a " + N + r";", _rep_sql(f"select n_cercanos {rob_}'principal'"), 0, "{:,.0f}")
    # pagina: cierre
    add("rep_cierre_mes6", W_REP, r"Al mes 6 la brecha de " + re.escape(cuenca.nombre) + r" es de " + PTS_ + r" puntos",
        _rep_sql(f"select 100 * brecha {ser_}'original' and k = 6"))
    # frases que citan el resultado fuera de la pagina (solo Colorado)
    if es_co:
        add("rep_readme_brecha", R, r"Replicación en Colorado \(cuenca DJ\) \| " + PTS_ + r" puntos al mes 1", _rep_sql(f"select 100 * brecha {V}"))
        add("rep_readme_previa", R, r"previa de " + PTS_ + r" en el mes -1", _rep_sql(f"select 100 * brecha_previa_limpia {V}"))
        add("rep_readme_ic_bajo", R, r"por bloques de 5 km: " + PTS_ + r" a -?\d+,\d+ \| se replica", _rep_sql(f"select 100 * ic_bajo_bloque {V}"))
        add("rep_readme_ic_alto", R, r"por bloques de 5 km: -?\d+,\d+ a " + PTS_ + r" \| se replica", _rep_sql(f"select 100 * ic_alto_bloque {V}"))
        # caso: tabla de Colorado (las celdas de la fila de la regla, la previa del mes -1 y el corte por dia producido)
        add("rep_caso_brecha", CASO, r"\(la medida de la regla\): se replica \| " + PTS_ + r" \|", _rep_sql(f"select 100 * brecha {V}"))
        add("rep_caso_ic_bajo", CASO, r"se replica \| -?\d+,\d+ \| " + PTS_ + r" a -?\d+,\d+ \|", _rep_sql(f"select 100 * ic_bajo_bloque {V}"))
        add("rep_caso_ic_alto", CASO, r"se replica \| -?\d+,\d+ \| -?\d+,\d+ a " + PTS_ + r" \|", _rep_sql(f"select 100 * ic_alto_bloque {V}"))
        add("rep_caso_previa", CASO, r"Mes -1 previo, base limpia \| " + PTS_ + r" \|", _rep_sql(f"select 100 * brecha_previa_limpia {V}"))
        add("rep_caso_previa_bajo", CASO, r"Mes -1 previo, base limpia \| -?\d+,\d+ \| " + PTS_ + r" a",
            _rep_sql(f"select 100 * ic_bajo_previa_bloque {V}"))
        add("rep_caso_previa_alto", CASO, r"Mes -1 previo, base limpia \| -?\d+,\d+ \| -?\d+,\d+ a " + PTS_ + r" \|",
            _rep_sql(f"select 100 * ic_alto_previa_bloque {V}"))
        add("rep_caso_dia_pct", CASO, r"por día producido: cerca de (\d+)% menos", _rep_sql(PCT_SQL), 0.5, "{:.0f}")
        add("rep_caso_dia_brecha", CASO, r"con menos eventos \| " + PTS_ + r" \|", _rep_sql(f"select 100 * brecha_mes1 {DIA}"))
        add("rep_caso_dia_bajo", CASO, r"con menos eventos \| -?\d+,\d+ \| " + PTS_ + r" a", _rep_sql(f"select 100 * ic_bajo_bloque {DIA}"))
        add("rep_caso_dia_alto", CASO, r"con menos eventos \| -?\d+,\d+ \| -?\d+,\d+ a " + PTS_ + r" \|", _rep_sql(f"select 100 * ic_alto_bloque {DIA}"))
        # README: la fila de Colorado, corte por dia producido
        add("rep_readme_dia_brecha", R, r"por día producido la brecha es " + PTS_ + r", cerca de", _rep_sql(f"select 100 * brecha_mes1 {DIA}"))
        add("rep_readme_dia_pct", R, r"cerca de (\d+)% menor", _rep_sql(PCT_SQL), 0.5, "{:.0f}")
    return out


W_FAM = "wiki/hallazgos/replicacion_cuencas.md"


def _claims_familia() -> list[Claim]:
    """Cada cifra de la pagina de la familia de cuencas (la tabla por cuenca y la lectura k de n) y las frases del README que la citan."""
    from pipeline.cuencas import CUENCAS
    from pipeline.familia import FAMILIA, resultados_desde
    PTS_ = r"(-?\d+,\d+)"
    out: list[Claim] = []
    # las celdas numericas de una fila de la tabla, en orden; cada claim captura una y deja las demas sin capturar
    celdas = [("hijos", r"[\d.]+", "{:,.0f}", 0), ("cercanos", r"[\d.]+", "{:,.0f}", 0), ("controles", r"[\d.]+", "{:,.0f}", 0),
              ("brecha", r"-?\d+,\d+", "{:.1f}", 0.05), ("ic", r"-?\d+,\d+ a -?\d+,\d+", "{:.1f}", 0.05),
              ("previa", r"-?\d+,\d+", "{:.1f}", 0.05), ("valor", r"-?\d+,\d+", "{:.3f}", 0.0005)]
    for i, nombre in FAMILIA:
        V = f"from {CUENCAS[i].tabla_veredicto} where k = 1"
        pre = r"\| " + nombre + r" \| "
        sqls = {"hijos": "select valor from mart_replicacion_recuentos where clave = 'hijos'", "cercanos": f"select n_cercanos {V}",
                "controles": f"select n_controles {V}", "brecha": f"select 100 * brecha {V}",
                "ic_bajo": f"select 100 * ic_bajo_bloque {V}", "ic_alto": f"select 100 * ic_alto_bloque {V}",
                "previa": f"select 100 * brecha_previa_limpia {V}", "valor": f"select valor {V}"}
        for j, (nom, rx, fm, tol) in enumerate(celdas):
            antes = [c[1] for c in celdas[:j]]
            objetivos = [("ic_bajo", r"(-?\d+,\d+) a -?\d+,\d+"), ("ic_alto", r"-?\d+,\d+ a (-?\d+,\d+)")] if nom == "ic" else [(nom, "(" + rx + ")")]
            for clave, captura in objetivos:
                patron = pre + r" \| ".join(antes + [captura])
                out.append(_c(f"fam_{clave}@{i}", W_FAM, patron, _rep_sql(sqls[clave]), tol, fm, almacen=i))

    def k_de(cons):
        return float(sum(1 for v, _ in resultados_desde(cons).values() if v))

    def n_de(cons):
        return float(len(resultados_desde(cons)))
    out += [_c("fam_k@familia", W_FAM, r"Se replica en " + N + r" de \d+ cuencas", k_de, 0, almacen="familia"),
            _c("fam_n@familia", W_FAM, r"Se replica en \d+ de " + N + r" cuencas", n_de, 0, almacen="familia"),
            _c("fam_n_nota@familia", W_FAM, r"Son " + N + r" cuencas:", n_de, 0, almacen="familia")]
    # README: las frases del resumen (en espanol y en ingles) y la fila de Wyoming
    R = "README.md"
    out += [_c("fam_readme_k_es@familia", R, r"se replica en " + N + r" de \d+ cuencas", k_de, 0, almacen="familia"),
            _c("fam_readme_n_es@familia", R, r"se replica en \d+ de " + N + r" cuencas", n_de, 0, almacen="familia"),
            _c("fam_readme_k_en@familia", R, r"replicates in " + N + r" of \d+ basins", k_de, 0, almacen="familia"),
            _c("fam_readme_n_en@familia", R, r"replicates in \d+ of " + N + r" basins", n_de, 0, almacen="familia"),
            _c("fam_readme_fila_k@familia", R, r"Replicación por cuenca \([^)]*\) \| se replica en " + N + r" de \d+ cuencas", k_de, 0, almacen="familia"),
            _c("fam_readme_fila_n@familia", R, r"Replicación por cuenca \([^)]*\) \| se replica en \d+ de " + N + r" cuencas", n_de, 0, almacen="familia")]
    V = f"from {WYOMING.tabla_veredicto} where k = 1"
    fila = r"Replicación en Wyoming \(WOGCC\) \| "
    out += [_c("wy_readme_brecha@wyoming", R, fila + PTS_ + r" puntos al mes 1", _rep_sql(f"select 100 * brecha {V}"), 0.05, "{:.1f}", almacen="wyoming"),
            _c("wy_readme_previa@wyoming", R, fila + r"-?\d+,\d+ puntos al mes 1; previa de " + PTS_ + r" en el mes -1",
               _rep_sql(f"select 100 * brecha_previa_limpia {V}"), 0.05, "{:.1f}", almacen="wyoming"),
            _c("wy_readme_ic_bajo@wyoming", R, r"por bloques de 5 km: " + PTS_ + r" a -?\d+,\d+ \| no se replica", _rep_sql(f"select 100 * ic_bajo_bloque {V}"),
               0.05, "{:.1f}", almacen="wyoming"),
            _c("wy_readme_ic_alto@wyoming", R, r"por bloques de 5 km: -?\d+,\d+ a " + PTS_ + r" \| no se replica", _rep_sql(f"select 100 * ic_alto_bloque {V}"),
               0.05, "{:.1f}", almacen="wyoming")]
    return out


def _sinc_grupo(b: int, col: str, factor: float = 1.0) -> Callable:
    return lambda con: factor * con.execute(f"select {col} from mart_sincronia where bin = {b}").fetchone()[0]


def _sinc_pend(k: int, col: str, factor: float = 1.0) -> Callable:
    return lambda con: factor * con.execute(f"select {col} from mart_sincronia_pendiente where k = {k}").fetchone()[0]


SD = r"(-?\d+,\d+)"   # signed decimal with comma


def _claims_sincronia() -> list[Claim]:
    """Every number of the synchrony page: the summary bullets, the three terciles and the two slopes (month 0 and -1)."""
    cl = []
    celda = lambda j: r"[^|]*\| " * j  # noqa: E731  (skips j table cells)
    for b in (1, 2, 3):
        fila = r"\| " + str(b) + r" \| "
        cl += [
            _c(f"sinc_g{b}_f0_desde@wiki", W_SINC, fila + SD, _sinc_grupo(b, "fraccion_desde"), 0.0005, "{:.3f}"),
            _c(f"sinc_g{b}_f0_hasta@wiki", W_SINC, fila + celda(1) + SD, _sinc_grupo(b, "fraccion_hasta"), 0.0005, "{:.3f}"),
            _c(f"sinc_g{b}_cercanos@wiki", W_SINC, fila + celda(2) + N, _sinc_grupo(b, "eventos"), 0),
            _c(f"sinc_g{b}_control@wiki", W_SINC, fila + celda(3) + N, _sinc_grupo(b, "eventos_control"), 0),
            _c(f"sinc_g{b}_brecha@wiki", W_SINC, fila + celda(4) + SD, _sinc_grupo(b, "brecha_mes0", 100), 0.05, "{:.1f}"),
            _c(f"sinc_g{b}_ic_bajo@wiki", W_SINC, fila + celda(5) + SD + r" a", _sinc_grupo(b, "ic_bajo", 100), 0.05, "{:.1f}"),
            _c(f"sinc_g{b}_ic_alto@wiki", W_SINC, fila + celda(5) + r"-?\d+,\d+ a " + SD, _sinc_grupo(b, "ic_alto", 100), 0.05, "{:.1f}"),
        ]
    for k in (0, -1):
        fila = r"\| " + str(k) + r" \| "
        cl += [
            _c(f"sinc_k{k}_cercanos@wiki", W_SINC, fila + N, _sinc_pend(k, "eventos_cercanos"), 0),
            _c(f"sinc_k{k}_control@wiki", W_SINC, fila + celda(1) + N, _sinc_pend(k, "eventos_control"), 0),
            _c(f"sinc_k{k}_pads@wiki", W_SINC, fila + celda(2) + N, _sinc_pend(k, "pads"), 0),
            _c(f"sinc_k{k}_pendiente@wiki", W_SINC, fila + celda(3) + SD, _sinc_pend(k, "pendiente", 10), 0.05, "{:.1f}"),
            _c(f"sinc_k{k}_ic_bajo@wiki", W_SINC, fila + celda(4) + SD + r" a", _sinc_pend(k, "ic_bajo", 10), 0.05, "{:.1f}"),
            _c(f"sinc_k{k}_ic_alto@wiki", W_SINC, fila + celda(4) + r"-?\d+,\d+ a " + SD, _sinc_pend(k, "ic_alto", 10), 0.05, "{:.1f}"),
        ]
    # summary bullets
    r0 = r"brecha del mes 0: "
    cl += [
        _c("sinc_resumen_k0_pendiente@wiki", W_SINC, r0 + SD + r" puntos", _sinc_pend(0, "pendiente", 10), 0.05, "{:.1f}"),
        _c("sinc_resumen_k0_ic_bajo@wiki", W_SINC, r0 + r"-?\d+,\d+ puntos de índice por cada 0,1 de fracción del mes \(IC 95%: " + SD,
           _sinc_pend(0, "ic_bajo", 10), 0.05, "{:.1f}"),
        _c("sinc_resumen_k0_ic_alto@wiki", W_SINC, r0 + r".{0,120}?\(IC 95%: -?\d+,\d+ a " + SD + r"\)", _sinc_pend(0, "ic_alto", 10), 0.05,
           "{:.1f}"),
        _c("sinc_resumen_k0_cercanos@wiki", W_SINC, r"sobre " + N + r" eventos cercanos y", _sinc_pend(0, "eventos_cercanos"), 0),
        _c("sinc_resumen_k0_control@wiki", W_SINC, r"eventos cercanos y " + N + r" controles", _sinc_pend(0, "eventos_control"), 0),
        _c("sinc_resumen_k0_pads@wiki", W_SINC, r"controles de " + N + r" pads hijo", _sinc_pend(0, "pads"), 0),
        _c("sinc_resumen_k0_total@wiki", W_SINC, r"del mes la brecha cambia " + SD + r" puntos", _sinc_pend(0, "pendiente", 100), 0.05, "{:.1f}"),
        _c("sinc_resumen_km1_pendiente@wiki", W_SINC, r"sin días expuestos: " + SD + r" puntos", _sinc_pend(-1, "pendiente", 10), 0.05, "{:.1f}"),
        _c("sinc_resumen_km1_ic_bajo@wiki", W_SINC, r"sin días expuestos: .{0,40}?\(IC 95%: " + SD + r" a", _sinc_pend(-1, "ic_bajo", 10), 0.05,
           "{:.1f}"),
        _c("sinc_resumen_km1_ic_alto@wiki", W_SINC, r"sin días expuestos: .{0,80}?\(IC 95%: -?\d+,\d+ a " + SD + r"\)", _sinc_pend(-1, "ic_alto", 10),
           0.05, "{:.1f}"),
        _c("sinc_resumen_km1_cercanos@wiki", W_SINC, r"puntos por cada 0,1 \(IC 95%: [^)]*\), sobre " + N + r" eventos cercanos",
           _sinc_pend(-1, "eventos_cercanos"), 0),
    ]
    return cl


def _claims_potencia_dosis() -> list[Claim]:
    """Numeros de la pagina de potencia del nulo de dosis: MDE80 del modelo conjunto A, mayor MDE de Holm de A y B,
    potencia empirica de la simulacion a 0,2 desvios y pads para ver 0,2 con Holm. Todo se lee de los marts."""
    nombres = {"arena_etapa": "arena por etapa", "arena_rama": "arena por metro de rama",
               "presion": "presión máxima de tratamiento", "deplecion": "depleción del padre"}

    def _mde(var: str, col: str) -> Callable:
        return lambda con: con.execute(
            f"select {col} from mart_potencia_dosis where resultado = 'A' and modelo = 'conjunto' "
            f"and variable = '{var}'").fetchone()[0]

    def _mayor(res: str) -> Callable:
        return lambda con: con.execute(
            f"select max(mde80_holm_desvios) from mart_potencia_dosis where resultado = '{res}' "
            f"and modelo = 'conjunto'").fetchone()[0]

    def _menor_a() -> Callable:
        return lambda con: con.execute(
            "select min(mde80_holm_desvios) from mart_potencia_dosis where resultado = 'A' "
            "and modelo = 'conjunto'").fetchone()[0]

    def _sim(var: str, regla: str) -> Callable:
        return lambda con: con.execute(
            f"select potencia from mart_potencia_dosis_sim where variable = '{nombres[var]}' and nivel = '0,2' "
            f"and regla = '{regla}'").fetchone()[0]

    cl = []
    for var, nom in nombres.items():
        fila = r"\| " + re.escape(nom) + r" \| -?\d+,\d+ \| \d+,\d+ \| "
        cl.append(_c(f"pot_dosis_mde_{var}@wiki", W_POT, fila + DEC + r" \| \d+,\d+ \|", _mde(var, "mde80_desvios"),
                     0.0006, "{:.3f}"))
        cl.append(_c(f"pot_dosis_mde_holm_{var}@wiki", W_POT, fila + r"\d+,\d+ \| " + DEC + r" \|",
                     _mde(var, "mde80_holm_desvios"), 0.0006, "{:.3f}"))
    cl += [
        _c("pot_dosis_mayor_A@wiki", W_POT, r"Resultado A: \*\*no alcanza para 0,2\*\*: el mayor MDE80 de Holm del modelo "
           r"conjunto es de " + DEC, _mayor("A"), 0.006, "{:.2f}"),
        _c("pot_dosis_mayor_B@wiki", W_POT, r"Resultado B: \*\*no alcanza para 0,2\*\*: el mayor MDE80 de Holm del modelo "
           r"conjunto es de " + DEC, _mayor("B"), 0.006, "{:.2f}"),
        _c("pot_dosis_sim_presion_holm@wiki", W_POT,
           r"\| presión máxima de tratamiento \| 0,2 \| 0,200 \| Holm \| 200 \| \d+ \| " + DEC + r" \|",
           _sim("presion", "holm"), 0.0006, "{:.3f}"),
        _c("pot_dosis_sim_etapa_sin_ajustar@wiki", W_POT,
           r"\| arena por etapa \| 0,2 \| 0,200 \| sin ajustar \| 200 \| \d+ \| " + DEC + r" \|",
           _sim("arena_etapa", "sin_ajustar"), 0.0006, "{:.3f}"),
        _c("pot_dosis_pads_02_holm_etapa@wiki", W_POT,
           r"\| arena por etapa \| [\d.]+ \| [\d.]+ \| [\d.]+ \| [\d.]+ \| [\d.]+ \| [\d.]+ \| " + N + r" \|",
           _mde("arena_etapa", "pads_02_holm"), 0.5),
        _c("pot_dosis_readme_menor@readme", R, r"va de " + DEC + r" a \d+,\d+ desvíos de la caída por desvío de la dosis",
           _menor_a(), 0.006, "{:.2f}"),
        _c("pot_dosis_readme_mayor@readme", R, r"va de \d+,\d+ a " + DEC + r" desvíos de la caída por desvío de la dosis",
           _mayor("A"), 0.006, "{:.2f}"),
    ]
    return cl


W_ROBOP = "wiki/hallazgos/robustez_operador.md"
EJES_ROB = ("operador", "area")


def _claims_robustez_operador() -> list[Claim]:
    """Numeros de la pagina de robustez por operador y area: brecha completa, rango de las salidas de grupo y cota superior del peor caso."""
    def _agr(eje: str, k: int, agregado: str, col: str = "brecha") -> Callable:
        return lambda con: 100 * con.execute(
            f"select {agregado}({col}) from mart_robustez_operador where eje = '{eje}' and k = {k} "
            f"and salida <> '(muestra completa)'").fetchone()[0]

    def _completa(k: int) -> Callable:
        return lambda con: 100 * con.execute(
            f"select brecha from mart_robustez_operador where eje = 'operador' and k = {k} and salida = '(muestra completa)'").fetchone()[0]

    def _peor_cota(eje: str) -> Callable:
        return lambda con: 100 * con.execute(
            f"select ic_alto from mart_robustez_operador where eje = '{eje}' and k = 1 and salida <> '(muestra completa)' "
            f"order by brecha desc limit 1").fetchone()[0]

    def _n(eje: str) -> Callable:
        return lambda con: con.execute(
            f"select count(*) from mart_robustez_operador where eje = '{eje}' and k = 1 and salida <> '(muestra completa)'").fetchone()[0]

    cl = [
        _c("rob_op_completa_mes1@wiki", W_ROBOP, r"\| \(muestra completa\) \| [\d.]+ \| [\d.]+ \| " + SD + r" \|", _completa(1), 0.05, "{:.1f}"),
        _c("rob_op_completa_mes6@wiki", W_ROBOP,
           r"\| \(muestra completa\) \| [\d.]+ \| [\d.]+ \| -?\d+,\d+ \| -?\d+,\d+ a -?\d+,\d+ \| " + SD + r" \|",
           _completa(6), 0.05, "{:.1f}"),
    ]
    for eje in EJES_ROB:
        base = r"al sacar de a un " + {"operador": "operador", "area": "área"}[eje] + r": en las "
        cl += [
            _c(f"rob_op_{eje}_n@wiki", W_ROBOP, base + N + r" salidas", _n(eje), 0),
            _c(f"rob_op_{eje}_min1@wiki", W_ROBOP, base + r"\d+ salidas.{0,120}?queda entre " + SD + r" y", _agr(eje, 1, "min"), 0.05, "{:.1f}"),
            _c(f"rob_op_{eje}_max1@wiki", W_ROBOP, base + r"\d+ salidas.{0,120}?queda entre -?\d+,\d+ y " + SD + r" puntos",
               _agr(eje, 1, "max"), 0.05, "{:.1f}"),
            _c(f"rob_op_{eje}_cota@wiki", W_ROBOP, base + r"\d+ salidas.{0,300}?cota superior " + SD + r"\)", _peor_cota(eje), 0.05, "{:.1f}"),
        ]
    for eje in EJES_ROB:
        nom = {"operador": "operador", "area": "área"}[eje]
        cl += [
            _c(f"rob_op_{eje}_min6@wiki", W_ROBOP, r"al sacar de a un " + nom + r": en las .{0,500}?El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre " + SD + r" y",
               _agr(eje, 6, "min"), 0.05, "{:.1f}"),
            _c(f"rob_op_{eje}_max6@wiki", W_ROBOP, r"al sacar de a un " + nom + r": en las .{0,500}?El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre -?\d+,\d+ y " + SD + r" puntos",
               _agr(eje, 6, "max"), 0.05, "{:.1f}"),
            _c(f"rob_op_{eje}_peor6@wiki", W_ROBOP, r"al sacar de a un " + nom + r": en las .{0,700}?el peor caso es sin [^(]+ \(" + SD + r" puntos\)\.",
               _agr(eje, 6, "min"), 0.05, "{:.1f}"),
            _c(f"rob_op_{eje}_posthoc@wiki", W_ROBOP, r"entre las salidas es " + SD + r" puntos, sin " + ("YPF" if eje == "operador" else "LA AMARGA CHICA"),
               lambda con, e=eje: 100 * con.execute(f"select max(ic_alto) from mart_robustez_operador where eje = '{e}' and k = 1 and salida <> '(muestra completa)'").fetchone()[0],
               0.05, "{:.1f}"),
        ]
    cl += [
        _c("rob_op_readme_cierre@wiki", W_LIM, r"el cierre del mes 6 queda dentro de " + N + r" puntos", lambda con: 5, 0),
        _c("rob_op_readme_area_min@wiki", W_LIM, r"queda entre " + SD + r" y -?\d+,\d+ puntos con el IC 95% siempre por debajo de cero", _agr("area", 1, "min"), 0.05, "{:.1f}"),
        _c("rob_op_readme_area_max@wiki", W_LIM, r"queda entre -?\d+,\d+ y " + SD + r" puntos con el IC 95% siempre por debajo de cero", _agr("area", 1, "max"), 0.05, "{:.1f}"),
        _c("rob_op_readme_ypf@wiki", W_LIM, r"\(sin YPF: " + SD + r"\)",
           lambda con: 100 * con.execute("select brecha from mart_robustez_operador where eje = 'operador' and k = 1 and salida = 'YPF'").fetchone()[0],
           0.05, "{:.1f}"),
        _c("rob_op_readme_n_op@wiki", W_LIM, r"de a un operador \(" + N + r"\)", _n("operador"), 0),
        _c("rob_op_readme_n_area@wiki", W_LIM, r"o de a un área \(" + N + r"\)", _n("area"), 0),
    ]
    return cl


W_RESUMEN = "docs/resumen-operador.md"


def _claims_resumen_operador() -> list[Claim]:
    """Cada cifra de la hoja resumen para un operador, leida de los marts de decision, de robustez y de potencia de dosis."""
    def _q(sql: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(sql).fetchone()[0]

    def _cota_mes6(con) -> float:
        return math.ceil(100 * con.execute("select max(-brecha_mes6) from mart_decision_cierre").fetchone()[0])

    ed = "select {c} from mart_decision_edad where grupo_edad = '{g}'"
    rb = "select {a}(brecha) from mart_robustez_operador where eje = '{e}' and k = 1 and salida <> '(muestra completa)'"
    return [
        _c("resumen_gap1@doc", W_RESUMEN, r"rinden " + DEC + r" puntos menos de su caudal previo", _q(ed.format(c="-brecha_mes1", g="todos"), 100), 0.05, "{:.1f}"),
        _c("resumen_eventos@doc", W_RESUMEN, r"\(" + N + r" eventos\)", _q(ed.format(c="eventos", g="todos")), 0),
        _c("resumen_edad_min@doc", W_RESUMEN, r"Va de " + DEC + r" puntos menos con padres", _q("select min(-brecha_mes1) from mart_decision_edad where grupo_edad <> 'todos'", 100), 0.05, "{:.1f}"),
        _c("resumen_edad_max@doc", W_RESUMEN, r"a " + DEC + r" puntos menos con padres de 48", _q("select max(-brecha_mes1) from mart_decision_edad where grupo_edad <> 'todos'", 100), 0.05, "{:.1f}"),
        _c("resumen_op_min@doc", W_RESUMEN, r"un operador, la brecha queda entre " + DEC + r" y", _q(rb.format(a="max", e="operador"), -100), 0.05, "{:.1f}"),
        _c("resumen_op_max@doc", W_RESUMEN, r"un operador, la brecha queda entre \d+,\d+ y " + DEC + r" puntos menos", _q(rb.format(a="min", e="operador"), -100), 0.05, "{:.1f}"),
        _c("resumen_sin_ypf@doc", W_RESUMEN, r"\(sin YPF, " + DEC + r"\)",
           _q("select -brecha from mart_robustez_operador where eje = 'operador' and k = 1 and salida = 'YPF'", 100), 0.05, "{:.1f}"),
        _c("resumen_area_min@doc", W_RESUMEN, r"un área, entre " + DEC + r" y", _q(rb.format(a="max", e="area"), -100), 0.05, "{:.1f}"),
        _c("resumen_area_max@doc", W_RESUMEN, r"un área, entre \d+,\d+ y " + DEC + r" puntos menos", _q(rb.format(a="min", e="area"), -100), 0.05, "{:.1f}"),
        _c("resumen_mes6@doc", W_RESUMEN, r"queda en " + DEC + r" puntos menos con el control principal", _q(ed.format(c="-brecha_mes6", g="todos"), 100), 0.05, "{:.1f}"),
        _c("resumen_mes6_max@doc", W_RESUMEN, r"llega a " + DEC + r" puntos menos con la variante de control de mayor brecha", _q("select max(-brecha_mes6) from mart_decision_cierre", 100), 0.05, "{:.1f}"),
        _c("resumen_mes6_cota@doc", W_RESUMEN, r"dentro de (\d+) puntos", _cota_mes6, 0, "{:.0f}"),
        _c("resumen_diferido@doc", W_RESUMEN, r"es de " + N + r" m3 de petróleo por padre", _q(ed.format(c="diferido_medio_m3", g="todos")), 0.5),
        _c("resumen_dif_ic_bajo@doc", W_RESUMEN, r"intervalo del 95%: " + N + r" a", _q(ed.format(c="diferido_ic_bajo_m3", g="todos")), 0.5),
        _c("resumen_dif_ic_alto@doc", W_RESUMEN, r"intervalo del 95%: [\d.]+ a " + N + r"\)", _q(ed.format(c="diferido_ic_alto_m3", g="todos")), 0.5),
        _c("resumen_ic_alto@doc", W_RESUMEN, r"el límite alto más alto es de " + SD + r"\)",
           _q("select max(ic_alto) from mart_robustez_operador where k = 1 and salida <> '(muestra completa)'", 100), 0.05, "{:.1f}"),
        _c("resumen_mde@doc", W_RESUMEN, r"con 80% de potencia, de " + DEC + r" desvíos",
           _q("select max(mde80_holm_desvios) from mart_potencia_dosis where resultado = 'A' and modelo = 'conjunto'"), 0.006, "{:.2f}"),
    ]


W_MUNDO = "site/mundo.html"


def _claims_mundo() -> list[Claim]:
    """Cifras del texto fijo de site/mundo.html (pipeline.mundo.textos), leidas de los marts que las publican."""
    def _q(sql: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(sql).fetchone()[0]

    bl = "select {c} from mart_bloques where metrica = '{m}' and k = 1"
    orig, desc = "brecha_mes1_base_original", "brecha_mes1_descontada"
    ed = "select {c} from mart_decision_edad where grupo_edad = 'todos'"
    ev = "select count(*) from int_interferencia_evento where banda = '{b}'"
    return [
        _c("mundo_pozos@site", W_MUNDO, r"<b>" + N + r" pozos shale con ubicación de superficie</b>",
           _q("select count(*) from int_pozo_ubicacion"), 0),
        _c("mundo_rango_bajo@site", W_MUNDO, r"rinden <b>entre " + N + r" y", _q(bl.format(c="estimacion", m=desc), -100)),
        _c("mundo_rango_alto@site", W_MUNDO, r"rinden <b>entre \d+ y " + N + r" puntos menos</b>",
           _q(bl.format(c="estimacion", m=orig), -100)),
        _c("mundo_cercanos@site", W_MUNDO, r"\(" + N + r" eventos cercanos y", _q(ev.format(b="cercano")), 0),
        _c("mundo_controles@site", W_MUNDO, r"eventos cercanos y " + N + r" de control\)", _q(ev.format(b="control")), 0),
        _c("mundo_brecha1@site", W_MUNDO, r"de la brecha de " + N + r" puntos:", _q(bl.format(c="estimacion", m=orig), -100)),
        _c("mundo_ic5_bajo@site", W_MUNDO, r"de la brecha de \d+ puntos: " + N + r" a",
           _q(bl.format(c="ic_alto_5km", m=orig), -100)),
        _c("mundo_ic5_alto@site", W_MUNDO, r"de la brecha de \d+ puntos: \d+ a " + N + r" \(",
           _q(bl.format(c="ic_bajo_5km", m=orig), -100)),
        _c("mundo_bloques@site", W_MUNDO, r"\(" + N + r" bloques\)", _q(bl.format(c="bloques_5km", m=orig)), 0),
        _c("mundo_cierre_min@site", W_MUNDO, r"la brecha queda <b>entre " + DEC + r" y",
           _q("select -max(brecha_mes6) from mart_decision_cierre", 100), 0.05, "{:.1f}"),
        _c("mundo_cierre_max@site", W_MUNDO, r"la brecha queda <b>entre \d+,\d+ y " + DEC + r" puntos</b>",
           _q("select -min(brecha_mes6) from mart_decision_cierre", 100), 0.05, "{:.1f}"),
        _c("mundo_diferido@site", W_MUNDO, r"meses 0 a 6: <b>" + N + r" bbl</b>", _q(ed.format(c="diferido_medio_bbl"))),
        _c("mundo_dif_ic_bajo@site", W_MUNDO, r"bbl</b> \(IC 95%: " + N + r" a", _q(ed.format(c="diferido_ic_bajo_bbl"))),
        _c("mundo_dif_ic_alto@site", W_MUNDO, r"bbl</b> \(IC 95%: [\d.]+ a " + N + r"\)", _q(ed.format(c="diferido_ic_alto_bbl"))),
        _c("mundo_cota@site", W_MUNDO, r"podría no volver: " + N + r" bbl por evento",
           _q("select cota_bbl from mart_decision_perdida")),
    ]


W_GLOBO = "site/globo.html"


def _claims_globo() -> list[Claim]:
    """Cifras del texto fijo de site/globo.html (pipeline.globo.textos): la auditoria de fuentes y los veredictos de las tres cuencas,
    leidos de los mismos marts que publican las paginas de Vaca Muerta, Colorado y Wyoming."""
    from pipeline.familia import CUENCAS

    def _q(sql: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(sql).fetchone()[0]

    bl = "select {c} from mart_bloques where metrica = '{m}' and k = 1"
    orig, desc = "brecha_mes1_base_original", "brecha_mes1_descontada"
    out = [
        _c("globo_auditadas@globo", W_GLOBO, r"De " + N + r" jurisdicciones auditadas", _fm("total"), 0, wh=False),
        _c("globo_con_fractura@globo", W_GLOBO, r"auditadas, " + N + r" publican petróleo por pozo", _fm("por_pozo_con_fractura"), 0, wh=False),
        _c("globo_entran@globo", W_GLOBO, r"y " + N + r" entran al estudio", _fm("entran"), 0, wh=False),
        _c("globo_vm_bajo@globo", W_GLOBO, r"rinden <b>entre " + N + r" y", _q(bl.format(c="estimacion", m=desc), -100)),
        _c("globo_vm_alto@globo", W_GLOBO, r"rinden <b>entre \d+ y " + N + r" puntos menos</b>", _q(bl.format(c="estimacion", m=orig), -100)),
    ]
    for cid, nom, pre in (("colorado", "Colorado", "co"), ("wyoming", "Wyoming", "wy")):
        v = f"from {CUENCAS[cid].tabla_veredicto} where k = 1"
        cabeza = r"<b>" + nom + r", [^<]*</b> Brecha al mes 1 de <b>"
        ic = r"-?\d+,\d+ puntos</b> \(IC 95% por bloques de 5 km: "
        out += [
            _c(f"globo_{pre}_brecha@globo", W_GLOBO, cabeza + SD + r" puntos</b>", _q(f"select 100 * brecha {v}"), 0.05, "{:.1f}", almacen=cid),
            _c(f"globo_{pre}_ic_bajo@globo", W_GLOBO, cabeza + ic + SD + r" a", _q(f"select 100 * ic_bajo_bloque {v}"), 0.05, "{:.1f}", almacen=cid),
            _c(f"globo_{pre}_ic_alto@globo", W_GLOBO, cabeza + ic + r"-?\d+,\d+ a " + SD + r"\)", _q(f"select 100 * ic_alto_bloque {v}"), 0.05, "{:.1f}", almacen=cid),
        ]

        # La lectura en palabras ("se replica" / "no se replica", "incluye el cero") sale de un atributo numerico del texto fijo.
        out.append(_c(f"globo_{pre}_se_replica@globo", W_GLOBO, r'<li data-cuenca="' + cid + r'" data-se-replica="(\d)"',
                      _q(f"select cast(se_replica as integer) {v}"), 0, "{:.0f}", almacen=cid))
    out.append(_c("globo_wy_incluye_cero@globo", W_GLOBO, r'<li data-cuenca="wyoming"[^>]* data-incluye-cero="(\d)"',
                  _q(f"select cast(ic_bajo_bloque < 0 and ic_alto_bloque > 0 as integer) from {CUENCAS['wyoming'].tabla_veredicto} where k = 1"),
                  0, "{:.0f}", almacen="wyoming"))

    def k_de(cons):
        from pipeline.familia import resultados_desde
        return float(sum(1 for r, _ in resultados_desde(cons).values() if r))

    def n_de(cons):
        from pipeline.familia import resultados_desde
        return float(len(resultados_desde(cons)))
    out += [_c("globo_replican@globo", W_GLOBO, r"Se replica en " + N + r" de \d+ cuencas", k_de, 0, almacen="familia"),
            _c("globo_de@globo", W_GLOBO, r"Se replica en \d+ de " + N + r" cuencas", n_de, 0, almacen="familia")]
    return out


W_INFORME = "site/informe.html"


def _claims_informe() -> list[Claim]:
    """Cifras del informe para un operador (site/informe.html), leidas de los mismos marts que la hoja resumen."""
    def _q(sql: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(sql).fetchone()[0]

    ed = "select {c} from mart_decision_edad where grupo_edad = '{g}'"
    rb = "select {a}(brecha) from mart_robustez_operador where eje = '{e}' and k = 1 and salida <> '(muestra completa)'"
    ficha = r'{t}</div>\s*<div class="v num">'
    blq = "select {c} from mart_bloques where metrica = 'brecha_mes1_base_original' and k = 1"
    return [
        _c("informe_gap1@site", W_INFORME, ficha.format(t="Mes 1") + SD, _q(ed.format(c="brecha_mes1", g="todos"), 100), 0.05, "{:.1f}"),
        _c("informe_gap1_ic_bajo@site", W_INFORME, r"IC 95% por bloques de 5 km: " + SD + r" a", _q(blq.format(c="ic_bajo_5km"), 100), 0.05, "{:.1f}"),
        _c("informe_gap1_ic_alto@site", W_INFORME, r"IC 95% por bloques de 5 km: -?\d+,\d+ a " + SD + r"\)", _q(blq.format(c="ic_alto_5km"), 100), 0.05, "{:.1f}"),
        _c("informe_gap6@site", W_INFORME, ficha.format(t="Mes 6") + SD, _q(ed.format(c="brecha_mes6", g="todos"), 100), 0.05, "{:.1f}"),
        _c("informe_eventos@site", W_INFORME, r"Un estudio de " + N + r" eventos en los que", _q(ed.format(c="eventos", g="todos")), 0),
        _c("informe_padres@site", W_INFORME, r"a menos de 1 km \(" + N + r" padres distintos\)",
           _q("select count(distinct padre) from mart_interferencia_diferida"), 0),
        _c("informe_diferido@site", W_INFORME, ficha.format(t="Diferido") + N, _q(ed.format(c="diferido_medio_m3", g="todos")), 0.5),
        _c("informe_dif_ic_bajo@site", W_INFORME, r"0 a 6 \(IC 95%: " + N + r" a", _q(ed.format(c="diferido_ic_bajo_m3", g="todos")), 0.5),
        _c("informe_dif_ic_alto@site", W_INFORME, r"0 a 6 \(IC 95%: [\d.]+ a " + N + r"\)", _q(ed.format(c="diferido_ic_alto_m3", g="todos")), 0.5),
        _c("informe_cota@site", W_INFORME, ficha.format(t="Cota de pérdida") + N, _q("select cota_bbl from mart_decision_perdida"), 0.5),
        _c("informe_cierre_peor@site", W_INFORME, r"hasta " + SD + r" con el control más exigente",
           _q("select min(brecha_mes6) from mart_decision_cierre", 100), 0.05, "{:.1f}"),
        _c("informe_op_min@site", W_INFORME, r"la brecha del mes 1 queda entre " + SD, _q(rb.format(a="max", e="operador"), 100), 0.05, "{:.1f}"),
        _c("informe_op_max@site", W_INFORME, r"la brecha del mes 1 queda entre -?\d+,\d+ y " + SD, _q(rb.format(a="min", e="operador"), 100), 0.05, "{:.1f}"),
        _c("informe_ar_min@site", W_INFORME, r"de a un área \(\d+\), entre " + SD, _q(rb.format(a="max", e="area"), 100), 0.05, "{:.1f}"),
        _c("informe_ar_max@site", W_INFORME, r"de a un área \(\d+\), entre -?\d+,\d+ y " + SD, _q(rb.format(a="min", e="area"), 100), 0.05, "{:.1f}"),
        _c("informe_ic_alto@site", W_INFORME, r"su límite alto más alto es " + SD,
           _q("select max(ic_alto) from mart_robustez_operador where k = 1 and salida <> '(muestra completa)'", 100), 0.05, "{:.1f}"),
        _c("informe_mde@site", W_INFORME, r"con 80% de potencia es de " + DEC + r" desvíos",
           _q("select max(mde80_holm_desvios) from mart_potencia_dosis where resultado = 'A' and modelo = 'conjunto'"), 0.006, "{:.2f}"),
    ]


def _claims_decision() -> list[Claim]:
    """Numeros de la pagina de decision: brechas por edad, parte recuperada entre variantes, diferido por evento,
    cota de perdida y celdas de la grilla de valor. Cada valor se lee de los marts de decision."""
    from pipeline.decision import valor_indicativo

    def _edad(grupo: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(
            f"select {col} from mart_decision_edad where grupo_edad = '{grupo}'").fetchone()[0]

    def _cierre(agregado: str) -> Callable:
        return lambda con: 100 * con.execute(
            f"select {agregado}(parte_recuperada) from mart_decision_cierre").fetchone()[0]

    def _grilla(precio: float, tasa: float, rezago: float) -> Callable:
        def f(con):
            m3 = con.execute("select diferido_medio_m3 from mart_decision_edad "
                             "where grupo_edad = 'todos'").fetchone()[0]
            return valor_indicativo(m3, precio, tasa, rezago)["costo_de_diferir"]
        return f

    def _grilla_cota(precio: float) -> Callable:
        def f(con):
            m3 = con.execute("select cota_m3 from mart_decision_perdida").fetchone()[0]
            return valor_indicativo(m3, precio, 0.0, 0)["valor_cota_perdida"]
        return f

    cl = []
    for g in ("06-11", "12-23", "24-47", "48+", "todos"):
        fila = r"\| " + re.escape(g) + r" \| [\d.]+ \| "
        cl.append(_c(f"dec_edad_{g}_b1@wiki", W_DEC, fila + SD + r" \|", _edad(g, "brecha_mes1", 100), 0.05,
                     "{:.1f}"))
        cl.append(_c(f"dec_edad_{g}_b6@wiki", W_DEC, fila + r"-?\d+,\d+ \| " + SD + r" \|",
                     _edad(g, "brecha_mes6", 100), 0.05, "{:.1f}"))
    cl += [
        _c("dec_parte_min@wiki", W_DEC, r"La parte recuperada va de " + DEC + r"% a", _cierre("min"), 0.05,
           "{:.1f}"),
        _c("dec_parte_max@wiki", W_DEC, r"La parte recuperada va de \d+,\d+% a " + DEC + r"% entre variantes",
           _cierre("max"), 0.05, "{:.1f}"),
        _c("dec_diferido_central@wiki", W_DEC,
           r"El diferido medio por evento de todos los cercanos es " + N + r" m3 por padre",
           _edad("todos", "diferido_medio_m3"), 0.5),
        _c("dec_diferido_bajo@wiki", W_DEC, r"rango bajo a alto: " + N + r" a",
           _edad("todos", "diferido_bajo_m3"), 0.5),
        _c("dec_diferido_alto@wiki", W_DEC, r"rango bajo a alto: [\d.]+ a " + N + r" m3",
           _edad("todos", "diferido_alto_m3"), 0.5),
        _c("dec_cota_m3@wiki", W_DEC, r"La cota superior de pérdida es de [\d.]+ bbl \(([\d.]+) m3\)",
           lambda con: con.execute("select cota_m3 from mart_decision_perdida").fetchone()[0], 0.5),
        _c("dec_readme_parte_min@readme", R, r"se cierra a los 6 meses \((\d+) a \d+% según", _cierre("min"), 0.5),
        _c("dec_readme_parte_max@readme", R, r"se cierra a los 6 meses \(\d+ a (\d+)% según", _cierre("max"), 0.5),
        _c("dec_readme_diferido_bajo@readme", R, r"\((\d+) a \d+ m3 de petróleo en los meses 0 a 6",
           _edad("todos", "diferido_bajo_m3"), 0.5),
        _c("dec_readme_diferido_alto@readme", R, r"\(\d+ a (\d+) m3 de petróleo en los meses 0 a 6",
           _edad("todos", "diferido_alto_m3"), 0.5),
        _c("dec_readme_cota@readme", R, r"\((\d+) m3 por evento\), por edad del padre",
           lambda con: con.execute("select cota_m3 from mart_decision_perdida").fetchone()[0], 0.5),
        _c("dec_readme_quedan_min@readme", R, r"quedan (\d+) a \d+ puntos",
           lambda con: round(100 * con.execute("select min(-brecha_mes6) from mart_decision_cierre").fetchone()[0]), 0.5),
        _c("dec_readme_quedan_max@readme", R, r"quedan \d+ a (\d+) puntos",
           lambda con: round(100 * con.execute("select max(-brecha_mes6) from mart_decision_cierre").fetchone()[0]), 0.5),
        _c("dec_cota_bbl@wiki", W_DEC, r"La cota superior de pérdida es de " + N + r" bbl",
           lambda con: con.execute("select cota_bbl from mart_decision_perdida").fetchone()[0], 0.5),
        _c("dec_48_b6@wiki", W_DEC, r"La fila de 48 meses o más queda en " + SD + r" puntos en el mes 6",
           _edad("48+", "brecha_mes6", 100), 0.05, "{:.1f}"),
        _c("dec_acum24_media@wiki", W_DEC, r"toda la cuenca\): media (-?[\d.]+) bbl",
           lambda con: con.execute("select media_24m_bbl from mart_decision_perdida").fetchone()[0], 0.5),
        _c("dec_exceso@wiki", W_DEC, r"al mes 12 es de " + SD + r" puntos",
           lambda con: 100 * con.execute("select exceso from mart_decision_perdida").fetchone()[0], 0.05, "{:.1f}"),
        _c("dec_grilla_60_10_12@wiki", W_DEC, r"\| 60 \| 10% \| 12 \| " + N + r" \|", _grilla(60, 0.10, 12),
           0.5),
        _c("dec_grilla_80_15_24@wiki", W_DEC, r"\| 80 \| 15% \| 24 \| " + N + r" \|", _grilla(80, 0.15, 24),
           0.5),
        _c("dec_grilla_cota_60@wiki", W_DEC, r"Sobre la cota de pérdida[\s\S]*?\| 60 \| " + N + r" \|",
           _grilla_cota(60), 0.5),
    ]
    return cl


W_HIJO = "wiki/hallazgos/hijo.md"
NG = r"-?[\d.]+(?:,\d+)?"   # signed number with thousands dots and optional decimal comma


def _hc(modelo: str, termino: str, col: str, factor: float = 1.0) -> Callable:
    return lambda con: factor * con.execute(f"select {col} from mart_hijo_coef where modelo = '{modelo}' and termino = '{termino}'").fetchone()[0]


def _hg(expo: str, grupo: int, col: str) -> Callable:
    return lambda con: con.execute(f"select {col} from mart_hijo_grupos where exposicion = '{expo}' and grupo = {grupo}").fetchone()[0]


def _he(variable: str, col: str, factor: float = 1.0) -> Callable:
    return lambda con: factor * con.execute(f"select {col} from mart_hijo_equilibrio where variable = '{variable}'").fetchone()[0]


def _fr(idx: int, *lit: str) -> str:
    """Pattern of a sentence made of literals with a number between each pair; the number at position idx is captured."""
    out = re.escape(lit[0])
    for k, s in enumerate(lit[1:]):
        out += (f"({NG})" if k == idx else f"(?:{NG})") + re.escape(s)
    return out


W_HCEL = "wiki/hallazgos/hijo_celdas.md"


def _claims_hijo_celdas() -> list[Claim]:
    """Numbers of the summary of the child side within 2 km cells: main coefficient and CI, control, bound, cells and descriptive rows."""
    def hc(modelo: str, termino: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(
            f"select {col} from mart_hijo_celdas_coef where modelo = '{modelo}' and termino = '{termino}'").fetchone()[0]

    def rs(col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from mart_hijo_celdas_resumen").fetchone()[0]

    cl = []

    def frase(clave, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"hcel_{clave}_{k}@wiki", W_HCEL, _fr(k, *lits), fn, tol, fmt))

    P, C, C2 = ("principal", "muy_depletado"), ("control_negativo", "muy_depletado"), ("control_negativo", "poco_depletado")
    K5, K1 = ("celdas_5_km", "muy_depletado"), ("celdas_1_km", "muy_depletado")
    d1, n0 = "{:.1f}", "{:,.0f}"
    frase("principal", ["Muy depletado contra virgen, dentro de celdas de 2 km: ", " bbl por metro de rama (IC 95%: ", " a ", "), o sea ",
                        "% del rendimiento virgen (IC 95%: ", "% a ", "%), sobre ", " hijos en ", " celdas."],
          [hc(*P, "coef_bbl_m"), hc(*P, "ic_bajo"), hc(*P, "ic_alto"), hc(*P, "pct_del_virgen"), hc(*P, "pct_ic_bajo"),
           hc(*P, "pct_ic_alto"), hc(*P, "n"), hc(*P, "conglomerados")], [0.05] * 6 + [0, 0], [d1] * 6 + [n0] * 2)
    frase("virgen", ["Rendimiento de los hijos en zona virgen a 12 meses: mediana de ", " bbl por metro de rama."],
          [rs("virgen_mediana_bbl_m")], [0.05], [d1])
    frase("control", ["Control negativo, muy depletado contra virgen: ", " bbl por metro de rama (IC 95%: ", " a ", ")."],
          [hc(*C, "coef_bbl_m"), hc(*C, "ic_bajo"), hc(*C, "ic_alto")], [0.05] * 3, [d1] * 3)
    frase("control2", ["El del grupo poco depletado, que la regla no usa, da ", " (IC 95%: ", " a ", ")"],
          [hc(*C2, "coef_bbl_m"), hc(*C2, "ic_bajo"), hc(*C2, "ic_alto")], [0.05] * 3, [d1] * 3)
    frase("cota", ["Cota superior de la pérdida del hijo muy depletado: ", " bbl por metro de rama, o ", "% del rendimiento virgen."],
          [rs("cota_bbl_m", -1), rs("cota_pct", -1)], [0.05] * 2, [d1] * 2)
    frase("celdas", ["Celdas que comparan: ", " celdas tienen a la vez hijos virgen y muy depletados, con ", " de los ", " hijos;"],
          [rs("celdas_informativas"), rs("hijos_en_informativas"), rs("hijos")], [0] * 3, [n0] * 3)
    frase("tamanos", ["Con celdas de 5 km (descriptivo) el muy depletado da ", " bbl por metro (IC 95%: ", " a ",
                      "); con celdas de 1 km, ", " (IC 95%: ", " a ", ")."],
          [hc(*K5, "coef_bbl_m"), hc(*K5, "ic_bajo"), hc(*K5, "ic_alto"), hc(*K1, "coef_bbl_m"), hc(*K1, "ic_bajo"), hc(*K1, "ic_alto")],
          [0.05] * 6, [d1] * 6)
    cl.append(_c("hcel_readme_punto@wiki", W_LIM, r"dentro de cuadrados de 2 km el hijo muy depletado da " + SD + r"% del virgen",
                 hc(*P, "pct_del_virgen"), 0.05, d1))
    cl.append(_c("hcel_readme_bajo@wiki", W_LIM, r"dentro de cuadrados de 2 km el hijo muy depletado da -?\d+,\d+% del virgen \(IC 95%: " + SD + r"%",
                 hc(*P, "pct_ic_bajo"), 0.05, d1))
    cl.append(_c("hcel_readme_alto@wiki", W_LIM, r"dentro de cuadrados de 2 km el hijo muy depletado da -?\d+,\d+% del virgen \(IC 95%: -?\d+,\d+% a " + SD + r"%",
                 hc(*P, "pct_ic_alto"), 0.05, d1))
    return cl


W_GAS = "wiki/hallazgos/gas.md"


def _claims_gas() -> list[Claim]:
    """Numbers of the summary of the gas window parent study: month 1 and 6 gaps with CIs, pretrend, bound, deferred gas and GOR."""
    def gb(res: str, k: int, col: str) -> Callable:
        return lambda con: 100 * con.execute(f"select {col} from mart_gas where resultado = '{res}' and k = {k}").fetchone()[0]

    def gn(res: str, k: int, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_gas where resultado = '{res}' and k = {k}").fetchone()[0]

    def tab(tabla: str, k: int, col: str) -> Callable:
        return lambda con: 100 * con.execute(f"select {col} from {tabla} where k = {k}").fetchone()[0]

    def vd(col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from mart_gas_veredicto").fetchone()[0]

    cl = []

    def frase(clave, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"gas_{clave}_{k}@wiki", W_GAS, _fr(k, *lits), fn, tol, fmt))

    d1, d2, n0 = "{:.1f}", "{:.2f}", "{:,.0f}"
    pre, gor = "mart_gas_pretendencia", "mart_gas_gor"
    frase("mes1", ["Brecha del gas del mes 1 (volumen, por día calendario): ", " puntos de índice (IC 95% por bloques de 5 km: ", " a ",
                   "; por pads hijo: ", " a ", "), con ", " eventos cercanos y ", " controles en ", " bloques de 5 km."],
          [gb("V", 1, "brecha"), gb("V", 1, "ic_bajo_5km"), gb("V", 1, "ic_alto_5km"), gb("V", 1, "ic_bajo_pad"), gb("V", 1, "ic_alto_pad"),
           gn("V", 1, "n_near"), gn("V", 1, "n_ctrl"), gn("V", 1, "bloques_5km")], [0.05] * 5 + [0] * 3, [d1] * 5 + [n0] * 3)
    frase("pre", ["ya es de ", " puntos en el mes -1, antes de la fractura (IC 95% por pads: ", " a ", "), y llega a ", " en el mes 1."],
          [tab(pre, -1, "brecha"), tab(pre, -1, "ic_bajo"), tab(pre, -1, "ic_alto"), tab(pre, 1, "brecha")], [0.05] * 4, [d1] * 4)
    frase("cota", ["Cota superior de la caída del mes 1 compatible con el dato público: ", " puntos de índice."],
          [vd("cota_mes1", -100)], [0.05], [d1])
    frase("mes6", ["- Mes 6: ", " puntos (IC 95% por bloques de 5 km: ", " a ", "):"],
          [gb("V", 6, "brecha"), gb("V", 6, "ic_bajo_5km"), gb("V", 6, "ic_alto_5km")], [0.05] * 3, [d1] * 3)
    frase("efectivo", ["Por día efectivo la brecha del mes 1 es ", " puntos (IC 95% por bloques de 5 km: ", " a ", ")."],
          [gb("E", 1, "brecha"), gb("E", 1, "ic_bajo_5km"), gb("E", 1, "ic_alto_5km")], [0.05] * 3, [d1] * 3)
    frase("diferido", ["contra el índice mediano de los controles: mediana de ", " millones de m3 (", " eventos con los 7 meses)."],
          [vd("diferido_mediana", 1 / 1000), vd("diferido_eventos")], [0.005, 0], [d2, n0])
    frase("gor", ["la brecha del índice de la relación gas petróleo es ", " puntos al mes 1 (IC 95% por pads: ", " a ", ") y ",
                  " al mes 6 (IC 95%: ", " a ", ")."],
          [tab(gor, 1, "brecha"), tab(gor, 1, "ic_bajo"), tab(gor, 1, "ic_alto"), tab(gor, 6, "brecha"), tab(gor, 6, "ic_bajo"),
           tab(gor, 6, "ic_alto")], [0.05] * 6, [d1] * 6)
    ic = r"IC 95% por bloques de 5 km de la brecha de gas: "
    cl += [_c("gas_readme_brecha@readme", R, r"el padre gasífero cercano da " + SD + r" puntos de gas al mes 1", gb("V", 1, "brecha"), 0.05, d1),
           _c("gas_readme_bajo@readme", R, ic + SD + r" a", gb("V", 1, "ic_bajo_5km"), 0.05, d1),
           _c("gas_readme_alto@readme", R, ic + r"-?\d+,\d+ a " + SD, gb("V", 1, "ic_alto_5km"), 0.05, d1),
           _c("gas_readme_pre@readme", R, r"ya va " + SD + r" puntos abajo en el mes -1", tab(pre, -1, "brecha"), 0.05, d1),
           _c("gas_readme_efectivo@readme", R, r"por día efectivo la brecha es " + SD, gb("E", 1, "brecha"), 0.05, d1)]
    return cl


W_PROS = "wiki/hallazgos/prospectiva.md"


def _cong(pred: str, campo: str, factor: float = 1.0) -> Callable:
    """Number of the frozen prospective file (verified against its sha256 on every read; the warehouse is not used)."""
    def f(con):
        from pipeline import prospectiva
        return factor * prospectiva.leer_congelada()[pred][campo]
    return f


def _claims_prospectiva() -> list[Claim]:
    """Frozen numbers of the prospective test on its page and in the README row: they must not move after the freeze."""
    cl = []

    def frase(clave, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"pros_{clave}_{k}@wiki", W_PROS, _fr(k, *lits), fn, tol, fmt, wh=False))

    d1, n0 = "{:.1f}", "{:,.0f}"
    frase("p1", ["- P1: brecha del mes 1 de ", " puntos de índice, con intervalo predicho de ", " a ", " (IC 95%"],
          [_cong("p1", "prediccion", 100), _cong("p1", "intervalo_bajo", 100), _cong("p1", "intervalo_alto", 100)], [0.05] * 3, [d1] * 3)
    frase("p1n", ["al congelar se conocían ", " cercanos y ", " controles.\n- P2"],
          [_cong("p1", "conocidos_cercanos"), _cong("p1", "conocidos_controles")], [0, 0], [n0] * 2)
    frase("p2", ["- P2: brecha del mes 6 a menos de ", " puntos de cero (", " puntos con los datos hasta"],
          [_cong("p2", "umbral", 100), _cong("p2", "prediccion", 100)], [0.05] * 2, [d1] * 2)
    frase("p2n", ["desde 2026-04; al congelar se conocían ", " cercanos y ", " controles."],
          [_cong("p2", "conocidos_cercanos"), _cong("p2", "conocidos_controles")], [0, 0], [n0] * 2)
    pre = r"Prueba prospectiva \(`wiki/hallazgos/prospectiva.md`\) \| congelada el 2026-11-18 con los datos hasta 2026-09: brecha del mes 1 de "
    # Los _bis no llevan el texto entre comillas inversas: numeros_sin_fijar lo borra, y sin ellos las cifras de la fila quedarian sueltas.
    cl += [_c("pros_readme_pred@readme", R, pre + SD, _cong("p1", "prediccion", 100), 0.05, d1, wh=False),
           _c("pros_readme_pred_bis@readme", R, r"brecha del mes 1 de " + SD + r" puntos \(intervalo predicho",
              _cong("p1", "prediccion", 100), 0.05, d1, wh=False),
           _c("pros_readme_bajo@readme", R, pre + r"-?\d+,\d+ puntos \(intervalo predicho " + SD, _cong("p1", "intervalo_bajo", 100), 0.05, d1,
              wh=False),
           _c("pros_readme_bajo_bis@readme", R, r"intervalo predicho " + SD + r" a", _cong("p1", "intervalo_bajo", 100), 0.05, d1,
              wh=False),
           _c("pros_readme_alto@readme", R, pre + r"-?\d+,\d+ puntos \(intervalo predicho -?\d+,\d+ a " + SD, _cong("p1", "intervalo_alto", 100),
              0.05, d1, wh=False),
           _c("pros_readme_alto_bis@readme", R, r"intervalo predicho -?\d+,\d+ a " + SD, _cong("p1", "intervalo_alto", 100),
              0.05, d1, wh=False)]
    return cl


W_LIT = "wiki/hallazgos/literatura.md"


def _quiebre(banda: str, col: str) -> Callable:
    """Descriptive share of events with mean index under 0.75 in months 0 and 1 (literature page, post hoc)."""
    def f(con):
        n, p = con.execute(
            "with e as (select padre, mes_frac, avg(indice) m from int_interferencia_mes where k in (0, 1) and banda = ? "
            "group by 1, 2 having count(*) = 2) select count(*), 100 * avg(case when m < 0.75 then 1.0 else 0 end) from e",
            [banda]).fetchone()
        return n if col == "n" else p
    return f


def _claims_literatura() -> list[Claim]:
    """Own numbers quoted on the hand-written literature page: oil gap, month-6 range, post hoc drop shares, child side and gas."""
    cl = []

    def frase(clave, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"lit_{clave}_{k}@wiki", W_LIT, _fr(k, *lits), fn, tol, fmt))

    def ani6(agg: str) -> Callable:
        return lambda con: 100 * con.execute(f"select {agg}(brecha) from mart_anillo where k = 6").fetchone()[0]

    def gb(res: str, k: int, col: str) -> Callable:
        return lambda con: 100 * con.execute(f"select {col} from mart_gas where resultado = '{res}' and k = {k}").fetchone()[0]

    def tab(tabla: str, k: int, col: str) -> Callable:
        return lambda con: 100 * con.execute(f"select {col} from {tabla} where k = {k}").fetchone()[0]

    def hc(col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_hijo_celdas_coef where modelo = 'principal' "
                                       "and termino = 'muy_depletado'").fetchone()[0]

    d1, n0 = "{:.1f}", "{:,.0f}"
    frase("petroleo", ["Padres a menos de 1 km: entre ", " y ", " puntos menos que controles de 2 a 5 km un mes después de la fractura del hijo (",
                       " eventos)"],
          [_pretrend_descontada("mart_placebo_pretrend"), _brecha_mes1, _eventos_cercanos], [0.5, 0.5, 0], [n0] * 3)
    frase("mes6", ["con los cuatro controles probados (de ", " a ", ")"], [ani6("max"), ani6("min")], [0.05] * 2, [d1] * 2)
    frase("quiebre", ["el ", "% de ", " eventos cercanos con los meses 0 y 1 tiene un índice medio menor que 0,75 en esos dos meses, contra el ",
                      "% de ", " eventos de control."],
          [_quiebre("cercano", "p"), _quiebre("cercano", "n"), _quiebre("control", "p"), _quiebre("control", "n")],
          [0.05, 0, 0.05, 0], [d1, n0, d1, n0])
    frase("hijo", ["mismo cuadrado de 2 km: ", "% del rendimiento virgen a 12 meses (IC 95%: ", "% a ", "%)."],
          [hc("pct_del_virgen"), hc("pct_ic_bajo"), hc("pct_ic_alto")], [0.05] * 3, [d1] * 3)
    frase("gas", ["Padres gasíferos a menos de 1 km: ", " puntos de gas al mes 1 (IC 95% por bloques de 5 km: ", " a ", "), pero ya ",
                  " en el mes -1, antes de la fractura; por día efectivo ", " puntos,"],
          [gb("V", 1, "brecha"), gb("V", 1, "ic_bajo_5km"), gb("V", 1, "ic_alto_5km"), tab("mart_gas_pretendencia", -1, "brecha"),
           gb("E", 1, "brecha")], [0.05] * 5, [d1] * 5)
    frase("gor", ["el GOR no muestra un cambio (IC que incluye cero): ", " puntos al mes 1 (IC 95% por pads: ", " a ", ")."],
          [tab("mart_gas_gor", 1, "brecha"), tab("mart_gas_gor", 1, "ic_bajo"), tab("mart_gas_gor", 1, "ic_alto")], [0.05] * 3, [d1] * 3)
    return cl


def _claims_hijo() -> list[Claim]:
    """Every number of the child-side page: summary bullets, the group table, the coefficient table, the balance table and the sample."""
    from pipeline import hijo as hj
    cl = []
    celda = lambda j: r"[^|]*\| " * j  # noqa: E731  (skips j table cells)

    def resumen(clave, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"hijo_resumen_{clave}_{k}@wiki", W_HIJO, _fr(k, *lits), fn, tol, fmt))

    P, C = ("principal", "muy_depletado"), ("control_negativo", "muy_depletado")
    d1 = "{:.1f}"
    cl += [
        _c("hijo_virgen_mediana@wiki", W_HIJO, _fr(0, "mediana de ", " bbl por metro de rama, sobre "), _hg("real", 1, "rend_12m_mediana_bbl_m"),
           0.05, d1),
        _c("hijo_virgen_hijos@wiki", W_HIJO, _fr(1, "mediana de ", " bbl por metro de rama, sobre ", " hijos de "), _hg("real", 1, "hijos"), 0),
        _c("hijo_virgen_pads@wiki", W_HIJO, _fr(2, "mediana de ", " bbl por metro de rama, sobre ", " hijos de ", " pads."),
           _hg("real", 1, "pads"), 0),
    ]
    resumen("principal", ["Muy depletado contra virgen: ", " bbl por metro de rama (IC 95%: ", " a ", "), o sea ",
                          "% del rendimiento virgen (IC 95%: ", "% a ", "%), sobre ", " hijos de ", " pads."],
            [_hc(*P, "coef_bbl_m"), _hc(*P, "ic_bajo"), _hc(*P, "ic_alto"), _hc(*P, "pct_del_virgen"), _hc(*P, "pct_ic_bajo"),
             _hc(*P, "pct_ic_alto"), _hc(*P, "n"), _hc(*P, "conglomerados")], [0.05] * 6 + [0, 0], [d1] * 6 + ["{:,.0f}"] * 2)
    resumen("control", ["Control negativo, muy depletado contra virgen: ", " bbl por metro de rama (IC 95%: ", " a ", "), o sea ",
                        "% del rendimiento virgen (IC 95%: ", "% a ", "%)."],
            [_hc(*C, "coef_bbl_m"), _hc(*C, "ic_bajo"), _hc(*C, "ic_alto"), _hc(*C, "pct_del_virgen"), _hc(*C, "pct_ic_bajo"),
             _hc(*C, "pct_ic_alto")], [0.05] * 6, [d1] * 6)
    K, KC = ("continua", hj.TERMINO_CONTINUA), ("continua_control_negativo", hj.TERMINO_CONTINUA)
    resumen("continua", ["Exposición continua (descriptivo): ", " bbl por metro de rama por cada 100 bbl por metro de exposición (IC 95%: ",
                         " a ", "); con la exposición del control negativo: ", " (IC 95%: ", " a ", ")."],
            [_hc(*K, "coef_bbl_m"), _hc(*K, "ic_bajo"), _hc(*K, "ic_alto"), _hc(*KC, "coef_bbl_m"), _hc(*KC, "ic_bajo"), _hc(*KC, "ic_alto")],
            [0.005] * 6, ["{:.2f}"] * 6)
    Y, RS = ("principal_ypf", "muy_depletado"), ("principal_resto", "muy_depletado")
    resumen("operadora", ["Por operadora (descriptivo, muy depletado contra virgen): YPF ", " bbl por metro (IC 95%: ", " a ",
                          "); resto ", " bbl por metro (IC 95%: ", " a ", ")."],
            [_hc(*Y, "coef_bbl_m"), _hc(*Y, "ic_bajo"), _hc(*Y, "ic_alto"), _hc(*RS, "coef_bbl_m"), _hc(*RS, "ic_bajo"), _hc(*RS, "ic_alto")],
            [0.05] * 6, [d1] * 6)
    resumen("equilibrio", ["el grupo muy depletado tiene ", " pozos de shale a menos de 5 km contra ", " del grupo virgen (p dentro de celdas ",
                           "), y ", " m de rama contra ", " m (p ", ")"],
            [_he("pozos_a_5_km", "grupo3"), _he("pozos_a_5_km", "grupo1"), _he("pozos_a_5_km", "p"), _he("rama_horizontal_m", "grupo3"),
             _he("rama_horizontal_m", "grupo1"), _he("rama_horizontal_m", "p")], [0.5, 0.5, 0.0005, 0.5, 0.5, 0.0005],
            ["{:,.0f}", "{:,.0f}", "{:.3f}", "{:,.0f}", "{:,.0f}", "{:.3f}"])
    # rule constants and the group cuts
    cl += [
        _c("hijo_regla_hijos_min@wiki", W_HIJO, _fr(0, "Sin muestra: menos de ", " hijos o de ", " pads en el grupo virgen"),
           lambda _: hj.MIN_HIJOS_GRUPO, 0, wh=False),
        _c("hijo_regla_pads_grupo@wiki", W_HIJO, _fr(1, "Sin muestra: menos de ", " hijos o de ", " pads en el grupo virgen"),
           lambda _: hj.MIN_PADS_GRUPO, 0, wh=False),
        _c("hijo_regla_pads_min@wiki", W_HIJO, _fr(0, "muy depletado, o menos de ", " pads."), lambda _: hj.MIN_PADS, 0, wh=False),
        _c("hijo_regla_umbral@wiki", W_HIJO, _fr(0, "el punto es menor que ", "% del rendimiento virgen y el control negativo es nulo (su"),
           lambda _: 100 * hj.UMBRAL_FALSA, 0, wh=False),
        _c("hijo_corte_poco@wiki", W_HIJO, _fr(0, "El grupo poco depletado llega hasta ", " bbl por metro de exposición y el muy"),
           _hg("real", 2, "expo_max_bbl_m"), 0.5),
        _c("hijo_corte_muy@wiki", W_HIJO, _fr(0, "y el muy depletado empieza en ", "; en el control"), _hg("real", 3, "expo_min_bbl_m"), 0.5),
    ]
    # group table
    for expo, rot in (("real", "Exposición real"), ("control", "Exposición de control negativo")):
        for b, et in ((1, "virgen"), (2, "poco depletado"), (3, "muy depletado")):
            f = r"\| " + rot + r" \| " + et + r" \| "
            for j, (col, pat, tol, fmt) in enumerate([("hijos", N, 0, "{:,.0f}"), ("pads", N, 0, "{:,.0f}"), ("expo_min_bbl_m", N, 0.5, "{:,.0f}"),
                                                      ("expo_max_bbl_m", N, 0.5, "{:,.0f}"), ("rend_12m_mediana_bbl_m", SD, 0.05, d1),
                                                      ("rend_12m_media_bbl_m", SD, 0.05, d1)]):
                cl.append(_c(f"hijo_grupos_{expo}{b}_{col}@wiki", W_HIJO, f + celda(j) + pat, _hg(expo, b, col), tol, fmt))
    # coefficient table
    for (modelo, termino), (rot_m, rot_t) in {
            ("principal", "poco_depletado"): ("Principal", "poco depletado"), P: ("Principal", "muy depletado"),
            ("control_negativo", "poco_depletado"): ("Control negativo", "poco depletado"), C: ("Control negativo", "muy depletado"),
            K: ("Continua", "por 100 bbl/m"), KC: ("Continua, control negativo", "por 100 bbl/m"),
            ("principal_ypf", "poco_depletado"): ("Solo YPF", "poco depletado"), Y: ("Solo YPF", "muy depletado"),
            ("principal_resto", "poco_depletado"): ("Resto", "poco depletado"), RS: ("Resto", "muy depletado")}.items():
        f = r"\| " + rot_m + r" \| " + rot_t + r" \| "
        k = f"{modelo}_{termino}"
        cl += [
            _c(f"hijo_coef_{k}_coef@wiki", W_HIJO, f + SD, _hc(modelo, termino, "coef_bbl_m"), 0.05, d1),
            _c(f"hijo_coef_{k}_pct@wiki", W_HIJO, f + celda(1) + SD, _hc(modelo, termino, "pct_del_virgen"), 0.05, d1),
            _c(f"hijo_coef_{k}_ic_bajo@wiki", W_HIJO, f + celda(2) + SD + r" a", _hc(modelo, termino, "ic_bajo"), 0.05, d1),
            _c(f"hijo_coef_{k}_ic_alto@wiki", W_HIJO, f + celda(2) + r"-?\d+,\d+ a " + SD, _hc(modelo, termino, "ic_alto"), 0.05, d1),
            _c(f"hijo_coef_{k}_n@wiki", W_HIJO, f + celda(3) + N, _hc(modelo, termino, "n"), 0),
            _c(f"hijo_coef_{k}_pads@wiki", W_HIJO, f + celda(4) + N, _hc(modelo, termino, "conglomerados"), 0),
            _c(f"hijo_coef_{k}_p@wiki", W_HIJO, f + celda(5) + SD, _hc(modelo, termino, "p"), 0.0005, "{:.3f}"),
        ]
    # balance table: variable, label, decimals, factor, whether the within-cell p exists
    for var, rot, dec, fac, p_celdas in [("rama_horizontal_m", "Rama horizontal \\(m\\)", 0, 1.0, True), ("etapas", "Etapas", 1, 1.0, True),
                                         ("arena_tn_por_m", "Arena por metro \\(tn/m\\)", 2, 1.0, True),
                                         ("cohorte", "Cohorte \\(año del primer petróleo\\)", 2, 1.0, False),
                                         ("ypf", "YPF \\(% de los hijos\\)", 1, 100.0, False),
                                         ("latitud", "Latitud \\(grados\\)", 3, 1.0, True), ("longitud", "Longitud \\(grados\\)", 3, 1.0, True),
                                         ("pozos_a_5_km", "Pozos de shale a menos de 5 km", 0, 1.0, True)]:
        f = r"\| " + rot + r" \| "
        fm, tol = "{:,.%df}" % dec, 0.5 * 10 ** -dec
        cl += [_c(f"hijo_eq_{var}_g{g}@wiki", W_HIJO, f + celda(g - 1) + f"({NG})", _he(var, f"grupo{g}", fac), tol,
                  fm if var != "cohorte" else "{:.2f}") for g in (1, 2, 3)]
        if p_celdas:
            cl.append(_c(f"hijo_eq_{var}_p@wiki", W_HIJO, f + celda(3) + SD, _he(var, "p"), 0.0005, "{:.3f}"))
        cl.append(_c(f"hijo_eq_{var}_p_sin@wiki", W_HIJO, f + celda(4) + SD, _he(var, "p_sin_celdas"), 0.0005, "{:.3f}"))
    # sample
    for paso in range(1, 6):
        cl.append(_c(f"hijo_muestra_{paso}@wiki", W_HIJO, rf"Paso {paso}, [^:]*: " + N + " hijos",
                     lambda con, paso=paso: con.execute(f"select hijos from mart_hijo_muestra where paso = {paso}").fetchone()[0], 0))
    # README row, limits and case study paragraph
    pr = r"muy depletado contra virgen: "
    cl += [
        _c("hijo_readme_coef@readme", R, pr + SD + r" bbl por metro de rama", _hc(*P, "coef_bbl_m"), 0.05, d1),
        _c("hijo_readme_pct@readme", R, r"bbl por metro de rama \(" + SD + r"% del rendimiento virgen\)", _hc(*P, "pct_del_virgen"), 0.05, d1),
        _c("hijo_readme_ic_bajo@readme", R, r"IC 95%: " + SD + r" a -?\d+,\d+; el control negativo da", _hc(*P, "ic_bajo"), 0.05, d1),
        _c("hijo_readme_ic_alto@readme", R, r"IC 95%: -?\d+,\d+ a " + SD + r"; el control negativo da", _hc(*P, "ic_alto"), 0.05, d1),
        _c("hijo_readme_ctrl@readme", R, r"el control negativo da " + SD + r" \(IC", _hc(*C, "coef_bbl_m"), 0.05, d1),
        _c("hijo_readme_ctrl_bajo@readme", R, r"el control negativo da -?\d+,\d+ \(IC " + SD + r" a", _hc(*C, "ic_bajo"), 0.05, d1),
        _c("hijo_readme_ctrl_alto@readme", R, r"el control negativo da -?\d+,\d+ \(IC -?\d+,\d+ a " + SD + r"\)", _hc(*C, "ic_alto"), 0.05, d1),
        _c("hijo_caso_corte@caso", CASO, r"Un hijo con más de " + N + r" bbl por metro de rama de petróleo ya producido",
           _hg("real", 2, "expo_max_bbl_m"), 0.5),
        _c("hijo_caso_coef@caso", CASO, r"a menos de 1 km difiere de uno en zona virgen en " + SD + r" bbl por metro a 12 meses", _hc(*P, "coef_bbl_m"), 0.05, d1),
        _c("hijo_caso_ic_bajo@caso", CASO, r"a 12 meses \(IC 95%: " + SD + r" a -?\d+,\d+; la mediana virgen", _hc(*P, "ic_bajo"), 0.05, d1),
        _c("hijo_caso_ic_alto@caso", CASO, r"a 12 meses \(IC 95%: -?\d+,\d+ a " + SD + r"; la mediana virgen", _hc(*P, "ic_alto"), 0.05, d1),
        _c("hijo_caso_virgen@caso", CASO, r"la mediana virgen es de " + SD + r"\)", _hg("real", 1, "rend_12m_mediana_bbl_m"), 0.05, d1),
        _c("hijo_caso_ctrl@caso", CASO, r"del hijo, da " + SD + r" \(IC", _hc(*C, "coef_bbl_m"), 0.05, d1),
        _c("hijo_caso_ctrl_bajo@caso", CASO, r"del hijo, da -?\d+,\d+ \(IC " + SD + r" a", _hc(*C, "ic_bajo"), 0.05, d1),
        _c("hijo_caso_ctrl_alto@caso", CASO, r"del hijo, da -?\d+,\d+ \(IC -?\d+,\d+ a " + SD + r"\)", _hc(*C, "ic_alto"), 0.05, d1),
    ]
    return cl


W_BLQ = "wiki/hallazgos/bloques.md"
B_HEAD, B_DESC, B_LIMP, B_PEND, B_DIAS, B_TASA = ("brecha_mes1_base_original", "brecha_mes1_descontada", "brecha_base_limpia",
                                                  "sincronia_pendiente", "parte_dias", "parte_tasa")
B_FACTOR = {B_HEAD: 100, B_DESC: 100, B_LIMP: 100, B_PEND: 10, B_DIAS: 100, B_TASA: 100}
B_FILAS = ([(B_HEAD, 1, "mediana"), (B_DESC, 1, "mediana")] + [(B_LIMP, k, "mediana") for k in range(-3, 4)]
           + [(B_PEND, 0, "pendiente"), (B_PEND, -1, "pendiente")]
           + [(m, 1, v) for m in (B_DIAS, B_TASA) for v in ("con_cerrados", "sin_cerrados")])
_TIPO = {"n": r"-?\d+,\d+", "i": r"[\d.]+"}


def _blq(metrica: str, k: int, col: str, factor: float = 1.0, est: str | None = None) -> Callable:
    """A column of mart_bloques (the 5 km / 2 km block intervals of pipeline.bloques) for one row, times factor."""
    def f(con):
        q = f"select {col} from mart_bloques where metrica = ? and k = ?" + (" and estimador = ?" if est else "")
        return factor * con.execute(q, [metrica, k] + ([est] if est else [])).fetchone()[0]
    return f


def _plantilla(texto: str, objetivo: str) -> str:
    """Regex of a sentence with slots <nombre:tipo> (n = signed decimal, i = integer): only the target slot is a capture group."""
    partes = re.split(r"<(\w+):(\w)>", texto)
    out = []
    for j in range(0, len(partes) - 1, 3):
        out.append(re.escape(partes[j]))
        rx = _TIPO[partes[j + 2]]
        out.append("(" + rx + ")" if partes[j + 1] == objetivo else rx)
    out.append(re.escape(partes[-1]))
    return "".join(out)


def _n_pruebas(parte: str) -> Callable:
    """Distinct statistical tests of the project: ledger hypotheses, robustness subsets, decomposition intervals, other block rows."""
    def f(con):
        hip = _hipotesis(con)
        rob = _rob_n()(con)
        desc = sum(con.execute(f"select count(*) from {t}").fetchone()[0]
                   for t in ("mart_descomposicion_k", "mart_descomposicion_aditiva", "mart_descomposicion_distancia"))
        blq = con.execute("select count(*) from mart_bloques").fetchone()[0] - 2
        hij = con.execute("select count(*) from mart_hijo_coef").fetchone()[0] - 1   # el lado del hijo, sin la fila que es la hipotesis
        return {"hip": hip, "rob": rob, "desc": desc, "hij": hij, "blq": blq, "total": hip + rob + desc + hij + blq}[parte]
    return f


def _claims_bloques() -> list[Claim]:
    """Every number of the spatial-blocks page: the summary bullets, both tables (15 rows each) and the project test count."""
    cl = []
    n, i = _TIPO["n"], _TIPO["i"]
    cols1 = {"est": "estimacion", "plo": "ic_bajo_pad", "phi": "ic_alto_pad", "l2": "ic_bajo_2km", "h2": "ic_alto_2km",
             "l5": "ic_bajo_5km", "h5": "ic_alto_5km"}
    seq = [("est",), ("plo", "phi"), ("l2", "h2"), ("l5", "h5")]
    cols2 = {"pads": "pads", "b2": "bloques_2km", "b5": "bloques_5km", "r2": "ratio_2km", "r5": "ratio_5km"}
    t2 = list(cols2)
    for m, k, e in B_FILAS:
        pre = r"\| `" + m + r"` \| " + str(k) + r" \| " + e + r" \| "
        for nom, col in cols1.items():
            celdas = [" a ".join(("(" + n + ")" if c == nom else n) for c in cel) for cel in seq]
            cl.append(_c(f"blq_{m}_k{k}_{e}_{nom}@wiki", W_BLQ, pre + r" \| ".join(celdas) + r" \|",
                         _blq(m, k, col, B_FACTOR[m], e), 0.05, "{:.1f}"))
        for nom, col in cols2.items():
            toks = [("(" + (i if c in t2[:3] else n) + ")" if c == nom else (i if c in t2[:3] else n)) for c in t2]
            ratio = nom in ("r2", "r5")
            cl.append(_c(f"blq_{m}_k{k}_{e}_{nom}@wiki", W_BLQ, pre + r" \| ".join(toks) + r" \|", _blq(m, k, col, 1, e),
                         0.005 if ratio else 0, "{:.2f}" if ratio else "{:.0f}"))

    def resumen(id_, texto, objetivo, fn, tol=0.05, fm="{:.1f}"):
        cl.append(_c(f"blq_resumen_{id_}@wiki", W_BLQ, _plantilla(texto, objetivo), fn, tol, fm))

    base = ("base de los meses -3 a -1: <est:n> puntos. IC 95% por pads: <plo:n> a <phi:n>; por bloques de 2 km: <l2:n> a <h2:n> "
            "(<b2:i> bloques); por bloques de 5 km: <l5:n> a <h5:n> (<b5:i> bloques).")
    for nom, col, f, tol, fm in (("est", "estimacion", 100, 0.05, "{:.1f}"), ("plo", "ic_bajo_pad", 100, 0.05, "{:.1f}"),
                                 ("phi", "ic_alto_pad", 100, 0.05, "{:.1f}"), ("l2", "ic_bajo_2km", 100, 0.05, "{:.1f}"),
                                 ("h2", "ic_alto_2km", 100, 0.05, "{:.1f}"), ("b2", "bloques_2km", 1, 0, "{:.0f}"),
                                 ("l5", "ic_bajo_5km", 100, 0.05, "{:.1f}"), ("h5", "ic_alto_5km", 100, 0.05, "{:.1f}"),
                                 ("b5", "bloques_5km", 1, 0, "{:.0f}")):
        resumen("brecha_" + nom, base, nom, _blq(B_HEAD, 1, col, f), tol, fm)
    pend = ("Pendiente del mes 0: <est:n> puntos por cada 0,1 de f0. IC 95% por pads: <plo:n> a <phi:n>; por bloques de 2 km: "
            "<l2:n> a <h2:n>; por bloques de 5 km: <l5:n> a <h5:n> (<b5:i> bloques). Mes -1, por bloques de 5 km: <m1l:n> a <m1h:n>.")
    for nom, k, col, f, tol, fm in (("est", 0, "estimacion", 10, 0.05, "{:.1f}"), ("plo", 0, "ic_bajo_pad", 10, 0.05, "{:.1f}"),
                                    ("phi", 0, "ic_alto_pad", 10, 0.05, "{:.1f}"), ("l2", 0, "ic_bajo_2km", 10, 0.05, "{:.1f}"),
                                    ("h2", 0, "ic_alto_2km", 10, 0.05, "{:.1f}"), ("l5", 0, "ic_bajo_5km", 10, 0.05, "{:.1f}"),
                                    ("h5", 0, "ic_alto_5km", 10, 0.05, "{:.1f}"), ("b5", 0, "bloques_5km", 1, 0, "{:.0f}"),
                                    ("m1l", -1, "ic_bajo_5km", 10, 0.05, "{:.1f}"), ("m1h", -1, "ic_alto_5km", 10, 0.05, "{:.1f}")):
        resumen("pend_" + nom, pend, nom, _blq(B_PEND, k, col, f), tol, fm)
    partes = ("los días explican el <est:n>% de la brecha del volumen (IC 95% por bloques de 5 km: <lo:n> a <hi:n>) y el caudal por día "
              "el <t:n>% (<tlo:n> a <thi:n>).")
    for nom, m, col in (("est", B_DIAS, "estimacion"), ("lo", B_DIAS, "ic_bajo_5km"), ("hi", B_DIAS, "ic_alto_5km"),
                        ("t", B_TASA, "estimacion"), ("tlo", B_TASA, "ic_bajo_5km"), ("thi", B_TASA, "ic_alto_5km")):
        resumen("partes_" + nom, partes, nom, _blq(m, 1, col, 100, "con_cerrados"))
    anchos = "de <min:n> a <max:n> veces en las <nf:i> filas."
    resumen("ancho_min", anchos, "min", lambda con: con.execute("select min(ratio_5km) from mart_bloques").fetchone()[0], 0.005, "{:.2f}")
    resumen("ancho_max", anchos, "max", lambda con: con.execute("select max(ratio_5km) from mart_bloques").fetchone()[0], 0.005, "{:.2f}")
    resumen("ancho_filas", anchos, "nf", lambda con: con.execute("select count(*) from mart_bloques").fetchone()[0], 0, "{:.0f}")
    total = ("Pruebas estadísticas corridas en el proyecto: <total:i> (<hip:i> hipótesis del libro, <rob:i> subconjuntos de robustez, "
             "<desc:i> intervalos de la descomposición, <hij:i> intervalos descriptivos del lado del hijo y <blq:i> intervalos por bloques")
    caso_total = ("En total son <total:i> pruebas estadísticas: <hip:i> hipótesis, <rob:i> subconjuntos de robustez, "
                  "<desc:i> intervalos de la descomposición, <hij:i> intervalos descriptivos del lado del hijo y <blq:i> intervalos por bloques")
    for fichero, plantilla, tag in ((W_BLQ, total, "wiki"), (CASO, caso_total, "caso")):
        for nom in ("total", "hip", "rob", "desc", "hij", "blq"):
            cl.append(_c(f"blq_pruebas_{nom}@{tag}", fichero, _plantilla(plantilla, nom), _n_pruebas(nom), 0, "{:.0f}"))
    # README and case study text that depends on the block intervals
    cl += [
        _c("blq_readme_bloques@wiki", W_LIM, r"con bloques espaciales de 5 km \((\d+) bloques\)", _blq(B_HEAD, 1, "bloques_5km"), 0),
        _c("blq_readme_ancho@wiki", W_LIM, r"es (\d+,\d+) veces más ancho y ningún veredicto cambia", _blq(B_HEAD, 1, "ratio_5km"), 0.005,
           "{:.2f}"),
    ]
    caso = ("El IC 95% por bloques espaciales de 5 km (<b5:i> bloques) de la brecha de <est:n> va de <l5:n> a <h5:n> puntos "
            "(por pads era <plo:n> a <phi:n>)")
    for nom, col, f, tol, fm in (("b5", "bloques_5km", 1, 0, "{:.0f}"), ("est", "estimacion", -100, 0.05, "{:.1f}"),
                                 ("l5", "ic_bajo_5km", 100, 0.05, "{:.1f}"), ("h5", "ic_alto_5km", 100, 0.05, "{:.1f}"),
                                 ("plo", "ic_bajo_pad", 100, 0.05, "{:.1f}"), ("phi", "ic_alto_pad", 100, 0.05, "{:.1f}")):
        cl.append(_c(f"blq_caso_{nom}@caso", CASO, _plantilla(caso, nom), _blq(B_HEAD, 1, col, f), tol, fm))
    return cl


W_INY = "wiki/hallazgos/inyeccion.md"
PC = r"(-?\d+)%"   # whole percent, signed


def _iny(esc: str, tam: int, medida: str, col: str, factor: float = 1.0) -> Callable:
    return lambda con: factor * con.execute(
        f"select {col} from mart_inyeccion where escenario = ? and tamano = ? and medida = ?", [esc, tam, medida]).fetchone()[0]


def _i50(esc: str, tam: int, medida: str, col: str, factor: float = 1.0) -> Callable:
    """A value of the saved 50-world run (docs/inyeccion_50_mundos.txt), no warehouse needed."""
    from pipeline import inyeccion
    return lambda _con: factor * float(inyeccion.corrida_50()[(esc, tam, medida)][col])


def _iny_k(esc: str, tam: int, medida: str) -> Callable:
    """Number of worlds whose CI excludes zero (fraction times worlds)."""
    return lambda con: float(round(_iny(esc, tam, medida, "ic_excluye_cero_frac")(con) * _iny(esc, tam, medida, "mundos")(con)))


def _iny_exacto(extremo: int) -> Callable:
    """Exact 95% interval of the false positive rate (percent): 0 lower end, 1 upper end."""
    from pipeline import inyeccion
    return lambda con: 100 * inyeccion.intervalo_exacto(int(_iny_k("S5", 0, "brecha_mes1")(con)), int(_iny("S5", 0, "brecha_mes1", "mundos")(con)))[extremo]


def _iny_const(nombre: str, factor: float = 1.0) -> Callable:
    from pipeline import inyeccion
    return lambda _con: factor * float(getattr(inyeccion, nombre))


def _veredictos_n(cumplidas: bool) -> Callable:
    """Number of preregistered injection rules that hold (cumplidas) or the number of rules."""
    from pipeline import inyeccion
    return lambda con: float(sum(inyeccion.veredictos(con).values()) if cumplidas else len(inyeccion.veredictos(con)))


def _claims_inyeccion() -> list[Claim]:
    """Every number of the injection page: the five summary bullets, the three tables and the design constants."""
    cl = []
    celda = lambda j: r"[^|]*\| " * j  # noqa: E731  (skips j table cells)

    def tabla(pref: str, titulo: str, filas, columnas) -> None:
        """columnas: (nombre, celda, medida, col, factor, tipo); tipo 'd' decimal con signo, 'p' porcentaje, 'ra' y 'rb' los dos extremos de un rango."""
        for esc, tam in filas:
            ini = titulo + r".*?\| " + esc + r" \| " + str(tam) + r" \| "
            for nombre, j, medida, col, factor, tipo in columnas:
                if tipo == "d":
                    pat, tol, fm = ini + celda(j) + SD, 0.05, "{:.1f}"
                elif tipo == "ra":
                    pat, tol, fm = ini + celda(j) + SD + r" a", 0.05, "{:.1f}"
                elif tipo == "rb":
                    pat, tol, fm = ini + celda(j) + r"-?\d+,\d+ a " + SD, 0.05, "{:.1f}"
                else:
                    pat, tol, fm = ini + celda(j) + PC, 0.5, "{:.0f}"
                cl.append(_c(f"iny_{pref}_{esc}_{tam}_{nombre}@wiki", W_INY, pat, _iny(esc, tam, medida, col, factor), tol, fm))

    brecha = [("plantado", 0, "brecha_mes1", "plantado", 1, "d"), ("plantado_puntos", 1, "brecha_mes1", "plantado_puntos", 1, "d"),
              ("recuperado", 2, "brecha_mes1", "recuperado_media", 1, "d"),
              ("p05", 4, "brecha_mes1", "recuperado_p05", 1, "ra"), ("p95", 4, "brecha_mes1", "recuperado_p95", 1, "rb"),
              ("ic", 5, "brecha_mes1", "ic_excluye_cero_frac", 100, "p")]
    neto_b = [("neto", 3, "brecha_mes1", "recuperado_neto", 1, "d")]
    partes = [("parte_dias", 6, "brecha_mes1", "parte_dias", 100, "p"), ("parte_tasa", 7, "brecha_mes1", "parte_tasa", 100, "p")]
    con_partes = [("S1", 100), ("S2", 10), ("S2", 20), ("S2", 30)]
    tabla("t1", r"## Brecha del mes 1", con_partes, brecha + neto_b + partes)
    tabla("t1", r"## Brecha del mes 1", [("S4", 3), ("S4", 5), ("S4", 8)], brecha + neto_b)
    tabla("t1", r"## Brecha del mes 1", [("S5", 0)], brecha)
    pend = [("plantado", 0, "pendiente_mes0", "plantado", 1, "d"), ("plantado_puntos", 1, "pendiente_mes0", "plantado_puntos", 1, "d"),
            ("recuperada", 2, "pendiente_mes0", "recuperado_media", 1, "d"),
            ("p05", 4, "pendiente_mes0", "recuperado_p05", 1, "ra"), ("p95", 4, "pendiente_mes0", "recuperado_p95", 1, "rb"),
            ("ic", 5, "pendiente_mes0", "ic_excluye_cero_frac", 100, "p"), ("mes_m1", 6, "pendiente_mes_m1", "recuperado_media", 1, "d")]
    tabla("t2", r"## Pendiente del mes 0", [("S3", 20), ("S3", 40), ("S3", 60)], pend + [("neto", 3, "pendiente_mes0", "recuperado_neto", 1, "d")])
    tabla("t2", r"## Pendiente del mes 0", [("S5", 0)], pend)
    previa = [("preten", 0, "preten", "recuperado_media", 1, "d"), ("base_limpia", 1, "brecha_mes1_base_limpia", "recuperado_media", 1, "d"),
              ("neta", 2, "brecha_mes1_neta", "recuperado_media", 1, "d"), ("base_original", 3, "brecha_mes1", "recuperado_media", 1, "d")]
    tabla("t3", r"## Brecha previa de nivel", [("S5", 0), ("S4", 3), ("S4", 5), ("S4", 8)], previa)
    # resumen
    cl += [
        _c("iny_r1_recuperado@wiki", W_INY, r"la brecha recuperada del mes 1 es " + SD + r" puntos en media de", _iny("S2", 20, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r1_mundos@wiki", W_INY, r"puntos en media de " + N + r" mundos", _iny("S2", 20, "brecha_mes1", "mundos"), 0, "{:.0f}"),
        _c("iny_r1_p05@wiki", W_INY, r"rango del 5% al 95%: " + SD + r" a", _iny("S2", 20, "brecha_mes1", "recuperado_p05"), 0.05, "{:.1f}"),
        _c("iny_r1_p95@wiki", W_INY, r"rango del 5% al 95%: -?\d+,\d+ a " + SD + r"\);", _iny("S2", 20, "brecha_mes1", "recuperado_p95"), 0.05, "{:.1f}"),
        _c("iny_r1_umbral_bajo@wiki", W_INY, r"la regla pedía entre (-\d+) y -\d+\.", lambda _c: -(20 + _iny_const("UMBRAL_R1")(_c)), 0.0, "{:.0f}"),
        _c("iny_r1_umbral_alto@wiki", W_INY, r"la regla pedía entre -\d+ y (-\d+)\.", lambda _c: -(20 - _iny_const("UMBRAL_R1")(_c)), 0.0, "{:.0f}"),
        _c("iny_r1_plantado_puntos@wiki", W_INY, r"una caída de 20% del caudal es unos " + SD + r" puntos y no -20", _iny("S2", 20, "brecha_mes1", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_r1_nulo@wiki", W_INY, r"la brecha residual del mundo nulo \(" + SD + r"\)\. Descontado", _iny("S5", 0, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r1_neto@wiki", W_INY, r"el estimador devuelve " + SD + r" puntos, lo plantado", _iny("S2", 20, "brecha_mes1", "recuperado_neto"), 0.05, "{:.1f}"),
        _c("iny_r2_dias@wiki", W_INY, r"la parte de los días del log de la brecha es " + PC, _iny("S1", 100, "brecha_mes1", "parte_dias", 100), 0.5, "{:.0f}"),
        _c("iny_r2_tasa@wiki", W_INY, r"la parte del caudal por día es " + PC, _iny("S2", 20, "brecha_mes1", "parte_tasa", 100), 0.5, "{:.0f}"),
        _c("iny_r2_umbral@wiki", W_INY, r"pedía al menos " + PC + r" en los dos", _iny_const("UMBRAL_R2", 100), 0.5, "{:.0f}"),
        _c("iny_r3_recuperada@wiki", W_INY, r"mes 0 recuperada es " + SD + r" puntos por cada", _iny("S3", 40, "pendiente_mes0", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r3_plantada@wiki", W_INY, r"mes 0 recuperada es [^(]*\(plantado " + SD + r" nominal\)", _iny("S3", 40, "pendiente_mes0", "plantado"), 0.05, "{:.1f}"),
        _c("iny_r3_plantada_puntos@wiki", W_INY, r"En puntos del índice lo plantado es " + SD + r" y, descontada", _iny("S3", 40, "pendiente_mes0", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_r3_nulo@wiki", W_INY, r"descontada la pendiente del mundo nulo \(" + SD + r"\)", _iny("S5", 0, "pendiente_mes0", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r3_neta@wiki", W_INY, r"del mundo nulo \(-?\d+,\d+\), lo recuperado es " + SD, _iny("S3", 40, "pendiente_mes0", "recuperado_neto"), 0.05, "{:.1f}"),
        _c("iny_r3_ic@wiki", W_INY, r"con el signo plantado en " + PC + r" de los mundos", _iny("S3", 40, "pendiente_mes0", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}"),
        _c("iny_r3_umbral@wiki", W_INY, r"de los mundos; la regla pedía al menos " + PC, _iny_const("UMBRAL_R3", 100), 0.5, "{:.0f}"),
        _c("iny_r4a_ic@wiki", W_INY, r"excluye cero en " + PC + r" de los mundos, \d+ de", _iny("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}"),
        _c("iny_r4a_k@wiki", W_INY, r"de los mundos, " + N + r" de \d+; la regla", _iny_k("S5", 0, "brecha_mes1"), 0, "{:.0f}"),
        _c("iny_r4a_mundos@wiki", W_INY, r"de los mundos, \d+ de " + N + r"; la regla", _iny("S5", 0, "brecha_mes1", "mundos"), 0, "{:.0f}"),
        _c("iny_r4a_umbral@wiki", W_INY, r"la regla del libro dice como máximo " + PC, _iny_const("UMBRAL_R4A", 100), 0.5, "{:.0f}"),
        _c("iny_r4a_operador@wiki", W_INY, r"el operador del libro es estricto \(< " + DEC + r"\)", _iny_const("UMBRAL_R4A"), 0.005, "{:.2f}"),
        _c("iny_r4a_borde_k@wiki", W_INY, r"con " + N + r" de \d+ mundos \(\d+%\) cumple el texto", _iny_k("S5", 0, "brecha_mes1"), 0, "{:.0f}"),
        _c("iny_r4a_borde_pc@wiki", W_INY, r"mundos \(" + PC + r"\) cumple el texto", _iny("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}"),
        _c("iny_r4a_exacto_bajo@wiki", W_INY, r"compatible con tasas de " + PC + r" a \d+%", _iny_exacto(0), 0.5, "{:.0f}"),
        _c("iny_r4a_exacto_alto@wiki", W_INY, r"compatible con tasas de \d+% a " + PC, _iny_exacto(1), 0.5, "{:.0f}"),
        _c("iny_r4a_brecha_nula@wiki", W_INY, r"La brecha media del mundo nulo es " + SD + r" puntos", _iny("S5", 0, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_s4_pts_preten@wiki", W_INY, r"con el 5% lo plantado es " + SD + r" en la pretendencia", _iny("S4", 5, "preten", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_s4_pts_mes1@wiki", W_INY, r"en la pretendencia, " + SD + r" en el mes 1 con la base limpia", _iny("S4", 5, "brecha_mes1_base_limpia", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_s4_pts_neta@wiki", W_INY, r"limpia y " + SD + r" en la brecha neta", _iny("S4", 5, "brecha_mes1_neta", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_r4b_preten@wiki", W_INY, r"la pretendencia recuperada es " + SD + r" puntos", _iny("S4", 5, "preten", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r4b_preten_plantada@wiki", W_INY, r"la pretendencia recuperada es [^(]*\(plantado " + SD + r"\)", _iny("S4", 5, "preten", "plantado"), 0.05, "{:.1f}"),
        _c("iny_r4b_neta@wiki", W_INY, r"la brecha neta del mes 1 es " + SD + r" puntos", _iny("S4", 5, "brecha_mes1_neta", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r4b_base_limpia@wiki", W_INY, r"de la base limpia como " + SD + r" puntos", _iny("S4", 5, "brecha_mes1_base_limpia", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_r4b_base_original@wiki", W_INY, r"a -1 como " + SD + r" puntos\.", _iny("S4", 5, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}"),
    ]
    # diseno
    cl += [
        _c("iny_meses_corridos@wiki", W_INY, r"corrida " + N + r" meses hacia atrás", _iny_const("DESPLAZAMIENTO", -1), 0, "{:.0f}"),
        _c("iny_mundos_diseno@wiki", W_INY, r"- Mundos: " + N + r" por celda", _iny("S2", 20, "brecha_mes1", "mundos"), 0, "{:.0f}"),
        _c("iny_fraccion_pads@wiki", W_INY, r"sortea el " + N + r"% de los pads hijo", _iny_const("FRACCION_PADS", 100), 0.5, "{:.0f}"),
        _c("iny_reps@wiki", W_INY, r"de falsación con " + N + r" repeticiones", _iny_const("REPS_MUNDO"), 0, "{:.0f}"),
        _c("iny_p_cierre@wiki", W_INY, r"S1 cierra el mes 1 \(cero días y cero petróleo\) en el " + DEC + r"% de los cercanos",
           _iny("S1", 100, "participacion_cierre", "recuperado_media", 100), 0.05, "{:.1f}"),
        _c("iny_objetivo_cierre@wiki", W_INY, r"brecha esperada de (-\d+) puntos en el mundo nulo", _iny_const("OBJETIVO_CIERRE", 100), 0.5, "{:.0f}"),
        _c("iny_caso_plantado_puntos@caso", CASO, r"\(unos " + SD + r" puntos del índice\)", _iny("S2", 20, "brecha_mes1", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_caso_nulo@caso", CASO, r"mundo nulo \(" + SD + r"\); descontado", _iny("S5", 0, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_caso_neto@caso", CASO, r"el estimador devuelve " + SD + r" puntos", _iny("S2", 20, "brecha_mes1", "recuperado_neto"), 0.05, "{:.1f}"),
        _c("iny_caso_tamano@caso", CASO, r"una caída plantada de " + PC + r" del caudal", _iny("S2", 20, "brecha_mes1", "tamano"), 0.5, "{:.0f}"),
        _c("iny_caso_recuperado@caso", CASO, r"se recupera como " + SD + r" puntos", _iny("S2", 20, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_caso_reglas_cumplidas@caso", CASO, r"se cumplen " + N + r" de las \d+ reglas", _veredictos_n(True), 0),
        _c("iny_caso_reglas_total@caso", CASO, r"se cumplen \d+ de las " + N + r" reglas", _veredictos_n(False), 0),
        _c("iny_caso_fp_k@caso", CASO, r"borde exacto \(" + N + r" de \d+ mundos", _iny_k("S5", 0, "brecha_mes1"), 0, "{:.0f}"),
        _c("iny_caso_fp_mundos@caso", CASO, r"borde exacto \(\d+ de " + N + r" mundos", _iny("S5", 0, "brecha_mes1", "mundos"), 0, "{:.0f}"),
        _c("iny_caso_falsos_positivos@caso", CASO, r"mundos, " + PC + r"\): cumple el texto", _iny("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}"),
        _c("iny_caso_umbral@caso", CASO, r"\(como máximo " + PC + r"\) pero no el operador", _iny_const("UMBRAL_R4A", 100), 0.5, "{:.0f}"),
        _c("iny_mundos_plan@wiki", W_INY, r"La corrida con " + N + r" mundos por celda pasó", _iny_const("MUNDOS_PLAN"), 0, "{:.0f}"),
        _c("iny_tope_minutos@wiki", W_INY, r"pasó de los " + N + r" minutos que la regla", _iny_const("TOPE_MINUTOS"), 0, "{:.0f}"),
        _c("iny_l_pend_pts@wiki", W_INY, r"con el 40% es " + SD + r" y no", _iny("S3", 40, "pendiente_mes0", "plantado_puntos"), 0.05, "{:.1f}"),
        _c("iny_l_pend_nominal@wiki", W_INY, r"con el 40% es -?\d+,\d+ y no " + SD, _iny("S3", 40, "pendiente_mes0", "plantado"), 0.05, "{:.1f}"),
        _c("iny_l_pend_nulo@wiki", W_INY, r"Descontando la pendiente del mundo nulo \(" + SD + r"\)", _iny("S5", 0, "pendiente_mes0", "recuperado_media"), 0.05, "{:.1f}"),
        _c("iny_l_pend_recuperado@wiki", W_INY, r"mundo nulo \(-?\d+,\d+\), lo recuperado \(" + SD + r"\)", _iny("S3", 40, "pendiente_mes0", "recuperado_neto"), 0.05, "{:.1f}"),
        _c("iny_l_pend_ratio@wiki", W_INY, r"queda cerca de lo plantado \(" + N + r"%\)", lambda con: 100 * _iny("S3", 40, "pendiente_mes0", "recuperado_neto")(con) / _iny("S3", 40, "pendiente_mes0", "plantado_puntos")(con), 0.5, "{:.0f}"),
        _c("iny_50_mundos@wiki", W_INY, r"La salida de esa corrida de " + N + r" mundos", _i50("S5", 0, "brecha_mes1", "mundos"), 0, "{:.0f}", wh=False),
        _c("iny_50_r1@wiki", W_INY, r"R1: " + SD + r" puntos\.", _i50("S2", 20, "brecha_mes1", "recuperado_media"), 0.05, "{:.1f}", wh=False),
        _c("iny_50_r2_dias@wiki", W_INY, r"R2: partes de " + PC + r" y", _i50("S1", 100, "brecha_mes1", "parte_dias", 100), 0.5, "{:.0f}", wh=False),
        _c("iny_50_r2_tasa@wiki", W_INY, r"R2: partes de \d+% y " + PC, _i50("S2", 20, "brecha_mes1", "parte_tasa", 100), 0.5, "{:.0f}", wh=False),
        _c("iny_50_r3@wiki", W_INY, r"R3: IC que excluye cero en " + PC, _i50("S3", 40, "pendiente_mes0", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}", wh=False),
        _c("iny_50_r4a@wiki", W_INY, r"R4a: " + PC + r" \(", _i50("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}", wh=False),
        _c("iny_50_r4a_k@wiki", W_INY, r"R4a: \d+% \(" + N + r" de \d+\)", lambda _c: round(_i50("S5", 0, "brecha_mes1", "ic_excluye_cero_frac")(_c) * _i50("S5", 0, "brecha_mes1", "mundos")(_c)), 0, "{:.0f}", wh=False),
        _c("iny_50_r4a_n@wiki", W_INY, r"R4a: \d+% \(\d+ de " + N + r"\)", _i50("S5", 0, "brecha_mes1", "mundos"), 0, "{:.0f}", wh=False),
        _c("iny_50_r4b_preten@wiki", W_INY, r"R4b: pretendencia " + SD + r" puntos", _i50("S4", 5, "preten", "recuperado_media"), 0.05, "{:.1f}", wh=False),
        _c("iny_50_r4b_neta@wiki", W_INY, r"brecha neta del mes 1 " + SD + r"\.", _i50("S4", 5, "brecha_mes1_neta", "recuperado_media"), 0.05, "{:.1f}", wh=False),
        _c("iny_mundos_bajados@wiki", W_INY, r"así que se bajó a " + N + r" mundos por celda", _iny("S2", 20, "brecha_mes1", "mundos"), 0, "{:.0f}"),
        _c("iny_fraccion_pads_limite@wiki", W_INY, r"Cada mundo usa el " + N + r"% de los pads", _iny_const("FRACCION_PADS", 100), 0.5, "{:.0f}"),
    ]
    return cl


def _claims_limites() -> list[Claim]:
    """Cifras de la pagina de limites (escrita a mano) que ningun otro grupo de claims fija: la brecha del mes 1 y el cierre
    a los 6 meses con los cuatro controles, la respuesta tardia de la dosis, las cotas del pad y la potencia del nulo. Las
    del README que no tenian claim (el resumen en ingles y los controles) van aca tambien. Todo se lee de los marts."""
    def anillo(agg: str, k: int) -> Callable:
        return lambda con: 100 * con.execute(f"select {agg}(brecha) from mart_anillo where k = {k}").fetchone()[0]

    def n_controles(con) -> float:
        return float(con.execute("select count(distinct variante) from mart_anillo where k = 1").fetchone()[0])

    def cierre_dentro(con) -> float:
        """5 cuando los cuatro controles quedan a menos de 5 puntos al mes 6; si no, el mayor desvio (y el claim falla)."""
        peor = 100 * con.execute("select max(abs(brecha)) from mart_anillo where k = 6").fetchone()[0]
        return 5.0 if peor < 5 else peor

    def ic_excluye_cero(con) -> float:
        return float(con.execute("select count(*) from mart_anillo where k = 6 and (ic_alto < 0 or ic_bajo > 0)").fetchone()[0])

    def potencia(col: str) -> Callable:
        return lambda con: con.execute(
            f"select max({col}) from mart_potencia_dosis where resultado = 'A' and modelo = 'conjunto'").fetchone()[0]

    def meses_n(con) -> float:
        return float(con.execute("select count(*) from mart_dosis_meses").fetchone()[0])

    def meses_min_p(col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_dosis_meses order by p limit 1").fetchone()[0]

    def cota_pad(resultado: list[str], pos: int) -> Callable:
        """Cota superior mayor de los IC del pad, tal como la escribe mart_dosis_pad_veredicto (pos 1: muestra completa, 2: cercania)."""
        def f(con):
            vals = []
            for (texto,) in con.execute("select texto from mart_dosis_pad_veredicto where resultado in ("
                                        + ", ".join(f"'{r}'" for r in resultado) + ")").fetchall():
                m = re.search(r"es de (\d+,\d+) desvíos de la caída en la muestra completa y (\d+,\d+) en la cercanía", texto)
                vals.append(parse_numero(m.group(pos)))
            return max(vals)
        return f

    def pruebas_pad(con) -> float:
        return float(con.execute("select count(*) from (select distinct modelo, variable from mart_dosis_pad "
                                 "where resultado = 'A' and modelo in ('completo', 'cercania'))").fetchone()[0])

    def fiv_max(con) -> float:
        return con.execute("select max(coef_sd) from mart_dosis_pad where modelo = 'vif'").fetchone()[0]

    brecha1 = r"la brecha del mes 1 \(de "
    cl = [
        _c("lim_brecha_mes1_max@wiki", W_LIM, brecha1 + SD + r" a", anillo("max", 1), 0.05, "{:.1f}"),
        _c("lim_brecha_mes1_min@wiki", W_LIM, brecha1 + r"-?\d+,\d+ a " + SD + r" puntos\)", anillo("min", 1), 0.05, "{:.1f}"),
        _c("lim_controles_n@wiki", W_LIM, r"de (cuatro) controles se use", n_controles, 0),
        _c("lim_mes6_dentro@wiki", W_LIM, r"la brecha queda dentro de " + N + r" puntos con los cuatro", cierre_dentro, 0),
        _c("lim_mes6_max@wiki", W_LIM, r"\(entre " + SD + r" y -?\d+,\d+\), pero con", anillo("max", 6), 0.05, "{:.1f}"),
        _c("lim_mes6_min@wiki", W_LIM, r"\(entre -?\d+,\d+ y " + SD + r"\), pero con", anillo("min", 6), 0.05, "{:.1f}"),
        _c("lim_mes6_ic_excluye@wiki", W_LIM, r"pero con " + N + r" de ellos su IC excluye cero", ic_excluye_cero, 0),
        _c("lim_mes6_menos_de@wiki", W_LIM, r"quiere decir menos de " + N + r" puntos y no cero", cierre_dentro, 0),
        _c("lim_meses_pruebas@wiki", W_LIM, r"\(" + N + r" pruebas con Holm", meses_n, 0),
        _c("lim_meses_k@wiki", W_LIM, r"la depleción al mes " + N + r", con p de", meses_min_p("k"), 0),
        _c("lim_meses_p@wiki", W_LIM, r"con p de " + DEC + r" sin ajustar", meses_min_p("p"), 0.0005, "{:.3f}"),
        _c("lim_meses_p_holm@wiki", W_LIM, r"y de " + DEC + r" ajustado", meses_min_p("p_holm"), 0.005, "{:.2f}"),
        _c("lim_pad_pruebas@wiki", W_LIM, r"ninguna de las (nueve) pruebas", pruebas_pad, 0),
        _c("lim_pad_cota_completa@wiki", W_LIM, r"llega a " + DEC + r" desvíos de la caída en la muestra completa",
           cota_pad(["A", "B"], 1), 0.005, "{:.2f}"),
        _c("lim_pad_cota_indice@wiki", W_LIM, r"y a " + DEC + r" \(índice\)", cota_pad(["A"], 2), 0.005, "{:.2f}"),
        _c("lim_pad_cota_caudal@wiki", W_LIM, r"o " + DEC + r" \(caudal por día\)", cota_pad(["B"], 2), 0.005, "{:.2f}"),
        _c("lim_pad_fiv@wiki", W_LIM, r"el FIV máximo es " + DEC, fiv_max, 0.05, "{:.1f}"),
        _c("lim_pot_eventos@wiki", W_LIM, r"con " + N + r" eventos en \d+ pads hijo", potencia("n"), 0),
        _c("lim_pot_pads@wiki", W_LIM, r"con [\d.]+ eventos en " + N + r" pads hijo", potencia("pads"), 0),
        _c("lim_pot_menor@wiki", W_LIM, r"va de " + DEC + r" a \d+,\d+ desvíos de la caída por desvío de la dosis",
           lambda con: con.execute("select min(mde80_holm_desvios) from mart_potencia_dosis where resultado = 'A' "
                                   "and modelo = 'conjunto'").fetchone()[0], 0.006, "{:.2f}"),
        _c("lim_pot_mayor@wiki", W_LIM, r"va de \d+,\d+ a " + DEC + r" desvíos de la caída por desvío de la dosis",
           potencia("mde80_holm_desvios"), 0.006, "{:.2f}"),
        # README: the English summary and the numbers of the short limits that had no claim
        # the English text writes 2,077 with a thousands comma, which parse_numero reads as a decimal: the value is divided by 1000
        _c("readme_en_brecha_bajo@readme", R, r"produce " + N + r" to \d+ percentage points less", _pretrend_descontada("mart_placebo_pretrend")),
        _c("readme_en_brecha_alto@readme", R, r"produce \d+ to " + N + r" percentage points less", _brecha_mes1),
        _c("readme_en_eventos@readme", R, r"\(([\d,]+) events\)", lambda con: _eventos_cercanos(con) / 1000, 0.0005, "{:.3f}"),
        _c("readme_controles_excluyen@readme", R, r"con " + N + r" de los 4 controles probados", ic_excluye_cero, 0),
        _c("readme_controles_n@readme", R, r"con \d+ de los " + N + r" controles probados", n_controles, 0),
        _c("readme_eventos_propios@readme", R, r"reproduce la brecha del mes 1 y sus " + N + r" eventos", _eventos_cercanos, 0),
    ]
    return cl


CLAIMS: list[Claim] = [
    # data quality report (committed JSON, no warehouse needed)
    _c("filas_origen_aprox@readme", R, r"son " + N + r" filas", lambda _: _dq()["filas_origen_produccion"], 1500, wh=False),
    _c("descarga_mb@readme", R, r"descarga unos (\d+) MB",
       lambda _: sum(v["bytes"] for v in json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8")).values()) / 1e6, 5, wh=False),
    _c("controles@readme", R, r"(\d+) controles de calidad", _n_controles, wh=False),
    _c("filas_origen@docs", D, r"\(" + N + r" filas de producci", lambda _: _dq()["filas_origen_produccion"], 0.5, wh=False),
    _c("filas_origen_aprox@docs", D, r"\b" + N + r" filas se reconstruyen", lambda _: _dq()["filas_origen_produccion"], 1500, wh=False),
    _c("controles@docs", D, r"(\d+) controles:", _n_controles, wh=False),
    _c("bloqueantes_fallidos@docs", D, r"\((\d+) fallidos hoy\)", lambda _: _dq()["bloqueantes_fallidos"], wh=False),
    # typed operations of the agent
    _c("ops@readme_agente", R, r"sobre (\d+) operaciones tipadas", _n_ops, wh=False),
    _c("ops@docs", D, r"Agente con (\d+) operaciones tipadas", _n_ops, wh=False),
    # agent evaluation (committed result files)
    _c("eval_dev_ok@readme", R, r"(\d+)/\d+ en desarrollo", lambda _: _ev_ok("dev"), wh=False),
    _c("eval_dev_n@readme", R, r"\d+/(\d+) en desarrollo", lambda _: _ev_n("dev"), wh=False),
    _c("eval_holdout_ok@readme", R, r"y (\d+)/\d+ en\s+reservadas", lambda _: _ev_ok("holdout"), wh=False),
    _c("eval_holdout_n@readme", R, r"y \d+/(\d+) en\s+reservadas", lambda _: _ev_n("holdout"), wh=False),
    _c("eval_dev_ok@docs", D, r"(\d+)/\d+ y \d+/\d+ en la .ltima medici", lambda _: _ev_ok("dev"), wh=False),
    _c("eval_dev_n@docs", D, r"\d+/(\d+) y \d+/\d+ en la .ltima medici", lambda _: _ev_n("dev"), wh=False),
    _c("eval_holdout_ok@docs", D, r"\d+/\d+ y (\d+)/\d+ en la .ltima medici", lambda _: _ev_ok("holdout"), wh=False),
    _c("eval_holdout_n@docs", D, r"\d+/\d+ y \d+/(\d+) en la .ltima medici", lambda _: _ev_n("holdout"), wh=False),
    # findings ledger (committed CSV)
    _c("hipotesis@readme", R, r"(\w+) hip.tesis con umbral", _hipotesis, wh=False),
    _c("hipotesis@docs", D, r"(\w+) hip.tesis con umbral", _hipotesis, wh=False),
    # interference event study: headline
    _c("eventos_cercanos@readme", R, r"\(" + N + r" eventos\)", _eventos_cercanos),
    _c("eventos_cercanos@docs", D, N + r" fracturas de un pozo nuevo", _eventos_cercanos),
    _c("brecha_mes1@readme", R, r"entre \d+ y (\d+) puntos menos", _brecha_mes1),
    _c("brecha_mes1_bis@readme", R, r"Interferencia al mes 1[^|]*\| \d+ a (\d+) puntos menos", _brecha_mes1),
    _c("brecha_mes1_cota@readme", R, r"por eso (\d+) es una cota superior", _brecha_mes1),
    _c("brecha_mes1_cota_bis@readme", R, r"de la brecha de (\d+): \d+ a \d+ \|", _brecha_mes1),
    _c("brecha_descontada@readme", R, r"entre (\d+) y \d+ puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_bis@readme", R, r"Interferencia al mes 1[^|]*\| (\d+) a \d+ puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_valor@readme", R, r"(\d+) a \d+ el valor descontado", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_sin_previos@readme", R, r"\d+ a (\d+) el valor descontado",
       _pretrend_descontada("mart_placebo_pretrend_sin_previos")),
    _c("brecha_ic_bajo@readme", R, r"brecha de \d+: (\d+) a \d+ \|", _blq(B_HEAD, 1, "ic_alto_5km", -100)),
    _c("brecha_ic_alto@readme", R, r"brecha de \d+: \d+ a (\d+) \|", _blq(B_HEAD, 1, "ic_bajo_5km", -100)),
    _c("brecha_mes1@docs", D, r"entre \d+ y (\d+) puntos menos que el control", _brecha_mes1),
    # year table and deferred oil now live on the finding page (milli-units of the index / barrels)
    _c("brecha_mes1_2025@wiki", W_INT, r"\| 2025 \| [\d.]+ \| -0,(\d+) \|", lambda con: _brecha_anio(2025)(con) * 10, 0.5),
    _c("brecha_mes1_2026@wiki", W_INT, r"\| 2026 \| [\d.]+ \| -0,(\d+) \|", lambda con: _brecha_anio(2026)(con) * 10, 0.5),
    _c("diferido_total@wiki", W_INT, r"eventos cercanos\): " + N + r" bbl", _diferido_bbl(), 1),
    _c("diferido_ypf@wiki", W_INT, r"\[YPF\]\([^)]*\) \| [\d.]+ \| " + N + r" \|", _diferido_bbl("YPF"), 1),
    _c("diferido_total@docs", D, r"entre " + DEC + r" y \d+,\d+ millones de barriles diferidos", _rango_mbbl("neto_previa"), 0.05, "{:.1f}"),
    _c("diferido_cota_superior@docs", D, r"entre \d+,\d+ y " + DEC + r" millones de barriles diferidos", _diferido(), 0.05, "{:.1f}"),
    # the deferred oil as a range (page diferido.md); the min() trick also checks the order of the variants
    _c("diferido_original@wiki_dif", W_DIF, r"- Original: " + N + r" barriles", _rango_bbl("original"), 1),
    _c("diferido_sin_duplicar@wiki_dif", W_DIF, r"- Sin duplicar: " + N + r" barriles", _rango_bbl("sin_duplicar", "original"), 1),
    _c("diferido_neto@wiki_dif", W_DIF, r"descontando la brecha previa: " + N + r" barriles", _rango_bbl("neto_previa", "sin_duplicar"), 1),
    _c("diferido_rango_inferior@wiki_dif", W_DIF, r"va de " + DEC + r" a \d+,\d+ millones de barriles",
       lambda con: _rango_bbl("neto_previa", "original")(con) / 1e6, 0.05, "{:.1f}"),
    _c("diferido_rango_superior@wiki_dif", W_DIF, r"va de \d+,\d+ a " + DEC + r" millones de barriles", _rango_mbbl("original"), 0.05, "{:.1f}"),
    _c("diferido_evento_mediana@wiki_dif", W_DIF, r"\| [\d.]+ \| -?[\d.]+ \| (-?[\d.]+) \| -?[\d.]+ \| -?[\d.]+ \| \d+% \|",
       _evento_mediana, 1),
    _c("diferido_evento_signo@wiki_dif", W_DIF, r"mediana por evento a 24 meses \((-?[\d.]+) barriles\) queda por (?:debajo|encima) de cero",
       _evento_mediana_signo, 1),
    _c("diferido_ypf_mediana@wiki_dif", W_DIF, r"\| YPF \| [\d.]+ \| (-?[\d.]+) \(", _operador_mediana("YPF"), 1),
    # placebo and permutation (table row of the README)
    _c("fechas_falsas_min@readme", R, r"fechas falsas de " + NEG + r" a", _fechas_falsas("min"), 0.05, "{:.1f}"),
    _c("fechas_falsas_max@readme", R, r"fechas falsas de -?\d+,\d+ a " + DEC + r" puntos", _fechas_falsas("max"), 0.05, "{:.1f}"),
    _c("permutadas_min@readme", R, r"permutadas de " + NEG + r" a", _permutacion("minimo"), 0.05, "{:.1f}"),
    _c("permutadas_max@readme", R, r"permutadas de -?\d+,\d+ a " + NEG + r"; real", _permutacion("maximo"), 0.05, "{:.1f}"),
    _c("permutadas_real@readme", R, r"real " + NEG + r" \|", _permutacion("brecha_real"), 0.05, "{:.1f}"),
    # decomposition of the gap (finding page): the headline reproduced, the near bands, the far ring
    _c("desc_brecha_principal@wiki", W_DES, r"base de los meses -3 a -1 la brecha del petróleo al mes 1 es " + NEG + r" puntos",
       lambda con: -_brecha_mes1(con), 0.05, "{:.1f}"),
    _c("desc_brecha_referencia@wiki", W_DES, r"base del resultado principal \(meses -3 a -1\) la brecha del petróleo al mes 1 es "
       + NEG + r" puntos", _desc_ref_k1, 0.05, "{:.1f}"),
    _c("desc_eventos_cercanos@wiki", W_DES, r"menos de 1 km suman " + N + r" eventos", _desc_n_bandas_cercanas, 0),
    _c("desc_eventos_k1@wiki", W_DES, r"los mismos " + N + r" cercanos del panel", _desc_n_k1, 0),
    _c("desc_anillo_brecha@wiki", W_DES, r"2 a 5 km, al mes 1\): (-?\d+,\d+) puntos", _desc_anillo("brecha"), 0.05, "{:.1f}"),
    _c("desc_anillo_ic_bajo@wiki", W_DES, r"2 a 5 km, al mes 1\): -?\d+,\d+ puntos \(IC (-?\d+,\d+) a", _desc_anillo("ic_bajo"), 0.05,
       "{:.1f}"),
    _c("desc_cabecera_anillo@wiki", W_DES, r"Contra el anillo de 5 a 10 km la brecha del mes 1 es " + NEG + r" puntos", _desc_cabecera, 0.05,
       "{:.1f}"),
    _c("desc_cabecera_contra_2a5@wiki", W_DES, r"negativa que los " + NEG + r" contra 2 a 5 km", _desc_ref_k1, 0.05, "{:.1f}"),
    _c("desc_anillo_rinden@wiki", W_DES, r"rinden " + DEC + r" puntos (?:más|menos) que los de 2 a 5 km", _desc_anillo_abs, 0.05, "{:.1f}"),
    _c("desc_parte_dias@wiki", W_DES, r"La parte de los días es " + N + r"% \(IC", _desc_adit("parte_dias"), 0.5),
    _c("desc_parte_tasa@wiki", W_DES, r"del caudal por día es " + N + r"%\. Las medianas", _desc_adit("parte_tasa"), 0.5),
    _c("desc_parte_dias_sin@wiki", W_DES, r"controles\): la parte de los días es " + N + r"% y", _desc_adit("parte_dias", "sin_cerrados"), 0.5),
    _c("desc_parte_tasa_sin@wiki", W_DES, r"los días es [\d.]+% y la del caudal por día " + N + r"%\.", _desc_adit("parte_tasa", "sin_cerrados"),
       0.5),
    _c("desc_cierres_bajo_cercano@wiki", W_DES, r"el " + N + r"% de los padres cercanos tiene un índice", _desc_cierres("near_bajo_umbral"), 0.5),
    _c("desc_cierres_bajo_control@wiki", W_DES, r"menor a 0,9 contra el " + N + r"% de los controles", _desc_cierres("ctrl_bajo_umbral"), 0.5),
    _c("desc_cierres_cerrado_cercano@wiki", W_DES, r"y el " + N + r"% de los cercanos estuvo cerrado", _desc_cierres("near_cerrado"), 0.5),
    _c("desc_cierres_cerrado_control@wiki", W_DES, r"cerrado todo el mes contra el " + N + r"% de los controles", _desc_cierres("ctrl_cerrado"),
       0.5),
    # synchrony within the month (finding page)
    *_claims_sincronia(),
    *_claims_decision(),
    *_claims_potencia_dosis(),
    *_claims_robustez_operador(),
    *_claims_resumen_operador(),
    *_claims_informe(),
    *_claims_mundo(),
    *_claims_globo(),
    *_claims_bloques(),
    # the page of the pre-registered 2026 test: its own numbers against the marts it writes
    *_claims_carga_anual(),
    # child side (finding page, README row and case study paragraph)
    *_claims_hijo(),
    *_claims_hijo_celdas(),
    *_claims_gas(),
    *_claims_literatura(),
    *_claims_limites(),
    *_claims_prospectiva(),
    *_claims_inyeccion(),
    *_claims_colorado(),
    *_claims_fuentes_mundo(),
    *_claims_mapa_base(),
    *_claims_replicacion(),
    *_claims_wyoming(),
    *_claims_replicacion(WYOMING),
    *_claims_familia(),
    _c("sinc_pendiente@readme", R, r"la brecha del mes 0 cambia " + SD + r" puntos por cada 0,1", _sinc_pend(0, "pendiente", 10), 0.05, "{:.1f}"),
    _c("sinc_ic_bajo@readme", R, r"IC 95%: " + SD + r" a -?\d+,\d+; el mes previo", _sinc_pend(0, "ic_bajo", 10), 0.05, "{:.1f}"),
    _c("sinc_ic_alto@readme", R, r"IC 95%: -?\d+,\d+ a " + SD + r"; el mes previo", _sinc_pend(0, "ic_alto", 10), 0.05, "{:.1f}"),
    _c("sinc_previo_pendiente@readme", R, r"el mes previo: " + SD + r" \(IC", _sinc_pend(-1, "pendiente", 10), 0.05, "{:.1f}"),
    _c("sinc_previo_ic_bajo@readme", R, r"el mes previo: -?\d+,\d+ \(IC " + SD + r" a", _sinc_pend(-1, "ic_bajo", 10), 0.05, "{:.1f}"),
    _c("sinc_previo_ic_alto@readme", R, r"el mes previo: -?\d+,\d+ \(IC -?\d+,\d+ a " + SD + r"\)", _sinc_pend(-1, "ic_alto", 10), 0.05, "{:.1f}"),
    # basin anisotropy axis
    _c("eje_cuenca@readme", R, r"\| (\d+) grados \(E-O\) \|", _cuenca("eje_grados")),
    _c("eje_ic_bajo@readme", R, r"\| (\d+) a \d+ grados \|", _cuenca("ic_bajo")),
    _c("eje_ic_alto@readme", R, r"\| \d+ a (\d+) grados \|", _cuenca("ic_alto")),
    _c("eje_cuenca@docs", D, r"unos (\d+) grados \(IC", _cuenca("eje_grados")),
    _c("eje_ic_bajo@docs", D, r"\(IC (\d+) a \d+\)", _cuenca("ic_bajo")),
    _c("eje_ic_alto@docs", D, r"\(IC \d+ a (\d+)\)", _cuenca("ic_alto")),
    _c("shmax@readme", R, r"SHmax publicado \(" + DEC + r"\)", _shmax, 0.05, "{:.1f}", wh=False),
    _c("shmax@docs", D, r"SHmax publicado \(unos " + DEC + r"\)", _shmax, 0.05, "{:.1f}", wh=False),
    _c("holdout_eje_entrenamiento@readme", R, r"(\d+) grados con datos viejos", _holdout_eje("Eje de entrenamiento")),
    _c("holdout_eje_prueba@readme", R, r"(\d+) en los nuevos", _holdout_eje("Eje ajustado en la prueba")),
    # cost model (out-of-sample)
    _c("costo_r2@readme", R, r"R2 fuera de muestra " + NEG, _costo_cv_r2("modelo"), 0.005, "{:.2f}"),
    _c("costo_r2_media_area@readme", R, r"la media del .rea da " + DEC, _costo_cv_r2("media_area"), 0.005, "{:.2f}"),
    # robustness (finding page)
    _c("rob_subconjuntos@wiki", W_ROB, r"El IC de \d+ de (\d+) subconjuntos", _rob_n(), 0),
    _c("rob_subconjuntos@docs", D, r"en (\d+) subconjuntos", _rob_n(), 0),
    _c("rob_definidos@wiki", W_ROB, r"de los (\d+) restantes", _rob_definidos, 0),
    _c("rob_indefinidos@wiki", W_ROB, r"En (\d+) el IC mide 90 grados", _rob_indefinidos, 0),
    _c("rob_p_alto@wiki", W_ROB, r"quedan (\d+) subconjuntos", _rob_p_alto, 0),
    _c("rob_alternativas@wiki", W_ROB, r"se repite en \d+ de (\d+) especificaciones alternativas", _rob_alternativas, 0),
    _c("rob_coef_desvio@wiki", W_ROB, r"es (-[\d.]+) bbl por 10 grados", _coef_desvio, 5),
    # pads (the pad-grouping report is a data-quality warning in the committed JSON)
    _c("pads_cambian@dq", DQ, r"(\d+) pozos cambian de pad", _pads("pozos_cambian"), 0),
    _c("pads_pozos@dq", DQ, r"sobre (\d+) pozos shale", _pads("pozos"), 0),
    # production and design
    _c("prod_kbbl_d@readme", R, r"produce unos (\d+) kbbl/d", _prod_kbbl),
    _c("ypf_pct@readme", R, r"YPF el (\d+)%", _ypf_pct),
    _c("rama_2017@readme", R, r"unos " + N + r" m \(cohorte 2017\)", _diseno(2017, "rama_m_mediana"), 50),
    _c("rama_2025@readme", R, r"a " + N + r" m \(cohorte 2025\)", _diseno(2025, "rama_m_mediana"), 50),
    _c("bblm_2017@readme", R, r"baj. de (\d+) a \d+ bbl/m", _diseno(2017, "bbl_12m_por_m_mediana")),
    _c("bblm_2025@readme", R, r"baj. de \d+ a (\d+) bbl/m", _diseno(2025, "bbl_12m_por_m_mediana")),
    # one number per fact: the README and the committed dashboard (site/index.html) must print the same value
    # the 2026 rise: the README prints the pre-registered test (pipeline.carga_anual), not the raw yearly figure
    _c("carga_anual_d@readme", R, r"antig.edad de carga de fracturas en todos los a.os: " + SIG + r" puntos", _carga_anual("d"), 0.05,
       "{:.1f}"),
    _c("carga_anual_ic_bajo@readme", R, r"puntos \| IC 95% por bloques de 5 km: " + SIG + r" a -?\d+,\d+; \d+ eventos cercanos de 2026",
       _carga_anual("ic_bajo"), 0.05, "{:.1f}"),
    _c("carga_anual_ic_alto@readme", R, r"puntos \| IC 95% por bloques de 5 km: -?\d+,\d+ a " + SIG + r"; \d+ eventos cercanos de 2026",
       _carga_anual("ic_alto"), 0.05, "{:.1f}"),
    _c("carga_anual_n@readme", R, r"; " + N + r" eventos cercanos de 2026 \| no firme", _carga_anual("n_cercanos", 1, "no firme"), 0),
    _c("carga_anual_juntos_d@readme", R, r"con 2025 y 2026 juntos da " + SIG + r" puntos", _carga_anual("d", estadistico="2025_2026"), 0.05,
       "{:.1f}"),
    _c("carga_anual_juntos_ic_bajo@readme", R, r"juntos da -?\d+,\d+ puntos \(IC 95%: " + SIG + r" a -?\d+,\d+\)",
       _carga_anual("ic_bajo", estadistico="2025_2026"), 0.05, "{:.1f}"),
    _c("carga_anual_juntos_ic_alto@readme", R, r"juntos da -?\d+,\d+ puntos \(IC 95%: -?\d+,\d+ a " + SIG + r"\)",
       _carga_anual("ic_alto", estadistico="2025_2026"), 0.05, "{:.1f}"),
    _c("diferido_total@readme", R, r"va de \d+,\d+ a " + DEC + r" millones de barriles", _diferido(), 0.05, "{:.1f}"),
    _c("diferido_cota_inferior@readme", R, r"va de " + DEC + r" a \d+,\d+ millones de barriles", _rango_mbbl("neto_previa"), 0.05, "{:.1f}"),
    _c("shmax@sitio", S, r"SHmax (\d+,\d+)</text>", _shmax, 0.05, "{:.1f}", wh=False),
    _c("brecha_mes1_descontada@sitio=readme", R, r"entre (\d+) y \d+ puntos menos",
       _sitio(r'id="kpis-interf"><div class="kpi"><div class="v">-(\d+) a -\d+</div>'), 0, wh=False),
    _c("brecha_mes1_bruta@sitio=readme", R, r"entre \d+ y (\d+) puntos menos",
       _sitio(r'id="kpis-interf"><div class="kpi"><div class="v">-\d+ a -(\d+)</div>'), 0, wh=False),
    _c("brecha_mes1_bruta_lectura@sitio=readme", R, r"entre \d+ y (\d+) puntos menos",
       _sitio(r"rinden (\d+) puntos menos que los padres de control"), 0, wh=False),
    _c("brecha_mes1_descontada@hallazgo=readme", R, r"entre (\d+) y \d+ puntos menos",
       _sitio(r'id="hallazgo"><p class="frase">.*?rinden entre (\d+) y \d+ puntos menos'), 0, wh=False),
    _c("brecha_mes1_bruta@hallazgo=readme", R, r"entre \d+ y (\d+) puntos menos",
       _sitio(r'id="hallazgo"><p class="frase">.*?rinden entre \d+ y (\d+) puntos menos'), 0, wh=False),
    _c("carga_anual_d@sitio=readme", R, r"antig.edad de carga de fracturas en todos los a.os: " + SIG + r" puntos",
       _sitio(r"entre 2026 y 2021 a 2024 es de " + SIG + r" puntos \(IC 95% por bloques de 5 km"), 0, "{:.1f}", wh=False),
    _c("carga_anual_ic_bajo@sitio=readme", R, r"puntos \| IC 95% por bloques de 5 km: " + SIG + r" a -?\d+,\d+; \d+ eventos cercanos de 2026",
       _sitio(r"es de -?\d+,\d+ puntos \(IC 95% por bloques de 5 km: " + SIG + r" a -?\d+,\d+\): no firme"), 0, "{:.1f}", wh=False),
    _c("carga_anual_ic_alto@sitio=readme", R, r"puntos \| IC 95% por bloques de 5 km: -?\d+,\d+ a " + SIG + r"; \d+ eventos cercanos de 2026",
       _sitio(r"es de -?\d+,\d+ puntos \(IC 95% por bloques de 5 km: -?\d+,\d+ a " + SIG + r"\): no firme"), 0, "{:.1f}", wh=False),
    _c("diferido_total@sitio=readme", R, r"va de \d+,\d+ a " + DEC + r" millones de barriles",
       _sitio(r'<span class="v">de \d+,\d+ a (\d+,\d+) M</span><span class="l">bbl diferidos'), 0, "{:.1f}", wh=False),
    _c("diferido_cota_inferior@sitio=readme", R, r"va de " + DEC + r" a \d+,\d+ millones de barriles",
       _sitio(r'<span class="v">de (\d+,\d+) a \d+,\d+ M</span><span class="l">bbl diferidos'), 0, "{:.1f}", wh=False),
    _c("bblm_2017@sitio=readme", R, r"baj. de (\d+) a \d+ bbl/m",
       _sitio(r"bajó de (\d+) bbl/m \(cohorte 2017\)"), 0, wh=False),
    _c("bblm_2025@sitio=readme", R, r"baj. de \d+ a (\d+) bbl/m",
       _sitio(r"a (\d+) bbl/m \(cohorte 2025\)"), 0, wh=False),
    # case study (docs/caso-interferencia.md): every number of the body; the English abstract writes 2,077 and 5.8 with the
    # English separators, so those are compared as thousandths / tenths
    _c("abstract_eventos@caso", CASO, r"event study of (\d,\d+) events", lambda con: _eventos_cercanos(con) / 1000, 0.0005, "{:.3f}"),
    _c("abstract_brecha_descontada@caso", CASO, r"yield (\d+) to \d+ percentage points less", _pretrend_descontada("mart_placebo_pretrend")),
    _c("abstract_brecha_descontada_neta@caso", CASO, r"(\d+) is net of the pre-trend", _pretrend_descontada("mart_placebo_pretrend")),
    _c("abstract_brecha_bruta@caso", CASO, r"yield \d+ to (\d+) percentage points less", _brecha_mes1),
    _c("abstract_brecha_bruta_parentesis@caso", CASO, r"\((\d+) is a raw upper bound", _brecha_mes1),
    _c("abstract_diferido_inferior@caso", CASO, r"ranges from (\d+\.\d+) to \d+\.\d+ million barrels",
       lambda con: 10 * _rango_bbl("neto_previa", "original")(con) / 1e6, 0.5, "{:.1f}"),
    _c("abstract_diferido_superior@caso", CASO, r"ranges from \d+\.\d+ to (\d+\.\d+) million barrels",
       lambda con: 10 * _rango_mbbl("original")(con), 0.5, "{:.1f}"),
    # data and method
    _c("filas_produccion@caso", CASO, N + r" filas de producci.n mensual por pozo", lambda _: _dq()["filas_origen_produccion"], 0.5, wh=False),
    _c("metodo_km_cercano@caso", CASO, r"a menos de (\d+) km del hijo", _km("km_hasta", "0 a 1")),
    _c("metodo_km_control_desde@caso", CASO, r"controles son pozos de la misma edad a (\d+) a \d+ km", _km("km_desde", "2 a 5")),
    _c("metodo_km_control_hasta@caso", CASO, r"controles son pozos de la misma edad a \d+ a (\d+) km", _km("km_hasta", "2 a 5")),
    _c("metodo_eventos@caso", CASO, r"un estudio de eventos con " + N + r" eventos", _eventos_cercanos),
    _c("metodo_hipotesis@caso", CASO, r"Pruebas corridas: (\w+) hip.tesis con umbral fijo", _hipotesis, wh=False),
    _c("metodo_subconjuntos@caso", CASO, r"y " + N + r" subconjuntos de robustez", _rob_n()),
    _c("metodo_intervalos@caso", CASO, r"agrega " + N + r" intervalos", _n_intervalos),
    # result
    _c("brecha_descontada@caso", CASO, r"entre (\d+) y \d+ puntos menos que los controles", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_el19@caso", CASO, r"el (\d+) descuenta la brecha previa", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_rango@caso", CASO, r"rango de (\d+) a \d+ se mantiene", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_bruta@caso", CASO, r"entre \d+ y (\d+) puntos menos que los controles", _brecha_mes1),
    _c("brecha_bruta_el23@caso", CASO, r"El (\d+) es el valor en bruto", _brecha_mes1),
    _c("brecha_bruta_rango@caso", CASO, r"rango de \d+ a (\d+) se mantiene", _brecha_mes1),
    _c("brecha_bruta_cota@caso", CASO, r"por eso (\d+) es una cota superior", _brecha_mes1),
    _c("brecha_principal@caso", CASO, r"\(" + NEG + r" puntos con la base de los meses -3 a -1", _desc_ref_k1, 0.05, "{:.1f}"),
    _c("brecha_sin_previos@caso", CASO, r"\(el (\d+) es el mismo descuento",
       _pretrend_descontada("mart_placebo_pretrend_sin_previos")),
    _c("pretendencia_k3@caso", CASO, r"hay una brecha: " + NEG + r", -\d+,\d+ y -\d+,\d+ puntos en los meses", _pretrend_k(-3), 0.05, "{:.1f}"),
    _c("pretendencia_k2@caso", CASO, r"hay una brecha: -\d+,\d+, " + NEG + r" y -\d+,\d+ puntos en los meses", _pretrend_k(-2), 0.05, "{:.1f}"),
    _c("pretendencia_k1@caso", CASO, r"hay una brecha: -\d+,\d+, -\d+,\d+ y " + NEG + r" puntos en los meses", _pretrend_k(-1), 0.05, "{:.1f}"),
    _c("brecha_mes6@caso", CASO, r"casi se cierra: " + NEG + r" puntos en el mes 6", _brecha_k_original(6), 0.05, "{:.1f}"),
    _c("diferido_inferior@caso", CASO, r"va de " + DEC + r" a \d+,\d+ millones de barriles",
       lambda con: _rango_bbl("neto_previa", "original")(con) / 1e6, 0.05, "{:.1f}"),
    _c("diferido_superior@caso", CASO, r"va de \d+,\d+ a " + DEC + r" millones de barriles", _rango_mbbl("original"), 0.05, "{:.1f}"),
    _c("diferido_mediana_24m@caso", CASO, r"la mediana es (-?[\d.]+) barriles", _evento_mediana, 1),
    _c("parte_dias@caso", CASO, r"d.as producidos explican el " + N + r"% de la brecha", _desc_adit("parte_dias"), 0.5),
    _c("parte_tasa@caso", CASO, r"caudal por d.a el " + N + r"%\. Sin", _desc_adit("parte_tasa"), 0.5),
    _c("parte_dias_sin@caso", CASO, r"sigue mixta \(" + N + r"% y \d+%\)", _desc_adit("parte_dias", "sin_cerrados"), 0.5),
    _c("parte_tasa_sin@caso", CASO, r"sigue mixta \(\d+% y " + N + r"%\)", _desc_adit("parte_tasa", "sin_cerrados"), 0.5),
    _c("cierres_cercanos@caso", CASO, r"El " + N + r"% de los padres cercanos redujo", _desc_cierres("near_bajo_umbral"), 0.5),
    _c("cierres_controles@caso", CASO, r"una d.cima, contra el " + N + r"%", _desc_cierres("ctrl_bajo_umbral"), 0.5),
    # distance and year
    _c("distancia_banda_max@caso", CASO, r"va de " + NEG + r" a -\d+,\d+ puntos en las tres bandas", _bandas_cercanas("max"), 0.05, "{:.1f}"),
    _c("distancia_banda_min@caso", CASO, r"va de -\d+,\d+ a " + NEG + r" puntos en las tres bandas", _bandas_cercanas("min"), 0.05, "{:.1f}"),
    _c("distancia_1a2@caso", CASO, r"es " + NEG + r" de 1 a 2 km", _banda_brecha("1 a 2"), 0.05, "{:.1f}"),
    _c("distancia_2a5@caso", CASO, r"y " + NEG + r" de 2 a 5 km", _banda_brecha("2 a 5"), 0.05, "{:.1f}"),
    _c("distancia_anillo_rinde@caso", CASO, r"rinden " + DEC + r" puntos m.s que los de 2 a 5 km", _desc_anillo_abs, 0.05, "{:.1f}"),
    _c("distancia_cabecera_anillo@caso", CASO, r"contra el anillo la brecha del mes 1 es " + NEG + r" puntos", _desc_cabecera, 0.05, "{:.1f}"),
    _c("distancia_cabecera_2a5@caso", CASO, r"m.s negativa que los " + NEG + r" contra 2 a 5 km", _desc_ref_k1, 0.05, "{:.1f}"),
    # the yearly bar of 2026 is shown as data; what is said about a rise is the pre-registered test (pipeline.carga_anual)
    _c("anio_2026@caso", CASO, r"La barra de 2026 \(" + N + r" puntos menos, a.o en curso\)", _brecha_anio(2026)),
    _c("carga_anual_d@caso", CASO, r"2026 menos 2021 a 2024 da " + SIG + r" puntos \(IC 95% por bloques de 5 km", _carga_anual("d"), 0.05,
       "{:.1f}"),
    _c("carga_anual_ic_bajo@caso", CASO, r"puntos \(IC 95% por bloques de 5 km: " + SIG + r" a -?\d+,\d+\): no firme",
       _carga_anual("ic_bajo", veredicto="no firme"), 0.05, "{:.1f}"),
    _c("carga_anual_ic_alto@caso", CASO, r"puntos \(IC 95% por bloques de 5 km: -?\d+,\d+ a " + SIG + r"\): no firme",
       _carga_anual("ic_alto", veredicto="no firme"), 0.05, "{:.1f}"),
    # falsification tests
    _c("fechas_falsas_min@caso", CASO, r"va de " + NEG + r" a \d+,\d+ puntos y todos", _fechas_falsas("min"), 0.05, "{:.1f}"),
    _c("fechas_falsas_max@caso", CASO, r"va de -\d+,\d+ a " + DEC + r" puntos y todos", _fechas_falsas("max"), 0.05, "{:.1f}"),
    _c("permutaciones@caso", CASO, r"Con " + N + r" permutaciones", _permutaciones),
    _c("permutadas_min@caso", CASO, r"la brecha va de " + NEG + r" a -\d+,\d+ puntos \(media", _permutacion("minimo"), 0.05, "{:.1f}"),
    _c("permutadas_max@caso", CASO, r"la brecha va de -\d+,\d+ a " + NEG + r" puntos \(media", _permutacion("maximo"), 0.05, "{:.1f}"),
    _c("permutadas_media@caso", CASO, r"\(media " + NEG + r"\)", _permutacion("media"), 0.05, "{:.1f}"),
    _c("permutadas_real@caso", CASO, r"contra " + NEG + r" la real", _permutacion("brecha_real"), 0.05, "{:.1f}"),
    _c("holdout_eje_entrenamiento@caso", CASO, r"eventos viejos da (\d+) grados", _holdout_eje("Eje de entrenamiento")),
    _c("holdout_eje_prueba@caso", CASO, r"y con los nuevos (\d+)\.", _holdout_eje("Eje ajustado en la prueba")),
    # what did not work
    _c("eje_cuenca@caso", CASO, r"de la cuenca es de (\d+) grados", _cuenca("eje_grados")),
    _c("eje_ic_bajo@caso", CASO, r"\(IC de (\d+) a \d+\)", _cuenca("ic_bajo")),
    _c("eje_ic_alto@caso", CASO, r"\(IC de \d+ a (\d+)\)", _cuenca("ic_alto")),
    _c("shmax@caso", CASO, r"SHmax publicado, de " + DEC + r" grados", _shmax, 0.05, "{:.1f}", wh=False),
    _c("costo_r2@caso", CASO, r"su R2 es " + NEG + r" contra", _costo_cv_r2("modelo"), 0.005, "{:.2f}"),
    _c("costo_r2_media_area@caso", CASO, r"contra " + DEC + r" de predecir la media", _costo_cv_r2("media_area"), 0.005, "{:.2f}"),
    # test count (runs pytest --collect-only)
    _c("tests@readme", R, r"hay (\d+) tests", _n_tests, 0, wh=False, lento=True),
]


# Numeros de README.md que son parte de una definicion y no un resultado: cada uno es una frase, no un numero suelto.
README_DEFINICIONALES: tuple[str, ...] = (
    r"datos a septiembre de 2026",
    r"cohorte 2017",
    r"cohorte 2025",
    r"de 12 meses",
    r"al mes 12",
    r"a menos de 1 km",
    r"within 1 km",
    r"a 2 a 5 km",
    r"2 to 5 km away",
    r"[Aa] los 6 meses",
    r"By month 6",
    r"meses 0 a 6",
    r"cierre a 6 meses",
    r"cierre al mes 6",
    r"\bmes 1\b",
    r"\bmes 0\b",
    r"\bmes -1\b",
    r"bloques de 5 km",
    r"IC 95%",
    r"R2",
    r"por cada 0,1 de fracción",
    r"congelada el 2026-11-18 con los datos hasta 2026-09",
    r"Suba de la brecha en 2026",
    r"2026 menos 2021 a 2024",
    r"con 2025 y 2026 juntos",
    r"eventos cercanos de 2026",
    r"bajo el 90% de su trayectoria",
    r"hacen falta 100 eventos cercanos",
    r"quiere decir menos de 5 puntos",
    r"con 80% de potencia",
    r"m3 de petróleo",
    r"m3 por evento",
    r"Python 3\.13",
    r"Vaca Muerta en 4D",
    r"la cuenca en 3D",
)

# Numeros de la pagina de limites que son parte de una definicion y no un resultado: cada uno es una frase, no un numero suelto.
LIMITES_DEFINICIONALES: tuple[str, ...] = (
    r"bloques espaciales de 5 km",
    r"IC 95%",
    r"\bmes 1\b",
    r"\bmes 6\b",
    r"a los 6 meses",
    r"meses 2 a 4",
    r"\b2 a 5 km\b",
    r"\b5 a 10 km\b",
    r"\b2 a 10 km\b",
    r"menos de 2 km",
    r"menos de 0,5 km",
    r"cuadrados de 2 km",
    r"80% de potencia",
    r"efecto de 0,2",
    r"al menos 50 eventos cercanos",
)

RESUMEN_DEFINICIONALES: tuple[str, ...] = (
    r"padre en el mes 1",
    r"a menos de 1 km",
    r"controles a 2 a 5 km",
    r"padres de 6 a 11 meses",
    r"padres de 48 meses",
    r"intervalo del 95%",
    r"A los 6 meses",
    r"en los meses 0 a 6",
    r"con 80% de potencia",
    r"Un efecto de 0,2",
    r"m3 de petróleo",
)

CASO_DEFINICIONALES: tuple[str, ...] = (
    r"deferral of months 0 to 6",
    r"## 1\. La pregunta",
    r"## 2\. Los datos",
    r"## 3\. El método",
    r"## 4\. El resultado",
    r"## 5\. Lo que dijeron",
    r"## 6\. Lo que no funcionó",
    r"## 7\. Qué cambiaría",
    r"## 8\. Cómo verificarlo",
    r"1\. Un evento",
    r"2\. Cada pozo",
    r"3\. La brecha",
    r"4\. Los intervalos",
    r"5\. Se mira",
    r"6\. Pruebas corridas",
    r"k = 0",
    r"intervalos de 95%",
    r"intervalo de 95%",
    r"IC 95% por bloques",
    r"IC 95%:",
    r"[Bb]recha del mes 1",
    r"Al mes 1",
    r"en el mes 6",
    r"A los 6 meses",
    r"meses 0 a 6",
    r"meses -3 a -1",
    r"meses -3, -2 y -1",
    r"meses -6 a -4",
    r"a 12 meses",
    r"a 24 meses",
    r"menos de 1 km",
    r"de 1 a 2 km",
    r"2 a 5 km",
    r"anillo de 5 a 10 km",
    r"bloques( espaciales)? de 5 km",
    r"sección 4",
    r"sección 5",
    r"La barra de 2026",
    r"2026 menos 2021 a 2024",
    r"no cruza -10",
    r"su R2 es",
    r"\| Mes 1,",
    r"\| Mes -1 previo",
)


def numeros_sin_fijar(fichero: str, definicionales: tuple[str, ...], raiz: Path | None = None,
                      claims: list[Claim] | None = None) -> list[str]:
    """Numeros de un documento que ninguna verificacion fija: ni dentro del grupo capturado por la primera coincidencia de un
    claim sobre ese fichero, ni dentro de una coincidencia (todas) de una regex de `definicionales`. Un numero es una cifra con
    puntos de miles, coma decimal, signo y % opcionales; el texto entre comillas invertidas se salta. Devuelve los numeros tal
    como estan escritos, en orden de aparicion."""
    raiz = ROOT if raiz is None else raiz
    claims = CLAIMS if claims is None else claims
    texto = (raiz / fichero).read_text(encoding="utf-8")
    texto = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), texto)
    fijos: list[tuple[int, int]] = []
    for c in claims:
        if c.fichero == fichero:
            m = re.search(c.patron, texto, re.S)
            if m:
                fijos.append(m.span(1))
    for patron in definicionales:
        fijos += [m.span() for m in re.finditer(patron, texto, re.S)]
    return [m.group(0) for m in re.finditer(r"-?\d+(?:\.\d{3})*(?:,\d+)?%?", texto)
            if not any(a < m.end() and m.start() < b for a, b in fijos)]


def imprimir(res: list[Resultado]) -> None:
    w = max(len(r.claim.id) for r in res)
    print(f"{'claim':<{w}}  {'doc':>9}  {'calculado':>10}  estado")
    for r in res:
        doc = fmt(r.claim, r.documento) if r.documento is not None else "-"
        calc = fmt(r.claim, r.calculado) if r.calculado is not None else "-"
        extra = f"  {r.detalle}" if r.detalle and r.estado != "PASS" else ""
        print(f"{r.claim.id:<{w}}  {doc:>9}  {calc:>10}  {r.estado}{extra}")
    n = {e: sum(1 for r in res if r.estado == e) for e in ("PASS", "FAIL", "SKIP")}
    print(f"\n{n['PASS']} PASS, {n['FAIL']} FAIL, {n['SKIP']} SKIP")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    res = verificar(lentos="--rapido" not in argv)
    imprimir(res)
    return 1 if any(r.estado == "FAIL" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
