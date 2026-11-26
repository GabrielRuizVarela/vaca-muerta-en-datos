"""Reconciliation between layers, schema drift, freshness and lineage."""
import csv
from datetime import date
from pathlib import Path

import duckdb
import pytest

from pipeline import checks, linaje
from pipeline.build import SQL_DIR, build
from pipeline.ingest import ROOT
from tests.test_pipeline import FRAC_COLS, PROD_COLS, frac_row, prod_row, write_csv

PROD = "produccion_no_convencional"
FRAC = "fractura_adjunto_iv"
HOY = date(2024, 8, 15)


def construir(tmp_path, prod_rows, frac_rows):
    """Warehouse built from CSV files on disk; returns it with the raw inputs the build read."""
    con = duckdb.connect()
    inputs = {
        PROD: write_csv(tmp_path / "p.csv", PROD_COLS, prod_rows),
        FRAC: write_csv(tmp_path / "f.csv", FRAC_COLS, frac_rows),
        "seed_operadores": ROOT / "seeds" / "operadores.csv",
    }
    build(con, inputs)
    return con, inputs


def correr(con, inputs, nombre, hoy=HOY):
    informe = checks.run(con, inputs=inputs, hoy=hoy)
    return next(c for c in informe["checks"] if c["nombre"].startswith(nombre))


@pytest.fixture
def datos(tmp_path):
    prods = [prod_row(1, 2024, m, 100 * m) for m in range(1, 7)] + [prod_row(2, 2024, 6, 50, gas=7, agua=3)]
    fracs = [frac_row(10, 1, "2023-12-01"), frac_row(11, 1, "2024-01-01")]
    return construir(tmp_path, prods, fracs)


NUEVOS = ("Conciliación", "Deriva de esquema", "Frescura")


def test_all_new_checks_pass_on_a_clean_warehouse(datos):
    con, inputs = datos
    informe = checks.run(con, inputs=inputs, hoy=HOY)
    nuevos = [c for c in informe["checks"] if c["nombre"].startswith(NUEVOS)]
    assert len(nuevos) == 9
    assert all(c["ok"] and not c.get("omitido") for c in nuevos), [c["nombre"] for c in nuevos if not c["ok"]]
    assert informe["bloqueantes_fallidos"] == 0


def test_registry_has_29_checks_and_unique_names():
    nombres = [c.nombre for c in checks.CHECKS]
    assert len(nombres) == 29 and len(set(nombres)) == 29


def test_raw_checks_are_marked_skipped_without_inputs(datos):
    con, _ = datos
    informe = checks.run(con, hoy=HOY)
    omitidos = [c["nombre"] for c in informe["checks"] if c.get("omitido")]
    assert len(omitidos) == 4  # two raw row counts and two schema drift checks
    assert all(c["ok"] for c in informe["checks"] if c.get("omitido"))


def test_report_is_deterministic_for_a_fixed_date(datos):
    con, inputs = datos
    assert checks.run(con, inputs=inputs, hoy=HOY) == checks.run(con, inputs=inputs, hoy=HOY)


# ------------------------------------------------------------ reconciliation

def test_raw_rows_reconcile_with_staging_and_detect_a_difference(datos):
    con, inputs = datos
    c = correr(con, inputs, "Conciliación: filas del CSV de producción")
    assert c["ok"] and "7 filas y stg_produccion 7" in c["detalle"]
    with inputs[PROD].open("a", newline="", encoding="utf-8") as f:  # a source row that the warehouse never saw
        csv.DictWriter(f, fieldnames=PROD_COLS).writerow(prod_row(9, 2024, 1, 1))
    c = correr(con, inputs, "Conciliación: filas del CSV de producción")
    assert not c["ok"] and c["muestra"] == [{"raw": 8, "staging": 7, "diferencia": -1}]


def test_staging_to_fact_rows_explain_dropped_rows(tmp_path):
    con, inputs = construir(tmp_path, [prod_row(1, 2024, 1, 100), prod_row("", 2024, 1, 5), prod_row(2, "", "", 5)], [])
    c = correr(con, inputs, "Conciliación: filas de stg_produccion contra fct")
    assert c["ok"] and "3 filas; 2 se descartan" in c["detalle"] and "debe tener 1" in c["detalle"]
    con.execute("delete from fct_produccion")
    assert not correr(con, inputs, "Conciliación: filas de stg_produccion contra fct")["ok"]


