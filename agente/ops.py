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
import numpy as np
from pydantic import BaseModel, Field

from pipeline.hallazgos import HIPOTESIS, leer_ledger
from pipeline.ingest import DATA, ROOT, load_manifest

BBL = 6.2898
Mes = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="Mes 'AAAA-MM'. Vacío: último mes publicado.")
GrupoEdad = Literal["06-11", "12-23", "24-47", "48+"]
TipoEvento = Literal["fractura", "primera_produccion", "cambio_estado", "cambio_extraccion", "cierre", "salto_agua",
                    "quiebre_caudal"]
Banda = Literal["cercano", "intermedio", "control"]


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


class ArgsCosto(BaseModel):
    pad: str | None = Field(default=None, pattern=r"^p\d+$",
                            description="Pad de pozos nuevos, por ejemplo 'p1234' (el que figura en el wiki). Alternativa a lat y lon.")
    lat: float | None = Field(default=None, ge=-60, le=-30, description="Latitud en grados decimales del punto del pozo nuevo (negativa).")
    lon: float | None = Field(default=None, ge=-80, le=-55, description="Longitud en grados decimales del punto del pozo nuevo (negativa).")
    fecha: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$",
                              description="Mes 'AAAA-MM' de la fractura del pozo nuevo. Vacío: último mes publicado.")


class ArgsRobustez(BaseModel):
    subconjunto: str | None = Field(default=None, max_length=60,
                                    description="Nombre o parte del nombre de un subconjunto de robustez (por ejemplo 'sin Loma Campana', 'Padre YPF', "
                                                "'2024 a 2026'). Vacío: todos.")


class ArgsPozo(BaseModel):
    sigla: str = Field(min_length=2, max_length=60, description="Sigla del pozo, como figura en el dato público.")


class ArgsEventos(BaseModel):
    sigla: str = Field(min_length=2, max_length=60, description="Sigla del pozo, como figura en el dato público.")
    tipo: TipoEvento | None = Field(default=None, description="Tipo de evento. Vacío: todos.")


class ArgsClases(BaseModel):
    operador: str | None = Field(default=None, description="Operadora del pozo padre. Vacío: todas.")
    area: str | None = Field(default=None, description="Área o concesión del pozo padre.")
    anio: int | None = Field(default=None, ge=2011, le=2030, description="Año de la fractura del pozo hijo.")
    banda: Banda = Field(default="cercano", description="Distancia del hijo: cercano (menos de 1 km), intermedio o control (2 a 5 km).")


class ArgsLibro(BaseModel):
    id: str | None = Field(default=None, max_length=60, description="Id de la hipótesis (por ejemplo 'brecha_mes1'). Vacío: todas.")


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


def eventos_pozo(con, a: ArgsEventos) -> dict:
    p = filas(con, "select pozo_id, sigla from dim_pozo where lower(sigla) = lower(?)", [a.sigla.strip()])
    if not p:
        raise ErrorOperacion(f"No hay un pozo con sigla '{a.sigla}'.")
    pid, sigla = p[0]["pozo_id"], p[0]["sigla"]
    cuenta = filas(con, """select tipo, count(*) as eventos from fct_evento
                           where pozo_id = ? and (? is null or tipo = ?) group by tipo order by tipo""", [pid, a.tipo, a.tipo])
    total = sum(r["eventos"] for r in cuenta)
    ultimos = filas(con, """select strftime(fecha, '%Y-%m-%d') as fecha, tipo, detalle, valor from fct_evento
                            where pozo_id = ? and (? is null or tipo = ?) order by fecha desc, tipo limit 20""", [pid, a.tipo, a.tipo])
    por_tipo = "; ".join(f"{r['tipo']} {num(r['eventos'])}" for r in cuenta) or "sin eventos"
    de_que = f" de tipo {a.tipo}" if a.tipo else ""
    return {"valor": total, "filas": ultimos,
            "texto": f"{sigla}: {num(total)} {'evento' if total == 1 else 'eventos'}{de_que} en el dato público ({por_tipo}). Se listan los últimos {num(len(ultimos))}."}


