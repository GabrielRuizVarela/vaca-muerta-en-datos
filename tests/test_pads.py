import duckdb

from pipeline import pads
from tests.test_pipeline import prod_row, warehouse  # noqa: F401  (fixture)

# 0.0001 degrees of latitude is about 11 m.
LAT0, LON0 = -38.0, -69.0


def _pozos(warehouse, coords):  # noqa: F811
    rows = [prod_row(i, 2024, 1, 100, lon=f"{lon:.6f}", lat=f"{lat:.6f}") for i, (lon, lat) in coords.items()]
    return warehouse(rows, [])


def _pad(con, pozo):
    return con.execute("select pad_id from int_pozo_ubicacion where pozo_id = ?", [pozo]).fetchone()[0]


def test_wells_10_m_apart_share_a_pad_and_far_wells_split(warehouse):  # noqa: F811
    con = _pozos(warehouse, {1: (LON0, LAT0), 2: (LON0, LAT0 + 0.00009),   # about 10 m
                             3: (LON0, LAT0 + 0.0109)})                    # about 1.2 km away
    assert _pad(con, 1) == _pad(con, 2) == "p1"
    assert _pad(con, 3) != _pad(con, 1)


def test_wells_100_m_apart_split(warehouse):  # noqa: F811
    con = _pozos(warehouse, {1: (LON0, LAT0), 2: (LON0, LAT0 + 0.0009)})   # about 100 m
    assert _pad(con, 1) != _pad(con, 2)


def test_chain_of_wells_40_m_apart_is_one_pad(warehouse):  # noqa: F811
    paso = 0.00036  # about 40 m of latitude
    con = _pozos(warehouse, {i: (LON0, LAT0 + i * paso) for i in range(1, 6)})  # ends 160 m apart
    assert len({_pad(con, i) for i in range(1, 6)}) == 1
    assert _pad(con, 3) == "p1"


def _ubicacion(rows):
    con = duckdb.connect()
    con.execute("create table int_pozo_ubicacion (pozo_id bigint, lon double, lat double, pad_id varchar)")
    con.executemany("insert into int_pozo_ubicacion values (?, ?, ?, ?)", rows)
    return con


def test_figures_count_a_hand_made_case():
    # Old rounding cells (3 decimals): A = wells 1,2,3 (new pads p1 = {1,2} and p3 = {3}: split),
    # B = wells 4,5 (one new pad, unchanged), C = well 6 (alone, unchanged),
    # D = well 7 and E = well 8 (different cells, one new pad: merge across a rounding edge).
    con = _ubicacion([
        (1, -69.0001, -38.0001, "p1"), (2, -69.0002, -38.0001, "p1"), (3, -69.0004, -38.0004, "p3"),
        (4, -69.1001, -38.1001, "p4"), (5, -69.1002, -38.1002, "p4"),
        (6, -69.2001, -38.2001, "p6"),
        (7, -69.3004, -38.3001, "p7"), (8, -69.3006, -38.3001, "p7"),
    ])
    c = pads.cifras(con)
    assert c["pozos"] == 8
    assert c["pads_viejos"] == 5 and c["pads_nuevos"] == 5
    assert c["pads_viejos_divididos"] == 1       # cell A
    assert c["pads_nuevos_fusionan"] == 1        # pad p7
    assert c["pozos_cambian"] == 5               # wells 1, 2, 3, 7, 8
    assert c["pct_pozos_3mas_viejo"] == 37.5     # cell A has 3 wells
    assert c["pct_pozos_3mas_nuevo"] == 0.0
    assert [r[0] for r in con.execute(pads.SQL_CAMBIADOS + " order by 1").fetchall()] == [1, 2, 3, 7, 8]
    assert "5 pozos cambian de pad" in pads.detalle(con)
