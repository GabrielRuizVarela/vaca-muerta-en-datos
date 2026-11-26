"""Cota de Rambachan y Roth: el conjunto identificado contiene el efecto verdadero bajo una violacion plantada."""
import numpy as np
import pytest

from pipeline import cota_rr as rr


def _serie_lineal(tau: float, pendiente: float, previos=(-3, -2, -1), posteriores=(0, 1, 2)):
    """beta(e) = tendencia lineal (sesgo) + tau en los posteriores; la base (mes -5 en promedio) vale cero."""
    sesgo = {e: pendiente * (e + 5) for e in previos + posteriores}
    beta = {e: sesgo[e] + (tau if e >= 0 else 0.0) for e in sesgo}
    return beta


@pytest.mark.parametrize("tau", [0.0, -10.0, 7.5])
def test_violacion_lineal_plantada_queda_dentro_con_mbar_uno(tau):
    # tendencia lineal: saltos previos de 2, 1, 1 (el primero es contra la base); los posteriores, de 1
    b = _serie_lineal(tau, pendiente=-1.0)
    for meses in ((0,), (1,), (0, 1)):
        l_beta = np.mean([b[e] for e in meses])
        lo, hi = rr.conjunto(l_beta, b[-3], b[-2], b[-1], 1.0, meses)
        assert lo <= tau <= hi


def test_violacion_mayor_que_mbar_queda_fuera():
    # sesgo posterior que salta 3 por mes con previos que saltan a lo sumo 1: hace falta Mbar = 3 para cubrirlo
    b = {-3: -1.0, -2: -2.0, -1: -3.0, 0: -6.0, 1: -9.0}
    lo, hi = rr.conjunto(b[1], b[-3], b[-2], b[-1], 1.0, (1,))
    assert not (lo <= 0.0 <= hi)
    lo, hi = rr.conjunto(b[1], b[-3], b[-2], b[-1], 3.0, (1,))
    assert lo <= 0.0 <= hi


def test_c_meses():
    assert rr.c_meses((1,)) == 2.0
    assert rr.c_meses((0, 1)) == 1.5
    with pytest.raises(ValueError):
        rr.c_meses((-1, 0))


def test_quiebre_y_veredicto_con_sorteos():
    rng = np.random.default_rng(0)
    n = 4000
    # efecto de -20 en el mes 1, pretendencia chica: resiste Mbar = 1
    b3, b2, b1 = (rng.normal(v, 0.3, n) for v in (-0.5, -1.0, -1.5))
    beta1 = rng.normal(-21.5, 1.0, n)
    q = rr.quiebre(beta1, b3, b2, b1, (1,))
    assert q >= 1.0
    assert rr.veredicto_rr(True, q) == rr.V_RR_RESISTE
    # el intervalo crece con Mbar
    anchos = [np.subtract(*rr.intervalo(beta1, b3, b2, b1, m, (1,))[::-1]) for m in rr.GRILLA_MBAR]
    assert all(a <= b + 1e-12 for a, b in zip(anchos, anchos[1:]))
    # sin efecto despues de restar b(-1): no resiste ni con Mbar = 0
    beta1_nulo = rng.normal(-1.5, 1.0, n)
    q0 = rr.quiebre(beta1_nulo, b3, b2, b1, (1,))
    assert q0 == 0.0
    assert rr.veredicto_rr(True, q0) == rr.V_RR_NO
    assert rr.veredicto_rr(False, 5.0) == rr.V_RR_SIN_DATO


def test_quiebre_parcial():
    rng = np.random.default_rng(1)
    n = 4000
    b3, b2, b1 = (rng.normal(v, 0.1, n) for v in (-2.0, -4.0, -6.0))   # m = 2
    beta1 = rng.normal(-6.0 - 4.0, 0.1, n)                               # efecto -4, cubre cero con 2 Mbar m = 4: Mbar ~ 1
    beta1 = beta1 + 2.0                                                  # efecto -2: quiebre ~ 0,5
    q = rr.quiebre(beta1, b3, b2, b1, (1,))
    assert 0.3 < q < 0.7
    assert rr.veredicto_rr(True, q) == rr.V_RR_PARCIAL


