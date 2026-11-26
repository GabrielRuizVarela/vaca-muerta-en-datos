"""Validacion por inyeccion con eventos sinteticos: un efecto plantado de tamano conocido se recupera, el nulo no da efecto y todo es determinista."""
from datetime import date

import duckdb
import numpy as np
import pytest

from pipeline import inyeccion as iy
from pipeline.costo import _escribir
from pipeline.placebo import BASE_ORIGINAL
from test_descomposicion import con_paneles

REPS = 40
MUNDOS = 6


@pytest.fixture(scope="module")
def mundo_sintetico() -> tuple[dict, dict, float]:
    """Datos sinteticos sin efecto con las columnas del mundo nulo, los eventos sin plantar y la parte de cerrados de S1."""
    D = con_paneles(0.0, 0.0, seed=11)
    rng = np.random.default_rng(2)
    D["mes_falso"] = D["hijo_mes"] - 12
    D["f0_falso"] = rng.uniform(1 / 31, 1.0, len(D["hijo_mes"]))
    D["anio_falso"] = D["hijo_anio"] - 1
    ev = iy.marco_falso(D, (1,), BASE_ORIGINAL)
    p = iy.participacion_cierre(ev["idx"][1][ev["banda"] == 0], ev["idx"][1][ev["banda"] == 2])
    return D, ev, p


def _media(D, ev, p, esc, tam, medida, completo=False, mundos=MUNDOS):
    rs = [iy.mundo(D, ev, w, esc, tam, p, completo, REPS) for w in range(mundos)]
    return np.array([r[medida][0] if isinstance(r[medida], tuple) else r[medida] for r in rs]), rs


def test_caida_de_caudal_plantada_se_recupera(mundo_sintetico):
    D, ev, p = mundo_sintetico
    for tam in (10, 30):
        g, rs = _media(D, ev, p, "S2", tam, "brecha_mes1")
        assert abs(g.mean() + tam) < 2.5
        assert np.mean([r["parte_tasa"] for r in rs]) > 0.8


def test_cierre_plantado_da_la_brecha_esperada_y_se_lee_como_dias(mundo_sintetico):
    D, ev, p = mundo_sintetico
    assert 0.3 < p < 0.7
    g, rs = _media(D, ev, p, "S1", 100, "brecha_mes1")
    assert abs(g.mean() + 50) < 10
    assert np.mean([r["parte_dias"] for r in rs]) > 0.8


def test_nulo_no_da_efecto_ni_pendiente(mundo_sintetico):
    D, ev, p = mundo_sintetico
    g, rs = _media(D, ev, p, "S5", 0, "brecha_mes1", completo=True)
    assert abs(g.mean()) < 1.5
    assert abs(np.mean([r["preten"] for r in rs])) < 1.5
    assert abs(np.mean([r["pendiente_mes0"][0] for r in rs])) < 1.5
    assert abs(np.mean([r["pendiente_mes_m1"] for r in rs])) < 1.5
    # el IC del mes 1 incluye cero casi siempre cuando no hay nada plantado
    assert np.mean([iy._excluye(r["brecha_mes1"], 0.0) for r in rs]) <= 0.34


def test_caida_desde_el_inicio_planta_la_pendiente_conocida(mundo_sintetico):
    D, ev, p = mundo_sintetico
    pend, rs = _media(D, ev, p, "S3", 40, "pendiente_mes0", completo=True)
    assert abs(pend.mean() + 4.0) < 1.2                         # -10 * 0,4 puntos por 0,1 de f0
    assert all(r["pendiente_mes0"][2] < 0 for r in rs)          # el IC excluye cero con el signo plantado
    assert abs(np.mean([r["pendiente_mes_m1"] for r in rs])) < 1.5


def test_brecha_previa_se_lee_en_la_pretendencia_y_no_en_el_mes_1_neto(mundo_sintetico):
    D, ev, p = mundo_sintetico
    nulo = [iy.mundo(D, ev, w, "S5", 0, p, True, REPS) for w in range(MUNDOS)]
    s4 = [iy.mundo(D, ev, w, "S4", 5, p, True, REPS) for w in range(MUNDOS)]
    pre = np.mean([a["preten"] - b["preten"] for a, b in zip(s4, nulo)])
    neta = np.mean([a["brecha_mes1_neta"] - b["brecha_mes1_neta"] for a, b in zip(s4, nulo)])
    principal = np.mean([a["brecha_mes1"][0] - b["brecha_mes1"][0] for a, b in zip(s4, nulo)])
    assert abs(pre + 5) < 1.5
    assert abs(neta) < 1.5
    assert abs(principal) < 1.5     # la base de los meses -3 a -1 incluye la brecha: no se filtra al resultado principal


def test_plantar_no_modifica_los_datos_originales(mundo_sintetico):
    D, ev, p = mundo_sintetico
    antes = D["tasa"].copy()
    sel = ev["banda"] == 0
    W = iy.plantar(D, ev, sel, "S2", 20)
    assert np.array_equal(D["tasa"], antes, equal_nan=True)
    assert not np.array_equal(W["tasa"], antes, equal_nan=True)


def test_los_mundos_son_deterministas(mundo_sintetico):
    D, ev, p = mundo_sintetico
    a = iy.mundo(D, ev, 3, "S3", 40, p, True, REPS)
    b = iy.mundo(D, ev, 3, "S3", 40, p, True, REPS)
    assert a == b
    c = iy.mundo(D, ev, 4, "S3", 40, p, True, REPS)
    assert a != c       # otro mundo sortea otros pads


