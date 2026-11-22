"""Mapa de ejes de interferencia por area contra el SHmax publicado.

Funcion pura de texto: arma un SVG a mano a partir de `mart_anisotropia_area` y `int_pozo_ubicacion`.
Determinista (areas ordenadas, formato numerico fijo, sin fechas) y sin dependencias nuevas.
Texto en espanol, sin rayas largas.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape, quoteattr

from pipeline import sistema

SHMAX_PUBLICADO = 67.5  # grados desde el norte, en sentido horario (RAGA 2024)
KM_POR_GRADO = 111.2
ANCHO, ALTO = 760, 760
MAPA = (40.0, 50.0, 720.0, 570.0)  # x0, y0, x1, y1 del recuadro del mapa
MARGEN = 95.0  # entre el recuadro y los centroides extremos (cabe el segmento y la etiqueta)
LARGO_MIN, LARGO_MAX = 28.0, 80.0  # largo del segmento en px, proporcional al contraste
LARGO_REF = 64.0
REF_CONTRASTE = 1.0  # contraste que corresponde a LARGO_MAX
FUENTE_ETIQUETA = 11.0
ANCHO_CARACTER = 6.6  # px por caracter de la etiqueta (estimado, mayusculas)

SQL_AREAS = """
select a.area, a.n, a.eje_grados, a.ic_bajo, a.ic_alto, a.contraste, a.p_perm, a.usa_en_costo,
       w.lon_m, w.lat_m
from mart_anisotropia_area a
join (select upper(trim(area)) as clave, avg(lon) as lon_m, avg(lat) as lat_m
      from int_pozo_ubicacion where lon is not null and lat is not null group by 1) w
  on upper(trim(a.area)) = w.clave
where a.area <> 'Cuenca'
order by upper(trim(a.area))
"""
SQL_CUENCA = "select n, eje_grados, ic_bajo, ic_alto, p_perm, usa_en_costo from mart_anisotropia_area where area = 'Cuenca'"

ESTILO = sistema.css_tokens() + f"""
:root {{ --fondo: var(--cielo); --texto: var(--tinta); --suave: var(--jarilla); --linea: var(--jarilla);
        --eje: var(--tinta); --ref: var(--s3); --cono: var(--s1); }}
