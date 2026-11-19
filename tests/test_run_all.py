"""run_all with a fake step registry: no step rebuilds the warehouse."""
import pytest

from pipeline import run_all
from pipeline.run_all import Paso


@pytest.fixture
def falsos(monkeypatch):
    pasos = [Paso("ingest", "pipeline.ingest", solo_con_flag=True),
             Paso("a", "pipeline.a"),
             Paso("b", "pipeline.b"),
             Paso("falta", "pipeline.no_existe_nunca", opcional=True),
             Paso("c", "pipeline.c")]
    llamados = []
    fallan = set()

    def ejecutor(p):
        llamados.append(p.nombre)
        return 3 if p.nombre in fallan else 0

    monkeypatch.setattr(run_all, "PASOS", pasos)
    monkeypatch.setattr(run_all, "ejecutar", ejecutor)
    return llamados, fallan


def test_cadena_completa_en_orden_sin_ingest_ni_modulo_ausente(falsos, capsys):
    llamados, _ = falsos
    assert run_all.main([]) == 0
    assert llamados == ["a", "b", "c"]
    out = capsys.readouterr().out
    assert "total" in out and out.count(" OK") == 3


def test_with_ingest_agrega_ingest_primero(falsos):
    llamados, _ = falsos
    assert run_all.main(["--with-ingest"]) == 0
    assert llamados == ["ingest", "a", "b", "c"]


def test_only_conserva_el_orden_de_la_cadena(falsos):
    llamados, _ = falsos
    assert run_all.main(["--only", "c,a"]) == 0
    assert llamados == ["a", "c"]


def test_skip(falsos):
    llamados, _ = falsos
    assert run_all.main(["--skip", "b"]) == 0
    assert llamados == ["a", "c"]


def test_se_detiene_en_el_primer_fallo(falsos, capsys):
    llamados, fallan = falsos
    fallan.add("a")
    assert run_all.main([]) == 1
    assert llamados == ["a"]
    cap = capsys.readouterr()
    assert "FALLO (exit 3)" in cap.out and "no corrio" in cap.out
    assert "--only a,b,c" in cap.err


def test_paso_desconocido(falsos):
    with pytest.raises(SystemExit):
        run_all.main(["--only", "zzz"])


def test_list_no_ejecuta_nada(falsos, capsys):
    llamados, _ = falsos
    assert run_all.main(["--list"]) == 0
    assert llamados == []
    out = capsys.readouterr().out
    assert "no disponible" in out and "con --with-ingest" in out


def test_registro_real_tiene_el_orden_documentado():
    nombres = [p.nombre for p in run_all.PASOS]
    assert nombres[:5] == ["ingest", "build", "carga", "costo", "robustez"]
    assert nombres[-5:] == ["report", "replay", "mundo", "globo", "claims"]
    assert nombres[nombres.index("bloques") + 1] == "carga_anual"
    assert next(p for p in run_all.PASOS if p.nombre == "ingest").solo_con_flag


def test_pasos_de_colorado_son_opcionales_y_estan_en_la_lista(capsys):
    co = [p for p in run_all.PASOS if p.solo_con_colorado]
    assert [p.nombre for p in co] == ["colorado_ingest", "colorado_build", "replicacion", "globo"]
    por_defecto = [p.nombre for p in run_all.seleccionar(run_all.PASOS)]
    assert not {p.nombre for p in co} & set(por_defecto)
    con_flag = [p.nombre for p in run_all.seleccionar(run_all.PASOS, con_colorado=True)]
    assert con_flag.index("colorado_ingest") < con_flag.index("colorado_build") < con_flag.index("replicacion") < con_flag.index("wiki")
    assert run_all.main(["--list"]) == 0
    assert "con --with-colorado" in capsys.readouterr().out
    corren, omitidos = run_all.pasos_muestra()
    assert not {"colorado_ingest", "colorado_build", "replicacion", "globo"} & (set(omitidos) | {p.nombre for p in corren})
