"""Registro de brechas: validación contra el repo, fórmula de prioridad y reescritura de la lista."""
from pipeline import brechas
from pipeline.brechas import cargar, ordenadas, prioridad, reescribir_lista, validar

CLAIMS = {"c_readme": "README.md", "c_nota": "wiki/hallazgos/nota.md", "c_paper": "docs/paper/paper.md"}


def _b(i, bloquea="", donde="a.md:2", **kw):
    b = {"id": i, "texto": "una brecha", "tipo": "metodo", "bloquea": bloquea, "cierra": "codigo", "donde": donde,
         "estado": "abierta", "cerrada_por": ""}
    return {**b, **kw}


def _raiz(tmp_path):
    (tmp_path / "a.md").write_text("uno\ndos\ntres\n", encoding="utf-8")
    return tmp_path


def test_valida_una_brecha_correcta(tmp_path):
    assert validar([_b("B01", "c_readme;a.md:3")], raiz=_raiz(tmp_path), claims=CLAIMS) == []


def test_rechaza_un_donde_con_linea_fuera_del_archivo(tmp_path):
    e = validar([_b("B01", donde="a.md:4")], raiz=_raiz(tmp_path), claims=CLAIMS)
    assert len(e) == 1 and "a.md:4" in e[0] and "3 líneas" in e[0]
    assert validar([_b("B01", donde="nada.md:1")], raiz=_raiz(tmp_path), claims=CLAIMS)


def test_rechaza_un_id_de_claim_desconocido_y_una_referencia_mala(tmp_path):
    e = validar([_b("B01", "c_inventado;a.md:9")], raiz=_raiz(tmp_path), claims=CLAIMS)
    assert any("c_inventado" in x for x in e) and any("a.md:9" in x for x in e)


def test_rechaza_conjuntos_fuera_de_lista_e_ids_repetidos(tmp_path):
    e = validar([_b("B01", tipo="otro"), _b("B01", cierra="nadie", estado="medio")], raiz=_raiz(tmp_path), claims=CLAIMS)
    assert any("tipo" in x for x in e) and any("cierra" in x for x in e) and any("estado" in x for x in e)
    assert any("repetido" in x for x in e)


def test_prioridad_cuenta_entradas_distintas_que_apuntan_a_ficheros_publicos():
    assert prioridad(_b("B01", "c_readme;c_paper;site/index.html:10"), CLAIMS) == 3
    assert prioridad(_b("B02", "c_readme;c_readme;c_nota;wiki/x.md:1"), CLAIMS) == 1   # repetida y no pública no cuentan
    assert prioridad(_b("B03"), CLAIMS) == 0


def test_orden_por_prioridad_y_empate_por_id():
    bs = [_b("B03", "c_readme"), _b("B01"), _b("B02", "c_readme;c_paper"), _b("B04", "c_paper")]
    assert [b["id"] for b in ordenadas(bs, CLAIMS)] == ["B02", "B03", "B04", "B01"]


def test_reescribe_solo_entre_marcadores():
    t = f"antes\n{brechas.INICIO}\nviejo\n{brechas.FIN}\ndespués\n"
    assert reescribir_lista(t, "1. nueva\n") == f"antes\n{brechas.INICIO}\n1. nueva\n{brechas.FIN}\ndespués\n"


def test_el_csv_real_valida():
    assert validar(cargar()) == []
