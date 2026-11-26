"""Potencia del resultado nulo de dosis y respuesta: que efecto minimo habria podido ver este dato.

Se corre despues de pipeline.dosis y pipeline.dosis_pad:  uv run python -m pipeline.potencia_dosis

REGLA FIJADA ANTES DE CORRER (2026-11-17, antes de calcular ninguna cifra de potencia de este modulo; no se cambia despues de ver
resultados). Solo se miraron los conteos de eventos y pads de los marts de dosis y los IC que ya estan publicados. No es una prueba
nueva sobre la caida: es la pregunta inversa de pipeline.dosis y pipeline.dosis_pad. Dice cuanto efecto de la dosis podria haber
pasado inadvertido con este tamano de muestra, que es lo que le dice a un operador que dato interno hace falta. NUNCA se escribe que
un efecto "queda descartado": la potencia dice cuan grande tiene que ser un efecto para verse, no que los efectos menores no existan.

Modelos cubiertos (resultado A, caida del indice al mes 1, el que decide; resultado B, caudal por dia, se informa aparte con el mismo
codigo y no cambia el de A):
  * "conjunto": las cuatro variables de pipeline.dosis (mart_dosis_modelo), n = 1.544 (A) y 1.395 (B), 262 y 247 pads hijo.
  * "pad_completo": las cuatro variables de pipeline.dosis_pad, modelo "completo" de mart_dosis_pad.
  * "pad_cercania": las cinco de pipeline.dosis_pad, modelo "cercania" (km_min < 0,5, con la interaccion depleccion por cercania).

Cuenta analitica (todos los modelos y variables, por cada fila publicada de coeficiente):
  1. Error estandar a partir del IC 95% de percentiles ya publicado: SE = (ic_alto - ic_bajo) / (2 * 1,96). Es una APROXIMACION
     normal: supone que la distribucion bootstrap es simetrica y de cola normal; la simulacion de abajo la valida.
  2. Unidades: desvios de la caida. Un coeficiente de los marts esta en unidades del indice por desvio de la dosis; se divide por el
     desvio (ddof = 0) de la caida de la muestra de cada modelo: el de y[cc] de pipeline.dosis (conjunto), el de la muestra
     de caso completo de pipeline.dosis_pad (pad_completo) y el del subconjunto km_min < 0,5 (pad_cercania). La muestra se reconstruye
     con las mismas funciones (dosis._mascara_controles, variables finitas, km_min < 0,5) y debe dar el n y los pads del mart.
  3. Efecto minimo detectable con 80% de potencia (MDE80), a dos colas con alfa = 0,05 sin ajustar: (1,96 + 0,8416) * SE. Version
     conservadora con Holm: (z(1 - alfa / (2 m)) + 0,8416) * SE con m = 4 (conjunto, pad_completo) o m = 5 (pad_cercania); z es el
     cuantil de la normal estandar (statistics.NormalDist). Es la version conservadora de Holm (la del paso mas exigente); el
     verdadero Holm paso a paso es algo menos exigente cuando hay varias variables con efecto.
  4. Pads y eventos necesarios para que el MDE80 llegue a un efecto objetivo (0,1 y 0,2 desvios de la caida): factor =
     (MDE80 / objetivo) ** 2, pads necesarios = pads actuales * factor, eventos necesarios = n actual * factor (el SE baja como 1 sobre
     la raiz del numero de conglomerados con eventos por pad constantes; se escribe asi). Si el factor es menor que 1, la muestra
     actual ya alcanza y se informa tal cual (factor < 1). Se informa con el MDE sin ajustar y con el de Holm.

Simulacion de planta y recupera (valida la cuenta analitica; solo el modelo "conjunto" del resultado A, n = 1.544, 262 pads hijo):
  1. Con los datos reales de pipeline.dosis._dataset_a se arma la muestra de caso completo y se ajusta el modelo conjunto (mismas
     variables estandarizadas, controles dosis._controles incluidas las dummies de terminacion, efectos fijos de area por ano).
     Se guarda beta (los cuatro coeficientes de dosis). La caida "limpia" es y0 = y - X beta: le quita al dato el efecto de dosis
     estimado, asi el efecto verdadero de la simulacion es exactamente el que se planta y 0 para las otras tres variables.
  2. Cada corrida r (r = 0 a N_CORRIDAS - 1) sortea con reemplazo tantos pads hijo como tiene la muestra (262), cada pad trae todas
     sus filas (variables, controles, celda de efectos fijos, y0) y recibe una clave unica; la semilla del sorteo depende solo de r
     (numeros aleatorios comunes entre variables y deltas).
  3. Se planta el efecto: y_sim = y0 + delta * sd_y * X[:, j], con X estandarizada en la muestra original (no se re-estandariza) y
     sd_y el desvio de la caida de la muestra. delta esta en desvios de la caida por desvio de la dosis; una variable j por vez.
  4. Se reajusta con dosis._ajuste (bootstrap por pads con B = B_SIM = 300) y se aplica la regla de pipeline.dosis: la variable "se
     ve" con la regla de Holm si coef > 0 y p ajustado por Holm (dosis._holm sobre los cuatro p) < 0,05; con la regla sin ajustar si
     coef > 0 y p < 0,05 (p de dos colas de dosis._p_boot).
  5. Deltas: 0 (tamano de la regla, 4 variables en un solo ajuste por corrida, se informa la fraccion que "se ve" con cada regla),
     0,1, 0,2, el MDE80 sin ajustar de esa variable (con la regla sin ajustar) y el MDE80 de Holm de esa variable (con la regla de
     Holm). Los MDE vienen de la cuenta analitica del modelo conjunto A. N_CORRIDAS = 200; semillas: sorteo SEMILLA_POT + r; bootstrap
     SEMILLA_POT + 100_000 + 10_000 * indice_de_delta + 1_000 * indice_de_variable + r; SEMILLA_POT = dosis.SEMILLA_DOSIS + 2_000_000.
  6. Potencia empirica = fraccion de corridas en que la variable plantada "se ve". Error de Monte Carlo = sqrt(p (1 - p) / 200) y se
     publica. Valida la cuenta analitica si la potencia empirica en el MDE80 (con su regla) esta entre 0,70 y 0,90 en las cuatro
     variables; si no, la pagina lo dice (la cuenta analitica es optimista o pesimista) y el veredicto sigue siendo el analitico.

Veredicto (con el resultado A, modelo conjunto, mayor MDE80 de Holm de las cuatro variables; B se informa aparte):
  * "alcanza para 0,1": el mayor MDE80 de Holm es de 0,1 desvios de la caida o menos.
  * "alcanza para 0,2 y no para 0,1": mayor que 0,1 y de hasta 0,2.
  * "no alcanza para 0,2": mayor que 0,2. Se escribe que un efecto de 0,2 desvios de la caida por desvio de la dosis puede pasar
    inadvertido con este dato, y que el nulo de pipeline.dosis no descarta efectos de ese tamano ni menores.
  El veredicto de pipeline.dosis y el de pipeline.dosis_pad no cambian con este modulo.

Aritmetica del dato interno (se informa, es ilustracion y no estimacion): si un dato interno (espaciamiento real, geometria de la
fractura, presion de monitoreo, registros de cierre) explicara una parte R2 de la varianza que hoy queda sin explicar de la caida,
el error estandar baja en un factor raiz de (1 - R2) (MCO, lo demas igual); R2 en (0,1, 0,25, 0,5), MDE80 de Holm del modelo
conjunto A multiplicado por ese factor. Son entradas, no una prediccion de cuanto explicaria un dato real.

Que NO prueba:
  * La potencia es sobre el efecto lineal de la dosis estandarizada con la forma del modelo; no dice nada de efectos no lineales,
    de umbrales ni de interacciones que no estan en el modelo (salvo la interaccion de pad_cercania).
  * El SE sale de un IC de percentiles; la simulacion valida solo el modelo conjunto A, no los de pad ni el resultado B.
  * Supone que un dato nuevo se parece al actual (mismas areas, mismo ruido, eventos por pad parecidos).
  * No dice que el efecto exista: dice cuan grande tendria que ser para verse con este dato.
"""
from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor
from statistics import NormalDist

