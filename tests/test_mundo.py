"""Data contract, pure functions and self-test of pipeline/mundo.py and the generated site/mundo.html."""
import base64
import hashlib
import itertools
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from array import array
from statistics import median

import duckdb
import numpy as np
import pytest

from pipeline import base_foto, base_mapa, informe, mundo, replay
from pipeline.decision import valor_indicativo
from pipeline.ingest import DATA, ROOT

WAREHOUSE = DATA / "warehouse.duckdb"
SITE = ROOT / "site" / "mundo.html"
README = ROOT / "README.md"
ANCHO = mundo.K_MAX - mundo.K_MIN + 1
NODE = shutil.which("node")

needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
needs_site = pytest.mark.skipif(not SITE.exists(), reason="site/mundo.html not generated")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")

# Runs the page's own core (the script with id "nucleo") against the data embedded in the same file.
NODE_AUTOTEST = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[1], "utf8");
const D = JSON.parse(html.match(/const DATA = (\{.*?\});\n/s)[1]);
const src = html.match(/<script id="nucleo">([\s\S]*?)<\/script>/)[1];
const m = { exports: {} };
new Function("module", src)(m);
const M = m.exports.abrir(D);
const casos = JSON.parse(process.argv[2] || "[]").map(c => m.exports.plantar(M, c[0], c[1], c[2]));
console.log(JSON.stringify({ autotest: m.exports.autotest(M, D.autotest), casos }));
"""

# The nearest well of another pad, by the page's own core, for the wells given as a JSON list.
NODE_VECINO = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[1], "utf8");
const D = JSON.parse(html.match(/const DATA = (\{.*?\});\n/s)[1]);
const m = { exports: {} };
new Function("module", html.match(/<script id="nucleo">([\s\S]*?)<\/script>/)[1])(m);
const M = m.exports.abrir(D);
console.log(JSON.stringify(JSON.parse(process.argv[2]).map(p => m.exports.vecino(M, p))));
"""

# The page's own series for the timeline chart and the scene events, for the wells and months given as JSON.
NODE_SERIE = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[1], "utf8");
const D = JSON.parse(html.match(/const DATA = (\{.*?\});\n/s)[1]);
const m = { exports: {} };
new Function("module", html.match(/<script id="nucleo">([\s\S]*?)<\/script>/)[1])(m);
const N = m.exports, M = N.abrir(D), e = JSON.parse(process.argv[2]), ac = N.acumuladoBbl(M), ll = N.llegadasPorMes(M);
console.log(JSON.stringify({ fracs: Array.from(N.fracsPorMes(M)), llegadas: { mes: Array.from(ll.mes), antes: ll.antes, sin: ll.sin },
  primeros: e.pozos.map(p => N.primerMes(M, p)), acumulado: e.pozos.map(p => e.meses.map(j => ac[p * M.nm + j])),
  partes: e.meses.map(j => N.partesCuenca(M, j)), dias: e.dias.map(d => N.mesDeDia(M.inicio, d)) }));
"""

# The page's own search, for the queries given as a JSON list.
NODE_BUSCAR = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[1], "utf8");
const D = JSON.parse(html.match(/const DATA = (\{.*?\});\n/s)[1]);
const m = { exports: {} };
new Function("module", html.match(/<script id="nucleo">([\s\S]*?)<\/script>/)[1])(m);
const M = m.exports.abrir(D), ix = m.exports.indiceBusqueda(M);
console.log(JSON.stringify(JSON.parse(process.argv[2]).map(q => m.exports.buscar(ix, q, M.meta.busca_max))));
"""

# The page's own line-source field: E1, the drawdown, the sampled profile and the pads around the wells given as JSON.
NODE_FRENTE = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[1], "utf8");
const D = JSON.parse(html.match(/const DATA = (\{.*?\});\n/s)[1]);
const m = { exports: {} };
new Function("module", html.match(/<script id="nucleo">([\s\S]*?)<\/script>/)[1])(m);
const N = m.exports, M = N.abrir(D), e = JSON.parse(process.argv[2]);
console.log(JSON.stringify({ e1: e.x.map(N.e1), caida: e.s.map(N.caidaAdim), perfil: Array.from(N.perfilCaida(e.n, e.s_max)),
  pads: e.casos.map(c => N.padsEnRadio(M, c[0], c[1], c[2])) }));
"""

# The page's own reading of a base map: ground elevation at the wells and the count of each vector layer.
NODE_BASE = r"""
const fs = require("fs");
const m = { exports: {} };
new Function("module", fs.readFileSync(process.argv[1], "utf8"))(m);
const N = m.exports, e = JSON.parse(process.argv[2]), B = N.abrirBase(e.base);
const cb = N.cotasBocas({ n: e.pozos.lon.length, base: B, pozos: e.pozos });
let suma = 0, min = Infinity, max = -Infinity;
for (const v of B.z) { suma += v; if (v < min) min = v; if (v > max) max = v; }
const capas = {};
for (const [capa, clave] of [["rios", "l"], ["agua", "p"], ["limites", "l"], ["bloques", "p"]]) capas[capa] = N.recuentoCapa(B[capa], clave);
console.log(JSON.stringify({ celdas: B.z.length, suma, min, max, fuera: cb.fuera, mediana_m: cb.mediana, tope_m: cb.tope,
  cotas: Array.from(cb.c, v => Number.isNaN(v) ? null : v), puntos: e.puntos.map(q => N.cota(B, q[0], q[1])), capas }));
