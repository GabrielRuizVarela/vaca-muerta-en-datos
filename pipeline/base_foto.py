"""Ground photo for the 3D world: true-colour Sentinel-2 L2A as two WebP rasters.

Usage (Pillow is needed only to encode, so run the build through uv):
    uv run --with pillow python -m pipeline.base_foto --descargar   # fetch missing windows, then build
    uv run --with pillow python -m pipeline.base_foto               # build from data/raw/base_foto only
    uv run --with pillow python -m pipeline.base_foto --descargar --fijar   # also print PINES to paste
    python -m pipeline.base_foto --verificar    # check data/base_foto.json against the files (no Pillow)

Outputs: data/base_foto_caja.webp (over CAJA), data/base_foto_nucleo.webp (over NUCLEO) and
data/base_foto.json. Image pixel (i, j) of a W x H image over the box (lon0, lat0, lon1, lat1) has its
centre at lon = lon0 + (j + 0.5) / W * (lon1 - lon0), lat = lat1 - (i + 0.5) / H * (lat1 - lat0), so row 0
is north.

Data contract of base_foto.json (written with sort_keys, indent 1, ensure_ascii False):
    v          1
    caja       CAJA as [lon0, lat0, lon1, lat1]
    nucleo     NUCLEO as [lon0, lat0, lon1, lat1]
    imagenes   {"caja": {...}, "nucleo": {...}}, each with archivo, ancho, alto, calidad, nivel (COG
               overview level it was sampled from), bytes, sha256 and sin_dato (pixels no scene covers)
    escenas    the 20 pinned scenes in ESCENAS order: id, fecha, tile, plataforma, capa (0 primary orbit,
               1 fill orbit), url of its TCI.tif and usos (the images that sampled it)
    desde, hasta, atribucion, url_licencia, catalogo, fecha_descarga, codificador

The wiki page wiki/hallazgos/mapa_base.md carries a section about this image (seccion() below). The page is
written by pipeline.base_mapa, so after a rebuild run: python -m pipeline.base_mapa --pagina

Processing, per image:
  1. Each scene is a Cloud-Optimized GeoTIFF (TCI.tif, 8-bit RGB, deflate + horizontal predictor) read
     over HTTPS range requests. The target pixel centres are projected to EPSG:32719 (UTM 19S, Krueger
     series); those inside the tile pick a window at the chosen overview level, padded by the feather
     radius, and only the 512 px blocks that touch it are fetched. The block-aligned window is cached
     under data/raw/base_foto as .npy and pinned by the sha256 of its bytes (PINES, FuenteCambiada).
  2. Feather weight: w = clip(2 * boxblur(valid) - 1, 0, 1) * valid, with a square box of radius
     FUNDIDO_KM, so a scene fades to zero at nodata edges and tile borders.
  3. Bilinear sampling of the premultiplied pair (rgb * w, w), so nodata never darkens a seam.
  4. Per capa colour = sum(rgb * w) / sum(w), alpha = clip(sum(w), 0, 1); final = alpha0 * colour0 +
     (1 - alpha0) * colour1. Where the fill capa has no data the primary colour is used instead of
     black. Pixels no capa covers stay black and are counted in sin_dato.
  5. Pillow encodes lossy WebP (quality CALIDAD, method 6).
"""

import argparse
import hashlib
import json
import math
import struct
import tempfile
import threading
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from pipeline.base_mapa import CAJA, NUCLEO, FuenteCambiada
from pipeline.ingest import DATA

TAM = {"caja": (3072, 3072), "nucleo": (3072, 2304)}  # (width, height)
CALIDAD = {"caja": 70, "nucleo": 80}
NIVEL = {"caja": 3, "nucleo": 1}  # IFD index (overview level) each image samples from
FUNDIDO_KM = 6.0
LADO_M = 109800.0  # a Sentinel-2 tile is 109800 m wide and high
BASE = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/"
CABECERA = 65536
RAW = DATA / "raw" / "base_foto"
DESTINO = DATA / "base_foto.json"
ATRIBUCION = "Contains modified Copernicus Sentinel data 2025"
URL_LICENCIA = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"
CATALOGO = "https://earth-search.aws.element84.com/v1"
FECHA_DESCARGA = "2026-11-19"
PLATAFORMAS = {"S2A": "Sentinel-2A", "S2B": "Sentinel-2B", "S2C": "Sentinel-2C"}

