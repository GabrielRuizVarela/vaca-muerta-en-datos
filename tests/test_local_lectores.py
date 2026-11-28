"""L1c: pipeline.local lee --daily y --shutins de punta a punta (pipeline/local.py). Todo el dato es sintetico y vive en tmp_path."""
from __future__ import annotations

import csv
import json

import pytest

from pipeline import local, local_cierres, local_diario
from pipeline.claims import CAPACIDADES, verificar
from pipeline.ingest import ROOT
from tests.test_local import sintetico

PADRE = 10000   # un padre del sintetico, con produccion mensual de 2018-01 a 2021-12
OTRO = 10001
AJENO = 77      # pozo que no esta en pozos.csv


def _escribe(ruta, columnas, filas):
    with open(ruta, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    return ruta


def _mensual(mensual_csv, pozo, mes):
    with open(mensual_csv, newline="") as f:
        for fila in csv.DictReader(f):
            if int(fila["pozo_id"]) == pozo and fila["mes"] == mes:
                return float(fila["petroleo_m3"])
    raise AssertionError("mes no encontrado")


def _archivos(tmp_path, mensual):
    """diario.csv: el PADRE en 2019-03 (31 dias de 5 m3) y 2019-04 (30 dias, el total del mensual), mas un pozo ajeno.

    cierres.csv: el PADRE cerrado de 2019-03-31 18:00 a 2019-04-01 06:00 (6 h y 6 h), OTRO abierto desde 2021-12-31 12:00 (sin fin:
    se cierra al final del ultimo mes del mensual) y una fila de un pozo ajeno.
    """
    filas = [[PADRE, f"2019-03-{d:02d}", "5", "", ""] for d in range(1, 32)]
    por_dia = _mensual(mensual, PADRE, "2019-04") / 30
    filas += [[PADRE, f"2019-04-{d:02d}", repr(por_dia), "", ""] for d in range(1, 31)]
    filas.append([AJENO, "2019-03-01", "9", "", ""])
    diario = _escribe(tmp_path / "diario.csv", ["pozo_id", "fecha", "petroleo_m3", "agua_m3", "horas_produccion"], filas)
    cierres = _escribe(tmp_path / "cierres.csv", ["pozo_id", "inicio", "fin", "motivo"],
                       [[PADRE, "2019-03-31 18:00", "2019-04-01 06:00", "Mantenimiento"],
                        [OTRO, "2021-12-31 12:00", "", ""],
                        [AJENO, "2019-03-01", "2019-03-02", ""]])
    return diario, cierres


def _corre(pozos, mensual, out, *extra):
    argv = ["--wells", str(pozos), "--monthly", str(mensual), "--out", str(out), "--reps", "200", *extra]
    assert local.main(argv) == 0
    return json.loads((out / "resumen.json").read_text())


def test_de_punta_a_punta_con_diario_y_cierres(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    diario, cierres = _archivos(tmp_path, mensual)
    out = tmp_path / "out"
    res = _corre(pozos, mensual, out, "--daily", str(diario), "--shutins", str(cierres))
    d, c = res["diario"], res["cierres"]
    assert (d["filas_leidas"], d["filas_ignoradas"], d["filas_usadas"], d["pozos"], d["meses"]) == (62, 1, 61, 1, 2)
    assert (d["fecha_desde"], d["fecha_hasta"]) == ("2019-03-01", "2019-04-30")
    assert d["meses_comparados"] == 2
    # una cuenta aparte: 2019-04 coincide con el mensual por construccion; 2019-03 (31 x 5 m3) difiere si pasa del 2%
    m3 = _mensual(mensual, PADRE, "2019-03")
    assert d["meses_difieren"] == (1 if abs(155 - m3) > 0.02 * m3 else 0)
    assert (c["filas"], c["pozos"], c["abiertos"], c["superpuestos"], c["ignoradas"]) == (2, 2, 1, 0, 1)
    assert c["cierre_abiertos"] == "ultimo_mes"
    # los avisos de los dos lectores llegan al resumen, con conteos y sin ids ni celdas
    avisos = res["avisos"]
    assert any("Se ignoraron 1 filas del diario" in a for a in avisos)
    assert any("Se ignoraron 1 filas de cierres.csv" in a for a in avisos)
    assert any("1 intervalos de cierres.csv no traen fin" in a for a in avisos)
    assert not any(str(AJENO) in a or str(PADRE) in a for a in avisos)
    md = (out / "resumen.md").read_text()
    assert "Diario de producción (diario.csv): 61 filas de 1 pozos" in md
    assert "Registro de cierres (cierres.csv): 2 intervalos de 2 pozos" in md
    assert "no se cruzan con las fracturas" in md and "—" not in md and "–" not in md
    # lo de siempre sigue ahi y no cambia por leer los dos archivos
    assert res["brecha"]["k1"]["n_cercanos"] == 24 and res["dosis"]["corrio"] is False


def test_las_cifras_de_siempre_no_cambian_con_los_dos_archivos(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    diario, cierres = _archivos(tmp_path, mensual)
    sin = _corre(pozos, mensual, tmp_path / "sin")
    con = _corre(pozos, mensual, tmp_path / "con", "--daily", str(diario), "--shutins", str(cierres))
    assert "diario" not in sin and "cierres" not in sin
    for clave in ("entradas", "brecha", "dosis"):
        assert sin[clave] == con[clave]
    assert (tmp_path / "sin" / "tarjeta.json").read_bytes() == (tmp_path / "con" / "tarjeta.json").read_bytes()
    assert "Diario de producción" not in (tmp_path / "sin" / "resumen.md").read_text()


def test_cada_archivo_es_opcional_por_separado(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    diario, cierres = _archivos(tmp_path, mensual)
    solo_diario = _corre(pozos, mensual, tmp_path / "a", "--daily", str(diario))
    solo_cierres = _corre(pozos, mensual, tmp_path / "b", "--shutins", str(cierres))
    assert "diario" in solo_diario and "cierres" not in solo_diario
    assert "cierres" in solo_cierres and "diario" not in solo_cierres


def test_solo_escribe_en_salida_con_los_dos_archivos(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    diario, cierres = _archivos(tmp_path, mensual)
    out = tmp_path / "out"
    _corre(pozos, mensual, out, "--daily", str(diario), "--shutins", str(cierres))
    todos = {p for p in tmp_path.rglob("*") if p.is_file()}
    resto = todos - {pozos, mensual, diario, cierres}
    assert resto <= {out / "resumen.json", out / "resumen.md", out / "eventos.csv", out / "tarjeta.json", out / "tarjeta.md",
                     out / "diario_mes.csv", out / "diario_contra_mensual.csv", out / "cierres_mes.csv"}


def _filas(ruta):
    with open(ruta, newline="") as f:
        return list(csv.DictReader(f))


def test_las_tablas_por_pozo_y_mes_salen_en_out(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    diario, cierres = _archivos(tmp_path, mensual)
    out = tmp_path / "out"
    res = _corre(pozos, mensual, out, "--daily", str(diario), "--shutins", str(cierres))
    assert res["tablas"] == ["diario_mes.csv", "diario_contra_mensual.csv", "cierres_mes.csv"]
    dm = _filas(out / "diario_mes.csv")
    assert list(dm[0]) == ["pozo_id", "mes", "petroleo_m3", "agua_m3", "dias_registrados", "dias_con_produccion", "dias_mes", "completo"]
    assert [(r["pozo_id"], r["mes"], r["dias_registrados"]) for r in dm] == [(str(PADRE), "2019-03-01", "31"),
                                                                              (str(PADRE), "2019-04-01", "30")]
    assert float(dm[0]["petroleo_m3"]) == 155 and dm[0]["agua_m3"] == ""
    dc = _filas(out / "diario_contra_mensual.csv")
    assert list(dc[0]) == ["pozo_id", "mes", "petroleo_mensual_m3", "petroleo_diario_m3", "difiere"] and len(dc) == res["diario"]["meses_comparados"]
    assert sum(r["difiere"] == "True" for r in dc) == res["diario"]["meses_difieren"]
    cm = _filas(out / "cierres_mes.csv")
    assert list(cm[0]) == ["pozo_id", "mes", "horas_cerrado", "dias_cerrado_completo", "n_cierres", "cerrado_todo_el_mes"]
    assert {(r["pozo_id"], r["mes"]) for r in cm if r["pozo_id"] == str(PADRE)} == {(str(PADRE), "2019-03-01"), (str(PADRE), "2019-04-01")}
    assert {float(r["horas_cerrado"]) for r in cm if r["pozo_id"] == str(PADRE)} == {6.0}
    md = (out / "resumen.md").read_text()
    assert "diario_mes.csv, diario_contra_mensual.csv, cierres_mes.csv" in md and "2%" in md
    # cada archivo por separado escribe solo el suyo; sin ellos no sale ninguna tabla
    _corre(pozos, mensual, tmp_path / "a", "--daily", str(diario))
    _corre(pozos, mensual, tmp_path / "b", "--shutins", str(cierres))
    nombres = lambda d: sorted(p.name for p in d.glob("*_mes.csv")) + sorted(p.name for p in d.glob("diario_contra*"))
    assert nombres(tmp_path / "a") == ["diario_mes.csv", "diario_contra_mensual.csv"] and nombres(tmp_path / "b") == ["cierres_mes.csv"]


def test_sin_los_archivos_la_salida_es_la_de_siempre(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    sin = tmp_path / "sin"
    res = _corre(pozos, mensual, sin)
    assert "tablas" not in res
    assert sorted(p.name for p in sin.iterdir()) == ["eventos.csv", "resumen.json", "resumen.md", "tarjeta.json", "tarjeta.md"]
    assert "Tablas por pozo y mes" not in (sin / "resumen.md").read_text()


def test_un_error_del_lector_sale_con_codigo_2_sin_valores(tmp_path, capsys):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    malo = _escribe(tmp_path / "diario.csv", ["pozo_id", "fecha", "petroleo_m3"],
                    [[PADRE, "2019-03-01", "1"], [PADRE, "2019-03-01", "2"]])   # (pozo_id, fecha) repetido
    with pytest.raises(SystemExit) as e:
        local.main(["--wells", str(pozos), "--monthly", str(mensual), "--out", str(tmp_path / "out"), "--daily", str(malo)])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "fecha" in err and str(PADRE) not in err and "2019-03-01" not in err


def test_rutas_de_los_lectores_pasan_por_comprobar_rutas(tmp_path, capsys):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    for bandera in ("--daily", "--shutins"):
        with pytest.raises(SystemExit) as e:   # README.md esta versionado dentro del repo
            local.main(["--wells", str(pozos), "--monthly", str(mensual), "--out", str(tmp_path / "out"),
                        bandera, str(ROOT / "README.md")])
        assert e.value.code == 2
        assert "versionada" in capsys.readouterr().err
    assert not (tmp_path / "out" / "resumen.json").exists()


def test_entradas_son_las_de_los_modulos_y_las_frases_son_verdad():
    assert local.ENTRADAS[2:] == (local_diario.ENTRADA, local_cierres.ENTRADA)
    assert any("diari" in e for e in local.ENTRADAS) and any("cierre" in e for e in local.ENTRADAS)
    capacidades = {r.claim.id: r.estado for r in verificar([c for c in CAPACIDADES if c.id.startswith(("cap_local_diario",
                                                                                                       "cap_local_cierres"))])}
    assert len(capacidades) == 11 and set(capacidades.values()) == {"PASS"}
