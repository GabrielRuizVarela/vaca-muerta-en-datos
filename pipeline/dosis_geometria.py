"""Dosis y respuesta con la geometria de las ramas, detras de una puerta de potencia: los padres cercanos medidos entre ramas.

Se corre despues de pipeline.alcance_rama y pipeline.potencia_dosis:  uv run python -m pipeline.dosis_geometria

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los modelos que se calculen, favorables o no. Un veredicto
"sin muestra" o "la geometria no da mas potencia" es un resultado terminado: no se rediseña la regla para evitarlo. Fuente del plan:
fase 4 del proyecto, unidad U4. Sigue a pipeline.dosis (seccion 3.8), pipeline.potencia_dosis (el MDE de hoy) y pipeline.alcance_rama
(la definicion de padre cercano entre ramas).

Que se habia mirado antes de fijarla
- Publicado en el repo: wiki/hallazgos/dosis.md, potencia_dosis.md, trayectorias.md y alcance_rama.md. De la potencia de hoy se leyo el
  MDE80 de Holm de las cuatro variables del modelo conjunto A (de 0,221 a 0,313 desvios de la caida; el mejor, el de la presion
  maxima, 0,221).
- De la muestra de esta pagina solo se vio que mart_trayectoria_par existe con las columnas hijo, padre, mes_frac, km, m_min,
  m_mediana, dtvd_m y misma_unidad, y que int_interferencia_evento tiene las bandas cercano, intermedio y control. No se conto el
  tamaño del subconjunto de esta pagina, no se calculo ningun error estandar ni ningun coeficiente con el.

Pregunta. El mejor efecto minimo detectable de la dosis hasta hoy es de 0,22 desvios de la caida. Medir el padre cercano por la
distancia entre ramas (en vez de la de superficie) podria afinar la exposicion y dar mas potencia. Esta pagina lo prueba en dos
pasos: primero la puerta de potencia (el MDE80 de la muestra de padres cercanos entre ramas, sin estimar ningun efecto), y solo si
la puerta pasa, el modelo conjunto de pipeline.dosis sobre esa muestra.

Muestra (la misma para los dos pasos)
- Eventos: los de pipeline.dosis._dataset_a (los eventos 'cercano' de int_interferencia_evento, padre a menos de 1 km en superficie del
  hijo_cercano; el hijo, el mes, la caida A y la caida B no cambian), SOLO los que cumplen: el par (hijo_cercano, padre) del evento esta
  en mart_trayectoria_par (la rama del hijo y la del padre medidas) y su `m_min` (menor distancia entre ramas en planta) es menor que
  CERCA_RAMA_M = 600 m, la misma definicion de padre cercano entre ramas de pipeline.alcance_rama (H-R2, medida A).
- Caso completo: el de pipeline.dosis y pipeline.potencia_dosis._caso_completo (caida A finita, controles completos, las cuatro
  variables finitas). Los controles, las dummies de terminacion, las celdas de efectos fijos y la estandarizacion se rehacen DENTRO del
  subconjunto con las mismas funciones (dosis._controles, dosis._std). km_min sigue siendo la distancia de superficie y `m_min` no
  entra como control: la regla del modelo no cambia, solo la muestra.
- Un subconjunto no puede traer eventos que el modelo de dosis no tenga: los padres con la rama a menos de 600 m del hijo pero con la
  boca a 1 km o mas del hijo no estan en la muestra de dosis. La pagina lo dice y no lo corrige.
- Resultados: A (caida del indice al mes 1) decide; B (caudal por dia) se calcula igual, solo para el MDE analitico y, si la puerta
  pasa, para el modelo conjunto, y no cambia ningun veredicto.
- Los conglomerados son los pads hijo de pipeline.dosis (pad_id del hijo; sin pad, el hijo es su propio conglomerado).
- "sin muestra": el caso completo de A tiene menos de N_MIN_CASOS (100) eventos o menos de PADS_MIN (30) pads hijo. No se calcula
  nada mas y no hay puerta.

Paso 1, la puerta de potencia (no se lee ni se publica ningun coeficiente; solo el ancho de los intervalos)
  * Cuenta analitica, la de pipeline.potencia_dosis: el modelo conjunto de las cuatro variables de pipeline.dosis sobre la muestra, con
    dosis._ajuste y bootstrap de pads hijo con B_GATE = dosis.B_MAIN (2.000) y semilla propia; SE = (ic_alto menos ic_bajo) sobre
    (2 por 1,96) y despues sobre el desvio (ddof = 0) de la caida de la muestra; MDE80 de Holm = (z(1 menos 0,05 sobre 2 por 4) mas
    0,8416) por SE, con m = M_HOLM = 4 (las mismas cuatro variables). Se publica tambien el MDE80 sin ajustar. Del bootstrap solo se usa
    el ancho del IC de percentiles.
  * Estadistico de la puerta: el menor de los cuatro MDE80 de Holm (el de la mejor variable). Es lo que se compara con "el mejor de
    hoy", 0,221 (presion maxima, modelo conjunto A de pipeline.potencia_dosis), que se fija en MDE_REF = 0,22. Se publica tambien el
    mayor de los cuatro (el estadistico del veredicto de pipeline.potencia_dosis, 0,31 hoy) y su codigo de potencia_dosis.veredicto,
    como informacion; no deciden la puerta.
  * Puerta: pasa si el menor MDE80 de Holm de A es MENOR que MDE_REF (0,22). Si es igual o mayor, el veredicto es "la geometria no da
    mas potencia", se publica el MDE y se termina (unidad terminada: no se corre el paso 2).
  * Simulacion de planta y recupera, la de pipeline.potencia_dosis.simular sobre la misma muestra y el mismo modelo conjunto A (ajusta
    el modelo, le quita a la caida el efecto estimado de las cuatro variables, planta un efecto delta por variable y reajusta con
    B_SIM = 300 sobre N_CORRIDAS = 200 remuestras de pads). Niveles: delta 0 (tamaño), 0,1, 0,2, MDE_REF (0,22), el MDE80 sin ajustar de
    cada variable (con la regla sin ajustar) y el MDE80 de Holm de cada variable (con la regla de Holm). Se publica la potencia
    empirica con su error de Monte Carlo. La simulacion valida la cuenta analitica si la potencia empirica en el MDE80 (con su regla)
    esta entre 0,70 y 0,90 en las cuatro variables; si no, la pagina lo dice y la puerta SIGUE siendo la analitica. La simulacion usa
    los coeficientes ajustados solo para armar la caida limpia; no se publican como resultado.
  * Tambien se publica, como en pipeline.potencia_dosis, cuantos pads y eventos harian falta para ver 0,1 y 0,2 desvios.

Paso 2, solo si la puerta pasa: el modelo conjunto de pipeline.dosis (dosis.analizar, A y B, con quintiles, modelo conjunto, FIV y
sensibilidades) sobre la muestra, con las reglas de la seccion 3.8 SIN cambios: dosis y respuesta si dos o mas variables tienen signo
positivo y p ajustado por Holm sobre las cuatro menor que 0,05; una sola variable; sin dosis y respuesta; orden sin coeficiente; y
"no concluyente por muestra" cuando hay menos de 1.000 eventos de caso completo o menos de 150 pads hijo (esa regla se aplica tal
cual: si el subconjunto es mas chico, el veredicto es ese). El veredicto sale solo del resultado A con el modelo conjunto
(dosis.veredicto); B y los quintiles se publican y no lo cambian. Si la puerta no pasa, no se publica ningun coeficiente de dosis.

Veredictos de la puerta (VEREDICTOS_PUERTA)
  * "sin muestra": ver arriba.
  * "la geometria no da mas potencia": el menor MDE80 de Holm de A es MDE_REF (0,22) o mas.
  * "la geometria da mas potencia": el menor MDE80 de Holm de A es menor que MDE_REF. Entonces se corre el paso 2 y se publica su
    veredicto (el de pipeline.dosis) junto a este.

Que NO prueba
  * La potencia es sobre el efecto lineal de la dosis estandarizada con la forma del modelo; no dice nada de efectos no lineales, de
    umbrales ni de interacciones. El SE sale de un IC de percentiles; la simulacion lo valida solo para el modelo conjunto A.
  * La muestra es la parte de los eventos de dosis con las dos ramas medidas: las trayectorias laterales cubren el 76 a 98% de los
    hijos fracturados de 2016 a 2023 (86% en conjunto) pero solo el 39% de los de 2024 y el 25% de los de 2025, asi que la muestra es
    sobre todo de 2016 a 2023 y no dice nada de 2024 en adelante.
  * "La geometria no da mas potencia" dice que este dato, con esta definicion de cercano, no alcanza para ver un efecto menor que
    0,22 desvios de la caida; no dice que no haya dosis y respuesta ni golpes de fractura. NUNCA se escribe que un efecto "queda
    descartado": la potencia dice cuan grande tiene que ser un efecto para verse. Una cota superior es una cota superior.
  * Medir entre ramas no mide el espaciamiento real ni la geometria de la fractura: es la distancia en planta de las ramas.
  * La definicion de cercano usa el hijo de pipeline.dosis (el mas cercano en superficie); un padre golpeado por otro hijo del pad queda
    clasificado por el hijo mas cercano en superficie.

Que cambia con cada veredicto (en la pagina, el README y los limites)
  * "la geometria no da mas potencia": la pagina da el MDE y dice que medir los padres cercanos entre ramas no baja el efecto minimo
    detectable de 0,22 desvios; el README y "Limites" repiten la linea y la muestra. No cambia el veredicto de pipeline.dosis.
  * "la geometria da mas potencia": ademas de lo anterior, la pagina publica el modelo conjunto y su veredicto, y el README y "Limites"
    dicen que el veredicto de dosis sobre esta muestra es ese (nunca "efecto descartado").
  * "sin muestra": la pagina lo dice con los conteos y no cambia ninguna linea de los demas resultados.
  * Nada de esto cambia data/prospectiva_congelada.json ni las reglas P1 y P2.
"""
from __future__ import annotations

