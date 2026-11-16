"""Regla de parada del eje: junta las cuatro patas desde los marts; una sola que dispare alcanza; las que faltan no cuentan."""

import duckdb

from pipeline import eje_parada as ep


def _con(potencia=None, previa=None, bloques=None, expo=None):
    con = duckdb.connect()
    if potencia is not None:
        con.execute("create table mart_potencia_resumen(escenario varchar, m80 double, m80_texto varchar, veredicto varchar, "
                    "n_requerido_analitico double, anios_hasta_m80 double)")
        con.execute("insert into mart_potencia_resumen values ('principal', ?, ?, ?, 3000, 5)", [potencia[0], potencia[1], potencia[2]])
        con.execute("create table mart_potencia_eje(escenario varchar, multiplo double, potencia double)")
        con.execute("insert into mart_potencia_eje values ('principal', 2.0, 0.8)")
    if previa is not None or bloques is not None:
        con.execute("create table mart_eje_controles(prueba varchar, eje double, ic_bajo double, ic_alto double, ancho_ic double, "
                    "p_perm double, dist_93 double, amplitud double)")
        con.execute("create table mart_eje_controles_veredicto(prueba varchar, veredicto varchar, dispara_regla_parada boolean)")
        for clave, disp in (("eje_previo_k-1", previa), ("bloques_5km", bloques)):
            if disp is not None:
                con.execute("insert into mart_eje_controles values (?, 90, 70, 110, 40, 0.05, 3, 10)", [clave])
                con.execute("insert into mart_eje_controles_veredicto values (?, 'x', ?)", [clave, disp])
    if expo is not None:
        con.execute("create table mart_eje_exposicion_veredicto(condicion varchar, cumple boolean, detalle varchar, dispara_regla_parada boolean)")
        con.execute("insert into mart_eje_exposicion_veredicto values ('(i) a', ?, 'd', ?)", [expo, expo])
    return con


def test_sin_marts_nada_corrio_y_no_se_puede_juzgar():
    con = _con()
    assert [p["estado"] for p in ep.patas(con)] == ["sin correr"] * 4
    assert ep.se_cumple(con) is None
    assert "No se corrió ninguna pata" in ep.pagina_eje_parada(con)


def test_ninguna_dispara_no_se_cumple():
    con = _con(potencia=(1.5, "1,5 veces", "separable"), previa=False, bloques=False, expo=False)
    assert ep.se_cumple(con) is False
    assert "no se cumple" in ep.pagina_eje_parada(con)


def test_una_sola_pata_alcanza():
    con = _con(potencia=(1.5, "1,5 veces", "separable"), previa=False, bloques=False, expo=True)
    ps = ep.patas(con)
    assert [p["dispara"] for p in ps] == [False, False, True, False]
    assert ep.se_cumple(con) is True
    pag = ep.pagina_eje_parada(con)
    assert ep.FRASE in pag and "asimetria_de_superficie" in pag


def test_pata_sin_correr_no_dispara():
    con = _con(potencia=(2.4, "2,4 veces", "no separable"))
    ps = {p["pata"]: p for p in ep.patas(con)}
    assert ps[1]["dispara"] and ps[2]["estado"] == "sin correr" and not ps[4]["dispara"]
    assert ep.se_cumple(con) is True


def test_la_pagina_no_usa_rayas_largas():
    con = _con(potencia=(2.4, "2,4 veces", "no separable"), previa=True, bloques=True, expo=True)
    pag = ep.pagina_eje_parada(con)
    assert chr(0x2013) not in pag and chr(0x2014) not in pag


def test_incompleta_si_faltan_patas_y_ninguna_dispara():
    con = _con(potencia=(1.5, "1,5 veces", "separable"), previa=False)
    assert ep.se_cumple(con) is False
    assert "incompleta" in ep.pagina_eje_parada(con)


def test_aviso_solo_si_dispara():
    assert ep.aviso_anisotropia(_con(potencia=(1.5, "1,5 veces", "separable"))) == []
