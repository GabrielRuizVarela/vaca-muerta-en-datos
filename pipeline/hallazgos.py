"""Libro de hallazgos: hipotesis en codigo, re-evaluadas en cada build.

Cada hipotesis tiene una consulta SQL que devuelve un numero, una expectativa
con umbral y un estado (confirmado / debilitado / refutado). Las evaluaciones
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

LEDGER_COLS = ["id", "sha_datos", "firma", "mes_datos", "valor", "op", "umbral", "estado", "evaluado_en"]
DEBIL_FRAC = 0.25
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


@dataclass(frozen=True)
class Hipotesis:
    id: str
    enunciado: str
    sql: str
    op: str  # '<', '>' o 'abs<'
    umbral: float
    unidad: str


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
    Hipotesis("anisotropia",
              "Entre eventos cercanos a 0,3 a 1 km, el eje de 56,25 a 101,25 grados pierde más "
              "producción al mes 1 que el eje de 0 +/- 22,5 grados (diferencia de medianas del índice).",
              _SQL_ANISOTROPIA, "<", -0.10, "índice"),
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
    return hashlib.sha256(f"{h.sql}|{h.op}|{h.umbral}".encode()).hexdigest()[:8]


def evaluar(con, manifest, hoy: str | None = None) -> list[dict]:
    sha = sha_produccion(manifest)
    mes = _mes_datos(con)
    hoy = hoy or date.today().isoformat()
    filas = []
    for h in HIPOTESIS:
        r = con.execute(h.sql).fetchall()
        valor = r[0][0] if r else None
        valor = None if valor is None else float(valor)
        filas.append({"id": h.id, "enunciado": h.enunciado, "valor": valor, "op": h.op,
                      "umbral": h.umbral, "estado": clasificar(h.op, valor, h.umbral),
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
    L = ["# Libro de hallazgos", ""]
    L.append("Cada hallazgo es una hipótesis en código (`pipeline/hallazgos.py`) que se re-evalúa en cada "
             "build. El historial muestra cómo cambia el veredicto entre versiones de los datos.")
    L.append("")
    L.append("Estado: confirmado si cumple el umbral; debilitado si falla por menos del 25% del umbral; "
             "refutado si falla por más.")
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
