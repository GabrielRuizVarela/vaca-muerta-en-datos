"""Causal profundo: si el corte de agua sube porque entra agua o porque sale petroleo, con que dosis, con que forma en el
tiempo, donde se sostiene y si se repite en Colorado.

Se corre despues de pipeline.build y de pipeline.causal:  uv run python -m pipeline.causal_profundo

REGLA FIJADA ANTES DE CORRER (2026-11-22). Este archivo es el primer commit de la unidad: la regla, las constantes y las
funciones de veredicto. Antes de fijarla no se calculo ninguna cifra de estos disenos: ni volumen de agua o de petroleo por
dia de tratados o controles, ni ATT por distancia, por tamano del hijo, por mes, por operador o por zona, ni nada de Colorado
con este diseno. Si algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una
cifra. El plan completo: docs/plan-causal-profundo.md.

Regla informada en esto: al fijarla se conocian las cifras de pipeline.causal (rama t3/causal-diseno, commit de regla 8f52ff1,
cabeza 7f2e499): D2 ATT_W = 13,8 puntos porcentuales (IC 9,5 a 19,9, 447 tratados), placebo de cierre 3,6, placebos previo,
fecha falsa y distancia falsa sin romper; por posicion costado 16,2 y punta 7,8; D1 ATT(1) = -25,8 con nunca tratados -8,0
(rompe); D1b sin muestra (43). Tambien la brecha descriptiva del corte de agua de descomposicion.md (panel 4) y el gradiente
por distancia del petroleo publicado. La caida del petroleo al mes 1 es conocida: por eso D3 no decide con el petroleo solo,
decide con el agua.

Todo reutiliza pipeline.causal sin tocarlo: universo, golpes, cohortes, tratados, controles aun no tratados, celdas de mes
y grupo de edad (H = H_CORTO salvo D5), agregacion pesada por tratados, bootstrap por bloques de 5 km con la misma semilla
(SEMILLA_CAUSAL) y las mismas repeticiones, y la regla de rotura de un placebo (`causal.rompe`).

D3. Agua que entra o petroleo que sale (prioridad uno; decide si D2 se gana el nombre "comunicacion fisica").
  * Por pozo y mes: A = agua_m3 / dias_mes y O = petroleo_m3 / dias_mes (por dia calendario, primario), y A_pd, O_pd con
    dias_efectivos en el denominador (meses con dias_efectivos de DIAS_MIN_PD o mas; secundario).
  * Base de liquido L = media de (agua_m3 + petroleo_m3) / dias_mes en los meses -6 a -4 (los tres con fila), mayor que
    BASE_MIN_LIQUIDO m3/d. Base de A y de O: media de esos mismos meses.
  * dA = (media de A en VENTANA_D3, con al menos un mes) - base de A, sobre L, x 100: puntos del liquido base. Igual dO.
    Recortados en +-TOPE_D3 (fraccion). La identidad dA + dO = cambio del liquido se publica como control de cuentas.
  * Puente con D2: dW con la media (no el maximo) de W en VENTANA_D3, publicado sin veredicto.
  * Placebos de dA (rompe con UMBRAL_ROTURA_VOLUMEN puntos): previo (ventana -2 y -1), fecha falsa, distancia falsa y nunca
    tratados, definidos como en pipeline.causal.
  * Veredicto (`veredicto_d3`), en este orden:
      - "sin muestra": menos de MIN_TRATADOS tratados con dA y dO, o menos de MIN_BLOQUES bloques.
      - "no sobrevive a su placebo": rompe cualquiera de los cuatro placebos de dA.
      - "entra agua": IC bajo de ATT_A (dia calendario) mayor que cero. Cerrar baja los dias, asi que un cierre no sube el
        agua por dia calendario: una suba es agua que llega.
      - "entra agua en los dias producidos": IC de ATT_A incluye cero, IC bajo de ATT_A_pd mayor que cero y su placebo previo
        y de nunca tratados no rompen.
      - "el corte sube porque cae el petroleo": IC alto de ATT_A menor que UMBRAL_VOLUMEN, IC alto de ATT_A_pd menor que
        UMBRAL_VOLUMEN e IC alto de ATT_O menor que cero (cota: el agua no sube UMBRAL_VOLUMEN puntos del liquido base).
      - "no firme": cualquier otro caso.
  * Que le pasa al texto de D2 (README fila y limite, wiki/index.md, resumen y lectura de causal.md): solo con "entra agua"
    o "entra agua en los dias producidos" se sigue leyendo "comunicacion fisica". Con cualquier otro veredicto el veredicto
    impreso de D2 no cambia (lo fija 8f52ff1) pero cada frase de entrada dice que D3, fijado despues, no le da ese nombre.
  * Sin veredicto: placebo de nunca tratados sobre dW de D2 (la regla de D2 no lo tenia), con UMBRAL_ROTURA_AGUA.

D4. Dosis: distancia y tamano del hijo.
  * Bandas de la distancia del primer golpe: BANDAS_KM. Las dos primeras parten los tratados de D2. La tercera es una
    cohorte nueva: primer golpe a menos de KM_LIMPIO en [1, 2) km, sin golpe a menos de 1 km en [g - VENTANA_PREVIA, g + H],
    mismas condiciones de tratado y los mismos controles. La banda de 3 a 5 km es el placebo de distancia falsa, se reimprime.
  * Resultado que decide: dW de D2. Se publica tambien dA de D3.
  * Veredicto de distancia (`veredicto_gradiente`): "sin muestra" si una banda tiene menos de MIN_TRATADOS_BANDA; "gradiente"
    si las tres estimaciones son monotonas (la mas cercana mayor o igual) y el IC de la diferencia cercana menos lejana
    (mismos sorteos) queda entero sobre cero; "sin gradiente" si ese IC incluye cero; "no firme" en otro caso.
  * Tamano: agua de fractura del hijo de la cohorte (dim_fractura_pozo.agua_m3), en terciles entre los tratados de D2 con el
    dato. Mismo veredicto con el tercil alto menos el bajo, "sin dato" si menos de COBERTURA_MIN de los tratados lo tienen.
    La longitud de rama se publica igual, sin veredicto.
  * Precisiones fijadas antes de calcular D4 (commit propio, ninguna cifra de D4 vista):
      - Sorteos: los mismos W de D3, con el mismo universo de pozos (asi el control de D2 sigue coincidiendo). Un pozo
        fuera de ese universo toma en cada sorteo el peso de su bloque de 5 km (el de cualquier pozo del universo en ese
        bloque); si su bloque no tiene ningun pozo del universo queda fuera, y se publica cuantos quedan fuera.
      - Distancia del primer golpe de un tratado de D2: km_min del padre en el mes g (el golpe mas cercano de ese mes).
        Banda 0 a 0,5 km: km_min < 0,5; banda 0,5 a 1 km: el resto de los tratados de D2.
      - Cohorte de 1 a 2 km: g = primer mes con un golpe a menos de KM_LIMPIO; el golpe mas cercano de ese mes esta en
        [1, 2) km; edad, base de petroleo valida y ventana previa limpia como en causal._condiciones; ningun golpe a
        menos de 1 km en [g - VENTANA_PREVIA, g + H_CORTO] (g1 del pozo antes de g - VENTANA_PREVIA no puede pasar
        porque g es el primer golpe a 2 km; se exige g1 < 0 o g1 > g + H_CORTO). Celdas y controles con causal.celdas.
      - "Tratados de D2" para el tamano: los tratados de las celdas de D2 con dW. El hijo es hijo_min del padre en g. Tiene
        el dato si agua_m3 de dim_fractura_pozo es mayor que cero. Cortes de terciles con np.quantile en 1/3 y 2/3 sobre
        esos tratados con dato; tercil bajo: <= corte 1/3; alto: > corte 2/3; medio: el resto. La cobertura es la parte de
        los tratados de D2 con dato. La longitud de rama (rama_horizontal_m > 0) se parte igual y publica alto menos bajo
        con su IC, sin veredicto.
      - Diferencias (cercana menos lejana, alto menos bajo): resta sorteo por sorteo de los dos bootstrap con los mismos W;
        IC con los percentiles de causal._ic.

D5. Forma en el tiempo.
  * Serie de e = E_D5 con H = H_D5, por mes (no maximo): dW(e) = W(e) - base de W, dA(e), dO(e). Controles aun no tratados
    hasta g + H_D5. Es el efecto de la primera fractura y de lo que venga despues: no se exige limpieza posterior a g + 1 (D1b
    mostro que exigirla vacia la muestra); se publica el numero de tratados con otro golpe a 2 km en 2 a 12.
  * Veredicto (`veredicto_forma`) sobre la media de dW en TRAMO_TARDE: "sin muestra" con menos de MIN_TRATADOS_D5; "persiste"
    si su IC bajo es mayor que cero; "se cura" si su IC incluye cero y su IC alto es menor que FRACCION_CURA de la media de dW
    en VENTANA_D3; "no firme" en otro caso. Se publica el primer mes con IC sobre cero, sin veredicto.
  * Precisiones fijadas antes de calcular D5 y D6 (commit propio, ninguna cifra de D5 ni de D6 vista):
      - Tratados: los de la cohorte de D2 (cohortes). Celdas: causal.celdas con H = H_D5 (controles sin golpe a KM_LIMPIO
        en [g - VENTANA_PREVIA, g + H_D5] y con su primer golpe a KM_TRATADO despues de g + H_D5).
      - Sorteos: los mismos W de D3 y el mismo universo, extendidos con extender_pesos como en D4; se publica cuantos
        pozos quedan fuera.
      - dW(e) = W(g + e) menos la base de W de D2 (media de los meses -6 a -4 con al menos MIN_MESES_W_BASE), un mes solo.
        dA(e) y dO(e): d3_pozos con la ventana (e, e), la base y el tope de D3.
      - Media tarde: la media de las estimaciones de dW de los meses de TRAMO_TARDE, sorteo por sorteo con los mismos W; IC
        con causal._ic. Su n es el menor n de tratados con dW entre esos meses. Media temprana: la media de las
        estimaciones de dW de los meses 0 y 1 de la misma serie (no el puente de D3, que usa otras celdas).
      - Primer mes con IC sobre cero: el menor e >= 0 de E_D5 con IC bajo de dW(e) mayor que cero; ninguno si no hay.
      - Otro golpe: tratados con al menos un golpe a menos de KM_LIMPIO en los meses g + 2 a g + 12 (causal._ventana).

D6. Donde se sostiene.
  * Cortes, todos publicados: cada operador con MIN_TRATADOS_OPERADOR o mas (subgrupo y sin el), grupo de edad del padre,
    periodo de la cohorte (PERIODOS) y area con MIN_TRATADOS_OPERADOR o mas. La formacion no es un corte: el universo es
    Vaca Muerta shale. Sin ajuste por comparaciones multiples; ningun subgrupo tiene veredicto.
  * Veredicto (`veredicto_general`) sobre dW: "general" si sin cada operador el IC bajo sigue sobre cero; "depende de un
    operador" en otro caso, con su nombre.
  * Precisiones fijadas antes de calcular D6 (mismo commit que las de D5):
      - Resultado: dW de D2 (causal._valores_agua con k = 0) sobre las celdas de D2, los mismos W de D3.
      - Un subgrupo filtra los tratados de cada celda y deja sus controles (celdas_por_mascara); "sin el operador" saca
        tratados y controles de ese operador (causal._celdas_sin_operador), como el dejar un operador afuera de D1.
      - Operadores y areas con MIN_TRATADOS_OPERADOR o mas tratados en las celdas de D2 (la cuenta de pipeline.causal, con
        o sin dW). Area: dim_pozo.area del padre por pozo_id, "Sin dato" si falta (es un corte mas si llega al minimo).
      - Edad: el grupo de edad de la celda (los cuatro de causal). Periodo: el anio del mes g del tratado (PERIODOS).
      - Veredicto: veredicto_general con el IC bajo de dW sin cada operador con el minimo. Valor del veredicto: el sin
        operador de IC bajo mas chico, con su IC.

D7. Colorado (segunda cuenca independiente).
  * Mismo diseno, mismas constantes, sobre el warehouse opcional de Colorado (data/colorado/warehouse.duckdb): pozos
    horizontales con coordenadas, mes de fractura de co_hijo sin fecha_dudosa, produccion de fct_produccion.
  * Compuerta de dato (`veredicto_colorado`): "sin dato de agua" si menos de COBERTURA_MIN de los meses base de los tratados
    tienen agua_m3 y dias_efectivos. Si pasa, D2 y D3 con sus veredictos tal cual. "se repite" si D2 de Colorado es
    "sostiene" y D3 de Colorado da el mismo veredicto que D3 de Vaca Muerta; "no se repite" si D2 de Colorado es "no firme"
    o cualquier otro que no sea "sostiene"; "sin muestra" si D2 de Colorado lo es; "se repite en parte" en otro caso.

D8. Lectura operativa: solo si D3 da "entra agua" (o en los dias producidos) y D4 da "gradiente" de distancia. Un parrafo, sin
dinero (eso es otra unidad), sin veredicto.

Lo que no dice: causa bajo los supuestos de pipeline.causal (tendencias paralelas condicionales, sin anticipacion mas alla de
3 meses, sin derrame sobre controles limpios a 2 km), no un hecho fisico medido. Sin presion de boca ni produccion diaria no
se ve el agua entrar; D3 la ve en el volumen mensual.
"""
from __future__ import annotations

import argparse

from pipeline.causal import (KM_LIMPIO, MIN_BLOQUES, MIN_TRATADOS, MIN_TRATADOS_OPERADOR, UMBRAL_ROTURA_AGUA,
                             UMBRAL_ROTURA_PUNTOS, V_D2_SOSTIENE, V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA, rompe)

# heredado de pipeline.causal sin cambio (la regla de rotura de un placebo es causal.rompe)
REGLA_HEREDADA = {"KM_LIMPIO": KM_LIMPIO, "MIN_TRATADOS_OPERADOR": MIN_TRATADOS_OPERADOR,
                  "UMBRAL_ROTURA_AGUA": UMBRAL_ROTURA_AGUA, "rompe": rompe}

# ---- regla fijada (no cambiar despues de ver cifras) ----
COMMIT_BASE = "7f2e499"               # cabeza de t3/causal-diseno sobre la que se fija esta regla

# D3
VENTANA_D3 = (0, 1)                   # meses relativos a g, inclusive
VENTANA_PREVIA_D3 = (-2, -1)          # placebo previo
BASE_MIN_LIQUIDO = 1.0                # m3/d de liquido de la base
DIAS_MIN_PD = 5                       # dias efectivos minimos para A_pd y O_pd
TOPE_D3 = 3.0                         # recorte de dA y dO, en fraccion del liquido base
UMBRAL_VOLUMEN = 5.0                  # puntos del liquido base: cota del agua que "no sube"
UMBRAL_ROTURA_VOLUMEN = UMBRAL_ROTURA_PUNTOS

