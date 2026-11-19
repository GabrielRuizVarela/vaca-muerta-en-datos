"""El lado del hijo: un pozo fracturado cerca de pozos que ya produjeron mucho, rinde menos petroleo por metro a 12 meses?

Se corre despues de pipeline.build:  uv run python -m pipeline.hijo

REGLA FIJADA ANTES DE CORRER (2026-11-15, antes de calcular ninguna cifra de resultado; no se cambia despues de ver resultados).
Fuente: docs/proceso/investigacion-fase3.md, seccion 3.10 (se omite la "Variante" del cierre preventivo).

Pregunta: a igualdad de area, cohorte y diseno de fractura, un pozo cuya fractura se hizo a menos de 1 km (superficie) de pozos
con mucho petroleo acumulado, produce menos petroleo por metro de rama en sus primeros 12 meses que un pozo en zona virgen.

Unidad y muestra: pozo en mart_pozo_12m (petrolifero de shale de Vaca Muerta con 12 meses publicados), con rama horizontal > 0,
etapas, arena, area, pad, coordenadas y fecha de primera fractura (dim_fractura_pozo). El mes de fractura es el mes de
primera_fractura. Se exige que el mes de la primera produccion de petroleo caiga entre 0 y 12 meses despues del mes de fractura:
fuera de eso hay refracturas o fechas dudosas. Se publica cuantos pozos sale en cada paso (mart_hijo_muestra).

Exposicion (continua): petroleo acumulado, en barriles, de los pozos de int_pozo_mop (los mismos petroliferos de shale) a menos de
1 km de distancia de superficie del hijo (formula equirectangular de int_pozo_arista), distintos del hijo, contando solo los meses
de produccion ANTERIORES al mes de fractura del hijo (se excluye el mes de la fractura y los siguientes). Se incluyen los pozos del
mismo pad que ya producian. La exposicion se divide por los metros de rama del hijo: barriles por metro de rama del hijo.
  * Continua: la exposicion en unidades de 100 barriles por metro.
  * Tres grupos (misma exposicion por metro): 1 virgen = exposicion cero; 2 poco depletado = exposicion positiva hasta la
    mediana de las exposiciones positivas; 3 muy depletado = exposicion positiva mayor que esa mediana. Los cortes se calculan una
    vez con todos los hijos de la muestra. Si hay menos de MIN_VIRGENES = 50 hijos con exposicion cero, se dice y se usan los
    terciles de la exposicion de todos los hijos (grupo 1 hasta q33, 2 hasta q67, 3 por encima).

Resultado: petroleo de 12 meses por metro de rama (petroleo_12m_bbl / rama_horizontal_m), en barriles por metro.

Modelo principal: minimos cuadrados con efectos fijos de area por cohorte (cohorte = ano del primer petroleo; las celdas se absorben
centrando), controles rama horizontal, arena por metro, etapas y operador (YPF, las operadoras con 30 o mas hijos por separado, el
resto agrupado), indicadores de los grupos 2 y 3 con el grupo 1 de referencia. Errores robustos agrupados por pad (CR1, normal,
IC 95%). Coeficiente primario: el del grupo 3 (muy depletado) contra el 1, en barriles por metro y en porcentaje de la MEDIANA del
rendimiento del grupo 1 (virgen) en la muestra del modelo. La regresion es de medias; la mediana es el denominador fijado por la regla.

Prueba de equilibrio, ANTES del resultado: para cada variable de diseno (rama, etapas, arena por metro) y de ubicacion (cohorte, YPF,
latitud, longitud y numero de pozos de shale a menos de 5 km, sin mirar fechas, como indicador de nucleo contra borde del desarrollo)
se publica la media por grupo y el p de la prueba conjunta (Wald, chi cuadrado de 2 grados, errores por pad) de que los grupos 2 y 3
no difieren del 1, dentro de las celdas de area por cohorte (p) y sin celdas (p_sin_celdas). No condiciona el veredicto.

CONTROL NEGATIVO: la misma exposicion medida con pozos que no pueden haber depletado al hijo. Pozos a menos de 1 km con primera
produccion de petroleo posterior a la fractura del hijo y, ademas, posterior al ultimo mes de la ventana de resultado del hijo (su mes
de primera produccion mas 11 meses): un pozo que empieza dentro de la ventana podria interferir con el hijo (el efecto de padre que
el proyecto mide), y eso no seria un control. Su exposicion es el petroleo acumulado de esos pozos hasta el ultimo mes con datos, por
metro de rama del hijo. Mismos grupos (virgen = cero; poco y muy por la mediana de las exposiciones positivas del control, calculada
aparte), mismo modelo y misma muestra. El control negativo es NULO si el IC 95% del coeficiente del grupo 3 incluye cero; NO es nulo
si lo excluye (con cualquier signo).

Minimos (si no se cumplen no se calcula veredicto y se informa "sin muestra"): 50 hijos y 20 pads en el grupo 1 y en el grupo 3 de
la exposicion real, y 100 pads en la muestra. MIN_HIJOS_GRUPO = 50, MIN_PADS_GRUPO = 20, MIN_PADS = 100.

VEREDICTO (regla de la seccion 3.10, fijada; "punto" es el coeficiente del grupo 3 del modelo principal, "virgen" la mediana del
rendimiento del grupo 1):
  * falsa la degradacion del hijo ("no se sostiene"): el IC 95% del punto incluye cero Y |punto| es menor que 5% de virgen Y el
    control negativo es nulo.
  * sostiene ("los hijos cerca de padres depletados rinden menos, asociacion con control de diseno"): el IC 95% del punto esta por
    debajo de cero (el grupo muy depletado rinde menos con IC que excluye cero) Y el control negativo es nulo. Se informa en bbl por
    metro y en porcentaje de virgen.
  * ubicacion: el IC del punto esta por debajo de cero Y el control negativo tampoco es nulo: la asociacion es de ubicacion (nucleo
    contra borde), no de depleccion.
  * no firme: cualquier otro caso (por ejemplo IC que incluye cero con |punto| de 5% de virgen o mas, IC que incluye cero con el
    control negativo no nulo, o IC por encima de cero).
Es la hipotesis `hijo_depletado` del libro: valor = limite superior del IC del punto, en bbl por metro, si el control negativo es
nulo; con el control negativo no nulo no hay valor. Expectativa: menor que 0.
Aclaracion posterior a los resultados (correccion del juez, 2026-11-15; no cambia la regla, ningun umbral ni ninguna estimacion):
el estado de la hipotesis en el libro sale del veredicto de esta regla y no del valor: sostiene = confirmado, no se sostiene =
refutado, y ubicacion, no firme y sin muestra = no firme. La codificacion del valor es la preregistrada de arriba.

Se publican ademas, como filas descriptivas y sin veredicto propio: la regresion con la exposicion continua (real y de control
negativo) y el modelo principal por separado para YPF y para el resto, con los mismos cortes de grupo.

Que NO prueba:
  * La distancia es de superficie: las ramas miden de 1.500 a 3.200 m y no hay trayectorias ni zona de aterrizaje. Un pozo a 1 km de
    superficie puede estar a 100 m o a 3 km en el subsuelo, y puede estar en otra zona apilada.
  * El espaciamiento entre ramas no se observa, asi que no se separa depleccion de espaciamiento.
  * Nucleo contra borde: el desarrollo denso esta donde la roca es mejor o peor; el control negativo mira ese riesgo, pero no lo
    elimina (la ubicacion futura y la pasada no son la misma).
  * No es una afirmacion causal: es una asociacion con control de diseno.
  * El resultado de 12 meses deja fuera a los pozos recientes (necesitan 12 meses publicados).
"""
from __future__ import annotations

