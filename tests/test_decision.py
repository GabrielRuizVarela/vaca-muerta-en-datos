"""Pruebas sinteticas de pipeline.decision (sin warehouse)."""
from __future__ import annotations

import duckdb
import numpy as np
import pytest

from pipeline.costo import _escribir
from pipeline.decision import (COLS_CIERRE, COLS_DISTANCIA, COLS_EDAD, COLS_PERDIDA, SQL_EVENTOS,
                               comprobar_total, main, media_con_ic, pagina_decision, parte_recuperada,
                               valor_indicativo)
from pipeline.placebo import SEMILLA_PLACEBO


def test_valor_indicativo_formula_a_mano():
    v = valor_indicativo(100.0, 60.0, 0.10, 12)
    assert v["valor_cota_perdida"] == pytest.approx(628.98 * 60.0)
    assert v["valor_cota_perdida"] == pytest.approx(37738.8)
    assert v["costo_de_diferir"] == pytest.approx(37738.8 / 11.0)
    assert v["costo_de_diferir"] == pytest.approx(3430.8)


def test_valor_indicativo_sin_rezago_o_sin_tasa_no_cuesta():
    assert valor_indicativo(100.0, 60.0, 0.10, 0)["costo_de_diferir"] == pytest.approx(0.0)
    assert valor_indicativo(100.0, 60.0, 0.0, 12)["costo_de_diferir"] == pytest.approx(0.0)


def test_parte_recuperada():
    assert parte_recuperada(-0.2, -0.02) == pytest.approx(0.9)
    assert parte_recuperada(-0.2293, -0.0210) == pytest.approx(1.0 - 0.0210 / 0.2293)


def test_parte_recuperada_vacia_si_la_brecha_no_llega_a_menos_0_05():
    assert parte_recuperada(-0.05, -0.01) is None
    assert parte_recuperada(-0.04, -0.01) is None
    assert parte_recuperada(0.01, -0.01) is None
    assert parte_recuperada(None, -0.01) is None
    assert parte_recuperada(-0.2, None) is None


def test_eventos_agrupan_por_el_pad_del_hijo_no_por_el_del_padre():
    con = duckdb.connect(":memory:")
    con.execute("create table mart_interferencia_diferida (padre integer, hijo_cercano integer, km_min double, "
                "pad_id varchar, grupo_edad varchar, petroleo_diferido_bbl double)")
    con.execute("create table int_pozo_ubicacion (pozo_id integer, pad_id varchar)")
    con.execute("insert into mart_interferencia_diferida values (1, 101, 0.2, 'PADRE-1', '06-11', 1000.0), "
                "(2, 102, 0.4, 'PADRE-2', '06-11', 2000.0)")
    con.execute("insert into int_pozo_ubicacion values (101, 'HIJO-A'), (102, 'HIJO-B')")
    filas = con.execute(SQL_EVENTOS).fetchall()
    con.close()
    assert [f[3] for f in filas] == ["HIJO-A", "HIJO-B"]
    assert not any(f[3].startswith("PADRE") for f in filas)


def test_media_con_ic_es_determinista_y_respeta_los_minimos():
    rng = np.random.default_rng(7)
    vals = rng.normal(5000, 1000, 40)
    pads12 = np.array([f"p{i % 12}" for i in range(40)])
    a = media_con_ic(vals, pads12, SEMILLA_PLACEBO + 900)
    b = media_con_ic(vals, pads12, SEMILLA_PLACEBO + 900)
    assert a == b
    assert a[1] is not None and a[2] is not None and a[1] <= a[0] <= a[2]
    assert media_con_ic(vals[:20], pads12[:20], SEMILLA_PLACEBO + 900)[1:] == (None, None)
    pads5 = np.array([f"p{i % 5}" for i in range(40)])
    assert media_con_ic(vals, pads5, SEMILLA_PLACEBO + 900)[1:] == (None, None)


def test_media_con_ic_cambia_con_la_estructura_de_pads():
    rng = np.random.default_rng(7)
    vals = rng.normal(5000, 1000, 40)
    en_grupo = media_con_ic(vals, np.array([f"p{i % 12}" for i in range(40)]), SEMILLA_PLACEBO + 900)
    sueltos = media_con_ic(vals, np.array([f"p{i}" for i in range(40)]), SEMILLA_PLACEBO + 900)
    assert en_grupo[0] == sueltos[0]
    assert (en_grupo[1], en_grupo[2]) != (sueltos[1], sueltos[2])


def test_comprobar_total_tolera_1_barril():
    comprobar_total(100.0, 100.5)
    comprobar_total(100.0, 101.0)
    with pytest.raises(RuntimeError):
        comprobar_total(100.0, 102.0)


COLS_BRECHA = [("grupo_edad", "varchar"), ("k", "integer"), ("eventos_cercanos", "integer"),
               ("indice_cercano", "double"), ("indice_control", "double"), ("brecha", "double")]
