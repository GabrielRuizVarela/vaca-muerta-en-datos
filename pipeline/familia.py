"""La familia de replicaciones: la lectura conjunta de las cuencas, con la regla fijada antes de calcular ninguna cifra de una cuenca nueva.

REGLA FIJADA (2026-11-19, antes de bajar la produccion de Wyoming; no se cambia despues de ver resultados).

Las cuencas de la familia, con su nombre, son las que replican la huella de interferencia de Vaca Muerta:
  * Colorado (cuenca DJ), la primera replicacion, ya publicada en `wiki/hallazgos/replicacion.md`;
  * Wyoming (WOGCC), la unica jurisdiccion que la auditoria de `wiki/hallazgos/fuentes_mundo.md` deja entrar ademas de Argentina
    (que es la cuenca original, no una replicacion), por la regla de elegibilidad y nada mas.
Una cuenca se agrega a la familia solo con una auditoria que la deje entrar por esa regla, y se agrega antes de ver su resultado.

Cada cuenca se lee con la misma regla de `replicacion_colorado` (pipeline/replicacion.py: brecha del mes 1 negativa con el limite
superior del IC por bloques de 5 km menor que 0, y brecha previa limpia menor en valor absoluto), con los mismos filtros y las mismas
semillas. La lectura de la familia es una frase, "se replica en k de n", con TODAS las cuencas listadas, cada una con su lectura:
  * "se replica", "no se replica" o "no se pudo medir" con el motivo escrito;
  * k cuenta las cuencas que se replican y n todas las de la familia, las que no se pudieron medir incluidas;
  * no hay estimacion conjunta, ni promedio, ni peso por cuenca: es la validez externa de la huella, no un efecto comun;
  * ninguna cuenca se quita de la lista despues de ver su resultado: si falta el resultado de una, la lectura no se arma.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from pipeline.cuencas import CUENCAS
from pipeline.ingest import ROOT
from pipeline.placebo import _g, _pts
from pipeline.replicacion import COLS_VEREDICTO
from pipeline.wyoming import MIN_CONTROLES_MEDIBLE, MIN_HIJOS_MEDIBLE

PAGINA = ROOT / "wiki" / "hallazgos" / "replicacion_cuencas.md"
# (id de la cuenca, nombre en una frase); el orden es el de la lista de la pagina.
FAMILIA: tuple[tuple[str, str], ...] = (("colorado", "Colorado"), ("wyoming", "Wyoming"))

LECTURAS = ("se replica", "no se replica", "no se pudo medir")


def lectura_cuenca(se_replica: bool | None, motivo: str = "") -> str:
    """`se_replica` es el resultado de la regla; None es una cuenca que no se pudo medir (el motivo es obligatorio)."""
    if se_replica is None:
        if not motivo.strip():
            raise ValueError("una cuenca que no se pudo medir lleva el motivo escrito")
        return f"no se pudo medir: {motivo.strip()}"
    return "se replica" if se_replica else "no se replica"


def lectura_familia(resultados: dict[str, tuple[bool | None, str]]) -> dict:
    """`resultados`: id de cuenca -> (se_replica o None, motivo). Devuelve k, n, la frase y la lista completa, en el orden de FAMILIA."""
    ids = [i for i, _ in FAMILIA]
    faltan = [i for i in ids if i not in resultados]
    sobran = [i for i in resultados if i not in ids]
    if faltan or sobran:
        raise ValueError(f"la lectura de la familia pide exactamente {ids}: faltan {faltan}, sobran {sobran}")
    filas = [(i, nombre, lectura_cuenca(*resultados[i])) for i, nombre in FAMILIA]
    k = sum(1 for i, _, _ in filas if resultados[i][0] is True)
    n = len(filas)
    frase = f"Se replica en {k} de {n} cuencas: " + "; ".join(f"{nombre} ({lec})" for _, nombre, lec in filas) + "."
    return {"k": k, "n": n, "frase": frase, "cuencas": filas}


def veredicto_cuenca(con, id_: str) -> dict:
    """La fila del veredicto (k = 1) de una cuenca como diccionario, leida de `mart_replicacion_<id>` de su warehouse."""
    cols = [c[0] for c in COLS_VEREDICTO]
    fila = con.execute(f"select * from {CUENCAS[id_].tabla_veredicto} where k = 1").fetchone()
    return dict(zip(cols, fila))


def resultados_desde(cons: dict) -> dict[str, tuple[bool | None, str]]:
    """Id de cuenca -> (se_replica, motivo) para todas las cuencas de la familia; si falta el warehouse de una, no hay lectura."""
    faltan = [i for i, _ in FAMILIA if i not in cons or cons[i] is None]
    if faltan:
        raise ValueError(f"falta el warehouse de: {', '.join(faltan)}; la lectura de la familia no se arma sin todas las cuencas")
    out: dict[str, tuple[bool | None, str]] = {}
    for i, _ in FAMILIA:
        v = veredicto_cuenca(cons[i], i)
        hijos = cons[i].execute("select valor from mart_replicacion_recuentos where clave = 'hijos'").fetchone()[0]
        if v["se_replica"] is None or v["valor"] is None or v["valor"] != v["valor"]:
            out[i] = (None, "el veredicto no tiene valor")
        elif hijos < MIN_HIJOS_MEDIBLE or v["n_controles"] < MIN_CONTROLES_MEDIBLE:
            out[i] = (None, f"menos de {MIN_HIJOS_MEDIBLE} hijos o de {MIN_CONTROLES_MEDIBLE} controles")
        else:
            out[i] = (bool(v["se_replica"]), "")
    return out


def pagina_familia(cons: dict) -> str:
    """Pagina wiki/hallazgos/replicacion_cuencas.md: la lectura de la familia y una tabla con el veredicto de cada cuenca."""
    lec = lectura_familia(resultados_desde(cons))
    v = {i: veredicto_cuenca(cons[i], i) for i, _ in FAMILIA}
    hijos = {i: cons[i].execute("select valor from mart_replicacion_recuentos where clave = 'hijos'").fetchone()[0] for i, _ in FAMILIA}
    L = ["# Replicación en otras cuencas: lectura de la familia", "",
         "Página generada por `pipeline/familia.py` a partir del veredicto de cada cuenca. Cada cuenca se lee con la misma regla, fijada "
         "antes de bajar o medir nada de Wyoming (`pipeline/familia.py` y `pipeline/wyoming/__init__.py`): la brecha del mes 1 es "
         "negativa con el límite superior del IC 95% por bloques de 5 km menor que cero, y la brecha previa con base "
         "limpia (mes -1) es menor, en valor absoluto, que la del mes 1. Mismo estimador, mismos filtros, mismas semillas.", "",
         "## Lectura", "", f"**{lec['frase']}**", "",
         "k cuenta las cuencas que se replican y n todas las de la familia, las que no se pudieran medir incluidas. No hay promedio, "
         "peso ni estimación conjunta: es la validez externa de la huella de Vaca Muerta medida cuenca por cuenca, no un efecto común.", "",
         "## Por cuenca", "",
         "| Cuenca | Hijos | Eventos cercanos | Controles | Brecha del mes 1 (puntos) | IC 95% por bloques de 5 km | "
         "Brecha previa, mes -1 (puntos) | Valor de la hipótesis | Lectura |",
         "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |"]
    for i, nombre, lectura in lec["cuencas"]:
        x = v[i]
        L.append(f"| {nombre} | {_g(hijos[i])} | {_g(x['n_cercanos'])} | {_g(x['n_controles'])} | {_pts(x['brecha'])} | "
                 f"{_pts(x['ic_bajo_bloque'])} a {_pts(x['ic_alto_bloque'])} | {_pts(x['brecha_previa_limpia'])} | "
                 f"{_g(x['valor'], 3)} | {lectura} |")
    L += ["", "Cada fila es la de la página de la cuenca: " + ", ".join(
        f"[{nombre}]({CUENCAS[i].pagina.name})" for i, nombre in FAMILIA) + ". El valor es el mayor entre el límite superior del IC y la "
        "diferencia de valores absolutos (previa menos mes 1); la cuenca se replica si es menor que cero.", ""]
    L += ["## Qué no es", "",
          "- No es una estimación conjunta ni una probabilidad: k de n no dice cuánto se espera que se replique en una cuenca nueva.",
          f"- Son {lec['n']} cuencas: una lectura de {lec['n']} no distingue entre una huella que depende de la cuenca y una que se "
          "mide con más o menos ruido en cada una.",
          "- Las cuencas no miden lo mismo: la fecha del hijo es el inicio de fractura de FracFocus en Colorado y la primera terminación "
          "del regulador en Wyoming, y difieren la convención de reporte y la población de pozos. No se probó cuánto de una diferencia "
          "entre cuencas sale de eso, y no se afirma que lo explique. Si la terminación cae después de la fractura, el mes 0 de Wyoming "
          "queda corrido hacia adelante respecto del de Colorado y la lectura no separa \"no hay huella\" de \"el mes 0 está corrido\".",
          "- Una cuenca que no se replica no refuta el resultado de Vaca Muerta ni una que se replica lo prueba: la lectura se "
          "publica entera y el resultado de Vaca Muerta queda con sus cifras.", ""]
    no = [(i, nombre, v[i]) for i, nombre in FAMILIA if not v[i]["se_replica"]]
    for i_, nombre, x in no:
        motivos = []
        if not x["ic_alto_bloque"] < 0:
            motivos.append("el IC por bloques de 5 km de la brecha del mes 1 incluye cero")
        if abs(x["brecha_previa_limpia"]) >= abs(x["brecha"]):
            motivos.append("la brecha previa es mayor, en valor absoluto, que la del mes 1: los padres cercanos ya venían por debajo de "
                           f"los controles antes del mes 0, el mes de la {CUENCAS[i_].fecha_hijo} del hijo, y no se probó por qué")
        L.append(f"En {nombre}, " + " y ".join(motivos) + ".")
        L.append("")
    return "\n".join(L)


def main(pagina: Path | None = PAGINA) -> int:
    cons = {}
    for i, _ in FAMILIA:
        if not CUENCAS[i].db.exists():
            print(f"falta {CUENCAS[i].db}: la lectura de la familia no se arma sin todas las cuencas", file=sys.stderr)
            return 2
        cons[i] = duckdb.connect(str(CUENCAS[i].db), read_only=True)
    try:
        texto = pagina_familia(cons)
    finally:
        for c in cons.values():
            c.close()
    if pagina is not None:
        pagina.write_text(texto, encoding="utf-8")
        print(f"pagina: {pagina}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
