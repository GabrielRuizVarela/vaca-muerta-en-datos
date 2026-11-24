"""El dia del mes en que empieza la fractura como dosis: la caida de los padres cercanos en el mes 0, segun la fraccion del mes
del padre que la fractura expone.

Se corre despues de pipeline.build:  uv run python -m pipeline.dia_inicio

REGLA FIJADA ANTES DE CORRER (2026-11-23, antes de calcular ninguna cifra de este estudio; no se cambia despues de ver
resultados). La regla completa, con sus razones, es docs/plan-dia-inicio.md; este modulo guarda sus constantes y sus funciones de
veredicto, sin tocar ningun dato. Todo lo que falta (cargar datos, estimar, escribir la pagina) se agrega en un commit posterior y no
cambia nada de lo de abajo.

Resumen:
  * Exposicion f0 = (dias del mes - dia de inicio + 1) / dias del mes (pipeline.sincronia.fraccion_mes0), de la primera fecha de
    inicio de fractura del hijo en el mes 0. Sensibilidad sin veredicto: fd, la fraccion mientras dura la fractura.
  * Muestra: padres a menos de 1 km (eventos de pipeline.placebo.marco, base de los meses -6 a -4, mismos filtros del titular).
  * Estimador: pendiente de f0 en una regresion del indice del mes 0 (acotado a [0, 2]) con efectos fijos de area y de ano de
    fractura, solo cercanos; IC 95% por bootstrap de bloques de 5 km, REPS_BOOT repeticiones.
  * Equilibrio: eta cuadrado de f0 contra operador del hijo, Spearman con edad y con caudal base; pendiente ajustada; pendiente sin
    cada operador grande.
  * Negativos: la misma pendiente en controles, con fecha falsa (-12 y -6 meses) y con la f0 sorteada entre hijos del mismo mes.
  * Tercio monotono; intercepto a exposicion cero leido contra la brecha previa (sin veredicto); Colorado con el mismo diseno.
  * Veredicto en orden: sin muestra, opuesta o plana, no equilibrado, no sobrevive a su placebo, no firme, con dosis.

Signo: el indice es el caudal del mes sobre su base; una dosis en el tiempo es una pendiente NEGATIVA (mas caida cuanto mayor es f0).

Que NO prueba:
  * Es un caudal mensual contra un dia: el mes 0 mezcla dias antes y despues del inicio; la dosis esta atenuada y la prueba lee signo y
    orden, no magnitud por dia.
  * No separa un cierre preventivo del operador de un dano del pozo: los dos empiezan con la fractura.
  * "El dia de inicio no se relaciona con la tendencia del padre" no se puede comprobar; el equilibrio y los placebos la hacen creible.
  * Es una huella medida, sin ajuste por comparaciones multiples, no una prueba de causa.
"""
from __future__ import annotations

import calendar
import math

import duckdb
import numpy as np

from pipeline import bloques, placebo, replicacion, sincronia
from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.cuencas import COLORADO
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, KS_PRE, M0, REPS_BOOT, SEMILLA_PLACEBO, _g

# ------------------------------------------------------------------ constantes fijadas (docs/plan-dia-inicio.md)

K_PRINCIPAL = 0
CLIP_INDICE = (0.0, 2.0)
KM_BLOQUE = 5.0                 # lado de la celda del IC por bloques
DESPLAZAMIENTOS_FALSOS = (-12, -6)   # los corrimientos hacia adelante no se usan: su base cae en los meses 0 a 2 reales
N_PERM = 200                    # sorteos de f0 entre hijos del mismo mes de fractura
OFFSET_SEMILLA_PERM = 900       # semilla del sorteo: SEMILLA_PLACEBO + 900
OFFSET_SEMILLA_TERCIOS = 800    # semilla del bootstrap de la diferencia de terciles: SEMILLA_PLACEBO + 800
OFFSET_SEMILLA_DIAGNOSTICO = 910  # semilla de la lectura posterior del sorteo (fuera del veredicto)
OFFSET_SEMILLA_INTERCEPTO = 810  # semilla del bootstrap del intercepto: SEMILLA_PLACEBO + 810

UMBRAL_DOSIS = -0.05            # limite superior del IC de la pendiente (por unidad de f0): 5 puntos entre el primer y el ultimo dia
RUPTURA_PLACEBO = 0.025         # un placebo rompe si su IC excluye cero y |pendiente| >= esto (la mitad del umbral de dosis)
SESGO_PERM = 0.0125             # el estimador de dias sorteados esta sesgado si |media de las pendientes sorteadas| >= esto
P_PERM = 0.05                   # el p bilateral de dias sorteados debe ser menor que esto

MAX_ETA2 = 0.10                 # equilibrio con el operador del hijo: eta cuadrado de f0 menor que esto
MAX_RHO = 0.10                  # equilibrio con edad y con caudal base: |Spearman| menor que esto
MIN_EVENTOS_OPERADOR = 50       # los operadores con menos eventos cercanos se juntan en "otros"
EDAD_GRUPOS = (12, 24, 48)      # cortes de edad del padre en meses (menos de 12, 12 a 24, 24 a 48, 48 o mas)
PARTE_OPERADOR_GRANDE = 0.10    # un operador es grande si tiene esta parte de los eventos cercanos o mas

MIN_CERCANOS = 1000
MIN_BLOQUES = 30
MIN_TERCIO = 300
MIN_CONTROLES = 3000
MIN_FALSA = 300                 # eventos cercanos de una fecha falsa; con menos, esa fecha queda sin muestra y no rompe


# ------------------------------------------------------------------ funciones de veredicto

def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def rompe(est: float, lo: float, hi: float) -> bool:
    """Un placebo rompe si su IC excluye cero y el valor absoluto de la pendiente es al menos RUPTURA_PLACEBO. Un IC indefinido no rompe."""
    if _nan(est) or _nan(lo) or _nan(hi):
        return False
    return (lo > 0 or hi < 0) and abs(est) >= RUPTURA_PLACEBO


def p_bilateral(real: float, sorteadas) -> float:
    """p bilateral de los dias sorteados: (1 + cantidad de pendientes sorteadas con |valor| >= |real|) / (1 + sorteos)."""
    s = [x for x in sorteadas if not _nan(x)]
    return (1 + sum(abs(x) >= abs(real) for x in s)) / (1 + len(s))


def hay_muestra(r: dict) -> bool:
    """Minimos de eventos cercanos, bloques, eventos por tercio y controles."""
    return (r["n_cercanos"] >= MIN_CERCANOS and r["bloques"] >= MIN_BLOQUES and min(r["n_tercios"]) >= MIN_TERCIO
            and r["n_controles"] >= MIN_CONTROLES)


def equilibrio(r: dict) -> list[str]:
    """Chequeos de equilibrio que fallan (lista vacia: equilibrado)."""
    fallas = []
    if r["eta2_operador"] >= MAX_ETA2:
        fallas.append("operador del hijo")
    if abs(r["rho_edad"]) >= MAX_RHO:
        fallas.append("edad del padre")
    if abs(r["rho_base"]) >= MAX_RHO:
        fallas.append("caudal base")
    return fallas


def placebos_rotos(r: dict) -> list[str]:
    """Chequeos negativos que rompen: pozos de control, cada fecha falsa con muestra y el sesgo de los dias sorteados."""
    rotos = []
    if rompe(*r["control"]):
        rotos.append("pozos de control")
    for d, (n, est, lo, hi) in sorted(r["falsas"].items()):
        if n >= MIN_FALSA and rompe(est, lo, hi):
            rotos.append(f"fecha falsa {d:+d}")
    if abs(r["perm_media"]) >= SESGO_PERM:
        rotos.append("dias sorteados (sesgo)")
    return rotos


