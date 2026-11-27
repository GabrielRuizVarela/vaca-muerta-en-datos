"""Validacion fijada de pipeline.replicacion_operadores_agua con datos sinteticos (sin warehouse).

Las cinco pruebas son las del docstring del modulo: celdas propias de un operador, la lectura de un operador del agua (placebos de
dos colas), la familia con los que no se pudieron medir, la lectura de dos colas del placebo de fechas del petroleo, y la pagina.
"""
import numpy as np

from pipeline import causal
from pipeline import replicacion_operadores as ro
from pipeline import replicacion_operadores_agua as ra

LIMPIOS = {"previo": (0.2, -1.0, 1.4), "fecha_falsa": (-0.3, -1.5, 0.9), "distancia_falsa": (0.5, -0.8, 1.7)}


def _celda(tratados, controles, g=10):
    t, c = np.array(tratados), np.array(controles)
    return {"tratados": t, "controles": c, "base_t": t * 10.0, "base_c": c * 10.0, "g": g}


def _D():
    # pozos 0 a 19: 0-9 de A, 10-19 de B
    return {"operador": np.array(["A"] * 10 + ["B"] * 10, dtype=object)}


def test_celdas_propias_deja_solo_los_de_x_y_descarta_la_celda_corta():
    D = _D()
    ok = _celda([0, 1, 10, 11], [2, 3, 4, 5, 6, 7, 12, 13])             # A: 2 tratados y 6 controles; B: 2 y 2
    corta = _celda([0, 8], [3, 4, 5, 6, 14, 15, 16, 17])                # A: 4 controles (< minimo); B: 0 tratados
    sin_t = _celda([10, 11], [0, 1, 2, 3, 4, 5, 6])                     # A: 0 tratados
    assert causal.MIN_CONTROLES_CELDA == 5
    out = ra.celdas_propias(D, [ok, corta, sin_t], "A")
    assert len(out) == 1
    ce = out[0]
    assert list(ce["tratados"]) == [0, 1] and list(ce["controles"]) == [2, 3, 4, 5, 6, 7]
    assert list(ce["base_t"]) == [0.0, 10.0] and list(ce["base_c"]) == [20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    assert ce["g"] == 10
    assert ra.celdas_propias(D, [ok, corta, sin_t], "B") == []          # B no llega al minimo de controles en ninguna
    assert ra.celdas_propias(D, [], "A") == []


def test_lectura_operador_agua():
    se, lec, rotos = ra.lectura_operador_agua(80, 6.0, 2.0, 10.0, LIMPIOS)
    assert (se, lec, rotos) == (True, "se replica", [])
    # el ATT_W pasa pero un placebo previo de +3 con IC entero sobre cero rompe por arriba
    se, lec, rotos = ra.lectura_operador_agua(80, 6.0, 2.0, 10.0, {**LIMPIOS, "previo": (3.0, 1.0, 5.0)})
    assert (se, lec, rotos) == (False, "no se replica: rompe el placebo previo", ["previo"])
    # y uno de -3 con IC entero bajo cero tambien (dos colas)
    se, lec, rotos = ra.lectura_operador_agua(80, 6.0, 2.0, 10.0, {**LIMPIOS, "fecha_falsa": (-3.0, -5.0, -1.0)})
    assert (se, lec, rotos) == (False, "no se replica: rompe el placebo fecha falsa", ["fecha falsa"])
    # se nombran todos los que rompen, en el orden de PLACEBOS_AGUA
    se, lec, rotos = ra.lectura_operador_agua(80, 6.0, 2.0, 10.0, {"previo": (3.0, 1.0, 5.0), "fecha_falsa": (0.0, -1.0, 1.0),
                                                                   "distancia_falsa": (-2.5, -4.0, -0.5)})
    assert rotos == ["previo", "distancia falsa"] and lec == "no se replica: rompe el placebo previo, distancia falsa"
    # un placebo con IC sobre cero pero por debajo del umbral no rompe
    assert ra.lectura_operador_agua(80, 6.0, 2.0, 10.0, {**LIMPIOS, "previo": (1.0, 0.2, 1.8)})[0] is True
    # IC del ATT_W que cruza el cero
    assert ra.lectura_operador_agua(80, 6.0, -1.0, 10.0, LIMPIOS) == (False, "no se replica: el IC 95% no queda entero sobre cero", [])
    # menos de MIN_TRATADOS_MEDIR tratados, o algun valor sin valor
    assert ra.MIN_TRATADOS_MEDIR == 50
    se, lec, rotos = ra.lectura_operador_agua(49, 6.0, 2.0, 10.0, LIMPIOS)
    assert se is None and lec.startswith("no se pudo medir: ") and rotos == []
    nan = float("nan")
    for args in ((80, nan, 2.0, 10.0, LIMPIOS), (80, 6.0, nan, 10.0, LIMPIOS), (80, 6.0, 2.0, nan, LIMPIOS),
                 (80, 6.0, 2.0, 10.0, {**LIMPIOS, "distancia_falsa": (nan, nan, nan)})):
        se, lec, rotos = ra.lectura_operador_agua(*args)
        assert se is None and lec.startswith("no se pudo medir: ") and rotos == []


def test_familia_cuenta_a_los_que_no_se_pudieron_medir():
    f = ra.lectura_familia_agua([("A", True, "se replica"), ("B", None, "no se pudo medir: poco"), ("C", False, "no se replica: y")])
    assert (f["k"], f["n"]) == (1, 3)
    assert f["frase"] == "Se replica en 1 de 3 operadores: A (se replica); B (no se pudo medir: poco); C (no se replica: y)."
    assert ra.lectura_familia_agua([])["frase"] == "Se replica en 0 de 0 operadores."
    assert ra.lectura_familia_agua([("A", False, "no se replica: y")])["k"] == 0


def test_dos_colas_rompe_con_ic_de_2_a_9_y_no_con_una_cola():
    assert ra.rompe_dos_colas(0.02, 0.09) is True                     # IC entero sobre cero: rompe por arriba
    assert ra.rompe_dos_colas(-0.09, -0.02) is True
    assert ra.rompe_dos_colas(-0.02, 0.09) is False
    assert ra.rompe_dos_colas(float("nan"), 0.09) is None
    # con la regla de una cola de replicacion_operadores (placebo_ic_alto < 0), el mismo placebo no rompe
    se, _valor, lec = ro.lectura_operador(-0.2, -0.1, -0.01, 0.09, 60)
    assert se is True and lec == "se replica"


def test_pagina_dice_la_regla_la_etiqueta_post_hoc_y_no_inventa_cifras():
    nan = float("nan")
    fila = ("YPF", 255, 200, 900, 6.0, 2.0, 10.0, True, 0.2, -1.0, 1.4, -0.3, -1.5, 0.9, 0.5, -0.8, 1.7, "", True, "se replica")
    fila_nm = ("Vista", 60, 0, 0, nan, nan, nan, None, nan, nan, nan, nan, nan, nan, nan, nan, nan, "", None,
               "no se pudo medir: 0 tratados con dW en las celdas propias, menos de 50")
    fam = ra.lectura_familia_agua([("YPF", True, "se replica"), ("Vista", None, fila_nm[-1])])
    fila2 = ("Vista", 0.075, 0.02, 0.09, True, True, False, "no se replica con dos colas: el placebo de fechas da brecha de un lado")
    fam2 = (0, 1, "Con el placebo de dos colas, se replica en 0 de 1 operadores: " + fila2[-1] + ".")
    txt = ra.pagina_replicacion_operadores_agua([fila, fila_nm], (fam["k"], fam["n"], fam["frase"]), [fila2], fam2)
    assert fam["frase"] in txt and fam2[2] in txt
    assert "(post hoc)" in txt and "## Qué no prueba" in txt and "de19052" in txt
    assert "| YPF | 255 | 200 / 900 | 6,0 | 2,0 a 10,0 | sí |" in txt
    assert "| Vista | 7,5 | 2,0 a 9,0 | sí | sí | no |" in txt
    assert "| Vista | 60 | 0 / 0 | n/d |" in txt
    assert "No cambia el 1 de 1 de la regla de `de19052`" in txt and "5 de 7" not in txt   # la cuenta sale de filas2
