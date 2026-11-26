"""D12 sin warehouse: las celdas por operador y area y los veredictos."""
import numpy as np

from pipeline import causal_exposicion as ce
from pipeline.causal import MIN_TRATADOS, MIN_TRATADOS_OPERADOR, UMBRAL_AGUA_PP, V_NO_FIRME, V_SIN_MUESTRA

# pozos 0..9: operador y area
OPS = np.array(["YPF", "YPF", "YPF", "PAE", "PAE", "YPF", "YPF", "PAE", "YPF", "PAE"], dtype=object)
AREAS = np.array(["A", "A", "B", "A", "A", "A", "B", "B", "A", "A"], dtype=object)
D = {"operador": OPS, "pozo_id": np.arange(10)}


def _celdas():
    return [
        {"g": 100, "grupo": 0, "tratados": np.array([0, 3]), "controles": np.array([1, 2, 4, 5, 6, 7]),
         "base_t": np.array([1.0, 2.0]), "base_c": np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])},
        {"g": 101, "grupo": 1, "tratados": np.array([8]), "controles": np.array([5, 9]),
         "base_t": np.array([3.0]), "base_c": np.array([1.0, 1.0])},
    ]


def _resumen(celdas_):
    return sorted((c["g"], tuple(c["tratados"].tolist()), tuple(c["controles"].tolist())) for c in celdas_)


def test_controles_del_mismo_operador_y_area():
    out = ce.celdas_operador_area(D, _celdas(), AREAS)
    assert _resumen(out) == [(100, (0,), (1, 5)), (100, (3,), (4,)), (101, (8,), (5,))]
    for c in out:
        assert len(c["base_t"]) == len(c["tratados"]) and len(c["base_c"]) == len(c["controles"])


def test_quitar_saca_ypf_de_tratados_y_controles():
    out = ce.celdas_operador_area(D, _celdas(), AREAS, quitar="YPF")
    assert _resumen(out) == [(100, (3,), (4,))]
    assert all(OPS[c["tratados"]].tolist() == ["PAE"] and set(OPS[c["controles"]]) == {"PAE"} for c in out)


def test_ypf_se_compara_en_mayusculas_y_sin_espacios_al_borde():
    d = {"operador": np.array([" ypf ", "YPF", "Ypf", "PAE", "PAE", "ypf", "YPF ", "PAE", "YPF", "PAE"], dtype=object),
         "pozo_id": np.arange(10)}
    assert _resumen(ce.celdas_operador_area(d, _celdas(), AREAS, quitar="YPF")) == [(100, (3,), (4,))]
    solo = ce.celdas_operador_area(d, _celdas(), AREAS, solo="YPF")
    assert {t for c in solo for t in c["tratados"].tolist()} == {0, 8}


def test_solo_ypf_deja_unicamente_ypf():
    out = ce.celdas_operador_area(D, _celdas(), AREAS, solo="YPF")
    assert _resumen(out) == [(100, (0,), (1, 5)), (101, (8,), (5,))]
    assert all(set(OPS[c["tratados"]]) == {"YPF"} and set(OPS[c["controles"]]) == {"YPF"} for c in out)


def test_par_sin_controles_queda_con_controles_vacios():
    cel = [{"g": 100, "grupo": 0, "tratados": np.array([3]), "controles": np.array([0, 1])}]
    out = ce.celdas_operador_area(D, cel, AREAS)
    assert len(out) == 1 and len(out[0]["controles"]) == 0   # el estimador la descarta por MIN_CONTROLES_CELDA


def test_veredicto_operador_area():
    f = ce.veredicto_operador_area
    assert f(MIN_TRATADOS - 1, 50.0, 60.0) == V_SIN_MUESTRA
    assert f(MIN_TRATADOS, UMBRAL_AGUA_PP + 1, UMBRAL_AGUA_PP + 9) == ce.V_D12_SOSTIENE
    assert f(MIN_TRATADOS, -1.0, 5.0) == ce.V_D12_COMPOSICION
    assert f(MIN_TRATADOS, UMBRAL_AGUA_PP / 2, 9.0) == V_NO_FIRME   # IC sobre cero pero no sobre el umbral
    assert f(MIN_TRATADOS, -9.0, -1.0) == V_NO_FIRME               # IC bajo cero


