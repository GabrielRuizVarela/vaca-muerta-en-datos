"""Pruebas de pipeline.calendario_golpes: las funciones puras y una corrida de punta a punta."""
import calendar

import numpy as np
import pytest

from pipeline import calendario_golpes as cg
from pipeline import decision
from pipeline import golpes_mismo_mes as gm

N_MES = 340
MES_2023 = 276          # (2023 - 2000) * 12: enero de 2023
MES_2024 = 288          # enero de 2024
A0 = 10.0               # costo fijo inyectado por mes de golpe (dias de base)
B0 = 3.0                # costo por hijo inyectado (dias de base)


def _tabla(n_obs, n_opt, K, base=10.0) -> dict:
    """Una tabla de padres minima, como la que arma estadisticos_padre."""
    return {"n_obs": np.atleast_1d(np.asarray(n_obs, dtype=np.int64)),
            "K": np.atleast_1d(np.asarray(K, dtype=float)),
            "base": np.atleast_1d(np.asarray(base, dtype=float)),
            "n_opt": {1: np.atleast_1d(np.asarray(n_opt, dtype=np.int64))},
            "n_opt_gt6": {1: np.zeros(len(np.atleast_1d(np.asarray(n_obs))), dtype=np.int64)}}


# ------------------------------------------------------------------ optimizador

def test_el_calendario_optimo_agrupa_hasta_dos_deltas():
    meses, k = cg.calendario_optimo([0, 2, 4, 6], [1, 1, 1, 1], 1)
    assert list(meses) == [1, 5]
    assert list(k) == [2.0, 2.0]


def test_el_calendario_optimo_con_delta_3_une_todo_en_un_grupo():
    meses, k = cg.calendario_optimo([0, 2, 4, 6], [1, 2, 3, 4], 3)
    assert list(meses) == [3]
    assert list(k) == [10.0]


def test_el_calendario_optimo_de_un_solo_mes_no_se_mueve():
    meses, k = cg.calendario_optimo([7], [3], 3)
    assert list(meses) == [10]
    assert list(k) == [3.0]


def test_el_calendario_optimo_suma_los_k_de_sus_meses():
    meses, k = cg.calendario_optimo([0, 1, 10], [2, 3, 4], 2)
    assert list(meses) == [2, 12]
    assert list(k) == [5.0, 4.0]


# ------------------------------------------------------------------ los dos casos

def test_el_ajuste_fijo_recupera_el_costo_fijo_y_el_costo_por_hijo():
    k = np.array([1.0, 2.0, 3.0, 4.0])
    p = 10.0 + 3.0 * k
    aj = cg.ajuste_fijo(k, p)
    assert abs(aj["a"] - 10.0) < 1e-9
    assert abs(aj["b"] - 3.0) < 1e-9
    assert aj["acotado_b"] is False
    assert aj["acotado_a"] is False


def test_el_ajuste_fijo_acota_el_b_negativo_y_pone_a_en_la_media():
    k = np.array([1.0, 2.0, 3.0, 4.0])
    p = 10.0 - 2.0 * k
    aj = cg.ajuste_fijo(k, p)
    assert aj["b"] == 0.0
    assert aj["acotado_b"] is True
    assert aj["b_sin_acotar"] < 0
    assert abs(aj["a"] - float(np.mean(p))) < 1e-9


def test_el_ajuste_fijo_acota_el_a_negativo_en_cero():
    k = np.array([1.0, 2.0, 3.0])
    p = np.array([-5.0, -7.0, -9.0])
    aj = cg.ajuste_fijo(k, p)
    assert aj["a"] == 0.0
    assert aj["acotado_a"] is True


def test_el_ajuste_aditivo_recupera_c_y_se_acota_en_cero():
    k = np.array([1.0, 2.0, 3.0, 4.0])
    assert abs(cg.ajuste_aditivo(k, 4.0 * k) - 4.0) < 1e-9
    assert cg.ajuste_aditivo(k, -4.0 * k) == 0.0


# ------------------------------------------------------------------ puntaje

