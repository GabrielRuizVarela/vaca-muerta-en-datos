"""Render the static dashboard (site/index.html) from the warehouse marts."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline.ingest import DATA, ROOT

TEMPLATE = Path(__file__).parent / "report_template.html"
CHARTJS = Path(__file__).parent / "vendor" / "chart.umd.min.js"
TOP_N = 5


def rows(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def tabla_existe(con, nombre: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_schema = 'main' "
                            "and table_name = ?", [nombre]).fetchone()[0])


def eje_cuenca(con) -> dict | None:
    """Eje de mayor merma de la cuenca (mart_anisotropia_area, fila 'Cuenca') y cuántos cortes de robustez lo sostienen."""
    if not tabla_existe(con, "mart_anisotropia_area"):
        return None
    fila = rows(con, "select eje_grados, ic_bajo, ic_alto, ancho_ic, p_perm, n from mart_anisotropia_area "
                     "where area = 'Cuenca'")
    if not fila:
        return None
    eje = fila[0]
    eje["cortes"] = None
    if tabla_existe(con, "mart_robustez_eje"):
        eje["cortes"] = rows(con, """
            select count(*) as total,
                   count(*) filter (where ancho_ic >= 90 or p_perm >= 0.10) as sin_evidencia
            from mart_robustez_eje where grupo <> 'completa'""")[0]
    return eje


def costo_cv(con) -> dict | None:
    """R2 fuera de muestra del modelo de costo y de la media del entrenamiento (mart_costo_cv, modelos 'modelo' y
    'media_entrenamiento'), o None si el mart no existe."""
    if not tabla_existe(con, "mart_costo_cv"):
        return None
    cols = [r[0] for r in con.execute("describe mart_costo_cv").fetchall()]
    if "modelo" not in cols or "r2" not in cols:
        return None
    dato = {r["modelo"]: r["r2"] for r in rows(con, "select modelo, r2 from mart_costo_cv "
                                                     "where modelo in ('modelo', 'media_entrenamiento')")}
    if dato.keys() != {"modelo", "media_entrenamiento"} or None in dato.values():
        return None
    return {"completo": dato["modelo"], "media": dato["media_entrenamiento"]}


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
        group by all order by 1, 2""")
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
    interf = {
        "curva": rows(con, "select banda, k, eventos, round(indice_mediana, 3) as indice from mart_interferencia_curva "
                           "where banda in ('cercano', 'control') order by banda, k"),
        "anual": rows(con, "select anio, eventos_cercanos, round(brecha_mes_1, 3) as brecha from mart_interferencia_anual "
                           "where anio >= 2016 and eventos_cercanos >= 30 order by anio"),
        "resumen": rows(con, """
            select (select count(*) from mart_interferencia_diferida) as eventos,
                   (select sum(petroleo_diferido_bbl) from mart_interferencia_diferida) as diferido_bbl,
                   (select sum(petroleo_diferido_bbl) from mart_interferencia_diferida where operador = 'YPF') as diferido_ypf_bbl,
                   (select median(indice) filter (where banda = 'cercano') - median(indice) filter (where banda = 'control')
                      from int_interferencia_mes where k = 1) as brecha_mes_1,
                   (select median(indice) filter (where banda = 'cercano') - median(indice) filter (where banda = 'control')
                      from int_interferencia_mes where k = 6) as brecha_mes_6""")[0],
    }
    evals = {}
    for split in ("dev", "holdout"):
        f = ROOT / "agente" / "eval" / "resultados" / f"{split}.json"
        if f.exists():
            r = json.loads(f.read_text())
            evals[split] = {k: r[k] for k in ("n", "exactitud", "modelo", "datos_a")}
    dq = json.loads((DATA / "dq_report.json").read_text())
    return {
        "ultimo_mes": ultimo.strftime("%Y-%m"),
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "operadores": top + ["Otros"],
        "kpi": kpi,
        "mensual": mensual,
        "curvas": curvas,
        "diseno": diseno,
        "interferencia": interf,
        "evals": evals,
        "eje": eje_cuenca(con),
        "costo_cv": costo_cv(con),
        "dq": {k: dq[k] for k in ("filas_origen_produccion", "bloqueantes_fallidos", "checks", "fuentes")},
    }


def fmt(n: float, d: int = 0) -> str:
    """Formato es-AR: punto de miles, coma decimal."""
    return f"{n:,.{d}f}".translate({ord(","): ".", ord("."): ","})


