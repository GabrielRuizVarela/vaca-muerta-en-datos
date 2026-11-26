"""Pruebas de falsacion del estudio de eventos de interferencia: pretendencia, fechas falsas y eje con fechas permutadas.

Se corre despues de pipeline.build:  uv run python -m pipeline.placebo

Escribe en data/warehouse.duckdb (create or replace, idempotente, con semilla fija):
  mart_placebo_pretrend                 brecha cercano menos control en k = -3..3, con base fuera de la ventana probada
  mart_placebo_pretrend_base_original   lo mismo con la base del resultado principal (meses -3 a -1)
  mart_placebo_pretrend_sin_previos     lo mismo que la principal sin eventos con otro hijo a menos de 2 km en los 6 meses previos
  mart_placebo_fechas                   brecha del mes 1 con la fecha de fractura del hijo corrida +-6 y +-12 meses
  mart_placebo_permutacion              brecha del mes 1 con las fechas de fractura permutadas entre hijos del mismo ano
  mart_placebo_eje                      eje axial con las fechas permutadas (debe quedar indefinido)

Que mide cada prueba (el resultado principal es: un mes despues de la fractura de un hijo, los padres a menos de 1 km
rinden unos 23 puntos menos de su caudal previo que los controles a 2 a 5 km; mediana de cada grupo, indice = caudal
del mes / media de los meses -3 a -1):
  (1) Pretendencia. Si los padres cercanos ya rendian distinto antes de la fractura, la brecha del mes 1 no es efecto de
      la fractura. Como el indice principal tiene como base los meses -3 a -1, en esos meses vale 1 por construccion en
      promedio y no puede mostrar nada. Por eso la tabla principal usa como base los meses -6 a -4 y prueba k = -3..3;
      la tabla con la base original se publica al lado.
  (2) Fechas falsas. Se corre la fecha de fractura de todos los hijos d meses (d = -12, -6, 6, 12), se conservan los
      pares padre e hijo y se exige que el padre tenga al menos 6 meses de produccion y datos en la ventana. Una brecha
      real no deberia aparecer en una fecha falsa.
  (3) Permutacion. Cada hijo recibe la fecha de fractura de otro hijo del mismo ano (N_PERM permutaciones, semilla
      fija). Se recalculan eventos, bandas y la brecha del mes 1; el eje axial se ajusta con el mismo estimador de
      pipeline.costo sobre esos eventos.

Que NO prueba:
  * Un resultado limpio no demuestra causalidad: descarta una brecha previa y una brecha que aparezca en cualquier fecha,
    no un cierre protector del operador ni una fractura de otro pozo cercano en esos meses.
  * Con fechas falsas el padre cercano puede haber sido golpeado de verdad por otro hijo en la ventana (las fracturas
    se agrupan en el tiempo y en el espacio), asi que una brecha distinta de cero en una fecha falsa tiene mas de una
    lectura; el informe lo dice y no lo corrige.
  * Los intervalos son bootstrap por conglomerados de pads hijo, sin ajuste por comparaciones multiples.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline.costo import (ANCHO_MAX, KM_MIN_EJE, P_EJE_COSTO, REPS_EJE, REPS_PERM, SEMILLA, _clusters, _controles_eje, _escribir,
                            _remuestra, ajustar_eje, eje_con_intervalo)
from pipeline.ingest import DATA

SEMILLA_PLACEBO = SEMILLA + 15
REPS_BOOT = REPS_EJE            # repeticiones del bootstrap por pads hijo de cada brecha
N_PERM = 200                    # permutaciones de fechas entre hijos del mismo ano
N_EJE_COMPLETO = 10             # permutaciones a las que se les calcula el IC y el p del eje (las demas solo amplitud)
DESPLAZAMIENTOS = (-12, -6, 6, 12)
KS_PRE = tuple(range(-3, 4))
BASE_ORIGINAL = (-3, -1)
BASE_LIMPIA = (-6, -4)
EDAD_MIN = 6                    # meses de produccion del padre en la fecha del evento (como en el resultado principal)
BASE_MIN = 1.0                  # m3/d de petroleo de la base para que el padre entre (como en el resultado principal)
KM_PREVIOS = 2.0                # un hijo a menos de esta distancia cuenta como golpe previo en la prueba sin previos
VENTANA_PREVIOS = 6             # meses previos que se miran para ese golpe
PAD = 40                        # columnas de relleno a cada lado del eje de meses
M0 = 2000 * 12

COLS_PRE = [("k", "integer"), ("n_near", "integer"), ("n_ctrl", "integer"), ("indice_cercano", "double"),
            ("indice_control", "double"), ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_FECHAS = [("desplazamiento_meses", "integer"), ("n", "integer"), ("brecha_mes1", "double"), ("ic_bajo", "double"),
               ("ic_alto", "double"), ("brecha_real", "double")]
COLS_PERM = [("n_perm", "integer"), ("eventos_cercanos_medio", "double"), ("media", "double"), ("sd", "double"),
             ("p025", "double"), ("p975", "double"), ("minimo", "double"), ("maximo", "double"), ("brecha_real", "double"),
             ("p_inferior", "double")]
COLS_EJE = [("escenario", "varchar"), ("n", "integer"), ("eje", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
            ("ancho_ic", "double"), ("amplitud", "double"), ("amplitud_p95", "double"), ("p_perm", "double"),
            ("definido", "boolean")]

SQL_PARES = """
select h.hijo, p.pozo_id as padre,
       111.32 * sqrt(power((p.lon - c.lon) * cos(radians(c.lat)), 2) + power(p.lat - c.lat, 2)) as km,
       (degrees(atan2((p.lon - c.lon) * cos(radians(c.lat)), p.lat - c.lat)) + 360) % 180 as rumbo_eje
