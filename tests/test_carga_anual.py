"""pipeline.carga_anual: veredicto, restriccion a hijos visibles, corrimiento de composicion y punta a punta."""
import duckdb
import numpy as np
import pytest

from pipeline import carga_anual, placebo
from pipeline.build import build
from pipeline.ingest import ROOT
from tests.test_pipeline import FRAC_COLS, PROD_COLS, frac_row, prod_row, write_csv


def test_veredicto_sin_muestra_por_eventos():
    assert carga_anual.veredicto(-0.1, -0.2, -0.05, 99, 30, -0.1, 60) == "sin muestra"


def test_veredicto_sin_muestra_por_bloques():
    assert carga_anual.veredicto(-0.1, -0.2, -0.05, 100, 29, -0.1, 60) == "sin muestra"


def test_veredicto_sostiene():
    assert carga_anual.veredicto(-0.1, -0.2, -0.05, 100, 30, -0.01, 50) == "sostiene"


def test_veredicto_no_firme_por_guarda_signo():
    assert carga_anual.veredicto(-0.1, -0.2, -0.05, 100, 30, 0.0, 60) == "no firme"


def test_veredicto_no_firme_por_guarda_conteo():
    assert carga_anual.veredicto(-0.1, -0.2, -0.05, 100, 30, -0.1, 49) == "no firme"


def test_veredicto_no_se_sostiene():
    assert carga_anual.veredicto(0.05, 0.0, 0.1, 100, 30, -0.1, 60) == "no se sostiene"


def test_veredicto_no_firme_por_cero_incluido():
    assert carga_anual.veredicto(-0.05, -0.1, 0.05, 100, 30, -0.1, 60) == "no firme"


def test_veredicto_no_firme_con_intervalo_nan():
    nan = float("nan")
    assert carga_anual.veredicto(nan, nan, nan, 100, 30, -0.1, 60) == "no firme"


def _pares():
    """Un padre viejo con tasa alta y dos hijos del mismo mes: uno cercano (0,5 km) y otro a 3 km."""
    M = 300
    ancho = M + 2 + 2 * placebo.PAD
    D = {
        "hijo_id": np.array([11, 22]),
        "hijo_mes": np.array([M, M]),
        "hijo_anio": np.array([2026, 2026]),
        "hijo_pad": np.array([0, 1]),
        "primer": np.array([M - 60]),
        "area": np.array([""]),
        "lat": np.array([-38.0]),
        "tasa": np.full((1, ancho), 5.0),
        "par_hijo": np.array([0, 1]),
        "par_padre": np.array([0, 0]),
        "par_km": np.array([0.5, 3.0]),
        "par_rumbo": np.array([0.0, 90.0]),
        "n_mes": ancho - 2 * placebo.PAD,
    }
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= D["hijo_mes"][D["par_hijo"]] - placebo.EDAD_MIN
    return D


def test_restringir_saca_al_hijo_cercano_no_visible():
    D = _pares()
    m_comp = placebo.marco(D, D["hijo_mes"], ks=(1,), base=placebo.BASE_ORIGINAL)
    assert m_comp["hijo"].tolist() == [0] and m_comp["banda"].tolist() == [0]
    assert not np.isnan(m_comp["idx"][1]).any()
    R = carga_anual.restringir(D, np.array([False, True]))
    assert R["hijo_id"] is D["hijo_id"] and len(R["hijo_id"]) == 2
    assert R["par_hijo"].tolist() == [1] and R["par_km"].tolist() == [3.0]
    m_const = placebo.marco(R, R["hijo_mes"], ks=(1,), base=placebo.BASE_ORIGINAL)
    assert m_const["hijo"].tolist() == [1] and m_const["banda"].tolist() == [2]


