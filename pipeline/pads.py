"""How many pads changed when pads moved from rounded coordinates to proximity clustering.

Old scheme: pad = (lat, lon) rounded to 3 decimals, as printed by
`printf('%.3f_%.3f', round(lat, 3), round(lon, 3))` in pipeline/sql/04_interferencia.sql
before commit 94580fd. New scheme: `pad_id` of int_pozo_ubicacion, single-linkage clusters
of surface locations within 50 m. Read-only: it only queries int_pozo_ubicacion.
"""
from __future__ import annotations

import duckdb

# One row per shale well with a location: its old pad, its new pad, and the sorted member lists of both
# groups. A well "changed pad" when the two member lists differ.
_POZOS = """
with u as (
    select pozo_id, pad_id as pad_nuevo, printf('%.3f_%.3f', round(lat, 3), round(lon, 3)) as pad_viejo
    from int_pozo_ubicacion
), m as (
    select *,
        list(pozo_id order by pozo_id) over (partition by pad_viejo) as miembros_viejo,
        list(pozo_id order by pozo_id) over (partition by pad_nuevo) as miembros_nuevo
    from u
)
"""

SQL_CAMBIADOS = _POZOS + """
select pozo_id, pad_viejo, pad_nuevo from m where miembros_viejo <> miembros_nuevo
"""


def cifras(con: duckdb.DuckDBPyConnection) -> dict:
    """Counts comparing the two schemes over the same wells."""
    pozos, viejos, nuevos, cambian, en3_viejo, en3_nuevo = con.execute(_POZOS + """
    select
        count(*),
        count(distinct pad_viejo),
        count(distinct pad_nuevo),
        count(*) filter (where miembros_viejo <> miembros_nuevo),
        count(*) filter (where len(miembros_viejo) >= 3),
        count(*) filter (where len(miembros_nuevo) >= 3)
    from m""").fetchone()
    divididos = con.execute(_POZOS + """
        select count(*) from (select pad_viejo from m group by 1 having count(distinct pad_nuevo) > 1)""").fetchone()[0]
    fusionan = con.execute(_POZOS + """
        select count(*) from (select pad_nuevo from m group by 1 having count(distinct pad_viejo) > 1)""").fetchone()[0]
    return {"pozos": pozos, "pads_viejos": viejos, "pads_nuevos": nuevos,
            "pads_viejos_divididos": divididos, "pads_nuevos_fusionan": fusionan,
            "pozos_cambian": cambian,
            "pct_pozos_3mas_viejo": round(100 * en3_viejo / pozos, 1) if pozos else 0.0,
            "pct_pozos_3mas_nuevo": round(100 * en3_nuevo / pozos, 1) if pozos else 0.0}


def detalle(con: duckdb.DuckDBPyConnection) -> str:
    c = cifras(con)
    return (f"Pads por agrupación de ubicaciones a 50 m (enlace simple) frente al redondeo de coordenadas a "
            f"3 decimales (el criterio anterior), sobre {c['pozos']} pozos shale con ubicación: "
            f"{c['pads_viejos']} pads antes y {c['pads_nuevos']} ahora; {c['pads_viejos_divididos']} pads "
            f"viejos se dividen en varios y {c['pads_nuevos_fusionan']} pads nuevos reúnen varios viejos; "
            f"{c['pozos_cambian']} pozos cambian de pad. Pozos en pads de 3 o más pozos: "
            f"{c['pct_pozos_3mas_viejo']}% antes y {c['pct_pozos_3mas_nuevo']}% ahora. Dato informativo, no un error.")
