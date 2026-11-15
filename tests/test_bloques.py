import numpy as np

from pipeline import bloques as bl
from pipeline import placebo


def _punto(x_km: float, y_km: float) -> tuple[float, float]:
    """(lat, lon) del punto que la proyeccion de pipeline.bloques lleva a (x_km, y_km)."""
    lon = bl.LON0 + x_km / (bl.KM_POR_GRADO * np.cos(np.radians(bl.LAT0)))
    lat = bl.LAT0 + y_km / bl.KM_POR_GRADO
    return lat, lon


def _clave(puntos, tam):
    lat, lon = zip(*[_punto(*p) for p in puntos])
    return bl.clave_bloque(np.array(lat), np.array(lon), tam)


def test_proyeccion_ida_y_vuelta():
    x, y = bl.proyectar(np.array([_punto(3.0, -7.0)[0]]), np.array([_punto(3.0, -7.0)[1]]))
    assert np.allclose([x[0], y[0]], [3.0, -7.0])


def test_clave_de_bloque_en_una_grilla():
    # 2 km: (0,5; 0,5) y (1,9; 1,9) comparten celda; (2,1; 0,5) cambia de columna; (-0,1; 0,1) cae en la columna -1
    c2 = _clave([(0.5, 0.5), (1.9, 1.9), (2.1, 0.5), (-0.1, 0.1), (0.5, 2.1)], 2.0)
    assert c2[0] == c2[1]
    assert len({c2[0], c2[2], c2[3], c2[4]}) == 4
    # 5 km: las tres primeras comparten celda; la del x negativo no
    c5 = _clave([(0.5, 0.5), (1.9, 1.9), (2.1, 0.5), (-0.1, 0.1), (4.9, 4.9), (5.1, 0.5)], 5.0)
    assert c5[0] == c5[1] == c5[2] == c5[4]
    assert c5[3] != c5[0] and c5[5] != c5[0]


def test_clave_de_bloque_es_entera_y_estable():
    pts = [(1.0, 1.0), (7.5, 3.2), (-12.3, 40.0)]
    a, b = _clave(pts, 2.0), _clave(pts, 2.0)
    assert a.dtype == np.int64 and (a == b).all() and len(set(a.tolist())) == 3
    assert (a >= 0).all()


