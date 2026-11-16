"""Dosis y respuesta mes a mes: la parte de caudal por dia, k = 1 a 4 (respuesta tardia).

Se corre despues de pipeline.dosis:  uv run python -m pipeline.dosis_meses

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ningun coeficiente de k = 2, 3 o 4; no se cambia despues de ver
resultados). Fuente: docs/proceso/siguientes-investigaciones.md, punto 2. Extiende pipeline.dosis (regla en su encabezado), que solo
mira el mes 1: un golpe de fractura que se note con retraso (meses 2 a 4) no aparecia.

Modelo: exactamente el modelo conjunto de pipeline.dosis (las cuatro variables estandarizadas, los mismos controles, efectos fijos de
area por ano, caso completo de las cuatro variables, bootstrap por pads hijo B = 2.000, p de dos colas de la regla), para el
resultado B (menos el logaritmo del indice de caudal por dia efectivo, variante sin cerrados de pipeline.descomposicion._logs) en
cada k = 1, 2, 3 y 4. Para cada k el caso completo exige ademas que el evento tenga caudal por dia positivo en ese mes; la muestra
puede achicarse con k y se informa. Se reutilizan las funciones de pipeline.dosis (variables, controles, ajuste, Holm); k = 1
debe reproducir el resultado B de pipeline.dosis (coeficientes iguales dentro de 0,001) y el modulo imprime si lo hace.

Holm: una sola familia de 16 pruebas (4 variables por 4 meses), alfa = 0,05; una celda "cumple" si su coeficiente es positivo y su p
ajustado es menor que 0,05; "signo contrario" si es negativo y su p ajustado menor que 0,05.

Veredicto (se publican todos los coeficientes, favorables o no):
  * "tampoco con respuesta tardia": ninguna de las 16 celdas cumple. Se agrega a la pagina de dosis (y a la linea del README) que
    tampoco aparece una respuesta en los meses 2 a 4.
  * "respuesta tardia exploratoria": alguna celda cumple en k = 2 a 4. Se informa cual, se rotula exploratoria (16 pruebas, sin
    preregistro anterior del mes) y NO cambia el veredicto de pipeline.dosis, que es el del mes 1.
  * Celdas de signo contrario se informan aparte y nunca cuentan como cumplidas.
Cualquier diagnostico agregado despues de ver los resultados se rotula "agregado despues de ver los resultados" y no cambia el
veredicto.

Que NO prueba:
  * Un coeficiente nulo no dice que no haya golpes de fractura (espaciamiento real y geometria no estan en el dato publico).
  * A mayor k la muestra y la potencia bajan (menos eventos con caudal por dia positivo y mas dependencia con el ciclo del pozo).
  * Los IC son por pads hijo; los eventos de un mismo padre en meses distintos no son independientes entre si.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import dosis
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

MESES = (1, 2, 3, 4)

COLS_MESES = [("k", "integer"), ("variable", "varchar"), ("coef_sd", "double"), ("ic_bajo", "double"),
              ("ic_alto", "double"), ("p", "double"), ("p_holm", "double"), ("n", "integer"), ("pads", "integer"),
              ("cumple", "boolean"), ("signo_contrario", "boolean")]
COLS_VEREDICTO_MESES = [("codigo", "varchar"), ("texto", "varchar"), ("detalle", "varchar")]


def _semilla(k: int) -> int:
    # Semilla por mes: SEMILLA_DOSIS + 100 * k + 10; el 10 replica ANA_CONJUNTO del modelo conjunto de dosis.
    return dosis.SEMILLA_DOSIS + 100 * k + 10


def holm_16(ps) -> np.ndarray:
    """p ajustados por Holm sobre la familia de 16 celdas, en matriz de meses por variables.

    `ps` trae los p sin ajustar en orden k = 1..4 y, dentro de cada mes, en el orden de VARIABLES.
    """
    return dosis._holm(np.asarray(ps, dtype=float).reshape(16)).reshape(4, 4)


def veredicto(filas) -> tuple[str, str]:
    """Veredicto puro sobre filas (k, nombre de variable, coeficiente, p Holm)."""
    filas = list(filas)
    cumplen = [(k, nom) for k, nom, c, ph in filas if c > 0 and ph < 0.05]
    contrarias = [(k, nom) for k, nom, c, ph in filas if c < 0 and ph < 0.05]
    # AMBIGUO: la lista de signo contrario se agrega al texto de cualquier veredicto cuando hay celdas.
    suf = ""
    if contrarias:
        suf = "; signo contrario en " + " y ".join(f"mes {k}, {nom}" for k, nom in contrarias)
    tardias = [(k, nom) for k, nom in cumplen if k in (2, 3, 4)]
    if not cumplen:
        return ("tampoco con respuesta tardia",
                "tampoco aparece una respuesta en los meses 2 a 4: ninguna de las 16 celdas cumple tras Holm" + suf)
    if tardias:
        lista = " y ".join(f"mes {k}, {nom}" for k, nom in tardias)
        return ("respuesta tardia exploratoria",
                f"cumple {lista}: respuesta exploratoria sobre 16 pruebas sin preregistro del mes y no cambia "
                f"el veredicto del mes 1 de pipeline.dosis{suf}")
    lista = " y ".join(f"mes {k}, {nom}" for k, nom in cumplen)
    return ("solo el mes 1",
            f"solo cumple {lista}; vale el veredicto del mes 1 de pipeline.dosis y no aparece respuesta "
            f"en los meses 2 a 4{suf}")


def pagina_dosis_meses(con) -> str:
    """Pagina de wiki a partir de los marts de dosis_meses.py. Texto en espanol, sin rayas largas."""
    mod = {(r[0], r[1]): r for r in con.execute("select k, variable, coef_sd, ic_bajo, ic_alto, p_holm, n, pads, "
                                               "cumple from mart_dosis_meses").fetchall()}
    codigo, texto, detalle = con.execute("select codigo, texto, detalle from mart_dosis_meses_veredicto").fetchall()[0]
    L = ["# Dosis y respuesta mes a mes: caudal por día, k = 1 a 4", "",
         "Página generada por `pipeline/dosis_meses.py`. Pregunta si la caída del caudal por día del padre crece con el ",
         "trabajo del hijo y la depleción en cada mes k = 1 a 4, porque un golpe que se note con retraso no aparece ",
         "en el mes 1. Mismo modelo conjunto de pipeline.dosis (resultado B) en cada mes, con Holm sobre 16 celdas.", "",
         "## Veredicto", "",
         f"**{codigo}**: {texto}.", "",
         f"Reproducción de pipeline.dosis en k = 1: {detalle}.", ""]
    for k in MESES:
        r0 = mod[(k, dosis.VARIABLES[0])]
        L += [f"### Mes {k} (n = {_g(r0[6])}, pads = {_g(r0[7])})", "",
              "| Variable | Coef por desvío | IC 95% | p Holm | Cumple |", "| --- | ---: | --- | ---: | --- |"]
        for var in dosis.VARIABLES:
            _k, _va, c, lo, hi, ph, _n, _pa, cu = mod[(k, var)]
            L.append(f"| {dosis.NOMBRES[var]} | {_g(c, 3)} | {_g(lo, 3)} a {_g(hi, 3)} | {_g(ph, 3)} | "
                     f"{'sí' if cu else 'no'} |")
        L.append("")
    L += ["## Qué no prueba", "",
          "- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometría ",
          "no están en el dato público.",
          "- A mayor k la muestra y la potencia bajan: menos eventos con caudal por día positivo y más dependencia ",
          "con el ciclo del pozo.",
          "- Los intervalos son por pads hijo; los eventos de un mismo padre en meses distintos no son independientes ",
          "entre sí.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    d = dosis._dataset_a(con)
    coefs, ics, ps, ns, pads, ny = {}, {}, {}, {}, {}, {}
    for k in MESES:
        y = np.asarray(dosis._caida_b(con, d, k=k), dtype=float)
        ny[k] = int(np.isfinite(y).sum())
        base = np.flatnonzero(np.isfinite(y))
        ib = base[dosis._mascara_controles(d, base)]
        cc = ib[np.all([np.isfinite(d[f"v{j + 1}"][ib]) for j in range(4)], axis=0)]
        X = np.column_stack([dosis._std(d[f"v{j + 1}"][cc]) for j in range(4)])
        C, grupo = dosis._controles(d, cc)
        c, ic, p = dosis._ajuste(y[cc], X, C, grupo, d["cluster"][cc], _semilla(k), dosis.B_MAIN)
        coefs[k], ics[k], ps[k] = c, ic, p
        ns[k], pads[k] = len(cc), len(set(d["cluster"][cc]))
    print("[dosis_meses] eventos con caudal por día en el mes: "
          + ", ".join(f"k={k} {ny[k]} (caso completo {ns[k]})" for k in MESES))
    ph = holm_16([ps[k] for k in MESES])
    filas = []
    for i, k in enumerate(MESES):
        for j, var in enumerate(dosis.VARIABLES):
            cu = bool(coefs[k][j] > 0 and ph[i][j] < 0.05)
            ct = bool(coefs[k][j] < 0 and ph[i][j] < 0.05)
            filas.append((k, var, float(coefs[k][j]), float(ics[k][j][0]), float(ics[k][j][1]),
                          float(ps[k][j]), float(ph[i][j]), ns[k], pads[k], cu, ct))
    vfilas = [(k, dosis.NOMBRES[var], coefs[k][j], ph[i][j])
              for i, k in enumerate(MESES) for j, var in enumerate(dosis.VARIABLES)]
    codigo, texto = veredicto(vfilas)
    ref = {r[0]: r[1] for r in con.execute("select variable, coef_sd from mart_dosis_modelo "
                                          "where resultado = 'B'").fetchall()}
    dif = max(abs(float(coefs[1][j]) - float(ref[var])) for j, var in enumerate(dosis.VARIABLES))
    # AMBIGUO: "dentro de 0,001" incluye la igualdad.
    detalle = f"{'reproduce' if dif <= 0.001 else 'no reproduce'} pipeline.dosis (diferencia máxima {_g(dif, 4)})"
    _escribir(con, "mart_dosis_meses", COLS_MESES, filas)
    _escribir(con, "mart_dosis_meses_veredicto", COLS_VEREDICTO_MESES, [(codigo, texto, detalle)])
    for r in filas:
        print(f"[dosis_meses] modelo k={r[0]} {r[1]:<12} coef={r[2]:+.4f} IC {r[3]:+.4f} a {r[4]:+.4f} p={r[5]:.4f} "
              f"p_holm={r[6]:.4f} n={r[7]} pads={r[8]} cumple={r[9]} contraria={r[10]}")
    print(f"[dosis_meses] veredicto: {codigo}: {texto}")
    print(f"[dosis_meses] {detalle}")
    con.close()


if __name__ == "__main__":
    main()
