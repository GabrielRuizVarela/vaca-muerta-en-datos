import csv
from pathlib import Path

import duckdb
import pytest

from pipeline import checks
from pipeline.build import build
from pipeline.ingest import ROOT, store

PROD_COLS = ["idempresa", "anio", "mes", "idpozo", "prod_pet", "prod_gas", "prod_agua", "tef", "tipopozo",
             "tipoestado", "rectificado", "empresa", "sigla", "formacion", "areapermisoconcesion",
             "areayacimiento", "provincia", "coordenadax", "coordenaday", "sub_tipo_recurso"]
FRAC_COLS = ["id_base_fractura_adjiv", "idpozo", "formacion_productiva", "subtipo_reservorio",
             "longitud_rama_horizontal_m", "cantidad_fracturas", "tipo_terminacion",
             "arena_bombeada_nacional_tn", "arena_bombeada_importada_tn", "agua_inyectada_m3",
             "fecha_inicio_fractura", "fecha_fin_fractura", "empresa_informante"]


def prod_row(pozo, anio, mes, pet, empresa="YPF S.A.", tef=30, gas=0):
    return {"idempresa": "X", "anio": anio, "mes": mes, "idpozo": pozo, "prod_pet": pet, "prod_gas": gas,
            "prod_agua": 0, "tef": tef, "tipopozo": "Petrolífero", "tipoestado": "Extracción Efectiva",
            "rectificado": "f", "empresa": empresa, "sigla": f"P-{pozo}", "formacion": "vaca muerta",
            "areapermisoconcesion": "A", "areayacimiento": "Y", "provincia": "Neuquén",
            "coordenadax": "-69", "coordenaday": "-38", "sub_tipo_recurso": "SHALE"}


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


def one(con, sql):
    return con.execute(sql).fetchall()[0][0]


def test_operator_name_variants_collapse(warehouse):
    con = warehouse([prod_row(1, 2024, 1, 100, "VISTA ENERGY ARGENTINA SAU"),
                     prod_row(2, 2024, 1, 100, "Vista Oil & Gas Argentina SA"),
                     prod_row(3, 2024, 1, 100, "PAN AMERICAN ENERGY (SUCURSAL ARGENTINA) LLC")], [])
    assert one(con, "select count(distinct operador) from fct_produccion where operador = 'Vista'") == 1
    assert one(con, "select count(*) from fct_produccion where operador = 'Vista'") == 2
    assert one(con, "select operador from fct_produccion where pozo_id = 3") == "Pan American Energy"


def test_month_on_production_starts_at_first_oil(warehouse):
    # Month 1 is the first month with oil, not the first reported month.
    con = warehouse([prod_row(1, 2024, 1, 0), prod_row(1, 2024, 2, 300), prod_row(1, 2024, 4, 200)], [])
    mops = con.execute("select mop from int_pozo_mop order by mop").fetchall()
    assert [m[0] for m in mops] == [1, 3]
    rate = one(con, "select petroleo_bbl_d from int_pozo_mop where mop = 1")
    assert rate == pytest.approx(300 * 6.2898 / 29)  # February 2024 has 29 days


def test_negative_source_volumes_are_clipped_and_reported(warehouse):
    con = warehouse([prod_row(1, 2024, 1, -5)], [])
    assert one(con, "select petroleo_m3 from fct_produccion") == 0
    report = {c["nombre"]: c for c in checks.run(con)["checks"]}
    assert report["Volúmenes negativos en el origen"]["filas"] == 1
    assert report["Volúmenes negativos en fct_produccion"]["ok"]


def test_duplicate_grain_fails_the_build(warehouse):
    con = warehouse([prod_row(1, 2024, 1, 100), prod_row(1, 2024, 1, 120)], [])
    report = checks.run(con)
    assert report["bloqueantes_fallidos"] == 1


def test_future_frac_jobs_are_excluded_and_reported(warehouse):
    con = warehouse([prod_row(1, 2024, 1, 100), prod_row(2, 2024, 1, 100)],
                    [frac_row(10, 1, "2023-11-01"), frac_row(11, 2, "2999-01-01"),
                     frac_row(12, 1, "2023-12-01", rama=0)])
    assert one(con, "select count(*) from dim_fractura_pozo") == 1
    assert one(con, "select trabajos from dim_fractura_pozo where pozo_id = 1") == 2
    assert one(con, "select rama_horizontal_m from dim_fractura_pozo where pozo_id = 1") == 2500
    report = {c["nombre"]: c for c in checks.run(con)["checks"]}
    assert report["Fracturas con fecha futura"]["filas"] == 1
    assert report["Fracturas sin longitud de rama horizontal"]["filas"] == 1


def test_build_is_idempotent(warehouse):
    rows = [prod_row(1, 2024, m, 100 * m) for m in range(1, 13)]
    con = warehouse(rows, [frac_row(1, 1, "2023-12-01")])
    first = con.execute("select * from mart_pozo_12m").fetchall()
    con2 = warehouse(rows, [frac_row(1, 1, "2023-12-01")])
    assert con2.execute("select * from mart_pozo_12m").fetchall() == first
    assert first[0][3] == pytest.approx(sum(100 * m for m in range(1, 13)) * 6.2898)


def test_ingest_store_skips_unchanged_bytes(tmp_path):
    raw = tmp_path / "raw"
    manifest = {}
    meta = {"url": "u", "loaded_at": "2026-11-15T00:00:00+00:00"}
    (tmp_path / "a").write_text("x")
    assert store("ds", tmp_path / "a", "abc123", meta, manifest, raw) is True
    (tmp_path / "b").write_text("x")
    assert store("ds", tmp_path / "b", "abc123", {**meta, "loaded_at": "2026-11-16T00:00:00+00:00"}, manifest, raw) is False
    assert len(list((raw / "ds").iterdir())) == 1
    assert manifest["ds"]["checked_at"].startswith("2026-11-16")
    (tmp_path / "c").write_text("y")
    assert store("ds", tmp_path / "c", "def456", meta, manifest, raw) is True
    assert len(list((raw / "ds").iterdir())) == 2


def test_fetch_skips_conditional_get_without_local_copy(tmp_path, monkeypatch):
    import io
    from pipeline import ingest

    sent = {}

    class Resp(io.BytesIO):
        headers = {"ETag": '"v2"', "Last-Modified": "x"}

    def fake_urlopen(req, timeout):
        sent.update(req.headers)
        return Resp(b"a,b\n1,2\n")

    monkeypatch.setattr(ingest, "DATA", tmp_path)
    monkeypatch.setattr(ingest.urllib.request, "urlopen", fake_urlopen)
    manifest = {"ds": {"etag": '"v1"', "path": "ds/missing.csv", "sha256": "old"}}
    assert ingest.fetch("ds", "http://example.invalid", manifest, tmp_path / "raw") == "stored"
    assert "If-none-match" not in sent
    assert (tmp_path / "raw" / manifest["ds"]["path"]).read_text() == "a,b\n1,2\n"