import math

import duckdb
import numpy as np

from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

BBL_POR_M3 = 6.2898
RADIO_KM = 1.0
RADIO_DENSIDAD_KM = 5.0
VENTANA_MESES = 12          # el resultado cuenta los meses 1 a 12 desde el primer petroleo
LAG_MAX_MESES = 12          # meses entre la fractura y el primer petroleo
MIN_VIRGENES = 50
MIN_HIJOS_GRUPO = 50
MIN_PADS_GRUPO = 20
MIN_PADS = 100
MIN_HIJOS_OPERADOR = 30
UMBRAL_FALSA = 0.05         # fraccion del rendimiento virgen
ESCALA_CONTINUA = 100.0     # bbl por metro
Z95 = 1.959963984540054

ETIQUETAS = {1: "virgen", 2: "poco depletado", 3: "muy depletado"}
TERMINOS = {2: "poco_depletado", 3: "muy_depletado"}
TERMINO_CONTINUA = "exposicion_por_100_bbl_m"

COLS_GRUPOS = [("grupo", "integer"), ("exposicion", "varchar"), ("etiqueta", "varchar"), ("hijos", "integer"), ("pads", "integer"),
               ("expo_min_bbl_m", "double"), ("expo_max_bbl_m", "double"), ("rend_12m_mediana_bbl_m", "double"),
               ("rend_12m_media_bbl_m", "double")]
COLS_COEF = [("modelo", "varchar"), ("termino", "varchar"), ("coef_bbl_m", "double"), ("pct_del_virgen", "double"),
             ("ic_bajo", "double"), ("ic_alto", "double"), ("n", "integer"), ("conglomerados", "integer"), ("p", "double"),
             ("pct_ic_bajo", "double"), ("pct_ic_alto", "double"), ("virgen_mediana_bbl_m", "double"), ("veredicto", "varchar")]
COLS_EQUILIBRIO = [("variable", "varchar"), ("grupo1", "double"), ("grupo2", "double"), ("grupo3", "double"), ("p", "double"),
                   ("p_sin_celdas", "double")]
COLS_MUESTRA = [("paso", "integer"), ("descripcion", "varchar"), ("hijos", "integer")]


# ------------------------------------------------------------------ datos

def mes_idx(d) -> int:
    return d.year * 12 + d.month - 1


