"""La subida de la brecha del mes 1 en 2026, con una muestra de la misma antiguedad de carga en todos los anos.

Se corre despues de pipeline.carga:  uv run python -m pipeline.carga_anual

REGLA FIJADA ANTES DE CORRER (2026-11-19, antes de calcular ninguna cifra de esta prueba; no se cambia despues de ver resultados).

Pregunta: el README dice que la brecha del mes 1 llega a 44 puntos en 2026 (mart_interferencia_anual: 243 eventos cercanos en
2026; 2025 da -32 y 2022 -35). Las fracturas aparecen en el dato publico con rezago de carga, y el rezago depende del operador:
para las fracturas iniciadas de 2023 a 2025 la mediana es de 3 meses para YPF y Vista y de 14 a 23 meses para Tecpetrol, Pan
American y Shell (pipeline.carga). Los hijos de 2026 que ya se ven son entonces sobre todo de los operadores que cargan rapido, y
los vecinos de un control de 2026 pueden ser hijos que todavia no se cargaron. La cifra de 2026 puede salir de esa composicion y
no de un cambio real. Esta prueba compara los anos con el mismo criterio de visibilidad en todos.

Lo que se miro antes de fijar la regla: el perfil anual sin restringir de mart_interferencia_anual (las cifras de arriba), las
medianas de rezago por operador citadas y el primer mes de carga del dataset (2019-06). Ninguna cifra de la muestra restringida.

Muestra de antiguedad constante:
  * U = ultimo mes de carga del archivo de fracturas (max de stg_fractura.mes_carga); rezago de un hijo = meses entre
    int_frac_hijo.mes_frac e int_frac_hijo.mes_carga (los mismos que define pipeline.carga).
  * Conjunto de hijos visibles: los hijos con mes_carga conocido, 0 <= rezago <= L_CARGA (3 meses) y mes_frac <= U menos
    L_CARGA meses (un hijo iniciado despues todavia podria cargarse dentro de L_CARGA sin que se vea). Los demas hijos se tratan
    como si no existieran, en todos los anos por igual: se quitan de los pares padre e hijo antes de elegir el hijo mas cercano
    de cada evento, asi que tampoco definen bandas ni contaminan controles.
  * Eventos: los del resultado principal (pipeline.placebo.cargar y placebo.marco con la base de los meses -3 a -1, k = 1,
    EDAD_MIN y BASE_MIN sin cambios) sobre los pares que quedan. Ano del evento = ano del mes de fractura de su hijo.
  * Brecha de un grupo de eventos = mediana del indice de los cercanos (menos de 1 km) menos mediana del de los controles
    (2 a 5 km), como placebo.brecha.

Estadistico de la prueba:
  D = brecha(eventos de 2026) menos brecha(eventos de 2021 a 2024 juntos), en la muestra de antiguedad constante.
  IC 95% de D por bootstrap de percentiles por bloques de 5 km (pipeline.bloques: el bloque del pad hijo del evento), con los
  eventos de los dos periodos remuestreados juntos (un bloque se mueve con todos sus eventos), REPS = 400, SEMILLA = 20261119.

Guarda de operador: D_YPF = el mismo D con solo los eventos cuyo hijo es de YPF (operador de int_pozo_ubicacion), sin IC.

Veredicto (uno solo, sobre D):
  * sin muestra: menos de 100 eventos cercanos de 2026 con el indice del mes 1 medido, o menos de 30 bloques de 5 km en total.
  * sostiene: el limite superior del IC de D es menor que 0 (2026 peor que 2021 a 2024) y D_YPF es menor que 0 con al menos 50
    eventos cercanos de YPF en 2026. Si el IC esta bajo cero pero la guarda no se cumple (D_YPF >= 0 o menos de 50 eventos de
    YPF en 2026), el veredicto es no firme.
  * no se sostiene: el limite inferior del IC de D es mayor o igual que 0.
  * no firme: cualquier otro caso (el IC incluye el cero).

Que cambia segun el veredicto:
  * sostiene: el README y el caso de estudio mantienen que la brecha sube en 2026, con la cifra de la muestra de antiguedad
    constante y su IC en vez de 44, y una linea que dice como se controlo el rezago de carga.
  * cualquier otro: la frase "llega a 44 puntos en 2026" sale del README (en castellano y en ingles) y del caso de estudio, y la
    operacion interferencia_anual del agente avisa "ano con carga incompleta" cuando la completitud estimada del ultimo mes del
    ano (pipeline.carga) es menor que 0,80.
  En los dos casos se agrega la hipotesis anio_2026_carga al libro (expectativa: limite superior del IC de D menor que 0).

Descriptivo, sin veredicto (se publica todo, favorable o no): el perfil anual 2019 a 2026 de la muestra de antiguedad constante
con IC por bloques de 5 km y el mismo perfil sin restringir (debe reproducir mart_interferencia_anual), D con 2025 y 2026
juntos, y la cantidad de eventos y bloques de cada ano.

Que NO prueba:
  * La muestra restringida ve solo a los hijos de carga rapida: dice si la subida existe entre esos hijos, no en toda la cuenca.
  * Un hijo de carga tardia sigue existiendo en el terreno: un control puede estar cerca de uno sin que se vea, en todos los
    anos por igual. La prueba iguala esa contaminacion entre anos; no la quita.
"""
# Nota posterior a la corrida (2026-11-19; la regla de arriba no se toca). Las medianas de rezago que cita la regla salieron de
# una consulta hecha antes de que existiera pipeline.carga, sobre las fracturas iniciadas de 2023 a 2025, que todavia se estan
# cargando. La pagina de pipeline.carga publica las de las cohortes maduras (24 meses o mas): esas son las que se citan.
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np

