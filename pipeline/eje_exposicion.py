"""Eje de exposicion: la geometria de desarrollo (hacia donde estan los padres respecto del hijo) contra el eje de merma.

Se corre despues de pipeline.costo:  uv run python -m pipeline.eje_exposicion

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ninguna cifra de este modulo; no se cambia despues de ver resultados).
Fuente: docs/proceso/investigacion-fase3.md, secciones 3.4 (piezas 1 y 2) y 4 (regla de parada del eje).

Pregunta: con coordenadas de superficie, el rumbo hijo a padre mezcla la direccion en que se propagan las fracturas con la forma en
que se disponen los pads y las ramas. Si los padres cercanos estan, por geometria, mas en una direccion (por ejemplo a lo largo de una
fila de pads), una merma mayor en esa direccion puede ser exposicion y no mecanismo. Se mide el eje de exposicion y se compara con
el eje de merma; luego se reestima el eje de merma dandole a cada direccion el mismo peso.

Muestra: los eventos de pipeline.costo.EVENTOS_SQL con distancia de 0,3 a menos de 1 km (la del eje principal; todos, tengan o no
caida), Cuenca y las areas con al menos MIN_N_AREA = 60 eventos (las de mart_anisotropia_area). Rumbo axial en [0, 180).

Pieza 1 (eje de exposicion):
  a. Eje axial medio de los rumbos: theta_e = 0,5 atan2(suma de sin 2r, suma de cos 2r) en [0, 180), con la concentracion
     Rbar = |suma de exp(2 i r)| / n. IC 95% de percentiles por bootstrap de pads hijo (REPS_EJE = 400, semilla fija), como el
     ancho en grados del arco axial de las desviaciones.
  b. Eje de las filas: primer eje principal (componente principal 1) de las posiciones proyectadas en km (pipeline.bloques.proyectar)
     de los pads hijo con al menos un evento de la muestra, dentro de cada area y para la cuenca (cuenca con las posiciones centradas
     por area). Convertido a rumbo axial en la misma convencion (0 es norte, 90 es este). IC 95% por bootstrap de pads. Se informa
     tambien la razon entre los autovalores (si es cercana a 1, el eje de filas no esta definido).
  c. Comparacion: el eje de merma de cada area y de la cuenca (mart_anisotropia_area: eje, IC) contra theta_e y contra el eje de
     filas. Distancia axial en grados, y si el eje de merma cae dentro del IC del eje de exposicion (a) y del de filas (b).

Pieza 2 (reponderacion):
  * Peso de cada evento = 1 / (numero de eventos de su area en su bin de rumbo), con bins de 15 grados sobre [0, 180) (12 bins), y los
    pesos normalizados para que sumen n en cada area (todas las direcciones pesan igual dentro de cada area). Un bin sin eventos no
    entra.
  * Reestimar el eje de merma con minimos cuadrados ponderados: el mismo ajuste que pipeline.costo.ajustar_eje con efectos fijos de
    area (dummies de area, no centrado), controles km y log de la edad, caida = control menos indice acotados a [0, 2]. IC 95% de
    percentiles por bootstrap de pads hijo (reponderando en cada remuestra con la misma regla) y p de permutacion de pads hijo
    completos (REPS_PERM = 499). Para la cuenca y para Loma Campana.
  * Eje definido si p de permutacion < 0,10 y el IC mide menos de 90 grados (la regla del proyecto).

Pieza 3 (modelo de ramas): NO se hace. Necesita azimut de rama y coordenadas de fondo, que no estan en el warehouse; no se verifico
si el padron de pozos de la Secretaria de Energia o el organismo provincial los publican. La pagina lo dice.

Veredicto (se publican todos los resultados, favorables o no):
  * "geometria explica el eje" (DISPARA la tercera pata de la regla de parada del eje) si ocurre CUALQUIERA de:
      (i) el eje de merma de Loma Campana cae dentro del IC del eje de exposicion (a) de Loma Campana Y el eje de merma de la cuenca
          cae dentro del IC del eje de exposicion (a) de la cuenca; o
      (ii) la reponderacion deja indefinido el eje de la cuenca.
  * Si ninguna se cumple: "no lo explica la exposicion que se midio", y el eje de merma se sigue llamando no firme por las otras
    razones. La pieza 3 queda sin hacer, asi que esto no descarta la geometria de ramas.

Que NO prueba:
  * El eje de exposicion con pads de superficie es un proxy: no es la direccion de las ramas.
  * Un eje de merma fuera del IC de exposicion no lo separa del SHmax ni demuestra un mecanismo.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import bloques, costo
from pipeline.costo import (KM_MIN_EJE, MIN_N_AREA, REPS_EJE, REPS_PERM, SEMILLA, _arr, _clusters, _controles_eje,
                            _dif_axial, _escribir, _filas, _perm_bloques, _remuestra)
from pipeline.eje_controles import dist_axial, en_ic, es_definido
from pipeline.ingest import DATA
from pipeline.placebo import _g, _pts

SEMILLA_EXP = SEMILLA + 800        # pieza 1a, mas el indice del area
SEMILLA_FILAS = SEMILLA + 810      # pieza 1b, mas el indice del area
SEMILLA_REPOND = SEMILLA + 820     # pieza 2 (cuenca + 0, Loma Campana + 1)
N_BINS = 12
ANCHO_BIN = 180.0 / N_BINS
CUENCA = "Cuenca"
AREA_FOCO = "LOMA CAMPANA"
TEXTO_EXPLICA = "geometria explica el eje"
TEXTO_NO_EXPLICA = "no lo explica la exposicion que se midio"
COND_I = "(i) merma de LC y Cuenca en IC de exposicion"
COND_II = "(ii) reponderacion deja indefinido el eje de Cuenca"
COND_VEREDICTO = "veredicto"

COLS_EXP = [("area", "varchar"), ("n", "integer"), ("pads", "integer"), ("eje_merma", "double"),
            ("merma_ic_bajo", "double"), ("merma_ic_alto", "double"), ("exp_eje", "double"), ("exp_ic_bajo", "double"),
            ("exp_ic_alto", "double"), ("exp_rbar", "double"), ("filas_eje", "double"), ("filas_ic_bajo", "double"),
            ("filas_ic_alto", "double"), ("filas_razon_autovalores", "double"), ("dist_merma_exp", "double"),
            ("merma_en_ic_exp", "boolean"), ("dist_merma_filas", "double"), ("merma_en_ic_filas", "boolean")]
COLS_REPOND = [("area", "varchar"), ("n", "integer"), ("eje", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
               ("ancho_ic", "double"), ("amplitud", "double"), ("p_perm", "double"), ("definido", "boolean")]
COLS_VEREDICTO = [("condicion", "varchar"), ("cumple", "boolean"), ("detalle", "varchar"),
                  ("dispara_regla_parada", "boolean")]


def eje_axial_medio(rumbo: np.ndarray) -> tuple[float, float]:
    """Eje axial medio de rumbos en [0, 180) y concentracion Rbar en [0, 1]."""
    r = np.radians(np.asarray(rumbo, dtype=float))
    c, s = float(np.cos(2 * r).sum()), float(np.sin(2 * r).sum())
    theta = float(np.degrees(np.arctan2(s, c)) / 2 % 180)
    return theta, float(np.hypot(s, c) / len(r))


def _ic_desviaciones(theta: float, boots) -> tuple[float, float, float]:
    """IC 95% con la convencion de costo.eje_con_intervalo: theta mas los percentiles 2,5 y 97,5 de las
    desviaciones axiales de los remuestreos. Devuelve (ic_bajo, ic_alto, ancho)."""
    lo, hi = np.percentile(_dif_axial(np.asarray(list(boots), dtype=float), theta), [2.5, 97.5])
    return float((theta + lo) % 180), float((theta + hi) % 180), float(hi - lo)


def exposicion_area(rumbo, clave, reps: int = REPS_EJE, semilla: int = SEMILLA_EXP) -> dict:
    """Pieza 1a: eje axial medio de los rumbos con Rbar e IC 95% por bootstrap de pads hijo."""
    rumbo = np.asarray(rumbo, dtype=float)
    theta, rbar = eje_axial_medio(rumbo)
    rng = np.random.default_rng(semilla)
    cl = _clusters(np.asarray(clave))
    boots = [eje_axial_medio(rumbo[_remuestra(rng, cl)])[0] for _ in range(reps)]
    lo, hi, ancho = _ic_desviaciones(theta, boots)
    return {"eje": theta, "ic_bajo": lo, "ic_alto": hi, "ancho_ic": ancho, "rbar": rbar}


def eje_filas(x, y) -> tuple[float, float]:
    """Primer eje principal de posiciones (x este, y norte, en km) como rumbo axial en [0, 180), con la razon
    entre los autovalores (cercana a 1 si el eje de filas no esta definido)."""
    xc = np.asarray(x, dtype=float) - np.mean(x)
    yc = np.asarray(y, dtype=float) - np.mean(y)
    vals, vecs = np.linalg.eigh(np.array([[xc @ xc, xc @ yc], [xc @ yc, yc @ yc]]))
    vx, vy = vecs[:, 1]
    rumbo = float(np.degrees(np.arctan2(vx, vy)) % 180)
    return rumbo, float(vals[1] / vals[0]) if vals[0] > 0 else float("inf")


def _centrar_por_grupo(x: np.ndarray, y: np.ndarray, grupo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Posiciones menos la media de su grupo (para la cuenca: centradas por area)."""
    xc, yc = x.copy(), y.copy()
    for g in np.unique(grupo):
        m = grupo == g
        xc[m] -= xc[m].mean()
        yc[m] -= yc[m].mean()
    return xc, yc


