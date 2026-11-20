"""Alcance entre ramas: los estadisticos, los veredictos y el bootstrap con la regla fijada antes de correr."""
import numpy as np
import pytest

from pipeline import alcance_rama as ar
from pipeline import placebo

PAD = placebo.PAD
MES = 100          # mes de fractura del sintetico (desde 2000-01)
N_GRUPOS = 5
N_POR_GRUPO = 120
RANGO_M = (150.0, 450.0, 800.0, 1500.0, 2500.0)   # distancia entre ramas de cada grupo


# ------------------------------------------------------------------ (a) estadisticos a mano

MANO_D = np.array([100.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1200.0, 1500.0, 2500.0, 3000.0])
MANO_V = np.array([0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.20, 1.30])
MANO_B = np.array([0, 0, 1, 1, 2, 2, 2, 1, 2, 2])


def test_estadisticos_se_pueden_calcular_a_mano():
    est = ar.estadisticos(MANO_V, MANO_D, MANO_B)
    # control lateral: la mediana de los dos controles (1,20 y 1,30) es 1,25
    assert est["brecha_0_300"] == pytest.approx(0.725 - 1.25)
    assert est["brecha_300_600"] == pytest.approx(0.825 - 1.25)
    assert est["brecha_600_1000"] == pytest.approx(0.925 - 1.25)
    assert est["brecha_1000_2000"] == pytest.approx(1.025 - 1.25)
    # A: los cuatro de menos de 600 m (mediana 0,775) contra el control lateral
    assert est["A"] == pytest.approx(0.775 - 1.25)
    # B: banda de superficie 0 (mediana 0,725) contra la banda 2 (mediana 1,00)
    assert est["B"] == pytest.approx(0.725 - 1.00)
    assert est["A_menos_B"] == pytest.approx(est["A"] - est["B"])
    # C menos L: banda 2 con menos de 1.000 m (0,925) contra la banda 2 de 2.000 m o mas (1,25)
    assert est["C_menos_L"] == pytest.approx(0.925 - 1.25)


def test_conteos_se_pueden_calcular_a_mano():
    c = ar.conteos(MANO_V, MANO_D, MANO_B)
    assert c == {"n_0_300": 2, "n_300_600": 2, "n_600_1000": 2, "n_1000_2000": 2, "n_control": 2,
                 "n_cerca": 4, "n_sup_cerca": 2, "n_sup_control": 5, "n_contaminado": 2, "n_limpio": 2,
                 "n_eventos": 10}


def test_estadisticos_son_nan_safe():
    # un nan en el medio de una banda no cambia la mediana; una banda vacia da nan
    v = MANO_V.copy()
    v[0] = np.nan
    est = ar.estadisticos(v, MANO_D, MANO_B)
    assert est["brecha_0_300"] == pytest.approx(0.75 - 1.25)
    vacio = ar.estadisticos(v, MANO_D + 10_000.0, MANO_B)
    assert np.isnan(vacio["brecha_0_300"])
    assert np.isnan(vacio["A"])
    c = ar.conteos(v, MANO_D + 10_000.0, MANO_B)
    assert c["n_0_300"] == 0
    assert c["n_eventos"] == 9   # el indice nan no cuenta como evento medido


# ------------------------------------------------------------------ (b) veredictos

