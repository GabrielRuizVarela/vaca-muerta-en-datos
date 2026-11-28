"""R1 (golpes repetidos) sin warehouse: los eventos, los tratados, los controles, el veredicto y la pagina, con paneles a mano.

Ningun numero de aca sale de datos reales: los paneles son sinteticos y las cifras son las que se plantan."""
import duckdb
import numpy as np
import pytest

from pipeline import causal
from pipeline import golpes_repetidos as gr
from pipeline.causal import (EDAD_MIN, H_CORTO, KM_LIMPIO, KM_TRATADO, UMBRAL_AGUA_PP, V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA,
                             _pesos_bloques)
from pipeline.causal_exposicion import COLS_VEREDICTO, S_CENSURA
from pipeline.causal_profundo import E_D5, FRACCION_CURA, MIN_TRATADOS_D5
from pipeline.costo import _escribir

T = 60
G = 32            # mes del golpe posterior de los casos de abajo
ATT_D2 = 13.8     # el comparador de D2 de los casos de veredicto (el valor real se lee de mart_causal_veredicto en la corrida)


def _panel(hits: dict[int, dict[int, float]], n: int, primer=None, w=None, bloque=None) -> dict:
    """D minimo (t0 = 0, T meses) con km_min[pozo, mes] = km de `hits` (nan = sin golpe) y W constante de 0,1."""
    km_min = np.full((n, T), np.nan)
    for i, meses in hits.items():
        for m, km in meses.items():
            km_min[i, m] = km
    primer = np.zeros(n, dtype=np.int64) if primer is None else np.asarray(primer, dtype=np.int64)
    w = np.full((n, T), 0.1) if w is None else w
    bloque = np.arange(n) if bloque is None else bloque
    return causal._armar(np.arange(n), np.array(["OP"] * n, dtype=object), np.zeros(n), np.zeros(n), primer, bloque, 0, T - 1,
                         np.full((n, T), 10.0), w, np.ones((n, T)), np.zeros((n, T)), np.ones((n, T), dtype=bool), km_min,
                         np.full((n, T), np.nan), np.full((n, T), np.nan), {})


# ---- eventos

def test_un_pad_entre_g_y_g_mas_1_es_un_solo_evento():
    fila = np.full(T, np.nan)
    fila[[20, 21]] = 0.5
    assert gr.eventos(fila, 0) == [(20, 1, None)]


def test_un_golpe_en_g_mas_2_es_un_evento_nuevo_de_orden_2():
    fila = np.full(T, np.nan)
    fila[[20, 21, 22]] = 0.5          # 20 abre el evento 1; 21 es de ese evento; 22 - 20 = 2 abre el evento 2
    assert S_CENSURA == 2
    assert gr.eventos(fila, 0) == [(20, 1, None), (22, 2, 2)]


def test_un_golpe_a_1_5_km_no_es_evento_y_los_meses_antes_de_primer_no_cuentan():
    fila = np.full(T, np.nan)
    fila[10], fila[20], fila[30] = 0.5, 1.5, 0.5
    assert gr.eventos(fila, 15, 0) == [(30, 1, None)]      # el de 10 es anterior a primer; el de 20 esta a 1,5 km
    assert gr.eventos(fila, -1, 0) == []                   # sin petroleo no hay eventos


def test_los_meses_son_absolutos_con_t0():
    fila = np.full(10, np.nan)
    fila[[2, 7]] = 0.5
    assert gr.eventos(fila, 100, t0=100) == [(102, 1, None), (107, 2, 5)]


def test_bandas_cerradas_y_la_ultima_abierta():
    assert gr.BANDAS_S == ((8, 12), (13, 24), (25, None))
    assert [gr.bandas_s(s) for s in (7, 8, 12, 13, 24, 25, 100)] == [None, 0, 0, 1, 1, 2, 2]
    assert gr.bandas_s(None) is None


# ---- tratados: s = 7 se cuenta y no se trata, s = 8 se trata

