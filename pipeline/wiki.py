"""Genera un wiki estatico en espanol y un grafo del warehouse de Vaca Muerta.

Determinista: no usa modelos ni marcas de tiempo. La unica version de datos
que aparece en el wiki es la del manifiesto mas el ultimo mes con produccion.

Salidas dentro de ``out_dir``:

    index.md                  indice con enlaces a todas las paginas
    operador/<slug>.md        una pagina por operador shale con ubicacion
    area/<slug>.md            una pagina por area
    pad/<slug>.md             una pagina por pad con eventos cercanos
    hallazgos/interferencia.md pagina de hallazgos con historial acumulado
    hallazgos/anisotropia.md   eje de maxima merma por area y costo (si corrio pipeline.costo)
    hallazgos/robustez.md      estabilidad del eje y del costo en subconjuntos (si corrio pipeline.robustez)
    hallazgos/linaje.md        de que dataset crudo sale cada tabla (se arma leyendo pipeline/sql)
    hallazgos/validacion.md    otros resultados, eje por ano y prueba fuera de tiempo (si corrio pipeline.validacion)
    hallazgos/descomposicion.md  dias producidos contra caudal por dia y gradiente por distancia (si corrio pipeline.descomposicion)
    hallazgos/diferido.md      rango de barriles diferidos y cifra por evento (si corrio pipeline.diferido)
    hallazgos/sincronia.md     la brecha del mes 0 segun la fraccion del mes posterior al inicio de la fractura (si corrio pipeline.sincronia)
    hallazgos/placebo.md       pretendencia, fechas falsas y permutacion del estudio de eventos (si corrio pipeline.placebo)
    grafo.json                grafo de operadores, areas, pads y pozos
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

import duckdb

from pipeline import costo, descomposicion, diferido, linaje, mapa, placebo, robustez, sincronia, validacion
from pipeline import hallazgos as hz
from pipeline.ingest import DATA, ROOT, load_manifest

TOP_N = 5
DASHES = ("\u2014", "\u2013")
K_BRECHA = (0, 1, 2, 4, 6)
HIST_RE = re.compile(r"^-\s+datos a\s+(\S+)\s+\(sha produccion\s+([0-9a-fA-F]+)\):")


# --------------------------------------------------------------------------
# formato
# --------------------------------------------------------------------------
def slug(text) -> str:
    """minusculas, sin acentos, sin caracteres raros: 'Loma Campana' -> 'loma-campana'."""
    s = unicodedata.normalize("NFKD", str(text))
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def pad_slug(pad_id) -> str:
    """'p1234' -> 'pad-p1234'."""
    return "pad-" + slug(pad_id)


def num(value, decimals: int = 0) -> str:
    """Formato español: miles con punto y decimales con coma."""
    if value is None:
        return "s/d"
    txt = f"{float(value):,.{decimals}f}"
    return txt.replace(",", "\x01").replace(".", ",").replace("\x01", ".")


def ym(value) -> str:
    return "s/d" if value is None else f"{value.year:04d}-{value.month:02d}"


def ymd(value) -> str:
    return "s/d" if value is None else value.strftime("%Y-%m-%d")


def _disp(value) -> str:
    """Nombre limpio para mostrar (algunas areas traen espacios al final)."""
    return str(value).strip()


def _clean(text: str) -> str:
    """Garantiza que no haya rayas Unicode en el texto generado."""
    for dash in DASHES:
        if dash in text:
            raise ValueError(f"el texto generado no puede contener {dash!r}")
    return text


def _rows(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _scalar(con, sql):
    row = con.execute(sql).fetchall()
    return row[0][0] if row and row[0] else None


def _unique_slugs(names):
    """slug por nombre, con sufijo numerico ante colisiones."""
    out, used = {}, set()
    for name in sorted(set(str(n) for n in names)):
        base = slug(name) or "sin-nombre"
        cand, i = base, 2
        while cand in used:
            cand = f"{base}-{i}"
            i += 1
        used.add(cand)
        out[name] = cand
    return out


# --------------------------------------------------------------------------
# consultas
# --------------------------------------------------------------------------
def _collect(con):
    """Lee del warehouse todo lo que el wiki necesita."""
    data = {}
    data["ultimo"] = _scalar(con, "select mes from ultimo_mes")

    data["operadores"] = _rows(con, """
        select operador, count(*) as pozos, count(distinct area) as areas
        from int_pozo_ubicacion group by operador order by operador""")

    data["areas"] = _rows(con, """
        select area, count(*) as pozos, count(distinct pad_id) as pads,
               count(distinct operador) as operadores
        from int_pozo_ubicacion group by area order by area""")

    data["areas_operadores"] = _rows(con, """
        select area, operador, count(*) as pozos
        from int_pozo_ubicacion group by area, operador order by area, operador""")

    data["kpi_mes"] = _rows(con, """
        select operador, sum(petroleo_kbbl_d) as kbbl_d,
               sum(gas_mmm3_d) as gas_mmm3_d, sum(pozos_activos) as pozos_activos
        from mart_vm_mensual
        where mes = (select mes from ultimo_mes)
        group by operador order by operador""")

    data["dif_operador"] = _rows(con, """
        select operador, count(*) as eventos, sum(petroleo_diferido_bbl) as diferido
        from mart_interferencia_diferida group by operador order by operador""")

    data["dif_area"] = _rows(con, """
        select area, count(*) as eventos, sum(petroleo_diferido_bbl) as diferido
        from mart_interferencia_diferida group by area order by area""")

    data["dif_pad"] = _rows(con, """
        select pad_id, operador, area, count(*) as eventos,
               sum(petroleo_diferido_bbl) as diferido
        from mart_interferencia_diferida group by pad_id, operador, area
        order by pad_id""")

    data["eventos"] = _rows(con, """
        select padre, mes_frac, hijo_cercano, km_min, petroleo_diferido_bbl, operador, area, pad_id
        from mart_interferencia_diferida
        order by pad_id, mes_frac, padre""")

    data["brecha"] = _rows(con, f"""
        select grupo_edad, k, eventos_cercanos, indice_cercano, indice_control, brecha
        from mart_interferencia_brecha where k in ({", ".join(str(k) for k in K_BRECHA)})
        order by grupo_edad, k""")

    data["anual"] = _rows(con, """
        select anio, eventos_cercanos, brecha_mes_1
        from mart_interferencia_anual where anio >= 2016 order by anio""")

    data["pozos_pad"] = _rows(con, """
        select u.pad_id, u.pozo_id, u.operador, u.primer_mes_petroleo, d.sigla,
               f.rama_horizontal_m
        from int_pozo_ubicacion u
        left join dim_pozo d using (pozo_id)
        left join dim_fractura_pozo f using (pozo_id)
        where u.pad_id in (select distinct pad_id from mart_interferencia_diferida)
        order by u.pad_id, u.pozo_id""")

    data["siglas"] = {
        r["pozo_id"]: r["sigla"]
        for r in _rows(con, """
            select distinct d.pozo_id, d.sigla from dim_pozo d
            where d.pozo_id in (select padre from mart_interferencia_diferida)
               or d.pozo_id in (select hijo_cercano from mart_interferencia_diferida)""")
    }

    data["deferred_total"] = _scalar(
        con, "select sum(petroleo_diferido_bbl) from mart_interferencia_diferida")
    data["brecha_mes1"] = _brecha_mes1(con)
    return data


def _brecha_mes1(con):
    """Brecha del mes 1 con todas las edades: mediana cercanos menos mediana control."""
    val = None
    try:
        val = _scalar(con, """
            select median(indice) filter (where banda = 'cercano')
                 - median(indice) filter (where banda = 'control')
            from int_interferencia_mes where k = 1""")
    except duckdb.Error:
        val = None
    if val is None:
        val = _scalar(con, "select median(brecha) from mart_interferencia_brecha where k = 1")
    return val


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def _fuentes(tablas, manifest) -> str:
    lines = ["## Fuentes", ""]
    lines.append("Tablas consultadas: " + ", ".join(f"`{t}`" for t in tablas) + ".")
    lines.append("")
    for ds in ("produccion_no_convencional", "fractura_adjunto_iv"):
        ent = (manifest or {}).get(ds) or {}
        sha = str(ent.get("sha256") or "s/d")[:12]
        loaded = ent.get("loaded_at") or "s/d"
        lines.append(f"- {ds}: sha256 `{sha}`, cargado {loaded}.")
    return "\n".join(lines)


def _pagina_operador(nombre, wells, areas, kpi, ev, dif, top_pads, manifest, slug_o) -> str:
    L = [f"# {_disp(nombre)}", ""]
    L.append(f"Operador shale con ubicación en Vaca Muerta. Página `{slug_o}`.")
    L.append("")
    L.append("## Ficha")
    L.append("")
    L.append("| Indicador | Valor |")
    L.append("|---|---|")
    L.append(f"| Petróleo Vaca Muerta (kbbl/d, {ym(kpi['mes'])}) | {num(kpi['kbbl_d'], 2)} |")
    L.append(f"| Pozos shale con ubicación | {num(wells)} |")
    L.append(f"| Áreas operadas | {num(len(areas))} |")
    L.append(f"| Eventos cercanos de interferencia | {num(ev)} |")
    L.append(f"| Petróleo diferido (bbl) | {num(dif)} |")
    L.append("")
    L.append("## Areas operadas")
    L.append("")
    if areas:
        for a in areas:
            L.append(f"- [{_disp(a)}](../area/{slug(a)}.md)")
    else:
        L.append("Sin áreas registradas.")
    L.append("")
    L.append("## Top 5 pads por petroleo diferido")
    L.append("")
    if top_pads:
        L.append("| Pad | Área | Eventos cercanos | Petróleo diferido (bbl) |")
        L.append("|---|---|---|---|")
        for p in top_pads:
            L.append(f"| [{p['pad_id']}](../pad/{pad_slug(p['pad_id'])}.md) | {_disp(p['area'])} | "
                     f"{num(p['eventos'])} | {num(p['diferido'])} |")
    else:
        L.append("Sin eventos cercanos registrados.")
    L.append("")
    L.append(_fuentes(["int_pozo_ubicacion", "mart_vm_mensual", "mart_interferencia_diferida"], manifest))
    L.append("")
    return _clean("\n".join(L))


def _pagina_area(nombre, wells, pads, operadores, ev, dif, top_pads, manifest, slug_a) -> str:
    L = [f"# {_disp(nombre)}", ""]
    L.append("Área de permisos de shale con ubicación en Vaca Muerta.")
    L.append("")
    L.append("## Ficha")
    L.append("")
    L.append("| Indicador | Valor |")
    L.append("|---|---|")
    L.append(f"| Operadores | {num(len(operadores))} |")
    L.append(f"| Pozos shale con ubicación | {num(wells)} |")
    L.append(f"| Pads | {num(pads)} |")
    L.append(f"| Eventos cercanos de interferencia | {num(ev)} |")
    L.append(f"| Petróleo diferido (bbl) | {num(dif)} |")
    L.append("")
    L.append("## Operadores")
    L.append("")
    if operadores:
        for o in operadores:
            L.append(f"- [{_disp(o)}](../operador/{slug(o)}.md)")
    else:
        L.append("Sin operadores registrados.")
    L.append("")
    L.append("## Top 5 pads por petroleo diferido")
    L.append("")
    if top_pads:
        L.append("| Pad | Operador | Eventos cercanos | Petróleo diferido (bbl) |")
        L.append("|---|---|---|---|")
        for p in top_pads:
            L.append(f"| [{p['pad_id']}](../pad/{pad_slug(p['pad_id'])}.md) | {_disp(p['operador'])} | "
                     f"{num(p['eventos'])} | {num(p['diferido'])} |")
    else:
        L.append("Sin eventos cercanos registrados.")
    L.append("")
    L.append(_fuentes(["int_pozo_ubicacion", "mart_interferencia_diferida"], manifest))
    L.append("")
    return _clean("\n".join(L))


def _pagina_pad(pad_id, pozos, eventos, areas, operadores, manifest) -> str:
    L = [f"# Pad {_disp(pad_id)}", ""]
    L.append(f"Pad con eventos cercanos de interferencia. Identificador del pad: `{pad_id}`.")
    L.append("")
    L.append("## Ficha")
    L.append("")
    L.append("| Indicador | Valor |")
    L.append("|---|---|")
    L.append(f"| Pozos en el pad | {num(len(pozos))} |")
    L.append(f"| Eventos cercanos | {num(len(eventos))} |")
    L.append(f"| Petróleo diferido (bbl) | {num(sum(e['petroleo_diferido_bbl'] or 0 for e in eventos))} |")
    L.append("")
    L.append("## Ubicacion")
    L.append("")
    if areas:
        for a in areas:
            L.append(f"- Área: [{_disp(a)}](../area/{slug(a)}.md)")
    else:
        L.append("- Area: sin area registrada.")
    for o in operadores:
        L.append(f"- Operador: [{_disp(o)}](../operador/{slug(o)}.md)")
    L.append("")
    L.append("## Pozos")
    L.append("")
    if pozos:
        L.append("| Pozo | Sigla | Operador | Primer mes de petróleo | Rama horizontal (m) |")
        L.append("|---|---|---|---|---|")
        for p in pozos:
            L.append(f"| {p['pozo_id']} | {p['sigla'] or p['pozo_id']} | {_disp(p['operador'])} | "
                     f"{ym(p['primer_mes_petroleo'])} | {num(p['rama_horizontal_m'])} |")
    else:
        L.append("Sin pozos con ubicación en este pad.")
    L.append("")
    L.append("## Eventos cercanos")
    L.append("")
    if eventos:
        L.append("| Mes | Padre | Hijo más cercano | km | Petróleo diferido (bbl) |")
        L.append("|---|---|---|---|---|")
        for e in eventos:
            padre = e["siglas"].get(e["padre"]) or e["padre"]
            hijo = e["siglas"].get(e["hijo_cercano"]) or e["hijo_cercano"]
            L.append(f"| {ym(e['mes_frac'])} | {padre} | {hijo} | {num(e['km_min'], 3)} | "
                     f"{num(e['petroleo_diferido_bbl'])} |")
    else:
        L.append("Sin eventos cercanos registrados.")
    L.append("")
    L.append(_fuentes(["int_pozo_ubicacion", "dim_pozo", "dim_fractura_pozo",
                        "mart_interferencia_diferida"], manifest))
    L.append("")
    return _clean("\n".join(L))


def _pagina_hallazgos(data, manifest, historial, sha_prod, version) -> str:
    L = ["# Interferencia entre fracturas en Vaca Muerta", ""]
    L.append("Huella medida de la interferencia: cuánto petróleo dejan de producir los pozos "
             "padre cuando se fractura un pozo hijo cercano, frente a pozos control de la misma edad.")
    L.append("")
    L.append("## Brecha por grupo de edad")
    L.append("")
    L.append("Índice de tasa mensual del pozo padre alrededor del mes de fractura del hijo "
             "(mes 0), menos el índice de los pozos control. Valores negativos indican "
             "producción por debajo del control.")
    L.append("")
    L.append("| Grupo de edad | k | Eventos cercanos | Índice cercano | Índice control | Brecha |")
    L.append("|---|---|---|---|---|---|")
    for r in data["brecha"]:
        L.append(f"| {r['grupo_edad']} | {r['k']} | {num(r['eventos_cercanos'])} | "
                 f"{num(r['indice_cercano'], 3)} | {num(r['indice_control'], 3)} | {num(r['brecha'], 3)} |")
    L.append("")
    L.append("## Huella por año")
    L.append("")
    L.append("| Año | Eventos cercanos | Brecha mes 1 |")
    L.append("|---|---|---|")
    for r in data["anual"]:
        L.append(f"| {r['anio']} | {num(r['eventos_cercanos'])} | {num(r['brecha_mes_1'], 3)} |")
    L.append("")
    L.append("## Petróleo diferido")
    L.append("")
    L.append(f"Petróleo diferido total (meses 0 a 6 desde la fractura, eventos cercanos): "
             f"{num(data['deferred_total'])} bbl.")
    L.append("")
    L.append("| Operador | Eventos cercanos | Petróleo diferido (bbl) |")
    L.append("|---|---|---|")
    for r in data["top_operadores"]:
        L.append(f"| [{_disp(r['operador'])}](../operador/{slug(r['operador'])}.md) | {num(r['eventos'])} | "
                 f"{num(r['diferido'])} |")
    L.append("")
    L.append("## Límites")
    L.append("")
    L.append("Coordenadas de superficie (pads), no trayectoria de la rama. Un cierre o ahogo "
             "preventivo del operador se ve igual que un daño en datos mensuales. Es una huella "
             "medida, no una causa.")
    L.append("")
    L.append("## Historial")
    L.append("")
    for line in historial:
        L.append(line)
    L.append("")
    L.append(_fuentes(["mart_interferencia_brecha", "mart_interferencia_anual",
                        "mart_interferencia_diferida", "int_interferencia_mes"], manifest))
    L.append("")
    return _clean("\n".join(L))


# --------------------------------------------------------------------------
# construccion
# --------------------------------------------------------------------------
def _historial_previo(path: Path):
    """Lee las lineas de historial ya escritas y las devuelve con su sha."""
    lineas = []
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = HIST_RE.match(raw.strip())
            if m:
                lineas.append((m.group(2).lower(), raw.strip()))
    return lineas


def build_wiki(con, manifest, out_dir) -> dict:
    out_dir = Path(out_dir)
    manifest = manifest or {}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hallazgos").mkdir(parents=True, exist_ok=True)

    data = _collect(con)
    data["top_operadores"] = sorted(
        [r for r in data["dif_operador"]],
        key=lambda r: (-(r["diferido"] or 0), r["operador"]))[:TOP_N]

    # historial compuesto: se leen las lineas previas antes de regenerar
    hist_path = out_dir / "hallazgos" / "interferencia.md"
    previas = _historial_previo(hist_path)
    sha_prod = str((manifest.get("produccion_no_convencional") or {}).get("sha256") or "s/d")[:12]
    version = ym(data["ultimo"])
    ya = {sha for sha, _ in previas}
    linea = (f"- datos a {version} (sha produccion {sha_prod}): brecha mes 1 (todas las edades, "
             f"mediana de eventos cercanos menos control) = {num(data['brecha_mes1'], 3)}; "
             f"petróleo diferido total = {num(data['deferred_total'])} bbl")
    historial = [l for _, l in previas]
    if sha_prod.lower() not in ya:
        historial.append(linea)

    # las paginas de datos se regeneran enteras
    for sub in ("operador", "area", "pad"):
        d = out_dir / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    kpi_por_op = {r["operador"]: r for r in data["kpi_mes"]}
    dif_por_op = {r["operador"]: r for r in data["dif_operador"]}
    dif_por_area = {r["area"]: r for r in data["dif_area"]}

    # indices: un renglon por (pad, operador) y por pad
    pads = {}
    for r in data["dif_pad"]:
        clave = (r["pad_id"], r["operador"])
        agg = pads.setdefault(clave, {"pad_id": r["pad_id"], "operador": r["operador"],
                                      "area": r["area"], "eventos": 0, "diferido": 0.0})
        agg["eventos"] += r["eventos"] or 0
        agg["diferido"] += r["diferido"] or 0.0

    pads_por_op, pads_por_area, pads_por_pad = {}, {}, {}
    for (pad_id, operador), agg in pads.items():
        pads_por_op.setdefault(operador, []).append(agg)
        pads_por_area.setdefault(agg["area"], []).append(agg)
        pinfo = pads_por_pad.setdefault(pad_id, {"pad_id": pad_id, "areas": set(),
                                                 "operadores": set(), "eventos": 0, "diferido": 0.0})
        pinfo["areas"].add(agg["area"])
        pinfo["operadores"].add(operador)
        pinfo["eventos"] += agg["eventos"]
        pinfo["diferido"] += agg["diferido"]
    for d in (pads_por_op, pads_por_area):
        for k in d:
            d[k].sort(key=lambda r: (-(r["diferido"] or 0), r["pad_id"]))

    areas_por_op = {}
    for r in data["areas_operadores"]:
        areas_por_op.setdefault(r["operador"], []).append(r["area"])
    ops_por_area = {}
    for r in data["areas_operadores"]:
        ops_por_area.setdefault(r["area"], []).append(r["operador"])

    paginas = 0

    # paginas de operador
    for r in data["operadores"]:
        op = r["operador"]
        kpi = dict(kpi_por_op.get(op) or {})
        kpi.setdefault("kbbl_d", None)
        kpi.setdefault("gas_mmm3_d", None)
        kpi.setdefault("pozos_activos", None)
        kpi["mes"] = data["ultimo"]
        ev = (dif_por_op.get(op) or {}).get("eventos", 0)
        dif = (dif_por_op.get(op) or {}).get("diferido")
        texto = _pagina_operador(
            op, r["pozos"], sorted(areas_por_op.get(op, [])), kpi, ev, dif,
            pads_por_op.get(op, [])[:TOP_N], manifest, slug(op))
        (out_dir / "operador" / f"{slug(op)}.md").write_text(texto, encoding="utf-8")
        paginas += 1

    # paginas de area
    for r in data["areas"]:
        ar = r["area"]
        ev = (dif_por_area.get(ar) or {}).get("eventos", 0)
        dif = (dif_por_area.get(ar) or {}).get("diferido")
        texto = _pagina_area(
            ar, r["pozos"], r["pads"], sorted(ops_por_area.get(ar, [])), ev, dif,
            pads_por_area.get(ar, [])[:TOP_N], manifest, slug(ar))
        (out_dir / "area" / f"{slug(ar)}.md").write_text(texto, encoding="utf-8")
        paginas += 1

    # paginas de pad
    pozos_por_pad = {}
    for p in data["pozos_pad"]:
        pozos_por_pad.setdefault(p["pad_id"], []).append(p)
    eventos_por_pad = {}
    for e in data["eventos"]:
        e = dict(e)
        e["siglas"] = data["siglas"]
        eventos_por_pad.setdefault(e["pad_id"], []).append(e)
    for pad_id, pinfo in sorted(pads_por_pad.items()):
        texto = _pagina_pad(
            pad_id, pozos_por_pad.get(pad_id, []), eventos_por_pad.get(pad_id, []),
            sorted(pinfo["areas"]), sorted(pinfo["operadores"]), manifest)
        (out_dir / "pad" / f"{pad_slug(pad_id)}.md").write_text(texto, encoding="utf-8")
        paginas += 1

    # pagina de hallazgos
    texto_h = _pagina_hallazgos(data, manifest, historial, sha_prod, version)
    hist_path.write_text(texto_h, encoding="utf-8")
    paginas += 1

    # libro de hallazgos (lee el ledger ya registrado)
    libro = hz.pagina_libro(hz.leer_ledger(out_dir / "hallazgos" / "ledger.csv"))
    (out_dir / "hallazgos" / "libro.md").write_text(_clean(libro), encoding="utf-8")
    paginas += 1

    # anisotropia y costo (necesita pipeline.costo corrido despues del build)
    hay_costo = con.execute("select count(*) from information_schema.tables where table_name = 'mart_anisotropia_area'"
                            ).fetchall()[0][0] > 0
    anis_path = out_dir / "hallazgos" / "anisotropia.md"
    if hay_costo:
        anis_path.write_text(_clean(costo.pagina_anisotropia(con)), encoding="utf-8")
        paginas += 1
        (out_dir / "hallazgos" / "anisotropia_mapa.svg").write_text(_clean(mapa.mapa_areas_svg(con)), encoding="utf-8")
    elif anis_path.exists():
        anis_path.unlink()
        (out_dir / "hallazgos" / "anisotropia_mapa.svg").unlink(missing_ok=True)

    # robustez del eje y del costo (necesita pipeline.robustez corrido despues de pipeline.costo)
    hay_robustez = con.execute("select count(*) from information_schema.tables where table_name = 'mart_robustez_eje'"
                               ).fetchall()[0][0] > 0
    rob_path = out_dir / "hallazgos" / "robustez.md"
    if hay_robustez:
        rob_path.write_text(_clean(robustez.pagina_robustez(con)), encoding="utf-8")
        paginas += 1
    elif rob_path.exists():
        rob_path.unlink()

    # linaje de datos (se arma del SQL y del codigo de los modulos, no del warehouse)
    (out_dir / "hallazgos" / "linaje.md").write_text(_clean(linaje.pagina_linaje()), encoding="utf-8")
    paginas += 1
    # validacion del eje (necesita pipeline.validacion corrido despues de pipeline.costo)
    hay_validacion = con.execute("select count(*) from information_schema.tables "
                                 "where table_name = 'mart_validacion_resultados'").fetchall()[0][0] > 0
    val_path = out_dir / "hallazgos" / "validacion.md"
    if hay_validacion:
        val_path.write_text(_clean(validacion.pagina_validacion(con)), encoding="utf-8")
        paginas += 1
    elif val_path.exists():
        val_path.unlink()

    # falsacion del estudio de eventos (necesita pipeline.placebo corrido despues de pipeline.costo)
    hay_placebo = con.execute("select count(*) from information_schema.tables "
                              "where table_name = 'mart_placebo_fechas'").fetchall()[0][0] > 0
    pla_path = out_dir / "hallazgos" / "placebo.md"
    if hay_placebo:
        pla_path.write_text(_clean(placebo.pagina_placebo(con)), encoding="utf-8")
        paginas += 1
    elif pla_path.exists():
        pla_path.unlink()

    # descomposicion de la brecha (necesita pipeline.descomposicion corrido despues de pipeline.placebo)
    hay_desc = con.execute("select count(*) from information_schema.tables "
                           "where table_name = 'mart_descomposicion_k'").fetchall()[0][0] > 0
    desc_path = out_dir / "hallazgos" / "descomposicion.md"
    if hay_desc:
        desc_path.write_text(_clean(descomposicion.pagina_descomposicion(con)), encoding="utf-8")
        paginas += 1
    elif desc_path.exists():
        desc_path.unlink()

    # barriles diferidos: rango y cifra por evento (necesita pipeline.diferido corrido despues de pipeline.descomposicion)
    hay_dif = con.execute("select count(*) from information_schema.tables "
                          "where table_name = 'mart_diferido_rango'").fetchall()[0][0] > 0
    dif_path = out_dir / "hallazgos" / "diferido.md"
    if hay_dif:
        dif_path.write_text(_clean(diferido.pagina_diferido(con)), encoding="utf-8")
        paginas += 1
    elif dif_path.exists():
        dif_path.unlink()

    # sincronia dentro del mes (necesita pipeline.sincronia corrido despues de pipeline.diferido)
    hay_sinc = con.execute("select count(*) from information_schema.tables "
                           "where table_name = 'mart_sincronia_pendiente'").fetchall()[0][0] > 0
    sinc_path = out_dir / "hallazgos" / "sincronia.md"
    if hay_sinc:
        sinc_path.write_text(_clean(sincronia.pagina_sincronia(con)), encoding="utf-8")
        paginas += 1
    elif sinc_path.exists():
        sinc_path.unlink()

    # indice
    grafo = _grafo(con, data)
    grafo_path = out_dir / "grafo.json"
    previo = None
    if grafo_path.exists():
        try:
            previo = json.loads(grafo_path.read_text(encoding="utf-8"))
        except ValueError:
            previo = None
    grafo["aristas"] = _bitemporal((previo or {}).get("aristas", []), grafo["aristas"],
                                   version, hz.sha_produccion(manifest))
    (out_dir / "grafo.json").write_text(
        json.dumps(grafo, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    L = ["# Vaca Muerta: wiki de datos", ""]
    L.append("Wiki generado desde el warehouse de producción no convencional y fracturas "
             "(Secretaría de Energía). Páginas deterministas, sin marcas de tiempo.")
    L.append("")
    L.append(f"- Datos a {version}.")
    L.append("- Hallazgos: [Interferencia entre fracturas](hallazgos/interferencia.md).")
    L.append("- Libro de hallazgos: [libro.md](hallazgos/libro.md).")
    if hay_costo:
        L.append("- Anisotropía de la interferencia y su costo: [anisotropia.md](hallazgos/anisotropia.md).")
    if hay_robustez:
        L.append("- Robustez del eje y del costo: [robustez.md](hallazgos/robustez.md).")
    L.append("- Linaje de datos, del CSV crudo a los marts: [linaje.md](hallazgos/linaje.md).")
    if hay_validacion:
        L.append("- Validación del eje con otros resultados, por año y fuera de tiempo: [validacion.md](hallazgos/validacion.md).")
    if hay_placebo:
        L.append("- Pruebas de falsación del estudio de eventos (pretendencia, fechas falsas, permutación): [placebo.md](hallazgos/placebo.md).")
    if hay_desc:
        L.append("- Descomposición de la brecha (días producidos contra caudal por día) y gradiente por distancia: [descomposicion.md](hallazgos/descomposicion.md).")
    if hay_dif:
        L.append("- Barriles diferidos como rango (sin duplicar y descontando la brecha previa) y cifra por evento: [diferido.md](hallazgos/diferido.md).")
    if hay_sinc:
        L.append("- Sincronía dentro del mes (la brecha del mes 0 según la fracción posterior al inicio de la fractura): [sincronia.md](hallazgos/sincronia.md).")
    L.append(f"- Grafo: [grafo.json](grafo.json) con {len(grafo['nodos'])} nodos y "
             f"{_vigentes(grafo['aristas'])} aristas vigentes.")
    L.append("")
    L.append("## Operadores")
    L.append("")
    for r in data["operadores"]:
        L.append(f"- [{_disp(r['operador'])}](operador/{slug(r['operador'])}.md)")
    L.append("")
    L.append("## Areas")
    L.append("")
    for r in data["areas"]:
        L.append(f"- [{_disp(r['area'])}](area/{slug(r['area'])}.md)")
    L.append("")
    L.append("## Pads con eventos cercanos")
    L.append("")
    for pad_id in sorted(pads_por_pad):
        L.append(f"- [{pad_id}](pad/{pad_slug(pad_id)}.md)")
    L.append("")
    L.append(_fuentes(["int_pozo_ubicacion", "mart_vm_mensual", "mart_interferencia_diferida",
                        "mart_interferencia_brecha", "mart_interferencia_anual"], manifest))
    L.append("")
    (out_dir / "index.md").write_text(_clean("\n".join(L)), encoding="utf-8")
    paginas += 1

    return {"paginas": paginas, "nodos": len(grafo["nodos"]), "aristas": _vigentes(grafo["aristas"])}


def _clave_arista(a) -> tuple:
    """Identidad de la relacion; los valores medidos (km, barriles) no forman parte."""
    return (a.get("origen"), a.get("destino"), a.get("tipo"), a.get("mes"))


BITEMPORAL = ("valido_desde", "valido_hasta", "registrado_en", "hash_datos", "actualizado_en")


def _vigentes(aristas) -> int:
    return sum(1 for a in aristas if not a.get("valido_hasta"))


def _bitemporal(previas, nuevas, version, sha) -> list[dict]:
    """Aristas estilo Graphiti: lo que deja de aparecer se invalida, no se borra.

    Una arista que sigue vigente conserva su registro original; si cambia un valor
    medido (km, barriles diferidos) se actualiza y queda ``actualizado_en``. Una que
    desaparece queda con ``valido_hasta`` = version actual. Las ya invalidadas se conservan.
    """
    vigentes = {}
    cerradas = []
    for a in previas:
        if a.get("valido_hasta"):
            cerradas.append(a)
        else:
            vigentes[_clave_arista(a)] = a
    out = []
    vistas = set()
    for a in nuevas:
        clave = _clave_arista(a)
        if clave in vistas:  # one edge per relation; the mart has one row per (padre, mes)
            continue
        vistas.add(clave)
        antes = vigentes.get(clave)
        if antes is not None:
            medidos = {k: v for k, v in a.items() if k not in BITEMPORAL}
            if any(antes.get(k) != v for k, v in medidos.items()):
                antes = dict(antes, **medidos, actualizado_en=version, hash_datos=sha)
            out.append(antes)
            continue
        a = dict(a)
        a["valido_desde"] = a.get("mes") if a["tipo"] == "interfiere" else None
        a["valido_hasta"] = None
        a["registrado_en"] = version
        a["hash_datos"] = sha
        out.append(a)
    for clave, a in vigentes.items():
        if clave not in vistas:
            a = dict(a)
            a["valido_hasta"] = version
            cerradas.append(a)
    return out + cerradas


def _grafo(con, data) -> dict:
    """Nodos y aristas del grafo de la wiki."""
    nodos, aristas = {}, []

    def nodo(nid, tipo, nombre, pagina=None):
        if nid not in nodos:
            nodos[nid] = {"id": nid, "tipo": tipo, "nombre": nombre, "pagina": pagina}
        return nid

    for r in data["operadores"]:
        nodo(f"operador:{slug(r['operador'])}", "operador", r["operador"],
             f"operador/{slug(r['operador'])}.md")
    for r in data["areas"]:
        nodo(f"area:{slug(r['area'])}", "area", r["area"], f"area/{slug(r['area'])}.md")
    for r in data["dif_pad"]:
        nodo(f"pad:{pad_slug(r['pad_id'])}", "pad", r["pad_id"],
             f"pad/{pad_slug(r['pad_id'])}.md")

    # pozo -> pad
    pozo_pad = {}
    for p in data["pozos_pad"]:
        pozo_pad[p["pozo_id"]] = p["pad_id"]
    eventos = data["eventos"]
    for e in eventos:
        for pid in (e["padre"], e["hijo_cercano"]):
            if pid not in pozo_pad:
                row = _rows(con, f"select pad_id from int_pozo_ubicacion where pozo_id = {int(pid)}")
                if row:
                    pozo_pad[pid] = row[0]["pad_id"]
    for e in eventos:
        for pid in (e["padre"], e["hijo_cercano"]):
            pad = pozo_pad.get(pid)
            if not pad:
                continue
            nombre = data["siglas"].get(pid) or str(pid)
            nodo(f"pozo:{pid}", "pozo", nombre, f"pad/{pad_slug(pad)}.md")

    # opera: operador -> area
    for r in data["areas_operadores"]:
        aristas.append({"origen": f"operador:{slug(r['operador'])}",
                        "destino": f"area:{slug(r['area'])}",
                        "tipo": "opera"})
    # contiene: area -> pad
    pares_pad = set()
    for r in data["dif_pad"]:
        pares_pad.add((r["area"], r["pad_id"]))
    for area, pad in pares_pad:
        aristas.append({"origen": f"area:{slug(area)}",
                        "destino": f"pad:{pad_slug(pad)}",
                        "tipo": "contiene"})
    # en_pad: pozo -> pad
    for e in eventos:
        for pid in (e["padre"], e["hijo_cercano"]):
            pad = pozo_pad.get(pid)
            if not pad:
                continue
            aristas.append({"origen": f"pozo:{pid}",
                            "destino": f"pad:{pad_slug(pad)}",
                            "tipo": "en_pad"})
    # interfiere: hijo -> padre
    for e in eventos:
        aristas.append({
            "origen": f"pozo:{e['hijo_cercano']}",
            "destino": f"pozo:{e['padre']}",
            "tipo": "interfiere",
            "mes": ym(e["mes_frac"]),
            "km": round(float(e["km_min"] or 0), 3),
            "petroleo_diferido_bbl": round(float(e["petroleo_diferido_bbl"] or 0)),
        })

    # deduplicar aristas identicas y ordenar de forma determinista
    vistas = set()
    unicas = []
    for a in aristas:
        clave = json.dumps(a, ensure_ascii=False, sort_keys=True)
        if clave in vistas:
            continue
        vistas.add(clave)
        unicas.append(a)
    unicas.sort(key=lambda a: (a["tipo"], a["origen"], a["destino"], json.dumps(a, ensure_ascii=False, sort_keys=True)))

    lista_nodos = sorted(nodos.values(), key=lambda n: (n["tipo"], n["id"]))
    return {"nodos": lista_nodos, "aristas": unicas}


def main() -> None:
    manifest = load_manifest()
    db = DATA / "warehouse.duckdb"
    con = duckdb.connect(str(db), read_only=True)
    try:
        filas = hz.evaluar(con, manifest)
        hz.registrar(filas, ROOT / "wiki" / "hallazgos" / "ledger.csv")
        stats = build_wiki(con, manifest, ROOT / "wiki")
    finally:
        con.close()
    print(json.dumps(stats, ensure_ascii=False))
    for aviso in hz.lint_wiki(ROOT / "wiki"):
        print(f"[aviso] {aviso}")


if __name__ == "__main__":
    main()
