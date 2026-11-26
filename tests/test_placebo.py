"""Pruebas de falsacion con eventos sinteticos: un efecto verdadero solo despues de la fractura del hijo."""
import duckdb
import numpy as np
import pytest

from pipeline import costo, placebo
from pipeline.ingest import DATA

WAREHOUSE = DATA / "warehouse.duckdb"
N_HIJOS = 70
N_MES = 220
REPS = 60


def sintetico(efecto: float = 0.25, previo: float = 0.0, seed: int = 3, eje: float = 70.0, amp_eje: float = 0.0) -> dict:
    """Cada hijo tiene 12 padres cercanos (0,3 a 0,9 km) y 30 controles (2 a 4,5 km). El caudal baja 1% por mes.

    Los cercanos pierden `efecto` en los meses 0 a 2 desde la fractura (mas `amp_eje` * cos(2 (rumbo - eje))) y `previo`
    en los meses -3 a -1. Cada padre tiene un solo hijo, asi que una fecha falsa nunca cae sobre un golpe de otro hijo.
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
    t = np.arange(N_MES)
    for i in range(n_par):
        h, cerca = ph[i], km[i] < 1
        y = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, 0.03, N_MES))
        if cerca:
            f = 1 - efecto - amp_eje * np.cos(2 * np.radians(rumbo[i] - eje))
            y[hijo_mes[h]:hijo_mes[h] + 3] *= f
            y[hijo_mes[h] - 3:hijo_mes[h]] *= 1 - previo
        tasa[i, placebo.PAD:placebo.PAD + N_MES] = y
    area = np.array(["A", "B", "C"])[np.arange(n_par) % 3]
    D = {"hijo_id": np.arange(N_HIJOS) + 1000, "hijo_mes": hijo_mes, "hijo_anio": 2000 + hijo_mes // 12,
         "hijo_pad": np.arange(N_HIJOS), "primer": np.zeros(n_par, dtype=np.int64), "area": area,
         "lat": np.full(n_par, -38.5), "tasa": tasa, "par_hijo": np.array(ph), "par_padre": np.array(pp),
         "par_km": np.array(km), "par_rumbo": np.array(rumbo), "n_mes": N_MES}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - placebo.EDAD_MIN
    return D


def test_efecto_solo_posterior_no_deja_pretendencia_y_si_brecha_al_mes_1():
    pre = {f[0]: f for f in placebo.tabla_pretendencia(sintetico(), reps=REPS)}
    for k in (-3, -2, -1):
        assert abs(pre[k][5]) < 0.03, pre[k]
        assert pre[k][6] <= 0 <= pre[k][7]
    assert pre[1][5] < -0.18 and pre[1][7] < -0.1
    assert pre[0][3] < pre[0][4] and pre[1][1] > 600 and pre[1][2] > 1500


def test_pretendencia_inyectada_queda_marcada():
    pre = {f[0]: f for f in placebo.tabla_pretendencia(sintetico(previo=0.12), reps=REPS)}
    for k in (-3, -2, -1):
        assert pre[k][5] == pytest.approx(-0.12, abs=0.03)
        assert pre[k][7] < 0  # el IC excluye cero
    assert pre[-1][5] > pre[1][5]


def test_fechas_falsas_dan_cerca_de_cero_y_la_real_no():
    D = sintetico()
    filas = {f[0]: f for f in placebo.tabla_fechas(D, desplazamientos=(-12, -6, 6, 12), reps=REPS)}
    assert filas[0][2] < -0.18
    for d in (-12, -6, 6, 12):
        n, g, lo, hi, real = filas[d][1:]
        assert n > 400
        assert abs(g) < 0.04 and lo <= 0 <= hi
        assert real < -0.18  # la brecha real en los mismos eventos sigue ahi


def test_desplazamiento_descarta_eventos_sin_datos():
    D = sintetico()
    D["hijo_mes"] = D["hijo_mes"].copy()
    D["hijo_mes"][:10] = N_MES - 2  # sin meses despues de la fractura en esos hijos
    m = placebo.marco(D, D["hijo_mes"] + 12, solo_reales=True)
    assert not np.isin(m["hijo"], np.arange(10)).any()   # sin base en la fecha falsa: el evento se descarta
    assert np.isin(m["hijo"], np.arange(10, N_HIJOS)).all()
    assert (m["banda"] == 0).sum() == 60 * 12


def test_permutar_fechas_conserva_el_conjunto_de_cada_ano():
    D = sintetico()
    p = placebo.permutar_fechas(D, np.random.default_rng(1))
    assert not np.array_equal(p, D["hijo_mes"])
    for a in np.unique(D["hijo_anio"]):
        m = D["hijo_anio"] == a
        assert sorted(p[m]) == sorted(D["hijo_mes"][m])


def test_permutacion_deja_la_brecha_real_fuera_y_eje_con_amplitud_real_mayor():
    D = sintetico(efecto=0.2, amp_eje=0.12)
    perm, eje = placebo.tabla_permutacion(D, n_perm=20, n_eje_completo=2, reps=REPS, reps_perm=49)
    assert perm[8] < perm[6]            # la brecha real queda por debajo del minimo permutado
    assert perm[9] == pytest.approx(1 / 21)
    assert abs(perm[2]) < 0.05
    real, resumen = eje[0], eje[-1]
    assert real[0] == "real" and real[1] == resumen[1]
    assert abs(float(costo._dif_axial(real[2], 70.0))) < 20
    assert real[6] > resumen[7]         # amplitud real mayor que el percentil 95 permutado
    assert [f[0] for f in eje[1:-1]] == ["permutacion 1", "permutacion 2"]


def test_dos_corridas_dan_las_mismas_tablas():
    D = sintetico()
    assert placebo.tabla_pretendencia(D, reps=REPS) == placebo.tabla_pretendencia(D, reps=REPS)
    assert placebo.tabla_fechas(D, desplazamientos=(6,), reps=REPS) == placebo.tabla_fechas(D, desplazamientos=(6,), reps=REPS)
    a = placebo.tabla_permutacion(D, n_perm=5, n_eje_completo=1, reps=REPS, reps_perm=19)
    assert a == placebo.tabla_permutacion(D, n_perm=5, n_eje_completo=1, reps=REPS, reps_perm=19)


def test_pagina_sin_rayas_y_con_las_secciones():
    D = sintetico(previo=0.05, amp_eje=0.1)
    con = duckdb.connect(":memory:")
    escribir = costo._escribir
    escribir(con, "mart_placebo_pretrend", placebo.COLS_PRE, placebo.tabla_pretendencia(D, placebo.BASE_LIMPIA, reps=REPS))
    escribir(con, "mart_placebo_pretrend_base_original", placebo.COLS_PRE,
             placebo.tabla_pretendencia(D, placebo.BASE_ORIGINAL, reps=REPS))
    escribir(con, "mart_placebo_pretrend_sin_previos", placebo.COLS_PRE,
             placebo.tabla_pretendencia(D, placebo.BASE_LIMPIA, reps=REPS, sin_previos=True))
    escribir(con, "mart_placebo_fechas", placebo.COLS_FECHAS, placebo.tabla_fechas(D, reps=REPS))
    perm, eje = placebo.tabla_permutacion(D, n_perm=10, n_eje_completo=2, reps=REPS, reps_perm=19)
    escribir(con, "mart_placebo_permutacion", placebo.COLS_PERM, [perm])
    escribir(con, "mart_placebo_eje", placebo.COLS_EJE, eje)
    texto = placebo.pagina_placebo(con)
    for raya in (chr(0x2014), chr(0x2013)):
        assert raya not in texto
    for seccion in ("## Pretendencia", "## Fechas de fractura falsas", "## Fechas permutadas", "## Qué se concluye", "## Qué no prueba"):
        assert seccion in texto
    cols = [c[0] for c in con.execute("describe mart_placebo_fechas").fetchall()]
    assert cols == ["desplazamiento_meses", "n", "brecha_mes1", "ic_bajo", "ic_alto", "brecha_real"]
    cols = [c[0] for c in con.execute("describe mart_placebo_pretrend").fetchall()]
    assert cols == ["k", "n_near", "n_ctrl", "indice_cercano", "indice_control", "brecha", "ic_bajo", "ic_alto"]


@pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
def test_motor_reproduce_los_eventos_del_warehouse():
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        D = placebo.cargar(con)
        m = placebo.marco(D, D["hijo_mes"])
        esperado = dict(con.execute("select banda, count(*) from int_interferencia_evento group by 1").fetchall())
        esperado_med = con.execute("select median(indice) from int_interferencia_mes where k = 1 and banda = 'cercano'").fetchone()[0]
    finally:
        con.close()
    assert (m["banda"] == 0).sum() == esperado["cercano"]
    assert (m["banda"] == 1).sum() == esperado["intermedio"]
    assert (m["banda"] == 2).sum() == esperado["control"]
    assert placebo.brecha(m["idx"][1], m["banda"])[0] == pytest.approx(esperado_med)


def test_sin_previos_descarta_el_evento_con_otro_golpe_cercano_en_los_meses_anteriores():
    D = sintetico()
    padre = int(D["par_padre"][0])  # cercano al hijo 0
    m0 = int(D["hijo_mes"][0])
    h = len(D["hijo_id"])
    for m_nuevo in (m0 + 3, m0 + 12):  # un hijo vecino 3 meses despues (dentro de la ventana) y otro 12 meses despues (fuera)
        E = dict(D)
        E["hijo_id"] = np.r_[D["hijo_id"], 99999]
        E["hijo_mes"] = np.r_[D["hijo_mes"], m_nuevo]
        E["hijo_anio"] = np.r_[D["hijo_anio"], 2000 + m_nuevo // 12]
        E["hijo_pad"] = np.r_[D["hijo_pad"], 9999]
        E["par_hijo"] = np.r_[D["par_hijo"], h]
        E["par_padre"] = np.r_[D["par_padre"], padre]
        E["par_km"] = np.r_[D["par_km"], 0.5]
        E["par_rumbo"] = np.r_[D["par_rumbo"], 10.0]
        E["par_real_ok"] = np.r_[D["par_real_ok"], True]
        con = placebo.marco(E, E["hijo_mes"], sin_previos=False)
        sin = placebo.marco(E, E["hijo_mes"], sin_previos=True)
        esta = lambda M: bool(((M["padre"] == padre) & (M["mes"] == m_nuevo)).any())
        assert esta(con)
        assert esta(sin) == (m_nuevo - m0 > placebo.VENTANA_PREVIOS)
        assert len(sin["padre"]) <= len(con["padre"])