def _sintetico(n_celdas: int = 60, pads_por_celda: int = 4, eventos_por_pad: int = 6, sd_celda: float = 0.15, semilla: int = 3):
    """Pads agrupados en celdas de 5 km. El efecto sobre los cercanos tiene un componente compartido por celda (ruido espacial)."""
    rng = np.random.default_rng(semilla)
    lat, lon = [], []
    for c in range(n_celdas):
        x0, y0 = 5.0 * (c % 10) + 0.5, 5.0 * (c // 10) + 0.5
        for p in range(pads_por_celda):
            la, lo = _punto(x0 + 3.5 * rng.random(), y0 + 3.5 * rng.random())
            lat.append(la)
            lon.append(lo)
    lat, lon = np.array(lat), np.array(lon)
    D = {"bloque_2km": bl.clave_bloque(lat, lon, 2.0), "bloque_5km": bl.clave_bloque(lat, lon, 5.0)}
    n_pad = len(lat)
    clave = np.repeat(np.arange(n_pad), eventos_por_pad)
    celda = D["bloque_5km"][clave]
    efecto_celda = dict(zip(np.unique(D["bloque_5km"]), rng.normal(0, sd_celda, len(np.unique(D["bloque_5km"])))))
    banda = np.tile([0, 0, 0, 2, 2, 2], n_pad)
    y = 1.0 + rng.normal(0, 0.03, len(clave)) + np.where(banda == 0, -0.2 + np.array([efecto_celda[c] for c in celda]), 0.0)
    return D, clave, banda, y


def test_bloques_de_5_km_juntan_los_pads_de_una_celda():
    D, clave, banda, y = _sintetico()
    cl = bl.claves(D, clave)
    assert len(np.unique(cl["pad"])) == 240
    assert len(np.unique(cl["5km"])) == 60
    assert len(np.unique(cl["2km"])) > len(np.unique(cl["5km"]))


def test_ruido_espacial_ensancha_el_ic_por_bloques():
    D, clave, banda, y = _sintetico()
    cl = bl.claves(D, clave)
    r = {u: placebo.brecha_ic(y, banda, cl[u], 150, 11) for u in cl}
    ancho = {u: r[u]["ic_alto"] - r[u]["ic_bajo"] for u in r}
    assert ancho["5km"] > 1.4 * ancho["pad"]
    assert ancho["2km"] > ancho["pad"]
    assert r["pad"]["brecha"] == r["5km"]["brecha"] == r["2km"]["brecha"]  # la estimacion puntual no cambia con la unidad


def test_sin_ruido_espacial_los_anchos_son_parecidos():
    D, clave, banda, y = _sintetico(sd_celda=0.0)
    cl = bl.claves(D, clave)
    r = {u: placebo.brecha_ic(y, banda, cl[u], 150, 11) for u in cl}
    a_pad, a_5 = (r[u]["ic_alto"] - r[u]["ic_bajo"] for u in ("pad", "5km"))
    assert 0.5 < a_5 / a_pad < 2.0


def test_deterministico():
    D, clave, banda, y = _sintetico()
    cl = bl.claves(D, clave)
    a = placebo.brecha_ic(y, banda, cl["5km"], 80, 5)
    b = placebo.brecha_ic(y, banda, cl["5km"], 80, 5)
    assert a == b
    y1, ym1 = y, y + 0.01
    d1 = bl.brecha_descontada_ic(y1, ym1, banda, cl["5km"], 60, 5)
    d2 = bl.brecha_descontada_ic(y1, ym1, banda, cl["5km"], 60, 5)
    assert d1 == d2
    assert np.isclose(d1["estimacion"], placebo.brecha(y1, banda)[2] - placebo.brecha(ym1, banda)[2])


def _fila(metrica, k, est, lo5, hi5, b5=100, estimador="mediana"):
    return {"metrica": metrica, "k": k, "estimador": estimador, "estimacion": est, "ic_bajo_5km": lo5, "ic_alto_5km": hi5,
            "bloques_5km": b5}


def test_r1_no_cruza_deja_el_rango():
    f = [_fila(bl.M_HEADLINE, 1, -0.23, -0.29, -0.17), _fila(bl.M_DESCONTADA, 1, -0.19, -0.26, -0.14)]
    assert bl.veredicto_r1(f) == {"estado": "no cruza", "cruza": False, "rango": None}


def test_r1_cruza_reescribe_el_rango_con_los_dos_extremos():
    f = [_fila(bl.M_HEADLINE, 1, -0.23, -0.35, -0.08), _fila(bl.M_DESCONTADA, 1, -0.19, -0.30, -0.05)]
    r = bl.veredicto_r1(f)
    assert r["cruza"] and r["rango"] == (5, 35)


def test_r1_con_pocos_bloques_no_reemplaza():
    f = [_fila(bl.M_HEADLINE, 1, -0.23, -0.35, -0.08, b5=29), _fila(bl.M_DESCONTADA, 1, -0.19, -0.30, -0.05, b5=29)]
    assert bl.veredicto_r1(f)["estado"] == "sin bloques"


def test_r2_usa_la_regla_de_sincronia_con_el_ic_de_bloques():
    grupos = [(b, 0.1, 0.9, 100, -0.1, -0.2, 0.0, 100) for b in (1, 2, 3)]
    firme = [_fila(bl.M_PEND, 0, -0.2, -0.35, -0.08, estimador="pendiente"), _fila(bl.M_PEND, -1, -0.06, -0.19, 0.05, estimador="pendiente")]
    assert bl.veredicto_r2(firme, grupos) == "sostiene"
    debil = [_fila(bl.M_PEND, 0, -0.2, -0.35, -0.01, estimador="pendiente"), firme[1]]
    assert bl.veredicto_r2(debil, grupos) == "no firme"
    plana = [_fila(bl.M_PEND, 0, -0.2, -0.35, 0.02, estimador="pendiente"), firme[1]]
    assert bl.veredicto_r2(plana, grupos) == "plana"
    pocos = [_fila(bl.M_PEND, 0, -0.2, -0.35, -0.08, b5=10, estimador="pendiente"), firme[1]]
    assert bl.veredicto_r2(pocos, grupos) == "sin bloques"


def test_fila_calcula_la_razon_de_anchos():
    f = bl._fila("m", 1, "mediana", -0.2, {"pad": (-0.3, -0.1), "2km": (-0.32, -0.08), "5km": (-0.4, 0.0)}, 100, 50, 20)
    assert f[0] == "m" and f[3] == -0.2
    assert np.isclose(f[-2], 1.2) and np.isclose(f[-1], 2.0)
    assert len(f) == len(bl.COLS_BLOQUES)


def test_linea_de_pruebas_suma_las_partes():
    c = {"hipotesis": 9, "robustez": 13, "descomposicion": 141, "hijo": 9, "bloques": 13, "total": 185}
    s = bl.linea_pruebas(c)
    assert "185" in s and "9 intervalos descriptivos del lado del hijo" in s and "141" in s and "\u2014" not in s and "\u2013" not in s
