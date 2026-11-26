"""Estimador apilado del petroleo (porcion E): una pila por evento con controles limpios emparejados.

Se corre despues de pipeline.causal:  uv run python -m pipeline.stacked

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo cada una (857d434
para la regla de abajo), y el plan que nombran (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto
de cada regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porcion E de docs/plan-siguiente-nivel.md). Este commit trae solo la regla, las
constantes y el veredicto; no se calculo ninguna cifra de este diseno (ni ATT, ni placebos, ni cuentas de eventos o de
controles). Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian las cifras de D1 (ATT(1) de -25,8 con 468 tratados; el placebo de nunca tratados con
fecha sorteada da -8,0 con IC de -15,2 a -0,5 y tumba el diseno; M* simplificado de 0,62) y la brecha mediana publicada.

Por que: D1 promedia celdas (g, edad) con controles aun no tratados de toda la cuenca, y su placebo de nunca tratados da -8,0:
los pozos que reciben un hijo a menos de 1 km ya rendian distinto. Aca cada evento tiene su propia pila (Cengiz, Dube,
Lindner y Zipperer, 2019) con controles cercanos, limpios en la ventana y emparejados por el nivel y la pendiente de la base.

Definiciones (todo lo que no se nombra es lo de pipeline.causal: golpe, edad, base, indice, bloques):
  * Evento: un tratado de D1 (cohortes de causal: padre i, mes g del primer golpe a KM_TRATADO, edad de EDAD_MIN o mas,
    ventana previa limpia a KM_LIMPIO, base valida).
  * Candidatos a control del evento: pozos j distintos de i con boca a KM_CONTROL_MIN a KM_CONTROL_MAX km de la boca de i,
    edad en g de EDAD_MIN o mas y en el mismo grupo de edad (CORTES_EDAD), base valida en g, sin golpe a KM_LIMPIO en
    [g - VENTANA_PREVIA, g + H_APILADO], y nunca tratados o con su primer golpe a KM_TRATADO despues de g + H_APILADO.
  * Emparejamiento, dentro del grupo de edad: dos variables de la base,
      - nivel: log de la media de petroleo por dia calendario en los meses BASE (la de causal);
      - pendiente: pendiente de minimos cuadrados del log de petroleo por dia calendario contra el mes, en los meses
        VENTANA_PENDIENTE (relativos a g) con fila y petroleo positivo, con al menos MIN_MESES_PENDIENTE meses; sin eso,
        el pozo no es candidato (y un tratado sin eso no es evento).
    Cada variable se estandariza con el desvio de los eventos. Distancia euclidea sobre las dos estandarizadas. Se toman
    los K_MAX candidatos mas cercanos con distancia de CALIPER o menos, con reemplazo entre eventos. Un evento con menos de
    K_MIN controles queda fuera; se publica cuantos.
  * Resultado: el indice I(e) de causal (recortado en INDICE_TOPE) para e en E_SERIE. Efecto del evento en e: I_i(e) menos
    la media de I(e) de sus controles con dato en e (al menos K_MIN con dato; si no, el evento no entra en e).
  * ATT(e): media simple de los efectos de los eventos que entran en e, por 100 (puntos de indice). Estimando: ATT(1).
  * IC 95%: bootstrap de percentiles por bloques de TAM_BLOQUE_KM km de la boca del padre del evento (causal._pesos_bloques
    sobre los padres de los eventos), REPS sorteos, semilla SEMILLA_APILADO; los mismos sorteos para todo e y para la cota.
    Aclaracion (2026-11-26, revision del PR): la serie principal, la cota y el dejar un operador afuera sortean los bloques
    sobre los padres de los eventos (ev_w); cada placebo los sortea sobre los padres de sus propios pseudo eventos, con la
    misma semilla SEMILLA_APILADO. La version anterior sorteaba sobre la union de eventos y pseudo eventos, contra esta regla,
    y sus cifras ya se habian visto: con el cambio se mueven los IC y la cota, no los valores ni el veredicto. Lo de los
    placebos (cada uno con los padres de sus pseudo eventos) es una lectura de "la misma maquinaria", no texto de la regla.
  * Balance: diferencia estandarizada de medias de nivel y pendiente entre eventos y controles, antes y despues de emparejar.
  * Cota: pipeline.cota_rr con ATT(1) y los previos e = -3, -2, -1 de esta misma serie, sorteo por sorteo.

Placebos (cada uno con la misma maquinaria: candidatos, emparejamiento, ATT(1)). Rompe si causal.rompe con
UMBRAL_ROTURA_PUNTOS:
  * fecha falsa: g' = g - DESFASE_FECHA_FALSA para cada evento, con las condiciones de evento y de control en g';
  * distancia falsa: pseudo eventos con el primer golpe en [KM_FALSO_MIN, KM_FALSO_MAX) km y ninguno a KM_LIMPIO en
    [g - VENTANA_PREVIA, g + H_APILADO];
  * nunca tratados: los pseudo eventos del placebo de D1 (causal._cohorte_nunca_tratados, la misma fecha sorteada), con sus
    propios controles emparejados. Es la prueba de que el -8,0 de D1 desaparece.
La pretendencia no es un placebo: va a la cota (D1 tolera anticipacion de hasta 3 meses).

Dejar un operador afuera: ATT(1) sin los eventos de cada operador del padre con MIN_TRATADOS_OPERADOR o mas eventos y sin
los controles de ese operador.

Veredicto (`veredicto_apilado`), en este orden:
  * "sin muestra": menos de MIN_TRATADOS eventos con efecto en e = 1, o menos de MIN_BLOQUES bloques.
  * "no sobrevive a su placebo": rompe la fecha falsa, la distancia falsa o los nunca tratados.
  * "sostiene como causal bajo tendencias paralelas condicionales al emparejamiento": IC alto de ATT(1) menor que
    UMBRAL_EFECTO_PUNTOS, la cota de Rambachan y Roth da "resiste Mbar = 1", y el IC alto de cada ATT(1) sin un operador
    es menor que cero.
  * "no firme": cualquier otro caso.

Que se publica en cada caso:
  * "sostiene": ATT(1) pasa a ser el titular del petroleo (README, portada, paper) y la brecha mediana agrupada de
    pipeline/sql/04_interferencia.sql pasa a descripcion.
  * cualquier otro: el titular sigue siendo una huella medida (la brecha mediana, rotulada descriptiva) y este resultado se
    publica como falla o como "no firme", con sus placebos.
  * Siempre: la serie ATT(e), los tres placebos, el balance, los eventos fuera por falta de controles, la cota y el dejar un
    operador afuera. Mart: mart_apilado (su llamada a _escribir lleva el nombre literal, para el linaje).

Prueba: en datos sinteticos con seleccion (los tratados rinden menos y caen mas rapido antes de g) y un efecto plantado,
el ATT(1) recupera el efecto plantado y los placebos no rompen; con efecto cero, el ATT(1) incluye cero.

Lo que no dice: aun con "sostiene" es causa bajo supuestos nombrados (tendencias paralelas condicionales al emparejamiento,
anticipacion acotada por la cota, sin derrame sobre controles a 2 a 5 km: lo prueba H), no un hecho fisico medido.

E2. REGLA FIJADA ANTES DE CALCULAR (2026-11-26, ronda 2, porcion E2). Este commit trae solo la regla y la constante; no se
calculo ninguna cifra de E2 (ni cuentas de eventos, bloques o controles, ni ATT, ni placebos, ni balance) y no se consulto
la base para ver si hay muestra. Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga, nunca
despues de ver una cifra. La regla de E de arriba (commit 857d434) no cambia.
  * Misma pila que E con un solo cambio: los candidatos a control estan a KM_CONTROL_MIN (2) a KM_CONTROL_MAX_E2 = 10 km de la
    boca del padre del evento, en lugar de 2 a 5. Todo lo demas es el de E, tal cual: edad y grupo de edad, ventana limpia,
    nunca tratados o tratados despues, emparejamiento por nivel y pendiente, CALIPER, K_MAX, K_MIN, resultado y ATT(1), el
    bootstrap por bloques con los mismos sorteos (semilla SEMILLA_APILADO: E2 no trae semilla propia), balance, placebos
    (con el anillo de E2 para sus controles), dejar un operador afuera, la cota de Rambachan y Roth y `veredicto_apilado`
    con los umbrales de E. La distancia falsa y los eventos no cambian de anillo: solo cambia el de los controles.
  * Lo que se conocia al fijarla: de E, 81 eventos en 26 bloques con al menos K_MIN controles, veredicto "sin muestra", 576 de
    657 eventos fuera por falta de controles a 2 a 5 km y su tabla de balance; de D1, ATT(1) de -25,8 con 468 tratados y el
    placebo de nunca tratados de -8,0; del paper, la cifra de D1 con controles a 5 a 10 km, -24,6. No se conocia ninguna
    cifra de E2.
  * El costo, dicho en la regla: donantes mas lejos dan mas eventos pero geologia menos comparable. Lo que los hace comparables
    es emparejar por el nivel y la pendiente de la base, y la tabla de balance despues de emparejar es la prueba. Si el balance
    de E2 despues de emparejar es peor que el de E, la pagina lo dice, y el veredicto no se lee sin ese dato.
  * Holm: E2 entra a FAMILIA_CONFIRMATORIA de pipeline/inferencia.py con el ATT(1) de su fila de veredicto, como E. Esto queda
    fijado antes de calcular y puede cambiar el k de la familia y el p ajustado de Holm de otros disenos.
  * Se publica: una seccion "E2" en wiki/hallazgos/apilado.md con las mismas tablas que E y el SHA de esta regla; su propio mart
    mart_apilado_e2 (mismas COLUMNAS, diseno = "E2"), con su llamada a _escribir con el nombre literal, para el linaje. Se
    eligio un mart aparte y no filas de E en mart_apilado para que la salida de E quede identica byte a byte; se verifica
    volcando mart_apilado (select * order by all) antes y despues.
  * Los veredictos de E y de E2 son independientes: que E2 tenga muestra no cambia el de E.
"""
from __future__ import annotations

