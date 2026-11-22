"""Pruebas de la regla de pipeline.causal_profundo: las funciones de veredicto y el calculo de D3.

Las funciones de veredicto se prueban sin datos; el calculo de D3 se prueba sobre paneles sinteticos chicos
(agua y petroleo por dia), sin el warehouse.
"""
from __future__ import annotations

from datetime import date

import duckdb
import numpy as np

from pipeline import causal
from pipeline import causal_profundo as cp
from pipeline.causal import V_D2_CIERRE, V_D2_SOSTIENE, V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA

OK = (1000, 100)


def test_d3_orden():
    assert cp.veredicto_d3(299, 100, False, (1, 2), (1, 2), (-2, -1), False) == V_SIN_MUESTRA
    assert cp.veredicto_d3(*OK, True, (1, 2), (1, 2), (-2, -1), False) == V_PLACEBO
    assert cp.veredicto_d3(*OK, False, (0.1, 9), (-1, 1), (-2, -1), False) == cp.V_D3_ENTRA
    assert cp.veredicto_d3(*OK, False, (-1, 9), (0.5, 9), (-2, -1), False) == cp.V_D3_ENTRA_PD
    assert cp.veredicto_d3(*OK, False, (-1, 9), (0.5, 9), (-2, -1), True) == V_NO_FIRME
    assert cp.veredicto_d3(*OK, False, (-3, 4), (-2, 4.9), (-20, -1), False) == cp.V_D3_PETROLEO
    assert cp.veredicto_d3(*OK, False, (-3, 6), (-2, 4), (-20, -1), False) == V_NO_FIRME
    assert cp.veredicto_d3(*OK, False, (-3, 4), (-2, 4), (-20, 0.5), False) == V_NO_FIRME


def test_d2_nombre():
    assert cp.d2_gana_nombre(cp.V_D3_ENTRA) and cp.d2_gana_nombre(cp.V_D3_ENTRA_PD)
    for v in (cp.V_D3_PETROLEO, V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA):
        assert not cp.d2_gana_nombre(v)


def test_gradiente():
    assert cp.veredicto_gradiente([200, 200, 200], [10, 8, 3], 1.0, 12.0) == cp.V_GRADIENTE
    assert cp.veredicto_gradiente([200, 200, 99], [10, 8, 3], 1.0, 12.0) == V_SIN_MUESTRA
    assert cp.veredicto_gradiente([200, 200, 200], [10, 11, 3], 1.0, 12.0) == V_NO_FIRME
    assert cp.veredicto_gradiente([200, 200, 200], [10, 8, 3], -1.0, 12.0) == cp.V_SIN_GRADIENTE
    assert cp.veredicto_gradiente([200, 200, 200], [10, 8, 3], 1.0, 12.0, cobertura=0.5) == cp.V_SIN_DATO


def test_forma():
    assert cp.veredicto_forma(199, 1, 2, 10) == V_SIN_MUESTRA
    assert cp.veredicto_forma(500, 0.5, 9, 10) == cp.V_PERSISTE
    assert cp.veredicto_forma(500, -2, 4.9, 10) == cp.V_CURA
    assert cp.veredicto_forma(500, -2, 5.1, 10) == V_NO_FIRME


def test_general():
    assert cp.veredicto_general({"A": 1.0, "B": 0.2}) == (cp.V_GENERAL, [])
    assert cp.veredicto_general({"A": 1.0, "B": -0.2}) == (cp.V_DEPENDE, ["B"])


def test_colorado():
    vm = cp.V_D3_ENTRA
    assert cp.veredicto_colorado(0.5, V_D2_SOSTIENE, vm, vm) == cp.V_SIN_DATO_AGUA
    assert cp.veredicto_colorado(0.9, V_SIN_MUESTRA, vm, vm) == V_SIN_MUESTRA
    assert cp.veredicto_colorado(0.9, V_D2_CIERRE, vm, vm) == cp.V_NO_REPITE
    assert cp.veredicto_colorado(0.9, V_NO_FIRME, vm, vm) == cp.V_NO_REPITE
    assert cp.veredicto_colorado(0.9, V_D2_SOSTIENE, vm, vm) == cp.V_REPITE
    assert cp.veredicto_colorado(0.9, V_D2_SOSTIENE, cp.V_D3_PETROLEO, vm) == cp.V_REPITE_PARTE


