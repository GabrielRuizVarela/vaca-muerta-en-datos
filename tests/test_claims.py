"""Claims check: the number parser, FAIL detection on a fake document, and the real README against the warehouse."""
import duckdb
import pytest

from pipeline import claims
from pipeline.claims import Claim, extraer, parse_numero, verificar


@pytest.mark.parametrize("s,esperado", [("1.234,5", 1234.5), ("10,7", 10.7), ("93", 93), ("431.322", 431322),
                                         ("-960", -960), ("0,05", 0.05), ("cinco", 5), ("Trece", 13)])
def test_parse_numero(s, esperado):
    assert parse_numero(s) == pytest.approx(esperado)


def test_extraer_y_frase_ausente():
    assert extraer("Son 2.077 eventos, un mes", r"Son ([\d.]+) eventos") == 2077
    assert extraer("otra frase", r"Son ([\d.]+) eventos") is None


def _doc(tmp_path, texto):
    (tmp_path / "doc.md").write_text(texto, encoding="utf-8")


def test_pass_fail_y_frase_cambiada(tmp_path):
    _doc(tmp_path, "Hay 10,7 millones y 93 grados. Quedan 4 pozos.")
    cs = [Claim("ok", "doc.md", r"Hay (\d+,\d+) millones", lambda con: 10.72, 0.05, "{:.1f}", requiere_wh=False),
          Claim("mal", "doc.md", r"y (\d+) grados", lambda con: 100.0, 0.5, requiere_wh=False),
          Claim("borrada", "doc.md", r"Son (\d+) filas", lambda con: 1.0, requiere_wh=False),
          Claim("sin_archivo", "nada.md", r"(\d+)", lambda con: 1.0, requiere_wh=False)]
    res = {r.claim.id: r for r in verificar(cs, raiz=tmp_path)}
    assert res["ok"].estado == "PASS"
    assert res["mal"].estado == "FAIL" and "93" in res["mal"].detalle and "100" in res["mal"].detalle
    assert res["borrada"].estado == "FAIL"
    assert res["sin_archivo"].estado == "FAIL"


def test_tolerancia_es_inclusiva(tmp_path):
    _doc(tmp_path, "unos 1.500 m")
    c = Claim("t", "doc.md", r"unos ([\d.]+) m", lambda con: 1450.0, 50, requiere_wh=False)
    assert verificar([c], raiz=tmp_path)[0].estado == "PASS"
    c = Claim("t", "doc.md", r"unos ([\d.]+) m", lambda con: 1449.0, 50, requiere_wh=False)
    assert verificar([c], raiz=tmp_path)[0].estado == "FAIL"


def test_skip_sin_warehouse_y_con_wh(tmp_path):
    _doc(tmp_path, "n = 5")
    c = Claim("w", "doc.md", r"n = (\d+)", lambda con: con.execute("select 5").fetchone()[0])
    assert verificar([c], raiz=tmp_path)[0].estado == "SKIP"
    duckdb.connect(str(tmp_path / "w.duckdb")).close()
    assert verificar([c], raiz=tmp_path, wh=tmp_path / "w.duckdb")[0].estado == "PASS"


def test_skip_sin_la_tabla_de_un_paso_opcional(tmp_path):
    _doc(tmp_path, "n = 5")
    c = Claim("t", "doc.md", r"n = (\d+)", lambda con: con.execute("select n from extra").fetchone()[0], tabla="extra")
    wh = tmp_path / "w.duckdb"
    duckdb.connect(str(wh)).close()
    r = verificar([c], raiz=tmp_path, wh=wh)[0]
    assert r.estado == "SKIP" and "extra" in r.detalle
    con = duckdb.connect(str(wh))
    con.execute("create table extra as select 5 as n")
    con.close()
    assert verificar([c], raiz=tmp_path, wh=wh)[0].estado == "PASS"


