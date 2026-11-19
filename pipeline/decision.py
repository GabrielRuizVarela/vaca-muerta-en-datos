"""Capa de decision para un operador: de los hallazgos a unidades de decision (edad del padre, banda de espaciamiento).

Se corre despues de pipeline.diferido, pipeline.anillo y pipeline.dosis_pad:  uv run python -m pipeline.decision

REGLA FIJADA ANTES DE CORRER (2026-11-17, antes de calcular ninguna cifra de este modulo; no se cambia despues de ver
resultados). No es una prueba nueva: es una traduccion de numeros que ya estan en el warehouse. Solo se lee de los marts de
costo, diferido, anillo, descomposicion, perdida_permanente y dosis; no se reestima ningun modelo. La unica cuenta propia es
el promedio de un diferido por evento que ya existe (mart_interferencia_diferida) por grupo, con IC bootstrap por pads HIJO.

Pregunta de un operador que va a fracturar un hijo cerca de un padre en produccion: de cuanto es la caida del padre en el mes 1,
que parte se recupera a los 6 meses, cuantos metros cubicos de petroleo se difieren por padre, que parte puede ser perdida y
cuanto valdria eso con un precio y una tasa que pone quien lo usa.

Unidades de decision (dos tablas separadas; no se cruzan porque el dato publico no alcanza para celdas de edad por distancia):
  * Por edad del padre (grupo_edad de int_interferencia_evento: 06-11, 12-23, 24-47, 48+, y "todos"): los cercanos son los
    padres a menos de 1 km del hijo mas cercano. Brecha del mes 1 y del mes 6 = indice mediano cercano menos indice mediano
    control, de mart_interferencia_brecha (base de los meses -3 a -1, control = banda 'control'). Brecha en puntos del nivel
    propio del padre (indice * 100), negativa si el padre rinde menos.
  * Por banda de espaciamiento (distancia al hijo mas cercano: 0 a 0,3, 0,3 a 0,6, 0,6 a 1 km, y de referencia 1 a 2 y 2 a 5 km,
    que no son cercanos): brecha del mes 1 con IC 95% de mart_descomposicion_distancia (base '-6 a -4', control '5 a 10 km').
    El mes 6 no esta publicado por banda de distancia: queda vacio y la pagina lo dice. Las dos tablas usan bases distintas
    (meses -3 a -1 la de edad, -6 a -4 la de distancia); las cifras no son intercambiables y la pagina lo rotula.

Cierre a los 6 meses (todos los cercanos juntos): de mart_anillo, brecha en k = 1 y k = 6 en las cuatro variantes de control
(V0 a V3). La parte recuperada = 1 - brecha6 / brecha1, por variante; se informa el rango entre variantes (minimo y maximo) y
los puntos que NO se recuperan (valor absoluto de la brecha del mes 6, entre su minimo y su maximo). Un cierre dentro de 5
puntos no es cero: la pagina lo dice y no llama "recuperado" a lo que queda.
Por edad, la parte recuperada = 1 - brecha6 / brecha1 solo si la brecha del mes 1 es menor que -0,05; si no, queda vacia.

Diferido por padre (barriles y metros cubicos de petroleo; 1 m3 = 6,2898 bbl, el factor de pipeline.diferido.BBL_M3):
  * Valor central y limite alto: el promedio, por evento cercano, de petroleo_diferido_bbl de mart_interferencia_diferida (los
    meses 0 a 6 con la cuenta original del estudio), por grupo (edad y banda de distancia km_min). Debe sumar, sobre todos los
    cercanos, el total 'original' de mart_diferido_rango; si difiere en mas de 1 barril el modulo falla.
  * IC 95% del promedio: bootstrap de percentiles por conglomerados de pad HIJO (pipeline.placebo.REPS_BOOT repeticiones, semilla
    SEMILLA_PLACEBO + 900 + indice del grupo). El pad hijo NO es int_interferencia_evento.pad_id (ese es el pad del PADRE): es
    int_pozo_ubicacion.pad_id del pozo hijo_cercano, con hijo_cercano::varchar si falta (igual que pipeline.diferido).
  * Valor bajo: el promedio por evento multiplicado por la razon entre las variantes 'neto_previa' y 'original' de
    mart_diferido_rango (por_evento_bbl); es una aproximacion con la razon de toda la cuenca, no un calculo por grupo, y se rotula asi.
  * Un grupo con menos de N_MIN_GRUPO eventos o menos de PADS_MIN_GRUPO pads hijo no publica intervalo.

Perdida (volumen que podria no volver): el limite alto del IC 95% de la media por evento del acumulado de 24 meses de toda
la cuenca (mart_diferido_operador, operador 'TODAS', media_ic_alto), acotado en cero por abajo, en barriles y en metros
cubicos; y el limite alto del exceso de padres que no recuperan el umbral (mart_perdida_permanente, grupo_edad 'todos',
exceso_ic_alto). Se informan como cotas superiores; no son una estimacion de la perdida.

Valor indicativo (precio y tasa son ENTRADAS de quien usa el modulo; ninguna cifra de precio es una afirmacion de este proyecto):
  valor_indicativo(volumen_m3, precio_usd_bbl, tasa_anual, rezago_meses) devuelve
    * costo_de_diferir = barriles * precio * (1 - (1 + tasa_anual) ** (-rezago_meses / 12)): el costo del valor tiempo de cobrar
      el volumen diferido rezago_meses mas tarde (supone que el volumen diferido se recupera; el dato no lo prueba).
    * valor_cota_perdida = barriles * precio: el valor sin descontar de un volumen que se perdiera (tope, no estimacion).
  La pagina muestra una grilla de entradas ilustrativas (precios, tasas y rezagos rotulados "entradas, no pronostico") sobre el
  diferido promedio por evento y sobre la cota de perdida. La linea de comandos acepta --precio, --tasa y --rezago.

Diferimiento y perdida: lo que se ve es un diferido de los meses 0 a 6 contra el control; a los 6 meses la brecha queda dentro de
5 puntos (no en cero) y a los 24 meses el acumulado por evento no se distingue de cero. Eso es compatible con diferimiento, pero
el dato mensual publico no prueba que el volumen se recupere, ni que el cierre sea preventivo y no dano.

Que NO se resuelve y que dato interno lo resolveria (se escribe en la pagina):
  * Dosis y respuesta (arena, etapas, presion, depleccion): sin respuesta en el dato publico; la potencia (pipeline.potencia_dosis)
    dice el tamano minimo detectable. Lo resolveria la geometria real de la fractura y el espaciamiento real entre ramas.
  * Direccion (el eje de mayor merma contra el SHmax publicado): no se separa con este dato. Lo resolveria el azimut de las ramas
    y la orientación de fracturas medida en pozo.
  * Cierre preventivo contra dano: con datos mensuales se ven igual. Lo resolverian los registros de cierres (shut-in) con fecha y
    hora y la presion de cabeza o de fondo del padre durante la fractura del hijo.
  * Recuperacion real del volumen diferido: lo resolverian curvas diarias o horarias del padre y pruebas de pozo antes y despues.

Que NO es: no es un pronostico de precio, de tasa ni de produccion; no es una comparacion entre operadoras; no usa datos privados.
Los numeros de la pagina se verifican en pipeline/claims.py.
"""
from __future__ import annotations

