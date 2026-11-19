"""Pruebas sinteticas de pipeline.robustez_operador (sin warehouse real)."""
from __future__ import annotations

import re

import duckdb
import numpy as np

from pipeline import robustez_operador as ro
from pipeline.costo import _escribir


def _marco(seed: int = 0, efecto: float = -0.25, n: int = 600):
    """Marco sintetico: tres operadores, indice a k = 1 con efecto en los cercanos (banda 0) y a k = 6 sin efecto."""
    rng = np.random.default_rng(seed)
    banda = rng.choice([0, 1, 2], size=n, p=[0.3, 0.1, 0.6])
    op = rng.choice(["A", "B", "C", "D"], size=n, p=[0.5, 0.3, 0.17, 0.03])
    i1 = 1 + rng.normal(0, 0.1, n) + np.where(banda == 0, efecto, 0)
    i6 = 1 + rng.normal(0, 0.1, n)
    m = {"idx": {1: i1, 6: i6}, "banda": banda, "clave": rng.integers(0, 120, n), "area": op}
    return m, {"operador": op, "area": op}


def test_grupos_a_sacar_usa_el_piso_y_el_orden():
    m, por = _marco()
    g = ro.grupos_a_sacar(m, por["operador"], minimo=30)
    assert g[0] == "A" and "D" not in g
    cuentas = [int(((por["operador"] == x) & (m["banda"] == 0)).sum()) for x in g]
    assert cuentas == sorted(cuentas, reverse=True)


def test_grupos_a_sacar_ignora_eventos_sin_indice():
    m, por = _marco()
    m["idx"][1][por["operador"] == "A"] = np.nan
    assert "A" not in ro.grupos_a_sacar(m, por["operador"], minimo=1)


def test_tabla_salidas_trae_completa_y_cada_salida_con_dos_meses():
    m, por = _marco()
    filas = ro.tabla_salidas(m, por, reps=50)
    for eje in ro.EJES:
        sel = [f for f in filas if f[0] == eje]
        salidas = {f[1] for f in sel}
        assert ro.COMPLETA in salidas and len(salidas) == 1 + len(ro.grupos_a_sacar(m, por[eje]))
        assert {f[2] for f in sel} == {1, 6}
    completa = [f for f in filas if f[0] == "operador" and f[1] == ro.COMPLETA and f[2] == 1][0]
    assert completa[5] < -0.15 and completa[7] < 0


def test_sacar_un_grupo_baja_los_eventos():
    m, por = _marco()
    filas = ro.tabla_salidas(m, por, reps=50)
    full = [f for f in filas if f[0] == "operador" and f[1] == ro.COMPLETA and f[2] == 1][0]
    sin_a = [f for f in filas if f[0] == "operador" and f[1] == "A" and f[2] == 1][0]
    assert sin_a[3] < full[3]


def _fila(eje, salida, k, brecha, lo, hi):
    return (eje, salida, k, 100, 900, brecha, lo, hi)


def test_veredicto_se_sostiene_y_nombra_los_peores_casos():
    f = [_fila("operador", ro.COMPLETA, 1, -0.2, -0.25, -0.15), _fila("operador", ro.COMPLETA, 6, -0.02, -0.05, 0.01),
         _fila("operador", "X", 1, -0.18, -0.24, -0.1), _fila("operador", "X", 6, -0.03, -0.06, 0.0),
         _fila("operador", "Y", 1, -0.22, -0.3, -0.14), _fila("operador", "Y", 6, -0.01, -0.05, 0.03)]
    v = ro.veredicto_eje(f, "operador")
    assert v["gap1"] and v["cierre"]
    assert v["peor1"][1] == "X" and v["peor6"][1] == "X"
    assert "se sostiene" in ro._frase(v) and "sin X" in ro._frase(v)


def test_veredicto_no_se_sostiene_si_el_ic_cruza_cero_o_cae_bajo_la_mitad():
    base = [_fila("area", ro.COMPLETA, 1, -0.2, -0.25, -0.15), _fila("area", ro.COMPLETA, 6, -0.02, -0.05, 0.01)]
    cruza = base + [_fila("area", "X", 1, -0.15, -0.3, 0.01), _fila("area", "X", 6, -0.02, -0.05, 0.0)]
    assert not ro.veredicto_eje(cruza, "area")["gap1"]
    mitad = base + [_fila("area", "X", 1, -0.09, -0.12, -0.05), _fila("area", "X", 6, -0.02, -0.05, 0.0)]
    assert not ro.veredicto_eje(mitad, "area")["gap1"]
    abierto = base + [_fila("area", "X", 1, -0.2, -0.25, -0.15), _fila("area", "X", 6, -0.06, -0.1, -0.02)]
    v = ro.veredicto_eje(abierto, "area")
    assert v["gap1"] and not v["cierre"] and "no se sostiene" in ro._frase(v)


def test_veredicto_sin_grupos_lo_dice():
    v = ro.veredicto_eje([_fila("area", ro.COMPLETA, 1, -0.2, -0.25, -0.15)], "area")
    assert not v["gap1"] and "No hay grupos" in v["texto"]


def test_constantes_fijadas_por_la_regla():
    assert ro.MIN_CERCANOS == 50 and ro.CIERRE_PUNTOS == 5.0 and ro.MITAD == 0.5 and ro.KS == (1, 6)


def test_pagina_sin_guiones_largos_y_con_las_secciones():
    m, por = _marco()
    filas = ro.tabla_salidas(m, por, reps=50)
    con = duckdb.connect()
    _escribir(con, "mart_robustez_operador", ro.COLS_ROB_OP, filas)
    vers = []
    for eje in ro.EJES:
        v = ro.veredicto_eje(filas, eje)
        vers.append((eje, v["gap1"], v["cierre"], v["peor1"][1], v["peor6"][1], ro._frase(v)))
    _escribir(con, "mart_robustez_operador_veredicto", ro.COLS_VER_OP, vers)
    t = ro.pagina_robustez_operador(con)
    assert "\u2014" not in t and "\u2013" not in t
    for h in ("Sacando de a un operador", "Sacando de a un área", "Regla fijada antes de correr", "## Colorado", "Qué no prueba"):
        assert h in t
    assert re.search(r"\| \(muestra completa\) \| [\d.]+ \| [\d.]+ \| -?\d+,\d+ \|", t)
    assert "descart" not in t.lower().replace("descartar", "")


def test_colorado_sin_dosis_lee_el_sql_real():
    assert ro.colorado_sin_dosis() is True


def test_hoja_resumen_para_operador_es_corta_y_sin_guiones_largos():
    from pathlib import Path
    t = (Path(__file__).resolve().parent.parent / "docs" / "resumen-operador.md").read_text(encoding="utf-8")
    assert "—" not in t and "–" not in t
    assert len(t.split()) <= 450
    for h in ("## Qué se ve", "## Qué no se sabe", "## Qué hacer con esto"):
        assert h in t
