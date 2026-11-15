"""Colorado (P5a): ingesta y tablas base con datos sinteticos. Ninguna prueba usa la red ni depende de data/colorado."""
from __future__ import annotations

import calendar
import csv
import hashlib
import io
import os
import random
import struct
import zipfile
import zlib
from pathlib import Path

import duckdb
import pytest

from pipeline import colorado as R
from pipeline.colorado import build as cb
from pipeline.colorado import ingest

PROD_COLS = ["DocNum", "ReportMonth", "ReportYear", "DaysProduced", "AcceptedDate", "Revised", "OpName", "ApiCountyCode",
             "ApiSequenceNumber", "ApiSidetrack", "WellStatus", "FormationCode", "OilProduced", "GasProduced", "WaterProduced"]
POZO_COLS = ["API_County", "API_Seq", "Well_Name", "Operator", "Facil_Stat", "Well_Class", "Spud_Date", "Max_MD", "Max_TVD",
             "Latitude", "Longitude", "Loc_Qual", "Facil_Id"]
FF_COLS = ["DisclosureId", "JobStartDate", "JobEndDate", "APINumber", "StateName", "CountyName", "OperatorName", "Latitude",
           "Longitude", "TVD", "TotalBaseWaterVolume"]

LAT0, LON0 = 40.0, -104.9
GRADO_LAT_KM = 1 / 111.32   # grados de latitud por km


def prod(cc, sq, anio, mes, oil, dias=None, st="00", fm="NBRR", doc=1, acc="03/01/2020 10:00:00", rev="", gas=0, agua=0, op="OP A", ws="PR"):
    dias = calendar.monthrange(anio, mes)[1] if dias is None else dias      # por defecto, el mes completo
    return {"DocNum": doc, "ReportMonth": mes, "ReportYear": anio, "DaysProduced": dias, "AcceptedDate": acc, "Revised": rev,
            "OpName": op, "ApiCountyCode": cc, "ApiSequenceNumber": sq, "ApiSidetrack": st, "WellStatus": ws,
            "FormationCode": fm, "OilProduced": oil, "GasProduced": gas, "WaterProduced": agua}


def pozo(cc, sq, lat=LAT0, lon=LON0, md="15000", tvd="7000", spud="20200101", loc="ACTUAL LatLong", fid=1):
    return {"API_County": cc, "API_Seq": sq, "Well_Name": f"W {cc}-{sq}", "Operator": "OP A", "Facil_Stat": "PR", "Well_Class": "OW",
            "Spud_Date": spud, "Max_MD": md, "Max_TVD": tvd, "Latitude": f"{lat:.6f}", "Longitude": f"{lon:.6f}",
            "Loc_Qual": loc, "Facil_Id": fid}


def ff(i, api14, inicio, estado="Colorado", condado="Weld"):
    return {"DisclosureId": f"d{i:03d}", "JobStartDate": inicio, "JobEndDate": inicio, "APINumber": api14, "StateName": estado,
            "CountyName": condado, "OperatorName": "OP A", "Latitude": "40.0", "Longitude": "-104.9", "TVD": "7000",
            "TotalBaseWaterVolume": "1000000"}


def fecha(a, m, d):
    return f"{m}/{d}/{a} 12:00:00 AM"


def escribir(path: Path, cols, filas) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    return path


def construir(tmp_path, prod_rows, pozo_rows, ff_rows, partes=1):
    """Warehouse en memoria desde filas sinteticas (la produccion se reparte en `partes` archivos)."""
    p = [escribir(tmp_path / f"p{i}.csv", PROD_COLS, prod_rows[i::partes]) for i in range(partes)]
    con = duckdb.connect()
    cb.build(con, p, escribir(tmp_path / "w.csv", POZO_COLS, pozo_rows), escribir(tmp_path / "f.csv", FF_COLS, ff_rows))
    return con


def uno(con, sql):
    return con.execute(sql).fetchall()[0][0]