def condiciones_no_firme(r: dict) -> list[str]:
    """Condiciones del veredicto 'con dosis' que no se cumplen (lista vacia: todas se cumplen)."""
    pend_hi = r["pend"][2]
    c = []
    if pend_hi >= UMBRAL_DOSIS:
        c.append("el limite superior no baja del umbral de dosis")
    if not r["perm_p"] < P_PERM:
        c.append("p de dias sorteados")
    m1, m2, m3 = r["medianas_tercios"]
    if not (m1 > m2 > m3 and r["dif_tercios"][2] < 0):
        c.append("tercio no monotono")
    if not r["ajustada"][2] < 0:
        c.append("pendiente ajustada")
    for nombre, hi in r["sin_operador"]:
        if not hi < 0:
            c.append(f"sin el operador {nombre}")
    return c


def veredicto(r: dict) -> tuple[str, list[str]]:
    """Veredicto de Vaca Muerta con la regla fijada: (etiqueta, motivos). Orden: sin muestra, opuesta o plana, no equilibrado,
    no sobrevive a su placebo, no firme, con dosis."""
    if not hay_muestra(r):
        return "sin muestra", []
    est, lo, hi = r["pend"]
    if _nan(lo) or _nan(hi):
        return "sin muestra", ["IC indefinido"]
    if lo > 0:
        return "opuesta", []
    if hi >= 0:
        return "plana", []
    f = equilibrio(r)
    if f:
        return "no equilibrado", f
    f = placebos_rotos(r)
    if f:
        return "no sobrevive a su placebo", f
    f = condiciones_no_firme(r)
    if f:
        return "no firme", f
    return "con dosis", []


def veredicto_colorado(r: dict | None) -> str:
    """Colorado: se repite / no se repite / sin muestra / no corrido (r None: el warehouse no se pudo armar)."""
    if r is None:
        return "no corrido"
    if r["n_cercanos"] < MIN_CERCANOS or r["bloques"] < MIN_BLOQUES or min(r["n_tercios"]) < MIN_TERCIO:
        return "sin muestra"
    est, lo, hi = r["pend"]
    if _nan(lo) or _nan(hi):
        return "sin muestra"
    if hi < 0 and not rompe(*r["control"]):
        return "se repite"
    return "no se repite"


def lectura_conjunta(vm: str, co: str) -> str:
    """Una linea con las dos cuencas, sin promediar."""
    if vm == "con dosis":
        return "dosis en las dos cuencas" if co == "se repite" else f"dosis en Vaca Muerta, Colorado {co}"
    return f"Vaca Muerta {vm}, Colorado {co}"


# ------------------------------------------------------------------ datos
# Desde aqui es la implementacion de la regla (commit posterior al de la regla): no cambia ninguna constante ni funcion de arriba.

SEMILLA_K0 = SEMILLA_PLACEBO + 100 + KS_PRE.index(K_PRINCIPAL)      # la del titular para k = 0
SEMILLA_K_PREVIO = SEMILLA_PLACEBO + 100 + KS_PRE.index(-1)         # la del titular para k = -1 (brecha previa)


def _fechas_vm(con) -> tuple[dict, dict]:
    """Primera fecha de inicio de fractura de cada hijo en su mes 0 (la que fija int_frac_hijo) y la ultima fecha de fin de las
    filas de fractura que empiezan en ese mes (precision de implementacion de la sensibilidad fd; no entra en el veredicto)."""
    q = ("select h.hijo, min(f.fecha_inicio), max(f.fecha_fin) from int_frac_hijo h join stg_fractura f on f.pozo_id = h.hijo "
         "where f.fecha_inicio is not null and date_trunc('month', f.fecha_inicio) = h.mes_frac group by h.hijo")
    filas = con.execute(q).fetchall()
    return {int(r[0]): r[1] for r in filas}, {int(r[0]): r[2] for r in filas}


def fd_de(ini, fin) -> float:
    """Fraccion del mes entre el dia de inicio y el menor entre el dia de fin y el ultimo dia del mes (extremos incluidos);
    nan si no hay fecha de fin o es anterior al inicio."""
    if fin is None or fin < ini:
        return float("nan")
    n = calendar.monthrange(ini.year, ini.month)[1]
    ultimo = fin.day if (fin.year, fin.month) == (ini.year, ini.month) else n
    return (ultimo - ini.day + 1) / n


def cargar(con, colorado: bool = False) -> dict:
    """Datos del placebo mas, por hijo: dia de inicio, f0, fd, operador y bloque de 5 km de su pad.

    `con` de Colorado puede estar abierto solo para leer (replicacion.preparar arma sus entradas como tablas temporales).
    """
    if colorado:
        replicacion.preparar(con)
        D = placebo.cargar(con)
        D["bloque_pad"] = replicacion.bloque_por_pad(con, D)
        ini = {int(r[0]): r[1] for r in con.execute("select pozo_id, fecha_frac from co_hijo where hijo").fetchall()}
        fin: dict = {}
    else:
        D = bloques.cargar(con)
        D["bloque_pad"] = D[bloques._nombre(KM_BLOQUE)]
        ini, fin = _fechas_vm(con)
    oper = {int(r[0]): r[1] for r in con.execute("select pozo_id, operador from int_pozo_ubicacion").fetchall()}
    fechas = [ini[int(h)] for h in D["hijo_id"]]
    D["hijo_f0"] = sincronia.fraccion_mes0(fechas)
    D["hijo_dia"] = np.array([f.day for f in fechas], dtype=np.int64)
    D["hijo_fd"] = np.array([fd_de(f, fin.get(int(h))) for f, h in zip(fechas, D["hijo_id"])], dtype=float)
    D["hijo_oper"] = np.array([oper.get(int(h)) or "sin dato" for h in D["hijo_id"]])
    return D