import duckdb
import numpy as np

from pipeline import dosis, dosis_pad
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

Z95 = 1.959963984540054
Z80 = 0.8416212335729143
ALFA = 0.05
OBJETIVOS = (0.1, 0.2)
N_CORRIDAS = 200
B_SIM = 300
SEMILLA_POT = dosis.SEMILLA_DOSIS + 2_000_000
MODELOS = ("conjunto", "pad_completo", "pad_cercania")

COLS_POTENCIA_DOSIS = [
    ("resultado", "varchar"), ("modelo", "varchar"), ("variable", "varchar"),
    ("n", "integer"), ("pads", "integer"), ("sd_caida", "double"),
    ("coef_desvios", "double"), ("se_desvios", "double"), ("m", "integer"),
    ("mde80_desvios", "double"), ("mde80_holm_desvios", "double"),
    ("pads_01", "double"), ("pads_02", "double"),
    ("eventos_01", "double"), ("eventos_02", "double"),
    ("pads_01_holm", "double"), ("pads_02_holm", "double"),
    ("eventos_01_holm", "double"), ("eventos_02_holm", "double"),
]
COLS_SIM = [
    ("variable", "varchar"), ("nivel", "varchar"), ("delta_desvios", "double"),
    ("regla", "varchar"), ("corridas", "integer"), ("se_ve", "integer"),
    ("potencia", "double"), ("error_mc", "double"),
]
COLS_VEREDICTO_POT = [("resultado", "varchar"), ("codigo", "varchar"), ("texto", "varchar")]

