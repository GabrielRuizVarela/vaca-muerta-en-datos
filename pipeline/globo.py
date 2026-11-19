"""El globo (site/globo.html): la Tierra oscura salvo donde un regulador publica petroleo por pozo, y cada cuenca medida abierta en la misma repeticion mes a mes del mundo.

  uv run python -m pipeline.globo     # data/warehouse.duckdb + data/<cuenca>/warehouse.duckdb + data/fuentes_mundo.json -> site/globo.html

No mide nada nuevo. El color de una jurisdiccion es el nivel que dice la auditoria de fuentes (`data/fuentes_mundo.json`,
`pipeline/fuentes_mundo.py`): un pais oscuro quiere decir "no publica por pozo" (o "no se pudo verificar"), nunca "no produce". Las tres
cuencas medidas (Vaca Muerta, Colorado, Wyoming) abren la repeticion con el motor de `pipeline/mundo_template.html`, que se copia
tal cual en la pagina (`<script id="motor">` y `<script id="nucleo">`): este modulo no tiene un motor propio. El veredicto de cada
cuenca sale de sus marts (`mart_bloques` y `mart_decision_*` en Vaca Muerta, `mart_replicacion_<cuenca>` en las otras dos), no de numeros
pegados, y la pagina verifica al abrir que las medianas que recalcula de los eventos embebidos dan la brecha publicada.

Colorado no tiene registro en la auditoria (se midio antes de que existiera): la pagina lo pinta como medido y lo dice.

Contrato de datos (lo lee `pipeline/globo_template.html`; todo arreglo tipado es zlib de valores little-endian en base64, "z64"):

- geo:       lo de `data/globo_geometria.json` (paises y unidades de Natural Earth, dominio publico, con su sha256 y sus terminos).
- niveles:   {nivel: rotulo} de `fuentes_mundo.NIVELES`.
- jur:       una por registro de la auditoria, mas Colorado: {id, pais, nombre, organismo, nivel, rotulo, entra, geo: ["pais", A3] |
             ["unidad", clave] | null, motivo, fecha_verificada, medida (id de la cuenca medida o null), auditada}.
- cuencas:   las tres medidas: {id, nombre, jur, centro: [lon, lat], tipo ("caso" | "replica"), veredicto, M}. `veredicto` trae las cifras
             de los marts (brecha, IC por bloques de 5 km, n); `M` es el contrato de `pipeline/mundo.py` reducido a lo que el motor lee:
             meta {meses, k_min, k_max, escala_caudal, sin_fila, escala_indice, sin_indice, bbl_m3, operadores, hash_datos, mes_datos},
             pozos {id, sigla, op, lon, lat, mes0, frac, md, rama} (md y rama van en null salvo en Vaca Muerta con el archivo crudo:
             aca siempre null, la profundidad del globo es de esquema), caudal (Uint16, pozos x meses, 0,1 bbl/d, 65535 = mes sin
             fila), fracs {pozo, dia}, eventos {padre, hijo, mes, km, flags, indice} (cercanos y controles de la regla fijada;
             `indice` es Uint16 de eventos x 10, el indice del padre para k = -3..6 por 10000), curva {cercano, control} (medianas
             de los indices sin cuantizar, para que la pagina compare).
  Colorado y Wyoming: solo los pozos que entran al estudio (padres cercanos y de control y los hijos mas cercanos de sus eventos),
  los meses desde 12 antes del primer evento hasta el ultimo con petroleo en esos pozos. Los eventos salen de `placebo.marco`
  con la preparacion de `replicacion.preparar`, es decir los mismos que el veredicto; el exportador para si las medianas no dan
  las del mart.
"""
from __future__ import annotations

import base64
import calendar
import hashlib
import json
import re
import statistics
import sys
import zlib
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

from pipeline import fuentes_mundo, mundo, placebo, replicacion
from pipeline.cuencas import COLORADO, WYOMING, Cuenca
from pipeline.ingest import DATA, ROOT
from pipeline.replay import BBL_PER_M3, month_key
from pipeline.wiki import num

TEMPLATE = Path(__file__).parent / "globo_template.html"
TEMPLATE_MUNDO = Path(__file__).parent / "mundo_template.html"
GEOMETRIA = DATA / "globo_geometria.json"
OUT = ROOT / "site" / "globo.html"
MAX_BYTES = 8 * 1024 * 1024