import time

import duckdb
import numpy as np

from pipeline import dosis, potencia_dosis
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

SEMILLA_GEO = dosis.SEMILLA_DOSIS + 3_000_000   # una semilla propia (potencia_dosis usa +2.000.000)
CERCA_RAMA_M = 600.0                    # padre cercano entre ramas: m_min menor que esto (el de alcance_rama, H-R2 medida A)
MDE_REF = 0.22                          # el mejor MDE80 de Holm de hoy (potencia_dosis, conjunto A, presion maxima: 0,221)
M_HOLM = 4                              # las cuatro variables de dosis.VARIABLES
N_MIN_CASOS = 100                       # eventos de caso completo minimos para que haya puerta
PADS_MIN = 30                           # pads hijo minimos para que haya puerta
B_GATE = dosis.B_MAIN                   # remuestras del bootstrap de pads del paso 1 (2.000)
N_CORRIDAS = potencia_dosis.N_CORRIDAS  # corridas de la simulacion (200)
B_SIM = potencia_dosis.B_SIM            # remuestras del bootstrap dentro de cada corrida (300)
OBJETIVOS = potencia_dosis.OBJETIVOS    # efectos objetivo para pads y eventos necesarios (0,1 y 0,2)
VALIDA_ENTRE = (0.70, 0.90)             # la simulacion valida el MDE80 si la potencia empirica cae en este rango
NIVELES_SIM = ("0", "0,1", "0,2", "0,22", "mde_sin_ajustar", "mde_holm")
RESULTADOS = ("A", "B")                 # A decide; B se informa aparte
# El texto publicado lleva tildes (el docstring de arriba no): "la geometría no da más potencia", "la geometría da más potencia".
VEREDICTOS_PUERTA = ("sin muestra", "la geometría no da más potencia", "la geometría da más potencia")

