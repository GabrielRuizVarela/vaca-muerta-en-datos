"""Calendario de golpes: matrices de costo, optimizador de calendario y backtest (ajustado en 2023, predice 2024 a 2026).

Se corre despues de pipeline.golpes_mismo_padre:  uv run python -m pipeline.calendario_golpes

Para que sirve. Es la tercera y ultima pieza del optimizador de calendario (U6b de la fase 4). pipeline.golpes_mismo_mes (PR #83)
midio cuanto pierde un padre en un mes de golpe, P = a + b k, y no pudo decidir si agrupar hijos ahorra; pipeline.golpes_mismo_padre
(PR #86, U6a) comparo cada padre consigo mismo y termino en "sin muestra" en las dos cuencas (87 padres y 197 meses de golpe en
Vaca Muerta, 19 y 38 en Colorado). Como U6a no decidio un caso de costo, queda lo ultimo publicado, el modelo agrupado de #83
(a = 13,9 y b = -1,7 dias de base en Vaca Muerta, con b negativo y un IC que incluye el cero), y esta unidad corre los DOS casos
de costo, los valua con la grilla de pipeline.decision (PRECIOS, TASAS, REZAGOS) y mide si el modelo, ajustado en 2023, predice la
perdida de 2024 a 2026. Antes de usar b lo acota a 0 o mas.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no. Un "no firme" o un "sin
muestra" es un resultado terminado: no se rediseña la regla para evitarlo.

Huecos del plan que esta regla cierra antes de calcular (el plan dice solo "matrices de costo valuadas en PRECIOS/TASAS/REZAGOS,
bajo los dos casos, y un backtest ajustado en 2023 que predice 2024 a 2026, con b acotado a 0 o mas"; no dice que elige el
optimizador, contra que se compara el arrepentimiento ni como se puntua el backtest ni con que umbrales). Se fijan aqui:
  1. Que elige el optimizador: para cada padre, en que meses de calendario caen los hijos que se fracturan a menos de 1 km de el.
  2. Contra que se compara el arrepentimiento: contra el calendario realmente observado de ese padre.
  3. Como se puntua el backtest, y con que umbrales sale el veredicto.
  4. Como se acota b, y que se hace con a.
  5. Que no se corre Colorado (ver abajo).

Que se habia mirado antes de fijarla
- Todo lo publicado de #83 y #86 en las dos cuencas: los coeficientes agrupados, sus IC, el veredicto "sin perdida medible" de #83, el
  "sin muestra" de #86 y sus conteos de padres y meses de golpe.
- NO se habia calculado ninguna cantidad de esta prueba: ni cuantos meses de golpe aislados hay en 2023 ni en 2024 a 2026, ni
  ningun calendario, ni ningun arrepentimiento, ni ningun puntaje fuera de muestra. El tamaño de las muestras de entrenamiento y
  de prueba se ve por primera vez cuando corre el modulo, y puede ser "sin muestra". Por eso es una prueba de regla informada en
  el sentido de #81 y #83 solo en lo que ya estaba publicado (el a y el b agrupados); el backtest es nuevo.

Que se reutiliza (de pipeline.golpes_mismo_mes y pipeline.golpes_mismo_padre, sin copiar)
- Los eventos, la perdida P (dias de produccion de base, meses -1 a 6 contra el indice mediano de los controles), el volumen
  V = P por el caudal de base (m3), k (hijos a menos de KM_CERCA fracturados ese mes), el aislamiento y la ventana completa: las
  definiciones de golpes_mismo_mes.eventos y golpes_mismo_mes.muestras, tal cual. El pad del padre es el de
  golpes_mismo_padre.cargar_pad_padre. La grilla de valor es la de pipeline.decision (PRECIOS, TASAS, REZAGOS) con
  decision.valor_indicativo, sin tocarla.
- Muestra de ajuste y de prueba del backtest: la muestra PRINCIPAL de #83 (cercanos aislados con la ventana completa). Entrenamiento:
  eventos cuyo mes de fractura cae en ANIO_ENTRENA (2023). Prueba: eventos cuyo mes de fractura cae en ANIOS_PRUEBA (2024 a 2026;
  con el dato a 2026-10 y la ventana completa, los ultimos hijos son de 2026-04). Es una partida por fecha, no al azar.

Los dos casos de costo (modelos de la perdida P de un mes de golpe con k hijos cercanos; los dos se ajustan en la muestra de
entrenamiento y los dos se acotan antes de usarlos)
- Caso ADITIVO, P = c k: el costo es por hijo y no depende de como se reparten los hijos en meses. c es de minimos cuadrados por el
  origen (c = suma(k P) / suma(k^2)); si sale menor que cero se acota en 0. Bajo este caso el calendario no cambia el costo
  total: el arrepentimiento es cero por construccion y la pagina lo dice, no lo presenta como un resultado.
- Caso FIJO MAS HIJO, P = a + b k: un costo fijo a por mes de golpe y b por hijo. Se acota asi, en este orden: (i) minimos
  cuadrados (a, b) sin controles; (ii) si b < 0, b = 0 y a se vuelve a ajustar sin k (a = media de P en la muestra de
  entrenamiento); (iii) si a < 0, a = 0. El b sin acotar y si el acotado se uso se publican. Un a o un b acotado es una
  decision de la regla, no una estimacion; la pagina lo rotula. Con b = 0 todos los hijos de un mes de golpe cuestan lo mismo que
  uno solo (phi = 1), el extremo de mas ahorro por agrupar.
- Referencia del backtest, que no es un caso de costo: M0, la media de P en la muestra de entrenamiento.
- Sin controles en el modelo principal (la decision solo mueve k). Sensibilidad S1, "con controles": los dos casos con k12 y el
  logaritmo del caudal de base de #83 como controles, centrados en la media de entrenamiento y sin efectos fijos (el año es uno solo
  en el entrenamiento, y las categorias de edad y operador de la prueba pueden no estar en el). Se publica; no cambia el veredicto.
- Descriptivo con la muestra completa: el modelo agrupado de #83 tal cual (golpes_mismo_mes.ajuste: con S, controles y efectos fijos
  de edad, año y operador, sobre toda la muestra principal 2016 a 2026), acotado con el mismo orden de pasos, y su caso aditivo
  (la misma especificacion con k sin constante). Valua el calendario observado de toda la muestra. Es dentro de muestra: no
  puntua nada y no entra en el veredicto. Debe reproducir el a y el b publicados de #83 antes de acotar, y si no lo hace el modulo falla.

Calendarios y optimizador
- Programa de un padre: los meses de golpe de ese padre (los eventos de la muestra de S2 de #83: cercanos con la ventana completa,
  aislados o no) con su k de cada mes. K es la suma de los k de sus meses. Para el backtest, solo los meses de golpe del periodo de
  prueba; para el descriptivo, todos.
- Calendario observado: los meses de golpe tal como ocurrieron. Costo de un calendario = suma sobre sus meses de f(k_mes), con
  f(k) = c k en el caso aditivo y f(k) = a + b k en el fijo mas hijo. SUPUESTO: el costo de un calendario es la suma de los
  costos de sus meses; los modelos se ajustaron en meses aislados, y dos meses de golpe a menos de 7 meses de distancia
  comparten ventana, asi que la suma no esta medida donde hay meses cercanos entre si. La pagina cuenta que parte de los meses
  del programa no esta aislada.
- Que elige el optimizador: a cada hijo se le permite moverse hasta DELTA_MESES meses (hacia antes o hacia despues) respecto de su mes
  observado, y el optimizador elige los meses de fractura para que el calendario tenga el menor costo del caso. Con a >= 0 y
  b >= 0, y como la suma de b k es la misma para cualquier calendario (K no cambia), eso es usar la menor cantidad de meses:
  se resuelve exacto agrupando los meses observados, de menor a mayor, mientras el primero y el ultimo del grupo esten a no mas
  de 2 DELTA_MESES de distancia; cada grupo cae en un mes y suma sus k. Sin tope de hijos por mes: el modelo esta respaldado
  hasta k = K_RESPALDADO (6, la tabla por k de #83) y la pagina da la parte de los meses del calendario optimo con k mayor, que es
  una extrapolacion. DELTA_MESES es una ENTRADA, como el precio: no sale del dato. Se publican tambien DELTAS_SENS; el
  veredicto usa solo DELTA_MESES. El valor del tiempo de los hijos que se mueven (producirian antes o despues) no esta en la
  prueba: es solo el lado del padre.
- Arrepentimiento = costo del calendario observado menos costo del calendario optimo del mismo caso, en dias de base, por programa;
  es cero o mas. Se valua en volumen con el caudal de base medio del padre (la media del caudal de base de sus eventos del
  programa): m3 = dias por ese caudal, y en dolares con decision.valor_indicativo(m3, precio, tasa, rezago)["costo_de_diferir"]
  en cada celda de PRECIOS por TASAS por REZAGOS (18 celdas, entradas ilustrativas, no pronostico), mas la celda central
  PRECIO_CENTRAL, TASA_CENTRAL, REZAGO_CENTRAL. El veredicto no depende de la celda. Se publica tambien el
  costo del calendario "todo separado" (cada hijo en su propio mes) para que se vea cuanto de ese costo ya evito la practica.
- Matrices de costo publicadas: (1) por k = KS_MATRIZ y por caso, la perdida P(k) de un mes en dias de base, la de k hijos
  juntos contra los mismos k separados y su razon rho; (2) por calendario (observado, optimo, todo separado), caso y celda de la
  grilla, el costo en m3 y en dolares, total y por padre; (3) el arrepentimiento por caso, por DELTA y por celda.

Backtest (el veredicto sale de el)
- Ajuste en la muestra de entrenamiento; prediccion en cada evento de la muestra de prueba con su k: P_hat = c k (aditivo),
  a + b k (fijo mas hijo), media de entrenamiento (M0). Puntaje: el error cuadratico medio fuera de muestra. Habilidad de un
  modelo X contra M0: SK_X = 1 - ECM_X / ECM_M0. Estadistico principal: D = SK_fijo - SK_aditivo = (ECM_aditivo - ECM_fijo) / ECM_M0;
  D > 0 dice que el modelo con costo fijo por mes predice 2024 a 2026 mejor que el aditivo. Se publican SK_fijo, SK_aditivo y D
  con su IC, el error absoluto medio de cada uno y la tabla por k de lo predicho contra lo observado en la prueba.
- IC 95% de percentiles. El conglomerado del bootstrap es el pad del padre (todos los padres de un pad, con todos sus meses, se
  mueven juntos, y un pad remuestreado cuenta como nuevo): un programa es de un padre y tiene que moverse entero, y el bootstrap
  espacial de 5 km de pipeline.bloques parte los programas entre los pads hijo de un mismo padre. Cada repeticion remuestrea los
  pads del padre de TODA la muestra (entrenamiento y prueba juntos), vuelve a ajustar los dos casos en el entrenamiento
  remuestreado, los puntua en la prueba remuestreada y vuelve a calcular los arrepentimientos. REPS_BOOT repeticiones, semilla
  SEMILLA_CALENDARIO. Las repeticiones con ECM_M0 igual a cero se descartan y se cuentan; tambien se cuentan las repeticiones en que
  se uso el b acotado.
- Veredicto, en este orden:
  1. "sin muestra": menos de N_ENTRENA_MIN eventos o de PADS_ENTRENA_MIN pads del padre en el entrenamiento, o menos de
     K_ENTRENA_DISTINTOS valores de k con al menos N_K_ENTRENA eventos cada uno en el entrenamiento, o menos de N_PRUEBA_MIN eventos
     o de PADS_PRUEBA_MIN pads del padre en la prueba. La pagina da los conteos, y en ese caso no se publica ningun otro veredicto
     (las cifras del backtest se publican como descriptivas).
  2. "costo aditivo": el limite alto del IC de D es menor que cero: el modelo aditivo predice mejor que el de costo fijo, y agrupar
     no ahorra del lado del padre.
  3. "sostiene": el limite bajo del IC de D es mayor que cero Y el limite bajo del IC del arrepentimiento del caso fijo mas hijo
     (dias de base, DELTA_MESES, padres del periodo de prueba, ajuste de 2023) es mayor que cero: el costo fijo por mes predice mejor
     que el aditivo y el ahorro del calendario optimo es medible. No es "agrupar ahorra" de #83: es una prueba fuera de muestra.
  4. "no firme": en otro caso. La pagina da los IC y dice que el dato no decide.
  El veredicto no depende de la grilla de precios.
- Que dice cada veredicto (en la pagina): "sostiene": el calendario optimo se publica como recomendacion con su ahorro y la cota
  de que es del lado del padre, con el b acotado y la suposicion de aditividad por mes dichos al lado; "costo aditivo": el
  calendario no se mueve, y se dice que mover hijos entre meses no baja la perdida del padre; "no firme" y "sin muestra": se
  publican las matrices y el arrepentimiento como lo que dice el modelo acotado (una cota de lo que podria ahorrar si el costo fijo
  fuera real), no como una estimacion, y la pagina dice que el dato no decide.

Colorado: no se corre. El warehouse de Colorado termina en 2024-12 y el backtest pide predecir 2024 a 2026 desde 2023; con #86 en
"sin muestra" en las dos cuencas no hay un resultado de Colorado que confirmar aqui, y correr una variante recortada seria una
prueba distinta que no se fijo.

Que NO prueba
- Con dato mensual "el mismo mes" no es "al mismo tiempo", y un hijo que se mueve DELTA_MESES meses no es un hijo que se mueve en
  la practica: hay que perforar, fracturar y completar en un orden que el dato publico no ve. El optimizador no tiene tope de
  hijos ni de equipos por mes.
- Solo el lado del padre: el costo de producir un hijo antes o despues, y lo que el hijo pierde por el padre, no esta en la prueba.
- La perdida es volumen diferido contra la trayectoria de los controles en la ventana, no dice que se pierda: el valor en
  dolares es el costo del valor tiempo de cobrar ese volumen mas tarde (decision.valor_indicativo), no un ingreso perdido, y los
  precios y las tasas son entradas, no pronosticos.
- La referencia de la perdida (la mediana de los controles) usa los controles de toda la muestra, incluidos los de 2024 a 2026: la
  referencia no es del todo fuera de muestra; el modelo, que es lo que se ajusta y se predice, si lo es.
- Un solo año de entrenamiento: los coeficientes de 2023 pueden no valer para 2024 a 2026 (cambia la operacion, los pads, los
  espaciamientos), y el IC no mide eso, mide el ruido del muestreo.
- b acotado en cero es una decision, no un dato: con b = 0 el modelo pone toda la perdida en el mes y no en cada hijo, el extremo
  de mas ahorro por agrupar. El arrepentimiento con b acotado es una cota superior de lo que el modelo agrupado podria ahorrar, no
  una estimacion.
"""
from __future__ import annotations

