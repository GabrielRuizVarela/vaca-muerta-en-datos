"""Tablero estático: cifras de cabecera, resultado del eje, bloque de reproducción y texto sin rayas largas."""
import re
import shutil

import duckdb
import pytest

from pipeline import report
from pipeline.ingest import DATA
from tests.test_pipeline import prod_row, warehouse  # noqa: F401  (fixture)

WAREHOUSE = DATA / "warehouse.duckdb"
needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")


def pagina(con, tmp_path, nombre="p.html"):
    datos = report.collect(con)
    destino = tmp_path / nombre
    report.render(datos, destino)
    return datos, destino.read_text()


def texto_visible(html: str) -> str:
    """El HTML sin el código de Chart.js y sin el JSON de datos, que no son texto de la página."""
    sin_scripts = re.sub(r"<script>.*?</script>", "", html, flags=re.S)
    return sin_scripts


@pytest.fixture(scope="module")
def copia(tmp_path_factory):
    destino = tmp_path_factory.mktemp("wh") / "warehouse.duckdb"
    shutil.copy(WAREHOUSE, destino)
    return destino


@needs_wh
def test_titulares_eje_y_reproduccion(copia, tmp_path):
    con = duckdb.connect(str(copia))
    try:
        datos, html = pagina(con, tmp_path)
    finally:
        con.close()
    k, r, dq = datos["kpi"], datos["interferencia"]["resumen"], datos["dq"]
    cab = re.search(r'<ul class="titulares".*?</ul>', html, flags=re.S).group(0)
    assert report.fmt(k["pet"]) in cab
    assert report.fmt(k["ypf"] / k["pet"] * 100, 1) + "%" in cab
    assert report.fmt(r["eventos"]) in cab
    assert report.fmt(r["diferido_bbl"] / 1e6, 1) + " M" in cab
    assert f"{len(dq['checks'])}</span>" in cab and f"{dq['bloqueantes_fallidos']} bloqueantes fallidos" in cab
    # el eje sale de mart_anisotropia_area, fila Cuenca
    e = datos["eje"]
    assert e is not None
    assert f"{report.fmt(e['eje_grados'])} grados" in html
    assert f"IC 95% de {report.fmt(e['ic_bajo'])} a {report.fmt(e['ic_alto'])}" in html
    assert f"p de permutación {report.fmt(e['p_perm'], 3)}" in html
    # reproducir
    assert 'id="reproducir"' in html and "Cómo reproducir" in html
    assert "uv sync" in html and "pipeline.run_all" in html and "uv run pytest" in html
    assert 'href="replay.html"' in html and 'href="../wiki/index.md"' in html
    # sin rayas largas en el texto de la página ni en el código propio
    visible = texto_visible(html)
    assert not re.search("[–—]", visible)
    assert not re.search("[–—]", (report.TEMPLATE).read_text())
    assert not re.search("[–—]", open(report.__file__).read())
    # sin red: Chart.js va dentro del archivo
    assert "cdnjs" not in html and "<script src=" not in html


@needs_wh
def test_modelo_de_costo_frente_a_la_media_solo_si_existe_el_mart(copia, tmp_path):
    con = duckdb.connect(str(copia))
    try:
        con.execute("drop table if exists mart_costo_cv")
        _, sin = pagina(con, tmp_path, "sin.html")
        con.execute("create or replace table mart_costo_cv as select * from (values "
                    "('modelo', -0.03), ('media_entrenamiento', 0.0), ('sin_angulo', -0.04)) t(modelo, r2)")
        _, peor = pagina(con, tmp_path, "peor.html")
        con.execute("create or replace table mart_costo_cv as select * from (values "
                    "('modelo', 0.12), ('media_entrenamiento', 0.0), ('sin_angulo', 0.1)) t(modelo, r2)")
        _, mejor = pagina(con, tmp_path, "mejor.html")
        con.execute("drop table mart_costo_cv")
    finally:
        con.close()
    assert "modelo de costo" not in texto_visible(sin).split('id="eje"')[1].split("</div>")[0]
    assert "El modelo de costo no supera a la media fuera de muestra (R² -0,03 contra 0,00)" in peor
    assert "El modelo de costo supera a la media fuera de muestra (R² 0,12 contra 0,00)" in mejor


@needs_wh
def test_la_pagina_se_arma_sin_mart_anisotropia_area(copia, tmp_path):
    con = duckdb.connect(str(copia))
    try:
        con.execute("begin")
        con.execute("drop table mart_anisotropia_area")
        datos, html = pagina(con, tmp_path)
        con.execute("rollback")
    finally:
        con.close()
    assert datos["eje"] is None
    assert 'id="eje"' not in html and "Eje de mayor merma" not in html
    assert '<ul class="titulares"' in html and 'id="reproducir"' in html


def test_pagina_con_marts_a_mano_sobre_warehouse_chico(warehouse, tmp_path):  # noqa: F811  (runs in CI: no real warehouse needed)
    con = warehouse([prod_row(i, y, 9, 100 + i) for i in range(1, 4) for y in (2023, 2024)], [])
    con.execute("create table mart_anisotropia_area as select * from (values "
                "('Cuenca', 92.9, 69.9, 122.5, 52.6, 0.022, 1734)) t(area, eje_grados, ic_bajo, ic_alto, ancho_ic, p_perm, n)")
    con.execute("create table mart_costo_cv as select * from (values ('modelo', -0.15), ('media_entrenamiento', 0.0), "
                "('sin_angulo', -0.16)) t(modelo, r2)")
    datos, html = pagina(con, tmp_path)
    visible = texto_visible(html)
    assert "Eje de mayor merma en la cuenca" in visible and "93 grados" in visible
    assert "El modelo de costo no supera a la media fuera de muestra (R² -0,15 contra 0,00)" in visible
    assert 'id="reproducir"' in html and not re.search("[–—]", visible)


def test_barra_eje_marca_el_shmax_publicado():
    eje = {"eje_grados": 93.0, "ic_bajo": 70.0, "ic_alto": 122.0, "shmax": 67.5}
    svg = report.barra_eje(eje)
    assert 'class="shmax"' in svg and "SHmax 67,5" in svg
    assert 'class="shmax"' not in report.barra_eje(dict(eje, shmax=None))


def test_kpis_interferencia_diferido_por_evento_y_rango_del_mes_1():
    datos = {"interferencia": {"resumen": {
        "eventos": 10, "diferido_bbl": 1000.0, "diferido_ypf_bbl": 800.0, "eventos_ypf": 6,
        "brecha_mes_1": -0.229, "brecha_mes_1_neta": -0.192, "brecha_mes_6": -0.02}}}
    html = report.kpis_interferencia(datos)
    assert "-19 a -23" in html
    assert "133" in html and "50 por evento (4 eventos)" in html   # 800/6 y 200/4, no la parte del total
