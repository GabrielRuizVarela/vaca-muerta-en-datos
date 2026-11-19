"""Wyoming: ingesta y tablas base con datos sinteticos. Ninguna prueba usa la red ni depende de data/wyoming."""
from __future__ import annotations

import calendar
import csv
import hashlib
import io
import os
import struct
import urllib.error
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import duckdb
import pytest

from pipeline import colorado as C
from pipeline import wyoming as R
from pipeline.wyoming import build as wb
from pipeline.wyoming import ingest

MESES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
PROD_COLS = (["APINO", "COMPANY", "FIELD", "YR"] + [f"{m}_OIL" for m in MESES] + [f"{m}_GAS" for m in MESES]
             + [f"{m}_WATER" for m in MESES] + [f"{m}_DAYS" for m in MESES])
POZO_COLS = ["APINO", "COMPANY", "UNIT_LEASE", "FIELD_NAME", "BASIN", "COUNTYTXT", "COUNTY", "LON", "LAT", "TD", "MD",
             "HORIZ_DIR", "WELL_CLASS", "FIRSTSPUD", "FIRSTCOMP", "STATUS"]

LAT0, LON0 = 43.0, -105.5
GRADO_LAT_KM = 1 / 111.32   # grados de latitud por km


def prod_year(apino, anio, oil=0, gas=0, agua=0, dias=None, company="OP A", field="FIELD A"):
    """Una fila de produccion (pozo y anio); oil/gas/agua/dias aceptan escalar o dict {mes: valor} (lo ausente es NULL).

    dias por defecto es el largo del mes."""
    def val(v, m):
        if isinstance(v, dict):
            return v.get(m, "")
        if v is None:
            return calendar.monthrange(anio, m)[1]
        return v
    fila = {"APINO": apino, "YR": anio, "COMPANY": company, "FIELD": field}
    for i, m in enumerate(MESES, 1):
        fila[f"{m}_OIL"], fila[f"{m}_GAS"] = val(oil, i), val(gas, i)
        fila[f"{m}_WATER"], fila[f"{m}_DAYS"] = val(agua, i), val(dias, i)
    return fila


def pozo(apino, firstcomp="", lat=LAT0, lon=LON0, md="15000", td="7000", hdir="", spud="20200101", status="PO"):
    return {"APINO": apino, "COMPANY": "OP A", "UNIT_LEASE": f"U {apino}", "FIELD_NAME": "FIELD A",
            "BASIN": "POWDER RIVER", "COUNTYTXT": "CAMPBELL", "COUNTY": "05", "LON": f"{lon:.6f}", "LAT": f"{lat:.6f}",
            "TD": td, "MD": md, "HORIZ_DIR": hdir, "WELL_CLASS": "OW", "FIRSTSPUD": spud,
            "FIRSTCOMP": firstcomp, "STATUS": status}


def escribir(path: Path, cols, filas) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    return path


def construir(tmp_path, prod_rows, pozo_rows, partes=1):
    """Warehouse en memoria desde filas sinteticas (la produccion se reparte en `partes` archivos)."""
    p = [escribir(tmp_path / f"p{i}.csv", PROD_COLS, prod_rows[i::partes]) for i in range(partes)]
    con = duckdb.connect()
    wb.build(con, p, escribir(tmp_path / "w.csv", POZO_COLS, pozo_rows))
    return con


def uno(con, sql):
    return con.execute(sql).fetchall()[0][0]


# ---------------------------------------------------------------- clave del APINO y unidades

def test_apino_texto_numerico_a_condado_mas_secuencia(tmp_path):
    con = construir(tmp_path, [prod_year("705000.00000", 2020, oil={1: 100}), prod_year(720921, 2020, oil={1: 50})],
                    [pozo("705000.00000"), pozo(720921, lat=LAT0 + 0.1)])
    assert [r[0] for r in con.execute("select pozo_id from dim_pozo order by pozo_id").fetchall()] == [705000, 720921]
    assert [r[0] for r in con.execute("select condado from dim_pozo order by pozo_id").fetchall()] == ["007", "007"]
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_filas_sin_pozo_o_anio'") == 0