K_MIN, K_MAX = mundo.K_MIN, mundo.K_MAX
ESCALA_CAUDAL, SIN_FILA = mundo.ESCALA_CAUDAL, mundo.SIN_FILA
ESCALA_INDICE, SIN_INDICE, TOPE_INDICE = mundo.ESCALA_INDICE, mundo.SIN_INDICE, mundo.TOPE_INDICE
MESES_PREVIOS = 12          # el replay de Colorado y Wyoming arranca 12 meses antes del primer evento (o del primer dato)
SIN_RAW = Path("/nonexistent-globo-sin-profundidad")   # la profundidad del globo es de esquema en las tres cuencas

# Jurisdiccion de la auditoria -> poligono ("pais", A3 de Natural Earth) o ("unidad", clave de globo_geometria). El registro nacional
# de fractura no es una jurisdiccion con limites: no se pinta, se lista.
GEO = {
    "ca_bc": ("unidad", "CA-BC"), "ca_ab": ("unidad", "CA-AB"), "ca_sk": ("unidad", "CA-SK"), "ca_mb": ("unidad", "CA-MB"),
    "ar": ("pais", "ARG"), "br": ("pais", "BRA"), "mx": ("pais", "MEX"), "no": ("pais", "NOR"), "gb": ("pais", "GBR"),
    "co": ("pais", "COL"), "au_qld": ("unidad", "AU-QLD"), "au_wa": ("unidad", "AU-WA"), "au_nt": ("unidad", "AU-NT"),
    "cn": ("pais", "CHN"), "ru": ("pais", "RUS"), "sa": ("pais", "SAU"), "dz": ("pais", "DZA"), "ly": ("pais", "LBY"),
    "us_nm": ("unidad", "US-NM"), "us_ut": ("unidad", "US-UT"), "us_mt": ("unidad", "US-MT"), "us_ok": ("unidad", "US-OK"),
    "us_nd": ("unidad", "US-ND"), "us_tx": ("unidad", "US-TX"), "us_pa": ("unidad", "US-PA"), "us_wy": ("unidad", "US-WY"),
    "us_fracfocus": None,
}
# Cuencas medidas: id -> (jurisdiccion de la auditoria o None, poligono, nombre en la pagina).
MEDIDAS = {
    "vaca_muerta": ("ar", ("pais", "ARG"), "Vaca Muerta (Argentina)"),
    "colorado": (None, ("unidad", "US-CO"), "Colorado (cuenca DJ)"),
    "wyoming": ("us_wy", ("unidad", "US-WY"), "Wyoming"),
}
ROTULO_COLORADO = "medida, sin registro en la auditoría"


# ------------------------------------------------------------------ utilidades de codificacion

def z64(datos: bytes) -> str:
    """zlib (nivel 9, determinista) en base64: la pagina lo abre con DecompressionStream('deflate')."""
    return base64.b64encode(zlib.compress(datos, 9)).decode("ascii")


def _h(a: np.ndarray) -> bytes:
    a = np.asarray(a)
    if a.size and (a.min() < 0 or a.max() > 65535):
        raise ValueError(f"globo: un valor no entra en 16 bits ({a.min()} a {a.max()}); el contrato de datos no lo recorta")
    return a.astype("<u2").tobytes()


def _b(a: np.ndarray) -> bytes:
    return np.asarray(a, dtype=np.uint8).tobytes()


def _r(x, d: int = 6):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def mediana_indices(indice: np.ndarray, flags: np.ndarray, control: bool, k: int) -> float | None:
    """Mediana del indice (sin cuantizar al almacenar, aca ya cuantizado) del mes k, de los eventos cercanos o de los de control."""
    col = indice[:, k - K_MIN]
    sel = ((flags & 1) == (1 if control else 0)) & (col != SIN_INDICE)
    return float(np.median(col[sel])) / ESCALA_INDICE if sel.any() else None


# ------------------------------------------------------------------ las tres cuencas medidas

