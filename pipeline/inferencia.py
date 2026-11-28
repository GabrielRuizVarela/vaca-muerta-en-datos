"""Inferencia (porcion I): escala de los bloques, permutacion de D2 y Holm sobre la familia confirmatoria.

Se corre al final de los pasos causales:  uv run python -m pipeline.inferencia

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo cada una (857d434
para la regla de abajo), y el plan que nombran (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto
de cada regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porcion I de docs/plan-siguiente-nivel.md). Este commit trae la regla, las
constantes, la familia, Holm y los veredictos; no se calculo ninguna cifra con otra escala de bloque, ninguna permutacion y
ningun p. Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian los IC publicados con bloques de 5 km de D1 a D7.

I1. Escala de los bloques.
  * D1 (ATT(1) y sus tres placebos) y D2 (ATT_W y sus placebos previo, fecha falsa y distancia falsa) con bloques de cada
    tamano de TAMANOS_BLOQUE_KM: pipeline.bloques.clave_bloque con ese tamano en lugar de TAM_BLOQUE_KM, los mismos REPS y
    SEMILLA_CAUSAL, el resto de pipeline.causal sin cambio. Se publica el IC y la cantidad de bloques de cada tamano.
  * Veredicto (`veredicto_escala`): "sin muestra a N km" si con N km hay menos de MIN_BLOQUES bloques (ese tamano no
    decide); "no depende de la escala" si para cada cantidad el IC excluye cero en todos los tamanos con muestra o en
    ninguno; "depende de la escala: ..." con las cantidades que cambian.

I2. Permutacion de D2.
  * Observaciones: los pares (pozo, celda) de D2 con dW (tratados y controles de cada celda, k = 0). Estratos: bloque de
    TAM_BLOQUE_KM km del pozo, anio del mes g de la celda y grupo de edad. En cada permutacion, dentro de cada estrato se
    reparten al azar las etiquetas de tratado entre sus observaciones, con la misma cantidad de tratados; cada observacion
    queda en su celda con su dW. ATT_W se recalcula con la regla de D2 (celdas con al menos 1 tratado y
    MIN_CONTROLES_CELDA controles, pesadas por tratados).
  * R_PERM permutaciones, semilla SEMILLA_PERM. p a dos colas = (1 + #{|ATT_perm| >= |ATT_obs|}) / (1 + R_PERM). Se publica
    tambien la parte de las observaciones en estratos con las dos etiquetas.
  * Veredicto: "sobrevive a la permutacion" si p < ALFA; "no sobrevive a la permutacion" si no.

I3. Holm sobre la familia confirmatoria.
  * La familia es FAMILIA_CONFIRMATORIA: el estimando principal de cada diseno con veredicto, fijada aca y contada en el
    codigo (len). Las 17 hipotesis con umbral fijo del libro (wiki/hallazgos/ledger.csv) quedan fuera: comparan un valor
    con un umbral, sin distribucion muestral.
  * p de cada una: aproximacion normal a su IC 95% publicado, ee = (IC alto - IC bajo) / (2 Z_95), p = 2 (1 - Phi(|valor| /
    ee)). Un diseno "sin muestra", sin fila o sin IC entra con p = 1 (la familia no se achica). Para D2 se publica tambien el
    p de I2, que no reemplaza al de la familia.
  * Holm (1979) a ALFA. Se publica p, p ajustado, si rechaza, y k = len(FAMILIA_CONFIRMATORIA).
  * Publicado sin veredicto: de los intervalos de la descomposicion sin ajuste (los 141 de docs/paper/paper.md), cuantos
    siguen excluyendo cero con Holm dentro de su propia familia, con la misma aproximacion normal.

Mart: mart_inferencia_escala, mart_inferencia_permutacion y mart_inferencia_holm (cada uno con su llamada a
_escribir escrita con el nombre literal, para el linaje), y una pagina wiki/hallazgos/inferencia.md con la regla
citada por el SHA de este commit.

ACLARACION (2026-11-26, antes de calcular ninguna cifra de esta porcion). Puntos que la regla dejaba abiertos; se fijan aca y no
se tocan despues de ver un numero.
  * I1, veredicto por diseno: `veredicto_escala` se aplica dos veces, una con las cuatro cantidades de D1 (ATT(1) y sus tres
    placebos) y otra con las cuatro de D2 (ATT_W y sus tres placebos); cada diseno tiene su veredicto. "El IC excluye cero" es
    ic_bajo > 0 o ic_alto < 0. La cantidad de bloques de un tamano es la de los pozos tratados de las celdas primarias, la que
    cuentan D1 y D2 en su propio veredicto (D1 y D2 comparten celdas, asi que el conteo es el mismo). El bootstrap de cada
    tamano usa el mismo universo de pozos y la misma semilla que `pipeline.causal.main` (las seis familias de celdas, para que
    con 5 km salgan los mismos sorteos); solo cambia `D["bloque"]` por `clave_bloque(lat, lon, tamano)`.
  * I2, observaciones: son los pares (pozo, celda) de las celdas que D2 usa de verdad (al menos 1 tratado y MIN_CONTROLES_CELDA
    controles con dW); los pares de una celda que D2 descarta no entran, asi el ATT_W observado es el de D2. El anio de la celda
    es g // 12 (g es el indice absoluto de mes, anio * 12 + mes - 1). Un estrato sin las dos etiquetas no cambia en las
    permutaciones y cuenta en el denominador de la parte de observaciones. La comparacion es |perm| >= |obs| sin tolerancia.
  * I3, lectura de los marts: se busca la fila por la columna `diseno`; el mart de D7 (`mart_causal_profundo_d7`) no tiene esa
    columna sino `resultado`, y su estimando de corte de agua es la fila resultado = 'dW' (no hay fila 'D2'): FILA_ALIAS. El
    mart de D9 (`mart_causal_profundo_d9`) tiene las columnas del de D7 (regla de D9 en pipeline.causal_profundo) y va con el
    mismo alias; se agrego en la revision del PR, antes de que la familia leyera ninguna fila de D9. Un
    veredicto que empieza con "sin muestra" entra con p = 1 aunque la fila tenga IC (el caso de D1b).
  * I3, publicado sin veredicto: los 141 son las filas de mart_descomposicion_k (95), mart_descomposicion_aditiva (38) y
    mart_descomposicion_distancia (8), una prueba por fila, como las cuenta pipeline.bloques.conteo_pruebas. La cantidad de cada
    fila es su brecha con su IC (brecha, ic_bajo, ic_alto; en la aditiva brecha_total con total_ic_bajo y total_ic_alto). Una sola
    familia de Holm con las filas de las tres tablas. Se informa cuantas excluyen cero sin ajuste y cuantas con Holm.

ACLARACION 2 (2026-11-26, revision del PR #192, despues de la primera corrida). La regla de D11 da dos filas con veredicto,
D11a (`veredicto_rama`) y D11c (`veredicto_anillos`, sobre dW); D11b va sin veredicto. Como D4 y D12 entran con sus dos filas,
D11c entra tambien: k pasa de 15 a 16. Ya se conocian las cifras de D11 (pagina de exposicion: D11a y D11c dan "sin muestra",
con menos tratados por banda que MIN_TRATADOS_BANDA) y las de la primera corrida de esta familia; por la regla, las dos filas
de D11 entran con p = 1, asi que sumar D11c solo puede hacer a Holm mas exigente. El valor de la fila D11c es el anillo de 2 a
3 km; su veredicto puede decidirlo tambien el de 3 a 5 km.
ACLARACION 3 (2026-11-26, revision externa; antes de calcular ninguna cifra de I4 ni de la fila nueva de D3).
I4. Permutacion dentro de las celdas de D2.
  * Observaciones: las mismas de I2 (pares pozo, celda de las celdas que usa D2).
  * Cada estrato es la celda de D2. Toda celda que D2 usa tiene al menos 1 tratado y MIN_CONTROLES_CELDA controles, asi que
    toda observacion se mezcla.
  * En cada permutacion se reparten al azar las etiquetas de tratado dentro de cada celda, con la cantidad de tratados de
    esa celda. ATT_W se recalcula con la regla de D2, asi que los pesos de las celdas no cambian.
  * R_PERM permutaciones (2000), semilla SEMILLA_PERM + 1. p a dos colas, como en I2.
  * Se publica: p, los percentiles 2,5 y 97,5 y la media de la distribucion nula, y la parte de las observaciones que se
    mezcla (debe ser 100%; si no lo es, se dice por que).
  * Veredicto, como en I2: "sobrevive a la permutacion" si p < ALFA.
  * I4 es lo que los textos citan como la prueba de permutacion. I2 sigue publicada con su debilidad dicha.
  * Se declara sin vueltas: I4 se agrego despues de ver las cifras de I2 (8,0% de observaciones que se mezclan, nula no
    centrada en cero) y antes de calcular ninguna cifra de I4. Lo que no prueba: la intercambiabilidad dentro de la celda es el
    supuesto que D2 ya hace, asi que I4 no prueba las tendencias paralelas.
Holm, fila de D3. La familia lee D3 de `mart_causal_profundo_d3` donde cantidad = 'dA_pd' (valor, ic_bajo, ic_alto,
n_tratados), el estadistico con el que decide su veredicto, en lugar de `mart_causal_profundo_veredicto:D3` (que guarda dA, el
volumen de agua del mes). Se declara sin vueltas: esto cambia despues de ver el p de Holm de D3 con dA (0,1308). La regla propia de
D3 decide con dA_pd desde su commit; la familia pasa a leer el estadistico que usa el veredicto del diseno. Su estado y su
veredicto siguen saliendo de `mart_causal_profundo_veredicto:D3`. Ninguno de los dos cambios toca el veredicto de un diseno.
Mart de I4: mart_inferencia_permutacion, segunda fila (cantidad = CANT_PERM_CELDA).

ACLARACION 4 (2026-11-26, revision externa; despues de ver las cifras de I4 y antes de calcular ninguna cifra de I5).
I5. Permutacion por pad padre dentro de las celdas de D2.
  * Motivo: I4 reparte los pozos de a uno dentro de la celda y da p = 1/2001, el minimo, con la nula centrada en cero. La
    revision lo objeta: los padres tratados de un mismo pad hijo comparten tratamiento, y la pagina no lo dice. Los pozos de un
    pad reciben juntos la fractura del hijo y comparten shocks, asi que permutar pozos sueltos puede exagerar la precision.
  * Observaciones: los mismos pares (pozo, celda) de I2 y de I4.
  * Cluster: los pozos padres de una celda que comparten `pad_id` en `int_pozo_pad` (componentes conexas de bocas de pozo;
    `pad_id` es 'p' mas el menor pozo_id del componente, pipeline/sql/04_interferencia.sql). Un pozo sin fila en `int_pozo_pad`
    es su propio cluster de tamano 1.
  * Estratos: (celda, tamano del cluster). Los clusters del mismo tamano en la misma celda son intercambiables.
  * En cada permutacion se reparten al azar, entre los clusters de cada estrato, las cantidades de tratados por cluster. Dentro
    de un cluster que recibe k tratados de n pozos, los k tratados se sortean con probabilidad uniforme entre sus n pozos. Asi
    cada celda conserva exactamente su cantidad de tratados y los pesos de las celdas de D2 no cambian. ATT_W se recalcula con
    la regla de D2 (`att_w`).
  * R_PERM permutaciones (2000), semilla SEMILLA_PERM + 2 (SEMILLA_PERM_PAD). p a dos colas, como en I2 y en I4.
  * Se publica: p, los percentiles 2,5 y 97,5 y la media de la distribucion nula; la cantidad de clusters y la parte de las
    observaciones que esta en clusters de mas de un pozo; y la parte que se mezcla (observaciones en estratos con al menos
    dos clusters de distinta cantidad de tratados).
  * Veredicto, como en I2 y en I4 (`veredicto_permutacion`): "sobrevive a la permutacion" si p < ALFA.
  * No entra en la familia de Holm, como I4. Los textos siguen citando I4 como la prueba de permutacion y agregan I5 como su
    version por pad. Si I5 no sobrevive, los textos lo dicen.
  * Se declara sin vueltas: I5 se agrego despues de ver las cifras de I4 (p en su minimo, nula centrada en cero) y la
    observacion de la revision, y antes de calcular ninguna cifra de I5. Lo que no prueba: los pads son clusters de bocas de
    pozo, no de laterales; un pad hijo puede alcanzar varios pads padres, que siguen correlacionados entre clusters; y la
    intercambiabilidad dentro de la celda es el supuesto que D2 ya hace, asi que I5 no prueba las tendencias paralelas.
  * Se corrigen dos frases de la pagina: la linea 3 de la pagina dice que la fila de D3 en Holm se fijo "antes de calcular
    ninguna cifra de ellas", y no es asi (el valor y el IC de dA_pd ya eran cifras publicadas del veredicto de D3, y el
    cambio se fijo despues de ver el p de D3 con dA); y el "que no prueba" de I4 agrega que las etiquetas se permutan pozo por
    pozo y no por pad, y que I5 lo hace por pad.
Mart de I5: mart_inferencia_permutacion, tercera fila (cantidad = CANT_PERM_PAD).
"""
from __future__ import annotations