def test_veredicto_fuera_de_ypf():
    f = ce.veredicto_fuera_de_ypf
    assert f(MIN_TRATADOS_OPERADOR - 1, 3.0, 9.0) == V_SIN_MUESTRA
    assert f(MIN_TRATADOS_OPERADOR, 0.1, 9.0) == ce.V_D12_FUERA_REPITE
    assert f(MIN_TRATADOS_OPERADOR, -2.0, 9.0) == ce.V_D12_FUERA_NO
    assert f(MIN_TRATADOS_OPERADOR, -9.0, -1.0) == V_NO_FIRME   # IC entero bajo cero


def test_operador_ypf_literal():
    assert ce.OPERADOR_YPF == "YPF"


# ---- D10: censura en el segundo golpe

def _d10(hits: dict[int, dict[int, float]], n: int = 5, T: int = 30, t0: int = 100):
    """D minimo con km_min (n pozos x T meses; nan = sin golpe); hits[pozo][mes] = km."""
    km = np.full((n, T), np.nan)
    for i, meses in hits.items():
        for m, k in meses.items():
            km[i, m - t0] = k
    return {"km_min": km, "t0": t0, "T": T}


def test_censura_mes_dos_a_doce_a_1_km_y_a_2_km():
    g = 110
    D10 = _d10({0: {g: 0.4, g + 1: 0.3, g + 2: 0.8},        # el mes g + 1 no censura; g + 2 a 0,8 km si, desde e = 2
                1: {g: 0.4, g + 1: 0.3},                     # solo el mes g + 1: no se censura nunca
                2: {g: 0.4, g + 3: 1.5},                     # 1,5 km: solo en la serie de 2 km
                3: {g: 0.4, g + 4: 1.5, g + 5: 0.5},         # 2 km desde 4, 1 km desde 5
                4: {g: 0.4, g + 13: 0.2}})                   # fuera de la ventana: no censura
    cel = {"g": g, "tratados": np.arange(5)}
    S = ce.SIN_CENSURA
    assert ce.mes_censura(D10, cel, ce.KM_CENSURA).tolist() == [2, S, S, 5, S]
    assert ce.mes_censura(D10, cel, ce.KM_CENSURA_SECUNDARIA).tolist() == [2, S, 3, 4, S]
    assert ce.mes_censura(D10, cel, None).tolist() == [S] * 5


def test_censura_respeta_el_borde_de_la_distancia_y_de_la_ventana():
    g = 110
    D10 = _d10({0: {g + 2: ce.KM_CENSURA},            # exactamente 1 km no es "menos de 1 km"
                1: {g + ce.H_D5: 0.9},                # el ultimo mes de la ventana cuenta
                2: {g + 2: 0.9}}, n=3)
    out = ce.mes_censura(D10, {"g": g, "tratados": np.arange(3)}, ce.KM_CENSURA)
    assert out.tolist() == [ce.SIN_CENSURA, ce.H_D5, 2]
    # un panel que termina antes de g + H_D5 no rompe nada: solo cuentan los meses que existen
    D10 = _d10({2: {g + 2: 0.9}}, n=3, T=g + 5 - 100)
    out = ce.mes_censura(D10, {"g": g, "tratados": np.arange(3)}, ce.KM_CENSURA)
    assert out.tolist() == [ce.SIN_CENSURA, ce.SIN_CENSURA, 2]


def test_censurar_pone_nan_desde_el_mes_de_censura():
    vt = [np.array([1.0, 2.0, 3.0]), np.array([4.0])]
    cens = [np.array([2, ce.SIN_CENSURA, 5]), np.array([3])]
    for e, esperado in ((0, [[1, 2, 3], [4]]), (1, [[1, 2, 3], [4]]), (2, [[np.nan, 2, 3], [4]]),
                        (3, [[np.nan, 2, 3], [np.nan]]), (5, [[np.nan, 2, np.nan], [np.nan]]),
                        (-3, [[1, 2, 3], [4]])):
        out = ce.censurar(vt, cens, e)
        for o, x in zip(out, esperado):
            np.testing.assert_array_equal(o, np.array(x, dtype=float))
    assert not np.isnan(vt[0]).any()   # no toca la entrada


def test_censura_solo_de_los_tratados_indicados():
    g = 110
    D10 = _d10({3: {g + 2: 0.1}, 0: {g + 2: 0.1}})
    out = ce.mes_censura(D10, {"g": g, "tratados": np.array([1, 3])}, ce.KM_CENSURA)
    assert out.tolist() == [ce.SIN_CENSURA, 2]


# ---- D11: rama y anillos

def test_bandas_de_rama_son_cerradas_a_la_izquierda():
    m = np.array([0.0, 249.9, 250.0, 999.9, 1000.0, 5000.0, np.nan])
    assert ce.bandas_rama(m).tolist() == [0, 0, 1, 1, 2, 2, -1]


