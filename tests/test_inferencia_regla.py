"""Holm, p normal y veredictos de pipeline.inferencia (la regla fijada antes de calcular)."""
import math

from pipeline import inferencia as inf


def test_holm_paso_a_paso():
    ajust, rech = inf.holm([0.01, 0.04, 0.03, 0.20])
    assert [round(a, 4) for a in ajust] == [0.04, 0.09, 0.09, 0.20]
    assert rech == [True, False, False, False]


def test_holm_monotono_y_recortado():
    ajust, _ = inf.holm([0.5, 0.6, 0.001])
    assert ajust[2] == 0.003 and ajust[0] == 1.0 and ajust[1] == 1.0


def test_p_normal():
    # IC simetrico de +-1,96 ee alrededor de 1,96 ee: p = 0,05
    assert math.isclose(inf.p_normal(1.959964, 0.0, 3.919928), 0.05, rel_tol=1e-4)
    assert inf.p_normal(None, 0, 1) == 1.0
    assert inf.p_normal(1.0, 2.0, 2.0) == 1.0
    assert inf.p_normal(float("nan"), 0, 1) == 1.0


def test_familia_fija():
    ids = [f[0] for f in inf.FAMILIA_CONFIRMATORIA]
    assert len(ids) == len(set(ids)) == 20   # 15 en la regla, mas D11c (ACLARACION 2), D13 (regla en causal_profundo), E2 (82d58c0), D14 (5002094) y R1 (0670d9c)


def test_veredicto_escala():
    b = {2.0: 80, 5.0: 40, 10.0: 12}
    assert inf.veredicto_escala({"D2": {2.0: True, 5.0: True, 10.0: False}}, b).startswith(inf.V_ESCALA_NO)
    assert "10 km" in inf.veredicto_escala({"D2": {2.0: True, 5.0: True, 10.0: False}}, b)
    assert inf.veredicto_escala({"D2": {2.0: True, 5.0: False, 10.0: False}}, b) == inf.V_ESCALA_SI.format("D2")
    assert inf.veredicto_escala({"D1": {2.0: True, 5.0: True, 10.0: True}}, {2.0: 80, 5.0: 40, 10.0: 31}) == inf.V_ESCALA_NO
    assert inf.veredicto_permutacion(0.01) == inf.V_PERM_SI and inf.veredicto_permutacion(0.05) == inf.V_PERM_NO
