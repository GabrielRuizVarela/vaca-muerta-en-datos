"""Barriles diferidos como rango: sin duplicar, descontando la brecha previa, por evento y por operadora, con filas sinteticas."""
import duckdb
import pytest

from pipeline import diferido as df
from pipeline.costo import _escribir

BASE, DIAS, GRUPO = 10.0, 30.0, "12-23"
BBL_MES = (BASE - 6.0) * DIAS * df.BBL_M3          # un mes de un cercano que rinde 6 m3/d contra un control en 10


def evento(padre, mes, m3_d=6.0, banda="cercano", operador="YPF", pad="p1", hasta=df.H_EVENTO):
    return [df.Fila(padre, mes, k, banda, GRUPO, operador, pad, BASE, m3_d, DIAS) for k in range(hasta + 1)]


def controles():
    return [f for i in range(5) for f in evento(f"c{i}", 90 + i, m3_d=BASE, banda="control", operador="Vista", pad=f"c{i}")]


def sintetico():
    """Un padre con dos hijos en meses seguidos (A), otro con un solo hijo (B) y cinco controles con indice 1."""
    return (evento("A", 100, pad="p1") + evento("A", 101, pad="p2") + evento("B", 100, operador="Vista", pad="p3") + controles())


def test_indice_de_control_es_la_mediana_por_grupo_y_mes():
    ctrl = df.indice_control(sintetico())
    assert ctrl[(GRUPO, 0)] == pytest.approx(1.0) and ctrl[(GRUPO, df.H_EVENTO)] == pytest.approx(1.0)
    assert len(ctrl) == df.H_EVENTO + 1


def test_padre_con_dos_hijos_seguidos_cuenta_cada_mes_una_vez():
    ctrl = df.indice_control(sintetico())
    ts = [t for t in df.terminos(sintetico(), ctrl, df.H_TOTAL) if t.fila.padre == "A"]
    assert len(ts) == 14 and sum(t.bbl for t in ts) == pytest.approx(14 * BBL_MES)
    sd = df.deduplicar(ts)
    assert len(sd) == 8                                         # meses de calendario 100 a 107
    assert sum(t.bbl for t in sd) < sum(t.bbl for t in ts)
    assert sum(t.bbl for t in sd) == pytest.approx(8 * BBL_MES)  # el valor contado una sola vez
    por_mes = {t.fila.mes + t.fila.k: t.fila.mes for t in sd}
    assert por_mes[100] == 100 and all(por_mes[m] == 101 for m in range(101, 108))   # el evento anterior mas cercano en el tiempo


def test_rango_ordena_original_sin_duplicar_y_neto():
    filas = sintetico()
    ts = df.terminos(filas, df.indice_control(filas), df.H_TOTAL)
    original, sd, neto = df.tabla_rango(ts, -0.05)
    assert original[2] == pytest.approx(21 * BBL_MES) and sd[2] == pytest.approx(15 * BBL_MES)
    assert neto[2] <= sd[2] <= original[2]
    assert neto[2] == pytest.approx(15 * (BBL_MES - 0.05 * BASE * DIAS * df.BBL_M3))
    assert (original[3], sd[3], neto[3]) == (3, 3, 3) and original[4] == 21 and sd[4] == 15
    assert neto[5] == pytest.approx(neto[2] / 3) and neto[6] == -0.05 and original[6] is None


def test_descuento_no_vuelve_negativo_un_mes_con_diferido_positivo_ni_toca_los_negativos():
    f = df.Fila("A", 100, 0, "cercano", GRUPO, "YPF", "p1", BASE, 9.9, DIAS)
    chico = df.Termino(f, 0.1 * DIAS * df.BBL_M3)
    assert df.descontar(chico, -0.2) == 0.0                     # la resta sola no lo pasa a negativo
    neg = df.Termino(f, -50.0)
    assert df.descontar(neg, -0.2) == -50.0
    assert df.descontar(df.Termino(f, BBL_MES), 0.1) == BBL_MES  # una brecha previa a favor no suma


def test_sin_duplicar_mayor_que_el_original_falla():
    # el mes repetido tiene diferido negativo en el evento anterior: descartarlo sube el total, y el modulo se niega a publicarlo
    filas = [df.Fila("A", 100, 0, "cercano", GRUPO, "YPF", "p1", BASE, 6.0, DIAS),
             df.Fila("A", 100, 1, "cercano", GRUPO, "YPF", "p1", BASE, 14.0, DIAS),
             df.Fila("A", 101, 0, "cercano", GRUPO, "YPF", "p2", BASE, 6.0, DIAS)]
    ts = df.terminos(filas, {(GRUPO, k): 1.0 for k in range(df.H_EVENTO + 1)}, df.H_TOTAL)
    assert sorted((t.fila.mes, t.fila.k) for t in df.deduplicar(ts)) == [(100, 0), (101, 0)]   # se queda el del 101
    with pytest.raises(ValueError, match="sin duplicar"):
        df.tabla_rango(ts, -0.04)


def test_acumulado_por_evento_solo_con_la_ventana_completa():
    filas = sintetico()
    ts = df.terminos(filas, df.indice_control(filas), df.H_EVENTO)
    evs = df.por_evento(ts, ultimo=124)
    assert len(evs) == 2 and all(e[2] == pytest.approx((df.H_EVENTO + 1) * BBL_MES) for e in evs)   # A en 101 queda fuera
    assert len(df.por_evento(ts, ultimo=200)) == 3
    assert {e[0] for e in evs} == {"YPF", "Vista"}


def test_operadora_con_pocos_eventos_va_en_otras_y_la_semilla_fija_el_intervalo():
    ev = [("YPF", f"p{i % 8}", float(i)) for i in range(40)] + [("Vista", f"q{i}", float(-i)) for i in range(6)]
    a, b = df.tabla_operador(ev, reps=80, minimo=10), df.tabla_operador(ev, reps=80, minimo=10)
    assert a == b
    assert [f[0] for f in a] == ["TODAS", "YPF", "OTRAS"] and [f[2] for f in a] == [46, 40, 6]
    ypf = a[1]
    assert ypf[8] <= ypf[5] <= ypf[9] and ypf[10] <= ypf[7] <= ypf[11]   # la mediana y la media caen en su intervalo
    assert ypf[3] == 8 and ypf[12] == pytest.approx(39 / 40)


def test_dos_corridas_dan_marts_identicos():
    filas = sintetico()
    a = df.calcular(filas, ultimo=200, g=-0.04, reps=60)
    b = df.calcular(filas, ultimo=200, g=-0.04, reps=60)
    assert a == b and a[0] and a[1]


def test_pagina_sin_rayas_ni_lenguaje_de_perdida(tmp_path):
    rango, operador = df.calcular(sintetico(), ultimo=200, g=-0.04, reps=60)
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    _escribir(con, "mart_diferido_rango", df.COLS_RANGO, rango)
    _escribir(con, "mart_diferido_operador", df.COLS_OPERADOR, operador)
    pagina = df.pagina_diferido(con)
    con.close()
    assert chr(0x2014) not in pagina and chr(0x2013) not in pagina
    assert "pérdida" not in pagina.lower() and "$" not in pagina and "USD" not in pagina
    assert "el reparto por operadora no es una comparación de desempeño" in pagina.lower()
    assert "diferido contra el control de la misma edad" in pagina
