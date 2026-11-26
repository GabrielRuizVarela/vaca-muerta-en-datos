"""Pruebas de la capa de calculo del lado del hijo dentro del pad (pipeline.hijo_pad)."""
import math

import numpy as np

from pipeline import hijo_pad as hp

LAT0, LON0 = -38.0, -68.5
M = 111_320.0
COS = math.cos(math.radians(38.0))


def _dlon(metros: float) -> float:
    """Grados de longitud que equivalen a la distancia en metros."""
    return metros / (M * COS)


def _dlat(metros: float) -> float:
    """Grados de latitud que equivalen a la distancia en metros."""
    return metros / M


def _pozos(filas: list[dict]) -> dict:
    """Pozos expositores a partir de filas con id, lat, lon, mes_pp y barriles mensuales."""
    P = {"pozo_id": np.array([f["id"] for f in filas]), "lat": np.array([f["lat"] for f in filas]),
         "lon": np.array([f["lon"] for f in filas]), "mes_pp": np.array([f["mes_pp"] for f in filas])}
    P["meses"] = [np.arange(f["mes_pp"], f["mes_pp"] + len(f["bbl"])) for f in filas]
    P["cum"] = [np.concatenate([[0.0], np.cumsum(f["bbl"])]) for f in filas]
    return P


def _hijos(filas: list[dict]) -> dict:
    """Hijos a partir de filas con id, lat, lon, mes_pp, mes_frac y rama."""
    g = lambda k, dt=float: np.array([f[k] for f in filas], dtype=dt)  # noqa: E731
    return {"pozo_id": g("id", int), "y_bbl": g("y_bbl"), "rama": g("rama"), "etapas": g("etapas", int),
            "arena": g("arena"), "lat": g("lat"), "lon": g("lon"), "pad": np.array([f["pad"] for f in filas]),
            "mes_pp": g("mes_pp", int), "mes_frac": g("mes_frac", int)}


def _caso() -> tuple[dict, dict, dict]:
    """Un hijo con su rama y cinco pozos: dos a 500 m, uno a 700 m, uno que empieza tarde y el hijo."""
    hijo = {"id": 1, "lat": LAT0, "lon": LON0, "mes_pp": 102, "mes_frac": 100, "rama": 1000.0,
            "etapas": 30, "arena": 5000.0, "y_bbl": 90000.0, "pad": "p1", "bbl": [10.0] * 12,
            "lon_rama": [LON0, LON0 + _dlon(800)], "lat_rama": [LAT0, LAT0]}
    a = {"id": 2, "lat": LAT0 + _dlat(500), "lon": LON0 + _dlon(100), "mes_pp": 90, "bbl": [100.0] * 20,
         "lon_rama": [LON0 + _dlon(100), LON0 + _dlon(700)], "lat_rama": [LAT0 + _dlat(500)] * 2,
         "unidad": 3, "pad": "p2"}
    b = {"id": 3, "lat": LAT0 + _dlat(700), "lon": LON0 + _dlon(100), "mes_pp": 90, "bbl": [1000.0] * 20,
         "lon_rama": [LON0 + _dlon(100), LON0 + _dlon(700)], "lat_rama": [LAT0 + _dlat(700)] * 2,
         "unidad": 3, "pad": "p2"}
    c = {"id": 4, "lat": LAT0 + _dlat(200), "lon": LON0 + _dlon(900), "mes_pp": 120, "bbl": [50.0] * 12,
         "lon_rama": [LON0 + _dlon(900), LON0 + _dlon(1500)], "lat_rama": [LAT0 + _dlat(200)] * 2,
         "unidad": 5, "pad": "p2"}
    d = {"id": 5, "lat": LAT0 - _dlat(500), "lon": LON0 + _dlon(100), "mes_pp": 90, "bbl": [100.0] * 20,
         "lon_rama": [LON0 + _dlon(100), LON0 + _dlon(700)], "lat_rama": [LAT0 - _dlat(500)] * 2,
         "unidad": 4, "pad": "p1"}
    H = _hijos([hijo])
    P = _pozos([hijo, a, b, c, d])
    ramas = {f["id"]: {"lon": np.array(f["lon_rama"]), "lat": np.array(f["lat_rama"]),
                       "unidad": f.get("unidad", 3), "pad": f["pad"]} for f in [hijo, a, b, c, d]}
    return H, P, ramas