def test_barriles_y_mcf_a_m3(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={3: 100}, gas={3: 1000}, agua={3: 200})],
                    [pozo(705000, firstcomp="20200310")])
    fila = con.execute("select petroleo_m3, gas_miles_m3, agua_m3 from fct_produccion where mes = date '2020-03-01'").fetchone()
    assert abs(fila[0] - 100 * 0.158987) < 1e-9
    assert abs(fila[1] - 1000 * 0.0283168) < 1e-9
    assert abs(fila[2] - 200 * 0.158987) < 1e-9


def test_empresa_con_coma_y_comillas(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100}, company='OP "A", SA')], [pozo(705000)])
    assert uno(con, "select operador from fct_produccion") == 'OP "A", SA'


def test_dim_pozo_atributos_de_wogcc(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100})], [pozo(705000, firstcomp="20200115")])
    d = dict(zip([c[0] for c in con.execute("select * from dim_pozo").description],
                 con.execute("select * from dim_pozo").fetchone()))
    assert d["provincia"] == "Wyoming" and d["sigla"] == "U 705000" and d["estado"] == "PO"
    assert d["area"] == "CAMPBELL" and d["tipo_pozo"] == "OW" and d["formacion"] == "field a"
    assert d["tvd_ft"] == 7000.0 and d["md_ft"] == 15000.0 and d["calidad_ubicacion"] is None
    assert d["con_produccion"] is True and d["en_archivo_pozos"] is True


# ---------------------------------------------------------------- filas de pozo y anio a pozo y mes

def test_el_anio_se_abre_en_doce_meses_y_el_null_es_cero(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={6: 100})], [pozo(705000)])
    assert uno(con, "select count(*) from fct_produccion") == 12
    assert abs(uno(con, "select petroleo_m3 from fct_produccion where mes = date '2020-06-01'") - 100 * 0.158987) < 1e-9
    assert uno(con, "select sum(petroleo_m3) from fct_produccion where mes <> date '2020-06-01'") == 0
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_pozo_anio'") == 1


def test_filas_repetidas_del_pozo_y_anio_se_suman_y_dias_es_el_maximo(tmp_path):
    filas = [prod_year(705000, 2020, oil={3: 100}, dias={3: 20}), prod_year(705000, 2020, oil={3: 50, 4: 10}, dias={3: 31, 4: 30})]
    con = construir(tmp_path, filas, [pozo(705000)])
    marzo = con.execute("select petroleo_m3, dias_efectivos, dias_mes from fct_produccion where mes = date '2020-03-01'").fetchone()
    assert abs(marzo[0] - 150 * 0.158987) < 1e-9
    assert marzo[1] == 31 and marzo[2] == 31          # dias efectivos: el maximo de las filas
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_pozo_anio_con_varias_filas'") == 1
    # las dos filas del pozo y anio aportan a los doce meses
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_pozo_mes_con_varias_filas'") == 12


def test_dias_99_son_desconocidos_y_31_en_abril_se_topa(tmp_path):
    # 99 es un codigo de la fuente, no un conteo: dias desconocidos. 31 en un mes de 30 se topa en 30.
    dias = {m: calendar.monthrange(2020, m)[1] for m in range(1, 13)} | {1: 99, 4: 31}
    con = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100, 4: 100}, dias=dias)], [pozo(705000)])
    assert uno(con, "select dias_efectivos from fct_produccion where mes = date '2020-01-01'") is None
    assert uno(con, "select dias_efectivos from fct_produccion where mes = date '2020-04-01'") == 30
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_pozo_mes_sin_dias_validos'") == 1
    assert all(ok for _, ok, _ in wb.controles(con))


