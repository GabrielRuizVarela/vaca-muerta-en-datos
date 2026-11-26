"""Registro de brechas: lo que el estudio no sabe todavía, quién lo cierra y qué frases públicas dependen de eso.

La fuente es `wiki/hallazgos/brechas.csv` (a mano). Este módulo la valida contra el repo y escribe dos salidas:
`wiki/hallazgos/brechas.md` (la tabla completa) y la lista numerada de brechas abiertas entre los marcadores
`<!-- brechas:inicio -->` y `<!-- brechas:fin -->` de `docs/proceso/siguientes-investigaciones.md`.

  uv run python -m pipeline.brechas      # exit 1 si el CSV no valida

Prioridad (fórmula fija, sin juicio): la cantidad de entradas distintas de `bloquea` que apuntan a un fichero público
(README.md, docs/paper/paper.md, docs/resumen-operador.md, site/index.html). Una entrada es un id de pipeline.claims
(cuenta por el fichero de ese claim) o una referencia `archivo:linea`. Empate: por id.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "wiki" / "hallazgos" / "brechas.csv"
SALIDA = ROOT / "wiki" / "hallazgos" / "brechas.md"
SIGUIENTES = ROOT / "docs" / "proceso" / "siguientes-investigaciones.md"
INICIO = "<!-- brechas:inicio -->"
FIN = "<!-- brechas:fin -->"

COLUMNAS = ("id", "texto", "tipo", "bloquea", "cierra", "donde", "estado", "cerrada_por")
TIPOS = {"dato_que_falta", "fuente_sin_verificar", "lectura_pendiente", "metodo"}
CIERRA = {"operador", "otra_cuenca", "lectura", "codigo"}
ESTADOS = {"abierta", "cerrada"}
PUBLICOS = ("README.md", "docs/paper/paper.md", "docs/resumen-operador.md", "site/index.html")
_REF = re.compile(r"^(.+):(\d+)$")

QUE_CIERRA = {"operador": "datos del operador", "otra_cuenca": "datos de otra cuenca",
              "lectura": "leer la fuente", "codigo": "código"}
TIPO_TEXTO = {"dato_que_falta": "dato que falta", "fuente_sin_verificar": "fuente sin verificar",
              "lectura_pendiente": "lectura pendiente", "metodo": "método"}


def cargar(ruta: Path | None = None) -> list[dict]:
    with open(CSV if ruta is None else ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _entradas(b: dict) -> list[str]:
    return [e.strip() for e in (b.get("bloquea") or "").split(";") if e.strip()]


def _ficheros_de_claims() -> dict[str, str]:
    from pipeline.claims import CAPACIDADES, CLAIMS
    return {c.id: c.fichero for c in [*CLAIMS, *CAPACIDADES]}


def _fichero_de(entrada: str, claims: dict[str, str]) -> str | None:
    m = _REF.match(entrada)
    if m:
        return m.group(1)
    return claims.get(entrada)


def _publicas(b: dict, claims: dict[str, str] | None = None) -> list[str]:
    claims = _ficheros_de_claims() if claims is None else claims
    return sorted({e for e in _entradas(b) if _fichero_de(e, claims) in PUBLICOS})


def prioridad(b: dict, claims: dict[str, str] | None = None) -> int:
    """Entradas distintas de `bloquea` que apuntan a un fichero público."""
    return len(_publicas(b, claims))


def validar(brechas: list[dict], raiz: Path | None = None, claims: dict[str, str] | None = None) -> list[str]:
    raiz = ROOT if raiz is None else raiz
    claims = _ficheros_de_claims() if claims is None else claims
    errores: list[str] = []
    vistos: set[str] = set()
    for b in brechas:
        i = b.get("id") or "?"
        if i in vistos:
            errores.append(f"{i}: id repetido")
        vistos.add(i)
        for col in COLUMNAS:
            if col not in b:
                errores.append(f"{i}: falta la columna {col}")
        for col, valores in (("tipo", TIPOS), ("cierra", CIERRA), ("estado", ESTADOS)):
            if b.get(col) not in valores:
                errores.append(f"{i}: {col} '{b.get(col)}' no está en {sorted(valores)}")
        if not (b.get("texto") or "").strip():
            errores.append(f"{i}: texto vacío")
        m = _REF.match(b.get("donde") or "")
        if not m:
            errores.append(f"{i}: donde '{b.get('donde')}' no es archivo:linea")
        else:
            errores += _revisar_ref(i, "donde", m.group(1), int(m.group(2)), raiz)
        for e in _entradas(b):
            m = _REF.match(e)
            if m:
                errores += _revisar_ref(i, "bloquea", m.group(1), int(m.group(2)), raiz)
            elif e not in claims:
                errores.append(f"{i}: bloquea '{e}' no es un id de pipeline.claims ni archivo:linea")
        if b.get("estado") == "cerrada" and not (b.get("cerrada_por") or "").strip():
            errores.append(f"{i}: está cerrada y no dice por qué (cerrada_por)")
    return errores


def _revisar_ref(i: str, campo: str, archivo: str, linea: int, raiz: Path) -> list[str]:
    p = raiz / archivo
    if not p.is_file():
        return [f"{i}: {campo} {archivo}:{linea}: no existe {archivo}"]
    n = len(p.read_text(encoding="utf-8").splitlines())
    if not 1 <= linea <= n:
        return [f"{i}: {campo} {archivo}:{linea}: el archivo tiene {n} líneas"]
    return []


def ordenadas(brechas: list[dict], claims: dict[str, str] | None = None) -> list[dict]:
    claims = _ficheros_de_claims() if claims is None else claims
    return sorted(brechas, key=lambda b: (-prioridad(b, claims), b["id"]))


def _celda(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def tabla_md(brechas: list[dict], claims: dict[str, str] | None = None) -> str:
    claims = _ficheros_de_claims() if claims is None else claims
    out = ["# Brechas del estudio",
           "",
           "Generado por `python -m pipeline.brechas` desde `wiki/hallazgos/brechas.csv`; no se edita a mano.",
           "",
           "Una brecha es algo que el estudio no sabe o no leyó todavía y que una frase pública da por resuelto o deja "
           "en el aire. La prioridad es una fórmula fija: la cantidad de entradas distintas de `bloquea` que apuntan a "
           "un fichero público (`README.md`, `docs/paper/paper.md`, `docs/resumen-operador.md`, `site/index.html`); un "
           "id de `pipeline/claims.py` cuenta por el fichero de su claim y una referencia `archivo:linea` cuenta por su "
           "archivo. Si dos brechas empatan, va primero la de id menor. Nadie ordena a mano.",
           "",
           "| Id | Brecha | Tipo | Qué la cierra | Frases públicas que bloquea | Dónde está escrita | Estado |",
           "|---|---|---|---|---|---|---|"]
    for b in ordenadas(brechas, claims):
        pub = _publicas(b, claims)
        frases = "<br>".join(f"`{e}`" for e in pub) if pub else "ninguna"
        estado = b["estado"] + (f" ({b['cerrada_por']})" if b["cerrada_por"] else "")
        out.append(f"| {b['id']} | {_celda(b['texto'])} | {TIPO_TEXTO[b['tipo']]} | {QUE_CIERRA[b['cierra']]} | "
                   f"{frases} ({prioridad(b, claims)}) | `{b['donde']}` | {estado} |")
    return "\n".join(out) + "\n"


def lista_md(brechas: list[dict], claims: dict[str, str] | None = None) -> str:
    abiertas = [b for b in ordenadas(brechas, claims) if b["estado"] == "abierta"]
    if not abiertas:
        return "No hay brechas abiertas.\n"
    return "".join(f"{n}. **{b['id']}** ({QUE_CIERRA[b['cierra']]}): {b['texto']} (`{b['donde']}`)\n"
                   for n, b in enumerate(abiertas, 1))


def reescribir_lista(texto: str, lista: str) -> str:
    if INICIO not in texto or FIN not in texto or texto.index(INICIO) > texto.index(FIN):
        raise ValueError(f"faltan los marcadores {INICIO} y {FIN}")
    a = texto.index(INICIO) + len(INICIO)
    return texto[:a] + "\n" + lista + texto[texto.index(FIN):]


def main(argv: list[str] | None = None) -> int:
    brechas = cargar()
    errores = validar(brechas)
    if errores:
        print("brechas.csv no valida:", file=sys.stderr)
        for e in errores:
            print(f"  {e}", file=sys.stderr)
        return 1
    claims = _ficheros_de_claims()
    SALIDA.write_text(tabla_md(brechas, claims), encoding="utf-8")
    SIGUIENTES.write_text(reescribir_lista(SIGUIENTES.read_text(encoding="utf-8"), lista_md(brechas, claims)), encoding="utf-8")
    abiertas = sum(1 for b in brechas if b["estado"] == "abierta")
    print(f"{len(brechas)} brechas ({abiertas} abiertas); escrito {SALIDA.relative_to(ROOT)} y la lista de {SIGUIENTES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
