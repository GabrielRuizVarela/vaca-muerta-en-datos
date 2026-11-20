"""Pinned, deterministic exporter of the base map for the WebGL page.

  python -m pipeline.base_mapa              # build data/base_mapa.json from data/raw/base_mapa
  python -m pipeline.base_mapa --descargar  # fetch the missing sources first, then build
  python -m pipeline.base_mapa --verificar  # compare an in-memory build with data/base_mapa.json and the wiki page
  python -m pipeline.base_mapa --salida OUT # write the product to OUT instead (the wiki page is left alone)
  python -m pipeline.base_mapa --pagina     # rewrite only the wiki page from data/base_mapa.json (needs no raw file)

Reads the raw sources under data/raw/base_mapa (Skadi relief tiles, IGN
GeoJSON layers, the Energia exploitation-blocks zip) and writes the single
JSON product data/base_mapa.json: relief, rivers, water bodies, province
borders, towns and concession blocks, all quantised over one shared box so
a WebGL page can draw them without reprojection. Every source is pinned by
hash (PINES): a changed source raises FuenteCambiada, a missing one raises
FileNotFoundError. The build is deterministic, the same sources always
produce the same bytes.

Data contract v1: {v:1, caja:[lon0,lat0,lon1,lat1], q:65535,
relieve:{cols, filas, min, max, d}, rios:[{n, km, l:[b64...]}],
agua:[{n, t:"embalse|lago|rio", km2, p:[b64 rings]}],
limites:[{n, l:[...]}], localidades:[{n, prov, lon, lat}],
bloques:[{n, c, op, km2, p:[...]}],
fuentes:[{capa, titulo, organismo, url, licencia, sha256, fecha}]}.
A second product, data/base_relieve_nucleo.json, is the finer relief of the
core: {v:1, caja, paso_seg, margen, cols, filas, min, max, d}, same codec.
Vectors are base64 of little-endian Uint16 (x, y) pairs quantised over the
box (x east from lon0, y south from lat1). Relief d is base64 of rows
(row 0 is north): an absolute Uint16 LE, then one Int8 delta per column,
where byte 128 is an escape followed by an absolute Uint16 LE. Each relief
cell is the rounded integer mean of 20 x 16 one-arc-second samples, voids
(values of -1000 or less) excluded. Serialisation:
json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
+ "\n", UTF-8.

Selection rules: rivers keep every full name whose joined length is 60 km
or more (simplified segments below 1 km are dropped); water polygons are
all kept except perennial lakes below 1 km2; towns are this fixed list of
20 names, in label priority order: Añelo, Neuquén, Rincón de los Sauces,
Cutral Có, Plaza Huincul, Zapala, San Patricio del Chañar, Chos Malal,
Catriel, Buta Ranquil, Cipolletti, General Roca, Villa El Chocón,
Picún Leufú, 25 de Mayo, Centenario, Plottier, Barrancas, Las Lajas,
Senillosa (LOCALIDADES), filtered by BAHRA
settlement type; blocks are the exploitation concessions whose bounding
box touches the box. This module is not a step of pipeline.run_all: the
product data/base_mapa.json is committed and pipeline.mundo embeds it.

The same run writes wiki/hallazgos/mapa_base.md (pagina): what the sheet
covers, the source, licence, download date and hash of every layer, how
each layer is built and what the map is not. pipeline.claims pins its
counts (recuentos) against data/base_mapa.json.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import math
import struct
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

from pipeline.ingest import DATA, ROOT

RAW = DATA / "raw" / "base_mapa"
DESTINO = DATA / "base_mapa.json"
PAGINA = ROOT / "wiki" / "hallazgos" / "mapa_base.md"
FOTO = DATA / "base_foto.json"  # the ground imagery of pipeline.base_foto: the page has a section about it
FINO = DATA / "base_relieve_nucleo.json"
EXACTITUD = DATA / "exactitud.json"  # the finer relief of the core, the second product of this module
CAJA = (-70.5, -39.6, -67.5, -36.6)  # lon0, lat0, lon1, lat1
COLS, FILAS = 540, 675  # blocks of 20 x 16 one-arc-second samples
# The finer relief covers the core (the box of the fine ground image) in blocks of PASO_FINO arc-seconds.
# MARGEN_FINO is the share of that box, from its edge inwards, over which a reader blends it into the sheet grid.
NUCLEO = (-69.25, -38.85, -68.25, -38.1)
PASO_FINO = 4
MARGEN_FINO = 0.04
Q = 65535
MX, MY = 4, 5  # approximate metres per quantisation unit in x and y
RIO_MIN_KM = 60.0
LAGO_MIN_KM2 = 1.0
TOL_RIO = 60  # Douglas-Peucker tolerances, in approximate metres
TOL_AGUA = 40
TOL_LIMITE = 100
TOL_BLOQUE = 15
TRAMO_MIN_KM = 1.0  # simplified river segments below this are dropped
LOCALIDADES = ["Añelo", "Neuquén", "Rincón de los Sauces", "Cutral Có", "Plaza Huincul", "Zapala",
               "San Patricio del Chañar", "Chos Malal", "Catriel", "Buta Ranquil", "Cipolletti",
               "General Roca", "Villa El Chocón", "Picún Leufú", "25 de Mayo", "Centenario", "Plottier",
               "Barrancas", "Las Lajas", "Senillosa"]
IGN = "https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:"
LIC_IGN = "uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional"
LIC_SRTM = "dominio público; datos SRTM cortesía del U.S. Geological Survey"
LIC_BLOQUES = "CC-BY-4.0"
SHP = "http://datos.energia.gob.ar/dataset/81cfad0a-4162-4f85-ad71-837f5a5fae57/resource/48a306a3-d5da-4f28-8ab5-7f80767ffdec/download/produccin-hidrocarburos-concesiones-de-explotacin.zip"
SKADI = "https://s3.amazonaws.com/elevation-tiles-prod/skadi/{d}/{d}{w}.hgt.gz"
FECHA_DESCARGA = "2026-11-19"
TILES = tuple(f"S{la}W{lo:03d}" for la in (37, 38, 39, 40) for lo in (71, 70, 69, 68))
CAPAS_IGN = ("areas_de_aguas_continentales_BH130", "areas_de_aguas_continentales_BH140",
             "areas_de_aguas_continentales_perenne", "linea_de_limite_070111",
             "lineas_de_aguas_continentales_perenne", "localidad_bahra")
ORDEN_AGUA = (("areas_de_aguas_continentales_BH130", "embalse", 0.0),
              ("areas_de_aguas_continentales_perenne", "lago", LAGO_MIN_KM2),
              ("areas_de_aguas_continentales_BH140", "rio", 0.0))
ZIP_NOMBRE = "concesiones_explotacion.zip"
# Expected hash of every source: file bytes for the tiles and the zip,
# canonical hash (see hash_canonico) for the IGN layers.
PINES = {
    "S37W071": "f0ce9d88121769aa41042a22d7ada50e6afe2b19d917ba3252abff163a8e7b08",
    "S37W070": "2e3e2eadbf8b64de16565127639019ddcc62c43767a0e819cb3e614ef7746807",
    "S37W069": "39fc2b97771800a66709526507b576b8927ae57dafdcb47fedb20d08c1cdea41",
    "S37W068": "2213d1603bff61568855f89b9506c14e79ba56bf9032f2714eb8c1e410d1c81c",
    "S38W071": "b681b70acc8c974bca123b6388516e09ad3c4bb0d36636c42960425b653e6ed6",
    "S38W070": "bac941c2f6bceff5274da735ae05f389d79998a76f0046de35a5123377cfc699",
    "S38W069": "54ad03e95d4486ce053dfe6c52a19ba983ca26913400d6368f3594e8a5427d24",
    "S38W068": "1f4cf4971cbb14091c4d5cbd5e3a70962e686345711ce844b01a5e2af7829fa2",
    "S39W071": "343de919159791b435bea618b1cb2525e569026fe8765af813f0a50f5405daf6",
    "S39W070": "825aa83d9c8576258ff1754f34a048e3b1d7d4e86b1a58a3942472bdbbb7fa52",
    "S39W069": "3cd308b2410bfd700a3aec5eabd3eb62fdb7b1426d608af4550dfabead36dd44",
    "S39W068": "ce139b79b2fe426e470ab658179f7ee592b6c3652f1ee13cd8e3a18a99970a6f",
    "S40W071": "297146fcb29cbcba09889e21dcfd74030280805363e03bfca922e90cea0e4e4d",
    "S40W070": "58516cf321eb089695160e915e14ee85958f6f7b6f78df4fee20cf187434273e",
    "S40W069": "d293f7723506df3aec0fd8525f7db7d07ddcac8373fd3cd80605aaf2431ca827",
    "S40W068": "06cc6cf1726f5b83f5ed98b8ea8b54aa000695cbf84541b386f93c46252fec91",
    "concesiones_explotacion.zip": "5245af707af4a4f8154d7ea80908aa4992d57f3eff7f19a64a92bbee4b45e0eb",
    "areas_de_aguas_continentales_BH130": "c51a96ef17a081ca71076158b0016c08ba1e946d8bdfc096f5fffbe9f1c7ec89",
    "areas_de_aguas_continentales_BH140": "c1515c50678fcce180b393be00271bca412884e7bfd5214b5643d48c8438068d",
    "areas_de_aguas_continentales_perenne": "39cfcdd5e92add20eb70545c6bd69bf77533fdd3ec13b6adf534fea4e2b71568",
    "lineas_de_aguas_continentales_perenne": "b08ccbbcb77eaad497d275ca45d410cf1069c8d0bad0e2882c1e8ef00b17e09c",
    "linea_de_limite_070111": "b96c7cdcf19042a40de59afced4a028f2de17a1cb2826ac61a788b0c8bc8fcb7",
    "localidad_bahra": "2a3e2f3e7c879300d82c3cac0aea1efb779437ca6459b2e8d005adb670c0e71d",
}

Punto = tuple[int, int]


class FuenteCambiada(ValueError):
    """A pinned source no longer hashes to its entry in PINES."""


def _sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _b64(datos: bytes) -> str:
    return base64.b64encode(bytes(datos)).decode("ascii")


def _leer_bytes(ruta: Path, nombre: str) -> bytes:
    """Read a pinned raw file, checking the pin of its bytes."""
    try:
        datos = ruta.read_bytes()
    except FileNotFoundError:
        raise FileNotFoundError(f"missing source {ruta}, run with --descargar to fetch it") from None
    encontrado = _sha(datos)
    if encontrado != PINES[nombre]:
        raise FuenteCambiada(f"source {nombre} changed: expected {PINES[nombre]}, found {encontrado}")
    return datos


def hash_canonico(features: list) -> str:
    """Canonical hash of an IGN layer, independent of feature and key order."""
    ordenadas = sorted(features, key=lambda f: f["id"])
    canon = json.dumps([[f["id"], f["geometry"], f["properties"]] for f in ordenadas],
                       ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha(canon)


def capa_ign(nombre: str, raw: Path = RAW) -> tuple[list, str]:
    """Read an IGN layer sorted by id, checking its canonical pin."""
    ruta = raw / "ign" / f"{nombre}.geojson"
    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"missing source {ruta}, run with --descargar to fetch it") from None
    features = sorted(json.loads(texto)["features"], key=lambda f: f["id"])
    encontrado = hash_canonico(features)
    if encontrado != PINES[nombre]:
        raise FuenteCambiada(f"source {nombre} changed: expected {PINES[nombre]}, found {encontrado}")
    return features, encontrado


# ---------- relief ----------


def cargar_mosaico(raw: Path = RAW) -> tuple[np.ndarray, list[tuple[str, str]]]:
    """Assemble the 16 Skadi tiles into one int32 mosaic, checking every pin.

    Row 0 is lat -36, column 0 is lon -71. Returns the mosaic and the
    (tile, sha256) pairs in tile order, used for the relief fuente entry.
    """
    mosaico = np.zeros((4 * 3600, 4 * 3600), dtype=np.int32)
    hs = []
    for nombre in TILES:
        datos = _leer_bytes(raw / "skadi" / f"{nombre}.hgt.gz", nombre)
        hs.append((nombre, _sha(datos)))
        loseta = np.frombuffer(gzip.decompress(datos), dtype=">i2").reshape(3601, 3601)
        i, j = int(nombre[1:3]) - 37, 71 - int(nombre[4:7])
        mosaico[i * 3600:(i + 1) * 3600, j * 3600:(j + 1) * 3600] = loseta[:3600, :3600]
    return mosaico, hs


def media_bloques(rec: np.ndarray, filas: int, cols: int, by: int, bx: int) -> np.ndarray:
    """Rounded integer mean of each by x bx block, voids (at most -1000) excluded."""
    m = rec.astype(np.int64)
    val = m > -1000
    s = np.where(val, m, 0).reshape(filas, by, cols, bx).sum(axis=(1, 3))
    n = val.reshape(filas, by, cols, bx).sum(axis=(1, 3))
    assert n.min() > 0
    return ((2 * s + n) // (2 * n)).astype(np.int64)


def codificar_relieve(z: np.ndarray) -> bytes:
    """Encode an integer grid row by row: absolute Uint16 LE, then Int8 deltas.

    Byte 128 is an escape followed by an absolute Uint16 LE (used for jumps
    outside -127..127, including a delta of exactly -128).
    """
    out = bytearray()
    filas, cols = z.shape
    for f in range(filas):
        v = int(z[f, 0])
        out += struct.pack("<H", v)
        for c in range(1, cols):
            d = int(z[f, c]) - v
            v = int(z[f, c])
            if -127 <= d <= 127:
                out.append(d & 255)
            else:
                out.append(128)
                out += struct.pack("<H", v)
    return bytes(out)


def decodificar_relieve(rel: dict) -> np.ndarray:
    """Decode a relief dict back to its integer grid (filas x cols)."""
    cols, filas = rel["cols"], rel["filas"]
    datos = base64.b64decode(rel["d"], validate=True)
    z = np.zeros((filas, cols), dtype=np.int64)
    o = 0
    for f in range(filas):
        v = struct.unpack_from("<H", datos, o)[0]
        o += 2
        z[f, 0] = v
        for c in range(1, cols):
            b = datos[o]
            o += 1
            if b == 128:
                v = struct.unpack_from("<H", datos, o)[0]
                o += 2
            else:
                v += b if b < 128 else b - 256
            z[f, c] = v
    return z


def construir_relieve(raw: Path = RAW) -> tuple[dict, list[tuple[str, str]]]:
    """Build the relief dict and the (tile, sha256) pairs for fuentes."""
    lon0, lat0, lon1, lat1 = CAJA
    mosaico, hs = cargar_mosaico(raw)
    c0, f0 = round((lon0 + 71) * 3600), round((-36 - lat1) * 3600)
    bx, by = round((lon1 - lon0) * 3600) // COLS, round((lat1 - lat0) * 3600) // FILAS
    z = media_bloques(mosaico[f0:f0 + FILAS * by, c0:c0 + COLS * bx], FILAS, COLS, by, bx)
    rel = {"cols": COLS, "filas": FILAS, "min": int(z.min()), "max": int(z.max()), "d": _b64(codificar_relieve(z))}
    return rel, hs


def construir_relieve_fino(raw: Path = RAW) -> dict:
    """Build the finer relief of the core: blocks of PASO_FINO arc-seconds over NUCLEO, same tiles, same codec.

    A tile sample sits on a whole arc-second, so the mean of a block of samples belongs half a second north-west
    of the centre of the block of cells that NUCLEO would give. The product's caja carries that shift, so a cell
    centre is where its samples are.
    """
    lon0, lat0, lon1, lat1 = NUCLEO
    mosaico, _ = cargar_mosaico(raw)
    c0, f0 = round((lon0 + 71) * 3600), round((-36 - lat1) * 3600)
    cols, filas = round((lon1 - lon0) * 3600) // PASO_FINO, round((lat1 - lat0) * 3600) // PASO_FINO
    z = media_bloques(mosaico[f0:f0 + filas * PASO_FINO, c0:c0 + cols * PASO_FINO], filas, cols, PASO_FINO, PASO_FINO)
    m = .5 / 3600
    return {"v": 1, "caja": [lon0 - m, lat0 + m, lon1 - m, lat1 + m], "paso_seg": PASO_FINO, "margen": MARGEN_FINO,
            "cols": cols, "filas": filas, "min": int(z.min()), "max": int(z.max()), "d": _b64(codificar_relieve(z))}


# ---------- vectors ----------


def qpt(lon: float, lat: float) -> Punto:
    """Quantise a lon/lat pair over the box: north west is (0, 0)."""
    lon0, lat0, lon1, lat1 = CAJA
    return (math.floor((lon - lon0) / (lon1 - lon0) * Q + .5), math.floor((lat1 - lat) / (lat1 - lat0) * Q + .5))


def dentro(p: Punto) -> bool:
    return 0 <= p[0] <= Q and 0 <= p[1] <= Q


def fijar(p: Punto) -> Punto:
    return (min(Q, max(0, p[0])), min(Q, max(0, p[1])))


def simplificar(pts: list[Punto], tol: float) -> list[Punto]:
    """Integer Douglas-Peucker (exact). tol in approximate metres."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    pila = [(0, len(pts) - 1)]
    while pila:
        a, b = pila.pop()
        ax, ay = pts[a][0] * MX, pts[a][1] * MY
        bx, by = pts[b][0] * MX, pts[b][1] * MY
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        mejor_n, mejor_d, im = 0, 1, -1
        for i in range(a + 1, b):
            px, py = pts[i][0] * MX - ax, pts[i][1] * MY - ay
            if l2 == 0:
                d2n, d2d = px * px + py * py, 1
            else:
                cr = px * dy - py * dx
                d2n, d2d = cr * cr, l2
            # squared distance to the chord as a fraction d2n/d2d, compared without floats
            if im < 0 or d2n * mejor_d > mejor_n * d2d:
                mejor_n, mejor_d, im = d2n, d2d, i
        if im >= 0 and mejor_n > tol * tol * mejor_d:
            keep[im] = True
            pila.append((a, im))
            pila.append((im, b))
    return [p for p, k in zip(pts, keep) if k]


