"""Descomposicion de la brecha con eventos sinteticos: cierres contra golpe, alcance por distancia y pagina."""
import duckdb
import numpy as np
import pytest

from pipeline import descomposicion as dc
from pipeline import placebo
from pipeline.costo import _escribir
from test_placebo import N_MES, sintetico

REPS = 60
KS = (-1, 0, 1, 2)


def con_paneles(efecto_dias: float, efecto_tasa: float, seed: int = 5, cerrados: float = 0.0) -> dict:
    """sintetico() con las matrices de dias, caudal por dia efectivo y corte de agua.

    Los cercanos pierden `efecto_dias` de dias producidos y `efecto_tasa` de caudal por dia en los meses 0 a 2. El volumen es
    el producto: el caudal por dia calendario del sintetico se rehace con esos dos factores. Con `cerrados`, esa parte de los
    cercanos (uno de cada cinco, dos de cada cinco...) queda cerrada entera los meses 0 a 2: cero dias, sin caudal por dia
    (nan) y volumen cero; los demas no cambian.
    """
    D = sintetico(efecto=0.0, seed=seed)
    rng = np.random.default_rng(seed)
    tef = np.full_like(D["tasa"], np.nan)
    tasa_ef = np.full_like(D["tasa"], np.nan)
    t = np.arange(N_MES)
    n_cerca = 0
    for i in range(len(D["par_padre"])):
        h = D["par_hijo"][i]
        y = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, 0.03, N_MES))
        d = np.full(N_MES, 0.9)
        if D["par_km"][i] < 1:
            d[D["hijo_mes"][h]:D["hijo_mes"][h] + 3] *= 1 - efecto_dias
            y[D["hijo_mes"][h]:D["hijo_mes"][h] + 3] *= 1 - efecto_tasa
            n_cerca += 1
        te = y / 0.9
        if D["par_km"][i] < 1 and cerrados > 0 and (n_cerca % 5) < round(5 * cerrados):
            d[D["hijo_mes"][h]:D["hijo_mes"][h] + 3] = 0.0
            te[D["hijo_mes"][h]:D["hijo_mes"][h] + 3] = np.nan
        tef[i, placebo.PAD:placebo.PAD + N_MES] = d
        tasa_ef[i, placebo.PAD:placebo.PAD + N_MES] = te
        D["tasa"][i, placebo.PAD:placebo.PAD + N_MES] = d * np.nan_to_num(te)
    D["tef"], D["tasa_ef"] = tef, tasa_ef
    D["corte"] = np.full_like(D["tasa"], 0.2)
    return D


def por_panel(filas: list[tuple]) -> dict:
    return {(f[0], f[1]): f for f in filas}


def leer(D: dict, ks=(1,)) -> dict:
    """Lectura aditiva al mes 1 con las dos variantes."""
    a = por_panel(dc.tabla_aditiva(D, ks=ks, reps=REPS))
    return dc.lectura_aditiva(a[("con_cerrados", 1)], a[("sin_cerrados", 1)])


def test_cierres_bajan_los_dias_y_no_el_caudal_por_dia():
    f = por_panel(dc.tabla_paneles(con_paneles(0.25, 0.0), ks=KS, reps=REPS))
    vol, dias, tasa = f[("petroleo", 1)][6], f[("dias", 1)][6], f[("tasa_por_dia", 1)][6]
    assert vol < -0.2
    assert dias == pytest.approx(vol, abs=0.03)
    assert abs(tasa) < 0.03
    assert f[("dias", 1)][8] < 0 and f[("tasa_por_dia", 1)][7] <= 0 <= f[("tasa_por_dia", 1)][8]
    assert leer(con_paneles(0.25, 0.0))["lectura"] == "dias"
    assert abs(f[("corte_agua", 1)][6]) < 1e-9


def test_golpe_baja_el_caudal_por_dia_y_no_los_dias():
    f = por_panel(dc.tabla_paneles(con_paneles(0.0, 0.25), ks=KS, reps=REPS))
    vol, dias, tasa = f[("petroleo", 1)][6], f[("dias", 1)][6], f[("tasa_por_dia", 1)][6]
    assert vol < -0.2
    assert tasa == pytest.approx(vol, abs=0.03)
    assert abs(dias) < 0.03
    assert leer(con_paneles(0.0, 0.25))["lectura"] == "tasa"


def test_sin_efecto_la_lectura_es_sin_brecha():
    assert leer(con_paneles(0.0, 0.0))["lectura"] == "sin_brecha"


