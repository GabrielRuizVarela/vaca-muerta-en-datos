"""How accurately the Mundo page places things: its relief, its wells and its drawing.

It measures the published page itself. Everything it needs about the page comes out of the data embedded in
site/mundo.html: the wellheads, the two relief grids, the water outlines and the ground image. Three checks:

  * relief: the height the page draws at each wellhead against the one-arc-second SRTM source (the pinned tiles
    of pipeline.base_mapa), the same at named summits and reservoir surfaces, and both against a pinned sample
    of an independent elevation model (data/exactitud_glo90.json);
  * image: where the published wellheads fall on the ground image (a stack of image patches centred on each
    pad, which peaks where the image shows a location) and the water outlines against the image's own water;
  * drawing: how much the flat drawing of the page stretches distances, from its two constants.

The result goes to data/exactitud.json. The wiki page of the base map quotes it (pipeline.base_mapa --pagina)
and pipeline.claims pins every number quoted. Order: base map products, the page, this, then the wiki page.

Needs data/raw/base_mapa/skadi and Pillow (to decode the image; numpy does the rest).

    python -m pipeline.exactitud               # measure and write data/exactitud.json
    python -m pipeline.exactitud --verificar   # measure and compare, never write
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import statistics
from pathlib import Path

import numpy as np

from pipeline import base_mapa

PAGINA = base_mapa.ROOT / "site" / "mundo.html"
DESTINO = base_mapa.DATA / "exactitud.json"
GLO90 = base_mapa.DATA / "exactitud_glo90.json"

KM_GRADO = 111.32            # the page's kilometres per degree, on both axes
A_WGS84, E2_WGS84 = 6378.137, 0.00669437999014
MESES_ANTES = 6              # a pad counts when a well of it produced at least this many months before the image
BORDE_GRADOS = 0.02          # pads this close to the edge of the image are left out
RADIO_PX = 20                # half side of the patch stacked around each pad
FONDO_M, CENTRO_M, PAD_M = 400.0, 300.0, 220.0
CONTROL_M = 1000.0           # the control stack looks this far east of each pad
BUSCA_PX = 8                 # how far the water outline is moved in the search for a better fit
CUMBRES = (("Volcán Auca Mahuida", (-69.1, -37.9, -68.75, -37.6)), ("Volcán Domuyo", (-70.5, -36.75, -70.3, -36.6)))
NIVELES = (("Embalse Los Barreales", -68.85, -38.55), ("Embalse Mari Menuco", -68.62, -38.58),
           ("Embalse Ezequiel Ramos Mexía", -68.85, -39.35), ("Lago Pellegrini", -68.0, -38.68))
EMBALSES = ("Embalse Los Barreales", "Embalse Mari Menuco")


def leer_pagina(ruta: Path = PAGINA) -> dict:
    """The data object embedded in the page."""
    t = ruta.read_text(encoding="utf-8")
    s = t[t.index('<script id="datos">'):]
    s = s[s.index("const DATA = ") + 13:s.index("</script>")]
    return json.loads(s.rstrip().rstrip(";"))


def fuente_en(mosaico: np.ndarray, lon: float, lat: float) -> float:
    """Bilinear height of the source at a point: its samples sit on whole arc-seconds counted from (-71, -36)."""
    x, y = (lon + 71) * 3600, (-36 - lat) * 3600
    c, f = int(math.floor(x)), int(math.floor(y))
    u, v = x - c, y - f
    q = mosaico[f:f + 2, c:c + 2].astype(float)
    return float((q[0, 0] * (1 - u) + q[0, 1] * u) * (1 - v) + (q[1, 0] * (1 - u) + q[1, 1] * u) * v)


def resumen(dif) -> dict:
    """Count and absolute-difference summary, in tenths of a metre."""
    a = np.abs(np.asarray(list(dif), dtype=float))
    return {"n": int(a.size), "mediana": round(float(np.median(a)), 1), "p90": round(float(np.percentile(a, 90)), 1),
            "p99": round(float(np.percentile(a, 99)), 1), "max": round(float(a.max()), 1)}


def medir_relieve(datos: dict, mosaico: np.ndarray, glo90: dict | None = None) -> dict:
    """The page's relief against its source at the wellheads, at named places and against the independent sample."""
    B, P = datos["base"], datos["pozos"]
    z, caja = base_mapa.decodificar_relieve(B["relieve"]), tuple(B["caja"])
    fino = base_mapa.abrir_fino(B["relieve_fino"]) if B.get("relieve_fino") else None

    def pagina(lon, lat):
        return base_mapa.cota_mixta(z, caja, fino, lon, lat)

    hoja, mixta, dentro, hoja_dentro = [], [], [], []
    for lon, lat in zip(P["lon"], P["lat"]):
        h = base_mapa.cota(z, caja, lon, lat)
        if h is None:
            continue
        s = fuente_en(mosaico, lon, lat)
        hoja.append(h - s)
        mixta.append(pagina(lon, lat) - s)
        if fino and base_mapa.peso_fino(fino["caja"], fino["margen"], lon, lat) >= 1:
            dentro.append(mixta[-1])
            hoja_dentro.append(hoja[-1])
    cumbres = []
    for nombre, (lon0, lat0, lon1, lat1) in CUMBRES:
        j0, j1 = round((lon0 + 71) * 3600), round((lon1 + 71) * 3600)
        i0, i1 = round((-36 - lat1) * 3600), round((-36 - lat0) * 3600)
        sub = mosaico[i0:i1, j0:j1]
        i, j = np.unravel_index(int(sub.argmax()), sub.shape)
        lon, lat = -71 + (j0 + int(j)) / 3600, -36 - (i0 + int(i)) / 3600
        cumbres.append({"nombre": nombre, "lon": round(lon, 4), "lat": round(lat, 4), "fuente_m": int(sub.max()),
                        "pagina_m": round(pagina(lon, lat))})
    niveles = [{"nombre": n, "fuente_m": round(fuente_en(mosaico, lon, lat)), "pagina_m": round(pagina(lon, lat))}
               for n, lon, lat in NIVELES]
    # solo_hoja and solo_hoja_nucleo are the sheet grid alone over the same wells as pozos and pozos_nucleo
    out = {"pozos": resumen(mixta), "pozos_nucleo": resumen(dentro) if dentro else None, "solo_hoja": resumen(hoja),
           "solo_hoja_nucleo": resumen(hoja_dentro) if dentro else None, "cumbres": cumbres, "niveles": niveles}
    if glo90:
        f, p = [], []
        for lon, lat, g in glo90["puntos"]:
            h = pagina(lon, lat)
            if h is not None:
                f.append(fuente_en(mosaico, lon, lat) - g)
                p.append(h - g)
        out["independiente"] = {
            "n": len(f), "fecha_consulta": glo90["fecha_consulta"],
            "fuente_mediana": round(statistics.median(f), 1), "fuente_max": round(max(abs(v) for v in f), 1),
            "pagina_mediana": round(statistics.median(p), 1), "pagina_max": round(max(abs(v) for v in p), 1)}
    return out