def cargar(con) -> dict:
    """Hijos (con la cuenta de cada paso de seleccion), pozos expositores y su produccion mensual en barriles."""
    filas = con.execute("""
        select m.pozo_id, m.operador, m.cohorte, m.petroleo_12m_bbl, m.rama_horizontal_m, m.etapas, m.arena_tn,
               u.area, u.lat, u.lon, u.pad_id, u.primer_mes_petroleo, f.primera_fractura
        from mart_pozo_12m m
        left join int_pozo_ubicacion u using (pozo_id)
        left join dim_fractura_pozo f using (pozo_id)
        order by m.pozo_id""").fetchall()
    pasos = [("mart_pozo_12m (petrolíferos de shale con 12 meses)", len(filas))]
    f1 = [r for r in filas if r[7] is not None and r[8] is not None and r[9] is not None and r[10] is not None
          and r[11] is not None]
    pasos.append(("con área, pad, coordenadas y primer petróleo", len(f1)))
    f2 = [r for r in f1 if r[4] is not None and r[4] > 0 and r[5] is not None and r[6] is not None and r[3] is not None]
    pasos.append(("con rama, etapas y arena", len(f2)))
    f3 = [r for r in f2 if r[12] is not None]
    pasos.append(("con fecha de primera fractura", len(f3)))
    f4 = [r for r in f3 if 0 <= mes_idx(r[11]) - mes_idx(r[12]) <= LAG_MAX_MESES]
    pasos.append((f"primer petróleo entre 0 y {LAG_MAX_MESES} meses después de la fractura", len(f4)))
    H = {"pozo_id": np.array([r[0] for r in f4], dtype=int), "operador": np.array([r[1] for r in f4]),
         "cohorte": np.array([r[2] for r in f4], dtype=int), "y_bbl": np.array([r[3] for r in f4], dtype=float),
         "rama": np.array([r[4] for r in f4], dtype=float), "etapas": np.array([r[5] for r in f4], dtype=float),
         "arena": np.array([r[6] for r in f4], dtype=float), "area": np.array([r[7] for r in f4]),
         "lat": np.array([r[8] for r in f4], dtype=float), "lon": np.array([r[9] for r in f4], dtype=float),
         "pad": np.array([r[10] for r in f4]), "mes_pp": np.array([mes_idx(r[11]) for r in f4], dtype=int),
         "mes_frac": np.array([mes_idx(r[12]) for r in f4], dtype=int)}
    pz = con.execute("""
        select distinct m.pozo_id, u.lat, u.lon, year(u.primer_mes_petroleo) * 12 + month(u.primer_mes_petroleo) - 1
        from int_pozo_mop m join int_pozo_ubicacion u using (pozo_id)
        where u.lat is not null and u.lon is not null and u.primer_mes_petroleo is not null
        order by m.pozo_id""").fetchall()
    P = {"pozo_id": np.array([r[0] for r in pz], dtype=int), "lat": np.array([r[1] for r in pz], dtype=float),
         "lon": np.array([r[2] for r in pz], dtype=float), "mes_pp": np.array([r[3] for r in pz], dtype=int)}
    pr = con.execute(f"""
        select m.pozo_id, year(u.primer_mes_petroleo) * 12 + month(u.primer_mes_petroleo) - 1 + m.mop - 1,
               coalesce(m.petroleo_m3, 0) * {BBL_POR_M3}
        from int_pozo_mop m join int_pozo_ubicacion u using (pozo_id)
        where u.primer_mes_petroleo is not null
        order by m.pozo_id, m.mop""").fetchall()
    meses: dict[int, list] = {}
    bbl: dict[int, list] = {}
    for pid, mes, b in pr:
        meses.setdefault(pid, []).append(mes)
        bbl.setdefault(pid, []).append(b)
    P["meses"] = [np.array(meses.get(int(p), []), dtype=int) for p in P["pozo_id"]]
    P["cum"] = [np.concatenate([[0.0], np.cumsum(bbl.get(int(p), []))]) for p in P["pozo_id"]]
    return {"H": H, "P": P, "pasos": pasos}


# ------------------------------------------------------------------ exposicion

def vecinos(lat_a, lon_a, lat_b, lon_b, radio_km: float, por_bloque: int = 400) -> tuple[np.ndarray, np.ndarray]:
    """Pares (i, j) con el punto j de B a menos de `radio_km` del punto i de A, con la distancia de superficie de
    int_pozo_arista (111,32 km por grado, longitud escalada por el coseno de la latitud de A)."""
    ia, ib = [], []
    for s in range(0, len(lat_a), por_bloque):
        la, lo = lat_a[s:s + por_bloque, None], lon_a[s:s + por_bloque, None]
        d = 111.32 * np.sqrt(((lon_b[None, :] - lo) * np.cos(np.radians(la))) ** 2 + (lat_b[None, :] - la) ** 2)
        i, j = np.nonzero(d < radio_km)
        ia.append(i + s)
        ib.append(j)
    if not ia:
        return np.zeros(0, dtype=int), np.zeros(0, dtype=int)
    return np.concatenate(ia), np.concatenate(ib)


def pares(H: dict, P: dict, radio_km: float = RADIO_KM) -> tuple[np.ndarray, np.ndarray]:
    """Pares hijo (indice en H) y expositor (indice en P), sin el pozo consigo mismo."""
    i, j = vecinos(H["lat"], H["lon"], P["lat"], P["lon"], radio_km)
    ok = H["pozo_id"][i] != P["pozo_id"][j]
    return i[ok], j[ok]


def exposicion_real(H: dict, P: dict, i: np.ndarray, j: np.ndarray) -> np.ndarray:
    """Barriles acumulados de los expositores en los meses ANTERIORES al mes de fractura de cada hijo (el mes de la fractura y los
    siguientes no cuentan)."""
    v = np.zeros(len(i))
    for n in range(len(i)):
        m, c = P["meses"][j[n]], P["cum"][j[n]]
        v[n] = c[int(np.searchsorted(m, H["mes_frac"][i[n]], side="left"))]
    return np.bincount(i, weights=v, minlength=len(H["pozo_id"]))


def exposicion_control(H: dict, P: dict, i: np.ndarray, j: np.ndarray) -> np.ndarray:
    """Control negativo: barriles acumulados (hasta el ultimo mes con datos) de los expositores cuyo primer petroleo es posterior
    al fin de la ventana de resultado del hijo (su primer petroleo mas 11 meses), o sea que ni depletaron ni interfirieron."""
    fuera = P["mes_pp"][j] > H["mes_pp"][i] + VENTANA_MESES - 1
    v = np.array([P["cum"][b][-1] for b in j[fuera]])
    return np.bincount(i[fuera], weights=v, minlength=len(H["pozo_id"]))