def clases_interferencia(con, a: ArgsClases) -> dict:
    op = _resolver(con, a.operador, "int_interferencia_clase", "operador", "Operadora") if a.operador else None
    area = _resolver(con, a.area, "int_interferencia_clase", "area", "Área") if a.area else None
    rs = filas(con, """select clase, count(*) as padres from int_interferencia_clase
                       where banda = ? and (? is null or operador = ?) and (? is null or area = ?)
                         and (? is null or year(mes_frac) = ?)
                       group by clase order by clase""", [a.banda, op, op, area, area, a.anio, a.anio])
    total = sum(r["padres"] for r in rs)
    if not total:
        raise ErrorOperacion("Sin pozos padre para ese filtro.")
    con_efecto = sum(r["padres"] for r in rs if r["clase"] != "sin_efecto")
    for r in rs:
        r["participacion"] = r["padres"] / total
    share = con_efecto / total
    filtro = ", ".join(x for x in (op, area and f"área {area}", a.anio and f"fracturas de {a.anio}") if x) or "todo el período"
    detalle = "; ".join(f"{r['clase']} {num(r['padres'])}" for r in rs)
    return {"valor": share, "filas": rs,
            "texto": f"Pozos padre en banda {a.banda} ({filtro}): {num(total)} casos, {num(100 * share, 1)}% con algún efecto "
                     f"({detalle}). Es una huella en datos mensuales, no una causa: un cierre preventivo y un golpe de "
                     f"interferencia pueden verse iguales."}


def libro_hallazgos(con, a: ArgsLibro) -> dict:
    ids = [h.id for h in HIPOTESIS]
    if a.id is not None and a.id not in ids:
        raise ErrorOperacion(f"No existe la hipótesis '{a.id}'. Ids válidos: {', '.join(ids)}.")
    ultimas: dict[str, dict] = {}
    for r in leer_ledger(ROOT / "wiki" / "hallazgos" / "ledger.csv"):
        ultimas[r["id"]] = r  # the ledger is append-only: the last row of an id is the latest
    enunciados = {h.id: h.enunciado for h in HIPOTESIS}
    rs = []
    for i in ids:
        if i in ultimas and (a.id is None or a.id == i):
            r = ultimas[i]
            # una hipotesis preregistrada y todavia sin correr tiene el valor vacio en el libro
            rs.append({"id": i, "enunciado": enunciados[i], "estado": r["estado"], "valor": float(r["valor"]) if r["valor"] != "" else None,
                       "umbral": float(r["umbral"]), "mes_datos": r["mes_datos"]})
    if a.id is not None:
        if not rs:
            raise ErrorOperacion(f"La hipótesis '{a.id}' todavía no tiene evaluación en el libro.")
        r = rs[0]
        return {"valor": r["valor"], "filas": rs,
                "texto": f"{r['id']}: {r['estado']} con datos a {r['mes_datos']} (valor {num(r['valor'], 3)}, umbral {num(r['umbral'], 3)}). {r['enunciado']}"}
    conf = sum(r["estado"] == "confirmado" for r in rs)
    lista = "; ".join(f"{r['id']} {r['estado']} ({num(r['valor'], 3)})" for r in rs)
    return {"valor": conf, "filas": rs, "texto": f"Libro de hallazgos: {num(conf)} de {num(len(rs))} hipótesis confirmadas. {lista}."}


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


_FACTORES = {"km": "distancia al pozo nuevo", "desvio_eje_10": "rumbo respecto del eje de máxima merma",
             "edad_anios": "edad del padre", "base_10m3d": "caudal base del padre",
             "hijos_1km": "cantidad de hijos a menos de 1 km", "arena_1000tn": "arena del hijo",
             "etapas_10": "etapas del hijo", "parado": "cierre declarado del padre", "area": "área"}

_SQL_PADRES = """
with c as (select ?::double as lat, ?::double as lon),
base as (
  select pozo_id, avg(petroleo_m3 / dias_mes) as base_m3_d
  from fct_produccion
  where mes between cast(? as date) - interval 3 month and cast(? as date) - interval 1 month
  group by pozo_id
)
select u.pozo_id as padre, trim(u.area) as area, b.base_m3_d,
       date_diff('month', u.primer_mes_petroleo, cast(? as date)) as edad_meses,
       111.32 * sqrt(power((u.lon - c.lon) * cos(radians(c.lat)), 2) + power(u.lat - c.lat, 2)) as km,
       (degrees(atan2((u.lon - c.lon) * cos(radians(c.lat)), u.lat - c.lat)) + 360) % 180 as rumbo
from int_pozo_ubicacion u, c
join base b on b.pozo_id = u.pozo_id
where abs(u.lat - c.lat) < 0.012 and abs(u.lon - c.lon) < 0.016
  and u.primer_mes_petroleo <= cast(? as date) - interval 6 month
  and b.base_m3_d > 1
  and 111.32 * sqrt(power((u.lon - c.lon) * cos(radians(c.lat)), 2) + power(u.lat - c.lat, 2)) < 1
order by km, u.pozo_id
"""


