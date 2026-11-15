"""Sincronia dentro del mes: la brecha del mes de la fractura, si crece con la fraccion del mes posterior al inicio de la fractura.

Se corre despues de pipeline.build:  uv run python -m pipeline.sincronia

REGLA FIJADA ANTES DE CORRER (2026-11-15, antes de calcular ninguna cifra; no se cambia despues de ver resultados).
Fuente: docs/proceso/investigacion-fase3.md, seccion 3.5.

Pregunta: si la merma de los padres cercanos sigue a la fecha de inicio de la fractura del hijo dentro del mes, la brecha del
mes 0 deberia ser mas grande cuanto mas temprano en el mes empieza la fractura (mas dias del mes 0 ya expuestos). Un
artefacto de calendario no deberia reproducir esa dosis en el tiempo.

Definiciones:
  * f0 = (dias_del_mes - dia_de_inicio + 1) / dias_del_mes, donde dia_de_inicio es el dia del mes de la PRIMERA fecha de inicio
    de fractura del hijo (la misma fecha que fija el mes 0, `int_frac_hijo`). Cuenta el dia de inicio como expuesto. Un inicio el
    dia 1 da f0 = 1; un inicio el ultimo dia da 1 / dias_del_mes. Se usan los dias reales del mes (28, 29, 30 o 31).
  * Eventos: los de pipeline.placebo.marco con la base limpia (meses -6 a -4, la de la pretendencia), padres cercanos (menos de
    1 km del hijo mas cercano) y controles (2 a 5 km). Cada evento hereda el f0 de su hijo mas cercano.
  * Resultado de un evento: indice de petroleo del mes k (caudal por dia sobre su media de la base), acotado a [0, 2].
  * Brecha de un grupo: mediana de los cercanos menos mediana de los controles, en puntos de indice (como el resto del estudio).

Prueba (k = 0, fija):
  1. Tabla por terciles de f0: los cortes son los terciles de f0 del conjunto de eventos cercanos y control juntos (3 grupos
     con los mismos cortes para los dos, asi un artefacto de calendario cae en ambos). Grupo 1: f0 <= q33; grupo 2: q33 < f0 <=
     q67; grupo 3: f0 > q67. En cada grupo, brecha del mes 0 con IC 95% por bootstrap de pads hijo (REPS_BOOT repeticiones).
  2. Pendiente: regresion de minimos cuadrados del indice del evento sobre cercano, f0 y cercano por f0, con efectos fijos de area
     y de ano de fractura. El coeficiente de cercano por f0 es la pendiente de la brecha en puntos de indice por unidad de f0 (de
     0 a 1). IC 95% por bootstrap de percentiles por pads hijo, con la semilla de la pretendencia de pipeline.placebo para el
     mismo k (SEMILLA_PLACEBO + 100 + posicion de k en KS_PRE).
  3. La misma pendiente en k = -1 (el mes anterior al inicio, sin dias expuestos): control de calendario. Se informa y entra en
     el veredicto solo como se dice abajo.

Signo: la brecha es cercano menos control, negativa si el padre cercano rinde menos. Una dosis en el tiempo es una pendiente
NEGATIVA (la brecha se hace mas negativa cuando f0 crece).

Umbrales fijos:
  * Con dosis (sostiene): IC 95% de la pendiente en k = 0 con limite superior menor que UMBRAL_DOSIS = -0,02 (la brecha cambia
    al menos 2 puntos de indice entre f0 = 0 y f0 = 1 y el intervalo excluye cero). Es la hipotesis `sincronia_mes0` del libro
    (valor = limite superior, expectativa < -0,02).
  * Plana (la sincronia no se sostiene): IC que incluye cero (limite inferior <= 0 <= limite superior).
  * Opuesta (debilita el vinculo temporal): limite inferior del IC mayor que cero.
  * Intermedia (no firme): limite superior entre -0,02 y 0 (excluye cero pero con menos de 2 puntos).
  * Si la pendiente en k = -1 tiene un IC que excluye cero con el mismo signo que la de k = 0, el veredicto con dosis pasa a "no
    firme" (la pendiente puede ser calendario o anticipacion, no dosis).
  * Minimo de eventos: 30 cercanos y 30 controles en cada grupo de terciles. Si algun grupo no llega, no se calcula veredicto y se
    informa eso.
  * Se publican todos los grupos calculados y las dos pendientes; no se elige el mejor.

Que NO prueba:
  * El indice es mensual: el mes 0 mezcla dias antes y despues del inicio, asi que la dosis esta atenuada y es una prueba de
    signo y orden, no de magnitud por dia.
  * Hay brecha previa al inicio (pretendencia); si la brecha del mes -1 depende de f0 la pendiente del mes 0 no se separa de ella.
  * Es una huella medida de sincronia entre fechas de fractura y caudal mensual, no una prueba de causa.
"""
from __future__ import annotations

