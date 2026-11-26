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
    assert nombres[nombres.index("bloques") + 1] == "dia_inicio"
    assert nombres[nombres.index("dia_inicio") + 1] == "carga_anual"
    assert next(p for p in run_all.PASOS if p.nombre == "ingest").solo_con_flag
    assert nombres.index("trayectorias") < nombres.index("hijo_pad") < nombres.index("wiki")
    assert nombres.index("golpes_mismo_padre") < nombres.index("calendario_golpes") < nombres.index("wiki")
    # the causal pages are built before wiki, which deletes them when their marts are absent
    assert nombres.index("hijo_pad") < nombres.index("causal") < nombres.index("causal_profundo") < nombres.index("colorado_build") < nombres.index("causal_profundo_colorado") < nombres.index("wiki")
    # this phase's designs: D10 to D12 and the bound after causal_profundo; Holm after both basins, before the pages
    assert nombres.index("causal_profundo") < nombres.index("causal_exposicion") < nombres.index("apilado") < nombres.index("cota_rr")
    assert nombres.index("causal_profundo_colorado") < nombres.index("causal_profundo_wyoming") < nombres.index("inferencia") < nombres.index("wiki")
    assert next(p for p in run_all.PASOS if p.nombre == "causal_profundo_wyoming").requiere == "data/wyoming/warehouse.duckdb"
    # the basin family (inferencia), the replication pages (wiki) and the globe read mart_replicacion_wyoming: build it before them
    assert nombres.index("causal_profundo_wyoming") < nombres.index("replicacion_wyoming") < nombres.index("inferencia")
    wy = next(p for p in run_all.PASOS if p.nombre == "replicacion_wyoming")
    assert (wy.modulo, wy.args, wy.requiere) == ("pipeline.replicacion", ("--cuenca", "wyoming"), "data/wyoming/warehouse.duckdb")
    assert next(p for p in run_all.PASOS if p.nombre == "globo").requiere == "data/wyoming/warehouse.duckdb"


