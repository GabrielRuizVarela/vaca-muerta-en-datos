"""Export the 3D world (site/mundo.html): one self-contained page with the play, its history and the event study.

  uv run python -m pipeline.mundo        # data/warehouse.duckdb -> site/mundo.html

It estimates nothing new. It embeds public data (wells, monthly rates, frac jobs), results that already exist in
the marts (event-study curve, gap by parent age, closure, deferred oil, loss bound) and reference answers that the
page recomputes at load (the self-test, "autoverificación N/N").

Data contract (read by pipeline/mundo_template.html; every typed array is base64 of little-endian values):

- meta:    {meses: ["2012-01", ...], n_pozos, n_eventos, hash_datos, mes_datos, generado, operadores: [...],
            areas: [...], escala_caudal, sin_fila, escala_indice, sin_indice, k_min, k_max, bbl_m3, profundidad,
            rezago_carga_desde, busca_min, busca_max, vecindad_km}
           busca_min is the shortest search key that returns anything and busca_max the number of wells listed.
           vecindad_km is the radius inside which the physics tool lists the neighbouring pads of a well.
           rezago_carga_desde is the index into meses from which recent frac jobs may still be missing from the
           public file (the last MESES_REZAGO_CARGA months; a generic note, not an estimate).
- pozos:   columns in matrix row order (shale wells with a surface location, ordered by pozo_id):
           id, sigla, op (index into meta.operadores), area (index into meta.areas), pad (number of pad_id), lon, lat
           (5 decimals, surface location), mes0 (months from meses[0] to the first month with oil, may be negative,
           null without oil), frac (date of the first frac job or null), md (total measured depth in m from the
           production file, it includes the lateral; null when the file has 0 or the raw file is absent), rama
           (lateral length in m), etapas, arena (t), agua (m3), np (cumulative oil in m3).
- caudal:  Uint16 matrix pozos x meses, calendar-day oil rate in units of 1 / escala_caudal bbl/d (0,1 bbl/d);
           sin_fila (65535) marks a month without a row in fct_produccion, which is not the same as a zero.
           A month with oil is never a zero (codificar_caudal), so a rate above zero is a producing well.
           A rate that does not fit (6.553,5 bbl/d or more) stops the export: it is never clipped.
- fracs:   {pozo: Uint16 well index, dia: Uint16 days since the first day of meses[0]}, every dated frac job, by date.
- eventos: the near (< 1 km) and control (2 to 5 km) events of int_interferencia_evento, ordered by band, month and
           parent: padre and hijo (Uint16 well index), mes (Uint16 index into meses), km (Uint16 metres to the
           nearest child), base (Uint16, base rate in 0,1 bbl/d), flags (Uint8: bit 0 set for a control, bits 1 and 2
           the parent age group 0..3 = 06-11, 12-23, 24-47, 48+), indice (Uint16 matrix eventos x 10, the parent's
           rate index for k = -3..6 times escala_indice, sin_indice when the month has no row). An index above
           TOPE_INDICE / escala_indice (6,5534; about 1 value in 180) is stored as TOPE_INDICE: medians are far
           below it and stay exact, so use these values for medians and for drawing, never for means.
- curva:   {cercano: [...], control: [...]} median index for k = -3..6 from mart_interferencia_curva.
- brecha:  [[near minus control median index for k = -3..6] per age group] from mart_interferencia_brecha.
- pub:     published numbers: month-1 gap and its 5 km block interval (mart_bloques), closure with the four controls
           (mart_decision_cierre), mean deferred oil per event with its interval and the loss bound
           (mart_decision_edad, mart_decision_perdida).
- cuenca:  {ops: [...], kbbl: [[per month] per operator]} from mart_vm_mensual (same grouping as the replay).
- acto2:   the event of the second act, picked by REGLA_ACTO2 (never by eye): child well index, month index, frac
           job data and the indices into eventos of its near parents and of its controls.
- autotest: reference answers computed here in Python (totals, the "plantá un pozo" answer at fixed positions with
           its split by month, the nearest well of another pad for fixed wells, the two physics formulas on a fixed
           grid, the search results of fixed queries). The page recomputes them with its own code and counts matches.
           autotest.serie pins what the timeline chart and the scene events draw: frac jobs per month and their
           peak, wells starting per month, each operator's share of the basin oil at fixed months, the cumulative
           oil of fixed wells and the fractional month of fixed days.
           With a base map it also carries autotest.base: the decoded relief (cells, sum, extremes), the ground
           elevation at AT_BOCAS wells and at five fixed points (two of them outside the box: null), the wells
           outside the box, the median and the highest ground elevation over all wells, and the item, part and
           point counts of each vector layer with the sum of its coordinates.
- base:    the base map of pipeline.base_mapa as written in data/base_mapa.json (its contract is in that module's
           docstring): relief, rivers, water bodies, province borders, towns, concession blocks and the source and
           licence of each layer. null when the file is absent: the page then draws its plain grid.
- foto:    the ground imagery of pipeline.base_foto (data/base_foto.json and its two WebP files): {capas: [{nombre,
           caja, ancho, alto, sha256, webp}] the whole base-map box first and the finer core tile second, each one
           base64 of the pinned file; desde and hasta, the acquisition dates of the scenes; escenas, how many;
           atribucion, url_licencia and fecha_descarga for the credit line}. null when the manifest or the base map
           is absent: the page then keeps its drawn relief and has no ground reading. The image is context: no
           number on the page is read from it. autotest.foto pins the bytes, the byte sum and the pixel size of
           each embedded image and the clock month of its dates.
"""
from __future__ import annotations

import base64
import calendar
import hashlib
import json
import math
import re
import sys
import unicodedata
from array import array
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

import duckdb

from pipeline import base_foto, base_mapa
from pipeline.decision import valor_indicativo
from pipeline.ingest import DATA, ROOT, load_manifest
from pipeline.replay import BBL_PER_M3, MIN_ACTIVE, N_OPS, b64, month_key, q
from pipeline.sistema import sistema_css
from pipeline.wiki import num

