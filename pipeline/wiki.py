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
    hallazgos/linaje.md        de que dataset crudo sale cada tabla (se arma leyendo pipeline/sql y el codigo de los modulos)
    hallazgos/validacion.md    otros resultados, eje por ano y prueba fuera de tiempo (si corrio pipeline.validacion)
    hallazgos/descomposicion.md  dias producidos contra caudal por dia y gradiente por distancia (si corrio pipeline.descomposicion)
    hallazgos/diferido.md      rango de barriles diferidos y cifra por evento (si corrio pipeline.diferido)
    hallazgos/sincronia.md     la brecha del mes 0 segun la fraccion del mes posterior al inicio de la fractura (si corrio pipeline.sincronia)
    hallazgos/dia_inicio.md    el dia del mes en que empieza la fractura como dosis, solo entre padres cercanos, con su veredicto (si corrio pipeline.dia_inicio)
    hallazgos/eje_parada.md    regla de parada del eje de merma; potencia.md, eje_controles.md y eje_exposicion.md son sus tres pruebas
    hallazgos/bloques.md       los intervalos principales con bootstrap por bloques espaciales de 2 y 5 km (si corrio pipeline.bloques)
    hallazgos/hijo.md          el rendimiento de 12 meses del hijo segun el petroleo ya producido a menos de 1 km (si corrio pipeline.hijo)
    hallazgos/inyeccion.md     efectos plantados contra efectos recuperados por los estimadores (si corrio pipeline.inyeccion)
    hallazgos/dosis.md          dosis y respuesta: la caida contra el trabajo del hijo y la deplecion (si corrio pipeline.dosis)
    hallazgos/dosis_meses.md    dosis y respuesta mes a mes: el caudal por dia en k = 1 a 4 (si corrio pipeline.dosis_meses)
    hallazgos/dosis_pad.md      dosis del pad y cercania: la caida contra la arena de todo el pad y la interaccion (si corrio pipeline.dosis_pad)
    hallazgos/anillo.md         la brecha del mes 1 y el cierre a 6 meses con cuatro controles (si corrio pipeline.anillo)
    hallazgos/decision_operador.md  brecha, diferido y valor por edad del padre y banda de distancia (si corrio pipeline.decision)
    hallazgos/potencia_dosis.md  potencia del nulo de dosis y respuesta (si corrio pipeline.potencia_dosis)
    hallazgos/robustez_operador.md  brecha del mes 1 y cierre del mes 6 sacando de a un operador y de a un area (si corrio pipeline.robustez_operador)
    hallazgos/dias_perdidos.md  dias de produccion que pierde un padre alrededor de la fractura de un hijo, por operador (si corrio pipeline.dias_perdidos)
    hallazgos/golpes_mismo_mes.md  si a un padre le cuesta menos recibir varios hijos en un mes que en meses separados (si corrio pipeline.golpes_mismo_mes)
    hallazgos/golpes_mismo_padre.md  lo mismo con cada padre como su propio control (si corrio pipeline.golpes_mismo_padre)
    hallazgos/calendario_golpes.md  matrices de costo, calendario optimo y backtest ajustado en 2023 (si corrio pipeline.calendario_golpes)
    hallazgos/trayectorias.md  trayectorias de pozo publicadas: cobertura y distancia entre ramas frente a la de superficie (si corrio pipeline.trayectorias)
    hallazgos/alcance_rama.md  alcance y dilucion de la huella medidos entre ramas, regla fijada de antemano (si corrio pipeline.alcance_rama)
    hallazgos/riesgo.md        riesgo de golpe fuerte con un modelo logistico probado hacia adelante, regla fijada de antemano (si corrio pipeline.riesgo)
    hallazgos/dosis_geometria.md  dosis con la geometria de las ramas, detras de una puerta de potencia (si corrio pipeline.dosis_geometria)
    hallazgos/hijo_celdas.md   el lado del hijo comparando hijos del mismo cuadrado de 2 km (si corrio pipeline.hijo_celdas)
    hallazgos/mecanismo.md      la geometria de las ramas: el padre al costado de la rama del hijo contra el de la punta (si corrio pipeline.mecanismo)
    hallazgos/causal_profundo.md volumen de agua y de petroleo debajo del corte de agua de D2 (si corrio pipeline.causal_profundo)
    hallazgos/causal.md         diseno causal: DiD escalonado con aun no tratados y el corte de agua, regla fijada de antemano (si corrio pipeline.causal)
    hallazgos/hijo_pad.md      el lado del hijo comparando hijos del mismo pad segun las ramas a menos de 600 m (si corrio pipeline.hijo_pad)
    hallazgos/gas.md           el padre gasifero con el gas como resultado (si corrio pipeline.gas)
    hallazgos/literatura.md    comparacion con la literatura (escrita a mano; el indice la enlaza si existe)
    hallazgos/prospectiva.md   prueba prospectiva congelada (la escribe pipeline.prospectiva; el indice la enlaza si existe)
    hallazgos/carga_fracturas.md  rezago de carga de las fracturas en el dato publico (la escribe pipeline.carga; el indice la enlaza si existe)
    hallazgos/carga_anual.md   la subida de 2026 con la misma antiguedad de carga (la escribe pipeline.carga_anual; el indice la enlaza si existe)
    hallazgos/replicacion.md   el estudio de eventos sobre Colorado (lo escribe pipeline.replicacion, solo con --with-colorado)
    hallazgos/replicacion_cuencas.md   la lectura de la familia de cuencas (la escribe pipeline.familia)
    hallazgos/placebo.md       pretendencia, fechas falsas y permutacion del estudio de eventos (si corrio pipeline.placebo)
    hallazgos/mapa_base.md     fuentes y licencias del mapa base de la pagina 3D (la escribe pipeline.base_mapa; el indice la enlaza si existe)
    grafo.json                grafo de operadores, areas, pads y pozos
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

