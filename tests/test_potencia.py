import math
from datetime import datetime

import numpy as np

from pipeline import potencia as pt


def _sintetico(n_pads=30, por_pad=8, R=1.0, th=93.0, ruido=0.2, semilla=11):
    """Muestra chica con eje plantado: controles mas R cos(2 (rumbo menos th)) mas ruido, en pads."""
    rng = np.random.default_rng(semilla)
    n = n_pads * por_pad
    clave = np.repeat([f"pad{i}" for i in range(n_pads)], por_pad)
    rumbo = rng.uniform(0, 180, n)
    km = rng.uniform(0.3, 1.0, n)
    edad = rng.integers(1, 60, n).astype(float)
    ctrl = np.column_stack([km, np.log(np.maximum(edad, 1))])
    grupo = np.repeat(np.arange(n_pads) % 2, por_pad)
    caida = (0.3 * km + 0.1 * np.log(edad)
             + R * np.cos(2 * (np.radians(rumbo) - math.radians(th))) + rng.normal(0, ruido, n))
    muestra = {"rumbo": rumbo, "ctrl": ctrl, "grupo": grupo, "clave": clave}
    return muestra, pt.ajuste_real(caida, ctrl, rumbo, grupo), caida


def test_ajuste_recupera_el_eje_y_descompone_la_caida():
    muestra, ajuste, caida = _sintetico()
    assert abs((ajuste["theta"] - 93.0 + 90) % 180 - 90) < 5.0
    assert abs(ajuste["amplitud"] - 1.0) < 0.15
    r = np.radians(muestra["rumbo"])
    axial = ajuste["beta"][-2] * np.cos(2 * r) + ajuste["beta"][-1] * np.sin(2 * r)
    assert np.allclose(ajuste["control"] + axial + ajuste["residuos"], caida)


def test_potencia_alta_con_amplitud_fuerte():
    muestra, ajuste, _caida = _sintetico()
    p = pt.potencia(muestra, ajuste, 1.0, 93.0, 1.0, corridas=25, reps_ic=50)
    assert p >= 0.80


def test_separa_conoce_el_arco_y_el_corte_en_cero():
    recto = {"eje": 93.0, "ic_bajo": 70.0, "ic_alto": 122.0, "ancho_ic": 52.0}
    assert pt.separa(recto, 67.5) is True
    assert pt.separa(recto, 100.0) is False
    assert pt.separa(recto, 70.0) is False
    vuelta = {"eje": 5.0, "ic_bajo": 170.0, "ic_alto": 20.0, "ancho_ic": 30.0}
    assert pt.separa(vuelta, 90.0) is True
    assert pt.separa(vuelta, 175.0) is False
    assert pt.separa(vuelta, 10.0) is False
    assert pt.separa(vuelta, 0.0) is False
    todo = {"eje": 5.0, "ic_bajo": 5.0, "ic_alto": 5.0, "ancho_ic": 180.0}
    assert pt.separa(todo, 90.0) is False


def test_simular_da_claves_unicas_y_mueve_las_filas_juntas():
    muestra, ajuste, _caida = _sintetico(n_pads=10, por_pad=6)
    sim = pt.simular(np.random.default_rng(3), muestra, ajuste, 2.0, 93.0, 1.0)
    assert len(np.unique(sim["clave"])) == 20
    assert len(sim["caida"]) == 120
    reales = {tuple(sorted(muestra["rumbo"][muestra["clave"] == p])) for p in np.unique(muestra["clave"])}
    for c in np.unique(sim["clave"]):
        assert tuple(sorted(sim["rumbo"][sim["clave"] == c])) in reales


def test_misma_semilla_da_mismo_resultado():
    muestra, ajuste, _caida = _sintetico()
    a = pt.simular(np.random.default_rng(8), muestra, ajuste, 1.5, 67.5, 0.5)
    b = pt.simular(np.random.default_rng(8), muestra, ajuste, 1.5, 67.5, 0.5)
    assert np.array_equal(a["caida"], b["caida"])
    assert np.array_equal(a["clave"], b["clave"])
    p1 = pt.potencia(muestra, ajuste, 1.0, 93.0, 1.0, corridas=10, reps_ic=30)
    p2 = pt.potencia(muestra, ajuste, 1.0, 93.0, 1.0, corridas=10, reps_ic=30)
    assert p1 == p2


def test_m80_interpola_y_avisa_si_no_llega():
    v, t = pt.m80([(1.0, 0.50), (1.5, 0.70), (2.0, 0.90)])
    assert v == 1.75
    assert t == "1,75 veces"
    assert pt.m80([(1.0, 0.10), (4.0, 0.50)]) == (None, "mas de 4")
    assert pt.m80([(1.0, 0.85), (1.5, 0.90)])[0] == 1.0


def test_veredicto_y_cuenta_analitica():
    assert pt.veredicto(None) == "no separable"
    assert pt.veredicto(2.5) == "no separable"
    assert pt.veredicto(1.75) == "alcanzable con 1,5 a 2 veces"
    assert pt.veredicto(1.2) == "alcanzable pronto"
    assert pt.n_analitico(1734, 52.590745091260885) == 1734 * (((52.590745091260885 / 2) / 1.96) / (25.5 / 2.8)) ** 2


def test_calendario_anualiza_2026():
    meses = [datetime(2025, m, 1) for m in range(1, 13)] * 2 + [datetime(2026, m, 1) for m in range(1, 8)] * 3
    cal = pt.calendario(meses)
    assert (cal["n2025"], cal["meses2025"], cal["n2026"], cal["meses2026"]) == (24, 12, 21, 7)
    assert cal["n2026_anual"] == 36.0
    assert cal["eventos_por_anio"] == 30.0
