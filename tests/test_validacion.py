import datetime as dt

import duckdb
import numpy as np
import pytest

from pipeline import costo, validacion

CORTE = dt.date(2019, 12, 1)


def _eventos(theta=70.0, n=900, amp=0.25, seed=5):
    rng = np.random.default_rng(seed)
    filas = []
    for i in range(n):
        km = float(rng.uniform(0.2, 1.1))
        rumbo = float(rng.uniform(0, 180))
        edad = float(rng.uniform(6, 60))
        caida = 0.2 + 0.1 * km + amp * np.cos(2 * np.radians(rumbo - theta)) + rng.normal(0, 0.15)
        f = {"padre": i, "mes_frac": dt.date(2016 + (i * 8) // n, 1 + i % 12, 1), "km_min": km,
             "edad_meses": edad, "rumbo_eje": rumbo, "indice": 0.8, "indice_control": 0.8 + float(caida),
             "pad_hijo": f"h{i // 3}", "area": ["A", "B", "C"][i % 3], "parado": bool(rng.random() < 0.1)}
        for j in range(4):
            f[f"y_{j}"] = float(caida + rng.normal(0, 0.1))
        f["y_parado"] = 1.0 if f["parado"] else 0.0
        filas.append(f)
    return filas


def test_outcome_runner_n_and_signed_difference():
    filas = _eventos()
    y = validacion._caida(filas)
    r = validacion.eje_resultado(filas, y, reps=60, reps_perm=49)
    assert r["n"] == len(filas)
    assert abs(float(costo._dif_axial(r["eje"], 70.0))) < 12
    y2 = y.copy()
    y2[:7] = np.nan
    assert validacion.eje_resultado(filas, y2, reps=20, reps_perm=9)["n"] == len(filas) - 7
    assert validacion.eje_resultado(filas[:10], y[:10], reps=10, reps_perm=9) is None
    t = validacion.tabla_resultados(filas, reps=30, reps_perm=19, corte=CORTE)
    base = t[0]
    assert base[0] == "principal" and base[8] == 0
    assert {r[0] for r in t} >= {"principal", "resultado", "anio", "holdout"}
    for r in t:
        assert -90 <= r[8] <= 90 and -90 <= r[9] <= 90
        assert r[8] == pytest.approx(float(costo._dif_axial(r[3], base[3])))
        assert r[9] == pytest.approx(float(costo._dif_axial(r[3], validacion.SHMAX)))


def test_year_groups_reach_minimum_and_cover_all_years():
    conteo = {2011: 1, 2012: 9, 2013: 12, 2014: 64, 2015: 180, 2016: 61, 2017: 46, 2018: 49, 2019: 62, 2020: 36,
              2021: 129, 2022: 198, 2023: 172, 2024: 224, 2025: 297, 2026: 194}
    g = validacion.agrupar_anios(conteo, 120)
    assert sorted(a for _n, ys in g for a in ys) == sorted(conteo)
    assert all(sum(conteo[a] for a in ys) >= 120 for _n, ys in g)
    assert g[0][0] == "2011 a 2015"


def test_holdout_split_respects_cutoff_and_is_disjoint():
    filas = _eventos()
    tr, te = validacion.dividir(filas, CORTE)
    assert tr and te
    assert len(tr) + len(te) == len(filas)
    assert max(f["mes_frac"] for f in tr) <= CORTE < min(f["mes_frac"] for f in te)
    assert not ({f["padre"] for f in tr} & {f["padre"] for f in te})
    # datetime y date dan lo mismo
    d = [dict(f, mes_frac=dt.datetime.combine(f["mes_frac"], dt.time())) for f in filas]
    tr2, te2 = validacion.dividir(d, CORTE)
    assert len(tr2) == len(tr) and len(te2) == len(te)


def _hold(filas):
    t = validacion.tabla_holdout(filas, corte=CORTE, reps=60)
    return {r[0]: r for r in t}


def test_train_axis_beats_wrong_axis_out_of_sample():
    filas = _eventos(theta=70.0)
    h = _hold(filas)
    tr = h["Eje de entrenamiento"]
    assert abs(float(costo._dif_axial(tr[3], 70.0))) < 15
    assert tr[4] > 0.05
    # un eje equivocado (a 45 grados del verdadero) explica menos
    ejes = np.array([tr[3], 70.0 + 45.0])
    te = [f for f in filas if f["mes_frac"] > CORTE]
    m = validacion.mejoras(validacion._caida(te), validacion._ctrl(te), validacion._codigos(te),
                           np.array([f["rumbo_eje"] for f in te]), ejes)
    assert m[0] > 5 * m[1]
    azar = next(v for k, v in h.items() if k.startswith("Eje aleatorio"))
    assert tr[4] > 1.5 * azar[4]
    prop = next(v for k, v in h.items() if k.startswith("Proporción"))
    assert prop[4] < 0.15


def test_no_true_axis_does_not_beat_random():
    filas = _eventos(amp=0.0, seed=9)
    h = _hold(filas)
    tr = h["Eje de entrenamiento"]
    assert tr[4] < 0.03
    prop = next(v for k, v in h.items() if k.startswith("Proporción"))
    assert prop[4] > 0.02
    azar = next(v for k, v in h.items() if k.startswith("Eje aleatorio"))
    assert tr[4] < azar[6] + 0.01


def test_improvement_is_a_fraction_and_matches_lstsq():
    filas = _eventos()
    y, ctrl = validacion._caida(filas), validacion._ctrl(filas)
    g, r = validacion._codigos(filas), np.array([f["rumbo_eje"] for f in filas])
    m = validacion.mejoras(y, ctrl, g, r, [70.0, 160.0, 10.0])
    assert np.all((m >= 0) & (m <= 1))
    # comparacion directa con minimos cuadrados con efectos fijos (columnas centradas por area)
    def cen(a):
        a = np.asarray(a, float)
        return a - np.array([a[g == k].mean(axis=0) for k in range(3)])[g]
    X0 = cen(ctrl)
    z = cen(np.cos(2 * np.radians(r - 70.0)))
    yc = cen(y)
    rss0 = float(np.sum((yc - X0 @ np.linalg.lstsq(X0, yc, rcond=None)[0]) ** 2))
    X1 = np.column_stack([X0, z])
    rss1 = float(np.sum((yc - X1 @ np.linalg.lstsq(X1, yc, rcond=None)[0]) ** 2))
    assert m[0] == pytest.approx((rss0 - rss1) / rss0, rel=1e-6)


def test_deterministic():
    filas = _eventos(n=600)
    a = validacion.tabla_resultados(filas, reps=20, reps_perm=9, corte=CORTE)
    b = validacion.tabla_resultados(filas, reps=20, reps_perm=9, corte=CORTE)
    assert a == b
    assert validacion.tabla_holdout(filas, corte=CORTE, reps=20) == validacion.tabla_holdout(filas, corte=CORTE, reps=20)


def test_page_has_no_dashes_or_nan():
    filas = _eventos()
    con = duckdb.connect(":memory:")
    costo._escribir(con, "mart_validacion_resultados", validacion.COLS_RES,
                    validacion.tabla_resultados(filas, reps=30, reps_perm=19, corte=CORTE))
    costo._escribir(con, "mart_validacion_holdout", validacion.COLS_HOLD,
                    validacion.tabla_holdout(filas, corte=CORTE, reps=30))
    txt = validacion.pagina_validacion(con)
    assert txt.startswith("# Validación del eje este-oeste")
    assert chr(0x2014) not in txt and chr(0x2013) not in txt
    assert "nan" not in txt.lower().replace("anual", "")
    assert "## Fuera de tiempo" in txt and "## Límites" in txt
    src = open(validacion.__file__, encoding="utf-8").read()
    assert chr(0x2014) not in src and chr(0x2013) not in src
