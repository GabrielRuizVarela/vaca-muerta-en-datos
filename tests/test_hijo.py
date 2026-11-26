import numpy as np

from pipeline import hijo as hj

LAT0, LON0 = -38.0, -68.5
SALTO_PAD = 0.05            # grados entre pads (unos 5,5 km): solo los de la misma pareja quedan a menos de 1 km
D_MADRE, D_FUTURO = 0.0054, -0.0045   # unos 0,6 km y 0,5 km del pad hijo


def _pozos(filas: list[dict]) -> dict:
    """Pozos expositores a partir de filas con id, lat, lon, mes_pp y barriles mensuales."""
    P = {"pozo_id": np.array([f["id"] for f in filas]), "lat": np.array([f["lat"] for f in filas]),
         "lon": np.array([f["lon"] for f in filas]), "mes_pp": np.array([f["mes_pp"] for f in filas])}
    P["meses"] = [np.arange(f["mes_pp"], f["mes_pp"] + len(f["bbl"])) for f in filas]
    P["cum"] = [np.concatenate([[0.0], np.cumsum(f["bbl"])]) for f in filas]
    return P


def _hijos(filas: list[dict]) -> dict:
    n = len(filas)
    g = lambda k, dt=float: np.array([f[k] for f in filas], dtype=dt)  # noqa: E731
    return {"pozo_id": g("id", int), "operador": np.array(["YPF"] * n), "cohorte": g("mes_pp", int) // 12,
            "y_bbl": g("y_bbl"), "rama": g("rama"), "etapas": g("etapas"), "arena": g("arena"), "area": np.array(["A"] * n),
            "lat": g("lat"), "lon": g("lon"), "pad": np.array([f["pad"] for f in filas]), "mes_pp": g("mes_pp", int),
            "mes_frac": g("mes_frac", int)}


def test_la_exposicion_excluye_pozos_posteriores_a_la_fractura():
    frac, pp = 100, 102
    hijo = {"id": 1, "lat": LAT0, "lon": LON0, "mes_pp": pp, "mes_frac": frac, "rama": 2500.0, "etapas": 30.0, "arena": 5000.0,
            "y_bbl": 1.0, "pad": "p1", "bbl": [10.0] * 12}
    previo = {"id": 2, "lat": LAT0 + 0.004, "lon": LON0, "mes_pp": 90, "bbl": [100.0] * 20}    # meses 90 a 109
    empieza_en_el_mes = {"id": 3, "lat": LAT0 - 0.004, "lon": LON0, "mes_pp": frac, "bbl": [999.0] * 12}
    posterior = {"id": 4, "lat": LAT0, "lon": LON0 + 0.004, "mes_pp": frac + 1, "bbl": [555.0] * 12}
    tardio = {"id": 5, "lat": LAT0, "lon": LON0 - 0.004, "mes_pp": pp + 20, "bbl": [7.0] * 12}
    lejos = {"id": 6, "lat": LAT0 + 0.05, "lon": LON0, "mes_pp": 80, "bbl": [1e6] * 12}
    P = _pozos([hijo, previo, empieza_en_el_mes, posterior, tardio, lejos])
    H = _hijos([hijo])
    i, j = hj.pares(H, P)
    assert set(P["pozo_id"][j]) == {2, 3, 4, 5}            # ni el propio pozo ni el que esta a 5,5 km
    # real: solo el previo y solo hasta el mes anterior a la fractura (meses 90 a 99, diez meses)
    assert hj.exposicion_real(H, P, i, j)[0] == 10 * 100.0
    # control: solo el que empieza despues de la ventana (primer petroleo mas 11 meses): el tardio
    assert hj.exposicion_control(H, P, i, j)[0] == 12 * 7.0


def test_un_pozo_que_empieza_dentro_de_la_ventana_no_es_control_negativo():
    hijo = {"id": 1, "lat": LAT0, "lon": LON0, "mes_pp": 102, "mes_frac": 100, "rama": 2500.0, "etapas": 30.0, "arena": 5000.0,
            "y_bbl": 1.0, "pad": "p1", "bbl": [10.0] * 12}
    dentro = {"id": 2, "lat": LAT0 + 0.004, "lon": LON0, "mes_pp": 113, "bbl": [50.0] * 12}    # ultimo mes de la ventana: 113
    fuera = {"id": 3, "lat": LAT0 - 0.004, "lon": LON0, "mes_pp": 114, "bbl": [60.0] * 12}
    P, H = _pozos([hijo, dentro, fuera]), _hijos([hijo])
    i, j = hj.pares(H, P)
    assert hj.exposicion_control(H, P, i, j)[0] == 12 * 60.0


