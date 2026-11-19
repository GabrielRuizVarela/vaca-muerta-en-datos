"""Ventana de gas con eventos sinteticos: caida de gas despues de la fractura del hijo."""
import numpy as np
import pytest

from pipeline import gas, placebo

N_HIJOS = 70
N_MES = 220
REPS = 60
NOMBRES = [c[0] for c in gas.COLS_GAS]


def sintetico_gas(efecto: float = 0.25, seed: int = 3, solo_dias: bool = False) -> dict:
    """Como tests/test_placebo.py sintetico: 12 cercanos y 30 controles por hijo, caudal que baja 1% por mes.

    Los cercanos pierden `efecto` en los meses 0 a 2. Con `solo_dias` la perdida va solo a la tasa por dia
    calendario (dias sin producir) y la tasa por dia efectivo queda intacta.
    """
    rng = np.random.default_rng(seed)
    hijo_mes = rng.integers(100, 150, N_HIJOS).astype(np.int64)
    ph, pp, km, rumbo = [], [], [], []
    for h in range(N_HIJOS):
        for j in range(42):
            ph.append(h)
            pp.append(len(pp))
            km.append(rng.uniform(0.3, 0.9) if j < 12 else rng.uniform(2.0, 4.5))
            rumbo.append(rng.uniform(0, 180))
    n_par = len(pp)
    tasa = np.full((n_par, N_MES + 2 * placebo.PAD), np.nan)
    tasa_ef = np.full((n_par, N_MES + 2 * placebo.PAD), np.nan)
    t = np.arange(N_MES)
    for i in range(n_par):
        h, cerca = ph[i], km[i] < 1
        y = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, 0.03, N_MES))
        yv = y.copy()
        if cerca:
            yv[hijo_mes[h]:hijo_mes[h] + 3] *= 1 - efecto
        tasa[i, placebo.PAD:placebo.PAD + N_MES] = yv
        tasa_ef[i, placebo.PAD:placebo.PAD + N_MES] = y if solo_dias else yv
    area = np.array(["A", "B", "C"])[np.arange(n_par) % 3]
    D = {"hijo_id": np.arange(N_HIJOS) + 1000, "hijo_mes": hijo_mes, "hijo_anio": 2000 + hijo_mes // 12,
         "hijo_pad": np.arange(N_HIJOS), "primer": np.zeros(n_par, dtype=np.int64), "area": area,
         "lat": np.full(n_par, -38.5), "tasa": tasa, "tasa_ef": tasa_ef,
         "dias": np.full((n_par, N_MES + 2 * placebo.PAD), 30.0),
         "bloque_5km": np.arange(N_HIJOS) // 2,
         "par_hijo": np.array(ph), "par_padre": np.array(pp),
         "par_km": np.array(km), "par_rumbo": np.array(rumbo), "n_mes": N_MES}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - placebo.EDAD_MIN
    return D


def por_clave(D: dict, reps: int = REPS) -> dict:
    return {(r[0], r[1]): dict(zip(NOMBRES, r)) for r in gas.filas_brecha(D, reps=reps)}


def test_penalizacion_recuperada_y_veredicto_sostiene():
    D = sintetico_gas(efecto=0.25)
    v1 = por_clave(D)[("V", 1)]
    assert v1["brecha"] == pytest.approx(-0.25, abs=0.05)
    assert v1["ic_alto_5km"] < 0
    fechas = placebo.tabla_fechas(D, reps=REPS, base_min=gas.BASE_MIN_GAS)
    pre = placebo.tabla_pretendencia(D, base=placebo.BASE_LIMPIA, reps=REPS, base_min=gas.BASE_MIN_GAS)
    c1, c2 = gas.c1_pasa(fechas), gas.c2_pasa(pre)
    assert (c1, c2) == (True, True)
    assert gas.veredicto(v1, c1, c2)[0] == "sostiene"


