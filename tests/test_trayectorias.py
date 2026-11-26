"""Trayectorias de pozo con geometría sintética: la rama, las distancias, la regla de versiones y de unión, y la página."""
import csv
import json
import math
from datetime import date

import duckdb
import numpy as np
import pytest

from pipeline import trayectorias as tr
from pipeline.costo import _escribir

LON0, LAT0 = -69.0, -38.5


def _lonlat(xy):
    """Metros (este, norte) desde (LON0, LAT0) a pares [lon, lat], con la escala del módulo."""
    c = math.cos(math.radians(LAT0))
    return [[LON0 + x / (tr.M_POR_GRADO * c), LAT0 + y / tr.M_POR_GRADO] for x, y in xy]


def test_tramo_final_corta_dentro_de_un_tramo():
    xy = np.array([[0.0, 0.0], [0.0, 1000.0], [2000.0, 1000.0]])
    t = tr.tramo_final(xy, 2500)
    assert np.allclose(t, [[0, 500], [0, 1000], [2000, 1000]])
    assert tr.largo(t) == pytest.approx(2500)
    assert np.allclose(tr.tramo_final(xy, 1500), [[500, 1000], [2000, 1000]])
    assert np.allclose(tr.tramo_final(xy, 9999), xy)


def test_simplificar_quita_el_ruido_y_deja_el_quiebre():
    x = np.linspace(0, 1000, 101)
    ruido = np.column_stack([x, np.sin(x) * 1.5])          # a menos de 2 m de la recta que une los extremos
    ruido[[0, -1], 1] = 0.0
    assert len(tr.simplificar(ruido)) == 2
    quiebre = np.array([[0.0, 0.0], [500.0, 0.0], [500.0, 300.0], [1000.0, 300.0]])
    assert np.allclose(tr.simplificar(quiebre), quiebre)


def test_distancia_minima_paralelas_cruzadas_y_contra_fuerza_bruta():
    a = np.array([[0.0, 0.0], [2000.0, 0.0]])
    assert tr.distancia_minima(a, a + [0, 300]) == pytest.approx(300)
    assert tr.distancia_minima(a, np.array([[1000.0, -500.0], [1000.0, 500.0]])) == 0.0
    assert tr.distancia_minima(a, np.array([[2100.0, 0.0], [3000.0, 0.0]])) == pytest.approx(100)
    rng = np.random.default_rng(3)
    for _ in range(20):
        p = np.cumsum(rng.normal(0, 200, (6, 2)), axis=0)
        q = np.cumsum(rng.normal(0, 200, (6, 2)), axis=0) + rng.normal(0, 300, 2)
        exacta = tr.distancia_minima(p, q)
        bruta = tr.dist_puntos_tramos(tr.remuestrear(p, 0.5), q[:-1], q[1:]).min()
        assert exacta <= bruta + 1e-9
        assert bruta - exacta < 0.5 or exacta == 0.0


def test_separacion_mediana_de_ramas_paralelas_es_el_espaciamiento():
    hijo = np.array([[0.0, 250.0], [2000.0, 250.0]])
    padre = np.array([[-100.0, 0.0], [2100.0, 0.0]])
    assert tr.separacion_mediana(hijo, padre) == pytest.approx(250)
    # ramas hacia lados opuestos desde el mismo pad: la menor distancia es corta y la separación, larga
    opuesta = np.array([[-200.0, 30.0], [-2200.0, 30.0]])
    rama = np.array([[200.0, 0.0], [2200.0, 0.0]])
    assert tr.distancia_minima(opuesta, rama) == pytest.approx(math.hypot(400, 30))
    assert tr.separacion_mediana(opuesta, rama) == pytest.approx(math.hypot(1400, 30), abs=1)


def _v(md, pnl_md, pnl_tvd, huella="b", hz=None, fila="x"):
    return {"md": md, "pnl_md": pnl_md, "pnl_tvd": pnl_tvd, "huella": huella, "hz": hz, "huella_fila": fila}


