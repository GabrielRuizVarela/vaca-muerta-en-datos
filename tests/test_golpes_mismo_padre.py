"""Golpes en el mismo mes con el padre como su propio control: cada padre con dos meses aislados y distinta k.

El panel sintetico tiene padres que se diferencian mucho entre si (alpha_i con dispersion grande) y dos golpes
aislados por padre con distinta cantidad de hijos, asi que el estimador intra-padre tiene que recuperar el costo
fijo y el costo por hijo inyectados."""
import calendar
import re

import duckdb
import numpy as np
import pytest

from pipeline import golpes_mismo_mes as gm
from pipeline import golpes_mismo_padre as gp
from pipeline import linaje

N_MES = 200
REPS = 60
A0 = 10.0          # costo fijo inyectado por mes de golpe (dias de base)
B0 = 3.0           # costo por hijo inyectado (dias de base)
SD_ALPHA = 25.0    # dispersion entre padres de su propio costo fijo (mucho mas que b)
GAP = 10           # meses entre los dos golpes del mismo padre
MES_LOS = 4        # meses en los que se reparte la perdida
PANEL = {}


def _base(mes: int) -> float:
    """El caudal base del padre en el mes mes (los meses -6 a -4 del golpe)."""
    return 50.0 * np.exp(-0.01 * (mes - 5))


