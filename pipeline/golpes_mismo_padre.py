"""Golpes en el mismo mes, con el padre como su propio control: si agrupar hijos le cuesta menos al padre, comparando cada
padre consigo mismo.

Se corre despues de pipeline.golpes_mismo_mes:  uv run python -m pipeline.golpes_mismo_padre
Colorado (prueba confirmatoria):                uv run python -m pipeline.golpes_mismo_padre --cuenca colorado

Para que sirve. pipeline.golpes_mismo_mes (PR #83) no pudo decidir si juntar varios hijos en un mes le cuesta al padre menos
que repartirlos, porque la perdida de un mes de golpe varia muchisimo entre padres (en Vaca Muerta, desvio de 97,8 dias de
base contra una media de 8,3): el costo fijo a y el costo por hijo b salian con intervalos que incluian el cero. Aqui cada
padre se compara con el mismo: un padre con dos o mas meses de golpe aislados y distinta cantidad de hijos en cada uno
aporta la diferencia de su perdida entre un mes y otro, y lo que es propio del padre (su roca, su caudal, su operador, su
terminacion) queda fuera de b. Es la segunda pieza del optimizador de calendario (U6a de la fase 4; la unidad siguiente,
U6b, son las matrices de costo, el optimizador y el backtest).

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no. Un "no firme" o un "sin
muestra" es un resultado terminado: no se rediseña la regla para evitarlo.

Que se habia mirado antes de fijarla
- Todo lo publicado de pipeline.golpes_mismo_mes (PR #83), en las dos cuencas: el modelo agrupado P = a + b k con
  controles (Vaca Muerta: a = 23,4 y b = -3,8 dias de base, con intervalos que incluyen el cero; Colorado: a = 33,8 y
  b = -2,5), el veredicto "sin perdida medible" y la dispersion de la perdida. Por eso en Vaca Muerta la prueba es de REGLA
  INFORMADA, y en Colorado, donde esos numeros agrupados tambien estaban publicados, se corre la misma regla despues de
  Vaca Muerta y sin tocarla (confirmatoria en el sentido de #81 y #83: no hay un segundo ajuste de la regla).
- NO se habia calculado ninguna cantidad de esta prueba: ni cuantos padres tienen dos o mas meses de golpe aislados, ni
  cuantos de ellos con distinta k, ni ninguna perdida dentro de un padre. El tamano de la muestra restringida se ve por
  primera vez cuando corre el modulo, y puede ser "sin muestra".
- Los datos de produccion se actualizan antes de correr esta prueba (refresco de la fase 4, otra unidad): la prueba corre
  sobre el warehouse que haya entonces, y la pagina da la fecha del ultimo mes de produccion.

Que se reutiliza (de pipeline.golpes_mismo_mes, sin copiar)
- La definicion del evento y de su perdida, tal cual: placebo.marco con ks=(1,) y base BASE; k, k12 y S; el aislamiento
  (ningun hijo a menos de KM_AISLADO en los MESES_AISLADO meses de cada lado); la ventana completa VENTANA; el indice
  acotado a [0, TOPE_INDICE]; el indice de control (mediana de los controles con ventana completa); la perdida P en dias
  de produccion de base y el volumen V = P por el caudal de base; los cargadores de pipeline.dias_perdidos, para Vaca Muerta
  y para Colorado, con las adaptaciones de Colorado de #83. La muestra de partida es la principal de #83: cercanos (hijo
  mas cercano a menos de KM_CERCA) aislados con la ventana completa.
- Un mes de golpe de un padre es un evento de esa muestra; k es la cantidad de hijos a menos de KM_CERCA fracturados en
  ese mes. Dos meses de golpe aislados de un mismo padre estan al menos a 7 meses.

Muestra de esta prueba
- Padres de la muestra de partida con al menos MIN_MESES_PADRE (2) meses de golpe y al menos MIN_K_PADRE (2) valores
  distintos de k entre ellos. Entran todos los meses de golpe aislados de esos padres. Sin ellos no hay variacion de k
  dentro del padre y b no se identifica.
- "Padre" es el pozo padre (int_pozo_ubicacion.pozo_id). El pad del padre es int_pozo_ubicacion.pad_id del padre; si falta,
  el pozo es su propio pad (como pipeline.diferido para el pad hijo). Esta columna no estaba en las matrices D de los
  cargadores: el modulo la agrega con una consulta propia, en el orden de pozo_id de int_pozo_ubicacion (el de D["primer"]),
  y no cambia ninguna matriz existente.

Modelo (minimos cuadrados con efecto fijo de padre)
- P_it = alpha_i + b k_it + gamma' X_it + e_it, con i el padre y t su mes de golpe. X: efectos fijos del grupo de edad del
  padre al momento del golpe (EDADES de pipeline.dias_perdidos: 6 a 11, 12 a 23, 24 a 47, 48 o mas meses; en Colorado, el
  grupo propio de primer petroleo censurado) y del ano del golpe. Sin otros controles en la prueba principal: lo propio del
  padre lo absorbe alpha_i.
- Se estima por la transformacion intra-padre (restar a P, k y X la media de los meses del padre), minimos cuadrados
  simples sin pesos, cada mes de golpe con el mismo peso. Una columna de X que queda constante despues de la transformacion
  no aporta; la solucion es la de minima norma (numpy.linalg.lstsq).
- a es la media de alpha_i sobre los padres de la muestra, cada padre con el mismo peso, y los controles se centran en la
  media (entre padres) de las medias de cada padre. Eso da  a = media_i(P_i) - b media_i(k_i), con P_i y k_i las medias
  de cada padre; a no depende de que categoria de edad o de ano sea la de referencia. a es lo que cuesta un mes de golpe
  sin importar cuantos hijos traiga, y b lo que cuesta cada hijo; un mes con un solo hijo cuesta a + b; juntos, k hijos
  cuestan a + b k; separados, k (a + b). phi = a / (a + b) es la parte fija del costo de un mes con un solo hijo, y
  rho_k = (a + b k) / (k (a + b)) es el costo de k hijos juntos sobre el de los mismos k separados.
- Estadistico del veredicto: phi.
- IC 95% de percentiles. El conglomerado del bootstrap es el pad del padre (todos los padres de un pad, con todos sus
  meses de golpe, se mueven juntos), REPS_BOOT repeticiones, semilla SEMILLA_PADRE. Cada pad remuestreado cuenta como un
  conglomerado nuevo aunque salga varias veces: sus padres se tratan como padres distintos en la transformacion intra-padre
  (no se juntan por pozo_id). Esta prueba usa los pads del padre y no el bootstrap espacial de 5 km de pipeline.bloques ni
  los pads hijo de #83: la dependencia que importa aqui es la de los padres de un mismo pad, que comparten hijos. Las
  repeticiones con a + b <= 0 se descartan para phi y rho_k, y se cuentan; tambien se cuentan las repeticiones con b < 0.
- Veredicto, en este orden (la misma regla que #83, con la muestra de padres):
  1. "sin muestra": menos de PADRES_MIN (150) padres o de MESES_MIN (400) meses de golpe en la muestra restringida. La
     pagina da los conteos, y en ese caso no se publica ningun otro veredicto.
  2. "sin perdida medible": el limite bajo del IC de a + b es menor o igual a cero.
  3. "agrupar ahorra": el limite bajo del IC de phi es mayor que cero y phi es de al menos UMBRAL_FIJO (0,25).
  4. "agrupar no ahorra": el limite alto del IC de phi es menor que UMBRAL_FIJO.
  5. "no firme": en otro caso. La pagina da el IC y dice que el dato no decide.
- Se publican a, b, a + b, phi y rho_k para cada k de KS_RHO con su IC, el error de phi (desvio de las repeticiones), las
  repeticiones descartadas, la fraccion de repeticiones con b < 0 y los conteos de la muestra (padres, pads del padre,
  meses de golpe, valores de k, meses por padre).

Sensibilidades (se publican; no cambian el veredicto)
- S1, volumen: el mismo modelo con V (m3) en lugar de P; da a, b y phi en m3.
- S2, mas controles: el modelo principal con tres controles mas de #83 que cambian de un golpe a otro del mismo padre:
  k12 (hijos del mismo mes entre KM_CERCA y KM_K12), la suma S de las desviaciones de distancia de los hijos y el logaritmo
  del caudal de base de cada golpe.
- Comparacion con #83 (descriptiva): el modelo agrupado de #83 en la misma muestra de padres, sin efecto fijo de padre
  (a, b, a + b y phi con los controles de #83), para que se vea cuanto cambia b al comparar a cada padre consigo mismo.
- Cualquier otra cosa que se agregue despues de ver los numeros se marca "agregado despues de ver" y no cambia el
  veredicto.

Colorado (confirmatoria, con esta misma regla)
- Las adaptaciones de pipeline.dias_perdidos.cargar_cuenca tal cual (como en #83) y el mismo umbral de muestra. S1 y S2 se
  calculan igual. Tablas en el warehouse de Vaca Muerta con el nombre de la cuenca: mart_golpes_mismo_padre_colorado y
  mart_golpes_mismo_padre_colorado_prueba.

Que cambia con cada veredicto (en la pagina y en la unidad siguiente)
- "agrupar ahorra" en Vaca Muerta: el optimizador usa costo fijo mas costo por hijo (a y b) por padre y mes, con b acotado
  a 0 o mas antes de usarlo.
- "agrupar no ahorra": costo aditivo por hijo.
- "no firme", "sin muestra" o "sin perdida medible": el optimizador corre los dos casos y publica el arrepentimiento con
  cada uno; la pagina dice que el dato no decide y da los numeros. Con "sin muestra", el costo del ultimo modelo agrupado
  de #83 sigue siendo lo unico publicado.

Que NO prueba
- Con dato mensual "el mismo mes" no es "al mismo tiempo".
- Los padres con dos golpes aislados de distinta k no son todos los padres: son los que vivieron mas de un desarrollo
  separado, y su k cambia porque cambia el pad hijo, su tamano y su epoca. El efecto fijo de padre absorbe lo estable del
  padre, no lo que cambia entre un golpe y otro (la edad y el ano entran como controles; el diseno del pad hijo, no).
- La identificacion viene solo de los padres con distinta k; un padre cuyos golpes tienen la misma k no aporta a b.
- La perdida es volumen diferido contra la trayectoria de los controles en la ventana, no dice que se pierda.
- Solo el lado del padre.
"""
from __future__ import annotations