# ---------------------------------------------------------------- clave del API y unidades

def test_api14_de_fracfocus_a_condado_mas_secuencia(tmp_path):
    con = construir(tmp_path, [prod("123", "24638", 2020, 1, 100)], [pozo("123", "24638")],
                    [ff(1, "05123246380000", fecha(2020, 1, 5)),        # 14 digitos: condado 123, secuencia 24638
                     ff(2, "05123246380100", fecha(2020, 1, 6)),        # sidetrack 01 del mismo pozo
                     ff(3, "5123246380000", fecha(2020, 1, 7)),         # 13 digitos: invalido
                     ff(4, "49123246380000", fecha(2020, 1, 7), estado="Wyoming")])  # otro estado
    assert [r[0] for r in con.execute("select pozo_id from stg_co_fracfocus order by divulgacion").fetchall()] == [12324638, 12324638, None]
    assert uno(con, "select count(*) from stg_co_fracfocus") == 3
    assert [r[0] for r in con.execute("select sidetrack from stg_co_fracfocus order by divulgacion").fetchall()][:2] == ["00", "01"]


def test_condado_con_ceros_a_la_izquierda_y_pozo_id(tmp_path):
    con = construir(tmp_path, [prod("017", "06369", 2020, 1, 100)], [pozo("017", "06369")], [ff(1, "05017063690000", fecha(2020, 1, 5))])
    assert uno(con, "select pozo_id from dim_pozo") == 1706369
    assert uno(con, "select pozo_id from stg_co_fracfocus") == 1706369


def test_barriles_a_m3_y_otras_unidades(tmp_path):
    con = construir(tmp_path, [prod("123", "1", 2020, 1, 100, gas=1000, agua=200)], [pozo("123", "1")], [ff(1, "05123000010000", fecha(2020, 1, 5))])
    assert abs(uno(con, "select petroleo_m3 from fct_produccion") - 100 * 0.158987) < 1e-9
    assert abs(uno(con, "select agua_m3 from fct_produccion") - 200 * 0.158987) < 1e-9
    assert abs(uno(con, "select gas_miles_m3 from fct_produccion") - 1000 * 0.0283168) < 1e-9
    assert abs(uno(con, "select agua_m3 from stg_fractura") - 1_000_000 * 0.00378541) < 1e-6


# ---------------------------------------------------------------- pozo y mes

def test_formaciones_y_sidetracks_se_suman_al_pozo_y_mes(tmp_path):
    filas = [prod("123", "1", 2020, 3, 100, fm="NBRR", dias=20), prod("123", "1", 2020, 3, 50, fm="CODL", dias=28),
             prod("123", "1", 2020, 3, 25, fm="NBRR", st="01", dias=31),
             prod("123", "1", 2020, 4, 10, fm="NBRR", dias=30)]
    con = construir(tmp_path, filas, [pozo("123", "1")], [ff(1, "05123000010000", fecha(2020, 1, 5))])
    assert uno(con, "select count(*) from fct_produccion") == 2
    marzo = con.execute("select petroleo_m3, dias_efectivos, dias_mes, formacion from fct_produccion where mes = date '2020-03-01'").fetchone()
    assert abs(marzo[0] - 175 * 0.158987) < 1e-9
    assert marzo[1] == 31 and marzo[2] == 31          # dias efectivos: el maximo de las filas
    assert marzo[3] == "nbrr"                         # la formacion que mas petroleo dio ese mes, en minuscula


def test_dias_efectivos_es_el_maximo_y_no_la_suma(tmp_path):
    filas = [prod("123", "1", 2020, 2, 10, fm=f, dias=d) for f, d in (("A", 12), ("B", 29), ("C", 5))]
    con = construir(tmp_path, filas, [pozo("123", "1")], [ff(1, "05123000010000", fecha(2020, 1, 5))])
    assert uno(con, "select dias_efectivos from fct_produccion") == 29


