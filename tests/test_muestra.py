"""La muestra de data/muestra: el generador es determinista y la demo corre sin tocar el sitio real."""
import csv
import hashlib
import json
from pathlib import Path

from pipeline import build, checks, muestra, report, run_all
from pipeline.ingest import ROOT

MUESTRA = ROOT / "data" / "muestra"


def _escribir(path: Path, cabecera: list[str], filas: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(filas)


def _raw_falso(tmp_path: Path) -> tuple[dict[str, Path], dict]:
    """Dos CSV con todas las columnas que lee el staging, mas una que no usa, en orden revuelto."""
    cp = sorted(checks.COLUMNAS_ESPERADAS["produccion_no_convencional"]) + ["observaciones"]
    cf = sorted(checks.COLUMNAS_ESPERADAS["fractura_adjunto_iv"]) + ["cuenca"]

    def fila(cab, **kv):
        return [kv.get(c, "x") for c in cab]
    prod = [fila(cp, anio=str(a), mes=str(m), idpozo=str(p), areapermisoconcesion=area)
            for a, m, p, area in [(2020, 3, 2, "LOMA CAMPANA "), (2019, 12, 1, "LOMA CAMPANA"), (2020, 1, 3, "OTRA"),
                                  (2020, 1, 2, "loma campana")]]
    frac = [fila(cf, idpozo=str(p), fecha_inicio_fractura=f"2020-0{p}-01", id_base_fractura_adjiv=str(p * 10))
            for p in (3, 2, 1)]
    _escribir(tmp_path / "p.csv", cp, prod)
    _escribir(tmp_path / "f.csv", cf, frac)
    raw = {"produccion_no_convencional": tmp_path / "p.csv", "fractura_adjunto_iv": tmp_path / "f.csv"}
    manifest = {n: {"url": "http://x", "sha256": "ab" * 32, "bytes": 1} for n in raw}
    return raw, manifest


def test_generador_es_determinista_y_filtra_por_area_y_pozo(tmp_path):
    raw, manifest = _raw_falso(tmp_path)
    muestra.generar(raw, manifest, tmp_path / "a", ["LOMA CAMPANA"])
    muestra.generar(raw, manifest, tmp_path / "b", ["LOMA CAMPANA"])
    nombres = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert nombres == ["README.md", "fractura_adjunto_iv.csv.gz", "manifest.json", "produccion_no_convencional.csv.gz"]
    for n in nombres:
        assert (tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes(), n
    sel = muestra.seleccionar(raw, ["LOMA CAMPANA"])
    cab, filas = sel["produccion_no_convencional"]
    assert "observaciones" not in cab and len(filas) == 3          # la fila de OTRA queda afuera
    assert [(f[cab.index("anio")], f[cab.index("mes")]) for f in filas] == [("2019", "12"), ("2020", "1"), ("2020", "3")]
    assert [f[sel["fractura_adjunto_iv"][0].index("idpozo")] for f in sel["fractura_adjunto_iv"][1]] == ["1", "2"]  # pozo 3 no quedo
    assert "no reproduce las cifras de la cuenca" in (tmp_path / "a" / "README.md").read_text(encoding="utf-8")


def test_muestra_versionada_pesa_poco_y_tiene_manifiesto():
    assert sum(p.stat().st_size for p in MUESTRA.iterdir()) <= 5 * 1024 * 1024
    manifest = json.loads((MUESTRA / "manifest.json").read_text())
    for nombre, entrada in manifest.items():
        datos = (MUESTRA / entrada["path"]).read_bytes()
        assert hashlib.sha256(datos).hexdigest() == entrada["sha256"], nombre


def test_build_y_pagina_sobre_la_muestra(tmp_path):
    db = tmp_path / "muestra.duckdb"
    assert build.main(["--raw-dir", str(MUESTRA), "--db", str(db)]) == 0
    assert (tmp_path / "muestra_dq_report.json").exists()
    assert report.main(["--db", str(db), "--out", str(tmp_path / "site"), "--banner"]) == 0
    html = (tmp_path / "site" / "index.html").read_text()
    assert "MUESTRA: no son las cifras de la cuenca" in html and "<title>MUESTRA" in html


def test_demo_no_toca_el_sitio_real(tmp_path, monkeypatch):
    index = ROOT / "site" / "index.html"
    antes = hashlib.sha256(index.read_bytes()).hexdigest()
    db, sitio = tmp_path / "muestra.duckdb", tmp_path / "site" / "muestra"
    monkeypatch.setattr(run_all, "MUESTRA_ARGS", {
        "build": ("--raw-dir", str(MUESTRA), "--db", str(db)),
        "report": ("--db", str(db), "--out", str(sitio), "--banner")})
    monkeypatch.setattr(run_all, "MUESTRA_SITE", sitio)
    assert run_all.main(["--muestra"]) == 0
    assert "MUESTRA" in (sitio / "index.html").read_text()
    assert hashlib.sha256(index.read_bytes()).hexdigest() == antes


def test_muestra_omite_pasos_con_motivo():
    corren, omitidos = run_all.pasos_muestra()
    assert [p.nombre for p in corren] == ["build", "report"]
    assert {"costo", "wiki", "replay", "claims"} <= set(omitidos) and "ingest" not in omitidos
