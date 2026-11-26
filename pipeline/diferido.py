"""Barriles diferidos del estudio de eventos: un rango en lugar de un total, y una cifra por evento.

Se corre despues de pipeline.placebo:  uv run python -m pipeline.diferido

Escribe en data/warehouse.duckdb (create or replace, idempotente, con semilla fija):
  mart_diferido_rango     el total de los meses 0 a 6 en tres variantes: original (el de mart_interferencia_diferida), sin duplicar
                          (cada mes de calendario de un padre se atribuye una sola vez) y sin duplicar y descontando la brecha previa
  mart_diferido_operador  el diferido acumulado en los 24 meses desde la fractura del hijo, por evento: distribucion de toda la
                          cuenca y por operadora del padre, con IC 95% por bootstrap de pads hijo

Que se cuenta. Para cada evento cercano (padre a menos de 1 km del hijo mas cercano) y cada mes k desde la fractura, el diferido del
mes es (indice mediano del control de la misma edad x caudal de la base del padre - caudal observado) x dias del mes, en barriles.
Es la misma cuenta de pipeline/sql/04_interferencia.sql; aca se recompone desde las tablas intermedias y se verifica contra el mart.

Por que un rango. El total original suma meses 0 a 6 de cada evento. Un padre con varios hijos en meses seguidos tiene ventanas que
se solapan, y un mismo mes de calendario de ese padre entra mas de una vez. Dos correcciones:
  (1) Sin duplicar. Cada (padre, mes de calendario) se atribuye al evento mas cercano en el tiempo entre los que lo preceden (el que
      tiene la mayor fecha de fractura menor o igual al mes). El total sin duplicar no puede superar al original mientras el diferido
      de los meses descartados no sea negativo en conjunto; se verifica y el modulo falla si no se cumple.
  (2) Descontando la brecha previa. Los padres cercanos ya rendian por debajo del control antes de la fractura (la brecha cercano
      menos control de los meses -3 a -1 en la base limpia de pipeline.placebo). Esa brecha, como punto del nivel de la base de cada
      padre y constante, se resta de cada mes. La resta no vuelve negativo un mes con diferido positivo: se corta en cero.
El rango va del total sin duplicar y descontado (cota inferior) al original (cota superior). No se da un punto medio.

Por evento. El acumulado de los meses 0 a 24 de cada evento cercano, sin las correcciones de arriba (es lo que ese padre difiere en
esa ventana contra su control, aunque otros hijos le hayan pegado en el medio). Entran los eventos con la ventana completa de 24
meses dentro de los datos. Por operadora del padre: eventos, mediana, media y proporcion con diferido positivo, con IC 95% por
bootstrap de percentiles por conglomerados de pads hijo (mismas repeticiones y misma convencion de semilla que pipeline.placebo).

Que NO es:
  * No es una comparacion de desempeno entre operadoras: cambian el tipo de pozo, la edad y las practicas de declaracion.
  * Los datos son mensuales; un cierre y un golpe dentro del mes se ven igual.
  * El control de la misma edad a 2 a 5 km no es un cero limpio: puede estar tambien afectado (ver descomposicion.md).
  * Un mes sin fila de produccion no suma ni resta (igual que en el mart original).
"""

from __future__ import annotations

from typing import NamedTuple

import duckdb
import numpy as np

from pipeline.costo import _clusters, _escribir, _g, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import REPS_BOOT, SEMILLA_PLACEBO

BBL_M3 = 6.2898                 # barriles por metro cubico, el mismo factor que 04_interferencia.sql
H_TOTAL = 6                     # el total se suma sobre los meses 0 a 6
H_EVENTO = 24                   # el acumulado por evento, sobre los meses 0 a 24
KS_PREVIOS = (-3, -2, -1)
MIN_EVENTOS_OPERADOR = 30       # una operadora con menos eventos va en el grupo OTRAS
SEMILLA_DIFERIDO = SEMILLA_PLACEBO + 100
TOL_REL = 1e-9

COLS_RANGO = [("variante", "varchar"), ("orden", "integer"), ("diferido_bbl", "double"), ("eventos", "integer"),
              ("meses_padre", "integer"), ("por_evento_bbl", "double"), ("brecha_previa", "double")]
