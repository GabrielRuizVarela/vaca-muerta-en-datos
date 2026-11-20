"""Pruebas de pipeline.riesgo: AUC, Brier, la matriz de diseño, el modelo y el veredicto.

Datos sinteticos: ningun test lee el warehouse.
"""
from __future__ import annotations

import datetime

import numpy as np
import pytest

import pipeline.riesgo as rg


# ------------------------------------------------------------------ datos sinteticos

def _bloque(n, rng, senal, fechas):
    """Un bloque de eventos sinteticos con las columnas crudas de cargar."""
    km = rng.uniform(0.05, 0.95, n)
    if senal:
        q = 1.0 / (1.0 + np.exp(4.0 * (km - 0.5)))
    else:
        q = np.full(n, 0.3)
    y = (rng.uniform(size=n) < q).astype(float)
    dif = np.where(y > 0, -0.45, 0.45)
    m_min = rng.uniform(0.0, 400.0, n)
    m_min[rng.uniform(size=n) < 0.2] = np.nan
    dif_azimut = rng.uniform(0.0, 90.0, n)
    dif_azimut[rng.uniform(size=n) < 0.2] = np.nan
    posicion = rng.choice(["costado", "mixto", "punta", None], size=n, p=[0.3, 0.3, 0.3, 0.1])
    largo_padre = rng.uniform(500.0, 3000.0, n)
    largo_padre[rng.uniform(size=n) < 0.2] = 0.0
    largo_hijo = rng.uniform(300.0, 2500.0, n)
    largo_hijo[rng.uniform(size=n) < 0.2] = np.nan
    return {
        "mes_frac": np.array(fechas, dtype=object),
        "km_min": km,
        "m_min": m_min,
        "dif_azimut": dif_azimut,
        "posicion": posicion,
        "edad_meses": rng.uniform(1.0, 120.0, n),
        "acum_m3": rng.uniform(1000.0, 50000.0, n),
        "largo_padre": largo_padre,
        "largo_hijo": largo_hijo,
        "arena_tn": rng.uniform(0.0, 500.0, n),
        "etapas": rng.integers(4, 40, n).astype(float),
        "base_m3_d": rng.uniform(1.0, 50.0, n),
        "hijos_1km": rng.integers(0, 4, n).astype(float),
        "operador": rng.choice(["op1", "op2"], size=n, p=[0.7, 0.3]),
        "area": np.array(["unica"] * n, dtype=object),
        "pad_hijo": np.array([f"pad{i // 2}" for i in range(n)], dtype=object),
        "pad_padre": np.array([f"padpad{i // 2}" for i in range(n)], dtype=object),
        "indice": dif,
        "indice_control": np.zeros(n),
    }


def _dataset(n_train=800, n_test=400, senal=True, semilla=7):
    """Un dataset con las dos ventanas y su resultado ya derivado."""
    rng = np.random.default_rng(semilla)
    meses_tr = [datetime.date(y, m, 1) for y in range(2016, 2023) for m in range(1, 13)]
    meses_te = [datetime.date(y, m, 1) for y in range(2023, 2025) for m in range(1, 13)]
    tr = _bloque(n_train, rng, senal, rng.choice(meses_tr, size=n_train))
    te = _bloque(n_test, rng, senal, rng.choice(meses_te, size=n_test))
    crudo = {k: np.concatenate([tr[k], te[k]]) for k in tr}
    return rg.derivar(crudo)


# ------------------------------------------------------------------ AUC y Brier

def test_auc_y_brier_a_mano():
    y = np.array([1, 1, 0, 0, 1, 0])
    p = np.array([0.9, 0.8, 0.7, 0.4, 0.4, 0.1])
    # a mano: los tres positivos (0,9; 0,8; 0,4) contra los tres negativos (0,7; 0,4; 0,1)
    # 3 + 3 + (0 + 0,5 + 1) = 7,5 sobre 9 pares
    esperado = 7.5 / 9.0
    assert rg.auc(y, p) == pytest.approx(esperado)
    br = float(np.mean((p - y) ** 2))
    assert rg.brier(y, p) == pytest.approx(br)
    assert rg.brier(y, p) == pytest.approx((0.01 + 0.04 + 0.49 + 0.16 + 0.36 + 0.01) / 6)


def test_auc_sin_una_clase_no_es_numero():
    assert rg.auc(np.array([1, 1]), np.array([0.2, 0.8])) is None


# ------------------------------------------------------------------ el modelo