# ---- the wells and the water outlines on the ground image ----

def _parche(gris: np.ndarray, x: float, y: float, r: int) -> np.ndarray:
    """Bilinear patch of (2r + 1) squared pixels centred exactly on (x, y), in pixel-centre coordinates."""
    xs, ys = x + np.arange(-r, r + 1), y + np.arange(-r, r + 1)
    c, f = np.floor(xs).astype(int), np.floor(ys).astype(int)
    u, v = xs - c, (ys - f)[:, None]
    return ((gris[np.ix_(f, c)] * (1 - u) + gris[np.ix_(f, c + 1)] * u) * (1 - v)
            + (gris[np.ix_(f + 1, c)] * (1 - u) + gris[np.ix_(f + 1, c + 1)] * u) * v)


def apilar(gris: np.ndarray, puntos: list[tuple[float, float]], mx: float, my: float, r: int = RADIO_PX) -> dict:
    """Stack the image around each point, each patch in standard deviations over its own surroundings.

    Returns the mean stack, how many points went in, how many sit on ground brighter than their surroundings by
    more than one deviation, the offset of the stack's peak (metres east and north of the points) and the
    median distance from each point to the centre of the bright ground next to it.
    """
    alto, ancho = gris.shape
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    rad = np.hypot(xx * mx, yy * my)
    lejos = rad > FONDO_M
    pila, n, claros, sueltos = np.zeros((2 * r + 1, 2 * r + 1)), 0, 0, []
    for x, y in puntos:
        if not (r + 1 <= x < ancho - r - 2 and r + 1 <= y < alto - r - 2):
            continue
        p = _parche(gris, x, y, r)
        q = (p - np.median(p[lejos])) / (p[lejos].std() + 1e-6)
        pila += q
        n += 1
        claros += bool(q[r, r] > 1)
        w = np.where(rad <= PAD_M, np.clip(q, 1, None) - 1, 0)
        if w.sum() > 0:
            sueltos.append(math.hypot((w * xx).sum() / w.sum() * mx, (w * yy).sum() / w.sum() * my))
    if not n:
        return {"n": 0}
    pila /= n
    w = np.where(rad <= CENTRO_M, np.clip(pila - pila.max() / 2, 0, None), 0)
    return {"n": n, "pila": pila, "claros": claros, "este_m": float((w * xx).sum() / w.sum() * mx),
            "norte_m": float(-(w * yy).sum() / w.sum() * my),
            "suelto_mediana_m": float(np.median(sueltos)) if sueltos else None}