# D4
BANDAS_KM = ((0.0, 0.5), (0.5, 1.0), (1.0, 2.0))
MIN_TRATADOS_BANDA = 100
COBERTURA_MIN = 0.7

# D5
E_D5 = tuple(range(-6, 13))
H_D5 = 12
TRAMO_TARDE = (6, 12)                 # inclusive
MIN_TRATADOS_D5 = 200
FRACCION_CURA = 0.5

# D6
PERIODOS = ((None, 2018), (2019, 2021), (2022, None))   # anio de la cohorte, inclusive

V_D3_ENTRA = "entra agua"
V_D3_ENTRA_PD = "entra agua en los días producidos"
V_D3_PETROLEO = "el corte sube porque cae el petróleo"
V_GRADIENTE = "gradiente"
V_SIN_GRADIENTE = "sin gradiente"
V_SIN_DATO = "sin dato"
V_PERSISTE = "persiste"
V_CURA = "se cura"
V_GENERAL = "general"
V_DEPENDE = "depende de un operador"
V_SIN_DATO_AGUA = "sin dato de agua"
V_REPITE = "se repite"
V_REPITE_PARTE = "se repite en parte"
V_NO_REPITE = "no se repite"

# veredictos de D3 con los que D2 conserva el nombre "comunicacion fisica"
D3_GANA_NOMBRE = (V_D3_ENTRA, V_D3_ENTRA_PD)


def veredicto_d3(n_tratados: int, n_bloques: int, placebos_rotos: bool,
                 a: tuple[float, float], a_pd: tuple[float, float], o: tuple[float, float],
                 placebos_pd_rotos: bool) -> str:
    """a, a_pd, o: (IC bajo, IC alto) de ATT_A, ATT_A_pd y ATT_O, en puntos del liquido base."""
    if n_tratados < MIN_TRATADOS or n_bloques < MIN_BLOQUES:
        return V_SIN_MUESTRA
    if placebos_rotos:
        return V_PLACEBO
    if a[0] > 0:
        return V_D3_ENTRA
    if a[0] <= 0 <= a[1] and a_pd[0] > 0 and not placebos_pd_rotos:
        return V_D3_ENTRA_PD
    if a[1] < UMBRAL_VOLUMEN and a_pd[1] < UMBRAL_VOLUMEN and o[1] < 0:
        return V_D3_PETROLEO
    return V_NO_FIRME


def d2_gana_nombre(v_d3: str) -> bool:
    """Si el texto de entrada de D2 puede seguir diciendo "comunicacion fisica"."""
    return v_d3 in D3_GANA_NOMBRE


def veredicto_gradiente(n_bandas: list[int], estimaciones: list[float], dif_bajo: float, dif_alto: float,
                        cobertura: float = 1.0) -> str:
    """estimaciones de la mas cercana (o el tercil mas grande) a la mas lejana (o el mas chico); dif = primera menos ultima."""
    if cobertura < COBERTURA_MIN:
        return V_SIN_DATO
    if min(n_bandas) < MIN_TRATADOS_BANDA:
        return V_SIN_MUESTRA
    monotono = all(a >= b for a, b in zip(estimaciones, estimaciones[1:]))
    if monotono and dif_bajo > 0:
        return V_GRADIENTE
    if dif_bajo <= 0 <= dif_alto:
        return V_SIN_GRADIENTE
    return V_NO_FIRME


def veredicto_forma(n_tratados: int, tarde_bajo: float, tarde_alto: float, temprano: float) -> str:
    """tarde: IC de la media de dW en TRAMO_TARDE; temprano: media de dW en VENTANA_D3."""
    if n_tratados < MIN_TRATADOS_D5:
        return V_SIN_MUESTRA
    if tarde_bajo > 0:
        return V_PERSISTE
    if tarde_bajo <= 0 <= tarde_alto and temprano > 0 and tarde_alto < FRACCION_CURA * temprano:
        return V_CURA
    return V_NO_FIRME


def veredicto_general(bajos_sin_operador: dict[str, float]) -> tuple[str, list[str]]:
    """Devuelve el veredicto y los operadores sin los cuales el IC bajo de dW deja de estar sobre cero."""
    malos = sorted(op for op, b in bajos_sin_operador.items() if not b > 0)
    return (V_GENERAL, []) if not malos else (V_DEPENDE, malos)


def veredicto_colorado(cobertura_agua: float, v_d2_co: str, v_d3_co: str, v_d3_vm: str) -> str:
    if cobertura_agua < COBERTURA_MIN:
        return V_SIN_DATO_AGUA
    if v_d2_co == V_SIN_MUESTRA:
        return V_SIN_MUESTRA
    if v_d2_co != V_D2_SOSTIENE:
        return V_NO_REPITE
    if v_d3_co == v_d3_vm:
        return V_REPITE
    return V_REPITE_PARTE


# ================================================================== calculo
# Todo lo que sigue aplica el docstring de este archivo. No cambia ninguna constante ni ningun veredicto.

import duckdb
import numpy as np

from pipeline.causal import (H_CORTO, KM_LIMPIO, KM_TRATADO, MIN_CONTROLES_CELDA, MIN_MESES_W_BASE, REPS, SEMILLA_CAUSAL,
                             _bases, _bootstrap_prep, _cohorte_falsa_distancia, _cohorte_falsa_fecha,
                             _cohorte_nunca_tratados, _condiciones, _celdas_sin_operador, _ventana, _ic, _mes, _n_bloques, _panel_promedio, _pesos_bloques,
                             _preparar, _primera, _valores_agua, cargar, celdas, celdas_d1b, cohortes, diseno_d2,
                             placebo_cierre, veredicto_d2, FRACCION_CIERRE)
from pipeline.costo import _escribir
from pipeline.ingest import DATA

# ---- paneles de volumen

def cargar_volumenes(con, D: dict) -> dict:
    """Volumenes por pozo y mes: agua, petroleo y liquido, por dia calendario y por dia producido.

    A = agua_m3 / dias_mes y O = petroleo_m3 / dias_mes (dia calendario); A_pd y O_pd usan dias_efectivos en el
    denominador y solo existen en los meses con dias_efectivos de DIAS_MIN_PD o mas. L = (agua_m3 + petroleo_m3) / dias_mes.
    Donde falta un dato va nan."""
    n, T = D["n"], D["T"]
    A = np.full((n, T), np.nan)
    O = np.full((n, T), np.nan)
    A_pd = np.full((n, T), np.nan)
    O_pd = np.full((n, T), np.nan)
    L = np.full((n, T), np.nan)
    pos = {int(p): i for i, p in enumerate(D["pozo_id"])}
    for pid, mes, pet, ag, de, dm in con.execute(
            "select pozo_id, mes, petroleo_m3, agua_m3, dias_efectivos, dias_mes "
            "from fct_produccion").fetchall():
        i = pos.get(int(pid))
        j = _mes(mes) - D["t0"]
        if i is None or j < 0 or j >= T:
            continue
        pet = float(pet) if pet is not None else float("nan")
        ag = float(ag) if ag is not None else float("nan")
        de = float(de) if de is not None else 0.0
        dm = float(dm) if dm is not None else 0.0
        if dm > 0:
            if not np.isnan(pet):
                O[i, j] = pet / dm
            if not np.isnan(ag):
                A[i, j] = ag / dm
            if not np.isnan(pet) and not np.isnan(ag):
                L[i, j] = (pet + ag) / dm
        if de >= DIAS_MIN_PD:
            if not np.isnan(pet):
                O_pd[i, j] = pet / de
            if not np.isnan(ag):
                A_pd[i, j] = ag / de
    return {"A": A, "O": O, "A_pd": A_pd, "O_pd": O_pd, "L": L}


def preparar_bases(D: dict) -> dict:
    """Bases de D3 por pozo y mes: la de A, la de O, las de A_pd y O_pd y la del liquido L.

    La base de un mes m son los meses m - 6 a m - 4. La base de A y de O es la media de esos mismos meses con fila de
    liquido (los tres); la de A_pd y de O_pd es la media con al menos 2 meses. La base de L es la media de los tres meses
    con fila y solo vale si supera BASE_MIN_LIQUIDO. Deja la base de liquido en D["base_L"]."""
    L = D["L"]
    con_fila = ~np.isnan(L)
    base_L, bueno_L = _panel_promedio(D, L, 3)
    D["base_L"] = np.where(bueno_L & (base_L > BASE_MIN_LIQUIDO), base_L, np.nan)
    base_A, _ = _panel_promedio(D, np.where(con_fila, D["A"], np.nan), 3)
    base_O, _ = _panel_promedio(D, np.where(con_fila, D["O"], np.nan), 3)
    base_A_pd, _ = _panel_promedio(D, D["A_pd"], 2)
    base_O_pd, _ = _panel_promedio(D, D["O_pd"], 2)
    return {"A": base_A, "O": base_O, "A_pd": base_A_pd, "O_pd": base_O_pd, "L": D["base_L"]}


# ---- magnitudes por pozo

def _media_ventana(D: dict, pozos: np.ndarray, g: int, ventana: tuple[int, int], mat: np.ndarray) -> np.ndarray:
    """Media de la magnitud en los meses de la ventana (relativos a g) de cada pozo, con al menos un mes con dato."""
    pozos = np.asarray(pozos, dtype=np.int64)
    T = D["T"]
    cols = np.array([g + e - D["t0"] for e in range(ventana[0], ventana[1] + 1)], dtype=np.int64)
    dentro = (cols >= 0) & (cols < T)
    vals = mat[np.ix_(pozos, np.clip(cols, 0, T - 1))]
    vals = np.where(dentro[None, :], vals, np.nan)
    cuenta = np.sum(~np.isnan(vals), axis=1)
    return np.where(cuenta > 0, np.nansum(vals, axis=1) / np.maximum(cuenta, 1), np.nan)


def d3_pozos(D: dict, pozos: np.ndarray, g: int, mat: np.ndarray, base: np.ndarray,
             ventana: tuple[int, int]) -> np.ndarray:
    """dX de cada pozo: (media de la ventana - base) sobre la base de liquido, en fraccion y recortada.

    `mat` es el panel de la magnitud (A, O, A_pd u O_pd), `base` su base por pozo y mes y `ventana` los meses relativos
    a g. Da nan cuando falta la base, la base de liquido o todos los meses de la ventana."""
    pozos = np.asarray(pozos, dtype=np.int64)
    out = np.full(len(pozos), np.nan)
    if not len(pozos):
        return out
    col = g - D["t0"]
    if col < 0 or col >= D["T"]:
        return out
    media = _media_ventana(D, pozos, g, ventana, mat)
    b = base[pozos, col]
    lq = D["base_L"][pozos, col]
    ok = ~np.isnan(media) & ~np.isnan(b) & ~np.isnan(lq)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(ok, (media - b) / lq, np.nan)
    return np.clip(out, -TOPE_D3, TOPE_D3)