def test_volumes_reconcile_with_clipped_negatives_and_dropped_rows(tmp_path):
    con, inputs = construir(tmp_path, [prod_row(1, 2023, 1, 100), prod_row(1, 2024, 1, -30, gas=4),
                                       prod_row("", 2024, 1, 999)], [])
    c = correr(con, inputs, "Conciliación: volúmenes")
    assert c["ok"]
    assert "suma 1.069 m3" in c["detalle"] and "aportan 999 m3" in c["detalle"] and "cero -30 m3" in c["detalle"]
    assert "fct_produccion suma 100 m3" in c["detalle"]
    con.execute("update fct_produccion set petroleo_m3 = petroleo_m3 + 5 where year(mes) = 2023")
    c = correr(con, inputs, "Conciliación: volúmenes")
    assert not c["ok"] and c["muestra"][0]["anio"] == 2023 and c["muestra"][0]["diferencia"] == 5


def test_wells_in_dim_pozo_match_fact(datos):
    con, inputs = datos
    assert correr(con, inputs, "Conciliación: pozos de dim_pozo")["ok"]
    con.execute("delete from dim_pozo where pozo_id = 2")
    c = correr(con, inputs, "Conciliación: pozos de dim_pozo")
    assert not c["ok"] and c["muestra"] == [{"dim_pozo": 1, "fct_produccion": 2}]


def test_fractured_wells_explain_future_only_wells(tmp_path):
    prods = [prod_row(p, 2024, 1, 10) for p in (1, 2, 3)]
    fracs = [frac_row(10, 1, "2023-11-01"), frac_row(11, 1, "2023-12-01"), frac_row(12, 2, "2999-01-01"),
             frac_row(13, 3, "2999-01-01"), frac_row(14, 3, "2023-12-01")]
    con, inputs = construir(tmp_path, prods, fracs)
    c = correr(con, inputs, "Conciliación: pozos fracturados")
    # wells 1, 2, 3 in stg; well 2 has only a future job; well 3 keeps one valid job
    assert c["ok"] and "3 pozos distintos" in c["detalle"] and "(1) quedan fuera" in c["detalle"]
    assert "debe tener 2 (tiene 2)" in c["detalle"] and "3 trabajos (tiene 3)" in c["detalle"]
    con.execute("delete from dim_fractura_pozo where pozo_id = 1")
    c = correr(con, inputs, "Conciliación: pozos fracturados")
    assert not c["ok"] and {f["medida"] for f in c["muestra"]} == {"pozos", "trabajos"}


# ------------------------------------------------------------ schema drift

def test_expected_columns_are_parsed_from_the_staging_sql():
    sql = ("create or replace table a as select p.uno, p.dos, o.otro from read_csv('{ds}', header = true) p "
           "left join o on o.x = p.tres;\n"
           "create or replace table b as select f.UNO from read_csv('{otro_ds}') f;\n"
           "create or replace table c as select s.x from read_csv('{seed_ops}') s;")
    assert checks.columnas_esperadas(sql) == {"ds": {"uno", "dos", "tres"}, "otro_ds": {"uno"}}


def test_expected_columns_of_the_real_staging_cover_what_the_fixture_files_carry():
    esperadas = checks.COLUMNAS_ESPERADAS
    assert set(esperadas) == {PROD, FRAC}
    assert {"idpozo", "prod_pet", "anio", "mes", "rectificado"} <= esperadas[PROD]
    assert {"id_base_fractura_adjiv", "fecha_inicio_fractura", "empresa_informante"} <= esperadas[FRAC]
    assert esperadas[PROD] <= set(PROD_COLS) and esperadas[FRAC] <= set(FRAC_COLS)
    for ds in esperadas:  # known-unused columns never overlap with the ones that staging reads
        assert not (esperadas[ds] & checks.COLUMNAS_SIN_USO[ds])


