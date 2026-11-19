"""Libro de hallazgos: hipotesis en codigo, re-evaluadas en cada build.

Cada hipotesis tiene una consulta SQL que devuelve un numero, una expectativa
con umbral y un estado (confirmado / debilitado / refutado / no firme). Las evaluaciones
se acumulan en ``wiki/hallazgos/ledger.csv`` (idempotente por id, hash de datos
de produccion y fractura, y firma de la hipotesis: consulta, operador y umbral).
"""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

LEDGER_COLS = ["id", "sha_datos", "firma", "mes_datos", "valor", "op", "umbral", "estado", "evaluado_en"]
DEBIL_FRAC = 0.25
# veredicto de una regla propia -> estado del libro. Solo "sostiene" confirma y solo "no se sostiene" refuta; el resto es no firme.
ESTADO_DE_VEREDICTO = {"sostiene": "confirmado", "no se sostiene": "refutado"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


@dataclass(frozen=True)
class Hipotesis:
    id: str
    enunciado: str
    sql: str
    op: str  # '<', '>' o 'abs<'
    umbral: float
    unidad: str
    firmeza: bool = False  # si cumple el umbral pero el eje no es firme (ver razones_eje_no_firme), el estado es "no firme"
    sql_estado: str = ""  # si esta, el estado sale del veredicto de la regla propia de la hipotesis (ver ESTADO_DE_VEREDICTO)
    almacen: str = "vm"  # id de una cuenca ("colorado"): se evalua sobre data/<id>/warehouse.duckdb; sin la tabla de su consulta queda "preregistrada"


_BRECHA_K = """
select
  (select median(indice) from int_interferencia_mes where banda = 'cercano' and k = {k})
  - (select median(indice) from int_interferencia_mes where banda = 'control' and k = {k})
"""

_EVENTOS_CC = """
  select padre, cast(mes_frac as date) as m, banda
  from int_interferencia_evento
  where banda in ('cercano', 'control')
"""

_SQL_SALTO_AGUA = f"""
with ev as ({_EVENTOS_CC}),
corte as (
  select e.padre, e.m, e.banda, t.k,
         f.agua_m3 / nullif(f.agua_m3 + f.petroleo_m3, 0) as wc
  from ev e
  cross join (values (-3), (-2), (-1), (0), (1)) t(k)
  join fct_produccion f
    on f.pozo_id = e.padre and f.mes = e.m + to_months(t.k)
),
salto as (
  select padre, m, banda,
         max(wc) filter (where k in (0, 1)) - avg(wc) filter (where k in (-3, -2, -1)) as salto
  from corte
  group by padre, m, banda
),
por_banda as (
  select banda, avg(case when salto > 0.15 then 1.0 else 0.0 end) as share
  from salto
  where salto is not null
  group by banda
)
select (select share from por_banda where banda = 'cercano')
     - (select share from por_banda where banda = 'control')
"""

_SQL_PARADO = f"""
with ev as ({_EVENTOS_CC}),
marca as (
  select e.banda,
         case when exists (
           select 1 from stg_produccion s
           where s.pozo_id = e.padre and s.mes = e.m and s.estado = 'Parado Transitoriamente'
         ) then 1.0 else 0.0 end as parado
  from ev e
),
por_banda as (select banda, avg(parado) as share from marca group by banda)
select (select share from por_banda where banda = 'cercano')
     - (select share from por_banda where banda = 'control')
"""

_SQL_ANISOTROPIA = """
with ev as (
  select e.padre, e.mes_frac, e.km_min,
         (degrees(atan2((p.lon - c.lon) * cos(radians(c.lat)), p.lat - c.lat)) + 360) % 180 as rumbo
  from int_interferencia_evento e
  join int_pozo_ubicacion c on c.pozo_id = e.hijo_cercano
  join int_pozo_ubicacion p on p.pozo_id = e.padre
  where e.banda = 'cercano' and e.km_min >= 0.3 and e.km_min < 1
),
idx as (
  select ev.rumbo, m.indice
  from ev
  join int_interferencia_mes m
    on m.padre = ev.padre and m.mes_frac = ev.mes_frac and m.banda = 'cercano' and m.k = 1
)
select
  (select median(indice) from idx where rumbo >= 56.25 and rumbo < 101.25)
  - (select median(indice) from idx where rumbo < 22.5 or rumbo >= 157.5)
"""

# Hipotesis renombradas: su historial en el ledger (solo agrega filas) sigue bajo el id anterior y se muestra junto al nuevo.
RENOMBRADAS = {"asimetria_de_superficie": "anisotropia"}

HIPOTESIS = [
    Hipotesis("brecha_mes1",
              "Al mes 1 de la fractura del hijo, el índice de los padres cercanos queda por debajo "
              "del de los controles (mediana cercano menos control).",
              _BRECHA_K.format(k=1), "<", -0.10, "índice"),
    Hipotesis("recuperacion_mes6",
              "Al mes 6 la brecha se cerró: la diferencia de medianas entre cercanos y controles es chica.",
              _BRECHA_K.format(k=6), "abs<", 0.05, "índice"),
    Hipotesis("salto_agua",
              "Los padres cercanos tienen saltos de corte de agua (más de 0,15) con más frecuencia "
              "que los controles (diferencia de proporciones).",
              _SQL_SALTO_AGUA, ">", 0.10, "proporción"),
    Hipotesis("parado_declarado",
              "Los padres cercanos figuran como Parado Transitoriamente en el mes de la fractura con "
              "más frecuencia que los controles (diferencia de proporciones).",
              _SQL_PARADO, ">", 0.03, "proporción"),
    Hipotesis("asimetria_de_superficie",
              "Entre eventos cercanos a 0,3 a 1 km, el sector de rumbos de superficie de 56,25 a 101,25 grados pierde más "
              "producción al mes 1 que el sector de 0 +/- 22,5 grados (diferencia de medianas del índice). Es una descripción de la "
              "muestra: el sector contiene a la vez el eje estimado (93 grados) y el SHmax publicado (67,5), así que no distingue "
              "entre ellos, y con datos públicos esa dirección no se separa de cómo se disponen los pads, y la geometría de las ramas no se pudo probar (regla de parada, "
              "eje_parada.md). Antes se llamaba `anisotropia` y figuraba como confirmado.",
              _SQL_ANISOTROPIA, "<", -0.10, "índice", firmeza=True),
    Hipotesis("sincronia_mes0",
              "La brecha del mes de la fractura crece con la fracción del mes posterior al inicio de la fractura del hijo: "
              "el límite superior del IC de la pendiente (índice por unidad de fracción) queda por debajo de -0,02 "
              "(regla fijada antes de correr, pipeline/sincronia.py).",
              "select ic_alto from mart_sincronia_pendiente where k = 0", "<", -0.02, "índice por unidad de fracción"),
    Hipotesis("brecha_mes1_bloques",
              "El IC 95% por bloques espaciales de 5 km de la brecha del mes 1 (base de los meses -3 a -1) tiene el límite superior "
              "por debajo de -0,10: no cruza -10 puntos (regla fijada antes de correr, pipeline/bloques.py).",
              "select ic_alto_5km from mart_bloques where metrica = 'brecha_mes1_base_original' and k = 1 limit 1", "<", -0.10, "índice"),
    Hipotesis("sincronia_mes0_bloques",
              "La pendiente de la brecha del mes 0 por fracción del mes tiene, con el IC por bloques espaciales de 5 km, el límite "
              "superior por debajo de -0,02 (regla fijada antes de correr, pipeline/bloques.py).",
              "select ic_alto_5km from mart_bloques where metrica = 'sincronia_pendiente' and k = 0 limit 1", "<", -0.02,
              "índice por unidad de fracción"),
    Hipotesis("hijo_depletado",
              "Un hijo cerca de pozos depletados rinde menos petróleo por metro de rama a 12 meses que un hijo en zona virgen y el "
              "control negativo, con pozos posteriores, es nulo: el valor es el límite superior del IC del grupo muy depletado, si el "
              "control negativo es nulo (sin valor si no lo es), y queda por debajo de cero, en bbl por metro (regla fijada antes de "
              "correr, pipeline/hijo.py). El estado sale del veredicto de esa regla: confirmado si sostiene, refutado si no se "
              "sostiene, y no firme en cualquier otro caso (ubicación, no firme o sin muestra).",
              "select case when c.ic_bajo <= 0 and 0 <= c.ic_alto then p.ic_alto end "
              "from mart_hijo_coef p, mart_hijo_coef c where p.modelo = 'principal' and p.termino = 'muy_depletado' "
              "and c.modelo = 'control_negativo' and c.termino = 'muy_depletado'", "<", 0.0, "bbl por metro",
              sql_estado="select veredicto from mart_hijo_coef where modelo = 'principal' and termino = 'muy_depletado'"),
    Hipotesis("inyeccion_r1",
              "Un efecto plantado de 20% de caída de caudal en el mes 1 se recupera con la brecha del mes 1 a menos de 5 puntos de "
              "-20 (media entre mundos simulados, índice con base de los meses -3 a -1; regla fijada antes de correr, "
              "pipeline/inyeccion.py).",
              "select recuperado_media - plantado from mart_inyeccion where escenario = 'S2' and tamano = 20 and medida = 'brecha_mes1'",
              "abs<", 5.0, "puntos"),
    Hipotesis("inyeccion_r2",
              "El reparto entre días y caudal por día se identifica: con un cierre plantado la parte de los días es de al menos 80% "
              "y con una caída de caudal plantada la parte del caudal por día es de al menos 80% (el menor de los dos valores; "
              "regla fijada antes de correr, pipeline/inyeccion.py).",
              "select least((select parte_dias from mart_inyeccion where escenario = 'S1' and medida = 'brecha_mes1'), "
              "(select parte_tasa from mart_inyeccion where escenario = 'S2' and tamano = 20 and medida = 'brecha_mes1'))",
              ">", 0.80, "proporción"),
    Hipotesis("inyeccion_r3",
              "Una caída plantada de 40% desde el día de inicio de la fractura se recupera con pendiente negativa y IC que excluye "
              "cero en al menos 80% de los mundos simulados (regla fijada antes de correr, pipeline/inyeccion.py).",
              "select ic_excluye_cero_frac from mart_inyeccion where escenario = 'S3' and tamano = 40 and medida = 'pendiente_mes0'",
              ">", 0.80, "proporción de mundos"),
    Hipotesis("inyeccion_r4a",
              "Sin efecto plantado, el IC de la brecha del mes 1 excluye cero en como máximo 10% de los mundos simulados "
              "(regla fijada antes de correr, pipeline/inyeccion.py).",
              "select ic_excluye_cero_frac from mart_inyeccion where escenario = 'S5' and medida = 'brecha_mes1'",
              "<", 0.10, "proporción de mundos"),
    Hipotesis("inyeccion_r4b",
              "Una brecha previa de nivel de 5% se lee como previa a la fractura: la pretendencia y la brecha neta del mes 1 quedan a "
              "menos de 2 puntos de lo plantado (-5 y 0), restando el mundo nulo de los mismos sorteos (regla fijada antes de "
              "correr, pipeline/inyeccion.py).",
              "select max(abs(recuperado_media - plantado)) from mart_inyeccion where escenario = 'S4' and tamano = 5 "
              "and medida in ('preten', 'brecha_mes1_neta')",
              "<", 2.0, "puntos"),
    Hipotesis("replicacion_colorado",
              "Réplica en la cuenca DJ de Colorado: se sostiene si el IC 95% por bloques espaciales de 5 km de la brecha del mes 1 queda "
              "por debajo de cero y la brecha previa a la fractura con base limpia es menor, en valor absoluto, que la del mes 1; si no, "
              "no se replica. El valor es el mayor entre el límite superior de ese IC y la diferencia de valores absolutos (previa menos "
              "mes 1), y se sostiene si es menor que cero (regla fijada antes de correr, pipeline/replicacion.py).",
              "select greatest(ic_alto_bloque, abs(brecha_previa_limpia) - abs(brecha)) from mart_replicacion_colorado where k = 1 limit 1",
              "<", 0.0, "índice", almacen="colorado"),
    Hipotesis("anio_2026_carga",
              "La brecha del mes 1 de 2026 es mayor que la de 2021 a 2024 cuando todos los años se miran con la misma antigüedad de "
              "carga de fracturas (hijos cargados con hasta 3 meses de rezago). El valor es el límite superior del IC 95% por bloques "
              "de 5 km de la diferencia D (2026 menos 2021 a 2024) y se sostiene si es menor que cero y la diferencia con solo los "
              "hijos de YPF también es negativa (regla fijada antes de correr, pipeline/carga_anual.py).",
              "select ic_alto from mart_carga_anual_prueba where estadistico = '2026'", "<", 0.0, "índice",
              sql_estado="select veredicto from mart_carga_anual_prueba where estadistico = '2026'"),
    Hipotesis("replicacion_wyoming",
              "Réplica en Wyoming (WOGCC): se sostiene si el IC 95% por bloques espaciales de 5 km de la brecha del mes 1 queda por "
              "debajo de cero y la brecha previa a la terminación con base limpia es menor, en valor absoluto, que la del mes 1; si no, no "
              "se replica. El valor es el mayor entre el límite superior de ese IC y la diferencia de valores absolutos (previa menos "
              "mes 1), y se sostiene si es menor que cero (misma regla que la de Colorado, fijada antes de bajar la producción de "
              "Wyoming, pipeline/wyoming/__init__.py).",
              "select greatest(ic_alto_bloque, abs(brecha_previa_limpia) - abs(brecha)) from mart_replicacion_wyoming where k = 1 limit 1",
              "<", 0.0, "índice", almacen="wyoming"),
]


def _cumple(op: str, valor: float, umbral: float) -> tuple[bool, float]:
    """(cumple, distancia al umbral; positiva si falla)."""
    if op == "<":
        return valor < umbral, valor - umbral
    if op == ">":
        return valor > umbral, umbral - valor
    if op == "abs<":
        return abs(valor) < umbral, abs(valor) - umbral
    raise ValueError(f"operador desconocido: {op}")


def clasificar(op: str, valor, umbral: float) -> str:
    if valor is None:
        return "refutado"
    ok, falta = _cumple(op, float(valor), umbral)
    if ok:
        return "confirmado"
    return "debilitado" if falta < DEBIL_FRAC * abs(umbral) else "refutado"


def _existe(con, tabla: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_schema = 'main' "
                            "and table_name = ?", [tabla]).fetchone()[0])


