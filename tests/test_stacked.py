"""Estimador apilado (porcion E) en datos sinteticos, sin warehouse.

Cada grupo (bloque) tiene un padre y muchos controles a 2 a 5 km. Los padres arrancan mas bajos y caen mas rapido antes
de g (seleccion) y a los tratados se les planta un efecto en e = 1."""
import numpy as np

from pipeline import causal
from pipeline import stacked as st

T = 60
G0 = 30                      # mes del primer golpe de los padres (por encima de EDAD_MIN y de la ventana de base)


def _sintetico(n_grupos=70, n_ctrl=140, efecto=0.0, semilla=7, sin_controles_en=(), radio=(2.3, 4.7)):
    """D con n_grupos de (1 padre + n_ctrl controles); `efecto` en puntos de indice a restar a los padres en e = 1."""
    rng = np.random.default_rng(semilla)
    n = n_grupos * (n_ctrl + 1)
    lat, lon = np.zeros(n), np.zeros(n)
    bloque = np.zeros(n, dtype=np.int64)
    operador = np.empty(n, dtype=object)
    nivel, pend = np.zeros(n), np.zeros(n)
    es_padre = np.zeros(n, dtype=bool)
    g_pad = np.zeros(n, dtype=np.int64)
    for k in range(n_grupos):
        a = k * (n_ctrl + 1)
        centro_lat, centro_lon = -38.0 + (k // 10) * 0.5, -69.0 + (k % 10) * 0.5     # grupos a mas de 50 km
        lat[a], lon[a] = centro_lat, centro_lon
        ang = rng.uniform(0, 2 * np.pi, n_ctrl)
        rad = rng.uniform(radio[0], radio[1], n_ctrl) / 111.32
        lat[a + 1:a + 1 + n_ctrl] = centro_lat + rad * np.sin(ang)
        lon[a + 1:a + 1 + n_ctrl] = centro_lon + rad * np.cos(ang) / np.cos(np.radians(centro_lat))
        bloque[a:a + 1 + n_ctrl] = k
        operador[a:a + 1 + n_ctrl] = ("A", "B", "C")[k % 3]
        es_padre[a] = True
        g_pad[a] = G0 + (k % 4)
        # seleccion: el padre arranca mas bajo y cae mas rapido que los controles
        nivel[a], pend[a] = rng.normal(1.0, 0.35), rng.normal(-0.03, 0.01)
        nivel[a + 1:a + 1 + n_ctrl] = rng.normal(1.2, 0.35, n_ctrl)
        pend[a + 1:a + 1 + n_ctrl] = rng.normal(-0.02, 0.01, n_ctrl)
        if k in sin_controles_en:
            nivel[a + 1:a + 1 + n_ctrl] += 8.0
    meses = np.arange(T)
    tasa = np.exp(nivel[:, None] + pend[:, None] * meses[None, :]) * np.exp(rng.normal(0, 0.02, (n, T)))
    for i in np.flatnonzero(es_padre):
        g = g_pad[i]
        base = tasa[i, g - 6:g - 3].mean()
        tasa[i, g + 1] -= efecto * base
    km_min = np.full((n, T), np.inf)
    km_min[es_padre, g_pad[es_padre]] = 0.5
    km_falso = np.full((n, T), np.inf)
    falsos = np.flatnonzero(~es_padre & (rng.random(n) < 0.2))
    km_falso[falsos, 25] = 4.0
    primer = np.zeros(n, dtype=np.int64)
    return causal._armar(np.arange(n), operador, lat, lon, primer, bloque, 0, T - 1, tasa, np.zeros((n, T)),
                         np.ones((n, T)), tasa.copy(), ~np.isnan(tasa), km_min, km_falso,
                         np.full((n, T), -1, dtype=np.int64), {})


def test_pendiente_necesita_al_menos_tres_meses():
    meses = np.arange(-9, -3)
    y = np.exp(2.0 - 0.1 * meses)
    assert abs(st.pendiente_mco(y[None, :])[0] - (-0.1)) < 1e-12
    tres = y.copy()
    tres[[0, 1, 2]] = np.nan
    assert abs(st.pendiente_mco(tres[None, :])[0] - (-0.1)) < 1e-12
    dos = tres.copy()
    dos[3] = np.nan
    assert np.isnan(st.pendiente_mco(dos[None, :])[0])
    cero = y.copy()                       # un mes sin petroleo no cuenta: quedan tres
    cero[[0, 1]] = 0.0
    cero[2] = np.nan
    assert abs(st.pendiente_mco(cero[None, :])[0] - (-0.1)) < 1e-12
    cero[3] = 0.0
    assert np.isnan(st.pendiente_mco(cero[None, :])[0])


def test_caliper_k_max_y_desempate_por_indice():
    cand = np.array([9, 4, 7, 2, 5, 3, 8])
    niv_c = np.array([0.0, 0.1, 0.1, 0.1, 0.2, 0.3, 0.6])     # el ultimo queda fuera del caliper (0,5)
    pen_c = np.zeros(7)
    m = st._emparejar(0.0, 0.0, cand, niv_c, pen_c, (1.0, 1.0))
    assert len(m) == st.K_MAX
    assert 8 not in m.tolist()
    assert m.tolist() == [9, 2, 4, 7, 5]                       # 9 (distancia 0), luego 2, 4, 7 empatados por indice, 5
    # distancia sobre las dos variables estandarizadas: con desvio 0,1 en la pendiente, 0,06 de pendiente son 0,6 desvios
    assert len(st._emparejar(0.0, 0.0, np.array([1]), np.array([0.0]), np.array([0.06]), (1.0, 0.1))) == 0
    assert len(st._emparejar(0.0, 0.0, np.array([1]), np.array([0.0]), np.array([0.04]), (1.0, 0.1))) == 1


def test_un_evento_sin_k_min_controles_queda_fuera():
    D = _sintetico(n_grupos=20, n_ctrl=40, sin_controles_en=(3, 11))
    coh = causal.cohortes(D)
    ev = np.flatnonzero(coh["tratado"])
    dis = st._construir(D, ev, coh["g"][ev], st.E_SERIE)
    assert dis["n_sin_controles"] >= 2
    assert dis["n_validos"] == len(ev)
    assert len(dis["pozos"]) + dis["n_sin_controles"] == dis["n_validos"]
    assert all(len(c) >= st.K_MIN for c in dis["ctrl"])
    assert all(len(c) <= st.K_MAX for c in dis["ctrl"])
    for i, ctrl in zip(dis["pozos"], dis["ctrl"]):
        d = st._distancias(D, int(i), ctrl)
        assert ((d >= st.KM_CONTROL_MIN) & (d <= st.KM_CONTROL_MAX)).all()


def test_recupera_el_efecto_plantado_y_los_placebos_no_rompen():
    D = _sintetico(efecto=0.20)
    res = st.calcular(D, reps=200)
    j1 = res["j1"]
    att = float(res["r"]["est"][j1])
    assert abs(att - (-20.0)) < 3.0, att
    assert float(res["r"]["ic_alto"][j1]) < 0
    assert int(res["r"]["n_tratados"][j1]) >= 25
    for nombre, p in res["placebos"].items():
        assert int(p["n_tratados"][0]) > 0, nombre
        assert not p["rompe"], (nombre, float(p["est"][0]))


def test_con_efecto_cero_el_ic_incluye_cero():
    D = _sintetico(efecto=0.0)
    res = st.calcular(D, reps=200)
    j1 = res["j1"]
    assert abs(float(res["r"]["est"][j1])) < 3.0
    assert float(res["r"]["ic_bajo"][j1]) <= 0 <= float(res["r"]["ic_alto"][j1])
    assert res["veredicto"] != st.V_APILADO_SOSTIENE


def test_filas_del_mart_y_pagina():
    D = _sintetico(n_grupos=30, n_ctrl=40, efecto=0.20)
    res = st.calcular(D, reps=100)
    filas = st.filas_mart(res)
    assert [f for f in filas if f[0] == "E"] == [filas[0]]
    assert filas[0][1] == "ATT(1)" and filas[0][2] == 1
    assert all(f[0] == "E_detalle" for f in filas[1:])
    resultados = {f[1] for f in filas}
    assert {"serie", "placebo_fecha_falsa", "placebo_distancia_falsa", "placebo_nunca_tratados", "balance_nivel_antes",
            "balance_nivel_despues", "balance_pendiente_antes", "balance_pendiente_despues", "eventos_sin_controles",
            "cota_grilla", "cota_quiebre", "n_bloques"} <= resultados
    assert sum(1 for f in filas if f[1] == "cota_grilla") == len(st.cota_rr.GRILLA_MBAR)
    assert all(len(f) == len(st.COLUMNAS) for f in filas)
    texto = st.pagina_apilado(filas)
    assert "regla fijada en el commit 857d434 antes de calcular" in texto
    assert "## Lo que no dice" in texto


def test_el_veredicto_sigue_la_regla():
    assert st.veredicto_apilado(10, 40, False, -20.0, st.V_RR_RESISTE, []) == st.V_SIN_MUESTRA
    assert st.veredicto_apilado(400, 40, True, -20.0, st.V_RR_RESISTE, []) == st.V_PLACEBO
    assert st.veredicto_apilado(400, 40, False, -20.0, st.V_RR_RESISTE, [-3.0, -1.0]) == st.V_APILADO_SOSTIENE
    assert st.veredicto_apilado(400, 40, False, -20.0, st.V_RR_RESISTE, [-3.0, 1.0]) == st.V_NO_FIRME


def test_e2_el_anillo_llega_a_los_candidatos_y_e_no_cambia():
    # donantes a 6 a 8 km: para E (2 a 5) no son candidatos; para E2 (2 a 10) si
    D = _sintetico(n_grupos=20, n_ctrl=40, radio=(6.0, 8.0))
    coh = causal.cohortes(D)
    ev = np.flatnonzero(coh["tratado"])
    e = st._construir(D, ev, coh["g"][ev], st.E_SERIE)
    e_explicito = st._construir(D, ev, coh["g"][ev], st.E_SERIE, st.KM_CONTROL_MAX)
    e2 = st._construir(D, ev, coh["g"][ev], st.E_SERIE, st.KM_CONTROL_MAX_E2)
    assert st.KM_CONTROL_MAX_E2 == 10.0 and st.KM_CONTROL_MAX == 5.0
    assert len(e["pozos"]) == 0 and e["n_sin_controles"] == e["n_validos"] > 0
    assert len(e2["pozos"]) > 0
    for i, cand in zip(e2["pozos"], e2["cand"]):
        d = st._distancias(D, int(i), cand)
        assert ((d >= st.KM_CONTROL_MIN) & (d <= st.KM_CONTROL_MAX_E2)).all() and (d > st.KM_CONTROL_MAX).any()
    # con el valor por defecto, las filas de E son las de siempre (mismo resultado que pasar el anillo de E)
    assert len(e_explicito["pozos"]) == len(e["pozos"]) and e_explicito["n_sin_controles"] == e["n_sin_controles"]
    D2 = _sintetico(n_grupos=30, n_ctrl=40, efecto=0.20)
    r_def, r_exp = st.calcular(D2, reps=50), st.calcular(D2, reps=50, km_max=st.KM_CONTROL_MAX)
    assert st.filas_mart(r_def) == st.filas_mart(r_exp)


def test_pagina_con_y_sin_filas_de_e2():
    D = _sintetico(n_grupos=30, n_ctrl=40, efecto=0.20)
    filas = st.filas_mart(st.calcular(D, reps=50))
    sin = st.pagina_apilado(filas)
    assert "## E2" not in sin
    r2 = st.calcular(D, reps=50, km_max=st.KM_CONTROL_MAX_E2)
    f2 = st.filas_mart(r2, "E2", st.KM_CONTROL_MAX_E2)
    assert f2[0][0] == "E2" and all(f[0] == "E2_detalle" for f in f2[1:]) and all(len(f) == len(st.COLUMNAS) for f in f2)
    con = st.pagina_apilado(filas + f2)
    assert con.startswith(sin.split("## Lo que no dice")[0][:200])
    assert "## E2: la misma pila con donantes a 2 a 10 km" in con and f"commit {st.REGLA_COMMIT_E2}" in con
    assert "El balance después de emparejar de E2" in con and "### Veredicto" in con
