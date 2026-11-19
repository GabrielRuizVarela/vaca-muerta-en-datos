"""pipeline.carga sobre un warehouse sintetico: el operador A carga 0 a 2 meses despues del inicio, el B 20 meses despues."""
import duckdb
import pytest

from pipeline import carga, checks
from pipeline.build import build
from pipeline.ingest import ROOT
from tests.test_pipeline import FRAC_COLS, PROD_COLS, frac_row, prod_row, write_csv


def _mes(i: int) -> tuple[int, int]:
    """(anio, mes) del mes numero i contado desde 2019-01."""
    return 2019 + i // 12, i % 12 + 1


def _datos():
    """41 meses de inicio (2019-08 a 2022-12). Por mes: un hijo de YPF (A) con rezago 0, 1 o 2, y dos hijos de Vista (B) con
    rezago 20. Ademas: C inicia en 2019-03 y se carga en 2019-06 (carga inicial, fija P0); D se carga un mes antes de iniciar
    (rezago negativo); E inicia en 2024-12 y se carga en 2025-02 (fija U)."""
    prod, frac = [], []

    def nuevo(inicio, cargado, empresa):
        pozo = len(prod) + 1
        prod.append(prod_row(pozo, 2025, 2, 100, empresa, lon=str(-69 + pozo * 0.001)))
        frac.append(frac_row(pozo, pozo, inicio, empresa=empresa, carga=cargado))

    for i in range(7, 48):
        a, m = _mes(i)
        nuevo(f"{a}-{m:02d}-10", _mes(i + i % 3), "YPF S.A.")
        for _ in range(2):
            nuevo(f"{a}-{m:02d}-10", _mes(i + 20), "VISTA ENERGY ARGENTINA SAU")
    nuevo("2019-03-10", (2019, 6), "YPF S.A.")
    nuevo("2020-05-10", (2020, 4), "YPF S.A.")
    nuevo("2024-12-10", (2025, 2), "YPF S.A.")
    return prod, frac


@pytest.fixture
def ruta(tmp_path):
    prod, frac = _datos()
    ruta = tmp_path / "w.duckdb"
    con = duckdb.connect(str(ruta))
    build(con, {"produccion_no_convencional": write_csv(tmp_path / "p.csv", PROD_COLS, prod),
                "fractura_adjunto_iv": write_csv(tmp_path / "f.csv", FRAC_COLS, frac),
                "seed_operadores": ROOT / "seeds" / "operadores.csv"})
    con.close()
    return ruta


@pytest.fixture
def con(ruta):
    c = duckdb.connect(str(ruta))
    yield c
    c.close()


def test_int_frac_hijo_tiene_una_fila_por_hijo(con):
    n = con.execute("select count(*), count(distinct hijo), count(mes_carga) from int_frac_hijo").fetchall()[0]
    assert n[0] == n[1] == n[2] == con.execute("select count(distinct pozo_id) from stg_fractura").fetchall()[0][0]
    assert n[0] == 41 * 3 + 3


def test_limites_y_curva(con):
    p0, u = carga.limites(con)
    assert (p0.year, p0.month, u.year, u.month) == (2019, 6, 2025, 2)
    cur = dict(carga.curva(con))
    assert sorted(cur) == list(range(25))
    # 123 hijos maduros con rezago >= 0: A 13 con rezago 0, 14 con 1, 14 con 2; 82 de B con 20. D (negativo) y C no entran.
    assert cur[0] == pytest.approx(13 / 123)
    assert cur[1] == pytest.approx(27 / 123)
    assert cur[2] == cur[19] == pytest.approx(41 / 123)
    assert cur[20] == cur[24] == pytest.approx(1.0)


def test_completitud_y_meses_incompletos(con):
    cur = dict(carga.curva(con))
    meses = {m["mes_frac"].strftime("%Y-%m"): m for m in carga.meses_incompletos(con)}
    assert min(meses) == "2019-06" and max(meses) == "2025-02" and len(meses) == 69
    assert meses["2025-02"]["completitud_estimada"] == pytest.approx(cur[0])
    assert meses["2024-07"]["completitud_estimada"] == pytest.approx(cur[7])
    assert meses["2020-01"]["completitud_estimada"] == pytest.approx(1.0)
    assert meses["2019-08"]["hijos_cargados"] == 3
    assert carga.completitud_anio(con, 2020) == pytest.approx(1.0)
    assert carga.completitud_anio(con, 2025) == pytest.approx(cur[0])        # ultimo mes del ano con tope U
    assert carga.completitud_anio(con, 2018) is None and carga.completitud_anio(con, 2030) is None