def razones_eje_no_firme(con) -> list[str] | None:
    """Razones por las que el eje de mayor merma no es firme, leídas de los marts que ya publican la robustez y la
    validación fuera de tiempo (sin análisis nuevo). Lista vacía: el eje es firme. None: faltan los marts y no se puede juzgar.

    No es firme si ocurre cualquiera de:
      * el eje no está definido en algún subconjunto de mart_robustez_eje (IC de ANCHO_MAX grados o más, o p de permutación
        de P_EJE_COSTO o más), o el IC de la muestra completa mide ANCHO_MAX grados o más;
      * falla la prueba fuera de tiempo de mart_validacion_holdout: el eje de entrenamiento no se separa del SHmax publicado
        ni de los ejes al azar (IC de la diferencia que incluye cero, o 5% o más de los ejes al azar lo iguala).
    """
    from pipeline.costo import ANCHO_MAX, P_EJE_COSTO
    if not (_existe(con, "mart_robustez_eje") and _existe(con, "mart_validacion_holdout")):
        return None
    razones = []
    completa = con.execute("select ancho_ic from mart_robustez_eje where grupo = 'completa'").fetchall()
    if not completa or completa[0][0] is None or completa[0][0] >= ANCHO_MAX:
        razones.append(f"el IC de la muestra completa mide {ANCHO_MAX:.0f} grados o más")
    sub = con.execute("select count(*), count(*) filter (where ancho_ic >= ? or p_perm >= ?) "
                      "from mart_robustez_eje where grupo <> 'completa'", [ANCHO_MAX, P_EJE_COSTO]).fetchone()
    if sub[1]:
        razones.append(f"el eje no está definido en {sub[1]} de {sub[0]} subconjuntos")
    from pipeline.validacion import holdout_razones
    cur = con.execute("select * from mart_validacion_holdout")
    cols = [d[0] for d in cur.description]
    razones += holdout_razones([dict(zip(cols, r)) for r in cur.fetchall()])
    if _existe(con, "mart_eje_parada"):
        for pata, nombre in con.execute("select pata, nombre from mart_eje_parada where dispara order by pata").fetchall():
            razones.append(f"regla de parada, pata {pata}: {nombre}")
    return razones