def test_s_7_se_cuenta_y_no_se_trata_s_8_si():
    hits = {0: {G - 7: 0.5, G: 0.5}, 1: {G - 8: 0.5, G: 0.5}}      # padre 0: s = 7; padre 1: s = 8
    D = _panel(hits, 2)
    pozo, g, k, s = gr.eventos_posteriores(D)
    assert (pozo.tolist(), s.tolist()) == ([0, 1], [7, 8])              # los dos se cuentan
    pozo, g, k, s = gr.tratados_r1(D)
    assert (pozo.tolist(), g.tolist(), k.tolist(), s.tolist()) == ([1], [G], [2], [8])


def test_tratado_pide_edad_base_de_w_y_ventana_previa_limpia():
    hits = {0: {10: 0.5, G: 0.5},                 # elegible
            1: {10: 0.5, G: 0.5},                 # edad en g menor que EDAD_MIN
            2: {10: 0.5, G: 0.5},                 # base de W sin datos
            3: {10: 0.5, G - 3: 1.5, G: 0.5},     # un golpe a 1,5 km (< KM_LIMPIO) en [g - 6, g - 1]
            4: {10: 0.5, G - 7: 1.5, G: 0.5}}     # a 1,5 km pero en g - 7: fuera de la ventana de 6 meses
    primer = [0, G - EDAD_MIN + 1, 0, 0, 0]
    w = np.full((5, T), 0.1)
    w[2, G - 6:G - 3] = np.nan                    # los tres meses de la base de W
    D = _panel(hits, 5, primer=primer, w=w)
    assert KM_LIMPIO > 1.5 > KM_TRATADO
    assert gr.VENTANA_PREVIA_POSTERIOR == 6
    assert gr.tratados_r1(D)[0].tolist() == [0, 4]


# ---- controles

def _caso_controles() -> dict:
    """Un tratado (pozo 0: golpes en 20 y 32, s = 12) y padres que prueban cada regla de un control."""
    hits = {0: {20: 0.5, G: 0.5},
            1: {20: 0.5},                         # control: un golpe a 12 meses de g
            2: {23: 0.5},                         # control: s_j = 9, la misma banda (8 a 12)
            3: {10: 0.5},                         # NO: su ultimo golpe es de otra banda (s_j = 22)
            4: {20: 0.5, G + 3: 1.5},             # NO: un golpe a 1,5 km en g + 3
            5: {},                                # NO: nunca golpeado
            6: {G + 8: 0.5},                      # NO: todavia no golpeado (su primer golpe es despues de g)
            7: {28: 0.5},                         # NO: s_j = 4, de la banda que no se estima
            8: {20: 0.5},                         # NO: de otro grupo de edad (primer = 15, edad 17 en g)
            9: {20: 0.5},                         # NO: edad menor que EDAD_MIN en g
            10: {20: 0.5, G: 0.5}}                # otro tratado de la misma celda
    primer = [0] * 11
    primer[8], primer[9] = 15, G - EDAD_MIN + 1
    return _panel(hits, 11, primer=primer)


def test_controles_de_la_celda():
    D = _caso_controles()
    trat = gr.tratados_r1(D)
    assert trat[0].tolist() == [0, 10] and trat[3].tolist() == [12, 12]
    cel = gr.celdas_r1(D, trat, H_CORTO)
    assert len(cel) == 1
    ce = cel[0]
    assert (ce["g"], ce["banda"], ce["tratados"].tolist()) == (G, 0, [0, 10])
    assert ce["controles"].tolist() == [1, 2]
    assert len(ce["base_t"]) == 2 and len(ce["base_c"]) == 2
    assert set(ce) >= {"g", "grupo", "tratados", "controles", "base_t", "base_c", "banda"}   # la forma de causal.celdas


def test_el_nunca_golpeado_y_el_no_golpeado_aun_nunca_son_controles():
    D = _caso_controles()
    ce = gr.celdas_r1(D, gr.tratados_r1(D), H_CORTO)[0]
    assert 5 not in ce["controles"] and 6 not in ce["controles"]