def test_ultimo_mes_y_primer_petroleo_censurado(tmp_path):
    filas = [prod_year(705000, 2018, oil={1: 100}), prod_year(705001, 2018, oil={6: 80})]
    con = construir(tmp_path, filas, [pozo(705000), pozo(705001, lat=LAT0 + 0.1)])
    assert str(uno(con, "select mes from ultimo_mes")) == "2018-12-01"
    assert [r[0] for r in con.execute("select primer_petroleo_censurado from dim_pozo order by pozo_id").fetchall()] == [True, False]


# ---------------------------------------------------------------- horizontal (sin la columna de direccion)

@pytest.mark.parametrize("md,td,esperado", [
    ("15000", "7000", True), ("8501", "7000", True), ("8500", "7000", False),   # MD menos TD: mas de 1.500 ft
    ("2600", "1001", True), ("2500", "1000", False),                              # TD: mas de 1.000 ft
    ("2600", "900", False), ("", "7000", False), ("15000", "", False)])           # TD corta o dato faltante
def test_bandera_horizontal(tmp_path, md, td, esperado):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100})], [pozo(705000, md=md, td=td)])
    assert uno(con, "select horizontal from dim_pozo") is esperado
    assert uno(con, "select subtipo_recurso from dim_pozo") == ("HORIZONTAL" if esperado else ("VERTICAL" if md and td else "SIN_DATO"))


def test_la_columna_de_direccion_no_se_usa(tmp_path):
    vertical = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100})], [pozo(705000, md="7100", td="7000", hdir="H")])
    assert uno(vertical, "select horizontal from dim_pozo") is False
    horizontal = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100})], [pozo(705000, hdir="")])
    assert uno(horizontal, "select horizontal from dim_pozo") is True


def test_largo_de_rama_por_proxy_md_menos_td(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100})], [pozo(705000, md="15000", td="7000")])
    assert abs(uno(con, "select rama_horizontal_m from dim_pozo") - 8000 * 0.3048) < 1e-6


# ---------------------------------------------------------------- FIRSTCOMP e hijos

def _hijo(tmp_path, firstcomp, prod_desde=(2020, 6), **kw):
    filas = [prod_year(705000, prod_desde[0], oil={prod_desde[1]: 100})]
    return construir(tmp_path, filas, [pozo(705000, firstcomp=firstcomp, **kw)])


def test_firstcomp_de_siete_digitos(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2024, oil={6: 100})], [pozo(705000, firstcomp="2024615")])
    assert str(uno(con, "select fecha_frac from co_hijo")) == "2024-06-15"
    assert uno(con, "select hijo from co_hijo") is True


@pytest.mark.parametrize("crudo,fecha", [("2024104", None), ("2024112", None), ("2024101", None), ("2024615", "2024-06-15"),
                                         ("2024311", "2024-03-11"), ("2024110", "2024-01-10"), ("2021127", None)])
def test_firstcomp_de_siete_digitos_ambiguo_no_se_lee(tmp_path, crudo, fecha):
    # 2024104 es el 4 de enero (AAAAMDD) o el 4 de octubre (AAAAMMD): se lee de las dos maneras y no se elige ninguna.
    con = construir(tmp_path, [prod_year(705000, 2024, oil={6: 100})], [pozo(705000, firstcomp=crudo)])
    if fecha is None:
        assert uno(con, "select count(*) from co_hijo") == 0
        assert uno(con, "select valor from mart_co_conciliacion where clave = 'fc_no_parsean'") == 1
        assert uno(con, "select valor from mart_co_conciliacion where clave = 'fc_ambiguas'") == 1
    else:
        assert str(uno(con, "select fecha_frac from co_hijo")) == fecha
        assert uno(con, "select valor from mart_co_conciliacion where clave = 'fc_ambiguas'") == 0


