"""Validacion por inyeccion: si el estimador sin cambios recupera efectos de tamano conocido plantados en datos reales.

Se corre despues de pipeline.build:  uv run python -m pipeline.inyeccion

REGLA FIJADA ANTES DE CORRER (2026-11-15, antes de calcular ninguna cifra; no se cambia despues de ver resultados).
Fuente: pivote P1 de la fase 4 (validacion por inyeccion).

Pregunta: el resultado principal dice que un mes despues de la fractura de un hijo los padres a menos de 1 km rinden unos 19 a
23 puntos menos que los controles. Si en datos reales, en una fecha donde la brecha real es cercana a cero, se planta un efecto
de tamano conocido, el estimador sin cambios (pipeline.placebo, pipeline.descomposicion, pipeline.sincronia) lo devuelve con
que sesgo y con que dispersion? Esto convierte "se midio 19 a 23" en "el metodo recupera X dentro de Y".

Mundo nulo: las fechas de fractura de todos los hijos corridas -12 meses (la fecha falsa es un ano anterior; se conservan los
pares padre e hijo y solo cuentan los pares ya elegibles con la fecha real, igual que `pipeline.placebo.tabla_fechas`). La
brecha real ahi es cercana a cero, y es el mundo del que sale la tasa de falsos positivos. Se usa solo d = -12: los corrimientos
hacia atras son los placebos limpios de la pagina de falsacion.

Mundos simulados: R = 50 por celda (si R por celdas pasa de 8 minutos se baja a 30 y la pagina lo dice). Cada mundo sortea, con
semilla fija SEMILLA_MUNDO + w (w = 0 a R - 1, la misma en todas las celdas, asi que S4 se compara con S5 sobre los mismos
sorteos), el 70% de los pads hijo sin reposicion (todos sus eventos, cercanos y control); el efecto se planta en los eventos
cercanos de esos pads. El IC de cada brecha es el bootstrap por pads hijo de pipeline.placebo con 200 repeticiones (REPS_MUNDO) y
una semilla que depende del mundo. La dispersion entre mundos es dispersion de muestreo de pads sobre datos reales.

Estimadores (sin cambios; se importan y se les da las entradas modificadas):
  * Brecha del mes 1: pipeline.placebo.brecha_ic del indice de petroleo (caudal por dia sobre la media de los meses -3 a -1),
    mediana de cercanos (menos de 1 km) menos mediana de controles (2 a 5 km), en puntos de indice.
  * Descomposicion: pipeline.descomposicion._logs y _brecha_logs_ic, variante con cerrados, base de los meses -6 a -4; parte de
    los dias = brecha de los dias sobre la del volumen, parte del caudal por dia = la del caudal sobre la del volumen.
  * Pendiente de sincronia: pipeline.sincronia.pendiente_ic del indice del mes 0 sobre f0 (base -6 a -4, indice acotado a 0 a 2),
    con IC por pads hijo. f0 es la fraccion del mes 0 posterior al inicio de la fractura del hijo en la fecha falsa
    (mismo dia del mes, dias reales del mes falso).

Efectos plantados (solo en los padres cercanos de los pads sorteados; los controles no se tocan; una fecha plantada por evento):
  * S1 cierre del mes: el mes 1 con cero dias producidos y cero petroleo (el caudal por dia efectivo queda sin dato). Se planta
    en una parte p de los cercanos elegidos al azar en cada mundo; p se fija una vez, antes de plantar, con la aritmetica de
    cuantiles del indice del mes 1 del mundo nulo completo, para que la brecha esperada sea -50 puntos (tamano 100 = se pierde el
    100% de los dias del mes). p se publica.
  * S2 caida de caudal: el caudal por dia del mes 1 baja 10, 20 y 30% en todos los cercanos; los dias no cambian.
  * S3 caida dentro del mes: el caudal baja 20, 40 y 60% desde el dia de inicio de la fractura del hijo en el mes 0 (un inicio el
    dia 15 es f0 de 0,5). El indice del mes 0 de un cercano queda multiplicado por 1 - s * f0 (s = 0,2, 0,4 o 0,6), asi que la
    pendiente plantada es -s en indice por unidad de f0, o -10 * s puntos por cada 0,1 de f0 (-4,0 con el 40%). No se planta otro mes.
  * S4 brecha previa de nivel: los cercanos quedan multiplicados por 0,97, 0,95 o 0,92 en todos los meses desde el mes -3 (dentro
    de la base original de los meses -3 a -1) hasta el mes 3, sin efecto de fractura en k >= 0. Una brecha de nivel anterior a la
    fractura que sigue despues: con la base de los meses -3 a -1 se anula (plantado 0), con la base limpia de los meses -6 a -4
    se ve como -3, -5 o -8 en los meses -3 a -1 y sigue en el mes 1 (plantado -3, -5, -8).
  * S5 nulo: no se planta nada.
Todo efecto se planta sobre las matrices del estimador (petroleo por dia, dias efectivos y petroleo por dia efectivo, de forma
consistente); no se edita ningun estimador.

Reglas fijadas (cada una es una hipotesis del libro: `inyeccion_r1`, `inyeccion_r2`, `inyeccion_r3`, `inyeccion_r4a`, `inyeccion_r4b`):
  R1 recuperacion de la cifra principal: en S2 al 20%, la media entre mundos de la brecha del mes 1 (puntos de indice, base -3 a
     -1) esta entre -25 y -15 (a menos de 5 puntos de -20). Si no, la pagina dice "el metodo no recupera el efecto en el rango
     preregistrado" y la cifra principal lleva una advertencia en el README y en el caso de estudio.
  R2 reparto: en S1 la media entre mundos de la parte de los dias del log de la brecha del mes 1 es al menos 80%; en S2 la parte
     del caudal por dia es al menos 80%. Si alguna falla, el reparto 53% y 47% se rotula "no identificada por el metodo" donde
     aparezca (README, caso de estudio, pagina de descomposicion).
  R3 tiempo: en S3 al 40%, la pendiente recuperada del mes 0 tiene el signo plantado (negativo) con IC que excluye cero en al
     menos 80% de los mundos. Si no, el veredicto de sincronia pasa a "no firme".
  R4a falsos positivos: en S5, el IC de la brecha del mes 1 excluye cero en como maximo 10% de los mundos.
  R4b lectura de S4: en S4 al 5%, restando el mundo nulo de los mismos sorteos (S4 menos S5, porque el nulo tiene su propia brecha
     residual), la media de la pretendencia con base limpia (meses -3 a -1) queda a menos de 2 puntos de -5 y la brecha neta del
     mes 1 (brecha del mes 1 con base limpia menos esa pretendencia) a menos de 2 puntos de 0: la brecha de nivel se lee como
     previa a la fractura y no como efecto de ella. Se publica cuanto se filtra a la brecha del mes 1 con las dos bases.
  La fraccion de mundos con IC que excluye cero cuenta, en los efectos plantados, el signo plantado; en S4 y S5, cualquier signo.
  Se publican todas las celdas calculadas (tres tamanos por escenario), no solo las de las reglas.

Nota posterior a ver resultados (2026-11-15, revision; no se cambia ningun umbral ni operador):
  * R2 y R3 dicen "al menos 80%" y R4a dice "como maximo 10%", pero los operadores codificados son estrictos (> 0,80 y < 0,10),
    igual que en el libro. Con R4a la diferencia importa: 3 de 30 mundos (10%) cumple el texto y no el operador. La pagina informa
    las dos lecturas.
  * Los tamanos son nominales (fraccion del indice de cada cercano). En puntos del indice el efecto plantado es el tamano por el
    indice de los cercanos (mediana de 0,86 en el mes 1, media de 0,83 en el mes 0): ver `plantado_en_puntos`.

Que NO prueba:
  * Los efectos plantados son simples, multiplicativos e independientes de la geologia, la distancia, el tiempo y el operador;
    un efecto real no es asi. Recuperar un efecto plantado dice algo del estimador, no de los pozos.
  * El mundo nulo conserva una brecha residual (los cercanos del mundo falso no son identicos a los controles) y los pozos reales
    traen su propio ruido y sus propios cierres; el sorteo de pads es muestreo, no una poblacion nueva.
  * Un padre puede ser cercano en un evento y control en otro: un efecto plantado puede tocar un control por solapamiento de
    ventanas, y un cercano en dos eventos cercanos recibe el efecto dos veces (se informa, no se corrige).
  * Pasar esta prueba no demuestra que la brecha real sea una causa.
"""
from __future__ import annotations