# ---- porcion F: ensamble de estimandos con sorteos inventados (sin warehouse) ----
def _sorteos(R=200, seed=1, l=-10.0, previos=(-1.0, -2.0, -3.0)):
    rng = np.random.default_rng(seed)
    lv = l + rng.normal(0, 1, R)
    pv = np.column_stack([p + rng.normal(0, 0.5, R) for p in previos])
    return lv, pv


def test_media_de_dos_meses_es_la_media_por_sorteo():
    a, b = np.array([1.0, 2.0, 3.0]), np.array([3.0, 4.0, 5.0])
    punto, vals = rr.media_meses([1.0, 3.0], [a, b])
    assert punto == 2.0
    assert np.allclose(vals, [2.0, 3.0, 4.0])


def test_un_sorteo_con_nan_se_descarta_y_se_cuenta():
    lv, pv = _sorteos(R=50)
    lv[3] = np.nan
    pv[7, 1] = np.nan
    e = rr.armar_estimando("D2", "tau_W(1)", (1,), -10.0, lv, (-1.0, -2.0, -3.0), pv, 100)
    assert e["descartados"] == 2 and e["sorteos"] == 48
    assert all(f[16] == 48 for f in e["filas"])
    assert len(e["filas"]) == len(rr.GRILLA_MBAR) + 1


def test_el_veredicto_sale_de_veredicto_rr_y_el_quiebre_infinito_va_como_null():
    lv, pv = _sorteos(R=200, l=-40.0, previos=(-0.1, -0.2, -0.3))
    e = rr.armar_estimando("D1", "ATT(1)", (1,), -40.0, lv, (-0.1, -0.2, -0.3), pv, 10)
    quiebre = e["filas"][-1]
    assert e["quiebre"] == float("inf")
    assert quiebre[8] is None and quiebre[17] == rr.MOTIVO_MAYOR
    assert quiebre[9] == rr.veredicto_rr(True, float("inf")) == rr.V_RR_RESISTE
    assert all(f[8] is None for f in e["filas"][:-1])


def test_el_veredicto_no_resiste_si_el_cero_esta_en_mbar_cero():
    lv, pv = _sorteos(R=200, l=0.0, previos=(0.0, 0.0, 0.0))
    e = rr.armar_estimando("D1", "ATT(1)", (1,), 0.0, lv, (0.0, 0.0, 0.0), pv, 10)
    assert e["quiebre"] == 0.0 and e["veredicto"] == rr.V_RR_NO


def test_sin_previos_es_sin_dato_y_no_publica_grilla():
    lv, pv = _sorteos(R=20)
    e = rr.armar_estimando("D2", "tau_W(1)", (1,), -10.0, lv, (float("nan"), -2.0, -3.0), pv, 10)
    assert e["veredicto"] == rr.V_RR_SIN_DATO and len(e["filas"]) == 1
    assert e["filas"][0][2] == "quiebre"


def test_la_grilla_del_ensamble_coincide_con_intervalo():
    lv, pv = _sorteos(R=100)
    e = rr.armar_estimando("D1", "ATT(1)", (0, 1), -10.0, lv, (-1.0, -2.0, -3.0), pv, 10)
    fila = e["filas"][4]
    iv = rr.intervalo(lv, pv[:, 0], pv[:, 1], pv[:, 2], rr.GRILLA_MBAR[4], (0, 1))
    assert (fila[6], fila[7]) == iv


def test_la_pagina_dice_la_regla_y_el_maximo_sin_cota():
    lv, pv = _sorteos(R=100)
    e = rr.armar_estimando("D1", "ATT(1)", (1,), -10.0, lv, (-1.0, -2.0, -3.0), pv, 10)
    txt = rr.pagina_cota_rr(e["filas"])
    assert "857d434" in txt and "no es lineal" in txt and "Lo que no dice" in txt
    assert "## E, ATT(1)" not in txt


def test_la_pagina_lleva_la_cota_de_e_cuando_existe_su_mart():
    lv, pv = _sorteos(R=100)
    e = rr.armar_estimando("D1", "ATT(1)", (1,), -10.0, lv, (-1.0, -2.0, -3.0), pv, 10)
    txt = rr.pagina_cota_rr(e["filas"], (0.3215, "resiste solo con Mbar menor que 1", "sin muestra"))
    assert "## E, ATT(1)" in txt and "Mbar de quiebre: 0,32" in txt and "«sin muestra»" in txt
