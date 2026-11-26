"""Descomposicion de la brecha de interferencia: dias producidos contra caudal por dia, y alcance por distancia.

Se corre despues de pipeline.build:  uv run python -m pipeline.descomposicion

Escribe en data/warehouse.duckdb (create or replace, idempotente, con semilla fija):
  mart_descomposicion_k          brecha cercano menos control (medianas, solo descriptiva) en k = -6..12 para cuatro paneles
                                 (volumen de petroleo, fraccion de dias efectivos, petroleo por dia efectivo, corte de agua) y,
                                 de referencia, el volumen con la base del resultado principal (meses -3 a -1)
  mart_descomposicion_aditiva    descomposicion aditiva de la brecha: media del logaritmo del indice de volumen = media del
                                 logaritmo del indice de dias + media del logaritmo del indice de caudal por dia, sobre los
                                 mismos eventos, por k, para dos variantes (con y sin los meses cerrados enteros)
  mart_descomposicion_cierres    al mes 1, parte de los eventos con indice de dias menor a 0,9 y parte cerrados todo el mes
  mart_descomposicion_distancia  brecha del mes 1 por banda de distancia al hijo mas cercano contra un anillo lejano, y la de todos
                                 los padres a menos de 1 km contra ese anillo con las dos bases

Que mide (la pregunta de un ingeniero de reservorio: "es un golpe de fractura, que baja el caudal por dia producido, o son
cierres, que bajan los dias producidos?"):
  * Los eventos son los del estudio de eventos: mismos padres elegibles, mismo hijo mas cercano que fija la banda, misma edad
    minima y misma base positiva (pipeline.placebo.marco con la base limpia de los meses -6 a -4, que deja ver la pretendencia).
  * Panel 1, petroleo: caudal por dia calendario del mes sobre su media de la base (el indice principal).
  * Panel 2, dias: dias efectivos del mes sobre dias del mes, sobre su media de la base.
  * Panel 3, caudal por dia efectivo: petroleo del mes sobre dias efectivos, sobre su media de la base (los meses sin dias
    efectivos no tienen caudal por dia y quedan fuera de ese panel).
  * Panel 4, corte de agua: agua sobre agua mas petroleo; la brecha es el cambio del corte respecto de su media de la base, en
    puntos de corte (no se divide, porque la base puede ser cero).
  * Brecha por medianas: mediana de los padres cercanos (menos de 1 km del hijo) menos mediana de los controles (2 a 5 km), en
    puntos del nivel propio de la base. Es descriptiva: las medianas no se suman, asi que no parten una brecha en partes.
  * Brecha aditiva: sobre los eventos presentes en todos los paneles, media del logaritmo de cada indice, cercanos menos
    controles. Volumen = dias por caudal por dia efectivo, asi que el logaritmo del volumen es la suma de los otros dos y la parte
    de cada panel es su brecha sobre la del volumen. Un mes con cero dias efectivos no tiene logaritmo: en la variante principal
    sus dias se acotan a un dia de 30 (DIAS_PISO) y su caudal por dia queda sin cambio (no existe); en la variante sin cerrados
    esos eventos se dejan fuera. Los eventos con petroleo cero y dias positivos (caudal por dia cero) quedan fuera de las dos.
    IC 95% por bootstrap de pads hijo con las repeticiones de pipeline.placebo y la semilla por k de su pretendencia.
  * Distancia: indice de petroleo al mes 1 por banda de distancia del hijo mas cercano (0 a 0,3, 0,3 a 0,6, 0,6 a 1, 1 a 2, 2 a 5)
    contra un anillo lejano (padres con el hijo mas cercano a 5 a 10 km), sin padres con otro hijo a menos de 1 km en los meses
    -6 a +3; las bandas de 1 km o mas tienen la misma restriccion. El propio anillo de 5 a 10 km se compara con 2 a 5 km (misma
    restriccion): una brecha ahi es un gradiente entre zonas, no se separa de la interferencia que llegue mas alla de 5 km.

Que NO prueba:
  * Con datos mensuales un cierre y un golpe dentro del mes se ven igual: un pozo que produce menos horas por dia tiene el mismo
    mes que uno cerrado unos dias. La descomposicion separa dias de caudal por dia dentro del mes, no el motivo.
  * Un efecto parejo hasta 10 km no se ve: solo se ve un gradiente entre 2 a 5 km y 5 a 10 km.
  * Los intervalos son bootstrap por pads hijo, sin ajuste por comparaciones multiples.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import placebo
from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, BASE_ORIGINAL, PAD, REPS_BOOT, _g, _pts

KS = tuple(range(-6, 13))
PANELES = ("petroleo", "dias", "tasa_por_dia", "corte_agua")
PANEL_REF = "petroleo_base_original"
NOMBRES = {"petroleo": "petróleo", "dias": "días efectivos", "tasa_por_dia": "petróleo por día efectivo", "corte_agua": "corte de agua"}
TITULOS = {"petroleo": "Petróleo (caudal por día calendario)", "dias": "Días efectivos (fracción del mes producida)",
           "tasa_por_dia": "Petróleo por día efectivo", "corte_agua": "Corte de agua"}
BANDAS = ((0.0, 0.3), (0.3, 0.6), (0.6, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 10.0))
ANILLO = (5.0, 10.0)
ANILLO_ALT = (2.0, 5.0)         # control de respaldo si el anillo lejano tiene pocos eventos
N_MIN_ANILLO = 200
KM_CERCA = 1.0                  # el control no puede tener un hijo a menos de esta distancia
VENT_PREVIA, VENT_POST = 6, 3   # meses alrededor del evento en que se mira ese hijo
K_DIST = 1
DIAS_PISO = 1 / 30              # fraccion minima de dias efectivos para tomar logaritmo (un dia de 30)
VARIANTES = ("con_cerrados", "sin_cerrados")
UMBRAL_DIAS = 0.9               # indice de dias bajo el cual el padre perdio mas de 10% de sus dias
ETQ_BASE = {BASE_LIMPIA: "-6 a -4", BASE_ORIGINAL: "-3 a -1"}
NOM_LECTURA = {"dias": "se lee como días", "tasa": "se lee como caudal por día", "mixta": "mixta", "sin_brecha": "sin brecha"}
ETQ_TODOS = "0 a 1"             # todos los padres a menos de 1 km

COLS_K = [("panel", "varchar"), ("k", "integer"), ("n_near", "integer"), ("n_ctrl", "integer"), ("mediana_cercano", "double"),
          ("mediana_control", "double"), ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_DIST = [("banda", "varchar"), ("km_desde", "double"), ("km_hasta", "double"), ("control", "varchar"), ("n_banda", "integer"),
             ("n_ctrl", "integer"), ("mediana_banda", "double"), ("mediana_control", "double"), ("brecha", "double"),
             ("ic_bajo", "double"), ("ic_alto", "double"), ("base", "varchar")]
COLS_ADIT = [("variante", "varchar"), ("k", "integer"), ("n_near", "integer"), ("n_ctrl", "integer"), ("brecha_total", "double"),
             ("total_ic_bajo", "double"), ("total_ic_alto", "double"), ("brecha_dias", "double"), ("dias_ic_bajo", "double"),
             ("dias_ic_alto", "double"), ("brecha_tasa", "double"), ("tasa_ic_bajo", "double"), ("tasa_ic_alto", "double"),
             ("parte_dias", "double"), ("parte_dias_ic_bajo", "double"), ("parte_dias_ic_alto", "double"), ("parte_tasa", "double")]
COLS_CIERRES = [("k", "integer"), ("n_near", "integer"), ("n_ctrl", "integer"), ("near_bajo_umbral", "double"),
                ("ctrl_bajo_umbral", "double"), ("near_cerrado", "double"), ("ctrl_cerrado", "double")]


# ------------------------------------------------------------------ datos

def cargar_ext(con, D: dict) -> dict:
    """Agrega a D las matrices por padre y mes: fraccion de dias efectivos, petroleo por dia efectivo y corte de agua."""
    ids = [r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()]
    pos = {int(v): i for i, v in enumerate(ids)}
    rows = con.execute("select x.pozo_id, x.mes, x.petroleo_m3, x.agua_m3, x.dias_efectivos, x.dias_mes from fct_produccion x "
                       "join int_pozo_ubicacion u on u.pozo_id = x.pozo_id order by x.pozo_id, x.mes").fetchall()
    pi = np.array([pos[r[0]] for r in rows], dtype=np.int64)
    pm = placebo._mes_idx([r[1] for r in rows])
    petr, agua, dias, dmes = (np.array([r[j] for r in rows], dtype=float) for j in (2, 3, 4, 5))
    dias = np.minimum(dias, dmes)  # unas decenas de meses informan mas dias efectivos que dias del mes
    with np.errstate(divide="ignore", invalid="ignore"):
        tef = dias / dmes
        tasa_ef = np.where(dias > 0, petr / dias, np.nan)
        suma = petr + agua
        corte = np.where(suma > 0, agua / suma, np.nan)
    forma = D["tasa"].shape
    out = dict(D)
    for nombre, v in (("tef", tef), ("tasa_ef", tasa_ef), ("corte", corte)):
        a = np.full(forma, np.nan)
        a[pi, pm + PAD] = v
        out[nombre] = a
    return out


def cargar_10km(con, D: dict) -> dict:
    """Copia de D con los pares padre e hijo a menos de 10 km (el cargador del placebo llega a 5 km)."""
    sql = (placebo.SQL_PARES.replace("< 0.05", "< 0.1").replace("< 0.07", "< 0.13").replace(") < 5\n", ") < 10\n"))
    assert "< 10\n" in sql and "< 0.13" in sql
    ids = [r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()]
    pos_padre = {int(v): i for i, v in enumerate(ids)}
    pos_hijo = {int(v): i for i, v in enumerate(D["hijo_id"])}
    pares = con.execute(sql).fetchall()
    out = dict(D)
    out["par_hijo"] = np.array([pos_hijo[p[0]] for p in pares], dtype=np.int64)
    out["par_padre"] = np.array([pos_padre[p[1]] for p in pares], dtype=np.int64)
    out["par_km"] = np.array([p[2] for p in pares], dtype=float)
    out["par_rumbo"] = np.array([p[3] for p in pares], dtype=float)
    out["par_real_ok"] = out["primer"][out["par_padre"]] <= out["hijo_mes"][out["par_hijo"]] - placebo.EDAD_MIN
    return out


# ------------------------------------------------------------------ paneles por mes k

def _indice(arr: np.ndarray, m: dict, k: int, relativo: bool) -> np.ndarray:
    """Valor del panel en el mes k sobre (o menos) su media de la base limpia, por evento."""
    b = placebo._media({"tasa": arr}, m["padre"], m["mes"], *BASE_LIMPIA)
    v = arr[m["padre"], m["mes"] + k + PAD]
    if not relativo:
        return v - b
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, v / b, np.nan)


def _semilla(k: int) -> int:
    """La semilla que usa la pretendencia del placebo para el mismo k: asi la misma brecha tiene el mismo IC en las dos paginas."""
    return placebo.SEMILLA_PLACEBO + 100 + (k - placebo.KS_PRE[0])


def tabla_paneles(D: dict, ks=KS, reps: int = REPS_BOOT) -> list[tuple]:
    """Filas (panel, k, n_near, n_ctrl, mediana cercano, mediana control, brecha, ic_bajo, ic_alto) de los cuatro paneles.

    Son medianas: sirven para describir cada panel, no para partir la brecha (las medianas no se suman).
    """
    m = placebo.marco(D, D["hijo_mes"], ks=ks, base=BASE_LIMPIA)
    ref = placebo.marco(D, D["hijo_mes"], ks=ks, base=BASE_ORIGINAL)
    filas = []

    def fila(nombre, k, vals, mm):
        r = placebo.brecha_ic(vals, mm["banda"], mm["clave"], reps, _semilla(k))
        filas.append((nombre, int(k), r["n_near"], r["n_ctrl"], r["near"], r["ctrl"], r["brecha"], r["ic_bajo"], r["ic_alto"]))

    for k in ks:
        fila("petroleo", k, m["idx"][k], m)
        fila("dias", k, _indice(D["tef"], m, k, True), m)
        fila("tasa_por_dia", k, _indice(D["tasa_ef"], m, k, True), m)
        fila("corte_agua", k, _indice(D["corte"], m, k, False), m)
        fila(PANEL_REF, k, ref["idx"][k], ref)
    return filas


# ------------------------------------------------------------------ descomposicion aditiva (media de logaritmos)

def _logs(D: dict, m: dict, k: int, con_cerrados: bool) -> tuple[np.ndarray, np.ndarray]:
    """(log del indice de dias, log del indice de caudal por dia efectivo) por evento; nan donde el evento no entra.

    Entran los eventos con volumen, dias y bases positivas presentes en el mes k. Con `con_cerrados`, un mes sin dias efectivos
    entra con los dias acotados a DIAS_PISO y el caudal por dia sin cambio (no existe); sin eso, queda fuera. Un mes con dias
    positivos y petroleo cero (caudal por dia cero, logaritmo no definido) queda fuera en las dos variantes.
    """
    col = m["mes"] + k + PAD
    b_t = placebo._media({"tasa": D["tef"]}, m["padre"], m["mes"], *BASE_LIMPIA)
    b_r = placebo._media({"tasa": D["tasa_ef"]}, m["padre"], m["mes"], *BASE_LIMPIA)
    t, r, v = D["tef"][m["padre"], col], D["tasa_ef"][m["padre"], col], m["idx"][k]
    with np.errstate(divide="ignore", invalid="ignore"):
        cerrado = t == 0
        base_ok = (b_t > 0) & (b_r > 0) & ~np.isnan(t) & ~np.isnan(v)
        ld = np.log(np.maximum(t, DIAS_PISO) / b_t)
        lr = np.where(cerrado, 0.0, np.log(r / b_r))
        ok = base_ok & np.where(cerrado, con_cerrados, r > 0)
    return np.where(ok, ld, np.nan), np.where(ok, lr, np.nan)


def _brecha_logs_ic(ld: np.ndarray, lr: np.ndarray, banda: np.ndarray, clave: np.ndarray, reps: int, semilla: int) -> dict:
    """Brecha cercano menos control de las medias de ld, lr y su suma (el log del volumen), con IC por bootstrap de pads hijo."""
    ok = ~np.isnan(ld) & ~np.isnan(lr) & (banda != 1)
    ld, lr, bd, cl = ld[ok], lr[ok], banda[ok], clave[ok]
    lt = ld + lr
    nan3 = (float("nan"),) * 3

    def gaps(i):
        n, c = bd[i] == 0, bd[i] == 2
        if not n.any() or not c.any():
            return nan3
        return tuple(float(x[i][n].mean() - x[i][c].mean()) for x in (lt, ld, lr))

    todos = np.arange(len(bd))
    out = {"n_near": int((bd == 0).sum()), "n_ctrl": int((bd == 2).sum())}
    out["total"], out["dias"], out["tasa"] = (float(x) for x in gaps(todos))
    out["parte_dias"] = out["dias"] / out["total"] if out["total"] else float("nan")
    out["parte_tasa"] = out["tasa"] / out["total"] if out["total"] else float("nan")
    nan = float("nan")
    for nom in ("total", "dias", "tasa", "parte"):
        out[nom + "_ic"] = (nan, nan)
    if out["n_near"] < 5 or out["n_ctrl"] < 5:
        return out
    grupos = _clusters(cl)
    rng = np.random.default_rng(semilla)
    g = np.array([gaps(_remuestra(rng, grupos)) for _ in range(reps)])
    g = g[~np.isnan(g).any(axis=1)]
    if len(g):
        for j, nom in enumerate(("total", "dias", "tasa")):
            out[nom + "_ic"] = tuple(float(x) for x in np.percentile(g[:, j], [2.5, 97.5]))
        with np.errstate(divide="ignore", invalid="ignore"):
            parte = g[:, 1] / g[:, 0]
        parte = parte[np.isfinite(parte)]
        if len(parte):
            out["parte_ic"] = tuple(float(x) for x in np.percentile(parte, [2.5, 97.5]))
    return out


def tabla_aditiva(D: dict, ks=KS, reps: int = REPS_BOOT) -> list[tuple]:
    """Filas de COLS_ADIT: brecha del log del volumen partida en la de los dias y la del caudal por dia, por variante y k."""
    m = placebo.marco(D, D["hijo_mes"], ks=ks, base=BASE_LIMPIA)
    filas = []
    for var in VARIANTES:
        for k in ks:
            ld, lr = _logs(D, m, k, var == "con_cerrados")
            r = _brecha_logs_ic(ld, lr, m["banda"], m["clave"], reps, _semilla(k))
            filas.append((var, int(k), r["n_near"], r["n_ctrl"], r["total"], *r["total_ic"], r["dias"], *r["dias_ic"], r["tasa"],
                          *r["tasa_ic"], r["parte_dias"], *r["parte_ic"], r["parte_tasa"]))
    return filas


def tabla_cierres(D: dict, k: int = K_DIST) -> list[tuple]:
    """Fila de COLS_CIERRES: parte de eventos con indice de dias menor a UMBRAL_DIAS y parte cerrados todo el mes, cercanos y control."""
    m = placebo.marco(D, D["hijo_mes"], ks=(k,), base=BASE_LIMPIA)
    idx = _indice(D["tef"], m, k, True)
    cerrado = D["tef"][m["padre"], m["mes"] + k + PAD] == 0
    ok = ~np.isnan(idx)

    def parte(mask, banda):
        sel = ok & (m["banda"] == banda)
        return float(mask[sel].mean()) if sel.any() else float("nan")

    bajo = np.where(ok, idx < UMBRAL_DIAS, False)
    return [(int(k), int((ok & (m["banda"] == 0)).sum()), int((ok & (m["banda"] == 2)).sum()), parte(bajo, 0), parte(bajo, 2),
             parte(cerrado, 0), parte(cerrado, 2))]


# ------------------------------------------------------------------ distancia

def _marco_distancia(D10: dict, base=BASE_LIMPIA) -> dict:
    """Eventos con pares hasta 10 km; `limpio` marca los padres sin un hijo a menos de 1 km en los meses -6 a +3."""
    m = placebo.marco(D10, D10["hijo_mes"], ks=(K_DIST,), base=base)
    mes_par = D10["hijo_mes"][D10["par_hijo"]]
    cerca = np.flatnonzero(D10["par_km"] < KM_CERCA)
    k_cerca = np.sort(D10["par_padre"][cerca] * 100_000 + mes_par[cerca])
    clave = m["padre"] * 100_000 + m["mes"]
    n = np.searchsorted(k_cerca, clave + VENT_POST, side="right") - np.searchsorted(k_cerca, clave - VENT_PREVIA, side="left")
    m["limpio"] = n == 0
    return m


def _etiqueta(lo: float, hi: float) -> str:
    return f"{_g(lo, 1)} a {_g(hi, 1)}".replace(",0", "")


def tabla_distancia(D10: dict, reps: int = REPS_BOOT, n_min_anillo: int = N_MIN_ANILLO) -> list[tuple]:
    """Filas (banda, km_desde, km_hasta, control, n_banda, n_ctrl, mediana banda, mediana control, brecha, ic_bajo, ic_alto, base).

    Con la base limpia: cada banda contra el anillo lejano y el anillo contra 2 a 5 km. Las bandas de KM_CERCA km o mas llevan la
    misma restriccion que el control (sin un hijo a menos de 1 km en los meses -6 a +3). Ademas, todos los padres a menos de
    1 km (ETQ_TODOS) contra el anillo, con la base limpia y con la original, para la frase de la cabecera.
    """
    m = _marco_distancia(D10)
    v, km = m["idx"][K_DIST], m["km"]
    ok = ~np.isnan(v)

    def en(a, b):
        return ok & (km >= a) & (km < b)

    anillo = ANILLO if (en(*ANILLO) & m["limpio"]).sum() >= n_min_anillo else ANILLO_ALT
    ctrl = en(*anillo) & m["limpio"]
    filas = []

    def fila(lo, hi, band, control_mask, control_lbl, marco=m, valores=v, base=BASE_LIMPIA, semilla=placebo.SEMILLA_PLACEBO):
        banda = np.where(band, 0, np.where(control_mask, 2, 1))
        r = placebo.brecha_ic(valores, banda, marco["clave"], reps, semilla)
        filas.append((_etiqueta(lo, hi), lo, hi, control_lbl, r["n_near"], r["n_ctrl"], r["near"], r["ctrl"], r["brecha"],
                      r["ic_bajo"], r["ic_alto"], ETQ_BASE[base]))

    for lo, hi in BANDAS:
        if (lo, hi) == anillo:
            continue
        fila(lo, hi, en(lo, hi) & (m["limpio"] if lo >= KM_CERCA else True), ctrl, _etiqueta(*anillo) + " km")
    # gradiente entre zonas: el anillo de 5 a 10 km contra 2 a 5 km, ambos sin hijo a menos de 1 km
    if anillo == ANILLO:
        fila(*ANILLO, en(*ANILLO) & m["limpio"], en(*ANILLO_ALT) & m["limpio"], _etiqueta(*ANILLO_ALT) + " km")
        # todos los padres a menos de 1 km contra el anillo, con las dos bases (la original es la del resultado principal)
        for base in (BASE_LIMPIA, BASE_ORIGINAL):
            mb = m if base == BASE_LIMPIA else _marco_distancia(D10, base)
            vb, kb = mb["idx"][K_DIST], mb["km"]
            okb = ~np.isnan(vb)
            fila(0.0, KM_CERCA, okb & (kb < KM_CERCA), okb & (kb >= ANILLO[0]) & (kb < ANILLO[1]) & mb["limpio"],
                 _etiqueta(*ANILLO) + " km", mb, vb, base, _semilla(K_DIST))
    return filas


# ------------------------------------------------------------------ lectura y pagina

def lectura(total: tuple, dias: tuple, tasa: tuple, parte_ic: tuple | None = None) -> dict:
    """Cual de las lecturas sostiene la brecha del mes 1. Cada tupla es (brecha, ic_bajo, ic_alto) en logaritmos.

    Las brechas de los logaritmos se suman: total = dias + caudal por dia, asi que las partes suman 100%.
    'sin_brecha' si el IC del total incluye cero; 'dias' si la parte de los dias es al menos la mitad y la del caudal por dia
    menos de la mitad; 'tasa' en el caso contrario; 'mixta' en cualquier otro caso. Con `parte_ic` (IC de la parte de los dias),
    si ese IC incluye la mitad la lectura es 'mixta': dos partes que no se separan de la mitad no son un 'dias' ni un 'tasa'.
    """
    v, t, r = total[0], dias[0], tasa[0]
    out = {"parte_dias": float("nan"), "parte_tasa": float("nan"), "lectura": "sin_brecha"}
    if np.isnan(v) or v == 0 or total[1] <= 0 <= total[2]:
        return out
    out["parte_dias"], out["parte_tasa"] = t / v, r / v
    if out["parte_dias"] >= 0.5 > out["parte_tasa"]:
        out["lectura"] = "dias"
    elif out["parte_tasa"] >= 0.5 > out["parte_dias"]:
        out["lectura"] = "tasa"
    else:
        out["lectura"] = "mixta"
    if parte_ic is not None and parte_ic[0] <= 0.5 <= parte_ic[1]:
        out["lectura"] = "mixta"
    return out


def _lectura_fila(f: tuple) -> dict:
    """lectura() sobre una fila de COLS_ADIT."""
    return lectura((f[4], f[5], f[6]), (f[7], f[8], f[9]), (f[10], f[11], f[12]), (f[14], f[15]))


def lectura_aditiva(con_cerrados: tuple, sin_cerrados: tuple) -> dict:
    """Lectura del mes 1 con las dos variantes (filas de COLS_ADIT). Si las dos leen distinto, 'mixta'.

    La variante principal deja entrar los meses cerrados enteros con los dias acotados; la otra los deja fuera. Una lectura que
    depende de como se trata un mes sin dias no se declara: queda 'mixta' y la pagina da las dos partes.
    """
    prim, sens = _lectura_fila(con_cerrados), _lectura_fila(sin_cerrados)
    out = dict(prim)
    out["lectura_principal"], out["lectura_sin_cerrados"] = prim["lectura"], sens["lectura"]
    out["parte_dias_sin"], out["parte_tasa_sin"] = sens["parte_dias"], sens["parte_tasa"]
    if prim["lectura"] != "sin_brecha" and sens["lectura"] not in ("sin_brecha", prim["lectura"]):
        out["lectura"] = "mixta"
    return out


def _excluye_cero(f: tuple) -> bool:
    return not (np.isnan(f[0]) or np.isnan(f[1]) or np.isnan(f[2])) and not (f[1] <= 0 <= f[2])


def _tabla_panel(filas: list[tuple], unidad: str) -> list[str]:
    L = [f"| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha ({unidad}) | IC 95% ({unidad}) |",
         "| ---: | ---: | ---: | ---: | --- |"]
    for _, k, nn, nc, _a, _b, g, lo, hi in filas:
        L.append(f"| {k} | {_g(nn)} | {_g(nc)} | {_pts(g)} | {_pts(lo)} a {_pts(hi)} |")
    return L


def _ic(a: float, b: float) -> str:
    return f"{_pts(a)} a {_pts(b)}"


def _tabla_aditiva(filas: list[tuple]) -> list[str]:
    L = ["| k | Eventos cercanos | Eventos control | Brecha del volumen (IC 95%) | Días efectivos (IC 95%) | Caudal por día (IC 95%) "
         "| Parte de los días (IC 95%) |", "| ---: | ---: | ---: | --- | --- | --- | --- |"]
    for f in filas:
        L.append(f"| {f[1]} | {_g(f[2])} | {_g(f[3])} | {_pts(f[4])} ({_ic(f[5], f[6])}) | {_pts(f[7])} ({_ic(f[8], f[9])}) | "
                 f"{_pts(f[10])} ({_ic(f[11], f[12])}) | {_g(100 * f[13])}% ({_g(100 * f[14])}% a {_g(100 * f[15])}%) |")
    return L


def _anillo_vs_2a5(d: tuple) -> bool:
    return d[0] == _etiqueta(*ANILLO) and d[3].startswith(_etiqueta(*ANILLO_ALT))


def _bandas(dist: list[tuple]) -> list[tuple]:
    """Las filas de banda contra el anillo con la base limpia (sin la del anillo contra 2 a 5 km ni la de todos los cercanos)."""
    return [d for d in dist if d[11] == ETQ_BASE[BASE_LIMPIA] and d[0] != ETQ_TODOS and not _anillo_vs_2a5(d)]


def _conclusion(filas: list[tuple], adit: list[tuple], cierres: tuple, dist: list[tuple]) -> list[str]:
    por = {(f[0], f[1]): f for f in filas}
    pa = {(f[0], f[1]): f for f in adit}

    def g(p, k):
        f = por[(p, k)]
        return (f[6], f[7], f[8])

    ref = por[(PANEL_REF, 1)]
    v, c = g("petroleo", 1), g("corte_agua", 1)
    a1, a2 = pa[("con_cerrados", 1)], pa[("sin_cerrados", 1)]
    lec = lectura_aditiva(a1, a2)
    P, Q = _g(100 * lec["parte_dias"]), _g(100 * lec["parte_tasa"])
    L = [f"- Resultado principal reproducido: con la base de los meses -3 a -1 la brecha del petróleo al mes 1 es {_pts(ref[6])} puntos "
         f"(IC {_pts(ref[7])} a {_pts(ref[8])}). Con la base limpia de -6 a -4 de estos paneles es {_pts(v[0])} puntos "
         f"(IC {_pts(v[1])} a {_pts(v[2])}); la diferencia es en parte la brecha previa que la base de -3 a -1 absorbe."]
    cab = next((d for d in dist if d[0] == ETQ_TODOS and d[11] == ETQ_BASE[BASE_ORIGINAL]), None)
    if cab is not None:
        L.append(f"- Contra el anillo de {_etiqueta(*ANILLO)} km la brecha del mes 1 es {_pts(cab[8])} puntos, "
                 f"{'más' if cab[8] < ref[6] else 'menos'} negativa que los {_pts(ref[6])} contra {_etiqueta(*ANILLO_ALT)} km.")
    L.append(f"- Mes 1, descomposición aditiva (media de los logaritmos, puntos logarítmicos, {_g(a1[2])} eventos cercanos y {_g(a1[3])} "
             f"controles con días y caudal por día): la brecha del volumen es {_pts(a1[4])} (IC {_ic(a1[5], a1[6])}), la de los "
             f"días efectivos {_pts(a1[7])} (IC {_ic(a1[8], a1[9])}) y la del caudal por día efectivo {_pts(a1[10])} "
             f"(IC {_ic(a1[11], a1[12])}). La parte de los días es {P}% (IC {_g(100 * a1[14])}% a {_g(100 * a1[15])}%) y la "
             f"del caudal por día es {Q}%. Las medianas no se suman; la parte de cada panel sale de la media de los logaritmos sobre los "
             f"mismos eventos.")
    L.append(f"- Misma descomposición sin los meses cerrados enteros ({_g(a2[2])} eventos cercanos y {_g(a2[3])} controles): la parte de "
             f"los días es {_g(100 * a2[13])}% y la del caudal por día {_g(100 * a2[16])}%. Los meses cerrados enteros no tienen "
             "logaritmo de los días: la variante principal los acota a un día de 30 y los deja sin cambio en el caudal por día; esta "
             "variante los deja fuera, y por eso resta peso a los días.")
    L.append(f"- Cierres al mes 1: el {_g(100 * cierres[3])}% de los padres cercanos tiene un índice de días menor a {_g(UMBRAL_DIAS, 1)} "
             f"contra el {_g(100 * cierres[4])}% de los controles, y el {_g(100 * cierres[5])}% de los cercanos estuvo cerrado todo "
             f"el mes contra el {_g(100 * cierres[6])}% de los controles.")
    dos = f"días {P}% y caudal por día {Q}%"
    txt = {"dias": f"la caída se parece a cierres o días perdidos: la parte de los días es la que lleva al menos la mitad de la brecha "
                   f"del volumen en logaritmos ({dos})",
           "tasa": f"la caída se parece a un golpe de fractura: la parte del caudal por día efectivo es la que lleva al menos la mitad "
                   f"de la brecha del volumen en logaritmos ({dos})",
           "mixta": (f"mixta: las dos variantes no coinciden (con los cerrados enteros: {NOM_LECTURA[lec['lectura_principal']]}, con "
                     f"{dos}; sin ellos: {NOM_LECTURA[lec['lectura_sin_cerrados']]}, con días {_g(100 * lec['parte_dias_sin'])}% y caudal "
                     f"por día {_g(100 * lec['parte_tasa_sin'])}%)" if lec["lectura_principal"] != "mixta" else
                     f"mixta: ninguna de las dos partes lleva sola la mayor parte de la brecha del volumen ({dos})"),
           "sin_brecha": "el IC de la brecha del volumen incluye cero con esta base, así que no hay una caída que descomponer"}[
        lec["lectura"]]
    L.append(f"- Lectura que sostienen los datos: {txt}.")
    marca = lambda ok: "sí" if ok else "no"  # noqa: E731
    L.append(f"- Las lecturas al mes 1. Cierres o días perdidos: {marca(lec['lectura'] == 'dias')}. Golpe de fractura (menos "
             f"caudal por día): {marca(lec['lectura'] == 'tasa')}. Mezcla de ambos: {marca(lec['lectura'] == 'mixta')}. La "
             f"diferencia entre zonas se mira en el anillo lejano más abajo.")
    sub = [k for k in (-3, -2, -1) if _excluye_cero(g("dias", k)) or _excluye_cero(g("tasa_por_dia", k))]
    L.append("- Pretendencia por panel, en medianas (k = -3 a -1, base de -6 a -4): "
             + ", ".join(f"{NOMBRES[p]} {_pts(g(p, -1)[0])} puntos en k = -1 (IC {_pts(g(p, -1)[1])} a {_pts(g(p, -1)[2])})" for p in PANELES)
             + (f"; en los paneles de días o caudal por día el IC excluye cero en k = {', '.join(str(k) for k in sub)}, así que parte de "
                f"la diferencia ya estaba antes de la fractura." if sub else "; los intervalos de días y caudal por día incluyen cero "
                "antes de la fractura."))
    picos = {p: min((por[(p, k)] for k in range(0, 13)), key=lambda f: np.inf if np.isnan(f[6]) else f[6]) for p in ("petroleo", "dias",
                                                                                                                   "tasa_por_dia")}
    L.append("- Mayor brecha entre k = 0 y 12, en medianas: " + "; ".join(f"{NOMBRES[p]} {_pts(f[6])} puntos en k = {f[1]}" for p, f in picos.items()) + ".")
    ca = c[0]
    L.append(f"- Corte de agua al mes 1: {_pts(ca)} puntos de corte (IC {_pts(c[1])} a {_pts(c[2])}); "
             + ("el IC excluye cero." if _excluye_cero(c) else "el IC incluye cero."))
    ring = next((d for d in dist if _anillo_vs_2a5(d)), None)
    if ring is not None:
        mas = "más" if ring[8] > 0 else "menos"
        L.append(f"- Anillo lejano ({_etiqueta(*ANILLO)} km contra {_etiqueta(*ANILLO_ALT)} km, al mes 1): {_pts(ring[8])} puntos "
                 f"(IC {_pts(ring[9])} a {_pts(ring[10])}, {_g(ring[4])} eventos contra {_g(ring[5])}). "
                 + (f"El IC excluye cero: los padres de {_etiqueta(*ANILLO)} km rinden {_pts(abs(ring[8]))} puntos {mas} que los de "
                    f"{_etiqueta(*ANILLO_ALT)} km. El control de {_etiqueta(*ANILLO_ALT)} km no es un cero limpio; con estos datos no se "
                    f"separa si es interferencia que llega más allá de {_g(ANILLO[0])} km o una diferencia entre zonas con y sin "
                    "actividad cercana (edad, desarrollo, declinación)." if _excluye_cero(ring[8:11]) else
                    "El IC incluye cero: no se ve un gradiente entre zonas de 2 a 5 km y 5 a 10 km, aunque un efecto parejo hasta "
                    "10 km no se podría ver así."))
    bandas = _bandas(dist)
    sig = [d[0] for d in bandas if _excluye_cero(d[8:11])]
    L.append("- Gradiente por distancia (contra el anillo lejano "
             + (f"de {bandas[0][3]}" if bandas else "") + "), no un alcance: " + ", ".join(f"{d[0]} km: {_pts(d[8])}" for d in bandas)
             + f" puntos. {_g(len(sig))} de {_g(len(bandas))} bandas tienen un IC que excluye cero"
             + (f" ({', '.join(sig)} km)" if sig else "")
             + "; la brecha cambia de forma gradual con la distancia y no corta en un punto, y como el control de "
             f"{_etiqueta(*ANILLO_ALT)} km tampoco es un cero limpio, esto no fija hasta dónde llega la interferencia.")
    return L


def pagina_descomposicion(con) -> str:
    filas = con.execute("select * from mart_descomposicion_k order by panel, k").fetchall()
    adit = con.execute("select * from mart_descomposicion_aditiva order by variante, k").fetchall()
    cierres = con.execute("select * from mart_descomposicion_cierres").fetchone()
    dist = con.execute("select * from mart_descomposicion_distancia order by base desc, km_desde, km_hasta, control").fetchall()
    ref1 = next(f for f in filas if f[0] == PANEL_REF and f[1] == 1)
    L = ["# Descomposición de la brecha de interferencia", "",
         "Página generada por `pipeline/descomposicion.py`. Responde lo primero que pregunta un ingeniero de reservorio sobre el "
         "resultado de interferencia: si la brecha es un golpe de fractura (baja el caudal por día producido) o son cierres (bajan "
         "los días producidos), y cómo cambia con la distancia.", "",
         "## Qué se mide", "",
         "Los eventos son los del estudio de eventos de interferencia (mismos padres elegibles a menos de 1 km del hijo y controles de "
         "2 a 5 km, mismo hijo más cercano, misma edad mínima y misma base positiva). La base de cada padre son los meses -6 a -4 "
         "(la base limpia de la página de falsación), para que la pretendencia se vea y no quede absorbida. k = 0 es el mes de la "
         f"fractura del hijo. Los IC 95% son bootstrap por pads hijo ({_g(REPS_BOOT)} repeticiones, con la semilla de la página de "
         "falsación para el mismo k, así que la misma brecha tiene el mismo intervalo en las dos páginas).", "",
         "- Petróleo: caudal por día calendario del mes sobre su base (el índice principal).",
         "- Días efectivos: días producidos del mes sobre días del mes, sobre su base.",
         "- Petróleo por día efectivo: volumen del mes sobre los días producidos, sobre su base. Los meses sin días producidos no "
         "tienen caudal por día y quedan fuera de ese panel (un mes cerrado entero baja los días y el volumen, no este panel).",
         "- Corte de agua: agua sobre agua más petróleo; la brecha es el cambio del corte respecto de su base, en puntos de corte.", ""]
    L += ["## Descomposición aditiva", "",
          "Las medianas no se suman: la mediana del volumen no es la de los días más la del caudal por día, y con los días agrupados "
          "en 1 (muchos padres producen todos los días) la mediana de los días casi no se mueve aunque una parte de los padres pierda "
          "días. Por eso la partición de la brecha se hace con medias de logaritmos sobre los mismos eventos: el volumen es días por "
          "caudal por día efectivo, así que el logaritmo de su índice es la suma de los otros dos (se usa esa suma como índice de "
          "volumen de esta sección, que difiere del índice principal porque cada base es la media de su propia serie). La brecha es la "
          "media de los cercanos menos la de los controles, en puntos logarítmicos (100 veces la diferencia de logaritmos naturales), "
          "y la parte de cada panel es su brecha sobre la del volumen.", "",
          "Los ceros se tratan así. Un mes con cero días efectivos (cerrado entero) no tiene logaritmo de los días ni caudal por día: "
          f"en la variante con cerrados sus días se acotan a un día de 30 ({_g(DIAS_PISO, 3)} del mes) y su caudal por día queda sin "
          "cambio; en la variante sin cerrados esos eventos se dejan fuera. Un mes con días positivos y petróleo cero queda fuera en "
          "las dos. Los eventos sin dato de volumen, días o base positiva en el mes k también quedan fuera. La variante con cerrados "
          "depende del piso de un día (un piso menor da más peso a los días), así que se muestran las dos.", ""]
    for var, titulo in (("con_cerrados", "Con los meses cerrados enteros (días acotados a un día de 30)"),
                        ("sin_cerrados", "Sin los meses cerrados enteros")):
        L += [f"### {titulo}", ""] + _tabla_aditiva([f for f in adit if f[0] == var]) + [""]
    L += ["## Cierres al mes 1", "",
          "Parte de los eventos con el índice de días por debajo de "
          f"{_g(UMBRAL_DIAS, 1)} (más de 10% de los días perdidos respecto de su base) y parte cerrados todo el mes, cercanos "
          "contra control (mismos eventos que el panel de días).", "",
          "| Grupo | Eventos | Índice de días menor a "
          f"{_g(UMBRAL_DIAS, 1)} | Cerrados todo el mes |", "| --- | ---: | ---: | ---: |",
          f"| Cercanos | {_g(cierres[1])} | {_g(100 * cierres[3], 1)}% | {_g(100 * cierres[5], 1)}% |",
          f"| Controles | {_g(cierres[2])} | {_g(100 * cierres[4], 1)}% | {_g(100 * cierres[6], 1)}% |", ""]
    L += ["## Paneles por mes (medianas, descriptivos)", "",
          "Brecha de las medianas por panel. Describen cada panel por separado y no se usan para partir la brecha.", ""]
    for i, p in enumerate(PANELES, start=1):
        L += [f"### Panel {i}: {TITULOS[p]}", ""]
        L += _tabla_panel([f for f in filas if f[0] == p], "puntos")
        L.append("")
    L += [f"De referencia, con la base del resultado principal (meses -3 a -1) la brecha del petróleo al mes 1 es {_pts(ref1[6])} "
          f"puntos (IC {_pts(ref1[7])} a {_pts(ref1[8])}) con {_g(ref1[2])} eventos cercanos y {_g(ref1[3])} controles.", ""]
    n_28 = next((d[4] for d in dist if d[0] == _etiqueta(*ANILLO_ALT) and d[11] == ETQ_BASE[BASE_LIMPIA]), None)
    n_ring = next((d[5] for d in dist if _anillo_vs_2a5(d)), None)
    L += ["## Gradiente por distancia", "",
          "Brecha del petróleo al mes 1 por banda de distancia al hijo más cercano, contra un anillo lejano: padres cuyo hijo más "
          "cercano está a 5 a 10 km, sin otro hijo a menos de 1 km en los meses -6 a +3 del evento. Las bandas de 1 km o más llevan "
          "la misma restricción que el anillo. La fila de 5 a 10 contra 2 a 5 km compara el anillo con 2 a 5 km (mismas "
          "restricciones): una brecha ahí es un gradiente entre zonas, y no se separa de la interferencia que llegue más allá de "
          f"{_g(ANILLO[0])} km. La fila de 0 a 1 km reúne a todos los padres a menos de 1 km contra el anillo, con la base limpia "
          "y con la base original (meses -3 a -1, la del resultado principal).", "",
          "| Banda (km) | Control (km) | Base (meses) | Eventos banda | Eventos control | Brecha (puntos) | IC 95% (puntos) |",
          "| --- | --- | --- | ---: | ---: | ---: | --- |"]
    for d in dist:
        L.append(f"| {d[0]} | {d[3]} | {d[11]} | {_g(d[4])} | {_g(d[5])} | {_pts(d[8])} | {_pts(d[9])} a {_pts(d[10])} |")
    cercanas = sum(d[4] for d in dist if d[2] <= 1.0 and d[0] != ETQ_TODOS and d[11] == ETQ_BASE[BASE_LIMPIA])
    n_k1 = next(f for f in filas if f[0] == "petroleo" and f[1] == 1)[2]
    L += ["", f"Las tres bandas de menos de 1 km suman {_g(cercanas)} eventos, los mismos {_g(n_k1)} cercanos del panel de petróleo en k = 1.", ""]
    if n_28 is not None and n_ring is not None:
        L += [f"La banda de 2 a 5 km ({_g(n_28)} eventos) y el control de 2 a 5 km de la fila del anillo ({_g(n_ring)} eventos) usan "
              "la misma regla: padres sin un hijo a menos de 1 km en los meses -6 a +3.", ""]
    L += ["## Qué se concluye", ""] + _conclusion(filas, adit, cierres, dist)
    L += ["", "## Límites", "",
          "- Con datos mensuales no se distingue un cierre de un golpe dentro del mes: un pozo que produce menos horas por día "
          "y uno cerrado unos días dan el mismo mes. La descomposición separa días de caudal por día, no el motivo del cambio.",
          "- Un cierre protector del operador y un golpe de la fractura se ven igual; el lenguaje de esta página es de brecha medida, "
          "no de causa.",
          "- La parte de los días depende de cómo se tratan los meses cerrados enteros (sin logaritmo): por eso se muestran la variante "
          "con el piso de un día y la que los deja fuera.",
          "- Un efecto parejo hasta 10 km no se ve: solo se ve un gradiente entre 2 a 5 km y 5 a 10 km.",
          f"- Los intervalos son bootstrap por pads hijo y no se ajustan por comparaciones múltiples; la página tiene "
          f"{_g(len(filas) + len(adit) + len(dist))} intervalos, así que alguno puede quedar fuera de cero por azar.",
          ""]
    return "\n".join(L)


# ------------------------------------------------------------------ entrada

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    D = cargar_ext(con, placebo.cargar(con))
    filas = tabla_paneles(D)
    dist = tabla_distancia(cargar_10km(con, D))
    _escribir(con, "mart_descomposicion_k", COLS_K, filas)
    _escribir(con, "mart_descomposicion_aditiva", COLS_ADIT, tabla_aditiva(D))
    _escribir(con, "mart_descomposicion_cierres", COLS_CIERRES, tabla_cierres(D))
    _escribir(con, "mart_descomposicion_distancia", COLS_DIST, dist)
    for r in con.execute("select * from mart_descomposicion_k where k in (-1, 1, 3) order by panel, k").fetchall():
        print("[descomposicion] k   ", tuple(round(x, 3) if isinstance(x, float) else x for x in r))
    for r in con.execute("select * from mart_descomposicion_aditiva where k in (-1, 1, 3) order by variante, k").fetchall():
        print("[descomposicion] adit", tuple(round(x, 3) if isinstance(x, float) else x for x in r))
    print("[descomposicion] cierres", con.execute("select * from mart_descomposicion_cierres").fetchone())
    for r in con.execute("select * from mart_descomposicion_distancia order by base desc, km_desde, km_hasta, control").fetchall():
        print("[descomposicion] dist", tuple(round(x, 3) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
