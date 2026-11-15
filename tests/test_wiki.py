import csv
import json
from pathlib import Path

import duckdb
import pytest

from pipeline.build import build
from pipeline.ingest import ROOT
from pipeline.wiki import build_wiki, pad_slug

PROD_COLS = ["idempresa", "anio", "mes", "idpozo", "prod_pet", "prod_gas", "prod_agua", "tef", "tipopozo",
             "tipoestado", "rectificado", "empresa", "sigla", "formacion", "areapermisoconcesion",
             "areayacimiento", "provincia", "coordenadax", "coordenaday", "sub_tipo_recurso"]
FRAC_COLS = ["id_base_fractura_adjiv", "idpozo", "formacion_productiva", "subtipo_reservorio",
             "longitud_rama_horizontal_m", "cantidad_fracturas", "tipo_terminacion",
             "arena_bombeada_nacional_tn", "arena_bombeada_importada_tn", "agua_inyectada_m3",
             "fecha_inicio_fractura", "fecha_fin_fractura", "empresa_informante"]


def prod_row(pozo, anio, mes, pet, empresa="YPF S.A.", tef=30, gas=0, lon="-69", lat="-38"):
    return {"idempresa": "X", "anio": anio, "mes": mes, "idpozo": pozo, "prod_pet": pet, "prod_gas": gas,
            "prod_agua": 0, "tef": tef, "tipopozo": "Petrolífero", "tipoestado": "Extracción Efectiva",
            "rectificado": "f", "empresa": empresa, "sigla": f"P-{pozo}", "formacion": "vaca muerta",
            "areapermisoconcesion": "A", "areayacimiento": "Y", "provincia": "Neuquén",
            "coordenadax": lon, "coordenaday": lat, "sub_tipo_recurso": "SHALE"}


def frac_row(fid, pozo, inicio, rama=2500, empresa="YPF S.A."):
    return {"id_base_fractura_adjiv": fid, "idpozo": pozo, "formacion_productiva": "vaca muerta",
            "subtipo_reservorio": "SHALE", "longitud_rama_horizontal_m": rama, "cantidad_fracturas": 40,
            "tipo_terminacion": "Plug & Perf", "arena_bombeada_nacional_tn": 8000,
            "arena_bombeada_importada_tn": 0, "agua_inyectada_m3": 50000,
            "fecha_inicio_fractura": inicio, "fecha_fin_fractura": inicio, "empresa_informante": empresa}


def write_csv(path: Path, cols, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture
def warehouse(tmp_path):
    def _build(prod_rows, frac_rows):
        con = duckdb.connect()
        build(con, {
            "produccion_no_convencional": write_csv(tmp_path / "p.csv", PROD_COLS, prod_rows),
            "fractura_adjunto_iv": write_csv(tmp_path / "f.csv", FRAC_COLS, frac_rows),
            "seed_operadores": ROOT / "seeds" / "operadores.csv",
        })
        return con
    return _build


@pytest.fixture
def escenario(warehouse):
    """Mismo escenario que test_interference_nets_out_control_decline.

    Pozo 1 (padre) a 90 m del pozo 3 (hijo) y pozo 2 a 3 km (control).
    El pozo 1 pierde la mitad de su tasa dos meses; el control no.
    """
    months = [(y, m) for y in (2023, 2024) for m in range(1, 13)]
    rows = []
    for y, m in months:
        dip = (y, m) in ((2024, 3), (2024, 4))
        rows.append(prod_row(1, y, m, 150 if dip else 300, lon="-69.000", lat="-38.000"))
        rows.append(prod_row(2, y, m, 300, lon="-69.000", lat="-38.027"))
        if (y, m) >= (2024, 4):
            rows.append(prod_row(3, y, m, 500, lon="-69.001", lat="-38.000"))
    con = warehouse(rows, [frac_row(1, 3, "2024-03-10")])
    return con


def manifest(sha="a" * 64, loaded="2026-11-01T00:00:00+00:00"):
    return {
        "produccion_no_convencional": {"sha256": sha, "loaded_at": loaded},
        "fractura_adjunto_iv": {"sha256": "b" * 64, "loaded_at": loaded},
    }


def historial(out_dir):
    text = (Path(out_dir) / "hallazgos" / "interferencia.md").read_text(encoding="utf-8")
    return [l for l in text.splitlines() if l.startswith("- datos a ")]


def test_pad_page_and_interference_edge(escenario, tmp_path):
    out = tmp_path / "wiki"
    stats = build_wiki(escenario, manifest(), out)

    pad_id = escenario.execute(
        "select pad_id from int_pozo_ubicacion where pozo_id = 1").fetchall()[0][0]
    pad_page = out / "pad" / f"{pad_slug(pad_id)}.md"
    assert pad_page.exists()
    assert "P-1" in pad_page.read_text(encoding="utf-8")

    grafo = json.loads((out / "grafo.json").read_text(encoding="utf-8"))
    edges = [a for a in grafo["aristas"]
             if a["tipo"] == "interfiere" and a["origen"] == "pozo:3" and a["destino"] == "pozo:1"]
    assert len(edges) == 1
    assert edges[0]["petroleo_diferido_bbl"] == round(300 * 6.2898)
    assert edges[0]["mes"] == "2024-03"
    km_min = escenario.execute(
        "select km_min from mart_interferencia_diferida where padre = 1").fetchall()[0][0]
    assert edges[0]["km"] == pytest.approx(round(km_min, 3))

    ids = {n["id"] for n in grafo["nodos"]}
    # solo entran los pozos del mart de diferidos: padre 1 e hijo 3, no el control 2
    assert "pozo:1" in ids and "pozo:3" in ids
    assert "pozo:2" not in ids
    assert "pad:" + pad_slug(pad_id) in ids
    assert stats["paginas"] == len(list(out.rglob("*.md")))
    assert stats["nodos"] == len(grafo["nodos"])
    assert stats["aristas"] == len(grafo["aristas"])


def test_historial_is_not_duplicated_with_the_same_sha(escenario, tmp_path):
    out = tmp_path / "wiki"
    build_wiki(escenario, manifest(), out)
    lineas = historial(out)
    assert len(lineas) == 1
    assert "sha produccion aaaaaaaaaaaa" in lineas[0]

    build_wiki(escenario, manifest(), out)
    lineas = historial(out)
    assert len(lineas) == 1

    build_wiki(escenario, manifest("c" * 64), out)
    lineas = historial(out)
    assert len(lineas) == 2
    assert "sha produccion cccccccccccc" in lineas[1]
    assert lineas[0] == lineas[0]  # la linea vieja sigue primero


def test_generated_pages_have_no_unicode_dashes(escenario, tmp_path):
    out = tmp_path / "wiki"
    build_wiki(escenario, manifest(), out)
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.suffix in (".md", ".json"):
            texto = path.read_text(encoding="utf-8")
            assert "\u2014" not in texto, path
            assert "\u2013" not in texto, path