from pipeline import golpes_mismo_mes as gm
from pipeline.decision import PRECIOS, REZAGOS, TASAS
from pipeline.placebo import REPS_BOOT

# Heredadas de pipeline.golpes_mismo_mes y pipeline.decision, sin cambiarlas
KM_CERCA = gm.KM_CERCA            # km: hijos que cuentan en k
VENTANA = gm.VENTANA              # meses de la perdida del evento (-1 a 6)
MESES_AISLADO = gm.MESES_AISLADO  # meses a cada lado sin otros hijos dentro de KM_AISLADO (la ventana de un golpe)
GRILLA_PRECIOS = PRECIOS          # (40, 60, 80) USD por barril, entradas ilustrativas
GRILLA_TASAS = TASAS              # (0,10, 0,15) por año
GRILLA_REZAGOS = REZAGOS          # (6, 12, 24) meses de cobro mas tarde
REPS = REPS_BOOT                  # repeticiones del bootstrap, las de todo el estudio

# Backtest
ANIO_ENTRENA = 2023               # año de fractura de los hijos de la muestra de ajuste
ANIOS_PRUEBA = (2024, 2026)       # años de fractura de la muestra de prueba (extremos incluidos)
N_ENTRENA_MIN = 100               # eventos aislados del entrenamiento para decidir
PADS_ENTRENA_MIN = 20             # pads del padre del entrenamiento
K_ENTRENA_DISTINTOS = 3           # valores de k con al menos N_K_ENTRENA eventos en el entrenamiento
N_K_ENTRENA = 10
N_PRUEBA_MIN = 150                # eventos aislados de la prueba para decidir
PADS_PRUEBA_MIN = 30              # pads del padre de la prueba
SEMILLA_CALENDARIO = gm.SEMILLA + 90  # semilla del bootstrap por pads del padre (#83: +70; #86: +80)

# Optimizador
DELTA_MESES = 3                   # meses que puede moverse un hijo (entrada del optimizador, no sale del dato)
DELTAS_SENS = (1, 2, 6)           # sensibilidades del DELTA, publicadas; el veredicto usa solo DELTA_MESES
K_RESPALDADO = 6                  # k hasta el que la tabla por k de #83 respalda el modelo
KS_MATRIZ = (1, 2, 3, 4, 5, 6)    # k de la matriz de costo por k
PRECIO_CENTRAL = 60               # celda central de la grilla de valor (USD por barril)
TASA_CENTRAL = 0.10               # por año
REZAGO_CENTRAL = 12               # meses

CASOS = ("aditivo", "fijo_mas_hijo")
CALENDARIOS = ("observado", "optimo", "separado")
VEREDICTOS = ("sostiene", "costo aditivo", "no firme", "sin muestra")

# ------------------------------------------------------------------ imports (agregados abajo de las constantes)

import math

import duckdb
import numpy as np

from pipeline import golpes_mismo_padre as gp
from pipeline.costo import _clusters, _escribir
from pipeline.decision import valor_indicativo
from pipeline.dias_perdidos import _f
from pipeline.ingest import DATA
from pipeline.placebo import _g

# Columnas de las tablas que escribe el modulo
COLS_K = [("grupo", "varchar"), ("orden", "integer"), ("n", "integer"), ("k_media", "double"),
          ("p_observada", "double"), ("p_m0", "double"), ("p_aditivo", "double"), ("p_fijo", "double")]
COLS_COSTO_K = [("ajuste", "varchar"), ("caso", "varchar"), ("k", "integer"), ("perdida_dias", "double"),
                ("separados_dias", "double"), ("rho", "double")]
COLS_MATRIZ = [("ajuste", "varchar"), ("caso", "varchar"), ("calendario", "varchar"), ("delta", "integer"),
               ("precio", "double"), ("tasa", "double"), ("rezago", "integer"), ("padres", "integer"),
               ("dias", "double"), ("m3", "double"), ("usd", "double"), ("usd_por_padre", "double"),
               ("usd_ic_bajo", "double"), ("usd_ic_alto", "double")]

NAN = math.nan


# ------------------------------------------------------------------ funciones puras

def _indices(x) -> np.ndarray:
    """Los indices de las filas seleccionadas: acepta una mascara booleana o un arreglo de indices."""
    x = np.asarray(x)
    return np.flatnonzero(x) if x.dtype == bool else x.astype(np.int64)


def calendario_optimo(meses, k, delta):
    """Los meses de calendario optimos de un padre: la menor cantidad de meses posible.

    Un grupo arranca en el primer mes sin agrupar y toma todos los meses siguientes que estan a no mas de
    2*delta de distancia del primero; el grupo cae en el mes inicial mas delta y suma los k de sus meses."""
    meses = np.asarray(meses, dtype=np.int64)
    k = np.asarray(k, dtype=float)
    if not len(meses):
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=float)
    u, inv = np.unique(meses, return_inverse=True)
    ks = np.bincount(inv, weights=k, minlength=len(u))
    meses_out: list[int] = []
    k_out: list[float] = []
    i = 0
    while i < len(u):
        m0 = int(u[i])
        j = i
        while j + 1 < len(u) and int(u[j + 1]) - m0 <= 2 * int(delta):
            j += 1
        meses_out.append(m0 + int(delta))
        k_out.append(float(ks[i:j + 1].sum()))
        i = j + 1
    return np.asarray(meses_out, dtype=np.int64), np.asarray(k_out, dtype=float)


