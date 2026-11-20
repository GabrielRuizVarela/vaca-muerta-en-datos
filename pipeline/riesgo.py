"""Riesgo de golpe fuerte: cuan probable es que un padre cercano pierda mas de 30 puntos de indice al mes 1 de la fractura de un hijo.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.riesgo

Para que sirve. El modelo de costo puntual (wiki/hallazgos/anisotropia.md) predice barriles y falla: su R2 fuera de muestra es de
-0,15. Esta pagina hace la pregunta que un operador puede usar: dado un padre y un hijo que se va a fracturar cerca, cuan probable
es un golpe fuerte. Es un modelo de clasificacion probado hacia adelante en el tiempo (entrena con los hijos fracturados hasta
2022 y se prueba con los de 2023 y 2024), con la distancia entre ramas y la geometria de las ramas entre sus variables.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los modelos que se calculen, favorables o no. Un veredicto
"no predice el riesgo" o "sin muestra" es un resultado terminado: no se rediseña la regla para evitarlo. Fuente del plan: fase 4
del proyecto, unidad U5.

Que se habia mirado antes de fijarla
- Publicado en el repo: la pagina de anisotropia (el modelo puntual, su R2 de -0,15 fuera de muestra), la de trayectorias y la de
  alcance entre ramas (la brecha del mes 1 por banda de distancia entre ramas). Ninguna probabilidad de golpe fuerte se calculo, y
  ningun ajuste de clasificacion se corrio, antes de fijar esta regla.
- Solo se conto cuantos eventos cercanos hay en cada ventana del corte (sin mirar ningun resultado): 673 de entrenamiento y 492 de
  prueba con el indice del mes 1 medido, de los cuales 515 y 302 tienen la rama del par medida. Con eso la regla de "sin muestra"
  (menos de 300 eventos de prueba) no es imposible de antemano.

Datos y eventos (el modelo principal; solo de el sale el veredicto)
- Eventos: las filas de int_interferencia_evento con banda = 'cercano' (el hijo mas cercano en superficie a menos de 1 km del padre;
  desempate por el menor id) que tienen el indice del mes 1 medido en int_interferencia_mes (k = 1, indice no nulo). Son los
  mismos eventos cercanos del estudio principal (placebo.marco, banda 0): un padre con al menos 6 meses de produccion y una base de
  los meses -3 a -1 mayor que 1 m3/d. Su hijo es `hijo_cercano` y su mes es `mes_frac`, el mes de fractura de ese hijo.
- Resultado ("golpe fuerte"): 1 si el indice del mes 1 del padre menos la mediana del indice del mes 1 de los controles de su mismo
  grupo de edad (`grupo_edad`; mart_interferencia_brecha con k = 1, columna `indice_control`, la mediana de los controles de 2 a
  5 km de ese grupo en todo el estudio, la misma que usa la brecha principal) es MENOR que UMBRAL_GOLPE (-0,30, es decir -30 puntos
  de indice). 0 en otro caso. La mediana de control sale de todo el periodo y no solo del entrenamiento: es la definicion del
  resultado, la del estudio principal, y no una variable del modelo; esta pagina lo dice en "Que NO prueba".
- Corte por fecha de fractura del hijo (`mes_frac`): entrenamiento de 2016-01 a 2022-12 (INICIO_ENTRENAMIENTO, FIN_ENTRENAMIENTO);
  prueba de 2023-01 a 2024-12 (INICIO_PRUEBA, FIN_PRUEBA). Los eventos de otras fechas no entran y se cuentan en la pagina. Los
  eventos de la prueba no se usan para elegir nada: no hay ningun ajuste.
- Cobertura de las ramas: las trayectorias laterales cubren alrededor del 76 al 98% de los hijos horizontales fracturados de 2016 a
  2023 (86% en conjunto) pero solo el 39% de los de 2024 y el 25% de los de 2025. La muestra es entonces sobre todo de 2016 a 2023
  y la ventana de prueba de 2023 a 2024 tiene pocos eventos de 2024 con la rama medida. Los eventos sin rama medida NO se
  descartan: entran con la distancia entre ramas faltante y su indicador (ver abajo). La pagina y el README lo dicen junto al
  veredicto.

Variables (columnas fijas; para el modelo principal son todas estas)
  km                    km_min de int_interferencia_evento: la distancia de superficie al hijo cercano.
  m_min                 la menor distancia entre las ramas en planta del par (hijo_cercano, padre), en metros, de mart_trayectoria_par.
  falta_rama            1 si el par (hijo_cercano, padre) no esta en mart_trayectoria_par (rama del hijo o del padre sin medir), 0 si esta.
  dif_azimut            dif_azimut de mart_par_rama para ese par, en grados (0 a 90).
  posicion_costado, posicion_mixto, posicion_punta   indicadoras de `posicion` de mart_par_rama para ese par.
  edad_meses            edad_meses del padre en el mes del evento (int_interferencia_evento).
  acum_m3_por_m         el petroleo acumulado del padre (m3, suma de fct_produccion.petroleo_m3 de los meses ANTERIORES a mes_frac) sobre
                        el largo de su rama horizontal en metros (dim_fractura_pozo.rama_horizontal_m del padre). Metros cubicos por metro.
  falta_largo_padre     1 si el padre no tiene rama_horizontal_m (nula o 0), 0 si la tiene.
  base_m3_d             base_m3_d de int_interferencia_evento: el caudal base del padre, de los meses -3 a -1.
  arena_por_m           toneladas de arena del hijo cercano (dim_fractura_pozo.arena_tn) sobre el largo de su rama horizontal en metros.
  etapas                dim_fractura_pozo.etapas del hijo cercano.
  falta_largo_hijo      1 si el hijo cercano no tiene rama_horizontal_m (nula o 0), 0 si la tiene.
  mismo_pad             1 si el padre y el hijo cercano tienen el mismo pad_id (int_pozo_ubicacion), 0 si no.
  hijos_1km             hijos_1km de int_interferencia_evento: los hijos fracturados ese mes a menos de 1 km del padre.
  operador_*, area_*    indicadoras del operador y del area (int_interferencia_evento, trim) del PADRE. Un nivel con menos de MIN_NIVEL (30)
                        eventos de entrenamiento se junta en `otro` (en operador y en area por separado), y un nivel que no aparece en
                        el entrenamiento va a `otro`.
- Faltantes: m_min, dif_azimut, acum_m3_por_m y arena_por_m faltantes se reemplazan por la mediana del ENTRENAMIENTO de esa columna
  (sobre las filas donde esta medida); posicion_* faltantes valen 0. El indicador de falta correspondiente (falta_rama,
  falta_largo_padre, falta_largo_hijo) dice cuales se reemplazaron. Esos tres indicadores y las columnas de arriba son todas las
  variables; no hay mas. (El plan nombra "arena por metro y etapas", "acumulado por metro" y "distancia minima con indicador de
  falta"; los indicadores de largo faltante son el mismo arreglo de la falta para las dos columnas por metro y se fijan aca,
  antes de calcular, porque el largo de la rama falta en cerca de una cuarta parte de los padres cercanos.)
- Estandarizacion: cada columna, indicadoras incluidas, se centra y se divide por su media y su desvio del ENTRENAMIENTO; una columna
  con desvio 0 en el entrenamiento queda en 0.

Modelo principal (el unico del que sale el veredicto)
- Regresion logistica con penalizacion L2, C = C_REGULARIZACION (1,0): minimiza 0,5 por la suma de los cuadrados de los coeficientes
  mas C por la suma de la perdida logistica; el termino constante no se penaliza; sin pesos de clase; sin ningun ajuste de C ni de
  variables. Se resuelve por Newton (IRLS) hasta que el cambio maximo de un coeficiente sea menor que TOL_NEWTON o se
  llegue a MAX_ITER, de modo que el resultado no depende del azar ni del orden de las filas.
- Referencia: la prevalencia de golpe fuerte del ENTRENAMIENTO por area (del padre); un area sin eventos de entrenamiento recibe la
  prevalencia de todo el entrenamiento. Es la probabilidad que la referencia da a cada evento de la prueba.

Estadisticos de la prueba (eventos de la ventana de prueba)
- AUC: la probabilidad de que un evento con golpe fuerte reciba mas riesgo que uno sin golpe (Mann-Whitney, empates a medias).
- Puntaje de Brier del modelo y de la referencia, y la habilidad de Brier BSS = 1 menos el Brier del modelo sobre el de la referencia.
- Intervalos: bootstrap de percentiles 95% (2,5 y 97,5) que remuestrea PADS DE HIJO COMPLETOS (el `pad_id` del hijo cercano) de los
  eventos de prueba, REPS_BOOT repeticiones y semilla SEMILLA_RIESGO. El modelo se ajusta una vez con el entrenamiento y no se
  reajusta en cada remuestra: el intervalo cubre el muestreo de la prueba y no la variacion del entrenamiento (la pagina lo dice).
  Una remuestra en que falta una de las dos clases se descarta y se cuenta. Las remuestras son las mismas para todos los modelos.

Veredicto (solo del modelo principal)
  1. "sin muestra": la prueba tiene menos de N_MIN_PRUEBA (300) eventos con el resultado medido, o le falta una de las dos clases.
  2. "predice el riesgo": AUC de la prueba de AUC_MIN (0,65) o mas Y limite bajo de su IC mayor que AUC_IC_BAJO (0,55), Y la habilidad
     de Brier mayor que 0 con el limite bajo de su IC mayor que 0 (el IC excluye cero).
  3. "no predice el riesgo": en cualquier otro caso.
  El orden es ese.

Se publica (sin veredicto; no cambia el de arriba)
  * El modelo principal, con su AUC, Brier, habilidad, IC, la prevalencia de entrenamiento y de prueba, y los coeficientes
    estandarizados (descriptivos, sin IC y sin prueba de significancia).
  * La calibracion por decil: los eventos de la prueba ordenados por el riesgo predicho (orden estable) en 10 grupos de tamaño casi
    igual (los primeros reciben el resto), con la cantidad, el riesgo medio predicho y la frecuencia observada de cada uno.
  * Modelos alternativos, con la misma muestra, el mismo corte y el mismo C, y los mismos intervalos:
      M2 "sin geometria de rama": todas las variables menos m_min, falta_rama, dif_azimut y posicion_*.
      M3 "solo la distancia de superficie": solo km.
      M4 "con rama medida": el modelo principal ajustado y probado solo con los eventos con la rama del par medida (sin falta_rama);
          su referencia es la prevalencia de entrenamiento por area de ESE subconjunto.
    Para M2 y M3 se publica tambien la diferencia de AUC contra el principal, con IC por las mismas remuestras.
  * El AUC del modelo principal en los eventos de la prueba con y sin rama medida, y los eventos de la prueba por año del hijo
    con cuantos tienen la rama medida.
  * Sensibilidades del umbral del resultado: UMBRALES_SENSIBILIDAD (-0,20 y -0,40). El modelo principal se reajusta con el otro
    resultado y se prueba igual. No cambian ningun veredicto.

Que NO prueba
  * Es una asociacion probada hacia adelante, sin afirmacion causal: un riesgo alto no dice que la fractura del hijo cause el golpe.
  * La mediana de control del resultado sale de todo el periodo (2016 a 2026), como en el estudio principal; no es una variable del
    modelo pero el resultado de los eventos de entrenamiento y el de los de prueba comparten esa mediana.
  * El entrenamiento tiene pocos eventos (cientos) y muchas variables: un "no predice el riesgo" es contra estas variables y
    este modelo (logistico L2 sin ajuste), no prueba que nada prediga el riesgo. Los IC cubren el muestreo de la prueba y no el
    del entrenamiento.
  * La rama medida cubre sobre todo hijos de 2016 a 2023: las variables de rama de la prueba estan medidas en una parte de los
    eventos y la muestra no dice nada de los hijos de 2025 en adelante.
  * El alcance de la muestra son los eventos con el hijo cercano a menos de 1 km en superficie: un padre con la rama cerca pero la
    boca lejos no esta.
  * La referencia por area usa la prevalencia de entrenamiento: una mejora sobre ella no es una mejora sobre un operador que ya
    conoce su campo.

Que cambia con cada veredicto (en la pagina, el README y los limites)
  * "predice el riesgo": la pagina da el AUC y la habilidad con el IC, la calibracion por decil y la cota de lo que queda sin
    explicar; los limites dicen que es una puntuacion de riesgo probada en 2023 y 2024 y no un pronostico de barriles.
  * "no predice el riesgo": la pagina dice que con estas variables el modelo no rankea los golpes fuertes mejor que la tasa por area
    fuera de muestra, igual que el modelo puntual de barriles; los limites lo dicen sin leerlo como que no haya riesgo.
  * "sin muestra": la pagina dice cuantos eventos de prueba hay y que el dato no decide.
  * Nada de esto cambia data/prospectiva_congelada.json ni las reglas P1 y P2.
"""
from __future__ import annotations