def _residuales_cv(con) -> dict | None:
    """Residuales fuera de muestra del modelo de costo por tercil de predicción, o None si los marts no están."""
    try:
        res = filas(con, "select tercil, residual, pred from mart_costo_residuales order by tercil, residual, pred")
        r2 = con.execute("select r2 from mart_costo_cv where modelo = 'modelo'").fetchall()
    except duckdb.Error:
        return None
    if not res or not r2:
        return None
    pools = {t: [x["residual"] for x in res if x["tercil"] == t] for t in (1, 2, 3)}
    if not all(pools.values()):
        return None
    cortes = tuple(max(x["pred"] for x in res if x["tercil"] == t) for t in (1, 2))
    return {"pools": {t: np.array(v) for t, v in pools.items()}, "cortes": cortes, "r2": r2[0][0]}


def costo_interferencia(con, a: ArgsCosto) -> dict:
    """Barriles diferidos esperados (meses 0 a 6) en los padres a menos de 1 km de un pad o punto, con el modelo de
    pipeline/costo.py: lineal, por padre acotado en cero, sin pérdida del hijo ni espaciamiento lateral."""
    from pipeline import costo as modelo
    if (a.lat is None) != (a.lon is None):
        raise ErrorOperacion("Pasá lat y lon juntas.")
    if a.pad and a.lat is not None:
        raise ErrorOperacion("Pasá el pad o las coordenadas, no ambos.")
    if not a.pad and a.lat is None:
        raise ErrorOperacion("Falta el pad (por ejemplo 'p1234') o las coordenadas lat y lon.")
    try:
        coef = {r["termino"]: r for r in filas(con, "select * from mart_costo_coef")}
        ejes = {r["area"]: r["eje_grados"] for r in filas(con, "select * from mart_anisotropia_area where usa_en_costo")}
    except duckdb.CatalogException as e:
        raise ErrorOperacion("El modelo de costo no está calculado: falta correr pipeline.costo.") from e
    mes = _mes(con, a.fecha)
    primero = f"{mes}-01"
    hijos, arena, etapas = 1, None, None
    if a.pad:
        pozos = filas(con, "select pozo_id, lat, lon from int_pozo_ubicacion where pad_id = ?", [a.pad])
        if not pozos:
            raise ErrorOperacion(f"No existe el pad '{a.pad}'. Se ve en el wiki, por ejemplo en pad/p1234.md.")
        lat = sum(p["lat"] for p in pozos) / len(pozos)
        lon = sum(p["lon"] for p in pozos) / len(pozos)
        ids = [p["pozo_id"] for p in pozos]
        marca = ",".join("?" * len(ids))
        hijos = max(1, con.execute(f"select count(*) from int_frac_hijo where hijo in ({marca}) and strftime(mes_frac, '%Y-%m') = ?",
                                   ids + [mes]).fetchall()[0][0])
        fr = con.execute(f"select avg(arena_tn), avg(etapas) from dim_fractura_pozo where pozo_id in ({marca})", ids).fetchall()[0]
        arena = fr[0] / 1000 if fr[0] is not None else None
        etapas = fr[1] / 10 if fr[1] is not None else None
        etiqueta = f"el pad {a.pad}"
    else:
        lat, lon = a.lat, a.lon
        etiqueta = f"el punto ({num(lat, 4)}, {num(lon, 4)})"
    arena = coef["arena_1000tn"]["media_x"] if arena is None else arena
    etapas = coef["etapas_10"]["media_x"] if etapas is None else etapas
    padres = filas(con, _SQL_PADRES, [lat, lon, primero, primero, primero, primero])
    fe = [t for t in coef if t.startswith("area:")]
    esperado, contrib, detalle, preds = 0.0, {k: 0.0 for k in _FACTORES}, [], []
    cv = _residuales_cv(con)
    for r in padres:
        x = {"km": r["km"], "desvio_eje_10": float(modelo.desvio_eje(r["rumbo"], modelo.eje_de_area(r["area"], ejes))) / 10,
             "edad_anios": r["edad_meses"] / 12, "base_10m3d": r["base_m3_d"] / 10, "hijos_1km": hijos,
             "arena_1000tn": arena, "etapas_10": etapas, "parado": 0.0}
        pred = coef["intercepto"]["coef"]
        for t, v in x.items():
            pred += coef[t]["coef"] * v
            contrib[t] += coef[t]["coef"] * (v - coef[t]["media_x"])
        for t in fe:
            d = 1.0 if t == f"area:{r['area']}" else 0.0
            pred += coef[t]["coef"] * d
            contrib["area"] += coef[t]["coef"] * (d - coef[t]["media_x"])
        esperado += max(pred, 0.0)
        preds.append(pred)
        fila = {"padre": r["padre"], "area": r["area"], "km": round(r["km"], 3), "rumbo": round(r["rumbo"], 1),
                "base_m3_d": round(r["base_m3_d"], 1), "esperado_bbl": round(max(pred, 0.0))}
        if cv:
            lo, hi = modelo.intervalo_padre(pred, cv["pools"], cv["cortes"])
            fila.update({"p10_bbl": round(lo), "p90_bbl": round(hi)})
        detalle.append(fila)
    factores = [{"factor": _FACTORES[k], "bbl_vs_evento_tipico": round(v)}
                for k, v in sorted(contrib.items(), key=lambda kv: -abs(kv[1]))[:3]] if padres else []
    if not padres:
        texto = (f"No hay padres en producción a menos de 1 km de {etiqueta} en {mes} (con al menos 6 meses de vida y más de "
                 f"1 m3/d de caudal base); el diferido esperado es 0 bbl.")
        intervalo = {"p10": 0.0, "p90": 0.0}
    else:
        fs = "; ".join(f"{f['factor']} ({'suma' if f['bbl_vs_evento_tipico'] >= 0 else 'resta'} "
                       f"{num(abs(f['bbl_vs_evento_tipico']))} bbl contra un evento típico)" for f in factores)
        texto = (f"Fractura en {etiqueta}, {mes}: {num(len(padres))} padres en producción a menos de 1 km; diferido esperado "
                 f"{num(esperado)} bbl en los meses 0 a 6 contra control de igual edad. Factores que más pesan: {fs}. "
                 f"Modelo lineal de asociación, sin la pérdida del pozo hijo ni el espaciamiento lateral.")
        intervalo = None
    if cv is None:
        calibracion = "No disponible: falta correr pipeline.costo para calcular los errores fuera de muestra."
        texto += " El intervalo de incertidumbre no está disponible: falta correr pipeline.costo."
        intervalo = None
    else:
        calibracion = (f"R2 fuera de muestra del modelo: {num(cv['r2'], 2)} (validación cruzada por pad hijo); el intervalo "
                       f"supone errores independientes entre padres.")
        if padres:
            lo, hi = modelo.intervalo_suma(preds, cv["pools"], cv["cortes"])
            intervalo = {"p10": lo, "p90": hi}
            texto += (f" Intervalo de 80%: de {num(lo)} a {num(hi)} bbl (según los errores fuera de muestra del modelo, "
                      f"que es de asociación; supone errores independientes entre padres).")
    return {"valor": esperado, "filas": detalle[:20], "factores": factores, "texto": texto,
            "intervalo_bbl": intervalo, "calibracion": calibracion}


