"""Golpes en el mismo mes: si a un padre le cuesta menos recibir k hijos en un mes que los mismos k hijos en meses separados.

Se corre despues de pipeline.dias_perdidos:  uv run python -m pipeline.golpes_mismo_mes
Colorado (prueba confirmatoria):              uv run python -m pipeline.golpes_mismo_mes --cuenca colorado

Para que sirve. Es la primera pieza del optimizador de calendario del libro de estrategias. Si fracturar varios hijos cerca
de un padre en el mismo mes le cuesta al padre menos por hijo que repartirlos en meses distintos, agrupar tiene valor y el
optimizador tiene que poder reagrupar fracturas; si el costo es aditivo por hijo, agrupar no ahorra nada del lado del padre.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion
de calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no.

Que se habia mirado antes de fijarla
- Publicado en el repo: el modelo de costo por evento de pipeline.costo (wiki/hallazgos/anisotropia.md, "Costo por
  evento") tiene hijos_1km como regresor: +479 bbl diferidos en los meses 0 a 6 por cada hijo adicional a menos de 1 km
  (IC 95% -991 a 1.790), con todos los eventos cercanos (no solo los aislados) y con la distancia, la arena y las etapas
  del hijo mas cercano como controles. El diferido por evento cercano de wiki/hallazgos/diferido.md va de 3.871 a 5.163
  bbl en los meses 0 a 6. Juntas, esas cifras sugieren que un hijo mas en el mismo mes agrega poco, pero el intervalo del
  coeficiente admite desde nada hasta un costo por hijo parecido al del evento entero.
- Tambien publicados: pipeline.dosis_pad (la arena de los pozos del pad del hijo fracturados en el mismo mes o a un mes de
  distancia: ninguna variable cumple), pipeline.sincronia (el dia del mes en que empieza la fractura) y
  pipeline.dias_perdidos (dias parados por banda y por operador).
- La forma del dato de este modulo, el 2026-11-20, fuera del repo: solo conteos, sin calcular ninguna perdida.
  Vaca Muerta: 2.031 eventos cercanos con la base limpia; por hijos a menos de 1 km en el mes, 281 con uno, 398 con dos,
  365 con tres y 987 con cuatro o mas. Aislados y con la ventana completa (definiciones abajo): 690 (21 con un hijo, 77
  con dos, 127 con tres, 264 con cuatro, 87 con cinco, 108 con seis y 6 con nueve o diez), de unos 160 pads hijo.
  Colorado (corte principal de la replicacion): 3.531 cercanos; aislados con ventana, 630 (64 con un hijo y el resto de 2
  a 16), de unos 100 pads hijo.
- Por eso: en Vaca Muerta la prueba es de REGLA INFORMADA (el coeficiente de costo ya se habia visto) y la pagina lo dice
  junto al veredicto. En Colorado no se habia mirado ninguna perdida con varios hijos en el mes: ahi la prueba es
  confirmatoria. Las dos cuencas se calculan en un cambio posterior a este, sin tocar la regla.
- Los meses de un solo hijo son pocos (21 aislados en Vaca Muerta), asi que la comparacion no puede ser "k hijos juntos
  contra k veces un hijo solo" medida directamente. La regla usa un modelo de costo fijo mas costo por hijo sobre todos
  los valores de k, y la tabla por k muestra la forma sin ese supuesto.

Pregunta y contrafactual
- Un mes de golpe de un padre es un mes en que se fractura por primera vez al menos un hijo a menos de KM_CERCA (1 km de
  distancia de superficie, como el resto del estudio). k es la cantidad de hijos distintos a menos de 1 km fracturados
  ese mes.
- Juntos: los k hijos en un solo mes de golpe. Separados: los mismos k hijos, cada uno en su propio mes de golpe, con los
  meses lo bastante lejos para que las ventanas no se toquen (al menos 7 meses entre uno y otro).
- Pregunta: la perdida del padre con los k juntos, es menor que la suma de las k perdidas separadas?

Datos y marco
- Cargadores de pipeline.dias_perdidos: en Vaca Muerta dias_perdidos.cargar_dias sobre descomposicion.cargar_ext y
  placebo.cargar; en Colorado dias_perdidos.cargar_cuenca.
- Eventos: placebo.marco(D, D["hijo_mes"], ks=(1,), base=BASE): el hijo mas cercano fija la banda, el padre tiene al
  menos 6 meses de produccion y la base (meses -6 a -4) da mas de 1 m3/d. Cercano: hijo mas cercano a menos de 1 km.
  Control: hijo mas cercano de 2 a 5 km. El conglomerado del bootstrap es el pad del hijo mas cercano (m["clave"]).
- k: pares padre e hijo de D con km < KM_CERCA, mes de fractura del hijo igual al mes del evento y la misma regla de edad
  del padre que usa marco. k12: lo mismo con km de KM_CERCA a KM_K12 (hijos del mismo mes algo mas lejos; un control).
- Aislado: ningun hijo a menos de KM_AISLADO (2 km) del padre se fractura en los meses -MESES_AISLADO a -1 ni en los
  meses 1 a MESES_AISLADO del evento, contando todos los pares (sin la regla de edad), como placebo.marco con sin_previos
  pero a los dos lados. Asi la ventana mide solo a los hijos de ese mes, y "separados" quiere decir al menos 7 meses.
- Ventana completa: dato de produccion en los 8 meses de VENTANA (-1 a 6), todos dentro de los datos. Un mes sin fila
  es dato faltante y el evento no entra.
- Indice del mes j: caudal por dia calendario (petroleo del mes sobre los dias del mes, D["tasa"]) sobre la base,
  acotado a [0, TOPE_INDICE] como en pipeline.costo.
- Indice de control del mes j: la mediana del indice de los eventos de control con ventana completa (a los controles no
  se les exige aislamiento).
- Perdida del evento P, en dias de produccion de base: suma sobre j de -1 a 6 de (indice de control menos indice del
  padre) por los dias del mes calendario j. Junta los dias parados y la caida de caudal. Volumen V (m3): P por el caudal
  de la base.

Modelo y prueba principal (muestra: cercanos aislados con ventana completa)
- Minimos cuadrados:  P = a + b k + c S + controles, con S = suma sobre los k hijos de (d_i - dbar), d_i la distancia de
  superficie de cada hijo y dbar la media de esas distancias sobre todos los hijos de la muestra. Controles, todos
  centrados en su media de la muestra: k12, el logaritmo del caudal de base y efectos fijos de grupo de edad del padre
  (EDADES de pipeline.dias_perdidos: 6 a 11, 12 a 23, 24 a 47, 48 o mas meses), de ano del evento y de operador del padre
  (los que tienen menos de MIN_OPERADOR eventos en la muestra van juntos como "otros").
- a es el costo fijo del mes de golpe (lo que no crece con la cantidad de hijos) y b el costo de cada hijo, los dos en
  dias de produccion de base y con la mezcla media de la muestra. Un mes con un solo hijo cuesta a + b. Juntos, k hijos
  cuestan a + b k; separados, k (a + b). Agrupar ahorra (k - 1) a.
- Estadistico del veredicto: phi = a / (a + b), la parte del costo de un mes con un solo hijo que no crece con los
  hijos. El ahorro por hijo de juntar k hijos es phi (k - 1) / k, y la razon juntos sobre separados es
  rho_k = (a + b k) / (k (a + b)).
- IC 95% de percentiles por pads hijo (REPS_BOOT repeticiones, semilla SEMILLA_GOLPES); cada repeticion reajusta el
  modelo con sus propios centros y su propio grupo "otros". Las repeticiones con a + b <= 0 se descartan para phi y
  rho_k, y se cuentan.
- Veredicto, en este orden:
  1. "sin muestra": menos de N_MIN eventos o de PADS_MIN pads hijo en la muestra, o menos de K_DISTINTOS valores de k
     con al menos N_K eventos cada uno. La pagina da los conteos.
  2. "sin perdida medible": el limite bajo del IC de a + b es menor o igual a cero (un mes con un solo hijo no tiene una
     perdida que se distinga de cero, asi que no hay nada que ahorrar).
  3. "agrupar ahorra": el limite bajo del IC de phi es mayor que cero y phi es de al menos UMBRAL_FIJO.
  4. "agrupar no ahorra": el limite alto del IC de phi es menor que UMBRAL_FIJO (el ahorro posible es menor que
     UMBRAL_FIJO (k - 1) / k por hijo).
  5. "no firme": en otro caso. La pagina da el IC y dice que el dato no decide.
- Se publican a, b, a + b, phi y rho_k para cada k de KS_RHO, con su IC, y el error de phi (desvio de las repeticiones).

Tabla por k (descriptiva, sin el supuesto lineal)
- El mismo modelo con un efecto fijo por grupo de k (GRUPOS_K: 1, 2, 3, 4, 5 a 6, 7 o mas) en lugar de a + b k y sin
  constante: la perdida ajustada de un mes de cada grupo con la mezcla media de controles, su IC por pads hijo y la
  perdida por hijo (la del grupo sobre la k media del grupo). Junto a cada grupo, la prediccion del modelo lineal en esa
  k media. Sin veredicto.

Sensibilidades (se publican; no cambian el veredicto)
- S1, volumen: el mismo modelo con V (m3) en lugar de P; da a, b y phi en m3. a en m3 es el volumen que ahorra cada hijo
  que se suma a un mes de golpe en lugar de ir a su propio mes.
- S2, sin aislamiento: todos los cercanos con ventana completa, con dos controles mas, la cantidad de hijos a menos de
  KM_AISLADO fracturados en los meses -MESES_AISLADO a -1 y en los meses 1 a MESES_AISLADO. phi con su IC.
- La distancia entre ramas (pipeline.trayectorias) no se usa: su cobertura cae despues de 2023 y la prueba queda en
  distancia de superficie, como el resto del estudio.

Valor (descriptivo; solo Vaca Muerta y solo si su veredicto es "agrupar ahorra")
- a de S1 (m3) valuado con decision.valor_indicativo en las grillas de pipeline.decision (PRECIOS, TASAS, REZAGOS): el
  costo de diferir ese volumen, en dolares por hijo agrupado. Precio y tasa son entradas de quien lo usa. Con otro
  veredicto la pagina dice que no hay ahorro que valuar.

Colorado (confirmatoria, con esta misma regla)
- Las adaptaciones de pipeline.dias_perdidos a Colorado, tal cual: dias_perdidos.cargar_cuenca (padres horizontales,
  hijos de co_hijo con la fecha de inicio de FracFocus, pad de co_pozo_pad, el warehouse de Colorado abierto solo para
  leer), el operador del ultimo mes informado a ECMC, y un padre con el primer petroleo censurado en 2018-01 y menos de
  48 meses contados desde ahi va a un grupo de edad propio (edad desconocida).
- S1 y S2 se calculan igual. El valor en dinero no se publica para Colorado.
- Tablas en el warehouse de Vaca Muerta con el nombre de la cuenca: mart_golpes_mismo_mes_colorado y
  mart_golpes_mismo_mes_colorado_prueba.

Que cambia con cada veredicto (en la pagina y en la unidad siguiente: matrices de costo, optimizador y backtest)
- Vaca Muerta "agrupar ahorra": el optimizador usa costo fijo mas costo por hijo (a y b) por padre y mes, asi que
  reagrupar hijos en un mismo mes tiene credito. Si Colorado tambien da "agrupar ahorra", la pagina lo dice sin la
  salvedad de regla informada; si no, la conserva.
- Vaca Muerta "agrupar no ahorra": el optimizador usa costo aditivo por arista (cada hijo cuesta lo mismo junto o
  separado), y agrupar no tiene credito del lado del padre.
- Vaca Muerta "no firme", "sin muestra" o "sin perdida medible": el optimizador corre los dos casos (aditivo, y fijo mas
  por hijo con la estimacion puntual) y publica el arrepentimiento con cada uno; la pagina dice que el dato no decide y
  da los numeros.

Que NO prueba
- Con dato mensual "el mismo mes" no es "al mismo tiempo": dos hijos del mismo mes pueden fracturarse con semanas de
  diferencia (pipeline.sincronia mira el dia de inicio).
- Los hijos de un mismo mes son casi siempre del mismo pad: la comparacion es entre pads de distinto tamano tanto como
  entre calendarios. Un pad mas grande puede tener otro espaciamiento, otra arena y otro diseno; los controles cubren el
  operador y la epoca, no el diseno.
- El modelo lineal en k es un supuesto; la tabla por k muestra la forma sin el.
- La perdida es contra la trayectoria del control en la ventana -1 a 6: es volumen diferido, no dice que se pierda.
- Solo el lado del padre: lo que pierde el hijo por la depleccion del padre no esta en la prueba.
- Un padre en medio de un desarrollo continuo (otros hijos cerca en los 6 meses de cada lado) no entra en la prueba
  principal; S2 lo incluye.
"""
from __future__ import annotations

