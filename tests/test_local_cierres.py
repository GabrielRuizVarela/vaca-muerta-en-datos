"""Tests del lector de cierres del modo con datos propios (pipeline/local_cierres.py). Todo sintetico, en tmp_path."""
from __future__ import annotations

import csv
import re

import duckdb
import pytest

from pipeline import local, local_cierres
from tests.test_local import sintetico

COLS = ["pozo_id", "inicio", "fin", "motivo"]


def _csv(base, filas, cols=COLS, nombre="cierres.csv"):
    ruta = base / nombre
    with open(ruta, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(filas)
    return ruta


def _con(ids=(7731, 7732)):
    """Conexion minima con dim_pozo y ultimo_mes, sin armar el pipeline completo."""
    con = duckdb.connect(":memory:")
    con.execute("create table dim_pozo as select unnest(?::integer[]) as pozo_id", [list(ids)])
    con.execute("create table ultimo_mes as select date '2024-03-01' as mes")
    return con


def _mes(con, pozo, mes):
    return con.execute("select horas_cerrado, dias_cerrado_completo, n_cierres, cerrado_todo_el_mes from cierres_mes "
                       "where pozo_id = ? and mes = ?", [pozo, mes]).fetchone()


def test_corte_en_el_limite_de_mes(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-01-31 18:00", "2024-02-02 06:00", "Mantenimiento"]])
    info = local_cierres.leer(con, ruta)
    assert _mes(con, 7731, "2024-01-01") == (6.0, 0, 1, False)
    assert _mes(con, 7731, "2024-02-01") == (30.0, 1, 0, False)
    assert con.execute("select count(*) from cierres_mes").fetchone()[0] == 2
    assert con.execute("select horas, motivo, abierto from cierres").fetchone() == (36.0, "mantenimiento", False)
    assert info["filas"] == 1 and info["avisos"] == []


def test_superposicion_no_cuenta_dos_veces(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-02-05 10:00", "2024-02-05 14:00", ""],
                           [7731, "2024-02-05 12:00", "2024-02-05 18:00", ""],
                           [7732, "2024-02-05 12:00", "2024-02-05 18:00", ""]])
    info = local_cierres.leer(con, ruta)
    assert _mes(con, 7731, "2024-02-01")[0] == 8.0
    assert _mes(con, 7731, "2024-02-01")[2] == 2
    assert _mes(con, 7732, "2024-02-01")[0] == 6.0
    assert info["superpuestos"] == 2
    assert any("2 intervalos" in a and "superponen" in a for a in info["avisos"])
    assert con.execute("select count(*) from cierres").fetchone()[0] == 3
    assert con.execute("select distinct motivo from cierres").fetchall() == [("sin motivo",)]


def test_intervalos_que_se_tocan_no_son_aviso(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-02-05 10:00", "2024-02-05 14:00", "a"],
                           [7731, "2024-02-05 14:00", "2024-02-05 18:00", "b"]])
    info = local_cierres.leer(con, ruta)
    assert info["superpuestos"] == 0 and info["avisos"] == []
    assert _mes(con, 7731, "2024-02-01")[0] == 8.0