def _mes_datos(con) -> str:
    row = con.execute("select mes from ultimo_mes").fetchall()
    v = row[0][0] if row else None
    return "s/d" if v is None else f"{v.year:04d}-{v.month:02d}"


def sha_produccion(manifest) -> str:
    """Hash corto de los datos: produccion y, si esta, fractura (Adjunto IV)."""
    m = manifest or {}
    prod = (m.get("produccion_no_convencional") or {}).get("sha256")
    frac = (m.get("fractura_adjunto_iv") or {}).get("sha256")
    if not prod:
        return "s/d"
    if not frac:
        return str(prod)[:12]
    return hashlib.sha256(f"{prod}+{frac}".encode()).hexdigest()[:12]


def firma(h) -> str:
    """Hash corto de la definicion de una hipotesis; cambia si cambia su consulta o su umbral."""
    base = f"{h.sql}|{h.op}|{h.umbral}" + ("|firmeza" if h.firmeza else "") + (f"|{h.sql_estado}" if h.sql_estado else "")
    return hashlib.sha256(base.encode()).hexdigest()[:8]


def _valor_cuenca(con_cuenca, h: Hipotesis):
    """Valor de una hipotesis de una cuenca, o None si todavia no hay warehouse o tabla (queda preregistrada)."""
    if con_cuenca is None:
        return None
    try:
        r = con_cuenca.execute(h.sql).fetchall()
    except duckdb.CatalogException:
        return None
    return None if not r or r[0][0] is None else float(r[0][0])