def _rama(*puntos):
    """Lateral sintética en planta: (n, 2) en metros, remuestreada cada 25 m como en el módulo."""
    return tr.remuestrear(np.array(puntos, float))


def _geo(hijo, padre):
    """La geometría del par con las dos laterales ya remuestreadas."""
    return tr.geometria_par(hijo, padre)


def test_geometria_par_paralelas_a_300_m_mismo_tramo():
    g = _geo(_rama((0, 0), (1000, 0)), _rama((0, 300), (1000, 300)))
    assert g["solape_frac"] == pytest.approx(1.0)
    assert g["desfase_perp_m"] == pytest.approx(300, abs=0.5)
    assert g["desfase_axial_m"] == pytest.approx(0, abs=0.5)
    assert g["posicion"] == "costado"
    assert g["dif_azimut"] == pytest.approx(0, abs=0.5)
    assert g["paralelas"] is True


def test_geometria_par_colineales_con_hueco_de_200_m():
    g = _geo(_rama((0, 0), (1000, 0)), _rama((1200, 0), (2200, 0)))
    assert g["solape_frac"] == pytest.approx(0.0)
    assert g["desfase_perp_m"] is None
    assert g["desfase_axial_m"] == pytest.approx(200, abs=0.5)
    assert g["posicion"] == "punta"


def test_geometria_par_solape_a_medio_y_solape_chico():
    medio = _geo(_rama((0, 0), (1000, 0)), _rama((500, 300), (1500, 300)))
    assert medio["solape_frac"] == pytest.approx(0.5)
    assert medio["posicion"] == "costado"
    assert medio["desfase_perp_m"] == pytest.approx(300, abs=0.5)
    chico = _geo(_rama((0, 0), (1000, 0)), _rama((900, 300), (1900, 300)))
    assert chico["solape_frac"] == pytest.approx(0.1)
    assert chico["posicion"] == "mixto"


def test_geometria_par_perpendiculares():
    g = _geo(_rama((0, 0), (1000, 0)), _rama((500, -500), (500, 500)))
    assert g["dif_azimut"] == pytest.approx(90, abs=0.5)
    assert g["paralelas"] is False


def test_azimut_eje_por_la_orientacion_de_la_lateral():
    assert tr.azimut_eje(_rama((0, 0), (0, 1000))) == pytest.approx(0, abs=0.01)
    assert tr.azimut_eje(_rama((0, 0), (1000, 0))) == pytest.approx(90, abs=0.01)
    a = math.radians(22.5)
    assert tr.azimut_eje(_rama((0, 0), (1000 * math.sin(a), 1000 * math.cos(a)))) == pytest.approx(22.5, abs=0.01)


def test_angulo_a_shmax():
    assert tr.angulo_a_shmax(157.5) == pytest.approx(90, abs=0.01)
    assert tr.angulo_a_shmax(67.5) == pytest.approx(0, abs=0.01)


def test_geometria_par_con_los_papeles_invertidos_no_falla():
    hijo = _rama((0, 0), (1000, 0))
    padre = _rama((500, -500), (500, 500))
    normal = _geo(hijo, padre)
    invertido = _geo(padre, hijo)
    assert normal["azimut_hijo"] == pytest.approx(90, abs=0.5)
    assert invertido["azimut_hijo"] == pytest.approx(0, abs=0.5)
    assert invertido["azimut_padre"] == pytest.approx(90, abs=0.5)
    assert invertido["dif_azimut"] == pytest.approx(90, abs=0.5)
    assert invertido["posicion"] in tr.POSICIONES


