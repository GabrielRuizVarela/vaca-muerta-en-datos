"""Data contract and invariants of pipeline/replay.py and the generated site/replay.html."""
import base64
import json
import re
import sys
from array import array

import duckdb
import pytest

from pipeline import replay
from pipeline.ingest import DATA, ROOT

WAREHOUSE = DATA / "warehouse.duckdb"
SITE = ROOT / "site" / "replay.html"
CLASES = {"golpe", "cierre_preventivo", "ambos", "sin_efecto"}
# The page is self-contained: no remote hosts at all (system font stack, works offline).
ALLOWED_REMOTE: set[str] = set()

needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def payloads():
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return replay.collect(con), replay.collect(con)
    finally:
        con.close()


@pytest.fixture(scope="module")
def data(payloads):
    return payloads[0]


def decode(s, typecode):
    a = array(typecode)
    a.frombytes(base64.b64decode(s, validate=True))
    if sys.byteorder == "big" and a.itemsize > 1:
        a.byteswap()
    return a


# ---- pure helpers (no warehouse) ----

def test_b64_roundtrip_uint16_little_endian():
    a = array("H", [0, 1, 258, 65535])
    raw = base64.b64decode(replay.b64(a))
    assert raw == bytes([0, 0, 1, 0, 2, 1, 255, 255])


def test_b64_uint8():
    assert base64.b64decode(replay.b64(array("B", [0, 7, 255]))) == bytes([0, 7, 255])


def test_axis_bearing_is_axis_not_direction():
    assert replay.axis_bearing(0, 0, 0, 1) == 0  # north
    assert replay.axis_bearing(0, 0, 1, 0) == 90  # east
    assert replay.axis_bearing(0, 0, 0, -1) == 0  # south is the same axis as north
    assert replay.axis_bearing(0, 0, -1, 0) == 90
    for lon, lat in ((1, 1), (-1, 1), (1, -1), (-3, 0.5), (0.2, -4)):
        assert 0 <= replay.axis_bearing(0, 0, lon, lat) < 180


def test_render_escapes_script_breakers_and_keeps_template(tmp_path):
    out = tmp_path / "x" / "r.html"
    size = replay.render({"s": "</script><!-- x"}, out)
    html = out.read_text()
    assert size == out.stat().st_size
    assert "/*__DATA__*/null" not in html
    assert "</script><!--" not in html.split("const DATA = ", 1)[1].split(";\n", 1)[0]
    m = re.search(r"const DATA = (.*?);\n", html, re.S)
    assert json.loads(m.group(1))["s"] == "</script><!-- x"


def test_render_enforces_size_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "MAX_BYTES", 10)
    with pytest.raises(SystemExit):
        replay.render({"a": 1}, tmp_path / "r.html")


# ---- payload contract (real warehouse) ----

@needs_wh
def test_top_level_keys_and_types(data):
    assert set(data) == {"meta", "pozos", "caudal", "agua", "estado", "eventos", "cuenca", "curva"}
    assert isinstance(data["pozos"], list) and isinstance(data["eventos"], list)
    for k in ("caudal", "agua", "estado"):
        assert isinstance(data[k], str)
    assert set(data["meta"]) >= {"meses", "n_pozos", "hash_datos", "mes_datos", "generado", "ops"}


@needs_wh
def test_meses_contiguous_sorted_and_end_at_mes_datos(data):
    meses = data["meta"]["meses"]
    assert meses and all(re.fullmatch(r"\d{4}-\d{2}", m) for m in meses)
    idx = [int(m[:4]) * 12 + int(m[5:]) - 1 for m in meses]
    assert idx == list(range(idx[0], idx[0] + len(idx)))
    assert meses[-1] == data["meta"]["mes_datos"]