def f0_falso(D: dict, d: int) -> np.ndarray:
    """f0 de cada hijo con su dia de inicio real y los dias del mes que queda d meses despues (el dia se ajusta al ultimo del mes)."""
    mes = D["hijo_mes"] + d + M0
    out = np.empty(len(mes))
    for j, m in enumerate(mes):
        n = calendar.monthrange(int(m) // 12, int(m) % 12 + 1)[1]
        out[j] = (n - min(int(D["hijo_dia"][j]), n) + 1) / n
    return out


# ------------------------------------------------------------------ eventos y regresion

def eventos(D: dict, mes_hijo: np.ndarray | None = None, f0_hijo: np.ndarray | None = None, solo_reales: bool = False,
            anio_hijo: np.ndarray | None = None) -> dict:
    """Eventos cercanos (banda 0) y de control (banda 2) con el indice del mes 0 acotado, f0, fd, area, anio, operador del hijo, edad y
    caudal base del padre, y la clave de bloque de 5 km del pad hijo. Con `mes_hijo` distinto: la fecha de fractura falsa."""
    mes_hijo = D["hijo_mes"] if mes_hijo is None else mes_hijo
    f0_hijo = D["hijo_f0"] if f0_hijo is None else f0_hijo
    anio_hijo = D["hijo_anio"] if anio_hijo is None else anio_hijo
    m = placebo.marco(D, mes_hijo, ks=(K_PRINCIPAL,), base=BASE_LIMPIA, solo_reales=solo_reales)
    y = np.clip(m["idx"][K_PRINCIPAL], *CLIP_INDICE)
    ok = ~np.isnan(y) & (m["banda"] != 1)
    base = placebo._media(D, m["padre"], m["mes"], *BASE_LIMPIA)
    h = m["hijo"]
    return {"y": y[ok], "banda": m["banda"][ok], "f0": f0_hijo[h][ok], "fd": D["hijo_fd"][h][ok], "area": m["area"][ok],
            "anio": anio_hijo[h][ok], "oper": D["hijo_oper"][h][ok], "edad": m["edad"][ok].astype(float),
            "base": np.log(base[ok]), "clave": D["bloque_pad"][m["clave"]][ok], "pad": m["clave"][ok], "hijo": h[ok]}


def subconjunto(e: dict, s: np.ndarray) -> dict:
    return {k: v[s] for k, v in e.items()}


def _dummies(x: np.ndarray) -> np.ndarray:
    return sincronia._dummies(x)


def grupo_operador(oper: np.ndarray) -> np.ndarray:
    """Operador del hijo; los que tienen menos de MIN_EVENTOS_OPERADOR eventos se juntan en 'otros'."""
    u, inv, cnt = np.unique(oper, return_inverse=True, return_counts=True)
    return np.where(cnt[inv] >= MIN_EVENTOS_OPERADOR, oper, "otros")


def grupo_edad(edad: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.array(EDAD_GRUPOS), edad, side="right")


def diseno(e: dict, ajustado: bool = False, x: np.ndarray | None = None) -> np.ndarray:
    """Constante, exposicion (columna 1) y efectos fijos de area y de ano; con `ajustado` (especificacion C) tambien operador del hijo
    (agrupado), grupo de edad del padre y logaritmo del caudal base."""
    x = e["f0"] if x is None else x
    cols = [np.ones(len(x)), x, _dummies(e["area"]), _dummies(e["anio"])]
    if ajustado:
        cols += [_dummies(grupo_operador(e["oper"])), _dummies(grupo_edad(e["edad"])), e["base"][:, None]]
    return np.column_stack(cols)


def _coef1(X: np.ndarray, y: np.ndarray) -> float:
    return float(np.linalg.lstsq(X, y, rcond=None)[0][1])


def percentiles(bs) -> tuple[float, float]:
    bs = np.array([b for b in bs if not _nan(b)])
    return tuple(float(v) for v in np.percentile(bs, [2.5, 97.5])) if len(bs) else (float("nan"), float("nan"))


def ic_bloques(clave: np.ndarray, estadistica, reps: int, semilla: int) -> tuple[float, float]:
    """Percentiles 2,5 y 97,5 de `estadistica(indices)` con remuestreo de bloques completos; la estadistica da nan si no se puede."""
    grupos = _clusters(clave)
    rng = np.random.default_rng(semilla)
    return percentiles([estadistica(_remuestra(rng, grupos)) for _ in range(reps)])


def pendiente_ic(e: dict, reps: int, semilla: int, ajustado: bool = False, x: np.ndarray | None = None) -> tuple[float, float, float]:
    """(pendiente, ic bajo, ic alto) de f0 (o de `x`) sobre el indice del mes 0, con IC por bloques de 5 km."""
    X = diseno(e, ajustado, x)
    y = e["y"]

    def est(i):
        return _coef1(X[i], y[i]) if len(i) >= 5 else float("nan")

    return (_coef1(X, y), *ic_bloques(e["clave"], est, reps, semilla))


# ------------------------------------------------------------------ equilibrio

def rangos(x: np.ndarray) -> np.ndarray:
    """Rangos con empates promediados."""
    _, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    fin = np.cumsum(cnt)
    return ((fin - cnt + 1 + fin) / 2)[inv]


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(rangos(a), rangos(b))[0, 1])


def eta2(f0: np.ndarray, grupo: np.ndarray) -> float:
    """Suma de cuadrados entre grupos de f0 sobre la suma total."""
    tot = float(((f0 - f0.mean()) ** 2).sum())
    if tot == 0:
        return float("nan")
    u, inv = np.unique(grupo, return_inverse=True)
    n = np.bincount(inv)
    m = np.bincount(inv, weights=f0) / n
    return float((n * (m - f0.mean()) ** 2).sum() / tot)


def tabla_operadores(e: dict) -> list[tuple]:
    """Por operador del hijo con MIN_EVENTOS_OPERADOR eventos cercanos o mas: eventos, f0 media y parte de eventos con f0 > 0,9."""
    filas = []
    for o in np.unique(e["oper"]):
        s = e["oper"] == o
        if s.sum() >= MIN_EVENTOS_OPERADOR:
            filas.append((str(o), int(s.sum()), float(e["f0"][s].mean()), float((e["f0"][s] > 0.9).mean())))
    return sorted(filas, key=lambda f: -f[1])


# ------------------------------------------------------------------ pruebas

def terciles(near: dict, reps: int, semilla: int) -> tuple[list[tuple], tuple[float, float, float]]:
    """Medianas del indice por tercil de f0 de los cercanos y la diferencia grupo 3 menos grupo 1 con su IC por bloques."""
    c = sincronia.cortes(near["f0"])
    g = sincronia.grupo(near["f0"], c)
    y = near["y"]
    filas = [(b, int((g == b).sum()), float(np.median(y[g == b])) if (g == b).any() else float("nan"),
              float(near["f0"][g == b].min()), float(near["f0"][g == b].max())) for b in (1, 2, 3)]

    def dif(i):
        a, b = y[i][g[i] == 3], y[i][g[i] == 1]
        return float(np.median(a) - np.median(b)) if len(a) and len(b) else float("nan")

    d = dif(np.arange(len(y)))
    return filas, (d, *ic_bloques(near["clave"], dif, reps, semilla))


def sorteo_dias(D: dict, near: dict, X: np.ndarray, n_perm: int, semilla: int) -> tuple[list[float], list[float]]:
    """Pendiente principal con la f0 de cada hijo sorteada entre hijos con el mismo mes de fractura (el evento hereda la de su hijo).
    Devuelve (pendientes sorteadas, [media, p2,5, p97,5])."""
    rng = np.random.default_rng(semilla)
    por_mes = [np.flatnonzero(D["hijo_mes"] == m) for m in np.unique(D["hijo_mes"])]
    X = X.copy()
    out = []
    for _ in range(n_perm):
        f = D["hijo_f0"].copy()
        for ix in por_mes:
            f[ix] = D["hijo_f0"][rng.permutation(ix)]
        X[:, 1] = f[near["hijo"]]
        out.append(_coef1(X, near["y"]))
    return out, [float(np.mean(out)), *(float(v) for v in np.percentile(out, [2.5, 97.5]))]


