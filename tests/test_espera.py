"""Pruebas de pipeline/espera.py: la regla de plata de la espera (supuestos, no mediciones)."""
import base64
import re
import sys
from array import array

import duckdb
import pytest

from pipeline import espera
from pipeline.ingest import DATA

WAREHOUSE = DATA / "warehouse.duckdb"
needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def datos():
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return espera.collect(con)
    finally:
        con.close()


def decode(s, typecode):
    a = array(typecode)
    a.frombytes(base64.b64decode(s, validate=True))
    if sys.byteorder == "big" and a.itemsize > 1:
        a.byteswap()
    return a


def evento(fecha, bbl, km=0.5, p=0, h=1, t="interf", con_bbl=True):
    ev = {"f": fecha, "t": t, "p": p, "h": h, "km": km}
    if con_bbl:
        ev["bbl"] = bbl
    return ev


# ---- helpers puros (sin warehouse) ----

def test_dinero_con_los_supuestos_por_defecto():
    assert espera.dinero(1e6, 60, 10, 12) == pytest.approx(1e6 * 60 * (1 - 1 / 1.1))


def test_dinero_cero_sin_tasa():
    assert espera.dinero(1e6, 60, 0, 12) == pytest.approx(0.0)


def test_dinero_crece_con_los_meses():
    assert espera.dinero(1e6, 60, 10, 6) < espera.dinero(1e6, 60, 10, 24)


def test_dinero_crece_con_la_tasa():
    assert espera.dinero(1e6, 60, 0, 12) < espera.dinero(1e6, 60, 20, 12)


@pytest.mark.parametrize("args", [
    (-1.0, 60, 10, 12),  # barriles negativos
    (1e6, 29, 10, 12),  # precio bajo el minimo
    (1e6, 101, 10, 12),  # precio sobre el maximo
    (1e6, 60, -1, 12),  # tasa negativa
    (1e6, 60, 21, 12),  # tasa sobre el maximo
    (1e6, 60, 10, 5),  # espera por debajo del minimo
    (1e6, 60, 10, 25),  # espera sobre el maximo
])
def test_dinero_fuera_de_rango(args):
    with pytest.raises(ValueError):
        espera.dinero(*args)


def test_frase_texto_exacto():
    esperada = ("Con USD 60 por barril, 10% anual y 12 meses de espera, esperar costó entre USD 35 y 62 "
                "millones: cota superior, supuesto, no medición.")
    assert espera.frase(6374450.54, 11445599.76, 60, 10, 12) == esperada


def test_frase_los_numeros_salen_de_la_formula():
    lo = espera.dinero(6374450.54, 60, 10, 12) / 1e6
    hi = espera.dinero(11445599.76, 60, 10, 12) / 1e6
    assert round(lo) == 35
    assert round(hi) == 62


def test_frase_no_tiene_raya():
    s = espera.frase(6374450.54, 11445599.76, 60, 10, 12)
    assert chr(0x2013) not in s
    assert chr(0x2014) not in s


def test_frase_fuera_de_rango():
    with pytest.raises(ValueError):
        espera.frase(1e6, 2e6, 200, 10, 12)


def test_elegir_caso_toma_la_mediana_inferior():
    # Solo cuentan los eventos con ventana de 24 meses completa (mes de datos 2026-10).
    eventos = [evento("2024-10-01", 300), evento("2024-09-01", 100), evento("2024-08-01", 200)]
    i = espera.elegir_caso(eventos, "2026-10")
    assert eventos[i]["bbl"] == 200  # mediana de 100, 200 y 300


def test_elegir_caso_ignora_los_que_no_cuentan():
    eventos = [
        evento("2024-10-01", 300),
        evento("2024-09-01", 100),
        evento("2024-08-01", 200),
        evento("2024-07-01", 50, km=1.5),  # lejos: no es cercano
        evento("2024-06-01", 10, con_bbl=False),  # sin diferido medido
        evento("2024-11-01", 1),  # ventana incompleta
    ]
    i = espera.elegir_caso(eventos, "2026-10")
    assert i == 2
    assert eventos[i]["bbl"] == 200


def test_elegir_caso_sin_candidatos():
    assert espera.elegir_caso([evento("2026-01-01", 10)], "2026-10") == -1


def test_numero_es_formato_argentino():
    assert espera.numero_es(6.4, 1) == "6,4"
    assert espera.numero_es(1234567) == "1.234.567"