def test_la_ventana_del_control_llega_a_g_mas_h():
    hits = {0: {20: 0.5, G: 0.5}, 1: {20: 0.5, G + H_CORTO: 1.5}, 2: {20: 0.5, G + H_CORTO + 1: 1.5}}
    D = _panel(hits, 3)
    ce = gr.celdas_r1(D, gr.tratados_r1(D), H_CORTO)[0]
    assert ce["controles"].tolist() == [2]                # el golpe de g + H_CORTO excluye; el de g + H_CORTO + 1 no
    assert gr.celdas_r1(D, gr.tratados_r1(D), H_CORTO + 1)[0]["controles"].tolist() == []


# ---- veredicto: cada rama

def test_veredicto_sin_muestra_primero():
    assert gr.veredicto_r1(MIN_TRATADOS_D5 - 1, True, 50.0, 60.0, ATT_D2) == V_SIN_MUESTRA     # gana al placebo y al efecto
    assert MIN_TRATADOS_D5 == 200


def test_veredicto_placebo_antes_que_el_efecto():
    assert gr.veredicto_r1(MIN_TRATADOS_D5, True, 50.0, 60.0, ATT_D2) == V_PLACEBO


def test_veredicto_se_repite_si_el_ic_bajo_pasa_el_umbral():
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, UMBRAL_AGUA_PP + 0.1, 20.0, ATT_D2) == gr.V_R1_REPITE
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, UMBRAL_AGUA_PP, 20.0, ATT_D2) == V_NO_FIRME   # el umbral no cuenta
    assert gr.V_R1_REPITE == "se repite en cada golpe"


def test_veredicto_no_se_repite_contra_el_d2_de_la_corrida():
    corte = FRACCION_CURA * ATT_D2                       # 6,9
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, -1.0, corte - 0.1, ATT_D2) == gr.V_R1_NO_REPITE
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, -1.0, corte, ATT_D2) == V_NO_FIRME             # el corte no cuenta
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, -1.0, corte - 0.1, 2 * ATT_D2) == gr.V_R1_NO_REPITE
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, -1.0, corte - 0.1, 0.0) == V_NO_FIRME          # el comparador cambia el corte
    assert gr.V_R1_NO_REPITE == "no se repite"


def test_veredicto_no_firme_en_el_resto():
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, -1.0, 12.0, ATT_D2) == V_NO_FIRME      # incluye cero pero el alto es grande
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, 1.0, 12.0, ATT_D2) == V_NO_FIRME       # excluye cero, no pasa el umbral
    assert gr.veredicto_r1(MIN_TRATADOS_D5, False, 1.0, 5.0, float("nan")) == V_NO_FIRME


def test_constantes_de_la_regla():
    assert (gr.S_MIN_POSTERIOR, gr.VENTANA_PREVIA_POSTERIOR, gr.E_PLACEBO) == (8, 6, (-3, -2, -1))
    assert gr.DISENO_R1 == "R1"
    assert gr.REGLA_HEREDADA["S_CENSURA"] == 2 and gr.REGLA_HEREDADA["MIN_TRATADOS_D5"] == 200


# ---- el estimador de punta a punta, sobre un panel sintetico con efecto plantado

EFECTO = 0.20     # la suba de W plantada en los meses g y g + 1 de los tratados (20 puntos porcentuales)


def _panel_con_efecto(tercer_golpe: bool = False) -> tuple[dict, tuple]:
    """10 tratados (golpes en 20 y 32), 30 controles (solo el de 20), 2 pozos con s = 5 (no se estiman).

    Con `tercer_golpe` suma el pozo 42: golpes en 8, 20, G y G + 5. Su evento de G es de orden 3 (s = 12, tratado, con el efecto
    plantado) y el golpe de G + 5 lo saca de la serie desde e = 5."""
    n = 43 if tercer_golpe else 42
    hits = {i: {20: 0.5, G: 0.5} for i in range(10)}
    hits.update({i: {20: 0.5} for i in range(10, 40)})
    hits.update({i: {20: 0.5, 25: 0.5} for i in range(40, 42)})
    if tercer_golpe:
        hits[42] = {8: 0.5, 20: 0.5, G: 0.5, G + 5: 0.5}
    w = 0.1 + np.random.default_rng(3).normal(0.0, 0.005, (n, T))
    w[:10, G:G + 2] += EFECTO
    if tercer_golpe:
        w[42, G:G + 2] += EFECTO
    D = _panel(hits, n, w=w, bloque=np.arange(n) % 20)
    wells = np.arange(n)
    W = _pesos_bloques(D, wells, 60, np.random.default_rng(1))
    return D, (D, None, W, wells, None)