def test_hijos_por_mes_de_terminacion_contra_el_primer_petroleo(tmp_path):
    filas = [prod_year(705000, 2020, oil={6: 100}), prod_year(705001, 2020, oil={6: 100}), prod_year(705002, 2020, oil={6: 100})]
    pozos = [pozo(705000, firstcomp="20200615"), pozo(705001, firstcomp="20200610", lat=LAT0 + 0.1),
             pozo(705002, firstcomp="20200701", lat=LAT0 + 0.2)]
    con = construir(tmp_path, filas, pozos)
    k = lambda c: uno(con, f"select valor from mart_co_conciliacion where clave = '{c}'")  # noqa: E731
    assert (k("hijos"), k("hijos_terminacion_mes_primer_petroleo"), k("hijos_primer_petroleo_posterior"),
            k("hijos_primer_petroleo_anterior")) == (3, 2, 0, 1)


@pytest.mark.parametrize("crudo", ["20241301", "99999999", "2024-06-15", "abc", "2024061"])
def test_firstcomp_que_no_parsea_es_null_y_se_cuenta(tmp_path, crudo):
    con = construir(tmp_path, [prod_year(705000, 2020, oil={1: 100})],
                    [pozo(705000, firstcomp=crudo), pozo(705001, firstcomp="", lat=LAT0 + 0.1)])
    assert uno(con, "select count(*) from co_hijo") == 0
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'fc_no_parsean'") == 1
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'fc_vacios'") == 1


def test_fecha_dudosa_a_mas_de_30_dias_del_primer_petroleo(tmp_path):
    # primer petroleo: 2020-06-01. 2020-07-01 son 30 dias despues (no es dudosa); 2020-07-02 son 31 (dudosa).
    ok = _hijo(tmp_path, "20200701")
    assert uno(ok, "select hijo from co_hijo") is True and uno(ok, "select fecha_dudosa from co_hijo") is False
    assert uno(ok, "select dias_desde_primer_petroleo from co_hijo") == 30
    dudoso = _hijo(tmp_path, "20200702")
    assert uno(dudoso, "select fecha_dudosa from co_hijo") is True and uno(dudoso, "select hijo from co_hijo") is False
    assert uno(dudoso, "select valor from mart_co_conciliacion where clave = 'fc_ventana_horizontales_fecha_dudosa'") == 1
    assert uno(dudoso, "select valor from mart_co_conciliacion where clave = 'hijos'") == 0


def test_pozo_sin_petroleo_no_es_hijo(tmp_path):
    con = construir(tmp_path, [prod_year(705000, 2020)], [pozo(705000, firstcomp="20200615")])
    assert uno(con, "select hijo from co_hijo") is False
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'hijos_sin_petroleo_excluidos'") == 1
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'hijos_sin_produccion'") == 0


@pytest.mark.parametrize("firstcomp,desde,esperado", [
    ("20180630", (2018, 6), False), ("20180701", (2018, 7), True),
    ("20240630", (2024, 6), True), ("20240701", (2024, 7), False)])
def test_ventana_de_terminaciones_incluye_los_bordes(tmp_path, firstcomp, desde, esperado):
    con = _hijo(tmp_path, firstcomp, prod_desde=desde)
    assert uno(con, "select en_ventana from co_hijo") is esperado
    assert uno(con, "select hijo from co_hijo") is esperado


def test_hijo_vertical_o_sin_coordenadas_no_cuenta(tmp_path):
    vertical = _hijo(tmp_path, "20200615", md="7100", td="7000")
    assert uno(vertical, "select hijo from co_hijo") is False
    assert uno(vertical, "select valor from mart_co_conciliacion where clave = 'fc_ventana_verticales_o_sin_dato'") == 1
    sin_coord = construir(tmp_path, [prod_year(705000, 2020, oil={6: 100})],
                          [dict(pozo(705000, firstcomp="20200615"), LAT="", LON="")])
    assert uno(sin_coord, "select hijo from co_hijo") is False


# ---------------------------------------------------------------- pads y conciliacion