def test_lento_se_omite_con_rapido(tmp_path):
    _doc(tmp_path, "n = 5")
    c = Claim("l", "doc.md", r"n = (\d+)", lambda con: 5.0, requiere_wh=False, lento=True)
    assert verificar([c], raiz=tmp_path, lentos=False)[0].estado == "SKIP"
    assert verificar([c], raiz=tmp_path, lentos=True)[0].estado == "PASS"


def test_main_sale_1_con_un_fail(tmp_path, monkeypatch):
    _doc(tmp_path, "n = 5")
    mal = [Claim("m", "doc.md", r"n = (\d+)", lambda con: 6.0, requiere_wh=False)]
    monkeypatch.setattr(claims, "ROOT", tmp_path)
    monkeypatch.setattr(claims, "CLAIMS", mal)
    monkeypatch.setattr(claims, "CAPACIDADES", [])   # sus frases viven en los ficheros reales, no en el ROOT de prueba
    assert claims.main(["--rapido"]) == 1
    monkeypatch.setattr(claims, "CLAIMS", [Claim("b", "doc.md", r"n = (\d+)", lambda con: 5.0, requiere_wh=False)])
    assert claims.main(["--rapido"]) == 0


def test_ids_unicos():
    ids = [c.id for c in claims.CLAIMS]
    assert len(ids) == len(set(ids))


def test_readme_y_docs_coinciden_con_el_warehouse():
    """The real documents against the real warehouse (rows needing it are SKIP when it is absent)."""
    res = verificar(lentos=False)
    fallos = [f"{r.claim.id}: {r.detalle}" for r in res if r.estado == "FAIL"]
    assert not fallos, "\n".join(fallos)
    if not claims.WAREHOUSE.exists():
        pytest.skip("sin data/warehouse.duckdb: solo se verificaron las cifras que salen de archivos versionados")


def test_numeros_sin_fijar_devuelve_solo_el_suelto(tmp_path):
    """Un numero fijado por un claim, uno definicional y uno entre comillas invertidas no salen; el suelto si."""
    _doc(tmp_path, "La brecha es de -22,9 puntos con bloques de 5 km y `uv run 14` da 77 casos.")
    cs = [Claim("brecha", "doc.md", r"es de (-?\d+,\d+) puntos", lambda con: -22.9, 0.05, requiere_wh=False),
          Claim("otro_fichero", "otro.md", r"da (\d+) casos", lambda con: 77.0, requiere_wh=False)]
    assert claims.numeros_sin_fijar("doc.md", (r"bloques de 5 km",), raiz=tmp_path, claims=cs) == ["77"]
    cs.append(Claim("casos", "doc.md", r"da (\d+) casos", lambda con: 77.0, requiere_wh=False))
    assert claims.numeros_sin_fijar("doc.md", (r"bloques de 5 km",), raiz=tmp_path, claims=cs) == []


def test_pagina_de_limites_sin_numeros_sueltos():
    """Cada cifra de wiki/hallazgos/limites.md esta fijada por un claim o es parte de una definicion de LIMITES_DEFINICIONALES."""
    assert claims.numeros_sin_fijar(claims.W_LIM, claims.LIMITES_DEFINICIONALES) == []


def test_resumen_del_operador_sin_numeros_sueltos():
    """Cada cifra de docs/resumen-operador.md esta fijada por un claim o es parte de una definicion de RESUMEN_DEFINICIONALES."""
    assert claims.numeros_sin_fijar(claims.W_RESUMEN, claims.RESUMEN_DEFINICIONALES) == []


def test_caso_de_interferencia_sin_numeros_sueltos():
    """Cada cifra de docs/caso-interferencia.md esta fijada por un claim o es parte de una definicion de CASO_DEFINICIONALES."""
    assert claims.numeros_sin_fijar(claims.CASO, claims.CASO_DEFINICIONALES) == []


def test_readme_sin_numeros_sueltos():
    """Cada cifra de README.md esta fijada por un claim o es parte de una definicion de README_DEFINICIONALES."""
    assert claims.numeros_sin_fijar(claims.R, claims.README_DEFINICIONALES) == []