def test_elegir_version_y_largo_de_rama():
    sin_inicio = _v(6000, 0, 0)
    valida = _v(5000, 3000, 2900)
    mas_honda = _v(5500, 3000, 2900)
    assert tr.elegir_version([sin_inicio, valida]) is valida
    assert tr.elegir_version([valida, mas_honda]) is mas_honda
    a, b = _v(5000, 3000, 2900, "a"), _v(5000, 3000, 2900, "b")
    assert tr.elegir_version([b, a]) is a and tr.elegir_version([a, b]) is a
    # mismo trazado y misma profundidad, otro largo de rama: decide la huella de la fila, no el orden
    c, d = _v(5000, 3000, 2900, "a", 1800, "1"), _v(5000, 3000, 2900, "a", 1900, "2")
    assert tr.elegir_version([d, c]) is c and tr.elegir_version([c, d]) is c
    assert tr.largo_rama(_v(5000, 3000, 2900, hz=1800)) == 1800
    assert tr.largo_rama(_v(5000, 3000, 2900, hz=0)) == 2000
    assert tr.largo_rama(_v(5000, 0, 0)) is None


def test_horizontal_por_la_sigla():
    for s in ("YPF.Nq.LACh-123(h)", "CHA.Nq.ET-2023h"):
        assert tr.HORIZONTAL.search(s)
    for s in ("SHE.Nq.CdL.x-3(d)", "YPF.Nq.LLL-12", ""):
        assert not tr.HORIZONTAL.search(s)


def _pozo(sigla, idpo, cabeza, rumbo, rama=2000.0, hz=True, md_extra=3000.0, pnl_md=None):
    """Una fila de la fuente: boca en `cabeza` (m), 200 m de curva en la dirección `rumbo` (+1 este, -1 oeste) y la rama."""
    x0, y0 = cabeza
    xy = [(x0, y0), (x0 + rumbo * 200, y0), (x0 + rumbo * (200 + rama), y0)]
    md = md_extra + 200 + rama
    return {"sigla": sigla, "idpo": str(idpo), "profundidad_final_total_mt": str(md), "profundidad_vertical_mt": "2900",
            "profundidad_sidetrack_mt": "0", "largo_rama_horizontal_mt": str(rama) if hz else "0",
            "unidad_intervalo_navegacion": "2", "detalle_unidad_intervalo_navegacion": "0",
            "pnl_md": str(md - rama if pnl_md is None else pnl_md), "pnl_tvd": "2900", "termini": "2020-01-01",
            "termfin": "2020-02-01", "drilini": "2019-06-01", "drilfin": "2019-08-01", "tipopozo": "4", "geometria": "",
            "geojson": json.dumps({"type": "LineString", "coordinates": _lonlat(xy)})}


@pytest.fixture
def mundo(tmp_path):
    """Un warehouse mínimo y un CSV con un caso por regla."""
    filas = [
        _pozo("A-1(h)", 1, (0, 0), +1),                      # padre, rama hacia el este en y = 0
        _pozo("A-1(h)", 1, (0, 0), +1),                      # fila repetida idéntica
        _pozo("B-2(h)", 2, (0, 300), +1, pnl_md=0),          # versión sin inicio de navegación válido (no se elige)
        _pozo("B-2(h)", 2, (0, 300), +1, md_extra=2500),     # hijo paralelo a 300 m
        _pozo("C-3(h)", 0, (0, 30), -1),                     # hijo del mismo pad, rama hacia el oeste; se une por sigla
        _pozo("A-1(h)", 0, (5, 0), +1),                      # idpo 0 con la sigla de A: pozo repetido
        _pozo("Z-9(h)", 99, (0, 900), +1),                   # sin pozo en el warehouse
        _pozo("F-5(h)", 5, (0, 1200), +1),                   # fuera del estudio
        _pozo("G-6(h)", 6, (0, 1500), +1),                   # boca a 500 m de su ubicación
        _pozo("H-7(h)", 7, (0, 1800), +1, hz=False, pnl_md=0),  # sin largo de rama
    ]
    ruta = tmp_path / "trayectorias.csv"
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=tr.COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    con = duckdb.connect()
    ubic = {1: (0, 0), 2: (0, 300), 3: (0, 30), 6: (500, 1500), 7: (0, 1800), 8: (0, 2100)}
    dim = {**ubic, 5: (0, 1200)}
    siglas = {1: "A-1(h)", 2: "B-2(h)", 3: "C-3(h)", 5: "F-5(h)", 6: "G-6(h)", 7: "H-7(h)", 8: "K-8(h)"}
    con.execute("create table dim_pozo (pozo_id integer, sigla varchar, lon double, lat double)")
    con.execute("create table int_pozo_ubicacion (pozo_id integer, lon double, lat double)")
    for pid, xy in dim.items():
        lon, lat = _lonlat([xy])[0]
        con.execute("insert into dim_pozo values (?, ?, ?, ?)", [pid, siglas[pid], lon, lat])
        if pid in ubic:
            con.execute("insert into int_pozo_ubicacion values (?, ?, ?)", [pid, lon, lat])
    con.execute("create table int_frac_hijo (hijo integer, mes_frac date)")
    con.execute("insert into int_frac_hijo values (2, '2021-05-01'), (3, '2021-07-01'), (8, '2025-03-01')")
    con.execute("create table int_par_padre_hijo (hijo integer, padre integer, mes_frac date, km double)")
    con.execute("insert into int_par_padre_hijo values (2, 1, '2021-05-01', 0.3), (3, 1, '2021-07-01', 0.03), "
                "(8, 1, '2025-03-01', 2.1)")
    return con, ruta, len(filas)