def test_fila_repetida_gana_la_ultima_aceptada(tmp_path):
    filas = [prod("123", "1", 2020, 5, 100, doc=1, acc="06/01/2020 10:00:00"),
             prod("123", "1", 2020, 5, 400, doc=2, acc="07/01/2020 10:00:00", rev="Y")]
    con = construir(tmp_path, filas, [pozo("123", "1")], [ff(1, "05123000010000", fecha(2020, 1, 5))])
    assert abs(uno(con, "select petroleo_m3 from fct_produccion") - 400 * 0.158987) < 1e-9
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_filas_fuente'") == 2
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'prod_filas_tras_revision'") == 1


def test_ultimo_mes_y_primer_petroleo_censurado(tmp_path):
    filas = [prod("123", "1", 2018, 1, 100), prod("123", "1", 2018, 2, 100), prod("123", "2", 2018, 5, 0), prod("123", "2", 2018, 6, 80)]
    con = construir(tmp_path, filas, [pozo("123", "1"), pozo("123", "2", lat=LAT0 + 0.1)], [ff(1, "05123000010000", fecha(2018, 1, 5))])
    assert str(uno(con, "select mes from ultimo_mes")) == "2018-06-01"
    assert [r[0] for r in con.execute("select primer_petroleo_censurado from dim_pozo order by pozo_id").fetchall()] == [True, False]
    assert str(uno(con, "select primer_mes_petroleo from dim_pozo where pozo_id = 12300002")) == "2018-06-01"


# ---------------------------------------------------------------- horizontal

@pytest.mark.parametrize("md,tvd,esperado", [
    ("15000", "7000", True), ("8501", "7000", True), ("8500", "7000", False),   # MD menos TVD: mas de 1.500 ft
    ("2600", "1001", True), ("2500", "1000", False),                              # TVD: mas de 1.000 ft
    ("2600", "900", False), ("", "7000", False), ("15000", "", False)])           # TVD corta o dato faltante
def test_bandera_horizontal(tmp_path, md, tvd, esperado):
    con = construir(tmp_path, [prod("123", "1", 2020, 1, 100)], [pozo("123", "1", md=md, tvd=tvd)], [ff(1, "05123000010000", fecha(2020, 1, 5))])
    assert uno(con, "select horizontal from dim_pozo") is esperado
    assert uno(con, "select subtipo_recurso from dim_pozo") == ("HORIZONTAL" if esperado else ("VERTICAL" if md and tvd else "SIN_DATO"))


def test_largo_de_rama_por_proxy_md_menos_tvd(tmp_path):
    con = construir(tmp_path, [prod("123", "1", 2020, 1, 100)], [pozo("123", "1", md="15000", tvd="7000")], [ff(1, "05123000010000", fecha(2020, 1, 5))])
    assert abs(uno(con, "select rama_horizontal_m from dim_pozo") - 8000 * 0.3048) < 1e-6
    assert abs(uno(con, "select rama_horizontal_m from stg_fractura") - 8000 * 0.3048) < 1e-6


# ---------------------------------------------------------------- hijos

def _hijo(tmp_path, inicio, prod_desde=(2020, 6), extra_ff=(), **kw):
    filas = [prod("123", "1", prod_desde[0], prod_desde[1], 100)]
    ffs = [ff(1, "05123000010000", inicio)] + list(extra_ff)
    return construir(tmp_path, filas, [pozo("123", "1", **kw)], ffs)


