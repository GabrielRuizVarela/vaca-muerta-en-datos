"""El sistema visual compartido (`pipeline/sistema.py`, v2 "Horizonte"): colores, fuentes, hoja base, marcas y figuras."""
from __future__ import annotations

import re
from pathlib import Path

from pipeline import sistema

RAIZ = Path(__file__).resolve().parent.parent
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def _variables(bloque: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6});", bloque))


def _luminancia(h: str) -> float:
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contraste(a: str, b: str) -> float:
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_los_colores_v2_con_su_version_oscura() -> None:
    assert list(sistema.TOKENS) == ["cielo", "estepa", "lutita", "orilla", "tinta", "hueso", "jarilla"]
    css = sistema.css_tokens()
    claro, resto = css.split("@media", 1)
    oscuro_pref, oscuro_forzado = resto.split(':root[data-theme="dark"]', 1)
    for nombre, (c, o) in sistema.TOKENS.items():
        assert _variables(claro)[nombre] == c
        assert _variables(oscuro_pref)[nombre] == o and _variables(oscuro_forzado)[nombre] == o
    assert "prefers-color-scheme: dark" in css


def test_el_texto_y_la_banda_se_leen_de_dia_y_de_noche() -> None:
    for i in (0, 1):
        t = {k: v[i] for k, v in sistema.TOKENS.items()}
        assert _contraste(t["tinta"], t["cielo"]) >= 4.5 and _contraste(t["tinta"], t["estepa"]) >= 4.5
        assert _contraste(t["hueso"], t["lutita"]) >= 4.5 and _contraste(t["jarilla"], t["cielo"]) >= 4.5
    noche = {k: v[1] for k, v in sistema.TOKENS.items()}
    assert _contraste(noche["lutita"], noche["cielo"]) < 3  # por eso existe la orilla
    assert _contraste(noche["orilla"], noche["cielo"]) >= 3 and _contraste(noche["orilla"], noche["estepa"]) >= 3
    assert sistema.TOKENS["orilla"][0] == sistema.TOKENS["lutita"][0]  # de día no se ve


def test_las_fuentes_estan_en_el_sitio_con_su_licencia_y_no_se_piden_afuera() -> None:
    css = sistema.css_fuentes()
    assert "http" not in css and "//" not in css.replace("/*", "")
    for familia, (ruta, _pesos, _anchos) in sistema.FUENTES.items():
        archivo = RAIZ / "site" / ruta
        assert archivo.stat().st_size > 10_000 and archivo.read_bytes()[:4] == b"wOF2", familia
        licencia = (archivo.parent / "OFL.txt").read_text(encoding="utf-8")
        assert "SIL Open Font License" in licencia and licencia.startswith("Copyright"), familia
        assert f'"{familia}"' in css and ruta in css


def test_la_hoja_base_no_tiene_colores_sueltos_ni_selectores_de_una_pagina() -> None:
    assert not HEX.search(sistema.CSS_BASE), "los colores van por variables"
    for clase in (".marca--pleno", ".marca--medio", ".marca--vacio", ".pie-sitio"):
        assert clase in sistema.CSS_BASE
    for selector in re.findall(r"([^{}]+)\{", sistema.CSS_BASE):
        assert not re.search(r"#[A-Za-z]", selector), selector
    assert sistema.sistema_css().startswith(sistema.css_fuentes())


def test_marcas_y_marcador_del_pozo() -> None:
    assert sistema.MARCAS == {"pleno": "●", "medio": "◐", "vacio": "○"}
    assert HEX.fullmatch(sistema.MARCADOR_POZO_NUEVO)


def test_matplotlib_acepta_el_estilo() -> None:
    import pytest
    matplotlib = pytest.importorskip("matplotlib")  # no es dependencia del proyecto; la usa quien dibuja figuras
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for modo in ("claro", "oscuro"):
        with sistema.contexto_matplotlib(modo):
            assert plt.rcParams["axes.grid"] is False
            assert plt.rcParams["text.color"].lower() == sistema.colores(modo)["tinta"].lower()
