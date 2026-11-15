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
        if "calls" in e:
            assert len(e["calls"]) == 2 and "op" not in e
        for c in _llamadas_esperadas(e):
            REGISTRO[c["op"]].args.model_validate(c["args"])
    assert sum(i["esperado"].get("op") == "abstener" for i in items) >= 6
    assert sum("calls" in i["esperado"] for i in items) >= 5


def _llamadas_esperadas(e):
    if "calls" in e:
        return e["calls"]
    return [] if e["op"] == "abstener" else [e]


def test_router_runs_two_calls_and_joins_their_answers(con):
    from agente.router import responder
    dos = '{"calls": [{"op": "produccion_vm", "args": {"operador": "YPF"}}, {"op": "variacion_interanual", "args": {}}]}'
    e = elegir(con, "q", guion(dos))
    assert e["op"] == ["produccion_vm", "variacion_interanual"] and e["intentos"] == 1
    assert e["args"][0]["operador"] == "YPF" and len(e["resultados"]) == 2 and "resultado" not in e
    texto = responder(con, "q", guion(dos))
    assert texto.count("Fuente:") == 2 and "Operación: produccion_vm" in texto and "Operación: variacion_interanual" in texto
    assert texto.index("YPF produjo") < texto.index("Operación: produccion_vm") < texto.index("Operación: variacion_interanual")
    # the single form and a one-element list both still give one result
    uno = elegir(con, "q", guion('{"calls": [{"op": "produccion_vm", "args": {}}]}'))
    assert uno["op"] == "produccion_vm" and uno["resultado"]["op"] == "produccion_vm"


def test_router_rejects_three_calls_then_accepts_the_correction(con):
    llamada = '{"op": "produccion_vm", "args": {}}'
    visto = []

    def llm(msgs):
        visto.append(msgs)
        if len(visto) == 1:
            return f'{{"calls": [{llamada}, {llamada}, {llamada}]}}'
        return '{"calls": [{"op": "produccion_vm", "args": {}}, {"op": "variacion_interanual", "args": {}}]}'

    e = elegir(con, "q", llm)
    assert e["intentos"] == 2 and len(e["resultados"]) == 2
    assert "máximo es 2" in visto[1][-1]["content"]
    assert elegir(con, "q", guion(f'{{"calls": [{llamada}, {llamada}, {llamada}]}}', "no sé"))["op"] == "error"
    # an error inside one of two calls names the call and is fed back
    malo = elegir(con, "q", guion('{"calls": [{"op": "produccion_vm", "args": {}}, {"op": "produccion_vm", "args": {"operador": "Exxon"}}]}',
                                  '{"op": "abstener", "motivo": "x"}'))
    assert malo["op"] == "abstener"
    inventada = elegir(con, "q", guion('{"calls": [{"op": "abstener"}, {"op": "produccion_vm"}]}', '{"calls": []}'))
    assert inventada["op"] == "error"


def test_scoring_multi_op_items(con):
    item = {"esperado": {"calls": [{"op": "produccion_vm", "args": {"operador": "YPF"}},
                                   {"op": "variacion_interanual", "args": {}}]}}
    bien = '{"calls": [{"op": "produccion_vm", "args": {"operador": "ypf"}}, {"op": "variacion_interanual", "args": {}}]}'
    assert puntuar(con, item, elegir(con, "q", guion(bien)))["correcto"]
    # wrong number of calls, wrong op order, wrong value, or abstaining all fail
    assert not puntuar(con, item, elegir(con, "q", guion('{"op": "produccion_vm", "args": {"operador": "YPF"}}')))["correcto"]
    cambiado = '{"calls": [{"op": "variacion_interanual", "args": {}}, {"op": "produccion_vm", "args": {"operador": "YPF"}}]}'
    assert not puntuar(con, item, elegir(con, "q", guion(cambiado)))["correcto"]
    valor = '{"calls": [{"op": "produccion_vm", "args": {"operador": "Vista"}}, {"op": "variacion_interanual", "args": {}}]}'
    assert not puntuar(con, item, elegir(con, "q", guion(valor)))["correcto"]
    assert not puntuar(con, item, elegir(con, "q", guion('{"op": "abstener"}')))["correcto"]
    # a single-op item is not satisfied by two calls
    simple = {"esperado": {"op": "produccion_vm", "args": {"operador": "YPF"}}}
    assert not puntuar(con, simple, elegir(con, "q", guion(bien)))["correcto"]


def test_mcp_exposes_every_operation_read_only():
    from agente.mcp_server import crear_servidor
    tools = asyncio.run(crear_servidor().list_tools())
    assert {t.name for t in tools} == set(REGISTRO)
    assert all(t.annotations.read_only_hint for t in tools)
    curva = next(t for t in tools if t.name == "curva_tipo")
    assert curva.input_schema["properties"]["cohorte"]["minimum"] == 2017
    json.dumps([t.input_schema for t in tools])


@pytest.fixture
def real():
    from agente.ops import conectar
    from pipeline.ingest import DATA
    if not (DATA / "warehouse.duckdb").exists():
        pytest.skip("warehouse.duckdb not built")
    con = conectar()
    yield con
    con.close()


def test_eventos_pozo_counts_and_rejects_bad_arguments(real):
    sigla = real.execute("select sigla from dim_pozo p join fct_evento e using (pozo_id) limit 1").fetchall()[0][0]
    r = ejecutar(real, "eventos_pozo", {"sigla": sigla})
    assert isinstance(r["valor"], int) and r["valor"] >= 1 and r["texto"] and len(r["filas"]) <= 20
    with pytest.raises(ErrorOperacion):
        ejecutar(real, "eventos_pozo", {"sigla": "no existe zzz"})
    with pytest.raises(ValidationError):
        ejecutar(real, "eventos_pozo", {"sigla": sigla, "tipo": "terremoto"})