def test_la_distancia_de_superficie_corta_en_1_km():
    la, lo = np.array([LAT0]), np.array([LON0])
    # 0,009 grados de latitud son 1,002 km; 0,0089 son 0,991 km
    i, _ = hj.vecinos(la, lo, np.array([LAT0 + 0.0089, LAT0 + 0.009]), np.array([LON0, LON0]), 1.0)
    assert len(i) == 1


def test_cortes_en_modo_virgen_y_en_modo_terciles():
    e = np.concatenate([np.zeros(60), np.arange(1.0, 101.0)])
    modo, bajo, alto = hj.cortes(e)
    assert (modo, bajo, alto) == ("virgen", 0.0, 50.5)
    g = hj.grupos(e, (modo, bajo, alto))
    assert (g == 1).sum() == 60 and (g == 2).sum() == 50 and (g == 3).sum() == 50
    pocos = np.concatenate([np.zeros(10), np.arange(1.0, 101.0)])
    modo, bajo, alto = hj.cortes(pocos)
    assert modo == "terciles"
    g = hj.grupos(pocos, (modo, bajo, alto))
    assert abs((g == 1).sum() - 37) <= 1 and abs((g == 3).sum() - 36) <= 2


def _mundo(penalizacion: float, ubicacion: float, futuros: str, semilla: int = 5) -> dict:
    """Mundo sintetico. 60 pads hijo aislados (virgenes) y 90 pads hijo con un pozo madre a 0,6 km que produjo antes de la
    fractura; cada pad tiene 2 hijos. Un hijo con madre de volumen alto (la mitad superior) pierde `penalizacion` bbl por metro
    (depleccion); un hijo del nucleo (con madre) cambia `ubicacion` bbl por metro sea cual sea el volumen. `futuros`: 'azar' pone
    un pozo posterior a 0,5 km en la mitad de los pads de cualquier tipo; 'nucleo' lo pone en todos los pads con madre."""
    rng = np.random.default_rng(semilla)
    pozos, hijos = [], []
    vol = rng.uniform(500, 3000, 90)
    alto = vol > np.median(vol)
    nid = 0
    for k in range(150):
        t0 = 12 * (2018 + k % 3) + 3
        lat = LAT0 + k * SALTO_PAD
        madre = k >= 60
        if madre:
            v = vol[k - 60]
            pozos.append({"id": 10000 + k, "lat": lat + D_MADRE, "lon": LON0, "mes_pp": t0, "bbl": [v] * 18})
        if futuros == "nucleo":
            tiene_futuro = madre
        else:
            tiene_futuro = bool(rng.random() < 0.5)
        if tiene_futuro:
            pozos.append({"id": 20000 + k, "lat": lat + D_FUTURO, "lon": LON0, "mes_pp": t0 + 40,
                          "bbl": [rng.uniform(500, 3000)] * 12})
        for h in range(2):
            nid += 1
            y_m = 100 + rng.normal(0, 8) + (ubicacion if madre else 0.0) - (penalizacion if madre and alto[k - 60] else 0.0)
            f = {"id": nid, "lat": lat, "lon": LON0, "mes_pp": t0 + 16, "mes_frac": t0 + 14, "rama": 2500.0, "etapas": 30.0,
                 "arena": 9000.0, "y_bbl": y_m * 2500.0, "pad": f"p{k}", "bbl": [10.0] * 12}
            hijos.append(f)
            pozos.append({"id": nid, "lat": lat, "lon": LON0, "mes_pp": t0 + 16, "bbl": [10.0] * 12})
    return {"H": _hijos(hijos), "P": _pozos(pozos),
            "pasos": [("sintetico", len(hijos))]}


def test_una_penalizacion_de_depleccion_se_recupera_con_el_signo_correcto():
    R = hj.calcular(_mundo(penalizacion=20.0, ubicacion=0.0, futuros="azar"))
    prin = next(r for r in R["coef"] if r[0] == "principal" and r[1] == "muy_depletado")
    ctrl = next(r for r in R["coef"] if r[0] == "control_negativo" and r[1] == "muy_depletado")
    assert R["cortes"][0] == "virgen"
    assert prin[5] < 0 and prin[4] < -20 < prin[5]           # IC por debajo de cero que contiene la penalizacion
    assert abs(prin[2] + 20) < 6
    assert hj.nulo(ctrl[4], ctrl[5])
    assert R["veredicto"] == "sostiene"
    assert prin[12] == "sostiene"                              # el veredicto queda en la fila del modelo principal
    assert abs(prin[3] - 100 * prin[2] / prin[11]) < 1e-9      # porcentaje del virgen