import duckdb

from pipeline import alcance_rama, anillo, bloques, calendario_golpes, causal, causal_profundo, costo, decision, descomposicion, dias_perdidos, dia_inicio, diferido, dosis, dosis_geometria, golpes_mismo_mes, golpes_mismo_padre, dosis_meses, dosis_pad, eje_controles, eje_exposicion, eje_parada, gas, hijo_pad, potencia, potencia_dosis, hijo, hijo_celdas, inyeccion, linaje, mapa, mecanismo, placebo, riesgo, robustez, robustez_operador, sincronia, trayectorias, validacion
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
    """Brecha del mes 1 con todas las edades: mediana cercanos menos mediana control. None si falta una de las dos bandas."""
    return _scalar(con, """
        select median(indice) filter (where banda = 'cercano')
             - median(indice) filter (where banda = 'control')
        from int_interferencia_mes where k = 1""")


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
    L.append("Las fracturas se cargan con rezago, así que a los últimos años les faltan pozos hijos y la tabla no se lee como "
             "tendencia." + (" La comparación con la misma antigüedad de carga en todos los años está en "
                             "[carga_anual.md](carga_anual.md)." if data.get("hay_carga_anual") else ""))
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
    data["hay_carga_anual"] = (out_dir / "hallazgos" / "carga_anual.md").exists()   # la escribe pipeline.carga_anual
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
        anis = costo.pagina_anisotropia(con)
        aviso = eje_parada.aviso_anisotropia(con)
        if aviso:
            anis = anis.replace("## Eje de máxima merma", "\n".join(aviso) + "\n## Eje de máxima merma", 1)
        anis_path.write_text(_clean(anis), encoding="utf-8")
        paginas += 1
        (out_dir / "hallazgos" / "anisotropia_mapa.svg").write_text(_clean(mapa.mapa_areas_svg(con)), encoding="utf-8")
    elif anis_path.exists():
        anis_path.unlink()
        (out_dir / "hallazgos" / "anisotropia_mapa.svg").unlink(missing_ok=True)

    # paginas que dependen de un mart: una fila por pagina (bandera, mart, archivo, funcion), en el orden del indice;
    # sin mart (None) la pagina se escribe siempre
    hay = {}
    paginas_mart = [
        # robustez del eje y del costo (necesita pipeline.robustez corrido despues de pipeline.costo)
        ("robustez", "mart_robustez_eje", "robustez.md", robustez.pagina_robustez),
        # linaje de datos (se arma del SQL y del codigo de los modulos, no del warehouse)
        ("linaje", None, "linaje.md", lambda con: linaje.pagina_linaje()),
        # validacion del eje (necesita pipeline.validacion corrido despues de pipeline.costo)
        ("validacion", "mart_validacion_resultados", "validacion.md", validacion.pagina_validacion),
        # falsacion del estudio de eventos (necesita pipeline.placebo corrido despues de pipeline.costo)
        ("placebo", "mart_placebo_fechas", "placebo.md", placebo.pagina_placebo),
        # descomposicion de la brecha (necesita pipeline.descomposicion corrido despues de pipeline.placebo)
        ("desc", "mart_descomposicion_k", "descomposicion.md", descomposicion.pagina_descomposicion),
        # barriles diferidos: rango y cifra por evento (necesita pipeline.diferido corrido despues de pipeline.descomposicion)
        ("dif", "mart_diferido_rango", "diferido.md", diferido.pagina_diferido),
        # sincronia dentro del mes (necesita pipeline.sincronia corrido despues de pipeline.diferido)
        ("sinc", "mart_sincronia_pendiente", "sincronia.md", sincronia.pagina_sincronia),
        # el dia de inicio como dosis, solo entre padres cercanos (necesita pipeline.dia_inicio; no depende de los marts de sincronia)
        ("dia_inicio", "mart_dia_inicio_veredicto", "dia_inicio.md", dia_inicio.pagina_dia_inicio),
        # bloques espaciales (necesita pipeline.bloques corrido despues de pipeline.sincronia)
        ("bloq", "mart_bloques", "bloques.md", bloques.pagina_bloques),
        # lado del hijo (necesita pipeline.hijo corrido despues de pipeline.sincronia)
        ("hijo", "mart_hijo_coef", "hijo.md", hijo.pagina_hijo),
        # validacion por inyeccion (necesita pipeline.inyeccion corrido despues de pipeline.sincronia)
        ("iny", "mart_inyeccion", "inyeccion.md", inyeccion.pagina_inyeccion),
        # dosis y respuesta (necesita pipeline.dosis corrido despues de pipeline.descomposicion)
        ("dosis", "mart_dosis_veredicto", "dosis.md", dosis.pagina_dosis),
        # dosis mes a mes (necesita pipeline.dosis_meses corrido despues de pipeline.dosis)
        ("dosis_meses", "mart_dosis_meses_veredicto", "dosis_meses.md", dosis_meses.pagina_dosis_meses),
        # dosis del pad y cercania (necesita pipeline.dosis_pad corrido despues de pipeline.dosis)
        ("dosis_pad", "mart_dosis_pad_veredicto", "dosis_pad.md", dosis_pad.pagina_dosis_pad),
        # anillo de control (necesita pipeline.anillo corrido despues de pipeline.descomposicion)
        ("anillo", "mart_anillo_veredicto", "anillo.md", anillo.pagina_anillo),
        # capa de decision para un operador (necesita pipeline.decision corrido despues de pipeline.hijo)
        ("decision", "mart_decision_cierre", "decision_operador.md", decision.pagina_decision),
        # potencia del nulo de dosis (necesita pipeline.potencia_dosis corrido despues de pipeline.dosis_pad)
        ("potencia_dosis", "mart_potencia_dosis_veredicto", "potencia_dosis.md", potencia_dosis.pagina_potencia_dosis),
        # el padre en la ventana de gas (necesita pipeline.gas)
        ("gas", "mart_gas_veredicto", "gas.md", gas.pagina_gas),
        # lado del hijo dentro de celdas de 2 km (necesita pipeline.hijo_celdas)
        ("hijo_celdas", "mart_hijo_celdas_resumen", "hijo_celdas.md", hijo_celdas.pagina_hijo_celdas),
        # geometria de las ramas: el padre al costado de la rama del hijo contra el de la punta (necesita pipeline.mecanismo)
        ("mecanismo", "mart_mecanismo_veredicto", "mecanismo.md", mecanismo.pagina_mecanismo),
        # diseno causal: DiD escalonado con aun no tratados y corte de agua (necesita pipeline.causal)
        ("causal", "mart_causal_veredicto", "causal.md", causal.pagina_causal),
        # agua que entra o petroleo que sale, debajo del corte de agua de D2 (necesita pipeline.causal_profundo)
        ("causal_profundo", "mart_causal_profundo_veredicto", "causal_profundo.md", causal_profundo.pagina_causal_profundo),
        # robustez por operador y area (necesita pipeline.robustez_operador, que corre despues de pipeline.placebo)
        ("rob_op", "mart_robustez_operador_veredicto", "robustez_operador.md", robustez_operador.pagina_robustez_operador),
        # dias parados del padre por operador (necesita pipeline.dias_perdidos, que corre despues de pipeline.descomposicion)
        ("dias", "mart_dias_perdidos_prueba", "dias_perdidos.md", dias_perdidos.pagina_dias_perdidos),
        # golpes en el mismo mes: costo fijo del mes contra costo por hijo (necesita pipeline.golpes_mismo_mes, despues de dias_perdidos)
        ("golpes", "mart_golpes_mismo_mes_prueba", "golpes_mismo_mes.md", golpes_mismo_mes.pagina_golpes_mismo_mes),
        # golpes en el mismo mes con el padre como su propio control (necesita pipeline.golpes_mismo_padre, despues de golpes_mismo_mes)
        ("golpes_padre", "mart_golpes_mismo_padre_prueba", "golpes_mismo_padre.md", golpes_mismo_padre.pagina_golpes_mismo_padre),
        # calendario de golpes: matrices de costo, optimizador y backtest (necesita pipeline.calendario_golpes, despues de golpes_mismo_padre)
        ("calendario", "mart_calendario_prueba", "calendario_golpes.md", calendario_golpes.pagina_calendario_golpes),
        # trayectorias de pozo publicadas, cobertura y distancia entre ramas (necesita pipeline.trayectorias)
        ("tray", "mart_trayectoria_resumen", "trayectorias.md", trayectorias.pagina_trayectorias),
        # alcance y dilucion de la huella medidos entre ramas (necesita pipeline.alcance_rama, despues de trayectorias)
        ("alcance_rama", "mart_alcance_rama_prueba", "alcance_rama.md", alcance_rama.pagina_alcance_rama),
        # riesgo de golpe fuerte, modelo logistico probado hacia adelante (necesita pipeline.riesgo, despues de trayectorias)
        ("riesgo", "mart_riesgo_prueba", "riesgo.md", riesgo.pagina_riesgo),
        # dosis y respuesta con la geometria de las ramas, detras de una puerta de potencia (necesita pipeline.trayectorias y pipeline.potencia_dosis)
        ("dosis_geo", "mart_dosis_geometria_puerta", "dosis_geometria.md", dosis_geometria.pagina_dosis_geometria),
        # lado del hijo dentro del pad con la distancia entre ramas (necesita pipeline.hijo_pad, despues de trayectorias)
        ("hijo_pad", "mart_hijo_pad_coef", "hijo_pad.md", hijo_pad.pagina_hijo_pad),
    ]
    for flag, tabla, archivo, funcion in paginas_mart:
        hay[flag] = tabla is None or con.execute(
            "select count(*) from information_schema.tables where table_name = ?", [tabla]).fetchall()[0][0] > 0
        ruta = out_dir / "hallazgos" / archivo
        if hay[flag]:
            ruta.write_text(_clean(funcion(con)), encoding="utf-8")
            paginas += 1
        elif ruta.exists():
            ruta.unlink()
    hay_robustez = hay["robustez"]
    hay_validacion = hay["validacion"]
    hay_placebo = hay["placebo"]
    hay_desc = hay["desc"]
    hay_dif = hay["dif"]
    hay_sinc = hay["sinc"]
    hay_dia_inicio = hay["dia_inicio"]
    hay_bloq = hay["bloq"]
    hay_hijo = hay["hijo"]
    hay_iny = hay["iny"]
    hay_dosis = hay["dosis"]
    hay_dosis_meses = hay["dosis_meses"]
    hay_dosis_pad = hay["dosis_pad"]
    hay_anillo = hay["anillo"]
    hay_decision = hay["decision"]
    hay_potencia_dosis = hay["potencia_dosis"]
    hay_gas = hay["gas"]
    hay_hijo_celdas = hay["hijo_celdas"]
    hay_mecanismo = hay["mecanismo"]
    hay_causal = hay["causal"]
    hay_causal_profundo = hay["causal_profundo"]
    hay_rob_op = hay["rob_op"]
    hay_dias = hay["dias"]
    hay_tray = hay["tray"]
    hay_golpes = hay["golpes"]
    hay_golpes_padre = hay["golpes_padre"]
    hay_alcance_rama = hay["alcance_rama"]
    hay_calendario = hay["calendario"]
    hay_riesgo = hay["riesgo"]
    hay_dosis_geo = hay["dosis_geo"]
    hay_hijo_pad = hay["hijo_pad"]

    # regla de parada del eje: potencia, controles negativos y exposicion (necesitan pipeline.potencia, eje_controles y eje_exposicion)
    paginas_eje = [("mart_potencia_resumen", "potencia.md", potencia.pagina_potencia),
                   ("mart_eje_controles", "eje_controles.md", eje_controles.pagina_eje_controles),
                   ("mart_eje_exposicion", "eje_exposicion.md", eje_exposicion.pagina_eje_exposicion),
                   ("mart_eje_parada", "eje_parada.md", eje_parada.pagina_eje_parada)]
    hay_eje = {}
    for tabla, archivo, funcion in paginas_eje:
        hay_eje[archivo] = con.execute("select count(*) from information_schema.tables where table_name = ?", [tabla]).fetchall()[0][0] > 0
        ruta = out_dir / "hallazgos" / archivo
        if hay_eje[archivo]:
            ruta.write_text(_clean(funcion(con)), encoding="utf-8")
            paginas += 1
        elif ruta.exists():
            ruta.unlink()

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
    if hay_dia_inicio:
        L.append("- El día de inicio como dosis (la caída de los padres cercanos según la parte del mes que expone la fractura, sin pozos lejanos en la pendiente): [dia_inicio.md](hallazgos/dia_inicio.md).")
    if hay_bloq:
        L.append("- Bloques espaciales (los intervalos principales remuestreando bloques de 2 y 5 km en vez de pads): [bloques.md](hallazgos/bloques.md).")
    if hay_hijo:
        L.append("- Lado del hijo (rendimiento de 12 meses según el petróleo ya producido a menos de 1 km): [hijo.md](hallazgos/hijo.md).")
    if hay_hijo_celdas:
        L.append("- Lado del hijo dentro de celdas de 2 km (hijos del mismo lugar fracturados antes y después de que sus vecinos produjeran): [hijo_celdas.md](hallazgos/hijo_celdas.md).")
    if hay_mecanismo:
        L.append("- Mecanismo por la geometría de las ramas (padres al costado de la rama del hijo contra padres en su punta, con placebo previo a la fractura): [mecanismo.md](hallazgos/mecanismo.md).")
    if hay_causal:
        L.append("- Diseño causal (diferencias en diferencias escalonadas con controles aún no tratados; el corte de agua como canal físico, con placebo de cierre): [causal.md](hallazgos/causal.md).")
    if hay_causal_profundo:
        L.append("- Debajo del corte de agua: si entra agua o sale petróleo, con el mismo diseño y la regla fijada antes: [causal_profundo.md](hallazgos/causal_profundo.md).")
    if hay_gas:
        L.append("- El padre en la ventana de gas (padres gasíferos, el gas como resultado y el GOR de los padres petrolíferos): [gas.md](hallazgos/gas.md).")
    if (out_dir / "hallazgos" / "literatura.md").exists():
        L.append("- Comparación con la literatura (las cifras de este trabajo al lado de las publicadas): [literatura.md](hallazgos/literatura.md).")
    if (out_dir / "hallazgos" / "limites.md").exists():
        L.append("- Límites y robustez en detalle (lo que el dato público no deja afirmar, con cada cifra verificada): [limites.md](hallazgos/limites.md).")
    if (out_dir / "hallazgos" / "prospectiva.md").exists():
        L.append("- Prueba prospectiva (predicciones congeladas con los datos hasta un mes y puntuadas cuando se publican los meses siguientes): "
                 "[prospectiva.md](hallazgos/prospectiva.md).")
    if (out_dir / "hallazgos" / "carga_fracturas.md").exists():
        L.append("- Rezago de carga de las fracturas (cuándo aparece cada fractura en el dato público, por operador y por año de inicio; descriptivo): [carga_fracturas.md](hallazgos/carga_fracturas.md).")
    if (out_dir / "hallazgos" / "carga_anual.md").exists():
        L.append("- La subida de 2026 con la misma antigüedad de carga (prueba con regla fijada antes de correr sobre el perfil por año): "
                 "[carga_anual.md](hallazgos/carga_anual.md).")
    if hay_iny:
        L.append("- Validación por inyección (efectos plantados contra efectos recuperados por los estimadores): [inyeccion.md](hallazgos/inyeccion.md).")
    if hay_dosis:
        L.append("- Dosis y respuesta (la caída del padre contra el trabajo del hijo y la depleción): [dosis.md](hallazgos/dosis.md).")
    if hay_dosis_meses:
        L.append("- Dosis mes a mes (la caída del caudal por día contra el trabajo del hijo, k = 1 a 4): [dosis_meses.md](hallazgos/dosis_meses.md).")
    if hay_dosis_pad:
        L.append("- Dosis del pad y cercanía (la caída contra la arena de todo el pad y la interacción depleción por cercanía): [dosis_pad.md](hallazgos/dosis_pad.md).")
    if hay_anillo:
        L.append("- Anillo de control (la brecha del mes 1 y el cierre a 6 meses con cuatro controles): [anillo.md](hallazgos/anillo.md).")
    if hay_decision:
        L.append("- Capa de decisión para un operador (brecha, diferido y valor por edad del padre y banda de distancia): [decision_operador.md](hallazgos/decision_operador.md).")
    if hay_potencia_dosis:
        L.append("- Potencia del nulo de dosis y respuesta (qué efecto mínimo habría podido verse): [potencia_dosis.md](hallazgos/potencia_dosis.md).")
    if hay_rob_op:
        L.append("- Robustez por operador y área (la brecha del mes 1 y el cierre del mes 6 sacando de a un operador y de a un área): [robustez_operador.md](hallazgos/robustez_operador.md).")
    if hay_dias:
        co = dias_perdidos.marts(con, "colorado") is not None
        L.append("- Días que pierde un padre cuando fracturan a un hijo, por operador (si la diferencia entre operadores se mantiene y si más días "
                 "compran mejor caudal después" + (", con la prueba confirmatoria en Colorado" if co else "") + "): [dias_perdidos.md](hallazgos/dias_perdidos.md).")
    if hay_golpes:
        co = golpes_mismo_mes.marts(con, "colorado") is not None
        L.append("- Golpes en el mismo mes: si a un padre le cuesta menos recibir varios hijos en un mes que los mismos hijos en meses "
                 "separados (costo fijo del mes contra costo por hijo, la primera pieza del optimizador de calendario"
                 + (", con la prueba confirmatoria en Colorado" if co else "") + "): [golpes_mismo_mes.md](hallazgos/golpes_mismo_mes.md).")
    if hay_golpes_padre:
        co = golpes_mismo_padre.marts(con, "colorado") is not None
        L.append("- Golpes en el mismo mes con el padre como su propio control: la misma pregunta, comparando cada padre consigo mismo entre "
                 "sus meses de golpe de distinta cantidad de hijos (segunda pieza del optimizador de calendario"
                 + (", con la prueba confirmatoria en Colorado" if co else "") + "): [golpes_mismo_padre.md](hallazgos/golpes_mismo_padre.md).")
    if hay_calendario:
        L.append("- Calendario de golpes: matrices de costo de los dos casos (aditivo y costo fijo más hijo), el calendario de fractura que menos "
                 "pérdida tendría y un backtest ajustado en 2023 que predice 2024 a 2026, con la regla fijada antes de correr (tercera pieza "
                 "del optimizador de calendario, solo el lado del padre): [calendario_golpes.md](hallazgos/calendario_golpes.md).")
    if hay_tray:
        L.append("- Trayectorias de pozo publicadas por la Secretaría de Energía: cuántos hijos y pares cubren y cuánto cambia la distancia al medirla entre ramas en lugar de entre bocas (descriptivo): [trayectorias.md](hallazgos/trayectorias.md).")
    if hay_alcance_rama:
        L.append("- Alcance y dilución de la huella del padre medidos entre ramas (distancia lateral a lateral) en lugar de entre bocas, con la regla fijada de antemano: [alcance_rama.md](hallazgos/alcance_rama.md).")
    if hay_riesgo:
        L.append("- Riesgo de golpe fuerte: cuán probable es que un padre cercano pierda más de 30 puntos de índice al mes 1 de la fractura de un hijo, con un modelo logístico probado hacia adelante (2023 y 2024) y la regla fijada antes de correr: [riesgo.md](hallazgos/riesgo.md).")
    if hay_dosis_geo:
        L.append("- Dosis y respuesta con la geometría de las ramas, detrás de una puerta de potencia (el efecto mínimo detectable de los padres cercanos entre ramas), con la regla fijada de antemano: [dosis_geometria.md](hallazgos/dosis_geometria.md).")
    if hay_hijo_pad:
        L.append("- Lado del hijo dentro del pad: hijos del mismo pad fracturados con más o menos petróleo ya producido por pozos cuya rama pasa a menos de 600 m, con la regla fijada antes de correr: [hijo_pad.md](hallazgos/hijo_pad.md).")
    if (out_dir / "hallazgos" / "colorado_datos.md").exists():
        L.append("- Colorado (cuenca DJ), datos y conteos de la replicación en otra cuenca: [colorado_datos.md](hallazgos/colorado_datos.md).")
    if (out_dir / "hallazgos" / "replicacion.md").exists():
        L.append("- Replicación en Colorado (el estudio de eventos sobre la cuenca DJ, con la regla fijada de antemano): [replicacion.md](hallazgos/replicacion.md).")
    if (out_dir / "hallazgos" / "wyoming_datos.md").exists():
        L.append("- Wyoming, datos y conteos de la replicación en otra cuenca: [wyoming_datos.md](hallazgos/wyoming_datos.md).")
    if (out_dir / "hallazgos" / "replicacion_wyoming.md").exists():
        L.append("- Replicación en Wyoming (el mismo estudio de eventos con la misma regla, fijada antes de bajar la producción): [replicacion_wyoming.md](hallazgos/replicacion_wyoming.md).")
    if (out_dir / "hallazgos" / "replicacion_cuencas.md").exists():
        L.append("- Replicación por cuenca (la lectura de la familia: en cuántas cuencas se replica la huella, sin estimación conjunta): [replicacion_cuencas.md](hallazgos/replicacion_cuencas.md).")
    if hay_eje.get("eje_parada.md"):
        L.append("- Regla de parada del eje de merma (potencia, ventana previa, bloques y exposición): [eje_parada.md](hallazgos/eje_parada.md), con [potencia.md](hallazgos/potencia.md), [eje_controles.md](hallazgos/eje_controles.md) y [eje_exposicion.md](hallazgos/eje_exposicion.md).")
    if (out_dir / "hallazgos" / "mapa_base.md").exists():
        L.append("- Mapa base de Vaca Muerta en 3D (fuente, licencia y huella del relieve, el agua, los límites, las localidades y las concesiones): [mapa_base.md](hallazgos/mapa_base.md).")
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
    from pipeline.cuencas import CUENCAS
    con = duckdb.connect(str(db), read_only=True)
    con_cuencas = {i: duckdb.connect(str(c.db), read_only=True) for i, c in CUENCAS.items() if c.db.exists()}
    try:
        filas = hz.evaluar(con, manifest, con_cuencas=con_cuencas)
        hz.registrar(filas, ROOT / "wiki" / "hallazgos" / "ledger.csv")
        stats = build_wiki(con, manifest, ROOT / "wiki")
    finally:
        con.close()
        for k in con_cuencas.values():
            k.close()
    print(json.dumps(stats, ensure_ascii=False))
    for aviso in hz.lint_wiki(ROOT / "wiki"):
        print(f"[aviso] {aviso}")


if __name__ == "__main__":
    main()
