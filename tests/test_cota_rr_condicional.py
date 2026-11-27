"""Cota de Rambachan y Roth condicional (ronda 3, S1): las cuatro validaciones fijadas en la regla (de19052), sin warehouse,
y el armado de filas y pagina sobre sorteos sinteticos."""
import numpy as np

from pipeline import cota_rr_condicional as cc


def test_dualidad_vertices_igual_al_minimo_directo():
    r = cc.validar_dualidad()
    assert r["casos"] == 200
    assert r["peor"] <= 1e-9, r
    assert r["n_inf"] > 0       # hay casos sin vertice (dual infactible): los dos lados dan -inf


def test_cobertura_con_la_restriccion_en_el_borde():
    r = cc.validar_cobertura()
    assert set(r["tasas"]) == {(0.5, "ATT(1)"), (0.5, "media"), (1.0, "ATT(1)"), (1.0, "media")}
    for caso, t in r["tasas"].items():
        assert t >= cc.COBERTURA_MIN, (caso, t, r)


def test_potencia_plantada_excluye_el_cero():
    r = cc.validar_potencia()
    for caso, t in r["tasas"].items():
        assert t >= cc.POTENCIA_MIN, (caso, t, r)


def test_conjunto_con_mbar_cero_contiene_el_punto():
    # enmienda del ancho: la puerta es contener el punto; el ancho contra el tope de 2 es un dato que la pagina publica
    r = cc.validar_ancho()
    assert r["contiene"] == r["de"] and r["ok"], r
    assert r["tope"] == 2.0 and r["cumple_tope"] == (r["razon_max"] <= 2.0), r


def test_diagnostico_del_ancho():
    d = cc.diagnostico_ancho()
    assert len(d["poliedros"]) == 6 and d["n"] == cc.N_MC
    si = [f for f in d["poliedros"] if f["contiene_delta"]]
    assert si, d
    # los poliedros que contienen a la delta verdadera no rechazan theta verdadero mas que el 5 % nominal, con margen de simulacion
    assert all(f["rechazo"] <= 0.05 + 3 * (0.05 * 0.95 / cc.N_MC) ** 0.5 for f in si), si
    assert d["union_cobertura"] >= 0.95 and d["union_ancho_max"] >= max(f["ancho_max"] for f in d["poliedros"]) - 1e-9, d


def test_matriz_rm_y_vertices():
    A = cc.matriz_rm(-3, 1, 0.5)
    assert A.shape == (8, 5)
    # fila 0: s(-2) - s(-3) = d(-2) - 2 d(-3); filas posteriores: p - Mbar s(-3)
    assert np.allclose(A[0], [-2, 1, 0, 0, 0])
    assert np.allclose(A[4], [-0.5, 0, -1, 1, 0])
    assert np.allclose(A[7], [-0.5, 0, 0, 1, -1])
    V = cc.vertices(np.array([0, 1, -2]), np.array([1.0, 2.0, 1.0]))
    assert V.shape == (2, 3) and np.all(V >= 0)
    assert np.allclose(V @ np.array([0, 1, -2]), 0) and np.allclose(V @ np.array([1.0, 2.0, 1.0]), 1)


def test_sin_vertice_no_rechaza():
    # todas las X del mismo signo y distintas de cero: el dual es infactible, eta = -inf
    assert cc.vertices(np.array([1.0, 2.0]), np.array([1.0, 1.0])).shape == (0, 2)


def test_estimando_sintetico_arma_filas_y_pagina():
    rng = np.random.default_rng(7)
    media = np.array([0.5, 1.0, 0.8, -3.0 + 0.8, -3.0 + 0.8])
    vals = media + rng.standard_normal((300, 5)) @ np.linalg.cholesky(cc.SIGMA_SINT).T
    vals[3, 2] = np.nan     # un sorteo incompleto se descarta
    e = cc.calcular_estimando("D1", "ATT(1)", (0, 1), (1, 0), (1,), media, vals, 40)
    assert e["sorteos"] == 299
    assert [f[2] for f in e["filas"]] == ["grilla"] * len(cc.GRILLA_MBAR) + ["quiebre"]
    assert all(len(f) == len(cc.COLS_COTA_RR_COND) for f in e["filas"])
    g = [f for f in e["filas"] if f[2] == "grilla"]
    assert g[0][3] == 0.0 and g[0][4] is not None and g[0][8] <= g[0][9]
    # el conjunto crece con Mbar
    assert g[-1][5] - g[-1][4] >= g[0][5] - g[0][4]
    val = {"dualidad": {"casos": 200, "peor": 0.0, "ok": True}, "ok": True, "fallas": [],
           "cobertura": {"tasas": {(0.5, "ATT(1)"): 0.99}, "minimo": 0.93, "ok": True},
           "potencia": {"tasas": {"ATT(1)": 1.0}, "minimo": 0.9, "ok": True},
           "ancho": {"contiene": 20, "de": 20, "razon_max": 1.9, "razon_media": 1.5, "ok": True}}
    txt = cc.pagina_cota_rr_condicional(e["filas"], {("D1", "ATT(1)"): e["extra"]}, val)
    assert "de19052" in txt and "## D1, ATT(1)" in txt and "Lo que no dice" in txt
    assert cc.pagina_falla({**val, "ok": False, "fallas": ["ancho"]}).startswith("# Cota de Rambachan y Roth")
