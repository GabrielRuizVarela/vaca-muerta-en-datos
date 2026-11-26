"""Pruebas del diseno causal (pipeline.causal) sobre paneles sinteticos chicos, sin el warehouse.

Se prueba lo que la regla fija: el ATT de una celda con un efecto plantado, la exclusion de los controles
invalidos (nunca tratados en el primario, golpe a 2 km dentro de la ventana), las funciones de umbral y las cotas
de Lee."""
from __future__ import annotations

import numpy as np

from pipeline import causal

T_MESES = 32
G = 12                      # mes de la cohorte de los tratados
TASA_BASE = 10.0            # m3/d de la base
TASA_EFECTO = 8.0           # m3/d del mes 1 de los tratados: un indice de 0,8, o sea -20 puntos


def _datos(spec: list[dict]) -> dict:
    """Arma un D sintetico: cada pozo tiene su serie de tasas, su primer mes y sus golpes (mes, km)."""
    n = len(spec)
    tasa = np.zeros((n, T_MESES))
    hay = np.zeros((n, T_MESES), dtype=bool)
    km_min = np.full((n, T_MESES), np.nan)
    km_falso = np.full((n, T_MESES), np.nan)
    hijo_min = np.full((n, T_MESES), -1, dtype=np.int64)
    primer = np.zeros(n, dtype=np.int64)
    operador = []
    for i, s in enumerate(spec):
        serie = list(s["tasa"])
        serie += [TASA_BASE] * (T_MESES - len(serie))
        tasa[i, :] = serie
        hay[i, :] = True
        primer[i] = s.get("primer", 0)
        operador.append(s.get("operador", "OP1"))
        for mes, km in s.get("golpes", {}).items():
            km_min[i, mes] = km
            hijo_min[i, mes] = 1000 + i
            if causal.KM_FALSO_MIN <= km < causal.KM_FALSO_MAX:
                km_falso[i, mes] = km
    w = np.zeros((n, T_MESES))
    tef = np.ones((n, T_MESES))
    tasa_pd = np.zeros((n, T_MESES))
    return causal._armar(np.arange(n), operador, np.zeros(n), np.zeros(n), primer, np.arange(n), 0, T_MESES - 1,
                         tasa, w, tef, tasa_pd, hay, km_min, km_falso, hijo_min, {})


def _tratado(efecto: float = TASA_EFECTO) -> dict:
    """Pozo tratado: golpe a 0,5 km en el mes de cohorte, base de 10 y el mes 1 con el efecto plantado."""
    serie = [TASA_BASE] * T_MESES
    serie[G + 1] = efecto
    return {"tasa": serie, "golpes": {G: 0.5}}


def _control(golpes: dict | None = None) -> dict:
    """Pozo control: sin efecto, con un golpe propio mas adelante (aun no tratado y alguna vez tratado)."""
    g = dict(golpes or {20: 0.5})
    return {"tasa": [TASA_BASE] * T_MESES, "golpes": g}


def _celda_de(D: dict, g: int) -> dict:
    """La celda (g, grupo de edad) de las cohortes del ejemplo."""
    cel = [c for c in causal.celdas(D, causal.cohortes(D), causal.H_CORTO) if c["g"] == g]
    assert len(cel) == 1
    return cel[0]


# ------------------------------------------------------------------ el estimador

def test_efecto_plantado_de_20_puntos_se_recupera_sin_pretendencia():
    """Con un efecto plantado de -20 puntos en e = 1 y sin tendencia previa, el ATT(1) da -20 y los meses previos dan 0."""
    spec = [_tratado(), _tratado()] + [_control() for _ in range(6)]
    D = _datos(spec)
    cel = _celda_de(D, G)
    att1 = causal.att_celdas(D, [cel], 1)["att"]
    assert abs(att1 - (-20.0)) < 1.0, f"el ATT(1) dio {att1}"
    for e in (-3, -2, -1):
        assert abs(causal.att_celdas(D, [cel], e)["att"]) < 1.0


def test_el_indice_es_el_caudal_sobre_la_base_recortado():
    """El indice de un mes es el caudal por dia calendario sobre la base, recortado arriba en INDICE_TOPE."""
    spec = [_tratado(), _tratado()] + [_control() for _ in range(6)]
    D = _datos(spec)
    cel = _celda_de(D, G)
    base = cel["base_t"]
    assert np.allclose(base, TASA_BASE)
    vals = causal.indice(D, cel["tratados"], base, G, 1)
    assert np.allclose(vals, TASA_EFECTO / TASA_BASE)
    # con un caudal enorme el indice se recorta en INDICE_TOPE
    alto = TASA_BASE * causal.INDICE_TOPE * 4
    D2 = _datos([_tratado()] + [_control() for _ in range(6)])
    D2["tasa"][0, G + 1] = alto
    assert np.isclose(causal.indice(D2, np.array([0]), np.array([TASA_BASE]), G, 1)[0], causal.INDICE_TOPE)