def test_a_renamed_column_fails_loudly(datos):
    con, inputs = datos
    renombradas = [("prod_petroleo" if c == "prod_pet" else c) for c in PROD_COLS]
    inputs = {**inputs, PROD: write_csv(inputs[PROD].parent / "renombrada.csv", renombradas, [])}
    informe = checks.run(con, inputs=inputs, hoy=HOY)
    falta = next(c for c in informe["checks"] if c["nombre"].startswith("Deriva de esquema: columnas esperadas"))
    assert falta["severidad"] == "bloqueante" and not falta["ok"]
    assert falta["muestra"] == [{"dataset": PROD, "columna": "prod_pet"}]
    assert "produccion_no_convencional.prod_pet" in falta["detalle"]
    assert informe["bloqueantes_fallidos"] >= 1
    nueva = next(c for c in informe["checks"] if c["nombre"].startswith("Deriva de esquema: columnas nuevas"))
    assert nueva["muestra"] == [{"dataset": PROD, "columna": "prod_petroleo"}]


def test_an_extra_column_only_warns_and_known_ones_do_not(datos):
    con, inputs = datos
    con2 = duckdb.connect()
    cols = PROD_COLS + ["columna_nueva", "Cuenca"]  # a new one, and a known one in different case
    fuente = write_csv(inputs[PROD].parent / "extra.csv", cols, [])
    faltan, nuevas = checks.deriva_esquema(con2, {PROD: fuente})
    assert faltan == [] and nuevas == [{"dataset": PROD, "columna": "columna_nueva"}]
    informe = checks.run(con, inputs={**inputs, PROD: fuente}, hoy=HOY)
    nueva = next(c for c in informe["checks"] if c["nombre"].startswith("Deriva de esquema: columnas nuevas"))
    assert nueva["severidad"] == "aviso" and not nueva["ok"] and "columna_nueva" in nueva["detalle"]
    falta = next(c for c in informe["checks"] if c["nombre"].startswith("Deriva de esquema: columnas esperadas"))
    assert falta["ok"]


def test_header_comparison_is_case_insensitive(tmp_path):
    cols = [c.upper() for c in PROD_COLS]
    fuente = write_csv(tmp_path / "mayus.csv", cols, [])
    assert checks.deriva_esquema(duckdb.connect(), {PROD: fuente}) == ([], [])


# ------------------------------------------------------------ freshness

def test_months_of_lag():
    assert checks.meses_de_atraso(date(2024, 6, 1), date(2024, 6, 30)) == 0
    assert checks.meses_de_atraso(date(2024, 6, 1), date(2024, 9, 1)) == 3
    assert checks.meses_de_atraso(date(2023, 11, 1), date(2024, 2, 10)) == 3
    assert checks.meses_de_atraso(date(2023, 11, 1), date(2024, 3, 1)) == 4


def test_freshness_warns_only_beyond_three_months(datos):  # last month with data: 2024-06
    con, inputs = datos
    assert correr(con, inputs, "Frescura", hoy=date(2024, 9, 30))["ok"]       # 3 months behind
    c = correr(con, inputs, "Frescura", hoy=date(2024, 10, 1))                # 4 months behind
    assert c["severidad"] == "aviso" and not c["ok"]
    assert c["muestra"] == [{"ultimo_mes": "2024-06", "hoy": "2024-10-01", "meses_de_atraso": 4}]
    assert "4 meses de atraso" in c["detalle"]
    assert checks.run(con, inputs=inputs, hoy=date(2024, 10, 1))["bloqueantes_fallidos"] == 0


def test_freshness_defaults_to_today(datos):
    con, inputs = datos
    informe = checks.run(con, inputs=inputs)
    c = next(c for c in informe["checks"] if c["nombre"].startswith("Frescura"))
    assert c["muestra"][0]["hoy"] == date.today().isoformat()


# ------------------------------------------------------------ lineage

def test_lineage_parser_on_a_small_sql():
    sql = """
    -- comentario: from fantasma
    create or replace table stg_a as
    select * from read_csv('{ds_uno}', header = true) x left join operadores o on o.k = x.k;

    create or replace table operadores as select * from read_csv('{seed_operadores}');

    create or replace table fct_b as
    with t as (select * from stg_a) select * from t join stg_a using (id);

    create or replace view mart_c as
    select year(mes), count(*) from fct_b group by 1;
    """
    assert linaje.linaje_archivo(sql) == [
        ("fct_b", "stg_a"), ("mart_c", "fct_b"), ("operadores", "seed:operadores"),
        ("stg_a", "operadores"), ("stg_a", "raw:ds_uno")]