def ajuste_aditivo(k, p):
    """El caso aditivo: P = c k por minimos cuadrados por el origen, con c acotado en 0."""
    k = np.asarray(k, dtype=float)
    p = np.asarray(p, dtype=float)
    if not len(k):
        return 0.0
    den = float(np.sum(k * k))
    if den <= 0:
        return 0.0
    c = float(np.sum(k * p) / den)
    return c if c > 0 else 0.0


def _acota(a: float, b: float, p: np.ndarray) -> dict:
    """Acota (a, b) en el orden del encabezado: si b < 0, b = 0 y a = media de P; si a < 0, a = 0."""
    b_sin_acotar = float(b)
    acotado_b = False
    a = float(a)
    b = float(b)
    if b < 0:
        b = 0.0
        a = float(np.mean(p)) if len(p) else 0.0
        acotado_b = True
    acotado_a = False
    if a < 0:
        a = 0.0
        acotado_a = True
    return {"a": a, "b": b, "b_sin_acotar": b_sin_acotar, "acotado_b": acotado_b, "acotado_a": acotado_a}


def ajuste_fijo(k, p) -> dict:
    """El caso fijo mas hijo: P = a + b k, acotado en el orden del encabezado."""
    k = np.asarray(k, dtype=float)
    p = np.asarray(p, dtype=float)
    if not len(k):
        return {"a": 0.0, "b": 0.0, "b_sin_acotar": 0.0, "acotado_b": False, "acotado_a": False}
    X = np.column_stack([np.ones(len(k)), k])
    beta = np.linalg.lstsq(X, p, rcond=None)[0]
    return _acota(float(beta[0]), float(beta[1]), p)


def _scores(p_pru, pred_aditivo, pred_fijo, M0: float) -> dict:
    """El ECM, el EAM y la habilidad (SK) de los dos casos contra la referencia M0, en la muestra de prueba."""
    p_pru = np.asarray(p_pru, dtype=float)
    if not len(p_pru):
        return {"ecm_m0": NAN, "ecm_aditivo": NAN, "ecm_fijo": NAN, "eam_m0": NAN, "eam_aditivo": NAN,
                "eam_fijo": NAN, "sk_aditivo": NAN, "sk_fijo": NAN, "d": NAN}
    pa = np.asarray(pred_aditivo, dtype=float)
    pf = np.asarray(pred_fijo, dtype=float)
    ecm_m0 = float(np.mean((p_pru - M0) ** 2))
    ecm_ad = float(np.mean((p_pru - pa) ** 2))
    ecm_fi = float(np.mean((p_pru - pf) ** 2))
    eam_m0 = float(np.mean(np.abs(p_pru - M0)))
    eam_ad = float(np.mean(np.abs(p_pru - pa)))
    eam_fi = float(np.mean(np.abs(p_pru - pf)))
    if not ecm_m0 > 0:
        sk_ad = sk_fi = d = NAN
    else:
        sk_ad = 1.0 - ecm_ad / ecm_m0
        sk_fi = 1.0 - ecm_fi / ecm_m0
        d = sk_fi - sk_ad
    return {"ecm_m0": ecm_m0, "ecm_aditivo": ecm_ad, "ecm_fijo": ecm_fi, "eam_m0": eam_m0,
            "eam_aditivo": eam_ad, "eam_fijo": eam_fi, "sk_aditivo": sk_ad, "sk_fijo": sk_fi, "d": d}


def puntuar(k_ent, p_ent, k_pru, p_pru) -> dict:
    """Ajusta los dos casos en la muestra de entrenamiento y los puntua en la de prueba."""
    p_ent = np.asarray(p_ent, dtype=float)
    c = ajuste_aditivo(k_ent, p_ent)
    ac = ajuste_fijo(k_ent, p_ent)
    M0 = float(np.mean(p_ent)) if len(p_ent) else NAN
    k_pru = np.asarray(k_pru, dtype=float)
    out = {"c": c, "a": ac["a"], "b": ac["b"], "b_sin_acotar": ac["b_sin_acotar"], "acotado_b": ac["acotado_b"],
           "acotado_a": ac["acotado_a"], "M0": M0}
    out.update(_scores(p_pru, c * k_pru, ac["a"] + ac["b"] * k_pru, M0))
    return out


def estadisticos_padre(e: dict, idx_prog, delta_list) -> dict:
    """Una fila por padre del programa: sus meses de golpe, su K, su base y los grupos optimos por delta.

    La tabla se calcula una sola vez (no por repeticion del bootstrap)."""
    idx = _indices(idx_prog)
    deltas = tuple(int(d) for d in delta_list)
    if not len(idx):
        vacio = np.zeros(0, dtype=np.int64)
        return {"padre": vacio, "pad_padre": vacio.copy(), "n_obs": vacio.copy(), "K": np.zeros(0),
                "base": np.zeros(0), "n_noais": vacio.copy(), "n_opt": {d: vacio.copy() for d in deltas},
                "n_opt_gt6": {d: vacio.copy() for d in deltas}}
    p = e["padre"][idx]
    u, first, inv = np.unique(p, return_inverse=True, return_index=True)
    n = len(u)
    n_obs = np.bincount(inv, minlength=n)
    K = np.bincount(inv, weights=e["k"][idx].astype(float), minlength=n)
    base = np.bincount(inv, weights=e["base"][idx].astype(float), minlength=n) / np.maximum(n_obs, 1)
    n_noais = np.bincount(inv, weights=(~e["aislado"][idx].astype(bool)).astype(float), minlength=n)
    pad_padre = np.asarray(e["pad_padre"], dtype=np.int64)[idx][first]
    meses = e["mes"][idx]
    kk = e["k"][idx].astype(float)
    n_opt = {d: np.zeros(n, dtype=np.int64) for d in deltas}
    n_opt_gt6 = {d: np.zeros(n, dtype=np.int64) for d in deltas}
    for j in range(n):
        sel = inv == j
        for d in deltas:
            _, ko = calendario_optimo(meses[sel], kk[sel], d)
            n_opt[d][j] = len(ko)
            n_opt_gt6[d][j] = int((ko > K_RESPALDADO).sum())
    return {"padre": u, "pad_padre": pad_padre, "n_obs": n_obs, "K": K, "base": base, "n_noais": n_noais,
            "n_opt": n_opt, "n_opt_gt6": n_opt_gt6}


def costo_calendario(caso: str, params: dict, n_meses, K) -> float:
    """El costo en dias de base de un calendario: c K en el aditivo, a n_meses + b K en el fijo mas hijo."""
    if caso == "aditivo":
        return float(params.get("c", 0.0)) * float(K)
    return float(params.get("a", 0.0)) * float(n_meses) + float(params.get("b", 0.0)) * float(K)


def _costo_vec(caso: str, params: dict, n_meses, K) -> np.ndarray:
    """El costo en dias de base de un calendario, para varios padres a la vez."""
    if caso == "aditivo":
        return float(params.get("c", 0.0)) * np.asarray(K, dtype=float)
    return (float(params.get("a", 0.0)) * np.asarray(n_meses, dtype=float)
            + float(params.get("b", 0.0)) * np.asarray(K, dtype=float))


def arrepentimiento_padres(caso: str, params: dict, tab: dict, filas, delta) -> tuple[np.ndarray, np.ndarray]:
    """El arrepentimiento por padre, en dias de base: el costo del calendario observado menos el del optimo.

    Devuelve (dias de arrepentimiento, caudal base del padre) para las filas indicadas de la tabla."""
    filas = _indices(filas)
    if not len(filas):
        return np.zeros(0), np.zeros(0)
    n_obs = tab["n_obs"][filas].astype(float)
    K = tab["K"][filas].astype(float)
    base = tab["base"][filas].astype(float)
    n_opt = tab["n_opt"][int(delta)][filas].astype(float)
    obs = _costo_vec(caso, params, n_obs, K)
    opt = _costo_vec(caso, params, n_opt, K)
    return obs - opt, base


def _usd(m3, precio: float, tasa: float, rezago: float) -> float:
    """El costo en dolares del valor tiempo de cobrar el volumen mas tarde (decision.valor_indicativo)."""
    m3 = np.asarray(m3, dtype=float)
    if not len(m3):
        return 0.0
    return float(np.sum(valor_indicativo(m3, precio, tasa, rezago)["costo_de_diferir"]))


def _celdas() -> list[tuple[float, float, float]]:
    """Las 18 celdas de la grilla de valor: precios por tasas por rezagos."""
    return [(pr, ta, rz) for pr in GRILLA_PRECIOS for ta in GRILLA_TASAS for rz in GRILLA_REZAGOS]


def _usd_por_celda(m3) -> np.ndarray:
    """El costo en dolares de un volumen por celda de la grilla."""
    return np.array([_usd(m3, pr, ta, rz) for (pr, ta, rz) in _celdas()], dtype=float)


def veredicto(n_ent: int, pads_ent: int, conteo_k_ent: int, n_pru: int, pads_pru: int,
              d_ic_bajo: float, d_ic_alto: float, arrep_ic_bajo: float) -> str:
    """La regla del encabezado, en orden: sin muestra, costo aditivo, sostiene, no firme."""
    if (n_ent < N_ENTRENA_MIN or pads_ent < PADS_ENTRENA_MIN or conteo_k_ent < K_ENTRENA_DISTINTOS
            or n_pru < N_PRUEBA_MIN or pads_pru < PADS_PRUEBA_MIN):
        return "sin muestra"
    if not d_ic_alto < 0:
        if d_ic_bajo > 0 and arrep_ic_bajo > 0:
            return "sostiene"
        return "no firme"
    return "costo aditivo"