def test_mes_completo(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-02-01", "2024-03-01", "x"], [7732, "2024-02-01", "2024-02-28", "x"]])
    local_cierres.leer(con, ruta)
    assert _mes(con, 7731, "2024-02-01") == (696.0, 29, 1, True)
    assert con.execute("select count(*) from cierres_mes where pozo_id = 7731").fetchone()[0] == 1
    assert _mes(con, 7732, "2024-02-01") == (648.0, 27, 1, False)


def test_intervalo_largo_cruza_meses_y_dias_completos(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-01-30 12:00", "2024-03-02 00:00", ""]])
    local_cierres.leer(con, ruta)
    assert _mes(con, 7731, "2024-01-01") == (36.0, 1, 1, False)      # 30 ene 12:00 a 1 feb: 12 h del 30 y el 31 completo
    assert _mes(con, 7731, "2024-02-01") == (696.0, 29, 0, True)
    assert _mes(con, 7731, "2024-03-01") == (24.0, 1, 0, False)


def test_abierto_cierra_al_final_del_ultimo_mes(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=3)
    con, _ = local.armar_base(pozos, mensual)
    ultimo = con.execute("select mes from ultimo_mes").fetchone()[0]
    ruta = _csv(tmp_path, [[10000, "2021-12-30 12:00", "", "Presion"], [10001, "2021-12-01", "2021-12-02", ""]])
    info = local_cierres.leer(con, ruta)
    assert str(ultimo)[:10] == "2021-12-01"
    assert con.execute("select fin, horas, abierto from cierres where pozo_id = 10000").fetchone()[1:] == (36.0, True)
    assert str(con.execute("select fin from cierres where pozo_id = 10000").fetchone()[0]) == "2022-01-01 00:00:00"
    assert _mes(con, 10000, "2021-12-01") == (36.0, 1, 1, False)
    assert con.execute("select abierto from cierres where pozo_id = 10001").fetchone() == (False,)
    assert info["abiertos"] == 1 and info["cierre_abiertos"] == "ultimo_mes"
    assert any("1 intervalos" in a and "no traen fin" in a for a in info["avisos"])


def test_abierto_sin_ultimo_mes_cierra_en_el_mayor_instante_del_archivo(tmp_path):
    con = duckdb.connect(":memory:")
    ruta = _csv(tmp_path, [[1, "2024-02-01", "", ""], [2, "2024-02-10 06:00", "2024-02-11 06:00", ""]])
    info = local_cierres.leer(con, ruta)
    assert info["cierre_abiertos"] == "archivo"
    assert con.execute("select horas from cierres where pozo_id = 1").fetchone() == (240.0 + 6.0,)


def test_abierto_posterior_al_cierre_queda_en_cero(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-05-01", "", ""]])
    info = local_cierres.leer(con, ruta)
    assert con.execute("select horas from cierres").fetchone() == (0.0,)
    assert con.execute("select count(*) from cierres_mes").fetchone()[0] == 0
    assert any("0 horas" in a for a in info["avisos"])


def test_pozos_ausentes_se_ignoran_y_se_cuentan(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-02-05", "2024-02-06", ""], [999999, "2024-02-05", "2024-02-06", ""]])
    info = local_cierres.leer(con, ruta)
    assert info["ignoradas"] == 1 and info["filas"] == 1 and info["pozos"] == 1
    assert con.execute("select count(*) from cierres where pozo_id = 999999").fetchone()[0] == 0
    assert any("1 filas" in a and "ausente" in a for a in info["avisos"])
    with pytest.raises(SystemExit) as e:
        local_cierres.leer(_con(), _csv(tmp_path, [[999999, "2024-02-05", "2024-02-06", ""]], nombre="otro.csv"))
    assert e.value.code == 2


@pytest.mark.parametrize("cols,fila,columna", [
    (COLS, [7731, "2024-02-05 10:00", "2024-02-05 08:00", ""], "fin"),
    (["pozo_id", "fin", "motivo"], [7731, "2024-02-05 12:00", ""], "inicio"),
    (["pozo_id", "inicio", "motivo"], [7731, "2024-02-05 10:00", ""], "fin"),
    (COLS, [7731, "", "2024-02-05 12:00", ""], "inicio"),
    (COLS, [7731, "2024-02-05 10:00", "ayer", ""], "fin"),
    (COLS, ["abc", "2024-02-05 10:00", "2024-02-05 12:00", ""], "pozo_id"),
])
def test_errores_con_codigo_2_sin_valores(tmp_path, capsys, cols, fila, columna):
    with pytest.raises(SystemExit) as e:
        local_cierres.leer(_con(), _csv(tmp_path, [fila], cols))
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert columna in err
    for valor in ("7731", "2024-02-05", "abc", "ayer"):
        assert valor not in err


def test_archivo_sin_filas_o_ilegible(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        local_cierres.leer(_con(), _csv(tmp_path, []))
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        local_cierres.leer(_con(), tmp_path / "no_existe.csv")
    assert e.value.code == 2
    assert not re.search(r"no_existe", capsys.readouterr().err)


def test_no_escribe_nada(tmp_path):
    con = _con()
    ruta = _csv(tmp_path, [[7731, "2024-02-05 10:00", "2024-02-05 14:00", "x"], [7731, "2024-02-06", "", "y"]])
    antes = {p for p in tmp_path.rglob("*")}
    local_cierres.leer(con, ruta)
    assert {p for p in tmp_path.rglob("*")} == antes == {ruta}
    tablas = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    assert tablas == {"dim_pozo", "ultimo_mes", "cierres", "cierres_mes"}