def valores_volumen(D: dict, celdas_: list[dict], mat: np.ndarray, base: np.ndarray,
                    ventana: tuple[int, int]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """dX de tratados y de controles de cada celda, en el mismo orden de las celdas."""
    vt, vc = [], []
    for ce in celdas_:
        vt.append(d3_pozos(D, ce["tratados"], ce["g"], mat, base, ventana))
        vc.append(d3_pozos(D, ce["controles"], ce["g"], mat, base, ventana))
    return vt, vc


def _dw_media(D: dict, pozos: np.ndarray, g: int, base_w: np.ndarray) -> np.ndarray:
    """dW con la media (no el maximo) de W en los meses 0 y 1 menos la base de W de D2, en fraccion."""
    pozos = np.asarray(pozos, dtype=np.int64)
    out = np.full(len(pozos), np.nan)
    if not len(pozos):
        return out
    col = g - D["t0"]
    if col < 0 or col >= D["T"]:
        return out
    media = _media_ventana(D, pozos, g, VENTANA_D3, D["w"])
    b = base_w[pozos, col]
    ok = ~np.isnan(media) & ~np.isnan(b)
    return np.where(ok, media - b, np.nan)


def valores_dw_media(D: dict, celdas_: list[dict]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Puente con D2: dW con la media de W en los meses 0 y 1, con la base de W de D2."""
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    vt, vc = [], []
    for ce in celdas_:
        vt.append(_dw_media(D, ce["tratados"], ce["g"], base_w))
        vc.append(_dw_media(D, ce["controles"], ce["g"], base_w))
    return vt, vc


def _suma(x, y):
    """Suma de dos magnitudes por pozo: nan en cuanto falta una de las dos.

    Trabaja con un array por celda o con la lista de arrays de todas las celdas."""
    if isinstance(x, list):
        return [_suma(a, b) for a, b in zip(x, y)]
    return np.where(np.isnan(x) | np.isnan(y), np.nan, x + y)


def estimar_valores(D: dict, celdas_: list[dict], W: np.ndarray, vt: list[np.ndarray],
                    vc: list[np.ndarray]) -> dict:
    """Bootstrap de una magnitud ya preparada por celda (est, IC, n tratados y n controles)."""
    prep = _preparar(celdas_, vt, vc)
    return _bootstrap_prep(D, prep, W)


def estimar(D: dict, celdas_: list[dict], W: np.ndarray, mat: np.ndarray, base: np.ndarray,
            ventana: tuple[int, int]) -> dict:
    """Bootstrap de una magnitud de volumen en las celdas dadas, con su ventana."""
    vt, vc = valores_volumen(D, celdas_, mat, base, ventana)
    return estimar_valores(D, celdas_, W, vt, vc)


# ---- D4: dosis por distancia y tamano del hijo

COLS_D4 = [("corte", "varchar"), ("banda", "varchar"), ("resultado", "varchar"), ("n_tratados", "integer"),
           ("n_controles", "integer"), ("valor", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]


def extender_pesos(D: dict, W: np.ndarray, universo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pesos de los sorteos para todos los pozos: uno fuera del universo toma el peso de su bloque de 5 km.

    Un pozo del universo conserva su columna; uno de fuera copia la de cualquier pozo del universo en su mismo bloque.
    Si su bloque no tiene ningun pozo del universo queda fuera (columna en cero y True en la mascara devuelta)."""
    universo = np.unique(np.asarray(universo, dtype=np.int64))
    bloque = np.asarray(D["bloque"])
    rep = {}
    for j in universo:
        rep.setdefault(bloque[j].item(), int(j))
    W_ext = np.array(W, dtype=float, copy=True)
    fuera = np.zeros(len(bloque), dtype=bool)
    en_universo = np.zeros(len(bloque), dtype=bool)
    en_universo[universo] = True
    for i in np.flatnonzero(~en_universo):
        j = rep.get(bloque[i].item())
        if j is None:
            fuera[i] = True
            W_ext[:, i] = 0.0
        else:
            W_ext[:, i] = W[:, j]
    return W_ext, fuera


def celdas_por_mascara(celdas_: list[dict], keep_fn, fuera: np.ndarray | None = None) -> list[dict]:
    """Celdas con solo los tratados que pide keep_fn(celda) (mascara booleana sobre sus tratados).

    Los pozos marcados en `fuera` (mascara por pozo) salen de tratados y de controles. Descarta la celda que se queda sin
    tratados o con menos de MIN_CONTROLES_CELDA controles; base_t y base_c siguen alineadas con sus pozos."""
    out = []
    for ce in celdas_:
        mt = np.asarray(keep_fn(ce), dtype=bool)
        mc = np.ones(len(ce["controles"]), dtype=bool)
        if fuera is not None:
            mt = mt & ~fuera[ce["tratados"]]
            mc = ~fuera[ce["controles"]]
        t, c = ce["tratados"][mt], ce["controles"][mc]
        if not len(t) or len(c) < MIN_CONTROLES_CELDA:
            continue
        out.append({**ce, "tratados": t, "controles": c, "base_t": ce["base_t"][mt], "base_c": ce["base_c"][mc]})
    return out


def _cohorte_1_2_km(D: dict) -> tuple[np.ndarray, np.ndarray]:
    """Primer golpe a menos de KM_LIMPIO con el golpe mas cercano de ese mes en [KM_TRATADO, KM_LIMPIO) km, sin golpe a
    menos de KM_TRATADO km en [g - VENTANA_PREVIA, g + H_CORTO], con edad, base valida y ventana previa limpia."""
    media, valida = _bases(D)
    g2 = _primera(D["km_min"] < KM_LIMPIO, D["t0"])
    sel = np.flatnonzero(g2 >= 0)
    gs = g2[sel]
    cols = np.clip(gs - D["t0"], 0, D["T"] - 1)
    km = D["km_min"][sel, cols]
    ok = (km >= KM_TRATADO) & (km < KM_LIMPIO)
    ok &= _condiciones(D, gs, valida[sel, cols], media[sel, cols], wells=sel)
    g1 = D["g1"][sel]
    ok &= (g1 < 0) | (g1 > gs + H_CORTO)
    return sel[ok], gs[ok]


def _dif(a: dict, b: dict) -> tuple[float, float, float]:
    """Diferencia a menos b sorteo por sorteo (mismos W): punto, IC bajo, IC alto."""
    vals = np.asarray(a["vals"], dtype=float) - np.asarray(b["vals"], dtype=float)
    bajo, alto = _ic(vals)
    return float(a["est"] - b["est"]), float(bajo), float(alto)


def _terciles(valores: np.ndarray) -> tuple[float, float]:
    """Cortes de 1/3 y 2/3 de los valores con dato."""
    c1, c2 = np.quantile(valores, [1 / 3, 2 / 3])
    return float(c1), float(c2)


def _etiquetas_terciles(n: int, pozos: np.ndarray, valores: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    """Tercil de cada pozo con dato (0 alto, 1 medio, 2 bajo) y -1 sin dato; devuelve tambien los cortes."""
    etiqueta = np.full(n, -1, dtype=np.int64)
    if not len(pozos):
        return etiqueta, (float("nan"), float("nan"))
    c1, c2 = _terciles(valores)
    et = np.where(valores <= c1, 2, np.where(valores > c2, 0, 1))
    etiqueta[pozos] = et
    return etiqueta, (c1, c2)


# ---- main

COLS_D3 = [("cantidad", "varchar"), ("n_tratados", "integer"), ("n_controles", "integer"), ("valor", "double"),
           ("ic_bajo", "double"), ("ic_alto", "double"), ("rompe", "boolean")]

COLS_VEREDICTO = [("diseno", "varchar"), ("veredicto", "varchar"), ("valor", "double"), ("ic_bajo", "double"),
                  ("ic_alto", "double"), ("n_tratados", "integer"), ("n_bloques", "integer"),
                  ("d2_gana_nombre", "boolean"), ("motivo", "varchar")]

COLS_D7 = [("resultado", "varchar"), ("n_tratados", "integer"), ("valor", "double"), ("ic_bajo", "double"),
            ("ic_alto", "double"), ("roto", "boolean"), ("veredicto", "varchar")]


def _fila(rr: dict, roto) -> tuple:
    """Fila de una magnitud: n tratados, n controles, valor, IC y si su placebo rompe."""
    return (int(rr["n_tratados"]), int(rr["n_controles"]), float(rr["est"]), float(rr["ic_bajo"]),
            float(rr["ic_alto"]), roto)


def _rompe(rr: dict, umbral: float) -> bool:
    """Si el placebo rompe con el umbral dado (la regla de causal.rompe)."""
    return bool(rompe(float(rr["est"]), float(rr["ic_bajo"]), float(rr["ic_alto"]), umbral))


def _par(D: dict, bases: dict, cel: list[dict], W: np.ndarray) -> tuple[dict, dict]:
    """dW (el de D2) y dA (el de D3) de unas celdas, con los mismos sorteos."""
    vt_w, vc_w = _valores_agua(D, cel, 0)
    vt_a, vc_a = valores_volumen(D, cel, D["A"], bases["A"], VENTANA_D3)
    return estimar_valores(D, cel, W, vt_w, vc_w), estimar_valores(D, cel, W, vt_a, vc_a)


def _tratados(cel: list[dict]) -> np.ndarray:
    return np.concatenate([ce["tratados"] for ce in cel]) if cel else np.zeros(0, dtype=np.int64)


def _fila_d4(corte: str, banda: str, resultado: str, rr: dict) -> tuple:
    return (corte, banda, resultado, int(rr["n_tratados"]), int(rr["n_controles"]), float(rr["est"]),
            float(rr["ic_bajo"]), float(rr["ic_alto"]))


def _fila_dif(corte: str, banda: str, resultado: str, a: dict, b: dict) -> tuple:
    est, bajo, alto = _dif(a, b)
    return (corte, banda, resultado, None, None, est, bajo, alto)


def _d4(con, D: dict, coh: dict, bases: dict, W: np.ndarray, universo: np.ndarray, cel_pri: list[dict], d2_todo: dict, res_fd: dict) -> list[tuple]:
    """D4: dosis por distancia del primer golpe y por tamano del hijo. Escribe mart_causal_profundo_d4 y devuelve las
    dos filas de veredicto (D4_distancia y D4_tamano)."""
    W_ext, fuera = extender_pesos(D, W, universo)
    filas = []
    n = D["n"]

    # ---- distancia
    def distancia(ce):
        return D["km_min"][ce["tratados"], ce["g"] - D["t0"]]

    cel_b0 = celdas_por_mascara(cel_pri, lambda ce: distancia(ce) < 0.5, fuera)
    cel_b1 = celdas_por_mascara(cel_pri, lambda ce: ~(distancia(ce) < 0.5), fuera)
    sel12, g12 = _cohorte_1_2_km(D)
    cel_12_bruto = celdas(D, coh, H_CORTO, False, tratados=sel12, g_por_tratado=g12)
    pozos_12 = np.unique(np.concatenate([_tratados(cel_12_bruto)] + [ce["controles"] for ce in cel_12_bruto])) \
        if cel_12_bruto else np.zeros(0, dtype=np.int64)
    n_fuera = int(fuera[pozos_12].sum())
    cel_12 = celdas_por_mascara(cel_12_bruto, lambda ce: np.ones(len(ce["tratados"]), dtype=bool), fuera)
    bandas = [("0-0.5", cel_b0), ("0.5-1", cel_b1), ("1-2", cel_12)]
    res = {}
    for nombre, cel in bandas:
        res[nombre] = _par(D, bases, cel, W_ext)
        for rr, etq in zip(res[nombre], ("dW", "dA")):
            filas.append(_fila_d4("distancia", nombre, etq, rr))
    filas.append(_fila_d4("distancia", "3-5", "dW", d2_todo["distancia_falsa"]))
    filas.append(_fila_d4("distancia", "3-5", "dA", res_fd))
    dif_w = _dif(res["0-0.5"][0], res["1-2"][0])
    dif_a = _dif(res["0-0.5"][1], res["1-2"][1])
    filas.append(_fila_dif("distancia", "cercana_menos_lejana", "dW", res["0-0.5"][0], res["1-2"][0]))
    filas.append(_fila_dif("distancia", "cercana_menos_lejana", "dA", res["0-0.5"][1], res["1-2"][1]))
    filas.append(("distancia", "fuera", "cuenta", None, None, float(n_fuera), None, None))
    for nombre, _ in bandas:
        w_, a_ = res[nombre]
        print(f"D4 distancia {nombre} km: dW = {w_['est']:+.2f} (IC {w_['ic_bajo']:+.2f} a {w_['ic_alto']:+.2f}), "
              f"dA = {a_['est']:+.2f} (IC {a_['ic_bajo']:+.2f} a {a_['ic_alto']:+.2f}), tratados {w_['n_tratados']}")
    rf = d2_todo["distancia_falsa"]
    print(f"D4 distancia 3-5 km (placebo): dW = {rf['est']:+.2f} (IC {rf['ic_bajo']:+.2f} a {rf['ic_alto']:+.2f}), "
          f"dA = {res_fd['est']:+.2f}, tratados {rf['n_tratados']}")
    print(f"D4 distancia cercana menos lejana: dW = {dif_w[0]:+.2f} (IC {dif_w[1]:+.2f} a {dif_w[2]:+.2f}), "
          f"dA = {dif_a[0]:+.2f} (IC {dif_a[1]:+.2f} a {dif_a[2]:+.2f}); pozos fuera por bloque: {n_fuera}")
    n_b = [int(res[b][0]["n_tratados"]) for b, _ in bandas]
    est_b = [float(res[b][0]["est"]) for b, _ in bandas]
    v_dist = veredicto_gradiente(n_b, est_b, dif_w[1], dif_w[2])
    trat_dist = np.concatenate([_tratados(c) for _, c in bandas])
    motivo_dist = (f"dW por banda {est_b[0]:+.2f} (0 a 0,5 km), {est_b[1]:+.2f} (0,5 a 1 km), {est_b[2]:+.2f} (1 a 2 km); "
                   f"cercana menos lejana {dif_w[0]:+.2f} (IC {dif_w[1]:+.2f} a {dif_w[2]:+.2f}); tratados {n_b}")
    fila_dist = ("D4_distancia", v_dist, dif_w[0], dif_w[1], dif_w[2], int(sum(n_b)), _n_bloques(D, trat_dist), None,
                 motivo_dist)
    print(f"D4: veredicto distancia {v_dist}; {motivo_dist}")

    # ---- tamano: agua de fractura del hijo y longitud de rama, en terciles entre los tratados de D2 con dW
    vt_w, _ = _valores_agua(D, cel_pri, 0)
    tr, hijo = [], []
    for ce, v in zip(cel_pri, vt_w):
        ok = ~np.isnan(v)
        tr.append(ce["tratados"][ok])
        hijo.append(D["hijo_min"][ce["tratados"][ok], ce["g"] - D["t0"]])
    tr = np.concatenate(tr) if tr else np.zeros(0, dtype=np.int64)
    hijo = np.concatenate(hijo) if hijo else np.zeros(0, dtype=np.int64)
    frac = {int(p): (a, r) for p, a, r in con.execute(
        "select pozo_id, agua_m3, rama_horizontal_m from dim_fractura_pozo").fetchall()}
    agua = np.array([(frac.get(int(h), (None, None))[0] or 0.0) if h >= 0 else 0.0 for h in hijo], dtype=float)
    rama = np.array([(frac.get(int(h), (None, None))[1] or 0.0) if h >= 0 else 0.0 for h in hijo], dtype=float)
    nombres = ("alto", "medio", "bajo")

    def por_terciles(valores: np.ndarray):
        con_dato = valores > 0
        etiqueta, cortes = _etiquetas_terciles(n, tr[con_dato], valores[con_dato])
        out = {}
        for k, nombre in enumerate(nombres):
            cel = celdas_por_mascara(cel_pri, lambda ce, k=k: etiqueta[ce["tratados"]] == k, fuera)
            out[nombre] = _par(D, bases, cel, W_ext)
        return out, cortes, float(con_dato.sum()) / max(len(tr), 1), int(con_dato.sum())

    ter, cortes, cobertura, n_dato = por_terciles(agua)
    for nombre in nombres:
        for rr, etq in zip(ter[nombre], ("dW", "dA")):
            filas.append(_fila_d4("tamano_agua", nombre, etq, rr))
    filas.append(_fila_dif("tamano_agua", "alto_menos_bajo", "dW", ter["alto"][0], ter["bajo"][0]))
    filas.append(_fila_dif("tamano_agua", "alto_menos_bajo", "dA", ter["alto"][1], ter["bajo"][1]))
    filas.append(("tamano_agua", "cobertura", "cuenta", n_dato, None, cobertura, None, None))
    d_tw = _dif(ter["alto"][0], ter["bajo"][0])
    d_ta = _dif(ter["alto"][1], ter["bajo"][1])
    for nombre in nombres:
        w_, a_ = ter[nombre]
        print(f"D4 tamano (agua del hijo) {nombre}: dW = {w_['est']:+.2f} (IC {w_['ic_bajo']:+.2f} a {w_['ic_alto']:+.2f}), "
              f"dA = {a_['est']:+.2f} (IC {a_['ic_bajo']:+.2f} a {a_['ic_alto']:+.2f}), tratados {w_['n_tratados']}")
    print(f"D4 tamano alto menos bajo: dW = {d_tw[0]:+.2f} (IC {d_tw[1]:+.2f} a {d_tw[2]:+.2f}), dA = {d_ta[0]:+.2f} "
          f"(IC {d_ta[1]:+.2f} a {d_ta[2]:+.2f}); cortes {cortes[0]:.0f} y {cortes[1]:.0f} m3; cobertura {cobertura:.3f} "
          f"({n_dato} de {len(tr)})")
    n_t = [int(ter[b][0]["n_tratados"]) for b in nombres]
    est_t = [float(ter[b][0]["est"]) for b in nombres]
    v_tam = veredicto_gradiente(n_t, est_t, d_tw[1], d_tw[2], cobertura)
    trat_tam = tr[agua > 0]
    motivo_tam = (f"dW por tercil de agua del hijo {est_t[0]:+.2f} (alto), {est_t[1]:+.2f} (medio), {est_t[2]:+.2f} (bajo); "
                  f"alto menos bajo {d_tw[0]:+.2f} (IC {d_tw[1]:+.2f} a {d_tw[2]:+.2f}); cobertura {cobertura:.3f}; "
                  f"tratados {n_t}")
    fila_tam = ("D4_tamano", v_tam, d_tw[0], d_tw[1], d_tw[2], int(sum(n_t)), _n_bloques(D, trat_tam), None, motivo_tam)
    print(f"D4: veredicto tamano {v_tam}; {motivo_tam}")

    # ---- longitud de rama (sin veredicto)
    ram, cortes_r, cob_r, n_r = por_terciles(rama)
    for nombre in nombres:
        filas.append(_fila_d4("rama", nombre, "dW", ram[nombre][0]))
    filas.append(_fila_dif("rama", "alto_menos_bajo", "dW", ram["alto"][0], ram["bajo"][0]))
    filas.append(("rama", "cobertura", "cuenta", n_r, None, cob_r, None, None))
    d_r = _dif(ram["alto"][0], ram["bajo"][0])
    print(f"D4 rama alto menos bajo: dW = {d_r[0]:+.2f} (IC {d_r[1]:+.2f} a {d_r[2]:+.2f}); cobertura {cob_r:.3f}")

    _escribir(con, "mart_causal_profundo_d4", COLS_D4, filas)
    return [fila_dist, fila_tam]


# ---- D5: forma en el tiempo

COLS_D5 = [("e", "integer"), ("resultado", "varchar"), ("n_tratados", "integer"), ("n_controles", "integer"),
           ("valor", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]


def _dw_mes(D: dict, pozos: np.ndarray, g: int, e: int, base_w: np.ndarray) -> np.ndarray:
    """dW de un solo mes: W(g + e) menos la base de W de D2, en fraccion; nan si falta algo o la columna sale del panel."""
    pozos = np.asarray(pozos, dtype=np.int64)
    out = np.full(len(pozos), np.nan)
    if not len(pozos):
        return out
    col, col_e = g - D["t0"], g + e - D["t0"]
    if col < 0 or col >= D["T"] or col_e < 0 or col_e >= D["T"]:
        return out
    w, b = D["w"][pozos, col_e], base_w[pozos, col]
    return np.where(np.isnan(w) | np.isnan(b), np.nan, w - b)


def valores_dw_mes(D: dict, celdas_: list[dict], e: int, base_w: np.ndarray | None = None):
    """dW del mes e de tratados y controles de cada celda."""
    if base_w is None:
        base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    vt, vc = [], []
    for ce in celdas_:
        vt.append(_dw_mes(D, ce["tratados"], ce["g"], e, base_w))
        vc.append(_dw_mes(D, ce["controles"], ce["g"], e, base_w))
    return vt, vc


def media_resultados(res: list[dict]) -> dict:
    """Media de varias estimaciones: el punto y los sorteos, sorteo por sorteo; IC con causal._ic; n = el menor n."""
    est = float(np.mean([r["est"] for r in res]))
    vals = np.mean([np.asarray(r["vals"], dtype=float) for r in res], axis=0)
    bajo, alto = _ic(vals)
    return {"est": est, "vals": vals, "ic_bajo": float(bajo), "ic_alto": float(alto),
            "n_tratados": int(min(r["n_tratados"] for r in res))}


def _d5(con, D: dict, coh: dict, bases: dict, W: np.ndarray, wells: np.ndarray) -> tuple:
    """D5: forma en el tiempo. Escribe mart_causal_profundo_d5 y devuelve la fila de veredicto."""
    W5, fuera5 = extender_pesos(D, W, wells)
    cel_bruto = celdas(D, coh, H_D5, False)
    pozos = np.unique(np.concatenate([_tratados(cel_bruto)] + [ce["controles"] for ce in cel_bruto])) \
        if cel_bruto else np.zeros(0, dtype=np.int64)
    n_fuera = int(fuera5[pozos].sum())
    cel5 = celdas_por_mascara(cel_bruto, lambda ce: np.ones(len(ce["tratados"]), dtype=bool), fuera5)
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    filas, dw = [], {}
    for e in E_D5:
        vt, vc = valores_dw_mes(D, cel5, e, base_w)
        dw[e] = estimar_valores(D, cel5, W5, vt, vc)
        da = estimar(D, cel5, W5, D["A"], bases["A"], (e, e))
        do = estimar(D, cel5, W5, D["O"], bases["O"], (e, e))
        for nombre, rr in (("dW", dw[e]), ("dA", da), ("dO", do)):
            filas.append((int(e), nombre, int(rr["n_tratados"]), int(rr["n_controles"]), float(rr["est"]),
                          float(rr["ic_bajo"]), float(rr["ic_alto"])))
        print(f"D5 e={e:+d}: dW = {dw[e]['est']:+.2f} (IC {dw[e]['ic_bajo']:+.2f} a {dw[e]['ic_alto']:+.2f}), "
              f"tratados {dw[e]['n_tratados']}")
    tarde = media_resultados([dw[e] for e in range(TRAMO_TARDE[0], TRAMO_TARDE[1] + 1)])
    temprano = float(np.mean([dw[0]["est"], dw[1]["est"]]))
    primer = next((e for e in E_D5 if e >= 0 and dw[e]["ic_bajo"] > 0), None)
    trat = _tratados(cel5)
    otro = 0
    for ce in cel5:
        otro += int(np.sum(_ventana(D, ce["g"] + 2, ce["g"] + 12, wells=ce["tratados"]) > 0))
    n_trat = len(trat)
    v = veredicto_forma(tarde["n_tratados"], tarde["ic_bajo"], tarde["ic_alto"], temprano)
    filas += [(None, "dW_tarde", tarde["n_tratados"], None, tarde["est"], tarde["ic_bajo"], tarde["ic_alto"]),
              (None, "dW_temprano", None, None, temprano, None, None),
              (None, "primer_mes_ic_sobre_cero", None, None, None if primer is None else float(primer), None, None),
              (None, "otro_golpe_2_12", otro, None, otro / max(n_trat, 1), None, None),
              (None, "fuera", None, None, float(n_fuera), None, None)]
    _escribir(con, "mart_causal_profundo_d5", COLS_D5, filas)
    motivo = (f"media de dW en {TRAMO_TARDE[0]} a {TRAMO_TARDE[1]} meses {tarde['est']:+.2f} "
              f"(IC {tarde['ic_bajo']:+.2f} a {tarde['ic_alto']:+.2f}); dW de 0 y 1 {temprano:+.2f}; "
              f"primer mes con IC sobre cero {primer if primer is not None else 'ninguno'}; "
              f"tratados con otro golpe a 2 km en 2 a 12: {otro} de {n_trat}; pozos fuera por bloque {n_fuera}")
    print(f"D5: veredicto {v}; {motivo}")
    fila = ("D5", v, tarde["est"], tarde["ic_bajo"], tarde["ic_alto"], tarde["n_tratados"], _n_bloques(D, trat), None,
            motivo)
    return fila


# ---- D6: donde se sostiene

COLS_D6 = [("corte", "varchar"), ("grupo", "varchar"), ("n_tratados", "integer"), ("n_controles", "integer"),
           ("valor", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
ETIQUETAS_EDAD = ("6-11", "12-23", "24-47", "48+")


def _periodo(g: int) -> str:
    """Etiqueta del periodo del mes g (indice absoluto de mes; el anio es g // 12)."""
    anio = int(g) // 12
    for (a, b), nombre in zip(PERIODOS, ("hasta 2018", "2019-2021", "2022 en adelante")):
        if (a is None or anio >= a) and (b is None or anio <= b):
            return nombre
    return "sin periodo"


def _fila_d6(corte: str, grupo: str, rr: dict | None) -> tuple:
    if rr is None:
        return (corte, grupo, 0, 0, None, None, None)
    return (corte, grupo, int(rr["n_tratados"]), int(rr["n_controles"]), float(rr["est"]), float(rr["ic_bajo"]),
            float(rr["ic_alto"]))


def _d6(con, D: dict, W: np.ndarray, cel_pri: list[dict]) -> tuple:
    """D6: donde se sostiene dW de D2. Devuelve las filas del mart y la fila de veredicto."""
    def est(cel):
        if not cel:
            return None
        vt, vc = _valores_agua(D, cel, 0)
        return estimar_valores(D, cel, W, vt, vc)

    filas = []

    def agregar(corte, grupo, cel):
        rr = est(cel)
        filas.append(_fila_d6(corte, grupo, rr))
        txt = "sin tratados" if rr is None else (f"dW = {rr['est']:+.2f} (IC {rr['ic_bajo']:+.2f} a {rr['ic_alto']:+.2f}), "
                                                f"tratados {rr['n_tratados']}")
        print(f"D6 {corte} {grupo}: {txt}")
        return rr

    todos = agregar("todos", "todos", cel_pri)
    trat = _tratados(cel_pri)
    ops, cuentas = np.unique(D["operador"][trat].astype(str), return_counts=True) if len(trat) else ([], [])
    sin_op = {}
    for op, c in zip(ops, cuentas):
        if c < MIN_TRATADOS_OPERADOR:
            continue
        agregar("operador", str(op), celdas_por_mascara(cel_pri, lambda ce, op=op: D["operador"][ce["tratados"]] == op))
        sin_op[str(op)] = agregar("sin_operador", str(op), _celdas_sin_operador(D, cel_pri, op))
    for k, nombre in enumerate(ETIQUETAS_EDAD):
        agregar("edad", nombre, [ce for ce in cel_pri if ce["grupo"] == k])
    for (a, b), nombre in zip(PERIODOS, ("hasta 2018", "2019-2021", "2022 en adelante")):
        agregar("periodo", nombre, celdas_por_mascara(cel_pri, lambda ce, n=nombre: np.full(len(ce["tratados"]), _periodo(ce["g"]) == n)))
    area_de = {int(p): a for p, a in con.execute("select pozo_id, coalesce(nullif(trim(area), ''), 'Sin dato') from dim_pozo").fetchall()}
    area = np.array([area_de.get(int(p), "Sin dato") for p in D["pozo_id"]], dtype=object)
    areas, cuentas_a = np.unique(area[trat].astype(str), return_counts=True) if len(trat) else ([], [])
    for ar, c in zip(areas, cuentas_a):
        if c >= MIN_TRATADOS_OPERADOR:
            agregar("area", str(ar), celdas_por_mascara(cel_pri, lambda ce, ar=ar: area[ce["tratados"]] == ar))
    bajos = {op: (float(r["ic_bajo"]) if r is not None else float("nan")) for op, r in sin_op.items()}
    v, malos = veredicto_general(bajos)
    peor = min((r for r in sin_op.values() if r is not None), key=lambda r: r["ic_bajo"], default=None)
    lista = "; ".join(f"sin {op} {r['est']:+.2f} (IC {r['ic_bajo']:+.2f} a {r['ic_alto']:+.2f})"
                      for op, r in sin_op.items() if r is not None)
    motivo = f"dW {lista}" + (f"; depende de: {', '.join(malos)}" if malos else "")
    print(f"D6: veredicto {v}; {motivo}")
    fila = ("D6", v, None if peor is None else float(peor["est"]), None if peor is None else float(peor["ic_bajo"]),
            None if peor is None else float(peor["ic_alto"]), int(todos["n_tratados"]) if todos else 0,
            _n_bloques(D, trat), None, motivo)
    _escribir(con, "mart_causal_profundo_d6", COLS_D6, filas)
    return fila


def _d3(D: dict, W: np.ndarray, bases: dict, cel_pri: list[dict], cel_ff: list[dict], cel_fd: list[dict],
        cel_nt: list[dict]) -> dict:
    """D3: los volumenes de agua y de petroleo con sus placebos, y el veredicto.

    Devuelve los resultados (dA, dO, dA_pd, dO_pd, dL, el puente con D2 y los placebos), que placebos rompieron,
    la cantidad de tratados, la de bloques y el veredicto. Lo usan Vaca Muerta (main) y Colorado (_d7)."""
    vt_a, vc_a = valores_volumen(D, cel_pri, D["A"], bases["A"], VENTANA_D3)
    vt_o, vc_o = valores_volumen(D, cel_pri, D["O"], bases["O"], VENTANA_D3)
    res_a = estimar_valores(D, cel_pri, W, vt_a, vc_a)
    res_o = estimar_valores(D, cel_pri, W, vt_o, vc_o)
    res_a_pd = estimar(D, cel_pri, W, D["A_pd"], bases["A_pd"], VENTANA_D3)
    res_o_pd = estimar(D, cel_pri, W, D["O_pd"], bases["O_pd"], VENTANA_D3)
    res_l = estimar_valores(D, cel_pri, W, _suma(vt_a, vt_o), _suma(vc_a, vc_o))

    # puente con D2 (sin veredicto)
    vt_w, vc_w = valores_dw_media(D, cel_pri)
    res_w = estimar_valores(D, cel_pri, W, vt_w, vc_w)

    # placebos de dA y de dA_pd, y placebo de nunca tratados sobre el dW de D2
    res_prev = estimar(D, cel_pri, W, D["A"], bases["A"], VENTANA_PREVIA_D3)
    res_ff = estimar(D, cel_ff, W, D["A"], bases["A"], VENTANA_D3)
    res_fd = estimar(D, cel_fd, W, D["A"], bases["A"], VENTANA_D3)
    res_nt = estimar(D, cel_nt, W, D["A"], bases["A"], VENTANA_D3)
    res_prev_pd = estimar(D, cel_pri, W, D["A_pd"], bases["A_pd"], VENTANA_PREVIA_D3)
    res_nt_pd = estimar(D, cel_nt, W, D["A_pd"], bases["A_pd"], VENTANA_D3)
    vt_nt_w, vc_nt_w = _valores_agua(D, cel_nt, 0)
    res_nt_w = estimar_valores(D, cel_nt, W, vt_nt_w, vc_nt_w)

    rotos = [nombre for nombre, rr in (("previo", res_prev), ("fecha_falsa", res_ff),
                                        ("distancia_falsa", res_fd), ("nunca_tratados", res_nt))
              if _rompe(rr, UMBRAL_ROTURA_VOLUMEN)]
    rotos_pd = [nombre for nombre, rr in (("previo", res_prev_pd), ("nunca_tratados", res_nt_pd))
                if _rompe(rr, UMBRAL_ROTURA_VOLUMEN)]

    trat_d3 = np.concatenate([ce["tratados"] for ce in cel_pri]) if cel_pri else np.zeros(0, dtype=np.int64)
    n_tratados = int(res_a["n_tratados"])
    n_bloques = _n_bloques(D, trat_d3)
    v_d3 = veredicto_d3(n_tratados, n_bloques, bool(rotos), (float(res_a["ic_bajo"]), float(res_a["ic_alto"])),
                        (float(res_a_pd["ic_bajo"]), float(res_a_pd["ic_alto"])),
                        (float(res_o["ic_bajo"]), float(res_o["ic_alto"])), bool(rotos_pd))
    return {"res_a": res_a, "res_o": res_o, "res_a_pd": res_a_pd, "res_o_pd": res_o_pd, "res_l": res_l,
            "res_w": res_w, "res_prev": res_prev, "res_ff": res_ff, "res_fd": res_fd, "res_nt": res_nt,
            "res_prev_pd": res_prev_pd, "res_nt_pd": res_nt_pd, "res_nt_w": res_nt_w,
            "rotos": rotos, "rotos_pd": rotos_pd, "n_tratados": n_tratados, "n_bloques": n_bloques, "v_d3": v_d3}


def _matriz_agua(con, D: dict) -> np.ndarray:
    """Verdad por pozo y mes: la fila de produccion trae agua_m3 y dias_efectivos (no nulos)."""
    n, T = D["n"], D["T"]
    ok = np.zeros((n, T), dtype=bool)
    pos = {int(p): i for i, p in enumerate(D["pozo_id"])}
    for pid, mes, ag, de in con.execute("select pozo_id, mes, agua_m3, dias_efectivos from fct_produccion").fetchall():
        i = pos.get(int(pid))
        j = _mes(mes) - D["t0"]
        if i is None or j < 0 or j >= T:
            continue
        ok[i, j] = ag is not None and de is not None
    return ok


def cobertura_agua(D: dict, celdas_: list[dict], ok: np.ndarray) -> float:
    """Parte de los meses base de los tratados de D2 que tienen fila de produccion con agua y dias efectivos.

    La base de D2 son los meses -6 a -4 del mes de la fractura (causal._panel_base). `ok` es la matriz de verdad
    por pozo y mes que arma _matriz_agua. Da nan si no hay ningun mes base dentro del panel."""
    total = 0
    cub = 0
    for ce in celdas_:
        trat = np.asarray(ce["tratados"], dtype=np.int64)
        if not len(trat):
            continue
        for e in (-6, -5, -4):
            col = ce["g"] + e - D["t0"]
            if col < 0 or col >= D["T"]:
                continue
            total += len(trat)
            cub += int(ok[trat, col].sum())
    return float(cub) / total if total else float("nan")


def _fila_d7(resultado: str, rr: dict, roto: bool, veredicto: str = "") -> tuple:
    """Fila del mart de D7: la magnitud, su veredicto y si su placebo rompe."""
    return (resultado, int(rr["n_tratados"]), float(rr["est"]), float(rr["ic_bajo"]), float(rr["ic_alto"]), roto,
            veredicto)


def _d7(con_vm, con_co) -> None:
    """D7: el mismo diseno de D2 y D3 sobre Colorado, con la compuerta de cobertura de agua.

    El warehouse de Colorado se abre solo lectura (las entradas que arma pipeline.replicacion son tablas
    temporales); las tablas se escriben en el warehouse de Vaca Muerta."""
    from pipeline import replicacion
    from pipeline.causal import _num

    replicacion.preparar(con_co)
    con_co.execute("create or replace temp table mart_par_rama (hijo bigint, padre bigint, posicion varchar)")

    D = cargar(con_co)
    D.update(cargar_volumenes(con_co, D))
    bases = preparar_bases(D)
    ok = _matriz_agua(con_co, D)

    coh = cohortes(D)
    rng = np.random.default_rng(SEMILLA_CAUSAL)
    cel_pri = celdas(D, coh, H_CORTO, False)
    trat_ff, g_ff = _cohorte_falsa_fecha(D, coh)
    cel_ff = celdas(D, coh, H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = _cohorte_falsa_distancia(D, coh, H_CORTO)
    cel_fd = celdas(D, coh, H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = _cohorte_nunca_tratados(D, coh)
    cel_nt = celdas(D, coh, H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    # los mismos seis grupos de causal.main, para que los sorteos de W sigan la misma receta
    cel_s1 = celdas(D, coh, H_CORTO, True)
    cel_d1b = celdas_d1b(D, coh)
    wells = []
    for grupo in (cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b):
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = _pesos_bloques(D, wells, REPS, rng)

    cobertura = cobertura_agua(D, cel_pri, ok)
    n_trat = int(sum(len(ce["tratados"]) for ce in cel_pri))
    fila_vm = con_vm.execute("select veredicto from mart_causal_profundo_veredicto where diseno = 'D3'").fetchone()
    if fila_vm is None:
        raise RuntimeError("D7 compara con el D3 de Vaca Muerta: correr antes `python -m pipeline.causal_profundo`")
    v_d3_vm = str(fila_vm[0])

    nan = float("nan")
    filas = [("cobertura_agua", n_trat, cobertura, nan, nan, False, "")]
    if np.isnan(cobertura) or cobertura < COBERTURA_MIN:
        # la compuerta de la regla: sin el dato de agua de los meses base no se calculan D2 ni D3; sin ningun mes base
        # (ningun tratado de D2 en el panel) no hay muestra
        v_d7 = V_SIN_MUESTRA if np.isnan(cobertura) else veredicto_colorado(cobertura, V_SIN_MUESTRA, V_SIN_MUESTRA,
                                                                             v_d3_vm)
        filas.append(("D7", 0, nan, nan, nan, False, v_d7))
        print(f"D7: cobertura de agua de los meses base: {cobertura:.4f} ({_num(100 * cobertura)}%); "
              f"la compuerta pide {COBERTURA_MIN:.0%}: no se calculan D2 ni D3")
        print(f"D7: veredicto {v_d7}")
    else:
        d2 = diseno_d2(D, W, cel_pri, cel_ff, cel_fd)
        cierre = placebo_cierre(D, W)
        rotos2 = [nombre for nombre, rr in (("previo", d2["previo"]), ("fecha_falsa", d2["fecha_falsa"]),
                                              ("distancia_falsa", d2["distancia_falsa"]))
                  if _rompe(rr, UMBRAL_ROTURA_AGUA)]
        v_d2 = veredicto_d2(int(d2["r"]["n_tratados"]), bool(rotos2), float(cierre["est"]), float(cierre["ic_bajo"]),
                            float(cierre["ic_alto"]), float(d2["r"]["est"]), float(d2["r"]["ic_bajo"]))
        d3 = _d3(D, W, bases, cel_pri, cel_ff, cel_fd, cel_nt)
        v_d3 = d3["v_d3"]
        v_d7 = veredicto_colorado(cobertura, v_d2, v_d3, v_d3_vm)

        filas.append(_fila_d7("dW", d2["r"], False, v_d2))
        filas.append(_fila_d7("placebo_previo_dW", d2["previo"], _rompe(d2["previo"], UMBRAL_ROTURA_AGUA)))
        filas.append(_fila_d7("placebo_fecha_falsa_dW", d2["fecha_falsa"], _rompe(d2["fecha_falsa"], UMBRAL_ROTURA_AGUA)))
        filas.append(_fila_d7("placebo_distancia_falsa_dW", d2["distancia_falsa"],
                              _rompe(d2["distancia_falsa"], UMBRAL_ROTURA_AGUA)))
        # el cierre rompe con la regla de causal.veredicto_d2: IC sin cero y al menos FRACCION_CIERRE del dW
        est_c, bajo_c, alto_c, att = (float(cierre["est"]), float(cierre["ic_bajo"]), float(cierre["ic_alto"]),
                                      float(d2["r"]["est"]))
        cierre_rompe = bool((bajo_c > 0 or alto_c < 0) and att > 0 and est_c >= FRACCION_CIERRE * att)
        filas.append(_fila_d7("placebo_cierre", cierre, cierre_rompe))
        filas.append(_fila_d7("dA", d3["res_a"], False, v_d3))
        filas.append(_fila_d7("dO", d3["res_o"], False, v_d3))
        filas.append(_fila_d7("dA_pd", d3["res_a_pd"], False, v_d3))
        for nombre, clave in (("previo", "res_prev"), ("fecha_falsa", "res_ff"), ("distancia_falsa", "res_fd"),
                              ("nunca_tratados", "res_nt")):
            filas.append(_fila_d7(f"placebo_{nombre}_dA", d3[clave], nombre in d3["rotos"]))
        for nombre, clave in (("previo", "res_prev_pd"), ("nunca_tratados", "res_nt_pd")):
            filas.append(_fila_d7(f"placebo_{nombre}_dA_pd", d3[clave], nombre in d3["rotos_pd"]))
        filas.append(("D7", int(d3["n_tratados"]), nan, nan, nan, False, v_d7))

        print(f"D7: cobertura de agua de los meses base: {cobertura:.4f} ({_num(100 * cobertura)}%); "
              f"la compuerta pide {COBERTURA_MIN:.0%}")
        print(f"D7: D2 en Colorado: dW = {d2['r']['est']:+.2f} puntos porcentuales (IC 95%: {d2['r']['ic_bajo']:+.2f} a "
              f"{d2['r']['ic_alto']:+.2f}), {int(d2['r']['n_tratados'])} tratados; veredicto {v_d2}")
        print(f"D7: D3 en Colorado: dA = {d3['res_a']['est']:+.2f} puntos del liquido base (IC 95%: "
              f"{d3['res_a']['ic_bajo']:+.2f} a {d3['res_a']['ic_alto']:+.2f}), {d3['n_tratados']} tratados; "
              f"veredicto {v_d3}; en Vaca Muerta {v_d3_vm}")
        print(f"D7: veredicto {v_d7}")

    con = con_vm    # el linaje busca la llamada _escribir(con, "mart_...")
    _escribir(con, "mart_causal_profundo_d7", COLS_D7, filas)


def main(path=DATA / "warehouse.duckdb") -> None:
    """Corre D3: el volumen de agua y el de petroleo por dia, con sus placebos, y escribe sus marts."""
    con = duckdb.connect(str(path))
    D = cargar(con)
    D.update(cargar_volumenes(con, D))
    bases = preparar_bases(D)

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

    # control: D2 recalculado con los mismos sorteos tiene que dar lo que dice mart_causal_veredicto
    d2_todo = diseno_d2(D, W, cel_pri, cel_ff, cel_fd)
    d2 = d2_todo["r"]
    fila_d2 = con.execute("select valor, ic_bajo, ic_alto from mart_causal_veredicto where diseno = 'D2'").fetchone()
    if fila_d2 is None:
        print(f"control D2: no hay fila D2 en mart_causal_veredicto; recalculado {d2['est']:.6f} "
              f"({d2['ic_bajo']:.6f} a {d2['ic_alto']:.6f})")
    else:
        dif = max(abs(float(d2["est"]) - float(fila_d2[0])), abs(float(d2["ic_bajo"]) - float(fila_d2[1])),
                  abs(float(d2["ic_alto"]) - float(fila_d2[2])))
        print(f"control D2: recalculado {d2['est']:.6f} ({d2['ic_bajo']:.6f} a {d2['ic_alto']:.6f}); "
              f"mart_causal_veredicto {float(fila_d2[0]):.6f} ({float(fila_d2[1]):.6f} a {float(fila_d2[2]):.6f}); "
              f"diferencia maxima {dif:.3e}")
        if dif > 1e-6:
            raise RuntimeError(f"el control D2 no coincide con mart_causal_veredicto: diferencia maxima {dif:.3e}")

    # D3 principal
    d3 = _d3(D, W, bases, cel_pri, cel_ff, cel_fd, cel_nt)
    res_a, res_o, res_a_pd = d3["res_a"], d3["res_o"], d3["res_a_pd"]
    res_o_pd, res_l, res_w = d3["res_o_pd"], d3["res_l"], d3["res_w"]
    res_prev, res_ff, res_fd, res_nt = d3["res_prev"], d3["res_ff"], d3["res_fd"], d3["res_nt"]
    res_prev_pd, res_nt_pd, res_nt_w = d3["res_prev_pd"], d3["res_nt_pd"], d3["res_nt_w"]
    rotos, rotos_pd = d3["rotos"], d3["rotos_pd"]
    n_tratados, n_bloques, v_d3 = d3["n_tratados"], d3["n_bloques"], d3["v_d3"]

    # ---- marts
    filas = []
    for nombre, rr in (("dA", res_a), ("dO", res_o), ("dA_pd", res_a_pd), ("dO_pd", res_o_pd), ("dL", res_l),
                       ("dW_media", res_w)):
        filas.append((nombre,) + _fila(rr, None))
    for nombre, rr, umbral in (("placebo_previo_dA", res_prev, UMBRAL_ROTURA_VOLUMEN),
                                ("placebo_fecha_falsa_dA", res_ff, UMBRAL_ROTURA_VOLUMEN),
                                ("placebo_distancia_falsa_dA", res_fd, UMBRAL_ROTURA_VOLUMEN),
                                ("placebo_nunca_tratados_dA", res_nt, UMBRAL_ROTURA_VOLUMEN),
                                ("placebo_previo_dA_pd", res_prev_pd, UMBRAL_ROTURA_VOLUMEN),
                                ("placebo_nunca_tratados_dA_pd", res_nt_pd, UMBRAL_ROTURA_VOLUMEN),
                                ("placebo_nunca_tratados_dW", res_nt_w, UMBRAL_ROTURA_AGUA)):
        filas.append((nombre,) + _fila(rr, _rompe(rr, umbral)))
    _escribir(con, "mart_causal_profundo_d3", COLS_D3, filas)

    motivo = (f"dA {res_a['est']:+.2f} puntos del liquido base (IC {res_a['ic_bajo']:+.2f} a {res_a['ic_alto']:+.2f}); "
              f"dO {res_o['est']:+.2f}; dA_pd {res_a_pd['est']:+.2f}; "
              f"placebos de dA rotos: {', '.join(rotos) if rotos else 'ninguno'}; "
              f"placebos de dA_pd rotos: {', '.join(rotos_pd) if rotos_pd else 'ninguno'}")
    fila_v3 = ("D3", v_d3, float(res_a["est"]), float(res_a["ic_bajo"]), float(res_a["ic_alto"]), n_tratados,
               n_bloques, bool(d2_gana_nombre(v_d3)), motivo)

    print(f"D3: dA = {res_a['est']:+.2f} puntos del liquido base (IC 95%: {res_a['ic_bajo']:+.2f} a "
          f"{res_a['ic_alto']:+.2f}), tratados {n_tratados}, bloques {n_bloques}")
    print(f"D3: dO = {res_o['est']:+.2f} puntos (IC 95%: {res_o['ic_bajo']:+.2f} a {res_o['ic_alto']:+.2f})")
    print(f"D3: dA_pd = {res_a_pd['est']:+.2f} puntos (IC 95%: {res_a_pd['ic_bajo']:+.2f} a "
          f"{res_a_pd['ic_alto']:+.2f})")
    print(f"D3: veredicto {v_d3}; {motivo}")

    filas_v4 = _d4(con, D, coh, bases, W, wells, cel_pri, d2_todo, res_fd)
    fila_v5 = _d5(con, D, coh, bases, W, wells)
    fila_v6 = _d6(con, D, W, cel_pri)
    _escribir(con, "mart_causal_profundo_veredicto", COLS_VEREDICTO, [fila_v3] + filas_v4 + [fila_v5, fila_v6])
    con.close()


# ------------------------------------------------------------------ pagina

COMMIT_REGLA = "74e3975"

# Marca de cada veredicto de este modulo (sistema Estepa, como causal.MARCA_VEREDICTO): lleno sostiene, medio sostiene con
# una condicion, vacio no sostiene. Va antes de las palabras, que no cambian.
MARCA = {
    V_D3_ENTRA: "●", V_GRADIENTE: "●", V_PERSISTE: "●", V_GENERAL: "●", V_REPITE: "●",
    V_D3_ENTRA_PD: "◐", V_DEPENDE: "◐", V_REPITE_PARTE: "◐", V_NO_FIRME: "◐",
    V_D3_PETROLEO: "○", V_SIN_GRADIENTE: "○", V_SIN_DATO: "○", V_CURA: "○", V_SIN_DATO_AGUA: "○", V_NO_REPITE: "○",
    V_PLACEBO: "○", V_SIN_MUESTRA: "○",
}

NOMBRE_D3 = {
    "dA": "Agua por día calendario (decide)",
    "dO": "Petróleo por día calendario",
    "dA_pd": "Agua por día producido",
    "dO_pd": "Petróleo por día producido",
    "dL": "Líquido por día calendario (agua más petróleo)",
}

NOMBRE_PLACEBO_D3 = {
    "placebo_previo_dA": "Previo (meses -2 y -1), agua por día calendario",
    "placebo_fecha_falsa_dA": "Fecha falsa (12 meses antes), agua por día calendario",
    "placebo_distancia_falsa_dA": "Distancia falsa (primer hijo a 3 a 5 km), agua por día calendario",
    "placebo_nunca_tratados_dA": "Nunca tratados (fechas sorteadas), agua por día calendario",
    "placebo_previo_dA_pd": "Previo (meses -2 y -1), agua por día producido",
    "placebo_nunca_tratados_dA_pd": "Nunca tratados (fechas sorteadas), agua por día producido",
}

TEXTO_D3 = {
    V_D3_ENTRA: "El agua por día calendario del padre sube aunque el padre pierda días: un cierre no puede subirla, así "
                "que llega agua. El corte de agua de D2 sube porque entra agua, no solo porque cae el petróleo.",
    V_D3_ENTRA_PD: "En los días que el padre produce, sale más agua por día: entra agua. Por día calendario la suba no "
                   "alcanza a separarse de cero; no se midió si es porque ese mes el padre produce menos días. El corte de agua de D2 sube porque entra agua en los días producidos, no solo porque cae el "
                   "petróleo.",
    V_D3_PETROLEO: "El agua del padre no sube (la cota está en el IC alto) y su petróleo cae: el corte de agua de D2 sube "
                   "porque cae el petróleo con el agua quieta, no porque entre agua.",
    V_NO_FIRME: "El volumen de agua no separa las dos lecturas: el corte sube, pero no se puede decir si entra agua o si "
                "cae el petróleo.",
    V_SIN_MUESTRA: "La muestra no alcanza el mínimo que fijó la regla; las cifras se publican pero no deciden.",
    V_PLACEBO: "Un placebo da una suba de agua donde no debería haberla: el diseño no separa la fractura de la selección "
               "en el volumen de agua.",
}


def _ent(n: int) -> str:
    """Entero con punto de miles."""
    return f"{int(n):,}".replace(",", ".")


def _fila_d3(con, cantidad: str):
    return con.execute("select n_tratados, n_controles, valor, ic_bajo, ic_alto, rompe from mart_causal_profundo_d3 "
                       "where cantidad = ?", [cantidad]).fetchone()


def frase_d2(con) -> str | None:
    """Frase que pipeline.causal agrega al resumen de D2 segun el veredicto de D3 (tabla del plan); None sin el mart."""
    from pipeline.causal import _ic_txt, _num
    try:
        v = con.execute("select veredicto, valor, ic_bajo, ic_alto from mart_causal_profundo_veredicto "
                        "where diseno = 'D3'").fetchone()
    except duckdb.Error:
        return None
    if v is None:
        return None
    ver, val, bajo, alto = v
    a_pd, o_pd, nt = _fila_d3(con, "dA_pd"), _fila_d3(con, "dO_pd"), _fila_d3(con, "placebo_nunca_tratados_dW")
    base = f"- {MARCA[ver]} **Debajo del corte de agua (D3, [causal_profundo.md](causal_profundo.md), regla fijada después): {ver}.** "
    if ver == V_D3_ENTRA_PD:
        pet = ("no se separa de cero" if o_pd[3] <= 0 <= o_pd[4] else ("sube" if o_pd[3] > 0 else "baja"))
        txt = (f"En los días que el padre produce, su agua por día sube {_num(a_pd[2])} puntos del líquido de la base "
               f"(IC 95%: {_ic_txt(a_pd[3], a_pd[4])}) y su petróleo por día {pet} ({_num(o_pd[2])}, IC "
               f"{_ic_txt(o_pd[3], o_pd[4])}); el volumen de agua del mes no alcanza a separarse de cero ({_num(val)}, IC "
               f"{_ic_txt(bajo, alto)}), y no se midió si es porque ese mes el padre produce menos días. El nombre \"comunicación física\" se conserva con esa salvedad.")
    elif ver == V_D3_ENTRA:
        txt = (f"El volumen de agua del padre sube {_num(val)} puntos del líquido de la base (IC 95%: {_ic_txt(bajo, alto)}): "
               "el corte sube porque entra agua, no solo porque cae el petróleo.")
    elif ver == V_D3_PETROLEO:
        txt = ("El corte sube porque cae el petróleo del padre; su agua no sube más que la cota "
               f"({_num(alto)} puntos del líquido de la base, IC alto). El nombre \"comunicación física\" de la regla de D2 no "
               "se gana.")
    else:
        txt = ("La suba del corte se sostiene, pero el canal queda sin identificar: el nombre \"comunicación física\" de la "
               "regla de D2 no se gana. " + TEXTO_D3.get(ver, ""))
    txt += (f" El placebo de nunca tratados sobre el corte de agua, que la regla de D2 no tenía, da {_num(nt[2])} puntos "
            f"porcentuales (IC 95%: {_ic_txt(nt[3], nt[4])}): " + ("rompe." if nt[5] else "no rompe."))
    return base + txt


def frase_d4(con) -> str | None:
    """Renglon de D4 para el resumen de causal.md: el veredicto de distancia y el de tamano, dichos tal cual."""
    from pipeline.causal import _ic_txt, _num
    try:
        vd = _veredicto_d4(con, "D4_distancia")
        vt = _veredicto_d4(con, "D4_tamano")
    except duckdb.Error:
        return None
    if vd is None or vt is None:
        return None
    marcas = {MARCA[vd[0]], MARCA[vt[0]]}
    marca = marcas.pop() if len(marcas) == 1 else "◐"   # mixtos: lleno solo si los dos, vacio solo si los dos
    base = f"- {marca} **Dosis (D4, [causal_profundo.md](causal_profundo.md), regla fijada después): "
    if vd[0] == V_SIN_GRADIENTE and vt[0] == V_SIN_GRADIENTE:
        return (base + "sin gradiente.** El corte de agua no sube más cuando el primer golpe está más cerca (la cercana "
                f"menos la lejana da {_num(vd[1])} puntos porcentuales, IC 95%: {_ic_txt(vd[2], vd[3])}) ni cuando el hijo "
                f"usa más agua de fractura (el tercil alto menos el bajo da {_num(vt[1])}, IC 95%: {_ic_txt(vt[2], vt[3])}). "
                "El dato no muestra una distancia ni un tamaño de hijo que concentre el efecto, así que la lectura operativa "
                "que lo pedía no se escribe.")
    return base + f"por distancia, {vd[0]}; por tamaño del hijo, {vt[0]}.** El detalle está en esa página."


COMMIT_REGLA_D4 = "df3a7d6"
NOMBRE_BANDA = {"0-0.5": "0 a 0,5 km", "0.5-1": "0,5 a 1 km", "1-2": "1 a 2 km (cohorte nueva)",
                "3-5": "3 a 5 km (placebo de distancia falsa)", "cercana_menos_lejana": "Cercana menos lejana (0 a 0,5 menos 1 a 2)"}
NOMBRE_TERCIL = {"alto": "Tercil alto", "medio": "Tercil medio", "bajo": "Tercil bajo", "alto_menos_bajo": "Alto menos bajo"}


def _filas_d4(con) -> dict | None:
    """{(corte, banda, resultado): (n_tratados, n_controles, valor, ic_bajo, ic_alto)}; None sin el mart de D4."""
    try:
        filas = con.execute("select corte, banda, resultado, n_tratados, n_controles, valor, ic_bajo, ic_alto "
                            "from mart_causal_profundo_d4").fetchall()
    except duckdb.Error:
        return None
    return {(f[0], f[1], f[2]): f[3:] for f in filas}


def _veredicto_d4(con, diseno: str):
    return con.execute("select veredicto, valor, ic_bajo, ic_alto, n_tratados, n_bloques from mart_causal_profundo_veredicto "
                       "where diseno = ?", [diseno]).fetchone()


COMMIT_REGLA_D56 = "cfd9039"
NOMBRE_CORTE_D6 = {"todos": "Todos (D2)", "operador": "Solo el operador", "sin_operador": "Sin el operador",
                   "edad": "Edad del padre (meses)", "periodo": "Año de la cohorte", "area": "Área"}


def _filas_d5(con) -> dict | None:
    """{(e, resultado): (n_tratados, n_controles, valor, ic_bajo, ic_alto)}; e es None en los resumenes. None sin el mart."""
    try:
        filas = con.execute("select e, resultado, n_tratados, n_controles, valor, ic_bajo, ic_alto "
                            "from mart_causal_profundo_d5").fetchall()
    except duckdb.Error:
        return None
    return {(f[0], f[1]): f[2:] for f in filas}


def _filas_d6(con) -> list[tuple] | None:
    """Filas de D6 en el orden del mart: (corte, grupo, n_tratados, n_controles, valor, ic_bajo, ic_alto)."""
    try:
        return con.execute("select corte, grupo, n_tratados, n_controles, valor, ic_bajo, ic_alto "
                           "from mart_causal_profundo_d6").fetchall()
    except duckdb.Error:
        return None


def _datos_d56(con):
    """(veredicto D5, filas D5, veredicto D6, filas D6) o None si falta algo."""
    try:
        v5, v6 = _veredicto_d4(con, "D5"), _veredicto_d4(con, "D6")
    except duckdb.Error:
        return None
    d5, d6 = _filas_d5(con), _filas_d6(con)
    if v5 is None or v6 is None or d5 is None or d6 is None:
        return None
    return v5, d5, v6, d6


def _depende_de(d6: list[tuple]) -> list[tuple]:
    """Filas "sin el operador" cuyo IC bajo no queda sobre cero (las que hacen "depende de un operador")."""
    return [f for f in d6 if f[0] == "sin_operador" and not (f[5] is not None and f[5] > 0)]


def _ver_d6(v6, d6: list[tuple]) -> str:
    """El veredicto de D6 con el nombre del operador del que depende."""
    malos = _depende_de(d6)
    return v6[0] + (": " + ", ".join(f[1] for f in malos) if v6[0] == V_DEPENDE and malos else "")


def _primer_mes(d5: dict) -> int | None:
    v = d5[(None, "primer_mes_ic_sobre_cero")][2]
    return None if v is None else int(v)


def _texto_d5(v5, d5: dict) -> str:
    """Renglon del resumen de D5, con el veredicto dicho tal cual."""
    from pipeline.causal import _ic_txt, _num
    ver, val, bajo, alto, n_t = v5[0], v5[1], v5[2], v5[3], v5[4]
    temprano = d5[(None, "dW_temprano")][2]
    a, b = TRAMO_TARDE
    cifras = (f"la media de los meses {a} a {b} da {_num(val)} puntos porcentuales (IC 95%: {_ic_txt(bajo, alto)}), "
              f"{_ent(n_t)} tratados, contra {_num(temprano)} de los meses 0 y 1.")
    if ver == V_PERSISTE:
        txt = f"La suba del corte de agua no se cura en {H_D5} meses: " + cifras
    elif ver == V_CURA:
        txt = "La suba del corte de agua se cura: " + cifras
    else:
        txt = "La forma en el tiempo no decide: " + cifras
    p = _primer_mes(d5)
    if p is not None and all(d5[(e, "dW")][3] > 0 for e in E_D5 if e >= p):
        txt += f" El IC queda sobre cero en cada mes desde el mes {p}."
    return txt


def _texto_d6(v6, d6: list[tuple]) -> str:
    """Renglon del resumen de D6: de que operador depende la suba, dicho tal cual."""
    from pipeline.causal import _ic_txt, _num
    if v6[0] == V_GENERAL:
        return "Sin cualquiera de los operadores con el mínimo de tratados, el IC del corte de agua sigue sobre cero."
    todos = next(f for f in d6 if f[0] == "todos")
    malos = _depende_de(d6)
    partes = []
    for f in malos:
        solo = next((g for g in d6 if g[0] == "operador" and g[1] == f[1]), None)
        t = (f"sin los pozos de {f[1]} da {_num(f[4])} puntos porcentuales con un IC que incluye cero (IC 95%: "
             f"{_ic_txt(f[5], f[6])}), sobre {_ent(f[2])} tratados de {_ent(todos[2])}")
        if solo is not None:
            t += f"; los de {f[1]} solos dan {_num(solo[4])} (IC 95%: {_ic_txt(solo[5], solo[6])}), {_ent(solo[2])} tratados"
        partes.append(t)
    nombres = ", ".join(f[1] for f in malos)
    otros = [f[1] for f in d6 if f[0] == "sin_operador" and f not in malos]
    txt = f"La suba del corte de agua de D2 depende de {nombres}: " + "; ".join(partes) + "."
    if len(malos) == 1:
        f = malos[0]
        txt += (f" Sin {f[1]} quedan {_ent(f[2])} tratados y el IC es ancho: el dato no muestra la suba fuera de {f[1]}, "
                "ni la descarta.")
    if otros:
        txt += (" Sacar cualquiera de los otros operadores con el mínimo (" + ", ".join(otros)
                + ") la deja sobre cero.")
    return txt


def frase_d56(con) -> list[str]:
    """Renglones de D5 y D6 para el resumen de causal.md; vacio sin los marts."""
    datos = _datos_d56(con)
    if datos is None:
        return []
    v5, d5, v6, d6 = datos
    enl = "[causal_profundo.md](causal_profundo.md), regla fijada después"
    return [f"- {MARCA[v5[0]]} **Forma en el tiempo (D5, {enl}): {v5[0]}.** {_texto_d5(v5, d5)}",
            f"- {MARCA[v6[0]]} **Dónde se sostiene (D6, {enl}): {_ver_d6(v6, d6)}.** {_texto_d6(v6, d6)}"]


def frase_d7(con) -> str | None:
    """Renglon de D7 (Colorado) para el resumen de causal.md; None sin el mart o si no se calculo D2."""
    from pipeline.causal import _ic_txt, _num
    d7 = _filas_d7(con)
    if d7 is None:
        return None
    ver = d7["D7"][5]
    enl = "[causal_profundo.md](causal_profundo.md), regla fijada después"
    L = f"- {MARCA[ver]} **Otra cuenca (D7, Colorado, {enl}): {ver}.** {TEXTO_D7.get(ver, '')}"
    dw = d7.get("dW")
    if dw is not None:
        L += (f" En Colorado el corte de agua sube {_num(dw[1])} puntos porcentuales (IC 95%: {_ic_txt(dw[2], dw[3])}), "
              f"{_ent(dw[0])} tratados.")
    return L


def frase_lectura_d56(con) -> str | None:
    """Frase que la Lectura de causal.md agrega sobre la suba del corte: D5 y D6 dichos tal cual; None sin los marts."""
    from pipeline.causal import _ic_txt, _num
    datos = _datos_d56(con)
    if datos is None:
        return None
    v5, d5, v6, d6 = datos
    partes = []
    if v5[0] == V_PERSISTE:
        partes.append(f"no se cura en los {H_D5} meses siguientes (D5)")
    elif v5[0] == V_CURA:
        partes.append(f"se cura dentro de los {H_D5} meses siguientes (D5)")
    malos = _depende_de(d6)
    if v6[0] == V_DEPENDE and malos:
        nombres = ", ".join(f[1] for f in malos)
        detalle = "; ".join(f"sin {f[1]} da {_num(f[4])} puntos porcentuales con un IC que incluye cero ({_ic_txt(f[5], f[6])}), "
                            f"sobre {_ent(f[2])} tratados" for f in malos)
        partes.append(f"depende de {nombres} (D6): {detalle}, así que el dato no la muestra fuera de {nombres}")
    elif v6[0] == V_GENERAL:
        partes.append("se sostiene sin cada operador (D6)")
    if not partes:
        return None
    return "Esa suba, con reglas fijadas después en `causal_profundo.md`, " + " y ".join(partes) + "."


def _seccion_d5(v5, d5: dict) -> list[str]:
    from pipeline.causal import _ic_txt, _num
    L = ["", "## D5: forma en el tiempo", ""]
    L.append(f"Las precisiones de D5 y D6 se fijaron en el commit {COMMIT_REGLA_D56}, antes de calcular cualquier cifra de D5 "
             f"o de D6. D5 sigue a los tratados de D2 mes a mes, de {E_D5[0]} a {E_D5[-1]} meses desde la fractura, con "
             f"controles aún no tratados hasta {H_D5} meses después. Cada mes se compara con la base de D2 (meses -6 a -4) y cuenta solo: D2 toma el mayor de dos meses "
             "seguidos, así que su cifra queda más alta que la de cualquier mes de esta tabla sin que eso sea una cura. "
             f"Decide la media del corte de agua en los meses {TRAMO_TARDE[0]} a {TRAMO_TARDE[1]}: \"persiste\" si su IC "
             f"queda entero sobre cero; \"se cura\" si su IC incluye el cero y su extremo alto queda bajo la mitad de la "
             "suba de los meses 0 y 1.")
    L += ["", "| Mes | Tratados | Corte de agua (pp) | IC 95% | Agua por día calendario (puntos) | IC 95% | "
          "Petróleo por día calendario (puntos) | IC 95% |", "| ---: | ---: | ---: | --- | ---: | --- | ---: | --- |"]
    for e in E_D5:
        w, a, o = d5[(e, "dW")], d5[(e, "dA")], d5[(e, "dO")]
        L.append(f"| {e} | {_ent(w[0])} | {_num(w[2])} | {_ic_txt(w[3], w[4])} | {_num(a[2])} | {_ic_txt(a[3], a[4])} | "
                 f"{_num(o[2])} | {_ic_txt(o[3], o[4])} |")
    t, p = d5[(None, "dW_tarde")], _primer_mes(d5)
    otro, fuera = d5[(None, "otro_golpe_2_12")], d5[(None, "fuera")]
    n_trat = round(otro[0] / otro[2]) if otro[2] else 0
    L.append("")
    L.append(f"- Media de los meses {TRAMO_TARDE[0]} a {TRAMO_TARDE[1]}: {_num(t[2])} puntos porcentuales (IC 95%: "
             f"{_ic_txt(t[3], t[4])}), con {_ent(t[0])} tratados (el menor n de esos meses). Media de los meses 0 y 1: "
             f"{_num(d5[(None, 'dW_temprano')][2])}.")
    L.append("- Primer mes con el IC del corte de agua sobre cero: " + ("ninguno." if p is None else f"{p}."))
    L.append(f"- {_ent(otro[0])} de {_ent(n_trat)} tratados ({_num(100 * otro[2], 0)}%) reciben otro golpe a menos de 2 km "
             "en los meses 2 a 12: la serie mide la primera fractura y lo que vino después, no la primera sola.")
    L.append(f"- Pozos fuera de los sorteos porque su bloque de 5 km no tiene ninguno del universo: {_ent(fuera[2])}.")
    previos = [d5[(e, "dW")] for e in E_D5 if e < 0]
    if all(f[3] <= 0 <= f[4] for f in previos):
        L.append(f"- Antes de la fractura (meses {E_D5[0]} a -1) el corte de agua no se separa de cero en ningún mes.")
    o1 = d5[(-1, "dO")]
    w1 = d5[(-1, "dW")]
    if o1[4] < 0 and w1[3] <= 0 <= w1[4]:
        L.append(f"- Sin veredicto, visto después de la regla: el petróleo por día calendario ya cae en el mes -1 "
                 f"({_num(o1[2])} puntos, IC 95%: {_ic_txt(o1[3], o1[4])}), antes de la fractura del hijo, y el corte de "
                 "agua de ese mes no se separa de cero. La regla de `causal.md` admite anticipación hasta 3 meses; no se "
                 "midió si es un cierre del padre.")
    tardes = [d5[(e, "dA")] for e in E_D5 if e >= 2]
    if all(f[3] > 0 for f in tardes):
        L.append(f"- Sin veredicto, visto después de la regla: el agua por día calendario, que en la media de los meses 0 y "
                 f"1 no alcanza a separarse de cero (D3), queda sobre cero en cada mes de 2 a {E_D5[-1]}, entre "
                 f"{_num(min(f[2] for f in tardes))} y {_num(max(f[2] for f in tardes))} puntos del líquido de la base.")
    return L


def _seccion_d6(v6, d6: list[tuple]) -> list[str]:
    from pipeline.causal import _ic_txt, _num
    L = ["", "## D6: dónde se sostiene", ""]
    L.append(f"El corte de agua de D2 partido por operador (solo y sin él, con {MIN_TRATADOS_OPERADOR} tratados o más), por "
             "edad del padre, por año de la cohorte y por área (con el mismo mínimo). Se publican todos los cortes, sin ajuste "
             "por comparaciones múltiples, y ningún subgrupo tiene veredicto. Decide solo el \"sin el operador\": "
             "\"general\" si sin cada operador el IC sigue sobre cero, \"depende de un operador\" si no. Sacar un "
             "operador saca sus tratados y sus controles; un subgrupo deja los controles de su celda.")
    L += ["", "| Corte | Grupo | Tratados | Controles | Corte de agua (pp) | IC 95% |",
          "| --- | --- | ---: | ---: | ---: | --- |"]
    for c, g, nt, nc, val, lo, hi in d6:
        if val is None:
            L.append(f"| {NOMBRE_CORTE_D6.get(c, c)} | {g} | 0 | 0 | | |")
            continue
        L.append(f"| {NOMBRE_CORTE_D6.get(c, c)} | {g} | {_ent(nt)} | {_ent(nc)} | {_num(val)} | {_ic_txt(lo, hi)} |")
    L.append("")
    L.append(f"Veredicto: {_ver_d6(v6, d6)}. {_texto_d6(v6, d6)}")
    pares = [(o[1], a[1]) for o in d6 if o[0] == "operador" for a in d6 if a[0] == "area"
             if o[2] == a[2] and o[4] is not None and a[4] is not None and abs(o[4] - a[4]) < 1e-9]
    for op, ar in pares:
        L.append("")
        L.append(f"{op} y el área {ar} son los mismos tratados: sus dos filas dan lo mismo.")
    return L


TEXTO_D7 = {
    V_REPITE: "El corte de agua de D2 sostiene también en Colorado, y D3 da allí el mismo veredicto que en Vaca Muerta.",
    V_NO_REPITE: "En Colorado el corte de agua de D2 no sostiene, así que D3 no se compara.",
    V_REPITE_PARTE: "En Colorado el corte de agua de D2 sostiene, pero D3 da un veredicto distinto al de Vaca Muerta.",
    V_SIN_MUESTRA: "La muestra de Colorado no llega al mínimo de la regla: las cifras se publican pero no deciden.",
    V_SIN_DATO_AGUA: "El dato de agua de los meses base no llega a la cobertura que pide la regla: en Colorado no se "
                     "calculan D2 ni D3.",
}

NOMBRE_PLACEBO_D7 = {"previo": "previo", "fecha_falsa": "fecha falsa", "distancia_falsa": "distancia falsa",
                     "nunca_tratados": "nunca tratados", "cierre": "cierre"}


def _filas_d7(con) -> dict | None:
    """{resultado: (n_tratados, valor, ic_bajo, ic_alto, roto, veredicto)}; None si D7 no se corrio."""
    try:
        filas = con.execute("select resultado, n_tratados, valor, ic_bajo, ic_alto, roto, veredicto "
                            "from mart_causal_profundo_d7").fetchall()
    except duckdb.Error:
        return None
    return {f[0]: f[1:] for f in filas}


def _placebos_d7(d7: dict, sufijo: str) -> tuple[int, list[str]]:
    """Cuantos placebos de una magnitud hay en el mart de D7 y cuales rompen."""
    claves = [k for k in d7 if k.startswith("placebo_") and k.endswith(sufijo)]
    rotos = [NOMBRE_PLACEBO_D7.get(k[len("placebo_"):-len(sufijo)] if sufijo else k[len("placebo_"):], k)
             for k in claves if d7[k][4]]
    return len(claves), rotos


def _txt_rotos(n: int, rotos: list[str]) -> str:
    if not rotos:
        return "no rompe" if n == 1 else f"ninguno de los {_ent(n)} rompe"
    return f"rompe{'n' if len(rotos) > 1 else ''} {', '.join(rotos)}"


def _seccion_d7(con, d7: dict | None) -> list[str]:
    """La seccion de D7 (Colorado): cobertura, D2 y D3 de la segunda cuenca y el veredicto."""
    from pipeline.causal import _ic_txt, _num
    L = ["", "## D7: Colorado", ""]
    if d7 is None:
        L.append("D7 no se corrió: Colorado es opcional y su warehouse puede no estar. No hay cifras de Colorado en "
                 "esta página.")
        return L
    cob = d7["cobertura_agua"]
    ver = d7["D7"][5]
    L.append("El mismo diseño de D2 y D3, con las mismas constantes, los mismos sorteos y una regla fijada antes de calcular D7, sobre el "
             "warehouse de Colorado (cuenca DJ): los pozos horizontales con coordenadas, el mes de fractura de los hijos "
             "sin fecha dudosa y la producción mensual. El warehouse de Colorado se abre solo para leer; la tabla "
             "`mart_causal_profundo_d7` se escribe en el de Vaca Muerta. La regla pide primero que el dato de agua "
             "alcance, y después compara.")
    L.append("")
    if np.isnan(cob[1]):
        L.append("- Cobertura del dato de agua: no hay meses base de tratados de D2 dentro del panel.")
    else:
        L.append(f"- Cobertura del dato de agua: {_ent(round(100 * cob[1]))}% de los meses base (meses -6 a -4) de los "
                 f"{_ent(cob[0])} tratados de las celdas de D2 tienen agua y días efectivos; la regla pide "
                 f"{_ent(round(100 * COBERTURA_MIN))}%.")
    dw = d7.get("dW")
    if dw is None:
        L.append("- D2 y D3 no se calcularon en Colorado: no se pasó la compuerta de dato de la regla.")
    else:
        da, do, da_pd = d7["dA"], d7["dO"], d7["dA_pd"]
        vm2 = con.execute("select veredicto, valor, ic_bajo, ic_alto from mart_causal_veredicto "
                          "where diseno = 'D2'").fetchone()
        vm3 = con.execute("select veredicto from mart_causal_profundo_veredicto where diseno = 'D3'").fetchone()
        txt_vm2 = (f"; en Vaca Muerta, {_num(vm2[1])} (IC 95%: {_ic_txt(vm2[2], vm2[3])})" if vm2 else "")
        L.append(f"- D2, corte de agua: {_num(dw[1])} puntos porcentuales (IC 95%: {_ic_txt(dw[2], dw[3])}), con "
                 f"{_ent(dw[0])} tratados{txt_vm2}. Veredicto en Colorado: {dw[5]}.")
        n2, r2 = _placebos_d7(d7, "_dW")
        c = d7["placebo_cierre"]
        L.append(f"- Placebos de D2: de los de cohorte, {_txt_rotos(n2, r2)}. El placebo de cierre da "
                 f"{_num(c[1])} (IC 95%: {_ic_txt(c[2], c[3])}): "
                 + ("rompe con la regla de D2." if c[4] else
                    "el intervalo toca cero, no rompe." if not (c[2] > 0 or c[3] < 0) else
                    f"el intervalo no toca cero, pero queda debajo de {_ent(round(100 * FRACCION_CIERRE))}% del corte "
                    "de D2, así que con la regla de D2 no rompe." if c[1] < FRACCION_CIERRE * dw[1] else
                    "el intervalo no toca cero, pero con la regla de D2 no rompe porque el corte de D2 no es positivo."))
        L.append(f"- D3, en puntos del líquido base: agua por día calendario {_num(da[1])} (IC 95%: "
                 f"{_ic_txt(da[2], da[3])}), agua por día producido {_num(da_pd[1])} (IC 95%: "
                 f"{_ic_txt(da_pd[2], da_pd[3])}), petróleo por día calendario {_num(do[1])} (IC 95%: "
                 f"{_ic_txt(do[2], do[3])}), con {_ent(da[0])} tratados.")
        n3, r3 = _placebos_d7(d7, "_dA")
        n3p, r3p = _placebos_d7(d7, "_dA_pd")
        L.append(f"- Placebos de D3: del agua por día calendario, {_txt_rotos(n3, r3)}; del agua por día producido, "
                 f"{_txt_rotos(n3p, r3p)}.")
        L.append(f"- D3 en Colorado: {da[5]}. En Vaca Muerta: {vm3[0] if vm3 else 'sin fila'}.")
    L.append(f"- {MARCA[ver]} **D7, Colorado: {ver}.** {TEXTO_D7.get(ver, '')}")
    return L


def pagina_causal_profundo(con) -> str:
    """Pagina wiki/hallazgos/causal_profundo.md desde los marts de este modulo."""
    from pipeline.causal import _ic_txt, _num
    v = con.execute("select veredicto, valor, ic_bajo, ic_alto, n_tratados, n_bloques, d2_gana_nombre "
                    "from mart_causal_profundo_veredicto where diseno = 'D3'").fetchone()
    ver, val, bajo, alto, n_t, n_b, gana = v
    a_pd = _fila_d3(con, "dA_pd")
    o = _fila_d3(con, "dO")
    o_pd = _fila_d3(con, "dO_pd")
    w = _fila_d3(con, "dW_media")
    nt_w = _fila_d3(con, "placebo_nunca_tratados_dW")
    d2 = con.execute("select veredicto, valor, ic_bajo, ic_alto from mart_causal_veredicto where diseno = 'D2'").fetchone()

    L = ["# Causal profundo: entra agua o sale petróleo", ""]
    L.append("Página generada por `pipeline/causal_profundo.py`. El diseño causal (`causal.md`) encontró que la primera "
             "fractura de un hijo a menos de 1 km sube el corte de agua del padre, y la regla le dio a eso el nombre "
             "\"comunicación física\". Pero el corte de agua es una proporción, agua sobre agua más petróleo: sube si entra "
             "agua o si cae el petróleo con el agua quieta. Esta página mide los dos volúmenes por separado, con el mismo "
             "diseño, los mismos controles aún no tratados y los mismos sorteos del bootstrap. El plan completo está en "
             "`docs/plan-causal-profundo.md`.")
    L += ["", "## Resumen", ""]
    L.append(f"- {MARCA[ver]} **D3, agua que entra o petróleo que sale: {ver}.** {TEXTO_D3.get(ver, '')}")
    L.append(f"- Agua por día calendario: {_num(val)} puntos del líquido de la base (IC 95% por bloques de 5 km: "
             f"{_ic_txt(bajo, alto)}), {_ent(n_t)} padres tratados en {n_b} bloques.")
    L.append(f"- Agua por día producido: {_num(a_pd[2])} puntos (IC 95%: {_ic_txt(a_pd[3], a_pd[4])}), {a_pd[0]} "
             f"tratados; petróleo por día producido: {_num(o_pd[2])} (IC 95%: {_ic_txt(o_pd[3], o_pd[4])}).")
    L.append(f"- Petróleo por día calendario: {_num(o[2])} puntos (IC 95%: {_ic_txt(o[3], o[4])}).")
    if gana:
        L.append("- Qué le pasa a D2: conserva el nombre \"comunicación física\""
                 + (" con la salvedad de que el agua entra en los días producidos y el volumen del mes no alcanza a separarse de cero."
                    if ver == V_D3_ENTRA_PD else "."))
    else:
        L.append("- Qué le pasa a D2: su veredicto impreso no cambia (lo fija la regla de `causal.md`), pero D3, fijado "
                 "después, no le da el nombre \"comunicación física\": la suba del corte se sostiene, el canal no.")
    nt_rompe = bool(nt_w[5])
    L.append(f"- El placebo de nunca tratados, que la regla de D2 no tenía, sobre el corte de agua de D2: "
             f"{_num(nt_w[2])} puntos porcentuales (IC 95%: {_ic_txt(nt_w[3], nt_w[4])}), {nt_w[0]} pseudo tratados; "
             + ("rompe." if nt_rompe else "no rompe."))
    d4 = _filas_d4(con)
    if d4 is not None:
        vd, vt = _veredicto_d4(con, "D4_distancia"), _veredicto_d4(con, "D4_tamano")
        bw = {b: d4[("distancia", b, "dW")] for b in ("0-0.5", "0.5-1", "1-2")}
        L.append(f"- {MARCA[vd[0]]} **D4, dosis por distancia: {vd[0]}.** El corte de agua sube {_num(bw['0-0.5'][2])} puntos porcentuales "
                 f"con el primer golpe a menos de 0,5 km, {_num(bw['0.5-1'][2])} entre 0,5 y 1 km y {_num(bw['1-2'][2])} "
                 f"entre 1 y 2 km; la cercana menos la lejana da {_num(vd[1])} (IC 95%: {_ic_txt(vd[2], vd[3])}).")
        tw = {b: d4[("tamano_agua", b, "dW")] for b in ("alto", "medio", "bajo")}
        L.append(f"- {MARCA[vt[0]]} **D4, dosis por tamaño del hijo (agua de fractura): {vt[0]}.** Tercil alto {_num(tw['alto'][2])}, "
                 f"medio {_num(tw['medio'][2])}, bajo {_num(tw['bajo'][2])} puntos porcentuales; alto menos bajo "
                 f"{_num(vt[1])} (IC 95%: {_ic_txt(vt[2], vt[3])}).")
        if not (ver in (V_D3_ENTRA, V_D3_ENTRA_PD) and vd[0] == V_GRADIENTE):
            L.append("- D8, la lectura operativa, no se escribe: la regla la pide solo si D3 da agua que entra y D4 da "
                     "gradiente de distancia.")

    d56 = _datos_d56(con)
    if d56 is not None:
        v5, d5, v6, d6 = d56
        L.append(f"- {MARCA[v5[0]]} **D5, forma en el tiempo: {v5[0]}.** {_texto_d5(v5, d5)}")
        L.append(f"- {MARCA[v6[0]]} **D6, dónde se sostiene: {_ver_d6(v6, d6)}.** {_texto_d6(v6, d6)}")

    d7 = _filas_d7(con)
    if d7 is not None:
        v_d7 = d7["D7"][5]
        L.append(f"- {MARCA[v_d7]} **D7, Colorado: {v_d7}.** {TEXTO_D7.get(v_d7, '')}")
    else:
        L.append("- D7, Colorado: no se corrió (Colorado es opcional).")

    L += ["", "## Regla fijada antes de calcular", ""]
    L.append(f"La regla se fijó en el commit {COMMIT_REGLA} de la rama `t3/causal-profundo`: la cabecera de "
             "`pipeline/causal_profundo.py`, sus constantes y las funciones de veredicto, sin ninguna cifra calculada. Al "
             "fijarla se conocían todas las cifras de `causal.md`, incluida la caída del petróleo: por eso D3 decide con el "
             "agua.")
    L.append("")
    L.append("- Unidad: puntos del líquido de la base. Para cada padre, el cambio de su agua (o de su petróleo) por día "
             "entre la base (meses -6 a -4) y la media de los meses 0 y 1, dividido por su líquido por día de la base, "
             "por 100. Agua y petróleo quedan en la misma unidad y suman el cambio del líquido.")
    L.append("- Decide el agua por día calendario: un cierre baja los días producidos, así que no puede subirla. El "
             f"agua por día producido (meses con {DIAS_MIN_PD} días producidos o más) es secundaria: puede inflarse por el "
             "flujo de una reapertura, y deja afuera los meses casi enteros cerrados.")
    L.append(f"- Un placebo rompe si su IC excluye cero y vale {_num(UMBRAL_ROTURA_VOLUMEN, 0)} puntos o más.")
    L.append("- Orden del veredicto: sin muestra; no sobrevive a su placebo; entra agua (IC bajo del agua por día "
             "calendario sobre cero); entra agua en los días producidos (el anterior incluye cero, el IC bajo por día "
             "producido queda sobre cero y sus placebos no rompen); el corte sube porque cae el petróleo (el agua no "
             f"sube {_num(UMBRAL_VOLUMEN, 0)} puntos por ninguna de las dos vías y el petróleo cae); no firme.")

    L += ["", "## D3: volúmenes", ""]
    L.append("| Cantidad | Tratados | Controles | Cambio (puntos del líquido base) | IC 95% |")
    L.append("| --- | ---: | ---: | ---: | --- |")
    for k, nombre in NOMBRE_D3.items():
        f = _fila_d3(con, k)
        L.append(f"| {nombre} | {_ent(f[0])} | {_ent(f[1])} | {_num(f[2])} | {_ic_txt(f[3], f[4])} |")
    L.append("")
    L.append(f"Puente con D2, sin veredicto: el corte de agua con la media de los meses 0 y 1 (D2 toma el mayor de los dos) "
             f"da {_num(w[2])} puntos porcentuales (IC 95%: {_ic_txt(w[3], w[4])}), contra {_num(d2[1])} de D2.")
    L += ["", "Placebos de D3.", "", "| Placebo | Tratados | Cambio (puntos) | IC 95% | Rompe |", "| --- | ---: | ---: | --- | --- |"]
    for k, nombre in NOMBRE_PLACEBO_D3.items():
        f = _fila_d3(con, k)
        L.append(f"| {nombre} | {f[0]} | {_num(f[2])} | {_ic_txt(f[3], f[4])} | {'sí' if f[5] else 'no'} |")

    if d4 is not None:
        L += ["", "## D4: dosis", ""]
        L.append(f"Las precisiones de D4 se fijaron en el commit {COMMIT_REGLA_D4}, antes de calcular cualquier cifra de D4: "
                 "los mismos sorteos que D3, la distancia del golpe más cercano del mes de la fractura, la cohorte nueva de "
                 "1 a 2 km y los terciles del hijo. Decide el corte de agua de D2; el agua por día calendario de D3 se "
                 "publica al lado. \"Gradiente\" pide que las tres estimaciones bajen de cerca a lejos (o de grande a "
                 "chico) y que el IC de la diferencia entre los extremos quede entero sobre cero; \"sin gradiente\", que "
                 "ese IC incluya el cero.")
        L += ["", "| Distancia del primer golpe | Tratados | Corte de agua (pp) | IC 95% | Agua por día calendario (puntos) | IC 95% |",
              "| --- | ---: | ---: | --- | ---: | --- |"]
        for b, nombre in NOMBRE_BANDA.items():
            w_, a_ = d4[("distancia", b, "dW")], d4[("distancia", b, "dA")]
            n_txt = _ent(w_[0]) if w_[0] is not None else ""
            L.append(f"| {nombre} | {n_txt} | {_num(w_[2])} | {_ic_txt(w_[3], w_[4])} | {_num(a_[2])} | "
                     f"{_ic_txt(a_[3], a_[4])} |")
        fuera = d4[("distancia", "fuera", "cuenta")][2]
        L.append("")
        L.append(f"Las bandas de 0 a 0,5 y de 0,5 a 1 km parten los tratados de D2. La de 1 a 2 km es otra cohorte: padres "
                 "cuyo primer golpe a menos de 2 km cae entre 1 y 2 km, sin ninguno a menos de 1 km en la ventana, con los "
                 "mismos controles; un pozo fuera del universo de los sorteos toma el peso de su bloque de 5 km, y "
                 f"{_ent(fuera)} quedan fuera porque su bloque no tiene ninguno. La banda de 3 a 5 km es el placebo de "
                 "distancia falsa de D2, reimpreso.")
        b12, b35 = d4[("distancia", "1-2", "dW")], d4[("distancia", "3-5", "dW")]
        b05 = d4[("distancia", "0-0.5", "dW")]
        cercana_no_mayor = b05[2] is not None and b05[2] < max(
            (x for x in (d4[("distancia", "0.5-1", "dW")][2], b12[2]) if x is not None), default=float("-inf"))
        if b12[3] > 0 and b35[3] <= 0 <= b35[4] and cercana_no_mayor:
            L.append("")
            L.append(f"Sin veredicto, visto después de la regla: la banda de 1 a 2 km también sube el corte (IC "
                     f"{_ic_txt(b12[3], b12[4])}) y la de 3 a 5 km no se separa de cero. El efecto no se corta en 1 km, "
                     "pero la regla no pidió un umbral y la banda más cercana no es la más alta.")
        L += ["", "| Agua de fractura del hijo | Tratados | Corte de agua (pp) | IC 95% | Agua por día calendario (puntos) | IC 95% |",
              "| --- | ---: | ---: | --- | ---: | --- |"]
        for b, nombre in NOMBRE_TERCIL.items():
            w_, a_ = d4[("tamano_agua", b, "dW")], d4[("tamano_agua", b, "dA")]
            n_txt = _ent(w_[0]) if w_[0] is not None else ""
            L.append(f"| {nombre} | {n_txt} | {_num(w_[2])} | {_ic_txt(w_[3], w_[4])} | {_num(a_[2])} | "
                     f"{_ic_txt(a_[3], a_[4])} |")
        cob = d4[("tamano_agua", "cobertura", "cuenta")]
        L.append("")
        L.append(f"Los cortes de los terciles salen de los {_ent(cob[0])} tratados de las celdas de D2 con el agua de fractura "
                 f"del hijo ({_num(100 * cob[2], 0)}% de los que tienen corte de agua); las estimaciones usan los que quedan en "
                 "celdas con controles suficientes, como D2.")
        dif_t = d4[("tamano_agua", "alto_menos_bajo", "dW")]
        if dif_t[2] < 0 and dif_t[3] <= 0 <= dif_t[4]:
            L.append("")
            L.append("Sin veredicto: el tercil de más agua da la suba más chica, al revés de una dosis; la regla no tiene "
                     "veredicto para un gradiente al revés y el IC de la diferencia incluye el cero.")
        r_ = d4[("rama", "alto_menos_bajo", "dW")]
        rc = d4[("rama", "cobertura", "cuenta")]
        L.append("")
        L.append(f"Longitud de rama del hijo, sin veredicto: el tercil más largo menos el más corto da {_num(r_[2])} puntos "
                 f"porcentuales (IC 95%: {_ic_txt(r_[3], r_[4])}); tiene el dato el {_num(100 * rc[2], 0)}% de los tratados.")

    if d56 is not None:
        L += _seccion_d5(v5, d5) + _seccion_d6(v6, d6)

    L += _seccion_d7(con, _filas_d7(con))

    L += ["", "## Límites", ""]
    L.append("- Causa bajo los supuestos de `causal.md` (tendencias paralelas condicionales a cohorte y edad, sin "
             "anticipación más allá de 3 meses, sin derrame sobre controles limpios a 2 km), no un hecho físico medido: "
             "el agua se ve en el volumen mensual, no entrando.")
    a = _fila_d3(con, "dA")
    L.append(f"- El agua por día producido deja afuera a los padres sin ningún mes de {DIAS_MIN_PD} días producidos o más "
             f"en la ventana o con menos de dos en la base (ese mínimo de dos meses no lo fijó la regla: se eligió al "
             f"calcular, en el mismo commit que dio las cifras): quedan {_num(100 * a_pd[0] / a[0], 0)}% de los tratados y "
             f"{_num(100 * a_pd[1] / a[1], 0)}% de los controles. Es una muestra que el cierre puede elegir.")
    L.append("- Una reapertura puede dar un flujo inicial alto; si eso explicara la suba por día producido, el petróleo "
             "por día producido también subiría.")
    L.append("- Solo la primera fractura a menos de 1 km de cada padre, distancia entre bocas de pozo, como en `causal.md`.")
    if d56 is not None:
        L.append("- D6 publica cada corte sin ajuste por comparaciones múltiples, y ningún subgrupo tiene veredicto: con "
                 "tantos cortes, alguno puede salir alto o bajo por azar.")
    L.append("- Lo que lo cargaría como hecho físico sigue en la tabla de datos de `causal.md`: presión del padre, "
             "producción diaria, trazadores.")

    L += ["", "## Reproducir", "", "```", "uv run python -m pipeline.build", "uv run python -m pipeline.trayectorias",
          "uv run python -m pipeline.causal", "uv run python -m pipeline.causal_profundo", "uv run python -m pipeline.wiki",
          "```", ""]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="pipeline.causal_profundo")
    ap.add_argument("--cuenca", choices=["colorado"], help="D7 sobre Colorado (la regla fija esa cuenca); sin argumento, Vaca Muerta")
    a = ap.parse_args()
    if a.cuenca:
        from pipeline.cuencas import cuenca
        c = cuenca(a.cuenca)
        con_vm = duckdb.connect(str(DATA / "warehouse.duckdb"))
        con_co = duckdb.connect(str(c.db), read_only=True)
        try:
            _d7(con_vm, con_co)
        finally:
            con_co.close()
            con_vm.close()
    else:
        main()
