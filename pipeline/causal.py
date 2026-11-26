"""Diseno causal: diferencias en diferencias escalonadas con controles aun no tratados, y el corte de agua como canal fisico.

Se corre despues de pipeline.build (y de pipeline.trayectorias para la lectura por posicion):  uv run python -m pipeline.causal

REGLA FIJADA ANTES DE CORRER (2026-11-21). Este archivo es el primer commit de la unidad: la regla, las constantes y los umbrales
del veredicto. Antes de fijarla no se calculo ninguna cifra con estos disenos (ni ATT, ni placebos, ni conteos de tratados o de
controles). Si algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: al fijarla se conocian las cifras publicadas del estudio (brecha del mes 1 de -19 a -23 puntos,
pretendencia de -2,5, -3,6 y -6,3 en los meses -3 a -1, salto de corte de agua de 0,187 mas de proporcion en los cercanos, dias
perdidos, alcance y contraste costado menos punta). El plan completo: docs/plan-causal.md, y la pagina
wiki/hallazgos/causal.md.

Por que: todo lo publicado compara padres cercanos con controles a 2 a 5 km de la misma edad, y los cercanos ya rendian menos antes
de la fractura (seleccion de zona de relleno). Aca el control es un padre que TAMBIEN recibira un hijo a menos de 1 km, pero mas
tarde (aun no tratado), y la tendencia previa se acota con una cota de sensibilidad. El corte de agua separa una comunicacion
fisica de un cierre preventivo: cerrar baja los dias, no mete agua.

Definiciones comunes:
  * Universo: pozos de `int_pozo_ubicacion`. Hijos y mes de fractura: `int_frac_hijo`. Distancia de superficie en km con la
    formula de `int_par_padre_hijo` (KM_POR_GRADO por grado, longitud por el coseno de la latitud del hijo).
  * Golpe a d km de un pozo i en el mes m: un hijo (distinto de i) fracturado en m a menos de d km de i, con m posterior al
    primer mes de petroleo de i. Sin la restriccion de 6 meses de edad, para ver tambien golpes a pozos jovenes.
  * Cohorte g_i: el primer mes con golpe a KM_TRATADO km. Tratado: edad (meses desde el primer mes de petroleo) en g de
    EDAD_MIN o mas, ningun golpe a KM_LIMPIO km en los VENTANA_PREVIA meses anteriores a g, y base valida.
  * Base: los meses BASE (de g - 6 a g - 4), los tres con fila en `fct_produccion`, con media de petroleo por dia calendario
    (petroleo_m3 / dias_mes) mayor que BASE_MIN m3/d.
  * Indice I_i(e) = petroleo_m3 / dias_mes del mes g + e sobre la base, recortado arriba en INDICE_TOPE. Mes sin fila: falta.
  * Control de la celda (g, grupo de edad, horizonte H): un pozo j con edad en g de EDAD_MIN o mas en el mismo grupo de edad
    (CORTES_EDAD: 6 a 11, 12 a 23, 24 a 47, 48 o mas meses), con base valida en g, sin golpe a KM_LIMPIO km en
    [g - VENTANA_PREVIA, g + H], y con su propio primer golpe a KM_TRATADO km despues de g + H y dentro de los datos (aun no
    tratado y alguna vez tratado). Un pozo puede ser control de muchas cohortes. S1 suma los nunca tratados (sin golpe a
    KM_TRATADO km en todo el dato) con las mismas condiciones.
  * ATT(g, a, e) = media de I de los tratados de la celda menos media de I de sus controles; la celda entra en e si tiene al menos
    1 tratado y MIN_CONTROLES_CELDA controles con dato en e. ATT(e) es el promedio de las celdas pesado por tratados con dato. En
    puntos de indice (x 100).
  * IC 95%: bootstrap de percentiles que remuestrea bloques de TAM_BLOQUE_KM km de la ubicacion de superficie de cada pozo
    (`pipeline.bloques.clave_bloque`), REPS repeticiones, semilla SEMILLA_CAUSAL. Los mismos sorteos para todas las cantidades
    de una misma muestra; un bloque sorteado entra con todos sus pozos, como tratados y como controles.

D1. Primera fractura a menos de 1 km y caudal del padre (principal).
  * Estimando ATT(1) con H = H_CORTO. Serie de e = -3 a 6 (E_SERIE). Pretendencia: beta(-3), beta(-2), beta(-1) contra la base.
  * Cota de sensibilidad (inspirada en Rambachan y Roth 2023, magnitudes relativas; version simplificada y conservadora, no su
    implementacion exacta): m = max(|b(-3)|, |b(-2) - b(-3)|, |b(-1) - b(-2)|); B(M) = |b(-1)| + 2 M m; intervalo robusto
    [IC bajo - B(M), IC alto + B(M)]; M* = (-IC alto - |b(-1)|) / (2 m), y 0 si eso es negativo (infinito si m es 0).
  * Potencia de la pretendencia (Roth 2022, informada, no decide): la pendiente lineal previa minima detectable con 80% de
    potencia, 2,8 veces el desvio bootstrap de la pendiente de b(-3), b(-2), b(-1).
  * Placebos. Rompe el diseno si su IC excluye cero y su valor absoluto es UMBRAL_ROTURA_PUNTOS o mas:
      - fecha falsa: g' = g - DESFASE_FECHA_FALSA para cada tratado, con las mismas condiciones de tratado y de control en g'.
      - distancia falsa: pseudo tratados con el primer golpe en [KM_FALSO_MIN, KM_FALSO_MAX) km y ninguno a KM_LIMPIO km en
        [g - VENTANA_PREVIA, g + H]; mismos controles.
      - nunca tratados: pozos sin golpe a KM_TRATADO km en todo el dato, con una fecha sorteada (semilla fija) de la
        distribucion de cohortes de los tratados entre las fechas en que cumplen las condiciones de tratado; mismos controles.
  * Dejar un operador afuera: ATT(1) sin los tratados y controles de cada operador del padre con MIN_TRATADOS_OPERADOR o mas
    tratados.
  * Veredicto, en este orden:
      - "sin muestra": menos de MIN_TRATADOS tratados con dato en e = 1 en celdas con control, o menos de MIN_BLOQUES bloques.
      - "no sobrevive a su placebo": rompe la fecha falsa, la distancia falsa o los nunca tratados.
      - "sostiene como causal bajo tendencias paralelas condicionales": IC alto de ATT(1) menor que UMBRAL_EFECTO_PUNTOS, M*
        de M_MIN o mas, y el IC alto de cada ATT(1) sin un operador menor que cero.
      - "no firme": cualquier otro caso.

D1b. Persistencia, meses 7 a 24 (extension de D1).
  * Por pozo, la media de I en e = 7 a 24 con al menos MIN_MESES_PERSISTENCIA de 18 meses con dato. H = H_LARGO. Tratados y
    controles sin otro golpe a KM_LIMPIO km en los meses 1 a 24 (simetrico). Misma agregacion por celdas.
  * Veredicto: "sin muestra" con menos de MIN_TRATADOS_LARGO tratados; "perdida persistente" si el IC alto es menor que
    -|b(-1)| de D1; "solo diferido (cota)" si el IC incluye cero y el IC bajo es mayor que -MARGEN_DIFERIDO_PUNTOS (el IC bajo
    es la mayor perdida compatible); "no firme" en cualquier otro caso. Se publica tambien el acumulado de e = 0 a 23.

D2. Comunicacion fisica: corte de agua.
  * W = agua_m3 / (agua_m3 + petroleo_m3) de un mes con liquido. Base de W: media en g - 6 a g - 4 con al menos MIN_MESES_W_BASE
    meses. dW = max(W(g), W(g + 1)) - base, con al menos un mes presente. En puntos porcentuales. Mismas celdas que D1 (H_CORTO).
  * Placebos, con UMBRAL_ROTURA_AGUA: previo (dW con max(W(g - 2), W(g - 1))), fecha falsa y distancia falsa como en D1.
  * Placebo de cierre (prueba de la exclusion): meses m de pozos que nunca son tratados o aun no lo son, con dias_efectivos /
    dias_mes menor que TEF_CIERRE en m, media de esa fraccion de TEF_BASE_MIN o mas en m - 6 a m - 4, base de W valida y sin
    golpe a KM_LIMPIO km en [m - VENTANA_PREVIA, m + 1]; contra meses sin cierre (fraccion de TEF_BASE_MIN o mas en m) de pozos
    con las mismas condiciones, por celda de mes calendario y grupo de edad. Mismo dW.
  * Veredicto, en este orden:
      - "sin muestra": menos de MIN_TRATADOS tratados con dW.
      - "no sobrevive a su placebo": rompe el previo, la fecha falsa o la distancia falsa.
      - "no separa el cierre de la comunicacion": el placebo de cierre tiene IC que excluye cero y vale FRACCION_CIERRE del
        ATT_W o mas.
      - "sostiene: comunicacion fisica causal bajo tendencias paralelas": IC bajo de ATT_W mayor que UMBRAL_AGUA_PP.
      - "no firme": cualquier otro caso.

Sin veredicto, publicado: S1 con nunca tratados; medianas en lugar de medias; e = 0; heterogeneidad por posicion (costado, punta,
de `mart_par_rama` con el hijo de la cohorte) en la muestra con ramas, que es sobre todo de 2016 a 2023 (las ramas cubren de 76
a 97% de los hijos de 2016 a 2023, 39% de 2024 y 25% de 2025); cotas de Lee (2009) del caudal por dia producido en e = 1
(petroleo_m3 / dias_efectivos sobre la misma razon de la base; observado si dias_efectivos / dias_mes es TEF_OBSERVADO o mas),
recortando el grupo con mas meses observados.

Lo que no dice: aun con "sostiene" es causa bajo supuestos nombrados (tendencias paralelas condicionales, sin anticipacion mas alla
de 3 meses, sin derrame sobre controles limpios a 2 km, exclusion del placebo de cierre), no un hecho fisico medido. Sin presion
ni produccion diaria no se mide la comunicacion directamente.
"""
from __future__ import annotations

from pipeline.costo import SEMILLA
from pipeline.placebo import REPS_BOOT

# ---- regla fijada (no cambiar despues de ver cifras) ----
SEMILLA_CAUSAL = SEMILLA + 50
REPS = REPS_BOOT                      # repeticiones del bootstrap, las de pipeline.placebo
KM_POR_GRADO = 111.32
KM_TRATADO = 1.0                      # golpe que define la cohorte
KM_LIMPIO = 2.0                       # ningun golpe a esta distancia en la ventana de limpieza
VENTANA_PREVIA = 12                   # meses previos a g sin golpe a KM_LIMPIO
EDAD_MIN = 6                          # meses de petroleo en g
BASE = (-6, -4)                       # meses de la base, relativos a g
BASE_MIN = 1.0                        # m3/d de petroleo de la base
INDICE_TOPE = 3.0                     # recorte superior del indice
CORTES_EDAD = (12, 24, 48)            # grupos de edad: 6 a 11, 12 a 23, 24 a 47, 48 o mas
MIN_CONTROLES_CELDA = 5
H_CORTO = 6                           # horizonte de D1 y D2
H_LARGO = 24                          # horizonte de D1b
E_PRINCIPAL = 1
E_SERIE = tuple(range(-3, 7))
E_PERSISTENCIA = (7, 24)              # inclusive
MIN_MESES_PERSISTENCIA = 15
TAM_BLOQUE_KM = 5.0
PERCENTILES_IC = (2.5, 97.5)
POTENCIA_Z = 2.8                      # 1,96 + 0,84: 80% de potencia a dos colas al 5%

DESFASE_FECHA_FALSA = 12
KM_FALSO_MIN, KM_FALSO_MAX = 3.0, 5.0
UMBRAL_ROTURA_PUNTOS = 5.0            # un placebo rompe si su IC excluye cero y |valor| >= esto
MIN_TRATADOS_OPERADOR = 50