def filas_area(x, y, grupo=None, reps: int = REPS_EJE, semilla: int = SEMILLA_FILAS) -> dict:
    """Pieza 1b: eje de filas por PCA de las posiciones de los pads, IC 95% por bootstrap de pads. Con `grupo`
    (codigo de area por pad) las posiciones se centran por area antes del PCA, tambien en cada remuestra."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    g = None if grupo is None else np.asarray(grupo)
    xc, yc = (x, y) if g is None else _centrar_por_grupo(x, y, g)
    theta, razon = eje_filas(xc, yc)
    rng = np.random.default_rng(semilla)
    n = len(x)
    boots, intentos = [], 0
    while len(boots) < reps and intentos < reps * 10 + 100:
        intentos += 1
        i = rng.integers(0, n, n)
        if len(np.unique(np.column_stack([xc[i], yc[i]]), axis=0)) < 2:
            continue
        xi, yi = (xc[i], yc[i]) if g is None else _centrar_por_grupo(xc[i], yc[i], g[i])
        boots.append(eje_filas(xi, yi)[0])
    lo, hi, ancho = _ic_desviaciones(theta, boots)
    return {"eje": theta, "ic_bajo": lo, "ic_alto": hi, "ancho_ic": ancho, "razon": razon}


def muestra(con) -> dict:
    """Eventos de la muestra del eje (0,3 a menos de 1 km) con area, rumbo, pad hijo, caida y controles."""
    filas = _filas(con, costo.EVENTOS_SQL)
    km = _arr(filas, "km_min")
    f = [x for x, s in zip(filas, (km >= KM_MIN_EJE) & (km < 1)) if s]
    area = np.array([x["area"] for x in f])
    caida = np.clip(_arr(f, "indice_control"), 0, 2) - np.clip(_arr(f, "indice"), 0, 2)
    return {"area": area, "rumbo": _arr(f, "rumbo_eje"), "clave": np.array([str(x["pad_hijo"]) for x in f]),
            "caida": caida, "ctrl": _controles_eje({"km": _arr(f, "km_min"), "edad": _arr(f, "edad_meses")}),
            "n": len(f)}


def posiciones_pads(con) -> dict:
    """Latitud y longitud medias de cada pad_id (posicion del pad)."""
    q = con.execute("select pad_id, avg(lat), avg(lon) from int_pozo_ubicacion group by pad_id").fetchall()
    return {str(p): (float(la), float(lo)) for p, la, lo in q}


def area_por_pad(area: np.ndarray, clave: np.ndarray) -> dict:
    """Area mayoritaria de los eventos de cada pad hijo (empates por orden de nombre, deterministico)."""
    out = {}
    for p in np.unique(clave):
        nombres, cuentas = np.unique(area[clave == p], return_counts=True)
        out[p] = nombres[cuentas == cuentas.max()][0]
    return out


def pesos_densidad_inversa(rumbo, grupo) -> np.ndarray:
    """Peso 1/(eventos del area en el bin de rumbo del evento), con 12 bins de 15 grados sobre [0, 180),
    normalizado para que los pesos sumen n en cada area. Un bin sin eventos no entra."""
    rumbo = np.asarray(rumbo, dtype=float) % 180
    grupo = np.asarray(grupo)
    w = np.empty(len(rumbo))
    for g in np.unique(grupo):
        m = grupo == g
        b = np.minimum((rumbo[m] // ANCHO_BIN).astype(int), N_BINS - 1)
        cuenta = np.bincount(b, minlength=N_BINS)
        wb = 1.0 / cuenta[b]
        w[m] = wb * m.sum() / wb.sum()
    return w


def ajustar_eje_ponderado(caida, ctrl, rumbo, grupo, pesos) -> tuple[float, float, np.ndarray]:
    """Como costo.ajustar_eje con efectos fijos de area, pero con dummies de area explicitas (no centrado) y
    minimos cuadrados ponderados. `grupo` son codigos de area de 0 a G menos 1. Devuelve theta, amplitud y beta."""
    r = np.radians(np.asarray(rumbo, dtype=float))
    ctrl = np.asarray(ctrl, dtype=float)
    base = (np.column_stack([ctrl, np.cos(2 * r), np.sin(2 * r)]) if np.size(ctrl)
            else np.column_stack([np.cos(2 * r), np.sin(2 * r)]))
    grupo = np.asarray(grupo)
    dum = np.zeros((len(grupo), int(grupo.max()) + 1))
    dum[np.arange(len(grupo)), grupo] = 1.0
    s = np.sqrt(np.asarray(pesos, dtype=float))
    beta = np.linalg.lstsq(s[:, None] * np.column_stack([dum, base]), s * np.asarray(caida, dtype=float),
                           rcond=None)[0]
    a, b = beta[-2], beta[-1]
    return float(np.degrees(np.arctan2(b, a)) / 2 % 180), float(np.hypot(a, b)), beta


def eje_reponderado_intervalo(caida, ctrl, rumbo, clave, grupo, reps: int = REPS_EJE,
                             reps_perm: int = REPS_PERM, semilla: int = SEMILLA_REPOND) -> dict:
    """Pieza 2: eje por minimos cuadrados ponderados con dummies de area, IC 95% por bootstrap de pads
    (reponderando en cada remuestra con la misma regla) y p por permutacion de pads hijo completos."""
    caida = np.asarray(caida, float)
    ctrl = np.asarray(ctrl, float)
    rumbo = np.asarray(rumbo, float)
    grupo = np.asarray(grupo)
    w = pesos_densidad_inversa(rumbo, grupo)
    theta, amp, _b = ajustar_eje_ponderado(caida, ctrl, rumbo, grupo, w)
    rng = np.random.default_rng(semilla)
    cl = _clusters(np.asarray(clave))
    boots = []
    for _ in range(reps):
        i = _remuestra(rng, cl)
        gb = np.unique(grupo[i], return_inverse=True)[1]
        boots.append(ajustar_eje_ponderado(caida[i], ctrl[i], rumbo[i], gb,
                                           pesos_densidad_inversa(rumbo[i], gb))[0])
    lo, hi, ancho = _ic_desviaciones(theta, boots)
    mayor = 0
    for _ in range(reps_perm):
        rp = _perm_bloques(rng, rumbo, cl)
        mayor += ajustar_eje_ponderado(caida, ctrl, rp, grupo, w)[1] >= amp
    return {"eje": float(theta), "ic_bajo": lo, "ic_alto": hi, "ancho_ic": ancho, "amplitud": amp,
            "p_perm": (1 + mayor) / (1 + reps_perm)}


def veredicto_exposicion(cumple_i: bool, cumple_ii: bool) -> tuple[str, bool]:
    """Texto del veredicto y si dispara la regla de parada (cualquiera de las dos condiciones dispara)."""
    dispara = bool(cumple_i or cumple_ii)
    return (TEXTO_EXPLICA if dispara else TEXTO_NO_EXPLICA), dispara


def _xy_pads(pads, pos: dict) -> tuple[np.ndarray, np.ndarray]:
    """Posiciones proyectadas en km (x este, y norte) de una lista de pads hijo."""
    lat = np.array([pos[p][0] for p in pads])
    lon = np.array([pos[p][1] for p in pads])
    return bloques.proyectar(lat, lon)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    m = muestra(con)
    mart = {r[0]: r[1:] for r in con.execute("select area, eje_grados, ic_bajo, ic_alto from mart_anisotropia_area"
                                             ).fetchall()}
    pos = posiciones_pads(con)
    mayoria = area_por_pad(m["area"], m["clave"])
    orden = [CUENCA] + sorted([a for a in mart if a != CUENCA],
                              key=lambda a: (-int((m["area"] == a).sum()), a))
    filas_exp = []
    for j, a in enumerate(orden):
        sel = np.ones(m["n"], dtype=bool) if a == CUENCA else m["area"] == a
        n, pads = int(sel.sum()), np.unique(m["clave"][sel])
        if a != CUENCA and n < MIN_N_AREA:
            continue
        eje_merma, merma_lo, merma_hi = (float(v) for v in mart[a])
        exp = exposicion_area(m["rumbo"][sel], m["clave"][sel], semilla=SEMILLA_EXP + j)
        x, y = _xy_pads(pads, pos)
        if a == CUENCA:
            g_pad = np.unique(np.array([mayoria[p] for p in pads]), return_inverse=True)[1]
            fil = filas_area(x, y, grupo=g_pad, semilla=SEMILLA_FILAS + j)
        else:
            fil = filas_area(x, y, semilla=SEMILLA_FILAS + j)
        d_exp = dist_axial(eje_merma, exp["eje"])
        d_fil = dist_axial(eje_merma, fil["eje"])
        filas_exp.append((a, n, len(pads), eje_merma, merma_lo, merma_hi, exp["eje"], exp["ic_bajo"],
                          exp["ic_alto"], exp["rbar"], fil["eje"], fil["ic_bajo"], fil["ic_alto"],
                          fil["razon"], d_exp, en_ic(eje_merma, exp["ic_bajo"], exp["ic_alto"], exp["eje"]),
                          d_fil, en_ic(eje_merma, fil["ic_bajo"], fil["ic_alto"], fil["eje"])))
    _escribir(con, "mart_eje_exposicion", COLS_EXP, filas_exp)
    grupo_cuenca = np.unique(m["area"], return_inverse=True)[1]
    rep_cuenca = eje_reponderado_intervalo(m["caida"], m["ctrl"], m["rumbo"], m["clave"], grupo_cuenca,
                                           semilla=SEMILLA_REPOND)
    sel_lc = m["area"] == AREA_FOCO
    rep_lc = eje_reponderado_intervalo(m["caida"][sel_lc], m["ctrl"][sel_lc], m["rumbo"][sel_lc],
                                       m["clave"][sel_lc], np.zeros(int(sel_lc.sum()), dtype=int),
                                       semilla=SEMILLA_REPOND + 1)
    filas_rep = []
    for a, n, r in ((CUENCA, m["n"], rep_cuenca), (AREA_FOCO, int(sel_lc.sum()), rep_lc)):
        filas_rep.append((a, n, r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], r["amplitud"], r["p_perm"],
                          es_definido(r["p_perm"], r["ancho_ic"])))
    _escribir(con, "mart_eje_reponderado", COLS_REPOND, filas_rep)
    d = {f[0]: dict(zip([c for c, _ in COLS_EXP], f)) for f in filas_exp}
    cumple_i = bool(d[AREA_FOCO]["merma_en_ic_exp"] and d[CUENCA]["merma_en_ic_exp"])
    cumple_ii = not filas_rep[0][8]
    texto, dispara = veredicto_exposicion(cumple_i, cumple_ii)
    lc, cu = d[AREA_FOCO], d[CUENCA]

    def sn(x) -> str:
        return "si" if x else "no"

    det_i = (f"LC merma {lc['eje_merma']:.1f} en IC exp ({lc['exp_ic_bajo']:.1f} a {lc['exp_ic_alto']:.1f}): "
             f"{sn(lc['merma_en_ic_exp'])}; Cuenca merma {cu['eje_merma']:.1f} en IC exp "
             f"({cu['exp_ic_bajo']:.1f} a {cu['exp_ic_alto']:.1f}): {sn(cu['merma_en_ic_exp'])}")
    det_ii = (f"Cuenca reponderada: eje {rep_cuenca['eje']:.1f} IC {rep_cuenca['ic_bajo']:.1f} a "
              f"{rep_cuenca['ic_alto']:.1f} ancho {rep_cuenca['ancho_ic']:.1f} p {rep_cuenca['p_perm']:.3f}, "
              f"{'definido' if filas_rep[0][8] else 'sin definir'}")
    _escribir(con, "mart_eje_exposicion_veredicto", COLS_VEREDICTO,
              [(COND_I, cumple_i, det_i, dispara), (COND_II, cumple_ii, det_ii, dispara),
               (COND_VEREDICTO, dispara, texto, dispara)])
    for r in con.execute("select * from mart_eje_exposicion").fetchall():
        a, n, pads, em, elo, ehi, ex, xlo, xhi, rbar, fx, flo, fhi, raz, dx, enx, df, enf = r
        print(f"[eje_exposicion] {a} n={n} pads={pads} merma={em:.1f} (IC {elo:.1f} a {ehi:.1f}) "
              f"exp={ex:.1f} (IC {xlo:.1f} a {xhi:.1f}) rbar={rbar:.3f} filas={fx:.1f} "
              f"(IC {flo:.1f} a {fhi:.1f}) razon={raz:.2f} d_exp={dx:.1f} en_exp={enx} "
              f"d_filas={df:.1f} en_filas={enf}")
    for r in con.execute("select * from mart_eje_reponderado").fetchall():
        a, n, e, lo, hi, an, amp, p, df = r
        print(f"[eje_exposicion] reponderado {a} n={n} eje={e:.1f} IC {lo:.1f} a {hi:.1f} ancho={an:.1f} "
              f"amp={amp:.3f} p={p:.3f} definido={df}")
    for c, cu, det, dd in con.execute("select * from mart_eje_exposicion_veredicto").fetchall():
        print(f"[eje_exposicion] {c} cumple={cu} dispara={dd} ({det})")
    con.close()


def pagina_eje_exposicion(con) -> str:
    """Markdown de wiki/hallazgos/eje_exposicion.md a partir de los marts (no escribe a disco)."""
    exp = [dict(zip([c for c, _ in COLS_EXP], r)) for r in con.execute("select * from mart_eje_exposicion"
                                                                       ).fetchall()]
    rep = [dict(zip([c for c, _ in COLS_REPOND], r)) for r in con.execute("select * from mart_eje_reponderado"
                                                                          ).fetchall()]
    ver = {r[0]: (r[1], r[2], r[3]) for r in con.execute("select * from mart_eje_exposicion_veredicto").fetchall()}
    d = {f["area"]: f for f in exp}
    lc, cu = d[AREA_FOCO], d[CUENCA]
    rc = {f["area"]: f for f in rep}[CUENCA]
    rl = {f["area"]: f for f in rep}[AREA_FOCO]
    ci, cii, cv = ver[COND_I], ver[COND_II], ver[COND_VEREDICTO]

    def sn(x) -> str:
        return "sí" if x else "no"

    def cont(amp) -> str:
        return _pts(2 * amp)

    L = ["# Eje de exposición", "",
         "Página generada por `pipeline/eje_exposicion.py`. Compara el eje de mayor merma con el eje que implica la "
         "geometría de desarrollo (hacia dónde están los padres respecto del hijo) y reestima el eje de merma dándole "
         "a cada dirección el mismo peso.", "",
         "## Resumen", "",
         f"- Veredicto: **{cv[1]}**. {'Dispara' if cv[2] else 'No dispara'} la regla de parada.",
         f"- Condición (i): el eje de merma de Loma Campana ({_g(lc['eje_merma'])} grados) cae dentro del IC de su eje "
         f"de exposición ({_g(lc['exp_ic_bajo'])} a {_g(lc['exp_ic_alto'])}): {sn(lc['merma_en_ic_exp'])}; el de la "
         f"cuenca ({_g(cu['eje_merma'])}) dentro del suyo ({_g(cu['exp_ic_bajo'])} a {_g(cu['exp_ic_alto'])}): "
         f"{sn(cu['merma_en_ic_exp'])}. {'Se cumple' if ci[0] else 'No se cumple'}.",
         f"- Condición (ii): la cuenca reponderada queda en {_g(rc['eje'])} grados, IC {_g(rc['ic_bajo'])} a "
         f"{_g(rc['ic_alto'])} (ancho {_g(rc['ancho_ic'])}), p {_g(rc['p_perm'], 3)}: "
         f"{'sin definir' if cii[0] else 'definido'}. {'Se cumple' if cii[0] else 'No se cumple'}.",
         f"- Loma Campana reponderada: {_g(rl['eje'])} grados, IC {_g(rl['ic_bajo'])} a {_g(rl['ic_alto'])}, p "
         f"{_g(rl['p_perm'], 3)} ({'definido' if rl['definido'] else 'sin definir'}).", "",
         "## Eje de merma contra ejes de exposición", "",
         "Por área: el eje de merma con su IC (mart_anisotropia_area), el eje de exposición (media axial de los "
         "rumbos) con su IC y concentración Rbar, y el eje de filas (primer eje principal de las posiciones de los "
         "pads hijo) con su IC y razón entre autovalores. Dist es la distancia axial en grados.", "",
         "| Área | Eventos | Pads | Eje merma | IC merma | Eje exposición | IC exposición | Rbar | Eje filas | IC filas | Razón autovalores | Dist merma-exp | Merma en IC exp | Dist merma-filas | Merma en IC filas |",
         "| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | --- |"]
    for f in exp:
        L.append(f"| {f['area']} | {_g(f['n'])} | {_g(f['pads'])} | {_g(f['eje_merma'])} | {_g(f['merma_ic_bajo'])} a "
                 f"{_g(f['merma_ic_alto'])} | {_g(f['exp_eje'])} | {_g(f['exp_ic_bajo'])} a {_g(f['exp_ic_alto'])} | "
                 f"{_g(f['exp_rbar'], 3)} | {_g(f['filas_eje'])} | {_g(f['filas_ic_bajo'])} a {_g(f['filas_ic_alto'])} "
                 f"| {_g(f['filas_razon_autovalores'], 1)} | {_g(f['dist_merma_exp'], 1)} | {sn(f['merma_en_ic_exp'])} "
                 f"| {_g(f['dist_merma_filas'], 1)} | {sn(f['merma_en_ic_filas'])} |")
    L += ["", "## Reponderación por dirección", "",
          "Eje de merma reestimado con mínimos cuadrados ponderados (cada dirección pesa igual dentro de cada área), "
          "con dummies de área. El contraste es dos veces la amplitud, en puntos de índice.", "",
          "| Área | Eventos | Eje (grados) | IC 95% (grados) | Ancho IC | Contraste (puntos) | p permutación | Definido |",
          "| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    for f in rep:
        L.append(f"| {f['area']} | {_g(f['n'])} | {_g(f['eje'])} | {_g(f['ic_bajo'])} a {_g(f['ic_alto'])} | "
                 f"{_g(f['ancho_ic'])} | {cont(f['amplitud'])} | {_g(f['p_perm'], 3)} | {sn(f['definido'])} |")
    L += ["", "## Pieza 3: modelo de ramas (no hecha)", "",
          "La pieza 3 (modelo de ramas) no se hizo. Necesita azimut de rama y coordenadas de fondo, que no están en "
          "el warehouse; no se verificó si el padrón de pozos de la Secretaría de Energía o el organismo provincial "
          "los publican. Por eso un veredicto negativo no descarta la geometría de ramas.", "",
          "## Regla fijada antes de correr", "",
          "La muestra es la del eje principal (eventos de 0,3 a menos de 1 km, todos, tengan o no caída), para la "
          "cuenca y las áreas con al menos 60 eventos. El eje de exposición es la media axial de los rumbos con IC "
          "por bootstrap de pads (400 repeticiones); el eje de filas es el primer eje principal de las posiciones "
          "proyectadas de los pads hijo (cuenca centrada por área), también con IC por pads. La reponderación pesa "
          "cada evento por la inversa de los eventos de su área en su bin de rumbo (12 bins de 15 grados) y reestima "
          "con mínimos cuadrados ponderados y dummies de área, con IC por pads y p por permutación de pads completos "
          "(400 y 499 repeticiones) para la cuenca y Loma Campana. Un eje está definido si su p es menor que 0,10 y "
          "su IC mide menos de 90 grados. Dispara la regla si la merma de Loma Campana y de la cuenca caen en sus IC "
          "de exposición, o si la reponderación deja indefinido el eje de la cuenca.", "",
          "## Qué no prueba", "",
          "- El eje de exposición con pads de superficie es un proxy: no es la dirección de las ramas.",
          "- Un eje de merma fuera del IC de exposición no lo separa del SHmax ni demuestra un mecanismo.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
