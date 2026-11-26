"""Exposicion: golpes repetidos (D10), exposicion por rama y anillos de derrame (D11), operador por area (D12).

Se corre despues de pipeline.causal_profundo:  uv run python -m pipeline.causal_exposicion

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porciones G, H y J de docs/plan-siguiente-nivel.md). Este commit trae solo la
regla, las constantes y los veredictos; no se calculo ninguna cifra de D10, D11 ni D12. Si algo resulta ambiguo al
construirlo, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian D2 (13,8 con 447 tratados), D4 (la banda de 1 a 2 km sube 7,2), D5 (142 de 341
tratados reciben otro golpe a menos de 2 km en los meses 2 a 12; no se conocia la cuenta a 1 km) y D6 (sin YPF da 7,1).

Todo reutiliza pipeline.causal y pipeline.causal_profundo sin tocarlos: universo, golpes, cohortes, celdas, W, dW, bloques,
sorteos (los W de D3 extendidos con extender_pesos, como D4 y D5), causal.rompe y causal._ic.

D10. Golpes repetidos (porcion G): D5 censurado en el segundo golpe.
  * Serie de D5 (E_D5, H = H_D5, sus celdas y su dW por mes; tambien dO(e)), con una sola diferencia: un tratado con un golpe
    a menos de KM_TRATADO (la distancia que define el primero) en un mes g + s, s >= S_CENSURA, sale de la serie desde
    e = s (sus meses e >= s quedan como faltantes). Los controles ya no tienen golpe a KM_LIMPIO hasta g + H_D5.
    El mes g + 1 no censura: un pad que se fractura entre dos meses es el mismo evento (como en "otro golpe" de D5).
  * Publicado sin veredicto: la misma serie censurada a KM_LIMPIO (2 km, la cuenta de D5) y cuantos tratados quedan en cada e.
  * Veredicto: veredicto_forma de D5 sobre la serie censurada a 1 km (media de dW en TRAMO_TARDE, n = el menor n de
    tratados con dW en esos meses, MIN_TRATADOS_D5, FRACCION_CURA, media temprana de los meses 0 y 1 de la misma serie).
  * Lo que no dice: la censura no es al azar (los padres de zonas de relleno reciben mas hijos); la serie censurada mide la
    primera fractura sola en los padres que no recibieron otra, no en todos.

D11. Exposicion por rama y anillos de derrame (porcion H).
  * Distancia entre ramas: `m_min` de mart_trayectoria_par (la distancia minima entre las dos ramas medidas, en m) para el
    par (hijo, padre). Bandas: las de RAMA en pipeline.trayectorias (menos de 250 m, 250 m a 1 km, 1 km o mas).
  * Submuestra: tratados de D2 con g en ANIOS_RAMA y con al menos un hijo de su mes g a menos de KM_TRATADO cuyo par con el
    padre tiene `m_min`; la distancia del tratado es la menor `m_min` de esos pares. Se publica la cobertura: tratados de D2
    en ANIOS_RAMA y cuantos tienen distancia.
  * D11a, dosis por rama: dW de D2 (k = 0) en cada banda de rama, con las celdas de D2 filtradas a los tratados de la banda
    (celdas_por_mascara, controles iguales). Diferencia "menos de 250 m" menos "250 m o mas" (las dos ultimas bandas
    juntas), sorteo por sorteo. Veredicto (`veredicto_rama`): "sin muestra" si alguna de las dos tiene menos de
    MIN_TRATADOS_BANDA; "gradiente por rama" si el IC bajo de la diferencia es mayor que cero; "sin gradiente por rama" si
    el IC de la diferencia incluye cero, el dW de la banda cercana es positivo y el IC alto de la diferencia es menor que
    FRACCION_RAMA de ese dW; "no firme" en otro caso.
  * D11b, controles limpios por rama: D2 en la submuestra, sacando de cada celda los controles con un par medido de
    `m_min` menor que RAMA_LIMPIA_M con un hijo fracturado en [g - VENTANA_PREVIA, g + H_CORTO] y los controles sin rama
    medida. Se publica junto al D2 de la misma submuestra con todos sus controles, y la diferencia con IC. Sin veredicto.
  * D11c, anillos (Butts, 2021): cohortes por anillo de la distancia de boca del golpe mas cercano del mes g, ANILLOS_KM
    (el de 1 a 2 km es la cohorte de D4, causal_profundo._cohorte_1_2_km); para los anillos de 2 km o mas: primer mes con
    km_min en el anillo, ningun golpe mas cerca que el borde interno en [g - VENTANA_PREVIA, g + H_CORTO], edad, base y
    ventana previa como causal._condiciones. Controles de todos los anillos: los de causal.celdas con H_CORTO y ademas sin
    golpe a menos de KM_ANILLO_LIMPIO (km_min) en [g - VENTANA_PREVIA, g + H_CORTO]. Resultados: dW de D2 e I(1) de D1.
    Tambien D2 (anillo de 0 a 1 km, los tratados de D2) con estos controles limpios a 5 km.
    Veredicto (`veredicto_anillos`) sobre dW: "sin muestra" si el anillo de 2 a 3 km tiene menos de MIN_TRATADOS_BANDA;
    "derrame hasta R km" con R el borde externo del anillo mas lejano con IC bajo de dW mayor que cero, si ese anillo
    empieza en KM_LIMPIO o mas (los controles de D1 y D2, limpios solo a 2 km, pueden estar contaminados); "controles
    limpios" si ningun anillo de 2 km o mas tiene IC bajo mayor que cero; mismo criterio sobre I(1) con IC alto menor que
    cero, publicado sin veredicto.
  * Lo que no dice: `m_min` es la geometria declarada de la rama, no la red de fracturas; la submuestra con rama es sobre
    todo de 2016 a 2023.

D12. Operador por area (porcion J): ¿YPF o composicion?
  * Celdas (g, grupo de edad, operador del padre, area del padre): las celdas de D2 partidas, con los controles de cada una
    restringidos al mismo operador y la misma area (dim_pozo.area por pozo_id; "Sin dato" es un area mas, como en D6). La
    celda entra con MIN_CONTROLES_CELDA controles con dato. dW de D2 (k = 0), mismos sorteos.
  * D12a: todos los tratados. D12b: sin los tratados ni controles de YPF (operador del padre igual a OPERADOR_YPF).
    D12c: solo YPF. Se publica tambien cuantos tratados de D2 conserva cada una.
  * Veredicto (`veredicto_operador_area`) sobre D12a: "sin muestra" con menos de MIN_TRATADOS tratados con dW en celdas con
    control; "sostiene dentro de operador y area" si el IC bajo es mayor que UMBRAL_AGUA_PP; "puede ser composicion" si el
    IC incluye cero; "no firme" en otro caso. Sobre D12b (S5 entre operadores): "se repite fuera de YPF" si tiene
    MIN_TRATADOS_OPERADOR o mas tratados y su IC bajo es mayor que cero; "no se repite fuera de YPF" si su IC incluye cero;
    "sin muestra" con menos tratados; "no firme" en otro caso.

Marts mart_causal_exposicion_d10, _d11, _d12 y _veredicto (cada uno con su llamada a _escribir con el nombre literal) y
una seccion por diseno en wiki/hallazgos/causal_profundo.md o una pagina propia, con su regla citada por el SHA de este commit.
REGLA D14 FIJADA ANTES DE CALCULAR (2026-11-26, ronda 2, S2 del revisor: "la distancia entre ramas como exposicion primaria en
2016-2023"). Este commit trae solo la regla y las constantes; no se calculo ninguna cuenta ni efecto de D14. Lo que se conocia:
D2 (13,8 con 447 tratados), la cobertura de D11a (279 de 312 tratados de D2 de 2016 a 2023 con distancia de rama, y su
"sin muestra"), y las cifras publicadas de D11b en wiki/hallazgos/exposicion.md (seccion D11). Ninguna cuenta de tratados ni
de controles de D14, ningun efecto y ningun p se vieron antes de este commit.

D14. D2 con el golpe definido por la distancia entre ramas.
  * Universo, celdas (g, grupo de edad, y lo demas que usen las celdas de D2), resultado (W, dW con k = 0), bloques de
    bootstrap y sorteos: los de D2, restringidos a g en ANIOS_RAMA (2016 a 2023). Eleccion: el filtro de g se aplica DESPUES de
    construir las celdas de D2 y de sus minimos (MIN_CONTROLES_CELDA), es decir, una celda de D2 de esos anios entra o sale
    igual que en D2; solo se descartan las celdas de otros anios. Asi D14 y la fila de comparacion usan las mismas celdas.
  * Tratado: un padre con golpe de rama en el mes g: un hijo fracturado en g con un par (hijo, padre) en mart_trayectoria_par
    con `m_min` menor que RAMA_TRATADO_M (250 m, la banda mas cercana de RAMA en pipeline.trayectorias). Cuenta sin importar la
    distancia de boca (hasta los 5 km que cubre el mart). Ademas: todas las condiciones de D2 sobre el padre (edad, base valida,
    etc.) y ventana previa limpia en los dos sentidos de D2: ningun par de rama a menos de RAMA_TRATADO_M ni golpe de boca a
    menos de KM_TRATADO con un hijo fracturado en [g - VENTANA_PREVIA, g - 1]. Eleccion: un padre con golpe de rama en g y un
    golpe de boca previo en la ventana queda fuera de los tratados (la ventana previa limpia manda) y no es control; un padre
    con un golpe de rama en g y tambien un golpe de boca en g es tratado (los dos golpes ocurren en el mes de la cohorte).
  * Controles: padres de las mismas celdas sin NINGUNO de estos en [g - VENTANA_PREVIA, g + H_CORTO]: un par medido con `m_min`
    menor que RAMA_CONTROL_M (1000 m, donde empieza la banda lejana); un hijo a distancia de boca menor que KM_LIMPIO cuyo par
    con el padre no tiene `m_min` medido (exposicion desconocida). Los controles de D2 que cumplen esto son los de D14.
  * Estimador: ATT_W de D2 con la regla de celdas de D2 (MIN_CONTROLES_CELDA) y el IC de D2 (bootstrap por bloques, los mismos
    sorteos).
  * Veredicto (`veredicto_d14`): usa la logica de veredicto_d2 de pipeline.causal: "sin muestra" con menos de MIN_TRATADOS (300)
    tratados con dW en celdas con control; "sostiene: la rama como golpe" si el IC bajo de ATT_W es mayor que UMBRAL_AGUA_PP;
    "no firme" en otro caso. Eleccion: los pasos de placebo y de cierre de veredicto_d2 NO se recalculan para D14 (no se
    construyen placebos con la definicion de rama), y el veredicto lo dice en su texto; "sin muestra" aqui significa menos de
    300 tratados de rama, no falta de cobertura de rama.
  * Publicado sin veredicto, al lado: D2 restringido a g en ANIOS_RAMA (golpe de boca a KM_TRATADO), con las mismas celdas,
    los mismos controles de D2 (los suyos, no los de D14) y los mismos sorteos, para ver si la definicion por rama mueve la
    estimacion. Tambien: cuantos tratados de D14 no son tratados de D2 (rama cerca, boca de 1 a 5 km) y cuantos tratados de D2
    de esos anios no son tratados de D14.
  * Holm: D14 entra en FAMILIA_CONFIRMATORIA de pipeline.inferencia con la fila `diseno` = "D14" de su mart. Esto se fija antes
    de calcular y puede cambiar el p ajustado por Holm de los otros disenos (k sube en uno).
  * Lo que no dice: `m_min` es la distancia entre ramas medidas, no la geometria de la fractura; un hijo sin rama medida puede
    estar cerca igual (queda fuera de los controles, pero no de los otros golpes de un padre tratado); la ventana es solo 2016 a
    2023.

Mart mart_causal_d14 (nombre literal en _escribir, con columna `diseno`) y una seccion D14 en wiki/hallazgos/exposicion.md
(su generador en este modulo), con la regla citada por el SHA de este commit.
ACLARACION D14 (2026-11-26, escrita antes de calcular cualquier cifra de D14; aprobada la regla con tres correcciones del lead).
  1. Celdas. D14 arma SUS PROPIAS celdas con la regla de D2: las mismas claves de celda (g, grupo de edad), MIN_CONTROLES_CELDA y
     los mismos minimos, aplicados a los tratados de D14 y a los controles de D14, y se quedan solo las g en ANIOS_RAMA. No
     reutiliza el conjunto de celdas de D2 (las que tienen tratados de D2). Esto es lo que ya queria decir la eleccion 2 de la
     regla; donde decia "las celdas de D2" se lee "la regla de celdas de D2". La fila de comparacion (D2 en 2016-2023) usa las
     celdas de D2 filtradas a esos anios.
  2. Etiqueta del veredicto. D14 reutiliza la identificacion de D2 y no repite los placebos de D2, asi que no dice "sostiene"
     como un diseno propio: V_D14_SOSTIENE = "la suba se ve también con el golpe por rama". Se mantienen "sin muestra" (menos
     de MIN_TRATADOS tratados con dW en celdas con control) y "no firme". La pagina dice en una frase que D14 cambia solo la
     definicion del golpe y que sus placebos son los de D2, no repetidos.
  3. Condiciones del padre. Las de D2 se aplican tal cual (causal._condiciones): edad desde EDAD_MIN, base valida y la ventana
     previa limpia propia de D2, que cuenta golpes a menos de KM_LIMPIO (2 km, no KM_TRATADO) en [g - VENTANA_PREVIA, g - 1].
     Sobre eso se agrega la ventana previa lateral: ningun par (hijo, padre) con m_min menor que RAMA_TRATADO_M con un hijo
     fracturado en [g - VENTANA_PREVIA, g - 1]. Ventanas que quedan aplicando a un tratado de D14: (a) boca a KM_LIMPIO en
     [g - VENTANA_PREVIA, g - 1] (la de D2, que ya incluye lo que decia la regla con KM_TRATADO); (b) rama a menos de
     RAMA_TRATADO_M en [g - VENTANA_PREVIA, g - 1]. Controles: las condiciones de D2 (causal.controles, incluida la ventana a
     KM_LIMPIO en [g - VENTANA_PREVIA, g + H_CORTO] y su primer golpe a KM_TRATADO despues de g + H_CORTO) mas las dos condiciones
     de rama de la regla, que son las de [g - VENTANA_PREVIA, g + H_CORTO] con m_min menor que RAMA_CONTROL_M y con hijo cercano
     sin m_min medido.
"""
from __future__ import annotations