def intercepto_y_previa(D: dict, e: dict, reps: int) -> dict:
    """Brecha a exposicion cero (intercepto cercano menos intercepto control) y brecha previa de referencia (mes -1), con IC por bloques."""
    X = diseno(e)
    cerca = e["banda"] == 0
    X0 = X.copy()
    X0[:, 1] = 0.0

    def inter(i):
        a, b = i[cerca[i]], i[~cerca[i]]
        if len(a) < 5 or len(b) < 5:
            return float("nan")
        ba, bb = np.linalg.lstsq(X[a], e["y"][a], rcond=None)[0], np.linalg.lstsq(X[b], e["y"][b], rcond=None)[0]
        return float((X0[a] @ ba).mean() - (X0[b] @ bb).mean())

    todos = np.arange(len(e["y"]))
    g0 = inter(todos)
    ic0 = ic_bloques(e["clave"], inter, reps, SEMILLA_PLACEBO + OFFSET_SEMILLA_INTERCEPTO)
    ep = sincronia.eventos(D, -1)
    ep["clave"] = D["bloque_pad"][ep["clave"]]
    cp = (ep["banda"] == 0).astype(float)
    Xp = np.column_stack([np.ones(len(cp)), cp, _dummies(ep["area"]), _dummies(ep["anio"])])

    def prev(i):
        return _coef1(Xp[i], ep["y"][i]) if (cp[i] == 1).sum() >= 5 and (cp[i] == 0).sum() >= 5 else float("nan")

    gp = prev(np.arange(len(cp)))
    icp = ic_bloques(ep["clave"], prev, reps, SEMILLA_K_PREVIO)
    if ic0[1] < icp[0]:
        lectura = "mas negativa que la previa"
    elif ic0[0] > icp[1]:
        lectura = "menos negativa que la previa"
    else:
        lectura = "coincide con la previa"
    return {"intercepto": (g0, *ic0), "previa": (gp, *icp), "lectura": lectura, "n_previa": int((cp == 1).sum())}


def diagnostico_sorteo(D: dict, near: dict, X: np.ndarray, n_perm: int, semilla: int) -> dict:
    """Lectura posterior, fuera del veredicto: de donde sale el sesgo del sorteo de dias.

    El sorteo de la regla deja a un hijo con su propia f0 a veces (parte esperada: media de 1 / hijos del mes sobre los eventos
    cercanos). Aqui se repite sin esa autoasignacion (rotacion aleatoria dentro del mes) y sin recibir la f0 de un hijo del propio pad
    (rotacion entre pads del mismo mes). Devuelve la parte autoasignada y la media y el rango 2,5 a 97,5 de cada variante."""
    mes, hijo = D["hijo_mes"], near["hijo"]
    n_mes = {int(m): int((mes == m).sum()) for m in np.unique(mes)}
    parte = float(np.mean([1.0 / n_mes[int(mes[j])] for j in hijo]))
    rng = np.random.default_rng(semilla)
    por_mes = [np.flatnonzero(mes == m) for m in np.unique(mes)]
    grupos: dict = {}
    for j in range(len(mes)):
        grupos.setdefault((int(D["hijo_pad"][j]), int(mes[j])), []).append(j)
    pads_mes: dict = {}
    for g in grupos.values():
        pads_mes.setdefault(int(mes[g[0]]), []).append(g)
    X = X.copy()
    a, b = [], []
    for _ in range(n_perm):
        f = D["hijo_f0"].copy()
        for ix in por_mes:
            if len(ix) >= 2:
                p = rng.permutation(ix)
                f[p] = D["hijo_f0"][np.roll(p, 1)]
        X[:, 1] = f[hijo]
        a.append(_coef1(X, near["y"]))
        f = D["hijo_f0"].copy()
        for gs in pads_mes.values():
            if len(gs) >= 2:
                p = rng.permutation(len(gs))   # ciclo aleatorio: cada pad recibe la f0 de otro pad, ninguno la suya
                for j in range(len(gs)):
                    f[gs[int(p[j])]] = D["hijo_f0"][gs[int(p[j - 1])][0]]
        X[:, 1] = f[hijo]
        b.append(_coef1(X, near["y"]))
    return {"parte": parte, "sin_auto": (float(np.mean(a)), *(float(v) for v in np.percentile(a, [2.5, 97.5]))),
            "sin_pad": (float(np.mean(b)), *(float(v) for v in np.percentile(b, [2.5, 97.5])))}


