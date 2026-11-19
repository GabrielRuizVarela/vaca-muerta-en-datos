"""El padre en la ventana de gas: el estudio de eventos de interferencia con padres gasiferos y el gas como resultado.

Se corre despues de pipeline.build:  uv run python -m pipeline.gas

REGLA FIJADA ANTES DE CORRER (2026-11-18, antes de calcular ninguna brecha, indice o conteo de eventos con este diseno; no se
cambia despues de ver resultados). Lo unico que se miro antes de fijarla: que hay 759 pozos 'Gasífero' de shale de Vaca Muerta con
ubicacion, la distribucion del caudal mensual de gas de esos pozos (mediana de unos 80 mil m3 por dia calendario, decil 1 de unos 9)
y la cobertura de dias_efectivos (presente en todos los meses; 7.799 meses con 0 dias, 63 meses con gas y 0 dias, 3 con mas dias
que el mes). Ningun indice posterior a una fractura.

Pregunta: todo el estudio de eventos mide al padre en PETROLEO. Un operador de Vaca Muerta tambien desarrolla la ventana de gas.
Cuando un hijo se fractura a menos de 1 km de un padre gasifero, el padre pierde gas al mes siguiente, como pierde petroleo el padre
petrolifero, y se recupera a los 6 meses?

Eventos: el mismo diseno que el resultado principal de petroleo (pipeline.placebo.marco), con estos cambios y nada mas:
  * Padres: pozos de int_pozo_ubicacion con tipo_pozo = 'Gasífero' (el atributo del ultimo mes informado). La edad se cuenta desde
    dim_pozo.primer_mes_produccion (primer mes con petroleo o gas), porque un pozo de gas seco no tiene primer mes de petroleo; el
    padre debe tener al menos EDAD_MIN = 6 meses de produccion en el mes de la fractura del hijo.
  * Hijos: todos los de int_frac_hijo (primera fractura de cada pozo de shale con ubicacion, de cualquier tipo), a menos de 5 km de
    superficie. El hijo mas cercano (desempate por el menor id) fija la banda: cercano a menos de 1 km, control de 2 a 5 km; los de
    1 a 2 km no entran a la brecha.
  * Base: la media del caudal de gas por dia calendario de los meses -3 a -1 debe ser mayor que BASE_MIN_GAS = 1,0 mil m3 por dia
    (en energia, del orden de 1 m3 de petroleo por dia, el umbral del estudio de petroleo). Se implementa pasando base_min a
    placebo.marco (parametro nuevo con el valor de petroleo por defecto, que no cambia nada del estudio de petroleo).

Resultados (indice = valor del mes k / media de los meses -3 a -1 del mismo padre, como en el estudio de petroleo):
  (V) volumen: gas_miles_m3 / dias_mes (caudal por dia calendario; es el volumen del mes). Es el resultado primario.
  (E) caudal por dia efectivo: gas_miles_m3 / dias_efectivos, solo en meses con 0 < dias_efectivos <= dias_mes (si no, falta). La
      base y el umbral de base se calculan con esta misma tasa, asi que el conjunto de eventos de (E) puede diferir en pocos eventos
      del de (V); se informan los dos conteos.
Brecha = mediana del indice de los cercanos menos mediana del de los controles (placebo.brecha), en k = 1 y en k = 6. Cada brecha
lleva dos IC 95% de percentiles con REPS_BOOT repeticiones: por pads hijo (placebo.brecha_ic) y por bloques de 5 km
(bloques.clave_bloque sobre el promedio de lat y lon de los pozos del pad hijo, como en pipeline.bloques). Semillas:
SEMILLA_PLACEBO + 900 + 10 * (0 para V, 1 para E) + (0 si k = 1, 1 si k = 6); la misma semilla para pads y para bloques.

Controles de falsacion del resultado primario (V, k = 1):
  C1, fechas falsas: placebo.tabla_fechas sobre estos eventos (desplazamientos -12, -6, 6 y 12 meses, base_min de gas). Pasa si en
      ninguno de los cuatro la brecha del mes 1 es menor que -0,10 con IC por pads con limite superior menor que cero.
  C2, pretendencia: con la base de los meses -6 a -4 (placebo.BASE_LIMPIA), la brecha de (V) en k = -1. Pasa si su valor absoluto es
      menor que 0,05 o su IC por pads incluye cero. Se publica la serie k = -3 a 3 con esa base.

Minimos (si no se cumplen: "sin muestra", sin veredicto): MIN_CERCANOS = 100 eventos cercanos y MIN_CONTROLES = 100 controles con
dato de (V) en k = 1, y MIN_BLOQUES = 30 bloques de 5 km con eventos.

VEREDICTO (sobre V, k = 1, con el IC por bloques de 5 km; se publican todos los resultados, favorables o no):
  * sostiene: brecha menor que -0,10, limite superior del IC menor que cero, y C1 y C2 pasan.
  * no se sostiene: el IC incluye cero y el valor absoluto de la brecha es menor que 0,05.
  * no firme: cualquier otro caso (entre ellos, la forma de "sostiene" con C1 o C2 sin pasar; el texto dice cual fallo).
  * sin muestra: no se cumplen los minimos.
Cota: con cualquier veredicto distinto de "sin muestra", el limite inferior del IC por bloques de 5 km de (V) en k = 1 se publica
como "cota superior de la caida del mes 1" compatible con el dato publico (en puntos de indice). No es un efecto descartado.

Filas descriptivas, sin veredicto propio:
  * Cierre: la brecha de (V) en k = 6. Se dice "se cierra a los 6 meses" solo si su valor absoluto es menor que 0,05 (el umbral de
    la hipotesis recuperacion_mes6 del petroleo) y su IC por bloques de 5 km incluye cero; si no, "no se cierra a los 6 meses".
  * Dias o caudal: si (V) en k = 1 es menor que -0,10 con IC por bloques bajo cero y el IC por bloques de (E) en k = 1 incluye cero,
    el texto dice "la caida del volumen esta en los dias producidos y no en el caudal por dia"; si (E) tambien queda bajo cero, "la
    caida tambien esta en el caudal por dia"; en otro caso no se dice nada. Con datos mensuales un cierre preventivo y un dano se ven
    igual (pipeline.decision): esta lectura no los separa.
  * Gas diferido por evento cercano, meses 0 a 6: suma de (indice mediano de los controles en k * base del padre - caudal del padre
    en k) * dias_mes, en miles de m3; se publican la mediana por evento, el total y el numero de eventos con los 7 meses.
  * GOR de los padres petroliferos (opcional, declarado aca): sobre los eventos del resultado principal de petroleo
    (placebo.marco con la base original), indice = (gas / petroleo del mes k) / (suma de gas / suma de petroleo de los meses -3 a
    -1), definido si el petroleo del mes k es mayor que cero y la base tiene gas y petroleo; brecha cercano menos control en k = 1 y
    k = 6 con IC por pads. Una brecha positiva dice que la relacion gas petroleo del padre cercano sube respecto del control; puede
    ser un cambio de orificio o la presion bajo el punto de burbuja, y no se lee como causa.

Que NO prueba:
  * Es una huella medida de la brecha entre padres cercanos y controles, no una prueba de causa. Las coordenadas son de superficie,
    no de la rama horizontal.
  * tipo_pozo es lo que declara el operador en su ultimo mes; un pozo puede haber cambiado de ventana.
  * Un cierre preventivo y un dano se ven igual con datos mensuales.
  * Los intervalos no se ajustan por comparaciones multiples (dos resultados, dos meses, dos unidades de remuestreo, el GOR).
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import placebo
from pipeline.bloques import clave_bloque
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, BASE_ORIGINAL, PAD, REPS_BOOT, SEMILLA_PLACEBO, _media, _mes_idx

BASE_MIN_GAS = 1.0
MIN_CERCANOS = 100
MIN_CONTROLES = 100
MIN_BLOQUES = 30
UMBRAL_MES1 = -0.10
UMBRAL_CHICO = 0.05
KS = (1, 6)
DESPLAZAMIENTO_SEMILLA = 900
RESULTADOS = ("V", "E")

COLS_GAS = [("resultado", "varchar"), ("k", "integer"), ("n_near", "integer"), ("n_ctrl", "integer"),
            ("indice_cercano", "double"), ("indice_control", "double"), ("brecha", "double"),
            ("ic_bajo_pad", "double"), ("ic_alto_pad", "double"), ("ic_bajo_5km", "double"),
            ("ic_alto_5km", "double"), ("pads", "integer"), ("bloques_5km", "integer")]
COLS_VEREDICTO = [("veredicto", "varchar"), ("texto", "varchar"), ("c1_pasa", "boolean"), ("c2_pasa", "boolean"),
                  ("cota_mes1", "double"), ("cierre", "varchar"), ("dias_o_caudal", "varchar"),
                  ("diferido_mediana", "double"), ("diferido_total", "double"), ("diferido_eventos", "integer")]

SQL_PADRES_GAS = """
select u.pozo_id, d.primer_mes_produccion, trim(u.area), u.lat
from int_pozo_ubicacion u join dim_pozo d using (pozo_id)
where u.tipo_pozo = 'Gasífero' and d.primer_mes_produccion is not null
order by u.pozo_id
"""

SQL_PARES_GAS = """
select h.hijo, p.pozo_id as padre,
       111.32 * sqrt(power((p.lon - c.lon) * cos(radians(c.lat)), 2) + power(p.lat - c.lat, 2)) as km,
       (degrees(atan2((p.lon - c.lon) * cos(radians(c.lat)), p.lat - c.lat)) + 360) % 180 as rumbo_eje