# (id, acquisition time, capa): capa 0 is the primary orbit, capa 1 the fill orbit.
ESCENAS = (
    ("S2A_19HDS_20251229_0_L2A", "2025-12-29T14:34:11Z", 0),
    ("S2A_19HDT_20251229_0_L2A", "2025-12-29T14:33:56Z", 0),
    ("S2A_19HDU_20251229_0_L2A", "2025-12-29T14:33:43Z", 0),
    ("S2A_19HES_20251229_0_L2A", "2025-12-29T14:34:08Z", 0),
    ("S2A_19HET_20251229_0_L2A", "2025-12-29T14:33:53Z", 0),
    ("S2A_19HEU_20251229_0_L2A", "2025-12-29T14:33:39Z", 0),
    ("S2A_19HEV_20251229_0_L2A", "2025-12-29T14:33:24Z", 0),
    ("S2A_19HFS_20251229_0_L2A", "2025-12-29T14:34:04Z", 0),
    ("S2A_19HFT_20251229_0_L2A", "2025-12-29T14:33:49Z", 0),
    ("S2A_19HFU_20251229_0_L2A", "2025-12-29T14:33:35Z", 0),
    ("S2A_19HFV_20251229_0_L2A", "2025-12-29T14:33:20Z", 0),
    ("S2C_19HCS_20251230_0_L2A", "2025-12-30T14:43:57Z", 1),
    ("S2C_19HCT_20251230_0_L2A", "2025-12-30T14:43:43Z", 1),
    ("S2C_19HCU_20251230_0_L2A", "2025-12-30T14:43:28Z", 1),
    ("S2C_19HCV_20251230_0_L2A", "2025-12-30T14:43:14Z", 1),
    ("S2C_19HDS_20251230_0_L2A", "2025-12-30T14:43:54Z", 1),
    ("S2C_19HDT_20251230_0_L2A", "2025-12-30T14:43:39Z", 1),
    ("S2C_19HDU_20251230_0_L2A", "2025-12-30T14:43:25Z", 1),
    ("S2C_19HDV_20251230_0_L2A", "2025-12-30T14:43:10Z", 1),
    ("S2C_19HEV_20251230_0_L2A", "2025-12-30T14:43:06Z", 1),
)

# cache file name of every scene window -> sha256 of its array bytes (fill with --fijar)
PINES: dict[str, str] = {
    "S2A_19HDS_20251229_0_L2A_n1_3584_0_5490_512.npy": "bfd0a2bfe739bdde34bcd3b3964c19414dea9c026342551e258639adfba45198",
    "S2A_19HDS_20251229_0_L2A_n3_0_0_1373_1373.npy": "681a8c9050aa482b37b5a55c1c14d803429786911377eecbea2dc194d922b7e2",
    "S2A_19HDT_20251229_0_L2A_n1_3584_512_5490_5490.npy": "cb27cfe8a8204ed9874d4ddabdd4dff44ecd194b2219e8a2d844963c5f223683",
    "S2A_19HDT_20251229_0_L2A_n3_0_0_1373_1373.npy": "0aaf2f8396cee1789d377a3fecc8285bfc461093466a3cda4f76690d778f1e9f",
    "S2A_19HDU_20251229_0_L2A_n3_0_0_1373_1373.npy": "dd808335b59b1ecb75ff4d9cbf4f936d7e229d09568703bc0014a4b1d5a0443e",
    "S2A_19HES_20251229_0_L2A_n1_0_0_3584_512.npy": "5d0ef80fcde8b979091a1ef7fcb523ea9c2413b7ae2aec47014b0f69a253edb3",
    "S2A_19HES_20251229_0_L2A_n3_0_0_1373_1373.npy": "d7af44ea667462cac8db527e9aa392a726ac4ace31799e71ae8fe78e384b8c13",
    "S2A_19HET_20251229_0_L2A_n1_0_512_4096_5490.npy": "0652e1ee60ab5beab0e2615fc0c18fbcb847322e78a37e0d808cb85a43b7c1db",
    "S2A_19HET_20251229_0_L2A_n3_0_0_1373_1373.npy": "15d2556318399d515c850a7c0d4466f5e5304a0b16d03996c1323093b560322e",
    "S2A_19HEU_20251229_0_L2A_n3_0_0_1373_1373.npy": "850e2e4dec758aa154986a2d6d14505a05654c20bdd41faae2100d57e2149610",
    "S2A_19HEV_20251229_0_L2A_n3_0_512_1373_1373.npy": "379fa19ff8c716ba03e50c921a9da540c580c18356645796b6373c6ab4cc8dc1",
    "S2A_19HFS_20251229_0_L2A_n3_0_0_512_1373.npy": "72da071ac63eba3549ee3704df0db513b6ab1b85b06077d08a232ab6e33b2067",
    "S2A_19HFT_20251229_0_L2A_n3_0_0_512_1373.npy": "c518c53c41421ef99b9ff1eadc09cb9af895788ef222d7ee803ea7a09067d787",
    "S2A_19HFU_20251229_0_L2A_n3_0_0_512_1373.npy": "3e65a9257c852125d202c8cedf65933b4411337f9855cf7e85bbda1a71795fcd",
    "S2A_19HFV_20251229_0_L2A_n3_0_512_512_1373.npy": "b2505d7b344f92ba70f20bd44dc555726a6a2d54f8f205ac516058c71f5deafe",
    "S2C_19HCS_20251230_0_L2A_n3_512_0_1373_1373.npy": "b8e96d27e890b9e07d809dd7d4b62f57c68c2b638cf0daae7e2f14d4c73bba6a",
    "S2C_19HCT_20251230_0_L2A_n3_512_0_1373_1373.npy": "0468739d00cfc7f1ff732361c7dce6aeddcfe0e5da1d1efdaeefa65038e1d9ce",
    "S2C_19HCU_20251230_0_L2A_n3_512_0_1373_1373.npy": "e454395c5847191520f4dd5dbd5e57b000173af5f0d795b2b20c28c802850342",
    "S2C_19HCV_20251230_0_L2A_n3_512_512_1373_1373.npy": "d110696e76e017788e5b55a768b45c4c2cdb61d92d12ac33c068a14a94b21dfc",
    "S2C_19HDS_20251230_0_L2A_n1_3584_0_5490_512.npy": "0e87b534637385ea9db0b0728a42a873091c09ea4ecd5cc6cc8c0d370cae14fb",
    "S2C_19HDS_20251230_0_L2A_n3_0_0_1373_1373.npy": "3a79864a0be9280e26f9765afd3fa2fb5113375f3c8c54bae67b0166e33b209e",
    "S2C_19HDT_20251230_0_L2A_n1_3584_512_5490_5490.npy": "65e849939997b851c1d7a4104b9a057d48665161cf7e377f98e72a9c2ac27254",
    "S2C_19HDT_20251230_0_L2A_n3_0_0_1373_1373.npy": "dd0859a1c4908a3cdc299eef9d9698ecc20bc3bbe2a2158e039bd068c0c77994",
    "S2C_19HDU_20251230_0_L2A_n3_0_0_1373_1373.npy": "973f37fb8d914030fc1e43df2885f1e6b89fe1e1f28e55667caf42f2cff683a2",
    "S2C_19HDV_20251230_0_L2A_n3_0_512_1373_1373.npy": "28364a1ab634de7a64ffcea7409edb27941c1111dedab79c2466ad13b666678e",
    "S2C_19HEV_20251230_0_L2A_n3_0_512_1373_1373.npy": "59b335a9ae9caed45aafc6e846984414937f31d6d305b85c6c1dfe0f4fba0d3a",
}