MIN_TRATADOS = 300
MIN_BLOQUES = 30
UMBRAL_EFECTO_PUNTOS = -10.0          # IC alto de ATT(1) por debajo de esto
M_MIN = 1.0

MIN_TRATADOS_LARGO = 200
MARGEN_DIFERIDO_PUNTOS = 5.0

MIN_MESES_W_BASE = 2
UMBRAL_ROTURA_AGUA = 2.0              # puntos porcentuales
UMBRAL_AGUA_PP = 2.0                  # IC bajo de ATT_W por encima de esto
TEF_CIERRE = 0.5
TEF_BASE_MIN = 0.8
FRACCION_CIERRE = 0.5
TEF_OBSERVADO = 0.9                   # cotas de Lee

V_SIN_MUESTRA = "sin muestra"
V_PLACEBO = "no sobrevive a su placebo"
V_NO_FIRME = "no firme"
V_D1_SOSTIENE = "sostiene como causal bajo tendencias paralelas condicionales"
V_D1B_PERSISTENTE = "pérdida persistente"
V_D1B_DIFERIDO = "solo diferido (cota)"
V_D2_CIERRE = "no separa el cierre de la comunicación"
V_D2_SOSTIENE = "sostiene: comunicación física causal bajo tendencias paralelas"


def rompe(est: float, bajo: float, alto: float, umbral: float) -> bool:
    """Un placebo rompe el diseno si su IC excluye cero y su valor absoluto es el umbral o mas."""
    return (bajo > 0 or alto < 0) and abs(est) >= umbral


def m_estrella(alto: float, b3: float, b2: float, b1: float) -> float:
    """M* de la cota de magnitudes relativas: el mayor M con IC alto + B(M) < 0."""
    m = max(abs(b3), abs(b2 - b3), abs(b1 - b2))
    resto = -alto - abs(b1)
    if m == 0:
        return float("inf") if resto > 0 else 0.0
    return max(0.0, resto / (2 * m))


def veredicto_d1(n_tratados: int, n_bloques: int, placebos_rotos: bool, alto: float, m_est: float,
                 altos_sin_operador: list[float]) -> str:
    if n_tratados < MIN_TRATADOS or n_bloques < MIN_BLOQUES:
        return V_SIN_MUESTRA
    if placebos_rotos:
        return V_PLACEBO
    if alto < UMBRAL_EFECTO_PUNTOS and m_est >= M_MIN and all(a < 0 for a in altos_sin_operador):
        return V_D1_SOSTIENE
    return V_NO_FIRME


def veredicto_d1b(n_tratados: int, bajo: float, alto: float, b1: float) -> str:
    if n_tratados < MIN_TRATADOS_LARGO:
        return V_SIN_MUESTRA
    if alto < -abs(b1):
        return V_D1B_PERSISTENTE
    if bajo <= 0 <= alto and bajo > -MARGEN_DIFERIDO_PUNTOS:
        return V_D1B_DIFERIDO
    return V_NO_FIRME


def veredicto_d2(n_tratados: int, placebos_rotos: bool, cierre_est: float, cierre_bajo: float, cierre_alto: float,
                 att: float, bajo: float) -> str:
    if n_tratados < MIN_TRATADOS:
        return V_SIN_MUESTRA
    if placebos_rotos:
        return V_PLACEBO
    if (cierre_bajo > 0 or cierre_alto < 0) and att > 0 and cierre_est >= FRACCION_CIERRE * att:
        return V_D2_CIERRE
    if bajo > UMBRAL_AGUA_PP:
        return V_D2_SOSTIENE
    return V_NO_FIRME


# ================================================================== calculo
# Todo lo que sigue aplica el docstring de este archivo. No cambia ninguna constante, ningun umbral
# ni ninguna funcion de veredicto: solo los usa.

import duckdb
import numpy as np

from pipeline.bloques import clave_bloque
from pipeline.costo import _clusters, _escribir
from pipeline.ingest import DATA
from pipeline.mecanismo import _texto_cobertura
from pipeline.placebo import _g

MESES_BASE = (BASE[0], BASE[1])          # (-6, -4) inclusive: los tres meses de la base
N_GRUPOS_EDAD = 4
MARGEN_PENDIENTE = 1e-9