def test_el_caso_fijo_le_vence_al_aditivo_fuera_de_muestra():
    k = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    p = 10.0 + 3.0 * k
    sc = cg.puntuar(k, p, k, p)
    assert abs(sc["sk_fijo"] - 1.0) < 1e-9
    assert sc["d"] > 0
    assert abs(sc["ecm_m0"]) > 0


def test_el_caso_aditivo_le_vence_al_fijo_fuera_de_muestra():
    # Con P = 5k los dos casos encajan exacto (el fijo con a = 0), asi que el D es cero:
    k = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    p = 5.0 * k
    sc = cg.puntuar(k, p, k, p)
    assert abs(sc["sk_aditivo"] - 1.0) < 1e-9
    assert abs(sc["sk_fijo"] - 1.0) < 1e-9
    assert sc["d"] == 0.0
    # Con un mes de k = 0 el aditivo lo ignora y el fijo tiene que acomodar el intercepto: el aditivo gana.
    k_ent = np.array([0.0, 1.0, 2.0, 3.0])
    p_ent = np.array([5.0, 5.0, 10.0, 15.0])
    k_pru = np.array([1.0, 2.0, 3.0])
    sc = cg.puntuar(k_ent, p_ent, k_pru, 5.0 * k_pru)
    assert abs(sc["sk_aditivo"] - 1.0) < 1e-9
    assert sc["d"] < 0


# ------------------------------------------------------------------ arrepentimiento

def test_el_arrepentimiento_del_caso_aditivo_es_cero():
    tab = _tabla([3], [2], [7.0])
    dias, _ = cg.arrepentimiento_padres("aditivo", {"c": 2.5}, tab, np.array([0]), 1)
    assert list(dias) == [0.0]


def test_el_arrepentimiento_del_caso_fijo_es_a_por_menos_meses():
    tab = _tabla([3], [2], [7.0])
    params = {"a": 10.0, "b": 3.0}
    dias, _ = cg.arrepentimiento_padres("fijo_mas_hijo", params, tab, np.array([0]), 1)
    assert abs(float(dias[0]) - 10.0 * (3 - 2)) < 1e-9
    assert float(dias[0]) >= 0


def test_el_calendario_separado_cuesta_mas_que_el_observado_y_este_mas_que_el_optimo():
    params = {"a": 10.0, "b": 3.0}
    n_obs, n_opt, K = 3, 2, 7.0
    obs = cg.costo_calendario("fijo_mas_hijo", params, n_obs, K)
    opt = cg.costo_calendario("fijo_mas_hijo", params, n_opt, K)
    sep = cg.costo_calendario("fijo_mas_hijo", params, K, K)
    assert sep >= obs >= opt


# ------------------------------------------------------------------ dolares

def test_el_costo_en_dolares_coincide_con_decision():
    m3 = np.array([1000.0, 250.0])
    usd = cg._usd(m3, 60.0, 0.10, 12)
    esperado = float(np.sum([decision.valor_indicativo(x, 60.0, 0.10, 12)["costo_de_diferir"] for x in m3]))
    assert abs(usd - esperado) < 1e-9
    assert usd > 0


# ------------------------------------------------------------------ veredicto

def test_el_veredicto_sin_muestra():
    assert cg.veredicto(cg.N_ENTRENA_MIN - 1, 100, 10, 1000, 100, 0.5, 0.9, 1.0) == "sin muestra"
    assert cg.veredicto(1000, cg.PADS_ENTRENA_MIN - 1, 10, 1000, 100, 0.5, 0.9, 1.0) == "sin muestra"
    assert cg.veredicto(1000, 100, cg.K_ENTRENA_DISTINTOS - 1, 1000, 100, 0.5, 0.9, 1.0) == "sin muestra"
    assert cg.veredicto(1000, 100, 10, cg.N_PRUEBA_MIN - 1, 100, 0.5, 0.9, 1.0) == "sin muestra"
    assert cg.veredicto(1000, 100, 10, 1000, cg.PADS_PRUEBA_MIN - 1, 0.5, 0.9, 1.0) == "sin muestra"


def test_el_veredicto_costo_aditivo_cuando_el_ic_de_d_termina_abajo_de_cero():
    v = cg.veredicto(1000, 100, 10, 1000, 100, -0.5, -0.1, 1.0)
    assert v == "costo aditivo"