def test_clases_interferencia_share_and_footprint_wording(real):
    r = ejecutar(real, "clases_interferencia", {})
    assert 0 <= r["valor"] <= 1 and "no una causa" in r["texto"]
    assert sum(f["participacion"] for f in r["filas"]) == pytest.approx(1)
    with pytest.raises(ValidationError):
        ejecutar(real, "clases_interferencia", {"banda": "lejano"})
    with pytest.raises(ErrorOperacion):
        ejecutar(real, "clases_interferencia", {"operador": "Exxon"})


def test_libro_hallazgos_reads_ledger_and_lists_valid_ids(real):
    todo = ejecutar(real, "libro_hallazgos", {})
    assert isinstance(todo["valor"], int) and todo["texto"]
    uno = ejecutar(real, "libro_hallazgos", {"id": "brecha_mes1"})
    assert isinstance(uno["valor"], float) and uno["filas"][0]["umbral"] == pytest.approx(-0.10)
    with pytest.raises(ErrorOperacion, match="brecha_mes1"):
        ejecutar(real, "libro_hallazgos", {"id": "inventada"})
    with pytest.raises(ValidationError):
        ejecutar(real, "libro_hallazgos", {"id": "x" * 100})


NUEVOS = {f"dev-{n}" for n in range(34, 40)} | {f"holdout-{n}" for n in range(22, 26)}


def test_new_eval_items_run_against_the_real_warehouse(real):
    items = [i for i in cargar("todo") if i["id"] in NUEVOS]
    assert len(items) == 10
    assert sum("calls" in i["esperado"] for i in items) == 5
    for i in items:
        for c in _llamadas_esperadas(i["esperado"]):
            r = ejecutar(real, c["op"], c["args"])
            assert r["texto"] and r["valor"] is not None
        if "calls" in i["esperado"]:  # an exact echo of the expected calls scores as correct
            eco = json.dumps({"calls": i["esperado"]["calls"]})
            assert puntuar(real, i, elegir(real, i["pregunta"], guion(eco)))["correcto"]


def _mart_robustez(con):
    con.execute("""create table mart_robustez_eje (grupo varchar, subconjunto varchar, n integer, eje double, ic_bajo double,
                   ic_alto double, ancho_ic double, p_perm double, dif_eje_completo double, dif_shmax double)""")
    con.execute("""insert into mart_robustez_eje values
        ('completa', 'Muestra completa', 100, 92.0, 70.0, 120.0, 50.0, 0.02, 0.0, 24.5),
        ('area', 'Sin LOMA CAMPANA', 60, 79.0, 30.0, 122.0, 92.0, 0.22, -13.0, 11.5),
        ('area', 'Sin BANDURRIA SUR', 90, 93.0, 70.0, 121.0, 51.0, 0.006, 1.0, 25.5),
        ('operador', 'Padre YPF', 70, 99.0, 71.0, 125.0, 54.0, 0.034, 7.0, 31.5)""")


def test_robustez_eje_counts_defined_subsets_and_rejects_unknown_names(con):
    with pytest.raises(ErrorOperacion, match="pipeline.robustez"):
        ejecutar(con, "robustez_eje", {})
    _mart_robustez(con)
    todo = ejecutar(con, "robustez_eje", {})
    assert todo["valor"] == 2 and len(todo["filas"]) == 4  # muestra completa + 3 subconjuntos; 2 con IC de menos de 90
    assert "2 de 3 subconjuntos" in todo["texto"] and "no es firme" in todo["texto"] and "Sin LOMA CAMPANA" in todo["texto"]
    uno = ejecutar(con, "robustez_eje", {"subconjunto": "sin loma campana"})
    assert uno["valor"] == pytest.approx(79.0) and "no definido" in uno["texto"] and "0,220" in uno["texto"]
    assert ejecutar(con, "robustez_eje", {"subconjunto": "padre ypf"})["filas"][0]["definido"] is True
    for malo in ("inventado", "sin"):  # no existe / ambiguo: ambos listan los nombres válidos
        with pytest.raises(ErrorOperacion, match="Padre YPF"):
            ejecutar(con, "robustez_eje", {"subconjunto": malo})
    with pytest.raises(ValidationError):
        ejecutar(con, "robustez_eje", {"subconjunto": "x" * 100})


def test_robustez_eje_real_warehouse_matches_sql(real):
    from pipeline.costo import ANCHO_MAX
    esperado = real.execute("select count(*) from mart_robustez_eje where grupo <> 'completa' and ancho_ic < ?", [ANCHO_MAX]).fetchone()[0]
    r = ejecutar(real, "robustez_eje", {})
    assert r["valor"] == esperado and r["valor"] > 0 and "firme" in r["texto"]
    nombre = real.execute("select subconjunto from mart_robustez_eje where grupo = 'periodo' order by 1 limit 1").fetchone()[0]
    assert ejecutar(real, "robustez_eje", {"subconjunto": nombre})["filas"][0]["subconjunto"] == nombre


def test_robustez_eval_items_run_and_one_combines_two_operations(real):
    items = [i for i in cargar("todo") if i["id"] in {"dev-40", "dev-41", "holdout-26", "holdout-27"}]
    assert len(items) == 4 and sum("calls" in i["esperado"] for i in items) == 1
    assert {i["split"] for i in items} == {"dev", "holdout"}
    for i in items:
        for c in _llamadas_esperadas(i["esperado"]):
            assert ejecutar(real, c["op"], c["args"])["texto"]


def test_robustez_eje_blank_subset_means_all(con):
    _mart_robustez(con)
    assert ejecutar(con, "robustez_eje", {"subconjunto": "  "})["valor"] == ejecutar(con, "robustez_eje", {})["valor"]