COLS_OPERADOR = [("operador", "varchar"), ("orden", "integer"), ("eventos", "integer"), ("pads_hijo", "integer"),
                 ("p25_bbl", "double"), ("mediana_bbl", "double"), ("p75_bbl", "double"), ("media_bbl", "double"),
                 ("mediana_ic_bajo", "double"), ("mediana_ic_alto", "double"), ("media_ic_bajo", "double"),
                 ("media_ic_alto", "double"), ("proporcion_positiva", "double")]
VARIANTES = ("original", "sin_duplicar", "neto_previa")

SQL_FILAS = f"""
select e.padre, (year(e.mes_frac) * 12 + month(e.mes_frac) - 1)::integer as mes, date_diff('month', e.mes_frac, x.mes)::integer as k,
       e.banda, e.grupo_edad, coalesce(e.operador, 'Sin dato') as operador, coalesce(h.pad_id, e.hijo_cercano::varchar) as pad_hijo,
       e.base_m3_d, x.petroleo_m3 / x.dias_mes as m3_d, x.dias_mes
from int_interferencia_evento e
join int_pozo_ubicacion h on h.pozo_id = e.hijo_cercano
join fct_produccion x on x.pozo_id = e.padre and x.mes between e.mes_frac and e.mes_frac + interval {H_EVENTO} month
where e.banda in ('cercano', 'control')
order by e.padre, e.mes_frac, k
"""


class Fila(NamedTuple):
    """Un mes de un padre en un evento: el padre, el mes de la fractura (indice), el mes k desde ella y su caudal."""
    padre: object
    mes: int
    k: int
    banda: str
    grupo: str
    operador: str
    pad_hijo: str
    base: float
    m3_d: float | None
    dias: float


class Termino(NamedTuple):
    fila: Fila
    bbl: float


# ------------------------------------------------------------------ calculo

def indice_control(filas: list[Fila]) -> dict[tuple[str, int], float]:
    """Mediana del indice (caudal sobre base) de los controles por grupo de edad y mes k, como mart_interferencia_brecha."""
    por: dict[tuple[str, int], list[float]] = {}
    for f in filas:
        if f.banda == "control" and f.m3_d is not None:
            por.setdefault((f.grupo, f.k), []).append(f.m3_d / f.base)
    return {k: float(np.median(v)) for k, v in sorted(por.items())}


def terminos(filas: list[Fila], ctrl: dict[tuple[str, int], float], hasta: int) -> list[Termino]:
    """Diferido en barriles de cada mes k = 0..hasta de los eventos cercanos; sin caudal o sin control no hay termino."""
    out = []
    for f in filas:
        if f.banda != "cercano" or not 0 <= f.k <= hasta or f.m3_d is None or (f.grupo, f.k) not in ctrl:
            continue
        out.append(Termino(f, (ctrl[(f.grupo, f.k)] * f.base - f.m3_d) * f.dias * BBL_M3))
    return out


def deduplicar(ts: list[Termino]) -> list[Termino]:
    """Cada (padre, mes de calendario) una sola vez, con el evento de mayor fecha de fractura que no pasa del mes."""
    mejor: dict[tuple, Termino] = {}
    for t in ts:
        clave = (t.fila.padre, t.fila.mes + t.fila.k)
        if clave not in mejor or t.fila.mes > mejor[clave].fila.mes:
            mejor[clave] = t
    return [t for t in ts if mejor[(t.fila.padre, t.fila.mes + t.fila.k)] is t]


def descontar(t: Termino, brecha_previa: float) -> float:
    """Resta la brecha previa (fraccion de la base, constante) al diferido del mes; un diferido positivo no pasa a negativo."""
    resta = max(-brecha_previa, 0.0) * t.fila.base * t.fila.dias * BBL_M3
    return max(t.bbl - resta, 0.0) if t.bbl > 0 else t.bbl


def _fila_rango(variante: str, orden: int, bbls: list[float], eventos: int, brecha_previa: float | None) -> tuple:
    total = float(sum(bbls))
    return (variante, orden, total, eventos, len(bbls), total / eventos if eventos else None, brecha_previa)


