"""Las cifras no cambian al reescribir la prosa de la puerta de entrada (README, tablero y páginas del sitio, hallazgos del wiki).

Sin datos ni warehouse: compara las cifras del texto versionado contra una foto congelada de antes de la reescritura
(`tests/fixtures/deslop_numeros_antes.json`, sacada de main en 05de1ca, antes de que la historia abriera el README y el sitio).

Una cifra es todo número con sus separadores y su signo (1.500, -23,0, 0,036), un porcentaje (51%) o una fecha
(2026-11-18). En el README y en el wiki se cuenta el texto entero. En las páginas HTML se cuenta el texto visible
(sin script ni style) y, aparte, el conjunto de números de todo el archivo (datos, estilos y guiones) como huella.

El contrato:
1. Las páginas que no son la puerta de entrada (hallazgos del wiki y páginas del sitio salvo `index.html`) conservan cada
   cifra, con su cantidad, igual que en la foto.
2. La puerta de entrada (README y `site/index.html`) puede repetir y reordenar cifras, porque la historia las cuenta de
   nuevo, pero el conjunto de cifras distintas de todo el repositorio visible no cambia: no entra ninguna y solo sale la
   que se declara en REMOVIDAS con su motivo (la meta es cero).
3. Toda cifra de la historia de `site/index.html` y de la apertura del README ya estaba en la foto: no se inventa ni se
   cambia ninguna.
4. Los datos que lleva `site/index.html` (el objeto `const D`) son idénticos a los de la foto.
   Una excepción declarada (fix/cifras-discordantes): `costo_cv.media` pasó de la media del entrenamiento (-0.0029998...)
   a la media del área (-0.027, redondeada del wiki a 3 decimales: el dato crudo del 2026-11-20 ya no existe), para que
   el sitio compare contra la misma referencia que el README. La huella de la foto se rehízo solo por eso.

Para rehacer la foto (solo si cambia la base): `python tests/test_deslop_numeros.py --congelar <ref-git>`.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FOTO = Path(__file__).resolve().parent / "fixtures" / "deslop_numeros_antes.json"

FECHA = r"\d{4}-\d{2}-\d{2}"
NUMERO = r"(?:(?<![\w.,])[-+])?\d+(?:[.,]\d+)*%?"
CIFRA = re.compile(f"{FECHA}|{NUMERO}")
TESTS_README = re.compile(r"hay \d+ tests")

# cifra -> motivo. Cifras que estaban en la foto y ya no están en ninguna página. Vacío si todo se conserva.
REMOVIDAS: dict[str, str] = {}

# La puerta de entrada: los dos archivos que la historia reescribió.
PUERTA = ("README.md", "site/index.html")

PAGINAS_HTML = ["site/index.html", "site/informe.html", "site/replay.html", "site/mundo.html", "site/globo.html"]


def archivos() -> list[str]:
    wiki = sorted(p.relative_to(RAIZ).as_posix() for p in (RAIZ / "wiki" / "hallazgos").glob("*.md"))
    return ["README.md", *wiki, *PAGINAS_HTML]


class _Visible(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.oculto = 0
        self.partes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self.oculto += 1
        self.partes.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.oculto -= 1
        self.partes.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.oculto:
            self.partes.append(data)


def cifras(texto: str) -> Counter:
    return Counter(CIFRA.findall(texto))


def visible(html: str) -> str:
    p = _Visible()
    p.feed(html)
    return "".join(p.partes)


def huella(c: Counter) -> str:
    return hashlib.sha256(json.dumps(sorted(c.items())).encode()).hexdigest()


def datos_de(html: str) -> str:
    """El script con los datos del tablero (`const D = {...}`), o vacío si la página no lo lleva."""
    i = html.find("const D = ")
    return "" if i < 0 else html[i : html.index("</script>", i)]


def historia_de(ruta: str, texto: str) -> str:
    """Lo que la historia cuenta: el artículo de apertura del sitio o lo que va antes del bloque en inglés del README."""
    if ruta == "README.md":
        return texto[: texto.index("## Result\n")]
    return visible(texto[texto.index('<article class="historia"') : texto.index('<div class="tablero"')])


def foto_de(ruta: str, texto: str) -> dict:
    if ruta == "README.md":
        texto = TESTS_README.sub("hay N tests", texto)
    if ruta.endswith(".html"):
        foto = {"visible": dict(cifras(visible(texto))), "huella_archivo": huella(cifras(texto))}
        if ruta == "site/index.html":
            foto["huella_datos"] = huella(cifras(datos_de(texto)))
        return foto
    return {"texto": dict(cifras(texto))}


def _figuras(foto: dict) -> set[str]:
    return set(foto.get("visible", foto.get("texto", {})))


def congelar(ref: str) -> None:
    salida = {}
    for ruta in archivos():
        texto = subprocess.run(["git", "show", f"{ref}:{ruta}"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
        salida[ruta] = foto_de(ruta, texto)
    FOTO.parent.mkdir(exist_ok=True)
    FOTO.write_text(json.dumps(salida, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf8")
    print(f"{len(salida)} archivos en {FOTO}")


def _delta(antes: dict, despues: dict) -> dict[str, int]:
    d = {k: despues.get(k, 0) - antes.get(k, 0) for k in set(antes) | set(despues)}
    return {k: v for k, v in sorted(d.items()) if v}


def _antes() -> dict:
    return json.loads(FOTO.read_text(encoding="utf8"))


@pytest.mark.parametrize("ruta", [r for r in archivos() if r not in PUERTA])
def test_las_cifras_no_cambian(ruta: str) -> None:
    antes = _antes()
    assert ruta in antes, f"{ruta} no está en la foto: rehacerla con --congelar si la página es nueva a propósito"
    ahora = foto_de(ruta, (RAIZ / ruta).read_text(encoding="utf8"))
    if ruta.endswith(".html"):
        assert _delta(antes[ruta]["visible"], ahora["visible"]) == {}, f"cambiaron cifras del texto visible de {ruta}"
        assert antes[ruta]["huella_archivo"] == ahora["huella_archivo"], f"cambiaron cifras dentro del código de {ruta}"
    else:
        assert _delta(antes[ruta]["texto"], ahora["texto"]) == {}, f"cambiaron cifras de {ruta}"


def _ahora_de_todos() -> dict[str, dict]:
    return {r: foto_de(r, (RAIZ / r).read_text(encoding="utf8")) for r in archivos()}


def test_el_conjunto_de_cifras_de_la_puerta_se_conserva() -> None:
    antes, ahora = _antes(), _ahora_de_todos()
    previas = set().union(*(_figuras(antes[r]) for r in archivos()))
    actuales = set().union(*(_figuras(ahora[r]) for r in archivos()))
    assert actuales - previas == set(), "entraron cifras que no estaban en la foto"
    assert previas - actuales == set(REMOVIDAS), "salieron cifras sin declarar (o se declaró una que sigue): REMOVIDAS lleva cada una con su motivo"
    assert all(REMOVIDAS.values()), "cada cifra removida lleva su motivo"


@pytest.mark.parametrize("ruta", PUERTA)
def test_la_historia_solo_cuenta_cifras_de_la_foto(ruta: str) -> None:
    antes = _antes()
    previas = set().union(*(_figuras(antes[r]) for r in archivos()))
    texto = (RAIZ / ruta).read_text(encoding="utf8")
    propias = set(cifras(historia_de(ruta, texto)))
    assert propias, f"la historia de {ruta} no tiene cifras: ¿cambió el marcador de dónde empieza o termina?"
    assert propias - previas == set(), f"cifras de la historia de {ruta} que no estaban antes"


def test_los_datos_del_tablero_son_los_mismos() -> None:
    antes = _antes()["site/index.html"]["huella_datos"]
    assert foto_de("site/index.html", (RAIZ / "site/index.html").read_text(encoding="utf8"))["huella_datos"] == antes


def test_la_historia_no_menciona_dashes() -> None:
    for ruta in PUERTA:
        assert not re.search(f"[{chr(0x2013)}{chr(0x2014)}]", historia_de(ruta, (RAIZ / ruta).read_text(encoding="utf8")))


def test_la_foto_cubre_los_mismos_archivos() -> None:
    assert sorted(_antes()) == sorted(archivos()), "hay una página del wiki nueva o borrada: rehacer la foto o declararla"


def test_el_extractor_cuenta_lo_que_importa() -> None:
    c = cifras("de -35,9 a -19,7 (IC 95%), 1.500 m, 2016-2023, 2026-11-18, pad-p166915, 0,036")
    assert c["-35,9"] == 1 and c["-19,7"] == 1 and c["95%"] == 1 and c["1.500"] == 1
    assert c["2016"] == 1 and c["2023"] == 1 and c["2026-11-18"] == 1 and c["166915"] == 1 and c["0,036"] == 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--congelar":
        congelar(sys.argv[2])
    else:
        sys.exit(__doc__)
