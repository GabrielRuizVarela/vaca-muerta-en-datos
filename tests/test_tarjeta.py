"""Tests de la tarjeta del operador y del modo local con agua (pipeline/tarjeta.py, porcion D)."""
from __future__ import annotations

import csv
import json
import re
import tempfile
from pathlib import Path

import numpy as np
import pytest

from pipeline import local, tarjeta
from pipeline.ingest import DATA
from tests.test_local import sintetico

REPS = 200


def _con_agua(pozos, mensual, con_dias=True, seed=5):
    """Reescribe mensual.csv con agua_m3 (y sin dias_produccion si con_dias es False)."""
    rng = np.random.default_rng(seed)
    with open(mensual, newline="") as f:
        filas = list(csv.DictReader(f))
    campos = ["pozo_id", "mes", "petroleo_m3", "agua_m3"] + (["dias_produccion"] if con_dias else [])
    with open(mensual, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for r in filas:
            r["agua_m3"] = repr(float(r["petroleo_m3"]) * (0.3 + 0.02 * float(rng.normal())))
            w.writerow(r)
    return pozos, mensual


def _corre(pozos, mensual, out, reps=REPS):
    extra = ["--reps", str(reps)] if reps else []
    assert local.main(["--wells", str(pozos), "--monthly", str(mensual), "--out", str(out)] + extra) == 0
    return json.loads((out / "resumen.json").read_text())


def test_privacidad_de_la_tarjeta(tmp_path):
    pozos, mensual = _con_agua(*sintetico(tmp_path, n_clusters=60))
    out = tmp_path / "out"
    _corre(pozos, mensual, out)
    js = (out / "tarjeta.json").read_text()
    md = (out / "tarjeta.md").read_text()
    t = json.loads(js)
    assert tuple(t) == tarjeta.CAMPOS_TARJETA
    with open(pozos, newline="") as f:
        filas = list(csv.DictReader(f))
    for texto in (js, md):
        for r in filas:
            assert not re.search(rf"(?<![\w.]){re.escape(r['pozo_id'])}(?![\w.])", texto), "pozo_id en la tarjeta"
            assert r["pad_id"] not in texto
            for coord in (r["lon"], r["lat"], f"{float(r['lon']):.3f}", f"{float(r['lat']):.3f}"):
                assert coord not in texto, "coordenada en la tarjeta"
        assert not re.search(r"\d{4}-\d{2}", texto)
        assert not re.search(r"\d{2}/\d{2}/\d{4}", texto)
        assert not re.search(r"-?\d{1,3}[.,]\d{3,}", texto), "numero con forma de coordenada"
    assert "pozo_id" not in md and "pad_id" not in md
    assert "no es una replicación independiente" in md


def test_supresion_de_cifras_de_menos_de_diez_pozos():
    br = {"k1": {"n_cercanos": 40, "n_controles": 60, "pads_hijo_cercanos": 20, "brecha": -0.2, "ic_bajo": -0.3,
                 "ic_alto": -0.1}}
    chico = {"n_tratados": 9, "att": 12.0, "ic_bajo": 1.0, "ic_alto": 20.0, "placebos_rotos": [], "con_cierre": True,
             "cierre": {"est": 0.0, "ic_bajo": 0.0, "ic_alto": 0.0}, "veredicto": "x"}
    t = tarjeta.armar_tarjeta({"brecha": br, "d2": chico})
    suprimida = f"menos de {tarjeta.MIN_POZOS_CIFRA} pozos"
    assert suprimida == "menos de 10 pozos"
    assert t["eventos"] == t["dw_pp"] == t["dw_ic"] == suprimida
    assert t["brecha_mes1"] == -20.0 and t["brecha_mes1_ic"] == [-30.0, -10.0]
    assert suprimida in tarjeta.tarjeta_md(t)
    br["k1"]["n_cercanos"] = 9
    t = tarjeta.armar_tarjeta({"brecha": br, "d2": dict(chico, n_tratados=10)})
    assert t["brecha_mes1"] == t["brecha_mes1_ic"] == suprimida
    assert t["eventos"] == 10 and t["dw_pp"] == 12.0 and t["dw_ic"] == [1.0, 20.0]


def test_sin_agua_la_tarjeta_lo_dice_y_main_la_escribe(tmp_path):
    br = {"k1": {"n_cercanos": 40, "n_controles": 60, "pads_hijo_cercanos": 20, "brecha": -0.2, "ic_bajo": -0.3,
                 "ic_alto": -0.1}}
    t = tarjeta.armar_tarjeta({"brecha": br, "d2": None})
    assert tuple(t) == tarjeta.CAMPOS_TARJETA
    assert t["dw_pp"] == t["veredicto_agua"] == tarjeta.SIN_AGUA == "sin dato de agua"
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    res = _corre(pozos, mensual, tmp_path / "out")
    assert "agua" not in res
    escrita = json.loads((tmp_path / "out" / "tarjeta.json").read_text())
    assert tuple(escrita) == tarjeta.CAMPOS_TARJETA and escrita["veredicto_agua"] == tarjeta.SIN_AGUA
    assert tarjeta.SIN_AGUA in (tmp_path / "out" / "tarjeta.md").read_text()


def test_dias_produccion_vacia_es_sin_cierre(tmp_path):
    pozos, mensual = _con_agua(*sintetico(tmp_path, n_clusters=60), con_dias=True)
    with open(mensual, newline="") as f:
        filas = list(csv.DictReader(f))
    with open(mensual, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        for r in filas:
            w.writerow(dict(r, dias_produccion=""))
    out = tmp_path / "out"
    res = _corre(pozos, mensual, out)
    assert res["agua"]["con_cierre"] is False and res["agua"]["cierre"] is None
    assert tarjeta.SIN_CIERRE in (out / "tarjeta.md").read_text()


def test_agua_sin_dias_produccion_da_sin_cierre(tmp_path):
    pozos, mensual = _con_agua(*sintetico(tmp_path, n_clusters=60), con_dias=False)
    out = tmp_path / "out"
    res = _corre(pozos, mensual, out)
    assert res["agua"]["con_cierre"] is False and res["agua"]["cierre"] is None
    t = json.loads((out / "tarjeta.json").read_text())
    assert any(tarjeta.SIN_CIERRE in n for n in t["notas"])
    assert tarjeta.SIN_CIERRE in (out / "tarjeta.md").read_text()


def test_agua_con_dias_produccion_corre_el_cierre(tmp_path):
    pozos, mensual = _con_agua(*sintetico(tmp_path, n_clusters=60))
    res = _corre(pozos, mensual, tmp_path / "out")
    assert res["agua"]["con_cierre"] is True and res["agua"]["cierre"] is not None
    assert (tmp_path / "out" / "tarjeta.json").exists()


@pytest.mark.slow
def test_validacion_d2_del_warehouse_publico_por_el_modo_local():
    """Exporta el warehouse publico a pozos.csv y mensual.csv (con agua_m3 y dias_produccion = dias_efectivos), corre el
    modo local y compara D2 con VALIDACION_D2_TRATADOS y VALIDACION_D2_PP (regla fijada antes de correr)."""
    import duckdb

    ruta = DATA / "warehouse.duckdb"
    if not ruta.exists():
        pytest.skip("sin data/warehouse.duckdb")
    pub = duckdb.connect(str(ruta), read_only=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pub.execute(f"""copy (
                select u.pozo_id, u.pad_id, u.lon, u.lat, u.operador, u.area,
                    f.primera as fecha_fractura, d.arena_tn, d.etapas, d.rama_horizontal_m as rama_m,
                    f.presion as presion_max_psi
                from int_pozo_ubicacion u
                left join (select pozo_id, min(fecha_inicio) as primera, max(presion_maxima_psi) as presion
                           from stg_fractura where fecha_inicio is not null group by pozo_id) f using (pozo_id)
                left join dim_fractura_pozo d using (pozo_id)
                order by u.pozo_id) to '{tmp / "pozos.csv"}' (header, delimiter ',')""")
            pub.execute(f"""copy (
                select p.pozo_id, strftime(p.mes, '%Y-%m-%d') as mes, p.petroleo_m3, p.agua_m3,
                    p.dias_efectivos as dias_produccion
                from fct_produccion p join int_pozo_ubicacion using (pozo_id)
                order by p.pozo_id, p.mes) to '{tmp / "mensual.csv"}' (header, delimiter ',')""")
            res = _corre(tmp / "pozos.csv", tmp / "mensual.csv", tmp / "out", reps=None)  # REPS y semilla de la regla
        publico = pub.execute("select valor, ic_bajo, ic_alto from mart_causal_veredicto where diseno = 'D2'").fetchone()
    finally:
        pub.close()
    a = res["agua"]
    print("VALIDACION_D2", a["n_tratados"], a["att"], a["ic_bajo"], a["ic_alto"], a["veredicto"])
    assert a["n_tratados"] == tarjeta.VALIDACION_D2_TRATADOS
    assert round(a["att"], 1) == tarjeta.VALIDACION_D2_PP
    assert abs(a["att"] - tarjeta.VALIDACION_D2_PP) <= tarjeta.TOLERANCIA_VALIDACION_PP
    for local_, pub_ in zip((a["att"], a["ic_bajo"], a["ic_alto"]), publico):
        assert abs(local_ - pub_) <= tarjeta.TOLERANCIA_VALIDACION_PP