# Titulo corto de cada modelo para la pagina.
TITULO_MODELO = {"conjunto": "modelo conjunto", "pad_completo": "pad, muestra completa",
                 "pad_cercania": "pad, cercania"}


def se_desde_ic(ic_bajo, ic_alto):
    """Error estandar aproximado desde un IC 95 por ciento ya publicado."""
    return (ic_alto - ic_bajo) / (2 * Z95)


def mde80(se):
    """Efecto minimo detectable con 80 por ciento de potencia, sin ajustar."""
    return (Z95 + Z80) * se


def mde80_holm(se, m):
    """Version conservadora con Holm: paso mas exigente sobre m pruebas."""
    z = NormalDist().inv_cdf(1 - ALFA / (2 * m))
    return (z + Z80) * se


def necesarios(mde, objetivo, n, pads):
    """Pads y eventos para que el MDE llegue al objetivo, sin redondear."""
    factor = (mde / objetivo) ** 2
    return {"factor": factor, "pads": pads * factor, "eventos": n * factor}


def veredicto(mde_holm_max):
    """Codigo y texto del veredicto con el mayor MDE80 de Holm del conjunto."""
    m = float(mde_holm_max)
    cita = f"{_g(m, 2)} desvíos de la caída por desvío de la dosis"
    if m <= 0.1:
        return ("alcanza para 0,1",
                f"el mayor MDE80 de Holm del modelo conjunto es de {cita}: "
                "la muestra alcanza para ver un efecto de 0,1 desvíos")
    if m <= 0.2:
        return ("alcanza para 0,2 y no para 0,1",
                f"el mayor MDE80 de Holm del modelo conjunto es de {cita}: "
                "la muestra alcanza para ver un efecto de 0,2 desvíos y no uno de 0,1")
    return ("no alcanza para 0,2",
            f"el mayor MDE80 de Holm del modelo conjunto es de {cita}: "
            "un efecto de 0,2 desvíos de la caída por desvío de la dosis puede pasar inadvertido "
            "con este dato, y el nulo de pipeline.dosis no descarta efectos de ese tamaño ni menores")


def aritmetica_interna(mde_holm_max, r2s=(0.1, 0.25, 0.5)):
    """MDE por raiz de (1 menos R2): ilustracion, no estimacion."""
    m = float(mde_holm_max)
    return [(r2, m * (1 - r2) ** 0.5) for r2 in r2s]