def test_pozos_a_menos_de_50_m_comparten_pad(tmp_path):
    pozos = [pozo(705000), pozo(705001, lat=LAT0 + 0.00009), pozo(705002, lat=LAT0 + 0.0109)]
    con = construir(tmp_path, [prod_year(a, 2020, oil={1: 100}) for a in (705000, 705001, 705002)], pozos)
    pads = dict(con.execute("select pozo_id, pad_id from co_pozo_pad").fetchall())
    assert pads[705000] == pads[705001] == "p705000" and pads[705002] != pads[705000]


def _escenario(tmp_path):
    """Un hijo con terminacion en 2020-06 y cuatro padres posibles: cercano horizontal, cercano vertical, de control y de edad corta."""
    km = GRADO_LAT_KM
    pozos = [pozo(705000, firstcomp="20200615", lat=LAT0, md="15000", td="7000"),          # hijo
             pozo(705001, lat=LAT0 + 0.5 * km, md="15000", td="7000"),                    # padre horizontal a 0,5 km
             pozo(705002, lat=LAT0 - 0.7 * km, md="7100", td="7000"),                     # padre vertical a 0,7 km
             pozo(705003, lat=LAT0 + 3.0 * km, md="15000", td="7000"),                    # control a 3 km
             pozo(705004, lat=LAT0 - 0.4 * km, md="15000", td="7000")]                    # padre cercano pero de edad corta
    filas = [prod_year(a, 2019, oil=300) for a in (705001, 705002, 705003)]
    filas += [prod_year(a, 2020, oil={m: 300 for m in range(1, 9)}) for a in (705001, 705002, 705003)]
    filas += [prod_year(705004, 2020, oil={m: 300 for m in range(3, 9)})]   # primer petroleo 2020-03: solo 3 meses antes
    filas += [prod_year(705000, 2020, oil={m: 300 for m in range(6, 9)})]
    return construir(tmp_path, filas, pozos)


def test_conciliacion_cuenta_eventos_por_banda_y_corte(tmp_path):
    con = _escenario(tmp_path)

    def v(clave):
        return uno(con, f"select valor from mart_co_conciliacion where clave = '{clave}'")
    assert v("hijos") == 1
    assert v("ev_regla_todos_cercanos") == 2 and v("ev_regla_horizontales_cercanos") == 1
    assert v("ev_regla_todos_controles") == 1 and v("ev_regla_horizontales_controles") == 1
    assert v("ev_regla_todos_intermedios") == 0
    assert v("hijos_con_padre_cercano_regla_todos") == 1 and v("hijos_con_padre_cercano_regla_horizontales") == 1
    assert [tuple(r) for r in con.execute("select anio, cercanos, controles from mart_co_eventos_anio where conjunto = 'regla' and corte = 'todos'").fetchall()] == [(2020, 2, 1)]


def test_el_padre_necesita_base_mayor_que_1_m3_dia(tmp_path):
    km = GRADO_LAT_KM
    pozos = [pozo(705000, firstcomp="20200615"), pozo(705001, lat=LAT0 + 0.5 * km)]
    # 100 bbl al mes son 15,9 m3 en 30 dias: 0,53 m3/d, por debajo del umbral de 1 m3/d
    filas = [prod_year(705001, 2019, oil=100), prod_year(705001, 2020, oil={m: 100 for m in range(1, 9)})]
    filas += [prod_year(705000, 2020, oil={m: 300 for m in range(6, 9)})]
    con = construir(tmp_path, filas, pozos)
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'ev_regla_todos_cercanos'") == 0


def test_controles_del_build_pasan_y_son_deterministas(tmp_path):
    a = _escenario(tmp_path)
    assert all(ok for _, ok, _ in wb.controles(a))
    b = _escenario(tmp_path)
    for tabla in ("fct_produccion", "dim_pozo", "co_hijo", "co_pozo_pad", "mart_co_conciliacion", "mart_co_eventos_anio",
                  "wy_encabezados_xlsx", "co_fuentes"):
        q = f"select * from {tabla} order by all"
        assert a.execute(q).fetchall() == b.execute(q).fetchall(), tabla