import datetime

import duckdb
import numpy as np

from pipeline.alcance_rama import _cobertura
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

SEMILLA_RIESGO = 20261115 + 100         # SEMILLA de pipeline.costo mas 100: una semilla propia del bootstrap por pads de hijo
REPS_BOOT = 400                         # repeticiones del bootstrap (como el resto del estudio)
K_TITULAR = 1                           # el mes del indice del resultado
UMBRAL_GOLPE = -0.30                    # golpe fuerte: indice del mes 1 menos la mediana de control, menor que esto (-30 puntos)
UMBRALES_SENSIBILIDAD = (-0.20, -0.40)  # sensibilidades del resultado, sin veredicto
INICIO_ENTRENAMIENTO = "2016-01-01"     # mes de fractura del hijo, incluido
FIN_ENTRENAMIENTO = "2022-12-01"        # mes de fractura del hijo, incluido
INICIO_PRUEBA = "2023-01-01"            # mes de fractura del hijo, incluido
FIN_PRUEBA = "2024-12-01"               # mes de fractura del hijo, incluido
C_REGULARIZACION = 1.0                  # L2 con C = 1,0 sin ajuste
TOL_NEWTON = 1e-8                       # cambio maximo de un coeficiente para parar
MAX_ITER = 100                          # iteraciones maximas de Newton
MIN_NIVEL = 30                          # eventos de entrenamiento minimos para que un operador o un area tenga su indicadora
N_MIN_PRUEBA = 300                      # eventos de prueba con el resultado medido para que haya veredicto
AUC_MIN = 0.65                          # predice el riesgo: AUC de la prueba de esto o mas
AUC_IC_BAJO = 0.55                      # ... con el limite bajo del IC del AUC por encima de esto
BSS_MIN = 0.0                           # ... y la habilidad de Brier por encima de esto, con el limite bajo del IC por encima tambien
N_DECILES = 10                          # grupos de la calibracion
VEREDICTOS = ("sin muestra", "predice el riesgo", "no predice el riesgo")

