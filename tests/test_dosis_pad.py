"""Dosis del pad sobre datos sinteticos: veredicto, pad_dose, interaccion y pagina."""
import math

import duckdb
import numpy as np

from pipeline import dosis, dosis_pad
from pipeline.costo import _escribir
from pipeline.placebo import _g


def test_veredicto_dosis_del_pad():
    cum = ["arena total del pad", "arena por metro de rama del pad"]
    cod, tex = dosis_pad.veredicto(cum, [], [], 1500, 200, 600, 120, 0.10, 0.20)
    assert cod == "dosis del pad y respuesta"
    assert "la caída crece con la dosis del pad" in tex
    assert "arena total del pad" in tex and "arena por metro de rama del pad" in tex


def test_veredicto_una_sola():
    cod, tex = dosis_pad.veredicto(["arena total del pad"], [], [], 1500, 200, 600, 120)
    assert cod == "una sola variable del pad"
    assert "no se escribe que la caída crece con la dosis" in tex


def test_veredicto_respuesta_solo_cercania():
    nom = dosis_pad.NOMBRES_PAD["interaccion"]
    cod, tex = dosis_pad.veredicto([], [nom], [], 1500, 200, 600, 120)
    assert cod == "respuesta solo en la cercania"
    assert nom in tex
    assert "exploratoria" in tex and "nueve pruebas" in tex
    assert "no cambia el veredicto de pipeline.dosis" in tex


def test_veredicto_sigue_sin_con_semianchos():
    cod, tex = dosis_pad.veredicto([], [], [], 1500, 200, 600, 120, 0.12, 0.25)
    assert cod == "sigue sin dosis y respuesta"
    assert "tampoco con la dosis del pad ni en la cercanía aparece respuesta" in tex
    assert _g(0.12, 2) in tex and _g(0.25, 2) in tex
    assert "desvíos de la caída" in tex


def test_veredicto_no_concluyente_por_completa():
    cod, _ = dosis_pad.veredicto([], [], [], 900, 200, 600, 120)
    assert cod == "no concluyente por muestra"
    cod2, _ = dosis_pad.veredicto([], [], [], 1500, 100, 600, 120)
    assert cod2 == "no concluyente por muestra"


def test_veredicto_no_concluyente_por_cercania():
    cod, _ = dosis_pad.veredicto([], [], [], 1500, 200, 300, 120)
    assert cod == "no concluyente por muestra"
    cod2, _ = dosis_pad.veredicto([], [], [], 1500, 200, 600, 80)
    assert cod2 == "no concluyente por muestra"


def test_veredicto_positiva_no_se_debilita():
    cum = ["arena total del pad", "presión máxima del pad"]
    cod, _ = dosis_pad.veredicto(cum, [], [], 500, 50, 100, 20)
    assert cod == "dosis del pad y respuesta"


def test_veredicto_signo_contrario_no_cambia_codigo():
    cod, tex = dosis_pad.veredicto([], [], ["arena total del pad"], 1500, 200, 600, 120)
    assert cod == "sigue sin dosis y respuesta"
    assert "; signo contrario en arena total del pad" in tex
    cum = ["arena total del pad", "arena por metro de rama del pad"]
    cod2, tex2 = dosis_pad.veredicto(cum, [], ["presión máxima del pad"], 1500, 200, 600, 120)
    assert cod2 == "dosis del pad y respuesta"
    assert "signo contrario en presión máxima del pad" in tex2


def _pozo(pid, arena, rama, presion, m):
    return {"pozo_id": pid, "arena": arena, "rama": rama, "presion": presion, "m": m}


def test_pad_dose_ventana_y_excluye_padre():
    m0 = 20250
    pozos = [
        _pozo(1, 100.0, 1000.0, 8000.0, m0),
        _pozo(2, 200.0, 2000.0, 9000.0, m0 + 1),
        _pozo(3, 300.0, 1500.0, 5000.0, m0 + 2),
        _pozo(99, 10000.0, 5000.0, 15000.0, m0),
    ]
    v1, v2, v3 = dosis_pad.pad_dose(pozos, 99, m0, 1)
    assert v1 == math.log(300.0)
    assert v2 == math.log(300.0 / 3000.0)
    assert v3 == 9000.0


def test_pad_dose_mismo_mes():
    m0 = 20250
    pozos = [
        _pozo(1, 100.0, 1000.0, 8000.0, m0),
        _pozo(2, 200.0, 2000.0, 9000.0, m0 + 1),
        _pozo(3, 400.0, 2000.0, 7000.0, m0 - 1),
    ]
    v1, v2, v3 = dosis_pad.pad_dose(pozos, 99, m0, 0)
    assert v1 == math.log(100.0)
    assert v2 == math.log(100.0 / 1000.0)
    assert v3 == 8000.0


