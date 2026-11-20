"""Trayectorias de pozo publicadas: cobertura y distancia entre ramas frente a la distancia de superficie.

  uv run python -m pipeline.trayectorias   # lee la copia de data/raw que registra data/manifest.json y escribe los marts

La fuente es el conjunto "Trayectorias de Pozo Vaca Muerta" de la Secretaría de Energía (datos.energia.gob.ar, licencia
CC-BY-4.0). `pipeline.ingest` la baja con las otras dos fuentes (clave `trayectorias_pozo` del manifiesto) y este
módulo la lee después del build, porque el modelo SQL no la usa. Cada fila trae el trazado del pozo en planta (una
línea de longitud y latitud que sale de la boca) y, entre otros campos, la profundidad medida y vertical al final, el
largo declarado de la rama horizontal, la profundidad medida y vertical donde empieza a navegar la rama (PNL_MD,
PNL_TVD) y la unidad de Vaca Muerta donde navega (códigos de la Resolución 319/93: 1 es la unidad inferior, 2 y 3 la
media, 4 a 6 la superior, 0 sin dato).

Reglas, fijadas antes de mirar las distancias:
  * Duplicados: se quitan las filas idénticas. Un pozo es su idpo, o su sigla cuando el idpo es 0 (el instructivo
    pide 0 cuando la empresa no tiene el código). Si a un pozo le quedan varias versiones, vale la que tiene un inicio
    de navegación válido (0 < PNL_MD < profundidad final y PNL_TVD > 0); entre ellas, la más profunda; y entre iguales,
    la de menor huella md5 del trazado y después la de menor huella de la fila entera, para que la elección no dependa
    del orden de las filas.
  * Unión con el warehouse: idpo = dim_pozo.pozo_id. Con idpo 0, la sigla exacta cuando es única en dim_pozo. Si dos
    pozos de la fuente caen en el mismo pozo_id, vale el unido por idpo y el otro queda sin pozo_id ni unión
    ("pozo repetido").
  * Rama: el tramo final del trazado en planta con el largo declarado de la rama (HZ) o, si falta, profundidad final
    menos PNL_MD. En la rama el pozo va casi horizontal, así que su largo medido y su largo en planta coinciden. La
    rama se simplifica con Douglas-Peucker a 2 m.
  * Un pozo queda sin rama medida (con su motivo) si no se une al warehouse, si no es un pozo shale de Vaca Muerta con
    ubicación (int_pozo_ubicacion), si el trazado empieza a más de 200 m de su ubicación en el warehouse, si el trazado
    en planta es más largo que el pozo (imposible), si no hay largo de rama o si la rama es más larga que el trazado.
  * Distancias, en planta y con la misma escala que int_par_padre_hijo (111,32 km por grado y el coseno de la
    latitud del hijo): `m_min` es la menor distancia entre las dos ramas (cero si se cruzan en planta); `m_mediana` es
    la mediana, sobre puntos cada 25 m de la rama del hijo, de la distancia a la rama del padre (para dos ramas
    paralelas es el espaciamiento). `dtvd_m` es la diferencia de PNL_TVD entre los dos pozos y `misma_unidad` dice si
    navegan en la misma unidad (nulo si a alguno le falta el código).
  * Posición del padre respecto de la rama del hijo: el eje de cada rama en planta es su primera componente
    principal. Con el eje del hijo, la rama del padre queda "costado" (solapa con el 30% o más de la rama del
    hijo), "punta" (no solapa nada) o "mixto" (el resto). Se miden el solape a lo largo del eje, el desvío
    perpendicular (mediana de la distancia al eje del hijo) y el hueco axial entre las dos ramas.

Escribe mart_trayectoria_pozo (un pozo de la fuente por fila, con su rama y su motivo), mart_trayectoria_par (los pares
de int_par_padre_hijo con las dos ramas medidas), mart_trayectoria_cobertura (por año de fractura del hijo),
mart_trayectoria_banda (por banda de distancia de superficie), mart_trayectoria_cruce (banda de superficie contra
banda de rama), mart_par_rama (la posición del padre respecto de la rama del hijo) y mart_trayectoria_resumen
(clave, valor). pipeline.wiki arma wiki/hallazgos/trayectorias.md con
`pagina_trayectorias`. Es descriptivo: no estima ningún efecto de interferencia.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import duckdb
import numpy as np

from pipeline.costo import _escribir
from pipeline.ingest import DATA, MANIFEST, OTRAS, load_manifest
from pipeline.mapa import SHMAX_PUBLICADO
from pipeline.placebo import _g

CLAVE = "trayectorias_pozo"
URL = OTRAS[CLAVE]
PAQUETE = "http://datos.energia.gob.ar/dataset/f5c0b5a5-b402-44d7-8fe0-f9e4fcb78b8d"
TITULO = "Trayectorias de Pozo Vaca Muerta"
ORGANISMO = "Secretaría de Energía (Subsecretaría de Eficiencia e Información Energética)"
LICENCIA = "CC-BY-4.0"
INSTRUCTIVO = "Resolución 319/93, Planos Base, instructivo de carga de información geográfica, objeto 4.1.4.10"
COLUMNAS = ("sigla", "idpo", "profundidad_final_total_mt", "profundidad_vertical_mt", "profundidad_sidetrack_mt",
            "largo_rama_horizontal_mt", "unidad_intervalo_navegacion", "detalle_unidad_intervalo_navegacion", "pnl_md",
            "pnl_tvd", "termini", "termfin", "drilini", "drilfin", "tipopozo", "geometria", "geojson")
M_POR_GRADO = 111_320.0      # la escala de int_par_padre_hijo (111.32 km por grado)
BOCA_MAX_M = 200.0           # el trazado tiene que salir a menos de esto de la ubicación del pozo en el warehouse
TOL_M = 2.0                  # Douglas-Peucker de la rama
PASO_M = 25.0                # puntos de la rama del hijo para la separación mediana
UNIDADES = {1: "U1, Vaca Muerta inferior", 2: "U2, Vaca Muerta media", 3: "U3, Vaca Muerta media",
            4: "U4, Vaca Muerta superior", 5: "U5, Vaca Muerta superior", 6: "U6, Vaca Muerta superior"}
# bandas de distancia de superficie de un par (km) y bandas de distancia entre ramas (m_min, km)
BANDAS = (("mismo_pad", 0.0, 0.05, "menos de 50 m (mismo pad)"), ("050_500", 0.05, 0.5, "50 a 500 m"),
          ("500_1000", 0.5, 1.0, "500 m a 1 km"), ("1_2", 1.0, 2.0, "1 a 2 km"), ("2_5", 2.0, 5.0, "2 a 5 km"))
SUPERFICIE = (("cercano", 0.0, 1.0, "cercano (menos de 1 km)"), ("intermedio", 1.0, 2.0, "intermedio (1 a 2 km)"),
              ("control", 2.0, 5.0, "control (2 a 5 km)"))
RAMA = (("menos_250", 0.0, 0.25, "menos de 250 m"), ("250_1000", 0.25, 1.0, "250 m a 1 km"),
        ("1_2", 1.0, 2.0, "1 a 2 km"), ("2_mas", 2.0, math.inf, "2 km o más"))
PARALELAS_MAX_GRADOS = 20.0   # dos ejes con menos de esto de diferencia se toman como paralelos
SOLAPE_COSTADO = 0.30         # parte de la rama del hijo que el padre solapa para que la posición sea "costado"
POSICIONES = ("costado", "punta", "mixto")
MOTIVOS = ("sin pozo en el warehouse", "pozo repetido", "fuera del estudio", "boca lejos de la ubicación",
           "trazado más largo que el pozo", "sin largo de rama", "rama más larga que el trazado")

COLS_POZO = [("clave", "VARCHAR"), ("idpo", "BIGINT"), ("sigla", "VARCHAR"), ("pozo_id", "INTEGER"), ("union_por", "VARCHAR"),
             ("filas", "INTEGER"), ("versiones", "INTEGER"), ("md_m", "DOUBLE"), ("tvd_m", "DOUBLE"),
             ("rama_declarada_m", "DOUBLE"), ("pnl_md_m", "DOUBLE"), ("pnl_tvd_m", "DOUBLE"), ("unidad", "INTEGER"),
             ("detalle", "INTEGER"), ("tipopozo", "INTEGER"), ("drilini", "DATE"), ("drilfin", "DATE"),
             ("largo_plano_m", "DOUBLE"), ("boca_m", "DOUBLE"), ("rama_m", "DOUBLE"), ("rama_lon", "DOUBLE[]"),
             ("rama_lat", "DOUBLE[]"), ("motivo", "VARCHAR")]
COLS_PAR = [("hijo", "INTEGER"), ("padre", "INTEGER"), ("mes_frac", "DATE"), ("km", "DOUBLE"), ("m_min", "DOUBLE"),
            ("m_mediana", "DOUBLE"), ("dtvd_m", "DOUBLE"), ("misma_unidad", "BOOLEAN")]
COLS_PAR_RAMA = [("hijo", "INTEGER"), ("padre", "INTEGER"), ("azimut_hijo", "DOUBLE"), ("azimut_padre", "DOUBLE"),
                 ("dif_azimut", "DOUBLE"), ("paralelas", "BOOLEAN"), ("solape_frac", "DOUBLE"),
                 ("desfase_perp_m", "DOUBLE"), ("desfase_axial_m", "DOUBLE"), ("posicion", "VARCHAR"),
                 ("angulo_shmax_hijo", "DOUBLE")]
COLS_COBERTURA = [("nivel", "VARCHAR"), ("anio", "INTEGER"), ("total", "INTEGER"), ("medidos", "INTEGER"),
                  ("horizontales", "INTEGER"), ("horizontales_en_fuente", "INTEGER"), ("horizontales_medidos", "INTEGER")]
HORIZONTAL = re.compile(r"\(h\)|\dh$")  # sigla de pozo horizontal: "(h)", o el número seguido de "h"
CORTE_RECIENTE = 2024  # la página compara la cobertura de los hijos horizontales antes y desde este año
COLS_BANDA = [("banda", "VARCHAR"), ("orden", "INTEGER"), ("pares", "INTEGER"), ("medidos", "INTEGER"),
              ("m_min_p25", "DOUBLE"), ("m_min_mediana", "DOUBLE"), ("m_min_p75", "DOUBLE"), ("m_mediana_mediana", "DOUBLE"),
              ("parte_min_bajo_1km", "DOUBLE"), ("parte_misma_unidad", "DOUBLE"), ("dtvd_mediana", "DOUBLE")]
COLS_CRUCE = [("superficie", "VARCHAR"), ("rama", "VARCHAR"), ("pares", "INTEGER")]
COLS_RESUMEN = [("clave", "VARCHAR"), ("valor", "DOUBLE")]


# ---------------------------------------------------------------- geometría en planta (metros)

def a_metros(lon, lat, lon0: float, lat0: float) -> np.ndarray:
    """(n, 2) en metros desde (lon0, lat0): este con el coseno de lat0, norte con 111,32 km por grado."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    return np.column_stack([(lon - lon0) * M_POR_GRADO * math.cos(math.radians(lat0)), (lat - lat0) * M_POR_GRADO])