def calcular(D: dict, reps: int = REPS_BOOT, n_perm: int = N_PERM) -> dict:
    """Todos los numeros de la regla sobre unos datos cargados. Devuelve las entradas de `veredicto` y las filas de las tablas."""
    e = eventos(D)
    near = subconjunto(e, e["banda"] == 0)
    ctrl = subconjunto(e, e["banda"] == 2)
    r: dict = {"n_cercanos": int(len(near["y"])), "n_controles": int(len(ctrl["y"])), "pads": int(len(np.unique(near["pad"]))),
               "bloques": int(len(np.unique(near["clave"])))}
    filas: list[tuple] = []

    def fila(metrica, detalle, n, est, lo=float("nan"), hi=float("nan")):
        filas.append((metrica, detalle, int(n), float(est), float(lo), float(hi)))

    r["pend"] = pendiente_ic(near, reps, SEMILLA_K0)
    fila("pendiente", "principal", r["n_cercanos"], *r["pend"])
    r["ajustada"] = pendiente_ic(near, reps, SEMILLA_K0, ajustado=True)
    fila("pendiente", "ajustada", r["n_cercanos"], *r["ajustada"])
    r["control"] = pendiente_ic(ctrl, reps, SEMILLA_K0)
    fila("pendiente", "control", r["n_controles"], *r["control"])
    ok_fd = ~np.isnan(near["fd"])
    nfd = subconjunto(near, ok_fd)
    if ok_fd.sum() >= 5:
        fila("pendiente", "fd", ok_fd.sum(), *pendiente_ic(nfd, reps, SEMILLA_K0, x=nfd["fd"]))

    # equilibrio
    go = grupo_operador(near["oper"])
    r["eta2_operador"] = eta2(near["f0"], go)
    r["rho_edad"] = spearman(near["f0"], near["edad"])
    r["rho_base"] = spearman(near["f0"], near["base"])
    for nombre, fn in (("eta2_operador", lambda i: eta2(near["f0"][i], go[i])),
                       ("rho_edad", lambda i: spearman(near["f0"][i], near["edad"][i])),
                       ("rho_base", lambda i: spearman(near["f0"][i], near["base"][i]))):
        fila("equilibrio", nombre, r["n_cercanos"], r[nombre], *ic_bloques(near["clave"], fn, reps, SEMILLA_K0))
    operadores = tabla_operadores(near)
    r["sin_operador"] = []
    for o in np.unique(near["oper"]):
        s = near["oper"] == o
        if s.mean() >= PARTE_OPERADOR_GRANDE:
            sub = subconjunto(near, ~s)
            p = pendiente_ic(sub, reps, SEMILLA_K0)
            r["sin_operador"].append((str(o), p[2]))
            fila("pendiente_sin_operador", str(o), len(sub["y"]), *p)

    # negativos
    r["falsas"] = {}
    for j, d in enumerate(DESPLAZAMIENTOS_FALSOS):
        mes = D["hijo_mes"] + d
        ef = eventos(D, mes, f0_falso(D, d), solo_reales=True, anio_hijo=(mes + M0) // 12)
        nf = subconjunto(ef, ef["banda"] == 0)
        if len(nf["y"]) >= 5:
            p = pendiente_ic(nf, reps, SEMILLA_PLACEBO + 200 + 1 + j)
        else:
            p = (float("nan"),) * 3
        r["falsas"][d] = (int(len(nf["y"])), *p)
        fila("pendiente_fecha_falsa", f"{d:+d}", len(nf["y"]), *p)
    sorteadas, resumen = sorteo_dias(D, near, diseno(near), n_perm, SEMILLA_PLACEBO + OFFSET_SEMILLA_PERM)
    r["perm_media"], r["perm_p"] = resumen[0], p_bilateral(r["pend"][0], sorteadas)
    fila("sorteo", "media", n_perm, resumen[0], resumen[1], resumen[2])
    fila("sorteo", "p_bilateral", n_perm, r["perm_p"])
    dg = diagnostico_sorteo(D, near, diseno(near), n_perm, SEMILLA_PLACEBO + OFFSET_SEMILLA_DIAGNOSTICO)
    r["diag_parte"], r["diag_sin_auto"], r["diag_sin_pad"] = dg["parte"], dg["sin_auto"], dg["sin_pad"]
    fila("diagnostico", "parte autoasignada", n_perm, dg["parte"])
    fila("diagnostico", "sorteo sin autoasignacion", n_perm, *dg["sin_auto"])
    fila("diagnostico", "sorteo sin pad propio", n_perm, *dg["sin_pad"])

    # terciles
    t, r["dif_tercios"] = terciles(near, reps, SEMILLA_PLACEBO + OFFSET_SEMILLA_TERCIOS)
    r["n_tercios"] = tuple(x[1] for x in t)
    r["medianas_tercios"] = tuple(x[2] for x in t)
    for b, n, med, lo_f, hi_f in t:
        fila("tercil", f"{b}", n, med, lo_f, hi_f)
    fila("tercil", "3 menos 1", r["n_cercanos"], *r["dif_tercios"])

    # intercepto y previa
    ip = intercepto_y_previa(D, e, reps)
    fila("brecha", "exposicion cero", r["n_cercanos"], *ip["intercepto"])
    fila("brecha", "previa (mes -1)", ip["n_previa"], *ip["previa"])
    r["lectura_intercepto"] = ip["lectura"]
    return {"r": r, "filas": filas, "operadores": operadores}


# ------------------------------------------------------------------ tablas

COLS_DIA = [("metrica", "varchar"), ("detalle", "varchar"), ("n", "integer"), ("estimacion", "double"), ("ic_bajo", "double"),
            ("ic_alto", "double")]
COLS_OPERADOR = [("operador", "varchar"), ("eventos", "integer"), ("f0_media", "double"), ("parte_f0_mayor_09", "double")]
COLS_VEREDICTO = [("cuenca", "varchar"), ("veredicto", "varchar"), ("motivos", "varchar"), ("lectura_intercepto", "varchar"),
                  ("eventos_cercanos", "integer"), ("eventos_control", "integer"), ("pads", "integer"), ("bloques", "integer")]


def tablas_de(res: dict, cuenca: str) -> dict:
    r = res["r"]
    if cuenca == "colorado":
        v, motivos = veredicto_colorado(r), []
    else:
        v, motivos = veredicto(r)
    return {"veredicto": [(cuenca, v, "; ".join(motivos), r["lectura_intercepto"], r["n_cercanos"], r["n_controles"], r["pads"], r["bloques"])],
            "metricas": res["filas"], "operadores": res["operadores"]}


def nombre_tabla(sufijo: str, cuenca: str = "") -> str:
    return "mart_dia_inicio" + (f"_{cuenca}" if cuenca else "") + sufijo


def escribir(con, t: dict, cuenca: str = "") -> None:
    """Escribe los tres marts; los nombres van literales (no de nombre_tabla) para que pipeline.linaje los encuentre."""
    if cuenca:
        _escribir(con, "mart_dia_inicio_colorado", COLS_DIA, t["metricas"])
        _escribir(con, "mart_dia_inicio_colorado_operador", COLS_OPERADOR, t["operadores"])
        _escribir(con, "mart_dia_inicio_colorado_veredicto", COLS_VEREDICTO, t["veredicto"])
    else:
        _escribir(con, "mart_dia_inicio", COLS_DIA, t["metricas"])
        _escribir(con, "mart_dia_inicio_operador", COLS_OPERADOR, t["operadores"])
        _escribir(con, "mart_dia_inicio_veredicto", COLS_VEREDICTO, t["veredicto"])


# ------------------------------------------------------------------ pagina del wiki y sus cifras
# Cada linea de cifras de la pagina se define una sola vez (`especificacion`): la pagina la rellena con el warehouse y
# pipeline.claims arma de las mismas literales el patron que la verifica. Lo que se imprime y lo que se verifica no pueden separarse.

REGLA_SHA = "d370e0b"        # commit de la regla, anterior a toda corrida
VEREDICTOS_VM = ("sin muestra", "opuesta", "plana", "no equilibrado", "no sobrevive a su placebo", "no firme", "con dosis")
ESTADOS_COLORADO = ("se repite", "no se repite", "sin muestra", "no corrido")
CLAVES_SOLO_VM = ("resumen", "resumen_controles", "diag_parte", "diag_sin_auto", "diag_sin_pad")   # lineas que la pagina no repite para Colorado
MAX_OPERADORES_GRANDES = 4   # filas "sin el operador grande i" que la pagina y sus claims admiten

TEXTO_ESTUDIO = {
    "con dosis": "Entre los padres a menos de 1 km, la caída del mes de la fractura crece cuanto más temprano en el mes empieza la "
                 "fractura del hijo (pendiente e IC de la página), con el día de inicio equilibrado frente a operador, edad y caudal "
                 "base, sin pendiente en pozos de control ni en fechas falsas. Bajo un supuesto que se puede revisar (el día de inicio "
                 "no se relaciona con la tendencia del padre), es una dosis en el tiempo, sin ningún pozo lejano en la comparación. No "
                 "separa cierre de daño: los dos empiezan con la fractura.",
    "plana": "El día del mes en que empieza la fractura no explica la caída del mes 0 entre padres cercanos: la brecha de 19 a 23 "
             "puntos queda como asociación y no se atribuye a la fractura. La pendiente de sincronía de la página anterior, medida "
             "contra controles, no se sostiene con este estimador y se lee como resultado de la comparación con los controles, no de "
             "la dosis.",
    "opuesta": "Los padres cercanos caen menos cuanto antes empieza la fractura: no hay dosis en el tiempo y el vínculo temporal con "
               "la fractura queda debilitado.",
    "no equilibrado": "El día de inicio no es independiente de {motivos}: la pendiente se informa y no se lee como dosis.",
    "no sobrevive a su placebo": "La misma pendiente aparece donde no hay exposición (controles, fechas falsas, días sorteados): la "
                                 "huella no se separa del calendario o de la selección y no se lee como dosis.",
    "no firme": "La pendiente es negativa pero no pasa todas las condiciones fijadas: se dice cuál no, y la huella no se promueve a "
                "dosis.",
    "sin muestra": "No hay eventos suficientes para decidir; no se calcula veredicto.",
}

TEXTO_COLORADO = {
    "se repite": "El límite superior del IC de la pendiente de los cercanos es menor que 0 y los pozos de control no rompen.",
    "no se repite": "El IC de la pendiente de los cercanos incluye cero o es positivo, o los pozos de control rompen.",
    "sin muestra": "Los eventos de Colorado no llegan a los mínimos fijados.",
    "no corrido": "El warehouse de Colorado no se pudo armar con los datos públicos de esta máquina; se dice por qué y no se reemplaza.",
}


def _con_acentos(motivos: str) -> str:
    """Los motivos del veredicto vienen sin acentos (la regla se fijo asi); en la pagina van con ellos."""
    for a, b in (("dias", "días"), ("limite", "límite"), ("monotono", "monótono")):
        motivos = motivos.replace(a, b)
    return motivos


def _pre(cuenca: str) -> str:
    return f"_{cuenca}" if cuenca else ""


def _sql_m(cuenca: str, metrica: str, detalle: str, col: str) -> str:
    return f"select {col} from {nombre_tabla('', cuenca)} where metrica = '{metrica}' and detalle = '{detalle}'"


def _sql_op(cuenca: str, i: int, col: str) -> str:
    return (f"select {col} from {nombre_tabla('', cuenca)} where metrica = 'pendiente_sin_operador' order by detalle "
            f"limit 1 offset {i}")


def _sql_v(cuenca: str, col: str) -> str:
    return f"select {col} from {nombre_tabla('_veredicto', cuenca)}"


def especificacion(cuenca: str = "") -> dict[str, tuple[list[str], list[tuple[str, float, int]]]]:
    """Las lineas con cifras de la pagina de una cuenca: clave -> (literales, cifras). Una cifra es (sql, factor, decimales); hay
    una literal mas que cifras y la pagina las intercala. {P} en la primera literal es el prefijo de la cuenca ('' o 'Colorado: ')."""
    def m(metrica, detalle, col, factor=1.0, dec=1):
        return (_sql_m(cuenca, metrica, detalle, col), factor, dec)

    def fila_pend(clave, rotulo, metrica, detalle, out):
        out[clave] = (["| {P}" + rotulo + " | ", " | ", " | ", " a ", " |"],
                      [m(metrica, detalle, "n", 1.0, 0), m(metrica, detalle, "estimacion", 10), m(metrica, detalle, "ic_bajo", 10),
                       m(metrica, detalle, "ic_alto", 10)])

    s: dict = {}
    vv = lambda col, dec=0: (_sql_v(cuenca, col), 1.0, dec)  # noqa: E731
    s["resumen"] = (["- {P}Pendiente de f0 entre padres cercanos: ", " puntos de índice por cada 0,1 de f0 (IC 95% por bloques de 5 km: ",
                     " a ", "), sobre ", " eventos cercanos de ", " pads hijo en ", " bloques de 5 km. Entre un inicio el último día "
                     "del mes y uno el primer día el índice cambia ", " puntos."],
                    [m("pendiente", "principal", "estimacion", 10), m("pendiente", "principal", "ic_bajo", 10),
                     m("pendiente", "principal", "ic_alto", 10), vv("eventos_cercanos"), vv("pads"), vv("bloques"),
                     m("pendiente", "principal", "estimacion", 100)])
    s["resumen_controles"] = (["- {P}Eventos de control (2 a 5 km): ", ", con pendiente ", " puntos por cada 0,1 de f0."],
                              [vv("eventos_control"), m("pendiente", "control", "estimacion", 10)])
    fila_pend("pend_principal", "Cercanos, principal", "pendiente", "principal", s)
    fila_pend("pend_ajustada", "Cercanos, ajustada por operador, edad y caudal base", "pendiente", "ajustada", s)
    fila_pend("pend_control", "Controles (2 a 5 km)", "pendiente", "control", s)
    fila_pend("pend_fd", "Cercanos, con fd en lugar de f0", "pendiente", "fd", s)
    for i in range(MAX_OPERADORES_GRANDES):
        s[f"pend_op{i + 1}"] = (["| {P}Cercanos sin el operador grande " + str(i + 1) + " | ", " | ", " | ", " a ", " |"],
                                [(_sql_op(cuenca, i, "n"), 1.0, 0), (_sql_op(cuenca, i, "estimacion"), 10, 1),
                                 (_sql_op(cuenca, i, "ic_bajo"), 10, 1), (_sql_op(cuenca, i, "ic_alto"), 10, 1)])
    fila_pend("pend_falsa12", "Fecha falsa, 12 meses antes", "pendiente_fecha_falsa", "-12", s)
    fila_pend("pend_falsa6", "Fecha falsa, 6 meses antes", "pendiente_fecha_falsa", "-6", s)
    s["pend_sorteo"] = (["| {P}Días sorteados (media y rango 2,5 a 97,5 de los sorteos) | ", " | ", " | ", " a ", " |"],
                        [m("sorteo", "media", "n", 1.0, 0), m("sorteo", "media", "estimacion", 10), m("sorteo", "media", "ic_bajo", 10),
                         m("sorteo", "media", "ic_alto", 10)])
    s["p_sorteo"] = (["- {P}p bilateral de los días sorteados: ", "."], [m("sorteo", "p_bilateral", "estimacion", 1.0, 3)])
    for clave, rotulo, nombre in (("eta2", "Eta cuadrado de f0 contra el operador del hijo", "eta2_operador"),
                                  ("rho_edad", "Spearman de f0 con la edad del padre", "rho_edad"),
                                  ("rho_base", "Spearman de f0 con el caudal base del padre", "rho_base")):
        s["eq_" + clave] = (["| {P}" + rotulo + " | ", " | ", " | ", " a ", " |"],
                            [m("equilibrio", nombre, "n", 1.0, 0), m("equilibrio", nombre, "estimacion", 1.0, 3),
                             m("equilibrio", nombre, "ic_bajo", 1.0, 3), m("equilibrio", nombre, "ic_alto", 1.0, 3)])
    for b in (1, 2, 3):
        s[f"tercil{b}"] = (["| {P}" + str(b) + " | ", " | ", " | ", " | ", " |"],
                           [m("tercil", str(b), "ic_bajo", 1.0, 3), m("tercil", str(b), "ic_alto", 1.0, 3),
                            m("tercil", str(b), "n", 1.0, 0), m("tercil", str(b), "estimacion", 100)])
    s["tercil_dif"] = (["- {P}Grupo 3 menos grupo 1: ", " puntos de índice (IC 95% por bloques de 5 km: ", " a ", "), sobre ",
                        " eventos cercanos."],
                       [m("tercil", "3 menos 1", "estimacion", 100), m("tercil", "3 menos 1", "ic_bajo", 100),
                        m("tercil", "3 menos 1", "ic_alto", 100), m("tercil", "3 menos 1", "n", 1.0, 0)])
    s["brecha_cero"] = (["- {P}Brecha a exposición cero, cercanos menos controles: ", " puntos de índice (IC 95% por bloques de 5 km: ",
                         " a ", "), sobre ", " eventos cercanos."],
                        [m("brecha", "exposicion cero", "estimacion", 100), m("brecha", "exposicion cero", "ic_bajo", 100),
                         m("brecha", "exposicion cero", "ic_alto", 100), m("brecha", "exposicion cero", "n", 1.0, 0)])
    s["brecha_previa"] = (["- {P}Brecha previa de referencia, mes -1: ", " puntos de índice (IC 95% por bloques de 5 km: ", " a ",
                           "), sobre ", " eventos cercanos."],
                          [m("brecha", "previa (mes -1)", "estimacion", 100), m("brecha", "previa (mes -1)", "ic_bajo", 100),
                           m("brecha", "previa (mes -1)", "ic_alto", 100), m("brecha", "previa (mes -1)", "n", 1.0, 0)])
    s["diag_parte"] = (["- {P}Parte de los eventos cercanos que en un sorteo de la regla conserva la f0 de su propio hijo, en promedio: ",
                        " %."], [m("diagnostico", "parte autoasignada", "estimacion", 100)])
    s["diag_sin_auto"] = (["| {P}Sorteo sin autoasignación (rotación dentro del mes) | ", " | ", " | ", " a ", " |"],
                          [m("diagnostico", "sorteo sin autoasignacion", "n", 1.0, 0),
                           m("diagnostico", "sorteo sin autoasignacion", "estimacion", 10),
                           m("diagnostico", "sorteo sin autoasignacion", "ic_bajo", 10),
                           m("diagnostico", "sorteo sin autoasignacion", "ic_alto", 10)])
    s["diag_sin_pad"] = (["| {P}Sorteo sin f0 de un hijo del mismo pad (rotación entre pads del mes) | ", " | ", " | ", " a ", " |"],
                         [m("diagnostico", "sorteo sin pad propio", "n", 1.0, 0),
                          m("diagnostico", "sorteo sin pad propio", "estimacion", 10),
                          m("diagnostico", "sorteo sin pad propio", "ic_bajo", 10),
                          m("diagnostico", "sorteo sin pad propio", "ic_alto", 10)])
    return s


def _sustituir(lits: list[str], pref: str) -> list[str]:
    return [lits[0].replace("{P}", pref)] + lits[1:]


def _valores(con, cifras) -> list[str]:
    out = []
    for sql, factor, dec in cifras:
        r = con.execute(sql).fetchone()
        out.append(None if r is None else _g(factor * r[0], dec))
    return out


def linea(con, spec: dict, clave: str, pref: str = "") -> str | None:
    """La linea `clave` rellena con el warehouse; None si alguna cifra no existe (por ejemplo fd en Colorado)."""
    lits, cifras = spec[clave]
    v = _valores(con, cifras)
    if any(x is None for x in v):
        return None
    lits = _sustituir(lits, pref)
    out = lits[0]
    for x, l in zip(v, lits[1:]):
        out += x + l
    return out


def _tiene(con, tabla: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [tabla]).fetchone()[0])