import argparse

import duckdb
import numpy as np

from pipeline import dias_perdidos
from pipeline import golpes_mismo_mes as gm
from pipeline.costo import _clusters, _escribir
from pipeline.cuencas import COLORADO, Cuenca, cuenca as _cuenca
from pipeline.dias_perdidos import _dummies
from pipeline.golpes_mismo_mes import _ict, _num, _val
from pipeline.ingest import DATA
from pipeline.placebo import REPS_BOOT, _g

# Heredadas de pipeline.golpes_mismo_mes, sin cambiarlas
BASE = gm.BASE                    # meses de la base del caudal (-6 a -4)
VENTANA = gm.VENTANA              # meses de la perdida del evento (-1 a 6)
KM_CERCA = gm.KM_CERCA            # km: hijos que cuentan en k
KM_K12 = gm.KM_K12                # km: hijos del mismo mes entre KM_CERCA y esta distancia (control de S2)
KM_AISLADO = gm.KM_AISLADO        # km: radio del aislamiento
MESES_AISLADO = gm.MESES_AISLADO  # meses a cada lado del evento sin otros hijos dentro del radio
TOPE_INDICE = gm.TOPE_INDICE      # el indice del padre se acota a [0, TOPE_INDICE]
UMBRAL_FIJO = gm.UMBRAL_FIJO      # phi minimo para "agrupar ahorra"; techo de phi para "agrupar no ahorra" (0,25)
KS_RHO = gm.KS_RHO                # k en las que se publica rho_k
VEREDICTOS = gm.VEREDICTOS        # las palabras del veredicto, las de #83

