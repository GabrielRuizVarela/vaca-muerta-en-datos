"""Tablero: la primera pantalla es el caso de interferencia (hallazgo, límites, glosario, números en es-AR)."""
import re

import duckdb

from pipeline import report
from tests.test_pipeline import prod_row, warehouse  # noqa: F401  (fixture)
from tests.test_report import copia, needs_wh, pagina, texto_visible  # noqa: F401  (fixture copia)


def primer_h2(html: str) -> str:
    return re.search(r"<h2>(.*?)</h2>", texto_visible(html), flags=re.S).group(1)


def test_pagina_abre_con_el_caso_de_interferencia(warehouse, tmp_path):  # noqa: F811  (runs in CI: no real warehouse needed)
    con = warehouse([prod_row(i, y, 9, 100 + i) for i in range(1, 4) for y in (2023, 2024)], [])
    con.execute("create table mart_anisotropia_area as select * from (values "
                "('Cuenca', 92.9, 69.9, 122.5, 52.6, 0.022, 1734)) t(area, eje_grados, ic_bajo, ic_alto, ancho_ic, p_perm, n)")
    _, html = pagina(con, tmp_path)
    visible = texto_visible(html)
    assert primer_h2(html) == "El caso: interferencia entre pozos"
    assert visible.index("Qué no se mide") < visible.index("<h2>Contexto de la cuenca</h2>") < visible.index("Producción de petróleo de Vaca Muerta por operador")
    assert re.search(r"<details class=\"glosario\"[^>]*><summary>Glosario</summary>", visible)
    assert "año en curso" in html and "67,5" in html
    # números en es-AR: formateador explícito, sin separador de miles en inglés
    plantilla = report.TEMPLATE.read_text()
    assert 'Intl.NumberFormat("es-AR"' in plantilla and 'Chart.defaults.locale = "es-AR"' in plantilla
    assert not re.search(r"en-US|en-GB|toLocaleString\(\)", plantilla)
    assert not re.search("[–—]", visible)


@needs_wh
def test_el_caso_va_primero_con_las_cifras_del_warehouse(copia, tmp_path):  # noqa: F811
    con = duckdb.connect(str(copia))
    try:
        datos, html = pagina(con, tmp_path)
    finally:
        con.close()
    r = datos["interferencia"]["resumen"]
    visible = texto_visible(html)
    assert primer_h2(html) == "El caso: interferencia entre pozos"
    assert f"entre {report.pts(r['brecha_mes_1_neta'], -1)} y {report.pts(r['brecha_mes_1'], -1)} puntos menos" in visible
    assert f"({report.fmt(r['eventos'])} eventos)" in visible
    assert "Qué no se mide" in visible and "año en curso" in visible and "Glosario" in visible and "67,5" in visible
    assert html.index("Qué no se mide") < 0.15 * len(html)
    assert len(datos["interferencia"]["pretrend"]) == 7


def test_hallazgo_y_leyenda_anual_salen_de_los_datos():
    datos = {"ultimo_mes": "2026-09", "interferencia": {
        "resumen": {"eventos": 2077, "brecha_mes_1": -0.229, "brecha_mes_1_neta": -0.192},
        "anual": [{"anio": 2025, "eventos_cercanos": 372, "brecha": -0.32},
                  {"anio": 2026, "eventos_cercanos": 243, "brecha": -0.44}]}}
    h = report.hallazgo(datos)
    assert "entre 19 y 23 puntos menos" in h and "(2.077 eventos)" in h
    assert "2026: año en curso" in report.leyenda_anual(datos)
    datos["ultimo_mes"] = "2027-01"
    assert "año en curso" not in report.leyenda_anual(datos)
    datos["interferencia"]["resumen"]["brecha_mes_1_neta"] = None
    sin_neta = report.hallazgo(datos)
    assert "23 puntos menos" in sin_neta and "entre" not in sin_neta