def test_fecha_dudosa_a_mas_de_30_dias_del_primer_petroleo(tmp_path):
    # primer petroleo: 2020-06-01. 2020-07-01 son 30 dias despues (no es dudosa); 2020-07-02 son 31 (dudosa).
    ok = _hijo(tmp_path, fecha(2020, 7, 1))
    assert uno(ok, "select hijo from co_hijo") is True and uno(ok, "select fecha_dudosa from co_hijo") is False
    assert uno(ok, "select dias_desde_primer_petroleo from co_hijo") == 30
    dudoso = _hijo(tmp_path, fecha(2020, 7, 2))
    assert uno(dudoso, "select fecha_dudosa from co_hijo") is True and uno(dudoso, "select hijo from co_hijo") is False
    assert uno(dudoso, "select valor from mart_co_conciliacion where clave = 'ff_ventana_horizontales_fecha_dudosa'") == 1
    assert uno(dudoso, "select valor from mart_co_conciliacion where clave = 'hijos'") == 0


def test_el_hijo_es_la_primera_divulgacion_del_pozo(tmp_path):
    # divulgacion de 2015 y otra de 2020: la primera es de 2015, fuera de la ventana; no es hijo (un refrac no es un hijo nuevo).
    con = _hijo(tmp_path, fecha(2020, 6, 10), extra_ff=[ff(2, "05123000010000", fecha(2015, 3, 1))])
    assert uno(con, "select mes_frac from co_hijo")  .isoformat() == "2015-03-01"
    assert uno(con, "select hijo from co_hijo") is False
    # la regla de la memoria (la mas antigua dentro de la ventana) si lo contaria
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'hijos_memoria'") == 1


@pytest.mark.parametrize("inicio,esperado", [
    (fecha(2018, 6, 30), False), (fecha(2018, 7, 1), True), (fecha(2024, 6, 30), True), (fecha(2024, 7, 1), False)])
def test_ventana_de_fracturas_incluye_los_bordes(tmp_path, inicio, esperado):
    desde = (2018, 5) if inicio.startswith("6/30/2018") else (int(inicio.split("/")[2].split()[0]), int(inicio.split("/")[0]))
    con = _hijo(tmp_path, inicio, prod_desde=desde)
    assert uno(con, "select en_ventana from co_hijo") is esperado
    assert uno(con, "select hijo from co_hijo") is esperado


def test_hijo_vertical_o_sin_coordenadas_no_cuenta(tmp_path):
    vertical = _hijo(tmp_path, fecha(2020, 6, 10), md="7100", tvd="7000")
    assert uno(vertical, "select hijo from co_hijo") is False
    assert uno(vertical, "select valor from mart_co_conciliacion where clave = 'ff_ventana_verticales_o_sin_dato'") == 1


# ---------------------------------------------------------------- pads y conciliacion

def test_pozos_a_menos_de_50_m_comparten_pad(tmp_path):
    pozos = [pozo("123", "1"), pozo("123", "2", lat=LAT0 + 0.00009), pozo("123", "3", lat=LAT0 + 0.0109)]
    con = construir(tmp_path, [prod("123", str(i), 2020, 1, 100) for i in (1, 2, 3)], pozos, [ff(1, "05123000010000", fecha(2020, 1, 5))])
    pads = dict(con.execute("select pozo_id, pad_id from co_pozo_pad").fetchall())
    assert pads[12300001] == pads[12300002] == "p12300001" and pads[12300003] != pads[12300001]