# ------------------------------------------------------------------ carga

SQL_EVENTOS = """\
select e.padre, e.mes_frac, e.hijo_cercano as hijo, e.km_min, e.hijos_1km, e.base_m3_d, e.edad_meses, e.grupo_edad,
       e.operador, trim(e.area) as area, hu.pad_id as pad_hijo, e.pad_id as pad_padre, m.indice, b.indice_control,
       par.m_min, pr.dif_azimut, pr.posicion, fp.rama_horizontal_m as largo_padre, fh.rama_horizontal_m as largo_hijo,
       fh.arena_tn, fh.etapas,
       (select sum(x.petroleo_m3) from fct_produccion x where x.pozo_id = e.padre and x.mes < e.mes_frac) as acum_m3
from int_interferencia_evento e
join int_interferencia_mes m on m.padre = e.padre and m.mes_frac = e.mes_frac and m.k = 1
join mart_interferencia_brecha b on b.grupo_edad = e.grupo_edad and b.k = 1
join int_pozo_ubicacion hu on hu.pozo_id = e.hijo_cercano
left join mart_trayectoria_par par on par.hijo = e.hijo_cercano and par.padre = e.padre
left join mart_par_rama pr on pr.hijo = e.hijo_cercano and pr.padre = e.padre
left join dim_fractura_pozo fp on fp.pozo_id = e.padre
left join dim_fractura_pozo fh on fh.pozo_id = e.hijo_cercano
where e.banda = 'cercano' and m.indice is not null
order by e.padre, e.mes_frac
"""

# las variables fijas del modelo principal, en el orden de la regla
COLS_BASE = ("km", "m_min", "falta_rama", "dif_azimut", "posicion_costado", "posicion_mixto", "posicion_punta",
             "edad_meses", "acum_m3_por_m", "falta_largo_padre", "base_m3_d", "arena_por_m", "etapas",
             "falta_largo_hijo", "mismo_pad", "hijos_1km")
VARS_RAMA = ("m_min", "falta_rama", "dif_azimut", "posicion_costado", "posicion_mixto", "posicion_punta")
IMPUTAN = ("m_min", "dif_azimut", "acum_m3_por_m", "arena_por_m")   # faltantes con mediana del entrenamiento
MODELOS_DAUC = ("m2_sin_rama", "m3_solo_km")                          # los que publican diferencia de AUC

COLS_MODELO = [("modelo", "varchar"), ("umbral", "double"), ("n_entrenamiento", "integer"),
                ("n_prueba", "integer"), ("prevalencia_entrenamiento", "double"), ("prevalencia_prueba", "double"),
                ("auc", "double"), ("auc_ic_bajo", "double"), ("auc_ic_alto", "double"),
                ("brier", "double"), ("brier_ref", "double"), ("bss", "double"),
                ("bss_ic_bajo", "double"), ("bss_ic_alto", "double"),
                ("dauc", "double"), ("dauc_ic_bajo", "double"), ("dauc_ic_alto", "double"),
                ("descartadas", "integer")]
COLS_PRUEBA = [("veredicto", "varchar"), ("n_entrenamiento", "integer"), ("n_prueba", "integer"),
               ("eventos", "integer"), ("fuera_ventana", "integer"), ("pads_prueba", "integer"),
               ("reps", "integer")]
COLS_CALIBRACION = [("decil", "integer"), ("n", "integer"), ("pred_media", "double"), ("obs_media", "double")]
COLS_COEF = [("variable", "varchar"), ("coef", "double")]
COLS_ANIO = [("anio", "integer"), ("ventana", "varchar"), ("eventos", "integer"),
             ("con_rama", "integer"), ("golpes", "integer")]
COLS_RAMA = [("grupo", "varchar"), ("n", "integer"), ("golpes", "integer"), ("auc", "double")]


def _armar(filas: list[tuple]) -> dict:
    """De las filas del SQL a un dict de arreglos de numpy (los nulos de numero son NaN)."""
    def textos(i):
        return np.array([f[i] for f in filas], dtype=object)

    def floats(i):
        return np.array([np.nan if f[i] is None else float(f[i]) for f in filas], dtype=float)

    return {
        "padre": textos(0), "mes_frac": textos(1), "hijo": textos(2),
        "km_min": floats(3), "hijos_1km": floats(4), "base_m3_d": floats(5),
        "edad_meses": floats(6), "grupo_edad": textos(7),
        "operador": np.array([("" if f[8] is None else str(f[8])) for f in filas], dtype=object),
        "area": np.array([("" if f[9] is None else str(f[9])) for f in filas], dtype=object),
        "pad_hijo": textos(10), "pad_padre": textos(11),
        "indice": floats(12), "indice_control": floats(13),
        "m_min": floats(14), "dif_azimut": floats(15), "posicion": textos(16),
        "largo_padre": floats(17), "largo_hijo": floats(18), "arena_tn": floats(19),
        "etapas": floats(20), "acum_m3": floats(21),
    }


def derivar(C: dict) -> dict:
    """Agrega a C las columnas derivadas que usan los modelos: faltantes, indicadores y resultado."""
    C = dict(C)
    C["km"] = C["km_min"].astype(float)
    C["falta_rama"] = np.isnan(C["m_min"]).astype(float)
    pos = np.array([("" if p is None else str(p)) for p in C["posicion"]], dtype=object)
    C["posicion_costado"] = (pos == "costado").astype(float)
    C["posicion_mixto"] = (pos == "mixto").astype(float)
    C["posicion_punta"] = (pos == "punta").astype(float)
    largo_padre = C["largo_padre"]
    largo_hijo = C["largo_hijo"]
    falta_padre = (~np.isfinite(largo_padre)) | (largo_padre == 0)
    falta_hijo = (~np.isfinite(largo_hijo)) | (largo_hijo == 0)
    C["falta_largo_padre"] = falta_padre.astype(float)
    C["falta_largo_hijo"] = falta_hijo.astype(float)
    C["acum_m3_por_m"] = np.where(falta_padre, np.nan,
                                  C["acum_m3"] / np.where(falta_padre, 1.0, largo_padre))
    C["arena_por_m"] = np.where(falta_hijo, np.nan,
                                C["arena_tn"] / np.where(falta_hijo, 1.0, largo_hijo))
    C["mismo_pad"] = np.array([1.0 if (a is not None and b is not None and a == b) else 0.0
                               for a, b in zip(C["pad_hijo"], C["pad_padre"])])
    dif = C["indice"] - C["indice_control"]
    C["golpe"] = (dif < UMBRAL_GOLPE).astype(float)
    C["golpe_s1"] = (dif < UMBRALES_SENSIBILIDAD[0]).astype(float)
    C["golpe_s2"] = (dif < UMBRALES_SENSIBILIDAD[1]).astype(float)
    anio = np.array([m.year if m is not None else 0 for m in C["mes_frac"]], dtype=int)
    mes = np.array([m.month if m is not None else 0 for m in C["mes_frac"]], dtype=int)
    C["anio"] = anio
    C["ym"] = anio * 12 + mes
    C["n"] = len(anio)
    return C