def test_pares_rama_descarta_el_pozo_lejano_y_el_propio_hijo():
    """Solo entran los ancestros a menos de 600 m y nunca el hijo consigo mismo."""
    H, P, ramas = _caso()
    i, j = hp.pares_rama(H, P, ramas, 600.0)
    Pr = hp.p_con_rama(P, ramas)
    assert set(Pr["pozo_id"][j].tolist()) == {2, 4, 5}
    assert 1 not in Pr["pozo_id"][j].tolist()
    assert 3 not in Pr["pozo_id"][j].tolist()          # el de 700 m queda afuera
    assert len(i) == 3


def test_exposiciones_en_barriles_por_metro():
    """E suma lo producido antes de la fractura, Ec lo que empieza despues de la ventana."""
    H, P, ramas = _caso()
    i, j = hp.pares_rama(H, P, ramas, 600.0)
    Pr = hp.p_con_rama(P, ramas)
    ex = hp.exposiciones(H, Pr, ramas, i, j)
    # el expositor de 500 m (1000 bbl antes de la fractura) y el del mismo pad (1000 bbl), sobre 1000 m de rama
    assert ex["E"][0] == 2.0
    # control negativo: el que empieza en el mes 120, 600 bbl hasta el ultimo mes con datos
    assert ex["Ec"][0] == 0.6
    # sin los expositores del propio pad del hijo queda solo el de 500 m
    assert ex["E_otros"][0] == 1.0
    assert ex["Ec_otros"][0] == 0.6
    # solo la misma unidad valida (3): el de 500 m
    assert ex["E_unidad"][0] == 1.0
    assert ex["Ec_unidad"][0] == 0.0
    # la parte de la exposicion que viene de la misma unidad
    assert ex["misma_unidad_frac"][0] == 0.5


def test_el_ajuste_dentro_del_pad_recupera_el_efecto():
    """Con grandes diferencias entre pads, el modelo con efectos fijos da 3 y el agrupado no."""
    pads = np.array(["p1"] * 4 + ["p2"] * 4 + ["p3"] * 4 + ["p4"] * 4)
    E = np.array([10.0, 40.0, 70.0, 100.0, 20.0, 50.0, 80.0, 110.0,
                  5.0, 35.0, 65.0, 95.0, 15.0, 45.0, 75.0, 105.0])
    Offsets = {"p1": 1000.0, "p2": -500.0, "p3": 2500.0, "p4": -3000.0}
    y = 3.0 * E / 100.0 + np.array([Offsets[p] for p in pads])
    X = (E / 100.0).reshape(-1, 1)
    aj = hp.ajuste_pad(y, X, pads)
    assert abs(aj["beta"] - 3.0) < 1e-8
    assert aj["n"] == 16
    assert aj["pads"] == 4
    # el ajuste sin efectos fijos de pad no recupera el pendiente
    agrupado = float(np.linalg.lstsq(X, y, rcond=None)[0][0])
    assert abs(agrupado - 3.0) > 1.0


def test_bootstrap_por_pads_es_determinista_y_cubre_el_pendiente():
    """El bootstrap devuelve una pendiente por repeticion, es reproducible y su IC cubre el valor."""
    rng = np.random.default_rng(7)
    pads = np.repeat([f"p{i}" for i in range(30)], 8)
    x = rng.normal(size=240) * 5.0 + np.repeat(np.arange(30), 8) * 0.1
    y = 2.0 * x + rng.normal(size=240) * 0.5 + np.repeat(np.arange(30), 8) * 7.0
    X = x.reshape(-1, 1)
    b1 = hp.bootstrap_pads(y, {"m": X}, pads, 300, 11)
    b2 = hp.bootstrap_pads(y, {"m": X}, pads, 300, 11)
    assert len(b1["m"]) == 300
    assert np.allclose(b1["m"], b2["m"])
    lo, hi = hp.ic95(b1["m"])
    assert lo < 2.0 < hi


def test_veredictos_de_la_regla():
    """Un caso de cada veredicto, con el orden del encabezado."""
    V = 100.0
    assert hp.veredicto(-5.0, -8.0, -2.0, -1.0, 1.0, V, 200) == "sostiene degradación"
    assert hp.veredicto(-1.0, -3.0, 1.0, -1.0, 1.0, V, 200) == "no se ve degradación"
    assert hp.veredicto(-1.0, -3.0, 1.0, 2.0, 5.0, V, 200) == "ubicación"
    assert hp.veredicto(-50.0, -60.0, 10.0, -1.0, 1.0, V, 200) == "no firme"
    assert hp.veredicto(-1.0, -3.0, 1.0, -1.0, 1.0, V, 99) == "sin muestra"
    assert hp.veredicto(float("nan"), -3.0, 1.0, -1.0, 1.0, V, 200) == "sin muestra"


