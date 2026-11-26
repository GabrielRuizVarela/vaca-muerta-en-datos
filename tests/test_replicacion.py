"""Replicacion en Colorado (P5b): la regla de lectura, la clave de bloque, el cargador sobre un warehouse sintetico y el determinismo.

Ninguna prueba depende de data/colorado ni de la red: el warehouse es una base en memoria con seis hijos aislados, cada uno con un padre
horizontal cercano (a 0,5 km), un padre vertical cercano (a 0,4 km) y un control (a 3 km). Los padres cercanos caen a la mitad del
caudal desde el mes de la fractura; los controles no cambian, asi que la brecha del mes 1 vale -0,5 y la previa vale 0.
"""
from __future__ import annotations

import calendar
import datetime as dt
import math

import duckdb
import numpy as np
import pytest

from pipeline import bloques, placebo, replicacion

N_HIJOS = 6
LAT0, LON0 = 40.0, -104.9
KM_LAT = 1 / 111.32
MES_FRAC = dt.date(2019, 8, 1)


def _meses(desde: dt.date, n: int) -> list[dt.date]:
    out, a, m = [], desde.year, desde.month
    for _ in range(n):
        out.append(dt.date(a, m, 1))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def _warehouse(n_hijos: int = N_HIJOS, dias_efectivos=None):
    """Base en memoria con las tablas de P5a que consume replicacion (dim_pozo, co_pozo_pad, co_hijo, fct_produccion, ultimo_mes)."""
    con = duckdb.connect(":memory:")
    con.execute("create table dim_pozo (pozo_id bigint, operador varchar, area varchar, tipo_pozo varchar, lon double, lat double, "
                "primer_mes_petroleo date, horizontal boolean)")
    con.execute("create table co_pozo_pad (pozo_id bigint, pad_id varchar)")
    con.execute("create table co_hijo (pozo_id bigint, mes_frac date, hijo boolean)")
    con.execute("create table fct_produccion (pozo_id bigint, mes date, petroleo_m3 double, dias_mes integer, dias_efectivos integer)")
    meses = _meses(dt.date(2017, 1, 1), 52)                  # alcanza para las fechas corridas +-12 meses del placebo
    con.execute("create table ultimo_mes as select ?::date as mes", [meses[-1]])
    pozos, produccion = [], []
    for i in range(n_hijos):
        lon = LON0 + 0.3 * i                                   # unos 25 km entre hijos: un bloque de 5 km cada uno
        coc = math.cos(math.radians(LAT0))
        pozos += [(100 + i, lon, LAT0, None, True), (200 + i, lon, LAT0 + 0.5 * KM_LAT, meses[0], True),
                  (300 + i, lon, LAT0 + 3.0 * KM_LAT, meses[0], True), (400 + i, lon + 0.4 * KM_LAT / coc, LAT0, meses[0], False)]
        for pid, cae in ((200 + i, True), (300 + i, False), (400 + i, True)):
            for m in meses:
                dm = calendar.monthrange(m.year, m.month)[1]
                tasa = 5.0 if cae and m >= MES_FRAC else 10.0
                de = dm if dias_efectivos is None else dias_efectivos(pid, m, dm)
                produccion.append((pid, m, tasa * dm, dm, de))
    for pid, lon, lat, primer, hor in pozos:
        con.execute("insert into dim_pozo values (?, 'OP A', 'Weld', 'OW', ?, ?, ?, ?)", [pid, lon, lat, primer, hor])
        con.execute("insert into co_pozo_pad values (?, ?)", [pid, f"p{pid}"])
    for i in range(n_hijos):
        con.execute("insert into co_hijo values (?, ?, true)", [100 + i, MES_FRAC])
    con.executemany("insert into fct_produccion values (?, ?, ?, ?, ?)", produccion)
    return con


# ------------------------------------------------------------------ la regla de lectura

@pytest.mark.parametrize("brecha, ic_alto, previa, se, valor", [
    (-0.20, -0.10, -0.07, True, -0.10),          # IC bajo cero y previa menor: se replica; el valor es el limite superior
    (-0.20, -0.10, -0.15, True, -0.05),          # la previa, en valor absoluto, sigue menor: el valor es la diferencia de valores absolutos
    (-0.20, 0.01, -0.07, False, 0.01),           # el IC incluye cero: no se replica
    (-0.05, -0.02, -0.08, False, 0.03),          # la previa es mayor que la del mes 1: no se replica
    (-0.10, -0.05, 0.10, False, 0.0),            # igualdad de valores absolutos: el valor es 0 y no es menor que 0
    (-0.20, -0.10, 0.07, True, -0.10),           # el signo de la previa no importa, solo su valor absoluto
])
def test_lectura_tabla_de_verdad(brecha, ic_alto, previa, se, valor):
    got_se, got_valor = replicacion.lectura(brecha, ic_alto, previa)
    assert got_se is se
    assert got_valor == pytest.approx(valor)


