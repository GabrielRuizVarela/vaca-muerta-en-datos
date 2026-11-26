"""La pagina de la espera: site/espera.html, su plantilla y la regla de plata recomputada.

La pagina se arma con pipeline/espera.py (collect + render) sobre pipeline/espera_template.html.
Aqui se comprueban tres cosas: que la plantilla es de la familia (los tokens Estepa, la escala
de tipos, sin cajas ni servidores remotos), que la frase del dinero se recalcula con la misma regla que Python, y
que el html generado sale con los textos de la foto y sin una cifra de dolares que no haya calculado el
navegador.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from pipeline import espera, sistema
from pipeline.ingest import DATA, ROOT
from tests.test_deslop_numeros import visible

SITE = ROOT / "site" / "espera.html"
WAREHOUSE = DATA / "warehouse.duckdb"
NODE = shutil.which("node")
needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")
# La escala de tipos de la familia (la del sistema): nada por debajo de 14 px ni entre dos pasos.
ESCALA = set(sistema.ESCALA)


def _tpl() -> str:
    return espera.TEMPLATE.read_text(encoding="utf-8")


def _tokens(tpl: str) -> str:
    """El bloque marcado de los tokens Estepa, de un comentario al otro (ya no existe: el sistema los trae)."""
    encontrado = re.search(r"/\* estepa:tokens:inicio \*/(.*?)/\* estepa:tokens:fin \*/", tpl, re.S)
    return encontrado.group(1) if encontrado else ""


# ---- render ----

def test_render_escapa_el_cierre_de_script(tmp_path):
    """Un '</script>' en los datos no puede cerrar el bloque de la pagina."""
    out = tmp_path / "espera.html"
    espera.render({"caso": "</script><script>alert(1)</script>"}, out)
    html = out.read_text(encoding="utf-8")
    assert "<\\/script>" in html
    assert "</script><script>alert(1)" not in html
    assert "<title>Barriles que llegan tarde</title>" in html


def test_render_no_pasa_del_presupuesto(tmp_path, monkeypatch):
    """Si la pagina pasa del presupuesto de bytes, el render se corta."""
    monkeypatch.setattr(espera, "MAX_BYTES", 1024)
    with pytest.raises(SystemExit):
        espera.render({"caso": "x" * 4000}, tmp_path / "espera.html")


def test_el_placeholder_de_los_datos_se_reemplaza(tmp_path):
    html = (tmp_path / "espera.html")
    espera.render({"caso": 3}, html)
    texto = html.read_text(encoding="utf-8")
    assert "/*__DATA__*/null" not in texto
    assert '"caso":3' in texto


# ---- la plantilla ----

def test_la_plantilla_usa_el_sistema():
    """Los tokens y el tipo base vienen del sistema: la plantilla no define los suyos."""
    tpl = _tpl()
    assert "/*__SISTEMA__*/" in tpl
    assert ":root {" not in tpl
    assert re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", tpl) == ["#E8A33D"]


def test_es_un_mazo():
    """La pagina es un mazo de seis laminas, con una sola transicion por lamina y sin cifras que cuenten."""
    tpl = _tpl()
    laminas = ("caso", "vecino", "cuenca", "diferidos", "cajon", "despues")
    posiciones = []
    for nombre in laminas:
        marca = f'id="{nombre}"'
        assert marca in tpl, nombre
        posiciones.append(tpl.index(marca))
    assert posiciones == sorted(posiciones)
    assert "prefers-reduced-motion" in tpl
    mazo = re.search(r"// mazo:inicio(.*?)// mazo:fin", tpl, re.S).group(1)
    assert "cuenta" not in mazo
    assert "contador" not in mazo
    assert "requestAnimationFrame" not in mazo


def test_la_plantilla_tiene_un_solo_tema_oscuro():
    """Los tokens oscuros los trae el sistema: en la plantilla solo queda el aviso de redibujar."""
    assert _tpl().count("prefers-color-scheme") <= 1


def test_sin_cajas_ni_pastillas():
    """Nada de eyebrow, pastillas, esquinas redondas, sombras, mayusculas ni letra espaciada."""
    tpl = _tpl()
    for prohibido in ('class="kicker"', 'class="marca', "border-radius", "box-shadow", "text-transform: uppercase",
                      "letter-spacing"):
        assert prohibido not in tpl, prohibido


def test_colores_solo_en_los_tokens():
    """Fuera del bloque de tokens, el unico color es el del pozo nuevo sobre el terreno."""
    tpl = _tpl()
    fuera = tpl.replace(_tokens(tpl), "")
    assert re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", fuera) == ["#E8A33D"]


def test_los_tamanos_de_letra_estan_en_la_escala():
    """Cada tamano, en css o en el lienzo, es un paso de la escala; nada por debajo de 14 px."""
    tpl = _tpl()
    estilo = re.search(r"<style>(.*?)</style>", tpl, re.S).group(1)
    css = [int(v) for v in re.findall(r"font(?:-size)?\s*:[^;{}]*?(\d+)px", estilo)]
    lienzo = [int(v) for v in re.findall(r'font\s*=\s*"(\d+)px', tpl)]
    assert len(css) > 8 and len(lienzo) > 2
    assert set(css) <= ESCALA, sorted(set(css) - ESCALA)
    assert set(lienzo) <= ESCALA, sorted(set(lienzo) - ESCALA)


def test_la_plantilla_no_tiene_servidores_remotos():
    """La pagina es autonoma: la foto va incrustada y no hay ni una fuente ni un host remoto."""
    tpl = _tpl()
    assert "http://" not in tpl
    assert "https://" not in tpl


def test_la_plantilla_no_tiene_rayas():
    """Ni raya corta ni raya larga: el sitio escribe con guion simple."""
    tpl = _tpl()
    assert chr(0x2013) not in tpl
    assert chr(0x2014) not in tpl


def test_la_plantilla_trae_el_bloque_de_la_regla():
    tpl = _tpl()
    assert "// regla:inicio" in tpl and "// regla:fin" in tpl


# ---- la regla de plata, recomputada ----

def _frases_js() -> list[str]:
    """Corre en node el bloque de la regla de la plantilla y trae las 27 frases."""
    tpl = _tpl()
    bloque = re.search(r"// regla:inicio(.*?)// regla:fin", tpl, re.S).group(1)
    guion = (bloque + """