def _sinteticos(semilla=11, sd=0.1, n_bloques=40):
    """Dos clases de operador: la rapida (YPF) con brecha -0,40 todos los anos y la lenta con -0,10.

    La base 2021 a 2024 trae las dos clases; en 2026 solo se cargo la rapida. Devuelve (completa, constante)."""
    rng = np.random.default_rng(semilla)
    filas = []
    h = 0

    def agrega(anio, n_cerca, n_ctrl, media_cerca, rapida):
        nonlocal h
        for banda, n, media in ((0, n_cerca, media_cerca), (2, n_ctrl, 1.0)):
            for _ in range(n):
                filas.append((anio, banda, float(rng.normal(media, sd)), int(rng.integers(0, n_bloques)), h,
                              rapida))
                h += 1

    for anio in (2021, 2022, 2023, 2024):
        agrega(anio, 30, 30, 0.6, True)
        agrega(anio, 30, 30, 0.9, False)
    agrega(2026, 120, 120, 0.6, True)
    completa = {"idx": np.array([f[2] for f in filas]), "banda": np.array([f[1] for f in filas]),
                "anio": np.array([f[0] for f in filas]), "bloque": np.array([f[3] for f in filas]),
                "hijo": np.array([f[4] for f in filas]), "ypf": np.array([f[5] for f in filas])}
    constante = {k: v[completa["ypf"]] for k, v in completa.items()}
    return completa, constante


def test_corrimiento_de_composicion():
    completa, constante = _sinteticos()
    r_comp = carga_anual.diferencia_ic(completa, (2026,), reps=200, semilla=7)
    assert r_comp["d"] < -0.08
    assert r_comp["ic_alto"] < 0
    assert r_comp["n_cercanos"] >= 100 and r_comp["n_bloques"] >= 30
    r_const = carga_anual.diferencia_ic(constante, (2026,), reps=200, semilla=7)
    assert r_const["ic_bajo"] < 0 <= r_const["ic_alto"]
    assert r_const["n_cercanos"] >= 100 and r_const["n_bloques"] >= 30
    d_ypf = carga_anual.diferencia(constante, (2026,), sel=constante["ypf"])
    n_ypf = int(((constante["anio"] == 2026) & (constante["banda"] == 0) & constante["ypf"]).sum())
    ver = carga_anual.veredicto(r_const["d"], r_const["ic_bajo"], r_const["ic_alto"], r_const["n_cercanos"],
                                r_const["n_bloques"], d_ypf, n_ypf)
    assert ver != "sostiene"


def test_deterministico():
    completa, _ = _sinteticos()
    a = carga_anual.diferencia_ic(completa, (2026,), reps=50, semilla=9)
    b = carga_anual.diferencia_ic(completa, (2026,), reps=50, semilla=9)
    assert a == b


def _meses(a0, m0, n):
    """n meses (anio, mes) desde (a0, m0)."""
    out = []
    a, m = a0, m0
    for _ in range(n):
        out.append((a, m))
        m += 1
        if m == 13:
            a += 1
            m = 1
    return out


@pytest.fixture
def ruta(tmp_path):
    """Warehouse minimo: 2 padres viejos con historia larga y 4 hijos con carga (uno tardio fija U)."""
    prod, frac = [], []
    pozo = [0]

    def nuevo_prod(lon, meses, pet=150):
        pozo[0] += 1
        for a, m in meses:
            prod.append(prod_row(pozo[0], a, m, pet, "YPF S.A.", lon=lon, lat="-38.00"))
        return pozo[0]

    nuevo_prod("-69.00", _meses(2020, 1, 30))
    nuevo_prod("-69.03", _meses(2020, 1, 30))
    for lon, inicio, cm in (("-69.005", "2021-06-10", (2021, 7)), ("-69.01", "2021-09-10", (2021, 10)),
                            ("-69.035", "2021-06-10", (2021, 8))):
        h = nuevo_prod(lon, _meses(2021, 6, 12), pet=200)
        frac.append(frac_row(h, h, inicio, carga=cm))
    h = nuevo_prod("-69.05", _meses(2022, 1, 6), pet=200)
    frac.append(frac_row(h, h, "2022-01-10", carga=(2022, 3)))
    ruta = tmp_path / "w.duckdb"
    con = duckdb.connect(str(ruta))
    build(con, {"produccion_no_convencional": write_csv(tmp_path / "p.csv", PROD_COLS, prod),
                "fractura_adjunto_iv": write_csv(tmp_path / "f.csv", FRAC_COLS, frac),
                "seed_operadores": ROOT / "seeds" / "operadores.csv"})
    con.close()
    return ruta