.fondo {{ fill: var(--fondo); }}
.marco {{ fill: none; stroke: var(--linea); stroke-width: 1; }}
text {{ fill: var(--texto); font-family: {sistema.ARCHIVO}; font-size: 11px; }}
.titulo {{ font-size: 15px; font-weight: 600; }}
.nota {{ fill: var(--suave); }}
.eje-def {{ stroke: var(--eje); stroke-width: 3; fill: none; }}
.eje-ndef {{ stroke: var(--suave); stroke-width: 2; stroke-dasharray: 6 4; fill: none; }}
.centro-def {{ fill: var(--eje); }}
.centro-ndef {{ fill: var(--fondo); stroke: var(--suave); stroke-width: 1.5; }}
.ref {{ stroke: var(--ref); stroke-width: 1.2; fill: none; }}
.cono {{ fill: var(--cono); fill-opacity: 0.22; stroke: var(--cono); stroke-opacity: 0.6; stroke-width: 0.8; }}
.punta-def {{ fill: var(--eje); }}
.punta-ndef {{ fill: var(--suave); }}
.etiqueta {{ font-size: 11px; }}
.norte {{ stroke: var(--texto); stroke-width: 1.5; fill: var(--texto); }}
.escala {{ stroke: var(--texto); stroke-width: 2; fill: none; }}
"""


def _n(x: float) -> str:
    """Numero con formato fijo (un decimal, punto) y sin menos cero."""
    s = f"{x:.1f}"
    return "0.0" if s == "-0.0" else s


def _c(x: float, dec: int = 1) -> str:
    """Numero para texto en espanol: coma decimal."""
    return f"{x:.{dec}f}".replace(".", ",")


def ancho_circular(bajo: float, alto: float) -> float:
    """Apertura en grados del intervalo de ejes (modulo 180) que va de `bajo` a `alto` en sentido horario.

    Si alto < bajo el intervalo cruza el norte. El resultado queda en [0, 180)."""
    return (alto - bajo) % 180.0


def _vec(rumbo: float) -> tuple[float, float]:
    """Vector unitario en pantalla (y hacia abajo) para un rumbo en grados desde el norte, horario."""
    r = math.radians(rumbo)
    return math.sin(r), -math.cos(r)


def _punto(cx: float, cy: float, rumbo: float, radio: float) -> tuple[float, float]:
    ux, uy = _vec(rumbo)
    return cx + radio * ux, cy + radio * uy


def _sector(cx: float, cy: float, bajo: float, alto: float, radio: float) -> str:
    """Camino SVG de un sector que va de `bajo` a `alto` en sentido horario (apertura < 180)."""
    x1, y1 = _punto(cx, cy, bajo, radio)
    x2, y2 = _punto(cx, cy, alto, radio)
    return f"M{_n(cx)},{_n(cy)} L{_n(x1)},{_n(y1)} A{_n(radio)},{_n(radio)} 0 0 1 {_n(x2)},{_n(y2)} Z"


def _largo(contraste: float) -> float:
    return max(LARGO_MIN, min(LARGO_MAX, LARGO_MAX * contraste / REF_CONTRASTE))


def _proyectar(areas: list[dict]) -> tuple[list[tuple[float, float]], float]:
    """Centroides a pixeles (equirectangular, x por cos de la latitud media). Devuelve puntos y px por grado."""
    lat_m = sum(a["lat_m"] for a in areas) / len(areas)
    k = math.cos(math.radians(lat_m))
    xs = [a["lon_m"] * k for a in areas]
    ys = [-a["lat_m"] for a in areas]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    x_ini, y_ini, x_fin, y_fin = MAPA
    disp_x, disp_y = (x_fin - x_ini) - 2 * MARGEN, (y_fin - y_ini) - 2 * MARGEN
    cand = []
    if x1 - x0 > 1e-9:
        cand.append(disp_x / (x1 - x0))
    if y1 - y0 > 1e-9:
        cand.append(disp_y / (y1 - y0))
    s = min(cand) if cand else 800.0
    ox = x_ini + (x_fin - x_ini) / 2 - s * (x0 + x1) / 2
    oy = y_ini + (y_fin - y_ini) / 2 - s * (y0 + y1) / 2
    return [(ox + s * x, oy + s * y) for x, y in zip(xs, ys)], s


def _se_cruzan(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _etiquetas(puntos, radios, nombres) -> list[tuple[float, float, str]]:
    """Ubica cada etiqueta con desplazamientos candidatos, en orden, sin cruzar marcadores ni etiquetas ya puestas."""
    x_ini, y_ini, x_fin, y_fin = MAPA
    marcas = [(px - r, py - r, px + r, py + r) for (px, py), r in zip(puntos, radios)]
    puestas: list[tuple[float, float, float, float]] = []
    out = []
    for (px, py), r, nombre in zip(puntos, radios, nombres):
        w, h = ANCHO_CARACTER * len(nombre), FUENTE_ETIQUETA + 2
        d = r - 4
        cands = [(d, h / 2, "start"), (-d, h / 2, "end"), (-w / 2, -d - 2, "start"), (-w / 2, d + h, "start"),
                 (d, -d, "start"), (-d, -d, "end"), (d, d + h, "start"), (-d, d + h, "end")]
        elegido = None
        for dx, dy, anc in cands:
            x = px + dx - (w if anc == "end" else 0)
            caja = (x, py + dy - h, x + w, py + dy)
            if caja[0] < x_ini or caja[2] > x_fin or caja[1] < y_ini or caja[3] > y_fin:
                continue
            if any(_se_cruzan(caja, o) for o in puestas) or any(_se_cruzan(caja, m) for m in marcas):
                continue
            elegido = (caja, px + dx, py + dy, anc)
            break
        if elegido is None:
            dx, dy, anc = cands[0]
            x = px + dx
            elegido = ((x, py + dy - h, x + w, py + dy), px + dx, py + dy, anc)
        puestas.append(elegido[0])
        out.append((elegido[1], elegido[2], elegido[3]))
    return out


def _flecha_norte(x: float, y: float) -> list[str]:
    return ['<g id="norte" aria-label="Norte">',
            f'<path class="norte" d="M{_n(x)},{_n(y - 30)} L{_n(x - 7)},{_n(y)} L{_n(x)},{_n(y - 7)} L{_n(x + 7)},{_n(y)} Z"/>',
            f'<text x="{_n(x)}" y="{_n(y + 15)}" text-anchor="middle" class="etiqueta">N</text>',
            "</g>"]


def mapa_areas_svg(con) -> str:
    """SVG del mapa de ejes por area. `con` es una conexion DuckDB con el mart de anisotropia y las ubicaciones."""
    cur = con.execute(SQL_AREAS)
    cols = [d[0] for d in cur.description]
    areas = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur = con.execute(SQL_CUENCA)
    cols = [d[0] for d in cur.description]
    cu = next((dict(zip(cols, r)) for r in cur.fetchall()), None)

    x_ini, y_ini, x_fin, y_fin = MAPA
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" width="{ANCHO}" height="{ALTO}" '
           'role="img" aria-labelledby="t d">',
           "<title id=\"t\">Mapa de ejes de interferencia por área contra el SHmax publicado</title>",
           f'<desc id="d">Por cada área con pozos ubicados, el eje de máxima merma estimado de la interferencia '
           f'(grados desde el norte) frente al SHmax publicado de {_c(SHMAX_PUBLICADO)} grados. Trazo continuo: '
           'eje definido; trazo gris punteado: eje no definido. El cono azul es el intervalo de confianza de 95% y solo '
           'se dibuja si el eje está definido. El eje no es una medición de esfuerzos.</desc>',
           "<style>" + ESTILO + "</style>",
           "<defs>",
           '<marker id="punta-def" class="punta-def" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" class="punta-def"/></marker>',
           '<marker id="punta-ndef" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" '
           'orient="auto-start-reverse"><path d="M1,1 L9,5 L1,9" class="eje-ndef" style="stroke-dasharray:none;stroke-width:1.5"/></marker>',
           "</defs>",
           f'<rect class="fondo" x="0" y="0" width="{ANCHO}" height="{ALTO}"/>',
           '<text class="titulo" x="40" y="30">Eje de máxima merma por área contra el SHmax publicado</text>',
           f'<rect class="marco" x="{_n(x_ini)}" y="{_n(y_ini)}" width="{_n(x_fin - x_ini)}" height="{_n(y_fin - y_ini)}"/>']

    if areas:
        puntos, esc = _proyectar(areas)
        largos = [_largo(a["contraste"]) for a in areas]
        radios = [max(l, LARGO_REF) / 2 + 2 for l in largos]
        pos_et = _etiquetas(puntos, radios, [a["area"].strip().upper() for a in areas])
        out.append('<g id="areas">')
        for a, (px, py), largo, (ex, ey, anc) in zip(areas, puntos, largos, pos_et):
            nombre = a["area"].strip().upper()
            definido = bool(a["usa_en_costo"])
            eje = float(a["eje_grados"]) % 180.0
            info = (f'{nombre}: eje {_c(eje)} grados, IC 95% de {_c(a["ic_bajo"])} a {_c(a["ic_alto"])}, '
                    f'contraste {_c(a["contraste"] * 100)} puntos, p de permutación {_c(a["p_perm"], 3)}, '
                    f'{"eje definido" if definido else "eje no definido"}')
            out.append(f'<g class="area" data-area={quoteattr(nombre)} data-definido="{"si" if definido else "no"}">')
            out.append(f"<title>{escape(info)}</title>")
            if definido:
                span = ancho_circular(a["ic_bajo"], a["ic_alto"])
                r = max(largo, LARGO_REF) / 2 - 4
                for lado in (0.0, 180.0):
                    out.append(f'<path class="cono" data-apertura="{_n(span)}" d="{_sector(px, py, a["ic_bajo"] + lado, a["ic_bajo"] + lado + span, r)}"/>')
            rx1, ry1 = _punto(px, py, SHMAX_PUBLICADO, LARGO_REF / 2)
            rx2, ry2 = _punto(px, py, SHMAX_PUBLICADO + 180.0, LARGO_REF / 2)
            out.append(f'<line class="ref" x1="{_n(rx1)}" y1="{_n(ry1)}" x2="{_n(rx2)}" y2="{_n(ry2)}"/>')
            ax1, ay1 = _punto(px, py, eje, largo / 2)
            ax2, ay2 = _punto(px, py, eje + 180.0, largo / 2)
            clase, marca = ("eje-def", "punta-def") if definido else ("eje-ndef", "punta-ndef")
            out.append(f'<line class="{clase}" x1="{_n(ax1)}" y1="{_n(ay1)}" x2="{_n(ax2)}" y2="{_n(ay2)}" '
                       f'marker-start="url(#{marca})" marker-end="url(#{marca})"/>')
            out.append(f'<circle class="{"centro-def" if definido else "centro-ndef"}" cx="{_n(px)}" cy="{_n(py)}" r="3"/>')
            out.append(f'<text class="etiqueta" x="{_n(ex)}" y="{_n(ey)}" text-anchor="{anc}">{escape(nombre)}</text>')
            out.append("</g>")
        out.append("</g>")
        km_px = esc / KM_POR_GRADO  # px por km
        barra = 20.0 * km_px
        bx, by = x_fin - 30 - barra, y_fin - 24
        out += ['<g id="escala" aria-label="Escala de 20 kilómetros">',
                f'<path class="escala" d="M{_n(bx)},{_n(by - 5)} L{_n(bx)},{_n(by)} L{_n(bx + barra)},{_n(by)} L{_n(bx + barra)},{_n(by - 5)}"/>',
                f'<text x="{_n(bx + barra / 2)}" y="{_n(by - 9)}" text-anchor="middle" class="etiqueta">20 km</text>',
                "</g>"]
    else:
        out.append(f'<text class="nota" x="{_n(x_ini + 20)}" y="{_n(y_ini + 30)}">Sin áreas con pozos ubicados.</text>')
    out += _flecha_norte(x_fin - 30, y_ini + 50)

    # leyenda
    ly = y_fin + 28
    out.append('<g id="leyenda">')
    out.append(f'<line class="eje-def" x1="50" y1="{_n(ly)}" x2="100" y2="{_n(ly)}" marker-start="url(#punta-def)" marker-end="url(#punta-def)"/>')
    out.append(f'<text x="110" y="{_n(ly + 4)}">Eje definido (p de permutación menor que 0,10 e IC menor que 90 grados)</text>')
    ly += 26
    out.append(f'<line class="eje-ndef" x1="50" y1="{_n(ly)}" x2="100" y2="{_n(ly)}" marker-start="url(#punta-ndef)" marker-end="url(#punta-ndef)"/>')
    out.append(f'<text x="110" y="{_n(ly + 4)}">Eje no definido (gris, punteado, sin cono)</text>')
    ly += 26
    out.append(f'<line class="ref" x1="50" y1="{_n(ly)}" x2="100" y2="{_n(ly)}"/>')
    out.append(f'<text x="110" y="{_n(ly + 4)}">SHmax publicado, {_c(SHMAX_PUBLICADO)} grados (RAGA 2024)</text>')
    ly += 26
    out.append(f'<path class="cono" d="{_sector(75.0, ly + 6, -20.0, 20.0, 22.0)}"/>')
    out.append(f'<text x="110" y="{_n(ly + 4)}">IC 95% del eje (solo si está definido)</text>')
    out.append(f'<text class="nota" x="380" y="{_n(ly - 52)}">Largo del segmento proporcional al contraste</text>')
    out.append(f'<text class="nota" x="380" y="{_n(ly - 36)}">(mínimo y máximo acotados).</text>')
    if cu:
        ancho = ancho_circular(cu["ic_bajo"], cu["ic_alto"])
        out.append(f'<text class="nota" x="380" y="{_n(ly - 12)}">Cuenca (no se dibuja): eje {_c(cu["eje_grados"] % 180.0)} grados,</text>')
        out.append(f'<text class="nota" x="380" y="{_n(ly + 4)}">IC de {_c(cu["ic_bajo"])} a {_c(cu["ic_alto"])} (apertura {_c(ancho)}),</text>')
        out.append(f'<text class="nota" x="380" y="{_n(ly + 20)}">{"eje definido" if cu["usa_en_costo"] else "eje no definido"}, n = {int(cu["n"])}.</text>')
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"
