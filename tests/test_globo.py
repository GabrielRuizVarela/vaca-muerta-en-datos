"""Contrato de datos, texto fijo y pagina generada de pipeline/globo.py (site/globo.html). Lo que necesita un warehouse o la pagina
generada se salta solo en un clon sin datos."""
import base64
import json
import re
import shutil
import subprocess
import zlib

import duckdb
import numpy as np
import pytest

from pipeline import fuentes_mundo, globo
from pipeline.cuencas import COLORADO, WYOMING
from pipeline.ingest import DATA, ROOT

SITE = ROOT / "site" / "globo.html"
README = ROOT / "README.md"
NODE = shutil.which("node")
WAREHOUSES = {"vm": DATA / "warehouse.duckdb", "colorado": DATA / "colorado" / "warehouse.duckdb",
              "wyoming": DATA / "wyoming" / "warehouse.duckdb"}

needs_wh = pytest.mark.skipif(not all(p.exists() for p in WAREHOUSES.values()), reason="faltan los warehouses de las tres cuencas")
needs_site = pytest.mark.skipif(not SITE.exists(), reason="site/globo.html no esta generado")
needs_node = pytest.mark.skipif(NODE is None, reason="node no esta instalado")
needs_geo = pytest.mark.skipif(not globo.GEOMETRIA.exists(), reason="falta data/globo_geometria.json")


def decodificar(s, dtype):
    return np.frombuffer(zlib.decompress(base64.b64decode(s)), dtype=dtype)


# ---- texto y plantilla (no necesitan datos) ----

def test_z64_es_zlib_en_base64_y_vuelve_igual():
    a = np.array([0, 1, 65535, 300, 7], dtype="<u2")
    s = globo.z64(globo._h(a))
    assert s == globo.z64(globo._h(a))                      # determinista
    assert np.array_equal(decodificar(s, "<u2"), a)
    assert np.array_equal(decodificar(globo.z64(globo._b(np.array([0, 3, 255]))), np.uint8), [0, 3, 255])


def test_pts_usa_coma_decimal_y_menos_de_teclado():
    assert globo._pts(-0.19926) == "-19,9"
    assert globo._pts(0.0224) == "2,2"
    assert chr(0x2212) not in globo._pts(-0.05)


def test_mediana_indices_salta_meses_sin_dato_y_separa_cercanos_de_controles():
    s = globo.SIN_INDICE
    indice = np.array([[10000, 5000], [20000, s], [30000, 7000], [40000, 9000]], dtype=np.uint16)
    flags = np.array([0, 0, 1, 1], dtype=np.uint8)           # bit 0 = control
    k0 = -globo.K_MIN
    m = np.zeros((4, globo.K_MAX - globo.K_MIN + 1), dtype=np.uint16)
    m[:, k0], m[:, k0 + 1] = indice[:, 0], indice[:, 1]
    assert globo.mediana_indices(m, flags, False, 0) == pytest.approx(1.5)
    assert globo.mediana_indices(m, flags, True, 0) == pytest.approx(3.5)
    assert globo.mediana_indices(m, flags, False, 1) == pytest.approx(0.5)      # el evento sin dato no cuenta


def test_cada_jurisdiccion_de_la_auditoria_tiene_lugar_en_el_globo():
    ids = {r["id"] for r in fuentes_mundo.cargar()}
    assert ids <= set(globo.GEO), ids - set(globo.GEO)
    assert set(globo.GEO) <= ids, "GEO nombra una jurisdiccion que la auditoria no tiene"


@needs_geo
def test_la_geometria_cubre_todo_lo_que_el_mapa_pide_y_dice_de_donde_sale():
    g = json.loads(globo.GEOMETRIA.read_text(encoding="utf-8"))
    for tipo, clave in [v for v in globo.GEO.values() if v] + [v[1] for v in globo.MEDIDAS.values()]:
        assert clave in g["paises" if tipo == "pais" else "unidades"], (tipo, clave)
    f = g["fuente"]
    assert f["licencia"] == "dominio publico" and len(f["paises"]["sha256"]) == 64 and len(f["unidades"]["sha256"]) == 64
    assert "public domain" in f["terminos"]["cita"]
    assert all(a[0] == a[-1] and len(a) >= 4 for u in list(g["paises"].values()) + list(g["unidades"].values()) for a in u["anillos"])