def robustez_eje(con, a: ArgsRobustez) -> dict:
    """Qué tan robusto es el eje de interferencia este-oeste: el eje de la muestra completa y el de cada subconjunto
    de pipeline/robustez.py. Un eje está definido si su IC mide menos de ANCHO_MAX grados."""
    from pipeline.costo import ANCHO_MAX, P_EJE_COSTO
    from pipeline.robustez import ic_contiene
    try:
        rs = filas(con, "select * from mart_robustez_eje order by (grupo <> 'completa'), grupo, subconjunto")
    except duckdb.CatalogException as e:
        raise ErrorOperacion("El análisis de robustez no está calculado: falta correr pipeline.robustez.") from e
    if not rs:
        raise ErrorOperacion("El análisis de robustez está vacío: falta correr pipeline.robustez.")
    for r in rs:
        r["definido"] = bool(r["ancho_ic"] < ANCHO_MAX)
        r["p_menor_umbral"] = bool(r["p_perm"] < P_EJE_COSTO)
    base = next(r for r in rs if r["grupo"] == "completa")
    sub = [r for r in rs if r["grupo"] != "completa"]
    cont90 = ic_contiene(base["eje"], base["ic_bajo"], base["ic_alto"], base["ancho_ic"], 90.0)
    if a.subconjunto is not None and a.subconjunto.strip():
        buscado = _plano(a.subconjunto)
        exactos = [r for r in rs if _plano(r["subconjunto"]) == buscado]
        elegidos = exactos or [r for r in rs if buscado and buscado in _plano(r["subconjunto"])]
        if len(elegidos) != 1:
            validos = "; ".join(r["subconjunto"] for r in rs)
            motivo = "no existe" if not elegidos else "es ambiguo"
            raise ErrorOperacion(f"El subconjunto '{a.subconjunto}' {motivo}. Subconjuntos válidos: {validos}.")
        r = elegidos[0]
        estado = (f"definido (IC de {num(r['ancho_ic'])} grados, menos de {num(ANCHO_MAX)})" if r["definido"]
                  else f"no definido (IC de {num(r['ancho_ic'])} grados, {num(ANCHO_MAX)} o más)")
        c90 = ic_contiene(r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], 90.0)
        firme = r["definido"] and r["p_menor_umbral"]
        texto = (f"{r['subconjunto']} ({num(r['n'])} eventos): eje de {num(r['eje'], 1)} grados, IC 95% de {num(r['ic_bajo'], 1)} "
                 f"a {num(r['ic_alto'], 1)}, p de permutación {num(r['p_perm'], 3)}. Eje {estado}. "
                 f"El IC {'incluye' if c90 else 'no incluye'} el este-oeste (90 grados): "
                 f"{'consistente' if c90 else 'no consistente'} con el este-oeste; {'firme' if firme else 'no firme'} "
                 f"(firme exige un IC de menos de {num(ANCHO_MAX)} grados y p menor que {num(P_EJE_COSTO, 2)}). "
                 f"Muestra completa: {num(base['eje'], 1)} grados.")
        return {"valor": r["eje"], "filas": [r], "texto": texto}
    defin = [r for r in sub if r["definido"]]
    firmes = [r for r in defin if r["p_menor_umbral"]]
    indef = [r["subconjunto"] for r in sub if not r["definido"]]
    firme = bool(sub) and len(firmes) == len(sub)
    texto = (f"El eje de la muestra completa es {num(base['eje'], 1)} grados (IC 95% de {num(base['ic_bajo'], 1)} a "
             f"{num(base['ic_alto'], 1)}, p de permutación {num(base['p_perm'], 3)}) y su IC {'incluye' if cont90 else 'no incluye'} "
             f"el este-oeste (90 grados). En {num(len(defin))} de {num(len(sub))} subconjuntos el eje está definido "
             f"(IC de menos de {num(ANCHO_MAX)} grados); en {num(len(firmes))} de ellos además el p de permutación es menor que "
             f"{num(P_EJE_COSTO, 2)}.")
    if indef:
        texto += f" No está definido en: {'; '.join(indef)}."
    texto += (f" Es {'consistente con el este-oeste' if cont90 else 'no consistente con el este-oeste'}"
              + (" y está firme en todos los cortes." if firme else " pero no es firme: depende del corte de datos."))
    return {"valor": len(defin), "filas": rs, "texto": texto}


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
    Operacion("costo_interferencia", "Barriles de petróleo que se esperaría diferir en los padres a menos de 1 km de un pad o "
              "punto cuando se fractura un pozo nuevo (meses 0 a 6), con los factores que más pesan.",
              ArgsCosto, costo_interferencia, ("int_pozo_ubicacion", "fct_produccion", "mart_costo_coef", "mart_anisotropia_area",
                                             "mart_costo_cv", "mart_costo_residuales")),
    Operacion("robustez_eje", "Qué tan robusto es el eje de interferencia este-oeste: eje, intervalo, p de permutación y si está "
              "definido, en la muestra completa y en 13 subconjuntos (períodos, operador, sin un área, distancia); "
              "opcionalmente uno solo por nombre.", ArgsRobustez, robustez_eje, ("mart_robustez_eje",)),
    Operacion("pozo", "Ficha de un pozo por sigla: operadora, área, primer petróleo, diseño de fractura, acumulado.",
              ArgsPozo, pozo, ("dim_pozo", "dim_fractura_pozo", "fct_produccion")),
    Operacion("eventos_pozo", "Cantidad y lista (últimos 20) de eventos de un pozo por sigla: fracturas, primera producción, "
              "cambios de estado o de extracción, cierres, saltos de corte de agua y quiebres de caudal "
              "(caída del caudal del pozo al fracturarse un vecino a menos de 1 km).",
              ArgsEventos, eventos_pozo, ("fct_evento", "dim_pozo")),
    Operacion("clases_interferencia", "Cuántos pozos padre muestran golpe, cierre preventivo, ambos o ningún efecto cuando se fractura "
              "un pozo cercano, y qué parte tiene algún efecto; por operadora, área, año y banda de distancia.",
              ArgsClases, clases_interferencia, ("int_interferencia_clase",)),
    Operacion("libro_hallazgos", "Estado actual de las hipótesis del libro de hallazgos (confirmada o no, valor, umbral, mes de datos).",
              ArgsLibro, libro_hallazgos, ("wiki/hallazgos/ledger.csv",)),
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
