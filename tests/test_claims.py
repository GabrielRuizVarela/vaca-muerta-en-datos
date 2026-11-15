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
