import csv
from pathlib import Path

import duckdb
import pytest

from pipeline import checks
from pipeline.build import build
from pipeline.ingest import ROOT, store

PROD_COLS = ["idempresa", "anio", "mes", "idpozo", "prod_pet", "prod_gas", "prod_agua", "tef", "tipopozo",
             "tipoestado", "rectificado", "empresa", "sigla", "formacion", "areapermisoconcesion",
             "areayacimiento", "provincia", "coordenadax", "coordenaday", "sub_tipo_recurso", "tipoextraccion"]
FRAC_COLS = ["id_base_fractura_adjiv", "idpozo", "formacion_productiva", "subtipo_reservorio",
             "longitud_rama_horizontal_m", "cantidad_fracturas", "tipo_terminacion",
             "arena_bombeada_nacional_tn", "arena_bombeada_importada_tn", "agua_inyectada_m3",
             "fecha_inicio_fractura", "fecha_fin_fractura", "empresa_informante", "presion_maxima_psi"]


def prod_row(pozo, anio, mes, pet, empresa="YPF S.A.", tef=30, gas=0, lon="-69", lat="-38", agua=0,
             estado="Extracción Efectiva", extraccion="Surgencia Natural"):
    return {"idempresa": "X", "anio": anio, "mes": mes, "idpozo": pozo, "prod_pet": pet, "prod_gas": gas,
            "prod_agua": agua, "tef": tef, "tipopozo": "Petrolífero", "tipoestado": estado,
            "rectificado": "f", "empresa": empresa, "sigla": f"P-{pozo}", "formacion": "vaca muerta",
            "areapermisoconcesion": "A", "areayacimiento": "Y", "provincia": "Neuquén",
            "coordenadax": lon, "coordenaday": lat, "sub_tipo_recurso": "SHALE", "tipoextraccion": extraccion}


def frac_row(fid, pozo, inicio, rama=2500, empresa="YPF S.A."):
    return {"id_base_fractura_adjiv": fid, "idpozo": pozo, "formacion_productiva": "vaca muerta",
            "subtipo_reservorio": "SHALE", "longitud_rama_horizontal_m": rama, "cantidad_fracturas": 40,
            "tipo_terminacion": "Plug & Perf", "arena_bombeada_nacional_tn": 8000,
            "arena_bombeada_importada_tn": 0, "agua_inyectada_m3": 50000,
            "fecha_inicio_fractura": inicio, "fecha_fin_fractura": inicio, "empresa_informante": empresa,
            "presion_maxima_psi": 9000}


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


def test_interference_nets_out_control_decline(warehouse):
    # Parent A sits 90 m from child C; parent B is 3 km away (control). C is fracked in March 2024.
    # A loses half its rate for two months; B does not. Both started in January 2023 (same age bucket).
    months = [(y, m) for y in (2023, 2024) for m in range(1, 13)]
    rows = []
    for y, m in months:
        dip = (y, m) in ((2024, 3), (2024, 4))
        rows.append(prod_row(1, y, m, 150 if dip else 300, lon="-69.000", lat="-38.000"))
        rows.append(prod_row(2, y, m, 300, lon="-69.000", lat="-38.027"))
        if (y, m) >= (2024, 4):
            rows.append(prod_row(3, y, m, 500, lon="-69.001", lat="-38.000"))
    con = warehouse(rows, [frac_row(1, 3, "2024-03-10")])
    bands = dict(con.execute("select padre, banda from int_interferencia_evento").fetchall())
    assert bands == {1: "cercano", 2: "control"}
    base = (300 / 31 + 300 / 31 + 300 / 29) / 3  # Dec 2023, Jan and Feb 2024 (leap year)
    assert one(con, "select brecha from mart_interferencia_brecha where k = 0") == pytest.approx(-150 / 31 / base)
    assert one(con, "select brecha from mart_interferencia_brecha where k = 3") == pytest.approx(0)
    # Two months at 150 m3 below the control-implied volume.
    assert one(con, "select petroleo_diferido_bbl from mart_interferencia_diferida") == pytest.approx(300 * 6.2898)