def evaluar(con, manifest, hoy: str | None = None, con_colorado=None, con_cuencas: dict | None = None) -> list[dict]:
    sha = sha_produccion(manifest)
    mes = _mes_datos(con)
    hoy = hoy or date.today().isoformat()
    filas = []
    for h in HIPOTESIS:
        if h.almacen != "vm":
            valor = _valor_cuenca((con_cuencas or {}).get(h.almacen, con_colorado if h.almacen == "colorado" else None), h)
            estado = "preregistrada" if valor is None else clasificar(h.op, valor, h.umbral)
            filas.append({"id": h.id, "enunciado": h.enunciado, "valor": valor, "op": h.op,
                          "umbral": h.umbral, "estado": estado,
                          "sha_datos": sha, "firma": firma(h), "mes_datos": mes, "evaluado_en": hoy})
            continue
        r = con.execute(h.sql).fetchall()
        valor = r[0][0] if r else None
        valor = None if valor is None else float(valor)
        estado = clasificar(h.op, valor, h.umbral)
        if h.firmeza and estado == "confirmado" and razones_eje_no_firme(con):
            estado = "no firme"
        if h.sql_estado:
            ver = con.execute(h.sql_estado).fetchall()
            estado = ESTADO_DE_VEREDICTO.get(ver[0][0] if ver else None, "no firme")
        filas.append({"id": h.id, "enunciado": h.enunciado, "valor": valor, "op": h.op,
                      "umbral": h.umbral, "estado": estado,
                      "sha_datos": sha, "firma": firma(h), "mes_datos": mes, "evaluado_en": hoy})
    return filas