COLS_ANILLO = [("variante", "varchar"), ("descripcion", "varchar"), ("k", "integer"), ("n_cercano", "integer"),
               ("n_control", "integer"), ("mediana_cercano", "double"), ("mediana_control", "double"),
               ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_DESCD = [("banda", "varchar"), ("km_desde", "double"), ("km_hasta", "double"), ("control", "varchar"),
              ("n_banda", "integer"), ("n_ctrl", "integer"), ("mediana_banda", "double"),
              ("mediana_control", "double"), ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
              ("base", "varchar")]
COLS_RANGO = [("variante", "varchar"), ("orden", "integer"), ("diferido_bbl", "double"), ("eventos", "integer"),
              ("meses_padre", "integer"), ("por_evento_bbl", "double"), ("brecha_previa", "double")]
COLS_OPER = [("operador", "varchar"), ("orden", "integer"), ("eventos", "integer"), ("pads_hijo", "integer"),
             ("p25_bbl", "double"), ("mediana_bbl", "double"), ("p75_bbl", "double"), ("media_bbl", "double"),
             ("mediana_ic_bajo", "double"), ("mediana_ic_alto", "double"), ("media_ic_bajo", "double"),
             ("media_ic_alto", "double"), ("proporcion_positiva", "double")]
COLS_PERM = [("grupo_edad", "varchar"), ("n_cercano", "integer"), ("no_recupera_cercano", "double"),
             ("n_control", "integer"), ("no_recupera_control", "double"), ("exceso", "double"),
             ("exceso_ic_bajo", "double"), ("exceso_ic_alto", "double"), ("umbral_indice", "double")]
COLS_DIF = [("padre", "integer"), ("hijo_cercano", "integer"), ("km_min", "double"), ("pad_id", "varchar"),
            ("grupo_edad", "varchar"), ("petroleo_diferido_bbl", "double")]
COLS_UBI = [("pozo_id", "integer"), ("pad_id", "varchar")]


def _warehouse_sintetico(path, total_original):
    con = duckdb.connect(str(path))
    brecha = []
    for g in ("06-11", "12-23", "24-47", "48+"):
        brecha.append((g, 1, 2, 0.8, 1.0, -0.2))
        brecha.append((g, 6, 2, 0.97, 1.0, -0.03))
    _escribir(con, "mart_interferencia_brecha", COLS_BRECHA, brecha)
    anillo = []
    for v, desc in (("V0", "2 a 5 km"), ("V1", "5 a 10 km"), ("V2", "2 a 10 km"), ("V3", "2 a 5 km bis")):
        anillo.append((v, desc, 1, 8, 80, 0.8, 1.0, -0.2, -0.25, -0.15))
        anillo.append((v, desc, 6, 8, 80, 0.97, 1.0, -0.03, -0.06, 0.0))
    _escribir(con, "mart_anillo", COLS_ANILLO, anillo)
    _escribir(con, "mart_descomposicion_distancia", COLS_DESCD,
              [(b, d, h, "5 a 10 km", 10, 100, 0.7, 1.0, -0.3, -0.4, -0.2, "-6 a -4")
               for b, d, h in (("0 a 0,3", 0.0, 0.3), ("0,3 a 0,6", 0.3, 0.6), ("0,6 a 1", 0.6, 1.0),
                               ("1 a 2", 1.0, 2.0), ("2 a 5", 2.0, 5.0))])
    _escribir(con, "mart_diferido_rango", COLS_RANGO,
              [("original", 1, total_original, 8, 56, total_original / 8, None),
               ("sin_duplicar", 2, 6000.0, 8, 56, 750.0, None),
               ("neto_previa", 3, 4000.0, 8, 56, 500.0, -0.04)])
    _escribir(con, "mart_diferido_operador", COLS_OPER,
              [("TODAS", 0, 8, 4, -100.0, 50.0, 200.0, -10.0, -60.0, 40.0, -200.0, 500.0, 0.5)])
    _escribir(con, "mart_perdida_permanente", COLS_PERM, [("todos", 8, 0.4, 80, 0.42, -0.02, -0.05, 0.01, 0.9)])
    _escribir(con, "mart_interferencia_diferida", COLS_DIF,
              [(1, 101, 0.2, "PADRE-1", "06-11", 1000.0), (2, 102, 0.2, "PADRE-2", "06-11", 1000.0),
               (3, 103, 0.4, "PADRE-3", "12-23", 1000.0), (4, 104, 0.4, "PADRE-4", "12-23", 1000.0),
               (5, 105, 0.7, "PADRE-5", "24-47", 1000.0), (6, 106, 0.7, "PADRE-6", "24-47", 1000.0),
               (7, 107, 0.8, "PADRE-7", "48+", 1000.0), (8, 108, 0.8, "PADRE-8", "48+", 1000.0)])
    _escribir(con, "int_pozo_ubicacion", COLS_UBI, [(101, "H-A"), (102, "H-A"), (103, "H-B"), (104, "H-B"),
                                                   (105, "H-C"), (106, "H-C"), (107, "H-D"), (108, "H-D")])
    con.close()


def test_main_escribe_los_cuatro_marts(tmp_path):
    db = tmp_path / "w.duckdb"
    _warehouse_sintetico(db, 8000.0)
    main(db)
    con = duckdb.connect(str(db), read_only=True)
    edad = {r[0]: r for r in con.execute("select * from mart_decision_edad").fetchall()}
    assert set(edad) == {"06-11", "12-23", "24-47", "48+", "todos"}
    assert edad["todos"][6] == pytest.approx(1000.0)
    assert edad["todos"][10] == pytest.approx(1000.0 / 6.2898)
    assert edad["06-11"][2] == 1  # un solo pad hijo (H-A), distinto del pad del padre
    assert edad["todos"][5] == pytest.approx(1.0 - 0.03 / 0.2)
    assert edad["06-11"][7] is None  # menos de 30 eventos: publica media, no intervalo
    dist = {r[0]: r for r in con.execute("select * from mart_decision_distancia").fetchall()}
    assert dist["0 a 0,3"][8] == pytest.approx(1000.0)
    assert dist["1 a 2"][8] is None and dist["2 a 5"][8] is None
    cierre = {r[0]: r for r in con.execute("select * from mart_decision_cierre").fetchall()}
    assert cierre["V0"][4] == pytest.approx(1.0 - 0.03 / 0.2)
    perdida = con.execute("select * from mart_decision_perdida").fetchall()[0]
    assert perdida[0] == pytest.approx(500.0) and perdida[1] == pytest.approx(500.0 / 6.2898)
    con.close()


def test_main_falla_si_la_suma_no_reproduce_el_total(tmp_path):
    db = tmp_path / "w.duckdb"
    _warehouse_sintetico(db, 9000.0)
    with pytest.raises(RuntimeError):
        main(db)


def _marts_decision(con):
    edad = []
    for g in ("06-11", "12-23", "24-47", "48+"):
        edad.append((g, 100, 20, -0.2, -0.03, 0.85, 5000.0, 4000.0, 6000.0, 2500.0, 795.0, 636.0, 954.0,
                     397.5, 795.0))
    edad.append(("todos", 400, 60, -0.2293, -0.0210, 0.9084, 5163.1, 3173.7, 6952.0, 2803.9, 820.9, 504.6,
                 1105.3, 445.8, 820.9))
    _escribir(con, "mart_decision_edad", COLS_EDAD, edad)
    dist = []
    for j, b in enumerate(("0 a 0,3", "0,3 a 0,6", "0,6 a 1")):
        dist.append((b, j, 300, -0.3, -0.4, -0.2, 300, 100, 5000.0, 4000.0, 6000.0, 2500.0, 795.0, 636.0,
                     954.0, 397.5, 795.0))
    for j, b in enumerate(("1 a 2", "2 a 5"), start=3):
        dist.append((b, j, 2000, -0.1, -0.14, -0.07, None, None, None, None, None, None, None, None, None,
                     None, None))
    _escribir(con, "mart_decision_distancia", COLS_DISTANCIA, dist)
    _escribir(con, "mart_decision_cierre", COLS_CIERRE,
              [(v, d, -0.23, -0.03, 0.87) for v, d in (("V0", "2 a 5 km"), ("V1", "5 a 10 km"),
                                                       ("V2", "2 a 10 km"), ("V3", "2 a 5 km bis"))])
    _escribir(con, "mart_decision_perdida", COLS_PERDIDA, [(1337.1, 212.6, -2830.5, -6502.8, 1337.1, -0.0191,
                                                           -0.051, 0.0122)])


def test_pagina_sin_rayas_y_con_las_secciones_en_orden():
    con = duckdb.connect(":memory:")
    _marts_decision(con)
    pagina = pagina_decision(con)
    con.close()
    assert chr(0x2014) not in pagina and chr(0x2013) not in pagina
    titulos = ["# Capa de decisión para un operador", "## Resumen", "## Por edad del padre",
               "## Por banda de espaciamiento", "## Cierre a 6 meses", "## Diferido o pérdida",
               "## Valor indicativo", "## Qué no se resuelve y qué dato interno lo resolvería",
               "## Cómo se reproduce"]
    pos = [pagina.index(t) for t in titulos]
    assert pos == sorted(pos)
    assert "entradas, no pronóstico ni precio observado" in pagina
    assert "El mes 6 no está publicado por distancia" in pagina
    assert "V0" in pagina and "V3" in pagina and "| todos |" in pagina
    assert "dentro de 5 puntos, no en cero" in pagina
    assert "no una pérdida demostrada" in pagina