from int_frac_hijo h
join int_pozo_ubicacion c on c.pozo_id = h.hijo
join int_pozo_ubicacion p
  on p.pozo_id <> h.hijo and abs(p.lat - c.lat) < 0.05 and abs(p.lon - c.lon) < 0.07
   and p.tipo_pozo = 'Gasífero'
join dim_pozo d on d.pozo_id = p.pozo_id and d.primer_mes_produccion is not null
where 111.32 * sqrt(power((p.lon - c.lon) * cos(radians(c.lat)), 2) + power(p.lat - c.lat, 2)) < 5
order by h.hijo, p.pozo_id
"""

SQL_PROD_GAS = """
select x.pozo_id, x.mes, x.gas_miles_m3, x.dias_mes, x.dias_efectivos
from fct_produccion x
join int_pozo_ubicacion u on u.pozo_id = x.pozo_id
join dim_pozo d on d.pozo_id = x.pozo_id
where u.tipo_pozo = 'Gasífero' and d.primer_mes_produccion is not null
order by x.pozo_id, x.mes
"""

SQL_CENTROIDES = """
select h.hijo, c.lat, c.lon
from int_frac_hijo h
join int_pozo_ubicacion u on u.pozo_id = h.hijo
join (select pad_id, avg(lat) as lat, avg(lon) as lon from int_pozo_ubicacion group by pad_id) c
  on c.pad_id = u.pad_id