from int_frac_hijo h
join int_pozo_ubicacion c on c.pozo_id = h.hijo
join int_pozo_ubicacion p
  on p.pozo_id <> h.hijo and abs(p.lat - c.lat) < 0.05 and abs(p.lon - c.lon) < 0.07 and p.primer_mes_petroleo is not null
where 111.32 * sqrt(power((p.lon - c.lon) * cos(radians(c.lat)), 2) + power(p.lat - c.lat, 2)) < 5
order by h.hijo, p.pozo_id
"""


def _mes_idx(fechas) -> np.ndarray:
    """Meses desde 2000-01; una fecha faltante pasa a un mes muy lejano (el pozo nunca cumple la regla de edad)."""
    return np.array([10**6 if d is None else d.year * 12 + d.month - 1 - M0 for d in fechas], dtype=np.int64)


# ------------------------------------------------------------------ datos y eventos

def cargar(con) -> dict:
    """Pares padre e hijo a menos de 5 km (sin la regla de edad), caudales mensuales de los padres y fechas de fractura."""
    hijos = con.execute("select h.hijo, h.mes_frac, u.pad_id from int_frac_hijo h join int_pozo_ubicacion u on u.pozo_id = h.hijo "
                        "order by h.hijo").fetchall()
    padres = con.execute("select pozo_id, primer_mes_petroleo, trim(area), lat from int_pozo_ubicacion order by pozo_id").fetchall()
    pares = con.execute(SQL_PARES).fetchall()
    prod = con.execute("select x.pozo_id, x.mes, x.petroleo_m3 / x.dias_mes from fct_produccion x "
                       "join int_pozo_ubicacion u on u.pozo_id = x.pozo_id order by x.pozo_id, x.mes").fetchall()
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
    pm = _mes_idx([r[1] for r in prod])
    pi = np.array([pos_padre[r[0]] for r in prod], dtype=np.int64)
    tasa[pi, pm + PAD] = np.array([np.nan if r[2] is None else r[2] for r in prod], dtype=float)
    d = {
        "hijo_id": hijo_id, "hijo_mes": mes_hijo, "hijo_anio": np.array([h[1].year for h in hijos]),
        "hijo_pad": np.array([pad_cod[h[2]] for h in hijos], dtype=np.int64),
        "primer": _mes_idx([p[1] for p in padres]), "area": np.array([p[2] or "" for p in padres]),
        "lat": np.array([p[3] for p in padres], dtype=float), "tasa": tasa,
        "par_hijo": np.array([pos_hijo[p[0]] for p in pares], dtype=np.int64),
        "par_padre": np.array([pos_padre[p[1]] for p in pares], dtype=np.int64),
        "par_km": np.array([p[2] for p in pares], dtype=float), "par_rumbo": np.array([p[3] for p in pares], dtype=float),
        "n_mes": ancho - 2 * PAD,
    }
    d["par_real_ok"] = d["primer"][d["par_padre"]] <= d["hijo_mes"][d["par_hijo"]] - EDAD_MIN
    return d


def _media(D: dict, padre: np.ndarray, mes: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """Media de los caudales de los meses mes+lo..mes+hi, sin contar meses sin dato (nan si no hay ninguno)."""
    cols = mes[:, None] + np.arange(lo, hi + 1)[None, :] + PAD
    v = D["tasa"][padre[:, None], cols]
    n = (~np.isnan(v)).sum(1)
    s = np.nansum(v, axis=1)
    return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def marco(D: dict, mes_hijo: np.ndarray, ks=(1,), base=BASE_ORIGINAL, solo_reales: bool = False,
          sin_previos: bool = False, base_min: float = BASE_MIN) -> dict:
    """Eventos (padre, mes de fractura) para unas fechas de fractura de los hijos dadas, con el indice a los meses `ks`.

    Mismas reglas que pipeline/sql/04_interferencia.sql: el hijo mas cercano (desempate por el menor id) fija la banda,
    el padre tiene al menos EDAD_MIN meses de produccion y una base original (meses -3 a -1) mayor que BASE_MIN.
    Con `base` distinta de la original tambien se exige esa base mayor que BASE_MIN. `solo_reales` conserva solo los
    pares que ya eran elegibles con la fecha real. `sin_previos` descarta los eventos en que el padre tuvo, en los
    VENTANA_PREVIOS meses anteriores, la fractura de otro hijo a menos de KM_PREVIOS km (otro golpe cercano antes).
    """
    mes_par = mes_hijo[D["par_hijo"]]
    ok = D["primer"][D["par_padre"]] <= mes_par - EDAD_MIN
    if solo_reales:
        ok &= D["par_real_ok"]
    sel = np.flatnonzero(ok)
    if sin_previos:
        cerca = np.flatnonzero(D["par_km"] < KM_PREVIOS)
        k_cerca = np.sort(D["par_padre"][cerca] * 100_000 + mes_par[cerca])
    padre, hijo, km = D["par_padre"][sel], D["par_hijo"][sel], D["par_km"][sel]
    mes, rumbo = mes_par[sel], D["par_rumbo"][sel]
    clave = padre * 100_000 + mes
    orden = np.lexsort((D["hijo_id"][hijo], km, clave))
    c = clave[orden]
    primero = orden[np.r_[True, c[1:] != c[:-1]]]
    padre, hijo, km, mes, rumbo = padre[primero], hijo[primero], km[primero], mes[primero], rumbo[primero]
    b0 = _media(D, padre, mes, *BASE_ORIGINAL)
    b1 = b0 if tuple(base) == BASE_ORIGINAL else _media(D, padre, mes, *base)
    ok = (b0 > base_min) & (b1 > base_min)
    if sin_previos:  # fracturas de otros hijos cercanos del mismo padre en los meses mes - VENTANA_PREVIOS .. mes - 1
        base_k = padre * 100_000 + mes
        n_prev = (np.searchsorted(k_cerca, base_k, side="left") - np.searchsorted(k_cerca, base_k - VENTANA_PREVIOS, side="left"))
        ok &= n_prev == 0
    padre, hijo, km, mes, rumbo, b1 = padre[ok], hijo[ok], km[ok], mes[ok], rumbo[ok], b1[ok]
    idx = {k: D["tasa"][padre, mes + k + PAD] / b1 for k in ks}
    banda = np.where(km < 1, 0, np.where(km < 2, 1, 2))
    return {"padre": padre, "hijo": hijo, "km": km, "mes": mes, "rumbo": rumbo, "banda": banda, "idx": idx,
            "clave": D["hijo_pad"][hijo], "edad": mes - D["primer"][padre], "area": D["area"][padre], "lat": D["lat"][padre]}


# ------------------------------------------------------------------ brecha con intervalo

def _med(x: np.ndarray) -> float:
    return float(np.median(x)) if len(x) else float("nan")


def brecha(vals: np.ndarray, banda: np.ndarray) -> tuple[float, float, float]:
    """(mediana cercanos, mediana controles, diferencia) ignorando los datos faltantes."""
    ok = ~np.isnan(vals)
    a, b = _med(vals[ok & (banda == 0)]), _med(vals[ok & (banda == 2)])
    return a, b, a - b


def brecha_ic(vals: np.ndarray, banda: np.ndarray, clave: np.ndarray, reps: int = REPS_BOOT, semilla: int = SEMILLA_PLACEBO) -> dict:
    """Brecha cercano menos control (medianas) con IC 95% por bootstrap de percentiles por conglomerados de pads hijo."""
    ok = ~np.isnan(vals) & (banda != 1)
    v, bd, cl = vals[ok], banda[ok], clave[ok]
    a, b, g = brecha(v, bd)
    out = {"n_near": int((bd == 0).sum()), "n_ctrl": int((bd == 2).sum()), "near": a, "ctrl": b, "brecha": g,
           "ic_bajo": float("nan"), "ic_alto": float("nan")}
    if out["n_near"] < 5 or out["n_ctrl"] < 5:
        return out
    grupos = _clusters(cl)
    rng = np.random.default_rng(semilla)
    gs = []
    for _ in range(reps):
        i = _remuestra(rng, grupos)
        gs.append(brecha(v[i], bd[i])[2])
    gs = np.array(gs)
    gs = gs[~np.isnan(gs)]
    if len(gs):
        out["ic_bajo"], out["ic_alto"] = (float(x) for x in np.percentile(gs, [2.5, 97.5]))
    return out


# ------------------------------------------------------------------ pruebas

def tabla_pretendencia(D: dict, base=BASE_LIMPIA, ks=KS_PRE, reps: int = REPS_BOOT, sin_previos: bool = False,
                       base_min: float = BASE_MIN) -> list[tuple]:
    m = marco(D, D["hijo_mes"], ks=ks, base=base, sin_previos=sin_previos, base_min=base_min)
    filas = []
    for j, k in enumerate(ks):
        r = brecha_ic(m["idx"][k], m["banda"], m["clave"], reps, SEMILLA_PLACEBO + 100 + j)
        filas.append((int(k), r["n_near"], r["n_ctrl"], r["near"], r["ctrl"], r["brecha"], r["ic_bajo"], r["ic_alto"]))
    return filas


def tabla_fechas(D: dict, desplazamientos=DESPLAZAMIENTOS, reps: int = REPS_BOOT,
                 base_min: float = BASE_MIN) -> list[tuple]:
    """Brecha del mes 1 con la fecha de fractura corrida d meses. brecha_real: la brecha real en los mismos eventos."""
    real = marco(D, D["hijo_mes"], solo_reales=True, base_min=base_min)
    clave_real = real["padre"] * 100_000 + real["mes"]
    filas = []
    for j, d in enumerate((0,) + tuple(desplazamientos)):
        m = marco(D, D["hijo_mes"] + d, solo_reales=True, base_min=base_min)
        r = brecha_ic(m["idx"][1], m["banda"], m["clave"], reps, SEMILLA_PLACEBO + 200 + j)
        # los mismos eventos con su fecha real: el evento (padre, mes + d) corresponde a (padre, mes)
        en = np.isin(clave_real, m["padre"] * 100_000 + m["mes"] - d)
        g_real = brecha(real["idx"][1][en], real["banda"][en])[2]
        filas.append((int(d), r["n_near"], r["brecha"], r["ic_bajo"], r["ic_alto"], g_real))
    return filas


def permutar_fechas(D: dict, rng) -> np.ndarray:
    """Fechas de fractura de los hijos permutadas entre hijos del mismo ano de fractura."""
    out = D["hijo_mes"].copy()
    for a in np.unique(D["hijo_anio"]):
        ix = np.flatnonzero(D["hijo_anio"] == a)
        out[ix] = D["hijo_mes"][rng.permutation(ix)]
    return out


def _datos_eje(m: dict, n_max: int | None = None, rng=None) -> dict | None:
    """Eventos de 0,3 a 1 km con la caida respecto del control por grupo de edad, como en pipeline.costo."""
    edad, idx = m["edad"], m["idx"][1]
    g = np.where(edad < 12, 0, np.where(edad < 24, 1, np.where(edad < 48, 2, 3)))
    ctl = np.full(4, np.nan)
    for j in range(4):
        x = idx[(m["banda"] == 2) & (g == j) & ~np.isnan(idx)]
        if len(x):
            ctl[j] = np.median(x)
    sel = (m["km"] >= KM_MIN_EJE) & (m["km"] < 1) & ~np.isnan(idx) & ~np.isnan(ctl[g])
    if sel.sum() < 40:
        return None
    if n_max is not None and sel.sum() > n_max:  # misma cantidad de eventos que la muestra real (la amplitud depende de n)
        pos = np.flatnonzero(sel)
        sel = np.zeros(len(sel), dtype=bool)
        sel[rng.choice(pos, n_max, replace=False)] = True
    area = m["area"][sel]
    caida = np.clip(ctl[g][sel], 0, 2) - np.clip(idx[sel], 0, 2)
    ev = {"km": m["km"][sel], "edad": edad[sel].astype(float), "lat": m["lat"][sel]}
    return {"caida": caida, "ctrl": _controles_eje(ev), "rumbo": m["rumbo"][sel], "clave": m["clave"][sel],
            "grupo": np.unique(area, return_inverse=True)[1], "n": int(sel.sum())}


def _fila_eje(nombre: str, e: dict, reps: int, reps_perm: int, semilla: int) -> tuple:
    r = eje_con_intervalo(e["caida"], e["ctrl"], e["rumbo"], e["clave"], grupo=e["grupo"], reps=reps, reps_perm=reps_perm,
                          semilla=semilla)
    definido = bool(r["p_perm"] < P_EJE_COSTO and r["ancho_ic"] < ANCHO_MAX)
    return (nombre, e["n"], r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], r["amplitud"], None, r["p_perm"], definido)


def tabla_permutacion(D: dict, n_perm: int = N_PERM, n_eje_completo: int = N_EJE_COMPLETO, reps: int = REPS_EJE,
                      reps_perm: int = REPS_PERM) -> tuple[tuple, list[tuple]]:
    """Brecha del mes 1 y eje axial con las fechas permutadas. Devuelve (fila de mart_placebo_permutacion, filas del eje)."""
    real = marco(D, D["hijo_mes"])
    g_real = brecha(real["idx"][1], real["banda"])[2]
    e_real = _datos_eje(real)
    rng = np.random.default_rng(SEMILLA_PLACEBO + 300)
    gaps, n_cerc, amps = [], [], []
    filas_eje = [_fila_eje("real", e_real, reps, reps_perm, SEMILLA)] if e_real else []
    for p in range(n_perm):
        m = marco(D, permutar_fechas(D, rng))
        gaps.append(brecha(m["idx"][1], m["banda"])[2])
        n_cerc.append(int((m["banda"] == 0).sum()))
        e = _datos_eje(m, e_real["n"] if e_real else None, rng)
        if e is None:
            continue
        amps.append(ajustar_eje(e["caida"], e["ctrl"], e["rumbo"], e["grupo"])[1])
        if p < n_eje_completo:
            filas_eje.append(_fila_eje(f"permutacion {p + 1}", e, reps, reps_perm, SEMILLA_PLACEBO + 500 + p))
    gaps = np.array(gaps)
    p_inf = float((1 + (gaps <= g_real).sum()) / (1 + len(gaps)))
    fila_perm = (n_perm, float(np.mean(n_cerc)), float(gaps.mean()), float(gaps.std(ddof=1)), float(np.percentile(gaps, 2.5)),
                 float(np.percentile(gaps, 97.5)), float(gaps.min()), float(gaps.max()), float(g_real), p_inf)
    if e_real and amps:
        amp_real = filas_eje[0][6]
        amps = np.array(amps)
        p_amp = float((1 + (amps >= amp_real).sum()) / (1 + len(amps)))
        filas_eje.append(("resumen de permutaciones", e_real["n"], None, None, None, None, float(np.median(amps)),
                          float(np.percentile(amps, 95)), p_amp, None))
    return fila_perm, filas_eje


# ------------------------------------------------------------------ pagina

def _g(x: float, dec: int = 0) -> str:
    """Numero con coma decimal y punto de miles; el signo menos solo si no se redondea a cero."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/d"
    if round(x, dec) == 0:
        x = 0.0
    s = f"{abs(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if x < 0 else "") + s