def sin_repetidos(pts: list[Punto]) -> list[Punto]:
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    return out


def unir(lineas: list[list[Punto]]) -> list[list[Punto]]:
    """Join segments that share an endpoint. Deterministic order."""
    lineas = sorted(l for l in lineas if len(l) >= 2)
    usado = [False] * len(lineas)
    ext: dict[Punto, list[int]] = {}
    for i, l in enumerate(lineas):
        ext.setdefault(l[0], []).append(i)
        ext.setdefault(l[-1], []).append(i)
    out = []
    for i, l in enumerate(lineas):
        if usado[i]:
            continue
        usado[i] = True
        cad = list(l)
        for _ in range(2):
            while True:
                sig = next((j for j in ext.get(cad[-1], []) if not usado[j]), None)
                if sig is None:
                    break
                usado[sig] = True
                t = lineas[sig]
                cad += t[1:] if t[0] == cad[-1] else t[-2::-1]
            cad.reverse()
        out.append(cad)
    return out


def codif(pts: list[Punto]) -> str:
    return _b64(b"".join(struct.pack("<HH", x, y) for x, y in pts))


def decodificar_linea(s: str) -> list[Punto]:
    """Decode a base64 line or ring back to its (x, y) pairs."""
    return [(x, y) for x, y in struct.iter_unpack("<HH", base64.b64decode(s, validate=True))]