REPS = REPS_BOOT                  # repeticiones del bootstrap, las de todo el estudio

# Propias de esta prueba
MIN_MESES_PADRE = 2               # meses de golpe aislados de un padre para entrar en la muestra
MIN_K_PADRE = 2                   # valores distintos de k entre los meses de golpe de ese padre
PADRES_MIN = 150                  # padres de la muestra restringida para decidir
MESES_MIN = 400                   # meses de golpe de la muestra restringida para decidir
SEMILLA_PADRE = gm.SEMILLA + 80   # semilla del bootstrap por pads del padre (la de #83 es SEMILLA + 70)

# ------------------------------------------------------------------ helpers

EXTRA_S2 = ("k12", "S", "log_base")   # controles extra de S2: k12, la suma S de distancias y el log del caudal de base
COLS_K = [("grupo", "varchar"), ("orden", "integer"), ("n", "integer"), ("padres", "integer"),
          ("k_media", "double"), ("perdida_media", "double"), ("desvio_intra_padre", "double")]
COLS_PRUEBA = gm.COLS_PRUEBA          # prueba, estadistico, valor, ic_bajo, ic_alto, n, veredicto


def mart(sufijo: str = "", cuenca: str = "") -> str:
    """Nombre de una tabla del modulo: mart_golpes_mismo_padre[_<cuenca>]<sufijo>; Vaca Muerta va sin cuenca."""
    return "mart_golpes_mismo_padre" + (f"_{cuenca}" if cuenca else "") + sufijo


# ------------------------------------------------------------------ carga

def cargar_pad_padre(con) -> np.ndarray:
    """El pad del padre por posicion de D (el orden de pozo_id de int_pozo_ubicacion, el de D["primer"]).

    Un pozo sin pad es su propio pad (como pipeline.diferido para el pad hijo)."""
    filas = con.execute("select pozo_id, pad_id from int_pozo_ubicacion order by pozo_id").fetchall()
    codigos: dict[str, int] = {}
    salida: list[int] = []
    for pozo_id, pad_id in filas:
        clave = f"pozo:{pozo_id}" if pad_id is None else str(pad_id)
        if clave not in codigos:
            codigos[clave] = len(codigos)
        salida.append(codigos[clave])
    return np.array(salida, dtype=np.int64)


def cargar(con) -> dict:
    """Vaca Muerta: los cargadores de pipeline.golpes_mismo_mes mas el pad del padre."""
    D = gm.cargar(con)
    D["pad_padre"] = cargar_pad_padre(con)
    return D


def cargar_cuenca(con) -> dict:
    """Colorado: los cargadores de pipeline.dias_perdidos mas el pad del padre."""
    D = dias_perdidos.cargar_cuenca(con)
    D["pad_padre"] = cargar_pad_padre(con)
    return D


# ------------------------------------------------------------------ muestra