# ------------------------------------------------------------------ constantes de la regla

SHA_REGLA = "59b3a26"   # commit donde quedo fijada la regla, antes de calcular ningun numero

COLS_GEO_MUESTRA = [
    ("resultado", "varchar"), ("eventos_dosis", "integer"), ("con_par", "integer"),
    ("cercano_rama", "integer"), ("caso_completo", "integer"), ("pads", "integer"),
]
COLS_GEO_POT = [
    ("resultado", "varchar"), ("variable", "varchar"), ("n", "integer"), ("pads", "integer"),
    ("sd_caida", "double"), ("se_desvios", "double"), ("m", "integer"),
    ("mde80_desvios", "double"), ("mde80_holm_desvios", "double"),
    ("pads_01", "double"), ("pads_02", "double"), ("eventos_01", "double"), ("eventos_02", "double"),
    ("pads_01_holm", "double"), ("pads_02_holm", "double"),
    ("eventos_01_holm", "double"), ("eventos_02_holm", "double"),
]
COLS_GEO_SIM = potencia_dosis.COLS_SIM
COLS_GEO_VEREDICTO = potencia_dosis.COLS_VEREDICTO_POT
COLS_GEO_PUERTA = [
    ("codigo", "varchar"), ("texto", "varchar"), ("n", "integer"), ("pads", "integer"),
    ("mde_menor_holm", "double"), ("mde_mayor_holm", "double"), ("mde_ref", "double"),
    ("codigo_potencia", "varchar"), ("pasa", "boolean"), ("valida_simulacion", "boolean"),
]
TABLAS_PASO2 = ("mart_dosis_geometria_modelo", "mart_dosis_geometria_quintiles",
                "mart_dosis_geometria_orden", "mart_dosis_geometria_sens",
                "mart_dosis_geometria_veredicto")

# Nota de cobertura de las trayectorias, textual (la pagina la publica tal cual).
NOTA_MUESTRA = ("Las trayectorias laterales cubren el 76 a 98% de los hijos fracturados de 2016 a 2023 "
                "(86% en conjunto) pero solo el 39% de los de 2024 y el 25% de los de 2025, así que la "
                "muestra es sobre todo de 2016 a 2023.")

# ------------------------------------------------------------------ muestra


def mascara_rama(d_hijo, d_padre, pares: dict) -> np.ndarray:
    """m_min de cada evento a partir del par (hijo, padre); nan si el par no esta medido."""
    d_hijo = np.asarray(d_hijo)
    d_padre = np.asarray(d_padre)
    out = np.full(len(d_hijo), np.nan)
    for i in range(len(d_hijo)):
        v = pares.get((int(d_hijo[i]), int(d_padre[i])))
        if v is not None:
            out[i] = float(v)
    return out


def dentro_de_rama(m_min) -> np.ndarray:
    """Cercano entre ramas: m_min menor que CERCA_RAMA_M. nan y el valor exacto no entran."""
    m = np.asarray(m_min, dtype=float)
    return np.isfinite(m) & (m < CERCA_RAMA_M)


def _pares(con) -> dict:
    """Diccionario (hijo, padre) con la distancia entre ramas en planta (m_min)."""
    hay = con.execute("select count(*) from information_schema.tables "
                      "where table_name = 'mart_trayectoria_par'").fetchall()[0][0]
    if not hay:
        raise RuntimeError("falta mart_trayectoria_par: correr pipeline.trayectorias antes")
    filas = con.execute("select hijo, padre, m_min from mart_trayectoria_par").fetchall()
    pares = {}
    for hijo, padre, m_min in filas:
        if m_min is None:
            continue
        v = float(m_min)
        if np.isfinite(v):
            pares[(int(hijo), int(padre))] = v
    return pares