import argparse

import duckdb
import numpy as np

from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.diferido import BBL_M3
from pipeline.ingest import DATA
from pipeline.placebo import REPS_BOOT, SEMILLA_PLACEBO, _g, _pts

GRUPOS_EDAD = ("06-11", "12-23", "24-47", "48+")
BANDAS = (("0 a 0,3", 0.0, 0.3), ("0,3 a 0,6", 0.3, 0.6), ("0,6 a 1", 0.6, 1.0), ("1 a 2", 1.0, 2.0),
          ("2 a 5", 2.0, 5.0))
BANDAS_CERCANAS = BANDAS[:3]
N_MIN_GRUPO = 30
PADS_MIN_GRUPO = 10
DESPLAZAMIENTO_SEMILLA = 900
UMBRAL_BRECHA1 = -0.05
TOL_SUMA_BBL = 1.0
PRECIOS = (40, 60, 80)
TASAS = (0.10, 0.15)
REZAGOS = (6, 12, 24)

COLS_EDAD = [("grupo_edad", "varchar"), ("eventos", "integer"), ("pads_hijo", "integer"),
             ("brecha_mes1", "double"), ("brecha_mes6", "double"), ("parte_recuperada", "double"),
             ("diferido_medio_bbl", "double"), ("diferido_ic_bajo_bbl", "double"),
             ("diferido_ic_alto_bbl", "double"), ("diferido_bajo_bbl", "double"),
             ("diferido_medio_m3", "double"), ("diferido_ic_bajo_m3", "double"),
             ("diferido_ic_alto_m3", "double"), ("diferido_bajo_m3", "double"),
             ("diferido_alto_m3", "double")]