def test_el_veredicto_sostiene_con_d_y_el_arrepentimiento_por_encima_de_cero():
    v = cg.veredicto(1000, 100, 10, 1000, 100, 0.1, 0.5, 0.2)
    assert v == "sostiene"


def test_el_veredicto_no_firme():
    assert cg.veredicto(1000, 100, 10, 1000, 100, 0.1, 0.5, 0.0) == "no firme"
    assert cg.veredicto(1000, 100, 10, 1000, 100, -0.2, 0.5, 1.0) == "no firme"


# ------------------------------------------------------------------ bootstrap

def test_el_boot_mueve_el_pad_del_padre_entero():
    pads = np.array([0, 0, 1, 1, 2, 2, 2])
    sal = cg._boot_pads({"eventos": pads}, 20, 7, lambda draw: draw["eventos"])
    assert len(sal) == 20
    for filas in sal:
        assert len(filas) > 0
        for p in np.unique(pads[filas]):
            esperados = set(np.flatnonzero(pads == p).tolist())
            assert esperados <= set(filas.tolist())
            n_esperado = int((pads == p).sum())
            n_dibujado = int((pads[filas] == p).sum())
            assert n_dibujado % n_esperado == 0


# ------------------------------------------------------------------ punta a punta

def _sintetico(n_padres: int = 60, n_controles: int = 30, seed: int = 3) -> dict:
    """Un panel con golpes en 2023 y en 2024 a 2026, con el caudal base del padre por mes de golpe."""
    rng = np.random.default_rng(seed)
    hijo_mes, hijo_pad, ph, pp, km = [], [], [], [], []
    losses = []
    for i in range(n_padres):
        m1 = MES_2023 + int(rng.integers(0, 3))
        m2 = MES_2024 + int(rng.integers(0, 20))
        for mes, k in ((m1, 1 + int(rng.integers(0, 3))), (m2, 2 + int(rng.integers(0, 3)))):
            for _ in range(k):
                hijo_mes.append(mes)
                hijo_pad.append(i)
                ph.append(len(ph))
                pp.append(i)
                km.append(float(rng.uniform(0.3, 0.9)))
            losses.append((i, mes, k))
    for c in range(n_controles):
        mes = MES_2023 - 6 + (c * 5) % 60
        for _ in range(2):
            hijo_mes.append(mes)
            hijo_pad.append(10 ** 6 + c)
            ph.append(len(ph))
            pp.append(n_padres + c)
            km.append(float(rng.uniform(2.5, 4.5)))
    hijo_mes = np.asarray(hijo_mes, dtype=np.int64)
    n_wells = n_padres + n_controles
    t = np.arange(N_MES)
    tasa = np.full((n_wells, N_MES + 2 * gm.PAD), np.nan)
    for i in range(n_wells):
        tasa[i, gm.PAD:gm.PAD + N_MES] = 50.0 * np.exp(-0.001 * t)
    for i, mes, k in losses:
        base = float(50.0 * np.exp(-0.001 * mes))
        perdida = A0 + B0 * k
        for j in range(5):
            dias = calendar.monthrange(2000 + (mes + j) // 12, (mes + j) % 12 + 1)[1]
            tasa[i, gm.PAD + mes + j] -= base * perdida / 5.0 / dias
    D = {"hijo_id": np.arange(len(ph)) + 1000, "hijo_mes": hijo_mes,
         "hijo_anio": 2000 + hijo_mes // 12, "hijo_pad": np.asarray(hijo_pad, dtype=np.int64),
         "primer": np.full(n_wells, 60, dtype=np.int64), "area": np.array(["A"] * n_wells),
         "lat": np.full(n_wells, -38.5), "tasa": tasa, "par_hijo": np.asarray(ph, dtype=np.int64),
         "par_padre": np.asarray(pp, dtype=np.int64), "par_km": np.asarray(km, dtype=float),
         "par_rumbo": np.zeros(len(pp)), "n_mes": N_MES,
         "operador": np.array(["A", "B", "C", "D"])[rng.integers(0, 4, n_wells)],
         "pad_padre": np.arange(n_wells, dtype=np.int64)}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - 6
    return D


def test_el_calculo_de_punta_a_punta_publica_las_cuatro_tablas():
    D = _sintetico()
    t = cg.calcular(D, reps=5)
    assert set(t) == {"prueba", "k", "costo_k", "matriz"}
    p = {(f[0], f[1]): f for f in t["prueba"]}
    assert ("backtest", "d") in p
    assert p[("backtest", "d")][6] in cg.VEREDICTOS
    assert len(t["k"]) == len(gm.ETQ_GRUPO)
    assert len(t["matriz"]) > 0
    for f in t["prueba"]:
        assert len(f) == 7


def test_una_repeticion_que_toma_cada_pad_una_vez_da_la_estimacion_puntual(monkeypatch):
    """Un draw trae posiciones dentro de cada arreglo de pads, no indices de evento: con el draw identidad (cada fila una
    vez) el IC de D tiene que colapsar en la estimacion puntual; si se usaran las posiciones como indices de evento,
    se puntuarian otras filas."""
    def identidad(arrays, reps, semilla, fn):
        return [fn({n: np.arange(len(a)) for n, a in arrays.items()}) for _ in range(reps)]
    monkeypatch.setattr(cg, "_boot_pads", identidad)
    t = cg.calcular(_sintetico(), reps=3)
    p = {(f[0], f[1]): f for f in t["prueba"]}
    d = p[("backtest", "d")]
    assert d[2] is not None
    assert d[3] == pytest.approx(d[2]) and d[4] == pytest.approx(d[2])
    ar = p[("arrepentimiento", f"dias_fijo_mas_hijo_d{cg.DELTA_MESES}")]
    assert ar[3] == pytest.approx(ar[2]) and ar[4] == pytest.approx(ar[2])


def _con_marts():
    import duckdb
    con = duckdb.connect(":memory:")
    cg.escribir(con, cg.calcular(_sintetico(), reps=5))
    return con


def test_la_pagina_se_arma_desde_los_marts_con_sus_secciones_y_sin_rayas():
    con = _con_marts()
    pagina = cg.pagina_calendario_golpes(con)
    for titulo in ("## Lectura", "## Los dos casos de costo", "## Matriz de costo por cantidad de hijos", "## Backtest",
                   "## Arrepentimiento del calendario", "## Valor en dólares", "## Muestra", "## Regla fijada antes de correr",
                   "## Qué no prueba"):
        assert titulo in pagina
    assert "c71f3a50" in pagina
    assert "4D" not in pagina
    assert chr(0x2013) not in pagina and chr(0x2014) not in pagina


def test_la_pagina_dice_el_veredicto_de_la_tabla_y_rotula_sin_muestra_como_descriptivo():
    con = _con_marts()
    veredicto = con.execute("select veredicto from mart_calendario_prueba where prueba = 'backtest' and estadistico = 'd'").fetchone()[0]
    pagina = cg.pagina_calendario_golpes(con)
    assert f"Backtest: **{veredicto}**" in pagina
    if veredicto == "sin muestra":
        assert "descriptivas, no un resultado de la regla" in pagina


def test_la_pagina_de_la_grilla_tiene_las_18_celdas_del_arrepentimiento_en_dolares():
    con = _con_marts()
    pagina = cg.pagina_calendario_golpes(con)
    i = pagina.index("| Precio (USD por barril) |")
    filas = [f for f in pagina[i:].split("\n\n")[0].split("\n")[2:]]
    assert len(filas) == len(cg.GRILLA_PRECIOS) * len(cg.GRILLA_TASAS)
    assert all(f.count("|") == 6 for f in filas)


def test_la_pagina_dice_que_no_es_una_recomendacion_y_el_supuesto_de_b_acotado_en_cero():
    con = _con_marts()
    pagina = cg.pagina_calendario_golpes(con)
    assert "No es una recomendación al operador" in pagina
    assert "b acotado en 0, heredado de #83" in pagina
    veredicto = con.execute("select veredicto from mart_calendario_prueba where prueba = 'backtest' and estadistico = 'd'").fetchone()[0]
    if veredicto == "sin muestra":
        for titulo in ("## Arrepentimiento del calendario", "## Valor en dólares"):
            i = pagina.index(titulo)
            assert pagina[i:].split("\n\n")[1].startswith("Descriptivo, no una recomendación al operador")