def sintetico(n_padres: int = 220, n_controles: int = 40, seed: int = 11, ruido: float = 0.0,
              alpha_sd: float = SD_ALPHA, a0: float = A0, b0: float = B0) -> dict:
    """Un panel con los padres del modelo: cada padre tiene dos golpes aislados separados GAP meses, con distinta
    cantidad de hijos, y un costo fijo propio (alpha_i) repartido en los meses del golpe.

    Los dos golpes de un padre caen en el mismo ano y en el mismo grupo de edad (para que el control de ano y el de
    edad no varien dentro del padre) y cada padre tiene su propio pad."""
    rng = np.random.default_rng(seed)
    alpha = rng.normal(0.0, alpha_sd, n_padres)
    alpha = alpha - alpha.mean()  # la media de alpha_i es cero: a sale como el costo fijo inyectado
    hijo_mes, hijo_pad, ph, pp, km = [], [], [], [], []
    losses = []
    hijo_n = 0
    primero = np.zeros(n_padres + n_controles, dtype=np.int64)
    for i in range(n_padres):
        anio = int(rng.integers(0, 2))
        m1 = (96 if anio == 0 else 108) + int(rng.integers(0, 2))
        m2 = m1 + GAP
        k1 = 1 + int(rng.integers(0, 2))
        k2 = 3 + int(rng.integers(0, 2))
        primero[i] = m1 - (12 if rng.integers(0, 2) else 30)  # el grupo de edad es el mismo en los dos golpes
        for mes, k in ((m1, k1), (m2, k2)):
            for _ in range(k):
                hijo_mes.append(mes)
                hijo_pad.append(2 * i + (0 if mes == m1 else 1))
                ph.append(hijo_n)
                pp.append(i)
                km.append(rng.uniform(0.3, 0.9))
                hijo_n += 1
            losses.append((i, mes, k))
    for c in range(n_controles):
        mes = 100 + (c * 7) % 60
        for _ in range(2):
            hijo_mes.append(mes)
            hijo_pad.append(10 ** 6 + c)
            ph.append(hijo_n)
            pp.append(n_padres + c)
            km.append(rng.uniform(2.5, 4.5))
            hijo_n += 1
    hijo_mes = np.array(hijo_mes, dtype=np.int64)
    n_wells = n_padres + n_controles
    t = np.arange(N_MES)
    tasa = np.full((n_wells, N_MES + 2 * gm.PAD), np.nan)
    ruido_panel = rng.normal(0.0, ruido, (n_wells, N_MES))
    for i in range(n_wells):
        tasa[i, gm.PAD:gm.PAD + N_MES] = 50.0 * np.exp(-0.01 * t) * (1 + ruido_panel[i])
    for i, mes, k in losses:
        perdida = alpha[i] + a0 + b0 * k
        base = _base(mes)
        for j in range(MES_LOS):
            dias = calendar.monthrange(2000 + (mes + j) // 12, (mes + j) % 12 + 1)[1]
            tasa[i, gm.PAD + mes + j] -= base * perdida / MES_LOS / dias
    D = {"hijo_id": np.arange(hijo_n) + 1000, "hijo_mes": hijo_mes,
         "hijo_anio": 2000 + hijo_mes // 12, "hijo_pad": np.array(hijo_pad, dtype=np.int64),
         "primer": primero, "area": np.array(["A"] * n_wells), "lat": np.full(n_wells, -38.5),
         "tasa": tasa, "par_hijo": np.array(ph), "par_padre": np.array(pp), "par_km": np.array(km),
         "par_rumbo": np.zeros(len(pp)), "n_mes": N_MES,
         "operador": np.array(["A", "B", "C", "D"])[rng.integers(0, 4, n_wells)],
         "pad_padre": np.arange(n_wells, dtype=np.int64)}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - 6
    return D


def _panel(n_padres: int = 220, n_controles: int = 40, seed: int = 11) -> dict:
    """El panel estandar, guardado para no regenerarlo en cada prueba."""
    clave = (n_padres, n_controles, seed)
    if clave not in PANEL:
        PANEL[clave] = sintetico(n_padres, n_controles, seed)
    return PANEL[clave]


def _prueba(t: dict) -> dict:
    return {(f[0], f[1]): f for f in t[gp.mart("_prueba")]}


def test_el_sintetico_tiene_dos_golpes_aislados_por_padre_con_distinta_k():
    e, idx = gp.muestra(_panel())
    c = gp.conteos(e, idx)
    assert c["aislados_con_ventana"] == 2 * 220
    assert c["padres_partida"] == 220 and c["padres_2_meses"] == 220
    assert c["padres_k_distinto"] == 220 and c["meses_restringida"] == 440
    assert c["padres"] == 220 and c["pads"] == 220 and c["valores_k"] == 4
    k = e["k"][idx]
    assert set(k.tolist()) == {1, 2, 3, 4}
    padre = e["padre"][idx]
    for p in np.unique(padre):
        kk = k[padre == p]
        assert len(kk) == 2 and kk[0] != kk[1]
    assert np.all(e["aislado"][idx])


def test_el_estimador_intra_padre_recupera_el_costo_fijo_y_el_costo_por_hijo():
    e, idx = gp.muestra(_panel())
    a, b = gp.ajuste(e, idx, e["perdida"], e["padre"][idx])
    assert abs(a - A0) < 0.1, a
    assert abs(b - B0) < 0.05, b
    # los padres tienen su propio costo fijo, muy disperso: comparar cada padre consigo mismo lo saca
    assert np.std(e["perdida"][idx] - e["perdida"][idx].mean()) > 10


def test_el_modelo_agrupado_de_83_esta_mas_lejos_de_b_que_el_intra_padre():
    e, idx = gp.muestra(_panel())
    a, b = gp.ajuste(e, idx, e["perdida"], e["padre"][idx])
    a83, b83 = gm.ajuste(e, idx, e["perdida"])
    assert abs(b - B0) < abs(b83 - B0), (b, b83)


def test_muestra_saca_a_los_padres_con_un_solo_mes_o_con_la_misma_k():
    D = sintetico(n_padres=8, n_controles=10)
    e, idx = gp.muestra(D)
    c = gp.conteos(e, idx)
    assert c["padres_k_distinto"] == 8 and c["meses_restringida"] == 16
    # un padre al que se le cae la ventana de uno de sus golpes queda con un solo mes y sale
    D1 = dict(D)
    D1["tasa"] = D["tasa"].copy()
    padre = int(e["padre"][idx][0])
    mes = int(e["mes"][idx][0])
    D1["tasa"][padre, gm.PAD + mes + 3] = np.nan
    e2, idx2 = gp.muestra(D1)
    assert len(idx2) == len(idx) - 2
    # un padre cuyos dos golpes tienen la misma k sale
    D2 = sintetico(n_padres=8, n_controles=10)
    hijos = np.flatnonzero((D2["par_padre"] == 0) & (D2["par_km"] < gm.KM_CERCA))
    m1 = int(D2["hijo_mes"][hijos].min())
    m2 = int(D2["hijo_mes"][hijos].max())
    segundo = hijos[D2["hijo_mes"][hijos] == m2]
    D2["hijo_mes"][segundo[0]] = m1  # el segundo golpe queda con la misma k que el primero
    e3, idx3 = gp.muestra(D2)
    c3 = gp.conteos(e3, idx3)
    assert c3["padres_partida"] == 8 and c3["padres_2_meses"] == 8
    assert c3["padres_k_distinto"] == 7 and c3["meses_restringida"] == 14


def test_el_bootstrap_trata_un_pad_sacado_dos_veces_como_dos_padres():
    e, idx = gp.muestra(_panel(n_padres=8, n_controles=10))
    vistos = []

    def fn(idx_r, grupo_r):
        vistos.append((idx_r.copy(), grupo_r.copy()))
        return len(np.unique(grupo_r))

    gp._boot(e, idx, 8, gp.SEMILLA_PADRE, fn)
    assert vistos
    repetido = False
    for idx_r, g_r in vistos:
        padre = e["padre"][idx_r]
        for g in np.unique(g_r):
            filas = padre[g_r == g]
            # una etiqueta de padre junta filas de un solo padre: un pad que sale dos veces no se junta consigo mismo
            assert len(np.unique(filas)) == 1
        for p in np.unique(padre):
            # un padre con mas de una etiqueta es un pad que salio mas de una vez: son padres distintos
            repetido = repetido or len(np.unique(g_r[padre == p])) > 1
    assert repetido


def test_a_no_depende_de_la_categoria_de_referencia_de_los_dummies():
    e, idx = gp.muestra(_panel(n_padres=40, n_controles=10))
    a, b = gp.ajuste(e, idx, e["perdida"], e["padre"][idx])
    e2 = dict(e)
    e2["anio"] = np.where(e["anio"] == 2008, 2020, 2001)  # cambia cual es la categoria de referencia
    a2, b2 = gp.ajuste(e2, idx, e2["perdida"], e2["padre"][idx])
    assert abs(a - a2) < 1e-9 and abs(b - b2) < 1e-9


def test_veredicto_en_el_orden_de_la_regla():
    assert gp.veredicto(gp.PADRES_MIN - 1, gp.MESES_MIN, 5.0, 0.9, 0.5, 1.0) == "sin muestra"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN - 1, 5.0, 0.9, 0.5, 1.0) == "sin muestra"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, 0.0, 0.9, 0.5, 1.0) == "sin perdida medible"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, float("nan"), 0.9, 0.5, 1.0) == "sin perdida medible"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, 1.0, 0.9, 0.1, 1.0) == "agrupar ahorra"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, 1.0, 0.9, 0.1, 0.2) == "agrupar ahorra"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, 1.0, 0.1, -0.1, 0.2) == "agrupar no ahorra"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, 1.0, 0.2, 0.1, 0.3) == "no firme"
    assert gp.veredicto(gp.PADRES_MIN, gp.MESES_MIN, 1.0, 0.3, 0.0, 0.6) == "no firme"
    assert set(gm.FRASE) == set(gm.VEREDICTOS)