def test_nulo_da_no_se_sostiene():
    v1 = por_clave(sintetico_gas(efecto=0.0))[("V", 1)]
    assert abs(v1["brecha"]) < 0.05
    assert v1["ic_bajo_5km"] <= 0 <= v1["ic_alto_5km"]
    assert gas.veredicto(v1, True, True)[0] == "no se sostiene"


def test_muestra_chica_da_sin_muestra():
    D = sintetico_gas(efecto=0.25)
    sel = D["par_hijo"] < 5
    for k in ("par_hijo", "par_padre", "par_km", "par_rumbo", "par_real_ok"):
        D[k] = D[k][sel]
    v1 = por_clave(D)[("V", 1)]
    assert v1["n_near"] < gas.MIN_CERCANOS
    assert gas.veredicto(v1, True, True)[0] == "sin muestra"


def test_dos_corridas_dan_las_mismas_filas():
    D = sintetico_gas()
    assert gas.filas_brecha(D, reps=REPS) == gas.filas_brecha(D, reps=REPS)


def test_veredicto_puro_marca_el_control_que_falla():
    prim = {"n_near": 200, "n_ctrl": 200, "bloques_5km": 35, "brecha": -0.2,
            "ic_bajo_5km": -0.3, "ic_alto_5km": -0.1}
    v, t = gas.veredicto(prim, False, True)
    assert v == "no firme" and "C1" in t
    v, t = gas.veredicto(prim, True, False)
    assert v == "no firme" and "C2" in t
    assert gas.veredicto(prim, True, True)[0] == "sostiene"


def test_lectura_dias_separa_dias_de_caudal():
    f = por_clave(sintetico_gas(efecto=0.25, solo_dias=True))
    assert gas.lectura_dias(f[("V", 1)], f[("E", 1)]) == \
        "la caida del volumen esta en los dias producidos y no en el caudal por dia"
    f = por_clave(sintetico_gas(efecto=0.25))
    assert gas.lectura_dias(f[("V", 1)], f[("E", 1)]) == "la caida tambien esta en el caudal por dia"


def test_gor_doble_en_cercanos_da_brecha_uno():
    ancho = 2 * placebo.PAD + 20
    gv = np.full((2, ancho), np.nan)
    ov = np.full((2, ancho), np.nan)
    gv[:, 7 + placebo.PAD:10 + placebo.PAD] = 10.0
    ov[:, 7 + placebo.PAD:10 + placebo.PAD] = 10.0
    gv[0, 11 + placebo.PAD] = 20.0
    gv[1, 11 + placebo.PAD] = 10.0
    ov[:, 11 + placebo.PAD] = 10.0
    m = {"padre": np.array([0, 1]), "mes": np.array([10, 10]),
         "banda": np.array([0, 2]), "clave": np.array([0, 1])}
    fila = gas.gor_brecha(gv, ov, m, ks=(1,), reps=10)[0]
    assert fila[0] == 1 and (fila[1], fila[2]) == (1, 1)
    assert fila[5] == pytest.approx(1.0)


def test_marco_base_min_por_defecto_no_cambia():
    D = sintetico_gas()
    a = placebo.marco(D, D["hijo_mes"], ks=(1, 6))
    b = placebo.marco(D, D["hijo_mes"], ks=(1, 6), base_min=placebo.BASE_MIN)
    for k in ("padre", "hijo", "mes", "banda", "clave"):
        assert np.array_equal(a[k], b[k])
    for k in (1, 6):
        assert np.array_equal(a["idx"][k], b["idx"][k], equal_nan=True)


def test_diferido_positivo_con_efecto():
    d = gas.diferido(sintetico_gas(efecto=0.25))
    assert d["eventos"] > 0 and d["mediana"] > 0