def _lineas(con, spec: dict, claves: list[str], pref: str = "") -> list[str]:
    return [x for x in (linea(con, spec, k, pref) for k in claves) if x is not None]


def _tabla_pendientes(con, spec: dict, pref: str, op_claves: list[str]) -> list[str]:
    cab = ["| Estimación | Eventos o sorteos | Pendiente (puntos por 0,1 de f0) | IC 95% (puntos por 0,1) |", "| --- | ---: | ---: | --- |"]
    claves = ["pend_principal", "pend_ajustada", "pend_control", "pend_fd", *op_claves, "pend_falsa12", "pend_falsa6", "pend_sorteo"]
    return cab + _lineas(con, spec, claves, pref)


def _bloque_cuenca(con, cuenca: str, nivel: str) -> list[str]:
    """Pendientes, equilibrio, tercios e intercepto de una cuenca. `nivel` es el encabezado de las secciones ('##' o '###')."""
    spec = especificacion(cuenca)
    pref = "Colorado: " if cuenca else ""
    lecto = con.execute(f"select lectura_intercepto, motivos from {nombre_tabla('_veredicto', cuenca)}").fetchone()
    ops = [f"pend_op{i + 1}" for i in range(MAX_OPERADORES_GRANDES)]
    grandes = [r[0] for r in con.execute(
        f"select detalle from {nombre_tabla('', cuenca)} where metrica = 'pendiente_sin_operador' order by detalle").fetchall()]
    L = [f"{nivel} Pendientes y chequeos negativos", "",
         "La pendiente se lee por cada 0,1 de f0 (un décimo del mes del padre) en puntos de índice. Una dosis en el tiempo es "
         "negativa: más caída cuanto más del mes expone la fractura. Cada fila es la misma regresión con los efectos fijos de área y de "
         "año de fractura; el IC es bootstrap de percentiles por bloques de 5 km.", ""]
    L += _tabla_pendientes(con, spec, pref, ops)
    L += ["", "Los operadores grandes (10% o más de los eventos cercanos) son, en orden alfabético y como los numera la tabla: "
          + (", ".join(f"{i + 1} {n}" for i, n in enumerate(grandes)) if grandes else "ninguno") + ".", ""]
    L += _lineas(con, spec, ["p_sorteo"], pref)
    L += ["", f"{nivel} Equilibrio del día de inicio", "",
          "| Chequeo | Eventos | Valor | IC 95% por bloques de 5 km |", "| --- | ---: | ---: | --- |"]
    L += _lineas(con, spec, ["eq_eta2", "eq_rho_edad", "eq_rho_base"], pref)
    L += ["", "Equilibrado si el eta cuadrado es menor que 0,10 y los dos Spearman tienen valor absoluto menor que 0,10.", ""]
    if con.execute(f"select count(*) from {nombre_tabla('_operador', cuenca)}").fetchone()[0]:
        L += [f"{nivel} Día de inicio por operador del hijo", "",
              "| Operador del hijo | Eventos cercanos | f0 media | Parte con inicio en los tres primeros días |",
              "| --- | ---: | ---: | ---: |"]
        for o, n, f0m, parte in con.execute(f"select * from {nombre_tabla('_operador', cuenca)} order by eventos desc, operador").fetchall():
            L.append(f"| {pref}{o} | {_g(n)} | {_g(f0m, 3)} | {_g(100 * parte, 1)} % |")
        L.append("")
    L += [f"{nivel} Tercios del día de inicio", "",
          "Grupo 1: inicio tarde en el mes (poca exposición); grupo 3: inicio temprano (mucha). Índice mediano del mes 0 en puntos "
          "(la base vale 100).", "",
          "| Grupo | f0 desde | f0 hasta | Eventos cercanos | Índice mediano |", "| ---: | ---: | ---: | ---: | ---: |"]
    L += _lineas(con, spec, ["tercil1", "tercil2", "tercil3"], pref)
    L += ["", *_lineas(con, spec, ["tercil_dif"], pref), "",
          f"{nivel} Intercepto a exposición cero", "",
          "Brecha entre cercanos y controles que la regresión predice con f0 = 0, comparada con la brecha que el estudio mide el mes "
          "anterior a la fractura. No tiene veredicto propio.", ""]
    L += _lineas(con, spec, ["brecha_cero", "brecha_previa"], pref)
    L += ["", f"Lectura fijada por la regla: la brecha a exposición cero **{lecto[0]}**.", ""]
    return L


