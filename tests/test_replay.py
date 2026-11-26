"""Data contract and invariants of pipeline/replay.py and the generated site/replay.html."""
import base64
import json
import re
import shutil
import subprocess
import sys
from array import array

import duckdb
import numpy as np
import pytest

from pipeline import base_mapa, mundo, replay
from pipeline.ingest import DATA, ROOT

WAREHOUSE = DATA / "warehouse.duckdb"
SITE = ROOT / "site" / "replay.html"
CLASES = {"golpe", "cierre_preventivo", "ambos", "sin_efecto"}
# The page is self-contained: no remote hosts at all (system font stack, works offline).
ALLOWED_REMOTE: set[str] = set()

needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")
needs_base = pytest.mark.skipif(not base_mapa.DESTINO.exists(), reason="data/base_mapa.json not built")
# The type scale of the family: nothing on the page is set below 13 px or between two steps.
ESCALA = {13, 15, 18, 24, 36, 56}


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
    assert set(data) == {"meta", "pozos", "caudal", "agua", "estado", "eventos", "cuenca", "curva", "corte", "base"}
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
def test_corte_is_the_median_water_cut_of_the_same_parents(data):
    """corte against the warehouse, with the median taken here: the same parents and months as the rate index."""
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    filas = con.execute("""
        select i.banda, i.k, f.agua_m3, f.petroleo_m3
        from int_interferencia_mes i join fct_produccion f on f.pozo_id = i.padre and f.mes = i.mes_frac + to_months(i.k)
        where i.banda in ('cercano', 'control')""").fetchall()
    con.close()
    grupos: dict = {}
    for banda, k, agua, pet in filas:
        if pet and pet > 0 and agua is not None:
            grupos.setdefault((banda, k), []).append(agua / (agua + pet))
    esperado = {g: float(np.median(v)) for g, v in grupos.items()}
    # unrounded in the payload: the page rounds once, when it prints
    assert {(r["banda"], r["k"]): r["corte"] for r in data["corte"]} == pytest.approx(esperado, abs=1e-12)
    assert {(r["banda"], r["k"]) for r in data["corte"]} == {(r["banda"], r["k"]) for r in data["curva"]}
    assert all(0 <= r["corte"] <= 1 for r in data["corte"])


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


# ---- one family with the 3D world: base map, palette, type and links ----

def _tpl():
    return replay.TEMPLATE.read_text(encoding="utf-8")


def _tpl_mundo():
    return mundo.TEMPLATE.read_text(encoding="utf-8")


def _raiz(tpl):
    """The custom properties of a template's :root block, by name."""
    bloque = re.search(r":root \{(.*?)\n\}", tpl, re.S).group(1)
    return {k: " ".join(v.split()) for k, v in re.findall(r"(--[\w-]+|color-scheme):\s*([^;]+);", bloque)}


def _vec3(texto, patron):
    """The three numbers of the first vec3(...) or [...] that follows a marker."""
    m = re.search(patron + r"\s*(?:vec3\(|\[)([^)\]]+)[)\]]", texto)
    assert m, patron
    return [float(v) for v in m.group(1).split(",")]


@needs_wh
@needs_base
def test_base_is_the_base_map_product(data):
    """The page draws the product of pipeline.base_mapa as it is on disk: nothing recut, nothing added."""
    assert data["base"] == json.loads(base_mapa.DESTINO.read_text(encoding="utf-8"))
    assert set(data["base"]) >= {"caja", "q", "relieve", "agua", "rios", "limites", "bloques", "localidades", "fuentes"}


def test_leer_base_without_the_file(tmp_path):
    assert replay.leer_base(tmp_path / "no_hay.json") is None
    (tmp_path / "base.json").write_text('{"caja": [1, 2, 3, 4]}', encoding="utf-8")
    assert replay.leer_base(tmp_path / "base.json") == {"caja": [1, 2, 3, 4]}


def test_render_without_base_keeps_the_plain_grid(tmp_path):
    """A payload with base None still renders: the script guards every use of the base map."""
    tpl = _tpl()
    assert "const BASE = D.base ? " in tpl and "if (BASE) {" in tpl and "if (D.base) {" in tpl
    replay.render({"meta": {"mes_max": "2025-01", "generado": "x"}, "base": None}, tmp_path / "replay.html")
    assert '"base":null' in (tmp_path / "replay.html").read_text(encoding="utf-8")


