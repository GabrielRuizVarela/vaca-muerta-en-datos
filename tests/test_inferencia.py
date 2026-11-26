"""Calculo de pipeline.inferencia: identidad con el analisis principal a 5 km, permutacion por estratos y Holm sobre la familia."""
from __future__ import annotations

import duckdb
import numpy as np
import pytest

from pipeline import inferencia as inf
from pipeline.ingest import DATA

WAREHOUSE = DATA / "warehouse.duckdb"


@pytest.mark.slow
def test_a_5_km_i1_da_los_numeros_de_mart_causal_veredicto_y_de_los_placebos():
    """El tamano por defecto de pipeline.causal es 5 km: con 5 km las cifras de I1 son las publicadas, a 1e-9."""
    if not WAREHOUSE.exists():
        pytest.skip("no hay warehouse")
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        if not all(con.execute("select count(*) from information_schema.tables where table_name = ?", [t]).fetchone()[0]
                   for t in ("mart_causal_veredicto", "mart_causal_placebo")):
            pytest.skip("faltan los marts causales")
        nb, filas = inf.escala_tamano(inf.preparar_datos(con), 5.0)
        ver = {d: (v, b, a, n) for d, v, b, a, n in con.execute(
            "select diseno, valor, ic_bajo, ic_alto, n_tratados from mart_causal_veredicto where diseno in ('D1','D2')").fetchall()}
        pla = {(d, p): (v, b, a, n) for d, p, v, b, a, n in con.execute(
            "select diseno, placebo, att, ic_bajo, ic_alto, n_tratados from mart_causal_placebo").fetchall()}
        n_bloques = con.execute("select n_bloques from mart_causal_veredicto where diseno = 'D1'").fetchone()[0]
    finally:
        con.close()
    assert nb == n_bloques
    comparadas = 0
    for diseno, clave, n_t, est, bajo, alto in filas:
        esperado = ver[diseno] if clave == "ATT" else pla.get((diseno, clave))
        if esperado is None:      # el placebo previo de D2 se llama igual en el mart
            continue
        assert n_t == esperado[3]
        for a, b in zip((est, bajo, alto), esperado[:3]):
            assert abs(a - b) < 1e-9
        comparadas += 1
    assert comparadas == 8


def test_las_permutaciones_conservan_los_tratados_de_cada_estrato():
    rng = np.random.default_rng(1)
    estrato = np.repeat(np.arange(6), [5, 8, 1, 12, 7, 3])
    trat = np.zeros(len(estrato), dtype=bool)
    for s, n_t in enumerate([2, 0, 1, 12, 3, 1]):       # el 2 y el 3 tienen una sola etiqueta; el 1, ningun tratado
        trat[np.flatnonzero(estrato == s)[:n_t]] = True
    cambio = False
    for _ in range(50):
        nueva = inf.etiquetas_permutadas(estrato, trat, rng)
        for s in range(6):
            assert nueva[estrato == s].sum() == trat[estrato == s].sum()
        cambio |= bool((nueva != trat).any())
    assert cambio


def test_att_w_usa_la_regla_de_celdas_de_d2():
    celda = np.array([0] * 7 + [1] * 5)
    valor = np.array([3.0, 5.0] + [1.0] * 5 + [9.0] + [0.0] * 4)
    trat = np.array([True, True] + [False] * 5 + [True] + [False] * 4)
    # la celda 1 tiene 4 controles (< 5) y no cuenta: ATT = media(3, 5) - 1 = 3 puntos de fraccion, x 100
    assert inf.att_w(celda, valor, trat, 2) == pytest.approx(300.0)


def test_la_permutacion_ve_un_efecto_plantado_y_no_ve_uno_ausente():
    rng = np.random.default_rng(7)
    n = 400
    celda = rng.integers(0, 4, n)
    estrato = rng.integers(0, 8, n)
    trat = rng.random(n) < 0.3
    ruido = rng.normal(0, 0.05, n)
    base = {"celda": celda, "estrato": estrato, "trat": trat, "n_celdas": 4}
    con_efecto = inf.permutacion(dict(base, valor=ruido + 0.3 * trat), reps=200, semilla=3)
    sin_efecto = inf.permutacion(dict(base, valor=ruido), reps=200, semilla=3)
    assert con_efecto["p"] == pytest.approx(1 / 201)
    assert sin_efecto["p"] > 0.05
    assert 0 < con_efecto["parte_mixtos"] <= 1.0
    assert inf.permutacion(dict(base, valor=ruido), reps=200, semilla=3)["p"] == sin_efecto["p"]