def _escenario(tmp_path):
    """Un hijo con fractura en 2020-06 y cuatro padres posibles: cercano horizontal, cercano vertical, de control y de edad corta."""
    km = GRADO_LAT_KM
    pozos = [pozo("123", "1", lat=LAT0, md="15000", tvd="7000"),                       # hijo
             pozo("123", "2", lat=LAT0 + 0.5 * km, md="15000", tvd="7000"),            # padre horizontal a 0,5 km
             pozo("123", "3", lat=LAT0 - 0.7 * km, md="7100", tvd="7000"),             # padre vertical a 0,7 km
             pozo("123", "4", lat=LAT0 + 3.0 * km, md="15000", tvd="7000"),            # control a 3 km
             pozo("123", "5", lat=LAT0 - 0.4 * km, md="15000", tvd="7000")]            # padre cercano pero de edad corta
    meses = [(2019, m) for m in range(1, 13)] + [(2020, m) for m in range(1, 9)]
    filas = [prod("123", str(s), a, m, 300) for s in (2, 3, 4) for a, m in meses]
    filas += [prod("123", "5", a, m, 300) for a, m in meses if (a, m) >= (2020, 3)]   # primer petroleo 2020-03: solo 3 meses antes
    filas += [prod("123", "1", 2020, m, 300) for m in range(6, 9)]
    return construir(tmp_path, filas, pozos, [ff(1, "05123000010000", fecha(2020, 6, 15))])


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
    pozos = [pozo("123", "1"), pozo("123", "2", lat=LAT0 + 0.5 * km)]
    meses = [(2019, m) for m in range(1, 13)] + [(2020, m) for m in range(1, 9)]
    # 100 bbl al mes son 15,9 m3 en 30 dias: 0,53 m3/d, por debajo del umbral de 1 m3/d
    filas = [prod("123", "2", a, m, 100) for a, m in meses] + [prod("123", "1", 2020, 7, 300)]
    con = construir(tmp_path, filas, pozos, [ff(1, "05123000010000", fecha(2020, 6, 15))])
    assert uno(con, "select valor from mart_co_conciliacion where clave = 'ev_regla_todos_cercanos'") == 0


def test_controles_del_build_pasan_y_son_deterministas(tmp_path):
    a = _escenario(tmp_path)
    assert all(ok for _, ok, _ in cb.controles(a))
    b = _escenario(tmp_path)
    for tabla in ("fct_produccion", "dim_pozo", "stg_fractura", "dim_fractura_pozo", "co_hijo", "co_pozo_pad", "mart_co_conciliacion", "mart_co_eventos_anio"):
        q = f"select * from {tabla} order by all"
        assert a.execute(q).fetchall() == b.execute(q).fetchall(), tabla


def test_una_corrida_en_varios_archivos_da_lo_mismo(tmp_path):
    a = _escenario(tmp_path)
    sub = tmp_path / "x"
    sub.mkdir()
    km = GRADO_LAT_KM
    pozos = [pozo("123", "1"), pozo("123", "2", lat=LAT0 + 0.5 * km)]
    meses = [(2019, m) for m in range(1, 13)] + [(2020, m) for m in range(1, 9)]
    filas = [prod("123", "2", y, m, 300) for y, m in meses] + [prod("123", "1", 2020, 7, 300)]
    uno_solo = construir(sub, filas, pozos, [ff(1, "05123000010000", fecha(2020, 6, 15))], partes=1)
    (tmp_path / "y").mkdir()
    varios = construir(tmp_path / "y", filas, pozos, [ff(1, "05123000010000", fecha(2020, 6, 15))], partes=3)
    assert uno_solo.execute("select * from fct_produccion order by all").fetchall() == varios.execute("select * from fct_produccion order by all").fetchall()
    assert a is not None


# ---------------------------------------------------------------- pagina y claims

def test_claims_del_colorado_se_saltan_sin_su_warehouse_y_se_cumplen_con_el_sintetico(tmp_path):
    from pipeline import claims
    cs = claims._claims_colorado()
    assert cs and all(c.almacen == "colorado" for c in cs)
    con = _escenario(tmp_path)
    pag = tmp_path / "raiz" / "wiki" / "hallazgos" / "colorado_datos.md"
    pag.parent.mkdir(parents=True)
    pag.write_text(cb.pagina_colorado(con), encoding="utf-8")
    sin = claims.verificar(cs, raiz=tmp_path / "raiz", wh_co=tmp_path / "no_existe.duckdb")
    assert {r.estado for r in sin} == {"SKIP"}
    db = tmp_path / "co.duckdb"
    filas = con.execute("select orden, clave, valor from mart_co_conciliacion").fetchall()
    c3 = duckdb.connect(str(db))
    c3.execute("create table mart_co_conciliacion (orden integer, clave varchar, valor bigint)")
    c3.executemany("insert into mart_co_conciliacion values (?, ?, ?)", filas)
    c3.close()
    con_valores = claims.verificar(cs, raiz=tmp_path / "raiz", wh_co=db)
    assert {r.estado for r in con_valores} == {"PASS"}, [(r.claim.id, r.detalle) for r in con_valores if r.estado != "PASS"]


