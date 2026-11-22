"""Sistema visual compartido ("Horizonte", v2): colores, fuentes, hoja de estilo base y estilo de figuras, en un solo lugar.

Lo importan los generadores de páginas (`pipeline/report.py` y los demás) y los de figuras. Acá no hay selectores de una
página en particular: lo que solo vale para una página va en su plantilla. La dirección completa está en
`direccion-ui-v2.md` (carpeta de handoff del 2026-11-21); este módulo es su traducción a código.

  css_fuentes()       las dos reglas `@font-face` (Archivo y Faustina, autoalojadas en site/fuentes/)
  css_tokens()        el bloque `:root` (claro) y su versión oscura (`prefers-color-scheme` y `data-theme`)
  CSS_BASE            escala tipográfica, espacios, enlaces, detalles y las marcas de veredicto
  estilo_matplotlib() diccionario de rcParams con los colores v1 (TOKENS_FIGURAS), para `plt.rc_context`
  contexto_matplotlib() lo mismo como administrador de contexto

Las plantillas lo reciben por el marcador `/*__SISTEMA__*/` (ver `pipeline.report`).
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

# nombre -> (claro, oscuro). La portada v2 ("Horizonte", direccion-ui-v2.md): siete colores y nada más. El cielo es el
# campo de arriba (los pozos de control) y el fondo del resto de la página; la estepa, el de abajo (los padres); la
# lutita, la banda de la brecha y nada más. De noche es el mismo lugar.
TOKENS: dict[str, tuple[str, str]] = {
    "cielo": ("#C9D7DC", "#18222B"),
    "estepa": ("#A39A7A", "#3A362B"),
    "lutita": ("#2A2623", "#0F0E0D"),
    # el borde de la banda: invisible de día (igual a la lutita); de noche la lutita casi no se separa del cielo oscuro
    # (1,1 a 1), así que la orilla la dibuja en jarilla (7,2 a 1 sobre el cielo)
    "orilla": ("#2A2623", "#9FB0B6"),
    "tinta": ("#1B2A31", "#E6DFCF"),      # texto sobre cielo y estepa
    "hueso": ("#EDE6D6", "#EDE6D6"),      # la cifra adentro de la banda
    "jarilla": ("#3E4A4F", "#9FB0B6"),    # texto secundario, pies, veredictos
}

# Las cinco tintas categóricas de los gráficos de operadores del tablero, debajo de la historia (no son de la historia).
SERIES: dict[str, tuple[str, str]] = {
    "s1": ("#2A78D6", "#3987E5"),
    "s2": ("#0E6F6B", "#5CC9BC"),
    "s3": ("#C2592F", "#E0825E"),
    "s4": ("#B88A00", "#D9B23A"),
    "s5": ("#C0508A", "#DE7FB0"),
}

# Los colores v1 ("Estepa") quedan solo para las dos figuras PNG de "Ver los números", que no cambian hasta que el
# dueño diga que sí a v2 (`pipeline.figuras_sitio`). Ninguna hoja de estilo los usa.
TOKENS_FIGURAS: dict[str, tuple[str, str]] = {
    "papel": ("#F2F4F1", "#16211F"),
    "tinta": ("#17262B", "#E6EBE7"),
    "jarilla": ("#5E6A66", "#93A19C"),
    "medido": ("#0E6F6B", "#5CC9BC"),
    "supuesto": ("#6A55B0", "#B3A2EE"),
    "linea": ("#D5DBD6", "#2A3936"),
}

# Marcas de veredicto en texto (Markdown y copias de revisión); en la página son las clases .marca--*.
MARCAS: dict[str, str] = {"pleno": "●", "medio": "◐", "vacio": "○"}

# El naranja del marcador del pozo nuevo sobre la foto satelital: la única excepción a los colores del sistema, con nombre para que
# una prueba de colores sueltos pueda permitirla.
MARCADOR_POZO_NUEVO = "#E8A33D"

# Escala tipográfica (px): pies 14, oración 17 a 19, preguntas 27 a 40; la cifra de la banda va de 56 a 120.
ESCALA = (14, 17, 19, 27, 40)
ESPACIOS = (4, 8, 16, 24, 40, 64)

# Las dos familias son de Omnibus-Type (Buenos Aires), OFL, servidas desde site/fuentes/ con su OFL.txt al lado.
ARCHIVO = '"Archivo", "Arial Narrow", system-ui, sans-serif'
FAUSTINA = '"Faustina", Georgia, serif'
FUENTES = {
    "Archivo": ("fuentes/archivo/Archivo.woff2", "100 900", "62% 125%"),
    "Faustina": ("fuentes/faustina/Faustina.woff2", "300 800", None),
}


def css_fuentes() -> str:
    """Las dos reglas `@font-face`, autoalojadas (ninguna fuente se pide a otro servidor)."""
    reglas = []
    for familia, (ruta, pesos, anchos) in FUENTES.items():
        ancho = f" font-stretch: {anchos};" if anchos else ""
        reglas.append(f'@font-face {{ font-family: "{familia}"; src: url("{ruta}") format("woff2"); font-weight: {pesos};{ancho} '
                      'font-style: normal; font-display: swap; }')
    return "\n".join(reglas) + "\n"


def _bloque(indice: int) -> str:
    return "\n".join(f"  --{nombre}: {valores[indice]};" for nombre, valores in (TOKENS | SERIES).items())


def css_tokens() -> str:
    """`:root` claro, oscuro por preferencia del sistema y oscuro forzado por `data-theme="dark"`."""
    return (
        f":root {{\n  color-scheme: light;\n{_bloque(0)}\n}}\n"
        "@media (prefers-color-scheme: dark) {\n"
        f'  :root:where(:not([data-theme="light"])) {{\n    color-scheme: dark;\n{_bloque(1).replace("  --", "    --")}\n  }}\n}}\n'
        f':root[data-theme="dark"] {{\n  color-scheme: dark;\n{_bloque(1)}\n}}\n'
    )


CSS_BASE = f"""
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }}
body {{ margin: 0; background: var(--cielo); color: var(--tinta); font: 400 17px/1.55 {FAUSTINA}; font-variant-numeric: lining-nums; }}
@media (min-width: 900px) {{ body {{ font-size: 18px; }} }}
h1, h2, h3 {{ font-family: {ARCHIVO}; font-weight: 600; font-stretch: 100%; line-height: 1.1; margin: 0; letter-spacing: -0.005em; }}
h1 {{ font-size: 40px; }}
h2 {{ font-size: 27px; }}
@media (min-width: 900px) {{ h2 {{ font-size: 40px; }} h1 {{ font-size: 56px; }} }}
h3 {{ font-size: 19px; }}
p {{ margin: 0 0 16px; }}
a {{ color: inherit; text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 3px;
  text-decoration-color: color-mix(in srgb, currentColor 45%, transparent); }}
