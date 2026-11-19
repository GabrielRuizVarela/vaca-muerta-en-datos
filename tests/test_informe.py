"""Pruebas de pipeline.informe sin warehouse: datos sintéticos y la página versionada."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from pipeline import informe
from pipeline.decision import valor_indicativo
from pipeline.ingest import ROOT

DASHES = re.compile("[\u2013\u2014]")


def _rob(eje: str, salida: str, k: int, b: float) -> dict:
    return {"eje": eje, "salida": salida, "k": k, "n": 100, "brecha": b, "ic_bajo": b - 0.05, "ic_alto": b + 0.05}


@pytest.fixture
def d() -> dict:
    return {
        "mes_dato": "2026-09", "verificado": "2026-11-15",
        "curva": {b: [[k, 1.0 - 0.01 * max(k, 0)] for k in range(-3, 7)] for b in ("cercano", "intermedio", "control")},
        "todos": {"eventos": 2077, "pads_hijo": 380, "brecha1": -0.229, "brecha6": -0.021, "ic1_bajo": -0.287, "ic1_alto": -0.168,
                  "dif_m3": 820.9, "dif_bajo_m3": 504.6, "dif_alto_m3": 1105.3},
        "edad": [{"grupo": g, "etiqueta": e, "eventos": 400, "brecha1": b1, "brecha6": b6}
                 for (g, e), b1, b6 in zip(informe.EDADES, (-0.146, -0.209, -0.220, -0.242), (0.006, -0.008, 0.026, -0.059))],
        "distancia": [{"banda": b, "n": 300, "brecha": x, "ic_bajo": x - 0.05, "ic_alto": x + 0.05, "cercana": i < 3}
                      for i, (b, x) in enumerate((("0 a 0,3", -0.280), ("0,3 a 0,6", -0.319), ("0,6 a 1", -0.288),
                                                  ("1 a 2", -0.106), ("2 a 5", -0.028)))],
        "cierre": [{"variante": "V0", "control": "2 a 5 km", "brecha1": -0.229, "brecha6": -0.021, "parte": 0.909},
                   {"variante": "V3", "control": "2 a 5 km, limpio a 2 km", "brecha1": -0.239, "brecha6": -0.047, "parte": 0.804}],
        "robustez": [_rob("operador", informe.COMPLETA, 1, -0.229), _rob("operador", "A", 1, -0.221),
                     _rob("operador", "B", 1, -0.240), _rob("operador", "A", 6, -0.010), _rob("operador", "B", 6, -0.030),
                     _rob("area", informe.COMPLETA, 1, -0.229), _rob("area", "X", 1, -0.200),
                     _rob("area", "Y", 1, -0.29253), _rob("area", "X", 6, -0.036), _rob("area", "Y", 6, -0.015)],
        "cota_m3": 212.6, "cota_bbl": 1337.1, "media24_bbl": -2830.5, "media24_bajo_bbl": -6502.8, "media24_alto_bbl": 1337.1,
        "mde": 0.323, "padres_mediana": 3, "padres_distintos": 1108, "bbl_m3": 6.2898,
        "ejemplo": {"precio": 60.0, "tasa": 0.10, "rezago": 12, "padres": 3},
    }


def test_textos_formatea_en_espanol_y_toma_extremos(d):
    t = informe.textos(d)
    assert t["gap1"] == "-22,9" and t["gap6"] == "-2,1" and t["eventos"] == "2.077"
    assert (t["gap1_ic_bajo"], t["gap1_ic_alto"]) == ("-28,7", "-16,8")
    assert t["edad_menos"] == "-14,6" and t["edad_mas"] == "-24,2"
    assert (t["op_min"], t["op_max"]) == ("-22,1", "-24,0")
    assert (t["ar_min"], t["ar_max"]) == ("-20,0", "-29,3")
    assert (t["seis_min"], t["seis_max"]) == ("-1,0", "-3,6")
    assert t["cierre_peor"] == "-4,7" and t["dif_alto_m3"] == "1.105" and t["mde"] == "0,32"


def test_calculadora_arranca_con_la_formula_de_decision(d):
    t = informe.textos(d)
    v = valor_indicativo(d["todos"]["dif_m3"], 60.0, 0.10, 12)["costo_de_diferir"]
    assert t["ej_costo"] == informe.num(3 * v)
    techo = valor_indicativo(d["cota_m3"], 60.0, 0.10, 12)["valor_cota_perdida"]
    assert t["ej_cota"] == informe.num(3 * techo)


def test_frase_de_padres_viejos_sigue_al_dato(d):
    assert "es el único grupo de edad fuera de los 5 puntos" in informe.textos(d)["frase_viejos"]
    d2 = copy.deepcopy(d)
    d2["edad"][3]["brecha6"] = -0.02
    assert "todos los grupos de edad quedan dentro" in informe.textos(d2)["frase_viejos"]
    d2["edad"][0]["brecha6"] = 0.07
    d2["edad"][3]["brecha6"] = -0.08
    assert informe.textos(d2)["frase_viejos"].startswith("2 grupos de edad")


def test_render_reemplaza_todo_y_embebe_los_datos(d):
    html = informe.render(d)
    assert html.startswith("<!doctype html>") and "<title>" in html.split("<body>")[0]
    assert "{{" not in html and "__DATOS__" not in html and not DASHES.search(html)
    datos = json.loads(re.search(r'<script id="datos" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert datos["todos"]["eventos"] == 2077
    frag = informe.render(d, documento=False)
    assert "<!doctype" not in frag and "<body>" not in frag and frag.startswith("<title>")


def test_la_ficha_del_mes_1_lleva_su_intervalo_y_el_pie_dice_de_cuando_es_el_dato(d):
    html = informe.render(d)
    assert "contra el control (IC 95% por bloques de 5 km: -28,7 a -16,8)." in html
    assert "hasta 2026-09 (copia verificada contra la fuente el 2026-11-15). La página se regenera con" in html
    d["verificado"] = None                                             # sin manifiesto la página no inventa una fecha
    assert "hasta 2026-09. La página se regenera con" in informe.render(d)


def test_fecha_verificada_es_la_mas_vieja_de_las_fuentes_y_falta_si_falta_una():
    a, b = informe.SOURCES
    m = {a: {"loaded_at": "2026-11-10T03:00:00+00:00", "checked_at": "2026-11-15T03:54:28+00:00"},
         b: {"loaded_at": "2026-11-14T03:00:00+00:00"}}                # sin checked_at vale el día en que se bajó
    assert informe.fecha_verificada(m) == "2026-11-14"
    m[b]["checked_at"] = "2026-11-16T01:00:00+00:00"
    assert informe.fecha_verificada(m) == "2026-11-15"
    assert informe.fecha_verificada({a: m[a]}) is None and informe.fecha_verificada(None) is None


def test_la_pagina_solo_pide_a_la_red_sus_tipografias(d):
    recurso = re.compile(r'<(?:link|script|img|iframe|source|video|audio)\b[^>]*?(?:src|href)="(?:https?:)?//([^/"]+)')
    for html in (informe.render(d), (ROOT / "site" / "informe.html").read_text(encoding="utf-8")):
        assert set(recurso.findall(html)) == {"fonts.googleapis.com", "fonts.gstatic.com"}
        assert "url(http" not in html and "@import" not in html and "fetch(" not in html
    assert "<script src=" not in informe.TEMPLATE.read_text(encoding="utf-8")


def test_render_falla_si_queda_un_marcador(d, monkeypatch, tmp_path):
    plantilla = tmp_path / "t.html"
    plantilla.write_text("<title>x</title>\n<!--FIN_HEAD-->\n<p>{{no_existe}}</p>", encoding="utf-8")
    monkeypatch.setattr(informe, "TEMPLATE", plantilla)
    with pytest.raises(ValueError):
        informe.render(d)


def test_pagina_versionada_esta_completa_y_sin_guiones_largos():
    html = (ROOT / "site" / "informe.html").read_text(encoding="utf-8")
    assert "{{" not in html and not DASHES.search(html)
    datos = json.loads(re.search(r'<script id="datos" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert {"curva", "todos", "edad", "distancia", "cierre", "robustez"} <= set(datos)
    assert "No es una recomendación de operación" in html
    assert Path(informe.TEMPLATE).exists()