def _toy() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    cols = "diseno varchar, veredicto varchar, valor double, ic_bajo double, ic_alto double, n_tratados integer"
    con.execute(f"create table mart_causal_veredicto ({cols})")
    con.execute("insert into mart_causal_veredicto values ('D1', 'x', -25.0, -33.0, -17.0, 468), "
                "('D1b', 'sin muestra', -6.0, -36.0, 17.0, 43), ('D2', 'y', 13.0, 9.0, 20.0, 447)")
    con.execute(f"create table mart_causal_profundo_veredicto ({cols})")
    con.execute("insert into mart_causal_profundo_veredicto values ('D3', 'z', 4.8, -0.1, 12.3, 468), "
                "('D5', 'persiste', 10.9, 7.7, 15.0, 297)")
    con.execute("create table mart_causal_profundo_d3 (cantidad varchar, n_tratados integer, n_controles integer, valor double, "
                "ic_bajo double, ic_alto double, rompe boolean)")
    con.execute("insert into mart_causal_profundo_d3 values ('dA', 468, 2026, 4.8, -0.1, 12.3, null), "
                "('dA_pd', 434, 1877, 19.5, 12.8, 29.2, null)")
    con.execute("create table mart_causal_profundo_d7 (resultado varchar, n_tratados integer, valor double, ic_bajo double, "
                "ic_alto double, roto boolean, veredicto varchar)")
    con.execute("insert into mart_causal_profundo_d7 values ('dW', 1247, 9.0, 6.2, 12.1, false, 'sostiene')")
    con.execute("create table mart_causal_profundo_d9 as select * from mart_causal_profundo_d7 where false")
    con.execute("insert into mart_causal_profundo_d9 values ('dW', 200, 8.0, 5.0, 11.0, false, 'se repite'), "
                "('D9', 200, null, null, null, null, 'se repite')")
    return con


def test_holm_sobre_la_familia_en_un_warehouse_de_juguete():
    filas = inf.familia_holm(_toy(), 0.0049)
    k = len(inf.FAMILIA_CONFIRMATORIA)
    assert len(filas) == k and {f[13] for f in filas} == {k}
    por_id = {f[1]: f for f in filas}
    assert por_id["D1b"][3] == "sin muestra" and por_id["D1b"][9] == 1.0     # tiene IC y entra con p = 1
    assert por_id["D1"][3] == "leido" and por_id["D1"][11] is True
    assert por_id["D3"][11] is True                                          # dA_pd: su IC excluye cero
    assert por_id["D7"][2] == "mart_causal_profundo_d7:dW" and por_id["D7"][3] == "leido"
    assert por_id["D9"][2] == "mart_causal_profundo_d9:dW" and por_id["D9"][3] == "leido" and por_id["D9"][9] < 1.0
    assert por_id["D2"][14] == 0.0049 and por_id["D1"][14] is None
    ps = [f[9] for f in filas]
    ajust, rech = inf.holm(ps)
    assert [f[10] for f in filas] == ajust and [f[11] for f in filas] == rech
    # los p ajustados no bajan de los p ni de los de menor p
    assert all(a >= p for a, p in zip(ajust, ps))


def test_un_mart_o_una_fila_que_faltan_entran_con_p_igual_a_1():
    con = duckdb.connect()
    assert inf.leer_fila(con, "mart_que_no_existe", "D1") is None
    assert inf.p_de_fila(None) == ("sin fila o sin mart", 1.0)
    filas = inf.familia_holm(con, 0.5)
    assert len(filas) == len(inf.FAMILIA_CONFIRMATORIA)
    assert all(f[9] == 1.0 and f[10] == 1.0 and f[11] is False and f[3] == "sin fila o sin mart" for f in filas)
    assert inf.p_de_fila({"veredicto": "", "valor": 1.0, "ic_bajo": float("nan"), "ic_alto": 2.0})[0] == "sin IC"


def test_la_descomposicion_cuenta_una_prueba_por_fila():
    con = duckdb.connect()
    con.execute("create table mart_descomposicion_k (panel varchar, k integer, n_near integer, n_ctrl integer, "
                "mediana_cercano double, mediana_control double, brecha double, ic_bajo double, ic_alto double)")
    con.execute("insert into mart_descomposicion_k values ('a', 1, 1, 1, 0, 0, -5.0, -6.0, -4.0), ('a', 2, 1, 1, 0, 0, 1.0, -1.0, 3.0)")
    con.execute("create table mart_descomposicion_aditiva (variante varchar, k integer, brecha_total double, total_ic_bajo double, "
                "total_ic_alto double)")
    con.execute("insert into mart_descomposicion_aditiva values ('v', 0, 2.0, 1.0, 3.0)")
    con.execute("create table mart_descomposicion_distancia (banda varchar, control varchar, brecha double, ic_bajo double, ic_alto double)")
    filas = inf.descomposicion_holm(con)
    assert len(filas) == 3 and {f[13] for f in filas} == {3}
    assert sum(f[12] for f in filas) == 3 - 1


def test_la_fila_de_d3_en_la_familia_lee_dA_pd_y_su_veredicto_del_mart_de_veredictos():
    d3 = next(f for f in inf.familia_holm(_toy(), 0.5) if f[1] == "D3")
    assert d3[2] == "mart_causal_profundo_d3:dA_pd" and d3[3] == "leido"
    assert (d3[5], d3[6], d3[7], d3[8]) == (19.5, 12.8, 29.2, 434)           # valor, IC y tratados de dA_pd, no los de dA
    assert d3[4] == "z"                                                      # veredicto de mart_causal_profundo_veredicto:D3
    assert d3[9] < 0.001