def test_template_shares_the_tokens_of_the_mundo():
    """Palette and type families are the 3D world's, token by token."""
    a, b = _raiz(_tpl()), _raiz(_tpl_mundo())
    assert a == b
    # --tinta no va en el bloque de la familia: la da el sistema, y --tinta: var(--tinta) sería un círculo
    assert {"--fondo", "--petroleo", "--mal", "--ui", "--relato", "color-scheme"} <= set(a)
    # no second theme: the page is the family's dark one on every system setting
    assert "prefers-color-scheme" not in _tpl()
    # the dark one is forced, so the system setting does not change it
    assert 'data-theme="dark"' in _tpl() and 'data-theme="dark"' in _tpl_mundo()


def test_template_operator_pigments_match_the_mundo():
    for nombre in ("PIGMENTOS", "PIGMENTO_DE"):
        linea = re.compile(r"const " + nombre + r" = (.+);")
        assert linea.search(_tpl()).group(1) == linea.search(_tpl_mundo()).group(1)


def test_template_terrain_matches_the_mundo_shader():
    """Ground, light, altitude and water colours are the constants of the 3D terrain shader."""
    tpl, m = _tpl(), _tpl_mundo()
    sombra, luz = re.search(r"vec3 c = mix\(vec3\(([^)]+)\), vec3\(([^)]+)\), luz\);", m).groups()
    assert _vec3(tpl, "SOMBRA =") == [float(v) for v in sombra.split(",")]
    assert _vec3(tpl, "LUZ =") == [float(v) for v in luz.split(",")]
    assert _vec3(tpl, "ALTURA =") == _vec3(m, r"c \+=")
    assert _vec3(tpl, "AGUA =") == _vec3(m, r"c = mix\(c,\s*(?=vec3\([^)]*\), agua\))")
    # the same light and the same two passes of the hillshade
    for trozo in ("[-.62, .6, -.5]", "[[1, .7], [5, .3]]", "(.5 + 1.25 * v)"):
        assert trozo in tpl and trozo in m


def test_template_type_stays_on_the_scale():
    """Every size set in css or on a canvas is a step of the scale; nothing under 13 px."""
    tpl = _tpl()
    estilo = re.search(r"<style>(.*?)</style>", tpl, re.S).group(1)
    css = [int(v) for v in re.findall(r"font(?:-size)?:[^;{}]*?(\d+)px", estilo)]
    lienzo = [int(v) for v in re.findall(r"\bF\((\d+)", tpl)] + [int(v) for v in re.findall(r'(\d+)px " \+ C\.', tpl)]
    assert len(css) > 20 and len(lienzo) > 8
    assert set(css) <= ESCALA, sorted(set(css) - ESCALA)
    assert set(lienzo) <= ESCALA, sorted(set(lienzo) - ESCALA)
    # canvas text goes through the helper or the serif of the family: no literal font stack is left
    assert not re.search(r'font = "[^"]*\d+px (?!" \+ C\.)', tpl)


def test_templates_link_both_ways_with_the_month():
    tpl, m = _tpl(), _tpl_mundo()
    assert '<a id="a-mundo" href="mundo.html#libre">' in tpl
    assert '"mundo.html#libre&mes=" + mf' in tpl
    assert '<a id="ir-replay" href="replay.html">' in m
    assert '"replay.html#m=" + Math.floor(t / 12) + "-" + String(t % 12 + 1).padStart(2, "0")' in m
    assert "else if (hmes && libre) ponerMes(Number(hmes[1]));" in m


def test_template_keeps_every_panel():
    """Joining the family removes nothing: the rose, the recovery curve, the share, the feed, the card and estado."""
    tpl = _tpl()
    for trozo in ('id="rose"', 'id="curva"', 'id="share"', 'id="feed"', 'id="card"', 'id="tl"', 'id="legend"',
                  'data-v="estado"', 'id="tab-e"', 'id="fuentes"'):
        assert trozo in tpl, trozo


def test_template_has_no_dashes():
    assert not re.search("[" + chr(0x2013) + chr(0x2014) + "]", _tpl())


