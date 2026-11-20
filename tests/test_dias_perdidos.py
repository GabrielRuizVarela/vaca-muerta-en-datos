"""Dias perdidos con eventos sinteticos: los dias inyectados por operador se recuperan y las reglas de veredicto responden."""
import math
import re

import duckdb
import numpy as np
import pytest

from pipeline import dias_perdidos as dp
from pipeline.costo import _escribir
from pipeline.placebo import PAD
from test_placebo import N_MES, sintetico

REPS = 60
OPS = list("ABCDEF")
DIAS = {"A": 2, "B": 4, "C": 8, "D": 12, "E": 16, "F": 20}
DIEZ = {o: 10 for o in OPS}
CERO = {o: 0 for o in OPS}


def con_dias(dias_op: dict, seed: int = 5, cambia: bool = False, efecto_y: float = 0.0) -> dict:
    """sintetico() con dias, caudal por dia efectivo y operador. Los cercanos pierden dias_op[operador] dias en el mes 0."""
    D = sintetico(efecto=0.0, seed=seed)
    rng = np.random.default_rng(seed + 100)
    op = np.array([OPS[h % 6] for h in D["par_hijo"]])
    forma = D["tasa"].shape
    D["operador"], D["dmes"] = op, np.full(forma, np.nan)
    D["tef"], D["tasa_ef"] = np.full(forma, np.nan), np.full(forma, np.nan)
    sl, t = slice(PAD, PAD + N_MES), np.arange(N_MES)
    D["dmes"][:, sl] = 30.0
    for i in range(len(op)):
        h = D["par_hijo"][i]
        m0, o = D["hijo_mes"][h], op[i]
        if cambia and m0 > 125:
            o = OPS[5 - OPS.index(o)]
        te = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, 0.03, N_MES))
        tef = np.full(N_MES, 0.9)
        if D["par_km"][i] < 1:
            perdido = dias_op[o] + rng.normal(0, 1)
            tef[m0] = (27 - perdido) / 30
            te[m0 + 4:m0 + 7] *= math.exp(efecto_y * perdido / 10)
        D["tef"][i, sl], D["tasa_ef"][i, sl], D["tasa"][i, sl] = tef, te, tef * te
    return D


def test_eventos_recupera_los_dias_inyectados():
    e = dp.eventos(con_dias(DIEZ))
    assert abs(e["exceso"][e["banda"] == 0].mean() - 10) < 1.0
    assert abs(e["exceso"][e["banda"] == 2].mean()) < 0.5
    fila = {f[0]: f for f in dp.tabla_bandas(e, reps=REPS)}["cercano"]
    assert fila[6] <= 10 <= fila[7]
    assert dp.veredicto_umbral(fila[5], fila[6], fila[7]) == "sostiene"
    cero = {f[0]: f for f in dp.tabla_bandas(dp.eventos(con_dias(CERO)), reps=REPS)}["cercano"]
    assert dp.veredicto_umbral(cero[5], cero[6], cero[7]) == "no se sostiene"


def test_un_nan_en_la_ventana_excluye_el_evento_y_no_cuenta_como_mes_cerrado():
    D = con_dias(DIEZ)
    e0 = dp.eventos(D)
    j = int(np.flatnonzero(e0["banda"] == 0)[0])
    D["tef"][e0["padre"][j], e0["mes"][j] + 1 + PAD] = np.nan
    e1 = dp.eventos(D)
    assert e1["excluidos"][0] == e0["excluidos"][0] + 1
    assert int((e1["banda"] == 0).sum()) == int((e0["banda"] == 0).sum()) - 1
    assert e0["padre"][j] not in e1["padre"][e1["banda"] == 0]


def test_volumen_de_los_dias_es_caudal_por_dias_por_indice():
    e = dp.eventos(con_dias(DIEZ))
    cerca = e["banda"] == 0
    esperado = 10 * e["caudal"][cerca].mean() * e["indice_control"][1]
    assert abs(e["vol"][cerca].mean() / esperado - 1) < 0.15


def test_tabla_operador_ordena_y_recupera_cada_brecha():
    filas = dp.tabla_operador(dp.eventos(con_dias(DIAS)), reps=REPS)
    assert [f[0] for f in filas] == list("FEDCBA")
    for f in filas:
        assert abs(f[5] - DIAS[f[0]]) < 1.5
        assert f[6] <= f[5] <= f[7]


