"""Pruebas sinteticas de pipeline.anillo (sin warehouse)."""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline.anillo import COLS_ANILLO, COLS_VEREDICTO, VARIANTES, _limpio, pagina_anillo, veredicto
from pipeline.costo import _escribir

OK1 = (-0.15, -0.20, -0.10)  # brecha menor que -0,10 con IC que excluye cero
OK6 = (0.02, -0.01, 0.04)  # valor absoluto menor que 0,05
MALA1 = (-0.05, -0.10, 0.01)  # brecha no menor que -0,10
MALA6 = (0.08, 0.03, 0.12)  # valor absoluto de 0,05 o mas


def _filas(mes1, mes6):
    filas = []
    for v, _ in VARIANTES:
        b, lo, hi = mes1.get(v, OK1)
        filas.append((v, 1, b, lo, hi))
        b, lo, hi = mes6.get(v, OK6)
        filas.append((v, 6, b, lo, hi))
    return filas


def test_veredicto_robusto():
    codigo, texto = veredicto(_filas({}, {}))
    assert codigo == "robusto a la eleccion del control"
    assert "las cuatro variantes" in texto


def test_veredicto_mes1():
    codigo, texto = veredicto(_filas({"V1": MALA1}, {}))
    assert codigo == "la brecha del mes 1 depende del control"
    assert "V1" in texto


def test_veredicto_mes1_por_ic():
    codigo, _ = veredicto(_filas({"V2": (-0.15, -0.20, 0.05)}, {}))
    assert codigo == "la brecha del mes 1 depende del control"


def test_veredicto_cierre():
    codigo, texto = veredicto(_filas({}, {"V3": MALA6}))
    assert codigo == "el cierre depende del control"
    assert "contra los controles de 2 a 5 km la brecha se cierra a los 6 meses; contra" in texto
    assert "V3" in texto


def test_veredicto_ambos():
    codigo, texto = veredicto(_filas({"V1": MALA1}, {"V3": MALA6}))
    assert codigo == "la brecha del mes 1 y el cierre dependen del control"
    assert "V1" in texto and "V3" in texto


def _d10(pares):
    return {
        "hijo_mes": np.array([p[1] for p in pares]),
        "par_hijo": np.arange(len(pares)),
        "par_padre": np.array([p[0] for p in pares]),
        "par_km": np.array([p[2] for p in pares], dtype=float),
    }


def _m():
    return {"padre": np.array([0]), "mes": np.array([100])}


def test_limpio_hijo_cercano():
    d10 = _d10([(0, 98, 0.8)])
    assert list(_limpio(d10, _m(), 1.0, 6, 3)) == [False]


def test_limpio_solo_2km():
    d10 = _d10([(0, 98, 1.5)])
    assert list(_limpio(d10, _m(), 1.0, 6, 3)) == [True]
    assert list(_limpio(d10, _m(), 2.0, 6, 6)) == [False]


def test_pagina_sin_rayas():
    con = duckdb.connect(":memory:")
    marts = []
    for v, desc in VARIANTES:
        marts.append((v, desc, 1, 10, 20, 0.8, 0.95, -0.15, -0.20, -0.10))
        marts.append((v, desc, 6, 9, 18, 0.97, 0.95, 0.02, -0.01, 0.04))
    _escribir(con, "mart_anillo", COLS_ANILLO, marts)
    _escribir(con, "mart_anillo_veredicto", COLS_VEREDICTO,
              [("robusto a la eleccion del control", "texto corto", "detalle corto")])
    pagina = pagina_anillo(con)
    con.close()
    assert chr(0x2014) not in pagina and chr(0x2013) not in pagina
    assert "Veredicto" in pagina and "V0" in pagina and "V3" in pagina