def _caso_completo(y, d):
    """Indices de caso completo con la misma regla de dosis.analizar."""
    y = np.asarray(y, dtype=float)
    base = np.flatnonzero(np.isfinite(y))
    ib = base[dosis._mascara_controles(d, base)]
    return ib[np.all([np.isfinite(d[f"v{j + 1}"][ib]) for j in range(4)], axis=0)]


def _mart_dosis(con, res):
    return {r[0]: r for r in con.execute(
        "select variable, coef_sd, ic_bajo, ic_alto, p, p_holm, n, pads from mart_dosis_modelo "
        "where resultado = ?", [res]).fetchall()}


def _mart_pad(con, res, modelo):
    return {r[0]: r for r in con.execute(
        "select variable, coef_sd, ic_bajo, ic_alto, p, p_holm, n, pads from mart_dosis_pad "
        "where resultado = ? and modelo = ?", [res, modelo]).fetchall()}


def analitica(con):
    """Cuenta analitica sobre los marts publicados e insumos de la simulacion del conjunto A.

    Devuelve (filas de mart_potencia_dosis, insumos con y0, X, C, grupo, clave y sd_y).
    La muestra de cada modelo se reconstruye con las mismas funciones y debe dar el n
    y los pads del mart; si no coinciden, falla con un error claro.
    """
    d = dosis._dataset_a(con)
    ys = {"A": np.asarray(d["caida"], dtype=float), "B": np.asarray(dosis._caida_b(con, d), dtype=float)}
    d2 = dict(d)
    d2["v1"], d2["v2"], d2["v3"] = dosis_pad._variables_pad(con, d, 1)
    clusters = np.asarray(d["cluster"])
    filas = []
    insumos = {}
    for res in ("A", "B"):
        y = ys[res]
        cc_conj = _caso_completo(y, d)
        cc_pad = _caso_completo(y, d2)
        sub = cc_pad[np.asarray(d2["km"][cc_pad]) < 0.5]
        muestras = {"conjunto": cc_conj, "pad_completo": cc_pad, "pad_cercania": sub}
        marts = {"conjunto": (_mart_dosis(con, res), dosis.VARIABLES, 4),
                 "pad_completo": (_mart_pad(con, res, "completo"), dosis_pad.VARIABLES_PAD, 4),
                 "pad_cercania": (_mart_pad(con, res, "cercania"), dosis_pad.VARIABLES_CERCA, 5)}
        for modelo in MODELOS:
            cc = np.asarray(muestras[modelo])
            mart, variables, m = marts[modelo]
            n = len(cc)
            pads = len(set(clusters[cc]))
            sd_y = float(y[cc].std())
            for var in variables:
                fila = mart.get(var)
                if fila is None:
                    raise RuntimeError(f"mart sin fila para {res} {modelo} {var}")
                _v, coef, lo, hi, _p, _ph, n_mart, pads_mart = fila
                if int(n_mart) != n or int(pads_mart) != pads:
                    raise RuntimeError(f"muestra reconstruida de {res} {modelo} (n = {n}, pads = {pads}) "
                                       f"no coincide con el mart (n = {n_mart}, pads = {pads_mart})")
                coef_d = coef / sd_y
                se_d = se_desde_ic(lo, hi) / sd_y
                mde = mde80(se_d)
                mde_h = mde80_holm(se_d, m)
                nec1 = necesarios(mde, 0.1, n, pads)
                nec2 = necesarios(mde, 0.2, n, pads)
                neh1 = necesarios(mde_h, 0.1, n, pads)
                neh2 = necesarios(mde_h, 0.2, n, pads)
                filas.append((res, modelo, var, n, pads, sd_y, coef_d, se_d, m, mde, mde_h,
                              nec1["pads"], nec2["pads"], nec1["eventos"], nec2["eventos"],
                              neh1["pads"], neh2["pads"], neh1["eventos"], neh2["eventos"]))
        if res == "A":
            cc = cc_conj
            X = np.column_stack([dosis._std(d[f"v{j + 1}"][cc]) for j in range(4)])
            C, grupo = dosis._controles(d, cc)
            beta = dosis._ols(dosis._demean(y[cc], grupo),
                              dosis._demean(np.column_stack([X, C]), grupo))[:4]
            insumos = {"y0": y[cc] - X @ beta, "X": X, "C": C, "grupo": grupo,
                       "clave": clusters[cc], "sd_y": float(y[cc].std())}
    return filas, insumos


