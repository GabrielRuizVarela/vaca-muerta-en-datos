"""Incertidumbre predictiva del modelo de costo: validacion cruzada por pad hijo, calibracion e intervalo."""
import numpy as np
import pytest

from agente import ops
from agente.ops import conectar, ejecutar
from pipeline import costo
from pipeline.ingest import DATA

AREAS = ["A", "B", "C"]


def _filas(senal: bool, n: int = 1500, seed: int = 11) -> list[dict]:
    """Eventos sinteticos con la forma de EVENTOS_SQL. Con senal, y es lineal en km y caudal base mas ruido."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        km = float(rng.uniform(0.05, 1))
        base = float(rng.uniform(5, 50))
        rumbo = float(rng.uniform(0, 180))
        ruido = float(rng.normal(0, 4000))
        y = (1000 + 8000 * km + 400 * base + ruido) if senal else ruido
        idx = float(rng.uniform(0.3, 1.0))
        out.append({"padre": i, "mes_frac": "2020-01", "pad_id": f"p{i}", "area": AREAS[i % 3], "km_min": km,
                    "edad_meses": float(rng.uniform(6, 60)), "base_m3_d": base, "hijos_1km": float(rng.integers(1, 4)),
                    "rumbo_eje": rumbo, "parado": 0.0, "indice": idx,
                    "indice_control": idx + 0.2 * np.cos(2 * np.radians(rumbo - 70)) + float(rng.normal(0, 0.1)),
                    "petroleo_diferido_bbl": y, "arena_tn": float(rng.uniform(500, 3000)),
                    "etapas": float(rng.integers(20, 60)), "lat": -38.0, "pad_hijo": f"h{i // 4}"})
    return out


def test_cv_folds_are_disjoint_by_child_pad_and_cover_every_row():
    pads = [f"h{i // 4}" for i in range(400)] + ["h0", None, None]
    fold = costo.pliegues_cv(pads)
    assert len(fold) == len(pads) and set(fold) == set(range(costo.FOLDS_CV))
    por_pad: dict = {}
    for p, f in zip(pads, fold):
        por_pad.setdefault(str(p), set()).add(int(f))
    assert all(len(v) == 1 for v in por_pad.values())
    assert np.array_equal(fold, costo.pliegues_cv(pads))           # semilla fija


def test_predictions_cover_every_complete_row_and_hold_out_whole_pads():
    filas = _filas(True, n=600)
    filas[5]["arena_tn"] = None                                      # fila incompleta: fuera del modelo, igual que tabla_costo
    p = costo.predicciones_cv(filas, {"Cuenca": 70.0})
    assert len(p["y"]) == 599 and 5 not in set(p["fila"])
    assert not np.isnan(p["pred"]).any() and not np.isnan(p["sin_angulo"]).any()
    assert not np.isnan(p["media"]).any() and not np.isnan(p["media_area"]).any()


def test_oof_r2_close_to_truth_and_beats_the_mean_baseline_on_a_known_signal():
    filas = _filas(True)
    cv, calib, resid = costo.tabla_costo_cv(filas, {"Cuenca": 70.0})
    m = {r[0]: r for r in cv}
    y = np.array([f["petroleo_diferido_bbl"] for f in filas])
    var_ruido = 4000.0 ** 2
    verdad = 1 - var_ruido / y.var()
    assert abs(m["modelo"][4] - verdad) < 0.08
    assert m["modelo"][4] > m["media_entrenamiento"][4] + 0.4 and m["modelo"][4] > m["media_area"][4] + 0.4
    assert m["modelo"][2] < m["media_entrenamiento"][2] and m["modelo"][3] < m["media_entrenamiento"][3]
    assert abs(m["media_entrenamiento"][4]) < 0.05
    assert [c[0] for c in calib] == list(range(1, 11)) and sum(c[1] for c in calib) == len(y)
    obs = [c[3] for c in calib]
    assert obs == sorted(obs)                                        # con senal, mas prediccion es mas observado
    assert sorted({r[0] for r in resid}) == [1, 2, 3] and len(resid) == len(y)


def test_oof_r2_on_pure_noise_is_near_or_below_zero():
    cv, _calib, _resid = costo.tabla_costo_cv(_filas(False), {"Cuenca": 70.0})
    m = {r[0]: r for r in cv}
    assert m["modelo"][4] < 0.05
    assert m["modelo"][4] < m["media_entrenamiento"][4] + 0.02       # no mejora a la media


def test_interval_is_deterministic_ordered_and_clamped():
    pools = {1: np.array([-2.0, -1.0, 0.0, 1.0, 2.0]), 2: np.array([-3.0, 0.0, 3.0]), 3: np.array([-5.0, 0.0, 5.0, 9.0])}
    cortes = (10.0, 20.0)
    assert [costo.tercil_de(x, cortes) for x in (-5, 10, 10.5, 20, 21)] == [1, 1, 2, 2, 3]
    preds = [30.0, 15.0, 5.0, -4.0]
    a = costo.intervalo_suma(preds, pools, cortes)
    assert a == costo.intervalo_suma(preds, pools, cortes)
    lo, hi = a
    puntual = sum(max(p, 0.0) for p in preds)
    assert lo <= hi and lo <= puntual + 10 and hi >= puntual - 10
    assert costo.intervalo_suma([], pools, cortes) == (0.0, 0.0)
    assert costo.intervalo_suma([1.0, 2.0], pools, cortes)[0] >= 0.0   # cada padre acotado en 0
    mas = costo.intervalo_suma([p + 100 for p in preds], pools, cortes)
    assert mas[0] > lo and mas[1] > hi
    l1, h1 = costo.intervalo_padre(15.0, pools, cortes)
    assert l1 <= 15.0 + 3.0 and h1 >= 15.0 and costo.intervalo_padre(0.0, pools, cortes)[0] == 0.0


def _pad_top(con) -> str:
    return con.execute("select pad_id from mart_interferencia_diferida order by petroleo_diferido_bbl desc limit 1").fetchall()[0][0]


def _hay_cv(con) -> bool:
    return con.execute("select count(*) from information_schema.tables where table_name in ('mart_costo_cv', 'mart_costo_residuales')"
                       ).fetchall()[0][0] == 2


@pytest.mark.skipif(not (DATA / "warehouse.duckdb").exists(), reason="sin warehouse real")
def test_op_keeps_the_point_estimate_and_adds_the_interval_on_real_warehouse():
    con = conectar()
    if not _hay_cv(con):
        pytest.skip("falta correr pipeline.costo")
    pad = _pad_top(con)
    r = ejecutar(con, "costo_interferencia", {"pad": pad})
    assert isinstance(r["valor"], float) and r["valor"] >= 0
    # el valor puntual es la suma de lo que muestra cada fila (hasta 20 padres, redondeada a bbl)
    if len(r["filas"]) < 20:
        assert abs(r["valor"] - sum(f["esperado_bbl"] for f in r["filas"])) <= 0.5 * len(r["filas"]) + 1e-6
    lo, hi = r["intervalo_bbl"]["p10"], r["intervalo_bbl"]["p90"]
    assert 0 <= lo <= hi and lo <= r["valor"] <= hi
    assert "Intervalo de 80%" in r["texto"] and "R2" in r["calibracion"]
    assert all(f["p10_bbl"] <= f["esperado_bbl"] + 1 and f["p90_bbl"] >= f["esperado_bbl"] - 1 for f in r["filas"])
    assert ejecutar(con, "costo_interferencia", {"pad": pad})["intervalo_bbl"] == r["intervalo_bbl"]   # estable
    # valor registrado antes de agregar el intervalo, valido mientras mart_costo_coef sea el de esa corrida
    suma = con.execute("select md5(string_agg(cast(t as varchar), '|' order by cast(t as varchar))) from mart_costo_coef t").fetchall()[0][0]
    if suma == "7c8a5ec480432cd29a5235b2eb687c1b" and pad == "p164455" and r["fuente"]["datos_a"]:
        assert r["valor"] == pytest.approx(137267.38607096358, rel=1e-9)


@pytest.mark.skipif(not (DATA / "warehouse.duckdb").exists(), reason="sin warehouse real")
def test_op_still_works_when_the_cv_marts_are_missing(monkeypatch):
    con = conectar()
    if not _hay_cv(con):
        pytest.skip("falta correr pipeline.costo")
    pad = _pad_top(con)
    con_cv = ejecutar(con, "costo_interferencia", {"pad": pad})
    monkeypatch.setattr(ops, "_residuales_cv", lambda _con: None)
    r = ejecutar(con, "costo_interferencia", {"pad": pad})
    assert r["valor"] == con_cv["valor"] and r["intervalo_bbl"] is None
    assert "no está disponible" in r["texto"] and "No disponible" in r["calibracion"]
