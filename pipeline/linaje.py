"""Linaje de datos: de qué dataset crudo sale cada tabla del warehouse.

Se arma leyendo el SQL de pipeline/sql (`create or replace table|view X` y las cláusulas
`from|join Y` hasta el próximo `create`) y el código de los módulos que escriben marts
fuera del SQL (pipeline.costo y pipeline.robustez). No consulta el warehouse, así que
la página es determinista y no lleva marcas de tiempo.
"""
from __future__ import annotations

import re
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"
PIPELINE_DIR = Path(__file__).parent
MODULOS = ("costo", "robustez")  # módulos que escriben marts con _escribir(con, "mart_x", ...)

_CREATE = re.compile(r"create\s+or\s+replace\s+(?:table|view)\s+(\w+)", re.I)
_CSV = re.compile(r"read_csv\(\s*'\{(\w+)\}'", re.I)
_FROM = re.compile(r"\b(?:from|join)\s+(\w+)", re.I)
_ESCRIBIR = re.compile(r"_escribir\(\s*con\s*,\s*\"(\w+)\"")
_LEE = re.compile(r"\b(?:from|join)\s+((?:stg|int|fct|dim|mart)_\w+)", re.I)


def _sin_comentarios(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def _nombre_crudo(clave: str) -> str:
    """`produccion_no_convencional` -> `raw:produccion_no_convencional`; `seed_operadores` -> `seed:operadores`."""
    return "seed:" + clave[len("seed_"):] if clave.startswith("seed_") else "raw:" + clave


def linaje_archivo(sql: str, creadas: set[str] | None = None) -> list[tuple[str, str]]:
    """Pares (destino, origen) de un texto SQL. `creadas` filtra los `from` a tablas conocidas
    (descarta CTE y subconsultas); por defecto son las tablas creadas en este mismo texto."""
    sql = _sin_comentarios(sql)
    partes = list(_CREATE.finditer(sql))
    if creadas is None:
        creadas = {m.group(1) for m in partes}
    pares: set[tuple[str, str]] = set()
    for i, m in enumerate(partes):
        destino = m.group(1)
        fin = partes[i + 1].start() if i + 1 < len(partes) else len(sql)
        cuerpo = sql[m.end():fin]
        for c in _CSV.findall(cuerpo):
            pares.add((destino, _nombre_crudo(c)))
        for o in _FROM.findall(cuerpo):
            if o in creadas and o != destino:
                pares.add((destino, o))
    return sorted(pares)


def linaje(sql_dir: Path = SQL_DIR) -> list[tuple[str, str]]:
    """Pares (destino, origen) de todos los .sql de `sql_dir`, ordenados."""
    textos = {p.name: _sin_comentarios(p.read_text(encoding="utf-8")) for p in sorted(sql_dir.glob("*.sql"))}
    creadas = {m.group(1) for t in textos.values() for m in _CREATE.finditer(t)}
    pares: set[tuple[str, str]] = set()
    for t in textos.values():
        pares.update(linaje_archivo(t, creadas))
    return sorted(pares)


def escritos_por(sql_dir: Path = SQL_DIR) -> dict[str, str]:
    """tabla -> fichero SQL que la crea."""
    salida: dict[str, str] = {}
    for p in sorted(sql_dir.glob("*.sql")):
        for m in _CREATE.finditer(_sin_comentarios(p.read_text(encoding="utf-8"))):
            salida[m.group(1)] = f"pipeline/sql/{p.name}"
    return salida


def linaje_modulos(pipeline_dir: Path = PIPELINE_DIR, modulos: tuple[str, ...] = MODULOS
                   ) -> list[tuple[str, str, str]]:
    """Ternas (destino, origen, modulo) de los marts que escriben los módulos de Python.

    Los marts son los de `_escribir(con, "mart_x", ...)`; los orígenes son las tablas del
    warehouse que el módulo lee (`from|join`), sin contar sus propios marts."""
    ternas: set[tuple[str, str, str]] = set()
    for mod in modulos:
        texto = (pipeline_dir / f"{mod}.py").read_text(encoding="utf-8")
        propios = set(_ESCRIBIR.findall(texto))
        origenes = {o for o in _LEE.findall(texto)} - propios
        for d in propios:
            for o in origenes:
                ternas.add((d, o, f"pipeline.{mod}"))
    return sorted(ternas)


def tipo(nombre: str) -> str:
    if nombre.startswith("raw:"):
        return "crudo"
    if nombre.startswith("seed:"):
        return "semilla"
    for prefijo, t in (("stg_", "staging"), ("int_", "intermedia"), ("fct_", "hecho"),
                       ("dim_", "dimensión"), ("mart_", "mart")):
        if nombre.startswith(prefijo):
            return t
    return "auxiliar"


def filas_linaje(sql_dir: Path = SQL_DIR, pipeline_dir: Path = PIPELINE_DIR
                 ) -> list[tuple[str, str, str, str]]:
    """Filas (destino, tipo, origen, escrito por) para la tabla de la página."""
    por = escritos_por(sql_dir)
    filas = [(d, tipo(d), o, por[d]) for d, o in linaje(sql_dir)]
    filas += [(d, tipo(d), o, m) for d, o, m in linaje_modulos(pipeline_dir)]
    return sorted(filas)


def arbol(filas: list[tuple[str, str, str, str]]) -> list[str]:
    """Árbol de texto sangrado desde cada crudo o semilla hasta los marts.
    Un nodo ya expandido se marca `(ver arriba)` en lugar de repetir su subárbol."""
    hijos: dict[str, list[str]] = {}
    destinos = set()
    for d, _, o, _ in filas:
        hijos.setdefault(o, []).append(d)
        destinos.add(d)
    raices = sorted(o for o in hijos if o not in destinos)
    vistos: set[str] = set()
    salida: list[str] = []

    def bajar(nodo: str, nivel: int) -> None:
        marca = "  " * nivel
        if nodo in vistos:
            salida.append(f"{marca}{nodo} (ver arriba)")
            return
        vistos.add(nodo)
        salida.append(f"{marca}{nodo}")
        for h in sorted(set(hijos.get(nodo, []))):
            bajar(h, nivel + 1)

    for r in raices:
        bajar(r, 0)
    return salida


def pagina_linaje(sql_dir: Path = SQL_DIR, pipeline_dir: Path = PIPELINE_DIR) -> str:
    filas = filas_linaje(sql_dir, pipeline_dir)
    destinos = sorted({f[0] for f in filas})
    L = ["# Linaje de datos", "",
         "Qué dataset crudo alimenta cada tabla del warehouse. Se genera leyendo `pipeline/sql` y el código de "
         "`pipeline.costo` y `pipeline.robustez`; no consulta el warehouse ni lleva marcas de tiempo.", "",
         "Capas: crudo (CSV inmutable en `data/raw`), staging (`stg_`), intermedia (`int_`), hecho (`fct_`), "
         "dimensión (`dim_`) y mart (`mart_`). Los marts de costo y de robustez los escriben módulos de Python "
         "y se alimentan de las tablas que ese módulo lee.", "",
         f"Hay {len(destinos)} tablas con {len(filas)} relaciones de origen.", "",
         "## Árbol", "", "```"]
    L += arbol(filas)
    L += ["```", "", "## Relaciones", "",
          "| Destino | Tipo | Origen | Escrito por |", "| --- | --- | --- | --- |"]
    for d, t, o, p in filas:
        L.append(f"| {d} | {t} | {o} | {p} |")
    L.append("")
    texto = "\n".join(L)
    for raya in ("\u2014", "\u2013"):
        if raya in texto:
            raise ValueError(f"la página de linaje no puede contener {raya!r}")
    return texto