def test_mezcla_de_ambos_se_lee_mixta():
    r = leer(con_paneles(0.15, 0.15))
    assert r["lectura"] == "mixta"
    assert r["parte_dias"] + r["parte_tasa"] == pytest.approx(1.0)  # los logaritmos se suman: las partes suman 100%


def test_cerrados_el_40_por_ciento_se_lee_dias_o_mixta_nunca_tasa():
    """El 40% de los cercanos cerrados el mes entero y el resto intacto: las medianas no ven nada, la descomposicion si."""
    D = con_paneles(0.0, 0.0, cerrados=0.4)
    f = por_panel(dc.tabla_paneles(D, ks=(1,), reps=REPS))
    assert abs(f[("dias", 1)][6]) < 0.03  # la mediana de los dias sigue en 1: el artefacto que la descomposicion corrige
    r = leer(D)
    assert r["lectura"] in ("dias", "mixta") and r["lectura"] != "tasa"
    assert r["parte_dias"] >= 0.5 > r["parte_tasa"]
    c = dc.tabla_cierres(D)[0]
    assert c[5] == pytest.approx(0.4, abs=0.03) and c[6] == 0.0 and c[3] >= c[5] and c[4] == 0.0


def test_tabla_cierres_cuenta_los_cercanos_con_dias_bajos_y_cerrados():
    c = dc.tabla_cierres(con_paneles(0.25, 0.0))[0]
    assert c[3] == pytest.approx(1.0, abs=0.02) and c[4] == 0.0 and c[5] == 0.0 and c[6] == 0.0


def test_semilla_igual_a_la_del_placebo_para_el_mismo_k():
    D2 = con_paneles(0.1, 0.1)
    ks = (-1, 1)
    f = por_panel(dc.tabla_paneles(D2, ks=ks, reps=REPS))
    ref = {r[0]: r for r in placebo.tabla_pretendencia(D2, reps=REPS)}
    for k in ks:
        assert f[("petroleo", k)][7:9] == ref[k][6:8]


def sintetico_distancia(alcance: float = 0.6, efecto: float = 0.3, seed: int = 11, n_hijos: int = 70, por_banda: int = 8) -> dict:
    """Cada hijo tiene `por_banda` padres en cada banda de distancia (0 a 10 km); solo los de menos de `alcance` km pierden `efecto`."""
    rng = np.random.default_rng(seed)
    hijo_mes = rng.integers(100, 150, n_hijos).astype(np.int64)
    ph, pp, km = [], [], []
    for h in range(n_hijos):
        for lo, hi in dc.BANDAS:
            for _ in range(por_banda):
                ph.append(h)
                pp.append(len(pp))
                km.append(rng.uniform(lo, hi))
    n_par = len(pp)
    tasa = np.full((n_par, N_MES + 2 * placebo.PAD), np.nan)
    t = np.arange(N_MES)
    for i in range(n_par):
        y = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, 0.03, N_MES))
        if km[i] < alcance:
            y[hijo_mes[ph[i]]:hijo_mes[ph[i]] + 3] *= 1 - efecto
        tasa[i, placebo.PAD:placebo.PAD + N_MES] = y
    D = {"hijo_id": np.arange(n_hijos) + 1000, "hijo_mes": hijo_mes, "hijo_anio": 2000 + hijo_mes // 12,
         "hijo_pad": np.arange(n_hijos), "primer": np.zeros(n_par, dtype=np.int64), "area": np.array(["A"] * n_par),
         "lat": np.full(n_par, -38.5), "tasa": tasa, "par_hijo": np.array(ph), "par_padre": np.array(pp),
         "par_km": np.array(km), "par_rumbo": np.zeros(n_par), "n_mes": N_MES}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - placebo.EDAD_MIN
    return D


def test_distancia_el_efecto_solo_llega_a_0_6_km():
    filas = {f[0]: f for f in dc.tabla_distancia(sintetico_distancia(), reps=REPS, n_min_anillo=50)}
    for banda in ("0 a 0,3", "0,3 a 0,6"):
        assert filas[banda][8] < -0.2 and filas[banda][10] < 0
    for banda in ("1 a 2", "2 a 5"):
        assert abs(filas[banda][8]) < 0.03, filas[banda]
        assert filas[banda][9] <= 0 <= filas[banda][10]
    assert filas["0,6 a 1"][4] > 0 and filas["0 a 0,3"][3] == "5 a 10 km"
    ring = [f for f in dc.tabla_distancia(sintetico_distancia(), reps=REPS, n_min_anillo=50) if f[0] == "5 a 10"]
    assert len(ring) == 1 and ring[0][3] == "2 a 5 km" and abs(ring[0][8]) < 0.03