import ast
import calendar
import math
from datetime import date

import duckdb
import numpy as np

from pipeline import descomposicion as de
from pipeline import placebo
from pipeline import sincronia as sc
from pipeline.costo import _escribir
from pipeline.ingest import DATA, ROOT
from pipeline.placebo import BASE_LIMPIA, BASE_ORIGINAL, PAD, SEMILLA_PLACEBO, _g, brecha_ic

SEMILLA_MUNDO = SEMILLA_PLACEBO + 7000
MUNDOS_PLAN = 50                 # mundos por celda de la regla fijada
TOPE_MINUTOS = 8                 # si MUNDOS_PLAN por celdas pasa de este tiempo, se baja a MUNDOS
MUNDOS = 30                      # la corrida con MUNDOS_PLAN tardo 9 minutos: se bajo a 30 como decia la regla
REPS_MUNDO = 200                 # repeticiones del bootstrap por pads hijo dentro de cada mundo
FRACCION_PADS = 0.7              # parte de los pads hijo que entra en cada mundo
DESPLAZAMIENTO = -12             # meses en que se corre la fecha de fractura de cada hijo (mundo nulo)
K_PRETEN = (-3, -2, -1)
OBJETIVO_CIERRE = -0.50          # brecha esperada del mes 1 en S1, en indice
ESCENARIOS = {                   # escenario: tamanos (S1 en % de dias perdidos, S2 y S3 en % de caida, S4 en % de nivel)
    "S1": (100,), "S2": (10, 20, 30), "S3": (20, 40, 60), "S4": (3, 5, 8), "S5": (0,),
}
NOMBRES = {"S1": "cierre del mes 1", "S2": "caída de caudal en el mes 1", "S3": "caída desde el inicio de la fractura (mes 0)",
           "S4": "brecha previa de nivel", "S5": "nulo (nada plantado)"}

COLS_INY = [("escenario", "varchar"), ("tamano", "integer"), ("medida", "varchar"), ("unidad", "varchar"), ("mundos", "integer"),
            ("plantado", "double"), ("recuperado_media", "double"), ("recuperado_p05", "double"), ("recuperado_p95", "double"),
            ("ic_excluye_cero_frac", "double"), ("parte_dias", "double"), ("parte_tasa", "double"),
            ("plantado_puntos", "double"), ("recuperado_neto", "double"), ("neto_p05", "double"), ("neto_p95", "double")]
CORRIDA_50 = ROOT / "docs" / "inyeccion_50_mundos.txt"   # salida guardada de la corrida de 50 mundos por celda (fuera del tope)


# ------------------------------------------------------------------ datos y mundo nulo