def _boot_pads(arrays: dict[str, np.ndarray], reps: int, semilla: int, fn) -> list:
    """Remuestrea los pads del padre de todas las filas dadas y llama fn con las filas de cada draw.

    arrays: dict nombre -> el pad del padre de cada fila. Cada pad remuestreado trae todas sus filas; un pad
    que sale dos veces repite sus filas (un clon, sin reetiquetar los padres)."""
    nombres = list(arrays)
    if not nombres:
        return []
    todos = np.concatenate([np.asarray(arrays[n], dtype=np.int64) for n in nombres])
    pads = np.unique(todos)
    pos = {int(p): i for i, p in enumerate(pads)}
    filas: dict[str, list[list[int]]] = {n: [[] for _ in pads] for n in nombres}
    for n in nombres:
        arr = np.asarray(arrays[n], dtype=np.int64)
        if not len(arr):
            continue
        for c in _clusters(arr):
            filas[n][pos[int(arr[c[0]])]].extend(int(x) for x in c)
    rng = np.random.default_rng(semilla)
    salida = []
    for _ in range(reps):
        pick = rng.integers(0, len(pads), len(pads))
        draw = {}
        for n in nombres:
            rows: list[int] = []
            for c in pick:
                rows.extend(filas[n][int(c)])
            draw[n] = np.asarray(rows, dtype=np.int64)
        salida.append(fn(draw))
    return salida


# ------------------------------------------------------------------ calculo

def _conteo_k(k) -> int:
    """La cantidad de valores de k con al menos N_K_ENTRENA eventos en la muestra."""
    k = np.asarray(k)
    if not len(k):
        return 0
    _, c = np.unique(k, return_counts=True)
    return int((c >= N_K_ENTRENA).sum())


def _s1(e: dict, idx_ent, idx_pru) -> dict:
    """S1: los dos casos con k12 y el logaritmo del caudal de base, centrados en la media de entrenamiento y sin FE."""
    idx_ent = _indices(idx_ent)
    idx_pru = _indices(idx_pru)
    if not len(idx_ent):
        return {"c": NAN, "a": NAN, "b": NAN, "b_sin_acotar": NAN, "acotado_b": False, "acotado_a": False,
                "M0": NAN, "ecm_m0": NAN, "ecm_aditivo": NAN, "ecm_fijo": NAN, "eam_m0": NAN, "eam_aditivo": NAN,
                "eam_fijo": NAN, "sk_aditivo": NAN, "sk_fijo": NAN, "d": NAN}
    k12_mean = float(np.mean(e["k12"][idx_ent]))
    lb = np.log(e["base"])
    lb_mean = float(np.mean(lb[idx_ent]))

    def ctrl(idx) -> np.ndarray:
        return np.column_stack([e["k12"][idx].astype(float) - k12_mean, lb[idx] - lb_mean])

    y = e["perdida"][idx_ent]
    za = np.column_stack([e["k"][idx_ent].astype(float), ctrl(idx_ent)])
    ba = np.linalg.lstsq(za, y, rcond=None)[0]
    c = max(float(ba[0]), 0.0)
    zf = np.column_stack([np.ones(len(y)), e["k"][idx_ent].astype(float), ctrl(idx_ent)])
    bf = np.linalg.lstsq(zf, y, rcond=None)[0]
    ac = _acota(float(bf[0]), float(bf[1]), y)
    M0 = float(np.mean(y))
    if len(idx_pru):
        pred_ad = c * e["k"][idx_pru].astype(float) + ctrl(idx_pru) @ ba[1:]
        pred_fi = ac["a"] + ac["b"] * e["k"][idx_pru].astype(float) + ctrl(idx_pru) @ bf[2:]
    else:
        pred_ad = np.zeros(0)
        pred_fi = np.zeros(0)
    out = {"c": c, "a": ac["a"], "b": ac["b"], "b_sin_acotar": ac["b_sin_acotar"], "acotado_b": ac["acotado_b"],
           "acotado_a": ac["acotado_a"], "M0": M0}
    out.update(_scores(e["perdida"][idx_pru], pred_ad, pred_fi, M0))
    return out


def _aditivo_completo(e: dict, i, y=None) -> float:
    """El caso aditivo de la muestra completa: P sobre [k, S, controles] sin constante, acotado en 0."""
    i = _indices(i)
    if not len(i):
        return 0.0
    y = e["perdida"] if y is None else y
    Z = np.column_stack([e["k"][i].astype(float), gm._s(e, i), gm._controles(e, i)])
    beta = np.linalg.lstsq(Z, y[i], rcond=None)[0]
    return max(float(beta[0]), 0.0)


def _matriz_draw(params: dict, tab: dict, filas, deltas) -> dict:
    """Los costos por calendario y celda de la grilla en un draw: dias, m3 y usd."""
    filas = np.asarray(filas, dtype=np.int64)
    n_obs = tab["n_obs"][filas].astype(float)
    K = tab["K"][filas].astype(float)
    base = tab["base"][filas].astype(float)
    out: dict[tuple, dict] = {}
    for caso in CASOS:
        p = params[caso]
        obs = _costo_vec(caso, p, n_obs, K)
        sep = _costo_vec(caso, p, K, K)
        out[(caso, "observado", 0)] = {"dias": float(obs.sum()), "m3": float((obs * base).sum()),
                                       "usd": _usd_por_celda(obs * base)}
        out[(caso, "separado", 0)] = {"dias": float(sep.sum()), "m3": float((sep * base).sum()),
                                      "usd": _usd_por_celda(sep * base)}
        for d in deltas:
            n_opt = tab["n_opt"][d][filas].astype(float)
            opt = _costo_vec(caso, p, n_opt, K)
            out[(caso, "optimo", d)] = {"dias": float(opt.sum()), "m3": float((opt * base).sum()),
                                        "usd": _usd_por_celda(opt * base)}
    return out


def _fila(prueba: str, estadistico: str, valor, ic_bajo=None, ic_alto=None, n=None, vered=None) -> tuple:
    """Una fila de mart_calendario_prueba (los NaN se escriben como None)."""
    return (prueba, estadistico, _f(valor), _f(ic_bajo), _f(ic_alto), None if n is None else int(n), vered)


def _conteos_programa(tab: dict) -> dict:
    """Los conteos de un programa: padres, meses de golpe, K y la parte no aislada y extrapola."""
    n_obs = int(tab["n_obs"].sum())
    sal = {"padres": int(len(tab["padre"])), "meses": n_obs, "K": float(tab["K"].sum()),
           "noais": float(tab["n_noais"].sum() / n_obs) if n_obs else NAN, "frac_gt6": {}}
    for d, v in tab["n_opt"].items():
        tot = int(v.sum())
        sal["frac_gt6"][d] = float(tab["n_opt_gt6"][d].sum() / tot) if tot else NAN
    return sal