def test_template_findings_have_no_typed_figures():
    """A sentence tagged as measured takes its figures from the payload: none is typed into the template."""
    tpl = _tpl()
    medidos = re.findall(r'<p[^>]*>\s*<span class="marca medido">medido</span>(.*?)</p>', tpl, re.S)
    assert len(medidos) == 2
    for frase in medidos:
        texto = re.sub(r"<[^>]+>", "", frase)
        assert not re.search(r"\d,\d|\d\s?%", texto), texto
    for marca in ("wc-antes", "wc-mes2", "wc-control", "br-1", "br-6"):
        assert f'<span id="{marca}"></span>' in tpl
    # a missing value hides the sentence instead of showing a blank
    assert tpl.count('<p id="cifra-agua" hidden>') == 1 and tpl.count('<p id="cifra-brecha" hidden>') == 1


@needs_wh
@needs_node
def test_figures_block_matches_python(data, tmp_path):
    """The page's own figures block, run under node on the payload, against the same arithmetic on the marts."""
    bloque = re.search(r'<script id="base">\n(.*?)</script>', _tpl(), re.S).group(1)
    guion = tmp_path / "cifras.js"
    guion.write_text(bloque + """
const fs = require("fs");
const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
console.log(JSON.stringify({ b1: Cifras.brecha(D.curva, 1), b6: Cifras.brecha(D.curva, 6), antes: Cifras.corte(D.corte, "cercano", -1),
  mes2: Cifras.corte(D.corte, "cercano", 2), control: Cifras.corte(D.corte, "control", 2),
  falta: [Cifras.brecha(D.curva, 99), Cifras.corte(D.corte, "cercano", 99), Cifras.corte(undefined, "cercano", 2), Cifras.brecha([{ banda: "cercano", k: 1, indice: .5 }], 1)] }));
""", encoding="utf-8")
    entrada = tmp_path / "series.json"
    entrada.write_text(json.dumps({"curva": data["curva"], "corte": data["corte"]}), encoding="utf-8")
    r = json.loads(subprocess.run([NODE, str(guion), str(entrada)], capture_output=True, text=True, check=True).stdout)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    idx = {(b, k): v for b, k, v in con.execute("select banda, k, indice_mediana from mart_interferencia_curva").fetchall()}
    con.close()
    # the gap is control minus near, on the unrounded index
    assert r["b1"] == pytest.approx(idx["control", 1] - idx["cercano", 1], abs=1e-12)
    assert r["b6"] == pytest.approx(idx["control", 6] - idx["cercano", 6], abs=1e-12)
    assert r["b1"] > r["b6"]
    corte = {(c["banda"], c["k"]): c["corte"] for c in data["corte"]}
    assert (r["antes"], r["mes2"], r["control"]) == (corte["cercano", -1], corte["cercano", 2], corte["control", 2])
    assert r["falta"] == [None, None, None, None]


@needs_wh
@needs_node
def test_printed_figures_are_the_warehouse_values_rounded_once(data, tmp_path):
    """The five figures as the page prints them (its own fmt and ponerCifras, under node, on the payload) against
    the warehouse values rounded here in one step. A payload that rounds first can print another last digit: at
    four decimals the control water cut of month 2 (0.130497) became 0.1305 and the page printed 13,1%."""
    tpl = _tpl()
    bloque = re.search(r'<script id="base">\n(.*?)</script>', tpl, re.S).group(1)
    fmt = re.search(r"^const fmt = .*$", tpl, re.M).group(0)
    poner = re.search(r"^function ponerCifras\(\) \{\n.*?\n\}$", tpl, re.S | re.M).group(0)
    guion = tmp_path / "impreso.js"
    guion.write_text(bloque + """
const fs = require("fs");
const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const nodos = {};
const $ = (s) => nodos[s] || (nodos[s] = { textContent: "", hidden: true });
""" + fmt + "\n" + poner + """
ponerCifras();
console.log(JSON.stringify(Object.fromEntries(Object.entries(nodos).map(([s, n]) => [s, [n.textContent, n.hidden]]))));
""", encoding="utf-8")
    entrada = tmp_path / "series.json"
    entrada.write_text(json.dumps({"curva": data["curva"], "corte": data["corte"]}), encoding="utf-8")
    impreso = json.loads(subprocess.run([NODE, str(guion), str(entrada)], capture_output=True, text=True, check=True).stdout)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    idx = {(b, k): v for b, k, v in con.execute("select banda, k, indice_mediana from mart_interferencia_curva").fetchall()}
    filas = con.execute("""
        select i.banda, i.k, f.agua_m3 / (f.agua_m3 + f.petroleo_m3)
        from int_interferencia_mes i join fct_produccion f on f.pozo_id = i.padre and f.mes = i.mes_frac + to_months(i.k)
        where i.banda in ('cercano', 'control') and f.petroleo_m3 > 0 and i.k in (-1, 2)""").fetchall()
    con.close()
    cortes: dict = {}
    for banda, k, c in filas:
        cortes.setdefault((banda, k), []).append(c)

    def es(v, d):
        return f"{v:.{d}f}".replace(".", ",")

    def pc(banda, k):
        return es(100 * float(np.median(cortes[banda, k])), 1) + "%"

    assert impreso == {
        "#wc-antes": [pc("cercano", -1), True], "#wc-mes2": [pc("cercano", 2), True], "#wc-control": [pc("control", 2), True],
        "#cifra-agua": ["", False],
        "#br-1": [es(idx["control", 1] - idx["cercano", 1], 2), True], "#br-6": [es(idx["control", 6] - idx["cercano", 6], 2), True],
        "#cifra-brecha": ["", False]}


