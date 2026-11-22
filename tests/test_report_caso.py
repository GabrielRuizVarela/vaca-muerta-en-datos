"""Página de entrada: abre con la historia en seis preguntas y sigue el tablero del caso de interferencia (hallazgo, límites, glosario, números en es-AR)."""
import re

import duckdb

from pipeline import report
from tests.test_pipeline import prod_row, warehouse  # noqa: F401  (fixture)
from tests.test_report import copia, needs_wh, pagina, texto_visible  # noqa: F401  (fixture copia)


def primer_h2(html: str) -> str:
    return re.search(r"<h2>(.*?)</h2>", texto_visible(html), flags=re.S).group(1)


def test_pagina_abre_con_la_historia_y_sigue_el_caso(warehouse, tmp_path):  # noqa: F811  (runs in CI: no real warehouse needed)
    con = warehouse([prod_row(i, y, 9, 100 + i) for i in range(1, 4) for y in (2023, 2024)], [])
    con.execute("create table mart_anisotropia_area as select * from (values "
                "('Cuenca', 92.9, 69.9, 122.5, 52.6, 0.022, 1734)) t(area, eje_grados, ic_bajo, ic_alto, ancho_ic, p_perm, n)")
    _, html = pagina(con, tmp_path)
    visible = texto_visible(html)
    assert primer_h2(html) == "¿Le pega al vecino?"
    assert visible.index("¿Le pega al vecino?") < visible.index("<h2>El caso: interferencia entre pozos</h2>")
    assert visible.index("Qué no se mide") < visible.index("<h2>Contexto de la cuenca</h2>") < visible.index("Producción de petróleo de Vaca Muerta por operador")
    assert re.search(r"<details class=\"glosario\"[^>]*><summary>Glosario</summary>", visible)
    assert "año en curso" in html and "67,5" in html
    # números en es-AR: formateador explícito, sin separador de miles en inglés
    plantilla = report.TEMPLATE.read_text()
    assert 'Intl.NumberFormat("es-AR"' in plantilla and 'Chart.defaults.locale = "es-AR"' in plantilla
    assert not re.search(r"en-US|en-GB|toLocaleString\(\)", plantilla)
    assert not re.search("[–—]", visible)


@needs_wh
def test_la_historia_va_primero_y_el_caso_con_las_cifras_del_warehouse(copia, tmp_path):  # noqa: F811
    con = duckdb.connect(str(copia))
    try:
        datos, html = pagina(con, tmp_path)
    finally:
        con.close()
    r = datos["interferencia"]["resumen"]
    visible = texto_visible(html)
    assert primer_h2(html) == "¿Le pega al vecino?"
    assert visible.index("¿Le pega al vecino?") < visible.index("<h2>El caso: interferencia entre pozos</h2>")
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


def test_la_frase_del_perfil_por_anio_sigue_el_veredicto_de_la_prueba():
    datos = {"interferencia": {}}
    sin = report.lectura_anual(datos)
    assert "no se lee como tendencia" in sin and "IC" not in sin
    datos["interferencia"]["prueba_anual"] = {"d": -0.1469, "ic_bajo": -0.4618, "ic_alto": 0.1272, "veredicto": "no firme"}
    no_firme = report.lectura_anual(datos)
    assert "no se lee como tendencia" in no_firme and no_firme.endswith("-14,7 puntos (IC 95% por bloques de 5 km: -46,2 a 12,7): no firme.")
    assert "mayor que" not in no_firme and "creció" not in no_firme
    datos["interferencia"]["prueba_anual"] = {"d": -0.20, "ic_bajo": -0.31, "ic_alto": -0.08, "veredicto": "sostiene"}
    sostiene = report.lectura_anual(datos)
    assert "es mayor que la de 2021 a 2024" in sostiene and "-20,0 puntos" in sostiene and "tendencia" not in sostiene


def test_prueba_anual_lee_el_mart_y_falta_sin_cifra():
    con = duckdb.connect()
    assert report.prueba_anual(con) is None                                       # sin mart
    con.execute("create table mart_carga_anual_prueba(estadistico varchar, d double, ic_bajo double, ic_alto double, "
                "veredicto varchar)")
    con.execute("insert into mart_carga_anual_prueba values ('2026', 'nan', 'nan', 'nan', 'sin muestra'), "
                "('2025_2026', -0.2, -0.4, -0.1, null)")
    assert report.prueba_anual(con) is None                                       # sin muestra: no hay cifra que mostrar
    con.execute("update mart_carga_anual_prueba set d = -0.15, ic_bajo = -0.46, ic_alto = 0.13, veredicto = 'no firme' "
                "where estadistico = '2026'")
    assert report.prueba_anual(con) == {"d": -0.15, "ic_bajo": -0.46, "ic_alto": 0.13, "veredicto": "no firme"}
