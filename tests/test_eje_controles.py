"""Controles del eje con datos sinteticos: IC circular, muestra por k, bloques y veredictos."""

import numpy as np

from pipeline import costo, eje_controles as ec


def _m(eje: float, amplitud: float, k_efecto: int = -1, n_pads: int = 30, por_pad: int = 10,
       semilla: int = 11) -> dict:
    """Cercanos y controles sinteticos: en el mes k_efecto el indice cercano es 1 menos la amplitud por el coseno
    axial del rumbo alrededor del eje, mas ruido; los controles valen 1 mas ruido en todos los meses."""
    rng = np.random.default_rng(semilla)
    n_near, n_ctrl = n_pads * por_pad, n_pads * por_pad
    rumbo = np.r_[rng.uniform(0, 180, n_near), rng.uniform(0, 180, n_ctrl)]
    efecto = np.r_[amplitud * np.cos(np.radians(2 * (rumbo[:n_near] - eje))), np.zeros(n_ctrl)]
    km = np.r_[rng.uniform(0.3, 1.0, n_near), rng.uniform(2.0, 5.0, n_ctrl)]
    banda = np.r_[np.zeros(n_near, dtype=int), np.full(n_ctrl, 2)]
    edad = rng.integers(6, 60, n_near + n_ctrl)
    clave = np.tile(np.repeat(np.arange(n_pads), por_pad), 2)
    idx = {}
    for k in (-1, 1):
        base = 1.0 + rng.normal(0, 0.1, n_near + n_ctrl)
        if k == k_efecto:
            base -= efecto
        idx[k] = base
    return {"edad": edad, "idx": idx, "banda": banda, "km": km, "rumbo": rumbo, "clave": clave,
            "area": np.where(clave % 2 == 0, "A", "B"), "lat": rng.uniform(-38.5, -37.5, n_near + n_ctrl)}


def _ajuste(m: dict, k: int, semilla: int) -> tuple:
    """Muestra del mes k y eje con pocas repeticiones (rapido)."""
    e = ec.datos_eje(m, k)
    assert e is not None
    r = costo.eje_con_intervalo(e["caida"], e["ctrl"], e["rumbo"], e["clave"], grupo=e["grupo"], reps=50,
                                reps_perm=49, semilla=semilla)
    return e, r


def test_en_ic_sin_vuelta():
    assert ec.en_ic(93.0, 70.0, 122.0, 93.0)
    assert ec.en_ic(70.0, 70.0, 122.0, 93.0)
    assert ec.en_ic(122.0, 70.0, 122.0, 93.0)
    assert not ec.en_ic(67.5, 70.0, 122.0, 93.0)
    assert not ec.en_ic(130.0, 70.0, 122.0, 93.0)


def test_en_ic_con_vuelta():
    assert ec.en_ic(5.0, 170.0, 20.0, 5.0)
    assert ec.en_ic(175.0, 170.0, 20.0, 5.0)
    assert ec.en_ic(10.0, 170.0, 20.0, 5.0)
    assert ec.en_ic(170.0, 170.0, 20.0, 5.0)
    assert ec.en_ic(20.0, 170.0, 20.0, 5.0)
    assert not ec.en_ic(100.0, 170.0, 20.0, 5.0)
    assert not ec.en_ic(90.0, 170.0, 20.0, 5.0)


def test_dist_axial():
    assert abs(ec.dist_axial(10.0, 170.0) - 20.0) < 1e-9
    assert abs(ec.dist_axial(93.0, 67.5) - 25.5) < 1e-9
    assert abs(ec.dist_axial(40.0, 40.0)) < 1e-9


def test_eje_plantado_en_kmenos1_se_recupera_y_queda_definido():
    _e, r = _ajuste(_m(40.0, 0.5, k_efecto=-1), -1, 3)
    assert ec.es_definido(r["p_perm"], r["ancho_ic"])
    assert ec.dist_axial(r["eje"], 40.0) < 10


def test_sin_efecto_el_eje_no_queda_definido():
    _e, r = _ajuste(_m(40.0, 0.0, k_efecto=-1), -1, 5)
    assert not ec.es_definido(r["p_perm"], r["ancho_ic"])


def test_bloque_misma_celda_mismo_codigo():
    assert ec.bloque_para(-38.123, -68.456, 5.0) == ec.bloque_para(-38.1225, -68.4555, 5.0)


def test_bloque_otra_celda_otro_codigo():
    assert ec.bloque_para(-38.123, -68.456, 5.0) != ec.bloque_para(-38.123, -68.0, 5.0)


def test_veredicto_previo():
    assert ec.veredicto_previo(0.02, 50.0, 20.0) == ("definido y cercano", True)
    assert ec.veredicto_previo(0.02, 50.0, 40.0) == ("definido y lejano", False)
    assert ec.veredicto_previo(0.02, 50.0, 30.0) == ("definido y lejano", False)
    assert ec.veredicto_previo(0.2, 50.0, 5.0) == ("no definido", False)
    assert ec.veredicto_previo(0.02, 95.0, 5.0) == ("no definido", False)


def test_veredicto_bloques():
    assert ec.veredicto_bloques(0.02, 50.0, 144) == ("sigue definido", False)
    assert ec.veredicto_bloques(0.02, 95.0, 144) == ("deja de estar definido", True)
    assert ec.veredicto_bloques(0.2, 50.0, 144) == ("deja de estar definido", True)
    assert ec.veredicto_bloques(0.02, 50.0, 20) == ("sin veredicto (menos de 30 bloques)", False)