@needs_node
@needs_base
def test_base_block_decodes_like_python(tmp_path):
    """The page's own base map block, run under node, against the decoders of pipeline.base_mapa."""
    bloque = re.search(r'<script id="base">\n(.*?)</script>', _tpl(), re.S).group(1)
    base = json.loads(base_mapa.DESTINO.read_text(encoding="utf-8"))
    rampa = [100 * (c + f) for f in range(9) for c in range(9)]   # rises to the south east, so it faces the north west
    guion = tmp_path / "base.js"
    guion.write_text(bloque + """
const fs = require("fs");
const B = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const z = Base.relieve(B.relieve);
let suma = 0, min = Infinity, max = -Infinity;
for (const v of z) { suma += v; if (v < min) min = v; if (v > max) max = v; }
const R = Int16Array.from(JSON.parse(process.argv[3]));
console.log(JSON.stringify({ n: z.length, suma, min, max, filas: [0, 337, 674].map((f) => Array.from(z.subarray(f * B.relieve.cols, f * B.relieve.cols + 40))),
  rio: Array.from(Base.linea(B.rios[0].l[0])), bloque: Array.from(Base.linea(B.bloques[0].p[0])),
  plano: Array.from(Base.sombra(new Int16Array(81).fill(700), 9, 9, 500, 500)),
  sube: Base.sombra(R, 9, 9, 500, 500)[40], baja: Base.sombra(R.map((v) => 1600 - v), 9, 9, 500, 500)[40],
  suelo: [[0, 300], [.5, 600], [1, 3000], [.25, 1500]].map(([l, h]) => Base.suelo(l, h)), agua: Base.css(Base.AGUA, .5) }));
""", encoding="utf-8")
    r = json.loads(subprocess.run([NODE, str(guion), str(base_mapa.DESTINO), json.dumps(rampa)], capture_output=True, text=True, check=True).stdout)
    z = base_mapa.decodificar_relieve(base["relieve"])
    assert r["n"] == z.size and r["suma"] == int(z.sum())
    assert (r["min"], r["max"]) == (base["relieve"]["min"], base["relieve"]["max"]) == (int(z.min()), int(z.max()))
    assert r["filas"] == [z[f, :40].tolist() for f in (0, 337, 674)]
    assert r["rio"] == [v for p in base_mapa.decodificar_linea(base["rios"][0]["l"][0]) for v in p]
    assert r["bloque"] == [v for p in base_mapa.decodificar_linea(base["bloques"][0]["p"][0]) for v in p]
    # flat ground is the middle grey; a slope that faces the north west light is brighter than one that faces away
    assert set(r["plano"]) == {128}
    assert r["sube"] > 128 > r["baja"]

    def suelo(luz, h):
        """The terrain colour of the 3D shader, in Python: shade to light, plus a lift with altitude."""
        e = min(1.0, max(0.0, (h - 400) / 2200))
        s = e * e * (3 - 2 * e)
        return [int(np.floor(255 * (a + (b - a) * luz + c * s) + .5)) for a, b, c in zip((.030, .092, .122), (.118, .232, .282), (.016, .024, .028))]

    assert r["suelo"] == [suelo(0, 300), suelo(.5, 600), suelo(1, 3000), suelo(.25, 1500)]
    assert r["agua"] == "rgba(17, 47, 65, 0.5)"


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
    if base_mapa.DESTINO.exists():
        assert d["base"] == json.loads(base_mapa.DESTINO.read_text(encoding="utf-8"))