def _meses(m0: int, m1: int) -> list[date]:
    """Meses (indices desde 2000-01, los de placebo) m0..m1 como fechas."""
    return [date((placebo.M0 + m) // 12, (placebo.M0 + m) % 12 + 1, 1) for m in range(m0, m1 + 1)]


def muestra_cuenca(cuenca: Cuenca) -> dict:
    """La cuenca (Colorado o Wyoming) en el contrato del mundo, reducida a los pozos de sus eventos; falla si no da las del mart."""
    if not cuenca.db.exists():
        raise SystemExit(f"globo: falta el almacén de {cuenca.nombre} ({cuenca.db}); la página de esa cuenca no se arma y no se rellena")
    con = duckdb.connect(str(cuenca.db), read_only=True)
    try:
        replicacion.preparar(con)
        D = placebo.cargar(con)
        ks = tuple(range(K_MIN, K_MAX + 1))
        m = placebo.marco(D, D["hijo_mes"], ks=ks)
        pid = np.array([r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()], dtype=np.int64)
        pos_de = {int(v): i for i, v in enumerate(pid)}
        hijo_pos = np.array([pos_de[int(h)] for h in D["hijo_id"]], dtype=np.int64)

        # Los eventos del veredicto: cercanos (banda 0) y de control (banda 2), igual que el exportador del mundo.
        ok = m["banda"] != 1
        padre, hijo = m["padre"][ok], hijo_pos[m["hijo"][ok]]
        mes, km, banda = m["mes"][ok], m["km"][ok], m["banda"][ok]
        edad = m["edad"][ok]
        idx = np.stack([m["idx"][k][ok] for k in ks], axis=1)          # eventos x 10, float, nan sin dato
        pozos_pos = np.array(sorted(set(padre.tolist()) | set(hijo.tolist())), dtype=np.int64)
        local = {int(p): i for i, p in enumerate(pozos_pos)}

        # Meses: desde MESES_PREVIOS antes del primer evento (o del primer dato de esos pozos) hasta el ultimo con petroleo.
        tasa = D["tasa"][pozos_pos][:, placebo.PAD: placebo.PAD + D["n_mes"]]
        con_dato = np.flatnonzero((~np.isnan(tasa)).any(axis=0))
        con_petroleo = np.flatnonzero((np.nan_to_num(tasa) > 0).any(axis=0))
        m0 = max(int(con_dato[0]), int(mes.min()) - MESES_PREVIOS)
        m1 = int(con_petroleo[-1])
        meses = _meses(m0, m1)
        nm = len(meses)
        tasa = tasa[:, m0: m1 + 1]
        bbl = np.rint(tasa * BBL_PER_M3 * ESCALA_CAUDAL)
        if np.nanmax(bbl) >= SIN_FILA:
            raise ValueError(f"{cuenca.nombre}: un caudal no entra en Uint16 con escala {ESCALA_CAUDAL}; no se recorta")
        caudal = np.where(np.isnan(tasa), SIN_FILA, bbl).astype(np.uint16)

        # Datos de superficie y fechas de los pozos de la muestra.
        ids = [int(pid[p]) for p in pozos_pos]
        fila = {r[0]: r for r in con.execute(
            "select pozo_id, sigla, operador, lon, lat from dim_pozo where pozo_id in (select unnest(?::bigint[]))", [ids]).fetchall()}
        fecha_frac = {r[0]: r[1] for r in con.execute(
            "select pozo_id, fecha_frac from co_hijo where hijo and pozo_id in (select unnest(?::bigint[]))", [ids]).fetchall()}
        operadores = sorted({(fila[i][2] or "sin dato") for i in ids})
        op_i = {o: j for j, o in enumerate(operadores)}
        primer = D["primer"][pozos_pos] if len(D["primer"]) == len(pid) else None
        assert primer is not None
        mes0 = [None if v >= 10**5 else int(v) - m0 for v in primer]
        pozos = {
            "id": ids, "sigla": [fila[i][1] or "" for i in ids], "op": [op_i[fila[i][2] or "sin dato"] for i in ids],
            "lon": [round(float(fila[i][3]), 5) for i in ids], "lat": [round(float(fila[i][4]), 5) for i in ids],
            "mes0": mes0, "frac": [fecha_frac[i].isoformat() if i in fecha_frac else None for i in ids],
            "md": [None] * len(ids), "rama": [None] * len(ids),
        }
        origen = meses[0]
        fr = sorted((f, local[pos_de[i]]) for i, f in fecha_frac.items() if origen <= f and pos_de[i] in local)
        fin = meses[-1].replace(day=calendar.monthrange(meses[-1].year, meses[-1].month)[1])   # el último día del último mes con dato, como el mundo
        fr = [(f, p) for f, p in fr if f <= fin]
        fracs_pozo = np.array([p for _f, p in fr], dtype=np.int64)
        fracs_dia = np.array([(f - origen).days for f, _p in fr], dtype=np.int64)

        # Eventos del contrato: cuantizar el indice como el mundo (sin recortar hacia abajo; arriba satura en TOPE_INDICE).
        q = np.where(np.isnan(idx), SIN_INDICE, np.minimum(TOPE_INDICE, np.rint(idx * ESCALA_INDICE))).astype(np.uint16)
        flags = np.array([(1 if b == 2 else 0) | (mundo.grupo_edad(int(e)) << 1) for b, e in zip(banda, edad)], dtype=np.uint8)
        ev = {"padre": np.array([local[int(p)] for p in padre]), "hijo": np.array([local[int(h)] for h in hijo]), "mes": mes - m0,
              "km": np.rint(km * 1000).astype(np.int64), "flags": flags, "indice": q}
        if not (0 <= ev["mes"].min() and ev["mes"].max() < nm):
            raise ValueError(f"{cuenca.nombre}: un evento cae fuera de los meses del replay")

        # Control contra el mart: n y mediana del mes 1, calculados de los indices sin cuantizar.
        v = con.execute(f"select n_cercanos, n_controles, indice_cercano, indice_control, brecha from {cuenca.tabla_veredicto} where k = 1").fetchone()
        i1 = 1 - K_MIN
        cer, ctl = banda == 0, banda == 2
        n_cer, n_ctl = int((~np.isnan(idx[cer, i1])).sum()), int((~np.isnan(idx[ctl, i1])).sum())
        med_cer, med_ctl = float(np.nanmedian(idx[cer, i1])), float(np.nanmedian(idx[ctl, i1]))
        if (n_cer, n_ctl) != (v[0], v[1]) or abs(med_cer - v[2]) > 1e-9 or abs(med_ctl - v[3]) > 1e-9:
            raise SystemExit(f"globo: {cuenca.nombre}: los eventos exportados no dan el mart del veredicto "
                             f"({n_cer}, {n_ctl}, {med_cer:.6f}, {med_ctl:.6f} contra {v})")
        curva = {"cercano": [_r(np.nanmedian(idx[cer, i])) if (~np.isnan(idx[cer, i])).any() else None for i in range(len(ks))],
                 "control": [_r(np.nanmedian(idx[ctl, i])) if (~np.isnan(idx[ctl, i])).any() else None for i in range(len(ks))]}
        veredicto = veredicto_mart(con, cuenca)
    finally:
        con.close()
    h = hashlib.sha1()
    for a in (caudal, *ev.values()):
        h.update(np.asarray(a).tobytes())
    meta = {"meses": [month_key(d) for d in meses], "k_min": K_MIN, "k_max": K_MAX, "escala_caudal": ESCALA_CAUDAL, "sin_fila": SIN_FILA,
            "escala_indice": ESCALA_INDICE, "sin_indice": SIN_INDICE, "bbl_m3": BBL_PER_M3, "operadores": operadores,
            "n_pozos": len(ids), "n_eventos": len(padre), "hash_datos": h.hexdigest()[:12], "mes_datos": month_key(meses[-1])}
    return {
        "meta": meta, "pozos": pozos, "caudal": z64(_h(caudal)),
        "fracs": {"pozo": z64(_h(fracs_pozo)), "dia": z64(_h(fracs_dia))},
        "eventos": {k: z64(_b(v) if k == "flags" else _h(v)) for k, v in ev.items()},
        "curva": curva, "veredicto": veredicto,
        "centro": [round(statistics.median(pozos["lon"]), 4), round(statistics.median(pozos["lat"]), 4)],
    }


def veredicto_mart(con, cuenca: Cuenca) -> dict:
    """Cifras del veredicto de Colorado o Wyoming tal como las publica su mart (en indice, no en puntos)."""
    cols = ["n_cercanos", "n_controles", "indice_cercano", "indice_control", "brecha", "ic_bajo_bloque", "ic_alto_bloque",
            "brecha_previa_limpia", "valor", "se_replica"]
    fila = con.execute(f"select {', '.join(cols)} from {cuenca.tabla_veredicto} where k = 1").fetchone()
    v = dict(zip(cols, fila))
    v = {k: (bool(x) if k == "se_replica" else _r(x) if isinstance(x, float) else x) for k, x in v.items()}
    rec = dict(con.execute("select clave, valor from mart_replicacion_recuentos").fetchall())
    v["pads_hijo"], v["bloques_5km"] = int(rec["pads_hijo_usados"]), int(rec["bloques_5km_usados"])
    v["mes0_es"] = cuenca.fecha_hijo
    return v


def muestra_vaca_muerta() -> dict:
    """Vaca Muerta: lo que ya exporta `pipeline.mundo`, reducido a lo que lee el motor, y el veredicto del caso de estudio."""
    wh = DATA / "warehouse.duckdb"
    if not wh.exists():
        raise SystemExit(f"globo: falta el almacén de Vaca Muerta ({wh})")
    con = duckdb.connect(str(wh), read_only=True)
    try:
        d = mundo.collect(con, raw_dir=SIN_RAW)
    finally:
        con.close()
    p = d["pozos"]
    pozos = {k: p[k] for k in ("id", "sigla", "op", "lon", "lat", "mes0", "frac")}
    pozos["md"], pozos["rama"] = [None] * len(p["id"]), [None] * len(p["id"])
    ev = {k: base64.b64decode(v) for k, v in d["eventos"].items() if k != "base"}
    meta = {k: d["meta"][k] for k in ("meses", "k_min", "k_max", "escala_caudal", "sin_fila", "escala_indice", "sin_indice", "bbl_m3",
                                     "operadores", "n_pozos", "n_eventos", "hash_datos", "mes_datos")}
    pub = d["pub"]
    veredicto = {"brecha_mes1": pub["brecha_mes1"], "brecha_mes1_descontada": pub["brecha_mes1_descontada"],
                 "ic_bajo_bloque": pub["ic5_bajo"], "ic_alto_bloque": pub["ic5_alto"], "bloques_5km": pub["bloques_5km"],
                 "n_cercanos": pub["n_cercanos"], "n_controles": d["meta"]["n_eventos"] - pub["n_cercanos"]}
    return {
        "meta": meta, "pozos": pozos, "caudal": z64(base64.b64decode(d["caudal"])),
        "fracs": {k: z64(base64.b64decode(v)) for k, v in d["fracs"].items()},
        "eventos": {k: z64(v) for k, v in ev.items()}, "curva": d["curva"], "veredicto": veredicto,
        "centro": [round(statistics.median(pozos["lon"]), 4), round(statistics.median(pozos["lat"]), 4)],
    }


# ------------------------------------------------------------------ jurisdicciones y lectura conjunta

def jurisdicciones() -> list[dict]:
    """Una por registro de la auditoria, en el orden de la auditoria, y Colorado (medido, sin registro) al final."""
    regs = fuentes_mundo.cargar()
    sin_mapa = [r["id"] for r in regs if r["id"] not in GEO]
    if sin_mapa:
        raise SystemExit(f"globo: jurisdicciones de la auditoría sin lugar en el globo (agregarlas a GEO): {sin_mapa}")
    medida_de = {jur: cid for cid, (jur, _g, _n) in MEDIDAS.items() if jur}
    out = []
    for r in regs:
        out.append({"id": r["id"], "pais": r["pais"], "nombre": r["jurisdiccion"], "organismo": r["organismo"], "nivel": r["nivel"],
                    "rotulo": fuentes_mundo.NIVELES[r["nivel"]], "entra": bool(r["entra_al_estudio"]),
                    "geo": list(GEO[r["id"]]) if GEO[r["id"]] else None, "motivo": r["motivo"],
                    "fecha_verificada": r["fecha_verificada"], "medida": medida_de.get(r["id"]), "auditada": True})
    out.append({"id": "us_co", "pais": "Estados Unidos", "nombre": "Colorado", "organismo": "COGCC y FracFocus", "nivel": "medida_sin_auditar",
                "rotulo": ROTULO_COLORADO, "entra": True, "geo": ["unidad", "US-CO"],
                "motivo": "Se midió con los archivos del regulador y la divulgación de FracFocus antes de la auditoría de fuentes; "
                          "la auditoría no tiene un registro de Colorado.",
                "fecha_verificada": None, "medida": "colorado", "auditada": False})
    return out


def collect() -> dict:
    cuencas = []
    for cid, (jur, geo, nombre) in MEDIDAS.items():
        m = muestra_vaca_muerta() if cid == "vaca_muerta" else muestra_cuenca(COLORADO if cid == "colorado" else WYOMING)
        cuencas.append({"id": cid, "nombre": nombre, "jur": jur or "us_co", "geo": list(geo), "centro": m.pop("centro"),
                        "tipo": "caso" if cid == "vaca_muerta" else "replica", "veredicto": m.pop("veredicto"), "M": m})
    geom = json.loads(GEOMETRIA.read_text(encoding="utf-8"))
    jur = jurisdicciones()
    h = hashlib.sha1("".join(c["M"]["meta"]["hash_datos"] for c in cuencas).encode()).hexdigest()[:12]
    return {
        "meta": {"hash_datos": h, "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                 "auditoria": "2026-11-19", "n_auditadas": sum(1 for j in jur if j["auditada"])},
        "geo": geom, "niveles": {**fuentes_mundo.NIVELES, "medida_sin_auditar": ROTULO_COLORADO}, "jur": jur, "cuencas": cuencas,
        "lectura": {"replican": sum(1 for c in cuencas if c["tipo"] == "replica" and c["veredicto"]["se_replica"]),
                    "de": sum(1 for c in cuencas if c["tipo"] == "replica")},
    }


# ------------------------------------------------------------------ texto fijo y pagina

def _pts(x: float) -> str:
    """Un indice como puntos con coma decimal y signo menos de teclado (el de las paginas de hallazgos)."""
    return num(100 * x, 1).replace("−", "-")


def _lectura(se_replica) -> str:
    return "se replica" if se_replica else "no se replica"


def _cruza_cero(v: dict) -> bool:
    return v["ic_bajo_bloque"] < 0 < v["ic_alto_bloque"]


def textos(d: dict) -> dict[str, str]:
    """Cifras del texto fijo de la pagina, ya formateadas en castellano; pipeline.claims fija cada una contra los marts."""
    c = {x["id"]: x["veredicto"] for x in d["cuencas"]}
    vm, co, wy = c["vaca_muerta"], c["colorado"], c["wyoming"]
    rec = fuentes_mundo.recuentos(fuentes_mundo.cargar())
    return {
        "n_auditadas": str(rec["total"]), "n_entran": str(rec["entran"]), "n_con_fractura": str(rec["por_pozo_con_fractura"]),
        "vm_rango_bajo": num(abs(100 * vm["brecha_mes1_descontada"])), "vm_rango_alto": num(abs(100 * vm["brecha_mes1"])),
        "co_brecha": _pts(co["brecha"]), "co_ic_bajo": _pts(co["ic_bajo_bloque"]), "co_ic_alto": _pts(co["ic_alto_bloque"]),
        "wy_brecha": _pts(wy["brecha"]), "wy_ic_bajo": _pts(wy["ic_bajo_bloque"]), "wy_ic_alto": _pts(wy["ic_alto_bloque"]),
        "co_replica": str(int(bool(co["se_replica"]))), "co_lectura": _lectura(co["se_replica"]),
        "wy_replica": str(int(bool(wy["se_replica"]))), "wy_lectura": _lectura(wy["se_replica"]),
        "wy_cero_n": str(int(_cruza_cero(wy))),
        "wy_cero": "el intervalo incluye el cero" if _cruza_cero(wy) else "el intervalo no incluye el cero",
        "replican": str(d["lectura"]["replican"]), "de": str(d["lectura"]["de"]),
        "mes_vm": d["cuencas"][0]["M"]["meta"]["mes_datos"], "mes_co": d["cuencas"][1]["M"]["meta"]["mes_datos"],
        "mes_wy": d["cuencas"][2]["M"]["meta"]["mes_datos"],
    }


def _script(html: str, id_: str) -> str:
    m = re.search(r'<script id="' + id_ + r'">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit(f"globo: no encuentro <script id=\"{id_}\"> en la plantilla del mundo")
    return m.group(1)


def render(data: dict, out: Path = OUT) -> int:
    html = TEMPLATE.read_text(encoding="utf-8")
    base = TEMPLATE_MUNDO.read_text(encoding="utf-8")
    for clave, valor in textos(data).items():
        html = html.replace("{{" + clave + "}}", valor)
    html = html.replace("/*__NUCLEO__*/", _script(base, "nucleo")).replace("/*__MOTOR__*/", _script(base, "motor"))
    if "{{" in html:
        raise ValueError("quedó un marcador sin reemplazar en la plantilla del globo")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    html = html.replace("/*__DATA__*/null", payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"{out} is {size} bytes, over the {MAX_BYTES} byte budget")
    return size


def main() -> int:
    data = collect()
    size = render(data, OUT)
    print(f"wrote {OUT} ({size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
