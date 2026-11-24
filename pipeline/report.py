"""Render the static dashboard (site/index.html) from the warehouse marts.

  uv run python -m pipeline.report                                   # data/warehouse.duckdb -> site/index.html
  uv run python -m pipeline.report --db X.duckdb --out DIR --banner  # pagina de la muestra: DIR/index.html con aviso MUESTRA
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline.ingest import DATA, ROOT
from pipeline.robustez import SHMAX
from pipeline.sistema import sistema_css

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
    eje["shmax"] = SHMAX
    eje["cortes"] = None
    if tabla_existe(con, "mart_robustez_eje"):
        eje["cortes"] = rows(con, """
            select count(*) as total,
                   count(*) filter (where ancho_ic >= 90 or p_perm >= 0.10) as sin_evidencia
            from mart_robustez_eje where grupo <> 'completa'""")[0]
    return eje


def regla_parada_cumplida(con) -> bool:
    """True si mart_eje_parada (pipeline.eje_parada) dice que alguna pata de la regla de parada del eje disparó."""
    if not tabla_existe(con, "mart_eje_parada"):
        return False
    return bool(con.execute("select count(*) from mart_eje_parada where dispara").fetchone()[0])


def costo_cv(con) -> dict | None:
    """R2 fuera de muestra del modelo de costo y de la media del área (mart_costo_cv, modelos 'modelo' y
    'media_area': la misma referencia que nombran el README y docs/caso-interferencia.md), o None si el mart no existe."""
    if not tabla_existe(con, "mart_costo_cv"):
        return None
    cols = [r[0] for r in con.execute("describe mart_costo_cv").fetchall()]
    if "modelo" not in cols or "r2" not in cols:
        return None
    dato = {r["modelo"]: r["r2"] for r in rows(con, "select modelo, r2 from mart_costo_cv "
                                                     "where modelo in ('modelo', 'media_area')")}
    if dato.keys() != {"modelo", "media_area"} or None in dato.values():
        return None
    return {"completo": dato["modelo"], "media": dato["media_area"]}


def brecha_neta(con) -> float | None:
    """Brecha del mes 1 menos la del mes -1 en la base limpia (mart_placebo_pretrend): lo que queda al descontar la
    brecha previa a la fractura. Misma cantidad que el 19 del README (claims.py, brecha_descontada@readme)."""
    if not tabla_existe(con, "mart_placebo_pretrend"):
        return None
    b = dict(con.execute("select k, brecha from mart_placebo_pretrend where k in (-1, 1)").fetchall())
    return b[1] - b[-1] if 1 in b and -1 in b else None


def diferido_rango(con) -> tuple[float, float] | None:
    """(cota inferior, cota superior) del diferido de los meses 0 a 6 en barriles (mart_diferido_rango): sin duplicar y
    descontando la brecha previa, y el total original. None si el mart no existe (la muestra no lo corre)."""
    if not tabla_existe(con, "mart_diferido_rango"):
        return None
    d = dict(con.execute("select variante, diferido_bbl from mart_diferido_rango").fetchall())
    return (d["neto_previa"], d["original"]) if {"neto_previa", "original"} <= d.keys() else None


def pretrend(con) -> list[dict]:
    """Brecha cercano menos control por mes relativo (k de -3 a 3) con su IC 95% por bootstrap, en la base limpia
    (mart_placebo_pretrend). Vacío si el mart no existe."""
    if not tabla_existe(con, "mart_placebo_pretrend"):
        return []
    return rows(con, "select k, n_near, brecha, ic_bajo, ic_alto from mart_placebo_pretrend order by k")


def prueba_anual(con) -> dict | None:
    """Prueba de la subida de 2026 con la misma antigüedad de carga en todos los años (mart_carga_anual_prueba, estadístico
    de 2026): D, su IC 95% por bloques de 5 km y el veredicto de la regla fijada antes de correr (pipeline.carga_anual).
    None si el mart no existe o la prueba no tiene cifra."""
    if not tabla_existe(con, "mart_carga_anual_prueba"):
        return None
    r = rows(con, "select d, ic_bajo, ic_alto, veredicto from mart_carga_anual_prueba where estadistico = '2026'")
    if not r or any(r[0][c] is None or r[0][c] != r[0][c] for c in ("d", "ic_bajo", "ic_alto")):
        return None
    return r[0]


def collect(con, dq_path: Path | None = None) -> dict:
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
        "anual": rows(con, "select anio, eventos_cercanos, brecha_mes_1 as brecha from mart_interferencia_anual "
                           "where anio >= 2016 and eventos_cercanos >= 30 order by anio"),
        "resumen": rows(con, """
            select (select count(*) from mart_interferencia_diferida) as eventos,
                   (select sum(petroleo_diferido_bbl) from mart_interferencia_diferida) as diferido_bbl,
                   (select sum(petroleo_diferido_bbl) from mart_interferencia_diferida where operador = 'YPF') as diferido_ypf_bbl,
                   (select count(*) from mart_interferencia_diferida where operador = 'YPF') as eventos_ypf,
                   (select median(indice) filter (where banda = 'cercano') - median(indice) filter (where banda = 'control')
                      from int_interferencia_mes where k = 1) as brecha_mes_1,
                   (select median(indice) filter (where banda = 'cercano') - median(indice) filter (where banda = 'control')
                      from int_interferencia_mes where k = 6) as brecha_mes_6""")[0],
    }
    interf["resumen"]["brecha_mes_1_neta"] = brecha_neta(con)
    interf["resumen"]["diferido_rango"] = diferido_rango(con)
    interf["pretrend"] = pretrend(con)
    interf["prueba_anual"] = prueba_anual(con)
    evals = {}
    for split in ("dev", "holdout"):
        f = ROOT / "agente" / "eval" / "resultados" / f"{split}.json"
        if f.exists():
            r = json.loads(f.read_text())
            evals[split] = {k: r[k] for k in ("n", "exactitud", "modelo", "datos_a")}
    dq = json.loads((dq_path or DATA / "dq_report.json").read_text())
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
        "eje_parada": regla_parada_cumplida(con),
        "costo_cv": costo_cv(con),
        "dq": {k: dq[k] for k in ("filas_origen_produccion", "bloqueantes_fallidos", "checks", "fuentes")},
    }


def fmt(n: float, d: int = 0) -> str:
    """Formato es-AR: punto de miles, coma decimal."""
    return f"{n:,.{d}f}".translate({ord(","): ".", ord("."): ","})


DIFERIDO_RANGO = "contra control de la misma edad; sin duplicar y descontando la brecha previa hasta el total original"
DIFERIDO_COTA = "contra control de la misma edad; cota superior"


def diferido_texto(r: dict, prefijo: str = "de") -> str:
    """El diferido de los meses 0 a 6 en millones de barriles: 'de A a B' (o 'entre A y B') si hay rango, el total si no."""
    rango = r.get("diferido_rango")
    if not rango:
        return fmt((r["diferido_bbl"] or 0) / 1e6, 1)
    a, b = fmt(rango[0] / 1e6, 1), fmt(rango[1] / 1e6, 1)
    return f"entre {a} y {b}" if prefijo == "entre" else f"de {a} a {b}"


def titulares(data: dict) -> str:
    """Bloque de cifras grandes, en HTML estático (se lee sin JavaScript)."""
    k, r, dq = data["kpi"], data["interferencia"]["resumen"], data["dq"]
    interanual = (k["pet"] / k["pet_anio_previo"] - 1) * 100
    celdas = [
        (fmt(k["pet"]), "kbbl/d de petróleo", f"{data['ultimo_mes']}, {'+' if interanual >= 0 else '-'}{fmt(abs(interanual), 1)}% interanual"),
        (fmt(k["ypf"] / k["pet"] * 100, 1) + "%", "participación de YPF", f"{fmt(k['ypf'])} kbbl/d"),
        (fmt(r["eventos"]), "eventos con padre a menos de 1 km", "fracturas de un pozo nuevo junto a uno en producción"),
        (diferido_texto(r) + " M", "bbl diferidos, meses 0 a 6", DIFERIDO_RANGO if r.get("diferido_rango") else DIFERIDO_COTA),
        (fmt(len(dq["checks"])), "controles de datos", f"{fmt(dq['bloqueantes_fallidos'])} bloqueantes fallidos"),
    ]
    items = "".join(f'<li><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></li>'
                    for v, l, d in celdas)
    return f'<ul class="titulares" aria-label="Cifras principales">{items}</ul>'


def pts(indice, signo: int = 1) -> str:
    """Brecha de un índice (fracción) en puntos, con el formato de todo el tablero; s/d si falta. signo -1 la muestra como pérdida."""
    return "s/d" if indice is None else fmt(signo * indice * 100)


def kpis_interferencia(data: dict) -> str:
    """KPI de la sección de interferencia, en HTML estático. El diferido, con sus tres bases, se explica aparte
    (`diferido_cuenta`)."""
    r = data["interferencia"]["resumen"]
    bruta, neta = r["brecha_mes_1"], r["brecha_mes_1_neta"]
    rango = f"{pts(neta)} a {pts(bruta)}" if neta is not None else pts(bruta)
    detalle = ("padre cercano contra control; el primero descuenta la brecha previa a la fractura, el segundo es la brecha bruta"
               if neta is not None else "padre cercano contra control")
    celdas = [
        (rango, "puntos al mes 1", detalle),
        (pts(r["brecha_mes_6"]), "puntos al mes 6", "la brecha casi se cierra"),
    ]
    items = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div><div class="d">{d}</div></div>'
                    for v, l, d in celdas)
    return f'<div class="kpis" id="kpis-interf">{items}</div>'


GLOSARIO = (
    '<details class="glosario" id="glosario"><summary>Glosario</summary><dl>'
    '<dt>Padre</dt><dd>Pozo que ya producía cuando se fractura uno nuevo a su lado (en inglés, parent).</dd>'
    '<dt>Hijo</dt><dd>El pozo nuevo que se fractura junto a uno en producción (en inglés, child).</dd>'
    '<dt>Golpe de fractura</dt><dd>Caída de la producción de un pozo vecino mientras se fractura el nuevo (en inglés, frac hit).</dd>'
    '<dt>Puntos</dt><dd>Puntos porcentuales del caudal previo del padre: pasar de 100 a 80 es una caída de 20 puntos.</dd>'
    '<dt>Diferido</dt><dd>Producción que se atrasa y no se pierde: el pozo la entrega más tarde.</dd>'
    '<dt>Pad</dt><dd>Plataforma de superficie desde la que se perforan varios pozos.</dd>'
    '<dt>Pozo de control</dt><dd>Pozo que produce a 2 a 5 km de un pozo hijo; sirve de comparación.</dd>'
    '<dt>Brecha</dt><dd>El caudal de los padres menos el de los pozos de control, en puntos.</dd>'
    '<dt>Huella medida</dt><dd>Una diferencia medida contra un control; no prueba una causa.</dd>'
    '<dt>Cierre preventivo</dt><dd>El operador frena el pozo padre antes de la fractura para protegerlo; en el dato mensual se ve igual que un daño por interferencia.</dd>'
    '<dt>Intervalo de 95%</dt><dd>El rango en el que cae la cifra con 95% de confianza. Si incluye el cero, el dato no la distingue de cero.</dd>'
    '<dt>Cota superior</dt><dd>El valor más alto que permite el dato; el efecto real puede ser menor.</dd>'
    '</dl></details>')


def leyenda_anual(data: dict) -> str:
    """Pie del gráfico por año: qué es n y, si el último año es el corriente, que va rayado."""
    anual = data["interferencia"]["anual"]
    en_curso = bool(anual) and str(anual[-1]["anio"]) == data["ultimo_mes"][:4]
    marca = (f'<span class="rayado">{anual[-1]["anio"]}: año en curso, con datos hasta {data["ultimo_mes"]}</span>'
             if en_curso else "")
    return f'<p class="leyenda-anual">Bajo cada año, n = eventos con padre a menos de 1 km. {marca}</p>'


def diferido_cuenta(data: dict) -> str:
    """Cómo se cuenta el diferido: por evento, por padre y en total de la cuenca. Son tres bases distintas; sin esta frase
    tres cifras parecen contradecirse. El diferido por operador va por evento, no como parte del total: YPF tiene la mayoría
    de los eventos, así que su parte del total no dice qué operador pierde más."""
    r = data["interferencia"]["resumen"]
    total, e_ypf = r["diferido_bbl"] or 0, r["eventos_ypf"] or 0
    e_otros = r["eventos"] - e_ypf
    por_ypf = (r["diferido_ypf_bbl"] or 0) / e_ypf if e_ypf else 0
    por_otros = (total - (r["diferido_ypf_bbl"] or 0)) / e_otros if e_otros else 0
    return ('<div class="diferido-cuenta" id="diferido-cuenta"><h3>Cómo se cuenta el diferido</h3><ul>'
            f'<li><strong>Por evento:</strong> en YPF, {fmt(por_ypf)} barriles por fractura ({fmt(e_ypf)} eventos); en los demás operadores, '
            f'{fmt(por_otros)} por fractura ({fmt(e_otros)} eventos). Es un promedio por fractura, no la parte de cada operador '
            'en el total: YPF tiene la mayoría de los eventos, y esa parte no dice qué operador pierde más.</li>'
            '<li><strong>Por padre:</strong> cada padre se cuenta una sola vez, aunque tenga varios eventos; la cifra de un padre típico '
            'está en <a href="informe.html">el informe</a>.</li>'
            '<li><strong>Total de la cuenca:</strong> el rango de arriba, de los meses 0 a 6.</li></ul></div>')


def lectura_anual(data: dict) -> str:
    """Frase sobre el perfil por año. La decide la prueba de pipeline.carga_anual: solo habla de una suba si el veredicto de la
    regla fijada antes de correr es "sostiene". Las fracturas se cargan con rezago, así que los últimos años están incompletos."""
    p = data["interferencia"].get("prueba_anual")
    if not p:
        return ("El perfil por año no se lee como tendencia: las fracturas se cargan con rezago y a los últimos años les "
                "faltan pozos hijos.")
    cifra = (f"{fmt(100 * p['d'], 1)} puntos (IC 95% por bloques de 5 km: {fmt(100 * p['ic_bajo'], 1)} a "
             f"{fmt(100 * p['ic_alto'], 1)})")
    if p["veredicto"] == "sostiene":
        return ("La brecha de 2026 es mayor que la de 2021 a 2024 también cuando todos los años se miran con la misma "
                f"antigüedad de carga de fracturas: la diferencia es de {cifra}.")
    return ("El perfil por año no se lee como tendencia: a los últimos años les faltan fracturas por cargar, y con la misma "
            f"antigüedad de carga en todos los años la diferencia entre 2026 y 2021 a 2024 es de {cifra}: {p['veredicto']}.")


def lectura_interferencia(data: dict) -> str:
    """Lo que la tabla del caso no dice sola: el perfil por año. El resultado del mes 1 y el diferido ya los cuenta la historia."""
    return f'<p class="finding" id="finding-interf">{lectura_anual(data)}</p>'


def lectura_diseno(data: dict) -> str:
    """Productividad por metro de rama de YPF entre la primera y la última cohorte de mart_diseno_productividad (las
    mismas cohortes que el README: 2017 y 2025)."""
    ypf = [d for d in data["diseno"] if d["grupo"] == "YPF"]
    if not ypf:
        return ""
    a, b = ypf[0], ypf[-1]
    return ('<p class="finding" id="finding"><strong>Lectura:</strong> la rama horizontal mediana de YPF pasó de '
            f'{fmt(a["rama_m_mediana"])} m (cohorte {a["cohorte"]}) a {fmt(b["rama_m_mediana"])} m (cohorte {b["cohorte"]}), '
            f'mientras el petróleo de 12 meses por metro bajó de {fmt(a["bbl_12m_por_m_mediana"])} bbl/m (cohorte {a["cohorte"]}) '
            f'a {fmt(b["bbl_12m_por_m_mediana"])} bbl/m (cohorte {b["cohorte"]}). '
            f'Los pozos producen más petróleo en total que en {a["cohorte"]}, pero cada metro de rama rinde menos. '
            'Es una correlación en datos públicos, no una causa: calidad de zona, espaciamiento y diseño de fractura son '
            'hipótesis a validar con datos internos.</p>')


PAGINA_PROSPECTIVA = ROOT / "wiki" / "hallazgos" / "prospectiva.md"


def estado_prospectiva(pagina: Path = PAGINA_PROSPECTIVA) -> dict | None:
    """Estado de la prueba prospectiva según su página (la escribe `pipeline.prospectiva`): {"estado": "pendiente"} o
    {"estado": "puntuado", "mes", "p1", "p2"} con los veredictos. None si la página no está o no se entiende."""
    if not pagina.exists():
        return None
    txt = pagina.read_text(encoding="utf-8")
    if "- **Pendiente.**" in txt:
        return {"estado": "pendiente"}
    mes = re.search(r"Puntuado con los datos hasta (\d{4}-\d{2})", txt)
    v1 = re.search(r"- \*\*P1, brecha del mes 1: ([^.*]+)\.\*\*", txt)
    v2 = re.search(r"- \*\*P2, cierre al mes 6: ([^.*]+)\.\*\*", txt)
    if not (mes and v1 and v2):
        return None
    return {"estado": "puntuado", "mes": mes.group(1), "p1": v1.group(1), "p2": v2.group(1)}


def prueba_abierta(est: dict | None) -> str:
    """El párrafo de la prueba prospectiva en 'Qué lo cambiaría'. El estado sale de la página de la prueba, no de un texto fijo:
    cuando se puntúe con muestra suficiente, la frase de 'hoy falta' cambia sola en vez de quedar equivocada."""
    base = ("Una prueba sigue abierta. El 2026-11-18, con datos hasta 2026-09, escribimos una predicción: una brecha de -22,9 "
            "puntos al mes 1 (rango -28,7 a -16,8) y el cierre al mes 6, en eventos cuyos meses siguientes todavía no estaban "
            "publicados. Cada publicación nueva la puntúa de nuevo. Para decidir hacen falta 100 eventos cercanos y 100 controles "
            "con el mes medido.")
    if est is None:
        return f"<p>{base}</p>"
    if est["estado"] == "pendiente":
        return f"<p>{base} Hoy falta.</p>"
    if est["p1"] == est["p2"] == "sin muestra":
        cierre = (f"Con los datos hasta {est['mes']} se puntuó y quedó sin muestra: los casos con el mes medido todavía "
                  "no llegan a los mínimos.")
    else:
        cierre = (f"Con los datos hasta {est['mes']} se puntuó: la brecha del mes 1 dio «{est['p1']}» y el cierre al mes 6, "
                  f"«{est['p2']}».")
    return f"<p>{base} {cierre}</p>"


PERFIL_ALTO = 24  # alto del escenario de las láminas con eje de tiempo, en puntos de brecha


def perfil_brecha(data: dict) -> tuple[str, str]:
    """La banda de la brecha con su borde superior dibujado mes a mes (meses -3 a 6, de `interferencia.curva`).

    Devuelve (área, línea) como atributos `d` de un `<path>` en el viewBox `0 0 100 PERFIL_ALTO`: x va de 0 (mes -3) a
    100 (mes 6), y del suelo (y = PERFIL_ALTO) sube un punto de brecha por unidad. Los meses con el padre por encima del
    control quedan en el suelo (horizonte cerrado). Las cifras van solo en atributos: el texto visible no cambia.

    Los meses -3 a -1 salen de `interferencia.pretrend` (mart_placebo_pretrend), los mismos que cita la lámina ("ya había
    una brecha de -2,5, -3,6 y -6,3 puntos"): la banda no puede mostrar un horizonte cerrado antes de la fractura cuando
    el texto dice que la brecha ya estaba. Sin ese mart, la curva.
    """
    curva = data["interferencia"]["curva"]
    por = {(r["banda"], r["k"]): r["indice"] for r in curva}
    previa = {r["k"]: r["brecha"] for r in data["interferencia"].get("pretrend") or [] if r["k"] < 0}
    ks = sorted({r["k"] for r in curva if -3 <= r["k"] <= 6})
    if not ks:
        return "M0 24 H100", "M0 24 H100"
    puntos = []
    for k in ks:
        cerca, ctrl = por.get(("cercano", k)), por.get(("control", k))
        if k in previa:
            alto = max(0.0, -previa[k] * 100)
        else:
            alto = max(0.0, (ctrl - cerca) * 100) if cerca is not None and ctrl is not None else 0.0
        puntos.append((round((k - ks[0]) / max(1, ks[-1] - ks[0]) * 100, 2), round(PERFIL_ALTO - min(alto, PERFIL_ALTO), 2)))
    borde = " ".join(f"L{x} {y}" for x, y in puntos)
    return f"M0 {PERFIL_ALTO} {borde} L100 {PERFIL_ALTO} Z", "M" + borde[1:]


BANNER_TITULO = "MUESTRA: no son las cifras de la cuenca"
BANNER_HTML = ('<aside class="muestra" role="note" style="border:3px solid #b45309;background:#fef3c7;color:#451a03;'
               'padding:14px 18px;margin:0 0 20px;border-radius:6px;font-size:16px">'
               f'<strong>{BANNER_TITULO}</strong><br>Esta página se generó con una muestra pequeña de los datos '
               '(unas pocas áreas, ver data/muestra/README.md). Sirve para ver el pipeline funcionando; '
               'las cifras de la cuenca están en la versión completa (make full).</aside>')


def render(data: dict, out: Path, banner: bool = False) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    area, linea = perfil_brecha(data)
    html = (TEMPLATE.read_text()
            .replace("__PERFIL_AREA__", area)
            .replace("__PERFIL_LINEA__", linea)
            .replace("<!--__TITULARES__-->", titulares(data))
            .replace("<!--__GLOSARIO__-->", GLOSARIO)
            .replace("<!--__LEYENDA_ANUAL__-->", leyenda_anual(data))
            .replace("<!--__KPIS_INTERF__-->", kpis_interferencia(data))
            .replace("<!--__FINDING_INTERF__-->", lectura_interferencia(data))
            .replace("<!--__DIFERIDO_CUENTA__-->", diferido_cuenta(data))
            .replace("<!--__PRUEBA_ABIERTA__-->", prueba_abierta(estado_prospectiva()))
            .replace("<!--__FINDING_DISENO__-->", lectura_diseno(data))
            .replace("/*__SISTEMA__*/", sistema_css())
            .replace("/*__CHARTJS__*/", CHARTJS.read_text())
            .replace("/*__DATA__*/null", payload))
    if banner:
        html = html.replace("<title>", "<title>MUESTRA - ", 1).replace("<body>", "<body>\n" + BANNER_HTML, 1)
    out.write_text(html)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.report", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DATA / "warehouse.duckdb", help="warehouse de entrada")
    ap.add_argument("--dq", type=Path, help="dq_report.json (por defecto data/dq_report.json, o el que va junto a --db)")
    ap.add_argument("--out", type=Path, default=ROOT / "site", help="directorio de salida (escribe index.html)")
    ap.add_argument("--banner", action="store_true", help="marca la página como MUESTRA")
    a = ap.parse_args(argv)
    dq = a.dq
    if dq is None and a.db != DATA / "warehouse.duckdb":
        dq = a.db.with_name(a.db.stem + "_dq_report.json")
    con = duckdb.connect(str(a.db), read_only=True)
    out = a.out / "index.html"
    render(collect(con, dq), out, banner=a.banner)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
