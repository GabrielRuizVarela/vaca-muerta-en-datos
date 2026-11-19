"""Pruebas sinteticas de pipeline.potencia_dosis (sin warehouse real)."""
from __future__ import annotations

import re
from statistics import NormalDist

import duckdb
import numpy as np
import pytest

from pipeline import dosis
from pipeline.costo import _escribir
from pipeline.potencia_dosis import (
    ALFA,
    B_SIM,
    COLS_POTENCIA_DOSIS,
    COLS_SIM,
    COLS_VEREDICTO_POT,
    N_CORRIDAS,
    SEMILLA_POT,
    Z80,
    Z95,
    aritmetica_interna,
    mde80,
    mde80_holm,
    necesarios,
    pagina_potencia_dosis,
    se_desde_ic,
    simular,
    veredicto,
)


def test_constantes_fijadas_por_la_regla():
    assert Z95 == pytest.approx(1.959963984540054)
    assert Z80 == pytest.approx(0.8416212335729143)
    assert ALFA == 0.05
    assert N_CORRIDAS == 200
    assert B_SIM == 300
    assert SEMILLA_POT == dosis.SEMILLA_DOSIS + 2_000_000


def test_se_desde_ic_y_mde80_a_mano():
    assert se_desde_ic(0, 0.392) == pytest.approx(0.1, rel=1e-3)
    assert mde80(0.1) == pytest.approx(0.28016, rel=1e-3)
    assert mde80(se_desde_ic(0, 0.392)) == pytest.approx((Z95 + Z80) * 0.1, rel=1e-3)


def test_mde80_holm_es_mayor_que_mde80_y_usa_m():
    se = 0.1
    esperado = (NormalDist().inv_cdf(1 - 0.05 / 8) + Z80) * se
    assert mde80_holm(se, 4) == pytest.approx(esperado)
    assert mde80_holm(se, 4) > mde80(se)
    assert mde80_holm(se, 5) > mde80_holm(se, 4)


def test_necesarios_factor_4_si_el_mde_duplica_el_objetivo():
    nec = necesarios(0.2, 0.1, 1500, 260)
    assert nec["factor"] == pytest.approx(4.0)
    assert nec["pads"] == pytest.approx(1040.0)
    assert nec["eventos"] == pytest.approx(6000.0)


def test_necesarios_factor_menor_que_1_si_el_mde_no_llega_al_objetivo():
    nec = necesarios(0.05, 0.1, 1500, 260)
    assert nec["factor"] == pytest.approx(0.25)
    assert nec["pads"] < 260 and nec["eventos"] < 1500


def test_veredicto_en_las_tres_ramas():
    assert veredicto(0.08)[0] == "alcanza para 0,1"
    assert veredicto(0.15)[0] == "alcanza para 0,2 y no para 0,1"
    assert veredicto(0.30)[0] == "no alcanza para 0,2"
    assert veredicto(0.10)[0] == "alcanza para 0,1"
    assert veredicto(0.20)[0] == "alcanza para 0,2 y no para 0,1"


def test_veredicto_cita_el_mde_y_nunca_descarta():
    for m in (0.08, 0.15, 0.30):
        codigo, texto = veredicto(m)
        assert "desvíos de la caída por desvío de la dosis" in texto
        assert "queda descartado" not in texto
    _codigo, texto = veredicto(0.30)
    assert "puede pasar inadvertido con este dato" in texto
    assert "el nulo de pipeline.dosis no descarta efectos de ese tamaño ni menores" in texto
    resto = texto.replace("no descarta", "")
    assert "descarta" not in resto


def test_aritmetica_interna_monotona_decreciente():
    pares = aritmetica_interna(0.3)
    assert [r2 for r2, _m in pares] == [0.1, 0.25, 0.5]
    mdes = [m for _r2, m in pares]
    assert mdes[0] > mdes[1] > mdes[2]
    assert mdes[0] == pytest.approx(0.3 * (1 - 0.1) ** 0.5)
    assert all(m < 0.3 for m in mdes)


def _sinteticos():
    rng = np.random.default_rng(11)
    n_pads, por_pad = 60, 5
    n = n_pads * por_pad
    X = np.column_stack([(c - c.mean()) / c.std() for c in [rng.normal(0, 1, n) for _ in range(4)]])
    grupo = np.zeros(n, dtype=int)
    # Ruido normal limpio como en produccion: se le quita el efecto muestral de X para que el
    # verdadero efecto bajo el nivel 0 sea exactamente 0 (si no, la correlacion espuria queda).
    y0 = rng.normal(0, 1, n)
    y0 = y0 - dosis._demean(X, grupo) @ dosis._ols(dosis._demean(y0, grupo), dosis._demean(X, grupo))
    C = np.zeros((n, 0))
    clave = np.repeat([f"pad{i}" for i in range(n_pads)], por_pad)
    return y0, X, C, grupo, clave, float(y0.std())