import math

from pipeline.causal import MIN_BLOQUES, MIN_CONTROLES_CELDA, REPS, SEMILLA_CAUSAL, TAM_BLOQUE_KM

REGLA_HEREDADA = {"MIN_BLOQUES": MIN_BLOQUES, "MIN_CONTROLES_CELDA": MIN_CONTROLES_CELDA, "REPS": REPS,
                  "TAM_BLOQUE_KM": TAM_BLOQUE_KM}

# ---- regla fijada (no cambiar despues de ver cifras) ----
TAMANOS_BLOQUE_KM = (2.0, 5.0, 10.0)
R_PERM = 2000
SEMILLA_PERM = SEMILLA_CAUSAL + 70
SEMILLA_PERM_CELDA = SEMILLA_PERM + 1
CANT_PERM_I2 = "ATT_W (pp)"
SEMILLA_PERM_PAD = SEMILLA_PERM + 2
CANT_PERM_CELDA = "ATT_W (pp), I4 dentro de la celda"
CANT_PERM_PAD = "ATT_W (pp), I5 por pad padre"
ALFA = 0.05
Z_95 = 1.959964

# (id, mart, diseno en ese mart): el estimando principal de cada diseno con veredicto. Los de los marts nuevos los escribe
# su construccion con columnas diseno, veredicto, valor, ic_bajo, ic_alto, n_tratados.
FAMILIA_CONFIRMATORIA = (
    ("D1", "mart_causal_veredicto", "D1"),                       # ATT(1) del petroleo, aun no tratados
    ("D1b", "mart_causal_veredicto", "D1b"),                     # persistencia, meses 7 a 24
    ("D2", "mart_causal_veredicto", "D2"),                       # corte de agua
    ("D3", "mart_causal_profundo_d3", "dA_pd"),                  # agua por dia producido (ACLARACION 3)
    ("D4_distancia", "mart_causal_profundo_veredicto", "D4_distancia"),
    ("D4_tamano", "mart_causal_profundo_veredicto", "D4_tamano"),
    ("D5", "mart_causal_profundo_veredicto", "D5"),              # media tarde de dW
    ("D6", "mart_causal_profundo_veredicto", "D6"),              # sin el operador de IC bajo mas chico
    ("D7", "mart_causal_profundo_d7", "D2"),                     # Colorado, el D2 de su mart
    ("D9", "mart_causal_profundo_d9", "D2"),                     # Wyoming, el D2 de su mart
    ("E", "mart_apilado", "E"),                                  # ATT(1) apilado
    ("E2", "mart_apilado_e2", "E2"),                             # E con donantes a 2 a 10 km (regla E2 de stacked)
    ("D10", "mart_causal_exposicion_veredicto", "D10"),          # D5 censurado
    ("D11a", "mart_causal_exposicion_veredicto", "D11a"),        # diferencia por rama
    ("D11c", "mart_causal_exposicion_veredicto", "D11c"),        # anillos (ACLARACION 2)
    ("D12a", "mart_causal_exposicion_veredicto", "D12a"),        # dentro de operador y area
    ("D12b", "mart_causal_exposicion_veredicto", "D12b"),        # fuera de YPF
    ("D14", "mart_causal_d14", "D14"),                           # D2 con el golpe por distancia entre ramas (regla en causal_exposicion)
    ("R1", "mart_golpes_repetidos_veredicto", "R1"),             # cada golpe posterior como su propio evento (regla 0670d9c en golpes_repetidos)
    ("D13", "mart_causal_profundo_d13", "D13"),                  # Colorado sin cada operador (regla en causal_profundo, D13)
)