def test_punta_a_punta(ruta, tmp_path):
    pagina = tmp_path / "carga_anual.md"
    carga_anual.main(ruta, pagina)
    d = duckdb.connect(str(ruta), read_only=True)
    assert d.execute("select count(*) from mart_carga_anual").fetchall()[0][0] == 16
    assert [r[1] for r in d.execute("pragma table_info(mart_carga_anual)").fetchall()] == [
        "muestra", "anio", "hijos", "eventos_cercanos", "eventos_control", "bloques_5km", "brecha", "ic_bajo",
        "ic_alto"]
    assert d.execute("select distinct muestra from mart_carga_anual order by 1").fetchall() == [
        ("completa",), ("constante",)]
    assert d.execute("select count(*) from mart_carga_anual_prueba").fetchall()[0][0] == 2
    assert [r[1] for r in d.execute("pragma table_info(mart_carga_anual_prueba)").fetchall()] == [
        "estadistico", "d", "ic_bajo", "ic_alto", "n_cercanos", "n_bloques", "d_ypf", "n_ypf", "veredicto",
        "reps_validas"]
    fila = d.execute("select veredicto from mart_carga_anual_prueba where estadistico = '2026'").fetchall()[0]
    assert fila == ("sin muestra",)
    nula = d.execute("select d_ypf, n_ypf, veredicto from mart_carga_anual_prueba "
                     "where estadistico = '2025_2026'").fetchall()[0]
    assert nula == (None, None, None)
    texto = pagina.read_text(encoding="utf-8")
    assert "# La subida de 2026 con la misma antigüedad de carga" in texto
    assert "sin muestra" in texto
    assert chr(0x2013) not in texto and chr(0x2014) not in texto
    assert carga_anual.SI_NO in texto and carga_anual.SI_SOSTIENE not in texto


def test_la_pagina_dice_que_cambia_con_cada_veredicto_y_no_imprime_ruido_numerico():
    r = {"d": -0.2, "ic_bajo": -0.3, "ic_alto": -0.1, "n_cercanos": 150, "n_bloques": 40, "reps_validas": 398}
    fila = [(2026, 80, 150, 900, 30, -0.3, -0.5, -0.1)]
    sostiene = carga_anual.pagina("sostiene", r, -0.2, 120, r, fila, fila, True)
    no_firme = carga_anual.pagina("no firme", r, -0.2, 40, r, fila, fila, True)
    assert carga_anual.SI_SOSTIENE in sostiene and carga_anual.SI_NO not in sostiene
    assert carga_anual.SI_NO in no_firme and carga_anual.SI_SOSTIENE not in no_firme
    assert "anio_2026_carga" in sostiene and "anio_2026_carga" in no_firme
    assert "e+00" not in no_firme and "e-1" not in no_firme   # la diferencia de punto flotante no va al texto
    assert "Remuestras del bootstrap con D definido: 398 de 400." in no_firme
    assert "398 de 400 remuestras con D definido" in no_firme


def test_el_ic_cuenta_las_remuestras_sin_d_y_no_las_usa():
    """Un bloque solo trae todo 2026: la remuestra que no lo sortea no tiene D, se descarta y se cuenta."""
    n = 40
    base = {"idx": np.r_[np.full(n, 0.7), np.full(n, 1.0)], "banda": np.r_[np.zeros(n, int), np.full(n, 2)],
            "anio": np.full(2 * n, 2022), "bloque": np.r_[np.arange(n) % 4, np.arange(n) % 4]}
    prueba = {"idx": np.r_[np.full(n, 0.5), np.full(n, 1.0)], "banda": np.r_[np.zeros(n, int), np.full(n, 2)],
              "anio": np.full(2 * n, 2026), "bloque": np.full(2 * n, 9)}
    ev = {k: np.r_[base[k], prueba[k]] for k in base}
    r = carga_anual.diferencia_ic(ev, (2026,), reps=300, semilla=3)
    assert r["d"] == pytest.approx(-0.2)
    assert 0 < r["reps_validas"] < 300          # (4/5)^5 de las remuestras no sortea el bloque de 2026
    assert r["ic_bajo"] == pytest.approx(-0.2) and r["ic_alto"] == pytest.approx(-0.2)
    completa, _ = _sinteticos()
    assert carga_anual.diferencia_ic(completa, (2026,), reps=50, semilla=9)["reps_validas"] == 50
    vacio = {k: v[:0] for k, v in ev.items()}
    assert carga_anual.diferencia_ic(vacio, (2026,), reps=50, semilla=9)["reps_validas"] == 0