def test_numeros_sin_fijar_mira_solo_entre_los_titulos(tmp_path):
    """Con desde y hasta solo cuenta los numeros de esa seccion; una definicion de otra seccion igual los fija."""
    _doc(tmp_path, "## A\nhay 3 pozos\n## B\nhay 5 pozos a 2 km\n## C\nhay 7 pozos\n")
    assert claims.numeros_sin_fijar("doc.md", (), raiz=tmp_path, claims=[], desde="## B", hasta="## C") == ["5", "2"]
    assert claims.numeros_sin_fijar("doc.md", (r"a 2 km",), raiz=tmp_path, claims=[], desde="## B", hasta="## C") == ["5"]
    assert claims.numeros_sin_fijar("doc.md", (), raiz=tmp_path, claims=[], desde="## C") == ["7"]
    with pytest.raises(ValueError):
        claims.numeros_sin_fijar("doc.md", (), raiz=tmp_path, claims=[], desde="## Z")


def test_paper_seccion_a_sin_numeros_sueltos():
    """Cada cifra del paper hasta 4. Resultados esta fijada por un claim o es parte de una definicion de PAPER_DEF_A."""
    desde, hasta = claims.PAPER_SECCIONES["a"]
    assert claims.numeros_sin_fijar(claims.W_PAPER, claims.PAPER_DEF_COMUN + claims.PAPER_DEF_A, desde=desde, hasta=hasta) == []


def test_paper_seccion_b_sin_numeros_sueltos():
    """Cada cifra del paper de 4. Resultados a 4.2 esta fijada por un claim o es parte de una definicion de PAPER_DEF_B."""
    desde, hasta = claims.PAPER_SECCIONES["b"]
    assert claims.numeros_sin_fijar(claims.W_PAPER, claims.PAPER_DEF_COMUN + claims.PAPER_DEF_B, desde=desde, hasta=hasta) == []


def test_paper_seccion_c_sin_numeros_sueltos():
    """Cada cifra de 4.3 del paper esta fijada por un claim o es parte de una definicion de PAPER_DEF_C."""
    desde, hasta = claims.PAPER_SECCIONES["c"]
    assert claims.numeros_sin_fijar(claims.W_PAPER, claims.PAPER_DEF_COMUN + claims.PAPER_DEF_C, desde=desde, hasta=hasta) == []


def test_paper_seccion_d_sin_numeros_sueltos():
    """Cada cifra del paper desde 4.4 hasta el final esta fijada por un claim o es parte de una definicion de PAPER_DEF_D."""
    desde, hasta = claims.PAPER_SECCIONES["d"]
    assert claims.numeros_sin_fijar(claims.W_PAPER, claims.PAPER_DEF_COMUN + claims.PAPER_DEF_D, desde=desde, hasta=hasta) == []


def test_paper_sin_numeros_sueltos():
    """Cada cifra de docs/paper/paper.md, de punta a punta, esta fijada por un claim o es parte de una definicion de
    PAPER_DEFINICIONALES."""
    assert claims.numeros_sin_fijar(claims.W_PAPER, claims.PAPER_DEFINICIONALES) == []


def test_espera_cada_cifra_fija_tiene_su_claim():
    """Las siete cifras fijas del texto de site/espera.html coinciden con su patron sin warehouse (CI corre sin el)."""
    texto = (claims.ROOT / claims.W_ESPERA).read_text(encoding="utf-8")
    leidas = {c.id: claims.extraer(texto, c.patron) for c in claims._claims_espera()}
    assert leidas == {"espera_eventos@site": 2094, "espera_brecha_descontada@site": 19, "espera_brecha_mes1@site": 23,
                      "espera_brecha_mes6@site": 2.1, "espera_rango_inferior@site": 6.4, "espera_rango_superior@site": 11.4,
                      "espera_mediana_24@site": -954}
    assert {c.id for c in claims._claims_espera()} <= {c.id for c in claims.CLAIMS}


