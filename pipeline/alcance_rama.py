"""Alcance y dilución de la huella medidos entre ramas: la brecha del mes 1 con la distancia entre la rama del hijo y la del padre.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.alcance_rama

Para que sirve. El estudio mide la distancia entre un hijo y un padre en superficie (boca contra boca). La pagina de trayectorias
(wiki/hallazgos/trayectorias.md) mostro que esa distancia clasifica mal: el 23% de los pares cercanos en superficie (menos de
1 km) tiene las ramas a 1 km o mas, y el 8% de los pares de control (2 a 5 km) tiene las ramas a menos de 1 km. Esta pagina
repite la medicion del alcance de la huella y de la dilucion del control con la distancia entre ramas en lugar de la de superficie.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no. Un veredicto "no firme" o
"sin muestra" es un resultado terminado: no se rediseña la regla para evitarlo. Fuente del plan: fase 4 del proyecto, unidad U1b.

Que se habia mirado antes de fijarla
- Publicado en el repo: la pagina de trayectorias (cobertura, la distancia entre ramas por banda de superficie, el 23% y el 8% de
  arriba) y mart_par_rama (eje, solape y posicion del padre). Ninguna brecha de caudal se calculo con la distancia entre ramas
  antes de fijar esta regla; tampoco se conto ninguna banda de esta pagina.
- Los umbrales salen del plan de la fase 4, escrito el mismo dia antes de calcular. El umbral de -10 puntos es el de la regla R1
  de pipeline.bloques (CRUCE_R1) aplicado a la banda mas cercana.

Datos y eventos (el modelo principal; solo de el sale el veredicto)
- Eventos: los del estudio principal, placebo.marco(D, D["hijo_mes"], ks=(1,), base=BASE_ORIGINAL), con D = placebo.cargar(con):
  cada evento es un padre y el mes de fractura de su hijo mas cercano en superficie (desempate por el menor id), el padre con al
  menos 6 meses de produccion y una base de los meses -3 a -1 mayor que 1 m3/d. Indice = caudal por dia del mes k sobre esa
  base. Los eventos son los mismos del estudio; lo unico que cambia es la distancia que los clasifica.
- Muestra de esta pagina: los eventos cuyo par (hijo, padre) esta en mart_trayectoria_par, es decir, con la rama del hijo y la del
  padre medidas. Un padre o un control sin rama medida no entra. El hijo de cada evento es el de placebo.marco (el mas cercano en
  superficie) y la distancia entre ramas del evento es la menor distancia entre las dos ramas en planta (`m_min` de
  mart_trayectoria_par), en metros.
- Alcance de la muestra: mart_trayectoria_par solo tiene pares con las bocas a menos de 5 km, asi que un padre con la rama a menos
  de 2 km de la del hijo pero la boca a mas de 5 km no esta. Esta pagina lo dice y no lo corrige.
- Cobertura de la muestra: las ramas medidas cubren entre 80 y 94% de los hijos fracturados de 2016 a 2023 pero solo el 39% de
  2024 y el 25% de 2025 (la fuente todavia no publica la mayoria de los pozos recientes), asi que la muestra es sobre todo de 2016
  a 2023. La pagina y el README lo dicen junto al veredicto, con los eventos por ano del hijo.
- Control lateral: eventos de la muestra con m_min de 2.000 m o mas. Para un cercano en una banda, el control es siempre este y
  nunca los de la banda vecina. Un evento que sea a la vez cercano y control no existe: las bandas no se solapan.
- Brecha: mediana del indice de los eventos del grupo menos mediana del indice del control, sin contar los datos faltantes
  (placebo.brecha). Se publica en puntos de indice (100 por la brecha).
- Intervalos: bootstrap de percentiles 95% (2,5 y 97,5) por bloques espaciales de 5 km (pipeline.bloques: el bloque del pad del
  hijo del evento, `bloques.cargar(con)` y la grilla `bloque_5km`), REPS_BOOT repeticiones y semilla SEMILLA_ALCANCE. Cada
  repeticion remuestrea bloques completos de la muestra y calcula con ellos TODAS las cantidades de la pagina; asi la brecha de
  cada banda, la diferencia de H-R2 y la de H-R3 salen de las mismas remuestras. Una remuestra en que un grupo queda vacio se
  descarta y se cuenta.

H-R1, alcance. Brecha del mes 1 (k = 1) por banda de la distancia entre ramas, cada una contra el control lateral:
BANDAS_RAMA_M = 0 a 300, 300 a 600, 600 a 1.000 y 1.000 a 2.000 m (cada banda incluye el extremo de abajo y deja afuera el de
arriba). Se publica tambien la cantidad de eventos de cada banda y del control.
  1. "sin muestra": alguna de las cuatro bandas o el control lateral tiene menos de N_MIN (100) eventos con el indice del mes 1
     medido, o la muestra tiene menos de MIN_BLOQUES (30) bloques de 5 km.
  2. "alcance medido": el IC de la banda de 0 a 300 m queda entero por debajo de -10 puntos (limite alto menor que -0,10) Y la
     brecha de la banda de 1.000 a 2.000 m tiene valor absoluto menor que 5 puntos (UMBRAL_PLANO) con un IC que incluye cero. El
     alcance que se informa es el borde superior de la ultima banda (la mas lejana) cuyo IC excluye cero.
  3. "gradiente": el IC de la banda de 1.000 a 2.000 m excluye cero. No se informa un alcance: la huella sigue por lo menos hasta
     esa banda (cota inferior del alcance), y la pagina dice que no se midio el borde.
  4. "no firme": en cualquier otro caso.
  El orden es ese; las condiciones de 2 y 3 no pueden darse juntas.

H-R2, dilucion de la huella por la distancia de superficie. Sobre los mismos eventos de la muestra, en las mismas remuestras:
  * A = brecha del mes 1 de los padres cercanos por distancia entre ramas (m_min menor que 600 m, CERCA_RAMA_M) contra el control
    lateral (m_min de 2.000 m o mas).
  * B = brecha del mes 1 de los padres cercanos en superficie (banda 0 de placebo.marco, menos de 1 km) contra el control de
    superficie usual (banda 2, de 2 a 5 km), tambien solo con eventos de la muestra.
  * Estadistico: A menos B. Se publican A, B y A menos B con su IC y los eventos de cada grupo.
  1. "sin muestra": alguno de los cuatro grupos tiene menos de N_MIN eventos con el indice medido.
  2. "la distancia de superficie diluye la huella": A menos B es negativo con un IC (limite alto) que queda por debajo de cero.
  3. "no se separa": en otro caso.

H-R3, control contaminado. Entre los controles de superficie de la muestra (banda 2, de 2 a 5 km): el grupo contaminado es el de
los que tienen la rama a menos de CONTAMINADO_RAMA_M (1.000 m) de la del hijo, y el limpio el de los que la tienen a 2.000 m o
mas. Estadistico: mediana del indice del mes 1 del contaminado menos la del limpio (la brecha entre esos dos controles).
  1. "sin muestra": alguno de los dos grupos tiene menos de N_MIN eventos con el indice medido.
  2. "control contaminado": la diferencia es negativa y su IC (limite alto) queda por debajo de cero.
  3. "control limpio": en otro caso.
  Solo con "control contaminado" se publica ademas, de forma descriptiva y sin veredicto: la brecha del mes 1 y el diferido
  de los meses 0 a 6 de los cercanos del estudio principal contra el control lateral limpio, junto al mismo calculo contra el
  control de superficie usual, y la pagina dice en "Limites" que el control de superficie subestima el diferido. Definicion:
  los cercanos son TODOS los eventos de banda 0 de placebo.marco (no solo los de la muestra: no necesitan rama medida); el
  control usual es la banda 2 de placebo.marco; el control lateral limpio son los eventos de la muestra con m_min de 2.000 m o
  mas que no son de banda 0. El diferido de un evento es la suma, sobre los meses k = 0 a 6, de (mediana del indice de los
  controles en k, por la base del padre, menos el caudal por dia observado) por los dias del mes calendario, en barriles
  (BBL_M3), sin duplicar los meses ni descontar la brecha previa: es la variante "original" de pipeline.diferido, que es una
  cota superior; el rango del estudio (sin duplicar y descontando la previa) no se recalcula aca. Un mes sin dato no suma ni resta.
  IC de la brecha y del total por los mismos bloques de 5 km.

Sensibilidades (se publican; no cambian ningun veredicto, que viene solo del modelo principal)
  S1. Hijo mas cercano por rama: la distancia del evento es la menor m_min entre los pares (hijo, padre) de mart_trayectoria_par de
      ese padre y ese mes de fractura (el hijo mas cercano entre ramas, no el mas cercano en superficie); los mismos eventos,
      las mismas bandas y el mismo control. Tabla de H-R1 y A de H-R2.
  S2. Base limpia: lo mismo que el modelo principal con la base de los meses -6 a -4 (placebo.BASE_LIMPIA) en k = 1 y en k = -1
      (la previa de cada banda contra el control lateral). Tabla de H-R1 en los dos meses.
  S3. Hijos fracturados hasta 2023: el modelo principal sobre los eventos cuyo hijo se fracturo en 2023 o antes (la parte bien
      cubierta de la fuente). Tabla de H-R1 y A, B y A menos B.
  Descriptivo: los eventos de la muestra por ano de fractura del hijo y por banda de distancia entre ramas.

Que NO prueba
  * Es una huella medida: la misma brecha del estudio principal con otra distancia, sin afirmacion causal y sin ajuste por
    comparaciones multiples. Ninguna brecha de esta pagina cambia el 19 a 23 del estudio, que sigue en distancia de superficie y
    en toda la muestra.
  * La muestra es sobre todo de 2016 a 2023: no dice nada de 2024 en adelante.
  * El control lateral solo sabe de las ramas medidas: un padre con un hijo del mismo mes de rama no publicada puede estar
    golpeado igual. Un resultado "control limpio" es limpio respecto de las ramas conocidas.
  * La distancia entre ramas es en planta: no tiene la cota de cada punto. La diferencia de profundidad vertical y la unidad
    donde navega cada rama estan en mart_trayectoria_par y esta pagina no las usa.
  * Un "alcance medido" es el borde de las bandas probadas (300, 600, 1.000 y 2.000 m), no un borde exacto.

Que cambia con cada veredicto (en la pagina, el README y los limites)
  * H-R1: "alcance medido" fija el alcance en metros entre ramas; "gradiente" dice que la huella sigue mas alla de 2.000 m entre
    ramas y que no se midio el borde; "no firme" y "sin muestra" no cambian ninguna linea.
  * H-R2: "la distancia de superficie diluye la huella" agrega a "Limites" que el 23 del estudio, medido por superficie, subestima
    la brecha entre ramas (y da A); "no se separa" dice que medir entre ramas no cambia la lectura.
  * H-R3: "control contaminado" agrega a "Limites" que el control de superficie subestima el diferido y publica el recalculo;
    "control limpio" dice que el control de 2 a 5 km no se ensucia por ramas cercanas al medirlo entre ramas.
  * Nada de esto cambia data/prospectiva_congelada.json ni las reglas P1 y P2.
"""
from __future__ import annotations