def cortes(expo: np.ndarray) -> tuple[str, float, float]:
    """Cortes de los tres grupos sobre la exposicion por metro: (modo, corte bajo, corte alto)."""
    if int((expo <= 0).sum()) >= MIN_VIRGENES:
        return "virgen", 0.0, float(np.median(expo[expo > 0])) if (expo > 0).any() else 0.0
    q = np.quantile(expo, [1 / 3, 2 / 3])
    return "terciles", float(q[0]), float(q[1])


def grupos(expo: np.ndarray, corte: tuple[str, float, float]) -> np.ndarray:
    """Grupo 1: expo <= corte bajo (cero en modo virgen); 2: hasta el corte alto; 3: por encima."""
    return 1 + (expo > corte[1]).astype(int) + (expo > corte[2]).astype(int)


# ------------------------------------------------------------------ regresion

def _centrar(a: np.ndarray, celda: np.ndarray, n_celdas: int) -> np.ndarray:
    cnt = np.maximum(np.bincount(celda, minlength=n_celdas), 1)
    if a.ndim == 1:
        return a - (np.bincount(celda, a, n_celdas) / cnt)[celda]
    return a - np.column_stack([np.bincount(celda, a[:, k], n_celdas) / cnt for k in range(a.shape[1])])[celda]


def ols_celdas(y: np.ndarray, X: np.ndarray, celda: np.ndarray, cluster: np.ndarray) -> dict:
    """Minimos cuadrados con efectos fijos de celda (se absorben centrando) y errores CR1 agrupados por `cluster`.

    Devuelve beta, se, cov (de las columnas de X), n, pads y celdas."""
    _, cel = np.unique(celda, return_inverse=True)
    n_cel = int(cel.max()) + 1
    yc, Xc = _centrar(y.astype(float), cel, n_cel), _centrar(X.astype(float), cel, n_cel)
    p = X.shape[1]
    beta = np.linalg.lstsq(Xc, yc, rcond=None)[0]
    u = yc - Xc @ beta
    _, cl = np.unique(cluster, return_inverse=True)
    G = int(cl.max()) + 1
    S = np.zeros((G, p))
    np.add.at(S, cl, Xc * u[:, None])
    bread = np.linalg.pinv(Xc.T @ Xc)
    n = len(y)
    gl = n - p - n_cel
    corr = (G / (G - 1)) * ((n - 1) / gl) if G > 1 and gl > 0 else float("nan")
    cov = bread @ (S.T @ S) @ bread * corr
    return {"beta": beta, "se": np.sqrt(np.maximum(np.diag(cov), 0)), "cov": cov, "n": n, "pads": G, "celdas": n_cel}


def controles(H: dict, minimo: int = MIN_HIJOS_OPERADOR) -> np.ndarray:
    """Rama, arena por metro, etapas y operador (YPF y las de 30 o mas hijos por separado; el resto agrupado)."""
    ops, cnt = np.unique(H["operador"], return_counts=True)
    grandes = [o for o, c in sorted(zip(ops, cnt), key=lambda t: (-t[1], t[0])) if c >= minimo]
    cat = np.where(np.isin(H["operador"], grandes), H["operador"], "otras")
    base = grandes[0] if grandes else "otras"
    cols = [H["rama"], H["arena"] / H["rama"], H["etapas"]]
    for c in sorted(set(cat.tolist()) - {base}):
        cols.append((cat == c).astype(float))
    return np.column_stack(cols)


def _sin_constantes(X: np.ndarray) -> np.ndarray:
    return X[:, X.std(axis=0) > 1e-12]


def _z(X: np.ndarray) -> np.ndarray:
    s = X.std(axis=0)
    return (X - X.mean(axis=0)) / np.where(s > 1e-12, s, 1.0)


def ajustar(y: np.ndarray, termino: np.ndarray, C: np.ndarray, celda: np.ndarray, cluster: np.ndarray) -> dict:
    """Ajusta y sobre las columnas de `termino` mas los controles C (estandarizados; se descartan los que no varian)."""
    C = _sin_constantes(C)
    X = np.column_stack([termino, _z(C)]) if C.shape[1] else termino
    r = ols_celdas(y, X, celda, cluster)
    k = termino.shape[1]
    r["b"], r["e"] = r["beta"][:k], r["se"][:k]
    return r


def _p_normal(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2)) if np.isfinite(z) else float("nan")


def p_conjunto(b: np.ndarray, cov: np.ndarray) -> float:
    """Wald de que todos los coeficientes son cero; con 2 grados de libertad el p es exp(-W/2)."""
    if len(b) != 2 or not np.all(np.isfinite(cov)) or np.allclose(cov, 0):   # sin variacion dentro de las celdas: no se define
        return float("nan")
    W = float(b @ np.linalg.pinv(cov) @ b)
    return float(math.exp(-W / 2))


# ------------------------------------------------------------------ tablas

def _celda(H: dict) -> np.ndarray:
    return np.array([f"{a}|{c}" for a, c in zip(H["area"], H["cohorte"])])


def _sub(H: dict, m: np.ndarray) -> dict:
    return {k: v[m] for k, v in H.items()}


def _fila_coef(modelo, termino, b, e, n, pads, virgen_med, veredicto=None):
    lo, hi = b - Z95 * e, b + Z95 * e
    ok = virgen_med is not None and np.isfinite(virgen_med) and virgen_med > 0

    def pc(x):
        return 100 * x / virgen_med if ok else float("nan")
    p = _p_normal(b / e) if e > 0 else float("nan")
    return (modelo, termino, float(b), pc(b), float(lo), float(hi), int(n), int(pads), float(p), pc(lo), pc(hi),
            float(virgen_med), veredicto)