# marts de D7 y D9 (las mismas columnas): la fila de su estimando de corte de agua (ver ACLARACION)
FILA_ALIAS = {("mart_causal_profundo_d7", "D2"): "dW", ("mart_causal_profundo_d9", "D2"): "dW"}

# D3: el estimando sale de su mart de cantidades, el estado y el veredicto del mart de veredictos (ACLARACION 3)
VEREDICTO_DE = {"D3": ("mart_causal_profundo_veredicto", "D3")}

V_ESCALA_NO = "no depende de la escala"
V_ESCALA_SI = "depende de la escala: {}"
V_ESCALA_SIN = "sin muestra a {:g} km"
V_PERM_SI = "sobrevive a la permutación"
V_PERM_NO = "no sobrevive a la permutación"


def p_normal(valor: float | None, bajo: float | None, alto: float | None) -> float:
    """p a dos colas de la aproximacion normal a un IC 95%; 1 si falta algo o el IC no tiene ancho."""
    if valor is None or bajo is None or alto is None or any(map(math.isnan, (valor, bajo, alto))) or alto <= bajo:
        return 1.0
    z = abs(valor) / ((alto - bajo) / (2 * Z_95))
    return math.erfc(z / math.sqrt(2))


def holm(ps: list[float], alfa: float = ALFA) -> tuple[list[float], list[bool]]:
    """p ajustados de Holm (monotonos, recortados en 1) y si cada hipotesis se rechaza a `alfa`."""
    k = len(ps)
    orden = sorted(range(k), key=lambda i: ps[i])
    ajust = [1.0] * k
    previo = 0.0
    for r, i in enumerate(orden):
        previo = max(previo, min(1.0, (k - r) * ps[i]))
        ajust[i] = previo
    return ajust, [a < alfa for a in ajust]


def veredicto_permutacion(p: float) -> str:
    return V_PERM_SI if p < ALFA else V_PERM_NO


def veredicto_escala(excluye: dict[str, dict[float, bool]], bloques: dict[float, int]) -> str:
    """excluye: cantidad -> {tamano: el IC excluye cero}; bloques: tamano -> cantidad de bloques."""
    sin = [t for t in TAMANOS_BLOQUE_KM if bloques.get(t, 0) < MIN_BLOQUES]
    validos = [t for t in TAMANOS_BLOQUE_KM if t not in sin]
    cambian = sorted(q for q, por in excluye.items() if len({por[t] for t in validos if t in por}) > 1)
    if cambian:
        return V_ESCALA_SI.format(", ".join(cambian))
    if sin:
        return "; ".join([V_ESCALA_NO] + [V_ESCALA_SIN.format(t) for t in sin])
    return V_ESCALA_NO


# ------------------------------------------------------------------ calculo (no cambia la regla de arriba)
import duckdb
import numpy as np

from pipeline.bloques import clave_bloque
from pipeline.causal import (E_PRINCIPAL, H_CORTO, V_SIN_MUESTRA, _bootstrap_prep, _cohorte_falsa_distancia,
                             _cohorte_falsa_fecha, _cohorte_nunca_tratados, _n_bloques, _pesos_bloques, _preparar,
                             _valores_agua, bootstrap, cargar, celdas, celdas_d1b, cohortes)
from pipeline.costo import _escribir
from pipeline.ingest import DATA, ROOT

COMMIT_REGLA = "857d434"
COMMIT_REGLA_DOCSTRING = "f72c10c"
COMMIT_ACLARACION_1 = "88a9168"    # puntos abiertos de la regla, antes de calcular ninguna cifra
COMMIT_ACLARACION_2 = "eb1c51b"    # D11c entra en Holm (k = 16), despues de la primera corrida
COMMIT_ACLARACION_4 = "052ee98"    # I5 (permutacion por pad padre): regla antes de calcular
COMMIT_ACLARACION_3 = "19415b3"    # I4 y la fila de D3 en Holm: regla antes de calcular
PAGINA = ROOT / "wiki" / "hallazgos" / "inferencia.md"