def calcular(D: dict, reps: int = REPS) -> dict[str, list[tuple]]:
    """Las cuatro tablas del modulo: la prueba del backtest, la tabla por k, el costo por k y la matriz de costo."""
    e = gm.eventos(D)
    e["pad_padre"] = np.asarray(D["pad_padre"], dtype=np.int64)[e["padre"]]
    mu = gm.muestras(e)
    principal = mu["principal"]
    s2 = mu["S2"]
    anio = e["anio"]
    idx_ent = principal & (anio == ANIO_ENTRENA)
    idx_pru = principal & (anio >= ANIOS_PRUEBA[0]) & (anio <= ANIOS_PRUEBA[1])
    prog_test = s2 & (anio >= ANIOS_PRUEBA[0]) & (anio <= ANIOS_PRUEBA[1])
    prog_full = s2
    deltas = tuple(sorted({int(DELTA_MESES)} | {int(d) for d in DELTAS_SENS}))
    tab_test = estadisticos_padre(e, prog_test, deltas)
    tab_full = estadisticos_padre(e, prog_full, deltas)
    prog_t = _conteos_programa(tab_test)
    prog_f = _conteos_programa(tab_full)

    n_ent = int(idx_ent.sum())
    n_pru = int(idx_pru.sum())
    pads_ent = int(len(np.unique(e["pad_padre"][idx_ent]))) if n_ent else 0
    pads_pru = int(len(np.unique(e["pad_padre"][idx_pru]))) if n_pru else 0
    padres_ent = int(len(np.unique(e["padre"][idx_ent]))) if n_ent else 0
    conteo_k = _conteo_k(e["k"][idx_ent])
    n_principal = int(principal.sum())

    k_ent = e["k"][idx_ent].astype(float)
    p_ent = e["perdida"][idx_ent]
    k_pru = e["k"][idx_pru].astype(float)
    p_pru = e["perdida"][idx_pru]

    score: dict = {}
    s1: dict = {}
    a83 = b83 = c83 = NAN
    comp: dict = {}
    rep: list = []
    if n_ent > 0:
        score = puntuar(k_ent, p_ent, k_pru, p_pru)
        s1 = _s1(e, idx_ent, idx_pru)
        a83, b83 = gm.ajuste(e, _indices(principal), e["perdida"])
        c83 = _aditivo_completo(e, principal)
        comp = _acota(a83, b83, e["perdida"][principal])
        params_main = {"aditivo": {"c": score["c"]}, "fijo_mas_hijo": {"a": score["a"], "b": score["b"]}}
        params83 = {"aditivo": {"c": c83}, "fijo_mas_hijo": {"a": comp["a"], "b": comp["b"]}}
        arrays = {"entrena": e["pad_padre"][idx_ent], "prueba": e["pad_padre"][idx_pru],
                  "completa": e["pad_padre"][principal], "prog_test": tab_test["pad_padre"],
                  "prog_full": tab_full["pad_padre"]}

        pos_ent, pos_pru, pos_comp = _indices(idx_ent), _indices(idx_pru), _indices(principal)

        def una(draw):
            # el draw trae posiciones dentro de cada arreglo de pads: se pasan a indices de evento
            i_ent = pos_ent[draw["entrena"]]
            i_pru = pos_pru[draw["prueba"]]
            ke = e["k"][i_ent].astype(float)
            pe = e["perdida"][i_ent]
            kp = e["k"][i_pru].astype(float)
            pp = e["perdida"][i_pru]
            M0 = float(np.mean(pe)) if len(pe) else NAN
            c = ajuste_aditivo(ke, pe)
            ac = ajuste_fijo(ke, pe)
            sc = _scores(pp, c * kp, ac["a"] + ac["b"] * kp, M0)
            s1d = _s1(e, i_ent, i_pru)
            pr = {"aditivo": {"c": c}, "fijo_mas_hijo": {"a": ac["a"], "b": ac["b"]}}
            reg = {}
            for d in deltas:
                for caso in CASOS:
                    dias, _ = arrepentimiento_padres(caso, pr[caso], tab_test, draw["prog_test"], d)
                    reg[(caso, d)] = (float(dias.sum()), float(dias.sum() / max(prog_t["padres"], 1)))
            i_comp = pos_comp[draw["completa"]]
            aa, bb = gm.ajuste(e, i_comp, e["perdida"])
            cc = _aditivo_completo(e, i_comp)
            ac83 = _acota(aa, bb, e["perdida"][i_comp])
            p83 = {"aditivo": {"c": cc}, "fijo_mas_hijo": {"a": ac83["a"], "b": ac83["b"]}}
            regc = {}
            for d in deltas:
                for caso in CASOS:
                    dias, _ = arrepentimiento_padres(caso, p83[caso], tab_full, draw["prog_full"], d)
                    regc[(caso, d)] = (float(dias.sum()), float(dias.sum() / max(prog_f["padres"], 1)))
            return {"sc": sc, "s1": s1d, "acotado_b": ac["acotado_b"], "reg": reg, "regc": regc,
                    "m23": _matriz_draw(pr, tab_test, draw["prog_test"], deltas),
                    "mcomp": _matriz_draw(p83, tab_full, draw["prog_full"], deltas)}

        rep = _boot_pads(arrays, reps, SEMILLA_CALENDARIO, una)

    # -------------------------------------------------------------- filas de la prueba
    prueba: list[tuple] = []
    prueba.append(_fila("entrena", "n", n_ent, n=n_ent))
    prueba.append(_fila("entrena", "pads", pads_ent, n=n_ent))
    prueba.append(_fila("entrena", "padres", padres_ent, n=n_ent))
    prueba.append(_fila("entrena", "valores_k", conteo_k, n=n_ent))
    for d in deltas:
        prueba.append(_fila("entrena", f"programa_test_gt6_d{d}", prog_t["frac_gt6"][d], n=prog_t["padres"]))
        prueba.append(_fila("entrena", f"programa_completa_gt6_d{d}", prog_f["frac_gt6"][d], n=prog_f["padres"]))
    prueba.append(_fila("entrena", "programa_test_padres", prog_t["padres"], n=prog_t["padres"]))
    prueba.append(_fila("entrena", "programa_test_meses", prog_t["meses"], n=prog_t["padres"]))
    prueba.append(_fila("entrena", "programa_test_k", prog_t["K"], n=prog_t["padres"]))
    prueba.append(_fila("entrena", "programa_test_noaislados", prog_t["noais"], n=prog_t["padres"]))
    prueba.append(_fila("entrena", "programa_completa_padres", prog_f["padres"], n=prog_f["padres"]))
    prueba.append(_fila("entrena", "programa_completa_meses", prog_f["meses"], n=prog_f["padres"]))
    prueba.append(_fila("entrena", "programa_completa_k", prog_f["K"], n=prog_f["padres"]))
    prueba.append(_fila("entrena", "programa_completa_noaislados", prog_f["noais"], n=prog_f["padres"]))

    def _ic_de(valores) -> tuple[float, float]:
        return gm._ic(np.asarray(valores, dtype=float))

    if score:
        d_rep = np.array([r["sc"]["d"] for r in rep], dtype=float)
        d_lo, d_hi = _ic_de(d_rep)
        ar_rep = np.array([r["reg"][("fijo_mas_hijo", DELTA_MESES)][0] for r in rep], dtype=float)
        ar_lo, ar_hi = _ic_de(ar_rep)
        v = veredicto(n_ent, pads_ent, conteo_k, n_pru, pads_pru, d_lo, d_hi, ar_lo)
        for est in ("c", "a", "b", "b_sin_acotar", "M0"):
            prueba.append(_fila("backtest", est, score[est], n=n_ent))
        prueba.append(_fila("backtest", "acotado_b", int(score["acotado_b"]), n=n_ent))
        prueba.append(_fila("backtest", "acotado_a", int(score["acotado_a"]), n=n_ent))
        for est in ("ecm_m0", "ecm_aditivo", "ecm_fijo", "eam_m0", "eam_aditivo", "eam_fijo",
                    "sk_aditivo", "sk_fijo"):
            prueba.append(_fila("backtest", est, score[est], n=n_pru))
        prueba.append(_fila("backtest", "d", score["d"], d_lo, d_hi, n_pru, v))
        prueba.append(_fila("backtest", "n_prueba", n_pru, n=n_pru))
        prueba.append(_fila("backtest", "pads_prueba", pads_pru, n=n_pru))
        prueba.append(_fila("backtest", "descartadas",
                            int(sum(1 for r in rep if not (r["sc"]["ecm_m0"] > 0))), n=reps))
        prueba.append(_fila("backtest", "b_acotadas", int(sum(1 for r in rep if r["acotado_b"])), n=reps))
        for est in ("c", "a", "b", "b_sin_acotar"):
            prueba.append(_fila("S1", est, s1[est], n=n_ent))
        prueba.append(_fila("S1", "acotado_b", int(s1["acotado_b"]), n=n_ent))
        for est in ("ecm_m0", "ecm_aditivo", "ecm_fijo", "eam_m0", "eam_aditivo", "eam_fijo",
                    "sk_aditivo", "sk_fijo"):
            prueba.append(_fila("S1", est, s1[est], n=n_pru))
        d1 = np.array([r["s1"]["d"] for r in rep], dtype=float)
        prueba.append(_fila("S1", "d", s1["d"], *_ic_de(d1), n=n_pru))
        prueba.append(_fila("completa", "a", comp["a"], n=n_principal))
        prueba.append(_fila("completa", "a_sin_acotar", a83, n=n_principal))
        prueba.append(_fila("completa", "b", comp["b"], n=n_principal))
        prueba.append(_fila("completa", "b_sin_acotar", b83, n=n_principal))
        prueba.append(_fila("completa", "acotado_b", int(comp["acotado_b"]), n=n_principal))
        prueba.append(_fila("completa", "acotado_a", int(comp["acotado_a"]), n=n_principal))
        prueba.append(_fila("completa", "c", c83, n=n_principal))
        prueba.append(_fila("completa", "n", n_principal, n=n_principal))
        pt_main: dict = {}
        pt_comp: dict = {}
        for d in deltas:
            for caso in CASOS:
                dias, _ = arrepentimiento_padres(caso, params_main[caso], tab_test,
                                                 np.arange(len(tab_test["padre"])), d)
                pt_main[(caso, d)] = float(dias.sum())
                dias_c, _ = arrepentimiento_padres(caso, params83[caso], tab_full,
                                                   np.arange(len(tab_full["padre"])), d)
                pt_comp[(caso, d)] = float(dias_c.sum())
                est = f"dias_{caso}_d{d}"
                vals = np.array([r["reg"][(caso, d)][0] for r in rep], dtype=float)
                prueba.append(_fila("arrepentimiento", est, pt_main[(caso, d)],
                                    *_ic_de(vals), n=prog_t["padres"]))
                vals_pp = np.array([r["reg"][(caso, d)][1] for r in rep], dtype=float)
                est_pp = f"dias_por_padre_{caso}_d{d}"
                prueba.append(_fila("arrepentimiento", est_pp, pt_main[(caso, d)] / max(prog_t["padres"], 1),
                                    *_ic_de(vals_pp), n=prog_t["padres"]))
                vals_c = np.array([r["regc"][(caso, d)][0] for r in rep], dtype=float)
                est_c = f"dias_{caso}_d{d}"
                prueba.append(_fila("completa_arrepentimiento", est_c, pt_comp[(caso, d)],
                                    *_ic_de(vals_c), n=prog_f["padres"]))
                vals_cp = np.array([r["regc"][(caso, d)][1] for r in rep], dtype=float)
                est_cp = f"dias_por_padre_{caso}_d{d}"
                prueba.append(_fila("completa_arrepentimiento", est_cp,
                                    pt_comp[(caso, d)] / max(prog_f["padres"], 1),
                                    *_ic_de(vals_cp), n=prog_f["padres"]))
    else:
        v = veredicto(n_ent, pads_ent, conteo_k, n_pru, pads_pru, NAN, NAN, NAN)
        prueba.append(_fila("backtest", "d", None, None, None, n_pru, v))
        prueba.append(_fila("backtest", "n_prueba", n_pru, n=n_pru))
        prueba.append(_fila("backtest", "pads_prueba", pads_pru, n=n_pru))

    # -------------------------------------------------------------- tabla por k (prueba, fuera de muestra)
    filas_k: list[tuple] = []
    g = gm._grupo_k(k_pru.astype(np.int64))
    for gi, etq in enumerate(gm.ETQ_GRUPO):
        en = g == gi
        if not en.any():
            filas_k.append((etq, gi, 0, None, None, None, None, None))
            continue
        pred_ad = score["c"] * k_pru[en] if score else None
        pred_fi = (score["a"] + score["b"] * k_pru[en]) if score else None
        filas_k.append((etq, gi, int(en.sum()), float(k_pru[en].mean()), float(p_pru[en].mean()),
                        score.get("M0"), None if pred_ad is None else float(pred_ad.mean()),
                        None if pred_fi is None else float(pred_fi.mean())))

    # -------------------------------------------------------------- costo por k
    filas_costo_k: list[tuple] = []
    if score:
        ajustes = (("2023", {"aditivo": {"c": score["c"]}, "fijo_mas_hijo": {"a": score["a"], "b": score["b"]}}),
                   ("completa", {"aditivo": {"c": c83}, "fijo_mas_hijo": {"a": comp["a"], "b": comp["b"]}}))
        for ajuste, pr in ajustes:
            for caso in CASOS:
                for k in KS_MATRIZ:
                    f1 = costo_calendario(caso, pr[caso], 1, 1)
                    fk = costo_calendario(caso, pr[caso], 1, k)
                    sep = k * f1
                    filas_costo_k.append((ajuste, caso, int(k), fk, sep, fk / sep if sep else NAN))

    # -------------------------------------------------------------- matriz de costo
    filas_matriz: list[tuple] = []
    if score:
        pr_main = {"aditivo": {"c": score["c"]}, "fijo_mas_hijo": {"a": score["a"], "b": score["b"]}}
        pr_comp = {"aditivo": {"c": c83}, "fijo_mas_hijo": {"a": comp["a"], "b": comp["b"]}}
        m_main = _matriz_draw(pr_main, tab_test, np.arange(len(tab_test["padre"])), deltas)
        m_comp = _matriz_draw(pr_comp, tab_full, np.arange(len(tab_full["padre"])), deltas)
        for ajuste, m, tab, n_padres in (("2023", m_main, tab_test, prog_t["padres"]),
                                         ("completa", m_comp, tab_full, prog_f["padres"])):
            for caso in CASOS:
                for calendario in CALENDARIOS:
                    d = DELTA_MESES if calendario == "optimo" else 0
                    info = m[(caso, calendario, d)]
                    for ic, (pr, ta, rz) in enumerate(_celdas()):
                        usd = float(info["usd"][ic])
                        if ajuste == "2023":
                            vals = np.array([r["m23"][(caso, calendario, d)]["usd"][ic] for r in rep], dtype=float)
                        else:
                            vals = np.array([r["mcomp"][(caso, calendario, d)]["usd"][ic] for r in rep], dtype=float)
                        lo, hi = _ic_de(vals)
                        filas_matriz.append((ajuste, caso, calendario, int(d), float(pr), float(ta), int(rz),
                                             int(n_padres), info["dias"], info["m3"], usd,
                                             usd / n_padres if n_padres else NAN, lo, hi))

    return {"prueba": prueba, "k": filas_k, "costo_k": filas_costo_k, "matriz": filas_matriz}