def test_marts_pagina_y_banderas(ruta, tmp_path):
    pagina = tmp_path / "carga.md"
    carga.main(ruta, pagina)
    d = duckdb.connect(str(ruta), read_only=True)
    ops = {r[0]: r for r in d.execute("select * from mart_carga_operador").fetchall()}
    assert ops["Vista"][1:] == (82, 20, 0, 0)
    assert ops["YPF"][1:] == (41, 1, 100, 100)
    assert d.execute("select count(*) from mart_carga_curva").fetchall()[0][0] == 25
    c = d.execute("select hijos, rezago_mediana_meses, completitud_estimada, carga_inicial, censurado "
                  "from mart_carga_fracturas where mes_frac = date '2019-03-01'").fetchall()
    assert c == [(1, None, None, True, False)]
    n = d.execute("select censurado, count(*) from mart_carga_fracturas where not carga_inicial group by 1 order by 1").fetchall()
    assert [x[0] for x in n] == [False, True]
    assert d.execute("select censurado from mart_carga_fracturas where mes_frac = date '2024-12-01'").fetchall() == [(True,)]
    assert d.execute("select max(rezago_max_observable) from mart_carga_fracturas").fetchall()[0][0] == 71
    texto = pagina.read_text(encoding="utf-8")
    assert "Descriptivo, sin veredicto" in texto and "Hay 1 hijos con carga anterior al inicio" in texto
    assert chr(0x2013) not in texto and chr(0x2014) not in texto


def test_aviso_de_meses_incompletos(con):
    r = {c["nombre"]: c for c in checks.run(con)["checks"]}["Meses de inicio de fractura con carga estimada incompleta"]
    assert r["severidad"] == "aviso" and not r["ok"]
    assert r["filas"] == 20                                    # F(L) < 0,80 para L de 0 a 19: de 2023-07 a 2025-02


def test_mes_carga_con_trabajos_empatados_o_sin_dato(tmp_path):
    """Un trabajo cargado dos veces con la misma fecha de inicio toma el primer mes de carga. Si el trabajo que fija mes_frac no
    tiene mes de carga valido, el hijo queda sin mes de carga aunque un trabajo posterior lo tenga."""
    prod = [prod_row(p, 2025, 2, 100, "YPF S.A.", lon=str(-69 + p * 0.001)) for p in (1, 2)]
    frac = [frac_row(1, 1, "2021-09-10", empresa="YPF S.A.", carga=(2023, 1)),
            frac_row(2, 1, "2021-09-10", empresa="YPF S.A.", carga=(2021, 9)),
            frac_row(3, 2, "2021-09-10", empresa="YPF S.A.", carga=(2021, 13)),
            frac_row(4, 2, "2022-03-10", empresa="YPF S.A.", carga=(2022, 4))]
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    build(con, {"produccion_no_convencional": write_csv(tmp_path / "p.csv", PROD_COLS, prod),
                "fractura_adjunto_iv": write_csv(tmp_path / "f.csv", FRAC_COLS, frac),
                "seed_operadores": ROOT / "seeds" / "operadores.csv"})
    filas = con.execute("select hijo, strftime(mes_frac, '%Y-%m'), strftime(mes_carga, '%Y-%m') from int_frac_hijo order by 1").fetchall()
    con.close()
    assert filas == [(1, "2021-09", "2021-09"), (2, "2021-09", None)]


def test_mes_carga_con_anio_invalido_queda_nulo_y_no_frena_el_build(tmp_path):
    """Un anio de carga fuera de rango o ilegible deja el mes de carga nulo: no frena el build ni mueve el primer mes de carga.
    Entre dos filas con la misma fecha de inicio vale la carga conocida, aunque la otra no la traiga."""
    malos = [99999999, 0, -5, 1900, "abc", ""]
    prod = [prod_row(p, 2025, 2, 100, "YPF S.A.", lon=str(-69 + p * 0.001)) for p in range(1, len(malos) + 3)]
    frac = [frac_row(i + 1, i + 1, "2021-09-10", carga=(anio, 6)) for i, anio in enumerate(malos)]
    bueno, empatado = len(malos) + 1, len(malos) + 2
    frac += [frac_row(90, bueno, "2021-09-10", carga=(2021, 10)),
             frac_row(91, empatado, "2021-09-10", carga=("abc", 6)),
             frac_row(92, empatado, "2021-09-10", carga=(2021, 11))]
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    build(con, {"produccion_no_convencional": write_csv(tmp_path / "p.csv", PROD_COLS, prod),
                "fractura_adjunto_iv": write_csv(tmp_path / "f.csv", FRAC_COLS, frac),
                "seed_operadores": ROOT / "seeds" / "operadores.csv"})
    filas = con.execute("select hijo, strftime(mes_carga, '%Y-%m') from int_frac_hijo order by 1").fetchall()
    limites = carga.limites(con)
    con.close()
    assert filas == [(i + 1, None) for i in range(len(malos))] + [(bueno, "2021-10"), (empatado, "2021-11")]
    assert [f"{d.year}-{d.month:02d}" for d in limites] == ["2021-10", "2021-11"]
