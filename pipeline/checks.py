"""Data quality checks.

`bloqueante` checks guard the model itself (grain, nulls, impossible values after
cleaning): if one fails, the build fails and nothing is published.
`aviso` checks measure anomalies in the public source. They do not stop the build;
they are counted, sampled and published so a reader knows what the numbers rest on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, NamedTuple

import duckdb

from pipeline import pads


@dataclass(frozen=True)
class Check:
    nombre: str
    severidad: str  # "bloqueante" | "aviso"
    sql: str        # returns the offending rows; zero rows means OK
    detalle: str
    detalle_dinamico: bool = False  # True: the text is computed from the warehouse by pads.detalle
    fn: Callable | None = None      # when set, fn(con, ctx) -> Resultado replaces `sql`


@dataclass(frozen=True)
class Contexto:
    inputs: dict[str, Path] | None  # raw file per dataset, as pipeline.build received them; None: no raw layer
    hoy: date                       # reference date of the run (freshness)


class Resultado(NamedTuple):
    filas: list[dict]               # offending rows; empty means OK
    detalle: str | None = None      # computed text; None keeps Check.detalle
    omitido: bool = False           # the check could not run (no raw files given)


# ---------------------------------------------------------------- reconciliation, drift, freshness

SQL_STAGING = Path(__file__).parent / "sql" / "01_staging.sql"
UMBRAL_MESES_ATRASO = 3   # the Secretaría publishes with lag: up to 3 months behind is normal
TOL_VOLUMEN = 1e-3        # float tolerance when summing volumes in different order (m3 or miles de m3)
SIN_RAW = "No se evaluó: no se pasaron archivos raw."

# Columns that the raw files carry and the staging SQL does not read. They are known, so only a
# column outside both lists (read or known) is NEW for the drift check.
COLUMNAS_SIN_USO = {
    "produccion_no_convencional": {
        "idempresa", "iny_agua", "iny_gas", "iny_co2", "iny_otro", "vida_util", "observaciones", "fechaingreso",
        "habilitado", "idusuario", "formprod", "profundidad", "idareapermisoconcesion", "idareayacimiento",
        "cuenca", "tipo_de_recurso", "proyecto", "clasificacion", "subclasificacion", "fecha_data"},
    "fractura_adjunto_iv": {
        "sigla", "cuenca", "areapermisoconcesion", "yacimiento", "tipo_reservorio", "co2_inyectado_m3",
        "potencia_equipos_fractura_hp", "fecha_data", "anio_if", "mes_if", "anio_ff", "mes_ff", "anio_carga",
        "mes_carga", "mes", "anio"},
}


def columnas_esperadas(sql: str) -> dict[str, set[str]]:
    """Columns that the staging SQL reads from each raw CSV: `alias.columna` in the statement
    that has `read_csv('{dataset}', ...) alias`. Names are lower case; seeds are left out."""
    esperadas: dict[str, set[str]] = {}
    for stmt in sql.split(";"):
        for m in re.finditer(r"read_csv\('\{(\w+)\}'[^)]*\)\s+(\w+)", stmt):
            dataset, alias = m.groups()
            esperadas.setdefault(dataset, set()).update(
                c.lower() for c in re.findall(rf"\b{alias}\.(\w+)", stmt))
    return {k: v for k, v in esperadas.items() if not k.startswith("seed_")}


COLUMNAS_ESPERADAS = columnas_esperadas(SQL_STAGING.read_text(encoding="utf-8"))


def _num(n) -> str:
    return f"{round(n) + 0:,}".replace(",", ".")


def _csv(path: Path) -> str:
    return f"read_csv('{str(path).replace(chr(39), chr(39) * 2)}', header = true, all_varchar = true)"


def _uno(con, sql: str):
    return con.execute(sql).fetchall()[0][0]


def columnas_raw(con, path: Path) -> list[str]:
    """Header of a raw CSV, lower case."""
    cur = con.execute(f"select * from {_csv(path)} limit 0")
    return [d[0].lower() for d in cur.description]


def deriva_esquema(con, inputs: dict[str, Path], esperadas: dict[str, set[str]] | None = None,
                   conocidas: dict[str, set[str]] | None = None) -> tuple[list[dict], list[dict]]:
    """(missing, new) columns of the latest raw file of each dataset against the staging SQL."""
    esperadas = COLUMNAS_ESPERADAS if esperadas is None else esperadas
    conocidas = COLUMNAS_SIN_USO if conocidas is None else conocidas
    faltan, nuevas = [], []
    for dataset in sorted(esperadas):
        if dataset not in inputs:
            continue
        header = set(columnas_raw(con, inputs[dataset]))
        faltan += [{"dataset": dataset, "columna": c} for c in sorted(esperadas[dataset] - header)]
        nuevas += [{"dataset": dataset, "columna": c}
                   for c in sorted(header - esperadas[dataset] - conocidas.get(dataset, set()))]
    return faltan, nuevas


def _chk_faltan(con, ctx: Contexto) -> Resultado:
    if not ctx.inputs:
        return Resultado([], SIN_RAW, True)
    faltan = deriva_esquema(con, ctx.inputs)[0]
    lista = ", ".join(f"{r['dataset']}.{r['columna']}" for r in faltan)
    return Resultado(faltan, f"Columnas ausentes: {lista}." if faltan else None)


def _chk_nuevas(con, ctx: Contexto) -> Resultado:
    if not ctx.inputs:
        return Resultado([], SIN_RAW, True)
    nuevas = deriva_esquema(con, ctx.inputs)[1]
    lista = ", ".join(f"{r['dataset']}.{r['columna']}" for r in nuevas)
    return Resultado(nuevas, f"Columnas nuevas: {lista}." if nuevas else None)


def _filas_raw(dataset: str, tabla: str) -> Callable:
    def chk(con, ctx: Contexto) -> Resultado:
        if not ctx.inputs or dataset not in ctx.inputs:
            return Resultado([], SIN_RAW, True)
        raw = _uno(con, f"select count(*) from {_csv(ctx.inputs[dataset])}")
        stg = _uno(con, f"select count(*) from {tabla}")
        texto = (f"El CSV de {dataset} tiene {_num(raw)} filas y {tabla} {_num(stg)}. "
                 f"El staging conserva una fila por fila de origen: la diferencia explicada es cero.")
        filas = [{"raw": raw, "staging": stg, "diferencia": stg - raw}] if raw != stg else []
        return Resultado(filas, texto)
    return chk


def _stg_fct_filas(con, ctx: Contexto) -> Resultado:
    n_stg, n_desc, n_fct = con.execute(
        "select (select count(*) from stg_produccion), "
        "(select count(*) from stg_produccion where pozo_id is null or mes is null), "
        "(select count(*) from fct_produccion)").fetchall()[0]
    esperado = n_stg - n_desc
    texto = (f"stg_produccion tiene {_num(n_stg)} filas; {_num(n_desc)} se descartan por pozo o mes inválido y "
             f"fct_produccion debe tener {_num(esperado)} (tiene {_num(n_fct)}).")
    filas = [{"staging": n_stg, "descartadas": n_desc, "esperado": esperado, "fct": n_fct}] if n_fct != esperado else []
    return Resultado(filas, texto)


def _volumenes(con, ctx: Contexto) -> Resultado:
    """Volume per year: stg (valid rows, negatives and nulls taken to zero as fct does) against fct."""
    filas = []
    for p in ("petroleo_m3", "gas_miles_m3", "agua_m3"):
        cur = con.execute(
            f"select coalesce(s.anio, f.anio) anio, coalesce(s.v, 0) stg, coalesce(f.v, 0) fct from "
            f"(select year(mes) anio, sum(greatest(coalesce({p}, 0), 0)) v from stg_produccion "
            f"where pozo_id is not null and mes is not null group by 1) s "
            f"full join (select year(mes) anio, sum({p}) v from fct_produccion group by 1) f using (anio) "
            f"order by 1")
        for anio, stg, fct in cur.fetchall():
            if abs(stg - fct) > TOL_VOLUMEN:
                filas.append({"anio": anio, "producto": p, "staging": stg, "fct": fct, "diferencia": fct - stg})
    tot_stg, desc, neg, tot_fct = (x or 0 for x in con.execute(
        "select (select sum(coalesce(petroleo_m3, 0)) from stg_produccion), "
        "(select sum(coalesce(petroleo_m3, 0)) from stg_produccion where pozo_id is null or mes is null), "
        "(select sum(least(coalesce(petroleo_m3, 0), 0)) from stg_produccion "
        "where pozo_id is not null and mes is not null), "
        "(select sum(petroleo_m3) from fct_produccion)").fetchall()[0])
    texto = (f"Petróleo: stg_produccion suma {_num(tot_stg)} m3; las filas sin pozo o mes válido aportan {_num(desc)} m3 "
             f"y los negativos llevados a cero {_num(neg)} m3; fct_produccion suma {_num(tot_fct)} m3. "
             f"Se concilia por año el petróleo, el gas y el agua, con tolerancia de {str(TOL_VOLUMEN).replace('.', ',')} por el orden de la suma.")
    return Resultado(filas, texto)


def _pozos_dim(con, ctx: Contexto) -> Resultado:
    n_dim, n_fct, n_stg = con.execute(
        "select (select count(*) from dim_pozo), (select count(distinct pozo_id) from fct_produccion), "
        "(select count(distinct pozo_id) from stg_produccion)").fetchall()[0]
    texto = (f"dim_pozo tiene {_num(n_dim)} pozos y fct_produccion {_num(n_fct)} pozos distintos "
             f"(stg_produccion: {_num(n_stg)} con id); deben coincidir.")
    filas = [{"dim_pozo": n_dim, "fct_produccion": n_fct}] if n_dim != n_fct else []
    return Resultado(filas, texto)


def _pozos_fractura(con, ctx: Contexto) -> Resultado:
    n_stg, n_fut, n_dim, trab_dim, trab_esp = con.execute(
        "select (select count(distinct pozo_id) from stg_fractura where pozo_id is not null), "
        "(select count(*) from (select pozo_id from stg_fractura where pozo_id is not null group by 1 "
        "having count(*) filter (where fecha_inicio is null or fecha_inicio <= current_date) = 0)), "
        "(select count(*) from dim_fractura_pozo), (select coalesce(sum(trabajos), 0) from dim_fractura_pozo), "
        "(select count(*) from stg_fractura where pozo_id is not null "
        "and (fecha_inicio is null or fecha_inicio <= current_date))").fetchall()[0]
    esperado = n_stg - n_fut
    texto = (f"stg_fractura tiene {_num(n_stg)} pozos distintos; los que tienen todos sus trabajos con fecha futura "
             f"({_num(n_fut)}) quedan fuera, así que dim_fractura_pozo debe tener {_num(esperado)} (tiene {_num(n_dim)}), "
             f"con {_num(trab_esp)} trabajos (tiene {_num(trab_dim)}).")
    filas = []
    if n_dim != esperado:
        filas.append({"medida": "pozos", "esperado": esperado, "dim_fractura_pozo": n_dim})
    if trab_dim != trab_esp:
        filas.append({"medida": "trabajos", "esperado": trab_esp, "dim_fractura_pozo": trab_dim})
    return Resultado(filas, texto)


def meses_de_atraso(ultimo: date, hoy: date) -> int:
    return (hoy.year * 12 + hoy.month) - (ultimo.year * 12 + ultimo.month)


def _frescura(con, ctx: Contexto) -> Resultado:
    ultimo = _uno(con, "select max(mes) from fct_produccion")
    if ultimo is None:
        return Resultado([{"ultimo_mes": None, "hoy": ctx.hoy.isoformat(), "meses_de_atraso": None}],
                         "fct_produccion no tiene datos.")
    atraso = meses_de_atraso(ultimo, ctx.hoy)
    texto = (f"Último mes con datos: {ultimo.strftime('%Y-%m')}; al {ctx.hoy.isoformat()} van {atraso} meses de atraso. "
             f"Se avisa si pasan de {UMBRAL_MESES_ATRASO} (la Secretaría publica con rezago).")
    filas = ([{"ultimo_mes": ultimo.strftime("%Y-%m"), "hoy": ctx.hoy.isoformat(), "meses_de_atraso": atraso}]
             if atraso > UMBRAL_MESES_ATRASO else [])
    return Resultado(filas, texto)


CHECKS = [
    Check("Grano único (pozo, mes) en fct_produccion", "bloqueante",
          "select pozo_id, mes, count(*) n from fct_produccion group by all having n > 1",
          "Un pozo no puede tener dos filas para el mismo mes."),
    Check("Volúmenes negativos en fct_produccion", "bloqueante",
          "select * from fct_produccion where petroleo_m3 < 0 or gas_miles_m3 < 0 or agua_m3 < 0",
          "Después de limpiar no debe quedar ningún volumen negativo."),
    Check("Pozos de producción sin dim_pozo", "bloqueante",
          "select distinct pozo_id from fct_produccion anti join dim_pozo using (pozo_id)",
          "Toda fila de hechos debe tener su pozo en la dimensión."),
    Check("Filas de origen descartadas por pozo o fecha inválidos", "aviso",
          "select * from stg_produccion where pozo_id is null or mes is null",
          "Filas sin id de pozo o con año/mes no interpretables."),
    Check("Producción con cero días efectivos", "aviso",
          "select pozo_id, mes, petroleo_m3, gas_miles_m3, dias_efectivos from stg_produccion "
          "where (petroleo_m3 > 0 or gas_miles_m3 > 0) and dias_efectivos = 0",
          "El pozo informa volumen pero ningún día en producción (TEF = 0)."),
    Check("Días efectivos mayores que los días del mes", "aviso",
          "select pozo_id, mes, dias_efectivos from stg_produccion where dias_efectivos > day(last_day(mes))",
          "TEF mayor que la cantidad de días calendario del mes."),
    Check("Volúmenes negativos en el origen", "aviso",
          "select pozo_id, mes, petroleo_m3, gas_miles_m3, agua_m3 from stg_produccion "
          "where petroleo_m3 < 0 or gas_miles_m3 < 0 or agua_m3 < 0",
          "Se llevan a cero en fct_produccion."),
    Check("Filas rectificadas", "aviso",
          "select pozo_id, mes, empresa_raw from stg_produccion where rectificado",
          "La empresa corrigió el dato después de la primera carga."),
    Check("Nombres de empresa sin normalizar", "aviso",
          "select distinct empresa_raw from stg_produccion anti join operadores using (empresa_raw) "
          "where formacion = 'vaca muerta' and petroleo_m3 > 0",
          "Razones sociales con producción en Vaca Muerta que no están en seeds/operadores.csv."),
    Check("Fracturas con fecha futura", "aviso",
          "select fractura_id, pozo_id, fecha_inicio, fecha_fin from stg_fractura where fecha_inicio > current_date",
          "Fecha de inicio posterior a la fecha de extracción. Excluidas del modelo."),
    Check("Fracturas que terminan antes de empezar", "aviso",
          "select fractura_id, pozo_id, fecha_inicio, fecha_fin from stg_fractura where fecha_fin < fecha_inicio",
          "Fecha de fin anterior a la de inicio."),
    Check("Fracturas sin longitud de rama horizontal", "aviso",
          "select fractura_id, pozo_id, formacion from stg_fractura where rama_horizontal_m is null",
          "Rama horizontal informada como 0 o vacía (pozos verticales o dato faltante)."),
    Check("Pozos fracturados ausentes en producción no convencional", "aviso",
          "select distinct pozo_id from stg_fractura anti join dim_pozo using (pozo_id)",
          "El pozo figura en Adjunto IV pero no en el dataset de producción no convencional."),
    Check("Pozos con más de un trabajo de fractura", "aviso",
          "select pozo_id, count(*) n from stg_fractura group by 1 having n > 1",
          "Se suman en dim_fractura_pozo (refracturas o cargas repetidas)."),
    Check("Eventos de pozos ausentes en dim_pozo", "aviso",
          "select distinct pozo_id from fct_evento anti join dim_pozo using (pozo_id)",
          "Eventos cuyo pozo_id no figura en dim_pozo."),
    Check("Quiebres de caudal sin fractura vecina o con caída fuera de rango", "aviso",
          "select q.pozo_id, q.fecha, q.valor from fct_evento q "
          "where q.tipo = 'quiebre_caudal' and (q.valor not between 0.25 and 1 or not exists ("
          "select 1 from int_par_padre_hijo h join fct_evento f "
          "on f.pozo_id = h.hijo and f.tipo = 'fractura' and f.mes = h.mes_frac "
          "where h.padre = q.pozo_id and h.mes_frac = q.mes and h.km < 1))",
          "Un quiebre de caudal debe coincidir con la fractura de un pozo vecino a menos de 1 km "
          "y una caída de entre 25% y 100% del caudal base."),
    Check("Eventos fuera del rango de datos", "aviso",
          "select pozo_id, tipo, fecha from fct_evento "
          "where fecha >= (select mes from ultimo_mes) + interval 1 month or fecha < date '2006-01-01'",
          "Eventos posteriores al último mes publicado (incluye fracturas cargadas antes que su producción) "
          "o anteriores a 2006."),
    Check("Pozos de Vaca Muerta shale oil sin datos de fractura", "aviso",
          "select pozo_id from mart_pozo_12m where rama_horizontal_m is null",
          "Pozos con 12 meses de producción que no tienen fractura con rama horizontal en Adjunto IV."),
    Check("Pozos que cambian de pad al agrupar por cercanía en vez de redondear coordenadas", "aviso",
          pads.SQL_CAMBIADOS, "", detalle_dinamico=True),
    # reconciliation between layers: raw CSV, staging, fact and dimensions
    Check("Conciliación: filas del CSV de producción contra stg_produccion", "bloqueante", "",
          "Una fila de staging por fila del CSV.", fn=_filas_raw("produccion_no_convencional", "stg_produccion")),
    Check("Conciliación: filas del CSV de fracturas contra stg_fractura", "bloqueante", "",
          "Una fila de staging por fila del CSV.", fn=_filas_raw("fractura_adjunto_iv", "stg_fractura")),
    Check("Conciliación: filas de stg_produccion contra fct_produccion", "bloqueante", "",
          "Solo se descartan las filas sin pozo o sin mes.", fn=_stg_fct_filas),
    Check("Conciliación: volúmenes de stg_produccion contra fct_produccion por año", "bloqueante", "",
          "Petróleo, gas y agua por año.", fn=_volumenes),
    Check("Conciliación: pozos de dim_pozo contra fct_produccion", "bloqueante", "",
          "Un pozo en la dimensión por cada pozo de hechos.", fn=_pozos_dim),
    Check("Conciliación: pozos fracturados de dim_fractura_pozo contra stg_fractura", "bloqueante", "",
          "Un pozo por cada pozo con trabajos vigentes.", fn=_pozos_fractura),
    # schema drift against the columns that the staging SQL reads
    Check("Deriva de esquema: columnas esperadas ausentes en el raw", "bloqueante", "",
          "Una columna que el staging lee no está en el último archivo del dataset.", fn=_chk_faltan),
    Check("Deriva de esquema: columnas nuevas en el raw", "aviso", "",
          "Columnas que el último archivo trae y que el staging no lee ni figuran como conocidas.", fn=_chk_nuevas),
    Check("Frescura: meses de atraso del último mes publicado", "aviso", "",
          "Meses entre el último mes de fct_produccion y la fecha de la corrida.", fn=_frescura),
]


def run(con: duckdb.DuckDBPyConnection, checks: list[Check] = CHECKS,
        inputs: dict[str, Path] | None = None, hoy: date | None = None) -> dict:
    """Run the checks. `inputs` are the raw files that the build read (checks that read them are
    marked `omitido` without it); `hoy` is the reference date of the freshness check (default: today)."""
    ctx = Contexto(inputs, hoy or date.today())
    results = []
    for c in checks:
        if c.fn is not None:
            r = c.fn(con, ctx)
            extra = {"omitido": True} if r.omitido else {}
            results.append({"nombre": c.nombre, "severidad": c.severidad, "detalle": r.detalle or c.detalle,
                            "filas": len(r.filas), "ok": not r.filas, "muestra": r.filas[:3], **extra})
            continue
        filas = con.execute(f"select count(*) from ({c.sql})").fetchall()[0][0]
        cur = con.execute(f"select * from ({c.sql}) order by all limit 3")
        cols = [d[0] for d in cur.description]
        muestra = [dict(zip(cols, r)) for r in cur.fetchall()]
        results.append({"nombre": c.nombre, "severidad": c.severidad,
                        "detalle": pads.detalle(con) if c.detalle_dinamico else c.detalle,
                        "filas": filas, "ok": filas == 0, "muestra": muestra})
    total = con.execute("select count(*) from stg_produccion").fetchall()[0][0]
    return {
        "filas_origen_produccion": total,
        "bloqueantes_fallidos": sum(1 for r in results if r["severidad"] == "bloqueante" and not r["ok"]),
        "checks": results,
    }