def modelo_grupos(H: dict, g: np.ndarray, y: np.ndarray, modelo: str) -> tuple[list[tuple], float]:
    """Modelo con los indicadores de los grupos 2 y 3 (referencia: grupo 1). Devuelve las filas y la mediana del grupo 1."""
    nan = float("nan")
    if len(y) < 10 or len(np.unique(H["pad"])) < 3 or not (g == 1).any():   # subconjunto sin datos: filas vacias
        return [_fila_coef(modelo, TERMINOS[k], nan, nan, len(y), len(np.unique(H["pad"])), nan) for k in (2, 3)], nan
    T = np.column_stack([(g == 2).astype(float), (g == 3).astype(float)])
    r = ajustar(y, T, controles(H), _celda(H), H["pad"])
    vm = float(np.median(y[g == 1])) if (g == 1).any() else float("nan")
    return [_fila_coef(modelo, TERMINOS[k + 2], r["b"][k], r["e"][k], r["n"], r["pads"], vm) for k in (0, 1)], vm


def modelo_continuo(H: dict, expo_m: np.ndarray, y: np.ndarray, modelo: str, virgen_med: float) -> tuple:
    r = ajustar(y, (expo_m / ESCALA_CONTINUA)[:, None], controles(H), _celda(H), H["pad"])
    return _fila_coef(modelo, TERMINO_CONTINUA, r["b"][0], r["e"][0], r["n"], r["pads"], virgen_med)


def nulo(ic_bajo: float, ic_alto: float) -> bool:
    return ic_bajo <= 0 <= ic_alto


def veredicto(prin: tuple, ctrl: tuple, n_virgen: int, pads_virgen: int, n_muy: int, pads_muy: int, pads: int) -> str:
    """Veredicto con la regla fijada: sostiene / no se sostiene / ubicacion / no firme / sin muestra.

    prin y ctrl son las filas (de _fila_coef) del grupo 3 del modelo principal y del control negativo."""
    if (min(n_virgen, n_muy) < MIN_HIJOS_GRUPO or min(pads_virgen, pads_muy) < MIN_PADS_GRUPO or pads < MIN_PADS
            or not np.isfinite(prin[2]) or not np.isfinite(ctrl[2]) or not np.isfinite(prin[5]) or not np.isfinite(ctrl[5])
            or not prin[11] > 0):
        return "sin muestra"
    punto, lo, hi, virgen = prin[2], prin[4], prin[5], prin[11]
    ctrl_nulo = nulo(ctrl[4], ctrl[5])
    if nulo(lo, hi) and abs(punto) < UMBRAL_FALSA * virgen and ctrl_nulo:
        return "no se sostiene"
    if hi < 0:
        return "sostiene" if ctrl_nulo else "ubicacion"
    return "no firme"


def tabla_grupos(H: dict, expo: np.ndarray, expo_c: np.ndarray, g: np.ndarray, gc: np.ndarray) -> list[tuple]:
    y = H["y_bbl"] / H["rama"]
    nan = float("nan")
    filas = []
    for nombre, e, gg in (("real", expo, g), ("control", expo_c, gc)):
        em = e / H["rama"]
        for b in (1, 2, 3):
            s = gg == b
            filas.append((b, nombre, ETIQUETAS[b], int(s.sum()), int(len(np.unique(H["pad"][s]))),
                          float(em[s].min()) if s.any() else nan, float(em[s].max()) if s.any() else nan,
                          float(np.median(y[s])) if s.any() else nan, float(y[s].mean()) if s.any() else nan))
    return filas


def variables_equilibrio(H: dict, vecinos_5km: np.ndarray) -> list[tuple[str, np.ndarray]]:
    return [("rama_horizontal_m", H["rama"]), ("etapas", H["etapas"]), ("arena_tn_por_m", H["arena"] / H["rama"]),
            ("cohorte", H["cohorte"].astype(float)), ("ypf", (H["operador"] == "YPF").astype(float)), ("latitud", H["lat"]),
            ("longitud", H["lon"]), ("pozos_a_5_km", vecinos_5km.astype(float))]


def tabla_equilibrio(H: dict, g: np.ndarray, vecinos_5km: np.ndarray) -> list[tuple]:
    T = np.column_stack([(g == 2).astype(float), (g == 3).astype(float)])
    celda, una = _celda(H), np.zeros(len(g), dtype=int)
    filas = []
    for nombre, v in variables_equilibrio(H, vecinos_5km):
        medias = [float(v[g == b].mean()) if (g == b).any() else float("nan") for b in (1, 2, 3)]
        ps = []
        for c in (celda, una):
            r = ols_celdas(v, T, c, H["pad"])
            ps.append(p_conjunto(r["beta"], r["cov"]))
        filas.append((nombre, *medias, ps[0], ps[1]))
    return filas


def calcular(D: dict) -> dict:
    """Todos los numeros: muestra, grupos, coeficientes, equilibrio y veredicto."""
    H, P = D["H"], D["P"]
    i, j = pares(H, P)
    expo, expo_c = exposicion_real(H, P, i, j), exposicion_control(H, P, i, j)
    em, emc = expo / H["rama"], expo_c / H["rama"]
    cor, corc = cortes(em), cortes(emc)
    g, gc = grupos(em, cor), grupos(emc, corc)
    y = H["y_bbl"] / H["rama"]
    i5, _ = vecinos(H["lat"], H["lon"], P["lat"], P["lon"], RADIO_DENSIDAD_KM)
    v5 = np.bincount(i5, minlength=len(y)) - 1   # cada hijo es tambien un expositor a distancia cero
    filas_p, vm = modelo_grupos(H, g, y, "principal")
    filas_c, _ = modelo_grupos(H, gc, y, "control_negativo")

    def pads_de(s):
        return int(len(np.unique(H["pad"][s])))
    v = veredicto(filas_p[1], filas_c[1], int((g == 1).sum()), pads_de(g == 1), int((g == 3).sum()), pads_de(g == 3),
                  int(len(np.unique(H["pad"]))))
    filas_p[1] = filas_p[1][:-1] + (v,)
    coef = filas_p + filas_c
    coef.append(modelo_continuo(H, em, y, "continua", vm))
    coef.append(modelo_continuo(H, emc, y, "continua_control_negativo", vm))
    ypf = H["operador"] == "YPF"
    for nombre, m in (("principal_ypf", ypf), ("principal_resto", ~ypf)):
        coef += modelo_grupos(_sub(H, m), g[m], y[m], nombre)[0]
    return {"muestra": [(k + 1, d, n) for k, (d, n) in enumerate(D["pasos"])], "grupos": tabla_grupos(H, expo, expo_c, g, gc),
            "coef": coef, "equilibrio": tabla_equilibrio(H, g, v5), "cortes": cor, "cortes_control": corc, "veredicto": v}


