"""La pagina de la familia de cuencas: se arma desde el veredicto de cada cuenca, lista todas y sus cifras estan fijadas por claims."""
from __future__ import annotations

import duckdb
import pytest

from pipeline import claims, familia
from pipeline.cuencas import CUENCAS
from pipeline.ingest import ROOT
from pipeline.replicacion import COLS_VEREDICTO

PAGINA = ROOT / "wiki" / "hallazgos" / "replicacion_cuencas.md"


def _almacen(id_: str, se_replica: bool, brecha: float, previa: float, hijos: int = 100):
    """Un warehouse en memoria con solo las dos tablas que lee la pagina."""
    con = duckdb.connect(":memory:")
    cols = [c[0] for c in COLS_VEREDICTO]
    fila = dict.fromkeys(cols, 0.0)
    fila.update(k=1, n_cercanos=50, n_controles=500, brecha=brecha, ic_bajo_bloque=brecha - 0.02, ic_alto_bloque=brecha + 0.02,
                brecha_previa_limpia=previa, valor=-0.1 if se_replica else 0.1, se_replica=se_replica)
    con.execute(f"create table {CUENCAS[id_].tabla_veredicto} ({', '.join(f'{c} double' for c in cols)})")
    con.execute(f"insert into {CUENCAS[id_].tabla_veredicto} values ({', '.join('?' for _ in cols)})", [fila[c] for c in cols])
    con.execute("create table mart_replicacion_recuentos (clave varchar, valor double)")
    con.execute("insert into mart_replicacion_recuentos values ('hijos', ?)", [hijos])
    return con


def _cons(co: bool, wy: bool):
    return {"colorado": _almacen("colorado", co, -0.2, -0.05), "wyoming": _almacen("wyoming", wy, -0.1, -0.12)}


@pytest.mark.parametrize("co,wy,k", [(True, True, 2), (True, False, 1), (False, False, 0)])
def test_la_lectura_sale_de_la_columna_se_replica_de_cada_cuenca(co, wy, k):
    r = familia.resultados_desde(_cons(co, wy))
    assert [i for i in r] == ["colorado", "wyoming"]
    assert familia.lectura_familia(r)["k"] == k


def test_sin_el_warehouse_de_una_cuenca_no_hay_lectura():
    with pytest.raises(ValueError, match="wyoming"):
        familia.resultados_desde({"colorado": _almacen("colorado", True, -0.2, -0.05)})
    with pytest.raises(ValueError, match="wyoming"):
        familia.resultados_desde({"colorado": _almacen("colorado", True, -0.2, -0.05), "wyoming": None})


def test_una_cuenca_con_pocos_hijos_o_sin_valor_no_tiene_lectura():
    cons = {"colorado": _almacen("colorado", True, -0.2, -0.05), "wyoming": _almacen("wyoming", True, -0.1, -0.02, hijos=10)}
    r = familia.resultados_desde(cons)
    assert r["colorado"] == (True, "") and r["wyoming"][0] is None and "menos de 30" in r["wyoming"][1]
    assert familia.lectura_familia(r)["k"] == 1 and familia.lectura_familia(r)["n"] == 2
    cons["wyoming"] = _almacen("wyoming", True, -0.1, -0.02)
    cons["wyoming"].execute("update mart_replicacion_wyoming set valor = 'nan'::double")
    assert familia.resultados_desde(cons)["wyoming"][0] is None


def test_la_pagina_lista_las_cuencas_y_no_promedia():
    t = familia.pagina_familia(_cons(True, False))
    assert "**Se replica en 1 de 2 cuencas: Colorado (se replica); Wyoming (no se replica).**" in t
    assert "| Colorado | 100 | 50 | 500 | -20,0 |" in t
    assert "| Wyoming | 100 | 50 | 500 | -10,0 |" in t
    assert "## Qué no es" in t and "estimación conjunta" in t
    assert chr(0x2013) not in t and chr(0x2014) not in t


def test_main_sale_con_2_si_falta_un_almacen(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CUENCAS["wyoming"].__class__, "db", property(lambda self: tmp_path / self.id / "no.duckdb"))
    assert familia.main(pagina=tmp_path / "p.md") == 2
    assert not (tmp_path / "p.md").exists()
    assert "falta" in capsys.readouterr().err


def test_los_claims_de_la_familia_encuentran_su_cifra_en_las_paginas_publicadas():
    fam = [c for c in claims.CLAIMS if c.id.startswith("fam_") or c.id.startswith("wy_readme_")]
    assert len(fam) == 27
    assert len({c.id for c in fam}) == len(fam)
    assert {c.almacen for c in fam} == {"colorado", "wyoming", "familia"}
    for c in fam:
        texto = (ROOT / c.fichero).read_text(encoding="utf-8")
        assert claims.extraer(texto, c.patron) is not None, f"{c.id}: la cifra no esta en {c.fichero}"


def test_los_claims_de_la_familia_se_saltan_si_falta_un_warehouse(tmp_path):
    fam = [c for c in claims.CLAIMS if c.almacen == "familia"]
    assert fam
    res = claims.verificar(fam, raiz=ROOT, wh=tmp_path / "a.duckdb", wh_co=tmp_path / "b.duckdb", wh_alm={"wyoming": tmp_path / "c.duckdb"})
    assert {r.estado for r in res} == {"SKIP"}


def test_la_pagina_publicada_dice_lo_que_la_lectura_no_es():
    t = PAGINA.read_text(encoding="utf-8")
    assert t.startswith("# Replicación en otras cuencas: lectura de la familia")
    assert "No hay promedio, peso ni estimación conjunta" in t
    assert "No se probó cuánto de una diferencia entre cuencas sale de eso" in t
    assert chr(0x2013) not in t and chr(0x2014) not in t
