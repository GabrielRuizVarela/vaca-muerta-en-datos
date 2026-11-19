"""Export the time replay (site/replay.html): one self-contained page with the basin history embedded.

Data contract (read by pipeline/replay_template.html):

- meta:    {meses: ["2012-01", ...], n_pozos, hash_datos, mes_datos, generado, ops: [...]}
- pozos:   [{id, op, area, pad, lon, lat, mes0, frac}] in matrix row order (shale wells with a location).
           mes0 is the index into meses of the first month with oil, frac the date of the first frac job.
- caudal:  base64 of a little-endian Uint16 matrix pozos x meses, oil rate in bbl/d.
- agua:    base64 of a Uint8 matrix pozos x meses, water cut x 255.
- estado:  base64 of a Uint8 matrix pozos x meses, bits 1 producing, 2 declared stopped, 4 lift system changed.
- eventos: [{f: "AAAA-MM-DD", t: "frac" | "interf", p: well index, h: child well index, km, rumbo, clase, bbl}]
           For t == "interf", p is the parent and h the child; rumbo is the axis bearing 0..180 deg of the
           child-parent line; clase is golpe / cierre_preventivo / ambos / sin_efecto; bbl is the deferred oil.
- cuenca:  {ops: [...], kbbl: [[per month] per operator]} from mart_vm_mensual (the rest goes to "Otros").
- curva:   median rate index of near parents and controls by month relative to the child frac.
- corte:   median water cut (water over water plus oil, months with oil) of the same parents, by band and month
           relative to the child frac. The page writes the figures of its findings from curva and corte, which
           is why neither is rounded here: a value rounded twice can print a different last digit.
- base:    the base map of pipeline.base_mapa as written in data/base_mapa.json (its contract is in that module's
           docstring), the same product that pipeline.mundo embeds; None when the file is absent, and then the
           page draws its plain grid.

Uses the T1 tables when they exist (fct_produccion.estado/extraccion, fct_evento, int_interferencia_clase) and
derives the same facts from staging otherwise.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import sys
from array import array
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from pipeline import base_mapa
from pipeline.ingest import DATA, ROOT

TEMPLATE = Path(__file__).parent / "replay_template.html"
OUT = ROOT / "site" / "replay.html"
BBL_PER_M3 = 6.2898
N_OPS = 6  # YPF plus five more; the rest is grey
MIN_ACTIVE = 10  # the timeline starts when this many mapped wells produce
JUMP = 0.15  # water cut jump (points) that counts as a hit
MAX_BYTES = 8 * 1024 * 1024
STOPPED = "Parado Transitoriamente"


def q(con, sql):
    return con.execute(sql).fetchall()


def columns(con, table):
    return {r[0] for r in q(con, f"select column_name from information_schema.columns where table_name = '{table}'")}


def month_key(d) -> str:
    return d.strftime("%Y-%m")


def b64(arr: array) -> str:
    if sys.byteorder == "big" and arr.itemsize > 1:
        arr = array(arr.typecode, arr)
        arr.byteswap()
    return base64.b64encode(arr.tobytes()).decode("ascii")


def axis_bearing(lon1, lat1, lon2, lat2) -> int:
    """Bearing 0..180 deg (axis, not direction) of the line between two surface points."""
    dx = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    dy = lat2 - lat1
    return int(round(math.degrees(math.atan2(dx, dy)))) % 180


def leer_base(path: Path = base_mapa.DESTINO) -> dict | None:
    """The base map that pipeline.base_mapa writes (relief, water, borders, towns and blocks); None when absent."""
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def collect(con, base_path: Path = base_mapa.DESTINO) -> dict:
    ultimo = q(con, "select mes from ultimo_mes")[0][0]
    ultimo = ultimo.date() if isinstance(ultimo, datetime) else ultimo
    fcols = columns(con, "fct_produccion")
    tables = {r[0] for r in q(con, "select table_name from information_schema.tables")}

    wells = q(con, """
        select pozo_id, operador, area, pad_id, lon, lat, primer_mes_petroleo
        from int_pozo_ubicacion order by pozo_id""")
    idx = {w[0]: i for i, w in enumerate(wells)}
    n = len(wells)

    estado_sql = "f.estado" if "estado" in fcols else "s.estado"
    extr_sql = "f.extraccion" if "extraccion" in fcols else "null"
    join_stg = "" if "estado" in fcols else "left join stg_produccion s on s.pozo_id = f.pozo_id and s.mes = f.mes"
    prod = q(con, f"""
        select f.pozo_id, f.mes, f.petroleo_m3, f.agua_m3, f.dias_mes, {estado_sql}, {extr_sql}
        from fct_produccion f
        join int_pozo_ubicacion u on u.pozo_id = f.pozo_id
        {join_stg}
        order by f.pozo_id, f.mes""")

    # Timeline: from the first month with MIN_ACTIVE producing mapped wells up to the last data month.
    active: dict[date, int] = {}
    for r in prod:
        if r[2] and r[2] > 0:
            active[r[1]] = active.get(r[1], 0) + 1
    first = min(m for m, c in sorted(active.items()) if c >= MIN_ACTIVE)
    months: list[date] = []
    y, m = first.year, first.month
    while date(y, m, 1) <= ultimo:
        months.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    mi = {d: i for i, d in enumerate(months)}
    nm = len(months)

    caudal = array("H", bytes(2 * n * nm))
    agua = array("B", bytes(n * nm))
    estado = array("B", bytes(n * nm))
    wc = [[math.nan] * nm for _ in range(n)]  # exact water cut, for the hit classification
    prev_extr: dict[int, str] = {}
    for pid, mes, pet, ag, dias, est, extr in prod:
        k = mi.get(mes.date() if isinstance(mes, datetime) else mes)
        if k is None:
            continue
        p = idx[pid]
        pet = pet or 0.0
        ag = ag or 0.0
        bit = 0
        if pet > 0:
            bit |= 1
            caudal[p * nm + k] = min(65535, int(round(pet / dias * BBL_PER_M3))) if dias else 0
        if est == STOPPED:
            bit |= 2
        if extr is not None:
            if p in prev_extr and prev_extr[p] != extr:
                bit |= 4
            prev_extr[p] = extr
        if pet + ag > 0:
            w = ag / (ag + pet)
            wc[p][k] = w
            agua[p * nm + k] = int(round(w * 255))
        estado[p * nm + k] = bit

    mes0 = []
    for w in wells:
        d = w[6]
        d = d.date() if isinstance(d, datetime) else d
        mes0.append(mi[d] if d in mi else (0 if d is not None and d < months[0] else nm))

    # Frac jobs (events): fct_evento when T1 is in, otherwise stg_fractura.
    frac_rows = []
    if "fct_evento" in tables:
        tipos = {r[0] for r in q(con, "select distinct tipo from fct_evento")}
        tipo = next((t for t in ("fractura", "frac") if t in tipos), None)
        if tipo:
            frac_rows = q(con, f"select pozo_id, fecha from fct_evento where tipo = '{tipo}' and fecha is not null")
    if not frac_rows:
        frac_rows = q(con, """
            select f.pozo_id, f.fecha_inicio from stg_fractura f join int_pozo_ubicacion u using (pozo_id)
            where f.fecha_inicio is not null""")
    after_last = date(ultimo.year + (ultimo.month == 12), ultimo.month % 12 + 1, 1)
    eventos = []
    first_frac: dict[int, date] = {}
    frac_by_well_month: dict[tuple[int, date], date] = {}
    for pid, fecha in sorted(frac_rows, key=lambda r: (r[1], r[0])):
        fecha = fecha.date() if isinstance(fecha, datetime) else fecha
        if pid not in idx or fecha >= after_last:
            continue
        p = idx[pid]
        first_frac.setdefault(p, fecha)
        frac_by_well_month.setdefault((p, fecha.replace(day=1)), fecha)
        if fecha.replace(day=1) >= months[0]:
            eventos.append({"f": fecha.isoformat(), "t": "frac", "p": p})

    # Interference events: near (< 1 km) and intermediate (1 to 2 km) parents, controls left out.
    has_clase = "int_interferencia_clase" in tables
    clase_map = {}
    if has_clase:
        for padre, mes_frac, clase, rumbo in q(con, "select padre, mes_frac, clase, rumbo_eje from int_interferencia_clase"):
            clase_map[(padre, mes_frac.date() if isinstance(mes_frac, datetime) else mes_frac)] = (clase, rumbo)
    bbl = {(r[0], r[1].date() if isinstance(r[1], datetime) else r[1], r[2]): r[3] for r in q(con, """
        select padre, mes_frac, hijo_cercano, petroleo_diferido_bbl from mart_interferencia_diferida""")}
    for padre, mes_frac, km, hijo in q(con, """
            select padre, mes_frac, km_min, hijo_cercano from int_interferencia_evento
            where banda in ('cercano', 'intermedio') order by mes_frac, padre"""):
        mes_frac = mes_frac.date() if isinstance(mes_frac, datetime) else mes_frac
        if padre not in idx or hijo not in idx or mes_frac not in mi:
            continue
        p, h, k = idx[padre], idx[hijo], mi[mes_frac]
        pw, hw = wells[p], wells[h]
        rumbo = axis_bearing(hw[4], hw[5], pw[4], pw[5])
        if (padre, mes_frac) in clase_map:
            clase, r2 = clase_map[(padre, mes_frac)]
            rumbo = int(round(r2)) % 180 if r2 is not None else rumbo
        else:
            pre = [wc[p][j] for j in range(max(0, k - 3), k) if not math.isnan(wc[p][j])]
            post = [wc[p][j] for j in (k, k + 1) if j < nm and not math.isnan(wc[p][j])]
            salto = bool(pre and post and max(post) - sum(pre) / len(pre) > JUMP)
            parado = bool(estado[p * nm + k] & 2)
            clase = ("ambos" if salto and parado else "golpe" if salto else
                     "cierre_preventivo" if parado else "sin_efecto")
        fecha = frac_by_well_month.get((h, mes_frac), mes_frac)
        ev = {"f": fecha.isoformat(), "t": "interf", "p": p, "h": h, "km": round(km, 2), "rumbo": rumbo,
              "clase": clase}
        b = bbl.get((padre, mes_frac, hijo))
        if b is not None:
            ev["bbl"] = int(round(b))
        eventos.append(ev)
    eventos.sort(key=lambda e: (e["f"], e["t"]))

    # Basin series by operator (kbbl/d).
    last = {r[0]: r[1] for r in q(con, """
        select operador, petroleo_kbbl_d from mart_vm_mensual where mes = (select mes from ultimo_mes)""")}
    top = ["YPF"] + [o for o in sorted(last, key=lambda o: -last[o]) if o != "YPF"][: N_OPS - 1]
    kbbl = {o: [0.0] * nm for o in top + ["Otros"]}
    for mes, op, v in q(con, "select mes, operador, petroleo_kbbl_d from mart_vm_mensual"):
        k = mi.get(mes.date() if isinstance(mes, datetime) else mes)
        if k is not None:
            kbbl[op if op in top else "Otros"][k] += v or 0.0
    cuenca = {"ops": top + ["Otros"], "kbbl": [[round(v, 3) for v in kbbl[o]] for o in top + ["Otros"]]}

    # The two series behind the printed findings travel unrounded: the page rounds once, at the moment it prints.
    curva = [{"banda": b, "k": k, "indice": float(v)} for b, k, v in q(con, """
        select banda, k, indice_mediana from mart_interferencia_curva
        where banda in ('cercano', 'control') order by banda, k""")]
    # Water cut of the same parents and months; a month without oil has no cut to speak of and stays out.
    corte = [{"banda": b, "k": k, "corte": float(v)} for b, k, v in q(con, """
        select i.banda, i.k, median(f.agua_m3 / (f.agua_m3 + f.petroleo_m3))
        from int_interferencia_mes i
        join fct_produccion f on f.pozo_id = i.padre and f.mes = i.mes_frac + to_months(i.k)
        where i.banda in ('cercano', 'control') and f.petroleo_m3 > 0
        group by i.banda, i.k order by i.banda, i.k""")]

    # The wiki writes a page only for pads with deferred-interference events.
    pads_wiki = {r[0] for r in q(con, "select distinct pad_id from mart_interferencia_diferida")}
    pozos = [{"id": w[0], "op": w[1] if w[1] in top else "Otros", "op_nombre": w[1], "area": w[2], "pad": w[3],
              "wiki": w[3] in pads_wiki,
              "lon": round(w[4], 5), "lat": round(w[5], 5), "mes0": mes0[i],
              "frac": first_frac[i].isoformat() if i in first_frac else None} for i, w in enumerate(wells)]

    h = hashlib.sha1()
    for a in (caudal, agua, estado):
        h.update(a.tobytes())
    meta = {"meses": [month_key(d) for d in months], "n_pozos": n, "hash_datos": h.hexdigest()[:12],
            "mes_datos": month_key(ultimo), "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "ops": cuenca["ops"], "usa_t1": has_clase or "estado" in fcols}
    return {"meta": meta, "pozos": pozos, "caudal": b64(caudal), "agua": b64(agua), "estado": b64(estado),
            "eventos": eventos, "cuenca": cuenca, "curva": curva, "corte": corte, "base": leer_base(base_path)}


def render(data: dict, out: Path) -> int:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"{out} is {size} bytes, over the {MAX_BYTES} byte budget")
    return size


def main() -> int:
    con = duckdb.connect(str(DATA / "warehouse.duckdb"), read_only=True)
    size = render(collect(con), OUT)
    print(f"wrote {OUT} ({size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
