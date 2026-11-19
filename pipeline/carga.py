"""Rezago de carga de las fracturas: cuando aparece cada fractura en el dato publico. Descriptivo, sin veredicto.

Se corre despues de pipeline.build:  uv run python -m pipeline.carga

DEFINICIONES (escritas antes de calcular):
- U = max(mes_carga) en stg_fractura: la edicion (vintage) del archivo de fracturas. P0 = min(mes_carga): el comienzo de la carga
  (junio de 2019 en el dato actual). mes_carga es el mes en que el operador cargo el registro, no cuando informo la produccion.
- rezago = datediff('month', mes_frac, mes_carga) sobre las filas de int_frac_hijo con mes_carga no nulo. mes_carga de cada hijo es
  el del trabajo de fractura que fija mes_frac. Desempate agregado en la revision del codigo, despues de la primera corrida: si
  ese trabajo figura cargado mas de una vez vale la primera carga (con el dato del 2026-11-15 cambia el rezago de 2 hijos), y si no tiene mes de carga
  el hijo queda sin rezago.
- carga_inicial: mes_frac < P0. Son fracturas anteriores al comienzo de la carga, cargadas de golpe despues: quedan fuera de toda
  estadistica de rezago. Un rezago < 0 (carga antes del inicio) se cuenta y se muestra, pero queda fuera de la curva.
- Cohortes maduras: mes_frac entre P0 y U menos 24 meses. Curva F(L) = proporcion de los hijos de las cohortes maduras (con
  rezago >= 0) cuyo rezago es <= L, para L = 0..24; el denominador son todos los hijos de las cohortes maduras con rezago >= 0.
  Es una aproximacion: las cargas posteriores a lo observado no se ven, asi que F es una cota superior de la completitud real.
- completitud_estimada de un mes de inicio m = F(min(U - m en meses, 24)). UMBRAL = 0,80: un mes de inicio con completitud_estimada
  menor que 0,80 es "carga incompleta".

Salidas: mart_carga_curva, mart_carga_fracturas, mart_carga_operador y wiki/hallazgos/carga_fracturas.md. En los marts, pct_* va de
0 a 100; en las funciones, las proporciones van de 0 a 1.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from pipeline.costo import _escribir
from pipeline.ingest import DATA, ROOT

RUTA_PAGINA = ROOT / "wiki" / "hallazgos" / "carga_fracturas.md"
UMBRAL = 0.80
MESES_MADURA = 24
MIN_HIJOS_OPERADOR = 30
L_PAGINA = (0, 1, 2, 3, 6, 12, 18, 24)

_BASE = ("select i.hijo, i.mes_frac::date as mes_frac, coalesce(u.operador, 'sin dato') as operador, "
         "datediff('month', i.mes_frac, i.mes_carga) as rezago "
         "from int_frac_hijo i left join int_pozo_ubicacion u on u.pozo_id = i.hijo where i.mes_carga is not null")


def _mas_meses(d: date, n: int) -> date:
    m = d.year * 12 + d.month - 1 + n
    return date(m // 12, m % 12 + 1, 1)


def _entre_meses(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + b.month - a.month


def limites(con) -> tuple[date | None, date | None]:
    """(P0, U): primer y ultimo mes de carga de stg_fractura."""
    p0, u = con.execute("select min(mes_carga), max(mes_carga) from stg_fractura").fetchall()[0]
    return p0, u


def _tope_maduras(con) -> tuple[date, date] | None:
    p0, u = limites(con)
    if p0 is None or u is None:
        return None
    return p0, _mas_meses(u, -MESES_MADURA)


def curva(con) -> list[tuple[int, float]]:
    """F(L) para L = 0..24 sobre las cohortes maduras; lista vacia si no hay hijos maduros."""
    lim = _tope_maduras(con)
    if lim is None:
        return []
    cuentas = dict(con.execute(
        f"select rezago, count(*) from ({_BASE}) where rezago >= 0 and mes_frac between ? and ? group by 1",
        list(lim)).fetchall())
    total = sum(cuentas.values())
    if total == 0:
        return []
    acum, out = 0, []
    for L in range(MESES_MADURA + 1):
        acum += cuentas.get(L, 0)
        out.append((L, acum / total))
    return out


def _f(cur: list[tuple[int, float]], meses_obs: int) -> float:
    return cur[min(max(meses_obs, 0), MESES_MADURA)][1]


def meses_incompletos(con) -> list[dict]:
    """Un dict por mes de inicio entre P0 y U: mes_frac, hijos_cargados, completitud_estimada (todos, no solo los incompletos)."""
    cur = curva(con)
    p0, u = limites(con)
    if not cur:
        return []
    cargados = dict(con.execute(
        f"select mes_frac, count(*) from ({_BASE}) where mes_frac between ? and ? group by 1", [p0, u]).fetchall())
    out = []
    for i in range(_entre_meses(p0, u) + 1):
        m = _mas_meses(p0, i)
        out.append({"mes_frac": m, "hijos_cargados": cargados.get(m, 0),
                    "completitud_estimada": _f(cur, _entre_meses(m, u))})
    return out


def completitud_anio(con, anio: int) -> float | None:
    """completitud_estimada del ultimo mes de inicio del ano (tope U); None si el ano queda fuera de P0..U o no hay curva."""
    cur = curva(con)
    p0, u = limites(con)
    if not cur:
        return None
    m = min(date(anio, 12, 1), u)
    if m.year != anio or m < p0:
        return None
    return _f(cur, _entre_meses(m, u))


def _fracturas(con, cur, p0, u) -> list[tuple]:
    filas = con.execute(
        f"select mes_frac, operador, count(*), median(rezago) filter (where rezago >= 0 and mes_frac >= ?) "
        f"from ({_BASE}) group by 1, 2 order by 1, 2", [p0]).fetchall()
    out = []
    for mes, op, n, med in filas:
        obs = _entre_meses(mes, u)
        ini = mes < p0
        out.append((mes, op, n, None if ini else med, obs, None if ini else _f(cur, obs), obs < MESES_MADURA, ini))
    return out


def _operadores(con, lim) -> list[tuple]:
    return con.execute(
        f"select operador, count(*), median(rezago), 100.0 * avg((rezago <= 3)::int), 100.0 * avg((rezago <= 12)::int) "
        f"from ({_BASE}) where rezago >= 0 and mes_frac between ? and ? "
        f"group by 1 having count(*) >= {MIN_HIJOS_OPERADOR} order by 2 desc, 1", list(lim)).fetchall()


def _anios(con, cur, p0, u) -> list[tuple]:
    filas = con.execute(
        f"select year(mes_frac), count(*), median(rezago) filter (where rezago >= 0), "
        f"100.0 * avg((rezago <= 3)::int) filter (where rezago >= 0) "
        f"from ({_BASE}) where mes_frac between ? and ? group by 1 order by 1", [p0, u]).fetchall()
    return [(a, n, med, p3, completitud_anio(con, a)) for a, n, med, p3 in filas]


def _num(x, d: int = 1) -> str:
    return "n/d" if x is None else f"{x:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _pct(x: float | None, d: int = 1) -> str:
    return "n/d" if x is None else _num(100 * x, d) + " %"


def pagina(cur, ops, anios, inc, u, p0, n_neg, n_ini) -> str:
    F = dict(cur)
    L = ["# Rezago de carga de las fracturas", "",
         "Descriptivo, sin veredicto: este análisis mide cuánto tarda cada fractura en aparecer en el dato público de fracturas "
         "(Adjunto IV), contando desde el mes en que empezó hasta el mes en que el operador cargó el registro. No evalúa si el "
         "rezago es razonable ni lo atribuye a una causa, y no cambia ningún otro resultado del repositorio.", "",
         f"Edición del archivo de fracturas (U, último mes de carga): {u.strftime('%Y-%m')}. La carga empieza en "
         f"{p0.strftime('%Y-%m')} (P0); las {_num(n_ini, 0)} fracturas de hijos que empezaron antes se cargaron de golpe después y "
         f"quedan fuera de toda estadística de rezago. Hay {_num(n_neg, 0)} hijos con carga anterior al inicio: se "
         "cuentan aquí y quedan fuera de la curva.", "",
         "## Curva de carga", "",
         f"Proporción de los hijos de cohortes maduras (inicio entre {p0.strftime('%Y-%m')} y "
         f"{_mas_meses(u, -MESES_MADURA).strftime('%Y-%m')}) ya cargados a L meses del inicio. Es una cota superior de la "
         "completitud real: las cargas posteriores a lo observado no se ven.", "",
         "| L (meses) | Cargados hasta L |", "| ---: | ---: |"]
    for k in L_PAGINA:
        L.append(f"| {k} | {_pct(F[k])} |")
    L += ["", "## Por operador", "",
          f"Hijos de cohortes maduras con al menos {MIN_HIJOS_OPERADOR} hijos por operador. El rezago está en meses.", "",
          "| Operador | Hijos | Rezago mediano | Cargados en 3 meses | Cargados en 12 meses |", "| --- | ---: | ---: | ---: | ---: |"]
    for op, n, med, p3, p12 in ops:
        L.append(f"| {op} | {_num(n, 0)} | {_num(med)} | {_num(p3)} % | {_num(p12)} % |")
    L += ["", "## Por año de inicio", "",
          "Incluye todos los hijos con carga desde P0, también los de cohortes que todavía no maduraron, así que los años "
          "recientes subestiman el rezago. La completitud estimada es la del último mes del año (con tope en U).", "",
          "| Año | Hijos con carga | Rezago mediano (meses) | Cargados en 3 meses | Completitud estimada |",
          "| ---: | ---: | ---: | ---: | ---: |"]
    for a, n, med, p3, comp in anios:
        L.append(f"| {a} | {_num(n, 0)} | {_num(med)} | {_num(p3)} % | {_pct(comp)} |")
    L += ["", "## Meses de inicio con carga incompleta", "",
          f"Meses de inicio con completitud estimada menor que {_num(UMBRAL, 2)}.", ""]
    if inc:
        L += ["| Mes de inicio | Hijos cargados | Completitud estimada |", "| --- | ---: | ---: |"]
        for m in inc:
            L.append(f"| {m['mes_frac'].strftime('%Y-%m')} | {_num(m['hijos_cargados'], 0)} | {_pct(m['completitud_estimada'])} |")
    else:
        L.append("Ninguno.")
    L += ["", "## Límites", "",
          "- F es una cota superior de la completitud real: lo que se carga después de U no está en el archivo.",
          "- Una sola curva para todos los operadores, aunque el rezago difiere mucho por operador.",
          "- El mes de carga es cuando se cargó el registro, no cuando se informó la producción.", ""]
    texto = "\n".join(L)
    for raya in (chr(0x2013), chr(0x2014)):
        if raya in texto:
            raise ValueError(f"el texto generado no puede contener {raya!r}")
    return texto


COLS_CURVA = [("rezago", "INTEGER"), ("pct_acumulado", "DOUBLE")]
COLS_FRAC = [("mes_frac", "DATE"), ("operador", "VARCHAR"), ("hijos", "BIGINT"), ("rezago_mediana_meses", "DOUBLE"),
             ("rezago_max_observable", "INTEGER"), ("completitud_estimada", "DOUBLE"), ("censurado", "BOOLEAN"),
             ("carga_inicial", "BOOLEAN")]
COLS_OP = [("operador", "VARCHAR"), ("hijos", "BIGINT"), ("rezago_mediana_meses", "DOUBLE"), ("pct_3m", "DOUBLE"),
           ("pct_12m", "DOUBLE")]


def main(path=DATA / "warehouse.duckdb", pagina_md: Path | None = RUTA_PAGINA) -> None:
    con = duckdb.connect(str(path))
    cur = curva(con)
    lim = _tope_maduras(con)
    if not cur or lim is None:
        print("[carga] sin cohortes maduras: no se escribe nada")
        con.close()
        return
    p0, u = limites(con)
    _escribir(con, "mart_carga_curva", COLS_CURVA, [(k, 100 * v) for k, v in cur])
    _escribir(con, "mart_carga_fracturas", COLS_FRAC, _fracturas(con, cur, p0, u))
    ops = _operadores(con, lim)
    _escribir(con, "mart_carga_operador", COLS_OP, ops)
    inc = [m for m in meses_incompletos(con) if m["completitud_estimada"] < UMBRAL]
    n_neg = con.execute(f"select count(*) from ({_BASE}) where rezago < 0 and mes_frac >= ?", [p0]).fetchall()[0][0]
    n_ini = con.execute(f"select count(*) from ({_BASE}) where mes_frac < ?", [p0]).fetchall()[0][0]
    print(f"[carga] U={u} P0={p0} carga_inicial={n_ini} rezago_negativo={n_neg} meses_incompletos={len(inc)}")
    print("[carga] curva", [(k, round(v, 3)) for k, v in cur if k in L_PAGINA])
    for r in ops:
        print("[carga] operador", tuple(round(x, 2) if isinstance(x, float) else x for x in r))
    if pagina_md is not None:
        pagina_md.parent.mkdir(parents=True, exist_ok=True)
        pagina_md.write_text(pagina(cur, ops, _anios(con, cur, p0, u), inc, u, p0, n_neg, n_ini), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
