"""Las cuatro figuras del caso de estudio: XML valido con titulo y descripcion, bytes deterministas, y el texto del caso.

Los datos son sinteticos: ninguna prueba depende del warehouse (las cifras del caso las verifica pipeline.claims).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline import figuras

ROOT = Path(__file__).resolve().parent.parent
CASO = ROOT / "docs" / "caso-interferencia.md"
RAYAS = chr(0x2014) + chr(0x2013)
SVG = "{http://www.w3.org/2000/svg}"

KS = list(range(-6, 13))
ORIGINAL = [(k, -22.9 if k == 1 else (-17.0 if k == 0 else (-3.0 if k < 0 else -2.0))) for k in KS]
LIMPIA = [(k, v - 2.5) for k, v in ORIGINAL]
DESCOMP = {"total": [(k, v * 3) for k, v in ORIGINAL], "dias": [(k, v * 1.5) for k, v in ORIGINAL],
           "tasa": [(k, v * 1.5) for k, v in ORIGINAL]}
BANDAS = [{"etiqueta": "0 a 0,3 km", "brecha": -28.0, "ic_bajo": -36.9, "ic_alto": -21.6, "n": 332, "ref": False},
          {"etiqueta": "2 a 5 km", "brecha": -2.8, "ic_bajo": -4.5, "ic_alto": -1.1, "n": 14253, "ref": False},
          {"etiqueta": "5 a 10 km contra 2 a 5 km", "brecha": 2.8, "ic_bajo": 1.1, "ic_alto": 4.5, "n": 25786, "ref": True}]
ANIOS = [(2012, 9, -34.5), (2015, 201, 7.5), (2025, 372, -32.4), (2026, 243, -44.5)]
INYECCION = {"mundos": 50, "celdas": [
    {"escenario": "S1", "tamano": 100, "plantado": -50.0, "media": -52.0, "p05": -58.0, "p95": -46.0, "panel": "brecha"},
    {"escenario": "S2", "tamano": 20, "plantado": -20.0, "media": -18.5, "p05": -24.0, "p95": -13.0, "panel": "brecha"},
    {"escenario": "S5", "tamano": 0, "plantado": 0.0, "media": -1.0, "p05": -6.0, "p95": 4.0, "panel": "brecha"},
    {"escenario": "S3", "tamano": 40, "plantado": -4.0, "media": -3.2, "p05": -5.0, "p95": -1.5, "panel": "pendiente"}]}
DATOS = {"original": ORIGINAL, "limpia": LIMPIA, "descomp": DESCOMP, "bandas": BANDAS, "anios": ANIOS, "inyeccion": INYECCION}


def _escritores() -> list:
    return [lambda: figuras.evento_svg(ORIGINAL, LIMPIA, DESCOMP),
            lambda: figuras.evento_svg(ORIGINAL, LIMPIA),
            lambda: figuras.distancia_svg(BANDAS),
            lambda: figuras.anio_svg(ANIOS),
            lambda: figuras.inyeccion_svg(INYECCION["celdas"], INYECCION["mundos"])]


def test_cada_figura_es_xml_con_titulo_y_descripcion():
    for escribir in _escritores():
        texto = escribir()
        raiz = ET.fromstring(texto)
        assert raiz.tag == SVG + "svg"
        titulo, desc = raiz.find(SVG + "title"), raiz.find(SVG + "desc")
        assert titulo is not None and titulo.text and titulo.text.strip()
        assert desc is not None and desc.text and len(desc.text.split()) >= 8
        assert not any(c in texto for c in RAYAS)
        assert "http" not in texto.replace("http://www.w3.org/2000/svg", "")  # sin fuentes ni recursos externos


def test_las_figuras_son_deterministas():
    for escribir in _escritores():
        assert escribir() == escribir()


def test_escribir_dos_veces_da_los_mismos_bytes(tmp_path):
    rutas = figuras.escribir(DATOS, tmp_path / "a")
    assert [r.name for r in rutas] == list(figuras.ARCHIVOS)
    primera = [r.read_bytes() for r in rutas]
    segunda = [r.read_bytes() for r in figuras.escribir(DATOS, tmp_path / "a")]
    otra = [r.read_bytes() for r in figuras.escribir(DATOS, tmp_path / "b")]
    assert primera == segunda == otra


def test_el_mes_1_queda_marcado_y_los_numeros_van_con_coma():
    texto = figuras.evento_svg(ORIGINAL, LIMPIA)
    assert "-22,9" in texto and "-25,4" in texto
    assert "-0.0" not in texto


def _cuerpo(texto: str) -> str:
    """El cuerpo del caso: sin el titulo ni el abstract en ingles, sin tablas ni lineas de figura."""
    resto = texto.split("\n## ", 1)[1]
    lineas = [ln for ln in resto.splitlines() if not ln.lstrip().startswith(("|", "!["))]
    return "\n".join(lineas)


def test_el_caso_no_tiene_rayas_largas_ni_pasa_el_limite_de_palabras():
    texto = CASO.read_text(encoding="utf-8")
    assert not any(c in texto for c in RAYAS)
    palabras = re.findall(r"\S+", _cuerpo(texto))
    assert len(palabras) <= 1500, len(palabras)
    assert texto.startswith("# Interferencia entre pozos en Vaca Muerta con datos públicos\n")
    resumen = [ln for ln in texto.splitlines() if ln.startswith(">")]
    assert len(resumen) == 5


def test_el_caso_enlaza_las_cuatro_imagenes_y_existen():
    texto = CASO.read_text(encoding="utf-8")
    enlaces = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", texto)
    assert sorted(enlaces) == sorted(f"img/{n}" for n in figuras.ARCHIVOS)
    for e in enlaces:
        assert (CASO.parent / e).is_file(), e
