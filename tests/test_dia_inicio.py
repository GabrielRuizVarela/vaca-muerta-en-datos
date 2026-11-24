"""Pruebas de las funciones de veredicto de pipeline.dia_inicio, con numeros inventados (la regla se fijo antes de correr)."""
import datetime as dt

import duckdb
import numpy as np
import pytest

from pipeline import claims
from pipeline import dia_inicio as di


def _r(**kw) -> dict:
    r = {"n_cercanos": 2000, "n_controles": 17000, "bloques": 120, "n_tercios": (650, 700, 650),
         "pend": (-0.20, -0.30, -0.10), "eta2_operador": 0.02, "rho_edad": 0.03, "rho_base": -0.02,
         "control": (0.001, -0.01, 0.01), "falsas": {-12: (800, 0.0, -0.02, 0.02), -6: (900, 0.01, -0.01, 0.03)},
         "perm_media": 0.001, "perm_p": 0.005, "medianas_tercios": (0.9, 0.8, 0.7), "dif_tercios": (-0.2, -0.3, -0.1),
         "ajustada": (-0.15, -0.25, -0.05), "sin_operador": [("A", -0.04), ("B", -0.08)]}
    r.update(kw)
    return r


def test_caso_limpio_es_con_dosis():
    assert di.veredicto(_r()) == ("con dosis", [])


def test_sin_muestra_por_cada_minimo():
    assert di.veredicto(_r(n_cercanos=999))[0] == "sin muestra"
    assert di.veredicto(_r(bloques=29))[0] == "sin muestra"
    assert di.veredicto(_r(n_tercios=(650, 299, 650)))[0] == "sin muestra"
    assert di.veredicto(_r(n_controles=2999))[0] == "sin muestra"
    assert di.veredicto(_r(pend=(float("nan"), float("nan"), float("nan"))))[0] == "sin muestra"


def test_plana_y_opuesta():
    assert di.veredicto(_r(pend=(-0.05, -0.20, 0.10)))[0] == "plana"
    assert di.veredicto(_r(pend=(0.0, -0.01, 0.0)))[0] == "plana"      # el limite superior en cero incluye cero
    assert di.veredicto(_r(pend=(0.10, 0.02, 0.20)))[0] == "opuesta"


def test_no_equilibrado_nombra_lo_que_falla():
    v, m = di.veredicto(_r(eta2_operador=0.10))
    assert v == "no equilibrado" and m == ["operador del hijo"]
    v, m = di.veredicto(_r(rho_edad=-0.10, rho_base=0.11))
    assert v == "no equilibrado" and m == ["edad del padre", "caudal base"]
    assert di.veredicto(_r(rho_edad=0.099))[0] == "con dosis"


def test_placebos_rompen_solo_con_ic_fuera_de_cero_y_tamano():
    assert di.rompe(0.03, 0.01, 0.05) and di.rompe(-0.03, -0.05, -0.01)
    assert not di.rompe(0.02, 0.01, 0.03)              # excluye cero pero es chico (menos de 0,025)
    assert not di.rompe(0.04, -0.01, 0.09)             # grande pero el IC incluye cero
    assert not di.rompe(float("nan"), float("nan"), float("nan"))
    v, m = di.veredicto(_r(control=(0.04, 0.02, 0.06)))
    assert v == "no sobrevive a su placebo" and m == ["pozos de control"]
    v, m = di.veredicto(_r(falsas={-12: (800, -0.04, -0.07, -0.01), -6: (900, 0.0, -0.02, 0.02)}))
    assert v == "no sobrevive a su placebo" and m == ["fecha falsa -12"]
    # una fecha falsa con menos de MIN_FALSA eventos no rompe
    assert di.veredicto(_r(falsas={-12: (299, -0.04, -0.07, -0.01), -6: (900, 0.0, -0.02, 0.02)}))[0] == "con dosis"
    assert di.veredicto(_r(perm_media=-0.0125))[0] == "no sobrevive a su placebo"


def test_no_firme_dice_cual_condicion_falla():
    v, m = di.veredicto(_r(pend=(-0.04, -0.07, -0.03)))
    assert v == "no firme" and m == ["el limite superior no baja del umbral de dosis"]
    assert di.veredicto(_r(perm_p=0.05))[1] == ["p de dias sorteados"]
    assert di.veredicto(_r(medianas_tercios=(0.9, 0.7, 0.8)))[1] == ["tercio no monotono"]
    assert di.veredicto(_r(dif_tercios=(-0.2, -0.1, 0.01)))[1] == ["tercio no monotono"]
    assert di.veredicto(_r(ajustada=(-0.1, -0.2, 0.0)))[1] == ["pendiente ajustada"]
    assert di.veredicto(_r(sin_operador=[("A", -0.04), ("B", 0.01)]))[1] == ["sin el operador B"]


