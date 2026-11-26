"""La cuenca de Wyoming registrada: libro, claims y paginas publicadas (sin necesitar el warehouse)."""
import json
import re

from pipeline import claims, hallazgos
from pipeline.cuencas import CUENCAS, WYOMING
from pipeline.ingest import ROOT

DATOS = ROOT / "wiki" / "hallazgos" / "wyoming_datos.md"
REP = WYOMING.pagina


def _texto(p):
    return p.read_text(encoding="utf-8")


def test_wyoming_esta_registrada_con_su_almacen_y_su_pagina():
    assert CUENCAS["wyoming"] is WYOMING
    assert WYOMING.db.parts[-2:] == ("wyoming", "warehouse.duckdb")
    assert WYOMING.tabla_veredicto == "mart_replicacion_wyoming"
    assert WYOMING.pagina.name == "replicacion_wyoming.md"
    assert WYOMING.pagina_datos == "wyoming_datos.md"


def test_la_hipotesis_de_wyoming_tiene_la_regla_de_colorado():
    h = {x.id: x for x in hallazgos.HIPOTESIS}
    w, c = h["replicacion_wyoming"], h["replicacion_colorado"]
    assert w.almacen == "wyoming" and c.almacen == "colorado"
    assert w.sql == c.sql.replace("colorado", "wyoming")
    assert (w.op, w.umbral) == (c.op, c.umbral)


def test_cada_claim_de_wyoming_encuentra_su_cifra_en_la_pagina_publicada():
    wy = [c for c in claims.CLAIMS if c.almacen == "wyoming"]
    assert len(wy) > 100
    assert {c.fichero for c in wy} == {"wiki/hallazgos/wyoming_datos.md", "wiki/hallazgos/replicacion_wyoming.md",
                                       "wiki/hallazgos/replicacion_cuencas.md", "README.md", "site/globo.html",
                                       "docs/paper/paper.md"}
    assert len({c.id for c in wy}) == len(wy)
    for c in wy:
        texto = _texto(ROOT / c.fichero)
        if claims.extraer(texto, c.patron) is None:
            assert c.opcional, f"{c.id}: la cifra no esta en la pagina y el claim no es opcional"


def test_los_claims_de_wyoming_se_saltan_sin_su_warehouse(tmp_path):
    wy = [c for c in claims.CLAIMS if c.almacen == "wyoming" and c.requiere_wh]   # las cifras fijas de antes de la correccion no lo necesitan
    res = claims.verificar(wy, raiz=ROOT, wh=tmp_path / "no.duckdb", wh_alm={"wyoming": tmp_path / "no2.duckdb"})
    assert {r.estado for r in res} == {"SKIP"}


def test_la_pagina_de_datos_cita_las_dos_lineas_de_los_terminos_y_dice_que_es_nuestra_lectura():
    fm = {r["id"]: r for r in json.loads((ROOT / "data" / "fuentes_mundo.json").read_text(encoding="utf-8"))}
    cita = fm["us_wy"]["terminos_cita"]
    t = _texto(DATOS)
    sin_nota = cita.split(" (Menu principal:")[0]
    assert sin_nota in t.replace("\n> ", " ").replace("\n>\n", " ")
    assert "Scraping of website data is not allowed." in t
    assert "Wyoming Oil and Gas Conservation Commission" in t
    assert "esta es nuestra lectura de los términos, no una licencia" in t
    assert "Nada de Wyoming se redistribuye crudo" in t


def test_la_pagina_de_replicacion_publica_el_veredicto_y_el_ic_sin_afirmar_de_mas():
    t = _texto(REP)
    assert "Veredicto contra la regla fijada antes de correr:" in t
    assert re.search(r"Valor de la hipótesis: -?\d+,\d+, el mayor", t)
    assert "## Qué Wyoming no puede mostrar" in t
    assert "FIRSTCOMP" in t
    assert "no se afirma causalidad" in t


def test_las_paginas_de_wyoming_no_llevan_rayas_largas_ni_cortas():
    for p in (DATOS, REP):
        t = _texto(p)
        assert chr(0x2013) not in t and chr(0x2014) not in t