import argparse
import calendar
import math

import duckdb
import numpy as np

from pipeline import descomposicion, dias_perdidos, placebo
from pipeline.costo import SEMILLA, _clusters, _escribir, _remuestra
from pipeline.cuencas import COLORADO, Cuenca, cuenca as _cuenca
from pipeline.decision import PRECIOS, REZAGOS, TASAS, valor_indicativo  # grillas y valor tiempo del valor descriptivo
from pipeline.dias_perdidos import EDADES, _dummies, _f  # grupos de edad del padre, los de la prueba C de dias_perdidos
from pipeline.diferido import BBL_M3
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, BASE_ORIGINAL, KM_PREVIOS, PAD, REPS_BOOT, VENTANA_PREVIOS, _g

BASE = BASE_LIMPIA            # meses de la base del caudal (-6 a -4)
VENTANA = (-1, 6)             # meses de la perdida del evento (extremos incluidos)
KM_CERCA = 1.0                # km: hijos que cuentan en k
KM_K12 = 2.0                  # km: hijos del mismo mes entre KM_CERCA y esta distancia (control k12)
KM_AISLADO = KM_PREVIOS       # km: radio del aislamiento (2 km)
MESES_AISLADO = VENTANA_PREVIOS  # meses a cada lado del evento sin otros hijos dentro del radio (6)
TOPE_INDICE = 2.0             # el indice del padre se acota a [0, TOPE_INDICE], como en pipeline.costo
MIN_OPERADOR = 30             # eventos en la muestra para tener efecto fijo de operador propio
N_MIN = 300                   # eventos de la muestra principal para decidir
PADS_MIN = 60                 # pads hijo de la muestra principal para decidir
K_DISTINTOS = 3               # valores de k con al menos N_K eventos cada uno
N_K = 20
UMBRAL_FIJO = 0.25            # phi minimo para "agrupar ahorra"; techo de phi para "agrupar no ahorra"
KS_RHO = (2, 3, 4, 6)         # k en las que se publica rho_k
GRUPOS_K = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 6), (7, None))  # grupos de la tabla por k
VEREDICTOS = ("agrupar ahorra", "agrupar no ahorra", "no firme", "sin muestra", "sin perdida medible")
SEMILLA_GOLPES = SEMILLA + 70