@needs_wh
def test_n_pozos_and_pozo_fields(data):
    pozos = data["pozos"]
    assert data["meta"]["n_pozos"] == len(pozos) > 0
    nm = len(data["meta"]["meses"])
    ops = set(data["meta"]["ops"])
    ids = [p["id"] for p in pozos]
    assert len(set(ids)) == len(ids)
    for p in pozos:
        assert set(p) >= {"id", "op", "area", "pad", "lon", "lat", "mes0", "frac"}
        assert isinstance(p["pad"], str) and re.fullmatch(r"p\d+", p["pad"]), p["pad"]
        assert p["op"] in ops
        assert -80 < p["lon"] < -60 and -45 < p["lat"] < -30  # Neuquen basin
        assert isinstance(p["mes0"], int) and 0 <= p["mes0"] <= nm
        assert p["frac"] is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["frac"])


@needs_wh
def test_matrices_decode_to_pozos_by_meses(data):
    n, nm = data["meta"]["n_pozos"], len(data["meta"]["meses"])
    assert len(decode(data["caudal"], "H")) == n * nm
    assert len(decode(data["agua"], "B")) == n * nm
    assert len(decode(data["estado"], "B")) == n * nm


@needs_wh
def test_matrix_value_ranges(data):
    caudal = decode(data["caudal"], "H")
    agua = decode(data["agua"], "B")
    estado = decode(data["estado"], "B")
    assert max(caudal) > 0
    assert max(caudal) < 20000  # no single shale well makes 20k bbl/d
    assert set(estado) <= {b for b in range(8)}  # only bits 1, 2, 4
    assert max(agua) <= 255
    # bit 1 (producing) holds exactly when the month has an oil rate
    for c, e in zip(caudal, estado):
        if c > 0:
            assert e & 1
        if not e & 1:
            assert c == 0


@needs_wh
def test_mes0_matches_first_producing_month(data):
    nm = len(data["meta"]["meses"])
    estado = decode(data["estado"], "B")
    for i, p in enumerate(data["pozos"]):
        if 0 < p["mes0"] < nm:
            row = estado[i * nm:(i + 1) * nm]
            assert not any(e & 1 for e in row[: p["mes0"]]), p["id"]


@needs_wh
def test_hash_covers_the_matrices(data):
    import hashlib
    h = hashlib.sha1()
    for k, t in (("caudal", "H"), ("agua", "B"), ("estado", "B")):
        h.update(decode(data[k], t).tobytes())
    assert data["meta"]["hash_datos"] == h.hexdigest()[:12]


@needs_wh
def test_eventos_reference_valid_wells_and_dates(data):
    n, meses = data["meta"]["n_pozos"], data["meta"]["meses"]
    lo, hi = meses[0] + "-01", meses[-1] + "-31"
    prev = ""
    kinds = set()
    for e in data["eventos"]:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["f"])
        assert lo <= e["f"] <= hi, e
        assert (e["f"], e["t"]) >= (prev, ""), "eventos not sorted"
        prev = e["f"]
        assert e["t"] in ("frac", "interf")
        kinds.add(e["t"])
        assert isinstance(e["p"], int) and 0 <= e["p"] < n
        if e["t"] == "interf":
            assert isinstance(e["h"], int) and 0 <= e["h"] < n and e["h"] != e["p"]
            assert 0 <= e["rumbo"] < 180
            assert e["clase"] in CLASES
            assert 0 <= e["km"] <= 2.0 + 1e-9  # near (<1 km) and intermediate (1 to 2 km) bands
            if "bbl" in e:
                assert isinstance(e["bbl"], int)
        else:
            assert set(e) == {"f", "t", "p"}
    assert kinds == {"frac", "interf"}


@needs_wh
def test_pozo_frac_matches_first_frac_event_or_precedes_window(data):
    first = {}
    for e in data["eventos"]:
        if e["t"] == "frac":
            first.setdefault(e["p"], e["f"])
    for i, f in first.items():
        pf = data["pozos"][i]["frac"]
        assert pf is not None and pf <= f


@needs_wh
def test_cuenca_series(data):
    c, nm = data["cuenca"], len(data["meta"]["meses"])
    assert c["ops"] == data["meta"]["ops"]
    assert c["ops"][0] == "YPF" and c["ops"][-1] == "Otros"
    assert len(c["ops"]) == replay.N_OPS + 1 and len(set(c["ops"])) == len(c["ops"])
    assert len(c["kbbl"]) == len(c["ops"])
    for row in c["kbbl"]:
        assert len(row) == nm
        assert all(v >= 0 for v in row)
    assert sum(c["kbbl"][0]) > 0


