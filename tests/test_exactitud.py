"""Accuracy measurements of the Mundo page: the pure pieces on hand-made inputs, then the product in the repo."""
import base64
import json
import math

import numpy as np
import pytest

from pipeline import base_mapa, exactitud

needs_raw = pytest.mark.skipif(not (base_mapa.RAW / "skadi").exists(), reason="raw base_mapa tiles not present")
needs_page = pytest.mark.skipif(not exactitud.PAGINA.exists(), reason="site/mundo.html not present")


def _pagina_medida() -> dict:
    """The page in the repo, or a skip when it no longer is the one the product measured."""
    datos, e = exactitud.leer_pagina(), exactitud.leer()
    if datos["meta"]["hash_datos"] != e["pagina"]["hash_datos"]:
        pytest.skip("the page has newer data than data/exactitud.json")
    return datos


# ---- relief ----

def test_fuente_en_is_bilinear_on_whole_arc_seconds():
    """The mosaic starts at (-71, -36) with one sample per arc-second, east and south."""
    mosaico = np.fromfunction(lambda f, c: 10 * f + c, (6, 6), dtype=np.int64)
    assert exactitud.fuente_en(mosaico, -71 + 2 / 3600, -36 - 3 / 3600) == pytest.approx(32)
    assert exactitud.fuente_en(mosaico, -71 + 2.5 / 3600, -36 - 1.25 / 3600) == pytest.approx(15)


def test_resumen_summarises_absolute_differences_in_tenths():
    r = exactitud.resumen([-4, 1, 2, 3])
    assert r == {"n": 4, "mediana": 2.5, "p90": 3.7, "p99": 4.0, "max": 4.0}


def test_medir_relieve_on_a_flat_source_finds_no_difference():
    """A sheet of 500 m over a source of 500 m: every wellhead inside agrees, the one outside is not counted."""
    z = np.full((675, 540), 500, dtype=np.int64)
    rel = {"cols": 540, "filas": 675, "min": 500, "max": 500,
           "d": base64.b64encode(base_mapa.codificar_relieve(z)).decode("ascii")}
    datos = {"base": {"caja": list(base_mapa.CAJA), "relieve": rel},
             "pozos": {"lon": [-68.7, -69.0, -60.0], "lat": [-38.3, -38.5, -38.3]}}
    mosaico = np.broadcast_to(np.int32(500), (4 * 3600, 4 * 3600))
    glo90 = {"fecha_consulta": "2026-01-02", "puntos": [[-68.7, -38.3, 497], [-60.0, -38.3, 0]]}
    r = exactitud.medir_relieve(datos, mosaico, glo90)
    assert r["pozos"] == r["solo_hoja"] == {"n": 2, "mediana": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0}
    assert r["pozos_nucleo"] is None
    assert [(c["fuente_m"], c["pagina_m"]) for c in r["cumbres"] + r["niveles"]] == [(500, 500)] * 6
    assert r["independiente"] == {"n": 1, "fecha_consulta": "2026-01-02", "fuente_mediana": 3.0, "fuente_max": 3.0,
                                  "pagina_mediana": 3.0, "pagina_max": 3.0}


# ---- image ----

def _suelo(puntos, dx=0, dy=0):
    """A noisy ground of 200 by 260 pixels with a bright square of 3 by 3 next to each point, moved (dx, dy)."""
    gris = 100 + np.random.default_rng(7).normal(0, 2, (200, 260))
    for x, y in puntos:
        gris[y + dy - 1:y + dy + 2, x + dx - 1:x + dx + 2] += 60
    return gris


PUNTOS = [(40 + 45 * i, 40 + 60 * j) for i in range(5) for j in range(3)]


def test_apilar_peaks_on_the_points_and_measures_a_known_offset():
    a = exactitud.apilar(_suelo(PUNTOS), PUNTOS, 30, 30)
    assert a["n"] == a["claros"] == len(PUNTOS)
    assert int(a["pila"].argmax()) // 41 in (19, 20, 21) and a["pila"][20, 20] > 5
    assert abs(a["este_m"]) < 3 and abs(a["norte_m"]) < 3
    corrido = exactitud.apilar(_suelo(PUNTOS, dx=2, dy=1), PUNTOS, 30, 30)
    assert corrido["este_m"] == pytest.approx(60, abs=6) and corrido["norte_m"] == pytest.approx(-30, abs=6)
    assert corrido["suelto_mediana_m"] == pytest.approx(math.hypot(60, 30), abs=8)


def test_apilar_shows_nothing_away_from_the_points_and_skips_the_border():
    lejos = exactitud.apilar(_suelo(PUNTOS), [(x + 20, y + 25) for x, y in PUNTOS], 30, 30)
    assert lejos["pila"][20, 20] < 1 and lejos["claros"] == 0
    assert exactitud.apilar(_suelo(PUNTOS), [(5, 5), (258, 100)], 30, 30) == {"n": 0}