def largo_km(pts: list[Punto]) -> float:
    return sum(((a[0] - b[0]) ** 2 * MX * MX + (a[1] - b[1]) ** 2 * MY * MY) ** .5
               for a, b in zip(pts, pts[1:])) / 1000


def area_km2(r: list[Punto]) -> float:
    return abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))) / 2 * MX * MY / 1e6


def tramos(coords: list) -> list[list[Punto]]:
    """Split a line where it leaves the box."""
    out, act = [], []
    for c in coords:
        p = qpt(c[0], c[1])
        if dentro(p):
            act.append(p)
        else:
            if len(act) >= 2:
                out.append(act)
            act = []
    if len(act) >= 2:
        out.append(act)
    return [sin_repetidos(t) for t in out]


def anillos(geom: dict, tol: float, min_km2: float = 0.0) -> list[list[Punto]]:
    out = []
    for pol in geom["coordinates"]:
        for k, r in enumerate(pol):
            q = sin_repetidos([fijar(qpt(c[0], c[1])) for c in r])
            if len(q) < 4:
                continue
            s = simplificar(q, tol)
            if len(s) < 4 or area_km2(s) <= 0:
                continue
            if k == 0 and area_km2(s) < min_km2:
                break
            out.append(s)
    return out


# ---------- layers (each takes parsed features, no file access) ----------


