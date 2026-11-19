"""Dosis del pad y cercania: la version mas favorable de la fisica de los golpes de fractura.

Se corre despues de pipeline.dosis:  uv run python -m pipeline.dosis_pad

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ningun coeficiente con la dosis del pad ni con la interaccion; no se
cambia despues de ver resultados). Fuente: docs/proceso/siguientes-investigaciones.md, punto 3. Es una prueba AGREGADA DESPUES DE VER
LOS RESULTADOS de pipeline.dosis y pipeline.dosis_meses (los dos dieron cero variables que cumplen): se elige la lectura mas favorable
a la fisica, justamente para que un nulo pese mas. Solo se miro la cobertura (cuantos eventos tienen cada variable y cuantos tienen
km_min < 0,5), nunca la caida. Cobertura mirada: 2.077 eventos 'cercano'; 660 con km_min < 0,5 y las variables completas, de 149 pads
hijo; 1.584 con las variables completas en total, de 268 pads hijo.

Idea: la dosis de un golpe de fractura no es el trabajo de un solo pozo sino el de todos los pozos del pad que se fracturan juntos, y
la interaccion fisica mas fuerte es padre depletado y hijo muy cerca. Si ni con eso aparece respuesta, la lectura "el dato publico
no muestra dosis y respuesta" queda mas firme.

Dosis del pad. Pad = el pad_id de int_pozo_ubicacion del hijo_cercano (el mismo pad hijo que ya es el conglomerado del bootstrap; el
pad_id de int_interferencia_evento es el del padre y NO se usa). Pozos del pad en la ventana: todos los pozos de int_pozo_ubicacion
con ese pad_id, salvo el padre del evento, cuyo primer trabajo de fractura (el de la primera fecha_inicio del pozo en stg_fractura,
el mismo criterio de pipeline.dosis._trabajos_hijo) cae en el mes calendario de mes_frac o en el anterior o el siguiente (mes_frac - 1
a mes_frac + 1). El hijo_cercano entra siempre (su primer trabajo fija mes_frac). Por pozo: arena = suma de arena_tn de las filas del
primer trabajo, rama = maximo de rama_horizontal_m, presion = maximo de presion_maxima_psi. Variables (todas con signo esperado
POSITIVO: mas dosis, mas caida), cada una estandarizada (media 0, desvio 1) dentro de la muestra del analisis:
  1. arena total del pad: logaritmo natural de la suma de arena_tn de los pozos en la ventana (solo cuentan los pozos con arena > 0);
  2. arena por metro de rama del pad: logaritmo natural de (suma de arena de los pozos con arena > 0 y rama > 0) / (suma de la rama
     de esos mismos pozos);
  3. presion maxima de tratamiento del pad: maximo de los pozos con 0 < presion < 20.000 psi, en psi sin transformar;
  4. depleccion del padre, igual que en pipeline.dosis (variable 4 de dosis._dataset_a).
Una variable queda faltante (el evento sale del analisis) si ningun pozo en la ventana la aporta. La ventana de un mes alrededor es la
definicion principal; la variante de mismo mes (solo mes_frac) es una sensibilidad.

Modelo conjunto del pad, muestra completa: exactamente el de pipeline.dosis.analizar (cuatro variables a la vez, los mismos controles
de dosis._controles incluidas las dummies de terminacion del hijo_cercano, efectos fijos de area por ano, caso completo de las cuatro
variables y de los controles, bootstrap por pads hijo B = 2.000 con dosis._ajuste, p de dos colas de la regla, Holm sobre 4 pruebas,
alfa = 0,05), para el resultado A (caida del indice al mes 1, el principal) y el resultado B (caudal por dia, informado aparte).
Cumple = coeficiente positivo y p ajustado menor que 0,05; signo contrario = negativo y p ajustado menor que 0,05.

Modelo de cercania (subconjunto): los eventos del caso completo con km_min < 0,5. Mismas cuatro variables del pad mas UNA interaccion:
proximidad = menos km_min; interaccion = estandarizacion (media 0, desvio 1, dentro del subconjunto) del producto de la depleccion
estandarizada y la proximidad estandarizada. km_min ya es un control, asi que la interaccion tiene su efecto principal. Un solo
modelo conjunto con las cinco, mismos controles y efectos fijos (definidos dentro del subconjunto), bootstrap por pads hijo B = 2.000,
Holm sobre 5 pruebas (las cuatro variables y la interaccion), para A y para B. Signo esperado de la interaccion: POSITIVO (mas caida
con padre depletado y hijo mas cerca).

Veredicto (con el resultado A; se publican todos los coeficientes, favorables o no; B se informa aparte con el mismo codigo y no
cambia el de A):
  * "no concluyente por muestra": si no se cumple ninguna regla positiva y el modelo de muestra completa tiene menos de 1.000 eventos
    o menos de 150 pads hijo, o el subconjunto tiene menos de 400 eventos o menos de 100 pads hijo (con esta cobertura no deberia
    pasar).
  * "dosis del pad y respuesta": dos o mas de las cuatro variables del pad cumplen en el modelo de muestra completa. Se escribe que
    la caida crece con la dosis del pad con las variables que cumplen; con la cercania se informa aparte.
  * "una sola variable del pad": exactamente una cumple en el modelo de muestra completa. No alcanza la regla; no se escribe que la
    caida crece con la dosis.
  * "respuesta solo en la cercania": ninguna de las cuatro cumple en la muestra completa pero alguna de las cinco pruebas del
    subconjunto cumple (se informa cual). Se rotula exploratoria (subconjunto elegido despues de ver resultados, nueve pruebas en
    total), no cambia el veredicto de pipeline.dosis y no se escribe como dosis y respuesta.
  * "sigue sin dosis y respuesta": ninguna de las cuatro del pad cumple en la muestra completa y ninguna de las cinco cumple en el
    subconjunto. Se escribe que tampoco con la dosis del pad ni en la cercania aparece respuesta, con el semiancho mayor de los IC
    sin ajustar en desvios de la caida (muestra completa y subconjunto), para que se lea cuanto efecto queda descartado.
  * Celdas de signo contrario se informan aparte y nunca cuentan como cumplidas. El orden se aplica de arriba abajo.
Sensibilidad (se informa, NO entra en el veredicto): el modelo de muestra completa con la ventana de mismo mes, B = 1.000.
Cualquier otro diagnostico agregado despues de ver los resultados se rotula "agregado despues de ver los resultados" y no cambia el
veredicto.

CORRECCION DE REDACCION (2026-11-17, despues de ver los resultados, revision de Opus; no cambia ningun codigo ni la regla): el semiancho
mide la precision, no el efecto descartado; el texto del veredicto publica la cota superior del IC (limite alto, en desvios de la caida).

Que NO prueba:
  * Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real, la geometria de la fractura y el hijo que de
    verdad golpeo al padre no estan en el dato publico; la dosis del pad suma pozos que pueden estar lejos del padre.
  * Un coeficiente positivo no separaria el golpe de un cierre preventivo mas largo cuanto mas grande es el trabajo.
  * El subconjunto km_min < 0,5 es chico (cientos de eventos) y el IC de la interaccion puede ser ancho; el semiancho se publica.
  * Los eventos de un mismo pad hijo comparten calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.
"""
from __future__ import annotations