def test_una_corrida_en_varios_archivos_da_lo_mismo(tmp_path):
    km = GRADO_LAT_KM
    pozos = [pozo(705000, firstcomp="20200615"), pozo(705001, lat=LAT0 + 0.5 * km)]
    filas = [prod_year(705001, 2019, oil=300), prod_year(705001, 2020, oil={m: 300 for m in range(1, 9)})]
    filas += [prod_year(705000, 2020, oil={m: 300 for m in range(6, 9)})]
    (tmp_path / "x").mkdir()
    uno_solo = construir(tmp_path / "x", filas, pozos, partes=1)
    (tmp_path / "y").mkdir()
    varios = construir(tmp_path / "y", filas, pozos, partes=3)
    assert uno_solo.execute("select * from fct_produccion order by all").fetchall() == varios.execute("select * from fct_produccion order by all").fetchall()


# ---------------------------------------------------------------- pagina y constantes

def test_pagina_sin_rayas_y_con_las_cifras_del_warehouse(tmp_path):
    con = _escenario(tmp_path)
    t = wb.pagina_wyoming(con)
    assert chr(0x2014) not in t and chr(0x2013) not in t
    assert t.startswith("# Wyoming")
    assert "| Pozo-mes (a\u00f1os abiertos en doce meses, filas repetidas sumadas) | " in t
    assert "WOGCC" in t and "FIRSTCOMP" in t
    assert t == wb.pagina_wyoming(con)


def test_encabezados_de_los_csv_en_el_warehouse(tmp_path):
    con = _escenario(tmp_path)
    filas = con.execute("select encabezado from wy_encabezados_xlsx").fetchall()
    assert filas and all("APINO" in e[0] and "JAN_OIL" in e[0] and "DEC_DAYS" in e[0] for e in filas)


def test_las_constantes_son_las_de_colorado():
    for nombre in ("HORIZONTAL_TVD_MIN_FT", "HORIZONTAL_LATERAL_MIN_FT", "VENTANA_FRAC", "FECHA_DUDOSA_DIAS",
                   "EDAD_MIN_MESES", "BASE_MIN_M3_D", "KM_CERCANO", "KM_CONTROL", "KM_MAX", "PAD_KM", "KM_POR_GRADO",
                   "FT_A_M", "BBL_A_M3"):
        assert getattr(R, nombre) == getattr(C, nombre), nombre


# ---------------------------------------------------------------- ingesta: XLSX, DBF, manifiesto

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _letra(i: int) -> str:
    out = ""
    while True:
        i, r = divmod(i, 26)
        out = chr(65 + r) + out
        if not i:
            return out
        i -= 1


def _xlsx_bytes(encabezados, filas, con_ss=True):
    """Un XLSX minimo en bytes: primera hoja mas (opcional) cadenas compartidas."""
    ss: list[str] = []

    def celda(ref, v):
        if isinstance(v, str):
            if con_ss:
                if v not in ss:
                    ss.append(v)
                return f'<c r="{ref}" t="s"><v>{ss.index(v)}</v></c>'
            return f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
        return f'<c r="{ref}"><v>{v}</v></c>'

    def fila_xml(n, valores):
        return f'<row r="{n}">' + "".join(celda(f"{_letra(i)}{n}", v) for i, v in enumerate(valores)) + "</row>"

    hoja = (f'<worksheet xmlns="{NS}"><sheetData>' + fila_xml(1, encabezados)
            + "".join(fila_xml(n, f) for n, f in enumerate(filas, 2)) + "</sheetData></worksheet>")
    sst = (f'<sst xmlns="{NS}" count="{len(ss)}" uniqueCount="{len(ss)}">'
           + "".join(f"<si><t>{escape(s)}</t></si>" for s in ss) + "</sst>")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml", hoja)
        if con_ss:
            z.writestr("xl/sharedStrings.xml", sst)
    return b.getvalue()


