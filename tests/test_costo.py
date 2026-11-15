import numpy as np
import pytest

from agente.ops import ErrorOperacion, conectar, ejecutar
from pipeline import costo
from pipeline.ingest import DATA
from tests.test_pipeline import prod_row, warehouse  # noqa: F401  (fixture)


def _sintetico(theta, n=800, amp=0.12, seed=7):
    rng = np.random.default_rng(seed)
    rumbo = rng.uniform(0, 180, n)
    km = rng.uniform(0.3, 1, n)
    edad = rng.uniform(6, 60, n)
    caida = 0.2 + 0.1 * km - 0.03 * np.log(edad) + amp * np.cos(2 * np.radians(rumbo - theta)) + rng.normal(0, 0.15, n)
    return caida, np.column_stack([km, np.log(edad)]), rumbo


@pytest.mark.parametrize("theta", [70.0, 5.0, 150.0])
def test_axis_fit_recovers_known_theta(theta):
    caida, ctrl, rumbo = _sintetico(theta)
    t, amp, _ = costo.ajustar_eje(caida, ctrl, rumbo)
    assert abs(costo._dif_axial(t, theta)) < 4
    assert amp == pytest.approx(0.12, abs=0.03)


def test_axis_interval_covers_truth_and_permutation_detects_it():
    caida, ctrl, rumbo = _sintetico(70.0)
    clave = np.arange(len(rumbo)) // 4
    r = costo.eje_con_intervalo(caida, ctrl, rumbo, clave, reps=150, reps_perm=99)
    assert abs(costo._dif_axial(r["eje"], 70.0)) < 4
    assert abs(costo._dif_axial(70.0, r["eje"])) <= max(abs(costo._dif_axial(r["ic_bajo"], r["eje"])),
                                                         abs(costo._dif_axial(r["ic_alto"], r["eje"]))) + 1e-9
    assert r["p_perm"] <= 0.02
    # same seed, same answer
    assert costo.eje_con_intervalo(caida, ctrl, rumbo, clave, reps=150, reps_perm=99)["ic_bajo"] == r["ic_bajo"]


def test_isotropic_data_has_no_defined_axis():
    rng = np.random.default_rng(3)
    n = 500
    rumbo = rng.uniform(0, 180, n)
    caida = rng.normal(0.2, 0.2, n)
    ctrl = np.column_stack([rng.uniform(0.3, 1, n), np.log(rng.uniform(6, 60, n))])
    r = costo.eje_con_intervalo(caida, ctrl, rumbo, np.arange(n), reps=100, reps_perm=99)
    assert r["p_perm"] > 0.05


def test_axis_fit_with_group_fixed_effects_ignores_area_level():
    caida, ctrl, rumbo = _sintetico(110.0)
    grupo = (np.arange(len(rumbo)) % 3).astype(int)
    caida = caida + grupo * 5.0   # area level shifts must not move the axis
    t, _, _ = costo.ajustar_eje(caida, ctrl, rumbo, grupo)
    assert abs(costo._dif_axial(t, 110.0)) < 5


def test_op_rejects_bad_input_on_fixture_warehouse(warehouse):  # noqa: F811
    con = warehouse([prod_row(1, 2024, 9, 300)], [])
    for args in ({}, {"lat": -38.4}, {"pad": "p1", "lat": -38.4, "lon": -69.5}):
        with pytest.raises(ErrorOperacion):
            ejecutar(con, "costo_interferencia", args)
    # valid arguments but the cost model was never computed
    with pytest.raises(ErrorOperacion, match="pipeline.costo"):
        ejecutar(con, "costo_interferencia", {"pad": "p1"})


