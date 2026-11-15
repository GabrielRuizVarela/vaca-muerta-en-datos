"""Anisotropia de la interferencia por area y costo (petroleo diferido) por evento.

Se corre despues de pipeline.build:  uv run python -m pipeline.costo

Escribe en data/warehouse.duckdb (create or replace, idempotente):
  mart_anisotropia_area   eje de maxima interferencia por area y para la cuenca, con IC por bootstrap
  mart_costo_coef         dosis-respuesta de los barriles diferidos (meses 0 a 6) por evento cercano
  mart_perdida_permanente padres cercanos que no vuelven al 90% de la trayectoria de control al mes 12
  mart_costo_cv           MAE, RMSE y R2 fuera de muestra (validacion cruzada por pad hijo) del modelo y de sus referencias
  mart_costo_calibracion  prediccion media contra observado medio por decil de prediccion, con residuales p10 y p90
  mart_costo_residuales   residuales fuera de muestra por tercil de prediccion (base del intervalo de agente/ops.py)

Que mide
  Eventos: un padre (pozo mas viejo, produciendo) y el mes en que se fractura por primera vez un hijo a menos de 1 km
  (banda cercana). Anisotropia: entre 0,3 y 1 km, la caida del indice al mes 1 (indice del control de igual edad menos
  indice del padre) se ajusta con un nucleo axial coseno
      caida = c + b1 * km + b2 * log(edad) + R * cos(2 * (rumbo - theta))
  El rumbo es el del eje hijo a padre, de 0 a 180 grados desde el norte (el mismo del test "anisotropia" del libro de
  hallazgos). theta es el eje de maxima caida y se obtiene en forma cerrada: con cos(2r) y sin(2r) como regresores,
  theta = atan2(b, a) / 2. El indice se trunca a [0, 2] para que un padre atipico no domine. En la fila "Cuenca" las
  variables se centran por area (efectos fijos de area).

Inferencia
  Bootstrap por conglomerados: se remuestrean pads hijo completos, porque los eventos del mismo pad responden al
  mismo hijo y no son independientes (con eventos sueltos el intervalo saldria demasiado angosto). Semilla fija. El IC
  del eje es circular (desvios respecto de la estimacion, modulo 180). p_perm es un test de permutacion por bloques: se intercambian
  los rumbos de pads hijo completos (del mismo tamano), para respetar la correlacion dentro del pad; la
  amplitud siempre es positiva, asi que su IC solo no prueba que haya anisotropia.

Minimo por area: MIN_N_AREA eventos entre 0,3 y 1 km con indice al mes 1. Con menos, el eje no se estima.

Que NO se puede identificar con estos datos
  * La perdida del pozo hijo por la depletion del padre: la comparacion es solo del lado del padre. Con coordenadas
    de superficie el petroleo ya producido a menos de 1 km no mueve el petroleo por metro del hijo, pero eso no prueba
    que no exista.
  * El espaciamiento lateral entre ramas: solo hay coordenadas de superficie (pads), no trayectorias. A distancia de
    superficie chica, un rumbo y una distancia no dicen cuanta roca separa las ramas.
  * Cierre preventivo versus golpe: un cierre o reduccion voluntaria del padre se ve igual que un dano en datos
    mensuales. El coeficiente de "parado" lo separa solo en parte (usa el estado declarado), el resto queda mezclado.
  * Causalidad del eje: el eje de caida mide donde se ve la merma, no la direccion de SHmax. Es una comparacion, no una
    inferencia de esfuerzos.
  * Cola de perdida permanente: una merma al mes 12 puede ser depletion, cierre del pozo o cambio de sistema de
    extraccion; los meses sin dato cuentan como indice 0.
"""
from __future__ import annotations

import math

import duckdb
import numpy as np

from pipeline.ingest import DATA

SEMILLA = 20261115
MIN_N_AREA = 60          # eventos entre 0,3 y 1 km para estimar un eje por area
MIN_N_AREA_FE = 30       # eventos cercanos para que un area tenga su propio efecto fijo en el costo
REPS_EJE = 400
REPS_PERM = 499
REPS_COSTO = 300
REPS_PERDIDA = 300
KM_MIN_EJE = 0.3
P_EJE_COSTO = 0.10       # un eje de area se usa en el costo solo si su p de permutacion es menor...
ANCHO_MAX = 90.0         # ...y su IC mide menos de 90 grados (con 90 o mas el eje no esta definido)
UMBRAL_RECUPERO = 0.9

EVENTOS_SQL = """
select e.padre, e.mes_frac, e.pad_id, trim(e.area) as area, e.km_min, e.edad_meses, e.base_m3_d, e.hijos_1km,
       c.rumbo_eje, coalesce(c.parado, false) as parado,
       m.indice, b.indice_control, d.petroleo_diferido_bbl,
       f.arena_tn, f.etapas, u.lat, h.pad_id as pad_hijo
from int_interferencia_evento e
join int_interferencia_clase c on c.padre = e.padre and c.mes_frac = e.mes_frac
join int_pozo_ubicacion u on u.pozo_id = e.padre
join int_interferencia_mes m on m.padre = e.padre and m.mes_frac = e.mes_frac and m.k = 1
join mart_interferencia_brecha b on b.grupo_edad = e.grupo_edad and b.k = 1
left join mart_interferencia_diferida d on d.padre = e.padre and d.mes_frac = e.mes_frac
left join dim_fractura_pozo f on f.pozo_id = e.hijo_cercano
left join int_pozo_ubicacion h on h.pozo_id = e.hijo_cercano
where e.banda = 'cercano' and c.rumbo_eje is not null
order by e.padre, e.mes_frac
"""