def test_simular_potencia_alta_con_delta_grande_y_tamano_chico():
    y0, X, C, grupo, clave, sd_y = _sinteticos()
    filas = simular(y0, X, C, grupo, clave, sd_y, [("plantado", [0.6, 0.0, 0.0, 0.0])],
                    corridas=24, reps=60, semilla_base=SEMILLA_POT, workers=1)
    pot = {(j, n, rg): s / c for j, n, _d, rg, c, s in filas}
    assert pot[(0, "plantado", "sin_ajustar")] >= 0.7
    for j in range(4):
        assert pot[(j, "0", "sin_ajustar")] <= 0.3


def test_simular_determinista_con_la_misma_semilla():
    y0, X, C, grupo, clave, sd_y = _sinteticos()
    niveles = [("plantado", [0.6, 0.0, 0.0, 0.0])]
    a = simular(y0, X, C, grupo, clave, sd_y, niveles, corridas=8, reps=20, workers=1)
    b = simular(y0, X, C, grupo, clave, sd_y, niveles, corridas=8, reps=20, workers=1)
    assert a == b
    assert {(n, rg) for _j, n, _d, rg, _c, _s in a} == {
        ("0", "holm"), ("0", "sin_ajustar"), ("plantado", "holm"), ("plantado", "sin_ajustar")}
    assert len(a) == 2 * 4 * 2  # dos niveles por cuatro variables por dos reglas


def _marts_potencia(con):
    filas = []
    for res in ("A", "B"):
        for modelo, variables in (("conjunto", dosis.VARIABLES),
                                  ("pad_completo", ("arena_pad", "arena_rama_pad", "presion_pad", "deplecion")),
                                  ("pad_cercania", ("arena_pad", "arena_rama_pad", "presion_pad", "deplecion",
                                                   "interaccion"))):
            m = 5 if modelo == "pad_cercania" else 4
            for k, var in enumerate(variables):
                se_d = 0.05 + 0.005 * k
                mde = mde80(se_d)
                mde_h = mde80_holm(se_d, m)
                nec1, nec2 = necesarios(mde, 0.1, 1500, 260), necesarios(mde, 0.2, 1500, 260)
                neh1, neh2 = necesarios(mde_h, 0.1, 1500, 260), necesarios(mde_h, 0.2, 1500, 260)
                filas.append((res, modelo, var, 1500, 260, 0.4, 0.02 * k, se_d, m, mde, mde_h,
                              nec1["pads"], nec2["pads"], nec1["eventos"], nec2["eventos"],
                              neh1["pads"], neh2["pads"], neh1["eventos"], neh2["eventos"]))
    _escribir(con, "mart_potencia_dosis", COLS_POTENCIA_DOSIS, filas)
    sim = []
    for j, var in enumerate(dosis.VARIABLES):
        nombre = dosis.NOMBRES[var]
        for nivel, delta in (("0", 0.0), ("0,1", 0.1), ("0,2", 0.2),
                             ("mde_sin_ajustar", 0.15 + 0.01 * j), ("mde_holm", 0.18 + 0.01 * j)):
            for regla in ("holm", "sin_ajustar"):
                s = 160 if nivel.startswith("mde") else (10 if nivel == "0" else 100)
                p = s / 200
                sim.append((nombre, nivel, delta, regla, 200, s, p, (p * (1 - p) / 200) ** 0.5))
    _escribir(con, "mart_potencia_dosis_sim", COLS_SIM, sim)
    _escribir(con, "mart_potencia_dosis_veredicto", COLS_VEREDICTO_POT,
              [("A",) + veredicto(0.19), ("B",) + veredicto(0.25)])


def test_pagina_con_marts_sinteticos():
    con = duckdb.connect(":memory:")
    _marts_potencia(con)
    pagina = pagina_potencia_dosis(con)
    con.close()
    assert pagina.startswith("# Potencia del nulo de dosis y respuesta")
    for titulo in ("## Veredicto", "## Efecto mínimo detectable",
                   "## Pads y eventos para ver 0,1 y 0,2 desvíos",
                   "## Simulación de planta y recupera (modelo conjunto, resultado A)",
                   "## Qué dato interno achicaría el error", "## Regla fijada antes de correr",
                   "## Qué no prueba"):
        assert titulo in pagina
    assert "Pads y eventos" in pagina
    assert "queda descartado" not in pagina
    assert re.search("[–—]", pagina) is None
    assert "Ilustración, no estimación" in pagina
    assert "valida la cuenta analítica" in pagina
