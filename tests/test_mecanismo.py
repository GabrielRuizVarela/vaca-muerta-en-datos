"""Pruebas de pipeline.mecanismo con datos sinteticos: la regla fijada, el veredicto, los tipos de evento, el contraste y el IC."""
from pathlib import Path

import duckdb
import numpy as np

from pipeline import mecanismo as mc
from pipeline.costo import _escribir


# ------------------------------------------------------------------ regla y veredicto

def test_las_constantes_de_la_regla():
    assert mc.LATERAL_CERCANO_M == 1000.0
    assert mc.LATERAL_CONTROL_M == 2000.0
    assert mc.MIN_EVENTOS_POSICION == 80
    assert mc.MIN_GRUPO_BANDA == 5
    assert mc.K_PRINCIPAL == 1
    assert mc.K_PLACEBO == -1
    assert mc.TAM_BLOQUE_KM == 5.0
    assert mc.BANDAS_LATERAL_M == ((0.0, 300.0), (300.0, 600.0), (600.0, 1000.0))
    assert mc.MIN_CONTROL_EDAD == 5
    assert mc.BASE_MIN == 1.0
    assert mc.CORTES_EDAD == (12, 24, 48)


def test_veredicto_sostiene():
    # el contraste principal tiene el IC por debajo de cero y el placebo incluye cero
    assert mc.veredicto(100, 100, 3, -0.10, -0.20, 0.05) == "sostiene"


def test_veredicto_ubicacion():
    # el placebo tambien excluye cero
    assert mc.veredicto(100, 100, 3, -0.10, -0.20, -0.05) == "ubicación"


def test_veredicto_no_firme_por_ic_que_incluye_cero():
    assert mc.veredicto(100, 100, 3, 0.10, -0.20, 0.05) == "no firme"


def test_veredicto_no_firme_por_contraste_positivo():
    assert mc.veredicto(100, 100, 3, 0.10, -0.20, -0.05) == "no firme"


def test_veredicto_sin_muestra():
    assert mc.veredicto(79, 100, 0, -0.10, -0.20, 0.05) == "sin muestra"
    assert mc.veredicto(100, 79, 3, -0.10, -0.20, 0.05) == "sin muestra"


def test_veredicto_no_firme_sin_ic_de_placebo():
    assert mc.veredicto(100, 100, 3, -0.10, float("nan"), float("nan")) == "no firme"


# ------------------------------------------------------------------ tipos y bandas

def test_tipos_y_bandas():
    ev = {"m_min": np.array([300.0, 600.0, 1000.0, 2000.0, 100.0, 100.0]),
          "paralelas": np.array([True, True, True, True, False, True]),
          "solape": np.array([0.5, 0.0, 0.5, 0.5, 0.5, 0.1])}
    tipo, banda = mc.tipos(ev, mc.SOLAPE_COSTADO_PRINCIPAL)
    assert tipo.tolist() == [1, 2, 0, 3, 0, 0]
    assert banda.tolist() == [1, 2, -1, -1, -1, -1]


def test_tipos_con_el_umbral_de_sensibilidad():
    ev = {"m_min": np.array([100.0, 100.0]), "paralelas": np.array([True, True]),
          "solape": np.array([0.4, 0.6])}
    tipo, _banda = mc.tipos(ev, mc.SOLAPE_COSTADO_SENSIBILIDAD)
    assert tipo.tolist() == [0, 1]          # con 0,5 el de solape 0,4 es mixto


# ------------------------------------------------------------------ controles y contraste

def test_control_por_edad_necesita_cinco_controles():
    idx = np.array([1.0, 1.1, 0.9, 1.2])
    grupo = np.zeros(4, dtype=np.int64)
    tipo = np.full(4, 3)
    assert np.isnan(mc.control_por_edad(idx, grupo, tipo)).all()
    idx = np.concatenate([idx, [1.0]])
    grupo = np.zeros(5, dtype=np.int64)
    tipo = np.full(5, 3)
    c = mc.control_por_edad(idx, grupo, tipo)
    assert not np.isnan(c[0]) and abs(c[0] - 1.0) < 1e-12