def test_sin_efecto_el_veredicto_es_que_no_se_sostiene():
    R = hj.calcular(_mundo(penalizacion=0.0, ubicacion=0.0, futuros="azar"))
    prin = next(r for r in R["coef"] if r[0] == "principal" and r[1] == "muy_depletado")
    assert hj.nulo(prin[4], prin[5]) and abs(prin[2]) < 0.05 * prin[11]
    assert R["veredicto"] == "no se sostiene"


def test_un_efecto_de_ubicacion_vuelve_no_nulo_el_control_negativo_y_el_veredicto_dice_ubicacion():
    R = hj.calcular(_mundo(penalizacion=0.0, ubicacion=-15.0, futuros="nucleo"))
    prin = next(r for r in R["coef"] if r[0] == "principal" and r[1] == "muy_depletado")
    ctrl = next(r for r in R["coef"] if r[0] == "control_negativo" and r[1] == "muy_depletado")
    assert prin[5] < 0                                         # el hijo del nucleo rinde menos sin que haya depleccion
    assert not hj.nulo(ctrl[4], ctrl[5]) and ctrl[2] < 0       # los pozos posteriores no depletaron nada y dan efecto
    assert R["veredicto"] == "ubicacion"


def test_el_calculo_es_determinista():
    a = hj.calcular(_mundo(penalizacion=10.0, ubicacion=-5.0, futuros="azar", semilla=9))
    b = hj.calcular(_mundo(penalizacion=10.0, ubicacion=-5.0, futuros="azar", semilla=9))
    assert repr(a) == repr(b)   # repr: los NaN de un subconjunto vacio no son iguales entre si


def _fila(coef, lo, hi, virgen=100.0):
    return ("m", "muy_depletado", coef, 100 * coef / virgen, lo, hi, 500, 100, 0.5, 0.0, 0.0, virgen, None)


def test_veredicto_sigue_la_regla_fijada():
    ok = dict(n_virgen=300, pads_virgen=80, n_muy=300, pads_muy=60, pads=200)
    nulo_c = _fila(1.0, -4.0, 6.0)
    assert hj.veredicto(_fila(0.5, -5.0, 6.0), nulo_c, **ok) == "no se sostiene"
    assert hj.veredicto(_fila(-12.0, -20.0, -4.0), nulo_c, **ok) == "sostiene"
    assert hj.veredicto(_fila(-12.0, -20.0, -4.0), _fila(8.0, 2.0, 14.0), **ok) == "ubicacion"
    assert hj.veredicto(_fila(0.5, -5.0, 6.0), _fila(8.0, 2.0, 14.0), **ok) == "no firme"       # falsar exige control nulo
    assert hj.veredicto(_fila(-7.0, -15.0, 1.0), nulo_c, **ok) == "no firme"                    # IC con cero y 5% o mas
    assert hj.veredicto(_fila(9.0, 2.0, 16.0), nulo_c, **ok) == "no firme"                      # rinde mas, no menos
    assert hj.veredicto(_fila(0.5, -5.0, 6.0), nulo_c, **{**ok, "n_muy": 49}) == "sin muestra"
    assert hj.veredicto(_fila(0.5, -5.0, 6.0), nulo_c, **{**ok, "pads_virgen": 19}) == "sin muestra"
    assert hj.veredicto(_fila(0.5, -5.0, 6.0), nulo_c, **{**ok, "pads": 99}) == "sin muestra"


def test_ols_con_celdas_recupera_el_coeficiente_y_el_error_agrupado_es_positivo():
    rng = np.random.default_rng(3)
    n = 400
    pad = np.repeat(np.arange(100), 4)
    celda = np.array([f"c{k % 5}" for k in range(n)])
    x = rng.normal(0, 1, n)
    y = 3.0 * x + (np.arange(n) % 5) * 10 + rng.normal(0, 1, n)
    r = hj.ols_celdas(y, x[:, None], celda, pad)
    assert abs(r["beta"][0] - 3.0) < 0.2
    assert 0 < r["se"][0] < 0.2 and r["pads"] == 100 and r["celdas"] == 5