from pipeline.causal import (H_CORTO, KM_LIMPIO, KM_TRATADO, MIN_CONTROLES_CELDA, MIN_TRATADOS, MIN_TRATADOS_OPERADOR,
                             UMBRAL_AGUA_PP, V_NO_FIRME, V_SIN_MUESTRA, VENTANA_PREVIA)
from pipeline.causal_profundo import E_D5, FRACCION_CURA, H_D5, MIN_TRATADOS_BANDA, MIN_TRATADOS_D5, TRAMO_TARDE

# heredado sin cambio
REGLA_HEREDADA = {"KM_TRATADO": KM_TRATADO, "KM_LIMPIO": KM_LIMPIO, "VENTANA_PREVIA": VENTANA_PREVIA,
                  "H_CORTO": H_CORTO, "MIN_CONTROLES_CELDA": MIN_CONTROLES_CELDA, "MIN_TRATADOS": MIN_TRATADOS,
                  "MIN_TRATADOS_OPERADOR": MIN_TRATADOS_OPERADOR, "UMBRAL_AGUA_PP": UMBRAL_AGUA_PP, "E_D5": E_D5,
                  "H_D5": H_D5, "TRAMO_TARDE": TRAMO_TARDE, "MIN_TRATADOS_D5": MIN_TRATADOS_D5,
                  "FRACCION_CURA": FRACCION_CURA, "MIN_TRATADOS_BANDA": MIN_TRATADOS_BANDA}

# ---- regla fijada (no cambiar despues de ver cifras) ----
# D10
KM_CENSURA = KM_TRATADO               # el segundo golpe a la distancia que define el primero
KM_CENSURA_SECUNDARIA = KM_LIMPIO     # publicado sin veredicto
S_CENSURA = 2                         # el mes g + 1 no censura

# D11
ANIOS_RAMA = (2016, 2023)             # inclusive; las ramas cubren de 76 a 97% de los hijos de esos anios
BANDAS_RAMA_M = ((0.0, 250.0), (250.0, 1000.0), (1000.0, None))   # las de RAMA en pipeline.trayectorias, en m
RAMA_LIMPIA_M = 250.0
FRACCION_RAMA = 0.5
ANILLOS_KM = ((1.0, 2.0), (2.0, 3.0), (3.0, 5.0))
KM_ANILLO_LIMPIO = 5.0

# D14
RAMA_TRATADO_M = 250.0                # tratado: par con m_min menor que esto (la banda mas cercana de RAMA)
RAMA_CONTROL_M = 1000.0               # control: ningun par medido con m_min menor que esto (empieza la banda lejana)

# D12
OPERADOR_YPF = "YPF"                  # se compara con el operador del padre en mayusculas y sin espacios al borde; si el
                                      # dato lo escribe distinto (p. ej. "YPF S.A."), el commit de construccion fija el
                                      # texto exacto y lo dice, sin mirar ninguna cifra de D12

V_D10_PERSISTE = "persiste"           # los de veredicto_forma de D5, sobre la serie censurada
V_RAMA_GRADIENTE = "gradiente por rama"
V_RAMA_SIN_GRADIENTE = "sin gradiente por rama"
V_ANILLOS_LIMPIOS = "controles limpios"
V_ANILLOS_DERRAME = "derrame hasta {r:g} km"
V_D12_SOSTIENE = "sostiene dentro de operador y área"
V_D12_COMPOSICION = "puede ser composición"
V_D12_FUERA_REPITE = "se repite fuera de YPF"
V_D12_FUERA_NO = "no se repite fuera de YPF"
V_D14_SOSTIENE = "la suba se ve también con el golpe por rama"


def veredicto_rama(n_cerca: int, n_lejos: int, dif_bajo: float, dif_alto: float, dw_cerca: float) -> str:
    if min(n_cerca, n_lejos) < MIN_TRATADOS_BANDA:
        return V_SIN_MUESTRA
    if dif_bajo > 0:
        return V_RAMA_GRADIENTE
    if dif_bajo <= 0 <= dif_alto and dw_cerca > 0 and dif_alto < FRACCION_RAMA * dw_cerca:
        return V_RAMA_SIN_GRADIENTE
    return V_NO_FIRME


def veredicto_d14(n_tratados: int, bajo: float) -> str:
    """Los pasos de veredicto_d2 sin placebos ni cierre (no se recalculan para D14)."""
    if n_tratados < MIN_TRATADOS:
        return V_SIN_MUESTRA
    if bajo > UMBRAL_AGUA_PP:
        return V_D14_SOSTIENE
    return V_NO_FIRME


def veredicto_anillos(n_por_anillo: dict[tuple[float, float], int], bajos: dict[tuple[float, float], float]) -> str:
    """bajos: IC bajo de dW por anillo (los de ANILLOS_KM)."""
    if n_por_anillo.get((2.0, 3.0), 0) < MIN_TRATADOS_BANDA:
        return V_SIN_MUESTRA
    lejos = [a for a in ANILLOS_KM if a[0] >= KM_LIMPIO and n_por_anillo.get(a, 0) >= MIN_TRATADOS_BANDA
             and bajos.get(a, float("-inf")) > 0]
    if lejos:
        return V_ANILLOS_DERRAME.format(r=max(a[1] for a in lejos))
    return V_ANILLOS_LIMPIOS