def _con_d2() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("create table mart_causal_veredicto (diseno varchar, veredicto varchar, estimando varchar, valor double, "
                "ic_bajo double, ic_alto double, n_tratados integer, n_bloques integer, motivo varchar)")
    con.execute("insert into mart_causal_veredicto values ('D2', 'x', 'ATT_W', ?, 9.5, 19.9, 447, 100, 'm')", [ATT_D2])
    return con


def test_calcular_recupera_el_efecto_plantado_y_cuenta_los_eventos(monkeypatch):
    D, prep = _panel_con_efecto()
    monkeypatch.setattr(gr, "MIN_TRATADOS_D5", 5)         # el panel tiene 10 tratados: la regla real pide 200
    filas, fila_v = gr.calcular(_con_d2(), prep)
    assert fila_v[0] == "R1" and fila_v[5] == 10
    assert fila_v[1] == gr.V_R1_REPITE and fila_v[3] > UMBRAL_AGUA_PP
    assert 100 * EFECTO - 2 < fila_v[2] < 100 * EFECTO + 2
    d = {(f[1], f[2], f[3]): f for f in filas}
    assert abs(d[("placebo", "pretendencia", None)][6]) < UMBRAL_AGUA_PP           # sin tendencia previa
    assert d[("d2", "ATT_W", None)][6] == ATT_D2                                    # leido del mart, no escrito
    assert d[("orden", "k=2", None)][4] == 10 and d[("orden", "k>=3", None)][4] == 0
    assert d[("banda", "8-12", None)][4] == 10 and d[("banda", "13-24", None)][4] == 0
    cuentas = {f[2]: f[4] for f in filas if f[1] == "cuenta"}
    assert cuentas == {"eventos_orden_2_o_mas": 12, "s_2_a_7": 2, "elegibles": 10, "en_celdas_con_controles": 10,
                       "pozos_sin_bloque": 0}
    serie = {f[3]: f for f in filas if f[1] == "serie"}
    assert sorted(serie) == list(E_D5)
    assert serie[0][6] > 100 * EFECTO - 3 and abs(serie[-3][6]) < 3 and abs(serie[5][6]) < 3


def test_el_tercer_golpe_sale_de_la_serie_desde_su_mes_y_cuenta_como_k_3_o_mas(monkeypatch):
    monkeypatch.setattr(gr, "MIN_TRATADOS_D5", 5)
    base = {f[3]: f for f in gr.calcular(_con_d2(), _panel_con_efecto()[1])[0] if f[1] == "serie"}
    filas, fila_v = gr.calcular(_con_d2(), _panel_con_efecto(tercer_golpe=True)[1])
    serie = {f[3]: f for f in filas if f[1] == "serie"}
    assert {e: f[4] for e, f in base.items()} == {e: 10 for e in E_D5}                    # sin el pozo 42: 10 en todos los meses
    assert S_CENSURA <= 5
    assert {e: f[4] for e, f in serie.items()} == {e: (11 if e < 5 else 10) for e in E_D5}   # el pozo 42 sale desde e = 5
    d = {(f[1], f[2], f[3]): f for f in filas}
    assert d[("orden", "k>=3", None)][4] > 0 and d[("orden", "k=2", None)][4] == 10         # el de orden 3 va a k>=3
    assert fila_v[5] == 11


def test_sin_muestra_con_la_regla_real_aunque_el_efecto_sea_grande():
    D, prep = _panel_con_efecto()
    filas, fila_v = gr.calcular(_con_d2(), prep)          # n = 10 < 200
    assert fila_v[1] == V_SIN_MUESTRA and fila_v[5] == 10
    assert [f for f in filas if f[1] == "cuenta"]         # las cuentas se publican igual