def construir_rios(features: list) -> list[dict]:
    """Group perennial lines by full name, keep names of 60 km or more."""
    por: dict[str, list] = {}
    for f in features:
        n = f["properties"]["fna"]
        if not n or not f["properties"]["nam"]:
            continue
        for l in f["geometry"]["coordinates"]:
            por.setdefault(n, []).extend(tramos(l))
    out = []
    for n in sorted(por):
        cad = unir(por[n])
        km = sum(largo_km(c) for c in cad)
        if km < RIO_MIN_KM:
            continue
        ls = [simplificar(c, TOL_RIO) for c in cad]
        ls = [l for l in ls if largo_km(l) >= TRAMO_MIN_KM]
        out.append({"n": n, "km": round(km), "l": [codif(l) for l in ls]})
    return out


def construir_agua(grupos: list[tuple[list, str, float]]) -> list[dict]:
    """Group water polygons by name within each (features, tipo, minimo) group."""
    out = []
    for features, tipo, minimo in grupos:
        por: dict[str, list] = {}
        for f in features:
            n = (f["properties"]["fna"] if f["properties"]["nam"] else "") or ""
            rs = anillos(f["geometry"], TOL_AGUA, minimo)
            if rs:
                por.setdefault(n, []).extend(rs)
        for n in sorted(por):
            km2 = sum(area_km2(r) for r in por[n])
            out.append({"n": n, "t": tipo, "km2": round(km2), "p": [codif(r) for r in por[n]]})
    return out


def construir_limites(features: list) -> list[dict]:
    """Group border lines by name, joining segments that share endpoints."""
    por: dict[str, list] = {}
    for f in features:
        n = f["properties"]["fna"].split(" Tramo")[0]
        for l in f["geometry"]["coordinates"]:
            por.setdefault(n, []).extend(tramos(l))
    out = []
    for n in sorted(por):
        ls = [simplificar(c, TOL_LIMITE) for c in unir(por[n])]
        out.append({"n": n, "l": [codif(l) for l in ls]})
    return out


def construir_localidades(features: list) -> list[dict]:
    """Pick the fixed town list in label priority order."""
    out = []
    for f in features:
        p = f["properties"]
        if p["fna"] in LOCALIDADES and (p["tipo_asent"] == "Localidad simple" or p["fna"] in (
                "Cutral Có", "Plaza Huincul", "Cipolletti", "General Roca", "Neuquén", "Plottier", "Centenario")):
            lon, lat = f["geometry"]["coordinates"][0][:2]
            out.append({"n": p["fna"], "prov": p["nom_pcia"], "lon": round(lon, 5), "lat": round(lat, 5)})
    out.sort(key=lambda d: (LOCALIDADES.index(d["n"]), d["prov"]))
    return out


def construir_bloques(datos: bytes) -> list[dict]:
    """Parse the exploitation-blocks zip bytes (SHP polygons plus DBF rows)."""
    z = zipfile.ZipFile(io.BytesIO(datos))
    shp = next(z.read(n) for n in z.namelist() if n.endswith(".shp"))
    dbf = next(z.read(n) for n in z.namelist() if n.endswith(".dbf"))
    n, hl, rl = struct.unpack("<IHH", dbf[4:12])
    campos = []
    o = 32
    while dbf[o] != 0x0D:
        campos.append((dbf[o:o + 11].split(b"\0")[0].decode("ascii"), dbf[o + 16]))
        o += 32
    filas = []
    for k in range(n):
        rec = dbf[hl + k * rl:hl + (k + 1) * rl]
        p = 1
        fila = {}
        for nom, lar in campos:
            fila[nom] = rec[p:p + lar].decode("utf-8", "replace").strip()
            p += lar
        filas.append(fila)
    out, o = [], 100
    lon0, lat0, lon1, lat1 = CAJA
    while o < len(shp):
        num, largo = struct.unpack(">ii", shp[o:o + 8])
        c = shp[o + 8:o + 8 + 2 * largo]
        o += 8 + 2 * largo
        tipo = struct.unpack("<i", c[:4])[0]
        fila = filas[num - 1]
        if tipo == 0:
            continue
        assert tipo in (5, 15, 25), tipo
        xmin, ymin, xmax, ymax = struct.unpack("<4d", c[4:36])
        np_, nv = struct.unpack("<ii", c[36:44])
        if xmax < lon0 or xmin > lon1 or ymax < lat0 or ymin > lat1:
            continue
        partes = list(struct.unpack(f"<{np_}i", c[44:44 + 4 * np_])) + [nv]
        pts = struct.unpack(f"<{2 * nv}d", c[44 + 4 * np_:44 + 4 * np_ + 16 * nv])
        rs = []
        for a, b in zip(partes, partes[1:]):
            q = sin_repetidos([fijar(qpt(pts[2 * i], pts[2 * i + 1])) for i in range(a, b)])
            if len(q) < 4:
                continue
            s = simplificar(q, TOL_BLOQUE)
            if len(s) >= 4 and area_km2(s) > 0:
                rs.append(s)
        if rs:
            out.append({"n": " ".join(fila["NOMBRE_DE_"].split()), "c": fila["CODIGO_DE_"],
                        "op": " ".join(fila["EMPRESA_OP"].split()), "km2": round(sum(area_km2(r) for r in rs)),
                        "p": [codif(r) for r in rs]})
    out.sort(key=lambda d: (d["n"], d["c"]))
    return out