def titulares(data: dict) -> str:
    """Bloque de cifras grandes, en HTML estático (se lee sin JavaScript)."""
    k, r, dq = data["kpi"], data["interferencia"]["resumen"], data["dq"]
    interanual = (k["pet"] / k["pet_anio_previo"] - 1) * 100
    celdas = [
        (fmt(k["pet"]), "kbbl/d de petróleo", f"{data['ultimo_mes']}, {'+' if interanual >= 0 else '-'}{fmt(abs(interanual), 1)}% interanual"),
        (fmt(k["ypf"] / k["pet"] * 100, 1) + "%", "participación de YPF", f"{fmt(k['ypf'])} kbbl/d"),
        (fmt(r["eventos"]), "eventos con padre a menos de 1 km", "fracturas de un pozo nuevo junto a uno en producción"),
        (fmt((r["diferido_bbl"] or 0) / 1e6, 1) + " M", "bbl diferidos, meses 0 a 6",
             f"{fmt((r['diferido_ypf_bbl'] or 0) / r['diferido_bbl'] * 100) if r['diferido_bbl'] else '0'}% en pozos de YPF"),
        (fmt(len(dq["checks"])), "controles de datos", f"{fmt(dq['bloqueantes_fallidos'])} bloqueantes fallidos"),
    ]
    items = "".join(f'<li><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></li>'
                    for v, l, d in celdas)
    return f'<ul class="titulares" aria-label="Cifras principales">{items}</ul>'


def barra_eje(eje: dict) -> str:
    """Intervalo de confianza del eje sobre una escala de 0 a 180 grados (el eje es módulo 180)."""
    def x(g):
        return 12 + g / 180 * 336
    lo, hi, pt = eje["ic_bajo"] % 180, eje["ic_alto"] % 180, eje["eje_grados"] % 180
    tramos = [(lo, hi)] if lo <= hi else [(lo, 180), (0, hi)]
    bandas = "".join(f'<rect class="ic" x="{x(a):.1f}" y="14" width="{x(b) - x(a):.1f}" height="10" rx="2"/>' for a, b in tramos)
    marcas = "".join(f'<line class="tick" x1="{x(g):.1f}" x2="{x(g):.1f}" y1="30" y2="35"/>'
                     f'<text x="{x(g):.1f}" y="48" text-anchor="middle">{g}</text>' for g in (0, 45, 90, 135, 180))
    desc = (f'Eje {fmt(eje["eje_grados"])} grados, intervalo de confianza de {fmt(eje["ic_bajo"])} '
            f'a {fmt(eje["ic_alto"])} grados sobre una escala de 0 a 180')
    return (f'<svg class="eje-barra" viewBox="0 0 360 54" role="img" aria-label="{desc}"><title>{desc}</title>'
            f'<line class="base" x1="12" x2="348" y1="19" y2="19"/>{bandas}'
            f'<circle class="pt" cx="{x(pt):.1f}" cy="19" r="5"/>{marcas}</svg>')


def bloque_eje(data: dict) -> str:
    """Resultado del eje de mayor merma y del modelo de costo, con su incertidumbre. Vacío si faltan los marts."""
    eje = data.get("eje")
    if not eje:
        return ""
    sentido = "consistente con E-O" if abs(eje["eje_grados"] % 180 - 90) <= 30 else "fuera de la dirección E-O"
    c = eje.get("cortes")
    if c and c["sin_evidencia"] == 0:
        firmeza = "firme en los cortes de robustez"
    elif c:
        firmeza = (f"no firme: en {c['sin_evidencia']} de {c['total']} cortes de robustez "
                   "el eje no está definido o no hay evidencia")
    else:
        firmeza = "sin cortes de robustez para juzgar su firmeza"
    linea = (f"Eje de mayor merma en la cuenca: <strong>{fmt(eje['eje_grados'])} grados</strong> "
             f"(IC 95% de {fmt(eje['ic_bajo'])} a {fmt(eje['ic_alto'])}, p de permutación {fmt(eje['p_perm'], 3)}); "
             f"{sentido}, {firmeza}.")
    cv = data.get("costo_cv")
    costo = ""
    if cv:
        verbo = "no supera" if cv["completo"] <= cv["media"] else "supera"
        costo = (f"<p>El modelo de costo {verbo} a la media fuera de muestra "
                 f"(R² {fmt(round(float(cv['completo']), 2) + 0.0, 2)} contra {fmt(round(float(cv['media']), 2) + 0.0, 2)}).</p>")
    return (f'<div class="resultado" id="eje"><p>{linea}</p>{barra_eje(eje)}'
            f'<p class="nota">Escala en grados desde el norte (0 a 180: un eje no tiene sentido). Barra: IC 95% por bootstrap; '
            f'punto: estimación. n = {fmt(eje["n"])} eventos.</p>{costo}</div>')


def render(data: dict, out: Path) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (TEMPLATE.read_text()
            .replace("<!--__TITULARES__-->", titulares(data))
            .replace("<!--__EJE__-->", bloque_eje(data))
            .replace("/*__CHARTJS__*/", CHARTJS.read_text())
            .replace("/*__DATA__*/null", payload))
    out.write_text(html)


def main() -> int:
    con = duckdb.connect(str(DATA / "warehouse.duckdb"), read_only=True)
    out = ROOT / "site" / "index.html"
    render(collect(con), out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