def _lectura_posterior(con) -> list[str]:
    spec = especificacion("")
    L = ["## Lectura posterior a la regla (no entra en el veredicto)", "",
         "Esta sección se escribió después de ver los resultados y está fuera de la regla fijada en el commit "
         f"`{REGLA_SHA}`. No cambia el veredicto ni ninguna constante; solo mira de dónde viene el sesgo de los días sorteados.", "",
         "El sorteo de la regla permuta la f0 entre hijos del mismo mes de fractura y puede devolverle a un hijo su propia f0. Se repitió "
         "con dos sorteos que no lo permiten: una rotación dentro del mes (ningún hijo recibe la suya) y una rotación entre pads del "
         "mismo mes (ningún hijo recibe la f0 de un hijo de su pad), salvo en los meses con un solo hijo o un solo pad, que no rotan "
         "(una fracción mínima de los eventos cercanos).", ""]
    L += _lineas(con, spec, ["diag_parte"])
    L += ["", "| Estimación | Sorteos | Media (puntos por 0,1) | Rango 2,5 a 97,5 (puntos por 0,1) |", "| --- | ---: | ---: | --- |"]
    L += _lineas(con, spec, ["pend_sorteo", "diag_sin_auto", "diag_sin_pad"])
    sesgos = [abs(con.execute(_sql_m("", "diagnostico", d, "estimacion")).fetchone()[0])
              for d in ("sorteo sin autoasignacion", "sorteo sin pad propio")]
    if all(x >= SESGO_PERM for x in sesgos):
        L += ["", f"Con cualquiera de los dos sorteos la media sorteada sigue en valor absoluto por encima del límite de sesgo de la regla "
              f"({_g(10 * SESGO_PERM, 3)} puntos por 0,1): el sesgo no viene de que un hijo conserve su propio día ni de que reciba el de "
              "un hijo de su pad. No se investigó otra causa. El veredicto queda como lo fijó la regla.", ""]
    else:
        L += ["", f"Con alguno de los dos sorteos la media sorteada queda por debajo del límite de sesgo de la regla "
              f"({_g(10 * SESGO_PERM, 3)} puntos por 0,1 en valor absoluto): una parte del sesgo viene de lo que ese sorteo permitía. "
              "El veredicto queda como lo fijó la regla, que usa el sorteo original.", ""]
    return L


