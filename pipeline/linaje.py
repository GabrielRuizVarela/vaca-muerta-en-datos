"""Linaje de datos: de qué dataset crudo sale cada tabla del warehouse.

Se arma leyendo el SQL de pipeline/sql (`create or replace table|view X` y las cláusulas
`from|join Y` hasta el próximo `create`) y el código de los módulos de Python que escriben
marts. Los módulos se descubren del código: son los `pipeline/*.py` que llaman a
`_escribir(con, "mart_...", ...)`. No consulta el warehouse, así que la página es
determinista y no lleva marcas de tiempo.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"
PIPELINE_DIR = Path(__file__).parent
# Módulos que no entran en la página: este (cita la llamada en su docstring) y replicacion, que
# escribe en el warehouse de Colorado con nombres tomados de un diccionario.
EXCLUIDOS = ("linaje", "replicacion")

_CREATE = re.compile(r"create\s+or\s+replace\s+(?:table|view)\s+(\w+)", re.I)
_CSV = re.compile(r"read_csv\(\s*'\{(\w+)\}'", re.I)
_FROM = re.compile(r"\b(?:from|join)\s+(\w+)", re.I)
_PARAM = re.compile(r"\{(\w+)\}")
_ESCRIBIR = re.compile(r"_escribir\(\s*con\s*,\s*\"(mart_\w+)\"")
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
        csvs = set(_CSV.findall(cuerpo))
        for c in csvs:
            pares.add((destino, _nombre_crudo(c)))
        for prm in set(_PARAM.findall(cuerpo)) - csvs:  # un valor que pipeline.build lee del manifiesto y pasa al SQL
            pares.add((destino, "manifiesto:" + prm))
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


def descubrir_modulos(pipeline_dir: Path = PIPELINE_DIR) -> tuple[str, ...]:
    """Módulos `pipeline/*.py` que escriben marts con `_escribir(con, "mart_...", ...)`, menos EXCLUIDOS."""
    return tuple(p.stem for p in sorted(pipeline_dir.glob("*.py"))
                 if p.stem not in EXCLUIDOS and _ESCRIBIR.search(p.read_text(encoding="utf-8")))


def _importados(arbol: ast.AST) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """Nombres que un módulo trae de otros módulos de pipeline: `funciones` (nombre local ->
    (módulo, nombre en ese módulo)) y `modulos` (nombre local -> módulo)."""
    funciones: dict[str, tuple[str, str]] = {}
    modulos: dict[str, str] = {}
    for n in ast.walk(arbol):
        if isinstance(n, ast.ImportFrom) and n.module == "pipeline":
            for a in n.names:
                modulos[a.asname or a.name] = a.name
        elif isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("pipeline."):
            for a in n.names:
                funciones[a.asname or a.name] = (n.module[len("pipeline."):], a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("pipeline."):
                    modulos[a.asname or a.name] = a.name[len("pipeline."):]
    return funciones, modulos


def _referencias(nodo: ast.AST, funciones: dict[str, tuple[str, str]], modulos: dict[str, str],
                 propio: str) -> set[tuple[str, str]]:
    """(módulo, nombre) a los que se refiere `nodo`: `f` de un `from pipeline.X import f`, `X.f` de un módulo
    de pipeline y un nombre suelto, que se busca en el mismo módulo. Cubre funciones llamadas y constantes de
    texto (el SQL guardado en una constante del módulo)."""
    salida: set[tuple[str, str]] = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.Name):
            salida.add(funciones.get(n.id, (propio, n.id)))
        elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in modulos:
            salida.add((modulos[n.value.id], n.attr))
    return salida


def _lecturas(nodo: ast.AST) -> set[str]:
    """Tablas del warehouse que leen los literales de texto dentro de `nodo`."""
    salida: set[str] = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            salida.update(_LEE.findall(n.value))
    return salida


def _es_texto(valor: ast.AST) -> bool:
    """Si una constante es un texto (un SQL): literal, f-string, suma o `%` de textos, `.format(...)` de un texto
    o un alias de otro nombre. Una lista o un registro de objetos no lo es: un módulo que solo usa su largo
    no lee las tablas de las consultas que lleva dentro."""
    if isinstance(valor, ast.Constant):
        return isinstance(valor.value, str)
    if isinstance(valor, ast.JoinedStr | ast.Name):
        return True
    if isinstance(valor, ast.BinOp):
        return _es_texto(valor.left) or _es_texto(valor.right)
    if isinstance(valor, ast.Call) and isinstance(valor.func, ast.Attribute):
        return _es_texto(valor.func.value)
    return False


def _definiciones(arbol: ast.Module, nombre: str) -> list[ast.AST]:
    """Funciones y constantes de texto de nivel de módulo llamadas `nombre`."""
    salida: list[ast.AST] = []
    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == nombre:
            salida.append(n)
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == nombre for t in n.targets):
            if _es_texto(n.value):
                salida.append(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == nombre and n.value:
            if _es_texto(n.value):
                salida.append(n.value)
    return salida


def _origenes_modulo(mod: str, pipeline_dir: Path) -> set[str]:
    """Tablas que lee el texto de `mod` más las que leen, por transitividad, las funciones y las constantes de
    SQL (constantes de texto) de otros módulos de pipeline a las que `mod` se refiere. No toma el módulo importado entero. Es una
    lectura del texto: un nombre local que coincide con un nombre del módulo importado suma un origen de más,
    nunca de menos."""
    texto = (pipeline_dir / f"{mod}.py").read_text(encoding="utf-8")
    origenes = set(_LEE.findall(texto))
    arboles: dict[str, ast.Module | None] = {}

    def arbol_de(m: str) -> ast.Module | None:
        if m not in arboles:
            ruta = pipeline_dir / f"{m}.py"
            arboles[m] = ast.parse(ruta.read_text(encoding="utf-8")) if ruta.exists() else None
        return arboles[m]

    raiz = arbol_de(mod)
    funciones, modulos = _importados(raiz)
    pendientes = [r for r in _referencias(raiz, funciones, modulos, mod) if r[0] != mod]
    vistos: set[tuple[str, str]] = set()
    while pendientes:
        m, nombre = pendientes.pop()
        if (m, nombre) in vistos:
            continue
        vistos.add((m, nombre))
        a = arbol_de(m)
        if a is None:
            continue
        f2, m2 = _importados(a)
        for d in _definiciones(a, nombre):
            origenes |= _lecturas(d)
            pendientes += list(_referencias(d, f2, m2, m))
    return origenes


def linaje_modulos(pipeline_dir: Path = PIPELINE_DIR, modulos: tuple[str, ...] | None = None
                   ) -> list[tuple[str, str, str]]:
    """Ternas (destino, origen, modulo) de los marts que escriben los módulos de Python.

    Los marts son los de `_escribir(con, "mart_x", ...)`. Los orígenes son las tablas del warehouse
    que lee el módulo (`from|join` en su texto y en las funciones de pipeline que importa y llama),
    sin contar sus propios marts. El grano es el módulo: cada mart de un módulo lista todos los
    orígenes del módulo. Sin `modulos`, se descubren del código."""
    if modulos is None:
        modulos = descubrir_modulos(pipeline_dir)
    ternas: set[tuple[str, str, str]] = set()
    for mod in modulos:
        texto = (pipeline_dir / f"{mod}.py").read_text(encoding="utf-8")
        propios = set(_ESCRIBIR.findall(texto))
        origenes = _origenes_modulo(mod, pipeline_dir) - propios
        for d in propios:
            for o in origenes:
                ternas.add((d, o, f"pipeline.{mod}"))
    return sorted(ternas)


def tipo(nombre: str) -> str:
    if nombre.startswith("raw:"):
        return "crudo"
    if nombre.startswith("seed:"):
        return "semilla"
    if nombre.startswith("manifiesto:"):
        return "manifiesto"
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
         "los módulos de Python que escriben marts; no consulta el warehouse ni lleva marcas de tiempo.", "",
         "Capas: crudo (CSV inmutable en `data/raw`), staging (`stg_`), intermedia (`int_`), hecho (`fct_`), "
         "dimensión (`dim_`) y mart (`mart_`). Los marts que escribe un módulo de Python se alimentan de las "
         "tablas que ese módulo lee en su código y en las funciones y el SQL de otros módulos de pipeline que importa y "
         "usa. El grano es el módulo: todos los marts de un módulo muestran los mismos orígenes, sin separar "
         "cuál de ellos usa cada mart. Un origen `manifiesto:` es un valor que `pipeline.build` "
         "lee de `data/manifest.json` y le pasa al SQL (la fecha de extracción del archivo de fracturas).", "",
         "Queda fuera la réplica en el warehouse de Colorado (`pipeline.replicacion`), que escribe con nombres "
         "tomados de un diccionario y no con una llamada por mart. Los marts `mart_dias_perdidos_colorado*`, `mart_golpes_mismo_mes_colorado*`, `mart_golpes_mismo_padre_colorado*` y `mart_causal_profundo_d7` sí están: "
         "se guardan en este warehouse, pero se calculan desde el de Colorado, que tiene tablas con los mismos nombres.", "",
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
