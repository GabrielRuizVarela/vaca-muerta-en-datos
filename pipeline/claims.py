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
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
EPS = 1e-9

_PALABRAS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
             "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
             "quince": 15, "veinte": 20}


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


def evaluar(c: Claim, texto: str, con, lentos: bool = True) -> Resultado:
    if c.lento and not lentos:
        return Resultado(c, "SKIP", detalle="lento (--rapido)")
    if c.requiere_wh and con is None:
        return Resultado(c, "SKIP", detalle="sin data/warehouse.duckdb")
    doc = extraer(texto, c.patron)
    if doc is None:
        return Resultado(c, "FAIL", detalle="la frase ya no coincide con el patron (cambio el texto o el numero dejo de estar)")
    calc = float(c.valor_fn(con))
    ok = abs(doc - calc) <= c.tolerancia + EPS
    return Resultado(c, "PASS" if ok else "FAIL", doc, calc, "" if ok else f"documento {fmt(c, doc)} contra calculado {fmt(c, calc)}")


def verificar(claims: list[Claim] | None = None, raiz: Path | None = None, wh: Path | None = None, lentos: bool = True) -> list[Resultado]:
    claims = CLAIMS if claims is None else claims
    raiz = ROOT if raiz is None else raiz
    wh = (raiz / "data" / "warehouse.duckdb") if wh is None else wh
    con = duckdb.connect(str(wh), read_only=True) if wh.exists() else None
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
            out.append(evaluar(c, textos[c.fichero], con, lentos))
        return out
    finally:
        if con is not None:
            con.close()


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
    from pipeline.hallazgos import leer_ledger
    rows = leer_ledger(ROOT / "wiki" / "hallazgos" / "ledger.csv")
    if not rows:
        return 0.0
    ultima = rows[-1]["sha_datos"]
    return float(len({r["id"] for r in rows if r["sha_datos"] == ultima}))


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
CASO = "docs/caso-interferencia.md"
DQ = "data/dq_report.json"
N = r"([\d.]+)"          # integer with thousands dots
DEC = r"(\d+,\d+)"       # decimal with comma
NEG = r"(-\d+,\d+)"      # negative decimal with comma


def _c(id, fichero, patron, fn, tol=0.5, formato="{:,.0f}", wh=True, lento=False) -> Claim:
    return Claim(id, fichero, patron, fn, tol, formato, wh, lento)


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


CLAIMS: list[Claim] = [
    # data quality report (committed JSON, no warehouse needed)
    _c("filas_origen_aprox@readme", R, r"son " + N + r" filas", lambda _: _dq()["filas_origen_produccion"], 1500, wh=False),
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
    _c("brecha_mes1_cota@readme", R, r"por eso (\d+) es una cota superior", _brecha_mes1),
    _c("brecha_descontada@readme", R, r"entre (\d+) y \d+ puntos menos", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_valor@readme", R, r"(\d+) a \d+ el valor descontado", _pretrend_descontada("mart_placebo_pretrend")),
    _c("brecha_descontada_sin_previos@readme", R, r"\d+ a (\d+) el valor descontado",
       _pretrend_descontada("mart_placebo_pretrend_sin_previos")),
    _c("brecha_ic_bajo@readme", R, r"brecha de \d+: (\d+) a \d+ \|", _pretrend_ic("ic_alto")),
    _c("brecha_ic_alto@readme", R, r"brecha de \d+: \d+ a (\d+) \|", _pretrend_ic("ic_bajo")),
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
    _c("brecha_2026@readme", R, r"llega a (\d+) puntos en 2026", _brecha_anio(2026)),
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
    _c("brecha_2026@sitio=readme", R, r"llega a (\d+) puntos en 2026",
       _sitio(r"(\d+) puntos en 2026 \(a.o en curso\)"), 0, wh=False),
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
    _c("abstract_brecha_bruta@caso", CASO, r"yield \d+ to (\d+) percentage points less", _brecha_mes1),
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
    _c("brecha_bruta@caso", CASO, r"entre \d+ y (\d+) puntos menos que los controles", _brecha_mes1),
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
    _c("anio_2025@caso", CASO, r"pasa de " + N + r" puntos menos en 2025", _brecha_anio(2025)),
    _c("anio_2026@caso", CASO, r"a " + N + r" puntos menos en 2026", _brecha_anio(2026)),
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