var salida = [];
var precios = [30, 60, 100], tasas = [0, 10, 20], meses = [6, 12, 24];
for (var i = 0; i < precios.length; i++)
  for (var j = 0; j < tasas.length; j++)
    for (var k = 0; k < meses.length; k++)
      salida.push(frase(6374450.54, 11445599.76, precios[i], tasas[j], meses[k]));
console.log(JSON.stringify(salida));
""")
    salida = subprocess.run([NODE, "-"], input=guion, capture_output=True, text=True, check=True).stdout
    return json.loads(salida)


@needs_node
def test_la_frase_del_dinero_es_la_misma_que_en_python():
    """La frase de la pagina no se escribe a mano: sale de la misma regla que el modulo."""
    js = _frases_js()
    esperado = []
    for p in (30, 60, 100):
        for t in (0, 10, 20):
            for m in (6, 12, 24):
                esperado.append(espera.frase(6374450.54, 11445599.76, p, t, m))
    assert len(js) == len(esperado) == 27
    assert js == esperado


# ---- la pagina generada ----

@needs_wh
def test_la_pagina_generada_esta_y_cabe():
    assert SITE.exists(), "correr python -m pipeline.espera"
    assert SITE.stat().st_size <= espera.MAX_BYTES


@needs_wh
def test_la_pagina_generada_trae_los_textos_de_la_foto():
    """Las cifras del relato estan en el html estatico: la pagina se lee sin javascript."""
    texto = " ".join(visible(SITE.read_text(encoding="utf-8")).split())
    assert "Barriles que llegan tarde" in texto
    assert "entre 6,4 y 11,4 millones de barriles" in texto
    assert "-954 barriles" in texto


@needs_wh
def test_la_pagina_sin_javascript_no_tiene_una_cifra_de_dolares():
    """El dinero aparece recien cuando el navegador aplica la regla: el html estatico no lo lleva."""
    texto = " ".join(visible(SITE.read_text(encoding="utf-8")).split())
    assert not re.search(r"USD\s*\d", texto)


def test_otro_caso_sortea_solo_ventanas_completas():
    """Un mes fuera de los datos no se dibuja como caudal cero: "Otro caso" sortea entre los
    casos con la ventana entera en los datos y la chispa corta la linea donde falta un mes."""
    tpl = _tpl()
    manejador = re.search(r'getElementById\("otro"\)\.addEventListener\("click", function \(\) \{(.*?)\}\);', tpl, re.S).group(1)
    assert "SORTEABLES[" in manejador and "D.eventos.length" not in manejador
    assert re.search(r"if \(hayMes\(sm \+ MES_MIN\) && hayMes\(sm \+ MES_MAX\)\) SORTEABLES\.push", tpl)
    assert "if (!hayMes(evMes + k)) { pts.push({ k: k, v: null }); continue; }" in tpl


def test_la_curva_se_dibuja_al_abrir_y_se_imprime_entera():
    """La curva está en un detalle cerrado: se dibuja al abrirlo. Al imprimir no queda texto escondido por el mazo."""
    tpl = _tpl()
    assert 'id="ver-curva"' in tpl and 'addEventListener("toggle"' in tpl
    assert "@media print" in tpl


def test_el_explorador_esta_debajo_del_mazo_con_las_cuatro_clases():
    """El explorador es una seccion comun debajo de la ultima lamina, con las cuatro clases con las palabras del sitio."""
    tpl = _tpl()
    assert 'id="explorador"' in tpl
    assert tpl.index('id="explorador"') > tpl.index('id="despues"')
    assert 'class="lamina" id="explorador"' not in tpl
    for rotulo in ("Subida del corte de agua tras el hijo", "Cierre preventivo", "Ambos", "Sin efecto"):
        assert f"<span>{rotulo}</span>" in tpl, rotulo
    assert "Ver la cuenca en el tiempo" in tpl


def test_el_explorador_no_cuenta_ni_suma():
    """La reproduccion enciende y apaga puntos: nada que sume ni que lleve un total."""
    tpl = _tpl()
    explorador = re.search(r"// explorador:inicio(.*?)// explorador:fin", tpl, re.S).group(1)
    assert "total" not in explorador.lower()
    assert "acumul" not in explorador.lower()


def test_las_teclas_del_mazo_dejan_bajar_al_explorador():
    """Con la ultima lamina activa y el explorador debajo, la flecha abajo desplaza la pagina."""
    tpl = _tpl()
    mazo = re.search(r"// mazo:inicio(.*?)// mazo:fin", tpl, re.S).group(1)
    assert 'document.getElementById("explorador")' in mazo
    assert "if (hayExplorador) return;" in mazo


@pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
def test_la_pagina_generada_trae_la_distancia():
    """El mapa pinta tres bandas de distancia: salen del warehouse y entran en D."""
    html = SITE.read_text(encoding="utf-8")
    datos = json.loads(re.search(r"const D = (\{.*?\});\n", html, re.S).group(1))
    assert len(datos["distancia"]) == 3


def test_los_anillos_solo_se_dibujan_en_el_acercamiento():
    """El mapa de la cuenca no lleva anillos ni bandas: solo el acercamiento los dibuja."""
    tpl = _tpl()
    explorador = re.search(r"// explorador:inicio(.*?)// explorador:fin", tpl, re.S).group(1)
    llamadas = re.findall(r"\bex(Anillos|Bandas)\((\w+)", explorador)
    llamadas = [(f, ctx) for f, ctx in llamadas if ctx not in ("c",)]
    assert sorted(f for f, _ in llamadas) == ["Anillos", "Bandas"]
    assert all(ctx.startswith("exCtxCerca") for _, ctx in llamadas), llamadas


def test_los_botones_del_caso_redibujan_el_explorador():
    # "Otro caso" y "El caso típico" cambian `caso`: el acercamiento y el texto del explorador lo siguen.
    t = _tpl()
    for boton in ("otro", "tipico"):
        i = t.index(f'getElementById("{boton}").addEventListener')
        cuerpo = t[i:t.index("});", i)]
        assert "exRedibuja()" in cuerpo, boton
