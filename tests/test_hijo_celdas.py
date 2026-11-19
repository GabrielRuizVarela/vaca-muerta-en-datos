"""Pruebas de pipeline.hijo_celdas con un mundo sintetico donde la ubicacion y la depleccion se pueden separar."""
import math
import re

import duckdb
import numpy as np

from pipeline import hijo as hj
from pipeline import hijo_celdas as hc
from pipeline.costo import _escribir
from tests.test_hijo import _hijos, _pozos

LON0 = -68.5
DASHES = re.compile("[\u2013\u2014]")


def _lat_celda(k: int) -> float:
    """Latitud a 0,5 km del borde sur de una celda de 2 km, con celdas separadas por unos 5,5 km: los pozos de una celda
    (desplazados hasta 0,6 km al norte) quedan en la misma celda y a mas de 1 km de las otras."""
    y0 = math.floor(hc.KM_GRADO * (-38.0 + 0.05 * k) / hc.LADO_KM) * hc.LADO_KM
    return (y0 + 0.5) / hc.KM_GRADO


def _mundo(n_celdas: int, penalizacion: float, ubicacion: float, semilla: int = 3) -> dict:
    """Cada celda: un padre a 0,6 km que empieza en t0, un pad hijo temprano (fracturado antes de que el padre produzca: virgen)
    y un pad hijo tardio (fracturado 14 meses despues: depletado), 2 hijos por pad, y un pozo posterior a la ventana de los
    hijos (control negativo) con volumen al azar. Las celdas con padre de volumen alto (mitad superior) tienen roca mejor:
    todos sus hijos ganan `ubicacion`; los hijos tardios de esas celdas pierden `penalizacion` (depleccion)."""
    rng = np.random.default_rng(semilla)
    vol = rng.uniform(500, 3000, n_celdas)
    alto = vol > np.median(vol)
    pozos, hijos, nid = [], [], 0
    for k in range(n_celdas):
        lat, t0 = _lat_celda(k), 12 * (2016 + k % 5) + 3
        pozos.append({"id": 10000 + k, "lat": lat + 0.0054, "lon": LON0, "mes_pp": t0, "bbl": [vol[k]] * 60})
        pozos.append({"id": 20000 + k, "lat": lat + 0.0045, "lon": LON0, "mes_pp": t0 + 90, "bbl": [rng.uniform(500, 3000)] * 12})
        for tardio, dlat in ((False, 0.0), (True, 0.002)):
            frac = t0 + int(rng.integers(14, 40)) if tardio else t0 - int(rng.integers(2, 30))
            for _ in range(2):
                nid += 1
                y = 100 + rng.normal(0, 6) + (ubicacion if alto[k] else 0.0) - (penalizacion if tardio and alto[k] else 0.0)
                hijos.append({"id": nid, "lat": lat + dlat, "lon": LON0, "mes_pp": frac + 2, "mes_frac": frac, "rama": 2500.0,
                              "etapas": 30.0, "arena": 9000.0, "y_bbl": y * 2500.0, "pad": f"p{k}{'t' if tardio else 'e'}",
                              "bbl": [10.0] * 12})
                pozos.append({"id": nid, "lat": lat + dlat, "lon": LON0, "mes_pp": frac + 2, "bbl": [10.0] * 12})
    return {"H": _hijos(hijos), "P": _pozos(pozos), "pasos": [("sintetico", len(hijos))]}


def _fila(R, modelo, termino="muy_depletado"):
    return next(r for r in R["coef"] if r[0] == modelo and r[1] == termino)


def test_la_grilla_es_fija_y_de_2_km():
    lat = np.array([_lat_celda(0), _lat_celda(0) + 0.0054, _lat_celda(0) + 0.02])
    c = hc.celdas(lat, np.full(3, LON0))
    assert c[0] == c[1] != c[2]                       # 0,6 km mas al norte sigue en la celda; 2,2 km no
    c1 = hc.celdas(lat, np.full(3, LON0), 1.0)
    assert c1[0] != c1[1]                             # con cuadrados de 1 km, 0,6 km desde 0,5 km del borde ya es otra celda


def test_un_efecto_de_ubicacion_no_se_confunde_con_depleccion_dentro_de_celdas():
    R = hc.calcular(_mundo(80, penalizacion=0.0, ubicacion=15.0))   # las celdas de roca buena son las de padre grande
    prin = _fila(R, "principal")
    assert hj.nulo(prin[4], prin[5]) and abs(prin[2]) < 0.05 * prin[11]
    assert R["veredicto"] == "no se sostiene"
    assert R["resumen"][0][4] == 40                   # celdas con hijos virgen y muy depletados
    assert R["resumen"][0][7] == prin[4]              # con control nulo, la cota es el limite bajo del IC


def test_una_penalizacion_de_depleccion_se_recupera_dentro_de_celdas():
    R = hc.calcular(_mundo(80, penalizacion=20.0, ubicacion=15.0))
    prin, ctrl = _fila(R, "principal"), _fila(R, "control_negativo")
    assert prin[5] < 0 and prin[4] < -20 < prin[5] and abs(prin[2] + 20) < 6
    assert hj.nulo(ctrl[4], ctrl[5])
    assert R["veredicto"] == "sostiene" and prin[12] == "sostiene"


def test_menos_de_30_celdas_informativas_es_sin_muestra_y_no_hay_cota():
    R = hc.calcular(_mundo(56, penalizacion=20.0, ubicacion=0.0))
    assert R["resumen"][0][4] == 28
    assert R["veredicto"] == "sin muestra"
    assert math.isnan(R["resumen"][0][7]) and math.isnan(R["resumen"][0][8])


def test_la_pagina_sale_de_los_marts_sin_guiones_largos():
    R = hc.calcular(_mundo(80, penalizacion=20.0, ubicacion=15.0))
    con = duckdb.connect()
    _escribir(con, "mart_hijo_celdas_coef", hc.COLS_COEF, R["coef"])
    _escribir(con, "mart_hijo_celdas_resumen", hc.COLS_RESUMEN, R["resumen"])
    _escribir(con, "mart_hijo_celdas_equilibrio", hc.COLS_EQUILIBRIO, R["equilibrio"])
    txt = hc.pagina_hijo_celdas(con)
    assert "**sostiene**" in txt and "Cota superior de la pérdida" in txt
    assert not DASHES.search(txt)
    assert txt.count("| Principal (celdas de 2 km) |") == 2


def test_el_calculo_es_determinista():
    a = hc.calcular(_mundo(60, penalizacion=10.0, ubicacion=5.0, semilla=9))
    b = hc.calcular(_mundo(60, penalizacion=10.0, ubicacion=5.0, semilla=9))
    assert repr(a) == repr(b)