def test_calcular_reglas_y_distancias(mundo):
    con, ruta, n = mundo
    t = tr.calcular(con, ruta)
    pozos = {r[0]: r for r in t["mart_trayectoria_pozo"]}          # clave -> fila
    motivo = {k: r[-1] for k, r in pozos.items()}
    assert motivo == {"1": None, "2": None, "s:C-3(h)": None, "s:A-1(h)": "pozo repetido", "99": "sin pozo en el warehouse",
                      "5": "fuera del estudio", "6": "boca lejos de la ubicación", "7": "sin largo de rama"}
    assert pozos["s:C-3(h)"][3] == 3 and pozos["s:C-3(h)"][4] == "sigla"
    assert pozos["s:A-1(h)"][3] is None and pozos["s:A-1(h)"][4] is None   # el repetido no repite pozo_id ni unión
    assert pozos["2"][6] == 2 and pozos["2"][10] > 0                 # dos versiones; vale la de inicio válido
    assert pozos["1"][5] == 2                                        # dos filas publicadas (una repetida)
    par = {(r[0], r[1]): r for r in t["mart_trayectoria_par"]}
    assert set(par) == {(2, 1), (3, 1)}                              # el hijo 8 no está en la fuente
    assert par[(2, 1)][4] == pytest.approx(300, abs=0.5) and par[(2, 1)][5] == pytest.approx(300, abs=0.5)
    assert par[(3, 1)][4] == pytest.approx(math.hypot(400, 30), abs=0.5)
    assert par[(3, 1)][5] == pytest.approx(math.hypot(1400, 30), abs=2)
    assert par[(2, 1)][7] is True and par[(2, 1)][6] == 0
    cob = {(r[0], r[1]): r[2:] for r in t["mart_trayectoria_cobertura"]}
    assert cob[("hijo", 2021)] == (2, 2, 2, 2, 2)
    assert cob[("hijo", 2025)] == (1, 0, 1, 0, 0)
    assert cob[("par_1km", 2021)] == (2, 2, None, None, None)
    assert ("par_1km", 2025) not in cob and cob[("par_2km", 2021)][:2] == (2, 2)
    R = dict(t["mart_trayectoria_resumen"])
    assert R["filas"] == n and R["filas_repetidas"] == 1 and R["pozos_fuente"] == 8
    assert R["unidos_idpo"] == 5 and R["unidos_sigla"] == 1 and R["con_rama"] == 3 and R["pares_medidos"] == 2
    assert R["motivo_1"] == 1 and R["rama_p50"] == pytest.approx(2000)
    cruce = {(s, r): k for s, r, k in t["mart_trayectoria_cruce"]}
    assert cruce[("cercano", "250_1000")] == 2 and sum(cruce.values()) == 2      # 300 m y 401 m