from pipeline import bloques, carga, placebo
from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.ingest import DATA, ROOT

L_CARGA = 3            # meses: rezago maximo de carga para que un hijo cuente como visible
ANIO_PRUEBA = 2026
ANIOS_BASE = (2021, 2022, 2023, 2024)
MIN_CERCANOS = 100     # eventos cercanos de 2026 con el mes 1 medido
MIN_BLOQUES = 30       # bloques de 5 km en total
MIN_YPF = 50           # eventos cercanos de YPF en 2026 para la guarda de operador
REPS = 400
SEMILLA = 20261119
TOL_REPRODUCE = 1e-9   # diferencia de brecha admitida al comparar la muestra completa con mart_interferencia_anual

RUTA_PAGINA = ROOT / "wiki" / "hallazgos" / "carga_anual.md"

# Que cambia segun el veredicto, como lo fija la regla del docstring (texto de la pagina)
SI_SOSTIENE = ("El README y el caso de estudio mantienen que la brecha sube en 2026, con la cifra de la muestra de antigüedad "
               "constante y su IC, y dicen cómo se controló el rezago de carga.")
SI_NO = ("La frase que decía que la brecha del mes 1 llega a 44 puntos en 2026 sale del README y del caso de estudio, y la "
         "operación interferencia_anual del agente avisa cuando el año consultado tiene carga incompleta (completitud estimada "
         "del último mes del año menor que 0,80, según pipeline.carga). El perfil por año se sigue publicando como dato.")

COLS_MART = [("muestra", "VARCHAR"), ("anio", "INTEGER"), ("hijos", "INTEGER"), ("eventos_cercanos", "INTEGER"),
             ("eventos_control", "INTEGER"), ("bloques_5km", "INTEGER"), ("brecha", "DOUBLE"), ("ic_bajo", "DOUBLE"),
             ("ic_alto", "DOUBLE")]
COLS_PRUEBA = [("estadistico", "VARCHAR"), ("d", "DOUBLE"), ("ic_bajo", "DOUBLE"), ("ic_alto", "DOUBLE"),
               ("n_cercanos", "INTEGER"), ("n_bloques", "INTEGER"), ("d_ypf", "DOUBLE"), ("n_ypf", "INTEGER"),
               ("veredicto", "VARCHAR"), ("reps_validas", "INTEGER")]


def visibles(con: duckdb.DuckDBPyConnection, hijo_id: np.ndarray) -> np.ndarray:
    """Hijos visibles (carga rapida y ventana completa), un bool por hijo alineado con hijo_id."""
    _, u = carga.limites(con)
    tope = carga._mas_meses(u, -L_CARGA)
    filas = con.execute("select h.hijo, h.mes_frac::date, h.mes_carga::date from int_frac_hijo h "
                        "order by h.hijo").fetchall()
    assert [int(r[0]) for r in filas] == [int(v) for v in hijo_id]
    out = np.zeros(len(filas), dtype=bool)
    for i, (_, mes_frac, mes_carga) in enumerate(filas):
        if mes_carga is None:
            continue
        rezago = (mes_carga.year - mes_frac.year) * 12 + mes_carga.month - mes_frac.month
        if 0 <= rezago <= L_CARGA and mes_frac <= tope:
            out[i] = True
    return out