COLS_SERIE = [("diseno", "varchar"), ("modelo", "varchar"), ("e", "integer"), ("n_tratados", "integer"),
              ("n_controles", "integer"), ("att", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_PLACEBO = [("diseno", "varchar"), ("placebo", "varchar"), ("n_tratados", "integer"), ("att", "double"),
                ("ic_bajo", "double"), ("ic_alto", "double"), ("rompe", "boolean")]
COLS_OPERADOR = [("operador", "varchar"), ("n_tratados", "integer"), ("att", "double"),
                  ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_EXTRA = [("diseno", "varchar"), ("cantidad", "varchar"), ("valor", "double"),
              ("ic_bajo", "double"), ("ic_alto", "double"), ("n", "integer")]
COLS_VEREDICTO = [("diseno", "varchar"), ("veredicto", "varchar"), ("estimando", "varchar"), ("valor", "double"),
                  ("ic_bajo", "double"), ("ic_alto", "double"), ("n_tratados", "integer"), ("n_bloques", "integer"),
                  ("motivo", "varchar")]

SQL_GOLPES = """
select c.pozo_id as hijo, w.pozo_id as pozo,
       (year(h.mes_frac) * 12 + month(h.mes_frac) - 1) as mes,
       111.32 * sqrt(power((w.lon - c.lon) * cos(radians(c.lat)), 2) + power(w.lat - c.lat, 2)) as km
from int_frac_hijo h
join int_pozo_ubicacion c on c.pozo_id = h.hijo
join int_pozo_ubicacion w
  on abs(c.lat - w.lat) < 0.05 and abs(c.lon - w.lon) < 0.07
where c.pozo_id <> w.pozo_id
  and h.mes_frac > w.primer_mes_petroleo
  and 111.32 * sqrt(power((w.lon - c.lon) * cos(radians(c.lat)), 2) + power(w.lat - c.lat, 2)) < 5.0
"""


# ------------------------------------------------------------------ carga

def _mes(fecha) -> int:
    """Indice de mes: year * 12 + month - 1."""
    return fecha.year * 12 + fecha.month - 1


def cargar(con) -> dict:
    """Universo del diseno: ubicacion y primer mes de petroleo de cada pozo, el panel mensual de produccion
    y los golpes (hijo, pozo, mes, km) a menos de 5 km.

    Devuelve, entre otras cosas, las matrices por pozo y mes: `tasa` (petroleo_m3 / dias_mes), `w` (corte de agua),
    `tef` (dias_efectivos / dias_mes), `tasa_pd` (petroleo_m3 / dias_efectivos), `hay` (fila de produccion),
    `km_min` (distancia del golpe mas cercano del mes) y `hijo_min` (ese hijo)."""
    wells = con.execute(
        "select pozo_id, coalesce(operador, 'Sin dato'), lat, lon, "
        "(year(primer_mes_petroleo) * 12 + month(primer_mes_petroleo) - 1) as pm "
        "from int_pozo_ubicacion order by pozo_id").fetchall()
    n = len(wells)
    pozo_id = np.array([int(r[0]) for r in wells], dtype=np.int64)
    operador = np.array([str(r[1]) for r in wells], dtype=object)
    lat = np.array([float(r[2]) for r in wells], dtype=float)
    lon = np.array([float(r[3]) for r in wells], dtype=float)
    primer = np.array([int(r[4]) if r[4] is not None else -1 for r in wells], dtype=np.int64)
    bloque = clave_bloque(lat, lon, TAM_BLOQUE_KM)

    mm = con.execute("select min(mes), max(mes) from fct_produccion").fetchone()
    t1 = _mes(mm[1])
    con_pm = primer[primer >= 0]
    t0 = min(_mes(mm[0]), int(con_pm.min()) if con_pm.size else _mes(mm[0]))
    T = t1 - t0 + 1

    tasa = np.full((n, T), np.nan)
    agua = np.full((n, T), np.nan)
    tef = np.full((n, T), np.nan)
    tasa_pd = np.full((n, T), np.nan)
    hay = np.zeros((n, T), dtype=bool)
    pos = {int(p): i for i, p in enumerate(pozo_id)}
    for pid, mes, pet, ag, de, dm in con.execute(
            "select pozo_id, mes, petroleo_m3, agua_m3, dias_efectivos, dias_mes from fct_produccion").fetchall():
        i = pos.get(int(pid))
        j = _mes(mes) - t0
        if i is None or j < 0 or j >= T:
            continue
        hay[i, j] = True
        pet = float(pet) if pet is not None else float("nan")
        ag = float(ag) if ag is not None else float("nan")
        de = float(de) if de is not None else 0.0
        dm = float(dm) if dm is not None else 0.0
        if dm > 0 and not np.isnan(pet):
            tasa[i, j] = pet / dm
        if dm > 0:
            tef[i, j] = de / dm
        if de > 0 and not np.isnan(pet):
            tasa_pd[i, j] = pet / de
        if not np.isnan(pet) and not np.isnan(ag) and (ag + pet) > 0:
            agua[i, j] = ag / (ag + pet)

    km_min = np.full((n, T), np.nan)
    km_falso = np.full((n, T), np.nan)
    hijo_min = np.full((n, T), -1, dtype=np.int64)
    for hijo, pozo, mes, km in con.execute(SQL_GOLPES).fetchall():
        i = pos.get(int(pozo))
        j = int(mes) - t0
        if i is None or j < 0 or j >= T:
            continue
        if np.isnan(km_min[i, j]) or km < km_min[i, j]:
            km_min[i, j] = km
            hijo_min[i, j] = int(hijo)
        if KM_FALSO_MIN <= km < KM_FALSO_MAX:
            if np.isnan(km_falso[i, j]) or km < km_falso[i, j]:
                km_falso[i, j] = km

    posicion = {(int(h), int(p)): str(pos) for h, p, pos in
                con.execute("select hijo, padre, posicion from mart_par_rama").fetchall()}
    return _armar(pozo_id, operador, lat, lon, primer, bloque, t0, t1, tasa, agua, tef, tasa_pd, hay,
                  km_min, km_falso, hijo_min, posicion)


def _armar(pozo_id, operador, lat, lon, primer, bloque, t0, t1, tasa, w, tef, tasa_pd, hay, km_min, km_falso,
           hijo_min, posicion) -> dict:
    """Arma el diccionario de datos con los paneles ya calculados (lo usa `cargar` y las pruebas)."""
    pozo_id = np.asarray(pozo_id, dtype=np.int64)
    n = len(pozo_id)
    T = tasa.shape[1]
    hit2 = km_min < KM_LIMPIO
    cs2 = np.concatenate([np.zeros((n, 1), dtype=np.int64), np.cumsum(hit2, axis=1, dtype=np.int64)], axis=1)
    return {"n": n, "pozo_id": pozo_id, "operador": np.asarray(operador, dtype=object),
            "lat": np.asarray(lat, dtype=float), "lon": np.asarray(lon, dtype=float),
            "primer": np.asarray(primer, dtype=np.int64), "bloque": np.asarray(bloque, dtype=np.int64),
            "t0": int(t0), "t1": int(t1), "T": T, "tasa": tasa, "w": w, "tef": tef, "tasa_pd": tasa_pd,
            "hay": hay, "km_min": km_min, "km_falso": km_falso, "hijo_min": hijo_min, "cs2": cs2,
            "posicion": posicion or {},
            "g1": _primera(km_min < KM_TRATADO, t0), "g_falso": _primera(km_falso < KM_FALSO_MAX, t0)}


def _primera(mat: np.ndarray, t0: int = 0) -> np.ndarray:
    """Primer mes con algo en cada fila de una matriz booleana (indice de mes absoluto), o -1."""
    any_ = mat.any(axis=1)
    idx = np.argmax(mat, axis=1)
    return np.where(any_, idx + t0, -1).astype(np.int64)


def _bases(D: dict) -> tuple[np.ndarray, np.ndarray]:
    """Media y validez de la base por pozo y mes (cacheadas en D)."""
    if "_bases" not in D:
        D["_bases"] = _panel_base(D)
    return D["_bases"]


def _cols_base(D: dict, g: int) -> np.ndarray:
    """Columnas del panel de los tres meses de la base del mes g."""
    return np.array([g - 6 - D["t0"], g - 5 - D["t0"], g - 4 - D["t0"]], dtype=np.int64)


def _panel_base(D: dict) -> tuple[np.ndarray, np.ndarray]:
    """Media de la base y base valida de cada pozo para cada mes del panel (la base de un mes m son los meses m - 6 a m - 4)."""
    n, T = D["n"], D["T"]
    t0 = D["t0"]
    v = np.nan_to_num(D["tasa"])
    nn = (~np.isnan(D["tasa"])).astype(np.int64)
    cs_v = np.concatenate([np.zeros((n, 1)), np.cumsum(v, axis=1)], axis=1)
    cs_n = np.concatenate([np.zeros((n, 1)), np.cumsum(nn, axis=1)], axis=1)
    meses = np.arange(t0, D["t1"] + 1)
    c1 = meses - 6 - t0
    c3 = meses - 4 - t0
    ok = (c1 >= 0) & (c3 < T)
    c1c = np.clip(c1, 0, T - 1)
    c3c = np.clip(c3, 0, T - 1)
    suma = cs_v[:, c3c + 1] - cs_v[:, c1c]
    cuenta = cs_n[:, c3c + 1] - cs_n[:, c1c]
    media = np.where(cuenta > 0, suma / np.maximum(cuenta, 1), np.nan)
    valida = ok[None, :] & (cuenta == 3) & (media > BASE_MIN)
    return media, valida


def _panel_promedio(D: dict, mat: np.ndarray, min_meses: int) -> tuple[np.ndarray, np.ndarray]:
    """Media en la base y bandera de al menos `min_meses` meses con dato, para cada pozo y cada mes del panel."""
    n, T = D["n"], D["T"]
    t0 = D["t0"]
    v = np.nan_to_num(mat)
    nn = (~np.isnan(mat)).astype(np.int64)
    cs_v = np.concatenate([np.zeros((n, 1)), np.cumsum(v, axis=1)], axis=1)
    cs_n = np.concatenate([np.zeros((n, 1)), np.cumsum(nn, axis=1)], axis=1)
    meses = np.arange(t0, D["t1"] + 1)
    c1 = meses - 6 - t0
    c3 = meses - 4 - t0
    ok = (c1 >= 0) & (c3 < T)
    c1c = np.clip(c1, 0, T - 1)
    c3c = np.clip(c3, 0, T - 1)
    cuenta = cs_n[:, c3c + 1] - cs_n[:, c1c]
    suma = cs_v[:, c3c + 1] - cs_v[:, c1c]
    media = np.where(cuenta > 0, suma / np.maximum(cuenta, 1), np.nan)
    bueno = ok[None, :] & (cuenta >= min_meses)
    return np.where(bueno, media, np.nan), bueno


def _ventana(D: dict, a: np.ndarray | int, b: np.ndarray | int, wells: np.ndarray | None = None) -> np.ndarray:
    """Cantidad de golpes a menos de KM_LIMPIO km por pozo en los meses [a, b] (de los pozos dados o de todos)."""
    cs = D["cs2"]
    T = D["T"]
    wells = np.arange(D["n"]) if wells is None else np.asarray(wells, dtype=np.int64)
    a = np.full(len(wells), a, dtype=np.int64) if np.isscalar(a) else np.asarray(a, dtype=np.int64)
    b = np.full(len(wells), b, dtype=np.int64) if np.isscalar(b) else np.asarray(b, dtype=np.int64)
    lo = np.clip(a - D["t0"], 0, T)
    hi = np.clip(b - D["t0"] + 1, 0, T)
    return cs[wells, hi] - cs[wells, lo]


def _grupo_edad(edad: np.ndarray) -> np.ndarray:
    """Grupo de edad: 0 de 6 a 11 meses, 1 de 12 a 23, 2 de 24 a 47, 3 de 48 o mas."""
    edad = np.asarray(edad, dtype=np.int64)
    return ((edad >= CORTES_EDAD[0]).astype(np.int64) + (edad >= CORTES_EDAD[1]).astype(np.int64)
            + (edad >= CORTES_EDAD[2]).astype(np.int64))


# ------------------------------------------------------------------ cohorte y controles

def _condiciones(D: dict, g: np.ndarray, base_valida: np.ndarray, base_media: np.ndarray,
                 wells: np.ndarray | None = None) -> np.ndarray:
    """Condiciones de tratado de cada pozo en el mes g: edad, ventana limpia previa y base valida."""
    wells = np.arange(D["n"]) if wells is None else np.asarray(wells, dtype=np.int64)
    edad = g - D["primer"][wells]
    ok = (D["primer"][wells] >= 0) & (edad >= EDAD_MIN) & base_valida
    limpio = _ventana(D, g - VENTANA_PREVIA, g - 1, wells=wells) == 0
    return ok & limpio


def cohortes(D: dict) -> dict:
    """Cohorte g de cada pozo: el primer mes con golpe a menos de KM_TRATADO km, con edad, ventana limpia y base valida.

    Devuelve `tratado` (booleano), `g` (indice de mes de cohorte, -1 si no hay), `base` (m3/d de la base),
    `edad` (meses de petroleo en g) y `grupo` (grupo de edad)."""
    media, valida = _bases(D)
    g = D["g1"].copy()
    tiene = g >= 0
    base = np.full(D["n"], np.nan)
    edad = np.full(D["n"], -1, dtype=np.int64)
    grupo = np.full(D["n"], -1, dtype=np.int64)
    cols = np.clip(g - D["t0"], 0, D["T"] - 1)
    base = media[np.arange(D["n"]), cols]
    val = valida[np.arange(D["n"]), cols]
    edad = np.where(tiene, g - D["primer"], -1)
    grupo = np.where(tiene, _grupo_edad(edad), -1)
    tratado = tiene & _condiciones(D, g, val, base)
    return {"tratado": tratado, "g": np.where(tratado, g, -1), "base": np.where(tratado, base, np.nan),
            "edad": edad, "grupo": grupo}


def controles(D: dict, g: int, H: int, incluir_nunca: bool = False) -> np.ndarray:
    """Pozos que pueden ser control de la celda del mes g: edad, grupo, base valida, sin golpe a KM_LIMPIO km en
    [g - VENTANA_PREVIA, g + H] y con su propio primer golpe a KM_TRATADO km despues de g + H.

    Con `incluir_nunca` se suman los nunca tratados (sin golpe a KM_TRATADO km en todo el dato)."""
    media, valida = _bases(D)
    col = g - D["t0"]
    if col < 0 or col >= D["T"]:
        return np.zeros(0, dtype=np.int64)
    edad = g - D["primer"]
    limpio = _ventana(D, g - VENTANA_PREVIA, g + H) == 0
    comun = valida[:, col] & (D["primer"] >= 0) & (edad >= EDAD_MIN) & limpio
    g1 = D["g1"]
    ok = comun & (g1 > g + H)
    if incluir_nunca:
        ok = ok | (comun & (g1 < 0))
    return np.flatnonzero(ok)


def celdas(D: dict, coh: dict, H: int, incluir_nunca: bool = False,
           tratados: np.ndarray | None = None, g_por_tratado: np.ndarray | None = None) -> list[dict]:
    """Celdas (g, grupo de edad) con sus tratados y sus controles.

    Cada celda lleva `g`, `grupo`, `tratados`, `controles`, `base_t` y `base_c`."""
    trat = np.flatnonzero(coh["tratado"]) if tratados is None else np.asarray(tratados, dtype=np.int64)
    if len(trat) == 0:
        return []
    gs = coh["g"][trat] if g_por_tratado is None else np.asarray(g_por_tratado, dtype=np.int64)
    gr = _grupo_edad(gs - D["primer"][trat])
    media, _ = _bases(D)
    out = []
    for g, grupo in dict.fromkeys(zip(gs.tolist(), gr.tolist())):
        sel = trat[(gs == g) & (gr == grupo)]
        con = controles(D, int(g), H, incluir_nunca)
        # el control es del mismo grupo de edad del padre en g (regla fijada); antes se tomaban todos los grupos
        con = con[_grupo_edad(int(g) - D["primer"][con]) == grupo]
        col = int(g) - D["t0"]
        out.append({"g": int(g), "grupo": int(grupo), "tratados": sel, "controles": con,
                    "base_t": media[sel, col], "base_c": media[con, col] if len(con) else np.zeros(0)})
    return out


# ------------------------------------------------------------------ indice y estimadores

def indice(D: dict, pozos: np.ndarray, base: np.ndarray, g: int, e: int) -> np.ndarray:
    """Indice I(e) de cada pozo: el caudal por dia calendario del mes g + e sobre su base, recortado arriba en INDICE_TOPE.

    Da nan cuando el mes no tiene fila de produccion."""
    pozos = np.asarray(pozos, dtype=np.int64)
    out = np.full(len(pozos), np.nan)
    col = g + e - D["t0"]
    if col < 0 or col >= D["T"]:
        return out
    vals = D["tasa"][pozos, col]
    ok = ~np.isnan(vals) & ~np.isnan(base) & (base > 0)
    out[ok] = np.minimum(vals[ok] / base[ok], INDICE_TOPE)
    return out


def _preparar(celdas_: list[dict], valores_t: list[np.ndarray], valores_c: list[np.ndarray],
              unidad_t: list[np.ndarray] | None = None, unidad_c: list[np.ndarray] | None = None) -> dict:
    """Arma los arrays planos de tratados y controles por celda para el estimador ponderado."""
    t_idx, t_val, t_cel, t_uni, c_idx, c_val, c_cel, c_uni = [], [], [], [], [], [], [], []
    for k, (vt, vc) in enumerate(zip(valores_t, valores_c)):
        okt = ~np.isnan(vt)
        okc = ~np.isnan(vc)
        if int(okt.sum()) < 1 or int(okc.sum()) < MIN_CONTROLES_CELDA:
            continue
        cel = len(t_cel)
        t_idx.append(np.flatnonzero(okt))
        t_val.append(vt[okt])
        t_cel.append(np.full(int(okt.sum()), cel, dtype=np.int64))
        t_uni.append(np.asarray(unidad_t[k], dtype=np.int64)[okt] if unidad_t is not None
                     else celdas_[k]["tratados"][okt])
        c_idx.append(np.flatnonzero(okc))
        c_val.append(vc[okc])
        c_cel.append(np.full(int(okc.sum()), cel, dtype=np.int64))
        c_uni.append(np.asarray(unidad_c[k], dtype=np.int64)[okc] if unidad_c is not None
                     else celdas_[k]["controles"][okc])
    return {"t_idx": np.concatenate(t_idx) if t_idx else np.zeros(0, dtype=np.int64),
            "t_val": np.concatenate(t_val) if t_val else np.zeros(0),
            "t_cel": np.concatenate(t_cel) if t_cel else np.zeros(0, dtype=np.int64),
            "t_uni": np.concatenate(t_uni) if t_uni else np.zeros(0, dtype=np.int64),
            "c_idx": np.concatenate(c_idx) if c_idx else np.zeros(0, dtype=np.int64),
            "c_val": np.concatenate(c_val) if c_val else np.zeros(0),
            "c_cel": np.concatenate(c_cel) if c_cel else np.zeros(0, dtype=np.int64),
            "c_uni": np.concatenate(c_uni) if c_uni else np.zeros(0, dtype=np.int64),
            "n_celdas": len(t_cel)}


def _att(prep: dict, pesos: np.ndarray | None, n_pozos: int) -> float:
    """ATT con medias por celda ponderadas por el numero de tratados (con `pesos`, medias ponderadas por pozo)."""
    if prep["n_celdas"] == 0:
        return float("nan")
    w = np.ones(n_pozos) if pesos is None else pesos
    wt = w[prep["t_uni"]]
    wc = w[prep["c_uni"]]
    nc = prep["n_celdas"]
    num_t = np.bincount(prep["t_cel"], weights=wt * prep["t_val"], minlength=nc)
    den_t = np.bincount(prep["t_cel"], weights=wt, minlength=nc)
    num_c = np.bincount(prep["c_cel"], weights=wc * prep["c_val"], minlength=nc)
    den_c = np.bincount(prep["c_cel"], weights=wc, minlength=nc)
    ok = (den_t > 0) & (den_c > 0)
    dif = np.where(ok, num_t / np.maximum(den_t, MARGEN_PENDIENTE) - num_c / np.maximum(den_c, MARGEN_PENDIENTE), 0.0)
    peso = np.where(ok, den_t, 0.0)
    total = peso.sum()
    return float((peso * dif).sum() / total) if total > 0 else float("nan")


def att_celdas(D: dict, celdas_: list[dict], e: int, pesos: np.ndarray | None = None) -> dict:
    """ATT(e) de las celdas: media de los indices tratados menos media de los controles, promedio de celdas pesado
    por tratados con dato. En puntos de indice (x 100)."""
    vt, vc = [], []
    for ce in celdas_:
        vt.append(indice(D, ce["tratados"], ce["base_t"], ce["g"], e))
        vc.append(indice(D, ce["controles"], ce["base_c"], ce["g"], e))
    prep = _preparar(celdas_, vt, vc)
    est = _att(prep, pesos, D["n"])
    n_t = int(len(prep["t_idx"]))
    n_c = int(len(prep["c_idx"]))
    return {"att": 100.0 * est, "n_tratados": n_t, "n_controles": n_c, "n_celdas": prep["n_celdas"], "prep": prep}


def _mediana_ponderada(vals: np.ndarray, pesos: np.ndarray) -> float:
    """Mediana ponderada de un grupo de valores."""
    if len(vals) == 0:
        return float("nan")
    o = np.argsort(vals, kind="stable")
    v, w = vals[o], pesos[o]
    cw = np.cumsum(w)
    tot = cw[-1]
    if tot <= 0:
        return float("nan")
    k = int(np.searchsorted(cw, tot / 2.0))
    return float(v[min(k, len(v) - 1)])


def att_celdas_medianas(D: dict, celdas_: list[dict], e: int, pesos: np.ndarray | None = None) -> dict:
    """ATT(e) con medianas en lugar de medias (sensitividad sin veredicto)."""
    w = np.ones(D["n"]) if pesos is None else pesos
    num, den = 0.0, 0.0
    n_t = n_c = 0
    for ce in celdas_:
        It = indice(D, ce["tratados"], ce["base_t"], ce["g"], e)
        Ic = indice(D, ce["controles"], ce["base_c"], ce["g"], e)
        okt = ~np.isnan(It)
        okc = ~np.isnan(Ic)
        if int(okt.sum()) < 1 or int(okc.sum()) < MIN_CONTROLES_CELDA:
            continue
        mt = _mediana_ponderada(It[okt], w[ce["tratados"][okt]])
        mc = _mediana_ponderada(Ic[okc], w[ce["controles"][okc]])
        if np.isnan(mt) or np.isnan(mc):
            continue
        peso = float(w[ce["tratados"][okt]].sum())
        num += peso * (mt - mc)
        den += peso
        n_t += int(okt.sum())
        n_c += int(okc.sum())
    est = num / den if den > 0 else float("nan")
    return {"att": 100.0 * est, "n_tratados": n_t, "n_controles": n_c}


# ------------------------------------------------------------------ bootstrap

def _pesos_bloques(D: dict, pozos: np.ndarray, reps: int, rng: np.random.Generator) -> np.ndarray:
    """Pesos por pozo de cada repeticion: un bloque de TAM_BLOQUE_KM km sorteado entra con todos sus pozos."""
    wells = np.unique(np.asarray(pozos, dtype=np.int64))
    w = np.zeros((reps, D["n"]), dtype=float)
    if len(wells) == 0:
        return w
    grupos = _clusters(D["bloque"][wells])
    nb = len(grupos)
    for r in range(reps):
        for i in rng.integers(0, nb, nb):
            w[r, wells[grupos[i]]] += 1.0
    return w


def bootstrap(D: dict, celdas_: list[dict], es: tuple[int, ...], W: np.ndarray) -> dict:
    """ATT(e) de cada evento con su IC 95% por bootstrap de bloques de 5 km (percentiles).

    Devuelve la estimacion, los percentiles, los valores de cada repeticion (para la potencia de la pretendencia)
    y los conteos."""
    vals = np.full((len(W), len(es)), np.nan)
    est = np.full(len(es), np.nan)
    n_t = np.zeros(len(es), dtype=np.int64)
    n_c = np.zeros(len(es), dtype=np.int64)
    preps = []
    for j, e in enumerate(es):
        r = att_celdas(D, celdas_, e)
        preps.append(r["prep"])
        est[j] = r["att"]
        n_t[j] = r["n_tratados"]
        n_c[j] = r["n_controles"]
    for i in range(len(W)):
        for j in range(len(es)):
            vals[i, j] = 100.0 * _att(preps[j], W[i], D["n"])
    bajo = np.full(len(es), np.nan)
    alto = np.full(len(es), np.nan)
    for j in range(len(es)):
        col = vals[:, j]
        col = col[~np.isnan(col)]
        if len(col):
            bajo[j], alto[j] = (float(x) for x in np.percentile(col, PERCENTILES_IC))
    return {"est": est, "ic_bajo": bajo, "ic_alto": alto, "vals": vals, "n_tratados": n_t, "n_controles": n_c}


def _pendiente(vals: np.ndarray) -> np.ndarray:
    """Pendiente de la regresion de cada fila de `vals` (b(-3), b(-2), b(-1)) contra (-3, -2, -1)."""
    x = np.array([-3.0, -2.0, -1.0])
    xc = x - x.mean()
    y = vals - vals.mean(axis=1, keepdims=True)
    return y @ xc / float((xc ** 2).sum())


def _n_bloques(D: dict, wells: np.ndarray) -> int:
    """Cantidad de bloques de TAM_BLOQUE_KM km con pozos del diseno."""
    wells = np.asarray(wells, dtype=np.int64)
    return int(len(_clusters(D["bloque"][wells]))) if len(wells) else 0


def _ic(vals: np.ndarray) -> tuple[float, float]:
    """Percentiles del intervalo de confianza de una lista de valores de bootstrap."""
    col = np.asarray(vals, dtype=float)
    col = col[~np.isnan(col)]
    if not len(col):
        return float("nan"), float("nan")
    return (float(x) for x in np.percentile(col, PERCENTILES_IC))


def _bootstrap_prep(D: dict, prep: dict, W: np.ndarray) -> dict:
    """Estimacion puntual e IC 95% de un estimador ya preparado (celdas y valores fijos), con los mismos sorteos."""
    est = 100.0 * _att(prep, None, D["n"])
    vals = np.array([100.0 * _att(prep, W[i], D["n"]) for i in range(len(W))])
    bajo, alto = _ic(vals)
    return {"est": est, "ic_bajo": bajo, "ic_alto": alto, "vals": vals,
            "n_tratados": int(len(prep["t_idx"])), "n_controles": int(len(prep["c_idx"]))}


# ------------------------------------------------------------------ cohortes de los placebos

def _cohorte_falsa_fecha(D: dict, coh: dict) -> tuple[np.ndarray, np.ndarray]:
    """Fecha falsa: g' = g - DESFASE_FECHA_FALSA para cada tratado, con las mismas condiciones de tratado en g'."""
    media, valida = _bases(D)
    trat = np.flatnonzero(coh["tratado"])
    g = coh["g"][trat] - DESFASE_FECHA_FALSA
    cols = np.clip(g - D["t0"], 0, D["T"] - 1)
    ok = _condiciones(D, g, valida[trat, cols], media[trat, cols], wells=trat)
    return trat[ok], g[ok]


def _cohorte_falsa_distancia(D: dict, coh: dict, H: int) -> tuple[np.ndarray, np.ndarray]:
    """Distancia falsa: el primer golpe en [KM_FALSO_MIN, KM_FALSO_MAX) km y ninguno a KM_LIMPIO km en
    [g - VENTANA_PREVIA, g + H]."""
    media, valida = _bases(D)
    g = D["g_falso"]
    sel = np.flatnonzero(g >= 0)
    gs = g[sel]
    cols = np.clip(gs - D["t0"], 0, D["T"] - 1)
    ok = (D["primer"][sel] >= 0) & (gs - D["primer"][sel] >= EDAD_MIN) & valida[sel, cols]
    ok &= _ventana(D, gs - VENTANA_PREVIA, gs + H, wells=sel) == 0
    return sel[ok], gs[ok]


def _cohorte_nunca_tratados(D: dict, coh: dict) -> tuple[np.ndarray, np.ndarray]:
    """Nunca tratados: una fecha sorteada de la distribucion de cohortes de los tratados, entre las fechas en que el
    pozo cumple las condiciones de tratado."""
    n, T = D["n"], D["T"]
    media, valida = _bases(D)
    meses = np.arange(D["t0"], D["t1"] + 1)
    filas = np.arange(n)
    hi = np.clip(meses - D["t0"], 0, T)
    lo = np.clip(meses - VENTANA_PREVIA - D["t0"], 0, T)
    limpio = (D["cs2"][filas[:, None], hi[None, :]] - D["cs2"][filas[:, None], lo[None, :]]) == 0
    cumple = ((meses[None, :] - D["primer"][:, None]) >= EDAD_MIN) & limpio & valida & (D["primer"][:, None] >= 0)
    dist = np.bincount((coh["g"][coh["tratado"]] - D["t0"]).clip(0, T - 1), minlength=T).astype(float)
    rng = np.random.default_rng(SEMILLA_CAUSAL + 1)
    trat, gs = [], []
    for i in np.flatnonzero(D["g1"] < 0):
        val = np.flatnonzero(cumple[i])
        if not len(val):
            continue
        p = dist[val]
        if p.sum() <= 0:
            continue
        j = int(rng.choice(val, p=p / p.sum()))
        trat.append(int(i))
        gs.append(int(D["t0"] + j))
    return np.array(trat, dtype=np.int64), np.array(gs, dtype=np.int64)


# ------------------------------------------------------------------ medidas por celda

def _dw(D: dict, pozos: np.ndarray, g: int, k: int, base: np.ndarray) -> np.ndarray:
    """dW = max(W(g + k), W(g + k + 1)) menos la base de W, como fraccion. Da nan si falta la base o los dos meses.

    Los puntos porcentuales salen al multiplicar por 100 el estimador, como el resto de las magnitudes."""
    col = g + k - D["t0"]
    w1 = D["w"][pozos, col] if 0 <= col < D["T"] else np.full(len(pozos), np.nan)
    w2 = D["w"][pozos, col + 1] if 0 <= col + 1 < D["T"] else np.full(len(pozos), np.nan)
    mx = np.fmax(w1, w2)
    ok = (~np.isnan(w1) | ~np.isnan(w2)) & ~np.isnan(base)
    return np.where(ok, mx - base, np.nan)


def _valores_agua(D: dict, celdas_: list[dict], k: int) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """dW de tratados y controles de cada celda."""
    media, ok = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    vt, vc = [], []
    for ce in celdas_:
        col = ce["g"] - D["t0"]
        base_t = media[ce["tratados"], col] if len(ce["tratados"]) else np.zeros(0)
        base_c = media[ce["controles"], col] if len(ce["controles"]) else np.zeros(0)
        vt.append(_dw(D, ce["tratados"], ce["g"], k, base_t))
        vc.append(_dw(D, ce["controles"], ce["g"], k, base_c))
    return vt, vc


def _indice_persistencia(D: dict, pozos: np.ndarray, base: np.ndarray, g: int) -> np.ndarray:
    """Media del indice en los meses E_PERSISTENCIA, con al menos MIN_MESES_PERSISTENCIA meses con dato."""
    e0, e1 = E_PERSISTENCIA
    vals = np.stack([indice(D, pozos, base, g, e) for e in range(e0, e1 + 1)], axis=1)
    cuenta = np.sum(~np.isnan(vals), axis=1)
    suma = np.nansum(vals, axis=1)
    media = np.where(cuenta > 0, suma / np.maximum(cuenta, 1), np.nan)
    return np.where(cuenta >= MIN_MESES_PERSISTENCIA, media, np.nan)


def _valores_persistencia(D: dict, celdas_: list[dict]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Media persistente del indice de tratados y controles de cada celda."""
    vt, vc = [], []
    for ce in celdas_:
        vt.append(_indice_persistencia(D, ce["tratados"], ce["base_t"], ce["g"]))
        vc.append(_indice_persistencia(D, ce["controles"], ce["base_c"], ce["g"]))
    return vt, vc


def _celdas_sin_operador(D: dict, celdas_: list[dict], op: str) -> list[dict]:
    """Celdas sin los tratados ni los controles del operador dado."""
    out = []
    for ce in celdas_:
        mt = D["operador"][ce["tratados"]] != op
        mc = D["operador"][ce["controles"]] != op
        t, c = ce["tratados"][mt], ce["controles"][mc]
        if not len(t) or len(c) < MIN_CONTROLES_CELDA:
            continue
        out.append({**ce, "tratados": t, "controles": c, "base_t": ce["base_t"][mt], "base_c": ce["base_c"][mc]})
    return out


# ------------------------------------------------------------------ D1

def diseno_d1(D: dict, W: np.ndarray, coh: dict, cel_pri: list[dict], cel_s1: list[dict]) -> dict:
    """D1: ATT(e) de la serie con H = H_CORTO, la cota M*, la potencia de la pretendencia y los tres placebos."""
    r = bootstrap(D, cel_pri, E_SERIE, W)
    idx = {e: j for j, e in enumerate(E_SERIE)}
    b3 = float(r["est"][idx[-3]])
    b2 = float(r["est"][idx[-2]])
    b1 = float(r["est"][idx[-1]])
    alto = float(r["ic_alto"][idx[E_PRINCIPAL]])
    m_est = m_estrella(alto, b3, b2, b1)
    vals_pre = r["vals"][:, [idx[-3], idx[-2], idx[-1]]]
    pendiente = _pendiente(vals_pre)
    sd = float(np.std(pendiente, ddof=1)) if len(pendiente) > 1 else float("nan")
    potencia = POTENCIA_Z * sd
    trat = np.concatenate([ce["tratados"] for ce in cel_pri]) if cel_pri else np.zeros(0, dtype=np.int64)
    n_bloques = _n_bloques(D, trat)
    r_s1 = bootstrap(D, cel_s1, E_SERIE, W)
    return {"r": r, "r_s1": r_s1, "b3": b3, "b2": b2, "b1": b1, "m_est": m_est, "potencia": potencia,
            "n_tratados": int(r["n_tratados"][idx[E_PRINCIPAL]]), "n_bloques": n_bloques, "idx": idx}


# ------------------------------------------------------------------ D1b

def celdas_d1b(D: dict, coh: dict) -> list[dict]:
    """Celdas de D1b: tratados sin otro golpe a KM_LIMPIO km en los meses 1 a 24 y controles con H = H_LARGO."""
    trat = np.flatnonzero(coh["tratado"])
    g = coh["g"][trat]
    limpio = _ventana(D, g + 1, g + H_LARGO, wells=trat) == 0
    return celdas(D, coh, H_LARGO, False, tratados=trat[limpio])


def diseno_d1b(D: dict, W: np.ndarray, cel: list[dict]) -> dict:
    """D1b: persistencia (media del indice en los meses 7 a 24) con H = H_LARGO y ventana limpia simetrica."""
    vt, vc = _valores_persistencia(D, cel)
    prep = _preparar(cel, vt, vc)
    r = _bootstrap_prep(D, prep, W)
    return {"r": r, "celdas": cel, "n_tratados": r["n_tratados"], "n_controles": r["n_controles"]}


def acumulado_persistencia(D: dict, W: np.ndarray, coh: dict, cel: list[dict]) -> dict:
    """Acumulado de e = 0 a 23 del ATT (descriptivo)."""
    es = tuple(range(0, 24))
    r = bootstrap(D, cel, es, W)
    valores = r["vals"].sum(axis=1)
    bajo, alto = _ic(valores)
    return {"est": float(r["est"].sum()), "ic_bajo": bajo, "ic_alto": alto}


# ------------------------------------------------------------------ D2

def diseno_d2(D: dict, W: np.ndarray, cel_pri: list[dict], cel_ff: list[dict], cel_fd: list[dict]) -> dict:
    """D2: dW (corte de agua) en las mismas celdas de D1, con sus tres placebos."""
    vt, vc = _valores_agua(D, cel_pri, 0)
    prep = _preparar(cel_pri, vt, vc)
    r = _bootstrap_prep(D, prep, W)
    vt_p, vc_p = _valores_agua(D, cel_pri, -2)
    r_prev = _bootstrap_prep(D, _preparar(cel_pri, vt_p, vc_p), W)
    vt_f, vc_f = _valores_agua(D, cel_ff, 0)
    r_ff = _bootstrap_prep(D, _preparar(cel_ff, vt_f, vc_f), W)
    vt_d, vc_d = _valores_agua(D, cel_fd, 0)
    r_fd = _bootstrap_prep(D, _preparar(cel_fd, vt_d, vc_d), W)
    return {"r": r, "previo": r_prev, "fecha_falsa": r_ff, "distancia_falsa": r_fd}


def placebo_cierre(D: dict, W: np.ndarray) -> dict:
    """Placebo de cierre: meses cerrados contra meses sin cierre de pozos nunca tratados o aun no tratados,
    por celda de mes calendario y grupo de edad."""
    n, T = D["n"], D["T"]
    meses = np.arange(D["t0"], D["t1"] + 1)
    filas = np.arange(n)
    hi = np.clip(meses - D["t0"] + 2, 0, T)  # ventana limpia hasta m + 1 inclusive (regla fijada)
    lo = np.clip(meses - VENTANA_PREVIA - D["t0"], 0, T)
    limpio = (D["cs2"][filas[:, None], hi[None, :]] - D["cs2"][filas[:, None], lo[None, :]]) == 0
    sin_tratar = (D["g1"][:, None] < 0) | (D["g1"][:, None] > meses[None, :])
    tef_base, _ = _panel_promedio(D, D["tef"], 1)
    w_base, w_ok = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    cond = sin_tratar & limpio & (tef_base >= TEF_BASE_MIN) & w_ok
    tef = D["tef"]
    cerr = cond & (tef < TEF_CIERRE)
    libre = cond & (tef >= TEF_BASE_MIN)
    edad = meses[None, :] - D["primer"][:, None]
    grupo = _grupo_edad(np.where(edad < 0, -1, edad))
    dw = np.full((n, T), np.nan)
    for k in range(T):
        col = k
        w1 = D["w"][:, col]
        w2 = D["w"][:, col + 1] if col + 1 < T else np.full(n, np.nan)
        ok = (~np.isnan(w1) | ~np.isnan(w2)) & w_ok[:, col]
        dw[:, col] = np.where(ok, np.fmax(w1, w2) - w_base[:, col], np.nan)
    celdas_ = []
    for m in range(T):
        for gr in range(N_GRUPOS_EDAD):
            sel_c = np.flatnonzero(cerr[:, m] & (grupo[:, m] == gr))
            sel_l = np.flatnonzero(libre[:, m] & (grupo[:, m] == gr))
            if not len(sel_c) or len(sel_l) < MIN_CONTROLES_CELDA:
                continue
            vt = dw[sel_c, m]
            vc = dw[sel_l, m]
            celdas_.append({"g": int(D["t0"] + m), "grupo": gr, "tratados": sel_c, "controles": sel_l,
                            "vt": vt, "vc": vc})
    t_idx, t_val, t_cel, t_uni, c_idx, c_val, c_cel, c_uni = [], [], [], [], [], [], [], []
    for k, ce in enumerate(celdas_):
        vt, vc = ce["vt"], ce["vc"]
        okt = ~np.isnan(vt)
        okc = ~np.isnan(vc)
        if int(okt.sum()) < 1 or int(okc.sum()) < MIN_CONTROLES_CELDA:
            continue
        cel = len(t_cel)
        t_idx.append(np.flatnonzero(okt))
        t_val.append(vt[okt])
        t_cel.append(np.full(int(okt.sum()), cel, dtype=np.int64))
        t_uni.append(ce["tratados"][okt])
        c_idx.append(np.flatnonzero(okc))
        c_val.append(vc[okc])
        c_cel.append(np.full(int(okc.sum()), cel, dtype=np.int64))
        c_uni.append(ce["controles"][okc])
    prep = {"t_idx": np.concatenate(t_idx) if t_idx else np.zeros(0, dtype=np.int64),
            "t_val": np.concatenate(t_val) if t_val else np.zeros(0),
            "t_cel": np.concatenate(t_cel) if t_cel else np.zeros(0, dtype=np.int64),
            "t_uni": np.concatenate(t_uni) if t_uni else np.zeros(0, dtype=np.int64),
            "c_idx": np.concatenate(c_idx) if c_idx else np.zeros(0, dtype=np.int64),
            "c_val": np.concatenate(c_val) if c_val else np.zeros(0),
            "c_cel": np.concatenate(c_cel) if c_cel else np.zeros(0, dtype=np.int64),
            "c_uni": np.concatenate(c_uni) if c_uni else np.zeros(0, dtype=np.int64),
            "n_celdas": len(t_cel)}
    return _bootstrap_prep(D, prep, W)


# ------------------------------------------------------------------ cotas de Lee

def lee_limites(y_trat: np.ndarray, n_trat: int, y_ctrl: np.ndarray, n_ctrl: int) -> dict:
    """Cotas de Lee (2009) de la diferencia de medias con observacion selectiva.

    `y_trat` son los valores observados del grupo tratado y `n_trat` su tamano total (observados y no observados).
    Se recorta el grupo con mas meses observados por p = (q_hi - q_lo) / q_hi, desde arriba y desde abajo."""
    y_trat = np.asarray(y_trat, dtype=float)
    y_ctrl = np.asarray(y_ctrl, dtype=float)
    q_t = len(y_trat) / n_trat if n_trat else 0.0
    q_c = len(y_ctrl) / n_ctrl if n_ctrl else 0.0
    if not len(y_trat) or not len(y_ctrl):
        return {"ic_bajo": float("nan"), "ic_alto": float("nan"), "q_tratados": q_t, "q_controles": q_c}
    if abs(q_t - q_c) < 1e-12:
        est = float(np.mean(y_trat) - np.mean(y_ctrl))
        return {"ic_bajo": est, "ic_alto": est, "q_tratados": q_t, "q_controles": q_c}
    if q_t > q_c:
        hi, lo = np.sort(y_trat), np.sort(y_ctrl)
        q_hi, q_lo = q_t, q_c
        trat_mayor = True
    else:
        hi, lo = np.sort(y_ctrl), np.sort(y_trat)
        q_hi, q_lo = q_c, q_t
        trat_mayor = False
    p = (q_hi - q_lo) / q_hi
    k = min(int(round(p * len(hi))), max(len(hi) - 1, 0))
    if k > 0:
        arriba = float(np.mean(hi[:-k]))
        abajo = float(np.mean(hi[k:]))
    else:
        arriba = abajo = float(np.mean(hi))
    if trat_mayor:
        bajo, alto = arriba - float(np.mean(lo)), abajo - float(np.mean(lo))
    else:
        bajo, alto = float(np.mean(lo)) - abajo, float(np.mean(lo)) - arriba
    return {"ic_bajo": float(bajo), "ic_alto": float(alto), "q_tratados": q_t, "q_controles": q_c}


def _lee_grupos(D: dict, coh: dict, cel_pri: list[dict]) -> dict:
    """Valor observado (caudal por dia producido sobre su base) en e = 1 de tratados y controles, y sus meses observados."""
    base_pd, _ = _panel_promedio(D, D["tasa_pd"], 3)
    trat = np.flatnonzero(coh["tratado"])
    g_t = coh["g"][trat]
    col_t = np.clip(g_t + 1 - D["t0"], 0, D["T"] - 1)
    v_t = D["tasa_pd"][trat, col_t] / base_pd[trat, np.clip(g_t - D["t0"], 0, D["T"] - 1)]
    o_t = D["tef"][trat, col_t] >= TEF_OBSERVADO
    con = np.unique(np.concatenate([ce["controles"] for ce in cel_pri])) if cel_pri else np.zeros(0, dtype=np.int64)
    g_c = np.full(len(con), -1, dtype=np.int64)
    for ce in sorted(cel_pri, key=lambda x: (x["g"], x["grupo"])):
        for i in ce["controles"]:
            j = np.searchsorted(con, i)
            if j < len(con) and con[j] == i and g_c[j] < 0:
                g_c[j] = ce["g"]
    ok = g_c >= 0
    con, g_c = con[ok], g_c[ok]
    col_c = np.clip(g_c + 1 - D["t0"], 0, D["T"] - 1)
    v_c = D["tasa_pd"][con, col_c] / base_pd[con, np.clip(g_c - D["t0"], 0, D["T"] - 1)]
    o_c = D["tef"][con, col_c] >= TEF_OBSERVADO
    return {"y_trat": v_t[o_t & ~np.isnan(v_t)], "n_trat": len(trat),
            "y_ctrl": v_c[o_c & ~np.isnan(v_c)], "n_ctrl": len(con)}


# ------------------------------------------------------------------ pagina

COMMIT_REGLA = "8f52ff1"

NOMBRE_PLACEBO = {
    "fecha_falsa": "Fecha falsa (la fecha de cada tratado corrida 12 meses hacia atrás)",
    "distancia_falsa": "Distancia falsa (primer hijo a 3 a 5 km, ninguno a menos de 2 km)",
    "nunca_tratados": "Nunca tratados (padres sin hijo a menos de 1 km, fechas sorteadas)",
    "previo": "Previo (ΔW en los meses -2 y -1)",
}

# Marca del veredicto (sistema Estepa, docs direccion-ui seccion 4): lleno sostiene, medio sostiene con una condicion,
# vacio no sostiene. Va antes de las palabras, que no cambian.
MARCA_VEREDICTO = {
    V_D1_SOSTIENE: "●", V_D2_SOSTIENE: "●", V_D1B_PERSISTENTE: "●",
    V_D1B_DIFERIDO: "◐", V_NO_FIRME: "◐",
    V_PLACEBO: "○", V_SIN_MUESTRA: "○", V_D2_CIERRE: "○",
}

TEXTO_VEREDICTO = {
    V_SIN_MUESTRA: "La muestra no alcanza el mínimo que fijó la regla; el valor se publica pero no decide nada.",
    V_PLACEBO: "Un placebo da un efecto donde no debería haberlo: el diseño no separa la fractura de la selección.",
    V_NO_FIRME: "No rompe ningún placebo, pero no cumple todas las condiciones de la regla.",
    V_D1_SOSTIENE: "El efecto queda bajo -10 puntos, resiste la cota de tendencias no paralelas y sin cada operador grande.",
    V_D1B_PERSISTENTE: "La pérdida de los meses 7 a 24 queda más allá de la brecha previa.",
    V_D1B_DIFERIDO: "El IC incluye cero y su límite bajo es la mayor pérdida persistente compatible.",
    V_D2_CIERRE: "Un cierre solo ya sube el corte de agua a la mitad del efecto o más: el agua no separa los canales.",
    V_D2_SOSTIENE: ("Ningún placebo rompe, el cierre solo no explica el salto y el IC queda entero sobre 2 puntos."
                    " Mide la proporción de agua, no su volumen: el corte también sube si el petróleo cae con el agua constante, y D2 no separa las dos cosas; el nombre del veredicto es el de la regla fijada."),
}


def _num(x: float, dec: int = 1) -> str:
    """Numero con coma decimal y signo, para cifras ya en puntos o puntos porcentuales."""
    return _g(x, dec)


def _ic_txt(a: float, b: float, dec: int = 1) -> str:
    return f"{_num(a, dec)} a {_num(b, dec)}"


def _limite_nunca_agua(con) -> str:
    """Limite sobre el placebo de nunca tratados en el agua: si D3 ya lo corrio, dice su resultado tal cual."""
    from pipeline.causal_profundo import _fila_d3
    try:
        nt = _fila_d3(con, "placebo_nunca_tratados_dW")
    except duckdb.Error:
        nt = None
    if nt is None:
        return ("- La regla fijada no le asigna a D2 el placebo de nunca tratados, el que rompe D1: que los controles aún no "
                "tratados difieran de los demás pozos, como muestra el petróleo, no se probó sobre el corte de agua; lo acota "
                "solo el placebo previo de la tabla de D2.")
    return ("- La regla fijada no le asigna a D2 el placebo de nunca tratados, el que rompe D1. Se corrió después, fuera de la "
            f"regla, sobre el corte de agua, y {'rompe' if nt[5] else 'no rompe'} (renglón de D3 del resumen y "
            "`causal_profundo.md`): es una prueba aparte, no parte del veredicto de D2.")


def pagina_causal(con) -> str:
    """Pagina de wiki del diseno causal; lee los cinco marts `mart_causal_*`."""
    ver = {r[0]: r for r in con.execute("select * from mart_causal_veredicto").fetchall()}
    if not {"D1", "D1b", "D2"} <= set(ver):
        raise ValueError("faltan filas en mart_causal_veredicto")
    serie = con.execute("select * from mart_causal_serie order by diseno, modelo, e").fetchall()
    pri = {r[2]: r for r in serie if r[0] == "D1" and r[1] == "principal"}
    s1 = {r[2]: r for r in serie if r[0] == "D1" and r[1] == "S1"}
    plac = con.execute("select * from mart_causal_placebo").fetchall()
    pl = {(r[0], r[1]): r for r in plac}
    ops = con.execute("select * from mart_causal_operador order by operador").fetchall()
    ex = {(r[0], r[1]): r for r in con.execute("select * from mart_causal_extra").fetchall()}

    v1, v1b, v2 = ver["D1"], ver["D1b"], ver["D2"]
    m_est = ex[("D1", "M*")][2]
    pot = ex[("D1", "potencia_pretrendencia")][2]
    cierre = ex[("D2", "cierre_placebo")]
    rotos1 = [r[1] for r in plac if r[0] == "D1" and r[6]]
    b3, b2, b1 = pri[-3][5], pri[-2][5], pri[-1][5]
    m_paso = max(abs(b3), abs(b2 - b3), abs(b1 - b2))

    L = ["# Diseño causal: qué puede sostener como causa el dato público", "",
         "Página generada por `pipeline/causal.py`. Todo lo demás del estudio es descriptivo: compara padres cercanos con "
         "controles a 2 a 5 km de la misma edad, y los cercanos ya rendían menos antes de la fractura. Esta página cambia el "
         "control por un padre que también va a recibir un hijo a menos de 1 km, pero más tarde (aún no tratado), y fija antes "
         "de calcular qué resultado se lee como causa. El plan completo está en `docs/plan-causal.md`.", "",
         "## Resumen", "",
         f"- {MARCA_VEREDICTO[v1[1]]} **D1, caudal de petróleo al mes 1: {v1[1]}.** {TEXTO_VEREDICTO.get(v1[1], '')} ATT(1) = {_num(v1[3])} puntos "
         f"(IC 95% por bloques de 5 km: {_ic_txt(v1[4], v1[5])}), {_g(v1[6])} padres tratados en {_g(v1[7])} bloques.",
         f"- {MARCA_VEREDICTO[v1b[1]]} **D1b, persistencia en los meses 7 a 24: {v1b[1]}.** {TEXTO_VEREDICTO.get(v1b[1], '')} {_g(v1b[6])} tratados "
         f"(la regla pide {MIN_TRATADOS_LARGO}); diferencia {_num(v1b[3])} puntos (IC 95%: {_ic_txt(v1b[4], v1b[5])}).",
         f"- {MARCA_VEREDICTO[v2[1]]} **D2, corte de agua: {v2[1]}.** {TEXTO_VEREDICTO.get(v2[1], '')} ATT_W = {_num(v2[3])} puntos porcentuales "
         f"(IC 95%: {_ic_txt(v2[4], v2[5])}), {_g(v2[6])} tratados."]
    from pipeline.causal_profundo import frase_d2, frase_d4, frase_d13, frase_d56, frase_d7, frase_lectura_d56
    d3 = frase_d2(con)
    if d3:
        L.append(d3)
    d4 = frase_d4(con)
    if d4:
        L.append(d4)
    L += frase_d56(con)
    d7 = frase_d7(con)
    if d7:
        L.append(d7)
    d13 = frase_d13(con)
    if d13:
        L.append(d13)
    lectura_d56 = frase_lectura_d56(con)
    L.append("")
    mitad ="menos de la mitad" if cierre[2] < FRACCION_CIERRE * v2[3] else "la mitad o más"
    if v2[1] == V_D2_SOSTIENE and v1[1] == V_PLACEBO:
        L += ["Lectura: el dato público carga una sola afirmación causal, y bajo supuestos nombrados. La primera fractura de "
              "un hijo a menos de 1 km sube el corte de agua del padre (la proporción, no el volumen de agua) en el mes de la fractura o el siguiente, frente a un "
              f"padre de la misma zona de relleno que todavía no la recibió; un cierre de más de medio mes sin hijo cerca lo "
              f"sube {_num(cierre[2])} puntos porcentuales, {mitad}. " + (lectura_d56 + " " if lectura_d56 else "")
              + "La caída del caudal de petróleo, en cambio, no "
              "sobrevive como causa con estos controles"
              + (f": el placebo de nunca tratados da {_num(pl[('D1', 'nunca_tratados')][3])} puntos con un IC que excluye cero"
                 if "nunca_tratados" in rotos1 else "")
              + f", y M* = {_g(m_est, 2)} queda bajo 1. La brecha del mes 1 sigue medida y publicada como descripción; lo que "
              "no se sostiene es leerla como el efecto de la fractura.", ""]

    L += ["## Regla fijada antes de calcular", "",
          f"La regla se fijó en el commit {COMMIT_REGLA} de la rama `t3/causal-diseno`: la cabecera de `pipeline/causal.py`, sus "
          "constantes y las funciones de veredicto, sin ninguna cifra calculada con estos diseños. Al fijarla se conocían las "
          "cifras ya publicadas del estudio (brecha del mes 1, pretendencia, salto de corte de agua). El commit siguiente "
          "declara dos arreglos de implementación hechos sin cambiar ninguna constante ni ningún umbral.", "",
          "- Cohorte de un padre: primer mes con un hijo fracturado a menos de 1 km. Tratado: 6 meses de edad o más en ese mes, "
          "ningún hijo a menos de 2 km en los 12 meses previos, y base (meses -6 a -4) con más de 1 m3/d de petróleo.",
          "- Índice: petróleo por día calendario sobre la base, recortado en 3. Control: padre del mismo grupo de edad en el "
          "mismo mes, con base válida, sin hijo a menos de 2 km desde 12 meses antes hasta el horizonte, y con su propio primer "
          "hijo a menos de 1 km después del horizonte (aún no tratado). Celda con al menos 1 tratado y 5 controles.",
          "- ATT por celda de mes y grupo de edad, promediado por tratados (estilo Callaway y Sant'Anna). IC 95%: bootstrap de "
          f"percentiles por bloques de 5 km, {REPS} repeticiones, semilla fija. M* es una versión simplificada de la cota de "
          "magnitudes relativas de Rambachan y Roth.",
          f"- Un placebo rompe si su IC excluye cero y vale {_g(UMBRAL_ROTURA_PUNTOS)} puntos o más ({_g(UMBRAL_ROTURA_AGUA)} "
          "puntos porcentuales en D2).",
          f"- D1 sostiene si no rompe ningún placebo, el IC de ATT(1) queda entero bajo {_g(UMBRAL_EFECTO_PUNTOS)} puntos, M* "
          "es 1 o más y sin cada operador con 50 tratados o más el IC sigue bajo cero.",
          f"- D2 sostiene si no rompe ningún placebo, el placebo de cierre no llega a la mitad del ATT_W con un IC que excluye "
          f"cero, y el IC de ATT_W queda entero sobre {_g(UMBRAL_AGUA_PP)} puntos porcentuales.", "",
          "## D1: caudal de petróleo", "",
          "Diferencia entre tratados y controles aún no tratados del índice de cada mes relativo a la fractura, en puntos. S1 "
          "suma los padres nunca tratados al control y no decide nada.", "",
          "| Mes | Tratados | Controles | ATT (puntos) | IC 95% | S1: ATT | S1: IC 95% |",
          "| ---: | ---: | ---: | ---: | --- | ---: | --- |"]
    for e in sorted(pri):
        r, s = pri[e], s1.get(e)
        L.append(f"| {e} | {_g(r[3])} | {_g(r[4])} | {_num(r[5])} | {_ic_txt(r[6], r[7])} | "
                 f"{_num(s[5]) if s else 'n/d'} | {_ic_txt(s[6], s[7]) if s else 'n/d'} |")
    L += ["", "Placebos de D1, en el mes 1.", "",
          "| Placebo | Tratados | ATT (puntos) | IC 95% | Rompe |", "| --- | ---: | ---: | --- | --- |"]
    for r in plac:
        if r[0] == "D1":
            L.append(f"| {NOMBRE_PLACEBO.get(r[1], r[1])} | {_g(r[2])} | {_num(r[3])} | {_ic_txt(r[4], r[5])} | "
                     f"{'sí' if r[6] else 'no'} |")
    L += ["", f"Tendencias no paralelas: el mayor paso previo es {_num(m_paso)} puntos (con la serie de los meses -3 a -1: "
          f"{_num(b3)}, {_num(b2)} y {_num(b1)}). M* = {_g(m_est, 2)}: si cada paso posterior a la fractura pudiera desviarse "
          f"{_g(m_est, 2)} veces ese paso, el IC robusto ya tocaría cero. Es el M* simplificado, que queda como registro; la cota de Rambachan y Roth (`cota_rr.md`) lo reemplaza en el texto. La pendiente previa que se detectaría con 80% de "
          f"potencia es {_num(pot)} puntos por mes.", "",
          "Dejar un operador afuera (operadores con 50 tratados o más), ATT(1).", "",
          "| Sin el operador | Tratados restantes | ATT (puntos) | IC 95% |", "| --- | ---: | ---: | --- |"]
    for r in ops:
        L.append(f"| {r[0]} | {_g(r[1])} | {_num(r[2])} | {_ic_txt(r[3], r[4])} |")
    acum = ex.get(("D1b", "acumulado_e0_e23"))
    L += ["", "## D1b: persistencia en los meses 7 a 24", "",
          f"Media del índice de los meses 7 a 24 (al menos 15 meses con dato), tratados y controles sin otro hijo a menos de "
          f"2 km en los meses 1 a 24: {_g(v1b[6])} tratados en {_g(v1b[7])} bloques, diferencia {_num(v1b[3])} puntos (IC 95%: "
          f"{_ic_txt(v1b[4], v1b[5])}). La regla pide {MIN_TRATADOS_LARGO} tratados: la exigencia de 24 meses sin otro hijo cerca "
          "deja muy pocos padres en zona de relleno, así que la pregunta de pérdida o diferido queda abierta."
          + (f" Suma de los meses 0 a 23, sin veredicto: {_num(acum[2])} puntos-mes (IC 95%: {_ic_txt(acum[3], acum[4])})."
             if acum else ""), "",
          "## D2: corte de agua", "",
          "ΔW: el mayor corte de agua del mes de la fractura y el siguiente, menos la media de los meses -6 a -4, en puntos "
          "porcentuales (W = agua sobre agua más petróleo). Mismas celdas y controles que D1.", "",
          f"- ATT_W = {_num(v2[3])} puntos porcentuales (IC 95%: {_ic_txt(v2[4], v2[5])}), {_g(v2[6])} tratados, "
          f"{_g(v2[7])} bloques.",
          "- Es una suba de corto plazo: ΔW toma el mayor de dos meses y promedia por celda. La brecha descriptiva del corte "
          "de agua (`descomposicion.md`, panel 4) es otra cantidad, una mediana mes a mes, más chica, que a los 12 meses sigue "
          "sobre cero (su IC lo excluye); D2 no mide si su propia suba persiste.",
          "- Qué es nuevo: que el padre responda a la fractura de un hijo cercano ya lo trata como señal de interferencia la "
          "literatura de golpes de fractura (frac hits) de Vaca Muerta y de cuencas de Estados Unidos (referencias en "
          "[literatura.md](literatura.md)). Min y coautores, \"Data-driven Analysis for Causality of Parent-child "
          "Interactions in the Bakken\" (URTeC), tienen causalidad en el título; de ese trabajo leímos el resumen y una nota "
          "de JPT, que no describen el diseño ([literatura.md](literatura.md)). Lo que agrega este trabajo, hasta donde "
          "leímos, es el diseño sobre dato mensual público de toda la cuenca, no el hecho físico.",
          f"- Placebo de cierre: meses de padres sin hijo a menos de 2 km desde 12 meses antes hasta el mes siguiente, con menos "
          f"de medio mes producido y base de 0,8 o más, contra meses sin cierre del mismo mes calendario y grupo de edad: "
          f"{_num(cierre[2])} puntos porcentuales (IC 95%: {_ic_txt(cierre[3], cierre[4])}), {_g(cierre[5])} meses cerrados. El cierre "
          f"sube el corte de agua {mitad} del efecto (el umbral es {_num(FRACCION_CIERRE * v2[3])}).", "",
          "| Placebo | Tratados | ΔW (pp) | IC 95% | Rompe |", "| --- | ---: | ---: | --- | --- |"]
    for r in plac:
        if r[0] == "D2":
            L.append(f"| {NOMBRE_PLACEBO.get(r[1], r[1])} | {_g(r[2])} | {_num(r[3])} | {_ic_txt(r[4], r[5])} | "
                     f"{'sí' if r[6] else 'no'} |")
    lb, la = ex[("D1", "lee_ic_bajo")][2], ex[("D1", "lee_ic_alto")][2]
    qt, qc = ex[("D1", "lee_q_tratados")][2], ex[("D1", "lee_q_controles")][2]
    L += ["", "## Sin veredicto", "",
          "Por posición del padre respecto de la rama del hijo de la cohorte (de `mart_par_rama`). NOTA DE MUESTRA: solo entran "
          f"los tratados con las dos ramas medidas; {_texto_cobertura(con)}, así que estas filas son sobre todo de 2016 a 2023. "
          "La posición la decide el diseño del pad, no se asigna al azar.", "",
          "| Posición | D1: tratados | D1: ATT(1) (puntos) | IC 95% | D2: tratados | D2: ATT_W (pp) | IC 95% |",
          "| --- | ---: | ---: | --- | ---: | ---: | --- |"]
    for nombre in ("costado", "punta"):
        a, w = ex.get(("D1", f"posicion_{nombre}")), ex.get(("D2", f"posicion_{nombre}"))
        if a and w:
            L.append(f"| {nombre} | {_g(a[5])} | {_num(a[2])} | {_ic_txt(a[3], a[4])} | {_g(w[5])} | {_num(w[2])} | "
                     f"{_ic_txt(w[3], w[4])} |")
    L += ["", "Esta partición de D1 y D2 por posición no tiene veredicto propio; el contraste entre costado y punta con su regla fijada "
          "está en [mecanismo.md](mecanismo.md), donde sostiene."]
    L += ["", f"Cotas de Lee del caudal por día producido en el mes 1 (meses con 0,9 del mes producido o más): de "
          f"{_num(100 * lb)} a {_num(100 * la)} puntos. Producen el mes entero {_g(100 * qt)}% de los tratados y "
          f"{_g(100 * qc)}% de los controles; con esa diferencia el recorte es grande y la cota no separa un efecto sobre "
          "el caudal de los días que se dejan de producir. Supone monotonía: la fractura solo baja la chance de producir el "
          "mes entero.", "",
          "## Límites", "",
          "- Causa bajo supuestos nombrados, no un hecho físico medido: tendencias paralelas condicionales a cohorte y edad, que "
          "no se pueden probar después de la fractura, y la exclusión del placebo de cierre.",
          "- El corte de agua es una proporción: sube si entra agua o si el petróleo cae más que el agua. Las dos lecturas son "
          "físicas y ninguna es el cierre del operador (el placebo de cierre acota ese canal), pero D2 no dice cuál de las "
          "dos domina" + ("; lo mide D3, con su regla fijada tras ver D2, en `causal_profundo.md`." if d3 else "."),
          f"- La pretendencia de D1 no es plana: el mes -1 vale {_num(b1)} puntos (IC 95%: {_ic_txt(pri[-1][6], pri[-1][7])}). "
          "Los cercanos que se tratan antes ya venían cayendo respecto de los que se tratan después.",
          "- Solo cuenta la primera fractura a menos de 1 km de cada padre: los golpes siguientes no se miden acá.",
          f"- La elección del control importa para el petróleo: con aún no tratados ATT(1) = {_num(pri[1][5])}, sumando los "
          f"nunca tratados {_num(s1[1][5])}, y los nunca tratados con fechas sorteadas ya dan "
          f"{_num(pl[('D1', 'nunca_tratados')][3])} puntos sin ninguna fractura cerca.",
          "- Un hijo sin fecha de fractura cargada no cuenta como golpe: un control puede tener uno cerca sin que se vea.",
          _limite_nunca_agua(con),
          "- Tratado y control se definen por la distancia entre bocas de pozo, no entre ramas: según `trayectorias.md`, parte de "
          "los pares cercanos tiene las ramas a 1 km o más y parte de los pares de control las tiene a menos de 1 km. Ese error "
          "de clasificación lleva sobre todo hacia cero, pero el placebo de distancia falsa también se mide entre bocas.",
          "- Los IC no tienen ajuste por comparaciones múltiples; el veredicto sale de una sola cantidad por diseño, fijada "
          "antes.", "",
          "## Qué datos cambiarían la conclusión", "",
          "| Dato | Para qué | Dónde estaría |", "| --- | --- | --- |",
          "| Presión de boca o de fondo del padre durante la fractura del hijo | Prueba física directa de comunicación; D2 "
          "dejaría de depender del agua | Operadoras (no es público) |",
          "| Producción diaria y motivo de cada parada | Separa un cierre preventivo de un golpe dentro del mes | Operadoras; "
          "la Secretaría publica el mes y el estado |",
          "| Cronograma de etapas de la fractura del hijo | Fija el tratamiento al día y la dosis por etapa | Carga de fractura "
          "detallada |",
          "| Trayectorias 2024 y 2025 | La lectura por posición cubre sobre todo 2016 a 2023 | Secretaría (carga pendiente) |",
          "| Trazadores químicos o análisis de agua producida | Confirma qué agua viene de la fractura del hijo | Operadoras |",
          "| Producción hasta el abandono, o más años de datos | EUR real en lugar del sustituto de 24 meses; muestra para D1b | "
          "Tiempo |", "",
          "## Reproducir", "",
          "```",
          "uv run python -m pipeline.build",
          "uv run python -m pipeline.trayectorias",
          "uv run python -m pipeline.causal",
          "uv run python -m pipeline.wiki",
          "```", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ main

def _posiciones(D: dict, coh: dict) -> np.ndarray:
    """Posicion del padre respecto de la rama del hijo de la cohorte, segun `mart_par_rama`."""
    trat = np.flatnonzero(coh["tratado"])
    g = coh["g"][trat]
    col = np.clip(g - D["t0"], 0, D["T"] - 1)
    hijo = D["hijo_min"][trat, col]
    pid = D["pozo_id"][trat]
    out = np.full(len(trat), "", dtype=object)
    for k in range(len(trat)):
        out[k] = D["posicion"].get((int(hijo[k]), int(pid[k])), "")
    return out


def main(path=DATA / "warehouse.duckdb") -> None:
    """Corre los tres disenos (D1, D1b y D2) y escribe sus marts."""
    con = duckdb.connect(str(path))
    D = cargar(con)
    coh = cohortes(D)
    rng = np.random.default_rng(SEMILLA_CAUSAL)

    cel_pri = celdas(D, coh, H_CORTO, False)
    cel_s1 = celdas(D, coh, H_CORTO, True)
    trat_ff, g_ff = _cohorte_falsa_fecha(D, coh)
    cel_ff = celdas(D, coh, H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = _cohorte_falsa_distancia(D, coh, H_CORTO)
    cel_fd = celdas(D, coh, H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = _cohorte_nunca_tratados(D, coh)
    cel_nt = celdas(D, coh, H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)

    cel_d1b = celdas_d1b(D, coh)
    universo = [cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b]
    wells = []
    for grupo in universo:
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = _pesos_bloques(D, wells, REPS, rng)

    d1 = diseno_d1(D, W, coh, cel_pri, cel_s1)
    d1b = diseno_d1b(D, W, cel_d1b)
    r1 = d1["r"]
    idx = d1["idx"]

    # placebos de D1
    pl1 = {}
    for nombre, cel in (("fecha_falsa", cel_ff), ("distancia_falsa", cel_fd), ("nunca_tratados", cel_nt)):
        rr = bootstrap(D, cel, (E_PRINCIPAL,), W)
        pl1[nombre] = rr
    rotos1 = [n for n, rr in pl1.items() if rompe(float(rr["est"][0]), float(rr["ic_bajo"][0]),
                                                   float(rr["ic_alto"][0]), UMBRAL_ROTURA_PUNTOS)]

    # dejar un operador afuera
    ops: dict[str, int] = {}
    for ce in cel_pri:
        for i in ce["tratados"]:
            ops[str(D["operador"][i])] = ops.get(str(D["operador"][i]), 0) + 1
    filas_op = []
    altos_op = []
    for op, n_op in sorted(ops.items()):
        if n_op < MIN_TRATADOS_OPERADOR:
            continue
        cel_op = _celdas_sin_operador(D, cel_pri, op)
        rr = bootstrap(D, cel_op, (E_PRINCIPAL,), W)
        filas_op.append((op, int(rr["n_tratados"][0]), float(rr["est"][0]), float(rr["ic_bajo"][0]),
                         float(rr["ic_alto"][0])))
        altos_op.append(float(rr["ic_alto"][0]))
    ver1 = veredicto_d1(d1["n_tratados"], d1["n_bloques"], bool(rotos1), float(r1["ic_alto"][idx[E_PRINCIPAL]]),
                         d1["m_est"], altos_op)

    # D1b
    r1b = d1b["r"]
    ver1b = veredicto_d1b(d1b["n_tratados"], float(r1b["ic_bajo"]), float(r1b["ic_alto"]), d1["b1"])
    acum = acumulado_persistencia(D, W, coh, d1b["celdas"])

    # D2
    d2 = diseno_d2(D, W, cel_pri, cel_ff, cel_fd)
    cierre = placebo_cierre(D, W)
    rotos2 = [n for n, rr in (("previo", d2["previo"]), ("fecha_falsa", d2["fecha_falsa"]),
                               ("distancia_falsa", d2["distancia_falsa"]))
              if rompe(float(rr["est"]), float(rr["ic_bajo"]), float(rr["ic_alto"]), UMBRAL_ROTURA_AGUA)]
    ver2 = veredicto_d2(int(d2["r"]["n_tratados"]), bool(rotos2), float(cierre["est"]), float(cierre["ic_bajo"]),
                        float(cierre["ic_alto"]), float(d2["r"]["est"]), float(d2["r"]["ic_bajo"]))

    # descriptivos: heterogeneidad por posicion y cotas de Lee
    pos = _posiciones(D, coh)
    filas_pos = []
    for nombre in ("costado", "punta"):
        sel = np.flatnonzero(coh["tratado"])[pos == nombre]
        cel_pos = celdas(D, coh, H_CORTO, False, tratados=sel)
        rr = bootstrap(D, cel_pos, (E_PRINCIPAL,), W)
        vt, vc = _valores_agua(D, cel_pos, 0)
        prep = _preparar(cel_pos, vt, vc)
        rr_agua = _bootstrap_prep(D, prep, W)
        filas_pos.append((nombre, int(rr["n_tratados"][0]), float(rr["est"][0]), float(rr["ic_bajo"][0]),
                          float(rr["ic_alto"][0]), rr_agua))
    lee = lee_limites(**_lee_grupos(D, coh, cel_pri))

    # ---- marts
    filas_serie = []
    for j, e in enumerate(E_SERIE):
        filas_serie.append(("D1", "principal", int(e), int(r1["n_tratados"][j]), int(r1["n_controles"][j]),
                            float(r1["est"][j]), float(r1["ic_bajo"][j]), float(r1["ic_alto"][j])))
    for j, e in enumerate(E_SERIE):
        filas_serie.append(("D1", "S1", int(e), int(d1["r_s1"]["n_tratados"][j]), int(d1["r_s1"]["n_controles"][j]),
                            float(d1["r_s1"]["est"][j]), float(d1["r_s1"]["ic_bajo"][j]),
                            float(d1["r_s1"]["ic_alto"][j])))
    filas_serie.append(("D2", "principal", 0, int(d2["r"]["n_tratados"]), int(d2["r"]["n_controles"]),
                        float(d2["r"]["est"]), float(d2["r"]["ic_bajo"]), float(d2["r"]["ic_alto"])))
    filas_serie.append(("D1b", "persistencia", int(E_PERSISTENCIA[0]), int(r1b["n_tratados"]),
                        int(r1b["n_controles"]), float(r1b["est"]), float(r1b["ic_bajo"]), float(r1b["ic_alto"])))

    filas_placebo = []
    for nombre, rr in pl1.items():
        filas_placebo.append(("D1", nombre, int(rr["n_tratados"][0]), float(rr["est"][0]), float(rr["ic_bajo"][0]),
                              float(rr["ic_alto"][0]), nombre in rotos1))
    for nombre, rr in (("previo", d2["previo"]), ("fecha_falsa", d2["fecha_falsa"]),
                       ("distancia_falsa", d2["distancia_falsa"])):
        filas_placebo.append(("D2", nombre, int(rr["n_tratados"]), float(rr["est"]), float(rr["ic_bajo"]),
                              float(rr["ic_alto"]), nombre in rotos2))

    filas_extra = [
        ("D1", "M*", float(d1["m_est"]), float("nan"), float("nan"), int(d1["n_tratados"])),
        ("D1", "potencia_pretrendencia", float(d1["potencia"]), float("nan"), float("nan"), int(d1["n_tratados"])),
        ("D1", "lee_ic_bajo", float(lee["ic_bajo"]), float("nan"), float("nan"), int(d1["n_tratados"])),
        ("D1", "lee_ic_alto", float(lee["ic_alto"]), float("nan"), float("nan"), int(d1["n_tratados"])),
        ("D1", "lee_q_tratados", float(lee["q_tratados"]), float("nan"), float("nan"), int(d1["n_tratados"])),
        ("D1", "lee_q_controles", float(lee["q_controles"]), float("nan"), float("nan"), int(d1["n_tratados"])),
        ("D2", "cierre_placebo", float(cierre["est"]), float(cierre["ic_bajo"]), float(cierre["ic_alto"]),
         int(cierre["n_tratados"])),
        ("D1b", "acumulado_e0_e23", float(acum["est"]), float(acum["ic_bajo"]), float(acum["ic_alto"]),
         int(r1b["n_tratados"])),
    ]
    for nombre, n_op, est, bajo, alto, rr_agua in filas_pos:
        filas_extra.append(("D1", f"posicion_{nombre}", float(est), float(bajo), float(alto), int(n_op)))
        filas_extra.append(("D2", f"posicion_{nombre}", float(rr_agua["est"]), float(rr_agua["ic_bajo"]),
                            float(rr_agua["ic_alto"]), int(rr_agua["n_tratados"])))

    trat_d1b = np.concatenate([ce["tratados"] for ce in cel_d1b]) if cel_d1b else np.zeros(0, dtype=np.int64)
    nb_d1b = _n_bloques(D, trat_d1b)
    trat_d2 = np.concatenate([ce["tratados"] for ce in cel_pri]) if cel_pri else np.zeros(0, dtype=np.int64)
    nb_d2 = _n_bloques(D, trat_d2)
    filas_veredicto = [
        ("D1", ver1, "ATT(1)", float(r1["est"][idx[E_PRINCIPAL]]), float(r1["ic_bajo"][idx[E_PRINCIPAL]]),
         float(r1["ic_alto"][idx[E_PRINCIPAL]]), int(d1["n_tratados"]), int(d1["n_bloques"]),
         f"M*={d1['m_est']:.2f}, placebos rotos: {', '.join(rotos1) if rotos1 else 'ninguno'}, "
         f"pretrendencia: {d1['potencia']:.2f} puntos por mes"),
        ("D1b", ver1b, "persistencia", float(r1b["est"]), float(r1b["ic_bajo"]), float(r1b["ic_alto"]),
         int(r1b["n_tratados"]), int(nb_d1b), f"b(-1) de D1: {d1['b1']:.1f} puntos"),
        ("D2", ver2, "ATT_W", float(d2["r"]["est"]), float(d2["r"]["ic_bajo"]), float(d2["r"]["ic_alto"]),
         int(d2["r"]["n_tratados"]), int(nb_d2),
         f"placebos rotos: {', '.join(rotos2) if rotos2 else 'ninguno'}, cierre: {cierre['est']:.2f} pp"),
    ]

    _escribir(con, "mart_causal_serie", COLS_SERIE, filas_serie)
    _escribir(con, "mart_causal_placebo", COLS_PLACEBO, filas_placebo)
    _escribir(con, "mart_causal_operador", COLS_OPERADOR, filas_op)
    _escribir(con, "mart_causal_extra", COLS_EXTRA, filas_extra)
    _escribir(con, "mart_causal_veredicto", COLS_VEREDICTO, filas_veredicto)

    print(f"D1: ATT(1) = {r1['est'][idx[E_PRINCIPAL]]:+.1f} puntos (IC 95%: {r1['ic_bajo'][idx[E_PRINCIPAL]]:+.1f} a "
          f"{r1['ic_alto'][idx[E_PRINCIPAL]]:+.1f}), tratados {d1['n_tratados']}, bloques {d1['n_bloques']}, "
          f"M* = {d1['m_est']:.2f}, veredicto: {ver1}")
    print(f"D1b: persistencia (e = 7 a 24) = {r1b['est']:+.1f} puntos (IC 95%: {r1b['ic_bajo']:+.1f} a "
          f"{r1b['ic_alto']:+.1f}), tratados {r1b['n_tratados']}, acumulado e = 0 a 23 = {acum['est']:+.1f}, "
          f"veredicto: {ver1b}")
    print(f"D2: ATT_W = {d2['r']['est']:+.2f} puntos porcentuales (IC 95%: {d2['r']['ic_bajo']:+.2f} a "
          f"{d2['r']['ic_alto']:+.2f}), tratados {d2['r']['n_tratados']}, placebo de cierre = {cierre['est']:+.2f}, "
          f"veredicto: {ver2}")
    con.close()


if __name__ == "__main__":
    main()