import calendar

import duckdb
import numpy as np

from pipeline import bloques, placebo
from pipeline.costo import SEMILLA, _clusters, _escribir, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import _g, _pts

SEMILLA_ALCANCE = SEMILLA + 80          # una semilla propia (dias_perdidos usa +60 y golpes_mismo_mes +70)
REPS_BOOT = placebo.REPS_BOOT           # repeticiones del bootstrap por bloques de 5 km (400, como el resto del estudio)
TAM_BLOQUE_KM = 5.0                     # la grilla de pipeline.bloques que usa el intervalo
K_TITULAR = 1                           # el mes de la brecha titular
K_PREVIO = -1                           # el mes de la previa (S2)
BASE = placebo.BASE_ORIGINAL            # meses -3 a -1: la base del estudio principal
BASE_S2 = placebo.BASE_LIMPIA           # meses -6 a -4, para S2
BANDAS_RAMA_M = ((0.0, 300.0), (300.0, 600.0), (600.0, 1000.0), (1000.0, 2000.0))  # H-R1: [abajo, arriba) en metros
CONTROL_RAMA_M = 2000.0                 # control lateral: m_min de 2.000 m o mas
CERCA_RAMA_M = 600.0                    # H-R2: cercano por rama
CONTAMINADO_RAMA_M = 1000.0             # H-R3: control de superficie con la rama a menos de esto de la del hijo
UMBRAL_ALCANCE = -0.10                  # H-R1: limite alto del IC de la banda de 0 a 300 m por debajo de esto (-10 puntos)
UMBRAL_PLANO = 0.05                     # H-R1: |brecha| de la banda de 1.000 a 2.000 m por debajo de esto (5 puntos)
N_MIN = 100                             # eventos con el indice medido en cada grupo para que haya veredicto
MIN_BLOQUES = 30                        # bloques de 5 km minimos de la muestra
ANIO_S3 = 2023                          # S3: hijos fracturados en este ano o antes
MESES_DIFERIDO = tuple(range(0, 7))     # H-R3 descriptivo: diferido de los meses 0 a 6
BBL_M3 = 6.2898                         # barriles por metro cubico, el factor de pipeline.diferido
VEREDICTOS_R1 = ("sin muestra", "alcance medido", "gradiente", "no firme")
VEREDICTOS_R2 = ("sin muestra", "la distancia de superficie diluye la huella", "no se separa")
VEREDICTOS_R3 = ("sin muestra", "control contaminado", "control limpio")

# ------------------------------------------------------------------ carga

NOMBRES_BANDA = ("brecha_0_300", "brecha_300_600", "brecha_600_1000", "brecha_1000_2000")
NOMBRES_EST = NOMBRES_BANDA + ("A", "B", "A_menos_B", "C_menos_L")
COLS_ALCANCE = [("modelo", "varchar"), ("k", "integer"), ("estadistico", "varchar"), ("valor", "double"),
                 ("ic_bajo", "double"), ("ic_alto", "double"), ("descartadas", "integer"),
                 ("n", "integer"), ("n_ref", "integer")]