def _caso(bandas: list[tuple[int, int, float, float]]) -> tuple[np.ndarray, ...]:
    """Sintetiza los eventos de unas bandas: (n_costado, n_punta, indice del costado, indice de la punta).

    Los controles del grupo 0 son seis con indice 1,0."""
    idx, grupo, tipo, banda = [], [], [], []
    for b, (nc, npt, ic, ip) in enumerate(bandas):
        idx += [ic] * nc + [ip] * npt
        grupo += [0] * (nc + npt)
        tipo += [1] * nc + [2] * npt
        banda += [b] * (nc + npt)
    idx += [1.0] * 6
    grupo += [0] * 6
    tipo += [3] * 6
    banda += [-1] * 6
    return np.array(idx, dtype=float), np.array(grupo, dtype=np.int64), np.array(tipo, dtype=np.int64), np.array(banda, dtype=np.int64)


def test_contraste_de_una_banda_con_datos():
    idx, grupo, tipo, banda = _caso([(6, 6, 0.5, 0.8), (6, 6, 0.5, 0.8), (6, 3, 0.5, 0.8)])
    c = mc.contraste(idx, grupo, tipo, banda)
    assert c["n_bandas"] == 2
    assert abs(c["delta"] + 0.3) < 1e-12                # el contraste es -0,3 en cada banda con dato
    assert c["n_costado"] == 18
    assert c["n_punta"] == 15
    assert c["n_control"] == 6
    tercera = c["bandas"][2]
    assert tercera["n_punta"] == 3 and tercera["peso"] == 0        # la banda con menos de 5 puntas no entra
    assert np.isnan(tercera["delta"])
    assert abs(tercera["gap_costado"] + 0.5) < 1e-12
    assert abs(tercera["gap_punta"] + 0.2) < 1e-12


def test_el_promedio_pesado_difiere_del_simple():
    idx, grupo, tipo, banda = _caso([(5, 5, 0.5, 0.8), (10, 20, 0.8, 0.9), (6, 3, 0.5, 0.8)])
    pesado = mc.contraste(idx, grupo, tipo, banda, ponderado=True)
    simple = mc.contraste(idx, grupo, tipo, banda, ponderado=False)
    assert abs(pesado["delta"] + 0.15) < 1e-12            # (-0,3 * 10 + -0,1 * 30) / 40
    assert abs(simple["delta"] + 0.2) < 1e-12             # (-0,3 + -0,1) / 2
    assert pesado["delta"] != simple["delta"]


# ------------------------------------------------------------------ intervalo

def _caso_ic(delta: float, n_bloques: int = 40) -> tuple[np.ndarray, ...]:
    """Bloques de tres eventos: un control, un costado y una punta, con el contraste constante."""
    idx, grupo, tipo, banda, clave = [], [], [], [], []
    for b in range(n_bloques):
        idx += [1.0, 1.0 + delta, 1.0]
        grupo += [0, 0, 0]
        tipo += [3, 1, 2]
        banda += [-1, 0, 0]
        clave += [b, b, b]
    return (np.array(idx, dtype=float), np.array(grupo, dtype=np.int64), np.array(tipo, dtype=np.int64),
            np.array(banda, dtype=np.int64), np.array(clave, dtype=np.int64))


def test_el_ic_es_determinista():
    idx, grupo, tipo, banda, clave = _caso_ic(-0.3)
    a = mc.ic(lambda ix, g, t, b: mc.contraste(ix, g, t, b)["delta"], idx, grupo, tipo, banda, clave, 50, 7)
    b = mc.ic(lambda ix, g, t, b: mc.contraste(ix, g, t, b)["delta"], idx, grupo, tipo, banda, clave, 50, 7)
    assert a == b


def test_el_ic_de_un_contraste_claro_excluye_cero():
    idx, grupo, tipo, banda, clave = _caso_ic(-0.3)
    bajo, alto = mc.ic(lambda ix, g, t, b: mc.contraste(ix, g, t, b)["delta"], idx, grupo, tipo, banda, clave, 50, 7)
    assert alto < 0.0