def test_el_borde_del_5_por_ciento():
    """Con V = 100, el alto del intervalo en 5 deja de ser "no se ve degradación"."""
    V = 100.0
    assert hp.veredicto(-1.0, -3.0, 0.05 * V, -1.0, 1.0, V, 200) == "no se ve degradación"
    assert hp.veredicto(-1.0, -3.0, 0.0501 * V, -1.0, 1.0, V, 200) == "no firme"


def test_pads_informativos_con_dispersion_49_y_50():
    """Un pad con dispersion de 49 no es informativo y uno de 50 si."""
    E = np.array([0.0, 49.0, 10.0, 60.0])
    pad = np.array(["p1", "p1", "p2", "p2"])
    assert hp.pads_informativos(E, pad) == 1


def test_virgen_cae_a_toda_la_muestra_con_menos_de_50_virgenes():
    """Con menos de 50 hijos sin exposicion, V es la mediana de toda la muestra."""
    y = np.array([10.0, 20.0, 100.0])
    E = np.array([0.0, 5.0, 7.0])
    V, n, ref = hp.virgin(y, E)
    assert n == 1
    assert ref == "toda la muestra"
    assert V == 20.0
    y2 = np.concatenate([np.zeros(50), [100.0]])
    E2 = np.concatenate([np.zeros(50), [1.0]])
    V2, n2, ref2 = hp.virgin(y2, E2)
    assert (n2, ref2, V2) == (50, "virgen", 0.0)


def test_cota_sin_extremo_bajo_finito_no_es_cero():
    c = hp.cota(float("nan"), 85.8, 388.0)
    assert all(np.isnan(v) for v in c.values())
    assert hp.cota(0.2, 85.8, 388.0)["cota_bbl_m"] == 0.0


def test_cota_con_lo_positivo_da_cero():
    """Si el extremo bajo del intervalo es positivo, la cota de perdida es cero."""
    c = hp.cota(2.0, 100.0, 50.0)
    assert c["cota_bbl_m"] == 0.0
    assert c["cota_pct"] == 0.0
    assert c["cota_a_mediana_bbl_m"] == 0.0
    c2 = hp.cota(-4.0, 100.0, 50.0)
    assert c2["cota_bbl_m"] == 4.0
    assert c2["cota_pct"] == 4.0
    assert c2["cota_a_mediana_bbl_m"] == 2.0


def test_el_diseno_trae_los_controles_del_encabezado():
    """La matriz de controles trae la rama, los indicadores de unidad y la fraccion de misma unidad."""
    H, P, ramas = _caso()
    H = dict(H)
    H["pozo_id"] = np.array([1, 2, 3])
    H["rama"] = np.array([1000.0, 1200.0, 900.0])
    H["pad"] = np.array(["p1", "p1", "p1"])
    H["mes_frac"] = np.array([100, 100, 112])
    C, nombres = hp.diseno(H, ramas, {"misma_unidad_frac": np.array([1.0, 0.0, 0.5])})
    assert nombres[0] == "rama_horizontal_m"
    assert "misma_unidad_frac" in nombres
    assert "meses_desde_primera_fractura_pad" in nombres
    assert C[0, nombres.index("misma_unidad_frac")] == 1.0
    assert C[2, nombres.index("meses_desde_primera_fractura_pad")] == 12.0


# ------------------------------------------------------------------ la pagina