from pipeline.causal import (CORTES_EDAD, DESFASE_FECHA_FALSA, E_SERIE, EDAD_MIN, INDICE_TOPE, KM_FALSO_MAX,
                             KM_FALSO_MIN, KM_LIMPIO, KM_TRATADO, MIN_BLOQUES, MIN_TRATADOS, MIN_TRATADOS_OPERADOR, REPS,
                             SEMILLA_CAUSAL, TAM_BLOQUE_KM, UMBRAL_EFECTO_PUNTOS, UMBRAL_ROTURA_PUNTOS, V_NO_FIRME,
                             V_PLACEBO, V_SIN_MUESTRA, VENTANA_PREVIA)
from pathlib import Path

import duckdb
import numpy as np

from pipeline import cota_rr
from pipeline.causal import (KM_POR_GRADO, _bases, _cohorte_falsa_distancia, _cohorte_falsa_fecha,
                             _cohorte_nunca_tratados, _g, _grupo_edad, _ic, _ic_txt, _n_bloques, _num, _pesos_bloques,
                             cargar, cohortes, controles, indice, rompe)
from pipeline.cota_rr import V_RR_RESISTE
from pipeline.costo import _escribir
from pipeline.ingest import DATA

# heredado de pipeline.causal sin cambio
REGLA_HEREDADA = {"KM_TRATADO": KM_TRATADO, "KM_LIMPIO": KM_LIMPIO, "VENTANA_PREVIA": VENTANA_PREVIA,
                  "EDAD_MIN": EDAD_MIN, "CORTES_EDAD": CORTES_EDAD, "INDICE_TOPE": INDICE_TOPE, "E_SERIE": E_SERIE,
                  "TAM_BLOQUE_KM": TAM_BLOQUE_KM, "REPS": REPS, "DESFASE_FECHA_FALSA": DESFASE_FECHA_FALSA,
                  "KM_FALSO": (KM_FALSO_MIN, KM_FALSO_MAX), "MIN_TRATADOS": MIN_TRATADOS, "MIN_BLOQUES": MIN_BLOQUES,
                  "MIN_TRATADOS_OPERADOR": MIN_TRATADOS_OPERADOR, "UMBRAL_ROTURA_PUNTOS": UMBRAL_ROTURA_PUNTOS,
                  "UMBRAL_EFECTO_PUNTOS": UMBRAL_EFECTO_PUNTOS}