def test_calcular_da_el_veredicto_y_es_determinista():
    t = gp.calcular(_panel(), reps=REPS)
    p = _prueba(t)
    assert p[("principal", "phi")][6] == "agrupar ahorra", p[("principal", "phi")]
    assert abs(p[("principal", "a")][2] - A0) < 0.1
    assert abs(p[("principal", "b")][2] - B0) < 0.05
    assert p[("principal", "padres")][2] == 220 and p[("principal", "pads")][2] == 220
    assert p[("principal", "meses")][2] == 440
    assert p[("principal", "valores_k")][2] == 4
    assert p[("conteo", "padres_partida")][2] == 220
    assert p[("conteo", "padres_2_meses")][2] == 220
    assert p[("conteo", "padres_k_distinto")][2] == 220
    assert p[("conteo", "meses_restringida")][2] == 440
    assert p[("conteo", "ultimo_mes_indice")][2] == N_MES
    assert ("S1", "phi_m3") in p and ("S2", "phi") in p and ("agrupado83", "b") in p
    assert ("principal", "b_negativas") in p and ("principal", "descartadas") in p
    t1 = gp.calcular(_panel(), reps=REPS)
    assert t1 == t and set(t1) == {"mart_golpes_mismo_padre", "mart_golpes_mismo_padre_prueba"}
    for filas in t1.values():
        assert not any(isinstance(x, float) and np.isnan(x) for f in filas for x in f)
    assert len(t1["mart_golpes_mismo_padre"]) == len(gm.GRUPOS_K)