def _filas(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _arr(filas: list[dict], col: str, dtype=float) -> np.ndarray:
    return np.array([np.nan if f[col] is None else f[col] for f in filas], dtype=dtype)


# ------------------------------------------------------------------ eje axial

def ajustar_eje(caida, ctrl, rumbo, grupo=None):
    """Ajusta caida = controles + a cos(2 r) + b sin(2 r) por minimos cuadrados.

    Devuelve (theta en [0, 180), amplitud R, coeficientes). `ctrl` es la matriz de controles sin constante.
    Con `grupo` (entero por evento) se centran todas las columnas por grupo, o sea efectos fijos, y no hay constante.
    """
    r = np.radians(np.asarray(rumbo, dtype=float))
    X = np.column_stack([ctrl, np.cos(2 * r), np.sin(2 * r)]) if np.size(ctrl) else np.column_stack([np.cos(2 * r), np.sin(2 * r)])
    y = np.asarray(caida, dtype=float)
    if grupo is None:
        X = np.column_stack([np.ones(len(y)), X])
    else:
        n_g = int(grupo.max()) + 1
        cnt = np.maximum(np.bincount(grupo, minlength=n_g), 1)

        def cen(a):
            return a - (np.bincount(grupo, a, n_g) / cnt)[grupo]
        X = np.column_stack([cen(X[:, j]) for j in range(X.shape[1])])
        y = cen(y)
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    a, b = beta[-2], beta[-1]
    theta = (math.degrees(math.atan2(b, a)) / 2) % 180
    return theta, float(math.hypot(a, b)), beta


def _dif_axial(a, b):
    """Diferencia entre dos ejes (grados), en (-90, 90]."""
    return (np.asarray(a) - b + 90) % 180 - 90


def _remuestra(rng, clusters: list[np.ndarray]) -> np.ndarray:
    pick = rng.integers(0, len(clusters), len(clusters))
    return np.concatenate([clusters[i] for i in pick])


def _clusters(clave: np.ndarray) -> list[np.ndarray]:
    orden = np.argsort(clave, kind="stable")
    ordenada = clave[orden]
    cortes = np.flatnonzero(ordenada[1:] != ordenada[:-1]) + 1
    return np.split(orden, cortes)


def _perm_bloques(rng, rumbo: np.ndarray, cl: list[np.ndarray]) -> np.ndarray:
    """Permuta los rumbos entre pads hijo completos del mismo tamano (los rumbos de un pad se mueven juntos)."""
    out = rumbo.copy()
    por_tam: dict[int, list[np.ndarray]] = {}
    for c in cl:
        por_tam.setdefault(len(c), []).append(c)
    for bloques in por_tam.values():
        for a, b in enumerate(rng.permutation(len(bloques))):
            out[bloques[a]] = rumbo[bloques[b]]
    return out


def eje_con_intervalo(caida, ctrl, rumbo, cluster_clave, grupo=None, reps=REPS_EJE, reps_perm=REPS_PERM, semilla=SEMILLA):
    """Eje, amplitud, IC bootstrap por conglomerados (95%) y p de permutacion."""
    caida, ctrl, rumbo = np.asarray(caida, float), np.asarray(ctrl, float), np.asarray(rumbo, float)
    theta, amp, beta = ajustar_eje(caida, ctrl, rumbo, grupo)
    rng = np.random.default_rng(semilla)
    cl = _clusters(np.asarray(cluster_clave))
    dev, amps = [], []
    for _ in range(reps):
        i = _remuestra(rng, cl)
        t, a, _b = ajustar_eje(caida[i], ctrl[i], rumbo[i], None if grupo is None else grupo[i])
        dev.append(_dif_axial(t, theta))
        amps.append(a)
    dev = np.array(dev)
    lo, hi = np.percentile(dev, [2.5, 97.5])
    a_lo, a_hi = np.percentile(amps, [2.5, 97.5])
    mayor = 0
    for _ in range(reps_perm):
        _t, a, _b = ajustar_eje(caida, ctrl, _perm_bloques(rng, rumbo, cl), grupo)
        mayor += a >= amp
    return {"eje": float(theta), "ic_bajo": float((theta + lo) % 180), "ic_alto": float((theta + hi) % 180),
            "ancho_ic": float(hi - lo), "amplitud": amp, "amp_ic_bajo": float(a_lo), "amp_ic_alto": float(a_hi),
            "p_perm": (1 + mayor) / (1 + reps_perm), "beta": beta}


# ------------------------------------------------------------------ tablas

def _escribir(con, tabla: str, columnas: list[tuple[str, str]], filas: list[tuple]) -> None:
    con.execute(f"create or replace table {tabla} ({', '.join(f'{n} {t}' for n, t in columnas)})")
    if filas:
        con.executemany(f"insert into {tabla} values ({', '.join('?' * len(columnas))})", filas)


def _controles_eje(ev: dict) -> np.ndarray:
    return np.column_stack([ev["km"], np.log(np.maximum(ev["edad"], 1))])


def tabla_anisotropia(filas: list[dict]) -> tuple[list[tuple], dict]:
    """Un eje por area con n suficiente y uno para toda la cuenca. Devuelve (filas, eje por area usado en el costo)."""
    km = _arr(filas, "km_min")
    sel = (km >= KM_MIN_EJE) & (km < 1)
    f = [x for x, s in zip(filas, sel) if s]
    area = np.array([x["area"] for x in f])
    ev = {"km": _arr(f, "km_min"), "edad": _arr(f, "edad_meses"), "lat": _arr(f, "lat")}
    idx = np.clip(_arr(f, "indice"), 0, 2)
    ctl = np.clip(_arr(f, "indice_control"), 0, 2)
    caida = ctl - idx
    rumbo = _arr(f, "rumbo_eje")
    clave = np.array([str(x["pad_hijo"]) for x in f])

    out, ejes = [], {}
    cuenca_cod = np.unique(area, return_inverse=True)[1]
    cb = eje_con_intervalo(caida, _controles_eje(ev), rumbo, clave, grupo=cuenca_cod)
    b = cb["beta"]
    out.append(("Cuenca", len(f), len(set(clave)), float(np.mean(ev["lat"])), cb["eje"], cb["ic_bajo"], cb["ic_alto"], cb["ancho_ic"],
                cb["amplitud"], cb["amp_ic_bajo"], cb["amp_ic_alto"], 2 * cb["amplitud"], cb["p_perm"], True,
                float(b[0]), float(b[1])))
    ejes["Cuenca"] = cb["eje"]
    nombres, cuentas = np.unique(area, return_counts=True)
    for nom, n in sorted(zip(nombres, cuentas), key=lambda t: -t[1]):
        if n < MIN_N_AREA:
            continue
        m = area == nom
        sub = {k: v[m] for k, v in ev.items()}
        r = eje_con_intervalo(caida[m], _controles_eje(sub), rumbo[m], clave[m])
        usa = bool(r["p_perm"] < P_EJE_COSTO and r["ancho_ic"] < ANCHO_MAX)
        if usa:
            ejes[str(nom)] = r["eje"]
        out.append((str(nom), int(n), len(set(clave[m])), float(np.mean(sub["lat"])), r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"],
                    r["amplitud"], r["amp_ic_bajo"], r["amp_ic_alto"], 2 * r["amplitud"], r["p_perm"], usa,
                    float(r["beta"][1]), float(r["beta"][2])))
    return out, ejes


COLS_ANISO = [("area", "varchar"), ("n", "integer"), ("pads_hijo", "integer"), ("lat_media", "double"),
              ("eje_grados", "double"), ("ic_bajo", "double"), ("ic_alto", "double"), ("ancho_ic", "double"), ("amplitud", "double"),
              ("amplitud_ic_bajo", "double"), ("amplitud_ic_alto", "double"), ("contraste", "double"),
              ("p_perm", "double"), ("usa_en_costo", "boolean"), ("coef_km", "double"), ("coef_log_edad", "double")]


# ------------------------------------------------------------------ costo

TERMINOS = [  # (nombre, unidad)
    ("km", "bbl por km de distancia"),
    ("desvio_eje_10", "bbl por 10 grados de desvio respecto del eje (0 = sobre el eje)"),
    ("edad_anios", "bbl por año de edad del padre"),
    ("base_10m3d", "bbl por 10 m3/d de caudal base del padre"),
    ("hijos_1km", "bbl por hijo adicional a menos de 1 km"),
    ("arena_1000tn", "bbl por 1.000 tn de arena del hijo"),
    ("etapas_10", "bbl por 10 etapas del hijo"),
    ("parado", "bbl si el padre figura Parado Transitoriamente en el mes 0"),
]


def desvio_eje(rumbo, eje):
    """Desvio angular absoluto entre un rumbo y un eje, en [0, 90] grados."""
    return np.abs(_dif_axial(rumbo, eje))


def eje_de_area(area: str, ejes: dict) -> float:
    return ejes.get(area, ejes["Cuenca"])


FOLDS_EJE = 5            # el eje de cada evento sale de los otros pliegues (cruzado), no de si mismo
MIN_N_EJE_AREA = 20      # eventos de entrenamiento minimos para un eje propio de area dentro de un pliegue


def _matriz_costo(f: list[dict], eje: np.ndarray, areas_fe: list[str]) -> tuple[np.ndarray, list[str]]:
    cols = [
        _arr(f, "km_min"),
        desvio_eje(_arr(f, "rumbo_eje"), eje) / 10,
        _arr(f, "edad_meses") / 12,
        _arr(f, "base_m3_d") / 10,
        _arr(f, "hijos_1km"),
        _arr(f, "arena_tn") / 1000,
        _arr(f, "etapas") / 10,
        _arr(f, "parado"),
    ]
    nombres = [t for t, _u in TERMINOS]
    for a in areas_fe:
        cols.append(np.array([1.0 if x["area"] == a else 0.0 for x in f]))
        nombres.append(f"area:{a}")
    return np.column_stack(cols), nombres


def _ols(X, y):
    """MCO con constante y errores robustos HC1. Las columnas se escalan por su maximo para estabilizar la inversa."""
    X1 = np.column_stack([np.ones(len(y)), X])
    esc = np.maximum(np.abs(X1).max(axis=0), 1e-12)
    Z = X1 / esc
    bz, *_ = np.linalg.lstsq(Z, y, rcond=None)
    res = y - Z @ bz
    ZtZi = np.linalg.pinv(Z.T @ Z)
    cov = ZtZi @ ((Z * res[:, None] ** 2).T @ Z) @ ZtZi * len(y) / max(len(y) - Z.shape[1], 1)
    ss = float(np.sum((y - y.mean()) ** 2))
    return bz / esc, np.sqrt(np.maximum(np.diag(cov), 0)) / esc, 1 - float(np.sum(res ** 2)) / ss if ss else float("nan")


def _eje_entrenado(d: dict, j: np.ndarray, area_te: np.ndarray, usadas: list[str]) -> np.ndarray:
    """Eje para filas de areas `area_te` estimado con las filas de entrenamiento `j` (ya filtradas por `en_eje`)."""
    ctrl = _controles_eje({"km": d["km"][j], "edad": d["edad"][j]})
    cod = np.unique(d["area"][j], return_inverse=True)[1]
    e_k = np.full(len(area_te), ajustar_eje(d["caida"][j], ctrl, d["rumbo"][j], cod)[0])
    for a in usadas:
        m = d["area"][j] == a
        if m.sum() >= MIN_N_EJE_AREA:
            e_k[area_te == a] = ajustar_eje(d["caida"][j][m], ctrl[m], d["rumbo"][j][m])[0]
    return e_k


def _ejes_cruzados(d: dict, i: np.ndarray, usadas: list[str]) -> np.ndarray:
    """Eje de cada fila `i` estimado SIN las filas de su mismo pliegue de pads hijo (validacion cruzada).

    Con el eje ajustado sobre los mismos eventos que despues se miden contra el, el desvio respecto del eje queda
    correlacionado con la caida por construccion; el eje cruzado corta esa circularidad. Cada area de `usadas` tiene
    eje propio si el pliegue de entrenamiento le deja MIN_N_EJE_AREA eventos; el resto usa el de la cuenca
    (con efectos fijos de area), como en tabla_anisotropia.
    """
    fold, area = d["fold"][i], d["area"][i]
    eje = np.empty(len(i))
    for k in range(FOLDS_EJE):
        te = fold == k
        if not te.any():
            continue
        j = i[(~te) & d["en_eje"][i]]
        eje[te] = _eje_entrenado(d, j, area[te], usadas)
    return eje


def _datos_eje(filas: list[dict], rng) -> tuple[dict, list[np.ndarray]]:
    km = _arr(filas, "km_min")
    d = {"km": km, "edad": _arr(filas, "edad_meses"), "area": np.array([x["area"] for x in filas]),
         "rumbo": _arr(filas, "rumbo_eje"),
         "caida": np.clip(_arr(filas, "indice_control"), 0, 2) - np.clip(_arr(filas, "indice"), 0, 2),
         "en_eje": (km >= KM_MIN_EJE) & (km < 1)}
    cl = _clusters(np.array([str(x["pad_hijo"]) for x in filas]))
    pliegue = rng.permutation(len(cl)) % FOLDS_EJE
    d["fold"] = np.empty(len(filas), dtype=int)
    for c, k in zip(cl, pliegue):
        d["fold"][c] = k
    return d, cl


def tabla_costo(filas: list[dict], ejes: dict, reps: int = REPS_COSTO) -> list[tuple]:
    """Dosis-respuesta de los barriles diferidos (meses 0 a 6).

    El eje usado en `desvio_eje_10` es el cruzado (_ejes_cruzados); el intervalo remuestrea pads hijo y re-estima los
    ejes en cada repeticion, asi incluye la incertidumbre del eje. Las areas con eje propio (`ejes`, salvo "Cuenca")
    se toman como dadas, de la estimacion con la muestra completa.
    """
    usadas = sorted(a for a in ejes if a != "Cuenca")
    rng = np.random.default_rng(SEMILLA + 1)
    d, cl = _datos_eje(filas, rng)
    ok = np.array([x["petroleo_diferido_bbl"] is not None and x["arena_tn"] is not None and x["etapas"] is not None
                   and x["base_m3_d"] is not None for x in filas])
    cuenta: dict[str, int] = {}
    for x, o in zip(filas, ok):
        if o:
            cuenta[x["area"]] = cuenta.get(x["area"], 0) + 1
    areas_fe = sorted(a for a, n in cuenta.items() if n >= MIN_N_AREA_FE)
    y_all = _arr(filas, "petroleo_diferido_bbl")

    def ajustar(i):
        i = i[ok[i]]
        eje = _ejes_cruzados(d, i, usadas)
        X, nombres = _matriz_costo([filas[t] for t in i], eje, areas_fe)
        return X, y_all[i], nombres

    X, y, nombres = ajustar(np.arange(len(filas)))
    beta, se, r2 = _ols(X, y)
    boot = []
    for _ in range(reps):
        pick = rng.integers(0, len(cl), len(cl))
        Xb, yb, _n = ajustar(np.concatenate([cl[t] for t in pick]))
        b = _ols(Xb, yb)[0]
        b[1:][~Xb.any(axis=0)] = np.nan   # area sin eventos en esta repeticion: coeficiente indefinido, no cero
        boot.append(b)
    lo, hi = np.nanpercentile(np.array(boot), [2.5, 97.5], axis=0)
    unidades = dict(TERMINOS)
    filas_out = [("intercepto", float(beta[0]), float(se[0]), float(lo[0]), float(hi[0]), "bbl, evento de referencia (areas chicas juntas)",
                  len(y), r2, 0.0, 0.0)]
    for j, nom in enumerate(nombres, start=1):
        un = unidades.get(nom, "bbl respecto de las areas chicas juntas (efecto fijo de area)")
        filas_out.append((nom, float(beta[j]), float(se[j]), float(lo[j]), float(hi[j]), un, len(y), r2, float(X[:, j - 1].mean()), float(X[:, j - 1].std())))
    return filas_out


COLS_COSTO = [("termino", "varchar"), ("coef", "double"), ("se_robusto", "double"), ("ic_bajo", "double"),
              ("ic_alto", "double"), ("unidad", "varchar"), ("n", "integer"), ("r2", "double"), ("media_x", "double"), ("sd_x", "double")]


# ------------------------------------------------------------------ incertidumbre predictiva (validacion cruzada)

FOLDS_CV = 5             # pliegues de la validacion cruzada por pad hijo (independientes de los del eje)
SEMILLA_CV = SEMILLA + 2
SEMILLA_MC = SEMILLA + 7  # semilla fija del Monte Carlo del intervalo de la suma sobre padres (la usa agente/ops.py)
REPS_MC = 2000
Q_INT = (10, 90)         # cuantiles del intervalo de 80%

COLS_CV = [("modelo", "varchar"), ("n", "integer"), ("mae", "double"), ("rmse", "double"), ("r2", "double"),
           ("frac_pred_neg", "double")]
COLS_CALIB = [("decil", "integer"), ("n", "integer"), ("pred_media", "double"), ("obs_media", "double"),
              ("resid_p10", "double"), ("resid_p90", "double")]
COLS_RESID = [("tercil", "integer"), ("residual", "double"), ("pred", "double")]


def pliegues_cv(pad_hijo, k: int = FOLDS_CV, semilla: int = SEMILLA_CV) -> np.ndarray:
    """Pliegue de cada fila: se asignan pads hijo completos (nunca se parte un pad entre entrenamiento y prueba)."""
    cl = _clusters(np.array([str(x) for x in pad_hijo]))
    pl = np.random.default_rng(semilla).permutation(len(cl)) % k
    fold = np.empty(len(pad_hijo), dtype=int)
    for c, f in zip(cl, pl):
        fold[c] = f
    return fold


def predicciones_cv(filas: list[dict], ejes: dict) -> dict:
    """Predicciones fuera de muestra del costo por evento, con validacion cruzada por pad hijo.

    En cada pliegue de prueba: los ejes de las filas de entrenamiento se re-estiman con el mismo ajuste cruzado que usa
    tabla_costo; el eje de las filas de prueba sale de todo el entrenamiento; los MCO se reajustan solo con el
    entrenamiento. Quedan fijas, tomadas de la muestra completa, la lista de areas con eje propio (`ejes`) y la de areas
    con efecto fijo; son detalles menores. Devuelve arreglos alineados: y, pred (modelo completo, sin acotar),
    sin_angulo (sin el termino de desvio del eje), media (media del entrenamiento), media_area, pad_hijo, fila.
    """
    usadas = sorted(a for a in ejes if a != "Cuenca")
    d, _cl = _datos_eje(filas, np.random.default_rng(SEMILLA + 1))
    ok = np.array([x["petroleo_diferido_bbl"] is not None and x["arena_tn"] is not None and x["etapas"] is not None
                   and x["base_m3_d"] is not None for x in filas])
    cuenta: dict[str, int] = {}
    for x, o in zip(filas, ok):
        if o:
            cuenta[x["area"]] = cuenta.get(x["area"], 0) + 1
    areas_fe = sorted(a for a, n in cuenta.items() if n >= MIN_N_AREA_FE)
    ang = [t for t, _u in TERMINOS].index("desvio_eje_10")
    y_all = _arr(filas, "petroleo_diferido_bbl")
    cvf = pliegues_cv([x["pad_hijo"] for x in filas])
    idx = np.flatnonzero(ok)
    pos = {int(t): n for n, t in enumerate(idx)}
    sal = {k: np.full(len(idx), np.nan) for k in ("pred", "sin_angulo", "media", "media_area")}
    for k in range(FOLDS_CV):
        te, tr = idx[cvf[idx] == k], idx[cvf[idx] != k]
        if not len(te) or not len(tr):
            continue
        Xtr, _n = _matriz_costo([filas[t] for t in tr], _ejes_cruzados(d, tr, usadas), areas_fe)
        eje_te = _eje_entrenado(d, tr[d["en_eje"][tr]], d["area"][te], usadas)
        Xte, _n = _matriz_costo([filas[t] for t in te], eje_te, areas_fe)
        ytr = y_all[tr]
        b = _ols(Xtr, ytr)[0]
        keep = [c for c in range(Xtr.shape[1]) if c != ang]
        b2 = _ols(Xtr[:, keep], ytr)[0]
        mu_area = {a: float(ytr[d["area"][tr] == a].mean()) for a in np.unique(d["area"][tr])}
        for n, t in enumerate(te):
            r = pos[int(t)]
            sal["pred"][r] = b[0] + Xte[n] @ b[1:]
            sal["sin_angulo"][r] = b2[0] + Xte[n, keep] @ b2[1:]
            sal["media"][r] = ytr.mean()
            sal["media_area"][r] = mu_area.get(d["area"][t], float(ytr.mean()))
    return {"y": y_all[idx], **sal, "pad_hijo": np.array([str(filas[t]["pad_hijo"]) for t in idx]), "fila": idx}


def _metricas(y: np.ndarray, p: np.ndarray) -> tuple[float, float, float]:
    e = y - p
    sst = float(np.sum((y - y.mean()) ** 2))
    return float(np.abs(e).mean()), float(np.sqrt(np.mean(e ** 2))), 1 - float(np.sum(e ** 2)) / sst if sst else float("nan")


def _rango(x: np.ndarray, grupos: int) -> np.ndarray:
    """Grupo 1..grupos por rango de `x` (desempate estable)."""
    r = np.empty(len(x), dtype=int)
    r[np.argsort(x, kind="stable")] = np.arange(len(x))
    return r * grupos // len(x) + 1


def tabla_costo_cv(filas: list[dict], ejes: dict) -> tuple[list[tuple], list[tuple], list[tuple]]:
    """(metricas, calibracion, residuales) fuera de muestra. Los residuales son y menos la prediccion sin acotar."""
    p = predicciones_cv(filas, ejes)
    y, pred = p["y"], p["pred"]
    cv = []
    for nombre, v, neg in [("modelo", pred, True), ("modelo_acotado", np.maximum(pred, 0), False),
                           ("media_entrenamiento", p["media"], False), ("media_area", p["media_area"], False),
                           ("sin_angulo", p["sin_angulo"], True)]:
        mae, rmse, r2 = _metricas(y, v)
        cv.append((nombre, len(y), mae, rmse, r2, float(np.mean(v < 0)) if neg else None))
    res = y - pred
    dec = _rango(pred, 10)
    calib = []
    for g in range(1, 11):
        m = dec == g
        lo, hi = np.percentile(res[m], Q_INT)
        calib.append((g, int(m.sum()), float(pred[m].mean()), float(y[m].mean()), float(lo), float(hi)))
    ter = _rango(pred, 3)
    resid = [(int(t), float(r), float(q)) for t, r, q in sorted(zip(ter, res, pred), key=lambda z: (z[0], z[1], z[2]))]
    return cv, calib, resid


def tercil_de(pred: float, cortes: tuple[float, float]) -> int:
    """Tercil (1 a 3) de una prediccion segun los cortes de las predicciones fuera de muestra."""
    return 1 + int(pred > cortes[0]) + int(pred > cortes[1])


def intervalo_padre(pred: float, pools: dict, cortes: tuple[float, float]) -> tuple[float, float]:
    """Intervalo de 80% de un padre: prediccion mas los cuantiles 10 y 90 de los residuales de su tercil, acotado en 0."""
    lo, hi = np.percentile(pools[tercil_de(pred, cortes)], Q_INT)
    return max(pred + float(lo), 0.0), max(pred + float(hi), 0.0)


def intervalo_suma(preds, pools: dict, cortes: tuple[float, float], reps: int = REPS_MC, semilla: int = SEMILLA_MC) -> tuple[float, float]:
    """Intervalo de 80% de la suma sobre padres por Monte Carlo con semilla fija.

    Por padre se sortea un residual fuera de muestra de su tercil y se acota la prediccion mas el residual en cero,
    como el estimador puntual. Supone errores independientes entre padres; si los de un mismo hijo se mueven juntos,
    el intervalo real es mas ancho.
    """
    preds = np.asarray(preds, dtype=float)
    if not len(preds):
        return 0.0, 0.0
    rng = np.random.default_rng(semilla)
    tot = np.zeros(reps)
    for q in preds:
        pool = pools[tercil_de(float(q), cortes)]
        tot += np.maximum(q + pool[rng.integers(0, len(pool), reps)], 0.0)
    lo, hi = np.percentile(tot, Q_INT)
    return float(lo), float(hi)


# ------------------------------------------------------------------ perdida permanente

SQL_MES12 = """
select e.padre, e.pad_id, e.banda, e.grupo_edad,
       coalesce(x.petroleo_m3 / x.dias_mes, 0) / e.base_m3_d as indice12,
       x.pozo_id is null as sin_dato
from int_interferencia_evento e
left join fct_produccion x on x.pozo_id = e.padre and x.mes = e.mes_frac + interval 12 month
where e.banda in ('cercano', 'control') and e.mes_frac + interval 12 month <= (select mes from ultimo_mes)
"""


def tabla_perdida(filas: list[dict]) -> list[tuple]:
    banda = np.array([x["banda"] for x in filas])
    edad = np.array([x["grupo_edad"] for x in filas])
    idx = _arr(filas, "indice12")
    clave = np.array([x["pad_id"] for x in filas])
    grupos = sorted(set(edad))
    umbral = {g: UMBRAL_RECUPERO * float(np.median(idx[(banda == "control") & (edad == g)])) for g in grupos}
    no = np.array([i < umbral[g] for i, g in zip(idx, edad)])
    cl = _clusters(clave)
    rng = np.random.default_rng(SEMILLA + 2)
    boots = [_remuestra(rng, cl) for _ in range(REPS_PERDIDA)]

    def medidas(mask):
        c, k = (banda == "cercano") & mask, (banda == "control") & mask
        return c, k

    out = []
    for g in ["todos"] + grupos:
        mask = np.ones(len(no), bool) if g == "todos" else edad == g
        c, k = medidas(mask)
        if not c.sum() or not k.sum():
            continue
        sc, sk = no[c].mean(), no[k].mean()
        ex = []
        for i in boots:
            m = mask[i]
            cb, kb = (banda[i] == "cercano") & m, (banda[i] == "control") & m
            if cb.sum() and kb.sum():
                ex.append(no[i][cb].mean() - no[i][kb].mean())
        lo, hi = np.percentile(ex, [2.5, 97.5])
        out.append((g, int(c.sum()), float(sc), int(k.sum()), float(sk), float(sc - sk), float(lo), float(hi),
                    float(np.mean([umbral[x] for x in grupos])) if g == "todos" else float(umbral[g])))
    return out


COLS_PERDIDA = [("grupo_edad", "varchar"), ("n_cercano", "integer"), ("no_recupera_cercano", "double"),
                ("n_control", "integer"), ("no_recupera_control", "double"), ("exceso", "double"),
                ("exceso_ic_bajo", "double"), ("exceso_ic_alto", "double"), ("umbral_indice", "double")]


# ------------------------------------------------------------------ pagina del wiki

def _g(x: float, dec: int = 0) -> str:
    s = f"{x:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return s


def _rosa(g: float) -> str:
    return ["N-S", "NNE-SSO", "NE-SO", "ENE-OSO", "E-O", "ESE-ONO", "SE-NO", "SSE-NNO"][int(((g + 11.25) % 180) // 22.5)]


_NOMBRE_CV = {"modelo": "Modelo completo", "modelo_acotado": "Modelo completo, acotado en cero",
              "media_entrenamiento": "Referencia: media del entrenamiento", "media_area": "Referencia: media del área",
              "sin_angulo": "Modelo sin el término de ángulo"}


def seccion_incertidumbre(con) -> list[str]:
    """Seccion 'Incertidumbre del costo' de la pagina de anisotropia; vacia si no corrio la validacion cruzada."""
    try:
        cv = {r["modelo"]: r for r in _filas(con, "select * from mart_costo_cv")}
        ca = _filas(con, "select * from mart_costo_calibracion order by decil")
        rs = _filas(con, "select tercil, residual from mart_costo_residuales")
    except duckdb.CatalogException:
        return []
    if "modelo" not in cv or not ca:
        return []
    m, b1, b2, sa = cv["modelo"], cv["media_entrenamiento"], cv["media_area"], cv["sin_angulo"]
    L = ["## Incertidumbre del costo", "",
         f"Validación cruzada en {FOLDS_CV} pliegues de pads hijo completos ({_g(m['n'])} eventos con todos los datos): "
         "en cada pliegue se reestiman los ejes y los coeficientes sin los eventos de prueba y se predicen esos eventos. "
         "La lista de áreas con eje propio y la de áreas con efecto fijo salen de la muestra completa y no se rehacen en cada "
         "pliegue. Las métricas son sobre esas predicciones fuera de muestra, con semilla fija.", "",
         "| Modelo | n | MAE (bbl) | RMSE (bbl) | R2 fuera de muestra | Predicho bajo cero |",
         "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for nom in ("modelo", "modelo_acotado", "media_entrenamiento", "media_area", "sin_angulo"):
        r = cv[nom]
        neg = f"{_g(r['frac_pred_neg'] * 100, 1)}%" if r["frac_pred_neg"] is not None else "no aplica"
        L.append(f"| {_NOMBRE_CV[nom]} | {_g(r['n'])} | {_g(r['mae'])} | {_g(r['rmse'])} | {_g(r['r2'], 3)} | {neg} |")
    mejor_ref = max((b1, b2), key=lambda r: r["r2"])
    gana = m["r2"] > mejor_ref["r2"] and m["mae"] < min(b1["mae"], b2["mae"])
    ac = cv["modelo_acotado"]
    if gana:
        veredicto = (f"El modelo supera a las dos referencias fuera de muestra (R2 {_g(m['r2'], 3)} contra "
                     f"{_g(mejor_ref['r2'], 3)} de la mejor referencia, con menor MAE).")
    else:
        veredicto = (f"El modelo no supera a las referencias en R2 ni en RMSE fuera de muestra: su R2 es {_g(m['r2'], 3)} contra "
                     f"{_g(b1['r2'], 3)} de la media del entrenamiento y {_g(b2['r2'], 3)} de la media del área, y su RMSE es "
                     f"{_g(m['rmse'])} bbl contra {_g(b1['rmse'])} y {_g(b2['rmse'])}. En MAE queda parecido: "
                     f"{_g(m['mae'])} bbl, o {_g(ac['mae'])} con la salida acotada en 0 (el estimador de la operación), "
                     f"contra {_g(b1['mae'])} y {_g(b2['mae'])} de las referencias.")
    if m["r2"] < 0.05:
        veredicto += (" El modelo explica poco de la variación entre eventos"
                      + (" y tiene peor R2 y RMSE que la media simple" if m["r2"] < b1["r2"] else "")
                      + ": el intervalo es ancho y el valor puntual no debe leerse como una predicción precisa.")
    d_ang = m["r2"] - sa["r2"]
    veredicto += (f" El término de ángulo respecto del eje {'mejora' if d_ang > 0.005 else 'no mejora'} el R2 fuera de "
                  f"muestra (diferencia de {_g(d_ang, 3)} contra el modelo sin ese término).")
    L += ["", veredicto + f" El {_g(m['frac_pred_neg'] * 100, 1)}% de los eventos se predice por debajo de cero; el estimador "
          "puntual de la operación los acota en 0.", "",
          "Calibración: eventos ordenados por la predicción fuera de muestra y agrupados en deciles. Si el modelo "
          "estuviera bien calibrado, el observado medio acompañaría al predicho medio.", "",
          "| Decil | n | Predicho medio (bbl) | Observado medio (bbl) | Residual p10 (bbl) | Residual p90 (bbl) |",
          "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in ca:
        L.append(f"| {r['decil']} | {_g(r['n'])} | {_g(r['pred_media'])} | {_g(r['obs_media'])} | "
                 f"{_g(r['resid_p10'])} | {_g(r['resid_p90'])} |")
    lo, hi = ca[0], ca[-1]
    L += ["", f"El decil más bajo promedia {_g(lo['pred_media'])} bbl predichos contra {_g(lo['obs_media'])} observados; el más "
              f"alto, {_g(hi['pred_media'])} contra {_g(hi['obs_media'])}. El residual es el observado menos el predicho.", ""]
    L += ["Intervalo de 80%: los residuales fuera de muestra se agrupan por tercil de la predicción y, para un padre, el "
          "intervalo es su predicción más los cuantiles 10 y 90 de los residuales de su tercil, acotado en 0. Para la suma "
          f"sobre los padres de un pad, la operación `costo_interferencia` sortea {_g(REPS_MC)} veces un residual por padre "
          "(semilla fija), acota cada padre en 0 y toma los percentiles 10 y 90 de la suma. Supone errores independientes "
          "entre padres; si los de un mismo hijo se mueven juntos, el intervalo real es más ancho. Es un intervalo de "
          "predicción de un modelo de asociación, no del efecto causal de una fractura.", "",
          "| Tercil de predicción | n | Residual p10 (bbl) | Residual p90 (bbl) |", "| ---: | ---: | ---: | ---: |"]
    for t in (1, 2, 3):
        v = np.array([x["residual"] for x in rs if x["tercil"] == t])
        if len(v):
            q = np.percentile(v, Q_INT)
            L.append(f"| {t} | {_g(len(v))} | {_g(q[0])} | {_g(q[1])} |")
    return L + [""]


def pagina_anisotropia(con) -> str:
    """Pagina de wiki a partir de las tablas de costo.py. Texto en espanol, sin rayas largas."""
    an = _filas(con, "select * from mart_anisotropia_area order by area = 'Cuenca' desc, lat_media")
    co = _filas(con, "select * from mart_costo_coef")
    pp = _filas(con, "select * from mart_perdida_permanente")
    cu = an[0]
    L = ["# Anisotropía de la interferencia y su costo", "",
         "Página generada por `pipeline/costo.py`. Sale de eventos entre 0,3 y 1 km de distancia de superficie, "
         "con el índice del padre al mes 1 de la fractura del hijo restado al del control de igual edad. "
         "El rumbo es el del eje hijo a padre (0 grados es norte, 90 es este).", "",
         "## Eje de máxima merma", "",
         f"En toda la cuenca (n = {_g(cu['n'])}, efectos fijos de área) el eje de mayor merma queda en "
         f"{_g(cu['eje_grados'])} grados ({_rosa(cu['eje_grados'])}), con intervalo de 95% de {_g(cu['ic_bajo'])} a "
         f"{_g(cu['ic_alto'])} grados. El contraste entre el eje y su perpendicular es de {_g(cu['contraste'] * 100, 1)} "
         f"puntos de índice (p de permutación {_g(cu['p_perm'], 3)}).", "",
         "| Área | n | Pads hijo | Eje (grados) | IC 95% | Ancho IC | Contraste (puntos) | p perm. | Latitud media | Eje definido |",
         "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |"]
    for r in an:
        L.append(f"| {r['area']} | {_g(r['n'])} | {_g(r['pads_hijo'])} | {_g(r['eje_grados'])} | "
                 f"{_g(r['ic_bajo'])} a {_g(r['ic_alto'])} | {_g(r['ancho_ic'])} | {_g(r['contraste'] * 100, 1)} | "
                 f"{_g(r['p_perm'], 3)} | {_g(r['lat_media'], 2)} | "
                 f"{'sí' if r['p_perm'] < P_EJE_COSTO and r['ancho_ic'] < ANCHO_MAX else 'no'} |")
    L += ["", "![Mapa de ejes por área](anisotropia_mapa.svg)", "",
          "Mapa: en cada área, segmento continuo oscuro si el eje está definido (con el cono de su IC de 95%) o gris "
          "punteado si no; la línea naranja es el SHmax publicado de 67,5 grados.", "",
          "Las áreas van ordenadas de sur a norte y tienen al menos "
          f"{MIN_N_AREA} eventos. Si el límite alto del intervalo es menor que el bajo, el intervalo cruza el norte "
          f"(0 y 180 grados son el mismo eje). Un eje se da por definido si el p de permutación es menor que "
          f"{_g(P_EJE_COSTO, 2)} y el intervalo mide menos de {_g(ANCHO_MAX)} grados; la amplitud del ajuste siempre es "
          "positiva, así que solo el p la separa del ruido. El intervalo sale de remuestrear pads de pozos hijo "
          "completos (los padres de un mismo hijo responden juntos), con semilla fija "
          f"({REPS_EJE} repeticiones). Los ejes de áreas chicas dependen de pocos pads hijo.", "",
          "## Comparación con lo publicado", "",
          "El SHmax publicado para la cuenca es OSO-ENE (RAGA 2024, https://revista.geologica.org.ar/raga/article/view/1793), "
          "es decir un eje cercano a 67,5 grados en esta convención. La literatura describe además una rotación regional "
          "del campo de esfuerzos entre el sur y el norte de la cuenca. Esta página no la cuantifica: pone los ejes "
          "estimados por área junto a la latitud para que se compare. No encontramos publicaciones que infieran la "
          "dirección de SHmax a partir de producción, y el eje de merma no es una medición de esfuerzos.", "",
          "## Costo por evento", "",
          f"Modelo lineal de los barriles diferidos en los meses 0 a 6 contra el control de igual edad, con "
          f"{_g(co[0]['n'])} eventos cercanos (R2 {_g(co[0]['r2'], 2)}), efectos fijos de área y errores robustos. "
          "El eje de cada evento se estima sin su propio pliegue de pads hijo (validación cruzada) y el intervalo sale de remuestrear pads hijo y re-estimar los ejes, con semilla fija.", "",
          "| Factor | Efecto | IC 95% | Unidad | Efecto por 1 desvío estándar (bbl) |", "| --- | ---: | --- | --- | ---: |"]
    for r in co:
        if r["termino"] == "intercepto" or r["termino"].startswith("area:"):
            continue
        L.append(f"| {r['termino']} | {_g(r['coef'])} | {_g(r['ic_bajo'])} a {_g(r['ic_alto'])} | {r['unidad']} | "
                 f"{_g(r['coef'] * r['sd_x'])} |")
    fac = [r for r in co if r["termino"] in dict(TERMINOS)]
    top = sorted(fac, key=lambda r: -abs(r["coef"] * r["sd_x"]))[:3]
    firme = [r["termino"] for r in fac if r["ic_bajo"] > 0 or r["ic_alto"] < 0]
    dev = next((r for r in co if r["termino"] == "desvio_eje_10"), None)
    L += ["", "En palabras: cada efecto es lo que cambian los barriles diferidos de un padre en los meses 0 a 6 si ese "
              "factor sube una unidad y los demás quedan fijos. Medidos por desvío estándar, los tres factores que más "
              "pesan son " + ", ".join(r["termino"] for r in top) + "; con intervalo que no cruza cero: "
              + (", ".join(firme) if firme else "ninguno") + ". Los demás no permiten afirmar el signo."]
    if dev:
        firme_dev = dev["ic_bajo"] > 0 or dev["ic_alto"] < 0
        L += ["", f"Cada 10 grados que el padre se aparta del eje de mayor merma cambia el diferido en {_g(dev['coef'])} bbl "
                  "(negativo: sobre el eje se difiere más). "
                  + ("" if firme_dev else "El intervalo cruza cero: es una tendencia, no una conclusión. ")
                  + "El eje de cada evento se estima sin los eventos de su propio pliegue de pads hijo (validación "
                  "cruzada) y el intervalo re-estima los ejes en cada repetición; es el de su área si está definido y, "
                  "si no, el de la cuenca. Un padre con el estado Parado Transitoriamente no se distingue de un golpe "
                  "en estos datos."]
    L += [""] + seccion_incertidumbre(con)
    tp = next((r for r in pp if r["grupo_edad"] == "todos"), None)
    L += ["## Cola de pérdida permanente", ""]
    if tp:
        L.append(f"Al mes 12, {_g(tp['no_recupera_cercano'] * 100, 1)}% de los padres cercanos (n = {_g(tp['n_cercano'])}) "
                 f"no vuelve al {_g(UMBRAL_RECUPERO * 100)}% de la trayectoria mediana del control de su edad, contra "
                 f"{_g(tp['no_recupera_control'] * 100, 1)}% de los controles (n = {_g(tp['n_control'])}). "
                 f"El exceso es de {_g(tp['exceso'] * 100, 1)} puntos (IC 95% de {_g(tp['exceso_ic_bajo'] * 100, 1)} a "
                 f"{_g(tp['exceso_ic_alto'] * 100, 1)}). Los meses sin dato cuentan como índice 0. El umbral es relativo a la mediana del control, así que una parte de los "
                 "controles queda por debajo por construcción: lo que importa es el exceso.")
        L += ["", "| Edad del padre | n cercanos | No recupera (cercanos) | No recupera (controles) | Exceso (puntos) |",
              "| --- | ---: | ---: | ---: | ---: |"]
        for r in pp:
            L.append(f"| {r['grupo_edad']} | {_g(r['n_cercano'])} | {_g(r['no_recupera_cercano'] * 100, 1)}% | "
                     f"{_g(r['no_recupera_control'] * 100, 1)}% | {_g(r['exceso'] * 100, 1)} |")
    L += ["", "## Límites", "",
          "- No se identifica la pérdida del pozo hijo por la depleción del padre: solo se mide el lado del padre.",
          "- No se identifica el espaciamiento lateral entre ramas: solo hay coordenadas de superficie.",
          "- Un cierre preventivo del padre se ve igual que un golpe en datos mensuales; el estado declarado "
          "(Parado Transitoriamente) los separa solo en parte.",
          "- El eje es la dirección de la merma observada, no del esfuerzo, y solo se estimó entre 0,3 y 1 km: "
          "no se midió cómo cambia el patrón con la distancia.",
          "- El modelo es lineal y de asociación: los coeficientes no son efectos causales."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    filas = _filas(con, EVENTOS_SQL)
    an, ejes = tabla_anisotropia(filas)
    _escribir(con, "mart_anisotropia_area", COLS_ANISO, an)
    _escribir(con, "mart_costo_coef", COLS_COSTO, tabla_costo(filas, ejes))
    _escribir(con, "mart_perdida_permanente", COLS_PERDIDA, tabla_perdida(_filas(con, SQL_MES12)))
    cv, calib, resid = tabla_costo_cv(filas, ejes)
    _escribir(con, "mart_costo_cv", COLS_CV, cv)
    _escribir(con, "mart_costo_calibracion", COLS_CALIB, calib)
    _escribir(con, "mart_costo_residuales", COLS_RESID, resid)
    for r in cv:
        print(f"[costo] cv {r[0]:<22} n={r[1]} mae={r[2]:.0f} rmse={r[3]:.0f} r2={r[4]:.3f}")
    for r in con.execute("select area, n, eje_grados, ic_bajo, ic_alto, contraste, p_perm, usa_en_costo "
                         "from mart_anisotropia_area order by area = 'Cuenca' desc, lat_media").fetchall():
        print(f"[costo] {r[0]:<34} n={r[1]:>4} eje={r[2]:6.1f} IC {r[3]:6.1f} a {r[4]:6.1f} contraste={r[5]:.3f} p={r[6]:.3f} costo={r[7]}")
    for r in con.execute("select termino, coef, se_robusto, ic_bajo, ic_alto from mart_costo_coef").fetchall():
        print(f"[costo] {r[0]:<28} {r[1]:12.1f} se={r[2]:10.1f} IC {r[3]:10.1f} a {r[4]:10.1f}")
    for r in con.execute("select * from mart_perdida_permanente").fetchall():
        print("[costo] perdida", r)
    con.close()


if __name__ == "__main__":
    main()