def test_a_value_the_build_takes_from_the_manifest_is_an_origin_of_its_table():
    sql = """
    create or replace table corte as select date '{fecha_extraccion}' as fecha;

    create or replace table stg_a as
    select * from read_csv('{ds_uno}') where f <= (select fecha from corte);
    """
    assert linaje.linaje_archivo(sql) == [
        ("corte", "manifiesto:fecha_extraccion"), ("stg_a", "corte"), ("stg_a", "raw:ds_uno")]
    assert linaje.tipo("manifiesto:fecha_extraccion") == "manifiesto"
    pares = set(linaje.linaje(SQL_DIR))
    assert ("extraccion_fractura", "manifiesto:fecha_extraccion") in pares
    assert ("dim_fractura_pozo", "extraccion_fractura") in pares


def test_every_table_created_in_the_sql_has_a_lineage_row_and_exists_in_the_warehouse(datos):
    con, _ = datos
    creadas = {t for t in linaje.escritos_por(SQL_DIR)}
    destinos = {d for d, _ in linaje.linaje(SQL_DIR)}
    assert creadas and creadas == destinos
    en_wh = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    assert creadas <= en_wh


def test_lineage_ends_at_raw_datasets_and_covers_the_staging():
    pares = set(linaje.linaje(SQL_DIR))
    assert ("stg_produccion", "raw:produccion_no_convencional") in pares
    assert ("stg_fractura", "raw:fractura_adjunto_iv") in pares
    assert ("fct_produccion", "stg_produccion") in pares
    assert ("dim_fractura_pozo", "stg_fractura") in pares
    assert ("mart_pozo_12m", "dim_fractura_pozo") in pares


def test_module_marts_are_derived_from_the_module_source():
    ternas = linaje.linaje_modulos()
    costo = {d for d, _, m in ternas if m == "pipeline.costo"}
    robustez = {d for d, _, m in ternas if m == "pipeline.robustez"}
    assert {"mart_anisotropia_area", "mart_costo_coef", "mart_perdida_permanente"} <= costo
    assert {"mart_robustez_eje", "mart_robustez_costo"} <= robustez
    assert ("mart_costo_coef", "int_interferencia_evento", "pipeline.costo") in ternas
    assert ("mart_robustez_eje", "mart_anisotropia_area", "pipeline.robustez") in ternas
    assert not any(d == o for d, o, _ in ternas)


def _marts_literales() -> dict[str, str]:
    """mart -> módulo, por cada `_escribir(con, "mart_...")` de pipeline/*.py salvo los EXCLUIDOS."""
    salida: dict[str, str] = {}
    for p in sorted(linaje.PIPELINE_DIR.glob("*.py")):
        if p.stem in linaje.EXCLUIDOS:
            continue
        for d in linaje._ESCRIBIR.findall(p.read_text(encoding="utf-8")):
            salida[d] = p.stem
    return salida


def test_every_mart_a_python_module_writes_has_a_lineage_origin():
    marts = _marts_literales()
    assert len(marts) > 50
    con_origen = {d for d, _, _ in linaje.linaje_modulos()}
    assert not set(marts) - con_origen, f"marts sin origen en la página de linaje: {sorted(set(marts) - con_origen)}"
    en_disco = {p.stem for p in linaje.PIPELINE_DIR.glob("*.py")
                if p.stem not in linaje.EXCLUIDOS and '_escribir(con, "mart_' in p.read_text(encoding="utf-8")}
    assert set(linaje.descubrir_modulos()) == en_disco == set(marts.values())


def test_modules_that_read_no_table_in_their_own_text_get_origins_from_the_functions_they_call():
    ternas = linaje.linaje_modulos()
    for mod in ("anillo", "hijo_celdas"):
        texto = (linaje.PIPELINE_DIR / f"{mod}.py").read_text(encoding="utf-8")
        propios = set(linaje._ESCRIBIR.findall(texto))
        assert not set(linaje._LEE.findall(texto)) - propios  # fuera de sus marts, no lee ninguna tabla
        assert any(m == f"pipeline.{mod}" for _, _, m in ternas)
    assert ("mart_hijo_celdas_coef", "mart_pozo_12m", "pipeline.hijo_celdas") in ternas


