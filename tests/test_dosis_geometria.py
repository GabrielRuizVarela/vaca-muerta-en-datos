"""Tests de la puerta de potencia de la geometria de las ramas (unidad U4).

Todo es sintetico: no se toca el warehouse real.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import dosis
from pipeline import dosis_geometria as geo
from pipeline.costo import _escribir

EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)


# ------------------------------------------------------------------ constantes


def test_constantes_son_las_de_la_regla_fijada():
    assert geo.SHA_REGLA == "59b3a26"
    assert geo.MDE_REF == 0.22
    assert geo.CERCA_RAMA_M == 600
    assert geo.M_HOLM == 4
    assert geo.N_MIN_CASOS == 100
    assert geo.PADS_MIN == 30
    assert geo.SEMILLA_GEO == dosis.SEMILLA_DOSIS + 3_000_000
    assert geo.VEREDICTOS_PUERTA == ("sin muestra", "la geometría no da más potencia",
                                    "la geometría da más potencia")


# ------------------------------------------------------------------ veredicto de la puerta


def test_veredicto_puerta_umbral_estricto():
    codigo, texto = geo.veredicto_puerta(0.22, 500, 60)
    assert codigo == geo.VEREDICTOS_PUERTA[1]
    assert "0,22" in texto
    assert geo.veredicto_puerta(0.2199, 500, 60)[0] == geo.VEREDICTOS_PUERTA[2]
    assert geo.veredicto_puerta(0.35, 500, 60)[0] == geo.VEREDICTOS_PUERTA[1]


def test_veredicto_puerta_sin_muestra():
    assert geo.veredicto_puerta(None, 99, 60)[0] == geo.VEREDICTOS_PUERTA[0]
    assert geo.veredicto_puerta(None, 500, 29)[0] == geo.VEREDICTOS_PUERTA[0]
    assert geo.veredicto_puerta(0.10, 99, 60)[0] == geo.VEREDICTOS_PUERTA[0]


def test_los_textos_de_la_puerta_no_descartan_nada():
    textos = [geo.veredicto_puerta(0.22, 500, 60)[1],
              geo.veredicto_puerta(0.2199, 500, 60)[1],
              geo.veredicto_puerta(None, 10, 2)[1]]
    for t in textos:
        assert "descartado" not in t
        assert "se descarta" not in t


# ------------------------------------------------------------------ muestra


def test_mascara_rama_y_umbral_de_cercania():
    pares = {(1, 10): 500.0, (2, 20): 600.0, (3, 30): 599.9}
    m_min = geo.mascara_rama([1, 2, 3, 4], [10, 20, 30, 40], pares)
    assert m_min[0] == 500.0
    assert m_min[1] == 600.0
    assert np.isnan(m_min[3])
    assert list(geo.dentro_de_rama(m_min)) == [True, False, True, False]


def test_dentro_de_rama_con_nan_y_con_el_valor_exacto():
    assert not geo.dentro_de_rama(np.array([np.nan]))[0]
    assert not geo.dentro_de_rama(np.array([600.0]))[0]
    assert geo.dentro_de_rama(np.array([599.9]))[0]


# ------------------------------------------------------------------ puerta analitica


def _d_sintetico(n_pads=40, por_pad=5, semilla=7):
    rng = np.random.default_rng(semilla)
    n = n_pads * por_pad
    d = {"caida": rng.normal(0, 1, n),
         "padre": np.arange(n, dtype=np.int64), "hijo": np.arange(n, dtype=np.int64),
         "km": rng.uniform(0.1, 1.0, n), "edad": rng.uniform(10, 200, n),
         "base": rng.uniform(100, 5000, n), "hijos": rng.integers(0, 5, n).astype(float),
         "term": np.array(["Tapón disparo"] * n, dtype=object),
         "area": np.array(["A1"] * n, dtype=object),
         "anio": np.full(n, 2020, dtype=int),
         "cluster": np.array([f"pad{i // por_pad}" for i in range(n)], dtype=object)}
    for j in range(4):
        d[f"v{j + 1}"] = rng.normal(0, 1, n)
    return d


def test_puerta_resultado_devuelve_cuatro_filas_sin_coeficiente(monkeypatch):
    monkeypatch.setattr(geo, "B_GATE", 60)
    d = _d_sintetico()
    cc = np.arange(len(d["caida"]))
    r = geo.puerta_resultado(d["caida"], d, cc, "A")
    filas = r["filas"]
    assert len(filas) == 4
    nombres = [c[0] for c in geo.COLS_GEO_POT]
    assert "coef_desvios" not in nombres
    assert not any("coef" in n for n in nombres)
    for f in filas:
        assert len(f) == len(geo.COLS_GEO_POT)
        assert f[8] > f[7]          # el MDE80 de Holm es mas demanding que el sin ajustar
        assert f[6] == geo.M_HOLM


def test_puerta_resultado_es_determinista(monkeypatch):
    monkeypatch.setattr(geo, "B_GATE", 60)
    d = _d_sintetico()
    cc = np.arange(len(d["caida"]))
    a = geo.puerta_resultado(d["caida"], d, cc, "A")
    b = geo.puerta_resultado(d["caida"], d, cc, "A")
    assert a["filas"] == b["filas"]


def test_valida_simulacion_usa_los_dos_niveles_con_su_regla():
    filas = []
    for var in dosis.VARIABLES:
        nombre = dosis.NOMBRES[var]
        filas.append((nombre, "mde_sin_ajustar", 0.15, "sin_ajustar", 200, 160, 0.8, 0.04))
        filas.append((nombre, "mde_holm", 0.18, "holm", 200, 150, 0.75, 0.04))
    assert geo.valida_simulacion(filas) is True
    filas[0] = (filas[0][0], filas[0][1], filas[0][2], filas[0][3], filas[0][4], 20, 0.1, 0.02)
    assert geo.valida_simulacion(filas) is False
    assert geo.valida_simulacion(filas[:-1]) is None
    assert geo.valida_simulacion([]) is None


# ------------------------------------------------------------------ pagina


def _marts_geo(con, pasa=True, con_potencia_hoy=True):
    _escribir(con, "mart_dosis_geometria_muestra", geo.COLS_GEO_MUESTRA,
              [("A", 1200, 900, 700, 650, 200), ("B", 1200, 900, 700, 600, 190)])
    pot = []
    for res in ("A", "B"):
        for k, var in enumerate(dosis.VARIABLES):
            se = 0.05 + 0.005 * k
            pot.append((res, dosis.NOMBRES[var], 650, 200, 0.4, se, geo.M_HOLM,
                        0.9 * se, 1.2 * se,
                        10.0, 20.0, 30.0, 40.0, 11.0, 21.0, 31.0, 41.0))
    _escribir(con, "mart_dosis_geometria_potencia", geo.COLS_GEO_POT, pot)
    sim = []
    for var in dosis.VARIABLES:
        nombre = dosis.NOMBRES[var]
        for nivel, delta in (("0", 0.0), ("0,1", 0.1), ("0,2", 0.2), ("0,22", 0.22),
                             ("mde_sin_ajustar", 0.15), ("mde_holm", 0.18)):
            for regla in ("holm", "sin_ajustar"):
                s = 160 if nivel.startswith("mde") else (10 if nivel == "0" else 100)
                p = s / 200
                sim.append((nombre, nivel, delta, regla, 200, s, p, (p * (1 - p) / 200) ** 0.5))
    _escribir(con, "mart_dosis_geometria_sim", geo.COLS_GEO_SIM, sim)
    if pasa:
        codigo = geo.VEREDICTOS_PUERTA[2]
        texto = "el menor MDE80 de Holm del resultado A es de 0,18 desvíos de la caída por desvío de la dosis"
        fila = (codigo, texto, 650, 200, 0.18, 0.40, geo.MDE_REF, "alcanza para 0,2", True, True)
    else:
        codigo = geo.VEREDICTOS_PUERTA[1]
        texto = ("el menor MDE80 de Holm del resultado A es de 0,30 desvíos de la caída por desvío de la "
                 "dosis: medir los padres cercanos entre ramas no baja el efecto mínimo detectable")
        fila = (codigo, texto, 650, 200, 0.30, 0.45, geo.MDE_REF, "no alcanza para 0,2", False, True)
    _escribir(con, "mart_dosis_geometria_puerta", geo.COLS_GEO_PUERTA, [fila])
    if con_potencia_hoy:
        _escribir(con, "mart_potencia_dosis", geo.potencia_dosis.COLS_POTENCIA_DOSIS,
                  [("A", "conjunto", dosis.NOMBRES[v], 1500, 260, 0.4, 0.02, 0.03, 4,
                    0.24, 0.31, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
                   for v in dosis.VARIABLES])
    if pasa:
        mod = [("A", v, 0.12, 0.01, 0.23, 0.01, 0.04, 650, 200, 1.2, True, False) for v in dosis.VARIABLES]
        mod += [("B", v, 0.05, -0.02, 0.12, 0.20, 0.40, 600, 190, 1.1, False, False)
                for v in dosis.VARIABLES]
        _escribir(con, "mart_dosis_geometria_modelo", dosis.COLS_MODELO, mod)
        _escribir(con, "mart_dosis_geometria_quintiles", dosis.COLS_QUINTILES, [])
        _escribir(con, "mart_dosis_geometria_orden", dosis.COLS_ORDEN, [])
        _escribir(con, "mart_dosis_geometria_sens", dosis.COLS_SENS, [])
        _escribir(con, "mart_dosis_geometria_veredicto", geo.COLS_GEO_VEREDICTO,
                  [("A", "dosis y respuesta", "dos variables con signo positivo y p de Holm bajo 0,05"),
                   ("B", "sin dosis y respuesta", "ninguna variable con p de Holm bajo 0,05")])


def test_pagina_cuando_la_puerta_no_pasa():
    con = duckdb.connect(":memory:")
    _marts_geo(con, pasa=False, con_potencia_hoy=False)
    pagina = geo.pagina_dosis_geometria(con)
    con.close()
    assert pagina.startswith("# Dosis con la geometría de las ramas, detrás de una puerta de potencia")
    assert geo.VEREDICTOS_PUERTA[1] in pagina
    assert geo.SHA_REGLA in pagina
    assert geo.NOTA_MUESTRA in pagina
    assert "## La puerta de potencia" in pagina
    assert "## Pads y eventos para ver 0,1 y 0,2 desvíos" in pagina
    assert "## Simulación de planta y recupera" in pagina
    assert "## Paso 2" not in pagina
    assert "descartado" not in pagina
    assert EN_DASH not in pagina and EM_DASH not in pagina


def test_pagina_cuando_la_puerta_pasa():
    con = duckdb.connect(":memory:")
    _marts_geo(con, pasa=True, con_potencia_hoy=True)
    pagina = geo.pagina_dosis_geometria(con)
    con.close()
    assert geo.VEREDICTOS_PUERTA[2] in pagina
    assert geo.SHA_REGLA in pagina
    assert geo.NOTA_MUESTRA in pagina
    assert "## Paso 2: el modelo conjunto" in pagina
    assert "dosis y respuesta" in pagina
    assert EN_DASH not in pagina and EM_DASH not in pagina


def test_main_sin_muestra_por_pads_no_calcula_nada(tmp_path, monkeypatch):
    """Con 100 eventos o mas pero menos de 30 pads la regla dice "sin muestra": no hay MDE, ni simulacion, ni paso 2."""
    conteos = {r: {"eventos_dosis": 500, "con_par": 300, "cercano_rama": 200, "caso_completo": 120, "pads": 20}
               for r in geo.RESULTADOS}
    monkeypatch.setattr(geo, "muestra", lambda con: {"d": {}, "cc": {r: list(range(120)) for r in geo.RESULTADOS},
                                                    "ys": {}, "conteos": conteos})
    monkeypatch.setattr(geo, "puerta_resultado", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe calcular")))
    monkeypatch.setattr(geo, "_paso2", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe correr el paso 2")))
    ruta = tmp_path / "wh.duckdb"
    geo.main(ruta)
    con = duckdb.connect(str(ruta), read_only=True)
    try:
        fila = con.execute("select codigo, n, pads, mde_menor_holm, pasa from mart_dosis_geometria_puerta").fetchall()
        assert fila == [("sin muestra", 120, 20, None, False)]
        assert con.execute("select count(*) from mart_dosis_geometria_potencia").fetchone()[0] == 0
    finally:
        con.close()
