"""Golpes repetidos (R1): cada golpe posterior de un padre como su propio evento, con controles de la misma historia.

Se corre despues de pipeline.causal_exposicion:  uv run python -m pipeline.golpes_repetidos

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla de abajo. Su
SHA, la fecha y el texto estan en docs/reglas-fijadas.md (lo agrega el carril de textos, T) y en la pagina
wiki/hallazgos/golpes_repetidos.md que genera el modulo ("regla fijada en <sha> antes de calcular").

REGLA FIJADA ANTES DE CALCULAR (2026-11-28, carril LR, paso R1 del mapa del Estratega, docs/orquestacion/mapa.md). Este
commit trae solo la regla, las constantes y el veredicto; no se calculo ninguna cuenta de golpes posteriores, ningun efecto
ni ningun p de R1. Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga (un parrafo
"ACLARACION", como en pipeline.causal_exposicion para D14), nunca despues de ver una cifra.

Por que R1. D2 estima el efecto del PRIMER golpe de un padre (un hijo fracturado a menos de 1 km); D5 sigue ese primer golpe
mes a mes; D10 corta la serie de D5 en el segundo golpe y responde si el efecto del primero persiste cuando se saca el
siguiente. Ninguno estima el efecto DEL segundo golpe: por la ventana previa limpia de D2 (ningun golpe a 2 km en los 12
meses antes de g), todo golpe posterior queda fuera de todos los disenos del repositorio. R1 trata cada golpe posterior como
un evento propio, con su cohorte, sus celdas y sus controles, y los controles son padres con la misma historia: ya golpeados
antes, con el ultimo golpe el mismo numero de meses atras. Es la logica de un tratamiento repetido y no absorbente: comparar
un pozo cuyo tratamiento cambia con pozos que tuvieron la misma trayectoria de tratamiento hasta ese mes y todavia no
cambiaron. No verificado: el repositorio solo cita a de Chaisemartin y D'Haultfoeuille (2020, AER,
docs/revision-independiente.md); su trabajo posterior sobre tratamientos no absorbentes no se leyo, asi que esta regla describe
el diseno propio de R1 y no dice que implemente ese estimador.

Todo reutiliza pipeline.causal, pipeline.causal_profundo y pipeline.causal_exposicion sin tocarlos: universo, golpes, W, dW,
bloques, sorteos (los W de D3 extendidos con extender_pesos, como D4, D5 y D10), causal.rompe y causal._ic. Las constantes
heredadas se importan, no se reescriben.

1. Lo que se conocia al fijarla. D2 (13,8 con 447 tratados), D5 (142 de 341 tratados reciben otro golpe a menos de 2 km en
   los meses 2 a 12), D10 (62 de 341 a 1 km; media tardia +10,5, "persiste") y D14 ("sin muestra"). No se conocia ninguna
   cuenta de golpes posteriores, ningun efecto y ningun p de R1.

2. Evento. Un golpe del padre i en el mes t es km_min[i, t] < KM_TRATADO. Los eventos se arman en orden de tiempo desde el
   primer mes de petroleo del padre: un mes de golpe t abre un evento nuevo cuando el padre no tiene evento anterior, o cuando
   t - g_prev >= S_CENSURA, con g_prev el mes de su evento anterior; si no, pertenece al evento anterior. El orden k de un
   evento es 1, 2, 3... en esa secuencia. s = g_k - g_(k-1) son los meses desde el evento anterior.

3. Tratado (R1). Un evento de orden k >= 2 en el mes g con: s >= S_MIN_POSTERIOR = 8 (asi la ventana de base g - 6 a g - 4
   empieza en g_prev + 2 o despues, tras los meses de resultado del evento anterior, g_prev y g_prev + 1); edad en g >=
   EDAD_MIN; base de W valida (media de W en g - 6 a g - 4 con al menos MIN_MESES_W_BASE meses); ningun golpe a menos de
   KM_LIMPIO en [g - 6, g - 1] (VENTANA_PREVIA_POSTERIOR = 6, los meses de la base y los previos; los 12 de D2 pedirian
   s >= 14). Los eventos de orden >= 2 con s de 2 a 7 se cuentan y se publican, no se estiman (su base se solapa con los
   meses de resultado del evento anterior).

4. Bandas de tiempo desde el golpe anterior. BANDAS_S = ((8, 12), (13, 24), (25, None)) meses, cerradas en los dos extremos;
   None es abierta.

5. Controles de una celda. Celda = (g, grupo de edad por CORTES_EDAD, banda de s). Un control es un padre j != i con al menos
   un evento anterior, cuyo ultimo evento antes de g cae en g - s_j (s_j = g menos el mes de su ultimo evento, el tiempo
   desde su propio ultimo golpe) con s_j en la misma banda, edad en g >= EDAD_MIN, base de W valida en g y ningun golpe a
   menos de KM_LIMPIO en [g - 6, g + H_CORTO]. Los padres aun no golpeados y los nunca golpeados no son controles: les falta
   el golpe previo, y su decaimiento (D10: de +18 a +9 en 12 meses) romperia las tendencias paralelas. Una celda entra con
   MIN_CONTROLES_CELDA controles con dW.

6. Resultado y estimando. dW como en D2 (k = 0): el mayor W de los meses g y g + 1 menos la media de la base, en puntos
   porcentuales. ATT_R1 = media sobre celdas de (media de dW de los tratados menos media de dW de los controles), pesada por
   tratados (como D2). IC 95 %: bootstrap de percentiles por bloques de 5 km, con los sorteos de D3 extendidos con
   extender_pesos (los pozos que se quedan sin bloque salen y se cuentan, como en D4, D5 y D10).

7. Placebo (tendencia previa). En las mismas celdas: la media sobre e = -3, -2, -1 de W(g + e) menos la media de la base,
   tratados menos controles. Rompe con la regla de causal.md: el IC excluye cero y |valor| >= UMBRAL_AGUA_PP.

8. Veredicto (`veredicto_r1(n, placebo_rompe, bajo, alto, att_d2)`, en este orden):
   * "sin muestra" si n (tratados con dW en celdas con controles) < MIN_TRATADOS_D5 (200, el minimo de las series dinamicas
     D5 y D10; se mantiene, no se baja: D2 y D14 usan 300, las series dinamicas 200, y solo los cortes sin veredicto y las
     bandas bajan mas). Resultado esperado, solo con cuentas ya publicadas: de los 341 tratados de D5, 62 reciben un segundo
     golpe a 1 km en los meses 2 a 12 (exposicion.md, D10), menos todavia con s >= 8 y [g - 6, g - 1] limpio; los golpes
     posteriores de otros padres suman, pero los controles necesitan su propio golpe anterior en la misma banda y 13 meses
     limpios, y D1b (43 de 200) y D14 (114 de 300) se quedaron cortos en el mismo relleno denso. "sin muestra" es el
     resultado probable: es un resultado planeado y terminado (el punto 9 publica igual las cuentas), nunca una falla a
     arreglar;
   * V_PLACEBO si el placebo rompe;
   * V_R1_REPITE = "se repite en cada golpe" si el IC bajo de ATT_R1 > UMBRAL_AGUA_PP;
   * V_R1_NO_REPITE = "no se repite" si el IC incluye cero y el IC alto < FRACCION_CURA x att_d2, con att_d2 el ATT_W de D2
     leido de mart_causal_veredicto en la corrida (nunca escrito a mano);
   * V_NO_FIRME en otro caso.

9. Publicado sin veredicto. (a) La serie dinamica: dW(e) para e en E_D5 de los tratados de R1, con controles limpios a
   KM_LIMPIO en [g - 6, g + H_D5], saliendo cada tratado de la serie desde su evento siguiente (el corte de D10 a 1 km, con
   s >= S_CENSURA). (b) ATT_R1 por orden (k = 2; k >= 3) y por banda de s. (c) Cuentas: todos los eventos de orden >= 2; los
   de s de 2 a 7; los elegibles; los que quedan en celdas con controles; los pozos que salen por no tener bloque. (d) Junto
   a ATT_R1, el ATT_W de D2 con el que se compara.

10. Pruebas multiples. R1 suma una hipotesis a pipeline.inferencia.FAMILIA_CONFIRMATORIA: la fila `diseno` = "R1" de
    mart_golpes_repetidos_veredicto. k = len(FAMILIA_CONFIRMATORIA) sube en uno; eso puede cambiar el p de Holm de los otros
    disenos, y queda fijado aca, antes de toda cifra. Las filas (a) a (d) no estan en la familia.

11. Lo que no dice. Las tendencias paralelas son condicionales al tiempo desde el golpe anterior y no se pueden probar despues
    de g; los golpes posteriores caen donde el relleno es denso (los tratados estan seleccionados); los eventos con s de 2 a 7
    no se estiman; el golpe es por distancia de boca de pozo, no por distancia lateral (D14 y trayectorias.md).

12. Marts y pagina. `mart_golpes_repetidos` (series y cortes, columna `diseno`) y `mart_golpes_repetidos_veredicto` (una fila
    "R1", con las columnas de causal_exposicion.COLS_VEREDICTO), cada uno escrito con su nombre literal en `_escribir`;
    pagina wiki/hallazgos/golpes_repetidos.md, generada por el modulo, que cita el SHA de este commit ("regla fijada en
    <sha> antes de calcular").

13. Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga (un parrafo "ACLARACION"), nunca
    despues de ver una cifra.

ACLARACION 1 (antes de escribir el codigo que calcula; no se vio ninguna cifra de R1). Decisiones de construccion que la
regla dejaba abiertas, sin cambiar nada de lo fijado arriba:
  a. Eventos (punto 2). Solo cuentan los golpes desde el primer mes de petroleo del padre (`primer`); los anteriores se
     ignoran. El mes g de un evento es el de su primer mes de golpe. El evento de orden 1 no tiene s.
  b. "Ultimo evento antes de g" (punto 5) es el ultimo evento con mes estrictamente menor que g. Como la ventana limpia del
     control incluye g - 6 a g + H_CORTO, ese evento cae en g - 7 o antes, y la banda de s_j lo exige igual (s_j >= 8).
  c. Placebo (punto 7). Es la media sobre e = -3, -2, -1 de tres estimaciones por mes (tratados menos controles de W(g + e)
     menos la media de la base, en las celdas y con los sorteos del punto 6), promediadas sorteo por sorteo con
     causal_profundo.media_resultados, como D10 promedia sus meses tardios; su n es el menor de los tres.
  d. n del veredicto (punto 8). Los tratados con dW (k = 0) en celdas con al menos MIN_CONTROLES_CELDA controles con dW: el
     `n_tratados` de causal_profundo.estimar_valores.
  e. Un pozo con varios eventos tratados entra una vez por evento, cada uno en su propia celda (g, grupo, banda); el
     bootstrap pesa por pozo, no por evento.
  f. Serie (punto 9a). Celdas con H = H_D5 (controles limpios a KM_LIMPIO en [g - 6, g + H_D5]); cada tratado sale desde el
     primer mes e con S_CENSURA <= e <= H_D5 y km_min < KM_TRATADO (causal_exposicion.mes_censura), igual que D10.
  g. Cortes (punto 9b). Orden k = 2 y k >= 3, y cada banda de s: las celdas de ATT_R1 con solo los tratados del corte
     (causal_profundo.celdas_por_mascara, mismos controles, mismos sorteos); sin veredicto.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np

from pipeline.causal import (EDAD_MIN, H_CORTO, KM_LIMPIO, KM_TRATADO, MIN_CONTROLES_CELDA, MIN_MESES_W_BASE, UMBRAL_AGUA_PP,
                             V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA, _grupo_edad, _panel_promedio, _valores_agua,
                             _ventana, rompe)
from pipeline.causal_exposicion import COLS_VEREDICTO, S_CENSURA, censurar, mes_censura, preparar
from pipeline.causal_profundo import (E_D5, FRACCION_CURA, H_D5, MIN_TRATADOS_D5, celdas_por_mascara, estimar_valores,
                                      extender_pesos, media_resultados, valores_dw_mes)
from pipeline.costo import _escribir
from pipeline.ingest import DATA

# heredado sin cambio (se importa arriba, nunca se reescribe)
REGLA_HEREDADA = {"KM_TRATADO": KM_TRATADO, "KM_LIMPIO": KM_LIMPIO, "EDAD_MIN": EDAD_MIN, "H_CORTO": H_CORTO,
                  "MIN_CONTROLES_CELDA": MIN_CONTROLES_CELDA, "MIN_MESES_W_BASE": MIN_MESES_W_BASE,
                  "UMBRAL_AGUA_PP": UMBRAL_AGUA_PP, "E_D5": E_D5, "H_D5": H_D5, "MIN_TRATADOS_D5": MIN_TRATADOS_D5,
                  "FRACCION_CURA": FRACCION_CURA, "S_CENSURA": S_CENSURA}

# ---- regla fijada (no cambiar despues de ver cifras)
S_MIN_POSTERIOR = 8                   # meses minimos desde el evento anterior para estimar (base despues de g_prev + 1)
VENTANA_PREVIA_POSTERIOR = 6          # meses previos a g sin golpe a KM_LIMPIO (la base y los previos); D2 pide 12
BANDAS_S = ((8, 12), (13, 24), (25, None))   # meses desde el golpe anterior, cerradas en los dos extremos; None es abierta
E_PLACEBO = (-3, -2, -1)              # meses del placebo de tendencia previa
DISENO_R1 = "R1"                      # la fila de mart_golpes_repetidos_veredicto y de FAMILIA_CONFIRMATORIA

V_R1_REPITE = "se repite en cada golpe"
V_R1_NO_REPITE = "no se repite"


def veredicto_r1(n: int, placebo_rompe: bool, bajo: float, alto: float, att_d2: float) -> str:
    """Veredicto de R1, en el orden de la regla. n: tratados con dW en celdas con controles; bajo y alto: el IC de ATT_R1;
    att_d2: el ATT_W de D2 leido de mart_causal_veredicto en la corrida."""
    if n < MIN_TRATADOS_D5:
        return V_SIN_MUESTRA
    if placebo_rompe:
        return V_PLACEBO
    if bajo > UMBRAL_AGUA_PP:
        return V_R1_REPITE
    if bajo <= 0 <= alto and alto < FRACCION_CURA * att_d2:
        return V_R1_NO_REPITE
    return V_NO_FIRME


# ---- constantes de construccion (no son parte de la regla: nombres de marts, pagina y SHA citado)
COLS_R1 = [("diseno", "varchar"), ("parte", "varchar"), ("corte", "varchar"), ("e", "integer"), ("n_tratados", "integer"),
           ("n_controles", "integer"), ("est", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
SHA_REGLA = "0670d9c"                 # el commit que fijo la regla; la aclaracion 1 es 99ed77a
PAGINA = Path("wiki/hallazgos/golpes_repetidos.md")
CUENTAS = ("eventos_orden_2_o_mas", "s_2_a_7", "elegibles", "en_celdas_con_controles", "pozos_sin_bloque")


# ---- eventos (puntos 2 y 3 de la regla)

def eventos(km_min_fila, primer: int, t0: int = 0) -> list[tuple[int, int, int | None]]:
    """Eventos de un padre en orden de tiempo: [(g, k, s)] con g el mes del evento (indice absoluto: columna + t0), k su orden
    (1, 2, 3...) y s los meses desde el evento anterior (None en el primero). Un mes de golpe (km_min < KM_TRATADO) abre un
    evento si no hay uno anterior o si t - g_prev >= S_CENSURA; si no, es del evento anterior. Los meses antes de `primer`
    (el primer mes de petroleo) no cuentan."""
    out: list[tuple[int, int, int | None]] = []
    if primer < 0:
        return out
    g_prev = None
    for t in (np.flatnonzero(np.asarray(km_min_fila, dtype=float) < KM_TRATADO) + t0).tolist():
        if t < primer:
            continue
        if g_prev is None or t - g_prev >= S_CENSURA:
            out.append((t, len(out) + 1, None if g_prev is None else t - g_prev))
            g_prev = t
    return out


def bandas_s(s: int | None) -> int | None:
    """Indice de la banda de BANDAS_S (cerrada en los dos extremos; None es abierta) de s meses, o None si no cae en ninguna."""
    if s is None:
        return None
    for i, (lo, hi) in enumerate(BANDAS_S):
        if s >= lo and (hi is None or s <= hi):
            return i
    return None


def _en_banda(s: np.ndarray, banda: int) -> np.ndarray:
    lo, hi = BANDAS_S[banda]
    return (s >= lo) if hi is None else ((s >= lo) & (s <= hi))


def _eventos_pozos(D: dict) -> list[list[tuple[int, int, int | None]]]:
    """Los eventos de cada pozo de D (cacheados)."""
    if "_eventos_r1" not in D:
        con_golpe = (np.asarray(D["km_min"]) < KM_TRATADO).any(axis=1)
        D["_eventos_r1"] = [eventos(D["km_min"][i], int(D["primer"][i]), D["t0"]) if con_golpe[i] else []
                            for i in range(D["n"])]
    return D["_eventos_r1"]


def _ultimo_evento(D: dict) -> np.ndarray:
    """Matriz (pozos x meses): el mes del ultimo evento con mes menor o igual al de la columna, o -1 (cacheada)."""
    if "_ultimo_r1" not in D:
        ev = np.full((D["n"], D["T"]), -1, dtype=np.int64)
        for i, lista in enumerate(_eventos_pozos(D)):
            for g, _k, _s in lista:
                ev[i, g - D["t0"]] = g
        D["_ultimo_r1"] = np.maximum.accumulate(ev, axis=1)
    return D["_ultimo_r1"]


def eventos_posteriores(D: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Todos los eventos de orden >= 2 como arrays (pozo, g, k, s)."""
    filas = [(i, g, k, s) for i, lista in enumerate(_eventos_pozos(D)) for g, k, s in lista if k >= 2]
    a = np.array(filas, dtype=np.int64).reshape(-1, 4)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def tratados_r1(D: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Los eventos tratados de R1 como arrays (pozo, g, k, s): orden >= 2, s >= S_MIN_POSTERIOR, edad >= EDAD_MIN, base de W
    valida y ningun golpe a KM_LIMPIO en [g - VENTANA_PREVIA_POSTERIOR, g - 1]."""
    pozo, g, k, s = eventos_posteriores(D)
    if not len(pozo):
        return pozo, g, k, s
    _, bueno = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    col = g - D["t0"]
    dentro = (col >= 0) & (col < D["T"])
    ok = (s >= S_MIN_POSTERIOR) & dentro & (g - D["primer"][pozo] >= EDAD_MIN)
    ok &= bueno[pozo, np.clip(col, 0, D["T"] - 1)]
    ok &= _ventana(D, g - VENTANA_PREVIA_POSTERIOR, g - 1, wells=pozo) == 0
    return pozo[ok], g[ok], k[ok], s[ok]


def celdas_r1(D: dict, tratados: tuple, H: int) -> list[dict]:
    """Celdas (g, grupo de edad, banda de s) con la forma de causal.celdas (`g`, `grupo`, `tratados`, `controles`, `base_t`,
    `base_c`) mas `banda`, para causal_profundo.estimar_valores. Controles: padres con un evento anterior cuyo ultimo evento
    antes de g cae en la misma banda de s, edad >= EDAD_MIN y el mismo grupo de edad, base de W valida en g y ningun golpe a
    KM_LIMPIO en [g - VENTANA_PREVIA_POSTERIOR, g + H]. Los no golpeados y los nunca golpeados nunca son controles."""
    pozo, g, _k, s = tratados
    if not len(pozo):
        return []
    media, bueno = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)  # base de W, como en tratados_r1
    ult = _ultimo_evento(D)
    grupo = _grupo_edad(g - D["primer"][pozo])
    banda = np.array([bandas_s(int(x)) for x in s], dtype=np.int64)
    out = []
    for gg, gr, bd in dict.fromkeys(zip(g.tolist(), grupo.tolist(), banda.tolist())):
        sel = pozo[(g == gg) & (grupo == gr) & (banda == bd)]
        col = gg - D["t0"]
        previo = ult[:, col - 1] if col >= 1 else np.full(D["n"], -1, dtype=np.int64)
        edad = gg - D["primer"]
        ok = (previo >= 0) & _en_banda(gg - previo, bd)
        ok &= (D["primer"] >= 0) & (edad >= EDAD_MIN) & (_grupo_edad(edad) == gr) & bueno[:, col]
        ok &= _ventana(D, gg - VENTANA_PREVIA_POSTERIOR, gg + H) == 0
        con = np.flatnonzero(ok)
        out.append({"g": int(gg), "grupo": int(gr), "banda": int(bd), "tratados": sel, "controles": con,
                    "base_t": media[sel, col], "base_c": media[con, col] if len(con) else np.zeros(0)})
    return out


# ---- estimacion (puntos 6, 7 y 9)

def _todos(ce: dict) -> np.ndarray:
    return np.ones(len(ce["tratados"]), dtype=bool)


def _vacio(W: np.ndarray) -> dict:
    nan = float("nan")
    return {"est": nan, "ic_bajo": nan, "ic_alto": nan, "vals": np.full(len(W), nan), "n_tratados": 0, "n_controles": 0}


def _att(D: dict, cel: list[dict], W: np.ndarray) -> dict:
    """ATT de dW (k = 0, como D2) en las celdas dadas."""
    if not cel:
        return _vacio(W)
    vt, vc = _valores_agua(D, cel, 0)
    return estimar_valores(D, cel, W, vt, vc)


def _placebo(D: dict, cel: list[dict], W: np.ndarray) -> dict:
    """Placebo de tendencia previa: la media sobre E_PLACEBO de las estimaciones por mes (aclaracion 1, c)."""
    if not cel:
        return _vacio(W)
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    res = []
    for e in E_PLACEBO:
        vt, vc = valores_dw_mes(D, cel, e, base_w)
        res.append(estimar_valores(D, cel, W, vt, vc))
    r = media_resultados(res)
    r["n_controles"] = int(min(x["n_controles"] for x in res))
    return r


def _serie(D: dict, cel: list[dict], W: np.ndarray) -> dict:
    """dW por mes e de E_D5 de los tratados de las celdas (con controles limpios hasta g + H_D5); cada tratado sale desde su
    evento siguiente (el corte de D10 a KM_TRATADO, con s >= S_CENSURA)."""
    base_w, _ = _panel_promedio(D, D["w"], MIN_MESES_W_BASE)
    censura = [mes_censura(D, ce, KM_TRATADO) for ce in cel]
    res = {}
    for e in E_D5:
        vt, vc = valores_dw_mes(D, cel, e, base_w)
        res[e] = estimar_valores(D, cel, W, censurar(vt, censura, e), vc)
    return res


def _fila(parte: str, corte: str, e: int | None, r: dict) -> tuple:
    return (DISENO_R1, parte, corte, e, int(r["n_tratados"]), int(r["n_controles"]), float(r["est"]), float(r["ic_bajo"]),
            float(r["ic_alto"]))


def _d2(con) -> tuple[float, float, float, int]:
    """El ATT_W de D2 con su IC y n, de mart_causal_veredicto en la corrida (nunca escrito a mano)."""
    r = con.execute("select valor, ic_bajo, ic_alto, n_tratados from mart_causal_veredicto where diseno = 'D2'").fetchone()
    if r is None:
        raise ValueError("falta la fila D2 de mart_causal_veredicto")
    return float(r[0]), float(r[1]), float(r[2]), int(r[3])


def calcular(con, prep: tuple) -> tuple[list[tuple], tuple]:
    """R1: ATT_R1, placebo, serie, cortes y cuentas. Devuelve (filas de mart_golpes_repetidos, fila de veredicto).

    `prep` es la de causal_exposicion.preparar: (D, celdas de D2, sorteos W, universo, cohortes)."""
    D, _cel_pri, W, wells, _coh = prep
    W5, fuera = extender_pesos(D, W, wells)
    posteriores = eventos_posteriores(D)
    trat = tratados_r1(D)
    bruto = celdas_r1(D, trat, H_CORTO)
    cel = celdas_por_mascara(bruto, _todos, fuera)
    n_eventos = int(len(posteriores[0]))
    n_s_2_7 = int(np.sum(posteriores[3] < S_MIN_POSTERIOR))
    n_en_celdas = int(sum(len(ce["tratados"]) for ce in cel))
    pozos_bruto = np.unique(np.concatenate([ce[k] for ce in bruto for k in ("tratados", "controles")])) \
        if bruto else np.zeros(0, dtype=np.int64)
    n_fuera = int(fuera[pozos_bruto].sum()) if len(pozos_bruto) else 0

    r = _att(D, cel, W5)
    pl = _placebo(D, cel, W5)
    rotura = bool(len(cel)) and rompe(float(pl["est"]), float(pl["ic_bajo"]), float(pl["ic_alto"]), UMBRAL_AGUA_PP)
    att_d2, d2_bajo, d2_alto, d2_n = _d2(con)
    v = veredicto_r1(int(r["n_tratados"]), rotura, float(r["ic_bajo"]), float(r["ic_alto"]), att_d2)

    filas = [_fila("att", "todos", None, r), _fila("placebo", "pretendencia", None, pl),
             (DISENO_R1, "d2", "ATT_W", None, d2_n, None, att_d2, d2_bajo, d2_alto)]
    orden = {(int(i), int(g)): int(k) for i, g, k in zip(*trat[:3])}
    for nombre, pred in (("k=2", lambda k: k == 2), ("k>=3", lambda k: k >= 3)):
        mascara = lambda ce, pred=pred: np.array([pred(orden[(int(i), ce["g"])]) for i in ce["tratados"]], dtype=bool)  # noqa: E731
        filas.append(_fila("orden", nombre, None, _att(D, celdas_por_mascara(cel, mascara), W5)))
    for b, (lo, hi) in enumerate(BANDAS_S):
        nombre = f"{lo}-{hi}" if hi is not None else f"{lo}+"
        filas.append(_fila("banda", nombre, None, _att(D, [ce for ce in cel if ce["banda"] == b], W5)))
    cel_serie = celdas_por_mascara(celdas_r1(D, trat, H_D5), _todos, fuera)
    if cel_serie:
        for e, rr in _serie(D, cel_serie, W5).items():
            filas.append(_fila("serie", "dW", int(e), rr))
    for nombre, n in zip(CUENTAS, (n_eventos, n_s_2_7, int(len(trat[0])), n_en_celdas, n_fuera)):
        filas.append((DISENO_R1, "cuenta", nombre, None, int(n), None, float(n), None, None))

    motivo = (f"ATT_R1 {r['est']:+.2f} (IC {r['ic_bajo']:+.2f} a {r['ic_alto']:+.2f}), tratados {r['n_tratados']}, "
              f"controles {r['n_controles']}, celdas {len(cel)}; placebo {pl['est']:+.2f} "
              f"(IC {pl['ic_bajo']:+.2f} a {pl['ic_alto']:+.2f}); D2 {att_d2:+.2f}; eventos de orden 2 o mas {n_eventos}, "
              f"con s de 2 a 7 {n_s_2_7}, elegibles {len(trat[0])}, en celdas con controles {n_en_celdas}, sin bloque {n_fuera}")
    print(f"R1: veredicto {v}; {motivo}")
    fila_v = (DISENO_R1, v, float(r["est"]), float(r["ic_bajo"]), float(r["ic_alto"]), int(r["n_tratados"]), motivo)
    return filas, fila_v


# ---- pagina

def _pp(x: float | None) -> str:
    return "—" if x is None or x != x else f"{x:+.1f}".replace(".", ",")


def pagina_golpes_repetidos(con) -> str:
    """wiki/hallazgos/golpes_repetidos.md a partir de mart_golpes_repetidos y mart_golpes_repetidos_veredicto."""
    ver = con.execute("select * from mart_golpes_repetidos_veredicto where diseno = ?", [DISENO_R1]).fetchone()
    filas = con.execute("select * from mart_golpes_repetidos").fetchall()
    d = {(f[1], f[2], f[3]): f for f in filas}
    v, est, bajo, alto, n = ver[1], ver[2], ver[3], ver[4], ver[5]
    cuenta = {f[2]: int(f[4]) for f in filas if f[1] == "cuenta"}
    d2 = d[("d2", "ATT_W", None)]
    lineas = [
        "# Golpes repetidos (R1)", "",
        "Un padre ya golpeado puede recibir otro hijo a menos de 1 km meses después. D2 mide solo el primer golpe de cada padre; "
        "D10 saca el segundo para ver si el primero persiste. R1 mide el efecto **del** golpe posterior: cada uno es un evento "
        "propio, y se lo compara con padres de la misma historia (ya golpeados antes, con su último golpe la misma cantidad de "
        f"meses atrás). La regla se fijó en {SHA_REGLA} antes de calcular ninguna cifra "
        f"(\"regla fijada en {SHA_REGLA} antes de calcular\").", "",
        f"**Veredicto: {v}.**", "",
        f"- ATT de R1 (suba del corte de agua de un golpe posterior, en puntos porcentuales): {_pp(est)} "
        f"(IC 95 %: {_pp(bajo)} a {_pp(alto)}), {n} golpes.",
        f"- El ATT de D2 con el que se compara (primer golpe): {_pp(d2[6])} (IC 95 %: {_pp(d2[7])} a {_pp(d2[8])}), "
        f"{d2[4]} tratados.",
    ]
    if n < MIN_TRATADOS_D5:
        lineas.append(f"- Con menos de {MIN_TRATADOS_D5} golpes con controles no hay veredicto: es un resultado terminado, "
                      "no una falla; abajo van las cuentas.")
    pl = d.get(("placebo", "pretendencia", None))
    if pl is not None:
        lineas.append(f"- Placebo (meses −3 a −1 antes del golpe): {_pp(pl[6])} (IC 95 %: {_pp(pl[7])} a {_pp(pl[8])}).")
    lineas.append("")
    serie = sorted((f for f in filas if f[1] == "serie"), key=lambda f: f[3])
    if serie:
        lineas += ["## Mes a mes desde el golpe posterior", "",
                   "| Mes (e) | dW (puntos porcentuales) | IC 95 % | Golpes que quedan |", "|---|---|---|---|"]
        lineas += [f"| {f[3]} | {_pp(f[6])} | {_pp(f[7])} a {_pp(f[8])} | {f[4]} |" for f in serie]
        lineas += ["", "Cada golpe sale de la serie desde su evento siguiente. Se publica sin veredicto.", ""]
    cortes = [f for f in filas if f[1] in ("orden", "banda")]
    if cortes:
        lineas += ["## Por orden y por tiempo desde el golpe anterior", "",
                   "| Corte | ATT (puntos porcentuales) | IC 95 % | Golpes |", "|---|---|---|---|"]
        lineas += [f"| {'orden ' if f[1] == 'orden' else 'meses desde el anterior: '}{f[2]} | {_pp(f[6])} | "
                   f"{_pp(f[7])} a {_pp(f[8])} | {f[4]} |" for f in cortes]
        lineas += ["", "Sin veredicto.", ""]
    if cuenta:
        lineas += ["## Cuentas", "",
                   f"- Golpes posteriores (orden 2 o más): {cuenta['eventos_orden_2_o_mas']}.",
                   f"- Con menos de {S_MIN_POSTERIOR} meses desde el anterior (se cuentan, no se estiman): {cuenta['s_2_a_7']}.",
                   f"- Elegibles: {cuenta['elegibles']}; en celdas con controles: {cuenta['en_celdas_con_controles']}.",
                   f"- Pozos sin bloque de 5 km que salen del bootstrap: {cuenta['pozos_sin_bloque']}.", ""]
    lineas += ["**Lo que no dice:** las tendencias paralelas valen condicionadas al tiempo desde el golpe anterior y no se "
               "pueden probar después de g; los golpes posteriores caen donde el relleno es denso, así que los tratados "
               "están seleccionados; los eventos con menos de 8 meses desde el anterior no se estiman; el golpe es por "
               "distancia de boca de pozo, no por distancia lateral.", ""]
    return "\n".join(lineas)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    prep = preparar(con)
    filas, fila_v = calcular(con, prep)
    _escribir(con, "mart_golpes_repetidos", COLS_R1, filas)
    _escribir(con, "mart_golpes_repetidos_veredicto", COLS_VEREDICTO, [fila_v])
    PAGINA.parent.mkdir(parents=True, exist_ok=True)
    PAGINA.write_text(pagina_golpes_repetidos(con), encoding="utf-8")
    print(f"escrito {PAGINA}")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(DATA / "warehouse.duckdb"))
    main(ap.parse_args().db)