# ------------------------------------------------------------------ pagina

MODELOS = {"principal": "Principal", "control_negativo": "Control negativo", "continua": "Continua",
           "continua_control_negativo": "Continua, control negativo", "principal_ypf": "Solo YPF", "principal_resto": "Resto"}
TERMINOS_TXT = {"poco_depletado": "poco depletado", "muy_depletado": "muy depletado", TERMINO_CONTINUA: "por 100 bbl/m"}
# variable, rotulo, decimales, factor
EQUILIBRIO_TXT = [("rama_horizontal_m", "Rama horizontal (m)", 0, 1.0), ("etapas", "Etapas", 1, 1.0),
                  ("arena_tn_por_m", "Arena por metro (tn/m)", 2, 1.0), ("cohorte", "Cohorte (año del primer petróleo)", 2, 1.0),
                  ("ypf", "YPF (% de los hijos)", 1, 100.0), ("latitud", "Latitud (grados)", 3, 1.0),
                  ("longitud", "Longitud (grados)", 3, 1.0), ("pozos_a_5_km", "Pozos de shale a menos de 5 km", 0, 1.0)]


def _texto_veredicto(v: str, prin: tuple, ctrl: tuple, cont_c: tuple | None = None) -> str:
    if v == "no se sostiene":
        return ("No se ve que los hijos cerca de pozos depletados rindan menos: el IC del grupo muy depletado incluye cero, el punto "
                "es menor que 5% del rendimiento virgen y el control negativo es nulo. La degradación del hijo no se sostiene con "
                "esta medición.")
    if v == "sostiene":
        return ("Los hijos cerca de padres depletados rinden menos, asociación con control de diseño: el IC del grupo muy depletado "
                "excluye cero y el control negativo es nulo.")
    if v == "ubicacion":
        return ("El grupo muy depletado rinde menos con IC que excluye cero, pero el control negativo tampoco es nulo: la asociación "
                "es de ubicación (núcleo contra borde), no de depleción.")
    if v == "sin muestra":
        return "Algún grupo no alcanza los mínimos de hijos o de pads fijados y no se calcula veredicto."
    chico = abs(prin[2]) < UMBRAL_FALSA * prin[11]
    if nulo(prin[4], prin[5]) and chico and not nulo(ctrl[4], ctrl[5]):
        return ("La regla no permite concluir en ningún sentido. El IC del grupo muy depletado incluye cero y el punto es menor que 5% "
                "del rendimiento virgen, lo que sería una falsación de la degradación, pero la falsación exige un control negativo "
                "nulo y aquí no lo es: la misma exposición medida con pozos posteriores también se asocia con el rendimiento, con "
                + ("signo positivo" if ctrl[2] > 0 else "signo negativo")
                + (", el contrario al de una degradación. Es compatible con que la ubicación, o un desarrollo posterior que sigue "
                   "a los hijos que rindieron bien, empuje el rendimiento hacia arriba y tape una degradación"
                   + ("; la versión continua del control negativo es nula, así que el control no nulo depende de los cortes por grupo"
                      if cont_c is not None and nulo(cont_c[4], cont_c[5]) else "")
                   + ". No permite leer el nulo del grupo muy depletado como ausencia de efecto." if ctrl[2] > 0 else "."))
    if nulo(prin[4], prin[5]):
        return ("La regla no permite concluir en ningún sentido: el IC del grupo muy depletado incluye cero, pero no se cumplen a la "
                "vez las condiciones de falsación (punto menor que 5% del rendimiento virgen y control negativo nulo).")
    return "La regla no permite concluir en ningún sentido: el IC del grupo muy depletado queda por encima de cero (rinde más, no menos)."