def muestra(con) -> dict:
    """Muestra de la pagina: eventos de dosis con el par medido y cercano entre ramas.

    Devuelve d (los arreglos de pipeline.dosis), m_min por evento, la caida de A y de B
    restringida a la muestra, los indices de caso completo de cada resultado y los conteos.
    """
    d = dosis._dataset_a(con)
    pares = _pares(con)
    m_min = mascara_rama(d["hijo"], d["padre"], pares)
    dentro = dentro_de_rama(m_min)
    y_b = np.asarray(dosis._caida_b(con, d), dtype=float)
    y_a = np.asarray(d["caida"], dtype=float)
    ys, cc, conteos = {}, {}, {}
    for res in RESULTADOS:
        y = y_a if res == "A" else y_b
        yr = np.where(dentro, y, np.nan)
        c = potencia_dosis._caso_completo(yr, d)
        ys[res] = yr
        cc[res] = c
        conteos[res] = {
            "eventos_dosis": int(len(d["padre"])),
            "con_par": int(np.isfinite(m_min).sum()),
            "cercano_rama": int(dentro.sum()),
            "caso_completo": int(len(c)),
            "pads": int(len(set(np.asarray(d["cluster"])[c].tolist()))) if len(c) else 0,
        }
    return {"d": d, "m_min": m_min, "ys": ys, "cc": cc, "conteos": conteos}


# ------------------------------------------------------------------ puerta de potencia


def puerta_resultado(y, d, cc, res) -> dict:
    """Puerta analitica de un resultado: MDE80 sin ajustar y de Holm, sin leer ningun coeficiente.

    Del bootstrap solo se usa el ancho del intervalo. Devuelve las filas del mart de potencia
    y los insumos de la simulacion (los coeficientes ajustados solo para armar la caida limpia).
    """
    y = np.asarray(y, dtype=float)
    cc = np.asarray(cc)
    n = int(len(cc))
    pads = int(len(set(np.asarray(d["cluster"])[cc].tolist())))
    X = np.column_stack([dosis._std(d[f"v{j + 1}"][cc]) for j in range(4)])
    C, grupo = dosis._controles(d, cc)
    semilla = SEMILLA_GEO + 500_000 + dosis.RES_OFFSET[res]
    coefs, ics, _p = dosis._ajuste(y[cc], X, C, grupo, d["cluster"][cc], semilla, B_GATE)
    sd_y = float(y[cc].std())
    filas = []
    for j, var in enumerate(dosis.VARIABLES):
        lo, hi = float(ics[j][0]), float(ics[j][1])
        se = potencia_dosis.se_desde_ic(lo, hi) / sd_y
        mde = potencia_dosis.mde80(se)
        mde_h = potencia_dosis.mde80_holm(se, M_HOLM)
        nec = {o: (potencia_dosis.necesarios(mde, o, n, pads),
                   potencia_dosis.necesarios(mde_h, o, n, pads)) for o in OBJETIVOS}
        filas.append((res, dosis.NOMBRES[var], n, pads, sd_y, se, M_HOLM, mde, mde_h,
                      nec[0.1][0]["pads"], nec[0.2][0]["pads"],
                      nec[0.1][0]["eventos"], nec[0.2][0]["eventos"],
                      nec[0.1][1]["pads"], nec[0.2][1]["pads"],
                      nec[0.1][1]["eventos"], nec[0.2][1]["eventos"]))
    beta = dosis._ols(dosis._demean(y[cc], grupo),
                      dosis._demean(np.column_stack([X, C]), grupo))[:4]
    return {"filas": filas, "beta": beta, "X": X, "C": C, "grupo": grupo,
            "clave": np.asarray(d["cluster"])[cc], "sd_y": sd_y, "y0": y[cc] - X @ beta}


def veredicto_puerta(mde_menor, n, pads) -> tuple[str, str]:
    """Codigo y texto de la puerta. Solo usa el ancho del intervalo, nunca un coeficiente."""
    ref = _g(MDE_REF, 2)
    if n < N_MIN_CASOS or pads < PADS_MIN:
        texto = (f"el caso completo del resultado A tiene {_g(n)} eventos y {_g(pads)} pads hijo: "
                 f"hacen falta {N_MIN_CASOS} eventos y {PADS_MIN} pads para que haya puerta de potencia")
        return (VEREDICTOS_PUERTA[0], texto)
    m = float(mde_menor)
    cita = f"{_g(m, 2)} desvíos de la caída por desvío de la dosis"
    if m >= MDE_REF:
        texto = (f"el menor MDE80 de Holm del resultado A es de {cita}: medir los padres cercanos entre "
                 f"ramas no baja el efecto mínimo detectable por debajo de {ref} desvíos de la caída por "
                 f"desvío de la dosis. Esto no dice que no haya dosis y respuesta ni golpes de fractura: "
                 f"la potencia dice qué tamaño de efecto hace falta para verse")
        return (VEREDICTOS_PUERTA[1], texto)
    texto = (f"el menor MDE80 de Holm del resultado A es de {cita}: medir los padres cercanos entre "
             f"ramas baja el efecto mínimo detectable por debajo de {ref} desvíos de la caída por "
             f"desvío de la dosis")
    return (VEREDICTOS_PUERTA[2], texto)


def valida_simulacion(filas) -> bool | None:
    """True si la potencia empirica esta en VALIDA_ENTRE en los dos niveles con su regla.

    None si faltan filas: sin simulacion no se puede validar la cuenta analitica.
    """
    precios = {}
    for f in filas or []:
        variable, nivel, regla, corridas, se_ve = f[0], f[1], f[3], f[4], f[5]
        if nivel == "mde_sin_ajustar" and regla == "sin_ajustar":
            precios[(variable, nivel)] = se_ve / corridas
        elif nivel == "mde_holm" and regla == "holm":
            precios[(variable, nivel)] = se_ve / corridas
    for var in dosis.VARIABLES:
        nombre = dosis.NOMBRES[var]
        for nivel in ("mde_sin_ajustar", "mde_holm"):
            if (nombre, nivel) not in precios:
                return None
    lo, hi = VALIDA_ENTRE
    return all(lo <= p <= hi for p in precios.values())