COLS_ESCALA = [("diseno", "varchar"), ("cantidad", "varchar"), ("tam_km", "double"), ("n_bloques", "integer"),
               ("n_tratados", "integer"), ("valor", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
               ("excluye_cero", "boolean"), ("veredicto", "varchar")]
COLS_PERM = [("cantidad", "varchar"), ("valor", "double"), ("r_perm", "integer"), ("semilla", "bigint"),
             ("p", "double"), ("veredicto", "varchar"), ("n_obs", "integer"), ("n_estratos", "integer"),
             ("parte_obs_estratos_mixtos", "double"), ("n_tratados", "integer"), ("perm_p2_5", "double"),
             ("perm_p97_5", "double"), ("perm_media", "double"), ("n_clusters", "integer"),
             ("parte_obs_multipozo", "double")]
COLS_HOLM = [("familia", "varchar"), ("id", "varchar"), ("fuente", "varchar"), ("estado", "varchar"), ("veredicto", "varchar"),
             ("valor", "double"), ("ic_bajo", "double"), ("ic_alto", "double"), ("n_tratados", "integer"),
             ("p", "double"), ("p_holm", "double"), ("rechaza", "boolean"), ("excluye_cero", "boolean"), ("k", "integer"),
             ("p_permutacion", "double")]

NOMBRES_ESCALA = {"ATT": "ATT(1)", "fecha_falsa": "placebo de fecha falsa", "distancia_falsa": "placebo de distancia falsa",
                  "nunca_tratados": "placebo de nunca tratados", "previo": "placebo previo"}


def excluye_cero(bajo: float, alto: float) -> bool:
    return bool(not (math.isnan(bajo) or math.isnan(alto)) and (bajo > 0 or alto < 0))


def preparar_datos(con) -> dict:
    """Cohortes, celdas y universo de pozos del bootstrap: lo mismo que arma pipeline.causal.main."""
    D = cargar(con)
    coh = cohortes(D)
    cel_pri = celdas(D, coh, H_CORTO, False)
    cel_s1 = celdas(D, coh, H_CORTO, True)
    trat_ff, g_ff = _cohorte_falsa_fecha(D, coh)
    cel_ff = celdas(D, coh, H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = _cohorte_falsa_distancia(D, coh, H_CORTO)
    cel_fd = celdas(D, coh, H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = _cohorte_nunca_tratados(D, coh)
    cel_nt = celdas(D, coh, H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    cel_d1b = celdas_d1b(D, coh)
    wells = []
    for grupo in (cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b):
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    return {"D": D, "coh": coh, "pri": cel_pri, "ff": cel_ff, "fd": cel_fd, "nt": cel_nt, "pozos": wells}


# ---- I1
def escala_tamano(datos: dict, tam: float) -> tuple[int, list[tuple]]:
    """D1 y D2 con bloques de `tam` km. Devuelve (bloques de los tratados primarios, filas sin veredicto)."""
    D = dict(datos["D"], bloque=clave_bloque(datos["D"]["lat"], datos["D"]["lon"], tam))
    rng = np.random.default_rng(SEMILLA_CAUSAL)
    W = _pesos_bloques(D, datos["pozos"], REPS, rng)
    trat = np.concatenate([ce["tratados"] for ce in datos["pri"]]) if datos["pri"] else np.zeros(0, dtype=np.int64)
    nb = _n_bloques(D, trat)
    filas = []
    for clave, cel in (("ATT", datos["pri"]), ("fecha_falsa", datos["ff"]), ("distancia_falsa", datos["fd"]),
                       ("nunca_tratados", datos["nt"])):
        r = bootstrap(D, cel, (E_PRINCIPAL,), W)
        filas.append(("D1", clave, int(r["n_tratados"][0]), float(r["est"][0]), float(r["ic_bajo"][0]), float(r["ic_alto"][0])))
    for clave, cel, k in (("ATT", datos["pri"], 0), ("previo", datos["pri"], -2), ("fecha_falsa", datos["ff"], 0),
                          ("distancia_falsa", datos["fd"], 0)):
        vt, vc = _valores_agua(D, cel, k)
        r = _bootstrap_prep(D, _preparar(cel, vt, vc), W)
        filas.append(("D2", clave, int(r["n_tratados"]), float(r["est"]), float(r["ic_bajo"]), float(r["ic_alto"])))
    return nb, filas


def escala(datos: dict) -> list[tuple]:
    por_tam = {t: escala_tamano(datos, t) for t in TAMANOS_BLOQUE_KM}
    bloques = {t: nb for t, (nb, _) in por_tam.items()}
    filas = []
    for diseno in ("D1", "D2"):
        excl: dict[str, dict[float, bool]] = {}
        for t, (_, fs) in por_tam.items():
            for d, clave, _, _, bajo, alto in fs:
                if d == diseno:
                    excl.setdefault(NOMBRES_ESCALA[clave], {})[t] = excluye_cero(bajo, alto)
        if diseno == "D2":
            excl = {("ATT_W" if q == "ATT(1)" else q): por for q, por in excl.items()}
        ver = veredicto_escala(excl, bloques)
        for t, (nb, fs) in por_tam.items():
            for d, clave, n_t, est, bajo, alto in fs:
                if d == diseno:
                    filas.append((d, "ATT_W" if (d, clave) == ("D2", "ATT") else NOMBRES_ESCALA[clave], float(t), int(nb), n_t, est, bajo, alto,
                                  excluye_cero(bajo, alto), ver))
    return filas


# ---- I2
def att_w(celda: np.ndarray, valor: np.ndarray, trat: np.ndarray, n_celdas: int) -> float:
    """ATT_W (puntos porcentuales) con la regla de celdas de D2: al menos un tratado y MIN_CONTROLES_CELDA controles."""
    nt = np.bincount(celda, weights=trat, minlength=n_celdas)
    nc = np.bincount(celda, weights=~trat, minlength=n_celdas)
    st = np.bincount(celda, weights=trat * valor, minlength=n_celdas)
    sc = np.bincount(celda, weights=(~trat) * valor, minlength=n_celdas)
    ok = (nt >= 1) & (nc >= MIN_CONTROLES_CELDA)
    if not ok.any():
        return float("nan")
    dif = st[ok] / nt[ok] - sc[ok] / nc[ok]
    return float(100.0 * (nt[ok] * dif).sum() / nt[ok].sum())


def etiquetas_permutadas(estrato: np.ndarray, trat: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Reparte al azar las etiquetas de tratado dentro de cada estrato, con la misma cantidad de tratados por estrato."""
    n = len(estrato)
    _, cod = np.unique(estrato, return_inverse=True)
    orden = np.argsort(cod + rng.random(n), kind="stable")        # agrupa por estrato; adentro, orden al azar
    cod_s = cod[orden]
    n_t = np.bincount(cod, weights=trat).astype(np.int64)
    inicio = np.concatenate([[0], np.cumsum(np.bincount(cod))[:-1]])
    rango = np.arange(n) - inicio[cod_s]
    nueva = np.zeros(n, dtype=bool)
    nueva[orden] = rango < n_t[cod_s]
    return nueva


def observaciones_d2(datos: dict) -> dict:
    """Pares (pozo, celda) de las celdas que usa D2, con dW, etiqueta y estrato (bloque, anio de g, grupo de edad)."""
    D = datos["D"]
    vt, vc = _valores_agua(D, datos["pri"], 0)
    pozo, celda, val, trat, g, grupo = [], [], [], [], [], []
    k = 0
    for ce, a, b in zip(datos["pri"], vt, vc):
        okt, okc = ~np.isnan(a), ~np.isnan(b)
        if int(okt.sum()) < 1 or int(okc.sum()) < MIN_CONTROLES_CELDA:
            continue
        for pz, v, t in ((ce["tratados"][okt], a[okt], True), (ce["controles"][okc], b[okc], False)):
            pozo.append(pz)
            val.append(v)
            trat.append(np.full(len(pz), t))
            celda.append(np.full(len(pz), k))
            g.append(np.full(len(pz), ce["g"]))
            grupo.append(np.full(len(pz), ce["grupo"]))
        k += 1
    pozo, val, trat = np.concatenate(pozo), np.concatenate(val), np.concatenate(trat)
    celda, g, grupo = np.concatenate(celda), np.concatenate(g), np.concatenate(grupo)
    bloque = D["bloque"][pozo]
    # un entero por (bloque, anio de g, grupo): np.unique sobre las filas
    estrato = np.unique(np.column_stack([bloque, g // 12, grupo]), axis=0, return_inverse=True)[1].reshape(-1)
    return {"pozo": pozo, "celda": celda, "valor": val, "trat": trat, "estrato": estrato, "n_celdas": k}


def permutacion(obs: dict, reps: int = R_PERM, semilla: int = SEMILLA_PERM) -> dict:
    celda, valor, trat, estrato, nc = obs["celda"], obs["valor"], obs["trat"], obs["estrato"], obs["n_celdas"]
    att_obs = att_w(celda, valor, trat, nc)
    rng = np.random.default_rng(semilla)
    perm = np.array([att_w(celda, valor, etiquetas_permutadas(estrato, trat, rng), nc) for _ in range(reps)])
    p = (1 + int((np.abs(perm) >= abs(att_obs)).sum())) / (1 + reps)
    n_t = np.bincount(estrato, weights=trat)
    n_c = np.bincount(estrato, weights=~trat)
    mixto = (n_t > 0) & (n_c > 0)
    return {"att_obs": att_obs, "p": p, "perm": perm, "n_obs": int(len(valor)), "n_estratos": int(len(n_t)),
            "parte_mixtos": float((n_t + n_c)[mixto].sum() / (n_t + n_c).sum()), "n_tratados": int(trat.sum())}


def observaciones_celda(obs: dict) -> dict:
    """I4: las mismas observaciones de I2 con la celda de D2 como estrato."""
    return dict(obs, estrato=obs["celda"])


def permutacion_celda(obs: dict, reps: int = R_PERM, semilla: int = SEMILLA_PERM_CELDA) -> dict:
    """I4: etiquetas de tratado permutadas dentro de cada celda de D2 (cada celda conserva su cantidad de tratados)."""
    return permutacion(observaciones_celda(obs), reps, semilla)


def observaciones_pad(obs: dict, pozo_id: np.ndarray, pad_de_pozo: dict) -> dict:
    """I5: las mismas observaciones de I2 con el pad padre de cada pozo (un pozo sin pad es su propio cluster)."""
    ids = [int(x) for x in pozo_id[obs["pozo"]]]
    claves = [pad_de_pozo.get(i, f"w{i}") for i in ids]
    pad = np.unique(np.array(claves, dtype=object).astype(str), return_inverse=True)[1].reshape(-1)
    return dict(obs, pad=pad)


def _clusters_pad(obs: dict) -> dict:
    """Clusters (celda, pad) con su tamano y cantidad de tratados, y su estrato (celda, tamano)."""
    clave = np.column_stack([obs["celda"], obs["pad"]])
    _, cod = np.unique(clave, axis=0, return_inverse=True)
    cod = cod.reshape(-1)
    tam = np.bincount(cod)
    k = np.bincount(cod, weights=obs["trat"]).astype(np.int64)
    celda_c = np.zeros(len(tam), dtype=np.int64)
    celda_c[cod] = obs["celda"]
    estrato = np.unique(np.column_stack([celda_c, tam]), axis=0, return_inverse=True)[1].reshape(-1)
    return {"cod": cod, "tam": tam, "k": k, "estrato": estrato}


def etiquetas_permutadas_pad(cl: dict, rng: np.random.Generator) -> np.ndarray:
    """I5: reparte entre los clusters de cada estrato las cantidades de tratados y, dentro de cada cluster, sortea cuales."""
    cod, k, estrato = cl["cod"], cl["k"], cl["estrato"]
    base = np.argsort(estrato, kind="stable")
    nuevo = np.lexsort((rng.random(len(k)), estrato))     # mismo orden de estratos; adentro, al azar
    k_nuevo = np.empty_like(k)
    k_nuevo[nuevo] = k[base]
    n = len(cod)
    orden = np.argsort(cod + rng.random(n), kind="stable")
    inicio = np.concatenate([[0], np.cumsum(cl["tam"])[:-1]])
    rango = np.arange(n) - inicio[cod[orden]]
    nueva = np.zeros(n, dtype=bool)
    nueva[orden] = rango < k_nuevo[cod[orden]]
    return nueva


def permutacion_pad(obs: dict, reps: int = R_PERM, semilla: int = SEMILLA_PERM_PAD) -> dict:
    """I5: etiquetas de tratado permutadas por pad padre dentro de cada celda de D2 (cada celda conserva sus tratados)."""
    celda, valor, trat, nc = obs["celda"], obs["valor"], obs["trat"], obs["n_celdas"]
    cl = _clusters_pad(obs)
    att_obs = att_w(celda, valor, trat, nc)
    rng = np.random.default_rng(semilla)
    perm = np.array([att_w(celda, valor, etiquetas_permutadas_pad(cl, rng), nc) for _ in range(reps)])
    p = (1 + int((np.abs(perm) >= abs(att_obs)).sum())) / (1 + reps)
    # estrato mezclado: al menos dos clusters con distinta cantidad de tratados
    e, k, tam = cl["estrato"], cl["k"], cl["tam"]
    n_e = int(e.max()) + 1
    kmin = np.full(n_e, np.iinfo(np.int64).max)
    kmax = np.full(n_e, -1)
    np.minimum.at(kmin, e, k)
    np.maximum.at(kmax, e, k)
    obs_e = np.bincount(e, weights=tam)
    mixto = kmax > kmin
    return {"att_obs": att_obs, "p": p, "perm": perm, "n_obs": int(len(valor)), "n_estratos": n_e,
            "n_clusters": int(len(tam)), "parte_multipozo": float(tam[tam > 1].sum() / tam.sum()),
            "parte_mixtos": float(obs_e[mixto].sum() / obs_e.sum()), "n_tratados": int(trat.sum())}


# ---- I3
def leer_fila(con, mart: str, diseno: str) -> dict | None:
    """Fila `diseno` de `mart` (columna diseno, o resultado en los marts de D7 y D9); None si falta el mart o la fila."""
    cols = [r[0] for r in con.execute("select column_name from information_schema.columns where table_name = ?",
                                      [mart]).fetchall()]
    if not cols:
        return None
    clave = "diseno" if "diseno" in cols else "resultado" if "resultado" in cols else "cantidad" if "cantidad" in cols else None
    if clave is None:
        return None
    fila = FILA_ALIAS.get((mart, diseno), diseno)
    sel = [c if c in cols else f"null as {c}" for c in ("veredicto", "valor", "ic_bajo", "ic_alto", "n_tratados")]
    r = con.execute(f"select {', '.join(sel)} from {mart} where {clave} = ? limit 1", [fila]).fetchone()
    if r is None:
        return None
    return dict(zip(("veredicto", "valor", "ic_bajo", "ic_alto", "n_tratados"), r))


def p_de_fila(fila: dict | None) -> tuple[str, float]:
    """(estado, p) de una fila de la familia: sin mart, sin fila, sin muestra o sin IC entran con p = 1."""
    if fila is None:
        return "sin fila o sin mart", 1.0
    if str(fila["veredicto"] or "").startswith(V_SIN_MUESTRA):
        return "sin muestra", 1.0
    if any(fila[c] is None or math.isnan(fila[c]) for c in ("valor", "ic_bajo", "ic_alto")):
        return "sin IC", 1.0
    return "leido", p_normal(fila["valor"], fila["ic_bajo"], fila["ic_alto"])


def familia_holm(con, p_perm_d2: float) -> list[tuple]:
    k = len(FAMILIA_CONFIRMATORIA)
    leidas = []
    for id_, mart, diseno in FAMILIA_CONFIRMATORIA:
        fila = leer_fila(con, mart, diseno)
        if id_ in VEREDICTO_DE and fila is not None:
            otra = leer_fila(con, *VEREDICTO_DE[id_])
            fila["veredicto"] = None if otra is None else otra["veredicto"]
        estado, p = p_de_fila(fila)
        leidas.append((id_, f"{mart}:{FILA_ALIAS.get((mart, diseno), diseno)}", estado, fila, p))
    ajust, rech = holm([x[4] for x in leidas])
    out = []
    for (id_, fuente, estado, fila, p), a, r in zip(leidas, ajust, rech):
        f = fila or {"veredicto": None, "valor": None, "ic_bajo": None, "ic_alto": None, "n_tratados": None}
        bajo = float(f["ic_bajo"]) if f["ic_bajo"] is not None else float("nan")
        alto = float(f["ic_alto"]) if f["ic_alto"] is not None else float("nan")
        out.append(("confirmatoria", id_, fuente, estado, f["veredicto"], _f(f["valor"]), bajo, alto,
                    None if f["n_tratados"] is None else int(f["n_tratados"]), p, a, r, excluye_cero(bajo, alto), k,
                    p_perm_d2 if id_ == "D2" else None))
    return out


def _f(x) -> float:
    return float("nan") if x is None else float(x)


TABLAS_DESCOMPOSICION = (
    ("mart_descomposicion_k", "panel || ':k=' || k", "brecha", "ic_bajo", "ic_alto"),
    ("mart_descomposicion_aditiva", "variante || ':k=' || k", "brecha_total", "total_ic_bajo", "total_ic_alto"),
    ("mart_descomposicion_distancia", "banda || ':' || control", "brecha", "ic_bajo", "ic_alto"),
)


def descomposicion_holm(con) -> list[tuple]:
    """Los intervalos de la descomposicion (una prueba por fila de las tres tablas) con Holm en una familia."""
    filas = []
    for tabla, ident, est, bajo, alto in TABLAS_DESCOMPOSICION:
        for id_, v, b, a in con.execute(f"select {ident}, {est}, {bajo}, {alto} from {tabla} order by 1").fetchall():
            filas.append((tabla, id_, _f(v), _f(b), _f(a)))
    ps = [p_normal(v, b, a) for _, _, v, b, a in filas]
    ajust, rech = holm(ps)
    k = len(filas)
    return [("descomposicion", id_, tabla, "leido", None, v, b, a, None, p, aj, r, excluye_cero(b, a), k, None)
            for (tabla, id_, v, b, a), p, aj, r in zip(filas, ps, ajust, rech)]


# ---- pagina
def _n(x, dec: int = 2) -> str:
    from pipeline.causal import _g
    return _g(x, dec)


def _p(x: float) -> str:
    return "< 0,0001" if x < 1e-4 else _n(x, 4)


def pagina(con) -> str:
    esc = con.execute("select diseno, cantidad, tam_km, n_bloques, n_tratados, valor, ic_bajo, ic_alto, excluye_cero, veredicto "
                      "from mart_inferencia_escala order by diseno, case when cantidad in ('ATT(1)', 'ATT_W') then 0 else 1 end, cantidad, tam_km").fetchall()
    per = con.execute("select valor, r_perm, semilla, p, veredicto, n_obs, n_estratos, parte_obs_estratos_mixtos, n_tratados, "
                      "perm_p2_5, perm_p97_5 from mart_inferencia_permutacion where cantidad = ?", [CANT_PERM_I2]).fetchone()
    per4 = con.execute("select valor, r_perm, semilla, p, veredicto, n_obs, n_estratos, parte_obs_estratos_mixtos, n_tratados, "
                       "perm_p2_5, perm_p97_5, perm_media from mart_inferencia_permutacion where cantidad = ?",
                       [CANT_PERM_CELDA]).fetchone()
    per5 = con.execute("select valor, r_perm, semilla, p, veredicto, n_obs, n_estratos, parte_obs_estratos_mixtos, n_tratados, "
                       "perm_p2_5, perm_p97_5, perm_media, n_clusters, parte_obs_multipozo from mart_inferencia_permutacion "
                       "where cantidad = ?", [CANT_PERM_PAD]).fetchone()
    fam = con.execute("select id, fuente, estado, veredicto, valor, ic_bajo, ic_alto, n_tratados, p, p_holm, rechaza, k, p_permutacion "
                      "from mart_inferencia_holm where familia = 'confirmatoria' order by p").fetchall()
    desc = con.execute("select count(*), sum(excluye_cero::int), sum(rechaza::int) from mart_inferencia_holm "
                       "where familia = 'descomposicion'").fetchone()
    L = ["# Inferencia: escala de los bloques, permutación de D2 y Holm", "",
         f"Regla fijada en el commit {COMMIT_REGLA} (y {COMMIT_REGLA_DOCSTRING}, que solo cambia el docstring). La primera "
         f"aclaración se fijó en {COMMIT_ACLARACION_1}, antes de calcular ninguna cifra; la segunda, que suma la fila D11c a la familia "
         f"de Holm, en {COMMIT_ACLARACION_2}, después de la primera corrida y cuando ya se conocían las cifras de D11. "
         f"La permutación dentro de las celdas (I4) y la fila de D3 en la familia de Holm se fijaron en {COMMIT_ACLARACION_3}, antes de "
         "calcular ninguna cifra de I4, y después de ver las de I2; la fila de D3 se fijó después de ver el p de D3 con el volumen "
         "de agua del mes, cuando el valor y el IC de dA_pd ya eran cifras publicadas del veredicto de D3. "
         f"La permutación por pad padre (I5) se fijó en {COMMIT_ACLARACION_4}, antes de calcular ninguna cifra de I5. "
         "Ningún número de esta página está escrito a mano: salen de `mart_inferencia_escala`, `mart_inferencia_permutacion` y "
         "`mart_inferencia_holm`. Se corre con `uv run python -m pipeline.inferencia`.", ""]
    veredictos = {}
    for r in esc:
        veredictos[r[0]] = r[9]
    L += ["## I1. ¿El intervalo depende del tamaño del bloque?", "",
          f"Se repite el bootstrap de D1 y D2 con bloques de {', '.join(_n(t, 0) for t in TAMANOS_BLOQUE_KM)} km "
          f"(mismos {REPS} sorteos y misma semilla que el análisis principal; 5 km es el publicado).", ""]
    for d in ("D1", "D2"):
        L += [f"**{d}: {veredictos[d]}.**", "", "| Cantidad | Bloque (km) | Bloques | Tratados | Valor | IC 95% | ¿Excluye cero? |",
              "| --- | ---: | ---: | ---: | ---: | --- | --- |"]
        for r in esc:
            if r[0] == d:
                L.append(f"| {r[1]} | {_n(r[2], 0)} | {r[3]} | {r[4]} | {_n(r[5])} | {_n(r[6])} a {_n(r[7])} | {'sí' if r[8] else 'no'} |")
        L.append("")
    valor, rp, sem, p, ver, n_obs, n_est, parte, n_t, q1, q2 = per
    L += ["## I2. Permutación de D2 (débil; la reemplaza I4)", "",
          "Esta prueba se publica con su debilidad dicha. La prueba de permutación que citan los textos es I4, más abajo.", "",
          f"**{ver[0].upper() + ver[1:]}** (p = {_n(p, 4)}, α = {_n(ALFA, 2)}).", "",
          "| Cantidad | Valor | Permutaciones | Semilla | p a dos colas | Observaciones | Estratos | Observaciones en estratos con las dos etiquetas | Tratados |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
          f"| ATT_W (pp) | {_n(valor)} | {rp} | {sem} | {_n(p, 4)} | {n_obs} | {n_est} | {_n(100 * parte, 1)}% | {n_t} |", "",
          f"Los percentiles 2,5 y 97,5 de ATT_W bajo la permutación son {_n(q1)} y {_n(q2)} pp.", "",
          "Qué no prueba: la permutación reparte las etiquetas de tratado entre pozos del mismo bloque, año de la cohorte y grupo de "
          "edad. Prueba que el ATT_W observado no sale de repartir al azar la etiqueta dentro de esos estratos. No prueba las "
          "tendencias paralelas, ni que la elección de controles sea la correcta, ni que no haya otra causa que siga al golpe "
          "(la ubicación fina, la geología, el calendario de cada operador). Los estratos con una sola etiqueta no cambian en "
          "ninguna permutación y por eso se informa la parte de las observaciones que sí se mezcla.", "",
          f"Una consecuencia que se ve en los números: solo el {_n(100 * parte, 1)}% de las observaciones está en estratos con las dos "
          f"etiquetas. El resto conserva su etiqueta en todas las permutaciones, así que la distribución de ATT_W bajo la permutación "
          f"({_n(q1)} a {_n(q2)} pp) no se centra en cero. El p mide cuánto se aleja el valor observado ({_n(valor)} pp) de lo que "
          f"queda al mezclar solo esa parte; con {rp} permutaciones el p no puede bajar de {_n(1 / (1 + rp), 4)}"
          f"{' y es ese mínimo' if p <= 1 / (1 + rp) + 1e-12 else ''}. Es una prueba débil y se lee así.", ""]
    v4, rp4, sem4, p4, ver4, n_obs4, n_est4, parte4, n_t4, a1, a2, media4 = per4
    L += ["## I4. Permutación dentro de las celdas de D2", "",
          f"**{ver4[0].upper() + ver4[1:]}** (p = {_n(p4, 4)}, α = {_n(ALFA, 2)}).", "",
          "Cada estrato es la celda de D2 (cohorte y mes de cada tratado con sus controles). Toda celda que D2 usa tiene al menos "
          f"un tratado y {MIN_CONTROLES_CELDA} controles, así que toda observación se mezcla. En cada permutación se reparten al azar las "
          "etiquetas de tratado dentro de cada celda, con la cantidad de tratados de esa celda, y ATT_W se recalcula con la regla de D2 "
          "(los pesos de las celdas no cambian).", "",
          "| Cantidad | Valor | Permutaciones | Semilla | p a dos colas | Observaciones | Celdas | Observaciones que se mezclan | Tratados |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
          f"| ATT_W (pp) | {_n(v4)} | {rp4} | {sem4} | {_n(p4, 4)} | {n_obs4} | {n_est4} | {_n(100 * parte4, 1)}% | {n_t4} |", "",
          f"Bajo la permutación, ATT_W tiene media {_n(media4)} pp y percentiles 2,5 y 97,5 de {_n(a1)} y {_n(a2)} pp"
          f"{'' if parte4 >= 1 - 1e-12 else '; no todas las observaciones se mezclan (hay celdas sin las dos etiquetas)'}. "
          f"Con {rp4} permutaciones el p no puede bajar de {_n(1 / (1 + rp4), 4)}"
          f"{' y es ese mínimo' if p4 <= 1 / (1 + rp4) + 1e-12 else ''}.", "",
          "I4 se agregó después de ver las cifras de I2 (solo el "
          f"{_n(100 * parte, 1)}% de las observaciones se mezclaba y la nula no se centraba en cero) y antes de calcular ninguna cifra "
          "de I4.", "",
          "Qué no prueba: la permutación supone que, dentro de una celda, tratados y controles son intercambiables si no hay efecto. "
          "Ese es el supuesto que D2 ya hace, así que I4 no prueba las tendencias paralelas, ni que la elección de controles sea la "
          "correcta, ni que no haya otra causa que siga al golpe. Solo dice que el ATT_W observado no sale de repartir al azar la "
          "etiqueta dentro de cada celda. Reparte los pozos de a uno, no por pad; I5, más abajo, lo hace por pad.", ""]
    v5, rp5, sem5, p5, ver5, n_obs5, n_est5, parte5, n_t5, e1, e2, media5, ncl5, multi5 = per5
    L += ["## I5. Permutación por pad padre dentro de las celdas de D2", "",
          f"**{ver5[0].upper() + ver5[1:]}** (p = {_n(p5, 4)}, α = {_n(ALFA, 2)}).", "",
          "I4 reparte los pozos de a uno, pero los pozos de un mismo pad comparten tratamiento (un pad hijo los fractura juntos) y "
          "comparten shocks, así que esa permutación puede exagerar la precisión. En I5 el cluster son los pozos de una celda que "
          "comparten `pad_id` en `int_pozo_pad` (un pozo sin pad es su propio cluster). Los clusters del mismo tamaño en la misma "
          "celda son intercambiables: en cada permutación se reparten entre ellos las cantidades de tratados y, dentro de cada "
          "cluster, se sortea cuáles pozos son los tratados. Cada celda conserva su cantidad de tratados y ATT_W se recalcula con "
          "la regla de D2.", "",
          "| Cantidad | Valor | Permutaciones | Semilla | p a dos colas | Observaciones | Estratos (celda y tamaño) | Clusters | "
          "Observaciones en clusters de más de un pozo | Observaciones que se mezclan | Tratados |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
          f"| ATT_W (pp) | {_n(v5)} | {rp5} | {sem5} | {_n(p5, 4)} | {n_obs5} | {n_est5} | {ncl5} | {_n(100 * multi5, 1)}% | "
          f"{_n(100 * parte5, 1)}% | {n_t5} |", "",
          f"Bajo la permutación por pad, ATT_W tiene media {_n(media5)} pp y percentiles 2,5 y 97,5 de {_n(e1)} y {_n(e2)} pp. "
          f"Con {rp5} permutaciones el p no puede bajar de {_n(1 / (1 + rp5), 4)}"
          f"{' y es ese mínimo' if p5 <= 1 / (1 + rp5) + 1e-12 else ''}. "
          + ("La nula no está centrada en cero, a diferencia de la de I4: solo se mezcla una parte de las observaciones, así que "
             "muchas permutaciones dejan a los tratados en su lugar y conservan parte del efecto. Por eso, como I2, es una prueba "
             "débil y se lee así. " if e1 > 0 else "")
          + ("El valor observado queda por encima del percentil 97,5 de esa nula." if v5 > e2
             else "El valor observado no queda por encima del percentil 97,5 de esa nula."), "",
          "I5 se agregó después de ver las cifras de I4 (p en su mínimo, nula centrada en cero) y la observación de la revisión, y "
          f"antes de calcular ninguna cifra de I5 (regla en {COMMIT_ACLARACION_4}). No entra en la familia de Holm, como I4.", "",
          "Qué no prueba: los pads son clusters de bocas de pozo, no de laterales; un pad hijo puede alcanzar varios pads padres, que "
          "siguen correlacionados entre clusters; y la intercambiabilidad dentro de la celda es el supuesto que D2 ya hace, así que "
          "I5 no prueba las tendencias paralelas.", ""]
    k = fam[0][11]
    nrech = sum(1 for f in fam if f[10])
    L += ["## I3. Holm sobre la familia confirmatoria", "",
          f"La familia tiene k = {k} diseños. Rechazan a α = {_n(ALFA, 2)} con Holm: {nrech} de {k}. "
          "Un diseño sin muestra, sin fila o sin IC entra con p = 1: la familia no se achica. D7 y D9 se leen de la fila `dW` de "
          "su mart, que guarda sus resultados en la columna `resultado`. D11c se sumó después de la primera corrida, con las "
          "cifras de D11 ya conocidas: la regla de D11 le da veredicto propio, como a D4 y D12 sus dos filas (segunda "
          "aclaración de la regla, en `pipeline/inferencia.py`). E2 y D14 se sumaron después, cada uno con su regla fijada antes "
          "de calcular ninguna de sus cifras (`82d58c0` en `pipeline/stacked.py` y `5002094` en `pipeline/causal_exposicion.py`); "
          "sumarlos sube k y puede cambiar el p ajustado de los demás.", "",
          "| Diseño | Fuente | Estado | Veredicto del diseño | Valor | IC 95% | p | p de Holm | ¿Rechaza? |",
          "| --- | --- | --- | --- | ---: | --- | ---: | ---: | --- |"]
    for id_, fuente, estado, vd, v, b, a, n_tr, pp, ph, rech, _, pperm in fam:
        ic = f"{_n(b)} a {_n(a)}" if b is not None and not math.isnan(b) else "n/d"
        L.append(f"| {id_} | `{fuente}` | {estado} | {vd or 'n/d'} | {_n(v)} | {ic} | {_p(pp)} | {_p(ph)} | {'sí' if rech else 'no'} |")
    p1 = [f[0] for f in fam if f[8] >= 1.0 and f[2] != "leido"]
    L += ["", "Entraron con p = 1 por no tener su mart o su fila en este warehouse (el paso que los escribe no corrió antes que este) o "
              f"por no tener muestra: {', '.join(p1) if p1 else 'ninguno'}. El p de la permutación de D2 (I4: {_n(p4, 4)}; I5: {_n(p5, 4)}; I2: {_n(p, 4)}) no "
              "reemplaza al de la familia.", ""]
    # rechazar es que el valor se separa de cero con el ajuste; el veredicto de cada diseno sale de su propia regla
    contra = [f"{f[0]} («{f[3]}»)" for f in fam if f[10] and f[3] and f[3].startswith("no ")]
    nota = ("Rechazar acá solo dice que el valor se separa de cero después del ajuste por la familia; no cambia el veredicto de "
            "cada diseño, que sale de su propia regla.")
    if contra:
        nota += f" Rechaza{'n' if len(contra) > 1 else ''} y su veredicto no cambia: {', '.join(contra)}."
    if any(f[0] == "D3" and f[2] == "leido" for f in fam):
        nota += (" D3 entra con el agua por día producido (`dA_pd` de `mart_causal_profundo_d3`), el estadístico con el que decide "
                 f"su veredicto ([causal_profundo.md](causal_profundo.md)); su estado y su veredicto salen de `mart_causal_profundo_veredicto`. "
                 f"Este cambio se fijó en {COMMIT_ACLARACION_3}, después de ver el p de Holm de D3 con el volumen de agua del mes.")
    L += [nota, ""]
    L += ["### Publicado sin veredicto: los intervalos de la descomposición", "",
          f"Son {desc[0]} intervalos (una prueba por fila de `mart_descomposicion_k`, `mart_descomposicion_aditiva` y "
          f"`mart_descomposicion_distancia`; en la aditiva, el de la brecha del volumen). Sin ajuste, {desc[1]} excluyen cero. "
          f"Con Holm dentro de esa familia, con la misma aproximación normal, siguen rechazando {desc[2]}.", ""]
    L += ["La aproximación normal usa el IC 95% publicado y no un p exacto: sirve para el orden de magnitud del ajuste, no para "
          "un valor p al cuarto decimal.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    datos = preparar_datos(con)
    filas_e = escala(datos)
    _escribir(con, "mart_inferencia_escala", COLS_ESCALA, filas_e)
    obs = observaciones_d2(datos)
    r = permutacion(obs)
    q1, q2 = (float(x) for x in np.percentile(r["perm"], (2.5, 97.5)))
    r4 = permutacion_celda(obs)
    c1, c2 = (float(x) for x in np.percentile(r4["perm"], (2.5, 97.5)))
    pads = dict(con.execute("select pozo_id, pad_id from int_pozo_pad").fetchall())
    r5 = permutacion_pad(observaciones_pad(obs, datos["D"]["pozo_id"], pads))
    d1, d2 = (float(x) for x in np.percentile(r5["perm"], (2.5, 97.5)))
    _escribir(con, "mart_inferencia_permutacion", COLS_PERM,
              [(CANT_PERM_I2, r["att_obs"], R_PERM, SEMILLA_PERM, r["p"], veredicto_permutacion(r["p"]), r["n_obs"],
                r["n_estratos"], r["parte_mixtos"], r["n_tratados"], q1, q2, float(np.mean(r["perm"])), None, None),
               (CANT_PERM_CELDA, r4["att_obs"], R_PERM, SEMILLA_PERM_CELDA, r4["p"], veredicto_permutacion(r4["p"]),
                r4["n_obs"], r4["n_estratos"], r4["parte_mixtos"], r4["n_tratados"], c1, c2, float(np.mean(r4["perm"])), None, None),
               (CANT_PERM_PAD, r5["att_obs"], R_PERM, SEMILLA_PERM_PAD, r5["p"], veredicto_permutacion(r5["p"]),
                r5["n_obs"], r5["n_estratos"], r5["parte_mixtos"], r5["n_tratados"], d1, d2, float(np.mean(r5["perm"])),
                r5["n_clusters"], r5["parte_multipozo"])])
    _escribir(con, "mart_inferencia_holm", COLS_HOLM, familia_holm(con, r["p"]) + descomposicion_holm(con))
    PAGINA.write_text(pagina(con), encoding="utf-8")
    for d in ("D1", "D2"):
        print(f"I1 {d}: {next(f[9] for f in filas_e if f[0] == d)}")
    print(f"I4: ATT_W = {r4['att_obs']:+.2f} pp, p = {r4['p']:.4f}, {veredicto_permutacion(r4['p'])}, nula {c1:+.2f} a {c2:+.2f} "
          f"(media {np.mean(r4['perm']):+.2f}), observaciones que se mezclan {100 * r4['parte_mixtos']:.1f}%")
    print(f"I5: ATT_W = {r5['att_obs']:+.2f} pp, p = {r5['p']:.4f}, {veredicto_permutacion(r5['p'])}, nula {d1:+.2f} a {d2:+.2f} "
          f"(media {np.mean(r5['perm']):+.2f}), clusters {r5['n_clusters']}, en clusters de mas de un pozo "
          f"{100 * r5['parte_multipozo']:.1f}%, se mezcla {100 * r5['parte_mixtos']:.1f}%")
    print(f"I2: ATT_W = {r['att_obs']:+.2f} pp, p = {r['p']:.4f}, {veredicto_permutacion(r['p'])}, "
          f"observaciones en estratos mixtos {100 * r['parte_mixtos']:.1f}%")
    h = con.execute("select count(*), sum(rechaza::int), sum((estado <> 'leido')::int) from mart_inferencia_holm "
                    "where familia = 'confirmatoria'").fetchone()
    d = con.execute("select count(*), sum(excluye_cero::int), sum(rechaza::int) from mart_inferencia_holm "
                    "where familia = 'descomposicion'").fetchone()
    print(f"I3: k = {h[0]}, rechazan {h[1]}, con p = 1: {h[2]}; descomposición {d[0]}: {d[1]} excluyen cero sin ajuste, {d[2]} con Holm")
    con.close()


if __name__ == "__main__":
    main()