def test_umbral_de_dosis_es_estricto():
    assert di.veredicto(_r(pend=(-0.2, -0.3, -0.05)))[0] == "no firme"      # el limite superior igual al umbral no alcanza
    assert di.veredicto(_r(pend=(-0.2, -0.3, -0.0501)))[0] == "con dosis"


def test_p_bilateral_con_sorteos():
    assert di.p_bilateral(-0.2, [0.0] * 200) == 1 / 201
    assert di.p_bilateral(0.1, [0.1, -0.1] + [0.0] * 8) == 3 / 11


def test_colorado_y_lectura_conjunta():
    co = {"n_cercanos": 3000, "bloques": 60, "n_tercios": (900, 1000, 1100), "pend": (-0.1, -0.2, -0.01), "control": (0.0, -0.01, 0.01)}
    assert di.veredicto_colorado(co) == "se repite"
    assert di.veredicto_colorado(dict(co, pend=(-0.1, -0.2, 0.01))) == "no se repite"
    assert di.veredicto_colorado(dict(co, control=(0.05, 0.03, 0.07))) == "no se repite"
    assert di.veredicto_colorado(dict(co, n_cercanos=900)) == "sin muestra"
    assert di.veredicto_colorado(None) == "no corrido"
    assert di.lectura_conjunta("con dosis", "se repite") == "dosis en las dos cuencas"
    assert di.lectura_conjunta("con dosis", "no corrido") == "dosis en Vaca Muerta, Colorado no corrido"
    assert di.lectura_conjunta("plana", "se repite") == "Vaca Muerta plana, Colorado se repite"


# ------------------------------------------------------------------ implementacion (commit posterior al de la regla)
def test_f0_falso_ajusta_el_dia_al_ultimo_del_mes():
    # hijos de enero de 2021 (indice 12 desde M0 = 2000 * 12) con inicio los dias 31, 1 y 15; un mes despues es febrero, de 28 dias
    D = {"hijo_mes": np.array([12, 12, 12]), "hijo_dia": np.array([31, 1, 15])}
    f = di.f0_falso(D, 1)
    assert np.allclose(f, [1 / 28, 1.0, 14 / 28])


def test_fd_cuenta_hasta_el_fin_o_el_ultimo_dia_del_mes():
    assert di.fd_de(dt.date(2021, 3, 10), dt.date(2021, 3, 20)) == (20 - 10 + 1) / 31
    assert di.fd_de(dt.date(2021, 3, 10), dt.date(2021, 4, 5)) == (31 - 10 + 1) / 31
    assert np.isnan(di.fd_de(dt.date(2021, 3, 10), dt.date(2021, 3, 5)))
    assert np.isnan(di.fd_de(dt.date(2021, 3, 10), None))