def test_persistencia_separa_los_grupos_y_sostiene():
    p = dp.persistencia(dp.eventos(con_dias(DIAS)), reps=REPS)
    assert p["veredicto"] == "sostiene"
    assert {f[0]: f[1] for f in p["filas"]} == {"A": "bajo", "B": "bajo", "C": "bajo", "D": "alto", "E": "alto", "F": "alto"}
    assert abs(p["valor"] - 11.33) < 2
    assert p["spearman"] > 0.9


def test_persistencia_con_el_orden_invertido_no_se_sostiene():
    p = dp.persistencia(dp.eventos(con_dias(DIAS, cambia=True)), reps=REPS)
    assert p["valor"] < 0
    assert p["veredicto"] == "no se sostiene"


def test_persistencia_con_pocos_operadores_no_aplica():
    p = dp.persistencia(dp.eventos(con_dias(DIAS)), reps=REPS, min_operadores=7)
    assert p["veredicto"] == "no aplicable"
    assert math.isnan(p["valor"]) and p["descartadas"] == 0


def test_pendiente_recupera_el_signo_y_el_valor():
    mejor = dp.pendiente(dp.eventos(con_dias(DIAS, efecto_y=0.05)), reps=REPS)
    assert abs(mejor["pendiente"] - 0.05) < 0.02
    assert mejor["veredicto"] == "mas dias, mejor caudal posterior"
    assert dp.pendiente(dp.eventos(con_dias(DIAS, efecto_y=-0.05)), reps=REPS)["veredicto"] == "mas dias, peor caudal posterior"
    nada = dp.pendiente(dp.eventos(con_dias(DIAS, efecto_y=0.0)), reps=REPS)
    assert nada["ic_bajo"] < 0 < nada["ic_alto"] and nada["veredicto"] == "no se ve relacion"


def _recorte(e: dict, n: int) -> dict:
    return {k: (v[:n] if isinstance(v, np.ndarray) and v.shape[:1] == e["banda"].shape else v) for k, v in e.items()}


def test_pendiente_sin_muestra_no_da_veredicto():
    sin = dp.pendiente(_recorte(dp.eventos(con_dias(DIAS)), 12), reps=REPS)
    assert sin["veredicto"] == "no aplicable" and math.isnan(sin["pendiente"])


def test_tamano_de_ensayo():
    assert dp.tamano_ensayo(0.5) == [(0.05, 1568), (0.10, 392), (0.20, 98)]
    assert dp.tamano_ensayo(math.nan) == []


def test_veredicto_umbral_los_cuatro_resultados():
    assert dp.veredicto_umbral(8.0, 3.0, 12.0) == "sostiene"
    assert dp.veredicto_umbral(1.0, -1.0, 3.0) == "no se sostiene"
    assert dp.veredicto_umbral(8.0, -1.0, 12.0) == "no firme"
    assert dp.veredicto_umbral(math.nan, 1.0, 2.0) == "no aplicable"


def test_tabla_estado_cuenta_los_meses_cerrados_por_estado():
    D = con_dias(DIEZ)
    e = dp.eventos(D)
    D["estados"] = ["Extraccion", "Parado"]
    D["estado_cod"] = np.full(D["tasa"].shape, -1, dtype=np.int16)
    D["estado_cod"][:, PAD:PAD + N_MES] = 0
    cerca, ctrl = np.flatnonzero(e["banda"] == 0)[:10], np.flatnonzero(e["banda"] == 2)[:5]
    for orden, j in enumerate(list(cerca) + list(ctrl)):
        col = e["mes"][j] + PAD
        D["tef"][e["padre"][j], col] = 0.0
        D["estado_cod"][e["padre"][j], col] = 1 if (j in ctrl or orden < 6) else 0
    filas, cierre = dp.tabla_estado(D, e)
    assert filas == [("cercano", "Parado", 6, 0.6), ("cercano", "Extraccion", 4, 0.4), ("control", "Parado", 5, 1.0)]
    assert math.isclose(cierre["cercano"], 10 / (e["banda"] == 0).sum())
    assert dp.tabla_estado({"tef": D["tef"]}, e) == ([], {})