def _una_corrida(tarea):
    """Una corrida r completa: sorteo de pads, nivel 0 y cada delta plantado. Va a otro proceso."""
    r, y0, X, C, grupo, clave, sd_y, niveles_idx, reps, semilla_base = tarea
    rng = np.random.default_rng(semilla_base + r)
    pads = np.unique(clave)
    por_pad = [np.flatnonzero(clave == p) for p in pads]
    pick = rng.integers(0, len(pads), len(pads))
    filas = np.concatenate([por_pad[i] for i in pick])
    clave_nueva = np.repeat(np.arange(len(pick)), [len(por_pad[i]) for i in pick])
    Xf, Cf, gf, y0f = X[filas], C[filas], grupo[filas], y0[filas]
    out = []
    coefs, _ics, ps = dosis._ajuste(y0f, Xf, Cf, gf, clave_nueva, semilla_base + 100_000 + r, reps)
    ph = dosis._holm(ps)
    for j in range(X.shape[1]):
        out.append((j, "0", 0.0, "holm", int(coefs[j] > 0 and ph[j] < ALFA)))
        out.append((j, "0", 0.0, "sin_ajustar", int(coefs[j] > 0 and ps[j] < ALFA)))
    for nombre, deltas, idx_delta in niveles_idx:
        for j, dj in enumerate(deltas):
            y_sim = y0f + dj * sd_y * Xf[:, j]
            sem = semilla_base + 100_000 + 10_000 * idx_delta + 1_000 * j + r
            coefs, _ics, ps = dosis._ajuste(y_sim, Xf, Cf, gf, clave_nueva, sem, reps)
            ph = dosis._holm(ps)
            out.append((j, nombre, float(dj), "holm", int(coefs[j] > 0 and ph[j] < ALFA)))
            out.append((j, nombre, float(dj), "sin_ajustar", int(coefs[j] > 0 and ps[j] < ALFA)))
    return out


def simular(y0, X, C, grupo, clave, sd_y, niveles, corridas=N_CORRIDAS, reps=B_SIM,
            semilla_base=SEMILLA_POT, workers=1):
    """Planta y recupera: filas (variable_idx, nivel, delta, regla, corridas, se_ve).

    niveles es una lista de (nombre, vector de 4 deltas). El nivel "0" (tamano, sin
    plantar, un solo ajuste por corrida) siempre se agrega con indice de delta 0; los
    niveles dados llevan indices 1, 2, ... en el orden recibido. Con workers = 1 corre
    en serie; si no, reparte una corrida por tarea entre procesos.
    """
    y0 = np.asarray(y0, dtype=float)
    X = np.asarray(X, dtype=float)
    C = np.asarray(C, dtype=float)
    grupo = np.asarray(grupo, dtype=int)
    clave = np.asarray(clave)
    sd_y = float(sd_y)
    niveles_idx = [(nombre, [float(v) for v in deltas], k + 1) for k, (nombre, deltas) in enumerate(niveles)]
    orden_nivel = {"0": 0}
    for nombre, _deltas, idx in niveles_idx:
        orden_nivel[nombre] = idx
    tareas = [(r, y0, X, C, grupo, clave, sd_y, niveles_idx, reps, semilla_base) for r in range(corridas)]
    if workers == 1:
        resultados = [_una_corrida(t) for t in tareas]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            resultados = list(ex.map(_una_corrida, tareas))
    conteo = {}
    for res in resultados:
        for j, nombre, dj, regla, vio in res:
            k = (j, nombre, dj, regla)
            conteo[k] = conteo.get(k, 0) + vio
    return [(j, nombre, dj, regla, corridas, conteo[(j, nombre, dj, regla)])
            for j, nombre, dj, regla in sorted(conteo, key=lambda k: (orden_nivel[k[1]], k[0], k[3]))]