def cargar(con) -> dict:
    """Los eventos cercanos con el indice del mes 1 medido, con sus variables derivadas."""
    return derivar(_armar(con.execute(SQL_EVENTOS).fetchall()))


# ------------------------------------------------------------------ ventanas

def _ym(iso: str) -> int:
    d = datetime.date.fromisoformat(iso)
    return d.year * 12 + d.month


def ventanas(C: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Los indices de entrenamiento, de prueba y de los eventos fuera de las dos ventanas."""
    ym = C["ym"]
    i_tr = np.flatnonzero((ym >= _ym(INICIO_ENTRENAMIENTO)) & (ym <= _ym(FIN_ENTRENAMIENTO)))
    i_te = np.flatnonzero((ym >= _ym(INICIO_PRUEBA)) & (ym <= _ym(FIN_PRUEBA)))
    i_fu = np.flatnonzero((ym < _ym(INICIO_ENTRENAMIENTO)) | (ym > _ym(FIN_PRUEBA)))
    return i_tr.astype(int), i_te.astype(int), i_fu.astype(int)


# ------------------------------------------------------------------ matriz de diseño

def _niveles(C: dict, campo: str, idx_train) -> list[str]:
    """Los niveles con indicadora propia: los del entrenamiento con al menos MIN_NIVEL eventos, mas 'otro'."""
    vals = C[campo]
    conteo: dict = {}
    for i in idx_train:
        conteo[vals[i]] = conteo.get(vals[i], 0) + 1
    return sorted(v for v, k in conteo.items() if k >= MIN_NIVEL) + ["otro"]


def matriz(C: dict, cols, idx_train, idx_test) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Matrices de diseño de entrenamiento y prueba, estandarizadas con el entrenamiento.

    `cols` acepta los nombres de COLS_BASE y los grupos "operador" y "area", que se expanden en
    sus indicadoras. Un nivel con menos de MIN_NIVEL eventos de entrenamiento, o que no aparece
    en el entrenamiento, va a "otro" (en operador y en area por separado).
    """
    idx_train = np.asarray(idx_train, dtype=int)
    idx_test = np.asarray(idx_test, dtype=int)
    nombres: list[str] = []
    bloques_tr: list[np.ndarray] = []
    bloques_te: list[np.ndarray] = []
    for col in cols:
        if col in ("operador", "area"):
            niveles = _niveles(C, col, idx_train)
            propios = set(niveles[:-1])
            vals = C[col]
            mapa = np.array([v if v in propios else "otro" for v in vals], dtype=object)
            for lv in niveles:
                nombres.append(f"{col}_{lv}")
                bloques_tr.append((mapa[idx_train] == lv).astype(float))
                bloques_te.append((mapa[idx_test] == lv).astype(float))
            continue
        v = np.asarray(C[col], dtype=float)
        if col in IMPUTAN:
            mid = v[idx_train][~np.isnan(v[idx_train])]
            med = float(np.median(mid)) if mid.size else 0.0
            if not np.isfinite(med):
                med = 0.0
            a = v[idx_train].copy()
            b = v[idx_test].copy()
            a[np.isnan(a)] = med
            b[np.isnan(b)] = med
        else:
            a = np.nan_to_num(v[idx_train].copy(), nan=0.0)
            b = np.nan_to_num(v[idx_test].copy(), nan=0.0)
        nombres.append(col)
        bloques_tr.append(a)
        bloques_te.append(b)
    Xtr = np.column_stack(bloques_tr) if bloques_tr else np.zeros((len(idx_train), 0))
    Xte = np.column_stack(bloques_te) if bloques_te else np.zeros((len(idx_test), 0))
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0, ddof=0)
    constante = sd == 0
    escala = np.where(constante, 1.0, sd)
    Ztr = (Xtr - mu) / escala
    Zte = (Xte - mu) / escala
    if constante.any():
        Ztr[:, constante] = 0.0
        Zte[:, constante] = 0.0
    return Ztr, Zte, nombres


# ------------------------------------------------------------------ modelo

def _sigmoide(z) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    out = np.empty(z.shape, dtype=float)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _intercepto(X) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    return np.column_stack([np.ones(len(X)), X])


def ajustar(X, y, c: float = C_REGULARIZACION) -> np.ndarray:
    """Logistica con L2 (C) resuelta por Newton: penaliza los coeficientes menos el intercepto."""
    Xa = _intercepto(X)
    y = np.asarray(y, dtype=float)
    w = np.zeros(Xa.shape[1])
    for _ in range(MAX_ITER):
        p = _sigmoide(Xa @ w)
        g = w.copy()
        g[0] = 0.0
        g = g + c * (Xa.T @ (p - y))
        s = p * (1.0 - p)
        H = c * (Xa.T @ (s[:, None] * Xa))
        H[1:, 1:] += np.eye(Xa.shape[1] - 1)
        try:
            dw = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            dw = np.linalg.lstsq(H, g, rcond=None)[0]
        w = w - dw
        if np.max(np.abs(dw)) < TOL_NEWTON:
            break
    return w


def gradiente(X, y, w, c: float = C_REGULARIZACION) -> np.ndarray:
    """El gradiente del objetivo penalizado en `w` (para chequear la solucion)."""
    Xa = _intercepto(X)
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)
    p = _sigmoide(Xa @ w)
    g = w.copy()
    g[0] = 0.0
    return g + c * (Xa.T @ (p - y))


def predecir(w, X) -> np.ndarray:
    """La probabilidad que el modelo da a cada fila de X."""
    return _sigmoide(_intercepto(X) @ np.asarray(w, dtype=float))


# ------------------------------------------------------------------ estadisticos

def _auc_pesado(y, p, w) -> float | None:
    """AUC de Mann-Whitney con empates a la mitad, con pesos por evento (None si falta una clase)."""
    y = np.asarray(y)
    p = np.asarray(p, dtype=float)
    w = np.asarray(w, dtype=float)
    pos = y == 1
    neg = y == 0
    if not pos.any() or not neg.any():
        return None
    orden = np.argsort(p[neg], kind="mergesort")
    pv = p[neg][orden]
    wv = w[neg][orden]
    acum = np.concatenate([[0.0], np.cumsum(wv)])
    x = p[pos]
    izquierda = np.searchsorted(pv, x, side="left")
    derecha = np.searchsorted(pv, x, side="right")
    menor = acum[izquierda]
    igual = acum[derecha] - acum[izquierda]
    w_pos = float(w[pos].sum())
    w_neg = float(w[neg].sum())
    if w_pos == 0 or w_neg == 0:
        return None
    return float(np.sum(w[pos] * (menor + 0.5 * igual))) / (w_pos * w_neg)


