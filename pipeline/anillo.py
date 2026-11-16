"""Cierre a 6 meses y brecha del mes 1 con cuatro controles distintos del de 2 a 5 km.

Se corre despues de pipeline.descomposicion:  uv run python -m pipeline.anillo

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ninguna brecha con un control distinto del de 2 a 5 km; no se cambia
despues de ver resultados). Fuente: docs/proceso/siguientes-investigaciones.md, punto 1.

Pregunta: la brecha del mes 1 (hipotesis brecha_mes1: mediana de los padres cercanos menos mediana de los controles, menor que
-0,10) y su cierre a los 6 meses (hipotesis recuperacion_mes6: valor absoluto menor que 0,05) dependen de usar como control a los
padres cuyo hijo mas cercano esta a 2 a 5 km? La descomposicion (pipeline.descomposicion) ya mostro que ese control recibe algo de
efecto (2,8 puntos de brecha entre 5 a 10 km y 2 a 5 km), asi que el control de referencia puede achicar la brecha y, a los 6 meses,
disimular o fabricar un cierre. La brecha del mes 1 contra 5 a 10 km ya se publica; lo que falta es el mes 6 y las otras variantes.

Eventos y brecha: mismos eventos y mismo indice que el resultado principal (pipeline.placebo.marco con la base original, meses
-3 a -1; padres con al menos EDAD_MIN meses y base mayor que BASE_MIN; hijo mas cercano fija la distancia). Los 'cercanos' son los
de menos de 1 km (los 2.077 eventos del resultado principal, sin otra restriccion). Brecha = mediana del indice de los cercanos
menos mediana del indice de los controles (placebo.brecha_ic), con IC 95% de percentiles por pads hijo (REPS_BOOT del placebo), en
k = 1 y k = 6. El indice a k = 6 solo cuenta eventos que tienen ese mes en la base (como en el resultado principal).

Cuatro controles (los eventos con hijo mas cercano a la distancia indicada), con la restriccion indicada:
  V0 (referencia): 2 a 5 km, sin otra restriccion. Debe reproducir las dos hipotesis del libro (brecha_mes1 y recuperacion_mes6);
     si la brecha de V0 difiere de la del libro en mas de 0,005 en k = 1 o en k = 6, el modulo lo imprime y lo escribe en el
     veredicto como "no reproduce el libro" y el resultado de las demas variantes se publica igual.
  V1: 5 a 10 km, sin un hijo a menos de 1 km en los meses -6 a +3 del evento (la restriccion `limpio` de
     pipeline.descomposicion._marco_distancia; usar cargar_10km y _marco_distancia con la base original).
  V2: 2 a 10 km, con la misma restriccion que V1.
  V3: 2 a 5 km, sin un hijo a menos de 2 km en los meses -6 a +6 del evento (misma construccion que `limpio`, con 2 km y la ventana
     -6 a +6).
Los cercanos son los mismos en las cuatro variantes (no se les aplica la restriccion).

Veredicto (se publican todos los resultados, favorables o no):
  * "robusto a la eleccion del control": en las cuatro variantes la brecha del mes 1 es menor que -0,10 con IC 95% que excluye cero
    Y el valor absoluto de la brecha del mes 6 es menor que 0,05. Se agrega al README y a la pagina una linea que lo dice.
  * "la brecha del mes 1 depende del control": en alguna variante la brecha del mes 1 no es menor que -0,10 o su IC incluye cero.
    Se informa en que variantes.
  * "el cierre depende del control": la brecha del mes 1 cumple en las cuatro, pero en alguna el valor absoluto de la brecha del
    mes 6 es 0,05 o mas. Se informa en cuales y la frase del README sobre el cierre a 6 meses se escribe con ese control ("contra los
    controles de 2 a 5 km la brecha se cierra a los 6 meses; contra X, no").
  * Si pasan las dos cosas a la vez, el veredicto lista las dos.
Un diagnostico agregado despues de ver los resultados se rotula "agregado despues de ver los resultados" y no cambia el veredicto.

Que NO prueba:
  * No dice que el cierre sea recuperacion de la produccion: con datos mensuales un cierre preventivo y un dano se ven igual.
  * Los controles mas lejanos comparan zonas distintas (geologia, operador); una brecha distinta puede ser un gradiente entre zonas
    y no un cambio en la huella.
  * El IC es por pads hijo, sin ajuste por comparaciones multiples (hay cuatro variantes y dos meses).
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import placebo
from pipeline.costo import _escribir
from pipeline.descomposicion import cargar_10km
from pipeline.hallazgos import _BRECHA_K
from pipeline.ingest import DATA
from pipeline.placebo import _g

# Semillas del bootstrap por variante y mes: SEMILLA_PLACEBO + 700 + 10 * indice + (0 si k == 1 else 1).
DESPLAZAMIENTO_SEMILLA = 700

VARIANTES = (
    ("V0", "2 a 5 km"),
    ("V1", "5 a 10 km, limpio a 1 km"),
    ("V2", "2 a 10 km, limpio a 1 km"),
    ("V3", "2 a 5 km, limpio a 2 km"),
)
DESCRIPCION = dict(VARIANTES)

KS = (1, 6)
UMBRAL_MES1 = -0.10
UMBRAL_MES6 = 0.05
TOLERANCIA_LIBRO = 0.005


def _limpio(D10: dict, m: dict, km_cerca: float, vent_previa: int, vent_post: int) -> np.ndarray:
    """Padres del marco m sin un hijo a menos de km_cerca km entre mes - vent_previa y mes + vent_post.

    Replica pipeline.descomposicion._marco_distancia con parametros libres: (1.0, 6, 3) es su `limpio`,
    (2.0, 6, 6) es la restriccion de V3.
    """
    mes_par = D10["hijo_mes"][D10["par_hijo"]]
    cerca = np.flatnonzero(D10["par_km"] < km_cerca)
    k_cerca = np.sort(D10["par_padre"][cerca] * 100_000 + mes_par[cerca])
    clave = m["padre"] * 100_000 + m["mes"]
    n = (np.searchsorted(k_cerca, clave + vent_post, side="right")
         - np.searchsorted(k_cerca, clave - vent_previa, side="left"))
    return n == 0


def _mascara_control(variante: str, km: np.ndarray, limpio_1km: np.ndarray, limpio_2km: np.ndarray) -> np.ndarray:
    """Eventos que entran al control de cada variante segun la distancia del hijo mas cercano."""
    if variante == "V0":
        return (km >= 2) & (km < 5)
    if variante == "V1":
        return (km >= 5) & (km < 10) & limpio_1km
    if variante == "V2":
        return (km >= 2) & (km < 10) & limpio_1km
    if variante == "V3":
        return (km >= 2) & (km < 5) & limpio_2km
    raise ValueError(variante)


def _ic_excluye_cero(lo: float, hi: float) -> bool:
    # AMBIGUO: un IC no computable (NaN por n chico) cuenta como que no excluye cero, o sea no cumple el mes 1.
    return bool(np.isfinite(lo) and np.isfinite(hi) and (hi < 0 or lo > 0))


def veredicto(filas) -> tuple[str, str]:
    """Codigo y texto del veredicto a partir de filas (variante, k, brecha, ic_bajo, ic_alto). Funcion pura."""
    b1 = {v: None for v, _ in VARIANTES}
    b6 = {v: None for v, _ in VARIANTES}
    for variante, k, brecha, lo, hi in filas:
        if variante not in b1:
            raise ValueError(variante)
        if k == 1:
            b1[variante] = (brecha, lo, hi)
        elif k == 6:
            b6[variante] = (brecha, lo, hi)
        else:
            raise ValueError(k)
    if any(v is None for v in list(b1.values()) + list(b6.values())):
        raise ValueError("faltan filas de alguna variante o mes")
    falla_mes1 = [v for v, _ in VARIANTES if not (b1[v][0] < UMBRAL_MES1 and _ic_excluye_cero(b1[v][1], b1[v][2]))]
    # AMBIGUO: una brecha de mes 6 no computable (NaN) cuenta como no cerrada, y las fallas de cierre se listan
    # aunque la variante tambien falle el mes 1 (el codigo combinado lista las dos cosas).
    falla_cierre = [v for v, _ in VARIANTES if not abs(b6[v][0]) < UMBRAL_MES6]

    def _nombres(vs) -> str:
        return ", ".join(f"{v} ({DESCRIPCION[v]})" for v in vs)

    if not falla_mes1 and not falla_cierre:
        codigo = "robusto a la eleccion del control"
        texto = ("en las cuatro variantes la brecha del mes 1 es menor que -0,10 con IC 95% que excluye cero y el valor "
                 "absoluto de la brecha del mes 6 es menor que 0,05: ni la brecha del mes 1 ni su cierre a los 6 meses "
                 "dependen del control usado")
    elif falla_mes1 and not falla_cierre:
        codigo = "la brecha del mes 1 depende del control"
        texto = (f"la brecha del mes 1 no es menor que -0,10 o su IC 95% incluye cero en: {_nombres(falla_mes1)}; el cierre "
                 "a los 6 meses cumple en las cuatro variantes")
    elif not falla_mes1 and falla_cierre:
        codigo = "el cierre depende del control"
        # AMBIGUO: la frase fija supone que V0 cierra; si V0 es el que no cierra se usa la forma alternativa.
        if "V0" in falla_cierre:
            otros = [v for v in falla_cierre if v != "V0"]
            texto = ("la brecha del mes 1 cumple en las cuatro variantes; ni contra los controles de 2 a 5 km la brecha se "
                     "cierra a los 6 meses"
                     + (f"; tampoco se cierra contra {_nombres(otros)}" if otros else ""))
        else:
            texto = ("la brecha del mes 1 cumple en las cuatro variantes; contra los controles de 2 a 5 km la brecha se cierra "
                     f"a los 6 meses; contra {_nombres(falla_cierre)}, no")
    else:
        codigo = "la brecha del mes 1 y el cierre dependen del control"
        texto = (f"la brecha del mes 1 no cumple en: {_nombres(falla_mes1)}; y el cierre a los 6 meses no cumple en: "
                 f"{_nombres(falla_cierre)}")
    return codigo, texto


COLS_ANILLO = [("variante", "varchar"), ("descripcion", "varchar"), ("k", "integer"), ("n_cercano", "integer"),
               ("n_control", "integer"), ("mediana_cercano", "double"), ("mediana_control", "double"),
               ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_VEREDICTO = [("codigo", "varchar"), ("texto", "varchar"), ("detalle", "varchar")]


def pagina_anillo(con) -> str:
    """Pagina de wiki a partir de los marts de anillo.py. Texto en espanol, sin rayas largas."""
    filas = con.execute("select variante, descripcion, k, n_cercano, n_control, brecha, ic_bajo, ic_alto from mart_anillo "
                        "order by variante, k").fetchall()
    codigo, texto, detalle = con.execute("select codigo, texto, detalle from mart_anillo_veredicto limit 1").fetchall()[0]
    L = ["# Anillo de control: mes 1 y mes 6 con cuatro controles distintos", "",
         "Página generada por `pipeline/anillo.py`. Pregunta si la brecha del mes 1 y su cierre a los 6 meses dependen de "
         "usar como control a los padres cuyo hijo más cercano está a 2 a 5 km.",
         "Los cercanos son siempre los mismos (menos de 1 km); lo único que cambia entre variantes es el control.",
         "Cada variante informa la brecha en k = 1 y k = 6 con IC 95% por pads hijo.", "",
         "## Veredicto", "",
         f"**{codigo}**: {texto}.", "",
         f"Control de consistencia: {detalle}.", "",
         "## Brechas por variante", "",
         "| Variante | Control | k | n cercano | n control | Brecha | IC 95% |",
         "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for v, desc, k, nn, nc, b, lo, hi in filas:
        L.append(f"| {v} | {desc} | {k} | {_g(nn)} | {_g(nc)} | {_g(b, 3)} | {_g(lo, 3)} a {_g(hi, 3)} |")
    L += ["", "## Qué no prueba", "",
          "- No dice que el cierre sea recuperación de la producción: con datos mensuales un cierre preventivo y un daño "
          "se ven igual.",
          "- Los controles más lejanos comparan zonas distintas (geología, operador); una brecha distinta puede ser un "
          "gradiente entre zonas y no un cambio en la huella.",
          "- El IC es por pads hijo, sin ajuste por comparaciones múltiples (hay cuatro variantes y dos meses).", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    D10 = cargar_10km(con, placebo.cargar(con))
    m = placebo.marco(D10, D10["hijo_mes"], ks=KS, base=placebo.BASE_ORIGINAL)
    limpio_1km = _limpio(D10, m, 1.0, 6, 3)
    limpio_2km = _limpio(D10, m, 2.0, 6, 6)
    cercanos = m["km"] < 1
    filas = []
    for vi, (variante, descripcion) in enumerate(VARIANTES):
        ctrl = _mascara_control(variante, m["km"], limpio_1km, limpio_2km)
        for k in KS:
            banda = np.full(len(m["km"]), 1)
            banda[cercanos] = 0
            banda[ctrl] = 2
            semilla = placebo.SEMILLA_PLACEBO + DESPLAZAMIENTO_SEMILLA + 10 * vi + (0 if k == 1 else 1)
            r = placebo.brecha_ic(m["idx"][k], banda, m["clave"], placebo.REPS_BOOT, semilla)
            filas.append((variante, descripcion, k, r["n_near"], r["n_ctrl"], r["near"], r["ctrl"], r["brecha"],
                          r["ic_bajo"], r["ic_alto"]))
    _escribir(con, "mart_anillo", COLS_ANILLO, filas)
    libro1 = con.execute(_BRECHA_K.format(k=1)).fetchall()[0][0]
    libro6 = con.execute(_BRECHA_K.format(k=6)).fetchall()[0][0]
    v0 = {r[2]: r for r in filas if r[0] == "V0"}
    d1, d6 = abs(v0[1][7] - libro1), abs(v0[6][7] - libro6)
    reproduce = d1 <= TOLERANCIA_LIBRO and d6 <= TOLERANCIA_LIBRO
    estado_libro = "reproduce el libro" if reproduce else "no reproduce el libro"
    detalle = (f"V0 {estado_libro}: libro k=1 {_g(libro1, 4)} contra V0 {_g(v0[1][7], 4)} (dif {_g(d1, 4)}), libro k=6 "
               f"{_g(libro6, 4)} contra V0 {_g(v0[6][7], 4)} (dif {_g(d6, 4)}); tolerancia {_g(TOLERANCIA_LIBRO, 3)}")
    codigo, texto = veredicto([(r[0], r[2], r[7], r[8], r[9]) for r in filas])
    _escribir(con, "mart_anillo_veredicto", COLS_VEREDICTO, [(codigo, texto, detalle)])
    for r in filas:
        print(f"[anillo] {r[0]} {r[1]} k={r[2]} n_cercano={r[3]} n_control={r[4]} brecha={r[7]:+.4f} "
              f"IC {r[8]:+.4f} a {r[9]:+.4f}")
    print(f"[anillo] libro k=1 {libro1:+.4f} V0 {v0[1][7]:+.4f} dif {d1:.4f}; libro k=6 {libro6:+.4f} V0 {v0[6][7]:+.4f} "
          f"dif {d6:.4f}: {estado_libro}")
    print(f"[anillo] veredicto: {codigo}: {texto}")
    print(f"[anillo] detalle: {detalle}")
    con.close()


if __name__ == "__main__":
    main()