def _sin_repetidos(xy: np.ndarray) -> np.ndarray:
    """Quita los vértices iguales al anterior."""
    if len(xy) < 2:
        return xy
    keep = np.r_[True, np.any(np.diff(xy, axis=0) != 0, axis=1)]
    return xy[keep]


def largo(xy: np.ndarray) -> float:
    return float(np.sqrt((np.diff(xy, axis=0) ** 2).sum(1)).sum()) if len(xy) > 1 else 0.0


def tramo_final(xy: np.ndarray, metros: float) -> np.ndarray:
    """La parte final de la polilínea con `metros` de largo, desde el punto interpolado hasta el último vértice."""
    seg = np.sqrt((np.diff(xy, axis=0) ** 2).sum(1))
    desde_fin = np.r_[np.cumsum(seg[::-1])[::-1], 0.0]          # largo de cada vértice al final
    if metros >= desde_fin[0]:
        return xy.copy()
    i = int(np.nonzero(desde_fin > metros)[0][-1])             # el corte cae en el tramo i -> i+1
    t = (desde_fin[i] - metros) / seg[i]
    inicio = xy[i] + t * (xy[i + 1] - xy[i])
    return np.vstack([inicio, xy[i + 1:]])


def simplificar(xy: np.ndarray, tol: float = TOL_M) -> np.ndarray:
    """Douglas-Peucker: ningún vértice quitado queda a más de `tol` de la línea simplificada."""
    if len(xy) < 3:
        return xy.copy()
    keep = np.zeros(len(xy), bool)
    keep[0] = keep[-1] = True
    pila = [(0, len(xy) - 1)]
    while pila:
        a, b = pila.pop()
        if b - a < 2:
            continue
        d = dist_puntos_tramos(xy[a + 1:b], xy[a:a + 1], xy[b:b + 1])
        k = int(np.argmax(d))
        if d[k] > tol:
            keep[a + 1 + k] = True
            pila += [(a, a + 1 + k), (a + 1 + k, b)]
    return xy[keep]