def auc(y, p) -> float | None:
    """La probabilidad de que un evento con golpe fuerte reciba mas riesgo que uno sin golpe."""
    y = np.asarray(y)
    p = np.asarray(p, dtype=float)
    return _auc_pesado(y, p, np.ones(len(p)))


def _brier_pesado(y, p, w) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    w = np.asarray(w, dtype=float)
    return float(np.sum(w * (p - y) ** 2) / np.sum(w))


def brier(y, p) -> float:
    """El puntaje de Brier: el error cuadratico medio de la probabilidad."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def referencia_area(area_tr, y_tr, area_te) -> np.ndarray:
    """La probabilidad de la referencia: prevalencia de entrenamiento por area; area sin training, la global."""
    area_tr = np.asarray(area_tr, dtype=object)
    area_te = np.asarray(area_te, dtype=object)
    y_tr = np.asarray(y_tr, dtype=float)
    global_ = float(y_tr.mean()) if y_tr.size else 0.0
    previas: dict = {}
    for a in np.unique(area_tr):
        previas[a] = float(y_tr[area_tr == a].mean())
    return np.array([previas.get(a, global_) for a in area_te], dtype=float)


def codigos_pad(valores) -> np.ndarray:
    """Un codigo por pad de hijo (los que no tienen pad comparten codigo)."""
    return np.array([("<sin_pad>" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v))
                     for v in valores], dtype=object)


def bootstrap(modelos: dict, pad_codes_all, reps: int = REPS_BOOT,
              semilla: int = SEMILLA_RIESGO) -> dict:
    """Los intervalos por bootstrap de pads de hijo completo, con las mismas remuestras para todos.

    `modelos[nombre]` trae "y", "p", "ref" y "pad" (el pad de cada fila de prueba del modelo).
    `pad_codes_all` son los pads de TODOS los eventos de prueba: las remuestras salen de ahi.
    Una remuestra sin una de las dos clases se descarta para ese modelo y se cuenta.
    """
    universo = np.unique(np.asarray(pad_codes_all, dtype=object))
    lugar = {p: i for i, p in enumerate(universo)}
    n_pads = len(universo)
    res = {nombre: {"auc": [], "bss": [], "dauc": [], "descartadas": 0} for nombre in modelos}
    codigos = {}
    for nombre, m in modelos.items():
        codigos[nombre] = np.array([lugar[p] for p in np.asarray(m["pad"], dtype=object)], dtype=int)
    rng = np.random.default_rng(semilla)
    for _ in range(reps):
        sorteo = rng.integers(0, n_pads, size=n_pads)
        conteo = np.bincount(sorteo, minlength=n_pads)
        aucs = {}
        for nombre, m in modelos.items():
            y = np.asarray(m["y"])
            p = np.asarray(m["p"], dtype=float)
            ref = np.asarray(m["ref"], dtype=float)
            w = conteo[codigos[nombre]]
            if w.sum() == 0 or w[y == 1].sum() == 0 or w[y == 0].sum() == 0:
                res[nombre]["auc"].append(None)
                res[nombre]["bss"].append(None)
                res[nombre]["descartadas"] += 1
                aucs[nombre] = None
                continue
            a = _auc_pesado(y, p, w)
            br = _brier_pesado(y, p, w)
            br_ref = _brier_pesado(y, ref, w)
            res[nombre]["auc"].append(a)
            res[nombre]["bss"].append(1.0 - br / br_ref if br_ref > 0 else None)
            aucs[nombre] = a
        if "principal" in modelos:
            a_prin = aucs.get("principal")
            for nombre in MODELOS_DAUC:
                if nombre not in res or a_prin is None or aucs.get(nombre) is None:
                    continue
                res[nombre]["dauc"].append(aucs[nombre] - a_prin)
    for nombre, r in res.items():
        r["auc_ic"] = _ic(r["auc"])
        r["bss_ic"] = _ic(r["bss"])
        r["dauc_ic"] = _ic(r["dauc"])
    return res


def _ic(valores) -> tuple[float | None, float | None]:
    """El intervalo de percentiles 2,5 y 97,5 de las remuestras validas."""
    v = np.array([x for x in valores if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return (None, None)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return (float(lo), float(hi))


def calibracion(y, p) -> list[tuple]:
    """La calibracion por decil: eventos de prueba ordenados por riesgo, en N_DECILES grupos."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    orden = np.argsort(p, kind="stable")
    filas = []
    for i, grupo in enumerate(np.array_split(orden, N_DECILES), start=1):
        if grupo.size == 0:
            filas.append((i, 0, None, None))
            continue
        filas.append((i, int(grupo.size), float(p[grupo].mean()), float(y[grupo].mean())))
    return filas


def veredicto(n_test: int, y_test, auc_: float | None, auc_lo: float | None,
              bss: float | None, bss_lo: float | None) -> str:
    """El veredicto del modelo principal, en el orden de la regla."""
    y = np.asarray(y_test)
    if n_test < N_MIN_PRUEBA:
        return "sin muestra"
    if y.size and (int((y == 1).sum()) == 0 or int((y == 0).sum()) == 0):
        return "sin muestra"
    if auc_ is None or bss is None or auc_lo is None or bss_lo is None:
        return "no predice el riesgo"
    if auc_ >= AUC_MIN and auc_lo > AUC_IC_BAJO and bss > BSS_MIN and bss_lo > BSS_MIN:
        return "predice el riesgo"
    return "no predice el riesgo"


# ------------------------------------------------------------------ calculo

def _modelos(C: dict, idx_train, idx_test) -> dict:
    """Los modelos de la regla: (cols, idx_entrenamiento, idx_prueba, clave del resultado)."""
    base = list(COLS_BASE)
    completo = base + ["operador", "area"]
    sin_rama = [c for c in base if c not in VARS_RAMA] + ["operador", "area"]
    sin_falta = [c for c in base if c != "falta_rama"] + ["operador", "area"]
    con_rama_tr = idx_train[C["falta_rama"][idx_train] == 0]
    con_rama_te = idx_test[C["falta_rama"][idx_test] == 0]
    return {
        "principal": (completo, idx_train, idx_test, "golpe"),
        "m2_sin_rama": (sin_rama, idx_train, idx_test, "golpe"),
        "m3_solo_km": (["km"], idx_train, idx_test, "golpe"),
        "m4_con_rama": (sin_falta, con_rama_tr, con_rama_te, "golpe"),
        "s1_umbral_m20": (completo, idx_train, idx_test, "golpe_s1"),
        "s2_umbral_m40": (completo, idx_train, idx_test, "golpe_s2"),
    }


UMBRAL_MODELO = {"principal": UMBRAL_GOLPE, "m2_sin_rama": UMBRAL_GOLPE, "m3_solo_km": UMBRAL_GOLPE,
                 "m4_con_rama": UMBRAL_GOLPE, "s1_umbral_m20": UMBRALES_SENSIBILIDAD[0],
                 "s2_umbral_m40": UMBRALES_SENSIBILIDAD[1]}


