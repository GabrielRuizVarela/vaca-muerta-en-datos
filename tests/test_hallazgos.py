import duckdb

from pipeline import hallazgos as hz


def test_clasificar_estados():
    assert hz.clasificar("<", -0.2, -0.1) == "confirmado"
    assert hz.clasificar("<", -0.08, -0.1) == "debilitado"  # falla por 0.02 < 0.025
    assert hz.clasificar("<", 0.0, -0.1) == "refutado"
    assert hz.clasificar(">", 0.12, 0.10) == "confirmado"
    assert hz.clasificar(">", 0.09, 0.10) == "debilitado"
    assert hz.clasificar(">", 0.0, 0.10) == "refutado"
    assert hz.clasificar("abs<", -0.02, 0.05) == "confirmado"
    assert hz.clasificar("abs<", 0.06, 0.05) == "debilitado"
    assert hz.clasificar("abs<", -0.2, 0.05) == "refutado"
    assert hz.clasificar(">", None, 0.1) == "refutado"


def _con():
    con = duckdb.connect()
    con.execute("create table ultimo_mes as select date '2026-01-01' as mes")
    con.execute("create table int_interferencia_mes(padre int, mes_frac timestamp, banda varchar,"
                " grupo_edad varchar, k bigint, indice double, m3_d double, dias_mes bigint)")
    rows = []
    for i, (cer, ctl) in enumerate([(0.7, 1.0), (0.8, 1.0), (0.9, 1.0)]):
        rows.append((i, "cercano", 1, cer))
        rows.append((i + 10, "control", 1, ctl))
        rows.append((i, "cercano", 6, 1.0))
        rows.append((i + 10, "control", 6, 1.0))
    for p, b, k, v in rows:
        con.execute("insert into int_interferencia_mes values (?, timestamp '2025-01-01', ?, 'a', ?, ?, 1, 30)",
                    [p, b, k, v])
    return con


def test_evaluar_en_memoria():
    con = _con()
    h1 = next(h for h in hz.HIPOTESIS if h.id == "brecha_mes1")
    assert abs(con.execute(h1.sql).fetchall()[0][0] - (-0.2)) < 1e-9
    h2 = next(h for h in hz.HIPOTESIS if h.id == "recuperacion_mes6")
    assert con.execute(h2.sql).fetchall()[0][0] == 0.0


def test_registrar_idempotente(tmp_path):
    p = tmp_path / "hallazgos" / "ledger.csv"
    fila = {"id": "x", "sha_datos": "abc", "mes_datos": "2026-01", "valor": 1.0, "op": "<",
            "umbral": 2.0, "estado": "confirmado", "evaluado_en": "2026-01-02"}
    assert hz.registrar([fila], p) == 1
    assert hz.registrar([fila], p) == 0
    assert len(hz.leer_ledger(p)) == 1
    assert hz.registrar([dict(fila, sha_datos="def")], p) == 1
    assert len(hz.leer_ledger(p)) == 2


def test_lint_enlace_roto_y_refutado(tmp_path):
    (tmp_path / "hallazgos").mkdir()
    (tmp_path / "ok.md").write_text("[a](hallazgos/b.md) [web](https://x.org) [i](#t)\n", encoding="utf-8")
    (tmp_path / "hallazgos" / "b.md").write_text("[roto](no_existe.md)\n", encoding="utf-8")
    hz.registrar([{"id": "h", "sha_datos": "s", "mes_datos": "2026-01", "valor": 5.0, "op": "<",
                   "umbral": 1.0, "estado": "refutado", "evaluado_en": "d"}],
                 tmp_path / "hallazgos" / "ledger.csv")
    avisos = hz.lint_wiki(tmp_path)
    assert any("no_existe.md" in a for a in avisos)
    assert not any("ok.md" in a for a in avisos)
    assert any("refutado" in a and "h" in a for a in avisos)


def test_registrar_nueva_fila_si_cambia_la_hipotesis(tmp_path):
    p = tmp_path / "ledger.csv"
    h = hz.HIPOTESIS[0]
    fila = {"id": h.id, "sha_datos": "abc", "firma": hz.firma(h), "mes_datos": "2026-01", "valor": 1.0,
            "op": h.op, "umbral": h.umbral, "estado": "confirmado", "evaluado_en": "2026-01-02"}
    assert hz.registrar([fila], p) == 1
    otra = hz.Hipotesis(h.id, h.enunciado, h.sql, h.op, h.umbral + 1, h.unidad)
    assert hz.firma(otra) != hz.firma(h)
    assert hz.registrar([dict(fila, firma=hz.firma(otra))], p) == 1


def test_sha_datos_incluye_fractura():
    m = {"produccion_no_convencional": {"sha256": "a" * 64}, "fractura_adjunto_iv": {"sha256": "b" * 64}}
    m2 = {"produccion_no_convencional": {"sha256": "a" * 64}, "fractura_adjunto_iv": {"sha256": "c" * 64}}
    assert hz.sha_produccion(m) != hz.sha_produccion(m2)


