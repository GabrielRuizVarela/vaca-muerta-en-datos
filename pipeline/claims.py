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
WAREHOUSE_CO = ROOT / "data" / "colorado" / "warehouse.duckdb"
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
    almacen: str = "vm"               # "vm" (data/warehouse.duckdb) or "colorado" (data/colorado/warehouse.duckdb)


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


def evaluar(c: Claim, texto: str, con, lentos: bool = True, con_co=None) -> Resultado:
    if c.lento and not lentos:
        return Resultado(c, "SKIP", detalle="lento (--rapido)")
    if c.almacen == "colorado":
        con = con_co
    if c.requiere_wh and con is None:
        return Resultado(c, "SKIP", detalle="sin data/colorado/warehouse.duckdb" if c.almacen == "colorado" else "sin data/warehouse.duckdb")
    doc = extraer(texto, c.patron)
    if doc is None:
        return Resultado(c, "FAIL", detalle="la frase ya no coincide con el patron (cambio el texto o el numero dejo de estar)")
    calc = float(c.valor_fn(con))
    ok = abs(doc - calc) <= c.tolerancia + EPS
    return Resultado(c, "PASS" if ok else "FAIL", doc, calc, "" if ok else f"documento {fmt(c, doc)} contra calculado {fmt(c, calc)}")


def verificar(claims: list[Claim] | None = None, raiz: Path | None = None, wh: Path | None = None, lentos: bool = True,
              wh_co: Path | None = None) -> list[Resultado]:
    claims = CLAIMS if claims is None else claims
    raiz = ROOT if raiz is None else raiz
    wh = (raiz / "data" / "warehouse.duckdb") if wh is None else wh
    wh_co = (raiz / "data" / "colorado" / "warehouse.duckdb") if wh_co is None else wh_co
    con = duckdb.connect(str(wh), read_only=True) if wh.exists() else None
    con_co = duckdb.connect(str(wh_co), read_only=True) if wh_co.exists() else None
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
            out.append(evaluar(c, textos[c.fichero], con, lentos, con_co))
        return out
    finally:
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


def _c(id, fichero, patron, fn, tol=0.5, formato="{:,.0f}", wh=True, lento=False, almacen="vm") -> Claim:
    return Claim(id, fichero, patron, fn, tol, formato, wh, lento, almacen)


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


def _claims_replicacion() -> list[Claim]:
    """Cada cifra de la pagina de replicacion (Colorado) y de las frases que la citan; se saltan (SKIP) sin el warehouse del Colorado."""
    from pipeline.replicacion import ROTULOS_RECUENTOS, ROTULOS_ROBUSTEZ
    out = []
    PTS_ = r"(-?\d+,\d+)"
    V = "from mart_replicacion_colorado where k = 1"

    def add(id_, fichero, patron, fn, tol=0.05, fmt_="{:.1f}"):
        out.append(_c(id_ + "@colorado", fichero, patron, fn, tol, fmt_, almacen="colorado"))

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
    for clave, rotulo in ROTULOS_RECUENTOS.items():
        add(f"rep_rec_{clave}", W_REP, r"\| " + re.escape(rotulo) + r" \| " + N + r" \|", _rep_sql(ev + f"'{clave}'"), 0, "{:,.0f}")
    # frases que citan el resultado fuera de la pagina
    add("rep_readme_brecha", R, r"Replicación en Colorado \(cuenca DJ\) \| " + PTS_ + r" puntos al mes 1", _rep_sql(f"select 100 * brecha {V}"))
    add("rep_readme_previa", R, r"previa de " + PTS_ + r" en el mes -1", _rep_sql(f"select 100 * brecha_previa_limpia {V}"))
    add("rep_readme_ic_bajo", R, r"por bloques de 5 km: " + PTS_ + r" a -?\d+,\d+ \| se replica", _rep_sql(f"select 100 * ic_bajo_bloque {V}"))
    add("rep_readme_ic_alto", R, r"por bloques de 5 km: -?\d+,\d+ a " + PTS_ + r" \| se replica", _rep_sql(f"select 100 * ic_alto_bloque {V}"))
    rob_ = "from mart_replicacion_robustez where corte = "
    ser_ = "from mart_replicacion_serie where base = "
    PCT_SQL = ("select 100 * (1 - abs(d.brecha_mes1) / abs(p.brecha_mes1)) from mart_replicacion_robustez d, mart_replicacion_robustez p "
               "where d.corte = 'por_dia_producido' and p.corte = 'principal'")
    DIA = rob_ + "'por_dia_producido'"
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
    add("rep_cierre_mes6", W_REP, r"Al mes 6 la brecha de Colorado es de " + PTS_ + r" puntos", _rep_sql(f"select 100 * brecha {ser_}'original' and k = 6"))
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
        _c("blq_readme_bloques@readme", R, r"con bloques espaciales de 5 km \((\d+) bloques\)", _blq(B_HEAD, 1, "bloques_5km"), 0),
        _c("blq_readme_ancho@readme", R, r"es (\d+,\d+) veces más ancho y ningún veredicto cambia", _blq(B_HEAD, 1, "ratio_5km"), 0.005,
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
    *_claims_bloques(),
    # child side (finding page, README row and case study paragraph)
    *_claims_hijo(),
    *_claims_inyeccion(),
    *_claims_colorado(),
    *_claims_replicacion(),
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