def test_participacion_de_cierre_deja_la_mediana_en_el_objetivo():
    x = np.linspace(0.5, 1.5, 1001)
    assert iy.participacion_cierre(x, np.array([1.0])) == pytest.approx(0.5, abs=0.01)
    p = iy.participacion_cierre(x, np.array([1.0]), objetivo=-0.25)
    assert p == pytest.approx(1 / 3, abs=0.01)
    mezcla = np.concatenate([np.zeros(int(round(p / (1 - p) * len(x)))), x])
    assert np.median(mezcla) == pytest.approx(0.75, abs=0.02)
    with pytest.raises(ValueError):
        iy.participacion_cierre(np.linspace(0.9, 1.1, 100), np.array([1.0]), objetivo=0.1)


def test_correr_fecha_acota_el_dia_y_respeta_el_ano():
    assert iy._correr_fecha(date(2024, 2, 29), -12) == date(2023, 2, 28)
    assert iy._correr_fecha(date(2025, 3, 31), -1) == date(2025, 2, 28)
    assert iy._correr_fecha(date(2025, 1, 15), -1) == date(2024, 12, 15)
    assert iy._correr_fecha(date(2025, 6, 10), 12) == date(2026, 6, 10)


def test_mart_y_pagina_sinteticos(mundo_sintetico):
    D, ev, p = mundo_sintetico
    filas, p2 = iy.calcular(D, mundos=3, reps=30, ev=ev)
    assert p2 == pytest.approx(p)
    assert filas == iy.calcular(D, mundos=3, reps=30, ev=ev)[0]
    con = duckdb.connect(":memory:")
    _escribir(con, "mart_inyeccion", iy.COLS_INY, filas)
    medidas = {(f[0], f[1], f[2]) for f in filas}
    for celda in (("S1", 100, "brecha_mes1"), ("S2", 20, "brecha_mes1"), ("S3", 40, "pendiente_mes0"), ("S4", 5, "preten"),
                  ("S5", 0, "brecha_mes1")):
        assert celda in medidas
    assert set(iy.veredictos(con)) == {"r1", "r2", "r3", "r4a", "r4b"}
    pagina = iy.pagina_inyeccion(con)
    assert pagina.startswith("# Validación por inyección")
    assert not any(c in pagina for c in (chr(0x2014), chr(0x2013)))
    for e, t in (("S1", 100), ("S2", 10), ("S3", 60), ("S4", 8), ("S5", 0)):
        assert f"| {e} | {t} |" in pagina


def test_plantado_en_puntos_es_el_tamano_por_el_indice(mundo_sintetico):
    D, ev, p = mundo_sintetico
    mediana = float(np.nanmedian(ev["idx"][1][ev["banda"] == 0]))
    s2 = iy.plantado_en_puntos(D, ev, "S2", 20)["brecha_mes1"]
    assert s2 == pytest.approx(-20 * mediana, abs=1.0)           # el efecto en puntos es el tamano por el indice de los cercanos
    s3 = iy.plantado_en_puntos(D, ev, "S3", 40)["pendiente_mes0"]
    assert -4.0 < s3 < 0.0                                         # menos que el nominal, porque el indice es menor que 1
    assert abs(iy.plantado_en_puntos(D, ev, "S3", 60)["pendiente_mes0"]) > abs(s3)
    pre = iy.plantado_en_puntos(D, ev, "S4", 5)
    assert set(pre) == {"preten", "brecha_mes1_base_limpia", "brecha_mes1_neta", "brecha_mes1"}
    assert abs(pre["brecha_mes1"]) < 1.0                          # la base de los meses -3 a -1 absorbe el nivel plantado
    with pytest.raises(ValueError):
        iy.plantado_en_puntos(D, ev, "S5", 0)


def test_intervalo_exacto_de_3_en_30():
    lo, hi = iy.intervalo_exacto(3, 30)
    assert lo == pytest.approx(0.0211, abs=0.001) and hi == pytest.approx(0.2653, abs=0.001)
    assert iy.intervalo_exacto(0, 10)[0] == 0.0 and iy.intervalo_exacto(10, 10)[1] == 1.0


def test_la_pagina_dice_las_dos_lecturas_de_r4a_en_el_borde(mundo_sintetico):
    D, ev, p = mundo_sintetico
    filas, _ = iy.calcular(D, mundos=3, reps=30, ev=ev)
    # forzar el borde exacto: 1 de 10 mundos excluye cero en el nulo
    filas = [f[:4] + (10,) + f[5:9] + (0.10,) + f[10:] if f[0] == "S5" and f[2] == "brecha_mes1" else f for f in filas]
    con = duckdb.connect(":memory:")
    _escribir(con, "mart_inyeccion", iy.COLS_INY, filas)
    assert not iy.veredictos(con)["r4a"]
    pagina = iy.pagina_inyeccion(con)
    assert "R4a, falsos positivos: en el borde exacto" in pagina
    assert "como máximo 10%" in pagina and "operador del libro es estricto (< 0,10)" in pagina
    assert "cumple el texto y no el operador" in pagina
    assert "IC por bloques de 5 km" in pagina
    assert "(bruto)" in pagina and "Plantado en puntos" in pagina
