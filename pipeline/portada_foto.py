"""Foto de tapa de la portada: el recorte del núcleo Sentinel en dos tonos, con el pozo nuevo marcado.

Uso (Pillow solo hace falta para codificar):
    uv run --with pillow python -m pipeline.portada_foto

Entrada: data/base_foto_nucleo.webp (ver `pipeline.base_foto`, caja NUCLEO). Salida, en site/img/:
    portada_{claro,oscuro}_{alto,ancho}.{avif,webp}
`alto` es el recorte 4:5 del teléfono y `ancho` el 16:10 de pantalla grande. Cada uno se carga solo en su modo y su
ancho, así que la página suma una sola de estas imágenes (menos de 150 kB cada una; la prueba lo controla).

Dos tonos: la luminancia, estirada entre sus percentiles 2 y 98, va de `lutita` (sombra) a `estepa` (luz) en claro y
de `lutita` a `jarilla` en oscuro, con gamma 1,8 (la misma estepa de noche). Los colores salen de `pipeline.sistema`; el único que no es
del sistema es `MARCADOR_POZO_NUEVO`, el punto naranja del pozo hijo del caso de la espera (Loma Campana, fracturado el
2014-05-04, el caso por defecto de `pipeline.espera.elegir_caso`).
"""
from __future__ import annotations

from pathlib import Path

from pipeline import sistema

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "base_foto_nucleo.webp"
SALIDA = RAIZ / "site" / "img"
NUCLEO = (-69.25, -38.85, -68.25, -38.1)  # la caja de base_foto_nucleo.webp, igual que base_foto.json
POZO = (-68.90333, -38.3149)  # lon, lat del pozo hijo (id 147298)
# recorte en píxeles de la imagen de 3072 x 2304: (x0, y0, ancho, alto) y tamaño final
RECORTES = {
    "alto": ((297, 0, 1536, 1920), (880, 1100)),
    "ancho": ((0, 192, 3072, 1920), (1600, 1000)),
}
MODOS = {"claro": ("lutita", "estepa", 0, 1.0), "oscuro": ("lutita", "jarilla", 1, 1.8)}  # el último es la gamma: de noche, menos luz
CALIDAD_AVIF = 48
CALIDAD_WEBP = 62
TOPE_BYTES = 150_000


def _rgb(hexa: str) -> tuple[int, int, int]:
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def pozo_px(ancho: int, alto: int) -> tuple[float, float]:
    """Posición del pozo en la imagen completa del núcleo."""
    lon0, lat0, lon1, lat1 = NUCLEO
    return (POZO[0] - lon0) / (lon1 - lon0) * ancho, (lat1 - POZO[1]) / (lat1 - lat0) * alto


def construir() -> list[Path]:
    from PIL import Image, ImageDraw, ImageOps

    foto = Image.open(ENTRADA).convert("L")
    # estirar entre los percentiles 2 y 98
    hist = foto.histogram()
    total = sum(hist)
    acum, bajo, alto = 0, 0, 255
    for v, n in enumerate(hist):
        acum += n
        if acum <= total * 0.02:
            bajo = v
        if acum <= total * 0.98:
            alto = v
    lut = [max(0, min(255, round((v - bajo) * 255 / max(1, alto - bajo)))) for v in range(256)]
    gris = foto.point(lut)
    px, py = pozo_px(*foto.size)
    escritos = []
    for modo, (sombra, luz, i, gamma) in MODOS.items():
        oscuro, claro = _rgb(sistema.TOKENS[sombra][i]), _rgb(sistema.TOKENS[luz][i])
        tono = gris.point([round(255 * (v / 255) ** gamma) for v in range(256)])
        duo = ImageOps.colorize(tono, black=oscuro, white=claro)
        for nombre, ((x0, y0, w, h), final) in RECORTES.items():
            img = duo.crop((x0, y0, x0 + w, y0 + h)).resize(final, Image.LANCZOS)
            esc = final[0] / w
            cx, cy = (px - x0) * esc, (py - y0) * esc
            d = ImageDraw.Draw(img)
            r = final[0] / 110
            d.ellipse((cx - 2.2 * r, cy - 2.2 * r, cx + 2.2 * r, cy + 2.2 * r), outline=_rgb(sistema.MARCADOR_POZO_NUEVO), width=max(2, round(r / 2.5)))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_rgb(sistema.MARCADOR_POZO_NUEVO))
            for ext, opciones in (("avif", {"quality": CALIDAD_AVIF, "speed": 4}), ("webp", {"quality": CALIDAD_WEBP, "method": 6})):
                ruta = SALIDA / f"portada_{modo}_{nombre}.{ext}"
                img.save(ruta, **opciones)
                assert ruta.stat().st_size < TOPE_BYTES, f"{ruta.name}: {ruta.stat().st_size} bytes"
                escritos.append(ruta)
    return escritos


if __name__ == "__main__":
    for r in construir():
        print(f"{r.relative_to(RAIZ)}: {r.stat().st_size} bytes")
