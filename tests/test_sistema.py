"""El sistema visual compartido (`pipeline/sistema.py`, v2 "Horizonte") y su uso en la portada."""
from __future__ import annotations

import re
import struct
from pathlib import Path

from pipeline import report, sistema

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = (RAIZ / "pipeline" / "report_template.html").read_text(encoding="utf-8")
SITIO = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")





def test_estilo_matplotlib_es_un_diccionario_sin_marco_ni_rejilla() -> None:
    for modo in ("claro", "oscuro"):
        e = sistema.estilo_matplotlib(modo)
        assert e["axes.grid"] is False and e["axes.spines.top"] is False and e["axes.spines.right"] is False
        assert e["text.color"] == sistema.TOKENS["tinta"][0 if modo == "claro" else 1]
    assert sistema.colores("oscuro")["s1"] == sistema.SERIES["s1"][1]


def test_la_portada_recibe_el_sistema_y_no_tiene_colores_sueltos() -> None:
    assert "/*__SISTEMA__*/" in PLANTILLA and "/*__SISTEMA__*/" not in SITIO
    for _, oscuro in sistema.TOKENS.values():
        assert oscuro in SITIO
    css = SITIO[SITIO.index("<style>"): SITIO.index("</style>")]
    fuera = re.sub(r":root[^{]*\{[^}]*\}", "", css)
    assert not HEX.search(fuera), HEX.findall(fuera)


def test_la_banda_tiene_orilla_y_no_engorda_al_crecer() -> None:
    """De noche la lutita casi no se separa del cielo (1,1 a 1): la orilla dibuja el borde. La transición escala la
    banda en vertical, así que el trazo no debe escalar con ella."""
    regla = re.search(r"\n\.banda \{([^}]*)\}", PLANTILLA).group(1)
    assert "stroke: var(--orilla)" in regla and "vector-effect: non-scaling-stroke" in regla
    assert sistema.TOKENS["orilla"][1] in SITIO


def test_la_portada_es_una_tapa_seis_laminas_y_un_cierre() -> None:
    arti = SITIO[SITIO.index('<article class="historia"'): SITIO.index("</article>")]
    lista = arti[arti.index('<ol class="seis"'): arti.index("</ol>")]
    destinos = re.findall(r'<a href="#(\w+)">', lista)
    assert destinos == ["vecino", "artefacto", "diferido", "direccion", "anticipar", "fuera"]
    assert re.findall(r'<section class="[^"]*lamina[^"]*" id="(\w+)"', arti) == ["inicio", "creemos", *destinos, "apuesta"]   # la tapa, la respuesta en tres columnas, las seis preguntas y la apuesta abierta
    for d in destinos:
        seccion = re.search(rf'<section class="pregunta lamina" id="{d}"[^>]*>.*?\n  </section>', arti, re.S).group(0)
        assert seccion.count("<h2") == 1 and 'class="primera' in seccion and 'class="prueba"' in seccion
        assert "<summary>Ver los números</summary>" in seccion
        # la prueba completa va adentro de "Ver los números"; la duda, si la hay, al pie de la lámina
        detalle = seccion[seccion.index("<details"): seccion.index("</details>")]
        assert 'class="prueba"' in detalle
        assert 'class="escenario"' in seccion, f"{d}: cada pregunta dibuja su banda en el horizonte"
    assert "<nav" not in SITIO[: SITIO.index('<article class="historia"')]
    assert 'class="pie-sitio"' in SITIO