def _eventos_sinteticos(pendiente: float, n: int = 600, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    f0 = rng.uniform(1 / 30, 1, n)
    return {"y": 1.0 + pendiente * f0 + rng.normal(0, 0.05, n), "f0": f0, "area": rng.integers(0, 3, n), "anio": rng.integers(0, 3, n),
            "clave": rng.integers(0, 60, n), "oper": rng.choice(["A", "B"], n), "edad": rng.uniform(6, 60, n),
            "base": rng.normal(1, 0.3, n)}


def test_la_pendiente_plantada_se_recupera_con_su_ic():
    e = _eventos_sinteticos(-0.3)
    est, lo, hi = di.pendiente_ic(e, 60, 1)
    assert abs(est + 0.3) < 0.03 and lo < est < hi and hi < 0
    est, lo, hi = di.pendiente_ic(_eventos_sinteticos(0.0), 60, 1)
    assert lo < 0 < hi


def test_spearman_eta2_y_rangos():
    assert di.rangos(np.array([10, 20, 20, 30])).tolist() == [1.0, 2.5, 2.5, 4.0]
    a = np.arange(10.0)
    assert di.spearman(a, a) == pytest.approx(1.0) and di.spearman(a, -a) == pytest.approx(-1.0)
    assert np.isnan(di.spearman(a, np.ones(10)))
    f0 = np.array([0.1, 0.1, 0.9, 0.9])
    assert abs(di.eta2(f0, np.array(["a", "a", "b", "b"])) - 1.0) < 1e-12
    assert di.eta2(f0, np.array(["a", "b", "a", "b"])) == 0.0


def test_terciles_ordena_y_separa():
    near = _eventos_sinteticos(-0.4, n=900)
    filas, dif = di.terciles(near, 40, 5)
    assert [f[0] for f in filas] == [1, 2, 3] and sum(f[1] for f in filas) == 900
    assert filas[0][2] > filas[2][2] and dif[0] < 0


# fila de cada (metrica, detalle) que la pagina lee, con numeros inventados
def _filas_inventadas() -> list[tuple]:
    f = [("pendiente", "principal", 2000, -0.27, -0.43, -0.16), ("pendiente", "ajustada", 2000, -0.25, -0.40, -0.13),
         ("pendiente", "control", 17000, -0.035, -0.07, -0.007), ("pendiente", "fd", 1990, -0.31, -0.46, -0.17),
         ("equilibrio", "eta2_operador", 2000, 0.022, 0.0096, 0.0799), ("equilibrio", "rho_edad", 2000, 0.0233, -0.0516, 0.1123),
         ("equilibrio", "rho_base", 2000, 0.0394, -0.0342, 0.1172),
         ("pendiente_sin_operador", "Vista", 1800, -0.256, -0.403, -0.137), ("pendiente_sin_operador", "YPF", 770, -0.245, -0.564, -0.003),
         ("pendiente_fecha_falsa", "-12", 1300, -0.0107, -0.1475, 0.138), ("pendiente_fecha_falsa", "-6", 1600, 0.1086, 0.0237, 0.207),
         ("sorteo", "media", 200, -0.0459, -0.167, 0.0559), ("sorteo", "p_bilateral", 200, 0.005, float("nan"), float("nan")),
         ("tercil", "1", 700, 0.686, 0.032, 0.4), ("tercil", "2", 650, 0.576, 0.419, 0.679), ("tercil", "3", 650, 0.486, 0.69, 1.0),
         ("tercil", "3 menos 1", 2000, -0.1999, -0.297, -0.0919), ("brecha", "exposicion cero", 2000, -0.0795, -0.1577, 0.0234),
         ("brecha", "previa (mes -1)", 2000, -0.0502, -0.0914, -0.0072), ("diagnostico", "parte autoasignada", 200, 0.0499, float("nan"), float("nan")),
         ("diagnostico", "sorteo sin autoasignacion", 200, -0.0341, -0.1284, 0.0719),
         ("diagnostico", "sorteo sin pad propio", 200, -0.0444, -0.1265, 0.054)]
    return f


def _warehouse_inventado(con, colorado: bool) -> None:
    ops = [("YPF", 1269, 0.5277, 0.13), ("Vista", 207, 0.5806, 0.1111)]
    filas = _filas_inventadas()
    if colorado:
        filas = [x for x in filas if x[1] != "fd"]
    v = [("colorado" if colorado else "", "se repite" if colorado else "no sobrevive a su placebo", "" if colorado else "pozos de control; fecha falsa -6",
          "coincide con la previa", 2000, 17000, 377, 91)]
    t = {"metricas": filas, "operadores": ops, "veredicto": v}
    di.escribir(con, t, "colorado" if colorado else "")


def test_la_pagina_y_sus_claims_se_corresponden_con_los_marts():
    con = duckdb.connect(":memory:")
    _warehouse_inventado(con, colorado=False)
    _warehouse_inventado(con, colorado=True)
    texto = di.pagina_dia_inicio(con)
    assert "**no sobrevive a su placebo**" in texto and "Veredicto de Colorado (posición 1 de 4): **se repite**" in texto
    assert texto.count("| Colorado: Cercanos, principal | ") == 1
    cs = [c for c in claims._claims_dia_inicio()]
    res = [claims.evaluar(c, texto, con) for c in cs]
    malos = [(r.claim.id, r.detalle) for r in res if r.estado == "FAIL"]
    assert not malos, malos[:5]
    # lo que no es opcional se verifico de verdad: filas de las dos cuencas, tablas, equilibrio, terciles, brechas y diagnostico
    ids = {r.claim.id for r in res if r.estado == "PASS"}
    for k in ("dia_vm_pend_principal_2", "dia_colorado_pend_principal_2", "dia_vm_eq_eta2_1", "dia_vm_tercil3_3", "dia_vm_brecha_previa_0",
              "dia_vm_diag_sin_pad_1", "dia_vm_oper0_eventos", "dia_vm_veredicto"):
        assert any(i.split("@")[0] == k for i in ids), k


def test_la_pagina_sin_colorado_dice_no_corrido():
    con = duckdb.connect(":memory:")
    _warehouse_inventado(con, colorado=False)
    texto = di.pagina_dia_inicio(con)
    assert "No corrido:" in texto and "Colorado: Cercanos" not in texto
    assert "Lectura conjunta con Colorado: Vaca Muerta no sobrevive a su placebo, Colorado no corrido." in texto


def test_especificacion_tiene_una_literal_mas_que_cifras_y_nombres_unicos():
    for cu in ("", "colorado"):
        spec = di.especificacion(cu)
        for clave, (lits, cifras) in spec.items():
            assert len(lits) == len(cifras) + 1, clave
        assert di.nombre_tabla("_veredicto", cu) == ("mart_dia_inicio_colorado_veredicto" if cu else "mart_dia_inicio_veredicto")
