"""Data contract and invariants of pipeline/base_mapa.py and data/base_mapa.json."""
import base64
import hashlib
import json
import struct
import zipfile

import numpy as np
import pytest

from pipeline import base_mapa
from pipeline.ingest import DATA, ROOT

RAW = DATA / "raw" / "base_mapa"
PRODUCTO = DATA / "base_mapa.json"
TIPOS_AGUA = {"embalse", "lago", "rio"}
CAMPOS_FUENTE = {"capa", "titulo", "organismo", "url", "licencia", "sha256", "fecha"}

needs_raw = pytest.mark.skipif(not RAW.exists(), reason="raw base_mapa not present")


def leer_producto():
    texto = PRODUCTO.read_text(encoding="utf-8")
    return texto, json.loads(texto)


# ---- simplificar ----

def test_simplificar_colineales():
    assert base_mapa.simplificar([(0, 0), (5, 0), (10, 0)], 60) == [(0, 0), (10, 0)]
    assert base_mapa.simplificar([(0, 0), (10, 0)], 60) == [(0, 0), (10, 0)]


def test_simplificar_zigzag_tolerancia():
    zig = [(0, 0), (5, 10), (10, 0)]  # middle point is 50 m off the chord
    assert base_mapa.simplificar(zig, 40) == zig
    assert base_mapa.simplificar(zig, 60) == [(0, 0), (10, 0)]


def test_simplificar_reversed():
    zig = [(0, 0), (5, 10), (10, 0)]
    assert base_mapa.simplificar(list(reversed(zig)), 40) == list(reversed(base_mapa.simplificar(zig, 40)))


# ---- unir ----

def test_unir_fusiona_invertido():
    assert base_mapa.unir([[(0, 0), (1, 1)], [(2, 2), (1, 1)]]) == [[(0, 0), (1, 1), (2, 2)]]


def test_unir_separados():
    lineas = [[(0, 0), (1, 1)], [(5, 5), (6, 6)]]
    assert base_mapa.unir(lineas) == lineas


# ---- codif, qpt ----

def test_codif_decodificar_roundtrip():
    pts = [(0, 0), (65535, 65535), (1, 2), (300, 40000)]
    assert base_mapa.decodificar_linea(base_mapa.codif(pts)) == pts


def test_qpt_esquinas():
    lon0, lat0, lon1, lat1 = base_mapa.CAJA
    assert base_mapa.qpt(lon0, lat1) == (0, 0)  # north west
    assert base_mapa.qpt(lon1, lat0) == (65535, 65535)  # south east


# ---- relief ----

def test_media_bloques_redondeo():
    rec = np.array([[1, 2, 0, 0], [3, 4, 0, 0], [0, 0, 5, 5], [0, 0, 5, 6]], dtype=np.int64)
    assert base_mapa.media_bloques(rec, 2, 2, 2, 2).tolist() == [[3, 0], [0, 5]]  # 2.5 rounds up


def test_media_bloques_sin_vacios():
    rec = np.array([[10, -5000], [-1000, 20]], dtype=np.int64)  # voids are at most -1000
    assert base_mapa.media_bloques(rec, 1, 1, 2, 2).tolist() == [[15]]


def test_relieve_escape_roundtrip():
    z = np.array([[100, 100, 50000, 49872, 49872], [50000, 49900, 49900, 10, 10]], dtype=np.int64)
    codificado = base_mapa.codificar_relieve(z)
    assert 128 in codificado  # the +49900 jump and the -128 delta need the escape byte
    rel = {"cols": 5, "filas": 2, "d": base64.b64encode(codificado).decode("ascii")}
    assert (base_mapa.decodificar_relieve(rel) == z).all()


# ---- cota ----

Z = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
CAJA = (0.0, 0.0, 4.0, 3.0)


def test_cota_centro():
    assert base_mapa.cota(Z, CAJA, 1.5, 1.5) == 6.0