def _pts(x: float) -> str:
    return _g(100 * x, 1)


def _tabla_pre(filas: list[tuple]) -> list[str]:
    L = ["| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |",
         "| ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for k, nn, nc, a, b, g, lo, hi in filas:
        L.append(f"| {k} | {_g(nn)} | {_g(nc)} | {_g(a, 3)} | {_g(b, 3)} | {_pts(g)} | {_pts(lo)} a {_pts(hi)} |")
    return L


def pagina_placebo(con) -> str:
    pre = con.execute("select * from mart_placebo_pretrend order by k").fetchall()
    orig = con.execute("select * from mart_placebo_pretrend_base_original order by k").fetchall()
    sinp = con.execute("select * from mart_placebo_pretrend_sin_previos order by k").fetchall()
    fechas = con.execute("select * from mart_placebo_fechas order by desplazamiento_meses").fetchall()
    perm = con.execute("select * from mart_placebo_permutacion").fetchone()
    eje = con.execute("select * from mart_placebo_eje").fetchall()
    L = ["# Pruebas de falsación del estudio de eventos", "",
         "Página generada por `pipeline/placebo.py`. Somete el resultado principal de interferencia (al mes 1 de la fractura de un "
         "hijo, los padres a menos de 1 km conservan unos 23 puntos menos de su caudal previo que los controles a 2 a 5 km) a tres "
         "pruebas en las que ese resultado no debería aparecer: una brecha previa a la fractura, brechas en fechas de fractura "
         "falsas y un eje de mayor merma con las fechas permutadas. Los intervalos son bootstrap por pads hijo (400 repeticiones, "
         f"semilla fija); el resumen de las permutaciones usa {_g(perm[0])} sorteos.", ""]
    L += ["## Pretendencia", "",
          "Brecha entre padres cercanos (menos de 1 km del hijo) y controles (2 a 5 km), en medianas del índice, en los meses "
          "alrededor de la fractura (k = 0 es el mes de la fractura). Como la base del índice principal son los meses -3 a -1, "
          "ahí el índice vale 1 por construcción en promedio y no puede mostrar una diferencia previa; por eso la tabla "
          "principal toma como base los meses -6 a -4, que no se usan como mes de prueba. Los padres deben tener "
          "datos en esa base y producir más de 1 m3/d.", ""]
    L += _tabla_pre(pre)
    L += ["", "Con la base del resultado principal (meses -3 a -1) la lectura de k = -3 a -1 queda forzada, pero k = 0 a 3 "
          "reproduce las cifras publicadas:", ""]
    L += _tabla_pre(orig)
    L += ["", f"Sin los eventos en que el padre tuvo, en los {VENTANA_PREVIOS} meses anteriores, la fractura de otro hijo a menos de "
          f"{_g(KM_PREVIOS)} km (para descartar que la brecha previa sea un golpe anterior de un pozo vecino del mismo pad), con la base de -6 a -4:", ""]
    L += _tabla_pre(sinp)
    L += ["", "## Fechas de fractura falsas", "",
          "Se corre la fecha de fractura de todos los hijos d meses, se conservan los pares padre e hijo y se exige que el padre "
          "tenga al menos 6 meses de producción en la fecha falsa y datos en los meses -3 a -1 (el mes 1 puede faltar y entonces no entra). La brecha real se calcula en "
          "los mismos eventos con su fecha verdadera. d = 0 es el resultado principal. Solo los desplazamientos de -6 y -12 meses son placebos limpios (la fecha falsa cae antes de la fractura real); con +6 y +12 el mes 1 falso puede caer sobre meses ya afectados por la fractura real, así que una brecha ahí no refuta nada.", "",
          "| Desplazamiento (meses) | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% (puntos) | Brecha real en los mismos eventos (puntos) |",
          "| ---: | ---: | ---: | --- | ---: |"]
    for d, n, g, lo, hi, gr in fechas:
        L.append(f"| {d} | {_g(n)} | {_pts(g)} | {_pts(lo)} a {_pts(hi)} | {_pts(gr)} |")
    L += ["", "## Fechas permutadas", "",
          f"Con {_g(perm[0])} permutaciones de las fechas de fractura entre hijos del mismo año (unos {_g(perm[1])} eventos cercanos por "
          f"sorteo), la brecha del mes 1 tiene media {_pts(perm[2])} puntos, desvío {_pts(perm[3])} y un rango de {_pts(perm[4])} a "
          f"{_pts(perm[5])} (percentiles 2,5 y 97,5; extremos {_pts(perm[6])} y {_pts(perm[7])}). La brecha real, {_pts(perm[8])} puntos, "
          f"{'queda fuera de' if perm[8] < perm[6] or perm[8] > perm[7] else 'queda dentro de'} ese rango; la fracción de permutaciones con una brecha tan "
          f"negativa o más es {_g(perm[9], 3)} (el mínimo posible con {_g(perm[0])} sorteos es {_g(1 / (1 + perm[0]), 3)}).", ""]
    L += ["## Eje de mayor merma con fechas permutadas", "",
          "Mismo ajuste axial coseno, mismos controles y efectos fijos de área que `pipeline/costo.py`, sobre los eventos de 0,3 a "
          "1 km, con las fechas permutadas. El eje se considera definido si el p de permutación es menor que 0,10 y el IC mide "
          "menos de 90 grados. Para las primeras permutaciones se calcula el eje con su intervalo; el resumen compara la "
          "amplitud del término angular de todas las permutaciones con la real.", "",
          "| Escenario | Eventos | Eje (grados) | IC 95% (grados) | Ancho IC | Amplitud | p permutación | Definido |",
          "| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    for esc, n, ej, lo, hi, an, amp, p95, p, df in eje:
        if ej is None:
            L.append(f"| {esc} | {_g(n)} | n/d | n/d | n/d | mediana {_g(amp, 3)}, p95 {_g(p95, 3)} | {_g(p, 3)} | n/d |")
        else:
            L.append(f"| {esc} | {_g(n)} | {_g(ej)} | {_g(lo)} a {_g(hi)} | {_g(an)} | {_g(amp, 3)} | {_g(p, 3)} | {'sí' if df else 'no'} |")
    L += ["", "En la fila de resumen el p es la fracción de permutaciones con una amplitud al menos igual a la real. Un intervalo "
          "de ejes puede cruzar los 180 grados (el límite inferior queda numéricamente por encima del superior): el eje es axial y "
          "el intervalo cierra la vuelta.", ""]
    L += ["## Qué se concluye", ""] + _conclusion(pre, orig, sinp, fechas, perm, eje)
    L += ["", "## Qué no prueba", "",
          "- Pasar estas pruebas no demuestra causalidad. Descarta una brecha previa y una brecha que aparezca en cualquier fecha; "
          "no separa el daño de un cierre o estrangulamiento protectivo del operador, que en datos mensuales se ve igual.",
          "- Con fechas falsas el padre cercano pudo ser golpeado por otro hijo en la ventana, porque las fracturas se agrupan en "
          "el tiempo y el espacio; una brecha en una fecha falsa tiene entonces más de una lectura.",
          "- Los intervalos son bootstrap por pads hijo sin ajuste por comparaciones múltiples; con 7 meses de prueba y 4 "
          "desplazamientos, alguno puede quedar fuera de su intervalo por azar.",
          "- La base de -6 a -4 exige datos en esos meses y deja fuera padres muy jóvenes, así que la muestra de la tabla de "
          "pretendencia es algo menor que la del resultado principal.", ""]
    return "\n".join(L)


def _conclusion(pre, orig, sinp, fechas, perm, eje) -> list[str]:
    previos = [f for f in pre if f[0] < 0]
    fuera = [f for f in previos if not (f[6] <= 0 <= f[7])]
    k1 = next(f for f in pre if f[0] == 1)
    falsas = [f for f in fechas if f[0] != 0]
    fuera_f = [f for f in falsas if not (f[3] <= 0 <= f[4])]
    L = []
    if fuera:
        ks = ", ".join(str(f[0]) for f in fuera)
        L.append(f"- Pretendencia: hay una brecha previa. Con la base de los meses -6 a -4, el IC excluye cero en k = {ks} "
                 f"(brechas de " + ", ".join(_pts(f[5]) for f in fuera) + " puntos), así que los padres cercanos ya rendían distinto "
                 f"antes de la fractura (por un nivel distinto de los padres cercanos o por un efecto anticipado; estos datos no los separan). "
                 f"La brecha del mes 1 con esta base es {_pts(k1[5])} puntos y la parte atribuible a la fractura es menor.")
    else:
        L.append(f"- Pretendencia: no se detecta una brecha previa. En k = -3, -2 y -1 las brechas ({', '.join(_pts(f[5]) for f in previos)} "
                 f"puntos) tienen intervalos que incluyen cero. Con la misma base la brecha del mes 1 es {_pts(k1[5])} puntos "
                 f"(IC {_pts(k1[6])} a {_pts(k1[7])}).")
    if fuera_f:
        L.append("- Fechas falsas: hay brechas con intervalo que excluye cero en d = " + ", ".join(str(f[0]) for f in fuera_f)
                 + " (" + ", ".join(_pts(f[2]) for f in fuera_f) + " puntos). Una brecha en una fecha sin evento no debería aparecer; "
                 "puede venir de otras fracturas cercanas en esos meses o de un patrón de los padres cercanos que no depende de la fecha.")
    else:
        L.append("- Fechas falsas: en los cuatro desplazamientos el intervalo incluye cero ("
                 + ", ".join(f"d = {f[0]}: {_pts(f[2])}" for f in falsas) + " puntos).")
    dentro = perm[8] >= perm[6]
    L.append(f"- Permutación: la brecha real ({_pts(perm[8])} puntos) "
             + ("no se separa de la de las fechas permutadas." if dentro else
                f"queda fuera de las {_g(perm[0])} brechas permutadas (rango {_pts(perm[6])} a {_pts(perm[7])}).")
             + f" La media permutada es {_pts(perm[2])} puntos, no cero: con la fecha de otro hijo del mismo año los padres cercanos rinden "
             "menos que los controles. Una lectura posible es que, en zonas de desarrollo denso, un padre cercano a un hijo también lo está de "
             "otro que sí fracturó en esa fecha; no se verificó.")
    res = next((f for f in eje if f[0].startswith("resumen")), None)
    perms = [f for f in eje if f[0].startswith("permutacion")]
    if res is not None:
        n_def = sum(1 for f in perms if f[9])
        L.append(f"- Eje: de {len(perms)} permutaciones con intervalo, {n_def} dejan un eje definido; la fracción de las {_g(perm[0])} con "
                 f"una amplitud tan grande como la real es {_g(res[8], 3)} (amplitud real {_g(eje[0][6], 3)}, mediana permutada "
                 f"{_g(res[6], 3)}, percentil 95 {_g(res[7], 3)}; las permutaciones se submuestrean a los mismos {_g(eje[0][1])} eventos que la real).")
    km1 = next(f for f in orig if f[0] == 1)
    km1p = next(f for f in pre if f[0] == -1)
    k1s = next((f for f in sinp if f[0] == 1), None)
    km1s = next((f for f in sinp if f[0] == -1), None)
    sp_fuera = [f for f in sinp if f[0] < 0 and not (f[6] <= 0 <= f[7])]
    difs = [abs(k1[5] - km1p[5])] + ([abs(k1s[5] - km1s[5])] if k1s is not None and km1s is not None else [])
    L.append(f"- Qué significa para el resultado principal: la caída de {_pts(abs(km1[5]))} puntos del mes 1 no es un artefacto de una fecha "
             f"cualquiera (las fechas falsas dan cerca de cero y las permutadas dan {_pts(perm[2])} en promedio), pero no sale limpia: "
             f"{'los padres cercanos ya rendían unos ' + _pts(abs(km1p[5])) + ' puntos menos en el mes -1' if fuera else 'sin brecha previa'}"
             f"{', y la brecha previa sigue sin los golpes previos de vecinos (' + ', '.join(_pts(f[5]) for f in sp_fuera) + ' puntos en k = ' + ', '.join(str(f[0]) for f in sp_fuera) + ')' if sp_fuera else ''}. "
             f"Medida contra el nivel previo con la misma base (-6 a -4), la caída adicional al mes 1 es de {_pts(abs(k1[5] - km1p[5]))} puntos"
             + (f" ({_pts(abs(k1s[5] - km1s[5]))} sin los golpes previos de vecinos)" if k1s is not None and km1s is not None else "")
             + ". Ese descuento supone que la brecha previa es un nivel distinto de los padres cercanos que no sigue creciendo; "
             "si fuera un efecto anticipado o una deriva que continúa, el descuento sería otro, y los datos mensuales no permiten separarlos. "
             "Por eso los puntos del resultado principal son una cota superior del efecto, y lo que queda después del descuento es del orden de "
             f"{_pts(min(difs))} a {_pts(max(difs))} puntos, condicional a ese supuesto. "
             "La media permutada no es cero y las fechas permutadas pueden coincidir con golpes reales de hijos vecinos, así que el valor p de la "
             f"permutación ({_g(1 / (perm[0] + 1), 3)} como mínimo con {_g(perm[0])} permutaciones) es un piso, no una probabilidad exacta.")
    return L


# ------------------------------------------------------------------ entrada

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    D = cargar(con)
    _escribir(con, "mart_placebo_pretrend", COLS_PRE, tabla_pretendencia(D, BASE_LIMPIA))
    _escribir(con, "mart_placebo_pretrend_base_original", COLS_PRE, tabla_pretendencia(D, BASE_ORIGINAL))
    _escribir(con, "mart_placebo_pretrend_sin_previos", COLS_PRE, tabla_pretendencia(D, BASE_LIMPIA, sin_previos=True))
    _escribir(con, "mart_placebo_fechas", COLS_FECHAS, tabla_fechas(D))
    perm, eje = tabla_permutacion(D)
    _escribir(con, "mart_placebo_permutacion", COLS_PERM, [perm])
    _escribir(con, "mart_placebo_eje", COLS_EJE, eje)
    for t in ("mart_placebo_pretrend", "mart_placebo_pretrend_base_original", "mart_placebo_pretrend_sin_previos",
              "mart_placebo_fechas", "mart_placebo_permutacion", "mart_placebo_eje"):
        for r in con.execute(f"select * from {t}").fetchall():
            print(f"[placebo] {t[13:]:<22}", tuple(round(x, 3) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