# ------------------------------------------------------------------ los controles

def test_el_nunca_tratado_fuera_de_los_controles_primarios_y_dentro_de_s1():
    """Un pozo sin golpe a KM_TRATADO km en todo el dato no es control primario (solo S1 lo suma)."""
    spec = [_tratado(), _tratado()] + [_control() for _ in range(6)]
    spec.append({"tasa": [TASA_BASE] * T_MESES, "golpes": {}})
    D = _datos(spec)
    nunca = len(spec) - 1
    assert D["g1"][nunca] == -1
    primarios = causal.controles(D, G, causal.H_CORTO, incluir_nunca=False)
    con_s1 = causal.controles(D, G, causal.H_CORTO, incluir_nunca=True)
    assert nunca not in primarios
    assert nunca in con_s1
    assert len(con_s1) == len(primarios) + 1


def test_el_control_con_golpe_a_2_km_dentro_de_la_ventana_queda_excluido():
    """Un control con un golpe a menos de KM_LIMPIO km dentro de [g - VENTANA_PREVIA, g + H] no entra a la celda."""
    spec = [_tratado(), _tratado()] + [_control() for _ in range(6)]
    spec.append(_control({8: 1.5, 20: 0.5}))          # golpe a 1,5 km dentro de la ventana
    D = _datos(spec)
    sospechoso = len(spec) - 1
    controles = causal.controles(D, G, causal.H_CORTO, incluir_nunca=False)
    assert sospechoso not in controles
    con_s1 = causal.controles(D, G, causal.H_CORTO, incluir_nunca=True)
    assert sospechoso not in con_s1
    # el mismo pozo sin el golpe de dentro de la ventana si entra
    spec2 = [_tratado(), _tratado()] + [_control() for _ in range(6)]
    spec2.append(_control({20: 0.5}))
    D2 = _datos(spec2)
    assert len(spec2) - 1 in causal.controles(D2, G, causal.H_CORTO, incluir_nunca=False)


def test_la_celda_necesita_cinco_controles_con_dato():
    """Una celda con menos de MIN_CONTROLES_CELDA controles con dato no entra al estimador."""
    spec = [_tratado(), _tratado()] + [_control() for _ in range(4)]
    D = _datos(spec)
    cel = _celda_de(D, G)
    r = causal.att_celdas(D, [cel], 1)
    assert r["n_celdas"] == 0
    assert np.isnan(r["att"])


# ------------------------------------------------------------------ umbrales y veredictos

def test_m_estrella():
    """La cota M* sale del maximo de los tres tramos y es infinita si no hay pretrendimiento."""
    assert causal.m_estrella(-5.0, 0.0, 0.0, 0.0) == float("inf")
    assert causal.m_estrella(5.0, 0.0, 0.0, 0.0) == 0.0
    # m = max(|b3|, |b2 - b3|, |b1 - b2|) = 1 y resto = 20 - 3 = 17
    assert abs(causal.m_estrella(-20.0, -1.0, -2.0, -3.0) - 8.5) < 1e-9
    # con resto negativo el resultado es cero
    assert causal.m_estrella(-1.0, -1.0, -1.0, -1.0) == 0.0


def test_rompe():
    """Un placebo rompe si su IC excluye cero y su valor absoluto llega al umbral."""
    assert causal.rompe(5.0, 1.0, 10.0, 5.0)
    assert causal.rompe(-6.0, -10.0, -1.0, 5.0)
    assert not causal.rompe(4.9, 1.0, 10.0, 5.0)      # por debajo del umbral
    assert not causal.rompe(5.0, -1.0, 10.0, 5.0)      # el IC incluye cero
    assert not causal.rompe(-5.0, -10.0, 1.0, 5.0)     # el IC incluye cero


# ------------------------------------------------------------------ cotas de Lee

def test_cotas_de_lee_sobre_un_caso_a_mano():
    """Con 4 de 5 tratados observados y 3 de 3 controles observados, el recorte es del 20% del grupo con mas observados."""
    y_trat = np.array([10.0, 12.0, 14.0, 16.0])
    y_ctrl = np.array([5.0, 6.0, 7.0])
    r = causal.lee_limites(y_trat, 5, y_ctrl, 3)
    assert abs(r["q_tratados"] - 0.8) < 1e-12
    assert abs(r["q_controles"] - 1.0) < 1e-12
    # los controles son el grupo con mas observados: se les recorta 1 de 3 valores (p = 0,2)
    assert abs(r["ic_bajo"] - 6.5) < 1e-9
    assert abs(r["ic_alto"] - 7.5) < 1e-9
    # con la misma tasa de observacion no hay recorte
    r2 = causal.lee_limites(np.array([1.0, 2.0]), 2, np.array([3.0]), 1)
    assert abs(r2["ic_bajo"] - (-1.5)) < 1e-9
    assert abs(r2["ic_alto"] - (-1.5)) < 1e-9


# ------------------------------------------------------------------ el bootstrap