def dist_puntos_tramos(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(n,) distancia de cada punto de p (n, 2) al más cercano de los tramos a[j] -> b[j] (m, 2)."""
    ab = b - a
    l2 = (ab ** 2).sum(1)
    ap = p[:, None, :] - a[None, :, :]
    t = np.clip((ap * ab).sum(2) / np.where(l2 > 0, l2, 1.0), 0.0, 1.0)
    d = ap - t[..., None] * ab
    return np.sqrt((d ** 2).sum(2)).min(1)


def _se_cruzan(p: np.ndarray, q: np.ndarray) -> bool:
    """Si algún tramo de p corta a uno de q en un punto interior de los dos."""
    a, b, c, d = p[:-1, None], p[1:, None], q[None, :-1], q[None, 1:]

    def cruz(o, x, y):
        return (x[..., 0] - o[..., 0]) * (y[..., 1] - o[..., 1]) - (x[..., 1] - o[..., 1]) * (y[..., 0] - o[..., 0])
    return bool(np.any((cruz(a, b, c) * cruz(a, b, d) < 0) & (cruz(c, d, a) * cruz(c, d, b) < 0)))


def distancia_minima(p: np.ndarray, q: np.ndarray) -> float:
    """Menor distancia entre dos polilíneas: cero si se cruzan; si no, la menor entre un vértice de una y un tramo de
    la otra (entre dos tramos que no se cortan, el mínimo cae siempre en un extremo de alguno)."""
    if _se_cruzan(p, q):
        return 0.0
    return float(min(dist_puntos_tramos(p, q[:-1], q[1:]).min(), dist_puntos_tramos(q, p[:-1], p[1:]).min()))


def remuestrear(xy: np.ndarray, paso: float = PASO_M) -> np.ndarray:
    """Puntos cada `paso` metros a lo largo de la polilínea, con sus dos extremos."""
    seg = np.sqrt((np.diff(xy, axis=0) ** 2).sum(1))
    acum = np.r_[0.0, np.cumsum(seg)]
    s = np.r_[np.arange(0.0, acum[-1], paso), acum[-1]]
    return np.column_stack([np.interp(s, acum, xy[:, 0]), np.interp(s, acum, xy[:, 1])])


def separacion_mediana(hijo: np.ndarray, padre: np.ndarray, paso: float = PASO_M) -> float:
    """Mediana, sobre puntos cada `paso` m de la rama del hijo, de la distancia a la rama del padre."""
    return float(np.median(dist_puntos_tramos(remuestrear(hijo, paso), padre[:-1], padre[1:])))


# ---------------------------------------------------------------- geometría del par (ejes, solape y desvíos)

def _eje_principal(xy: np.ndarray) -> np.ndarray:
    """Vector unitario del eje principal en planta: la primera componente principal de los puntos centrados."""
    p = np.asarray(xy, float)
    if len(p) < 2:
        return np.array([0.0, 1.0])
    c = p - p.mean(axis=0)
    if not np.any(c):
        return np.array([0.0, 1.0])
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    u = np.asarray(vt[0], float)
    n = float(np.hypot(u[0], u[1]))
    return u / n if n > 0 else np.array([0.0, 1.0])


def azimut_eje(xy: np.ndarray) -> float:
    """Azimut del eje principal en planta, en grados [0, 180) desde el norte en sentido horario.

    Norte sur vale 0 y este oeste vale 90; el eje es una recta, así que el sentido no cuenta."""
    u = _eje_principal(xy)
    return float(math.degrees(math.atan2(u[0], u[1])) % 180.0)


def angulo_a_shmax(az: float) -> float:
    """Menor ángulo entre un eje de azimut `az` y el SHmax publicado, como rectas: de 0 a 90 grados."""
    a = abs(float(az) - SHMAX_PUBLICADO) % 180.0
    return float(min(a, 180.0 - a))


def _dif_azimut(az1: float, az2: float) -> float:
    """Menor ángulo entre dos ejes como rectas: de 0 a 90 grados."""
    a = abs(float(az1) - float(az2)) % 180.0
    return float(min(a, 180.0 - a))


def geometria_par(h: np.ndarray, q: np.ndarray) -> dict:
    """Posición del padre `q` respecto de la rama del hijo `h`. Los dos son (n, 2) en metros, ya remuestreados.

    El eje es el del hijo (su primera componente principal) y el origen, su centroide. `solape_frac` es la parte de
    la rama del hijo que el padre cubre a lo largo de ese eje, `desfase_perp_m` la distancia mediana al eje del hijo
    sobre la parte que se solapa (nula si no hay solape) y `desfase_axial_m` el hueco entre las dos ramas a lo largo
    del eje (cero si se solapan)."""
    h = np.asarray(h, float)
    q = np.asarray(q, float)
    u = _eje_principal(h)
    c = h.mean(axis=0)

    def proyectado(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        v = p - c
        return v @ u, np.abs(u[0] * v[:, 1] - u[1] * v[:, 0])

    s_h, _ = proyectado(h)
    s_q, d_q = proyectado(q)
    h0, h1 = float(s_h.min()), float(s_h.max())
    p0, p1 = float(s_q.min()), float(s_q.max())
    az_h, az_p = azimut_eje(h), azimut_eje(q)
    dif = _dif_azimut(az_h, az_p)
    solape = max(0.0, min(h1, p1) - max(h0, p0))
    if abs(solape) < 1e-9:
        solape = 0.0
    largo = h1 - h0
    frac = solape / largo if largo > 0 else None
    dentro = (s_q >= max(h0, p0)) & (s_q <= min(h1, p1))
    perp = float(np.median(d_q[dentro])) if solape > 0 and dentro.any() else None
    axial = 0.0 if solape > 0 else float(max(h0, p0) - min(h1, p1))
    if frac is not None and frac >= SOLAPE_COSTADO:
        posicion = "costado"
    elif frac == 0:
        posicion = "punta"
    else:
        posicion = "mixto"
    return {"azimut_hijo": az_h, "azimut_padre": az_p, "dif_azimut": dif, "paralelas": dif <= PARALELAS_MAX_GRADOS,
            "solape_frac": frac, "desfase_perp_m": perp, "desfase_axial_m": axial, "posicion": posicion,
            "angulo_shmax_hijo": angulo_a_shmax(az_h)}


# ---------------------------------------------------------------- lectura y reglas

def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _entero(x) -> int | None:
    v = _num(x)
    return None if v is None else int(v)


def _fecha(x) -> str | None:
    """La fecha ISO, o None para vacíos y para el 1899-12-30 que la fuente usa como fecha nula."""
    s = (x or "").strip()[:10]
    return s if len(s) == 10 and s[:4].isdigit() and int(s[:4]) >= 1950 else None


def landing_valido(md, pnl_md, pnl_tvd) -> bool:
    return md is not None and pnl_md is not None and pnl_tvd is not None and 0 < pnl_md < md and pnl_tvd > 0


def elegir_version(versiones: list[dict]) -> dict:
    """La regla de versiones: inicio de navegación válido, después la más profunda, después la menor huella del trazado
    y, entre versiones con el mismo trazado, la menor huella de la fila entera (las filas ya son distintas)."""
    return min(versiones, key=lambda v: (not landing_valido(v["md"], v["pnl_md"], v["pnl_tvd"]), -(v["md"] or 0.0), v["huella"],
                                         v["huella_fila"]))


def largo_rama(v: dict) -> float | None:
    """El largo de la rama: HZ si es positivo; si no, profundidad final menos PNL_MD cuando el inicio es válido."""
    if v["hz"] is not None and v["hz"] > 0:
        return v["hz"]
    if v["md"] is not None and v["pnl_md"] is not None and 0 < v["pnl_md"] < v["md"]:
        return v["md"] - v["pnl_md"]
    return None


def leer_filas(con, ruta: Path) -> tuple[int, list[dict]]:
    """(filas publicadas, filas distintas como dicts). Falla si el CSV no trae las columnas esperadas."""
    lit = str(ruta).replace("'", "''")
    cols = [r[0] for r in con.execute(f"describe select * from read_csv('{lit}', all_varchar = true, header = true)").fetchall()]
    faltan = [c for c in COLUMNAS if c not in cols]
    if faltan:
        raise SystemExit(f"{ruta}: faltan columnas {faltan}; la fuente cambió de formato")
    total = con.execute(f"select count(*) from read_csv('{lit}', all_varchar = true, header = true)").fetchone()[0]
    sel = ", ".join(COLUMNAS)
    filas = con.execute(f"select distinct {sel} from read_csv('{lit}', all_varchar = true, header = true)").fetchall()
    return int(total), [dict(zip(COLUMNAS, f)) for f in filas]


def versiones_por_pozo(filas: list[dict]) -> dict[str, list[dict]]:
    """Agrupa las filas distintas por pozo de la fuente (idpo, o s:sigla si el idpo es 0) y tipa los campos."""
    pozos: dict[str, list[dict]] = {}
    for f in filas:
        idpo = _entero(f["idpo"]) or 0
        clave = str(idpo) if idpo else "s:" + (f["sigla"] or "").strip()
        g = json.loads(f["geojson"])
        lineas = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        pts = np.array([p[:2] for linea in lineas for p in linea], float)
        pozos.setdefault(clave, []).append({
            "clave": clave, "idpo": idpo, "sigla": (f["sigla"] or "").strip(), "md": _num(f["profundidad_final_total_mt"]),
            "tvd": _num(f["profundidad_vertical_mt"]), "hz": _num(f["largo_rama_horizontal_mt"]), "pnl_md": _num(f["pnl_md"]),
            "pnl_tvd": _num(f["pnl_tvd"]), "unidad": _entero(f["unidad_intervalo_navegacion"]),
            "detalle": _entero(f["detalle_unidad_intervalo_navegacion"]), "tipopozo": _entero(f["tipopozo"]),
            "drilini": _fecha(f["drilini"]), "drilfin": _fecha(f["drilfin"]), "pts": pts,
            "huella": hashlib.md5(f["geojson"].encode("utf-8")).hexdigest(),
            "huella_fila": hashlib.md5(json.dumps([f[c] for c in COLUMNAS]).encode("utf-8")).hexdigest()})
    return pozos


def procesar_pozos(pozos: dict[str, list[dict]], filas_por_clave: dict[str, int], dim: dict[int, tuple],
                   por_sigla: dict[str, int], estudio: set[int]) -> list[dict]:
    """Un registro por pozo de la fuente: versión elegida, unión, rama en planta y motivo (None = rama medida).
    `dim` es pozo_id -> (lon, lat) de dim_pozo; `por_sigla` las siglas únicas de dim_pozo; `estudio` los pozo_id de
    int_pozo_ubicacion."""
    out = []
    for clave in sorted(pozos, key=lambda k: (k.startswith("s:"), k)):
        v = elegir_version(pozos[clave])
        if v["idpo"]:
            pid, union = (v["idpo"], "idpo") if v["idpo"] in dim else (None, None)
        else:
            pid = por_sigla.get(v["sigla"])
            union = "sigla" if pid is not None else None
        r = {**v, "pozo_id": pid, "union_por": union, "filas": filas_por_clave[clave], "versiones": len(pozos[clave]),
             "largo_plano": None, "boca_m": None, "rama_m": None, "rama": None, "motivo": None}
        xy = _sin_repetidos(a_metros(v["pts"][:, 0], v["pts"][:, 1], v["pts"][0, 0], v["pts"][0, 1]))
        r["largo_plano"] = largo(xy)
        if pid is not None and dim[pid][0] is not None:
            lon, lat = dim[pid]
            r["boca_m"] = float(np.hypot(*a_metros([v["pts"][0, 0]], [v["pts"][0, 1]], lon, lat)[0]))
        rama_m = largo_rama(v)
        if pid is None:
            r["motivo"] = MOTIVOS[0]
        elif pid not in estudio:
            r["motivo"] = MOTIVOS[2]
        elif r["boca_m"] is None or r["boca_m"] > BOCA_MAX_M:
            r["motivo"] = MOTIVOS[3]
        elif v["md"] is None or r["largo_plano"] > v["md"]:
            r["motivo"] = MOTIVOS[4]
        elif rama_m is None:
            r["motivo"] = MOTIVOS[5]
        elif rama_m > r["largo_plano"]:
            r["motivo"] = MOTIVOS[6]
        else:
            r["rama_m"] = rama_m
            rama = simplificar(tramo_final(xy, rama_m))
            c = math.cos(math.radians(v["pts"][0, 1]))
            r["rama"] = (v["pts"][0, 0] + rama[:, 0] / (M_POR_GRADO * c), v["pts"][0, 1] + rama[:, 1] / M_POR_GRADO)
        out.append(r)
    # un pozo del warehouse una sola vez: vale el unido por idpo (va primero en el orden de arriba). El repetido queda
    # sin pozo_id ni unión, así que pozo_id no se repite en mart_trayectoria_pozo.
    vistos: set[int] = set()
    for r in out:
        if r["pozo_id"] is None:
            continue
        if r["pozo_id"] in vistos:
            r["motivo"], r["rama"], r["rama_m"], r["pozo_id"], r["union_por"] = MOTIVOS[1], None, None, None, None
        else:
            vistos.add(r["pozo_id"])
    return out


def medir_pares(pares: list[tuple], ramas: dict[int, tuple], boca: dict[int, tuple], atributos: dict[int, tuple]) -> list[tuple]:
    """Filas de mart_trayectoria_par para los pares (hijo, padre, mes_frac, km) con las dos ramas medidas.
    `ramas` es pozo_id -> (lon[], lat[]); `boca` pozo_id -> (lon, lat) de la superficie; `atributos` pozo_id ->
    (pnl_tvd, unidad)."""
    out = []
    cache: dict[tuple[int, int], np.ndarray] = {}
    for hijo, padre, mes, km in pares:
        if hijo not in ramas or padre not in ramas:
            continue
        lon0, lat0 = boca[hijo]
        for p in (hijo, padre):
            if (hijo, p) not in cache:
                cache[(hijo, p)] = a_metros(ramas[p][0], ramas[p][1], lon0, lat0)
        h, q = cache[(hijo, hijo)], cache[(hijo, padre)]
        (tvd_h, u_h), (tvd_p, u_p) = atributos[hijo], atributos[padre]
        dtvd = abs(tvd_h - tvd_p) if tvd_h and tvd_p and tvd_h > 0 and tvd_p > 0 else None
        misma = (u_h == u_p) if u_h in UNIDADES and u_p in UNIDADES else None
        out.append((hijo, padre, mes, km, distancia_minima(h, q), separacion_mediana(h, q), dtvd, misma))
    return out


def medir_pares_rama(pares: list[tuple], ramas: dict[int, tuple], boca: dict[int, tuple]) -> list[tuple]:
    """Filas de mart_par_rama para los pares (hijo, padre, mes_frac, km) con las dos ramas medidas.

    `ramas` es pozo_id -> (lon[], lat[]); `boca` pozo_id -> (lon, lat) de la superficie. El marco local es el del
    hijo (origen en su boca, eje este y norte) y las dos ramas se remuestrean antes de medir."""
    out = []
    cache: dict[tuple[int, int], np.ndarray] = {}
    for hijo, padre, mes, km in pares:
        if hijo not in ramas or padre not in ramas:
            continue
        lon0, lat0 = boca[hijo]
        for p in (hijo, padre):
            if (hijo, p) not in cache:
                cache[(hijo, p)] = remuestrear(a_metros(ramas[p][0], ramas[p][1], lon0, lat0))
        g = geometria_par(cache[(hijo, hijo)], cache[(hijo, padre)])
        out.append((hijo, padre, g["azimut_hijo"], g["azimut_padre"], g["dif_azimut"], g["paralelas"],
                    g["solape_frac"], g["desfase_perp_m"], g["desfase_axial_m"], g["posicion"], g["angulo_shmax_hijo"]))
    return out


def _cuantil(x, q) -> float | None:
    x = np.asarray([v for v in x if v is not None], float)
    return float(np.quantile(x, q)) if len(x) else None


def _rangos(x: np.ndarray) -> np.ndarray:
    """Rangos con empates promediados."""
    orden = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[orden] = np.arange(len(x), dtype=float)
    _, inv, cuenta = np.unique(x, return_inverse=True, return_counts=True)
    suma = np.bincount(inv, weights=r)
    return suma[inv] / cuenta[inv]


def spearman(x, y) -> float | None:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3:
        return None
    return float(np.corrcoef(_rangos(x), _rangos(y))[0, 1])


def _banda(km: float, bandas) -> str | None:
    for clave, desde, hasta, _ in bandas:
        if desde <= km < hasta:
            return clave
    return None


def tabla_bandas(pares_todos: list[tuple], medidos: list[tuple]) -> list[tuple]:
    """Por banda de superficie: pares, medidos, cuartiles de m_min, mediana de m_mediana, parte con ramas a menos de
    1 km, parte en la misma unidad (entre los que tienen las dos unidades) y mediana de la diferencia de PNL_TVD."""
    out = []
    for i, (clave, _, _, _) in enumerate(BANDAS):
        n = sum(1 for p in pares_todos if _banda(p[3], BANDAS) == clave)
        m = [p for p in medidos if _banda(p[3], BANDAS) == clave]
        mins = [p[4] for p in m]
        uni = [p[7] for p in m if p[7] is not None]
        out.append((clave, i, n, len(m), _cuantil(mins, 0.25), _cuantil(mins, 0.5), _cuantil(mins, 0.75),
                    _cuantil([p[5] for p in m], 0.5), (sum(1 for x in mins if x < 1000) / len(m)) if m else None,
                    (sum(uni) / len(uni)) if uni else None, _cuantil([p[6] for p in m], 0.5)))
    return out


def tabla_cruce(medidos: list[tuple]) -> list[tuple]:
    cuenta: dict[tuple[str, str], int] = {}
    for p in medidos:
        s, r = _banda(p[3], SUPERFICIE), _banda(p[4] / 1000, RAMA)
        if s and r:
            cuenta[(s, r)] = cuenta.get((s, r), 0) + 1
    return [(s, r, cuenta.get((s, r), 0)) for s, *_ in SUPERFICIE for r, *_ in RAMA]


def tabla_cobertura(hijos: list[tuple], pares_todos: list[tuple], en_fuente: set[int], con_rama: set[int]) -> list[tuple]:
    """Por año de fractura del hijo. Hijos (hijo, mes, sigla): total y con rama medida; y los horizontales por la sigla:
    cuántos, cuántos están unidos a un pozo de la fuente y cuántos tienen la rama medida. Pares a menos de 1 y de 2 km:
    total y con las dos ramas medidas (las columnas de horizontales quedan nulas)."""
    cuenta: dict[tuple[str, int], list] = {}
    for hijo, mes, sigla in hijos:
        c = cuenta.setdefault(("hijo", mes.year), [0, 0, 0, 0, 0])
        h = bool(HORIZONTAL.search(sigla or ""))
        c[0] += 1
        c[1] += int(hijo in con_rama)
        c[2] += int(h)
        c[3] += int(h and hijo in en_fuente)
        c[4] += int(h and hijo in con_rama)
    for hijo, padre, mes, km in pares_todos:
        ok = int(hijo in con_rama and padre in con_rama)
        for nivel, tope in (("par_1km", 1.0), ("par_2km", 2.0)):
            if km < tope:
                c = cuenta.setdefault((nivel, mes.year), [0, 0, None, None, None])
                c[0] += 1
                c[1] += ok
    return [(n, a, *v) for (n, a), v in sorted(cuenta.items())]


def resumen(total_filas: int, distintas: int, pozos: list[dict], universo: int, medidos: list[tuple]) -> list[tuple]:
    con_rama = [r for r in pozos if r["motivo"] is None]
    ramas = [r["rama_m"] for r in con_rama]
    tvd = [r["pnl_tvd"] for r in con_rama if r["pnl_tvd"] and r["pnl_tvd"] > 0]
    uni = [r["unidad"] for r in con_rama if r["unidad"] in UNIDADES]
    out = [("filas", total_filas), ("filas_repetidas", total_filas - distintas), ("pozos_fuente", len(pozos)),
           ("pozos_idpo_cero", sum(1 for r in pozos if not r["idpo"])),
           ("pozos_varias_versiones", sum(1 for r in pozos if r["versiones"] > 1)),
           ("unidos_idpo", sum(1 for r in pozos if r["union_por"] == "idpo")),
           ("unidos_sigla", sum(1 for r in pozos if r["union_por"] == "sigla")),
           ("universo_estudio", universo), ("con_rama", len(con_rama)),
           ("boca_mediana_m", _cuantil([r["boca_m"] for r in con_rama], 0.5)),
           ("con_unidad", len(uni)), ("pares_medidos", len(medidos)),
           ("spearman_km_m_min", spearman([p[3] for p in medidos], [p[4] for p in medidos]))]
    out += [(f"motivo_{i}", sum(1 for r in pozos if r["motivo"] == m)) for i, m in enumerate(MOTIVOS)]
    out += [(f"rama_p{int(q * 100):02d}", _cuantil(ramas, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
    out += [(f"pnl_tvd_p{int(q * 100):02d}", _cuantil(tvd, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
    out += [(f"unidad_{u}", sum(1 for x in uni if x == u)) for u in UNIDADES]
    anios = [int(r["drilini"][:4]) for r in con_rama if r["drilini"]]
    out += [("anio_perforacion_min", min(anios) if anios else None), ("anio_perforacion_max", max(anios) if anios else None)]
    return [(k, None if v is None else float(v)) for k, v in out]


def _insertar(con, tabla: str, columnas: list[tuple[str, str]], filas: list[tuple]) -> None:
    """Agrega muchas filas de una vez (executemany tarda unos 20 s cada 60.000 filas)."""
    if not filas:
        return
    cols = list(zip(*filas))
    sel = ", ".join(f"unnest(${i + 1}::{t}[])" for i, (_, t) in enumerate(columnas))
    con.execute(f"insert into {tabla} select {sel}", [list(c) for c in cols])


def ruta_fuente(manifest: dict | None = None, raw_dir: Path = DATA / "raw") -> Path:
    entry = (load_manifest(MANIFEST) if manifest is None else manifest).get(CLAVE) or {}
    ruta = raw_dir / entry["path"] if entry.get("path") else None
    if ruta is None or not ruta.exists():
        raise SystemExit(f"falta la copia de {CLAVE} en data/raw: correr `uv run python -m pipeline.ingest` (necesita una red que llegue a datos.energia.gob.ar)")
    return ruta


def calcular(con, ruta: Path) -> dict[str, list[tuple]]:
    """Todo el cálculo; lee dim_pozo, int_pozo_ubicacion, int_frac_hijo e int_par_padre_hijo y no escribe."""
    total, filas = leer_filas(con, ruta)
    pozos = versiones_por_pozo(filas)
    filas_por_clave: dict[str, int] = {}
    lit = str(ruta).replace("'", "''")
    for idpo, sigla, n in con.execute(f"select idpo, sigla, count(*) from read_csv('{lit}', all_varchar = true, header = true) "
                                      "group by all").fetchall():
        i = _entero(idpo) or 0
        k = str(i) if i else "s:" + (sigla or "").strip()
        filas_por_clave[k] = filas_por_clave.get(k, 0) + int(n)
    dim = {r[0]: (r[1], r[2]) for r in con.execute("select pozo_id, lon, lat from dim_pozo").fetchall()}
    por_sigla = {r[0]: r[1] for r in con.execute(
        "select sigla, min(pozo_id) from dim_pozo where sigla is not null group by sigla having count(*) = 1").fetchall()}
    ubic = {r[0]: (r[1], r[2]) for r in con.execute("select pozo_id, lon, lat from int_pozo_ubicacion").fetchall()}
    reg = procesar_pozos(pozos, filas_por_clave, dim, por_sigla, set(ubic))
    con_rama = {r["pozo_id"]: r for r in reg if r["motivo"] is None}
    en_fuente = {r["pozo_id"] for r in reg if r["pozo_id"] is not None}
    pares_todos = con.execute("select hijo, padre, mes_frac::date, km from int_par_padre_hijo order by hijo, padre").fetchall()
    medidos = medir_pares(pares_todos, {k: r["rama"] for k, r in con_rama.items()}, ubic,
                          {k: (r["pnl_tvd"], r["unidad"]) for k, r in con_rama.items()})
    pares_rama = medir_pares_rama(pares_todos, {k: r["rama"] for k, r in con_rama.items()}, ubic)
    hijos = con.execute("select h.hijo, h.mes_frac::date, d.sigla from int_frac_hijo h "
                        "left join dim_pozo d on d.pozo_id = h.hijo order by h.hijo").fetchall()
    pozo_filas = [(r["clave"], r["idpo"], r["sigla"], r["pozo_id"], r["union_por"], r["filas"], r["versiones"], r["md"], r["tvd"],
                   r["hz"], r["pnl_md"], r["pnl_tvd"], r["unidad"], r["detalle"], r["tipopozo"], r["drilini"], r["drilfin"],
                   r["largo_plano"], r["boca_m"], r["rama_m"],
                   None if r["rama"] is None else [float(x) for x in r["rama"][0]],
                   None if r["rama"] is None else [float(x) for x in r["rama"][1]], r["motivo"]) for r in reg]
    return {"mart_trayectoria_pozo": pozo_filas, "mart_trayectoria_par": medidos,
            "mart_par_rama": pares_rama,
            "mart_trayectoria_cobertura": tabla_cobertura(hijos, pares_todos, en_fuente, set(con_rama)),
            "mart_trayectoria_banda": tabla_bandas(pares_todos, medidos),
            "mart_trayectoria_cruce": tabla_cruce(medidos),
            "mart_trayectoria_resumen": resumen(total, len(filas), reg, len(ubic), medidos)}


# ---------------------------------------------------------------- página

def _pct(x, dec: int = 0) -> str:
    return "n/d" if x is None else _g(100 * x, dec) + "%"


def _km(m) -> str:
    return "n/d" if m is None else _g(m / 1000, 2)


def _anio(x) -> str:
    return "n/d" if x is None else str(int(x))


def pagina_trayectorias(con, manifest: dict | None = None) -> str:
    """Página de la wiki a partir de los marts (solo lee)."""
    manifest = load_manifest(MANIFEST) if manifest is None else manifest
    fuente = manifest.get(CLAVE) or {}
    R = dict(con.execute("select clave, valor from mart_trayectoria_resumen").fetchall())
    cob = {(r[0], r[1]): tuple(r[2:]) for r in con.execute(
        "select nivel, anio, total, medidos, horizontales, horizontales_en_fuente, horizontales_medidos "
        "from mart_trayectoria_cobertura").fetchall()}
    ban = {r[0]: r for r in con.execute("select * from mart_trayectoria_banda").fetchall()}
    cru = {(r[0], r[1]): r[2] for r in con.execute("select * from mart_trayectoria_cruce").fetchall()}
    pos_cuenta: dict[tuple[str, str], int] = {}
    for km, posicion in con.execute(
            "select b.km, p.posicion from mart_par_rama p "
            "join mart_trayectoria_par b on b.hijo = p.hijo and b.padre = p.padre").fetchall():
        s = _banda(km, SUPERFICIE)
        if s:
            pos_cuenta[(s, posicion)] = pos_cuenta.get((s, posicion), 0) + 1
    pos_total = {s: sum(pos_cuenta.get((s, p), 0) for p in POSICIONES) for s, *_ in SUPERFICIE}

    def tot(nivel: str, desde: int | None = None, hasta: int | None = None) -> tuple[int, ...]:
        """Suma por columna de los años [desde, hasta)."""
        f = [v for (n, a), v in cob.items() if n == nivel and (desde is None or a >= desde) and (hasta is None or a < hasta)]
        return tuple(sum(x[i] or 0 for x in f) for i in range(5))
    h_t, h_m, hh_t, hh_f, hh_m = tot("hijo")
    _, _, ha_t, ha_f, ha_m = tot("hijo", hasta=CORTE_RECIENTE)
    _, _, hr_t, hr_f, hr_m = tot("hijo", desde=CORTE_RECIENTE)
    p1_t, p1_m, *_ = tot("par_1km")
    p2_t, p2_m, *_ = tot("par_2km")
    fila_s = {s: sum(cru[(s, r)] for r, *_ in RAMA) for s, *_ in SUPERFICIE}

    def parte(s: str, rs: tuple[str, ...]) -> float | None:
        return sum(cru[(s, r)] for r in rs) / fila_s[s] if fila_s[s] else None
    cer_lejos = parte("cercano", ("1_2", "2_mas"))
    ctl_cerca = parte("control", ("menos_250", "250_1000"))
    int_cerca = parte("intermedio", ("menos_250", "250_1000"))
    pad = ban["mismo_pad"]
    descarga = (fuente.get("loaded_at") or "")[:10] or "n/d"
    publicado = fuente.get("last_modified") or "n/d"
    L = ["# Trayectorias de pozo: la rama en planta frente a la distancia de superficie", "",
         "Hasta acá, la distancia entre un hijo y un padre es la de sus bocas en superficie. Dos pozos del mismo pad están a "
         "menos de 50 m en superficie y sus ramas pueden ir en direcciones opuestas; dos pads a 2 km pueden tener las ramas "
         "lado a lado. La Secretaría de Energía publica las trayectorias de los pozos horizontales y dirigidos de Vaca Muerta. Esta página dice "
         "cuántos pozos y pares cubre y cuánto cambia la distancia cuando se mide entre ramas. Es descriptiva: no estima "
         "ningún efecto de interferencia y no cambia ninguna cifra del estudio, que sigue usando la distancia de superficie.", "",
         "Esta página la escribe `python -m pipeline.wiki` con `pipeline.trayectorias.pagina_trayectorias`. No se edita a mano.", "",
         "## Lectura", "",
         f"- La fuente trae {_g(R['pozos_fuente'])} pozos en {_g(R['filas'])} filas. {_g(R['con_rama'])} de los "
         f"{_g(R['universo_estudio'])} pozos shale de Vaca Muerta del estudio tienen la rama medida.",
         f"- Tienen la rama medida {_g(hh_m)} de los {_g(hh_t)} hijos horizontales ({_pct(hh_m / hh_t if hh_t else None)}) y "
         f"{_g(p1_m)} de los {_g(p1_t)} pares a menos de 1 km en superficie ({_pct(p1_m / p1_t if p1_t else None)}). "
         f"Los otros {_g(h_t - hh_t)} hijos (dirigidos y verticales, por su sigla) casi no están en la fuente; con la rama "
         f"medida: {_g(h_m - hh_m)}.",
         f"- La fuente todavía no publica la mayoría de los pozos recientes. De los hijos horizontales fracturados antes de "
         f"{CORTE_RECIENTE}, {_g(ha_f)} de {_g(ha_t)} están en la fuente ({_pct(ha_f / ha_t if ha_t else None)}); de los "
         f"fracturados desde {CORTE_RECIENTE}, {_g(hr_f)} de {_g(hr_t)} ({_pct(hr_f / hr_t if hr_t else None)}).",
         f"- En el mismo pad (bocas a menos de 50 m) la mediana de la menor distancia entre ramas es {_g(pad[5])} m, pero la "
         f"separación mediana a lo largo de la rama del hijo es {_g(pad[7])} m: muchas ramas de un pad salen hacia lados opuestos.",
         f"- De los pares cercanos en superficie (menos de 1 km), el {_pct(cer_lejos)} tiene las ramas a 1 km o más. De los pares "
         f"de control (2 a 5 km), el {_pct(ctl_cerca)} tiene las ramas a menos de 1 km; de los intermedios (1 a 2 km), el "
         f"{_pct(int_cerca)}.",
         f"- La correlación de rangos entre la distancia de superficie y la menor distancia entre ramas es {_g(R['spearman_km_m_min'], 2)} "
         f"({_g(R['pares_medidos'])} pares con las dos ramas medidas).", "",
         "## Fuente", "",
         "| Conjunto | Organismo | Licencia | Publicado | Bajado | Huella sha256 |", "| --- | --- | --- | --- | --- | --- |",
         f"| {TITULO} | {ORGANISMO} | {LICENCIA} | {publicado} | {descarga} | `{fuente.get('sha256', 'n/d')}` |", "",
         f"Paquete: {PAQUETE}. Archivo: `{URL}`. Diccionario de campos y códigos de unidad: {INSTRUCTIVO}. La copia cruda queda "
         "en data/raw y no se redistribuye: el repositorio publica solo las tablas derivadas de esta página, con la fuente citada.", "",
         "## Cobertura", "",
         f"- Filas publicadas: {_g(R['filas'])}; filas repetidas idénticas: {_g(R['filas_repetidas'])}; pozos: {_g(R['pozos_fuente'])} "
         f"({_g(R['pozos_idpo_cero'])} sin idpo, identificados por sigla; {_g(R['pozos_varias_versiones'])} con más de una versión).",
         f"- Unidos al warehouse: {_g(R['unidos_idpo'])} por idpo y {_g(R['unidos_sigla'])} por sigla.",
         f"- Con la rama medida: {_g(R['con_rama'])}. Mediana de la distancia entre el inicio del trazado y la ubicación del pozo "
         f"en el warehouse: {_g(R['boca_mediana_m'], 1)} m.", "",
         "| Motivo por el que un pozo de la fuente no tiene rama medida | Pozos |", "| --- | ---: |"]
    L += [f"| {m} | {_g(R[f'motivo_{i}'])} |" for i, m in enumerate(MOTIVOS)]
    L += ["", "Por año de fractura del hijo. Horizontales: por la sigla del pozo. En la fuente: unidos a un pozo de la "
          "fuente, tenga o no la rama medida.", "",
          "| Año | Hijos | Horizontales | En la fuente | Con rama | Parte | Pares a menos de 1 km | Con las dos ramas | Parte | "
          "Pares a menos de 2 km | Con las dos ramas | Parte |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]

    def fila(etq: str, h: tuple, p1: tuple, p2: tuple) -> str:
        celdas = [_g(h[0]), _g(h[2]), _g(h[3]), _g(h[4]), _pct(h[4] / h[2] if h[2] else None)]
        for t, m, *_ in (p1, p2):
            celdas += [_g(t), _g(m), _pct(m / t if t else None)]
        return f"| {etq} | " + " | ".join(celdas) + " |"
    cero = (0, 0, 0, 0, 0)
    for a in sorted({a for (_, a) in cob}):
        L.append(fila(str(a), cob.get(("hijo", a), cero), cob.get(("par_1km", a), cero), cob.get(("par_2km", a), cero)))
    L += [fila("Total", tot("hijo"), tot("par_1km"), tot("par_2km")), "",
          "## Las ramas", "",
          f"Pozos con la rama medida. Largo de la rama (m), cuantiles 5, 25, 50, 75 y 95%: {_g(R['rama_p05'])}, {_g(R['rama_p25'])}, "
          f"{_g(R['rama_p50'])}, {_g(R['rama_p75'])} y {_g(R['rama_p95'])}. Profundidad vertical del inicio de la navegación (m): "
          f"{_g(R['pnl_tvd_p05'])}, {_g(R['pnl_tvd_p25'])}, {_g(R['pnl_tvd_p50'])}, {_g(R['pnl_tvd_p75'])} y {_g(R['pnl_tvd_p95'])}. "
          f"Perforados entre {_anio(R['anio_perforacion_min'])} y {_anio(R['anio_perforacion_max'])}.", "",
          "| Unidad donde navega la rama | Pozos | Parte |", "| --- | ---: | ---: |"]
    L += [f"| {UNIDADES[u]} | {_g(R[f'unidad_{u}'])} | {_pct(R[f'unidad_{u}'] / R['con_unidad'] if R['con_unidad'] else None)} |"
          for u in UNIDADES]
    L += ["", "## Distancia entre ramas por banda de superficie", "",
          "Pares hijo y padre de int_par_padre_hijo (padre con petróleo desde al menos 6 meses antes de la fractura del hijo, "
          "bocas a menos de 5 km). Menor distancia: la menor entre las dos ramas en planta. Separación mediana: la mediana de la "
          "distancia de cada punto de la rama del hijo a la rama del padre.", "",
          "| Distancia de superficie | Pares | Con las dos ramas | Menor distancia, mediana (m) | Cuartiles (m) | "
          "Separación mediana (m) | Ramas a menos de 1 km | Misma unidad | Diferencia de profundidad vertical, mediana (m) |",
          "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |"]
    for clave, _, _, etq in BANDAS:
        r = ban[clave]
        L.append(f"| {etq} | {_g(r[2])} | {_g(r[3])} | {_g(r[5])} | {_g(r[4])} a {_g(r[6])} | {_g(r[7])} | {_pct(r[8])} | "
                 f"{_pct(r[9])} | {_g(r[10])} |")
    L += ["", "## Cómo se reparten los pares al medir entre ramas", "",
          "Pares con las dos ramas medidas. Filas: la banda de superficie del estudio. Columnas: la menor distancia entre ramas.", "",
          "| Superficie | " + " | ".join(e for *_, e in RAMA) + " | Pares |", "| --- |" + " ---: |" * (len(RAMA) + 1)]
    for s, *_, etq in SUPERFICIE:
        L.append(f"| {etq} | " + " | ".join(f"{_g(cru[(s, r)])} ({_pct(cru[(s, r)] / fila_s[s] if fila_s[s] else None)})"
                                              for r, *_ in RAMA) + f" | {_g(fila_s[s])} |")
    L += ["", "## Dónde queda el padre respecto de la rama del hijo", "",
          "El eje de cada rama en planta es su primera componente principal. Con el eje del hijo, el padre queda de "
          "costado cuando su rama solapa el 30% o más de la rama del hijo, de punta cuando no solapa nada y mixto en el "
          "resto. Es descriptivo: no cambia ninguna cifra del estudio.", "",
          "Pares con las dos ramas medidas. Filas: la banda de superficie del estudio. Columnas: la posición del padre "
          "respecto de la rama del hijo. El porcentaje es sobre los pares de la fila.", "",
          "| Superficie | " + " | ".join(POSICIONES) + " | Pares |", "| --- |" + " ---: |" * (len(POSICIONES) + 1)]
    for s, _, _, etq in SUPERFICIE:
        total = pos_total[s]
        celdas = [f"{_g(pos_cuenta.get((s, p), 0))} ({_pct(pos_cuenta.get((s, p), 0) / total if total else None)})"
                  for p in POSICIONES]
        L.append(f"| {etq} | " + " | ".join(celdas) + f" | {_g(total)} |")
    L += ["", "## Cómo se mide", "",
          "- Duplicados: se quitan las filas idénticas. Un pozo es su idpo, o su sigla cuando el idpo es 0. Si quedan varias "
          "versiones, vale la que tiene un inicio de navegación válido; entre ellas, la más profunda.",
          "- Unión: idpo igual a pozo_id del warehouse; con idpo 0, la sigla exacta cuando es única.",
          "- Rama: el tramo final del trazado en planta con el largo declarado de la rama (o profundidad final menos el inicio "
          "de la navegación, si falta), simplificado a 2 m. En la rama el pozo va casi horizontal: su largo medido y su largo "
          "en planta coinciden.",
          f"- Un pozo se descarta si su trazado sale a más de {_g(BOCA_MAX_M)} m de su ubicación en el warehouse o si el trazado "
          "en planta es más largo que el pozo.",
          "- Las distancias usan la misma escala que la distancia de superficie del estudio: 111,32 km por grado y el coseno "
          "de la latitud del hijo.",
          "- Posición del padre: el eje de cada rama en planta es su primera componente principal; con el eje del hijo, "
          "el solape a lo largo de ese eje da la posición (costado, punta o mixto) y el desvío perpendicular es la "
          "mediana de la distancia al eje del hijo sobre la parte que se solapa.", "",
          "## Qué no es", "",
          "- Es la rama en planta. La fuente no publica la cota de cada punto: la profundidad entra solo como la diferencia "
          "del inicio de la navegación entre los dos pozos y como la unidad donde navega cada uno.",
          "- No es un espaciamiento declarado por el operador ni dice dónde se fracturó cada etapa.",
          "- La cobertura cae en los pozos recientes, así que una comparación por año mezcla años bien cubiertos con años "
          "que todavía no lo están. Los pozos verticales no tienen trayectoria: el instructivo la pide para los horizontales, "
          "dirigidos y sidetrack.",
          "- No mide interferencia: el estudio de eventos sigue con la distancia de superficie. Cambiarla por la distancia entre "
          "ramas es una corrida aparte, con su regla fijada antes.", "",
          "## Reproducir", "",
          "- `uv run python -m pipeline.ingest` baja la fuente con las otras dos y registra su huella en data/manifest.json.",
          "- `uv run python -m pipeline.trayectorias` arma los marts (mart_trayectoria_pozo, mart_trayectoria_par, "
          "mart_par_rama y los de esta página); `uv run python -m pipeline.wiki` reescribe la página y "
          "`uv run python -m pipeline.claims` verifica sus cifras contra el warehouse.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> int:
    try:
        ruta = ruta_fuente()
    except SystemExit as e:
        # sin la copia cruda (data/raw anterior a esta fuente) el paso no corta run_all: avisa y deja los marts como están
        print(f"AVISO: {e}; los marts de trayectorias quedan como estaban", file=sys.stderr)
        return 0
    con = duckdb.connect(str(path))
    try:
        t = calcular(con, ruta)
        _escribir(con, "mart_trayectoria_pozo", COLS_POZO, t["mart_trayectoria_pozo"])
        _escribir(con, "mart_trayectoria_par", COLS_PAR, [])
        _insertar(con, "mart_trayectoria_par", COLS_PAR, t["mart_trayectoria_par"])
        _escribir(con, "mart_par_rama", COLS_PAR_RAMA, [])
        _insertar(con, "mart_par_rama", COLS_PAR_RAMA, t["mart_par_rama"])
        _escribir(con, "mart_trayectoria_cobertura", COLS_COBERTURA, t["mart_trayectoria_cobertura"])
        _escribir(con, "mart_trayectoria_banda", COLS_BANDA, t["mart_trayectoria_banda"])
        _escribir(con, "mart_trayectoria_cruce", COLS_CRUCE, t["mart_trayectoria_cruce"])
        _escribir(con, "mart_trayectoria_resumen", COLS_RESUMEN, t["mart_trayectoria_resumen"])
    finally:
        con.close()
    R = dict(t["mart_trayectoria_resumen"])
    print(f"[trayectorias] {R['pozos_fuente']:.0f} pozos en la fuente, {R['con_rama']:.0f} con rama medida, "
          f"{R['pares_medidos']:.0f} pares con las dos ramas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