COLS_DISTANCIA = [("banda", "varchar"), ("orden", "integer"), ("n_banda", "integer"),
                  ("brecha_mes1", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
                  ("eventos_diferido", "integer"), ("pads_hijo", "integer"),
                  ("diferido_medio_bbl", "double"), ("diferido_ic_bajo_bbl", "double"),
                  ("diferido_ic_alto_bbl", "double"), ("diferido_bajo_bbl", "double"),
                  ("diferido_medio_m3", "double"), ("diferido_ic_bajo_m3", "double"),
                  ("diferido_ic_alto_m3", "double"), ("diferido_bajo_m3", "double"),
                  ("diferido_alto_m3", "double")]
COLS_CIERRE = [("variante", "varchar"), ("descripcion", "varchar"), ("brecha_mes1", "double"),
               ("brecha_mes6", "double"), ("parte_recuperada", "double")]
COLS_PERDIDA = [("cota_bbl", "double"), ("cota_m3", "double"), ("media_24m_bbl", "double"),
                ("media_ic_bajo_bbl", "double"), ("media_ic_alto_bbl", "double"), ("exceso", "double"),
                ("exceso_ic_bajo", "double"), ("exceso_ic_alto", "double")]

SQL_EVENTOS = """
select e.grupo_edad, e.km_min, e.petroleo_diferido_bbl,
       coalesce(h.pad_id, e.hijo_cercano::varchar) as pad_hijo
from mart_interferencia_diferida e
join int_pozo_ubicacion h on h.pozo_id = e.hijo_cercano
order by e.grupo_edad, e.km_min
"""


def parte_recuperada(brecha1: float | None, brecha6: float | None) -> float | None:
    """1 menos brecha6 sobre brecha1, solo si la brecha del mes 1 es menor que -0,05. Funcion pura."""
    if brecha1 is None or brecha6 is None or not brecha1 < UMBRAL_BRECHA1:
        return None
    return 1.0 - brecha6 / brecha1


def valor_indicativo(volumen_m3: float, precio_usd_bbl: float, tasa_anual: float,
                     rezago_meses: float) -> dict:
    """Costo del valor tiempo de cobrar el volumen mas tarde, y valor sin descontar de la cota. Funcion pura."""
    barriles = volumen_m3 * BBL_M3
    costo = barriles * precio_usd_bbl * (1.0 - (1.0 + tasa_anual) ** (-rezago_meses / 12.0))
    return {"costo_de_diferir": costo, "valor_cota_perdida": barriles * precio_usd_bbl}


def comprobar_total(suma: float, original: float) -> None:
    """Falla si la suma de los eventos no reproduce el total original en mas de 1 barril. Funcion pura."""
    if abs(suma - original) > TOL_SUMA_BBL:
        raise RuntimeError(f"la suma de los eventos ({suma:.1f} bbl) difiere del total original "
                           f"({original:.1f} bbl) en mas de {TOL_SUMA_BBL:g} barril")


def media_con_ic(valores: np.ndarray, pads: np.ndarray, semilla: int,
                 reps: int = REPS_BOOT) -> tuple[float, float | None, float | None]:
    """Media con IC 95% bootstrap por conglomerados de pad hijo; sin intervalo si el grupo es chico."""
    vals = np.asarray(valores, dtype=float)
    media = float(vals.mean())
    if len(vals) < N_MIN_GRUPO or len(np.unique(np.asarray(pads))) < PADS_MIN_GRUPO:
        return media, None, None
    codigos = np.unique(np.asarray(pads), return_inverse=True)[1]
    grupos = _clusters(codigos)
    rng = np.random.default_rng(semilla)
    medias = np.array([vals[_remuestra(rng, grupos)].mean() for _ in range(reps)])
    lo, hi = (float(x) for x in np.percentile(medias, [2.5, 97.5]))
    return media, lo, hi


def _pct(x: float | None) -> str:
    return "n/d" if x is None else _g(100.0 * x, 1) + "%"


def main(path=DATA / "warehouse.duckdb", precio: float | None = None, tasa: float | None = None,
         rezago: float | None = None) -> None:
    con = duckdb.connect(str(path))
    brecha_edad = {(g, k): (n, b) for g, k, n, b in
                   con.execute("select grupo_edad, k, eventos_cercanos, brecha from mart_interferencia_brecha "
                               "where k in (1, 6)").fetchall()}
    anillo = {(v, k): (desc, n, b) for v, desc, k, n, _nc, _a, _c, b, _lo, _hi in
              con.execute("select variante, descripcion, k, n_cercano, n_control, mediana_cercano, "
                          "mediana_control, brecha, ic_bajo, ic_alto from mart_anillo where k in (1, 6)").fetchall()}
    dist = {b: (n, g, lo, hi) for b, _de, _ha, _ct, n, _nc, _mb, _mc, g, lo, hi, _ba in
            con.execute("select banda, km_desde, km_hasta, control, n_banda, n_ctrl, mediana_banda, "
                        "mediana_control, brecha, ic_bajo, ic_alto, base from mart_descomposicion_distancia "
                        "where base = '-6 a -4' and control = '5 a 10 km'").fetchall()}
    rango = {v: (d, e) for v, _o, d, _ev, _mp, e, _bp in
             con.execute("select variante, orden, diferido_bbl, eventos, meses_padre, por_evento_bbl, brecha_previa "
                         "from mart_diferido_rango").fetchall()}
    razon_baja = rango["neto_previa"][1] / rango["original"][1]
    filas = con.execute(SQL_EVENTOS).fetchall()
    comprobar_total(float(sum(f[2] for f in filas)), rango["original"][0])

    def _grupo(vals, pads, indice):
        media, lo, hi = media_con_ic(np.array(vals), np.array(pads),
                                     SEMILLA_PLACEBO + DESPLAZAMIENTO_SEMILLA + indice)
        bajo = media * razon_baja
        return (media, lo, hi, bajo, media / BBL_M3,
                None if lo is None else lo / BBL_M3, None if hi is None else hi / BBL_M3,
                bajo / BBL_M3, media / BBL_M3)

    filas_edad = []
    for i, g in enumerate(GRUPOS_EDAD):
        sel = [f for f in filas if f[0] == g]
        b1 = brecha_edad[(g, 1)][1]
        filas_edad.append((g, brecha_edad[(g, 1)][0], len({f[3] for f in sel}), b1, brecha_edad[(g, 6)][1],
                           parte_recuperada(b1, brecha_edad[(g, 6)][1]),
                           *_grupo([f[2] for f in sel], [f[3] for f in sel], i)))
    b1t, b6t = anillo[("V0", 1)][2], anillo[("V0", 6)][2]
    filas_edad.append(("todos", anillo[("V0", 1)][1], len({f[3] for f in filas}), b1t, b6t,
                       parte_recuperada(b1t, b6t),
                       *_grupo([f[2] for f in filas], [f[3] for f in filas], len(GRUPOS_EDAD))))
    _escribir(con, "mart_decision_edad", COLS_EDAD, filas_edad)

    filas_dist = []
    for j, (banda, lo_km, hi_km) in enumerate(BANDAS):
        n_b, g_b, lo_b, hi_b = dist[banda]
        if j < len(BANDAS_CERCANAS):
            sel = [f for f in filas if lo_km <= f[1] < hi_km]
            dif = (len(sel), len({f[3] for f in sel}),
                   *_grupo([f[2] for f in sel], [f[3] for f in sel], len(GRUPOS_EDAD) + 1 + j))
        else:
            dif = (None, None, None, None, None, None, None, None, None, None, None)
        filas_dist.append((banda, j, n_b, g_b, lo_b, hi_b, *dif))
    _escribir(con, "mart_decision_distancia", COLS_DISTANCIA, filas_dist)

    filas_cierre = []
    for v in ("V0", "V1", "V2", "V3"):
        b1, b6 = anillo[(v, 1)][2], anillo[(v, 6)][2]
        filas_cierre.append((v, anillo[(v, 1)][0], b1, b6, 1.0 - b6 / b1))
    _escribir(con, "mart_decision_cierre", COLS_CIERRE, filas_cierre)

    med, lo24, hi24 = con.execute("select media_bbl, media_ic_bajo, media_ic_alto from mart_diferido_operador "
                                  "where operador = 'TODAS'").fetchone()
    exc, exc_lo, exc_hi = con.execute("select exceso, exceso_ic_bajo, exceso_ic_alto from mart_perdida_permanente "
                                       "where grupo_edad = 'todos'").fetchone()
    cota = max(0.0, hi24)
    _escribir(con, "mart_decision_perdida", COLS_PERDIDA,
              [(cota, cota / BBL_M3, med, lo24, hi24, exc, exc_lo, exc_hi)])
    for r in filas_edad:
        print(f"[decision] edad {r[0]}: {r[1]} eventos, {r[2]} pads hijo, brecha1 {r[3]:+.4f}, brecha6 {r[4]:+.4f}, "
              f"diferido medio {r[6]:,.1f} bbl ({r[10]:,.1f} m3)")
    for r in filas_dist:
        medio = "n/d" if r[8] is None else f"{r[8]:,.1f} bbl"
        print(f"[decision] distancia {r[0]}: brecha1 {r[3]:+.4f}, diferido medio {medio}")
    print(f"[decision] cota de perdida {cota:,.1f} bbl ({cota / BBL_M3:,.1f} m3), exceso {_pts(exc)} puntos")
    if precio is not None and tasa is not None and rezago is not None:
        for etiqueta, m3 in ([(f"edad {r[0]}", r[10]) for r in filas_edad] +
                             [(f"distancia {r[0]}", r[12]) for r in filas_dist if r[12] is not None]):
            v = valor_indicativo(m3, precio, tasa, rezago)
            print(f"[decision] {etiqueta}: {_g(m3)} m3 por padre -> costo de diferir {_g(v['costo_de_diferir'])} USD "
                  f"con {precio:g} USD/bbl, tasa {tasa * 100:g}% y rezago {rezago:g} meses")
        v = valor_indicativo(cota / BBL_M3, precio, tasa, rezago)
        print(f"[decision] cota de perdida: {_g(cota / BBL_M3)} m3 -> valor sin descontar "
              f"{_g(v['valor_cota_perdida'])} USD con {precio:g} USD/bbl")
    con.close()


def pagina_decision(con) -> str:
    """Página de wiki a partir de los marts de decision.py. Texto en espanol, sin rayas largas."""
    edad = {r[0]: r for r in con.execute("select * from mart_decision_edad").fetchall()}
    dist = con.execute("select * from mart_decision_distancia order by orden").fetchall()
    cierre = con.execute("select * from mart_decision_cierre order by variante").fetchall()
    cota_bbl, cota_m3, med24, lo24, hi24, exc, exc_lo, exc_hi = con.execute(
        "select * from mart_decision_perdida").fetchall()[0]
    t = edad["todos"]
    pmin = min(r[4] for r in cierre)
    pmax = max(r[4] for r in cierre)
    b6min = min(r[3] for r in cierre)
    b6max = max(r[3] for r in cierre)
    b1min = min(edad[g][3] for g in GRUPOS_EDAD)
    b1max = max(edad[g][3] for g in GRUPOS_EDAD)
    L = ["# Capa de decisión para un operador", "",
         "Página generada por `pipeline/decision.py`. Traduce los hallazgos del estudio de eventos a unidades de "
         "decisión para un operador que va a fracturar un hijo cerca de un padre en produccion: caída del padre en el "
         "mes 1, parte de la brecha que se cierra a los 6 meses, metros cúbicos diferidos por padre, cota de lo que podría no "
         "volver y su valor indicativo con precio y tasa que pone quien lo usa. No estima modelos nuevos: solo "
         "promedia un diferido por evento que ya existe y reordena brechas ya publicadas.", "",
         "## Resumen", "",
         f"- Diferido medio por evento de todos los cercanos: {_g(t[10])} m3 por padre "
         f"(IC 95%: {_g(t[11])} a {_g(t[12])}; rango bajo a alto: {_g(t[13])} a {_g(t[14])}).",
         f"- A los 6 meses la brecha queda dentro de 5 puntos, no en cero: con el control de 2 a 5 km (V0) es de "
         f"{_pts(edad['todos'][4])} puntos, y entre las cuatro variantes de control va de {_pts(b6min)} a {_pts(b6max)}.",
         "- El diferido es el volumen que falta contra el control en los meses 0 a 6 (no se sabe si llega después), no una "
         "pérdida demostrada: a los 24 meses el acumulado por evento no se distingue de cero.",
         f"- Cota superior de lo que podría no volver: {_g(cota_bbl)} bbl ({_g(cota_m3)} m3) por evento, sin "
         "descontar; no es una estimación de la pérdida.",
         f"- La caída del mes 1 va de {_pts(b1min)} a {_pts(b1max)} puntos segun la edad del padre (tabla de abajo).",
         "", "## Por edad del padre", "",
         "Brechas en puntos del nivel propio del padre (índice por 100, negativa si el padre rinde menos). Base de los "
         "meses -3 a -1 y control de la misma edad a 2 a 5 km, de mart_interferencia_brecha. La fila todos usa las "
         "brechas V0 de mart_anillo (cercanos juntos, control 2 a 5 km). La parte recuperada es 1 menos el cociente "
         "entre la brecha del mes 6 y la del mes 1, solo si la brecha del mes 1 es menor que -0,05; si no, queda "
         "vacia. El diferido medio es el promedio por evento de mart_interferencia_diferida, con IC bootstrap por "
         "pads hijo; el valor bajo multiplica el promedio por la razón neto_previa sobre original de toda la cuenca "
         "(aproximación, no cálculo por grupo).", "",
         "| Grupo de edad del padre (meses) | Eventos | Brecha mes 1 (puntos) | Brecha mes 6 (puntos) | "
         "Parte recuperada | Diferido medio por padre (m3) | IC 95% (m3) | Rango bajo a alto (m3) |",
         "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for g in list(GRUPOS_EDAD) + ["todos"]:
        r = edad[g]
        ic = "n/d" if r[11] is None or r[12] is None else f"{_g(r[11])} a {_g(r[12])}"
        L.append(f"| {g} | {_g(r[1])} | {_pts(r[3])} | {_pts(r[4])} | {_pct(r[5])} | {_g(r[10])} | {ic} | "
                 f"{_g(r[13])} a {_g(r[14])} |")
    L += ["", "Por edad las brechas son diferencias de medianas, sin intervalo. Una parte recuperada mayor que 100% quiere "
          "decir que la mediana del padre cercano queda por encima de la del control en el mes 6.",
          f"La fila de 48 meses o más queda en {_pts(edad['48+'][4])} puntos en el mes 6, fuera de los 5 puntos del total: "
          "con padres viejos el cierre a los 6 meses es el menos completo de los cuatro grupos.", "",
          "## Por banda de espaciamiento", "",
          "Base de los meses -6 a -4 y control de 5 a 10 km, de mart_descomposicion_distancia. Las cifras no son "
          "intercambiables con la tabla por edad (bases distintas). El mes 6 no está publicado por distancia. Las "
          "bandas 1 a 2 y 2 a 5 km son de referencia (no son cercanos) y no tienen diferido. La columna Eventos es la de "
          "la brecha; el diferido promedia los eventos de mart_interferencia_diferida cuya distancia cae en la banda.", "",
          "| Banda de distancia al hijo más cercano (km) | Eventos | Brecha mes 1 (puntos) | IC 95% (puntos) | "
          "Diferido medio por padre (m3) |",
          "| --- | ---: | ---: | --- | ---: |"]
    for _b, _o, n_b, g_b, lo_b, hi_b, _ev, _pads, _mb, _lb, _hb, _bb, m3, _l3, _h3, _b3, _a3 in dist:
        L.append(f"| {_b} | {_g(n_b)} | {_pts(g_b)} | {_pts(lo_b)} a {_pts(hi_b)} | {_g(m3)} |")
    L += ["", "## Cierre a 6 meses", "",
          "Brechas de mart_anillo en k = 1 y k = 6 con cuatro controles distintos (los cercanos son siempre los mismos, "
          "a menos de 1 km). La parte recuperada es 1 menos el cociente entre la brecha del mes 6 y la del mes 1, por "
          "variante.", "",
          "| Variante | Control | Brecha k = 1 (puntos) | Brecha k = 6 (puntos) | Parte recuperada |",
          "| --- | --- | ---: | ---: | ---: |"]
    for v, desc, b1, b6, p in cierre:
        L.append(f"| {v} | {desc} | {_pts(b1)} | {_pts(b6)} | {_pct(p)} |")
    L += ["",
          f"La parte recuperada va de {_g(100 * pmin, 1)}% a {_g(100 * pmax, 1)}% entre variantes, y lo que no se "
          f"recupera (valor absoluto de la brecha del mes 6) va de {_pts(min(abs(b6min), abs(b6max)))} a "
          f"{_pts(max(abs(b6min), abs(b6max)))} puntos. Un cierre dentro de 5 puntos no es cero: la página no llama "
          "recuperado a lo que queda.", "",
          "## Diferido o pérdida", "",
          f"El diferido medio por evento de todos los cercanos es {_g(t[10])} m3 por padre "
          f"(IC 95%: {_g(t[11])} a {_g(t[12])} m3; rango bajo a alto: {_g(t[13])} a {_g(t[14])} m3). En barriles: "
          f"{_g(t[6])} bbl por evento (IC 95%: {_g(t[7])} a {_g(t[8])}; rango bajo a alto: {_g(t[9])} a {_g(t[6])}).",
          "",
          f"Acumulado por evento a 24 meses (toda la cuenca): media {_g(med24)} bbl, IC 95% {_g(lo24)} a {_g(hi24)}: "
          "no se distingue de cero.", "",
          f"La cota superior de pérdida es de {_g(cota_bbl)} bbl ({_g(cota_m3)} m3) por evento, sin descontar; no es "
          "una estimación de la pérdida.", "",
          f"El exceso de padres que no recuperan el umbral (90% de la trayectoria del control) al mes 12 es de {_pts(exc)} puntos "
          f"(IC 95%: {_pts(exc_lo)} a {_pts(exc_hi)}).", "",
          "Lo que se ve es un diferido de los meses 0 a 6 contra el control; a los 6 meses la brecha queda dentro de "
          "5 puntos (no en cero) y a los 24 meses el acumulado por evento no se distingue de cero. Eso es compatible "
          "con diferimiento, pero el dato mensual público no prueba que el volumen se recupere, ni que el cierre sea "
          "preventivo y no daño.", "",
          "## Valor indicativo", "",
          "Precio y tasa son entradas de quien usa el módulo; ningúna cifra de precio es una afirmación de este "
          "proyecto. Fórmulas: costo_de_diferir = barriles * precio * (1 - (1 + tasa) ** (-rezago_meses / 12)); "
          f"valor_cota_perdida = barriles * precio. Con 1 m3 = {_g(BBL_M3, 4)} bbl. El costo de diferir supone que "
          "el volumen diferido se recupera; el dato no lo prueba.", "",
          "Precios, tasas y rezagos de las grillas son entradas, no pronóstico ni precio observado.", "",
          f"Sobre el diferido medio por evento de todos los cercanos ({_g(t[10])} m3 por padre): costo de diferir "
          "en USD por padre.", "",
          "| Precio (USD/bbl) | Tasa anual | Rezago (meses) | Costo de diferir (USD por padre) |",
          "| ---: | ---: | ---: | ---: |"]
    for p in PRECIOS:
        for ts in TASAS:
            for rz in REZAGOS:
                v = valor_indicativo(t[10], p, ts, rz)
                L.append(f"| {p} | {ts * 100:.0f}% | {rz} | {_g(v['costo_de_diferir'])} |")
    L += ["", f"Sobre la cota de pérdida ({_g(cota_m3)} m3 por evento): valor sin descontar en USD por evento.", "",
          "| Precio (USD/bbl) | Valor de la cota (USD) |",
          "| ---: | ---: |"]
    for p in PRECIOS:
        v = valor_indicativo(cota_m3, p, 0.0, 0)
        L.append(f"| {p} | {_g(v['valor_cota_perdida'])} |")
    L += ["", "## Qué no se resuelve y qué dato interno lo resolvería", "",
          "| Tema | Estado con el dato público | Dato interno que lo resolvería |",
          "| --- | --- | --- |",
          "| Dosis y respuesta (arena, etapas, presión, depleción) | Sin respuesta en el dato público; "
          "pipeline.potencia_dosis dice el tamaño minimo detectable | Geometría real de la fractura y espaciamiento "
          "real entre ramas |",
          "| Dirección (eje de mayor merma contra el SHmax publicado) | No se separa con este dato | Azimut de las "
          "ramas y orientación de fracturas medida en pozo |",
          "| Cierre preventivo contra daño | Con datos mensuales se ven igual | Registros de cierres (shut-in) con "
          "fecha y hora y presión de cabeza o de fondo del padre durante la fractura del hijo |",
          "| Recuperación real del volumen diferido | El dato mensual público no prueba que el volumen se recupere | "
          "Curvas diarias o horarias del padre y pruebas de pozo antes y despues |", "",
          "## Cómo se reproduce", "",
          "`uv run python -m pipeline.decision` escribe los marts mart_decision_edad, mart_decision_distancia, "
          "mart_decision_cierre y mart_decision_perdida; `uv run python -m pipeline.wiki` genera esta página.", "",
          "Con `uv run python -m pipeline.decision --precio P --tasa R --rezago M` también imprime el valor indicativo "
          "por grupo con esas entradas.", "",
          f"Promedios con IC bootstrap de percentiles por pads hijo ({REPS_BOOT} repeticiones, semilla fija); un grupo "
          f"con menos de {N_MIN_GRUPO} eventos o {PADS_MIN_GRUPO} pads hijo no publica intervalo.", "",
          "El valor bajo multiplica el promedio por la razón neto_previa sobre original de toda la cuenca: "
          "aproximación, no cálculo por grupo. La suma sobre todos los cercanos reproduce el total original de "
          "mart_diferido_rango (el módulo falla si difiere en más de 1 barril).", ""]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="pipeline.decision", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--precio", type=float, default=None, help="precio en USD/bbl para el valor por grupo")
    ap.add_argument("--tasa", type=float, default=None, help="tasa anual (tanto por uno) para el valor por grupo")
    ap.add_argument("--rezago", type=float, default=None, help="rezago en meses para el valor por grupo")
    a = ap.parse_args()
    dados = [x is not None for x in (a.precio, a.tasa, a.rezago)]
    if any(dados) and not all(dados):
        ap.error("--precio, --tasa y --rezago se dan los tres juntos")
    main(precio=a.precio, tasa=a.tasa, rezago=a.rezago)
