"""Las cifras no cambian al reescribir la prosa de la puerta de entrada (README, tablero y páginas del sitio, hallazgos del wiki).

Sin datos ni warehouse: compara las cifras del texto versionado contra una foto congelada de antes de la reescritura
(`tests/fixtures/deslop_numeros_antes.json`, sacada de main en 05de1ca, antes de que la historia abriera el README y el sitio).

Una cifra es todo número con sus separadores y su signo (1.500, -23,0, 0,036), un porcentaje (51%) o una fecha
(2026-11-18). En el README y en el wiki se cuenta el texto entero. En las páginas HTML se cuenta el texto visible
(sin script ni style) y, aparte, el conjunto de números de todo el archivo (datos, estilos y guiones) como huella.

El contrato:
1. Las páginas que no son la puerta de entrada (hallazgos del wiki y páginas del sitio salvo `index.html`) conservan cada
   cifra, con su cantidad, igual que en la foto, salvo las que se declaran en REMOVIDAS con su motivo.
2. La puerta de entrada (README y `site/index.html`) puede repetir y reordenar cifras, porque la historia las cuenta de
   nuevo, pero el conjunto de cifras distintas de todo el repositorio visible no cambia: no entra ninguna y solo sale la
   que se declara en REMOVIDAS con su motivo (la meta es cero).
3. Toda cifra de la historia de `site/index.html` y de la apertura del README ya estaba en la foto: no se inventa ni se
   cambia ninguna.
4. Los datos que lleva `site/index.html` (el objeto `const D`) son idénticos a los de la foto.
   Una excepción declarada (fix/cifras-discordantes): `costo_cv.media` pasó de la media del entrenamiento (-0.0029998...)
   a la media del área (-0.027, redondeada del wiki a 3 decimales: el dato crudo del 2026-11-20 ya no existe), para que
   el sitio compare contra la misma referencia que el README. La huella de la foto se rehízo solo por eso.
   Otra excepción declarada (fix/replay-contador): el contador de `site/replay.html` deja de acumular y muestra el
   diferido del mes, porque un total que solo sube se lee como pérdida. Cambia solo el código del guion (sale el
   redondeo a millones), no el texto visible ni los datos; la huella del archivo de esa página se rehízo solo por eso.
   Otra excepción declarada (ui/informe-horizonte): `site/informe.html` pasa al sistema Horizonte (pipeline/sistema.py). Salen los números
   de las tres líneas de Google Fonts (pesos y anchos de IBM Plex y Archivo) y se rehizo solo la huella del archivo de esa
   página; el texto visible y los datos no cambian (se comprobó que, sin los bloques `<style>`, las cifras del archivo son las mismas
   salvo esas líneas).
   Otra excepción declarada (ui/replay-horizonte): `site/replay.html` y `site/mundo.html` pasan al sistema Horizonte
   (pipeline/sistema.py), de noche, y en cualquier configuración del sistema. Cambia solo el chrome (los bloques
   `<style>`, con los tokens y las dos letras del sistema); el texto visible y los datos no cambian, y la huella del
   archivo de esas dos páginas se rehízo solo por eso.
   En la misma rama, los `summary` de la leyenda y de las fuentes de `site/mundo.html` dejan el triángulo y el peso de
   la hoja base (tienen su propio ícono): la huella de mundo se rehízo otra vez solo por ese CSS.
   Otra excepción declarada (ui/mundo-marco-horizonte): el marco de `site/mundo.html` (placas, botones, planilla y
   barra de tiempo) pasa a los tokens del sistema Horizonte, y una frase del titular corrige qué son los controles de
   la comparación. Cambia solo el chrome (el bloque `<style>`) y esa frase; el texto visible conserva sus cifras, los
   datos no cambian, y la huella del archivo de esa página se rehízo solo por eso.
   Página nueva (estudio-dia-inicio): `wiki/hallazgos/dia_inicio.md` entró a la foto con sus cifras (el día de inicio como dosis, pipeline/dia_inicio.py).
   `wiki/hallazgos/linaje.md` se rehízo en la foto solo porque suma las seis tablas de ese módulo (de 168 a 174 tablas, de 929 a 959 relaciones).
   Página nueva (cota-rr-condicional): `wiki/hallazgos/cota_rr_condicional.md` entró a la foto con sus cifras (la cota de Rambachan y Roth con la prueba condicional, pipeline/cota_rr_condicional.py).
   Página nueva (replicacion-operadores): `wiki/hallazgos/replicacion_operadores.md` entró a la foto con sus cifras (la brecha del mes 1 operador por operador, pipeline/replicacion_operadores.py).
   `wiki/hallazgos/linaje.md` se rehízo en la foto solo porque suma las dos tablas de replicacion_operadores y la de cota_rr_condicional (de 187 a 190 tablas, de 1052 a 1063 relaciones).
   Página nueva (replicacion-operadores-agua): `wiki/hallazgos/replicacion_operadores_agua.md` entró a la foto con sus cifras (el corte de agua de D2 operador por operador, pipeline/replicacion_operadores_agua.py).
   `wiki/hallazgos/linaje.md` se rehízo en la foto solo porque suma las cuatro tablas de replicacion_operadores_agua (de 190 a 194 tablas, de 1063 a 1079 relaciones).
   Otra excepción declarada (ronda4-texto): `wiki/hallazgos/cota_rr_condicional.md` suma sus referencias de método
   (Rambachan y Roth 2023, Andrews, Roth y Pakes 2023, HonestDiD 0.2.8) y la sección de la cláusula de la regla que no se
   siguió; entran solo las cifras de esas referencias (año, volumen, número, páginas, DOI y versión) y los identificadores
   de esa sección (D1, ATT(1), el commit de19052, los meses 0 y 1). Las cifras del análisis no cambian; la clave de esa
   página se rehízo solo por eso.
   Ronda 4, S1 (contraste con HonestDiD): `wiki/hallazgos/cota_rr_condicional.md` suma las secciones "Contraste con HonestDiD" y "E y E2" (pipeline/cota_rr_contraste.py): cifras nuevas medidas por esa regla (quiebres y diferencias de las lecturas L1, L1p, L2 y L3, y la cota condicional de E y E2), con la regla fijada en 06f7720 y sus aclaraciones en 21e1a91; el resto de la página no cambia. `wiki/hallazgos/linaje.md` se rehízo en la foto solo porque suma la tabla mart_cota_rr_contraste (de 194 a 195 tablas, de 1079 a 1086 relaciones).
   Página nueva (espera): `site/espera.html` entró a la foto con sus cifras; las nuevas son los supuestos de la regla de plata (pipeline/espera.py).
   Otra excepción declarada (espera-claims): el control de `site/espera.html` se describe por la distancia ("a 2 a 5 km de
   un pozo nuevo") y no por la edad (revisión independiente, F1); entran el 2 y el 5 de esa distancia, que ya están en el
   README. La clave de esa página se rehízo solo por eso.
   Página del globo sobre el sistema v2 (`ui/globo-horizonte`): `site/globo.html` recibe la hoja de estilo del sistema, así que cambian
   los números que están dentro del archivo (tamaños de letra y colores de la base) y su huella se rehízo solo por eso. El texto visible
   y sus cifras no cambian.
   Otra excepción declarada (copy/auditoria-lenguaje): `site/mundo.html` y el README escriben con signo negativo el intervalo del mes 1
   ("-30,0 a -17,0" de la brecha de -23,0) y el cierre del mes 6 ("-2,1 y -4,8"), como el informe y el tablero (auditoría de la
   historia, ítem 9). Cada cifra pasa de su valor sin signo a su valor con signo; no entra ninguna cifra nueva en el repositorio. La clave
   de `site/mundo.html` se rehízo solo por eso.
   Otra excepción declarada (copy/auditoria-honestidad): `site/informe.html` suma la cota superior y la brecha previa a la fractura
   bajo el -23,0 de la ficha ("19 puntos menos" sin ella, y el mes 1 de la nota); `site/globo.html` suma que la brecha de Colorado al
   mes 6 no se cierra del todo (-5,9, que ya está en wiki/hallazgos/replicacion.md). Entran un "1" y dos "19" en informe, y un "-5,9" y un "6" en globo; ninguna es una cifra
   nueva en el repositorio. La clave de cada página se rehízo solo por eso.
   Otra excepción declarada (copy/claridad-1-terminos): un término por cosa en todo el sitio ("pozos vecinos", "subida del corte de agua",
   "La cuenca mes a mes", "Vaca Muerta en 3D"). `site/globo.html` llama "Vaca Muerta en 3D" a la página que antes llamaba "el mundo":
   entra un "3" en el texto visible, que ya está en el repositorio (nombre de esa página). En `site/replay.html` la leyenda del gráfico
   de rosas alinea a la derecha el texto "con subida del corte de agua", más largo que "con salto de agua": salen los desplazamientos
   de la leyenda vieja y entran los de la nueva, solo en el guion; el texto visible conserva sus cifras. En `site/espera.html` la etiqueta
   del gráfico "pozos vecinos" va en dos renglones (el margen derecho del gráfico no alcanza para uno): entran las posiciones del segundo
   renglón, solo en el guion. La clave de cada página se rehízo solo por eso.
   Otra excepción declarada (docs/articulos-leidos): `wiki/hallazgos/literatura.md` cita ahora con página las cifras de tres
   trabajos leídos completos (Crespo 2020, Min 2023 y el URTeC 2690466 de 2017): muestras, espaciamientos, años de depleción y
   porcentajes de esos trabajos, ninguna cifra medida por este proyecto. La clave de esa página se rehízo solo por eso.
   Otra excepción declarada (docs/fable-cierre-2): en esa misma página, la cita de las cifras de la simulación del
   URTeC 2690466 pasa de "p. 14-15" a "p. 14", la página donde están en el original; sale un "15", que era un
   número de página. La clave de esa página se rehízo solo por eso.

Para rehacer la foto (solo si cambia la base): `python tests/test_deslop_numeros.py --congelar <ref-git>`.
Para rehacer solo las páginas cuyas cifras cambian a propósito: `python tests/test_deslop_numeros.py --refotear <ruta> [<ruta> ...]`.
La foto va un renglón por página, así dos ramas que rehacen páginas distintas se juntan sin conflicto.
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
# Una cifra declarada sale de una página y de la foto: el archivo congelado no se toca, se declara la excepción.
REMOVIDAS: dict[str, str] = {}
# 28726 y 33591 (filas de una fuente cuyos términos no permiten reproducirlas) salieron de la foto el 2026-11-26, al rehacer
# la clave de wiki/hallazgos/fuentes_mundo.md con el reintento de cuatro fuentes de EE. UU.

# La puerta de entrada: los dos archivos que la historia reescribió.
PUERTA = ("README.md", "site/index.html")

PAGINAS_HTML = ["site/index.html", "site/informe.html", "site/replay.html", "site/mundo.html", "site/globo.html",
                "site/espera.html"]


def archivos() -> list[str]:
    # brechas.md lo genera pipeline.brechas desde brechas.csv: sus cifras son ids (B01) y numeros de linea, no prosa de la puerta
    wiki = sorted(p.relative_to(RAIZ).as_posix() for p in (RAIZ / "wiki" / "hallazgos").glob("*.md") if p.name != "brechas.md")
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
    """Lo que la historia cuenta: el artículo de apertura del sitio o lo que va antes de "Mirá esto primero" en el README (el abstract en inglés, el Resumen y las seis preguntas)."""
    if ruta == "README.md":
        return texto[: texto.index("## Mirá esto primero")]
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
    escribir_foto(salida)
    print(f"{len(salida)} archivos en {FOTO}")


def escribir_foto(foto: dict) -> None:
    """Un renglon por pagina: dos ramas que rehacen paginas distintas se juntan sin conflicto."""
    renglones = [json.dumps(k, ensure_ascii=False) + ":" + json.dumps(foto[k], sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                 for k in sorted(foto)]
    FOTO.parent.mkdir(exist_ok=True)
    FOTO.write_text("{\n" + ",\n".join(renglones) + "\n}\n", encoding="utf8")


def refotear(rutas: list[str]) -> None:
    """Rehace solo la clave de cada pagina nombrada, desde el arbol de trabajo (cuando sus cifras cambian a proposito)."""
    foto = json.loads(FOTO.read_text(encoding="utf8"))
    for ruta in rutas:
        foto[ruta] = foto_de(ruta, (RAIZ / ruta).read_text(encoding="utf8"))
    escribir_foto(foto)
    print(f"rehechas: {', '.join(rutas)}")


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
        delta = _delta(antes[ruta]["texto"], ahora["texto"])
        nuevas = {k for k, v in delta.items() if v > 0}
        assert nuevas == set(), f"entraron cifras nuevas en {ruta}"
        salidas = {k for k, v in delta.items() if v < 0}
        assert salidas <= set(REMOVIDAS), f"cambiaron cifras de {ruta}: declara en REMOVIDAS cada cifra que sale"


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
    elif len(sys.argv) >= 3 and sys.argv[1] == "--refotear":
        refotear(sys.argv[2:])
    else:
        sys.exit(__doc__)