def construir_fuentes(hs: list[tuple[str, str]], hr: str, ha: dict[str, str],
                      hl: str, hlo: str, hb: str) -> list[dict]:
    """Build the fuentes entries from the checked hashes."""
    return [
        {"capa": "relieve", "titulo": "SRTM de 1 segundo de arco (teselas skadi de Terrain Tiles)",
         "organismo": "NASA y USGS", "url": SKADI.format(d="S39", w="W069"), "licencia": LIC_SRTM,
         "sha256": _sha("".join(f"{n}:{h}\n" for n, h in hs).encode()), "fecha": FECHA_DESCARGA},
        {"capa": "rios", "titulo": "Corriente de agua perenne", "organismo": "Instituto Geográfico Nacional",
         "url": IGN + "lineas_de_aguas_continentales_perenne", "licencia": LIC_IGN,
         "sha256": hr, "fecha": FECHA_DESCARGA},
        {"capa": "agua", "titulo": "Embalse", "organismo": "Instituto Geográfico Nacional",
         "url": IGN + "areas_de_aguas_continentales_BH130", "licencia": LIC_IGN,
         "sha256": ha["areas_de_aguas_continentales_BH130"], "fecha": FECHA_DESCARGA},
        {"capa": "agua", "titulo": "Espejo de agua perenne", "organismo": "Instituto Geográfico Nacional",
         "url": IGN + "areas_de_aguas_continentales_perenne", "licencia": LIC_IGN,
         "sha256": ha["areas_de_aguas_continentales_perenne"], "fecha": FECHA_DESCARGA},
        {"capa": "agua", "titulo": "Corriente de agua (áreas)", "organismo": "Instituto Geográfico Nacional",
         "url": IGN + "areas_de_aguas_continentales_BH140", "licencia": LIC_IGN,
         "sha256": ha["areas_de_aguas_continentales_BH140"], "fecha": FECHA_DESCARGA},
        {"capa": "limites", "titulo": "Límite interprovincial", "organismo": "Instituto Geográfico Nacional",
         "url": IGN + "linea_de_limite_070111", "licencia": LIC_IGN, "sha256": hl, "fecha": FECHA_DESCARGA},
        {"capa": "localidades", "titulo": "Localidad (BAHRA)", "organismo": "Instituto Geográfico Nacional",
         "url": IGN + "localidad_bahra", "licencia": LIC_IGN, "sha256": hlo, "fecha": FECHA_DESCARGA},
        {"capa": "bloques", "titulo": "Producción de hidrocarburos: concesiones de explotación",
         "organismo": "Secretaría de Energía", "url": SHP, "licencia": LIC_BLOQUES,
         "sha256": hb, "fecha": FECHA_DESCARGA},
    ]


def cota(z: np.ndarray, caja: tuple[float, float, float, float], lon: float, lat: float) -> float | None:
    """Bilinear elevation over a decoded grid, None outside the box."""
    lon0, lat0, lon1, lat1 = caja
    if not (lon >= lon0 and lon <= lon1 and lat >= lat0 and lat <= lat1):
        return None
    filas, cols = z.shape
    x = max(0.0, min(cols - 1, (lon - lon0) / (lon1 - lon0) * cols - .5))
    y = max(0.0, min(filas - 1, (lat1 - lat) / (lat1 - lat0) * filas - .5))
    c, f = min(cols - 2, math.floor(x)), min(filas - 2, math.floor(y))
    u, v = x - c, y - f
    return float((z[f, c] * (1 - u) + z[f, c + 1] * u) * (1 - v)
                 + (z[f + 1, c] * (1 - u) + z[f + 1, c + 1] * u) * v)


# ---------- wiki page ----------

def abrir_fino(fino: dict) -> dict:
    """Decode the finer relief once: its grid, its box and its blend margin."""
    return {"z": decodificar_relieve(fino), "caja": tuple(fino["caja"]), "margen": fino["margen"]}


def peso_fino(caja: tuple[float, float, float, float], margen: float, lon: float, lat: float) -> float:
    """Weight of the finer relief at a point: 0 outside its box and on its edge, 1 past the margin (smoothstep)."""
    lon0, lat0, lon1, lat1 = caja
    qx, qy = (lon - lon0) / (lon1 - lon0), (lat1 - lat) / (lat1 - lat0)
    t = max(0.0, min(1.0, min(qx, 1 - qx, qy, 1 - qy) / margen))
    return t * t * (3 - 2 * t)


def cota_mixta(z: np.ndarray, caja: tuple[float, float, float, float], fino: dict | None,
               lon: float, lat: float) -> float | None:
    """Elevation the page draws: the sheet grid, blended into the finer grid (abrir_fino) inside its box."""
    h = cota(z, caja, lon, lat)
    if h is None or fino is None:
        return h
    w = peso_fino(fino["caja"], fino["margen"], lon, lat)
    if w <= 0:
        return h
    return h + (cota(fino["z"], fino["caja"], lon, lat) - h) * w


CAPA_ES = {"relieve": "Relieve", "rios": "Ríos", "agua": "Lagos, embalses y cauces anchos",
           "limites": "Límites interprovinciales", "localidades": "Localidades", "bloques": "Concesiones de explotación"}


