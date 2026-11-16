"""Eje de exposicion con datos sinteticos: media axial, PCA de filas, pesos, ajuste ponderado y veredicto."""

import numpy as np

from pipeline import costo, eje_exposicion as ee


def test_media_axial_recupera_eje():
    rng = np.random.default_rng(7)
    theta, rbar = ee.eje_axial_medio(rng.normal(100, 10, 2000) % 180)
    assert ee.dist_axial(theta, 100) < 2.0
    assert rbar > 0.85


def test_media_axial_a_caballo_del_cero():
    rng = np.random.default_rng(8)
    theta, rbar = ee.eje_axial_medio(rng.normal(178, 8, 2000) % 180)
    assert ee.dist_axial(theta, 178) < 2.0
    assert rbar > 0.85


def test_filas_este_oeste_y_norte_sur():
    rng = np.random.default_rng(3)
    b_ew, raz_ew = ee.eje_filas(np.linspace(0, 10, 40), rng.normal(0, 0.05, 40))
    assert ee.dist_axial(b_ew, 90) < 2.0
    assert raz_ew > 10
    b_ns, raz_ns = ee.eje_filas(rng.normal(0, 0.05, 40), np.linspace(0, 10, 40))
    assert ee.dist_axial(b_ns, 0) < 2.0
    assert raz_ns > 10


def test_pesos_suman_n_e_igualan_bines():
    rng = np.random.default_rng(5)
    rumbo = np.r_[rng.uniform(80, 100, 300), rng.uniform(0, 180, 100)]
    grupo = np.r_[np.zeros(300, dtype=int), np.ones(100, dtype=int)]
    w = ee.pesos_densidad_inversa(rumbo, grupo)
    assert abs(w[grupo == 0].sum() - 300) < 1e-9
    assert abs(w[grupo == 1].sum() - 100) < 1e-9
    for g in (0, 1):
        m = grupo == g
        b = np.minimum((rumbo[m] % 180 // 15).astype(int), 11)
        tot = np.bincount(b, weights=w[m], minlength=12)
        nz = tot[tot > 0]
        assert len(nz) > 1
        assert np.allclose(nz, nz[0])


def test_ponderado_con_pesos_iguales_iguala_ajustar_eje():
    rng = np.random.default_rng(9)
    n = 400
    rumbo = rng.uniform(0, 180, n)
    ctrl = np.column_stack([rng.uniform(0.3, 1.0, n), np.log(rng.uniform(6, 60, n))])
    grupo = rng.integers(0, 3, n)
    caida = (np.array([0.5, -0.3, 0.1])[grupo] + 0.2 * ctrl[:, 0] - 0.1 * ctrl[:, 1]
             + 0.3 * np.cos(np.radians(2 * (rumbo - 100))) + rng.normal(0, 0.1, n))
    t0 = costo.ajustar_eje(caida, ctrl, rumbo, grupo)[0]
    t1 = ee.ajustar_eje_ponderado(caida, ctrl, rumbo, grupo, np.ones(n))[0]
    assert ee.dist_axial(t1, t0) < 1e-6


def test_exposicion_area_ic_rapido_y_deterministico():
    rng = np.random.default_rng(13)
    rumbo = rng.normal(100, 15, 300) % 180
    clave = np.repeat([f"p{i}" for i in range(20)], 15)
    r = ee.exposicion_area(rumbo, clave, reps=50, semilla=1)
    assert ee.dist_axial(r["eje"], 100) < 5.0
    assert 0 < r["ancho_ic"] < 90
    assert ee.en_ic(r["eje"], r["ic_bajo"], r["ic_alto"], r["eje"])
    assert r == ee.exposicion_area(rumbo, clave, reps=50, semilla=1)


def test_filas_area_ic_rapido():
    rng = np.random.default_rng(17)
    r = ee.filas_area(np.linspace(0, 10, 30), rng.normal(0, 0.1, 30), reps=50, semilla=2)
    assert ee.dist_axial(r["eje"], 90) < 5.0
    assert 0 <= r["ancho_ic"] < 90


def test_reponderado_humo_rapido():
    rng = np.random.default_rng(21)
    n = 300
    rumbo = rng.uniform(0, 180, n)
    ctrl = np.column_stack([rng.uniform(0.3, 1, n), np.log(rng.uniform(6, 60, n))])
    grupo = np.repeat([0, 1], [n // 2, n - n // 2])
    caida = 0.3 * np.cos(np.radians(2 * (rumbo - 100))) + rng.normal(0, 0.2, n)
    clave = np.repeat([f"p{i}" for i in range(25)], 12)
    r = ee.eje_reponderado_intervalo(caida, ctrl, rumbo, clave, grupo, reps=20, reps_perm=19, semilla=4)
    assert ee.dist_axial(r["eje"], 100) < 15.0
    assert 0 < r["p_perm"] <= 1


def test_veredicto_dispara_con_cualquiera():
    assert ee.veredicto_exposicion(True, False) == ("geometria explica el eje", True)
    assert ee.veredicto_exposicion(False, True) == ("geometria explica el eje", True)
    assert ee.veredicto_exposicion(True, True) == ("geometria explica el eje", True)
    assert ee.veredicto_exposicion(False, False) == ("no lo explica la exposicion que se midio", False)