def test_pasos_de_colorado_son_opcionales_y_estan_en_la_lista(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(run_all, "ROOT", tmp_path)
    (tmp_path / "data" / "colorado").mkdir(parents=True)
    (tmp_path / "data" / "colorado" / "warehouse.duckdb").write_text("")
    co = [p for p in run_all.PASOS if p.solo_con_colorado]
    assert [p.nombre for p in co] == ["colorado_ingest", "colorado_build", "globo"]
    por_defecto = [p.nombre for p in run_all.seleccionar(run_all.PASOS)]
    assert not {p.nombre for p in co} & set(por_defecto)
    # the replication steps are not opt-in: they run whenever the Colorado warehouse is on disk
    for n in ("replicacion", "dia_inicio_colorado", "dias_perdidos_colorado", "golpes_mismo_mes_colorado", "golpes_mismo_padre_colorado"):
        p = next(p for p in run_all.PASOS if p.nombre == n)
        assert not p.solo_con_colorado and p.requiere == "data/colorado/warehouse.duckdb"
    # the globe reads both basins: without Wyoming's warehouse it is left out instead of crashing at the end of the chain
    fuera: dict[str, str] = {}
    assert "globo" not in [p.nombre for p in run_all.seleccionar(run_all.PASOS, con_colorado=True, fuera=fuera)]
    assert fuera["globo"] == "falta data/wyoming/warehouse.duckdb"
    (tmp_path / "data" / "wyoming").mkdir(parents=True)
    (tmp_path / "data" / "wyoming" / "warehouse.duckdb").write_text("")
    con_flag =[p.nombre for p in run_all.seleccionar(run_all.PASOS, con_colorado=True)]
    assert con_flag.index("colorado_ingest") < con_flag.index("colorado_build") < con_flag.index("causal_profundo_colorado") < con_flag.index("replicacion") < con_flag.index("wiki")
    assert con_flag.index("colorado_build") < con_flag.index("dia_inicio_colorado") < con_flag.index("globo")
    assert con_flag.index("dia_inicio") < con_flag.index("dia_inicio_colorado") < con_flag.index("wiki")
    assert con_flag.index("dias_perdidos") < con_flag.index("dias_perdidos_colorado") < con_flag.index("wiki")
    assert con_flag.index("golpes_mismo_mes") < con_flag.index("golpes_mismo_mes_colorado") < con_flag.index("wiki")
    assert con_flag.index("golpes_mismo_mes") < con_flag.index("golpes_mismo_padre") < con_flag.index("wiki")
    assert con_flag.index("trayectorias") < con_flag.index("alcance_rama") < con_flag.index("wiki")
    assert con_flag.index("alcance_rama") < con_flag.index("riesgo") < con_flag.index("wiki")
    assert con_flag.index("potencia_dosis") < con_flag.index("dosis_geometria") < con_flag.index("wiki")
    assert con_flag.index("trayectorias") < con_flag.index("dosis_geometria")
    assert con_flag.index("golpes_mismo_mes_colorado") < con_flag.index("golpes_mismo_padre_colorado") < con_flag.index("wiki")
    assert run_all.main(["--list"]) == 0
    assert "con --with-colorado" in capsys.readouterr().out
    corren, omitidos = run_all.pasos_muestra()
    assert not {"colorado_ingest", "colorado_build", "globo"} & (set(omitidos) | {p.nombre for p in corren})


def test_requiere_deja_fuera_el_paso_si_falta_el_archivo(tmp_path, monkeypatch):
    monkeypatch.setattr(run_all, "ROOT", tmp_path)
    pasos = [run_all.Paso("a", "m.a"), run_all.Paso("b", "m.b", requiere="data/x.duckdb"), run_all.Paso("c", "m.c")]
    fuera: dict[str, str] = {}
    assert [p.nombre for p in run_all.seleccionar(pasos, fuera=fuera)] == ["a", "c"]
    assert fuera == {"b": "falta data/x.duckdb"}
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.duckdb").write_text("")
    fuera = {}
    assert [p.nombre for p in run_all.seleccionar(pasos, fuera=fuera)] == ["a", "b", "c"]
    assert fuera == {}


def test_paso_causal_de_colorado_no_es_opt_in_y_requiere_su_base():
    p = next(p for p in run_all.PASOS if p.nombre == "causal_profundo_colorado")
    assert not p.solo_con_colorado
    assert p.requiere == "data/colorado/warehouse.duckdb" and p.args == ("--cuenca", "colorado")


def test_correr_omite_el_paso_cuyo_requisito_no_aparecio(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_all, "ROOT", tmp_path)
    corridos = []
    pasos = [run_all.Paso("a", "m.a"), run_all.Paso("b", "m.b", requiere="data/x.duckdb"), run_all.Paso("c", "m.c")]
    filas = run_all.correr(pasos, ejecutor=lambda p: corridos.append(p.nombre) or 0)
    assert corridos == ["a", "c"] and [f[2] for f in filas] == ["OK", "omitido", "OK"]


def test_con_colorado_no_deja_fuera_los_pasos_que_leen_el_almacen_que_se_arma(tmp_path, monkeypatch):
    monkeypatch.setattr(run_all, "ROOT", tmp_path)   # no data/colorado/warehouse.duckdb yet
    nombres = [p.nombre for p in run_all.seleccionar(run_all.PASOS, con_colorado=True)]
    assert {"causal_profundo_colorado", "replicacion", "dia_inicio_colorado", "golpes_mismo_padre_colorado"} <= set(nombres)
    assert "replicacion" not in [p.nombre for p in run_all.seleccionar(run_all.PASOS)]


def test_only_con_un_paso_sin_su_requisito_sale_con_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_all, "ROOT", tmp_path)   # no data/colorado/warehouse.duckdb
    assert run_all.main(["--only", "causal_profundo_colorado"]) == 2
    assert "causal_profundo_colorado" in capsys.readouterr().err
    # --with-colorado only covers the missing warehouse when colorado_build is in the run too
    assert run_all.main(["--only", "causal_profundo_colorado", "--with-colorado"]) == 2
    assert [p.nombre for p in run_all.seleccionar(run_all.PASOS, solo=["colorado_build", "causal_profundo_colorado"],
                                                   con_colorado=True)] == ["colorado_build", "causal_profundo_colorado"]