def tabla_rango(ts: list[Termino], brecha_previa: float) -> list[tuple]:
    """Las tres variantes del total de los meses 0 a 6. Falla si sin duplicar supera al original o el neto al sin duplicar."""
    ts = [t for t in ts if t.fila.k <= H_TOTAL]
    sd = deduplicar(ts)
    neto = [descontar(t, brecha_previa) for t in sd]
    original = float(sum(t.bbl for t in ts))
    if sum(t.bbl for t in sd) > original * (1 + TOL_REL) + TOL_REL:
        raise ValueError("el diferido sin duplicar supera al original")
    if sum(neto) > sum(t.bbl for t in sd) * (1 + TOL_REL) + TOL_REL:
        raise ValueError("el diferido neto supera al sin duplicar")
    ev = {(t.fila.padre, t.fila.mes) for t in ts}
    ev_sd = {(t.fila.padre, t.fila.mes) for t in sd}
    return [_fila_rango("original", 1, [t.bbl for t in ts], len(ev), None),
            _fila_rango("sin_duplicar", 2, [t.bbl for t in sd], len(ev_sd), None),
            _fila_rango("neto_previa", 3, neto, len(ev_sd), brecha_previa)]


def por_evento(ts: list[Termino], ultimo: int) -> list[tuple]:
    """(operadora, pad del hijo, acumulado en bbl) de cada evento con los 24 meses de ventana dentro de los datos."""
    acum: dict[tuple, list] = {}
    for t in ts:
        f = t.fila
        if f.mes + H_EVENTO > ultimo:
            continue
        a = acum.setdefault((f.padre, f.mes), [f.operador, f.pad_hijo, 0.0])
        a[2] += t.bbl
    return [tuple(v) for _, v in sorted(acum.items(), key=lambda kv: (str(kv[0][0]), kv[0][1]))]


def _estadisticas(v: np.ndarray) -> tuple[float, float, float, float, float]:
    p25, med, p75 = np.percentile(v, [25, 50, 75])
    return float(p25), float(med), float(p75), float(v.mean()), float((v > 0).mean())


def _ic(v: np.ndarray, clave: np.ndarray, semilla: int, reps: int) -> tuple:
    """IC 95% por bootstrap de percentiles por pads hijo: (mediana bajo, mediana alto, media bajo, media alto)."""
    if len(v) < 5 or len(np.unique(clave)) < 2:
        return (None,) * 4
    grupos = _clusters(clave)
    rng = np.random.default_rng(semilla)
    med, mean = np.empty(reps), np.empty(reps)
    for r in range(reps):
        i = _remuestra(rng, grupos)
        med[r], mean[r] = np.median(v[i]), v[i].mean()
    a, b = np.percentile(med, [2.5, 97.5])
    c, d = np.percentile(mean, [2.5, 97.5])
    return float(a), float(b), float(c), float(d)


def _fila_operador(nombre: str, orden: int, v: np.ndarray, clave: np.ndarray, semilla: int, reps: int) -> tuple:
    p25, med, p75, media, pos = _estadisticas(v)
    return (nombre, orden, len(v), len(np.unique(clave)), p25, med, p75, media, *_ic(v, clave, semilla, reps), pos)


def tabla_operador(eventos: list[tuple], reps: int = REPS_BOOT, minimo: int = MIN_EVENTOS_OPERADOR) -> list[tuple]:
    """Toda la cuenca, cada operadora del padre con al menos `minimo` eventos (de mas a menos eventos) y el resto en OTRAS."""
    if not eventos:
        return []
    op = np.array([e[0] for e in eventos])
    pad = np.array([e[1] for e in eventos])
    v = np.array([e[2] for e in eventos], dtype=float)
    nombres, cuentas = np.unique(op, return_counts=True)
    propios = [n for n, c in sorted(zip(nombres, cuentas), key=lambda x: (-x[1], x[0])) if c >= minimo]
    grupo = np.where(np.isin(op, propios), op, "OTRAS")
    filas = [_fila_operador("TODAS", 0, v, pad, SEMILLA_DIFERIDO, reps)]
    for j, n in enumerate(propios, start=1):
        s = grupo == n
        filas.append(_fila_operador(str(n), j, v[s], pad[s], SEMILLA_DIFERIDO + j, reps))
    s = grupo == "OTRAS"
    if s.any():
        filas.append(_fila_operador("OTRAS", len(propios) + 1, v[s], pad[s], SEMILLA_DIFERIDO + len(propios) + 1, reps))
    return filas


def brecha_previa(con) -> float:
    """Media de la brecha cercano menos control de k = -3..-1 en la base limpia (mart_placebo_pretrend), en fraccion de la base."""
    r = con.execute("select avg(brecha), count(*) from mart_placebo_pretrend where k in (-3, -2, -1)").fetchone()
    if r[1] != len(KS_PREVIOS):
        raise RuntimeError("falta mart_placebo_pretrend: correr pipeline.placebo antes")
    return float(r[0])