# ------------------------------------------------------------------ escritura de marts


def _borrar_paso2(con) -> None:
    """Sin paso 2 no queda ninguna tabla vieja de la muestra."""
    for tabla in TABLAS_PASO2:
        con.execute(f"drop table if exists {tabla}")


def _paso2(con, d, ys) -> None:
    """El modelo conjunto de pipeline.dosis sobre la muestra, solo si la puerta pasa."""
    rA = dosis.analizar("A", ys["A"], d)
    rB = dosis.analizar("B", ys["B"], d)
    _escribir(con, "mart_dosis_geometria_modelo", dosis.COLS_MODELO, rA["modelo"] + rB["modelo"])
    _escribir(con, "mart_dosis_geometria_quintiles", dosis.COLS_QUINTILES,
              rA["quintiles"] + rB["quintiles"])
    _escribir(con, "mart_dosis_geometria_orden", dosis.COLS_ORDEN, rA["orden"] + rB["orden"])
    _escribir(con, "mart_dosis_geometria_sens", dosis.COLS_SENS, rA["sens"] + rB["sens"])
    codA, texA = dosis.veredicto(rA["cumplen"], rA["contrarias"], rA["ordenes"], rA["n"], rA["pads"],
                                  rA["semiancho"], rA["cota"])
    codB, texB = dosis.veredicto(rB["cumplen"], rB["contrarias"], rB["ordenes"], rB["n"], rB["pads"],
                                  rB["semiancho"], rB["cota"])
    if codA == "dosis y respuesta":
        texA += ", " + ("y la parte de caudal por día lo confirma" if len(rB["cumplen"]) >= 2
                        else "pero la parte de caudal por día no lo muestra por separado")
    _escribir(con, "mart_dosis_geometria_veredicto", COLS_GEO_VEREDICTO,
              [("A", codA, texA), ("B", codB, texB)])
    for r in rA["modelo"] + rB["modelo"]:
        print(f"[dosis_geometria] modelo {r[0]} {r[1]:<12} coef={r[2]:+.4f} "
              f"p_holm={r[6]:.4f} cumple={r[10]}")
    print(f"[dosis_geometria] veredicto A: {codA}: {texA}")
    print(f"[dosis_geometria] veredicto B: {codB}: {texB}")


def main(path=DATA / "warehouse.duckdb") -> None:
    """Corre la puerta de potencia y, solo si pasa, el modelo conjunto de la dosis."""
    con = duckdb.connect(str(path))
    m = muestra(con)
    d, cc, ys, conteos = m["d"], m["cc"], m["ys"], m["conteos"]
    _escribir(con, "mart_dosis_geometria_muestra", COLS_GEO_MUESTRA,
              [(res, conteos[res]["eventos_dosis"], conteos[res]["con_par"],
                conteos[res]["cercano_rama"], conteos[res]["caso_completo"],
                conteos[res]["pads"]) for res in RESULTADOS])
    n_a, pads_a = conteos["A"]["caso_completo"], conteos["A"]["pads"]
    filas_pot, puerta = [], {}
    for res in RESULTADOS:
        if len(cc[res]) < N_MIN_CASOS or conteos[res]["pads"] < PADS_MIN:
            continue
        r = puerta_resultado(ys[res], d, cc[res], res)
        filas_pot += r["filas"]
        puerta[res] = r
    if "A" not in puerta:
        codigo, texto = veredicto_puerta(None, n_a, pads_a)
        _escribir(con, "mart_dosis_geometria_potencia", COLS_GEO_POT, [])
        con.execute("drop table if exists mart_dosis_geometria_sim")
        _escribir(con, "mart_dosis_geometria_puerta", COLS_GEO_PUERTA,
                  [(codigo, texto, n_a, pads_a, None, None, MDE_REF, None, False, None)])
        _borrar_paso2(con)
        print(f"[dosis_geometria] {codigo}: {texto}")
        con.close()
        return
    filas_a = [f for f in filas_pot if f[0] == "A"]
    mdes = [f[7] for f in filas_a]
    mdes_h = [f[8] for f in filas_a]
    mde_menor, mde_mayor = min(mdes_h), max(mdes_h)
    codigo, texto = veredicto_puerta(mde_menor, n_a, pads_a)
    pasa = codigo == VEREDICTOS_PUERTA[2]
    codigo_potencia = potencia_dosis.veredicto(mde_mayor)[0]
    niveles = [("0,1", [0.1] * 4), ("0,2", [0.2] * 4), ("0,22", [MDE_REF] * 4),
               ("mde_sin_ajustar", mdes), ("mde_holm", mdes_h)]
    ins = puerta["A"]
    t0 = time.perf_counter()
    sim = potencia_dosis.simular(ins["y0"], ins["X"], ins["C"], ins["grupo"], ins["clave"],
                                 ins["sd_y"], niveles, semilla_base=SEMILLA_GEO, workers=4)
    dt = time.perf_counter() - t0
    filas_sim = []
    for j, nivel, delta, regla, corridas, se_ve in sim:
        p = se_ve / corridas
        filas_sim.append((dosis.NOMBRES[dosis.VARIABLES[j]], nivel, delta, regla, corridas, se_ve,
                          p, (p * (1 - p) / corridas) ** 0.5))
    valida = valida_simulacion(filas_sim)
    _escribir(con, "mart_dosis_geometria_potencia", COLS_GEO_POT, filas_pot)
    _escribir(con, "mart_dosis_geometria_sim", COLS_GEO_SIM, filas_sim)
    _escribir(con, "mart_dosis_geometria_puerta", COLS_GEO_PUERTA,
              [(codigo, texto, n_a, pads_a, mde_menor, mde_mayor, MDE_REF, codigo_potencia,
                pasa, valida)])
    if pasa:
        _paso2(con, d, ys)
    else:
        _borrar_paso2(con)
    for r in filas_pot:
        print(f"[dosis_geometria] {r[0]} {r[1]:<28} n={r[2]} pads={r[3]} "
              f"se={r[5]:.4f} mde={r[7]:.4f} mde_holm={r[8]:.4f}")
    for r in filas_sim:
        print(f"[dosis_geometria] sim {r[0]:<28} {r[1]:<15} {r[3]:<11} delta={r[2]:.4f} "
              f"potencia={r[6]:.3f} +- {r[7]:.3f} ({r[5]}/{r[4]})")
    print(f"[dosis_geometria] puerta: {codigo}: {texto}")
    print(f"[dosis_geometria] simulacion: {dt:.1f} s")
    con.close()


