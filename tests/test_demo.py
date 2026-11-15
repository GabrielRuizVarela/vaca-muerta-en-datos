import re

import pytest

from agente.demo import SELECCION, demo, main
from agente.ops import REGISTRO, conectar
from pipeline.ingest import DATA

needs_wh = pytest.mark.skipif(not (DATA / "warehouse.duckdb").exists(), reason="sin warehouse real")


def _salida():
    con = conectar()
    if con.execute("select count(*) from information_schema.tables where table_name = 'fct_evento'").fetchall()[0][0] == 0:
        pytest.skip("falta correr pipeline.build")
    return demo(con)


@needs_wh
def test_demo_prints_five_blocks_with_real_operations_and_citation():
    s = _salida()
    bloques = s.split("\n\n")[1:]
    assert len(bloques) == len(SELECCION) == 5
    for b in bloques[:-1]:
        op = re.search(r"^Operación: (\w+)$", b, re.M).group(1)
        assert op in REGISTRO
        assert re.search(r"^Cita: tablas .+; datos a \d{4}-\d{2}; hash del crudo \w+ [0-9a-f]{12}", b, re.M)
    assert "Operación: abstener" in bloques[-1] and "\nCita:" in bloques[-1]


@needs_wh
def test_demo_abstention_has_no_figure_and_output_is_deterministic():
    s = _salida()
    abst = s.split("\n\n")[-1]
    respuesta = re.search(r"^Respuesta: (.*)$", abst, re.M).group(1)
    assert not re.search(r"\d", respuesta) and "no incluyen" in respuesta
    assert s == _salida()
    assert chr(0x2014) not in s and chr(0x2013) not in s


def test_modelo_flag_without_endpoint_exits_2(monkeypatch, capsys):
    monkeypatch.delenv("VM_LLM_URL", raising=False)
    monkeypatch.delenv("VM_LLM_MODEL", raising=False)
    monkeypatch.setattr("sys.argv", ["demo", "--modelo"])
    assert main() == 2
    assert "VM_LLM_URL" in capsys.readouterr().out