def test_distancia_el_anillo_ve_un_efecto_que_llega_hasta_5_km():
    """Con el efecto en todo lo que esta a menos de 5 km, el anillo rinde mas que 2 a 5 km y las bandas dan la brecha del efecto."""
    filas = dc.tabla_distancia(sintetico_distancia(alcance=5.0), reps=REPS, n_min_anillo=50)
    ring = next(f for f in filas if f[0] == "5 a 10")
    assert ring[3] == "2 a 5 km" and ring[8] > 0.2 and ring[9] > 0  # el IC excluye cero: el control de 2 a 5 km no es un cero limpio
    for f in filas:
        if f[0] in ("2 a 5", "1 a 2", "0,6 a 1"):
            assert f[8] < -0.2 and f[10] < 0, f
    sin = dc.tabla_distancia(sintetico_distancia(alcance=0.6), reps=REPS, n_min_anillo=50)
    assert next(f for f in sin if f[0] == "5 a 10")[9] <= 0  # sin efecto lejos, el anillo no se separa de 2 a 5 km


def test_la_fila_de_todos_los_cercanos_usa_las_dos_bases_y_el_mismo_anillo():
    filas = dc.tabla_distancia(sintetico_distancia(), reps=REPS, n_min_anillo=50)
    todos = [f for f in filas if f[0] == dc.ETQ_TODOS]
    assert sorted(f[11] for f in todos) == ["-3 a -1", "-6 a -4"]
    assert all(f[3] == "5 a 10 km" and f[8] < -0.2 for f in todos)
    assert len({f[5] for f in todos}) == 1  # mismo anillo con las dos bases (todas las bases son positivas en el sintetico)
    bandas = [f for f in filas if f[0] in ("0 a 0,3", "0,3 a 0,6", "0,6 a 1")]
    assert sum(f[4] for f in bandas) == todos[0][4]


def test_la_banda_de_2_a_5_usa_la_misma_regla_que_el_control_del_anillo():
    D = sintetico_distancia(n_hijos=10, por_banda=4)
    banda = int(D["par_padre"][np.flatnonzero((D["par_hijo"] == 0) & (D["par_km"] > 2) & (D["par_km"] < 5))[0]])
    N = dict(D)
    N["hijo_mes"] = D["hijo_mes"].copy()
    N["hijo_mes"][5] = D["hijo_mes"][0] + 1  # otro hijo fractura a 0,4 km de un padre de 2 a 5 km un mes despues
    for k, v in (("par_hijo", 5), ("par_padre", banda), ("par_km", 0.4), ("par_rumbo", 0.0)):
        N[k] = np.append(D[k], v)
    N["par_real_ok"] = np.append(D["par_real_ok"], True)
    base = {f[0]: f for f in dc.tabla_distancia(D, reps=REPS, n_min_anillo=10)}
    con = {f[0]: f for f in dc.tabla_distancia(N, reps=REPS, n_min_anillo=10)}
    assert con["2 a 5"][4] == base["2 a 5"][4] - 1  # el padre con otro hijo cerca sale de la banda
    assert con["5 a 10"][5] == base["5 a 10"][5] - 1  # y del control de la fila del anillo: las dos filas comparten la regla


def test_cargar_10km_trae_los_pares_hasta_10_km_con_una_tabla_en_memoria():
    con = duckdb.connect(":memory:")
    con.execute("create table int_frac_hijo (hijo integer)")
    con.execute("insert into int_frac_hijo values (1)")
    con.execute("create table int_pozo_ubicacion (pozo_id integer, lat double, lon double, primer_mes_petroleo date)")
    # hijo 1 en (-38.5, -69.0); 1 deg de latitud = 111,32 km
    for pid, dlat, dlon in ((1, 0, 0), (2, 0.03, 0), (3, 0.07, 0), (4, 0.088, 0), (5, 0.15, 0), (6, 0, 0.12), (7, 0.02, 0.01)):
        con.execute("insert into int_pozo_ubicacion values (?, ?, ?, date '2010-01-01')", [pid, -38.5 + dlat, -69.0 + dlon])
    D = {"hijo_id": np.array([1]), "hijo_mes": np.array([100]), "primer": np.zeros(7, dtype=np.int64), "n_mes": 150}
    out = dc.cargar_10km(con, D)
    km = dict(zip((int(i) + 1 for i in out["par_padre"]), out["par_km"]))
    assert set(km) == {2, 3, 4, 7}  # 5 (16,7 km), 6 (10,4 km) y el propio hijo quedan fuera
    assert km[2] == pytest.approx(3.34, abs=0.05) and km[3] == pytest.approx(7.79, abs=0.05) and km[4] == pytest.approx(9.80, abs=0.05)
    assert (out["par_hijo"] == 0).all() and out["par_real_ok"].all()
    assert placebo.SQL_PARES.count("< 5\n") == 1  # el reemplazo de texto depende de esta forma exacta del SQL
    con.close()


