"""Render the static dashboard (site/index.html) from the warehouse marts."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline.ingest import DATA, ROOT

TEMPLATE = Path(__file__).parent / "report_template.html"
TOP_N = 5


def rows(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def collect(con) -> dict:
    ultimo = con.execute("select mes from ultimo_mes").fetchall()[0][0]
    top = [r["operador"] for r in rows(con, f"""
        select operador from mart_vm_mensual where mes = (select mes from ultimo_mes)
        order by petroleo_kbbl_d desc limit {TOP_N}""")]
    top_sql = ", ".join("'" + t.replace("'", "''") + "'" for t in top)
    mensual = rows(con, f"""
        select strftime(mes, '%Y-%m') as mes,
               case when operador in ({top_sql}) then operador else 'Otros' end as grupo,
               round(sum(petroleo_kbbl_d), 2) as kbbl_d
        from mart_vm_mensual where mes >= date '2015-01-01'
        group by all order by 1""")
    kpi = rows(con, """
        with t as (
          select mes, sum(petroleo_kbbl_d) pet, sum(petroleo_kbbl_d) filter (where operador = 'YPF') ypf,
                 sum(gas_mmm3_d) gas, sum(pozos_activos) pozos
          from mart_vm_mensual group by mes)
        select a.pet, a.ypf, a.gas, a.pozos, b.pet as pet_anio_previo, b.ypf as ypf_anio_previo
        from t a join t b on b.mes = a.mes - interval 12 month
        where a.mes = (select mes from ultimo_mes)""")[0]
    curvas = rows(con, "select cohorte, grupo, mop, pozos, round(petroleo_bbl_d, 1) as bbl_d "
                       "from mart_curva_tipo order by cohorte, grupo, mop")
    diseno = rows(con, "select * from mart_diseno_productividad order by cohorte, grupo")
    dq = json.loads((DATA / "dq_report.json").read_text())
    return {
        "ultimo_mes": ultimo.strftime("%Y-%m"),
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "operadores": top + ["Otros"],
        "kpi": kpi,
        "mensual": mensual,
        "curvas": curvas,
        "diseno": diseno,
        "dq": {k: dq[k] for k in ("filas_origen_produccion", "bloqueantes_fallidos", "checks", "fuentes")},
    }


def render(data: dict, out: Path) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.read_text().replace("/*__DATA__*/null", payload))


def main() -> int:
    con = duckdb.connect(str(DATA / "warehouse.duckdb"), read_only=True)
    out = ROOT / "site" / "index.html"
    render(collect(con), out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