def test_pagina_sin_rayas_y_con_las_cifras_del_warehouse(tmp_path):
    con = _escenario(tmp_path)
    t = cb.pagina_colorado(con)
    assert chr(0x2014) not in t and chr(0x2013) not in t
    assert t.startswith("# Colorado")
    assert "| Pozo-mes (formaciones y sidetracks sumados) | " in t
    assert t == cb.pagina_colorado(con)


# ---------------------------------------------------------------- ingesta: zip por rangos, DBF, manifiesto

def _zip(miembros: dict[str, bytes], metodo=zipfile.ZIP_DEFLATED) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", metodo) as z:
        for n, d in miembros.items():
            z.writestr(n, d)
    return b.getvalue()


def _leer(datos: bytes, log=None):
    def leer(ini, fin):
        if log is not None:
            log.append((ini, fin))
        return datos[ini:fin + 1]
    return leer


def test_extraer_miembro_por_rangos_sin_bajar_el_zip_entero():
    grande = b"DisclosureId,APINumber\n" + b"x,05123000010000\n" * 50000
    zip_bytes = _zip({"readme.txt": b"hola" * 100, "DisclosureList_1.csv": grande, "Registry_1.csv": random.Random(7).randbytes(2_000_000)})
    log: list = []
    salida = b"".join(ingest.extraer_miembro(_leer(zip_bytes, log), len(zip_bytes), "DisclosureList_1.csv"))
    assert salida == grande
    pedidos = sum(fin - ini + 1 for ini, fin in log)
    assert pedidos < len(zip_bytes) / 2                 # no se leyo el zip completo (el otro miembro grande quedo sin leer)


def test_extraer_miembro_detecta_corrupcion_por_crc():
    z = bytearray(_zip({"DisclosureList_1.csv": b"abc" * 1000}, metodo=zipfile.ZIP_STORED))
    i = z.find(b"abc")
    z[i + 5] ^= 0xFF
    with pytest.raises(ingest.ErrorRango, match="CRC"):
        b"".join(ingest.extraer_miembro(_leer(bytes(z)), len(z), "DisclosureList_1.csv"))


def test_directorio_central_y_miembro_ausente():
    z = _zip({"a.txt": b"1", "b.txt": b"2"})
    assert [e["nombre"] for e in ingest.directorio_central(_leer(z), len(z))] == ["a.txt", "b.txt"]
    with pytest.raises(ingest.ErrorRango, match="no tiene"):
        ingest.entrada(_leer(z), len(z), "c.txt")


def test_un_servidor_que_no_atiende_rangos_frena(monkeypatch):
    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"x"
    monkeypatch.setattr(ingest, "_pedido", lambda *a, **k: Resp())
    with pytest.raises(ingest.ErrorRango, match="no atiende rangos"):
        ingest.leer_rango_http("http://ejemplo.invalido/z.zip")(0, 9)


def _dbf(campos: list[tuple[str, int]], filas: list[list[str]], borradas: tuple[int, ...] = ()) -> bytes:
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
    cuerpo = b""
    for i, f in enumerate(filas):
        cuerpo += (b"*" if i in borradas else b" ") + b"".join(v.ljust(w).encode("latin1") for v, (_, w) in zip(f, campos))
    return bytes(cab) + desc + b"\x0d" + cuerpo