# ------------------------------------------------------------------ pagina de wiki


def _tiene_mart(con, tabla) -> bool:
    return con.execute("select count(*) from information_schema.tables where table_name = ?",
                       [tabla]).fetchall()[0][0] > 0


def pagina_dosis_geometria(con) -> str:
    """Pagina de wiki desde los marts de dosis_geometria. Solo lee, no recalcula."""
    puerta = con.execute("select codigo, texto, n, pads, mde_menor_holm, mde_mayor_holm, mde_ref, "
                          "codigo_potencia, pasa, valida_simulacion "
                          "from mart_dosis_geometria_puerta").fetchall()
    codigo, texto, n, pads, mde_menor, mde_mayor, mde_ref, codigo_pot, pasa, valida = puerta[0]
    mu = con.execute("select resultado, eventos_dosis, con_par, cercano_rama, caso_completo, pads "
                      "from mart_dosis_geometria_muestra").fetchall()
    pot = con.execute("select resultado, variable, n, pads, sd_caida, se_desvios, m, mde80_desvios, "
                       "mde80_holm_desvios, pads_01, pads_02, eventos_01, eventos_02, pads_01_holm, "
                       "pads_02_holm, eventos_01_holm, eventos_02_holm "
                       "from mart_dosis_geometria_potencia").fetchall()
    sim = []
    if _tiene_mart(con, "mart_dosis_geometria_sim"):
        sim = con.execute("select variable, nivel, delta_desvios, regla, corridas, se_ve, potencia, "
                           "error_mc from mart_dosis_geometria_sim").fetchall()
    hoy, hoy_n = [], None
    if _tiene_mart(con, "mart_dosis_modelo"):
        fila = con.execute("select max(n), max(pads) from mart_dosis_modelo where resultado = 'A'").fetchall()[0]
        if fila[0] is not None:
            hoy_n = (int(fila[0]), int(fila[1]))
    if _tiene_mart(con, "mart_potencia_dosis"):
        hoy = con.execute("select mde80_holm_desvios from mart_potencia_dosis "
                          "where resultado = 'A' and modelo = 'conjunto'").fetchall()
    L = ["# Dosis con la geometría de las ramas, detrás de una puerta de potencia", "",
         f"La regla se fijó antes de calcular cualquier número, en el commit {SHA_REGLA}, y no se "
         "cambia después de ver resultados. Se publican todos los modelos que se calculen, "
         "favorables o no. Esta página la genera `python -m pipeline.wiki` y no se edita a mano.", "",
         "## Lectura", ""]
    for r in mu:
        L.append(f"- Muestra, resultado {r[0]}: {_g(r[1])} eventos de dosis, {_g(r[2])} con el par "
                 f"(hijo, padre) medido entre ramas, {_g(r[3])} cercanos entre ramas (m_min menor que "
                 f"{_g(CERCA_RAMA_M)} m), {_g(r[4])} de caso completo y {_g(r[5])} pads hijo.")
    L.append(f"- Puerta: **{codigo}**: {texto}.")
    if mde_menor is not None:
        linea = (f"- Comparación: el menor MDE80 de Holm del resultado A es de "
                 f"{_g(mde_menor, 2)} desvíos de la caída por desvío de la dosis y el mayor es de "
                 f"{_g(mde_mayor, 2)}, contra la referencia de {_g(mde_ref, 2)} "
                 f"(el mejor MDE80 de Holm de hoy).")
        if hoy:
            vals = sorted(float(v[0]) for v in hoy)
            linea += (f" Hoy (pipeline.potencia_dosis, modelo conjunto A) los cuatro MDE80 de Holm van de "
                      f"{_g(vals[0], 2)} a {_g(vals[-1], 2)}.")
        if hoy_n:
            linea += (f" La muestra de hoy tiene {_g(hoy_n[0])} eventos y {_g(hoy_n[1])} pads hijo; "
                      "la de esta página es la parte con las dos ramas medidas y cercana entre ramas.")
        L.append(linea)
    else:
        L.append("- Puerta de potencia: no hay muestra suficiente del resultado A, así que no hay "
                 "MDE80 que comparar.")
    if valida is None:
        L.append("- Simulación de planta y recupera: no se pudo comparar con la cuenta analítica.")
    elif valida:
        L.append("- Simulación de planta y recupera: la potencia empírica valida la cuenta analítica "
                 "en los dos niveles con su regla.")
    else:
        L.append("- Simulación de planta y recupera: la potencia empírica no valida la cuenta "
                 "analítica; la puerta sigue siendo la analítica.")
    if pasa:
        L.append("- Modelo de dosis sobre esta muestra: se corrió porque la puerta pasó.")
    elif codigo == VEREDICTOS_PUERTA[0]:
        L.append("- Modelo de dosis sobre esta muestra: no se corrió nada más, sin muestra.")
    else:
        L.append("- Modelo de dosis sobre esta muestra: no se corrió, la puerta no pasó.")
    L.append("")
    L += ["## La puerta de potencia", "",
          "MDE80: efecto mínimo con 80% de potencia a dos colas con alfa 0,05, desde el ancho del "
          "intervalo de percentiles del bootstrap por pads hijo. La versión con Holm es la "
          "conservadora (paso más exigente sobre 4 pruebas). De la puerta no se lee ni se publica "
          "ningún coeficiente.", ""]
    for res in RESULTADOS:
        filas = [r for r in pot if r[0] == res]
        if not filas:
            continue
        r0 = filas[0]
        L += [f"### Resultado {res} (n = {_g(r0[2])}, pads = {_g(r0[3])})", "",
              "| Variable | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |",
              "| --- | ---: | ---: | ---: |"]
        for r in filas:
            L.append(f"| {r[1]} | {_g(r[5], 3)} | {_g(r[7], 3)} | {_g(r[8], 3)} |")
        L.append("")
    L += ["## Pads y eventos para ver 0,1 y 0,2 desvíos", "",
          "Pads y eventos necesarios para que el MDE80 con Holm llegue a cada objetivo. Si el número "
          "necesario es menor que el actual (factor menor que 1), la muestra actual ya alcanza para "
          "ese objetivo. La cuenta supone eventos por pad constantes: el error baja como 1 sobre la "
          "raíz del número de pads.", ""]
    filas_a = [r for r in pot if r[0] == "A"]
    if filas_a:
        r0 = filas_a[0]
        L += [f"### Resultado A (actual: n = {_g(r0[2])}, pads = {_g(r0[3])})", "",
              "| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,2 | Eventos 0,2 |",
              "| --- | ---: | ---: | ---: | ---: |"]
        for r in filas_a:
            L.append(f"| {r[1]} | {_g(r[13])} | {_g(r[15])} | {_g(r[14])} | {_g(r[16])} |")
        L.append("")
    L += ["## Simulación de planta y recupera", "",
          "Se ajusta el modelo conjunto A sobre la muestra, se le quita a la caída el efecto estimado "
          "de las cuatro variables, se planta un efecto delta por variable y se reajusta con "
          "bootstrap por pads. La tabla da la potencia empírica con su error de Monte Carlo.", ""]
    if sim:
        L += ["| Variable | Nivel | Delta (desvíos) | Regla | Potencia | Error | Aciertos | Corridas |",
              "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |"]
        nombre_nivel = {"0": "sin efecto", "0,1": "0,1", "0,2": "0,2", "0,22": "0,22 (referencia)",
                        "mde_sin_ajustar": "MDE80 sin ajustar", "mde_holm": "MDE80 de Holm"}
        nombre_regla = {"holm": "Holm", "sin_ajustar": "sin ajustar"}
        for r in sim:
            L.append(f"| {r[0]} | {nombre_nivel.get(r[1], r[1])} | {_g(r[2], 3)} | {nombre_regla.get(r[3], r[3])} | {_g(r[6], 3)} | {_g(r[7], 3)} | "
                     f"{_g(r[5])} | {_g(r[4])} |")
        L.append("")
        tam = {rg: [r[6] for r in sim if r[1] == "0" and r[3] == rg] for rg in ("sin_ajustar", "holm")}
        if tam["sin_ajustar"] and tam["holm"]:
            L.append(f"Tamaño (sin efecto plantado): la fracción que se ve va de {_g(min(tam['sin_ajustar']), 3)} a "
                     f"{_g(max(tam['sin_ajustar']), 3)} con la regla sin ajustar y de {_g(min(tam['holm']), 3)} a "
                     f"{_g(max(tam['holm']), 3)} con Holm, entre las cuatro variables.")
            L.append("")
    if valida is None:
        L.append("No hay filas de simulación: no se puede comparar la cuenta analítica con la empírica.")
    elif valida:
        L.append("La simulación valida la cuenta analítica: la potencia empírica en el MDE80 de cada "
                 "variable, con su regla, cae dentro del rango esperado.")
    else:
        pares = [r[6] for r in sim if (r[1], r[3]) in (("mde_sin_ajustar", "sin_ajustar"), ("mde_holm", "holm"))]
        bajo = any(p < VALIDA_ENTRE[0] for p in pares)
        alto = any(p > VALIDA_ENTRE[1] for p in pares)
        lado = ("optimista en unas variables y pesimista en otras" if bajo and alto
                else "optimista" if bajo else "pesimista")
        L.append("La simulación no valida la cuenta analítica: la potencia empírica en algún MDE80 (con su "
                 f"regla) queda fuera de {_g(VALIDA_ENTRE[0], 2)} a {_g(VALIDA_ENTRE[1], 2)}, así que la cuenta "
                 f"analítica es {lado}. La puerta sigue siendo la analítica.")
        if bajo:
            L.append("")
            L.append("Agregado después de ver los resultados (no cambia la puerta): parte de la diferencia puede "
                     "venir de la resolución del bootstrap de la simulación. Con B = 300 el p mínimo posible es 2 "
                     "sobre 301, y con Holm sobre cuatro pruebas la variable de menor p solo pasa si ningún sorteo cae del "
                     "lado contrario, un umbral más exigente que el normal de la cuenta analítica.")
    L.append("")
    if _tiene_mart(con, "mart_dosis_geometria_modelo"):
        L += ["## Paso 2: el modelo conjunto", "",
              "El modelo conjunto de pipeline.dosis sobre la muestra de padres cercanos entre ramas, "
              "con las reglas de la sección 3.8 sin cambios. B y los quintiles se publican y no "
              "cambian el veredicto de A.", ""]
        mod = con.execute("select resultado, variable, coef_sd, ic_bajo, ic_alto, p, p_holm, n, "
                           "pads, vif, cumple, signo_contrario "
                           "from mart_dosis_geometria_modelo").fetchall()
        for res in RESULTADOS:
            filas = [r for r in mod if r[0] == res]
            if not filas:
                continue
            L += [f"### Resultado {res} (n = {_g(filas[0][7])}, pads = {_g(filas[0][8])})", "",
                  "| Variable | Coef (desvíos) | IC 95% | p | p Holm | FIV | Cumple |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
            for r in filas:
                L.append(f"| {dosis.NOMBRES.get(r[1], r[1])} | {_g(r[2], 3)} | {_g(r[3], 3)} a "
                         f"{_g(r[4], 3)} | {_g(r[5], 3)} | {_g(r[6], 3)} | {_g(r[9], 2)} | "
                         f"{'sí' if r[10] else 'no'} |")
            L.append("")
        if _tiene_mart(con, "mart_dosis_geometria_veredicto"):
            ver = con.execute("select resultado, codigo, texto "
                              "from mart_dosis_geometria_veredicto").fetchall()
            for r in ver:
                L.append(f"Veredicto del resultado {r[0]}: **{r[1]}**: {r[2]}.")
            L.append("")
    L += ["## Cómo se mide", "",
          "- Muestra: los eventos de pipeline.dosis (los eventos cercano de int_interferencia_evento) "
          "cuyo par (hijo, padre) está en mart_trayectoria_par y cuya distancia entre ramas en "
          f"planta `m_min` es menor que {_g(CERCA_RAMA_M)} m. El caso completo, los controles, las "
          "dummies de terminación, las celdas de efectos fijos y la estandarización se rehacen "
          "dentro del subconjunto con las mismas funciones de pipeline.dosis.",
          "- Puerta: el menor de los cuatro MDE80 de Holm del resultado A se compara con la "
          f"referencia de {_g(MDE_REF, 2)} desvíos de la caída por desvío de la dosis. Pasa si es "
          "menor. La regla se fijó antes de calcular cualquier número y no se cambia después de ver "
          "resultados.",
          "- Decide la regla, no el resultado: si la puerta no pasa, la unidad termina y no se "
          "publica ningún coeficiente de dosis sobre esta muestra.",
          "- El resultado A (caída del índice al mes 1) decide; el resultado B (caudal por día) se "
          "informa aparte y no cambia ningún veredicto.", ""]
    L += ["## Qué no es", "",
          "- La potencia es sobre el efecto lineal de la dosis estandarizada con la forma del "
          "modelo; no dice nada de efectos no lineales, de umbrales ni de interacciones. El error "
          "estándar sale de un intervalo de percentiles y la simulación lo contrasta solo para el "
          "modelo conjunto A.",
          "- La muestra es la parte de los eventos de dosis con las dos ramas medidas y cercana entre "
          f"ramas. {NOTA_MUESTRA}",
          "- Un padre con la rama a menos de 600 m de la del hijo pero con la boca a 1 km o más no está "
          "en la muestra de dosis (los eventos de dosis son los de menos de 1 km en superficie): esta "
          "página no lo corrige.",
          f"- \"La geometría no da más potencia\" dice que este dato, con esta definición de "
          f"cercano, no alcanza para ver un efecto menor que {_g(MDE_REF, 2)} desvíos de la caída; "
          "no dice que no haya dosis y respuesta ni golpes de fractura.",
          "- Medir entre ramas no mide el espaciamiento real ni la geometría de la fractura: es la "
          "distancia en planta de las ramas.",
          "- La definición de cercano usa el hijo de pipeline.dosis (el más cercano en superficie); "
          "un padre golpeado por otro hijo del pad queda clasificado por el hijo más cercano en "
          "superficie.", ""]
    L += ["## Reproducir", "",
          "1. `uv run python -m pipeline.dosis_geometria` (necesita pipeline.trayectorias y "
          "pipeline.potencia_dosis antes)",
          "2. `uv run python -m pipeline.wiki`",
          "3. `uv run python -m pipeline.claims`", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
