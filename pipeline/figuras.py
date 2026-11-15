"""Cuatro figuras SVG del caso de estudio (docs/caso-interferencia.md), generadas desde el warehouse.

  uv run python -m pipeline.figuras [--db data/warehouse.duckdb] [--out docs/img]

Cada escritor es una funcion pura de datos simples (listas de tuplas o diccionarios) que devuelve el texto del SVG:
determinista (formato numerico fijo, orden fijo, sin fechas ni identificadores al azar), sin fuentes externas y con
`<title>` y `<desc>`. Los datos salen de los marts ya construidos; esta pagina no calcula nada nuevo.
La cuarta (`inyeccion_svg`) pone lo recuperado contra lo plantado en la validacion por inyeccion.
Texto en espanol, sin rayas largas. Paleta de Okabe e Ito (segura para daltonismo) y trazos distintos por serie.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

import duckdb

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
SALIDA = ROOT / "docs" / "img"
ARCHIVOS = ("caso_event_study.svg", "caso_distancia.svg", "caso_anio.svg", "caso_inyeccion.svg")

ANCHO = 700
AZUL, NARANJA, NEGRO, GRIS, CLARO = "#0072B2", "#D55E00", "#222222", "#6b6b6b", "#e4e4e4"

ESTILO = f"""
text {{ fill: {NEGRO}; font-family: 'DejaVu Sans', Helvetica, Arial, sans-serif; font-size: 11px; }}
.titulo {{ font-size: 15px; font-weight: bold; }}
.sub {{ fill: {GRIS}; }}
.eje {{ stroke: {NEGRO}; stroke-width: 1; fill: none; }}
.rejilla {{ stroke: {CLARO}; stroke-width: 1; }}
.cero {{ stroke: {NEGRO}; stroke-width: 1.2; }}
.marca {{ stroke: {GRIS}; stroke-width: 1; stroke-dasharray: 4 3; }}
.banda {{ fill: #f0e442; fill-opacity: 0.25; }}
.pie {{ fill: {GRIS}; font-size: 10px; }}
""".strip()


def _n(x: float) -> str:
    """Numero con formato fijo (un decimal, punto) y sin menos cero."""
    s = f"{x:.1f}"
    return "0.0" if s == "-0.0" else s


def _c(x: float, dec: int = 1) -> str:
    """Numero para texto en espanol: coma decimal y sin menos cero."""
    s = f"{x:.{dec}f}"
    if float(s) == 0:
        s = f"{0:.{dec}f}"
    return s.replace(".", ",")


def _miles(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _escala(lo: float, hi: float) -> tuple[float, float, float]:
    """(minimo, maximo, paso) redondeados a un paso legible que contengan [lo, hi] y el cero."""
    lo, hi = min(lo, 0.0), max(hi, 0.0)
    span = max(hi - lo, 1e-9)
    paso = 5.0
    for cand in (1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0, 100.0):
        paso = cand
        if span / cand <= 7:
            break
    return math.floor(lo / paso) * paso, math.ceil(hi / paso) * paso, paso


def _ticks(lo: float, hi: float, paso: float) -> list[float]:
    out, v = [], lo
    while v <= hi + 1e-9:
        out.append(v)
        v += paso
    return out


def _abrir(alto: int, titulo: str, desc: str, cabecera: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}" width="{ANCHO}" height="{alto}" '
            'role="img" aria-labelledby="t d">',
            f'<title id="t">{escape(titulo)}</title>',
            f'<desc id="d">{escape(desc)}</desc>',
            f"<style>{ESTILO}</style>",
            f'<rect x="0" y="0" width="{ANCHO}" height="{alto}" fill="#ffffff"/>',
            f'<text class="titulo" x="20" y="26">{escape(titulo)}</text>',
            f'<text class="sub" x="20" y="43">{escape(cabecera)}</text>']


def _cerrar(out: list[str]) -> str:
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _panel_lineas(out: list[str], x0: float, y0: float, w: float, h: float, ks: list[int],
                  series: list[dict], ytitulo: str, marca_k: int | None, banda: tuple[int, int] | None,
                  xtitulo: str | None) -> None:
    """Un panel de lineas por k. Cada serie: {"nombre", "color", "trazo", "puntos": [(k, valor)]}."""
    valores = [v for s in series for _, v in s["puntos"]]
    lo, hi, paso = _escala(min(valores), max(valores))
    kmin, kmax = min(ks), max(ks)

    def px(k: float) -> float:
        return x0 + (k - kmin) / (kmax - kmin) * w

    def py(v: float) -> float:
        return y0 + h - (v - lo) / (hi - lo) * h

    if banda:
        a, b = px(banda[0] - 0.5), px(banda[1] + 0.5)
        out.append(f'<rect class="banda" x="{_n(a)}" y="{_n(y0)}" width="{_n(b - a)}" height="{_n(h)}"/>')
        out.append(f'<text class="pie" x="{_n((a + b) / 2)}" y="{_n(y0 + 11)}" text-anchor="middle">pretendencia</text>')
    for t in _ticks(lo, hi, paso):
        out.append(f'<line class="rejilla" x1="{_n(x0)}" y1="{_n(py(t))}" x2="{_n(x0 + w)}" y2="{_n(py(t))}"/>')
        out.append(f'<text x="{_n(x0 - 6)}" y="{_n(py(t) + 4)}" text-anchor="end">{_c(t, 0)}</text>')
    out.append(f'<line class="cero" x1="{_n(x0)}" y1="{_n(py(0))}" x2="{_n(x0 + w)}" y2="{_n(py(0))}"/>')
    out.append(f'<path class="eje" d="M{_n(x0)},{_n(y0)} L{_n(x0)},{_n(y0 + h)} L{_n(x0 + w)},{_n(y0 + h)}"/>')
    for k in ks:
        out.append(f'<text x="{_n(px(k))}" y="{_n(y0 + h + 14)}" text-anchor="middle">{k}</text>')
    if marca_k is not None and kmin <= marca_k <= kmax:
        out.append(f'<line class="marca" x1="{_n(px(marca_k))}" y1="{_n(y0)}" x2="{_n(px(marca_k))}" y2="{_n(y0 + h)}"/>')
    for s in series:
        pts = sorted(s["puntos"])
        d = " ".join(f'{"M" if i == 0 else "L"}{_n(px(k))},{_n(py(v))}' for i, (k, v) in enumerate(pts))
        dash = f' stroke-dasharray="{s["trazo"]}"' if s["trazo"] else ""
        out.append(f'<path d="{d}" fill="none" stroke="{s["color"]}" stroke-width="2"{dash}/>')
        for k, v in pts:
            out.append(f'<circle cx="{_n(px(k))}" cy="{_n(py(v))}" r="2.5" fill="{s["color"]}"/>')
        if marca_k is not None:
            for k, v in pts:
                if k == marca_k:
                    out.append(f'<circle cx="{_n(px(k))}" cy="{_n(py(v))}" r="6" fill="none" stroke="{s["color"]}" stroke-width="1.5"/>')
                    ancla, dx = ("start", 10) if marca_k < (kmin + kmax) / 2 else ("end", -10)
                    out.append(f'<text x="{_n(px(k) + dx)}" y="{_n(py(v) + 4 + s.get("dy", 0))}" text-anchor="{ancla}" '
                               f'style="fill:{s["color"]};font-weight:bold">{_c(v)}</text>')
    out.append(f'<text x="{_n(x0 - 38)}" y="{_n(y0 + h / 2)}" text-anchor="middle" '
               f'transform="rotate(-90 {_n(x0 - 38)} {_n(y0 + h / 2)})">{escape(ytitulo)}</text>')
    if xtitulo:
        out.append(f'<text x="{_n(x0 + w / 2)}" y="{_n(y0 + h + 32)}" text-anchor="middle">{escape(xtitulo)}</text>')


def _leyenda(out: list[str], x: float, y: float, series: list[dict]) -> None:
    for i, s in enumerate(series):
        yy = y + 16 * i
        dash = f' stroke-dasharray="{s["trazo"]}"' if s["trazo"] else ""
        out.append(f'<line x1="{_n(x)}" y1="{_n(yy)}" x2="{_n(x + 28)}" y2="{_n(yy)}" stroke="{s["color"]}" stroke-width="2"{dash}/>')
        out.append(f'<text x="{_n(x + 34)}" y="{_n(yy + 4)}">{escape(s["nombre"])}</text>')


def evento_svg(original: list[tuple[int, float]], limpia: list[tuple[int, float]],
               descomp: dict | None = None) -> str:
    """Estudio de eventos: brecha (cercano menos control, en puntos del indice de la misma edad) por mes k.

    `original` es la serie con la base del resultado principal (meses -3 a -1), `limpia` la serie con la base de los
    meses -6 a -4, donde la pretendencia se ve. `descomp`, si viene, es {"total", "dias", "tasa"}: listas de (k, puntos
    logaritmicos) de la descomposicion aditiva, y agrega un segundo panel chico.
    """
    ks = sorted({k for k, _ in original} | {k for k, _ in limpia})
    k1 = dict(original).get(1)
    desc = ("Brecha del petróleo entre los padres a menos de 1 km y los controles de la misma edad, por mes desde la fractura "
            "del pozo hijo, en puntos del índice. La brecha cae en el mes 1" + (f" a {_c(k1)} puntos" if k1 is not None else "")
            + ", ya era negativa antes de la fractura y casi se cierra a los 6 meses. Medida, no causa.")
    alto = 660 if descomp else 400
    out = _abrir(alto, "Brecha de petróleo por mes desde la fractura del hijo", desc,
                 "Padres a menos de 1 km menos controles de la misma edad a 2 a 5 km, en puntos del índice de caudal")
    s1 = [{"nombre": "Base de los meses -3 a -1 (resultado principal)", "color": AZUL, "trazo": "", "puntos": original},
          {"nombre": "Base de los meses -6 a -4 (muestra la pretendencia)", "color": NARANJA, "trazo": "6 4", "puntos": limpia}]
    xtit = "Meses desde la fractura del hijo (k = 0 es el mes de la fractura)"
    if not descomp:
        _panel_lineas(out, 70, 70, 600, 240, ks, s1, "Brecha (puntos)", 1, (-3, -1), xtit)
        _leyenda(out, 70, 354, s1)
        out.append(f'<text class="pie" x="20" y="{alto - 8}">Huella medida, no causa.</text>')
        return _cerrar(out)
    _panel_lineas(out, 70, 70, 600, 200, ks, s1, "Brecha (puntos)", 1, (-3, -1), None)
    _leyenda(out, 70, 306, s1)
    out.append('<text class="titulo" x="20" y="366" style="font-size:13px">Cómo se reparte la brecha del volumen (puntos logarítmicos)</text>')
    s2 = [{"nombre": "Volumen", "color": NEGRO, "trazo": "2 3", "puntos": descomp["total"]},
          {"nombre": "Días producidos", "color": AZUL, "trazo": "", "dy": 9, "puntos": descomp["dias"]},
          {"nombre": "Caudal por día producido", "color": NARANJA, "trazo": "6 4", "dy": -9, "puntos": descomp["tasa"]}]
    _panel_lineas(out, 70, 380, 600, 140, ks, s2, "Brecha (puntos)", 1, None, xtit)
    _leyenda(out, 70, 570, s2)
    out.append(f'<text class="pie" x="20" y="{alto - 8}">Mediana de los eventos en el panel superior; media de logaritmos en el inferior. '
               'Huella medida, no causa.</text>')
    return _cerrar(out)


def distancia_svg(bandas: list[dict]) -> str:
    """Brecha del mes 1 por banda de distancia al hijo mas cercano.

    Cada banda: {"etiqueta", "brecha", "ic_bajo", "ic_alto", "n", "ref"} en puntos; la de `ref` es el anillo de 5 a 10 km
    contra 2 a 5 km (el control de 2 a 5 km no es un cero limpio).
    """
    fila, x0, w, y0 = 34, 250, 400, 76
    h = fila * len(bandas)
    lo, hi, paso = _escala(min(b["ic_bajo"] for b in bandas), max(b["ic_alto"] for b in bandas))
    alto = int(y0 + h + 82)

    def px(v: float) -> float:
        return x0 + (v - lo) / (hi - lo) * w

    ref = next((b for b in bandas if b.get("ref")), None)
    desc = ("Brecha del petróleo al mes 1 por banda de distancia al hijo más cercano, contra el anillo de 5 a 10 km. "
            "La brecha cambia de forma gradual con la distancia y no corta en un punto" +
            (f"; el anillo de 5 a 10 km rinde {_c(ref['brecha'])} puntos más que el control de 2 a 5 km, que no es un cero limpio." if ref else "."))
    out = _abrir(alto, "Brecha del mes 1 por distancia al pozo hijo", desc,
                 "Control: anillo de 5 a 10 km (la última fila compara ese anillo con 2 a 5 km). Intervalo de 95%.")
    for t in _ticks(lo, hi, paso):
        out.append(f'<line class="rejilla" x1="{_n(px(t))}" y1="{_n(y0 - 6)}" x2="{_n(px(t))}" y2="{_n(y0 + h)}"/>')
        out.append(f'<text x="{_n(px(t))}" y="{_n(y0 + h + 16)}" text-anchor="middle">{_c(t, 0)}</text>')
    out.append(f'<line class="cero" x1="{_n(px(0))}" y1="{_n(y0 - 6)}" x2="{_n(px(0))}" y2="{_n(y0 + h)}"/>')
    for i, b in enumerate(bandas):
        yc = y0 + fila * i + fila / 2
        color = NARANJA if b.get("ref") else AZUL
        x_a, x_b = sorted((px(0), px(b["brecha"])))
        out.append(f'<rect x="{_n(x_a)}" y="{_n(yc - 8)}" width="{_n(max(x_b - x_a, 0.5))}" height="16" fill="{color}" fill-opacity="0.85"/>')
        out.append(f'<line x1="{_n(px(b["ic_bajo"]))}" y1="{_n(yc)}" x2="{_n(px(b["ic_alto"]))}" y2="{_n(yc)}" stroke="{NEGRO}" stroke-width="1.5"/>')
        for v in (b["ic_bajo"], b["ic_alto"]):
            out.append(f'<line x1="{_n(px(v))}" y1="{_n(yc - 4)}" x2="{_n(px(v))}" y2="{_n(yc + 4)}" stroke="{NEGRO}" stroke-width="1.5"/>')
        out.append(f'<text x="{_n(x0 - 12)}" y="{_n(yc + 4)}" text-anchor="end">{escape(b["etiqueta"])}</text>')
        out.append(f'<text class="pie" x="20" y="{_n(yc + 4)}">n = {_miles(b["n"])}</text>')
        out.append(f'<text x="{_n(px(b["ic_alto"]) + 6)}" y="{_n(yc + 4)}" style="font-weight:bold">{_c(b["brecha"])}</text>')
    out.append(f'<text x="{_n(x0 + w / 2)}" y="{_n(y0 + h + 36)}" text-anchor="middle">Brecha del petróleo al mes 1 (puntos del índice)</text>')
    out.append(f'<text class="pie" x="20" y="{alto - 22}">Naranja: el anillo contra 2 a 5 km; un valor distinto de cero ahí dice que 2 a 5 km no es un control limpio.</text>')
    out.append(f'<text class="pie" x="20" y="{alto - 8}">Es un gradiente por distancia, no un alcance.</text>')
    return _cerrar(out)


def anio_svg(anios: list[tuple[int, int, float]]) -> str:
    """Brecha del mes 1 por ano de la fractura: (ano, eventos cercanos, puntos). Los anos con menos de 30 eventos van claros."""
    x0, w, y0, h = 70, 610, 80, 250
    lo, hi, paso = _escala(min(v for _, _, v in anios), max(v for _, _, v in anios))
    alto = y0 + h + 90
    pitch = w / len(anios)

    def py(v: float) -> float:
        return y0 + h - (v - lo) / (hi - lo) * h

    ultimo = max(a for a, _, _ in anios)
    v_ult = next(v for a, _, v in anios if a == ultimo)
    desc = ("Brecha del petróleo al mes 1 entre padres a menos de 1 km y controles de la misma edad, por año de la fractura del hijo, "
            f"con el número de eventos de cada año. Llega a {_c(abs(v_ult), 0)} puntos menos en {ultimo}, año en curso. Medida, no causa.")
    out = _abrir(alto, "Brecha del mes 1 por año de la fractura", desc,
                 "Padres a menos de 1 km menos controles de la misma edad, en puntos del índice de caudal")
    for t in _ticks(lo, hi, paso):
        out.append(f'<line class="rejilla" x1="{_n(x0)}" y1="{_n(py(t))}" x2="{_n(x0 + w)}" y2="{_n(py(t))}"/>')
        out.append(f'<text x="{_n(x0 - 6)}" y="{_n(py(t) + 4)}" text-anchor="end">{_c(t, 0)}</text>')
    out.append(f'<line class="cero" x1="{_n(x0)}" y1="{_n(py(0))}" x2="{_n(x0 + w)}" y2="{_n(py(0))}"/>')
    out.append(f'<path class="eje" d="M{_n(x0)},{_n(y0)} L{_n(x0)},{_n(y0 + h)}"/>')
    for i, (a, n, v) in enumerate(anios):
        cx = x0 + pitch * (i + 0.5)
        y_a, y_b = sorted((py(0), py(v)))
        op = "0.35" if n < 30 else "0.9"
        out.append(f'<rect x="{_n(cx - pitch * 0.36)}" y="{_n(y_a)}" width="{_n(pitch * 0.72)}" height="{_n(max(y_b - y_a, 0.5))}" fill="{AZUL}" fill-opacity="{op}"/>')
        ty = y_b + 12 if v < 0 else y_a - 4
        out.append(f'<text x="{_n(cx)}" y="{_n(ty)}" text-anchor="middle" style="font-size:10px">{_c(v, 0)}</text>')
        out.append(f'<text x="{_n(cx)}" y="{_n(y0 + h + 18)}" text-anchor="middle">{a}</text>')
        out.append(f'<text class="pie" x="{_n(cx)}" y="{_n(y0 + h + 32)}" text-anchor="middle">{_miles(n)}</text>')
    out.append(f'<text class="pie" x="{_n(x0 - 6)}" y="{_n(y0 + h + 32)}" text-anchor="end">eventos</text>')
    out.append(f'<text x="{_n(x0 - 44)}" y="{_n(y0 + h / 2)}" text-anchor="middle" '
               f'transform="rotate(-90 {_n(x0 - 44)} {_n(y0 + h / 2)})">Brecha al mes 1 (puntos)</text>')
    out.append(f'<text x="{_n(x0 + w / 2)}" y="{_n(y0 + h + 54)}" text-anchor="middle">Año de la fractura del pozo hijo</text>')
    out.append(f'<text class="pie" x="20" y="{alto - 8}">Claro: menos de 30 eventos en el año. {ultimo} es el año en curso. Huella medida, no causa.</text>')
    return _cerrar(out)


def _panel_recuperado(out: list[str], x0: float, y0: float, lado: float, puntos: list[dict], titulo: str, unidad: str) -> None:
    """Un panel cuadrado de recuperado (eje y: media y p05 a p95) contra plantado (eje x), con la recta de 1 a 1."""
    vals = [v for p in puntos for v in (p["plantado"], p["media"], p["p05"], p["p95"])]
    lo, hi, paso = _escala(min(vals), max(vals))

    def pos(v: float, y: bool = False) -> float:
        f = (v - lo) / (hi - lo)
        return y0 + lado - f * lado if y else x0 + f * lado

    out.append(f'<text style="font-weight:bold" x="{_n(x0)}" y="{_n(y0 - 10)}">{escape(titulo)}</text>')
    for t in _ticks(lo, hi, paso):
        out.append(f'<line class="rejilla" x1="{_n(x0)}" y1="{_n(pos(t, True))}" x2="{_n(x0 + lado)}" y2="{_n(pos(t, True))}"/>')
        out.append(f'<line class="rejilla" x1="{_n(pos(t))}" y1="{_n(y0)}" x2="{_n(pos(t))}" y2="{_n(y0 + lado)}"/>')
        out.append(f'<text x="{_n(x0 - 6)}" y="{_n(pos(t, True) + 4)}" text-anchor="end">{_c(t, 0)}</text>')
        out.append(f'<text x="{_n(pos(t))}" y="{_n(y0 + lado + 14)}" text-anchor="middle">{_c(t, 0)}</text>')
    out.append(f'<path class="eje" d="M{_n(x0)},{_n(y0)} L{_n(x0)},{_n(y0 + lado)} L{_n(x0 + lado)},{_n(y0 + lado)}"/>')
    out.append(f'<line class="marca" x1="{_n(pos(lo))}" y1="{_n(pos(lo, True))}" x2="{_n(pos(hi))}" y2="{_n(pos(hi, True))}"/>')
    for p in puntos:
        x = pos(p["plantado"])
        out.append(f'<line x1="{_n(x)}" y1="{_n(pos(p["p05"], True))}" x2="{_n(x)}" y2="{_n(pos(p["p95"], True))}" '
                   f'stroke="{p["color"]}" stroke-width="2"/>')
        out.append(f'<circle cx="{_n(x)}" cy="{_n(pos(p["media"], True))}" r="4" fill="{p["color"]}"/>')
    out.append(f'<text x="{_n(x0 + lado / 2)}" y="{_n(y0 + lado + 32)}" text-anchor="middle">Plantado ({escape(unidad)})</text>')
    out.append(f'<text x="{_n(x0 - 40)}" y="{_n(y0 + lado / 2)}" text-anchor="middle" '
               f'transform="rotate(-90 {_n(x0 - 40)} {_n(y0 + lado / 2)})">Recuperado ({escape(unidad)})</text>')


COLOR_ESCENARIO = {"S1": AZUL, "S2": NARANJA, "S3": AZUL, "S4": "#009E73", "S5": NEGRO}
ETIQUETA_ESCENARIO = {"S1": "S1 cierre", "S2": "S2 caída de caudal", "S3": "S3 caída dentro del mes", "S4": "S4 brecha previa",
                      "S5": "S5 nulo"}


def inyeccion_svg(celdas: list[dict], mundos: int) -> str:
    """Recuperado contra plantado. Cada celda: {"escenario", "plantado", "media", "p05", "p95", "panel"}, panel "brecha" o "pendiente"."""
    desc = ("Dos paneles con la recta de uno a uno. A la izquierda, la brecha del mes 1 recuperada contra la plantada, en puntos del "
            f"índice, con la media de {mundos} mundos simulados y el rango del 5% al 95%. A la derecha, la pendiente del mes 0 sobre la "
            "fracción del mes. Lo recuperado es la diferencia con el mundo nulo de los mismos sorteos y lo plantado está en puntos del "
            "índice. Los puntos cerca de la recta dicen que el estimador sin cambios recupera lo plantado. Recuperar un "
            "efecto plantado dice algo del método, no de los pozos.")
    out = _abrir(470, "Efectos plantados contra efectos recuperados", desc,
                 "Estimadores sin cambios sobre datos reales con la fecha de fractura corrida un año")
    pa = [dict(c, color=COLOR_ESCENARIO[c["escenario"]]) for c in celdas if c["panel"] == "brecha"]
    pb = [dict(c, color=COLOR_ESCENARIO[c["escenario"]]) for c in celdas if c["panel"] == "pendiente"]
    _panel_recuperado(out, 70, 90, 250, pa, "Brecha del mes 1", "puntos")
    _panel_recuperado(out, 410, 90, 250, pb, "Pendiente del mes 0", "puntos por 0,1 de f0")
    x = 30.0
    for e in [e for e in ("S1", "S2", "S3", "S4", "S5") if any(c["escenario"] == e for c in celdas)]:
        out.append(f'<circle cx="{_n(x)}" cy="414" r="4" fill="{COLOR_ESCENARIO[e]}"/>')
        out.append(f'<text x="{_n(x + 10)}" y="418">{escape(ETIQUETA_ESCENARIO[e])}</text>')
        x += 32 + 6.4 * len(ETIQUETA_ESCENARIO[e])
    out.append('<text class="pie" x="20" y="446">Punto: media de los mundos; barra: del 5% al 95%; recta punteada: recuperado igual a plantado.</text>')
    out.append('<text class="pie" x="20" y="432">Plantado en puntos del índice; recuperado menos el mundo nulo de los mismos sorteos (el nulo mismo no se dibuja).</text>')
    out.append(f'<text class="pie" x="20" y="460">{mundos} mundos por celda. Prueba del método sobre efectos plantados simples, no de los pozos.</text>')
    return _cerrar(out)


# ---- lectura del warehouse y escritura -------------------------------------------------------------------------------

def _etiqueta_banda(banda: str, ref: bool) -> str:
    return f"{banda} km contra 2 a 5 km" if ref else f"{banda} km"


def datos(con) -> dict:
    """Las series de los tres graficos, en puntos, desde los marts."""
    q = "select k, 100 * brecha from mart_descomposicion_k where panel = ? order by k"
    original = [(int(k), float(v)) for k, v in con.execute(q, ["petroleo_base_original"]).fetchall()]
    limpia = [(int(k), float(v)) for k, v in con.execute(q, ["petroleo"]).fetchall()]
    ad = con.execute("select k, 100 * brecha_total, 100 * brecha_dias, 100 * brecha_tasa from mart_descomposicion_aditiva "
                     "where variante = 'con_cerrados' order by k").fetchall()
    descomp = {"total": [(int(r[0]), float(r[1])) for r in ad], "dias": [(int(r[0]), float(r[2])) for r in ad],
               "tasa": [(int(r[0]), float(r[3])) for r in ad]}
    filas = con.execute("select banda, km_desde, km_hasta, control, n_banda, 100 * brecha, 100 * ic_bajo, 100 * ic_alto "
                        "from mart_descomposicion_distancia where base = '-6 a -4' and not (km_desde = 0 and km_hasta = 1) "
                        "order by km_desde").fetchall()
    bandas = []
    for banda, desde, hasta, control, n, b, lo, hi in filas:
        ref = desde == 5
        bandas.append({"etiqueta": _etiqueta_banda(banda, ref), "brecha": float(b), "ic_bajo": float(lo),
                       "ic_alto": float(hi), "n": int(n), "ref": ref})
    anios = [(int(a), int(n), 100 * float(b)) for a, n, b in con.execute(
        "select anio, eventos_cercanos, brecha_mes_1 from mart_interferencia_anual where brecha_mes_1 is not null order by anio").fetchall()]
    return {"original": original, "limpia": limpia, "descomp": descomp, "bandas": bandas, "anios": anios,
            "inyeccion": datos_inyeccion(con)}


def datos_inyeccion(con) -> dict:
    """Celdas de la validacion por inyeccion: lo recuperado menos el mundo nulo contra lo plantado en puntos del indice, de la brecha
    del mes 1 (S1, S2 y S4 con base limpia) y de la pendiente del mes 0 (S3). El nulo (S5) no se dibuja: restado da cero por construccion."""
    q = ("select escenario, tamano, medida, plantado_puntos, recuperado_neto, neto_p05, neto_p95, mundos from mart_inyeccion "
         "where (medida = 'brecha_mes1' and escenario in ('S1', 'S2')) or (medida = 'brecha_mes1_base_limpia' and escenario = 'S4') "
         "or (medida = 'pendiente_mes0' and escenario = 'S3') order by escenario, tamano")
    celdas, mundos = [], 0
    for esc, tam, med, plant, media, p05, p95, n in con.execute(q).fetchall():
        celdas.append({"escenario": esc, "tamano": int(tam), "plantado": float(plant), "media": float(media), "p05": float(p05),
                       "p95": float(p95), "panel": "pendiente" if med == "pendiente_mes0" else "brecha"})
        mundos = int(n)
    return {"celdas": celdas, "mundos": mundos}


def svgs(d: dict) -> dict[str, str]:
    return {ARCHIVOS[0]: evento_svg(d["original"], d["limpia"], d["descomp"]),
            ARCHIVOS[1]: distancia_svg(d["bandas"]),
            ARCHIVOS[2]: anio_svg(d["anios"]),
            ARCHIVOS[3]: inyeccion_svg(d["inyeccion"]["celdas"], d["inyeccion"]["mundos"])}


def escribir(d: dict, carpeta: Path) -> list[Path]:
    """Escribe las cuatro figuras en `carpeta` (UTF-8, saltos de linea \\n) y devuelve las rutas."""
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for nombre, texto in svgs(d).items():
        ruta = carpeta / nombre
        ruta.write_bytes(texto.encode("utf-8"))
        rutas.append(ruta)
    return rutas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(WAREHOUSE))
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)
    con = duckdb.connect(a.db, read_only=True)
    try:
        rutas = escribir(datos(con), Path(a.out))
    finally:
        con.close()
    for r in rutas:
        print(f"escrito {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