def test_anios_de_rama_son_inclusivos():
    g = lambda anio, mes: anio * 12 + mes - 1   # noqa: E731
    assert not ce.en_anios_rama(g(2015, 12))
    assert ce.en_anios_rama(g(2016, 1)) and ce.en_anios_rama(g(2023, 12))
    assert not ce.en_anios_rama(g(2024, 1))


def test_distancia_de_rama_es_la_menor_del_mes_y_nan_fuera_de_anios():
    g = 2020 * 12
    pares = {(7, g): 120.0, (8, g): 900.0, (7, g + 1): 5.0}
    out = ce.distancia_rama(np.array([7, 8, 9]), g, pares)
    assert out[:2].tolist() == [120.0, 900.0] and np.isnan(out[2])
    fuera = ce.distancia_rama(np.array([7]), 2024 * 12, {(7, 2024 * 12): 1.0})
    assert np.isnan(fuera).all()


def test_controles_limpios_de_rama():
    g = 100
    cerca = {1: np.array([g - ce.VENTANA_PREVIA - 1]),        # justo antes de la ventana: se queda
             2: np.array([g - ce.VENTANA_PREVIA]),            # borde de la ventana: sale
             3: np.array([g + ce.H_CORTO]),                   # borde de la ventana: sale
             4: np.array([g + ce.H_CORTO + 1, 5])}            # fuera de la ventana: se queda
    medidos = {1, 2, 3, 4, 5}                                  # el 6 no tiene rama medida
    keep = ce.controles_rama_limpios(np.array([1, 2, 3, 4, 5, 6]), g, cerca, medidos)
    assert keep.tolist() == [True, False, False, True, True, False]


def test_controles_sin_golpe_a_5_km_en_la_ventana():
    t0, g = 100, 120
    km = np.full((4, 60), np.nan)
    km[0, g - ce.VENTANA_PREVIA - t0] = 4.9                    # borde de la ventana: sale
    km[1, g - ce.VENTANA_PREVIA - 1 - t0] = 1.0                # un mes antes de la ventana: se queda
    km[2, g + ce.H_CORTO - t0] = 4.99                          # ultimo mes de la ventana: sale
    km[3, g + ce.H_CORTO + 1 - t0] = 1.0                       # un mes despues: se queda
    D = {"km_min": km, "t0": t0, "T": 60}
    assert ce.controles_sin_golpe(D, g, np.arange(4)).tolist() == [False, True, False, True]
    assert ce.controles_sin_golpe(D, g, np.array([2, 3])).tolist() == [False, True]
    km[1, g - t0] = ce.KM_ANILLO_LIMPIO                         # exactamente 5 km no es "menos de 5 km"
    assert ce.controles_sin_golpe(D, g, np.array([1])).tolist() == [True]


def test_filtrar_controles_recorta_bases_y_descarta_celdas_chicas():
    cel = [{"g": 100, "grupo": 0, "tratados": np.array([0]), "controles": np.arange(1, 1 + ce.MIN_CONTROLES_CELDA + 2),
            "base_t": np.array([1.0]), "base_c": np.arange(ce.MIN_CONTROLES_CELDA + 2, dtype=float)},
           {"g": 101, "grupo": 0, "tratados": np.array([0]), "controles": np.arange(1, 1 + ce.MIN_CONTROLES_CELDA),
            "base_t": np.array([1.0]), "base_c": np.zeros(ce.MIN_CONTROLES_CELDA)}]

    def sin_el_primero(c):
        m = np.ones(len(c["controles"]), dtype=bool)
        m[0] = False
        return m
    out = ce.filtrar_controles(cel, sin_el_primero)
    assert [c["g"] for c in out] == [100]                       # la segunda queda con MIN - 1 controles
    assert out[0]["controles"].tolist() == cel[0]["controles"][1:].tolist()
    assert out[0]["base_c"].tolist() == cel[0]["base_c"][1:].tolist()


