"""Reproducibilidad: build, marts de costo y robustez, wiki, report y replay dan el mismo resultado en dos corridas."""
import hashlib
import re
import shutil
from pathlib import Path

import duckdb
import pytest

from pipeline import costo, placebo, replay, report, robustez
from pipeline.build import build
from pipeline.ingest import DATA, ROOT, load_manifest
from pipeline.wiki import build_wiki
from tests.test_pipeline import FRAC_COLS, PROD_COLS, frac_row, prod_row, write_csv

WAREHOUSE = DATA / "warehouse.duckdb"
needs_wh = pytest.mark.skipif(not WAREHOUSE.exists(), reason="warehouse not built")
MARTS_ROBUSTEZ = ["mart_robustez_eje", "mart_robustez_costo"]
MARTS_PLACEBO = ["mart_placebo_pretrend", "mart_placebo_pretrend_base_original", "mart_placebo_pretrend_sin_previos",
                 "mart_placebo_fechas", "mart_placebo_permutacion", "mart_placebo_eje"]
MARTS_COSTO = ["mart_anisotropia_area", "mart_costo_coef", "mart_perdida_permanente", "mart_costo_cv",
               "mart_costo_calibracion", "mart_costo_residuales"]


def tablas(con) -> list[str]:
    return [r[0] for r in con.execute(
        "select table_name from information_schema.tables where table_schema = 'main' order by 1").fetchall()]


def filas_ordenadas(con, tabla: str) -> list[tuple]:
    return con.execute(f'select * from "{tabla}" order by all').fetchall()


def sintetico(directorio: Path) -> dict[str, Path]:
    prod, frac = [], []
    for k in range(6):
        pozo = f"P{k}"
        for mes in range(1, 13):
            prod.append(prod_row(pozo, 2022, mes, 900 - 40 * mes + 25 * k, lon=str(-69 - 0.01 * k),
                                 lat=str(-38 - 0.005 * k), gas=100 + mes, agua=10 * k))
        frac.append(frac_row(f"F{k}", pozo, f"2022-0{k + 1}-15", rama=2000 + 100 * k))
    return {
        "produccion_no_convencional": write_csv(directorio / "p.csv", PROD_COLS, prod),
        "fractura_adjunto_iv": write_csv(directorio / "f.csv", FRAC_COLS, frac),
        "seed_operadores": ROOT / "seeds" / "operadores.csv",
    }


def test_build_dos_veces_da_las_mismas_tablas(tmp_path):
    entradas = sintetico(tmp_path)
    con_a, con_b = duckdb.connect(str(tmp_path / "a.duckdb")), duckdb.connect(str(tmp_path / "b.duckdb"))
    build(con_a, entradas)
    build(con_b, entradas)
    nombres = tablas(con_a)
    assert nombres and nombres == tablas(con_b)
    for t in nombres:
        assert filas_ordenadas(con_a, t) == filas_ordenadas(con_b, t), f"tabla no determinista: {t}"
    build(con_a, entradas)  # idempotente sobre el mismo archivo
    for t in nombres:
        assert filas_ordenadas(con_a, t) == filas_ordenadas(con_b, t), f"build no idempotente: {t}"


@pytest.mark.slow
@needs_wh
def test_costo_dos_veces_da_marts_identicos(tmp_path):
    resultados = []
    for nombre in ("a", "b"):
        copia = tmp_path / f"{nombre}.duckdb"
        shutil.copyfile(WAREHOUSE, copia)
        costo.main(copia)
        con = duckdb.connect(str(copia), read_only=True)
        try:
            resultados.append({t: con.execute(f"select * from {t}").fetchall() for t in MARTS_COSTO})
        finally:
            con.close()
    for t in MARTS_COSTO:
        assert resultados[0][t], f"{t} vacia"
        assert resultados[0][t] == resultados[1][t], f"mart no determinista: {t}"


def hash_arbol(raiz: Path) -> dict[str, str]:
    return {str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(raiz.rglob("*")) if p.is_file()}


@pytest.mark.slow
@needs_wh
def test_wiki_dos_veces_da_el_mismo_arbol(tmp_path):
    manifest = load_manifest()
    arboles = []
    for nombre in ("a", "b"):
        con = duckdb.connect(str(WAREHOUSE), read_only=True)
        try:
            build_wiki(con, manifest, tmp_path / nombre)
        finally:
            con.close()
        arboles.append(hash_arbol(tmp_path / nombre))
    assert arboles[0], "la wiki no genero archivos"
    assert arboles[0] == arboles[1]


GENERADO = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")


def normaliza(html: str) -> str:
    """Quita la marca de hora de generacion, lo unico que cambia entre dos corridas."""
    return GENERADO.sub("<generado>", html)


@needs_wh
def test_report_dos_veces_da_el_mismo_html(tmp_path):
    salidas = []
    for nombre in ("a", "b"):
        con = duckdb.connect(str(WAREHOUSE), read_only=True)
        try:
            report.render(report.collect(con), tmp_path / f"{nombre}.html")
        finally:
            con.close()
        salidas.append((tmp_path / f"{nombre}.html").read_text())
    assert GENERADO.search(salidas[0]), "el html ya no lleva marca de hora: revisar la normalizacion"
    assert normaliza(salidas[0]) == normaliza(salidas[1])


@pytest.mark.slow
@needs_wh
def test_replay_dos_veces_da_el_mismo_html(tmp_path):
    salidas = []
    for nombre in ("a", "b"):
        con = duckdb.connect(str(WAREHOUSE), read_only=True)
        try:
            replay.render(replay.collect(con), tmp_path / f"{nombre}.html")
        finally:
            con.close()
        salidas.append((tmp_path / f"{nombre}.html").read_text())
    assert GENERADO.search(salidas[0]), "el html ya no lleva marca de hora: revisar la normalizacion"
    assert normaliza(salidas[0]) == normaliza(salidas[1])


@pytest.mark.slow
@needs_wh
def test_robustez_dos_veces_da_marts_identicos(tmp_path):
    resultados = []
    for nombre in ("a", "b"):
        copia = tmp_path / f"{nombre}.duckdb"
        shutil.copyfile(WAREHOUSE, copia)
        robustez.main(copia)
        con = duckdb.connect(str(copia), read_only=True)
        try:
            resultados.append({t: con.execute(f"select * from {t}").fetchall() for t in MARTS_ROBUSTEZ})
        finally:
            con.close()
    for t in MARTS_ROBUSTEZ:
        assert resultados[0][t], f"{t} vacia"
        assert resultados[0][t] == resultados[1][t], f"mart no determinista: {t}"


@pytest.mark.slow
@needs_wh
def test_placebo_dos_veces_da_marts_identicos(tmp_path):
    resultados = []
    for nombre in ("a", "b"):
        copia = tmp_path / f"{nombre}.duckdb"
        shutil.copyfile(WAREHOUSE, copia)
        placebo.main(copia)
        con = duckdb.connect(str(copia), read_only=True)
        try:
            resultados.append({t: con.execute(f"select * from {t}").fetchall() for t in MARTS_PLACEBO})
        finally:
            con.close()
    for t in MARTS_PLACEBO:
        assert resultados[0][t], f"{t} vacia"
        assert resultados[0][t] == resultados[1][t], f"mart no determinista: {t}"