COLS_PRUEBA = [("prueba", "varchar"), ("veredicto", "varchar"), ("alcance_m", "double"), ("eventos", "integer"),
               ("bloques", "integer"), ("reps", "integer"), ("eventos_marco", "integer")]
COLS_ANIO = [("anio", "integer"), ("eventos", "integer"), ("n_0_300", "integer"), ("n_300_600", "integer"),
              ("n_600_1000", "integer"), ("n_1000_2000", "integer"), ("n_control", "integer")]
COLS_DIFERIDO = [("control", "varchar"), ("n_cercanos", "integer"), ("n_control", "integer"),
                  ("brecha_mes1", "double"), ("brecha_ic_bajo", "double"), ("brecha_ic_alto", "double"),
                  ("diferido_bbl", "double"), ("diferido_ic_bajo", "double"), ("diferido_ic_alto", "double")]


def cargar(con) -> dict:
    """Datos de la pagina: el D del estudio con la grilla de bloques y los pares medidos con su distancia.

    `par_hijo` y `par_padre` son ids de pozo; `par_m` es el `m_min` de cada par de mart_trayectoria_par.
    """
    D = bloques.cargar(con)
    pid = np.array([int(r[0]) for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()],
                   dtype=np.int64)
    filas = con.execute("select hijo, padre, m_min from mart_trayectoria_par").fetchall()
    par_hijo = np.array([int(f[0]) for f in filas], dtype=np.int64)
    par_padre = np.array([int(f[1]) for f in filas], dtype=np.int64)
    par_m = np.array([np.nan if f[2] is None else float(f[2]) for f in filas], dtype=float)
    return {"D": D, "pid": pid, "par_hijo": par_hijo, "par_padre": par_padre, "par_m": par_m}


def _posiciones(C: dict) -> tuple[dict, dict]:
    """Posicion de cada id de hijo en D["hijo_id"] y de cada id de padre en C["pid"]."""
    D = C["D"]
    pos_hijo = {int(v): i for i, v in enumerate(D["hijo_id"])}
    pos_padre = {int(v): i for i, v in enumerate(C["pid"])}
    return pos_hijo, pos_padre


def _distancias(C: dict) -> tuple[dict, dict]:
    """La distancia del par (hijo, padre) y la menor distancia de cada (padre, mes de fractura del hijo)."""
    D = C["D"]
    pos_hijo, pos_padre = _posiciones(C)
    propio: dict[tuple[int, int], float] = {}
    por_padre_mes: dict[int, float] = {}
    for h, p, mm in zip(C["par_hijo"], C["par_padre"], C["par_m"]):
        if mm is None or np.isnan(mm):
            continue
        hi = pos_hijo.get(int(h))
        pi = pos_padre.get(int(p))
        if hi is None or pi is None:
            continue
        propio[(hi, pi)] = float(mm)
        clave = pi * 100_000 + int(D["hijo_mes"][hi])
        if clave not in por_padre_mes or float(mm) < por_padre_mes[clave]:
            por_padre_mes[clave] = float(mm)
    return propio, por_padre_mes


def _armar(C: dict, m: dict, filtrar: bool) -> dict:
    """Le agrega al marco la distancia entre ramas, el anio del hijo y el bloque, y filtra la muestra."""
    D = C["D"]
    propio, por_padre_mes = _distancias(C)
    n = len(m["padre"])
    m_min = np.full(n, np.nan)
    m_min_s1 = np.full(n, np.nan)
    for i in range(n):
        h, p = int(m["hijo"][i]), int(m["padre"][i])
        if (h, p) in propio:
            m_min[i] = propio[(h, p)]
        clave = p * 100_000 + int(D["hijo_mes"][h])
        if clave in por_padre_mes:
            m_min_s1[i] = por_padre_mes[clave]
    s = {"padre": m["padre"], "hijo": m["hijo"], "km": m["km"], "mes": m["mes"], "rumbo": m["rumbo"],
         "banda": m["banda"], "clave": m["clave"], "area": m["area"], "lat": m["lat"], "edad": m["edad"],
         "idx": {k: m["idx"][k] for k in m["idx"]}, "anio": D["hijo_anio"][m["hijo"]],
         "bloque": D["bloque_5km"][m["clave"]], "m_min": m_min, "m_min_s1": m_min_s1}
    n_marco = n
    if filtrar:
        keep = ~np.isnan(m_min)
        s = {k: (v[keep] if isinstance(v, np.ndarray) else {kk: vv[keep] for kk, vv in v.items()})
             for k, v in s.items()}
    s["n_marco"] = n_marco
    return s


def muestra(C: dict, base=BASE, ks=(K_TITULAR,)) -> dict:
    """La muestra de la pagina: los eventos del marco cuyo par (hijo, padre) tiene la rama medida.

    Trae `m_min` (la distancia del par del evento), `m_min_s1` (la menor distancia de los pares del mismo
    padre en ese mes), `anio` (del hijo), `bloque` (de 5 km) y `n_marco` (los eventos antes del filtro).
    """
    m = placebo.marco(C["D"], C["D"]["hijo_mes"], ks=tuple(ks), base=base)
    return _armar(C, m, filtrar=True)


def muestra_todos(C: dict, ks, base=BASE) -> dict:
    """El marco completo, sin filtrar por la distancia medida, con `m_min` y `bloque` agregados."""
    m = placebo.marco(C["D"], C["D"]["hijo_mes"], ks=tuple(ks), base=base)
    return _armar(C, m, filtrar=False)


# ------------------------------------------------------------------ estadisticos