import calendar

import duckdb
import numpy as np

from pipeline import placebo
from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, KS_PRE, REPS_BOOT, SEMILLA_PLACEBO, _g, _pts, brecha_ic

UMBRAL_DOSIS = -0.02
MIN_EVENTOS_GRUPO = 30
N_GRUPOS = 3
KS_SINCRONIA = (-1, 0)
CLIP_INDICE = (0.0, 2.0)
K_PRINCIPAL = 0

COLS_GRUPOS = [("bin", "integer"), ("fraccion_desde", "double"), ("fraccion_hasta", "double"), ("eventos", "integer"),
               ("brecha_mes0", "double"), ("ic_bajo", "double"), ("ic_alto", "double"), ("eventos_control", "integer")]
COLS_PENDIENTE = [("k", "integer"), ("eventos_cercanos", "integer"), ("eventos_control", "integer"), ("pads", "integer"),
                  ("pendiente", "double"), ("ic_bajo", "double"), ("ic_alto", "double"), ("veredicto", "varchar")]


# ------------------------------------------------------------------ fraccion del mes

def fraccion_mes0(fechas) -> np.ndarray:
    """f0 de cada fecha de inicio: (dias del mes - dia + 1) / dias del mes, con los dias reales del mes (28, 29, 30 o 31)."""
    out = []
    for d in fechas:
        n = calendar.monthrange(d.year, d.month)[1]
        out.append((n - d.day + 1) / n)
    return np.array(out, dtype=float)


def cargar(con) -> dict:
    """Datos del placebo mas f0 de cada hijo (primera fecha de inicio de fractura, la que fija el mes 0)."""
    D = placebo.cargar(con)
    ini = dict(con.execute("select h.hijo, min(f.fecha_inicio) from int_frac_hijo h join stg_fractura f on f.pozo_id = h.hijo "
                           "where f.fecha_inicio is not null and date_trunc('month', f.fecha_inicio) = h.mes_frac "
                           "group by h.hijo").fetchall())
    D["hijo_f0"] = fraccion_mes0([ini[int(h)] for h in D["hijo_id"]])
    return D


# ------------------------------------------------------------------ eventos y pendiente

def eventos(D: dict, k: int) -> dict:
    """Cercanos (banda 0) y controles (banda 2) con indice del mes k acotado, f0 de su hijo, area y ano de fractura."""
    m = placebo.marco(D, D["hijo_mes"], ks=(k,), base=BASE_LIMPIA)
    y = np.clip(m["idx"][k], *CLIP_INDICE)
    f0 = D["hijo_f0"][m["hijo"]]
    ok = ~np.isnan(y) & (m["banda"] != 1)
    return {"y": y[ok], "banda": m["banda"][ok], "f0": f0[ok], "area": m["area"][ok], "anio": D["hijo_anio"][m["hijo"]][ok],
            "clave": m["clave"][ok]}


def cortes(f0: np.ndarray) -> np.ndarray:
    """Cortes de los terciles de f0 (q33, q67)."""
    return np.quantile(f0, [1 / 3, 2 / 3])