def main(path=DATA / "warehouse.duckdb"):
    con = duckdb.connect(str(path))
    filas, insumos = analitica(con)
    por_var = {(r[0], r[1], r[2]): r for r in filas}
    mdes = [por_var[("A", "conjunto", v)][9] for v in dosis.VARIABLES]
    mdes_h = [por_var[("A", "conjunto", v)][10] for v in dosis.VARIABLES]
    niveles = [("0,1", [0.1] * 4), ("0,2", [0.2] * 4), ("mde_sin_ajustar", mdes), ("mde_holm", mdes_h)]
    t0 = time.perf_counter()
    sim = simular(insumos["y0"], insumos["X"], insumos["C"], insumos["grupo"], insumos["clave"],
                  insumos["sd_y"], niveles, workers=4)
    dt = time.perf_counter() - t0
    filas_sim = []
    for j, nivel, delta, regla, corridas, se_ve in sim:
        p = se_ve / corridas
        filas_sim.append((dosis.NOMBRES[dosis.VARIABLES[j]], nivel, delta, regla, corridas, se_ve,
                          p, (p * (1 - p) / corridas) ** 0.5))
    _escribir(con, "mart_potencia_dosis", COLS_POTENCIA_DOSIS, filas)
    _escribir(con, "mart_potencia_dosis_sim", COLS_SIM, filas_sim)
    verdictos = []
    for res in ("A", "B"):
        mayor = max(por_var[(res, "conjunto", v)][10] for v in dosis.VARIABLES)
        codigo, texto = veredicto(mayor)
        verdictos.append((res, codigo, texto))
    _escribir(con, "mart_potencia_dosis_veredicto", COLS_VEREDICTO_POT, verdictos)
    for r in filas:
        print(f"[potencia_dosis] {r[0]} {r[1]:<12} {r[2]:<14} n={r[3]} pads={r[4]} "
              f"coef={r[6]:+.4f} se={r[7]:.4f} mde={r[9]:.4f} mde_holm={r[10]:.4f}")
    for r in filas_sim:
        print(f"[potencia_dosis] sim {r[0]:<28} {r[1]:<15} {r[3]:<11} delta={r[2]:.4f} "
              f"potencia={r[6]:.3f} +- {r[7]:.3f} ({r[5]}/{r[4]})")
    for res, codigo, texto in verdictos:
        print(f"[potencia_dosis] veredicto {res}: {codigo}: {texto}")
    print(f"[potencia_dosis] simulacion: {dt:.1f} s")
    con.close()


def _nombre(var):
    return dosis.NOMBRES.get(var, dosis_pad.NOMBRES_PAD.get(var, var))