import math

import duckdb
import numpy as np

from pipeline import dosis
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

VARIABLES_PAD = ("arena_pad", "arena_rama_pad", "presion_pad", "deplecion")
NOMBRES_PAD = {
    "arena_pad": "arena total del pad",
    "arena_rama_pad": "arena por metro de rama del pad",
    "presion_pad": "presión máxima del pad",
    "deplecion": "depleción del padre",
    "interaccion": "interacción depleción por cercanía",
}
INTERACCION = "interaccion"
VARIABLES_CERCA = ("arena_pad", "arena_rama_pad", "presion_pad", "deplecion", "interaccion")

RES_OFFSET = {"A": 0, "B": 50}
OFFSET_PAD = 600
ANA_COMPLETO = 10
ANA_CERCANIA = 11
ANA_MISMO_MES = 12
ANA_SOLA = 20  # agregado despues de ver los resultados: 20 + indice de la variable

COLS_PAD = [("resultado", "varchar"), ("modelo", "varchar"), ("variable", "varchar"),
            ("coef_sd", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
            ("p", "double"), ("p_holm", "double"), ("n", "integer"), ("pads", "integer"),
            ("cumple", "boolean"), ("signo_contrario", "boolean")]
COLS_VEREDICTO_PAD = [("resultado", "varchar"), ("codigo", "varchar"), ("texto", "varchar")]


def _semilla(res: str, ana: int) -> int:
    return dosis.SEMILLA_DOSIS + OFFSET_PAD + RES_OFFSET[res] + ana


def _mes_idx(fecha):
    if fecha is None:
        return None
    if hasattr(fecha, "year") and hasattr(fecha, "month"):
        return int(fecha.year) * 12 + int(fecha.month)
    if isinstance(fecha, str):
        try:
            partes = fecha.split("-")
            return int(partes[0]) * 12 + int(partes[1])
        except (ValueError, IndexError):
            return None
    return None


def pad_dose(pozos_pad, padre, m0, w):
    """Variables del pad (v1, v2, v3) sobre pozos ya agregados por pozo.

    `pozos_pad` es una lista de dicts con claves pozo_id, arena, rama, presion, m
    (m es indice de mes ano*12+mes del primer trabajo). Excluye al padre y exige
    abs(m - m0) <= w. v1 = ln(suma de arena con arena > 0), v2 = ln(suma arena /
    suma rama sobre pozos con arena > 0 y rama > 0), v3 = max presion con
    0 < presion < 20000. Faltante es nan.
    """
    m0 = int(m0)
    w = int(w)
    ventana = [p for p in pozos_pad
               if p.get("pozo_id") != padre and p.get("m") is not None
               and abs(int(p["m"]) - m0) <= w]
    suma = 0.0
    hay1 = False
    for p in ventana:
        a = p.get("arena")
        if a is not None and a > 0:
            suma += float(a)
            hay1 = True
    v1 = math.log(suma) if hay1 and suma > 0 else float("nan")
    sa, sr = 0.0, 0.0
    hay2 = False
    for p in ventana:
        a = p.get("arena")
        r = p.get("rama")
        if a is not None and r is not None and a > 0 and r > 0:
            sa += float(a)
            sr += float(r)
            hay2 = True
    v2 = math.log(sa / sr) if hay2 and sa > 0 and sr > 0 else float("nan")
    pres = []
    for p in ventana:
        pr = p.get("presion")
        if pr is not None and 0 < float(pr) < 20000:
            pres.append(float(pr))
    v3 = max(pres) if pres else float("nan")
    return (v1, v2, v3)


def _primer_trabajo_por_pozo(filas):
    por_pozo: dict = {}
    for f in filas:
        por_pozo.setdefault(f["pozo_id"], []).append(f)
    out = {}
    for pozo, todos in por_pozo.items():
        cand = [f for f in todos if f["fecha_inicio"] is not None]
        if not cand:
            continue
        primera = min(f["fecha_inicio"] for f in cand)
        job = [f for f in cand if f["fecha_inicio"] == primera]
        arenas = [f["arena_tn"] for f in job if f["arena_tn"] is not None]
        ramas = [f["rama_horizontal_m"] for f in job if f["rama_horizontal_m"] is not None]
        pres = [f["presion_maxima_psi"] for f in job if f["presion_maxima_psi"] is not None]
        out[pozo] = {"arena": sum(arenas) if arenas else None,
                     "rama": max(ramas) if ramas else None,
                     "presion": max(pres) if pres else None,
                     "m": _mes_idx(primera)}
    return out


def _variables_pad(con, d, w):
    """Arreglos v1, v2, v3 del pad alineados con d, con ventana +-w meses."""
    frac = dosis._filas(con, "select pozo_id, fecha_inicio, rama_horizontal_m, arena_tn, "
                             "presion_maxima_psi from stg_fractura")
    trab = _primer_trabajo_por_pozo(frac)
    pozo_pad: dict = {}
    for r in dosis._filas(con, "select pozo_id, pad_id from int_pozo_ubicacion"):
        try:
            pid = int(r["pozo_id"])
        except (TypeError, ValueError):
            pid = r["pozo_id"]
        pozo_pad[pid] = r["pad_id"]
    pad_pozos: dict = {}
    for pozo, t in trab.items():
        try:
            pid = int(pozo)
        except (TypeError, ValueError):
            pid = pozo
        pad = pozo_pad.get(pid)
        if pad is None or t["m"] is None:
            continue
        pad_pozos.setdefault(pad, []).append({"pozo_id": pid, "arena": t["arena"],
                                              "rama": t["rama"], "presion": t["presion"],
                                              "m": t["m"]})
    n = len(d["padre"])
    v1 = np.full(n, np.nan)
    v2 = np.full(n, np.nan)
    v3 = np.full(n, np.nan)
    for i in range(n):
        try:
            hijo = int(d["hijo"][i])
        except (TypeError, ValueError):
            hijo = d["hijo"][i]
        pad = pozo_pad.get(hijo)
        if pad is None:
            continue
        m0 = _mes_idx(d["mes"][i])
        if m0 is None:
            continue
        try:
            padre = int(d["padre"][i])
        except (TypeError, ValueError):
            padre = d["padre"][i]
        a, b, c = pad_dose(pad_pozos.get(pad, []), padre, m0, w)
        v1[i], v2[i], v3[i] = a, b, c
    return v1, v2, v3


def interaccion_cercania(v4_sub, km_sub):
    """Interaccion estandarizada dentro del subconjunto: std(std(v4) * std(-km))."""
    v4s = dosis._std(np.asarray(v4_sub, dtype=float))
    kxs = dosis._std(-np.asarray(km_sub, dtype=float))
    return dosis._std(v4s * kxs)


def _cota(ics, y_std):
    """Mayor limite alto de los IC sin ajustar, en desvios de la caida (efecto positivo mas grande compatible)."""
    if not np.isfinite(y_std) or y_std <= 0:
        return float("nan")
    return float(np.max(np.asarray(ics, dtype=float)[:, 1]) / y_std)


def _semiancho(ics, y_std):
    if not np.isfinite(y_std) or y_std <= 0:
        return float("nan")
    ics = np.asarray(ics, dtype=float)
    return float(np.max((ics[:, 1] - ics[:, 0]) / 2) / y_std)


def _modelo_completo(y, d2, res, semilla, reps):
    y = np.asarray(y, dtype=float)
    base = np.flatnonzero(np.isfinite(y))
    ib = base[dosis._mascara_controles(d2, base)]
    cc = ib[np.all([np.isfinite(d2[f"v{j + 1}"][ib]) for j in range(4)], axis=0)]
    if len(cc) == 0:
        nan4 = np.full(4, np.nan)
        return {"coefs": nan4, "ics": np.full((4, 2), np.nan), "ps": np.ones(4),
                "ph": np.ones(4), "n": 0, "pads": 0, "cc": cc, "semiancho": float("nan"), "cota": float("nan")}
    X = np.column_stack([dosis._std(d2[f"v{j + 1}"][cc]) for j in range(4)])
    C, grupo = dosis._controles(d2, cc)
    coefs, ics, ps = dosis._ajuste(y[cc], X, C, grupo, d2["cluster"][cc], semilla, reps)
    ph = dosis._holm(ps)
    sd = float(y[cc].std())
    return {"coefs": coefs, "ics": ics, "ps": ps, "ph": ph, "n": len(cc),
            "pads": len(set(d2["cluster"][cc])), "cc": cc, "semiancho": _semiancho(ics, sd), "cota": _cota(ics, sd)}


def _modelo_cercania(y, d2, cc, res, semilla):
    y = np.asarray(y, dtype=float)
    cc = np.asarray(cc)
    sub = cc[np.asarray(d2["km"][cc]) < 0.5]
    if len(sub) == 0:
        nan5 = np.full(5, np.nan)
        return {"coefs": nan5, "ics": np.full((5, 2), np.nan), "ps": np.ones(5),
                "ph": np.ones(5), "n": 0, "pads": 0, "sub": sub, "semiancho": float("nan"), "cota": float("nan")}
    X4 = np.column_stack([dosis._std(d2[f"v{j + 1}"][sub]) for j in range(4)])
    inter = interaccion_cercania(d2["v4"][sub], d2["km"][sub])
    X = np.column_stack([X4, inter])
    C, grupo = dosis._controles(d2, sub)
    coefs, ics, ps = dosis._ajuste(y[sub], X, C, grupo, d2["cluster"][sub], semilla, dosis.B_MAIN)
    ph = dosis._holm(ps)
    sd = float(y[sub].std())
    return {"coefs": coefs, "ics": ics, "ps": ps, "ph": ph, "n": len(sub),
            "pads": len(set(d2["cluster"][sub])), "sub": sub, "semiancho": _semiancho(ics, sd), "cota": _cota(ics, sd)}


def _diagnostico_sola(res, y, d2, cc):
    """Agregado despues de ver los resultados (revision de Opus, 2026-11-17): cada variable del pad sola con los controles y el FIV.

    No entra en el veredicto. Filas del mart con modelo 'sola' (coeficientes) y 'vif' (coef_sd lleva el FIV, el resto nan).
    """
    cc = np.asarray(cc)
    if len(cc) == 0:
        return []
    y = np.asarray(y, dtype=float)
    X = np.column_stack([dosis._std(d2[f"v{j + 1}"][cc]) for j in range(4)])
    C, grupo = dosis._controles(d2, cc)
    n, pads = len(cc), len(set(d2["cluster"][cc]))
    vif = dosis._vif(X, C, grupo)
    nan = float("nan")
    filas = []
    for j, var in enumerate(VARIABLES_PAD):
        c, ic, p = dosis._ajuste(y[cc], X[:, [j]], C, grupo, d2["cluster"][cc],
                                 _semilla(res, ANA_SOLA + j), dosis.B_SENS)
        filas.append((res, "sola", var, float(c[0]), float(ic[0][0]), float(ic[0][1]), float(p[0]), nan, n, pads,
                      False, False))
        filas.append((res, "vif", var, float(vif[j]), nan, nan, nan, nan, n, pads, False, False))
    return filas


def veredicto(cum_completo: list[str], cum_cercania: list[str], contra: list[str],
              n_c, pads_c, n_s, pads_s, semiancho_c=None, semiancho_s=None, cota_c=None, cota_s=None) -> tuple[str, str]:
    """Codigo y texto del veredicto de la regla, para un resultado (A o B)."""
    cum_completo = list(cum_completo)
    cum_cercania = list(cum_cercania)
    contra = list(contra)
    if len(cum_completo) >= 2:
        codigo = "dosis del pad y respuesta"
    elif len(cum_completo) == 1:
        codigo = "una sola variable del pad"
    elif len(cum_cercania) >= 1:
        codigo = "respuesta solo en la cercania"
    else:
        codigo = "sigue sin dosis y respuesta"
    if codigo != "dosis del pad y respuesta" and (n_c < 1000 or pads_c < 150 or n_s < 400 or pads_s < 100):
        codigo = "no concluyente por muestra"
    suf = ""
    if contra:
        suf = "; signo contrario en " + dosis._unir(contra)
    if codigo == "dosis del pad y respuesta":
        texto = (f"la caída crece con la dosis del pad: {dosis._unir(cum_completo)} cumplen "
                 "en el modelo de muestra completa")
        if cum_cercania:
            texto += f"; en la cercanía cumple {dosis._unir(cum_cercania)}"
        else:
            texto += "; en la cercanía se informa aparte"
    elif codigo == "una sola variable del pad":
        texto = (f"solo {cum_completo[0]} cumple en el modelo de muestra completa: no alcanza la regla "
                 "de dos o más; no se escribe que la caída crece con la dosis")
    elif codigo == "respuesta solo en la cercania":
        texto = (f"ninguna de las cuatro cumple en la muestra completa pero cumple "
                 f"{dosis._unir(cum_cercania)} en la cercanía: respuesta exploratoria sobre nueve pruebas, "
                 "subconjunto elegido después de ver resultados; no cambia el veredicto de pipeline.dosis "
                 "y no se escribe como dosis y respuesta")
    elif codigo == "sigue sin dosis y respuesta":
        texto = ("ninguna de las cuatro del pad cumple en la muestra completa y ninguna de las cinco cumple "
                 "en la cercanía: tampoco con la dosis del pad ni en la cercanía aparece respuesta")
        if cota_c is not None and cota_s is not None:
            texto += (f"; la cota superior mayor de los IC sin ajustar es de {_g(cota_c, 2)} desvíos de la "
                      f"caída en la muestra completa y {_g(cota_s, 2)} en la cercanía: el efecto positivo "
                      "compatible con los datos llega, como mucho, a eso")
        elif semiancho_c is not None and semiancho_s is not None:
            texto += (f"; el semiancho mayor de los IC sin ajustar es de {_g(semiancho_c, 2)} desvíos de la "
                      f"caída en la muestra completa y {_g(semiancho_s, 2)} en la cercanía (mide la precisión, "
                      "no el efecto descartado)")
    else:
        texto = (f"muestra chica para juzgar (muestra completa n = {_g(n_c)}, {_g(pads_c)} pads hijo; "
                 f"cercanía n = {_g(n_s)}, {_g(pads_s)} pads hijo; la regla pide 1.000 eventos y 150 pads "
                 "en la completa y 400 eventos y 100 pads en la cercanía): el modelo se publica pero el "
                 "veredicto queda no concluyente por muestra")
    return codigo, texto + suf


def pagina_dosis_pad(con) -> str:
    """Pagina de wiki a partir de los marts de dosis_pad.py. Texto en espanol, sin rayas largas."""
    mod = {(r[0], r[1], r[2]): r for r in con.execute("select resultado, modelo, variable, coef_sd, ic_bajo, "
                                                     "ic_alto, p_holm, n, pads, cumple "
                                                     "from mart_dosis_pad").fetchall()}
    ver = {r[0]: (r[1], r[2]) for r in con.execute("select resultado, codigo, texto "
                                                  "from mart_dosis_pad_veredicto").fetchall()}
    L = ["# Dosis del pad y cercanía", "",
         "Página generada por `pipeline/dosis_pad.py`. Pregunta si la caída del padre crece con la dosis de todo ",
         "el pad del hijo y con la interacción de padre depletado e hijo muy cerca.",
         "Prueba agregada después de ver los resultados de pipeline.dosis y pipeline.dosis_meses, con la lectura ",
         "más favorable a la física para que un nulo pese más.", "",
         "## Veredicto", ""]
    for res in ("A", "B"):
        codigo, texto = ver[res]
        L.append(f"Resultado {res}: **{codigo}**: {texto}.")
    L.append("")
    for res, titulo in (("A", "Resultado A, caída del índice"), ("B", "Resultado B, caída del caudal por día")):
        for modelo, tit_m in (("completo", "muestra completa"), ("cercania", "cercanía km menor que 0,5")):
            vars_m = VARIABLES_PAD if modelo == "completo" else VARIABLES_CERCA
            r0 = mod[(res, modelo, vars_m[0])]
            L += [f"### {titulo}, {tit_m} (n = {_g(r0[7])}, pads = {_g(r0[8])})", "",
                  "| Variable | Coef por desvío | IC 95% | p Holm | Cumple |",
                  "| --- | ---: | --- | ---: | --- |"]
            for var in vars_m:
                _re, _mo, _va, c, lo, hi, ph, _n, _pa, cu = mod[(res, modelo, var)]
                L.append(f"| {NOMBRES_PAD[var]} | {_g(c, 3)} | {_g(lo, 3)} a {_g(hi, 3)} | {_g(ph, 3)} | "
                         f"{'sí' if cu else 'no'} |")
            L.append("")
    L += ["## Sensibilidad (mismo mes)", "",
          "Modelo de muestra completa con la ventana de mismo mes (se informa, no entra en el veredicto).", ""]
    for res in ("A", "B"):
        r0 = mod[(res, "mismo_mes", VARIABLES_PAD[0])]
        L += [f"### Resultado {res} (n = {_g(r0[7])}, pads = {_g(r0[8])})", "",
              "| Variable | Coef por desvío | IC 95% | p Holm | Cumple |",
              "| --- | ---: | --- | ---: | --- |"]
        for var in VARIABLES_PAD:
            _re, _mo, _va, c, lo, hi, ph, _n, _pa, cu = mod[(res, "mismo_mes", var)]
            L.append(f"| {NOMBRES_PAD[var]} | {_g(c, 3)} | {_g(lo, 3)} a {_g(hi, 3)} | {_g(ph, 3)} | "
                     f"{'sí' if cu else 'no'} |")
        L.append("")
    sola = [(r[0], r[2], r[3], r[4], r[5]) for r in con.execute(
        "select resultado, modelo, variable, coef_sd, ic_bajo, ic_alto from mart_dosis_pad where modelo = 'sola' "
        "order by resultado").fetchall()]
    vifs = {(r[0], r[1]): r[2] for r in con.execute(
        "select resultado, variable, coef_sd from mart_dosis_pad where modelo = 'vif'").fetchall()}
    if sola:
        L += ["## Cada variable sola (agregado después de ver los resultados)", "",
              "Diagnóstico agregado después de ver los resultados, a pedido de una revisión: cada variable del pad sola con los "
              "controles, y el FIV en el modelo conjunto. No entra en el veredicto.", "",
              "| Resultado | Variable | Coef por desvío (IC 95%) | FIV conjunto |", "| --- | --- | --- | ---: |"]
        for res, var, c, lo, hi in sola:
            L.append(f"| {res} | {NOMBRES_PAD[var]} | {_g(c, 3)} ({_g(lo, 3)} a {_g(hi, 3)}) | "
                     f"{_g(vifs.get((res, var), float('nan')), 1)} |")
        L.append("")
    L += ["## Qué no prueba", "",
          "- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real, la geometría de la ",
          "fractura y el hijo que de verdad golpeó al padre no están en el dato público; la dosis del pad suma pozos ",
          "que pueden estar lejos del padre.",
          "- Un coeficiente positivo no separaría el golpe de un cierre preventivo más largo cuanto más grande es el trabajo.",
          "- El subconjunto km menor que 0,5 es chico (cientos de eventos) y el IC de la interacción puede ser ancho; ",
          "el semiancho se publica.",
          "- Los eventos de un mismo pad hijo comparten calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.",
          ""]
    return "\n".join(L)


def _filas_modelo(res, modelo, variables, r):
    filas = []
    cumplen, contrarias = [], []
    for j, var in enumerate(variables):
        cu = bool(r["coefs"][j] > 0 and r["ph"][j] < 0.05)
        ct = bool(r["coefs"][j] < 0 and r["ph"][j] < 0.05)
        if cu:
            cumplen.append(NOMBRES_PAD[var])
        if ct:
            contrarias.append(NOMBRES_PAD[var])
        filas.append((res, modelo, var, float(r["coefs"][j]), float(r["ics"][j][0]),
                      float(r["ics"][j][1]), float(r["ps"][j]), float(r["ph"][j]),
                      r["n"], r["pads"], cu, ct))
    return filas, cumplen, contrarias


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    d = dosis._dataset_a(con)
    yA = np.asarray(d["caida"], dtype=float)
    yB = np.asarray(dosis._caida_b(con, d), dtype=float)
    print(f"[dosis_pad] eventos con caida: A {int(np.isfinite(yA).sum())} de {len(yA)}, "
          f"B {int(np.isfinite(yB).sum())}")
    todas, verdictos = [], []
    for res, y in (("A", yA), ("B", yB)):
        d2 = dict(d)
        a, b, c = _variables_pad(con, d, 1)
        d2["v1"], d2["v2"], d2["v3"] = a, b, c
        rc = _modelo_completo(y, d2, res, _semilla(res, ANA_COMPLETO), dosis.B_MAIN)
        rs = _modelo_cercania(y, d2, rc["cc"], res, _semilla(res, ANA_CERCANIA))
        d0 = dict(d)
        a0, b0, c0 = _variables_pad(con, d, 0)
        d0["v1"], d0["v2"], d0["v3"] = a0, b0, c0
        rm = _modelo_completo(y, d0, res, _semilla(res, ANA_MISMO_MES), dosis.B_SENS)
        fc, cum_c, contra_c = _filas_modelo(res, "completo", VARIABLES_PAD, rc)
        fs, cum_s, contra_s = _filas_modelo(res, "cercania", VARIABLES_CERCA, rs)
        fm, _, _ = _filas_modelo(res, "mismo_mes", VARIABLES_PAD, rm)
        fm += _diagnostico_sola(res, y, d2, rc["cc"])
        contra = contra_c + [x for x in contra_s if x not in contra_c]
        codigo, texto = veredicto(cum_c, cum_s, contra, rc["n"], rc["pads"], rs["n"], rs["pads"],
                                  rc["semiancho"], rs["semiancho"], rc["cota"], rs["cota"])
        print(f"[dosis_pad] resultado {res}: caso completo n={rc['n']} pads={rc['pads']}, "
              f"cercania km<0.5 n={rs['n']} pads={rs['pads']}, mismo_mes n={rm['n']}")
        todas += fc + fs + fm
        verdictos.append((res, codigo, texto))
    _escribir(con, "mart_dosis_pad", COLS_PAD, todas)
    _escribir(con, "mart_dosis_pad_veredicto", COLS_VEREDICTO_PAD, verdictos)
    for r in todas:
        print(f"[dosis_pad] modelo {r[0]} {r[1]:<10} {r[2]:<14} coef={r[3]:+.4f} IC {r[4]:+.4f} a {r[5]:+.4f} "
              f"p={r[6]:.4f} p_holm={r[7]:.4f} n={r[8]} pads={r[9]} cumple={r[10]} contraria={r[11]}")
    for res, codigo, texto in verdictos:
        print(f"[dosis_pad] veredicto {res}: {codigo}: {texto}")
    con.close()


if __name__ == "__main__":
    main()