def grupo(f0: np.ndarray, corte: np.ndarray) -> np.ndarray:
    """Grupo 1: f0 <= q33; 2: q33 < f0 <= q67; 3: f0 > q67."""
    return 1 + (f0 > corte[0]).astype(int) + (f0 > corte[1]).astype(int)


def _dummies(x: np.ndarray) -> np.ndarray:
    u, inv = np.unique(x, return_inverse=True)
    return (inv[:, None] == np.arange(1, len(u))[None, :]).astype(float)


def diseno(e: dict) -> np.ndarray:
    """Columnas: constante, cercano, f0, cercano por f0, y efectos fijos de area y de ano (la columna 3 es la pendiente)."""
    cerca = (e["banda"] == 0).astype(float)
    return np.column_stack([np.ones(len(cerca)), cerca, e["f0"], cerca * e["f0"], _dummies(e["area"]), _dummies(e["anio"])])


def pendiente(X: np.ndarray, y: np.ndarray) -> float:
    return float(np.linalg.lstsq(X, y, rcond=None)[0][3])


def pendiente_ic(e: dict, k: int, reps: int = REPS_BOOT) -> dict:
    """Pendiente del cercano por f0 con IC 95% por bootstrap de percentiles por pads hijo."""
    X = diseno(e)
    out = {"k": int(k), "n_near": int((e["banda"] == 0).sum()), "n_ctrl": int((e["banda"] == 2).sum()),
           "pads": int(len(np.unique(e["clave"]))), "pendiente": pendiente(X, e["y"]), "ic_bajo": float("nan"),
           "ic_alto": float("nan")}
    grupos = _clusters(e["clave"])
    rng = np.random.default_rng(SEMILLA_PLACEBO + 100 + KS_PRE.index(k))
    bs = []
    for _ in range(reps):
        i = _remuestra(rng, grupos)
        if (e["banda"][i] == 0).sum() < 5 or (e["banda"][i] == 2).sum() < 5:
            continue
        bs.append(pendiente(X[i], e["y"][i]))
    if bs:
        out["ic_bajo"], out["ic_alto"] = (float(x) for x in np.percentile(bs, [2.5, 97.5]))
    return out


def tabla_grupos(e: dict, k: int = K_PRINCIPAL, reps: int = REPS_BOOT) -> list[tuple]:
    """Una fila por grupo de terciles de f0 con la brecha del mes k (cercano menos control) y su IC por pads hijo."""
    g = grupo(e["f0"], cortes(e["f0"]))
    seed = SEMILLA_PLACEBO + 100 + KS_PRE.index(k)
    filas = []
    for b in range(1, N_GRUPOS + 1):
        s = g == b
        r = brecha_ic(e["y"][s], e["banda"][s], e["clave"][s], reps, seed)
        filas.append((b, float(e["f0"][s].min()), float(e["f0"][s].max()), r["n_near"], r["brecha"], r["ic_bajo"], r["ic_alto"],
                      r["n_ctrl"]))
    return filas


def veredicto(p0: dict, p_pre: dict, filas: list[tuple]) -> str:
    """Veredicto con la regla fijada en el docstring: sostiene / no firme / plana / opuesta / sin muestra."""
    if any(f[3] < MIN_EVENTOS_GRUPO or f[7] < MIN_EVENTOS_GRUPO for f in filas):
        return "sin muestra"
    if p0["ic_bajo"] > 0:
        return "opuesta"
    if p0["ic_alto"] >= 0:
        return "plana"
    if p0["ic_alto"] >= UMBRAL_DOSIS:
        return "no firme"
    if p_pre["ic_alto"] < 0:  # el mes sin dias expuestos tambien tiene pendiente negativa: calendario o anticipacion
        return "no firme"
    return "sostiene"


# ------------------------------------------------------------------ pagina

def _pend(x: float) -> str:
    """Pendiente por 0,1 de f0, en puntos de indice."""
    return _g(10 * x, 1)