def _correr_fecha(d, meses: int) -> date:
    """La misma fecha `meses` meses despues (o antes si es negativo); el dia se acota al ultimo dia del mes de llegada."""
    total = d.year * 12 + d.month - 1 + meses
    y, m = divmod(total, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def cargar(con, desplazamiento: int = DESPLAZAMIENTO) -> dict:
    """Datos del estimador (placebo, descomposicion) mas la fecha de fractura corrida: mes, f0 y ano de cada hijo en la fecha falsa."""
    D = de.cargar_ext(con, placebo.cargar(con))
    ini = dict(con.execute("select h.hijo, min(f.fecha_inicio) from int_frac_hijo h join stg_fractura f on f.pozo_id = h.hijo "
                           "where f.fecha_inicio is not null and date_trunc('month', f.fecha_inicio) = h.mes_frac "
                           "group by h.hijo").fetchall())
    falsas = [_correr_fecha(ini[int(h)], desplazamiento) for h in D["hijo_id"]]
    D["mes_falso"] = D["hijo_mes"] + desplazamiento
    D["f0_falso"] = sc.fraccion_mes0(falsas)
    D["anio_falso"] = np.array([d.year for d in falsas])
    return D


def marco_falso(D: dict, ks, base) -> dict:
    """Eventos del mundo nulo: los de pipeline.placebo.marco con la fecha corrida y solo los pares elegibles con la fecha real."""
    return placebo.marco(D, D["mes_falso"], ks=ks, base=base, solo_reales=True)


# ------------------------------------------------------------------ plantar

def _copias(D: dict) -> dict:
    out = dict(D)
    for nombre in ("tasa", "tef", "tasa_ef"):
        out[nombre] = D[nombre].copy()
    return out


def _mult(D: dict, nombres, padre: np.ndarray, mes: np.ndarray, k: int, factor) -> None:
    """Multiplica por `factor` el mes k de cada evento (np.multiply.at: dos eventos en la misma celda se componen)."""
    for n in nombres:
        np.multiply.at(D[n], (padre, mes + k + PAD), factor)


def plantar(D: dict, ev: dict, sel: np.ndarray, escenario: str, tam: int) -> dict:
    """Copia de D con el efecto plantado en los eventos `sel` (mascara sobre los eventos `ev`)."""
    W = _copias(D)
    padre, mes = ev["padre"][sel], ev["mes"][sel]
    s = tam / 100.0
    if escenario == "S1":    # cierre: cero petroleo y cero dias; el caudal por dia efectivo no existe
        _mult(W, ("tasa", "tef"), padre, mes, 1, 0.0)
        W["tasa_ef"][padre, mes + 1 + PAD] = np.nan
    elif escenario == "S2":
        _mult(W, ("tasa", "tasa_ef"), padre, mes, 1, 1.0 - s)
    elif escenario == "S3":
        f0 = D["f0_falso"][ev["hijo"][sel]]
        _mult(W, ("tasa", "tasa_ef"), padre, mes, 0, 1.0 - s * f0)
    elif escenario == "S4":
        for k in range(-3, 4):
            _mult(W, ("tasa", "tasa_ef"), padre, mes, k, 1.0 - s)
    elif escenario != "S5":
        raise ValueError(escenario)
    return W


def participacion_cierre(idx_cerca: np.ndarray, idx_ctrl: np.ndarray, objetivo: float = OBJETIVO_CIERRE) -> float:
    """Parte p de los cercanos cerrados para que la mediana de la mezcla quede `objetivo` por debajo de la de los controles.

    Con p de los cercanos en indice 0, la mediana de la mezcla es el cuantil (0,5 - p) / (1 - p) del indice sin cerrar:
    se busca p tal que ese cuantil sea la mediana de los controles mas `objetivo` (aritmetica sobre el mundo nulo, sin plantar).
    """
    c = idx_cerca[~np.isnan(idx_cerca)]
    meta = float(np.median(idx_ctrl[~np.isnan(idx_ctrl)])) + objetivo
    q = float((c < meta).mean())
    if q >= 0.5:
        raise ValueError("el objetivo ya esta dentro de la distribucion sin cerrar: no hace falta cerrar a nadie")
    return (0.5 - q) / (1.0 - q)


# ------------------------------------------------------------------ un mundo

def _recorte(m: dict, mask: np.ndarray) -> dict:
    """El marco `m` reducido a los eventos de la mascara (solo los campos por evento que usan los estimadores)."""
    out = {k: m[k][mask] for k in ("padre", "hijo", "km", "mes", "banda", "clave", "area")}
    out["idx"] = {k: v[mask] for k, v in m["idx"].items()}
    return out


def _eventos_pendiente(D: dict, m: dict, k: int) -> dict:
    """Los eventos de pipeline.sincronia.eventos, con la fecha falsa: indice acotado, f0 falso, area y ano falso del hijo."""
    y = np.clip(m["idx"][k], *sc.CLIP_INDICE)
    ok = ~np.isnan(y) & (m["banda"] != 1)
    return {"y": y[ok], "banda": m["banda"][ok], "f0": D["f0_falso"][m["hijo"]][ok], "area": m["area"][ok],
            "anio": D["anio_falso"][m["hijo"]][ok], "clave": m["clave"][ok]}


def _pendiente_puntual(e: dict) -> float:
    return sc.pendiente(sc.diseno(e), e["y"])


def mundo(D: dict, ev: dict, w: int, escenario: str, tam: int, p_cierre: float, completo: bool,
          reps: int = REPS_MUNDO, fraccion_pads: float = FRACCION_PADS) -> dict:
    """Una celda en un mundo: sortea pads, planta, corre los estimadores sin cambios y devuelve las medidas en puntos.

    `completo` pide tambien la base limpia, la pendiente con IC y el mes -1 (S3, S4 y S5); sin eso solo la brecha del mes 1
    (con IC) y, en S1 y S2, la descomposicion. `ev` son los eventos del mundo nulo sin plantar (para elegir a quien plantar).
    """
    pads = np.unique(ev["clave"])
    elegidos = np.random.default_rng([SEMILLA_MUNDO, w, 0]).choice(pads, size=int(round(fraccion_pads * len(pads))), replace=False)
    cerca = np.flatnonzero((ev["banda"] == 0) & np.isin(ev["clave"], elegidos))
    if escenario == "S1":
        cerca = np.random.default_rng([SEMILLA_MUNDO, w, 1]).choice(cerca, size=int(round(p_cierre * len(cerca))), replace=False)
    sel = np.zeros(len(ev["clave"]), dtype=bool)
    sel[cerca] = True
    W = D if escenario == "S5" else plantar(D, ev, sel, escenario, tam)
    sem = SEMILLA_MUNDO + 100_000 + w
    out: dict = {}

    m = marco_falso(W, (1,), BASE_ORIGINAL)
    m = _recorte(m, np.isin(m["clave"], elegidos))
    g = brecha_ic(m["idx"][1], m["banda"], m["clave"], reps, sem)
    out["brecha_mes1"] = (100 * g["brecha"], 100 * g["ic_bajo"], 100 * g["ic_alto"])

    if escenario in ("S1", "S2"):
        ml = marco_falso(W, (1,), BASE_LIMPIA)
        ld, lr = de._logs(W, ml, 1, True)
        mk = np.isin(ml["clave"], elegidos)
        r = de._brecha_logs_ic(ld[mk], lr[mk], ml["banda"][mk], ml["clave"][mk], 1, sem)
        out["parte_dias"], out["parte_tasa"] = r["parte_dias"], r["parte_tasa"]
    if completo:
        ml = marco_falso(W, (-3, -2, -1, 0, 1), BASE_LIMPIA)
        ml = _recorte(ml, np.isin(ml["clave"], elegidos))
        gk = {k: brecha_ic(ml["idx"][k], ml["banda"], ml["clave"], 1, sem)["brecha"] for k in (-3, -2, -1, 1)}
        preten = float(np.mean([gk[k] for k in K_PRETEN]))
        out["preten"] = 100 * preten
        out["brecha_mes1_base_limpia"] = 100 * gk[1]
        out["brecha_mes1_neta"] = 100 * (gk[1] - preten)
        if escenario in ("S3", "S5"):
            p0 = sc.pendiente_ic(_eventos_pendiente(W, ml, 0), 0, reps)
            out["pendiente_mes0"] = (10 * p0["pendiente"], 10 * p0["ic_bajo"], 10 * p0["ic_alto"])
            out["pendiente_mes_m1"] = 10 * _pendiente_puntual(_eventos_pendiente(W, ml, -1))
    return out


# ------------------------------------------------------------------ todas las celdas

MEDIDAS_PAREADAS = ("brecha_mes1", "preten", "brecha_mes1_base_limpia", "brecha_mes1_neta")


def _excluye(g: tuple, plantado: float) -> bool:
    """El IC (g = (valor, bajo, alto)) excluye cero; con signo plantado distinto de cero, solo del lado plantado."""
    _, lo, hi = g
    if np.isnan(lo) or np.isnan(hi):
        return False
    if plantado < 0:
        return bool(hi < 0)
    if plantado > 0:
        return bool(lo > 0)
    return bool(lo > 0 or hi < 0)


def _fila(esc: str, tam: int, medida: str, unidad: str, plantado: float | None, valores: list[float], ic: list[bool] | None = None,
          parte_dias: float | None = None, parte_tasa: float | None = None, plantado_puntos: float | None = None,
          pareados: list[float] | None = None) -> tuple:
    """Una fila del mart. `plantado_puntos` es el efecto plantado en puntos del indice (por defecto el nominal) y `pareados` las
    diferencias con el mundo nulo de los mismos sorteos (media y percentiles 5 y 95; por defecto no hay)."""
    q = None if pareados is None else np.array(pareados, dtype=float)
    v = np.array(valores, dtype=float)
    return (esc, int(tam), medida, unidad, int(len(v)), plantado, float(v.mean()), float(np.percentile(v, 5)), float(np.percentile(v, 95)),
            None if ic is None else float(np.mean(ic)), parte_dias, parte_tasa,
            plantado if plantado_puntos is None else float(plantado_puntos), None if q is None else float(q.mean()),
            None if q is None else float(np.percentile(q, 5)), None if q is None else float(np.percentile(q, 95)))


def plantado_en_puntos(D: dict, ev: dict, escenario: str, tam: int) -> dict[str, float]:
    """El efecto plantado solo, en las unidades del estimador (puntos del indice), por medida, sobre el mundo nulo completo.

    Se planta en todos los cercanos, sin sorteo de pads, y se mide la diferencia entre el estimador con el efecto y sin el, asi que
    no hay ruido. S2: brecha del mes 1. S3: pendiente del mes 0 con el diseno del estimador, del efecto solo (-tam por f0 por el
    indice del mes 0 de cada cercano, en puntos por 0,1 de f0). S4: la pretendencia, el mes 1 con base limpia, el mes 1 neto y el
    mes 1 con la base original."""
    cerca = ev["banda"] == 0
    brecha = lambda m, k: 100 * brecha_ic(m["idx"][k], m["banda"], m["clave"], 1, SEMILLA_MUNDO)["brecha"]  # noqa: E731
    if escenario == "S2":
        W = plantar(D, ev, cerca, escenario, tam)
        return {"brecha_mes1": brecha(marco_falso(W, (1,), BASE_ORIGINAL), 1) - brecha(ev, 1)}
    if escenario == "S3":
        ml = marco_falso(D, (-3, -2, -1, 0, 1), BASE_LIMPIA)
        e = _eventos_pendiente(D, ml, 0)
        efecto = -(tam / 100.0) * e["f0"] * e["y"] * (e["banda"] == 0)
        return {"pendiente_mes0": 10 * sc.pendiente(sc.diseno(e), efecto)}
    if escenario == "S4":
        W = plantar(D, ev, cerca, escenario, tam)
        ks = (-3, -2, -1, 0, 1)
        m0, m1 = marco_falso(D, ks, BASE_LIMPIA), marco_falso(W, ks, BASE_LIMPIA)
        pre = float(np.mean([brecha(m1, k) - brecha(m0, k) for k in K_PRETEN]))
        mes1 = brecha(m1, 1) - brecha(m0, 1)
        return {"preten": pre, "brecha_mes1_base_limpia": mes1, "brecha_mes1_neta": mes1 - pre,
                "brecha_mes1": brecha(marco_falso(W, (1,), BASE_ORIGINAL), 1) - brecha(ev, 1)}
    raise ValueError(escenario)


def intervalo_exacto(k: int, n: int, nivel: float = 0.95) -> tuple[float, float]:
    """Intervalo exacto (Clopper y Pearson) de una proporcion k de n, por biseccion sobre la binomial."""
    def cola_baja(p: float) -> float:      # P(X <= k)
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))

    def cola_alta(p: float) -> float:      # P(X >= k)
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))

    def biseccion(f, objetivo: float, creciente: bool) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if (f(mid) < objetivo) == creciente:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    a = (1 - nivel) / 2
    bajo = 0.0 if k == 0 else biseccion(cola_alta, a, True)
    alto = 1.0 if k == n else biseccion(cola_baja, a, False)
    return bajo, alto