# ------------------------------------------------------------------ escritura

def escribir(con, t: dict[str, list[tuple]]) -> None:
    """Escribe las cuatro tablas del modulo."""
    _escribir(con, "mart_calendario_prueba", gm.COLS_PRUEBA, t["prueba"])
    _escribir(con, "mart_calendario_k", COLS_K, t["k"])
    _escribir(con, "mart_calendario_costo_k", COLS_COSTO_K, t["costo_k"])
    _escribir(con, "mart_calendario_matriz", COLS_MATRIZ, t["matriz"])


def marts(con) -> dict | None:
    """Las tablas del modulo (None si todavia no se corrio)."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?",
                       ["mart_calendario_prueba"]).fetchone()[0]:
        return None
    return {"prueba": con.execute("select * from mart_calendario_prueba").fetchall(),
            "k": con.execute("select * from mart_calendario_k order by orden").fetchall(),
            "costo_k": con.execute("select * from mart_calendario_costo_k").fetchall(),
            "matriz": con.execute("select * from mart_calendario_matriz").fetchall()}


def _comprueba_83(con, D: dict) -> None:
    """Falla si el a y el b de la muestra completa no reproducen los publicados por #83 (antes de acotar)."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?",
                       ["mart_golpes_mismo_mes_prueba"]).fetchone()[0]:
        return
    pub = {r[0]: r[1] for r in con.execute(
        "select estadistico, valor from mart_golpes_mismo_mes_prueba where prueba = 'principal'").fetchall()}
    e = gm.eventos(D)
    principal = gm.muestras(e)["principal"]
    a, b = gm.ajuste(e, _indices(principal), e["perdida"])
    for est, valor in (("a", a), ("b", b)):
        if est not in pub or pub[est] is None:
            continue
        if abs(float(pub[est]) - valor) > 0.05:
            raise RuntimeError(f"el {est} de la muestra completa ({valor:.4f}) no reproduce el publicado por #83 "
                               f"({float(pub[est]):.4f})")


# ------------------------------------------------------------------ pagina

def _p(t: dict, prueba: str, est: str, col: int = 2):
    r = t["p"].get((prueba, est))
    return None if r is None else r[col]


def _ic(t: dict, prueba: str, est: str, dec: int = 1) -> str:
    r = t["p"].get((prueba, est))
    if r is None or r[2] is None:
        return "n/d"
    return _g(r[2], dec) + (f" ({_g(r[3], dec)} a {_g(r[4], dec)})" if r[3] is not None else "")


def _tabla_ajustes(t: dict) -> list[str]:
    """Los dos casos de costo con sus parametros, antes y despues de acotar."""
    L = ["| Ajuste | Parámetro | Sin acotar | Usado | Acotado |", "| --- | --- | ---: | ---: | --- |"]
    L.append(f"| 2023 (entrenamiento) | c, caso aditivo (días de base por hijo) | n/d | "
             f"{_g(_p(t, 'backtest', 'c'), 2)} | {'sí' if _p(t, 'backtest', 'c') == 0 else 'no'} |")
    L.append(f"| 2023 (entrenamiento) | b, caso fijo más hijo (días de base por hijo) | {_g(_p(t, 'backtest', 'b_sin_acotar'), 1)} | "
             f"{_g(_p(t, 'backtest', 'b'), 1)} | {'sí' if _p(t, 'backtest', 'acotado_b') else 'no'} |")
    L.append(f"| 2023 (entrenamiento) | a, caso fijo más hijo (días de base por mes de golpe) | n/d | "
             f"{_g(_p(t, 'backtest', 'a'), 1)} | {'sí' if _p(t, 'backtest', 'acotado_a') else 'no'} |")
    L.append(f"| Muestra completa (descriptivo) | c, caso aditivo (días de base por hijo) | {_g(_p(t, 'completa', 'c'), 2)} | "
             f"{_g(_p(t, 'completa', 'c'), 2)} | no |")
    L.append(f"| Muestra completa (descriptivo) | b, caso fijo más hijo (días de base por hijo) | "
             f"{_g(_p(t, 'completa', 'b_sin_acotar'), 1)} | {_g(_p(t, 'completa', 'b'), 1)} | "
             f"{'sí' if _p(t, 'completa', 'acotado_b') else 'no'} |")
    L.append(f"| Muestra completa (descriptivo) | a, caso fijo más hijo (días de base por mes de golpe) | "
             f"{_g(_p(t, 'completa', 'a_sin_acotar'), 1)} | {_g(_p(t, 'completa', 'a'), 1)} | "
             f"{'sí' if _p(t, 'completa', 'acotado_a') else 'no'} |")
    return L