TEXTO_VEREDICTO = {
    "sostiene": "La caída sigue a la fecha de fractura dentro del mes: la pendiente es negativa, su IC excluye cero y pasa el umbral.",
    "plana": "No se ve que la caída siga a la fecha de fractura dentro del mes: el IC de la pendiente incluye cero. Esto debilita el "
             "vínculo temporal con la fractura; no lo refuta.",
    "opuesta": "La pendiente tiene el signo contrario al de una dosis en el tiempo: la brecha es menor cuando la fractura empieza antes. "
               "Esto debilita el vínculo temporal con la fractura.",
    "no firme": "La pendiente no alcanza el umbral fijado, o la del mes anterior al inicio tiene el mismo signo: no se separa de un "
                "artefacto de calendario o de anticipación.",
    "sin muestra": "Algún grupo tiene menos de 30 eventos y no se calcula veredicto.",
}


def pagina_sincronia(con) -> str:
    grupos = con.execute("select * from mart_sincronia order by bin").fetchall()
    pend = {r[0]: r for r in con.execute("select * from mart_sincronia_pendiente").fetchall()}
    p0, pm1 = pend[0], pend[-1]
    v = p0[7]
    L = ["# Sincronía dentro del mes", "",
         "Página generada por `pipeline/sincronia.py`. Pregunta si la brecha del mes de la fractura crece con la fracción del mes "
         "posterior al inicio de la fractura del hijo. Complementa [Interferencia entre fracturas](interferencia.md) y la "
         "[descomposición de la brecha](descomposicion.md); la regla se fijó antes de correr y está en el libro de hallazgos como "
         "`sincronia_mes0`.", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada: **{v}**. {TEXTO_VEREDICTO[v]}", "",
         f"- Pendiente de la brecha del mes 0: {_pend(p0[4])} puntos de índice por cada 0,1 de fracción del mes (IC 95%: "
         f"{_pend(p0[5])} a {_pend(p0[6])}), sobre {_g(p0[1])} eventos cercanos y {_g(p0[2])} controles de {_g(p0[3])} pads hijo. "
         f"Entre un inicio el último día y uno el primer día del mes la brecha cambia {_g(100 * p0[4], 1)} puntos.",
         f"- Pendiente del mes -1, sin días expuestos: {_pend(pm1[4])} puntos por cada 0,1 (IC 95%: {_pend(pm1[5])} a "
         f"{_pend(pm1[6])}), sobre {_g(pm1[1])} eventos cercanos.",
         "- Se publican los tres grupos y las dos pendientes calculados; no se eligió el mejor.", "",
         "## Regla fijada antes de correr", "",
         "La fracción es f0 = (días del mes - día de inicio + 1) / días del mes, con la primera fecha de inicio de fractura del hijo y "
         "los días reales del mes (28, 29, 30 o 31). Los eventos, la base de los meses -6 a -4, los cercanos (menos de 1 km) y los "
         "controles (2 a 5 km) son los de la página de falsación; el índice se acota a 0 a 2. La pendiente sale de una regresión del "
         "índice sobre cercano, f0 y su producto, con efectos fijos de área y de año de fractura; el IC 95% es bootstrap de "
         f"percentiles por pads hijo ({_g(REPS_BOOT)} repeticiones, semilla de la pretendencia para el mismo k). La brecha es negativa "
         "si el cercano rinde menos, así que una dosis en el tiempo es una pendiente negativa.", "",
         f"- Con dosis: el límite superior del IC de la pendiente del mes 0 es menor que {_g(UMBRAL_DOSIS, 2)} (al menos 2 puntos de "
         "cambio entre f0 = 0 y 1, sin incluir cero).",
         "- Plana: el IC incluye cero. Opuesta: el límite inferior del IC es mayor que cero. No firme: el límite superior está entre "
         "-0,02 y 0, o la pendiente del mes -1 también es negativa con IC que excluye cero.",
         f"- Mínimo de {MIN_EVENTOS_GRUPO} eventos cercanos y {MIN_EVENTOS_GRUPO} controles por grupo.", "",
         "## Brecha del mes 0 por grupo de f0", "",
         "Los cortes son los terciles de f0 de los eventos cercanos y control juntos, los mismos para los dos grupos (el grupo 1 es de "
         "f0 hasta el primer corte, el 3 es de f0 mayor que el segundo). La brecha es cercano menos control, en medianas del índice y "
         "en puntos.", "",
         "| Grupo | f0 desde | f0 hasta | Eventos cercanos | Eventos control | Brecha del mes 0 (puntos) | IC 95% (puntos) |",
         "| ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for b, d, h, n, g, lo, hi, nc in grupos:
        L.append(f"| {b} | {_g(d, 3)} | {_g(h, 3)} | {_g(n)} | {_g(nc)} | {_pts(g)} | {_pts(lo)} a {_pts(hi)} |")
    L += ["", "## Pendiente", "",
          "| Mes | Eventos cercanos | Eventos control | Pads hijo | Pendiente (puntos por 0,1 de f0) | IC 95% (puntos por 0,1) |",
          "| ---: | ---: | ---: | ---: | ---: | --- |"]
    for k in KS_SINCRONIA:
        r = pend[k]
        L.append(f"| {k} | {_g(r[1])} | {_g(r[2])} | {_g(r[3])} | {_pend(r[4])} | {_pend(r[5])} a {_pend(r[6])} |")
    L += ["", "El mes -1 es el control de calendario: ahí la fractura del hijo todavía no empezó, así que una pendiente negativa en ese "
          "mes no puede ser una dosis posterior al inicio."]
    if pm1[4] < 0 <= pm1[6]:
        L.append("La pendiente del mes -1 tiene el mismo signo que la del mes 0 pero su IC incluye cero: no se puede descartar que una "
                 "parte de la pendiente del mes 0 sea calendario o anticipación, y el IC no alcanza para medir cuánta.")
    L += ["",
          "## Límites", "",
          "- El índice es mensual: el mes 0 mezcla días antes y después del inicio, de modo que la dosis está atenuada. La prueba mira "
          "el signo y el orden de los grupos, no la magnitud por día.",
          "- Hay brecha previa al inicio (la página de falsación la mide en el mes -1); si depende de la fecha de inicio, la pendiente "
          "del mes 0 no se separa de ella.",
          "- Los controles tienen su propio hijo a 2 a 5 km con su propia fecha de inicio; la comparación dentro de cada grupo supone "
          "que el calendario afecta igual a los dos.",
          "- El IC es bootstrap por pads hijo sin ajuste por comparaciones múltiples. Es una huella medida de sincronía entre las "
          "fechas de fractura y el caudal mensual, no una prueba de causa.", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ principal

def calcular(D: dict) -> tuple[list[tuple], list[tuple]]:
    e0, em1 = eventos(D, K_PRINCIPAL), eventos(D, -1)
    filas = tabla_grupos(e0)
    p0, pm1 = pendiente_ic(e0, K_PRINCIPAL), pendiente_ic(em1, -1)
    v = veredicto(p0, pm1, filas)
    pend = [(p["k"], p["n_near"], p["n_ctrl"], p["pads"], p["pendiente"], p["ic_bajo"], p["ic_alto"], v if p["k"] == K_PRINCIPAL else None)
            for p in (pm1, p0)]
    return filas, pend


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    filas, pend = calcular(cargar(con))
    _escribir(con, "mart_sincronia", COLS_GRUPOS, filas)
    _escribir(con, "mart_sincronia_pendiente", COLS_PENDIENTE, pend)
    for r in con.execute("select * from mart_sincronia order by bin").fetchall():
        print("[sincronia] grupo    ", tuple(round(x, 4) if isinstance(x, float) else x for x in r))
    for r in con.execute("select * from mart_sincronia_pendiente order by k").fetchall():
        print("[sincronia] pendiente", tuple(round(x, 4) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