def _holdout(ic_sh, ic_al, prop):
    return [{"modelo": "Entrenamiento menos SHmax", "ic_bajo": ic_sh, "mejora_rss": 0.0},
            {"modelo": "Entrenamiento menos la mediana de los ejes aleatorios", "ic_bajo": ic_al, "mejora_rss": 0.0},
            {"modelo": "Proporción de ejes aleatorios con mejora igual o mayor", "ic_bajo": None, "mejora_rss": prop}]


def test_holdout_razones_firme_y_no_firme():
    from pipeline.validacion import holdout_razones
    assert holdout_razones(_holdout(0.01, 0.01, 0.02)) == []
    assert len(holdout_razones(_holdout(-0.01, 0.01, 0.02))) == 1   # no se separa del SHmax
    assert len(holdout_razones(_holdout(0.01, 0.01, 0.07))) == 1    # una parte de los ejes al azar lo iguala
    assert len(holdout_razones(_holdout(-0.01, -0.01, 0.07))) == 2


def _con_robustez(ancho_sub, p_sub, holdout):
    con = duckdb.connect()
    con.execute("create table mart_robustez_eje as select * from (values "
                f"('completa', 50.0, 0.01), ('periodo', {ancho_sub}, {p_sub})) t(grupo, ancho_ic, p_perm)")
    con.execute("create table mart_validacion_holdout (modelo varchar, ic_bajo double, mejora_rss double)")
    for r in holdout:
        con.execute("insert into mart_validacion_holdout values (?, ?, ?)", [r["modelo"], r["ic_bajo"], r["mejora_rss"]])
    return con


def test_razones_eje_no_firme_lee_los_marts():
    firme = _con_robustez(60.0, 0.02, _holdout(0.01, 0.01, 0.02))
    assert hz.razones_eje_no_firme(firme) == []
    ancho = _con_robustez(120.0, 0.02, _holdout(0.01, 0.01, 0.02))
    assert any("subconjuntos" in r for r in hz.razones_eje_no_firme(ancho))
    fuera_de_tiempo = _con_robustez(60.0, 0.02, _holdout(-0.01, 0.01, 0.02))
    assert any("SHmax" in r for r in hz.razones_eje_no_firme(fuera_de_tiempo))
    assert hz.razones_eje_no_firme(duckdb.connect()) is None


def test_solo_la_hipotesis_del_eje_exige_firmeza():
    assert [h.id for h in hz.HIPOTESIS if h.firmeza] == ["asimetria_de_superficie"]
    sin = hz.Hipotesis("x", "e", "select 1", "<", 0.0, "u")
    assert hz.firma(sin) != hz.firma(hz.Hipotesis("x", "e", "select 1", "<", 0.0, "u", firmeza=True))


def test_id_renombrado_sigue_siendo_valido_en_la_operacion_del_agente():
    import duckdb
    from agente.ops import ArgsLibro, libro_hallazgos
    r = libro_hallazgos(duckdb.connect(), ArgsLibro(id="anisotropia"))
    assert r["texto"].startswith("asimetria_de_superficie")


def test_la_hipotesis_del_anio_2026_toma_el_estado_del_veredicto_de_su_regla():
    h = next(h for h in hz.HIPOTESIS if h.id == "anio_2026_carga")
    con = duckdb.connect()
    con.execute("create table mart_carga_anual_prueba(estadistico varchar, d double, ic_bajo double, ic_alto double, "
                "veredicto varchar)")
    con.execute("insert into mart_carga_anual_prueba values ('2026', -0.15, -0.46, 0.13, 'no firme'), "
                "('2025_2026', -0.22, -0.42, -0.02, null)")
    assert con.execute(h.sql).fetchall() == [(0.13,)] and (h.op, h.umbral) == ("<", 0.0)
    ver = con.execute(h.sql_estado).fetchall()[0][0]
    assert hz.ESTADO_DE_VEREDICTO.get(ver, "no firme") == "no firme"
    # un IC bajo cero no alcanza si la guarda de operador falla: el estado sale del veredicto, no del umbral
    con.execute("update mart_carga_anual_prueba set ic_alto = -0.01 where estadistico = '2026'")
    assert hz.clasificar(h.op, con.execute(h.sql).fetchall()[0][0], h.umbral) == "confirmado"
    assert hz.ESTADO_DE_VEREDICTO.get(con.execute(h.sql_estado).fetchall()[0][0], "no firme") == "no firme"
    con.execute("update mart_carga_anual_prueba set veredicto = 'sostiene' where estadistico = '2026'")
    assert hz.ESTADO_DE_VEREDICTO.get(con.execute(h.sql_estado).fetchall()[0][0], "no firme") == "confirmado"