def calcular(filas: list[Fila], ultimo: int, g: float, reps: int = REPS_BOOT) -> tuple[list[tuple], list[tuple]]:
    ctrl = indice_control(filas)
    return tabla_rango(terminos(filas, ctrl, H_TOTAL), g), tabla_operador(por_evento(terminos(filas, ctrl, H_EVENTO), ultimo), reps)


# ------------------------------------------------------------------ pagina

def _tab(cab: list[str], filas: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"] + ["| " + " | ".join(f) + " |" for f in filas]


def _bbl(x: float) -> str:
    return "s/d" if x is None else _g(x)


def _mbbl(x: float) -> str:
    return _g(x / 1e6, 1)


def _con_ic(x: float, bajo: float, alto: float) -> str:
    return f"{_bbl(x)} ({_bbl(bajo)} a {_bbl(alto)})" if bajo is not None else _bbl(x)


def pagina_diferido(con) -> str:
    rango = {r[0]: r for r in con.execute("select * from mart_diferido_rango order by orden").fetchall()}
    ops = con.execute("select * from mart_diferido_operador order by orden").fetchall()
    orig, sd, neto = rango["original"], rango["sin_duplicar"], rango["neto_previa"]
    todas = ops[0]
    previa = -100 * neto[6]
    L = ["# Barriles diferidos: un rango y una cifra por evento", "",
         "Página generada por `pipeline/diferido.py`. El total de barriles diferidos del estudio de interferencia se citaba como una "
         "sola cifra. Un revisor puede objetar que esa cifra cuenta dos veces los meses de un padre al que le fracturaron varios "
         "hijos seguidos, y que no descuenta que los padres cercanos ya rendían por debajo del control antes de la fractura. Acá se "
         "responde con un rango y con cifras por evento.", "",
         "## Qué se cuenta", "",
         "Para cada evento cercano (un padre a menos de 1 km de un hijo recién fracturado) y cada mes desde la fractura, el diferido "
         "del mes es el caudal que habría tenido el padre al ritmo del control de la misma edad, menos el caudal observado, por los días "
         "del mes, en barriles. Es diferido contra el control de la misma edad: producción que se atrasa, medida contra un control, "
         "sin precio y sin una causa atribuida.", "",
         "## Los tres totales (meses 0 a 6)", ""]
    L += _tab(["Variante", "Barriles diferidos", "Eventos", "Meses de padre", "Barriles por evento"],
              [[{"original": "Original (cota superior)", "sin_duplicar": "Sin duplicar",
                 "neto_previa": "Sin duplicar y descontando la brecha previa (cota inferior)"}[r[0]],
                _bbl(r[2]), _g(r[3]), _g(r[4]), _bbl(r[5])] for r in (orig, sd, neto)])
    L += ["",
          f"- Original: {_bbl(orig[2])} barriles. Suma los meses 0 a 6 de cada evento; un mismo mes de un padre con varios hijos "
          "puede entrar más de una vez.",
          f"- Sin duplicar: {_bbl(sd[2])} barriles. Cada mes de calendario de un padre se atribuye una sola vez, al evento más cercano "
          "en el tiempo entre los que lo preceden (el de la fecha de fractura más reciente que no pasa del mes).",
          f"- Sin duplicar y descontando la brecha previa: {_bbl(neto[2])} barriles. A cada mes se le resta la brecha previa a la "
          f"fractura, {_g(previa, 1)} puntos del nivel de la base de cada padre (el promedio de la brecha cercano menos control de los "
          "meses -3 a -1 en la base limpia de la página de falsación), constante y cortada en cero para que la resta no vuelva "
          "negativo un mes con diferido positivo.", "",
          f"El diferido de los meses 0 a 6 va de {_mbbl(neto[2])} a {_mbbl(orig[2])} millones de barriles. No se da un punto medio: "
          "el rango dice qué tanto depende la cifra de cómo se cuente, no cuál es la verdadera.", "",
          "## Por evento, a 24 meses", "",
          "El acumulado de los meses 0 a 24 desde la fractura del hijo, por evento y contra el control de la misma edad, sin las "
          "correcciones de arriba (es lo que ese padre difiere en la ventana, aunque otro hijo le haya pegado en el medio). Entran "
          "los eventos con la ventana completa dentro de los datos.", ""]
    L += _tab(["Eventos", "P25 (bbl)", "Mediana (bbl)", "P75 (bbl)", "Media (bbl)", "Con diferido positivo"],
              [[_g(todas[2]), _bbl(todas[4]), _bbl(todas[5]), _bbl(todas[6]), _bbl(todas[7]), f"{_g(100 * todas[12])}%"]])
    signo = ("queda por debajo de cero: a los 24 meses el padre típico no acumula diferido contra su control" if todas[5] < 0 else
             "queda por encima de cero: a los 24 meses el padre típico acumula diferido contra su control")
    if todas[8] is not None and todas[8] <= 0 <= todas[9]:
        signo += ", y el intervalo de 95% de la mediana incluye el cero (no se distingue de un padre sin diferido a esa altura)"
    L += ["", f"Intervalo de 95% de la mediana: {_bbl(todas[8])} a {_bbl(todas[9])} barriles; de la media: {_bbl(todas[10])} a "
              f"{_bbl(todas[11])} barriles (bootstrap por pads hijo, {_g(REPS_BOOT)} repeticiones).", "",
          f"La mediana por evento a 24 meses ({_bbl(todas[5])} barriles) {signo}. Es otro horizonte que el de los totales de arriba (meses 0 a 6): el diferido "
          "del primer tramo y el acumulado a 24 meses no se suman ni se restan.", "",
          "## Por operadora del padre, por evento", ""]
    L += _tab(["Operadora", "Eventos", "Mediana por evento (bbl, IC 95%)", "Media por evento (bbl, IC 95%)", "Con diferido positivo"],
              [[{"TODAS": "Toda la cuenca", "OTRAS": f"Otras (menos de {_g(MIN_EVENTOS_OPERADOR)} eventos)"}.get(o[0], o[0]),
                _g(o[2]), _con_ic(o[5], o[8], o[9]), _con_ic(o[7], o[10], o[11]), f"{_g(100 * o[12])}%"] for o in ops])
    L += ["", "El reparto por operadora no es una comparación de desempeño: cambian el tipo de pozo, la edad y las prácticas de "
              "declaración. Los intervalos son bootstrap de percentiles por conglomerados de pads hijo, sin ajuste por comparaciones "
              "múltiples.", "",
          "## Límites", "",
          "- Los datos son mensuales: un cierre y un golpe dentro del mes se ven igual.",
          "- El control de la misma edad a 2 a 5 km no es un cero limpio: puede estar también afectado por las fracturas cercanas "
          "(la página de descomposición mira el anillo de 5 a 10 km). Si lo está, el diferido medido contra él queda corto.",
          "- La brecha previa se mide en la base de los meses -6 a -4 y se aplica sobre la base de los meses -3 a -1; la corrección "
          "es una aproximación y por eso se publica como cota y no como valor.",
          "- A 24 meses el control de la misma edad también declina con la edad y su mediana no es la media: el acumulado largo se "
          "lee por su signo y su intervalo, no como un nivel.",
          "- Un mes sin fila de producción no suma ni resta.",
          "- Es una huella medida, no una causa demostrada.", "",
          "## Cómo se reproduce", "",
          "`uv run python -m pipeline.diferido` (después de `pipeline.placebo`) escribe `mart_diferido_rango` y "
          "`mart_diferido_operador`; esta página sale de esas dos tablas.", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ entrada

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    g = brecha_previa(con)
    filas = [Fila(*r) for r in con.execute(SQL_FILAS).fetchall()]
    ultimo_fecha = con.execute("select mes from ultimo_mes").fetchone()[0]
    ultimo = ultimo_fecha.year * 12 + ultimo_fecha.month - 1
    rango, operador = calcular(filas, ultimo, g)
    mart = con.execute("select sum(petroleo_diferido_bbl), count(*) from mart_interferencia_diferida").fetchone()
    if abs(rango[0][2] - mart[0]) > TOL_REL * abs(mart[0]) * 1e3 or rango[0][3] != mart[1]:
        raise RuntimeError(f"el total recompuesto ({rango[0][2]}, {rango[0][3]}) no coincide con el mart ({mart[0]}, {mart[1]})")
    _escribir(con, "mart_diferido_rango", COLS_RANGO, rango)
    _escribir(con, "mart_diferido_operador", COLS_OPERADOR, operador)
    for t in ("mart_diferido_rango", "mart_diferido_operador"):
        for r in con.execute(f"select * from {t} order by orden").fetchall():
            print(f"[diferido] {t[14:]:<10}", tuple(round(x, 3) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
