"""Render the static dashboard (site/index.html) from the warehouse marts.

  uv run python -m pipeline.report                                   # data/warehouse.duckdb -> site/index.html
  uv run python -m pipeline.report --db X.duckdb --out DIR --banner  # pagina de la muestra: DIR/index.html con aviso MUESTRA
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline.ingest import DATA, ROOT
from pipeline.robustez import SHMAX

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
    """KPI de la sección de interferencia, en HTML estático. El diferido por operador va por evento, no como parte del
    total: YPF tiene la mayoría de los eventos, así que su parte del total no dice qué operador pierde más."""
    r = data["interferencia"]["resumen"]
    bruta, neta = r["brecha_mes_1"], r["brecha_mes_1_neta"]
    rango = f"{pts(neta)} a {pts(bruta)}" if neta is not None else pts(bruta)
    detalle = ("padre cercano contra control; el primero descuenta la brecha previa a la fractura, el segundo es la brecha bruta"
               if neta is not None else "padre cercano contra control")
    total, e_ypf = r["diferido_bbl"] or 0, r["eventos_ypf"] or 0
    e_otros = r["eventos"] - e_ypf
    por_ypf = (r["diferido_ypf_bbl"] or 0) / e_ypf if e_ypf else 0
    por_otros = (total - (r["diferido_ypf_bbl"] or 0)) / e_otros if e_otros else 0
    celdas = [
        (rango, "puntos al mes 1", detalle),
        (pts(r["brecha_mes_6"]), "puntos al mes 6", "la brecha casi se cierra"),
        (fmt(por_ypf), "bbl diferidos por evento en YPF",
         f"{fmt(e_ypf)} eventos; en los demás operadores {fmt(por_otros)} por evento ({fmt(e_otros)} eventos)"),
    ]
    items = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div><div class="d">{d}</div></div>'
                    for v, l, d in celdas)
    return f'<div class="kpis" id="kpis-interf">{items}</div>'


def hallazgo(data: dict) -> str:
    """El resultado de la página, en HTML estático: la frase del README (Resultado) con las cifras del warehouse."""
    r = data["interferencia"]["resumen"]
    bruta, neta = r["brecha_mes_1"], r["brecha_mes_1_neta"]
    brecha = f"{pts(bruta, -1)} puntos menos" if neta is None else f"entre {pts(neta, -1)} y {pts(bruta, -1)} puntos menos"
    return ('<div class="hallazgo" id="hallazgo">'
            '<p class="frase">Un mes después de fracturar un pozo nuevo, los pozos vecinos a menos de 1 km rinden '
            f'{brecha} que pozos de control de la misma edad a 2 a 5 km ({fmt(r["eventos"])} eventos).</p>'
            '<p class="apoyo">A los 6 meses la brecha casi se cierra: es producción diferida, no perdida.</p></div>')


NO_SE_MIDE = (
    '<aside class="limites" id="no-se-mide" aria-label="Qué no se mide">'
    '<h3>Qué no se mide</h3>'
    '<p class="nota-datos">Las posiciones son coordenadas de superficie y la producción es mensual.</p>'
    '<ul>'
    '<li><strong>Trayectorias de la rama y espaciamiento real:</strong> solo hay cabezas de pozo.</li>'
    '<li><strong>Zona de aterrizaje:</strong> no se sabe el nivel de cada pozo.</li>'
    '<li><strong>Presiones:</strong> no hay presión de fondo ni de reservorio.</li>'
    '<li><strong>Datos diarios:</strong> el golpe dura días y se ve promediado en el mes.</li>'
    '<li><strong>Cierres no declarados:</strong> un cierre preventivo se ve como un daño.</li>'
    '</ul></aside>')

GLOSARIO = (
    '<details class="glosario" id="glosario"><summary>Glosario</summary><dl>'
    '<dt>Padre</dt><dd>Pozo que ya producía cuando se fractura uno nuevo a su lado (en inglés, parent).</dd>'
    '<dt>Hijo</dt><dd>El pozo nuevo que se fractura junto a uno en producción (en inglés, child).</dd>'
    '<dt>Golpe de fractura</dt><dd>Caída de la producción de un pozo vecino mientras se fractura el nuevo (en inglés, frac hit).</dd>'
    '<dt>Puntos</dt><dd>Puntos porcentuales del caudal previo del padre: pasar de 100 a 80 es una caída de 20 puntos.</dd>'
    '<dt>Diferido</dt><dd>Producción que se atrasa y no se pierde: el pozo la entrega más tarde.</dd>'
    '<dt>Pad</dt><dd>Plataforma de superficie desde la que se perforan varios pozos.</dd>'
    '</dl></details>')


def leyenda_anual(data: dict) -> str:
    """Pie del gráfico por año: qué es n y, si el último año es el corriente, que va rayado."""
    anual = data["interferencia"]["anual"]
    en_curso = bool(anual) and str(anual[-1]["anio"]) == data["ultimo_mes"][:4]
    marca = (f'<span class="rayado">{anual[-1]["anio"]}: año en curso, con datos hasta {data["ultimo_mes"]}</span>'
             if en_curso else "")
    return f'<p class="leyenda-anual">Bajo cada año, n = eventos con padre a menos de 1 km. {marca}</p>'


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
    i = data["interferencia"]
    r = i["resumen"]
    return ('<p class="finding" id="finding-interf"><strong>Lectura:</strong> un mes después de fracturar un pozo nuevo, '
            f'los padres a menos de 1 km rinden {pts(r["brecha_mes_1"], -1)} puntos menos que los padres de control a 2-5 km; '
            f'a los 6 meses la brecha casi se cierra ({pts(r["brecha_mes_6"], -1)} puntos). '
            f'{lectura_anual(data)} '
            f'Contra un control de la misma edad, suma {diferido_texto(r, "entre")} millones de barriles diferidos '
            f'en los meses 0 a 6 ({"sin duplicar y descontando la brecha previa hasta el total original" if r.get("diferido_rango") else "cota superior"}).</p>')


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


def barra_eje(eje: dict) -> str:
    """Intervalo de confianza del eje sobre una escala de 0 a 180 grados (el eje es módulo 180), con el SHmax publicado."""
    def x(g):
        return 12 + g / 180 * 336
    lo, hi, pt = eje["ic_bajo"] % 180, eje["ic_alto"] % 180, eje["eje_grados"] % 180
    sh = eje.get("shmax")
    tramos = [(lo, hi)] if lo <= hi else [(lo, 180), (0, hi)]
    bandas = "".join(f'<rect class="ic" x="{x(a):.1f}" y="22" width="{x(b) - x(a):.1f}" height="10" rx="2"/>' for a, b in tramos)
    marcas = "".join(f'<line class="tick" x1="{x(g):.1f}" x2="{x(g):.1f}" y1="38" y2="43"/>'
                     f'<text x="{x(g):.1f}" y="56" text-anchor="middle">{g}</text>' for g in (0, 45, 90, 135, 180))
    desc = (f'Eje {fmt(eje["eje_grados"])} grados, intervalo de confianza de {fmt(eje["ic_bajo"])} '
            f'a {fmt(eje["ic_alto"])} grados sobre una escala de 0 a 180')
    marca_sh = ""
    if sh is not None:
        desc += f'; SHmax publicado en {fmt(sh, 1)} grados'
        marca_sh = (f'<line class="shmax" x1="{x(sh):.1f}" x2="{x(sh):.1f}" y1="14" y2="36"/>'
                    f'<text class="shmax-t" x="{x(sh):.1f}" y="10" text-anchor="middle">SHmax {fmt(sh, 1)}</text>')
    return (f'<svg class="eje-barra" viewBox="0 0 360 62" role="img" aria-label="{desc}"><title>{desc}</title>'
            f'<line class="base" x1="12" x2="348" y1="27" y2="27"/>{bandas}{marca_sh}'
            f'<circle class="pt" cx="{x(pt):.1f}" cy="27" r="5"/>{marcas}</svg>')


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
    if data.get("eje_parada"):
        linea += (" La regla de parada fijada antes de correr se cumplió: la dirección no se separa del SHmax publicado ni de la "
                  "forma en que se disponen los pads (la geometría de las ramas se probó con otra prueba, costado contra punta, en mecanismo.md), y no se presenta como hallazgo sobre esfuerzos ni sobre la fractura.")
    cv = data.get("costo_cv")
    costo = ""
    if cv:
        verbo = "no supera" if cv["completo"] <= cv["media"] else "supera"
        costo = (f"<p>El modelo de costo {verbo} a la media del área fuera de muestra "
                 f"(R² {fmt(round(float(cv['completo']), 2) + 0.0, 2)} contra {fmt(round(float(cv['media']), 2) + 0.0, 2)}).</p>")
    return (f'<div class="resultado" id="eje"><p>{linea}</p>{barra_eje(eje)}'
            f'<p class="nota">Escala en grados desde el norte (0 a 180: un eje no tiene sentido). Barra: IC 95% por bootstrap; '
            f'punto: estimación; línea punteada: SHmax publicado ({fmt(eje["shmax"], 1) if eje.get("shmax") is not None else "s/d"} grados). n = {fmt(eje["n"])} eventos.</p>{costo}</div>')


BANNER_TITULO = "MUESTRA: no son las cifras de la cuenca"
BANNER_HTML = ('<aside class="muestra" role="note" style="border:3px solid #b45309;background:#fef3c7;color:#451a03;'
               'padding:14px 18px;margin:0 0 20px;border-radius:6px;font-size:16px">'
               f'<strong>{BANNER_TITULO}</strong><br>Esta página se generó con una muestra pequeña de los datos '
               '(unas pocas áreas, ver data/muestra/README.md). Sirve para ver el pipeline funcionando; '
               'las cifras de la cuenca están en la versión completa (make full).</aside>')


def render(data: dict, out: Path, banner: bool = False) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (TEMPLATE.read_text()
            .replace("<!--__TITULARES__-->", titulares(data))
            .replace("<!--__HALLAZGO__-->", hallazgo(data))
            .replace("<!--__NO_SE_MIDE__-->", NO_SE_MIDE)
            .replace("<!--__GLOSARIO__-->", GLOSARIO)
            .replace("<!--__LEYENDA_ANUAL__-->", leyenda_anual(data))
            .replace("<!--__EJE__-->", bloque_eje(data))
            .replace("<!--__KPIS_INTERF__-->", kpis_interferencia(data))
            .replace("<!--__FINDING_INTERF__-->", lectura_interferencia(data))
            .replace("<!--__FINDING_DISENO__-->", lectura_diseno(data))
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