def test_anillo_fino_usa_2_a_5_km_de_control():
    filas = dc.tabla_distancia(sintetico_distancia(), reps=REPS, n_min_anillo=10**9)
    assert all(f[3] == "2 a 5 km" for f in filas)
    assert not any(f[0] == "2 a 5" for f in filas)


def test_los_controles_excluyen_padres_con_un_hijo_a_menos_de_1_km():
    D = sintetico_distancia(n_hijos=10, por_banda=4)
    m0 = dc._marco_distancia(D)
    assert m0["limpio"][m0["km"] >= 2].all()  # un solo hijo por padre: ningun control tiene otro hijo cerca
    ctrl = int(D["par_padre"][np.flatnonzero((D["par_hijo"] == 0) & (D["par_km"] > 5))[0]])
    N = dict(D)
    N["hijo_mes"] = D["hijo_mes"].copy()
    N["hijo_mes"][5] = D["hijo_mes"][0] + 1  # otro hijo fractura a 0,4 km del padre control un mes despues
    for k, v in (("par_hijo", 5), ("par_padre", ctrl), ("par_km", 0.4), ("par_rumbo", 0.0)):
        N[k] = np.append(D[k], v)
    N["par_real_ok"] = np.append(D["par_real_ok"], True)
    m = dc._marco_distancia(N)
    i = np.flatnonzero((m["padre"] == ctrl) & (m["mes"] == D["hijo_mes"][0]))
    assert len(i) == 1 and not m["limpio"][i[0]]


def test_dos_corridas_dan_las_mismas_filas():
    D = con_paneles(0.2, 0.1)
    assert dc.tabla_paneles(D, ks=KS, reps=REPS) == dc.tabla_paneles(D, ks=KS, reps=REPS)
    assert dc.tabla_aditiva(D, ks=KS, reps=REPS) == dc.tabla_aditiva(D, ks=KS, reps=REPS)
    S = sintetico_distancia(n_hijos=30)
    assert dc.tabla_distancia(S, reps=REPS, n_min_anillo=20) == dc.tabla_distancia(S, reps=REPS, n_min_anillo=20)


def escribir_marts(con, D: dict) -> None:
    _escribir(con, "mart_descomposicion_k", dc.COLS_K, dc.tabla_paneles(D, ks=dc.KS, reps=REPS))
    _escribir(con, "mart_descomposicion_aditiva", dc.COLS_ADIT, dc.tabla_aditiva(D, ks=dc.KS, reps=REPS))
    _escribir(con, "mart_descomposicion_cierres", dc.COLS_CIERRES, dc.tabla_cierres(D))
    _escribir(con, "mart_descomposicion_distancia", dc.COLS_DIST, dc.tabla_distancia(sintetico_distancia(), reps=REPS, n_min_anillo=50))


def test_pagina_sin_rayas_y_con_la_lectura():
    con = duckdb.connect(":memory:")
    escribir_marts(con, con_paneles(0.0, 0.25))
    pagina = dc.pagina_descomposicion(con)
    assert chr(0x2014) not in pagina and chr(0x2013) not in pagina
    assert "## Qué se concluye" in pagina and "## Límites" in pagina
    assert "se parece a un golpe de fractura" in pagina
    assert "Cierres o días perdidos: no" in pagina
    assert "las medianas no se suman; la parte de cada panel sale de la media de los logaritmos sobre los mismos eventos" in pagina.lower()
    assert "Contra el anillo de 5 a 10 km la brecha del mes 1 es" in pagina and "negativa que los" in pagina
    assert "frac hit" not in pagina and "contiene un efecto regional" not in pagina
    for p in dc.PANELES:
        assert dc.TITULOS[p] in pagina
    con.close()


def test_pagina_con_cierres_dice_cierres():
    con = duckdb.connect(":memory:")
    escribir_marts(con, con_paneles(0.25, 0.0))
    pagina = dc.pagina_descomposicion(con)
    assert "se parece a cierres o días perdidos" in pagina
    assert "Cierres o días perdidos: sí" in pagina
    con.close()