TEMPLATE = Path(__file__).parent / "mundo_template.html"
OUT = ROOT / "site" / "mundo.html"
MAX_BYTES = 8 * 1024 * 1024
BASE_MAPA = DATA / "base_mapa.json"
BASE_FOTO = DATA / "base_foto.json"
ESCALA_CAUDAL = 10          # caudal is stored in 0,1 bbl/d
SIN_FILA = 65535            # month without a row
ESCALA_INDICE = 10000       # index is stored in 1 / 10000
SIN_INDICE = 65535
TOPE_INDICE = SIN_INDICE - 1   # a larger index saturates here (see the data contract)
K_MIN, K_MAX = -3, 6
GRUPOS = ("06-11", "12-23", "24-47", "48+")
MESES_REZAGO_CARGA = 12     # recent frac jobs are loaded late: the last 12 months are shaded on the timeline
KM_CERCANO, KM_INTERMEDIO, KM_CONTROL = 1.0, 2.0, 5.0
EDAD_MINIMA = 6             # parent's first oil at least 6 months before the child's frac month
BASE_MINIMA_M3_D = 1.0      # parent's base rate above 1 m3/d
MIN_PADRES_ACTO2 = 3
REGLA_ACTO2 = ("entre los hijos con datos de fractura completos, al menos 3 padres cercanos y 3 controles con la "
               "ventana de meses -3 a 6 completa, el que tiene la mediana del índice de sus padres cercanos en el mes 1 "
               "más próxima a la mediana de la cuenca; si empatan, el más antiguo")
# Fixed inputs of the self-test (not a forecast and not an observed price).
AT_PRECIO, AT_TASA, AT_REZAGO = 60.0, 0.10, 12
AT_POSICIONES = 20
AT_VECINOS = 20
AT_BOCAS = 24          # wells whose ground elevation the page recomputes from the embedded relief
AT_BUSQUEDAS = 6
AT_ACUMULADO = 12      # wells whose cumulative oil the page recomputes from the monthly matrix
AT_PADS = 8            # wells whose neighbouring pads the page recomputes
VECINDAD_KM = 2.0      # the physics tool lists the pads whose nearest wellhead is this close to the chosen well
EULER = 0.5772156649015329
BUSCA_MIN = 2               # a shorter search key returns nothing
BUSCA_MAX = 8               # wells listed per search
AT_DESPLAZAMIENTO = (0.004, 0.002)  # degrees east and north of a real well, about 350 m and 220 m
# Unit conversions of the physics calculators.
MD_M2 = 9.869233e-16
CP_PAS = 1e-3
PSI_PA = 6894.757
FT_M = 0.3048


def _d(x):
    return x.date() if isinstance(x, datetime) else x


def _r(x, d: int = 6):
    return None if x is None else round(float(x), d)


# ---- pure functions (the page has the same ones in JavaScript; the self-test compares the two) ----

def distancia_km(lon_h: float, lat_h: float, lon_p: float, lat_p: float) -> float:
    """Surface distance child to parent, the formula of pipeline/sql/04_interferencia.sql."""
    return 111.32 * math.sqrt(((lon_p - lon_h) * math.cos(math.radians(lat_h))) ** 2 + (lat_p - lat_h) ** 2)


def grupo_edad(edad_meses: int) -> int:
    """Index into GRUPOS for a parent age in months (the age is at least EDAD_MINIMA)."""
    return 0 if edad_meses < 12 else 1 if edad_meses < 24 else 2 if edad_meses < 48 else 3