ETQ_GRUPO = tuple(f"{lo}" if hi == lo else (f"{lo} a {hi}" if hi is not None else f"{lo} o más") for lo, hi in GRUPOS_K)
COLS_K = [("grupo", "varchar"), ("orden", "integer"), ("n", "integer"), ("pads", "integer"), ("padres", "integer"),
          ("k_media", "double"), ("perdida", "double"), ("ic_bajo", "double"), ("ic_alto", "double"), ("por_hijo", "double"),
          ("por_hijo_ic_bajo", "double"), ("por_hijo_ic_alto", "double"), ("lineal", "double")]
COLS_PRUEBA = dias_perdidos.COLS_PRUEBA  # prueba, estadistico, valor, ic_bajo, ic_alto, n, veredicto
EXTRA_S2 = ("antes", "despues")          # controles de S2: hijos a menos de KM_AISLADO antes y despues del evento


def mart(sufijo: str = "", cuenca: str = "") -> str:
    """Nombre de una tabla del modulo: mart_golpes_mismo_mes[_<cuenca>]<sufijo>; Vaca Muerta va sin cuenca."""
    return "mart_golpes_mismo_mes" + (f"_{cuenca}" if cuenca else "") + sufijo


# ------------------------------------------------------------------ eventos

def _dias_calendario(mes: np.ndarray) -> np.ndarray:
    """Dias del mes calendario de cada indice de mes (meses desde 2000-01, el de placebo._mes_idx)."""
    unicos = np.unique(mes)
    dias = {int(m): calendar.monthrange(2000 + int(m) // 12, int(m) % 12 + 1)[1] for m in unicos}
    return np.vectorize(dias.__getitem__, otypes=[float])(mes) if mes.size else np.zeros(mes.shape)


def _sumar(clave_par: np.ndarray, valores: np.ndarray, clave_ev: np.ndarray) -> np.ndarray:
    """Suma de `valores` de los pares con la misma clave (padre * 100_000 + mes) que cada evento; 0 sin pares."""
    if not len(clave_par):
        return np.zeros(len(clave_ev))
    u, inv = np.unique(clave_par, return_inverse=True)
    s = np.bincount(inv, weights=valores, minlength=len(u))
    pos = np.minimum(np.searchsorted(u, clave_ev), len(u) - 1)
    return np.where(u[pos] == clave_ev, s[pos], 0.0)


def _en_rango(claves: np.ndarray, padre: np.ndarray, mes: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """Cuantos pares (claves ordenadas) tiene el padre con un hijo fracturado en los meses mes + lo a mes + hi."""
    base = padre * 100_000 + mes
    return np.searchsorted(claves, base + hi, side="right") - np.searchsorted(claves, base + lo, side="left")


def _grupo_edad(edad: np.ndarray, desconocida: np.ndarray) -> np.ndarray:
    g = np.full(len(edad), -1)
    for i, (lo, hi) in enumerate(EDADES):
        g[(edad >= lo) & ((edad <= hi) if hi is not None else True)] = i
    g[desconocida] = len(EDADES)  # Colorado: primer petroleo censurado y edad contada menor que el ultimo grupo
    return g


def eventos(D: dict) -> dict:
    """Eventos de placebo.marco con k, k12, aislamiento, ventana completa y la perdida P (dias de base) y V (m3)."""
    m = placebo.marco(D, D["hijo_mes"], ks=(1,), base=BASE)  # tambien exige la base original (BASE_ORIGINAL) > BASE_MIN
    mes_par = D["hijo_mes"][D["par_hijo"]]
    edad_ok = D["primer"][D["par_padre"]] <= mes_par - placebo.EDAD_MIN
    clave_par = D["par_padre"] * 100_000 + mes_par
    clave = m["padre"] * 100_000 + m["mes"]
    cerca = edad_ok & (D["par_km"] < KM_CERCA)
    medio = edad_ok & (D["par_km"] >= KM_CERCA) & (D["par_km"] < KM_K12)
    k = _sumar(clave_par[cerca], np.ones(int(cerca.sum())), clave).astype(np.int64)
    suma_km = _sumar(clave_par[cerca], D["par_km"][cerca], clave)
    k12 = _sumar(clave_par[medio], np.ones(int(medio.sum())), clave)
    radio = np.sort(clave_par[D["par_km"] < KM_AISLADO])
    antes = _en_rango(radio, m["padre"], m["mes"], -MESES_AISLADO, -1)
    despues = _en_rango(radio, m["padre"], m["mes"], 1, MESES_AISLADO)
    j = np.arange(VENTANA[0], VENTANA[1] + 1)
    tasa = D["tasa"][m["padre"][:, None], m["mes"][:, None] + j[None, :] + PAD]
    base = placebo._media(D, m["padre"], m["mes"], *BASE)
    ventana = (m["mes"] + VENTANA[1] < D["n_mes"]) & ~np.isnan(tasa).any(1)
    with np.errstate(all="ignore"):
        idx = np.clip(tasa / base[:, None], 0, TOPE_INDICE)
    ctrl = ventana & (m["banda"] == 2)
    if not ctrl.any():
        raise ValueError("no hay eventos de control con la ventana completa para el indice de control")
    indice_control = np.median(idx[ctrl], axis=0)
    perdida = ((indice_control[None, :] - idx) * _dias_calendario(m["mes"][:, None] + j[None, :])).sum(1)
    censura = D.get("censurado")
    desconocida = (censura[m["padre"]] & (m["edad"] < EDADES[-1][0]) if censura is not None
                   else np.zeros(len(m["padre"]), dtype=bool))
    e = {c: m[c] for c in ("padre", "mes", "km", "banda", "clave", "edad")}
    e.update(k=k, suma_km=suma_km, k12=k12, antes=antes.astype(float), despues=despues.astype(float),
             aislado=(antes == 0) & (despues == 0), ventana=ventana, base=base, perdida=perdida, vol=perdida * base,
             edad_g=_grupo_edad(m["edad"], desconocida), anio=2000 + m["mes"] // 12, operador=D["operador"][m["padre"]],
             indice_control=tuple(float(v) for v in indice_control))
    return e


def muestras(e: dict) -> dict[str, np.ndarray]:
    """Mascaras: la muestra principal (cercanos aislados con ventana) y la de S2 (cercanos con ventana)."""
    cerca = e["banda"] == 0
    return {"principal": cerca & e["ventana"] & e["aislado"], "S2": cerca & e["ventana"]}


# ------------------------------------------------------------------ modelo

def _controles(e: dict, i: np.ndarray, extra=()) -> np.ndarray:
    """Controles centrados en la media de la muestra i: k12, log del caudal de base, extra y efectos fijos de edad, ano y operador."""
    op = e["operador"][i].astype(object)
    vals, cnt = np.unique(op, return_counts=True)
    grandes = set(vals[cnt >= MIN_OPERADOR].tolist())
    op = np.array([o if o in grandes else "otros" for o in op], dtype=object)
    cols = [e["k12"][i], np.log(e["base"][i])] + [e[c][i] for c in extra]
    cols += _dummies(e["edad_g"][i]) + _dummies(e["anio"][i]) + _dummies(op)
    X = np.column_stack(cols)
    return X - X.mean(0)


def _s(e: dict, i: np.ndarray) -> np.ndarray:
    """S: suma sobre los k hijos de (d_i - dbar), con dbar la distancia media de todos los hijos de la muestra i."""
    k = e["k"][i].astype(float)
    return e["suma_km"][i] - k * (e["suma_km"][i].sum() / k.sum())


def ajuste(e: dict, i: np.ndarray, y: np.ndarray, extra=()) -> tuple[float, float]:
    """Minimos cuadrados de y sobre [1, k, S, controles centrados] en la muestra i: (a, b), costo fijo y costo por hijo."""
    Z = np.column_stack([np.ones(len(i)), e["k"][i].astype(float), _s(e, i), _controles(e, i, extra)])
    beta = np.linalg.lstsq(Z, y[i], rcond=None)[0]
    return float(beta[0]), float(beta[1])


def _grupo_k(k: np.ndarray) -> np.ndarray:
    g = np.full(len(k), -1)
    for n, (lo, hi) in enumerate(GRUPOS_K):
        g[(k >= lo) & ((k <= hi) if hi is not None else True)] = n
    return g


def ajuste_grupos(e: dict, i: np.ndarray, y: np.ndarray) -> np.ndarray:
    """El mismo modelo con un efecto fijo por grupo de k y sin constante: la perdida ajustada de cada grupo (NaN si falta)."""
    g = _grupo_k(e["k"][i])
    G = np.column_stack([(g == n).astype(float) for n in range(len(GRUPOS_K))])
    Z = np.column_stack([G, _s(e, i), _controles(e, i)])
    beta = np.linalg.lstsq(Z, y[i], rcond=None)[0][:len(GRUPOS_K)]
    return np.where(G.sum(0) > 0, beta, np.nan)


def _phi(a: float, b: float) -> float:
    return a / (a + b) if a + b > 0 else math.nan


def _rho(a: float, b: float, k: int) -> float:
    return (a + b * k) / (k * (a + b)) if a + b > 0 else math.nan


def _ic(x) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return (float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))) if len(x) else (math.nan, math.nan)


def veredicto(n: int, pads: int, conteo_k: dict, ab_ic_bajo: float, phi: float, phi_ic_bajo: float, phi_ic_alto: float) -> str:
    """La regla del encabezado, en orden: muestra, perdida medible, ahorra, no ahorra, no firme."""
    if n < N_MIN or pads < PADS_MIN or sum(c >= N_K for c in conteo_k.values()) < K_DISTINTOS:
        return "sin muestra"
    if not ab_ic_bajo > 0:
        return "sin perdida medible"
    if phi_ic_bajo > 0 and phi >= UMBRAL_FIJO:
        return "agrupar ahorra"
    if phi_ic_alto < UMBRAL_FIJO:
        return "agrupar no ahorra"
    return "no firme"


def _boot(e: dict, idx: np.ndarray, reps: int, semilla: int, fn) -> list:
    """fn(indices) en `reps` remuestras por pads hijo de la muestra idx."""
    grupos, rng = _clusters(e["clave"][idx]), np.random.default_rng(semilla)
    return [fn(idx[_remuestra(rng, grupos)]) for _ in range(reps)]


def _filas_ab(prueba: str, a: float, b: float, rep: np.ndarray, n: int, sufijo: str = "") -> tuple[list[tuple], dict]:
    """Filas de a, b, a + b y phi con su IC; rep es (reps, 2). Devuelve tambien phi, su IC y el IC de a + b."""
    ab_r = rep[:, 0] + rep[:, 1]
    ok = ab_r > 0
    phi_r = np.where(ok, rep[:, 0] / np.where(ok, ab_r, 1), np.nan)
    phi = _phi(a, b)
    r = {"phi": phi, "phi_ic": _ic(phi_r), "ab_ic": _ic(ab_r), "phi_r": phi_r, "rep": rep, "descartadas": int((~ok).sum())}
    filas = [(prueba, "a" + sufijo, a, *_ic(rep[:, 0]), n, None), (prueba, "b" + sufijo, b, *_ic(rep[:, 1]), n, None),
             (prueba, "a_mas_b" + sufijo, a + b, *r["ab_ic"], n, None), (prueba, "phi" + sufijo, phi, *r["phi_ic"], n, None)]
    return filas, r


def diagnostico(e: dict, idx: np.ndarray, ab: float, ab_r: np.ndarray, reps: int) -> list[tuple]:
    """Agregado despues de ver los resultados (no cambia el veredicto): la perdida media de los controles contra su propia
    trayectoria mediana, y a + b medido contra esa media en lugar de contra la mediana. IC de los controles por sus pads
    hijo (semilla SEMILLA_GOLPES + 2); el de a + b resta, repeticion a repeticion, las dos remuestras independientes."""
    ctrl = np.flatnonzero((e["banda"] == 2) & e["ventana"])
    media_c = float(e["perdida"][ctrl].mean())
    rep_c = np.array(_boot(e, ctrl, reps, SEMILLA_GOLPES + 2, lambda i: e["perdida"][i].mean()), dtype=float)
    return [("diagnostico", "perdida_media_control", media_c, *_ic(rep_c), len(ctrl), None),
            ("diagnostico", "perdida_mediana_control", float(np.median(e["perdida"][ctrl])), None, None, len(ctrl), None),
            ("diagnostico", "perdida_mediana", float(np.median(e["perdida"][idx])), None, None, len(idx), None),
            ("diagnostico", "desvio_perdida", float(np.std(e["perdida"][idx], ddof=1)), None, None, len(idx), None),
            ("diagnostico", "a_mas_b_contra_media_control", ab - media_c, *_ic(ab_r - rep_c), len(idx), None)]


def calcular(D: dict, reps: int = REPS_BOOT) -> dict[str, list[tuple]]:
    """Las dos tablas del modulo: la tabla por k y las pruebas (principal, S1, S2 y conteos)."""
    e = eventos(D)
    mu = muestras(e)
    idx = np.flatnonzero(mu["principal"])
    n = len(idx)
    k = e["k"][idx]
    pads, padres = len(set(e["clave"][idx].tolist())), len(set(e["padre"][idx].tolist()))
    conteo_k = {int(v): int((k == v).sum()) for v in np.unique(k)}
    prueba: list[tuple] = []
    filas_k: list[tuple] = []
    if n == 0:
        prueba.append(("principal", "phi", None, None, None, 0, "sin muestra"))
    else:
        a, b = ajuste(e, idx, e["perdida"])
        av, bv = ajuste(e, idx, e["vol"])
        th = ajuste_grupos(e, idx, e["perdida"])

        def una(i):
            return (*ajuste(e, i, e["perdida"]), *ajuste(e, i, e["vol"]), *ajuste_grupos(e, i, e["perdida"]))
        rep = np.array(_boot(e, idx, reps, SEMILLA_GOLPES, una), dtype=float)
        f, r = _filas_ab("principal", a, b, rep[:, :2], n)
        v = veredicto(n, pads, conteo_k, r["ab_ic"][0], r["phi"], *r["phi_ic"])
        f[3] = (*f[3][:6], v)
        prueba += f
        valido = r["phi_r"][np.isfinite(r["phi_r"])]
        prueba += [("principal", "error_phi", float(np.std(valido, ddof=1)) if len(valido) > 1 else None, None, None, len(valido), None),
                   ("principal", "descartadas", r["descartadas"], None, None, reps, None)]
        ab_r = rep[:, 0] + rep[:, 1]
        for kk in KS_RHO:
            rho_r = np.where(ab_r > 0, (rep[:, 0] + rep[:, 1] * kk) / (kk * np.where(ab_r > 0, ab_r, 1)), np.nan)
            prueba.append(("principal", f"rho_{kk}", _rho(a, b, kk), *_ic(rho_r), n, None))
        prueba += [("principal", "k_media", float(k.mean()), None, None, n, None),
                   ("principal", "perdida_media", float(e["perdida"][idx].mean()), None, None, n, None),
                   ("principal", "pads", pads, None, None, n, None), ("principal", "padres", padres, None, None, n, None),
                   ("principal", "valores_k_con_n_k", sum(c >= N_K for c in conteo_k.values()), None, None, len(conteo_k), None)]
        f1, _ = _filas_ab("S1", av, bv, rep[:, 2:4], n, "_m3")
        prueba += f1
        prueba += diagnostico(e, idx, a + b, ab_r, reps)
        g = _grupo_k(k)
        for gi, (etq, rg) in enumerate(zip(ETQ_GRUPO, rep[:, 4:].T)):
            en = g == gi
            if not en.any():
                filas_k.append((etq, gi, 0, 0, 0, None, None, None, None, None, None, None, None))
                continue
            km = float(k[en].mean())
            lo, hi = _ic(rg)
            filas_k.append((etq, gi, int(en.sum()), len(set(e["clave"][idx][en].tolist())), len(set(e["padre"][idx][en].tolist())),
                            km, _f(th[gi]), _f(lo), _f(hi), _f(th[gi] / km), _f(lo / km), _f(hi / km), a + b * km))
    i2 = np.flatnonzero(mu["S2"])
    if len(i2):
        a2, b2 = ajuste(e, i2, e["perdida"], EXTRA_S2)
        rep2 = np.array(_boot(e, i2, reps, SEMILLA_GOLPES + 1, lambda i: ajuste(e, i, e["perdida"], EXTRA_S2)), dtype=float)
        f2, _ = _filas_ab("S2", a2, b2, rep2, len(i2))
        prueba += f2 + [("S2", "pads", len(set(e["clave"][i2].tolist())), None, None, len(i2), None)]
    cerca = e["banda"] == 0
    prueba += [("conteo", "cercanos", int(cerca.sum()), None, None, None, None),
               ("conteo", "cercanos_con_ventana", int((cerca & e["ventana"]).sum()), None, None, None, None),
               ("conteo", "aislados_con_ventana", n, None, None, None, None),
               ("conteo", "controles_con_ventana", int(((e["banda"] == 2) & e["ventana"]).sum()), None, None, None, None),
               ("conteo", "un_hijo_aislados", conteo_k.get(1, 0), None, None, None, None)]
    prueba = [(p, s, _f(x) if x is not None else None, _f(lo), _f(hi), nn, vv) for p, s, x, lo, hi, nn, vv in prueba]
    return {mart(): filas_k, mart("_prueba"): prueba}


def escribir(con, t: dict[str, list[tuple]], cuenca: str = "") -> None:
    """Escribe las dos tablas con el nombre de la cuenca (Colorado tambien queda en el warehouse de Vaca Muerta).

    Una llamada por mart con el nombre escrito, que es lo que lee pipeline.linaje."""
    if not cuenca:
        _escribir(con, "mart_golpes_mismo_mes", COLS_K, t[mart()])
        _escribir(con, "mart_golpes_mismo_mes_prueba", COLS_PRUEBA, t[mart("_prueba")])
        return
    if cuenca != COLORADO.id:
        raise ValueError(f"golpes_mismo_mes no tiene adaptacion escrita para la cuenca {cuenca!r}: solo Vaca Muerta y Colorado")
    _escribir(con, "mart_golpes_mismo_mes_colorado", COLS_K, t[mart()])
    _escribir(con, "mart_golpes_mismo_mes_colorado_prueba", COLS_PRUEBA, t[mart("_prueba")])


def marts(con, cuenca: str = "") -> dict | None:
    """Las tablas de una cuenca (None si no se corrio): por k y pruebas."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?", [mart("_prueba", cuenca)]).fetchone()[0]:
        return None
    return {"k": con.execute(f"select * from {mart('', cuenca)} order by orden").fetchall(),
            "p": {(r[0], r[1]): r for r in con.execute(f"select * from {mart('_prueba', cuenca)}").fetchall()}}


# ------------------------------------------------------------------ pagina

FRASE = {
    "agrupar ahorra": "Un mes con varios hijos le cuesta al padre menos que los mismos hijos en meses separados: una parte de la "
                      "pérdida es fija por mes de golpe.",
    "agrupar no ahorra": "La pérdida crece con cada hijo casi como si cada uno tuviera su propio mes: agrupar no ahorra del lado del padre.",
    "no firme": "El intervalo de φ admite tanto un costo fijo por mes como uno por hijo: el dato no decide.",
    "sin muestra": "No hay eventos suficientes para aplicar la regla: el dato no decide.",
    "sin perdida medible": "La pérdida de un mes de golpe con un solo hijo no se distingue de cero, así que no hay nada medible que "
                           "ahorrar agrupando: el dato no decide.",
}
ETQ_VEREDICTO = {"sin perdida medible": "sin pérdida medible"}  # solo la grafia de la pagina; el mart guarda la de VEREDICTOS
FILAS_MODELO = (("principal", "Principal", "a", "a: costo fijo del mes (días de base)", 1),
                ("principal", "Principal", "b", "b: costo de cada hijo (días de base)", 1),
                ("principal", "Principal", "a_mas_b", "a + b: un mes con un solo hijo (días de base)", 1),
                ("principal", "Principal", "phi", "φ = a / (a + b)", 2),
                *(("principal", "Principal", f"rho_{k}", f"ρ con {k} hijos (juntos sobre separados)", 2) for k in KS_RHO),
                ("S1", "S1, volumen", "a_m3", "a (m3)", 0), ("S1", "S1, volumen", "b_m3", "b (m3)", 0),
                ("S1", "S1, volumen", "a_mas_b_m3", "a + b (m3)", 0), ("S1", "S1, volumen", "phi_m3", "φ en volumen", 2),
                ("S2", "S2, sin aislamiento", "a", "a (días de base)", 1), ("S2", "S2, sin aislamiento", "b", "b (días de base)", 1),
                ("S2", "S2, sin aislamiento", "a_mas_b", "a + b (días de base)", 1), ("S2", "S2, sin aislamiento", "phi", "φ", 2))
FILAS_CONTEO = (("cercanos", "Eventos cercanos (hijo más cercano a menos de 1 km)"),
                ("cercanos_con_ventana", "Con la ventana completa (muestra de S2)"),
                ("aislados_con_ventana", "Aislados con la ventana completa (muestra principal)"),
                ("un_hijo_aislados", "De ellos, con un solo hijo en el mes"),
                ("controles_con_ventana", "Controles con la ventana completa (índice de control)"))


def _ict(lo, hi, dec: int = 1) -> str:
    return f"{_g(lo, dec)} a {_g(hi, dec)}"


def _val(p: dict, prueba: str, est: str, dec: int = 1, unidad: str = "") -> str:
    """'valor unidad (IC 95% bajo a alto)' de una fila de la tabla de pruebas; n/d si no esta."""
    r = p.get((prueba, est))
    if r is None or r[2] is None:
        return "n/d"
    return f"{_g(r[2], dec)}{unidad}" + (f" (IC 95% {_ict(r[3], r[4], dec)})" if r[3] is not None else "")


def _num(p: dict, prueba: str, est: str, col: int = 2):
    r = p.get((prueba, est))
    return None if r is None else r[col]


def _tabla_k(filas: list[tuple]) -> list[str]:
    L = ["| Hijos a menos de 1 km en el mes | Eventos | Pads hijo | k media | Pérdida del mes (días de base) | IC 95% | Por hijo | "
         "IC 95% por hijo | Recta a + b k |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in filas:
        if not r[2]:
            L.append(f"| {r[0]} | 0 | 0 | | | | | | |")
            continue
        L.append(f"| {r[0]} | {_g(r[2])} | {_g(r[3])} | {_g(r[5], 1)} | {_g(r[6], 1)} | {_ict(r[7], r[8])} | {_g(r[9], 1)} | "
                 f"{_ict(r[10], r[11])} | {_g(r[12], 1)} |")
    return L


def _tabla_modelo(p: dict, pco: dict | None) -> list[str]:
    cab = "| Prueba | Estadístico | Vaca Muerta | IC 95% |" + (" Colorado | IC 95% |" if pco else "")
    L = [cab, "| --- | --- | ---: | ---: |" + (" ---: | ---: |" if pco else "")]
    for prueba, etq, est, desc, dec in FILAS_MODELO:
        celdas = []
        for q in (p, pco) if pco else (p,):
            r = q.get((prueba, est))
            celdas += ["n/d", ""] if r is None or r[2] is None else [_g(r[2], dec), _ict(r[3], r[4], dec) if r[3] is not None else ""]
        L.append(f"| {etq} | {desc} | " + " | ".join(celdas) + " |")
    return L


def _tabla_conteo(p: dict, pco: dict | None) -> list[str]:
    L = ["| Muestra | Vaca Muerta |" + (" Colorado |" if pco else ""), "| --- | ---: |" + (" ---: |" if pco else "")]
    filas = [(est, d, "conteo") for est, d in FILAS_CONTEO] + [("pads", "Pads hijo de la muestra principal", "principal"),
                                                              ("padres", "Padres de la muestra principal", "principal")]
    for est, desc, prueba in filas:
        L.append(f"| {desc} | {_g(_num(p, prueba, est))} |" + (f" {_g(_num(pco, prueba, est))} |" if pco else ""))
    vk = _num(p, "principal", "valores_k_con_n_k")
    if vk is not None:
        L.append(f"| Valores de k con al menos {N_K} eventos | {_g(vk)} |"
                 + (f" {_g(_num(pco, 'principal', 'valores_k_con_n_k'))} |" if pco else ""))
    return L


def _linea_veredicto(p: dict, nombre: str) -> str:
    v = _num(p, "principal", "phi", 6)
    linea = (f"- {nombre}: **{ETQ_VEREDICTO.get(v, v)}**. {FRASE.get(v, '')} Un mes con un solo hijo, a + b = "
             f"{_val(p, 'principal', 'a_mas_b', unidad=' días de producción de base')}; ")
    if v == "sin muestra":
        return linea + (f"{_g(_num(p, 'conteo', 'aislados_con_ventana'))} meses de golpe aislados con la ventana completa, de "
                        f"{_g(_num(p, 'principal', 'pads'))} pads hijo (la regla pide {_g(N_MIN)} y {_g(PADS_MIN)}).")
    return linea + (f"{_g(_num(p, 'conteo', 'aislados_con_ventana'))} meses de golpe aislados, de {_g(_num(p, 'principal', 'pads'))} "
                    f"pads hijo; φ = {_val(p, 'principal', 'phi', 2)}.")


def _variantes_con_perdida(p: dict, pco: dict | None) -> list[str]:
    """Las variantes (principal, S1, S2 de cada cuenca) cuyo IC de a + b queda por encima de cero, con su phi."""
    out = []
    for q, cuenca in ((p, "Vaca Muerta"), (pco, "Colorado")):
        if not q:
            continue
        for prueba, etq, suf in (("principal", "principal", ""), ("S1", "S1 (volumen)", "_m3"), ("S2", "S2 (sin aislamiento)", "")):
            lo = _num(q, prueba, "a_mas_b" + suf, 3)
            if lo is not None and lo > 0:
                out.append(f"{cuenca}, {etq}: φ = {_val(q, prueba, 'phi' + suf, 2)}")
    return out


def _phis(p: dict, pco: dict | None) -> list[float]:
    return [x for q in (p, pco) if q for x in (_num(q, "principal", "phi"), _num(q, "S1", "phi_m3"), _num(q, "S2", "phi"))
            if x is not None]


def _linea_optimizador(p: dict) -> str:
    v = _num(p, "principal", "phi", 6)
    a, b = _num(p, "principal", "a"), _num(p, "principal", "b")
    if v == "agrupar ahorra":
        return ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): el optimizador usa costo fijo más "
                "costo por hijo (a y b) por padre y mes, así que reagrupar hijos en un mismo mes tiene crédito.")
    if v == "agrupar no ahorra":
        return ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): el optimizador usa un costo aditivo "
                "por hijo; agrupar no tiene crédito del lado del padre.")
    linea = ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): con este veredicto el optimizador corre "
             f"los dos casos y publica el arrepentimiento con cada uno, costo aditivo por hijo y costo fijo más costo por hijo con la "
             f"estimación puntual (a = {_g(a, 1)} y b = {_g(b, 1)} días de base).")
    if b is not None and b < 0:
        linea += (" La estimación puntual de b es negativa y su IC incluye el cero: un hijo de más no puede restarle pérdida al padre, "
                  "así que esa unidad tiene que decir cómo acota b antes de usarla.")
    return linea


def _seccion_valor(p: dict) -> list[str]:
    L = ["", "## Cuánto vale", ""]
    if _num(p, "principal", "phi", 6) != "agrupar ahorra":
        return L + ["El veredicto de Vaca Muerta no es «agrupar ahorra», así que no hay ahorro que valuar: la regla fija que el valor en "
                    "dinero se publica solo con ese veredicto."]
    a = _num(p, "S1", "a_m3")
    L += [f"Cada hijo que se suma a un mes de golpe en lugar de ir a su propio mes le ahorra al padre a = {_g(a)} m3 ({_g(a * BBL_M3)} "
          "barriles) de volumen diferido (S1). La tabla da el costo de diferir ese volumen (el valor tiempo de cobrarlo más tarde), en "
          "dólares por hijo agrupado, según cuánto tarde en recuperarse. Precio y tasa son entradas de quien lo usa, no resultados.", "",
          "| Precio (USD/bbl) | Tasa anual | " + " | ".join(f"Se recupera en {z} meses" for z in REZAGOS) + " |",
          "| ---: | ---: |" + " ---: |" * len(REZAGOS)]
    for precio in PRECIOS:
        for tasa in TASAS:
            L.append(f"| {precio} | {_g(100 * tasa)}% | "
                     + " | ".join(_g(valor_indicativo(a, precio, tasa, z)["costo_de_diferir"]) for z in REZAGOS) + " |")
    return L


def pagina_golpes_mismo_mes(con) -> str:
    """Pagina de la wiki a partir de los marts (solo lee); la seccion de Colorado solo si se corrio."""
    vm, co = marts(con), marts(con, COLORADO.id)
    p, pco = vm["p"], (co["p"] if co else None)
    v = _num(p, "principal", "phi", 6)
    L = ["# Golpes en el mismo mes: si agrupar hijos le cuesta menos al padre", "",
         f"Cuando se fracturan varios hijos a menos de {_g(KM_CERCA)} km de un padre en el mismo mes, ¿le cuesta al padre menos que si esos "
         "mismos hijos se fracturaran en meses separados? Si una parte de la pérdida es fija por mes de golpe, agrupar ahorra esa parte "
         "por cada hijo que se suma; si es toda por hijo, agrupar no ahorra nada del lado del padre. Es la primera pieza del optimizador de "
         "calendario. La regla se fijó antes de calcular; en Vaca Muerta es de regla informada (un coeficiente de costo por hijo ya se "
         "había visto) y en Colorado es confirmatoria.", "",
         "## Lectura", "",
         _linea_veredicto(p, "Vaca Muerta (regla informada)")]
    if v in ("sin perdida medible", "no firme") and _num(p, "diagnostico", "desvio_perdida") is not None:
        L.append(f"- Por qué no decide: la pérdida de un mes de golpe varía mucho de un evento a otro. En la muestra principal de Vaca Muerta "
                 f"el desvío es de {_g(_num(p, 'diagnostico', 'desvio_perdida'), 1)} días contra una media de "
                 f"{_g(_num(p, 'principal', 'perdida_media'), 1)} y una mediana de {_g(_num(p, 'diagnostico', 'perdida_mediana'), 1)}.")
    if pco:
        L.append(_linea_veredicto(pco, "Colorado (confirmatoria, misma regla)"))
    con_perdida, phis = _variantes_con_perdida(p, pco), _phis(p, pco)
    if con_perdida:
        L.append("- Las sensibilidades no cambian el veredicto. Las variantes en las que un mes con un solo hijo sí tiene una pérdida "
                 "distinta de cero: " + "; ".join(con_perdida) + ".")
    if phis:
        forma = ("si hay una pérdida, el punto la pone casi toda en el mes de golpe y no en cada hijo" if min(phis) >= 0.75 else
                 "si hay una pérdida, el punto la pone casi toda en cada hijo" if max(phis) <= UMBRAL_FIJO else
                 "el punto no señala una forma")
        L.append(f"- La estimación puntual de φ va de {_g(min(phis), 2)} a {_g(max(phis), 2)} en las {len(phis)} variantes "
                 f"(principal, S1 y S2{' de las dos cuencas' if pco else ''}): {forma}. Es una estimación puntual, no un veredicto.")
    L.append(_linea_optimizador(p))
    ab_m = _num(p, "diagnostico", "a_mas_b_contra_media_control")
    if ab_m is not None:
        L.append("- Agregado después de ver, sin cambiar el veredicto: contra la media de los controles en lugar de su mediana, a + b sería "
                 f"{_val(p, 'diagnostico', 'a_mas_b_contra_media_control', unidad=' días')} en Vaca Muerta"
                 + (f" y {_val(pco, 'diagnostico', 'a_mas_b_contra_media_control', unidad=' días')} en Colorado" if pco else "")
                 + ". La sección «Diagnóstico» dice por qué se publica.")
    L += ["", "## El modelo: costo fijo del mes y costo por hijo", "",
          "Mínimos cuadrados de la pérdida del mes de golpe P (días de producción de base, meses "
          f"{VENTANA[0]} a {VENTANA[1]} contra el índice mediano de los controles) sobre la cantidad k de hijos a menos de "
          f"{_g(KM_CERCA)} km fracturados ese mes: P = a + b k, con la distancia de los hijos, los hijos de {_g(KM_CERCA)} a {_g(KM_K12)} km "
          "del mismo mes, el caudal de base y efectos fijos de edad del padre, año y operador como controles. a es lo que cuesta el mes "
          "de golpe sin importar cuántos hijos traiga; b, cada hijo. Juntos, k hijos cuestan a + b k; separados, k (a + b). "
          "φ = a / (a + b) es la parte fija del costo de un mes con un solo hijo, y ρ es el costo de k hijos juntos sobre el de los "
          "mismos k separados.", "", *_tabla_modelo(p, pco), "",
          f"Los IC son de percentiles por pads hijo ({_g(_num(p, 'principal', 'descartadas', 5))} repeticiones). Para φ y ρ se descartan las "
          f"repeticiones con a + b de cero o menos: {_g(_num(p, 'principal', 'descartadas'))} en Vaca Muerta"
          + (f" y {_g(_num(pco, 'principal', 'descartadas'))} en Colorado" if pco else "")
          + f". Error de φ (desvío de las repeticiones) en Vaca Muerta: {_g(_num(p, 'principal', 'error_phi'), 2)}. "
          "S1 mide lo mismo en volumen (P por el caudal de base). S2 suma los cercanos que no están aislados y controla por los hijos a "
          f"menos de {_g(KM_AISLADO)} km de los {MESES_AISLADO} meses de antes y de después.",
          "", "## Pérdida por cantidad de hijos en el mes", "",
          "El mismo modelo con un efecto fijo por grupo de k en lugar de la recta: la pérdida ajustada de un mes de cada grupo, sin el "
          "supuesto lineal. Es descriptiva. La última columna es la recta a + b k en la k media del grupo.", "", *_tabla_k(vm["k"])]
    L += _seccion_valor(p)
    L += ["", "## Muestra", "", *_tabla_conteo(p, pco)]
    if ab_m is not None:
        L += ["", "## Diagnóstico (agregado después de ver; no cambia el veredicto)", "",
              "La regla mide la pérdida contra la mediana del índice de los controles, mes a mes. La pérdida de los propios controles contra "
              f"esa mediana tiene media {_val(p, 'diagnostico', 'perdida_media_control', unidad=' días')} en Vaca Muerta"
              + (f" y {_val(pco, 'diagnostico', 'perdida_media_control', unidad=' días')} en Colorado" if pco else "")
              + ", con mediana cerca de cero: algunos controles suben mucho y la media de los controles queda por encima de su mediana. "
              "Contra esa media, a + b sería " + _val(p, "diagnostico", "a_mas_b_contra_media_control", unidad=" días") + " en Vaca Muerta"
              + (f" y {_val(pco, 'diagnostico', 'a_mas_b_contra_media_control', unidad=' días')} en Colorado" if pco else "")
              + " (el IC resta, repetición a repetición, dos remuestras independientes por pads). Se publica para que se vea cuánto pesa "
              "esa elección. Elegir la referencia después de ver sería aflojar la regla, así que el veredicto queda como está."]
    if co:
        L += ["", "## Colorado (confirmatoria)", "",
              "La misma regla, con las adaptaciones de pipeline.dias_perdidos a Colorado (padres horizontales, hijos con la fecha de inicio "
              "de FracFocus, el operador del último mes informado y un grupo de edad propio para los padres con el primer petróleo "
              "censurado). En Colorado no se había mirado ninguna pérdida con varios hijos en el mes antes de fijar la regla.", "",
              _linea_veredicto(pco, "Veredicto"), "", *_tabla_k(co["k"])]
    L += ["", "## Regla fijada antes de correr", "",
          "- La regla está en el encabezado de `pipeline/golpes_mismo_mes.py`, en un commit que solo trae el encabezado y las constantes, "
          "anterior a cualquier cálculo de este módulo. No se cambió después de ver los resultados.",
          f"- Veredicto, en orden: «sin muestra» con menos de {_g(N_MIN)} eventos, de {_g(PADS_MIN)} pads hijo o de {K_DISTINTOS} valores "
          f"de k con al menos {N_K} eventos; «sin pérdida medible» si el límite bajo del IC de a + b no pasa de cero; «agrupar ahorra» si "
          f"el límite bajo del IC de φ es mayor que cero y φ es de al menos {_g(UMBRAL_FIJO, 2)}; «agrupar no ahorra» si el límite alto "
          f"del IC de φ es menor que {_g(UMBRAL_FIJO, 2)}; «no firme» en otro caso.",
          "- Qué se había mirado antes en Vaca Muerta: el coeficiente de hijos a menos de 1 km del modelo de costo por evento "
          "(pipeline.costo), el diferido por evento cercano y los conteos de eventos por k, sin ninguna pérdida. Por eso Vaca Muerta es "
          "de regla informada y Colorado es confirmatoria.",
          "- Lo único agregado después de ver es la sección «Diagnóstico», que no cambia ningún veredicto.",
          "- Aclaraciones posteriores, sin cambiar la regla, el código ni ninguna cifra: placebo.marco, que la regla nombra, también pide "
          f"que la base original (meses {BASE_ORIGINAL[0]} a {BASE_ORIGINAL[1]}) dé más de 1 m3/d, y los conteos ya la incluyen; y con la "
          f"ventana de {VENTANA[0]} a {VENTANA[1]}, dos hijos a 7 meses de distancia comparten un mes de ventana (el {VENTANA[1]} del "
          f"primero es el {VENTANA[0]} del segundo).",
          "- La distancia entre ramas (pipeline.trayectorias) no se usa: la prueba queda en distancia de superficie, como el resto del "
          "estudio.", "",
          "## Qué no prueba", "",
          "- Con dato mensual, «el mismo mes» no es «al mismo tiempo»: dos hijos del mismo mes pueden fracturarse con semanas de diferencia.",
          "- Los hijos de un mismo mes son casi siempre del mismo pad: la comparación es entre pads de distinto tamaño tanto como entre "
          "calendarios. Los controles cubren el operador y la época, no el diseño.",
          "- La recta en k es un supuesto; la tabla por k muestra la forma sin ella.",
          "- La pérdida es volumen diferido contra la trayectoria de los controles en los meses -1 a 6: no dice que ese petróleo se pierda.",
          "- Solo el lado del padre: lo que pierde el hijo por la depleción del padre no está en la prueba.",
          "- Un padre en medio de un desarrollo continuo no entra en la muestra principal; S2 lo incluye.",
          f"- El aislamiento mira {MESES_AISLADO} meses hacia atrás y la base son los meses {BASE[0]} a {BASE[1]}: un hijo a menos de "
          f"{_g(KM_AISLADO)} km fracturado más de {MESES_AISLADO} meses antes todavía puede caer con su golpe sobre la base del evento, y "
          "eso no se descarta.", ""]
    return "\n".join(L)


def cargar(con) -> dict:
    """Vaca Muerta: los cargadores de pipeline.dias_perdidos (placebo.cargar, descomposicion.cargar_ext y cargar_dias)."""
    return dias_perdidos.cargar_dias(con, descomposicion.cargar_ext(con, placebo.cargar(con)))


def _resumen(t: dict, nombre: str) -> None:
    p = {(f[0], f[1]): f for f in t[mart("_prueba")]}
    f = p[("principal", "phi")]
    print(f"[{nombre}] phi {f[2]} (IC {f[3]} a {f[4]}; n {f[5]}): {f[6]}")


def main(path=DATA / "warehouse.duckdb", cuenca: Cuenca | None = None, reps: int = REPS_BOOT) -> None:
    """Vaca Muerta sobre su warehouse; con `cuenca`, esa cuenca sobre el suyo (solo lectura) y las tablas en el de Vaca Muerta."""
    if cuenca is None:
        con = duckdb.connect(str(path))
        t = calcular(cargar(con), reps)
        escribir(con, t)
        con.close()
        _resumen(t, "golpes_mismo_mes")
        return
    if cuenca.id != COLORADO.id:
        raise ValueError(f"golpes_mismo_mes no tiene adaptacion escrita para la cuenca {cuenca.id!r}: solo Vaca Muerta y Colorado")
    con_c = duckdb.connect(str(cuenca.db), read_only=True)
    try:
        t = calcular(dias_perdidos.cargar_cuenca(con_c), reps)
    finally:
        con_c.close()
    con = duckdb.connect(str(path))
    escribir(con, t, cuenca.id)
    con.close()
    _resumen(t, f"golpes_mismo_mes {cuenca.id}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="pipeline.golpes_mismo_mes")
    ap.add_argument("--cuenca", help="id de una cuenca de la replicacion (pipeline/cuencas.py); sin argumento, Vaca Muerta")
    a = ap.parse_args()
    main(cuenca=_cuenca(a.cuenca) if a.cuenca else None)