_CANDADO = threading.Lock()
_DESCARGADO = [0]  # bytes fetched over HTTP in this run


def _sha(datos) -> str:
    return hashlib.sha256(datos).hexdigest()


# ---------------------------------------------------------------- projection

_A = 6378137.0
_F = 1 / 298.257223563
_N3 = _F / (2 - _F)
_E = (_F * (2 - _F)) ** 0.5
_AA = _A / (1 + _N3) * (1 + _N3**2 / 4 + _N3**4 / 64)
_ALFA = (
    _N3 / 2 - 2 * _N3**2 / 3 + 5 * _N3**3 / 16 + 41 * _N3**4 / 180,
    13 * _N3**2 / 48 - 3 * _N3**3 / 5 + 557 * _N3**4 / 1440,
    61 * _N3**3 / 240 - 103 * _N3**4 / 140,
    49561 * _N3**4 / 161280,
)


def utm19s(lon, lat):
    """Forward transverse Mercator (Krueger series) of WGS 84 degrees to EPSG:32719 (E, N) metres."""
    fi = np.radians(np.asarray(lat, dtype=np.float64))
    dl = np.radians(np.asarray(lon, dtype=np.float64) + 69.0)
    sf = np.sin(fi)
    t = np.sinh(np.arctanh(sf) - _E * np.arctanh(_E * sf))
    xi = np.arctan2(t, np.cos(dl))
    eta = np.arcsinh(np.sin(dl) / np.sqrt(t * t + np.cos(dl) ** 2))
    xs, es = xi.copy(), eta.copy()
    for j, a in enumerate(_ALFA, start=1):
        xs += a * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
        es += a * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
    return 500000.0 + 0.9996 * _AA * es, 10000000.0 + 0.9996 * _AA * xs


# ---------------------------------------------------------------- COG reader

_TIPOS = {1: ("u1", 1), 2: ("u1", 1), 3: ("<u2", 2), 4: ("<u4", 4), 12: ("<f8", 8)}


class _Insuficiente(Exception):
    """The header buffer ends before something the IFDs point to."""

    def __init__(self, fin: int):
        super().__init__(fin)
        self.fin = fin


