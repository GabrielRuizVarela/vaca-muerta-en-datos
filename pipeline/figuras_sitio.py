"""Figuras de la portada en PNG, con el estilo del sistema (`pipeline.sistema`): un panel por imagen, sin marco, sin rejilla
ni leyenda, cada serie con su nombre al final de la línea. Se dibujan para 350 px CSS de ancho a 2x, en claro y en oscuro.

Los números salen de los mismos marts que las figuras SVG de `pipeline.figuras` (`figuras.datos`), así que las dos series
coinciden. Necesita matplotlib, que no es dependencia del proyecto: `uv run --with matplotlib python -m pipeline.figuras_sitio`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from pipeline import figuras, sistema

ROOT = Path(__file__).resolve().parent.parent
SALIDA = ROOT / "site" / "img"
ANCHO_CSS = 350
ALTO_CSS = 250
MODOS = {"claro": "", "oscuro": "_oscuro"}
ARCHIVOS = ("vecino_brecha", "vecino_reparto")


def _coma(v: float, dec: int = 1) -> str:
    return f"{v:.{dec}f}".replace(".", ",")


def _lienzo(plt, modo: str, ks: list[int]):
    c = sistema.colores(modo)
    fig = plt.figure(figsize=(ANCHO_CSS / 96, ALTO_CSS / 96))
    ax = fig.add_axes([0.12, 0.13, 0.62, 0.74])
    ax.set_xlim(min(ks) - 0.5, max(ks) + 0.5)
    ax.spines["bottom"].set_color(c["tinta"])
    ax.spines["bottom"].set_alpha(0.35)
    ax.set_xticks([k for k in ks if k % 3 == 0])
    return fig, ax, c


def _fin(ax, serie, color, texto, dy=0.0, negrita=False, tamano=None):
    """Nombre de la serie a la derecha de su último punto."""
    k, v = sorted(serie)[-1]
    ax.annotate(texto, (k, v), xytext=(7, dy), textcoords="offset points", ha="left", va="center", color=color,
                fontweight="bold" if negrita else "normal", annotation_clip=False, **({"fontsize": tamano} if tamano else {}))


def _marcas_evento(ax, c, ymin, ymax, banda=True):
    ax.axvline(0, color=c["tinta"], alpha=0.35, lw=1.0, zorder=1)
    ax.text(0.35, ymax, "fractura", color=c["jarilla"], ha="left", va="top")
    if banda:
        ax.axvspan(-3.5, -0.5, color=c["s4"], alpha=0.25, lw=0, zorder=0)
        ax.text(-2, ymin, "pretendencia", color=c["jarilla"], ha="center", va="bottom")


def figura_brecha(plt, d: dict, modo: str):
    """Brecha por mes desde la fractura: la base del resultado principal (llena) y la base limpia (la pretendencia)."""
    ks = sorted({k for k, _ in d["original"]} | {k for k, _ in d["limpia"]})
    fig, ax, c = _lienzo(plt, modo, ks)
    vals = [v for _, v in d["original"] + d["limpia"]]
    ymin, ymax = min(vals) - 7, 6
    ax.set_ylim(ymin, ymax)
    _marcas_evento(ax, c, ymin, ymax)
    ax.axhline(0, color=c["tinta"], alpha=0.35, lw=1.0, zorder=1)
    lim = sorted(d["limpia"])
    ori = sorted(d["original"])
    ax.plot(*zip(*lim), color=c["jarilla"], lw=1.5, ls=(0, (5, 3)), zorder=2)
    ax.plot(*zip(*ori), color=c["s1"], lw=2.0, zorder=3)
    k1 = dict(ori).get(1)
    if k1 is not None:
        ax.plot([1], [k1], "o", ms=6, mfc="none", mec=c["s1"], mew=1.5, zorder=4)
        ax.annotate(_coma(k1), (1, k1), xytext=(9, -7), textcoords="offset points", ha="left", va="center", color=c["tinta"], fontweight="bold")
    _fin(ax, ori, c["tinta"], "base -3 a -1", dy=4)
    _fin(ax, lim, c["jarilla"], "base -6 a -4", dy=-8)
    ax.set_yticks([t for t in (0, -10, -20, -30) if ymin <= t <= ymax])
    ax.set_title("puntos", loc="left", fontsize=10.5, color=c["jarilla"], pad=6, x=-0.14)
    return fig


def figura_reparto(plt, d: dict, modo: str):
    """Cómo se reparte la brecha del volumen: días producidos y caudal por día producido."""
    s = d["descomp"]
    ks = sorted({k for k, _ in s["total"]})
    fig, ax, c = _lienzo(plt, modo, ks)
    vals = [v for serie in s.values() for _, v in serie]
    ymin, ymax = min(vals) - 6, 16
    ax.set_ylim(ymin, ymax)
    _marcas_evento(ax, c, ymin, ymax, banda=False)
    ax.axhline(0, color=c["tinta"], alpha=0.35, lw=1.0, zorder=1)
    ax.plot(*zip(*sorted(s["dias"])), color=c["jarilla"], lw=1.5, ls=(0, (5, 3)), zorder=2)
    ax.plot(*zip(*sorted(s["tasa"])), color=c["s1"], lw=2.0, ls=(0, (1, 2.5)), zorder=3)
    ax.plot(*zip(*sorted(s["total"])), color=c["tinta"], lw=2.0, zorder=4)
    etiqueta = {"total": ("volumen", c["tinta"], 0), "dias": ("días", c["jarilla"], 15), "tasa": ("caudal\npor día", c["tinta"], -26)}
    for n, (texto, color, dy) in etiqueta.items():
        _fin(ax, s[n], color, texto, dy=dy)
    ax.set_yticks([t for t in (0, -20, -40, -60) if ymin <= t <= ymax])
    ax.set_title("puntos logarítmicos", loc="left", fontsize=10.5, color=c["jarilla"], pad=6, x=-0.14)
    return fig


def escribir(d: dict, carpeta: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for modo, sufijo in MODOS.items():
        with plt.rc_context(sistema.estilo_matplotlib(modo)):
            for nombre, hacer in zip(ARCHIVOS, (figura_brecha, figura_reparto)):
                fig = hacer(plt, d, modo)
                ruta = carpeta / f"{nombre}{sufijo}.png"
                fig.savefig(ruta, metadata={"Software": None})
                plt.close(fig)
                rutas.append(ruta)
    return rutas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(figuras.WAREHOUSE))
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)
    con = duckdb.connect(a.db, read_only=True)
    try:
        d = figuras.datos(con)
    finally:
        con.close()
    for r in escribir(d, Path(a.out)):
        print(f"escrito {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
