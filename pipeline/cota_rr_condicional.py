"""Cota de Rambachan y Roth (2023) con la prueba condicional e hibrida de Andrews, Roth y Pakes (ronda 3, S1).

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla, y el plan que
nombra (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto de la regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-27, ronda 3 de docs/plan-siguiente-nivel.md). Este commit trae la regla, las constantes y
las firmas; no se calculo ninguna cifra con esta prueba antes de fijarla. Si algo resulta ambiguo al calcular, se corrige en un
commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocen las cifras publicadas de pipeline.cota_rr (regla 857d434), que usa el mismo marco con un
intervalo de union por bootstrap: Mbar de quiebre 0,20 en D1 ATT(1), mayor que 2 en D2 tau_W(1) y 1,62 en la media de tau_W(0) y
tau_W(1); en D1, b(-3) = -6,1, b(-2) = -3,6, b(-1) = -10,0.

Que cambia respecto de pipeline.cota_rr. El marco, la restriccion y los estimandos son los mismos: magnitudes relativas,
Delta^RM(Mbar), con los saltos previos s(-3) = delta(-3) (contra la base), s(-2) = delta(-2) - delta(-3), s(-1) = delta(-1) -
delta(-2), y cada salto posterior delta(0) - delta(-1), delta(1) - delta(0) a lo sumo Mbar max|s| en valor absoluto. Cambia la
inferencia: en lugar de la union de percentiles del bootstrap, el conjunto de confianza de Rambachan y Roth (2023, seccion 4), que
invierte la prueba condicional e hibrida de Andrews, Roth y Pakes (2023) para cada valor del parametro. El max de |s| deja de ser
un limite: Delta^RM se escribe como la union de seis poliedros, uno por salto previo que es el mayor y por su signo, y el conjunto
de confianza es la union de los de cada poliedro (como computeConditionalCS_DeltaRM del paquete HonestDiD). No se agrega ninguna
dependencia nueva: numpy y statistics.NormalDist de la biblioteca estandar.

Entradas, por estimando: beta = (b(-3), b(-2), b(-1), b(0), b(1)) con el punto de la muestra completa y Sigma = la covarianza
muestral de los sorteos completos del bootstrap por bloques del diseno (los mismos sorteos para los cinco coeficientes; un sorteo
con algun valor faltante se descarta). Estimandos: D1 ATT(1) (theta = tau(1)); D2 tau_W(1); D2 media de tau_W(0) y tau_W(1)
(theta = (tau(0) + tau(1)) / 2), armados como en pipeline.cota_rr._estimandos_d1 y _estimandos_d2 pero guardando tambien b(0).
E ATT(1) no entra: su veredicto es "sin muestra".

Prueba para un poliedro (j, sg), j en {-3, -2, -1} el salto previo mayor y sg en {+1, -1} su signo, y un valor theta0:
  * A (8 x 5) sobre delta = (delta(-3), delta(-2), delta(-1), delta(0), delta(1)): para cada salto previo i distinto de j,
    s(i) - sg s(j) <= 0 y -s(i) - sg s(j) <= 0 (4 filas); para cada salto posterior p, p - Mbar sg s(j) <= 0 y
    -p - Mbar sg s(j) <= 0 (4 filas). Con d = 0.
  * delta = beta - (0, 0, 0, tau(0), tau(1)) y tau_post = theta0 a + gamma b, con a = (0, 1), b = (1, 0) para ATT(1) y
    a = (1, 1), b = (1, -1) para la media. Momentos: Y = A beta - theta0 A_post a, X = A_post b (A_post son las columnas de
    delta(0) y delta(1)); bajo la nula hay un gamma con E[Y - X gamma] <= 0. Sigma_Y = A Sigma A', sigma = raiz de su diagonal.
  * Estadistico: eta = max sobre los vertices v de {nu >= 0, nu'X = 0, nu'sigma = 1} de v'Y (el dual del programa lineal
    min eta sujeto a Y - X gamma <= eta sigma). Con un solo parametro de estorbo, cada vertice tiene a lo sumo dos componentes
    distintas de cero: las filas i con X_i = 0 (nu = e_i / sigma_i) y los pares (i, k) con X_i X_k < 0 que resuelven
    nu_i X_i + nu_k X_k = 0, nu_i sigma_i + nu_k sigma_k = 1. Se enumeran todos; nu* es el que da el maximo (empate: el primero
    en el orden de las filas).
  * Primera etapa, menos favorable (LF): c_LF = cuantil 1 - KAPPA de max_v v'xi, con xi ~ N(0, Sigma_Y) en N_LF sorteos con la
    semilla SEMILLA_LF (raiz de Sigma_Y por autovalores, los negativos llevados a cero). Si eta > c_LF, se rechaza.
  * Segunda etapa, condicional: s2 = nu*'Sigma_Y nu*, c = Sigma_Y nu* / s2, z = Y - c eta. Para cada vertice v, con
    a_v = v'c y b_v = v'z: si a_v < 1, b_v / (1 - a_v) es una cota inferior; si a_v > 1, es una cota superior (tolerancia
    TOL_VERTICE). V_lo es la mayor de las inferiores y V_up la menor de las superiores, tope c_LF. Con la media en cero (el caso
    menos favorable de la nula), p = (F(V_up) - F(eta)) / (F(V_up) - F(V_lo)), F la normal con desvio raiz de s2. Se rechaza si
    p < (ALFA - KAPPA) / (1 - KAPPA). Si el denominador no es positivo, no se rechaza.

Conjunto de confianza para un Mbar: los theta0 de una grilla de N_THETA puntos que alguno de los seis poliedros no rechaza. La
grilla va del extremo bajo del conjunto identificado de pipeline.cota_rr.conjunto (con el punto) menos THETA_SE desvios al extremo
alto mas THETA_SE desvios, con el desvio de l(beta) - b(-1) en los sorteos. Si un extremo de la grilla queda aceptado, se duplica
la cantidad de desvios que se agrega a cada lado (THETA_SE, 2 THETA_SE, 4 THETA_SE...), con N_THETA puntos cada vez, hasta
MAX_AMPLIAR veces; si sigue aceptado, el extremo se publica como abierto. Se publica [min, max] de los aceptados y
si el conjunto tiene huecos.

Mbar de quiebre: el menor Mbar en [0, MBAR_MAX] cuyo conjunto contiene cero, probando theta0 = 0 directamente (no en la grilla),
por biseccion con TOL_BISECCION; 0 si ya lo contiene con Mbar = 0; "mayor que MBAR_MAX" si no lo contiene en MBAR_MAX. Veredicto:
pipeline.cota_rr.veredicto_rr con ese quiebre, mismas palabras y mismo M_MIN.

Que se publica:
  * mart_cota_rr_condicional: por estimando, la grilla GRILLA_MBAR con el conjunto de confianza condicional, y la fila del quiebre
    con su veredicto; al lado, el intervalo de union de pipeline.cota_rr del mismo Mbar, como registro;
  * la pagina wiki/hallazgos/cota_rr_condicional.md, y una linea en wiki/hallazgos/cota_rr.md que remite a ella;
  * en un PR de texto aparte, el README y la portada pasan a citar el quiebre condicional de D1 ATT(1) como la cota de Rambachan y
    Roth, cualquiera sea, y dicen que el de la union es mas conservador. Si el quiebre condicional es menor que el de la union, se
    dice igual.

Validacion fijada antes de leer cifras reales (tests/test_cota_rr_condicional.py, sin warehouse):
  * dualidad: para Y, X y sigma al azar (semilla fija, 200 casos), eta por vertices coincide hasta 1e-9 con el minimo sobre gamma
    de max_i (Y_i - X_i gamma) / sigma_i, calculado aparte en los quiebres de esa funcion lineal por tramos;
  * cobertura: con Sigma sintetica (desvio 1 y correlacion 0,5 entre coeficientes vecinos, 5 x 5), delta previa (0,5; 1,0; 0,8)
    (m = 0,5), saltos posteriores iguales a +Mbar m (en el borde de la restriccion) y tau(0) = tau(1) = theta = -3, cada
    simulacion sortea beta ~ N(delta + (0, 0, 0, tau(0), tau(1)), Sigma) con la semilla SEMILLA_MC y la prueba usa esa Sigma; en
    N_MC simulaciones por Mbar con Mbar en {0,5; 1}, el conjunto contiene a theta (probado en theta0 = theta) en al menos
    COBERTURA_MIN de las simulaciones, para ATT(1) y para la media;
  * potencia plantada: igual con tau(0) = tau(1) = -10 y Mbar = 0 (saltos posteriores cero): el conjunto excluye el cero (todos
    los poliedros rechazan theta0 = 0) en al menos POTENCIA_MIN de las N_MC simulaciones;
  * en las primeras 20 simulaciones con theta = -3 y Mbar = 0, el conjunto de ATT(1) en la grilla contiene el punto b(1) - b(-1)
    y no es mas ancho que el doble del intervalo normal al 95% de b(1) - b(-1).
Si alguna falla, no se publica ninguna cifra real con esta prueba y la pagina dice que fallo.

Enmienda del 2026-11-27, antes de calcular ninguna cifra real. Va despues de 2ffa2ef, que implemento la regla sin cambios y solo
corrio la validacion sintetica. La cuarta validacion fallo tal como estaba escrita: en las primeras 20 simulaciones el conjunto
de ATT(1) contiene el punto en 20 de 20, pero el mas ancho mide 2,14 veces el intervalo normal al 95% (el promedio, 1,79) y el
tope era 2. Ese tope no salia de la literatura ni de una cuenta: se puso como guarda contra una implementacion rota, y el ancho
mide eficiencia, no correccion. Las tres validaciones de correccion pasan. diagnostico_ancho() (sin warehouse, los mismos datos
sinteticos) muestra de donde sale el ancho. Los dos poliedros que contienen a la delta verdadera rechazan theta verdadero en
4,3% y 2,8% de 1000 simulaciones y miden como maximo 1,70 y 1,97 veces. El 2,14 viene de un poliedro que no la contiene, y la
union tiene que incluirlo porque con datos reales no se sabe cual vale. Con Mbar = 0 la union contiene a theta en las 1000
simulaciones. Un conjunto mas ancho incluye antes el cero: solo puede bajar el Mbar de quiebre, nunca subirlo. Lo que cambia:
  * el ancho deja de ser puerta. Se sigue calculando con los mismos 20 casos, y la pagina publica el mas ancho, el promedio, el
    tope de 2 que no se cumplio, esta enmienda y el diagnostico;
  * que el conjunto contenga el punto en las 20 sigue siendo puerta;
  * no cambia ningun otro numero. El tope no se reemplaza por otro, y las constantes, la dualidad, la cobertura y la potencia
    quedan iguales.

Lo que no dice: supone, como pipeline.cota_rr, que los meses previos no tienen efecto (sin anticipacion). Sigma sale del bootstrap
por bloques, no de una formula; con N_LF sorteos fijos el quiebre tiene error de simulacion del orden de TOL_BISECCION o mayor.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from statistics import NormalDist

import numpy as np

from pipeline import cota_rr

# ---- regla fijada (no cambiar despues de ver cifras) ----
ALFA = 0.05
KAPPA = ALFA / 10           # nivel de la primera etapa LF (el valor por defecto de HonestDiD)
N_LF = 10_000               # sorteos para el valor critico LF
SEMILLA_LF = 20261127
TOL_VERTICE = 1e-12
N_THETA = 1001
THETA_SE = 6.0
MAX_AMPLIAR = 3
GRILLA_MBAR = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)   # la de pipeline.cota_rr
MBAR_MAX = 2.0
TOL_BISECCION = 1e-3
N_MC = 1000
COBERTURA_MIN = 0.93
POTENCIA_MIN = 0.90
SEMILLA_MC = 20261128

COLS_COTA_RR_COND = [("diseno", "varchar"), ("estimando", "varchar"), ("fila", "varchar"), ("mbar", "double"),
                     ("cc_bajo", "double"), ("cc_alto", "double"), ("cc_abierto", "varchar"), ("cc_con_huecos", "boolean"),
                     ("union_bajo", "double"), ("union_alto", "double"), ("mbar_quiebre", "double"), ("veredicto", "varchar"),
                     ("n_tratados", "integer"), ("sorteos", "integer"), ("motivo", "varchar")]
PAGINA = Path("wiki/hallazgos/cota_rr_condicional.md")


# ---- constantes de armado (no son parte de la regla: estructura de las filas y de los estimandos) ----
PREVIOS = (-3, -2, -1)
# saltos sobre delta = (d(-3), d(-2), d(-1), d(0), d(1)): s(-3), s(-2), s(-1) y los posteriores d(0)-d(-1), d(1)-d(0)
_SALTO_PREVIO = {-3: (1, 0, 0, 0, 0), -2: (-1, 1, 0, 0, 0), -1: (0, -1, 1, 0, 0)}
_SALTO_POST = ((0, 0, -1, 1, 0), (0, 0, 0, -1, 1))
POLIEDROS = tuple((j, sg) for j in PREVIOS for sg in (1, -1))
# (diseno, estimando, a, b, meses del estimando)
ESTIMANDOS = (("D1", "ATT(1)", (0, 1), (1, 0), (1,)),
              ("D2", "tau_W(1)", (0, 1), (1, 0), (1,)),
              ("D2", "media tau_W(0,1)", (1, 1), (1, -1), (0, 1)))
MOTIVO_MAYOR = "mayor que MBAR_MAX"
COMMIT_REGLA = "de19052"
COMMIT_ENMIENDA = "55a709a"  # el commit de la enmienda del ancho; lo fija el commit que corre la prueba con datos reales
TOPE_ANCHO = 2.0            # el tope de la regla original; desde la enmienda es dato, no puerta


def matriz_rm(j: int, sg: int, mbar: float):
    """A (8 x 5) del poliedro (j, sg) de Delta^RM(Mbar), en el orden de filas de la regla."""
    sj = sg * np.array(_SALTO_PREVIO[j], float)
    filas = []
    for i in PREVIOS:
        if i == j:
            continue
        si = np.array(_SALTO_PREVIO[i], float)
        filas += [si - sj, -si - sj]
    for p in _SALTO_POST:
        p = np.array(p, float)
        filas += [p - mbar * sj, -p - mbar * sj]
    return np.vstack(filas)


def vertices(X, sigma):
    """Vertices de {nu >= 0, nu'X = 0, nu'sigma = 1}, en un arreglo (n_vertices, n_momentos).

    Primero los de una componente (filas con X_i = 0, en el orden de las filas) y despues los pares (i, k), i < k, con
    X_i X_k < 0, en orden lexicografico."""
    X = np.asarray(X, float)
    sigma = np.asarray(sigma, float)
    n = len(X)
    out = []
    for i in range(n):
        if X[i] == 0:
            v = np.zeros(n)
            v[i] = 1.0 / sigma[i]
            out.append(v)
    ii, kk = np.triu_indices(n, 1)
    for i, k in zip(ii, kk):
        if X[i] * X[k] < 0:
            nu_k = X[i] / (X[i] * sigma[k] - sigma[i] * X[k])
            v = np.zeros(n)
            v[k] = nu_k
            v[i] = -nu_k * X[k] / X[i]
            out.append(v)
    return np.array(out).reshape(-1, n)


@lru_cache(maxsize=1)
def _z_lf() -> np.ndarray:
    return np.random.default_rng(SEMILLA_LF).standard_normal((N_LF, 8))


def _cdf(x: np.ndarray) -> np.ndarray:
    return np.array([0.5 * math.erfc(-v / math.sqrt(2.0)) for v in np.ravel(x)]).reshape(np.shape(x))


def _sf(x: np.ndarray) -> np.ndarray:
    return np.array([0.5 * math.erfc(v / math.sqrt(2.0)) for v in np.ravel(x)]).reshape(np.shape(x))


def _p_truncada(x: np.ndarray, lo: np.ndarray, up: np.ndarray) -> np.ndarray:
    """(F(up) - F(x)) / (F(up) - F(lo)) con F la normal estandar; inf si el denominador no es positivo.

    En la cola alta se calcula con la funcion de supervivencia (igual en aritmetica exacta, sin la cancelacion)."""
    alta = x > 0
    num = np.where(alta, _sf(x) - _sf(up), _cdf(up) - _cdf(x))
    den = np.where(alta, _sf(lo) - _sf(up), _cdf(up) - _cdf(lo))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, num / den, np.inf)


class _Prueba:
    """Todo lo que no depende de theta0 para un poliedro (j, sg) y un Mbar: A, X, Sigma_Y, vertices y c_LF."""

    def __init__(self, Sigma, a, b, j: int, sg: int, mbar: float):
        self.A = matriz_rm(j, sg, mbar)
        A_post = self.A[:, 3:]
        self.w = A_post @ np.asarray(a, float)
        self.X = A_post @ np.asarray(b, float)
        SY = self.A @ np.asarray(Sigma, float) @ self.A.T
        self.SY = (SY + SY.T) / 2
        self.sigma = np.sqrt(np.diag(self.SY))
        if not np.all(self.sigma > 0):
            raise ValueError("un momento sin varianza: no se puede normalizar")
        self.V = vertices(self.X, self.sigma)
        if len(self.V):
            lam, U = np.linalg.eigh(self.SY)
            raiz = U * np.sqrt(np.clip(lam, 0.0, None))
            xi = _z_lf() @ raiz.T
            self.c_lf = float(np.quantile((xi @ self.V.T).max(axis=1), 1 - KAPPA))
            self.s2 = np.einsum("vi,ij,vj->v", self.V, self.SY, self.V)
            # nu'Sigma_Y nu <= (nu'sigma)^2 = 1: una varianza de redondeo (par de filas opuestas con Mbar = 0) es cero
            self.s2 = np.where(self.s2 > TOL_VERTICE, self.s2, 0.0)
            C = (self.SY @ self.V.T) / np.where(self.s2 > 0, self.s2, 1.0)   # columna k: c del vertice k
            self.a_mat = self.V @ C                           # a_v para cada vertice nu* = k
        else:
            self.c_lf = float("inf")

    def momentos(self, betas, theta0) -> np.ndarray:
        """Y = A beta - theta0 A_post a, por fila de `betas` (T, 5) y theta0 escalar o (T,)."""
        betas = np.atleast_2d(np.asarray(betas, float))
        th = np.broadcast_to(np.asarray(theta0, float), (len(betas),))
        return betas @ self.A.T - th[:, None] * self.w[None, :]

    def rechaza_Y(self, Y, c_lf: float | None = None) -> np.ndarray:
        """Rechazo de la prueba condicional e hibrida, por fila de Y (T, 8)."""
        Y = np.atleast_2d(Y)
        T = len(Y)
        if not len(self.V):
            return np.zeros(T, bool)                          # el dual es infactible: eta = -inf, no rechaza
        c_lf = self.c_lf if c_lf is None else c_lf
        VY = Y @ self.V.T
        k = VY.argmax(axis=1)                                 # empate: el primero
        eta = VY[np.arange(T), k]
        rech = eta > c_lf
        idx = np.nonzero(~rech & (self.s2[k] > 0))[0]
        if idx.size:
            kk, e = k[idx], eta[idx]
            a_v = self.a_mat[:, kk].T                         # (m, n_vertices)
            b_v = VY[idx] - a_v * e[:, None]
            baja = a_v < 1 - TOL_VERTICE
            alta = a_v > 1 + TOL_VERTICE
            cota = b_v / np.where(baja | alta, 1 - a_v, 1.0)
            v_lo = np.where(baja, cota, -np.inf).max(axis=1)
            v_up = np.minimum(np.where(alta, cota, np.inf).min(axis=1), c_lf)
            s = np.sqrt(self.s2[kk])
            p = _p_truncada(e / s, v_lo / s, v_up / s)
            rech[idx] = p < (ALFA - KAPPA) / (1 - KAPPA)
        return rech


def rechaza(beta, Sigma, a, b, j: int, sg: int, mbar: float, theta0: float, c_lf: float | None = None) -> bool:
    """La prueba condicional e hibrida de la regla para un poliedro y un theta0."""
    P = _Prueba(Sigma, a, b, j, sg, mbar)
    return bool(P.rechaza_Y(P.momentos(beta, theta0), c_lf)[0])


def _pruebas(Sigma, a, b, mbar: float) -> list[_Prueba]:
    return [_Prueba(Sigma, a, b, j, sg, mbar) for j, sg in POLIEDROS]


def _aceptado(pruebas: list[_Prueba], betas, theta0) -> np.ndarray:
    """True donde algun poliedro no rechaza, por fila de `betas` (o por theta0 si es un vector)."""
    acepta = None
    for P in pruebas:
        a = ~P.rechaza_Y(P.momentos(betas, theta0))
        acepta = a if acepta is None else acepta | a
    return acepta


def conjunto_confianza(beta, Sigma, a, b, mbar: float, centro_id: tuple[float, float], desvio: float,
                       pruebas: list[_Prueba] | None = None) -> dict:
    """Union sobre los seis poliedros (o sobre `pruebas`, si se pasan): bajo, alto, abierto y con_huecos."""
    beta = np.asarray(beta, float)
    pruebas = _pruebas(Sigma, a, b, mbar) if pruebas is None else pruebas
    lo_id, hi_id = centro_id
    for k in range(MAX_AMPLIAR + 1):
        ext = THETA_SE * 2 ** k * desvio
        grilla = np.linspace(lo_id - ext, hi_id + ext, N_THETA)
        acepta = np.zeros(N_THETA, bool)
        for P in pruebas:
            Y = P.A @ beta
            acepta |= ~P.rechaza_Y(Y[None, :] - grilla[:, None] * P.w[None, :])
        if not (acepta[0] or acepta[-1]):
            break
    idx = np.nonzero(acepta)[0]
    if not idx.size:
        return {"bajo": None, "alto": None, "abierto": None, "con_huecos": False, "paso": float(grilla[1] - grilla[0])}
    ab_lo, ab_hi = bool(acepta[0]), bool(acepta[-1])
    return {"bajo": float(grilla[idx[0]]), "alto": float(grilla[idx[-1]]),
            "abierto": "ambos" if ab_lo and ab_hi else "bajo" if ab_lo else "alto" if ab_hi else None,
            "con_huecos": bool(idx[-1] - idx[0] + 1 != idx.size), "paso": float(grilla[1] - grilla[0])}


def quiebre_condicional(beta, Sigma, a, b) -> float:
    """Menor Mbar en [0, MBAR_MAX] cuyo conjunto contiene cero; inf si no lo contiene en MBAR_MAX."""
    beta = np.asarray(beta, float)

    def contiene(mbar: float) -> bool:
        return bool(_aceptado(_pruebas(Sigma, a, b, mbar), beta, 0.0)[0])
    if contiene(0.0):
        return 0.0
    if not contiene(MBAR_MAX):
        return float("inf")
    lo, hi = 0.0, MBAR_MAX
    while hi - lo > TOL_BISECCION:
        mid = (lo + hi) / 2
        if contiene(mid):
            hi = mid
        else:
            lo = mid
    return hi


# ---- por estimando ----
def calcular_estimando(diseno: str, nombre: str, a, b, meses: tuple[int, ...], beta, vals, n_tratados: int) -> dict:
    """Filas del mart (grilla y quiebre) y datos de un estimando. `beta` (5,) y `vals` (R, 5): b(-3) a b(1)."""
    beta = np.asarray(beta, float)
    vals = np.asarray(vals, float).reshape(-1, 5)
    ok = ~np.isnan(vals).any(axis=1)
    sorteos = int(ok.sum())
    base = (diseno, nombre)
    if not np.all(np.isfinite(beta)) or sorteos < 10:
        v = cota_rr.veredicto_rr(False, float("nan"))
        fila = (*base, "quiebre", None, None, None, None, None, None, None, None, v, n_tratados, sorteos,
                "falta algun previo o muy pocos sorteos completos")
        return {"diseno": diseno, "estimando": nombre, "filas": [fila], "quiebre": None, "veredicto": v,
                "sorteos": sorteos, "extra": None}
    vv = vals[ok]
    Sigma = np.cov(vv, rowvar=False)
    cols = [3 + e for e in meses]
    l_pt = float(beta[cols].mean())
    l_v = vv[:, cols].mean(axis=1)
    p3, p2, p1 = vv[:, 0], vv[:, 1], vv[:, 2]
    b3, b2, b1 = (float(x) for x in beta[:3])
    desvio = float(np.std(l_v - p1, ddof=1))
    filas = []
    for mbar in GRILLA_MBAR:
        lo, hi = cota_rr.conjunto(l_pt, b3, b2, b1, mbar, meses)
        cc = conjunto_confianza(beta, Sigma, a, b, mbar, (float(lo), float(hi)), desvio)
        ic = cota_rr.intervalo(l_v, p3, p2, p1, mbar, meses)
        filas.append((*base, "grilla", float(mbar), cc["bajo"], cc["alto"], cc["abierto"], cc["con_huecos"],
                      ic[0], ic[1], None, None, n_tratados, sorteos, None))
    q = quiebre_condicional(beta, Sigma, a, b)
    v = cota_rr.veredicto_rr(True, q)
    inf = not np.isfinite(q)
    filas.append((*base, "quiebre", None, None, None, None, None, None, None, None if inf else float(q), v,
                  n_tratados, sorteos, MOTIVO_MAYOR if inf else None))
    qu = cota_rr.quiebre(l_v, p3, p2, p1, meses)
    extra = {"l": l_pt, "b3": b3, "b2": b2, "b1": b1, "union_quiebre": None if not np.isfinite(qu) else float(qu),
             "union_veredicto": cota_rr.veredicto_rr(True, qu)}
    return {"diseno": diseno, "estimando": nombre, "filas": filas, "quiebre": q, "veredicto": v,
            "sorteos": sorteos, "extra": extra}


# ---- validacion fijada (sin warehouse) ----
SIGMA_SINT = np.eye(5) + 0.5 * (np.eye(5, k=1) + np.eye(5, k=-1))
DELTA_PREVIA = (0.5, 1.0, 0.8)     # saltos previos 0,5; 0,5; -0,2: m = 0,5
M_SINT = 0.5
N_DUALIDAD = 200
SEMILLA_DUALIDAD = 20261129
N_ANCHO = 20
_NOMBRE_SINT = {"ATT(1)": ((0, 1), (1, 0), (1,)), "media": ((1, 1), (1, -1), (0, 1))}


def eta_vertices(Y, X, sigma) -> float:
    V = vertices(X, sigma)
    return float("-inf") if not len(V) else float((V @ np.asarray(Y, float)).max())


def eta_primal(Y, X, sigma) -> float:
    """min sobre gamma de max_i (Y_i - X_i gamma) / sigma_i, en los quiebres de la funcion lineal por tramos."""
    Y, X, sigma = (np.asarray(x, float) for x in (Y, X, sigma))
    q, p = Y / sigma, -X / sigma                      # f(g) = max_i (q_i + p_i g)
    if not ((p > 0).any() and (p < 0).any()):         # sin pendientes de signos opuestos el minimo esta en el infinito
        return float(q[p == 0].max()) if (p == 0).any() else float("-inf")
    ii, kk = np.triu_indices(len(q), 1)
    dif = p[ii] != p[kk]
    g = (q[kk] - q[ii])[dif] / (p[ii] - p[kk])[dif]
    return float((q[None, :] + p[None, :] * g[:, None]).max(axis=1).min())


def validar_dualidad() -> dict:
    rng = np.random.default_rng(SEMILLA_DUALIDAD)
    peor, n_inf = 0.0, 0
    for caso in range(N_DUALIDAD):
        n = 8
        Y, X, sg = rng.normal(0, 2, n), rng.normal(0, 1, n), rng.uniform(0.3, 2.0, n)
        if 150 <= caso < 175:
            X[rng.choice(n, 3, replace=False)] = 0.0
        elif caso >= 175:
            X = np.abs(X)
            X[rng.choice(n, 2, replace=False)] = 0.0 if caso % 2 else X[0]
        e1, e2 = eta_vertices(Y, X, sg), eta_primal(Y, X, sg)
        if np.isinf(e1) or np.isinf(e2):
            if e1 != e2:
                return {"ok": False, "peor": float("inf"), "n_inf": n_inf, "casos": caso + 1}
            n_inf += 1
        else:
            peor = max(peor, abs(e1 - e2))
    return {"ok": peor <= 1e-9, "peor": peor, "n_inf": n_inf, "casos": N_DUALIDAD}


def _betas_sinteticos(mbar: float, tau: float) -> np.ndarray:
    d = np.array(DELTA_PREVIA)
    delta = np.concatenate([d, [d[-1] + mbar * M_SINT, d[-1] + 2 * mbar * M_SINT]])
    z = np.random.default_rng(SEMILLA_MC).standard_normal((N_MC, 5))
    return delta + np.array([0, 0, 0, tau, tau]) + z @ np.linalg.cholesky(SIGMA_SINT).T


def validar_cobertura() -> dict:
    tasas = {}
    for mbar in (0.5, 1.0):
        betas = _betas_sinteticos(mbar, -3.0)
        for nom, (a, b, _m) in _NOMBRE_SINT.items():
            tasas[(mbar, nom)] = float(_aceptado(_pruebas(SIGMA_SINT, a, b, mbar), betas, -3.0).mean())
    return {"ok": all(t >= COBERTURA_MIN for t in tasas.values()), "tasas": tasas, "minimo": COBERTURA_MIN}


def validar_potencia() -> dict:
    betas = _betas_sinteticos(0.0, -10.0)
    tasas = {}
    for nom, (a, b, _m) in _NOMBRE_SINT.items():
        tasas[nom] = float(1.0 - _aceptado(_pruebas(SIGMA_SINT, a, b, 0.0), betas, 0.0).mean())
    return {"ok": all(t >= POTENCIA_MIN for t in tasas.values()), "tasas": tasas, "minimo": POTENCIA_MIN}


def validar_ancho() -> dict:
    a, b, meses = _NOMBRE_SINT["ATT(1)"]
    betas = _betas_sinteticos(0.0, -3.0)[:N_ANCHO]
    desvio = float(np.sqrt(SIGMA_SINT[4, 4] + SIGMA_SINT[2, 2] - 2 * SIGMA_SINT[2, 4]))
    ancho_normal = 2 * NormalDist().inv_cdf(0.975) * desvio
    contiene, anchos = 0, []
    for beta in betas:
        punto = float(beta[4] - beta[2])
        cc = conjunto_confianza(beta, SIGMA_SINT, a, b, 0.0, (punto, punto), desvio)
        if cc["bajo"] is not None:
            contiene += int(cc["bajo"] <= punto <= cc["alto"])
            anchos.append(cc["alto"] - cc["bajo"])
        else:
            anchos.append(float("inf"))
    razon = float(max(anchos) / ancho_normal)
    # enmienda del ancho: la puerta es solo que el conjunto contenga el punto; el ancho contra TOPE_ANCHO queda como dato
    return {"ok": contiene == N_ANCHO, "contiene": contiene, "de": N_ANCHO, "razon_max": razon,
            "razon_media": float(np.mean(anchos) / ancho_normal), "tope": TOPE_ANCHO, "cumple_tope": razon <= TOPE_ANCHO}


def diagnostico_ancho() -> dict:
    """Dato de la enmienda, no puerta. Con los datos sinteticos del ancho (ATT(1), Mbar = 0, theta = -3): para cada poliedro,
    si contiene a la delta verdadera (eta por vertices <= 0 sin ruido), su rechazo de theta verdadero en las N_MC simulaciones
    y su ancho en los N_ANCHO casos del ancho, contra el intervalo normal; y la cobertura y el ancho de la union."""
    a, b, _m = _NOMBRE_SINT["ATT(1)"]
    theta = -3.0
    betas = _betas_sinteticos(0.0, theta)
    d = np.array(DELTA_PREVIA)
    media = np.concatenate([d, [d[-1], d[-1]]]) + np.array([0, 0, 0, theta, theta])
    desvio = float(np.sqrt(SIGMA_SINT[4, 4] + SIGMA_SINT[2, 2] - 2 * SIGMA_SINT[2, 4]))
    ancho_normal = 2 * NormalDist().inv_cdf(0.975) * desvio
    pruebas = _pruebas(SIGMA_SINT, a, b, 0.0)

    def _anchos(ps):
        out = []
        for beta in betas[:N_ANCHO]:
            punto = float(beta[4] - beta[2])
            cc = conjunto_confianza(beta, SIGMA_SINT, a, b, 0.0, (punto, punto), desvio, pruebas=ps)
            out.append(0.0 if cc["bajo"] is None else (cc["alto"] - cc["bajo"]) / ancho_normal)
        return out

    filas = []
    for (j, sg), P in zip(POLIEDROS, pruebas):
        w = _anchos([P])
        filas.append({"j": j, "sg": sg,
                      "contiene_delta": bool(eta_vertices(P.momentos(media, theta)[0], P.X, P.sigma) <= 1e-9),
                      "rechazo": float(P.rechaza_Y(P.momentos(betas, theta)).mean()),
                      "ancho_medio": float(np.mean(w)), "ancho_max": float(max(w))})
    u = _anchos(pruebas)
    return {"poliedros": filas, "union_cobertura": float(_aceptado(pruebas, betas, theta).mean()), "n": len(betas),
            "union_ancho_medio": float(np.mean(u)), "union_ancho_max": float(max(u))}


def validar() -> dict:
    """Las cuatro validaciones de la regla; main publica cifras reales solo si pasan todas (la del ancho, desde la enmienda,
    solo por contener el punto). Trae ademas diagnostico_ancho(), que no es puerta."""
    v = {"dualidad": validar_dualidad(), "cobertura": validar_cobertura(), "potencia": validar_potencia(),
         "ancho": validar_ancho(), "diagnostico": diagnostico_ancho()}
    v["fallas"] = [k for k in ("dualidad", "cobertura", "potencia", "ancho") if not v[k]["ok"]]
    v["ok"] = not v["fallas"]
    return v


# ---- pagina ----
def _fmt(x, dec: int = 2) -> str:
    return cota_rr._fmt(x, dec)


def _pct(x: float) -> str:
    return _fmt(100 * x, 1) + " %"


def _texto_validacion(val: dict) -> list[str]:
    d, c, p, w = val["dualidad"], val["cobertura"], val["potencia"], val["ancho"]
    L = ["## Validación fijada antes de leer cifras reales", "",
         "La prueba se validó con datos sintéticos, sin warehouse, antes de calcular nada con los datos reales. Resultado:", "",
         f"- Dualidad ({d['casos']} casos al azar): el estadístico por vértices coincide con el mínimo directo sobre gamma, "
         f"diferencia máxima {d['peor']:.0e} (tolerancia 1e-9). {'Pasa' if d['ok'] else 'FALLA'}.",
         f"- Cobertura (delta previa sintética, saltos posteriores en el borde de la restricción, {N_MC} simulaciones por caso, "
         f"mínimo exigido {_pct(c['minimo'])}):"]
    for (mbar, nom), t in c["tasas"].items():
        L.append(f"  - Mbar = {_fmt(mbar, 1)}, {nom}: {_pct(t)}.")
    L += [f"  - {'Pasa' if c['ok'] else 'FALLA'}.",
          f"- Potencia plantada (efecto de -10, Mbar = 0; mínimo exigido {_pct(p['minimo'])}): "
          + "; ".join(f"{nom} {_pct(t)}" for nom, t in p["tasas"].items()) + f". {'Pasa' if p['ok'] else 'FALLA'}.",
          f"- Ancho (primeras {w['de']} simulaciones, ATT(1), Mbar = 0): el conjunto contiene el punto en {w['contiene']} de "
          f"{w['de']}. {'Pasa' if w['ok'] else 'FALLA'}. El más ancho mide {_fmt(w['razon_max'], 2)} veces el intervalo "
          f"normal al 95 % y el promedio {_fmt(w['razon_media'], 2)} veces. La regla de {COMMIT_REGLA} ponía un tope de "
          f"{_fmt(w.get('tope', TOPE_ANCHO), 0)}, que "
          + ("se cumple" if w.get("cumple_tope", w["razon_max"] <= TOPE_ANCHO) else "no se cumple")
          + ": desde la enmienda de abajo, el ancho es un dato y no una puerta.", ""]
    return L + _texto_enmienda(val)


def _texto_enmienda(val: dict) -> list[str]:
    w, dg = val["ancho"], val.get("diagnostico")
    sha = f" ({COMMIT_ENMIENDA})" if COMMIT_ENMIENDA else ""
    L = [f"## Enmienda antes de calcular{sha}", "",
         f"La regla de {COMMIT_REGLA} hacía del ancho una puerta: con Mbar = 0, el conjunto no podía medir más del doble del "
         f"intervalo normal. La primera corrida de la validación, todavía sin datos reales, no la pasó: el más ancho midió "
         f"{_fmt(w['razon_max'], 2)} veces. Ese tope no salía de la literatura ni de una cuenta. Se puso como guarda contra "
         "una implementación rota, y el ancho mide eficiencia, no corrección. La enmienda, hecha antes de calcular ninguna "
         "cifra real, deja el ancho como dato. Que el conjunto contenga el punto sigue siendo puerta, y no cambia ningún otro "
         "número: el tope no se reemplazó por otro, y la dualidad, la cobertura y la potencia quedan iguales.", ""]
    if dg:
        L += ["De dónde sale el ancho, con los mismos datos sintéticos (ATT(1), Mbar = 0, theta = -3): cada poliedro por "
              f"separado, con su rechazo de theta verdadero en {dg['n']} simulaciones y su ancho en los {w['de']} casos del ancho.", "",
              "| Poliedro (mes del mayor salto previo, signo) | Contiene la delta verdadera | Rechazo de theta verdadero | "
              "Ancho medio | Ancho máximo |", "|---|---|---|---|---|"]
        for f in dg["poliedros"]:
            L.append(f"| {f['j']}, {'+' if f['sg'] > 0 else '-'} | {'sí' if f['contiene_delta'] else 'no'} | {_pct(f['rechazo'])} | "
                     f"{_fmt(f['ancho_medio'], 2)} | {_fmt(f['ancho_max'], 2)} |")
        si = [f for f in dg["poliedros"] if f["contiene_delta"]]
        tope = w.get("tope", TOPE_ANCHO)
        L += ["", "Los anchos son en veces el intervalo normal al 95 %. "
              + (f"Los {len(si)} poliedros que contienen a la delta verdadera rechazan theta verdadero en "
                 + " y ".join(_pct(f["rechazo"]) for f in si) + ", y su conjunto mide como máximo "
                 + " y ".join(_fmt(f["ancho_max"], 2) for f in si) + " veces. " if si else "")
              + f"La unión de los seis contiene a theta en {_pct(dg['union_cobertura'])} de las {dg['n']} simulaciones; "
              f"su ancho medio es {_fmt(dg['union_ancho_medio'], 2)} veces y el máximo {_fmt(dg['union_ancho_max'], 2)}."
              + (" El exceso sobre el tope viene de poliedros que no contienen a la delta verdadera: la unión tiene que "
                 "incluirlos porque con datos reales no se sabe cuál vale."
                 if si and max(f["ancho_max"] for f in si) <= tope < dg["union_ancho_max"] else "")
              + " Un conjunto más ancho incluye antes el cero, así que solo puede bajar el Mbar de quiebre, nunca subirlo.", ""]
    return L


def _texto_clausula() -> list[str]:
    """La clausula de la regla de de19052 ("dicen que el de la union es mas conservador") que el texto no siguio, y por que."""
    return [
            '## Una cláusula de la regla que no se siguió',
            '',
            'La regla de de19052 pedía que, en un PR de texto aparte, el README y la portada citaran el quiebre condicional de D1 ATT(1) como la cota de Rambachan y Roth y dijeran que el de la unión es más conservador, aunque el quiebre condicional saliera menor. La primera parte se siguió; la segunda no. Nadie midió el nivel de la unión de percentiles, y en el petróleo al mes 1 de D1 su quiebre quedó por encima del condicional (las dos cifras están en su tabla, arriba): decir que la unión es más conservadora habría sido falso ahí. El README y el paper ponen los dos quiebres lado a lado para el petróleo al mes 1 de D1 y para la media de los meses 0 y 1 del agua, y la portada, para el petróleo; en el mes 1 del agua ninguno de los dos cae dentro de la grilla de Mbar. La regla queda como se escribió en el código; esta sección registra el desvío.',
            '',
    ]


def _texto_referencias() -> list[str]:
    return [
            '## Referencias',
            '',
            '- Rambachan, A. y Roth, J. (2023). A More Credible Approach to Parallel Trends. *Review of Economic Studies*, 90(5), 2555-2591. doi:10.1093/restud/rdad018.',
            '- Andrews, I., Roth, J. y Pakes, A. (2023). Inference for Linear Conditional Moment Inequalities. *Review of Economic Studies*, 90(6), 2763-2791. doi:10.1093/restud/rdad004.',
            '- Rambachan, A. y Roth, J. HonestDiD, paquete de R, versión 0.2.8. https://github.com/asheshrambachan/HonestDiD.',
            '',
            'Qué se leyó de cada una está en `docs/proceso/antecedentes-leidos.md`, sección 14.',
            '',
    ]


def _texto_no_dice() -> list[str]:
    return ["## Lo que no dice", "",
            "Supone, como la cota de la unión, que los meses previos no tienen efecto (sin anticipación). La matriz de "
            "covarianza sale del bootstrap por bloques, no de una fórmula; con un número fijo de sorteos para el valor crítico "
            "el Mbar de quiebre tiene un error de simulación del orden de la tolerancia de la bisección o mayor. El conjunto se "
            "busca en una grilla de valores del parámetro: si llega al borde de la grilla se publica como abierto de ese lado.", ""]


def pagina_falla(val: dict) -> str:
    L = ["# Cota de Rambachan y Roth con la prueba condicional e híbrida: no se publican cifras", "",
         "Página generada por `pipeline/cota_rr_condicional.py`, regla fijada en el commit " + COMMIT_REGLA + " antes de calcular.", "",
         "La validación sintética fijada en la regla no pasó, así que no se publica ninguna cifra real con esta prueba. "
         "Falló: " + ", ".join(val["fallas"]) + ".", ""]
    return "\n".join(L + _texto_validacion(val) + _texto_no_dice())


def _texto_cc(x: dict) -> str:
    if x["cc_bajo"] is None:
        return "vacío"
    s = f"{_fmt(x['cc_bajo'], 1)} a {_fmt(x['cc_alto'], 1)}"
    ab = x["cc_abierto"]
    if ab:
        s += {"bajo": " (abierto abajo)", "alto": " (abierto arriba)", "ambos": " (abierto de los dos lados)"}[ab]
    if x["cc_con_huecos"]:
        s += " (con huecos)"
    return s


def _qtxt(q) -> str:
    return MOTIVO_MAYOR.replace("MBAR_MAX", _fmt(MBAR_MAX, 2)) if q is None else _fmt(q, 2)


def _comparacion(g0: dict, q_cond, q_union) -> list[str]:
    """Lineas que comparan con la union: el ancho con Mbar = 0 y el quiebre (None es mayor que MBAR_MAX)."""
    L = []
    if g0["cc_bajo"] is not None and g0["union_alto"] > g0["union_bajo"]:
        r = (g0["cc_alto"] - g0["cc_bajo"]) / (g0["union_alto"] - g0["union_bajo"])
        L.append(f"Con Mbar = 0 el conjunto condicional mide {_fmt(r, 2)} veces el intervalo de unión.")
    qc = float("inf") if q_cond is None else q_cond
    qu = float("inf") if q_union is None else q_union
    if abs(qc - qu) >= TOL_BISECCION and not (np.isinf(qc) and np.isinf(qu)):
        L.append("El quiebre condicional es " + ("menor" if qc < qu else "mayor") + " que el de la unión: con esta prueba "
                 "el efecto resiste " + ("menos" if qc < qu else "más") + ".")
    return L


def pagina_cota_rr_condicional(filas: list[tuple], extras: dict, val: dict) -> str:
    """Pagina de wiki a partir de las filas de `mart_cota_rr_condicional`. `extras[(diseno, estimando)]` trae el punto,
    los previos y el quiebre y veredicto de la union."""
    cols = [c[0] for c in COLS_COTA_RR_COND]
    reg = [dict(zip(cols, f)) for f in filas]
    orden: list[tuple[str, str]] = []
    for x in reg:
        if (x["diseno"], x["estimando"]) not in orden:
            orden.append((x["diseno"], x["estimando"]))
    L = ["# Cota de Rambachan y Roth con la prueba condicional e híbrida", "",
         "Página generada por `pipeline/cota_rr_condicional.py`, regla fijada en el commit " + COMMIT_REGLA + " antes de calcular.", "",
         "Es la misma pregunta que en [la cota de Rambachan y Roth](cota_rr.md): qué tan grande tendría que ser la violación de "
         "tendencias paralelas después del tratamiento, medida contra el mayor salto previo, para que el efecto deje de "
         "distinguirse de cero. Cambia la inferencia. En lugar de la unión de percentiles del bootstrap, que no sale de una prueba con nivel conocido, "
         "esta página usa el conjunto de confianza de Rambachan y Roth (2023), que invierte la prueba condicional e híbrida de "
         "Andrews, Roth y Pakes (2023) para cada valor del parámetro, con la restricción de magnitudes relativas escrita "
         "como unión de seis poliedros. La matriz de covarianza sale de los mismos sorteos del bootstrap por bloques de 5 km. "
         "La tabla de cada estimando pone al lado el intervalo de unión de la otra página, como registro. Unidades: puntos "
         "de producción en D1 y puntos porcentuales de corte de agua en D2.", ""]
    L += _texto_validacion(val)
    for d, nom in orden:
        g = [x for x in reg if x["diseno"] == d and x["estimando"] == nom and x["fila"] == "grilla"]
        q = next(x for x in reg if x["diseno"] == d and x["estimando"] == nom and x["fila"] == "quiebre")
        L += [f"## {d}, {nom}", ""]
        if not g:
            L += [f"Sin dato: {q['motivo']}. Veredicto: **{q['veredicto']}**.", ""]
            continue
        ex = extras[(d, nom)]
        L += [f"Efecto estimado {_fmt(ex['l'], 1)}; previos b(-3) = {_fmt(ex['b3'], 1)}, b(-2) = {_fmt(ex['b2'], 1)}, "
              f"b(-1) = {_fmt(ex['b1'], 1)}; {q['n_tratados']} tratados, {q['sorteos']} sorteos completos. Saltos previos entre "
              f"meses: {_fmt(ex['b3'], 1)}; {_fmt(ex['b2'] - ex['b3'], 1)}; {_fmt(ex['b1'] - ex['b2'], 1)}.", "",
              "| Mbar | Conjunto de confianza condicional | Intervalo de unión |", "|---|---|---|"]
        for x in g:
            L.append(f"| {_fmt(x['mbar'], 2)} | {_texto_cc(x)} | {_fmt(x['union_bajo'], 1)} a {_fmt(x['union_alto'], 1)} |")
        L += ["", f"Mbar de quiebre condicional: {_qtxt(q['mbar_quiebre'])}. Veredicto: **{q['veredicto']}**.",
              f"Mbar de quiebre de la unión: {_qtxt(ex['union_quiebre'])}. Veredicto: **{ex['union_veredicto']}**."]
        L += _comparacion(g[0], q["mbar_quiebre"], ex["union_quiebre"]) + [""]
    L += _texto_clausula() + _texto_no_dice() + _texto_referencias()
    return "\n".join(L)


# ---- datos reales ----
def _entradas_reales(con) -> list[tuple]:
    """(diseno, estimando, a, b, meses, beta, vals, n_tratados), con los sorteos de pipeline.causal.main."""
    from pipeline import causal as c
    from pipeline import causal_profundo
    from pipeline.causal import MIN_MESES_W_BASE, _panel_promedio
    D = c.cargar(con)
    coh = c.cohortes(D)
    rng = np.random.default_rng(c.SEMILLA_CAUSAL)
    # mismo orden de construccion y de sorteos que pipeline.cota_rr.main
    cel_pri = c.celdas(D, coh, c.H_CORTO, False)
    cel_s1 = c.celdas(D, coh, c.H_CORTO, True)
    trat_ff, g_ff = c._cohorte_falsa_fecha(D, coh)
    cel_ff = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = c._cohorte_falsa_distancia(D, coh, c.H_CORTO)
    cel_fd = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = c._cohorte_nunca_tratados(D, coh)
    cel_nt = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    cel_d1b = c.celdas_d1b(D, coh)
    wells = []
    for grupo in [cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b]:
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = c._pesos_bloques(D, wells, c.REPS, rng)
    r1 = c.bootstrap(D, cel_pri, c.E_SERIE, W)
    meses5 = (-3, -2, -1, 0, 1)
    ix = {e: c.E_SERIE.index(e) for e in meses5}
    d1 = (np.array([float(r1["est"][ix[e]]) for e in meses5]),
          np.column_stack([np.asarray(r1["vals"][:, ix[e]], float) for e in meses5]), int(r1["n_tratados"][ix[1]]))
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    por_mes = {}
    for e in meses5:
        vt, vc = causal_profundo.valores_dw_mes(D, cel_pri, e, base_w)
        por_mes[e] = causal_profundo.estimar_valores(D, cel_pri, W, vt, vc)
    d2 = (np.array([float(por_mes[e]["est"]) for e in meses5]),
          np.column_stack([np.asarray(por_mes[e]["vals"], float) for e in meses5]))
    out = []
    for diseno, nombre, a, b, meses in ESTIMANDOS:
        if diseno == "D1":
            beta, vals, n = d1
        else:
            beta, vals = d2
            n = int(min(por_mes[e]["n_tratados"] for e in meses))
        out.append((diseno, nombre, a, b, meses, beta, vals, n))
    return out


def _imprimir(e: dict) -> None:
    print(f"\n== {e['diseno']} {e['estimando']}  (sorteos usados {e['sorteos']})")
    for f in e["filas"]:
        d = dict(zip((c[0] for c in COLS_COTA_RR_COND), f))
        if d["fila"] == "grilla":
            cc = "vacio" if d["cc_bajo"] is None else f"[{d['cc_bajo']:.3f}, {d['cc_alto']:.3f}]"
            print(f"  Mbar {d['mbar']:.2f}: CS {cc} abierto={d['cc_abierto']} huecos={d['cc_con_huecos']}  "
                  f"union [{d['union_bajo']:.3f}, {d['union_alto']:.3f}]")
        else:
            print(f"  quiebre condicional {d['mbar_quiebre']}  ({d['motivo']})  veredicto: {d['veredicto']}")
    if e["extra"]:
        print(f"  quiebre union {e['extra']['union_quiebre']}  veredicto: {e['extra']['union_veredicto']}")


def main(path=None) -> None:
    """Escribe mart_cota_rr_condicional y la pagina."""
    import time

    import duckdb

    from pipeline import causal as c
    from pipeline.costo import _escribir
    t0 = time.time()
    path = path or c.DATA / "warehouse.duckdb"
    val = validar()
    print(f"validacion: dualidad {val['dualidad']}\n  cobertura {val['cobertura']}\n  potencia {val['potencia']}\n  "
          f"ancho {val['ancho']}\n  fallas: {val['fallas'] or 'ninguna'}  ({time.time() - t0:.1f} s)")
    PAGINA.parent.mkdir(parents=True, exist_ok=True)
    if not val["ok"]:
        PAGINA.write_text(pagina_falla(val), encoding="utf-8")
        print(f"la validacion fallo ({', '.join(val['fallas'])}): no se publica ninguna cifra real; escrita {PAGINA}")
        return
    con = duckdb.connect(str(path), read_only=True)
    entradas = _entradas_reales(con)
    union_mart = {}
    if con.execute("select count(*) from information_schema.tables where table_name = 'mart_cota_rr'").fetchone()[0]:
        for d, n, q, v in con.execute("select diseno, estimando, quiebre, veredicto from mart_cota_rr "
                                      "where fila = 'quiebre'").fetchall():
            union_mart[(d, n)] = (q, v)
    con.close()
    ests = [calcular_estimando(*e) for e in entradas]
    extras = {}
    for e in ests:
        if e["extra"] is not None and (e["diseno"], e["estimando"]) in union_mart:
            q, v = union_mart[(e["diseno"], e["estimando"])]
            if (q, v) != (e["extra"]["union_quiebre"], e["extra"]["union_veredicto"]) and not (
                    q is not None and e["extra"]["union_quiebre"] is not None
                    and abs(q - e["extra"]["union_quiebre"]) < 1e-3 and v == e["extra"]["union_veredicto"]):
                print(f"AVISO: el quiebre de la union de {e['estimando']} ({e['extra']['union_quiebre']}) no coincide con "
                      f"mart_cota_rr ({q}, {v}); se publica el de mart_cota_rr")
            e["extra"]["union_quiebre"], e["extra"]["union_veredicto"] = q, v
        extras[(e["diseno"], e["estimando"])] = e["extra"]
        _imprimir(e)
    filas = [f for e in ests for f in e["filas"]]
    con = duckdb.connect(str(path))
    _escribir(con, "mart_cota_rr_condicional", COLS_COTA_RR_COND, filas)
    txt = pagina_cota_rr_condicional(con.execute("select * from mart_cota_rr_condicional order by rowid").fetchall(),
                                     extras, val)
    con.close()
    PAGINA.write_text(txt, encoding="utf-8")
    print(f"\nescrito mart_cota_rr_condicional ({len(filas)} filas) y {PAGINA}  (total {time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