def test_calcular_es_determinista_y_sin_nan():
    D = con_dias(DIAS, efecto_y=0.05)
    t1, t2 = dp.calcular(D, reps=REPS), dp.calcular(D, reps=REPS)
    assert t1 == t2
    assert set(t1) == {"mart_dias_perdidos", "mart_dias_perdidos_operador", "mart_dias_perdidos_mitades",
                       "mart_dias_perdidos_estado", "mart_dias_perdidos_prueba"}
    for filas in t1.values():
        assert not any(isinstance(x, float) and math.isnan(x) for f in filas for x in f)
    prueba = {(f[0], f[1]): f for f in t1["mart_dias_perdidos_prueba"]}
    assert prueba[("A", "brecha_dias")][6] == "sostiene" and ("E", "n_por_rama_5") in prueba
    assert ("F", "parte_con_mes_cerrado_cercano") not in prueba


COLS = {"mart_dias_perdidos": dp.COLS_BANDA, "mart_dias_perdidos_operador": dp.COLS_OPERADOR, "mart_dias_perdidos_mitades": dp.COLS_MITADES,
        "mart_dias_perdidos_estado": dp.COLS_ESTADO, "mart_dias_perdidos_prueba": dp.COLS_PRUEBA}


def pagina(D: dict) -> str:
    con = duckdb.connect()
    for tabla, filas in dp.calcular(D, reps=REPS).items():
        _escribir(con, tabla, COLS[tabla], filas)
    return dp.pagina_dias_perdidos(con)


def test_pagina_sin_rayas_con_las_secciones_y_el_veredicto():
    txt = pagina(con_dias(DIAS))
    assert "\u2014" not in txt and "\u2013" not in txt
    for seccion in ("## Lectura", "## Cuántos días, por distancia al hijo", "## Por operador del padre", "## Prueba B", "## Prueba C",
                    "## Cuánto vale", "## Tamaño de un ensayo", "## Regla fijada antes de correr", "## Qué no prueba"):
        assert seccion in txt, seccion
    assert "veredicto: sostiene" in txt and dp.FRASE_B["sostiene"] in txt
    assert "## Estado declarado" not in txt  # el sintetico no trae estado
    assert "y falta confirmarla en Colorado." in txt and "## Colorado" not in txt  # sin marts de Colorado
    assert all(f"| {o} | " in txt for o in DIAS)
    assert "| 60 | 10% |" in txt and not re.search(r"\bnan\b", txt)


def test_pagina_con_operadores_chicos_dice_que_no_se_puede_decidir():
    D = con_dias(DIAS)
    D["operador"] = np.array([f"op{h:02d}" for h in D["par_hijo"]])  # 70 operadores de 12 cercanos: ninguno llega al minimo
    txt = pagina(D)
    assert "veredicto: no aplicable" in txt and dp.FRASE_B["no aplicable"] in txt
    assert "n/d días" in txt and "| op00 |" not in txt


def test_pagina_sin_estimacion_de_c_no_afirma_un_nulo(monkeypatch):
    real = dp.pendiente
    monkeypatch.setattr(dp, "pendiente", lambda e, *a, **k: real(_recorte(e, 12), *a, **k))
    txt = pagina(con_dias(DIAS))
    seccion_c = txt.split("## Prueba C")[1].split("## Cuánto vale")[0]
    assert "Prueba C (regla informada): no aplicable." in txt and "no se ve relación" not in txt
    assert "n/d" not in seccion_c and "## Tamaño de un ensayo" not in txt


def test_eventos_marca_la_edad_desconocida_solo_con_el_padre_censurado_y_joven():
    D = con_dias(DIEZ)
    assert not dp.eventos(D)["edad_desconocida"].any()
    D["primer"] = np.full_like(D["primer"], 80)                  # edades de unos 20 a 70 meses: a los dos lados de 48
    D["censurado"] = np.arange(D["tasa"].shape[0]) % 2 == 0
    e = dp.eventos(D)
    joven = e["edad"] < dp.EDADES[-1][0]
    censurado = D["censurado"][e["padre"]]
    assert (censurado & joven).any() and (censurado & ~joven).any() and (~censurado & joven).any()
    assert np.array_equal(e["edad_desconocida"], censurado & joven)


