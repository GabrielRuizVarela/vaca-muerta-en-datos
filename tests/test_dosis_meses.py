"""Dosis mes a mes sobre datos sinteticos: veredicto, Holm de 16 y pagina."""
import inspect

import duckdb
import numpy as np

from pipeline import dosis, dosis_meses
from pipeline.costo import _escribir


def _filas_16(cumplen=(), contrarias=()):
    filas = []
    for k in (1, 2, 3, 4):
        for var in dosis.VARIABLES:
            nom = dosis.NOMBRES[var]
            if (k, nom) in cumplen:
                filas.append((k, nom, 0.05, 0.01))
            elif (k, nom) in contrarias:
                filas.append((k, nom, -0.05, 0.01))
            else:
                filas.append((k, nom, 0.01, 0.40))
    assert len(filas) == 16
    return filas


def test_veredicto_tampoco_sin_celdas():
    cod, tex = dosis_meses.veredicto(_filas_16())
    assert cod == "tampoco con respuesta tardia"
    assert tex == ("tampoco aparece una respuesta en los meses 2 a 4: "
                   "ninguna de las 16 celdas cumple tras Holm")


def test_veredicto_tampoco_lista_signo_contrario():
    nom = dosis.NOMBRES["presion"]
    cod, tex = dosis_meses.veredicto(_filas_16(contrarias={(3, nom)}))
    assert cod == "tampoco con respuesta tardia"
    assert "signo contrario en mes 3, " + nom in tex


def test_veredicto_respuesta_tardia_exploratoria():
    nom = dosis.NOMBRES["arena_etapa"]
    cod, tex = dosis_meses.veredicto(_filas_16(cumplen={(2, nom)}))
    assert cod == "respuesta tardia exploratoria"
    assert f"mes 2, {nom}" in tex
    assert "exploratoria" in tex and "16 pruebas" in tex
    assert "no cambia el veredicto del mes 1" in tex


def test_veredicto_solo_el_mes_1():
    nom = dosis.NOMBRES["deplecion"]
    cod, tex = dosis_meses.veredicto(_filas_16(cumplen={(1, nom)}))
    assert cod == "solo el mes 1"
    assert cod != "tampoco con respuesta tardia"
    assert "vale el veredicto del mes 1 de pipeline.dosis" in tex


def test_holm_16_monotono_y_valor_a_mano():
    ps = [0.001, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15,
          0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 0.90]
    adj = dosis_meses.holm_16(ps)
    assert adj.shape == (4, 4)
    plano = adj.reshape(16)
    assert plano[0] == np.float64(16 * 0.001)
    orden = np.argsort(ps, kind="stable")
    assert all(b >= a for a, b in zip(plano[orden][:-1], plano[orden][1:]))
    assert (plano <= 1.0).all()
    assert (plano >= np.asarray(ps)).all()


def test_pagina_sobre_marts_a_mano_sin_rayas():
    con = duckdb.connect(":memory:")
    filas = []
    for k in (1, 2, 3, 4):
        for j, var in enumerate(dosis.VARIABLES):
            filas.append((k, var, 0.01 * (j + 1), -0.02, 0.04, 0.10 * (j + 1), 0.20 * (j + 1),
                          1400 - 100 * k, 200 - 10 * k, j == 0 and k == 2, False))
    _escribir(con, "mart_dosis_meses", dosis_meses.COLS_MESES, filas)
    _escribir(con, "mart_dosis_meses_veredicto", dosis_meses.COLS_VEREDICTO_MESES,
              [("respuesta tardia exploratoria", "cumple mes 2, arena por etapa: texto de prueba",
                "reproduce pipeline.dosis (diferencia máxima 0,0000)")])
    txt = dosis_meses.pagina_dosis_meses(con)
    con.close()
    assert chr(0x2013) not in txt and chr(0x2014) not in txt
    assert txt.startswith("# Dosis y respuesta mes a mes")
    assert "## Veredicto" in txt and "respuesta tardia exploratoria" in txt
    for k in (1, 2, 3, 4):
        assert f"### Mes {k} (n = " in txt
    assert "## Qué no prueba" in txt
    assert len(txt.splitlines()) <= 70


def test_caida_b_k_por_defecto_1():
    assert inspect.signature(dosis._caida_b).parameters["k"].default == 1