def pagina_dia_inicio(con) -> str:
    v, motivos, lectura, nc, nk, pads, bloques = con.execute(
        f"select veredicto, motivos, lectura_intercepto, eventos_cercanos, eventos_control, pads, bloques "
        f"from {nombre_tabla('_veredicto')}").fetchone()
    spec = especificacion("")
    texto = TEXTO_ESTUDIO[v].replace("{motivos}", _con_acentos(motivos) or "operador, edad o caudal base")
    co_hay = _tiene(con, nombre_tabla("_veredicto", "colorado"))
    co = con.execute(f"select veredicto, motivos from {nombre_tabla('_veredicto', 'colorado')}").fetchone() if co_hay else None
    co_v = co[0] if co else "no corrido"
    L = ["# El día de inicio como dosis", "",
         f"Página generada por `pipeline/dia_inicio.py`. Pregunta si la caída de los padres a menos de 1 km en el mes de la fractura "
         "del hijo crece con la parte del mes del padre que la fractura expone: un inicio el día 3 expone casi todo el mes 0, uno el día "
         "27 casi nada, y nadie elige el día mirando la cifra mensual del padre. Se compara cada padre cercano solo con padres cercanos; "
         "ningún pozo lejano entra en la pendiente. La regla completa, con sus razones, es [plan-dia-inicio](../../docs/plan-dia-inicio.md) "
         f"y se fijó en el commit `{REGLA_SHA}`, antes de calcular ninguna cifra de este estudio. Complementa [Sincronía dentro del mes]"
         "(sincronia.md), que mide la misma fracción contra controles lejanos.", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada (posición {VEREDICTOS_VM.index(v) + 1} de {len(VEREDICTOS_VM)} en el orden de la regla): "
         f"**{v}**." + (f" Motivos: {_con_acentos(motivos)}." if motivos else ""), "",
         texto, ""]
    L += _lineas(con, spec, ["resumen", "resumen_controles", "p_sorteo"])
    L += ["", f"Lectura conjunta con Colorado: {lectura_conjunta(v, co_v)}.", ""]
    L += ["## Regla fijada antes de correr", "",
          "- Exposición f0 = (días del mes - día de inicio + 1) / días del mes, con la primera fecha de inicio de fractura del hijo en su "
          "mes 0 y los días reales del mes. La sensibilidad fd cuenta solo los días hasta el fin de la fractura; no entra en el veredicto.",
          "- Muestra: padres a menos de 1 km del hijo más cercano, con los filtros del titular (base limpia de los meses -6 a -4, edad del "
          "padre de al menos 6 meses, caudal base mayor que 1 m3/d). Resultado: índice de petróleo del mes 0, acotado a 0 a 2.",
          f"- Umbral de dosis: límite superior del IC de la pendiente menor que {_g(UMBRAL_DOSIS, 2)} por unidad de f0 "
          f"({_g(100 * UMBRAL_DOSIS, 0)} puntos entre el primer y el último día). Un chequeo negativo rompe si su IC excluye cero y su "
          f"pendiente es al menos {_g(RUPTURA_PLACEBO, 3)} por unidad (el de días sorteados, si su media es al menos {_g(SESGO_PERM, 4)}).",
          "- Orden del veredicto: sin muestra, opuesta o plana, no equilibrado, no sobrevive a su placebo, no firme, con dosis.", ""]
    L += _bloque_cuenca(con, "", "##")
    L += ["## Qué dice el estudio con este veredicto", "", texto, "",
          "Si el veredicto no es «con dosis», el README y el sitio no ganan ninguna frase nueva: la fila «Sincronía dentro del mes» se "
          "vuelve a leer con esta página al lado.", ""]
    L += ["## Colorado", ""]
    if co_hay and co_v != "no corrido":
        L += [f"Veredicto de Colorado (posición {ESTADOS_COLORADO.index(co_v) + 1} de {len(ESTADOS_COLORADO)}): **{co_v}**. "
              f"{TEXTO_COLORADO[co_v]}", "",
              "Mismo diseño, mismas constantes y mismas semillas sobre el warehouse opcional de Colorado; la fecha de cada hijo es la "
              "de inicio de trabajo de su primera divulgación de FracFocus. Efectos fijos: condado y año de fractura. No tiene fd.", ""]
        L += _bloque_cuenca(con, "colorado", "###")
    else:
        L += [f"No corrido: {TEXTO_COLORADO['no corrido']}", ""]
    L += _lectura_posterior(con)
    L += ["## Límites", "",
          "- Es una pendiente de un caudal mensual contra un día: el mes 0 mezcla días antes y después del inicio, así que la dosis está "
          "atenuada; la prueba lee signo y orden, no magnitud por día.",
          "- No separa un cierre preventivo del operador de un daño del pozo: los dos empiezan con la fractura.",
          "- «El día de inicio no se relaciona con la tendencia del padre» no se puede comprobar; el equilibrio y los placebos la hacen "
          "creíble y no la prueban.",
          "- Los controles heredan la f0 de su hijo más cercano: la prueba de controles mide que esa f0 no mueve a un pozo lejano, no que "
          "no haya derrame a 2 km.",
          "- El IC es bootstrap por bloques de 5 km sin ajuste por comparaciones múltiples. Es una huella medida, no una prueba de causa.",
          ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb", colorado: bool = False) -> None:
    """Vaca Muerta sobre su warehouse; con `colorado`, la cuenca DJ sobre el suyo (solo lectura) y las tablas en el de Vaca Muerta."""
    con = duckdb.connect(str(path))
    try:
        if not colorado:
            D = cargar(con)
        else:
            if not COLORADO.db.exists():
                print(f"[dia_inicio] Colorado no corrido: falta {COLORADO.db}", flush=True)
                return
            con_c = duckdb.connect(str(COLORADO.db), read_only=True)
            try:
                D = cargar(con_c, colorado=True)
            finally:
                con_c.close()
        t = tablas_de(calcular(D), COLORADO.id if colorado else "")
        escribir(con, t, COLORADO.id if colorado else "")
        for f in t["veredicto"]:
            print("[dia_inicio] veredicto", f)
        for f in t["metricas"]:
            print("[dia_inicio]", tuple(round(x, 4) if isinstance(x, float) else x for x in f))
    finally:
        con.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="pipeline.dia_inicio")
    ap.add_argument("--cuenca", help="'colorado' para la cuenca DJ; sin argumento, Vaca Muerta")
    a = ap.parse_args()
    if a.cuenca not in (None, COLORADO.id):
        raise SystemExit(f"dia_inicio no tiene adaptacion escrita para la cuenca {a.cuenca!r}")
    main(colorado=a.cuenca == COLORADO.id)