def test_el_gradiente_es_cero_en_la_solucion():
    X = np.array([[-1.0], [0.0], [1.0], [2.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    w = rg.ajustar(X, y)
    g = rg.gradiente(X, y, w)
    assert np.max(np.abs(g)) < 1e-6


def test_untoy_separable_tiene_coeficiente_positivo():
    X = np.array([[0.0], [1.0], [2.0], [3.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    w = rg.ajustar(X, y)
    assert w[1] > 0
    p = rg.predecir(w, X)
    assert p[0] < p[-1]


def test_el_modelo_es_determinista():
    X = np.array([[-1.0], [0.0], [1.0], [2.0], [3.0]])
    y = np.array([0.0, 0.0, 1.0, 1.0, 1.0])
    assert np.array_equal(rg.ajustar(X, y), rg.ajustar(X, y))


# ------------------------------------------------------------------ la referencia

def test_referencia_usa_la_prevalencia_por_area_y_cae_a_la_global():
    area_tr = np.array(["a", "a", "b", "b"], dtype=object)
    y_tr = np.array([1.0, 1.0, 0.0, 0.0])
    area_te = np.array(["a", "b", "c"], dtype=object)
    ref = rg.referencia_area(area_tr, y_tr, area_te)
    assert ref[0] == pytest.approx(1.0)
    assert ref[1] == pytest.approx(0.0)
    assert ref[2] == pytest.approx(0.5)     # area sin entrenamiento: la prevalencia global


# ------------------------------------------------------------------ la matriz de diseño

def _matriz_de_prueba():
    """60 eventos: un nivel frecuente, dos raros, y un nivel que solo aparece en la prueba."""
    rng = np.random.default_rng(3)
    n = 60
    operadores = np.array(["A"] * 40 + ["B"] * 5 + ["C"] * 15, dtype=object)
    areas = np.array(["x"] * 55 + ["y"] * 5, dtype=object)
    m_min = rng.uniform(10.0, 100.0, n)
    m_min[0] = np.nan
    m_min[55] = np.nan
    crudo = {
        "mes_frac": np.array([datetime.date(2020, 1, 1)] * n, dtype=object),
        "km_min": rng.uniform(0.1, 0.9, n),
        "m_min": m_min,
        "dif_azimut": rng.uniform(0.0, 90.0, n),
        "posicion": np.array(["costado"] * 30 + [None] * 30, dtype=object),
        "edad_meses": rng.uniform(1.0, 100.0, n),
        "acum_m3": rng.uniform(100.0, 900.0, n),
        "largo_padre": np.full(n, 1000.0),
        "largo_hijo": np.full(n, 500.0),
        "arena_tn": rng.uniform(1.0, 9.0, n),
        "etapas": np.full(n, 7.0),                  # columna constante: queda en 0
        "base_m3_d": rng.uniform(1.0, 9.0, n),
        "hijos_1km": rng.integers(0, 3, n).astype(float),
        "operador": operadores,
        "area": areas,
        "pad_hijo": np.array([f"p{i}" for i in range(n)], dtype=object),
        "pad_padre": np.array([f"q{i}" for i in range(n)], dtype=object),
        "indice": np.zeros(n),
        "indice_control": np.zeros(n),
    }
    return rg.derivar(crudo)


def test_matriz_niveles_raros_y_desconocidos_van_a_otro():
    C = _matriz_de_prueba()
    i_tr = np.arange(50)
    i_te = np.arange(50, 60)
    Xtr, Xte, nombres = rg.matriz(C, ["operador", "area"], i_tr, i_te)
    assert "operador_A" in nombres
    assert "operador_otro" in nombres
    assert "operador_B" not in nombres
    j_a = nombres.index("operador_A")
    j_o = nombres.index("operador_otro")
    # el nivel frecuente tiene su propia indicadora y no aparece en la de otro
    assert Xtr[3, j_a] == pytest.approx(Xtr[10, j_a])
    assert Xtr[3, j_o] == pytest.approx(Xtr[10, j_o])
    # el nivel raro va a otro: las filas 40 a 49 (B y C) valen uno en la de otro
    assert Xtr[45, j_o] == pytest.approx(Xtr[48, j_o])
    assert Xtr[45, j_o] != pytest.approx(Xtr[3, j_o])
    assert Xtr[45, j_a] < Xtr[3, j_a]
    # un nivel que no aparece en el entrenamiento va a otro
    C2 = dict(C)
    C2["operador"] = np.array([("Z" if i == 50 else C["operador"][i]) for i in range(60)], dtype=object)
    Xtr2, Xte2, nombres2 = rg.matriz(C2, ["operador"], i_tr, i_te)
    j_o2 = nombres2.index("operador_otro")
    j_a2 = nombres2.index("operador_A")
    assert Xte2[0, j_o2] == pytest.approx(Xtr2[45, j_o2])
    assert Xte2[0, j_a2] == pytest.approx(Xtr2[45, j_a2])


def test_matriz_imputa_con_la_mediana_del_entrenamiento():
    C = _matriz_de_prueba()
    i_tr = np.arange(50)
    i_te = np.arange(50, 60)
    Xtr, Xte, nombres = rg.matriz(C, ["m_min"], i_tr, i_te)
    j = nombres.index("m_min")
    mid = C["m_min"][i_tr]
    med = float(np.nanmedian(mid))
    columna = np.where(np.isnan(mid), med, mid)
    esperado = (med - columna.mean()) / columna.std(ddof=0)
    # la fila 55 de la prueba tiene m_min faltante: se le pone la mediana del entrenamiento
    assert Xte[5, j] == pytest.approx(esperado)
    # la fila 0 del entrenamiento tambien faltaba
    assert Xtr[0, j] == pytest.approx(esperado)


def test_matriz_posicion_faltante_vale_cero():
    C = _matriz_de_prueba()
    i_tr = np.arange(50)
    i_te = np.arange(50, 60)
    Xtr, Xte, nombres = rg.matriz(C, ["posicion_costado"], i_tr, i_te)
    j = nombres.index("posicion_costado")
    columna = C["posicion_costado"][i_tr]
    esperado = (0.0 - columna.mean()) / columna.std(ddof=0)
    assert Xte[0, j] == pytest.approx(esperado)


def test_matriz_estandariza_y_deja_en_cero_las_constantes():
    C = _matriz_de_prueba()
    i_tr = np.arange(50)
    i_te = np.arange(50, 60)
    cols = list(rg.COLS_BASE) + ["operador", "area"]
    Xtr, Xte, nombres = rg.matriz(C, cols, i_tr, i_te)
    for j in range(len(nombres)):
        columna = Xtr[:, j]
        if np.allclose(columna, columna[0]):
            assert np.allclose(Xtr[:, j], 0.0)
            assert np.allclose(Xte[:, j], 0.0)
        else:
            assert columna.mean() == pytest.approx(0.0, abs=1e-9)
            assert columna.std(ddof=0) == pytest.approx(1.0, abs=1e-9)
    j_etapas = nombres.index("etapas")
    assert np.allclose(Xtr[:, j_etapas], 0.0)


# ------------------------------------------------------------------ el veredicto

def _y(n=500, pos=250):
    y = np.zeros(n)
    y[:pos] = 1.0
    return y


def test_veredicto_sin_muestra_por_pocos_eventos():
    assert rg.veredicto(rg.N_MIN_PRUEBA - 1, _y(), 0.90, 0.80, 0.20, 0.10) == "sin muestra"


def test_veredicto_sin_muestra_por_clase_faltante():
    assert rg.veredicto(500, np.ones(500), 0.90, 0.80, 0.20, 0.10) == "sin muestra"
    assert rg.veredicto(500, np.zeros(500), 0.90, 0.80, 0.20, 0.10) == "sin muestra"


def test_veredicto_predice_el_riesgo():
    v = rg.veredicto(500, _y(), 0.70, 0.60, 0.10, 0.05)
    assert v == "predice el riesgo"
    assert v in rg.VEREDICTOS


def test_veredicto_no_predice_por_auc_bajo():
    assert rg.veredicto(500, _y(), 0.60, 0.58, 0.10, 0.05) == "no predice el riesgo"


def test_veredicto_no_predice_por_ic_de_bss_que_cruza_cero():
    assert rg.veredicto(500, _y(), 0.70, 0.60, 0.10, -0.01) == "no predice el riesgo"


def test_veredicto_no_predice_por_limite_bajo_del_ic_de_auc():
    assert rg.veredicto(500, _y(), 0.70, rg.AUC_IC_BAJO, 0.10, 0.05) == "no predice el riesgo"


# ------------------------------------------------------------------ la calibracion

def test_calibracion_suma_los_eventos_y_los_primeros_grupos_agarran_el_resto():
    y = np.array([1.0, 0.0] * 12 + [1.0])
    p = np.linspace(0.0, 1.0, len(y))
    filas = rg.calibracion(y, p)
    assert len(filas) == rg.N_DECILES
    assert sum(f[1] for f in filas) == len(y)
    tamanos = [f[1] for f in filas]
    assert tamanos[0] == max(tamanos)
    assert tamanos[-1] == min(tamanos)


def test_calibracion_de_un_orden_perfecto_tiene_obs_media_creciente():
    n = 100
    p = np.linspace(0.0, 1.0, n)
    y = (p > 0.5).astype(float)
    filas = rg.calibracion(y, p)
    observadas = [f[3] for f in filas]
    assert observadas == sorted(observadas)
    assert observadas[0] == pytest.approx(0.0)
    assert observadas[-1] == pytest.approx(1.0)


# ------------------------------------------------------------------ el bootstrap

def _modelo_para_bootstrap():
    rng = np.random.default_rng(11)
    n = 120
    y = np.array([1.0] * 40 + [0.0] * 80)
    p = np.concatenate([rng.uniform(0.6, 0.9, 40), rng.uniform(0.1, 0.5, 80)])
    ref = np.full(n, 0.33)
    pads = np.array([f"pad{i % 20}" for i in range(n)], dtype=object)
    return {"y": y, "p": p, "ref": ref, "pad": pads}, pads


def test_bootstrap_es_determinista():
    modelos, pads = _modelo_para_bootstrap()
    a = rg.bootstrap({"principal": modelos}, pads, reps=100)
    b = rg.bootstrap({"principal": modelos}, pads, reps=100)
    assert a["principal"]["auc"] == b["principal"]["auc"]
    assert a["principal"]["bss"] == b["principal"]["bss"]
    assert a["principal"]["auc_ic"] == b["principal"]["auc_ic"]


def test_bootstrap_de_un_modelo_contra_su_mismo_da_cero():
    modelos, pads = _modelo_para_bootstrap()
    copia = dict(modelos)
    res = rg.bootstrap({"principal": modelos, "m2_sin_rama": copia}, pads, reps=100)
    dauc = [d for d in res["m2_sin_rama"]["dauc"] if d is not None]
    assert dauc
    assert max(abs(d) for d in dauc) == pytest.approx(0.0, abs=1e-12)


# ------------------------------------------------------------------ de punta a punta

def _flujo(C, reps=100):
    i_tr, i_te, i_fu = rg.ventanas(C)
    cols = list(rg.COLS_BASE) + ["operador", "area"]
    Xtr, Xte, nombres = rg.matriz(C, cols, i_tr, i_te)
    y_tr = C["golpe"][i_tr]
    y_te = C["golpe"][i_te]
    w = rg.ajustar(Xtr, y_tr)
    p = rg.predecir(w, Xte)
    ref = rg.referencia_area(C["area"][i_tr], y_tr, C["area"][i_te])
    a = rg.auc(y_te, p)
    br = rg.brier(y_te, p)
    br_ref = rg.brier(y_te, ref)
    hab = 1.0 - br / br_ref if br_ref > 0 else None
    pads = rg.codigos_pad(C["pad_hijo"][i_te])
    boot = rg.bootstrap({"principal": {"y": y_te, "p": p, "ref": ref, "pad": pads}}, pads, reps=reps)
    return rg.veredicto(len(y_te), y_te, a, boot["principal"]["auc_ic"][0], hab, boot["principal"]["bss_ic"][0])


def test_flujo_completo_con_senal_dice_predice_el_riesgo():
    C = _dataset(senal=True)
    assert _flujo(C) == "predice el riesgo"


def test_flujo_completo_con_ruido_dice_no_predice_el_riesgo():
    C = _dataset(senal=False)
    assert _flujo(C) == "no predice el riesgo"


# ------------------------------------------------------------------ la pagina

def _con_marts(senal: bool, con_cobertura: bool = True):
    import duckdb
    con = duckdb.connect(":memory:")
    rg.escribir(con, rg.calcular(_dataset(senal=senal), reps=60))
    if con_cobertura:
        con.execute("create table mart_trayectoria_cobertura (nivel varchar, anio integer, horizontales integer, horizontales_medidos integer)")
        con.execute("insert into mart_trayectoria_cobertura values ('hijo', 2018, 100, 90), ('hijo', 2022, 100, 80), "
                    "('hijo', 2024, 100, 40), ('hijo', 2025, 100, 25)")
    return con


def test_la_pagina_dice_la_palabra_guardada_y_la_nota_de_muestra():
    con = _con_marts(False)
    ver = con.execute("select veredicto from mart_riesgo_prueba").fetchone()[0]
    pagina = rg.pagina_riesgo(con)
    assert f"**{ver}**" in pagina
    assert rg.SHA_REGLA in pagina
    assert "el 40% de los de 2024" in pagina and "el 25% de los de 2025" in pagina
    assert "sobre todo de 2016 a 2023" in pagina


def test_la_pagina_sin_la_tabla_de_cobertura_no_inventa_porcentajes():
    pagina = rg.pagina_riesgo(_con_marts(False, con_cobertura=False))
    assert "de los de 2024" not in pagina


def test_la_pagina_con_senal_afirma_que_predice():
    pagina = rg.pagina_riesgo(_con_marts(True))
    assert "**predice el riesgo**" in pagina
    assert "excluye cero" in pagina


def test_la_pagina_no_tiene_guiones_largos_ni_cuatro_d():
    pagina = rg.pagina_riesgo(_con_marts(True))
    assert chr(0x2013) not in pagina and chr(0x2014) not in pagina
    assert "4D" not in pagina


def test_la_pagina_pide_correr_antes_de_escribir():
    import duckdb
    with pytest.raises(SystemExit):
        rg.pagina_riesgo(duckdb.connect(":memory:"))