def _padres(e: dict, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Por padre de la muestra idx: la cantidad de meses de golpe y la cantidad de valores distintos de k."""
    idx = np.asarray(idx)
    if not len(idx):
        vacio = np.zeros(0, dtype=np.int64)
        return vacio, vacio, vacio
    u, inv = np.unique(e["padre"][idx], return_inverse=True)
    n_meses = np.bincount(inv, minlength=len(u))
    pares = np.unique(np.column_stack([inv, np.asarray(e["k"][idx], dtype=np.int64)]), axis=0)
    n_k = np.bincount(pares[:, 0], minlength=len(u))
    return u, n_meses, n_k


def muestra(D: dict) -> tuple[dict, np.ndarray]:
    """Eventos y la muestra restringida.

    Entran los padres de la muestra de partida con al menos MIN_MESES_PADRE meses de golpe y al menos MIN_K_PADRE
    valores distintos de k entre ellos; de esos padres entran todos sus meses de golpe aislados."""
    e = gm.eventos(D)
    e["pad_padre"] = np.asarray(D["pad_padre"], dtype=np.int64)[e["padre"]]
    idx0 = np.flatnonzero(gm.muestras(e)["principal"])
    u, n_meses, n_k = _padres(e, idx0)
    califican = u[(n_meses >= MIN_MESES_PADRE) & (n_k >= MIN_K_PADRE)]
    idx = idx0[np.isin(e["padre"][idx0], califican)]
    return e, idx


def conteos(e: dict, idx: np.ndarray) -> dict:
    """Conteos de la muestra: la de partida y la restringida."""
    idx = np.asarray(idx)
    idx0 = np.flatnonzero(gm.muestras(e)["principal"])
    u, n_meses, n_k = _padres(e, idx0)
    con2 = n_meses >= MIN_MESES_PADRE
    conk = con2 & (n_k >= MIN_K_PADRE)
    padres = np.unique(e["padre"][idx]) if len(idx) else np.zeros(0, dtype=np.int64)
    pads = np.unique(e["pad_padre"][idx]) if len(idx) else np.zeros(0, dtype=np.int64)
    return {"aislados_con_ventana": int(len(idx0)),
            "padres_partida": int(len(u)),
            "padres_2_meses": int(con2.sum()),
            "padres_k_distinto": int(conk.sum()),
            "meses_restringida": int(len(idx)),
            "padres": int(len(padres)),
            "pads": int(len(pads)),
            "valores_k": int(len(np.unique(e["k"][idx]))) if len(idx) else 0,
            "meses_por_padre_media": float(len(idx) / len(padres)) if len(padres) else 0.0}


# ------------------------------------------------------------------ modelo

def _extra(e: dict, idx: np.ndarray, nombres) -> list[np.ndarray]:
    """Columnas extra del modelo: k12, la suma S de las distancias y el log del caudal de base."""
    cols: list[np.ndarray] = []
    for nombre in nombres:
        if nombre == "k12":
            cols.append(np.asarray(e["k12"][idx], dtype=float))
        elif nombre == "S":
            cols.append(gm._s(e, idx))
        elif nombre == "log_base":
            cols.append(np.log(np.asarray(e["base"][idx], dtype=float)))
    return cols


def ajuste(e: dict, idx: np.ndarray, y, grupo, extra=()) -> tuple[float, float]:
    """Minimos cuadrados intra-padre: P_it = alpha_i + b k_it + gamma' X_it, con los controles demeanados por padre.

    `grupo` es la etiqueta de padre de cada fila de idx. a es la media entre padres de alpha_i, con los controles
    centrados en la media de las medias de cada padre: a = media_i(P_i) - b media_i(k_i)."""
    idx = np.asarray(idx)
    grupo = np.asarray(grupo)
    u, inv = np.unique(grupo, return_inverse=True)
    n_padres = len(u)
    k = np.asarray(e["k"][idx], dtype=float)
    cols = ([k] + _extra(e, idx, extra)
            + _dummies(np.asarray(e["edad_g"][idx])) + _dummies(np.asarray(e["anio"][idx])))
    X = np.column_stack(cols)
    yy = np.asarray(y, dtype=float)
    yy = yy[idx] if len(yy) == len(e["padre"]) else yy
    cuenta = np.bincount(inv, minlength=n_padres).astype(float)

    def medias(v: np.ndarray) -> np.ndarray:
        """La media de cada padre (una por padre)."""
        return np.bincount(inv, weights=v, minlength=n_padres) / cuenta

    def por_fila(v: np.ndarray) -> np.ndarray:
        """La media de cada padre, repetida en sus filas."""
        return np.bincount(inv, weights=v, minlength=n_padres)[inv] / cuenta[inv]

    yd = yy - por_fila(yy)
    Xd = X - np.column_stack([por_fila(X[:, j]) for j in range(X.shape[1])])
    quedan = [j for j in range(X.shape[1]) if np.any(np.abs(Xd[:, j]) > 1e-12)]
    b = 0.0
    if quedan:
        beta = np.linalg.lstsq(Xd[:, quedan], yd, rcond=None)[0]
        b = float(beta[quedan.index(0)]) if 0 in quedan else 0.0
    a = float(np.mean(medias(yy)) - b * np.mean(medias(k)))
    return a, b


def _boot(e: dict, idx: np.ndarray, reps: int, semilla: int, fn) -> list:
    """fn(indices, grupo) en `reps` remuestras por pad del padre.

    Cada pad remuestreado cuenta como un padre distinto: sus filas reciben una etiqueta de padre unica por draw, de
    modo que un pad que sale dos veces no junta a sus padres (ni los junta consigo mismo)."""
    idx = np.asarray(idx)
    grupos = _clusters(e["pad_padre"][idx])
    rng = np.random.default_rng(semilla)
    base = int(e["padre"].max()) + 1
    salida = []
    for _ in range(reps):
        pick = rng.integers(0, len(grupos), len(grupos))
        filas, etiquetas = [], []
        for t, c in enumerate(pick):
            pos = grupos[c]
            filas.append(idx[pos])
            etiquetas.append(t * base + e["padre"][idx[pos]])
        idx_r = np.concatenate(filas)
        grupo_r = np.concatenate(etiquetas)
        salida.append(fn(idx_r, grupo_r))
    return salida


def veredicto(n_padres: int, n_meses: int, ab_ic_bajo: float, phi: float, phi_ic_bajo: float, phi_ic_alto: float) -> str:
    """La regla del encabezado, en orden: muestra, perdida medible, ahorra, no ahorra, no firme."""
    if n_padres < PADRES_MIN or n_meses < MESES_MIN:
        return "sin muestra"
    if not ab_ic_bajo > 0:
        return "sin perdida medible"
    if phi_ic_bajo > 0 and phi >= UMBRAL_FIJO:
        return "agrupar ahorra"
    if phi_ic_alto < UMBRAL_FIJO:
        return "agrupar no ahorra"
    return "no firme"


# ------------------------------------------------------------------ calculo

def _filas_k(e: dict, idx: np.ndarray) -> list[tuple]:
    """La tabla por cantidad de hijos en el mes (descriptiva): media y desvío dentro del padre."""
    filas: list[tuple] = []
    if not len(idx):
        return [(etq, gi, 0, 0, None, None, None) for gi, (etq, _) in enumerate(zip(gm.ETQ_GRUPO, gm.GRUPOS_K))]
    p = e["padre"][idx]
    k = e["k"][idx]
    perdida = e["perdida"][idx]
    u, inv = np.unique(p, return_inverse=True)
    media_padre = np.bincount(inv, weights=perdida, minlength=len(u)) / np.bincount(inv, minlength=len(u))
    desv = perdida - media_padre[inv]
    g = gm._grupo_k(k)
    for gi, etq in enumerate(gm.ETQ_GRUPO):
        en = g == gi
        if not en.any():
            filas.append((etq, gi, 0, 0, None, None, None))
            continue
        filas.append((etq, gi, int(en.sum()), int(len(np.unique(p[en]))), float(k[en].mean()),
                      float(perdida[en].mean()), float(desv[en].mean())))
    return filas


def calcular(D: dict, reps: int = REPS) -> dict[str, list[tuple]]:
    """Las dos tablas del modulo: la tabla por k y las pruebas (principal, S1, S2, agrupado83 y conteos)."""
    e, idx = muestra(D)
    c = conteos(e, idx)
    n = len(idx)
    filas_k = _filas_k(e, idx)
    prueba: list[tuple] = []
    if len(np.unique(e["padre"][idx])) < 2:
        prueba.append(("principal", "phi", None, None, None, n, "sin muestra"))
    else:
        grupo = e["padre"][idx]
        a, b = ajuste(e, idx, e["perdida"], grupo)
        av, bv = ajuste(e, idx, e["vol"], grupo)
        a83, b83 = gm.ajuste(e, idx, e["perdida"])

        def una(i, g):
            return (*ajuste(e, i, e["perdida"], g), *ajuste(e, i, e["vol"], g), *gm.ajuste(e, i, e["perdida"]))

        rep = np.array(_boot(e, idx, reps, SEMILLA_PADRE, una), dtype=float)
        f, r = gm._filas_ab("principal", a, b, rep[:, :2], n)
        v = veredicto(c["padres"], n, r["ab_ic"][0], r["phi"], *r["phi_ic"])
        f[3] = (*f[3][:6], v)
        prueba += f
        valido = r["phi_r"][np.isfinite(r["phi_r"])]
        prueba += [("principal", "error_phi", float(np.std(valido, ddof=1)) if len(valido) > 1 else None, None, None,
                    len(valido), None),
                   ("principal", "descartadas", r["descartadas"], None, None, reps, None),
                   ("principal", "b_negativas", int((rep[:, 1] < 0).sum()), None, None, reps, None)]
        ab_r = rep[:, 0] + rep[:, 1]
        for kk in KS_RHO:
            rho_r = np.where(ab_r > 0, (rep[:, 0] + rep[:, 1] * kk) / (kk * np.where(ab_r > 0, ab_r, 1)), np.nan)
            prueba.append(("principal", f"rho_{kk}", gm._rho(a, b, kk), *gm._ic(rho_r), n, None))
        k = e["k"][idx]
        prueba += [("principal", "k_media", float(k.mean()), None, None, n, None),
                   ("principal", "perdida_media", float(e["perdida"][idx].mean()), None, None, n, None),
                   ("principal", "pads", c["pads"], None, None, n, None),
                   ("principal", "padres", c["padres"], None, None, n, None),
                   ("principal", "meses", n, None, None, n, None),
                   ("principal", "valores_k", c["valores_k"], None, None, n, None),
                   ("principal", "meses_por_padre_media", c["meses_por_padre_media"], None, None, n, None)]
        f1, _ = gm._filas_ab("S1", av, bv, rep[:, 2:4], n, "_m3")
        prueba += f1
        a2, b2 = ajuste(e, idx, e["perdida"], grupo, EXTRA_S2)
        rep2 = np.array(_boot(e, idx, reps, SEMILLA_PADRE + 1,
                              lambda i, g: ajuste(e, i, e["perdida"], g, EXTRA_S2)), dtype=float)
        f2, _ = gm._filas_ab("S2", a2, b2, rep2, n)
        prueba += f2 + [("S2", "pads", c["pads"], None, None, n, None)]
        f3, _ = gm._filas_ab("agrupado83", a83, b83, rep[:, 4:6], n)
        prueba += f3
    prueba += [("conteo", "aislados_con_ventana", c["aislados_con_ventana"], None, None, None, None),
               ("conteo", "padres_partida", c["padres_partida"], None, None, None, None),
               ("conteo", "padres_2_meses", c["padres_2_meses"], None, None, None, None),
               ("conteo", "padres_k_distinto", c["padres_k_distinto"], None, None, None, None),
               ("conteo", "meses_restringida", c["meses_restringida"], None, None, None, None),
               ("conteo", "ultimo_mes_indice", int(D["n_mes"]), None, None, None, None)]
    prueba = [(p, s, gm._f(x) if x is not None else None, gm._f(lo), gm._f(hi), nn, vv)
              for p, s, x, lo, hi, nn, vv in prueba]
    return {mart(): filas_k, mart("_prueba"): prueba}


def escribir(con, t: dict[str, list[tuple]], cuenca: str = "") -> None:
    """Escribe las dos tablas con el nombre de la cuenca (Colorado tambien queda en el warehouse de Vaca Muerta).

    Una llamada por mart con el nombre escrito, que es lo que lee pipeline.linaje."""
    if not cuenca:
        _escribir(con, "mart_golpes_mismo_padre", COLS_K, t[mart()])
        _escribir(con, "mart_golpes_mismo_padre_prueba", COLS_PRUEBA, t[mart("_prueba")])
        return
    if cuenca != COLORADO.id:
        raise ValueError(f"golpes_mismo_padre no tiene adaptacion escrita para la cuenca {cuenca!r}: "
                         "solo Vaca Muerta y Colorado")
    _escribir(con, "mart_golpes_mismo_padre_colorado", COLS_K, t[mart()])
    _escribir(con, "mart_golpes_mismo_padre_colorado_prueba", COLS_PRUEBA, t[mart("_prueba")])


def marts(con, cuenca: str = "") -> dict | None:
    """Las tablas de una cuenca (None si no se corrio): por k y pruebas."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?",
                       [mart("_prueba", cuenca)]).fetchone()[0]:
        return None
    return {"k": con.execute(f"select * from {mart('', cuenca)} order by orden").fetchall(),
            "p": {(r[0], r[1]): r for r in con.execute(f"select * from {mart('_prueba', cuenca)}").fetchall()}}