def test_las_figuras_de_la_portada_estan_y_son_de_ancho_de_telefono() -> None:
    for nombre in ("vecino_brecha", "vecino_reparto"):
        for sufijo in ("", "_oscuro"):
            ruta = RAIZ / "site" / "img" / f"{nombre}{sufijo}.png"
            assert f"img/{nombre}{sufijo}.png" in SITIO
            cabecera = ruta.read_bytes()[:24]
            assert cabecera[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", cabecera[16:24]) == (700, 500)  # 350 por 250 px CSS a 2x


def test_cada_banda_se_dibuja_sin_js_y_tiene_su_alto() -> None:
    """Progresivo: la banda de cada lámina está en el HTML en su estado final; el guion solo la anima."""
    assert "__PERFIL_" not in SITIO
    for alto in re.findall(r'class="[^"]*banda[^"]*" data-alto="([\d.]+)"', SITIO):
        assert 0 < float(alto) <= 52
    for lamina in re.findall(r'<section class="[^"]*lamina[^"]*" id="\w+" data-alto="([\d.]+)"', SITIO):
        assert float(lamina) >= 0
    # una sola transición por cambio y nada en bucle
    assert "setInterval" not in SITIO and "infinite" not in SITIO
    assert "prefers-reduced-motion: reduce" in SITIO


def test_el_perfil_sale_de_la_curva_del_estudio_de_eventos() -> None:
    datos = {"interferencia": {"curva": [
        {"banda": b, "k": k, "indice": v} for k in range(-3, 7)
        for b, v in (("cercano", 0.8 if k == 1 else 1.0), ("control", 1.0))]}}
    area, linea = report.perfil_brecha(datos)
    assert area.startswith(f"M0 {report.PERFIL_ALTO} ") and area.endswith("Z")
    assert f"L44.44 {report.PERFIL_ALTO - 20.0}" in area  # mes 1: 20 puntos de brecha, en x = 4/9
    assert linea.startswith("M0.0 24") and "Z" not in linea


def test_antes_de_la_fractura_la_banda_usa_la_brecha_que_cita_la_lamina() -> None:
    """La lámina dice que antes de la fractura ya había brecha (pretrend); la banda no puede quedar en el suelo."""
    datos = {"interferencia": {
        "curva": [{"banda": b, "k": k, "indice": v} for k in range(-3, 7)
                  for b, v in (("cercano", 1.03 if k < 0 else 0.8), ("control", 1.0))],
        "pretrend": [{"k": -3, "brecha": -0.025}, {"k": -2, "brecha": -0.036}, {"k": -1, "brecha": -0.063},
                     {"k": 1, "brecha": -0.5}]}}
    area, _ = report.perfil_brecha(datos)
    alto = report.PERFIL_ALTO
    assert f"L0.0 {round(alto - 2.5, 2)}" in area and f"L22.22 {round(alto - 6.3, 2)}" in area
    assert f"L44.44 {alto - 20.0}" in area  # después de la fractura sigue la curva, no el pretrend


def test_la_portada_no_pide_fuentes_afuera_y_son_livianas() -> None:
    """Archivos y licencias: tests/test_sistema_modulo.py. Acá, lo que la portada sirve."""
    assert "fonts.googleapis" not in SITIO and "fonts.gstatic" not in SITIO
    peso = sum((RAIZ / "site" / r).stat().st_size for r, _, _ in sistema.FUENTES.values())
    assert peso < 110_000


def test_la_tapa_es_la_foto_en_dos_tonos_y_liviana() -> None:
    for modo in ("claro", "oscuro"):
        for recorte in ("alto", "ancho"):
            for ext in ("avif", "webp"):
                nombre = f"img/portada_{modo}_{recorte}.{ext}"
                assert nombre in SITIO
                assert (RAIZ / "site" / nombre).stat().st_size < 150_000
    assert "Contains modified Copernicus Sentinel data 2025" in SITIO


def test_report_render_llena_el_marcador(tmp_path: Path) -> None:
    datos = __import__("json").loads(re.search(r"const D = (\{.*?\});\nconst css", SITIO, re.S).group(1).replace("<\\/", "</"))
    datos["interferencia"]["resumen"]["diferido_rango"] = tuple(datos["interferencia"]["resumen"]["diferido_rango"])
    report.render(datos, tmp_path / "index.html")
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "/*__SISTEMA__*/" not in html and "__PERFIL_" not in html