def calcular(D: dict, mundos: int = MUNDOS, reps: int = REPS_MUNDO, ev: dict | None = None) -> tuple[list[tuple], float]:
    """Filas de mart_inyeccion (todas las celdas, `mundos` mundos cada una) y la parte p de cercanos cerrados en S1."""
    if ev is None:
        ev = marco_falso(D, (1,), BASE_ORIGINAL)
    p = participacion_cierre(ev["idx"][1][ev["banda"] == 0], ev["idx"][1][ev["banda"] == 2])
    res: dict = {}
    for esc, tams in ESCENARIOS.items():
        for tam in tams:
            res[(esc, tam)] = [mundo(D, ev, w, esc, tam, p, esc in ("S3", "S4", "S5"), reps) for w in range(mundos)]
    filas = [("S1", 100, "participacion_cierre", "proporcion", None, 1, p, p, p, None, None, None, None, None, None, None)]
    nulo = res[("S5", 0)]
    for (esc, tam), rs in res.items():
        if esc in ("S1", "S2"):
            plant = -50.0 if esc == "S1" else -float(tam)
            pts = plant if esc == "S1" else plantado_en_puntos(D, ev, esc, tam)["brecha_mes1"]
            par = [r["brecha_mes1"][0] - n["brecha_mes1"][0] for r, n in zip(rs, nulo)]
            filas.append(_fila(esc, tam, "brecha_mes1", "puntos", plant, [r["brecha_mes1"][0] for r in rs],
                               [_excluye(r["brecha_mes1"], plant) for r in rs],
                               float(np.mean([r["parte_dias"] for r in rs])), float(np.mean([r["parte_tasa"] for r in rs])), pts, par))
        elif esc == "S3":
            par = [r["pendiente_mes0"][0] - n["pendiente_mes0"][0] for r, n in zip(rs, nulo)]
            filas.append(_fila(esc, tam, "pendiente_mes0", "puntos por 0,1 de f0", -tam / 10.0, [r["pendiente_mes0"][0] for r in rs],
                               [_excluye(r["pendiente_mes0"], -1.0) for r in rs], None, None,
                               plantado_en_puntos(D, ev, esc, tam)["pendiente_mes0"], par))
            filas.append(_fila(esc, tam, "pendiente_mes_m1", "puntos por 0,1 de f0", 0.0, [r["pendiente_mes_m1"] for r in rs]))
        elif esc == "S4":
            plant = {"brecha_mes1": 0.0, "preten": -float(tam), "brecha_mes1_base_limpia": -float(tam), "brecha_mes1_neta": 0.0}
            pts = plantado_en_puntos(D, ev, esc, tam)
            for med in MEDIDAS_PAREADAS:
                if med == "brecha_mes1":
                    vals = [r["brecha_mes1"][0] - n["brecha_mes1"][0] for r, n in zip(rs, nulo)]
                    ic = [_excluye(r["brecha_mes1"], 0.0) for r in rs]
                else:
                    vals = [r[med] - n[med] for r, n in zip(rs, nulo)]
                    ic = None
                filas.append(_fila(esc, tam, med, "puntos", plant[med], vals, ic, plantado_puntos=pts[med], pareados=vals))
        else:  # S5
            filas.append(_fila(esc, tam, "brecha_mes1", "puntos", 0.0, [r["brecha_mes1"][0] for r in rs],
                               [_excluye(r["brecha_mes1"], 0.0) for r in rs]))
            for med in ("preten", "brecha_mes1_base_limpia", "brecha_mes1_neta"):
                filas.append(_fila(esc, tam, med, "puntos", 0.0, [r[med] for r in rs]))
            filas.append(_fila(esc, tam, "pendiente_mes0", "puntos por 0,1 de f0", 0.0, [r["pendiente_mes0"][0] for r in rs],
                               [_excluye(r["pendiente_mes0"], 0.0) for r in rs]))
            filas.append(_fila(esc, tam, "pendiente_mes_m1", "puntos por 0,1 de f0", 0.0, [r["pendiente_mes_m1"] for r in rs]))
    return filas, p


