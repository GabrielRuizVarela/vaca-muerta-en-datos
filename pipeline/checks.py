"""Data quality checks.

`bloqueante` checks guard the model itself (grain, nulls, impossible values after
cleaning): if one fails, the build fails and nothing is published.
`aviso` checks measure anomalies in the public source. They do not stop the build;
they are counted, sampled and published so a reader knows what the numbers rest on.
"""
from __future__ import annotations

from dataclasses import dataclass

import duckdb


@dataclass(frozen=True)
class Check:
    nombre: str
    severidad: str  # "bloqueante" | "aviso"
    sql: str        # returns the offending rows; zero rows means OK
    detalle: str


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
    Check("Pozos de Vaca Muerta shale oil sin datos de fractura", "aviso",
          "select pozo_id from mart_pozo_12m where rama_horizontal_m is null",
          "Pozos con 12 meses de producción que no tienen fractura con rama horizontal en Adjunto IV."),
]


def run(con: duckdb.DuckDBPyConnection, checks: list[Check] = CHECKS) -> dict:
    results = []
    for c in checks:
        filas = con.execute(f"select count(*) from ({c.sql})").fetchall()[0][0]
        cur = con.execute(f"select * from ({c.sql}) limit 3")
        cols = [d[0] for d in cur.description]
        muestra = [dict(zip(cols, r)) for r in cur.fetchall()]
        results.append({"nombre": c.nombre, "severidad": c.severidad, "detalle": c.detalle,
                        "filas": filas, "ok": filas == 0, "muestra": muestra})
    total = con.execute("select count(*) from stg_produccion").fetchall()[0][0]
    return {
        "filas_origen_produccion": total,
        "bloqueantes_fallidos": sum(1 for r in results if r["severidad"] == "bloqueante" and not r["ok"]),
        "checks": results,
    }