def test_pad_dose_ignora_arena_no_positiva():
    m0 = 20250
    pozos = [
        _pozo(1, 0.0, 1000.0, 8000.0, m0),
        _pozo(2, -5.0, 1000.0, 8100.0, m0),
        _pozo(3, None, 1000.0, 8200.0, m0),
    ]
    v1, v2, v3 = dosis_pad.pad_dose(pozos, 99, m0, 1)
    assert math.isnan(v1) and math.isnan(v2)
    assert v3 == 8200.0


def test_pad_dose_v2_exige_rama_positiva():
    m0 = 20250
    pozos = [
        _pozo(1, 100.0, 0.0, 8000.0, m0),
        _pozo(2, 100.0, 1000.0, 8000.0, m0),
        _pozo(3, 50.0, None, 8000.0, m0),
    ]
    v1, v2, _v3 = dosis_pad.pad_dose(pozos, 99, m0, 1)
    assert v1 == math.log(250.0)
    assert v2 == math.log(100.0 / 1000.0)


def test_pad_dose_presion_fuera_de_rango():
    m0 = 20250
    pozos = [
        _pozo(1, 100.0, 1000.0, 0.0, m0),
        _pozo(2, 100.0, 1000.0, 20000.0, m0),
        _pozo(3, 100.0, 1000.0, 25000.0, m0),
        _pozo(4, 100.0, 1000.0, -10.0, m0),
        _pozo(5, 100.0, 1000.0, None, m0),
        _pozo(6, 100.0, 1000.0, 7000.0, m0),
    ]
    _v1, _v2, v3 = dosis_pad.pad_dose(pozos, 99, m0, 1)
    assert v3 == 7000.0
    _v1b, _v2b, v3b = dosis_pad.pad_dose(pozos[:5], 99, m0, 1)
    assert math.isnan(v3b)


def test_pad_dose_ventana_vacia_da_nan():
    m0 = 20250
    pozos = [_pozo(1, 100.0, 1000.0, 8000.0, m0 + 5)]
    v1, v2, v3 = dosis_pad.pad_dose(pozos, 99, m0, 1)
    assert math.isnan(v1) and math.isnan(v2) and math.isnan(v3)


def test_interaccion_estandarizada_y_producto():
    v4 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    km = np.array([0.10, 0.20, 0.30, 0.40, 0.49])
    inter = dosis_pad.interaccion_cercania(v4, km)
    assert abs(float(inter.mean())) < 1e-12
    assert abs(float(inter.std()) - 1.0) < 1e-12
    esperado = dosis._std(dosis._std(v4) * dosis._std(-km))
    assert np.allclose(inter, esperado)


def _marts_a_mano(con):
    filas = []
    for res in ("A", "B"):
        for j, var in enumerate(dosis_pad.VARIABLES_PAD):
            filas.append((res, "completo", var, 0.01 * (j + 1), -0.02, 0.04, 0.30, 0.40,
                          1500, 200, False, False))
        for j, var in enumerate(dosis_pad.VARIABLES_CERCA):
            filas.append((res, "cercania", var, 0.02 * (j + 1), -0.03, 0.05, 0.25, 0.35,
                          600, 120, False, False))
        for j, var in enumerate(dosis_pad.VARIABLES_PAD):
            filas.append((res, "mismo_mes", var, 0.015 * (j + 1), -0.02, 0.05, 0.30, 0.45,
                          1400, 190, False, False))
    _escribir(con, "mart_dosis_pad", dosis_pad.COLS_PAD, filas)
    _escribir(con, "mart_dosis_pad_veredicto", dosis_pad.COLS_VEREDICTO_PAD,
              [("A", "sigue sin dosis y respuesta", "texto A de prueba"),
               ("B", "sigue sin dosis y respuesta", "texto B de prueba")])


def test_pagina_sobre_marts_a_mano():
    con = duckdb.connect(":memory:")
    _marts_a_mano(con)
    txt = dosis_pad.pagina_dosis_pad(con)
    con.close()
    assert chr(0x2013) not in txt and chr(0x2014) not in txt
    assert txt.startswith("# Dosis del pad y cercanía")
    assert "## Veredicto" in txt
    assert "## Sensibilidad (mismo mes)" in txt
    assert "## Qué no prueba" in txt
    assert "agregada después de ver los resultados" in txt
    assert "| Variable | Coef por desvío | IC 95% | p Holm | Cumple |" in txt
    assert len(txt.splitlines()) <= 90
