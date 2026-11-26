"""Arma el warehouse del Colorado (data/colorado/warehouse.duckdb) desde data/colorado/raw y escribe la pagina de datos.

    uv run python -m pipeline.colorado.build

Es un warehouse APARTE: no toca data/warehouse.duckdb. Las reglas estan fijadas en pipeline/colorado/__init__.py. Las tablas
usan los nombres y columnas que consume el estudio de interferencia (fct_produccion, ultimo_mes, dim_pozo, stg_fractura,
dim_fractura_pozo) y se reconstruyen enteras con create or replace: dos corridas sobre las mismas entradas dan las mismas filas.
Este tramo solo CUENTA hijos, padres cercanos y controles (mart_co_conciliacion); no calcula brecha ni rendimiento.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import duckdb

from pipeline import colorado as R
from pipeline.colorado import ingest
from pipeline.ingest import DATA, ROOT

SQL_DIR = Path(__file__).parent / "sql"
DB = DATA / "colorado" / "warehouse.duckdb"
PAGINA = ROOT / "wiki" / "hallazgos" / "colorado_datos.md"


def parametros() -> dict:
    return {
        "bbl_a_m3": R.BBL_A_M3, "mcf_a_miles_m3": R.MCF_A_MILES_M3, "gal_a_m3": R.GAL_A_M3, "ft_a_m": R.FT_A_M,
        "horizontal_tvd_min_ft": R.HORIZONTAL_TVD_MIN_FT, "horizontal_lateral_min_ft": R.HORIZONTAL_LATERAL_MIN_FT,
        "ventana_ini": R.VENTANA_FRAC[0], "ventana_fin": R.VENTANA_FRAC[1], "fecha_dudosa_dias": R.FECHA_DUDOSA_DIAS,
        "edad_min": R.EDAD_MIN_MESES, "base_min": R.BASE_MIN_M3_D, "km_cercano": R.KM_CERCANO,
        "km_control_min": R.KM_CONTROL[0], "km_max": R.KM_MAX, "pad_km": R.PAD_KM, "km_por_grado": R.KM_POR_GRADO,
    }


def _lit(p: Path) -> str:
    return str(p).replace("'", "''")


def build(con: duckdb.DuckDBPyConnection, produccion_csvs: list[Path], pozos_csv: Path, fracfocus_csv: Path,
          fuentes: dict | None = None) -> None:
    """Corre los tres SQL en orden sobre CSV de texto. `fuentes` (el manifiesto) llena co_fuentes."""
    params = parametros() | {
        "produccion_csvs": "[" + ", ".join(f"'{_lit(p)}'" for p in produccion_csvs) + "]",
        "pozos_csv": _lit(pozos_csv), "fracfocus_csv": _lit(fracfocus_csv),
    }
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        con.execute(sql_file.read_text().format(**params))
    con.execute("create or replace table co_fuentes (nombre varchar, bytes bigint, sha256 varchar)")
    for nombre, e in sorted((fuentes or {}).items()):
        con.execute("insert into co_fuentes values (?, ?, ?)", [nombre, e.get("bytes"), e.get("sha256")])


def controles(con) -> list[tuple[str, bool, str]]:
    """Controles bloqueantes del warehouse del Colorado: (nombre, ok, detalle)."""
    def q(sql):
        return con.execute(sql).fetchone()[0]
    out = []
    n, d = con.execute("select count(*), count(distinct (pozo_id, mes)) from fct_produccion").fetchone()
    out.append(("fct_produccion: un registro por pozo y mes", n == d, f"{n} filas, {d} claves"))
    out.append(("fct_produccion: sin valores negativos ni dias fuera de rango", q(
        "select count(*) from fct_produccion where petroleo_m3 < 0 or gas_miles_m3 < 0 or agua_m3 < 0 "
        "or dias_efectivos < 0 or dias_efectivos > dias_mes") == 0, "petroleo, gas, agua y dias"))
    out.append(("dim_pozo: un registro por pozo", q("select count(*) - count(distinct pozo_id) from dim_pozo") == 0, "pozo_id unico"))
    out.append(("fct_produccion: todo pozo esta en dim_pozo", q(
        "select count(*) from (select distinct pozo_id from fct_produccion) f left join dim_pozo d using (pozo_id) "
        "where d.pozo_id is null") == 0, "sin huerfanos"))
    out.append(("dim_pozo: todo pozo con ubicacion tiene pad", q(
        "select count(*) from dim_pozo d left join co_pozo_pad p using (pozo_id) where d.lat is not null and p.pad_id is null") == 0,
        "pad_id completo"))
    out.append(("co_hijo: un registro por pozo", q("select count(*) - count(distinct pozo_id) from co_hijo") == 0, "pozo_id unico"))
    out.append(("co_hijo: los hijos cumplen la regla fijada", q(
        f"select count(*) from co_hijo where hijo and not (en_ventana and en_archivo_pozos and con_coordenadas and horizontal "
        f"and not fecha_dudosa and fecha_frac between date '{R.VENTANA_FRAC[0]}' and date '{R.VENTANA_FRAC[1]}')") == 0,
        "ventana, coordenadas, horizontal, fecha no dudosa"))
    out.append(("co_hijo: ningun hijo tiene fecha dudosa", q("select count(*) from co_hijo where hijo and fecha_dudosa") == 0, "excluidos"))
    return out


def _n(x) -> str:
    """Entero con punto de miles (convencion de las paginas del repo)."""
    return f"{int(x):,}".replace(",", ".")


def _pct(a, b) -> str:
    return f"{100 * a / b:.1f}".replace(".", ",") + " %" if b else "s/d"


def pagina_colorado(con) -> str:
    """Pagina wiki/hallazgos/colorado_datos.md: todas las cifras salen de las tablas del warehouse del Colorado."""
    v = dict(con.execute("select clave, valor from mart_co_conciliacion").fetchall())
    g = lambda k: v.get(k, 0)  # noqa: E731
    fuentes = con.execute("select nombre, bytes, sha256 from co_fuentes order by nombre").fetchall()
    primer, ultimo = con.execute("select min(mes), max(mes) from fct_produccion").fetchone()
    e = R.ESTIMACION_SCOUT
    sc_h, sc_c, sc_k = e["hijos"], e["eventos_cercanos"], e["controles"]
    dif = lambda a, b: ("+" if a - b >= 0 else "-") + _n(abs(a - b))  # noqa: E731
    o = []
    o.append("# Colorado (cuenca DJ): datos y conteos de la replicación")
    o.append("")
    o.append("Esta página la escribe el código (`uv run python -m pipeline.colorado.build`) a partir del warehouse del Colorado, "
             "separado de `data/warehouse.duckdb`. Solo cuenta filas, pozos, hijos, padres cercanos y controles con las reglas "
             "fijadas antes de correr (`pipeline/colorado/__init__.py`). No calcula brecha ni rendimiento: eso es el tramo "
             "siguiente, y no se afirma nada causal.")
    o.append("")
    o.append("## Fuentes")
    o.append("")
    o.append("Datos públicos de ECMC (producción mensual 2018 a 2024 y archivo de pozos) y de FracFocus (lista de divulgaciones). "
             "Se usan con atribución a las fuentes y sujetos a los términos de uso de cada sitio. "
             f"La producción cubre de {primer} a {ultimo}.")
    o.append("")
    o.append("| Archivo | Bytes | sha256 |")
    o.append("|---|---:|---|")
    for n, b, s in fuentes:
        o.append(f"| `{n}` | {_n(b) if b is not None else 's/d'} | `{(s or '')[:12]}` |")
    o.append("")
    o.append("## Filas por etapa")
    o.append("")
    o.append("| Etapa | Filas |")
    o.append("|---|---:|")
    for etiqueta, k in [
        ("Filas de producción en la fuente (una por formación y mes)", "prod_filas_fuente"),
        ("Sin pozo o sin mes válido", "prod_filas_sin_pozo_o_mes"),
        ("Tras quedarse con la última revisión de cada fila", "prod_filas_tras_revision"),
        ("Pozo-mes (formaciones y sidetracks sumados)", "prod_pozo_mes"),
        ("Pozos con producción", "prod_pozos"),
        ("Pozos con más de un sidetrack", "prod_pozos_varios_sidetracks"),
        ("Pozo-mes con más de una fila en la fuente", "prod_pozo_mes_con_varias_filas"),
        ("Pozo-mes con cero días producidos", "prod_pozo_mes_cero_dias"),
        ("Pozo-mes con petróleo", "prod_pozo_mes_con_petroleo"),
    ]:
        o.append(f"| {etiqueta} | {_n(g(k))} |")
    o.append("")
    o.append("## Pozos")
    o.append("")
    o.append("| Conjunto | Pozos |")
    o.append("|---|---:|")
    for etiqueta, k in [
        ("Archivo de pozos de ECMC", "pozos_archivo"),
        ("Archivo de pozos con coordenadas", "pozos_archivo_con_coordenadas"),
        ("Pozos con producción que están en el archivo", "pozos_prod_en_archivo"),
        ("Pozos con producción que no están en el archivo", "pozos_prod_fuera_del_archivo"),
        ("Pozos con producción y coordenadas", "pozos_prod_con_coordenadas"),
        ("Pozos con producción horizontales", "pozos_prod_horizontales"),
        ("Pozos con algún mes de petróleo", "pozos_prod_con_petroleo"),
        ("Pozos con primer petróleo censurado (enero de 2018)", "pozos_primer_petroleo_censurado"),
        ("Pads (ubicaciones a menos de 50 m)", "pads"),
        ("Pozos en pads de 3 o más", "pozos_en_pads_de_3_o_mas"),
    ]:
        o.append(f"| {etiqueta} | {_n(g(k))} |")
    o.append("")
    o.append(f"Horizontal: profundidad vertical mayor que {_n(R.HORIZONTAL_TVD_MIN_FT)} ft y profundidad medida menos vertical "
             f"mayor que {_n(R.HORIZONTAL_LATERAL_MIN_FT)} ft. Sin alguno de los dos datos, no es horizontal.")
    o.append("")
    o.append("## De las divulgaciones a los hijos")
    o.append("")
    o.append("| Paso | Pozos |")
    o.append("|---|---:|")
    for etiqueta, k in [
        ("Divulgaciones de FracFocus en Colorado", "ff_divulgaciones"),
        ("Con clave de API inválida", "ff_api_invalidos"),
        ("Pozos distintos", "ff_pozos"),
        ("Pozos que están en el archivo de pozos", "ff_pozos_en_archivo"),
        ("Pozos con producción", "ff_pozos_con_produccion"),
        ("Pozos con fecha de primera divulgación", "ff_pozos_con_fecha"),
        (f"Primera divulgación entre {R.VENTANA_FRAC[0][:7]} y {R.VENTANA_FRAC[1][:7]}", "ff_primera_en_ventana"),
        ("En la ventana, en el archivo y con coordenadas", "ff_ventana_con_coordenadas"),
        ("De esos, horizontales", "ff_ventana_horizontales"),
        ("De esos, con fecha dudosa (más de 30 días después del primer petróleo)", "ff_ventana_horizontales_fecha_dudosa"),
        ("En la ventana con coordenadas pero verticales o sin dato de profundidad", "ff_ventana_verticales_o_sin_dato"),
        ("Hijos (regla fijada)", "hijos"),
        ("Hijos sin producción", "hijos_sin_produccion"),
        ("Hijos con ubicación marcada como planificada", "hijos_ubicacion_planificada"),
    ]:
        o.append(f"| {etiqueta} | {_n(g(k))} |")
    o.append("")
    o.append("## Conteo frente a la estimación de la memoria")
    o.append("")
    base, km1 = f"{R.BASE_MIN_M3_D:g}".replace(".", ","), f"{R.KM_CERCANO:g}".replace(".", ",")
    k2, k5 = f"{R.KM_CONTROL[0]:g}".replace(".", ","), f"{R.KM_CONTROL[1]:g}".replace(".", ",")
    o.append(f"Eventos = (padre, mes de fractura) con caudal base mayor que {base} m3/d. Cercano: a menos de {km1} km del hijo "
             f"más cercano; control: de {k2} a {k5} km.")
    o.append("")
    o.append("| Conteo | Hijos | Eventos cercanos | Controles |")
    o.append("|---|---:|---:|---:|")
    o.append(f"| Estimación de la memoria | {_n(sc_h)} | {_n(sc_c)} | {_n(sc_k)} |")
    filas = [
        ("Regla fijada, solo padres horizontales (corte principal)", g("hijos"), g("ev_regla_horizontales_cercanos"), g("ev_regla_horizontales_controles")),
        ("Regla fijada, todos los padres", g("hijos"), g("ev_regla_todos_cercanos"), g("ev_regla_todos_controles")),
        ("Método de la memoria, solo padres horizontales", g("hijos_memoria"), g("ev_memoria_horizontales_cercanos"), g("ev_memoria_horizontales_controles")),
        ("Método de la memoria, todos los padres", g("hijos_memoria"), g("ev_memoria_todos_cercanos"), g("ev_memoria_todos_controles")),
    ]
    for etiqueta, h, c, k in filas:
        o.append(f"| {etiqueta} | {_n(h)} | {_n(c)} | {_n(k)} |")
    o.append("")
    o.append("Diferencia de la regla fijada, todos los padres, frente a la estimación: "
             f"{dif(g('hijos'), sc_h)} hijos, {dif(g('ev_regla_todos_cercanos'), sc_c)} eventos cercanos, "
             f"{dif(g('ev_regla_todos_controles'), sc_k)} controles.")
    o.append("")
    o.append("Eventos intermedios (de 1 a 2 km, fuera de la brecha), regla fijada: "
             f"{_n(g('ev_regla_horizontales_intermedios'))} con padres horizontales y {_n(g('ev_regla_todos_intermedios'))} con todos. "
             f"Hijos con al menos un padre cercano con base válida: {_n(g('hijos_con_padre_cercano_regla_horizontales'))} "
             f"(padres horizontales) y {_n(g('hijos_con_padre_cercano_regla_todos'))} (todos).")
    o.append("")
    o.append("## Por año de la fractura")
    o.append("")
    o.append("Eventos por año del mes de fractura, regla fijada.")
    o.append("")
    o.append("| Año | Cercanos, horizontales | Controles, horizontales | Cercanos, todos | Controles, todos |")
    o.append("|---|---:|---:|---:|---:|")
    por_anio: dict[int, dict] = {}
    for conj, corte, anio, cer, con_ in con.execute(
            "select conjunto, corte, anio, cercanos, controles from mart_co_eventos_anio where conjunto = 'regla' order by anio, corte").fetchall():
        por_anio.setdefault(anio, {})[corte] = (cer, con_)
    for anio, d in sorted(por_anio.items()):
        h, t = d.get("horizontales", (0, 0)), d.get("todos", (0, 0))
        o.append(f"| {anio} | {_n(h[0])} | {_n(h[1])} | {_n(t[0])} | {_n(t[1])} |")
    o.append("")
    o.append("## Por qué difieren")
    o.append("")
    o.append(f"La memoria toma la divulgación más antigua dentro de la ventana; la regla fijada toma la primera de cada pozo de "
             f"cualquier año, porque un refrac no es un hijo nuevo, y excluye los pozos con fecha dudosa "
             f"({_n(g('ff_ventana_horizontales_fecha_dudosa'))} pozos horizontales en la ventana). "
             f"Con el método de la memoria salen {_n(g('hijos_memoria'))} hijos"
             f"{' (la misma cifra de la estimación)' if g('hijos_memoria') == sc_h else ''}. Además, {_n(g('hijos_memoria_con_coordenadas_sin_horizontal'))} "
             "pozos tienen divulgación en la ventana y coordenadas antes de pedir que sean horizontales. La diferencia restante con "
             "la estimación no se explica con estos datos.")
    o.append("")
    o.append("## Límites")
    o.append("")
    o.append("- No hay etapas ni arena de la fractura; el largo de rama es un proxy (profundidad medida menos vertical).")
    o.append("- El primer petróleo está censurado en enero de 2018, cuando empieza la producción descargada.")
    o.append("- La fecha de la fractura viene de un formulario de divulgación, no de un mes de reporte; se la contrasta con el primer petróleo.")
    o.append("- La fuente trae una fila por formación y mes: se suman al pozo y mes, y los días son el máximo de las filas.")
    o.append("- Algunos hijos tienen la ubicación marcada como planificada y no medida; la cifra está en la tabla de hijos.")
    o.append("- El corte principal usa solo padres horizontales; el corte con todos los padres se publica al lado.")
    o.append("")
    return "\n".join(o)


def construir(raw: Path = ingest.RAW, db: Path = DB, pagina: Path | None = PAGINA) -> int:
    m = ingest.cargar_manifiesto(raw / "manifest.json")
    faltan = [n for n in ([f"produccion_{a}" for a in R.ANIOS_PRODUCCION] + ["pozos", "fracfocus_disclosure_list"])
              if n not in m or not (raw / m[n]["ruta"]).exists()]
    if faltan:
        print(f"faltan datos en {raw}: {', '.join(faltan)}. Corre `uv run python -m pipeline.colorado.ingest`.", file=sys.stderr)
        return 2
    db.parent.mkdir(parents=True, exist_ok=True)
    stage_base = db.parent
    with tempfile.TemporaryDirectory(dir=stage_base, prefix="tmp_stage_") as tmp:
        tmp = Path(tmp)
        csvs = []
        for a in R.ANIOS_PRODUCCION:
            destino = tmp / f"prod_{a}.csv"
            ingest.produccion_a_csv(raw / m[f"produccion_{a}"]["ruta"], destino)
            csvs.append(destino)
        pozos_csv = tmp / "pozos.csv"
        ingest.pozos_a_csv(raw / m["pozos"]["ruta"], pozos_csv)
        con = duckdb.connect(str(db))
        try:
            build(con, csvs, pozos_csv, raw / m["fracfocus_disclosure_list"]["ruta"], m)
            res = controles(con)
            for nombre, ok, detalle in res:
                print(f"[{'OK ' if ok else 'NO '}] {nombre} ({detalle})")
            if pagina is not None:
                pagina.parent.mkdir(parents=True, exist_ok=True)
                pagina.write_text(pagina_colorado(con), encoding="utf-8")
                print(f"pagina: {pagina}")
        finally:
            con.close()
    if not all(ok for _, ok, _ in res):
        print("FALLO un control bloqueante", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.colorado.build", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default=str(ingest.RAW))
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--pagina", default=str(PAGINA), help="ruta de la pagina de datos ('' para no escribirla)")
    a = ap.parse_args(argv)
    return construir(Path(a.raw_dir), Path(a.db), Path(a.pagina) if a.pagina else None)


if __name__ == "__main__":
    sys.exit(main())