# ------------------------------------------------------------------ pagina

FILAS_MODELO = (("principal", "Principal (cada padre consigo mismo)", "a", "a: costo fijo del mes (días de base)", 1),
                ("principal", "Principal (cada padre consigo mismo)", "b", "b: costo de cada hijo (días de base)", 1),
                ("principal", "Principal (cada padre consigo mismo)", "a_mas_b",
                 "a + b: un mes con un solo hijo (días de base)", 1),
                ("principal", "Principal (cada padre consigo mismo)", "phi", "φ = a / (a + b)", 2),
                *(("principal", "Principal (cada padre consigo mismo)", f"rho_{k}", f"ρ con {k} hijos (juntos sobre separados)", 2)
                  for k in KS_RHO),
                ("S1", "S1, volumen", "a_m3", "a (m3)", 0), ("S1", "S1, volumen", "b_m3", "b (m3)", 0),
                ("S1", "S1, volumen", "a_mas_b_m3", "a + b (m3)", 0), ("S1", "S1, volumen", "phi_m3", "φ en volumen", 2),
                ("S2", "S2, más controles", "a", "a (días de base)", 1),
                ("S2", "S2, más controles", "b", "b (días de base)", 1),
                ("S2", "S2, más controles", "a_mas_b", "a + b (días de base)", 1),
                ("S2", "S2, más controles", "phi", "φ", 2),
                ("agrupado83", "Agrupado de #83, misma muestra", "a", "a (días de base)", 1),
                ("agrupado83", "Agrupado de #83, misma muestra", "b", "b (días de base)", 1),
                ("agrupado83", "Agrupado de #83, misma muestra", "a_mas_b", "a + b (días de base)", 1),
                ("agrupado83", "Agrupado de #83, misma muestra", "phi", "φ", 2))
