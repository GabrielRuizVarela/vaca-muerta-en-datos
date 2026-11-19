"""Arma el warehouse de Wyoming (data/wyoming/warehouse.duckdb) desde data/wyoming/raw y escribe la pagina de datos.

    uv run python -m pipeline.wyoming.build

Es un warehouse APARTE: no toca data/warehouse.duckdb. Las reglas estan fijadas en pipeline/wyoming/__init__.py. Las tablas
usan los nombres y columnas que consume el estudio de interferencia (fct_produccion, ultimo_mes, dim_pozo, co_hijo,
co_pozo_pad) y se reconstruyen enteras con create or replace: dos corridas sobre las mismas entradas dan las mismas filas.
Este tramo solo CUENTA hijos, padres cercanos y controles (mart_co_conciliacion); no calcula brecha ni rendimiento.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

from pipeline import colorado as C
from pipeline import wyoming as R
from pipeline.ingest import DATA, ROOT
from pipeline.wyoming import ingest

SQL_DIR = Path(__file__).parent / "sql"
DB = DATA / "wyoming" / "warehouse.duckdb"
PAGINA = ROOT / "wiki" / "hallazgos" / "wyoming_datos.md"


def parametros() -> dict:
    return {
        "bbl_a_m3": R.BBL_A_M3, "mcf_a_miles_m3": C.MCF_A_MILES_M3, "ft_a_m": R.FT_A_M,
        "horizontal_tvd_min_ft": R.HORIZONTAL_TVD_MIN_FT, "horizontal_lateral_min_ft": R.HORIZONTAL_LATERAL_MIN_FT,
        "ventana_ini": R.VENTANA_FRAC[0], "ventana_fin": R.VENTANA_FRAC[1], "fecha_dudosa_dias": R.FECHA_DUDOSA_DIAS,
        "edad_min": R.EDAD_MIN_MESES, "base_min": R.BASE_MIN_M3_D, "km_cercano": R.KM_CERCANO,
        "km_control_min": R.KM_CONTROL[0], "km_max": R.KM_MAX, "pad_km": R.PAD_KM, "km_por_grado": R.KM_POR_GRADO,
    }


def _lit(p: Path) -> str:
    return str(p).replace("'", "''")


def build(con: duckdb.DuckDBPyConnection, produccion_csvs: list[Path], pozos_csv: Path,
          fuentes: dict | None = None, encabezados: dict[str, list[str]] | None = None) -> None:
    """Corre los tres SQL en orden sobre CSV de texto. `fuentes` (el manifiesto) llena co_fuentes y `encabezados`
    (nombre de CSV a encabezados originales del XLSX) llena wy_encabezados_xlsx; sin `encabezados` se leen del CSV."""
    params = parametros() | {
        "produccion_csvs": "[" + ", ".join(f"'{_lit(p)}'" for p in produccion_csvs) + "]",
        "pozos_csv": _lit(pozos_csv),
    }
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        con.execute(sql_file.read_text().format(**params))
    con.execute("create or replace table co_fuentes (nombre varchar, bytes bigint, sha256 varchar)")
    for nombre, e in sorted((fuentes or {}).items()):
        con.execute("insert into co_fuentes values (?, ?, ?)", [nombre, e.get("bytes"), e.get("sha256")])
    con.execute("create or replace table wy_encabezados_xlsx (archivo varchar, encabezado varchar)")
    for p in produccion_csvs:
        cols = (encabezados or {}).get(p.name) or p.read_text(encoding="utf-8").splitlines()[0].split(",")
        con.execute("insert into wy_encabezados_xlsx values (?, ?)", [p.name, " | ".join(cols)])


def controles(con) -> list[tuple[str, bool, str]]:
    """Controles bloqueantes del warehouse de Wyoming: (nombre, ok, detalle)."""
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
        f"and primer_mes_petroleo is not null and not fecha_dudosa "
        f"and fecha_frac between date '{R.VENTANA_FRAC[0]}' and date '{R.VENTANA_FRAC[1]}')") == 0,
        "ventana, coordenadas, horizontal, con petroleo, fecha no dudosa"))
    out.append(("co_hijo: ningun hijo tiene fecha dudosa", q("select count(*) from co_hijo where hijo and fecha_dudosa") == 0, "excluidos"))
    return out


# Filas de las tablas de la pagina de datos (rotulo, clave de mart_co_conciliacion); las usan la pagina y los claims.
FILAS_ETAPAS = [
    ("Filas de producción en la fuente (una por pozo, año y reservorio)", "prod_filas_fuente"),
    ("Sin pozo o sin año válido", "prod_filas_sin_pozo_o_anio"),
    ("Pozo-año distintos", "prod_pozo_anio"),
    ("Pozo-mes (años abiertos en doce meses, filas repetidas sumadas)", "prod_pozo_mes"),
    ("Pozos con producción", "prod_pozos"),
    ("Pozo-año con más de una fila en la fuente", "prod_pozo_anio_con_varias_filas"),
    ("Pozo-mes con más de una fila aportante", "prod_pozo_mes_con_varias_filas"),
    ("Pozo-mes con cero días producidos", "prod_pozo_mes_cero_dias"),
    ("Pozo-mes sin días válidos", "prod_pozo_mes_sin_dias_validos"),
    ("Pozo-mes con petróleo", "prod_pozo_mes_con_petroleo"),
]

FILAS_POZOS = [
    ("Encabezados de WOGCC", "pozos_archivo"),
    ("Encabezados con coordenadas", "pozos_archivo_con_coordenadas"),
    ("Pozos con producción que están en los encabezados", "pozos_prod_en_archivo"),
    ("Pozos con producción que no están en los encabezados", "pozos_prod_fuera_del_archivo"),
    ("Pozos con producción y coordenadas", "pozos_prod_con_coordenadas"),
    ("Pozos con producción horizontales", "pozos_prod_horizontales"),
    ("Pozos con algún mes de petróleo", "pozos_prod_con_petroleo"),
    ("Pozos con primer petróleo censurado (primer mes descargado)", "pozos_primer_petroleo_censurado"),
    ("Pads (ubicaciones a menos de 50 m)", "pads"),
    ("Pozos en pads de 3 o más", "pozos_en_pads_de_3_o_mas"),
]

FILAS_HIJOS = [
    ("Pozos con fecha de primera terminación (FIRSTCOMP)", "fc_pozos_con_fecha"),
    ("FIRSTCOMP vacío", "fc_vacios"),
    ("FIRSTCOMP que no se lee como fecha válida", "fc_no_parsean"),
    ("De esos, de siete dígitos que se leen como fecha válida de dos maneras (ambiguos)", "fc_ambiguas"),
    ("Pozos con fecha y con producción", "fc_pozos_con_produccion"),
    (f"Primera terminación entre {R.VENTANA_FRAC[0][:7]} y {R.VENTANA_FRAC[1][:7]}", "fc_primera_en_ventana"),
    ("En la ventana, en los encabezados y con coordenadas", "fc_ventana_con_coordenadas"),
    ("De esos, horizontales", "fc_ventana_horizontales"),
    ("De esos, con fecha dudosa (más de 30 días después del primer petróleo)", "fc_ventana_horizontales_fecha_dudosa"),
    ("En la ventana con coordenadas pero verticales o sin dato de profundidad", "fc_ventana_verticales_o_sin_dato"),
    ("En la ventana, horizontales y con coordenadas, pero sin petróleo (excluidos)", "hijos_sin_petroleo_excluidos"),
    ("Hijos (regla fijada)", "hijos"),
    ("Hijos sin producción", "hijos_sin_produccion"),
]


def _n(x) -> str:
    """Entero con punto de miles (convencion de las paginas del repo)."""
    return f"{int(x):,}".replace(",", ".")


def pagina_wyoming(con) -> str:
    """Pagina wiki/hallazgos/wyoming_datos.md: todas las cifras salen de las tablas del warehouse de Wyoming."""
    v = dict(con.execute("select clave, valor from mart_co_conciliacion").fetchall())
    g = lambda k: v.get(k, 0)  # noqa: E731
    fuentes = con.execute("select nombre, bytes, sha256 from co_fuentes order by nombre").fetchall()
    primer, ultimo = con.execute("select min(mes), max(mes) filter (where petroleo_m3 > 0 or gas_miles_m3 > 0 or agua_m3 > 0) "
                                 "from fct_produccion").fetchone()
    enc = con.execute("select archivo, encabezado from wy_encabezados_xlsx order by archivo").fetchall()
    o = []
    o.append("# Wyoming: datos y conteos de la replicación")
    o.append("")
    o.append("Esta página la escribe el código (`uv run python -m pipeline.wyoming.build`) a partir del warehouse de Wyoming, "
             "separado de `data/warehouse.duckdb`. Solo cuenta filas, pozos, hijos, padres cercanos y controles con las reglas "
             "fijadas antes de correr (`pipeline/wyoming/__init__.py`). No calcula brecha ni rendimiento: eso es el tramo "
             "siguiente, y no se afirma nada causal.")
    o.append("")
    o.append("## Fuentes")
    o.append("")
    o.append("Datos públicos de WOGCC (Wyoming Oil and Gas Conservation Commission): encabezados de pozos y producción mensual "
             "por pozo y año, bajados del menú de descargas del regulador por URL directa, una vez por archivo. Se usan con "
             "atribución a la fuente y sujetos a los términos de uso del sitio, que dicen textualmente (menú principal y pie de "
             "datos de WOGCC, `pipeline.wyo.gov`):")
    o.append("")
    o.append("> No Warranty is made by the Wyoming Oil and Gas Conservation Commission for the use of this data. Those making use of, "
             "or relying on, this information assume all risks and liability arising from such use or reliance.")
    o.append(">")
    o.append("> Scraping of website data is not allowed.")
    o.append("")
    o.append("Los términos no traen prohibición de usar ni publicar cifras derivadas de los archivos que el menú ofrece para "
             "descargar; esta es nuestra lectura de los términos, no una licencia. Por la segunda línea, la ingesta baja solo los "
             "archivos de ese menú, por URL directa, una vez por archivo, sin recorrer páginas ni usar formularios de consulta ni "
             "consultas por pozo. Nada de Wyoming se redistribuye crudo: solo se publican cifras derivadas. "
             f"La producción cubre de {primer} a {ultimo}, el último mes con producción reportada: los meses que faltan del año en curso "
             "llegan en cero por el formato de una fila por pozo y año.")
    o.append("")
    o.append("| Archivo | Bytes | sha256 |")
    o.append("|---|---:|---|")
    for n, b, s in fuentes:
        o.append(f"| `{n}` | {_n(b) if b is not None else 's/d'} | `{(s or '')[:12]}` |")
    o.append("")
    o.append("Unidades: el petróleo se toma como barriles y pasa a m3 (x 0,158987); el gas se toma como Mcf y pasa a miles de m3 "
             "(x 0,0283168); el agua se toma como barriles y pasa a m3. Son la convención del regulador: el archivo no las escribe. "
             "TD se toma como profundidad vertical total y MD como profundidad medida; que TD sea vertical no se pudo confirmar.")
    o.append("")
    o.append("Encabezados exactos de cada XLSX de producción, leídos del archivo:")
    o.append("")
    for archivo, encabezado in enc:
        o.append(f"- `{archivo}`: {encabezado}")
    o.append("")
    o.append("## Filas por etapa")
    o.append("")
    o.append("| Etapa | Filas |")
    o.append("|---|---:|")
    for etiqueta, k in FILAS_ETAPAS:
        o.append(f"| {etiqueta} | {_n(g(k))} |")
    o.append("")
    o.append("## Pozos")
    o.append("")
    o.append("| Conjunto | Pozos |")
    o.append("|---|---:|")
    for etiqueta, k in FILAS_POZOS:
        o.append(f"| {etiqueta} | {_n(g(k))} |")
    o.append("")
    o.append(f"Horizontal: profundidad vertical (TD) mayor que {_n(R.HORIZONTAL_TVD_MIN_FT)} ft y profundidad medida (MD) menos "
             f"vertical mayor que {_n(R.HORIZONTAL_LATERAL_MIN_FT)} ft; la columna de dirección del encabezado no se usa. "
             "Sin alguno de los dos datos, no es horizontal.")
    o.append("")
    o.append("## De las terminaciones a los hijos")
    o.append("")
    o.append("| Paso | Pozos |")
    o.append("|---|---:|")
    for etiqueta, k in FILAS_HIJOS:
        o.append(f"| {etiqueta} | {_n(g(k))} |")
    o.append("")
    o.append("La fecha del hijo es FIRSTCOMP, la fecha de primera terminación del regulador: no es una fecha de fractura, y un "
             "refrac no se distingue de un hijo nuevo porque hay una sola fecha por pozo. FIRSTCOMP viene como AAAAMMDD o "
             "AAAAMDD (mes sin cero a la izquierda); un valor de siete dígitos que también se lee como AAAAMMD es ambiguo y el pozo "
             "queda afuera.")
    o.append("")
    o.append(f"Entre los {_n(g('hijos'))} hijos, el mes de FIRSTCOMP es el del primer petróleo en "
             f"{_n(g('hijos_terminacion_mes_primer_petroleo'))}, el primer petróleo es posterior en {_n(g('hijos_primer_petroleo_posterior'))} "
             f"y anterior en {_n(g('hijos_primer_petroleo_anterior'))}. Una fecha de terminación que cae más tarde que el inicio de la "
             "fractura corre el mes 0 hacia adelante: si pasa en Wyoming, la base de los meses -3 a -1 incluye meses posteriores a la "
             "fractura y el mes 1 queda más lejos de ella. Eso se publica como límite y no como explicación: no se probó cuánto del "
             "resultado sale de ahí, y la lectura no separa \"no hay huella\" de \"el mes 0 está corrido\".")
    o.append("")
    o.append("## Hijos, padres cercanos y controles")
    o.append("")
    base, km1 = f"{R.BASE_MIN_M3_D:g}".replace(".", ","), f"{R.KM_CERCANO:g}".replace(".", ",")
    k2, k5 = f"{R.KM_CONTROL[0]:g}".replace(".", ","), f"{R.KM_CONTROL[1]:g}".replace(".", ",")
    o.append(f"Eventos = (padre, mes de terminación) con caudal base mayor que {base} m3/d. Cercano: a menos de {km1} km del hijo "
             f"más cercano; control: de {k2} a {k5} km.")
    o.append("")
    o.append("| Conteo | Hijos | Eventos cercanos | Controles |")
    o.append("|---|---:|---:|---:|")
    for etiqueta, h, c, k in [
        ("Regla fijada, solo padres horizontales (corte principal)", g("hijos"), g("ev_regla_horizontales_cercanos"), g("ev_regla_horizontales_controles")),
        ("Regla fijada, todos los padres", g("hijos"), g("ev_regla_todos_cercanos"), g("ev_regla_todos_controles")),
    ]:
        o.append(f"| {etiqueta} | {_n(h)} | {_n(c)} | {_n(k)} |")
    o.append("")
    o.append("Eventos intermedios (de 1 a 2 km, fuera de la brecha), regla fijada: "
             f"{_n(g('ev_regla_horizontales_intermedios'))} con padres horizontales y {_n(g('ev_regla_todos_intermedios'))} con todos. "
             f"Hijos con al menos un padre cercano con base válida: {_n(g('hijos_con_padre_cercano_regla_horizontales'))} "
             f"(padres horizontales) y {_n(g('hijos_con_padre_cercano_regla_todos'))} (todos).")
    o.append("")
    o.append("## Por año de la terminación")
    o.append("")
    o.append("Eventos por año del mes de terminación, regla fijada.")
    o.append("")
    o.append("| Año | Cercanos, horizontales | Controles, horizontales | Cercanos, todos | Controles, todos |")
    o.append("|---|---:|---:|---:|---:|")
    por_anio: dict[int, dict] = {}
    for _conj, corte, anio, cer, con_ in con.execute(
            "select conjunto, corte, anio, cercanos, controles from mart_co_eventos_anio order by anio, corte").fetchall():
        por_anio.setdefault(anio, {})[corte] = (cer, con_)
    for anio, d in sorted(por_anio.items()):
        h, t = d.get("horizontales", (0, 0)), d.get("todos", (0, 0))
        o.append(f"| {anio} | {_n(h[0])} | {_n(h[1])} | {_n(t[0])} | {_n(t[1])} |")
    o.append("")
    o.append("## Límites")
    o.append("")
    o.append("- No hay fecha de fractura: se usa FIRSTCOMP, la primera terminación del regulador; un refrac no se distingue de un hijo nuevo.")
    o.append("- Los bloques espaciales de 5 km usan la proyección de `pipeline/bloques.py`, centrada en la latitud de Vaca Muerta: a las latitudes de Wyoming (41 a 45 grados norte) un bloque es algo más angosto que 5 km de este a oeste y mide 5 km de norte a sur. No se midió cuánto cambia el intervalo.")
    o.append("- No hay etapas ni arena de la fractura; el largo de rama es un proxy (profundidad medida menos vertical).")
    o.append("- El primer petróleo está censurado en el primer mes descargado, cuando empieza la producción.")
    o.append("- La fuente trae una fila por pozo y año con doce columnas por mes: se abre en doce meses, se suma al pozo y mes, y los días son el máximo de las filas.")
    o.append(f"- Los días fuera del rango 0 a 31 (casi siempre 99 en la fuente, un código y no un conteo) se toman como desconocidos: {_n(g('prod_pozo_mes_sin_dias_validos'))} pozo-mes. El máximo válido se topa en el largo del mes.")
    o.append("- El petróleo NULL del mes es 0; el gas se toma como Mcf y el agua como barriles, convención del regulador no escrita en el archivo.")
    o.append("- TD se toma como profundidad vertical sin confirmación; la columna de dirección del encabezado no se usa.")
    o.append("- El corte principal usa solo padres horizontales; el corte con todos los padres se publica al lado.")
    o.append("- El corte con todos los padres de esta página y el de la página de replicación salen de dos armados distintos y sus "
             "conteos no coinciden del todo; la diferencia no se reconcilió. El corte principal coincide en las dos páginas.")
    caso = con.execute("select s.fecha_firstcomp, h.primer_mes_petroleo, h.en_ventana, h.horizontal, h.fecha_dudosa, "
                       "h.dias_desde_primer_petroleo from co_hijo h join stg_wy_pozos s using (pozo_id) where pozo_id = 720921").fetchone()
    if caso:
        fc, pm, vent, hor, dud, dias = caso
        o.append(f"- La auditoría de fuentes anotó una discrepancia para el pozo 720921: el encabezado trae FIRSTCOMP {fc} y la producción "
                 f"empieza en {str(pm)[:7]}, {_n(dias)} días antes. Es consistente con una terminación nueva de un pozo viejo (no se pudo "
                 f"confirmar): {'cae' if vent else 'no cae'} en la ventana, {'es' if hor else 'no es'} horizontal y "
                 f"{'queda marcado' if dud else 'no queda marcado'} como fecha dudosa, así que {'no entra' if not (hor and not dud) else 'entra'} "
                 "entre los hijos. La regla de fecha dudosa existe para estos casos.")
    o.append(f"- {_n(g('pozos_prod_fuera_del_archivo'))} pozos con producción no están en los encabezados: no tienen coordenadas ni "
             "FIRSTCOMP y no entran como hijos, padres ni controles. Pueden estar en el archivo de pozos taponados y abandonados, "
             "que no se usa; no se midió cuánto cambiaría una cifra si entraran.")
    o.append("")
    return "\n".join(o)


def construir(raw: Path = ingest.RAW, db: Path = DB, pagina: Path | None = PAGINA) -> int:
    m = ingest.cargar_manifiesto(raw / "manifest.json")
    faltan = [n for n in ("pozos", "produccion") if n not in m or not (raw / m[n]["ruta"]).exists()]
    if faltan:
        print(f"faltan datos en {raw}: {', '.join(faltan)}. Corre `uv run python -m pipeline.wyoming.ingest`.", file=sys.stderr)
        return 2
    db.parent.mkdir(parents=True, exist_ok=True)
    miembros = ingest.miembros_produccion(raw / m["produccion"]["ruta"])
    if not miembros:
        print(f"{m['produccion']['ruta']}: el zip no trae XLSX", file=sys.stderr)
        return 2
    print(f"produccion: {len(miembros)} XLSX ({', '.join(miembros)})")
    with tempfile.TemporaryDirectory(dir=db.parent, prefix="tmp_stage_") as tmp:
        tmp = Path(tmp)
        csvs, encabezados = [], {}
        with zipfile.ZipFile(raw / m["produccion"]["ruta"]) as z:
            for miembro in miembros:
                destino = raw / (Path(miembro).stem + ".csv")
                encabezados[destino.name] = ingest.xlsx_a_csv(z.read(miembro), destino)
                csvs.append(destino)
                print(f"  {miembro} -> {destino.name} ({destino.stat().st_size // 1_000_000} MB)")
        pozos_csv = tmp / "pozos.csv"
        print(f"pozos: {ingest.pozos_a_csv(raw / m['pozos']['ruta'], pozos_csv)} filas")
        con = duckdb.connect(str(db))
        try:
            build(con, csvs, pozos_csv, m, encabezados)
            res = controles(con)
            for nombre, ok, detalle in res:
                print(f"[{'OK ' if ok else 'NO '}] {nombre} ({detalle})")
            if pagina is not None:
                pagina.parent.mkdir(parents=True, exist_ok=True)
                pagina.write_text(pagina_wyoming(con), encoding="utf-8")
                print(f"pagina: {pagina}")
        finally:
            con.close()
    if not all(ok for _, ok, _ in res):
        print("FALLO un control bloqueante", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.wyoming.build", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default=str(ingest.RAW))
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--pagina", default=str(PAGINA), help="ruta de la pagina de datos ('' para no escribirla)")
    a = ap.parse_args(argv)
    return construir(Path(a.raw_dir), Path(a.db), Path(a.pagina) if a.pagina else None)


if __name__ == "__main__":
    sys.exit(main())