def test_the_lineage_covers_every_table_of_the_warehouse():
    wh = ROOT / "data" / "warehouse.duckdb"
    if not wh.exists():
        pytest.skip("sin data/warehouse.duckdb")
    con = duckdb.connect(str(wh), read_only=True)
    try:
        tablas = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    finally:
        con.close()
    destinos = {d for d, _, _, _ in linaje.filas_linaje()}
    solo_con_colorado = {d for d in destinos if d.startswith(("mart_dias_perdidos_colorado", "mart_golpes_mismo_mes_colorado", "mart_golpes_mismo_padre_colorado",
                                                                    "mart_causal_profundo_d7", "mart_causal_profundo_d9", "mart_dia_inicio_colorado"))}  # run_all --with-colorado o causal_profundo --cuenca colorado|wyoming
    # el paso 2 de dosis_geometria solo escribe sus tablas si la puerta de potencia pasa
    solo_si_pasa_la_puerta = {d for d in destinos if d.startswith("mart_dosis_geometria_") and not d.endswith(("_muestra", "_potencia", "_sim", "_puerta"))}
    assert not tablas - destinos and not destinos - tablas - solo_con_colorado - solo_si_pasa_la_puerta, (sorted(tablas - destinos), sorted(destinos - tablas))


def test_following_imports_takes_the_used_functions_and_sql_constants_and_not_the_whole_module(tmp_path):
    (tmp_path / "base.py").write_text(
        'def _escribir(con, nombre, cols, filas):\n    pass\n\n'
        'SQL_K = "select * from int_k"\n\n'
        'def cargar(con):\n    con.execute(SQL_K)\n    return con.execute("select * from fct_a join dim_b using (k)")\n\n'
        'def via(con):\n    return cargar(con)\n\n'
        'REGISTRO = [("a", "select * from stg_registro")]\n\n'
        'def ajena(con):\n    return con.execute("select * from stg_ajena")\n', encoding="utf-8")
    (tmp_path / "uno.py").write_text(
        'from pipeline.base import _escribir, via\n\n'
        'def correr(con):\n    via(con)\n    _escribir(con, "mart_uno", [], [])\n', encoding="utf-8")
    (tmp_path / "dos.py").write_text(
        'from pipeline import base\n\n'
        'def correr(con):\n    n = len(base.REGISTRO)\n    base.cargar(con)\n    con.execute("select * from mart_uno")\n'
        '    base._escribir(con, "mart_dos", [], [])\n', encoding="utf-8")
    assert linaje.descubrir_modulos(tmp_path) == ("dos", "uno")  # base define _escribir pero no escribe marts
    assert linaje.linaje_modulos(tmp_path) == [
        ("mart_dos", "dim_b", "pipeline.dos"), ("mart_dos", "fct_a", "pipeline.dos"),
        ("mart_dos", "int_k", "pipeline.dos"), ("mart_dos", "mart_uno", "pipeline.dos"),
        ("mart_uno", "dim_b", "pipeline.uno"), ("mart_uno", "fct_a", "pipeline.uno"),
        ("mart_uno", "int_k", "pipeline.uno")]


def test_lineage_page_is_deterministic_and_has_no_long_dashes():
    pagina = linaje.pagina_linaje()
    assert pagina == linaje.pagina_linaje()
    assert "\u2014" not in pagina and "\u2013" not in pagina
    assert "| stg_produccion | staging | raw:produccion_no_convencional | pipeline/sql/01_staging.sql |" in pagina
    assert "| mart_costo_coef | mart | int_interferencia_evento | pipeline.costo |" in pagina
    assert "| mart_hijo_celdas_coef | mart | mart_pozo_12m | pipeline.hijo_celdas |" in pagina
    assert "El grano es el módulo" in pagina and "pipeline.replicacion" in pagina
    arbol = pagina.split("```")[1].splitlines()
    assert "raw:produccion_no_convencional" in arbol and "seed:operadores" in arbol
    assert any(l.startswith("  ") and "stg_produccion" in l for l in arbol)


def test_checked_in_lineage_page_is_current():
    pagina = Path(__file__).resolve().parent.parent / "wiki" / "hallazgos" / "linaje.md"
    if pagina.exists():
        assert pagina.read_text(encoding="utf-8") == linaje.pagina_linaje()