@needs_wh
def test_curva_rows(data):
    assert data["curva"]
    assert {r["banda"] for r in data["curva"]} <= {"cercano", "control"}
    assert all(isinstance(r["k"], int) and r["indice"] >= 0 for r in data["curva"])


@needs_wh
def test_caudal_matches_warehouse_for_a_sample_month(data):
    n, meses = data["meta"]["n_pozos"], data["meta"]["meses"]
    nm = len(meses)
    caudal = decode(data["caudal"], "H")
    k = nm - 13  # a settled month, a year before the last
    mes = meses[k] + "-01"
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        rows = con.execute("""
            select f.pozo_id, f.petroleo_m3, f.dias_mes
            from fct_produccion f join int_pozo_ubicacion u using (pozo_id)
            where f.mes = ?::date and f.petroleo_m3 > 0""", [mes]).fetchall()
    finally:
        con.close()
    ids = {p["id"]: i for i, p in enumerate(data["pozos"])}
    assert rows
    expected = 0.0
    for pid, pet, dias in rows:
        expected += pet / dias * replay.BBL_PER_M3 if dias else 0.0
    total = sum(caudal[i * nm + k] for i in range(n))
    assert abs(total - expected) <= 0.5 * len(rows)
    # and per well
    for pid, pet, dias in rows[:200]:
        if dias:
            got = caudal[ids[pid] * nm + k]
            assert abs(got - min(65535, pet / dias * replay.BBL_PER_M3)) <= 0.5 + 1e-6


@needs_wh
def test_two_runs_are_identical_apart_from_generado(payloads):
    a, b = payloads
    a, b = json.loads(json.dumps(a)), json.loads(json.dumps(b))
    a["meta"].pop("generado")
    b["meta"].pop("generado")
    assert a == b


# ---- generated file ----

@pytest.mark.skipif(not SITE.exists(), reason="site/replay.html not generated")
def test_generated_file_size_and_shape():
    assert SITE.stat().st_size < replay.MAX_BYTES
    html = SITE.read_text()
    assert html.lstrip().lower().startswith("<!doctype html")
    assert "/*__DATA__*/null" not in html
    assert html.count("const DATA = ") == 1


@pytest.mark.skipif(not SITE.exists(), reason="site/replay.html not generated")
def test_generated_file_has_no_unexpected_remote_urls():
    html = SITE.read_text()
    # strip the embedded data so only markup, css and code are inspected
    head = html.split("const DATA = ", 1)[0]
    tail = re.sub(r"^.*?;\n", "", html.split("const DATA = ", 1)[1], count=1, flags=re.S)
    code = head + tail
    hosts = set(re.findall(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//([^/"'?#]+)""", code, re.I))
    hosts |= set(re.findall(r"""url\(\s*["']?(?:https?:)?//([^/"')]+)""", code, re.I))
    hosts |= set(re.findall(r"""@import\s+["']?(?:https?:)?//([^/"';]+)""", code, re.I))
    assert hosts <= ALLOWED_REMOTE, hosts - ALLOWED_REMOTE
    assert not re.search(r"<script[^>]+\bsrc=", code, re.I), "template must not load external scripts"


@pytest.mark.skipif(not SITE.exists(), reason="site/replay.html not generated")
def test_generated_payload_parses_and_matches_contract():
    html = SITE.read_text()
    m = re.search(r"const DATA = (\{.*?\});\n", html, re.S)
    assert m
    d = json.loads(m.group(1))
    n, nm = d["meta"]["n_pozos"], len(d["meta"]["meses"])
    assert n == len(d["pozos"])
    assert len(decode(d["caudal"], "H")) == n * nm
    assert len(decode(d["agua"], "B")) == n * nm
    assert len(decode(d["estado"], "B")) == n * nm
    assert all(0 <= e["p"] < n for e in d["eventos"])