def _miles(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def _grados(v: float) -> str:
    return f"{abs(v):.1f}".replace(".", ",")


def recuentos(base: dict) -> dict[str, int]:
    """Counts printed on the wiki page; pipeline.claims pins each one against the product."""
    rel, agua = base["relieve"], base["agua"]
    tipo = {t: sum(1 for a in agua if a["n"] and a["t"] == t) for t in ("embalse", "lago", "rio")}
    return {"cols": rel["cols"], "filas": rel["filas"], "cota_min": rel["min"], "cota_max": rel["max"],
            "rios": len(base["rios"]), "agua_con_nombre": sum(tipo.values()), "embalses": tipo["embalse"],
            "lagos": tipo["lago"], "cauces": tipo["rio"],
            "agua_sin_nombre": sum(len(a["p"]) for a in agua if not a["n"]),
            "limites": len(base["limites"]), "localidades": len(base["localidades"]),
            "bloques": len(base["bloques"]), "operadoras": len({b["op"] for b in base["bloques"]})}


def recuentos_fino(fino: dict) -> dict[str, int]:
    """Counts of the finer relief printed on the wiki page; pipeline.claims pins each one against the product."""
    lon0, lat0, lon1, lat1 = fino["caja"]
    paso_m = fino["paso_seg"] / 3600 * 111320
    return {"cols": fino["cols"], "filas": fino["filas"], "paso_seg": fino["paso_seg"],
            "cota_min": fino["min"], "cota_max": fino["max"], "margen_pct": round(fino["margen"] * 100),
            "m_este": round(paso_m * math.cos(math.radians((lat0 + lat1) / 2))), "m_sur": round(paso_m)}


def leer_fino(ruta: Path | None = None) -> dict | None:
    """The finer relief of the core as written by this module, or None when it is not built."""
    ruta = FINO if ruta is None else ruta
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def leer_foto(ruta: Path | None = None) -> dict | None:
    """The manifest of the ground imagery that pipeline.base_foto writes, or None when it is not built."""
    ruta = FOTO if ruta is None else ruta
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def _linea_fino(fino: dict) -> str:
    f = recuentos_fino(fino)
    lon0, lat0, lon1, lat1 = (f"{abs(v):.2f}".rstrip("0").replace(".", ",") for v in NUCLEO)
    return (f"- relieve fino del núcleo: entre los {lon0}° y los {lon1}° de longitud oeste y entre los {lat0}° y los "
            f"{lat1}° de latitud sur, donde está la mayoría de los pozos, una segunda grilla fina de "
            f"{_miles(f['cols'])} por {_miles(f['filas'])} celdas de {f['paso_seg']} segundos de arco (cerca de "
            f"{f['m_este']} m hacia el este y {f['m_sur']} m hacia el sur), con cotas de {_miles(f['cota_min'])} a "
            f"{_miles(f['cota_max'])} m. La página dibuja esta y la funde con la de la hoja en una franja junto a "
            f"cada borde, el {f['margen_pct']} % del lado del recorte;")


def leer_exactitud(ruta: Path | None = None) -> dict | None:
    """The accuracy measurements that pipeline.exactitud writes, or None when they are not there."""
    ruta = EXACTITUD if ruta is None else ruta
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def _dec(v: float, n: int = 1) -> str:
    return f"{abs(v):.{n}f}".replace(".", ",")


def seccion_exactitud(e: dict) -> list[str]:
    """The wiki section that quotes data/exactitud.json; pipeline.claims pins each number against that file."""
    r, im, d, pg = e["relieve"], e["imagen"], e["dibujo"], e["pagina"]
    po, nu, ho, hn, ind = r["pozos"], r["pozos_nucleo"], r["solo_hoja"], r["solo_hoja_nucleo"], r.get("independiente")

    def lugares(filas):
        return "; ".join(f"{f['nombre']}: {_miles(f['fuente_m'])} m en la fuente y {_miles(f['pagina_m'])} m en la "
                         "página" for f in filas) + "."

    def largas(v):
        return f"un {_dec(v)} % {'largas' if v >= 0 else 'cortas'}"

    L = [
        "## Exactitud",
        "",
        "Qué tan bien ubica la página lo que dibuja. Lo mide `python -m pipeline.exactitud` sobre la página publicada "
        f"(datos a {pg['mes_datos']}, {_miles(pg['pozos'])} pozos) y lo guarda en `data/exactitud.json`. Cada línea dice "
        "si es una medida o un supuesto.",
        "",
        f"- medido, relieve contra su fuente: en las bocas de los {_miles(po['n'])} pozos que caen dentro de la hoja, "
        "la cota que dibuja la página difiere de la del modelo de un segundo de arco en "
        f"{_dec(po['mediana'])} m de mediana; el 99 % queda a {_dec(po['p99'])} m o menos y el peor caso es de "
        f"{_dec(po['max'])} m."
        + ("" if nu is None else " Con la grilla de la hoja sola, en esos mismos pozos, la mediana era de "
           f"{_dec(ho['mediana'])} m y el 99 % quedaba a {_dec(ho['p99'])} m o menos. En los {_miles(nu['n'])} pozos "
           f"donde rige entero el relieve fino, la mediana es de {_dec(nu['mediana'])} m, el 99 % queda a "
           f"{_dec(nu['p99'])} m o menos y el peor caso es de {_dec(nu['max'])} m; en esos, con la grilla de la hoja "
           f"sola eran {_dec(hn['mediana'])} m y {_dec(hn['p99'])} m."),
        "- medido, cumbres: una celda promedia el terreno que cubre, así que la página rebaja las cumbres. "
        + lugares(r["cumbres"]),
        "- medido, espejos de agua: " + lugares(r["niveles"]),
    ]
    if ind:
        a, m, dia = ind["fecha_consulta"].split("-")

        def mas(v):
            return f"{_dec(v)} m {'más' if v >= 0 else 'menos'}"

        L.append(
            f"- medido, relieve contra un modelo independiente: en una muestra fija de {ind['n']} bocas, la fuente da "
            f"{mas(ind['fuente_mediana'])} que el modelo Copernicus GLO-90 en la mediana, con una diferencia máxima de "
            f"{_dec(ind['fuente_max'])} m; la página da {mas(ind['pagina_mediana'])}, con una máxima de "
            f"{_dec(ind['pagina_max'])} m. Los valores de GLO-90 se consultaron una sola vez, el {dia}/{m}/{a}, y "
            "quedaron, con su fuente y su atribución, en `data/exactitud_glo90.json`.")
    dx, dy = im["agua_mejor_px"]
    L += [
        f"- medido, pozos sobre la imagen: se apilaron los recortes de la imagen centrados en {_miles(im['pads'])} "
        f"locaciones, las de pozos que producían al menos {im['meses_antes']} meses antes de la imagen. La pila tiene "
        f"su máximo{' en el píxel del centro' if im['pico_en_centro'] else ''}, de {_dec(im['pico_sd'])} desvíos sobre "
        f"el entorno, y su centro queda a {abs(im['este_m'])} m al {'este' if im['este_m'] >= 0 else 'oeste'} y "
        f"{abs(im['norte_m'])} m al {'norte' if im['norte_m'] >= 0 else 'sur'} de la posición publicada; un píxel mide "
        f"{im['pixel_m'][0]} por {im['pixel_m'][1]} m. El {im['claros_pct']} % de las locaciones cae sobre suelo más "
        f"claro que su entorno. La misma pila corrida {im['control_km']} km al este no muestra ningún máximo: llega a "
        f"{_dec(im['control_sd'])} desvíos. La imagen se ve blanda de cerca porque cada píxel cubre esas decenas de "
        "metros: es resolución, no un error de ubicación.",
        f"- medido, agua sobre la imagen: el contorno de {' y '.join(im['embalses'])} coincide con el agua de la "
        f"imagen en el {_dec(100 * im['agua_iou'])} % (intersección sobre unión)"
        + (f", y ningún corrimiento de hasta {im['busca_px']} píxeles lo mejora." if (dx, dy) == (0, 0) else
           f"; corrido {abs(dx)} píxeles al {'este' if dx >= 0 else 'oeste'} y {abs(dy)} al "
           f"{'sur' if dy >= 0 else 'norte'} llega al {_dec(100 * im['agua_mejor_iou'])} %."),
        f"- supuesto, el dibujo es plano: la página dibuja cada grado de latitud como {_dec(d['km_grado'], 2)} km y "
        f"cada grado de longitud como {_dec(d['km_grado'], 2)} km por el coseno de la latitud del pozo mediano. Contra "
        "el elipsoide WGS84, eso "
        f"{'alarga' if d['ns_pct'] >= 0 else 'acorta'} las distancias norte-sur un {_dec(d['ns_pct'], 2)} %. Las "
        f"distancias este-oeste quedan {largas(d['eo_nucleo_pct'][0])} en el borde norte del núcleo y "
        f"{largas(d['eo_nucleo_pct'][1])} en el borde sur; en los bordes de la hoja, {largas(d['eo_hoja_pct'][0])} al "
        f"norte y {largas(d['eo_hoja_pct'][1])} al sur. Las distancias entre pozos del estudio no salen del dibujo: se "
        "calculan con la latitud de cada pozo.",
        "- supuesto, registro de la grilla de la hoja: sus celdas quedan medio segundo de arco corridas respecto de "
        f"las muestras que promedian, cerca de {d['medio_segundo_m'][0]} m al este y {d['medio_segundo_m'][1]} m al "
        "sur. El relieve fino lo corrige en el núcleo, y el efecto ya está dentro de las diferencias medidas arriba.",
        "",
    ]
    return L


def pagina(base: dict, foto: dict | None = None, fino: dict | None = None, exactitud: dict | None = None) -> str:
    """The wiki page of the base map, from the product alone (same product, same bytes).

    foto is the manifest of the ground imagery (leer_foto()); with it the page gains the section about the image.
    fino is the finer relief of the core (leer_fino()); with it the page says what it covers and how it is built.
    exactitud is what pipeline.exactitud measured (leer_exactitud()); with it the page gains the accuracy section.
    """
    r = recuentos(base)
    lon0, lat0, lon1, lat1 = base["caja"]
    seg_x, seg_y = round((lon1 - lon0) * 3600 / r["cols"]), round((lat1 - lat0) * 3600 / r["filas"])
    L = [
        "# Mapa base de Vaca Muerta en 3D: fuentes y licencias",
        "",
        "Lo que se ve debajo de los pozos en `site/mundo.html` (relieve, ríos, lagos y embalses, límites entre "
        "provincias, localidades y concesiones de explotación) es dato publicado por tres organismos, no una estimación "
        "de este estudio. La regla es una sola: sin fuente no hay capa. Ningún río se dibuja de memoria y ningún bloque "
        "se inventa a partir de los pozos.",
        "",
        "Esta página la escribe `python -m pipeline.base_mapa` a partir de `data/base_mapa.json`"
        + (" y, para la imagen del suelo, de `data/base_foto.json`" if foto is not None else "") + ". No se edita a mano.",
        "",
        "## Qué cubre",
        "",
        f"La hoja va de {_grados(lon0)}° a {_grados(lon1)}° de longitud oeste y de {_grados(lat0)}° a {_grados(lat1)}° "
        "de latitud sur. Tiene:",
        "",
        f"- relieve: una grilla de {r['cols']} por {r['filas']} celdas ({seg_x} por {seg_y} segundos de arco, cerca de "
        f"500 m de lado), con cotas de {_miles(r['cota_min'])} a {_miles(r['cota_max'])} m sobre el nivel del mar;",
        *([] if fino is None else [_linea_fino(fino)]),
        f"- {_miles(r['rios'])} ríos y arroyos con nombre, los que suman {RIO_MIN_KM:.0f} km o más dentro de la hoja;",
        f"- {_miles(r['agua_con_nombre'])} cuerpos de agua con nombre ({r['embalses']} embalses, {r['lagos']} lagos y "
        f"{r['cauces']} cauces anchos) y {_miles(r['agua_sin_nombre'])} contornos sin nombre;",
        f"- {_miles(r['limites'])} límites entre provincias;",
        f"- {_miles(r['localidades'])} localidades, de una lista fija;",
        f"- {_miles(r['bloques'])} concesiones de explotación de {_miles(r['operadoras'])} empresas operadoras, con "
        "nombre y código.",
        "",
        "## Fuentes",
        "",
        "| Capa | Conjunto | Organismo | Licencia | Bajado |",
        "|---|---|---|---|---|",
    ]
    for f in base["fuentes"]:
        dia = "/".join(reversed(f["fecha"].split("-")))
        L.append(f"| {CAPA_ES[f['capa']]} | {f['titulo']} | {f['organismo']} | {f['licencia']} | {dia} |")
    L += [
        "",
        "Dirección de descarga y huella de cada conjunto:",
        "",
    ]
    for f in base["fuentes"]:
        L.append(f"- {f['titulo']}: `{f['url']}`, sha256 `{f['sha256']}`.")
    L += [
        "",
        f"El relieve son {len(TILES)} teselas de un grado (la dirección de arriba es una de ellas) y su huella es el "
        "sha256 de la lista de las huellas de cada tesela. La huella de las capas del Instituto Geográfico Nacional es "
        "el sha256 de una forma canónica de sus elementos (ordenados por id), porque ese servicio no devuelve dos veces "
        "los mismos bytes. La de las concesiones es el sha256 del archivo bajado. El exportador no corre si una fuente "
        "cambió: hay que mirar qué cambió y fijar la huella nueva a mano.",
        "",
        "## Cómo se arma cada capa",
        "",
        f"- Relieve: cada celda es la media entera de {seg_x} por {seg_y} muestras de un segundo de arco, sin contar "
        "los vacíos de la fuente."
        + ("" if fino is None else f" El relieve fino del núcleo sale de las mismas teselas con bloques de "
           f"{fino['paso_seg']} por {fino['paso_seg']} muestras. Cada muestra de la fuente cae sobre un segundo de "
           "arco entero, así que la media de un bloque corresponde a medio segundo al noroeste del centro que le "
           "daría la caja: la caja del relieve fino lleva ese corrimiento y la de la hoja no"
           + (" (ver Exactitud)." if exactitud is not None else ".")),
        "- Ríos: las líneas de agua perenne se agrupan por nombre completo, se unen los tramos que comparten un extremo "
        f"y se simplifican con una tolerancia de {TOL_RIO} m. Quedan los nombres que suman {RIO_MIN_KM:.0f} km o más.",
        f"- Agua: todos los embalses y cauces anchos, y los lagos de {LAGO_MIN_KM2:.0f} km² o más, con una tolerancia de "
        f"{TOL_AGUA} m.",
        f"- Límites: los tramos de cada límite se unen y se simplifican con una tolerancia de {TOL_LIMITE} m.",
        "- Localidades: la lista fija del exportador, en el orden en que la página decide qué nombre mostrar primero.",
        "- Concesiones: los polígonos del archivo cuya caja toca la hoja, tal como se publican, con una tolerancia de "
        f"{TOL_BLOQUE} m.",
        f"- Todas las coordenadas se guardan en una grilla de {_miles(Q)} pasos por lado: cerca de {MX} m hacia el este "
        f"y {MY} m hacia el sur.",
        "",
    ]
    if foto is not None:
        from pipeline import base_foto  # here and not at the top: base_foto imports this module
        L += base_foto.seccion(foto)
    if exactitud is not None:
        L += seccion_exactitud(exactitud)
    L += [
        "## Qué no es",
        "",
        "- No es cartografía oficial y no sirve para medir un lindero: las líneas están simplificadas.",
        "- Las concesiones son las del archivo publicado el día de la descarga. No muestran cambios posteriores de "
        "titular ni permisos de exploración.",
        "- El relieve es el terreno. No dice nada de la profundidad de una formación: en la página la profundidad sigue "
        "siendo un esquema, y así está rotulada.",
    ]
    if foto is not None:
        L.append("- La imagen del suelo tiene fecha y no cambia con el reloj de la página: un pozo posterior a esa "
                 "fecha puede no tener todavía su locación en ella, y al mirar un mes anterior se ven locaciones que "
                 "todavía no existían. La página lo dice en pantalla.")
    L += [
        "",
        "## Reproducir",
        "",
        "```",
        "uv run python -m pipeline.base_mapa --descargar   # baja lo que falta a data/raw/base_mapa y arma el producto",
        "uv run python -m pipeline.base_mapa --verificar   # compara con data/base_mapa.json y con esta página",
        "uv run python -m pipeline.base_mapa --pagina      # reescribe solo esta página, sin los archivos crudos",
    ]
    if foto is not None:
        L += [
            "uv run --with pillow python -m pipeline.base_foto --descargar   # baja las ventanas que faltan y arma la imagen",
            "uv run python -m pipeline.base_foto --verificar   # compara data/base_foto.json con los dos archivos WebP",
        ]
    if exactitud is not None:
        L += [
            "uv run --with pillow python -m pipeline.exactitud   # mide la página armada y escribe data/exactitud.json",
            "uv run --with pillow python -m pipeline.exactitud --verificar   # mide de nuevo y compara",
        ]
    L += [
        "```",
        "",
    ]
    return "\n".join(L)


# ---------- assembly ----------


def construir(raw: Path = RAW) -> dict:
    """Check every pin and return the product dict."""
    rel, hs = construir_relieve(raw)
    fs_r, hr = capa_ign("lineas_de_aguas_continentales_perenne", raw)
    r = construir_rios(fs_r)
    ha, grupos = {}, []
    for capa, tipo, minimo in ORDEN_AGUA:
        fs, ha[capa] = capa_ign(capa, raw)
        grupos.append((fs, tipo, minimo))
    a = construir_agua(grupos)
    fs_li, hl = capa_ign("linea_de_limite_070111", raw)
    li = construir_limites(fs_li)
    fs_lo, hlo = capa_ign("localidad_bahra", raw)
    lo = construir_localidades(fs_lo)
    datos_zip = _leer_bytes(raw / "energia" / ZIP_NOMBRE, ZIP_NOMBRE)
    bl = construir_bloques(datos_zip)
    fuentes = construir_fuentes(hs, hr, ha, hl, hlo, _sha(datos_zip))
    return {"v": 1, "caja": list(CAJA), "q": Q, "relieve": rel, "rios": r, "agua": a,
            "limites": li, "localidades": lo, "bloques": bl, "fuentes": fuentes}


def serializar(base: dict) -> str:
    """Serialise the product dict to its exact bytes (as text with trailing newline)."""
    return json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def descargar(raw: Path = RAW) -> list[str]:
    """Fetch the missing sources (temp file, then atomic rename). Returns what it fetched."""
    pendientes = ([(SKADI.format(d=n[:3], w=n[3:]), raw / "skadi" / f"{n}.hgt.gz") for n in TILES]
                  + [(IGN + capa, raw / "ign" / f"{capa}.geojson") for capa in CAPAS_IGN]
                  + [(SHP, raw / "energia" / ZIP_NOMBRE)])
    fetched = []
    for url, destino in pendientes:
        if destino.exists():
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "vaca-muerta-data/0.1"})
        with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as out:
            tmp = Path(out.name)
            try:
                size = 0
                with urllib.request.urlopen(req, timeout=600) as resp:
                    while trozo := resp.read(1 << 20):
                        size += len(trozo)
                        out.write(trozo)
                if size == 0:
                    raise RuntimeError(f"{url}: empty download")
                out.flush()
                tmp.replace(destino)  # atomic: a crash never leaves a half-written source
            finally:
                tmp.unlink(missing_ok=True)  # a failed or empty download leaves nothing behind
        fetched.append(destino.relative_to(raw).as_posix())
    return fetched


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pipeline.base_mapa", description="Build the base map product.")
    ap.add_argument("--descargar", action="store_true", help="fetch the missing sources first")
    ap.add_argument("--verificar", action="store_true",
                    help="compare with the two products and the wiki page, never write")
    ap.add_argument("--salida", type=Path, default=None, help="write the product somewhere else, leave the page alone")
    ap.add_argument("--pagina", action="store_true", help="rewrite only the wiki page from data/base_mapa.json")
    args = ap.parse_args(argv)
    if args.pagina:
        PAGINA.write_text(pagina(json.loads(DESTINO.read_text(encoding="utf-8")), leer_foto(), leer_fino(),
                                 leer_exactitud()), encoding="utf-8")
        print(f"wrote {PAGINA}")
        return 0
    if args.descargar:
        descargar()
    base, fino = construir(), construir_relieve_fino()
    datos, datos_fino = serializar(base).encode("utf-8"), serializar(fino).encode("utf-8")
    texto = pagina(base, leer_foto(), fino, leer_exactitud()).encode("utf-8")
    h = _sha(datos)
    if args.verificar:
        distintos = [str(ruta.relative_to(ROOT))
                     for ruta, esperado in ((DESTINO, datos), (FINO, datos_fino), (PAGINA, texto))
                     if not ruta.exists() or ruta.read_bytes() != esperado]
        if not distintos:
            print(f"verificar ok bytes {len(datos)} sha256 {h}")
            return 0
        print(f"verificar difieren ({', '.join(distintos)}) bytes {len(datos)} sha256 {h}")
        return 1
    if args.salida:
        args.salida.write_bytes(datos)
    else:
        DESTINO.write_bytes(datos)
        FINO.write_bytes(datos_fino)
        PAGINA.write_bytes(texto)
    print(f"bytes {len(datos)} sha256 {h}")
    print(f"relieve fino bytes {len(datos_fino)} sha256 {_sha(datos_fino)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

