"""Auditoria de fuentes del mundo: el archivo cumple el esquema, la regla de elegibilidad y la pagina sale de el."""
import copy
import json

import pytest

from pipeline import fuentes_mundo as fm


def test_registros_cumplen_el_esquema():
    regs = fm.cargar()
    assert len(regs) >= 20
    for r in regs:
        assert r["fecha_verificada"] == "2026-11-19"
        assert r["pedidos_hechos"], r["id"]
        assert r["permiten_derivadas"] in {"si", "sin_restriccion", "no_claro", "no"}, r["id"]


def test_una_fuente_entra_solo_con_las_cuatro_condiciones():
    for r in fm.cargar():
        if r["entra_al_estudio"]:
            assert r["nivel"] == "por_pozo_con_fractura", r["id"]
            assert r["acceso"] in {"descarga_directa", "api_documentada"}, r["id"]
            assert r["permiten_derivadas"] in {"si", "sin_restriccion"}, r["id"]
            assert r["campos"]["petroleo_mensual_por_pozo"] and r["campos"]["fecha_fractura_o_terminacion"], r["id"]


def test_sin_login_ni_pago_afuera():
    for r in fm.cargar():
        if r["acceso"] in {"login", "pago"} or r["permiten_derivadas"] in {"no", "no_claro"}:
            assert not r["entra_al_estudio"], r["id"]


def test_la_pagina_sale_del_archivo(tmp_path):
    out = tmp_path / "p.md"
    assert fm.main(salida=out) == (fm.PAGINA).read_text(encoding="utf-8") == out.read_text(encoding="utf-8")
    texto = out.read_text(encoding="utf-8")
    assert chr(0x2013) not in texto and chr(0x2014) not in texto


def test_esquema_rechaza_entrar_sin_ser_por_pozo(tmp_path):
    regs = copy.deepcopy(fm.cargar())
    regs[-1]["entra_al_estudio"], regs[-1]["nivel"] = True, "por_lease_o_campo"
    p = tmp_path / "f.json"
    p.write_text(json.dumps(regs), encoding="utf-8")
    with pytest.raises(SystemExit):
        fm.cargar(p)


def test_la_pagina_no_lleva_none_de_python():
    assert "None" not in fm.pagina(fm.cargar())