def test_lector_de_dbf_filas_y_borrados():
    d = _dbf([("API", 8), ("Operator", 12)], [["12324638", "KERR MCGEE"], ["01706369", "OTRA SA"], ["99999999", "BORRADA"]], borradas=(2,))
    filas = list(ingest.leer_dbf(io.BytesIO(d)))
    assert filas == [["API", "Operator"], ["12324638", "KERR MCGEE"], ["01706369", "OTRA SA"]]
    with pytest.raises(ValueError):
        list(ingest.leer_dbf(io.BytesIO(d[:-5])))


def test_pozos_a_csv_desde_el_zip(tmp_path):
    zp = tmp_path / "w.zip"
    zp.write_bytes(_zip({"Wells.dbf": _dbf([("API", 8), ("Latitude", 9)], [["12324638", "40.300010"]]), "Wells.prj": b"x"}))
    n = ingest.pozos_a_csv(zp, tmp_path / "w.csv")
    assert n == 1 and (tmp_path / "w.csv").read_text().splitlines() == ["API,Latitude", "12324638,40.300010"]


def test_asegurar_fracfocus_valida_la_copia_y_registra(tmp_path):
    csv_bytes = b"DisclosureId,APINumber\nx,05123000010000\n" * 200
    zb = _zip({"DisclosureList_1.csv": csv_bytes})
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / ingest.RUTA_FRACFOCUS).write_bytes(csv_bytes)       # copia previa, sin manifiesto
    m: dict = {}
    r1 = ingest.asegurar_fracfocus(m, raw=raw, leer=_leer(zb), total=len(zb))
    assert "copia validada" in r1
    assert m["fracfocus_disclosure_list"]["sha256"] == hashlib.sha256(csv_bytes).hexdigest()
    assert ingest.asegurar_fracfocus(m, raw=raw, leer=_leer(zb), total=len(zb)) == "sin cambios"
    (raw / ingest.RUTA_FRACFOCUS).write_bytes(b"corrupto")      # una copia distinta se baja de nuevo por rangos
    r3 = ingest.asegurar_fracfocus(m, raw=raw, leer=_leer(zb), total=len(zb))
    assert "descarga por rango" in r3 and (raw / ingest.RUTA_FRACFOCUS).read_bytes() == csv_bytes
    assert m["fracfocus_disclosure_list"]["crc32"] == f"{zlib.crc32(csv_bytes) & 0xFFFFFFFF:08x}"


def test_manifiesto_ida_y_vuelta(tmp_path):
    p = tmp_path / "m" / "manifest.json"
    ingest.guardar_manifiesto({"a": {"sha256": "x", "bytes": 1}}, p)
    assert ingest.cargar_manifiesto(p) == {"a": {"sha256": "x", "bytes": 1}}
    assert ingest.cargar_manifiesto(tmp_path / "no.json") == {}


def test_las_urls_de_las_fuentes():
    assert ingest.URL_PRODUCCION.format(anio=2021) == "https://ecmc.state.co.us/documents/data/downloads/production/2021_prod_reports.zip"
    assert ingest.URL_POZOS.endswith("/gis/WELLS_SHP.ZIP")
    assert ingest.URL_FRACFOCUS_ZIP.endswith("/FracFocusCSV.zip") and ingest.MIEMBRO_FRACFOCUS == "DisclosureList_1.csv"
    assert R.ANIOS_PRODUCCION == tuple(range(2018, 2025))


# ---------------------------------------------------------------- red (omitidas por defecto)

@pytest.mark.skipif(not os.environ.get("VM_RED"), reason="necesita la red: VM_RED=1")
def test_fuentes_responden_y_fracfocus_atiende_rangos():
    assert ingest.tamano_remoto(ingest.URL_PRODUCCION.format(anio=2024)) > 5_000_000
    total = ingest.tamano_remoto(ingest.URL_FRACFOCUS_ZIP)
    e = ingest.entrada(ingest.leer_rango_http(ingest.URL_FRACFOCUS_ZIP), total, ingest.MIEMBRO_FRACFOCUS)
    assert e["tamano"] > 10_000_000