def test_candidatos_anillo_primer_mes_y_sin_golpe_mas_cerca():
    t0, T = 100, 60
    km = np.full((5, T), np.nan)
    km[0, 30] = 2.5                                            # primer mes 2,5 km: entra en 2 a 3
    km[1, 30] = 2.0                                            # exactamente 2 km: entra en 2 a 3 (cerrado a la izquierda)
    km[2, 30] = 3.0                                            # exactamente 3 km: no entra en 2 a 3, si en 3 a 5
    km[3, 30], km[3, 25] = 2.5, 1.5                            # golpe a 1,5 km 5 meses antes de g: sale
    km[4, 30], km[4, 30 + ce.H_CORTO + 1] = 2.5, 1.0           # golpe cercano despues de la ventana: se queda
    D = {"km_min": km, "t0": t0, "T": T}
    sel, gs = ce.candidatos_anillo(D, 2.0, 3.0)
    assert sel.tolist() == [0, 1, 4] and gs.tolist() == [130, 130, 130]
    sel, gs = ce.candidatos_anillo(D, 3.0, 5.0)
    assert sel.tolist() == [2] and gs.tolist() == [130]


def test_candidatos_anillo_toma_el_primer_mes_aunque_despues_haya_otro_anillo():
    t0, T = 100, 60
    km = np.full((1, T), np.nan)
    km[0, 20], km[0, 28] = 4.0, 2.5                            # primero a 4 km (anillo 3 a 5); a 2,5 km mas tarde
    D = {"km_min": km, "t0": t0, "T": T}
    assert ce.candidatos_anillo(D, 3.0, 5.0)[1].tolist() == [120]
    assert ce.candidatos_anillo(D, 2.0, 3.0)[1].tolist() == [128]   # su primer mes en ese anillo
    # y con el golpe de 4 km dentro de la ventana previa no hay golpe "mas cerca" que 3 km: sigue siendo candidato en 2 a 3
    assert ce.candidatos_anillo(D, 2.0, 3.0)[0].tolist() == [0]


def test_veredicto_rama():
    f = ce.veredicto_rama
    n = ce.MIN_TRATADOS_BANDA
    assert f(n - 1, n, 5.0, 9.0, 10.0) == V_SIN_MUESTRA
    assert f(n, n - 1, 5.0, 9.0, 10.0) == V_SIN_MUESTRA
    assert f(n, n, 0.1, 9.0, 10.0) == ce.V_RAMA_GRADIENTE
    assert f(n, n, -2.0, 4.9, 10.0) == ce.V_RAMA_SIN_GRADIENTE        # IC alto < 0,5 x 10
    assert f(n, n, -2.0, 5.0, 10.0) == V_NO_FIRME                     # exactamente la mitad no alcanza
    assert f(n, n, -2.0, 1.0, -3.0) == V_NO_FIRME                     # banda cercana negativa
    assert f(n, n, -9.0, -1.0, 10.0) == V_NO_FIRME                    # IC bajo cero


def test_veredicto_anillos():
    f = ce.veredicto_anillos
    n = ce.MIN_TRATADOS_BANDA
    a12, a23, a35 = ce.ANILLOS_KM
    todos = {a12: n, a23: n, a35: n}
    assert f({a12: n, a23: n - 1, a35: n}, {a12: 5.0, a23: 5.0, a35: 5.0}) == V_SIN_MUESTRA
    assert f(todos, {a12: 1.0, a23: -1.0, a35: -1.0}) == ce.V_ANILLOS_LIMPIOS      # 1 a 2 km no cuenta: puede estar contaminado
    assert f(todos, {a12: 1.0, a23: 0.5, a35: -1.0}) == "derrame hasta 3 km"
    assert f(todos, {a12: 1.0, a23: 0.5, a35: 0.2}) == "derrame hasta 5 km"
    assert f(todos, {a12: -1.0, a23: -1.0, a35: 0.2}) == "derrame hasta 5 km"
    assert f({a12: n, a23: n, a35: n - 1}, {a12: 1.0, a23: -1.0, a35: 3.0}) == ce.V_ANILLOS_LIMPIOS   # anillo chico no cuenta
    assert f(todos, {a12: 1.0, a23: 0.0, a35: float("nan")}) == ce.V_ANILLOS_LIMPIOS                # IC bajo cero no es mayor que cero


def test_constantes_de_la_regla_de_d11():
    assert ce.ANIOS_RAMA == (2016, 2023) and ce.BANDAS_RAMA_M == ((0.0, 250.0), (250.0, 1000.0), (1000.0, None))
    assert ce.RAMA_LIMPIA_M == 250.0 and ce.FRACCION_RAMA == 0.5
    assert ce.ANILLOS_KM == ((1.0, 2.0), (2.0, 3.0), (3.0, 5.0)) and ce.KM_ANILLO_LIMPIO == 5.0


# ---- D14: el golpe por distancia entre ramas

def _d14_D():
    n, T = 6, 40
    return {"n": n, "T": T, "t0": 0, "pozo_id": np.arange(100, 100 + n)}