def _tabla_costo_k(filas: list[tuple]) -> list[str]:
    L = ["| Ajuste | Caso | Hijos en el mes | Pérdida juntos (días de base) | Los mismos hijos separados (días de base) | "
         "ρ (juntos sobre separados) |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for ajuste, caso, k, juntos, sep, rho in filas:
        etq = "2023" if ajuste == "2023" else "muestra completa"
        L.append(f"| {etq} | {CASO_ETQ[caso]} | {k} | {_g(juntos, 1)} | {_g(sep, 1)} | {_g(rho, 2)} |")
    return L


CASO_ETQ = {"aditivo": "aditivo", "fijo_mas_hijo": "fijo más hijo"}


def _tabla_backtest(t: dict) -> list[str]:
    L = ["| Modelo | ECM | Error absoluto medio | Habilidad contra M0 | ECM con controles (S1) | Habilidad con controles (S1) |",
         "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for etq, sufijo in (("M0 (media de 2023)", "m0"), ("Aditivo, P = c k", "aditivo"), ("Fijo más hijo, P = a + b k", "fijo")):
        sk = "" if sufijo == "m0" else _g(_p(t, "backtest", f"sk_{sufijo}"), 3)
        sk1 = "" if sufijo == "m0" else _g(_p(t, "S1", f"sk_{sufijo}"), 3)
        L.append(f"| {etq} | {_g(_p(t, 'backtest', f'ecm_{sufijo}'), 1)} | {_g(_p(t, 'backtest', f'eam_{sufijo}'), 1)} | {sk} | "
                 f"{_g(_p(t, 'S1', f'ecm_{sufijo}'), 1)} | {sk1} |")
    r = t["p"][("backtest", "d")]
    r1 = t["p"][("S1", "d")]
    L.append(f"| D = habilidad del fijo menos la del aditivo | | | {_g(r[2], 3)} (IC 95% {_g(r[3], 2)} a {_g(r[4], 2)}) | | "
             f"{_g(r1[2], 3)} (IC 95% {_g(r1[3], 2)} a {_g(r1[4], 2)}) |")
    return L


def _tabla_k_prueba(filas: list[tuple]) -> list[str]:
    L = ["| Hijos a menos de 1 km en el mes | Eventos de 2024 a 2026 | k media | Pérdida observada (días de base) | "
         "Predicha por M0 | Predicha por el aditivo | Predicha por el fijo más hijo |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for g, _o, n, km, po, m0, ad, fi in filas:
        if not n:
            L.append(f"| {g} | 0 | | | | | |")
            continue
        L.append(f"| {g} | {_g(n)} | {_g(km, 1)} | {_g(po, 1)} | {_g(m0, 1)} | {_g(ad, 1)} | {_g(fi, 1)} |")
    return L


def _tabla_arrepentimiento(t: dict, prefijo: str) -> list[str]:
    L = ["| Caso | Máximo de meses que se mueve un hijo | Arrepentimiento (días de base) | IC 95% | Por padre (días de base) | "
         "IC 95% por padre |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for caso in CASOS:
        for d in sorted({int(DELTA_MESES)} | {int(x) for x in DELTAS_SENS}):
            r = t["p"].get((prefijo, f"dias_{caso}_d{d}"))
            rp = t["p"].get((prefijo, f"dias_por_padre_{caso}_d{d}"))
            marca = " (la del veredicto)" if d == DELTA_MESES else ""
            L.append(f"| {CASO_ETQ[caso]} | {d}{marca} | {_g(r[2], 0)} | {_g(r[3], 0)} a {_g(r[4], 0)} | {_g(rp[2], 2)} | "
                     f"{_g(rp[3], 2)} a {_g(rp[4], 2)} |")
    return L


def _usd_millones(x) -> str:
    return "n/d" if x is None else _g(x / 1e6, 1)


def _tabla_matriz_central(filas: list[tuple]) -> list[str]:
    """Calendario observado, optimo y todo separado en la celda central de la grilla."""
    L = ["| Ajuste | Caso | Calendario | Padres | Días de base | m3 | USD (millones) | IC 95% (USD millones) |",
         "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in filas:
        ajuste, caso, cal, delta, pr, ta, rz, padres, dias, m3, usd, _pp, lo, hi = r
        if (pr, ta, rz) != (PRECIO_CENTRAL, TASA_CENTRAL, REZAGO_CENTRAL):
            continue
        etq = "2023" if ajuste == "2023" else "muestra completa"
        L.append(f"| {etq} | {CASO_ETQ[caso]} | {'óptimo' if cal == 'optimo' else cal} | {_g(padres)} | {_g(dias)} | {_g(m3)} | {_usd_millones(usd)} | "
                 f"{_usd_millones(lo)} a {_usd_millones(hi)} |")
    return L


def _grilla_arrepentimiento(filas: list[tuple], ajuste: str) -> list[str]:
    """Arrepentimiento en dolares (observado menos optimo, caso fijo mas hijo) en las 18 celdas de la grilla."""
    obs, opt = {}, {}
    for r in filas:
        if r[0] == ajuste and r[1] == "fijo_mas_hijo":
            if r[2] == "observado":
                obs[(r[4], r[5], r[6])] = r[10]
            elif r[2] == "optimo":
                opt[(r[4], r[5], r[6])] = r[10]
    L = ["| Precio (USD por barril) | Tasa por año | " + " | ".join(f"Rezago {z} meses" for z in GRILLA_REZAGOS) + " |",
         "| ---: | ---: | " + " | ".join("---:" for _ in GRILLA_REZAGOS) + " |"]
    for pr in GRILLA_PRECIOS:
        for ta in GRILLA_TASAS:
            celdas = [_usd_millones(obs[(float(pr), float(ta), int(rz))] - opt[(float(pr), float(ta), int(rz))])
                      for rz in GRILLA_REZAGOS]
            L.append(f"| {pr} | {_g(ta, 2)} | " + " | ".join(celdas) + " |")
    return L


def _tabla_muestra_cal(t: dict) -> list[str]:
    L = ["| Muestra | Valor |", "| --- | ---: |"]
    filas = (("Eventos aislados de 2023 (entrenamiento)", "entrena", "n", 0),
             ("Pads del padre de 2023", "entrena", "pads", 0),
             ("Padres de 2023", "entrena", "padres", 0),
             (f"Valores distintos de k con al menos {N_K_ENTRENA} eventos en 2023", "entrena", "valores_k", 0),
             ("Eventos aislados de 2024 a 2026 (prueba)", "backtest", "n_prueba", 0),
             ("Pads del padre de 2024 a 2026", "backtest", "pads_prueba", 0),
             ("Padres con programa de 2024 a 2026 (cercanos con la ventana completa)", "entrena", "programa_test_padres", 0),
             ("Meses de golpe de esos programas", "entrena", "programa_test_meses", 0),
             ("Padres con programa en toda la muestra", "entrena", "programa_completa_padres", 0),
             ("Meses de golpe de esos programas", "entrena", "programa_completa_meses", 0),
             ("Eventos aislados de toda la muestra (descriptivo)", "completa", "n", 0))
    for etq, a, b, dec in filas:
        L.append(f"| {etq} | {_g(_p(t, a, b), dec)} |")
    return L


def _lectura_veredicto(t: dict) -> str:
    v = t["p"][("backtest", "d")][6]
    n_ent, pads_ent = _p(t, "entrena", "n"), _p(t, "entrena", "pads")
    if v == "sin muestra":
        return (f"- Backtest: **sin muestra**. El dato no decide. El entrenamiento de 2023 tiene {_g(n_ent)} eventos aislados "
                f"({_g(pads_ent)} pads del padre y {_g(_p(t, 'entrena', 'valores_k'))} valores de k con al menos {N_K_ENTRENA} eventos) "
                f"y la regla pide {_g(N_ENTRENA_MIN)} eventos y {_g(PADS_ENTRENA_MIN)} pads. La prueba de 2024 a 2026 tiene "
                f"{_g(_p(t, 'backtest', 'n_prueba'))} eventos en {_g(_p(t, 'backtest', 'pads_prueba'))} pads, que alcanzan "
                f"({_g(N_PRUEBA_MIN)} y {_g(PADS_PRUEBA_MIN)}). Las cifras del backtest de abajo son descriptivas, no un resultado "
                "de la regla.")
    return f"- Backtest: **{v}**."


def pagina_calendario_golpes(con) -> str:
    """Pagina de la wiki a partir de los marts (solo lee)."""
    m = marts(con)
    t = {"p": {(r[0], r[1]): r for r in m["prueba"]}}
    d = t["p"][("backtest", "d")]
    sin = d[6] == "sin muestra"
    desc = "Descriptivo. " if sin else ""
    L = ["# Calendario de golpes: matrices de costo, optimizador y backtest", "",
         "¿Conviene mover cuándo se fractura cada hijo para que los hijos cercanos a un padre caigan en menos meses? Esta página "
         "es la tercera pieza del optimizador de calendario. Parte de lo que midieron golpes_mismo_mes (PR #83, el modelo agrupado) y "
         "golpes_mismo_padre (PR #86, cada padre consigo mismo, que terminó «sin muestra»), valúa los dos modelos de costo "
         "posibles, calcula el calendario que menos pérdida tendría y mide si un modelo ajustado en 2023 predice la pérdida de 2024 "
         "a 2026.", "",
         "## Lectura", "", _lectura_veredicto(t),
         f"- {desc}No es una recomendación al operador. {'Como la prueba de #86 quedó «sin muestra» y este backtest tampoco decide, el' if sin else 'El'} "
         "calendario óptimo, el arrepentimiento y los dólares de esta página salen del modelo agrupado de #83 y del ajuste de "
         "esta página: dicen qué haría el modelo, no qué conviene hacer, y no hay un calendario recomendado.",
         "- Supuesto que sostiene el optimizador: b, el costo por hijo adicional dentro de un mes, se acota en 0 cuando sale "
         "negativo, igual que en #83 (b acotado en 0, heredado de #83). Con b = 0 todos los hijos de un mes cuestan lo mismo que "
         "uno solo, el extremo de más ahorro por agrupar, así que el arrepentimiento y los dólares son una cota superior y no una "
         "estimación. Es una decisión de la regla, no un dato.",
         f"- {desc}Con #86 sin decidir un caso de costo, queda lo último publicado, el modelo agrupado de #83, y se corren los dos "
         f"casos. En toda la muestra el ajuste es a = {_g(_p(t, 'completa', 'a_sin_acotar'), 1)} y "
         f"b = {_g(_p(t, 'completa', 'b_sin_acotar'), 1)} días de base: b sale negativo, así que se acota en 0 y a pasa a ser la "
         f"media de la pérdida, {_g(_p(t, 'completa', 'a'), 1)} días. Con b = 0 todos los hijos de un mes cuestan lo mismo que uno "
         "solo: es el extremo de más ahorro por agrupar, una decisión de la regla y no un dato.",
         f"- {desc}Fuera de muestra, con el ajuste de 2023, el modelo de costo fijo más hijo predice {'peor' if d[2] < 0 else 'mejor'} que el aditivo en la "
         f"estimación puntual: D = {_g(d[2], 3)} (IC 95% {_g(d[3], 2)} a {_g(d[4], 2)}), con habilidad "
         f"{_g(_p(t, 'backtest', 'sk_fijo'), 3)} contra {_g(_p(t, 'backtest', 'sk_aditivo'), 3)} del aditivo. Ninguno de los dos "
         f"supera claramente a la media de 2023. El intervalo {'incluye' if d[3] <= 0 <= d[4] else 'no incluye'} el cero; con una muestra "
         "de entrenamiento que no alcanza, eso no es una prueba de que no haya diferencia.",
         f"- {desc}El ajuste de 2023 no tiene un costo fijo: el aditivo sale con c = {_g(_p(t, 'backtest', 'c'), 2)} (la media de "
         f"2023 es negativa, {_g(_p(t, 'backtest', 'M0'), 1)} días) y el fijo más hijo con a = {_g(_p(t, 'backtest', 'a'), 1)} y "
         f"b = {_g(_p(t, 'backtest', 'b'), 1)} días, es decir, un modelo por hijo. Con ese ajuste el arrepentimiento del "
         "calendario es cero.",
         f"- {desc}El arrepentimiento del calendario observado contra el óptimo (cada hijo puede moverse hasta {DELTA_MESES} meses), "
         f"caso fijo más hijo con el ajuste de toda la muestra: {_ic(t, 'completa_arrepentimiento', f'dias_fijo_mas_hijo_d{DELTA_MESES}', 0)} "
         f"días de base en {_g(_p(t, 'entrena', 'programa_completa_padres'))} padres (IC 95% entre paréntesis). Es una "
         "cota superior de lo que agrupar podría ahorrar si el costo fijo con b = 0 fuera real, no una estimación; en el caso "
         "aditivo es cero por construcción.",
         "- Medido contra supuesto: lo medido es el ajuste y su puntaje fuera de muestra; lo supuesto es que el costo de un "
         "calendario es la suma del costo de sus meses y que un hijo puede moverse esos meses. De los meses de golpe de los "
         f"programas, el {_g(100 * _p(t, 'entrena', 'programa_test_noaislados'), 0)}% (2024 a 2026) y el "
         f"{_g(100 * _p(t, 'entrena', 'programa_completa_noaislados'), 0)}% (toda la muestra) no son aislados, y el modelo se ajustó "
         "solo con meses aislados.", "",
         "## Los dos casos de costo", "",
         "Los dos modelos de la pérdida P de un mes de golpe, en días de producción de base, con k hijos a menos de "
         f"{_g(KM_CERCA)} km fracturados en ese mes: el aditivo, P = c k, donde cada hijo cuesta lo mismo y mover hijos entre "
         "meses no cambia nada; y el fijo más hijo, P = a + b k, donde el mes cuesta a aunque tenga un solo hijo y agrupar "
         "ahorra. Se ajustan en 2023 (o en toda la muestra, para el descriptivo) y antes de usarlos se acotan: c mayor o igual "
         "que cero; b menor que cero pasa a 0 y a se vuelve la media; a menor que cero pasa a 0.", "",
         *_tabla_ajustes(t), "",
         f"En las {_g(_p(t, 'backtest', 'descartadas', 5))} repeticiones del bootstrap "
         f"de 2023, el b salió acotado en {_g(_p(t, 'backtest', 'b_acotadas'))}. El b sin acotar de 2023 es "
         f"{_g(_p(t, 'backtest', 'b_sin_acotar'), 1)} y el de toda la muestra {_g(_p(t, 'completa', 'b_sin_acotar'), 1)}: el "
         "ajuste de 2023 y el de toda la muestra dicen cosas distintas sobre el signo y ninguno es una estimación firme. El c sin "
         "acotar de 2023 no se guarda: un c igual a cero solo sale de la cota.", "",
         "## Matriz de costo por cantidad de hijos", "",
         "La pérdida de un mes con k hijos juntos contra los mismos k hijos en k meses separados, y la razón ρ entre las dos. "
         "Más allá de k = " + str(K_RESPALDADO) + " el modelo extrapola: la tabla por k de #83 respalda hasta ahí.", "",
         *_tabla_costo_k(m["costo_k"]), "",
         "## Backtest: ajustado en 2023, puntuado en 2024 a 2026", "",
         "El error cuadrático medio (ECM) y el error absoluto medio de cada modelo en los eventos aislados de 2024 a 2026, y la "
         "habilidad SK = 1 - ECM / ECM de M0, donde M0 es la media de 2023. D es la habilidad del modelo fijo más hijo menos "
         "la del aditivo: D positivo dice que el costo fijo predice mejor. Las columnas S1 repiten el ajuste con la k de 12 "
         "meses y el caudal de base como controles. El intervalo es de percentiles por pads del padre, "
         f"{_g(_p(t, 'backtest', 'descartadas', 5))} repeticiones, de las que {_g(_p(t, 'backtest', 'descartadas'))} se descartaron por "
         "ECM de M0 igual a cero.", "",
         *_tabla_backtest(t), "",
         "### Lo predicho contra lo observado por k", "",
         *_tabla_k_prueba(m["k"]), "",
         "## Arrepentimiento del calendario", "",
         f"{'Descriptivo, no una recomendación al operador. ' if sin else ''}"
         "Arrepentimiento = costo del calendario observado menos el del óptimo, en días de base. El óptimo es exacto: con a y b "
         "no negativos agrupa los meses observados, de menor a mayor, mientras el primero y el último del grupo estén a no más de "
         f"dos veces el máximo de meses que puede moverse un hijo ({DELTA_MESES} en la regla, con {_g(DELTAS_SENS[0])}, "
         f"{_g(DELTAS_SENS[1])} y {_g(DELTAS_SENS[2])} como sensibilidades). Es una entrada, no sale del dato. No hay tope de "
         "hijos por mes: la parte de los meses del programa óptimo con más de "
         f"{K_RESPALDADO} hijos es una extrapolación (en 2024 a 2026, {_g(100 * _p(t, 'entrena', f'programa_test_gt6_d{DELTA_MESES}'), 1)}% "
         f"con el máximo de {DELTA_MESES} meses; en toda la muestra, "
         f"{_g(100 * _p(t, 'entrena', f'programa_completa_gt6_d{DELTA_MESES}'), 1)}%).", "",
         "### Con el ajuste de 2023, sobre los programas de 2024 a 2026", "",
         *_tabla_arrepentimiento(t, "arrepentimiento"), "",
         "### Con el ajuste de toda la muestra (descriptivo, dentro de muestra)", "",
         *_tabla_arrepentimiento(t, "completa_arrepentimiento"), "",
         "## Valor en dólares", "",
         f"{'Descriptivo, no una recomendación al operador. ' if sin else ''}"
         "El arrepentimiento en días se pasa a volumen con el caudal de base medio de cada padre y a dólares con el costo de "
         "diferir de pipeline.decision.valor_indicativo, que es el valor tiempo de cobrar ese petróleo más tarde, no un "
         "ingreso perdido. La grilla es la de decision (precio, tasa y rezago de cobro) y son entradas ilustrativas, no un "
         f"pronóstico. Celda central: {_g(PRECIO_CENTRAL)} USD por barril, tasa {_g(TASA_CENTRAL, 2)} por año, rezago de "
         f"{_g(REZAGO_CENTRAL)} meses. El calendario «separado» pone cada hijo en su propio mes, para ver cuánto del costo ya "
         "evita la práctica. Los IC de cada fila son los de esa fila, no de una resta entre filas.", "",
         *_tabla_matriz_central(m["matriz"]), "",
         "Arrepentimiento en dólares (millones), caso fijo más hijo, con el ajuste de toda la muestra, en las 18 celdas de la "
         f"grilla (máximo de {DELTA_MESES} meses). Es el mismo arrepentimiento de arriba valuado en cada celda; el intervalo es el "
         "de la tabla en días.", "",
         *_grilla_arrepentimiento(m["matriz"], "completa"), "",
         "El mismo arrepentimiento con el ajuste de 2023 es cero en todas las celdas, porque ese ajuste no tiene costo fijo.", "",
         "## Muestra", "", *_tabla_muestra_cal(t), "",
         "## Regla fijada antes de correr", "",
         "- La regla está en el encabezado de `pipeline/calendario_golpes.py`, en el commit `c71f3a50` que trae solo el "
         "encabezado y las constantes, anterior a cualquier cálculo de este módulo. No se cambió después de ver los resultados. "
         "Se publican todos los resultados, favorables o no: «no firme» o «sin muestra» es un resultado terminado.",
         "- El plan decía solo «matrices de costo valuadas en la grilla de decision, bajo los dos casos, y un backtest ajustado en "
         "2023 que predice 2024 a 2026, con b acotado a 0 o más». La regla cerró antes de calcular lo que el plan no decía: qué "
         "elige el optimizador, contra qué se compara el arrepentimiento, cómo se puntúa el backtest y con qué umbrales, cómo "
         "se acota b y qué se hace con a, y que no se corre Colorado.",
         f"- Veredicto, en orden: «sin muestra» con menos de {_g(N_ENTRENA_MIN)} eventos o {_g(PADS_ENTRENA_MIN)} pads del padre en 2023, "
         f"menos de {_g(K_ENTRENA_DISTINTOS)} valores de k con al menos {_g(N_K_ENTRENA)} eventos, o menos de {_g(N_PRUEBA_MIN)} "
         f"eventos o {_g(PADS_PRUEBA_MIN)} pads en 2024 a 2026; «costo aditivo» si el límite alto del IC de D es menor que cero; "
         "«sostiene» si el límite bajo del IC de D y el del arrepentimiento del caso fijo más hijo son mayores que cero; «no "
         "firme» en otro caso. El veredicto no depende de la grilla de precios.",
         "- Qué se había mirado antes: lo publicado de #83 y #86 en las dos cuencas, incluidos los coeficientes agrupados y sus "
         "intervalos. No se había calculado ninguna cantidad de esta prueba: ni los eventos de 2023 y de 2024 a 2026, ni ningún "
         "calendario, arrepentimiento o puntaje fuera de muestra.",
         "- El bootstrap es por pads del padre, no por los pads hijo ni por bloques de 5 km: un programa es de un padre y tiene "
         "que moverse entero.",
         "- Colorado no se corre: su warehouse termina en 2024-12 y el backtest pide predecir hasta 2026.", "",
         "## Qué no prueba", "",
         "- Con dato mensual, «el mismo mes» no es «al mismo tiempo», y un hijo que se mueve " + str(DELTA_MESES) + " meses no es un "
         "hijo que se mueve en la práctica: hay que perforar, fracturar y completar en un orden que el dato público no ve. El "
         "optimizador no tiene tope de hijos ni de equipos por mes.",
         "- Solo el lado del padre: el costo de producir un hijo antes o después y lo que el hijo pierde por el padre no están.",
         "- La pérdida es volumen diferido contra la trayectoria de los controles en la ventana, no petróleo perdido. Los "
         "dólares son el valor tiempo de cobrarlo más tarde, con precios y tasas que son entradas.",
         "- La referencia de la pérdida usa los controles de toda la muestra, incluidos los de 2024 a 2026: no es del todo "
         "fuera de muestra, aunque el modelo que se ajusta y se predice sí lo es.",
         "- Un solo año de entrenamiento: los coeficientes de 2023 pueden no valer para 2024 a 2026, y el IC mide el ruido del "
         "muestreo, no ese cambio.",
         "- El costo de un calendario como suma del de sus meses es un supuesto: los modelos se ajustaron en meses aislados y "
         "una parte grande de los meses de los programas no lo es.", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ main

def _resumen(t: dict[str, list[tuple]]) -> None:
    p = {(f[0], f[1]): f for f in t["prueba"]}
    f = p[("backtest", "d")]
    print(f"[calendario_golpes] D {f[2]} (IC {f[3]} a {f[4]}; n {f[5]}): {f[6]}")


def main(path=DATA / "warehouse.duckdb", reps: int = REPS) -> None:
    """Vaca Muerta sobre su warehouse: las cuatro tablas del modulo."""
    con = duckdb.connect(str(path))
    try:
        D = gp.cargar(con)
        _comprueba_83(con, D)
        t = calcular(D, reps)
        escribir(con, t)
    finally:
        con.close()
    _resumen(t)


if __name__ == "__main__":
    main()