def test_las_jurisdicciones_siguen_la_auditoria_y_colorado_va_aparte():
    jur = globo.jurisdicciones()
    regs = fuentes_mundo.cargar()
    assert [j["id"] for j in jur[:-1]] == [r["id"] for r in regs]
    assert all(j["auditada"] for j in jur[:-1])
    co = jur[-1]
    assert (co["id"], co["auditada"], co["medida"], co["nivel"]) == ("us_co", False, "colorado", "medida_sin_auditar")
    assert co["rotulo"] == globo.ROTULO_COLORADO
    assert {j["medida"] for j in jur if j["medida"]} == {"vaca_muerta", "colorado", "wyoming"}


def _mini():
    def v(**k):
        return {"brecha": -0.199264, "ic_bajo_bloque": -0.274673, "ic_alto_bloque": -0.148105, "se_replica": True, **k}
    return {"cuencas": [
        {"id": "vaca_muerta", "tipo": "caso", "M": {"meta": {"mes_datos": "2026-09"}},
         "veredicto": {"brecha_mes1": -0.229264, "brecha_mes1_descontada": -0.192115}},
        {"id": "colorado", "tipo": "replica", "M": {"meta": {"mes_datos": "2024-12"}}, "veredicto": v()},
        {"id": "wyoming", "tipo": "replica", "M": {"meta": {"mes_datos": "2026-09"}},
         "veredicto": v(brecha=-0.0252, ic_bajo_bloque=-0.0551, ic_alto_bloque=0.0221, se_replica=False)}],
        "lectura": {"replican": 1, "de": 2}}


def test_textos_da_las_cifras_en_castellano_y_cubre_todos_los_marcadores():
    t = globo.textos(_mini())
    assert (t["vm_rango_bajo"], t["vm_rango_alto"]) == ("19", "23")
    assert (t["co_brecha"], t["co_ic_bajo"], t["co_ic_alto"]) == ("-19,9", "-27,5", "-14,8")
    assert (t["wy_brecha"], t["wy_ic_bajo"], t["wy_ic_alto"]) == ("-2,5", "-5,5", "2,2")
    assert (t["replican"], t["de"]) == ("1", "2")
    assert (t["co_lectura"], t["co_replica"], t["wy_lectura"], t["wy_replica"]) == ("se replica", "1", "no se replica", "0")
    assert (t["wy_cero"], t["wy_cero_n"]) == ("el intervalo incluye el cero", "1")
    assert (t["mes_vm"], t["mes_co"], t["mes_wy"]) == ("2026-09", "2024-12", "2026-09")
    marcadores = set(re.findall(r"\{\{(\w+)\}\}", globo.TEMPLATE.read_text(encoding="utf-8")))
    assert marcadores == set(t), (marcadores ^ set(t))


def test_el_texto_fijo_no_dice_que_se_replica_en_conjunto():
    """La regla del estudio: una lectura por cuenca, sin estimacion conjunta; y lo oscuro no es 'no produce'."""
    html = globo.TEMPLATE.read_text(encoding="utf-8")
    assert "Sin estimación conjunta" in html
    assert re.search(r"no publica por pozo", html) and "no produce" in html
    assert "medida, sin registro en la auditoría" in (globo.ROTULO_COLORADO + html)


