"""Golpes en el mismo mes con pads sinteticos: el costo fijo y el costo por hijo inyectados se recuperan y la regla responde."""
import calendar
import re

import duckdb
import numpy as np
import pytest

from pipeline import golpes_mismo_mes as gm
from pipeline import linaje
from pipeline.placebo import PAD

N_MES = 220
REPS = 60


def sintetico(fijo: float, por_hijo: float, n_pads: int = 160, seed: int = 7, padres_por_pad: int = 6,
              ruido: float = 0.03) -> dict:
    """Pads hijo de 1 a 8 pozos fracturados en un mismo mes; cada pad tiene sus padres cercanos (a 0,3 a 0,9 km de todos
    sus hijos) y sus controles (2 a 4,5 km). Cada padre recibe un solo pad, asi que todos los eventos quedan aislados.
    Un padre cercano pierde, en los meses 0 a 2, fijo + por_hijo * k dias de produccion de base."""
    rng = np.random.default_rng(seed)
    ops = np.array(["A", "B", "C", "D"])
    ph, pp, km = [], [], []
    hijo_mes, hijo_pad, n_padre, padre_pad = [], [], 0, []
    tamanos = rng.integers(1, 9, n_pads)
    for p in range(n_pads):
        mes = int(rng.integers(100, 150))
        hijos = list(range(len(hijo_mes), len(hijo_mes) + int(tamanos[p])))
        hijo_mes += [mes] * len(hijos)
        hijo_pad += [p] * len(hijos)
        for j in range(padres_por_pad + 20):
            cerca = j < padres_por_pad
            for h in hijos:
                ph.append(h)
                pp.append(n_padre)
                km.append(rng.uniform(0.3, 0.9) if cerca else rng.uniform(2.0, 4.5))
            padre_pad.append((p, cerca))
            n_padre += 1
    hijo_mes = np.array(hijo_mes, dtype=np.int64)
    tasa = np.full((n_padre, N_MES + 2 * PAD), np.nan)
    t = np.arange(N_MES)
    for i, (p, cerca) in enumerate(padre_pad):
        y = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, ruido, N_MES))
        if cerca:
            m0 = hijo_mes[hijo_pad.index(p)]
            base = 50 * np.exp(-0.01 * (m0 + np.arange(-6, -3))).mean()
            for j in range(3):  # la perdida se reparte en los meses 0 a 2 para que ningun mes baje de cero
                dias = calendar.monthrange(2000 + (m0 + j) // 12, (m0 + j) % 12 + 1)[1]
                y[m0 + j] -= base * (fijo + por_hijo * tamanos[p]) / 3 / dias
        tasa[i, PAD:PAD + N_MES] = y
    D = {"hijo_id": np.arange(len(hijo_mes)) + 1000, "hijo_mes": hijo_mes, "hijo_anio": 2000 + hijo_mes // 12,
         "hijo_pad": np.array(hijo_pad, dtype=np.int64), "primer": np.zeros(n_padre, dtype=np.int64),
         "area": np.array(["A"] * n_padre), "lat": np.full(n_padre, -38.5), "tasa": tasa,
         "par_hijo": np.array(ph), "par_padre": np.array(pp), "par_km": np.array(km),
         "par_rumbo": np.zeros(len(pp)), "n_mes": N_MES, "operador": ops[np.arange(n_padre) % 4]}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - 6
    return D


def _principal(D: dict) -> tuple[dict, np.ndarray]:
    e = gm.eventos(D)
    return e, np.flatnonzero(gm.muestras(e)["principal"])


def _prueba(t: dict) -> dict:
    return {(f[0], f[1]): f for f in t[gm.mart("_prueba")]}


def _con_hijo(D: dict, padre: int, mes: int, km: float) -> dict:
    """D con un hijo nuevo, de su propio pad, fracturado en `mes` a `km` del padre (un solo par)."""
    D = dict(D)
    D["hijo_id"] = np.append(D["hijo_id"], D["hijo_id"].max() + 1)
    D["hijo_mes"] = np.append(D["hijo_mes"], mes)
    D["hijo_anio"] = np.append(D["hijo_anio"], 2000 + mes // 12)
    D["hijo_pad"] = np.append(D["hijo_pad"], D["hijo_pad"].max() + 1)
    D["par_hijo"] = np.append(D["par_hijo"], len(D["hijo_mes"]) - 1)
    D["par_padre"] = np.append(D["par_padre"], padre)
    D["par_km"] = np.append(D["par_km"], km)
    D["par_rumbo"] = np.append(D["par_rumbo"], 0.0)
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= D["hijo_mes"][D["par_hijo"]] - 6
    return D


def _evento(e: dict, padre: int, mes: int) -> int:
    return int(np.flatnonzero((e["padre"] == padre) & (e["mes"] == mes))[0])


def test_ajuste_recupera_el_costo_fijo_y_el_costo_por_hijo():
    e, idx = _principal(sintetico(10, 2))
    a, b = gm.ajuste(e, idx, e["perdida"])
    assert abs(a - 10) < 1 and abs(b - 2) < 0.3
    grupos = gm.ajuste_grupos(e, idx, e["perdida"])
    g = gm._grupo_k(e["k"][idx])
    for n in range(4):  # grupos de k = 1 a 4: la perdida del grupo es fijo + por_hijo * k
        assert abs(grupos[n] - (10 + 2 * (n + 1))) < 1.5, (n, grupos[n])
    assert np.isfinite(grupos[4]) and abs(grupos[4] - (10 + 2 * e["k"][idx][g == 4].mean())) < 1.5


def test_eventos_cuenta_k_y_todos_los_eventos_del_sintetico_quedan_aislados():
    D = sintetico(10, 2)
    e, idx = _principal(D)
    cerca = np.flatnonzero((e["banda"] == 0) & e["ventana"])
    assert len(idx) == len(cerca) > 300
    tamano = np.bincount(D["hijo_pad"])
    pad_de = {int(p): int(D["hijo_pad"][h]) for p, h, km in zip(D["par_padre"], D["par_hijo"], D["par_km"]) if km < 1}
    assert all(e["k"][i] == tamano[pad_de[int(e["padre"][i])]] for i in idx)
    assert np.all(e["k12"][idx] == 0) and np.all(e["k"][e["banda"] == 2] == 0)


def test_un_hijo_cercano_a_los_tres_meses_saca_el_evento_de_la_muestra_principal():
    D = sintetico(10, 2)
    e0, idx0 = _principal(D)
    i = idx0[0]
    padre, mes = int(e0["padre"][i]), int(e0["mes"][i])
    e, idx = _principal(_con_hijo(D, padre, mes + 3, 1.5))
    j = _evento(e, padre, mes)
    assert e["despues"][j] == 1 and e["antes"][j] == 0 and not e["aislado"][j] and j not in set(idx.tolist())
    assert gm.muestras(e)["S2"][j] and e["k"][j] == e0["k"][i]  # sigue en S2, con la misma k
    e, _ = _principal(_con_hijo(D, padre, mes - 6, 1.9))
    assert e["antes"][_evento(e, padre, mes)] == 1
    e, _ = _principal(_con_hijo(D, padre, mes - 7, 1.9))  # fuera de los 6 meses: sigue aislado
    assert e["aislado"][_evento(e, padre, mes)]


def test_un_hijo_del_mismo_mes_entre_1_y_2_km_suma_a_k12_y_no_a_k():
    D = sintetico(10, 2)
    e0, idx0 = _principal(D)
    i = idx0[0]
    padre, mes = int(e0["padre"][i]), int(e0["mes"][i])
    e, _ = _principal(_con_hijo(D, padre, mes, 1.5))
    j = _evento(e, padre, mes)
    assert e["k12"][j] == 1 and e["k"][j] == e0["k"][i] and e["aislado"][j]


def test_un_mes_sin_dato_en_la_ventana_saca_el_evento():
    D = sintetico(10, 2)
    e0, idx0 = _principal(D)
    i = idx0[0]
    padre, mes = int(e0["padre"][i]), int(e0["mes"][i])
    D["tasa"] = D["tasa"].copy()
    D["tasa"][padre, mes + 4 + PAD] = np.nan
    e, idx = _principal(D)
    j = _evento(e, padre, mes)
    assert not e["ventana"][j] and j not in set(idx.tolist()) and len(idx) == len(idx0) - 1


def test_perdida_en_dias_de_base_y_volumen():
    e, idx = _principal(sintetico(10, 2, ruido=0.0))
    ctrl = (e["banda"] == 2) & e["ventana"]
    assert abs(np.median(e["perdida"][ctrl])) < 0.5
    esperado = 10 + 2 * e["k"][idx]
    assert np.max(np.abs(e["perdida"][idx] - esperado)) < 0.6
    assert np.allclose(e["vol"], e["perdida"] * e["base"])


def test_phi_y_rho():
    assert gm._phi(6, 6) == 0.5 and gm._rho(6, 6, 2) == 0.75
    assert gm._rho(0, 5, 4) == 1.0 and gm._rho(5, 0, 4) == 0.25 and gm._phi(5, 0) == 1.0
    assert np.isnan(gm._phi(1, -1)) and np.isnan(gm._rho(-2, 1, 3))


def test_veredicto_en_el_orden_de_la_regla():
    ks = {1: 30, 2: 30, 3: 30}
    ok = dict(n=400, pads=80, conteo_k=ks)
    assert gm.veredicto(299, 80, ks, 5, 0.9, 0.5, 1.0) == "sin muestra"
    assert gm.veredicto(400, 59, ks, 5, 0.9, 0.5, 1.0) == "sin muestra"
    assert gm.veredicto(400, 80, {1: 30, 2: 30, 3: 19}, 5, 0.9, 0.5, 1.0) == "sin muestra"
    assert gm.veredicto(**ok, ab_ic_bajo=0.0, phi=0.9, phi_ic_bajo=0.5, phi_ic_alto=1.0) == "sin perdida medible"
    assert gm.veredicto(**ok, ab_ic_bajo=float("nan"), phi=0.9, phi_ic_bajo=0.5, phi_ic_alto=1.0) == "sin perdida medible"
    assert gm.veredicto(**ok, ab_ic_bajo=1, phi=0.25, phi_ic_bajo=0.01, phi_ic_alto=1.0) == "agrupar ahorra"
    assert gm.veredicto(**ok, ab_ic_bajo=1, phi=0.1, phi_ic_bajo=-0.1, phi_ic_alto=0.249) == "agrupar no ahorra"
    assert gm.veredicto(**ok, ab_ic_bajo=1, phi=0.3, phi_ic_bajo=0.0, phi_ic_alto=0.6) == "no firme"
    assert gm.veredicto(**ok, ab_ic_bajo=1, phi=0.2, phi_ic_bajo=0.05, phi_ic_alto=0.4) == "no firme"
    assert set(gm.FRASE) == set(gm.VEREDICTOS)


def test_calcular_da_cada_veredicto_con_el_sintetico_y_es_determinista():
    casos = {(6, 6): "agrupar ahorra", (0, 5): "agrupar no ahorra", (0, 0): "sin perdida medible"}
    for (fijo, por), esperado in casos.items():
        t = gm.calcular(sintetico(fijo, por), reps=REPS)
        p = _prueba(t)
        assert p[("principal", "phi")][6] == esperado, (fijo, por, p[("principal", "phi")])
    t = gm.calcular(sintetico(0, 5, n_pads=20), reps=REPS)
    assert _prueba(t)[("principal", "phi")][6] == "sin muestra"
    t1, t2 = gm.calcular(sintetico(6, 6), reps=REPS), gm.calcular(sintetico(6, 6), reps=REPS)
    assert t1 == t2 and set(t1) == {"mart_golpes_mismo_mes", "mart_golpes_mismo_mes_prueba"}
    for filas in t1.values():
        assert not any(isinstance(x, float) and np.isnan(x) for f in filas for x in f)
    p = _prueba(t1)
    assert abs(p[("principal", "a_mas_b")][2] - p[("principal", "a")][2] - p[("principal", "b")][2]) < 1e-9
    assert abs(p[("diagnostico", "a_mas_b_contra_media_control")][2]
               - (p[("principal", "a_mas_b")][2] - p[("diagnostico", "perdida_media_control")][2])) < 1e-9
    assert len(t1["mart_golpes_mismo_mes"]) == len(gm.GRUPOS_K) and p[("conteo", "un_hijo_aislados")][2] > 0


def _pagina(tablas: dict, colorado: dict | None = None) -> str:
    con = duckdb.connect()
    gm.escribir(con, tablas)
    if colorado:
        gm.escribir(con, colorado, "colorado")
    return gm.pagina_golpes_mismo_mes(con)


def test_pagina_con_agrupar_ahorra_valua_el_ahorro_y_sin_colorado_no_trae_su_columna():
    txt = _pagina(gm.calcular(sintetico(6, 6), reps=REPS))
    assert "\u2014" not in txt and "\u2013" not in txt and not re.search(r"\bnan\b", txt)
    for seccion in ("## Lectura", "## El modelo", "## Pérdida por cantidad de hijos en el mes", "## Cuánto vale", "## Muestra",
                    "## Diagnóstico", "## Regla fijada antes de correr", "## Qué no prueba"):
        assert seccion in txt, seccion
    assert "**agrupar ahorra**" in txt and gm.FRASE["agrupar ahorra"] in txt and "| 60 | 10% |" in txt
    assert "## Colorado" not in txt and "| Colorado |" not in txt and "reagrupar hijos en un mismo mes tiene crédito" in txt
    assert "profit" not in txt.lower()


def test_pagina_sin_perdida_medible_no_valua_y_corre_los_dos_casos_y_trae_colorado():
    vm, co = gm.calcular(sintetico(0, 0), reps=REPS), gm.calcular(sintetico(6, 6, seed=11), reps=REPS)
    txt = _pagina(vm, co)
    assert "**sin pérdida medible**" in txt and "no hay ahorro que valuar" in txt and "| 60 | 10% |" not in txt
    assert "corre los dos casos" in txt and "Por qué no decide" in txt
    assert "## Colorado (confirmatoria)" in txt and "| Colorado | IC 95% |" in txt
    assert "Colorado (confirmatoria, misma regla): **agrupar ahorra**" in txt


def test_escribir_deja_los_nombres_que_lee_el_linaje_y_rechaza_otra_cuenca():
    texto = (linaje.PIPELINE_DIR / "golpes_mismo_mes.py").read_text(encoding="utf-8")
    assert set(linaje._ESCRIBIR.findall(texto)) == {"mart_golpes_mismo_mes", "mart_golpes_mismo_mes_prueba",
                                                     "mart_golpes_mismo_mes_colorado", "mart_golpes_mismo_mes_colorado_prueba"}
    with pytest.raises(ValueError, match="wyoming"):
        gm.escribir(duckdb.connect(), {}, "wyoming")