def test_cota_esquina_media():
    assert base_mapa.cota(Z, CAJA, 2.0, 1.0) == pytest.approx((6 + 7 + 10 + 11) / 4)


def test_cota_fuera_none():
    assert base_mapa.cota(Z, CAJA, -0.1, 1.5) is None
    assert base_mapa.cota(Z, CAJA, 4.1, 1.5) is None
    assert base_mapa.cota(Z, CAJA, 1.5, -0.1) is None
    assert base_mapa.cota(Z, CAJA, 1.5, 3.1) is None


def test_cota_borde():
    assert base_mapa.cota(Z, CAJA, 4.0, 1.5) == 8.0  # clamped to the east edge column


# ---- canonical hash ----

def test_hash_canonico_orden():
    f1 = {"id": 1, "geometry": {"type": "Point", "coordinates": [1, 2]}, "properties": {"b": 2, "a": 1}}
    f2 = {"id": 2, "geometry": {"type": "Point", "coordinates": [3, 4]}, "properties": {"a": 1}}
    f1b = {"properties": {"a": 1, "b": 2}, "id": 1, "geometry": {"coordinates": [1, 2], "type": "Point"}}
    assert base_mapa.hash_canonico([f1, f2]) == base_mapa.hash_canonico([f2, f1b])


# ---- SHP/DBF reader ----

