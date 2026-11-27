"""Validacion fijada de pipeline.replicacion_operadores con eventos sinteticos (sin warehouse).

Las tres pruebas son las del docstring del modulo: una brecha plantada se replica solo en su operador; un placebo de fechas con brecha
anula la replicacion; k y n cuentan a los operadores que no se pudieron medir.
"""
import numpy as np

from pipeline import replicacion_operadores as ro

REPS = 200
OPS = [f"OP{i}" for i in range(6)]
N_BANDA = 60   # eventos por banda y operador (cercanos y control), sobre el piso de 50


def _marco(k, brecha_por_op, semilla, controles_por_op=None):
    """Marco sintetico: por operador N_BANDA cercanos (banda 0) y `controles_por_op` controles (banda 2); indice ~ 1 + ruido sd 0.05."""
    rng = np.random.default_rng(semilla)
    ops, banda, idx, clave = [], [], [], []
    pad = 0
    for op in OPS:
        nc = (controles_por_op or {}).get(op, N_BANDA)
        for b, n in ((0, N_BANDA), (2, nc)):
            v = 1.0 + rng.normal(0, 0.05, n)
            if b == 0:
                v = v + brecha_por_op.get(op, 0.0)
            ops += [op] * n
            banda += [b] * n
            idx += list(v)
            clave += [f"pad{pad + j // 2}" for j in range(n)]
            pad += n
    return {"idx": {k: np.array(idx)}, "banda": np.array(banda), "clave": np.array(clave)}, np.array(ops)


def _medir(brecha_m, brecha_f=None, controles=None):
    m, om = _marco(1, brecha_m, 1, controles)
    mp, op_ = _marco(-1, {}, 2, controles)
    mf, of = _marco(1, brecha_f or {}, 3, controles)
    return ro.medir_operadores(m, mp, mf, om, op_, of, reps=REPS)


def _por_op(filas):
    return {f[0]: f for f in filas}


def test_brecha_plantada_se_replica_solo_en_su_operador():
    filas, (k, n, frase) = _medir({"OP0": ro.BRECHA_PLANTADA})
    r = _por_op(filas)
    assert n == len(OPS) and k == 1
    assert r["OP0"][11] is True and r["OP0"][12].startswith("se replica")
    assert r["OP0"][3] < -0.15 and r["OP0"][5] < 0
    for op in OPS[1:]:
        assert r[op][11] is False and r[op][12].startswith("no se replica")
    assert frase.startswith("Se replica en 1 de 6 operadores: OP0 (se replica")


def test_placebo_de_fechas_con_brecha_anula_la_replicacion():
    filas, (k, n, _) = _medir({"OP0": ro.BRECHA_PLANTADA, "OP1": ro.BRECHA_PLANTADA}, brecha_f={"OP1": ro.BRECHA_PLANTADA})
    r = _por_op(filas)
    assert r["OP1"][3] < -0.15 and r["OP1"][5] < 0   # la brecha del mes 1 pasa
    assert r["OP1"][8] < 0 and r["OP1"][9] is False   # pero el placebo tambien da brecha
    assert r["OP1"][11] is False and r["OP1"][12] == "no se replica: el placebo de fechas también da brecha"
    assert r["OP0"][11] is True and k == 1 and n == len(OPS)


def test_lectura_operador_casos():
    assert ro.lectura_operador(-0.2, -0.1, -0.01, 0.02, 60)[0] is True
    assert ro.lectura_operador(-0.2, -0.1, -0.01, -0.05, 60)[0] is False
    assert ro.lectura_operador(-0.2, 0.01, -0.01, 0.02, 60)[0] is False            # IC cruza el cero
    assert ro.lectura_operador(-0.2, -0.1, -0.25, 0.02, 60)[0] is False            # la previa es mayor
    for args in ((-0.2, -0.1, -0.01, 0.02, 49), (np.nan, -0.1, -0.01, 0.02, 60), (-0.2, np.nan, -0.01, 0.02, 60),
                 (-0.2, -0.1, np.nan, 0.02, 60), (-0.2, -0.1, -0.01, np.nan, 60)):
        se, valor, lec = ro.lectura_operador(*args)
        assert se is None and np.isnan(valor) and lec.startswith("no se pudo medir: ")
    for args in ((-0.2, -0.1, -0.01, 0.02, 60), (-0.2, 0.01, -0.01, 0.02, 60), (-0.2, -0.1, -0.01, 0.02, 10)):
        assert ro.lectura_operador(*args)[2].startswith(ro.LECTURAS_OP)


def test_k_y_n_cuentan_a_los_que_no_se_pudieron_medir():
    f = ro.lectura_familia_op([("A", True, "se replica: x"), ("B", None, "no se pudo medir: poco"), ("C", False, "no se replica: y")])
    assert (f["k"], f["n"]) == (1, 3)
    assert f["frase"] == "Se replica en 1 de 3 operadores: A (se replica: x); B (no se pudo medir: poco); C (no se replica: y)."
    assert ro.lectura_familia_op([])["frase"] == "Se replica en 0 de 0 operadores."
    # con eventos sinteticos: un operador con 20 controles se cuenta en n, no en k, con su motivo
    filas, (k, n, frase) = _medir({"OP0": ro.BRECHA_PLANTADA, "OP5": ro.BRECHA_PLANTADA}, controles={"OP5": 20})
    r = _por_op(filas)
    assert r["OP5"][11] is None and r["OP5"][12].startswith("no se pudo medir")
    assert (k, n) == (1, len(OPS))
    assert "OP5 (no se pudo medir" in frase


def test_pagina_dice_la_regla_y_no_inventa_cifras():
    filas, fam = _medir({"OP0": ro.BRECHA_PLANTADA})
    txt = ro.pagina_replicacion_operadores(filas, fam)
    assert fam[2] in txt and "de19052" in txt and "## Qué no prueba" in txt
    assert all(f"| {op} |" in txt for op in OPS)