def test_el_pozo_sin_bloque_sale_y_se_cuenta(monkeypatch):
    D, prep = _panel_con_efecto()
    monkeypatch.setattr(gr, "MIN_TRATADOS_D5", 5)
    D_, _c, W, wells, _coh = prep
    D_["bloque"][39:] = 99                                # el pozo 39 (un control) queda en un bloque sin pozos del universo
    filas, fila_v = gr.calcular(_con_d2(), (D_, None, W, np.arange(39), None))
    cuentas = {f[2]: f[4] for f in filas if f[1] == "cuenta"}
    assert cuentas["pozos_sin_bloque"] == 1 and cuentas["eventos_orden_2_o_mas"] == 12
    assert fila_v[5] == 10                                # los tratados siguen; el control que sale ya no cuenta


# ---- la pagina

def _con_marts(veredicto: str, n: int, con_filas: bool = True) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    filas = [("R1", "att", "todos", None, n, 40, 9.5, 4.0, 15.0),
             ("R1", "placebo", "pretendencia", None, n, 40, 0.4, -1.0, 1.8),
             ("R1", "d2", "ATT_W", None, 447, None, 13.8, 9.5, 19.9)]
    if con_filas:
        filas += [("R1", "orden", "k=2", None, n, 40, 9.0, 3.0, 15.0), ("R1", "banda", "8-12", None, n, 40, 9.0, 3.0, 15.0),
                  *[("R1", "serie", "dW", e, n, 40, 10.0 - e, 1.0, 20.0) for e in E_D5],
                  ("R1", "cuenta", "eventos_orden_2_o_mas", None, 321, None, 321.0, None, None),
                  ("R1", "cuenta", "s_2_a_7", None, 87, None, 87.0, None, None),
                  ("R1", "cuenta", "elegibles", None, 120, None, 120.0, None, None),
                  ("R1", "cuenta", "en_celdas_con_controles", None, n, None, float(n), None, None),
                  ("R1", "cuenta", "pozos_sin_bloque", None, 2, None, 2.0, None, None)]
    _escribir(con, "mart_golpes_repetidos", gr.COLS_R1, filas)
    _escribir(con, "mart_golpes_repetidos_veredicto", COLS_VEREDICTO, [("R1", veredicto, 9.5, 4.0, 15.0, n, "motivo")])
    return con


def test_la_pagina_dice_sin_muestra_con_menos_de_200():
    txt = gr.pagina_golpes_repetidos(_con_marts(V_SIN_MUESTRA, MIN_TRATADOS_D5 - 1))
    assert "**Veredicto: sin muestra.**" in txt
    assert f"menos de {MIN_TRATADOS_D5} golpes" in txt
    assert f"regla fijada en {gr.SHA_REGLA} antes de calcular" in txt
    assert "321" in txt and "87" in txt                    # las cuentas salen aunque no haya veredicto


@pytest.mark.parametrize("v", [V_SIN_MUESTRA, V_PLACEBO, gr.V_R1_REPITE, gr.V_R1_NO_REPITE, V_NO_FIRME])
def test_la_pagina_imprime_cada_veredicto(v):
    n = MIN_TRATADOS_D5 - 1 if v == V_SIN_MUESTRA else MIN_TRATADOS_D5
    txt = gr.pagina_golpes_repetidos(_con_marts(v, n))
    assert f"**Veredicto: {v}.**" in txt
    assert ("menos de" in txt.split("Veredicto")[1].split("##")[0]) == (v == V_SIN_MUESTRA)
    assert "+13,8" in txt and "+9,5" in txt                # el comparador de D2 y el ATT, con coma decimal


def test_la_pagina_sin_serie_ni_cortes_no_falla():
    txt = gr.pagina_golpes_repetidos(_con_marts(V_SIN_MUESTRA, 0, con_filas=False))
    assert "Mes a mes" not in txt and "Cuentas" not in txt and "Lo que no dice" in txt