@pytest.mark.skipif(not (DATA / "warehouse.duckdb").exists(), reason="sin warehouse real")
def test_op_returns_a_number_on_real_warehouse():
    con = conectar()
    if con.execute("select count(*) from information_schema.tables where table_name = 'mart_costo_coef'").fetchall()[0][0] == 0:
        pytest.skip("falta correr pipeline.costo")
    pad = con.execute("select pad_id from mart_interferencia_diferida order by petroleo_diferido_bbl desc limit 1").fetchall()[0][0]
    r = ejecutar(con, "costo_interferencia", {"pad": pad})
    assert isinstance(r["valor"], float) and r["valor"] >= 0
    assert "bbl" in r["texto"] and len(r["factores"]) <= 3
    with pytest.raises(ErrorOperacion):
        ejecutar(con, "costo_interferencia", {"pad": "p0"})
    with pytest.raises(ErrorOperacion):
        ejecutar(con, "costo_interferencia", {})


def test_block_permutation_moves_pad_rumbos_together():
    rng = np.random.default_rng(1)
    clave = np.repeat(np.arange(30), 3)
    rumbo = np.repeat(rng.uniform(0, 180, 30), 3) + np.tile([0.0, 1.0, 2.0], 30)
    cl = costo._clusters(clave)
    p = costo._perm_bloques(np.random.default_rng(2), rumbo, cl)
    assert sorted(p) == pytest.approx(sorted(rumbo))                      # same multiset
    for c in cl:                                                          # each pad still has one block of 3 consecutive rumbos
        assert np.ptp(p[c]) == pytest.approx(2.0)
    assert not np.array_equal(p, rumbo)


def test_permutation_test_is_not_fooled_by_pad_clusters():
    """Rumbo and drop share a pad-level random effect but no axis exists: the p value must not be tiny."""
    ps = []
    for seed in range(8):
        rng = np.random.default_rng(100 + seed)
        n_pad, k = 40, 5
        clave = np.repeat(np.arange(n_pad), k)
        rumbo = np.repeat(rng.uniform(0, 180, n_pad), k) + rng.normal(0, 3, n_pad * k)
        caida = np.repeat(rng.normal(0, 0.3, n_pad), k) + rng.normal(0, 0.05, n_pad * k)
        ctrl = np.column_stack([rng.uniform(0.3, 1, n_pad * k), np.log(rng.uniform(6, 60, n_pad * k))])
        ps.append(costo.eje_con_intervalo(caida, ctrl, rumbo, clave, reps=30, reps_perm=199)["p_perm"])
    assert np.median(ps) > 0.15 and sum(p < 0.05 for p in ps) <= 2


@pytest.mark.parametrize("theta", [3.0, 177.0])
def test_axis_interval_wraps_around_north(theta):
    caida, ctrl, rumbo = _sintetico(theta, n=1200, amp=0.2)
    r = costo.eje_con_intervalo(caida, ctrl, rumbo, np.arange(len(rumbo)) // 3, reps=150, reps_perm=49)
    assert abs(costo._dif_axial(r["eje"], theta)) < 6
    assert r["ancho_ic"] < 30


def test_cross_fitted_axis_ignores_its_own_fold():
    rng = np.random.default_rng(5)
    n = 600
    d = {"km": rng.uniform(0.3, 1, n), "edad": rng.uniform(6, 60, n), "area": np.array(["A"] * n),
         "rumbo": rng.uniform(0, 180, n), "en_eje": np.ones(n, bool), "fold": np.arange(n) % costo.FOLDS_EJE}
    d["caida"] = 0.2 * np.cos(2 * np.radians(d["rumbo"] - 70)) + rng.normal(0, 0.1, n)
    i = np.arange(n)
    base = costo._ejes_cruzados(d, i, ["A"])
    assert np.all(np.abs(costo._dif_axial(base, 70.0)) < 10)
    d2 = dict(d, caida=d["caida"].copy())
    d2["caida"][d["fold"] == 0] = 5.0 * np.sin(2 * np.radians(d["rumbo"][d["fold"] == 0]))   # wreck fold 0 only
    cambiado = costo._ejes_cruzados(d2, i, ["A"])
    assert np.allclose(cambiado[d["fold"] == 0], base[d["fold"] == 0])      # fold 0's own axis never saw fold 0
    assert not np.allclose(cambiado[d["fold"] == 1], base[d["fold"] == 1])  # other folds did