@pytest.mark.parametrize("args", [(float("nan"), -0.1, -0.05), (-0.2, float("nan"), -0.05), (-0.2, -0.1, float("nan")), (None, -0.1, -0.05)])
def test_un_dato_indefinido_cuenta_como_no_se_replica(args):
    se, valor = replicacion.lectura(*args)
    assert se is False and math.isnan(valor)


def test_las_reglas_numericas_son_las_preregistradas():
    assert replicacion.KM_BLOQUE == 5.0
    assert replicacion.BASE_VEREDICTO == (-3, -1) and replicacion.BASE_PREVIA == (-6, -4)
    assert replicacion.K_VEREDICTO == 1 and replicacion.K_PREVIO == -1
    assert replicacion.DESPLAZAMIENTOS_PLACEBO == (-12, 12)
    assert replicacion.semilla_k(1) == placebo.SEMILLA_PLACEBO + 100 + 4        # misma semilla por k que bloques.py


# ------------------------------------------------------------------ clave de bloque

def test_la_clave_de_bloque_es_la_de_bloques_py():
    lat = np.array([40.0, 40.0 + 1.0 * KM_LAT, 40.0 + 12.0 * KM_LAT])
    lon = np.full(3, -104.9)
    k = bloques.clave_bloque(lat, lon, 5.0)
    assert k[0] == k[1] and k[0] != k[2]                  # a 1 km comparten celda de 5 km; a 12 km no
    assert (bloques.clave_bloque(lat, lon, 5.0) == k).all() and k.dtype == np.int64


def test_cada_pad_hijo_aislado_cae_en_su_propio_bloque():
    con = _warehouse()
    replicacion.preparar(con)
    D = placebo.cargar(con)
    por_pad = replicacion.bloque_por_pad(con, D)
    assert len(por_pad) == N_HIJOS and len(set(por_pad.tolist())) == N_HIJOS


# ------------------------------------------------------------------ el cargador sobre el warehouse sintetico