def leer_ifds(buf: bytes) -> list[dict]:
    """Parse the IFD chain of a little-endian classic TIFF held in buf (header plus offset arrays)."""
    if buf[:2] != b"II" or struct.unpack_from("<H", buf, 2)[0] != 42:
        raise ValueError("not a little-endian classic TIFF")

    def tomar(off, n):
        if off + n > len(buf):
            raise _Insuficiente(off + n)
        return buf[off:off + n]

    ifds, off = [], struct.unpack_from("<I", buf, 4)[0]
    while off and len(ifds) < 16:
        n = struct.unpack("<H", tomar(off, 2))[0]
        crudo = tomar(off + 2, 12 * n + 4)
        tags = {}
        for k in range(n):
            tag, tipo, cuenta, valor = struct.unpack_from("<HHI4s", crudo, 12 * k)
            if tipo not in _TIPOS:
                continue
            dt, tam = _TIPOS[tipo]
            if cuenta * tam <= 4:
                datos = valor[:cuenta * tam]
            else:
                datos = tomar(struct.unpack("<I", valor)[0], cuenta * tam)
            tags[tag] = np.frombuffer(datos, dtype=dt)
        escalar = lambda t, d=None: int(tags[t][0]) if t in tags else d  # noqa: E731
        ifds.append({
            "ancho": escalar(256), "alto": escalar(257), "tw": escalar(322), "th": escalar(323),
            "offsets": tags[324].astype(np.int64), "counts": tags[325].astype(np.int64),
            "compresion": escalar(259, 1), "predictor": escalar(317, 1),
            "muestras": escalar(277, 1), "planar": escalar(284, 1),
            "escala": tags[33550].astype(float) if 33550 in tags else None,
            "tiepoint": tags[33922].astype(float) if 33922 in tags else None,
        })
        off = struct.unpack_from("<I", crudo, 12 * n)[0]
    return ifds


def cabecera(leer_rango, tam: int = CABECERA) -> tuple[bytes, list[dict]]:
    """Read the file head and parse its IFDs; fetch more only if an array lies beyond it."""
    while True:
        buf = leer_rango(0, tam)
        try:
            return buf, leer_ifds(buf)
        except _Insuficiente as e:
            if len(buf) < tam:
                raise ValueError("truncated TIFF") from None
            tam = max(e.fin, tam * 2)


def _tile(ifd: dict, leer_rango, idx: int) -> np.ndarray:
    comp = leer_rango(int(ifd["offsets"][idx]), int(ifd["counts"][idx]))
    datos = zlib.decompress(comp)
    th, tw, m = ifd["th"], ifd["tw"], ifd["muestras"]
    a = np.frombuffer(datos, dtype=np.uint8).reshape(th, tw, m)
    if ifd["predictor"] == 2:
        a = np.cumsum(a, axis=1, dtype=np.uint8)  # wraps mod 256, like the encoder
    return a