def pagina_hijo(con) -> str:
    coef = {(r[0], r[1]): r for r in con.execute("select * from mart_hijo_coef").fetchall()}
    gr = {(r[1], r[0]): r for r in con.execute("select * from mart_hijo_grupos").fetchall()}
    eq = {r[0]: r for r in con.execute("select * from mart_hijo_equilibrio").fetchall()}
    mu = con.execute("select * from mart_hijo_muestra order by paso").fetchall()
    prin, ctrl = coef[("principal", "muy_depletado")], coef[("control_negativo", "muy_depletado")]
    cont, cont_c = coef[("continua", TERMINO_CONTINUA)], coef[("continua_control_negativo", TERMINO_CONTINUA)]
    ypf, resto = coef[("principal_ypf", "muy_depletado")], coef[("principal_resto", "muy_depletado")]
    v = prin[12]
    v1 = gr[("real", 1)]
    g2, g3 = gr[("real", 2)], gr[("real", 3)]
    terciles = v1[6] > 0   # el grupo 1 no es el de exposicion cero: se usaron los terciles de todos los hijos
    pc = lambda r: f"{_g(r[3], 1)}% del rendimiento virgen (IC 95%: {_g(r[9], 1)}% a {_g(r[10], 1)}%)"  # noqa: E731
    ic = lambda r: f"IC 95%: {_g(r[4], 1)} a {_g(r[5], 1)}"  # noqa: E731
    L = ["# Hijos cerca de pozos depletados", "",
         "Página generada por `pipeline/hijo.py`. Pregunta si un pozo fracturado cerca de pozos que ya produjeron mucho rinde menos "
         "petróleo por metro de rama en sus primeros 12 meses que un pozo en zona virgen, a igualdad de área, cohorte y diseño de la "
         "fractura. Es el lado del hijo: las demás páginas miden al padre. Complementa [Interferencia entre fracturas]"
         "(interferencia.md). La regla se fijó antes de correr y está en el libro de hallazgos como `hijo_depletado`.", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada: **{v}**. {_texto_veredicto(v, prin, ctrl, cont_c)}", "",
         f"- Rendimiento de los hijos en zona virgen a 12 meses: mediana de {_g(v1[7], 1)} bbl por metro de rama, sobre "
         f"{_g(v1[3])} hijos de {_g(v1[4])} pads.",
         f"- Muy depletado contra virgen: {_g(prin[2], 1)} bbl por metro de rama ({ic(prin)}), o sea {pc(prin)}, sobre "
         f"{_g(prin[6])} hijos de {_g(prin[7])} pads.",
         f"- Control negativo, muy depletado contra virgen: {_g(ctrl[2], 1)} bbl por metro de rama ({ic(ctrl)}), o sea {pc(ctrl)}. "
         + ("Es nulo." if nulo(ctrl[4], ctrl[5]) else "No es nulo."),
         f"- Exposición continua (descriptivo): {_g(cont[2], 2)} bbl por metro de rama por cada 100 bbl por metro de exposición "
         f"(IC 95%: {_g(cont[4], 2)} a {_g(cont[5], 2)}); con la exposición del "
         f"control negativo: {_g(cont_c[2], 2)} (IC 95%: {_g(cont_c[4], 2)} a {_g(cont_c[5], 2)}).",
         f"- Por operadora (descriptivo, muy depletado contra virgen): YPF {_g(ypf[2], 1)} bbl por metro ({ic(ypf)}); "
         f"resto {_g(resto[2], 1)} bbl por metro ({ic(resto)}).",
         f"- Equilibrio (ubicación): el grupo muy depletado tiene {_g(eq['pozos_a_5_km'][3])} pozos de shale a menos de 5 km contra "
         f"{_g(eq['pozos_a_5_km'][1])} del grupo virgen (p dentro de celdas {_g(eq['pozos_a_5_km'][4], 3)}), y {_g(eq['rama_horizontal_m'][3])} m "
         f"de rama contra {_g(eq['rama_horizontal_m'][1])} m (p {_g(eq['rama_horizontal_m'][4], 3)}): se ubican en zonas de desarrollo más "
         "denso, que es lo que el control negativo ya muestra.",
         "- El IC del modelo principal es ancho: en porcentaje del rendimiento virgen, no excluye una diferencia relevante en ninguno "
         "de los dos sentidos.",
         "- Se publican todos los modelos calculados; el veredicto sale solo del modelo principal y su control negativo.", "",
         "## Regla fijada antes de correr", "",
         "La unidad es el pozo con 12 meses publicados, con rama, etapas, arena y fecha de primera fractura, cuyo primer petróleo "
         "llega entre 0 y 12 meses después del mes de la fractura. La exposición es el petróleo acumulado de los pozos de shale a "
         "menos de 1 km de distancia de superficie, contado solo hasta el mes anterior a la fractura del hijo y dividido por los "
         "metros de rama del hijo. Hay tres grupos: virgen (exposición cero), poco depletado (exposición positiva hasta la mediana "
         "de las positivas) y muy depletado (por encima de esa mediana). "
         + ("Con menos de 50 hijos sin exposición se usaron los terciles de todos los hijos, no el cero. " if terciles else "")
         + "El resultado es el petróleo de 12 meses por metro de rama. El modelo es de mínimos cuadrados con efectos fijos de área "
         "por cohorte, rama, arena por metro, etapas y operador, con errores agrupados por pad.", "",
         "El control negativo repite el modelo con la exposición de pozos que empezaron a producir después de la ventana de 12 meses "
         "del hijo: no pudieron depletarlo ni interferirlo. La regla pedía pozos posteriores a la fractura; se exige que empiecen "
         "después de la ventana porque un pozo que empieza dentro de ella podría afectar al hijo, que es el efecto de padre que este "
         "proyecto mide. Esa definición de la ventana se fijó antes de correr (commit 39c7dfe). La exposición de control se acumula "
         "hasta el último mes con datos, así que los hijos de cohortes recientes casi no tienen exposición de control y caen "
         "mecánicamente en el grupo virgen del control: las celdas de área por cohorte absorben el nivel, pero el control se apoya "
         "sobre todo en cohortes viejas.", "",
         "- No se sostiene: el IC 95% del grupo muy depletado incluye cero, el punto es menor que 5% del rendimiento virgen y el "
         "control negativo es nulo (su IC incluye cero).",
         "- Sostiene: el grupo muy depletado rinde menos con IC que excluye cero y el control negativo es nulo.",
         "- Ubicación: igual que el anterior, pero el control negativo tampoco es nulo (núcleo contra borde, no depleción).",
         "- No firme: cualquier otro caso. Sin muestra: menos de 50 hijos o de 20 pads en el grupo virgen o en el muy depletado, "
         "o menos de 100 pads.", "",
         "## Grupos", "",
         f"El grupo poco depletado llega hasta {_g(g2[6])} bbl por metro de exposición y el muy depletado empieza en "
         f"{_g(g3[5])}; en el control negativo los cortes son los de sus propias exposiciones positivas. La exposición es el "
         "petróleo acumulado de los vecinos por metro de rama del hijo.", "",
         "| Exposición | Grupo | Hijos | Pads | Exposición mínima (bbl/m) | Exposición máxima (bbl/m) | Mediana a 12 meses (bbl/m) | "
         "Media a 12 meses (bbl/m) |",
         "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for nombre, rot in (("real", "Exposición real"), ("control", "Exposición de control negativo")):
        for b in (1, 2, 3):
            r = gr[(nombre, b)]
            L.append(f"| {rot} | {r[2]} | {_g(r[3])} | {_g(r[4])} | {_g(r[5])} | {_g(r[6])} | {_g(r[7], 1)} | {_g(r[8], 1)} |")
    L += ["", "## Coeficientes", "",
          "Cada coeficiente es la diferencia de petróleo de 12 meses por metro de rama contra el grupo virgen (en el modelo continuo, "
          "por cada 100 bbl por metro de exposición), en bbl por metro. El porcentaje es contra la mediana del grupo virgen del "
          "modelo. El IC es de 95% con errores agrupados por pad; el p, con tres decimales, es el de la prueba normal de cada "
          "coeficiente.", "",
          "| Modelo | Término | Coeficiente (bbl/m) | % del virgen | IC 95% (bbl/m) | Hijos | Pads | p |",
          "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |"]
    for (modelo, termino), r in coef.items():
        L.append(f"| {MODELOS[modelo]} | {TERMINOS_TXT[termino]} | {_g(r[2], 1)} | {_g(r[3], 1)} | {_g(r[4], 1)} a {_g(r[5], 1)} | "
                 f"{_g(r[6])} | {_g(r[7])} | {_g(r[8], 3)} |")
    L += ["", "## Equilibrio entre grupos, antes del resultado", "",
          "Medias de diseño y de ubicación por grupo de exposición real. El p es el de la prueba conjunta (Wald, errores por pad) de "
          "que los grupos poco y muy depletado no difieren del virgen: dentro de las celdas de área por cohorte, que es lo que "
          "el modelo ajusta, y sin celdas. Un p de 0,000 es menor que 0,0005. Una variable que no varía dentro de las celdas "
          "(la cohorte, y el operador, que en este dato coincide con el área) no tiene p dentro de ellas (n/d).", "",
          "| Variable | Virgen | Poco depletado | Muy depletado | p dentro de celdas | p sin celdas |",
          "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for nombre, rot, dec, fac in EQUILIBRIO_TXT:
        r = eq[nombre]
        f = (lambda x, d: f"{x:.{d}f}".replace(".", ",")) if nombre == "cohorte" else _g   # un ano no lleva punto de miles
        L.append(f"| {rot} | {f(fac * r[1], dec)} | {f(fac * r[2], dec)} | {f(fac * r[3], dec)} | {_g(r[4], 3)} | {_g(r[5], 3)} |")
    L += ["", "## Muestra", ""]
    for paso, d, n in mu:
        L.append(f"- Paso {paso}, {d}: {_g(n)} hijos.")
    L += ["", "## Límites", "",
          "- La distancia es de superficie: no hay trayectorias ni zona de aterrizaje. Con ramas de 1.500 a 3.200 m, un vecino a "
          "menos de 1 km de superficie puede estar a 100 m o a 3 km en el subsuelo, y puede estar en otra zona apilada.",
          "- El espaciamiento entre ramas no se observa, así que no se separa depleción de espaciamiento.",
          "- Núcleo contra borde: el desarrollo denso está donde la roca y la infraestructura son distintas. El control negativo mira "
          "ese riesgo con pozos posteriores, pero no lo elimina: la ubicación futura y la pasada no son la misma.",
          "- Es una asociación con control de diseño, no una afirmación causal.",
          "- El libro de hallazgos tiene su propio estado no firme: el estado de `hijo_depletado` sale del veredicto de arriba "
          "(confirmado si sostiene, refutado si no se sostiene, no firme en cualquier otro caso), no del valor.",
          "- El resultado de 12 meses deja fuera a los pozos recientes, que todavía no tienen 12 meses publicados.",
          "- Los intervalos no tienen ajuste por comparaciones múltiples: se publican todos los modelos calculados, favorables o no. "
          "Los coeficientes descriptivos entran en el conteo de pruebas del proyecto de [Bloques espaciales](bloques.md); los p de la "
          "prueba de equilibrio, que es un diagnóstico de la muestra, no.",
          ""]
    return "\n".join(L)


# ------------------------------------------------------------------ principal

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    R = calcular(cargar(con))
    _escribir(con, "mart_hijo_muestra", COLS_MUESTRA, R["muestra"])
    _escribir(con, "mart_hijo_grupos", COLS_GRUPOS, R["grupos"])
    _escribir(con, "mart_hijo_coef", COLS_COEF, R["coef"])
    _escribir(con, "mart_hijo_equilibrio", COLS_EQUILIBRIO, R["equilibrio"])
    print("[hijo] cortes", R["cortes"], "control", R["cortes_control"])
    for t in ("mart_hijo_muestra", "mart_hijo_grupos", "mart_hijo_coef", "mart_hijo_equilibrio"):
        for r in con.execute(f"select * from {t}").fetchall():
            print(f"[hijo] {t[10:]:10}", tuple(round(x, 4) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