def test_pendiente_pone_la_edad_desconocida_en_un_grupo_propio(monkeypatch):
    e = dp.eventos(con_dias(DIAS))
    s = (e["banda"] == 0) & np.isfinite(e["y"]) & (e["caudal"] > 0)
    e["edad_desconocida"] = np.zeros(len(e["banda"]), dtype=bool)
    e["edad_desconocida"][np.flatnonzero(s)[::3]] = True
    vistos, real = [], dp._dummies
    monkeypatch.setattr(dp, "_dummies", lambda v: vistos.append(np.asarray(v).copy()) or real(v))
    dp.pendiente(e, reps=5)
    edad, marca = vistos[1], e["edad_desconocida"][s]   # operador, edad, anio
    assert (edad[marca] == len(dp.EDADES)).all() and (edad[~marca] < len(dp.EDADES)).all()


def test_cargar_cuenca_lee_un_warehouse_de_solo_lectura(tmp_path):
    from test_replicacion import _warehouse
    con = _warehouse()
    con.execute("alter table fct_produccion add column agua_m3 double default 0")
    con.execute("alter table fct_produccion add column estado varchar")
    con.execute("alter table dim_pozo add column primer_petroleo_censurado boolean")
    con.execute("update dim_pozo set primer_petroleo_censurado = pozo_id between 200 and 202")
    ruta = tmp_path / "co.duckdb"
    con.execute(f"attach '{ruta}' as f")
    con.execute("copy from database memory to f")
    con.close()
    ro = duckdb.connect(str(ruta), read_only=True)
    D = dp.cargar_cuenca(ro)
    ids = [r[0] for r in ro.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()]
    assert "estados" not in D and "estado_cod" not in D            # F solo en Vaca Muerta
    assert list(D["censurado"]) == [200 <= i <= 202 for i in ids]
    assert D["dmes"].shape == D["tasa"].shape and np.isfinite(D["dmes"]).any()
    e = dp.eventos(D)
    assert e["edad_desconocida"].any() and not e["edad_desconocida"].all()


def pagina_con_colorado(D_co: dict) -> tuple[str, set]:
    """Pagina de Vaca Muerta (DIAS: B sostiene) con los marts de Colorado escritos por dp.escribir."""
    con = duckdb.connect()
    for tabla, filas in dp.calcular(con_dias(DIAS), reps=REPS).items():
        _escribir(con, tabla, COLS[tabla], filas)
    dp.escribir(con, dp.calcular(D_co, reps=REPS), "colorado")
    tablas = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    return dp.pagina_dias_perdidos(con), tablas


def test_colorado_con_b_sostiene_saca_la_salvedad():
    txt, tablas = pagina_con_colorado(con_dias(DIAS, seed=7))
    assert {dp.mart(s, "colorado") for s in ("", "_operador", "_mitades", "_prueba")} <= tablas
    assert dp.mart("_estado", "colorado") not in tablas                # sin estado declarado fuera de Vaca Muerta
    assert "## Colorado: la prueba confirmatoria" in txt and "En Colorado la brecha es de " in txt
    assert "- Prueba B: " in txt and "También se sostiene en Colorado" in txt
    assert dp.SALVEDAD_B not in txt and "falta confirmarla" not in txt
    assert txt.index("## Colorado") < txt.index("## Regla fijada antes de correr")
    assert "\u2014" not in txt and not re.search(r"\bnan\b", txt)


def test_colorado_sin_b_conserva_la_salvedad():
    txt, _ = pagina_con_colorado(con_dias(DIEZ, seed=7))            # todos los operadores pierden lo mismo: B no sostiene
    v_co = re.search(r"no se confirmó \(veredicto: ([^)]+)\)", txt)
    assert v_co and v_co.group(1) != "sostiene"
    assert "- Prueba B (regla informada): " in txt and dp.SALVEDAD_B in txt
    assert f"Con la prueba B {v_co.group(1)} en Colorado, estas diferencias no se separan del ruido" in txt


def test_otra_cuenca_sin_adaptacion_escrita_no_se_escribe():
    with pytest.raises(ValueError, match="wyoming"):
        dp.escribir(duckdb.connect(), {}, "wyoming")