"""

# Five wells, two operators and three areas for the search tests.
POZOS_BUSCA = {"id": [1, 2, 3, 4, 5], "sigla": ["XX.LOMA-2", "LOMA-10", "LOMA-1", "OTRO.x-1", "LOMA-1"],
               "op": [0, 1, 1, 0, 1], "area": [0, 0, 1, 2, 1]}
OPS_BUSCA, AREAS_BUSCA = ["Lomax SA", "Otra Cia"], ["LOMA CAMPANA  ", "La Loma", "RINCON"]


def decode(s, typecode):
    a = array(typecode)
    a.frombytes(base64.b64decode(s, validate=True))
    if sys.byteorder == "big" and a.itemsize > 1:
        a.byteswap()
    return a


def node_autotest(path, casos=()):
    r = subprocess.run([NODE, "-e", NODE_AUTOTEST, str(path), json.dumps(list(casos))],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout)


@pytest.fixture(scope="module")
def payloads():
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        return mundo.collect(con), mundo.collect(con)
    finally:
        con.close()


@pytest.fixture(scope="module")
def data(payloads):
    return payloads[0]


@pytest.fixture(scope="module")
def ev(data):
    return {k: decode(v, "B" if k == "flags" else "H") for k, v in data["eventos"].items()}


def caudal_fixture(nm, filas):
    """Matrix of len(filas) wells x nm months: each row is {month index: bbl/d}; the rest has no row."""
    c = array("H", [mundo.SIN_FILA]) * (len(filas) * nm)
    for p, fila in enumerate(filas):
        for j, v in fila.items():
            c[p * nm + j] = int(round(v * mundo.ESCALA_CAUDAL))
    return c


# ---- pure functions (no warehouse) ----

def test_distancia_km_is_the_formula_of_the_event_sql():
    assert mundo.distancia_km(-69, -38, -69, -38) == 0
    assert mundo.distancia_km(-69, -38, -69, -38.01) == pytest.approx(1.1132)
    assert mundo.distancia_km(-69, -38, -68.99, -38) == pytest.approx(1.1132 * math.cos(math.radians(-38)))
    # the cosine is taken at the child's latitude, as in int_par_padre_hijo
    assert mundo.distancia_km(-69, 0, -68, 60) != mundo.distancia_km(-68, 60, -69, 0)


def test_grupo_edad_boundaries():
    assert [mundo.grupo_edad(e) for e in (6, 11, 12, 23, 24, 47, 48, 200)] == [0, 0, 1, 1, 2, 2, 3, 3]


def test_dias_del_mes_runs_past_the_data_and_knows_leap_years():
    assert [mundo.dias_del_mes((2012, 1), j) for j in (0, 1, 2, 11, 13)] == [31, 29, 31, 31, 28]
    assert mundo.dias_del_mes((2026, 9), 5) == 28  # February 2027


def test_mes_de_dia_counts_from_the_first_day_and_knows_month_lengths():
    abril = (2011, 4)
    assert [mundo.mes_de_dia(abril, d) for d in (0, 15, 30, 61)] == [0.0, 0.5, 1.0, 2.0]   # April has 30 days, May 31
    assert mundo.mes_de_dia((2024, 2), 28) == pytest.approx(28 / 29)                        # the last day of a leap February
    assert mundo.mes_de_dia((2024, 2), 29) == 1.0 and mundo.mes_de_dia((2023, 2), 28) == 1.0


def test_primer_mes_is_the_earlier_of_first_oil_and_frac_job():
    pozos = {"id": [1, 2, 3, 4, 5], "mes0": [5, None, 3, None, 2],
             "frac": [None, "2011-06-15", "2011-04-02", None, "2010-12-01"]}
    assert [mundo.primer_mes(pozos, p, (2011, 4)) for p in range(5)] == [5, 2, 0, None, -4]
    r = mundo.llegadas_por_mes(pozos, (2011, 4), 4)
    assert r == {"mes": [1, 0, 1, 0], "antes": 1, "sin": 1}   # month 5 is past the four months and is not counted
    assert sum(r["mes"]) + r["antes"] + r["sin"] == 4          # the fifth well starts after the window


def test_fracs_por_mes_counts_each_dated_job_in_its_month():
    assert mundo.fracs_por_mes([0, 29, 30, 30, 61, 1000], (2011, 4), 3) == [2, 2, 1]   # day 1000 is past the series
    assert mundo.fracs_por_mes([], (2011, 4), 2) == [0, 0]


def test_pico_is_the_first_month_of_the_maximum():
    assert mundo.pico([1, 5, 3, 5]) == {"mes": 1, "n": 5}
    assert mundo.pico([]) == {"mes": 0, "n": 0} and mundo.pico([0, 0]) == {"mes": 0, "n": 0}


def test_partes_cuenca_add_up_to_one_and_are_missing_without_oil():
    cuenca = {"kbbl": [[1.0, 0.0], [3.0, 0.0]]}
    assert mundo.partes_cuenca(cuenca, 0) == [0.25, 0.75]
    assert mundo.partes_cuenca(cuenca, 1) == [None, None]


def test_acumulado_bbl_is_rate_times_calendar_days_and_skips_missing_rows():
    c = caudal_fixture(4, [{0: 100.0, 2: 50.0}, {}])
    abril = (2011, 4)   # April 30 days, May 31, June 30
    assert [mundo.acumulado_bbl(c, 4, 0, m, abril) for m in range(4)] == pytest.approx([3000.0, 3000.0, 4500.0, 4500.0])
    assert mundo.acumulado_bbl(c, 4, 1, 3, abril) == 0.0


def test_autotest_serie_on_a_hand_made_fixture():
    pozos = {"id": [1, 2], "mes0": [0, 2], "frac": [None, "2011-05-10"]}
    c = caudal_fixture(4, [{0: 100.0, 2: 50.0}, {2: 10.0, 3: 10.0}])
    cuenca = {"kbbl": [[1.0, 1.0, 1.0, 3.0], [1.0, 3.0, 0.0, 1.0]]}
    r = mundo.autotest_serie(pozos, c, 4, cuenca, (2011, 4), [39, 39, 70])
    assert r["fracs_mes"] == [0, 2, 1, 0] and r["pico_fracs"] == {"mes": 1, "n": 2}
    assert r["llegadas"] == {"mes": [1, 1, 0, 0], "antes": 0, "sin": 0}   # the second well arrives with its frac job
    assert {c["m"]: c["partes"] for c in r["partes"]}[3] == [0.75, 0.25]
    assert {(c["p"], c["m"]): c["bbl"] for c in r["acumulado"]}[(0, 3)] == pytest.approx(4500.0)
    assert {c["dia"] for c in r["dias"]} >= {0, 27, 30, 31, 59, 365, 1000, 39} and all(c["mes"] >= 0 for c in r["dias"])


def test_base_skips_months_without_a_row():
    c = caudal_fixture(6, [{2: 100.0, 4: 50.0}, {}])
    assert mundo.base_bbl_d(c, 6, 0, 5) == pytest.approx(75.0)  # months 2..4, month 3 has no row
    assert mundo.base_bbl_d(c, 6, 0, 1) is None                 # months -2..0: nothing
    assert mundo.base_bbl_d(c, 6, 1, 5) is None


def test_plantar_on_a_hand_computable_fixture():
    nm, m = 24, 12
    tres = {9: 100.0, 10: 100.0, 11: 100.0}
    lons = [-69.0, -69.0, -69.0, -69.0, -69.0]
    lats = [-38.005, -38.0135, -38.027, -38.004, -38.003]   # 0,56 km, 1,50 km, 3,01 km, 0,45 km, 0,33 km
    mes0 = [2, 0, 0, 7, None]                               # ages 10, 12, 12, 5 (too young), no oil
    caudal = caudal_fixture(nm, [tres, tres, tres, tres, tres])
    brecha = [[0.0] * 3 + [-0.1] * 7] + [[0.0] * 3 + [-0.5] * 7] * 3
    r = mundo.plantar(-69.0, -38.0, m, lons, lats, mes0, caudal, nm, brecha, (2020, 1))
    assert [c["p"] for c in r["cercanos"]] == [0]
    assert (r["n_intermedio"], r["n_control"]) == (1, 1)
    assert r["cercanos"][0]["grupo"] == 0 and r["base_bbl_d"] == pytest.approx(100.0)
    # January to July 2021 have 212 days: 0,1 x 100 bbl/d x 212 d
    assert r["diferido_bbl"] == pytest.approx(2120.0)


def test_plantar_drops_parents_under_the_base_rate():
    nm = 12
    bajo = {j: 6.0 for j in (5, 6, 7)}    # 6 bbl/d is 0,95 m3/d: under the 1 m3/d rule
    justo = {j: 6.4 for j in (5, 6, 7)}   # 1,02 m3/d
    r = mundo.plantar(-69.0, -38.0, 8, [-69.0, -69.0], [-38.001, -38.002], [0, 0],
                      caudal_fixture(nm, [bajo, justo]), nm, [[-0.1] * ANCHO] * 4, (2020, 1))
    assert [c["p"] for c in r["cercanos"]] == [1]


def test_plantar_splits_the_deferred_oil_by_month():
    nm, tres = 24, {9: 100.0, 10: 100.0, 11: 100.0}
    brecha = [[0.0] * 3 + [-0.1, -0.2, 0.0, 0.05, 0.0, 0.0, 0.0]] * 4
    r = mundo.plantar(-69.0, -38.0, 12, [-69.0], [-38.005], [0], caudal_fixture(nm, [tres]), nm, brecha, (2020, 1))
    # January 2021 has 31 days and February 28; a month where the near parents run above the control is negative
    assert r["por_mes"] == pytest.approx([310.0, 560.0, 0.0, -150.0, 0.0, 0.0, 0.0])
    assert len(r["por_mes"]) == mundo.K_MAX + 1 and sum(r["por_mes"]) == pytest.approx(r["diferido_bbl"])
    # two near parents: the total doubles and the figure per parent stays at 310 + 560 - 150
    dos = mundo.plantar(-69.0, -38.0, 12, [-69.0, -69.0], [-38.005, -38.004], [0, 0], caudal_fixture(nm, [tres, tres]),
                        nm, brecha, (2020, 1))
    assert dos["diferido_bbl"] == pytest.approx(1440.0) and dos["por_padre_bbl"] == pytest.approx(720.0)
    vacio = mundo.plantar(-60.0, -38.0, 12, [-69.0], [-38.005], [0], caudal_fixture(nm, [tres]), nm, brecha, (2020, 1))
    assert vacio["cercanos"] == [] and vacio["por_mes"] == [0.0] * (mundo.K_MAX + 1) and vacio["diferido_bbl"] == 0
    assert vacio["por_padre_bbl"] is None


def test_vecino_otro_pad_skips_pad_mates_and_keeps_the_first_of_a_tie():
    lons = [-69.0, -69.0, -69.0, -69.0]
    lats = [-38.0, -38.0001, -38.005, -37.995]   # a pad mate 11 m away, then two wells of other pads at 0,56 km
    assert mundo.vecino_otro_pad(0, lons, lats, [7, 7, 8, 9]) == (2, pytest.approx(0.5566))
    assert mundo.vecino_otro_pad(0, lons, lats, [7, 7, 7, 9]) == (3, pytest.approx(0.5566))
    assert mundo.vecino_otro_pad(0, lons, lats, [7, 7, 7, 7]) is None
    q, km = mundo.vecino_otro_pad(2, lons, lats, [7, 7, 8, 9])
    assert q == 1 and km == pytest.approx(mundo.distancia_km(-69.0, -38.005, -69.0, -38.0001))


def test_clave_busqueda_drops_accents_case_and_punctuation():
    assert mundo.clave_busqueda("Xx.Nq.LLL-1234(h)") == "XXNQLLL1234H"
    assert mundo.clave_busqueda(" A\u00f1elo  \u00d1and\u00fa ") == "ANELONANDU"
    assert mundo.clave_busqueda("") == "" and mundo.clave_busqueda("- .") == ""


def test_buscar_puts_prefix_matches_first_and_counts_wells_by_area_and_operator():
    r = mundo.buscar("loma", POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA)
    assert r["pozos"] == [2, 4, 1, 0] and r["total"] == 4   # LOMA1 twice by index, LOMA10, then the one that only contains it
    assert r["areas"] == [[0, 2], [1, 2]] and r["operadores"] == [[0, 2]]   # a tie keeps the lower index first
    assert mundo.buscar("loma", POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA, tope=1) == {**r, "pozos": [2]}
    vacio = {"pozos": [], "total": 0, "areas": [], "operadores": []}
    assert mundo.buscar("l", POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA) == vacio      # one character is too short
    assert mundo.buscar("- l.", POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA) == vacio   # and punctuation does not count
    assert mundo.buscar("zzz", POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA) == vacio
    assert mundo.buscar("rinc\u00f3n", POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA) == {**vacio, "areas": [[2, 1]]}


def test_consultas_de_prueba_cover_wells_groups_and_the_two_empty_cases():
    qs = mundo.consultas_de_prueba(POZOS_BUSCA, OPS_BUSCA, AREAS_BUSCA)
    assert len(qs) == mundo.AT_BUSQUEDAS + 4 and qs[-2:] == ["a", "zzqqzz"]
    assert qs[:mundo.AT_BUSQUEDAS] == ["XX.LOM", "LOMA-1", "LOMA-1", "OTRO.x", "LOMA-1", "LOMA-1"]
    assert qs[-4] == "otra " and qs[-3] == "LOMA CAMPANA  "   # the operator and the area with most wells


def test_costo_de_diferir_is_the_formula_of_decision():
    esperado = 1000.0 * 60.0 * (1 - 1.1 ** -1)
    assert mundo.costo_de_diferir(1000.0, 60.0, 0.10, 12) == pytest.approx(esperado)
    v = valor_indicativo(1000.0 / mundo.BBL_PER_M3, 60.0, 0.10, 12)
    assert mundo.costo_de_diferir(1000.0, 60.0, 0.10, 12) == v["costo_de_diferir"]


def test_radio_de_investigacion_textbook_value_and_units():
    # k = 10 md, t = 10 h, phi = 0,1, mu = 1 cp, ct = 1e-5 1/psi: r = sqrt(100 / 9,48e-4) = 324,8 ft
    r = mundo.radio_investigacion_ft(10.0, 10.0, 0.1, 1.0, 1e-5)
    assert r == pytest.approx(324.78, abs=0.01)
    assert mundo.tiempo_a_radio_h(r, 10.0, 0.1, 1.0, 1e-5) == pytest.approx(10.0)
    assert mundo.permeabilidad_a_radio_md(r, 10.0, 0.1, 1.0, 1e-5) == pytest.approx(10.0)   # and solved for k
    # the SI form (2 sqrt(eta t)) is the same formula: 948 is a rounded constant, so they agree to 0,1%
    assert mundo.radio_investigacion_m(10.0, 10.0, 0.1, 1.0, 1e-5) == pytest.approx(r * mundo.FT_M, rel=1e-3)
    # four times the time, twice the radius
    assert mundo.radio_investigacion_ft(10.0, 40.0, 0.1, 1.0, 1e-5) == pytest.approx(2 * r)


def test_radio_with_matrix_permeability_does_not_reach_a_kilometre():
    horas = mundo.tiempo_a_radio_h(1000 / mundo.FT_M, 1e-4, 0.08, 0.5, 1.5e-5)  # 100 nD
    assert horas / 8766 > 1000  # thousands of years


def test_e1_matches_the_tables_a_quadrature_and_both_of_its_branches():
    # Abramowitz and Stegun, table 5.1, to its ten decimals
    tabla = {0.1: 1.8229239584, 0.5: 0.5597735948, 1.0: 0.2193839344, 2.0: 0.0489005107, 5.0: 0.0011482956}
    for x, v in tabla.items():
        assert mundo.e1(x) == pytest.approx(v, abs=6e-11), x
    assert mundo.e1(10.0) == pytest.approx(4.156968930e-6, rel=1e-9)

    def cuadratura(x, n=20000):
        # E1(x) = integral over u in (0, 1] of exp(-x / u) / u, by Simpson's rule (the integrand is 0 at u = 0)
        f = [0.0] + [math.exp(-x / (i / n)) / (i / n) for i in range(1, n + 1)]
        return (f[0] + f[n] + 4 * sum(f[1:n:2]) + 2 * sum(f[2:n:2])) / (3 * n)

    for x in (0.3, 0.9, 1.0, 1.1, 3.0, 7.5):
        assert mundo.e1(x) == pytest.approx(cuadratura(x), rel=1e-9), x
    # the series and the continued fraction meet at 1 without a step, and near zero E1 is the logarithm
    assert mundo.e1(1.0 + 1e-9) == pytest.approx(mundo.e1(1.0), rel=1e-8)
    assert mundo.e1(1e-8) == pytest.approx(-mundo.EULER - math.log(1e-8), abs=1e-7)
    for malo in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            mundo.e1(malo)


def test_caida_adim_keeps_its_shape_and_has_no_edge():
    # pD(s) = E1(s^2) / 2 with s = r / r_inv: one curve for every time, falling outwards and never zero
    assert mundo.caida_adim(1.0) == pytest.approx(0.5 * 0.2193839344, rel=2e-9)
    assert mundo.caida_adim(0.5) == pytest.approx(0.5 * mundo.e1(0.25))
    valores = [mundo.caida_adim(x / 10) for x in range(1, 31)]
    assert all(a > b > 0 for a, b in zip(valores, valores[1:]))
    # at the radius of investigation about a twentieth of the drawdown at a tenth of it is left: the page says 5%
    assert round(100 * mundo.caida_adim(1.0) / mundo.caida_adim(0.1)) == 5
    # the same point in physical units: r = r_inv(t) is s = 1 whatever the time
    eta_args = (1.0, 0.08, 0.5, 1.5e-5)
    for t in (24.0, 720.0, 8766.0):
        r = mundo.radio_investigacion_ft(eta_args[0], t, *eta_args[1:])
        assert mundo.tiempo_a_radio_h(r, *eta_args) == pytest.approx(t)


def test_pads_en_radio_groups_by_pad_and_counts_only_wells_that_produce():
    #        anchor   pad mate    pad 8, 0,56 km  pad 8, 1,0 km  pad 9, 1,1 km  pad 10, later  pad 11, no oil  pad 12, 3,3 km
    lons = [-69.0,   -69.0,      -69.0,          -69.0,         -69.0,         -69.0,         -69.0,          -69.0]
    lats = [-38.0,   -38.0001,   -38.005,        -38.009,       -37.99,        -38.003,       -38.002,        -38.03]
    pads = [7, 7, 8, 8, 9, 10, 11, 12]
    mes0 = [0, 0, 5, 2, 3, 40, None, 0]
    r = mundo.pads_en_radio(0, lons, lats, pads, mes0, 2.0, 10)
    assert [(g["q"], g["n"]) for g in r] == [(2, 2), (4, 1)]
    assert r[0]["km"] == pytest.approx(mundo.distancia_km(-69.0, -38.0, -69.0, -38.005))
    assert r[1]["km"] == pytest.approx(1.1132, abs=1e-3)
    # before the nearer well of pad 8 produces, the pad is named by the other one; later, pad 10 joins as the nearest
    antes = mundo.pads_en_radio(0, lons, lats, pads, mes0, 2.0, 4)
    assert [(g["q"], g["n"]) for g in antes] == [(3, 1), (4, 1)]
    assert [g["q"] for g in mundo.pads_en_radio(0, lons, lats, pads, mes0, 2.0, 40)] == [5, 2, 4]
    # a smaller radius drops the far pads, and a well alone has an empty list
    assert [(g["q"], g["n"]) for g in mundo.pads_en_radio(0, lons, lats, pads, mes0, 0.8, 10)] == [(2, 1)]
    assert mundo.pads_en_radio(7, lons, lats, pads, mes0, 2.0, 10) == []
    assert mundo.pads_en_radio(0, lons, lats, [7] * 8, mes0, 2.0, 10) == []


def test_ancho_drenado_textbook_value():
    # 50.000 m3 x 1,4 / (30 m x 0,08 x 0,7 x 0,08) = 520.833 m2; over 2.500 m of lateral = 208,3 m
    assert mundo.ancho_drenado_m(50000.0, 1.4, 30.0, 0.08, 0.3, 0.08, 2500.0) == pytest.approx(208.333, abs=1e-3)


def test_mediana_indices_skips_missing_months():
    ind = array("H", [mundo.SIN_INDICE] * (3 * ANCHO))
    for e, v in enumerate((8000, 6000, mundo.SIN_INDICE)):
        ind[e * ANCHO + 1 - mundo.K_MIN] = v
    assert mundo.mediana_indices(ind, 3, range(3), 1) == pytest.approx(0.7)
    assert mundo.mediana_indices(ind, 3, range(3), 2) is None


def _eventos_acto2(grupos):
    """grupos: [(child, month, [near month-1 indices], n controls)] -> arguments of elegir_acto2."""
    hijos, meses, control, ind = [], [], [], array("H")
    for h, m, cerca, n_ctrl in grupos:
        for v, es_control in [(v, False) for v in cerca] + [(1.0, True)] * n_ctrl:
            hijos.append(h)
            meses.append(m)
            control.append(es_control)
            fila = [10000] * ANCHO
            fila[1 - mundo.K_MIN] = int(round(v * 10000))
            ind.extend(fila)
    return hijos, meses, control, ind


def test_elegir_acto2_follows_the_rule():
    hijos, meses, control, ind = _eventos_acto2([
        (1, 50, [0.60, 0.66, 0.70], 3),   # median 0,66: distance 0,01 from the basin
        (2, 40, [0.64, 0.65, 0.90], 3),   # median 0,65: the closest
        (3, 30, [0.65, 0.65], 3),         # only 2 near parents
        (4, 20, [0.65, 0.65, 0.65], 2),   # only 2 controls
        (5, 10, [0.65, 0.65, 0.65], 3),   # child without complete frac data
        (6, 45, [0.64, 0.65, 0.90], 3),   # ties with child 2, later month
    ])
    h, m, cerca, ctrl = mundo.elegir_acto2(hijos, meses, control, ind, {1, 2, 3, 4, 6}, 0.65)
    assert (h, m) == (2, 40)
    assert len(cerca) == 3 and len(ctrl) == 3 and not any(control[e] for e in cerca) and all(control[e] for e in ctrl)


def test_elegir_acto2_needs_the_full_window():
    hijos, meses, control, ind = _eventos_acto2([(1, 50, [0.65, 0.65, 0.65], 3)])
    ind[0] = mundo.SIN_INDICE  # one near parent loses month -3
    assert mundo.elegir_acto2(hijos, meses, control, ind, {1}, 0.65) is None


def _hoja_mini():
    """A base map of 4 by 3 cells over a box of 4 by 3 degrees, with one element in each vector layer."""
    z = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], dtype=np.int64)
    rel = {"cols": 4, "filas": 3, "min": 1, "max": 12,
           "d": base64.b64encode(base_mapa.codificar_relieve(z)).decode("ascii")}
    linea, anillo = base_mapa.codif([(0, 0), (10, 20), (30, 5)]), base_mapa.codif([(1, 1), (5, 1), (5, 5), (1, 1)])
    return {"v": 1, "caja": [0.0, 0.0, 4.0, 3.0], "q": 65535, "relieve": rel,
            "rios": [{"n": "Río A", "km": 70.0, "l": [linea, linea]}],
            "agua": [{"n": "Lago B", "t": "lago", "km2": 2.0, "p": [anillo]}],
            "limites": [{"n": "A y B", "l": [linea]}], "localidades": [{"n": "Añelo", "x": 1, "y": 2}],
            "bloques": [{"n": "Área", "c": "A-1", "op": "Op", "km2": 1.0, "p": [anillo, anillo]}], "fuentes": []}


POZOS_HOJA = {"id": [1, 2, 3, 4], "lon": [1.5, 2.0, -0.1, 4.0], "lat": [1.5, 1.0, 1.5, 1.5]}


def test_autotest_base_on_a_hand_made_sheet():
    """Cell centres give the cell, a cell corner the mean of four, the east edge its column; outside there is none."""
    t = mundo.autotest_base(_hoja_mini(), POZOS_HOJA)
    assert (t["celdas"], t["suma"], t["min"], t["max"]) == (12, 78, 1, 12)
    assert [b["p"] for b in t["bocas"]] == [0, 1, 2] + [3] * (mundo.AT_BOCAS - 3)
    assert [b["m"] for b in t["bocas"][:4]] == [6.0, 8.5, None, 8.0]
    assert (t["fuera"], t["mediana_m"], t["tope_m"]) == (1, 8.0, 8.5)
    assert [q["m"] for q in t["puntos"]] == [1.0, 12.0, 6.5, None, None]
    assert t["capas"] == {"rios": {"n": 1, "partes": 2, "puntos": 6, "suma": 130},
                          "agua": {"n": 1, "partes": 1, "puntos": 4, "suma": 20},
                          "limites": {"n": 1, "partes": 1, "puntos": 3, "suma": 65},
                          "bloques": {"n": 1, "partes": 2, "puntos": 8, "suma": 40}}
    assert t["localidades"] == 1


def test_autotest_base_without_wells_inside_the_sheet():
    t = mundo.autotest_base(_hoja_mini(), {"id": [1], "lon": [9.0], "lat": [9.0]})
    assert (t["fuera"], t["mediana_m"], t["tope_m"]) == (1, None, None)


@needs_node
def test_core_reads_a_hand_made_sheet_like_python(tmp_path):
    """The same sheet through the page's core: the decoder, the bilinear elevation and the layer counts agree."""
    js = tmp_path / "nucleo.js"
    js.write_text(_script(mundo.TEMPLATE.read_text(encoding="utf-8"), "nucleo"), encoding="utf-8")
    hoja, t = _hoja_mini(), mundo.autotest_base(_hoja_mini(), POZOS_HOJA)
    entrada = {"base": hoja, "pozos": POZOS_HOJA, "puntos": [[q["lon"], q["lat"]] for q in t["puntos"]]}
    r = subprocess.run([NODE, "-e", NODE_BASE, str(js), json.dumps(entrada)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-800:]
    js_r = json.loads(r.stdout)
    assert js_r["cotas"] == [6.0, 8.5, None, 8.0]
    assert js_r["puntos"] == [q["m"] for q in t["puntos"]]
    for k in ("celdas", "suma", "min", "max", "fuera", "mediana_m", "tope_m", "capas"):
        assert js_r[k] == t[k], k


def test_collect_without_a_base_map_leaves_the_page_without_one(tmp_path):
    assert mundo.leer_base_mapa(tmp_path / "no_hay.json") is None
    assert mundo.leer_base_mapa()["v"] == 1


def test_the_finer_relief_travels_with_the_base_map_when_its_file_is_next_to_it(tmp_path):
    """The sheet alone gives a page that draws the sheet grid everywhere; with the file next to it, both travel."""
    solo = tmp_path / "base_mapa.json"
    solo.write_bytes(mundo.BASE_MAPA.read_bytes())
    assert "relieve_fino" not in mundo.leer_base_mapa(solo)
    (tmp_path / base_mapa.FINO.name).write_bytes(base_mapa.FINO.read_bytes())
    assert mundo.leer_base_mapa(solo)["relieve_fino"] == base_mapa.leer_fino() == mundo.leer_base_mapa()["relieve_fino"]


def _hoja_mini_con_fino():
    """The hand-made sheet with a finer grid of 100 m over its middle, blended over a quarter of each side."""
    z = np.full((2, 4), 100, dtype=np.int64)
    return dict(_hoja_mini(), relieve_fino={
        "v": 1, "caja": [1.0, 1.0, 3.0, 2.0], "paso_seg": 4, "margen": 0.25, "cols": 4, "filas": 2, "min": 100,
        "max": 100, "d": base64.b64encode(base_mapa.codificar_relieve(z)).decode("ascii")})


def test_autotest_base_follows_the_finer_relief_where_it_rules():
    """Inside the finer box the wellhead takes its height; on its edge and outside, the sheet's, as without it."""
    sin, t = mundo.autotest_base(_hoja_mini(), POZOS_HOJA), mundo.autotest_base(_hoja_mini_con_fino(), POZOS_HOJA)
    assert "fino" not in sin and [b["m"] for b in t["bocas"][:4]] == [100.0, 8.5, None, 8.0]
    assert (t["celdas"], t["suma"], t["capas"]) == (sin["celdas"], sin["suma"], sin["capas"])
    f = t["fino"]
    assert (f["celdas"], f["suma"], f["min"], f["max"]) == (8, 800, 100, 100)
    assert [q["w"] for q in f["puntos"]] == pytest.approx([1, 0, 0, .5, 7 / 27, .15625, .896, .5])
    hoja = _hoja_mini()
    z, caja = base_mapa.decodificar_relieve(hoja["relieve"]), tuple(hoja["caja"])
    for q in f["puntos"]:
        h = base_mapa.cota(z, caja, q["lon"], q["lat"])
        assert q["m"] == pytest.approx(h + (100 - h) * q["w"])


def test_the_finer_relief_is_blended_the_same_way_in_the_core_and_in_the_shader():
    """One weight, three places: pipeline.base_mapa.peso_fino, the core of the page and the terrain shader."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    nucleo, motor = _script(tpl, "nucleo"), _script(tpl, "motor")
    assert "function pesoFino(F, lon, lat) {" in nucleo and "return t * t * (3 - 2 * t);" in nucleo
    assert "smoothstep(0., u_margen, min(min(q.x, 1. - q.x), min(q.y, 1. - q.y)))" in motor
    assert "return f.z > 0. ? mix(h, textureLod(u_rel2, f.xy, 0.).r, f.z) : h;" in motor
    for nombre in ('ver("relieve fino", ', 'ver("cota fina de un punto " + i, ', 'ver("sin relieve fino", !B.fino)'):
        assert nombre in nucleo, nombre


def _mini():
    pub = {"brecha_mes1": -0.229, "brecha_mes1_descontada": -0.192, "ic5_bajo": -0.287, "ic5_alto": -0.168,
           "bloques_5km": 144, "n_cercanos": 2, "cierre": [{"brecha6": -0.021}, {"brecha6": -0.047}],
           "dif_bbl": 5163.1, "dif_ic_bajo_bbl": 3173.7, "dif_ic_alto_bbl": 6952.0, "cota_bbl": 1337.1}
    return {"meta": {"mes_datos": "2026-09", "n_pozos": 3, "n_eventos": 5}, "pub": pub, "s": "</script><!-- x"}


def test_textos_formats_published_numbers_in_spanish():
    t = mundo.textos(_mini())
    assert (t["rango_bajo"], t["rango_alto"], t["ic5_bajo"], t["ic5_alto"]) == ("19", "23", "17", "29")
    assert (t["cierre_min"], t["cierre_max"]) == ("2,1", "4,7")
    assert (t["dif_bbl"], t["cota_bbl"], t["n_controles"]) == ("5.163", "1.337", "3")


def test_render_fills_markers_escapes_and_enforces_the_budget(tmp_path, monkeypatch):
    out = tmp_path / "x" / "m.html"
    size = mundo.render(_mini(), out)
    html = out.read_text(encoding="utf-8")
    assert size == out.stat().st_size
    assert "{{" not in html and "/*__DATA__*/null" not in html
    m = re.search(r"const DATA = (\{.*?\});\n", html, re.S)
    assert "</script" not in m.group(1) and json.loads(m.group(1))["s"] == "</script><!-- x"
    monkeypatch.setattr(mundo, "MAX_BYTES", 10)
    with pytest.raises(SystemExit):
        mundo.render(_mini(), tmp_path / "m.html")


def test_render_fails_on_an_unknown_marker(tmp_path, monkeypatch):
    plantilla = tmp_path / "t.html"
    plantilla.write_text("<p>{{no_existe}}</p>", encoding="utf-8")
    monkeypatch.setattr(mundo, "TEMPLATE", plantilla)
    with pytest.raises(ValueError):
        mundo.render(_mini(), tmp_path / "m.html")


def test_template_and_module_text_rules():
    for ruta in (mundo.TEMPLATE, ROOT / "pipeline" / "mundo.py"):
        texto = ruta.read_text(encoding="utf-8")
        assert chr(0x2013) not in texto and chr(0x2014) not in texto, ruta.name
        assert "TODO" not in texto and "FIXME" not in texto, ruta.name
    html = mundo.TEMPLATE.read_text(encoding="utf-8")
    assert not re.search(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", html, re.I)
    assert not re.search(r"""url\(\s*["']?(?:https?:)?//|@import""", html, re.I)
    assert not re.search(r"<script[^>]+\bsrc=", html, re.I)
    for bloque in ('<script id="datos">', '<script id="nucleo">', '<script id="app">'):
        assert html.count(bloque) == 1


# ---- payload contract (real warehouse) ----

def _script(tpl, nombre):
    return re.search(r'<script id="' + nombre + r'">\n(.*?)</script>', tpl, re.S).group(1)


def test_template_has_the_four_scripts_in_load_order():
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    assert re.findall(r'<script id="(\w+)">', tpl) == ["datos", "nucleo", "motor", "app"]


@needs_node
@pytest.mark.parametrize("nombre", ["nucleo", "motor", "app"])
def test_each_script_parses_under_node(nombre, tmp_path):
    js = tmp_path / (nombre + ".js")
    js.write_text(_script(mundo.TEMPLATE.read_text(encoding="utf-8"), nombre), encoding="utf-8")
    r = subprocess.run([NODE, "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_every_shader_declares_its_version_and_precision():
    motor = _script(mundo.TEMPLATE.read_text(encoding="utf-8"), "motor")
    assert 'const CAB = "#version 300 es\\nprecision highp float;' in motor
    fuentes = re.findall(r"const ([VF]S_\w+) = (CAB \+ )?`", motor)
    assert len(fuentes) >= 10 and all(con for _, con in fuentes)


def test_honesty_contract_is_on_the_page():
    """Section 2 of the plan: what the page must say wherever it draws something that is not data."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    for frase in ("exageración vertical", "dirección no publicada", "vertical aproximada (medida total menos rama)",
                  "m nominales de esquema", "las fracturas recientes se cargan con rezago",
                  "Sobre 2 queda fuera del cuadro", "hasta dónde puede llegar la rama"):
        assert frase in tpl, frase
    leyenda = re.search(r'<details class="leyenda".*?</details>', tpl, re.S).group(0)
    items = re.findall(r'<li(?: (?:id|class)="[\w-]+"| hidden)*>(.*?)</li>', leyenda, re.S)
    assert len(items) == leyenda.count("<li") >= 12 and all(re.match(r'<span class="marca (dato|medido|supuesto)">\1</span>', i) for i in items)
    app = _script(tpl, "app")
    marcas = re.findall(r'marca: "(\w+)"', app)
    assert len(marcas) == len(re.findall(r"\btitulo: \"", app)) >= 3 and set(marcas) <= {"dato", "medido", "supuesto"}


def test_page_degrades_without_webgl2_and_respects_reduced_motion():
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    aviso = re.search(r'<p class="sin-webgl" id="sin-webgl" hidden>(.*?)</p>', tpl, re.S).group(1)
    assert "WebGL2" in aviso and 'href="replay.html"' in aviso
    assert 'getContext("webgl2"' in _script(tpl, "motor")
    app = _script(tpl, "app")
    assert "prefers-reduced-motion" in app and "prefers-reduced-motion" in tpl.split("</style>")[0]
    assert ":focus-visible" in tpl.split("</style>")[0]


def test_every_control_is_a_native_element_with_a_name():
    """Keyboard and screen readers: buttons, a select and a range input, each with text or an aria-label."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    cuerpo = tpl.split('<div class="mundo"')[1].split("<footer")[0]
    assert not re.search(r"<(div|span)[^>]*\bonclick", cuerpo)
    botones = re.findall(r"<button[^>]*>(.*?)</button>", cuerpo, re.S)
    assert len(botones) >= 8
    for etiqueta, texto in re.findall(r"(<button[^>]*>)(.*?)</button>", cuerpo, re.S):
        assert 'type="button"' in etiqueta and (len(texto.strip()) > 1 or "aria-label=" in etiqueta), etiqueta
    for campo in re.findall(r"<(?:input|select)[^>]*>", cuerpo):
        assert "aria-label=" in campo, campo
    assert cuerpo.count('aria-hidden="true"') >= 3  # canvases and projected labels stay out of the reading order


def test_the_vertical_axis_says_what_it_is_in_every_reading():
    """Part D: time as height is one switch away, and the page always names the reading that is on. Part E: the
    ground reading is a third button, offered only when the page carries its image."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    # Part F: each reading carries an icon; it is hidden from assistive tech, so the name is still the word and its tag.
    ico = '<svg class="ico" aria-hidden="true"><use href="#i-%s"/></svg>'
    assert '<button type="button" id="lect-2" aria-pressed="false" hidden>' + ico % "suelo" + 'Suelo<span class="marca dato">' in tpl
    assert '<button type="button" id="lect-0" aria-pressed="true">' + ico % "prof" + 'Profundidad<span class="marca supuesto">' in tpl
    assert '<button type="button" id="lect-1" aria-pressed="false">' + ico % "tiempo" + 'Tiempo<span class="marca dato">' in tpl
    app = _script(tpl, "app")
    for frase in ('"la altura es el tiempo: "', "relieve sin exagerar", '"profundidad de esquema, exageración vertical "',
                  '"suelo: imagen satelital Sentinel-2 de "', 'relieve exagerado ×" + fmt(motor.VE_SUELO, 0)'):
        assert frase in app, frase
    # the tour opens and closes on the ground when the page carries its image and in the time reading when it does
    # not; the acts about the estimator stay in the depth schematic
    actos = re.findall(r'titulo: "([^"]+)", seg: \d+,([^\n]*)', app)
    assert ["get lect() { return conFoto ? 2 : 1; }" in resto for _, resto in actos] == [True, False, False, False, False, True]
    assert not re.search(r"\blect: [12]\b", "".join(resto for _, resto in actos))
    assert 'if (conFoto) {\n    document.body.classList.add("con-foto"); $("lect-2").hidden = false;' in app
    assert "v = v === 2 && conFoto ? 2 : v ? 1 : 0;" in app   # no image, no ground reading, whoever asks for it


def test_the_axis_labels_do_not_need_the_base_map_and_the_reading_follows_the_camera():
    """Review of part D: a page without a base map keeps its year rule, #libre opens in the reading its camera
    frames, and with the estimator open the depth button leaves the camera on the chart."""
    app = _script(mundo.TEMPLATE.read_text(encoding="utf-8"), "app")
    armar = app.split("function armarGeo() {")[1].split("\n  let firmaGeo")[0]
    assert "if (!N) return;" not in armar
    con_base, sin_base = armar.split("\n    }\n", 1)  # the block that needs the base map closes at the function's indent
    assert "if (N) {" in con_base and "M.base.fuentes" in con_base and '$("margen").hidden = false' in con_base
    for rotulo in ('rotulo("eje-t"', 'rotulo("ahora"', 'rotulo("fondo-prof"'):
        assert rotulo in sin_base and rotulo not in con_base, rotulo
    assert '(M.base ? "; relieve sin exagerar" : "")' in app  # no relief, no claim about it
    assert "if (/libre/.test(ancla)) { ACTOS[0].fin(); girarLectura(ACTOS[0].lect, 0); irLibre(); }" in app
    assert '$("lect-0").onclick = () => { if (est.morph <= .5) ponerLectura(0); };' in app


def test_the_place_under_the_wells_comes_from_the_base_map_and_names_its_sources():
    """Part D: relief, north, scale and a line per source with its licence; the motor asks the core for elevations."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    for pieza in ('<details class="fuentes" id="fuentes"><summary><span class="s-largo">Mapa base: fuentes y licencias</span>',
                  '<span class="s-corto">Fuentes</span><svg class="ico" aria-hidden="true"><use href="#i-info"/></svg></summary>',
                  '<svg id="norte"', 'aria-label="Norte"', '<div class="regla-km"', 'id="regla-txt"'):
        assert pieza in tpl, pieza
    app, motor = _script(tpl, "app"), _script(tpl, "motor")
    assert "for (const f of M.base.fuentes)" in app and '". Licencia: " + g.f.licencia + ". Bajado el "' in app
    assert "wiki/hallazgos/mapa_base.md" in app and "fuera de la hoja" in app
    assert 'agua: "lagos, embalses y cauces anchos"' in app  # the layer as the exporter names it: it carries wide channels too
    assert base_mapa.CAPA_ES["agua"].lower() == "lagos, embalses y cauces anchos"
    assert "Nucleo.cotasBocas(M)" in motor and "Nucleo.cotasBocas(M).fuera" in app
    assert "abrirBase" in _script(tpl, "nucleo") and "D.base ? abrirBase(D.base) : null" in tpl


def test_small_screens_keep_the_margin_the_panels_and_the_light_in_range():
    """Part D on a phone: panels rest on the measured timeline, the margin moves up, one gain dims every well alike."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    angosta = re.search(r"@media \(max-width: 760px\) \{\n  \.titulo \.nombre.*?\n\}\n", tpl, re.S).group(0)
    assert ".relato, .taller { bottom: calc(var(--alto-tiempo, 176px) + 4px); }" in angosta
    assert re.search(r"\.margen \{[^}]*top: 10px; bottom: auto;", angosta)
    # the credit of each source is a condition of use: the list is never hidden, on a phone it opens as a sheet
    assert not re.search(r"\.fuentes \{[^}]*display: none", tpl)
    assert ".margen .fuentes .s-corto { display: inline; }" in angosta
    assert re.search(r"\.margen \.fuentes\[open\] \{ position: fixed;[^}]*overflow: auto; \}", angosta)
    app, motor = _script(tpl, "app"), _script(tpl, "motor")
    assert 'setProperty("--alto-tiempo"' in app and "lejosDelReloj(k)" in app
    # the gain depends on the view only, never on the well: brightness still compares wells with each other
    assert re.search(r"function apretado\(\) \{ return Math\.max\(\.5, Math\.min\(1, Math\.sqrt\([^{}]*cam\.dist[^{}]*\)\)\); \}", motor)
    assert 'pr.u("u_tenue"), (1 - .72 * est.morph * est.ver[1]) * apretado()' in motor


def test_template_ids_are_unique():
    """getElementById answers with the first match: a repeated id silently points a handler at the wrong element."""
    ids = re.findall(r'\bid="([^"]+)"', mundo.TEMPLATE.read_text(encoding="utf-8"))
    assert len(ids) > 100 and sorted({i for i in ids if ids.count(i) > 1}) == []


def test_the_timeline_is_the_chart_and_reads_from_the_core():
    """Slice D3: display date and counters, basin oil by operator and frac jobs per month, one tooltip, a table."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    css, app = tpl.split("</style>")[0], _script(tpl, "app")
    angosta = re.search(r"@media \(max-width: 760px\) \{\n  \.titulo \.nombre.*?\n\}\n", tpl, re.S).group(0)
    # type scale of the plan: the date at 56 (36 on a phone), the counters at 36 (24 on a phone), both in the serif
    assert ".tiempo #mes { font: 400 56px/1 var(--relato);" in css and ".tiempo #mes { font-size: 36px; }" in angosta
    assert re.search(r"\.tiempo \.conteo b \{[^}]*font: 400 36px/1 var\(--relato\)", css) and ".tiempo .conteo b { font-size: 24px; }" in angosta
    # the chart is drawn on a canvas that stays out of the reading order; the native range input is the keyboard path
    pista = re.search(r'<div class="pista" id="pista">(.*?)\n      </div>', tpl, re.S).group(1)
    assert '<canvas id="serie" aria-hidden="true">' in pista and '<input type="range" id="cursor"' in pista
    assert 'aria-label="Mes"' in pista and "aria-valuetext" in app
    # every series comes from the verified core, none is recounted in the page
    for llamada in ("Nucleo.fracsPorMes(M)", "Nucleo.llegadasPorMes(M)", "Nucleo.pico(fracsMes)", "Nucleo.partesCuenca(M, j)"):
        assert llamada in app, llamada
    assert "M.cuenca.kbbl" in app and "rezago_carga_desde" in app
    # one axis per plot: the frac bars have their own band and their own caption, and say the lag
    assert '<p class="eje-f" id="eje-f"><span>Fracturas por mes<span id="pico-f"></span></span>' in tpl
    assert "Rayado: las fracturas recientes se cargan con rezago" in tpl
    assert "Las fracturas recientes se cargan con rezago: este recuento puede crecer." in app
    # the tooltip and the table are built from text nodes, never from markup
    lectura = app.split("function mirar(j, fija) {")[1].split("function abrirTabla() {")
    assert "innerHTML" not in lectura[0] and "innerHTML" not in lectura[1].split('$("ver-tabla").onclick')[0]
    # the table view: a named modal dialog with the same series, opened by a button
    assert ('<button type="button" id="ver-tabla" aria-haspopup="dialog"><svg class="ico" aria-hidden="true">'
            '<use href="#i-tabla"/></svg>Ver la tabla</button>') in tpl
    assert re.search(r'<dialog class="planilla" id="planilla" aria-labelledby="planilla-t">\s*<div class="planilla-cab"><h2 id="planilla-t">', tpl)
    assert "d.showModal()" in app and 'if ($("planilla").open) return;' in app
    # dragging on the chart moves time, hovering only reads
    assert 'pista.addEventListener("pointerdown"' in app and "else if (toma === null && e.pointerType !== \"touch\") mirar(" in app


def test_scene_events_are_functions_of_the_month_and_say_what_they_are_not():
    """Slice D3: a frac pulse of fixed size, a strike of light for a new well and the ember of cumulative oil."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    motor, app = _script(tpl, "motor"), _script(tpl, "app")
    leyenda = re.search(r'<details class="leyenda".*?</details>', tpl, re.S).group(0)
    for frase in ("Un pulso blanco en el suelo es una fractura en su fecha. Su tamaño es fijo: no es un frente.",
                  "Un trazo vertical de luz es un pozo nuevo: el mes de su primera fractura o de su primera producción, lo que venga antes.",
                  "La brasa del suelo es el petróleo acumulado de cada pozo hasta el mes del reloj.",
                  "no es un área drenada."):
        assert frase in leyenda, frase
    # the pulse: its radius depends on the camera distance only, its light on the age; nothing grows with the age
    frac = re.search(r"const VS_FRAC = CAB \+ `(.*?)`;", motor, re.S).group(1)
    radio = re.search(r"float r = ([^;]*);", frac).group(1)
    assert "edad" not in radio and "u_dia" not in radio and "exp(-edad / 9.)" in frac
    # the ember: cumulative barrels of the core, a fixed footprint, and the brightness curve applied to the sum
    brasa = re.search(r"const VS_BRASA = CAB \+ `(.*?)`;", motor, re.S).group(1)
    assert "Nucleo.acumuladoBbl(M)" in motor and "a_esq * u_brasa.x" in brasa and "u_mes" in brasa
    assert "gl.blendFunc(gl.ONE, gl.ONE)" in motor.split("function sumarBrasa() {")[1].split("\n    }")[0]
    assert "e / (e + u_ascua.x)" in motor and re.search(r"const BRASA_KM = \.6, BRASA_MBBL = 1\.2", motor)
    assert 'fmt(motor.BRASA_KM * 1000, 0) + " m"' in app and '$("ley-brasa").hidden = true' in app
    # the strike: lit by the clock month minus the well's first month, so a paused frame is exact
    llega = re.search(r"const VS_LLEGA = CAB \+ `(.*?)`;", motor, re.S).group(1)
    assert "if (edad < 0. || k <= 0." in llega
    # it lasts one month, read off the shader's own expression: on a whole month the wells of the month before are
    # out, and so is a well of a windowed sample that started before the first frame (first month below zero)
    largo = re.search(r"float edad = u_mes - a_meta\.y, k = ([^;]+);", llega).group(1)

    def apagado(mes, primer):
        edad = mes - primer
        return edad < 0 or eval(largo, {"edad": edad}) <= 0

    assert not apagado(7, 7) and not apagado(7.9, 7) and apagado(7, 6) and apagado(0, -1) and apagado(6.9, 7)
    assert "Nucleo.primerMes(M, p)" in motor


def test_tour_has_its_six_acts_in_order():
    app = _script(mundo.TEMPLATE.read_text(encoding="utf-8"), "app")
    assert re.findall(r'\btitulo: "([^"]+)"', app) == ["La cuenca", "Un evento", "Del mapa al estimador", "El cierre",
                                                        "Lo que no se ve", "Tu turno"]
    assert '"Acto " + (i + 1) + " de " + ACTOS.length' in app   # the step text follows the list
    # act 4 reads the closure table of the mart, act 5 turns medido and supuesto off and act 6 offers both tools
    assert "pub.cierre.map(" in app and "ponerCapa(1, false" in app and "ponerCapa(2, false" in app
    assert re.search(r'acciones: true', app) and 'id="ir-plantar"' in mundo.TEMPLATE.read_text(encoding="utf-8")
    # the month 6 gap is small under every control and one interval includes zero: the page never says it stays open
    assert "no llega a cero" not in mundo.TEMPLATE.read_text(encoding="utf-8") and "control que se use: casi se cierra" in app


def test_tools_carry_the_labels_of_the_plan_under_their_tag():
    """Plan section 3: what each tool is, said next to it, and never a claim the data cannot back."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    cuerpo = tpl.split('<div class="mundo"')[1].split("<footer")[0]
    plantar = cuerpo.split('id="panel-plantar"')[1].split('id="panel-fisica"')[0]
    fisica = cuerpo.split('id="panel-fisica"')[1]
    marca = '<span class="marca {0}">{0}</span>'
    assert marca.format("medido") + "aplica la huella medida en la cuenca a estos padres; no es un pronóstico de este pozo" in plantar
    assert marca.format("supuesto") + "volumetría de libro con tus supuestos; no es un área de drenaje medida" in fisica
    assert fisica.count('<span class="marca supuesto">supuesto</span>') >= 2 and "marca medido" not in fisica
    assert "cota superior" in plantar and "r = √(k·t / (948·φ·μ·ct))" in fisica and "r = 2·√(η·t)" in fisica
    assert "A = Np·Bo / (h·φ·(1 − Sw)·FR); ancho = A / rama" in fisica and "sin orientación" in fisica
    app = _script(tpl, "app")
    for frase in ("Es un techo, no una estimación de la pérdida.", "Esta cuenta no tiene intervalo propio.",
                  "hacia dónde va no se publica", "sin orientación", "no llega en la vida de un pozo",
                  "frente supuesto", "pozo hijo hipotético"):
        assert frase in app, frase
    assert "perdido para siempre" not in tpl and "efecto descartado" not in tpl


def test_tools_call_the_verified_core_instead_of_redoing_the_arithmetic():
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    app, nucleo = _script(tpl, "app"), _script(tpl, "nucleo")
    for f in ("plantar", "costoDeDiferir", "valorCota", "tiempoARadioH", "permeabilidadARadioMd", "radioFt", "anchoDrenadoM", "vecino"):
        assert "Nucleo." + f + "(" in app, f
        assert re.search(r"\bfunction " + f + r"\(", nucleo), f
    # the constants of the three formulas live in the core, which the self-test checks against Python
    assert "948" not in app and "Math.pow(1 +" not in app and "6.2898" not in app
    # no figure on screen is a core result reworked in the app: not the oil per parent, not the permeability for a month
    assert "diferido_bbl /" not in app and "/ H_MES" not in app and "r.por_padre_bbl" in app
    # nor the gap between the two medians: the labels read the core's answer
    assert re.search(r"\bfunction brechaMediana\(", nucleo) and "Nucleo.brechaMediana(" in _script(tpl, "motor")
    assert "medianas.brecha" in app and not re.search(r"\bmc\[[^\]]+\] - mk\[", app)
    assert "948 * phi * muCp * ctPsi" in nucleo


def test_the_front_is_a_field_from_the_core_with_real_neighbours_and_no_direction():
    """Plan D4: the line-source field, the arrivals at the real neighbours and the chart; every number from the core."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    app, nucleo, motor = _script(tpl, "app"), _script(tpl, "nucleo"), _script(tpl, "motor")
    fisica = tpl.split('<div class="mundo"')[1].split("<footer")[0].split('id="panel-fisica"')[1]
    for f in ("e1", "caidaAdim", "perfilCaida", "padsEnRadio"):
        assert re.search(r"\bfunction " + f + r"\(", nucleo), f
    # the shader has no physics of its own: it reads the profile the core sampled, and the app draws nothing but it
    sombra = motor.split("const FS_FRENTE")[1].split("`;")[0]
    assert "texture(u_perfil" in sombra and "exp(" not in sombra and "Nucleo.perfilCaida(N_PERFIL, S_MAX)" in motor
    assert "Nucleo.padsEnRadio(M, p, VECINDAD_KM, mes)" in app and "VECINDAD_KM = M.meta.vecindad_km" in app
    assert "Nucleo.tiempoARadioH(g.km * KM_FT, q.k, q.phi, q.mu, q.ct)" in app
    taller = app.split("Física con tus supuestos")[1].split("Cámara: arrastrar gira")[0]
    assert "Nucleo.caidaAdim(1) / Nucleo.caidaAdim(.1)" in taller and "Math.exp(" not in taller and "948" not in taller
    # the chart: every line is the core's radius, on two logarithmic axes, with a text reading next to it
    regla = app.split("function dibujarRegla()")[1].split("\n  function ")[0]
    assert "Nucleo.radioM(k, t, q.phi, q.mu, q.ct)" in regla and "Math.sqrt(" not in regla
    # the canvas is a picture of numbers the panel also says in words (the reading and the list), and the slider under it
    # is the control a keyboard or a screen reader uses
    assert '<canvas id="fi-regla" aria-hidden="true">' in fisica and '<p id="fi-lee">' in fisica
    assert '<p class="total" id="fi-llega" aria-live="polite">' in fisica and '<p id="fi-cuenta">' in fisica
    assert '$("fi-t").setAttribute("aria-valuetext", tiempoTxt(FI.tH))' in app
    campo = re.search(r'<input[^>]*id="fi-t"[^>]*>', fisica).group(0)
    assert 'type="range"' in campo and 'value="0"' in campo and "H_MES * Math.pow(10, leer(\"fi-t\"))" in app
    assert re.search(r'<button type="button" id="fi-correr"', fisica) and 'reducido ? "Saltar a 30 años"' in app
    # the list: distance is data, the arrival is an assumption, and matrix permeability leaves it empty in words
    assert re.search(r'<ol class="llegadas" id="fi-llegadas"', fisica)
    cab = fisica.split('id="fi-cab"')[1].split("</p>")[0]
    assert '<span class="marca dato">dato</span>' in cab and '<span class="marca supuesto">supuesto</span>' in cab
    for frase in ("la lista queda vacía: el frente no llega en la vida de un pozo", "No hay bocas de otro pad que ya hayan entrado en producción",
                  "Cada fila es un pad, nombrado por su pozo más cercano"):
        assert frase in app, frase
    for frase in ("Δp ∝ E₁(r² / (4·η·t))", "No tiene borde", "sin orientación", "no un pronóstico de interferencia"):
        assert frase in fisica, frase
    # no permeability is inferred from a measured distance or gap: the only inverse is the one for 1 km in a month
    assert app.count("Nucleo.permeabilidadARadioMd(") == 1 and "Nucleo.permeabilidadARadioMd(KM_FT, H_MES," in app
    # the marks of the scene are rings under wellheads: nothing joins two wells
    marcas = app.split("function ponerMarcas()")[1].split("\n  function ")[0]
    assert "est.anillos.push(" in marcas and "motor.linea" not in marcas and "trazo(" not in marcas


def test_a_paused_clock_is_a_whole_month_and_a_new_anchor_is_computed_before_it_is_drawn():
    """Two rules of the app code that a browser smoke exercises: what is on screen belongs to the month on the clock.

    Pausing snaps the clock to a whole month, so the date, the counters, the events of the scene and the list of pads
    read the same month. And picking another well recomputes before drawing: the rings of the width view are built
    from the values of the new well, not from those of the one before.
    """
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    assert "function andar(si) { if (!si && T.andando) ponerMes(Math.round(T.mes)); T.andando = si;" in tpl
    assert "Math.floor(T.mes" not in tpl and tpl.count("const mes = Math.round(T.mes), otros = ") == 1
    for nombre in ("pozoFisica", "tomarFisica"):
        cuerpo = tpl.split(f"function {nombre}(")[1].split("\n  function ")[0]
        assert "calcularFisica(); dibujarFisica(); encuadrarFisica();" in cuerpo, nombre


def test_search_is_a_named_field_and_the_matching_lives_in_the_core():
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    assert '<input type="search" id="busca" aria-label="Buscar un pozo, un \u00e1rea o un operador"' in tpl
    assert '<p id="busca-estado" aria-live="polite" hidden>' in tpl
    assert '<p id="resalte" hidden><span class="marca dato">dato</span>' in tpl
    app, nucleo = _script(tpl, "app"), _script(tpl, "nucleo")
    assert "Nucleo.buscar(" in app and "Nucleo.indiceBusqueda(" in app
    # the search key is built in one place, the one the self-test compares with Python
    assert ".normalize(" not in app and nucleo.count('.normalize("NFD")') == 1
    assert 'ver("b\u00fasqueda "' in nucleo


def test_layer_toggles_and_tool_tabs_are_named_controls():
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    capas = re.findall(r'<button type="button" id="capa-(\d)" aria-pressed="true" aria-label="Capa (\w+)">'
                       r'<span class="marca (\w+)">(\w+)</span></button>', tpl)
    assert capas == [("0", "dato", "dato", "dato"), ("1", "medido", "medido", "medido"),
                     ("2", "supuesto", "supuesto", "supuesto")]
    assert tpl.count('role="tablist"') == 1
    tabs = re.findall(r'<button type="button" role="tab" id="tab-(\w+)" aria-controls="panel-(\w+)" aria-selected="(\w+)"', tpl)
    assert tabs == [("explorar", "explorar", "true"), ("plantar", "plantar", "false"), ("fisica", "fisica", "false")]
    for nombre, _, _ in tabs:
        assert re.search(r'role="tabpanel" id="panel-%s" aria-labelledby="tab-%s"' % (nombre, nombre), tpl)
    app = _script(tpl, "app")
    assert "/^(ArrowLeft|ArrowRight|Home|End)$/" in app   # the tab list moves with the arrow keys
    assert "u_ver" in _script(tpl, "motor")   # the three layers reach the shaders, they are not a style on the labels


def test_value_sliders_start_at_the_example_of_the_informe():
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    inf = (ROOT / "pipeline" / "informe_template.html").read_text(encoding="utf-8")

    def rango(html, ident):
        campo = re.search(r'<input[^>]*id="%s"[^>]*>' % ident, html).group(0)
        return tuple(re.search(r'\b%s="([^"]+)"' % a, campo).group(1) for a in ("min", "max", "step"))

    for mio, suyo in (("pl-precio", "c-precio"), ("pl-tasa", "c-tasa"), ("pl-rezago", "c-rezago")):
        assert rango(tpl, mio) == rango(inf, suyo), mio

    def arranque(ident):
        return float(re.search(r'id="%s"[^>]*\bvalue="([^"]+)"' % ident, tpl).group(1))

    assert (arranque("pl-precio"), arranque("pl-tasa") / 100, arranque("pl-rezago")) == (
        informe.PRECIO_EJEMPLO, informe.TASA_EJEMPLO, informe.REZAGO_EJEMPLO)


def test_index_informe_and_readme_point_to_the_page():
    indice = (ROOT / "pipeline" / "report_template.html").read_text(encoding="utf-8")
    inf = (ROOT / "pipeline" / "informe_template.html").read_text(encoding="utf-8")
    assert indice.count('href="mundo.html"') == 3   # la navegación, el enlace de la primera pregunta de la historia y la línea de recorrido del tablero
    assert 'href="mundo.html#libre&amp;hoja=plantar"' in inf
    app = _script(mundo.TEMPLATE.read_text(encoding="utf-8"), "app")
    assert "/libre/.test(ancla)" in app and re.search(r"hoja=\(plantar\|fisica\)", app)   # the link of the informe lands on the tool
    primero = README.read_text(encoding="utf-8").split("## Mirá esto primero")[1].split("\n## ")[0]
    assert len(re.findall(r"^- `site/mundo\.html`: ", primero, re.M)) == 1
    for pagina, enlace in (("index.html", 'href="mundo.html"'), ("informe.html", 'href="mundo.html#libre&amp;hoja=plantar"')):
        generada = ROOT / "site" / pagina
        if generada.exists():
            assert enlace in generada.read_text(encoding="utf-8"), pagina


@needs_wh
def test_top_level_keys(data):
    assert set(data) == {"meta", "pozos", "caudal", "fracs", "eventos", "curva", "brecha", "pub", "cuenca", "acto2",
                         "autotest", "base", "foto"}
    assert list(data)[-2:] == ["base", "foto"]   # the map sheet and the imagery are the heaviest parts and go last
    assert set(data["eventos"]) == {"padre", "hijo", "mes", "km", "base", "flags", "indice"}
    assert set(data["pozos"]) == {"id", "sigla", "op", "area", "pad", "lon", "lat", "mes0", "frac", "md", "rama",
                                  "etapas", "arena", "agua", "np"}


@needs_wh
def test_timeline_and_wells_are_those_of_the_replay(data):
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        r = replay.collect(con)
    finally:
        con.close()
    assert data["meta"]["meses"] == r["meta"]["meses"]
    assert data["pozos"]["id"] == [p["id"] for p in r["pozos"]]
    assert data["cuenca"] == r["cuenca"]
    assert data["meta"]["meses"][-1] == data["meta"]["mes_datos"]
    # both pages count the same producing wells, month by month: a rate above zero here, bit 1 of estado there
    n, nm = data["meta"]["n_pozos"], len(data["meta"]["meses"])
    caudal, estado = decode(data["caudal"], "H"), decode(r["estado"], "B")
    aqui = [sum(1 for p in range(n) if 0 < caudal[p * nm + m] != mundo.SIN_FILA) for m in range(nm)]
    alla = [sum(1 for p in range(n) if estado[p * nm + m] & 1) for m in range(nm)]
    assert aqui == alla and max(aqui) > 2000


@needs_wh
def test_pozo_columns(data):
    p, m = data["pozos"], data["meta"]
    n = m["n_pozos"]
    assert n == len(p["id"]) == len(set(p["id"])) > 0
    assert all(len(col) == n for col in p.values())
    assert all(0 <= o < len(m["operadores"]) for o in p["op"]) and all(0 <= a < len(m["areas"]) for a in p["area"])
    assert all(-80 < lon < -60 for lon in p["lon"]) and all(-45 < lat < -30 for lat in p["lat"])
    assert all(x is None or x > 0 for x in p["md"])
    assert m["profundidad"] is True and sum(1 for x in p["md"] if x) > 0.9 * n
    assert all(x is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) for x in p["frac"])
    assert all(x >= 0 for x in p["np"])


@needs_wh
def test_caudal_matches_the_warehouse_and_marks_missing_rows(data):
    n, nm = data["meta"]["n_pozos"], len(data["meta"]["meses"])
    caudal = decode(data["caudal"], "H")
    assert len(caudal) == n * nm
    k = nm - 13
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        filas = con.execute("""
            select f.pozo_id, f.petroleo_m3 / f.dias_mes * 6.2898
            from fct_produccion f join int_pozo_ubicacion u using (pozo_id)
            where f.mes = ?::date and f.petroleo_m3 is not null""", [data["meta"]["meses"][k] + "-01"]).fetchall()
    finally:
        con.close()
    ids = {pid: i for i, pid in enumerate(data["pozos"]["id"])}
    assert len(filas) > 1000
    chicos = 0
    for pid, bbl_d in filas:
        v = caudal[ids[pid] * nm + k]
        if 0 < bbl_d < 0.05:   # a month with oil under half a step takes the smallest step instead of a zero
            assert v == 1
            chicos += 1
        else:
            assert v / mundo.ESCALA_CAUDAL == pytest.approx(bbl_d, abs=0.05 + 1e-9)
        assert (v > 0) == (bbl_d > 0)
    assert chicos < 0.02 * len(filas)
    con_fila = {ids[pid] for pid, _v in filas}
    assert all((caudal[p * nm + k] == mundo.SIN_FILA) == (p not in con_fila) for p in range(n))
    assert max(v for v in caudal if v != mundo.SIN_FILA) < mundo.SIN_FILA - 1  # nothing was clipped


@needs_wh
def test_eventos_are_the_near_and_control_events(data, ev):
    ne, n, nm = data["meta"]["n_eventos"], data["meta"]["n_pozos"], len(data["meta"]["meses"])
    assert all(len(ev[k]) == ne for k in ("padre", "hijo", "mes", "km", "base", "flags"))
    assert len(ev["indice"]) == ne * ANCHO
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        cuenta = dict(con.execute("select banda, count(*) from int_interferencia_evento group by 1").fetchall())
    finally:
        con.close()
    cercanos = sum(1 for f in ev["flags"] if not f & 1)
    assert cercanos == cuenta["cercano"] == data["pub"]["n_cercanos"]
    assert ne - cercanos == cuenta["control"]
    assert max(ev["padre"]) < n and max(ev["hijo"]) < n and max(ev["mes"]) < nm
    for e in range(ne):
        km = ev["km"][e] / 1000
        assert (km < 1.0005) if not ev["flags"][e] & 1 else (1.9995 <= km < 5.0005)
        assert ev["flags"][e] >> 1 < len(mundo.GRUPOS)


def test_a_rate_that_does_not_fit_stops_the_export_instead_of_being_clipped():
    assert mundo.codificar_caudal(5395.71) == 53957
    assert mundo.codificar_caudal(0) == 0
    # a month with oil is never a zero: the smallest positive rate takes the smallest step
    assert mundo.codificar_caudal(0.0001) == mundo.codificar_caudal(0.049) == mundo.codificar_caudal(0.1) == 1
    assert mundo.codificar_caudal(0.151) == 2
    for malo in (6553.5, 9000.0, -1.0):
        with pytest.raises(ValueError):
            mundo.codificar_caudal(malo)

@needs_wh
def test_indices_saturate_only_above_the_documented_cap(data, ev):
    """Uint16 cannot hold an index above 6,5534: those are stored as the cap, the rest within half a unit."""
    ids = {pid: i for i, pid in enumerate(data["pozos"]["id"])}
    mi = {m: i for i, m in enumerate(data["meta"]["meses"])}
    pos = {(ev["padre"][e], ev["mes"][e], ev["flags"][e] & 1): e for e in range(data["meta"]["n_eventos"])}
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        filas = con.execute("""
            select padre, strftime(mes_frac, '%Y-%m'), banda, k, indice from int_interferencia_mes
            where banda in ('cercano', 'control') and indice is not null and k between ? and ?""",
                            [mundo.K_MIN, mundo.K_MAX]).fetchall()
    finally:
        con.close()
    assert len(filas) > 100_000
    topados = 0
    for padre, mes, banda, k, ind in filas:
        got = ev["indice"][pos[(ids[padre], mi[mes], int(banda == "control"))] * ANCHO + k - mundo.K_MIN]
        if ind * mundo.ESCALA_INDICE > mundo.TOPE_INDICE:
            topados += 1
            assert got == mundo.TOPE_INDICE
        else:
            assert abs(got - ind * mundo.ESCALA_INDICE) <= 0.5 + 1e-6
    assert 0 < topados < len(filas) / 100
    assert max(c for banda in data["curva"].values() for c in banda) * mundo.ESCALA_INDICE < mundo.TOPE_INDICE / 2


@needs_wh
def test_embedded_indices_reproduce_the_published_medians(data, ev):
    """The medians the page draws come from the events it embeds; they must be the ones of the marts."""
    ne = data["meta"]["n_eventos"]
    for banda, es_control in (("cercano", 0), ("control", 1)):
        sel = [e for e in range(ne) if ev["flags"][e] & 1 == es_control]
        for k in range(mundo.K_MIN, mundo.K_MAX + 1):
            got = mundo.mediana_indices(ev["indice"], ne, sel, k)
            assert got == pytest.approx(data["curva"][banda][k - mundo.K_MIN], abs=1e-4)
    for g in range(len(mundo.GRUPOS)):
        cerca = [e for e in range(ne) if ev["flags"][e] == g << 1]
        ctrl = [e for e in range(ne) if ev["flags"][e] == g << 1 | 1]
        for k in range(mundo.K_MIN, mundo.K_MAX + 1):
            got = mundo.mediana_indices(ev["indice"], ne, cerca, k) - mundo.mediana_indices(ev["indice"], ne, ctrl, k)
            assert got == pytest.approx(data["brecha"][g][k - mundo.K_MIN], abs=1.5e-4)


@needs_wh
def test_published_numbers_are_the_headline(data):
    p = data["pub"]
    assert p["brecha_mes1"] == pytest.approx(data["curva"]["cercano"][4] - data["curva"]["control"][4], abs=1e-5)
    assert p["ic5_bajo"] < p["brecha_mes1"] < p["ic5_alto"] < 0
    assert p["brecha_mes1"] < p["brecha_mes1_descontada"] < 0
    assert [c["variante"] for c in p["cierre"]] == ["V0", "V1", "V2", "V3"]
    assert p["dif_ic_bajo_bbl"] < p["dif_bbl"] < p["dif_ic_alto_bbl"] and p["cota_bbl"] > 0


@needs_wh
def test_acto2_event_meets_its_rule(data, ev):
    a, p = data["acto2"], data["pozos"]
    assert len(a["cercanos"]) >= mundo.MIN_PADRES_ACTO2 and len(a["controles"]) >= mundo.MIN_PADRES_ACTO2
    for e in a["cercanos"] + a["controles"]:
        assert ev["hijo"][e] == a["hijo"] and ev["mes"][e] == a["mes"]
        assert mundo.SIN_INDICE not in ev["indice"][e * ANCHO:(e + 1) * ANCHO]
    assert not any(ev["flags"][e] & 1 for e in a["cercanos"]) and all(ev["flags"][e] & 1 for e in a["controles"])
    assert a["fecha"] == p["frac"][a["hijo"]] and a["fecha"][:7] == data["meta"]["meses"][a["mes"]]
    assert a["etapas"] and a["arena"] and a["agua"]
    # no other eligible child is closer to the basin median
    mediana_cuenca = data["curva"]["cercano"][1 - mundo.K_MIN]
    elegido = abs(median(ev["indice"][e * ANCHO + 1 - mundo.K_MIN] for e in a["cercanos"]) / 10000 - mediana_cuenca)
    assert elegido < 0.01


@needs_wh
def test_plantar_at_a_real_child_finds_the_parents_of_the_event_sql(data):
    """Planting where a real child is, in its frac month, must give the near parents the SQL found for it."""
    a, p, nm = data["acto2"], data["pozos"], len(data["meta"]["meses"])
    caudal = decode(data["caudal"], "H")
    inicio = (int(data["meta"]["meses"][0][:4]), int(data["meta"]["meses"][0][5:]))
    r = mundo.plantar(p["lon"][a["hijo"]], p["lat"][a["hijo"]], a["mes"], p["lon"], p["lat"], p["mes0"], caudal, nm,
                      data["brecha"], inicio)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        sql = con.execute("""
            select x.padre, x.km, e.base_m3_d * 6.2898
            from int_par_padre_hijo x join int_interferencia_evento e using (padre, mes_frac)
            where x.hijo = ? and x.km < 1""", [p["id"][a["hijo"]]]).fetchall()
    finally:
        con.close()
    seguros = {pid: base for pid, km, base in sql if abs(km - 1) > 0.002}  # away from the 1 km edge after rounding
    mios = {p["id"][c["p"]]: c["base"] for c in r["cercanos"]}
    assert len(seguros) >= 3 and set(seguros) <= set(mios)
    assert len(mios) - len(seguros) <= len(sql) - len(seguros)
    for pid, base in seguros.items():
        assert mios[pid] == pytest.approx(base, abs=0.06)


@needs_wh
def test_autotest_references_are_recomputed_from_the_embedded_arrays(data):
    t, p, nm = data["autotest"], data["pozos"], len(data["meta"]["meses"])
    caudal = decode(data["caudal"], "H")
    inicio = (int(data["meta"]["meses"][0][:4]), int(data["meta"]["meses"][0][5:]))
    assert len(t["plantar"]) == mundo.AT_POSICIONES and len(t["fisica"]) == 12 and len(t["drenaje"]) == 8
    assert sum(1 for c in t["plantar"] if c["n_cercanos"] > 0) >= 10  # most fixed positions have near parents
    for c in t["plantar"]:
        r = mundo.plantar(c["lon"], c["lat"], c["m"], p["lon"], p["lat"], p["mes0"], caudal, nm, data["brecha"], inicio)
        assert (len(r["cercanos"]), r["n_intermedio"], r["n_control"]) == (c["n_cercanos"], c["n_intermedio"], c["n_control"])
        assert r["diferido_bbl"] == c["diferido_bbl"] and r["por_padre_bbl"] == c["por_padre_bbl"]
        assert (c["por_padre_bbl"] is None) == (c["n_cercanos"] == 0)
    for c in t["fisica"]:
        assert c["k_1km_md"] == mundo.permeabilidad_a_radio_md(1000.0 / mundo.FT_M, c["t_h"], c["phi"], c["mu_cp"], c["ct_psi"])
        # the permeability for a month puts the front at 1 km in exactly that month
        assert mundo.tiempo_a_radio_h(1000.0 / mundo.FT_M, c["k_1km_md"], c["phi"], c["mu_cp"], c["ct_psi"]) == pytest.approx(c["t_h"])
    for c in t["totales"]:
        assert c["kbbl"] * 1000 == pytest.approx(c["suma_bbl_d"], rel=0.01)  # mapped wells against the basin mart
    curva = data["curva"]
    assert t["brecha_mediana"] == mundo.brecha_medianas(curva) and len(t["brecha_mediana"]) == mundo.K_MAX - mundo.K_MIN + 1
    assert t["brecha_mediana"][1 - mundo.K_MIN] == pytest.approx(data["pub"]["brecha_mes1"], abs=1e-5)
    assert mundo.brecha_medianas({"cercano": [0.8, None, 1.0], "control": [1.0, 1.0, None]}) == [pytest.approx(-0.2), None, None]


@needs_wh
def test_autotest_carries_the_split_by_month_and_the_neighbours(data):
    t, p, nm = data["autotest"], data["pozos"], len(data["meta"]["meses"])
    caudal = decode(data["caudal"], "H")
    inicio = (int(data["meta"]["meses"][0][:4]), int(data["meta"]["meses"][0][5:]))
    for c in t["plantar"]:
        r = mundo.plantar(c["lon"], c["lat"], c["m"], p["lon"], p["lat"], p["mes0"], caudal, nm, data["brecha"], inicio)
        assert c["por_mes"] == r["por_mes"] and len(c["por_mes"]) == mundo.K_MAX + 1
        assert sum(c["por_mes"]) == pytest.approx(c["diferido_bbl"])
    assert len(t["vecinos"]) == mundo.AT_VECINOS and len({v["p"] for v in t["vecinos"]}) == mundo.AT_VECINOS
    for v in t["vecinos"]:
        assert (v["q"], v["km"]) == mundo.vecino_otro_pad(v["p"], p["lon"], p["lat"], p["pad"])
        assert p["pad"][v["q"]] != p["pad"][v["p"]] and v["km"] > 0


@needs_wh
def test_autotest_frente_is_recomputed_from_the_embedded_arrays(data):
    t, p, nm = data["autotest"]["frente"], data["pozos"], len(data["meta"]["meses"])
    assert data["meta"]["vecindad_km"] == mundo.VECINDAD_KM
    assert t == mundo.autotest_frente(p, nm)
    assert [c["x"] for c in t["e1"]] == sorted(c["x"] for c in t["e1"]) and t["e1"][0]["x"] < 1 < t["e1"][-1]["x"]
    assert all(c["v"] == mundo.e1(c["x"]) for c in t["e1"]) and all(c["pd"] == mundo.caida_adim(c["s"]) for c in t["caida"])
    assert t["anillo"] == pytest.approx(0.0543, abs=1e-4)
    assert len(t["pads"]) == mundo.AT_PADS and len({c["m"] for c in t["pads"]}) > 1 and len({c["km_max"] for c in t["pads"]}) == 2
    assert sum(1 for c in t["pads"] if c["pads"]) >= mundo.AT_PADS // 2   # most reference wells have neighbours
    for c in t["pads"]:
        assert c["pads"] == mundo.pads_en_radio(c["p"], p["lon"], p["lat"], p["pad"], p["mes0"], c["km_max"], c["m"])
        assert len({p["pad"][g["q"]] for g in c["pads"]}) == len(c["pads"])   # one entry per pad
        for g, h in zip(c["pads"], c["h"]):
            assert p["pad"][g["q"]] != p["pad"][c["p"]] and p["mes0"][g["q"]] <= c["m"] and 0 < g["km"] <= c["km_max"]
            assert h == mundo.tiempo_a_radio_h(g["km"] * 1000.0 / mundo.FT_M, 1.0, 0.08, 0.5, 1.5e-5)
        assert c["h"] == sorted(c["h"])   # nearest first is earliest first


@needs_wh
def test_autotest_serie_is_recomputed_from_the_embedded_arrays(data):
    t, p, nm = data["autotest"]["serie"], data["pozos"], len(data["meta"]["meses"])
    caudal, dias = decode(data["caudal"], "H"), decode(data["fracs"]["dia"], "H")
    inicio = (int(data["meta"]["meses"][0][:4]), int(data["meta"]["meses"][0][5:]))
    assert t == mundo.autotest_serie(p, caudal, nm, data["cuenca"], inicio, dias)
    assert sum(t["fracs_mes"]) == len(dias) and t["pico_fracs"]["n"] == max(t["fracs_mes"]) > 0
    ll = t["llegadas"]
    assert sum(ll["mes"]) + ll["antes"] + ll["sin"] == len(p["id"]) and len(ll["mes"]) == nm
    assert len(t["acumulado"]) >= mundo.AT_ACUMULADO and any(c["bbl"] > 0 for c in t["acumulado"])
    for c in t["partes"]:
        assert sum(c["partes"]) == pytest.approx(1.0) and len(c["partes"]) == len(data["cuenca"]["ops"])


@needs_wh
def test_autotest_search_references_are_those_of_buscar(data):
    t, p, m = data["autotest"]["busquedas"], data["pozos"], data["meta"]
    assert (m["busca_min"], m["busca_max"]) == (mundo.BUSCA_MIN, mundo.BUSCA_MAX)
    assert [c["q"] for c in t] == mundo.consultas_de_prueba(p, m["operadores"], m["areas"])
    for c in t:
        assert {k: v for k, v in c.items() if k != "q"} == mundo.buscar(c["q"], p, m["operadores"], m["areas"])
        assert len(c["pozos"]) == min(c["total"], mundo.BUSCA_MAX)
    assert all(c["total"] >= 1 for c in t[:mundo.AT_BUSQUEDAS])   # each sigla prefix finds at least its own well
    assert t[-4]["operadores"] and t[-3]["areas"][0][1] == max(p["area"].count(a) for a in set(p["area"]))
    assert t[-2]["total"] == t[-1]["total"] == 0 and not t[-1]["areas"] and not t[-1]["operadores"]


@needs_wh
def test_cierre_is_the_closure_mart(data):
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        filas = con.execute("select variante, descripcion, brecha_mes1, brecha_mes6, parte_recuperada "
                            "from mart_decision_cierre order by variante").fetchall()
    finally:
        con.close()
    cierre = data["pub"]["cierre"]
    assert len(cierre) == len(filas) == 4
    for c, (variante, descripcion, b1, b6, parte) in zip(cierre, filas):
        assert (c["variante"], c["control"]) == (variante, descripcion)
        assert (c["brecha1"], c["brecha6"], c["parte"]) == pytest.approx((b1, b6, parte), abs=1e-6)
        assert c["brecha1"] < c["brecha6"] < 0 < c["parte"] < 1   # it closes, and it does not reach zero
    assert cierre[0]["brecha1"] == pytest.approx(data["pub"]["brecha_mes1"], abs=1e-5)   # V0 is the headline control


@needs_wh
def test_two_runs_are_identical_apart_from_generado(payloads):
    a, b = (json.loads(json.dumps(x)) for x in payloads)
    a["meta"].pop("generado")
    b["meta"].pop("generado")
    assert a == b


@needs_wh
def test_hash_covers_the_arrays(data, ev):
    import hashlib
    h = hashlib.sha1(decode(data["caudal"], "H").tobytes())
    for k in ("padre", "hijo", "mes", "km", "base", "flags", "indice"):
        h.update(ev[k].tobytes())
    assert data["meta"]["hash_datos"] == h.hexdigest()[:12]


@needs_wh
@needs_node
def test_fresh_page_passes_its_own_self_test_under_node(data, tmp_path):
    out = tmp_path / "mundo.html"
    mundo.render(data, out)
    t = data["autotest"]["plantar"]
    r = node_autotest(out, [(c["lon"], c["lat"], c["m"]) for c in t])
    assert r["autotest"]["fallas"] == [] and r["autotest"]["ok"] == r["autotest"]["total"] > 100
    assert [len(c["cercanos"]) for c in r["casos"]] == [c["n_cercanos"] for c in t]


@needs_wh
@needs_node
def test_self_test_agrees_when_no_well_falls_inside_the_sheet(data, tmp_path):
    """A sheet far from every well: Python and the page both get no median and no top, and that is agreement."""
    hoja = _hoja_mini()
    ref = mundo.autotest_base(hoja, data["pozos"])
    assert (ref["fuera"], ref["mediana_m"], ref["tope_m"]) == (len(data["pozos"]["id"]), None, None)
    referencias = {k: v for k, v in data["autotest"].items() if k != "foto"}   # the imagery covers the real box only
    otra = dict(data, base=hoja, foto=None, autotest=dict(referencias, base=ref))
    out = tmp_path / "mundo.html"
    mundo.render(otra, out)
    r = node_autotest(out)["autotest"]
    assert r["fallas"] == [] and r["ok"] == r["total"]


@needs_wh
def test_autotest_base_is_recomputed_from_the_embedded_sheet(data):
    """The references of the base map follow the product in the repo, and the wells outside the sheet are counted."""
    hoja, t = data["base"], data["autotest"]["base"]
    assert {k: v for k, v in hoja.items() if k != "relieve_fino"} == json.loads(mundo.BASE_MAPA.read_text(encoding="utf-8"))
    fino = base_mapa.abrir_fino(hoja["relieve_fino"])
    assert hoja["relieve_fino"] == base_mapa.leer_fino() and t["fino"]["celdas"] == fino["z"].size
    assert [q["w"] for q in t["fino"]["puntos"]][:3] == [1, 0, 0] and all(0 < q["w"] < 1 for q in t["fino"]["puntos"][3:])
    z = base_mapa.decodificar_relieve(hoja["relieve"])
    assert (t["celdas"], t["suma"], t["min"], t["max"]) == (z.size, int(z.sum()), hoja["relieve"]["min"], hoja["relieve"]["max"])
    lon0, lat0, lon1, lat1 = hoja["caja"]
    lon, lat = data["pozos"]["lon"], data["pozos"]["lat"]
    fuera = sum(1 for x, y in zip(lon, lat) if not (lon0 <= x <= lon1 and lat0 <= y <= lat1))
    assert t["fuera"] == fuera < len(lon) // 100
    assert len(t["bocas"]) == mundo.AT_BOCAS and len({b["p"] for b in t["bocas"]}) == mundo.AT_BOCAS
    assert hoja["relieve"]["min"] <= t["mediana_m"] <= t["tope_m"] <= hoja["relieve"]["max"]
    assert [q["m"] is None for q in t["puntos"]] == [False, False, False, True, True]
    assert t["capas"]["bloques"]["n"] == len(hoja["bloques"]) and t["localidades"] == len(hoja["localidades"])


# ---- ground imagery ----

def _webp_mini(ancho, alto, relleno=b""):
    """The header of a lossy WebP of the given size and some filler: enough for the size readers, not a picture."""
    cuerpo = b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", ancho, alto) + relleno
    return b"RIFF" + struct.pack("<I", 12 + len(cuerpo)) + b"WEBPVP8 " + struct.pack("<I", len(cuerpo)) + cuerpo


def _foto_mini(carpeta, caja=base_mapa.CAJA):
    """A manifest in the contract of pipeline.base_foto with two header-only images, written under carpeta."""
    imagenes = {}
    for nombre, (ancho, alto) in (("caja", (64, 64)), ("nucleo", (64, 48))):
        datos = _webp_mini(ancho, alto, nombre.encode())
        (carpeta / f"base_foto_{nombre}.webp").write_bytes(datos)
        imagenes[nombre] = {"archivo": f"base_foto_{nombre}.webp", "ancho": ancho, "alto": alto, "bytes": len(datos),
                            "sha256": hashlib.sha256(datos).hexdigest()}
    m = {"v": 1, "caja": list(caja), "nucleo": list(base_foto.NUCLEO), "imagenes": imagenes,
         "escenas": [{"id": "a", "fecha": "2025-12-29"}, {"id": "b", "fecha": "2025-12-30"}, {"id": "c", "fecha": "2025-12-30"}],
         "desde": "2025-12-29", "hasta": "2025-12-30", "atribucion": base_foto.ATRIBUCION,
         "url_licencia": base_foto.URL_LICENCIA, "fecha_descarga": "2026-11-19"}
    ruta = carpeta / "base_foto.json"
    ruta.write_text(json.dumps(m), encoding="utf-8")
    return ruta


def test_clock_month_of_a_date():
    """Month index from the first data month; a date before the data is negative, one after it runs past the end."""
    assert mundo.mes_de_fecha((2011, 4), "2011-04-30") == 0
    assert mundo.mes_de_fecha((2011, 4), "2025-12-29") == 176
    assert mundo.mes_de_fecha((2011, 4), "2011-03-31") == -1
    assert mundo.mes_de_fecha((2011, 4), "2027-01-01") == 189


def test_ground_imagery_is_read_from_its_manifest_and_checked_against_it(tmp_path):
    """No manifest, no imagery; with one, the page embeds the pinned bytes and refuses a file that changed or
    is gone: a manifest that pins an image never builds a page without it."""
    assert mundo.leer_base_foto(tmp_path / "base_foto.json") is None
    ruta = _foto_mini(tmp_path)
    foto = mundo.leer_base_foto(ruta)
    assert [c["nombre"] for c in foto["capas"]] == ["caja", "nucleo"]
    assert [c["caja"] for c in foto["capas"]] == [list(base_mapa.CAJA), list(base_foto.NUCLEO)]
    for c in foto["capas"]:
        datos = (tmp_path / f"base_foto_{c['nombre']}.webp").read_bytes()
        assert base64.b64decode(c["webp"]) == datos and c["sha256"] == hashlib.sha256(datos).hexdigest()
    assert (foto["desde"], foto["hasta"], foto["escenas"]) == ("2025-12-29", "2025-12-30", 3)
    assert (foto["atribucion"], foto["fecha_descarga"]) == (base_foto.ATRIBUCION, "2026-11-19")
    otro = tmp_path / "base_foto_nucleo.webp"
    otro.write_bytes(otro.read_bytes()[:-1] + b"X")   # same length, another content
    with pytest.raises(SystemExit, match="base_foto_nucleo.webp no coincide"):
        mundo.leer_base_foto(ruta)
    otro.write_bytes(otro.read_bytes() + b"X")        # another length
    with pytest.raises(SystemExit, match="base_foto_nucleo.webp no coincide"):
        mundo.leer_base_foto(ruta)
    otro.unlink()
    with pytest.raises(SystemExit, match="falta base_foto_nucleo.webp, que base_foto.json fija"):
        mundo.leer_base_foto(ruta)


def test_autotest_foto_pins_what_the_page_embeds(tmp_path):
    foto = mundo.leer_base_foto(_foto_mini(tmp_path))
    t = mundo.autotest_foto(foto, (2011, 4))
    caja, nucleo = _webp_mini(64, 64, b"caja"), _webp_mini(64, 48, b"nucleo")
    assert t["capas"] == [{"bytes": len(caja), "suma": sum(caja), "ancho": 64, "alto": 64},
                          {"bytes": len(nucleo), "suma": sum(nucleo), "ancho": 64, "alto": 48}]
    assert (t["mes_desde"], t["mes_hasta"], t["escenas"]) == (176, 176, 3)


@needs_wh
def test_payload_carries_the_imagery_only_over_a_base_map_of_the_same_box(tmp_path):
    """The image drapes over the base map's relief with no reprojection: another box is an error, and a page with
    no base map or no manifest has no imagery and no reference for it."""
    ruta = _foto_mini(tmp_path)
    (tmp_path / "otra").mkdir()
    corrida = _foto_mini(tmp_path / "otra", caja=[v + 0.5 for v in base_mapa.CAJA])
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        con_foto = mundo.collect(con, foto_path=ruta)
        sin_manifiesto = mundo.collect(con, foto_path=tmp_path / "no_hay.json")
        sin_mapa = mundo.collect(con, base_path=tmp_path / "no_hay.json", foto_path=ruta)
        with pytest.raises(SystemExit, match="no cubre la caja del mapa base"):
            mundo.collect(con, foto_path=corrida)
    finally:
        con.close()
    assert con_foto["foto"] == mundo.leer_base_foto(ruta)
    assert con_foto["autotest"]["foto"] == mundo.autotest_foto(con_foto["foto"], (2011, 4))
    assert sin_manifiesto["foto"] is None and "foto" not in sin_manifiesto["autotest"] and sin_manifiesto["base"] is not None
    assert sin_mapa["foto"] is None and sin_mapa["base"] is None and "foto" not in sin_mapa["autotest"]


@needs_wh
@needs_node
def test_self_test_reads_the_embedded_imagery_back(data, tmp_path):
    """The page measures the bytes it carries: it agrees with Python on the pinned images and fails on any other."""
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        sin = mundo.collect(con, foto_path=tmp_path / "no_hay.json")
        con_foto = mundo.collect(con, foto_path=_foto_mini(tmp_path))
    finally:
        con.close()
    out = tmp_path / "mundo.html"
    mundo.render(sin, out)
    base = node_autotest(out)["autotest"]
    mundo.render(con_foto, out)
    r = node_autotest(out)["autotest"]
    assert base["fallas"] == [] and r["fallas"] == [] and r["total"] == r["ok"] == base["total"] + 4
    # another image under the same reference, a core tile that leaves the box, and a reference without its image
    cambiada = json.loads(json.dumps(con_foto))
    cambiada["foto"]["capas"][0]["webp"] = base64.b64encode(_webp_mini(64, 64, b"cajb")).decode("ascii")
    mundo.render(cambiada, out)
    assert node_autotest(out)["autotest"]["fallas"] == ["imagen del suelo 0"]
    corrida = json.loads(json.dumps(con_foto))
    corrida["foto"]["capas"][1]["caja"][2] = base_mapa.CAJA[2] + 1
    mundo.render(corrida, out)
    assert node_autotest(out)["autotest"]["fallas"] == ["caja de la imagen"]
    huerfana = dict(con_foto, foto=None)
    mundo.render(huerfana, out)
    assert node_autotest(out)["autotest"]["fallas"] == ["imagen del suelo"]


def test_the_ground_reading_says_what_the_image_is_and_when_it_was_taken():
    """Part E: the image is context with a date. The page states the date in the caption and the legend, warns
    when the clock is on another month, credits the programme and reads every date through the verified core."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    app, motor, nucleo = _script(tpl, "app"), _script(tpl, "motor"), _script(tpl, "nucleo")
    leyenda = re.search(r'<details class="leyenda".*?</details>', tpl, re.S).group(0)
    for frase in ("La imagen del suelo es contexto: muestra el lugar, no mide nada.", "no cambia con el reloj",
                  "Cada punto es la boca de un pozo, en su ubicación de superficie.",
                  "Punto lleno: produjo petróleo este mes.", "Punto apagado: sin petróleo informado este mes.",
                  "Su tamaño es fijo: no es un frente."):
        assert frase in leyenda, frase
    assert '<p class="foto-nota" id="foto-nota" aria-live="polite" hidden></p>' in tpl
    for frase in ('"La imagen es de " + f + " y no cambia con el reloj: las locaciones que ves en el suelo pueden ser '
                  'posteriores al mes que estás mirando."',
                  '" y no cambia con el reloj: un pozo posterior puede no tener todavía su locación en ella."',
                  '"El suelo es una imagen satelital de " + f + ", atenuada."',
                  '"Programa Copernicus de la Unión Europea, Sentinel-2: mosaico de " + fmt(FOTO.escenas, 0)',
                  'con esta atribución: " + FOTO.atribucion', '$("ley-foto-mes").textContent = fotoTxt(true)'):
        assert frase in app, frase
    # the month of the image comes from its dates through the core, never from a literal
    assert "Nucleo.mesDeFecha(M.inicio, FOTO.desde), Nucleo.mesDeFecha(M.inicio, FOTO.hasta)" in app
    assert not re.search(r"diciembre de|2025", tpl) and "Copernicus Sentinel data" not in tpl
    assert "foto: D.base && D.foto ? D.foto : null" in nucleo and "medirWebp" in nucleo
    assert "if (terreno && M.foto) {" in motor   # no image in the payload, no texture and no ground reading


def test_the_ground_reading_keeps_the_camera_and_the_rings_on_the_terrain():
    """Part E: the ground reading draws no depth, so nothing goes there. A flight to a well, a planted well, a
    highlighted group or a pair of wells ends looking at the terrain, the reach ring of a selected well lies on
    the ground around its mouth, and the camera stops once it has reached the terrain."""
    app = _script(mundo.TEMPLATE.read_text(encoding="utf-8"), "app")
    assert "function ySuelo(x, z, y) { return lectura === 2 ? motor.altSuelo(x, z) : y; }" in app
    for vuelo in ("volar(lectura === 2 ? { t: [x, motor.altSuelo(x, z), z], dist: 14, az: cam.az, el: Math.max(cam.el, .6) }",
                  "t: [cx, ySuelo(cx, cz, 0), cz]", "t: [PL.x, ySuelo(PL.x, PL.z, 0), PL.z]",
                  "t: [(x + vx) / 2, ySuelo((x + vx) / 2, (z + vz) / 2, 0), (z + vz) / 2]"):
        assert vuelo in app, vuelo
    # the depth of the reach ring fades with the ground reading, like the plane of the physics tab
    assert "const y = () => -motor.prof(p) * est.ve * est.ver[2] * (1 - est.suelo);" in app
    assert "const planoFisica = () => -motor.prof(FI.p) * est.ve * est.ver[2] * (1 - est.lect) * (1 - est.suelo);" in app
    # the follow settles: below a tenth of a metre it lands on the terrain instead of approaching it forever
    assert "cam.t[1] += Math.abs(d) < 1e-4 ? d : d * Math.min(1, dt * 4);" in app


def test_marks_take_their_colour_from_the_legend_table():
    """Part E: one table of operator pigments. The timeline, the legend and the ground marks read the same names;
    the marks use the lighter step of each pigment, declared next to it."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    css, app = tpl.split("</style>")[0], _script(tpl, "app")
    pigmentos = re.findall(r"--(\w+)-claro: (#[0-9a-f]{6});", css)
    assert [n for n, _ in pigmentos] == ["azul", "rosa", "oliva", "ladrillo", "celeste", "ciruela", "gris"]
    for nombre, _ in pigmentos:
        assert re.search(rf"--{nombre}: #[0-9a-f]{{6}};", css), nombre
    assert "const colorOps = pigmentoOps.map(tinta);" in app
    assert 'pigmentoOps.map(c => { const v = parseInt(tinta(c + "-claro").slice(1), 16);' in app
    assert "motor.ponerTintas(rgb);" in app and not re.search(r"\[\d{2,3}, \d{2,3}, \d{2,3}\]", app)   # no second table


def _oklab(hexa):
    """OKLab coordinates of an sRGB hex colour (Ottosson, 2020)."""
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))]
    l, m, s = ((0.4122214708 * lin[0] + 0.5363325363 * lin[1] + 0.0514459929 * lin[2]) ** (1 / 3),
               (0.2119034982 * lin[0] + 0.6806995451 * lin[1] + 0.1073969566 * lin[2]) ** (1 / 3),
               (0.0883024619 * lin[0] + 0.2817188376 * lin[1] + 0.6299787005 * lin[2]) ** (1 / 3))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def test_mark_colours_can_be_told_apart():
    """Part E: the marks carry the operator by colour alone, so no two of them may sit close. The floor is an
    OKLab distance of 0.13 between any pair; the first table, with every pigment at one lightness, had pairs at 0.08."""
    css = mundo.TEMPLATE.read_text(encoding="utf-8").split("</style>")[0]
    marcas = dict(re.findall(r"--(\w+)-claro: (#[0-9a-f]{6});", css))
    assert len(marcas) == 7
    assert _oklab("#ffffff")[0] == pytest.approx(1, abs=1e-6) and _oklab("#000000") == (0, 0, 0)
    for (a, ca), (b, cb) in itertools.combinations(marcas.items(), 2):
        assert math.dist(_oklab(ca), _oklab(cb)) >= .13, (a, b)
    # the grey of "Otros" carries almost no hue, so it is never read as one of the blues
    assert math.hypot(*_oklab(marcas["gris"])[1:]) < .02


def test_every_icon_comes_from_the_one_sprite():
    """Part F: one icon family. Every icon is a <use> of a symbol in the inline sprite, the symbols share one 20 px
    grid, none is dead weight, and each icon is hidden from assistive tech: a control is named by its text or its
    aria-label, never by its drawing."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    simbolos = re.findall(r'<symbol id="(i-[a-z]+)" viewBox="([^"]+)">', tpl)
    nombres = {n for n, _ in simbolos}
    assert len(simbolos) == len(nombres) >= 20 and tpl.count("<symbol ") == len(simbolos)
    assert {v for _, v in simbolos} == {"0 0 20 20"}
    usados = set(re.findall(r'<use (?:id="[a-z-]+" )?href="#(i-[a-z]+)"/>', tpl)) | set(re.findall(r'"#(i-[a-z]+)"', _script(tpl, "app")))
    assert usados == nombres, usados ^ nombres
    cuerpo = tpl.split("</style>")[1]
    assert cuerpo.count("<use ") == cuerpo.count('<svg class="ico" aria-hidden="true"><use ') >= 25
    # the page stays self-contained: the sprite is inline and nothing points outside the document
    assert not re.search(r'<use [^>]*href="(?!#)', tpl)


def test_the_sky_and_the_haze_are_ambience_and_say_so():
    """Part F: the ground reading draws a sky and a haze toward the horizon. They are drawn only over the satellite
    image in the ground reading, the background and the terrain share one haze colour and one pair of distances (each
    with its own ramp), and the legend says they measure nothing. The shading of the relief is computed from the real relief, and the legend says that too."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    motor = _script(tpl, "motor")
    assert "const FS_CIELO = CAB + `" in motor and "pCielo = programa(VS_PANT, FS_CIELO)" in motor
    assert "const k = foto.k * enSuelo() * est.mapa * (1 - est.morph), th = Math.tan(FOV / 2);\n      if (k <= 0) return;" in motor
    assert "if (terreno) { dibujarFondo(); dibujarMapa(); }" in motor
    assert motor.count("vec3(.76, .80, .81)") == 2
    assert 'gl.uniform2fv(pCielo.u("u_niebla"), niebla());' in motor and 'gl.uniform2fv(pTerreno.u("u_niebla"), niebla());' in motor
    assert ('<li class="ley-suelo"><span class="marca dato">dato</span>El relieve es el de la misión SRTM. Su sombreado se calcula acá, '
            'con luz del noroeste. La bruma del horizonte y el cielo son ambiente: no miden nada.</li>') in tpl
    assert "/* Sombreado: luz del noroeste sobre la pendiente" in motor and "const L = norm([-.62, .6, -.5]);" in motor


def test_the_image_caution_sits_in_the_margin_or_in_the_cartouche():
    """Part F: on a wide screen the caution about the image date sits in the map margin, with the sources and the
    scale; on a phone it sits in the cartouche. It is one element, so its text and its live region are the same in
    both places, and the well card leaves room for the margin at its measured height."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    css, app = tpl.split("</style>")[0], _script(tpl, "app")
    assert tpl.count('id="foto-nota"') == 1
    assert '<div class="margen" id="margen" hidden>\n    <p class="foto-nota" id="foto-nota" aria-live="polite" hidden></p>\n' in tpl
    assert 'const fn = $("foto-nota"), casa = an ? $("margen") : document.querySelector(".titulo");' in app
    assert "if (fn.parentNode !== casa) { if (an) casa.prepend(fn); else casa.append(fn); }" in app
    assert "if (fn.textContent !== nota) { fn.textContent = nota; fn.hidden = !nota; }" in app
    assert css.count("var(--alto-margen, 64px)") == 2 and 'style.setProperty("--alto-margen", Math.round(margen.getBoundingClientRect().height) + "px")' in app
    # one left column: the cartouche, the tour card and the tool panel share a width, and the lens shift knows it
    assert "min-width: min(470px, calc(100vw - 40px));" in css and css.count("width: min(470px, calc(100vw - 40px));") == 3
    assert "const bordeRelato = () => 20 + Math.min(470, window.innerWidth - 40);" in app
    assert "const bordeTaller = () => 20 + Math.min(470, window.innerWidth - 40);" in app


def test_the_help_names_only_keys_the_page_listens_to():
    """Part F: the folded help gives one row per move. Every key it names is read by the keyboard handler, and the
    drag with Shift is the one the pointer handler pans with."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    app = _script(tpl, "app")
    ayuda = re.search(r'<details class="leyenda ayuda" id="ayuda">\n(.*?)</details>', tpl, re.S).group(1)
    assert re.findall(r"<dt>(.*?)</dt>", ayuda) == ["Girar", "Moverte", "Acercarte", "Inclinar"]
    teclas = re.findall(r"<kbd>(.*?)</kbd>", ayuda)
    assert teclas == ["Q", "E", "Mayús", "W", "A", "S", "D", "+", "−", "R", "F"]
    assert "else if (e.shiftKey || e.buttons === 2) desplazar(dx, dy);" in app
    for t in teclas:
        if t != "Mayús":
            assert 'on("%s")' % {"−": "-"}.get(t, t.lower()) in app, t
    assert '<p class="toque">Tocá un pozo para ver su ficha.</p>' in tpl
    assert ".taller .ayuda { display: none; }" in tpl.split("</style>")[0]   # a phone has no keys to list


def test_marks_never_grow_and_plates_that_scroll_say_there_is_more():
    """Part F: on a narrow canvas the marks shrink, by 28 % at most, and never grow, so the size still reads as the
    month's oil. A panel or a card with content left below its edge fades there, and stops fading at the end."""
    tpl = mundo.TEMPLATE.read_text(encoding="utf-8")
    css, motor, app = tpl.split("</style>")[0], _script(tpl, "motor"), _script(tpl, "app")
    assert 'gl.uniform1f(pMarca.u("u_talla"), Math.max(.72, Math.min(1, ancho / est.dpr / 900)));' in motor
    assert "tope, min(1., e.x)), activo) * (sel ? 1.6 : 1.) * u_talla;" in motor
    assert 'const CORREN = [...document.querySelectorAll(".taller .hoja"), $("ficha")];' in app
    assert 'h.classList.toggle("sigue", !h.hidden && h.scrollHeight - h.scrollTop - h.clientHeight > 8);' in app
    assert ".taller .hoja.sigue::after, .ficha.sigue::after {" in css and "pointer-events: none; }\n.ficha.sigue::after" in css


# ---- generated file ----

@needs_site
def test_generated_file_size_and_shape():
    assert SITE.stat().st_size < mundo.MAX_BYTES
    html = SITE.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html")
    assert "/*__DATA__*/null" not in html and "{{" not in html.split("const DATA = ", 1)[0]
    assert html.count("const DATA = ") == 1


@needs_site
def test_generated_file_has_no_remote_urls_and_no_dashes():
    html = SITE.read_text(encoding="utf-8")
    code = html.split("const DATA = ", 1)[0] + re.sub(r"^.*?;\n", "", html.split("const DATA = ", 1)[1], count=1, flags=re.S)
    assert not re.search(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", code, re.I)
    assert not re.search(r"""url\(\s*["']?(?:https?:)?//|@import""", code, re.I)
    assert not re.search(r"<script[^>]+\bsrc=", code, re.I)
    assert chr(0x2013) not in code and chr(0x2014) not in code


@needs_site
def test_generated_payload_matches_the_contract():
    html = SITE.read_text(encoding="utf-8")
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    n, nm, ne = d["meta"]["n_pozos"], len(d["meta"]["meses"]), d["meta"]["n_eventos"]
    assert len(decode(d["caudal"], "H")) == n * nm
    assert len(decode(d["eventos"]["indice"], "H")) == ne * ANCHO
    assert len(decode(d["eventos"]["flags"], "B")) == ne
    assert len(decode(d["fracs"]["pozo"], "H")) == len(decode(d["fracs"]["dia"], "H")) > 0
    assert all(len(col) == n for col in d["pozos"].values())
    # part D: the map sheet in the page is the product in the repo, and every source names its licence
    # part E: the finer relief of the core travels inside it, and it is the product in the repo as well
    fino = d["base"].pop("relieve_fino")
    assert fino == json.loads(base_mapa.FINO.read_text(encoding="utf-8"))
    assert d["base"] == json.loads(mundo.BASE_MAPA.read_text(encoding="utf-8")) and d["base"]["v"] == 1
    assert d["base"]["fuentes"] and all(f["licencia"] and f["organismo"] and f["sha256"] for f in d["base"]["fuentes"])
    assert set(d["autotest"]["base"]["capas"]) == {"rios", "agua", "limites", "bloques"}


@needs_site
@needs_node
def test_generated_page_passes_its_own_self_test_under_node():
    r = node_autotest(SITE)["autotest"]
    assert r["fallas"] == [] and r["ok"] == r["total"] > 100


@needs_site
@needs_node
def test_generated_core_answers_like_python_on_the_tools_of_part_c():
    """The page's own plantar and vecino, run under node on the embedded data, against the Python functions."""
    html = SITE.read_text(encoding="utf-8")
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    p, nm, caudal = d["pozos"], len(d["meta"]["meses"]), decode(d["caudal"], "H")
    inicio = (int(d["meta"]["meses"][0][:4]), int(d["meta"]["meses"][0][5:]))
    hijo, m = d["acto2"]["hijo"], d["acto2"]["mes"]
    casos = [(p["lon"][hijo], p["lat"][hijo], m), (p["lon"][hijo], p["lat"][hijo], nm - 1), (-60.0, -38.0, m)]
    for (lon, lat, mes), js in zip(casos, node_autotest(SITE, casos)["casos"]):
        py = mundo.plantar(lon, lat, mes, p["lon"], p["lat"], p["mes0"], caudal, nm, d["brecha"], inicio)
        assert [c["p"] for c in js["cercanos"]] == [c["p"] for c in py["cercanos"]]
        assert (len(js["intermedios"]), len(js["controles"])) == (py["n_intermedio"], py["n_control"])
        assert (js["n_intermedio"], js["n_control"]) == (py["n_intermedio"], py["n_control"])
        assert js["por_mes"] == pytest.approx(py["por_mes"], rel=1e-9, abs=1e-6)
        assert js["diferido_bbl"] == pytest.approx(py["diferido_bbl"], rel=1e-9, abs=1e-6)
        assert js["por_padre_bbl"] == (None if py["por_padre_bbl"] is None else pytest.approx(py["por_padre_bbl"], rel=1e-9))
    n = d["meta"]["n_pozos"]
    pozos = sorted({hijo, 1, n // 3, n // 2 + 7, n - 2})   # wells the embedded reference list does not cover
    r = subprocess.run([NODE, "-e", NODE_VECINO, str(SITE), json.dumps(pozos)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    for pozo, js in zip(pozos, json.loads(r.stdout)):
        q, km = mundo.vecino_otro_pad(pozo, p["lon"], p["lat"], p["pad"])
        assert js["q"] == q and js["km"] == pytest.approx(km, rel=1e-12)


@needs_site
@needs_node
def test_generated_core_searches_like_python():
    """The page's own search, run under node on the embedded data, against mundo.buscar on queries of every kind."""
    html = SITE.read_text(encoding="utf-8")
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    p, m = d["pozos"], d["meta"]
    n = m["n_pozos"]
    consultas = ["la", "LO", "sa", "1", "(h)", "\u00e9", "s.a.", "  ", p["sigla"][n // 7], p["sigla"][n - 3][2:9].lower(),
                 m["areas"][len(m["areas"]) // 2], m["operadores"][-1].upper(), m["operadores"][0][:3]]
    r = subprocess.run([NODE, "-e", NODE_BUSCAR, str(SITE), json.dumps(consultas)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    hallados = 0
    for c, js in zip(consultas, json.loads(r.stdout)):
        assert js == mundo.buscar(c, p, m["operadores"], m["areas"]), c
        hallados += js["total"] > 0
    assert hallados >= 6


@needs_site
@needs_node
def test_generated_core_builds_the_series_like_python():
    """The page's own series (frac jobs, arrivals, shares, cumulative oil, day to month) against the Python functions."""
    html = SITE.read_text(encoding="utf-8")
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    p, nm, caudal, dias = d["pozos"], len(d["meta"]["meses"]), decode(d["caudal"], "H"), decode(d["fracs"]["dia"], "H")
    inicio = (int(d["meta"]["meses"][0][:4]), int(d["meta"]["meses"][0][5:]))
    n = d["meta"]["n_pozos"]
    e = {"pozos": sorted({3, n // 7, n // 3 + 1, n // 2 + 5, n - 4}), "meses": [0, 1, nm // 3, nm - 2, nm - 1],
         "dias": [1, 44, 400, 3000, int(max(dias))]}   # wells, months and days the embedded reference does not cover
    r = subprocess.run([NODE, "-e", NODE_SERIE, str(SITE), json.dumps(e)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    js = json.loads(r.stdout)
    assert js["fracs"] == mundo.fracs_por_mes(dias, inicio, nm)
    assert js["llegadas"] == mundo.llegadas_por_mes(p, inicio, nm)
    assert js["primeros"] == [mundo.primer_mes(p, q, inicio) for q in e["pozos"]]
    for q, fila in zip(e["pozos"], js["acumulado"]):
        assert fila == pytest.approx([mundo.acumulado_bbl(caudal, nm, q, j, inicio) for j in e["meses"]], rel=1e-12)
    for j, partes in zip(e["meses"], js["partes"]):
        assert partes == pytest.approx(mundo.partes_cuenca(d["cuenca"], j), rel=1e-12)
    assert js["dias"] == pytest.approx([mundo.mes_de_dia(inicio, x) for x in e["dias"]], rel=1e-12)


@needs_site
@needs_node
def test_generated_core_computes_the_front_like_python():
    """The page's own E1, drawdown, sampled profile and neighbour pads, under node, against the Python functions."""
    html = SITE.read_text(encoding="utf-8")
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    p, nm, n = d["pozos"], len(d["meta"]["meses"]), d["meta"]["n_pozos"]
    e = {"x": [1e-9, 3e-4, 0.07, 0.3, 0.999, 1.0, 1.001, 1.7, 4.0, 12.5, 50.0, 300.0], "s": [0.01, 0.3, 0.77, 1.0, 1.3, 1.99],
         "n": 16, "s_max": 2,
         "casos": [(d["acto2"]["hijo"], d["meta"]["vecindad_km"], nm - 1), (d["acto2"]["hijo"], 5.0, nm // 2),
                   (1, 2.0, nm - 1), (n // 3, 0.5, nm - 1), (n // 2 + 7, 3.0, nm - 30), (n - 2, 2.0, 0)]}
    r = subprocess.run([NODE, "-e", NODE_FRENTE, str(SITE), json.dumps(e)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    js = json.loads(r.stdout)
    assert js["e1"] == pytest.approx([mundo.e1(x) for x in e["x"]], rel=1e-12, abs=1e-300)
    assert js["caida"] == pytest.approx([mundo.caida_adim(x) for x in e["s"]], rel=1e-12)
    # the profile is the texture of the field: Float32, sampled at the centre of each cell out to two radii
    assert js["perfil"] == pytest.approx([mundo.caida_adim(2 * (i + 0.5) / 16) for i in range(16)], rel=1e-6)
    hallados = 0
    for (q, km_max, m), pads in zip(e["casos"], js["pads"]):
        py = mundo.pads_en_radio(q, p["lon"], p["lat"], p["pad"], p["mes0"], km_max, m)
        assert [(g["q"], g["n"]) for g in pads] == [(g["q"], g["n"]) for g in py]
        assert [g["km"] for g in pads] == pytest.approx([g["km"] for g in py], rel=1e-12)
        hallados += len(py) > 0
    assert hallados >= 3