def mejor_corrimiento(contorno: np.ndarray, agua: np.ndarray, busca: int = BUSCA_PX) -> tuple[float, float, int, int]:
    """Overlap (intersection over union) of two masks as placed, and the best one moving the first up to busca pixels.

    Returns (as placed, best, pixels east, pixels south). A tie keeps the outline where it is.
    """
    def iou(a, b):
        return float((a & b).sum() / max(1, (a | b).sum()))

    mejor = (iou(contorno, agua), 0, 0)
    for dy in range(-busca, busca + 1):
        for dx in range(-busca, busca + 1):
            v = iou(np.roll(np.roll(contorno, dy, axis=0), dx, axis=1), agua)
            if v > mejor[0]:
                mejor = (v, dx, dy)
    return iou(contorno, agua), mejor[0], mejor[1], mejor[2]


def abrir_imagen(datos: dict, nombre: str = "nucleo") -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """The named layer of the embedded ground image as an RGB array, with its box."""
    try:
        from PIL import Image
    except ImportError as e:
        raise SystemExit("pipeline.exactitud needs Pillow to decode the ground image") from e
    capa = next(c for c in datos["foto"]["capas"] if c["nombre"] == nombre)
    im = Image.open(io.BytesIO(base64.b64decode(capa["webp"]))).convert("RGB")
    return np.asarray(im).astype(float), tuple(capa["caja"])


def mascara_agua(base: dict, caja: tuple[float, float, float, float], ancho: int, alto: int,
                 nombres: tuple[str, ...] = EMBALSES) -> np.ndarray:
    """The named water outlines of the base map drawn over the image's pixel grid (holes left out)."""
    from PIL import Image, ImageDraw
    lon0, lat0, lon1, lat1 = caja
    b0, c0, b1, c1 = base["caja"]
    lienzo = Image.new("L", (ancho, alto), 0)
    dib = ImageDraw.Draw(lienzo)
    for e in base["agua"]:
        if e.get("n") not in nombres:
            continue
        for k, s in enumerate(e["p"]):
            pts = [((b0 + x / base["q"] * (b1 - b0) - lon0) / (lon1 - lon0) * ancho,
                    (lat1 - (c1 - y / base["q"] * (c1 - c0))) / (lat1 - lat0) * alto)
                   for x, y in base_mapa.decodificar_linea(s)]
            dib.polygon(pts, fill=0 if k else 255)
    return np.asarray(lienzo) > 0


def medir_imagen(datos: dict, rgb: np.ndarray, caja: tuple[float, float, float, float],
                 contorno: np.ndarray) -> dict:
    """Where the published wellheads and the water outlines fall on the ground image."""
    P, meta = datos["pozos"], datos["meta"]
    lon0, lat0, lon1, lat1 = caja
    alto, ancho = rgb.shape[:2]
    gris = rgb.mean(axis=2)
    mx = (lon1 - lon0) / ancho * KM_GRADO * math.cos(math.radians((lat0 + lat1) / 2)) * 1000
    my = (lat1 - lat0) / alto * KM_GRADO * 1000
    mes_imagen = meta["meses"].index(datos["foto"]["desde"][:7])
    pads: dict[int, list[tuple[float, float]]] = {}
    for lon, lat, pad, m0 in zip(P["lon"], P["lat"], P["pad"], P["mes0"]):
        if (m0 is not None and m0 <= mes_imagen - MESES_ANTES
                and lon0 + BORDE_GRADOS < lon < lon1 - BORDE_GRADOS and lat0 + BORDE_GRADOS < lat < lat1 - BORDE_GRADOS):
            pads.setdefault(pad, []).append((lon, lat))
    px = [((statistics.fmean(w[0] for w in ws) - lon0) / (lon1 - lon0) * ancho - .5,
           (lat1 - statistics.fmean(w[1] for w in ws)) / (lat1 - lat0) * alto - .5) for ws in pads.values()]
    a = apilar(gris, px, mx, my)
    control = apilar(gris, [(x + CONTROL_M / mx, y) for x, y in px], mx, my)
    umbral = (gris[contorno].mean() + gris[~contorno].mean()) / 2
    ys, xs = np.where(contorno)
    y0, y1, x0, x1 = max(0, ys.min() - 40), ys.max() + 40, max(0, xs.min() - 40), xs.max() + 40
    puesto, mejor, dx, dy = mejor_corrimiento(contorno[y0:y1, x0:x1], (gris < umbral)[y0:y1, x0:x1])
    r = RADIO_PX
    return {"pixel_m": [round(mx), round(my)], "mes_imagen": datos["foto"]["desde"][:7], "meses_antes": MESES_ANTES,
            "pads": a["n"], "pico_sd": round(float(a["pila"].max()), 1),
            "pico_en_centro": bool(int(a["pila"].argmax()) == r * (2 * r + 1) + r),
            "este_m": round(a["este_m"]), "norte_m": round(a["norte_m"]),
            "claros_pct": round(100 * a["claros"] / a["n"]), "suelto_mediana_m": round(a["suelto_mediana_m"]),
            "control_km": round(CONTROL_M / 1000), "control_sd": round(float(control["pila"].max()), 1),
            "embalses": list(EMBALSES), "busca_px": BUSCA_PX,
            "agua_iou": round(puesto, 3), "agua_mejor_iou": round(mejor, 3), "agua_mejor_px": [dx, dy]}