# ---- regla fijada (no cambiar despues de ver cifras) ----
SEMILLA_APILADO = SEMILLA_CAUSAL + 60
H_APILADO = 6                          # ventana limpia de los controles, como H_CORTO de D1
KM_CONTROL_MIN, KM_CONTROL_MAX = 2.0, 5.0
KM_CONTROL_MAX_E2 = 10.0               # E2: el mismo piso, anillo de donantes hasta 10 km (regla E2 del docstring)
VENTANA_PENDIENTE = (-9, -4)           # meses relativos a g, inclusive
MIN_MESES_PENDIENTE = 3
K_MAX = 5
K_MIN = 3
CALIPER = 0.5                          # en desvios de los eventos, distancia euclidea sobre las dos variables
E_PRINCIPAL = 1
_MBAR_TOPE = _g(cota_rr.MBAR_MAX)           # el Mbar mas alto de la cota, como lo imprime la pagina

V_APILADO_SOSTIENE = "sostiene como causal bajo tendencias paralelas condicionales al emparejamiento"


def veredicto_apilado(n_eventos: int, n_bloques: int, placebos_rotos: bool, alto: float, v_rr: str,
                      altos_sin_operador: list[float]) -> str:
    if n_eventos < MIN_TRATADOS or n_bloques < MIN_BLOQUES:
        return V_SIN_MUESTRA
    if placebos_rotos:
        return V_PLACEBO
    if alto < UMBRAL_EFECTO_PUNTOS and v_rr == V_RR_RESISTE and all(a < 0 for a in altos_sin_operador):
        return V_APILADO_SOSTIENE
    return V_NO_FIRME


# ------------------------------------------------------------------ implementacion (porcion E)

ROOT = Path(__file__).resolve().parent.parent
PAGINA = ROOT / "wiki" / "hallazgos" / "apilado.md"
REGLA_COMMIT = "857d434"
REGLA_COMMIT_E2 = "82d58c0"
PLACEBOS = (("placebo_fecha_falsa", "fecha falsa"), ("placebo_distancia_falsa", "distancia falsa"),
            ("placebo_nunca_tratados", "nunca tratados"))
COLUMNAS = [("diseno", "varchar"), ("resultado", "varchar"), ("e", "integer"), ("mbar", "double"),
            ("n_tratados", "integer"), ("n_controles", "integer"), ("valor", "double"), ("ic_bajo", "double"),
            ("ic_alto", "double"), ("veredicto", "varchar"), ("motivo", "varchar")]


def pendiente_mco(tasas: np.ndarray, meses_rel: np.ndarray = None) -> np.ndarray:
    """Pendiente de minimos cuadrados del log del caudal contra el mes, por fila de `tasas` (pozos x meses de la ventana).

    Usa solo los meses con fila y caudal positivo (nan o cero o menos se ignoran); con menos de MIN_MESES_PENDIENTE
    meses la fila da nan."""
    tasas = np.atleast_2d(np.asarray(tasas, dtype=float))
    if meses_rel is None:
        meses_rel = np.arange(VENTANA_PENDIENTE[0], VENTANA_PENDIENTE[1] + 1)
    x = np.asarray(meses_rel, dtype=float)[None, :]
    with np.errstate(invalid="ignore"):
        usable = ~np.isnan(tasas) & (tasas > 0)
    y = np.log(np.where(usable, tasas, 1.0))
    cuenta = usable.sum(axis=1)
    div = np.maximum(cuenta, 1)
    xm = (usable * x).sum(axis=1) / div
    ym = (usable * y).sum(axis=1) / div
    xc = x - xm[:, None]
    sxx = (usable * xc ** 2).sum(axis=1)
    sxy = (usable * xc * (y - ym[:, None])).sum(axis=1)
    ok = (cuenta >= MIN_MESES_PENDIENTE) & (sxx > 0)
    return np.where(ok, sxy / np.where(sxx > 0, sxx, 1.0), np.nan)


