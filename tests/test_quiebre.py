import pytest

from agente.ops import ArgsEventos, eventos_pozo
from pipeline import checks
from tests.test_pipeline import frac_row, one, prod_row, warehouse  # noqa: F401  (fixture)

MESES = [(2023, m) for m in range(1, 13)] + [(2024, m) for m in range(1, 7)]
CHECK = next(c for c in checks.CHECKS if c.nombre.startswith("Quiebres de caudal"))


def _rows(rate_parent_a, rate_parent_b):
    """Parents 1 (90 m from the child) and 2 (about 4 km away) plus child 3, fracked in March 2024."""
    rows = []
    for y, m in MESES:
        rows.append(prod_row(1, y, m, rate_parent_a(y, m), lon="-69.000", lat="-38.000"))
        rows.append(prod_row(2, y, m, rate_parent_b(y, m), lon="-69.000", lat="-38.036"))
        if (y, m) >= (2024, 3):
            rows.append(prod_row(3, y, m, 500, lon="-69.001", lat="-38.000"))
    return rows


def _con(warehouse, rate_a):
    return warehouse(_rows(rate_a, lambda y, m: 300), [frac_row(1, 3, "2024-03-10")])


def _drop(y, m):
    return 150 if (y, m) in ((2024, 3), (2024, 4)) else 300


def test_parent_that_drops_gets_exactly_one_quiebre(warehouse):
    con = _con(warehouse, _drop)
    rows = con.execute("select pozo_id, fecha, mes, detalle, valor from fct_evento where tipo = 'quiebre_caudal'").fetchall()
    assert len(rows) == 1
    pozo, fecha, mes, detalle, valor = rows[0]
    assert pozo == 1 and str(fecha)[:10] == "2024-03-01" and fecha == mes
    base = (300 / 31 + 300 / 31 + 300 / 29) / 3  # Dec 2023, Jan and Feb 2024
    indice = (150 / 31 / base + 150 / 30 / base) / 2
    assert valor == pytest.approx(1 - indice)
    assert 0.25 < valor < 1
    assert detalle.startswith("pad ") and detalle.endswith(" km")
    assert CHECK.nombre in [c["nombre"] for c in checks.run(con, [CHECK])["checks"]]
    assert checks.run(con, [CHECK])["checks"][0]["ok"]


def test_parent_that_does_not_drop_gets_none(warehouse):
    con = _con(warehouse, lambda y, m: 300)
    assert one(con, "select count(*) from fct_evento where tipo = 'quiebre_caudal'") == 0
    # A mild dip (index 0.8) stays above the 75% threshold.
    con = _con(warehouse, lambda y, m: 240 if (y, m) in ((2024, 3), (2024, 4)) else 300)
    assert one(con, "select count(*) from fct_evento where tipo = 'quiebre_caudal'") == 0


def test_far_parent_never_gets_quiebre(warehouse):
    # The control parent (about 4 km away, banda control) drops as well but is not a near neighbour.
    rows = _rows(lambda y, m: 300, lambda y, m: 100 if (y, m) in ((2024, 3), (2024, 4)) else 300)
    con = warehouse(rows, [frac_row(1, 3, "2024-03-10")])
    assert one(con, "select count(*) from fct_evento where tipo = 'quiebre_caudal'") == 0


def test_quiebre_requires_both_months(warehouse):
    rows = [r for r in _rows(_drop, lambda y, m: 300) if not (r["idpozo"] == 1 and (r["anio"], r["mes"]) == (2024, 4))]
    con = warehouse(rows, [frac_row(1, 3, "2024-03-10")])
    assert one(con, "select count(*) from fct_evento where tipo = 'quiebre_caudal'") == 0


def test_eventos_pozo_accepts_quiebre_and_rejects_unknown(warehouse):
    con = _con(warehouse, _drop)
    r = eventos_pozo(con, ArgsEventos(sigla="P-1", tipo="quiebre_caudal"))
    assert r["valor"] == 1
    assert r["filas"][0]["tipo"] == "quiebre_caudal"
    assert eventos_pozo(con, ArgsEventos(sigla="P-2", tipo="quiebre_caudal"))["valor"] == 0
    with pytest.raises(ValueError):
        ArgsEventos(sigla="P-1", tipo="terremoto")


def test_check_flags_corrupted_rows(warehouse):
    con = _con(warehouse, _drop)
    assert checks.run(con, [CHECK])["checks"][0]["filas"] == 0
    con.execute("update fct_evento set valor = 0.1 where tipo = 'quiebre_caudal'")
    assert checks.run(con, [CHECK])["checks"][0]["filas"] == 1
    con.execute("update fct_evento set valor = 0.5, mes = date '2023-05-01' where tipo = 'quiebre_caudal'")
    assert checks.run(con, [CHECK])["checks"][0]["filas"] == 1
