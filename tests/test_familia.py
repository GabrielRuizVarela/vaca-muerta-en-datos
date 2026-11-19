"""La regla de la familia: las constantes de Wyoming son las de Colorado, la lectura lista todas las cuencas y no pesa ni promedia."""
from __future__ import annotations

import pytest

from pipeline import colorado, familia, fuentes_mundo, replicacion, wyoming


def test_wyoming_usa_exactamente_los_filtros_de_colorado():
    for nombre in ("BASE_MIN_M3_D", "BBL_A_M3", "EDAD_MIN_MESES", "FECHA_DUDOSA_DIAS", "FT_A_M", "HORIZONTAL_LATERAL_MIN_FT",
                   "HORIZONTAL_TVD_MIN_FT", "KM_CERCANO", "KM_CONTROL", "KM_MAX", "KM_POR_GRADO", "PAD_KM", "VENTANA_FRAC"):
        assert getattr(wyoming, nombre) == getattr(colorado, nombre), nombre
    assert wyoming.VENTANA_FRAC == ("2018-07-01", "2024-06-30")
    assert (wyoming.MIN_HIJOS_MEDIBLE, wyoming.MIN_CONTROLES_MEDIBLE) == (30, 30)


def test_la_regla_de_lectura_y_las_semillas_son_las_de_colorado():
    assert replicacion.KM_BLOQUE == 5.0 and replicacion.BASE_VEREDICTO == (-3, -1) and replicacion.BASE_PREVIA == (-6, -4)
    assert replicacion.K_VEREDICTO == 1 and replicacion.K_PREVIO == -1 and replicacion.DESPLAZAMIENTOS_PLACEBO == (-12, 12)


def test_la_familia_nombra_las_cuencas_y_la_original_no_es_una_replicacion():
    assert [i for i, _ in familia.FAMILIA] == ["colorado", "wyoming"]
    entran = {r["id"] for r in fuentes_mundo.cargar() if r["entra_al_estudio"]}
    assert entran == {"ar", "us_wy"}                      # la familia sale de la auditoria: la original (ar) mas Wyoming
    assert "ar" not in {i for i, _ in familia.FAMILIA}


def test_la_lectura_lista_todas_las_cuencas_y_cuenta_k_de_n():
    r = familia.lectura_familia({"colorado": (True, ""), "wyoming": (None, "menos de 30 hijos tras los filtros")})
    assert (r["k"], r["n"]) == (1, 2)
    assert r["frase"] == "Se replica en 1 de 2 cuencas: Colorado (se replica); Wyoming (no se pudo medir: menos de 30 hijos tras los filtros)."
    assert [c[0] for c in r["cuencas"]] == ["colorado", "wyoming"]
    assert familia.lectura_familia({"colorado": (False, ""), "wyoming": (False, "")})["k"] == 0


def test_no_se_arma_sin_el_resultado_de_una_cuenca_ni_con_una_de_mas():
    with pytest.raises(ValueError):
        familia.lectura_familia({"colorado": (True, "")})
    with pytest.raises(ValueError):
        familia.lectura_familia({"colorado": (True, ""), "wyoming": (True, ""), "otra": (True, "")})


def test_una_cuenca_que_no_se_pudo_medir_lleva_motivo():
    with pytest.raises(ValueError):
        familia.lectura_cuenca(None, "  ")


def test_la_lectura_no_tiene_estimacion_conjunta():
    r = familia.lectura_familia({"colorado": (True, ""), "wyoming": (True, "")})
    assert set(r) == {"k", "n", "frase", "cuencas"}
    assert not any(chr(c) in familia.__doc__ + r["frase"] for c in (0x2013, 0x2014))