def dias_del_mes(inicio: tuple[int, int], j: int) -> int:
    """Calendar days of month index j, where index 0 is the (year, month) inicio; j may run past the data."""
    t = inicio[0] * 12 + inicio[1] - 1 + j
    return calendar.monthrange(t // 12, t % 12 + 1)[1]


def mes_de_dia(inicio: tuple[int, int], dia: int) -> float:
    """Fractional month index of a day counted from the first day of the series; its integer part is the month."""
    f = date(inicio[0], inicio[1], 1) + timedelta(days=dia)
    k = (f.year - inicio[0]) * 12 + f.month - inicio[1]
    return k + (f.day - 1) / dias_del_mes(inicio, k)


def primer_mes(pozos: dict, p: int, inicio: tuple[int, int]) -> int | None:
    """First month of well p in the scene: its first month with oil or the month of its frac job, whichever is first."""
    m0, f = pozos["mes0"][p], pozos["frac"][p]
    if f is not None:
        mf = (int(f[:4]) - inicio[0]) * 12 + int(f[5:7]) - inicio[1]
        m0 = mf if m0 is None else min(m0, mf)
    return m0


def fracs_por_mes(frac_dia, inicio: tuple[int, int], nm: int) -> list[int]:
    """Dated frac jobs in each month of the series."""
    cuenta = Counter(math.floor(mes_de_dia(inicio, d)) for d in frac_dia)
    return [cuenta.get(m, 0) for m in range(nm)]


def llegadas_por_mes(pozos: dict, inicio: tuple[int, int], nm: int) -> dict:
    """Wells starting in each month; `antes` started before the first month and `sin` have no date at all."""
    primeros = [primer_mes(pozos, p, inicio) for p in range(len(pozos["id"]))]
    cuenta = Counter(m for m in primeros if m is not None and 0 <= m < nm)
    return {"mes": [cuenta.get(m, 0) for m in range(nm)], "antes": sum(1 for m in primeros if m is not None and m < 0),
            "sin": sum(1 for m in primeros if m is None)}


def pico(serie: list) -> dict:
    """First month where a series reaches its maximum."""
    n = max(serie, default=0)
    return {"mes": serie.index(n) if serie else 0, "n": n}


def partes_cuenca(cuenca: dict, j: int) -> list[float | None]:
    """Each operator's share of the basin oil in month j, None when the month has no oil."""
    tot = sum(fila[j] for fila in cuenca["kbbl"])
    return [fila[j] / tot if tot > 0 else None for fila in cuenca["kbbl"]]


def acumulado_bbl(caudal, nm: int, p: int, m: int, inicio: tuple[int, int]) -> float:
    """Cumulative oil of well p up to month m in barrels: the month's mean rate times its calendar days."""
    s = 0.0
    for j in range(m + 1):
        v = caudal[p * nm + j]
        if v != SIN_FILA:
            s += v / ESCALA_CAUDAL * dias_del_mes(inicio, j)
    return s


def base_bbl_d(caudal, nm: int, p: int, m: int) -> float | None:
    """Mean rate of well p over the months m-3..m-1 that have a row (the avg of the SQL), or None without rows."""
    vals = [caudal[p * nm + j] for j in range(m - 3, m) if 0 <= j < nm and caudal[p * nm + j] != SIN_FILA]
    return sum(vals) / len(vals) / ESCALA_CAUDAL if vals else None


def plantar(lon: float, lat: float, m: int, lons, lats, mes0, caudal, nm: int, brecha, inicio: tuple[int, int]) -> dict:
    """The measured footprint applied to the real parents around a hypothetical child fractured in month index m.

    Same rules as the event study: parents with first oil at least 6 months before m, within 5 km, base rate (months
    m-3..m-1) above 1 m3/d; under 1 km they are near, 1 to 2 km intermediate, 2 to 5 km control. For each near parent
    the deferred oil is the sum over k = 0..6 of -brecha[age group][k] x base rate x days of month m+k; por_mes is the
    same oil split by k and added over the near parents, and por_padre_bbl is the total per near parent (None when
    there is none).
    """
    cercanos, n_inter, n_control = [], 0, 0
    por_mes = [0.0] * (K_MAX + 1)
    for p in range(len(lons)):
        if mes0[p] is None or m - mes0[p] < EDAD_MINIMA:
            continue
        km = distancia_km(lon, lat, lons[p], lats[p])
        if not km < KM_CONTROL:
            continue
        base = base_bbl_d(caudal, nm, p, m)
        if base is None or not base / BBL_PER_M3 > BASE_MINIMA_M3_D:
            continue
        if km < KM_CERCANO:
            g = grupo_edad(m - mes0[p])
            dif = 0.0
            for k in range(0, K_MAX + 1):
                v = -brecha[g][k - K_MIN] * base * dias_del_mes(inicio, m + k)
                dif += v
                por_mes[k] += v
            cercanos.append({"p": p, "km": km, "grupo": g, "base": base, "diferido": dif})
        elif km < KM_INTERMEDIO:
            n_inter += 1
        else:
            n_control += 1
    diferido = sum(c["diferido"] for c in cercanos)
    return {"cercanos": cercanos, "n_intermedio": n_inter, "n_control": n_control, "por_mes": por_mes,
            "base_bbl_d": sum(c["base"] for c in cercanos), "diferido_bbl": diferido,
            "por_padre_bbl": diferido / len(cercanos) if cercanos else None}


def vecino_otro_pad(p: int, lons, lats, pads) -> tuple[int, float] | None:
    """Nearest well of another pad by surface distance, as (well index, km); the first one wins a tie.

    Wells of one pad sit metres apart at the surface while their laterals fan out underground, so the nearest
    pad mate says nothing about spacing. The public data has no lateral spacing: this is a surface distance.
    """
    mejor = None
    for otro in range(len(lons)):
        if pads[otro] == pads[p]:
            continue
        km = distancia_km(lons[p], lats[p], lons[otro], lats[otro])
        if mejor is None or km < mejor[1]:
            mejor = (otro, km)
    return mejor


def clave_busqueda(texto: str) -> str:
    """Search key: accents dropped, upper case, letters and digits only (the page builds the same key)."""
    return re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFD", texto).upper())


def buscar(consulta: str, pozos: dict, operadores: list[str], areas: list[str], tope: int = BUSCA_MAX) -> dict:
    """Wells whose sigla contains the query and the areas and operators whose name contains it.

    Wells: those whose key starts with the query first, then by key and by index; `total` counts every match and
    `pozos` lists the first `tope`. Areas and operators: [index, number of wells], most wells first. A key shorter
    than BUSCA_MIN returns nothing.
    """
    c = clave_busqueda(consulta)
    if len(c) < BUSCA_MIN:
        return {"pozos": [], "total": 0, "areas": [], "operadores": []}
    hallados = sorted((not k.startswith(c), k, p) for p, k in enumerate(map(clave_busqueda, pozos["sigla"])) if c in k)

    def grupos(nombres: list[str], de: list[int]) -> list[list[int]]:
        cuenta = Counter(de)
        return sorted(([i, cuenta[i]] for i, n in enumerate(nombres) if c in clave_busqueda(n)),
                      key=lambda g: (-g[1], g[0]))

    return {"pozos": [p for _, _, p in hallados[:tope]], "total": len(hallados),
            "areas": grupos(areas, pozos["area"]), "operadores": grupos(operadores, pozos["op"])}


def consultas_de_prueba(pozos: dict, operadores: list[str], areas: list[str]) -> list[str]:
    """Fixed queries for the self-test: sigla prefixes of evenly spaced wells as published (with their
    punctuation), the operator and the area with most wells (the first in lower case, the second whole), one
    key that is too short and one that matches nothing."""
    n = len(pozos["id"])
    qs = [pozos["sigla"][min(n - 1, i * max(1, n // AT_BUSQUEDAS))][:6] for i in range(AT_BUSQUEDAS)]
    for nombres, de in ((operadores, pozos["op"]), (areas, pozos["area"])):
        cuenta = Counter(de)
        qs.append(nombres[min(cuenta, key=lambda i: (-cuenta[i], i))])
    qs[-2] = qs[-2][:5].lower()
    return [*qs, "a", "zzqqzz"]


def costo_de_diferir(bbl: float, precio: float, tasa: float, rezago: float) -> float:
    """Time value of collecting bbl barrels rezago months later: the formula of pipeline.decision.valor_indicativo."""
    return valor_indicativo(bbl / BBL_PER_M3, precio, tasa, rezago)["costo_de_diferir"]


def radio_investigacion_ft(k_md: float, t_h: float, phi: float, mu_cp: float, ct_psi: float) -> float:
    """Radius of investigation in field units: r = sqrt(k t / (948 phi mu ct)), r in ft, t in hours."""
    return math.sqrt(k_md * t_h / (948.0 * phi * mu_cp * ct_psi))


def tiempo_a_radio_h(r_ft: float, k_md: float, phi: float, mu_cp: float, ct_psi: float) -> float:
    """Hours until the radius of investigation reaches r_ft (the same formula solved for t)."""
    return 948.0 * phi * mu_cp * ct_psi * r_ft ** 2 / k_md


def permeabilidad_a_radio_md(r_ft: float, t_h: float, phi: float, mu_cp: float, ct_psi: float) -> float:
    """Permeability in md that takes the radius of investigation to r_ft in t_h hours (the same formula solved for k)."""
    return 948.0 * phi * mu_cp * ct_psi * r_ft ** 2 / t_h


def radio_investigacion_m(k_md: float, t_h: float, phi: float, mu_cp: float, ct_psi: float) -> float:
    """The same radius in SI, r = 2 sqrt(eta t) with eta = k / (phi mu ct); it agrees with the field form to 0,1%."""
    eta = k_md * MD_M2 / (phi * mu_cp * CP_PAS * ct_psi / PSI_PA)
    return 2.0 * math.sqrt(eta * t_h * 3600.0)


def e1(x: float) -> float:
    """Exponential integral E1(x) = integral from x to infinity of exp(-t) / t, for x > 0.

    The power series up to x = 1 and a continued fraction (modified Lentz) above it; the page has the same
    two branches, so the two agree to the last bits.
    """
    if not x > 0:
        raise ValueError("E1 needs a positive argument")
    if x <= 1.0:
        suma, termino = -EULER - math.log(x), 1.0
        for k in range(1, 40):
            termino *= -x / k
            suma -= termino / k
        return suma
    b = x + 1.0
    c, d = 1e300, 1.0 / b
    h = d
    for i in range(1, 120):
        a = -float(i * i)
        b += 2.0
        d = 1.0 / (a * d + b)
        c = b + a / c
        h *= c * d
    return h * math.exp(-x)


def caida_adim(s: float) -> float:
    """Dimensionless drawdown of the line-source solution at s = r / r_inv: pD = E1(s^2) / 2.

    With r_inv = 2 sqrt(eta t) the argument r^2 / (4 eta t) is s^2, so the profile keeps its shape and only
    stretches with time. It has no edge: at the radius of investigation the drawdown is small, not zero.
    """
    return 0.5 * e1(s * s)


def pads_en_radio(p: int, lons, lats, pads, mes0, km_max: float, m: int) -> list[dict]:
    """Other pads with a wellhead already on stream within km_max of well p at month m, nearest first.

    One entry per pad: its nearest well (q), that surface distance (km) and how many of its wells are inside
    the radius (n). A well counts once its first month of oil is m or earlier, even if it stopped later, and the page
    says "ya entraron en producción", not "en producción". Ties go to the lower index.
    """
    por_pad: dict = {}
    for otro in range(len(lons)):
        if pads[otro] == pads[p] or mes0[otro] is None or mes0[otro] > m:
            continue
        km = distancia_km(lons[p], lats[p], lons[otro], lats[otro])
        if km > km_max:
            continue
        g = por_pad.get(pads[otro])
        if g is None:
            por_pad[pads[otro]] = {"q": otro, "km": km, "n": 1}
        else:
            g["n"] += 1
            if km < g["km"]:
                g["q"], g["km"] = otro, km
    return sorted(por_pad.values(), key=lambda g: (g["km"], g["q"]))


def autotest_frente(pozos: dict, nm: int) -> dict:
    """References for the field of the physics tool: E1, the profile, and the pads around a few wells."""
    n = len(pozos["id"])
    casos = []
    for i in range(AT_PADS):
        p = min(n - 1, i * max(1, n // AT_PADS) + 3)
        m = nm - 1 if i % 2 == 0 else max(0, nm - 1 - 24 * (1 + i // 2))
        km_max = VECINDAD_KM if i % 3 else VECINDAD_KM / 2
        lista = pads_en_radio(p, pozos["lon"], pozos["lat"], pozos["pad"], pozos["mes0"], km_max, m)
        casos.append({"p": p, "m": m, "km_max": km_max, "pads": lista,
                      "h": [tiempo_a_radio_h(g["km"] * 1000.0 / FT_M, 1.0, 0.08, 0.5, 1.5e-5) for g in lista]})
    return {"e1": [{"x": x, "v": e1(x)} for x in (1e-6, 1e-4, 0.01, 0.1, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0, 30.0)],
            "caida": [{"s": x, "pd": caida_adim(x)} for x in (0.02, 0.1, 0.5, 1.0, 1.5, 2.0)],
            "anillo": caida_adim(1.0) / caida_adim(0.1), "pads": casos}


def ancho_drenado_m(np_m3: float, bo: float, h_m: float, phi: float, sw: float, fr: float, rama_m: float) -> float:
    """Equivalent drained width: A = Np Bo / (h phi (1 - Sw) FR), width = A / lateral length. Textbook volumetrics."""
    return np_m3 * bo / (h_m * phi * (1.0 - sw) * fr) / rama_m


def mediana_indices(indice, n_ev: int, sel, k: int) -> float | None:
    """Median over the events in sel of the stored index at offset k, skipping months without a row."""
    ancho = K_MAX - K_MIN + 1
    vals = [indice[e * ancho + k - K_MIN] for e in sel if indice[e * ancho + k - K_MIN] != SIN_INDICE]
    return median(vals) / ESCALA_INDICE if vals else None


def elegir_acto2(hijos: list[int], meses_ev: list[int], control: list[bool], indice, completos_hijo: set[int],
                 mediana_cuenca: float) -> tuple[int, int, list[int], list[int]] | None:
    """REGLA_ACTO2 over the embedded events: (child, month index, near event indices, control event indices)."""
    ancho = K_MAX - K_MIN + 1
    grupos: dict[tuple[int, int], tuple[list[int], list[int]]] = {}
    for e, (h, m) in enumerate(zip(hijos, meses_ev)):
        if all(indice[e * ancho + j] != SIN_INDICE for j in range(ancho)):
            grupos.setdefault((m, h), ([], []))[1 if control[e] else 0].append(e)
    mejor = None
    for (m, h), (cerca, ctrl) in sorted(grupos.items()):
        if h not in completos_hijo or len(cerca) < MIN_PADRES_ACTO2 or len(ctrl) < MIN_PADRES_ACTO2:
            continue
        dist = abs(median(indice[e * ancho + 1 - K_MIN] for e in cerca) / ESCALA_INDICE - mediana_cuenca)
        if mejor is None or dist < mejor[0]:
            mejor = (dist, h, m, cerca, ctrl)
    return None if mejor is None else mejor[1:]


# ---- warehouse readers ----

def linea_de_tiempo(con) -> list[date]:
    """Months from the first one with MIN_ACTIVE producing mapped wells to the last data month (as the replay)."""
    ultimo = _d(q(con, "select mes from ultimo_mes")[0][0])
    activos = q(con, """
        select f.mes, count(*) from fct_produccion f join int_pozo_ubicacion u using (pozo_id)
        where f.petroleo_m3 > 0 group by 1 order by 1""")
    y, m = (lambda d: (d.year, d.month))(min(_d(mes) for mes, c in activos if c >= MIN_ACTIVE))
    meses = []
    while date(y, m, 1) <= ultimo:
        meses.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return meses


def profundidades(raw_dir: Path = DATA / "raw") -> dict[int, float]:
    """Total measured depth by well from the raw production file (the warehouse does not keep the column)."""
    try:
        ruta = raw_dir / load_manifest()["produccion_no_convencional"]["path"]
    except (KeyError, OSError, ValueError):
        return {}
    if not ruta.exists():
        return {}
    con = duckdb.connect()
    try:
        return {r[0]: float(r[1]) for r in con.execute(
            "select idpozo, max(profundidad) from read_csv(?) group by 1 having max(profundidad) > 0",
            [str(ruta)]).fetchall()}
    finally:
        con.close()


def leer_pozos(con, meses: list[date], md: dict[int, float]) -> tuple[dict, dict[int, int]]:
    filas = q(con, """
        select u.pozo_id, d.sigla, u.operador, u.area, u.pad_id, u.lon, u.lat, u.primer_mes_petroleo,
               f.primera_fractura, f.rama_horizontal_m, f.etapas, f.arena_tn, f.agua_m3, p.np_m3
        from int_pozo_ubicacion u
        join dim_pozo d using (pozo_id)
        left join dim_fractura_pozo f using (pozo_id)
        left join (
            -- suma en orden fijo: sin el order by, el paralelismo cambia el último bit y dos corridas difieren
            select pozo_id, sum(petroleo_m3 order by mes, petroleo_m3) as np_m3 from fct_produccion group by 1
        ) p using (pozo_id)
        order by u.pozo_id""")
    ops = sorted({f[2] for f in filas})
    areas = sorted({f[3] for f in filas})
    oi, ai = {o: i for i, o in enumerate(ops)}, {a: i for i, a in enumerate(areas)}
    t0 = meses[0].year * 12 + meses[0].month
    pozos = {
        "id": [f[0] for f in filas], "sigla": [f[1] for f in filas], "op": [oi[f[2]] for f in filas],
        "area": [ai[f[3]] for f in filas], "pad": [int(f[4][1:]) for f in filas],
        "lon": [round(f[5], 5) for f in filas], "lat": [round(f[6], 5) for f in filas],
        "mes0": [None if f[7] is None else f[7].year * 12 + f[7].month - t0 for f in filas],
        "frac": [None if f[8] is None else _d(f[8]).isoformat() for f in filas],
        "md": [_r(md.get(f[0]), 0) for f in filas],
        "rama": [_r(f[9], 0) for f in filas], "etapas": [f[10] for f in filas],
        "arena": [_r(f[11], 0) for f in filas], "agua": [_r(f[12], 0) for f in filas],
        "np": [_r(f[13] or 0.0, 0) for f in filas],
    }
    return {"pozos": pozos, "operadores": ops, "areas": areas}, {f[0]: i for i, f in enumerate(filas)}


def matriz_caudal(con, idx: dict[int, int], mi: dict[date, int]) -> array:
    n, nm = len(idx), len(mi)
    caudal = array("H", [SIN_FILA]) * (n * nm)
    for pid, mes, pet, dias in q(con, """
            select f.pozo_id, f.mes, f.petroleo_m3, f.dias_mes
            from fct_produccion f join int_pozo_ubicacion u using (pozo_id) order by 1, 2"""):
        k = mi.get(_d(mes))
        if k is None or pet is None:
            continue
        caudal[idx[pid] * nm + k] = codificar_caudal(pet / dias * BBL_PER_M3)
    return caudal


def codificar_caudal(bbl_d: float) -> int:
    """Rate in tenths of bbl/d for a Uint16. It never clips: a rate that does not fit stops the export.

    A month with oil never encodes as zero: under 0,05 bbl/d it is stored as one tenth, the smallest step. A zero in
    the matrix then means a month without oil, so the wells with a rate above zero are the producing wells that
    pipeline.replay counts (bit 1 of its estado matrix) and both pages show one number.
    """
    v = int(round(bbl_d * ESCALA_CAUDAL))
    if bbl_d > 0 and v == 0:
        v = 1
    if not 0 <= v < SIN_FILA:
        raise ValueError(f"caudal de {bbl_d:.1f} bbl/d fuera del rango que entra en Uint16 con escala {ESCALA_CAUDAL}")
    return v


def leer_fracs(con, idx: dict[int, int], meses: list[date]) -> tuple[array, array]:
    fin = meses[-1].replace(day=calendar.monthrange(meses[-1].year, meses[-1].month)[1])
    filas = sorted({(_d(f), idx[p]) for p, f in q(con, """
        select pozo_id, fecha from fct_evento where tipo = 'fractura' and fecha is not null""")
        if p in idx and meses[0] <= _d(f) <= fin})
    return array("H", [p for _f, p in filas]), array("H", [(f - meses[0]).days for f, _p in filas])


def leer_eventos(con, idx: dict[int, int], mi: dict[date, int]) -> dict[str, array]:
    """Near and control events with the parent's index for k = -3..6, ordered by band, month and parent."""
    ancho = K_MAX - K_MIN + 1
    ev = q(con, """
        select padre, mes_frac, banda, grupo_edad, km_min, hijo_cercano, base_m3_d
        from int_interferencia_evento where banda in ('cercano', 'control')
        order by banda, mes_frac, padre""")
    pos = {(e[0], _d(e[1])): i for i, e in enumerate(ev)}
    indice = array("H", [SIN_INDICE]) * (len(ev) * ancho)
    for padre, mes_frac, k, ind in q(con, """
            select padre, mes_frac, k, indice from int_interferencia_mes
            where banda in ('cercano', 'control') and indice is not null"""):
        if K_MIN <= k <= K_MAX:
            indice[pos[(padre, _d(mes_frac))] * ancho + k - K_MIN] = min(TOPE_INDICE, int(round(ind * ESCALA_INDICE)))
    return {
        "padre": array("H", [idx[e[0]] for e in ev]),
        "hijo": array("H", [idx[e[5]] for e in ev]),
        "mes": array("H", [mi[_d(e[1])] for e in ev]),
        "km": array("H", [int(round(e[4] * 1000)) for e in ev]),
        "base": array("H", [min(65535, int(round(e[6] * BBL_PER_M3 * ESCALA_CAUDAL))) for e in ev]),
        "flags": array("B", [(1 if e[2] == "control" else 0) | (GRUPOS.index(e[3]) << 1) for e in ev]),
        "indice": indice,
    }


def leer_curvas(con) -> tuple[dict, list]:
    curva = {b: [None] * (K_MAX - K_MIN + 1) for b in ("cercano", "control")}
    for b, k, v in q(con, "select banda, k, indice_mediana from mart_interferencia_curva "
                          "where banda in ('cercano', 'control')"):
        if K_MIN <= k <= K_MAX:
            curva[b][k - K_MIN] = _r(v)
    brecha = [[None] * (K_MAX - K_MIN + 1) for _ in GRUPOS]
    for g, k, v in q(con, "select grupo_edad, k, brecha from mart_interferencia_brecha"):
        if K_MIN <= k <= K_MAX:
            brecha[GRUPOS.index(g)][k - K_MIN] = _r(v)
    return curva, brecha


def leer_publicado(con) -> dict:
    """Numbers already published in the wiki, read from their marts."""
    bl = {m: (e, lo, hi, n) for m, e, lo, hi, n in q(con, """
        select metrica, estimacion, ic_bajo_5km, ic_alto_5km, bloques_5km from mart_bloques
        where k = 1 and metrica in ('brecha_mes1_base_original', 'brecha_mes1_descontada')""")}
    orig, desc = bl["brecha_mes1_base_original"], bl["brecha_mes1_descontada"]
    t = q(con, """select eventos, diferido_medio_bbl, diferido_ic_bajo_bbl, diferido_ic_alto_bbl, diferido_bajo_bbl
                  from mart_decision_edad where grupo_edad = 'todos'""")[0]
    n_ctrl = q(con, "select n_control from mart_anillo where variante = 'V0' and k = 1")[0][0]
    # Los eventos que se dibujan y se cuentan en la página salen de la misma tabla. El recuento de los marts deja
    # afuera a un evento sin dato en el mes 1, y restarlo del total lo haría pasar por control.
    n_cerca = q(con, "select count(*) from int_interferencia_evento where banda = 'cercano'")[0][0]
    return {
        "brecha_mes1": _r(orig[0]), "brecha_mes1_descontada": _r(desc[0]),
        "ic5_bajo": _r(orig[1]), "ic5_alto": _r(orig[2]), "bloques_5km": int(orig[3]),
        "n_cercanos": int(n_cerca), "n_controles_mes1": int(n_ctrl),
        "cierre": [{"variante": v, "control": d, "brecha1": _r(b1), "brecha6": _r(b6), "parte": _r(p)}
                   for v, d, b1, b6, p in q(con, "select * from mart_decision_cierre order by variante")],
        "dif_bbl": _r(t[1], 1), "dif_ic_bajo_bbl": _r(t[2], 1), "dif_ic_alto_bbl": _r(t[3], 1),
        "dif_bajo_bbl": _r(t[4], 1),
        "cota_bbl": _r(q(con, "select cota_bbl from mart_decision_perdida")[0][0], 1),
    }


def leer_cuenca(con, mi: dict[date, int]) -> dict:
    """Basin series by operator in kbbl/d: YPF, the next N_OPS - 1 by last month, and the rest (as the replay)."""
    ultimo = {r[0]: r[1] for r in q(con, """
        select operador, petroleo_kbbl_d from mart_vm_mensual where mes = (select mes from ultimo_mes)""")}
    top = ["YPF"] + [o for o in sorted(ultimo, key=lambda o: (-ultimo[o], o)) if o != "YPF"][: N_OPS - 1]
    kbbl = {o: [0.0] * len(mi) for o in top + ["Otros"]}
    for mes, op, v in q(con, "select mes, operador, petroleo_kbbl_d from mart_vm_mensual order by mes, operador"):
        k = mi.get(_d(mes))
        if k is not None:
            kbbl[op if op in top else "Otros"][k] += v or 0.0
    return {"ops": top + ["Otros"], "kbbl": [[round(v, 3) for v in kbbl[o]] for o in top + ["Otros"]]}


# ---- reference answers of the self-test ----

def brecha_medianas(curva: dict) -> list[float | None]:
    """Gap of the two medians per relative month: near minus control, None where either is missing."""
    return [None if a is None or b is None else a - b for a, b in zip(curva["cercano"], curva["control"])]


def autotest_serie(pozos: dict, caudal: array, nm: int, cuenca: dict, inicio: tuple[int, int], frac_dia) -> dict:
    """Reference answers for the timeline chart and the scene events (see the contract, autotest.serie)."""
    n = len(pozos["id"])
    fm = fracs_por_mes(frac_dia, inicio, nm)
    dias = sorted({0, 27, 30, 31, 59, 365, 1000, *(list(frac_dia)[:: max(1, len(frac_dia) // 6)])})
    return {
        "fracs_mes": fm, "pico_fracs": pico(fm), "llegadas": llegadas_por_mes(pozos, inicio, nm),
        "partes": [{"m": m, "partes": partes_cuenca(cuenca, m)} for m in sorted({nm - 1, max(0, nm - 13), nm // 2, 0})],
        "acumulado": [{"p": p, "m": m, "bbl": acumulado_bbl(caudal, nm, p, m, inicio)}
                      for p in sorted({min(n - 1, i * max(1, n // AT_ACUMULADO)) for i in range(AT_ACUMULADO)})
                      for m in (nm - 1, nm // 2)],
        "dias": [{"dia": d, "mes": mes_de_dia(inicio, d)} for d in dias],
    }


def autotest(pozos: dict, caudal: array, nm: int, brecha: list, curva: dict, cuenca: dict, inicio: tuple[int, int],
             operadores: list[str], areas: list[str], frac_dia=()) -> dict:
    n = len(pozos["id"])
    totales = []
    for m in sorted({nm - 1, nm - 13, nm - 61, nm // 2, nm // 4, 0}):
        col = [caudal[p * nm + m] for p in range(n)]
        totales.append({"m": m, "kbbl": sum(fila[m] for fila in cuenca["kbbl"]),
                        "activos": sum(1 for v in col if v != SIN_FILA and v > 0),
                        "suma_bbl_d": sum(v for v in col if v != SIN_FILA) / ESCALA_CAUDAL})
    casos = []
    paso = max(1, n // AT_POSICIONES)
    for i in range(AT_POSICIONES):
        p = min(n - 1, i * paso)
        lon = round(pozos["lon"][p] + AT_DESPLAZAMIENTO[0], 5)
        lat = round(pozos["lat"][p] + AT_DESPLAZAMIENTO[1], 5)
        m = nm - 1 if i % 2 == 0 else nm - 1 - 12 * (1 + i % 5)
        r = plantar(lon, lat, m, pozos["lon"], pozos["lat"], pozos["mes0"], caudal, nm, brecha, inicio)
        casos.append({"lon": lon, "lat": lat, "m": m, "n_cercanos": len(r["cercanos"]),
                      "n_intermedio": r["n_intermedio"], "n_control": r["n_control"],
                      "base_bbl_d": r["base_bbl_d"], "diferido_bbl": r["diferido_bbl"], "por_mes": r["por_mes"],
                      "por_padre_bbl": r["por_padre_bbl"],
                      "costo_usd": costo_de_diferir(r["diferido_bbl"], AT_PRECIO, AT_TASA, AT_REZAGO)})
    vecinos = []
    for i in range(AT_VECINOS):
        p = min(n - 1, i * max(1, n // AT_VECINOS))
        v = vecino_otro_pad(p, pozos["lon"], pozos["lat"], pozos["pad"])
        if v is not None:
            vecinos.append({"p": p, "q": v[0], "km": v[1]})
    fisica = []
    for k_md in (1e-4, 1e-2, 1.0, 1000.0):          # 100 nD matrix to 1 D fracture network
        for phi, mu, ct in ((0.08, 0.5, 1.5e-5), (0.12, 1.2, 8e-6), (0.05, 0.3, 3e-5)):
            fisica.append({"k_md": k_md, "t_h": 720.0, "phi": phi, "mu_cp": mu, "ct_psi": ct,
                           "r_ft": radio_investigacion_ft(k_md, 720.0, phi, mu, ct),
                           "r_m": radio_investigacion_m(k_md, 720.0, phi, mu, ct),
                           "t_1km_h": tiempo_a_radio_h(1000.0 / FT_M, k_md, phi, mu, ct),
                           "k_1km_md": permeabilidad_a_radio_md(1000.0 / FT_M, 720.0, phi, mu, ct)})
    drenaje = [{"np_m3": np_m3, "bo": bo, "h_m": h, "phi": phi, "sw": sw, "fr": fr, "rama_m": rama,
                "ancho_m": ancho_drenado_m(np_m3, bo, h, phi, sw, fr, rama)}
               for np_m3, rama in ((50000.0, 2500.0), (120000.0, 3200.0))
               for bo, h, phi, sw, fr in ((1.4, 30.0, 0.08, 0.3, 0.08), (1.6, 60.0, 0.12, 0.4, 0.05),
                                          (1.2, 100.0, 0.06, 0.25, 0.12), (1.5, 45.0, 0.1, 0.35, 0.1))]
    return {"tol_rel": 1e-9, "tol_mediana": 1.5e-4, "tol_si": 1e-3, "precio": AT_PRECIO, "tasa": AT_TASA,
            "rezago": AT_REZAGO, "totales": totales, "plantar": casos, "vecinos": vecinos, "fisica": fisica,
            "drenaje": drenaje, "brecha_mediana": brecha_medianas(curva),
            "serie": autotest_serie(pozos, caudal, nm, cuenca, inicio, frac_dia),
            "frente": autotest_frente(pozos, nm),
            "busquedas": [{"q": c, **buscar(c, pozos, operadores, areas)}
                          for c in consultas_de_prueba(pozos, operadores, areas)]}


def autotest_base(base: dict, pozos: dict) -> dict:
    """Reference answers for the base map: what the page must get when it decodes the relief and the vector layers."""
    z = base_mapa.decodificar_relieve(base["relieve"])
    caja = tuple(base["caja"])
    lon0, lat0, lon1, lat1 = caja
    n = len(pozos["id"])
    # With the finer relief of the core, the elevation the page draws is the blend of the two grids.
    fino = base_mapa.abrir_fino(base["relieve_fino"]) if "relieve_fino" in base else None
    cotas = [base_mapa.cota_mixta(z, caja, fino, pozos["lon"][p], pozos["lat"][p]) for p in range(n)]
    dentro = [c for c in cotas if c is not None]
    paso = max(1, n // AT_BOCAS)
    puntos = [(lon0, lat1), (lon1, lat0), ((lon0 + lon1) / 2, (lat0 + lat1) / 2), (lon0 - 0.01, lat0), (lon1, lat1 + 0.01)]
    capas = {}
    for capa, clave in (("rios", "l"), ("agua", "p"), ("limites", "l"), ("bloques", "p")):
        partes = [base_mapa.decodificar_linea(s) for e in base[capa] for s in e[clave]]
        capas[capa] = {"n": len(base[capa]), "partes": len(partes), "puntos": sum(len(q) for q in partes),
                       "suma": sum(x + y for q in partes for x, y in q)}
    ref = {"celdas": int(z.size), "suma": int(z.sum()), "min": int(z.min()), "max": int(z.max()),
           "bocas": [{"p": p, "m": cotas[p]} for p in (min(n - 1, i * paso) for i in range(AT_BOCAS))],
           "fuera": n - len(dentro), "mediana_m": median(dentro) if dentro else None,
           "tope_m": max(dentro) if dentro else None,
           "puntos": [{"lon": lon, "lat": lat, "m": base_mapa.cota_mixta(z, caja, fino, lon, lat)} for lon, lat in puntos],
           "capas": capas, "localidades": len(base["localidades"])}
    if fino is not None:
        # Fixed points of the finer relief: its centre, its edge, just outside, and inside the blend margin on
        # each side and in a corner, each with the weight the finer grid gets there.
        f0, g0, f1, g1 = fino["caja"]
        dx, dy = f1 - f0, g1 - g0
        m = fino["margen"]
        pts = [(f0 + dx / 2, g0 + dy / 2), (f0, g0 + dy / 2), (f0 - dx / 100, g0 + dy / 2),
               (f0 + dx * m / 2, g0 + dy / 2), (f1 - dx * m / 3, g0 + dy / 3), (f0 + dx / 3, g1 - dy * m / 4),
               (f0 + dx * .7, g0 + dy * m * .8), (f0 + dx * m / 2, g1 - dy * m / 2)]
        zf = fino["z"]
        ref["fino"] = {"celdas": int(zf.size), "suma": int(zf.sum()), "min": int(zf.min()), "max": int(zf.max()),
                       "puntos": [{"lon": lon, "lat": lat, "w": base_mapa.peso_fino(fino["caja"], m, lon, lat),
                                   "m": base_mapa.cota_mixta(z, caja, fino, lon, lat)} for lon, lat in pts]}
    return ref


def leer_base_mapa(path: Path = BASE_MAPA) -> dict | None:
    """The base map that pipeline.base_mapa writes (relief, water, borders, towns and blocks); None when absent.

    The finer relief of the core is the file next to it: when it is there the map carries it as relieve_fino,
    and when it is not the page draws the sheet grid everywhere.
    """
    if not path.exists():
        return None
    mapa = json.loads(path.read_text(encoding="utf-8"))
    fino = path.parent / base_mapa.FINO.name
    if fino.exists():
        mapa["relieve_fino"] = json.loads(fino.read_text(encoding="utf-8"))
    return mapa


def leer_base_foto(path: Path = BASE_FOTO) -> dict | None:
    """The ground imagery that pipeline.base_foto pins, as the page embeds it; None when its manifest is absent.

    Two WebP layers travel inside the page as base64: the whole base-map box and a finer tile over the core. Each
    file is checked against its manifest entry (bytes and sha256), so the page never carries an image other than
    the pinned one; a manifest without one of its files stops the build, it never drops the image silently. The
    acquisition dates, the scene count and the credit line come from the same manifest.
    """
    if not path.exists():
        return None
    m = json.loads(path.read_text(encoding="utf-8"))
    capas = []
    for nombre in ("caja", "nucleo"):
        e = m["imagenes"][nombre]
        archivo = path.parent / e["archivo"]
        if not archivo.exists():
            raise SystemExit(f"falta {e['archivo']}, que {path.name} fija: recuperalo del repo o corré "
                             "python -m pipeline.base_foto")
        datos = archivo.read_bytes()
        if len(datos) != e["bytes"] or hashlib.sha256(datos).hexdigest() != e["sha256"]:
            raise SystemExit(f"{e['archivo']} no coincide con {path.name}: corré python -m pipeline.base_foto --fijar")
        capas.append({"nombre": nombre, "caja": list(m[nombre]), "ancho": e["ancho"], "alto": e["alto"],
                      "sha256": e["sha256"], "webp": base64.b64encode(datos).decode("ascii")})
    return {"capas": capas, "desde": m["desde"], "hasta": m["hasta"], "escenas": len(m["escenas"]),
            "atribucion": m["atribucion"], "url_licencia": m["url_licencia"], "fecha_descarga": m["fecha_descarga"]}


def mes_de_fecha(inicio: tuple[int, int], fecha: str) -> int:
    """Clock month (index from the first data month; may fall before or after the data) of a 'yyyy-mm-dd' date."""
    return (int(fecha[:4]) - inicio[0]) * 12 + int(fecha[5:7]) - inicio[1]


def autotest_foto(foto: dict, inicio: tuple[int, int]) -> dict:
    """Reference answers for the ground imagery: what the page must read back from the bytes it embeds."""
    capas = []
    for c in foto["capas"]:
        datos = base64.b64decode(c["webp"])
        ancho, alto = base_foto.tam_webp(datos)
        capas.append({"bytes": len(datos), "suma": sum(datos), "ancho": ancho, "alto": alto})
    return {"capas": capas, "mes_desde": mes_de_fecha(inicio, foto["desde"]),
            "mes_hasta": mes_de_fecha(inicio, foto["hasta"]), "escenas": foto["escenas"]}


# ---- assembly ----

def collect(con, raw_dir: Path = DATA / "raw", base_path: Path = BASE_MAPA, foto_path: Path = BASE_FOTO) -> dict:
    meses = linea_de_tiempo(con)
    mi = {d: i for i, d in enumerate(meses)}
    nm = len(meses)
    md = profundidades(raw_dir)
    base, idx = leer_pozos(con, meses, md)
    pozos = base["pozos"]
    caudal = matriz_caudal(con, idx, mi)
    frac_pozo, frac_dia = leer_fracs(con, idx, meses)
    ev = leer_eventos(con, idx, mi)
    curva, brecha = leer_curvas(con)
    cuenca = leer_cuenca(con, mi)
    inicio = (meses[0].year, meses[0].month)

    completos = {p for p in range(len(pozos["id"]))
                 if pozos["frac"][p] and pozos["etapas"][p] and pozos["arena"][p] and pozos["agua"][p]}
    control = [bool(f & 1) for f in ev["flags"]]
    elegido = elegir_acto2(list(ev["hijo"]), list(ev["mes"]), control, ev["indice"], completos, curva["cercano"][1 - K_MIN])
    if elegido is None:
        raise SystemExit("ningún evento cumple la regla del acto 2")
    hijo, mes_ev, cerca, ctrl = elegido
    acto2 = {"hijo": hijo, "mes": mes_ev, "fecha": pozos["frac"][hijo], "etapas": pozos["etapas"][hijo],
             "arena": pozos["arena"][hijo], "agua": pozos["agua"][hijo], "cercanos": cerca, "controles": ctrl}

    h = hashlib.sha1()
    for a in (caudal, *ev.values()):
        h.update(a.tobytes())
    meta = {
        "meses": [month_key(d) for d in meses], "n_pozos": len(pozos["id"]), "n_eventos": len(ev["padre"]),
        "hash_datos": h.hexdigest()[:12], "mes_datos": month_key(meses[-1]),
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "operadores": base["operadores"], "areas": base["areas"],
        "escala_caudal": ESCALA_CAUDAL, "sin_fila": SIN_FILA, "escala_indice": ESCALA_INDICE,
        "sin_indice": SIN_INDICE, "k_min": K_MIN, "k_max": K_MAX, "bbl_m3": BBL_PER_M3,
        "profundidad": bool(md), "rezago_carga_desde": max(0, nm - MESES_REZAGO_CARGA),
        "busca_min": BUSCA_MIN, "busca_max": BUSCA_MAX, "vecindad_km": VECINDAD_KM,
    }
    mapa = leer_base_mapa(base_path)
    referencias = autotest(pozos, caudal, nm, brecha, curva, cuenca, inicio, base["operadores"], base["areas"],
                           frac_dia)
    if mapa is not None:
        referencias["base"] = autotest_base(mapa, pozos)
    # The imagery drapes over the base map's relief with no reprojection: no base map, or another box, no imagery.
    foto = leer_base_foto(foto_path) if mapa is not None else None
    if foto is not None:
        if foto["capas"][0]["caja"] != list(mapa["caja"]):
            raise SystemExit("la imagen del suelo no cubre la caja del mapa base: corré python -m pipeline.base_foto")
        referencias["foto"] = autotest_foto(foto, inicio)
    return {
        "meta": meta, "pozos": pozos, "caudal": b64(caudal),
        "fracs": {"pozo": b64(frac_pozo), "dia": b64(frac_dia)},
        "eventos": {k: b64(v) for k, v in ev.items()},
        "curva": curva, "brecha": brecha, "pub": leer_publicado(con), "cuenca": cuenca, "acto2": acto2,
        "autotest": referencias, "base": mapa, "foto": foto,
    }


def textos(d: dict) -> dict[str, str]:
    """Numbers of the page's static text, already formatted in Spanish. pipeline.claims pins each one."""
    p = d["pub"]
    b6 = [c["brecha6"] for c in p["cierre"]]
    n_ev = d["meta"]["n_eventos"]
    return {
        "mes_datos": d["meta"]["mes_datos"],
        "n_pozos": num(d["meta"]["n_pozos"]),
        "n_cercanos": num(p["n_cercanos"]),
        "n_controles": num(n_ev - p["n_cercanos"]),
        "rango_bajo": num(abs(100 * p["brecha_mes1_descontada"])),
        "rango_alto": num(abs(100 * p["brecha_mes1"])),
        "brecha1": num(abs(100 * p["brecha_mes1"])),
        "ic5_bajo": num(abs(100 * p["ic5_alto"])),
        "ic5_alto": num(abs(100 * p["ic5_bajo"])),
        "bloques_5km": num(p["bloques_5km"]),
        "cierre_min": num(min(-100 * b for b in b6), 1),
        "cierre_max": num(max(-100 * b for b in b6), 1),
        "dif_bbl": num(p["dif_bbl"]),
        "dif_ic_bajo_bbl": num(p["dif_ic_bajo_bbl"]),
        "dif_ic_alto_bbl": num(p["dif_ic_alto_bbl"]),
        "cota_bbl": num(p["cota_bbl"]),
        "regla_acto2": REGLA_ACTO2,
    }


def render(data: dict, out: Path) -> int:
    html = TEMPLATE.read_text(encoding="utf-8")
    for clave, valor in textos(data).items():
        html = html.replace("{{" + clave + "}}", valor)
    if "{{" in html:
        raise ValueError("quedó un marcador sin reemplazar en la plantilla del mundo")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    html = html.replace("/*__DATA__*/null", payload)
    html = html.replace("/*__SISTEMA__*/", sistema_css())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"{out} is {size} bytes, over the {MAX_BYTES} byte budget")
    return size


def main() -> int:
    con = duckdb.connect(str(DATA / "warehouse.duckdb"), read_only=True)
    try:
        data = collect(con)
    finally:
        con.close()
    size = render(data, OUT)
    print(f"wrote {OUT} ({size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