def restringir(D: dict, visible: np.ndarray) -> dict:
    """Copia de D sin los pares cuyo hijo no es visible; los hijos no se renumeran."""
    keep = visible[D["par_hijo"]]
    out = dict(D)
    for k in [k for k in D if k.startswith("par_")]:
        out[k] = D[k][keep]
    return out


def eventos(D: dict, operador_hijo: np.ndarray) -> dict:
    """Eventos del resultado principal sobre D, con ano, bloque de 5 km y marca de YPF por evento."""
    m = placebo.marco(D, D["hijo_mes"], ks=(1,), base=placebo.BASE_ORIGINAL)
    return {"idx": m["idx"][1], "banda": m["banda"], "anio": D["hijo_anio"][m["hijo"]],
            "bloque": bloques.claves(D, m["clave"])["5km"], "hijo": m["hijo"],
            "ypf": operador_hijo[m["hijo"]] == "YPF"}


def diferencia(ev: dict, anios_prueba: tuple[int, ...], sel: np.ndarray | None = None) -> float:
    """Brecha de los anos de prueba menos brecha de ANIOS_BASE, con el mes 1 medido y banda 0 o 2."""
    ok = ~np.isnan(ev["idx"]) & ((ev["banda"] == 0) | (ev["banda"] == 2))
    if sel is not None:
        ok = ok & sel
    p = ok & np.isin(ev["anio"], list(anios_prueba))
    b = ok & np.isin(ev["anio"], list(ANIOS_BASE))
    g_p = placebo.brecha(ev["idx"][p], ev["banda"][p])[2]
    g_b = placebo.brecha(ev["idx"][b], ev["banda"][b])[2]
    return g_p - g_b


def diferencia_ic(ev: dict, anios_prueba: tuple[int, ...], reps: int = REPS, semilla: int = SEMILLA) -> dict:
    """D con IC 95% por bootstrap de percentiles por bloques de 5 km, remuestreando los dos periodos juntos.

    reps_validas cuenta las remuestras con D definido: una remuestra en la que un periodo queda sin cercanos o sin
    controles no tiene D, no entra en los percentiles y se publica cuantas fueron."""
    ok = ~np.isnan(ev["idx"]) & ((ev["banda"] == 0) | (ev["banda"] == 2))
    en_prueba = np.isin(ev["anio"], list(anios_prueba))
    en_base = np.isin(ev["anio"], list(ANIOS_BASE))
    ambos = ok & (en_prueba | en_base)
    d = diferencia(ev, anios_prueba)
    out = {"d": d, "ic_bajo": float("nan"), "ic_alto": float("nan"),
           "n_cercanos": int((ok & en_prueba & (ev["banda"] == 0)).sum()),
           "n_bloques": int(len(np.unique(ev["bloque"][ambos]))), "reps_validas": 0}
    if int(ambos.sum()) == 0:
        return out
    grupos = _clusters(ev["bloque"][ambos])
    if not grupos:
        return out
    v, b, a = ev["idx"][ambos], ev["banda"][ambos], ev["anio"][ambos]
    rng = np.random.default_rng(semilla)
    ds = []
    for _ in range(reps):
        i = _remuestra(rng, grupos)
        ds.append(diferencia({"idx": v[i], "banda": b[i], "anio": a[i]}, anios_prueba))
    ds = np.array(ds)
    ds = ds[~np.isnan(ds)]
    out["reps_validas"] = int(len(ds))
    if len(ds):
        out["ic_bajo"], out["ic_alto"] = (float(x) for x in np.percentile(ds, [2.5, 97.5]))
    return out


def veredicto(d: float, ic_bajo: float, ic_alto: float, n_cercanos: int, n_bloques: int, d_ypf: float,
              n_ypf: int) -> str:
    """Un veredicto sobre D, en el orden de la regla."""
    if n_cercanos < MIN_CERCANOS or n_bloques < MIN_BLOQUES:
        return "sin muestra"
    if ic_alto < 0:
        return "sostiene" if d_ypf < 0 and n_ypf >= MIN_YPF else "no firme"
    if ic_bajo >= 0:
        return "no se sostiene"
    return "no firme"


def perfil(ev: dict, reps: int = REPS, semilla: int = SEMILLA) -> list[tuple]:
    """Por ano 2019 a 2026: hijos con eventos, cercanos, controles, bloques de 5 km, brecha y su IC."""
    out = []
    for anio in range(2019, 2027):
        sel = ev["anio"] == anio
        r = placebo.brecha_ic(ev["idx"][sel], ev["banda"][sel], ev["bloque"][sel], reps, semilla)
        out.append((anio, len(np.unique(ev["hijo"][sel])), r["n_near"], r["n_ctrl"],
                    len(np.unique(ev["bloque"][sel])), r["brecha"], r["ic_bajo"], r["ic_alto"]))
    return out