def test_calcular_con_muestra_chica_da_sin_muestra():
    t = gp.calcular(sintetico(n_padres=20, n_controles=10), reps=REPS)
    p = _prueba(t)
    assert p[("principal", "phi")][6] == "sin muestra"
    assert p[("conteo", "padres_k_distinto")][2] == 20
    # con un solo padre no hay bootstrap: solo el veredicto y los conteos
    t2 = gp.calcular(sintetico(n_padres=1, n_controles=10), reps=REPS)
    p2 = _prueba(t2)
    assert p2[("principal", "phi")][6] == "sin muestra"
    assert ("principal", "a") not in p2
    assert ("conteo", "meses_restringida") in p2


def _pagina(tablas: dict, colorado: dict | None = None) -> str:
    con = duckdb.connect()
    gp.escribir(con, tablas)
    if colorado:
        gp.escribir(con, colorado, "colorado")
    return gp.pagina_golpes_mismo_padre(con)


def test_la_pagina_se_escribe_y_se_lee():
    t = gp.calcular(_panel(), reps=REPS)
    con = duckdb.connect(":memory:")
    gp.escribir(con, t)
    m = gp.marts(con)
    assert m is not None
    assert len(m["k"]) == len(gm.GRUPOS_K)
    assert ("principal", "phi") in m["p"]
    texto = (linaje.PIPELINE_DIR / "golpes_mismo_padre.py").read_text(encoding="utf-8")
    assert set(linaje._ESCRIBIR.findall(texto)) == {"mart_golpes_mismo_padre", "mart_golpes_mismo_padre_prueba",
                                                     "mart_golpes_mismo_padre_colorado",
                                                     "mart_golpes_mismo_padre_colorado_prueba"}
    with pytest.raises(ValueError, match="wyoming"):
        gp.escribir(duckdb.connect(), {}, "wyoming")


def test_la_pagina_tiene_las_secciones_y_sin_rayas_largas():
    txt = _pagina(gp.calcular(_panel(), reps=REPS))
    assert chr(0x2013) not in txt and chr(0x2014) not in txt
    assert not re.search(r"\bnan\b", txt)
    for seccion in ("## Lectura", "## El modelo", "## Pérdida por cantidad de hijos en el mes", "## Muestra",
                    "## Regla fijada antes de correr", "## Qué no prueba"):
        assert seccion in txt, seccion
    assert "# Golpes en el mismo mes, con el padre como su propio control" in txt
    assert "## Colorado" not in txt and "| Colorado |" not in txt
    assert "**agrupar ahorra**" in txt


def test_la_pagina_con_sin_muestra_dice_los_conteos_y_los_umbrales():
    txt = _pagina(gp.calcular(sintetico(n_padres=20, n_controles=10), reps=REPS))
    assert "**sin muestra**" in txt
    assert "regla pide" in txt
    assert chr(0x2013) not in txt and chr(0x2014) not in txt


def test_la_pagina_con_colorado_trae_su_seccion():
    vm = gp.calcular(_panel(), reps=REPS)
    co = gp.calcular(sintetico(n_padres=220, n_controles=40, seed=3), reps=REPS)
    txt = _pagina(vm, co)
    assert "## Colorado (confirmatoria)" in txt and "| Colorado | IC 95% |" in txt
    assert "Colorado (confirmatoria, misma regla): **agrupar ahorra**" in txt
    assert chr(0x2013) not in txt and chr(0x2014) not in txt