# ---- the flat drawing ----

def grado_km(lat: float) -> tuple[float, float]:
    """Kilometres per degree on the WGS84 ellipsoid at a latitude: along the meridian and along the parallel."""
    f = math.radians(lat)
    w = math.sqrt(1 - E2_WGS84 * math.sin(f) ** 2)
    return math.radians(1) * A_WGS84 * (1 - E2_WGS84) / w ** 3, math.radians(1) * A_WGS84 * math.cos(f) / w


def deformacion(lat0: float, lat: float) -> tuple[float, float]:
    """Per cent by which the page's drawing overstates a north-south and an east-west distance at a latitude.

    The page draws every degree of latitude as KM_GRADO kilometres and every degree of longitude as KM_GRADO times
    the cosine of lat0, the latitude of its origin.
    """
    ns, eo = grado_km(lat)
    return 100 * (KM_GRADO / ns - 1), 100 * (KM_GRADO * math.cos(math.radians(lat0)) / eo - 1)


def medir_dibujo(datos: dict) -> dict:
    """The stretch of the flat drawing at its origin and at the north and south edges of the core and of the sheet."""
    lat0 = statistics.median(datos["pozos"]["lat"])
    hoja = datos["base"]["caja"]
    nucleo = next(c for c in datos["foto"]["capas"] if c["nombre"] == "nucleo")["caja"]
    ns, eo = deformacion(lat0, lat0)
    km_ns, km_eo = grado_km(lat0)
    return {"lat0": round(lat0, 4), "km_grado": KM_GRADO, "ns_pct": round(ns, 2), "eo_centro_pct": round(eo, 2),
            # half an arc-second on the ground at the origin, east and south: the shift of the sheet's relief grid
            "medio_segundo_m": [round(km_eo * 1000 / 7200), round(km_ns * 1000 / 7200)],
            "eo_nucleo_pct": [round(deformacion(lat0, nucleo[3])[1], 1), round(deformacion(lat0, nucleo[1])[1], 1)],
            "eo_hoja_pct": [round(deformacion(lat0, hoja[3])[1], 1), round(deformacion(lat0, hoja[1])[1], 1)]}


# ---- product ----

def medir(pagina: Path = PAGINA, raw: Path = base_mapa.RAW, glo90: Path = GLO90) -> dict:
    datos = leer_pagina(pagina)
    mosaico, _ = base_mapa.cargar_mosaico(raw)
    rgb, caja = abrir_imagen(datos)
    contorno = mascara_agua(datos["base"], caja, rgb.shape[1], rgb.shape[0])
    meta = datos["meta"]
    return {"v": 1,
            "pagina": {"hash_datos": meta["hash_datos"], "mes_datos": meta["mes_datos"], "pozos": meta["n_pozos"]},
            "relieve": medir_relieve(datos, mosaico, json.loads(glo90.read_text(encoding="utf-8"))),
            "imagen": medir_imagen(datos, rgb, caja, contorno), "dibujo": medir_dibujo(datos)}


def serializar(m: dict) -> str:
    return json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def leer(ruta: Path = DESTINO) -> dict | None:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pipeline.exactitud", description="Measure the accuracy of the page.")
    ap.add_argument("--verificar", action="store_true", help="compare with data/exactitud.json, never write")
    args = ap.parse_args(argv)
    texto = serializar(medir())
    if args.verificar:
        igual = DESTINO.exists() and DESTINO.read_text(encoding="utf-8") == texto
        print("verificar ok" if igual else "verificar difiere")
        return 0 if igual else 1
    DESTINO.write_text(texto, encoding="utf-8")
    print(f"wrote {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
