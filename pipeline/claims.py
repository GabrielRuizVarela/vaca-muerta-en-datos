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
from dataclasses import dataclass, replace
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
             "quince": 15, "dieciséis": 16, "dieciseis": 16, "veinte": 20,
             "mitad": 50, "half": 50}  # "mitad" y "half": la mitad de una parte, en por ciento


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
    tabla: str = ""                   # SKIP when this table is not in the warehouse (written by a step that runs only with a flag)


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
    if c.tabla and not con.execute("select count(*) from information_schema.tables where table_name = ?", [c.tabla]).fetchone()[0]:
        return Resultado(c, "SKIP", detalle=f"sin la tabla {c.tabla} en el warehouse")
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


def _desc_adit(col: str, variante: str = "con_cerrados", k: int = 1) -> Callable:
    """Share (percent) from the additive decomposition at month k (1 unless stated)."""
    return lambda con: 100 * con.execute(f"select {col} from mart_descomposicion_aditiva where variante = ? and k = ?", [variante, k]).fetchone()[0]


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


def _c(id, fichero, patron, fn, tol=0.5, formato="{:,.0f}", wh=True, lento=False, almacen="vm", opcional=False, tabla="") -> Claim:
    return Claim(id, fichero, patron, fn, tol, formato, wh, lento, almacen, opcional, tabla)


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
    """Recuento del mapa base de la pagina 3D, leido de data/base_mapa.json (no necesita ningun warehouse)."""
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


def _claims_relieve_fino() -> list[Claim]:
    """Finer relief of the core on the base map page, read from data/base_relieve_nucleo.json (no warehouse needed)."""
    def f(clave):
        def g(_con):
            from pipeline.base_mapa import leer_fino, recuentos_fino
            return float(recuentos_fino(leer_fino())[clave])
        return g
    fina, cerca = r"segunda grilla fina de ", r"segundos de arco \(cerca de "
    pats = [("cols", fina + N + r" por [\d.]+ celdas"), ("filas", fina + r"[\d.]+ por " + N + r" celdas"),
            ("paso_seg", fina + r"[\d.]+ por [\d.]+ celdas de " + N + r" segundos de arco"),
            ("m_este", fina + r"[^\n]*?" + cerca + N + r" m hacia el este"),
            ("m_sur", fina + r"[^\n]*?" + cerca + r"\d+ m hacia el este y " + N + r" m hacia el sur"),
            ("cota_min", fina + r"[^\n]*?hacia el sur\), con cotas de " + N + r" a "),
            ("cota_max", fina + r"[^\n]*?hacia el sur\), con cotas de [\d.]+ a " + N + r" m\. "),
            ("margen_pct", r"junto a cada borde, el " + N + r" % del lado del recorte")]
    return [_c(f"rf_{k}@mapa_base", W_MB, pat, f(k), 0, wh=False) for k, pat in pats]


def _ex(*ruta, por: float = 1) -> Callable:
    """Absolute value of one accuracy measurement of the Mundo page, read from data/exactitud.json."""
    def f(_con):
        from pipeline.base_mapa import leer_exactitud
        v = leer_exactitud()
        for k in ruta:
            v = v[k]
        return abs(float(v)) * por
    return f


def _claims_exactitud() -> list[Claim]:
    """Every number of the accuracy section of the base map page against data/exactitud.json (no warehouse needed)."""
    def lugares(grupo, filas):
        out = []
        for i, f in enumerate(filas):
            n = re.escape(f["nombre"])
            out.append((f"{grupo}{i}_fuente", n + r": " + N + r" m en la fuente", ("relieve", grupo, i, "fuente_m"), {}))
            out.append((f"{grupo}{i}_pagina", n + r": [\d.]+ m en la fuente y " + N + r" m en la página",
                        ("relieve", grupo, i, "pagina_m"), {}))
        return out

    from pipeline.base_mapa import leer_exactitud
    e = leer_exactitud()
    if e is None:
        return []
    uno, dos = {"tol": 0.05, "formato": "{:.1f}"}, {"tol": 0.005, "formato": "{:.2f}"}
    lado = r" % (?:largas|cortas) "
    pats = [
        ("pagina_pozos", r"sobre la página publicada \(datos a [\d-]+, " + N + r" pozos\)", ("pagina", "pozos"), {}),
        ("pozos_n", r"en las bocas de los " + N + r" pozos que caen dentro", ("relieve", "pozos", "n"), {}),
        ("pozos_mediana", r"segundo de arco en " + DEC + r" m de mediana", ("relieve", "pozos", "mediana"), uno),
        ("pozos_p99", r"de mediana; el 99 % queda a " + DEC + r" m o menos", ("relieve", "pozos", "p99"), uno),
        ("pozos_max", r"y el peor caso es de " + DEC + r" m\. Con la grilla", ("relieve", "pozos", "max"), uno),
        ("hoja_mediana", r"en esos mismos pozos, la mediana era de " + DEC + r" m", ("relieve", "solo_hoja", "mediana"), uno),
        ("hoja_p99", r"el 99 % quedaba a " + DEC + r" m o menos", ("relieve", "solo_hoja", "p99"), uno),
        ("nucleo_n", r"En los " + N + r" pozos donde rige entero", ("relieve", "pozos_nucleo", "n"), {}),
        ("nucleo_mediana", r"relieve fino, la mediana es de " + DEC + r" m", ("relieve", "pozos_nucleo", "mediana"), uno),
        ("nucleo_p99", r"la mediana es de \d+,\d+ m, el 99 % queda a " + DEC + r" m o menos",
         ("relieve", "pozos_nucleo", "p99"), uno),
        ("nucleo_max", r"y el peor caso es de " + DEC + r" m; en esos", ("relieve", "pozos_nucleo", "max"), uno),
        ("hoja_nucleo_mediana", r"hoja sola eran " + DEC + r" m y ", ("relieve", "solo_hoja_nucleo", "mediana"), uno),
        ("hoja_nucleo_p99", r"hoja sola eran \d+,\d+ m y " + DEC + r" m\.", ("relieve", "solo_hoja_nucleo", "p99"), uno),
        *lugares("cumbres", e["relieve"]["cumbres"]), *lugares("niveles", e["relieve"]["niveles"]),
        ("ind_n", r"muestra fija de " + N + r" bocas", ("relieve", "independiente", "n"), {}),
        ("ind_fuente_mediana", r"la fuente da " + DEC + r" m (?:más|menos) que el modelo",
         ("relieve", "independiente", "fuente_mediana"), uno),
        ("ind_fuente_max", r"diferencia máxima de " + DEC + r" m; la página",
         ("relieve", "independiente", "fuente_max"), uno),
        ("ind_pagina_mediana", r"; la página da " + DEC + r" m (?:más|menos), con",
         ("relieve", "independiente", "pagina_mediana"), uno),
        ("ind_pagina_max", r"con una máxima de " + DEC + r" m\.", ("relieve", "independiente", "pagina_max"), uno),
        ("pads", r"centrados en " + N + r" locaciones", ("imagen", "pads"), {}),
        ("meses_antes", r"al menos " + N + r" meses antes de la imagen", ("imagen", "meses_antes"), {}),
        ("pico_sd", r", de " + DEC + r" desvíos sobre el entorno", ("imagen", "pico_sd"), uno),
        ("este_m", r"su centro queda a " + N + r" m al (?:este|oeste)", ("imagen", "este_m"), {}),
        ("norte_m", r"m al (?:este|oeste) y " + N + r" m al (?:norte|sur) de la posición", ("imagen", "norte_m"), {}),
        ("pixel_este", r"un píxel mide " + N + r" por \d+ m", ("imagen", "pixel_m", 0), {}),
        ("pixel_sur", r"un píxel mide \d+ por " + N + r" m\. El", ("imagen", "pixel_m", 1), {}),
        ("claros_pct", r"m\. El " + N + r" % de las locaciones", ("imagen", "claros_pct"), {}),
        ("control_km", r"La misma pila corrida " + N + r" km al este", ("imagen", "control_km"), {}),
        ("control_sd", r"llega a " + DEC + r" desvíos", ("imagen", "control_sd"), uno),
        ("agua_iou", r"imagen en el " + DEC + r" % \(intersección", ("imagen", "agua_iou"), dict(uno, por=100)),
        ("busca_px", r"corrimiento de hasta " + N + r" píxeles", ("imagen", "busca_px"), {}),
        ("km_grado_lat", r"cada grado de latitud como " + DEC + r" km", ("dibujo", "km_grado"), dos),
        ("km_grado_lon", r"cada grado de longitud como " + DEC + r" km", ("dibujo", "km_grado"), dos),
        ("ns_pct", r"las distancias norte-sur un " + DEC + r" %", ("dibujo", "ns_pct"), dos),
        ("eo_nucleo_norte", r"quedan un " + DEC + lado + r"en el borde norte del núcleo", ("dibujo", "eo_nucleo_pct", 0), uno),
        ("eo_nucleo_sur", r"del núcleo y un " + DEC + lado + r"en el borde sur", ("dibujo", "eo_nucleo_pct", 1), uno),
        ("eo_hoja_norte", r"bordes de la hoja, un " + DEC + lado + r"al norte", ("dibujo", "eo_hoja_pct", 0), uno),
        ("eo_hoja_sur", r"al norte y un " + DEC + lado + r"al sur", ("dibujo", "eo_hoja_pct", 1), uno),
        ("medio_seg_este", r"que promedian, cerca de " + N + r" m al este", ("dibujo", "medio_segundo_m", 0), {}),
        ("medio_seg_sur", r"que promedian, cerca de \d+ m al este y " + N + r" m al sur", ("dibujo", "medio_segundo_m", 1), {}),
    ]
    out = []
    for k, pat, ruta, extra in pats:
        extra = dict(extra)
        out.append(_c(f"ex_{k}@mapa_base", W_MB, pat, _ex(*ruta, por=extra.pop("por", 1)), extra.pop("tol", 0),
                      extra.pop("formato", "{:,.0f}"), wh=False))
    return out


def _bf(clave: str) -> Callable:
    """Recuento de la imagen del suelo de la pagina 3D, leido de data/base_foto.json (no necesita ningun warehouse)."""
    def f(_con):
        from pipeline.base_foto import DESTINO, recuentos
        return float(recuentos(json.loads(DESTINO.read_text(encoding="utf-8")))[clave])
    return f