def test_matrices_rama_toma_la_menor_m_min_y_marca_los_cercanos_sin_medir():
    D = _d14_D()
    pares = [(100, 10, 0.5, 300.0), (100, 10, 0.5, 120.0), (101, 11, 1.5, None), (102, 12, 3.0, None), (999, 5, 0.1, 10.0)]
    lat, sin = ce.matrices_rama(D, pares)
    assert lat[0, 10] == 120.0 and np.isnan(lat[1, 11])
    assert sin[1, 11] and not sin[2, 12]   # sin medir pero a 3 km: no cuenta (mas de KM_LIMPIO)


def test_controles_d14_sin_rama_cerca_ni_hijo_cercano_sin_medir():
    D = _d14_D()
    lat = np.full((6, 40), np.nan)
    sin = np.zeros((6, 40), dtype=bool)
    lat[1, 12] = 800.0    # rama a menos de 1 km en la ventana: sale
    lat[2, 12] = 1500.0   # rama lejana: se queda
    sin[3, 14] = True     # hijo cercano sin m_min: sale
    lat[4, 30] = 100.0    # fuera de la ventana [g - 12, g + 6]: se queda
    keep = ce.controles_d14(D, lat, sin, 10, np.array([0, 1, 2, 3, 4]))
    assert keep.tolist() == [True, False, True, False, True]


def test_cohorte_d14_rama_cerca_con_boca_lejos_es_tratado(monkeypatch):
    D = _d14_D()
    lat = np.full((6, 40), np.nan)
    lat[0, 24] = 100.0   # 2016 si t0 = 0 y g // 12 == 2: se prueba con ANIOS_RAMA movido
    lat[1, 24] = 100.0
    lat[1, 20] = 200.0   # rama cercana previa en la ventana: sale
    lat[2, 24] = 400.0   # m_min no menor que 250 m: no es tratado
    monkeypatch.setattr(ce, "ANIOS_RAMA", (2, 2))
    monkeypatch.setattr(ce, "_bases", lambda D: (np.ones((6, 40)), np.ones((6, 40), dtype=bool)))
    monkeypatch.setattr(ce, "_condiciones", lambda D, g, v, m, wells=None: np.ones(len(g), dtype=bool))
    sel, gs = ce.cohorte_d14(D, lat)
    assert sel.tolist() == [0] and gs.tolist() == [24]


def test_solapamiento_cuenta_por_pozo():
    c14 = [{"tratados": np.array([1, 2, 3])}]
    c2 = [{"tratados": np.array([3, 4])}, {"tratados": np.array([5])}]
    assert ce.solapamiento(c14, c2) == (2, 2, 1)


def test_veredicto_d14():
    assert ce.veredicto_d14(MIN_TRATADOS - 1, 50.0) == V_SIN_MUESTRA     # sin muestra: menos de MIN_TRATADOS
    assert ce.veredicto_d14(MIN_TRATADOS, UMBRAL_AGUA_PP + 0.1) == ce.V_D14_SOSTIENE
    assert ce.veredicto_d14(MIN_TRATADOS, UMBRAL_AGUA_PP) == V_NO_FIRME
    assert ce.V_D14_SOSTIENE == "la suba se ve también con el golpe por rama"


def test_seccion_d14_sin_y_con_el_mart():
    import duckdb
    con = duckdb.connect(":memory:")
    assert ce._seccion_d14(con) == []
    cols = ", ".join(f"{n} {t}" for n, t in ce.COLS_D14)
    con.execute(f"create table mart_causal_d14 ({cols})")
    assert ce._seccion_d14(con) == []   # sin filas
    filas = [("D14", "sin muestra", 13.3, 6.2, 23.0, 114, "m", 810, 60), ("D2_2016_2023", "sin veredicto", 15.1, 10.5, 20.3, 290, "m", 1440, 79),
             ("D14_no_D2", "recuento", 65.0, None, None, 65, "m", None, None), ("D2_no_D14", "recuento", 242.0, None, None, 242, "m", None, None),
             ("D14_y_D2", "recuento", 64.0, None, None, 64, "m", None, None)]
    con.executemany("insert into mart_causal_d14 values (?,?,?,?,?,?,?,?,?)", filas)
    txt = "\n".join(ce._seccion_d14(con))
    assert "sin muestra" in txt and "+13,3" in txt and "placebos son los de D2" in txt and ce.SHA_REGLA_D14 in txt


def test_constantes_de_la_regla_de_d14():
    assert (ce.RAMA_TRATADO_M, ce.RAMA_CONTROL_M) == (250.0, 1000.0)
