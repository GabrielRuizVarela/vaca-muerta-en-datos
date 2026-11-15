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