def _claims_base_foto() -> list[Claim]:
    hoja, recorte = r"La hoja entera mide ", r"cubre el núcleo, .{0,120}? Mide "
    pats = [("escenas", r"Es un mosaico de " + N + r" escenas"), ("principal", r": " + N + r" de la órbita principal"),
            ("relleno", r"órbita principal y " + N + r" de la órbita vecina"),
            ("caja_ancho", hoja + N + r" por [\d.]+ píxeles"), ("caja_alto", hoja + r"[\d.]+ por " + N + r" píxeles"),
            ("caja_m_este", hoja + r"[^\n]*?cerca de " + N + r" m hacia el este"),
            ("caja_m_sur", hoja + r"[^\n]*?hacia el este y " + N + r" m hacia el sur"),
            ("nucleo_ancho", recorte + N + r" por [\d.]+ píxeles"), ("nucleo_alto", recorte + r"[\d.]+ por " + N + r" píxeles"),
            ("nucleo_m_este", recorte + r"[^\n]*?cerca de " + N + r" m hacia el este"),
            ("nucleo_m_sur", recorte + r"[^\n]*?hacia el este y " + N + r" m hacia el sur"),
            ("caja_bytes", r"base_foto_caja\.webp`: " + N + r" bytes"),
            ("nucleo_bytes", r"base_foto_nucleo\.webp`: " + N + r" bytes")]
    return [_c(f"bf_{k}@mapa_base", W_MB, pat, _bf(k), 0, wh=False) for k, pat in pats]


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
    out += [_c("fam_readme_k_es@familia", R, r"[Ss]e replica en " + N + r" de \d+ cuencas", k_de, 0, almacen="familia"),
            _c("fam_readme_n_es@familia", R, r"[Ss]e replica en \d+ de " + N + r" cuencas", n_de, 0, almacen="familia"),
            _c("readme_q6_k@familia", R, r"Pasa fuera de Vaca Muerta\?\*\* \*Se replica en " + N + r" de \d+ cuencas", k_de, 0, almacen="familia"),
            _c("readme_q6_n@familia", R, r"Pasa fuera de Vaca Muerta\?\*\* \*Se replica en \d+ de " + N + r" cuencas", n_de, 0, almacen="familia"),
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


W_DIA = "wiki/hallazgos/dia_inicio.md"


def _claims_dia_inicio() -> list[Claim]:
    """Cada cifra de la pagina del dia de inicio como dosis contra pipeline.dia_inicio. Las lineas se arman de
    `dia_inicio.especificacion`, la misma que escribe la pagina, asi que lo impreso y lo verificado no se separan. Los marts de
    Colorado viven en el warehouse de Vaca Muerta y se saltan (tabla) si Colorado no corrio. El veredicto impreso va como su posicion
    en el orden de la regla: una pagina vieja cuyo veredicto ya no es el del mart da otra posicion (FAIL)."""
    from pipeline import dia_inicio as di

    cl = []
    for cuenca in ("", "colorado"):
        pref = "Colorado: " if cuenca else ""
        tabla = di.nombre_tabla("_veredicto", cuenca) if cuenca else ""
        sufijo = cuenca or "vm"
        for clave, (lits, cifras) in di.especificacion(cuenca).items():
            if cuenca and clave in di.CLAVES_SOLO_VM:
                continue
            lits = di._sustituir(lits, pref)
            opc = clave.startswith("pend_op") or clave == "pend_fd"
            for k, (sql, factor, dec) in enumerate(cifras):
                tol = 0 if dec == 0 else 0.5 * 10 ** -dec * 1.001
                cl.append(_c(f"dia_{sufijo}_{clave}_{k}@wiki", W_DIA, _fr(k, *lits),
                             (lambda q, f: lambda con: f * con.execute(q).fetchone()[0])(sql, factor), tol,
                             "{:,.0f}" if dec == 0 else "{:." + str(dec) + "f}", opcional=opc, tabla=tabla))
        # tabla del dia de inicio por operador del hijo: la fila i, sin el nombre (que sale de los datos)
        anc = "\n" + ("###" if cuenca else "##") + " Día de inicio por operador del hijo\n\n"
        cab = ("| Operador del hijo | Eventos cercanos | f0 media | Parte con inicio en los tres primeros días |\n"
               "| --- | ---: | ---: | ---: |\n")
        for i in range(10):
            fila = r"(?:\|[^\n]*\n){" + str(i) + r"}\| [^|\n]+ \| "
            tn = di.nombre_tabla("_operador", cuenca)
            for col, factor, dec in (("eventos", 1.0, 0), ("f0_media", 1.0, 3), ("parte_f0_mayor_09", 100.0, 1)):
                pat = re.escape(anc) + re.escape(cab) + fila + ("" if col == "eventos" else r"[\d.]+ \| ") \
                    + ("" if col != "parte_f0_mayor_09" else r"\d+,\d+ \| ") + f"({NG})" + (" %" if col == "parte_f0_mayor_09" else "")
                q = f"select {col} from {tn} order by eventos desc, operador limit 1 offset {i}"
                cl.append(_c(f"dia_{sufijo}_oper{i}_{col}@wiki", W_DIA, pat,
                             (lambda q, f: lambda con: f * con.execute(q).fetchone()[0])(q, factor),
                             0 if dec == 0 else 0.5 * 10 ** -dec * 1.001, "{:,.0f}" if dec == 0 else "{:." + str(dec) + "f}",
                             opcional=True, tabla=tn))
    orden_vm = {v: i + 1 for i, v in enumerate(di.VEREDICTOS_VM)}
    orden_co = {v: i + 1 for i, v in enumerate(di.ESTADOS_COLORADO)}
    cl.append(_c("dia_vm_veredicto@wiki", W_DIA, r"Veredicto contra la regla fijada \(posición (\d) de " + str(len(di.VEREDICTOS_VM)) + " en el orden",
                 lambda con: orden_vm[con.execute("select veredicto from mart_dia_inicio_veredicto").fetchone()[0]], 0, "{:.0f}"))
    cl.append(_c("dia_colorado_veredicto@wiki", W_DIA, r"Veredicto de Colorado \(posición (\d) de " + str(len(di.ESTADOS_COLORADO)) + r"\)",
                 lambda con: orden_co[con.execute("select veredicto from mart_dia_inicio_colorado_veredicto").fetchone()[0]], 0, "{:.0f}",
                 tabla="mart_dia_inicio_colorado_veredicto"))
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


W_DIAS = "wiki/hallazgos/dias_perdidos.md"


def _claims_dias_perdidos() -> list[Claim]:
    """Numeros de la pagina de dias perdidos contra sus marts: brecha, pruebas B y C, volumen, valor, ensayo y meses cerrados.
    La seccion de Colorado se ancla en "En Colorado ..." y lee los marts _colorado, que se guardan en el warehouse de Vaca Muerta."""
    def _p(prueba: str, est: str, col: str = "valor", por: float = 1.0, cuenca: str = "") -> Callable:
        t = "mart_dias_perdidos" + (f"_{cuenca}" if cuenca else "") + "_prueba"
        return lambda con: por * con.execute(
            f"select {col} from {t} where prueba = '{prueba}' and estadistico = '{est}'").fetchone()[0]

    def _banda(col: str, cuenca: str = "") -> Callable:
        t = "mart_dias_perdidos" + (f"_{cuenca}" if cuenca else "")
        return lambda con: con.execute(f"select {col} from {t} where banda = 'cercano'").fetchone()[0]

    def _co(prueba: str, est: str, col: str = "valor", por: float = 1.0) -> Callable:
        return _p(prueba, est, col, por, "colorado")

    def _cc(*a, tabla: str = "mart_dias_perdidos_colorado_prueba", **k) -> Claim:  # las de Colorado: SKIP sin el mart que leen,
        return _c(*a, tabla=tabla, **k)                                               # que escribe solo run_all --with-colorado

    def _op(operador: str) -> Callable:
        return lambda con: con.execute("select brecha from mart_dias_perdidos_operador where operador = ?", [operador]).fetchone()[0]

    def _valor(con) -> float:
        from pipeline.decision import valor_indicativo
        return valor_indicativo(_banda("brecha_vol_m3")(con) * _p("A", "eventos_cercanos_12m")(con), 60, 0.10, 12)["costo_de_diferir"] / 1e6

    out = [
        _c("dias_brecha@wiki", W_DIAS, r"pierde " + DEC + r" días más que un control", _p("A", "brecha_dias"), 0.05, "{:.1f}"),
        _c("dias_brecha_ic_bajo@wiki", W_DIAS, r"días más que un control \(IC 95% " + SD + r" a", _p("A", "brecha_dias", "ic_bajo"), 0.05, "{:.1f}"),
        _c("dias_brecha_ic_alto@wiki", W_DIAS, r"días más que un control \(IC 95% -?\d+,\d+ a " + SD + r";", _p("A", "brecha_dias", "ic_alto"), 0.05, "{:.1f}"),
        _c("dias_n_cercanos@wiki", W_DIAS, N + r" eventos cercanos\)", _p("A", "brecha_dias", "n"), 0),
        _c("dias_b_diferencia@wiki", W_DIAS, r"en la segunda mitad: " + SD + r" días", _p("B", "diferencia_dias"), 0.05, "{:.1f}"),
        _c("dias_b_ic_bajo@wiki", W_DIAS, r"en la segunda mitad: -?\d+,\d+ días \(IC 95% " + SD + r" a", _p("B", "diferencia_dias", "ic_bajo"), 0.05, "{:.1f}"),
        _c("dias_b_ic_alto@wiki", W_DIAS, r"en la segunda mitad: -?\d+,\d+ días \(IC 95% -?\d+,\d+ a " + SD + r";",
           _p("B", "diferencia_dias", "ic_alto"), 0.05, "{:.1f}"),
        _c("dias_b_operadores@wiki", W_DIAS, r"; " + N + r" operadores; veredicto", _p("B", "diferencia_dias", "n"), 0),
        _c("dias_c_pendiente@wiki", W_DIAS, r"Pendiente: " + SD + r" puntos logarítmicos", _p("C", "pendiente", por=100), 0.05, "{:.1f}"),
        _c("dias_c_cota@wiki", W_DIAS, r"mayor beneficio compatible con el dato es " + SD + r" puntos", _p("C", "pendiente", "ic_alto", 100), 0.05, "{:.1f}"),
        _c("dias_c_mde@wiki", W_DIAS, r"efecto mínimo detectable: " + DEC + r" puntos", _p("C", "mde", por=100), 0.05, "{:.1f}"),
        _c("dias_volumen@wiki", W_DIAS, r"equivalen a " + N + r" m3 de petróleo por evento cercano", _banda("brecha_vol_m3")),
        _c("dias_eventos_12m@wiki", W_DIAS, r"por los " + N + r" eventos cercanos de los últimos 12 meses", _p("A", "eventos_cercanos_12m"), 0),
        _c("dias_valor_60_10_12@wiki", W_DIAS, r"\| 60 \| 10% \| \d+,\d+ \| " + DEC + r" \|", _valor, 0.05, "{:.1f}"),
        _c("dias_ensayo_10@wiki", W_DIAS, r"hacen falta [\d.]+, " + N + r" y [\d.]+ eventos por rama", _p("E", "n_por_rama_10"), 0),
        _c("dias_cerrado_cercano@wiki", W_DIAS, r"El " + DEC + r"% de los eventos cercanos tiene al menos un mes",
           _p("F", "parte_con_mes_cerrado_cercano", por=100), 0.05, "{:.1f}"),
        _c("dias_ypf@wiki", W_DIAS, r"\| YPF \| [\d.]+ \| [\d.]+ \| " + SD + r" \|", _op("YPF"), 0.05, "{:.1f}"),
        _c("dias_vista@wiki", W_DIAS, r"\| Vista \| [\d.]+ \| [\d.]+ \| " + SD + r" \|", _op("Vista"), 0.05, "{:.1f}"),
        _cc("dias_co_lectura@wiki", W_DIAS, r"misma regla: brecha de días, [^(]+\(" + SD + r" días, IC 95%", _co("A", "brecha_dias"), 0.05, "{:.1f}"),
    ]
    a, b, c = r"En Colorado la brecha es de ", r"En Colorado la diferencia entre el grupo alto y el bajo en la segunda mitad es de ", \
        r"En Colorado la pendiente es de "
    ic = r"-?\d+,\d+ días \(IC 95% "
    for k, cabeza, prueba, est, por, uni in (("a", a, "A", "brecha_dias", 1, " días"), ("b", b, "B", "diferencia_dias", 1, " días"),
                                            ("c", c, "C", "pendiente", 100, " puntos")):
        icc = ic.replace("días", "puntos logarítmicos por cada 10 días") if k == "c" else ic
        out += [
            _cc(f"dias_co_{k}@wiki", W_DIAS, cabeza + SD + uni, _co(prueba, est, por=por), 0.05, "{:.1f}"),
            _cc(f"dias_co_{k}_ic_bajo@wiki", W_DIAS, cabeza + icc + SD + r" a", _co(prueba, est, "ic_bajo", por), 0.05, "{:.1f}"),
            _cc(f"dias_co_{k}_ic_alto@wiki", W_DIAS, cabeza + icc + r"-?\d+,\d+ a " + SD + r";", _co(prueba, est, "ic_alto", por), 0.05, "{:.1f}"),
            _cc(f"dias_co_{k}_n@wiki", W_DIAS, cabeza + icc + r"-?\d+,\d+ a -?\d+,\d+; " + N + " ", _co(prueba, est, "n"), 0),
        ]
    return out + [
        _cc("dias_co_c_cota@wiki", W_DIAS, c + r"[^\n]*?El mayor beneficio compatible con el dato es " + SD + r" puntos",
           _co("C", "pendiente", "ic_alto", 100), 0.05, "{:.1f}"),
        _cc("dias_co_volumen@wiki", W_DIAS, r"En Colorado los días de más equivalen a " + N + r" m3", _banda("brecha_vol_m3", "colorado"),
            tabla="mart_dias_perdidos_colorado"),
        _cc("dias_co_sigma@wiki", W_DIAS, r"con el desvío de sus residuos de C \(" + DEC + r"\)", _co("C", "sigma"), 0.005, "{:.2f}"),
        _cc("dias_co_ensayo_10@wiki", W_DIAS, r"se necesitan [\d.]+, " + N + r" y [\d.]+ eventos por rama", _co("E", "n_por_rama_10"), 0),
        _cc("dias_co_crestone@wiki", W_DIAS, r"\| CRESTONE PEAK RESOURCES OPERATING LLC \| [\d.]+ \| [\d.]+ \| " + SD + r" \|",
           lambda con: con.execute("select brecha from mart_dias_perdidos_colorado_operador where operador = ?",
                                   ["CRESTONE PEAK RESOURCES OPERATING LLC"]).fetchone()[0], 0.05, "{:.1f}",
            tabla="mart_dias_perdidos_colorado_operador"),
    ]


W_GOLPES = "wiki/hallazgos/golpes_mismo_mes.md"


def _claims_golpes_mismo_mes() -> list[Claim]:
    """Numeros de la pagina de golpes en el mismo mes contra sus marts: la tabla del modelo (las dos cuencas), la muestra, la
    tabla por k, la lectura y el diagnostico. Las de Colorado SKIP sin los marts _colorado (solo run_all --with-colorado)."""
    def _p(prueba: str, est: str, col: str = "valor", cuenca: str = "") -> Callable:
        t = "mart_golpes_mismo_mes" + (f"_{cuenca}" if cuenca else "") + "_prueba"
        return lambda con: con.execute(f"select {col} from {t} where prueba = ? and estadistico = ?", [prueba, est]).fetchone()[0]

    def _k(grupo: str, col: str, cuenca: str = "") -> Callable:
        t = "mart_golpes_mismo_mes" + (f"_{cuenca}" if cuenca else "")
        return lambda con: con.execute(f"select {col} from {t} where grupo = ?", [grupo]).fetchone()[0]

    TCO = "mart_golpes_mismo_mes_colorado_prueba"
    ENT = r"(-?[\d.]+)"    # entero con signo y puntos de miles
    num = r"-?[\d.]+(?:,\d+)?"
    out: list[Claim] = []
    filas = (("principal", "Principal", "a", r"a: costo fijo del mes \(días de base\)", 1),
             ("principal", "Principal", "b", r"b: costo de cada hijo \(días de base\)", 1),
             ("principal", "Principal", "a_mas_b", r"a \+ b: un mes con un solo hijo \(días de base\)", 1),
             ("principal", "Principal", "phi", r"φ = a / \(a \+ b\)", 2),
             *(("principal", "Principal", f"rho_{k}", f"ρ con {k} hijos \\(juntos sobre separados\\)", 2) for k in (2, 3, 4, 6)),
             ("S1", "S1, volumen", "a_m3", r"a \(m3\)", 0),
             ("S1", "S1, volumen", "b_m3", r"b \(m3\)", 0),
             ("S1", "S1, volumen", "a_mas_b_m3", r"a \+ b \(m3\)", 0),
             ("S1", "S1, volumen", "phi_m3", r"φ en volumen", 2),
             ("S2", "S2, sin aislamiento", "a", r"a \(días de base\)", 1),
             ("S2", "S2, sin aislamiento", "b", r"b \(días de base\)", 1),
             ("S2", "S2, sin aislamiento", "a_mas_b", r"a \+ b \(días de base\)", 1),
             ("S2", "S2, sin aislamiento", "phi", r"φ", 2))
    for prueba, etq, est, desc, dec in filas:
        cap, tol, fmt_ = (ENT, 0.5, "{:,.0f}") if dec == 0 else (SD, 0.5 * 10 ** -dec, f"{{:.{dec}f}}")
        cab = r"\| " + etq + r" \| " + desc + r" \| "
        for sufijo, cuenca, salto in (("", "", ""), ("_co", "colorado", num + r" \| " + num + r" a " + num + r" \| ")):
            kw = {"tabla": TCO} if cuenca else {}
            base = f"golpes{sufijo}_{prueba.lower()}_{est}@wiki"
            out += [_c(base, W_GOLPES, cab + salto + cap + r" \| ", _p(prueba, est, cuenca=cuenca), tol, fmt_, **kw),
                    _c(base.replace("@", "_ic_bajo@"), W_GOLPES, cab + salto + num + r" \| " + cap + r" a ",
                       _p(prueba, est, "ic_bajo", cuenca), tol, fmt_, **kw),
                    _c(base.replace("@", "_ic_alto@"), W_GOLPES, cab + salto + num + r" \| " + num + r" a " + cap + r" \|",
                       _p(prueba, est, "ic_alto", cuenca), tol, fmt_, **kw)]
    conteos = (("conteo", "cercanos", r"Eventos cercanos \(hijo más cercano a menos de 1 km\)"),
               ("conteo", "aislados_con_ventana", r"Aislados con la ventana completa \(muestra principal\)"),
               ("conteo", "un_hijo_aislados", r"De ellos, con un solo hijo en el mes"),
               ("conteo", "cercanos_con_ventana", r"Con la ventana completa \(muestra de S2\)"),
               ("conteo", "controles_con_ventana", r"Controles con la ventana completa \(índice de control\)"),
               ("principal", "pads", r"Pads hijo de la muestra principal"),
               ("principal", "padres", r"Padres de la muestra principal"),
               ("principal", "valores_k_con_n_k", r"Valores de k con al menos \d+ eventos"))
    for prueba, est, desc in conteos:
        out += [_c(f"golpes_n_{est}@wiki", W_GOLPES, r"\| " + desc + r" \| " + N + r" \|", _p(prueba, est), 0),
                _c(f"golpes_co_n_{est}@wiki", W_GOLPES, r"\| " + desc + r" \| [\d.]+ \| " + N + r" \|", _p(prueba, est, cuenca="colorado"),
                   0, tabla=TCO)]
    co_k = r"## Colorado \(confirmatoria\).*?"  # la tabla por k de Colorado es la segunda; se ancla en su seccion
    for n, grupo in enumerate(("1", "2", "3", "4", "5 a 6", "7 o más")):
        fila = r"\| " + grupo + r" \| [\d.]+ \| [\d.]+ \| \d+,\d \| "
        for sufijo, cuenca, ancla in (("", "", ""), ("_co", "colorado", co_k)):
            kw = {"tabla": "mart_golpes_mismo_mes_colorado"} if cuenca else {}
            out += [_c(f"golpes{sufijo}_k{n + 1}_perdida@wiki", W_GOLPES, ancla + fila + SD + r" \|", _k(grupo, "perdida", cuenca), 0.05,
                       "{:.1f}", **kw),
                    _c(f"golpes{sufijo}_k{n + 1}_por_hijo@wiki", W_GOLPES, ancla + fila + num + r" \| " + num + r" a " + num + r" \| " + SD + r" \|",
                       _k(grupo, "por_hijo", cuenca), 0.05, "{:.1f}", **kw),
                    _c(f"golpes{sufijo}_k{n + 1}_eventos@wiki", W_GOLPES, ancla + r"\| " + grupo + r" \| " + N + r" \|", _k(grupo, "n", cuenca),
                       0, **kw)]
    lect = r"Vaca Muerta \(regla informada\): \*\*[^*]+\*\*\. [^\n]*?Un mes con un solo hijo, a \+ b = "
    out += [
        _c("golpes_lectura_ab@wiki", W_GOLPES, lect + SD + r" días", _p("principal", "a_mas_b"), 0.05, "{:.1f}"),
        _c("golpes_lectura_ab_ic_bajo@wiki", W_GOLPES, lect + r"-?\d+,\d+ días de producción de base \(IC 95% " + SD + r" a",
           _p("principal", "a_mas_b", "ic_bajo"), 0.05, "{:.1f}"),
        _c("golpes_lectura_eventos@wiki", W_GOLPES, lect + r"[^;]+; " + N + r" meses de golpe aislados", _p("principal", "phi", "n"), 0),
        _c("golpes_lectura_pads@wiki", W_GOLPES, lect + r"[^;]+; [\d.]+ meses de golpe aislados, de " + N + r" pads hijo",
           _p("principal", "pads"), 0),
        _c("golpes_desvio@wiki", W_GOLPES, r"el desvío es de " + DEC + r" días", _p("diagnostico", "desvio_perdida"), 0.05, "{:.1f}",
           opcional=True),
        _c("golpes_media@wiki", W_GOLPES, r"días contra una media de " + SD, _p("principal", "perdida_media"), 0.05, "{:.1f}", opcional=True),
        _c("golpes_mediana@wiki", W_GOLPES, r"y una mediana de " + SD + r"\.", _p("diagnostico", "perdida_mediana"), 0.05, "{:.1f}",
           opcional=True),
        _c("golpes_b_puntual@wiki", W_GOLPES, r"con la estimación puntual \(a = -?\d+,\d+ y b = " + SD + r" días de base\)",
           _p("principal", "b"), 0.05, "{:.1f}", opcional=True),
        _c("golpes_descartadas@wiki", W_GOLPES, r"a \+ b de cero o menos: " + N + r" en Vaca Muerta", _p("principal", "descartadas"), 0),
        _c("golpes_co_descartadas@wiki", W_GOLPES, r"a \+ b de cero o menos: [\d.]+ en Vaca Muerta y " + N + r" en Colorado",
           _p("principal", "descartadas", cuenca="colorado"), 0, tabla=TCO),
        _c("golpes_error_phi@wiki", W_GOLPES, r"Error de φ \(desvío de las repeticiones\) en Vaca Muerta: " + DEC, _p("principal", "error_phi"),
           0.005, "{:.2f}"),
        _c("golpes_reps@wiki", W_GOLPES, r"por pads hijo \(" + N + r" repeticiones\)", _p("principal", "descartadas", "n"), 0),
        _c("golpes_diag_control@wiki", W_GOLPES, r"esa mediana tiene media " + SD + r" días", _p("diagnostico", "perdida_media_control"),
           0.05, "{:.1f}"),
        _c("golpes_diag_ab@wiki", W_GOLPES, r"Contra esa media, a \+ b sería " + SD + r" días",
           _p("diagnostico", "a_mas_b_contra_media_control"), 0.05, "{:.1f}"),
        _c("golpes_diag_ab_ic_bajo@wiki", W_GOLPES, r"Contra esa media, a \+ b sería -?\d+,\d+ días \(IC 95% " + SD + r" a",
           _p("diagnostico", "a_mas_b_contra_media_control", "ic_bajo"), 0.05, "{:.1f}"),
        _c("golpes_co_lectura_ab@wiki", W_GOLPES, r"Colorado \(confirmatoria, misma regla\): \*\*[^*]+\*\*\. [^\n]*?Un mes con un solo hijo, "
           r"a \+ b = " + SD + r" días", _p("principal", "a_mas_b", cuenca="colorado"), 0.05, "{:.1f}", tabla=TCO),
    ]
    return out


W_PADRE = "wiki/hallazgos/golpes_mismo_padre.md"


def _claims_golpes_mismo_padre() -> list[Claim]:
    """Numeros de la pagina de golpes en el mismo mes con el padre como su propio control contra sus marts: la tabla del modelo
    (las dos cuencas), la muestra, la tabla por k, la lectura y la fila del README. Las de Colorado SKIP sin los marts _colorado
    (solo run_all --with-colorado); las filas de phi y rho SKIP cuando la celda es n/d (a + b de cero o menos)."""
    def _p(prueba: str, est: str, col: str = "valor", cuenca: str = "") -> Callable:
        t = "mart_golpes_mismo_padre" + (f"_{cuenca}" if cuenca else "") + "_prueba"
        return lambda con: con.execute(f"select {col} from {t} where prueba = ? and estadistico = ?", [prueba, est]).fetchone()[0]

    def _k(grupo: str, col: str, cuenca: str = "") -> Callable:
        t = "mart_golpes_mismo_padre" + (f"_{cuenca}" if cuenca else "")
        return lambda con: con.execute(f"select {col} from {t} where grupo = ?", [grupo]).fetchone()[0]

    TCO = "mart_golpes_mismo_padre_colorado_prueba"
    ENT = r"(-?[\d.]+)"
    DM = r"(-?[\d.]+,\d+)"           # decimal con signo y puntos de miles
    num = r"-?[\d.]+(?:,\d+)?"
    out: list[Claim] = []
    from pipeline.golpes_mismo_padre import FILAS_MODELO
    for prueba, etq, est, desc, dec in FILAS_MODELO:
        cap, tol, fmt_ = (ENT, 0.5, "{:,.0f}") if dec == 0 else (DM, 0.5 * 10 ** -dec, f"{{:.{dec}f}}")
        cab = r"\| " + re.escape(etq) + r" \| " + re.escape(desc) + r" \| "
        vm = r"(?:" + num + r" \| " + num + r" a " + num + r"|n/d \| ) \| "   # la celda de Vaca Muerta, con su IC o n/d
        pend = est.startswith(("phi", "rho"))
        for sufijo, cuenca, salto in (("", "", ""), ("_co", "colorado", vm)):
            kw = {"tabla": TCO} if cuenca else {}
            base = f"golpes_padre{sufijo}_{prueba.lower()}_{est}@wiki"
            out += [_c(base, W_PADRE, cab + salto + cap + r" \| ", _p(prueba, est, cuenca=cuenca), tol, fmt_, opcional=pend, **kw),
                    _c(base.replace("@", "_ic_bajo@"), W_PADRE, cab + salto + num + r" \| " + cap + r" a ",
                       _p(prueba, est, "ic_bajo", cuenca), tol, fmt_, opcional=pend, **kw),
                    _c(base.replace("@", "_ic_alto@"), W_PADRE, cab + salto + num + r" \| " + num + r" a " + cap + r" \|",
                       _p(prueba, est, "ic_alto", cuenca), tol, fmt_, opcional=pend, **kw)]
    conteos = (("conteo", "aislados_con_ventana", r"Meses de golpe aislados con la ventana completa \(muestra de partida\)"),
               ("conteo", "padres_partida", r"Padres de la muestra de partida"),
               ("conteo", "padres_2_meses", r"De ellos, con dos o más meses de golpe"),
               ("conteo", "padres_k_distinto", r"De ellos, con distinta cantidad de hijos entre esos meses"),
               ("conteo", "meses_restringida", r"Meses de golpe de la muestra restringida"),
               ("principal", "padres", r"Padres de la muestra restringida"),
               ("principal", "pads", r"Pads del padre de la muestra restringida"),
               ("principal", "valores_k", r"Valores distintos de k"),
               ("principal", "meses_por_padre_media", r"Meses de golpe por padre \(media\)"))
    for prueba, est, desc in conteos:
        out += [_c(f"golpes_padre_n_{est}@wiki", W_PADRE, r"\| " + desc + r" \| " + N + r" \|", _p(prueba, est), 0.5),
                _c(f"golpes_padre_co_n_{est}@wiki", W_PADRE, r"\| " + desc + r" \| [\d.]+ \| " + N + r" \|",
                   _p(prueba, est, cuenca="colorado"), 0.5, tabla=TCO)]
    for cuenca, tabla, ancla in (("", {}, r""), ("colorado", {"tabla": TCO}, r"\d{4}-\d\d \| ")):
        u = r"Último mes de producción \| " + ancla
        sufijo = "_co" if cuenca else ""
        out += [_c(f"golpes_padre{sufijo}_ultimo_anio@wiki", W_PADRE, u + r"(\d{4})-\d\d",
                   lambda con, c=cuenca: 2000 + (_p("conteo", "ultimo_mes_indice", cuenca=c)(con) - 1) // 12, 0, "{:.0f}", **tabla),
                _c(f"golpes_padre{sufijo}_ultimo_mes@wiki", W_PADRE, u + r"\d{4}-(\d\d)",
                   lambda con, c=cuenca: (_p("conteo", "ultimo_mes_indice", cuenca=c)(con) - 1) % 12 + 1, 0, "{:.0f}", **tabla)]
    co_k = r"## Colorado \(confirmatoria\).*?"
    for n, grupo in enumerate(("1", "2", "3", "4", "5 a 6", "7 o más")):
        fila = r"\| " + grupo + r" \| [\d.]+ \| [\d.]+ \| (?:\d+,\d|) \| "
        for sufijo, cuenca, ancla in (("", "", r"\A(?:(?!## Colorado \(confirmatoria\)).)*?"), ("_co", "colorado", co_k)):
            kw = {"tabla": "mart_golpes_mismo_padre_colorado"} if cuenca else {}
            out += [_c(f"golpes_padre{sufijo}_k{n + 1}_meses@wiki", W_PADRE, ancla + r"\| " + grupo + r" \| " + N + r" \|",
                       _k(grupo, "n", cuenca), 0, **kw),
                    _c(f"golpes_padre{sufijo}_k{n + 1}_perdida@wiki", W_PADRE, ancla + fila + SD + r" \|", _k(grupo, "perdida_media", cuenca),
                       0.05, "{:.1f}", opcional=True, **kw),
                    _c(f"golpes_padre{sufijo}_k{n + 1}_intra@wiki", W_PADRE, ancla + fila + r"-?\d+,\d+ \| " + SD + r" \|",
                       _k(grupo, "desvio_intra_padre", cuenca), 0.05, "{:.1f}", opcional=True, **kw)]
    vm_l = r"Vaca Muerta \(regla informada\): \*\*[^*]+\*\*\. [^\n]*?"
    co_l = r"Colorado \(confirmatoria, misma regla\): \*\*[^*]+\*\*\. [^\n]*?"
    for sufijo, cuenca, l_, kw in (("", "", vm_l, {}), ("_co", "colorado", co_l, {"tabla": TCO})):
        out += [_c(f"golpes_padre{sufijo}_lectura_partida@wiki", W_PADRE, l_ + r"muestra de partida tiene " + N + r" meses de golpe",
                   _p("conteo", "aislados_con_ventana", cuenca=cuenca), 0.5, opcional=True, **kw),
                _c(f"golpes_padre{sufijo}_lectura_padres_partida@wiki", W_PADRE, l_ + r"aislados con la ventana completa, de " + N + r" padres",
                   _p("conteo", "padres_partida", cuenca=cuenca), 0.5, opcional=True, **kw),
                _c(f"golpes_padre{sufijo}_lectura_2_meses@wiki", W_PADRE, l_ + r"padres; " + N + r" de esos padres tienen",
                   _p("conteo", "padres_2_meses", cuenca=cuenca), 0.5, opcional=True, **kw),
                _c(f"golpes_padre{sufijo}_lectura_k_distinto@wiki", W_PADRE, l_ + r"de esos padres tienen 2 meses de golpe o más y " + N + r" tienen además",
                   _p("conteo", "padres_k_distinto", cuenca=cuenca), 0.5, opcional=True, **kw),
                _c(f"golpes_padre{sufijo}_lectura_meses@wiki", W_PADRE, l_ + r"la muestra restringida queda en " + N + r" meses de golpe",
                   _p("conteo", "meses_restringida", cuenca=cuenca), 0.5, opcional=True, **kw)]
    b = r"El costo por hijo es b = "
    out += [_c("golpes_padre_lectura_b@wiki", W_PADRE, b + DM + r" días", _p("principal", "b"), 0.05, "{:.1f}", opcional=True),
            _c("golpes_padre_lectura_b_ic_bajo@wiki", W_PADRE, b + r"-?[\d.]+,\d+ días de producción de base \(IC 95% " + DM + r" a",
               _p("principal", "b", "ic_bajo"), 0.05, "{:.1f}", opcional=True),
            _c("golpes_padre_lectura_b_ic_alto@wiki", W_PADRE, b + r"-?[\d.]+,\d+ días de producción de base \(IC 95% -?[\d.]+,\d+ a " + DM + r"\)",
               _p("principal", "b", "ic_alto"), 0.05, "{:.1f}", opcional=True),
            _c("golpes_padre_lectura_b_negativas@wiki", W_PADRE, r"; " + N + r" de [\d.]+ repeticiones del bootstrap dieron b menor que cero",
               _p("principal", "b_negativas"), 0.5, opcional=True),
            _c("golpes_padre_lectura_83_b@wiki", W_PADRE, r"sin efecto fijo de padre: b = " + DM + r" días", _p("agrupado83", "b"), 0.05,
               "{:.1f}", opcional=True),
            _c("golpes_padre_lectura_83_b_ic_bajo@wiki", W_PADRE, r"sin efecto fijo de padre: b = -?[\d.]+,\d+ días de producción de base "
               r"\(IC 95% " + DM + r" a", _p("agrupado83", "b", "ic_bajo"), 0.05, "{:.1f}", opcional=True),
            _c("golpes_padre_descartadas@wiki", W_PADRE, r"a \+ b de cero o menos: " + N + r" en Vaca Muerta", _p("principal", "descartadas"), 0.5),
            _c("golpes_padre_co_descartadas@wiki", W_PADRE, r"a \+ b de cero o menos: [\d.]+ en Vaca Muerta y " + N + r" en Colorado",
               _p("principal", "descartadas", cuenca="colorado"), 0.5, tabla=TCO),
            _c("golpes_padre_error_phi@wiki", W_PADRE, r"Error de φ \(desvío de las repeticiones\) en Vaca Muerta: " + DEC,
               _p("principal", "error_phi"), 0.005, "{:.2f}"),
            _c("golpes_padre_reps@wiki", W_PADRE, r"por pads del padre \(" + N + r" repeticiones\)", _p("principal", "descartadas", "n"), 0.5)]
    # README: la fila de resultados
    fila = r"con el padre como su propio control [^|]*\| [^|]*?: "
    out += [_c("golpes_padre_readme_padres@readme", R, fila + N + r" padres y [\d.]+ meses de golpe en Vaca Muerta", _p("principal", "padres"), 0.5),
            _c("golpes_padre_readme_meses@readme", R, fila + r"[\d.]+ padres y " + N + r" meses de golpe en Vaca Muerta",
               _p("principal", "meses"), 0.5),
            _c("golpes_padre_readme_co_padres@readme", R, fila + r"[\d.]+ padres y [\d.]+ meses de golpe en Vaca Muerta y " + N
               + r" padres y [\d.]+ meses en Colorado", _p("principal", "padres", cuenca="colorado"), 0.5, tabla=TCO),
            _c("golpes_padre_readme_co_meses@readme", R, fila + r"[\d.]+ padres y [\d.]+ meses de golpe en Vaca Muerta y [\d.]+ padres y "
               + N + r" meses en Colorado", _p("principal", "meses", cuenca="colorado"), 0.5, tabla=TCO)]
    return out


W_HPAD = "wiki/hallazgos/hijo_pad.md"


def _claims_hijo_pad() -> list[Claim]:
    """Cada cifra de la pagina del lado del hijo dentro del pad contra sus marts: el resumen, la cobertura, la muestra, el cuadro por
    ano, los coeficientes de todos los modelos, el equilibrio y la fila del README."""
    from pipeline.hijo_pad import ANIO_MAX, ANIO_MIN, EQUILIBRIO_TXT, MODELOS_TXT, cobertura_rama

    def cf(modelo: str, tipo: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(
            f"select {col} from mart_hijo_pad_coef where modelo = '{modelo}' and exposicion = '{tipo}'").fetchone()[0]

    def rs(clave: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select valor from mart_hijo_pad_resumen where clave = '{clave}'").fetchone()[0]

    def cob(k: int) -> Callable:
        return lambda con: cobertura_rama(con)[k]

    cl: list[Claim] = []
    d1, d0 = "{:.1f}", "{:,.0f}"

    def frase(clave, lits, fns, tols, fmts, opcional=False):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"hpad_{clave}_{k}@wiki", W_HPAD, _fr(k, *lits), fn, tol, fmt, opcional=opcional))

    P = ("principal", "real")
    C = ("principal", "control")
    frase("virgen", ["Rendimiento de los hijos sin exposición a 12 meses: mediana de ", " bbl por metro de rama, sobre ", " hijos."],
          [rs("virgen_mediana_bbl_m"), rs("virgenes_n")], [0.05, 0], [d1, d0])
    frase("principal", ["Pendiente dentro del pad: ", " bbl por metro de rama por cada 100 bbl por metro de exposición (IC 95%: ", " a ",
                        "), o sea ", "% del rendimiento virgen (IC 95%: ", "% a ", "%), sobre ", " hijos de ", " pads."],
          [cf(*P, "coef"), cf(*P, "ic_bajo"), cf(*P, "ic_alto"), cf(*P, "pct_del_virgen"), cf(*P, "pct_ic_bajo"), cf(*P, "pct_ic_alto"),
           cf(*P, "n"), cf(*P, "pads")], [0.05] * 6 + [0, 0], [d1] * 6 + [d0] * 2)
    frase("control", ["Control negativo, la misma pendiente con la exposición de pozos posteriores a la ventana del hijo: ",
                      " bbl por metro de rama (IC 95%: ", " a ", ")."],
          [cf(*C, "coef"), cf(*C, "ic_bajo"), cf(*C, "ic_alto")], [0.05] * 3, [d1] * 3)
    frase("cota", ["Cota superior de la pérdida (el extremo bajo del IC, no una estimación): ",
                   " bbl por metro de rama por cada 100 bbl por metro de exposición, o ",
                   "% del rendimiento virgen; a la mediana de las exposiciones positivas, ", " bbl por metro, son ", " bbl por metro de rama."],
          [rs("cota_bbl_m"), rs("cota_pct"), rs("expo_positiva_mediana_bbl_m"), rs("cota_a_mediana_bbl_m")], [0.05, 0.05, 0.5, 0.05],
          [d1, d1, d0, d1], opcional=True)
    frase("pads", ["Pads que informan: ", " de ", " tienen una dispersión de la exposición de al menos 50 bbl por metro entre sus hijos "
                   "(mediana de la dispersión: ", " bbl por metro); ", "% de los hijos no tienen exposición."],
          [rs("pads_informativos"), rs("pads"), rs("dispersion_mediana_bbl_m"), rs("parte_E_cero", 100.0)], [0, 0, 0.5, 0.5],
          [d0] * 4)
    frase("cobertura", ["Las ramas medidas cubren entre ", "% y ", f"% de los hijos horizontales fracturados de {ANIO_MIN} a {ANIO_MAX}, "
                        "pero solo ", "% de los de 2024 y ", "% de los de 2025"],
          [cob(0), cob(1), cob(2), cob(3)], [0.5] * 4, [d0] * 4)
    # la muestra: un conteo por paso y, desde el 6, los pads
    for paso in range(1, 9):
        cl.append(_c(f"hpad_paso{paso}_hijos@wiki", W_HPAD, rf"- Paso {paso}, [^:\n]*: {N} hijos",
                     lambda con, k=paso: con.execute("select hijos from mart_hijo_pad_muestra where paso = ?", [k]).fetchone()[0], 0))
        if paso >= 6:
            cl.append(_c(f"hpad_paso{paso}_pads@wiki", W_HPAD, rf"- Paso {paso}, [^:\n]*: [\d.]+ hijos en {N} pads",
                         lambda con, k=paso: con.execute("select pads from mart_hijo_pad_muestra where paso = ?", [k]).fetchone()[0], 0))
    for anio in range(ANIO_MIN, ANIO_MAX + 1):
        for k, col in enumerate(("hijos", "pads", "hijos_en_pads_informativos")):
            cl.append(_c(f"hpad_anio{anio}_{col}@wiki", W_HPAD, rf"\| {anio} \| " + r"[\d.]+ \| " * k + N + r" \|",
                         lambda con, a=anio, c=col: con.execute(f"select {c} from mart_hijo_pad_anio where anio = ?", [a]).fetchone()[0], 0))
    # coeficientes de todos los modelos, cada uno con su control negativo
    for modelo, etiqueta in MODELOS_TXT.items():
        for tipo, rot in (("real", "real"), ("control", "control negativo")):
            cab = r"\| " + re.escape(etiqueta) + r" \| " + rot + r" \| "
            base = f"hpad_{modelo}_{tipo}"
            cl += [_c(f"{base}_coef@wiki", W_HPAD, cab + f"({NG})" + r" \|", cf(modelo, tipo, "coef"), 0.005, "{:.2f}"),
                   _c(f"{base}_ic_bajo@wiki", W_HPAD, cab + NG + r" \| " + f"({NG})" + r" a ", cf(modelo, tipo, "ic_bajo"), 0.005, "{:.2f}"),
                   _c(f"{base}_ic_alto@wiki", W_HPAD, cab + NG + r" \| " + NG + r" a " + f"({NG})" + r" \|", cf(modelo, tipo, "ic_alto"),
                      0.005, "{:.2f}"),
                   _c(f"{base}_pct@wiki", W_HPAD, cab + NG + r" \| " + NG + r" a " + NG + r" \| " + f"({NG})" + r"% \|",
                      cf(modelo, tipo, "pct_del_virgen"), 0.05, d1)]
            for j, col in enumerate(("n", "pads", "pads_informativos")):
                cl.append(_c(f"{base}_{col}@wiki", W_HPAD,
                             cab + NG + r" \| " + NG + r" a " + NG + r" \| " + NG + r"% \| " + r"[\d.]+ \| " * j + N + r" \|",
                             cf(modelo, tipo, col), 0, d0))
    for variable, rot, dec in EQUILIBRIO_TXT:
        cab = r"\| " + re.escape(rot) + r" \| "
        tol, fmt = 0.5 * 10 ** -dec, f"{{:.{dec}f}}"
        for col, patron in (("coef", cab + f"({NG})" + r" \|"), ("ic_bajo", cab + NG + r" \| " + f"({NG})" + r" a "),
                            ("ic_alto", cab + NG + r" \| " + NG + r" a " + f"({NG})" + r" \|")):
            cl.append(_c(f"hpad_eq_{variable}_{col}@wiki", W_HPAD, patron,
                         lambda con, v=variable, c=col: con.execute(
                             f"select {c} from mart_hijo_pad_equilibrio where variable = '{v}'").fetchone()[0], tol, fmt))
    # README: la fila de resultados
    fila = r"Lado del hijo dentro del pad \([^|]*\| pendiente dentro del pad: "
    cl += [_c("hpad_readme_coef@readme", R, fila + f"({NG})" + r" bbl por metro de rama por cada 100", cf(*P, "coef"), 0.05, d1),
           _c("hpad_readme_n@readme", R, fila + NG + r" bbl por metro de rama por cada 100 bbl por metro de exposición previa, sobre "
              + N + r" hijos", cf(*P, "n"), 0, d0),
           _c("hpad_readme_pads@readme", R, fila + NG + r" bbl por metro de rama por cada 100 bbl por metro de exposición previa, sobre [\d.]+ hijos de "
              + N + r" pads", cf(*P, "pads"), 0, d0),
           _c("hpad_readme_ic_bajo@readme", R, fila + r"[^|]*\| IC 95%: (" + NG + r") a ", cf(*P, "ic_bajo"), 0.05, d1),
           _c("hpad_readme_ic_alto@readme", R, fila + r"[^|]*\| IC 95%: " + NG + r" a (" + NG + r");", cf(*P, "ic_alto"), 0.05, d1),
           _c("hpad_readme_cota@readme", R, fila + r"[^|]*\| IC 95%: [^|]*?cota superior de la pérdida: (" + NG + r")% del rendimiento",
              rs("cota_pct"), 0.05, d1),
           _c("hpad_readme_control@readme", R, fila + r"[^|]*\| [^|]*?el control negativo da (" + NG + r") \(IC 95%", cf(*C, "coef"), 0.05, d1),
           _c("hpad_readme_control_bajo@readme", R, fila + r"[^|]*\| [^|]*?el control negativo da " + NG + r" \(IC 95%: (" + NG + r") a ",
              cf(*C, "ic_bajo"), 0.05, d1),
           _c("hpad_readme_control_alto@readme", R, fila + r"[^|]*\| [^|]*?el control negativo da " + NG + r" \(IC 95%: " + NG + r" a ("
              + NG + r")\)", cf(*C, "ic_alto"), 0.05, d1)]
    return cl


W_CAL = "wiki/hallazgos/calendario_golpes.md"


def _claims_calendario_golpes() -> list[Claim]:
    """Numeros de la pagina del calendario de golpes contra sus marts: la lectura, el backtest, el arrepentimiento y la fila del README."""
    def _p(prueba: str, est: str, col: str = "valor") -> Callable:
        return lambda con: con.execute(f"select {col} from mart_calendario_prueba where prueba = ? and estadistico = ?",
                                       [prueba, est]).fetchone()[0]

    from pipeline.calendario_golpes import DELTA_MESES
    DM = r"(-?[\d.]+,\d+)"
    out: list[Claim] = []
    lec = r"Backtest: \*\*[^*]+\*\*\. [^\n]*?"
    out += [_c("calendario_entrena_n@wiki", W_CAL, lec + r"El entrenamiento de 2023 tiene " + N + r" eventos aislados",
               _p("entrena", "n"), 0.5),
            _c("calendario_entrena_pads@wiki", W_CAL, lec + r"eventos aislados \(" + N + r" pads del padre", _p("entrena", "pads"), 0.5),
            _c("calendario_entrena_valores_k@wiki", W_CAL, lec + r"pads del padre y " + N + r" valores de k", _p("entrena", "valores_k"), 0.5),
            _c("calendario_prueba_n@wiki", W_CAL, lec + r"La prueba de 2024 a 2026 tiene " + N + r" eventos en", _p("backtest", "n_prueba"), 0.5),
            _c("calendario_prueba_pads@wiki", W_CAL, lec + r"eventos en " + N + r" pads, que alcanzan", _p("backtest", "pads_prueba"), 0.5)]
    lec2 = r"- (?:Descriptivo\. )?"
    out += [_c("calendario_completa_a_sin_acotar@wiki", W_CAL, lec2 + r"Con #86[^\n]*?el ajuste es a = " + DM,
               _p("completa", "a_sin_acotar"), 0.05, "{:.1f}"),
            _c("calendario_completa_b_sin_acotar@wiki", W_CAL, lec2 + r"Con #86[^\n]*?el ajuste es a = -?[\d.]+,\d+ y b = " + DM,
               _p("completa", "b_sin_acotar"), 0.05, "{:.1f}"),
            _c("calendario_completa_a_acotado@wiki", W_CAL, lec2 + r"Con #86[^\n]*?la media de la pérdida, " + DM + r" días",
               _p("completa", "a"), 0.05, "{:.1f}"),
            _c("calendario_d@wiki", W_CAL, lec2 + r"Fuera de muestra, con el ajuste de 2023[^\n]*?: D = " + DM,
               _p("backtest", "d"), 0.0005, "{:.3f}"),
            _c("calendario_d_ic_bajo@wiki", W_CAL, lec2 + r"Fuera de muestra[^\n]*?: D = -?[\d.]+,\d+ \(IC 95% " + DM + r" a",
               _p("backtest", "d", "ic_bajo"), 0.005, "{:.2f}"),
            _c("calendario_d_ic_alto@wiki", W_CAL, lec2 + r"Fuera de muestra[^\n]*?: D = -?[\d.]+,\d+ \(IC 95% -?[\d.]+,\d+ a " + DM + r"\)",
               _p("backtest", "d", "ic_alto"), 0.005, "{:.2f}"),
            _c("calendario_sk_fijo@wiki", W_CAL, lec2 + r"Fuera de muestra[^\n]*?con habilidad " + DM + r" contra",
               _p("backtest", "sk_fijo"), 0.0005, "{:.3f}"),
            _c("calendario_sk_aditivo@wiki", W_CAL, lec2 + r"Fuera de muestra[^\n]*?contra " + DM + r" del aditivo",
               _p("backtest", "sk_aditivo"), 0.0005, "{:.3f}"),
            _c("calendario_arrep_dias_d3@wiki", W_CAL, lec2 + r"El arrepentimiento del calendario observado[^\n]*?toda la muestra: " + N + r" \(",
               _p("completa_arrepentimiento", f"dias_fijo_mas_hijo_d{DELTA_MESES}"), 0.5),
            _c("calendario_arrep_ic_alto@wiki", W_CAL, lec2 + r"El arrepentimiento del calendario observado[^\n]*?toda la muestra: [\d.]+ \(\d+ a " + N + r"\)",
               _p("completa_arrepentimiento", f"dias_fijo_mas_hijo_d{DELTA_MESES}", "ic_alto"), 0.5),
            _c("calendario_noaislados_test@wiki", W_CAL, r"el " + N + r"% \(2024 a 2026\)",
               lambda con: 100 * _p("entrena", "programa_test_noaislados")(con), 0.5),
            _c("calendario_noaislados_completa@wiki", W_CAL, r"y el " + N + r"% \(toda la muestra\)",
               lambda con: 100 * _p("entrena", "programa_completa_noaislados")(con), 0.5)]
    # README: la fila de resultados
    fila = r"Calendario de golpes: matrices de costo[^\n]*?"
    out += [_c("calendario_readme_n@readme", R, fila + r"predice peor que el aditivo, en la estimación puntual, en " + N + r" eventos aislados", _p("backtest", "n_prueba"), 0.5),
            _c("calendario_readme_d@readme", R, fila + r"D = " + DM, _p("backtest", "d"), 0.005, "{:.2f}"),
            _c("calendario_readme_d_ic_bajo@readme", R, fila + r"IC 95% por pads del padre: " + DM + r" a", _p("backtest", "d", "ic_bajo"), 0.005, "{:.2f}"),
            _c("calendario_readme_d_ic_alto@readme", R, fila + r"IC 95% por pads del padre: -?[\d.]+,\d+ a " + DM + r";",
               _p("backtest", "d", "ic_alto"), 0.005, "{:.2f}"),
            _c("calendario_readme_arrep@readme", R, fila + r"cota superior: " + N + r" días de base",
               _p("completa_arrepentimiento", f"dias_fijo_mas_hijo_d{DELTA_MESES}"), 0.5),
            _c("calendario_readme_arrep_ic_bajo@readme", R, fila + r"días de base \(IC 95%: (\d+) a",
               _p("completa_arrepentimiento", f"dias_fijo_mas_hijo_d{DELTA_MESES}", "ic_bajo"), 0.5),
            _c("calendario_readme_arrep_ic_alto@readme", R, fila + r"días de base \(IC 95%: \d+ a " + N + r"\)",
               _p("completa_arrepentimiento", f"dias_fijo_mas_hijo_d{DELTA_MESES}", "ic_alto"), 0.5),
            _c("calendario_readme_entrena@readme", R, fila + r"y hay " + N + r", así que", _p("entrena", "n"), 0.5)]
    return out


W_TRAY = "wiki/hallazgos/trayectorias.md"


def _claims_trayectorias() -> list[Claim]:
    """Numeros de la pagina de trayectorias contra sus marts. Las partes de pares se recalculan desde mart_trayectoria_par
    y no desde la tabla cruzada que usa la pagina."""
    def _r(clave: str) -> Callable:
        return lambda con: con.execute("select valor from mart_trayectoria_resumen where clave = ?", [clave]).fetchone()[0]

    def _cob(col: str, nivel: str = "hijo", desde: int = 0, hasta: int = 9999) -> Callable:
        return lambda con: con.execute(f"select sum({col}) from mart_trayectoria_cobertura where nivel = ? and anio >= ? "
                                       "and anio < ?", [nivel, desde, hasta]).fetchone()[0]

    def _pad(col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_trayectoria_banda where banda = 'mismo_pad'").fetchone()[0]

    def _parte(km: str, rama: str) -> Callable:
        return lambda con: 100 * con.execute(f"select avg(({rama})::int) from mart_trayectoria_par where {km}").fetchone()[0]

    # posición del padre respecto de la rama del hijo: una celda por banda de superficie y posición, más el total de
    # la banda. El patrón ancla en el encabezado de la tabla, porque la de cruces tiene las mismas etiquetas de fila.
    BANDA_POS = {"cercano": "b.km < 1", "intermedio": "b.km >= 1 and b.km < 2", "control": "b.km >= 2 and b.km < 5"}
    ETIQUETA_POS = {"cercano": r"cercano \(menos de 1 km\)", "intermedio": r"intermedio \(1 a 2 km\)",
                    "control": r"control \(2 a 5 km\)"}
    CABECERA_POS = r"\| Superficie \| costado \| punta \| mixto \| Pares \|"

    def _pos(banda: str, posicion: str | None) -> Callable:
        cond = BANDA_POS[banda] + (f" and p.posicion = '{posicion}'" if posicion else "")
        return lambda con: con.execute(
            "select count(*) from mart_par_rama p "
            "join mart_trayectoria_par b "
            f"on b.hijo = p.hijo and b.padre = p.padre where {cond}").fetchone()[0]

    def _patron_pos(banda: str, columna: int, total: bool = False) -> str:
        """La celda `columna` de la fila de la banda: salta las celdas anteriores de la misma fila."""
        return (CABECERA_POS + r"[\s\S]*?\| " + ETIQUETA_POS[banda] + r" \| "
                + r"[\d.]+ \([^|]*\) \| " * columna + N + (r" \|" if total else r" \("))

    cl = [
        _c("tray_pozos@wiki", W_TRAY, r"La fuente trae " + N + r" pozos", _r("pozos_fuente"), 0),
        _c("tray_filas@wiki", W_TRAY, r"pozos en " + N + r" filas", _r("filas"), 0),
        _c("tray_con_rama@wiki", W_TRAY, r"filas\. " + N + r" de los [\d.]+ pozos shale", _r("con_rama"), 0),
        _c("tray_hijos_h_medidos@wiki", W_TRAY, r"Tienen la rama medida " + N + r" de los", _cob("horizontales_medidos"), 0),
        _c("tray_hijos_h@wiki", W_TRAY, r"de los " + N + r" hijos horizontales", _cob("horizontales"), 0),
        _c("tray_pares_1km_medidos@wiki", W_TRAY, r"\) y " + N + r" de los [\d.]+ pares a menos de 1 km", _cob("medidos", "par_1km"), 0),
        _c("tray_pares_1km@wiki", W_TRAY, r"de los " + N + r" pares a menos de 1 km en superficie", _cob("total", "par_1km"), 0),
        _c("tray_antes_en_fuente@wiki", W_TRAY, r"antes de 2024, " + N + r" de", _cob("horizontales_en_fuente", hasta=2024), 0),
        _c("tray_antes@wiki", W_TRAY, r"antes de 2024, [\d.]+ de " + N + r" están", _cob("horizontales", hasta=2024), 0),
        _c("tray_desde_en_fuente@wiki", W_TRAY, r"desde 2024, " + N + r" de", _cob("horizontales_en_fuente", desde=2024), 0),
        _c("tray_desde@wiki", W_TRAY, r"desde 2024, [\d.]+ de " + N + r" \(", _cob("horizontales", desde=2024), 0),
        _c("tray_pad_m_min@wiki", W_TRAY, r"menor distancia entre ramas es " + N + r" m", _pad("m_min_mediana")),
        _c("tray_pad_separacion@wiki", W_TRAY, r"rama del hijo es " + N + r" m:", _pad("m_mediana_mediana")),
        _c("tray_cercano_lejos@wiki", W_TRAY, r"el " + N + r"% tiene las ramas a 1 km o más", _parte("km < 1", "m_min >= 1000")),
        _c("tray_control_cerca@wiki", W_TRAY, r"de control \(2 a 5 km\), el " + N + r"%", _parte("km >= 2", "m_min < 1000")),
        _c("tray_intermedio_cerca@wiki", W_TRAY, r"de los intermedios \(1 a 2 km\), el " + N + r"%",
           _parte("km >= 1 and km < 2", "m_min < 1000")),
        _c("tray_spearman@wiki", W_TRAY, r"menor distancia entre ramas es " + DEC + r" \(", _r("spearman_km_m_min"), 0.005, "{:.2f}"),
        _c("tray_pares_medidos@wiki", W_TRAY, r"\(" + N + r" pares con las dos ramas medidas\)",
           lambda con: con.execute("select count(*) from mart_trayectoria_par").fetchone()[0], 0),
    ]
    for banda in ("cercano", "intermedio", "control"):
        for columna, posicion in enumerate(("costado", "punta", "mixto")):
            cl.append(_c(f"tray_posicion_{banda}_{posicion}@wiki", W_TRAY, _patron_pos(banda, columna),
                         _pos(banda, posicion), 0))
        cl.append(_c(f"tray_posicion_{banda}_total@wiki", W_TRAY, _patron_pos(banda, 3, total=True), _pos(banda, None), 0))
    return cl


W_ALCANCE = "wiki/hallazgos/alcance_rama.md"


W_DGEO = "wiki/hallazgos/dosis_geometria.md"


def _claims_dosis_geometria() -> list[Claim]:
    """Numeros de la pagina de dosis con la geometria de las ramas (la puerta de potencia) contra sus marts y el README."""
    nombres = {"arena_etapa": "arena por etapa", "arena_rama": "arena por metro de rama",
               "presion": "presión máxima de tratamiento", "deplecion": "depleción del padre"}

    def _num(v) -> float:
        """Con el veredicto "sin muestra" los marts de la puerta quedan sin cifras: el claim falla con calculado nan, no se cae."""
        return float("nan") if v is None else v

    def _pot(res: str, var: str, col: str) -> Callable:
        def fn(con):
            r = con.execute(f"select {col} from mart_dosis_geometria_potencia where resultado = '{res}' "
                            f"and variable = '{nombres[var]}'").fetchone()
            return float("nan") if r is None else _num(r[0])
        return fn

    def _puerta(col: str) -> Callable:
        return lambda con: _num(con.execute(f"select {col} from mart_dosis_geometria_puerta").fetchone()[0])

    def _muestra(res: str, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_dosis_geometria_muestra where resultado = '{res}'").fetchone()[0]

    def _cob(desde: int, hasta: int) -> Callable:
        return lambda con: 100 * con.execute(
            "select sum(horizontales_medidos) / sum(horizontales) from mart_trayectoria_cobertura "
            "where nivel = 'hijo' and anio between ? and ?", [desde, hasta]).fetchone()[0]

    def _cob_anio(f: str) -> Callable:
        return lambda con: con.execute(
            f"select {f}(r) from (select 100 * sum(horizontales_medidos) / sum(horizontales) as r from mart_trayectoria_cobertura "
            "where nivel = 'hijo' and anio between 2016 and 2023 group by anio)").fetchone()[0]

    cl = []
    for var, nom in nombres.items():
        fila = r"\| " + re.escape(nom) + r" \| \d+,\d+ \| "
        cl.append(_c(f"dgeo_mde_{var}@wiki", W_DGEO, fila + DEC + r" \| \d+,\d+ \|", _pot("A", var, "mde80_desvios"), 0.0006, "{:.3f}"))
        cl.append(_c(f"dgeo_mde_holm_{var}@wiki", W_DGEO, fila + r"\d+,\d+ \| " + DEC + r" \|", _pot("A", var, "mde80_holm_desvios"),
                     0.0006, "{:.3f}"))
    cl += [
        _c("dgeo_menor_holm@wiki", W_DGEO, r"el menor MDE80 de Holm del resultado A es de " + DEC + r" desvíos de la caída por desvío de la dosis: medir",
           _puerta("mde_menor_holm"), 0.006, "{:.2f}"),
        _c("dgeo_mayor_holm@wiki", W_DGEO, r"el mayor es de " + DEC + r", contra la referencia", _puerta("mde_mayor_holm"), 0.006, "{:.2f}"),
        _c("dgeo_n_A@wiki", W_DGEO, r"### Resultado A \(n = " + N + r", pads = \d+\)", _muestra("A", "caso_completo"), 0.5),
        _c("dgeo_pads_A@wiki", W_DGEO, r"### Resultado A \(n = [\d.]+, pads = " + N + r"\)", _muestra("A", "pads"), 0.5),
        _c("dgeo_con_par@wiki", W_DGEO, r"Muestra, resultado A: [\d.]+ eventos de dosis, " + N + r" con el par", _muestra("A", "con_par"), 0.5),
        _c("dgeo_cercano_rama@wiki", W_DGEO, r"Muestra, resultado A: [\d.]+ eventos de dosis, [\d.]+ con el par \(hijo, padre\) medido entre ramas, "
           + N + r" cercanos", _muestra("A", "cercano_rama"), 0.5),
        _c("dgeo_readme_menor@readme", R, r"el menor MDE80 con Holm es de " + DEC + r" desvíos de la caída por desvío de la dosis, contra 0,22",
           _puerta("mde_menor_holm"), 0.006, "{:.2f}"),
        _c("dgeo_readme_mayor@readme", R, r"el mayor MDE80 con Holm es de " + DEC + r"; la simulación", _puerta("mde_mayor_holm"), 0.006, "{:.2f}"),
        _c("dgeo_readme_n@readme", R, r"entre ramas \(" + N + r" eventos de \d+ pads hijo\)", _muestra("A", "caso_completo"), 0.5),
        _c("dgeo_readme_pads@readme", R, r"entre ramas \([\d.]+ eventos de " + N + r" pads hijo\)", _muestra("A", "pads"), 0.5),
        _c("dgeo_cob_2016_2023@wiki", W_DGEO, r"\((\d+)% en conjunto\)", _cob(2016, 2023), 0.5),
        _c("dgeo_cob_min@wiki", W_DGEO, r"cubren el (\d+) a \d+% de los hijos fracturados de 2016 a 2023", _cob_anio("min"), 0.5),
        _c("dgeo_cob_max@wiki", W_DGEO, r"cubren el \d+ a (\d+)% de los hijos fracturados de 2016 a 2023", _cob_anio("max"), 0.5),
        _c("dgeo_cob_2024@wiki", W_DGEO, r"pero solo el (\d+)% de los de 2024", _cob(2024, 2024), 0.5),
        _c("dgeo_cob_2025@wiki", W_DGEO, r"y el (\d+)% de los de 2025", _cob(2025, 2025), 0.5),
        _c("dgeo_readme_cob_2016_2023@readme", R, r"no dice que no haya dosis y respuesta\. La muestra es sobre todo de hijos fracturados de 2016 a 2023: las trayectorias cubren el (\d+)% de esos hijos", _cob(2016, 2023), 0.5),
        _c("dgeo_readme_cob_2024@readme", R, r"no dice que no haya dosis y respuesta\. La muestra es sobre todo de hijos fracturados de 2016 a 2023: las trayectorias cubren el \d+% de esos hijos pero el (\d+)% de los de 2024", _cob(2024, 2024), 0.5),
        _c("dgeo_readme_cob_2025@readme", R, r"no dice que no haya dosis y respuesta\. La muestra es sobre todo de hijos fracturados de 2016 a 2023: las trayectorias cubren el \d+% de esos hijos pero el \d+% de los de 2024 y el (\d+)% de los de 2025", _cob(2025, 2025), 0.5),
        _c("dgeo_readme_limites@readme", R, r"no pasó \(el menor MDE80 con Holm es de " + DEC + r" desvíos contra 0,22\)",
           _puerta("mde_menor_holm"), 0.006, "{:.2f}"),
    ]
    # las frases de la pagina dependen del veredicto de la puerta: con otro veredicto el texto cambia y no hay frase que verificar
    return [replace(c, opcional=True) if c.fichero == W_DGEO else c for c in cl]


def _claims_alcance_rama() -> list[Claim]:
    """Numeros de la pagina de alcance y dilucion entre ramas contra sus marts. Los puntos van con una decimal (tolerancia 0,05).
    Las frases que dependen de un veredicto (alcance, dilucion, control, diferido) son opcionales: SKIP si el texto no las trae."""
    INT, DECS = r"[\d.]+", r"-?\d+,\d+"

    def _e(modelo: str, est: str, col: str = "valor", k: int = 1, f: float = 100.0) -> Callable:
        return lambda con: f * con.execute(f"select {col} from mart_alcance_rama where modelo = ? and k = ? and estadistico = ?",
                                           [modelo, k, est]).fetchone()[0]

    def _pr(col: str, prueba: str = "H-R1", f: float = 1.0) -> Callable:
        return lambda con: f * con.execute(f"select {col} from mart_alcance_rama_prueba where prueba = ?", [prueba]).fetchone()[0]

    def _dif(control: str, col: str, f: float = 100.0) -> Callable:
        return lambda con: f * con.execute(f"select {col} from mart_alcance_rama_diferido where control = ?", [control]).fetchone()[0]

    def _anio(anio: int, col: str) -> Callable:
        def fn(con):
            r = con.execute(f"select {col} from mart_alcance_rama_anio where anio = ?", [anio]).fetchone()
            return float("nan") if r is None else r[0]
        return fn

    def _cob(desde: int, hasta: int) -> Callable:
        return lambda con: 100 * con.execute(
            "select sum(horizontales_medidos) / sum(horizontales) from mart_trayectoria_cobertura "
            "where nivel = 'hijo' and anio between ? and ?", [desde, hasta]).fetchone()[0]

    def _hasta_2023(con) -> float:
        h, t = con.execute("select sum(eventos) filter (where anio between 1 and 2023), sum(eventos) filter (where anio = 0) "
                           "from mart_alcance_rama_anio").fetchone()
        return 100 * h / t

    def _fila(pref: str, celdas: list[tuple[str, str]], i: int, j: int = 0, ancla: str = "") -> str:
        """Regex de la fila `| pref | celda | ... |` que captura el j-esimo `@` de la celda i. Cada celda es (plantilla, numero)."""
        partes = []
        for a, (plantilla, num) in enumerate(celdas[:i + 1]):
            trozos = plantilla.split("@")
            s = trozos[0]
            for b, t in enumerate(trozos[1:]):
                s += (f"({num})" if (a == i and b == j) else num) + t
            partes.append(s)
        return ancla + r"\| " + pref + r" \| " + r" \| ".join(partes) + r" \|"

    def _sec(titulo: str) -> str:
        return re.escape(titulo) + r"(?:(?!\n## ).)*?"

    PTS, CNT = (0.05, "{:.1f}"), (0, "{:,.0f}")
    out: list[Claim] = []

    def add(id_, patron, fn, tol_fmt=PTS, opcional=False):
        out.append(_c(f"alcance_{id_}@wiki", W_ALCANCE, patron, fn, tol_fmt[0], tol_fmt[1], opcional=opcional))

    # la muestra
    add("muestra_eventos", r"- Muestra: Son " + N + r" eventos", _pr("eventos"), CNT)
    add("muestra_marco", r"- Muestra: Son [\d.]+ eventos \(el [\d.]+% de los " + N + r" eventos del estudio\)", _pr("eventos_marco"), CNT)
    add("muestra_pct", r"- Muestra: Son [\d.]+ eventos \(el (\d+)% de los", lambda con: 100 * _pr("eventos")(con) / _pr("eventos_marco")(con),
        (0.5, "{:.0f}"))
    add("muestra_bloques", r"- Muestra: [^\n]*? en " + N + r" bloques de 5 km", _pr("bloques"), CNT)
    pct = (0.5, "{:.0f}")
    add("cobertura_2016_2023", r"cubren el (\d+)% de los hijos horizontales fracturados de 2016 a 2023", _cob(2016, 2023), pct, True)
    add("cobertura_2024", r"pero solo el (\d+)% de los de 2024", _cob(2024, 2024), pct, True)
    add("cobertura_2025", r"y el (\d+)% de los de 2025", _cob(2025, 2025), pct, True)
    add("eventos_hasta_2023", r"el (\d+)% de los eventos son de hijos fracturados hasta 2023", _hasta_2023, pct, True)

    # las lineas de lectura
    add("lectura_alcance_m", r"llega hasta " + N + r" m entre ramas", _pr("alcance_m"), (0.5, "{:,.0f}"), True)
    g0 = r"A menos de 300 m la brecha es "
    add("lectura_brecha_0_300", g0 + SD + r" puntos", _e("principal", "brecha_0_300"), opcional=True)
    add("lectura_brecha_0_300_ic_bajo", g0 + DECS + r" puntos \(IC 95%: " + SD + r" a ", _e("principal", "brecha_0_300", "ic_bajo"),
        opcional=True)
    add("lectura_brecha_0_300_ic_alto", g0 + DECS + r" puntos \(IC 95%: " + DECS + r" a " + SD + r"\)",
        _e("principal", "brecha_0_300", "ic_alto"), opcional=True)
    add("lectura_a", r"\(A, " + SD + r" puntos\)", _e("principal", "A"), opcional=True)
    add("lectura_b", r"\(B, " + SD + r" puntos\)", _e("principal", "B"), opcional=True)
    d0 = r"A menos B es "
    add("lectura_a_menos_b", d0 + SD + r" puntos", _e("principal", "A_menos_B"), opcional=True)
    add("lectura_a_menos_b_ic_bajo", d0 + DECS + r" puntos \(IC 95%: " + SD + r" a ", _e("principal", "A_menos_B", "ic_bajo"), opcional=True)
    add("lectura_a_menos_b_ic_alto", d0 + DECS + r" puntos \(IC 95%: " + DECS + r" a " + SD + r"\)",
        _e("principal", "A_menos_B", "ic_alto"), opcional=True)
    c0 = r"rinden "
    add("lectura_c_menos_l", c0 + DEC + r" puntos menos", _e("principal", "C_menos_L", f=-100.0), opcional=True)
    ci = c0 + DECS.replace("-?", "") + r" puntos menos \(IC 95% de la diferencia: "
    add("lectura_c_menos_l_ic_bajo", ci + SD + r" a ", _e("principal", "C_menos_L", "ic_bajo"), opcional=True)
    add("lectura_c_menos_l_ic_alto", ci + DECS + r" a " + SD + r"\)", _e("principal", "C_menos_L", "ic_alto"), opcional=True)
    cl = r"2\.000 m o más es "
    add("lectura_limpio_diferencia", cl + SD + r" puntos", _e("principal", "C_menos_L"), opcional=True)
    add("lectura_limpio_ic_bajo", cl + DECS + r" puntos \(IC 95%: " + SD + r" a ", _e("principal", "C_menos_L", "ic_bajo"), opcional=True)
    add("lectura_limpio_ic_alto", cl + DECS + r" puntos \(IC 95%: " + DECS + r" a " + SD + r"\)",
        _e("principal", "C_menos_L", "ic_alto"), opcional=True)
    lat = r"Contra el control lateral limpio la brecha del mes 1 es "
    sup = r"contra el control de superficie "
    for sufijo, col, cap_l, cap_s in (("", "brecha_mes1", lat + SD + r" puntos", lat + DECS + r" puntos[^\n]*?" + sup + SD),
                                      ("_ic_bajo", "brecha_ic_bajo", lat + DECS + r" puntos \(IC 95%: " + SD + r" a ",
                                       sup + DECS + r" \(IC 95%: " + SD + r" a "),
                                      ("_ic_alto", "brecha_ic_alto", lat + DECS + r" puntos \(IC 95%: " + DECS + r" a " + SD + r"\)",
                                       sup + DECS + r" \(IC 95%: " + DECS + r" a " + SD + r"\)")):
        add(f"lectura_diferido_lateral{sufijo}", cap_l, _dif("lateral_limpio", col), opcional=True)
        add(f"lectura_diferido_usual{sufijo}", cap_s, _dif("usual", col), opcional=True)
    pv = r"ya estaba "

    def _previa_signo(con) -> float:
        """La brecha previa que imprime la pagina junto a 'abajo' o 'arriba'; nan si la palabra no es la del signo del mart."""
        v = _e("s2", "brecha_0_300", k=-1)(con)
        m = re.search(r"ya estaba [\d.,]+ puntos (abajo|arriba)", (ROOT / W_ALCANCE).read_text(encoding="utf-8"))
        if not m or (m.group(1) == "abajo") != (v < 0):
            return float("nan")
        return abs(v)

    add("lectura_previa", pv + DEC + r" puntos (?:abajo|arriba)", _previa_signo, opcional=True)
    add("lectura_previa_ic_bajo", pv + r"[^\n]*?\(IC 95% de la brecha: " + SD + r" a ", _e("s2", "brecha_0_300", "ic_bajo", k=-1),
        opcional=True)
    add("lectura_previa_ic_alto", pv + r"[^\n]*?\(IC 95% de la brecha: " + DECS + r" a " + SD + r"\)",
        _e("s2", "brecha_0_300", "ic_alto", k=-1), opcional=True)

    # tabla de H-R1 (modelo principal) y la previa de S2
    sec1 = _sec("## H-R1: la brecha del mes 1 por banda de distancia entre ramas")
    for etq, nombre in (("0 a 300 m", "brecha_0_300"), ("300 a 600 m", "brecha_300_600"), ("600 a 1.000 m", "brecha_600_1000"),
                        ("1.000 a 2.000 m", "brecha_1000_2000")):
        celdas = [("@", INT), ("@", DECS), ("@ a @", DECS), (r"@ \(@ a @\)", DECS)]
        pref = re.escape(etq)
        b = nombre[len("brecha_"):]
        add(f"h1_{b}_eventos", _fila(pref, celdas, 0, ancla=sec1), _e("principal", nombre, "n", f=1), CNT)
        add(f"h1_{b}_brecha", _fila(pref, celdas, 1, ancla=sec1), _e("principal", nombre))
        add(f"h1_{b}_ic_bajo", _fila(pref, celdas, 2, 0, ancla=sec1), _e("principal", nombre, "ic_bajo"))
        add(f"h1_{b}_ic_alto", _fila(pref, celdas, 2, 1, ancla=sec1), _e("principal", nombre, "ic_alto"))
        for j, col in enumerate(("valor", "ic_bajo", "ic_alto")):
            add(f"h1_{b}_previa_{col}", _fila(pref, celdas, 3, j, ancla=sec1), _e("s2", nombre, col, k=-1), opcional=True)
    add("h1_control_eventos", sec1 + r"\| Control lateral \(2\.000 m o más\) \| " + N + r" \|",
        _e("principal", "brecha_0_300", "n_ref", f=1), CNT)

    # tabla de H-R2
    sec2 = _sec("## H-R2: la dilución")
    txt = ("[^|]*", "")
    for etq, est in (("A (entre ramas)", "A"), ("B (superficie)", "B")):
        celdas = [txt, ("@", INT), txt, ("@", INT), ("@", DECS), ("@ a @", DECS)]
        pref = re.escape(etq)
        add(f"h2_{est}_eventos", _fila(pref, celdas, 1, ancla=sec2), _e("principal", est, "n", f=1), CNT)
        add(f"h2_{est}_control_eventos", _fila(pref, celdas, 3, ancla=sec2), _e("principal", est, "n_ref", f=1), CNT)
        add(f"h2_{est}_brecha", _fila(pref, celdas, 4, ancla=sec2), _e("principal", est))
        add(f"h2_{est}_ic_bajo", _fila(pref, celdas, 5, 0, ancla=sec2), _e("principal", est, "ic_bajo"))
        add(f"h2_{est}_ic_alto", _fila(pref, celdas, 5, 1, ancla=sec2), _e("principal", est, "ic_alto"))
    celdas = [("n/d", ""), ("n/d", ""), ("n/d", ""), ("n/d", ""), ("@", DECS), ("@ a @", DECS)]
    add("h2_a_menos_b_brecha", _fila("A menos B", celdas, 4, ancla=sec2), _e("principal", "A_menos_B"))
    add("h2_a_menos_b_ic_bajo", _fila("A menos B", celdas, 5, 0, ancla=sec2), _e("principal", "A_menos_B", "ic_bajo"))
    add("h2_a_menos_b_ic_alto", _fila("A menos B", celdas, 5, 1, ancla=sec2), _e("principal", "A_menos_B", "ic_alto"))

    # tabla de H-R3 y el recalculo del diferido
    sec3 = _sec("## H-R3: el control de superficie")
    add("h3_contaminado_eventos", _fila("Contaminado", [("@", INT)], 0, ancla=sec3), _e("principal", "C_menos_L", "n", f=1), CNT)
    add("h3_limpio_eventos", _fila("Limpio", [("@", INT)], 0, ancla=sec3), _e("principal", "C_menos_L", "n_ref", f=1), CNT)
    celdas = [("n/d", ""), (r"contaminado menos limpio: @ puntos \(IC 95%: @ a @\)", DECS)]
    for j, col in enumerate(("valor", "ic_bajo", "ic_alto")):
        add(f"h3_diferencia_{col}", _fila("Diferencia", celdas, 1, j, ancla=sec3), _e("principal", "C_menos_L", col), opcional=True)
    mill, f6 = DECS, 1e-6
    for control, etq in (("usual", "control de superficie usual \\(2 a 5 km\\)"), ("lateral_limpio", "control lateral limpio")):
        celdas = [("@", INT), ("@", INT), ("@", DECS), ("@ a @", DECS), ("@", mill), ("@ a @", mill)]
        k = "usual" if control == "usual" else "limpio"
        add(f"h3_dif_{k}_cercanos", _fila(etq, celdas, 0, ancla=sec3), _dif(control, "n_cercanos", 1), CNT, True)
        add(f"h3_dif_{k}_controles", _fila(etq, celdas, 1, ancla=sec3), _dif(control, "n_control", 1), CNT, True)
        add(f"h3_dif_{k}_brecha", _fila(etq, celdas, 2, ancla=sec3), _dif(control, "brecha_mes1"), opcional=True)
        add(f"h3_dif_{k}_ic_bajo", _fila(etq, celdas, 3, 0, ancla=sec3), _dif(control, "brecha_ic_bajo"), opcional=True)
        add(f"h3_dif_{k}_ic_alto", _fila(etq, celdas, 3, 1, ancla=sec3), _dif(control, "brecha_ic_alto"), opcional=True)
        add(f"h3_dif_{k}_bbl", _fila(etq, celdas, 4, ancla=sec3), _dif(control, "diferido_bbl", f6), opcional=True)
        add(f"h3_dif_{k}_bbl_ic_bajo", _fila(etq, celdas, 5, 0, ancla=sec3), _dif(control, "diferido_ic_bajo", f6), opcional=True)
        add(f"h3_dif_{k}_bbl_ic_alto", _fila(etq, celdas, 5, 1, ancla=sec3), _dif(control, "diferido_ic_alto", f6), opcional=True)
    add("h3_rango_estudio_bajo", r"no es el rango del estudio \(" + DEC + r" a ", _rango_mbbl("neto_previa"), opcional=True)
    add("h3_rango_estudio_alto", r"no es el rango del estudio \(\d+,\d+ a " + DEC + r" millones", _rango_mbbl("original"), opcional=True)

    # eventos por anio del hijo y total
    sec4 = _sec("## Eventos por año del hijo")
    for anio in range(2011, 2027):
        add(f"anio_{anio}_eventos", _fila(str(anio), [("@", INT)], 0, ancla=sec4), _anio(anio, "eventos"), CNT, True)
    celdas = [("@", INT)] * 6
    for i, col in enumerate(("eventos", "n_0_300", "n_300_600", "n_600_1000", "n_1000_2000", "n_control")):
        add(f"anio_total_{col}", _fila("Total", celdas, i, ancla=sec4), _anio(0, col), CNT)

    # la fila del README: las cifras que repite de la pagina, contra los mismos marts
    fila = r"\| Alcance y dilución de la huella entre ramas[^\n]*?"
    sd, n_ = f"({DECS})", f"({INT})"

    def rd(id_, patron, fn, tol_fmt=PTS):
        out.append(_c(f"alcance_readme_{id_}@readme", R, fila + patron, fn, tol_fmt[0], tol_fmt[1]))

    rd("alcance_m", r"alcance medido hasta " + n_ + r" m entre ramas", _pr("alcance_m"), CNT)
    rd("b0", r"es de " + sd + r" puntos a menos de 300 m", _e("principal", "brecha_0_300"))
    rd("b1", r"puntos a menos de 300 m, " + sd + r" de 300 a 600 m", _e("principal", "brecha_300_600"))
    rd("b2", r"de 300 a 600 m, " + sd + r" de 600 a 1\.000 m", _e("principal", "brecha_600_1000"))
    rd("b3", r"de 600 a 1\.000 m y " + sd + r" de 1\.000 a 2\.000 m", _e("principal", "brecha_1000_2000"))
    rd("eventos", r"sobre " + n_ + r" eventos con las dos ramas", _pr("eventos"), CNT)
    rd("ic_bajo", r"a menos de 300 m: " + sd + r" a ", _e("principal", "brecha_0_300", "ic_bajo"))
    rd("ic_alto", r"a menos de 300 m: " + DECS + r" a " + sd + r";", _e("principal", "brecha_0_300", "ic_alto"))
    rd("a_menos_b", r"\(A menos B\) da " + sd + r" puntos", _e("principal", "A_menos_B"))
    rd("a_menos_b_bajo", r"\(A menos B\) da " + DECS + r" puntos \(IC 95%: " + sd + r" a ", _e("principal", "A_menos_B", "ic_bajo"))
    rd("a_menos_b_alto", r"\(A menos B\) da " + DECS + r" puntos \(IC 95%: " + DECS + r" a " + sd + r"\)", _e("principal", "A_menos_B", "ic_alto"))
    rd("contaminado", r"rinden " + r"(\d+,\d+)" + r" puntos menos", _e("principal", "C_menos_L", f=-100.0))
    rd("cob_2016_2023", r"cubren el (\d+)% de esos hijos", _cob(2016, 2023), pct)
    rd("cob_2024", r"pero el (\d+)% de los de 2024", _cob(2024, 2024), pct)
    rd("cob_2025", r"y el (\d+)% de los de 2025", _cob(2025, 2025), pct)

    return out


W_RIESGO = "wiki/hallazgos/riesgo.md"


def _claims_riesgo() -> list[Claim]:
    """Numeros de la pagina de riesgo de golpe fuerte contra sus marts: la lectura, la tabla de modelos, la calibracion, los coeficientes
    de las variables fijas, el grupo con y sin rama, los eventos por ano y la fila del README. Los decimales van con dos cifras
    (tolerancia 0,005) y los porcentajes con una (0,05). Las frases que dependen del veredicto son opcionales."""
    DECS = r"-?\d+,\d+"
    INT = r"[\d.]+"
    out: list[Claim] = []

    def add(id_, patron, fn, tol_fmt, opcional=False):
        out.append(_c(f"riesgo_{id_}@wiki", W_RIESGO, patron, fn, tol_fmt[0], tol_fmt[1], opcional=opcional))

    D2, P1, CNT = (0.005, "{:.2f}"), (0.05, "{:.1f}"), (0, "{:,.0f}")

    def _m(modelo: str, col: str, f: float = 1.0) -> Callable:
        return lambda con: f * con.execute(f"select {col} from mart_riesgo_modelo where modelo = ?", [modelo]).fetchone()[0]

    def _p(col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_riesgo_prueba").fetchone()[0]

    def _cal(dec: int, col: str, f: float = 1.0) -> Callable:
        return lambda con: f * con.execute(f"select {col} from mart_riesgo_calibracion where decil = ?", [dec]).fetchone()[0]

    def _coef(variable: str) -> Callable:
        return lambda con: con.execute("select coef from mart_riesgo_coef where variable = ?", [variable]).fetchone()[0]

    def _rama(grupo: str, col: str) -> Callable:
        def fn(con):
            r = con.execute(f"select {col} from mart_riesgo_rama where grupo = ?", [grupo]).fetchone()
            return float("nan") if r is None or r[0] is None else r[0]
        return fn

    def _anio(anio: int, col: str) -> Callable:
        def fn(con):
            r = con.execute(f"select {col} from mart_riesgo_anio where anio = ?", [anio]).fetchone()
            return float("nan") if r is None else r[0]
        return fn

    def _cob(desde: int, hasta: int) -> Callable:
        return lambda con: 100 * con.execute(
            "select sum(horizontales_medidos) / sum(horizontales) from mart_trayectoria_cobertura "
            "where nivel = 'hijo' and anio between ? and ?", [desde, hasta]).fetchone()[0]

    # la lectura
    lec = r"- Muestra: Son "
    add("muestra_eventos", lec + N + r" eventos cercanos", _p("eventos"), CNT)
    add("muestra_entrenamiento", lec + r"[\d.]+ eventos cercanos[^\n]*?\): " + N + r" de entrenamiento", _p("n_entrenamiento"), CNT)
    add("muestra_prueba", r"de entrenamiento \(hijos fracturados de 2016-01 a 2022-12\) y " + N + r" de prueba", _p("n_prueba"), CNT)
    add("muestra_fuera", r"de 2023-01 a 2024-12\); " + N + r" quedan fuera", _p("fuera_ventana"), CNT)
    add("muestra_con_rama", r"De los de prueba, " + N + r" tienen la rama del par medida", _rama("con_rama", "n"), CNT)
    pct = (0.5, "{:.0f}")
    add("cob_2016_2023", r"cubren el (\d+)% de los hijos horizontales fracturados de 2016 a 2023", _cob(2016, 2023), pct, True)
    add("cob_2024", r"pero solo el (\d+)% de los de 2024", _cob(2024, 2024), pct, True)
    add("cob_2025", r"y el (\d+)% de los de 2025", _cob(2025, 2025), pct, True)
    add("prueba_2024_con_rama", r"fina en 2024: " + N + r" de sus", _anio(2024, "con_rama"), CNT, True)
    add("prueba_2024_eventos", r"fina en 2024: [\d.]+ de sus " + N + r" eventos", _anio(2024, "eventos"), CNT, True)
    add("prevalencia_entrenamiento", r"Ocurre en el (" + DECS + r")% de los eventos de entrenamiento", _m("principal", "prevalencia_entrenamiento", 100.0), P1)
    add("prevalencia_prueba", r"y en el (" + DECS + r")% de los de prueba", _m("principal", "prevalencia_prueba", 100.0), P1)
    ri = r"- Riesgo: [^\n]*?En la prueba el AUC es "
    add("lectura_auc", ri + "(" + DECS + r")", _m("principal", "auc"), D2, True)
    add("lectura_auc_bajo", ri + DECS + r" \(IC 95%: (" + DECS + r") a ", _m("principal", "auc_ic_bajo"), D2, True)
    add("lectura_auc_alto", ri + DECS + r" \(IC 95%: " + DECS + r" a (" + DECS + r")\)", _m("principal", "auc_ic_alto"), D2, True)
    hb = ri + DECS + r" \(IC 95%: " + DECS + r" a " + DECS + r"\) y la habilidad de Brier contra la tasa de entrenamiento por área es "
    add("lectura_bss", hb + "(" + DECS + r")", _m("principal", "bss"), D2, True)
    add("lectura_bss_bajo", hb + DECS + r" \(IC 95%: (" + DECS + r") a ", _m("principal", "bss_ic_bajo"), D2, True)
    add("lectura_bss_alto", hb + DECS + r" \(IC 95%: " + DECS + r" a (" + DECS + r")\)", _m("principal", "bss_ic_alto"), D2, True)
    cb = r"- Calibración \(descriptivo, tabla de abajo\): el décimo de mayor riesgo predice "
    add("calib_pred_alto", cb + "(" + DECS + r")%", _cal(10, "pred_media", 100.0), P1, True)
    add("calib_obs_alto", cb + DECS + r"% y observa (" + DECS + r")%", _cal(10, "obs_media", 100.0), P1, True)
    add("calib_pred_bajo", cb + DECS + r"% y observa " + DECS + r"%; el de menor riesgo predice (" + DECS + r")%", _cal(1, "pred_media", 100.0), P1, True)
    add("calib_obs_bajo", r"el de menor riesgo predice " + DECS + r"% y observa (" + DECS + r")%", _cal(1, "obs_media", 100.0), P1, True)
    gl = r"- Geometría \(descriptivo, sin veredicto\): sin las variables de las ramas el AUC es "
    for j, col in enumerate(("auc", "auc_ic_bajo", "auc_ic_alto")):
        cap = [DECS, DECS, DECS]
        cap[j] = "(" + DECS + ")"
        add(f"geo_m2_{col}", gl + cap[0] + r" \(" + cap[1] + r" a " + cap[2] + r"\)", _m("m2_sin_rama", col), D2, True)
        cap3 = [DECS, DECS, DECS]
        cap3[j] = "(" + DECS + ")"
        add(f"geo_m3_{col}", gl + DECS + r" \(" + DECS + r" a " + DECS + r"\) y con la distancia de superficie sola "
            + cap3[0] + r" \(" + cap3[1] + r" a " + cap3[2] + r"\)", _m("m3_solo_km", col), D2, True)

    # la tabla de modelos
    etiquetas = {"principal": "Principal \\(todas las variables\\)", "m2_sin_rama": "M2: sin la geometría de las ramas",
                 "m3_solo_km": "M3: solo la distancia de superficie", "m4_con_rama": "M4: solo eventos con la rama del par medida",
                 "s1_umbral_m20": "S1: golpe fuerte desde -20 puntos", "s2_umbral_m40": "S2: golpe fuerte desde -40 puntos"}
    trio = DECS + r" \(" + DECS + r" a " + DECS + r"\)"

    def DECS_FIJO(t):
        return t[0] + r" \(" + t[1] + r" a " + t[2] + r"\)"

    def fila(modelo: str, i: int, j: int | None = None) -> str:
        """Regex de la fila del modelo con una captura en la celda i (y, si es un trio, en su elemento j)."""
        celdas = [r"[^|]*", INT, INT, r"[^|]*", trio, trio, r"[^|]*"]
        if i in (1, 2):
            celdas[i] = "(" + INT + ")"
        elif i in (4, 5, 6):
            t = [DECS, DECS, DECS]
            t[j] = "(" + DECS + ")"
            celdas[i] = DECS_FIJO(t)
        elif i == 3:
            celdas[3] = "(" + DECS + ")"
        return r"\| " + etiquetas[modelo] + r" \| [^|]*\| " + r" \| ".join(c for c in (celdas[1], celdas[2], celdas[3], celdas[4], celdas[5], celdas[6])) + r" \|"

    for modelo in etiquetas:
        add(f"modelo_{modelo}_n_entrenamiento", fila(modelo, 1), _m(modelo, "n_entrenamiento"), CNT)
        add(f"modelo_{modelo}_n_prueba", fila(modelo, 2), _m(modelo, "n_prueba"), CNT)
        add(f"modelo_{modelo}_prevalencia", fila(modelo, 3), _m(modelo, "prevalencia_prueba", 100.0), P1)
        for j, col in enumerate(("auc", "auc_ic_bajo", "auc_ic_alto")):
            add(f"modelo_{modelo}_{col}", fila(modelo, 4, j), _m(modelo, col), D2)
        for j, col in enumerate(("bss", "bss_ic_bajo", "bss_ic_alto")):
            add(f"modelo_{modelo}_{col}", fila(modelo, 5, j), _m(modelo, col), D2)
    for modelo in ("m2_sin_rama", "m3_solo_km"):
        for j, col in enumerate(("dauc", "dauc_ic_bajo", "dauc_ic_alto")):
            add(f"modelo_{modelo}_{col}", fila(modelo, 6, j), _m(modelo, col), D2)

    # la calibracion por decil
    for dec in range(1, 10 + 1):
        fila_c = r"\| " + str(dec) + r" \| "
        add(f"cal_{dec}_n", fila_c + "(" + INT + r")", _cal(dec, "n"), CNT)
        add(f"cal_{dec}_pred", fila_c + INT + r" \| (" + DECS + r")", _cal(dec, "pred_media", 100.0), P1)
        add(f"cal_{dec}_obs", fila_c + INT + r" \| " + DECS + r" \| (" + DECS + r")", _cal(dec, "obs_media", 100.0), P1)

    # los coeficientes de las variables fijas
    for var in ("intercepto", "km", "m_min", "falta_rama", "dif_azimut", "posicion_costado", "posicion_mixto", "posicion_punta", "edad_meses",
                "acum_m3_por_m", "falta_largo_padre", "base_m3_d", "arena_por_m", "etapas", "falta_largo_hijo", "mismo_pad", "hijos_1km"):
        add(f"coef_{var}", r"\| " + re.escape(var) + r" \| (" + DECS + r") \|", _coef(var), D2)

    # con y sin rama
    for grupo, etiqueta in (("con_rama", "Con la rama del par medida"), ("sin_rama", "Sin la rama del par medida")):
        fila_r = r"\| " + etiqueta + r" \| "
        add(f"rama_{grupo}_n", fila_r + "(" + INT + r")", _rama(grupo, "n"), CNT)
        add(f"rama_{grupo}_golpes", fila_r + INT + r" \| (" + INT + r")", _rama(grupo, "golpes"), CNT)
        add(f"rama_{grupo}_auc", fila_r + INT + r" \| " + INT + r" \| (" + DECS + r") \|", _rama(grupo, "auc"), D2)

    # los eventos por ano
    for anio in range(2011, 2027):
        fila_a = r"\| " + str(anio) + r" \| (?:entrenamiento|prueba|fuera) \| "
        add(f"anio_{anio}_eventos", fila_a + "(" + INT + r")", _anio(anio, "eventos"), CNT, True)
        add(f"anio_{anio}_con_rama", fila_a + INT + r" \| (" + INT + r")", _anio(anio, "con_rama"), CNT, True)
        add(f"anio_{anio}_golpes", fila_a + INT + r" \| " + INT + r" \| (" + INT + r") \|", _anio(anio, "golpes"), CNT, True)
    add("reps", r"\(([\d.]+) remuestras, ", _p("reps"), CNT)
    add("pads", r"remuestras, ([\d.]+) pads", _p("pads_prueba"), CNT)

    # la fila del README: las cifras que repite de la pagina
    fila_rd = r"\| Riesgo de golpe fuerte con un modelo logístico[^\n]*?"

    def rd(id_, patron, fn, tol_fmt):
        out.append(_c(f"riesgo_readme_{id_}@readme", R, fila_rd + patron, fn, tol_fmt[0], tol_fmt[1]))

    rd("eventos", r"sobre " + N + r" eventos", _p("n_prueba"), CNT)
    rd("auc", r"el AUC es (" + DECS + r") y la habilidad", _m("principal", "auc"), D2)
    rd("bss", r"habilidad de Brier contra la tasa de entrenamiento por área es (" + DECS + r") \|", _m("principal", "bss"), D2)
    rd("auc_bajo", r"del AUC: (" + DECS + r") a ", _m("principal", "auc_ic_bajo"), D2)
    rd("auc_alto", r"del AUC: " + DECS + r" a (" + DECS + r");", _m("principal", "auc_ic_alto"), D2)
    rd("bss_bajo", r"de la habilidad de Brier: (" + DECS + r") a ", _m("principal", "bss_ic_bajo"), D2)
    rd("bss_alto", r"de la habilidad de Brier: " + DECS + r" a (" + DECS + r") \|", _m("principal", "bss_ic_alto"), D2)
    rd("cob_2016_2023", r"cubren el (\d+)% de esos hijos", _cob(2016, 2023), pct)
    rd("cob_2024", r"pero el (\d+)% de los de 2024", _cob(2024, 2024), pct)
    rd("cob_2025", r"y el (\d+)% de los de 2025", _cob(2025, 2025), pct)
    return out


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


W_ESPERA = "site/espera.html"


def _claims_espera() -> list[Claim]:
    """Las cifras fijas del texto de site/espera.html, con las mismas funciones que las del README: la pagina y el README no
    pueden decir cosas distintas. El JS reescribe n-casos, rango y med24 desde D; estos claims leen el HTML sin JS."""
    return [
        _c("espera_eventos@site", W_ESPERA, r'id="n-casos">' + N + r"</span> veces a menos de un kilómetro", _eventos_cercanos, 0),
        _c("espera_brecha_descontada@site", W_ESPERA, r'rinden entre <span class="cifra">(\d+)</span> y <span class="cifra">\d+</span> puntos',
           _pretrend_descontada("mart_placebo_pretrend")),
        _c("espera_brecha_mes1@site", W_ESPERA, r'rinden entre <span class="cifra">\d+</span> y <span class="cifra">(\d+)</span> puntos',
           _brecha_mes1),
        _c("espera_brecha_mes6@site", W_ESPERA, r'a los seis meses la brecha es de <span class="cifra">' + DEC + r"</span> puntos",
           lambda con: -_brecha_k_original(6)(con), 0.05, "{:.1f}"),
        _c("espera_rango_inferior@site", W_ESPERA, r'id="rango">' + DEC + r" y \d+,\d+</span> millones de barriles",
           lambda con: _rango_bbl("neto_previa", "original")(con) / 1e6, 0.05, "{:.1f}"),
        _c("espera_rango_superior@site", W_ESPERA, r'id="rango">\d+,\d+ y ' + DEC + r"</span> millones de barriles",
           _rango_mbbl("original"), 0.05, "{:.1f}"),
        _c("espera_mediana_24@site", W_ESPERA, r'id="med24">(-?[\d.]+)</span> barriles y su intervalo incluye el cero',
           _evento_mediana, 0.5),
    ]


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
        _c("resumen_gap1@doc", W_RESUMEN, r"rinden entre \d+ y (\d+) puntos menos de su caudal previo", _brecha_mes1),
        _c("resumen_gap1_descontada@doc", W_RESUMEN, r"rinden entre (\d+) y \d+ puntos menos de su caudal previo", _pretrend_descontada("mart_placebo_pretrend")),
        _c("resumen_gap1_cota@doc", W_RESUMEN, r"(\d+) es la cota superior", _brecha_mes1),
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


def _claims_entrada() -> list[Claim]:
    """Las cifras de la entrada nueva (README, site/index.html, docs/resumen-operador.md y el abstract en ingles): los dias y el
    caudal de la descomposicion (79 a 88%, cerca de la mitad) y la suba del corte de agua (13,8; 10,9; Colorado 9,0; sin YPF 7,1).
    Mismos marts y mismas guardas de veredicto que las de descomposicion.md y causal_profundo.md."""
    T5, T6, T7, TV = ("mart_causal_profundo_d5", "mart_causal_profundo_d6", "mart_causal_profundo_d7",
                      "mart_causal_profundo_veredicto")

    def veredicto(con, dis: str) -> str:
        return con.execute(f"select veredicto from {TV} where diseno = '{dis}'").fetchone()[0]

    def d2(con) -> float:  # D2 es la fila "todos" de D6: el mayor de los meses 0 y 1, regla fijada antes
        return con.execute(f"select valor from {T6} where corte = 'todos' and grupo = 'todos'").fetchone()[0]

    def d5(con) -> float:  # media de los meses 6 a 12; nan si D5 ya no dice "persiste"
        return con.execute(f"select valor from {TV} where diseno = 'D5'").fetchone()[0] if veredicto(con, "D5") == "persiste" else float("nan")

    def d6_sin_ypf(con) -> float:  # nan si D6 ya no dice que depende de YPF y solo de YPF
        if veredicto(con, "D6") != "depende de un operador":
            return float("nan")
        malos = [r[0] for r in con.execute(f"select grupo from {T6} where corte = 'sin_operador' and not coalesce(ic_bajo > 0, false)").fetchall()]
        return con.execute(f"select valor from {T6} where corte = 'sin_operador' and grupo = 'YPF'").fetchone()[0] if malos == ["YPF"] else float("nan")

    def d7_colorado(con) -> float:  # nan si D7 ya no dice "se repite"
        v = con.execute(f"select veredicto from {T7} where resultado = 'D7'").fetchone()[0]
        return con.execute(f"select valor from {T7} where resultado = 'dW'").fetchone()[0] if v == "se repite" else float("nan")

    def mitad(con) -> float:
        """50 cuando los dias son entre 40 y 55% de la brecha del volumen al mes 1 en las dos variantes (cerca de la mitad); si no, la parte que se sale."""
        partes = [_desc_adit("parte_dias", v)(con) for v in ("con_cerrados", "sin_cerrados")]
        fuera = [p for p in partes if not 40 <= p <= 55]
        return 50.0 if not fuera else fuera[0]

    cl: list[Claim] = []
    ES = r"entre {} y {}% de la caída"
    # los dias del mes de la fractura: 79 (sin los meses cerrados enteros) a 88% (con ellos); un pedazo de texto por superficie
    for sup, fichero, ant in (("readme_resumen", R, r"el mes de la fractura, "), ("readme_q1", R, r"El mes de la fractura el padre pierde días de producción: "),
                              ("site_resumen", S, r"el mes de la fractura, "), ("site_vecino", S, r"Sí\. El mes de la fractura el padre pierde días de producción: "),
                              ("resumen_operador", W_RESUMEN, r"El mes de la fractura, ")):
        for lado, var, grupo in (("bajo", "sin_cerrados", ("(\\d+)", "\\d+")), ("alto", "con_cerrados", ("\\d+", "(\\d+)"))):
            cl.append(_c(f"entrada_dias_{lado}_{sup}", fichero, ant + ES.format(*grupo), _desc_adit("parte_dias", var, 0), 0.5))
    cl.append(_c("entrada_dias_bajo_readme_en", R, r"In the frac month, (\d+) to \d+% of the parent", _desc_adit("parte_dias", "sin_cerrados", 0), 0.5))
    cl.append(_c("entrada_dias_alto_readme_en", R, r"In the frac month, \d+ to (\d+)% of the parent", _desc_adit("parte_dias", "con_cerrados", 0), 0.5))
    # "cerca de la mitad" del volumen ya es caudal por dia al mes 1 (42 a 52%, las dos variantes)
    for sup, fichero, pat in (("readme_resumen", R, r"Cerca de la (mitad) de la caída del volumen ya es menos petróleo por día"),
                              ("site_resumen", S, r"Cerca de la (mitad) de la caída del volumen ya es menos petróleo por día"),
                              ("resumen_operador", W_RESUMEN, r"cerca de la (mitad) ya es menos petróleo por día"),
                              ("readme_en", R, r"about (half) of the volume drop is now lower oil per producing day"),
                              ("caso_en", CASO, r"about (half) of the volume drop is now lower oil per producing day")):
        cl.append(_c(f"entrada_mitad_{sup}", fichero, pat, mitad, 0))
    # los eventos de la entrada
    cl.append(_c("entrada_eventos_readme", R, r"en toda la cuenca: " + N + r" eventos", _eventos_cercanos))
    cl.append(_c("entrada_eventos_site", S, r"en toda la cuenca: " + N + r" eventos", _eventos_cercanos))
    # el corte de agua: D2 13,8 (regla fijada antes), D5 10,9 (meses 6 a 12), D6 7,1 (sin YPF), D7 9,0 (Colorado, fijado despues)
    for sup, fichero, pat in (("readme_resumen", R, r"sube " + DEC + r" puntos porcentuales y sigue arriba en los meses 6 a 12"),
                              ("readme_q3", R, r"el corte de agua del padre sube " + DEC + r" puntos porcentuales y en los meses 6 a 12"),
                              ("site_resumen", S, r"sube " + DEC + r" puntos porcentuales y sigue arriba en los meses 6 a 12"),
                              ("site_diferido", S, r"El corte de agua del padre sube " + DEC + r" puntos porcentuales y en los meses 6 a 12"),
                              ("resumen_operador", W_RESUMEN, r"El corte de agua del padre sube " + DEC + r" puntos porcentuales y en los meses 6 a 12")):
        cl.append(_c(f"entrada_agua_d2_{sup}", fichero, pat, d2, 0.05, "{:.1f}", tabla=T6))
    for sup, fichero in (("readme_q3", R), ("site_diferido", S), ("resumen_operador", W_RESUMEN)):
        cl.append(_c(f"entrada_agua_d5_{sup}", fichero, r"en los meses 6 a 12 sigue " + DEC + r" puntos arriba", d5, 0.05, "{:.1f}", tabla=T5))
    for sup, fichero in (("readme_q3", R), ("resumen_operador", W_RESUMEN)):
        cl.append(_c(f"entrada_agua_d6_{sup}", fichero, r"sin sus pozos da " + DEC, d6_sin_ypf, 0.05, "{:.1f}", tabla=T6))
    cl.append(_c("entrada_agua_d7_readme_q3", R, r"Se repite en Colorado \(" + DEC + r", regla fijada después\)", d7_colorado, 0.05, "{:.1f}", tabla=T7))
    # el abstract en ingles redondea 13,8 y 10,9 a enteros
    for sup, fichero in (("readme_en", R), ("caso_en", CASO)):
        cl.append(_c(f"entrada_agua_d2_{sup}", fichero, r"water cut rises about (\d+) percentage points", d2, 0.5, "{:.0f}", tabla=T6))
        cl.append(_c(f"entrada_agua_d5_{sup}", fichero, r"stays about (\d+) points up in months 6 to 12", d5, 0.5, "{:.0f}", tabla=T5))
    return cl


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
        _c("mundo_pozos@site", W_MUNDO, r"<b>" + N + r" pozos no convencionales con ubicación de superficie</b>",
           _q("select count(*) from int_pozo_ubicacion"), 0),
        _c("mundo_rango_bajo@site", W_MUNDO, r"rinden <b>entre " + N + r" y", _q(bl.format(c="estimacion", m=desc), -100)),
        _c("mundo_rango_alto@site", W_MUNDO, r"rinden <b>entre \d+ y " + N + r" puntos menos</b>",
           _q(bl.format(c="estimacion", m=orig), -100)),
        _c("mundo_cercanos@site", W_MUNDO, r"\(" + N + r" eventos cercanos y", _q(ev.format(b="cercano")), 0),
        _c("mundo_controles@site", W_MUNDO, r"eventos cercanos y " + N + r" de control\)", _q(ev.format(b="control")), 0),
        _c("mundo_brecha1@site", W_MUNDO, r"de la brecha de " + SD + r" puntos:", _q(bl.format(c="estimacion", m=orig), 100), 0.05, "{:.1f}"),
        _c("mundo_ic5_bajo@site", W_MUNDO, r"de la brecha de -?\d+,\d+ puntos: " + SD + r" a",
           _q(bl.format(c="ic_bajo_5km", m=orig), 100), 0.05, "{:.1f}"),
        _c("mundo_ic5_alto@site", W_MUNDO, r"de la brecha de -?\d+,\d+ puntos: -?\d+,\d+ a " + SD + r" \(",
           _q(bl.format(c="ic_alto_5km", m=orig), 100), 0.05, "{:.1f}"),
        _c("mundo_bloques@site", W_MUNDO, r"\(" + N + r" bloques\)", _q(bl.format(c="bloques_5km", m=orig)), 0),
        _c("mundo_cierre_min@site", W_MUNDO, r"la brecha queda <b>entre " + SD + r" y",
           _q("select max(brecha_mes6) from mart_decision_cierre", 100), 0.05, "{:.1f}"),
        _c("mundo_cierre_max@site", W_MUNDO, r"la brecha queda <b>entre -?\d+,\d+ y " + SD + r" puntos</b>",
           _q("select min(brecha_mes6) from mart_decision_cierre", 100), 0.05, "{:.1f}"),
        _c("mundo_diferido@site", W_MUNDO, r"meses 0 a 6: <b>" + N + r" bbl</b>", _q(ed.format(c="diferido_medio_bbl"))),
        _c("mundo_dif_ic_bajo@site", W_MUNDO, r"bbl</b> \(intervalo de 95%: " + N + r" a", _q(ed.format(c="diferido_ic_bajo_bbl"))),
        _c("mundo_dif_ic_alto@site", W_MUNDO, r"bbl</b> \(intervalo de 95%: [\d.]+ a " + N + r"\)", _q(ed.format(c="diferido_ic_alto_bbl"))),
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
        _c("globo_auditadas@globo", W_GLOBO, r"Revisamos " + N + r" lugares", _fm("total"), 0, wh=False),
        _c("globo_con_fractura@globo", W_GLOBO, r"Solo " + N + r" publican el petróleo de cada pozo", _fm("por_pozo_con_fractura"), 0, wh=False),
        _c("globo_entran@globo", W_GLOBO, r"y " + N + r" de esos cumplen nuestras condiciones", _fm("entran"), 0, wh=False),
        _c("globo_vm_bajo@globo", W_GLOBO, r"rinden <b>entre " + N + r" y", _q(bl.format(c="estimacion", m=desc), -100)),
        _c("globo_vm_alto@globo", W_GLOBO, r"rinden <b>entre \d+ y " + N + r" puntos menos</b>", _q(bl.format(c="estimacion", m=orig), -100)),
    ]
    for cid, nom, pre in (("colorado", "Colorado", "co"), ("wyoming", "Wyoming", "wy")):
        v = f"from {CUENCAS[cid].tabla_veredicto} where k = 1"
        cabeza = r"<b>" + nom + r", [^<]*</b> Brecha al mes 1 de <b>"
        ic = r"-?\d+,\d+ puntos</b> \(intervalo de 95% por bloques de 5 km: "
        out += [
            _c(f"globo_{pre}_brecha@globo", W_GLOBO, cabeza + SD + r" puntos</b>", _q(f"select 100 * brecha {v}"), 0.05, "{:.1f}", almacen=cid),
            _c(f"globo_{pre}_ic_bajo@globo", W_GLOBO, cabeza + ic + SD + r" a", _q(f"select 100 * ic_bajo_bloque {v}"), 0.05, "{:.1f}", almacen=cid),
            _c(f"globo_{pre}_ic_alto@globo", W_GLOBO, cabeza + ic + r"-?\d+,\d+ a " + SD + r"\)", _q(f"select 100 * ic_alto_bloque {v}"), 0.05, "{:.1f}", almacen=cid),
        ]

        # La lectura en palabras ("se replica" / "no se replica", "incluye el cero") sale de un atributo numerico del texto fijo.
        out.append(_c(f"globo_{pre}_se_replica@globo", W_GLOBO, r'<li data-cuenca="' + cid + r'" data-se-replica="(\d)"',
                      _q(f"select cast(se_replica as integer) {v}"), 0, "{:.0f}", almacen=cid))
    mes6_co = "select 100 * brecha from mart_replicacion_serie where base = 'original' and k = 6"
    out.append(_c("globo_co_mes6@globo", W_GLOBO, r"Al mes 6 la brecha no se cierra del todo \(" + SD + r"\)", _q(mes6_co), 0.05, "{:.1f}", almacen="colorado"))
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
        _c("informe_gap1_ic_bajo@site", W_INFORME, r"intervalo de 95%: " + SD + r" a", _q(blq.format(c="ic_bajo_5km"), 100), 0.05, "{:.1f}"),
        _c("informe_gap1_ic_alto@site", W_INFORME, r"intervalo de 95%: -?\d+,\d+ a " + SD + r"\)", _q(blq.format(c="ic_alto_5km"), 100), 0.05, "{:.1f}"),
        _c("informe_gap6@site", W_INFORME, ficha.format(t="Mes 6") + SD, _q(ed.format(c="brecha_mes6", g="todos"), 100), 0.05, "{:.1f}"),
        _c("informe_eventos@site", W_INFORME, r"Estudiamos " + N + r" eventos\.", _q(ed.format(c="eventos", g="todos")), 0),
        _c("informe_padres@site", W_INFORME, r"· " + N + r" padres distintos ·",
           _q("select count(distinct padre) from mart_interferencia_diferida"), 0),
        _c("informe_diferido@site", W_INFORME, ficha.format(t="Diferido") + N, _q(ed.format(c="diferido_medio_bbl", g="todos")), 0.5),
        _c("informe_dif_ic_bajo@site", W_INFORME, r"m³; intervalo de 95%: " + N + r" a", _q(ed.format(c="diferido_ic_bajo_m3", g="todos")), 0.5),
        _c("informe_dif_ic_alto@site", W_INFORME, r"m³; intervalo de 95%: [\d.]+ a " + N + r" m³\)", _q(ed.format(c="diferido_ic_alto_m3", g="todos")), 0.5),
        _c("informe_cota@site", W_INFORME, ficha.format(t="Lo máximo que podría no volver") + N, _q("select cota_bbl from mart_decision_perdida"), 0.5),
        _c("informe_gap1_descontada@site", W_INFORME, r"sin la brecha previa a la fractura, (\d+) puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
        _c("informe_gap1_descontada_nota@site", W_INFORME, r"sin esa brecha previa son (\d+) puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
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


W_MEC = "wiki/hallazgos/mecanismo.md"


def _claims_mecanismo() -> list[Claim]:
    """Cifras de la pagina del mecanismo por la geometria de las ramas (resumen, tabla de modelos, bandas, limites), la linea del README
    y el parrafo que la cita en la pagina del eje, contra los marts de pipeline.mecanismo."""
    def mc(modelo: str, k: int, col: str, factor: float = 100.0) -> Callable:
        return lambda con: factor * con.execute(
            f"select {col} from mart_mecanismo_contraste where modelo = '{modelo}' and k = {k}").fetchone()[0]

    def mb(modelo: str, banda: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(
            f"select {col} from mart_mecanismo_banda where modelo = '{modelo}' and banda = '{banda}'").fetchone()[0]

    def vd(col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from mart_mecanismo_veredicto").fetchone()[0]

    def cercanos_16_23(con) -> float:
        a, t = con.execute("select sum(case when anio between 2016 and 2023 then n_costado + n_punta else 0 end), "
                           "sum(n_costado + n_punta) from mart_mecanismo_muestra").fetchone()
        return 100.0 * a / t

    cl = []

    def frase(clave, fichero, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"mec_{clave}_{k}@wiki", fichero, _fr(k, *lits), fn, tol, fmt))

    d1, n0 = "{:.1f}", "{:,.0f}"
    BP = ["0 a 300 m", "300 a 600 m", "600 a 1.000 m"]
    frase("principal", W_MEC, ["Contraste costado menos punta al mes 1 (principal): ", " puntos (IC 95% por bloques de 5 km: ", " a ",
                               "), sobre ", " costados y ", " puntas y ", " bloques."],
          [mc("principal", 1, "contraste"), mc("principal", 1, "ic_bajo_5km"), mc("principal", 1, "ic_alto_5km"),
           mc("principal", 1, "n_costado", 1), mc("principal", 1, "n_punta", 1), mc("principal", 1, "bloques_5km", 1)],
          [0.05] * 3 + [0] * 3, [d1] * 3 + [n0] * 3)
    frase("placebo", W_MEC, ["Mismo contraste en el mes -1 con la base de los meses -6 a -4: ", " puntos (IC 95% por bloques de 5 km: ",
                             " a ", ")."],
          [vd("placebo", 100), vd("placebo_ic_bajo", 100), vd("placebo_ic_alto", 100)], [0.05] * 3, [d1] * 3)
    frase("cota", W_MEC, ["el límite más lejano de cero es ", " puntos, una cota superior"], [vd("placebo_ic_bajo", -100)], [0.05], [d1])
    frase("serie", W_MEC, ["vale ", " puntos en el mes -3, ", " puntos en el mes -2 y ", " puntos en el mes 0."],
          [mc("serie_base_limpia", -3, "contraste"), mc("serie_base_limpia", -2, "contraste"), mc("serie_base_limpia", 0, "contraste")],
          [0.05] * 3, [d1] * 3)
    frase("bandas", W_MEC, ["es de ", " puntos en la banda de 0 a 300 m (", " costados, ", " puntas), de ", " puntos en la banda de 300 a 600 m (",
                            " costados, ", " puntas), de ", " puntos en la banda de 600 a 1.000 m (", " costados, ", " puntas)."],
          [mb("principal", BP[0], "contraste", 100), mb("principal", BP[0], "n_costado"), mb("principal", BP[0], "n_punta"),
           mb("principal", BP[1], "contraste", 100), mb("principal", BP[1], "n_costado"), mb("principal", BP[1], "n_punta"),
           mb("principal", BP[2], "contraste", 100), mb("principal", BP[2], "n_costado"), mb("principal", BP[2], "n_punta")],
          [0.05, 0, 0] * 3, [d1, n0, n0] * 3)
    frase("otros_ic", W_MEC, ["por pads hijo, de ", " a ", "; por bloques de 2 km, de ", " a ", "."],
          [mc("principal", 1, "ic_bajo_pad"), mc("principal", 1, "ic_alto_pad"), mc("principal", 1, "ic_bajo_2km"),
           mc("principal", 1, "ic_alto_2km")], [0.05] * 4, [d1] * 4)
    frase("variantes", W_MEC, ["Sin pesar por eventos: ", " puntos; con el costado definido por un solape de 0,5 o más: ", " puntos."],
          [mc("sin_pesar", 1, "contraste"), mc("costado_05", 1, "contraste")], [0.05] * 2, [d1] * 2)
    frase("anios", W_MEC, ["De los ", " eventos cercanos del modelo principal, ", "% corresponden"],
          [vd("eventos_cercanos"), cercanos_16_23], [0, 0.05], [n0, d1])
    frase("limite_banda", W_MEC, ["en la banda de 0 a 300 m: allí el contraste del mes -1 ya es de ", " puntos (sin IC"],
          [mb("placebo", BP[0], "contraste", 100)], [0.05], [d1])
    def peso_total(con) -> float:
        return con.execute("select sum(peso) from mart_mecanismo_banda where modelo = 'principal'").fetchone()[0]

    frase("limite_banda_peso", W_MEC, ["en esa banda el contraste del mes 1 es de ", " puntos y pesa ", " de ", " eventos en el promedio."],
          [mb("principal", BP[0], "contraste", 100), mb("principal", BP[0], "peso"), peso_total], [0.05, 0, 0], [d1, n0, n0])
    # table of models: principal and placebo rows (contrast and the 5 km interval)
    for modelo, k, etq in [("principal", 1, r"Principal \(decide\) \| 1"), ("placebo", -1, r"Placebo en k = -1, base de los meses -6 a -4 \| -1")]:
        fila = r"\| " + etq + r" \| [\d.]+ \| [\d.]+ \| "
        cl.append(_c(f"mec_tabla_{modelo}_n@wiki", W_MEC, r"\| " + etq + r" \| " + N + r" \|", mc(modelo, k, "n_costado", 1), 0, n0))
        cl.append(_c(f"mec_tabla_{modelo}_c@wiki", W_MEC, fila + "(" + NG + r") \|", mc(modelo, k, "contraste"), 0.05, d1))
    # the paragraph of the page of the axis
    cl.append(_c("mec_eje_contraste@wiki", "wiki/hallazgos/eje_parada.md",
                 r"Al mes 1 el costado rinde " + "(" + NG + r") puntos menos que la punta", vd("contraste", -100), 0.05, d1))
    cl.append(_c("mec_eje_placebo@wiki", "wiki/hallazgos/eje_parada.md",
                 r"el mismo contraste en el mes -1 es de (" + NG + r") puntos", vd("placebo", 100), 0.05, d1))
    # README row
    fila = r"Mecanismo por la geometría de las ramas [^|]*\| [^|]*?"
    cl.append(_c("mec_readme_contraste@readme", R, fila + r"un contraste de (" + NG + r") puntos", vd("contraste", 100), 0.05, d1))
    cl.append(_c("mec_readme_costados@readme", R, fila + r"sobre (" + NG + r") costados y", vd("n_costado"), 0, n0))
    cl.append(_c("mec_readme_puntas@readme", R, fila + r"costados y (" + NG + r") puntas", vd("n_punta"), 0, n0))
    f3 = fila + r"\| [^|]*?"
    cl.append(_c("mec_readme_ic_bajo@readme", R, f3 + r"IC 95% por bloques de 5 km: (" + NG + r") a", vd("ic_bajo", 100), 0.05, d1))
    cl.append(_c("mec_readme_ic_alto@readme", R, f3 + r"IC 95% por bloques de 5 km: " + NG + r" a (" + NG + r");", vd("ic_alto", 100), 0.05, d1))
    cl.append(_c("mec_readme_placebo_bajo@readme", R, f3 + r"\(IC (" + NG + r") a", vd("placebo_ic_bajo", 100), 0.05, d1))
    cl.append(_c("mec_readme_placebo_alto@readme", R, f3 + r"\(IC " + NG + r" a (" + NG + r")\)", vd("placebo_ic_alto", 100), 0.05, d1))
    f4 = fila + r"\| [^|]*\| [^|]*?"
    # the README prints the verdict word: nan (FAIL) unless the stored verdict is the one it says
    def cota_si_sostiene(con) -> float:
        ver, bajo = con.execute("select veredicto, placebo_ic_bajo from mart_mecanismo_veredicto").fetchone()
        return float("nan") if ver != "sostiene" else -100 * bajo

    cl.append(_c("mec_readme_cota@readme", R, f4 + r"sostiene, con la regla fijada antes de correr [^|]*?diferencia previa de hasta ("
                 + NG + r") puntos", cota_si_sostiene, 0.05, d1))
    # coverage of the measured branches, as the page prints it (from mart_trayectoria_cobertura)
    def cob(i: int) -> Callable:
        def f(con) -> float:
            from pipeline.mecanismo import cobertura_ramas
            c = cobertura_ramas(con)
            return float("nan") if c is None else float(c[i])
        return f

    frase("cobertura", W_MEC, ["las ramas medidas cubren de ", " a ", "% de los hijos fracturados de 2016 a 2023 pero solo ",
                               "% de los de 2024 y ", "% de los de 2025"],
          [cob(0), cob(1), cob(2), cob(3)], [0] * 4, [n0] * 4)
    cl.append(_c("mec_readme_banda@readme", R, f4 + r"la banda de 0 a 300 m ya da (" + NG + r") en el mes -1",
                 mb("placebo", BP[0], "contraste", 100), 0.05, d1))
    cl.append(_c("mec_readme_placebo@readme", R, fila + r"\| [^|]*?el mes -1 da (" + NG + r") puntos", vd("placebo", 100), 0.05, d1))
    return cl


W_CAU = "wiki/hallazgos/causal.md"


def _claims_causal() -> list[Claim]:
    """Cifras de la pagina del diseno causal (resumen, tablas, limites) y de la fila y el limite del README, contra los marts
    de pipeline.causal. Un veredicto impreso que ya no es el del mart da nan (FAIL)."""
    def vd(dis: str, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_causal_veredicto where diseno = '{dis}'").fetchone()[0]

    def se(modelo: str, e: int, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_causal_serie where diseno = 'D1' and modelo = '{modelo}' "
                                       f"and e = {e}").fetchone()[0]

    def pl(dis: str, nombre: str, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_causal_placebo where diseno = '{dis}' and placebo = "
                                       f"'{nombre}'").fetchone()[0]

    def ex(dis: str, cantidad: str, col: str = "valor", factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from mart_causal_extra where diseno = '{dis}' and cantidad = "
                                                f"'{cantidad}'").fetchone()[0]

    def op(nombre: str, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_causal_operador where operador = '{nombre}'").fetchone()[0]

    def si_veredicto(dis: str, texto: str, fn: Callable) -> Callable:
        def f(con) -> float:
            v = con.execute(f"select veredicto from mart_causal_veredicto where diseno = '{dis}'").fetchone()[0]
            return float(fn(con)) if v == texto else float("nan")
        return f

    def umbral_cierre(con) -> float:
        from pipeline.causal import FRACCION_CIERRE
        return FRACCION_CIERRE * vd("D2", "valor")(con)

    cl = []
    d1, n0, d2 = "{:.1f}", "{:,.0f}", "{:.2f}"

    def frase(clave, fichero, lits, fns, tols, fmts):
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"cau_{clave}_{k}@{'readme' if fichero == R else 'wiki'}", fichero, _fr(k, *lits), fn, tol, fmt,
                         tabla="mart_causal_veredicto"))

    V1, V1B, V2 = "no sobrevive a su placebo", "sin muestra", "sostiene: comunicación física causal bajo tendencias paralelas"
    # resumen
    frase("d1", W_CAU, ["**D1, caudal de petróleo al mes 1: no sobrevive a su placebo.** Un placebo da un efecto donde no debería "
                        "haberlo: el diseño no separa la fractura de la selección. ATT(1) = ", " puntos (IC 95% por bloques de 5 km: ",
                        " a ", "), ", " padres tratados en ", " bloques."],
          [si_veredicto("D1", V1, vd("D1", "valor")), vd("D1", "ic_bajo"), vd("D1", "ic_alto"), vd("D1", "n_tratados"),
           vd("D1", "n_bloques")], [0.05] * 3 + [0] * 2, [d1] * 3 + [n0] * 2)
    frase("d1b", W_CAU, ["**D1b, persistencia en los meses 7 a 24: sin muestra.** La muestra no alcanza el mínimo que fijó la regla; "
                         "el valor se publica pero no decide nada. ", " tratados (la regla pide 200); diferencia ", " puntos (IC 95%: ",
                         " a ", ")."],
          [si_veredicto("D1b", V1B, vd("D1b", "n_tratados")), vd("D1b", "valor"), vd("D1b", "ic_bajo"), vd("D1b", "ic_alto")],
          [0, 0.05, 0.05, 0.05], [n0, d1, d1, d1])
    frase("d2", W_CAU, ["**D2, corte de agua: " + V2 + ".** Ningún placebo rompe, el cierre solo no explica el salto y el IC queda "
                        "entero sobre 2 puntos. Mide la proporción de agua, no su volumen: el corte también sube si el petróleo cae con el agua constante, y D2 no separa las dos cosas; el nombre del veredicto es el de la regla fijada. ATT_W = ", " puntos porcentuales (IC 95%: ", " a ", "), ", " tratados."],
          [si_veredicto("D2", V2, vd("D2", "valor")), vd("D2", "ic_bajo"), vd("D2", "ic_alto"), vd("D2", "n_tratados")],
          [0.05] * 3 + [0], [d1] * 3 + [n0])
    frase("lectura", W_CAU, ["un cierre de más de medio mes sin hijo cerca lo sube ", " puntos porcentuales, menos de la mitad."],
          [ex("D2", "cierre_placebo")], [0.05], [d1])
    frase("lectura_pet", W_CAU, ["La caída del caudal de petróleo, en cambio, no sobrevive como causa con estos controles: el "
                                 "placebo de nunca tratados da ", " puntos con un IC que excluye cero, y M* = ", " queda bajo 1."],
          [pl("D1", "nunca_tratados", "att"), ex("D1", "M*")], [0.05, 0.005], [d1, d2])
    # tabla de la serie de D1 (principal y S1)
    for e in range(-3, 7):
        fila = r"\| " + str(e) + r" \| [\d.]+ \| [\d.]+ \| "
        cl.append(_c(f"cau_serie_{e}_n@wiki", W_CAU, r"\| " + str(e) + r" \| (" + N[1:-1] + r") \| [\d.]+ \|",
                     se("principal", e, "n_tratados"), 0, n0, tabla="mart_causal_serie"))
        cl.append(_c(f"cau_serie_{e}_att@wiki", W_CAU, fila + "(" + NG + r") \|", se("principal", e, "att"), 0.05, d1,
                     tabla="mart_causal_serie"))
        cl.append(_c(f"cau_serie_{e}_bajo@wiki", W_CAU, fila + NG + r" \| (" + NG + r") a", se("principal", e, "ic_bajo"), 0.05,
                     d1, tabla="mart_causal_serie"))
        cl.append(_c(f"cau_serie_{e}_alto@wiki", W_CAU, fila + NG + r" \| " + NG + r" a (" + NG + r") \|",
                     se("principal", e, "ic_alto"), 0.05, d1, tabla="mart_causal_serie"))
        f2 = fila + NG + r" \| " + NG + r" a " + NG + r" \| "
        cl.append(_c(f"cau_serie_{e}_s1@wiki", W_CAU, f2 + "(" + NG + r") \|", se("S1", e, "att"), 0.05, d1,
                     tabla="mart_causal_serie"))
    # placebos (D1 y D2)
    for dis, nombre, etq in [("D1", "fecha_falsa", "Fecha falsa"), ("D1", "distancia_falsa", "Distancia falsa"),
                             ("D1", "nunca_tratados", "Nunca tratados"), ("D2", "previo", "Previo"),
                             ("D2", "fecha_falsa", "Fecha falsa"), ("D2", "distancia_falsa", "Distancia falsa")]:
        # las filas de D2 van despues del encabezado "ΔW (pp)"
        pre = r"ΔW \(pp\).*?" if dis == "D2" else r"Placebos de D1.*?"
        fila = pre + r"\| " + etq + r" \([^|]*\) \| "
        cl.append(_c(f"cau_pl_{dis}_{nombre}_n@wiki", W_CAU, fila + r"(" + N[1:-1] + r") \|", pl(dis, nombre, "n_tratados"), 0,
                     n0, tabla="mart_causal_placebo"))
        f2 = fila + r"[\d.]+ \| "
        cl.append(_c(f"cau_pl_{dis}_{nombre}_att@wiki", W_CAU, f2 + "(" + NG + r") \|", pl(dis, nombre, "att"), 0.05, d1,
                     tabla="mart_causal_placebo"))
        cl.append(_c(f"cau_pl_{dis}_{nombre}_bajo@wiki", W_CAU, f2 + NG + r" \| (" + NG + r") a", pl(dis, nombre, "ic_bajo"),
                     0.05, d1, tabla="mart_causal_placebo"))
        cl.append(_c(f"cau_pl_{dis}_{nombre}_alto@wiki", W_CAU, f2 + NG + r" \| " + NG + r" a (" + NG + r") \|",
                     pl(dis, nombre, "ic_alto"), 0.05, d1, tabla="mart_causal_placebo"))
    # M* y potencia
    frase("mstar", W_CAU, ["M* = ", ": si cada paso posterior a la fractura pudiera desviarse"], [ex("D1", "M*")], [0.005], [d2])
    frase("potencia", W_CAU, ["La pendiente previa que se detectaría con 80% de potencia es ", " puntos por mes."],
          [ex("D1", "potencia_pretrendencia")], [0.05], [d1])
    # operadores
    for nombre in ("Pluspetrol", "Tecpetrol", "Vista", "YPF"):
        fila = r"\| " + nombre + r" \| ([\d.]+) \| "
        cl.append(_c(f"cau_op_{nombre}_n@wiki", W_CAU, fila, op(nombre, "n_tratados"), 0, n0, tabla="mart_causal_operador"))
        f2 = r"\| " + nombre + r" \| [\d.]+ \| "
        cl.append(_c(f"cau_op_{nombre}_att@wiki", W_CAU, f2 + "(" + NG + r") \|", op(nombre, "att"), 0.05, d1,
                     tabla="mart_causal_operador"))
        cl.append(_c(f"cau_op_{nombre}_alto@wiki", W_CAU, f2 + NG + r" \| " + NG + r" a (" + NG + r") \|", op(nombre, "ic_alto"),
                     0.05, d1, tabla="mart_causal_operador"))
    # D1b, D2 y descriptivos
    frase("d1b_cuerpo", W_CAU, ["en los meses 1 a 24: ", " tratados en ", " bloques, diferencia "],
          [vd("D1b", "n_tratados"), vd("D1b", "n_bloques")], [0, 0], [n0, n0])
    frase("acum", W_CAU, ["Suma de los meses 0 a 23, sin veredicto: ", " puntos-mes (IC 95%: ", " a ", ")."],
          [ex("D1b", "acumulado_e0_e23"), ex("D1b", "acumulado_e0_e23", "ic_bajo"), ex("D1b", "acumulado_e0_e23", "ic_alto")],
          [0.05] * 3, [d1] * 3)
    frase("d2_cuerpo", W_CAU, ["- ATT_W = ", " puntos porcentuales (IC 95%: ", " a ", "), ", " tratados, ", " bloques."],
          [vd("D2", "valor"), vd("D2", "ic_bajo"), vd("D2", "ic_alto"), vd("D2", "n_tratados"), vd("D2", "n_bloques")],
          [0.05] * 3 + [0] * 2, [d1] * 3 + [n0] * 2)
    frase("cierre", W_CAU, ["grupo de edad: ", " puntos porcentuales (IC 95%: ", " a ", "), ", " meses cerrados."],
          [ex("D2", "cierre_placebo"), ex("D2", "cierre_placebo", "ic_bajo"), ex("D2", "cierre_placebo", "ic_alto"),
           ex("D2", "cierre_placebo", "n")], [0.05] * 3 + [0], [d1] * 3 + [n0])
    frase("umbral", W_CAU, ["menos de la mitad del efecto (el umbral es ", ")."], [umbral_cierre], [0.05], [d1])
    for pos in ("costado", "punta"):
        fila = r"\| " + pos + r" \| "
        cl.append(_c(f"cau_pos_{pos}_n@wiki", W_CAU, fila + r"([\d.]+) \|", ex("D1", f"posicion_{pos}", "n"), 0, n0,
                     tabla="mart_causal_extra"))
        cl.append(_c(f"cau_pos_{pos}_d1@wiki", W_CAU, fila + r"[\d.]+ \| (" + NG + r") \|", ex("D1", f"posicion_{pos}"), 0.05, d1,
                     tabla="mart_causal_extra"))
        f3 = fila + r"[\d.]+ \| " + NG + r" \| " + NG + r" a " + NG + r" \| [\d.]+ \| "
        cl.append(_c(f"cau_pos_{pos}_d2@wiki", W_CAU, f3 + "(" + NG + r") \|", ex("D2", f"posicion_{pos}"), 0.05, d1,
                     tabla="mart_causal_extra"))
    frase("lee", W_CAU, ["en el mes 1 (meses con 0,9 del mes producido o más): de ", " a ", " puntos. Producen el mes entero ",
                         "% de los tratados y ", "% de los controles"],
          [ex("D1", "lee_ic_bajo", factor=100), ex("D1", "lee_ic_alto", factor=100), ex("D1", "lee_q_tratados", factor=100),
           ex("D1", "lee_q_controles", factor=100)], [0.05, 0.05, 0.5, 0.5], [d1, d1, n0, n0])
    frase("lim_pre", W_CAU, ["el mes -1 vale ", " puntos (IC 95%: ", " a ", ")."],
          [se("principal", -1, "att"), se("principal", -1, "ic_bajo"), se("principal", -1, "ic_alto")], [0.05] * 3, [d1] * 3)
    frase("lim_ctrl", W_CAU, ["con aún no tratados ATT(1) = ", ", sumando los nunca tratados ", ", y los nunca tratados con "
                              "fechas sorteadas ya dan ", " puntos"],
          [se("principal", 1, "att"), se("S1", 1, "att"), pl("D1", "nunca_tratados", "att")], [0.05] * 3, [d1] * 3)
    # fila del README
    fila = r"Diseño causal con controles aún no tratados [^|]*\| "
    frase("readme_cifra", R, ["sube el corte de agua del padre ", " puntos porcentuales (", " tratados), pero sin los pozos de "
                              "YPF no se separa de cero; el petróleo al mes 1 da ", " puntos (", " tratados)"],
          [vd("D2", "valor"), vd("D2", "n_tratados"), vd("D1", "valor"), vd("D1", "n_tratados")], [0.05, 0, 0.05, 0],
          [d1, n0, d1, n0])
    frase("index_causal", S, ["el corte de agua del padre sube ", " puntos porcentuales; depende de los pozos de YPF"], [vd("D2", "valor")], [0.05], [d1])
    frase("readme_ic", R, ["IC 95% por bloques de 5 km del corte de agua: ", " a ", "; un cierre de más de medio mes sin hijo cerca sube el "
                           "corte ", " (IC ", " a ", "); del petróleo: ", " a ", ", pero padres nunca tratados con fechas sorteadas "
                           "ya dan ", " (IC ", " a ", ")"],
          [vd("D2", "ic_bajo"), vd("D2", "ic_alto"), ex("D2", "cierre_placebo"), ex("D2", "cierre_placebo", "ic_bajo"),
           ex("D2", "cierre_placebo", "ic_alto"), vd("D1", "ic_bajo"), vd("D1", "ic_alto"), pl("D1", "nunca_tratados", "att"),
           pl("D1", "nunca_tratados", "ic_bajo"), pl("D1", "nunca_tratados", "ic_alto")], [0.05] * 10, [d1] * 10)
    # la frase de D3 en el medio de esta celda la verifica _claims_causal_profundo (readme_d3)
    frase("readme_ver", R, ["; el petróleo no sobrevive "
                            "a su placebo (M* = ", "), así que la brecha sigue siendo una huella y no se lee como efecto causal; la "
                            "persistencia de los meses 7 a 24 queda sin muestra (", " tratados de 200)"],
          [si_veredicto("D2", V2, si_veredicto("D1", V1, ex("D1", "M*"))), si_veredicto("D1b", V1B, vd("D1b", "n_tratados"))],
          [0.005, 0], [d2, n0])
    return cl


W_CAUP = "wiki/hallazgos/causal_profundo.md"


def _claims_causal_profundo() -> list[Claim]:
    """Cifras de la pagina de causal profundo (D3: agua que entra o petroleo que sale) contra los marts de
    pipeline.causal_profundo. Un veredicto impreso que ya no es el del mart da nan (FAIL)."""
    from pipeline.causal_profundo import NOMBRE_D3, NOMBRE_PLACEBO_D3, TEXTO_D3

    def d3(cantidad: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from mart_causal_profundo_d3 where cantidad = "
                                                f"'{cantidad}'").fetchone()[0]

    def vd(col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_causal_profundo_veredicto where diseno = 'D3'").fetchone()[0]

    def si_veredicto(texto: str, fn: Callable) -> Callable:
        def f(con) -> float:
            v = con.execute("select veredicto from mart_causal_profundo_veredicto where diseno = 'D3'").fetchone()[0]
            return float(fn(con)) if v == texto else float("nan")
        return f

    def cuota(cantidad: str, col: str) -> Callable:
        return lambda con: 100 * d3(cantidad, col)(con) / d3("dA", col)(con)

    cl = []
    d1, n0 = "{:.1f}", "{:,.0f}"

    def frase(clave, lits, fns, tols, fmts, tabla="mart_causal_profundo_d3", fichero=W_CAUP):
        sufijo = "readme" if fichero == R else "wiki"
        for k, (fn, tol, fmt) in enumerate(zip(fns, tols, fmts)):
            cl.append(_c(f"caup_{clave}_{k}@{sufijo}", fichero, _fr(k, *lits), fn, tol, fmt, tabla=tabla))

    V3 = "entra agua en los días producidos"
    # resumen: el veredicto impreso va pegado a la primera cifra, que da nan si el mart dice otro
    frase("agua", ["- ◐ **D3, agua que entra o petróleo que sale: " + V3 + ".** " + TEXTO_D3[V3] + "\n- Agua por día calendario: "," puntos del líquido de la base (IC 95% por bloques de 5 km: ", " a ",
                   "), ", " padres tratados en ", " bloques."],
          [si_veredicto(V3, vd("valor")), vd("ic_bajo"), vd("ic_alto"), vd("n_tratados"), vd("n_bloques")],
          [0.05] * 3 + [0] * 2, [d1] * 3 + [n0] * 2, tabla="mart_causal_profundo_veredicto")
    frase("pd", ["- Agua por día producido: ", " puntos (IC 95%: ", " a ", "), ", " tratados; petróleo por día producido: ",
                 " (IC 95%: ", " a ", ")."],
          [d3("dA_pd", "valor"), d3("dA_pd", "ic_bajo"), d3("dA_pd", "ic_alto"), d3("dA_pd", "n_tratados"),
           d3("dO_pd", "valor"), d3("dO_pd", "ic_bajo"), d3("dO_pd", "ic_alto")],
          [0.05] * 3 + [0] + [0.05] * 3, [d1] * 3 + [n0] + [d1] * 3)
    frase("o", ["- Petróleo por día calendario: ", " puntos (IC 95%: ", " a ", ")."],
          [d3("dO", "valor"), d3("dO", "ic_bajo"), d3("dO", "ic_alto")], [0.05] * 3, [d1] * 3)
    frase("nt_dw", ["sobre el corte de agua de D2: ", " puntos porcentuales (IC 95%: ", " a ", "), ", " pseudo tratados"],
          [d3("placebo_nunca_tratados_dW", "valor"), d3("placebo_nunca_tratados_dW", "ic_bajo"),
           d3("placebo_nunca_tratados_dW", "ic_alto"), d3("placebo_nunca_tratados_dW", "n_tratados")],
          [0.05] * 3 + [0], [d1] * 3 + [n0])
    # tabla de volumenes
    for k, nombre in NOMBRE_D3.items():
        fila = r"\| " + re.escape(nombre) + r" \| "
        cl.append(_c(f"caup_tab_{k}_n@wiki", W_CAUP, fila + N + r" \|", d3(k, "n_tratados"), 0, n0,
                     tabla="mart_causal_profundo_d3"))
        cl.append(_c(f"caup_tab_{k}_nc@wiki", W_CAUP, fila + r"[\d.]+ \| " + N + r" \|", d3(k, "n_controles"), 0, n0,
                     tabla="mart_causal_profundo_d3"))
        f3 = fila + r"[\d.]+ \| [\d.]+ \| "
        cl.append(_c(f"caup_tab_{k}_att@wiki", W_CAUP, f3 + "(" + NG + r") \|", d3(k, "valor"), 0.05, d1,
                     tabla="mart_causal_profundo_d3"))
        cl.append(_c(f"caup_tab_{k}_bajo@wiki", W_CAUP, f3 + NG + r" \| (" + NG + r") a", d3(k, "ic_bajo"), 0.05, d1,
                     tabla="mart_causal_profundo_d3"))
        cl.append(_c(f"caup_tab_{k}_alto@wiki", W_CAUP, f3 + NG + r" \| " + NG + r" a (" + NG + r") \|", d3(k, "ic_alto"),
                     0.05, d1, tabla="mart_causal_profundo_d3"))
    # placebos
    for k, nombre in NOMBRE_PLACEBO_D3.items():
        fila = r"\| " + re.escape(nombre) + r" \| "
        cl.append(_c(f"caup_pl_{k}_n@wiki", W_CAUP, fila + N + r" \|", d3(k, "n_tratados"), 0, n0,
                     tabla="mart_causal_profundo_d3"))
        f2 = fila + r"[\d.]+ \| "
        cl.append(_c(f"caup_pl_{k}_att@wiki", W_CAUP, f2 + "(" + NG + r") \|", d3(k, "valor"), 0.05, d1,
                     tabla="mart_causal_profundo_d3"))
        cl.append(_c(f"caup_pl_{k}_bajo@wiki", W_CAUP, f2 + NG + r" \| (" + NG + r") a", d3(k, "ic_bajo"), 0.05, d1,
                     tabla="mart_causal_profundo_d3"))
        cl.append(_c(f"caup_pl_{k}_alto@wiki", W_CAUP, f2 + NG + r" \| " + NG + r" a (" + NG + r") \|", d3(k, "ic_alto"),
                     0.05, d1, tabla="mart_causal_profundo_d3"))
    # puente con D2 y limite de la muestra por dia producido
    frase("puente", ["(D2 toma el mayor de los dos) da ", " puntos porcentuales (IC 95%: ", " a ", "), contra ", " de D2."],
          [d3("dW_media", "valor"), d3("dW_media", "ic_bajo"), d3("dW_media", "ic_alto"),
           lambda con: con.execute("select valor from mart_causal_veredicto where diseno = 'D2'").fetchone()[0]],
          [0.05] * 4, [d1] * 4)
    # texto de D2 en README (fila y limite) y en causal.md, segun el veredicto de D3
    # el texto dice que el petroleo por dia producido "no se separa de cero": si su IC deja de incluir el cero, nan
    def o_pd_cero(fn):
        def g(con):
            lo, hi = d3("dO_pd", "ic_bajo")(con), d3("dO_pd", "ic_alto")(con)
            return fn(con) if lo <= 0 <= hi else float("nan")
        return g

    # empieza despues del enlace: numeros_sin_fijar borra el texto entre comillas invertidas antes de buscar
    frase("readme_d3", ["(wiki/hallazgos/causal_profundo.md)), muestra que en los días que el padre produce entra agua: su agua "
                        "por día producido sube ", " puntos del líquido de la base (IC ", " a ", ") y su petróleo por día "
                        "producido no se separa de cero; el volumen de agua del mes no alcanza a separarse de cero (", ", IC ",
                        " a ", "), y no se midió si es porque el padre pierde días;"],
          [o_pd_cero(si_veredicto(V3, d3("dA_pd", "valor"))), d3("dA_pd", "ic_bajo"), d3("dA_pd", "ic_alto"), vd("valor"),
           vd("ic_bajo"), vd("ic_alto")], [0.05] * 6, [d1] * 6, fichero=R)
    frase("cau_d3", ["- ◐ **Debajo del corte de agua (D3, [causal_profundo.md](causal_profundo.md), regla fijada después): " + V3
                     + ".** En los días que el padre produce, su agua por día sube ", " puntos del líquido de la base (IC 95%: ",
                     " a ", ") y su petróleo por día no se separa de cero (", ", IC ", " a ",
                     "); el volumen de agua del mes no alcanza a separarse de cero (", ", IC ", " a ",
                     "), y no se midió si es porque ese mes el padre produce menos días. El nombre \"comunicación física\" se conserva con esa "
                     "salvedad. El placebo de nunca tratados sobre el corte de agua, que la regla de D2 no tenía, da ",
                     " puntos porcentuales (IC 95%: ", " a ", "): no rompe."],
          [o_pd_cero(si_veredicto(V3, d3("dA_pd", "valor"))), d3("dA_pd", "ic_bajo"), d3("dA_pd", "ic_alto"), d3("dO_pd", "valor"),
           d3("dO_pd", "ic_bajo"), d3("dO_pd", "ic_alto"), vd("valor"), vd("ic_bajo"), vd("ic_alto"),
           d3("placebo_nunca_tratados_dW", "valor"), d3("placebo_nunca_tratados_dW", "ic_bajo"),
           d3("placebo_nunca_tratados_dW", "ic_alto")], [0.05] * 12, [d1] * 12, fichero="wiki/hallazgos/causal.md")
    frase("cuota", ["en el mismo commit que dio las cifras): quedan ", "% de los tratados y ", "% de los controles."],
          [cuota("dA_pd", "n_tratados"), cuota("dA_pd", "n_controles")], [0.5, 0.5], [n0, n0])

    # D4: dosis por distancia y por tamano del hijo
    from pipeline.causal_profundo import NOMBRE_BANDA, NOMBRE_TERCIL

    def d4(corte: str, banda: str, res: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from mart_causal_profundo_d4 where corte = '{corte}' and "
                                                f"banda = '{banda}' and resultado = '{res}'").fetchone()[0]

    def v4(dis: str, col: str, texto: str | None = None) -> Callable:
        def f(con) -> float:
            v = con.execute(f"select veredicto, {col} from mart_causal_profundo_veredicto where diseno = '{dis}'").fetchone()
            return float(v[1]) if texto is None or v[0] == texto else float("nan")
        return f

    SG = "sin gradiente"
    T4 = "mart_causal_profundo_d4"

    def con_veredicto(dis: str, fn: Callable) -> Callable:
        """La cifra pegada al veredicto impreso: nan si el mart ya no dice "sin gradiente"."""
        return lambda con: fn(con) if con.execute(f"select veredicto from mart_causal_profundo_veredicto where diseno = "
                                                  f"'{dis}'").fetchone()[0] == SG else float("nan")

    frase("d4_dist", ["- ○ **D4, dosis por distancia: " + SG + ".** El corte de agua sube ", " puntos porcentuales con el "
                      "primer golpe a menos de 0,5 km, ", " entre 0,5 y 1 km y ", " entre 1 y 2 km; la cercana menos la "
                      "lejana da ", " (IC 95%: ", " a ", ")."],
          [con_veredicto("D4_distancia", d4("distancia", "0-0.5", "dW", "valor")), d4("distancia", "0.5-1", "dW", "valor"),
           d4("distancia", "1-2", "dW", "valor"), v4("D4_distancia", "valor"), v4("D4_distancia", "ic_bajo"),
           v4("D4_distancia", "ic_alto")], [0.05] * 6, [d1] * 6, tabla=T4)
    frase("d4_tam", ["- ○ **D4, dosis por tamaño del hijo (agua de fractura): " + SG + ".** Tercil alto ", ", medio ",
                     ", bajo ", " puntos porcentuales; alto menos bajo ", " (IC 95%: ", " a ", ")."],
          [con_veredicto("D4_tamano", d4("tamano_agua", "alto", "dW", "valor")), d4("tamano_agua", "medio", "dW", "valor"),
           d4("tamano_agua", "bajo", "dW", "valor"), v4("D4_tamano", "valor"), v4("D4_tamano", "ic_bajo"),
           v4("D4_tamano", "ic_alto")], [0.05] * 6, [d1] * 6, tabla=T4)
    # renglon de D4 en el README (fila de D2) y en el resumen de causal.md
    frase("readme_d4", ["la dosis, fijada también después, no da gradiente: la cercana menos la lejana da ",
                        " puntos porcentuales (IC ", " a ", ") y el tercil de más agua de fractura del hijo menos el de "
                        "menos da ", " (IC ", " a ", ");"],
          [con_veredicto("D4_distancia", v4("D4_distancia", "valor")), v4("D4_distancia", "ic_bajo"),
           v4("D4_distancia", "ic_alto"), con_veredicto("D4_tamano", v4("D4_tamano", "valor")), v4("D4_tamano", "ic_bajo"),
           v4("D4_tamano", "ic_alto")], [0.05] * 6, [d1] * 6, tabla=T4, fichero=R)
    frase("cau_d4", ["- ○ **Dosis (D4, [causal_profundo.md](causal_profundo.md), regla fijada después): " + SG + ".** El "
                     "corte de agua no sube más cuando el primer golpe está más cerca (la cercana menos la lejana da ",
                     " puntos porcentuales, IC 95%: ", " a ", ") ni cuando el hijo usa más agua de fractura (el tercil "
                     "alto menos el bajo da ", ", IC 95%: ", " a ", ")."],
          [con_veredicto("D4_distancia", v4("D4_distancia", "valor")), v4("D4_distancia", "ic_bajo"),
           v4("D4_distancia", "ic_alto"), con_veredicto("D4_tamano", v4("D4_tamano", "valor")), v4("D4_tamano", "ic_bajo"),
           v4("D4_tamano", "ic_alto")], [0.05] * 6, [d1] * 6, tabla=T4, fichero="wiki/hallazgos/causal.md")
    # tablas de D4: | nombre | tratados | dW | IC dW | dA | IC dA |
    celdas6 = [("dW", "valor"), ("dW", "ic_bajo"), ("dW", "ic_alto"), ("dA", "valor"), ("dA", "ic_bajo"), ("dA", "ic_alto")]
    for corte, nombres in (("distancia", NOMBRE_BANDA), ("tamano_agua", NOMBRE_TERCIL)):
        for b, nombre in nombres.items():
            fila = r"\| " + re.escape(nombre) + r" \| "
            dif = b in ("cercana_menos_lejana", "alto_menos_bajo")
            if not dif:
                cl.append(_c(f"caup_d4_{corte}_{b}_n@wiki", W_CAUP, fila + N + r" \|", d4(corte, b, "dW", "n_tratados"),
                             0, n0, tabla=T4))
            for j, (res, col) in enumerate(celdas6):
                p_ = [("(" + NG + ")") if k == j else NG for k in range(6)]
                patron = (fila + (r" \| " if dif else r"[\d.]+ \| ") + p_[0] + r" \| " + p_[1] + " a " + p_[2] + r" \| "
                          + p_[3] + r" \| " + p_[4] + " a " + p_[5] + r" \|")
                cl.append(_c(f"caup_d4_{corte}_{b}_{res}_{col}@wiki", W_CAUP, patron, d4(corte, b, res, col), 0.05, d1,
                             tabla=T4))
    frase("d4_fuera", [" y ", " quedan fuera porque su bloque no tiene ninguno"],
          [d4("distancia", "fuera", "cuenta", "valor")], [0], [n0], tabla=T4)
    frase("d4_12", ["la banda de 1 a 2 km también sube el corte (IC ", " a ", ")"],
          [d4("distancia", "1-2", "dW", "ic_bajo"), d4("distancia", "1-2", "dW", "ic_alto")], [0.05] * 2, [d1] * 2, tabla=T4)
    frase("d4_cob", ["Los cortes de los terciles salen de los ",
                     " tratados de las celdas de D2 con el agua de fractura del hijo (",
                     "% de los que tienen corte de agua)"],
          [d4("tamano_agua", "cobertura", "cuenta", "n_tratados"), d4("tamano_agua", "cobertura", "cuenta", "valor", 100)],
          [0, 0.5], [n0, n0], tabla=T4)
    frase("d4_rama", ["el tercil más largo menos el más corto da ", " puntos porcentuales (IC 95%: ", " a ",
                      "); tiene el dato el ", "% de los tratados"],
          [d4("rama", "alto_menos_bajo", "dW", "valor"), d4("rama", "alto_menos_bajo", "dW", "ic_bajo"),
           d4("rama", "alto_menos_bajo", "dW", "ic_alto"), d4("rama", "cobertura", "cuenta", "valor", 100)],
          [0.05] * 3 + [0.5], [d1] * 3 + [n0], tabla=T4)

    # D5 y D6: forma en el tiempo y donde se sostiene
    from pipeline.causal_profundo import E_D5, NOMBRE_CORTE_D6
    T5, T6 = "mart_causal_profundo_d5", "mart_causal_profundo_d6"
    CAU = "wiki/hallazgos/causal.md"

    def d5(e, res: str, col: str, factor: float = 1.0) -> Callable:
        donde = "e is null" if e is None else f"e = {int(e)}"
        return lambda con: factor * con.execute(f"select {col} from {T5} where {donde} and resultado = '{res}'").fetchone()[0]

    def d6(corte: str, grupo: str, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from {T6} where corte = '{corte}' and grupo = '{grupo}'").fetchone()[0]

    def v56(dis: str, col: str) -> Callable:
        return lambda con: con.execute(f"select {col} from mart_causal_profundo_veredicto where diseno = '{dis}'").fetchone()[0]

    def persiste(fn: Callable) -> Callable:
        """nan si D5 ya no dice "persiste"."""
        return lambda con: fn(con) if v56("D5", "veredicto")(con) == "persiste" else float("nan")

    def solo_ypf(fn: Callable) -> Callable:
        """nan si D6 ya no dice que depende de YPF y solo de YPF."""
        def f(con) -> float:
            if v56("D6", "veredicto")(con) != "depende de un operador":
                return float("nan")
            malos = [r[0] for r in con.execute(f"select grupo from {T6} where corte = 'sin_operador' and "
                                               "not coalesce(ic_bajo > 0, false)").fetchall()]
            return fn(con) if malos == ["YPF"] else float("nan")
        return f

    def otro_total(con) -> float:
        n, frac = con.execute(f"select n_tratados, valor from {T5} where resultado = 'otro_golpe_2_12'").fetchone()
        return n / frac

    def da_tarde(agg: str) -> Callable:
        return lambda con: con.execute(f"select {agg}(valor) from {T5} where resultado = 'dA' and e >= 2").fetchone()[0]

    t5 = ["la media de los meses 6 a 12 da ", " puntos porcentuales (IC 95%: ", " a ", "), ", " tratados, contra ",
          " de los meses 0 y 1. El IC queda sobre cero en cada mes desde el mes ", "."]
    f5 = [persiste(v56("D5", "valor")), v56("D5", "ic_bajo"), v56("D5", "ic_alto"), v56("D5", "n_tratados"),
          d5(None, "dW_temprano", "valor"), d5(None, "primer_mes_ic_sobre_cero", "valor")]
    tol5, fmt5 = [0.05] * 3 + [0, 0.05, 0], [d1] * 3 + [n0, d1, n0]
    cola5 = "La suba del corte de agua no se cura en 12 meses: "
    frase("d5_res", ["- ● **D5, forma en el tiempo: persiste.** " + cola5 + t5[0]] + t5[1:], f5, tol5, fmt5, tabla=T5)
    frase("cau_d5", ["- ● **Forma en el tiempo (D5, [causal_profundo.md](causal_profundo.md), regla fijada después): "
                     "persiste.** " + cola5 + t5[0]] + t5[1:], f5, tol5, fmt5, tabla=T5, fichero=CAU)
    t6 = [" puntos porcentuales con un IC que incluye cero (IC 95%: ", " a ", "), sobre ", " tratados de ",
          "; los de YPF solos dan ", " (IC 95%: ", " a ", "), ", " tratados. Sin YPF quedan ",
          " tratados y el IC es ancho: el dato no muestra la suba fuera de YPF, ni la descarta. Sacar cualquiera de los "
          "otros operadores con el mínimo (Pluspetrol, Tecpetrol, Vista) la deja sobre cero."]
    f6 = [solo_ypf(d6("sin_operador", "YPF", "valor")), d6("sin_operador", "YPF", "ic_bajo"), d6("sin_operador", "YPF", "ic_alto"),
          d6("sin_operador", "YPF", "n_tratados"), d6("todos", "todos", "n_tratados"), d6("operador", "YPF", "valor"),
          d6("operador", "YPF", "ic_bajo"), d6("operador", "YPF", "ic_alto"), d6("operador", "YPF", "n_tratados"),
          d6("sin_operador", "YPF", "n_tratados")]
    tol6, fmt6 = [0.05] * 3 + [0, 0] + [0.05] * 3 + [0, 0], [d1] * 3 + [n0, n0] + [d1] * 3 + [n0, n0]
    cola6 = ("depende de un operador: YPF.** La suba del corte de agua de D2 depende de YPF: sin los pozos de YPF da ")
    frase("d6_res", ["- ◐ **D6, dónde se sostiene: " + cola6] + t6, f6, tol6, fmt6, tabla=T6)
    frase("cau_d6", ["- ◐ **Dónde se sostiene (D6, [causal_profundo.md](causal_profundo.md), regla fijada después): " + cola6]
          + t6, f6, tol6, fmt6, tabla=T6, fichero=CAU)
    frase("d6_ver", ["Veredicto: " + cola6.replace(".** ", ". ")] + t6, f6, tol6, fmt6, tabla=T6)
    # tabla de D5: | e | tratados | dW | IC | dA | IC | dO | IC |
    for e in E_D5:
        fila = r"\| " + str(e) + r" \| "
        cl.append(_c(f"caup_d5_{e}_n@wiki", W_CAUP, fila + N + r" \|", d5(e, "dW", "n_tratados"), 0, n0, tabla=T5))
        celdas9 = [(r, c) for r in ("dW", "dA", "dO") for c in ("valor", "ic_bajo", "ic_alto")]
        for j, (res, col) in enumerate(celdas9):
            p_ = [("(" + NG + ")") if k == j else NG for k in range(9)]
            patron = (fila + r"[\d.]+ \| " + p_[0] + r" \| " + p_[1] + " a " + p_[2] + r" \| " + p_[3] + r" \| " + p_[4]
                      + " a " + p_[5] + r" \| " + p_[6] + r" \| " + p_[7] + " a " + p_[8] + r" \|")
            cl.append(_c(f"caup_d5_{e}_{res}_{col}@wiki", W_CAUP, patron, d5(e, res, col), 0.05, d1, tabla=T5))
    frase("d5_media", ["- Media de los meses 6 a 12: ", " puntos porcentuales (IC 95%: ", " a ", "), con ",
                       " tratados (el menor n de esos meses). Media de los meses 0 y 1: ", "."],
          [d5(None, "dW_tarde", "valor"), d5(None, "dW_tarde", "ic_bajo"), d5(None, "dW_tarde", "ic_alto"),
           d5(None, "dW_tarde", "n_tratados"), d5(None, "dW_temprano", "valor")], [0.05] * 3 + [0, 0.05],
          [d1] * 3 + [n0, d1], tabla=T5)
    frase("d5_primer", ["- Primer mes con el IC del corte de agua sobre cero: ", "."],
          [d5(None, "primer_mes_ic_sobre_cero", "valor")], [0], [n0], tabla=T5)
    frase("d5_otro", ["- ", " de ", " tratados (", "%) reciben otro golpe a menos de 2 km"],
          [d5(None, "otro_golpe_2_12", "n_tratados"), otro_total, d5(None, "otro_golpe_2_12", "valor", 100)], [0, 0.5, 0.5],
          [n0] * 3, tabla=T5)
    frase("d5_fuera", ["no tiene ninguno del universo: ", "."], [d5(None, "fuera", "valor")], [0], [n0], tabla=T5)
    frase("d5_pet", ["el petróleo por día calendario ya cae en el mes -1 (", " puntos, IC 95%: ", " a ", ")"],
          [d5(-1, "dO", "valor"), d5(-1, "dO", "ic_bajo"), d5(-1, "dO", "ic_alto")], [0.05] * 3, [d1] * 3, tabla=T5)
    frase("d5_agua", ["queda sobre cero en cada mes de 2 a 12, entre ", " y ", " puntos del líquido de la base."],
          [da_tarde("min"), da_tarde("max")], [0.05] * 2, [d1] * 2, tabla=T5)
    # tabla de D6: | corte | grupo | tratados | controles | dW | IC |
    grupos6 = ([("todos", "todos")] + [(c, op) for op in ("Pluspetrol", "Tecpetrol", "Vista", "YPF")
                                        for c in ("operador", "sin_operador")]
               + [("edad", g) for g in ("6-11", "12-23", "24-47", "48+")]
               + [("periodo", g) for g in ("hasta 2018", "2019-2021", "2022 en adelante")]
               + [("area", g) for g in ("FORTIN DE PIEDRA", "LA AMARGA CHICA", "LOMA CAMPANA")])
    def mismos_grupos(fn: Callable) -> Callable:
        """nan si el mart publica otro conjunto de grupos que el que fijan estos claims (una fila sin claim)."""
        def f(con) -> float:
            en_mart = set(con.execute(f"select corte, grupo from {T6}").fetchall())
            return fn(con) if en_mart == set(grupos6) else float("nan")
        return f

    for corte, grupo in grupos6:
        fila = r"\| " + re.escape(NOMBRE_CORTE_D6[corte]) + r" \| " + re.escape(grupo) + r" \| "
        clave = f"caup_d6_{corte}_{grupo}".replace(" ", "_")
        cl.append(_c(f"{clave}_n@wiki", W_CAUP, fila + N + r" \|", mismos_grupos(d6(corte, grupo, "n_tratados")), 0, n0,
                     tabla=T6))
        cl.append(_c(f"{clave}_c@wiki", W_CAUP, fila + r"[\d.]+ \| " + N + r" \|", d6(corte, grupo, "n_controles"), 0, n0,
                     tabla=T6))
        for j, col in enumerate(("valor", "ic_bajo", "ic_alto")):
            p_ = [("(" + NG + ")") if k == j else NG for k in range(3)]
            patron = fila + r"[\d.]+ \| [\d.]+ \| " + p_[0] + r" \| " + p_[1] + " a " + p_[2] + r" \|"
            cl.append(_c(f"{clave}_{col}@wiki", W_CAUP, patron, d6(corte, grupo, col), 0.05, d1, tabla=T6))
    # README (fila de D2 y limite) y Lectura de causal.md
    frase("readme_d6_titulo", ["puntos porcentuales (", " tratados), pero sin los pozos de YPF no se separa de cero;"],
          [solo_ypf(d6("todos", "todos", "n_tratados"))], [0], [n0], tabla=T6, fichero=R)
    frase("readme_d56", ["la suba no se cura en 12 meses (media de los meses 6 a 12, cada mes solo y no el mayor de dos como en D2: ", ", IC ", " a ",
                         ") y depende de YPF: sin sus pozos da ", " con un IC que incluye cero (", " a ", ") sobre ",
                         " tratados de ", ", así que el dato no la muestra fuera de YPF;"],
          [persiste(v56("D5", "valor")), v56("D5", "ic_bajo"), v56("D5", "ic_alto"), solo_ypf(d6("sin_operador", "YPF", "valor")),
           d6("sin_operador", "YPF", "ic_bajo"), d6("sin_operador", "YPF", "ic_alto"), d6("sin_operador", "YPF", "n_tratados"),
           d6("todos", "todos", "n_tratados")], [0.05] * 6 + [0, 0], [d1] * 6 + [n0] * 2, tabla=T6, fichero=R)
    frase("readme_lim_d56", ["la suba no se cura en 12 meses, y depende de YPF: sin sus pozos da ",
                             " puntos porcentuales con un IC que incluye cero (", " a ", ", ",
                             " tratados), así que no se lee como un efecto de toda la cuenca;"],
          [persiste(solo_ypf(d6("sin_operador", "YPF", "valor"))), d6("sin_operador", "YPF", "ic_bajo"),
           d6("sin_operador", "YPF", "ic_alto"), d6("sin_operador", "YPF", "n_tratados")], [0.05] * 3 + [0],
          [d1] * 3 + [n0], tabla=T6, fichero=R)
    frase("cau_lectura_d56", ["no se cura en los 12 meses siguientes (D5) y depende de YPF (D6): sin YPF da ",
                              " puntos porcentuales con un IC que incluye cero (", " a ", "), sobre ",
                              " tratados, así que el dato no la muestra fuera de YPF."],
          [persiste(solo_ypf(d6("sin_operador", "YPF", "valor"))), d6("sin_operador", "YPF", "ic_bajo"),
           d6("sin_operador", "YPF", "ic_alto"), d6("sin_operador", "YPF", "n_tratados")], [0.05] * 3 + [0],
          [d1] * 3 + [n0], tabla=T6, fichero=CAU)

    # D7: Colorado (el mart lo escribe solo `--cuenca colorado`; sin el, SKIP)
    T7 = "mart_causal_profundo_d7"

    def d7(res: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from {T7} where resultado = '{res}'").fetchone()[0]

    def repite(fn: Callable) -> Callable:
        """nan si D7 ya no dice "se repite"."""
        def f(con) -> float:
            v = con.execute(f"select veredicto from {T7} where resultado = 'D7'").fetchone()[0]
            return fn(con) if v == "se repite" else float("nan")
        return f

    frase("d7_cob", ["- Cobertura del dato de agua: ", "% de los meses base (meses -6 a -4) de los ",
                     " tratados de las celdas de D2 tienen agua y días efectivos"],
          [d7("cobertura_agua", "valor", 100), d7("cobertura_agua", "n_tratados")], [0.5, 0], [n0, n0], tabla=T7)
    frase("d7_d2", ["- D2, corte de agua: ", " puntos porcentuales (IC 95%: ", " a ", "), con ", " tratados; en Vaca Muerta, "],
          [repite(d7("dW", "valor")), d7("dW", "ic_bajo"), d7("dW", "ic_alto"), d7("dW", "n_tratados")],
          [0.05] * 3 + [0], [d1] * 3 + [n0], tabla=T7)
    frase("d7_cierre", ["El placebo de cierre da ", " (IC 95%: ", " a ", ")"],
          [d7("placebo_cierre", "valor"), d7("placebo_cierre", "ic_bajo"), d7("placebo_cierre", "ic_alto")],
          [0.05] * 3, [d1] * 3, tabla=T7)
    frase("d7_d3", ["- D3, en puntos del líquido base: agua por día calendario ", " (IC 95%: ", " a ",
                    "), agua por día producido ", " (IC 95%: ", " a ", "), petróleo por día calendario ", " (IC 95%: ",
                    " a ", "), con ", " tratados."],
          [repite(d7("dA", "valor")), d7("dA", "ic_bajo"), d7("dA", "ic_alto"), d7("dA_pd", "valor"),
           d7("dA_pd", "ic_bajo"), d7("dA_pd", "ic_alto"), d7("dO", "valor"), d7("dO", "ic_bajo"), d7("dO", "ic_alto"),
           d7("dA", "n_tratados")], [0.05] * 9 + [0], [d1] * 9 + [n0], tabla=T7)
    frase("cau_d7", ["- ● **Otra cuenca (D7, Colorado, [causal_profundo.md](causal_profundo.md), regla fijada después): "
                     "se repite.** El corte de agua de D2 sostiene también en Colorado, y D3 da allí el mismo veredicto que "
                     "en Vaca Muerta. En Colorado el corte de agua sube ", " puntos porcentuales (IC 95%: ", " a ", "), ",
                     " tratados."],
          [repite(d7("dW", "valor")), d7("dW", "ic_bajo"), d7("dW", "ic_alto"), d7("dW", "n_tratados")],
          [0.05] * 3 + [0], [d1] * 3 + [n0], tabla=T7, fichero=CAU)
    frase("readme_d7", ["en Colorado, la cuenca DJ (D7, regla fijada después), el mismo diseño se repite: el corte sube ",
                        " puntos porcentuales (IC ", " a ", ", ", " tratados) y D3 da el mismo veredicto que en Vaca Muerta;"],
          [repite(d7("dW", "valor")), d7("dW", "ic_bajo"), d7("dW", "ic_alto"), d7("dW", "n_tratados")],
          [0.05] * 3 + [0], [d1] * 3 + [n0], tabla=T7, fichero=R)
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
        _c("iny_r4a_operador@wiki", W_INY, r"el operador del libro es estricto \(< " + DEC + r"\)", _iny_const("UMBRAL_R4A"), 0.005, "{:.2f}", opcional=True),
        _c("iny_r4a_borde_k@wiki", W_INY, r"con " + N + r" de \d+ mundos \(\d+%\) cumple el texto", _iny_k("S5", 0, "brecha_mes1"), 0, "{:.0f}", opcional=True),
        _c("iny_r4a_borde_pc@wiki", W_INY, r"mundos \(" + PC + r"\) cumple el texto", _iny("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}", opcional=True),
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
        _c("iny_caso_fp_k@caso", CASO, r"borde exacto \(" + N + r" de \d+ mundos", _iny_k("S5", 0, "brecha_mes1"), 0, "{:.0f}", opcional=True),
        _c("iny_caso_fp_mundos@caso", CASO, r"borde exacto \(\d+ de " + N + r" mundos", _iny("S5", 0, "brecha_mes1", "mundos"), 0, "{:.0f}", opcional=True),
        _c("iny_caso_falsos_positivos@caso", CASO, r"mundos, " + PC + r"\): cumple el texto", _iny("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}", opcional=True),
        _c("iny_caso_fp_k_nuevo@caso", CASO, r"falsos positivos da " + N + r" de \d+ mundos", _iny_k("S5", 0, "brecha_mes1"), 0, "{:.0f}"),
        _c("iny_caso_fp_pc_nuevo@caso", CASO, r"falsos positivos da \d+ de \d+ mundos \(" + PC + r"\)", _iny("S5", 0, "brecha_mes1", "ic_excluye_cero_frac", 100), 0.5, "{:.0f}"),
        _c("iny_caso_fp_mundos_nuevo@caso", CASO, r"falsos positivos da \d+ de " + N + r" mundos", _iny("S5", 0, "brecha_mes1", "mundos"), 0, "{:.0f}"),
        _c("iny_caso_umbral@caso", CASO, r"\(como máximo " + PC + r"\) pero no el operador", _iny_const("UMBRAL_R4A", 100), 0.5, "{:.0f}", opcional=True),
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
    ]
    return cl


CLAIMS: list[Claim] = [
    # data quality report (committed JSON, no warehouse needed)
    _c("filas_origen_aprox@readme", R, r"son " + N + r" filas", lambda _: _dq()["filas_origen_produccion"], 1500, wh=False),
    _c("descarga_mb@readme", R, r"descarga unos (\d+) MB",
       lambda _: sum(v["bytes"] for v in json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8")).values()) / 1e6, 5, wh=False),
    _c("filas_origen@docs", D, r"\(" + N + r" filas de producci", lambda _: _dq()["filas_origen_produccion"], 0.5, wh=False),
    _c("filas_origen_aprox@docs", D, r"\b" + N + r" filas se reconstruyen", lambda _: _dq()["filas_origen_produccion"], 1500, wh=False),
    _c("controles@docs", D, r"(\d+) controles:", _n_controles, wh=False),
    _c("bloqueantes_fallidos@docs", D, r"\((\d+) fallidos hoy\)", lambda _: _dq()["bloqueantes_fallidos"], wh=False),
    # typed operations of the agent
    _c("ops@docs", D, r"Agente con (\d+) operaciones tipadas", _n_ops, wh=False),
    # agent evaluation (committed result files)
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
    _c("brecha_mes1_cota_bis@readme", R, r"de la brecha de -(\d+),\d: -?\d+,\d a -?\d+,\d \|", _brecha_mes1),
    _c("brecha_descontada@readme", R, r"entre (\d+) y \d+ puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_bis@readme", R, r"Interferencia al mes 1[^|]*\| (\d+) a \d+ puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
    # La misma cifra dicha dos veces en el README (el Resumen y la primera pregunta): la primera coincidencia fija la del Resumen, estas fijan la de la pregunta.
    _c("eventos_cercanos_q1@readme", R, r"de control a 2 a 5 km \(" + N + r" eventos\)", _eventos_cercanos),
    _c("brecha_mes1_q1@readme", R, r"Un mes después rinde entre \d+ y (\d+) puntos menos que pozos de control", _brecha_mes1),
    _c("brecha_descontada_q1@readme", R, r"Un mes después rinde entre (\d+) y \d+ puntos menos que pozos de control",
       _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_valor@readme", R, r"(\d+) a \d+ el valor descontado", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_sin_previos@readme", R, r"\d+ a (\d+) el valor descontado",
       _pretrend_descontada("mart_placebo_pretrend_sin_previos")),
    _c("brecha_ic_bajo@readme", R, r"brecha de -\d+,\d: " + SD + r" a -?\d+,\d \|", _blq(B_HEAD, 1, "ic_bajo_5km", 100), 0.05, "{:.1f}"),
    _c("brecha_ic_alto@readme", R, r"brecha de -\d+,\d: -?\d+,\d a " + SD + r" \|", _blq(B_HEAD, 1, "ic_alto_5km", 100), 0.05, "{:.1f}"),
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
    *_claims_dia_inicio(),
    *_claims_decision(),
    *_claims_potencia_dosis(),
    *_claims_robustez_operador(),
    *_claims_dias_perdidos(),
    *_claims_golpes_mismo_mes(),
    *_claims_golpes_mismo_padre(),
    *_claims_calendario_golpes(),
    *_claims_trayectorias(),
    *_claims_alcance_rama(),
    *_claims_riesgo(),
    *_claims_dosis_geometria(),
    *_claims_resumen_operador(),
    *_claims_entrada(),
    *_claims_espera(),
    *_claims_informe(),
    *_claims_mundo(),
    *_claims_globo(),
    *_claims_bloques(),
    # the page of the pre-registered 2026 test: its own numbers against the marts it writes
    *_claims_carga_anual(),
    # child side (finding page, README row and case study paragraph)
    *_claims_hijo(),
    *_claims_hijo_celdas(),
    *_claims_mecanismo(),
    *_claims_causal(),
    *_claims_causal_profundo(),
    *_claims_hijo_pad(),
    *_claims_gas(),
    *_claims_literatura(),
    *_claims_limites(),
    *_claims_prospectiva(),
    *_claims_inyeccion(),
    *_claims_colorado(),
    *_claims_fuentes_mundo(),
    *_claims_mapa_base(),
    *_claims_base_foto(),
    *_claims_relieve_fino(),
    *_claims_exactitud(),
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
    _c("costo_r2_media_area@readme", R, r"la media del .rea da " + SIG, _costo_cv_r2("media_area"), 0.005, "{:.2f}"),
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
    _c("index_co_mes6@sitio", S, r"Ahí, al mes 6, la brecha no se cierra del todo \(" + SD + r"\)",
       lambda con: 100 * con.execute("select brecha from mart_replicacion_serie where base = 'original' and k = 6").fetchone()[0], 0.05, "{:.1f}",
       almacen="colorado"),
    _c("brecha_mes1_descontada@sitio=readme", R, r"entre (\d+) y \d+ puntos menos",
       _sitio(r'id="kpis-interf"><div class="kpi"><div class="v">-(\d+) a -\d+</div>'), 0, wh=False),
    _c("brecha_mes1_bruta@sitio=readme", R, r"entre \d+ y (\d+) puntos menos",
       _sitio(r'id="kpis-interf"><div class="kpi"><div class="v">-\d+ a -(\d+)</div>'), 0, wh=False),
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
    # case study (docs/caso-interferencia.md): every number of the body; the English abstract writes 2,077 and 5.8 with the
    # English separators, so those are compared as thousandths / tenths
    _c("abstract_eventos@caso", CASO, r"event study of (\d,\d+) events", lambda con: _eventos_cercanos(con) / 1000, 0.0005, "{:.3f}"),
    _c("abstract_brecha_descontada@caso", CASO, r"(?:yield|produce) (\d+) to \d+ percentage points less", _pretrend_descontada("mart_placebo_pretrend")),
    _c("abstract_brecha_descontada_neta@caso", CASO, r"(\d+) is net of the pre-trend", _pretrend_descontada("mart_placebo_pretrend")),
    _c("abstract_brecha_bruta@caso", CASO, r"(?:yield|produce) \d+ to (\d+) percentage points less", _brecha_mes1),
    _c("abstract_brecha_bruta_parentesis@caso", CASO, r"(\d+) is a raw upper bound", _brecha_mes1),
    _c("abstract_diferido_inferior@caso", CASO, r"ranges from (\d+\.\d+) to \d+\.\d+ million barrels",
       lambda con: 10 * _rango_bbl("neto_previa", "original")(con) / 1e6, 0.5, "{:.1f}"),
    _c("abstract_diferido_superior@caso", CASO, r"ranges from \d+\.\d+ to (\d+\.\d+) million barrels",
       lambda con: 10 * _rango_mbbl("original")(con), 0.5, "{:.1f}"),
    # data and method
    _c("filas_produccion@caso", CASO, N + r" filas de producci.n mensual por pozo", lambda _: _dq()["filas_origen_produccion"], 0.5, wh=False),
    _c("metodo_km_cercano@caso", CASO, r"a menos de (\d+) km del hijo", _km("km_hasta", "0 a 1")),
    _c("metodo_km_control_desde@caso", CASO, r"controles son pozos a (\d+) a \d+ km de un pozo hijo", _km("km_desde", "2 a 5")),
    _c("metodo_km_control_hasta@caso", CASO, r"controles son pozos a \d+ a (\d+) km de un pozo hijo", _km("km_hasta", "2 a 5")),
    _c("metodo_eventos@caso", CASO, r"un estudio de eventos con " + N + r" eventos", _eventos_cercanos),
    _c("metodo_hipotesis@caso", CASO, r"Pruebas corridas: (\w+) hip.tesis con umbral fijo", _hipotesis, wh=False),
    _c("metodo_subconjuntos@caso", CASO, r"y " + N + r" subconjuntos de robustez", _rob_n()),
    _c("metodo_intervalos@caso", CASO, r"agrega " + N + r" intervalos", _n_intervalos),
    # result
    _c("brecha_descontada@caso", CASO, r"entre (\d+) y \d+ puntos menos que los pozos de control", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_el19@caso", CASO, r"el (\d+) descuenta la brecha previa", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_rango@caso", CASO, r"rango de (\d+) a \d+ se mantiene", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_bruta@caso", CASO, r"entre \d+ y (\d+) puntos menos que los pozos de control", _brecha_mes1),
    _c("brecha_bruta_el23@caso", CASO, r"El (\d+) es el valor en bruto", _brecha_mes1),
    _c("brecha_bruta_rango@caso", CASO, r"rango de \d+ a (\d+) se mantiene", _brecha_mes1),
    _c("brecha_bruta_cota@caso", CASO, r"por eso (\d+) es una cota superior", _brecha_mes1),
    _c("brecha_principal@caso", CASO, r"\(" + NEG + r" puntos con la base de los meses -3 a -1", _desc_ref_k1, 0.05, "{:.1f}"),
    _c("brecha_sin_previos@caso", CASO, r"\(el (\d+), sin golpes previos de vecinos",
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
    _c("costo_r2_media_area@caso", CASO, r"contra " + SIG + r" de predecir la media", _costo_cv_r2("media_area"), 0.005, "{:.2f}"),
    # test count (runs pytest --collect-only)
]


# Numeros de README.md que son parte de una definicion y no un resultado: cada uno es una frase, no un numero suelto.
README_DEFINICIONALES: tuple[str, ...] = (
    r"less than 1 km away",  # el abstract en ingles: la definicion del padre
    r"under 5 points",
    r"months 6 to 12",
    r"con los datos hasta 2026-10 ya se puntuó y quedó sin muestra",  # tests/test_report.py lo ata al estado de la página de la prueba
    r"ajustado en 2023",
    r"con el ajuste de 2023",
    r"de 2024 a 2026",
    r"pedía 100 eventos aislados en 2023",
    r"b acotado en cero",
    r"IC 95% por pads del padre",
    r"MDE80",
    r"contra 0,22",
    r"a 1 km o más",
    r"pedía 150 padres y 400 meses de golpe",
    r"commit bddf1e0771",
    r"commit 8f52ff1",
    r"D3, fijado después",
    r"D7, regla fijada después", r"D3 da el mismo veredicto",
    r"meses 7 a 24",
    r"no se cura en 12 meses",
    r"meses 6 a 12",
    r"no el mayor de dos como en D2",
    r"tratados de 200\)",
    r"banda de 0 a 300 m",
    r"a menos de 600 m",
    r"a menos de 300 m",
    r"a menos de 1\.000 m",
    r"de 300 a 600 m",
    r"de 600 a 1\.000 m",
    r"de 1\.000 a 2\.000 m",
    r"\(300, 600, 1\.000 y 2\.000 m\)",
    r"de los de 2024",
    r"de los de 2025",
    r"en la prueba de 2023 y 2024",
    r"por cada 100 bbl por metro",
    r"de 2016 a 2023",
    r"Sentinel-2",
    r"datos a octubre de 2026",
    r"público de septiembre de 2026",
    r"sus 2\.077 eventos",
    r"cohorte 2017",
    r"cohorte 2025",
    r"de 12 meses",
    r"al mes 12",
    r"a menos de 1 km",
    r"within 1 km",
    r"a 2 a 5 km",
    r"2 to 5 km away",
    r"2 to 5 km from a child well",
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
    r"se escribió el 2026-11-18 con los datos hasta 2026-09",
    r"Vaca Muerta en 3D",
    r"Suba de la brecha en 2026",
    r"2026 menos 2021 a 2024",
    r"con 2025 y 2026 juntos",
    r"eventos cercanos de 2026",
    r"bajo el 90% de su trayectoria",
    r"hacen falta 100 eventos cercanos",
    r"quiere decir menos de 5 puntos",
    r"la brecha es de menos de 5 puntos",
    r"con 80% de potencia",
    r"m3 de petróleo",
    r"m3 por evento",
    r"Python 3\.13",
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
    r"En el mes 1, cerca de la mitad",
    r"en los meses 6 a 12",
    r"con 80% de potencia",
    r"Un efecto de 0,2",
    r"m3 de petróleo",
)

CASO_DEFINICIONALES: tuple[str, ...] = (
    r"2 to 5 km from a child well",
    r"deferral of months 0 to 6",
    r"2 to 5 km away",
    r"under 5 points",
    r"months 6 to 12",
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
