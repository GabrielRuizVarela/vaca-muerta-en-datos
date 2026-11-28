"""Arma una entrada nueva de docs/reglas-fijadas.md a partir de un commit, sin copiarla a mano.

Uso (desde la raíz del repositorio de trabajo):

    uv run python scripts/reglas_nueva_entrada.py SHA [SHA ...] [--archivo docs/reglas-fijadas.md] [--tip REF]
        [--completa] [--todos-los-archivos] [--escribir]
    uv run python scripts/reglas_nueva_entrada.py --recontar [--archivo docs/reglas-fijadas.md] [--escribir]

Sin --escribir imprime la entrada. Con --escribir la inserta en el archivo por fecha y reescribe los números del
encabezado. --recontar solo cuenta: imprime «(N commits; M se citan en esta copia fuera de este archivo y K solo en
documentos de trabajo que no se publican)» y, con --escribir, lo deja en el encabezado.

El método es el que el encabezado del archivo describe; este programa es su única implementación:

* la entrada lleva la fecha en UTC, el asunto, los archivos que tocó el commit (los primeros 14 y «y N más») y el primer
  commit posterior, sin merges, que desciende del citado y cambia alguno de esos archivos
  (``git log --ancestry-path --no-merges --date-order --reverse SHA..TIP -- archivos``, con TIP = --tip, por defecto HEAD);
* si el asunto tiene «regla», «fijada», «antes de calcular» o «aclaración», copia el texto que el commit agregó, por
  archivo y entre ``~~~``: hasta 60 líneas por archivo y 3 archivos, sin datos, wiki, sitio ni PDF, ni los planes de trabajo
  que no se publican;
* --completa quita el tope de 60 líneas; --todos-los-archivos copia hasta 5 archivos de ``pipeline/`` (sin tests);
* un merge sin cambios propios no tiene la línea del primer commit posterior.

El número M del encabezado se cuenta solo sobre los archivos que se publican: los del repositorio menos los que quita
scripts/publicar_sitio.sh, menos scripts/no_publicar.txt si existe, menos el archivo de reglas mismo.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = "docs/reglas-fijadas.md"
PALABRAS_REGLA = ("regla", "fijada", "antes de calcular", "aclaración")
TOPE_LINEAS = 60
TOPE_ARCHIVOS = 3
TOPE_ARCHIVOS_TODOS = 5
TOPE_LISTA = 14
# Lo que nunca se copia: datos y lo generado (wiki, sitio, PDF) y los textos binarios.
PREFIJOS_GENERADOS = ("data/", "wiki/", "site/", "tests/fixtures/")
SUFIJOS_GENERADOS = (".pdf",)
# Aunque estos no se publican, también se descartan sin leer scripts/publicar_sitio.sh (para repos sin ese script).
PLANES_NO_PUBLICADOS = (
    "docs/plan-siguiente-nivel.md",
    "docs/plan-nueva-entrada.md",
    "docs/deslop-review.md",
    "docs/revision-independiente.md",
)
# Archivos internos que la copia pública nunca lleva (regla 6 de AGENTS.md), además de lo que quita publicar_sitio.sh.
INTERNOS = ("AGENTS.md", "REVIEW.md", "docs/orquestacion")
ENTRADA = re.compile(r"(?m)^(?=## `[0-9a-f]{7}` · )")
SECCION_USO = "## Cómo agregar una entrada"
ENCABEZADO_CUENTA = re.compile(
    r"\((\d+) commits; (\d+) se citan en esta copia fuera de este archivo y (\d+) solo en documentos de trabajo "
    r"que no se publican\)"
)
CABECERA = re.compile(r"## `([0-9a-f]{7})` · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC")
ARBOL_VACIO = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def git(*args: str, raiz: Path = RAIZ, check: bool = True) -> str:
    r = subprocess.run(
        ["git", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8"
    )
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def fecha_utc(iso: str) -> str:
    return (
        datetime.fromisoformat(iso)
        .astimezone(timezone.utc)
        .strftime("%Y-%m-%d %H:%M UTC")
    )


def base_de(sha: str) -> str:
    """El primer padre (o el árbol vacío): un merge se mide contra la rama en que entró."""
    padres = git("rev-list", "--parents", "-n", "1", sha).split()[1:]
    return padres[0] if padres else ARBOL_VACIO


def archivos_del_commit(sha: str) -> list[str]:
    salida = git("diff", "--name-only", "--no-renames", "-z", base_de(sha), sha)
    return sorted(a for a in salida.split("\0") if a)


def es_generado(ruta: str) -> bool:
    return ruta.startswith(PREFIJOS_GENERADOS) or ruta.endswith(SUFIJOS_GENERADOS)


def archivos_publicables(archivos: list[str], raiz: Path = RAIZ) -> list[str]:
    """Los archivos del commit sin los planes de trabajo que no se publican (ni en la lista ni en el recorte)."""
    fuera = no_publicados_de_script(raiz) | set(PLANES_NO_PUBLICADOS) | set(INTERNOS)
    return [a for a in archivos if not es_no_publicado(a, fuera)]


def no_publicados_de_script(raiz: Path = RAIZ) -> set[str]:
    """Los archivos que scripts/publicar_sitio.sh quita del árbol de docs (las rutas de sus líneas ``rm``)."""
    ruta = raiz / "scripts" / "publicar_sitio.sh"
    rutas: set[str] = set()
    if not ruta.exists():
        return rutas
    texto = ruta.read_text(encoding="utf-8").replace("\\\n", " ")
    for bloque in re.findall(r"(?m)^rm -[rf]+ [^\n]*", texto):
        for m in re.findall(r'"\$OUT_DIR/([^"]+)"', bloque):
            rutas.add(m)
    return rutas


def no_publicados_de_lista(raiz: Path = RAIZ) -> set[str]:
    ruta = raiz / "scripts" / "no_publicar.txt"
    if not ruta.exists():
        return set()
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return {
        ln.strip() for ln in lineas if ln.strip() and not ln.lstrip().startswith("#")
    }


def es_no_publicado(ruta: str, fuera: set[str]) -> bool:
    return any(ruta == f or ruta.startswith(f.rstrip("/") + "/") for f in fuera)


def fija_regla(asunto: str) -> bool:
    bajo = asunto.lower()
    return any(p in bajo for p in PALABRAS_REGLA)


def lista_archivos(archivos: list[str]) -> str:
    if not archivos:
        return "(merge, sin cambios propios)"
    visibles = ", ".join(f"`{a}`" for a in archivos[:TOPE_LISTA])
    resto = len(archivos) - TOPE_LISTA
    return visibles + (f" y {resto} más" if resto > 0 else "")


def lineas_agregadas(sha: str, ruta: str) -> list[str]:
    diff = git("diff", "-U0", "--no-renames", base_de(sha), sha, "--", ruta)
    salida: list[str] = []
    en_cuerpo = False  # la cabecera del diff (``+++ b/ruta``) va antes del primer ``@@``; después todo ``+`` es texto
    for ln in diff.split("\n"):
        if ln.startswith("@@"):
            en_cuerpo = True
        elif en_cuerpo and ln.startswith("+"):
            salida.append(ln[1:])
    return salida


def textos_agregados(
    sha: str, archivos: list[str], *, completa: bool, todos: bool, raiz: Path = RAIZ
) -> list[tuple[str, list[str]]]:
    fuera = no_publicados_de_script(raiz) | set(PLANES_NO_PUBLICADOS) | set(INTERNOS)
    elegibles = [
        a for a in archivos if not es_generado(a) and not es_no_publicado(a, fuera)
    ]
    if todos:
        elegibles = [a for a in elegibles if a.startswith("pipeline/")][
            :TOPE_ARCHIVOS_TODOS
        ]
    else:
        elegibles = elegibles[:TOPE_ARCHIVOS]
    return [(a, lineas_agregadas(sha, a)) for a in elegibles]


def primer_posterior(sha: str, archivos: list[str], tip: str) -> str | None:
    if not archivos:
        return None
    salida = git(
        "log",
        "--ancestry-path",
        "--no-merges",
        "--date-order",
        "--reverse",
        "--format=%h%x09%cI%x09%s",
        f"{sha}..{tip}",
        "--",
        *archivos,
    )
    for ln in salida.splitlines():
        corto, fecha, asunto = ln.split("\t", 2)
        return f"`{corto[:7]}` · {fecha_utc(fecha)} · {asunto}"
    return ""


def armar_entrada(
    sha: str, *, tip: str = "HEAD", completa: bool = False, todos: bool = False
) -> tuple[str, str]:
    """Devuelve (fecha ``YYYY-MM-DD HH:MM``, texto de la entrada, terminado en un salto de línea)."""
    git("cat-file", "-e", f"{sha}^{{commit}}")
    corto, iso, asunto = (
        git("log", "-1", "--format=%h%x09%cI%x09%s", sha).rstrip("\n").split("\t", 2)
    )
    corto = corto[:7]
    archivos = archivos_publicables(archivos_del_commit(sha))
    fecha = fecha_utc(iso)
    out = [
        f"## `{corto}` · {fecha}",
        "",
        f"**Asunto:** {asunto}",
        "",
        f"**Archivos:** {lista_archivos(archivos)}",
        "",
    ]
    posterior = primer_posterior(sha, archivos, tip)
    if posterior is not None:
        out += [
            "**Primer commit posterior que toca los mismos archivos:** "
            + (posterior or f"ninguno hasta `{tip}`"),
            "",
        ]
    if not fija_regla(asunto):
        out += [
            "(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)",
            "",
        ]
    else:
        for ruta, lineas in textos_agregados(
            sha, archivos, completa=completa, todos=todos
        ):
            n = len(lineas)
            corte = n if completa else min(n, TOPE_LINEAS)
            marca = f" (primeras {corte} de {n} líneas)" if corte < n else ""
            out += [
                f"Texto agregado en `{ruta}`{marca}:",
                "",
                "~~~",
                *lineas[:corte],
                "~~~",
                "",
            ]
    return fecha[:16], "\n".join(out)


def partir(texto: str) -> tuple[str, list[str], str]:
    """El archivo en (preámbulo, entradas, cola).

    Cada entrada va de su ``## `sha` `` hasta la siguiente (el texto copiado puede traer sus propios ``## ``, por eso
    solo cuenta una cabecera con sha). La cola es la sección «Cómo agregar una entrada», que no se toca.
    """
    corte = texto.find("\n" + SECCION_USO + "\n")
    cola = texto[corte + 1 :] if corte >= 0 else ""
    cuerpo = texto[: corte + 1] if corte >= 0 else texto
    trozos = ENTRADA.split(cuerpo)
    return trozos[0], trozos[1:], cola


def sha_de(entrada: str) -> str:
    return CABECERA.match(entrada).group(1)  # type: ignore[union-attr]


def fecha_de(entrada: str) -> str:
    return CABECERA.match(entrada).group(2)  # type: ignore[union-attr]


def ruta_relativa(archivo: str, raiz: Path = RAIZ) -> str:
    """``archivo`` como lo lista git (relativo a la raíz, con «/»), también si llega absoluto o con «./»."""
    try:
        return (raiz / archivo).resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return archivo


def citados_fuera(shas: list[str], archivo: str, raiz: Path = RAIZ) -> set[str]:
    """Los commits de ``shas`` que se citan en algún archivo publicado distinto de ``archivo``."""
    archivo = ruta_relativa(archivo, raiz)
    fuera = (
        no_publicados_de_script(raiz)
        | no_publicados_de_lista(raiz)
        | set(INTERNOS)
        | {archivo}
    )
    rutas = [
        r
        for r in git("ls-files", "-z", raiz=raiz).split("\0")
        if r and not es_no_publicado(r, fuera)
    ]
    citados: set[str] = set()
    pendientes = set(shas)
    for r in rutas:
        p = raiz / r
        if not pendientes or not p.is_file():
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for s in [s for s in pendientes if s in t]:
            if re.search(
                rf"(?<![0-9a-f]){s}", t
            ):  # también cuenta la cita con más de 7 caracteres
                citados.add(s)
                pendientes.discard(s)
    return citados


def cuenta(texto: str, archivo: str, raiz: Path = RAIZ) -> tuple[int, int, int]:
    _, entradas, _ = partir(texto)
    shas = [sha_de(e) for e in entradas]
    m = len(citados_fuera(shas, archivo, raiz))
    return len(shas), m, len(shas) - m


def frase_cuenta(n: int, m: int, k: int) -> str:
    return (
        f"({n} commits; {m} se citan en esta copia fuera de este archivo y {k} solo en documentos de trabajo "
        "que no se publican)"
    )


def reescribir_cuenta(texto: str, archivo: str, raiz: Path = RAIZ) -> str:
    n, m, k = cuenta(texto, archivo, raiz)
    nuevo, hechos = ENCABEZADO_CUENTA.subn(frase_cuenta(n, m, k), texto, count=1)
    if not hechos:
        raise SystemExit("no encuentro la frase de la cuenta en el encabezado")
    return nuevo


def insertar(texto: str, fecha: str, entrada: str) -> str:
    pre, entradas, cola = partir(texto)
    nueva_sha = CABECERA.match(entrada).group(1)  # type: ignore[union-attr]
    if nueva_sha in {sha_de(e) for e in entradas}:
        raise SystemExit(f"`{nueva_sha}` ya tiene su entrada")
    items = [e.rstrip("\n") + "\n" for e in entradas]
    # Después de las entradas con fecha igual o anterior (las de la misma hora conservan su orden en el archivo).
    pos = sum(1 for e in entradas if fecha_de(e) <= fecha)
    items.insert(pos, entrada.rstrip("\n") + "\n")
    return pre + "\n".join(items) + ("\n" + cola if cola else "")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("shas", nargs="*", metavar="SHA")
    p.add_argument("--archivo", default=ARCHIVO)
    p.add_argument("--tip", default="HEAD")
    p.add_argument(
        "--completa", action="store_true", help="sin el tope de 60 líneas por archivo"
    )
    p.add_argument(
        "--todos-los-archivos",
        action="store_true",
        help="hasta 5 archivos de pipeline/",
    )
    p.add_argument(
        "--escribir",
        action="store_true",
        help="inserta la entrada y reescribe la cuenta del encabezado",
    )
    p.add_argument(
        "--recontar", action="store_true", help="solo recuenta (N, M, K) del encabezado"
    )
    a = p.parse_args(argv)
    ruta = RAIZ / a.archivo
    if a.recontar:
        texto = ruta.read_text(encoding="utf-8")
        if a.escribir:
            texto = reescribir_cuenta(texto, a.archivo)
            ruta.write_text(texto, encoding="utf-8")
        print(frase_cuenta(*cuenta(texto, a.archivo)))
        return 0
    if not a.shas:
        p.error("falta al menos un SHA (o --recontar)")
    nuevas = [
        armar_entrada(s, tip=a.tip, completa=a.completa, todos=a.todos_los_archivos)
        for s in a.shas
    ]
    if not a.escribir:
        print("\n".join(e for _, e in nuevas), end="")
        return 0
    texto = ruta.read_text(encoding="utf-8")
    for fecha, entrada in nuevas:
        texto = insertar(texto, fecha, entrada)
    texto = reescribir_cuenta(texto, a.archivo)
    ruta.write_text(texto, encoding="utf-8")
    print(frase_cuenta(*cuenta(texto, a.archivo)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