def _med(x: np.ndarray) -> float:
    """Mediana que ignora los nan; nan si no queda ningun valor."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    return float(np.median(x)) if x.size else float("nan")


def estadisticos(v: np.ndarray, d: np.ndarray, bsup: np.ndarray, i=None) -> dict[str, float]:
    """Las ocho cantidades de la pagina para una muestra (o para una remuestra `i`).

    `v` es el indice del mes 1, `d` la distancia entre ramas (m) y `bsup` la banda de superficie.
    """
    v = np.asarray(v, dtype=float)
    d = np.asarray(d, dtype=float)
    bsup = np.asarray(bsup)
    if i is not None:
        v, d, bsup = v[i], d[i], bsup[i]
    ctrl = _med(v[d >= CONTROL_RAMA_M])
    est: dict[str, float] = {}
    for (lo, hi), nombre in zip(BANDAS_RAMA_M, NOMBRES_BANDA):
        est[nombre] = _med(v[(d >= lo) & (d < hi)]) - ctrl
    est["A"] = _med(v[d < CERCA_RAMA_M]) - ctrl
    est["B"] = _med(v[bsup == 0]) - _med(v[bsup == 2])
    est["A_menos_B"] = est["A"] - est["B"]
    est["C_menos_L"] = (_med(v[(bsup == 2) & (d < CONTAMINADO_RAMA_M)])
                        - _med(v[(bsup == 2) & (d >= CONTROL_RAMA_M)]))
    return est


def conteos(v: np.ndarray, d: np.ndarray, bsup: np.ndarray) -> dict[str, int]:
    """Cuantos eventos con el indice medido hay en cada grupo de la pagina."""
    v = np.asarray(v, dtype=float)
    d = np.asarray(d, dtype=float)
    bsup = np.asarray(bsup)
    ok = ~np.isnan(v)
    c: dict[str, int] = {}
    for (lo, hi), nombre in zip(BANDAS_RAMA_M, NOMBRES_BANDA):
        c["n_" + nombre[len("brecha_"):]] = int((ok & (d >= lo) & (d < hi)).sum())
    c["n_control"] = int((ok & (d >= CONTROL_RAMA_M)).sum())
    c["n_cerca"] = int((ok & (d < CERCA_RAMA_M)).sum())
    c["n_sup_cerca"] = int((ok & (bsup == 0)).sum())
    c["n_sup_control"] = int((ok & (bsup == 2)).sum())
    c["n_contaminado"] = int((ok & (bsup == 2) & (d < CONTAMINADO_RAMA_M)).sum())
    c["n_limpio"] = int((ok & (bsup == 2) & (d >= CONTROL_RAMA_M)).sum())
    c["n_eventos"] = int(ok.sum())
    return c


def bootstrap(v: np.ndarray, d: np.ndarray, bsup: np.ndarray, bloque: np.ndarray,
              reps=REPS_BOOT, semilla=SEMILLA_ALCANCE) -> dict[str, dict]:
    """El valor puntual y el IC 95% por bootstrap de bloques de 5 km, con las mismas remuestras para todo.

    En cada remuestrea se calculan las ocho cantidades juntas, asi que los IC son comparables entre si.
    """
    v = np.asarray(v, dtype=float)
    d = np.asarray(d, dtype=float)
    bsup = np.asarray(bsup)
    bloque = np.asarray(bloque)
    puntual = estadisticos(v, d, bsup)
    grupos = _clusters(bloque)
    rng = np.random.default_rng(semilla)
    draws: dict[str, list[float]] = {n: [] for n in NOMBRES_EST}
    for _ in range(reps):
        i = _remuestra(rng, grupos)
        e = estadisticos(v, d, bsup, i)
        for n in NOMBRES_EST:
            draws[n].append(e[n])
    out: dict[str, dict] = {}
    for n in NOMBRES_EST:
        arr = np.asarray(draws[n], dtype=float)
        buenos = arr[~np.isnan(arr)]
        descartadas = int(arr.size - buenos.size)
        if buenos.size:
            lo, hi = (float(x) for x in np.percentile(buenos, [2.5, 97.5]))
        else:
            lo = hi = float("nan")
        out[n] = {"valor": puntual[n], "ic_bajo": lo, "ic_alto": hi, "descartadas": descartadas}
    out["_bloques"] = int(len(np.unique(bloque[~np.isnan(v)])))
    return out


# ------------------------------------------------------------------ veredictos

def veredicto_r1(est: dict, cnt: dict, bloques: int) -> tuple[str, float | None]:
    """H-R1: el veredicto y el alcance medido (None si el veredicto no informa un alcance)."""
    bandas = (cnt["n_0_300"], cnt["n_300_600"], cnt["n_600_1000"], cnt["n_1000_2000"], cnt["n_control"])
    if min(bandas) < N_MIN or bloques < MIN_BLOQUES:
        return VEREDICTOS_R1[0], None
    lejos = est["brecha_1000_2000"]
    if (est["brecha_0_300"]["ic_alto"] < UMBRAL_ALCANCE and abs(lejos["valor"]) < UMBRAL_PLANO
            and lejos["ic_bajo"] <= 0 <= lejos["ic_alto"]):
        alcance = None
        for (_, hi), nombre in zip(BANDAS_RAMA_M, NOMBRES_BANDA):
            e = est[nombre]
            if e["ic_alto"] < 0 or e["ic_bajo"] > 0:
                alcance = float(hi)
        return VEREDICTOS_R1[1], alcance
    if lejos["ic_alto"] < 0 or lejos["ic_bajo"] > 0:
        return VEREDICTOS_R1[2], None
    return VEREDICTOS_R1[3], None


def veredicto_r2(est: dict, cnt: dict) -> str:
    """H-R2: la distancia de superficie diluye la huella o no se separa."""
    if min(cnt["n_cerca"], cnt["n_control"], cnt["n_sup_cerca"], cnt["n_sup_control"]) < N_MIN:
        return VEREDICTOS_R2[0]
    if est["A_menos_B"]["ic_alto"] < 0 and est["A_menos_B"]["valor"] < 0:
        return VEREDICTOS_R2[1]
    return VEREDICTOS_R2[2]


def veredicto_r3(est: dict, cnt: dict) -> str:
    """H-R3: el control de superficie esta contaminado o esta limpio."""
    if cnt["n_contaminado"] < N_MIN or cnt["n_limpio"] < N_MIN:
        return VEREDICTOS_R3[0]
    e = est["C_menos_L"]
    if e["valor"] < 0 and e["ic_alto"] < 0:
        return VEREDICTOS_R3[1]
    return VEREDICTOS_R3[2]


# ------------------------------------------------------------------ descriptivos

def por_anio(s: dict) -> list[tuple]:
    """Los eventos de la muestra por ano de fractura del hijo y por banda de distancia entre ramas.

    `eventos` son los eventos de la muestra de ese ano (con la rama medida) y los `n_...` son los que
    tienen el indice del mes 1 medido. La ultima fila es el total, con `anio` en 0.
    """
    v = s["idx"][K_TITULAR]
    filas = []
    for anio in sorted({int(a) for a in s["anio"]}):
        sel = s["anio"] == anio
        c = conteos(v[sel], s["m_min"][sel], s["banda"][sel])
        filas.append((anio, int(sel.sum()), c["n_0_300"], c["n_300_600"], c["n_600_1000"],
                      c["n_1000_2000"], c["n_control"]))
    c = conteos(v, s["m_min"], s["banda"])
    filas.append((0, int(len(s["m_min"])), c["n_0_300"], c["n_300_600"], c["n_600_1000"],
                  c["n_1000_2000"], c["n_control"]))
    return filas


def _dias_mes(j: int) -> int:
    """Dias del calendario del mes j (los meses desde 2000-01)."""
    return calendar.monthrange(2000 + j // 12, j % 12 + 1)[1]


def _diferido_evento(base: float, tasa: np.ndarray, c: np.ndarray, dias: np.ndarray) -> float:
    """El diferido de un evento cercano, en barriles: (c * base - tasa) * dias * BBL_M3, mes a mes.

    Un mes sin dato (tasa o c nan) no suma ni resta.
    """
    val = (np.asarray(c, dtype=float) * base - np.asarray(tasa, dtype=float)) * np.asarray(dias, dtype=float) * BBL_M3
    val = val[~np.isnan(val)]
    return float(val.sum()) if val.size else 0.0


def _diferido_vec(base: np.ndarray, tasa: np.ndarray, c: float, dias: np.ndarray) -> float:
    """El diferido de varios eventos cercanos, en barriles (la misma cuenta que `_diferido_evento`)."""
    if np.isnan(c):
        return 0.0
    val = (c * base - tasa) * dias * BBL_M3
    val = val[~np.isnan(val)]
    return float(val.sum()) if val.size else 0.0


def diferido_h3(C: dict, reps=REPS_BOOT, semilla=SEMILLA_ALCANCE) -> list[tuple]:
    """El recalculo descriptivo de H-R3: la brecha del mes 1 y el diferido de los meses 0 a 6.

    Solo tiene sentido si el control de superficie salio contaminado. Los cercanos son todos los eventos
    de banda 0 (no necesitan rama medida) y los controles son el de superficie usual (banda 2) y el lateral
    limpio (m_min de 2.000 m o mas, que no sea de banda 0). El IC sale de un solo bootstrap por bloques de
    5 km del universo entero, con las mismas remuestras para las cuatro cantidades.
    """
    D = C["D"]
    ev = muestra_todos(C, MESES_DIFERIDO)
    padre, mes, banda, m_min = ev["padre"], ev["mes"], ev["banda"], ev["m_min"]
    idx = ev["idx"]
    ks = list(MESES_DIFERIDO)
    cerca = banda == 0
    controles = {"usual": banda == 2,
                 "lateral_limpio": (~np.isnan(m_min)) & (m_min >= CONTROL_RAMA_M) & (banda != 0)}
    base = placebo._media(D, padre, mes, *placebo.BASE_ORIGINAL)
    max_mes = int(np.nanmax(mes)) + max(ks) + 1 if len(mes) else 1
    dias_tabla = np.array([_dias_mes(j) for j in range(max_mes + 1)], dtype=float)
    tasa = {}
    for k in ks:
        col = mes + k + placebo.PAD
        val = np.where(col < D["tasa"].shape[1], D["tasa"][padre, np.clip(col, 0, D["tasa"].shape[1] - 1)],
                       np.nan)
        tasa[k] = val
    dias = {k: dias_tabla[mes + k] for k in ks}

    def _una(i: np.ndarray) -> dict[str, tuple[float, float]]:
        res = {}
        for nombre, mask in controles.items():
            ctrl = i[mask[i]]
            cerca_i = i[cerca[i]]
            c = {k: _med(idx[k][ctrl]) for k in ks}
            brecha = _med(idx[1][cerca_i]) - _med(idx[1][ctrl])
            dif = 0.0
            for k in ks:
                dif += _diferido_vec(base[cerca_i], tasa[k][cerca_i], c[k], dias[k][cerca_i])
            res[nombre] = (brecha, dif)
        return res

    punto = _una(np.arange(len(padre)))
    grupos = _clusters(ev["bloque"])
    rng = np.random.default_rng(semilla)
    draws: dict[str, dict[str, list[float]]] = {n: {"brecha": [], "diferido": []} for n in controles}
    for _ in range(reps):
        r = _una(_remuestra(rng, grupos))
        for nombre in controles:
            draws[nombre]["brecha"].append(r[nombre][0])
            draws[nombre]["diferido"].append(r[nombre][1])
    filas = []
    for nombre in ("usual", "lateral_limpio"):
        mask = controles[nombre]
        brecha, dif = punto[nombre]
        db = np.asarray(draws[nombre]["brecha"], dtype=float)
        dd = np.asarray(draws[nombre]["diferido"], dtype=float)
        bb, ba = (float(x) for x in np.percentile(db[~np.isnan(db)], [2.5, 97.5])) if (~np.isnan(db)).any() \
            else (float("nan"), float("nan"))
        db2, da2 = (float(x) for x in np.percentile(dd[~np.isnan(dd)], [2.5, 97.5])) if (~np.isnan(dd)).any() \
            else (float("nan"), float("nan"))
        filas.append((nombre, int((cerca & ~np.isnan(idx[1])).sum()), int((mask & ~np.isnan(idx[1])).sum()),
                      brecha, bb, ba, dif, db2, da2))
    return filas


# ------------------------------------------------------------------ tablas

def _ns(nombre: str, c: dict) -> tuple:
    """Las dos cuentas que van en la fila de un estadistico."""
    if nombre.startswith("brecha_"):
        return c["n_" + nombre[len("brecha_"):]], c["n_control"]
    if nombre == "A":
        return c["n_cerca"], c["n_control"]
    if nombre == "B":
        return c["n_sup_cerca"], c["n_sup_control"]
    if nombre == "A_menos_B":
        return None, None
    return c["n_contaminado"], c["n_limpio"]


def calcular(C: dict, reps=REPS_BOOT) -> dict[str, list[tuple]]:
    """Las cuatro tablas de la pagina, listas para escribir."""
    s = muestra(C)
    v = s["idx"][K_TITULAR]
    est = bootstrap(v, s["m_min"], s["banda"], s["bloque"], reps=reps)
    cnt = conteos(v, s["m_min"], s["banda"])
    bloques = est["_bloques"]
    ver1, alcance = veredicto_r1(est, cnt, bloques)
    ver2 = veredicto_r2(est, cnt)
    ver3 = veredicto_r3(est, cnt)

    modelos = [("principal", K_TITULAR, est, cnt)]
    modelos.append(("s1", K_TITULAR, bootstrap(v, s["m_min_s1"], s["banda"], s["bloque"], reps=reps),
                    conteos(v, s["m_min_s1"], s["banda"])))
    s2 = muestra(C, base=BASE_S2, ks=(K_TITULAR, K_PREVIO))
    for k in (K_TITULAR, K_PREVIO):
        modelos.append(("s2", k, bootstrap(s2["idx"][k], s2["m_min"], s2["banda"], s2["bloque"], reps=reps),
                        conteos(s2["idx"][k], s2["m_min"], s2["banda"])))
    keep = s["anio"] <= ANIO_S3
    modelos.append(("s3", K_TITULAR, bootstrap(v[keep], s["m_min"][keep], s["banda"][keep], s["bloque"][keep], reps=reps),
                    conteos(v[keep], s["m_min"][keep], s["banda"][keep])))

    filas = []
    for modelo, k, e, c in modelos:
        for nombre in NOMBRES_EST:
            n, n_ref = _ns(nombre, c)
            filas.append((modelo, k, nombre, e[nombre]["valor"], e[nombre]["ic_bajo"], e[nombre]["ic_alto"],
                          e[nombre]["descartadas"], n, n_ref))
    eventos = int(len(s["m_min"]))
    prueba = [("H-R1", ver1, alcance, eventos, bloques, reps, int(s["n_marco"])),
              ("H-R2", ver2, None, eventos, bloques, reps, int(s["n_marco"])),
              ("H-R3", ver3, None, eventos, bloques, reps, int(s["n_marco"]))]
    diferido = diferido_h3(C, reps=reps) if ver3 == "control contaminado" else []
    return {"mart_alcance_rama": filas, "mart_alcance_rama_prueba": prueba,
            "mart_alcance_rama_anio": por_anio(s), "mart_alcance_rama_diferido": diferido}


def escribir(con, t: dict[str, list[tuple]]) -> None:
    """Una llamada por mart, con el nombre escrito (lo que lee pipeline.linaje)."""
    _escribir(con, "mart_alcance_rama", COLS_ALCANCE, t["mart_alcance_rama"])
    _escribir(con, "mart_alcance_rama_prueba", COLS_PRUEBA, t["mart_alcance_rama_prueba"])
    _escribir(con, "mart_alcance_rama_anio", COLS_ANIO, t["mart_alcance_rama_anio"])
    _escribir(con, "mart_alcance_rama_diferido", COLS_DIFERIDO, t["mart_alcance_rama_diferido"])


def marts(con) -> dict | None:
    """Las cuatro tablas de la pagina (None si no se corrio todavia)."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?",
                       ["mart_alcance_rama_prueba"]).fetchone()[0]:
        return None
    return {"alcance": con.execute("select * from mart_alcance_rama order by modelo, k, estadistico").fetchall(),
            "prueba": con.execute("select * from mart_alcance_rama_prueba order by prueba").fetchall(),
            "anio": con.execute("select * from mart_alcance_rama_anio order by anio").fetchall(),
            "diferido": con.execute("select * from mart_alcance_rama_diferido").fetchall()}