def _est(**kw) -> dict:
    base = {n: {"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0} for n in ar.NOMBRES_EST}
    base.update(kw)
    return base


def _cnt(**kw) -> dict:
    base = {"n_0_300": 200, "n_300_600": 200, "n_600_1000": 200, "n_1000_2000": 200, "n_control": 200,
            "n_cerca": 200, "n_sup_cerca": 200, "n_sup_control": 200, "n_contaminado": 200, "n_limpio": 200,
            "n_eventos": 1000}
    base.update(kw)
    return base


@pytest.mark.parametrize("cnt,bloques,palabra", [
    (_cnt(n_0_300=50), 40, "sin muestra"),
    (_cnt(n_300_600=99), 40, "sin muestra"),
    (_cnt(n_600_1000=0), 40, "sin muestra"),
    (_cnt(n_1000_2000=10), 40, "sin muestra"),
    (_cnt(n_control=99), 40, "sin muestra"),
    (_cnt(), 29, "sin muestra"),
])
def test_r1_sin_muestra_tiene_precedencia(cnt, bloques, palabra):
    est = _est(brecha_0_300={"valor": -0.5, "ic_bajo": -0.6, "ic_alto": -0.4, "descartadas": 0})
    ver, alcance = ar.veredicto_r1(est, cnt, bloques)
    assert ver == palabra
    assert alcance is None


def test_r1_alcance_medido_y_el_alcance_informado():
    est = _est(brecha_0_300={"valor": -0.5, "ic_bajo": -0.6, "ic_alto": -0.4, "descartadas": 0},
               brecha_300_600={"valor": -0.3, "ic_bajo": 0.2, "ic_alto": 0.3, "descartadas": 0},
               brecha_600_1000={"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0},
               brecha_1000_2000={"valor": 0.01, "ic_bajo": -0.05, "ic_alto": 0.05, "descartadas": 0})
    ver, alcance = ar.veredicto_r1(est, _cnt(), 40)
    assert ver == "alcance medido"
    # la banda mas lejana cuyo IC excluye cero es la de 300 a 600 m
    assert alcance == pytest.approx(600.0)


def test_r1_alcance_medido_con_el_borde_de_300():
    est = _est(brecha_0_300={"valor": -0.5, "ic_bajo": -0.6, "ic_alto": -0.4, "descartadas": 0},
               brecha_300_600={"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0},
               brecha_600_1000={"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0},
               brecha_1000_2000={"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0})
    ver, alcance = ar.veredicto_r1(est, _cnt(), 40)
    assert ver == "alcance medido"
    assert alcance == pytest.approx(300.0)


def test_r1_gradiente_no_informa_alcance():
    est = _est(brecha_0_300={"valor": -0.05, "ic_bajo": -0.2, "ic_alto": 0.02, "descartadas": 0},
               brecha_1000_2000={"valor": -0.2, "ic_bajo": -0.3, "ic_alto": -0.1, "descartadas": 0})
    ver, alcance = ar.veredicto_r1(est, _cnt(), 40)
    assert ver == "gradiente"
    assert alcance is None


def test_r1_no_firme():
    est = _est(brecha_0_300={"valor": -0.05, "ic_bajo": -0.2, "ic_alto": 0.02, "descartadas": 0},
               brecha_1000_2000={"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0})
    ver, alcance = ar.veredicto_r1(est, _cnt(), 40)
    assert ver == "no firme"
    assert alcance is None


def test_r1_un_ic_nan_no_satisface_la_condicion():
    est = _est(brecha_0_300={"valor": -0.5, "ic_bajo": -0.6, "ic_alto": np.nan, "descartadas": 3},
               brecha_1000_2000={"valor": 0.0, "ic_bajo": -0.1, "ic_alto": 0.1, "descartadas": 0})
    ver, alcance = ar.veredicto_r1(est, _cnt(), 40)
    assert ver == "no firme"
    assert alcance is None


@pytest.mark.parametrize("cnt,palabra", [
    (_cnt(n_cerca=50), "sin muestra"),
    (_cnt(n_control=50), "sin muestra"),
    (_cnt(n_sup_cerca=50), "sin muestra"),
    (_cnt(n_sup_control=50), "sin muestra"),
])
def test_r2_sin_muestra(cnt, palabra):
    assert ar.veredicto_r2(_est(), cnt) == palabra


@pytest.mark.parametrize("ic_alto,palabra", [
    (-0.2, "la distancia de superficie diluye la huella"),
    (-0.001, "la distancia de superficie diluye la huella"),
    (0.0, "no se separa"),
    (0.2, "no se separa"),
    (np.nan, "no se separa"),
])
def test_r2_separa_o_no(ic_alto, palabra):
    est = _est(A_menos_B={"valor": -0.1, "ic_bajo": -0.3, "ic_alto": ic_alto, "descartadas": 0})
    assert ar.veredicto_r2(est, _cnt()) == palabra


@pytest.mark.parametrize("cnt,palabra", [
    (_cnt(n_contaminado=50), "sin muestra"),
    (_cnt(n_limpio=50), "sin muestra"),
])
def test_r3_sin_muestra(cnt, palabra):
    assert ar.veredicto_r3(_est(), cnt) == palabra


@pytest.mark.parametrize("valor,ic_alto,palabra", [
    (-0.2, -0.1, "control contaminado"),
    (-0.001, -0.0001, "control contaminado"),
    (-0.2, 0.1, "control limpio"),
    (0.2, 0.3, "control limpio"),
    (-0.2, np.nan, "control limpio"),
])
def test_r3_contaminado_o_limpio(valor, ic_alto, palabra):
    est = _est(C_menos_L={"valor": valor, "ic_bajo": -0.4, "ic_alto": ic_alto, "descartadas": 0})
    assert ar.veredicto_r3(est, _cnt()) == palabra


def test_las_palabras_son_las_fijadas():
    assert ar.VEREDICTOS_R1 == ("sin muestra", "alcance medido", "gradiente", "no firme")
    assert ar.VEREDICTOS_R2 == ("sin muestra", "la distancia de superficie diluye la huella", "no se separa")
    assert ar.VEREDICTOS_R3 == ("sin muestra", "control contaminado", "control limpio")


# ------------------------------------------------------------------ (c) bootstrap

def _arrancador_bootstrap():
    v = np.array([0.7, 0.72, 0.9, 0.95, 1.2, 1.25, 0.95, 0.97])
    d = np.array([100.0, 200.0, 700.0, 800.0, 2500.0, 3000.0, 1200.0, 1500.0])
    b = np.array([0, 0, 2, 2, 2, 2, 2, 2])
    bloque = np.array([1, 1, 2, 2, 3, 3, 4, 4])
    return v, d, b, bloque


def test_bootstrap_con_la_misma_semilla_da_lo_mismo():
    v, d, b, bloque = _arrancador_bootstrap()
    uno = ar.bootstrap(v, d, b, bloque, reps=40, semilla=11)
    dos = ar.bootstrap(v, d, b, bloque, reps=40, semilla=11)
    for n in ar.NOMBRES_EST:
        for clave in ("valor", "ic_bajo", "ic_alto", "descartadas"):
            x, y = uno[n][clave], dos[n][clave]
            if isinstance(x, float) and np.isnan(x):
                assert np.isnan(y)
            else:
                assert x == y
    otro = ar.bootstrap(v, d, b, bloque, reps=40, semilla=12)
    assert otro["brecha_0_300"]["valor"] == uno["brecha_0_300"]["valor"]


def test_bootstrap_las_cantidades_salen_de_las_mismas_remuestras(monkeypatch):
    v, d, b, bloque = _arrancador_bootstrap()
    original = ar.estadisticos
    llamadas = []

    def espia(v_, d_, b_, i=None):
        e = original(v_, d_, b_, i)
        if i is not None:
            llamadas.append((np.asarray(i).copy(), e))
        return e

    monkeypatch.setattr(ar, "estadisticos", espia)
    ar.bootstrap(v, d, b, bloque, reps=25, semilla=5)
    assert len(llamadas) == 25
    for i, e in llamadas:
        # A menos B solo puede valer A menos B si las tres salieron de la misma remuestra
        assert e["A_menos_B"] == pytest.approx(e["A"] - e["B"], nan_ok=True)
        # y esa remuestra es la misma para todas las ocho cantidades
        control = original(v[i], d[i], b[i])
        for nombre in ar.NOMBRES_EST:
            assert e[nombre] == pytest.approx(control[nombre], nan_ok=True)
    assert ar.bootstrap(v, d, b, bloque, reps=25, semilla=5)["A_menos_B"]["valor"] == pytest.approx(
        ar.estadisticos(v, d, b)["A_menos_B"])


def test_bootstrap_cuenta_los_bloques():
    v, d, b, bloque = _arrancador_bootstrap()
    est = ar.bootstrap(v, d, b, bloque, reps=10, semilla=3)
    assert est["_bloques"] == 4


# ------------------------------------------------------------------ (d) y (f) sintetico

def _sintetico(n_por_grupo=N_POR_GRUPO) -> dict:
    """Un D con la forma de placebo.marco: un padre y un hijo por evento, con la distancia entre ramas a mano."""
    n = N_GRUPOS * n_por_grupo
    hijo_id = np.arange(1, n + 1, dtype=np.int64)
    hijo_mes = np.full(n, MES, dtype=np.int64)
    hijo_pad = np.arange(n, dtype=np.int64)
    primer = np.zeros(n, dtype=np.int64)
    area = np.array(["A"] * n)
    lat = np.full(n, -38.5)
    tasa = np.full((n, 200), np.nan)
    for p in range(n):
        tasa[p, MES - 6 + PAD:MES + 2 + PAD] = 2.0
    grupo = np.repeat(np.arange(N_GRUPOS), n_por_grupo)
    # los dos grupos cercanos por ramas (menos de 600 m) pierden 30 puntos en el mes 1
    for p in np.flatnonzero(grupo <= 1):
        tasa[p, MES + 1 + PAD] = 1.4
    d = np.array([RANGO_M[g] for g in grupo])
    km = np.where(grupo <= 1, 0.5, 2.5)
    D = {"hijo_id": hijo_id, "hijo_mes": hijo_mes, "hijo_anio": np.full(n, 2000 + MES // 12), "hijo_pad": hijo_pad,
         "primer": primer, "area": area, "lat": lat, "tasa": tasa, "n_mes": 120,
         "par_hijo": np.arange(n, dtype=np.int64), "par_padre": np.arange(n, dtype=np.int64),
         "par_km": km, "par_rumbo": np.zeros(n)}
    D["par_real_ok"] = primer <= hijo_mes - placebo.EDAD_MIN
    D["bloque_5km"] = np.arange(n, dtype=np.int64) // 20   # 30 bloques de 20 eventos
    return {"D": D, "pid": np.arange(10_000, 10_000 + n, dtype=np.int64),
            "par_hijo": hijo_id, "par_padre": D["par_padre"] + 10_000, "par_m": d}


def test_sintetico_hasta_el_alcance_medido():
    C = _sintetico()
    s = ar.muestra(C)
    est = ar.bootstrap(s["idx"][1], s["m_min"], s["banda"], s["bloque"], reps=40)
    cnt = ar.conteos(s["idx"][1], s["m_min"], s["banda"])
    ver, alcance = ar.veredicto_r1(est, cnt, est["_bloques"])
    assert ver == "alcance medido"
    assert alcance == pytest.approx(600.0)
    # las dos bandas cercanas pierden 30 puntos y las otras dos nada
    assert est["brecha_0_300"]["valor"] == pytest.approx(-0.30)
    assert est["brecha_300_600"]["valor"] == pytest.approx(-0.30)
    assert est["brecha_600_1000"]["valor"] == pytest.approx(0.0)
    assert est["brecha_1000_2000"]["valor"] == pytest.approx(0.0)
    assert est["_bloques"] == 30


def test_muestra_saca_los_pares_sin_medir_y_cuenta_el_marco():
    C = _sintetico()
    n = len(C["par_m"])
    # el ultimo par no tiene la rama medida: se saca de la muestra pero queda en el marco
    C2 = {"D": C["D"], "pid": C["pid"], "par_hijo": C["par_hijo"][:-1], "par_padre": C["par_padre"][:-1],
          "par_m": C["par_m"][:-1]}
    s = ar.muestra(C2)
    assert s["n_marco"] == n
    assert len(s["m_min"]) == n - 1
    assert not np.isnan(s["m_min"]).any()


# ------------------------------------------------------------------ (e) diferido

def test_dias_del_mes():
    assert ar._dias_mes(0) == 31          # enero de 2000
    assert ar._dias_mes(1) == 29          # febrero de 2000, bisiesto
    assert ar._dias_mes(12) == 31         # enero de 2001
    assert ar._dias_mes(13) == 28         # febrero de 2001


def test_diferido_de_un_evento_con_respuesta_conocida():
    base = 2.0
    tasa = np.array([1.0])
    c = np.array([0.75])
    dias = np.array([30.0])
    # (0,75 * 2 - 1) * 30 dias * 6,2898 barriles por metro cubico
    assert ar._diferido_evento(base, tasa, c, dias) == pytest.approx(0.5 * 30 * ar.BBL_M3)


def test_diferido_de_un_evento_con_un_mes_sin_dato():
    base = 2.0
    dias = np.array([30.0, 31.0])
    c = np.array([0.75, 0.75])
    # el primer mes con tasa nan no suma ni resta: solo cuenta el segundo
    con_nan = ar._diferido_evento(base, np.array([np.nan, 1.0]), c, dias)
    solo_el_segundo = ar._diferido_evento(base, np.array([np.nan, 1.0]), np.array([np.nan, 0.75]), dias)
    assert con_nan == pytest.approx(solo_el_segundo)
    assert con_nan == pytest.approx(0.5 * 31 * ar.BBL_M3)
    # y un c nan tampoco suma
    assert ar._diferido_evento(base, np.array([1.0]), np.array([np.nan]), np.array([30.0])) == 0.0


def test_diferido_de_un_evento_sin_meses_suma_cero():
    assert ar._diferido_evento(2.0, np.array([np.nan]), np.array([0.5]), np.array([30.0])) == 0.0


# ------------------------------------------------------------------ (g) encabezado congelado

def test_el_encabezado_congelado_no_cambio():
    assert "REGLA FIJADA ANTES DE CORRER" in ar.__doc__
    assert ar.UMBRAL_ALCANCE == pytest.approx(-0.10)
    assert ar.UMBRAL_PLANO == pytest.approx(0.05)
    assert ar.N_MIN == 100
    assert ar.MIN_BLOQUES == 30
    assert ar.CERCA_RAMA_M == pytest.approx(600.0)
    assert ar.CONTAMINADO_RAMA_M == pytest.approx(1000.0)
    assert ar.CONTROL_RAMA_M == pytest.approx(2000.0)
    assert ar.ANIO_S3 == 2023


# ------------------------------------------------------------------ (f) la pagina de la wiki

def _filas_alcance(valores: dict[str, float]) -> list[tuple]:
    """Filas de mart_alcance_rama para los cuatro modelos, con el mismo valor puntual y un IC de 5 puntos a cada lado."""
    filas = []
    for modelo, k in (("principal", 1), ("s1", 1), ("s2", 1), ("s2", -1), ("s3", 1)):
        for nombre in ar.NOMBRES_EST:
            v = valores[nombre]
            n, nr = (None, None) if nombre == "A_menos_B" else (300, 900)
            filas.append((modelo, k, nombre, v, v - 0.05, v + 0.05, 0, n, nr))
    return filas


def _con_marts(real: bool):
    import duckdb
    con = duckdb.connect(":memory:")
    if real:
        valores = {"brecha_0_300": -0.50, "brecha_300_600": -0.20, "brecha_600_1000": -0.09, "brecha_1000_2000": -0.015,
                   "A": -0.28, "B": -0.24, "A_menos_B": -0.04, "C_menos_L": -0.08}
        prueba = [("H-R1", "alcance medido", 1000.0, 1234, 55, 400, 3000), ("H-R2", "no se separa", None, 1234, 55, 400, 3000),
                  ("H-R3", "control contaminado", None, 1234, 55, 400, 3000)]
        dif = [("usual", 500, 3000, -0.23, -0.29, -0.16, 19.2e6, 11.6e6, 28.8e6),
               ("lateral_limpio", 500, 900, -0.22, -0.30, -0.15, 18.4e6, 11.5e6, 27.2e6)]
        anio = [(2021, 400, 10, 20, 30, 90, 200), (2023, 834, 20, 40, 60, 180, 400), (0, 1234, 30, 60, 90, 270, 600)]
    else:
        valores = {n: float("nan") for n in ar.NOMBRES_EST}
        prueba = [(p, "sin muestra", None, 50, 10, 400, 3000) for p in ("H-R1", "H-R2", "H-R3")]
        dif = []
        anio = [(2021, 50, 1, 2, 3, 4, 5), (0, 50, 1, 2, 3, 4, 5)]
    ar.escribir(con, {"mart_alcance_rama": _filas_alcance(valores), "mart_alcance_rama_prueba": prueba,
                      "mart_alcance_rama_anio": anio, "mart_alcance_rama_diferido": dif})
    con.execute("create table mart_trayectoria_cobertura (nivel varchar, anio integer, total integer, medidos integer, "
                "horizontales integer, horizontales_en_fuente integer, horizontales_medidos integer)")
    con.executemany("insert into mart_trayectoria_cobertura values ('hijo', ?, 100, 80, 100, 100, ?)",
                    [(2021, 90), (2023, 80), (2024, 40), (2025, 25)])
    con.execute("create table mart_diferido_rango (variante varchar, orden integer, diferido_bbl double, eventos integer, "
                "meses_padre integer, por_evento_bbl double, brecha_previa double)")
    con.executemany("insert into mart_diferido_rango values (?, ?, ?, 1, 1, 1.0, null)",
                    [("original", 1, 11.4e6), ("sin_duplicar", 2, 8.7e6), ("neto_previa", 3, 6.4e6)])
    return con


def test_pagina_con_los_veredictos_de_hoy():
    page = ar.pagina_alcance_rama(_con_marts(True))
    assert page.startswith("# Alcance y dilución de la huella medidos entre ramas\n")
    for v in ("**alcance medido**", "**no se separa**", "**control contaminado**"):
        assert v in page
    assert "76d9831" in page and "llega hasta 1.000 m entre ramas" in page
    assert "cubren el 85% de los hijos horizontales fracturados de 2016 a 2023 pero solo el 40% de los de 2024 y el 25% de los de 2025" in page
    assert "así que la muestra es sobre todo de 2016 a 2023: el 100% de los eventos son de hijos fracturados hasta 2023" in page
    assert "el rango del estudio (6,4 a 11,4 millones de barriles)" in page
    assert "| control lateral limpio | 500 | 900 |" in page and "los intervalos se solapan" in page
    assert "| Total | 1.234 | 30 | 60 | 90 | 270 | 600 |" in page
    assert "La regla esperaba que el control de superficie subestimara el diferido" in page
    assert "los intervalos del diferido de los meses 0 a 6 se solapan" in page
    assert chr(0x2013) not in page and chr(0x2014) not in page


def test_pagina_sin_muestra_no_dice_el_alcance():
    page = ar.pagina_alcance_rama(_con_marts(False))
    assert page.count("**sin muestra**") == 3
    assert "llega hasta" not in page and "rinden" not in page and "Contra el control lateral limpio" not in page
    assert "Los datos no deciden el alcance" in page and "76d9831" in page
    assert chr(0x2013) not in page and chr(0x2014) not in page
    assert "recálculo descriptivo" not in page


def test_los_veredictos_de_la_pagina_son_los_de_la_regla():
    con = _con_marts(True)
    con.execute("update mart_alcance_rama_prueba set veredicto = 'gradiente', alcance_m = null where prueba = 'H-R1'")
    con.execute("update mart_alcance_rama_prueba set veredicto = 'la distancia de superficie diluye la huella' where prueba = 'H-R2'")
    con.execute("update mart_alcance_rama_prueba set veredicto = 'control limpio' where prueba = 'H-R3'")
    page = ar.pagina_alcance_rama(con)
    assert "el alcance es de por lo menos 2.000 m entre ramas y no se midió el borde" in page
    assert "subestima la brecha entre ramas" in page and "no se ensucia" in page
    for v in ("gradiente", "la distancia de superficie diluye la huella", "control limpio"):
        assert f"**{v}**" in page


def test_cada_afirmacion_de_alcance_coincide_con_la_pagina():
    import re
    from pipeline import claims
    page = ar.pagina_alcance_rama(_con_marts(True))
    lista = [c for c in claims._claims_alcance_rama() if c.fichero == claims.W_ALCANCE]   # las del README se prueban aparte
    assert len(lista) > 100
    ausentes = []
    for c in lista:
        assert c.id.startswith("alcance_")
        m = re.search(c.patron, page, re.S)
        assert re.compile(c.patron).groups == 1, c.id
        if m is None:
            ausentes.append(c)
    assert all(c.opcional for c in ausentes), [c.id for c in ausentes if not c.opcional]
    # las que dependen de un veredicto que esta en la pagina de prueba no faltan
    assert not {c.id for c in ausentes} & {"alcance_lectura_alcance_m@wiki", "alcance_h2_A_brecha@wiki",
                                           "alcance_lectura_c_menos_l@wiki", "alcance_h3_dif_usual_bbl@wiki"}


def test_las_afirmaciones_del_readme_traen_un_grupo_y_coinciden_con_su_fila():
    import re
    from pathlib import Path
    from pipeline import claims
    texto = (Path(__file__).resolve().parents[1] / claims.R).read_text(encoding="utf-8")
    del_readme = [c for c in claims._claims_alcance_rama() if c.fichero == claims.R]
    assert len(del_readme) >= 10
    for c in del_readme:
        assert re.compile(c.patron).groups == 1, c.id
        assert re.search(c.patron, texto, re.S), c.id


def test_la_frase_del_diferido_sale_de_los_intervalos():
    con = _con_marts(True)
    con.execute("update mart_alcance_rama_diferido set diferido_bbl = 31e6, diferido_ic_bajo = 28e6, diferido_ic_alto = 35e6 "
                "where control = 'usual'")
    page = ar.pagina_alcance_rama(con)
    assert "no lo subestima, al revés de lo que esperaba la regla" in page
    con.execute("update mart_alcance_rama_diferido set diferido_bbl = 5e6, diferido_ic_bajo = 1e6, diferido_ic_alto = 6e6 "
                "where control = 'usual'")
    assert "el control de superficie lo subestima, como esperaba la regla" in ar.pagina_alcance_rama(con)


def test_h_r2_no_dice_que_la_distancia_de_superficie_diluye_con_un_valor_positivo():
    est = {"A_menos_B": {"valor": 0.01, "ic_bajo": -0.1, "ic_alto": 0.05}}
    cnt = {"n_cerca": 500, "n_control": 500, "n_sup_cerca": 500, "n_sup_control": 500}
    assert ar.veredicto_r2(est, cnt) == ar.VEREDICTOS_R2[2]
    est["A_menos_B"] = {"valor": -0.2, "ic_bajo": -0.3, "ic_alto": -0.05}
    assert ar.veredicto_r2(est, cnt) == ar.VEREDICTOS_R2[1]