def test_el_bootstrap_por_bloques_es_determinista_y_arrastra_el_bloque_entero():
    """Los mismos sorteos dan el mismo IC, y un bloque entra con todos sus pozos."""
    spec = [_tratado(), _tratado()] + [_control() for _ in range(6)]
    D = _datos(spec)
    cel = _celda_de(D, G)
    w = causal._pesos_bloques(D, np.arange(D["n"]), 50, np.random.default_rng(causal.SEMILLA_CAUSAL))
    assert w.shape == (50, D["n"])
    assert np.all(w.sum(axis=1) == w.sum(axis=1)[0])       # cada repeticion sortea la misma cantidad de bloques
    r1 = causal.bootstrap(D, [cel], (1,), w)
    r2 = causal.bootstrap(D, [cel], (1,), w)
    assert np.allclose(r1["ic_bajo"], r2["ic_bajo"])
    assert np.allclose(r1["ic_alto"], r2["ic_alto"])
    assert abs(r1["est"][0] - (-20.0)) < 1.0


def _marts_sinteticos(con, v1: str, v2: str) -> None:
    """Escribe los cinco marts con cifras inventadas, con los veredictos dados para D1 y D2."""
    filas_serie = [("D1", m, e, 400, 2000, -1.0 * e, -5.0, 5.0) for m in ("principal", "S1") for e in causal.E_SERIE]
    causal._escribir(con, "mart_causal_serie", causal.COLS_SERIE, filas_serie)
    causal._escribir(con, "mart_causal_placebo", causal.COLS_PLACEBO,
                     [("D1", "nunca_tratados", 500, -8.0, -15.0, -1.0, True),
                      ("D2", "previo", 400, 1.0, -1.0, 3.0, False)])
    causal._escribir(con, "mart_causal_operador", causal.COLS_OPERADOR, [("YPF", 100, -20.0, -30.0, -10.0)])
    nan = float("nan")
    causal._escribir(con, "mart_causal_extra", causal.COLS_EXTRA,
                     [("D1", "M*", 0.5, nan, nan, 400), ("D1", "potencia_pretrendencia", 6.0, nan, nan, 400),
                      ("D1", "lee_ic_bajo", -0.4, nan, nan, 400), ("D1", "lee_ic_alto", 0.1, nan, nan, 400),
                      ("D1", "lee_q_tratados", 0.4, nan, nan, 400), ("D1", "lee_q_controles", 0.8, nan, nan, 400),
                      ("D2", "cierre_placebo", 3.0, 2.0, 7.0, 2000)])
    causal._escribir(con, "mart_causal_veredicto", causal.COLS_VEREDICTO,
                     [("D1", v1, "ATT(1)", -25.0, -33.0, -17.0, 400, 80, ""),
                      ("D1b", causal.V_SIN_MUESTRA, "persistencia", -6.0, -36.0, 17.0, 40, 50, ""),
                      ("D2", v2, "ATT_W", 14.0, 9.5, 20.0, 400, 80, "")])


def test_la_pagina_imprime_cada_veredicto_y_la_lectura_solo_si_corresponde():
    import duckdb
    con = duckdb.connect(":memory:")
    _marts_sinteticos(con, causal.V_PLACEBO, causal.V_D2_SOSTIENE)
    txt = causal.pagina_causal(con)
    assert f"**D1, caudal de petróleo al mes 1: {causal.V_PLACEBO}.**" in txt
    assert f"**D1b, persistencia en los meses 7 a 24: {causal.V_SIN_MUESTRA}.**" in txt
    assert f"**D2, corte de agua: {causal.V_D2_SOSTIENE}.**" in txt
    assert "Lectura: el dato público carga una sola afirmación causal" in txt
    assert "commit 8f52ff1" in txt and "NOTA DE MUESTRA" in txt
    assert "\u2013" not in txt and "\u2014" not in txt
    con2 = duckdb.connect(":memory:")
    _marts_sinteticos(con2, causal.V_NO_FIRME, causal.V_NO_FIRME)
    assert "Lectura:" not in causal.pagina_causal(con2)


def test_cada_veredicto_lleva_su_marca_antes_de_las_palabras():
    import duckdb
    veredictos = {v for k, v in vars(causal).items() if k.startswith("V_") and isinstance(v, str)}
    assert veredictos == set(causal.MARCA_VEREDICTO)
    assert set(causal.MARCA_VEREDICTO.values()) <= {"●", "◐", "○"}
    con = duckdb.connect(":memory:")
    _marts_sinteticos(con, causal.V_PLACEBO, causal.V_D2_SOSTIENE)
    txt = causal.pagina_causal(con)
    assert f"- ○ **D1, caudal de petróleo al mes 1: {causal.V_PLACEBO}.**" in txt
    assert f"- ○ **D1b, persistencia en los meses 7 a 24: {causal.V_SIN_MUESTRA}.**" in txt
    assert f"- ● **D2, corte de agua: {causal.V_D2_SOSTIENE}.**" in txt