FILAS_CONTEO = (("conteo", "aislados_con_ventana",
                 "Meses de golpe aislados con la ventana completa (muestra de partida)"),
                ("conteo", "padres_partida", "Padres de la muestra de partida"),
                ("conteo", "padres_2_meses", "De ellos, con dos o más meses de golpe"),
                ("conteo", "padres_k_distinto", "De ellos, con distinta cantidad de hijos entre esos meses"),
                ("conteo", "meses_restringida", "Meses de golpe de la muestra restringida"),
                ("principal", "padres", "Padres de la muestra restringida"),
                ("principal", "pads", "Pads del padre de la muestra restringida"),
                ("principal", "valores_k", "Valores distintos de k"),
                ("principal", "meses_por_padre_media", "Meses de golpe por padre (media)"),
                ("conteo", "ultimo_mes_indice", "Último mes de producción"))


def _ultimo_mes(n_mes) -> str:
    """El indice del ultimo mes de produccion como 'ano-mes'."""
    if n_mes is None:
        return "n/d"
    m = int(n_mes) - 1
    return f"{2000 + m // 12}-{m % 12 + 1:02d}"


def _linea_veredicto(p: dict, nombre: str) -> str:
    """La linea de veredicto de una cuenca, con los numeros que la sostienen."""
    v = _num(p, "principal", "phi", 6)
    linea = f"- {nombre}: **{gm.ETQ_VEREDICTO.get(v, v)}**. {gm.FRASE.get(v, '')}"
    if v == "sin muestra":
        return linea + (f" La muestra de partida tiene {_g(_num(p, 'conteo', 'aislados_con_ventana'))} meses de golpe aislados con "
                        f"la ventana completa, de {_g(_num(p, 'conteo', 'padres_partida'))} padres; "
                        f"{_g(_num(p, 'conteo', 'padres_2_meses'))} de esos padres tienen {_g(MIN_MESES_PADRE)} meses de golpe o "
                        f"más y {_g(_num(p, 'conteo', 'padres_k_distinto'))} tienen además {_g(MIN_K_PADRE)} valores distintos de "
                        f"k, así que la muestra restringida queda en {_g(_num(p, 'conteo', 'meses_restringida'))} meses de golpe "
                        f"de {_g(_num(p, 'conteo', 'padres_k_distinto'))} padres. La regla pide {_g(PADRES_MIN)} padres y "
                        f"{_g(MESES_MIN)} meses de golpe.")
    return linea + (f" Un mes con un solo hijo, a + b = {_val(p, 'principal', 'a_mas_b', unidad=' días de producción de base')}; "
                    f"la muestra restringida son {_g(_num(p, 'principal', 'meses'))} meses de golpe de "
                    f"{_g(_num(p, 'principal', 'padres'))} padres en {_g(_num(p, 'principal', 'pads'))} pads del padre; "
                    f"φ = {_val(p, 'principal', 'phi', 2)}.")


def _linea_optimizador(p: dict) -> str:
    """Lo que hace la unidad siguiente con este veredicto (U6b)."""
    v = _num(p, "principal", "phi", 6)
    a, b = _num(p, "principal", "a"), _num(p, "principal", "b")
    if v == "agrupar ahorra":
        return ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): el optimizador usa costo fijo "
                "más costo por hijo (a y b) por padre y mes, con b acotado a 0 o más antes de usarlo, así que reagrupar hijos en un "
                "mismo mes tiene crédito.")
    if v == "agrupar no ahorra":
        return ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): el optimizador usa un costo "
                "aditivo por hijo; agrupar no tiene crédito del lado del padre.")
    if v == "sin muestra":
        return ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): esta prueba no aporta ningún valor de "
                "a ni de b, y la estimación puntual de esta página no se usa. Con «sin muestra» queda lo último publicado, el modelo "
                "agrupado de pipeline.golpes_mismo_mes (PR #83): el optimizador corre los dos casos, costo aditivo por hijo y costo fijo "
                "más costo por hijo con esa estimación puntual, con b acotado a 0 o más antes de usarla, y publica el arrepentimiento "
                "con cada uno.")
    return ("- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): con este veredicto el optimizador "
            "corre los dos casos y publica el arrepentimiento con cada uno, costo aditivo por hijo y costo fijo más costo por hijo "
            f"con la estimación puntual (a = {_g(a, 1)} y b = {_g(b, 1)} días de base), con b acotado a 0 o más antes de usarla.")


def _tabla_modelo(p: dict, pco: dict | None) -> list[str]:
    cab = "| Prueba | Estadístico | Vaca Muerta | IC 95% |" + (" Colorado | IC 95% |" if pco else "")
    L = [cab, "| --- | --- | ---: | ---: |" + (" ---: | ---: |" if pco else "")]
    for prueba, etq, est, desc, dec in FILAS_MODELO:
        celdas = []
        for q in (p, pco) if pco else (p,):
            r = q.get((prueba, est))
            celdas += (["n/d", ""] if r is None or r[2] is None
                       else [_g(r[2], dec), _ict(r[3], r[4], dec) if r[3] is not None else ""])
        L.append(f"| {etq} | {desc} | " + " | ".join(celdas) + " |")
    return L