def _marts_gas(D: dict):
    import duckdb

    from pipeline import costo
    con = duckdb.connect(":memory:")
    filas = gas.filas_brecha(D, reps=REPS)
    costo._escribir(con, "mart_gas", gas.COLS_GAS, filas)
    fechas = placebo.tabla_fechas(D, reps=REPS, base_min=gas.BASE_MIN_GAS)
    costo._escribir(con, "mart_gas_fechas", placebo.COLS_FECHAS, fechas)
    pre = placebo.tabla_pretendencia(D, base=placebo.BASE_LIMPIA, reps=REPS, base_min=gas.BASE_MIN_GAS)
    costo._escribir(con, "mart_gas_pretendencia", placebo.COLS_PRE, pre)
    costo._escribir(con, "mart_gas_gor", placebo.COLS_PRE, [(1, 50, 300, 0.95, 0.96, -0.01, -0.03, 0.01),
                                                             (6, 48, 290, 0.90, 0.90, 0.0, -0.02, 0.02)])
    c = {(r[0], r[1]): dict(zip(NOMBRES, r)) for r in filas}
    v1, v6, e1 = c[("V", 1)], c[("V", 6)], c[("E", 1)]
    c1, c2 = gas.c1_pasa(fechas), gas.c2_pasa(pre)
    v, t = gas.veredicto(v1, c1, c2)
    dif = gas.diferido(D)
    costo._escribir(con, "mart_gas_veredicto", gas.COLS_VEREDICTO,
                    [(v, t, c1, c2, None if v == "sin muestra" else v1["ic_bajo_5km"], gas.lectura_cierre(v6),
                      gas.lectura_dias(v1, e1), dif["mediana"], dif["total"], dif["eventos"])])
    return con, v


def test_pagina_sin_rayas_con_veredicto_secciones_y_cota():
    con, v = _marts_gas(sintetico_gas(efecto=0.25))
    texto = gas.pagina_gas(con)
    assert v == "sostiene" and "**Veredicto: sostiene.**" in texto
    for raya in (chr(0x2013), chr(0x2014)):
        assert raya not in texto
    for seccion in ("## Resumen", "## Regla fijada antes de correr", "## Resultados", "## Qué quiere decir para un operador", "## Límites"):
        assert seccion in texto
    assert "Cota superior de la caída del mes 1 compatible con el dato público: " in texto
    assert "brecha del índice de la relación gas petróleo es -1,0 puntos al mes 1" in texto


def test_pagina_sin_muestra_no_da_cota():
    D = sintetico_gas(efecto=0.25)
    D = dict(D, par_km=np.where(D["par_km"] < 1, 1.5, D["par_km"]))  # sin padres cercanos
    con, v = _marts_gas(D)
    texto = gas.pagina_gas(con)
    assert v == "sin muestra" and "**Veredicto: sin muestra.**" in texto
    assert "Cota superior" not in texto


def test_c2_sin_ic_o_sin_fila_no_pasa():
    nan = float("nan")
    assert gas.c2_pasa([(-1, 50, 300, 0.9, 1.0, -0.08, nan, nan)]) is False
    assert gas.c2_pasa([(-2, 50, 300, 0.9, 1.0, -0.08, -0.1, -0.05)]) is False
    assert gas.c2_pasa([(-1, 50, 300, 0.9, 1.0, -0.03, nan, nan)]) is True
    assert gas.c2_pasa([(-1, 50, 300, 0.9, 1.0, -0.08, -0.12, 0.01)]) is True


def test_diferido_sin_controles_no_cuenta_eventos():
    D = sintetico_gas(efecto=0.25)
    D = dict(D, par_km=np.where(D["par_km"] >= 1, 0.5, D["par_km"]))  # todos cercanos, ningun control
    assert gas.diferido(D)["eventos"] == 0


def test_lectura_no_firme_sin_forma_no_dice_que_cae():
    ver = {"veredicto": "no firme", "c2_pasa": False, "dias_o_caudal": None, "cierre": "se cierra a los 6 meses"}
    texto = "\n".join(gas._lectura_operador(ver, forma=False, previa=0.08))
    assert "produce menos gas" not in texto and "no alcanza para decir" in texto
    texto = "\n".join(gas._lectura_operador(ver, forma=True, previa=0.08))
    assert "ya se separaba de los controles" in texto and "rindiendo menos" not in texto