def _zip_bloque_minimo(ruta):
    campos = [("NOMBRE_DE_", "  Área   Test ", 40), ("CODIGO_DE_", "TT-01", 10), ("EMPRESA_OP", "Operadora Ñandú", 40)]
    n, hl = 1, 32 + 32 * len(campos) + 1
    rl = 1 + sum(lar for _, _, lar in campos)
    cab = bytearray(hl)
    struct.pack_into("<IHH", cab, 4, n, hl, rl)
    o = 32
    for nom, _, lar in campos:
        cab[o:o + len(nom)] = nom.encode("ascii")
        cab[o + 16] = lar
        o += 32
    cab[o] = 0x0D
    rec = bytearray(rl)
    rec[0] = 0x20
    p = 1
    for _, valor, lar in campos:
        rec[p:p + lar] = valor.encode("utf-8")[:lar].ljust(lar)
        p += lar
    anillo = (-69.9, -38.0, -69.8, -38.0, -69.8, -37.9, -69.9, -37.9, -69.9, -38.0)
    cont = (struct.pack("<i", 5) + struct.pack("<4d", -69.9, -38.0, -69.8, -37.9)
            + struct.pack("<ii", 1, 5) + struct.pack("<i", 0) + struct.pack("<10d", *anillo))
    shp = bytes(100) + struct.pack(">ii", 1, len(cont) // 2) + cont
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("t.shp", shp)
        z.writestr("t.dbf", bytes(cab) + bytes(rec))


def test_bloques_zip_minimo(tmp_path):
    ruta = tmp_path / "t.zip"
    _zip_bloque_minimo(ruta)
    (bloque,) = base_mapa.construir_bloques(ruta.read_bytes())
    assert bloque["n"] == "Área Test"
    assert bloque["c"] == "TT-01"
    assert bloque["op"] == "Operadora Ñandú"
    assert bloque["km2"] > 0
    (anillo,) = [base_mapa.decodificar_linea(s) for s in bloque["p"]]
    assert len(anillo) >= 4 and anillo[0] == anillo[-1]


# ---- pins ----

def test_pin_cambiado(tmp_path):
    (tmp_path / "ign").mkdir()
    features = [{"id": 1, "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {"fna": "X"}}]
    (tmp_path / "ign" / "localidad_bahra.geojson").write_text(json.dumps({"features": features}))
    with pytest.raises(base_mapa.FuenteCambiada) as exc:
        base_mapa.capa_ign("localidad_bahra", raw=tmp_path)
    assert "localidad_bahra" in str(exc.value)
    assert base_mapa.PINES["localidad_bahra"] in str(exc.value)
    assert base_mapa.hash_canonico(features) in str(exc.value)


def test_archivo_faltante(tmp_path):
    with pytest.raises(FileNotFoundError, match="--descargar"):
        base_mapa.capa_ign("localidad_bahra", raw=tmp_path)
    with pytest.raises(FileNotFoundError, match="--descargar"):
        base_mapa.construir(raw=tmp_path)


# ---- committed product ----

def test_producto_encabezado():
    _, base = leer_producto()
    assert base["v"] == 1
    assert base["caja"] == list(base_mapa.CAJA)
    assert base["q"] == 65535


def test_producto_relieve():
    _, base = leer_producto()
    rel = base["relieve"]
    z = base_mapa.decodificar_relieve(rel)
    assert z.shape == (base_mapa.FILAS, base_mapa.COLS)
    assert int(z.min()) == rel["min"]
    assert int(z.max()) == rel["max"]


def test_producto_vectores():
    _, base = leer_producto()
    for rio in base["rios"]:
        assert rio["km"] >= 60
        for s in rio["l"]:
            assert len(base_mapa.decodificar_linea(s)) >= 2
    for cuerpo in base["agua"]:
        assert cuerpo["t"] in TIPOS_AGUA
        for s in cuerpo["p"]:
            assert len(base_mapa.decodificar_linea(s)) >= 4
    for limite in base["limites"]:
        for s in limite["l"]:
            assert len(base_mapa.decodificar_linea(s)) >= 2
    for bloque in base["bloques"]:
        for s in bloque["p"]:
            assert len(base_mapa.decodificar_linea(s)) >= 4


def test_producto_orden():
    _, base = leer_producto()
    indices = [base_mapa.LOCALIDADES.index(d["n"]) for d in base["localidades"]]
    assert indices == sorted(indices)
    claves = [(d["n"], d["c"]) for d in base["bloques"]]
    assert claves == sorted(claves)


def test_producto_fuentes_serializar():
    texto, base = leer_producto()
    assert len(texto.encode("utf-8")) < 700 * 1024
    assert base_mapa.serializar(json.loads(texto)) == texto
    assert len(base["fuentes"]) == 8
    lineas = "".join(f"{t}:{base_mapa.PINES[t]}\n" for t in base_mapa.TILES)
    pines = {("relieve", base["fuentes"][0]["titulo"]): hashlib.sha256(lineas.encode()).hexdigest(),
             ("rios", "Corriente de agua perenne"): base_mapa.PINES["lineas_de_aguas_continentales_perenne"],
             ("agua", "Embalse"): base_mapa.PINES["areas_de_aguas_continentales_BH130"],
             ("agua", "Espejo de agua perenne"): base_mapa.PINES["areas_de_aguas_continentales_perenne"],
             ("agua", "Corriente de agua (áreas)"): base_mapa.PINES["areas_de_aguas_continentales_BH140"],
             ("limites", "Límite interprovincial"): base_mapa.PINES["linea_de_limite_070111"],
             ("localidades", "Localidad (BAHRA)"): base_mapa.PINES["localidad_bahra"],
             ("bloques", "Producción de hidrocarburos: concesiones de explotación"):
                 base_mapa.PINES[base_mapa.ZIP_NOMBRE]}
    for fuente in base["fuentes"]:
        assert set(fuente) == CAMPOS_FUENTE
        assert fuente["sha256"] == pines[(fuente["capa"], fuente["titulo"])]


def test_sin_rayas():
    texto = (ROOT / "pipeline" / "base_mapa.py").read_text(encoding="utf-8")
    assert chr(0x2013) not in texto
    assert chr(0x2014) not in texto


# ---- sources page ----

def test_recuentos_a_mano():
    base = {"relieve": {"cols": 3, "filas": 2, "min": 5, "max": 9}, "rios": [{}, {}],
            "agua": [{"n": "A", "t": "embalse", "p": ["x"]}, {"n": "B", "t": "lago", "p": ["x", "y"]},
                     {"n": "C", "t": "rio", "p": ["x"]}, {"n": "D", "t": "rio", "p": ["x"]},
                     {"n": "", "t": "lago", "p": ["x", "y", "z"]}, {"n": "", "t": "rio", "p": ["x"]}],
            "limites": [{}], "localidades": [{}, {}, {}], "bloques": [{"op": "X"}, {"op": "Y"}, {"op": "X"}]}
    assert base_mapa.recuentos(base) == {
        "cols": 3, "filas": 2, "cota_min": 5, "cota_max": 9, "rios": 2, "agua_con_nombre": 4, "embalses": 1,
        "lagos": 1, "cauces": 2, "agua_sin_nombre": 4, "limites": 1, "localidades": 3, "bloques": 3, "operadoras": 2}


def test_pagina_es_la_del_repo():
    _, base = leer_producto()
    assert base_mapa.pagina(base) == base_mapa.PAGINA.read_text(encoding="utf-8")


def test_pagina_nombra_cada_fuente_con_licencia_y_huella():
    """No source, no layer: every layer of the product has a source, and the page prints its licence and hash."""
    _, base = leer_producto()
    texto = base_mapa.pagina(base)
    assert chr(0x2013) not in texto and chr(0x2014) not in texto
    assert {f["capa"] for f in base["fuentes"]} == set(base_mapa.CAPA_ES)
    assert all(base[capa] for capa in base_mapa.CAPA_ES)
    filas = [linea for linea in texto.splitlines() if linea.startswith("| ")]
    for fuente in base["fuentes"]:
        (fila,) = [linea for linea in filas if f"| {fuente['titulo']} |" in linea]
        assert fila.startswith(f"| {base_mapa.CAPA_ES[fuente['capa']]} |")
        assert fuente["organismo"] in fila and fuente["licencia"] in fila
        assert fila.endswith("| " + "/".join(reversed(fuente["fecha"].split("-"))) + " |")
        assert f"`{fuente['url']}`, sha256 `{fuente['sha256']}`." in texto


def test_main_pagina_verificar_y_salida(tmp_path, monkeypatch, capsys):
    """The command line without the raw files: the page from the product, a check that never writes, --salida."""
    _, base = leer_producto()
    destino, hoja = tmp_path / "base_mapa.json", tmp_path / "mapa_base.md"
    destino.write_bytes(PRODUCTO.read_bytes())
    monkeypatch.setattr(base_mapa, "DESTINO", destino)
    monkeypatch.setattr(base_mapa, "PAGINA", hoja)
    monkeypatch.setattr(base_mapa, "ROOT", tmp_path)
    monkeypatch.setattr(base_mapa, "construir", lambda: base)
    assert base_mapa.main(["--pagina"]) == 0
    assert hoja.read_text(encoding="utf-8") == base_mapa.pagina(base)
    capsys.readouterr()
    assert base_mapa.main(["--verificar"]) == 0
    assert capsys.readouterr().out.startswith("verificar ok bytes " + str(PRODUCTO.stat().st_size) + " sha256 ")
    hoja.write_text("otra\n", encoding="utf-8")
    assert base_mapa.main(["--verificar"]) == 1
    assert "verificar difieren (mapa_base.md)" in capsys.readouterr().out
    assert hoja.read_text(encoding="utf-8") == "otra\n"
    otra = tmp_path / "otra.json"
    assert base_mapa.main(["--salida", str(otra)]) == 0
    assert otra.read_bytes() == PRODUCTO.read_bytes() and hoja.read_text(encoding="utf-8") == "otra\n"
    destino.unlink()
    assert base_mapa.main([]) == 0
    assert destino.read_bytes() == PRODUCTO.read_bytes() and hoja.read_text(encoding="utf-8") == base_mapa.pagina(base)


@needs_raw
def test_construir_reproduce_referencia():
    assert base_mapa.serializar(base_mapa.construir()).encode("utf-8") == PRODUCTO.read_bytes()