def _tabla_k_padre(filas) -> list[str]:
    L = ["| Hijos a menos de 1 km en el mes | Meses de golpe | Padres | k media | Pérdida media (días de base) | "
         "Desvío dentro del padre |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in filas:
        if not r[2]:
            L.append(f"| {r[0]} | 0 | 0 | | | |")
            continue
        L.append(f"| {r[0]} | {_g(r[2])} | {_g(r[3])} | {_g(r[4], 1)} | {_g(r[5], 1)} | {_g(r[6], 1)} |")
    return L


def _tabla_muestra(p: dict, pco: dict | None) -> list[str]:
    L = ["| Muestra | Vaca Muerta |" + (" Colorado |" if pco else ""), "| --- | ---: |" + (" ---: |" if pco else "")]
    for prueba, est, desc in FILAS_CONTEO:
        if est == "ultimo_mes_indice":
            val, valco = _ultimo_mes(_num(p, prueba, est)), _ultimo_mes(_num(pco, prueba, est)) if pco else None
        else:
            val, valco = _g(_num(p, prueba, est)), _g(_num(pco, prueba, est)) if pco else None
        L.append(f"| {desc} | {val} |" + (f" {valco} |" if pco else ""))
    return L


def pagina_golpes_mismo_padre(con) -> str:
    """Pagina de la wiki a partir de los marts (solo lee); la seccion de Colorado solo si se corrio."""
    vm, co = marts(con), marts(con, COLORADO.id)
    p, pco = vm["p"], (co["p"] if co else None)
    L = ["# Golpes en el mismo mes, con el padre como su propio control", "",
         f"Cuando se fracturan varios hijos a menos de {_g(KM_CERCA)} km de un padre en el mismo mes, ¿le cuesta al padre menos que "
         "si esos mismos hijos se fracturaran en meses separados? El modelo agrupado de pipeline.golpes_mismo_mes no pudo "
         "decidirlo: la pérdida de un mes de golpe varía mucho de un padre a otro y los intervalos incluían el cero. Acá cada "
         f"padre se compara consigo mismo: los padres con {_g(MIN_MESES_PADRE)} meses de golpe aislados o más y con distinta "
         "cantidad de hijos en cada uno aportan la diferencia de su pérdida entre un mes y otro, y lo que es propio del padre (su "
         "roca, su caudal, su operador, su terminación) queda fuera de b. Es la segunda pieza del optimizador de calendario: la "
         "unidad siguiente son las matrices de costo, el optimizador y el backtest.", "",
         "## Lectura", "",
         _linea_veredicto(p, "Vaca Muerta (regla informada)")]
    if pco:
        L.append(_linea_veredicto(pco, "Colorado (confirmatoria, misma regla)"))
    sin = _num(p, "principal", "phi", 6) == "sin muestra"
    desc = ("Descriptivo, la muestra no alcanza y no es una estimación de la que la regla pueda decir algo. " if sin else "")
    if _num(p, "principal", "b") is not None:
        L.append(f"- {desc}El costo por hijo es b = {_val(p, 'principal', 'b', unidad=' días de producción de base')}; "
                 f"{_g(_num(p, 'principal', 'b_negativas'))} de {_g(_num(p, 'principal', 'descartadas', 5))} repeticiones del "
                 "bootstrap dieron b menor que cero.")
    if _num(p, "agrupado83", "b") is not None:
        L.append("- " + desc + "Comparación con el modelo agrupado de pipeline.golpes_mismo_mes (PR #83) sobre la misma muestra de padres, sin "
                 "efecto fijo de padre: b = " + _val(p, "agrupado83", "b", unidad=" días de producción de base")
                 + " contra b = " + _val(p, "principal", "b", unidad=" días de producción de base")
                 + " de comparar cada padre consigo mismo. Es descriptiva: no cambia el veredicto.")
    L.append(_linea_optimizador(p))
    L += ["", "## El modelo", "",
          "Mínimos cuadrados con efecto fijo de padre: P_it = alpha_i + b k_it + gamma' X_it, con i el padre y t su mes de "
          f"golpe. P es la pérdida del mes de golpe en días de producción de base (meses {VENTANA[0]} a {VENTANA[1]} contra el "
          f"índice mediano de los controles), k la cantidad de hijos a menos de {_g(KM_CERCA)} km fracturados ese mes, y X los "
          "efectos fijos del grupo de edad del padre al momento del golpe y del año del golpe. La transformación intra-padre "
          "resta a cada variable la media de los meses de su padre, así que lo propio del padre queda fuera de b. a es la media "
          "entre padres de alpha_i, con los controles centrados en la media de las medias de cada padre: no depende de qué "
          "categoría de edad o de año sea la de referencia. Un mes con un solo hijo cuesta a + b; juntos, k hijos cuestan "
          "a + b k; separados, k (a + b). φ = a / (a + b) es la parte fija del costo de un mes con un solo hijo, y ρ es el costo "
          "de k hijos juntos sobre el de los mismos k separados.", "", *_tabla_modelo(p, pco), "",
          f"Los IC son de percentiles por pads del padre ({_g(_num(p, 'principal', 'descartadas', 5))} repeticiones). Para φ y ρ se "
          f"descartan las repeticiones con a + b de cero o menos: {_g(_num(p, 'principal', 'descartadas'))} en Vaca Muerta"
          + (f" y {_g(_num(pco, 'principal', 'descartadas'))} en Colorado" if pco else "")
          + f". Error de φ (desvío de las repeticiones) en Vaca Muerta: {_g(_num(p, 'principal', 'error_phi'), 2)}."
          + (" Con la muestra por debajo de lo que pide la regla, estas cifras se publican porque la regla manda publicar todos los "
             "resultados, no como estimaciones: con tan pocos pads del padre en el bootstrap los intervalos no informan, y un a + b "
             "negativo no tiene lectura como costo." if sin else ""),
          "", "## Pérdida por cantidad de hijos en el mes", "",
          "Descriptivo: en la muestra restringida, la cantidad de hijos que trae el mes de golpe, la pérdida media del mes y el "
          "desvío de la pérdida de cada mes respecto de la media de los meses de su propio padre. No lleva intervalos: es la "
          "forma de la muestra, no una estimación.", "", *_tabla_k_padre(vm["k"]),
          "", "## Muestra", "", *_tabla_muestra(p, pco)]
    if co:
        L += ["", "## Colorado (confirmatoria)", "",
              "La misma regla, con las adaptaciones de pipeline.dias_perdidos a Colorado (padres horizontales, hijos con la fecha "
              "de inicio de FracFocus, el operador del último mes informado y un grupo de edad propio para los padres con el primer "
              "petróleo censurado). En Colorado no se había mirado ninguna pérdida dentro de un padre antes de fijar la regla.",
              "", _linea_veredicto(pco, "Veredicto"), "", *_tabla_k_padre(co["k"])]
    L += ["", "## Regla fijada antes de correr", "",
          "- La regla está en el encabezado de `pipeline/golpes_mismo_padre.py`, en un commit que solo trae el encabezado y las "
          "constantes, anterior a cualquier cálculo de este módulo. No se cambió después de ver los resultados. Se publican "
          "todos los resultados, favorables o no: «no firme» o «sin muestra» es un resultado terminado, no se rediseña la regla "
          "para evitarlo.",
          f"- Veredicto, en orden: «sin muestra» con menos de {_g(PADRES_MIN)} padres o menos de {_g(MESES_MIN)} meses de golpe en "
          "la muestra restringida; «sin pérdida medible» si el límite bajo del IC de a + b no pasa de cero; «agrupar ahorra» si el "
          f"límite bajo del IC de φ es mayor que cero y φ es de al menos {_g(UMBRAL_FIJO, 2)}; «agrupar no ahorra» si el límite alto "
          f"del IC de φ es menor que {_g(UMBRAL_FIJO, 2)}; «no firme» en otro caso.",
          "- Qué se había mirado antes: todo lo publicado de pipeline.golpes_mismo_mes (PR #83), en las dos cuencas: el modelo "
          "agrupado P = a + b k con controles, sus intervalos y el veredicto de esa prueba. Lo que NO se había calculado era "
          "ninguna cantidad de esta prueba: ni cuántos padres tienen dos o más meses de golpe aislados, ni cuántos de ellos con "
          "distinta k, ni ninguna pérdida dentro de un padre. El tamaño de la muestra restringida se ve por primera vez cuando "
          "corre el módulo, y puede ser «sin muestra».",
          "- Por eso en Vaca Muerta la prueba es de regla informada y en Colorado es confirmatoria, en el sentido de #81 y #83: la "
          "misma regla, corrida después de Vaca Muerta y sin tocarla.",
          "- El bootstrap es por pads del padre, no por los pads hijo de #83 ni por el bootstrap espacial de 5 km: la dependencia "
          "que importa aquí es la de los padres de un mismo pad, que comparten hijos. Cada pad remuestreado cuenta como un padre "
          "distinto.",
          "- Datos: el warehouse con el último mes de producción de "
          + _ultimo_mes(_num(p, "conteo", "ultimo_mes_indice"))
          + (f"; Colorado, { _ultimo_mes(_num(pco, 'conteo', 'ultimo_mes_indice'))}." if pco else "."),
          "", "## Qué no prueba", "",
          "- Con dato mensual, «el mismo mes» no es «al mismo tiempo»: dos hijos del mismo mes pueden fracturarse con semanas de "
          "diferencia.",
          "- Solo los padres con distinta k identifican b: un padre cuyos golpes tienen la misma k no aporta nada a b. Los padres "
          "que entran son los que vivieron más de un desarrollo separado, con otro pad hijo, otro tamaño y otra época; el efecto "
          "fijo de padre absorbe lo estable del padre, no lo que cambia entre un golpe y otro (la edad y el año entran como "
          "controles, el diseño del pad hijo no).",
          "- La pérdida es volumen diferido contra la trayectoria de los controles en la ventana: no dice que ese petróleo se pierda.",
          "- Solo el lado del padre: lo que pierde el hijo por la depleción del padre no está en la prueba.",
          f"- El aislamiento mira {MESES_AISLADO} meses hacia atrás y la base son los meses {BASE[0]} a {BASE[1]}: dos golpes "
          f"aislados del mismo padre tienen que estar al menos a {MESES_AISLADO + 1} meses de distancia.", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ main

def _resumen(t: dict, nombre: str) -> None:
    p = {(f[0], f[1]): f for f in t[mart("_prueba")]}
    f = p[("principal", "phi")]
    print(f"[{nombre}] phi {f[2]} (IC {f[3]} a {f[4]}; n {f[5]}): {f[6]}")


def main(path=DATA / "warehouse.duckdb", cuenca: Cuenca | None = None, reps: int = REPS) -> None:
    """Vaca Muerta sobre su warehouse; con `cuenca`, esa cuenca sobre el suyo (solo lectura) y las tablas en el de Vaca Muerta."""
    if cuenca is None:
        con = duckdb.connect(str(path))
        try:
            t = calcular(cargar(con), reps)
            escribir(con, t)
        finally:
            con.close()
        _resumen(t, "golpes_mismo_padre")
        return
    if cuenca.id != COLORADO.id:
        raise ValueError(f"golpes_mismo_padre no tiene adaptacion escrita para la cuenca {cuenca.id!r}: "
                         "solo Vaca Muerta y Colorado")
    con_c = duckdb.connect(str(cuenca.db), read_only=True)
    try:
        t = calcular(cargar_cuenca(con_c), reps)
    finally:
        con_c.close()
    con = duckdb.connect(str(path))
    escribir(con, t, cuenca.id)
    con.close()
    _resumen(t, f"golpes_mismo_padre {cuenca.id}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="pipeline.golpes_mismo_padre")
    ap.add_argument("--cuenca", help="id de una cuenca de la replicacion (pipeline/cuencas.py); sin argumento, Vaca Muerta")
    a = ap.parse_args()
    main(cuenca=_cuenca(a.cuenca) if a.cuenca else None)
