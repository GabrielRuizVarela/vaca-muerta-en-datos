import xml.etree.ElementTree as ET

import duckdb
import pytest

from pipeline import mapa

AREAS = [  # area, n, eje, ic_bajo, ic_alto, contraste, p_perm, usa_en_costo
    ("Cuenca", 1000, 90.0, 60.0, 120.0, 0.14, 0.02, True),
    ("ALFA", 100, 60.0, 40.0, 80.0, 0.5, 0.02, True),
    ("BETA", 90, 20.0, 150.0, 60.0, 0.9, 0.30, False),
    ("GAMMA", 80, 170.0, 150.0, 20.0, 0.3, 0.01, True),  # el IC cruza el norte
    ("SIN POZOS", 70, 45.0, 10.0, 90.0, 0.2, 0.01, True),
]
POZOS = [("ALFA ", -68.9, -38.5), ("alfa", -68.8, -38.4), ("BETA", -68.7, -38.3), ("GAMMA", -68.6, -38.2),
         ("OTRA", -68.5, -38.1)]


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute("create table mart_anisotropia_area (area varchar, n integer, eje_grados double, ic_bajo double, "
              "ic_alto double, contraste double, p_perm double, usa_en_costo boolean)")
    c.executemany("insert into mart_anisotropia_area values (?,?,?,?,?,?,?,?)", AREAS)
    c.execute("create table int_pozo_ubicacion (area varchar, lon double, lat double)")
    c.executemany("insert into int_pozo_ubicacion values (?,?,?)", POZOS)
    return c


def _raiz(svg):
    return ET.fromstring(svg)


def _marcas(root):
    return [g for g in root.iter("{http://www.w3.org/2000/svg}g") if g.get("class") == "area"]


def test_svg_is_valid_xml_with_one_group_per_area_with_wells(con):
    marcas = _marcas(_raiz(mapa.mapa_areas_svg(con)))
    assert sorted(g.get("data-area") for g in marcas) == ["ALFA", "BETA", "GAMMA"]  # Cuenca y sin pozos fuera


def test_area_without_wells_is_skipped_and_empty_map_is_valid():
    c = duckdb.connect(":memory:")
    c.execute("create table mart_anisotropia_area (area varchar, n integer, eje_grados double, ic_bajo double, "
              "ic_alto double, contraste double, p_perm double, usa_en_costo boolean)")
    c.executemany("insert into mart_anisotropia_area values (?,?,?,?,?,?,?,?)", AREAS)
    c.execute("create table int_pozo_ubicacion (area varchar, lon double, lat double)")
    assert _marcas(_raiz(mapa.mapa_areas_svg(c))) == []


def test_deterministic(con):
    assert mapa.mapa_areas_svg(con) == mapa.mapa_areas_svg(con)


def test_no_long_dashes(con):
    svg = mapa.mapa_areas_svg(con)
    assert "—" not in svg and "–" not in svg


def test_wedge_only_when_axis_defined(con):
    for g in _marcas(_raiz(mapa.mapa_areas_svg(con))):
        conos = [p for p in g.iter("{http://www.w3.org/2000/svg}path") if p.get("class") == "cono"]
        assert len(conos) == (2 if g.get("data-definido") == "si" else 0)


def test_wrap_around_ci_wedge_is_not_wider_than_180(con):
    svg = mapa.mapa_areas_svg(con)
    gamma = next(g for g in _marcas(_raiz(svg)) if g.get("data-area") == "GAMMA")
    aperturas = [float(p.get("data-apertura")) for p in gamma.iter("{http://www.w3.org/2000/svg}path") if p.get("class") == "cono"]
    assert aperturas and all(0 < a < 180 for a in aperturas)
    assert aperturas[0] == pytest.approx(50.0)  # de 150 a 20 por el norte
    assert mapa.ancho_circular(150, 20) == pytest.approx(50.0)
    assert mapa.ancho_circular(40, 80) == pytest.approx(40.0)
    assert 0 <= mapa.ancho_circular(10, 10) < 180


def test_axis_screen_direction_matches_bearing():
    # 0 grados apunta al norte (y hacia arriba), 90 al este (x a la derecha)
    assert mapa._punto(0, 0, 0, 10) == pytest.approx((0, -10))
    assert mapa._punto(0, 0, 90, 10) == pytest.approx((10, 0))


def test_reference_line_and_legend_present(con):
    svg = mapa.mapa_areas_svg(con)
    assert svg.count('class="ref"') == 3 + 1  # una por area con pozos y la de la leyenda
    assert "67,5" in svg and "20 km" in svg and "Cuenca (no se dibuja)" in svg
