"""Validacion fijada de pipeline.cota_rr_contraste (sin warehouse y sin R): cambio de base, regla de coincidencia sobre la salida
sintetica guardada y lectura de una salida desactualizada."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from pipeline import cota_rr_condicional as crc
from pipeline import cota_rr_contraste as c

RAIZ = Path(__file__).resolve().parents[1]
ENT = RAIZ / c.ENTRADAS_SINT
SAL = RAIZ / c.SALIDA_SINT


def test_cambio_de_base_saltos_y_A():
    rng = np.random.default_rng(7)
    for _ in range(20):
        beta = rng.normal(size=5)
        Sigma = np.cov(rng.normal(size=(50, 5)), rowvar=False)
        bh, sh = c.base_honestdid(beta, Sigma)
        # saltos de HonestDiD: secuencia (previos, 0 de la referencia, posteriores)
        seq = np.array([bh[0], bh[1], bh[2], 0.0, bh[3], bh[4]])
        saltos_h = np.diff(seq)
        b3, b2, b1, b0, bp = beta
        assert np.allclose(saltos_h, [b3, b2 - b3, b1 - b2, b0 - b1, bp - b0])
        assert np.allclose(sh, sh.T)
        for m in crc.GRILLA_MBAR:
            for j, sg in crc.POLIEDROS:
                A = crc.matriz_rm(j, sg, m)
                assert np.allclose(c.a_honestdid(A) @ bh, A @ beta)
                assert np.allclose(c.a_honestdid(A) @ sh @ c.a_honestdid(A).T, A @ Sigma @ A.T)


def test_A_es_lineal_en_mbar_en_la_base_de_honestdid():
    for j, sg in crc.POLIEDROS:
        a0, a1 = (c.a_honestdid(crc.matriz_rm(j, sg, m)) for m in (0.0, 1.0))
        for m in (0.37, 1.63):
            assert np.allclose(c.a_honestdid(crc.matriz_rm(j, sg, m)), a0 + m * (a1 - a0), atol=1e-12)


def test_entradas_sinteticas_guardadas_son_las_de_la_regla():
    guardadas = json.loads(ENT.read_text())["estimandos"]
    nuevas = c.entradas_sinteticas()
    assert [e["nombre"] for e in guardadas] == [e["nombre"] for e in nuevas] == ["ATT(1)", "media"]
    for g, n in zip(guardadas, nuevas):
        assert np.allclose(g["beta"], n["beta"]) and np.allclose(g["Sigma"], crc.SIGMA_SINT)
        assert g["modulo"]["quiebre"] == n["modulo"]["quiebre"]
        for sg_, sn in zip(g["modulo"]["sets"], n["modulo"]["sets"]):
            assert sg_["bajo"] == pytest.approx(sn["bajo"], abs=1e-9) and sg_["alto"] == pytest.approx(sn["alto"], abs=1e-9)
            assert sg_["paso"] > 0


def test_coincide_sobre_la_salida_sintetica_guardada():
    r = c.evaluar(ENT, SAL)
    assert r["estado"] == "ok"
    for nombre, v in r["estimandos"].items():
        assert v["L1_coincide"], (nombre, v["falla"])
    assert r["coincide"] is True


def _l1_y_modulo(nombre="ATT(1)"):
    ent = {e["nombre"]: e for e in json.loads(ENT.read_text())["estimandos"]}[nombre]
    s = json.loads(SAL.read_text())["estimandos"][nombre]
    mod = {"sets": ent["modulo"]["sets"], "quiebre": ent["modulo"]["quiebre"], "sd": ent["sd"]}
    l1 = {"sets": s["L1"]["sets"], "paso_r": s["paso_r"], "quiebre_prueba": s["L1"]["quiebre_prueba"]}
    return mod, l1


def test_coincide_detecta_un_extremo_corrido():
    mod, l1 = _l1_y_modulo()
    malo = copy.deepcopy(l1)
    malo["sets"][3]["alto"] += 0.2 * mod["sd"]
    ok, falla = c.coincide(mod, malo)
    assert not ok and any("alto" in f for f in falla)


def test_coincide_detecta_abierto_vacio_y_quiebre():
    mod, l1 = _l1_y_modulo()
    ab = copy.deepcopy(l1)
    ab["sets"][0]["abierto"] = "alto"
    assert not c.coincide(mod, ab)[0]
    vac = copy.deepcopy(l1)
    vac["sets"][1].update(bajo=None, alto=None, abierto=None)
    assert not c.coincide(mod, vac)[0]
    q = copy.deepcopy(l1)
    q["quiebre_prueba"] = [{"mbar": 0.0, "acepta_cero": False}]
    assert not c.coincide(mod, q)[0]
    dos_vacios = copy.deepcopy(mod), copy.deepcopy(l1)
    for lado in dos_vacios:
        lado["sets"][1].update(bajo=None, alto=None, abierto=None)
    assert c.coincide(*dos_vacios)[0]


def test_reglas_del_quiebre():
    assert c._falla_quiebre(0.0, [{"mbar": 0.0, "acepta_cero": True}]) == []
    assert c._falla_quiebre(None, [{"mbar": 2.0, "acepta_cero": False}]) == []
    assert c._falla_quiebre(None, [{"mbar": 2.0, "acepta_cero": True}])
    q = 0.5
    ok = [{"mbar": 0.48, "acepta_cero": False}, {"mbar": 0.52, "acepta_cero": True}]
    assert c._falla_quiebre(q, ok) == []
    assert len(c._falla_quiebre(q, [dict(p, acepta_cero=not p["acepta_cero"]) for p in ok])) == 2
    assert c.mbars_quiebre(0.5) == [0.48, 0.52] and c.mbars_quiebre(1.99) == [1.97, 2.0] and c.mbars_quiebre(None) == [2.0]


def test_salida_con_el_sha_de_otras_entradas_esta_desactualizada(tmp_path):
    assert c.leer_salida(SAL, ENT)[0] == "ok"
    ent2 = tmp_path / "ent.json"
    ent2.write_text(ENT.read_text().replace('"ATT(1)"', '"ATT(2)"', 1))
    estado, salida = c.leer_salida(SAL, ent2)
    assert estado == "desactualizado" and salida is None
    assert c.evaluar(ent2, SAL) == {"estado": "desactualizado"}
    sal2 = tmp_path / "sal.json"
    d = json.loads(SAL.read_text())
    d["sha256_entradas"] = "0" * 64
    sal2.write_text(json.dumps(d))
    assert c.leer_salida(sal2, ENT)[0] == "desactualizado"
    assert c.leer_salida(tmp_path / "no_existe.json", ENT)[0] == "sin_salida"


def test_json_de_entradas_es_determinista(tmp_path):
    lista = c.entradas_sinteticas()
    a = c.escribir_entradas(lista, tmp_path / "a.json")
    b = c.escribir_entradas(copy.deepcopy(lista), tmp_path / "b.json")
    assert a == b == c.sha256_archivo(tmp_path / "a.json")


def test_anidamiento_cuenta_con_tolerancia():
    sets = [{"mbar": 0.0, "bajo": -1.0, "alto": 1.0, "paso": 0.01}, {"mbar": 0.25, "bajo": -0.5, "alto": 1.5, "paso": 0.01}]
    assert c.anidamiento(sets, 1.0) == [{"mbar": 0.25, "contiene_al_anterior": False}]
    sets[1]["bajo"] = -1.1
    assert c.anidamiento(sets, 1.0)[0]["contiene_al_anterior"] is True


def _sint():
    lista = json.loads(ENT.read_text())["estimandos"]
    salida = json.loads(SAL.read_text())
    return lista, salida, c.evaluar(ENT, SAL)


def test_filas_del_mart_sobre_la_salida_sintetica():
    lista, salida, ev = _sint()
    filas = c.filas_mart(lista, ev, salida)
    cols = [x[0] for x in c.COLS_CONTRASTE]
    reg = [dict(zip(cols, f)) for f in filas]
    assert all(len(f) == len(cols) for f in filas)
    n_m = len(c.GRILLA_MBAR)
    for nombre in ("ATT(1)", "media"):
        r = [x for x in reg if x["estimando"] == nombre]
        for lec in c.LECTURAS:
            assert len([x for x in r if x["lectura"] == lec and x["fila"] == "grilla"]) == n_m
            assert len([x for x in r if x["lectura"] == lec and x["fila"] == "quiebre"]) == 1
        ver = [x for x in r if x["fila"] == "veredicto"]
        assert len(ver) == 1 and ver[0]["lectura"] == "L1" and ver[0]["coincide"] is True
        assert ver[0]["dif_max_bajo_sd"] <= 0.05 + 0.1 and ver[0]["nota"] == "coincide"
    assert len(reg) == 2 * (len(c.LECTURAS) * n_m + len(c.LECTURAS) + 1)
    q3 = next(x for x in reg if x["estimando"] == "media" and x["lectura"] == "L3" and x["fila"] == "quiebre")
    assert q3["mbar_quiebre"] == pytest.approx(0.1181640625) and q3["veredicto_rr"] == c._veredicto_rr(0.1181640625)
    assert "filas de A" in q3["nota"]
    mod = next(x for x in reg if x["estimando"] == "ATT(1)" and x["lectura"] == "modulo" and x["fila"] == "quiebre")
    assert mod["mbar_quiebre"] == lista[0]["modulo"]["quiebre"]
    primero = next(x for x in reg if x["lectura"] == "L1p" and x["fila"] == "grilla" and x["mbar"] == 0.0)
    assert primero["contiene_al_anterior"] is None and primero["errores_paquete"] is not None


def test_filas_del_mart_sin_salida_al_dia_solo_llevan_el_modulo():
    lista, _, _ = _sint()
    filas = c.filas_mart(lista, {"estado": "desactualizado"}, None)
    reg = [dict(zip([x[0] for x in c.COLS_CONTRASTE], f)) for f in filas]
    assert {x["lectura"] for x in reg} == {"modulo", "L1"}
    assert [x["nota"] for x in reg if x["fila"] == "veredicto"] == ["desactualizado: correr scripts/contraste_honestdid.sh"] * 2


PAGINA_PRUEBA = "# Titulo\n\ntexto\n\n## Lo que no dice\n\nfinal\n"


def _secciones():
    lista, salida, ev = _sint()
    lista_e = [dict(e, diseno="E", estimando="ATT(1)", union_quiebre=0.32, n_tratados=10, sorteos=400) for e in lista[:1]]
    return (c.seccion_contraste(lista, ev, salida) + c.seccion_e_e2(lista_e, {"E": (0.3186, "resiste solo con Mbar menor que 1")},
                                                                      {"E": "sin muestra"}))


def test_insertar_secciones_es_idempotente_y_va_antes_de_lo_que_no_dice():
    sec = _secciones()
    una = c.insertar_secciones(PAGINA_PRUEBA, sec)
    dos = c.insertar_secciones(una, sec)
    assert una == dos
    assert una.count("## Contraste con HonestDiD") == 1 and una.count("## E y E2") == 1
    assert c._pos(una, "## E y E2") < c._pos(una, "## Lo que no dice") and una.startswith("# Titulo\n\ntexto\n\n## Contraste")
    assert una.endswith("## Lo que no dice\n\nfinal\n")
    assert c.quitar_secciones(una) == PAGINA_PRUEBA
    # un contenido distinto reemplaza al anterior en vez de sumarse
    otra = c.insertar_secciones(una, ["## Contraste con HonestDiD", "", "otro", "", "## E y E2", "", "otro", ""])
    assert otra.count("## Contraste con HonestDiD") == 1 and "otro" in otra and "coincide" not in otra
    with pytest.raises(ValueError):
        c.insertar_secciones("# sin cierre\n", sec)


def test_las_secciones_citan_la_regla_y_publican_las_lecturas():
    txt = "\n".join(_secciones())
    assert c.COMMIT_REGLA == "06f7720" and c.COMMIT_ACLARACIONES == "21e1a91"
    assert "06f7720" in txt and "21e1a91" in txt and "**Lectura L1 (misma A y mismo valor crítico que el módulo): coincide**" in txt
    for lec in c.LECTURAS_R:
        assert f"| {lec} |" in txt
    assert "Lo que no dice el contraste" in txt and "sin muestra" in txt and "veredicto_apilado" in txt
    viejo = "\n".join(c.seccion_contraste(_sint()[0], {"estado": "desactualizado"}, None))
    assert "Desactualizado: correr scripts/contraste_honestdid.sh" in viejo and "| L1 |" not in viejo