def test_el_ic_de_un_contraste_nulo_incluye_cero():
    idx, grupo, tipo, banda, clave = _caso_ic(0.0)
    bajo, alto = mc.ic(lambda ix, g, t, b: mc.contraste(ix, g, t, b)["delta"], idx, grupo, tipo, banda, clave, 50, 7)
    assert bajo <= 0.0 <= alto


# ------------------------------------------------------------------ eventos

def _D_micro() -> dict:
    """Diccionario minimo a mano: 3 padres (posiciones 0, 1 y 2) y 3 hijos (posiciones 0, 1 y 2).

    Padre 0 (posicion 0): primer mes 100, base 2,0 en los meses 117 a 119 y en los 167 a 169, caudal 1,0 en el mes 121
    y 1,4 en el 131. Padre 1 (posicion 1): primer mes 100, base 3,0 en los meses 117 a 119, caudal 2,4 en el mes 121 y
    base 0,5 (menor que 1) en los meses 167 a 169. Padre 2 (posicion 2): primer mes 125, tarde para el mes 130."""
    tasa = np.full((3, 220), np.nan)
    for col in (154, 155, 156, 157, 158, 159, 164, 165, 166, 167, 168, 169):
        tasa[0, col] = 2.0
    tasa[0, 161] = 1.0
    tasa[0, 171] = 1.4
    for col in (157, 158, 159):
        tasa[1, col] = 3.0
    tasa[1, 161] = 2.4
    for col in (167, 168, 169):
        tasa[1, col] = 0.5
    for col in (167, 168, 169):
        tasa[2, col] = 2.0
    return {
        "hijo_id": np.array([10, 20, 30], dtype=np.int64),
        "hijo_mes": np.array([120, 120, 130], dtype=np.int64),
        "hijo_anio": np.array([2010, 2010, 2010], dtype=np.int64),
        "hijo_pad": np.array([0, 0, 1], dtype=np.int64),
        "primer": np.array([100, 100, 125], dtype=np.int64),
        "tasa": tasa,
        "padre_id": np.array([100, 200, 300], dtype=np.int64),
        "bloque5": np.array([1, 1, 2], dtype=np.int64),
        "bloque2": np.array([2, 2, 3], dtype=np.int64),
        "rama_hijo": np.array([0, 1, 0, 1, 2, 2, 2], dtype=np.int64),
        "rama_padre": np.array([0, 0, 1, 1, 0, 1, 2], dtype=np.int64),
        "rama_m_min": np.array([100.0, 500.0, 300.0, 300.0, 100.0, 100.0, 100.0]),
        "rama_paralelas": np.array([True] * 7),
        "rama_posicion": np.array(["costado", "punta", "costado", "costado", "costado", "costado", "costado"], dtype=object),
        "rama_solape": np.array([0.5, 0.0, 0.4, 0.4, 0.5, 0.5, 0.5]),
        "rama_angulo": np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]),
    }


def test_eventos_elijo_el_hijo_mas_cercano_y_rompe_el_empate_con_el_id():
    ev = mc.eventos(_D_micro(), mc.BASE_PRINCIPAL, (1,))
    # padre 0 en el mes 120 (gana el hijo con m_min 100), padre 0 en el mes 130, padre 1 en el mes 120 (empate de
    # m_min: gana el id menor). El padre 2 queda afuera por la regla de edad y el padre 1 en el mes 130 por la base.
    assert ev["padre"].tolist() == [0, 0, 1]
    assert ev["hijo"].tolist() == [0, 2, 0]
    assert ev["m_min"].tolist() == [100.0, 100.0, 300.0]
    assert ev["anio"].tolist() == [2010, 2010, 2010]
    assert ev["grupo"].tolist() == [1, 2, 1]
    assert ev["pad"].tolist() == [0, 1, 0]
    assert ev["bloque5"].tolist() == [1, 2, 1]