def test_mejor_corrimiento_finds_the_shift_and_keeps_a_tie_in_place():
    contorno = np.zeros((60, 80), dtype=bool)
    contorno[20:40, 25:55] = True
    assert exactitud.mejor_corrimiento(contorno, contorno) == (1.0, 1.0, 0, 0)
    agua = np.roll(np.roll(contorno, -2, axis=0), 3, axis=1)
    puesto, mejor, dx, dy = exactitud.mejor_corrimiento(contorno, agua)
    assert puesto < 0.8 and (mejor, dx, dy) == (1.0, 3, -2)
    assert exactitud.mejor_corrimiento(contorno, np.zeros_like(contorno))[1:] == (0.0, 0, 0)


# ---- drawing ----

def test_grado_km_matches_the_ellipsoid_at_the_equator_and_the_pole():
    assert exactitud.grado_km(0) == pytest.approx((110.574, 111.320), abs=0.001)
    assert exactitud.grado_km(90)[0] == pytest.approx(111.694, abs=0.001)


def test_deformacion_of_the_flat_drawing():
    """North-south the constant is a little long; east-west it is exact where the cosine is, and drifts away from it."""
    ns, eo = exactitud.deformacion(-38.3, -38.3)
    assert ns == pytest.approx(0.29, abs=0.01) and eo == pytest.approx(-0.13, abs=0.01)
    assert exactitud.deformacion(-38.3, -37.3)[1] < eo < exactitud.deformacion(-38.3, -39.3)[1]


# ---- reading the page ----

def test_leer_pagina_reads_the_embedded_object(tmp_path):
    hoja = tmp_path / "mundo.html"
    hoja.write_text('<html><script id="datos">\nconst DATA = {"meta": {"n": 1}, "t": "á"};\n</script><script>x</script>',
                    encoding="utf-8")
    assert exactitud.leer_pagina(hoja) == {"meta": {"n": 1}, "t": "á"}


# ---- the product in the repo ----

def test_product_is_canonical_and_says_what_it_measured():
    e = exactitud.leer()
    assert exactitud.DESTINO.read_text(encoding="utf-8") == exactitud.serializar(e)
    assert set(e) == {"v", "pagina", "relieve", "imagen", "dibujo"} and e["v"] == 1
    r, im = e["relieve"], e["imagen"]
    assert r["pozos"]["n"] == r["solo_hoja"]["n"] <= e["pagina"]["pozos"] and r["pozos_nucleo"]["n"] < r["pozos"]["n"]
    # each "sheet alone" summary covers the same wells as the one it is compared with
    assert r["solo_hoja_nucleo"]["n"] == r["pozos_nucleo"]["n"]
    assert [c["nombre"] for c in r["cumbres"]] == [n for n, _ in exactitud.CUMBRES]
    assert [c["nombre"] for c in r["niveles"]] == [n for n, _, _ in exactitud.NIVELES]
    assert im["embalses"] == list(exactitud.EMBALSES) and im["busca_px"] == exactitud.BUSCA_PX
    assert im["meses_antes"] == exactitud.MESES_ANTES and len(im["agua_mejor_px"]) == 2


def test_claims_never_exceed_the_measurements():
    """What the wiki page says in words holds in the numbers: the finer relief helps, the wells sit on their locations."""
    e = exactitud.leer()
    r, im = e["relieve"], e["imagen"]
    for k in ("mediana", "p99", "max"):
        # same wells on each side: the page against the sheet grid alone, in the whole sheet and in the core
        assert r["pozos"][k] <= r["solo_hoja"][k] and r["pozos_nucleo"][k] <= r["solo_hoja_nucleo"][k]
        assert r["pozos_nucleo"][k] <= r["pozos"][k]
    assert all(c["pagina_m"] <= c["fuente_m"] for c in r["cumbres"])
    assert im["pico_en_centro"] and im["pico_sd"] > 3 * im["control_sd"]
    assert max(abs(im["este_m"]), abs(im["norte_m"])) < min(im["pixel_m"])
    assert im["agua_mejor_px"] == [0, 0] and im["agua_iou"] == im["agua_mejor_iou"] > 0.9


def test_independent_sample_is_pinned_with_its_source():
    g = json.loads(exactitud.GLO90.read_text(encoding="utf-8"))
    lon0, lat0, lon1, lat1 = base_mapa.CAJA
    assert g["fuente"].startswith("Copernicus DEM GLO-90") and g["atribucion"] and g["fecha_consulta"] == "2026-11-19"
    assert len(g["puntos"]) == 91 and len({(p[0], p[1]) for p in g["puntos"]}) == 91
    assert all(isinstance(p[2], int) and -180 < p[0] < 180 for p in g["puntos"])
    assert sum(lon0 <= p[0] <= lon1 and lat0 <= p[1] <= lat1 for p in g["puntos"]) == exactitud.leer()["relieve"]["independiente"]["n"]


