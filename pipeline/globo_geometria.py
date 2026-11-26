"""Geometria del globo: paises y unidades subnacionales de Natural Earth, simplificados y guardados en `data/globo_geometria.json`.

    python -m pipeline.globo_geometria PAISES.zip UNIDADES.zip     # una sola vez; el armado de la pagina lee el JSON versionado

Es una herramienta de una sola vez (no entra en `run_all`): el globo se arma sin red y sin pyshp ni shapely, que no son
dependencias del proyecto (se importan aca, adentro de `construir`). Las fuentes son dominio publico:

  * ne_110m_admin_0_countries.zip       https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip
  * ne_50m_admin_1_states_provinces.zip https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_1_states_provinces.zip
  * terminos: https://www.naturalearthdata.com/about/terms-of-use/ ("All versions of Natural Earth raster + vector map data found
    on this website are in the public domain. You may use the maps in any manner, including modifying the content and design,
    electronic dissemination, and offset printing."), leidos el 2026-11-19.

El JSON guarda el sha256 de cada zip bajado, para que quien lo regenere pueda comprobar que parte de los mismos archivos. Los
limites son los de Natural Earth tal como los dibuja, simplificados: sirven para ubicar una jurisdiccion en un globo, no para
medir una distancia ni para decir de quien es una frontera disputada.

Formato: {"fuente": {...}, "paises": {A3: {"nombre": str, "anillos": [[[lon, lat], ...], ...]}},
          "unidades": {clave: {"nombre": str, "pais": str, "anillos": [...]}}}. Coordenadas en grados con dos decimales; cada anillo
es un exterior (los huecos se omiten: ninguno cambia lo que dice el globo).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from pipeline.ingest import DATA

SALIDA = DATA / "globo_geometria.json"

URL_PAISES = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
URL_UNIDADES = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_1_states_provinces.zip"
URL_TERMINOS = "https://www.naturalearthdata.com/about/terms-of-use/"
TERMINOS = ("All versions of Natural Earth raster + vector map data found on this website are in the public domain. "
            "You may use the maps in any manner, including modifying the content and design, electronic dissemination, "
            "and offset printing.")

# Unidades subnacionales que la auditoria de fuentes nombra (clave del globo -> (pais en Natural Earth, nombre en Natural Earth)).
UNIDADES = {
    "CA-BC": ("Canada", "British Columbia"), "CA-AB": ("Canada", "Alberta"), "CA-SK": ("Canada", "Saskatchewan"),
    "CA-MB": ("Canada", "Manitoba"),
    "AU-QLD": ("Australia", "Queensland"), "AU-WA": ("Australia", "Western Australia"), "AU-NT": ("Australia", "Northern Territory"),
    "US-NM": ("United States of America", "New Mexico"), "US-UT": ("United States of America", "Utah"),
    "US-MT": ("United States of America", "Montana"), "US-OK": ("United States of America", "Oklahoma"),
    "US-ND": ("United States of America", "North Dakota"), "US-TX": ("United States of America", "Texas"),
    "US-PA": ("United States of America", "Pennsylvania"), "US-WY": ("United States of America", "Wyoming"),
    "US-CO": ("United States of America", "Colorado"),
}
TOLERANCIA_UNIDADES = 0.03   # grados (unos 3 km): el contorno se ve igual en un globo
TOLERANCIA_PAISES = 0.0      # ya vienen simplificados a 110 m


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _anillos(shape, tolerancia: float) -> list[list[list[float]]]:
    """Exteriores de un shape de pyshp, simplificados y redondeados; descarta los que quedan sin area."""
    from shapely.geometry import Polygon

    partes = list(shape.parts) + [len(shape.points)]
    salida = []
    for a, b in zip(partes[:-1], partes[1:]):
        pts = shape.points[a:b]
        if len(pts) < 4:
            continue
        # En pyshp 3 los exteriores van en sentido horario y los huecos en antihorario: area con signo > 0 = exterior.
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:])) / 2
        if area > 0:
            continue
        poly = Polygon(pts)
        if tolerancia > 0:
            poly = poly.simplify(tolerancia, preserve_topology=True)
        if poly.is_empty or poly.geom_type != "Polygon" or poly.area < 1e-4:
            continue
        salida.append([[round(x, 2), round(y, 2)] for x, y in poly.exterior.coords])
    return salida


def construir(zip_paises: Path, zip_unidades: Path) -> dict:
    import shapefile

    paises = {}
    for sr in shapefile.Reader(str(zip_paises)).shapeRecords():
        d = sr.record.as_dict()
        a3 = d["ADM0_A3"]
        if a3 in ("ATA",):          # la Antartida no entra al globo de reguladores
            continue
        anillos = _anillos(sr.shape, TOLERANCIA_PAISES)
        if anillos:
            paises[a3] = {"nombre": d["NAME"], "anillos": anillos}
    por_nombre = {(pais, nombre): clave for clave, (pais, nombre) in UNIDADES.items()}
    unidades = {}
    for sr in shapefile.Reader(str(zip_unidades)).shapeRecords():
        d = sr.record.as_dict()
        clave = por_nombre.get((d["admin"], d["name"]))
        if clave:
            unidades[clave] = {"nombre": d["name"], "pais": d["adm0_a3"], "anillos": _anillos(sr.shape, TOLERANCIA_UNIDADES)}
    falta = sorted(set(UNIDADES) - set(unidades))
    if falta:
        raise SystemExit(f"globo_geometria: no estan en Natural Earth: {falta}")
    return {
        "fuente": {"paises": {"url": URL_PAISES, "sha256": sha256(zip_paises)},
                   "unidades": {"url": URL_UNIDADES, "sha256": sha256(zip_unidades)},
                   "terminos": {"url": URL_TERMINOS, "cita": TERMINOS, "leido": "2026-11-19"},
                   "licencia": "dominio publico", "simplificacion_grados": TOLERANCIA_UNIDADES},
        "paises": dict(sorted(paises.items())), "unidades": dict(sorted(unidades.items())),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    datos = construir(Path(argv[0]), Path(argv[1]))
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"escribi {SALIDA} ({SALIDA.stat().st_size / 1024:.0f} kB): {len(datos['paises'])} paises, {len(datos['unidades'])} unidades")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
