"""Dosis y respuesta sobre datos sinteticos: OLS con EF, Holm, veredicto, p bootstrap y pagina."""
import duckdb
import numpy as np
import pytest

from pipeline import dosis
from pipeline.costo import _escribir


def test_ols_con_ef_recupera_el_coeficiente_plantado():
    rng = np.random.default_rng(7)
    n = 300
    grupo = rng.integers(0, 6, n)
    fe = np.array([1.5, -2.0, 0.5, 3.0, -1.0, 0.0])[grupo]
    x = rng.normal(size=n)
    c = rng.normal(size=(n, 2))
    y = 1.5 * x + c @ np.array([0.7, -0.4]) + fe
    beta = dosis._ols(dosis._demean(y, grupo), dosis._demean(np.column_stack([x, c]), grupo))
    assert beta[0] == pytest.approx(1.5, abs=1e-8)
    assert beta[1] == pytest.approx(0.7, abs=1e-8)
    assert beta[2] == pytest.approx(-0.4, abs=1e-8)


def test_holm_monotono_y_ejemplo_a_mano():
    adj = dosis._holm([0.01, 0.04, 0.03, 0.20])
    assert list(adj) == pytest.approx([0.04, 0.09, 0.09, 0.20], abs=1e-12)
    orden = np.argsort([0.01, 0.04, 0.03, 0.20])
    assert all(b >= a for a, b in zip(adj[orden][:-1], adj[orden][1:]))
    assert (adj <= 1.0).all()


def test_veredicto_los_cinco_codigos():
    cod, tex = dosis.veredicto(["arena por etapa", "depleción del padre"], [], [], 1400, 200)
    assert cod == "dosis y respuesta"
    assert tex == "la caída crece con arena por etapa y depleción del padre, como se espera de un golpe de fractura"
    cod, tex = dosis.veredicto(["arena por etapa"], [], [], 1400, 200)
    assert cod == "una sola variable"
    assert "arena por etapa" in tex and "la caída crece con" not in tex
    cod, tex = dosis.veredicto([], [], [], 1400, 200, semiancho=0.15)
    assert cod == "sin dosis y respuesta"
    assert "cierre preventivo" in tex and "0,15" in tex and "no haya golpes de fractura" in tex
    cod, tex = dosis.veredicto([], [], ["arena por etapa"], 1400, 200)
    assert cod == "orden sin coeficiente"
    assert "arena por etapa" in tex
    cod, _tex = dosis.veredicto([], [], [], 500, 200)
    assert cod == "no concluyente por muestra"
    cod, _tex = dosis.veredicto([], [], ["arena por etapa"], 1400, 100)
    assert cod == "no concluyente por muestra"
    cod, _tex = dosis.veredicto(["a", "b"], ["c"], [], 500, 100)
    assert cod == "dosis y respuesta"
    cod, _tex = dosis.veredicto(["a"], [], [], 500, 100)
    assert cod == "no concluyente por muestra"  # solo la regla positiva (dos o mas variables) no se debilita
    cod, _tex = dosis.veredicto(["a"], [], [], 1400, 200)
    assert cod == "una sola variable"


def test_p_boot_con_arreglo_conocido():
    b = np.array([0.1] * 1900 + [-0.1] * 100)
    assert dosis._p_boot(b) == pytest.approx(2 * 101 / 2001, abs=1e-12)
    assert dosis._p_boot(np.array([0.5, 0.2, 0.1])) == pytest.approx(2 * 1 / 4, abs=1e-12)
    assert dosis._p_boot(np.array([np.nan, np.nan])) == 1.0


def test_pagina_sobre_marts_a_mano_sin_rayas():
    con = duckdb.connect(":memory:")
    mod, qui, orde, sens = [], [], [], []
    for res in ("A", "B"):
        for j, var in enumerate(dosis.VARIABLES):
            mod.append((res, var, 0.01 * (j + 1), -0.02, 0.04, 0.10 * (j + 1), 0.20 * (j + 1), 1400, 200,
                        1.5, j == 0, False))
            for k in range(1, 6):
                qui.append((res, var, k, 100, 0.20 + 0.01 * k, 0.18, 0.22))
            orde.append((res, var, 500, 0.9, 0.05, 0.01, 0.09, 0.02, 0.04, True))
            for sen in ("sin_terminacion", "solo_tapon", "rangos", "sola"):
                sens.append((res, sen, var, 0.01, -0.01, 0.03, 1200 if sen != "solo_tapon" else 800))
    _escribir(con, "mart_dosis_modelo", dosis.COLS_MODELO, mod)
    _escribir(con, "mart_dosis_quintiles", dosis.COLS_QUINTILES, qui)
    _escribir(con, "mart_dosis_orden", dosis.COLS_ORDEN, orde)
    _escribir(con, "mart_dosis_sens", dosis.COLS_SENS, sens)
    _escribir(con, "mart_dosis_veredicto", dosis.COLS_VEREDICTO,
              [("A", "una sola variable", "solo arena por etapa cumple"),
               ("B", "sin dosis y respuesta", "el dato público no muestra dosis y respuesta")])
    t = dosis.pagina_dosis(con)
    assert chr(0x2013) not in t and chr(0x2014) not in t
    assert "# Dosis y respuesta" in t and "## Veredicto" in t and "## Sensibilidades" in t
    assert "no entran en el veredicto" in t and "## Qué no prueba" in t
    assert "arena por etapa" in t and "FIV" in t
    assert len(t.splitlines()) < 130
    con.close()