def test_plantilla_y_modulo_siguen_las_reglas_de_texto():
    for ruta in (globo.TEMPLATE, ROOT / "pipeline" / "globo.py", ROOT / "pipeline" / "globo_geometria.py"):
        texto = ruta.read_text(encoding="utf-8")
        assert chr(0x2013) not in texto and chr(0x2014) not in texto, ruta.name
        assert "TODO" not in texto and "FIXME" not in texto, ruta.name
    html = globo.TEMPLATE.read_text(encoding="utf-8")
    assert not re.search(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", html, re.I)
    assert not re.search(r"""url\(\s*["']?(?:https?:)?//|@import""", html, re.I)
    assert not re.search(r"<script[^>]+\bsrc=", html, re.I)
    assert re.findall(r'<script id="([\w-]+)">', html) == ["datos", "nucleo", "motor", "globo-app"]
    assert html.count("const DATA = ") == 1 and html.count("/*__NUCLEO__*/") == 1 and html.count("/*__MOTOR__*/") == 1


def _script(tpl, nombre):
    return re.search(r'<script id="' + nombre + r'">\n?(.*?)</script>', tpl, re.S).group(1)


@needs_node
def test_el_script_de_la_pagina_parsea_bajo_node(tmp_path):
    js = tmp_path / "app.js"
    js.write_text(_script(globo.TEMPLATE.read_text(encoding="utf-8"), "globo-app"), encoding="utf-8")
    r = subprocess.run([NODE, "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_la_pagina_degrada_sin_webgl2_y_respeta_movimiento_reducido():
    html = globo.TEMPLATE.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in html and "DecompressionStream" in html
    assert 'id="sin-webgl"' in html and "b.sinMotor = true" in html     # la tarjeta con las cifras cuando no hay WebGL2


def test_render_reemplaza_marcadores_escapa_y_respeta_el_tope(tmp_path, monkeypatch):
    d = _mini()
    d["s"] = "</script><!-- x"
    out = tmp_path / "x" / "g.html"
    size = globo.render(d, out)
    html = out.read_text(encoding="utf-8")
    assert size == out.stat().st_size
    assert "{{" not in html and "/*__DATA__*/null" not in html and "/*__NUCLEO__*/" not in html and "/*__MOTOR__*/" not in html
    carga = re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1)
    assert "</script" not in carga and json.loads(carga)["s"] == "</script><!-- x"
    monkeypatch.setattr(globo, "MAX_BYTES", 10)
    with pytest.raises(SystemExit):
        globo.render(d, tmp_path / "g2.html")


def test_render_falla_con_un_marcador_desconocido(tmp_path, monkeypatch):
    plantilla = tmp_path / "t.html"
    plantilla.write_text("<p>{{no_existe}}</p>", encoding="utf-8")
    monkeypatch.setattr(globo, "TEMPLATE", plantilla)
    with pytest.raises(Exception):
        globo.render(_mini(), tmp_path / "g.html")


def test_readme_e_indice_apuntan_a_la_pagina():
    primero = README.read_text(encoding="utf-8").split("## Mirá esto primero")[1].split("\n## ")[0]
    assert len(re.findall(r"^- `site/globo\.html`: ", primero, re.M)) == 1
    from pipeline import run_all
    assert any(p.modulo == "pipeline.globo" for p in run_all.PASOS)


# ---- contrato del payload (warehouses reales) ----

@pytest.fixture(scope="module")
def payloads():
    return globo.collect(), globo.collect()


@pytest.fixture(scope="module")
def data(payloads):
    return payloads[0]


@needs_wh
@needs_geo
def test_las_tres_cuencas_y_su_contrato(data):
    assert [c["id"] for c in data["cuencas"]] == ["vaca_muerta", "colorado", "wyoming"]
    assert data["lectura"] == {"replican": 1, "de": 2}
    for c in data["cuencas"]:
        M = c["M"]
        meta = M["meta"]
        nm, ancho = len(meta["meses"]), meta["k_max"] - meta["k_min"] + 1
        n = len(M["pozos"]["id"])
        assert n == meta["n_pozos"]
        assert decodificar(M["caudal"], "<u2").size == n * nm
        ev = {k: decodificar(v, "<u1" if k == "flags" else "<u2") for k, v in M["eventos"].items()}
        ne = len(ev["padre"])
        assert ne == meta["n_eventos"] > 0 and ev["indice"].size == ne * ancho
        assert all(len(v) == ne for k, v in ev.items() if k != "indice")
        assert max(ev["padre"].max(), ev["hijo"].max()) < n
        assert set(M["curva"]) == {"cercano", "control"} and all(len(v) == ancho for v in M["curva"].values())


@needs_wh
@needs_geo
def test_el_indice_embebido_reproduce_las_medianas_publicadas(data):
    for c in data["cuencas"]:
        M = c["M"]
        ancho = M["meta"]["k_max"] - M["meta"]["k_min"] + 1
        indice = decodificar(M["eventos"]["indice"], "<u2").reshape(-1, ancho)
        flags = decodificar(M["eventos"]["flags"], "<u1")
        for k in range(M["meta"]["k_min"], M["meta"]["k_max"] + 1):
            for ctl, nombre in ((False, "cercano"), (True, "control")):
                m = globo.mediana_indices(indice, flags, ctl, k)
                assert m == pytest.approx(M["curva"][nombre][k - M["meta"]["k_min"]], abs=1.5e-4), (c["id"], nombre, k)


@needs_wh
@needs_geo
def test_el_veredicto_es_el_del_mart_y_no_un_numero_pegado(data):
    por = {c["id"]: c["veredicto"] for c in data["cuencas"]}
    for cuenca in (COLORADO, WYOMING):
        con = duckdb.connect(str(WAREHOUSES[cuenca.id]), read_only=True)
        try:
            fila = con.execute(f"select brecha, ic_bajo_bloque, ic_alto_bloque, n_cercanos, n_controles, se_replica "
                               f"from {cuenca.tabla_veredicto} where k = 1").fetchone()
        finally:
            con.close()
        v = por[cuenca.id]
        assert (v["brecha"], v["ic_bajo_bloque"], v["ic_alto_bloque"]) == tuple(pytest.approx(x, abs=1e-6) for x in fila[:3])
        assert (v["n_cercanos"], v["n_controles"], v["se_replica"]) == (fila[3], fila[4], bool(fila[5]))
    con = duckdb.connect(str(WAREHOUSES["vm"]), read_only=True)
    try:
        r = con.execute("select estimacion from mart_bloques where metrica = 'brecha_mes1_base_original' and k = 1").fetchone()[0]
    finally:
        con.close()
    assert por["vaca_muerta"]["brecha_mes1"] == pytest.approx(r, abs=1e-6)
    assert por["wyoming"]["ic_bajo_bloque"] < 0 < por["wyoming"]["ic_alto_bloque"]       # el intervalo incluye el cero
    assert por["colorado"]["ic_alto_bloque"] < 0


@needs_wh
@needs_geo
def test_dos_corridas_son_identicas_salvo_generado(payloads):
    a, b = (json.loads(json.dumps(x)) for x in payloads)
    a["meta"].pop("generado")
    b["meta"].pop("generado")
    assert a == b


# ---- pagina generada ----

@needs_site
def test_la_pagina_generada_tiene_forma_y_tamano():
    assert SITE.stat().st_size < globo.MAX_BYTES
    html = SITE.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html")
    assert "{{" not in html.split("const DATA = ", 1)[0] and html.count("const DATA = ") == 1
    assert "/*__DATA__*/null" not in html and "/*__NUCLEO__*/" not in html and "/*__MOTOR__*/" not in html


@needs_site
def test_la_pagina_generada_no_tiene_urls_remotas_ni_guiones_largos():
    html = SITE.read_text(encoding="utf-8")
    code = html.split("const DATA = ", 1)[0] + re.sub(r"^.*?;\n", "", html.split("const DATA = ", 1)[1], count=1, flags=re.S)
    assert not re.search(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", code, re.I)
    assert not re.search(r"""url\(\s*["']?(?:https?:)?//|@import""", code, re.I)
    assert not re.search(r"<script[^>]+\bsrc=", code, re.I)
    assert chr(0x2013) not in code and chr(0x2014) not in code


@needs_site
def test_la_pagina_generada_trae_las_27_auditadas_y_a_colorado_aparte():
    html = SITE.read_text(encoding="utf-8")
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1))
    assert d["meta"]["n_auditadas"] == 27 == sum(1 for j in d["jur"] if j["auditada"])
    assert [j for j in d["jur"] if not j["auditada"]] == [j for j in d["jur"] if j["id"] == "us_co"]
    assert set(d["niveles"]) >= {"por_pozo_con_fractura", "nada_publico", "no_verificado", "medida_sin_auditar"}
    assert {j["nivel"] for j in d["jur"]} <= set(d["niveles"])
    assert d["lectura"]["de"] == 2


def test_la_ficha_de_colorado_no_dice_que_esta_oscuro_y_cambiar_de_cuenca_se_puede_cancelar():
    """Colorado es medida_sin_auditar: su ficha tiene su propia frase (no la de las jurisdicciones oscuras); y salir() cancela el destino pendiente."""
    app = _script(globo.TEMPLATE.read_text(encoding="utf-8"), "globo-app")
    texto = re.search(r"function textoNivel\(j\) \{(.*?)\n  \}", app, re.S).group(1)
    assert texto.index("medida_sin_auditar") < texto.index('return "No publica petróleo por pozo. No dice')   # antes de la frase por defecto
    assert "Oscuro:" not in texto
    assert re.search(r"function salir\(\) \{.*?S\.pend = null;", app, re.S)
    assert "salir(); S.pend = id;" in app


def test_h_no_recorta_en_silencio_lo_que_no_entra_en_16_bits():
    assert globo._h(np.array([0, 65535])) == np.array([0, 65535], dtype="<u2").tobytes()
    for malo in ([65536], [-1]):
        with pytest.raises(ValueError):
            globo._h(np.array(malo))


def test_la_inversa_del_globo_normaliza_la_longitud_aunque_se_gire_mas_de_una_vuelta():
    app = _script(globo.TEMPLATE.read_text(encoding="utf-8"), "globo-app")
    assert "((((lon / RAD) % 360) + 540) % 360) - 180" in app and "(lon / RAD + 540) % 360" not in app