def veredicto_operador_area(n_tratados: int, bajo: float, alto: float) -> str:
    if n_tratados < MIN_TRATADOS:
        return V_SIN_MUESTRA
    if bajo > UMBRAL_AGUA_PP:
        return V_D12_SOSTIENE
    if bajo <= 0 <= alto:
        return V_D12_COMPOSICION
    return V_NO_FIRME


def veredicto_fuera_de_ypf(n_tratados: int, bajo: float, alto: float) -> str:
    if n_tratados < MIN_TRATADOS_OPERADOR:
        return V_SIN_MUESTRA
    if bajo > 0:
        return V_D12_FUERA_REPITE
    if bajo <= 0 <= alto:
        return V_D12_FUERA_NO
    return V_NO_FIRME


# ================================================================== construccion (D12)
# Todo lo que sigue aplica la regla de arriba. No cambia ninguna constante ni ningun veredicto.

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

import duckdb  # noqa: E402
import numpy as np  # noqa: E402

from pipeline.causal import (MIN_MESES_W_BASE, REPS, SEMILLA_CAUSAL, SQL_GOLPES, _bases, _cohorte_falsa_distancia,  # noqa: E402
                             _cohorte_falsa_fecha, _cohorte_nunca_tratados, _condiciones, _panel_promedio, _pesos_bloques,
                             _preparar, _primera, _valores_agua, bootstrap, cargar, celdas, celdas_d1b, cohortes)
from pipeline.causal_profundo import (_cohorte_1_2_km, _dif, cargar_volumenes, celdas_por_mascara,  # noqa: E402
                                      estimar_valores, extender_pesos, media_resultados, preparar_bases, valores_dw_mes,
                                      valores_volumen, veredicto_forma)
from pipeline.costo import _escribir  # noqa: E402
from pipeline.ingest import DATA  # noqa: E402