def leer_ventana(ifd: dict, leer_rango, x0: int, y0: int, x1: int, y1: int, hilos: int = 8) -> np.ndarray:
    """Decode the window [x0, x1) x [y0, y1) of one level into a (rows, cols, 3) uint8 array.

    leer_rango(offset, length) -> bytes is the byte-range fetcher, so tests need no network.
    """
    if ifd["compresion"] not in (8, 32946) or ifd["planar"] != 1 or ifd["muestras"] != 3:
        raise ValueError("unsupported TIFF layout (need deflate, chunky RGB)")
    th, tw = ifd["th"], ifd["tw"]
    ntx = -(-ifd["ancho"] // tw)
    celdas = [(ty, tx) for ty in range(y0 // th, (y1 - 1) // th + 1) for tx in range(x0 // tw, (x1 - 1) // tw + 1)]
    with ThreadPoolExecutor(hilos) as pool:
        tiles = list(pool.map(lambda c: _tile(ifd, leer_rango, c[0] * ntx + c[1]), celdas))
    out = np.zeros((y1 - y0, x1 - x0, 3), dtype=np.uint8)
    for (ty, tx), t in zip(celdas, tiles, strict=True):
        ya, xa = max(y0, ty * th), max(x0, tx * tw)
        yb, xb = min(y1, (ty + 1) * th), min(x1, (tx + 1) * tw)
        out[ya - y0:yb - y0, xa - x0:xb - x0] = t[ya - ty * th:yb - ty * th, xa - tx * tw:xb - tx * tw]
    return out


# ---------------------------------------------------------------- HTTP

def _pedir(url: str, offset: int, largo: int) -> bytes:
    """One HTTP range request, retried up to 3 times."""
    req = urllib.request.Request(url, headers={"User-Agent": "map-builder/0.1",
                                               "Range": f"bytes={offset}-{offset + largo - 1}"})
    ultimo = None
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status != 206:
                    raise RuntimeError(f"{url}: expected HTTP 206, got {resp.status}")
                datos = resp.read()
            with _CANDADO:
                _DESCARGADO[0] += len(datos)
            return datos
        except Exception as e:  # noqa: BLE001 - network errors come in many classes
            ultimo = e
            time.sleep(1 + intento)
    raise RuntimeError(f"{url}: range {offset}+{largo} failed 3 times: {ultimo}") from ultimo


def _lector_http(url: str):
    return lambda offset, largo: _pedir(url, offset, largo)


def _escribir_atomico(ruta: Path, escribir) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=ruta.parent, delete=False) as out:
        tmp = Path(out.name)
        try:
            escribir(out)
            out.flush()
            tmp.replace(ruta)
        finally:
            tmp.unlink(missing_ok=True)


def url_escena(eid: str) -> str:
    """URL of the TCI.tif of a scene id like S2A_19HDT_20251229_0_L2A."""
    _, tile, fecha, _, _ = eid.split("_")
    return f"{BASE}{tile[:2]}/{tile[2]}/{tile[3:]}/{fecha[:4]}/{int(fecha[4:6])}/{eid}/TCI.tif"


# ---------------------------------------------------------------- image maths

def pesos(rgb: np.ndarray, radio: int) -> np.ndarray:
    """Feather weight of a window: 0 on nodata and at its borders, 1 from `radio` px inside."""
    valido = (rgb > 0).any(axis=2)
    h, w = valido.shape
    s = np.zeros((h + 2 * radio + 1, w + 2 * radio + 1), dtype=np.int32)
    relleno = np.zeros((h + 2 * radio, w + 2 * radio), dtype=np.int32)
    relleno[radio:radio + h, radio:radio + w] = valido
    np.cumsum(relleno, axis=0, out=relleno)
    np.cumsum(relleno, axis=1, out=relleno)
    s[1:, 1:] = relleno
    del relleno
    d = 2 * radio + 1
    suma = (s[d:, d:] - s[:h, d:] - s[d:, :w] + s[:h, :w]).astype(np.float32)
    media = suma / np.float32(d * d)
    return (np.clip(2 * media - 1, 0, 1) * valido).astype(np.float32)


def acumular(num: np.ndarray, den: np.ndarray, idx: np.ndarray, x: np.ndarray, y: np.ndarray,
             rgb: np.ndarray, w: np.ndarray, trozo: int = 1 << 20) -> None:
    """Add the bilinear sample of the premultiplied (rgb * w, w) at window coords (x, y) to num, den.

    num is (n, 3) float32 and den (n,) float32; idx gives the flat target index of each point.
    """
    h, ancho = w.shape
    for a in range(0, idx.size, trozo):
        sl = slice(a, a + trozo)
        xs, ys = x[sl], y[sl]
        ix, iy = np.floor(xs).astype(np.int64), np.floor(ys).astype(np.int64)
        fx, fy = (xs - ix).astype(np.float32), (ys - iy).astype(np.float32)
        n3 = np.zeros((ix.size, 3), dtype=np.float32)
        d1 = np.zeros(ix.size, dtype=np.float32)
        for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1)):
            p = (fx if dx else 1 - fx) * (fy if dy else 1 - fy)
            yy, xx = np.clip(iy + dy, 0, h - 1), np.clip(ix + dx, 0, ancho - 1)
            pw = p * w[yy, xx]
            n3 += rgb[yy, xx].astype(np.float32) * pw[:, None]
            d1 += pw
        num[idx[sl]] += n3
        den[idx[sl]] += d1


def componer(num0, den0, num1, den1):
    """Compose the primary (0) and fill (1) capas into uint8 rgb. Returns (rgb, sin_dato)."""
    def color(num, den):
        return np.where(den[..., None] > 0, num / np.maximum(den, 1e-12)[..., None], 0.0)

    c0, c1 = color(num0, den0), color(num1, den1)
    c1 = np.where(den1[..., None] > 0, c1, c0)  # no fill data: keep the primary colour, never black
    a0 = np.clip(den0, 0, 1)[..., None]
    final = a0 * c0 + (1 - a0) * c1
    sin_dato = int(((den0 <= 0) & (den1 <= 0)).sum())
    return np.rint(np.clip(final, 0, 255)).astype(np.uint8), sin_dato


# ---------------------------------------------------------------- build