def test_el_cargador_de_placebo_corre_sobre_las_tablas_preparadas():
    con = _warehouse()
    replicacion.preparar(con)
    D = placebo.cargar(con)
    assert len(D["hijo_id"]) == N_HIJOS
    ids = {r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion").fetchall()}
    assert not any(400 <= i < 500 for i in ids)           # el corte principal deja afuera los padres verticales
    m = placebo.marco(D, D["hijo_mes"], ks=(1,), base=replicacion.BASE_VEREDICTO)
    assert int((m["banda"] == 0).sum()) == N_HIJOS and int((m["banda"] == 2).sum()) == N_HIJOS
    assert m["idx"][1][m["banda"] == 0] == pytest.approx(0.5) and m["idx"][1][m["banda"] == 2] == pytest.approx(1.0)


def test_todos_los_padres_suma_los_verticales():
    con = _warehouse()
    replicacion.preparar(con, todos_los_padres=True)
    D = placebo.cargar(con)
    m = placebo.marco(D, D["hijo_mes"], ks=(1,), base=replicacion.BASE_VEREDICTO)
    assert int((m["banda"] == 0).sum()) == 2 * N_HIJOS


def test_la_tasa_por_dia_producido_deja_sin_dato_los_meses_sin_dias():
    def dias(pid, m, dm):
        return 0 if (pid == 200 and m == dt.date(2019, 9, 1)) else 15 if pid == 201 else dm
    con = _warehouse(dias_efectivos=dias)
    replicacion.preparar(con)
    D = placebo.cargar(con)
    tasa = replicacion.tasa_por_dia_producido(con, D)
    assert tasa.shape == D["tasa"].shape
    pos = {int(p[0]): i for i, p in enumerate(con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall())}
    col = lambda m: int(placebo._mes_idx([m])[0]) + placebo.PAD    # noqa: E731
    assert np.isnan(tasa[pos[200], col(dt.date(2019, 9, 1))])
    assert tasa[pos[201], col(dt.date(2019, 3, 1))] == pytest.approx(10.0 * 31 / 15)
    assert tasa[pos[202], col(dt.date(2019, 3, 1))] == pytest.approx(10.0)


# ------------------------------------------------------------------ corrida completa

def test_la_corrida_es_determinista_y_da_la_brecha_conocida():
    a = replicacion.calcular(_warehouse(), reps=30, placebo_reps=30)
    b = replicacion.calcular(_warehouse(), reps=30, placebo_reps=30)
    assert a == b                                                  # mismas semillas, mismas tablas, byte a byte
    cols, filas = a["mart_replicacion_colorado"]
    v = dict(zip([c[0] for c in cols], filas[0]))
    assert v["k"] == 1 and v["n_cercanos"] == N_HIJOS and v["n_controles"] == N_HIJOS
    assert v["brecha"] == pytest.approx(-0.5) and v["brecha_previa_limpia"] == pytest.approx(0.0)
    assert v["ic_alto_bloque"] == pytest.approx(-0.5) and v["se_replica"] is True and v["valor"] == pytest.approx(-0.5)
    rob = {r[0]: r for r in a["mart_replicacion_robustez"][1]}
    assert set(rob) == set(replicacion.CORTES)
    assert rob["todos_los_padres"][1] == 2 * N_HIJOS and rob["principal"][1] == N_HIJOS
    assert {r[1] for r in a["mart_replicacion_serie"][1] if r[0] == "limpia"} == set(range(-3, 4))
    assert {r[0] for r in a["mart_replicacion_placebo"][1]} == {0, -12, 12}


def test_las_tablas_se_escriben_y_la_pagina_lleva_el_veredicto_y_no_tiene_rayas():
    con = _warehouse()
    tablas = replicacion.calcular(con, reps=30, placebo_reps=30)
    replicacion.escribir(con, tablas)
    replicacion.escribir(con, tablas)                              # idempotente
    assert con.execute("select count(*) from mart_replicacion_colorado").fetchone()[0] == 1
    pagina = replicacion.pagina_replicacion(con)
    assert "**se replica**" in pagina and "validación externa" in pagina
    assert not any(chr(c) in pagina for c in (0x2014, 0x2013))
    assert "causa" not in pagina.replace("no se afirma causalidad", "").replace("afirmación causal", "")


def test_la_pagina_dice_que_no_se_replica_cuando_la_regla_lo_dice():
    con = _warehouse()
    tablas = replicacion.calcular(con, reps=30, placebo_reps=30)
    cols, filas = tablas["mart_replicacion_colorado"]
    i = [c[0] for c in cols].index("se_replica")
    tablas["mart_replicacion_colorado"] = (cols, [tuple(False if j == i else x for j, x in enumerate(filas[0]))])
    replicacion.escribir(con, tablas)
    assert "**no se replica**" in replicacion.pagina_replicacion(con)


def test_main_sin_warehouse_avisa_y_devuelve_2(tmp_path, capsys):
    assert replicacion.main(tmp_path / "no_existe.duckdb", None) == 2
    assert "falta" in capsys.readouterr().err


def test_otra_cuenca_usa_su_tabla_su_titulo_y_sus_limites():
    """La cuenca es un parametro: la tabla del veredicto lleva su id y la pagina su nombre, sin rastro de Colorado."""
    import dataclasses

    from pipeline import cuencas

    otra = dataclasses.replace(
        cuencas.COLORADO, id="otra", nombre="Otra", titulo="Replicación en Otra", de_el="de Otra", modulo="pipeline/otra",
        pagina_datos="otra_datos.md", ordinal="otra cuenca", regla_fijada="en el commit de la regla", nota_regla="",
        no_puede=("Un limite propio.",), rotulo_hijos="Hijos (regla fijada)", filtros="de la regla de la familia")
    con = _warehouse()
    tablas = replicacion.calcular(con, reps=30, placebo_reps=30, cuenca=otra)
    assert "mart_replicacion_otra" in tablas and "mart_replicacion_colorado" not in tablas
    replicacion.escribir(con, tablas)
    pagina = replicacion.pagina_replicacion(con, otra)
    assert pagina.startswith("# Replicación en Otra") and "## Qué Otra no puede mostrar" in pagina and "- Un limite propio." in pagina
    assert "`replicacion_otra`" in pagina and "[datos y conteos](otra_datos.md)" in pagina and "Hijos (regla fijada)" in pagina
    assert "Colorado" not in pagina and "FracFocus" not in pagina and "P5a" not in pagina


def test_el_registro_de_cuencas_nombra_las_rutas():
    from pipeline import cuencas

    c = cuencas.cuenca("colorado")
    assert c.db.parts[-3:] == ("data", "colorado", "warehouse.duckdb") and c.tabla_veredicto == "mart_replicacion_colorado"
    with pytest.raises(SystemExit):
        cuencas.cuenca("no_existe")


def test_main_de_otra_cuenca_escribe_su_pagina_y_no_la_de_colorado(tmp_path, monkeypatch):
    import dataclasses
    from pipeline.cuencas import COLORADO
    otra = dataclasses.replace(COLORADO, id="otra", pagina=tmp_path / "otra.md")
    archivo = tmp_path / "otra.duckdb"
    archivo.write_bytes(b"")                                       # solo para que exista; la conexion se reemplaza abajo
    con = _warehouse()
    monkeypatch.setattr(replicacion.duckdb, "connect", lambda *_a, **_k: con)
    antes = replicacion.PAGINA.read_bytes()
    assert replicacion.main(archivo, cuenca=otra) == 0
    assert (tmp_path / "otra.md").exists() and replicacion.PAGINA.read_bytes() == antes