def test_eventos_con_el_indice_sobre_la_base():
    ev = mc.eventos(_D_micro(), mc.BASE_PRINCIPAL, (1,))
    assert np.allclose(ev["idx"][1], [0.5, 0.7, 0.8])


def test_eventos_con_la_base_limpia_piden_las_dos_bases():
    # el padre 1 no tiene datos en los meses -6 a -4: con la base limpia queda afuera
    ev = mc.eventos(_D_micro(), mc.BASE_PLACEBO, (-1,))
    assert ev["padre"].tolist() == [0, 0]


# ------------------------------------------------------------------ fuente

def test_el_modulo_no_tiene_rayas_tipograficas():
    src = Path(mc.__file__).read_text(encoding="utf-8")
    assert chr(0x2013) not in src
    assert chr(0x2014) not in src


# ------------------------------------------------------------------ pagina

def _con_mecanismo(veredicto: str = "sostiene"):
    """Conexion en memoria con los cinco marts de la prueba y cifras inventadas.

    El placebo tiene un IC que incluye cero si el veredicto es "sostiene" y lo excluye si es "ubicacion"."""
    con = duckdb.connect()

    def fc(modelo, k, c, ib, ia):
        return (modelo, k, 100, 90, 500, 3, c, ib, ia, ib, ia, ib, ia, 10, 20)

    placebo = (-0.056, -0.14, 0.02) if veredicto == "sostiene" else (-0.056, -0.14, -0.05)
    _escribir(con, "mart_mecanismo_contraste", mc.COLS_CONTRASTE, [
        fc("principal", 1, -0.28, -0.36, -0.20),
        fc("placebo", -1, placebo[0], placebo[1], placebo[2]),
        fc("k1_base_limpia", 1, -0.27, -0.35, -0.19),
        fc("serie_base_limpia", -3, -0.02, -0.06, 0.03),
        fc("serie_base_limpia", -2, 0.00, -0.07, 0.04),
        fc("serie_base_limpia", -1, -0.06, -0.12, 0.02),
        fc("serie_base_limpia", 0, -0.29, -0.36, -0.21),
        fc("serie_base_limpia", 1, -0.27, -0.35, -0.18),
        fc("serie_base_limpia", 2, -0.12, -0.20, -0.03),
        fc("serie_base_limpia", 3, -0.08, -0.15, 0.00),
        fc("sin_pesar", 1, -0.32, -0.40, -0.24),
        fc("costado_05", 1, -0.28, -0.37, -0.19),
    ])
    _escribir(con, "mart_mecanismo_banda", mc.COLS_BANDA, [
        ("principal", "0 a 300 m", 1, 40, 30, -0.58, -0.05, -0.53, 70),
        ("principal", "300 a 600 m", 1, 35, 30, -0.37, -0.09, -0.28, 65),
        ("principal", "600 a 1.000 m", 1, 25, 30, -0.20, -0.06, -0.14, 55),
        ("placebo", "0 a 300 m", -1, 38, 29, -0.15, -0.01, -0.14, 67),
    ])
    _escribir(con, "mart_mecanismo_shmax", mc.COLS_SHMAX, [
        (1, 0.0, 67.5, "todos", 70, -0.19, -0.28, -0.12),
        (1, 0.0, 67.5, "costado", 40, -0.32, -0.42, -0.25),
        (1, 0.0, 67.5, "punta", 30, -0.07, -0.11, -0.01),
        (2, 67.5, 67.8, "todos", 70, -0.20, -0.26, -0.13),
        (2, 67.5, 67.8, "costado", 40, -0.40, -0.49, -0.23),
        (2, 67.5, 67.8, "punta", 30, -0.08, -0.17, -0.00),
        (3, 67.8, 90.0, "todos", 70, -0.22, -0.30, -0.16),
        (3, 67.8, 90.0, "costado", 40, -0.37, -0.45, -0.30),
        (3, 67.8, 90.0, "punta", 30, -0.06, -0.15, -0.00),
    ])
    _escribir(con, "mart_mecanismo_muestra", mc.COLS_MUESTRA, [
        (2016, 8, 10, 30), (2017, 9, 11, 35), (2018, 11, 13, 40), (2019, 13, 15, 45),
        (2020, 15, 17, 50), (2021, 17, 19, 55), (2022, 19, 21, 60), (2023, 21, 23, 65),
        (2024, 12, 12, 30), (2025, 8, 8, 20),
    ])
    _escribir(con, "mart_trayectoria_cobertura", [("nivel", "VARCHAR"), ("anio", "INTEGER"), ("total", "INTEGER"), ("medidos", "INTEGER")], [
        ("hijo", a, t, m) for a, t, m in [(2016, 116, 98), (2017, 140, 121), (2018, 176, 134), (2019, 183, 142), (2020, 87, 84),
                                           (2021, 261, 246), (2022, 296, 260), (2023, 334, 255), (2024, 355, 138), (2025, 457, 115)]])
    _escribir(con, "mart_mecanismo_veredicto", mc.COLS_VEREDICTO, [
        (veredicto, 100, 90, 3, -0.28, -0.36, -0.20, placebo[0], placebo[1], placebo[2], 282, 500, 10),
    ])
    return con