def _con_marts(veredicto="no se ve degradación", lo=-0.757, hi=1.055, lo_c=-0.144, hi_c=0.949, cota=0.757, cota_pct=0.882, toda_muestra=False):
    import duckdb

    from pipeline.costo import _escribir
    con = duckdb.connect(":memory:")
    cob = [("hijo", a, 0, 0, 100, 100, 90 if a <= 2023 else 40) for a in range(2016, 2026)]
    _escribir(con, "mart_trayectoria_cobertura", [("nivel", "varchar"), ("anio", "integer"), ("total", "integer"), ("medidos", "integer"),
                                                  ("horizontales", "integer"), ("horizontales_en_fuente", "integer"),
                                                  ("horizontales_medidos", "integer")], cob)
    filas = []
    for modelo in ("principal",) + hp.MODELOS_DESCRIPTIVOS:
        for tipo in ("real", "control"):
            es_p = modelo == "principal" and tipo == "real"
            b, l_, h_ = (0.1, lo, hi) if tipo == "real" else (0.35, lo_c, hi_c)
            filas.append((modelo, tipo, hp.TERMINO, b, l_, h_, 850, 234, 132, 0.1, 0.2, 0.3, 85.8, veredicto if es_p else None))
    _escribir(con, "mart_hijo_pad_coef", hp.COLS_COEF, filas)
    _escribir(con, "mart_hijo_pad_muestra", hp.COLS_MUESTRA,
              [(k, f"paso {k}", 1000 - k, None if k < 6 else 200 - k) for k in range(1, 9)])
    resumen = {"virgen_mediana_bbl_m": 85.8, "virgenes_n": 328.0, "pads": 234.0, "pads_informativos": 132.0,
               "dispersion_mediana_bbl_m": 269.0, "parte_E_cero": 0.386, "expo_positiva_mediana_bbl_m": 388.0,
               "cota_bbl_m": cota, "cota_pct": cota_pct, "cota_a_mediana_bbl_m": 2.9,
               "virgen_referencia_toda_muestra": 1.0 if toda_muestra else 0.0}
    _escribir(con, "mart_hijo_pad_resumen", hp.COLS_RESUMEN, list(resumen.items()))
    _escribir(con, "mart_hijo_pad_equilibrio", hp.COLS_EQUILIBRIO,
              [("rama_horizontal_m", -44.0, -64.0, -26.0, 850, 234), ("etapas", -0.8, -1.1, -0.5, 850, 234),
               ("arena_tn_por_m", -0.005, -0.014, 0.002, 850, 234),
               ("meses_desde_primera_fractura_pad", 0.2, 0.01, 0.6, 850, 234)])
    _escribir(con, "mart_hijo_pad_anio", hp.COLS_ANIO, [(a, 100, 30, 50) for a in range(2016, 2024)])
    return con


def test_la_pagina_dice_cuando_el_rendimiento_de_referencia_es_toda_la_muestra():
    normal = hp.pagina_hijo_pad(_con_marts())
    assert "Rendimiento de los hijos sin exposición a 12 meses" in normal
    assert "de toda la muestra" not in normal.split("## Muestra")[0]
    txt = hp.pagina_hijo_pad(_con_marts(toda_muestra=True))
    assert "Rendimiento de referencia a 12 meses: mediana de 85,8 bbl por metro de rama de toda la muestra" in txt
    assert "Rendimiento de los hijos sin exposición a 12 meses" not in txt


def test_la_cobertura_de_ramas_es_la_de_la_tabla_de_trayectorias():
    con = _con_marts()
    cmin, cmax, c24, c25 = hp.cobertura_rama(con)
    assert (cmin, cmax) == (90.0, 90.0)
    assert (c24, c25) == (40.0, 40.0)


def test_la_pagina_sale_de_los_marts_sin_guiones_largos():
    txt = hp.pagina_hijo_pad(_con_marts())
    assert chr(0x2013) not in txt and chr(0x2014) not in txt
    assert "**no se ve degradación**" in txt and "no es que no haya degradación" in txt
    assert "entre 90% y 90% de los hijos horizontales fracturados de 2016 a 2023, pero solo 40% de los de 2024 y 40% de los de 2025" in txt
    assert "0,8 bbl por metro de rama por cada 100 bbl por metro de exposición, o 0,9% del rendimiento virgen" in txt
    assert "Es una asociación dentro del pad" in txt
    assert "Variables que cambian con la exposición dentro del pad, con IC que excluye cero: Rama horizontal (m), Etapas, " \
           "Meses desde la primera fractura del pad." in txt
    # todos los modelos con su control negativo en la tabla de coeficientes
    assert txt.count("| real |") + txt.count("| control negativo |") == 2 * (1 + len(hp.MODELOS_DESCRIPTIVOS))


def test_la_pagina_dice_cota_cero_y_el_control_de_la_misma_unidad():
    con = _con_marts(veredicto="no firme", lo=0.2, hi=1.0, cota=0.0, cota_pct=0.0)
    con.execute("update mart_hijo_pad_coef set ic_bajo = 0.5, ic_alto = 2.0 where modelo = 'misma_unidad' and exposicion = 'control'")
    txt = hp.pagina_hijo_pad(con)
    assert "**no firme**" in txt
    assert "la cota superior es cero: todo el IC está por encima de cero" in txt
    assert "En el modelo de la misma unidad el control excluye cero" in txt


def test_cada_veredicto_tiene_su_texto_propio():
    textos = {v: hp._texto_veredicto(v, 0.1, -0.7, 1.0, -0.1, 0.9, 85.8) for v in hp.VEREDICTOS}
    assert len(set(textos.values())) == len(hp.VEREDICTOS)
    assert all(t.strip() for t in textos.values())