def test_espera_no_dice_misma_edad():
    """El control no se empareja por edad (revision independiente, F1): la pagina no lo describe asi."""
    for ruta in (claims.W_ESPERA, "pipeline/espera_template.html"):
        assert "misma edad" not in (claims.ROOT / ruta).read_text(encoding="utf-8")


# ---------------------------------------------------------------- capacidades: frases que dicen qué lee el código
def test_capacidad_falsa_da_fail_y_una_verdadera_pasa(tmp_path):
    from pipeline.claims import Capacidad
    _doc(tmp_path, "Desde hoy el modo local lee agua. No lee diario.")
    falsa = Capacidad("falsa", "doc.md", r"el modo local lee agua", True, lambda: False)   # el código no la lee
    verdadera = Capacidad("ok", "doc.md", r"No lee diario", False, lambda: False)
    borrada = Capacidad("borrada", "doc.md", r"lee cierres", False, lambda: False)
    res = {r.claim.id: r for r in verificar([falsa, verdadera, borrada], raiz=tmp_path)}
    assert res["falsa"].estado == "FAIL" and "código dice otra cosa" in res["falsa"].detalle
    assert res["ok"].estado == "PASS"
    assert res["borrada"].estado == "FAIL" and "ya no está" in res["borrada"].detalle


def test_frase_real_de_capacidad_falla_si_el_codigo_deja_de_leer_agua(monkeypatch):
    from pipeline import local
    ids = {c.id for c in claims.CAPACIDADES}
    assert "cap_local_agua_readme_es" in ids
    assert {r.estado for r in verificar(claims.CAPACIDADES)} == {"PASS"}
    monkeypatch.setattr(local, "MENSUAL_OPCIONALES", ("dias_produccion",))   # el codigo deja de leer agua_m3
    res = {r.claim.id: r.estado for r in verificar(claims.CAPACIDADES)}
    assert res["cap_local_agua_readme_es"] == "FAIL" and res["cap_local_agua_sitio"] == "FAIL"
    assert res["cap_local_diario_readme_es"] == "PASS"   # sigue sin leer el diario


def _d13_con(filas):
    con = duckdb.connect()
    con.execute("create table mart_causal_profundo_d13 (corte varchar, grupo varchar, n_tratados integer, n_controles integer, "
                "valor double, ic_bajo double, ic_alto double, diseno varchar, veredicto varchar)")
    con.executemany("insert into mart_causal_profundo_d13 values (?, ?, ?, ?, ?, ?, ?, ?, ?)", filas)
    return con


def _d13_fn(slot):
    return next(c for c in claims.CLAIMS if c.id.endswith(f"_paper_d13_{slot}")).valor_fn


def test_d13_sin_muestra_da_nan_y_no_rompe():
    """Sin muestra, el mart de D13 lleva solo la fila de veredicto: los claims dan nan (FAIL), no una excepcion."""
    import math
    con = _d13_con([("veredicto", "", 0, 0, None, None, None, "D13", "sin muestra")])
    for slot in ("d13", "d13lo", "d13n", "p13", "p13hi", "p13n"):
        assert math.isnan(_d13_fn(slot)(con)), slot


def test_d13_solo_con_cero_pide_el_cero_dentro_del_ic():
    """Un operador con todo el IC bajo cero no cuenta como 'IC que incluye cero'."""
    import math
    base = [("veredicto", "", 0, 0, None, None, None, "D13", "general"),
            ("operador", "PDC ENERGY INC", 342, 900, 3.6, -0.9, 8.1, "D13", "")]
    con = _d13_con(base + [("operador", "PRAIRIE OPERATING CO LLC", 60, 300, 1.0, -1.0, 3.0, "D13", "")])
    assert _d13_fn("s13")(con) == 2
    con = _d13_con(base + [("operador", "PRAIRIE OPERATING CO LLC", 60, 300, -3.0, -5.0, -1.0, "D13", "")])
    assert math.isnan(_d13_fn("s13")(con))