def test_la_pagina_tiene_el_veredicto_las_secciones_y_la_muestra():
    pag = mc.pagina_mecanismo(_con_mecanismo("sostiene"))
    assert "Veredicto contra la regla fijada: **sostiene**." in pag
    for seccion in ("# Mecanismo por la geometría de las ramas", "## Resumen",
                    "## Regla fijada antes de correr", "## Resultados", "## Límites"):
        assert seccion in pag
    assert "Muestra: las ramas medidas cubren de 76 a 97% de los hijos fracturados de 2016 a 2023 pero solo 39% de los de 2024 y 25% de los de 2025" in pag
    assert "De los 282 eventos cercanos del modelo principal, 85,8% corresponden a hijos fracturados de 2016 a 2023." in pag
    assert "Los cortes de los terciles son 67,5 y 67,8 grados" in pag
    assert "es descriptiva y no prueba ninguna dirección" in pag
    assert "La regla se fijó en el commit bddf1e0771 de la rama de esta prueba, antes de calcular ninguna cifra." in pag


def test_la_pagina_no_tiene_rayas_tipograficas_ni_4d():
    pag = mc.pagina_mecanismo(_con_mecanismo("sostiene"))
    assert chr(0x2013) not in pag and chr(0x2014) not in pag
    assert "4D" not in pag


def test_la_pagina_con_otro_veredicto():
    pag = mc.pagina_mecanismo(_con_mecanismo("ubicación"))
    assert "Veredicto contra la regla fijada: **ubicación**." in pag
    assert "El IC no incluye cero: la diferencia ya estaba antes de la fractura" in pag
    assert "## Límites" in pag


def test_la_cobertura_sale_del_mart_y_sin_mart_la_pagina_no_inventa_cifras():
    con = _con_mecanismo("sostiene")
    assert mc.cobertura_ramas(con) == (76, 97, 39, 25)
    con.execute("drop table mart_trayectoria_cobertura")
    assert mc.cobertura_ramas(con) is None
    pag = mc.pagina_mecanismo(con)
    assert "trayectorias.md" in pag and "de 80 a 94%" not in pag


def test_la_pagina_dice_que_la_banda_cercana_tiene_el_menor_peso_y_que_el_control_no_es_un_grupo_aparte():
    pag = mc.pagina_mecanismo(_con_mecanismo("sostiene"))
    assert "más pesa" not in pag
    assert ("allí el contraste del mes -1 ya es de -14,0 puntos (sin IC por banda). El veredicto decide con el promedio ponderado de "
            "las tres bandas; en esa banda el contraste del mes 1 es de -53,0 puntos y pesa 70 de 190 eventos en el promedio.") in pag
    assert "un cierre preventivo del padre que queda al costado" in pag
    assert "el control no es un grupo de padres aparte del grupo tratado" in pag