def _estado(D: dict, g: int, cache: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Nivel (log de la base), pendiente y validez de cada pozo en el mes g (con cache por mes)."""
    if g in cache:
        return cache[g]
    n, T, col = D["n"], D["T"], g - D["t0"]
    nivel = np.full(n, np.nan)
    pend = np.full(n, np.nan)
    ok = np.zeros(n, dtype=bool)
    if 0 <= col < T:
        media, valida = _bases(D)
        cols = col + np.arange(VENTANA_PENDIENTE[0], VENTANA_PENDIENTE[1] + 1)
        dentro = (cols >= 0) & (cols < T)
        vals = D["tasa"][:, np.clip(cols, 0, T - 1)].astype(float)
        vals[:, ~dentro] = np.nan
        pend = pendiente_mco(vals)
        ok = valida[:, col] & ~np.isnan(pend)
        with np.errstate(divide="ignore", invalid="ignore"):
            nivel = np.where(valida[:, col], np.log(media[:, col]), np.nan)
    cache[g] = (nivel, pend, ok)
    return cache[g]


def _distancias(D: dict, i: int, js: np.ndarray) -> np.ndarray:
    """Distancia equirectangular en km de la boca de i a la de cada j."""
    dx = (D["lon"][js] - D["lon"][i]) * np.cos(np.radians(D["lat"][i])) * KM_POR_GRADO
    dy = (D["lat"][js] - D["lat"][i]) * KM_POR_GRADO
    return np.hypot(dx, dy)


def _emparejar(niv_e: float, pen_e: float, cand: np.ndarray, niv_c: np.ndarray, pen_c: np.ndarray,
               sds: tuple[float, float]) -> np.ndarray:
    """Los K_MAX candidatos mas cercanos con distancia de CALIPER o menos (desempate estable por indice de pozo)."""
    if not len(cand):
        return np.zeros(0, dtype=np.int64)
    d = np.hypot((niv_c - niv_e) / sds[0], (pen_c - pen_e) / sds[1])
    orden = np.lexsort((cand, d))
    orden = orden[d[orden] <= CALIPER][:K_MAX]
    return np.asarray(cand[orden], dtype=np.int64)


def _indices(D: dict, pozos: np.ndarray, base: np.ndarray, g: int, es: tuple[int, ...]) -> np.ndarray:
    return np.column_stack([indice(D, pozos, base, g, e) for e in es])


def _construir(D: dict, pozos: np.ndarray, g: np.ndarray, es: tuple[int, ...], km_max: float = KM_CONTROL_MAX) -> dict:
    """Candidatos, emparejamiento e indices de un diseno (el principal o un placebo).

    Un pozo sin nivel o sin pendiente valida en su g no es evento. Un evento con menos de K_MIN controles queda fuera."""
    pozos = np.asarray(pozos, dtype=np.int64)
    g = np.asarray(g, dtype=np.int64)
    media, _ = _bases(D)
    cache: dict = {}
    nivel_e = np.full(len(pozos), np.nan)
    pend_e = np.full(len(pozos), np.nan)
    for k, (i, gi) in enumerate(zip(pozos, g)):
        niv, pen, ok = _estado(D, int(gi), cache)
        if ok[i]:
            nivel_e[k], pend_e[k] = niv[i], pen[i]
    valido = ~np.isnan(nivel_e)
    if int(valido.sum()) > 1:
        sds = (float(np.std(nivel_e[valido], ddof=1)), float(np.std(pend_e[valido], ddof=1)))
    else:
        sds = (float("nan"), float("nan"))
    ctrl_g: dict = {}
    out = {"pozos": [], "g": [], "ctrl": [], "cand": [], "I_ev": [], "I_c": [], "sds": sds, "estado": cache,
           "n_validos": int(valido.sum()), "n_sin_pendiente": int((~valido).sum()), "n_sin_controles": 0, "es": es}
    if not np.isfinite(sds[0]) or sds[0] <= 0 or sds[1] <= 0:
        return {**out, "pozos": np.zeros(0, dtype=np.int64), "g": np.zeros(0, dtype=np.int64),
                "I_ev": np.zeros((0, len(es)))}
    for k in np.flatnonzero(valido):
        i, gi = int(pozos[k]), int(g[k])
        niv, pen, ok = cache[gi]
        grupo = int(_grupo_edad(np.array([gi - D["primer"][i]]))[0])
        if (gi, grupo) not in ctrl_g:
            con = controles(D, gi, H_APILADO, True)
            con = con[ok[con] & (_grupo_edad(gi - D["primer"][con]) == grupo)]
            ctrl_g[(gi, grupo)] = con
        cand = ctrl_g[(gi, grupo)]
        cand = cand[cand != i]
        if len(cand):
            d = _distancias(D, i, cand)
            cand = cand[(d >= KM_CONTROL_MIN) & (d <= km_max)]
        match = _emparejar(nivel_e[k], pend_e[k], cand, niv[cand], pen[cand], sds)
        if len(match) < K_MIN:
            out["n_sin_controles"] += 1
            continue
        col = gi - D["t0"]
        out["pozos"].append(i)
        out["g"].append(gi)
        out["ctrl"].append(match)
        out["cand"].append(cand)
        out["I_ev"].append(_indices(D, np.array([i]), media[[i], col], gi, es)[0])
        out["I_c"].append(_indices(D, match, media[match, col], gi, es))
    out["pozos"] = np.array(out["pozos"], dtype=np.int64)
    out["g"] = np.array(out["g"], dtype=np.int64)
    out["I_ev"] = np.array(out["I_ev"], dtype=float).reshape(len(out["pozos"]), len(es))
    return out


def _efectos(D: dict, dis: dict, sin_operador: str | None = None) -> tuple[np.ndarray, list[int]]:
    """Efecto de cada evento en cada e (nan si no entra) y la cantidad de controles distintos que usa cada e."""
    k, ne = len(dis["pozos"]), len(dis["es"])
    eff = np.full((k, ne), np.nan)
    usados: list[set] = [set() for _ in range(ne)]
    for a in range(k):
        ctrl, Ic = dis["ctrl"][a], dis["I_c"][a]
        if sin_operador is not None:
            if str(D["operador"][dis["pozos"][a]]) == sin_operador:
                continue
            keep = np.array([str(D["operador"][j]) != sin_operador for j in ctrl], dtype=bool)
            ctrl, Ic = ctrl[keep], Ic[keep]
        cuenta = (~np.isnan(Ic)).sum(axis=0)
        suma = np.nansum(Ic, axis=0)
        media_c = np.where(cuenta > 0, suma / np.maximum(cuenta, 1), np.nan)
        entra = (cuenta >= K_MIN) & ~np.isnan(dis["I_ev"][a])
        eff[a, entra] = dis["I_ev"][a, entra] - media_c[entra]
        for j in np.flatnonzero(entra):
            usados[j].update(ctrl[~np.isnan(Ic[:, j])].tolist())
    return eff, [len(u) for u in usados]


def _att_sorteos(eff: np.ndarray, pesos: np.ndarray) -> np.ndarray:
    """ATT_r(e) = 100 * suma W eff / suma W sobre los eventos que entran en e. Forma (reps, e)."""
    entra = ~np.isnan(eff)
    num = pesos @ np.nan_to_num(eff)
    den = pesos @ entra.astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, 100.0 * num / den, np.nan)


def _resumen(D: dict, dis: dict, W: np.ndarray, sin_operador: str | None = None) -> dict:
    eff, n_con = _efectos(D, dis, sin_operador)
    entra = ~np.isnan(eff)
    n_t = entra.sum(axis=0)
    est = np.where(n_t > 0, 100.0 * np.nansum(eff, axis=0) / np.maximum(n_t, 1), np.nan)
    sorteos = _att_sorteos(eff, W[:, dis["pozos"]]) if len(dis["pozos"]) else np.full((len(W), len(dis["es"])), np.nan)
    bajo = np.full(len(dis["es"]), np.nan)
    alto = np.full(len(dis["es"]), np.nan)
    for j in range(len(dis["es"])):
        bajo[j], alto[j] = _ic(sorteos[:, j])
    return {"es": dis["es"], "est": est, "ic_bajo": bajo, "ic_alto": alto, "n_tratados": n_t.astype(int),
            "n_controles": n_con, "sorteos": sorteos, "eff": eff, "entra": entra}


def _smd(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    s = float(np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2))
    return float((np.mean(a) - np.mean(b)) / s) if s > 0 else float("nan")


def _balance(dis: dict) -> dict:
    """Diferencia estandarizada de medias de nivel y pendiente, antes (todos los candidatos) y despues (emparejados)."""
    ev_n, ev_p, an, ap, dn, dp = [], [], [], [], [], []
    for gi, i, cand, ctrl in zip(dis["g"], dis["pozos"], dis["cand"], dis["ctrl"]):
        niv, pen, _ = dis["estado"][int(gi)]
        ev_n.append(niv[i])
        ev_p.append(pen[i])
        an.append(niv[cand])
        ap.append(pen[cand])
        dn.append(niv[ctrl])
        dp.append(pen[ctrl])
    cat = lambda x: np.concatenate(x) if x else np.zeros(0)  # noqa: E731
    ev_n, ev_p = np.array(ev_n), np.array(ev_p)
    return {"nivel_antes": (_smd(ev_n, cat(an)), len(cat(an))), "nivel_despues": (_smd(ev_n, cat(dn)), len(cat(dn))),
            "pendiente_antes": (_smd(ev_p, cat(ap)), len(cat(ap))),
            "pendiente_despues": (_smd(ev_p, cat(dp)), len(cat(dp))), "n_eventos": len(ev_n)}


def calcular(D: dict, reps: int = REPS, semilla: int = SEMILLA_APILADO, km_max: float = KM_CONTROL_MAX) -> dict:
    """Corre el diseno apilado, sus tres placebos, el dejar un operador afuera, el balance y la cota.

    km_max es el borde externo del anillo de controles: KM_CONTROL_MAX para E, KM_CONTROL_MAX_E2 para E2."""
    coh = cohortes(D)
    ev_w = np.flatnonzero(coh["tratado"])
    ev_g = coh["g"][ev_w]
    coh_pl = {"placebo_fecha_falsa": _cohorte_falsa_fecha(D, coh),
              "placebo_distancia_falsa": _cohorte_falsa_distancia(D, coh, H_APILADO),
              "placebo_nunca_tratados": _cohorte_nunca_tratados(D, coh)}
    W = _pesos_bloques(D, ev_w, reps, np.random.default_rng(semilla))

    dis = _construir(D, ev_w, ev_g, E_SERIE, km_max)
    r = _resumen(D, dis, W)
    j1 = E_SERIE.index(E_PRINCIPAL)
    entran1 = dis["pozos"][r["entra"][:, j1]]
    n_bl = _n_bloques(D, entran1)

    placebos = {}
    for nombre, (w, g) in coh_pl.items():
        dp = _construir(D, w, g, (E_PRINCIPAL,), km_max)
        Wp = _pesos_bloques(D, w, reps, np.random.default_rng(semilla))  # bloques sobre los padres de sus pseudo eventos
        rp = _resumen(D, dp, Wp)
        rp["n_eventos_cohorte"] = int(len(w))
        rp["n_sin_pendiente"], rp["n_sin_controles"] = dp["n_sin_pendiente"], dp["n_sin_controles"]
        rp["rompe"] = bool(rompe(float(rp["est"][0]), float(rp["ic_bajo"][0]), float(rp["ic_alto"][0]),
                                 UMBRAL_ROTURA_PUNTOS))
        placebos[nombre] = rp

    ops: dict[str, int] = {}
    for i in entran1:
        ops[str(D["operador"][i])] = ops.get(str(D["operador"][i]), 0) + 1
    sin_op = {}
    for op, n_op in sorted(ops.items()):
        if n_op >= MIN_TRATADOS_OPERADOR:
            sin_op[op] = _resumen(D, dis, W, sin_operador=op)

    # cota de Rambachan y Roth con los previos de esta misma serie, sorteo por sorteo
    col = {e: E_SERIE.index(e) for e in (-3, -2, -1, E_PRINCIPAL)}
    puntos = [float(r["est"][col[e]]) for e in (-3, -2, -1)]
    hay_previos = not any(np.isnan(p) for p in puntos) and not np.isnan(float(r["est"][j1]))
    cota = {"hay_previos": hay_previos, "grilla": [], "quiebre": float("nan"), "veredicto": cota_rr.V_RR_SIN_DATO}
    if hay_previos:
        s = np.column_stack([r["sorteos"][:, col[e]] for e in (-3, -2, -1, E_PRINCIPAL)])
        s = s[~np.isnan(s).any(axis=1)]
        if len(s):
            b3, b2, b1, lb = s[:, 0], s[:, 1], s[:, 2], s[:, 3]
            meses = (E_PRINCIPAL,)
            for mbar in cota_rr.GRILLA_MBAR:
                lo, hi = cota_rr.conjunto(float(r["est"][j1]), puntos[0], puntos[1], puntos[2], mbar, meses)
                iv = cota_rr.intervalo(lb, b3, b2, b1, mbar, meses)
                cota["grilla"].append((mbar, float(lo), float(hi), iv[0], iv[1]))
            cota["quiebre"] = cota_rr.quiebre(lb, b3, b2, b1, meses)
            cota["veredicto"] = cota_rr.veredicto_rr(True, cota["quiebre"])
        else:
            cota["hay_previos"] = False
    altos_op = [float(x["ic_alto"][j1]) for x in sin_op.values()]
    rotos = [n for n, p in placebos.items() if p["rompe"]]
    ver = veredicto_apilado(int(r["n_tratados"][j1]), n_bl, bool(rotos), float(r["ic_alto"][j1]), cota["veredicto"],
                            altos_op)
    return {"dis": dis, "r": r, "j1": j1, "n_bloques": n_bl, "placebos": placebos, "sin_operador": sin_op,
            "balance": _balance(dis), "cota": cota, "rotos": rotos, "veredicto": ver, "altos_op": altos_op,
            "n_cohorte": int(len(ev_w))}


def _f(x) -> float | None:
    x = float(x)
    return None if np.isnan(x) or np.isinf(x) else x


def _motivo_veredicto(res: dict) -> str:
    c = res["cota"]
    quiebre = c["quiebre"]
    q = "sin dato" if np.isnan(quiebre) else (f"no se rompe ni con Mbar = {_MBAR_TOPE}" if np.isinf(quiebre)
                                               else f"se rompe con Mbar = {_g(quiebre, 2)}")
    rotos = ", ".join(n.replace("placebo_", "").replace("_", " ") for n in res["rotos"]) or "ninguno"
    altos = "; ".join(f"{op} {_num(float(x['ic_alto'][res['j1']]))}" for op, x in res["sin_operador"].items()) or "ninguno"
    return (f"Placebos que rompen: {rotos}. Cota RR: {c['veredicto']} ({q}). IC alto sin cada operador: {altos}. "
            f"Bloques: {_g(res['n_bloques'])}.")


def filas_mart(res: dict, diseno: str = "E", km_max: float = KM_CONTROL_MAX) -> list[tuple]:
    r, j1 = res["r"], res["j1"]
    filas = [(diseno, "ATT(1)", E_PRINCIPAL, None, int(r["n_tratados"][j1]), int(r["n_controles"][j1]), _f(r["est"][j1]),
              _f(r["ic_bajo"][j1]), _f(r["ic_alto"][j1]), res["veredicto"], _motivo_veredicto(res))]
    det = f"{diseno}_detalle"
    for j, e in enumerate(E_SERIE):
        filas.append((det, "serie", int(e), None, int(r["n_tratados"][j]), int(r["n_controles"][j]), _f(r["est"][j]),
                      _f(r["ic_bajo"][j]), _f(r["ic_alto"][j]), None, None))
    for nombre, _ in PLACEBOS:
        p = res["placebos"][nombre]
        filas.append((det, nombre, E_PRINCIPAL, None, int(p["n_tratados"][0]), int(p["n_controles"][0]),
                      _f(p["est"][0]), _f(p["ic_bajo"][0]), _f(p["ic_alto"][0]),
                      "rompe" if p["rompe"] else "no rompe",
                      f"{p['n_eventos_cohorte']} pseudo eventos en la cohorte; {p['n_sin_pendiente']} sin nivel o pendiente "
                      f"y {p['n_sin_controles']} sin controles"))
    for op, x in res["sin_operador"].items():
        filas.append((det, f"sin_operador:{op}", E_PRINCIPAL, None, int(x["n_tratados"][j1]), int(x["n_controles"][j1]),
                      _f(x["est"][j1]), _f(x["ic_bajo"][j1]), _f(x["ic_alto"][j1]), None, None))
    b = res["balance"]
    for clave in ("nivel_antes", "nivel_despues", "pendiente_antes", "pendiente_despues"):
        smd, n_c = b[clave]
        filas.append((det, f"balance_{clave}", None, None, int(b["n_eventos"]), int(n_c), _f(smd), None, None, None,
                      None))
    d = res["dis"]
    filas.append((det, "eventos_sin_controles", None, None, int(d["n_validos"]), None, float(d["n_sin_controles"]), None,
                  None, None, f"sin nivel o pendiente válida (no son evento): {d['n_sin_pendiente']}; con menos de {K_MIN} "
                              f"controles a {KM_CONTROL_MIN:g} a {km_max:g} km dentro del caliper: "
                              f"{d['n_sin_controles']}"))
    c = res["cota"]
    for mbar, lo, hi, a, bb in c["grilla"]:
        filas.append((det, "cota_grilla", E_PRINCIPAL, float(mbar), None, None, None, _f(a), _f(bb), None,
                      f"conjunto {_g(lo, 1)}..{_g(hi, 1)}"))
    if not np.isnan(c["quiebre"]):
        filas.append((det, "cota_quiebre", E_PRINCIPAL, None, None, None, _f(c["quiebre"]), None, None, c["veredicto"],
                      f"no se rompe ni con Mbar = {_MBAR_TOPE}" if np.isinf(c["quiebre"]) else "Mbar del quiebre"))
    else:
        filas.append((det, "cota_quiebre", E_PRINCIPAL, None, None, None, None, None, None, c["veredicto"],
                      "sin previos validos"))
    filas.append((det, "n_bloques", None, None, int(r["n_tratados"][j1]), None, float(res["n_bloques"]), None, None,
                  None, f"bloques de {TAM_BLOQUE_KM:g} km con eventos que entran en e = {E_PRINCIPAL}"))
    return filas


# ------------------------------------------------------------------ pagina

LO_QUE_NO_DICE = ("Aun con \"sostiene\" es causa bajo supuestos nombrados (tendencias paralelas condicionales al "
                  "emparejamiento, anticipación acotada por la cota, sin derrame sobre controles a 2 a 5 km: lo prueba "
                  "H), no un hecho físico medido.")
TEXTO_PUBLICA = {V_APILADO_SOSTIENE: "ATT(1) pasa a ser el titular del petroleo y la brecha mediana agrupada pasa a "
                                     "descripcion.",
                 "no firme": "El titular sigue siendo una huella medida (la brecha mediana, rotulada descriptiva) y este "
                             "resultado se publica como \"no firme\", con sus placebos.",
                 V_PLACEBO: "El titular sigue siendo una huella medida (la brecha mediana, rotulada descriptiva) y este "
                            "resultado se publica como falla, con sus placebos.",
                 V_SIN_MUESTRA: "La muestra no alcanza el mínimo de la regla: el valor se publica pero no decide nada."}


def _ic_fila(x: tuple) -> str:
    return _ic_txt(x[7], x[8]) if x[7] is not None and x[8] is not None else "n/d"


def _cuerpo(filas: list[tuple], diseno: str, km_max: float, h: str) -> list[str]:
    """Las tablas de un diseno (veredicto, serie, placebos, balance, cota, operadores) desde sus filas de mart; h es el
    prefijo de los titulos ("##" para E y "###" para la seccion de E2)."""
    v = next(f for f in filas if f[0] == diseno)
    det = [f for f in filas if f[0] == f"{diseno}_detalle"]
    por = lambda res: [f for f in det if f[1] == res]  # noqa: E731
    uno = lambda res: next((f for f in det if f[1] == res), None)  # noqa: E731
    val = lambda f, dec=1: _num(f[6], dec) if f is not None and f[6] is not None else "n/d"  # noqa: E731
    L = [f"{h} Veredicto", "",
         f"**{v[9]}.** ATT(1) = {val(v)} puntos (IC 95%: {_ic_fila(v)}), {_g(v[4])} eventos con efecto en e = 1 y "
         f"{_g(v[5])} controles distintos. {v[10]}", "",
         TEXTO_PUBLICA.get(v[9], ""), "",
         f"{h} Serie ATT(e)", "", "| e | eventos | controles | ATT(e), puntos | IC 95% |", "|---:|---:|---:|---:|---|"]
    for f in por("serie"):
        L.append(f"| {f[2]} | {_g(f[4])} | {_g(f[5])} | {val(f)} | {_ic_fila(f)} |")
    L += ["", "Los meses previos (e negativo) son un diagnóstico: con emparejamiento exacto en la base deberían quedar cerca de "
          "cero. No son un placebo; van a la cota.", "",
          f"{h} Placebos", "",
          "Cada uno pasa por la misma maquinaria (candidatos, emparejamiento, ATT(1)). Rompe si su IC excluye cero y su "
          f"valor absoluto es {_num(UMBRAL_ROTURA_PUNTOS)} puntos o más.", "",
          "| placebo | eventos | ATT(1), puntos | IC 95% | resultado |", "|---|---:|---:|---|---|"]
    for nombre, etiqueta in PLACEBOS:
        f = uno(nombre)
        L.append(f"| {etiqueta} | {_g(f[4])} | {val(f)} | {_ic_fila(f)} | {f[9]} |")
    L += ["", f"{h} Balance", "",
          "Diferencia estandarizada de medias entre eventos y controles, antes (todos los candidatos de los eventos) y "
          "después de emparejar (controles con multiplicidad).", "",
          "| variable | antes | después | controles antes | controles después |", "|---|---:|---:|---:|---:|"]
    for var, etiqueta in (("nivel", "nivel de la base (log)"), ("pendiente", "pendiente previa")):
        a, d = uno(f"balance_{var}_antes"), uno(f"balance_{var}_despues")
        L.append(f"| {etiqueta} | {val(a, 2)} | {val(d, 2)} | {_g(a[5])} | {_g(d[5])} |")
    s = uno("eventos_sin_controles")
    L += ["", f"Eventos fuera por falta de controles: {_g(s[6])} de {_g(s[4])} con nivel y pendiente válidos. De los tratados de la cohorte, {s[10]}.", "",
          f"{h} Cota de Rambachan y Roth", "",
          "Con ATT(1) y los previos e = -3, -2, -1 de esta misma serie, sorteo por sorteo. Un Mbar de 1 deja que el salto "
          "posterior sea tan grande como el mayor salto previo. La cota toma el valor de e = -1 como sesgo que ya estaba y lo "
          "descuenta: con Mbar = 0 el conjunto es ATT(1) menos el valor de e = -1, no ATT(1).", "",
          "| Mbar | conjunto identificado | intervalo 95% |", "|---:|---|---|"]
    for f in por("cota_grilla"):
        L.append(f"| {_g(f[3], 2)} | {f[10].replace('conjunto ', '').replace('..', ' a ')} | {_ic_fila(f)} |")
    q = uno("cota_quiebre")
    L += ["", f"Quiebre: {_g(q[6], 2) if q[6] is not None else 'n/d'} ({q[10]}). Veredicto de la cota: **{q[9]}**.", ""]
    ops = [f for f in det if f[1].startswith("sin_operador:")]
    L += [f"{h} Dejar un operador afuera", ""]
    if ops:
        L += ["| sin el operador | eventos | ATT(1), puntos | IC 95% |", "|---|---:|---:|---|"]
        for f in ops:
            L.append(f"| {f[1].split(':', 1)[1]} | {_g(f[4])} | {val(f)} | {_ic_fila(f)} |")
    else:
        L.append(f"Ningún operador tiene {MIN_TRATADOS_OPERADOR} o más eventos: no hay filas.")
    nb = uno("n_bloques")
    L += ["", f"Bloques de {TAM_BLOQUE_KM:g} km con eventos que entran en e = 1: {_g(nb[6])} (la regla pide "
          f"{MIN_BLOQUES}).", ""]
    return L




def _comparacion_balance(filas: list[tuple]) -> str:
    """Compara el balance despues de emparejar de E2 con el de E (valor absoluto de la diferencia estandarizada)."""
    def d(diseno, var):
        f = next(f for f in filas if f[0] == f"{diseno}_detalle" and f[1] == f"balance_{var}_despues")
        return None if f[6] is None else abs(f[6])
    pares = [(var, d("E", var), d("E2", var)) for var in ("nivel", "pendiente")]
    if any(a is None or b is None for _, a, b in pares):
        return "El balance después de emparejar de E o de E2 no tiene dato: no se compara."
    peor = [var for var, a, b in pares if b > a]
    txt = "; ".join(f"{var}: E {_num(a, 2)}, E2 {_num(b, 2)}" for var, a, b in pares)
    if peor:
        return (f"El balance después de emparejar de E2 es peor que el de E en {' y '.join(peor)} ({txt}, en valor absoluto): "
                "la regla dice que eso se lee junto con el veredicto, porque donantes más lejos son geología menos comparable.")
    return f"El balance después de emparejar de E2 no es peor que el de E ({txt}, en valor absoluto)."


def pagina_apilado(filas: list[tuple]) -> str:
    """Pagina del hallazgo, armada solo con las filas de mart_apilado (E) y, si estan, las de mart_apilado_e2 (E2)."""
    filas_e = [f for f in filas if f[0] in ("E", "E_detalle")]
    filas_e2 = [f for f in filas if f[0] in ("E2", "E2_detalle")]
    L = ["# Estimador apilado del petróleo: una pila por evento con controles limpios emparejados", "",
         "Página generada por `pipeline/stacked.py` desde `mart_apilado` y `mart_apilado_e2`. Esta es la regla fijada en el commit "
         f"{REGLA_COMMIT} antes de calcular.", "",
         "## Qué estima", "",
         "El diseño de `causal.md` promedia celdas de padres tratados con controles aún no tratados de toda la cuenca, y su "
         "placebo de nunca tratados da un efecto donde no debería haberlo: los padres que reciben un hijo a menos de 1 km "
         "ya rendían distinto. Acá cada evento (un padre con su primer golpe a menos de 1 km) tiene su propia pila: "
         f"hasta {K_MAX} controles a {KM_CONTROL_MIN:g} a {KM_CONTROL_MAX:g} km de la misma edad, limpios en la "
         f"ventana, emparejados por el nivel y la pendiente de la base (caliper de {_g(CALIPER, 1)} desvíos de los eventos). "
         "El efecto es la diferencia del índice de caudal contra la media de sus controles, en puntos de índice; el IC 95% "
         f"sale de remuestrear bloques de {TAM_BLOQUE_KM:g} km.", ""]
    L += _cuerpo(filas_e, "E", KM_CONTROL_MAX, "##")
    L += ["## Lo que no dice", "", LO_QUE_NO_DICE, ""]
    if filas_e2:
        L += ["## E2: la misma pila con donantes a 2 a 10 km", "",
              f"Regla fijada en el commit {REGLA_COMMIT_E2} antes de calcular (docstring de `pipeline/stacked.py`, bloque E2), "
              f"desde `mart_apilado_e2`. Es E con un solo cambio: los candidatos a control están a {KM_CONTROL_MIN:g} a "
              f"{KM_CONTROL_MAX_E2:g} km de la boca del padre del evento, en lugar de {KM_CONTROL_MIN:g} a {KM_CONTROL_MAX:g}. "
              "Todo lo demás es lo de E. Donantes más lejos dan más eventos pero geología menos comparable: lo que los hace "
              "comparables es emparejar por el nivel y la pendiente de la base, y el balance después de emparejar es la prueba.", "",
              _comparacion_balance(filas_e + filas_e2), ""]
        L += _cuerpo(filas_e2, "E2", KM_CONTROL_MAX_E2, "###")
        L += ["Lo que no dice E2: lo mismo que arriba, con controles a 2 a 10 km en lugar de 2 a 5 (el derrame sobre ese "
              "anillo más ancho lo prueba H solo hasta lo que H mide).", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    D = cargar(con)
    res = calcular(D)
    _escribir(con, "mart_apilado", COLUMNAS, filas_mart(res))
    res2 = calcular(D, km_max=KM_CONTROL_MAX_E2)   # E2: la misma pila con donantes a 2 a 10 km (regla E2 del docstring)
    _escribir(con, "mart_apilado_e2", COLUMNAS, filas_mart(res2, "E2", KM_CONTROL_MAX_E2))
    filas = (con.execute("select * from mart_apilado").fetchall()
             + con.execute("select * from mart_apilado_e2").fetchall())
    PAGINA.write_text(pagina_apilado(filas), encoding="utf-8")
    con.close()
    r, j1 = res["r"], res["j1"]
    print(f"ATT(1) = {_num(r['est'][j1])} puntos, IC95 {_ic_txt(r['ic_bajo'][j1], r['ic_alto'][j1])}, "
          f"{int(r['n_tratados'][j1])} eventos entran en e=1 ({int(r['n_controles'][j1])} controles; "
          f"{res['n_bloques']} bloques)")
    print("serie ATT(e): " + "; ".join(f"e={e}: {_num(r['est'][j])} [{_ic_txt(r['ic_bajo'][j], r['ic_alto'][j])}] "
                                      f"n={int(r['n_tratados'][j])}" for j, e in enumerate(E_SERIE)))
    for nombre, etiqueta in PLACEBOS:
        p = res["placebos"][nombre]
        print(f"placebo {etiqueta}: {_num(p['est'][0])} [{_ic_txt(p['ic_bajo'][0], p['ic_alto'][0])}] "
              f"n={int(p['n_tratados'][0])} -> {'ROMPE' if p['rompe'] else 'no rompe'}")
    b = res["balance"]
    print("balance SMD: " + ", ".join(f"{k}={_g(v[0], 2)}" for k, v in b.items() if k != "n_eventos"))
    d = res["dis"]
    print(f"eventos: {d['n_validos']} con nivel y pendiente; {d['n_sin_pendiente']} sin pendiente; "
          f"{d['n_sin_controles']} sin controles")
    c = res["cota"]
    print(f"cota RR: {c['veredicto']}; quiebre Mbar = {c['quiebre']}")
    for mbar, lo, hi, a, bb in c["grilla"]:
        print(f"  Mbar {mbar}: conjunto {_g(lo, 1)}..{_g(hi, 1)}, intervalo {_g(a, 1)}..{_g(bb, 1)}")
    for op, x in res["sin_operador"].items():
        print(f"sin {op}: {_num(x['est'][j1])} [{_ic_txt(x['ic_bajo'][j1], x['ic_alto'][j1])}] n={int(x['n_tratados'][j1])}")
    print(f"VEREDICTO: {res['veredicto']}")
    r2 = res2["r"]
    print(f"E2 ATT(1) = {_num(r2['est'][j1])} puntos, IC95 {_ic_txt(r2['ic_bajo'][j1], r2['ic_alto'][j1])}, "
          f"{int(r2['n_tratados'][j1])} eventos entran en e=1 ({int(r2['n_controles'][j1])} controles; "
          f"{res2['n_bloques']} bloques)")
    for nombre, etiqueta in PLACEBOS:
        p = res2["placebos"][nombre]
        print(f"E2 placebo {etiqueta}: {_num(p['est'][0])} [{_ic_txt(p['ic_bajo'][0], p['ic_alto'][0])}] "
              f"n={int(p['n_tratados'][0])} -> {'ROMPE' if p['rompe'] else 'no rompe'}")
    print("E2 balance SMD: " + ", ".join(f"{k}={_g(v[0], 2)}" for k, v in res2["balance"].items() if k != "n_eventos"))
    print(f"E2 cota RR: {res2['cota']['veredicto']}; quiebre Mbar = {res2['cota']['quiebre']}")
    for op, x in res2["sin_operador"].items():
        print(f"E2 sin {op}: {_num(x['est'][j1])} [{_ic_txt(x['ic_bajo'][j1], x['ic_alto'][j1])}] n={int(x['n_tratados'][j1])}")
    print(f"E2 VEREDICTO: {res2['veredicto']}")


if __name__ == "__main__":
    main()