a:hover, a:focus-visible {{ text-decoration-color: currentColor; }}
:focus-visible {{ outline: 2px solid var(--tinta); outline-offset: 3px; }}
img {{ max-width: 100%; height: auto; }}
figure {{ margin: 24px 0; }}
figcaption, .pie {{ font-size: 14px; line-height: 1.45; color: var(--jarilla); margin-top: 8px; }}
details {{ margin: 16px 0; }}
summary {{ cursor: pointer; min-height: 44px; display: inline-flex; align-items: center; gap: 8px; font-weight: 600; list-style: none; }}
summary::-webkit-details-marker {{ display: none; }}
summary::before {{ content: ""; width: 0; height: 0; border-style: solid; border-width: 5px 0 5px 7px;
  border-color: transparent transparent transparent currentColor; transition: transform 160ms ease-out; }}
details[open] > summary::before {{ transform: rotate(90deg); }}
@media (prefers-reduced-motion: reduce) {{ summary::before {{ transition: none; }} }}
/* veredicto: una marca dibujada (disco, medio disco, anillo) en tinta y las palabras de siempre en jarilla */
.veredicto {{ font-family: {ARCHIVO}; font-size: 17px; line-height: 1.4; color: var(--jarilla); margin: 8px 0 16px; display: flex; flex-wrap: wrap; gap: 4px 24px; }}
.veredicto > span {{ display: inline-flex; align-items: baseline; gap: 8px; }}
.marca {{ display: inline-block; width: 12px; height: 12px; border: 1.5px solid var(--tinta); border-radius: 50%; flex: none; transform: translateY(1px); }}
.marca--pleno {{ background: var(--tinta); }}
.marca--medio {{ background: linear-gradient(90deg, var(--tinta) 50%, transparent 50%); }}
.marca--vacio {{ background: transparent; }}
/* pie de todas las páginas: la lista de enlaces del sitio */
.pie-sitio {{ display: flex; flex-wrap: wrap; gap: 0 24px; margin: 64px 0 24px; padding-top: 16px; }}
.pie-sitio a {{ display: inline-flex; align-items: center; min-height: 44px; font-size: 17px; }}
""".strip() + "\n"


def sistema_css() -> str:
    """Todo lo que una página recibe por `/*__SISTEMA__*/`."""
    return css_fuentes() + css_tokens() + CSS_BASE


def estilo_matplotlib(modo: str = "claro") -> dict:
    """rcParams de matplotlib con los colores del sistema, para `matplotlib.pyplot.rc_context(estilo_matplotlib())`.

    Sin marco, sin rejilla, sin leyenda; los ejes en tinta, los textos a 14 px (10,5 pt a 96 ppp) con cifras tabulares.
    Pensado para figuras de 350 px CSS de ancho dibujadas a 2x (dpi 192). `modo` es "claro" u "oscuro".
    """
    i = {"claro": 0, "oscuro": 1}[modo]
    c = {nombre: valores[i] for nombre, valores in TOKENS_FIGURAS.items()}
    return {
        "figure.facecolor": "none", "axes.facecolor": "none", "savefig.facecolor": "none", "savefig.transparent": True,
        "figure.dpi": 192, "savefig.dpi": 192,
        "font.family": "serif", "font.serif": ["Charter", "Georgia", "Noto Serif", "DejaVu Serif"],
        "font.size": 10.5, "axes.labelsize": 10.5, "xtick.labelsize": 10.5, "ytick.labelsize": 10.5,
        "text.color": c["tinta"], "axes.labelcolor": c["tinta"], "xtick.color": c["tinta"], "ytick.color": c["tinta"],
        "axes.edgecolor": c["linea"], "axes.linewidth": 1.0, "axes.grid": False,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 6, "ytick.major.pad": 4,
        "lines.linewidth": 2.0, "lines.solid_capstyle": "round", "lines.dash_capstyle": "butt",
        "legend.frameon": False, "axes.unicode_minus": False,  # el guion común, igual que en el texto de la página
        "axes.prop_cycle": f"cycler('color', ['{c['medido']}', '{c['jarilla']}', '{c['supuesto']}'])",
        "svg.fonttype": "none",
    }


def colores(modo: str = "claro") -> dict[str, str]:
    """Los colores v1 de las figuras PNG en el modo pedido, para dibujar con ellos fuera de las rcParams."""
    i = {"claro": 0, "oscuro": 1}[modo]
    return {nombre: valores[i] for nombre, valores in TOKENS_FIGURAS.items()}


@contextmanager
def contexto_matplotlib(modo: str = "claro") -> Iterator[None]:
    """`with contexto_matplotlib("oscuro"): ...`: las rcParams del sistema solo adentro del bloque."""
    import matplotlib.pyplot as plt

    with plt.rc_context(estilo_matplotlib(modo)):
        yield
