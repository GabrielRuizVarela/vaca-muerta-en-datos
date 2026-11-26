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
    # el eje retirado ya no tiene tarjeta propia: sus cifras viven en "Ver los números" de la historia (texto de la plantilla)
    assert datos["eje"] is not None
    assert 'id="eje"' not in html and 'class="eje-barra"' not in html and "p de permutación" not in html
    # reproducir
    assert 'id="reproducir"' in html and "Cómo lo medimos y cómo repetirlo" in html and "Código y reglas fijadas" in html
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
    # sin tarjeta propia del eje; la frase de "Ver los números" es texto fijo de la plantilla (8a38c29), con su claim
    assert 'id="eje"' not in html and 'class="eje-barra"' not in html
    assert '<ul class="titulares"' in html and 'id="reproducir"' in html


def test_pagina_con_marts_a_mano_sobre_warehouse_chico(warehouse, tmp_path):  # noqa: F811  (runs in CI: no real warehouse needed)
    con = warehouse([prod_row(i, y, 9, 100 + i) for i in range(1, 4) for y in (2023, 2024)], [])
    con.execute("create table mart_anisotropia_area as select * from (values "
                "('Cuenca', 92.9, 69.9, 122.5, 52.6, 0.022, 1734)) t(area, eje_grados, ic_bajo, ic_alto, ancho_ic, p_perm, n)")
    con.execute("create table mart_costo_cv as select * from (values ('modelo', -0.15), ('media_entrenamiento', 0.0), "
                "('media_area', -0.03), ('sin_angulo', -0.16)) t(modelo, r2)")
    datos, html = pagina(con, tmp_path)
    visible = texto_visible(html)
    assert 'id="eje"' not in html and "p de permutación" not in visible   # sin tarjeta propia del eje
    assert 'id="reproducir"' in html and not re.search("[–—]", visible)


def test_kpis_interferencia_diferido_por_evento_y_rango_del_mes_1():
    datos = {"interferencia": {"resumen": {
        "eventos": 10, "diferido_bbl": 1000.0, "diferido_ypf_bbl": 800.0, "eventos_ypf": 6,
        "brecha_mes_1": -0.229, "brecha_mes_1_neta": -0.192, "brecha_mes_6": -0.02}}}
    html = report.kpis_interferencia(datos)
    assert "-19 a -23" in html and "bbl diferidos" not in html
    cuenta = report.diferido_cuenta(datos)
    assert "133 barriles por fractura (6 eventos)" in cuenta and "50 por fractura (4 eventos)" in cuenta   # 800/6 y 200/4, no la parte del total
    assert "Por evento" in cuenta and "Por padre" in cuenta and "Total de la cuenca" in cuenta



def test_prueba_abierta_sigue_el_estado_de_la_pagina_prospectiva(tmp_path):
    pagina_p = tmp_path / "prospectiva.md"
    pagina_p.write_text("## Estado\n\n- **Pendiente.** El warehouse llega a 2026-09.\n", encoding="utf-8")
    assert report.estado_prospectiva(pagina_p) == {"estado": "pendiente"}
    assert "Hoy falta." in report.prueba_abierta(report.estado_prospectiva(pagina_p))
    pagina_p.write_text("## Estado\n\nPuntuado con los datos hasta 2026-11.\n\n- **P1, brecha del mes 1: sostiene.** x.\n"
                        "- **P2, cierre al mes 6: no firme.** y.\n", encoding="utf-8")
    est = report.estado_prospectiva(pagina_p)
    assert est == {"estado": "puntuado", "mes": "2026-11", "p1": "sostiene", "p2": "no firme"}
    texto = report.prueba_abierta(est)
    assert "Hoy falta" not in texto and "«sostiene»" in texto and "«no firme»" in texto and "2026-11" in texto
    assert report.estado_prospectiva(tmp_path / "no-existe.md") is None
    assert "Hoy falta" not in report.prueba_abierta(None)


def test_sitio_y_readme_dicen_el_estado_de_la_prueba_prospectiva():
    """El estado de la prueba sale de su página: el índice del sitio lo repite tal cual y el README lo dice a mano,
    así que si la página cambia de estado (se puntúa con muestra, o vuelve a pendiente) estos textos tienen que cambiar."""
    est = report.estado_prospectiva()
    assert est is not None
    sitio = (report.ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert report.prueba_abierta(est) in sitio
    plantilla = report.TEMPLATE.read_text(encoding="utf-8")
    assert "Hoy falta" not in plantilla and "<!--__PRUEBA_ABIERTA__-->" in plantilla
    readme = (report.ROOT / "README.md").read_text(encoding="utf-8")
    if est["estado"] == "pendiente":
        assert "hoy está pendiente" in readme
    else:
        assert "hoy está pendiente" not in readme and f"con los datos hasta {est['mes']} ya se puntuó" in readme
        if est["p1"] == est["p2"] == "sin muestra":
            assert f"con los datos hasta {est['mes']} ya se puntuó y quedó sin muestra" in readme
        else:  # con otro veredicto el README tiene que dejar de decir 'sin muestra' a mano
            assert "ya se puntuó y quedó sin muestra" not in readme