def test_parent_water_jump_after_child_frac_is_golpe(warehouse):
    rows = []
    for y, m in [(2023, mm) for mm in range(1, 13)] + [(2024, mm) for mm in range(1, 7)]:
        jump = (y, m) >= (2024, 3)
        rows.append(prod_row(1, y, m, 300 if not jump else 200, agua=30 if not jump else 200,
                             lon="-69.000", lat="-38.000"))
        if (y, m) >= (2024, 3):
            rows.append(prod_row(2, y, m, 500, lon="-69.003", lat="-38.000"))
    con = warehouse(rows, [frac_row(1, 2, "2024-03-10")])
    assert one(con, "select clase from int_interferencia_clase where padre = 1") in ("golpe", "ambos")
    assert one(con, "select count(*) from fct_evento where pozo_id = 1 and tipo = 'salto_agua'") >= 1
    assert one(con, "select count(*) from fct_evento where tipo = 'fractura'") == 1


def test_pads_cluster_within_50_m(warehouse):
    rows = [prod_row(1, 2024, 1, 100, lon="-69.0000", lat="-38.0000"),
            prod_row(2, 2024, 1, 100, lon="-69.0002", lat="-38.0000"),   # about 17 m away
            prod_row(3, 2024, 1, 100, lon="-69.0057", lat="-38.0000")]   # about 500 m away
    con = warehouse(rows, [])
    pad = dict(con.execute("select pozo_id, pad_id from int_pozo_ubicacion").fetchall())
    assert pad[1] == pad[2] == "p1"
    assert pad[3] == "p3"


def test_lift_change_yields_one_event(warehouse):
    rows = [prod_row(1, 2024, m, 100, extraccion="Surgencia Natural" if m < 3 else "Bombeo Mecánico")
            for m in range(1, 6)]
    con = warehouse(rows, [])
    assert one(con, "select count(*) from fct_evento where tipo = 'cambio_extraccion'") == 1
    assert one(con, "select detalle from fct_evento where tipo = 'cambio_extraccion'") == \
        "Surgencia Natural -> Bombeo Mecánico"


def test_replay_builds_arrays_pozos_by_meses(warehouse, tmp_path):
    import base64
    import json
    import re
    from array import array

    from pipeline import replay

    prod = []
    for pozo in (1, 2, 3):
        for mes in range(1, 13):
            prod.append(prod_row(pozo, 2024, mes, 100 + pozo, lon=f"-69.{pozo}"))
    prod += [prod_row(p, 2024, m, 50) for p in range(4, 14) for m in range(1, 13)]
    con = warehouse(prod, [frac_row("f1", 1, "2024-03-10")])
    data = replay.collect(con)

    n, m = data["meta"]["n_pozos"], len(data["meta"]["meses"])
    assert n == len(data["pozos"]) and n >= 3 and m >= 12
    caudal = array("H"); caudal.frombytes(base64.b64decode(data["caudal"]))
    agua = base64.b64decode(data["agua"]); estado = base64.b64decode(data["estado"])
    assert len(caudal) == n * m and len(agua) == n * m and len(estado) == n * m
    row = next(i for i, p in enumerate(data["pozos"]) if p["id"] == 1)
    assert caudal[row * m + data["meta"]["meses"].index("2024-03")] == round(101 / 31 * 6.2898)
    assert any(e["t"] == "frac" and e["f"] == "2024-03-10" and e["p"] == row for e in data["eventos"])
    assert [len(k) for k in data["cuenca"]["kbbl"]] == [m] * len(data["cuenca"]["ops"])

    out = tmp_path / "replay.html"
    assert replay.render(data, out) < replay.MAX_BYTES
    html = out.read_text()
    assert "/*__DATA__*/" not in html
    assert json.loads(re.search(r"const DATA = (\{.*?\});\n\(\(\) =>", html, re.S).group(1))["meta"]["n_pozos"] == n