def _puntos(x) -> str:
    """Indice por 100 en formato espanol, o n/d si falta."""
    if x is None or np.isnan(x):
        return "n/d"
    return carga._num(100 * x)


def _falta(x) -> bool:
    """Falta el dato (None o nan)."""
    return x is None or (isinstance(x, float) and np.isnan(x))


def pagina(ver: str, r: dict, d_ypf: float, n_ypf: int, r_pool: dict, p_const: list[tuple], p_comp: list[tuple],
           reproduce: bool, reps: int = REPS) -> str:
    """Pagina de la prueba en markdown."""
    L = ["# La subida de 2026 con la misma antigüedad de carga", "",
         "Se prueba si la brecha del mes 1 de 2026 sigue mayor que la de 2021 a 2024 cuando todos los años se miran "
         "con el mismo criterio de visibilidad de carga: hijos con rezago de 0 a 3 meses e inicio hasta U menos 3 "
         "meses, y eventos del resultado principal sobre los pares que quedan. La regla de esta prueba se fijó antes "
         "de calcular ninguna cifra (ver el docstring de pipeline/carga_anual.py) y no se cambió después de ver "
         "resultados.", "",
         "## Veredicto", "",
         f"**{ver}**.", "",
         f"D (brecha de 2026 menos brecha de 2021 a 2024, muestra de antigüedad constante): {_puntos(r['d'])} "
         f"puntos, IC 95 % [{_puntos(r['ic_bajo'])}, {_puntos(r['ic_alto'])}].", "",
         f"Eventos cercanos de 2026 con el mes 1 medido: {r['n_cercanos']}. Bloques de 5 km en total: "
         f"{r['n_bloques']}.", "",
         f"Remuestras del bootstrap con D definido: {r['reps_validas']} de {reps}. El IC sale de los percentiles de "
         "esas; una remuestra en la que un período queda sin cercanos o sin controles no tiene D y no entra.", "",
         f"Guarda de operador: D_YPF = {_puntos(d_ypf)} puntos con {n_ypf} eventos cercanos de YPF en 2026.", "",
         "## Qué cambia con este veredicto", "",
         SI_SOSTIENE if ver == "sostiene" else SI_NO, "",
         "En los dos casos la hipótesis anio_2026_carga queda en el libro de hallazgos (expectativa: límite superior del IC "
         "de D menor que 0).", "",
         "## Perfil anual", "",
         "Brecha del mes 1 por año en puntos (índice por 100), con IC 95 % por bloques de 5 km.", "",
         "| Año | Muestra | Hijos | Cercanos | Controles | Bloques 5 km | Brecha | IC bajo | IC alto |",
         "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for muestra, perf in (("constante", p_const), ("completa", p_comp)):
        for a, hijos, n0, n2, nb, b, lo, hi in perf:
            L.append(f"| {a} | {muestra} | {hijos} | {n0} | {n2} | {nb} | {_puntos(b)} | {_puntos(lo)} | "
                     f"{_puntos(hi)} |")
    L += ["", "## Descriptivo", "",
          f"D con 2025 y 2026 juntos: {_puntos(r_pool['d'])} puntos, IC 95 % [{_puntos(r_pool['ic_bajo'])}, "
          f"{_puntos(r_pool['ic_alto'])}] ({r_pool['n_cercanos']} cercanos, {r_pool['n_bloques']} bloques, "
          f"{r_pool['reps_validas']} de {reps} remuestras con D definido).", "",
          f"La muestra completa reproduce mart_interferencia_anual 2019 a 2026: {'sí' if reproduce else 'no'} "
          "(misma cantidad de eventos cercanos y la misma brecha en cada año, con una tolerancia de 1e-9 en el índice).", "",
          "## Qué no prueba", "",
          "- La muestra restringida ve solo a los hijos de carga rápida: dice si la subida existe entre esos hijos, "
          "no en toda la cuenca.",
          "- Un hijo de carga tardía sigue existiendo en el terreno: un control puede estar cerca de uno sin que se "
          "vea, en todos los años por igual. La prueba iguala esa contaminación entre años; no la quita.", ""]
    texto = "\n".join(L)
    for raya in (chr(0x2013), chr(0x2014)):
        if raya in texto:
            raise ValueError(f"el texto generado no puede contener {raya!r}")
    return texto


def main(path: Path = DATA / "warehouse.duckdb", pagina_md: Path | None = RUTA_PAGINA) -> None:
    con = duckdb.connect(str(path))
    n_carga = con.execute("select count(*) from int_frac_hijo where mes_carga is not null").fetchall()[0][0]
    if n_carga == 0:
        print("[carga_anual] sin datos de mes_carga: no se escribe nada")
        con.close()
        return
    D = bloques.cargar(con)
    filas = con.execute("select h.hijo, coalesce(u.operador, 'sin dato') from int_frac_hijo h "
                        "left join int_pozo_ubicacion u on u.pozo_id = h.hijo order by h.hijo").fetchall()
    assert [int(r[0]) for r in filas] == [int(v) for v in D["hijo_id"]]
    operador_hijo = np.array([r[1] for r in filas])
    constante = eventos(restringir(D, visibles(con, D["hijo_id"])), operador_hijo)
    completa = eventos(D, operador_hijo)
    if len(completa["idx"]) == 0:
        print("[carga_anual] sin eventos: no se escribe nada")
        con.close()
        return
    r = diferencia_ic(constante, (ANIO_PRUEBA,))
    d_ypf = diferencia(constante, (ANIO_PRUEBA,), sel=constante["ypf"])
    n_ypf = int(((constante["anio"] == ANIO_PRUEBA) & (constante["banda"] == 0) & ~np.isnan(constante["idx"])
                 & constante["ypf"]).sum())
    ver = veredicto(r["d"], r["ic_bajo"], r["ic_alto"], r["n_cercanos"], r["n_bloques"], d_ypf, n_ypf)
    r_pool = diferencia_ic(constante, (2025, 2026))
    p_const, p_comp = perfil(constante), perfil(completa)
    try:
        mart = {a: (n, b) for a, n, b in
                con.execute("select anio, eventos_cercanos, brecha_mes_1 from mart_interferencia_anual").fetchall()}
    except duckdb.CatalogException:   # warehouse sin ese mart (una muestra parcial): no hay contra que comparar
        mart = {}
    reproduce, max_dif = True, 0.0
    for a, _, n0, _, _, b, _, _ in p_comp:
        mn, mb = mart.get(a, (None, None))
        if mn != n0:
            reproduce = False
        if _falta(b) or _falta(mb):
            if _falta(b) != _falta(mb):
                reproduce = False
        else:
            dif = abs(b - mb)
            max_dif = max(max_dif, dif)
            if dif > TOL_REPRODUCE:
                reproduce = False
    _escribir(con, "mart_carga_anual", COLS_MART,
              [("constante",) + f for f in p_const] + [("completa",) + f for f in p_comp])
    _escribir(con, "mart_carga_anual_prueba", COLS_PRUEBA,
              [("2026", r["d"], r["ic_bajo"], r["ic_alto"], r["n_cercanos"], r["n_bloques"], d_ypf, n_ypf, ver,
                r["reps_validas"]),
               ("2025_2026", r_pool["d"], r_pool["ic_bajo"], r_pool["ic_alto"], r_pool["n_cercanos"],
                r_pool["n_bloques"], None, None, None, r_pool["reps_validas"])])
    print(f"[carga_anual] prueba_2026 d={r['d']:.4f} ic=[{r['ic_bajo']:.4f}, {r['ic_alto']:.4f}] "
          f"n_cercanos={r['n_cercanos']} n_bloques={r['n_bloques']} d_ypf={d_ypf:.4f} n_ypf={n_ypf} veredicto={ver} "
          f"reps_validas={r['reps_validas']}")
    print(f"[carga_anual] descriptivo_2025_2026 d={r_pool['d']:.4f} ic=[{r_pool['ic_bajo']:.4f}, "
          f"{r_pool['ic_alto']:.4f}] n_cercanos={r_pool['n_cercanos']} n_bloques={r_pool['n_bloques']} "
          f"reps_validas={r_pool['reps_validas']}")
    print(f"[carga_anual] reproduce={reproduce} max_dif={max_dif:.2e}")
    for muestra, perf in (("constante", p_const), ("completa", p_comp)):
        for a, hijos, n0, n2, nb, b, lo, hi in perf:
            print(f"[carga_anual] perfil {muestra} {a} hijos={hijos} cercanos={n0} controles={n2} bloques={nb} "
                  f"brecha={b:.4f} ic=[{lo:.4f}, {hi:.4f}]")
    if pagina_md is not None:
        pagina_md.parent.mkdir(parents=True, exist_ok=True)
        pagina_md.write_text(pagina(ver, r, d_ypf, n_ypf, r_pool, p_const, p_comp, reproduce), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