def main(path=DATA / "warehouse.duckdb", reps=REPS_BOOT) -> None:
    """Corre la pagina entera sobre el warehouse y escribe los marts."""
    con = duckdb.connect(str(path))
    try:
        C = cargar(con)
        t = calcular(C, reps=reps)
        escribir(con, t)
    finally:
        con.close()
    for prueba, veredicto, alcance, eventos, n_bloques, _reps, _marco in t["mart_alcance_rama_prueba"]:
        if alcance is not None:
            print(f"[alcance_rama] {prueba}: {veredicto} (alcance {alcance:.0f} m), "
                  f"eventos {eventos}, bloques {n_bloques}")
        else:
            print(f"[alcance_rama] {prueba}: {veredicto}, eventos {eventos}, bloques {n_bloques}")


# ------------------------------------------------------------------ la pagina de la wiki

SHA_REGLA = "76d9831"                   # el commit que fijo la regla antes de calcular ninguna cifra
ETIQUETAS_BANDA = ("0 a 300 m", "300 a 600 m", "600 a 1.000 m", "1.000 a 2.000 m")
TITULO = "Alcance y dilución de la huella medidos entre ramas"


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and np.isnan(x))


def _ic(lo, hi) -> str:
    return f"{_pts(lo)} a {_pts(hi)}"