def _encabezados_xlsx():
    return ["APINO", "Company", "FIELD NAME", "YR"] + [f"{m} {t}" for m in MESES for t in ("Oil", "Gas", "Water", "Days")]


def test_xlsx_a_csv_canoniza_y_convierte_numeros(tmp_path):
    datos = _xlsx_bytes(_encabezados_xlsx(), [
        [705000.0, "OP A", "FIELD A", 2020, *([100, 5.5, 0, 31] + [0] * 44)],
        [720921, "OP B", "FIELD B", 2020],       # fila rala: se rellena
        ["", "", "", ""],                        # fila vacia: no se escribe
    ])
    destino = tmp_path / "prod.csv"
    original = ingest.xlsx_a_csv(datos, destino)
    assert original[:4] == ["APINO", "Company", "FIELD NAME", "YR"]
    assert original[4] == "JAN Oil"
    lineas = destino.read_text(encoding="utf-8").splitlines()
    assert lineas[0].split(",")[:6] == ["APINO", "COMPANY", "FIELD", "YR", "JAN_OIL", "JAN_GAS"]
    assert len(lineas) == 3
    assert lineas[1].split(",")[:8] == ["705000", "OP A", "FIELD A", "2020", "100", "5.5", "0", "31"]
    assert lineas[2].split(",")[0] == "720921" and lineas[2].count(",") == lineas[0].count(",")


def test_xlsx_sin_cadenas_compartidas_y_fila_rala(tmp_path):
    datos = _xlsx_bytes(["APINO", "YR", *[f"{m}_OIL" for m in MESES], *[f"{m}_GAS" for m in MESES],
                         *[f"{m}_WATER" for m in MESES], *[f"{m}_DAYS" for m in MESES]],
                        [[705000, 2020, 100]], con_ss=False)
    destino = tmp_path / "p.csv"
    ingest.xlsx_a_csv(datos, destino)
    lineas = destino.read_text(encoding="utf-8").splitlines()
    assert lineas[1].split(",")[:3] == ["705000", "2020", "100"]
    assert "COMPANY,FIELD" in lineas[0]   # las opcionales ausentes se agregan vacias


@pytest.mark.parametrize("crudo,canon", [("JAN_OIL", "JAN_OIL"), ("Jan Oil", "JAN_OIL"), ("jan_oil", "JAN_OIL"),
                                        ("DEC-DAYS", "DEC_DAYS"), ("API", "APINO"), ("Year", "YR"),
                                        ("Operator", "COMPANY"), ("Field Name", "FIELD")])
def test_canonizar_columna(crudo, canon):
    assert ingest.canonizar_columna(crudo) == canon


def test_xlsx_sin_columna_de_mes_frena_nombrandola(tmp_path):
    enc = [c for c in _encabezados_xlsx() if c != "JAN Oil"]
    with pytest.raises(ValueError, match="JAN_OIL"):
        ingest.xlsx_a_csv(_xlsx_bytes(enc, []), tmp_path / "p.csv")


def test_xlsx_con_columnas_canonicas_repetidas_frena(tmp_path):
    enc = ["APINO", "API", "YR", *[f"{m}_OIL" for m in MESES], *[f"{m}_GAS" for m in MESES],
           *[f"{m}_WATER" for m in MESES], *[f"{m}_DAYS" for m in MESES]]
    with pytest.raises(ValueError, match="APINO"):
        ingest.xlsx_a_csv(_xlsx_bytes(enc, []), tmp_path / "p.csv")