def test_wiki_section_is_the_one_in_the_repo_and_tags_every_line():
    e = base_mapa.leer_exactitud()
    seccion = base_mapa.seccion_exactitud(e)
    texto = base_mapa.PAGINA.read_text(encoding="utf-8")
    assert "\n".join(seccion) in texto and texto.index("## Exactitud") < texto.index("## Qué no es")
    vinetas = [linea for linea in seccion if linea.startswith("- ")]
    assert sum(linea.startswith("- medido, ") for linea in vinetas) == 6
    assert sum(linea.startswith("- supuesto, ") for linea in vinetas) == 2 and len(vinetas) == 8
    # the sheet-alone figures are quoted next to the wells they were measured on
    r = e["relieve"]
    assert (f"en esos mismos pozos, la mediana era de {base_mapa._dec(r['solo_hoja']['mediana'])} m") in vinetas[0]
    assert (f"en esos, con la grilla de la hoja sola eran {base_mapa._dec(r['solo_hoja_nucleo']['mediana'])} m y "
            f"{base_mapa._dec(r['solo_hoja_nucleo']['p99'])} m.") in vinetas[0]
    assert chr(0x2013) not in texto and chr(0x2014) not in texto
    sin = base_mapa.pagina(json.loads(base_mapa.DESTINO.read_text(encoding="utf-8")), None, base_mapa.leer_fino())
    assert "Exactitud" not in sin and "pipeline.exactitud" not in sin


def test_wiki_section_words_follow_the_signs():
    """An offset to the east and north, a short north-south drawing and a better shifted outline change the words."""
    e = json.loads(exactitud.DESTINO.read_text(encoding="utf-8"))
    e["imagen"].update(este_m=4, norte_m=9, pico_en_centro=False, agua_mejor_px=[2, -1], agua_mejor_iou=0.95)
    e["dibujo"].update(ns_pct=-0.5, eo_nucleo_pct=[0.2, -0.3])
    e["relieve"]["independiente"].update(fuente_mediana=-1.5)
    e["relieve"]["pozos_nucleo"] = None
    t = "\n".join(base_mapa.seccion_exactitud(e))
    assert "queda a 4 m al este y 9 m al norte de la posición" in t and "su máximo, de " in t
    assert "; corrido 2 píxeles al este y 1 al norte llega al 95,0 %." in t
    assert "acorta las distancias norte-sur un 0,50 %" in t
    assert "quedan un 0,2 % largas en el borde norte del núcleo y un 0,3 % cortas en el borde sur" in t
    assert "la fuente da 1,5 m menos que el modelo" in t and "donde rige entero" not in t and "hoja sola" not in t
    e["imagen"].update(agua_mejor_px=[-3, 2])
    assert "; corrido 3 píxeles al oeste y 2 al sur llega al" in "\n".join(base_mapa.seccion_exactitud(e))


@needs_raw
@needs_page
def test_relief_half_is_remeasured_from_the_tiles():
    datos = _pagina_medida()
    mosaico, _ = base_mapa.cargar_mosaico()
    glo90 = json.loads(exactitud.GLO90.read_text(encoding="utf-8"))
    assert exactitud.medir_relieve(datos, mosaico, glo90) == exactitud.leer()["relieve"]


@needs_page
def test_drawing_half_is_remeasured_from_the_page():
    assert exactitud.medir_dibujo(_pagina_medida()) == exactitud.leer()["dibujo"]


@needs_page
def test_image_half_is_remeasured_where_pillow_is_installed():
    pytest.importorskip("PIL")
    datos = _pagina_medida()
    rgb, caja = exactitud.abrir_imagen(datos)
    contorno = exactitud.mascara_agua(datos["base"], caja, rgb.shape[1], rgb.shape[0])
    assert exactitud.medir_imagen(datos, rgb, caja, contorno) == exactitud.leer()["imagen"]


def test_main_verificar_never_writes(tmp_path, monkeypatch, capsys):
    destino = tmp_path / "exactitud.json"
    monkeypatch.setattr(exactitud, "DESTINO", destino)
    monkeypatch.setattr(exactitud, "medir", lambda: {"v": 1, "b": [1, 2]})
    assert exactitud.main(["--verificar"]) == 1 and not destino.exists()
    assert exactitud.main([]) == 0 and json.loads(destino.read_text(encoding="utf-8")) == {"v": 1, "b": [1, 2]}
    capsys.readouterr()
    assert exactitud.main(["--verificar"]) == 0 and capsys.readouterr().out == "verificar ok\n"
