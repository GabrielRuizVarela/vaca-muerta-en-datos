import asyncio
import json

import pytest
from pydantic import ValidationError

from agente.eval.run import cargar, puntuar
from agente.ops import REGISTRO, ErrorOperacion, ejecutar
from agente.router import elegir
from tests.test_pipeline import prod_row, warehouse  # noqa: F401  (fixture)


@pytest.fixture
def con(warehouse):  # noqa: F811
    return warehouse([prod_row(1, 2024, 9, 300), prod_row(2, 2024, 9, 100, "VISTA ENERGY ARGENTINA SAU"),
                      prod_row(1, 2025, 9, 600), prod_row(2, 2025, 9, 100, "VISTA ENERGY ARGENTINA SAU")], [])


def guion(*respuestas):
    it = iter(respuestas)
    return lambda msgs: next(it)


def test_operation_numbers_come_from_the_warehouse(con):
    r = ejecutar(con, "produccion_vm", {"operador": "ypf"})
    assert r["args"]["operador"] == "ypf" and r["fuente"]["datos_a"] == "2025-09"
    assert r["valor"] == pytest.approx(600 * 6.2898 / 30 / 1000)
    assert r["filas"][0]["participacion"] == pytest.approx(600 / 700)
    assert "85,7%" in r["texto"]
    assert ejecutar(con, "variacion_interanual", {})["valor"] == pytest.approx(700 / 400 - 1)


def test_operator_lookup_accepts_variants_and_rejects_unknown(con):
    assert ejecutar(con, "produccion_vm", {"operador": "Vista Energy Argentina"})["filas"][0]["pozos_activos"] == 1
    with pytest.raises(ErrorOperacion, match="Opciones"):
        ejecutar(con, "produccion_vm", {"operador": "Exxon"})


def test_bad_arguments_never_reach_sql(con):
    with pytest.raises(ValidationError):
        ejecutar(con, "produccion_vm", {"mes": "2025-09'; drop table fct_produccion; --"})
    with pytest.raises(ErrorOperacion):
        ejecutar(con, "produccion_vm", {"mes": "2030-01"})
    with pytest.raises(ErrorOperacion):
        ejecutar(con, "pagina_wiki", {"ruta": "../site/index.md"})
    assert con.execute("select count(*) from fct_produccion").fetchall()[0][0] == 4


def test_router_retries_once_with_the_error_then_gives_up(con):
    ok = elegir(con, "q", guion('{"op": "produccion_vm", "args": {"operador": "Exxon"}}',
                                '{"op": "produccion_vm", "args": {"operador": "YPF"}}'))
    assert ok["op"] == "produccion_vm" and ok["intentos"] == 2
    mal = elegir(con, "q", guion("no sé", '{"op": "inventada"}'))
    assert mal["op"] == "error"
    assert elegir(con, "q", guion('{"op": "abstener", "motivo": "precios"}'))["op"] == "abstener"


def test_scoring_compares_values_not_spelling(con):
    item = {"esperado": {"op": "produccion_vm", "args": {"operador": "YPF"}}}
    assert puntuar(con, item, elegir(con, "q", guion('{"op": "produccion_vm", "args": {"operador": "ypf"}}')))["correcto"]
    assert not puntuar(con, item, elegir(con, "q", guion('{"op": "produccion_vm", "args": {}}')))["correcto"]
    assert not puntuar(con, {"esperado": {"op": "abstener", "args": {}}},
                       elegir(con, "q", guion('{"op": "produccion_vm", "args": {}}')))["correcto"]


def test_eval_items_are_valid_calls_and_splits_are_disjoint():
    items = cargar("todo")
    assert {i["split"] for i in items} == {"dev", "holdout"}
    assert len({i["id"] for i in items}) == len(items)
    assert len({i["pregunta"] for i in items}) == len(items)
    for i in items:
        e = i["esperado"]
        if e["op"] != "abstener":
            REGISTRO[e["op"]].args.model_validate(e["args"])
    assert sum(i["esperado"]["op"] == "abstener" for i in items) >= 6


def test_mcp_exposes_every_operation_read_only():
    from agente.mcp_server import crear_servidor
    tools = asyncio.run(crear_servidor().list_tools())
    assert {t.name for t in tools} == set(REGISTRO)
    assert all(t.annotations.read_only_hint for t in tools)
    curva = next(t for t in tools if t.name == "curva_tipo")
    assert curva.input_schema["properties"]["cohorte"]["minimum"] == 2017
    json.dumps([t.input_schema for t in tools])
