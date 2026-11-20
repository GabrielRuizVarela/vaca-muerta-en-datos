"""Tests of the Sentinel-2 ground photo builder: projection, COG reader, feather, composition, product."""

import json
import struct
import zlib

import numpy as np
import pytest

from pipeline import base_foto as bf
from pipeline.base_mapa import CAJA
from pipeline.ingest import DATA


# a. projection against PROJ 9.8.1 reference values -------------------------------------------------

@pytest.mark.parametrize("lon, lat, e, n", [
    (-69.0, -38.5, 500000.000, 5738706.573),
    (-70.5, -36.6, 365835.573, 5948452.200),
    (-67.5, -39.6, 628786.303, 5615562.623),
    (-68.79, -38.35, 518349.476, 5755329.728),
    (-69.25, -38.1, 478080.490, 5783060.170),
    (-68.25, -38.85, 565081.115, 5699601.660),
])
def test_utm19s_matches_proj(lon, lat, e, n):
    """The Krueger series agrees with PROJ within 1 cm."""
    ee, nn = bf.utm19s(lon, lat)
    assert abs(float(ee) - e) < 0.01
    assert abs(float(nn) - n) < 0.01


# b. TIFF reader on a synthetic file ----------------------------------------------------------------

def _tiff(niveles, th, tw, e0=300000.0, n0=5900000.0):
    """Little-endian classic TIFF with one IFD per level, deflate + predictor 2, padded edge tiles."""
    comprimidos = []
    for img in niveles:
        h, w, _ = img.shape
        nty, ntx = -(-h // th), -(-w // tw)
        nivel = []
        for ty in range(nty):
            for tx in range(ntx):
                t = np.zeros((th, tw, 3), dtype=np.uint8)
                trozo = img[ty * th:(ty + 1) * th, tx * tw:(tx + 1) * tw]
                t[:trozo.shape[0], :trozo.shape[1]] = trozo
                dif = t.copy()
                dif[:, 1:] = t[:, 1:] - t[:, :-1]  # horizontal differencing, wraps mod 256
                nivel.append(zlib.compress(dif.tobytes()))
        comprimidos.append(nivel)
    # layout: header, then per level IFD + offsets array + counts array (+ geo doubles), then tile data
    pos, plan = 8, []
    for k, nivel in enumerate(comprimidos):
        nent = 14 if k == 0 else 11
        p = {"ifd": pos}
        pos += 2 + 12 * nent + 4
        p["offs"], pos = pos, pos + 4 * len(nivel)
        p["cnts"], pos = pos, pos + 4 * len(nivel)
        if k == 0:
            p["escala"], pos = pos, pos + 24
            p["tiepoint"], pos = pos, pos + 48
        plan.append(p)
    offsets = []
    for nivel in comprimidos:
        lista = []
        for c in nivel:
            lista.append(pos)
            pos += len(c)
        offsets.append(lista)
    corto = lambda tag, v: struct.pack("<HHIH2x", tag, 3, 1, v)  # noqa: E731
    largo = lambda tag, v: struct.pack("<HHII", tag, 4, 1, v)  # noqa: E731
    matriz = lambda tag, tipo, n, off: struct.pack("<HHII", tag, tipo, n, off)  # noqa: E731
    cuerpo = bytearray(b"II" + struct.pack("<HI", 42, plan[0]["ifd"]))
    for k, img in enumerate(niveles):
        h, w, _ = img.shape
        p, nt = plan[k], len(comprimidos[k])
        ents = [largo(256, w), largo(257, h), corto(259, 8), corto(262, 2), corto(277, 3), corto(284, 1),
                corto(317, 2), largo(322, tw), largo(323, th), matriz(324, 4, nt, p["offs"]),
                matriz(325, 4, nt, p["cnts"])]
        if k == 0:
            ents += [matriz(33550, 12, 3, p["escala"]), matriz(33922, 12, 6, p["tiepoint"]),
                     corto(254, 0)]
        ents.sort(key=lambda b: struct.unpack_from("<H", b)[0])
        sig = plan[k + 1]["ifd"] if k + 1 < len(niveles) else 0
        cuerpo += struct.pack("<H", len(ents)) + b"".join(ents) + struct.pack("<I", sig)
        cuerpo += struct.pack(f"<{nt}I", *offsets[k]) + struct.pack(f"<{nt}I", *map(len, comprimidos[k]))
        if k == 0:
            cuerpo += struct.pack("<3d", 10.0, 10.0, 0.0) + struct.pack("<6d", 0, 0, 0, e0, n0, 0)
    for nivel in comprimidos:
        for c in nivel:
            cuerpo += c
    return bytes(cuerpo)


def test_tiff_reader_roundtrip():
    """The reader returns the original arrays for both levels and for a sub-window, via injected ranges."""
    rng = np.random.default_rng(1)
    n0 = rng.integers(0, 256, (24, 40, 3), dtype=np.uint8)  # 40 x 24 with 16 px tiles: padded edges
    n1 = rng.integers(0, 256, (12, 20, 3), dtype=np.uint8)
    datos = _tiff([n0, n1], 16, 16)
    pedidos = []

    def leer(off, n):
        pedidos.append((off, n))
        return datos[off:off + n]

    _, ifds = bf.cabecera(leer)
    assert [(i["ancho"], i["alto"]) for i in ifds] == [(40, 24), (20, 12)]
    assert list(ifds[0]["tiepoint"][3:5]) == [300000.0, 5900000.0]
    assert list(ifds[0]["escala"][:2]) == [10.0, 10.0]
    assert ifds[1]["tiepoint"] is None
    assert np.array_equal(bf.leer_ventana(ifds[0], leer, 0, 0, 40, 24), n0)
    assert np.array_equal(bf.leer_ventana(ifds[1], leer, 0, 0, 20, 12), n1)
    assert np.array_equal(bf.leer_ventana(ifds[0], leer, 5, 3, 33, 20), n0[3:20, 5:33])
    assert pedidos[0] == (0, bf.CABECERA)


def test_tiff_header_grows_when_arrays_lie_beyond():
    """If an offset array is past the first read, the head is fetched again, larger."""
    img = np.arange(24 * 40 * 3, dtype=np.uint8).reshape(24, 40, 3)
    datos = _tiff([img, img[::2, ::2]], 16, 16)
    _, ifds = bf.cabecera(lambda off, n: datos[off:off + n], tam=100)
    assert len(ifds) == 2


# c. feather weights --------------------------------------------------------------------------------

def test_pesos_feather():
    """1 well inside, 0 on nodata, and non-decreasing between 0 and 1 walking inward from the edge."""
    rgb = np.zeros((30, 60, 3), dtype=np.uint8)
    rgb[:, 20:] = (90, 120, 60)  # nodata on the left third
    radio = 6
    w = bf.pesos(rgb, radio)
    assert np.all(w[:, :20] == 0)
    assert np.allclose(w[10:20, 20 + radio + 1:60 - radio - 1], 1.0)
    fila = w[15, 20:20 + radio + 2]
    assert np.all(np.diff(fila) >= 0)
    assert 0 <= fila[0] < 0.2
    assert np.all((fila >= 0) & (fila <= 1))
    assert fila[1:radio].min() > 0 and fila[radio] == pytest.approx(1.0)


# d. composition ------------------------------------------------------------------------------------

def test_componer_no_dark_fringe():
    """Primary with a nodata half, fill everywhere: primary inside, fill in the gap, no dark seam."""
    alto, ancho, radio = 40, 80, 5
    c0, c1 = np.array([200, 100, 50]), np.array([20, 150, 220])
    p0 = np.zeros((alto, ancho, 3), dtype=np.uint8)
    p0[:, 40:] = c0
    p1 = np.empty((alto, ancho, 3), dtype=np.uint8)
    p1[:] = c1
    # sample the interior only: the window border is nodata by design (padding keeps real data away from it)
    yy, xx = np.mgrid[8:alto - 8, 8:ancho - 8]
    idx = np.arange(yy.size)
    num = np.zeros((2, yy.size, 3), dtype=np.float32)
    den = np.zeros((2, yy.size), dtype=np.float32)
    for capa, img in enumerate((p0, p1)):
        bf.acumular(num[capa], den[capa], idx, xx.ravel().astype(float), yy.ravel().astype(float),
                    img, bf.pesos(img, radio))
    rgb, sin_dato = bf.componer(num[0], den[0], num[1], den[1])
    rgb = rgb.reshape(yy.shape + (3,)).astype(int)
    assert sin_dato == 0
    assert np.abs(rgb[:, 50 - 8:70 - 8] - c0).max() <= 1
    assert np.abs(rgb[:, :30 - 8] - c1).max() <= 1
    lo, hi = np.minimum(c0, c1), np.maximum(c0, c1)
    franja = rgb[:, 25 - 8:55 - 8]
    assert np.all(franja >= lo - 1) and np.all(franja <= hi + 1)


def test_componer_counts_uncovered():
    """Pixels with no data in either capa stay black and are counted."""
    num = np.zeros((4, 3), dtype=np.float32)
    den = np.zeros(4, dtype=np.float32)
    rgb, sin_dato = bf.componer(num, den, num, den)
    assert sin_dato == 4 and not rgb.any()


# e. WebP header ------------------------------------------------------------------------------------

def test_tam_webp_header():
    """Width and height come from the lossy VP8 frame header, low 14 bits."""
    cab = (b"RIFF" + struct.pack("<I", 100) + b"WEBP" + b"VP8 " + struct.pack("<I", 80)
           + b"\x10\x02\x00" + b"\x9d\x01\x2a" + struct.pack("<HH", 3072 | 0x4000, 2304))
    assert bf.tam_webp(cab + b"\0" * 20) == (3072, 2304)
    with pytest.raises(ValueError):
        bf.tam_webp(b"RIFF" + b"\0" * 40)


def test_url_escena():
    """The COG URL has the tile split, unpadded month and scene id."""
    assert bf.url_escena("S2A_19HDT_20251229_0_L2A") == (
        "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/"
        "19/H/DT/2025/12/S2A_19HDT_20251229_0_L2A/TCI.tif")


# f. the committed product --------------------------------------------------------------------------

def test_committed_product():
    """data/base_foto.json agrees with the committed WebP files."""
    ruta = DATA / "base_foto.json"
    if not ruta.exists():
        pytest.skip("data/base_foto.json not built")
    obj = json.loads(ruta.read_text(encoding="utf-8"))
    assert len(obj["escenas"]) == 20
    assert [e["id"] for e in obj["escenas"]] == [e[0] for e in bf.ESCENAS]
    assert obj["caja"] == list(CAJA) and obj["nucleo"] == list(bf.NUCLEO)
    assert obj["atribucion"] == "Contains modified Copernicus Sentinel data 2025"
    for nombre in ("caja", "nucleo"):
        im = obj["imagenes"][nombre]
        datos = (DATA / im["archivo"]).read_bytes()
        assert len(datos) == im["bytes"]
        assert bf._sha(datos) == im["sha256"]
        assert bf.tam_webp(datos) == (im["ancho"], im["alto"]) == bf.TAM[nombre]
        assert im["sin_dato"] == 0
    assert bf.verificar() == 0


# g. the wiki section ------------------------------------------------------------------------------

def _manifiesto_mini():
    """A manifest with three scenes on two days, in the contract of base_foto.json."""
    return {"v": 1, "caja": [-70.5, -39.6, -67.5, -36.6], "nucleo": [-69.25, -38.85, -68.25, -38.1],
            "imagenes": {"caja": {"archivo": "base_foto_caja.webp", "ancho": 3072, "alto": 3072, "bytes": 1234567,
                                  "sha256": "aa" * 32},
                         "nucleo": {"archivo": "base_foto_nucleo.webp", "ancho": 3072, "alto": 2304, "bytes": 890,
                                    "sha256": "bb" * 32}},
            "escenas": [{"id": "a", "capa": 0}, {"id": "b", "capa": 0}, {"id": "c", "capa": 1}],
            "desde": "2025-12-29", "hasta": "2025-12-30", "atribucion": bf.ATRIBUCION,
            "url_licencia": bf.URL_LICENCIA, "catalogo": bf.CATALOGO, "fecha_descarga": "2026-11-19"}


def test_recuentos_of_a_hand_made_manifest():
    """Scene counts by orbit, the pixel size of each image and the ground size of a pixel at the box's latitude."""
    assert bf.recuentos(_manifiesto_mini()) == {
        "escenas": 3, "principal": 2, "relleno": 1,
        "caja_ancho": 3072, "caja_alto": 3072, "caja_bytes": 1234567, "caja_m_este": 86, "caja_m_sur": 109,
        "nucleo_ancho": 3072, "nucleo_alto": 2304, "nucleo_bytes": 890, "nucleo_m_este": 28, "nucleo_m_sur": 36}


def test_wiki_section_states_source_dates_licence_and_hashes():
    obj = _manifiesto_mini()
    texto = "\n".join(bf.seccion(obj))
    assert texto.startswith("## Imagen del suelo\n") and texto.endswith("\n")
    assert chr(0x2013) not in texto and chr(0x2014) not in texto
    for frase in ("La imagen es contexto: muestra el lugar en una fecha, no mide nada",
                  "Es un mosaico de 3 escenas tomadas el 29/12/2025 y el 30/12/2025: 2 de la órbita principal y 1 de",
                  "La hoja entera mide 3.072 por 3.072 píxeles", "de 69,25° a 68,25° de longitud oeste",
                  f'con esta atribución: "{bf.ATRIBUCION}"', f"(`{bf.URL_LICENCIA}`)", "Bajado el 19/11/2026.",
                  "- `data/base_foto_caja.webp`: 1.234.567 bytes, sha256 `" + "aa" * 32 + "`.",
                  "- `data/base_foto_nucleo.webp`: 890 bytes, sha256 `" + "bb" * 32 + "`."):
        assert frase in texto, frase
    un_dia = "\n".join(bf.seccion(dict(obj, hasta="2025-12-29")))
    assert "escenas tomadas el 29/12/2025: 2 de la órbita principal" in un_dia


def test_manifest_dates_follow_the_pinned_scenes():
    """The dates the page prints are those of the scene list, and the committed manifest says the same."""
    dias = sorted(fecha[:10] for _, fecha, _ in bf.ESCENAS)
    assert (dias[0], dias[-1]) == ("2025-12-29", "2025-12-30")
    assert all(eid.split("_")[2] == fecha[:10].replace("-", "") for eid, fecha, _ in bf.ESCENAS)
    ruta = DATA / "base_foto.json"
    if not ruta.exists():
        pytest.skip("data/base_foto.json not built")
    obj = json.loads(ruta.read_text(encoding="utf-8"))
    assert (obj["desde"], obj["hasta"], obj["fecha_descarga"]) == (dias[0], dias[-1], bf.FECHA_DESCARGA)
    assert [e["fecha"] for e in obj["escenas"]] == [fecha for _, fecha, _ in bf.ESCENAS]