def _entero(x) -> str:
    return "n/d" if x is None else _g(x, 0)


def _porcentaje(num, den) -> str:
    return "n/d" if not den else _g(100 * num / den, 0)


def _cobertura(con) -> tuple[str, str, str] | None:
    """El porcentaje de hijos horizontales con la rama medida: 2016 a 2023, 2024 y 2025 (mart_trayectoria_cobertura)."""
    if not con.execute("select count(*) from information_schema.tables where table_name = 'mart_trayectoria_cobertura'").fetchone()[0]:
        return None

    def parte(desde: int, hasta: int) -> str:
        h, m = con.execute("select sum(horizontales), sum(horizontales_medidos) from mart_trayectoria_cobertura "
                           "where nivel = 'hijo' and anio between ? and ?", [desde, hasta]).fetchone()
        return _porcentaje(m or 0, h or 0)
    return parte(2016, ANIO_S3), parte(2024, 2024), parte(2025, 2025)


def _rango_estudio(con) -> str:
    """El rango publicado del diferido (mart_diferido_rango: con descuento de la previa y el total original), en millones."""
    if con.execute("select count(*) from information_schema.tables where table_name = 'mart_diferido_rango'").fetchone()[0]:
        d = dict(con.execute("select variante, diferido_bbl from mart_diferido_rango").fetchall())
        if "neto_previa" in d and "original" in d:
            return f"el rango del estudio ({_g(d['neto_previa'] / 1e6, 1)} a {_g(d['original'] / 1e6, 1)} millones de barriles)"
    return "el rango del estudio (`wiki/hallazgos/diferido.md`)"