def test_banda_svg_cierra_y_no_sale_del_cuadro():
    """La banda de la brecha se cierra y no se sale del cuadro: sin datos ni warehouse."""
    curva = [
        {"banda": "cercano", "k": -3, "indice": 1.00}, {"banda": "control", "k": -3, "indice": 1.00},
        {"banda": "cercano", "k": 0, "indice": 0.80}, {"banda": "control", "k": 0, "indice": 0.95},
        {"banda": "cercano", "k": 6, "indice": 0.90}, {"banda": "control", "k": 6, "indice": 0.92},
    ]
    svg = espera.banda_svg(curva)
    camino = re.search(r'<path d="([^"]+)"', svg).group(1)
    assert camino.rstrip().endswith("Z")
    puntos = re.findall(r"([\d.]+),([\d.]+)", camino)
    assert puntos
    for _, y in puntos:
        assert 0 <= float(y) <= 60
    assert 'class="banda"' in svg and 'role="img"' in svg
    assert 'aria-label="brecha entre los vecinos y el control, mes a mes"' in svg
    assert 'fill="var(--lutita)"' in svg and 'stroke="var(--orilla)"' in svg
    assert 'vector-effect="non-scaling-stroke"' in svg
    assert espera.banda_svg([]) == ""


def test_banda_svg_salta_los_meses_sin_control():
    """Un mes que trae solo una de las dos curvas no se dibuja como una brecha enorme: se saltea."""
    curva = [
        {"banda": "cercano", "k": 0, "indice": 0.80}, {"banda": "control", "k": 0, "indice": 0.95},
        {"banda": "cercano", "k": 1, "indice": 0.70},
        {"banda": "cercano", "k": 2, "indice": 0.90}, {"banda": "control", "k": 2, "indice": 0.92},
    ]
    camino = re.search(r'<path d="([^"]+)"', espera.banda_svg(curva)).group(1)
    ys = [float(y) for _, y in re.findall(r"(-?[\d.]+),(-?[\d.]+)", camino)]
    assert max(ys) < 15, ys
    assert len(ys) == 4, ys


# ---- con el warehouse ----

@needs_wh
def test_rango_6_4_y_11_4_millones(datos):
    rango = datos["rango"]
    assert round(rango["inferior_bbl"] / 1e6, 1) == 6.4
    assert round(rango["superior_bbl"] / 1e6, 1) == 11.4
    assert rango["eventos_inferior"] == 2090
    assert rango["eventos_superior"] == 2094


@needs_wh
def test_la_copia_lleva_todos_los_eventos_del_rango(datos):
    """Los cercanos se eligen por traer bbl, no por el km redondeado: no se pierde ninguno."""
    assert len(datos["eventos"]) == datos["rango"]["eventos_superior"]


@needs_wh
def test_mediana_24_operador_todas(datos):
    m = datos["mediana_24"]
    assert round(m["bbl"]) == -954
    assert m["eventos"] == 1432
    assert m["ic_bajo"] < m["bbl"] < m["ic_alto"]


@needs_wh
def test_eventos_son_interferencias_cercanas_con_diferido(datos):
    assert datos["eventos"]
    for ev in datos["eventos"]:
        assert ev["t"] == "interf"
        assert ev["km"] <= 1
        assert "bbl" in ev


@needs_wh
def test_los_indices_apuntan_a_los_pozos_reducidos(datos):
    n = len(datos["pozos"])
    for ev in datos["eventos"]:
        assert 0 <= ev["p"] < n
        assert 0 <= ev["h"] < n


@needs_wh
def test_caudal_y_agua_describen_los_pozos_reducidos(datos):
    nm = len(datos["meta"]["meses"])
    assert len(decode(datos["caudal"], "H")) == len(datos["pozos"]) * nm
    assert len(decode(datos["agua"], "B")) == len(datos["pozos"]) * nm


@needs_wh
def test_caso_valido_y_con_ventana_completa(datos):
    i = datos["caso"]
    assert 0 <= i < len(datos["eventos"])
    ev = datos["eventos"][i]
    assert espera.ventana_ok(ev["f"][:7], datos["meta"]["mes_datos"])


@needs_wh
def test_supuestos_publicados(datos):
    assert datos["supuestos"]["precio"] == espera.PRECIO
    assert datos["supuestos"]["tasa"] == espera.TASA
    assert datos["supuestos"]["meses"] == espera.MESES


@needs_wh
def test_distancia_trae_tres_bandas_ordenadas(datos):
    """Las tres bandas gruesas contra el control de 5 a 10 km: la mas cercana es la de mayor brecha."""
    d = datos["distancia"]
    assert [(r["km_desde"], r["km_hasta"]) for r in d] == [(0.0, 1.0), (1.0, 2.0), (2.0, 5.0)]
    assert d[0]["brecha"] < d[1]["brecha"] < d[2]["brecha"] < 0