def _celdas_toy(efecto: float, semilla: int = 11) -> dict:
    rng = np.random.default_rng(semilla)
    celda = np.repeat(np.arange(5), 30)
    trat = np.tile(np.r_[np.ones(6, dtype=bool), np.zeros(24, dtype=bool)], 5)
    valor = rng.normal(0, 0.05, len(celda)) + efecto * trat
    return {"celda": celda, "valor": valor, "trat": trat, "estrato": np.zeros(len(celda), dtype=int), "n_celdas": 5}


def test_i4_el_estrato_es_la_celda_y_cada_celda_conserva_sus_tratados():
    obs = _celdas_toy(0.0)
    i4 = inf.observaciones_celda(obs)
    assert (i4["estrato"] == obs["celda"]).all()
    rng = np.random.default_rng(5)
    for _ in range(30):
        nueva = inf.etiquetas_permutadas(i4["estrato"], i4["trat"], rng)
        assert [int(nueva[obs["celda"] == c].sum()) for c in range(5)] == [6] * 5
    assert inf.permutacion_celda(obs, reps=50)["parte_mixtos"] == 1.0


def test_i4_sin_efecto_da_un_p_que_no_es_chico_y_con_efecto_grande_da_el_minimo():
    sin = inf.permutacion_celda(_celdas_toy(0.0), reps=300)
    con = inf.permutacion_celda(_celdas_toy(0.5), reps=300)
    assert sin["p"] > 0.05
    assert con["p"] == pytest.approx(1 / 301)
    assert abs(np.mean(sin["perm"])) < 1.0                                    # centrada cerca de cero (pp)


def _con_pads(obs: dict, tam_pad: int) -> dict:
    """Asigna pads de `tam_pad` pozos consecutivos dentro de cada celda (los tratados juntos, los controles juntos)."""
    pad = np.zeros(len(obs["celda"]), dtype=int)
    for c in range(obs["n_celdas"]):
        for t in (True, False):
            idx = np.flatnonzero((obs["celda"] == c) & (obs["trat"] == t))
            pad[idx] = c * 1000 + int(t) * 500 + np.arange(len(idx)) // tam_pad
    return dict(obs, pad=pad)


def test_i5_cada_celda_conserva_sus_tratados_y_cada_estrato_sus_cantidades_por_cluster():
    obs = _con_pads(_celdas_toy(0.0), 3)
    # cluster mixto para que las cantidades por cluster no sean todas 0 o n
    obs["trat"][[0, 31]] = [False, True]
    cl = inf._clusters_pad(obs)
    rng = np.random.default_rng(3)
    for _ in range(30):
        nueva = inf.etiquetas_permutadas_pad(cl, rng)
        assert [int(nueva[obs["celda"] == c].sum()) for c in range(5)] == [int(obs["trat"][obs["celda"] == c].sum()) for c in range(5)]
        k_nuevo = np.bincount(cl["cod"], weights=nueva).astype(int)
        for e in np.unique(cl["estrato"]):
            m = cl["estrato"] == e
            assert sorted(k_nuevo[m]) == sorted(cl["k"][m])
            assert (k_nuevo[m] <= cl["tam"][m]).all()


def test_i5_sin_efecto_da_un_p_que_no_es_chico_y_con_efecto_grande_da_el_minimo():
    sin = inf.permutacion_pad(_con_pads(_celdas_toy(0.0), 3), reps=300)
    con = inf.permutacion_pad(_con_pads(_celdas_toy(0.5), 3), reps=300)
    assert sin["p"] > 0.05
    assert con["p"] == pytest.approx(1 / 301)
    assert sin["n_clusters"] == 5 * (2 + 8) and sin["parte_multipozo"] == 1.0


def test_i5_con_todos_los_clusters_de_un_pozo_es_el_esquema_de_i4():
    obs = _con_pads(_celdas_toy(0.0), 1)
    cl = inf._clusters_pad(obs)
    assert (cl["tam"] == 1).all()
    rng = np.random.default_rng(9)
    for _ in range(20):
        nueva = inf.etiquetas_permutadas_pad(cl, rng)
        assert [int(nueva[obs["celda"] == c].sum()) for c in range(5)] == [6] * 5
    i5 = inf.permutacion_pad(obs, reps=400, semilla=4)
    i4 = inf.permutacion_celda(obs, reps=400, semilla=4)
    assert i5["parte_multipozo"] == 0.0 and i5["parte_mixtos"] == 1.0 and i5["n_clusters"] == len(obs["celda"])
    assert i5["att_obs"] == pytest.approx(i4["att_obs"])
    assert np.mean(i5["perm"]) == pytest.approx(np.mean(i4["perm"]), abs=0.5)
    assert np.std(i5["perm"]) == pytest.approx(np.std(i4["perm"]), rel=0.3)