def pagina_alcance_rama(con) -> str:
    """Página de la wiki a partir de los marts (solo lee). Cada frase que depende de un veredicto sale de la palabra guardada."""
    M = marts(con)
    if M is None:
        raise SystemExit("falta correr `uv run python -m pipeline.alcance_rama` antes de escribir la página")
    E = {(r[0], r[1], r[2]): r[3:] for r in M["alcance"]}        # (valor, ic_bajo, ic_alto, descartadas, n, n_ref)
    P = {r[0]: r[1:] for r in M["prueba"]}                       # (veredicto, alcance_m, eventos, bloques, reps, eventos_marco)
    anios = {r[0]: r[1:] for r in M["anio"]}
    dif = {r[0]: r[1:] for r in M["diferido"]}

    def e(modelo: str, est: str, k: int = K_TITULAR) -> tuple:
        return E.get((modelo, k, est), (None,) * 6)

    def celda(modelo: str, est: str, k: int = K_TITULAR) -> str:
        v, lo, hi = e(modelo, est, k)[:3]
        return f"{_pts(v)} ({_ic(lo, hi)})" if _ok(v) else "n/d"

    v1, alcance, eventos, n_bloques, reps, marco = P["H-R1"]
    v2 = P["H-R2"][0]
    v3 = P["H-R3"][0]
    n_banda = [e("principal", nombre)[4] for nombre in NOMBRES_BANDA]
    n_control = e("principal", "brecha_0_300")[5]
    cob = _cobertura(con)
    tot = anios.get(0)
    hasta_s3 = sum(a[0] for z, a in anios.items() if 0 < z <= ANIO_S3)
    muestra = (f"- Muestra: Son {_entero(eventos)} eventos (el {_porcentaje(eventos, marco)}% de los {_entero(marco)} eventos del estudio) "
               f"con la rama del hijo y la del padre medidas, en {_entero(n_bloques)} bloques de 5 km.")
    if cob and tot and tot[0]:
        muestra += (f" Las trayectorias laterales cubren el {cob[0]}% de los hijos horizontales fracturados de 2016 a 2023 "
                    f"pero solo el {cob[1]}% de los de 2024 y el {cob[2]}% de los de 2025, así que la muestra es sobre todo de "
                    f"2016 a 2023: el {_porcentaje(hasta_s3, tot[0])}% de los eventos son de hijos fracturados hasta 2023.")

    # H-R1
    linea1 = f"- Alcance (H-R1): **{v1}**."
    if v1 == "alcance medido" and alcance is not None:
        linea1 += (f" La brecha del mes 1 llega hasta {_g(alcance, 0)} m entre ramas (borde superior de la última banda cuyo "
                   "intervalo excluye cero) y no se distingue de cero entre 1.000 y 2.000 m.")
    elif v1 == "gradiente":
        linea1 += (" La brecha sigue distinta de cero entre 1.000 y 2.000 m: el alcance es de por lo menos 2.000 m entre ramas "
                   "y no se midió el borde.")
    elif v1 == "sin muestra":
        linea1 += (f" Los datos no deciden el alcance: las bandas tienen {_entero(n_banda[0])}, {_entero(n_banda[1])}, "
                   f"{_entero(n_banda[2])} y {_entero(n_banda[3])} eventos con el índice del mes 1 medido y el control lateral "
                   f"{_entero(n_control)} (se piden por lo menos {N_MIN} cada uno), en {_entero(n_bloques)} bloques de 5 km "
                   f"(se piden por lo menos {MIN_BLOQUES}).")
    else:
        linea1 += " Los datos no deciden el alcance: ninguna de las condiciones de la regla se cumple."
    v0, lo0, hi0 = e("principal", "brecha_0_300")[:3]
    if v1 != "sin muestra" and _ok(v0):
        linea1 += f" A menos de 300 m la brecha es {_pts(v0)} puntos (IC 95%: {_ic(lo0, hi0)})."

    # H-R2
    a_v, a_lo, a_hi, _d, a_n, a_nref = e("principal", "A")
    b_v, _b_lo, _b_hi, _d, b_n, b_nref = e("principal", "B")
    d_v, d_lo, d_hi = e("principal", "A_menos_B")[:3]
    linea2 = f"- Dilución (H-R2): **{v2}**."
    if v2 == "sin muestra":
        linea2 += (f" Los datos no deciden la dilución: los cuatro grupos tienen {_entero(a_n)}, {_entero(a_nref)}, "
                   f"{_entero(b_n)} y {_entero(b_nref)} eventos con el índice medido (se piden por lo menos {N_MIN} cada uno).")
    else:
        cierre = (" se separan" if v2 == "la distancia de superficie diluye la huella" else " no se distinguen")
        linea2 += (f" Medido entre ramas, la brecha de los padres a menos de 600 m (A, {_pts(a_v)} puntos) y la medida por "
                   f"superficie con los mismos eventos (B, {_pts(b_v)} puntos){cierre}: A menos B es {_pts(d_v)} puntos "
                   f"(IC 95%: {_ic(d_lo, d_hi)}).")
        if v2 == "la distancia de superficie diluye la huella":
            linea2 += (" A es más negativa que B y el intervalo de la diferencia excluye cero: la distancia de superficie "
                       "subestima la brecha entre ramas.")
        else:
            linea2 += " Medir entre ramas no cambia la lectura."

    # H-R3
    c_v, c_lo, c_hi, _d, c_n, c_nref = e("principal", "C_menos_L")
    linea3 = f"- Control (H-R3): **{v3}**."
    if v3 == "sin muestra":
        linea3 += (f" Los dos grupos de control tienen {_entero(c_n)} y {_entero(c_nref)} eventos con el índice medido "
                   f"(se piden por lo menos {N_MIN} cada uno).")
    elif v3 == "control contaminado" and _ok(c_v):
        linea3 += (f" Los controles de 2 a 5 km con la rama a menos de 1.000 m de la del hijo rinden {_pts(-c_v)} puntos menos "
                   f"(IC 95% de la diferencia: {_ic(c_lo, c_hi)}) que los de 2.000 m o más ({_entero(c_n)} y {_entero(c_nref)} eventos).")
    elif _ok(c_v):
        linea3 += (f" Medido entre ramas, el control de 2 a 5 km no se ensucia: la diferencia entre los de rama a menos de 1.000 m y "
                   f"los de 2.000 m o más es {_pts(c_v)} puntos (IC 95%: {_ic(c_lo, c_hi)}).")
    us, la = dif.get("usual"), dif.get("lateral_limpio")
    if v3 == "control contaminado" and us and la and all(_ok(x) for x in (us[2], us[3], us[4], la[2], la[3], la[4])):
        base = (f" Contra el control lateral limpio la brecha del mes 1 es {_pts(la[2])} puntos (IC 95%: {_ic(la[3], la[4])}) y "
                f"contra el control de superficie {_pts(us[2])} (IC 95%: {_ic(us[3], us[4])}): ")
        if la[3] <= us[4] and us[3] <= la[4]:
            linea3 += base + ("los intervalos se solapan y no se ve que el control de superficie subestime la brecha.")
        elif la[2] < us[2]:
            linea3 += base + "el control de superficie subestima la brecha."
        else:
            linea3 += base + "el control de superficie no subestima la brecha."
        if all(_ok(x) for x in (us[5], us[6], us[7], la[5], la[6], la[7])):
            if la[6] <= us[7] and us[6] <= la[7]:
                linea3 += (" La regla esperaba que el control de superficie subestimara el diferido; el recálculo descriptivo de la tabla "
                           "de más abajo no lo muestra: los intervalos del diferido de los meses 0 a 6 se solapan.")
            elif la[5] > us[5]:
                linea3 += " En el recálculo descriptivo del diferido de los meses 0 a 6 el control de superficie lo subestima, como esperaba la regla."
            else:
                linea3 += " En el recálculo descriptivo del diferido de los meses 0 a 6 el control de superficie no lo subestima, al revés de lo que esperaba la regla."

    # previa
    p_v, p_lo, p_hi = e("s2", "brecha_0_300", K_PREVIO)[:3]
    if _ok(p_v):
        lado = "abajo" if p_v < 0 else "arriba"
        linea4 = (f"- Previa (descriptivo): un mes antes de la fractura (base de los meses -6 a -4) la banda de 0 a 300 m ya estaba "
                  f"{_pts(abs(p_v))} puntos {lado} del control lateral (IC 95% de la brecha: {_ic(p_lo, p_hi)}).")
        if p_v < 0:
            linea4 += " Parte de la brecha existía antes de la fractura, y el alcance se lee con eso en cuenta."
    else:
        linea4 = "- Previa (descriptivo): no hay brecha previa medida en la banda de 0 a 300 m."

    L = [f"# {TITULO}", "",
         "Hasta acá, la distancia entre un hijo y un padre es la de sus bocas en superficie. La página de trayectorias "
         "(`trayectorias.md`) mostró que esa distancia clasifica mal los pares: hay pares cercanos en superficie con las ramas lejos "
         "y pares de control con las ramas cerca. Esta página repite el alcance y la dilución de la huella con la distancia entre "
         "ramas: la menor distancia en planta entre la rama del hijo y la del padre. La regla se fijó antes de calcular ninguna cifra, "
         f"en el commit {SHA_REGLA}. Se publican todos los resultados, favorables o no.", "",
         "Esta página la escribe `python -m pipeline.wiki` con `pipeline.alcance_rama.pagina_alcance_rama`. No se edita a mano.", "",
         "## Lectura", "", muestra, linea1, linea2, linea3, linea4,
         "- Nada de esto cambia los 19 a 23 puntos del estudio, que siguen en distancia de superficie.", ""]

    L += ["## H-R1: la brecha del mes 1 por banda de distancia entre ramas", "",
          "| Banda | Eventos | Brecha (puntos) | IC 95% | Un mes antes (puntos, IC; base de los meses -6 a -4) |",
          "|---|---|---|---|---|"]
    for etq, nombre in zip(ETIQUETAS_BANDA, NOMBRES_BANDA):
        v, lo, hi, _d, n, _r = e("principal", nombre)
        L.append(f"| {etq} | {_entero(n)} | {_pts(v)} | {_ic(lo, hi)} | {celda('s2', nombre, K_PREVIO)} |")
    L += [f"| Control lateral (2.000 m o más) | {_entero(n_control)} | referencia | referencia | referencia |", "",
          "Brecha = mediana del índice del mes 1 de la banda menos la del control lateral, en puntos de índice.", ""]

    L += ["## H-R2: la dilución", "",
          "| Medida | Padres cercanos | Eventos | Control | Eventos | Brecha | IC 95% |", "|---|---|---|---|---|---|---|"]
    for etq, cerca, control, est in (("A (entre ramas)", "menos de 600 m entre ramas", "control lateral (2.000 m o más)", "A"),
                                     ("B (superficie)", "menos de 1 km en superficie", "2 a 5 km en superficie", "B")):
        v, lo, hi, _d, n, nr = e("principal", est)
        L.append(f"| {etq} | {cerca} | {_entero(n)} | {control} | {_entero(nr)} | {_pts(v)} | {_ic(lo, hi)} |")
    L += [f"| A menos B | n/d | n/d | n/d | n/d | {_pts(d_v)} | {_ic(d_lo, d_hi)} |", ""]

    L += ["## H-R3: el control de superficie", "", "| Grupo | Eventos | Descripción |", "|---|---|---|",
          f"| Contaminado | {_entero(c_n)} | control de superficie (2 a 5 km) con la rama a menos de 1.000 m de la del hijo |",
          f"| Limpio | {_entero(c_nref)} | control de superficie (2 a 5 km) con la rama a 2.000 m o más de la del hijo |",
          f"| Diferencia | n/d | contaminado menos limpio: {_pts(c_v)} puntos (IC 95%: {_ic(c_lo, c_hi)}) |", ""]
    if dif:
        L += ["| Control | Cercanos | Controles | Brecha del mes 1 (puntos) | IC 95% | Diferido de los meses 0 a 6 (millones de barriles) | IC 95% |",
              "|---|---|---|---|---|---|---|"]
        for clave, etq in (("usual", "control de superficie usual (2 a 5 km)"), ("lateral_limpio", "control lateral limpio")):
            r = dif.get(clave)
            if r:
                L.append(f"| {etq} | {_entero(r[0])} | {_entero(r[1])} | {_pts(r[2])} | {_ic(r[3], r[4])} | "
                         f"{_g(r[5] / 1e6, 1)} | {_g(r[6] / 1e6, 1)} a {_g(r[7] / 1e6, 1)} |")
        L += ["", f"Es un recálculo descriptivo y no es {_rango_estudio(con)}: suma los meses 0 a 6 de cada evento cercano contra "
                  "la mediana de todos los controles, sin grupos de edad, sin descontar la brecha previa y sin quitar los meses "
                  "repetidos, así que da un total más alto; sirve para comparar un control con el otro y no como el total "
                  "del estudio.", ""]

    L += ["## Sensibilidades (no cambian ningún veredicto)", "",
          "| Cantidad | Principal | S1 (hijo más cercano por rama) | S2 (base de los meses -6 a -4) | S3 (hijos fracturados hasta 2023) |",
          "|---|---|---|---|---|"]
    filas = [(f"Brecha de {etq}", nombre) for etq, nombre in zip(ETIQUETAS_BANDA, NOMBRES_BANDA)]
    filas += [("A", "A"), ("B", "B"), ("A menos B", "A_menos_B")]
    for etq, est in filas:
        L.append(f"| {etq} | " + " | ".join(celda(m, est) for m in ("principal", "s1", "s2", "s3")) + " |")
    L += ["", "- S1: la distancia del evento es la menor distancia entre ramas sobre todos los hijos medidos de ese padre y de ese "
              "mes de fractura, no la del hijo más cercano en superficie; los mismos eventos, las mismas bandas y el mismo control.",
          "- S2: lo mismo que el modelo principal con la base de los meses -6 a -4 en lugar de la de los meses -3 a -1.",
          f"- S3: el modelo principal con los eventos cuyo hijo se fracturó en {ANIO_S3} o antes, la parte bien cubierta de la fuente.", ""]

    L += ["## Eventos por año del hijo", "",
          "| Año | Eventos | 0 a 300 m | 300 a 600 m | 600 a 1.000 m | 1.000 a 2.000 m | Control lateral |", "|---|---|---|---|---|---|---|"]
    for anio in sorted(anios):
        if anio:
            L.append(f"| {anio} | " + " | ".join(_entero(x) for x in anios[anio]) + " |")
    if tot:
        L.append("| Total | " + " | ".join(_entero(x) for x in tot) + " |")
    L += ["", "Eventos son los de la muestra de ese año; las bandas cuentan los que tienen el índice del mes 1 medido.", ""]

    L += ["## Cómo se mide", "",
          "- Los eventos son los del estudio: un padre y el mes de fractura de su hijo más cercano en superficie, que fija el mes y el hijo.",
          "- La muestra son los eventos cuyo par (hijo, padre) está en `mart_trayectoria_par`: con la rama del hijo y la del padre medidas.",
          "- La distancia es la menor distancia entre las dos ramas en planta (`m_min`), en metros.",
          "- La brecha es la mediana del índice del grupo menos la mediana del índice del control lateral (`m_min` de 2.000 m o más); "
          "el índice es el caudal del mes 1 sobre la base de los meses -3 a -1.",
          f"- Los intervalos son bootstrap de percentiles 95% por bloques espaciales de 5 km ({_entero(reps)} remuestras, "
          "las mismas para todas las cantidades).",
          "- El veredicto sale solo del modelo principal. Las bandas incluyen el extremo de abajo y dejan afuera el de arriba.", ""]

    L += ["## Qué no es", "",
          "- Es una huella medida: la misma brecha del estudio con otra distancia, sin afirmación causal y sin ajuste por comparaciones múltiples.",
          "- La muestra es sobre todo de 2016 a 2023: no dice nada de 2024 en adelante.",
          "- El control lateral solo sabe de las ramas medidas: un padre con un hijo de rama no publicada puede estar golpeado igual.",
          "- Solo hay pares con las bocas a menos de 5 km: un padre con la rama cerca pero la boca lejos no está.",
          "- La distancia entre ramas es en planta: no tiene la cota de cada punto.",
          "- Un alcance medido es el borde de las bandas probadas (300, 600, 1.000 y 2.000 m), no un borde exacto.", ""]

    L += ["## Reproducir", "",
          "1. `uv run python -m pipeline.alcance_rama` (necesita `pipeline.trayectorias` antes).",
          "2. `uv run python -m pipeline.wiki`", "3. `uv run python -m pipeline.claims`", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