COLS_D12 = [("resultado", "varchar"), ("est", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
            ("n_tratados", "integer"), ("n_celdas", "integer"), ("parte_de_d2", "double")]
COLS_VEREDICTO = [("diseno", "varchar"), ("veredicto", "varchar"), ("valor", "double"), ("ic_bajo", "double"),
                  ("ic_alto", "double"), ("n_tratados", "integer"), ("motivo", "varchar")]
COLS_D10 = [("serie", "varchar"), ("e", "integer"), ("resultado", "varchar"), ("n_tratados", "integer"),
            ("n_controles", "integer"), ("est", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_D11 = [("parte", "varchar"), ("banda", "varchar"), ("resultado", "varchar"), ("n_tratados", "integer"),
            ("n_controles", "integer"), ("est", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_D14 = COLS_VEREDICTO + [("n_controles", "integer"), ("n_celdas", "integer")]
SHA_REGLA_D14 = "5002094"        # la regla de D14
SHA_ACLARACION_D14 = "f1b1e08"   # su aclaracion, tambien antes de calcular
SIN_CENSURA = 10 ** 6   # mes de censura de un tratado que no recibe otro golpe
PAGINA = Path("wiki/hallazgos/exposicion.md")
SHA_REGLA = "857d434"
TOLERANCIA_CONTROL = 1e-9
TOLERANCIA_CONTROL_IC = 1e-6   # los extremos del IC son percentiles de los sorteos: los compara como causal_profundo.main


def preparar(con) -> tuple[dict, list[dict], np.ndarray, np.ndarray, dict]:
    """D, las celdas de D2, los sorteos W, el universo de pozos y las cohortes: los mismos que el main de
    pipeline.causal_profundo (D6 los usa igual)."""
    D = cargar(con)
    coh = cohortes(D)
    rng = np.random.default_rng(SEMILLA_CAUSAL)
    cel_pri = celdas(D, coh, H_CORTO, False)
    cel_s1 = celdas(D, coh, H_CORTO, True)
    trat_ff, g_ff = _cohorte_falsa_fecha(D, coh)
    cel_ff = celdas(D, coh, H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = _cohorte_falsa_distancia(D, coh, H_CORTO)
    cel_fd = celdas(D, coh, H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = _cohorte_nunca_tratados(D, coh)
    cel_nt = celdas(D, coh, H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    cel_d1b = celdas_d1b(D, coh)
    universo = [cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b]
    wells = []
    for grupo in universo:
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = _pesos_bloques(D, wells, REPS, rng)
    return D, cel_pri, W, wells, coh


def areas_por_pozo(con, D: dict) -> np.ndarray:
    """Area de cada pozo de D (dim_pozo.area; 'Sin dato' es un area mas, como en D6)."""
    area_de = {int(p): a for p, a in con.execute(
        "select pozo_id, coalesce(nullif(trim(area), ''), 'Sin dato') from dim_pozo").fetchall()}
    return np.array([area_de.get(int(p), "Sin dato") for p in D["pozo_id"]], dtype=object)


def _recortar(ce: dict, t_sel: np.ndarray, c_sel: np.ndarray) -> dict:
    """Celda con los tratados y controles elegidos (por mascara); si trae base_t o base_c los recorta igual."""
    out = {**ce, "tratados": ce["tratados"][t_sel], "controles": ce["controles"][c_sel]}
    for clave, m in (("base_t", t_sel), ("base_c", c_sel)):
        if clave in ce:
            out[clave] = ce[clave][m]
    return out


def celdas_operador_area(D: dict, cel: list[dict], area: np.ndarray, quitar: str | None = None,
                         solo: str | None = None) -> list[dict]:
    """Las celdas de D2 partidas por (operador, area) del padre, con controles del mismo operador y la misma area."""
    op = np.asarray(D["operador"]).astype(str)
    op_cmp = np.char.upper(np.char.strip(op))   # la regla compara con OPERADOR_YPF en mayusculas y sin espacios al borde
    area = np.asarray(area, dtype=object)
    out = []
    for ce in cel:
        mt = np.ones(len(ce["tratados"]), dtype=bool)
        mc = np.ones(len(ce["controles"]), dtype=bool)
        if quitar is not None:
            mt &= op_cmp[ce["tratados"]] != quitar.strip().upper()
            mc &= op_cmp[ce["controles"]] != quitar.strip().upper()
        if solo is not None:
            mt &= op_cmp[ce["tratados"]] == solo.strip().upper()
            mc &= op_cmp[ce["controles"]] == solo.strip().upper()
        t_op, t_ar = op[ce["tratados"]], area[ce["tratados"]]
        c_op, c_ar = op[ce["controles"]], area[ce["controles"]]
        pares = sorted({(str(o), str(a)) for o, a, ok in zip(t_op, t_ar, mt) if ok})
        for o, a in pares:
            t_sel = mt & (t_op == o) & (t_ar == a)
            c_sel = mc & (c_op == o) & (c_ar == a)
            if not t_sel.any():
                continue
            out.append(_recortar(ce, t_sel, c_sel))
    return out


def _estimar(D: dict, cel: list[dict], W: np.ndarray) -> dict:
    vt, vc = _valores_agua(D, cel, 0)
    return {**estimar_valores(D, cel, W, vt, vc), "n_celdas": _preparar(cel, vt, vc)["n_celdas"]}


def _fila(nombre: str, rr: dict, n_d2: int, n_celdas: int) -> tuple:
    return (nombre, float(rr["est"]), float(rr["ic_bajo"]), float(rr["ic_alto"]), int(rr["n_tratados"]), int(n_celdas),
            float(rr["n_tratados"]) / n_d2 if n_d2 else None)


def calcular(con, prep: tuple | None = None) -> tuple[list[tuple], list[tuple]]:
    """D12a, D12b y D12c con sus veredictos; antes comprueba que el D2 recalculado sea el de D6."""
    D, cel_pri, W, _wells, _coh = prep if prep is not None else preparar(con)
    rr = _estimar(D, cel_pri, W)
    d6 = con.execute("select valor, ic_bajo, ic_alto from mart_causal_profundo_d6 where corte = 'todos'").fetchone()
    print(f"control D2: recalculado {rr['est']:.6f} ({rr['ic_bajo']:.6f} a {rr['ic_alto']:.6f}) con {rr['n_tratados']} "
          f"tratados; D6 'todos' {float(d6[0]):.6f} ({float(d6[1]):.6f} a {float(d6[2]):.6f})")
    if (abs(float(rr["est"]) - float(d6[0])) > TOLERANCIA_CONTROL
            or abs(float(rr["ic_bajo"]) - float(d6[1])) > TOLERANCIA_CONTROL_IC
            or abs(float(rr["ic_alto"]) - float(d6[2])) > TOLERANCIA_CONTROL_IC):
        raise RuntimeError("el D2 recalculado no coincide con mart_causal_profundo_d6: los sorteos o las celdas cambiaron")
    area = areas_por_pozo(con, D)
    casos = (("D12a", {}), ("D12b", {"quitar": OPERADOR_YPF}), ("D12c", {"solo": OPERADOR_YPF}))
    filas, res = [], {}
    for nombre, kw in casos:
        cel = celdas_operador_area(D, cel_pri, area, **kw)
        r = _estimar(D, cel, W)
        res[nombre] = r
        filas.append(_fila(nombre, r, int(rr["n_tratados"]), r["n_celdas"]))
        print(f"{nombre}: dW = {r['est']:+.2f} (IC {r['ic_bajo']:+.2f} a {r['ic_alto']:+.2f}), tratados {r['n_tratados']} "
              f"({filas[-1][6]:.1%} de D2), celdas {filas[-1][5]}")
    va = veredicto_operador_area(int(res["D12a"]["n_tratados"]), float(res["D12a"]["ic_bajo"]), float(res["D12a"]["ic_alto"]))
    vb = veredicto_fuera_de_ypf(int(res["D12b"]["n_tratados"]), float(res["D12b"]["ic_bajo"]), float(res["D12b"]["ic_alto"]))
    filas_v = []
    for nombre, v in (("D12a", va), ("D12b", vb)):
        r = res[nombre]
        filas_v.append((nombre, v, float(r["est"]), float(r["ic_bajo"]), float(r["ic_alto"]), int(r["n_tratados"]),
                        f"dW {r['est']:+.2f} (IC {r['ic_bajo']:+.2f} a {r['ic_alto']:+.2f}), {r['n_tratados']} tratados"))
        print(f"{nombre}: veredicto {v}")
    return filas, filas_v


# ---- D10: D5 censurado en el segundo golpe

def mes_censura(D: dict, ce: dict, km: float | None) -> np.ndarray:
    """Mes s (relativo a g) desde el que sale de la serie cada tratado de la celda: el primero con S_CENSURA <= s <= H_D5
    y un golpe a menos de `km` km (km_min < km). SIN_CENSURA si no tiene ninguno; con km None nadie se censura."""
    n = len(ce["tratados"])
    out = np.full(n, SIN_CENSURA, dtype=np.int64)
    if km is None or not n:
        return out
    meses = np.arange(S_CENSURA, H_D5 + 1)
    cols = ce["g"] + meses - D["t0"]
    dentro = (cols >= 0) & (cols < D["T"])
    if not dentro.any():
        return out
    golpe = D["km_min"][np.ix_(ce["tratados"], cols[dentro])] < km     # nan < km es False: sin golpe
    tiene = golpe.any(axis=1)
    out[tiene] = meses[dentro][np.argmax(golpe, axis=1)][tiene]
    return out


def censurar(valores: list[np.ndarray], censura: list[np.ndarray], e: int) -> list[np.ndarray]:
    """Valores de los tratados de cada celda con nan donde el tratado ya salio de la serie (e >= su mes de censura)."""
    return [np.where(s > e, v, np.nan) for v, s in zip(valores, censura)]


def serie_censurada(D: dict, cel: list[dict], W: np.ndarray, bases: dict, km: float | None) -> tuple[dict, int]:
    """dW y dO por mes e de D5 con los tratados censurados a `km`; devuelve {e: {'dW': rr, 'dO': rr}} y los censurados."""
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    censura = [mes_censura(D, ce, km) for ce in cel]
    res = {}
    for e in E_D5:
        vt, vc = valores_dw_mes(D, cel, e, base_w)
        vt_o, vc_o = valores_volumen(D, cel, D["O"], bases["O"], (e, e))
        res[e] = {"dW": estimar_valores(D, cel, W, censurar(vt, censura, e), vc),
                  "dO": estimar_valores(D, cel, W, censurar(vt_o, censura, e), vc_o)}
    return res, int(sum(int(np.sum(s <= H_D5)) for s in censura))


def _filas_serie(nombre: str, res: dict) -> list[tuple]:
    return [(nombre, int(e), r, int(rr["n_tratados"]), int(rr["n_controles"]), float(rr["est"]), float(rr["ic_bajo"]),
             float(rr["ic_alto"])) for e in E_D5 for r, rr in res[e].items()]


def _tarde_temprano(res: dict) -> tuple[dict, float]:
    tarde = media_resultados([res[e]["dW"] for e in range(TRAMO_TARDE[0], TRAMO_TARDE[1] + 1)])
    return tarde, float(np.mean([res[0]["dW"]["est"], res[1]["dW"]["est"]]))


def calcular_d10(con, prep: tuple) -> tuple[list[tuple], tuple]:
    """D10: la serie de D5 sin censura (control contra mart_causal_profundo_d5), censurada a 1 km y a 2 km."""
    D, _cel_pri, W, wells, coh = prep
    D.update(cargar_volumenes(con, D))
    bases = preparar_bases(D)
    W5, fuera5 = extender_pesos(D, W, wells)
    cel_bruto = celdas(D, coh, H_D5, False)
    cel5 = celdas_por_mascara(cel_bruto, lambda ce: np.ones(len(ce["tratados"]), dtype=bool), fuera5)
    n_trat = int(sum(len(ce["tratados"]) for ce in cel5))

    sin, _ = serie_censurada(D, cel5, W5, bases, None)
    d5 = {(int(e), r): (float(v), float(b), float(a)) for e, r, v, b, a in con.execute(
        "select e, resultado, valor, ic_bajo, ic_alto from mart_causal_profundo_d5 where e is not null "
        "and resultado in ('dW', 'dO')").fetchall()}
    dif = max(abs(float(sin[e][r]["est"]) - d5[(e, r)][0]) for e in E_D5 for r in ("dW", "dO"))
    # los extremos del IC son percentiles de los sorteos: comprueban que W5 es el de D5 (revision del PR #186)
    dif_ic = max(abs(float(sin[e][r][k]) - d5[(e, r)][j]) for e in E_D5 for r in ("dW", "dO")
                 for j, k in ((1, "ic_bajo"), (2, "ic_alto")))
    print(f"control D10 sin censura: {2 * len(E_D5)} estimaciones (dW y dO, e {E_D5[0]} a {E_D5[-1]}) contra "
          f"mart_causal_profundo_d5; diferencia maxima {dif:.3e} en el valor y {dif_ic:.3e} en el IC")
    if dif > TOLERANCIA_CONTROL or dif_ic > TOLERANCIA_CONTROL_IC:
        raise RuntimeError(f"la serie D10 sin censura no coincide con mart_causal_profundo_d5: diferencia maxima {dif:.3e} "
                           f"en el valor y {dif_ic:.3e} en el IC")

    filas, series, cuentas = [], {}, {}
    for nombre, km in (("1km", KM_CENSURA), ("2km", KM_CENSURA_SECUNDARIA)):
        res, k = serie_censurada(D, cel5, W5, bases, km)
        series[nombre], cuentas[nombre] = res, k
        tarde, temprano = _tarde_temprano(res)
        filas += _filas_serie(nombre, res)
        filas += [(nombre, None, "dW_tarde", tarde["n_tratados"], None, tarde["est"], tarde["ic_bajo"], tarde["ic_alto"]),
                  (nombre, None, "dW_temprano", None, None, temprano, None, None),
                  (nombre, None, "censurados_12", k, n_trat, k / max(n_trat, 1), None, None)]
        print(f"D10 {nombre}: media de dW en {TRAMO_TARDE[0]} a {TRAMO_TARDE[1]} = {tarde['est']:+.2f} "
              f"(IC {tarde['ic_bajo']:+.2f} a {tarde['ic_alto']:+.2f}), n {tarde['n_tratados']}; temprano {temprano:+.2f}; "
              f"censurados {k} de {n_trat}")
        for e in E_D5:
            r = res[e]["dW"]
            print(f"  e={e:+d}: dW {r['est']:+.2f} (IC {r['ic_bajo']:+.2f} a {r['ic_alto']:+.2f}), tratados {r['n_tratados']}")
    tarde, temprano = _tarde_temprano(series["1km"])
    tarde_2, _ = _tarde_temprano(series["2km"])
    tarde_sin, _ = _tarde_temprano(sin)
    v = veredicto_forma(tarde["n_tratados"], tarde["ic_bajo"], tarde["ic_alto"], temprano)
    motivo = (f"media de dW en {TRAMO_TARDE[0]} a {TRAMO_TARDE[1]} meses, serie censurada a {KM_CENSURA:g} km, "
              f"{tarde['est']:+.2f} (IC {tarde['ic_bajo']:+.2f} a {tarde['ic_alto']:+.2f}); dW de 0 y 1 {temprano:+.2f}; "
              f"censurados {cuentas['1km']} de {n_trat}; a {KM_CENSURA_SECUNDARIA:g} km {tarde_2['est']:+.2f} "
              f"(IC {tarde_2['ic_bajo']:+.2f} a {tarde_2['ic_alto']:+.2f}), censurados {cuentas['2km']}; "
              f"D5 sin censura {tarde_sin['est']:+.2f}")
    print(f"D10: veredicto {v}; {motivo}")
    fila_v = ("D10", v, tarde["est"], tarde["ic_bajo"], tarde["ic_alto"], tarde["n_tratados"], motivo)
    return filas, fila_v


# ---- D11: exposicion por rama y anillos de derrame
# Decisiones de construccion (fijadas antes de calcular, sin mirar ninguna cifra de D11; van tambien en el commit):
#  * "tratados de D2": los de las celdas de D2 (cel_pri); la cobertura cuenta los de las celdas con g en ANIOS_RAMA. El anio
#    de g es g // 12 (g = anio * 12 + mes - 1).
#  * la distancia de un tratado sale de los pares (hijo, padre) de SQL_GOLPES (km < KM_TRATADO, mes del hijo = g) unidos a
#    mart_trayectoria_par por (hijo, padre); un par con m_min nulo no cuenta.
#  * las bandas de rama son [lo, hi) en m; "250 m o mas" son las dos ultimas juntas.
#  * "control sin rama medida": su pozo_id no aparece en ninguna fila de mart_trayectoria_par (ni de padre ni de hijo).
#    "par medido de m_min < RAMA_LIMPIA_M con un hijo fracturado en la ventana": el control es el padre y mes_frac del par
#    cae en [g - VENTANA_PREVIA, g + H_CORTO] (m_min estrictamente menor que RAMA_LIMPIA_M).
#  * D11b: la diferencia es limpios menos todos los controles.
#  * D11c: para los anillos de 2 km o mas, g es el primer mes de todo el panel con km_min en [lo, hi); si ese mes no cumple
#    las condiciones el pozo no entra (no se busca otro mes). "Ningun golpe mas cerca": km_min < lo en [g - VENTANA_PREVIA,
#    g + H_CORTO]. Controles limpios: km_min nulo (sin golpe a menos de 5 km) en todos esos meses.
#  * Los pozos de anillos fuera del universo de D2 toman el peso de su bloque (extender_pesos) y los que se quedan sin
#    bloque salen, como en D4, D5 y D10. El control de D4 es contra mart_causal_profundo_d4, corte distancia, banda 1-2.
#  * Criterio de D11c sobre I(1): veredicto_anillos con -ic_alto en lugar del IC bajo (ic_alto < 0 equivale a -ic_alto > 0).

def en_anios_rama(g: int) -> bool:
    return ANIOS_RAMA[0] <= int(g) // 12 <= ANIOS_RAMA[1]


def bandas_rama(m: np.ndarray) -> np.ndarray:
    """Banda de BANDAS_RAMA_M de cada distancia en m ([lo, hi)); -1 si no hay distancia."""
    m = np.asarray(m, dtype=float)
    out = np.full(len(m), -1, dtype=np.int64)
    for k, (lo, hi) in enumerate(BANDAS_RAMA_M):
        out[(m >= lo) & (m < (np.inf if hi is None else hi))] = k
    return out


def distancia_rama(pozo_ids: np.ndarray, g: int, pares: dict) -> np.ndarray:
    """m_min de cada tratado de una celda: la menor de sus pares del mes g; nan si no tiene o g fuera de ANIOS_RAMA.
    pares: {(pozo_id del padre, mes del hijo): m_min menor}."""
    if not en_anios_rama(g):
        return np.full(len(pozo_ids), np.nan)
    return np.array([pares.get((int(p), int(g)), np.nan) for p in pozo_ids], dtype=float)


def controles_rama_limpios(pozo_ids: np.ndarray, g: int, cerca: dict, medidos: set) -> np.ndarray:
    """Mascara de los controles que se quedan: con rama medida y sin un par de m_min < RAMA_LIMPIA_M con un hijo
    fracturado en [g - VENTANA_PREVIA, g + H_CORTO]. cerca: {pozo_id del padre: meses de hijo con m_min < RAMA_LIMPIA_M}."""
    a, b = g - VENTANA_PREVIA, g + H_CORTO
    keep = np.zeros(len(pozo_ids), dtype=bool)
    for i, p in enumerate(pozo_ids):
        p = int(p)
        if p not in medidos:
            continue
        meses = cerca.get(p)
        keep[i] = meses is None or not bool(np.any((meses >= a) & (meses <= b)))
    return keep


def controles_sin_golpe(D: dict, g: int, controles: np.ndarray, km: float = KM_ANILLO_LIMPIO) -> np.ndarray:
    """Mascara de los controles sin golpe a menos de `km` km (km_min) en [g - VENTANA_PREVIA, g + H_CORTO]."""
    a = max(g - VENTANA_PREVIA - D["t0"], 0)
    b = min(g + H_CORTO - D["t0"], D["T"] - 1)
    if b < a or not len(controles):
        return np.ones(len(controles), dtype=bool)
    return ~(D["km_min"][controles, a:b + 1] < km).any(axis=1)


def filtrar_controles(cel: list[dict], keep_fn) -> list[dict]:
    """Celdas con solo los controles que pide keep_fn(celda); descarta las que quedan con menos de MIN_CONTROLES_CELDA."""
    out = []
    for ce in cel:
        c_sel = np.asarray(keep_fn(ce), dtype=bool)
        if int(c_sel.sum()) < MIN_CONTROLES_CELDA:
            continue
        out.append(_recortar(ce, np.ones(len(ce["tratados"]), dtype=bool), c_sel))
    return out


def candidatos_anillo(D: dict, lo: float, hi: float) -> tuple[np.ndarray, np.ndarray]:
    """Pozos con un mes con km_min en [lo, hi) y su primer mes g, sin golpe mas cerca que lo (km_min < lo) en
    [g - VENTANA_PREVIA, g + H_CORTO]. Sin las condiciones de edad, base y ventana previa."""
    km = D["km_min"]
    g = _primera((km >= lo) & (km < hi), D["t0"])
    sel = np.flatnonzero(g >= 0)
    gs = g[sel]
    ok = np.ones(len(sel), dtype=bool)
    for i, (p, gg) in enumerate(zip(sel, gs)):
        a = max(int(gg) - VENTANA_PREVIA - D["t0"], 0)
        b = min(int(gg) + H_CORTO - D["t0"], D["T"] - 1)
        ok[i] = not bool((km[p, a:b + 1] < lo).any())
    return sel[ok], gs[ok]


def cohorte_anillo(D: dict, lo: float, hi: float) -> tuple[np.ndarray, np.ndarray]:
    """Cohorte de un anillo de 2 km o mas: candidatos_anillo con edad, base valida y ventana previa de causal._condiciones."""
    sel, gs = candidatos_anillo(D, lo, hi)
    media, valida = _bases(D)
    cols = np.clip(gs - D["t0"], 0, D["T"] - 1)
    ok = _condiciones(D, gs, valida[sel, cols], media[sel, cols], wells=sel)
    return sel[ok], gs[ok]


def pares_de_rama(con) -> tuple[dict, dict, set]:
    """(pares de tratado, hijos cercanos por padre, pozos con rama medida) de mart_trayectoria_par."""
    pares = {}
    for hijo, padre, mes, km, m in con.execute(
            f"select g.hijo, g.pozo, g.mes, g.km, p.m_min from ({SQL_GOLPES}) g "
            "join mart_trayectoria_par p on p.hijo = g.hijo and p.padre = g.pozo where p.m_min is not null").fetchall():
        if km < KM_TRATADO:
            k = (int(padre), int(mes))
            pares[k] = min(pares.get(k, float("inf")), float(m))
    cerca: dict[int, list[int]] = {}
    for padre, mes in con.execute(
            "select padre, year(mes_frac) * 12 + month(mes_frac) - 1 from mart_trayectoria_par "
            "where m_min is not null and m_min < ?", [RAMA_LIMPIA_M]).fetchall():
        cerca.setdefault(int(padre), []).append(int(mes))
    medidos = {int(x) for fila in con.execute("select hijo, padre from mart_trayectoria_par").fetchall() for x in fila}
    return pares, {p: np.array(v, dtype=np.int64) for p, v in cerca.items()}, medidos


def _todos(ce: dict) -> np.ndarray:
    return np.ones(len(ce["tratados"]), dtype=bool)


def _vacio(W: np.ndarray) -> dict:
    nan = float("nan")
    return {"est": nan, "ic_bajo": nan, "ic_alto": nan, "vals": np.full(len(W), nan), "n_tratados": 0, "n_controles": 0}


def _estimar_o_vacio(D: dict, cel: list[dict], W: np.ndarray) -> dict:
    return _estimar(D, cel, W) if cel else _vacio(W)


def _indice1(D: dict, cel: list[dict], W: np.ndarray) -> dict:
    """I(1) de D1 en las celdas dadas, con los mismos sorteos: el formato de _estimar."""
    if not cel:
        return _vacio(W)
    r = bootstrap(D, cel, (1,), W)
    return {"est": float(r["est"][0]), "ic_bajo": float(r["ic_bajo"][0]), "ic_alto": float(r["ic_alto"][0]),
            "vals": r["vals"][:, 0], "n_tratados": int(r["n_tratados"][0]), "n_controles": int(r["n_controles"][0])}


def _fila11(parte: str, banda: str, resultado: str, rr: dict) -> tuple:
    return (parte, banda, resultado, int(rr["n_tratados"]), int(rr["n_controles"]), float(rr["est"]),
            float(rr["ic_bajo"]), float(rr["ic_alto"]))


def _fila11_dif(parte: str, banda: str, resultado: str, a: dict, b: dict) -> tuple:
    est, bajo, alto = _dif(a, b)
    return (parte, banda, resultado, None, None, est, bajo, alto)


def _txt(rr: dict) -> str:
    return f"{rr['est']:+.2f} (IC {rr['ic_bajo']:+.2f} a {rr['ic_alto']:+.2f}), tratados {rr['n_tratados']}"


NOMBRES_BANDA = ("menos de 250 m", "250 m a 1 km", "1 km o más")
CLAVES_BANDA = ("0-250", "250-1000", "1000+")


def calcular_d11(con, prep: tuple) -> tuple[list[tuple], list[tuple]]:
    """D11a, D11b y D11c: filas del mart y las dos filas de veredicto (D11a y D11c)."""
    D, cel_pri, W, wells, coh = prep
    filas = []
    pares, hijos_cerca, medidos = pares_de_rama(con)

    def dist(ce):
        return distancia_rama(D["pozo_id"][ce["tratados"]], ce["g"], pares)

    # ---- cobertura y D11a
    n_anios = sum(len(ce["tratados"]) for ce in cel_pri if en_anios_rama(ce["g"]))
    n_dist = int(sum(int(np.sum(~np.isnan(dist(ce)))) for ce in cel_pri))
    filas.append(("D11a", "cobertura", "tratados_d2_en_anios", n_anios, None, float(n_anios), None, None))
    filas.append(("D11a", "cobertura", "con_distancia", n_dist, None, n_dist / n_anios if n_anios else float("nan"), None, None))
    print(f"D11 cobertura: {n_dist} de {n_anios} tratados de D2 con g de {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]} tienen distancia de rama")
    bandas = {}
    for k, clave in enumerate(CLAVES_BANDA):
        cel = celdas_por_mascara(cel_pri, lambda ce, k=k: bandas_rama(dist(ce)) == k)
        bandas[clave] = _estimar_o_vacio(D, cel, W)
        filas.append(_fila11("D11a", clave, "dW", bandas[clave]))
        print(f"D11a {NOMBRES_BANDA[k]}: dW {_txt(bandas[clave])}")
    cel_cerca = celdas_por_mascara(cel_pri, lambda ce: bandas_rama(dist(ce)) == 0)
    cel_lejos = celdas_por_mascara(cel_pri, lambda ce: bandas_rama(dist(ce)) >= 1)
    cerca, lejos = _estimar_o_vacio(D, cel_cerca, W), _estimar_o_vacio(D, cel_lejos, W)
    filas.append(_fila11("D11a", "cerca", "dW", cerca))
    filas.append(_fila11("D11a", "lejos", "dW", lejos))
    d_est, d_bajo, d_alto = _dif(cerca, lejos)
    filas.append(("D11a", "cerca_menos_lejos", "dW", None, None, d_est, d_bajo, d_alto))
    v_a = veredicto_rama(int(cerca["n_tratados"]), int(lejos["n_tratados"]), d_bajo, d_alto, float(cerca["est"]))
    motivo_a = (f"dW menos de 250 m {_txt(cerca)}; 250 m o más {_txt(lejos)}; diferencia {d_est:+.2f} "
                f"(IC {d_bajo:+.2f} a {d_alto:+.2f}); con distancia {n_dist} de {n_anios} tratados de D2 de "
                f"{ANIOS_RAMA[0]} a {ANIOS_RAMA[1]}")
    print(f"D11a: cerca menos lejos {d_est:+.2f} (IC {d_bajo:+.2f} a {d_alto:+.2f}); veredicto {v_a}")
    fila_va = ("D11a", v_a, d_est, d_bajo, d_alto, int(cerca["n_tratados"]) + int(lejos["n_tratados"]), motivo_a)

    # ---- D11b
    cel_sub = celdas_por_mascara(cel_pri, lambda ce: bandas_rama(dist(ce)) >= 0)
    cel_limpia = filtrar_controles(cel_sub, lambda ce: controles_rama_limpios(D["pozo_id"][ce["controles"]], ce["g"],
                                                                              cerca=hijos_cerca, medidos=medidos))
    todos, limpios = _estimar_o_vacio(D, cel_sub, W), _estimar_o_vacio(D, cel_limpia, W)
    quitados = sum(len(ce["controles"]) for ce in cel_sub) - sum(len(ce["controles"]) for ce in cel_limpia)
    filas.append(_fila11("D11b", "submuestra", "todos_los_controles", todos))
    filas.append(_fila11("D11b", "submuestra", "controles_limpios", limpios))
    filas.append(_fila11_dif("D11b", "submuestra", "limpios_menos_todos", limpios, todos))
    b_est, b_bajo, b_alto = _dif(limpios, todos)
    print(f"D11b todos los controles: dW {_txt(todos)}; controles limpios: dW {_txt(limpios)}; limpios menos todos "
          f"{b_est:+.2f} (IC {b_bajo:+.2f} a {b_alto:+.2f}); controles quitados {quitados}, celdas {len(cel_sub)} a {len(cel_limpia)}")

    # ---- D11c
    W_ext, fuera = extender_pesos(D, W, wells)
    anillos, plano_12 = {}, None
    for lo, hi in ANILLOS_KM:
        sel, gs = _cohorte_1_2_km(D) if (lo, hi) == (KM_TRATADO, KM_LIMPIO) else cohorte_anillo(D, lo, hi)
        bruto = celdas(D, coh, H_CORTO, False, tratados=sel, g_por_tratado=gs)
        if (lo, hi) == (KM_TRATADO, KM_LIMPIO):
            plano_12 = _estimar_o_vacio(D, celdas_por_mascara(bruto, _todos, fuera), W_ext)
        limpia = filtrar_controles(bruto, lambda ce: controles_sin_golpe(D, ce["g"], ce["controles"]))
        cel = celdas_por_mascara(limpia, _todos, fuera)
        anillos[(lo, hi)] = (len(sel), _estimar_o_vacio(D, cel, W_ext), _indice1(D, cel, W_ext))
    cel_01 = celdas_por_mascara(filtrar_controles(cel_pri, lambda ce: controles_sin_golpe(D, ce["g"], ce["controles"])),
                                _todos, fuera)
    r01 = (_estimar_o_vacio(D, cel_01, W_ext), _indice1(D, cel_01, W_ext))
    filas.append(_fila11("D11c", "0-1", "dW", r01[0]))
    filas.append(_fila11("D11c", "0-1", "I1", r01[1]))
    print(f"D11c anillo 0 a 1 km (tratados de D2, controles limpios a {KM_ANILLO_LIMPIO:g} km): dW {_txt(r01[0])}; "
          f"I(1) {_txt(r01[1])}")
    d4 = con.execute("select valor, n_tratados, ic_bajo, ic_alto from mart_causal_profundo_d4 "
                     "where corte = 'distancia' and banda = '1-2' and resultado = 'dW'").fetchone()
    dif4 = abs(float(plano_12["est"]) - float(d4[0]))
    # los extremos del IC dependen de W_ext: comprueban que los sorteos son los de D4 (revision del PR #189)
    dif4_ic = max(abs(float(plano_12["ic_bajo"]) - float(d4[2])), abs(float(plano_12["ic_alto"]) - float(d4[3])))
    print(f"control D11c: anillo 1 a 2 km con los controles de causal.celdas: dW {plano_12['est']:.6f}, {plano_12['n_tratados']} "
          f"tratados; mart_causal_profundo_d4 {float(d4[0]):.6f}, {d4[1]} tratados; diferencia {dif4:.3e} en el valor y "
          f"{dif4_ic:.3e} en el IC")
    if dif4 > TOLERANCIA_CONTROL or not dif4_ic <= TOLERANCIA_CONTROL_IC:
        raise RuntimeError(f"el anillo de 1 a 2 km no reproduce D4: diferencia {dif4:.3e} en el valor y {dif4_ic:.3e} en el IC")
    n_ani, bajos_w, bajos_i, n_i = {}, {}, {}, {}
    for (lo, hi), (n_coh, rw, ri) in anillos.items():
        clave = f"{lo:g}-{hi:g}"
        filas.append(_fila11("D11c", clave, "dW", rw))
        filas.append(_fila11("D11c", clave, "I1", ri))
        filas.append(("D11c", clave, "cohorte", n_coh, None, float(n_coh), None, None))
        n_ani[(lo, hi)], bajos_w[(lo, hi)] = int(rw["n_tratados"]), float(rw["ic_bajo"])
        n_i[(lo, hi)], bajos_i[(lo, hi)] = int(ri["n_tratados"]), -float(ri["ic_alto"])
        print(f"D11c anillo {lo:g} a {hi:g} km: dW {_txt(rw)}; I(1) {_txt(ri)}; cohorte {n_coh}")
    v_c = veredicto_anillos(n_ani, bajos_w)
    v_i = veredicto_anillos(n_i, bajos_i)
    filas.append(("D11c", "criterio_I1", v_i, None, None, None, None, None))
    r23 = anillos[(2.0, 3.0)][1]
    motivo_c = "dW por anillo " + "; ".join(f"{lo:g} a {hi:g} km {rw['est']:+.2f} (IC {rw['ic_bajo']:+.2f} a {rw['ic_alto']:+.2f}, "
                                          f"{rw['n_tratados']} tratados)" for (lo, hi), (_, rw, _ri) in anillos.items()) + \
        f"; criterio sobre I(1) (sin veredicto): {v_i}"
    print(f"D11c: veredicto {v_c}; criterio I(1) {v_i}")
    fila_vc = ("D11c", v_c, float(r23["est"]), float(r23["ic_bajo"]), float(r23["ic_alto"]), int(r23["n_tratados"]), motivo_c)
    return filas, [fila_va, fila_vc]


# ---- D14: D2 con el golpe definido por distancia entre ramas

def matrices_rama(D: dict, pares) -> tuple[np.ndarray, np.ndarray]:
    """(lat_min, sin_medir) por pozo y mes del panel, a partir de pares (padre_id, mes, km, m_min o None).

    lat_min: la menor m_min de los pares medidos del padre en ese mes (nan si no hay). sin_medir: el padre tiene ese mes un
    hijo a menos de KM_LIMPIO cuyo par no tiene m_min medido."""
    n, T, t0 = D["n"], D["T"], D["t0"]
    idx = {int(p): i for i, p in enumerate(D["pozo_id"])}
    lat = np.full((n, T), np.nan)
    sin = np.zeros((n, T), dtype=bool)
    for padre, mes, km, m in pares:
        i, c = idx.get(int(padre)), int(mes) - t0
        if i is None or c < 0 or c >= T:
            continue
        if m is None:
            if km < KM_LIMPIO:
                sin[i, c] = True
        elif np.isnan(lat[i, c]) or float(m) < lat[i, c]:
            lat[i, c] = float(m)
    return lat, sin


def _hay_en_ventana(mat: np.ndarray, D: dict, a, b, wells: np.ndarray) -> np.ndarray:
    """Hay algun True de `mat` en los meses [a, b] (escalar o uno por pozo) para cada pozo de `wells`."""
    T, t0 = D["T"], D["t0"]
    a = np.broadcast_to(np.asarray(a, dtype=np.int64), len(wells))
    b = np.broadcast_to(np.asarray(b, dtype=np.int64), len(wells))
    cs = np.concatenate([np.zeros((mat.shape[0], 1), dtype=np.int64), np.cumsum(mat, axis=1)], axis=1)
    lo = np.clip(a - t0, 0, T)
    hi = np.clip(b - t0 + 1, 0, T)
    return (cs[wells, hi] - cs[wells, lo]) > 0


def cohorte_d14(D: dict, lat_min: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Tratados de D14 (pozo, mes g): primer mes con un par de m_min < RAMA_TRATADO_M, g en ANIOS_RAMA, condiciones del padre de
    D2 (causal._condiciones, con su ventana previa a KM_LIMPIO) y ninguna rama cercana en [g - VENTANA_PREVIA, g - 1]."""
    cerca = np.nan_to_num(lat_min, nan=np.inf) < RAMA_TRATADO_M
    g = _primera(cerca, D["t0"])
    sel = np.flatnonzero(g >= 0)
    gs = g[sel]
    en = np.array([en_anios_rama(int(x)) for x in gs], dtype=bool)
    sel, gs = sel[en], gs[en]
    if not len(sel):
        return sel, gs
    media, valida = _bases(D)
    cols = np.clip(gs - D["t0"], 0, D["T"] - 1)
    ok = _condiciones(D, gs, valida[sel, cols], media[sel, cols], wells=sel)
    ok &= ~_hay_en_ventana(cerca, D, gs - VENTANA_PREVIA, gs - 1, sel)
    return sel[ok], gs[ok]


def controles_d14(D: dict, lat_min: np.ndarray, sin_medir: np.ndarray, g: int, controles: np.ndarray) -> np.ndarray:
    """Mascara de los controles que se quedan: sin par medido con m_min < RAMA_CONTROL_M ni hijo cercano sin m_min medido
    en [g - VENTANA_PREVIA, g + H_CORTO]."""
    if not len(controles):
        return np.ones(0, dtype=bool)
    controles = np.asarray(controles, dtype=np.int64)
    expuesto = np.nan_to_num(lat_min, nan=np.inf) < RAMA_CONTROL_M
    a, b = g - VENTANA_PREVIA, g + H_CORTO
    return ~(_hay_en_ventana(expuesto, D, a, b, controles) | _hay_en_ventana(sin_medir, D, a, b, controles))


def solapamiento(cel14: list[dict], cel2: list[dict]) -> tuple[int, int, int]:
    """(D14 y no D2, D2 y no D14, en los dos) por pozo, entre los tratados en celdas de cada diseno."""
    s14 = {int(p) for ce in cel14 for p in ce["tratados"]}
    s2 = {int(p) for ce in cel2 for p in ce["tratados"]}
    return len(s14 - s2), len(s2 - s14), len(s14 & s2)


def pares_golpe_rama(con) -> list[tuple]:
    """Pares (padre, mes del hijo, km, m_min o None) de todo golpe a menos de 5 km (SQL_GOLPES) con su m_min si esta medido."""
    return con.execute(
        f"select g.pozo, g.mes, g.km, p.m_min from ({SQL_GOLPES}) g "
        "left join mart_trayectoria_par p on p.hijo = g.hijo and p.padre = g.pozo").fetchall()


def calcular_d14(con, prep: tuple) -> list[tuple]:
    """Filas de mart_causal_d14: D14 (con veredicto), D2 en ANIOS_RAMA y los recuentos de solapamiento."""
    D, cel_pri, W, wells, coh = prep
    lat, sin = matrices_rama(D, pares_golpe_rama(con))
    sel, gs = cohorte_d14(D, lat)
    bruto = celdas(D, coh, H_CORTO, False, tratados=sel, g_por_tratado=gs)
    W_ext, fuera = extender_pesos(D, W, wells)
    limpia = filtrar_controles(bruto, lambda ce: controles_d14(D, lat, sin, ce["g"], ce["controles"]))
    cel14 = celdas_por_mascara(limpia, _todos, fuera)
    cel2 = celdas_por_mascara([ce for ce in cel_pri if en_anios_rama(ce["g"])], _todos, fuera)
    r14, r2 = _estimar_o_vacio(D, cel14, W_ext), _estimar_o_vacio(D, cel2, W_ext)
    solo14, solo2, ambos = solapamiento(cel14, cel2)
    v = veredicto_d14(int(r14["n_tratados"]), float(r14["ic_bajo"]))
    nan = float("nan")

    def fila(d, vv, rr, motivo):
        return (d, vv, float(rr["est"]), float(rr["ic_bajo"]), float(rr["ic_alto"]), int(rr["n_tratados"]), motivo,
                int(rr["n_controles"]), int(rr.get("n_celdas", len(cel14 if d == "D14" else cel2))))

    motivo14 = (f"dW {_txt(r14)}, {r14['n_controles']} controles, {len(cel14)} celdas; cohorte de rama {len(sel)} pozos "
                f"antes de las celdas")
    filas = [fila("D14", v, r14, motivo14),
             fila("D2_2016_2023", "sin veredicto", r2, f"dW {_txt(r2)}, {r2['n_controles']} controles, {len(cel2)} celdas")]
    for nombre, n in (("D14_no_D2", solo14), ("D2_no_D14", solo2), ("D14_y_D2", ambos)):
        filas.append((nombre, "recuento", float(n), nan, nan, int(n), "pozos tratados en celdas con control", None, None))
    print(f"D14: dW {_txt(r14)}, controles {r14['n_controles']}, celdas {len(cel14)}; veredicto {v}")
    print(f"D2 {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]}: dW {_txt(r2)}, controles {r2['n_controles']}, celdas {len(cel2)}")
    print(f"solapamiento: D14 y no D2 {solo14}; D2 y no D14 {solo2}; en los dos {ambos}")
    return filas


def _pp(x: float) -> str:
    return f"{x:+.1f}".replace(".", ",")


def _seccion_d10(con, ver: dict) -> list[str]:
    """Seccion de D10 a partir de mart_causal_exposicion_d10 y su fila de veredicto (vacia si no estan)."""
    if "D10" not in ver:
        return []
    filas = con.execute("select * from mart_causal_exposicion_d10").fetchall()
    dw = {(r[0], r[1]): r for r in filas if r[2] == "dW" and r[1] is not None}
    resumen = {(r[0], r[2]): r for r in filas if r[1] is None}
    tabla = ["| Mes desde el golpe (e) | dW (puntos porcentuales) | IC 95 % | Tratados que quedan |", "|---|---|---|---|"]
    for e in E_D5:
        r = dw[("1km", e)]
        tabla.append(f"| {e} | {_pp(r[5])} | {_pp(r[6])} a {_pp(r[7])} | {r[3]} |")
    t1, t2 = resumen[("1km", "dW_tarde")], resumen[("2km", "dW_tarde")]
    c1, c2 = resumen[("1km", "censurados_12")], resumen[("2km", "censurados_12")]
    temprano = resumen[("1km", "dW_temprano")][5]
    return [
        "## D10: golpes repetidos", "",
        "Un pozo golpeado puede recibir otro golpe unos meses después, y entonces no sabés cuál de los dos mueve el agua. D10 "
        "repite la serie por mes de D5 sacando, desde el mes del segundo golpe, a todo tratado que recibe otro golpe a menos "
        f"de {KM_CENSURA:g} km entre los meses {S_CENSURA} y {H_D5} después del primero (el mes 1 no cuenta: un pad que se "
        "fractura entre dos meses es el mismo evento). Los controles no tienen golpe a "
        f"{KM_CENSURA_SECUNDARIA:g} km en toda la ventana. La regla se fijó en {SHA_REGLA} antes de calcular ninguna cifra "
        f"(\"regla fijada en {SHA_REGLA} antes de calcular\").", "",
        *tabla, "",
        f"- Media de dW entre los meses {TRAMO_TARDE[0]} y {TRAMO_TARDE[1]} (serie a {KM_CENSURA:g} km): {_pp(t1[5])} "
        f"(IC {_pp(t1[6])} a {_pp(t1[7])}), con {t1[3]} tratados como mínimo; media de los meses 0 y 1: {_pp(temprano)}.",
        f"- Misma serie censurada a {KM_CENSURA_SECUNDARIA:g} km (la cuenta de D5, sin veredicto): media tardía {_pp(t2[5])} "
        f"(IC {_pp(t2[6])} a {_pp(t2[7])}), con {t2[3]} tratados como mínimo.",
        f"- Tratados que salen de la serie antes del mes {H_D5}: {c1[3]} de {c1[4]} a {KM_CENSURA:g} km y {c2[3]} de {c2[4]} a "
        f"{KM_CENSURA_SECUNDARIA:g} km.",
        f"- **Veredicto de D10: {ver['D10'][1]}.**", "",
        "**Lo que no dice:** la censura no es al azar (los padres de zonas de relleno reciben más hijos); la serie censurada "
        "mide la primera fractura sola en los padres que no recibieron otra, no en todos.", "",
    ]


def _seccion_d11(con, ver: dict) -> list[str]:
    """Seccion de D11 a partir de mart_causal_exposicion_d11 y sus filas de veredicto (vacia si no estan)."""
    if "D11a" not in ver or "D11c" not in ver:
        return []
    f = {(r[0], r[1], r[2]): r for r in con.execute("select * from mart_causal_exposicion_d11").fetchall()}

    def pct(x):
        return f"{100 * x:.0f}".replace(".", ",") + " %"

    def ic(r):
        return f"{_pp(r[6])} a {_pp(r[7])}"

    n_anios, con_dist = f[("D11a", "cobertura", "tratados_d2_en_anios")], f[("D11a", "cobertura", "con_distancia")]
    tabla_a = ["| Distancia entre ramas | dW (puntos porcentuales) | IC 95 % | Tratados |", "|---|---|---|---|"]
    for clave, nombre in zip(CLAVES_BANDA, NOMBRES_BANDA):
        r = f[("D11a", clave, "dW")]
        tabla_a.append(f"| {nombre} | {_pp(r[5])} | {ic(r)} | {r[3]} |")
    lejos, dif = f[("D11a", "lejos", "dW")], f[("D11a", "cerca_menos_lejos", "dW")]
    tabla_a.append(f"| 250 m o más (las dos bandas juntas) | {_pp(lejos[5])} | {ic(lejos)} | {lejos[3]} |")
    tabla_a.append(f"| Diferencia, menos de 250 m menos 250 m o más | {_pp(dif[5])} | {ic(dif)} | |")
    todos, limpios = f[("D11b", "submuestra", "todos_los_controles")], f[("D11b", "submuestra", "controles_limpios")]
    d_b = f[("D11b", "submuestra", "limpios_menos_todos")]
    tabla_b = ["| Controles | dW (puntos porcentuales) | IC 95 % | Tratados | Controles |", "|---|---|---|---|---|",
               f"| Todos los de D2 | {_pp(todos[5])} | {ic(todos)} | {todos[3]} | {todos[4]} |",
               f"| Sin rama cercana con hijo en la ventana ni sin rama medida | {_pp(limpios[5])} | {ic(limpios)} | "
               f"{limpios[3]} | {limpios[4]} |",
               f"| Diferencia, limpios menos todos | {_pp(d_b[5])} | {ic(d_b)} | | |"]
    tabla_c = ["| Anillo (km del golpe más cercano) | dW (puntos porcentuales) | IC 95 % | Tratados | "
               "I(1) (puntos de índice) | IC 95 % | Tratados |", "|---|---|---|---|---|---|---|"]
    filas_c = [("0 a 1 (los tratados de D2)", "0-1")] + [(f"{lo:g} a {hi:g}", f"{lo:g}-{hi:g}") for lo, hi in ANILLOS_KM]
    for nombre, clave in filas_c:
        w, i = f[("D11c", clave, "dW")], f[("D11c", clave, "I1")]
        tabla_c.append(f"| {nombre} | {_pp(w[5])} | {ic(w)} | {w[3]} | {_pp(i[5])} | {ic(i)} | {i[3]} |")
    crit = next(r[2] for k, r in f.items() if k[1] == "criterio_I1")
    return [
        "## D11: exposición por rama y anillos", "",
        "El golpe se mide por la distancia entre bocas de pozo, pero lo que pasa bajo tierra depende de cuánto se acercan las "
        "ramas horizontales. D11 hace tres cosas con los tratados de D2: parte el efecto según la distancia mínima entre las "
        "dos ramas (D11a), vuelve a estimarlo sin los controles que tienen una rama cerca de otro pozo recién fracturado "
        "(D11b) y mira anillos de distancia de boca más lejanos que los de D2 para ver si el efecto llega más lejos (D11c). "
        f"La regla se fijó en {SHA_REGLA} antes de calcular ninguna cifra (\"regla fijada en {SHA_REGLA} antes de calcular\").",
        "",
        f"**D11a, dosis por rama.** La distancia de cada tratado es la menor distancia entre ramas con sus hijos del mes del "
        f"golpe a menos de {KM_TRATADO:g} km; solo entran los golpes de {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]}. De {n_anios[3]} "
        f"tratados de D2 en esos años, {con_dist[3]} ({pct(con_dist[5])}) tienen distancia.", "",
        *tabla_a, "",
        f"- **Veredicto de D11a: {ver['D11a'][1]}.**", "",
        f"**D11b, controles limpios por rama.** En la misma submuestra, se sacan de cada celda los controles con una rama a "
        f"menos de {RAMA_LIMPIA_M:g} m de un hijo fracturado entre {VENTANA_PREVIA} meses antes y {H_CORTO} después del "
        "golpe, y los que no tienen rama medida. Sin veredicto.", "",
        *tabla_b, "",
        f"**D11c, anillos (Butts, 2021).** Cada cohorte es el primer mes en que el golpe más cercano cae en el anillo, sin golpes "
        f"más cerca en la ventana; los controles no tienen golpe a menos de {KM_ANILLO_LIMPIO:g} km en la ventana. La fila de "
        "0 a 1 km es D2 con esos controles limpios.", "",
        *tabla_c, "",
        f"- **Veredicto de D11c: {ver['D11c'][1]}.**",
        f"- Mismo criterio sobre I(1), con el IC alto menor que cero (sin veredicto): {crit}.", "",
        "**Lo que no dice:** `m_min` es la geometría declarada de la rama, no la red de fracturas; la submuestra con rama es "
        "sobre todo de 2016 a 2023.", "",
    ]


def _seccion_d14(con) -> list[str]:
    """Seccion de D14 a partir de mart_causal_d14 (vacia si el mart no esta)."""
    if not con.execute("select 1 from information_schema.tables where table_name = 'mart_causal_d14'").fetchone():
        return []
    f = {r[0]: r for r in con.execute("select * from mart_causal_d14").fetchall()}
    if "D14" not in f or "D2_2016_2023" not in f:
        return []

    def ic(r):
        return f"{_pp(r[3])} a {_pp(r[4])}"

    d14, d2 = f["D14"], f["D2_2016_2023"]
    tabla = ["| Definición del golpe | ATT_W de dW (puntos porcentuales) | IC 95 % | Tratados | Controles | Celdas |",
             "|---|---|---|---|---|---|",
             f"| D14: rama a menos de {RAMA_TRATADO_M:g} m | {_pp(d14[2])} | {ic(d14)} | {d14[5]} | {d14[7]} | {d14[8]} |",
             f"| D2 de {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]}: boca a menos de {KM_TRATADO:g} km (sin veredicto) | {_pp(d2[2])} | "
             f"{ic(d2)} | {d2[5]} | {d2[7]} | {d2[8]} |"]
    return [
        "## D14: el golpe definido por la distancia entre ramas", "",
        "D2 define el golpe por la distancia entre bocas de pozo (un hijo a menos de "
        f"{KM_TRATADO:g} km). D14 repite D2 definiendo el golpe por la distancia entre las ramas horizontales, que es la que "
        f"importa bajo tierra: un padre es tratado si un hijo fracturado en su mes g tiene una rama a menos de {RAMA_TRATADO_M:g} m "
        f"de la suya, sin importar la distancia de boca (hasta 5 km), y solo entran los golpes de {ANIOS_RAMA[0]} a "
        f"{ANIOS_RAMA[1]}, los años en que hay ramas medidas. Los controles son los de D2 sin ninguna rama a menos de "
        f"{RAMA_CONTROL_M:g} m ni hijo cercano sin rama medida en la ventana. D14 cambia solo la definición del golpe: usa la "
        "identificación de D2 y sus placebos son los de D2, no se repitieron. "
        f"La regla se fijó en {SHA_REGLA_D14} (con su aclaración en {SHA_ACLARACION_D14}) antes de calcular ninguna cifra "
        f"(\"regla fijada en {SHA_REGLA_D14} antes de calcular\").", "",
        *tabla, "",
        f"- **Veredicto de D14: {d14[1]}.**",
        f"- Tratados de D14 que no son tratados de D2 de {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]} en una celda con controles: "
        f"{f['D14_no_D2'][5]}.",
        f"- Tratados de D2 de {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]} que no son tratados de D14: {f['D2_no_D14'][5]}.",
        f"- Tratados en los dos: {f['D14_y_D2'][5]}.",
        "- Estos tres recuentos toman a todos los tratados de celdas con controles. La tabla cuenta solo a los que entran a "
        "la estimación, con el corte de agua medido y en celdas con suficientes controles que también lo tengan; por eso los "
        "recuentos suman más que los tratados de la tabla.", "",
        "**Lo que no dice:** `m_min` es la distancia entre ramas medidas, no la geometría de la fractura; un hijo sin rama "
        "medida puede estar cerca igual (queda fuera de los controles, pero no de los otros golpes de un padre tratado); la "
        f"ventana es solo {ANIOS_RAMA[0]} a {ANIOS_RAMA[1]}.", "",
    ]


def pagina_exposicion(con) -> str:
    """Pagina de D12 y D10 a partir de los marts ya escritos."""
    d12 = {r[0]: r for r in con.execute("select * from mart_causal_exposicion_d12").fetchall()}
    ver = {r[0]: r for r in con.execute("select * from mart_causal_exposicion_veredicto").fetchall()}
    nombres = {"D12a": "D12a, todos los tratados", "D12b": "D12b, sin YPF", "D12c": "D12c, solo YPF"}
    filas = []
    for k, nombre in nombres.items():
        if k not in d12:
            continue
        _, est, bajo, alto, n, celdas_n, parte = d12[k]
        filas.append(f"| {nombre} | {_pp(est)} | {_pp(bajo)} a {_pp(alto)} | {n} | {celdas_n} | "
                     f"{'' if parte is None else f'{parte * 100:.0f}'.replace('.', ',')} % |")
    tabla = "\n".join(["| Resultado | dW (puntos porcentuales) | IC 95 % | Tratados | Celdas | Parte de los tratados de D2 |",
                       "|---|---|---|---|---|---|", *filas])
    lineas = [
        "# Exposición: operador por área (D12)", "",
        "¿El efecto del golpe sobre el corte de agua es de YPF o de la composición de pozos? Para responderlo, D12 vuelve a "
        "estimar el D2 dentro de celdas de operador y área: cada pozo golpeado se compara solo con controles del mismo "
        "operador y la misma área del mismo mes y la misma edad. La regla se fijó en "
        f"{SHA_REGLA} antes de calcular ninguna cifra (\"regla fijada en {SHA_REGLA} antes de calcular\"), y los sorteos son "
        "los de D2 y D6, así que los números se pueden comparar.", "",
        tabla, "",
        f"- **D12a (dentro de operador y área):** {ver['D12a'][1]}.",
        f"- **D12b (fuera de YPF):** {ver['D12b'][1]}.", "",
        "**Lo que no dice:** comparar dentro de cada celda saca la composición entre operadores y entre áreas, pero no la "
        "que queda adentro de cada operador y área.", "",
    ]
    return "\n".join(lineas + _seccion_d10(con, ver) + _seccion_d11(con, ver)
                      + _seccion_d14(con))


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    prep = preparar(con)
    filas, filas_v = calcular(con, prep)
    filas_d10, fila_v10 = calcular_d10(con, prep)
    filas_d11, filas_v11 = calcular_d11(con, prep)
    filas_d14 = calcular_d14(con, prep)
    _escribir(con, "mart_causal_exposicion_d12", COLS_D12, filas)
    _escribir(con, "mart_causal_exposicion_d10", COLS_D10, filas_d10)
    _escribir(con, "mart_causal_exposicion_d11", COLS_D11, filas_d11)
    _escribir(con, "mart_causal_exposicion_veredicto", COLS_VEREDICTO, [*filas_v, fila_v10, *filas_v11])
    _escribir(con, "mart_causal_d14", COLS_D14, filas_d14)
    PAGINA.parent.mkdir(parents=True, exist_ok=True)
    PAGINA.write_text(pagina_exposicion(con), encoding="utf-8")
    print(f"escrito {PAGINA}")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(DATA / "warehouse.duckdb"))
    main(ap.parse_args().db)