def _rejilla(caja, ancho: int, alto: int, fila: int = 256):
    """Flat UTM (E, N) of every target pixel centre, computed in row chunks."""
    lon0, lat0, lon1, lat1 = caja
    lon = lon0 + (np.arange(ancho) + 0.5) / ancho * (lon1 - lon0)
    lat = lat1 - (np.arange(alto) + 0.5) / alto * (lat1 - lat0)
    e = np.empty((alto, ancho))
    n = np.empty((alto, ancho))
    for i in range(0, alto, fila):
        e[i:i + fila], n[i:i + fila] = utm19s(lon[None, :], lat[i:i + fila, None])
    return e.ravel(), n.ravel()


def _cabecera_escena(eid: str, descargar: bool) -> list[dict]:
    ruta = RAW / f"{eid}.cab"
    if not ruta.exists():
        if not descargar:
            raise FileNotFoundError(f"missing {ruta}, run with --descargar to fetch it")
        buf, _ = cabecera(_lector_http(url_escena(eid)))
        _escribir_atomico(ruta, lambda f: f.write(buf))
    return leer_ifds(ruta.read_bytes())


def _ventana(x, y, radio: int, ifd: dict) -> tuple[int, int, int, int]:
    """Block-aligned window (x0, y0, x1, y1) covering the sample points plus the feather padding."""
    pad = radio + 2
    x0, x1 = int(np.floor(x.min())) - pad, int(np.floor(x.max())) + 2 + pad
    y0, y1 = int(np.floor(y.min())) - pad, int(np.floor(y.max())) + 2 + pad
    tw, th = ifd["tw"], ifd["th"]
    return (max(0, x0 // tw * tw), max(0, y0 // th * th),
            min(ifd["ancho"], -(-x1 // tw) * tw), min(ifd["alto"], -(-y1 // th) * th))


def _cargar_ventana(eid: str, nivel: int, ifd: dict, v, descargar: bool, fijar: bool, nuevos: dict) -> np.ndarray:
    nombre = f"{eid}_n{nivel}_{v[0]}_{v[1]}_{v[2]}_{v[3]}.npy"
    ruta = RAW / nombre
    if ruta.exists():
        arr = np.load(ruta)
    elif descargar:
        arr = np.ascontiguousarray(leer_ventana(ifd, _lector_http(url_escena(eid)), *v))
        _escribir_atomico(ruta, lambda f: np.save(f, arr))
    else:
        raise FileNotFoundError(f"missing {ruta}, run with --descargar to fetch it")
    h = _sha(arr.reshape(-1))
    if nombre in PINES:
        if h != PINES[nombre]:
            raise FuenteCambiada(f"window {nombre} changed: expected {PINES[nombre]}, found {h}")
    elif fijar:
        nuevos[nombre] = h
    else:
        raise FuenteCambiada(f"window {nombre} is not pinned, run with --fijar and paste PINES")
    return arr


def construir_imagen(nombre: str, caja, descargar: bool = False, fijar: bool = False, nuevos: dict | None = None):
    """Build one image. Returns (rgb array (alto, ancho, 3), sin_dato, ids of the scenes it used)."""
    nuevos = {} if nuevos is None else nuevos
    ancho, alto = TAM[nombre]
    nivel = NIVEL[nombre]
    e, n = _rejilla(caja, ancho, alto)
    total = ancho * alto
    num = np.zeros((2, total, 3), dtype=np.float32)
    den = np.zeros((2, total), dtype=np.float32)
    usos = []
    for eid, _, capa in ESCENAS:
        ifds = _cabecera_escena(eid, descargar)
        ifd = ifds[nivel]
        e0, n0 = ifds[0]["tiepoint"][3], ifds[0]["tiepoint"][4]
        idx = np.flatnonzero((e >= e0) & (e < e0 + LADO_M) & (n <= n0) & (n > n0 - LADO_M))
        if idx.size == 0:
            continue
        res = LADO_M / ifd["ancho"]
        x, y = (e[idx] - e0) / res - 0.5, (n0 - n[idx]) / res - 0.5
        radio = round(FUNDIDO_KM * 1000 / res)
        v = _ventana(x, y, radio, ifd)
        rgb = _cargar_ventana(eid, nivel, ifd, v, descargar, fijar, nuevos)
        w = pesos(rgb, radio)
        acumular(num[capa], den[capa], idx, x - v[0], y - v[1], rgb, w)
        del rgb, w
        usos.append(eid)
        print(f"  {nombre}: {eid} capa {capa} nivel {nivel} ventana {v} puntos {idx.size}", flush=True)
    del e, n
    out = np.empty((total, 3), dtype=np.uint8)
    sin_dato = 0
    for a in range(0, total, 1 << 20):
        sl = slice(a, a + (1 << 20))
        out[sl], s = componer(num[0, sl], den[0, sl], num[1, sl], den[1, sl])
        sin_dato += s
    return out.reshape(alto, ancho, 3), sin_dato, usos


def codificar(rgb: np.ndarray, calidad: int) -> bytes:
    """Encode lossy WebP with Pillow (imported here so the other commands do not need it)."""
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Pillow is missing, run with: uv run --with pillow python -m pipeline.base_foto") from None
    import io
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, "WEBP", quality=calidad, method=6)
    return buf.getvalue()


def _codificador() -> str:
    import PIL
    from PIL import features
    return f"Pillow {PIL.__version__}, libwebp {features.version('webp')}"


def construir(descargar: bool = False, fijar: bool = False) -> dict:
    """Build both images and write the webp files and data/base_foto.json."""
    nuevos: dict = {}
    imagenes, usos_por_escena = {}, {}
    for nombre, caja in (("caja", CAJA), ("nucleo", NUCLEO)):
        rgb, sin_dato, usos = construir_imagen(nombre, caja, descargar, fijar, nuevos)
        datos = codificar(rgb, CALIDAD[nombre])
        archivo = f"base_foto_{nombre}.webp"
        (DATA / archivo).write_bytes(datos)
        ancho, alto = TAM[nombre]
        imagenes[nombre] = {"archivo": archivo, "ancho": ancho, "alto": alto, "calidad": CALIDAD[nombre],
                            "nivel": NIVEL[nombre], "bytes": len(datos), "sha256": _sha(datos),
                            "sin_dato": sin_dato}
        for eid in usos:
            usos_por_escena.setdefault(eid, []).append(nombre)
    escenas = [{"id": eid, "fecha": fecha, "tile": eid.split("_")[1], "plataforma": PLATAFORMAS[eid[:3]],
                "capa": capa, "url": url_escena(eid), "usos": usos_por_escena.get(eid, [])}
               for eid, fecha, capa in ESCENAS]
    dias = sorted(fecha[:10] for _, fecha, _ in ESCENAS)
    obj = {"v": 1, "caja": list(CAJA), "nucleo": list(NUCLEO), "imagenes": imagenes, "escenas": escenas,
           "desde": dias[0], "hasta": dias[-1], "atribucion": ATRIBUCION,
           "url_licencia": URL_LICENCIA, "catalogo": CATALOGO, "fecha_descarga": FECHA_DESCARGA,
           "codificador": _codificador()}
    DESTINO.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    if fijar:
        todos = {**PINES, **nuevos}
        print("PINES = {")
        for k in sorted(todos):
            print(f'    "{k}": "{todos[k]}",')
        print("}")
    return obj


# ---------------------------------------------------------------- verification

def tam_webp(datos: bytes) -> tuple[int, int]:
    """(width, height) from the header of a lossy ('VP8 ') WebP."""
    if len(datos) < 30 or datos[:4] != b"RIFF" or datos[8:12] != b"WEBP" or datos[12:16] != b"VP8 ":
        raise ValueError("not a lossy WebP")
    if datos[23:26] != b"\x9d\x01\x2a":
        raise ValueError("bad VP8 start code")
    ancho, alto = struct.unpack_from("<HH", datos, 26)
    return ancho & 0x3FFF, alto & 0x3FFF


def verificar() -> int:
    """Check data/base_foto.json against the webp files. Needs neither Pillow nor data/raw."""
    obj = json.loads(DESTINO.read_text(encoding="utf-8"))
    problemas = []
    for nombre, im in obj["imagenes"].items():
        ruta = DATA / im["archivo"]
        if not ruta.exists():
            problemas.append(f"{nombre}: {ruta.name} is missing")
            continue
        datos = ruta.read_bytes()
        if len(datos) != im["bytes"]:
            problemas.append(f"{nombre}: bytes {len(datos)} != {im['bytes']}")
        if _sha(datos) != im["sha256"]:
            problemas.append(f"{nombre}: sha256 differs")
        try:
            tam = tam_webp(datos)
        except ValueError as e:
            problemas.append(f"{nombre}: {e}")
            continue
        if tam != (im["ancho"], im["alto"]):
            problemas.append(f"{nombre}: size {tam} != {(im['ancho'], im['alto'])}")
    if problemas:
        print("verificar difieren: " + "; ".join(problemas))
        return 1
    im = obj["imagenes"]
    print(f"verificar ok caja {im['caja']['bytes']} nucleo {im['nucleo']['bytes']}")
    return 0


# ---------------------------------------------------------------- wiki section

def _metros(caja, ancho: int, alto: int) -> tuple[int, int]:
    """Approximate ground size of one pixel, (east, south) in metres, at the middle latitude of the box."""
    lon0, lat0, lon1, lat1 = caja
    grado = 111320.0
    return (round((lon1 - lon0) / ancho * grado * math.cos(math.radians((lat0 + lat1) / 2))),
            round((lat1 - lat0) / alto * grado))


def recuentos(obj: dict) -> dict[str, int]:
    """Counts printed in the wiki section; pipeline.claims pins each one against data/base_foto.json."""
    r = {"escenas": len(obj["escenas"]), "principal": sum(1 for e in obj["escenas"] if e["capa"] == 0),
         "relleno": sum(1 for e in obj["escenas"] if e["capa"] == 1)}
    for nombre in ("caja", "nucleo"):
        im = obj["imagenes"][nombre]
        este, sur = _metros(obj[nombre], im["ancho"], im["alto"])
        r.update({f"{nombre}_ancho": im["ancho"], f"{nombre}_alto": im["alto"], f"{nombre}_bytes": im["bytes"],
                  f"{nombre}_m_este": este, f"{nombre}_m_sur": sur})
    return r


def _miles(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def _grados(v: float) -> str:
    return f"{abs(v):g}".replace(".", ",")


def _dia(fecha: str) -> str:
    return "/".join(reversed(fecha[:10].split("-")))


def seccion(obj: dict) -> list[str]:
    """Lines of the "Imagen del suelo" section of wiki/hallazgos/mapa_base.md (pipeline.base_mapa writes the page)."""
    r = recuentos(obj)
    lon0, lat0, lon1, lat1 = obj["nucleo"]
    cuando = f"el {_dia(obj['desde'])}" if obj["desde"] == obj["hasta"] else f"el {_dia(obj['desde'])} y el {_dia(obj['hasta'])}"
    L = [
        "## Imagen del suelo",
        "",
        "En la lectura de suelo de `site/mundo.html` los pozos se ven sobre una imagen satelital en color real, tendida "
        "sobre el relieve de esta misma hoja. La imagen es contexto: muestra el lugar en una fecha, no mide nada, y "
        "ningún número de la página sale de ella.",
        "",
        "- Fuente: programa Copernicus de la Unión Europea, misión Sentinel-2, producto L2A en color real (TCI), leído "
        f"del catálogo abierto Earth Search de Element 84 (`{obj['catalogo']}`).",
        f"- Es un mosaico de {r['escenas']} escenas tomadas {cuando}: {r['principal']} de la órbita principal y "
        f"{r['relleno']} de la órbita vecina, que rellena la franja que la primera no cubre.",
        f"- La hoja entera mide {_miles(r['caja_ancho'])} por {_miles(r['caja_alto'])} píxeles: cada uno cubre cerca de "
        f"{r['caja_m_este']} m hacia el este y {r['caja_m_sur']} m hacia el sur.",
        f"- Un recorte más fino cubre el núcleo, de {_grados(lon0)}° a {_grados(lon1)}° de longitud oeste y de "
        f"{_grados(lat0)}° a {_grados(lat1)}° de latitud sur. Mide {_miles(r['nucleo_ancho'])} por "
        f"{_miles(r['nucleo_alto'])} píxeles: cada uno cubre cerca de {r['nucleo_m_este']} m hacia el este y "
        f"{r['nucleo_m_sur']} m hacia el sur.",
        f"- Licencia: los datos Sentinel son de uso libre y abierto (`{obj['url_licencia']}`), con esta atribución: "
        f"\"{obj['atribucion']}\". Dice \"modified\" porque las escenas se recortan, se remuestrean, se funden en sus "
        "bordes y se comprimen.",
        f"- Bajado el {_dia(obj['fecha_descarga'])}.",
        "",
        "Huella de cada archivo:",
        "",
    ]
    for nombre in ("caja", "nucleo"):
        im = obj["imagenes"][nombre]
        L.append(f"- `data/{im['archivo']}`: {_miles(im['bytes'])} bytes, sha256 `{im['sha256']}`.")
    L += [
        "",
        "La lista de las escenas, con la fecha y el satélite de cada una, está en `data/base_foto.json`. El armador "
        "(`pipeline/base_foto.py`) fija la huella de cada ventana que lee de cada escena y no corre si una cambió.",
        "",
    ]
    return L


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pipeline.base_foto", description="Build the Sentinel-2 ground photo.")
    ap.add_argument("--descargar", action="store_true", help="fetch the missing scene windows first")
    ap.add_argument("--fijar", action="store_true", help="accept unpinned windows and print PINES")
    ap.add_argument("--verificar", action="store_true", help="check data/base_foto.json against the files")
    args = ap.parse_args(argv)
    if args.verificar:
        return verificar()
    obj = construir(descargar=args.descargar, fijar=args.fijar)
    im = obj["imagenes"]
    print(f"caja {im['caja']['bytes']} bytes sin_dato {im['caja']['sin_dato']}; "
          f"nucleo {im['nucleo']['bytes']} bytes sin_dato {im['nucleo']['sin_dato']}; "
          f"descargado {_DESCARGADO[0] / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