# ------------------------------------------------------------------ pagina

UMBRAL_R1 = 5.0       # puntos de distancia entre lo recuperado y lo plantado (-20)
UMBRAL_R2 = 0.80
UMBRAL_R3 = 0.80
UMBRAL_R4A = 0.10
UMBRAL_R4B = 2.0


def _fila_mart(con, esc: str, tam: int, medida: str) -> dict:
    cur = con.execute("select * from mart_inyeccion where escenario = ? and tamano = ? and medida = ?", [esc, tam, medida])
    cols = [d[0] for d in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else {}


def veredictos(con) -> dict:
    """Los cinco veredictos con la regla fijada en el docstring: True si se cumple."""
    r1 = _fila_mart(con, "S2", 20, "brecha_mes1")
    s1 = _fila_mart(con, "S1", 100, "brecha_mes1")
    r3 = _fila_mart(con, "S3", 40, "pendiente_mes0")
    r4a = _fila_mart(con, "S5", 0, "brecha_mes1")
    pre = _fila_mart(con, "S4", 5, "preten")
    neta = _fila_mart(con, "S4", 5, "brecha_mes1_neta")
    return {
        "r1": abs(r1["recuperado_media"] - r1["plantado"]) < UMBRAL_R1,
        "r2": min(s1["parte_dias"], r1["parte_tasa"]) > UMBRAL_R2,
        "r3": r3["ic_excluye_cero_frac"] > UMBRAL_R3,
        "r4a": r4a["ic_excluye_cero_frac"] < UMBRAL_R4A,
        "r4b": max(abs(pre["recuperado_media"] - pre["plantado"]), abs(neta["recuperado_media"] - neta["plantado"])) < UMBRAL_R4B,
    }


def _pc(x) -> str:
    return "n/d" if x is None else f"{_g(100 * x, 0)}%"


def _rango(f: dict) -> str:
    return f"{_g(f['recuperado_p05'], 1)} a {_g(f['recuperado_p95'], 1)}"


def corrida_50() -> dict:
    """La salida guardada de la corrida de 50 mundos por celda: {(escenario, tamano, medida): fila del mart} (vacio si no esta)."""
    out = {}
    if CORRIDA_50.exists():
        for linea in CORRIDA_50.read_text(encoding="utf-8").splitlines():
            if linea.startswith("[inyeccion] ("):
                r = ast.literal_eval(linea[len("[inyeccion] "):])
                out[(r[0], r[1], r[2])] = dict(zip([c for c, _ in COLS_INY], r))
    return out


def pagina_inyeccion(con) -> str:
    v = veredictos(con)
    f = lambda e, t, m: _fila_mart(con, e, t, m)  # noqa: E731
    s2, s1, s3, s5 = f("S2", 20, "brecha_mes1"), f("S1", 100, "brecha_mes1"), f("S3", 40, "pendiente_mes0"), f("S5", 0, "brecha_mes1")
    s5p = f("S5", 0, "pendiente_mes0")
    pre, neta = f("S4", 5, "preten"), f("S4", 5, "brecha_mes1_neta")
    base_limpia, principal_s4 = f("S4", 5, "brecha_mes1_base_limpia"), f("S4", 5, "brecha_mes1")
    p = f("S1", 100, "participacion_cierre")["recuperado_media"]
    n = s2["mundos"]
    ok = lambda b: "se cumple" if b else "no se cumple"  # noqa: E731
    k_fp = round(s5["ic_excluye_cero_frac"] * n)
    lo_fp, hi_fp = intervalo_exacto(k_fp, int(n))
    texto_r4a = s5["ic_excluye_cero_frac"] <= UMBRAL_R4A + 1e-9
    if v["r4a"]:
        r4a_titulo, r4a_cola = "se cumple", ""
    elif texto_r4a:
        r4a_titulo = "en el borde exacto"
        r4a_cola = (f" Pero el operador del libro es estricto (< {_g(UMBRAL_R4A, 2)}): con "
                    f"{_g(k_fp)} de {_g(n)} mundos ({_pc(s5['ic_excluye_cero_frac'])}) cumple el texto y no el operador, y el libro la marca "
                    "debilitada. Se informa en el borde: con los mundos que hay, uno más o uno menos cambia el veredicto del operador.")
    else:
        r4a_titulo = "no se cumple"
        r4a_cola = " No se cumple ni con el texto (como máximo 10%) ni con el operador estricto del libro."
    c50 = corrida_50()
    ok50 = bool(c50)
    atenuacion = s3["recuperado_neto"] / s3["plantado_puntos"] if s3["plantado_puntos"] else float("nan")
    cerca = abs(atenuacion - 1) <= 0.2
    L = ["# Validación por inyección", "",
         "Página generada por `pipeline/inyeccion.py`. Pregunta si el estimador sin cambios recupera efectos de tamaño conocido "
         "plantados en datos reales, en fechas falsas donde la brecha real es cercana a cero. Convierte \"se midió una brecha\" en "
         "\"el método recupera tanto, con esta dispersión\". Complementa [Interferencia entre fracturas](interferencia.md), la "
         "[falsación](placebo.md), la [descomposición](descomposicion.md) y la [sincronía](sincronia.md); las reglas se fijaron antes "
         "de correr y están en el libro de hallazgos como `inyeccion_r1`, `inyeccion_r2`, `inyeccion_r3`, `inyeccion_r4a` e "
         "`inyeccion_r4b`.", "",
         "## Resumen", "",
         f"- **R1, cifra principal: {ok(v['r1'])}.** Con una caída plantada de 20% del caudal del mes 1, la brecha recuperada del mes 1 "
         f"es {_g(s2['recuperado_media'], 1)} puntos en media de {_g(n)} mundos (rango del 5% al 95%: {_rango(s2)}); la regla pedía "
         "entre -25 y -15." + ("" if v["r1"] else " El método no recupera el efecto en el rango preregistrado.")
         + f" En puntos del índice, una caída de 20% del caudal es unos {_g(s2['plantado_puntos'], 1)} puntos y no -20, porque el índice "
         f"de los cercanos es menor que 1; lo recuperado ({_g(s2['recuperado_media'], 1)}) suma eso y la brecha residual del mundo nulo "
         f"({_g(s5['recuperado_media'], 1)}). Descontado el nulo, el estimador devuelve {_g(s2['recuperado_neto'], 1)} puntos, lo plantado.",
         f"- **R2, reparto entre días y caudal: {ok(v['r2'])}.** Con un cierre plantado la parte de los días del log de la brecha es "
         f"{_pc(s1['parte_dias'])}; con una caída de caudal plantada la parte del caudal por día es {_pc(s2['parte_tasa'])}. La regla "
         "pedía al menos 80% en los dos." + ("" if v["r2"] else " El reparto entre días y caudal queda como no identificada por el método.")
         + " Las partes son repartos del log de la brecha y pasan de 100% cuando la otra parte tiene signo contrario (el mundo nulo trae "
         "su propia composición).",
         f"- **R3, tiempo dentro del mes: {ok(v['r3'])}.** Con una caída plantada de 40% desde el inicio de la fractura la pendiente del "
         f"mes 0 recuperada es {_g(s3['recuperado_media'], 1)} puntos por cada 0,1 de f0 (plantado {_g(s3['plantado'], 1)} nominal), y su IC "
         f"excluye cero con el signo plantado en {_pc(s3['ic_excluye_cero_frac'])} de los mundos; la regla pedía al menos 80%."
         + ("" if v["r3"] else " El veredicto de sincronía pasa a no firme.")
         + f" En puntos del índice lo plantado es {_g(s3['plantado_puntos'], 1)} y, descontada la pendiente del mundo nulo "
         f"({_g(s5p['recuperado_media'], 1)}), lo recuperado es {_g(s3['recuperado_neto'], 1)}.",
         f"- **R4a, falsos positivos: {r4a_titulo}.** Sin nada plantado el IC de la brecha del mes 1 excluye cero en "
         f"{_pc(s5['ic_excluye_cero_frac'])} de los mundos, {_g(k_fp)} de {_g(n)}; la regla del libro dice como máximo "
         f"{_g(100 * UMBRAL_R4A)}%." + r4a_cola
         + f" La brecha media del mundo nulo es {_g(s5['recuperado_media'], 1)} puntos."
         f" La tasa es la del IC por pads, no la del IC por bloques de 5 km que informa el caso, y con {_g(n)} mundos {_g(k_fp)} de "
         f"{_g(n)} es compatible con tasas de {_g(100 * lo_fp, 0)}% a {_g(100 * hi_fp, 0)}%.",
         f"- **R4b, brecha previa de nivel: {ok(v['r4b'])}.** Con una brecha de 5% plantada desde el mes -3 y sin efecto de fractura, "
         f"restando el mundo nulo de los mismos sorteos, la pretendencia recuperada es {_g(pre['recuperado_media'], 1)} puntos "
         f"(plantado {_g(pre['plantado'], 1)}) y la brecha neta del mes 1 es {_g(neta['recuperado_media'], 1)} puntos (plantado 0,0). "
         f"Se filtra al mes 1 de la base limpia como {_g(base_limpia['recuperado_media'], 1)} puntos y al de la base de los meses -3 "
         f"a -1 como {_g(principal_s4['recuperado_media'], 1)} puntos.", "",
         "Se publican todas las celdas calculadas, no solo las de las reglas. Recuperar un efecto plantado dice algo del estimador, no de "
         "los pozos.", "",
         "## Cómo se hizo", "",
         f"- Mundo nulo: la fecha de fractura de cada hijo corrida {_g(-DESPLAZAMIENTO)} meses hacia atrás, con los pares padre e hijo "
         "de la página de falsación y solo los pares ya elegibles con la fecha real. La brecha real ahí es cercana a cero.",
         f"- Mundos: {_g(n)} por celda. Cada mundo sortea el {_g(100 * FRACCION_PADS)}% de los pads hijo con una semilla fija y planta "
         f"el efecto en los padres cercanos de esos pads; los controles no se tocan. El IC es el bootstrap por pads hijo de la página "
         f"de falsación con {_g(REPS_MUNDO)} repeticiones. La dispersión entre mundos es muestreo de pads sobre datos reales.",
         "- Estimadores sin cambios: la brecha del mes 1 de `pipeline/placebo.py`, la descomposición en logaritmos de "
         "`pipeline/descomposicion.py` y la pendiente de `pipeline/sincronia.py`; solo se les dan las matrices con el efecto plantado.",
         f"- S1 cierra el mes 1 (cero días y cero petróleo) en el {_g(100 * p, 1)}% de los cercanos de cada mundo, la parte que da una "
         f"brecha esperada de {_g(100 * OBJETIVO_CIERRE, 0)} puntos en el mundo nulo completo. S2 baja el caudal por día del mes 1 "
         "10, 20 y 30%. S3 lo baja 20, 40 y 60% desde el día de inicio de la fractura dentro del mes 0, de modo que la pendiente "
         "nominal es el tamaño sobre 10 en puntos por cada 0,1 de f0. S4 deja a los cercanos 3, 5 y 8% más abajo desde el mes -3 "
         "(la base de los meses -3 a -1 la incluye) sin efecto de fractura. S5 no planta nada.",
         "- Los tamaños son nominales: un porcentaje de lo que produce cada cercano. En puntos del índice el efecto plantado es ese "
         "porcentaje por el índice de los cercanos, que es menor que 1. La columna Plantado en puntos lo mide sobre el mundo nulo "
         "completo, con el estimador del escenario aplicado al efecto plantado solo, sin ruido ni sorteo de pads; Recuperado menos "
         "nulo resta la media del mundo nulo de los mismos sorteos.", "",
         "## Brecha del mes 1", "",
         "Puntos del índice (base de los meses -3 a -1), cercano menos control. En S4 lo recuperado es la diferencia con S5 de los "
         "mismos sorteos, y el IC excluye cero de S4 es el del valor bruto (con la brecha residual del mundo nulo), no el de esa "
         "diferencia. Tamaño en %: S1 es el % de días del mes perdidos, S2 el % de caída, S4 el % de nivel. Las partes son la "
         "media entre mundos del reparto del log de la brecha.", "",
         "| Escenario | Tamaño | Plantado (nominal) | Plantado en puntos | Recuperado (media) | Recuperado menos nulo | p05 a p95 | IC excluye cero | Parte de los días | Parte del caudal por día |",
         "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |"]
    for esc, tam in (("S1", 100), ("S2", 10), ("S2", 20), ("S2", 30), ("S4", 3), ("S4", 5), ("S4", 8), ("S5", 0)):
        r = f(esc, tam, "brecha_mes1")
        neto = "n/d" if r["recuperado_neto"] is None else _g(r["recuperado_neto"], 1)
        bruto = " (bruto)" if esc == "S4" else ""
        L.append(f"| {esc} | {tam} | {_g(r['plantado'], 1)} | {_g(r['plantado_puntos'], 1)} | {_g(r['recuperado_media'], 1)} | {neto} | {_rango(r)} "
                 f"| {_pc(r['ic_excluye_cero_frac'])}{bruto} | {_pc(r['parte_dias'])} | {_pc(r['parte_tasa'])} |")
    L += ["", "## Pendiente del mes 0", "",
          "Puntos del índice por cada 0,1 de f0 (la fracción del mes posterior al inicio de la fractura). El IC cuenta el signo plantado "
          "(negativo) salvo en S5, donde cuenta cualquier signo. La última columna es la misma pendiente en el mes -1, sin días "
          "expuestos, que debe quedar cerca de cero.", "",
          "| Escenario | Tamaño | Plantado (nominal) | Plantado en puntos | Recuperada (media) | Recuperada menos nulo | p05 a p95 | IC excluye cero | Mes -1 (media) |",
          "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |"]
    for esc, tam in (("S3", 20), ("S3", 40), ("S3", 60), ("S5", 0)):
        r = f(esc, tam, "pendiente_mes0")
        m1 = f(esc, tam, "pendiente_mes_m1")
        neto = "n/d" if r["recuperado_neto"] is None else _g(r["recuperado_neto"], 1)
        L.append(f"| {esc} | {tam} | {_g(r['plantado'], 1)} | {_g(r['plantado_puntos'], 1)} | {_g(r['recuperado_media'], 1)} | {neto} | {_rango(r)} "
                 f"| {_pc(r['ic_excluye_cero_frac'])} | {_g(m1['recuperado_media'], 1)} |")
    pts4 = [f("S4", 5, m)["plantado_puntos"] for m in ("preten", "brecha_mes1_base_limpia", "brecha_mes1_neta")]
    L += ["", "## Brecha previa de nivel", "",
          "Medias entre mundos en puntos. En S4 se resta S5 de los mismos sorteos; la fila de S5 es el valor absoluto del mundo nulo, "
          "su brecha residual. Lo plantado en S4 es menos el tamaño en la pretendencia y en el mes 1 con la base limpia (meses -6 a "
          "-4), y cero en la brecha neta (el mes 1 menos la pretendencia) y en el mes 1 con la base de los meses -3 a -1. Medido en "
          f"puntos del índice, con el 5% lo plantado es {_g(pts4[0], 1)} en la pretendencia, {_g(pts4[1], 1)} en el mes 1 con la base "
          f"limpia y {_g(pts4[2], 1)} en la brecha neta.", "",
          "| Escenario | Tamaño | Pretendencia | Mes 1, base limpia | Mes 1 neto | Mes 1, base -3 a -1 |",
          "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for esc, tam in (("S5", 0), ("S4", 3), ("S4", 5), ("S4", 8)):
        vals = [f(esc, tam, m)["recuperado_media"] for m in ("preten", "brecha_mes1_base_limpia", "brecha_mes1_neta", "brecha_mes1")]
        L.append(f"| {esc} | {tam} | " + " | ".join(_g(x, 1) for x in vals) + " |")
    L += ["", "## Límites", "",
          "- Los efectos plantados son simples (multiplicativos, el mismo para todos los cercanos de un pad) e independientes de la "
          "geología, la distancia y el operador. Recuperarlos dice algo del estimador, no de los pozos.",
          "- El cierre de S1 se mide con los días acotados a un día de 30 en la descomposición, así que un mes cerrado entero es un "
          "efecto de días casi por construcción: la parte de los días de S1 es una verificación débil. S2 es la prueba que separa.",
          "- El mundo nulo tiene una brecha residual (los cercanos de la fecha falsa no son idénticos a los controles) y los pozos "
          "reales traen su propio ruido y sus cierres; por eso en S4 se resta el nulo.",
          "- Un padre puede ser cercano en un evento y control en otro: un efecto plantado puede tocar un control por solapamiento de "
          "ventanas, y un cercano en dos eventos cercanos recibe el efecto dos veces. No se corrige.",
          f"- Cada mundo usa el {_g(100 * FRACCION_PADS)}% de los pads, así que el IC y la tasa de falsos positivos son los de una "
          "muestra más chica que la del resultado principal.",
          f"- La corrida con {_g(MUNDOS_PLAN)} mundos por celda pasó de los {_g(TOPE_MINUTOS)} minutos que la regla fijó como tope "
          f"(unos 9 minutos), así que se bajó a {_g(n)} mundos por celda, como la regla decía. Con menos mundos las medias y los rangos "
          "son menos estables."]
    if ok50:
        c = lambda e, t, m, col: c50[(e, t, m)][col]  # noqa: E731
        n50 = int(c("S5", 0, "brecha_mes1", "mundos"))
        k50 = round(c("S5", 0, "brecha_mes1", "ic_excluye_cero_frac") * n50)
        L.append(f"- La salida de esa corrida de {_g(n50)} mundos se guardó en `docs/inyeccion_50_mundos.txt` y se publica acá, fuera de tope y "
                 f"sin cambiar los veredictos fijados. Se corrió con una versión anterior de los datos y no se repitió con la actual, así que sus cifras son de esa versión. R1: {_g(c('S2', 20, 'brecha_mes1', 'recuperado_media'), 1)} puntos. R2: partes de "
                 f"{_pc(c('S1', 100, 'brecha_mes1', 'parte_dias'))} y {_pc(c('S2', 20, 'brecha_mes1', 'parte_tasa'))}. R3: IC que excluye cero "
                 f"en {_pc(c('S3', 40, 'pendiente_mes0', 'ic_excluye_cero_frac'))} de los mundos. R4a: {_pc(c('S5', 0, 'brecha_mes1', 'ic_excluye_cero_frac'))} "
                 f"({_g(k50)} de {_g(n50)}), que con {_g(n50)} mundos pasaría también el operador estricto. R4b: pretendencia "
                 f"{_g(c('S4', 5, 'preten', 'recuperado_media'), 1)} puntos y brecha neta del mes 1 {_g(c('S4', 5, 'brecha_mes1_neta', 'recuperado_media'), 1)}. "
                 f"El veredicto de R4a que vale es el de {_g(n)} mundos, el que fijó la regla; los {_g(n50)} dicen que el borde es "
                 "sensible al número de mundos.")
    pend_txt = (f"queda cerca de lo plantado ({_g(100 * atenuacion, 0)}%)" if cerca
                else f"no queda cerca de lo plantado ({_g(100 * atenuacion, 0)}%)")
    L += [f"- La pendiente plantada en puntos del índice es el tamaño por el índice del mes 0 de los cercanos, que es menor que 1: con el "
          f"40% es {_g(s3['plantado_puntos'], 1)} y no {_g(s3['plantado'], 1)}. Descontando la pendiente del mundo nulo "
          f"({_g(s5p['recuperado_media'], 1)}), lo recuperado ({_g(s3['recuperado_neto'], 1)}) {pend_txt}. La columna Plantado (nominal) usa "
          "el tamaño nominal. La regla R3 usa solo el signo y el IC.",
          "- Es una prueba del método sobre efectos plantados, no una prueba de causa.", ""]
    return "\n".join(L)


def principal(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    filas, p = calcular(cargar(con))
    _escribir(con, "mart_inyeccion", COLS_INY, filas)
    for r in con.execute("select * from mart_inyeccion order by escenario, tamano, medida").fetchall():
        print("[inyeccion]", tuple(round(x, 3) if isinstance(x, float) else x for x in r))
    con.close()


main = principal

if __name__ == "__main__":
    main()