# ------------------------------------------------------------------ D3 sobre paneles sinteticos

T_MESES = 32
G = 12                        # columna del panel del mes de cohorte de los tratados
T0 = 2015 * 12                # indice de mes absoluto de la primera columna del panel
TASA_BASE = 10.0              # m3/d de petroleo de la base (para que el pozo sea tratado)
AGUA_BASE = 10.0              # m3/d de agua de la base
PETROLEO_BASE = 10.0          # m3/d de petroleo de la base
DIAS_MES = 30
N_TRATADOS = 2
N_CONTROLES = 6


def _fecha(c: int) -> date:
    """Fecha del mes de la columna c del panel."""
    a = T0 + c
    return date(a // 12, a % 12 + 1, 1)


def _panel(spec: list[dict]) -> dict:
    """Arma un D sintetico como lo hace tests.test_causal: series de tasa, primer mes y golpes por pozo."""
    n = len(spec)
    tasa = np.zeros((n, T_MESES))
    hay = np.zeros((n, T_MESES), dtype=bool)
    km_min = np.full((n, T_MESES), np.nan)
    km_falso = np.full((n, T_MESES), np.nan)
    hijo_min = np.full((n, T_MESES), -1, dtype=np.int64)
    primer = np.full(n, T0, dtype=np.int64)
    operador = ["OP1"] * n
    for i, s in enumerate(spec):
        tasa[i, :] = s.get("tasa", TASA_BASE)
        hay[i, :] = True
        for mes, km in s.get("golpes", {}).items():
            km_min[i, mes] = km
            hijo_min[i, mes] = 1000 + i
            if causal.KM_FALSO_MIN <= km < causal.KM_FALSO_MAX:
                km_falso[i, mes] = km
    w = np.zeros((n, T_MESES))
    tef = np.ones((n, T_MESES))
    tasa_pd = np.zeros((n, T_MESES))
    return causal._armar(np.arange(n), operador, np.zeros(n), np.zeros(n), primer, np.arange(n), T0,
                         T0 + T_MESES - 1, tasa, w, tef, tasa_pd, hay, km_min, km_falso, hijo_min, {})


def _volumenes(agua_efecto: float = 0.0, petroleo_efecto: float = 0.0):
    """D sintetico con volumenes: dos tratados cambian en los meses G y G + 1 y seis controles no cambian.

    El agua y el petroleo estan en m3/dia calendario y los meses con cambio son los de la ventana de D3."""
    spec = [{"golpes": {G: 0.5}} for _ in range(N_TRATADOS)]
    spec += [{"golpes": {20: 0.5}} for _ in range(N_CONTROLES)]
    D = _panel(spec)
    filas = []
    for i in range(N_TRATADOS + N_CONTROLES):
        tratado = i < N_TRATADOS
        for c in range(T_MESES):
            agua = AGUA_BASE
            pet = PETROLEO_BASE
            if tratado and c in (G, G + 1):
                agua += agua_efecto
                pet += petroleo_efecto
            filas.append((i, _fecha(c), pet * DIAS_MES, agua * DIAS_MES, float(DIAS_MES), DIAS_MES))
    con = duckdb.connect(":memory:")
    con.execute("create table fct_produccion (pozo_id integer, mes date, petroleo_m3 double, agua_m3 double, "
                "dias_efectivos double, dias_mes bigint)")
    con.executemany("insert into fct_produccion values (?, ?, ?, ?, ?, ?)", filas)
    D.update(cp.cargar_volumenes(con, D))
    D["bases"] = cp.preparar_bases(D)
    return D, con


def _celda(D: dict) -> list[dict]:
    """La celda (g, grupo de edad) de los tratados y controles del ejemplo."""
    cel = [c for c in causal.celdas(D, causal.cohortes(D), causal.H_CORTO) if c["g"] == T0 + G]
    assert len(cel) == 1
    return cel


def _atts(D: dict, cel: list[dict]) -> tuple[float, float, float]:
    """ATT de dA, de dO y de dL en las celdas dadas, con pesos planos (sin ruido de bootstrap)."""
    W = np.ones((2, D["n"]))
    vt_a, vc_a = cp.valores_volumen(D, cel, D["A"], D["bases"]["A"], cp.VENTANA_D3)
    vt_o, vc_o = cp.valores_volumen(D, cel, D["O"], D["bases"]["O"], cp.VENTANA_D3)
    a = float(cp.estimar_valores(D, cel, W, vt_a, vc_a)["est"])
    o = float(cp.estimar_valores(D, cel, W, vt_o, vc_o)["est"])
    l = float(cp.estimar_valores(D, cel, W, cp._suma(vt_a, vt_o), cp._suma(vc_a, vc_o))["est"])
    return a, o, l


def test_agua_que_entra_sube_dA_y_deja_el_petroleo_plano():
    """Con el agua plantada arriba y el petroleo plano, dA da positivo y dO queda en cero."""
    D, con = _volumenes(agua_efecto=30.0)
    try:
        a, o, _ = _atts(D, _celda(D))
    finally:
        con.close()
    # agua de 10 a 40 m3/d sobre un liquido base de 20 m3/d: 150 puntos del liquido base
    assert abs(a - 150.0) < 1e-6, f"dA dio {a}"
    assert abs(o) < 1e-9, f"dO dio {o}"


def test_petroleo_que_sale_baja_dO_y_deja_el_agua_plana():
    """Con el petroleo plantado abajo y el agua plana, dO da negativo y dA queda en cero."""
    D, con = _volumenes(petroleo_efecto=-5.0)
    try:
        a, o, _ = _atts(D, _celda(D))
    finally:
        con.close()
    # petroleo de 10 a 5 m3/d sobre un liquido base de 20 m3/d: -25 puntos del liquido base
    assert abs(o - (-25.0)) < 1e-6, f"dO dio {o}"
    assert abs(a) < 1e-9, f"dA dio {a}"


def test_dA_mas_dO_es_dL():
    """El cambio del liquido es la suma del cambio del agua y del petroleo."""
    D, con = _volumenes(agua_efecto=30.0, petroleo_efecto=-5.0)
    try:
        a, o, l = _atts(D, _celda(D))
    finally:
        con.close()
    assert abs(l - (a + o)) < 1e-9, f"dL dio {l} y dA + dO dio {a + o}"


def test_el_recorte_de_dA_es_el_de_TOPE_D3():
    """Una suba de agua enorme se recorta en TOPE_D3 puntos del liquido base."""
    D, con = _volumenes(agua_efecto=200.0)
    try:
        a, _, _ = _atts(D, _celda(D))
    finally:
        con.close()
    assert abs(a - 100.0 * cp.TOPE_D3) < 1e-6, f"dA dio {a}"


# ---- D4: pesos extendidos y celdas por mascara

def test_extender_pesos_copia_el_bloque_y_marca_al_solitario():
    D = {"bloque": np.array([10, 10, 10, 20, 30])}
    W = np.zeros((3, 5))
    W[:, 0] = [1, 2, 3]
    W[:, 3] = [4, 5, 6]
    W_ext, fuera = cp.extender_pesos(D, W, np.array([0, 3]))
    assert np.array_equal(W_ext[:, 0], [1, 2, 3])        # el del universo conserva su columna
    assert np.array_equal(W_ext[:, 3], [4, 5, 6])
    assert np.array_equal(W_ext[:, 1], [1, 2, 3])        # copia a su companero de bloque
    assert np.array_equal(W_ext[:, 2], [1, 2, 3])
    assert np.array_equal(W_ext[:, 4], [0, 0, 0])        # bloque solitario fuera del universo
    assert fuera.tolist() == [False, False, False, False, True]
    assert W[:, 1].sum() == 0                            # no toca la entrada


def _celda_d4(tratados, controles, g=100):
    tratados, controles = np.array(tratados), np.array(controles)
    return {"g": g, "grupo": 0, "tratados": tratados, "controles": controles,
            "base_t": tratados * 10.0, "base_c": controles * 10.0}


def test_celdas_por_mascara_filtra_tratados_y_alinea_bases():
    cel = [_celda_d4([1, 2, 3], [10, 11, 12, 13, 14]), _celda_d4([4], [10, 11, 12, 13, 14], g=101)]
    out = cp.celdas_por_mascara(cel, lambda ce: ce["tratados"] % 2 == 1)
    assert len(out) == 1                                  # la segunda se queda sin tratados
    assert out[0]["tratados"].tolist() == [1, 3]
    assert out[0]["base_t"].tolist() == [10.0, 30.0]
    assert out[0]["controles"].tolist() == [10, 11, 12, 13, 14]
    assert cel[0]["tratados"].tolist() == [1, 2, 3]       # no modifica la entrada


def test_celdas_por_mascara_saca_los_pozos_fuera_y_descarta_celdas_con_pocos_controles():
    cel = [_celda_d4([1, 2], [10, 11, 12, 13, 14]), _celda_d4([3], [10, 11, 12, 13, 14], g=101)]
    fuera = np.zeros(20, dtype=bool)
    fuera[[2, 14]] = True
    out = cp.celdas_por_mascara(cel, lambda ce: np.ones(len(ce["tratados"]), dtype=bool), fuera)
    # el control 14 sale: quedan 4 controles (< MIN_CONTROLES_CELDA), se descartan las dos celdas
    assert out == []
    fuera = np.zeros(20, dtype=bool)
    fuera[2] = True
    out = cp.celdas_por_mascara(cel, lambda ce: np.ones(len(ce["tratados"]), dtype=bool), fuera)
    assert [ce["tratados"].tolist() for ce in out] == [[1], [3]]
    assert out[0]["base_t"].tolist() == [10.0]


def test_dw_mes_resta_la_base_y_da_nan_fuera_de_panel_o_sin_base():
    D = {"t0": 100, "T": 10, "w": np.arange(30, dtype=float).reshape(3, 10) / 100.0}
    D["w"][1, 5] = np.nan
    base = np.full((3, 10), 0.1)
    out = cp._dw_mes(D, np.array([0, 2]), 102, 3, base)           # columna 5
    assert np.allclose(out, [0.05 - 0.1, 0.25 - 0.1])
    assert np.isnan(cp._dw_mes(D, np.array([1]), 102, 3, base)).all()      # falta W
    assert np.isnan(cp._dw_mes(D, np.array([0]), 102, 20, base)).all()     # fuera del panel
    assert np.isnan(cp._dw_mes(D, np.array([0]), 102, -5, base)).all()
    base[0, 2] = np.nan
    assert np.isnan(cp._dw_mes(D, np.array([0]), 102, 1, base)).all()      # falta la base


def test_media_resultados_promedia_punto_y_sorteos_uno_a_uno():
    a = {"est": 2.0, "vals": np.array([1.0, 3.0, 5.0]), "n_tratados": 300}
    b = {"est": 4.0, "vals": np.array([3.0, 5.0, 7.0]), "n_tratados": 250}
    m = cp.media_resultados([a, b])
    assert m["est"] == 3.0
    assert m["vals"].tolist() == [2.0, 4.0, 6.0]
    assert m["n_tratados"] == 250
    assert m["ic_bajo"] <= 4.0 <= m["ic_alto"]


def test_periodo_etiqueta_por_anio_de_la_cohorte():
    assert cp._periodo(2018 * 12 + 11) == "hasta 2018"
    assert cp._periodo(2019 * 12) == "2019-2021"
    assert cp._periodo(2021 * 12 + 5) == "2019-2021"
    assert cp._periodo(2022 * 12) == "2022 en adelante"


def test_cada_veredicto_de_causal_profundo_lleva_su_marca():
    veredictos = {v for k, v in vars(cp).items() if k.startswith("V_") and isinstance(v, str)}
    assert veredictos - {causal.V_D2_SOSTIENE} == set(cp.MARCA)
    assert set(cp.MARCA.values()) <= {"●", "◐", "○"}
    con = duckdb.connect(":memory:")
    con.execute("create table mart_causal_profundo_veredicto (diseno varchar, veredicto varchar, valor double, "
                "ic_bajo double, ic_alto double, n_tratados integer, n_bloques integer)")
    for vd, vt, m in ((cp.V_SIN_GRADIENTE, cp.V_SIN_GRADIENTE, "○"), (cp.V_GRADIENTE, cp.V_GRADIENTE, "●"),
                      (V_NO_FIRME, cp.V_SIN_GRADIENTE, "◐"), (cp.V_GRADIENTE, V_SIN_MUESTRA, "◐")):
        con.execute("delete from mart_causal_profundo_veredicto")
        con.execute("insert into mart_causal_profundo_veredicto values ('D4_distancia', ?, 1, 0, 2, 300, 50), "
                    "('D4_tamano', ?, 1, 0, 2, 300, 50)", [vd, vt])
        assert cp.frase_d4(con).startswith(f"- {m} **Dosis (D4,")


def _marts_d56(con, v5: str, v6: str, sin_ypf_bajo: float) -> None:
    con.execute("create or replace table mart_causal_profundo_veredicto (diseno varchar, veredicto varchar, valor double, "
                "ic_bajo double, ic_alto double, n_tratados integer, n_bloques integer)")
    con.execute("insert into mart_causal_profundo_veredicto values ('D5', ?, 10, 7, 15, 300, 60), ('D6', ?, 7, ?, 18, 447, 89)",
                [v5, v6, sin_ypf_bajo])
    con.execute("create or replace table mart_causal_profundo_d5 (e integer, resultado varchar, n_tratados integer, "
                "n_controles integer, valor double, ic_bajo double, ic_alto double)")
    for e in cp.E_D5:
        lo = 1.0 if e >= 0 else -1.0
        con.execute("insert into mart_causal_profundo_d5 values (?, 'dW', 300, 1000, 5, ?, 9)", [e, lo])
    con.execute("insert into mart_causal_profundo_d5 values (null, 'dW_temprano', null, null, 11, null, null), "
                "(null, 'primer_mes_ic_sobre_cero', null, null, 0, null, null)")
    con.execute("create or replace table mart_causal_profundo_d6 (corte varchar, grupo varchar, n_tratados integer, "
                "n_controles integer, valor double, ic_bajo double, ic_alto double)")
    con.execute("insert into mart_causal_profundo_d6 values ('todos', 'todos', 447, 1900, 14, 9, 20), "
                "('operador', 'YPF', 255, 1100, 17, 11, 24), ('sin_operador', 'YPF', 129, 449, 7, ?, 18), "
                "('sin_operador', 'Vista', 397, 1600, 14, 9, 19)", [sin_ypf_bajo])


def test_d5_y_d6_se_dicen_tal_cual_en_causal_md():
    con = duckdb.connect(":memory:")
    assert cp.frase_d56(con) == [] and cp.frase_lectura_d56(con) is None
    _marts_d56(con, cp.V_PERSISTE, cp.V_DEPENDE, -0.6)
    d5, d6 = cp.frase_d56(con)
    assert d5.startswith("- ● **Forma en el tiempo (D5,") and "no se cura en 12 meses" in d5
    assert "desde el mes 0." in d5
    assert d6.startswith("- ◐ **Dónde se sostiene (D6,") and "depende de un operador: YPF.**" in d6
    assert "el dato no muestra la suba fuera de YPF" in d6 and "(Vista) la deja sobre cero" in d6
    lec = cp.frase_lectura_d56(con)
    assert "no se cura" in lec and "depende de YPF (D6)" in lec
    _marts_d56(con, V_NO_FIRME, cp.V_GENERAL, 1.0)
    d5, d6 = cp.frase_d56(con)
    assert "no se cura" not in d5 and d6.startswith("- ● ") and "YPF" not in d6
    assert cp.frase_lectura_d56(con) == "Esa suba, con reglas fijadas después en `causal_profundo.md`, se sostiene sin cada operador (D6)."


def test_cobertura_agua_cuenta_los_meses_base_de_cada_tratado():
    # dos tratados con g = 10 (base: meses 4 a 6); el pozo 1 no tiene agua en el mes 5
    D = {"t0": 0, "T": 20}
    ok = np.ones((3, 20), dtype=bool)
    ok[1, 5] = False
    cel = [{"tratados": np.array([0, 1]), "g": 10}, {"tratados": np.array([], dtype=np.int64), "g": 12}]
    assert abs(cp.cobertura_agua(D, cel, ok) - 5 / 6) < 1e-12
    # una base que cae fuera del panel no cuenta; sin ningun mes base da nan
    assert abs(cp.cobertura_agua(D, [{"tratados": np.array([2]), "g": 4}], ok) - 1.0) < 1e-12
    assert np.isnan(cp.cobertura_agua(D, [{"tratados": np.array([2]), "g": 30}], ok))


def _mart_d7(con, ver: str, cobertura: float, con_d2: bool = True) -> None:
    nan = float("nan")
    filas = [("cobertura_agua", 100, cobertura, nan, nan, False, ""), ("D7", 100, nan, nan, nan, False, ver)]
    if con_d2:
        filas += [("dW", 100, 9.0, 6.0, 12.0, False, V_D2_SOSTIENE),
                  ("placebo_previo_dW", 100, 0.4, -0.8, 1.6, False, ""),
                  ("placebo_cierre", 100, 2.6, 1.5, 3.7, False, ""),
                  ("dA", 100, 2.7, -1.0, 7.7, False, cp.V_D3_ENTRA_PD), ("dO", 100, -20.0, -25.0, -14.0, False, ""),
                  ("dA_pd", 100, 10.4, 5.3, 16.6, False, ""), ("placebo_previo_dA", 100, -1.0, -3.0, 0.9, False, ""),
                  ("placebo_previo_dA_pd", 100, -0.2, -2.0, 1.3, True, "")]
    con.execute("create or replace table mart_causal_profundo_d7 (resultado varchar, n_tratados int, valor double, "
                "ic_bajo double, ic_alto double, roto boolean, veredicto varchar)")
    con.executemany("insert into mart_causal_profundo_d7 values (?, ?, ?, ?, ?, ?, ?)", filas)


def test_d7_en_la_pagina_dice_el_veredicto_y_la_compuerta():
    con = duckdb.connect()
    assert "D7 no se corrió" in "\n".join(cp._seccion_d7(con, cp._filas_d7(con)))
    _mart_d7(con, cp.V_SIN_DATO_AGUA, 0.5, con_d2=False)
    texto = "\n".join(cp._seccion_d7(con, cp._filas_d7(con)))
    assert "50% de los meses base" in texto and "la regla pide 70%" in texto and "no se calcularon" in texto
    assert texto.rstrip().endswith(cp.TEXTO_D7[cp.V_SIN_DATO_AGUA]) and "○ **D7, Colorado: sin dato de agua.**" in texto
    con.execute("create table mart_causal_veredicto as select 'D2' as diseno, 13.8 as valor, 9.5 as ic_bajo, "
                "19.9 as ic_alto, 'sostiene' as veredicto")
    con.execute(f"create table mart_causal_profundo_veredicto as select 'D3' as diseno, '{cp.V_D3_ENTRA_PD}' as veredicto")
    _mart_d7(con, cp.V_REPITE, 1.0)
    texto = "\n".join(cp._seccion_d7(con, cp._filas_d7(con)))
    assert "● **D7, Colorado: se repite.**" in texto and "en Vaca Muerta, 13,8 (IC 95%: 9,5 a 19,9)" in texto
    assert f"D3 en Colorado: {cp.V_D3_ENTRA_PD}. En Vaca Muerta: {cp.V_D3_ENTRA_PD}." in texto
    assert "queda debajo de 50% del corte de D2, así que con la regla de D2 no rompe" in texto
    assert "del agua por día calendario, no rompe; del agua por día producido, rompe previo" in texto