def calcular(C: dict, reps: int = REPS_BOOT) -> dict[str, list[tuple]]:
    """Las seis tablas de la pagina, listas para escribir."""
    idx_train, idx_test, idx_fuera = ventanas(C)
    specs = _modelos(C, idx_train, idx_test)
    ajustados = {}
    for nombre, (cols, i_tr, i_te, clave) in specs.items():
        Xtr, Xte, nombres = matriz(C, cols, i_tr, i_te)
        y_tr = C[clave][i_tr]
        y_te = C[clave][i_te]
        w = ajustar(Xtr, y_tr)
        p = predecir(w, Xte)
        ref = referencia_area(C["area"][i_tr], y_tr, C["area"][i_te])
        ajustados[nombre] = {"cols": cols, "i_tr": i_tr, "i_te": i_te, "nombres": nombres, "w": w,
                              "y_tr": y_tr, "y_te": y_te, "p": p, "ref": ref}
    pads_todos = codigos_pad(C["pad_hijo"][idx_test])
    para_boot = {nombre: {"y": d["y_te"], "p": d["p"], "ref": d["ref"],
                           "pad": codigos_pad(C["pad_hijo"][d["i_te"]])} for nombre, d in ajustados.items()}
    boot = bootstrap(para_boot, pads_todos, reps=reps)

    filas_modelo = []
    a_principal = auc(ajustados["principal"]["y_te"], ajustados["principal"]["p"])
    for nombre, d in ajustados.items():
        y_te = d["y_te"]
        a = auc(y_te, d["p"])
        br = brier(y_te, d["p"])
        br_ref = brier(y_te, d["ref"])
        hab = 1.0 - br / br_ref if br_ref > 0 else None
        ic_auc = boot[nombre]["auc_ic"]
        ic_bss = boot[nombre]["bss_ic"]
        ic_dauc = boot[nombre]["dauc_ic"]
        dauc = (a - a_principal) if (nombre in MODELOS_DAUC and a is not None and a_principal is not None) else None
        filas_modelo.append((nombre, float(UMBRAL_MODELO[nombre]), int(len(d["y_tr"])), int(len(y_te)),
                             float(d["y_tr"].mean()) if len(d["y_tr"]) else None,
                             float(y_te.mean()) if len(y_te) else None,
                             a, ic_auc[0], ic_auc[1], br, br_ref, hab,
                             ic_bss[0], ic_bss[1],
                             dauc,
                             ic_dauc[0] if nombre in MODELOS_DAUC else None,
                             ic_dauc[1] if nombre in MODELOS_DAUC else None,
                             int(boot[nombre]["descartadas"])))

    prin = ajustados["principal"]
    y_te = prin["y_te"]
    p_te = prin["p"]
    br = brier(y_te, p_te)
    br_ref = brier(y_te, prin["ref"])
    hab = 1.0 - br / br_ref if br_ref > 0 else None
    a_prin = auc(y_te, p_te)
    ic_auc = boot["principal"]["auc_ic"]
    ic_bss = boot["principal"]["bss_ic"]
    ver = veredicto(len(y_te), y_te, a_prin, ic_auc[0], hab, ic_bss[0])
    filas_prueba = [(ver, int(len(prin["y_tr"])), int(len(y_te)), int(C["n"]), int(len(idx_fuera)),
                     int(len(np.unique(pads_todos))), int(reps))]
    filas_cal = calibracion(y_te, p_te)
    coef = [("intercepto", float(prin["w"][0]))]
    coef += [(prin["nombres"][i], float(prin["w"][i + 1])) for i in range(len(prin["nombres"]))]

    ventana_por_fila = np.array([_ventana(ym) for ym in C["ym"]], dtype=object)
    filas_anio = []
    for anio in sorted(set(int(a) for a in C["anio"])):
        mask = C["anio"] == anio
        filas_anio.append((anio, str(ventana_por_fila[mask][0]), int(mask.sum()),
                           int((C["falta_rama"][mask] == 0).sum()), int(C["golpe"][mask].sum())))

    filas_rama = []
    for grupo, mask in (("con_rama", C["falta_rama"][idx_test] == 0), ("sin_rama", C["falta_rama"][idx_test] == 1)):
        y_g = y_te[mask]
        filas_rama.append((grupo, int(mask.sum()), int(y_g.sum()), auc(y_g, p_te[mask])))

    return {"mart_riesgo_modelo": filas_modelo, "mart_riesgo_prueba": filas_prueba,
            "mart_riesgo_calibracion": filas_cal, "mart_riesgo_coef": coef,
            "mart_riesgo_anio": filas_anio, "mart_riesgo_rama": filas_rama}


def _ventana(ym: int) -> str:
    if _ym(INICIO_ENTRENAMIENTO) <= ym <= _ym(FIN_ENTRENAMIENTO):
        return "entrenamiento"
    if _ym(INICIO_PRUEBA) <= ym <= _ym(FIN_PRUEBA):
        return "prueba"
    return "fuera"


# ------------------------------------------------------------------ escritura

def escribir(con, t: dict[str, list[tuple]]) -> None:
    """Una llamada por mart, con el nombre escrito (lo que lee pipeline.linaje)."""
    _escribir(con, "mart_riesgo_modelo", COLS_MODELO, t["mart_riesgo_modelo"])
    _escribir(con, "mart_riesgo_prueba", COLS_PRUEBA, t["mart_riesgo_prueba"])
    _escribir(con, "mart_riesgo_calibracion", COLS_CALIBRACION, t["mart_riesgo_calibracion"])
    _escribir(con, "mart_riesgo_coef", COLS_COEF, t["mart_riesgo_coef"])
    _escribir(con, "mart_riesgo_anio", COLS_ANIO, t["mart_riesgo_anio"])
    _escribir(con, "mart_riesgo_rama", COLS_RAMA, t["mart_riesgo_rama"])