order by h.hijo
"""


def cargar(con) -> dict:
    """Pares con padres gasiferos, caudales de gas por dia calendario y por dia efectivo, y bloques de 5 km."""
    hijos = con.execute("select h.hijo, h.mes_frac, u.pad_id from int_frac_hijo h join int_pozo_ubicacion u on u.pozo_id = h.hijo "
                        "order by h.hijo").fetchall()
    padres = con.execute(SQL_PADRES_GAS).fetchall()
    pares = con.execute(SQL_PARES_GAS).fetchall()
    prod = con.execute(SQL_PROD_GAS).fetchall()
    ultimo = con.execute("select mes from ultimo_mes").fetchone()[0]
    hijo_id = np.array([h[0] for h in hijos], dtype=np.int64)
    pad_ids = sorted({h[2] for h in hijos})
    pad_cod = {p: i for i, p in enumerate(pad_ids)}
    pid = np.array([p[0] for p in padres], dtype=np.int64)
    pos_padre = {int(v): i for i, v in enumerate(pid)}
    pos_hijo = {int(v): i for i, v in enumerate(hijo_id)}
    mes_hijo = _mes_idx([h[1] for h in hijos])
    ancho = int(_mes_idx([ultimo])[0]) + 1 + 2 * PAD
    tasa = np.full((len(pid), ancho), np.nan)
    tasa_ef = np.full((len(pid), ancho), np.nan)
    dias = np.full((len(pid), ancho), np.nan)
    pm = _mes_idx([r[1] for r in prod])
    pi = np.array([pos_padre[r[0]] for r in prod], dtype=np.int64)
    gv = np.array([np.nan if r[2] is None else r[2] for r in prod], dtype=float)
    dm = np.array([np.nan if r[3] is None else r[3] for r in prod], dtype=float)
    de = np.array([np.nan if r[4] is None else r[4] for r in prod], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        tv = gv / dm
    tv[~(dm > 0)] = np.nan
    te = np.full_like(tv, np.nan)
    ok_ef = (de > 0) & (de <= dm)
    te[ok_ef] = gv[ok_ef] / de[ok_ef]
    tasa[pi, pm + PAD] = tv
    tasa_ef[pi, pm + PAD] = te
    dias[pi, pm + PAD] = dm
    d = {
        "hijo_id": hijo_id, "hijo_mes": mes_hijo, "hijo_anio": np.array([h[1].year for h in hijos]),
        "hijo_pad": np.array([pad_cod[h[2]] for h in hijos], dtype=np.int64),
        "primer": _mes_idx([p[1] for p in padres]), "area": np.array([p[2] or "" for p in padres]),
        "lat": np.array([p[3] for p in padres], dtype=float), "tasa": tasa, "tasa_ef": tasa_ef, "dias": dias,
        "par_hijo": np.array([pos_hijo[p[0]] for p in pares], dtype=np.int64),
        "par_padre": np.array([pos_padre[p[1]] for p in pares], dtype=np.int64),
        "par_km": np.array([p[2] for p in pares], dtype=float), "par_rumbo": np.array([p[3] for p in pares], dtype=float),
        "n_mes": ancho - 2 * PAD,
    }
    d["par_real_ok"] = d["primer"][d["par_padre"]] <= d["hijo_mes"][d["par_hijo"]] - placebo.EDAD_MIN
    cent = con.execute(SQL_CENTROIDES).fetchall()
    cc = {r[0]: (r[1], r[2]) for r in cent}
    lat = np.array([cc[int(h)][0] for h in hijo_id], dtype=float)
    lon = np.array([cc[int(h)][1] for h in hijo_id], dtype=float)
    por_pad = np.zeros(len(pad_ids), dtype=np.int64)
    por_pad[d["hijo_pad"]] = clave_bloque(lat, lon, 5.0)
    d["bloque_5km"] = por_pad
    return d


def marco_resultado(D: dict, resultado: str, ks=KS, base=BASE_ORIGINAL) -> dict:
    """Eventos del resultado V (dia calendario) o E (dia efectivo), con el umbral de base de gas."""
    if resultado == "V":
        return placebo.marco(D, D["hijo_mes"], ks=ks, base=base, base_min=BASE_MIN_GAS)
    if resultado == "E":
        return placebo.marco(dict(D, tasa=D["tasa_ef"]), D["hijo_mes"], ks=ks, base=base, base_min=BASE_MIN_GAS)
    raise ValueError(f"resultado debe ser V o E, no {resultado!r}")


def brecha_dos_ic(vals: np.ndarray, banda: np.ndarray, clave_pad: np.ndarray, clave_5km: np.ndarray,
                  reps: int = REPS_BOOT, semilla: int = SEMILLA_PLACEBO) -> dict:
    """Brecha con IC por pads hijo y por bloques de 5 km, con la misma semilla."""
    r_pad = placebo.brecha_ic(vals, banda, clave_pad, reps, semilla)
    r_5km = placebo.brecha_ic(vals, banda, clave_5km, reps, semilla)
    ok = ~np.isnan(vals) & (banda != 1)
    pads = int(len(np.unique(clave_pad[ok]))) if ok.any() else 0
    bloques = int(len(np.unique(clave_5km[ok]))) if ok.any() else 0
    return {"n_near": r_pad["n_near"], "n_ctrl": r_pad["n_ctrl"], "indice_cercano": r_pad["near"],
            "indice_control": r_pad["ctrl"], "brecha": r_pad["brecha"], "ic_bajo_pad": r_pad["ic_bajo"],
            "ic_alto_pad": r_pad["ic_alto"], "ic_bajo_5km": r_5km["ic_bajo"], "ic_alto_5km": r_5km["ic_alto"],
            "pads": pads, "bloques_5km": bloques}


def filas_brecha(D: dict, reps: int = REPS_BOOT) -> list[tuple]:
    """Una fila por resultado (V, E) y mes k, con las columnas de COLS_GAS."""
    filas = []
    for resultado in RESULTADOS:
        m = marco_resultado(D, resultado, ks=KS)
        for k in KS:
            semilla = (SEMILLA_PLACEBO + DESPLAZAMIENTO_SEMILLA + 10 * (0 if resultado == "V" else 1)
                       + (0 if k == 1 else 1))
            r = brecha_dos_ic(m["idx"][k], m["banda"], m["clave"], D["bloque_5km"][m["clave"]], reps, semilla)
            filas.append((resultado, int(k), r["n_near"], r["n_ctrl"], r["indice_cercano"], r["indice_control"],
                          r["brecha"], r["ic_bajo_pad"], r["ic_alto_pad"], r["ic_bajo_5km"], r["ic_alto_5km"],
                          r["pads"], r["bloques_5km"]))
    return filas


def diferido(D: dict) -> dict:
    """Gas diferido por evento cercano, meses 0 a 6, en miles de m3 (mediana, total y eventos con los 7 meses)."""
    m = marco_resultado(D, "V", ks=range(0, 7))
    ctrl = {}
    for k in range(0, 7):
        v = m["idx"][k][m["banda"] == 2]
        v = v[~np.isnan(v)]
        ctrl[k] = float(np.median(v)) if len(v) else float("nan")
    if any(np.isnan(c) for c in ctrl.values()):
        return {"mediana": float("nan"), "total": 0.0, "eventos": 0}
    sel = np.flatnonzero(m["banda"] == 0)
    vals = []
    for i in sel:
        p, t = int(m["padre"][i]), int(m["mes"][i])
        tk = D["tasa"][p, t + np.arange(0, 7) + PAD]
        if np.isnan(tk).any():
            continue
        base = float(_media(D, np.array([p]), np.array([t]), -3, -1)[0])
        dk = D["dias"][p, t + np.arange(0, 7) + PAD]
        vals.append(float(sum((ctrl[k] * base - tk[k]) * dk[k] for k in range(7))))
    if not vals:
        return {"mediana": float("nan"), "total": 0.0, "eventos": 0}
    return {"mediana": float(np.median(vals)), "total": float(sum(vals)), "eventos": len(vals)}


def c1_pasa(fechas_rows) -> bool:
    """C1 pasa si ninguna fecha falsa muestra una caida del mes 1 menor que -0,10 con IC bajo cero."""
    for r in fechas_rows:
        if r[0] != 0 and r[2] < UMBRAL_MES1 and r[4] < 0:
            return False
    return True


def c2_pasa(pre_rows) -> bool:
    """C2 pasa si la brecha en k = -1 es chica o su IC incluye cero; sin fila de k = -1 o sin IC no se puede mostrar y no pasa."""
    for r in pre_rows:
        if r[0] == -1:
            b, lo, hi = r[5], r[6], r[7]
            if abs(b) < UMBRAL_CHICO:
                return True
            if np.isnan(lo) or np.isnan(hi):
                return False
            return bool(lo <= 0 <= hi)
    return False


def veredicto(prim: dict, c1: bool, c2: bool) -> tuple[str, str]:
    """Veredicto puro sobre la fila de V en k = 1 (dict con los nombres de COLS_GAS) y los dos controles."""
    n, m, b = prim["n_near"], prim["n_ctrl"], prim["bloques_5km"]
    if n < MIN_CERCANOS or m < MIN_CONTROLES or b < MIN_BLOQUES:
        return ("sin muestra", f"muestra bajo los minimos: {n} cercanos, {m} controles, {b} bloques")
    g, lo, hi = prim["brecha"], prim["ic_bajo_5km"], prim["ic_alto_5km"]
    forma = g < UMBRAL_MES1 and hi < 0
    if forma and c1 and c2:
        return ("sostiene", f"brecha {g:.3f} en V k=1 con IC 5km bajo cero y C1 y C2 que pasan")
    if lo <= 0 <= hi and abs(g) < UMBRAL_CHICO:
        return ("no se sostiene", f"brecha {g:.3f} cerca de cero con IC 5km que incluye cero")
    if forma:
        fallos = " y ".join(s for s, ok in (("C1 fechas falsas", c1), ("C2 pretendencia", c2)) if not ok)
        return ("no firme", f"forma de sostiene pero no pasa {fallos}")
    return ("no firme", f"brecha {g:.3f} sin forma de sostiene ni de nula")


def lectura_cierre(fila_v6: dict) -> str:
    """Cierre a los 6 meses: brecha chica con IC 5km que incluye cero."""
    if abs(fila_v6["brecha"]) < UMBRAL_CHICO and fila_v6["ic_bajo_5km"] <= 0 <= fila_v6["ic_alto_5km"]:
        return "se cierra a los 6 meses"
    return "no se cierra a los 6 meses"


def lectura_dias(fila_v1: dict, fila_e1: dict) -> str | None:
    """Dias o caudal: donde esta la caida del volumen de V en k = 1, o nada si V no cae."""
    if fila_v1["brecha"] < UMBRAL_MES1 and fila_v1["ic_alto_5km"] < 0:
        if fila_e1["ic_bajo_5km"] <= 0 <= fila_e1["ic_alto_5km"]:
            return "la caida del volumen esta en los dias producidos y no en el caudal por dia"
        if fila_e1["ic_alto_5km"] < 0:
            return "la caida tambien esta en el caudal por dia"
    return None


def gor_brecha(gas: np.ndarray, oil: np.ndarray, m: dict, ks=KS, reps: int = REPS_BOOT,
               semilla: int = SEMILLA_PLACEBO + DESPLAZAMIENTO_SEMILLA + 50) -> list[tuple]:
    """Brecha del indice de GOR en cada k, sobre un marco del estudio de petroleo (columnas de COLS_PRE)."""
    filas = []
    p, t = np.asarray(m["padre"]), np.asarray(m["mes"])
    cols_base = t[:, None] + np.arange(-3, 0)[None, :] + PAD
    gb = np.nansum(gas[p[:, None], cols_base], axis=1)
    ob = np.nansum(oil[p[:, None], cols_base], axis=1)
    base_ok = (gb > 0) & (ob > 0)
    for j, k in enumerate(ks):
        gk = gas[p, t + k + PAD]
        oc = oil[p, t + k + PAD]
        idx = np.full(len(p), np.nan)
        ok = (oc > 0) & base_ok
        idx[ok] = (gk[ok] / oc[ok]) / (gb[ok] / ob[ok])
        r = placebo.brecha_ic(idx, m["banda"], m["clave"], reps, semilla + j)
        filas.append((int(k), r["n_near"], r["n_ctrl"], r["near"], r["ctrl"], r["brecha"], r["ic_bajo"], r["ic_alto"]))
    return filas


def cargar_gor(con) -> dict:
    """Eventos del resultado principal de petroleo con matrices de volumenes mensuales de gas y petroleo."""
    Doil = placebo.cargar(con)
    m = placebo.marco(Doil, Doil["hijo_mes"], ks=KS)
    pid = [r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()]
    pos = {int(v): i for i, v in enumerate(pid)}
    prod = con.execute("select x.pozo_id, x.mes, x.gas_miles_m3, x.petroleo_m3 from fct_produccion x "
                       "join int_pozo_ubicacion u on u.pozo_id = x.pozo_id order by x.pozo_id, x.mes").fetchall()
    ancho = Doil["tasa"].shape[1]
    gas = np.full((len(pid), ancho), np.nan)
    oil = np.full((len(pid), ancho), np.nan)
    pm = _mes_idx([r[1] for r in prod])
    pi = np.array([pos[r[0]] for r in prod], dtype=np.int64)
    gas[pi, pm + PAD] = np.array([np.nan if r[2] is None else r[2] for r in prod], dtype=float)
    oil[pi, pm + PAD] = np.array([np.nan if r[3] is None else r[3] for r in prod], dtype=float)
    return {"m": m, "gas": gas, "oil": oil}


# ------------------------------------------------------------------ pagina

TEXTO_VEREDICTO = {
    "sostiene": "la brecha del mes 1 es menor que -10 puntos con IC por bloques de 5 km bajo cero, y pasan las fechas falsas y la "
                "pretendencia.",
    "no se sostiene": "la brecha del mes 1 queda a menos de 5 puntos de cero y su IC por bloques de 5 km incluye cero.",
    "no firme": "ni la forma de \"sostiene\" con sus dos controles ni la de \"no se sostiene\".",
    "sin muestra": "no se cumplen los mínimos de eventos y bloques fijados antes de correr.",
}
TEXTO_DIAS = {
    "la caida del volumen esta en los dias producidos y no en el caudal por dia":
        "la caída del volumen está en los días producidos y no en el caudal por día",
    "la caida tambien esta en el caudal por dia": "la caída también está en el caudal por día",
}


def _pts(x: float) -> str:
    return placebo._g(100 * x, 1)


def _leer(con, tabla: str, cols: list[tuple[str, str]]) -> list[dict]:
    nombres = [c for c, _ in cols]
    return [dict(zip(nombres, r)) for r in con.execute(f"select {', '.join(nombres)} from {tabla} order by rowid").fetchall()]


def _lectura_operador(ver: dict, forma: bool, previa: float) -> list[str]:
    """Frases para un operador que dependen del veredicto, de la forma de la brecha del mes 1 y de la brecha del mes -1."""
    L = []
    if ver["veredicto"] == "sostiene":
        L.append("- El padre gasífero cercano produce menos gas el mes siguiente a la fractura del hijo, y la brecha pasa las fechas "
                 "falsas y la pretendencia fijadas antes de correr.")
    elif ver["veredicto"] == "no firme" and forma and not ver["c2_pasa"]:
        antes = "ya venía rindiendo menos que los controles" if previa < 0 else "ya se separaba de los controles"
        L.append("- El padre gasífero cercano produce menos gas el mes siguiente a la fractura del hijo, pero " + antes + " antes de la "
                 "fractura: con la regla fijada, el resultado no alcanza para atribuir la caída a la fractura.")
    elif ver["veredicto"] == "no se sostiene":
        L.append("- Con el dato público no se ve una caída del gas del padre cercano al mes siguiente de la fractura del hijo; la cota "
                 "superior de arriba es la mayor caída compatible con el dato.")
    else:
        L.append("- El resultado no alcanza para decir si el gas del padre cercano cae al mes siguiente de la fractura del hijo.")
    if ver["dias_o_caudal"] == "la caida del volumen esta en los dias producidos y no en el caudal por dia" and \
            ver["cierre"] == "se cierra a los 6 meses":
        L.append("- En la mediana la caída está en los días producidos, no en el caudal por día efectivo, y a los 6 meses la brecha "
                 "queda a menos de 5 puntos: es compatible con cierres del padre durante la fractura del hijo, que con datos mensuales "
                 "no se separan de un daño.")
    return L + [""]


def pagina_gas(con) -> str:
    """Pagina wiki/hallazgos/gas.md desde los marts de main()."""
    g = placebo._g
    filas = {(f["resultado"], f["k"]): f for f in _leer(con, "mart_gas", COLS_GAS)}
    fechas = _leer(con, "mart_gas_fechas", placebo.COLS_FECHAS)
    pre = {f["k"]: f for f in _leer(con, "mart_gas_pretendencia", placebo.COLS_PRE)}
    gor = {f["k"]: f for f in _leer(con, "mart_gas_gor", placebo.COLS_PRE)}
    ver = _leer(con, "mart_gas_veredicto", COLS_VEREDICTO)[0]
    v1, v6, e1, e6 = filas[("V", 1)], filas[("V", 6)], filas[("E", 1)], filas[("E", 6)]
    falsas = [f for f in fechas if f["desplazamiento_meses"] != 0]
    fallo = []
    if not ver["c1_pasa"]:
        fallo.append("las fechas falsas (C1)")
    if not ver["c2_pasa"]:
        fallo.append("la pretendencia (C2)")
    texto_ver = TEXTO_VEREDICTO[ver["veredicto"]]
    forma = bool(v1["brecha"] < UMBRAL_MES1 and v1["ic_alto_5km"] < 0)
    if ver["veredicto"] == "no firme" and forma and fallo:
        texto_ver = ("la brecha del mes 1 tiene la forma de \"sostiene\" (menor que -10 puntos con IC por bloques de 5 km bajo cero), "
                     f"pero no pasa {' ni '.join(fallo)}.")
    L = ["# El padre en la ventana de gas", "",
         "Página generada por `pipeline/gas.py`. Todo el estudio de eventos mide al padre en petróleo; esta página repite el diseño con "
         "padres gasíferos (`tipo_pozo` 'Gasífero') y el gas como resultado, para un operador de Vaca Muerta que también desarrolla "
         "la ventana de gas. La regla, la muestra mínima y el veredicto se fijaron en el código antes de correr. Complementa "
         "[Interferencia entre fracturas](interferencia.md) y las [pruebas de falsación](placebo.md).", "",
         "## Resumen", "",
         f"- **Veredicto: {ver['veredicto']}.** {texto_ver[0].upper()}{texto_ver[1:]}",
         f"- Brecha del gas del mes 1 (volumen, por día calendario): {_pts(v1['brecha'])} puntos de índice "
         f"(IC 95% por bloques de 5 km: {_pts(v1['ic_bajo_5km'])} a {_pts(v1['ic_alto_5km'])}; por pads hijo: {_pts(v1['ic_bajo_pad'])} "
         f"a {_pts(v1['ic_alto_pad'])}), con {g(v1['n_near'])} eventos cercanos y {g(v1['n_ctrl'])} controles en {g(v1['bloques_5km'])} "
         "bloques de 5 km.",
         f"- Pretendencia: con la base de los meses -6 a -4, la brecha entre cercanos y controles ya es de {_pts(pre[-1]['brecha'])} puntos "
         f"en el mes -1, antes de la fractura (IC 95% por pads: {_pts(pre[-1]['ic_bajo'])} a {_pts(pre[-1]['ic_alto'])}), y llega a "
         f"{_pts(pre[1]['brecha'])} en el mes 1.",
    ]
    if ver["cota_mes1"] is not None:
        L.append(f"- Cota superior de la caída del mes 1 compatible con el dato público: {_pts(-ver['cota_mes1'])} puntos de índice.")
    L += [f"- Mes 6: {_pts(v6['brecha'])} puntos (IC 95% por bloques de 5 km: {_pts(v6['ic_bajo_5km'])} a {_pts(v6['ic_alto_5km'])}): "
          f"{ver['cierre']}."]
    if ver["dias_o_caudal"]:
        L.append(f"- Días o caudal: {TEXTO_DIAS[ver['dias_o_caudal']]}. Por día efectivo la brecha del mes 1 es {_pts(e1['brecha'])} "
                 f"puntos (IC 95% por bloques de 5 km: {_pts(e1['ic_bajo_5km'])} a {_pts(e1['ic_alto_5km'])}). Con datos mensuales un "
                 "cierre preventivo y un daño se ven igual: esta lectura no los separa.")
    L += [f"- Gas diferido por evento cercano en los meses 0 a 6, contra el índice mediano de los controles: mediana de "
          f"{g(ver['diferido_mediana'] / 1000, 2)} millones de m3 ({g(ver['diferido_eventos'])} eventos con los 7 meses). Sin descontar la "
          "pretendencia ni los solapes entre eventos del mismo padre.",
          f"- GOR de los padres petrolíferos: la brecha del índice de la relación gas petróleo es {_pts(gor[1]['brecha'])} puntos al mes 1 "
          f"(IC 95% por pads: {_pts(gor[1]['ic_bajo'])} a {_pts(gor[1]['ic_alto'])}) y {_pts(gor[6]['brecha'])} al mes 6 "
          f"(IC 95%: {_pts(gor[6]['ic_bajo'])} a {_pts(gor[6]['ic_alto'])}).", "",
          "## Regla fijada antes de correr", "",
          "Mismos eventos que el resultado principal de petróleo: el hijo más cercano fija la banda (cercano a menos de 1 km, control de 2 "
          "a 5 km), el padre tiene al menos 6 meses de producción y el índice es el caudal del mes sobre la media de los meses -3 a -1. "
          f"Cambia el padre (pozos 'Gasífero', edad desde el primer mes con gas o petróleo) y la base mínima: {g(BASE_MIN_GAS, 1)} mil m3 "
          "de gas por día, del orden en energía del umbral de 1 m3 de petróleo por día.", "",
          "- Resultado primario (V): gas del mes por día calendario. Secundario (E): gas por día efectivo, en meses con días efectivos.",
          f"- Veredicto con el IC por bloques de 5 km de V al mes 1. Sostiene: brecha menor que -10 puntos con IC bajo cero, y pasan C1 "
          "(ninguna de las cuatro fechas falsas, de -12, -6, 6 y 12 meses, da una brecha menor que -10 puntos con IC por pads bajo cero) "
          "y C2 (con base -6 a -4, la brecha del mes -1 queda a menos de 5 puntos o su IC incluye cero). No se sostiene: IC que incluye "
          "cero y brecha a menos de 5 puntos. No firme: cualquier otro caso. Sin muestra: menos de "
          f"{g(MIN_CERCANOS)} cercanos, {g(MIN_CONTROLES)} controles o {g(MIN_BLOQUES)} bloques de 5 km.",
          "- Descriptivo, sin veredicto propio: el cierre al mes 6, la lectura de días o caudal, el gas diferido y el GOR de los padres "
          "petrolíferos.", "",
          "## Resultados", "",
          "Brechas en puntos de índice (mediana de los cercanos menos mediana de los controles).", "",
          "| Resultado | Mes | Cercanos | Controles | Índice cercano | Índice control | Brecha | IC 95% por pads | IC 95% por bloques de 5 km |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    nombre = {"V": "Volumen (día calendario)", "E": "Caudal por día efectivo"}
    for f in (v1, v6, e1, e6):
        L.append(f"| {nombre[f['resultado']]} | {f['k']} | {g(f['n_near'])} | {g(f['n_ctrl'])} | {g(f['indice_cercano'], 3)} | "
                 f"{g(f['indice_control'], 3)} | {_pts(f['brecha'])} | {_pts(f['ic_bajo_pad'])} a {_pts(f['ic_alto_pad'])} | "
                 f"{_pts(f['ic_bajo_5km'])} a {_pts(f['ic_alto_5km'])} |")
    L += ["", "Fechas falsas (C1), brecha del mes 1 del volumen con la fecha de fractura del hijo corrida:", "",
          "| Desplazamiento (meses) | Eventos cercanos | Brecha | IC 95% por pads | Brecha real en los mismos eventos |",
          "| ---: | ---: | ---: | --- | ---: |"]
    for f in fechas:
        L.append(f"| {f['desplazamiento_meses']} | {g(f['n'])} | {_pts(f['brecha_mes1'])} | {_pts(f['ic_bajo'])} a {_pts(f['ic_alto'])} | "
                 f"{_pts(f['brecha_real'])} |")
    L += ["", "Pretendencia (C2), volumen con la base de los meses -6 a -4:", "",
          "| Mes | Cercanos | Controles | Brecha | IC 95% por pads |", "| ---: | ---: | ---: | ---: | --- |"]
    for k in sorted(pre):
        f = pre[k]
        L.append(f"| {k} | {g(f['n_near'])} | {g(f['n_ctrl'])} | {_pts(f['brecha'])} | {_pts(f['ic_bajo'])} a {_pts(f['ic_alto'])} |")
    L += ["", "GOR de los padres petrolíferos (eventos del resultado principal de petróleo):", "",
          "| Mes | Cercanos | Controles | Brecha | IC 95% por pads |", "| ---: | ---: | ---: | ---: | --- |"]
    for k in sorted(gor):
        f = gor[k]
        L.append(f"| {k} | {g(f['n_near'])} | {g(f['n_ctrl'])} | {_pts(f['brecha'])} | {_pts(f['ic_bajo'])} a {_pts(f['ic_alto'])} |")
    L += ["", f"Las fechas falsas dan brechas de {_pts(min(f['brecha_mes1'] for f in falsas))} a {_pts(max(f['brecha_mes1'] for f in falsas))} "
          "puntos; como en el estudio de petróleo, una fecha falsa puede caer sobre el golpe de otro hijo cercano, así que una brecha "
          "distinta de cero en una fecha falsa tiene más de una lectura.", "",
          "## Qué quiere decir para un operador", ""]
    L += _lectura_operador(ver, forma, pre[-1]["brecha"] if -1 in pre else float("nan"))
    L += ["## Límites", "",
          "- Es una huella medida contra un control, no una prueba de causa. Las coordenadas son de superficie, no de la rama.",
          "- `tipo_pozo` es lo que declara el operador en su último mes; un pozo puede haber cambiado de ventana.",
          "- El gas diferido no descuenta la pretendencia ni los solapes, así que no se suma a la cifra de petróleo diferido.",
          "- Los intervalos no se ajustan por comparaciones múltiples (dos resultados, dos meses, dos unidades de remuestreo y el GOR).", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    """Calcula las brechas de gas y escribe las tablas mart_gas_* en el warehouse."""
    con = duckdb.connect(str(path))
    D = cargar(con)
    filas = filas_brecha(D)
    _escribir(con, "mart_gas", COLS_GAS, filas)
    print(f"[gas] mart_gas: {len(filas)} filas")
    fechas = placebo.tabla_fechas(D, reps=REPS_BOOT, base_min=BASE_MIN_GAS)
    _escribir(con, "mart_gas_fechas", placebo.COLS_FECHAS, fechas)
    print(f"[gas] mart_gas_fechas: {len(fechas)} filas")
    pre = placebo.tabla_pretendencia(D, base=BASE_LIMPIA, reps=REPS_BOOT, base_min=BASE_MIN_GAS)
    _escribir(con, "mart_gas_pretendencia", placebo.COLS_PRE, pre)
    print(f"[gas] mart_gas_pretendencia: {len(pre)} filas")
    g = cargar_gor(con)
    gor = gor_brecha(g["gas"], g["oil"], g["m"])
    _escribir(con, "mart_gas_gor", placebo.COLS_PRE, gor)
    print(f"[gas] mart_gas_gor: {len(gor)} filas")
    nombres = [c[0] for c in COLS_GAS]
    por_clave = {(r[0], r[1]): dict(zip(nombres, r)) for r in filas}
    v1, v6, e1 = por_clave[("V", 1)], por_clave[("V", 6)], por_clave[("E", 1)]
    c1, c2 = c1_pasa(fechas), c2_pasa(pre)
    v, t = veredicto(v1, c1, c2)
    dif = diferido(D)
    ver = [(v, t, c1, c2, None if v == "sin muestra" else v1["ic_bajo_5km"], lectura_cierre(v6),
            lectura_dias(v1, e1), dif["mediana"], dif["total"], dif["eventos"])]
    _escribir(con, "mart_gas_veredicto", COLS_VEREDICTO, ver)
    print(f"[gas] mart_gas_veredicto: {v} ({t})")
    con.close()


if __name__ == "__main__":
    main()