def _dbf(campos: list[tuple[str, int]], filas: list[list[str]]) -> bytes:
    largo_reg = 1 + sum(w for _, w in campos)
    cab = bytearray(32)
    cab[0] = 3
    struct.pack_into("<IHH", cab, 4, len(filas), 32 + 32 * len(campos) + 1, largo_reg)
    desc = b""
    for nombre, w in campos:
        d = bytearray(32)
        d[:len(nombre)] = nombre.encode()
        d[11] = ord("C")
        d[16] = w
        desc += bytes(d)
    cuerpo = b"".join(b" " + b"".join(v.ljust(w).encode("latin1") for v, (_, w) in zip(f, campos)) for f in filas)
    return bytes(cab) + desc + b"\x0d" + cuerpo


def test_pozos_a_csv_usa_el_dbf_de_pozos_y_no_el_de_taponados(tmp_path):
    zp = tmp_path / "wh.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("110326WH.DBF", _dbf([("APINO", 14), ("LAT", 9)], [["705000.00000", "43.000010"]]))
        z.writestr("110326PA.DBF", _dbf([("APINO", 14)], [["99999999"]]))
    n = ingest.pozos_a_csv(zp, tmp_path / "w.csv")
    assert n == 1
    assert (tmp_path / "w.csv").read_text().splitlines() == ["APINO,LAT", "705000.00000,43.000010"]
    assert ingest.miembro_encabezados(zp) == "110326WH.DBF"


def test_miembros_produccion_son_los_xlsx_ordenados(tmp_path):
    zp = tmp_path / "prod.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("b.xlsx", b"x")
        z.writestr("a.xlsx", b"x")
        z.writestr("nota.txt", b"x")
    assert ingest.miembros_produccion(zp) == ["a.xlsx", "b.xlsx"]


def test_manifiesto_ida_y_vuelta(tmp_path):
    p = tmp_path / "m" / "manifest.json"
    ingest.guardar_manifiesto({"a": {"sha256": "x", "bytes": 1}}, p)
    assert ingest.cargar_manifiesto(p) == {"a": {"sha256": "x", "bytes": 1}}
    assert ingest.cargar_manifiesto(tmp_path / "no.json") == {}


def test_las_urls_de_las_fuentes():
    assert ingest.URL_POZOS == "https://pipeline.wyo.gov/downloads/110326WH.zip"
    assert ingest.URL_PRODUCCION == "https://pipeline.wyo.gov/downloads/TTLProd_110426.zip"
    assert ingest.RAW.name == "raw" and ingest.RAW.parent.name == "wyoming"


def test_descargar_reintenta_una_sola_vez_ante_error_de_red(monkeypatch, tmp_path):
    class Resp:
        def __init__(self, datos=b"datos"):
            self._datos, self.headers = datos, {}
            self._leido = False

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            if self._leido:
                return b""
            self._leido = True
            return self._datos

    llamadas = []

    def cae_una_vez(url, metodo="GET"):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise urllib.error.URLError("corte")
        return Resp()

    monkeypatch.setattr(ingest, "_pedido", cae_una_vez)
    meta = ingest.descargar("http://ejemplo.invalido/x.zip", tmp_path / "x.zip")
    assert len(llamadas) == 2 and (tmp_path / "x.zip").read_bytes() == b"datos"
    assert meta["sha256"] == hashlib.sha256(b"datos").hexdigest()

    def cae_siempre(url, metodo="GET"):
        llamadas.append(1)
        raise urllib.error.URLError("corte")

    monkeypatch.setattr(ingest, "_pedido", cae_siempre)
    antes = len(llamadas)
    with pytest.raises(urllib.error.URLError):
        ingest.descargar("http://ejemplo.invalido/y.zip", tmp_path / "y.zip")
    assert len(llamadas) - antes == 2   # el intento mas un unico reintento, nada mas


# ---------------------------------------------------------------- red (omitidas por defecto)

@pytest.mark.skipif(not os.environ.get("VM_RED"), reason="necesita la red: VM_RED=1")
def test_fuentes_responden():
    assert ingest.tamano_remoto(ingest.URL_POZOS) > 10_000_000
    assert ingest.tamano_remoto(ingest.URL_PRODUCCION) > 400_000_000
