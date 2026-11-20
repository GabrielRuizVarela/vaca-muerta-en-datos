"""El mecanismo medido con la geometria de las ramas: padres al costado de la rama del hijo contra padres en su punta.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.mecanismo

REGLA FIJADA ANTES DE CORRER (2026-11-20). Este archivo es el primer commit de la unidad: la regla, las constantes y los umbrales
del veredicto. Antes de fijarla no se calculo ninguna cifra de resultado con este diseno (ni brechas, ni diferencias entre
posiciones, ni conteos de eventos por posicion o por banda). Todo lo que falta decidir esta decidido aca; si algo resulta
ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra de resultado.

Pregunta: la pagina de la regla de parada (`wiki/hallazgos/eje_parada.md`) cerro el eje de la brujula y dijo que "la geometria de
las ramas no se pudo probar". Con las ramas publicadas (`mart_trayectoria_par`, `mart_par_rama`) si se puede. Esta es una prueba
NUEVA, no una repeticion del eje: la posicion del padre se mide respecto de la rama de cada hijo (su costado o su punta), que no
es la disposicion de pads de la cuenca. El mecanismo que se pone a prueba: el padre que queda al costado de la rama del hijo, en
paralelo, rinde menos que el que queda en su punta, a igual distancia entre ramas.

Eventos y muestra (como el estudio principal, con la distancia entre ramas en lugar de la distancia de superficie):
  * Pares: las filas de `mart_trayectoria_par` (hijo, padre, mes de fractura, distancia minima entre ramas `m_min` en metros)
    unidas a `mart_par_rama` por (hijo, padre). El padre cumple la regla de edad del estudio principal (al menos 6 meses de
    produccion en el mes de la fractura del hijo), que ya trae `int_par_padre_hijo`.
  * Un evento es un (padre, mes de fractura del hijo). El hijo que fija el evento es el de menor `m_min` entre los pares
    del evento (empate: el de menor id). La banda, la posicion, el paralelismo y el angulo al SHmax son los de ese par.
  * El padre entra con la base de los meses -3 a -1 mayor que 1 m3/d de petroleo, y el indice es su caudal del mes sobre esa
    base, como en `pipeline.placebo.marco`.
  * Muestra del contraste: eventos con `m_min` menor que LATERAL_CERCANO_M = 1.000 m, `paralelas` verdadera (diferencia de
    azimut de 20 grados o menos) y `posicion` en {costado, punta}. Los "mixto" y los no paralelos no entran.
  * Bandas de distancia lateral: 0 a 300, 300 a 600 y 600 a 1.000 m (el limite inferior incluido, el superior no).
  * Control lateral: los eventos cuyo hijo mas cercano por ramas queda a LATERAL_CONTROL_M = 2.000 m o mas de la rama del padre
    (mismas reglas de padre y de base). Cada evento se mide contra el control de su misma edad: el grupo de edad del padre en
    el mes del evento (6 a 11, 12 a 23, 24 a 47, 48 o mas meses) y el mismo k. Un grupo de edad con menos de
    MIN_CONTROL_EDAD = 5 controles con dato en ese k no da control y sus eventos quedan afuera de ese k.

Estimador (el del estudio principal: cada padre indexado contra su propia base, brecha entre medianas):
  * brecha de un conjunto de eventos G en el mes k = mediana del indice de G en k menos la mediana, sobre los eventos de G, del
    indice mediano del control de su grupo de edad en k. Con esa resta el control tiene la misma mezcla de edades que G.
  * contraste de una banda b = brecha de los costados de b menos brecha de las puntas de b. Es la cantidad central de la prueba
    (H-G1): negativa si el costado rinde menos que la punta.
  * contraste principal = promedio de los contrastes de las tres bandas pesado por los eventos de cada banda (costados mas
    puntas de la banda con dato en k). Una banda con menos de MIN_GRUPO_BANDA = 5 eventos en el costado o en la punta no tiene
    contraste y no entra al promedio (su peso es cero).
  * IC 95%: bootstrap de percentiles (2,5 y 97,5) con REPS_BOOT repeticiones que remuestrean bloques de 5 km (el bloque del pad
    del hijo que fija el evento, la misma grilla que `pipeline.bloques`), con semilla fija SEMILLA_MECANISMO. En cada
    remuestra se recalculan controles, brechas, pesos y contraste. Las remuestras sin ninguna banda con contraste se descartan.

Modelo principal, el unico que da el veredicto:
  * contraste principal en k = 1, base de los meses -3 a -1, eventos del estudio principal (base mayor que 1 m3/d) y el IC por
    bloques de 5 km.
  * Contraste placebo en k = -1 (antes de que el hijo fracture): misma muestra y mismo estimador, pero con la base limpia de los
    meses -6 a -4, la que usa `pipeline.placebo` para su pretendencia (con la base principal el mes -1 es parte de la base y no
    puede mostrar nada), con los eventos que pasan las dos bases y con el IC por bloques de 5 km.

Veredicto (se aplica en este orden):
  * "sin muestra": menos de MIN_EVENTOS_POSICION = 80 eventos en los costados o menos de 80 en las puntas en el modelo
    principal (eventos con indice en k = 1 y control de su edad, sumados las tres bandas), o ninguna banda con contraste.
    No hay veredicto.
  * "sostiene": el contraste principal en k = 1 tiene el limite superior de su IC menor que cero (negativo, con IC que excluye
    cero) Y el contraste placebo en k = -1 tiene un IC que incluye cero.
  * "ubicación": el contraste principal en k = 1 tiene el limite superior de su IC menor que cero Y el contraste placebo en
    k = -1 tambien tiene un IC que excluye cero (con cualquier signo): la diferencia viene de donde estan los pozos, no
    del mecanismo.
  * "no firme": cualquier otro caso (entre ellos, un IC del contraste en k = 1 que incluye cero o un contraste positivo con IC
    que excluye cero, que seria el signo contrario al del mecanismo).
El veredicto sale solo del modelo principal. "no firme" y "sin muestra" son resultados terminados: no se rediseña la regla.

Se publican todos los modelos calculados (ninguno cambia el veredicto):
  * los contrastes de cada banda en k = 1 con sus conteos y sus brechas por posicion;
  * el contraste principal en k = 1 con la base limpia sobre los mismos eventos que el placebo, para ver el k = 1 y el k = -1
    sobre un mismo conjunto de eventos;
  * la serie del contraste principal para k = -3 a 3 con la base limpia;
  * el contraste principal en k = 1 con IC por pads hijo y con IC por bloques de 2 km, y el promedio de las tres bandas sin
    pesar por eventos;
  * el mismo contraste en k = 1 con el costado definido por `solape_frac` de 0,5 o mas (y la punta igual), como lectura de
    sensibilidad de la definicion de costado.
Descriptivo, sin veredicto: la brecha de k = 1 por tercil del angulo al SHmax del hijo (`angulo_shmax_hijo`, SHMAX_PUBLICADO =
67,5 grados desde el norte), sobre la muestra del contraste principal, con los cortes en los terciles de ese angulo en la
muestra, total y por posicion, con n y el IC por bloques de 5 km cuando hay al menos 20 eventos.

`eje_parada.md` se actualiza con cualquier resultado: con "ni con la geometria de las ramas" si el veredicto es no firme o
ubicación, con el resultado nuevo si es sostiene, y con la nota de que no hubo muestra si es sin muestra. El eje de la brujula
sigue retirado.

Muestra (decirlo en la pagina y en la PR): las ramas medidas cubren de 80 a 94% de los hijos fracturados de 2016 a 2023 pero solo 39%
de los de 2024 y 25% de los de 2025, asi que la muestra es sobre todo de 2016 a 2023.

Que NO prueba:
  * Una asociacion medida, no la causa: el costado y la punta pueden diferir en lo que el contraste no ve (profundidad, unidad
    navegada, tamano de la fractura, tiempo desde la puesta en produccion del padre). La prueba placebo de k = -1 cubre las
    diferencias que ya existian antes de la fractura, no las que aparecen justo con ella.
  * No mide esfuerzos ni fracturas: es una huella de caudal entre padres con distinta posicion relativa.
  * Solo cubre pares con las dos ramas medidas y con menos de 5 km de superficie (los pares de `int_par_padre_hijo`).
    Un padre cuya rama no se publico queda afuera, tanto de la muestra cercana como del control lateral; un control puede
    tener otro hijo cercano con rama no publicada.
  * La posicion y el paralelismo se miden entre los ejes principales de las ramas en planta, sin la profundidad.
  * Los IC no se ajustan por comparaciones multiples, y los eventos de un mismo padre con varios hijos no son independientes.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import bloques, placebo
from pipeline.costo import SEMILLA, _clusters, _escribir, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, BASE_ORIGINAL, REPS_BOOT, _g
from pipeline.trayectorias import PARALELAS_MAX_GRADOS, SOLAPE_COSTADO

SEMILLA_MECANISMO = SEMILLA + 40
REPS = REPS_BOOT                    # repeticiones del bootstrap, las de pipeline.placebo
PARALELAS_MAX = PARALELAS_MAX_GRADOS  # diferencia de azimut maxima para "paralelas" (de pipeline.trayectorias)
SOLAPE_COSTADO_PRINCIPAL = SOLAPE_COSTADO  # solape minimo para "costado" (de pipeline.trayectorias)
LATERAL_CERCANO_M = 1000.0          # distancia entre ramas (m_min) por debajo de la cual el padre es cercano
LATERAL_CONTROL_M = 2000.0          # distancia entre ramas desde la cual el padre es control lateral
BANDAS_LATERAL_M = ((0.0, 300.0), (300.0, 600.0), (600.0, 1000.0))
POSICIONES_MUESTRA = ("costado", "punta")
SOLAPE_COSTADO_SENSIBILIDAD = 0.5   # lectura de sensibilidad: costado con solape de al menos la mitad de la rama del hijo
CORTES_EDAD = (12, 24, 48)          # grupos de edad del padre en el evento: 6 a 11, 12 a 23, 24 a 47 y 48 o mas meses
K_PRINCIPAL = 1
K_PLACEBO = -1
KS_SERIE = tuple(range(-3, 4))
BASE_PRINCIPAL = BASE_ORIGINAL      # meses -3 a -1
BASE_PLACEBO = BASE_LIMPIA          # meses -6 a -4
BASE_MIN = 1.0                      # m3/d de petroleo de la base (como en el estudio principal)
MIN_EVENTOS_POSICION = 80           # eventos en costado y en punta para que haya veredicto
MIN_GRUPO_BANDA = 5                 # eventos en el costado y en la punta de una banda para que tenga contraste
MIN_CONTROL_EDAD = 5                # controles con dato en un grupo de edad para que haya control
TAM_BLOQUE_KM = 5.0                 # bloque de remuestreo del IC del veredicto
TAM_BLOQUE_ALT_KM = 2.0             # IC alternativo publicado
N_TERCILES = 3
MIN_TERCIL_IC = 20                  # eventos desde los cuales la tabla de terciles publica IC
PERCENTILES_IC = (2.5, 97.5)
VEREDICTOS = ("sostiene", "ubicación", "no firme", "sin muestra")


def veredicto(n_costado: int, n_punta: int, n_bandas: int, k1_alto: float, km1_bajo: float, km1_alto: float) -> str:
    """Veredicto de la regla con los conteos del modelo principal, el limite superior del IC del contraste en k = 1 y el IC
    del contraste placebo en k = -1. No lee ninguna cifra del warehouse."""
    if n_costado < MIN_EVENTOS_POSICION or n_punta < MIN_EVENTOS_POSICION or n_bandas == 0:
        return "sin muestra"
    if not k1_alto < 0 or km1_bajo != km1_bajo or km1_alto != km1_alto:  # sin IC del placebo (nan) no se afirma nada
        return "no firme"
    return "ubicación" if (km1_bajo > 0 or km1_alto < 0) else "sostiene"


# ------------------------------------------------------------------ carga

SQL_PARES_RAMA = ("select p.hijo, p.padre, p.m_min, r.paralelas, r.posicion, r.solape_frac, r.angulo_shmax_hijo "
                   "from mart_trayectoria_par p join mart_par_rama r using (hijo, padre)")
SQL_BLOQUES = ("select h.hijo, c.lat, c.lon from int_frac_hijo h join int_pozo_ubicacion u on u.pozo_id = h.hijo "
               "join (select pad_id, avg(lat) as lat, avg(lon) as lon from int_pozo_ubicacion group by pad_id) c "
               "on c.pad_id = u.pad_id order by h.hijo")
ETIQUETAS_BANDA = ("0 a 300 m", "300 a 600 m", "600 a 1.000 m")
N_GRUPOS_EDAD = 4


def cargar(con) -> dict:
    """Datos de los pares con las dos ramas medidas, con la posicion del padre respecto de la rama del hijo.

    Devuelve el diccionario de `pipeline.placebo.cargar` mas los pares (la posicion del hijo y del padre dentro de ese
    diccionario), la distancia minima entre ramas, el paralelismo, la posicion, el solape y el angulo al SHmax, y el
    bloque de 5 km y de 2 km de cada hijo (la grilla de `pipeline.bloques`, por el centroide del pad del hijo)."""
    D = placebo.cargar(con)
    padre_id = np.array([int(r[0]) for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()],
                         dtype=np.int64)
    pos_hijo = {int(v): i for i, v in enumerate(D["hijo_id"])}
    pos_padre = {int(v): i for i, v in enumerate(padre_id)}
    q = con.execute(SQL_BLOQUES).fetchall()
    assert [int(r[0]) for r in q] == [int(v) for v in D["hijo_id"]], "los bloques no alinean con los hijos"
    lat = np.array([float(r[1]) for r in q], dtype=float)
    lon = np.array([float(r[2]) for r in q], dtype=float)
    D["bloque5"] = bloques.clave_bloque(lat, lon, TAM_BLOQUE_KM)
    D["bloque2"] = bloques.clave_bloque(lat, lon, TAM_BLOQUE_ALT_KM)
    hijo, padre, m_min, paralelas, posicion, solape, angulo = [], [], [], [], [], [], []
    for h, p, mm, par, pos, sol, ang in con.execute(SQL_PARES_RAMA).fetchall():
        i, j = pos_hijo.get(int(h)), pos_padre.get(int(p))
        if i is None or j is None:      # par cuyo hijo o cuyo padre no esta en los datos
            continue
        hijo.append(i)
        padre.append(j)
        m_min.append(float(mm))
        paralelas.append(bool(par))
        posicion.append(str(pos))
        solape.append(float(sol) if sol is not None else float("nan"))
        angulo.append(float(ang) if ang is not None else float("nan"))
    D["rama_hijo"] = np.array(hijo, dtype=np.int64)
    D["rama_padre"] = np.array(padre, dtype=np.int64)
    D["rama_m_min"] = np.array(m_min, dtype=float)
    D["rama_paralelas"] = np.array(paralelas, dtype=bool)
    D["rama_posicion"] = np.array(posicion, dtype=object)
    D["rama_solape"] = np.array(solape, dtype=float)
    D["rama_angulo"] = np.array(angulo, dtype=float)
    D["padre_id"] = padre_id
    return D


# ------------------------------------------------------------------ eventos

def _tasa(D: dict, padre: np.ndarray, mes: np.ndarray, k: int) -> np.ndarray:
    """Caudal del padre en el mes `mes + k`, con nan fuera de la matriz de tasas."""
    ancho = D["tasa"].shape[1]
    col = mes + k + placebo.PAD
    dentro = (col >= 0) & (col < ancho)
    v = D["tasa"][padre, np.clip(col, 0, ancho - 1)]
    return np.where(dentro, v, np.nan)


def _posicion(solape: np.ndarray, solape_costado: float) -> np.ndarray:
    """Posicion del padre respecto de la rama del hijo, relabelada con el umbral de solape dado.

    Costado con solape igual o mayor que el umbral, punta con solape cero y mixto en el resto, igual que
    `pipeline.trayectorias` con su umbral de 0,30."""
    sol = np.asarray(solape, dtype=float)
    out = np.full(len(sol), "mixto", dtype=object)
    out[sol >= solape_costado] = "costado"
    out[sol == 0.0] = "punta"
    return out


def eventos(D: dict, base: tuple[int, int], ks, solape_costado: float = SOLAPE_COSTADO_PRINCIPAL) -> dict:
    """Eventos (padre, mes de fractura del hijo) con el hijo mas cercano por ramas, como en `pipeline.placebo.marco`.

    Un evento es un (padre, mes): lo fija el hijo de menor `m_min` entre los pares del evento (empate por el menor id).
    El padre cumple la regla de edad (al menos EDAD_MIN meses de produccion) y su base de los meses -3 a -1 y la base
    pedida tienen que ser mayores que BASE_MIN. El indice de cada mes k es el caudal del padre sobre la base pedida."""
    h, p = D["rama_hijo"], D["rama_padre"]
    mes_par = D["hijo_mes"][h]
    sel = np.flatnonzero(D["primer"][p] <= mes_par - placebo.EDAD_MIN)
    padre, hijo, mes = p[sel], h[sel], mes_par[sel]
    m_min = D["rama_m_min"][sel]
    clave = padre * 100_000 + mes
    orden = np.lexsort((D["hijo_id"][hijo], m_min, clave))
    c = clave[orden]
    primero = orden[np.r_[True, c[1:] != c[:-1]]]
    padre, hijo, mes, m_min = padre[primero], hijo[primero], mes[primero], m_min[primero]
    par = sel[primero]                                        # el par del que sale cada evento
    b0 = placebo._media(D, padre, mes, *BASE_ORIGINAL)
    b1 = b0 if tuple(base) == BASE_ORIGINAL else placebo._media(D, padre, mes, *base)
    ok = (b0 > BASE_MIN) & (b1 > BASE_MIN)
    padre, hijo, mes, m_min, par, b1 = padre[ok], hijo[ok], mes[ok], m_min[ok], par[ok], b1[ok]
    idx = {k: _tasa(D, padre, mes, k) / b1 for k in ks}
    edad = mes - D["primer"][padre]
    grupo = np.zeros(len(edad), dtype=np.int64)
    for corte in CORTES_EDAD:
        grupo += (edad >= corte).astype(np.int64)
    solape = D["rama_solape"][par]
    return {"padre": padre, "padre_id": D["padre_id"][padre], "hijo": hijo, "hijo_id": D["hijo_id"][hijo],
            "mes": mes, "anio": D["hijo_anio"][hijo], "m_min": m_min, "idx": idx, "grupo": grupo,
            "pad": D["hijo_pad"][hijo], "bloque5": D["bloque5"][hijo], "bloque2": D["bloque2"][hijo],
            "angulo": D["rama_angulo"][par], "solape": solape,
            "posicion": _posicion(solape, solape_costado), "posicion_col": D["rama_posicion"][par],
            "paralelas": D["rama_paralelas"][par]}


def tipos(ev: dict, solape_costado: float = SOLAPE_COSTADO_PRINCIPAL) -> tuple[np.ndarray, np.ndarray]:
    """Tipo y banda de cada evento.

    Tipo 0: el evento no entra (mixto, no paralelo o a distancia lateral intermedia). Tipo 1: costado cercano. Tipo 2:
    punta cercana. Tipo 3: control lateral (a LATERAL_CONTROL_M o mas de la rama del padre). La banda va de 0 a 2 para
    los tipos 1 y 2 (limite inferior incluido, superior no) y es -1 para los demas."""
    m_min = np.asarray(ev["m_min"], dtype=float)
    par = np.asarray(ev["paralelas"], dtype=bool)
    pos = _posicion(ev["solape"], solape_costado)
    tipo = np.zeros(len(m_min), dtype=np.int64)
    cerca = m_min < LATERAL_CERCANO_M
    tipo[cerca & par & (pos == "costado")] = 1
    tipo[cerca & par & (pos == "punta")] = 2
    tipo[m_min >= LATERAL_CONTROL_M] = 3
    banda = np.full(len(m_min), -1, dtype=np.int64)
    for b, (lo, hi) in enumerate(BANDAS_LATERAL_M):
        sel = ((tipo == 1) | (tipo == 2)) & (m_min >= lo) & (m_min < hi)
        banda[sel] = b
    return tipo, banda


# ------------------------------------------------------------------ estimador

def control_por_edad(idx: np.ndarray, grupo: np.ndarray, tipo: np.ndarray) -> np.ndarray:
    """Indice mediano del control lateral por grupo de edad del padre (0 a 3).

    Es nan en un grupo con menos de MIN_CONTROL_EDAD controles con dato."""
    idx = np.asarray(idx, dtype=float)
    grupo = np.asarray(grupo)
    tipo = np.asarray(tipo)
    out = np.full(N_GRUPOS_EDAD, np.nan)
    control = (tipo == 3) & ~np.isnan(idx)
    for g in range(N_GRUPOS_EDAD):
        sel = control & (grupo == g)
        if int(sel.sum()) >= MIN_CONTROL_EDAD:
            out[g] = float(np.median(idx[sel]))
    return out


def brecha(idx: np.ndarray, grupo: np.ndarray, tipo: np.ndarray, sel: np.ndarray, ctl: np.ndarray) -> float:
    """Mediana del indice del conjunto `sel` menos la mediana del control de su misma edad.

    Un evento cuenta solo si tiene indice y control de su grupo de edad."""
    idx = np.asarray(idx, dtype=float)
    grupo = np.asarray(grupo)
    c = np.asarray(ctl, dtype=float)[grupo]
    ok = np.asarray(sel, dtype=bool) & ~np.isnan(idx) & ~np.isnan(c)
    if not bool(ok.any()):
        return float("nan")
    return float(np.median(idx[ok]) - np.median(c[ok]))


def contraste(idx: np.ndarray, grupo: np.ndarray, tipo: np.ndarray, banda: np.ndarray, ponderado: bool = True) -> dict:
    """Contraste por banda y promedio de las bandas, con los conteos de cada posicion.

    El contraste de una banda es la brecha de sus costados menos la brecha de sus puntas. Una banda con menos de
    MIN_GRUPO_BANDA eventos en el costado o en la punta no tiene contraste y no entra al promedio (su peso es cero).
    El promedio es ponderado por los eventos de cada banda con dato, o simple si `ponderado` es falso."""
    idx = np.asarray(idx, dtype=float)
    grupo = np.asarray(grupo)
    tipo = np.asarray(tipo)
    banda = np.asarray(banda)
    ctl = control_por_edad(idx, grupo, tipo)
    c = ctl[grupo]
    ok = ~np.isnan(idx) & ~np.isnan(c)
    bandas, deltas, pesos = [], [], []
    n_costado, n_punta = 0, 0
    for b in range(len(BANDAS_LATERAL_M)):
        sel_c = ok & (tipo == 1) & (banda == b)
        sel_p = ok & (tipo == 2) & (banda == b)
        nc, npu = int(sel_c.sum()), int(sel_p.sum())
        n_costado += nc
        n_punta += npu
        gc = brecha(idx, grupo, tipo, sel_c, ctl)
        gp = brecha(idx, grupo, tipo, sel_p, ctl)
        if nc >= MIN_GRUPO_BANDA and npu >= MIN_GRUPO_BANDA:
            d, peso = gc - gp, nc + npu
        else:
            d, peso = float("nan"), 0
        bandas.append({"banda": b, "n_costado": nc, "n_punta": npu, "gap_costado": gc, "gap_punta": gp,
                       "delta": d, "peso": peso})
        if peso > 0:
            deltas.append(d)
            pesos.append(peso)
    if not deltas:
        delta = float("nan")
    elif ponderado:
        delta = float(np.average(deltas, weights=pesos))
    else:
        delta = float(np.mean(deltas))
    return {"delta": delta, "n_costado": n_costado, "n_punta": n_punta, "bandas": bandas, "n_bandas": len(deltas),
            "n_control": int((ok & (tipo == 3)).sum())}


def ic(fun, idx: np.ndarray, grupo: np.ndarray, tipo: np.ndarray, banda: np.ndarray, clave: np.ndarray,
       reps: int = REPS, semilla: int = SEMILLA_MECANISMO) -> tuple[float, float]:
    """IC 95% por bootstrap de percentiles: remuestrea los conglomerados de `clave` y recalcula la estimacion.

    Los eventos de tipo 0 quedan afuera (los bloques son solo los de los eventos que entran). Las remuestras sin dato
    se descartan; sin ninguna, el intervalo es (nan, nan)."""
    idx = np.asarray(idx, dtype=float)
    grupo = np.asarray(grupo)
    tipo = np.asarray(tipo)
    banda = np.asarray(banda)
    clave = np.asarray(clave)
    keep = tipo != 0
    idx, grupo, tipo, banda, clave = idx[keep], grupo[keep], tipo[keep], banda[keep], clave[keep]
    if len(idx) == 0:
        return (float("nan"), float("nan"))
    clusters = _clusters(clave)
    rng = np.random.default_rng(semilla)
    vals = []
    for _ in range(reps):
        i = _remuestra(rng, clusters)
        v = float(fun(idx[i], grupo[i], tipo[i], banda[i]))
        if v == v:
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, PERCENTILES_IC[0])), float(np.percentile(vals, PERCENTILES_IC[1])))


def modelo(ev: dict, k: int, ponderado: bool = True, solape_costado: float = SOLAPE_COSTADO_PRINCIPAL,
           semilla: int = SEMILLA_MECANISMO) -> dict:
    """Una fila de resultados: el contraste del estimador en el mes k, sus conteos y sus intervalos.

    Los tres intervalos son el bootstrap de percentiles por bloques de 5 km (el del veredicto), por pad del hijo y por
    bloques de 2 km. En cada remuestra se recalculan los controles, las brechas, los pesos y el contraste."""
    idx = np.asarray(ev["idx"][k], dtype=float)
    grupo = np.asarray(ev["grupo"])
    tipo, banda = tipos(ev, solape_costado)
    c = contraste(idx, grupo, tipo, banda, ponderado)

    def fun(ix, g, t, b):
        return contraste(ix, g, t, b, ponderado)["delta"]

    ic5 = ic(fun, idx, grupo, tipo, banda, ev["bloque5"], REPS, semilla)
    icp = ic(fun, idx, grupo, tipo, banda, ev["pad"], REPS, semilla)
    ic2 = ic(fun, idx, grupo, tipo, banda, ev["bloque2"], REPS, semilla)
    ok = ~np.isnan(idx)
    rel = ok & (tipo >= 1)
    return {"k": k, "delta": c["delta"], "n_costado": c["n_costado"], "n_punta": c["n_punta"], "n_control": c["n_control"],
            "n_bandas": c["n_bandas"], "bandas": c["bandas"], "ic_bajo_5km": ic5[0], "ic_alto_5km": ic5[1],
            "ic_bajo_pad": icp[0], "ic_alto_pad": icp[1], "ic_bajo_2km": ic2[0], "ic_alto_2km": ic2[1],
            "bloques_5km": int(len(np.unique(ev["bloque5"][rel]))), "pads": int(len(np.unique(ev["pad"][rel]))),
            "eventos_cercanos": int((ok & ((tipo == 1) | (tipo == 2))).sum()), "ponderado": bool(ponderado)}


# ------------------------------------------------------------------ calculo

def _tabla_shmax(ev: dict, k: int, semilla: int) -> list[tuple]:
    """Brecha de k por tercil del angulo al SHmax del hijo, total y por posicion.

    Los cortes son los terciles del angulo en la muestra del contraste principal. El IC es por bloques de 5 km y sale
    solo con al menos MIN_TERCIL_IC eventos: en cada remuestra se remuestran todos los eventos de tipo 1 a 3 (asi el
    control se recalcula) y se vuelve a medir la brecha del subconjunto con los cortes fijos."""
    idx = np.asarray(ev["idx"][k], dtype=float)
    grupo = np.asarray(ev["grupo"])
    tipo, _banda = tipos(ev, SOLAPE_COSTADO_PRINCIPAL)
    ctl = control_por_edad(idx, grupo, tipo)
    ok = ~np.isnan(idx) & ~np.isnan(ctl[grupo])
    cerca = ok & ((tipo == 1) | (tipo == 2))
    ang = np.asarray(ev["angulo"], dtype=float)
    if not bool(cerca.any()):
        return []
    cortes = np.quantile(ang[cerca], [1 / 3, 2 / 3])
    tercil = np.searchsorted(cortes, ang, side="right") + 1
    banda_tercil = np.where((tipo == 1) | (tipo == 2), tercil, -1)
    filas = []
    for t in range(1, N_TERCILES + 1):
        bajo = 0.0 if t == 1 else float(cortes[t - 2])
        alto = float(cortes[t - 1]) if t < N_TERCILES else 90.0
        for posicion in ("todos", "costado", "punta"):
            if posicion == "costado":
                sel = (tipo == 1) & (tercil == t)
            elif posicion == "punta":
                sel = (tipo == 2) & (tercil == t)
            else:
                sel = ((tipo == 1) | (tipo == 2)) & (tercil == t)
            n = int((ok & sel).sum())
            b = brecha(idx, grupo, tipo, sel, ctl)
            if n >= MIN_TERCIL_IC:
                def fun(ix, g, ti, ba, _t=t, _p=posicion):
                    ctl_r = control_por_edad(ix, g, ti)
                    if _p == "costado":
                        s = (ba == _t) & (ti == 1)
                    elif _p == "punta":
                        s = (ba == _t) & (ti == 2)
                    else:
                        s = (ba == _t) & ((ti == 1) | (ti == 2))
                    return brecha(ix, g, ti, s, ctl_r)
                bajo_ic, alto_ic = ic(fun, idx, grupo, tipo, banda_tercil, ev["bloque5"], REPS, semilla)
            else:
                bajo_ic, alto_ic = float("nan"), float("nan")
            filas.append((t, bajo, alto, posicion, n, b, bajo_ic, alto_ic))
    return filas


def calcular(D: dict) -> dict:
    """Calcula los modelos y las tablas que se publican."""
    ev1 = eventos(D, BASE_PRINCIPAL, (K_PRINCIPAL,))
    evL = eventos(D, BASE_PLACEBO, KS_SERIE)
    ev05 = eventos(D, BASE_PRINCIPAL, (K_PRINCIPAL,), solape_costado=SOLAPE_COSTADO_SENSIBILIDAD)
    planes = [("principal", ev1, K_PRINCIPAL, True, SOLAPE_COSTADO_PRINCIPAL),
              ("placebo", evL, K_PLACEBO, True, SOLAPE_COSTADO_PRINCIPAL),
              ("k1_base_limpia", evL, K_PRINCIPAL, True, SOLAPE_COSTADO_PRINCIPAL)]
    for k in KS_SERIE:
        planes.append(("serie_base_limpia", evL, k, True, SOLAPE_COSTADO_PRINCIPAL))
    planes.append(("sin_pesar", ev1, K_PRINCIPAL, False, SOLAPE_COSTADO_PRINCIPAL))
    planes.append(("costado_05", ev05, K_PRINCIPAL, True, SOLAPE_COSTADO_SENSIBILIDAD))
    resultados, filas_contraste = [], []
    for j, (nombre, ev, k, pond, solape_c) in enumerate(planes):
        r = modelo(ev, k, pond, solape_c, SEMILLA_MECANISMO + j)
        r["modelo"] = nombre
        resultados.append(r)
        filas_contraste.append((nombre, k, r["n_costado"], r["n_punta"], r["n_control"], r["n_bandas"], r["delta"],
                                r["ic_bajo_5km"], r["ic_alto_5km"], r["ic_bajo_pad"], r["ic_alto_pad"],
                                r["ic_bajo_2km"], r["ic_alto_2km"], r["bloques_5km"], r["pads"]))
    por_nombre = {}
    for r in resultados:
        por_nombre.setdefault(r["modelo"], r)
    filas_banda = []
    for nombre in ("principal", "placebo", "k1_base_limpia"):
        r = por_nombre[nombre]
        for b in r["bandas"]:
            filas_banda.append((nombre, ETIQUETAS_BANDA[b["banda"]], r["k"], b["n_costado"], b["n_punta"],
                                b["gap_costado"], b["gap_punta"], b["delta"], b["peso"]))
    filas_shmax = _tabla_shmax(ev1, K_PRINCIPAL, SEMILLA_MECANISMO)
    # muestra por ano de fractura del hijo (modelo principal)
    idx = np.asarray(ev1["idx"][K_PRINCIPAL], dtype=float)
    tipo, _banda = tipos(ev1, SOLAPE_COSTADO_PRINCIPAL)
    ok = ~np.isnan(idx)
    anios = np.asarray(ev1["anio"])
    filas_muestra = []
    for anio in sorted({int(a) for a in anios[ok]}):
        sel = ok & (anios == anio)
        filas_muestra.append((anio, int((sel & (tipo == 1)).sum()), int((sel & (tipo == 2)).sum()),
                              int((sel & (tipo == 3)).sum())))
    # veredicto: el modelo principal con el IC del placebo
    pr, pl = por_nombre["principal"], por_nombre["placebo"]
    v = veredicto(pr["n_costado"], pr["n_punta"], pr["n_bandas"], pr["ic_alto_5km"], pl["ic_bajo_5km"], pl["ic_alto_5km"])
    filas_veredicto = [(v, pr["n_costado"], pr["n_punta"], pr["n_bandas"], pr["delta"], pr["ic_bajo_5km"], pr["ic_alto_5km"],
                        pl["delta"], pl["ic_bajo_5km"], pl["ic_alto_5km"], pr["eventos_cercanos"], pr["n_control"],
                        pr["bloques_5km"])]
    return {"contraste": filas_contraste, "banda": filas_banda, "shmax": filas_shmax, "muestra": filas_muestra,
            "veredicto": filas_veredicto, "modelos": por_nombre}


# ------------------------------------------------------------------ tablas

COLS_CONTRASTE = [("modelo", "VARCHAR"), ("k", "INTEGER"), ("n_costado", "INTEGER"), ("n_punta", "INTEGER"),
                  ("n_control", "INTEGER"), ("bandas", "INTEGER"), ("contraste", "DOUBLE"), ("ic_bajo_5km", "DOUBLE"),
                  ("ic_alto_5km", "DOUBLE"), ("ic_bajo_pad", "DOUBLE"), ("ic_alto_pad", "DOUBLE"),
                  ("ic_bajo_2km", "DOUBLE"), ("ic_alto_2km", "DOUBLE"), ("bloques_5km", "INTEGER"), ("pads", "INTEGER")]
COLS_BANDA = [("modelo", "VARCHAR"), ("banda", "VARCHAR"), ("k", "INTEGER"), ("n_costado", "INTEGER"),
              ("n_punta", "INTEGER"), ("gap_costado", "DOUBLE"), ("gap_punta", "DOUBLE"), ("contraste", "DOUBLE"),
              ("peso", "INTEGER")]
COLS_SHMAX = [("tercil", "INTEGER"), ("corte_bajo", "DOUBLE"), ("corte_alto", "DOUBLE"), ("posicion", "VARCHAR"),
              ("n", "INTEGER"), ("brecha", "DOUBLE"), ("ic_bajo", "DOUBLE"), ("ic_alto", "DOUBLE")]
COLS_MUESTRA = [("anio", "INTEGER"), ("n_costado", "INTEGER"), ("n_punta", "INTEGER"), ("n_control", "INTEGER")]
COLS_VEREDICTO = [("veredicto", "VARCHAR"), ("n_costado", "INTEGER"), ("n_punta", "INTEGER"), ("bandas", "INTEGER"),
                  ("contraste", "DOUBLE"), ("ic_bajo", "DOUBLE"), ("ic_alto", "DOUBLE"), ("placebo", "DOUBLE"),
                  ("placebo_ic_bajo", "DOUBLE"), ("placebo_ic_alto", "DOUBLE"), ("eventos_cercanos", "INTEGER"),
                  ("controles", "INTEGER"), ("bloques_5km", "INTEGER")]


TEXTO_VEREDICTO = {
    "sostiene": "Entre los padres cercanos (menos de 1.000 m entre ramas) y paralelos, el que queda al costado de la rama del hijo "
                "rinde menos al mes 1 que el que queda en su punta, y el mismo contraste antes de la fractura (mes -1) tiene un "
                "intervalo que incluye cero. Es una huella medida compatible con un efecto de la geometría de las ramas; no es una "
                "prueba de causa ni una medición de esfuerzos.",
    "ubicación": "El costado rinde menos que la punta al mes 1, pero el mismo contraste ya se separaba de cero antes de la fractura "
                 "(mes -1): la diferencia viene de dónde están los pozos y no del mecanismo.",
    "no firme": "El contraste entre el costado y la punta al mes 1 no se separa de cero con el intervalo fijado (o tiene el signo "
                "contrario al del mecanismo): ni con la geometría de las ramas se sostiene un mecanismo direccional.",
    "sin muestra": "Hay menos de 80 eventos en el costado o en la punta: no hay veredicto.",
}

MODELOS_TXT = {
    "principal": "Principal (decide)",
    "placebo": "Placebo en k = -1, base de los meses -6 a -4",
    "k1_base_limpia": "k = 1 con la base limpia",
    "serie_base_limpia": "Serie con la base limpia",
    "sin_pesar": "Principal sin pesar por eventos",
    "costado_05": "Costado con solape de 0,5 o más",
}


def cobertura_ramas(con) -> tuple[int, int, int, int] | None:
    """Porcentaje de hijos con rama medida (medidos sobre total de `mart_trayectoria_cobertura`, nivel hijo): minimo y maximo de 2016
    a 2023, y los de 2024 y 2025. None si el mart no esta (la pagina dice entonces que la cobertura esta en trayectorias.md)."""
    try:
        filas = con.execute("select anio, medidos, total from mart_trayectoria_cobertura where nivel = 'hijo' "
                            "and anio between 2016 and 2025 and total > 0").fetchall()
    except duckdb.Error:
        return None
    pct = {a: 100.0 * m / t for a, m, t in filas}
    if not all(a in pct for a in range(2016, 2026)):
        return None
    viejos = [pct[a] for a in range(2016, 2024)]
    return round(min(viejos)), round(max(viejos)), round(pct[2024]), round(pct[2025])


def _texto_cobertura(con) -> str:
    c = cobertura_ramas(con)
    if c is None:
        return ("la cobertura de las ramas medidas por año de fractura del hijo está en trayectorias.md y cae en los años "
                "recientes, así que la muestra es sobre todo de los años anteriores")
    return (f"las ramas medidas cubren de {c[0]} a {c[1]}% de los hijos fracturados de 2016 a 2023 pero solo {c[2]}% de los de "
            f"2024 y {c[3]}% de los de 2025")


def _limite_placebo_banda(bandas: list[tuple]) -> list[str]:
    """Linea de Limites sobre el placebo por banda: el contraste del mes -1 en la banda de 0 a 300 m, que el promedio del veredicto
    no muestra por separado, junto con el contraste y el peso de esa banda en el mes 1 (todo leido de `mart_mecanismo_banda`)."""
    cerca = [r for r in bandas if r[0] == "placebo" and r[1] == ETIQUETAS_BANDA[0] and r[7] == r[7]]
    prin = [r for r in bandas if r[0] == "principal"]
    banda1 = [r for r in prin if r[1] == ETIQUETAS_BANDA[0]]
    if not cerca or not banda1:
        return []
    peso_total = sum(r[8] for r in prin)
    return [f"- El placebo por banda no es plano en la banda de 0 a 300 m: allí el contraste del mes -1 ya es de {_g(100 * cerca[0][7], 1)} "
            f"puntos (sin IC por banda). El veredicto decide con el promedio ponderado de las tres bandas; en esa banda el contraste "
            f"del mes 1 es de {_g(100 * banda1[0][7], 1)} puntos y pesa {_g(banda1[0][8])} de {_g(peso_total)} eventos en el promedio."]


def _limite_cierre_preventivo() -> list[str]:
    """Linea de Limites: con datos mensuales de caudal, un cierre preventivo del padre cercano no se separa de la geometria."""
    return ["- Con datos mensuales de caudal, un cierre preventivo del padre que queda al costado mientras se fractura el hijo da el "
            "mismo contraste sin que intervenga la geometría de la roca: la prueba no separa la geometría de las ramas de esa "
            "decisión del operador (el índice cuenta días calendario, así que los días cerrados también bajan el caudal)."]


def pagina_mecanismo(con) -> str:
    """Pagina de wiki de la prueba de la geometria de las ramas; lee los cinco marts de la prueba."""
    g = _g

    def pts(x, dec=1):
        return g(100 * x, dec)

    def ic_txt(a, b):
        if a is None or b is None or a != a or b != b:
            return "n/d"
        return f"{pts(a)} a {pts(b)}"

    ver = con.execute("select * from mart_mecanismo_veredicto").fetchone()
    if ver is None:
        raise ValueError("falta mart_mecanismo_veredicto")
    (v, n_costado, n_punta, n_bandas, c1, c1_b, c1_a, pl, pl_b, pl_a,
     n_cercanos, n_controles, n_bloques) = ver
    filas_cont = con.execute("select * from mart_mecanismo_contraste").fetchall()
    cont = {(r[0], r[1]): r for r in filas_cont}
    prin = cont[("principal", 1)]
    bandas = con.execute("select * from mart_mecanismo_banda").fetchall()
    shmax = con.execute("select * from mart_mecanismo_shmax").fetchall()
    muestra = con.execute("select * from mart_mecanismo_muestra").fetchall()
    serie = {r[1]: r for r in filas_cont if r[0] == "serie_base_limpia"}
    bandas_prin = [r for r in bandas if r[0] == "principal"]

    if pl_b <= 0.0 <= pl_a:
        lejos = max(abs(pl_b), abs(pl_a))
        frase_placebo = (f"Un IC que incluye cero no descarta una diferencia previa: el límite más lejano de cero es "
                         f"{pts(lejos)} puntos, una cota superior de lo que ya podía haber antes.")
    else:
        cerca = min(abs(pl_b), abs(pl_a))
        frase_placebo = (f"El IC no incluye cero: la diferencia ya estaba antes de la fractura, y el límite más cercano de cero "
                         f"es {pts(cerca)} puntos.")

    L = ["# Mecanismo por la geometría de las ramas", "",
         "Página generada por `pipeline/mecanismo.py`. Prueba nueva: la posición del padre se mide respecto de la rama de cada "
         "hijo (su costado o su punta), no respecto de la disposición de pads de la cuenca. No es una repetición del eje de la "
         "brújula, que sigue retirado, y no mide esfuerzos.", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada: **{v}**. {TEXTO_VEREDICTO.get(v, '')}", ""]
    partes = ", de ".join(f"{pts(r[7])} puntos en la banda de {r[1]} ({_g(r[3])} costados, {_g(r[4])} puntas)"
                          for r in bandas_prin)
    n_1623 = sum(r[1] + r[2] for r in muestra if 2016 <= r[0] <= 2023)
    pct = 100.0 * n_1623 / n_cercanos if n_cercanos else 0.0
    L += [f"- Contraste costado menos punta al mes 1 (principal): {pts(c1)} puntos (IC 95% por bloques de 5 km: "
          f"{pts(c1_b)} a {pts(c1_a)}), sobre {_g(n_costado)} costados y {_g(n_punta)} puntas y {_g(n_bloques)} bloques.",
          f"- Mismo contraste en el mes -1 con la base de los meses -6 a -4: {pts(pl)} puntos (IC 95% por bloques de 5 km: "
          f"{pts(pl_b)} a {pts(pl_a)}). {frase_placebo}",
          f"- En la serie con la base limpia el contraste vale {pts(serie[-3][6])} puntos en el mes -3, {pts(serie[-2][6])} puntos "
          f"en el mes -2 y {pts(serie[0][6])} puntos en el mes 0.",
          f"- Por banda de distancia entre ramas, el contraste del mes 1 es de {partes}.",
          f"- El mismo contraste con otros intervalos: por pads hijo, de {pts(prin[9])} a {pts(prin[10])}; por bloques de 2 km, de "
          f"{pts(prin[11])} a {pts(prin[12])}.",
          f"- Sin pesar por eventos: {pts(cont[('sin_pesar', 1)][6])} puntos; con el costado definido por un solape de 0,5 o más: "
          f"{pts(cont[('costado_05', 1)][6])} puntos.",
          f"- Muestra: {_texto_cobertura(con)}, así que la muestra es sobre todo de 2016 a 2023.",
          f"- De los {_g(n_cercanos)} eventos cercanos del modelo principal, {_g(pct, 1)}% corresponden a hijos fracturados de "
          "2016 a 2023.", "",
          "## Regla fijada antes de correr", "",
          "Eventos: los pares de `mart_trayectoria_par` con el padre que cumple la regla de edad del estudio principal; un evento "
          "es un padre y el mes de fractura del hijo, y el hijo que lo fija es el de menor distancia entre ramas. Muestra: padres a "
          "menos de 1.000 m entre ramas, en paralelo (20 grados o menos de diferencia de azimut) y con posición clara de costado o "
          "de punta; bandas de 0 a 300, de 300 a 600 y de 600 a 1.000 m. Control lateral: los padres cuyo hijo más cercano queda a "
          "2.000 m o más de la rama del padre, comparados por la edad del padre en el mes del evento (6 a 11, 12 a 23, 24 a 47, 48 "
          "meses o más) y por el mismo mes, con al menos 5 controles por grupo de edad. Estimador: cada padre indexado contra su "
          "propia base, brecha entre medianas contra el control de su grupo de edad, y el contraste como la brecha del costado "
          "menos la brecha de la punta en cada banda, promediado por los eventos de cada banda; una banda con menos de 5 eventos en "
          "el costado o en la punta no entra. IC 95%: bootstrap de percentiles que remuestrea bloques de 5 km, con semilla fija. "
          "Veredicto: sin muestra si hay menos de 80 eventos en el costado o en la punta; sostiene si el IC del contraste del mes 1 "
          "queda entero por debajo de cero y el placebo del mes -1 tiene un IC que incluye cero; ubicación si el placebo también "
          "excluye cero; no firme en cualquier otro caso. Placebo: el mismo contraste en el mes -1 con la base limpia de los meses "
          "-6 a -4. La regla se fijó en el commit bddf1e0771 de la rama de esta prueba, antes de calcular ninguna cifra.", "",
          "## Resultados", "",
          "Todos los modelos calculados. El contraste es el del costado menos la punta, en puntos: negativo significa que el "
          "costado rinde menos. Las filas del mes -1 (el placebo y la serie con la base limpia) usan los mismos eventos y el mismo "
          "estimador, y sus intervalos difieren solo por la semilla del bootstrap.", "",
          "| Modelo | k | Costados | Puntas | Contraste (puntos) | IC 95% por bloques de 5 km | IC 95% por pads | IC 95% por "
          "bloques de 2 km |",
          "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |"]
    for r in filas_cont:
        L.append(f"| {MODELOS_TXT.get(r[0], r[0])} | {r[1]} | {_g(r[2])} | {_g(r[3])} | {pts(r[6])} | {pts(r[7])} a {pts(r[8])} | "
                 f"{pts(r[9])} a {pts(r[10])} | {pts(r[11])} a {pts(r[12])} |")
    L += ["", "Contraste por banda de distancia entre ramas, en puntos. El peso es el número de eventos de la banda (costados más "
          "puntas).", "",
          "| Modelo | Banda | k | Costados | Puntas | Brecha costado | Brecha punta | Contraste | Peso |",
          "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in bandas:
        L.append(f"| {MODELOS_TXT.get(r[0], r[0])} | {r[1]} | {r[2]} | {_g(r[3])} | {_g(r[4])} | {pts(r[5])} | {pts(r[6])} | "
                 f"{pts(r[7])} | {_g(r[8])} |")
    L += ["", "Brecha del mes 1 por tercil del ángulo al SHmax del hijo (67,5 grados desde el norte). Descriptivo: no decide nada.", "",
          "| Tercil | Ángulo al SHmax (grados) | Posición | Eventos | Brecha al mes 1 (puntos) | IC 95% |",
          "| ---: | --- | --- | ---: | ---: | --- |"]
    for r in shmax:
        L.append(f"| {r[0]} | {_g(r[1], 1)} a {_g(r[2], 1)} | {r[3]} | {_g(r[4])} | {pts(r[5])} | {ic_txt(r[6], r[7])} |")
    cortes = {r[0]: r[2] for r in shmax if r[3] == "todos"}
    L += ["", f"Los cortes de los terciles son {_g(cortes.get(1), 1)} y {_g(cortes.get(2), 1)} grados: casi todas las ramas de la "
          "muestra son norte sur y el ángulo al SHmax casi no varía, así que esta tabla es descriptiva y no prueba ninguna "
          "dirección.", "",
          "Eventos por año de la fractura del hijo, en la muestra del contraste y en el control lateral.", "",
          "| Año | Costados | Puntas | Controles |", "| ---: | ---: | ---: | ---: |"]
    for r in muestra:
        L.append(f"| {r[0]} | {_g(r[1])} | {_g(r[2])} | {_g(r[3])} |")
    L += ["", "## Límites", "",
          "- Es una asociación medida, no la causa: el costado y la punta pueden diferir en lo que el contraste no ve (profundidad, "
          "unidad navegada, tamaño de la fractura, tiempo desde la puesta en producción del padre).",
          "- La prueba placebo del mes -1 cubre las diferencias que ya existían antes de la fractura, no las que aparecen justo "
          "con ella.",
          *_limite_placebo_banda(bandas),
          *_limite_cierre_preventivo(),
          f"- La muestra es sobre todo de 2016 a 2023: {_texto_cobertura(con)}.",
          "- Solo entran los pares con las dos ramas medidas y con menos de 5 km de superficie: un padre cuya rama no se publicó "
          "queda afuera, tanto de la muestra cercana como del control lateral, y un control puede tener otro hijo cercano cuya "
          "rama no se publicó (pesa más en 2024 y 2025, donde la cobertura es menor).",
          "- La posición y el paralelismo se miden entre los ejes principales de las ramas en planta, sin la profundidad.",
          "- Los IC no tienen ajuste por comparaciones múltiples, y los eventos de un mismo padre con varios hijos no son "
          "independientes: un mismo padre puede aportar al costado o a la punta con un hijo cercano y al control lateral con otro "
          "hijo a más de 2.000 m en otro mes, así que el control no es un grupo de padres aparte del grupo tratado. El bootstrap "
          "por bloques de 5 km remuestrea juntos esos eventos, pero esa dependencia no se midió por separado.",
          "- El veredicto sale solo del modelo principal; todos los demás modelos se publican y no deciden nada.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    """Corre el mecanismo sobre el warehouse y escribe las cinco tablas."""
    con = duckdb.connect(str(path))
    R = calcular(cargar(con))
    _escribir(con, "mart_mecanismo_contraste", COLS_CONTRASTE, R["contraste"])
    _escribir(con, "mart_mecanismo_banda", COLS_BANDA, R["banda"])
    _escribir(con, "mart_mecanismo_shmax", COLS_SHMAX, R["shmax"])
    _escribir(con, "mart_mecanismo_muestra", COLS_MUESTRA, R["muestra"])
    _escribir(con, "mart_mecanismo_veredicto", COLS_VEREDICTO, R["veredicto"])
    v = R["veredicto"][0]
    print(f"[mecanismo] veredicto: {v[0]} | contraste k=1 {v[4]:+.4f} (IC {v[5]:+.4f} a {v[6]:+.4f}) | "
          f"placebo k=-1 {v[7]:+.4f} (IC {v[8]:+.4f} a {v[9]:+.4f}) | n_costado {v[1]} n_punta {v[2]} bandas {v[3]} "
          f"eventos_cercanos {v[10]} controles {v[11]} bloques_5km {v[12]}")
    for nombre in ("principal", "placebo"):
        r = R["modelos"][nombre]
        print(f"[mecanismo] {nombre:9} k={r['k']:2d} contraste {r['delta']:+.4f} "
              f"IC 5km [{r['ic_bajo_5km']:+.4f}, {r['ic_alto_5km']:+.4f}] "
              f"IC pad [{r['ic_bajo_pad']:+.4f}, {r['ic_alto_pad']:+.4f}] "
              f"IC 2km [{r['ic_bajo_2km']:+.4f}, {r['ic_alto_2km']:+.4f}] "
              f"n_costado {r['n_costado']} n_punta {r['n_punta']} n_control {r['n_control']} "
              f"bandas {r['n_bandas']} bloques_5km {r['bloques_5km']} pads {r['pads']}")
    con.close()


if __name__ == "__main__":
    main()