def leer_ledger(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def registrar(rows, path) -> int:
    """Agrega filas al ledger, idempotente por (id, sha_datos, firma). Devuelve cuantas agrego."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existentes = leer_ledger(path)
    vistas = {(r["id"], r["sha_datos"], r.get("firma") or "") for r in existentes}
    nuevas = []
    for r in rows:
        clave = (r["id"], r["sha_datos"], r.get("firma") or "")
        if clave in vistas:
            continue
        vistas.add(clave)
        nuevas.append({c: ("" if r.get(c) is None else r.get(c)) for c in LEDGER_COLS})
    if not nuevas and path.exists():
        return 0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS, lineterminator="\n")
        w.writeheader()
        for r in existentes:
            w.writerow({c: r.get(c, "") for c in LEDGER_COLS})
        for r in nuevas:
            w.writerow(r)
    return len(nuevas)


def _fmt(v, dec=3) -> str:
    try:
        return f"{float(v):.{dec}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "s/d"


def pagina_libro(ledger_rows) -> str:
    por_id: dict[str, list[dict]] = {}
    for r in ledger_rows:
        por_id.setdefault(r["id"], []).append(r)
    for nuevo, viejo in RENOMBRADAS.items():
        por_id[nuevo] = por_id.get(viejo, []) + por_id.get(nuevo, [])
    L = ["# Libro de hallazgos", ""]
    L.append("Cada hallazgo es una hipótesis en código (`pipeline/hallazgos.py`) que se re-evalúa en cada "
             "build. El historial muestra cómo cambia el veredicto entre versiones de los datos.")
    L.append("")
    L.append("Estado: confirmado si cumple el umbral; debilitado si falla por menos del 25% del umbral; "
             "refutado si falla por más.")
    L.append("")
    L.append("Estado no firme: la hipótesis del eje (`asimetria_de_superficie`, antes `anisotropia`) cumple el umbral, pero se marca no firme si el eje no es "
             "firme según la robustez y la validación fuera de tiempo. Eso pasa si el eje no está definido en algún "
             "subconjunto de `mart_robustez_eje` (IC de 90 grados o más, o p de permutación de 0,10 o más), si el IC de la "
             "muestra completa mide 90 grados o más, o si el eje estimado con datos viejos no se separa del SHmax publicado "
             "ni de ejes al azar en `mart_validacion_holdout`, o si dispara alguna pata de la regla de parada (`mart_eje_parada`: potencia, "
             "ventana previa, exposición, bloques). Se lee de esos marts; no es un análisis nuevo. "
             "Los umbrales de las demás hipótesis no cambian.")
    L.append("")
    L.append("Estado de `hijo_depletado`: sale del veredicto de su propia regla (`pipeline/hijo.py`), no del umbral del valor. "
             "Confirmado si el veredicto es sostiene, refutado si es no se sostiene, y no firme en cualquier otro caso "
             "(ubicación, no firme o sin muestra). Su valor es el límite superior del IC del grupo muy depletado y no existe "
             "(s/d) cuando el control negativo no es nulo.")
    L.append("")
    L.append("El ledger solo agrega filas: cuando cambia la regla de una hipótesis se registra una fila nueva con la misma "
             "versión de datos y la fila anterior queda en el historial. La última fila de cada hipótesis es la vigente.")
    L.append("")
    L.append("## Estado actual")
    L.append("")
    L.append("| Hallazgo | Estado | Valor | Expectativa | Datos |")
    L.append("|---|---|---|---|---|")
    for h in HIPOTESIS:
        hist = por_id.get(h.id, [])
        if hist:
            u = hist[-1]
            L.append(f"| `{h.id}` | {u['estado']} | {_fmt(u['valor'])} | {h.op} {_fmt(h.umbral)} | "
                     f"{u['mes_datos']} ({u['sha_datos']}) |")
        else:
            L.append(f"| `{h.id}` | sin evaluar | s/d | {h.op} {_fmt(h.umbral)} | s/d |")
    L.append("")
    for h in HIPOTESIS:
        L.append(f"## {h.id}")
        L.append("")
        L.append(h.enunciado)
        L.append("")
        L.append(f"Expectativa: valor {h.op} {_fmt(h.umbral)} ({h.unidad}).")
        L.append("")
        L.append("| Datos a | Hash de datos | Valor | Estado |")
        L.append("|---|---|---|---|")
        hist = por_id.get(h.id, [])
        for r in hist:
            L.append(f"| {r['mes_datos']} | {r['sha_datos']} | {_fmt(r['valor'])} | {r['estado']} |")
        if not hist:
            L.append("| s/d | s/d | s/d | sin evaluar |")
        L.append("")
    L.append("Ver también [Interferencia entre fracturas](interferencia.md).")
    L.append("")
    return "\n".join(L)


def lint_wiki(out_dir) -> list[str]:
    """Avisos: enlaces relativos rotos y hallazgos cuyo ultimo estado es refutado."""
    out_dir = Path(out_dir)
    avisos = []
    for md in sorted(out_dir.rglob("*.md")):
        texto = md.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(texto):
            destino = m.group(1).split("#")[0]
            if not destino or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", destino):
                continue
            if not (md.parent / destino).resolve().exists():
                avisos.append(f"enlace roto en {md.relative_to(out_dir).as_posix()}: {m.group(1)}")
    ultimo = {}
    for r in leer_ledger(out_dir / "hallazgos" / "ledger.csv"):
        ultimo[r["id"]] = r
    for hid, r in sorted(ultimo.items()):
        if r["estado"] == "refutado":
            avisos.append(f"hallazgo refutado: {hid} (valor {r['valor']}, datos {r['mes_datos']})")
    return avisos
