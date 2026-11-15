"""Typed, read-only operations over the warehouse.

The model never writes SQL. It picks one operation from REGISTRO and fills its typed
arguments; the arguments are validated with pydantic, the SQL is fixed and parameterized,
and the answer sentence is built here from the result rows, so every number in an answer
comes from the warehouse. Each result carries its provenance (tables, data month, raw sha).
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import duckdb
from pydantic import BaseModel, Field

from pipeline.ingest import DATA, ROOT, load_manifest

BBL = 6.2898
Mes = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="Mes 'AAAA-MM'. Vacío: último mes publicado.")
GrupoEdad = Literal["06-11", "12-23", "24-47", "48+"]


class ErrorOperacion(ValueError):
    """Bad argument value (unknown operator, month out of range...). Shown to the model."""


def conectar(path: Path = DATA / "warehouse.duckdb") -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=True)


def filas(con, sql: str, params: list | None = None) -> list[dict]:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def num(x: float | int | None, dec: int = 0) -> str:
    """Spanish number format: 1.234.567,8"""
    if x is None:
        return "s/d"
    s = f"{x:,.{dec}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _resolver(con, valor: str, tabla: str, col: str, que: str) -> str:
    opciones = [r[0] for r in con.execute(f"select distinct {col} from {tabla} where {col} is not null").fetchall()]
    buscado = _plano(valor)
    exactos = [o for o in opciones if _plano(o) == buscado]
    if exactos:
        return exactos[0]
    parciales = [o for o in opciones if buscado and buscado in _plano(o)]
    if len(parciales) == 1:
        return parciales[0]
    # "Vista Energy Argentina" -> "Vista": the longest option contained in the query, as whole words.
    contenidos = sorted((o for o in opciones if f" {_plano(o)} " in f" {buscado} "), key=len, reverse=True)
    if contenidos:
        return contenidos[0]
    muestra = ", ".join(sorted(opciones)[:30])
    raise ErrorOperacion(f"{que} '{valor}' no existe o es ambiguo. Opciones: {muestra}")


def _mes(con, mes: str | None) -> str:
    ultimo = con.execute("select strftime(mes, '%Y-%m') from ultimo_mes").fetchall()[0][0]
    if mes is None:
        return ultimo
    if mes > ultimo:
        raise ErrorOperacion(f"El último mes publicado es {ultimo}; no hay datos de {mes}.")
    return mes


# ---------------------------------------------------------------- arguments

class ArgsProduccion(BaseModel):
    mes: str | None = Mes
    operador: str | None = Field(default=None, description="Operadora (por ejemplo 'YPF', 'Vista'). Vacío: toda la formación.")


class ArgsRanking(BaseModel):
    mes: str | None = Mes
    n: int = Field(default=5, ge=1, le=20, description="Cantidad de operadoras.")


class ArgsInteranual(BaseModel):
    mes: str | None = Mes
    operador: str | None = Field(default=None, description="Operadora. Vacío: toda la formación.")


class ArgsCurva(BaseModel):
    cohorte: int = Field(ge=2017, le=2025, description="Año del primer petróleo del pozo.")
    grupo: Literal["YPF", "Resto"] = "YPF"
    mes_produccion: int = Field(default=12, ge=1, le=36, description="Mes de producción del pozo (1 = primer mes con petróleo).")


class ArgsDiseno(BaseModel):
    cohorte: int = Field(ge=2017, le=2025, description="Año del primer petróleo.")
    grupo: Literal["YPF", "Resto"] = "YPF"


class ArgsBrecha(BaseModel):
    k: int = Field(default=1, ge=-3, le=6, description="Meses desde la fractura del pozo hijo (0 = mes de la fractura).")
    grupo_edad: GrupoEdad | None = Field(default=None, description="Edad del pozo padre en meses. Vacío: todas.")


class ArgsAnual(BaseModel):
    anio: int = Field(ge=2012, le=2030, description="Año de la fractura del pozo hijo.")


class ArgsDiferido(BaseModel):
    operador: str | None = None
    area: str | None = Field(default=None, description="Área o concesión (por ejemplo 'Loma Campana').")
    anio: int | None = Field(default=None, ge=2012, le=2030, description="Año de la fractura del pozo hijo.")


class ArgsPozo(BaseModel):
    sigla: str = Field(min_length=2, max_length=60, description="Sigla del pozo, como figura en el dato público.")


class ArgsCalidad(BaseModel):
    pass


class ArgsWiki(BaseModel):
    ruta: str = Field(default="index.md", max_length=120, pattern=r"^[a-z0-9_./-]+\.md$",
                      description="Página de la wiki, por ejemplo 'hallazgos/interferencia.md' o 'area/loma-campana.md'.")


# ---------------------------------------------------------------- operations

def produccion_vm(con, a: ArgsProduccion) -> dict:
    mes = _mes(con, a.mes)
    op = _resolver(con, a.operador, "mart_vm_mensual", "operador", "Operadora") if a.operador else None
    r = filas(con, """
        select sum(petroleo_kbbl_d) filter (where ? is null or operador = ?) as petroleo_kbbl_d,
               sum(gas_mmm3_d) filter (where ? is null or operador = ?) as gas_mmm3_d,
               sum(pozos_activos) filter (where ? is null or operador = ?) as pozos_activos,
               sum(petroleo_kbbl_d) as total_kbbl_d
        from mart_vm_mensual where strftime(mes, '%Y-%m') = ?""", [op, op] * 3 + [mes])[0]
    quien = op or "Vaca Muerta"
    texto = (f"{quien} produjo {num(r['petroleo_kbbl_d'], 1)} kbbl/d de petróleo y {num(r['gas_mmm3_d'], 1)} MMm3/d "
             f"de gas en {mes}, con {num(r['pozos_activos'])} pozos activos")
    if op:
        r["participacion"] = r["petroleo_kbbl_d"] / r["total_kbbl_d"] if r["total_kbbl_d"] else None
        texto += f" ({num(100 * r['participacion'], 1)}% del petróleo de la formación)"
    return {"valor": r["petroleo_kbbl_d"], "filas": [r], "texto": texto + "."}


def ranking_operadores(con, a: ArgsRanking) -> dict:
    mes = _mes(con, a.mes)
    rs = filas(con, """select operador, petroleo_kbbl_d from mart_vm_mensual
                       where strftime(mes, '%Y-%m') = ? order by petroleo_kbbl_d desc limit ?""", [mes, a.n])
    lista = "; ".join(f"{i + 1}. {r['operador']} {num(r['petroleo_kbbl_d'], 1)} kbbl/d" for i, r in enumerate(rs))
    return {"valor": [r["operador"] for r in rs], "filas": rs, "texto": f"Mayores productoras de petróleo en {mes}: {lista}."}


def variacion_interanual(con, a: ArgsInteranual) -> dict:
    mes = _mes(con, a.mes)
    op = _resolver(con, a.operador, "mart_vm_mensual", "operador", "Operadora") if a.operador else None
    r = filas(con, """
        select sum(petroleo_kbbl_d) filter (where strftime(mes, '%Y-%m') = ?) as actual,
               sum(petroleo_kbbl_d) filter (where mes = strptime(?, '%Y-%m')::date - interval 12 month) as previo
        from mart_vm_mensual where ? is null or operador = ?""", [mes, mes, op, op])[0]
    r["variacion"] = r["actual"] / r["previo"] - 1 if r["previo"] else None
    quien = op or "Vaca Muerta"
    return {"valor": r["variacion"], "filas": [r],
            "texto": f"{quien}: {num(r['actual'], 1)} kbbl/d en {mes} contra {num(r['previo'], 1)} kbbl/d un año antes "
                     f"({'+' if (r['variacion'] or 0) >= 0 else ''}{num(100 * r['variacion'], 1) if r['variacion'] is not None else 's/d'}%)."}


def curva_tipo(con, a: ArgsCurva) -> dict:
    rs = filas(con, "select pozos, petroleo_bbl_d from mart_curva_tipo where cohorte = ? and grupo = ? and mop = ?",
               [a.cohorte, a.grupo, a.mes_produccion])
    if not rs:
        raise ErrorOperacion("Sin dato: el punto tiene menos de 10 pozos o la cohorte todavía no llegó a ese mes.")
    r = rs[0]
    return {"valor": r["petroleo_bbl_d"], "filas": rs,
            "texto": f"Pozos shale oil {a.grupo} con primer petróleo en {a.cohorte}: en su mes {a.mes_produccion} producen "
                     f"en promedio {num(r['petroleo_bbl_d'], 1)} bbl/d ({num(r['pozos'])} pozos)."}


def diseno_cohorte(con, a: ArgsDiseno) -> dict:
    rs = filas(con, "select * from mart_diseno_productividad where cohorte = ? and grupo = ?", [a.cohorte, a.grupo])
    if not rs:
        raise ErrorOperacion("Sin dato para esa cohorte (menos de 10 pozos con 12 meses publicados).")
    r = rs[0]
    return {"valor": r["bbl_12m_por_m_mediana"], "filas": rs,
            "texto": f"Cohorte {a.cohorte} ({a.grupo}, {num(r['pozos'])} pozos): rama mediana {num(r['rama_m_mediana'])} m, "
                     f"{num(r['etapas_mediana'])} etapas, {num(r['arena_tn_por_m_mediana'], 2)} t de arena por metro, "
                     f"{num(r['petroleo_12m_bbl_mediana'])} bbl en 12 meses, {num(r['bbl_12m_por_m_mediana'], 1)} bbl por metro de rama."}


def interferencia_brecha(con, a: ArgsBrecha) -> dict:
    r = filas(con, """
        select count(*) filter (where banda = 'cercano') as eventos_cercanos,
               median(indice) filter (where banda = 'cercano') as indice_cercano,
               median(indice) filter (where banda = 'control') as indice_control
        from int_interferencia_mes where k = ? and (? is null or grupo_edad = ?)""", [a.k, a.grupo_edad, a.grupo_edad])[0]
    r["brecha"] = r["indice_cercano"] - r["indice_control"]
    edad = f"padres de {a.grupo_edad} meses" if a.grupo_edad else "padres de todas las edades"
    return {"valor": r["brecha"], "filas": [r],
            "texto": f"Mes {a.k} desde la fractura del pozo hijo, {edad}: los pozos padre a menos de 1 km rinden "
                     f"{num(100 * r['indice_cercano'])}% de su caudal previo contra {num(100 * r['indice_control'])}% de los "
                     f"pozos de control a 2-5 km (brecha {num(100 * r['brecha'])} puntos, {num(r['eventos_cercanos'])} eventos). "
                     f"Huella medida, no causa: un cierre preventivo se ve igual en datos mensuales."}


def interferencia_anual(con, a: ArgsAnual) -> dict:
    rs = filas(con, "select * from mart_interferencia_anual where anio = ?", [a.anio])
    if not rs or rs[0]["brecha_mes_1"] is None:
        raise ErrorOperacion(f"Sin eventos cercanos en {a.anio}.")
    r = rs[0]
    return {"valor": r["brecha_mes_1"], "filas": rs,
            "texto": f"Fracturas de {a.anio}: {num(r['eventos_cercanos'])} eventos con un pozo padre a menos de 1 km; un mes "
                     f"después el padre rinde {num(-100 * r['brecha_mes_1'])} puntos menos que el control."}


def petroleo_diferido(con, a: ArgsDiferido) -> dict:
    op = _resolver(con, a.operador, "mart_interferencia_diferida", "operador", "Operadora") if a.operador else None
    area = _resolver(con, a.area, "mart_interferencia_diferida", "area", "Área") if a.area else None
    r = filas(con, """select count(*) as eventos, sum(petroleo_diferido_bbl) as petroleo_diferido_bbl
                      from mart_interferencia_diferida
                      where (? is null or operador = ?) and (? is null or area = ?) and (? is null or year(mes_frac) = ?)""",
              [op, op, area, area, a.anio, a.anio])[0]
    filtro = ", ".join(x for x in (op, area and f"área {area}", a.anio and f"fracturas de {a.anio}") if x) or "todo el período"
    return {"valor": r["petroleo_diferido_bbl"], "filas": [r],
            "texto": f"Petróleo diferido en pozos padre a menos de 1 km de una fractura nueva ({filtro}): "
                     f"{num(r['petroleo_diferido_bbl'])} bbl en {num(r['eventos'])} eventos, meses 0 a 6 contra control de igual edad."}


def pozo(con, a: ArgsPozo) -> dict:
    rs = filas(con, """select p.pozo_id, p.sigla, p.operador, p.area, p.tipo_pozo, p.formacion, p.subtipo_recurso,
                              strftime(p.primer_mes_petroleo, '%Y-%m') as primer_mes_petroleo,
                              f.rama_horizontal_m, f.etapas, f.arena_tn,
                              (select sum(petroleo_m3) * 6.2898 from fct_produccion x where x.pozo_id = p.pozo_id) as petroleo_acum_bbl
                       from dim_pozo p left join dim_fractura_pozo f using (pozo_id)
                       where lower(p.sigla) = lower(?)""", [a.sigla.strip()])
    if not rs:
        raise ErrorOperacion(f"No hay un pozo con sigla '{a.sigla}'.")
    r = rs[0]
    rama = f", rama {num(r['rama_horizontal_m'])} m y {num(r['etapas'])} etapas" if r["rama_horizontal_m"] else ""
    return {"valor": r["petroleo_acum_bbl"], "filas": rs,
            "texto": f"{r['sigla']}: {r['operador']}, {r['area']}, {r['formacion']} {r['subtipo_recurso']} ({r['tipo_pozo']}); "
                     f"primer petróleo {r['primer_mes_petroleo'] or 's/d'}{rama}; acumulado {num(r['petroleo_acum_bbl'])} bbl."}


def calidad(con, a: ArgsCalidad) -> dict:
    rep = json.loads((DATA / "dq_report.json").read_text())
    rs = [{"nombre": c["nombre"], "severidad": c["severidad"], "filas": c["filas"], "ok": c["ok"]} for c in rep["checks"]]
    avisos = "; ".join(f"{c['nombre']}: {num(c['filas'])}" for c in rs if not c["ok"])
    return {"valor": rep["bloqueantes_fallidos"], "filas": rs,
            "texto": f"Controles bloqueantes fallidos: {rep['bloqueantes_fallidos']}. Avisos del dato público: {avisos}."}


def pagina_wiki(con, a: ArgsWiki) -> dict:
    base = (ROOT / "wiki").resolve()
    p = (base / a.ruta).resolve()
    if base not in p.parents or not p.exists():
        raise ErrorOperacion(f"No existe la página '{a.ruta}'. Empezá por 'index.md'.")
    texto = p.read_text()
    return {"valor": a.ruta, "filas": [], "texto": texto}


# ---------------------------------------------------------------- registry

@dataclass(frozen=True)
class Operacion:
    nombre: str
    descripcion: str
    args: type[BaseModel]
    fn: Callable[[duckdb.DuckDBPyConnection, BaseModel], dict]
    tablas: tuple[str, ...]


REGISTRO: dict[str, Operacion] = {o.nombre: o for o in [
    Operacion("produccion_vm", "Producción de petróleo (kbbl/d), gas (MMm3/d) y pozos activos de Vaca Muerta en un mes, "
              "total o de una operadora, con su participación.", ArgsProduccion, produccion_vm, ("mart_vm_mensual",)),
    Operacion("ranking_operadores", "Las operadoras que más petróleo producen en Vaca Muerta en un mes.",
              ArgsRanking, ranking_operadores, ("mart_vm_mensual",)),
    Operacion("variacion_interanual", "Variación de la producción de petróleo contra el mismo mes del año anterior.",
              ArgsInteranual, variacion_interanual, ("mart_vm_mensual",)),
    Operacion("curva_tipo", "Caudal promedio de petróleo (bbl/d) de los pozos shale oil de una cohorte en su mes N de producción.",
              ArgsCurva, curva_tipo, ("mart_curva_tipo",)),
    Operacion("diseno_cohorte", "Diseño de terminación (rama, etapas, arena por metro) y productividad a 12 meses de una cohorte.",
              ArgsDiseno, diseno_cohorte, ("mart_diseno_productividad",)),
    Operacion("interferencia_brecha", "Cuánto cae un pozo padre cuando fracturan un pozo nuevo a menos de 1 km, "
              "contra pozos de control de igual edad.", ArgsBrecha, interferencia_brecha, ("int_interferencia_mes",)),
    Operacion("interferencia_anual", "Huella de interferencia (brecha al mes 1) según el año de la fractura del pozo hijo.",
              ArgsAnual, interferencia_anual, ("mart_interferencia_anual",)),
    Operacion("petroleo_diferido", "Barriles de petróleo diferidos en pozos padre por fracturas cercanas, por operadora, área o año.",
              ArgsDiferido, petroleo_diferido, ("mart_interferencia_diferida",)),
    Operacion("pozo", "Ficha de un pozo por sigla: operadora, área, primer petróleo, diseño de fractura, acumulado.",
              ArgsPozo, pozo, ("dim_pozo", "dim_fractura_pozo", "fct_produccion")),
    Operacion("calidad", "Controles de calidad del dato público y cuántas filas afecta cada anomalía.",
              ArgsCalidad, calidad, ("dq_report.json",)),
    Operacion("pagina_wiki", "Lee una página de la wiki generada (operadoras, áreas, pads, hallazgos).",
              ArgsWiki, pagina_wiki, ("wiki/",)),
]}


def catalogo() -> list[dict]:
    return [{"nombre": o.nombre, "descripcion": o.descripcion, "argumentos": o.args.model_json_schema()} for o in REGISTRO.values()]


def fuente(con) -> dict:
    m = load_manifest()
    return {"datos_a": con.execute("select strftime(mes, '%Y-%m') from ultimo_mes").fetchall()[0][0],
            "sha": {k: v.get("sha256", "")[:12] for k, v in m.items()}}


def ejecutar(con, nombre: str, args: dict | None = None) -> dict:
    """Validate and run one operation. Raises KeyError, pydantic.ValidationError or ErrorOperacion."""
    op = REGISTRO[nombre]
    parsed = op.args.model_validate(args or {})
    out = op.fn(con, parsed)
    return {"op": nombre, "args": parsed.model_dump(), **out, "fuente": {"tablas": list(op.tablas), **fuente(con)}}