def test_mart_par_rama_con_las_laterales_del_fixture(mundo):
    con, ruta, _ = mundo
    t = tr.calcular(con, ruta)
    par = {(r[0], r[1]): r for r in t["mart_par_rama"]}
    assert set(par) == {(r[0], r[1]) for r in t["mart_trayectoria_par"]}
    assert set(par) == {(2, 1), (3, 1)}
    # el hijo 2 va al este a 300 m del padre, con el mismo tramo: de costado
    r = par[(2, 1)]
    assert r[9] == "costado" and r[6] == pytest.approx(1.0)
    assert r[7] == pytest.approx(300, abs=1) and r[8] == pytest.approx(0, abs=1)
    assert r[4] == pytest.approx(0, abs=1) and r[5] is True
    assert r[2] == pytest.approx(90, abs=1) and r[10] == pytest.approx(22.5, abs=1)
    # el hijo 3 va al oeste desde el mismo pad y el padre al este: sin solape y con 400 m de hueco
    r = par[(3, 1)]
    assert r[9] == "punta" and r[6] == pytest.approx(0.0)
    assert r[7] is None and r[8] == pytest.approx(400, abs=1)
    assert r[4] == pytest.approx(0, abs=1) and r[5] is True


def test_insertar_y_pagina(mundo):
    con, ruta, _ = mundo
    t = tr.calcular(con, ruta)
    for tabla, cols in (("mart_trayectoria_pozo", tr.COLS_POZO), ("mart_trayectoria_cobertura", tr.COLS_COBERTURA),
                        ("mart_trayectoria_banda", tr.COLS_BANDA), ("mart_trayectoria_cruce", tr.COLS_CRUCE),
                        ("mart_trayectoria_resumen", tr.COLS_RESUMEN)):
        _escribir(con, tabla, cols, t[tabla])
    _escribir(con, "mart_trayectoria_par", tr.COLS_PAR, [])
    tr._insertar(con, "mart_trayectoria_par", tr.COLS_PAR, t["mart_trayectoria_par"])
    _escribir(con, "mart_par_rama", tr.COLS_PAR_RAMA, [])
    tr._insertar(con, "mart_par_rama", tr.COLS_PAR_RAMA, t["mart_par_rama"])
    filas = con.execute("select * from mart_trayectoria_par order by hijo").fetchall()
    assert [f[:3] for f in filas] == [(2, 1, date(2021, 5, 1)), (3, 1, date(2021, 7, 1))]
    assert filas[0][4] == pytest.approx(t["mart_trayectoria_par"][0][4])
    manifest = {tr.CLAVE: {"sha256": "abc123", "loaded_at": "2026-11-20T07:03:05+00:00", "last_modified": "x"}}
    pagina = tr.pagina_trayectorias(con, manifest)
    for texto in ("CC-BY-4.0", tr.TITULO, "`abc123`", "No mide interferencia", "todavía no publica",
                  "| 2025 | 1 | 1 | 0 | 0 | 0% |", "| pozo repetido | 1 |",
                  "## Dónde queda el padre respecto de la rama del hijo", "mart_par_rama",
                  "| cercano (menos de 1 km) | 1 (50%) | 1 (50%) | 0 (0%) | 2 |"):
        assert texto in pagina, texto


def test_ruta_fuente_sin_copia_pide_la_ingesta(tmp_path):
    with pytest.raises(SystemExit, match="pipeline.ingest"):
        tr.ruta_fuente({}, tmp_path)
    with pytest.raises(SystemExit, match="pipeline.ingest"):
        tr.ruta_fuente({tr.CLAVE: {"path": "trayectorias_pozo/no.csv"}}, tmp_path)


def test_main_sin_copia_avisa_y_no_corta_la_cadena(tmp_path, monkeypatch, capsys):
    def falta():
        raise SystemExit("falta la copia de trayectorias_pozo en data/raw")
    monkeypatch.setattr(tr, "ruta_fuente", falta)
    db = tmp_path / "w.duckdb"
    assert tr.main(db) == 0
    assert "AVISO" in capsys.readouterr().err and not db.exists()
