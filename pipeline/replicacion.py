"""Replicacion en el Colorado (cuenca DJ): el estudio de eventos de la interferencia, sin cambios, sobre el warehouse del Colorado.

Pivote P5 de la fase 4, tramo P5b. P5a (pipeline/colorado) bajo los datos y armo las tablas base; este tramo corre los estimadores
del proyecto (pipeline/placebo.py: `cargar`, `marco`, `brecha_ic`; clave de bloque de pipeline/bloques.py) contra ese warehouse y
publica la lectura de la replicacion, sea cual sea.

    uv run python -m pipeline.replicacion    # escribe mart_replicacion_* en data/colorado/warehouse.duckdb

REGLA FIJADA ANTES DE CORRER (2026-11-15, antes de calcular ninguna cifra de brecha del Colorado; no se cambia despues de ver
resultados; se publican todos los resultados, favorables o no). Hipotesis `replicacion_colorado` del libro de hallazgos.

Lectura de la replicacion (la misma fijada en pipeline/colorado/__init__.py):
  * "se replica" si la brecha del mes 1 (mediana del indice de los padres cercanos menos la de los controles, base de los meses
    -3 a -1, padres a menos de 1 km, controles de 2 a 5 km, los mismos filtros de P5a: padres horizontales con primer petroleo al
    menos 6 meses antes de la fractura y caudal base mayor que 1 m3/d) es negativa con un IC 95% que excluye cero (limite superior
    menor que 0) Y la brecha previa a la fractura con base limpia (mes -1, base de los meses -6 a -4) es menor, en valor absoluto,
    que la brecha del mes 1. Si no, "no se replica". Se publican las dos lecturas.
  * Valor de la hipotesis = max(limite superior del IC, |brecha previa limpia| - |brecha del mes 1|); se replica si es < 0.
    Un IC indefinido (menos de 5 eventos cercanos o de 5 controles) cuenta como "no se replica".

Intervalos (afinado en P5b, antes de ver numeros; P5a nombraba el IC por pads):
  * Se publican los dos, lado a lado: bootstrap de percentiles 95% (2,5 y 97,5), REPS_BOOT repeticiones, por pads hijo (el
    de placebo.py) y por bloques espaciales de 5 km (remuestrear celdas completas, con la clave `bloques.clave_bloque` sobre el
    promedio de lat y lon de los pozos del pad hijo; la proyeccion usa el origen de Vaca Muerta de bloques.py sin recentrarlo:
    la grilla es una particion fija y 5 km quedan en 5 km a menos de 3% en x). Misma semilla por k que bloques.py
    (SEMILLA_PLACEBO + 100 + posicion de k en KS_PRE), asi que la unica diferencia es la unidad que se remuestrea.
  * La lectura usa el IC por bloques de 5 km (el mas ancho esperado, porque pads vecinos comparten geologia y programa); si el
    de pads fuera mas ancho, la lectura sigue usando el de bloques. Columna `ic_alto_bloque` de la tabla del veredicto.

Resultados secundarios, descriptivos (no son veredictos; se publican todos):
  * Placebo con la fecha de fractura de los hijos corrida +12 y -12 meses (la maquina de placebo.tabla_fechas; IC por pads).
  * Brecha del mes 6 (base -3 a -1) y la pretendencia limpia en k = -3, -2, -1 (base -6 a -4), con los dos IC.
  * Recuentos: eventos, padres, controles, pads hijo y bloques de 5 km.

Un solo corte de robustez para los dos riesgos de la memoria de factibilidad, sin veredicto adicional (tres filas, la principal
y una por riesgo): (1) padres horizontales (el corte principal) frente a todos los padres, con la misma regla de pozo por pozo;
(2) caudal por dia calendario (el principal: petroleo del mes sobre los dias del mes) frente a caudal por dia producido
(petroleo del mes sobre sus dias efectivos; un mes con cero dias efectivos queda sin dato y no entra en medianas ni bases).

Que NO es: Colorado y Vaca Muerta difieren en convencion de reporte (una fila por formacion; los cierres aparecen como cero dias),
en fechas (formulario de divulgacion frente a mes calendario), en la poblacion (muchos padres verticales) y no hay etapas ni arena;
la lateral va por proxy (MD menos TVD). Ninguna cifra es una afirmacion causal ni una estimacion conjunta con Vaca Muerta: la
lectura dice si la huella de la brecha aparece tambien en otra cuenca (validez externa de la huella), no cuanto vale en general.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np

from pipeline import bloques, placebo
from pipeline.cuencas import COLORADO, Cuenca, cuenca as _cuenca
from pipeline.costo import _escribir
from pipeline.ingest import ROOT
from pipeline.placebo import KS_PRE, REPS_BOOT, SEMILLA_PLACEBO

# Reglas numericas (las usa este modulo; cambiarlas despues de ver resultados rompe la preregistracion).
KM_BLOQUE = 5.0                 # lado de la celda del IC por bloques
K_VEREDICTO = 1                 # mes de la brecha del veredicto
BASE_VEREDICTO = (-3, -1)       # base del indice del mes 1
BASE_PREVIA = (-6, -4)          # base limpia de la pretendencia
K_PREVIO = -1                   # mes de la brecha previa del veredicto
K_SECUNDARIOS = (6,)            # brecha del mes 6 con la base original
DESPLAZAMIENTOS_PLACEBO = (-12, 12)

DB = COLORADO.db
CORTES = ("principal", "todos_los_padres", "por_dia_producido")

COLS_VEREDICTO = [
    ("k", "integer"), ("n_cercanos", "integer"), ("n_controles", "integer"), ("indice_cercano", "double"), ("indice_control", "double"),
    ("brecha", "double"), ("ic_bajo_pad", "double"), ("ic_alto_pad", "double"), ("ic_bajo_bloque", "double"), ("ic_alto_bloque", "double"),
    ("brecha_previa_limpia", "double"), ("ic_bajo_previa_pad", "double"), ("ic_alto_previa_pad", "double"),
    ("ic_bajo_previa_bloque", "double"), ("ic_alto_previa_bloque", "double"), ("valor", "double"), ("se_replica", "boolean")]
COLS_SERIE = [
    ("base", "varchar"), ("k", "integer"), ("n_cercanos", "integer"), ("n_controles", "integer"), ("indice_cercano", "double"),
    ("indice_control", "double"), ("brecha", "double"), ("ic_bajo_pad", "double"), ("ic_alto_pad", "double"),
    ("ic_bajo_bloque", "double"), ("ic_alto_bloque", "double"), ("pads", "integer"), ("bloques", "integer")]
COLS_PLACEBO = [("desplazamiento_meses", "integer"), ("n_cercanos", "integer"), ("brecha_mes1", "double"), ("ic_bajo", "double"),
                ("ic_alto", "double"), ("brecha_real", "double")]
COLS_ROBUSTEZ = [
    ("corte", "varchar"), ("n_cercanos", "integer"), ("n_controles", "integer"), ("brecha_mes1", "double"), ("ic_bajo_pad", "double"),
    ("ic_alto_pad", "double"), ("ic_bajo_bloque", "double"), ("ic_alto_bloque", "double"), ("brecha_previa_limpia", "double"),
    ("n_cercanos_previa", "integer"), ("ic_bajo_previa_bloque", "double"), ("ic_alto_previa_bloque", "double")]
COLS_RECUENTOS = [("orden", "integer"), ("clave", "varchar"), ("valor", "bigint")]


# ------------------------------------------------------------------ la lectura (la regla, sin datos)

def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and np.isnan(x))


def lectura(brecha: float, ic_alto: float, brecha_previa: float) -> tuple[bool, float]:
    """(se_replica, valor). Valor = max(limite superior del IC, |brecha previa limpia| - |brecha del mes 1|); se replica si es < 0.

    Un dato indefinido (brecha, IC o brecha previa sin valor) cuenta como "no se replica" y su valor es nan.
    """
    if _nan(brecha) or _nan(ic_alto) or _nan(brecha_previa):
        return False, float("nan")
    valor = max(float(ic_alto), abs(float(brecha_previa)) - abs(float(brecha)))
    return bool(valor < 0), float(valor)


# ------------------------------------------------------------------ entradas del estudio (sobre las tablas de P5a)

def preparar(con, todos_los_padres: bool = False) -> None:
    """Arma, como tablas temporales, las dos entradas que consume placebo.cargar con los nombres del warehouse de Vaca Muerta.

    int_pozo_ubicacion: pozos con coordenadas y primer petroleo (mas los hijos), horizontales salvo `todos_los_padres`; el pad sale
    de co_pozo_pad y el area es el condado. int_frac_hijo: los hijos de la regla de P5a (co_hijo.hijo) con su mes de fractura.
    """
    filtro = "" if todos_los_padres else "and (d.horizontal or h.hijo)"
    con.execute(f"""
        create or replace temp table int_pozo_ubicacion as
        select d.pozo_id, d.operador, d.area, d.tipo_pozo, d.lon, d.lat, d.primer_mes_petroleo, p.pad_id
        from dim_pozo d
        join co_pozo_pad p using (pozo_id)
        left join (select pozo_id, true as hijo from co_hijo where hijo) h using (pozo_id)
        where d.lon is not null and d.lat is not null and (d.primer_mes_petroleo is not null or h.hijo) {filtro}
        order by d.pozo_id""")
    con.execute("""
        create or replace temp table int_frac_hijo as
        select pozo_id as hijo, mes_frac from co_hijo where hijo order by pozo_id""")


def tasa_por_dia_producido(con, D: dict) -> np.ndarray:
    """Matriz de caudales con la misma forma e indices que placebo.cargar, pero petroleo del mes sobre sus dias efectivos.

    Un mes con cero dias efectivos queda sin dato (nan): no entra en las bases ni en las medianas.
    """
    pid = [r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()]
    pos = {int(v): i for i, v in enumerate(pid)}
    prod = con.execute("select x.pozo_id, x.mes, x.petroleo_m3 / nullif(x.dias_efectivos, 0) from fct_produccion x "
                       "join int_pozo_ubicacion u on u.pozo_id = x.pozo_id order by x.pozo_id, x.mes").fetchall()
    tasa = np.full_like(D["tasa"], np.nan)
    pm = placebo._mes_idx([r[1] for r in prod])
    pi = np.array([pos[r[0]] for r in prod], dtype=np.int64)
    tasa[pi, pm + placebo.PAD] = np.array([np.nan if r[2] is None else r[2] for r in prod], dtype=float)
    return tasa


def bloque_por_pad(con, D: dict, tam_km: float = KM_BLOQUE) -> np.ndarray:
    """Bloque de 5 km de cada pad hijo (indexado por D["hijo_pad"]): clave de pipeline.bloques sobre el promedio de lat y lon del pad."""
    q = con.execute("select h.hijo, c.lat, c.lon from int_frac_hijo h join int_pozo_ubicacion u on u.pozo_id = h.hijo "
                    "join (select p.pad_id, avg(d.lat) as lat, avg(d.lon) as lon from co_pozo_pad p join dim_pozo d using (pozo_id) "
                    "group by p.pad_id) c on c.pad_id = u.pad_id order by h.hijo").fetchall()
    assert [int(r[0]) for r in q] == [int(v) for v in D["hijo_id"]]
    lat, lon = np.array([r[1] for r in q], dtype=float), np.array([r[2] for r in q], dtype=float)
    por_pad = np.zeros(int(D["hijo_pad"].max()) + 1, dtype=np.int64)
    por_pad[D["hijo_pad"]] = bloques.clave_bloque(lat, lon, tam_km)
    return por_pad


# ------------------------------------------------------------------ brechas con los dos intervalos

def _n(x: np.ndarray) -> int:
    return int(len(np.unique(x)))


def brecha_dos_ic(m: dict, vals: np.ndarray, bloque: np.ndarray, semilla: int, reps: int = REPS_BOOT) -> dict:
    """Brecha cercano menos control (placebo.brecha_ic) con el IC por pads hijo y el IC por bloques de 5 km, misma semilla."""
    rp = placebo.brecha_ic(vals, m["banda"], m["clave"], reps, semilla)
    rb = placebo.brecha_ic(vals, m["banda"], bloque[m["clave"]], reps, semilla)
    ok = ~np.isnan(vals) & (m["banda"] != 1)
    return {"n_near": rp["n_near"], "n_ctrl": rp["n_ctrl"], "near": rp["near"], "ctrl": rp["ctrl"], "brecha": rp["brecha"],
            "lo_pad": rp["ic_bajo"], "hi_pad": rp["ic_alto"], "lo_blq": rb["ic_bajo"], "hi_blq": rb["ic_alto"],
            "pads": _n(m["clave"][ok]), "bloques": _n(bloque[m["clave"]][ok])}


def semilla_k(k: int) -> int:
    """La misma semilla por k que bloques.py (placebo.tabla_pretendencia): SEMILLA_PLACEBO + 100 + posicion de k en KS_PRE."""
    return SEMILLA_PLACEBO + 100 + (k - KS_PRE[0])


def veredicto(D: dict, bloque: np.ndarray, reps: int = REPS_BOOT) -> tuple[tuple, dict, dict]:
    """Fila del veredicto (k = 1), mas el detalle del mes 1 y de la brecha previa limpia (k = -1) para reusar en la robustez."""
    m1 = placebo.marco(D, D["hijo_mes"], ks=(K_VEREDICTO,), base=BASE_VEREDICTO)
    r1 = brecha_dos_ic(m1, m1["idx"][K_VEREDICTO], bloque, semilla_k(K_VEREDICTO), reps)
    mp = placebo.marco(D, D["hijo_mes"], ks=(K_PREVIO,), base=BASE_PREVIA)
    rp = brecha_dos_ic(mp, mp["idx"][K_PREVIO], bloque, semilla_k(K_PREVIO), reps)
    se_replica, valor = lectura(r1["brecha"], r1["hi_blq"], rp["brecha"])
    fila = (K_VEREDICTO, r1["n_near"], r1["n_ctrl"], r1["near"], r1["ctrl"], r1["brecha"], r1["lo_pad"], r1["hi_pad"], r1["lo_blq"], r1["hi_blq"],
            rp["brecha"], rp["lo_pad"], rp["hi_pad"], rp["lo_blq"], rp["hi_blq"], valor, se_replica)
    return fila, r1, rp


def _fila_serie(k: int, r: dict) -> tuple:
    return (int(k), r["n_near"], r["n_ctrl"], r["near"], r["ctrl"], r["brecha"], r["lo_pad"], r["hi_pad"], r["lo_blq"], r["hi_blq"],
            r["pads"], r["bloques"])


def serie(D: dict, bloque: np.ndarray, reps: int = REPS_BOOT) -> list[tuple]:
    """Pretendencia limpia (base -6 a -4, k = -3..3) y mes 1 y mes 6 con la base original (-3 a -1), con los dos IC."""
    filas = []
    ml = placebo.marco(D, D["hijo_mes"], ks=KS_PRE, base=BASE_PREVIA)
    for k in KS_PRE:
        filas.append(("limpia",) + _fila_serie(k, brecha_dos_ic(ml, ml["idx"][k], bloque, semilla_k(k), reps)))
    ks = (K_VEREDICTO,) + K_SECUNDARIOS
    mo = placebo.marco(D, D["hijo_mes"], ks=ks, base=BASE_VEREDICTO)
    for k in ks:
        filas.append(("original",) + _fila_serie(k, brecha_dos_ic(mo, mo["idx"][k], bloque, semilla_k(k), reps)))
    return filas


def fila_robustez(corte: str, D: dict, bloque: np.ndarray, reps: int = REPS_BOOT) -> tuple:
    _, r1, rp = veredicto(D, bloque, reps)
    return (corte, r1["n_near"], r1["n_ctrl"], r1["brecha"], r1["lo_pad"], r1["hi_pad"], r1["lo_blq"], r1["hi_blq"], rp["brecha"], rp["n_near"],
            rp["lo_blq"], rp["hi_blq"])


def recuentos(D: dict, bloque: np.ndarray) -> list[tuple]:
    """Eventos, padres, controles, pads hijo y bloques de 5 km del corte principal (mes 1, base original)."""
    m = placebo.marco(D, D["hijo_mes"], ks=(K_VEREDICTO,), base=BASE_VEREDICTO)
    con_dato = ~np.isnan(m["idx"][K_VEREDICTO])
    cerc, ctrl, inter = m["banda"] == 0, m["banda"] == 2, m["banda"] == 1
    usados = con_dato & (cerc | ctrl)
    cl = m["clave"]
    vals = [("hijos", len(D["hijo_id"])), ("pads_hijo", _n(D["hijo_pad"])), ("bloques_5km_hijos", _n(bloque[D["hijo_pad"]])),
            ("eventos_cercanos", int(cerc.sum())), ("eventos_intermedios", int(inter.sum())), ("eventos_controles", int(ctrl.sum())),
            ("padres_cercanos", _n(m["padre"][cerc])), ("padres_controles", _n(m["padre"][ctrl])),
            ("eventos_cercanos_con_mes1", int((cerc & con_dato).sum())), ("eventos_controles_con_mes1", int((ctrl & con_dato).sum())),
            ("pads_hijo_usados", _n(cl[usados])), ("bloques_5km_usados", _n(bloque[cl][usados]))]
    return [(10 * (i + 1), c, int(v)) for i, (c, v) in enumerate(vals)]


# ------------------------------------------------------------------ corrida

def calcular(con, reps: int = REPS_BOOT, placebo_reps: int = REPS_BOOT, cuenca: Cuenca = COLORADO) -> dict:
    """Todas las tablas (nombre -> (columnas, filas)) a partir de un warehouse con las tablas de P5a."""
    preparar(con)
    D = placebo.cargar(con)
    bloque = bloque_por_pad(con, D)
    fila_v, _, _ = veredicto(D, bloque, reps)
    principal = fila_robustez("principal", D, bloque, reps)
    por_dia = fila_robustez("por_dia_producido", dict(D, tasa=tasa_por_dia_producido(con, D)), bloque, reps)
    out = {
        cuenca.tabla_veredicto: (COLS_VEREDICTO, [fila_v]),
        "mart_replicacion_serie": (COLS_SERIE, serie(D, bloque, reps)),
        "mart_replicacion_placebo": (COLS_PLACEBO, placebo.tabla_fechas(D, DESPLAZAMIENTOS_PLACEBO, placebo_reps)),
        "mart_replicacion_recuentos": (COLS_RECUENTOS, recuentos(D, bloque)),
    }
    preparar(con, todos_los_padres=True)
    D_todos = placebo.cargar(con)
    todos = fila_robustez("todos_los_padres", D_todos, bloque_por_pad(con, D_todos), reps)
    out["mart_replicacion_robustez"] = (COLS_ROBUSTEZ, [principal, todos, por_dia])
    return out


def escribir(con, tablas: dict) -> None:
    for nombre, (cols, filas) in tablas.items():
        _escribir(con, nombre, cols, filas)


# ------------------------------------------------------------------ pagina

PAGINA = ROOT / "wiki" / "hallazgos" / "replicacion.md"
ROTULOS_RECUENTOS = {
    "hijos": "Hijos (regla de P5a)", "pads_hijo": "Pads hijo", "bloques_5km_hijos": "Bloques de 5 km con algún hijo",
    "eventos_cercanos": "Eventos cercanos (a menos de 1 km)", "eventos_intermedios": "Eventos intermedios (de 1 a 2 km, fuera de la brecha)",
    "eventos_controles": "Eventos de control (de 2 a 5 km)", "padres_cercanos": "Padres distintos entre los eventos cercanos",
    "padres_controles": "Padres distintos entre los eventos de control",
    "eventos_cercanos_con_mes1": "Eventos cercanos con dato al mes 1", "eventos_controles_con_mes1": "Eventos de control con dato al mes 1",
    "pads_hijo_usados": "Pads hijo en la brecha del mes 1", "bloques_5km_usados": "Bloques de 5 km en la brecha del mes 1"}
ROTULOS_ROBUSTEZ = {"principal": "Principal (padres horizontales, caudal por día calendario)",
                    "todos_los_padres": "Todos los padres (horizontales, verticales y sin dato)",
                    "por_dia_producido": "Caudal por día producido (petróleo sobre días efectivos)"}


def _ic(lo: float, hi: float) -> str:
    return f"{placebo._pts(lo)} a {placebo._pts(hi)}"


def rotulos_recuentos(cuenca: Cuenca) -> dict:
    return {**ROTULOS_RECUENTOS, **({"hijos": cuenca.rotulo_hijos} if cuenca.rotulo_hijos else {})}


def pagina_replicacion(con, cuenca: Cuenca = COLORADO) -> str:
    g, pts = placebo._g, placebo._pts
    v = dict(zip([c[0] for c in COLS_VEREDICTO], con.execute(f"select * from {cuenca.tabla_veredicto} where k = 1").fetchone()))
    ser = con.execute("select * from mart_replicacion_serie order by base desc, k").fetchall()
    pla = con.execute("select * from mart_replicacion_placebo where desplazamiento_meses <> 0 order by desplazamiento_meses").fetchall()
    rob = {r[0]: r for r in con.execute("select * from mart_replicacion_robustez").fetchall()}
    rec = {r[1]: r[2] for r in con.execute("select * from mart_replicacion_recuentos").fetchall()}
    bloques_v = next(r[12] for r in ser if r[0] == "original" and r[1] == K_VEREDICTO)
    se = bool(v["se_replica"])
    sale_ic = v["ic_alto_bloque"] < 0
    previa_menor = abs(v["brecha_previa_limpia"]) < abs(v["brecha"])
    dif = abs(v["brecha_previa_limpia"]) - abs(v["brecha"])
    dia, prin = rob["por_dia_producido"], rob["principal"]
    menor = abs(dia[3]) < abs(prin[3])
    pct_menos = round(100 * (1 - abs(dia[3]) / abs(prin[3])))
    k2 = next(r for r in ser if r[0] == "limpia" and r[1] == -2)
    k6 = next(r for r in ser if r[0] == "original" and r[1] == 6)
    fx = cuenca.fecha_hijo
    L = [f"# {cuenca.titulo}", "",
         f"Página generada por `pipeline/replicacion.py` sobre el warehouse {cuenca.de_el} (`data/{cuenca.id}/warehouse.duckdb`). Corre, sin "
         "cambiarlos, los estimadores del estudio de eventos de Vaca Muerta (`pipeline/placebo.py` y la clave de bloque de "
         f"`pipeline/bloques.py`) sobre las tablas que armó `{cuenca.modulo}` ([datos y conteos]({cuenca.pagina_datos})). La regla se fijó "
         f"antes de correr, {cuenca.regla_fijada}, y está en el libro de hallazgos como `{cuenca.hipotesis}`. Complementa "
         "[Interferencia entre fracturas](interferencia.md) y [Bloques espaciales](bloques.md).", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada antes de correr: **{'se replica' if se else 'no se replica'}**. El límite superior del IC por "
         f"bloques de 5 km de la brecha del mes 1 {'queda por debajo de cero' if sale_ic else 'no queda por debajo de cero'} y la brecha "
         f"previa a la {fx} con base limpia {'es menor' if previa_menor else 'no es menor'}, en valor absoluto, que la del mes 1. "
         "La segunda condición es una barrera baja: pide una brecha previa menor que la del mes 1, no una brecha previa igual a cero. "
         + (f"Con base limpia la brecha del mes -1 ({pts(v['brecha_previa_limpia'])}, IC 95% por bloques de 5 km: "
            f"{_ic(v['ic_bajo_previa_bloque'], v['ic_alto_previa_bloque'])}) y la del mes -2 ({pts(k2[6])}, IC: {_ic(k2[9], k2[10])}) "
            f"{'también excluyen' if v['ic_alto_previa_bloque'] < 0 and k2[10] < 0 else 'no excluyen ambas'} cero. ")
         + (f"Medida por día producido, la brecha del mes 1 es de {pts(dia[3])} puntos (IC 95% por bloques de 5 km: "
            f"{_ic(dia[6], dia[7])}), cerca de {pct_menos}% menor en valor absoluto que los {pts(prin[3])} de la medida principal, y con "
            f"menos eventos cercanos ({g(dia[1])} frente a {g(prin[1])}). La regla se aplica a la medida principal (por día calendario): "
            "una parte grande de la brecha principal pasa entonces por meses o días sin producción, en línea con la descomposición en "
            "días y caudal por día de Vaca Muerta (`descomposicion.md`). " if menor else
            "Medida por día producido, la brecha del mes 1 no es menor que por día calendario. ")
         + "Es la lectura de una cuenca, con las limitaciones de abajo, y no una afirmación causal.", "",
         f"- Brecha del mes 1 (padres horizontales a menos de 1 km frente a controles de 2 a 5 km, base de los meses -3 a -1): "
         f"{pts(v['brecha'])} puntos. IC 95% por pads hijo: {_ic(v['ic_bajo_pad'], v['ic_alto_pad'])}; por bloques de 5 km: "
         f"{_ic(v['ic_bajo_bloque'], v['ic_alto_bloque'])} ({g(bloques_v)} bloques).",
         f"- Brecha previa a la {fx} con base limpia (mes -1, base de los meses -6 a -4): {pts(v['brecha_previa_limpia'])} puntos "
         f"(IC 95% por bloques de 5 km: {_ic(v['ic_bajo_previa_bloque'], v['ic_alto_previa_bloque'])}).",
         f"- Valor de la hipótesis: {g(v['valor'], 3)}, el mayor entre el límite superior del IC por bloques, {g(v['ic_alto_bloque'], 3)}, y "
         f"la diferencia de valores absolutos (previa menos mes 1), {g(dif, 3)}; se replica si es menor que cero.",
         f"- Eventos con dato al mes 1: {g(rec['eventos_cercanos_con_mes1'])} cercanos y {g(rec['eventos_controles_con_mes1'])} controles, de "
         f"{g(rec['pads_hijo_usados'])} pads hijo y {g(rec['bloques_5km_usados'])} bloques de 5 km.",
         "- Los resultados secundarios (pretendencia, mes 6, placebo con fechas corridas, robustez) se publican completos abajo; no son "
         "veredictos.", "",
         "## Regla fijada antes de correr", "",
         "Se replica si la brecha del mes 1 (mediana del índice de los padres cercanos menos la de los controles, base de los meses -3 a "
         f"-1, padres a menos de 1 km y controles de 2 a 5 km, con los filtros {cuenca.filtros}) es negativa con un IC 95% que excluye cero, y si la "
         "brecha previa con base limpia (mes -1, base de los meses -6 a -4) es menor, en valor absoluto, que la del mes 1. Si no, no se "
         "replica. La lectura usa el IC por bloques espaciales de 5 km; el IC por pads hijo se publica al lado."
         + cuenca.nota_regla, "",
         "## Brecha por mes, con los dos intervalos", "",
         "Índice = caudal de petróleo del mes sobre la media de la base; brecha = mediana de los cercanos menos mediana de los controles, "
         f"en puntos de índice. k = 0 es el mes de la {fx} del hijo.", "",
         "| Base | k | Eventos cercanos | Eventos de control | Brecha (puntos) | IC 95% por pads | IC 95% por bloques de 5 km | Bloques |",
         "| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |"]
    for base, k, nn, nc, _a, _b, gap, lop, hip, lob, hib, _p, nb in ser:
        rot = "Meses -6 a -4" if base == "limpia" else "Meses -3 a -1"
        L.append(f"| {rot} | {k} | {g(nn)} | {g(nc)} | {pts(gap)} | {_ic(lop, hip)} | {_ic(lob, hib)} | {g(nb)} |")
    L += ["", "Con la base de los meses -6 a -4 los meses -3 a -1 son la pretendencia (la brecha previa a la " + fx + "); con la base de los meses "
          "-3 a -1 el mes 1 es el resultado del veredicto y el mes 6 mide cuánto queda de la brecha. "
          f"Al mes 6 la brecha es de {pts(k6[6])} puntos; su IC por bloques {'excluye' if k6[10] < 0 else 'incluye'} cero.", "",
          f"## Placebo con la fecha de {fx} corrida", "",
          f"Se corre la fecha de {fx} de todos los hijos 12 meses (hacia atrás y hacia adelante), se conservan los pares padre e hijo y "
          "se exige que el padre cumpla las mismas reglas en la fecha falsa (la misma máquina de `pipeline/placebo.py`, IC por pads). "
          f"Con -12 meses la fecha falsa cae antes de la {fx} real y es el placebo limpio; con +12 el mes falso puede caer sobre meses "
          "ya afectados, así que no refuta nada por sí solo.", "",
          "| Desplazamiento (meses) | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% por pads | Brecha real en los mismos eventos (puntos) |",
          "| ---: | ---: | ---: | --- | ---: |"]
    for d, n, gap, lo, hi, real in pla:
        L.append(f"| {d} | {g(n)} | {pts(gap)} | {_ic(lo, hi)} | {pts(real)} |")
    L += ["", "## Robustez a los dos riesgos de la memoria de factibilidad", "",
          "Un solo corte, sin veredicto adicional: padres horizontales (el corte principal) frente a todos los padres, y caudal por día "
          "calendario (el principal) frente a caudal por día producido (petróleo del mes sobre sus días efectivos; un mes sin días "
          "efectivos queda sin dato). Cada fila recalcula el mes 1 y la brecha previa del mes -1 con su propia regla.", "",
          "| Corte | Eventos cercanos | Eventos de control | Brecha del mes 1 (puntos) | IC 95% por pads | IC 95% por bloques de 5 km | "
          "Brecha previa del mes -1 (puntos) |",
          "| --- | ---: | ---: | ---: | --- | --- | ---: |"]
    for c in CORTES:
        r = rob[c]
        L.append(f"| {ROTULOS_ROBUSTEZ[c]} | {g(r[1])} | {g(r[2])} | {pts(r[3])} | {_ic(r[4], r[5])} | {_ic(r[6], r[7])} | {pts(r[8])} |")
    L += ["", f"Medida por día producido la brecha del mes 1 {'es menor' if menor else 'no es menor'} en valor absoluto que por día "
          "calendario. En la medida principal un mes cerrado entra con caudal cero; por día producido queda sin dato. "
          + (f"La brecha por día producido es de {pts(dia[3])} puntos, cerca de {pct_menos}% menor que la principal, con "
             f"{g(dia[1])} eventos cercanos frente a {g(prin[1])}; la regla se aplica a la medida principal, así que una parte grande de "
             "la brecha pasa por meses o días sin producir, en línea con la descomposición en días y caudal por día de Vaca Muerta "
             "(`descomposicion.md`)." if menor else
             "La brecha no depende entonces de meses o días sin producir."), "",
          "## Recuentos", "", "| Concepto | Cantidad |", "| --- | ---: |"]
    for clave, rot in rotulos_recuentos(cuenca).items():
        L.append(f"| {rot} | {g(rec[clave])} |")
    L += ["", f"## Qué {cuenca.nombre} no puede mostrar", "", *[f"- {t}" for t in cuenca.no_puede], "",
          "## Qué significa para el resultado de Vaca Muerta", "",
          (f"La brecha del mes 1 y la regla fijada de antemano se sostienen también en {cuenca.ordinal} con los mismos estimadores: es una "
           "validación externa de eso, no una estimación conjunta ni una cifra que se pueda trasladar de una cuenca a otra. "
           f"Al mes 6 la brecha de {cuenca.nombre} es de {pts(k6[6])} puntos y su IC por bloques {'excluye' if k6[10] < 0 else 'incluye'} cero: "
           "la caída no se cierra del todo al mes 6, a diferencia de la lectura de recuperación de Vaca Muerta. La forma más allá del "
           "mes 1 no formó parte de la regla."
           if se else
           f"La huella no se confirma en {cuenca.nombre} con los mismos estimadores y la regla fijada de antemano, y se publica así. "
           "Esta cuenca sola no confirma ni desmiente el resultado de Vaca Muerta: se lee junto con las otras cuencas, no sola. No es "
           "una estimación conjunta ni cambia las cifras de Vaca Muerta."), ""]
    return "\n".join(L)


_DE_LA_CUENCA = object()        # "pagina" sin dar: la pagina de la cuenca (None sigue queriendo decir "no escribir pagina")


def main(path: Path | None = None, pagina=_DE_LA_CUENCA, cuenca: Cuenca = COLORADO) -> int:
    path = cuenca.db if path is None else path
    pagina = cuenca.pagina if pagina is _DE_LA_CUENCA else pagina
    if not Path(path).exists():
        print(f"falta {path}: corre `uv run python -m {cuenca.modulo.replace('/', '.')}.build`.", file=sys.stderr)
        return 2
    con = duckdb.connect(str(path))
    try:
        tablas = calcular(con, cuenca=cuenca)
        escribir(con, tablas)
        if pagina is not None:
            pagina.parent.mkdir(parents=True, exist_ok=True)
            pagina.write_text(pagina_replicacion(con, cuenca), encoding="utf-8")
            print(f"pagina: {pagina}")
        for nombre, (_, filas) in tablas.items():
            for f in filas:
                print(f"[replicacion] {nombre[17:]:<10}", tuple(round(x, 4) if isinstance(x, float) else x for x in f))
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="pipeline.replicacion")
    ap.add_argument("--cuenca", default=COLORADO.id, help="id de la cuenca (pipeline/cuencas.py); sin argumento, Colorado")
    a = ap.parse_args()
    c = _cuenca(a.cuenca)
    sys.exit(main(cuenca=c, pagina=c.pagina))