def pagina_potencia_dosis(con):
    """Pagina de wiki desde los marts de potencia_dosis. Solo lee, no recalcula."""
    ver = {r[0]: (r[1], r[2]) for r in con.execute(
        "select resultado, codigo, texto from mart_potencia_dosis_veredicto").fetchall()}
    pot = {(r[0], r[1], r[2]): r for r in con.execute("select * from mart_potencia_dosis").fetchall()}
    sim = con.execute("select * from mart_potencia_dosis_sim").fetchall()
    L = ["# Potencia del nulo de dosis y respuesta", "",
         "Página generada por `pipeline/potencia_dosis.py`. Pregunta inversa de pipeline.dosis y "
         "pipeline.dosis_pad: cuánto efecto de la dosis podría haber pasado inadvertido con este "
         "tamaño de muestra, y qué dato interno haría falta para ver efectos más chicos. Todo en "
         "desvíos de la caída por desvío de la dosis.", "",
         "## Veredicto", ""]
    for res in ("A", "B"):
        codigo, texto = ver[res]
        L.append(f"Resultado {res}: **{codigo}**: {texto}.")
    L.append("")
    L += ["## Efecto mínimo detectable", "",
          "MDE80: efecto mínimo con 80% de potencia, a dos colas con alfa 0,05, desde el IC 95% "
          "publicado. La versión con Holm es la conservadora (paso más exigente sobre 4 o 5 pruebas).", ""]
    for res in ("A", "B"):
        for modelo in MODELOS:
            variables = (dosis.VARIABLES if modelo == "conjunto" else dosis_pad.VARIABLES_PAD
                         if modelo == "pad_completo" else dosis_pad.VARIABLES_CERCA)
            r0 = pot[(res, modelo, variables[0])]
            L += [f"### Resultado {res}, {TITULO_MODELO[modelo]} (n = {_g(r0[3])}, pads = {_g(r0[4])})", "",
                  "| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |",
                  "| --- | ---: | ---: | ---: | ---: |"]
            for var in variables:
                r = pot[(res, modelo, var)]
                L.append(f"| {_nombre(var)} | {_g(r[6], 3)} | {_g(r[7], 3)} | {_g(r[9], 3)} | {_g(r[10], 3)} |")
            L.append("")
    L += ["## Pads y eventos para ver 0,1 y 0,2 desvíos", "",
          "Pads y eventos necesarios para que el MDE80 llegue a cada objetivo, con el MDE sin "
          "ajustar y con el de Holm. Si el número necesario es menor que el actual (factor menor "
          "que 1), la muestra actual ya alcanza para ese objetivo. La cuenta supone eventos por "
          "pad constantes: el error baja como 1 sobre la raíz del número de pads.", ""]
    for res in ("A", "B"):
        for modelo in MODELOS:
            variables = (dosis.VARIABLES if modelo == "conjunto" else dosis_pad.VARIABLES_PAD
                         if modelo == "pad_completo" else dosis_pad.VARIABLES_CERCA)
            r0 = pot[(res, modelo, variables[0])]
            L += [f"### Resultado {res}, {TITULO_MODELO[modelo]} "
                  f"(actual: n = {_g(r0[3])}, pads = {_g(r0[4])})", "",
                  "| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | "
                  "Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
            for var in variables:
                r = pot[(res, modelo, var)]
                L.append(f"| {_nombre(var)} | {_g(r[11])} | {_g(r[13])} | {_g(r[15])} | {_g(r[17])} | "
                         f"{_g(r[12])} | {_g(r[14])} | {_g(r[16])} | {_g(r[18])} |")
            L.append("")
    L += ["## Simulación de planta y recupera (modelo conjunto, resultado A)", "",
          "Potencia empírica: fracción de corridas en que la variable plantada se ve, con error de "
          "Monte Carlo. El nivel 0 es el tamaño (sin efecto plantado).", "",
          "| Variable | Nivel | Delta (desvíos) | Regla | Corridas | Se ve | Potencia | Error MC |",
          "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |"]
    for _v, n, dl, rg, cr, sv, p, e in sim:
        regla = "Holm" if rg == "holm" else "sin ajustar"
        L.append(f"| {_v} | {n} | {_g(dl, 3)} | {regla} | {_g(cr)} | {_g(sv)} | {_g(p, 3)} | {_g(e, 3)} |")
    L.append("")
    valida = {(n, rg): [p for _v, nn, _d, rr, _c, _s, p, _e in sim if nn == n and rr == rg]
              for n, rg in (("mde_sin_ajustar", "sin_ajustar"), ("mde_holm", "holm"))}
    pares = valida[("mde_sin_ajustar", "sin_ajustar")] + valida[("mde_holm", "holm")]
    if len(pares) == 8 and all(0.70 <= p <= 0.90 for p in pares):
        L.append("La simulación valida la cuenta analítica: la potencia empírica en el MDE80 (con su "
                 "regla, sin ajustar y Holm) está entre 0,70 y 0,90 en las cuatro variables.")
    elif pares:
        bajo = any(p < 0.70 for p in pares)
        alto = any(p > 0.90 for p in pares)
        lado = ("optimista en unas variables y pesimista en otras" if bajo and alto else
                "optimista" if bajo else "pesimista")
        L.append("La simulación no valida la cuenta analítica: la potencia empírica en el MDE80 (con su "
                 f"regla) queda fuera de 0,70 a 0,90 en alguna variable, así que la cuenta analítica es "
                 f"{lado}; el veredicto sigue siendo el analítico.")
        if bajo:
            L.append("Agregado después de ver los resultados (no cambia el veredicto): parte de la diferencia puede venir de la resolución "
                     "del bootstrap de la simulación. Con B = 300 el p mínimo posible es 2 sobre 301, y con Holm sobre cuatro pruebas una "
                     "variable solo pasa si ningún sorteo cae del lado contrario, un umbral más exigente que el normal de la cuenta "
                     "analítica; así que la simulación puede subestimar la potencia, y la cuenta analítica no es necesariamente tan "
                     "optimista como parece.")
    else:
        L.append("La simulación no trae las filas de MDE para validar la cuenta analítica.")
    tam0 = {(rg): [p for _v, nn, _d, rr, _c, _s, p, _e in sim if nn == "0" and rr == rg]
            for rg in ("sin_ajustar", "holm")}
    if tam0["sin_ajustar"] and tam0["holm"]:
        L.append(f"Tamaño (nivel 0, sin efecto plantado): la fracción que se ve va de "
                 f"{_g(min(tam0['sin_ajustar']), 3)} a {_g(max(tam0['sin_ajustar']), 3)} con la regla "
                 f"sin ajustar y de {_g(min(tam0['holm']), 3)} a {_g(max(tam0['holm']), 3)} con Holm, "
                 "entre las cuatro variables.")
    L.append("")
    mayor_a = max(pot[("A", "conjunto", v)][10] for v in dosis.VARIABLES)
    L += ["## Qué dato interno achicaría el error", "",
          f"El mayor MDE80 de Holm del modelo conjunto A es de {_g(mayor_a, 2)} desvíos: si un dato "
          "interno explicara una parte R2 de la varianza que hoy queda sin explicar, el error "
          "bajaría como la raíz de (1 menos R2). Ilustración, no estimación: las R2 son entradas, "
          "no una predicción de cuánto explicaría un dato real.", "",
          "| R2 que explicaría el dato interno | MDE80 de Holm (desvíos) |",
          "| ---: | ---: |"]
    for r2, m in aritmetica_interna(mayor_a):
        L.append(f"| {_g(r2, 2)} | {_g(m, 2)} |")
    L += ["", "Datos internos que podrían achicar el error:", "",
          "- espaciamiento real entre ramas",
          "- geometría de la fractura",
          "- presión de monitoreo del pozo padre durante la fractura del hijo",
          "- registros de cierre con fecha y hora",
          "- tamaño de la ventana de cierre", "",
          "## Regla fijada antes de correr", "",
          "- Error estándar desde el IC 95% publicado: (alto menos bajo) sobre (2 por 1,96); todo en "
          "desvíos de la caída.",
          "- MDE80 sin ajustar y versión conservadora con Holm sobre 4 pruebas (conjunto y pad "
          "completo) o 5 (cercanía).",
          "- Pads y eventos necesarios con factor (MDE sobre objetivo) al cuadrado, a 0,1 y 0,2 "
          "desvíos, sin ajustar y con Holm.",
          "- Simulación de planta y recupera solo en el modelo conjunto A: 200 corridas con deltas "
          "0, 0,1, 0,2 y los dos MDE de cada variable.",
          "- Veredicto con el mayor MDE80 de Holm del conjunto; el resultado B se informa aparte.", "",
          "## Qué no prueba", "",
          "- La potencia es sobre el efecto lineal de la dosis estandarizada con la forma del modelo; "
          "no dice nada de efectos no lineales, de umbrales ni de interacciones que no están en el "
          "modelo (salvo la interacción de pad_cercania).",
          "- El SE sale de un IC de percentiles; la simulación valida solo el modelo conjunto A, no "
          "los de pad ni el resultado B.",
          "- Supone que un dato nuevo se parece al actual (mismas áreas, mismo ruido, eventos por "
          "pad parecidos).",
          "- No dice que el efecto exista: dice cuán grande tendría que ser para verse con este dato.",
          ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
