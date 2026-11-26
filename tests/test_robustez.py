import datetime as dt
import re

import duckdb
import numpy as np
import pytest

from pipeline import costo, robustez


def _eventos(theta=95.0, n=600, amp=0.15, seed=11):
    rng = np.random.default_rng(seed)
    filas = []
    for i in range(n):
        km = float(rng.uniform(0.2, 1.1))
        rumbo = float(rng.uniform(0, 180))
        edad = float(rng.uniform(6, 60))
        caida = 0.2 + 0.1 * km + amp * np.cos(2 * np.radians(rumbo - theta)) + rng.normal(0, 0.15)
        filas.append({"padre": i, "mes_frac": dt.date(2015 + (i * 11) // n, 1 + i % 12, 1), "km_min": km,
                      "edad_meses": edad, "rumbo_eje": rumbo, "indice": 0.8, "indice_control": 0.8 + float(caida),
                      "pad_hijo": f"h{i // 3}", "area": ["A", "B", "C"][i % 3],
                      "operador": "YPF" if i % 2 else "Otra", "parado": False})
    return filas


def test_subset_runner_returns_n_and_signed_circular_difference():
    filas = _eventos()
    esperado = sum(0.3 <= f["km_min"] < 1 for f in filas)
    r = robustez.eje_subconjunto(filas, reps=60, reps_perm=49)
    assert r["n"] == esperado
    assert abs(float(costo._dif_axial(r["eje"], 95.0))) < 12
    banda = robustez.eje_subconjunto(filas, 0.3, 0.6, reps=60, reps_perm=49)
    assert banda["n"] == sum(0.3 <= f["km_min"] < 0.6 for f in filas)
    assert robustez.eje_subconjunto(filas[:10], reps=10, reps_perm=9) is None
    for a, b in [(179.0, 1.0), (1.0, 179.0), (90.0, 0.0), (0.0, 90.0), (92.9, 67.5)]:
        d = float(costo._dif_axial(a, b))
        assert -90 <= d <= 90   # costo._dif_axial devuelve [-90, 90): el borde exacto cae en -90


def test_table_rows_have_consistent_differences():
    filas = _eventos()
    t = robustez.tabla_robustez_eje(filas, reps=40, reps_perm=29)
    base = t[0]
    assert base[0] == "completa" and base[8] == 0
    assert {r[0] for r in t} >= {"periodo", "operador", "area", "distancia", "recortada"}
    for r in t:
        assert -90 <= r[8] <= 90 and -90 <= r[9] <= 90
        assert r[8] == pytest.approx(float(costo._dif_axial(r[3], base[3])))
        assert r[9] == pytest.approx(float(costo._dif_axial(r[3], robustez.SHMAX)))


def test_determinism_same_seed_same_output():
    filas = _eventos(n=300)
    a = robustez.tabla_robustez_eje(filas, reps=30, reps_perm=19)
    b = robustez.tabla_robustez_eje(filas, reps=30, reps_perm=19)
    assert a == b


def _fila(sub, eje, lo, hi, p=0.01, grupo="area"):
    return {"grupo": grupo, "subconjunto": sub, "n": 100, "eje": eje, "ic_bajo": lo, "ic_alto": hi,
            "ancho_ic": float(costo._dif_axial(hi, eje) - costo._dif_axial(lo, eje)), "p_perm": p}


BASE = _fila("Muestra completa", 93.0, 70.0, 122.0, grupo="completa")


def test_ic_contiene_handles_wraparound():
    assert robustez.ic_contiene(175.0, 160.0, 15.0, 35.0, 5.0)
    assert not robustez.ic_contiene(175.0, 160.0, 15.0, 35.0, 90.0)
    assert robustez.ic_contiene(100.0, 10.0, 10.0, 180.0, 50.0)   # IC de 180 grados contiene todo


def test_verdict_all_contain():
    v = robustez.veredicto_eje([BASE, _fila("A", 95.0, 70.0, 120.0), _fila("B", 90.0, 65.0, 118.0)])
    assert "2 de 2 subconjuntos contiene el eje" in v
    assert "estable ante estos cortes" in v


def test_verdict_some_do_not_contain():
    v = robustez.veredicto_eje([BASE, _fila("A", 95.0, 70.0, 120.0), _fila("B", 40.0, 20.0, 60.0)])
    assert "1 de 2 subconjuntos contiene el eje" in v
    assert "no contiene el eje completo en: B" in v
    assert "no es estable ante todos los cortes" in v


def test_verdict_undefined_axis_is_not_overclaimed():
    ancho = _fila("Ancho", 80.0, 10.0, 150.0, p=0.4)
    v = robustez.veredicto_eje([BASE, ancho, _fila("A", 95.0, 70.0, 120.0)])
    assert "el eje no está definido ahí (Ancho)" in v
    assert "estable ante estos cortes" not in v
    solo = robustez.veredicto_eje([BASE, ancho])
    assert "Ningún subconjunto tiene un eje definido" in solo
    assert "Ancho" in solo   # p alto: aparece como corte sin evidencia


def test_cost_verdict_sign_and_zero():
    base = {"especificacion": "Muestra completa", "coef": -900.0, "ic_bajo": -1800.0, "ic_alto": 200.0,
            "mismo_signo": True, "ic_excluye_cero": False}
    otras = [dict(base, especificacion="X"), dict(base, especificacion="Y")]
    assert "Ninguna especificación permite afirmar" in robustez.veredicto_costo([base] + otras)
    otras[1] = dict(otras[1], ic_alto=-100.0, ic_excluye_cero=True)
    v = robustez.veredicto_costo([base] + otras)
    assert "excluye el cero en 1 (Y)" in v and "solo aparece en algunas" in v


def test_winsorize_clips_outcome_only():
    filas = [{"petroleo_diferido_bbl": float(v)} for v in range(101)] + [{"petroleo_diferido_bbl": None}]
    w = robustez._winsorizar(filas)
    assert max(f["petroleo_diferido_bbl"] for f in w[:-1]) == pytest.approx(99.0)
    assert min(f["petroleo_diferido_bbl"] for f in w[:-1]) == pytest.approx(1.0)
    assert w[-1]["petroleo_diferido_bbl"] is None
    assert filas[100]["petroleo_diferido_bbl"] == 100.0   # copia: no toca el original


def _con_marts():
    con = duckdb.connect(":memory:")
    ej = [("completa", "Muestra completa", 1734, 92.9, 69.9, 122.5, 52.6, 0.022, 0.0, 25.4),
          ("area", "Sin LOMA CAMPANA", 1040, 78.9, 29.6, 122.3, 92.7, 0.22, -14.0, 11.4),
          ("operador", "Padre YPF", 1147, 99.1, 70.7, 125.4, 54.7, 0.034, 6.2, 31.6)]
    co = [("Muestra completa", 2077, -962.8, -1840.7, 231.5, True, False),
          ("Sin padres parados", 1786, -908.7, -1896.6, 620.8, True, False)]
    costo._escribir(con, "mart_robustez_eje", robustez.COLS_EJE, ej)
    costo._escribir(con, "mart_robustez_costo", robustez.COLS_COSTO, co)
    return con


def test_page_has_no_long_dashes_and_no_nan():
    texto = robustez.pagina_robustez(_con_marts())
    assert chr(0x2014) not in texto and chr(0x2013) not in texto
    assert not re.search(r"\bnan\b", texto, re.IGNORECASE)
    assert texto.startswith("# Robustez del eje y del costo")
    assert "## Estabilidad del eje" in texto and "desvio_eje_10" in texto
    assert "93" in texto and "-963" in texto
