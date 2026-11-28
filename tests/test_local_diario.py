"""Tests del lector local de produccion diaria (pipeline/local_diario.py). Todo el dato es sintetico y vive en tmp_path."""
from __future__ import annotations

import csv
from calendar import monthrange
from datetime import date, timedelta

import duckdb
import pytest

from pipeline import local, local_diario
from tests.test_local import sintetico

COLUMNAS = ["pozo_id", "fecha", "petroleo_m3", "agua_m3", "horas_produccion"]
ID_RARO = 424242


def _escribe(ruta, filas, columnas=COLUMNAS):
    with open(ruta, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    return ruta


def _con(ids):
    con = duckdb.connect(":memory:")
    con.execute("create table dim_pozo as select * from (values " + ",".join(f"({i})" for i in ids) + ") t(pozo_id)")
    return con


def _planta(tmp_path):
    """3 pozos x 3 meses (2024-01 a 2024-03, con febrero bisiesto) con dias en cero y volumenes conocidos.

    Pozo 1: todos los dias registrados; dias 3, 4 y 10 de enero en cero, ninguno en febrero, el 29 de marzo en cero.
    Pozo 2: todos los dias registrados; todo febrero en cero salvo el dia 29.
    Pozo 3: enero y febrero completos sin ceros; marzo solo los dias 1 a 20 (incompleto), el dia 5 en cero.
    El petroleo de un dia con produccion es dia * pozo (en m3), el de un dia en cero es 0. Devuelve (ruta, esperado), con el
    esperado calculado aparte de la lectura: {(pozo, mes): (petroleo, dias_registrados, dias_con_produccion, dias_mes, completo)}.
    """
    ceros = {(1, 1): {3, 4, 10}, (1, 3): {29}, (2, 2): set(range(1, 29)), (3, 3): {5}}
    ultimo = {(3, 3): 20}
    filas, esperado = [], {}
    for pozo in (1, 2, 3):
        for mes in (1, 2, 3):
            dias_mes = monthrange(2024, mes)[1]
            n = ultimo.get((pozo, mes), dias_mes)
            z = ceros.get((pozo, mes), set())
            total, con_prod = 0.0, 0
            for dia in range(1, n + 1):
                v = 0.0 if dia in z else float(dia * pozo)
                total += v
                con_prod += 0 if dia in z else 1
                filas.append([pozo, f"2024-{mes:02d}-{dia:02d}", repr(v), "", ""])
            esperado[(pozo, date(2024, mes, 1))] = (total, n, con_prod, dias_mes, n == dias_mes)
    return _escribe(tmp_path / "diario.csv", filas), esperado


def test_dias_planteados(tmp_path):
    ruta, esperado = _planta(tmp_path)
    con = _con([1, 2, 3])
    info = local_diario.leer(con, ruta)
    got = {(r[0], r[1]): r[2:] for r in con.execute(
        """select pozo_id, mes, petroleo_m3, dias_registrados, dias_con_produccion, dias_mes, completo
        from diario_mes""").fetchall()}
    assert set(got) == set(esperado)
    for k, v in esperado.items():
        assert got[k] == pytest.approx(v), k
    # los dos casos que un lector equivocado confunde: febrero bisiesto y el mes incompleto
    assert got[(1, date(2024, 2, 1))][3] == 29 and got[(1, date(2024, 2, 1))][4] is True
    assert got[(3, date(2024, 3, 1))][4] is False
    assert got[(1, date(2024, 1, 1))][2] == 28  # 31 dias menos 3 en cero, no 31 filas
    assert info["filas_leidas"] == info["filas_usadas"] == con.execute("select count(*) from fct_diario").fetchone()[0]
    assert info["filas_ignoradas"] == 0 and info["pozos"] == 3 and info["meses"] == 9
    assert (info["fecha_desde"], info["fecha_hasta"]) == ("2024-01-01", "2024-03-31")
    assert info["avisos"] == []
    # sin fct_produccion no hay comparacion
    assert info["meses_comparados"] is None and info["meses_difieren"] is None
    assert con.execute("select count(*) from information_schema.tables where table_name = 'diario_contra_mensual'"
                       ).fetchone()[0] == 0
    assert "raw_diario" not in {r[0] for r in con.execute("show tables").fetchall()}


def test_las_horas_cuentan(tmp_path):
    ruta = _escribe(tmp_path / "diario.csv", [
        [1, "2024-02-01", "0", "", "6"],      # petroleo 0 con horas: produjo
        [1, "2024-02-02", "0", "", "0"],      # ambos 0: no produjo
        [1, "2024-02-03", "0", "", ""],       # horas nulas y petroleo 0: no produjo
        [1, "2024-02-04", "2.5", "", "0"],    # petroleo sin horas registradas como 0: produjo por el petroleo
        [1, "2024-02-05", "", "", "24"],      # petroleo vacio (0, con aviso) y 24 horas: produjo
    ])
    con = _con([1])
    local_diario.leer(con, ruta)
    got = dict(con.execute("select cast(fecha as varchar), produjo from fct_diario").fetchall())
    assert got == {"2024-02-01": True, "2024-02-02": False, "2024-02-03": False, "2024-02-04": True,
                   "2024-02-05": True}
    assert con.execute("select dias_con_produccion, dias_registrados from diario_mes").fetchone() == (3, 5)


def test_avisos_y_conversiones(tmp_path):
    ruta = _escribe(tmp_path / "diario.csv", [
        [1, "2024-02-01", "5", "1.5", "3"],
        [1, "2024-02-02", "-4", "-1", ""],       # petroleo negativo -> 0, agua negativa -> nula
        [1, "2024-02-03", "", "abc", ""],        # petroleo vacio -> 0, agua ilegible -> nula
        [1, "2024-02-04", "xyz", "nan", ""],     # petroleo ilegible -> 0, agua no finita -> nula
        [1, "2024-02-05", "nan", "", ""],        # petroleo no finito -> 0 (nunca NaN en las sumas)
        [999, "2024-02-01", "7", "", ""],        # pozo ausente en dim_pozo: se ignora
        [999, "2024-02-02", "7", "", ""],
    ])
    con = _con([1])
    info = local_diario.leer(con, ruta)
    assert info["filas_leidas"] == 7 and info["filas_ignoradas"] == 2 and info["filas_usadas"] == 5
    fila = con.execute("select petroleo_m3, agua_m3 from diario_mes").fetchone()
    assert fila == (5.0, 1.5)  # sin NaN, el agua suma solo el dato valido
    texto = " ".join(info["avisos"])
    assert "2 filas del diario con pozo ausente" in texto
    assert "2 filas del diario traen petroleo_m3 vacío o negativo" in texto
    assert "2 filas del diario traen petroleo_m3 no interpretable" in texto
    assert "3 filas del diario traen agua_m3 negativa o no interpretable" in texto


def test_agua_toda_nula_queda_nula(tmp_path):
    ruta = _escribe(tmp_path / "diario.csv", [[1, "2024-02-01", "1", "", ""], [1, "2024-02-02", "1", "x", ""]])
    con = _con([1])
    local_diario.leer(con, ruta)
    assert con.execute("select agua_m3 from diario_mes").fetchone() == (None,)


def test_columnas_opcionales_ausentes(tmp_path):
    ruta = _escribe(tmp_path / "diario.csv", [[1, "2024-02-01", "3"], [1, "2024-02-02", "0"]],
                    ["pozo_id", "fecha", "petroleo_m3"])
    con = _con([1])
    info = local_diario.leer(con, ruta)
    assert info["con_agua"] is False and info["con_horas"] is False
    assert con.execute("select dias_con_produccion, agua_m3 from diario_mes").fetchone() == (1, None)


@pytest.mark.parametrize("filas, columnas, nombres, conteo", [
    ([[ID_RARO, "2024-02-01", "1", "", ""], [ID_RARO, "2024-02-01", "2", "", ""]], COLUMNAS,
     ("pozo_id", "fecha"), "1 pares repetidos"),
    ([[ID_RARO, "2024-02-01", "1", "", ""]], ["pozo_id", "dia", "petroleo_m3", "agua_m3", "horas_produccion"],
     ("fecha",), None),
    ([[ID_RARO, "2024-02-01", "1", "", "25"], [ID_RARO, "2024-02-02", "1", "", "24"]], COLUMNAS,
     ("horas_produccion",), "1 filas con horas_produccion"),
    ([[ID_RARO, "2024-02-01", "1", "", "-1"]], COLUMNAS, ("horas_produccion",), "1 filas con horas_produccion"),
    ([[ID_RARO, "2024-02-01", "1", "", "nan"]], COLUMNAS, ("horas_produccion",), "1 filas con horas_produccion"),
    ([[ID_RARO, "2024-02-01", "1", "", "abc"]], COLUMNAS, ("horas_produccion",), "1 filas con horas_produccion"),
    ([[ID_RARO, "2024-02-30", "1", "", ""], [ID_RARO, "2024-02-01", "1", "", ""]], COLUMNAS, ("fecha",),
     "1 filas con fecha no interpretable"),
    ([[ID_RARO, "", "1", "", ""]], COLUMNAS, ("fecha",), "1 filas con fecha no interpretable"),
    ([[ID_RARO, "2024-02-01", "1", "", ""], ["x7", "2024-02-02", "1", "", ""]], COLUMNAS, ("pozo_id",),
     "1 filas con pozo_id no interpretable"),
    ([], COLUMNAS, ("filas",), None),
    ([[1, "2024-02-01", "1", "", ""]], ["pozo_id", "fecha"], ("petroleo_m3",), None),
])
def test_errores(tmp_path, capsys, filas, columnas, nombres, conteo):
    ruta = _escribe(tmp_path / "diario.csv", filas, columnas)
    con = _con([ID_RARO])
    with pytest.raises(SystemExit) as e:
        local_diario.leer(con, ruta)
    assert e.value.code == 2
    err = capsys.readouterr().err
    for nombre in nombres:
        assert nombre in err
    if conteo:
        assert conteo in err
    assert str(ID_RARO) not in err, "valor de celda en el mensaje"
    assert "2024-02-0" not in err, "fecha de una celda en el mensaje"
    assert "x7" not in err
    assert "raw_diario" not in {r[0] for r in con.execute("show tables").fetchall()}


def test_error_archivo_inexistente_y_pozos_ajenos(tmp_path, capsys):
    con = _con([1])
    with pytest.raises(SystemExit) as e:
        local_diario.leer(con, tmp_path / "no_existe.csv")
    assert e.value.code == 2 and "no se pudo leer" in capsys.readouterr().err
    ruta = _escribe(tmp_path / "diario.csv", [[77, "2024-02-01", "1", "", ""]])
    with pytest.raises(SystemExit) as e:
        local_diario.leer(con, ruta)
    err = capsys.readouterr().err
    assert e.value.code == 2 and "ninguna fila corresponde a un pozo" in err and "77" not in err
    with pytest.raises(SystemExit) as e:
        local_diario.leer(duckdb.connect(":memory:"), ruta)
    assert e.value.code == 2 and "dim_pozo" in capsys.readouterr().err


def test_contra_el_mensual(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=2)
    con, _ = local.armar_base(pozos, mensual)
    ids = (1000, 1001)
    meses = con.execute("select pozo_id, cast(mes as date), petroleo_m3, dias_mes from fct_produccion where pozo_id in (1000, 1001) "
                        "order by pozo_id, mes").fetchall()
    assert len(meses) > 30
    de_1000 = [m for m in meses if m[0] == 1000]
    de_1001 = [m for m in meses if m[0] == 1001]
    desvios = {(1000, de_1000[2][1]), (1001, de_1001[-3][1])}  # justo 2 meses con 10% de diferencia
    assert len(desvios) == 2
    filas = []
    for pozo, mes, vol, dias_mes in meses:
        f = 1.10 if (pozo, mes) in desvios else 1.0
        for d in range(dias_mes):
            filas.append([pozo, (mes + timedelta(days=d)).isoformat(), repr(vol * f / dias_mes), "", ""])
    filas.append([999999, "2020-02-01", "5", "", ""])  # pozo que esta en el mensual pero no en dim_pozo
    diario = _escribe(tmp_path / "diario.csv", filas)
    info = local_diario.leer(con, diario)
    assert info["meses_comparados"] == len(meses) and info["meses_difieren"] == 2
    assert info["filas_ignoradas"] == 1
    difieren = {(r[0], r[1]) for r in con.execute(
        "select pozo_id, mes from diario_contra_mensual where difiere").fetchall()}
    assert difieren == desvios
    assert any("2 de " in a and "difieren del mensual" in a for a in info["avisos"])
    fila = con.execute("select petroleo_mensual_m3, petroleo_diario_m3 from diario_contra_mensual "
                       "where pozo_id = ? and mes = ?", [1000, meses[0][1]]).fetchone()
    assert fila[1] == pytest.approx(fila[0])
    # la base del modo local sigue intacta
    assert con.execute("select count(*) from dim_pozo").fetchone()[0] == 10
    assert ids[0] in {r[0] for r in con.execute("select pozo_id from dim_pozo").fetchall()}


def test_tolerancia_y_ceros(tmp_path):
    con = _con([1, 2, 3, 4, 5])
    con.execute("""create table fct_produccion as select * from (values
        (1, date '2024-02-01', 100.0), (2, date '2024-02-01', 100.0), (3, date '2024-02-01', 0.0),
        (4, date '2024-02-01', 0.0), (5, date '2024-02-01', 100.0)) t(pozo_id, mes, petroleo_m3)""")
    ruta = _escribe(tmp_path / "diario.csv", [
        [1, "2024-02-01", "101.9", "", ""],   # 1.9% de diferencia: dentro
        [2, "2024-02-01", "102.5", "", ""],   # 2.5%: fuera
        [3, "2024-02-01", "0", "", ""],       # los dos en cero: no difiere
        [4, "2024-02-01", "0.5", "", ""],     # mensual en cero y diario con petroleo: difiere
        [5, "2024-02-01", "97", "", ""],      # por debajo, 3%: difiere tambien
    ])
    info = local_diario.leer(con, ruta)
    got = dict(con.execute("select pozo_id, difiere from diario_contra_mensual").fetchall())
    assert got == {1: False, 2: True, 3: False, 4: True, 5: True}
    assert info["meses_comparados"] == 5 and info["meses_difieren"] == 3


def test_no_escribe_nada(tmp_path):
    ruta, _ = _planta(tmp_path)
    antes = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert antes == {ruta}
    con = _con([1, 2, 3])
    local_diario.leer(con, ruta)
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == {ruta}


def test_la_entrada_es_la_que_cablea_L1c():
    assert local_diario.ENTRADA == "diario.csv" and "diari" in local_diario.ENTRADA
    # L1c lo cableo: local.ENTRADAS lo trae y pipeline.claims lee ahi lo que el modo local lee
    assert local_diario.ENTRADA in local.ENTRADAS