def marts(con) -> dict | None:
    """Las seis tablas de la pagina (None si no se corrio todavia)."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?",
                       ["mart_riesgo_prueba"]).fetchone()[0]:
        return None
    return {"modelo": con.execute("select * from mart_riesgo_modelo order by modelo").fetchall(),
            "prueba": con.execute("select * from mart_riesgo_prueba").fetchall(),
            "calibracion": con.execute("select * from mart_riesgo_calibracion order by decil").fetchall(),
            "coef": con.execute("select * from mart_riesgo_coef").fetchall(),
            "anio": con.execute("select * from mart_riesgo_anio order by anio").fetchall(),
            "rama": con.execute("select * from mart_riesgo_rama").fetchall()}


def _num(x, dec: int = 3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/d"
    return f"{x:.{dec}f}"


def main(path=DATA / "warehouse.duckdb", reps: int = REPS_BOOT) -> None:
    """Corre la pagina entera sobre el warehouse y escribe los marts."""
    con = duckdb.connect(str(path))
    try:
        C = cargar(con)
        t = calcular(C, reps=reps)
        escribir(con, t)
    finally:
        con.close()
    fila = next(r for r in t["mart_riesgo_modelo"] if r[0] == "principal")
    ver = t["mart_riesgo_prueba"][0][0]
    print(f"[riesgo] veredicto: {ver}, AUC {_num(fila[6])} (IC {_num(fila[7])} a {_num(fila[8])}), "
          f"BSS {_num(fila[11])} (IC {_num(fila[12])} a {_num(fila[13])}), "
          f"eventos de prueba {fila[3]}, de entrenamiento {fila[2]}")
    print(f"[riesgo] eventos: {t['mart_riesgo_prueba'][0][3]} en total, {fila[2]} de entrenamiento, "
          f"{fila[3]} de prueba, {t['mart_riesgo_prueba'][0][4]} fuera de ventana, "
          f"{t['mart_riesgo_prueba'][0][5]} pads de hijo en la prueba")


# ------------------------------------------------------------------ la pagina de la wiki

SHA_REGLA = "4b19b90"                   # el commit que fijo la regla antes de calcular ninguna cifra
TITULO = "Riesgo de golpe fuerte"
ETIQUETAS_MODELO = {
    "principal": "Principal (todas las variables)",
    "m2_sin_rama": "M2: sin la geometría de las ramas",
    "m3_solo_km": "M3: solo la distancia de superficie",
    "m4_con_rama": "M4: solo eventos con la rama del par medida",
    "s1_umbral_m20": "S1: golpe fuerte desde -20 puntos",
    "s2_umbral_m40": "S2: golpe fuerte desde -40 puntos",
}


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and np.isnan(x))


def _d2(x) -> str:
    return _g(x, 2)


def _ic2(v, lo, hi) -> str:
    return f"{_d2(v)} ({_d2(lo)} a {_d2(hi)})" if _ok(v) and _ok(lo) and _ok(hi) else "n/d"


def _pct(x) -> str:
    return _g(100 * x, 1) if _ok(x) else "n/d"


def _entero(x) -> str:
    return "n/d" if x is None else _g(x, 0)


def pagina_riesgo(con) -> str:
    """Página de la wiki a partir de los marts (solo lee). Cada frase que depende de un veredicto sale de la palabra guardada."""
    M = marts(con)
    if M is None:
        raise SystemExit("falta correr `uv run python -m pipeline.riesgo` antes de escribir la página")
    mod = {r[0]: r[1:] for r in M["modelo"]}   # umbral, n_tr, n_te, prev_tr, prev_te, auc, lo, hi, brier, ref, bss, lo, hi, dauc, lo, hi, descartadas
    ver, n_tr, n_te, n_todos, n_fuera, n_pads, reps = M["prueba"][0]
    prin = mod["principal"]
    umbral, _a, _b, prev_tr, prev_te, a, a_lo, a_hi, _br, _rf, b, b_lo, b_hi = prin[:13]
    cal = M["calibracion"]
    rama = {r[0]: r[1:] for r in M["rama"]}
    anios = {r[0]: r[1:] for r in M["anio"]}
    cob = _cobertura(con)
    te_rama = rama.get("con_rama", (0, 0, None))[0]
    te_2024 = anios.get(2024, ("prueba", 0, 0, 0))

    muestra = (f"- Muestra: Son {_entero(n_todos)} eventos cercanos del estudio (el padre a menos de 1 km en superficie del hijo más cercano, "
               f"con el índice del mes 1 medido): {_entero(n_tr)} de entrenamiento (hijos fracturados de 2016-01 a 2022-12) y "
               f"{_entero(n_te)} de prueba (de 2023-01 a 2024-12); {_entero(n_fuera)} quedan fuera de las dos ventanas y no se usan. "
               f"De los de prueba, {_entero(te_rama)} tienen la rama del par medida y el resto entra con la distancia entre ramas faltante y su indicador.")
    if cob:
        muestra += (f" Las trayectorias laterales cubren el {cob[0]}% de los hijos horizontales fracturados de 2016 a 2023 pero solo el "
                    f"{cob[1]}% de los de 2024 y el {cob[2]}% de los de 2025, así que la muestra es sobre todo de 2016 a 2023 y la prueba "
                    f"de 2023 a 2024 es fina en 2024: {_entero(te_2024[2])} de sus {_entero(te_2024[1])} eventos tienen la rama del par medida.")
    prevalencia = (f"- Golpe fuerte: el índice del mes 1 del padre menos la mediana del mismo grupo de edad de los controles queda por debajo de "
                   f"{_pts_u(umbral)} puntos. Ocurre en el {_pct(prev_tr)}% de los eventos de entrenamiento y en el {_pct(prev_te)}% de los de prueba.")

    if ver == "sin muestra":
        lectura = (f"- Riesgo: **{ver}**. Los datos no deciden: la prueba tiene {_entero(n_te)} eventos (la regla pide por lo menos "
                   f"{N_MIN_PRUEBA}) o le falta una de las dos clases.")
    else:
        lectura = (f"- Riesgo: **{ver}**. En la prueba el AUC es {_d2(a)} (IC 95%: {_d2(a_lo)} a {_d2(a_hi)}) y la habilidad de Brier contra la "
                   f"tasa de entrenamiento por área es {_d2(b)} (IC 95%: {_d2(b_lo)} a {_d2(b_hi)}).")
        auc_ok = _ok(a) and a >= AUC_MIN and _ok(a_lo) and a_lo > AUC_IC_BAJO
        bss_ok = _ok(b) and b > BSS_MIN and _ok(b_lo) and b_lo > BSS_MIN
        if ver == "predice el riesgo":
            lectura += (f" El AUC pasa el umbral de la regla ({_d2(AUC_MIN)} con límite bajo sobre {_d2(AUC_IC_BAJO)}) y la habilidad de Brier "
                        "excluye cero: el modelo separa los golpes fuertes y sus probabilidades mejoran la tasa por área.")
        elif auc_ok and not bss_ok:
            lectura += (f" El AUC pasa el umbral de la regla ({_d2(AUC_MIN)} con límite bajo sobre {_d2(AUC_IC_BAJO)}) pero la habilidad de Brier "
                        "no excluye cero: el modelo ordena los eventos de la prueba y no se puede afirmar que sus probabilidades mejoren "
                        "la tasa de entrenamiento por área. La regla pide las dos cosas.")
        elif bss_ok and not auc_ok:
            lectura += " La habilidad de Brier excluye cero pero el AUC no pasa el umbral de la regla."
        else:
            lectura += " Ni el AUC ni la habilidad de Brier pasan el umbral de la regla."
    if len(cal) == N_DECILES and _ok(cal[0][2]) and _ok(cal[-1][2]):
        calib = (f"- Calibración (descriptivo, tabla de abajo): el décimo de mayor riesgo predice {_pct(cal[-1][2])}% y observa {_pct(cal[-1][3])}%; "
                 f"el de menor riesgo predice {_pct(cal[0][2])}% y observa {_pct(cal[0][3])}%.")
    else:
        calib = "- Calibración: no hay decil que publicar."
    m2, m3 = mod.get("m2_sin_rama"), mod.get("m3_solo_km")
    geo = []
    if m2 and m3:
        geo = [f"- Geometría (descriptivo, sin veredicto): sin las variables de las ramas el AUC es {_ic2(m2[5], m2[6], m2[7])} y con la distancia de "
               f"superficie sola {_ic2(m3[5], m3[6], m3[7])}. La diferencia de AUC contra el principal es {_ic2(m2[13], m2[14], m2[15])} sin las "
               f"ramas y {_ic2(m3[13], m3[14], m3[15])} con la distancia de superficie sola. Es una lectura de esta muestra y no cambia el veredicto."]

    L = [f"# {TITULO}", "",
         "El modelo puntual de costo (`anisotropia.md`) predice barriles y falla fuera de muestra. Esta página hace la pregunta que un operador "
         "puede usar: dado un padre y un hijo que se va a fracturar a menos de 1 km, cuán probable es un golpe fuerte. Es un modelo de "
         "clasificación probado hacia adelante en el tiempo: entrena con los hijos fracturados de 2016 a 2022 y se prueba con los de 2023 y 2024. "
         f"La regla se fijó antes de calcular ninguna cifra, en el commit {SHA_REGLA}. Se publican todos los modelos, favorables o no.", "",
         "Esta página la escribe `python -m pipeline.wiki` con `pipeline.riesgo.pagina_riesgo`. No se edita a mano.", "",
         "## Lectura", "", muestra, prevalencia, lectura, calib, *geo, ""]

    L += ["## Modelos", "",
          "| Modelo | Umbral (puntos) | Entrenamiento | Prueba | Golpes en la prueba (%) | AUC (IC 95%) | Habilidad de Brier (IC 95%) | AUC menos el del principal (IC 95%) |",
          "|---|---|---|---|---|---|---|---|"]
    for nombre in ETIQUETAS_MODELO:
        if nombre not in mod:
            continue
        u, ntr, nte, _pt, pte, aa, lo, hi, _br, _rf, bb, blo, bhi, da, dlo, dhi, _desc = mod[nombre]
        dif = _ic2(da, dlo, dhi) if nombre in MODELOS_DAUC else "n/d"
        L.append(f"| {ETIQUETAS_MODELO[nombre]} | {_g(100 * u, 0)} | {_entero(ntr)} | {_entero(nte)} | {_pct(pte)} | "
                 f"{_ic2(aa, lo, hi)} | {_ic2(bb, blo, bhi)} | {dif} |")
    L += ["", "La habilidad de Brier es 1 menos el Brier del modelo sobre el de la referencia (la prevalencia de entrenamiento por área; en M4 la de ese "
              "subconjunto). Solo el modelo principal decide el veredicto; los demás son descriptivos.", ""]

    L += ["## Calibración por decil (modelo principal, eventos de prueba)", "",
          "| Decil de riesgo | Eventos | Riesgo medio predicho (%) | Frecuencia observada (%) |", "|---|---|---|---|"]
    for dec, n, pm, om in cal:
        L.append(f"| {dec} | {_entero(n)} | {_pct(pm)} | {_pct(om)} |")
    L += ["", "Los eventos de la prueba van ordenados por el riesgo predicho en 10 grupos de tamaño casi igual (el décimo es el de mayor riesgo).", ""]

    L += ["## Coeficientes del modelo principal (unidades estandarizadas)", "",
          "| Variable | Coeficiente |", "|---|---|"]
    for var, c in M["coef"]:
        L.append(f"| {var} | {_d2(c)} |")
    L += ["", "Son descriptivos: no tienen intervalo ni prueba de significancia, y con variables correlacionadas no se leen una por una.", ""]

    L += ["## Con y sin la rama del par medida (modelo principal, eventos de prueba)", "",
          "| Grupo | Eventos | Golpes fuertes | AUC |", "|---|---|---|---|"]
    for g, etiqueta in (("con_rama", "Con la rama del par medida"), ("sin_rama", "Sin la rama del par medida")):
        if g in rama:
            n, gl, au = rama[g]
            L.append(f"| {etiqueta} | {_entero(n)} | {_entero(gl)} | {_d2(au)} |")
    L += [""]

    L += ["## Eventos por año del hijo", "", "| Año | Ventana | Eventos | Con la rama del par medida | Golpes fuertes |", "|---|---|---|---|---|"]
    for anio in sorted(anios):
        vent, ev, cr, gl = anios[anio]
        L.append(f"| {anio} | {vent} | {_entero(ev)} | {_entero(cr)} | {_entero(gl)} |")
    L += [""]

    L += ["## Cómo se mide", "",
          "- Los eventos son los cercanos del estudio: un padre a menos de 1 km en superficie de su hijo más cercano, en el mes de fractura de ese hijo.",
          "- El resultado es golpe fuerte si el índice del mes 1 del padre menos la mediana de los controles de 2 a 5 km de su grupo de edad queda por debajo de -30 puntos.",
          "- Las variables son la distancia de superficie, la menor distancia entre ramas con su indicador de falta, la posición y la diferencia de azimut, la edad y el "
          "caudal base del padre, su petróleo acumulado por metro de rama, la arena por metro y las etapas del hijo, si comparten pad, los hijos a menos de 1 km ese mes, "
          "el operador y el área.",
          "- El modelo principal es una regresión logística con penalización L2 (C = 1,0), variables estandarizadas con el entrenamiento y sin ningún ajuste.",
          f"- Los intervalos son bootstrap de percentiles 95% que remuestrea pads de hijo completos de los eventos de prueba ({_entero(reps)} remuestras, "
          f"{_entero(n_pads)} pads, las mismas para todos los modelos). El modelo se ajusta una vez: el intervalo cubre el muestreo de la prueba y no el del entrenamiento.",
          f"- El veredicto sale solo del modelo principal: \"predice el riesgo\" pide un AUC de {_d2(AUC_MIN)} o más con límite bajo sobre {_d2(AUC_IC_BAJO)} y una habilidad de Brier "
          f"mayor que cero con intervalo que excluye cero; \"sin muestra\" es menos de {_entero(N_MIN_PRUEBA)} eventos de prueba.", ""]

    L += ["## Qué no es", "",
          "- Es una asociación probada hacia adelante, sin afirmación causal: un riesgo alto no dice que la fractura del hijo cause el golpe.",
          "- La mediana de control del resultado sale de todo el periodo, como en el estudio principal; no es una variable del modelo, pero el resultado de los eventos "
          "de entrenamiento y el de los de prueba comparten esa mediana.",
          "- El entrenamiento tiene cientos de eventos y muchas variables: un \"no predice el riesgo\" es contra estas variables y este modelo (logístico L2 sin ajuste) "
          "y no prueba que nada prediga el riesgo. Los intervalos cubren el muestreo de la prueba, no el del entrenamiento.",
          "- La rama medida cubre sobre todo hijos de 2016 a 2023: las variables de rama de la prueba están medidas en una parte de los eventos y la muestra no dice nada de "
          "los hijos de 2025 en adelante.",
          "- Solo están los eventos con el hijo cercano a menos de 1 km en superficie: un padre con la rama cerca pero la boca lejos no está.",
          "- La referencia por área usa la prevalencia de entrenamiento: una mejora sobre ella no es una mejora sobre un operador que ya conoce su campo.", ""]

    L += ["## Reproducir", "",
          "1. `uv run python -m pipeline.riesgo` (necesita `pipeline.trayectorias` antes).",
          "2. `uv run python -m pipeline.wiki`", "3. `uv run python -m pipeline.claims`", ""]
    return "\n".join(L) + "\n"


def _pts_u(x: float) -> str:
    return _g(100 * x, 0)


if __name__ == "__main__":
    main()

