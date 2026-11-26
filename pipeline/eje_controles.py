"""Controles del eje: el eje de merma en la ventana previa a la fractura y con bloques espaciales de 5 km.

Se corre despues de pipeline.bloques:  uv run python -m pipeline.eje_controles

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ninguna cifra de este modulo; no se cambia despues de ver resultados).
Fuente: docs/proceso/investigacion-fase3.md, secciones 3.3 (control negativo 1), 3.7 y 4 (regla de parada del eje).

Pregunta 1 (ventana previa): si el eje de mayor merma fuera un efecto de la fractura del hijo, antes de la fractura los padres
cercanos no deberian mostrar un eje. Si lo muestran cerca de 93 grados, el eje es una direccion en la que los padres ya rendian
menos (seleccion o geometria), no interferencia.

Pregunta 2 (bloques espaciales): el IC del eje remuestrea pads hijo; dos pads vecinos comparten geologia y programa. Con bloques
de una grilla espacial el IC mide esa dependencia, y la regla de parada pide que el eje de la cuenca siga definido.

Muestra: eventos de 0,3 a menos de 1 km del hijo mas cercano, con las mismas reglas de elegibilidad del eje principal
(pipeline.placebo.marco: edad minima, base positiva, hijo mas cercano; controles de 2 a 5 km del mismo grupo de edad: menos de
12 meses, 12 a 23, 24 a 47, 48 o mas). Mismo ajuste que el eje principal (pipeline.costo.eje_con_intervalo con efectos fijos de
area, controles km y log de la edad, rumbo axial 0 a 180 grados). REPS_EJE = 400 y REPS_PERM = 499 como el eje principal.

Prueba 1 (eje previo):
  * Resultado de cada evento: caida previa = (mediana del indice de los controles del mismo grupo de edad en k = -1) menos (indice
    del evento en k = -1), ambos acotados a [0, 2], con el indice del mes k = -1 sobre la base de los meses -6 a -4 (la base limpia
    de pipeline.placebo: BASE_LIMPIA). Eventos y controles con esa base mayor que BASE_MIN (lo hace placebo.marco con base=BASE_LIMPIA).
  * IC 95% por pads hijo y p de permutacion de pads hijo completos, con la semilla SEMILLA_PLACEBO + 700.
  * Se informa tambien, sobre los mismos eventos, el eje del mes k = 1 con esa misma base limpia (para que la comparacion sea
    manzanas con manzanas) y el eje del resultado principal (93 grados, base original).
  * Un eje se da por definido si p de permutacion < 0,10 y el IC mide menos de 90 grados (la regla del proyecto).
  * La distancia entre dos ejes es la diferencia axial en (-90, 90], en valor absoluto.

Prueba 2 (bloques):
  * El eje de la cuenca del resultado principal (k = 1, base original, pipeline.costo.EVENTOS_SQL, 0,3 a menos de 1 km), con la
    clave de remuestreo y de permutacion igual al bloque de la grilla en vez del pad hijo. Grilla de 5 km (la que usa la regla) y
    de 2 km (informativa), con pipeline.bloques.clave_bloque sobre el promedio de lat y lon del pad hijo del hijo mas cercano.
  * Si el IC por bloques de 5 km se calcula con menos de 30 bloques, no hay veredicto.

Veredicto (se publican todos los resultados, favorables o no):
  * Eje previo "definido y cercano": el eje previo esta definido y a menos de 30 grados de 93. DISPARA la segunda pata de la regla de
    parada del eje y el eje se reescribe como "direccion en la que los padres ya rendian menos".
  * "definido y lejano": definido pero a 30 grados o mas de 93: no dispara.
  * "no definido": no dispara.
  * Bloques de 5 km: el eje de la cuenca "deja de estar definido" si su p de permutacion por bloques es >= 0,10 o su IC mide 90
    grados o mas. DISPARA la cuarta pata de la regla de parada. Si sigue definido, no dispara.
  * Se informa para cada eje si el SHmax publicado (67,5) cae dentro de su IC.

Que NO prueba:
  * El eje previo usa la misma muestra, asi que su ruido no es independiente del eje posterior.
  * La ventana previa mezcla pretendencia con seleccion de padres; un eje previo definido no se separa de ninguna de las dos.
  * No es un test de causa: solo pone una condicion necesaria (el eje no debe estar ya antes de la fractura).
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import bloques, costo, placebo
from pipeline.costo import (ANCHO_MAX, KM_MIN_EJE, P_EJE_COSTO, REPS_EJE, REPS_PERM, _arr, _controles_eje, _dif_axial,
                            _escribir, _filas)
from pipeline.ingest import DATA
from pipeline.placebo import SEMILLA_PLACEBO, _g, _pts

SHMAX = 67.5            # SHmax publicado, en la misma convencion axial que el eje
EJE_REF = 93.0          # eje principal de la cuenca, referencia de la distancia
UMBRAL_CERCANO = 30.0   # el eje previo es cercano si esta a menos de 30 grados de 93
MIN_BLOQUES = 30        # bloques minimos de 5 km para que haya veredicto

COLS = [("prueba", "varchar"), ("n", "integer"), ("unidades", "integer"), ("eje", "double"), ("ic_bajo", "double"),
        ("ic_alto", "double"), ("ancho_ic", "double"), ("amplitud", "double"), ("p_perm", "double"),
        ("definido", "boolean"), ("dist_93", "double"), ("dist_shmax", "double"), ("shmax_en_ic", "boolean")]
COLS_VEREDICTO = [("prueba", "varchar"), ("veredicto", "varchar"), ("dispara_regla_parada", "boolean")]
COLS_ROTACION = [("unidad", "varchar"), ("unidades", "integer"), ("eventos_en_bloques_de_tamano_unico", "integer"),
                 ("p_permutacion_tamano", "double"), ("p_rotacion", "double")]
N_ROTACION = 999        # diagnostico agregado despues de ver los resultados; no entra en la regla fijada antes de correr


def dist_axial(a: float, b: float) -> float:
    """Distancia axial entre dos ejes, en [0, 90] grados."""
    return float(abs(_dif_axial(a, b)))


def _en_arco(x: float, a: float, b: float) -> bool:
    """Si x cae en el arco que va de a a b en sentido creciente, modulo 180 (bordes incluidos)."""
    return bool((x - a) % 180 <= (b - a) % 180)


def en_ic(x: float, ic_bajo: float, ic_alto: float, eje: float) -> bool:
    """Si x cae en el IC, que es el arco de ic_bajo a ic_alto que pasa por el eje (modulo 180)."""
    if _en_arco(eje, ic_bajo, ic_alto):
        return _en_arco(x, ic_bajo, ic_alto)
    return _en_arco(x, ic_alto, ic_bajo)


def es_definido(p_perm: float, ancho_ic: float) -> bool:
    """Un eje esta definido si su p es menor que 0,10 y su IC mide menos de 90 grados (regla del proyecto)."""
    return bool(p_perm < P_EJE_COSTO and ancho_ic < ANCHO_MAX)


def veredicto_previo(p_perm: float, ancho_ic: float, dist_93: float) -> tuple[str, bool]:
    """Veredicto del eje previo y si dispara la regla de parada."""
    if not es_definido(p_perm, ancho_ic):
        return "no definido", False
    if dist_93 < UMBRAL_CERCANO:
        return "definido y cercano", True
    return "definido y lejano", False


def veredicto_bloques(p_perm: float, ancho_ic: float, n_bloques: int) -> tuple[str, bool]:
    """Veredicto del eje por bloques de 5 km y si dispara la regla de parada."""
    if n_bloques < MIN_BLOQUES:
        return "sin veredicto (menos de 30 bloques)", False
    if not es_definido(p_perm, ancho_ic):
        return "deja de estar definido", True
    return "sigue definido", False


def datos_eje(m: dict, k: int) -> dict | None:
    """Muestra del eje para el mes k, con la misma logica que placebo._datos_eje generalizada en k."""
    edad, idx = m["edad"], m["idx"][k]
    g = np.where(edad < 12, 0, np.where(edad < 24, 1, np.where(edad < 48, 2, 3)))
    ctl = np.full(4, np.nan)
    for j in range(4):
        x = idx[(m["banda"] == 2) & (g == j) & ~np.isnan(idx)]
        if len(x):
            ctl[j] = np.median(x)
    sel = (m["km"] >= KM_MIN_EJE) & (m["km"] < 1) & ~np.isnan(idx) & ~np.isnan(ctl[g])
    if sel.sum() < 40:
        return None
    area = m["area"][sel]
    caida = np.clip(ctl[g][sel], 0, 2) - np.clip(idx[sel], 0, 2)
    ev = {"km": m["km"][sel], "edad": edad[sel].astype(float), "lat": m["lat"][sel]}
    return {"caida": caida, "ctrl": _controles_eje(ev), "rumbo": m["rumbo"][sel], "clave": m["clave"][sel],
            "grupo": np.unique(area, return_inverse=True)[1], "n": int(sel.sum())}


def bloque_para(lat: float, lon: float, tam_km: float) -> int:
    """Codigo de la celda de tam_km km que contiene el punto (lat, lon)."""
    return int(bloques.clave_bloque(np.array([lat]), np.array([lon]), tam_km)[0])


def bloques_por_pad(con) -> dict:
    """Bloque de 2 y 5 km de cada pad_id, por el promedio de lat y lon de sus pozos."""
    q = con.execute("select pad_id, avg(lat), avg(lon) from int_pozo_ubicacion group by pad_id").fetchall()
    ids = [str(r[0]) for r in q]
    lat = np.array([r[1] for r in q], dtype=float)
    lon = np.array([r[2] for r in q], dtype=float)
    b2 = bloques.clave_bloque(lat, lon, 2.0)
    b5 = bloques.clave_bloque(lat, lon, 5.0)
    return {p: (int(a), int(b)) for p, a, b in zip(ids, b2, b5)}


def _fila(prueba: str, e: dict, r: dict) -> tuple:
    """Fila de mart_eje_controles para un eje ya ajustado."""
    d93, dsh = dist_axial(r["eje"], EJE_REF), dist_axial(r["eje"], SHMAX)
    return (prueba, e["n"], int(len(np.unique(e["clave"]))), r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"],
            r["amplitud"], r["p_perm"], es_definido(r["p_perm"], r["ancho_ic"]), d93, dsh,
            en_ic(SHMAX, r["ic_bajo"], r["ic_alto"], r["eje"]))


def _nula(prueba: str) -> tuple:
    """Fila nula cuando la muestra no alcanza el minimo de eventos."""
    return (prueba, 0, 0, None, None, None, None, None, None, False, None, None, None)


def prueba_previa(D: dict) -> list[tuple]:
    """Prueba 1: eje del mes -1 y del mes 1 con la base limpia, mas el principal con la base original."""
    limpia = placebo.marco(D, D["hijo_mes"], ks=(-1, 1), base=placebo.BASE_LIMPIA)
    orig = placebo.marco(D, D["hijo_mes"])
    muestras = [("eje_previo_k-1", datos_eje(limpia, -1)), ("eje_k1_base_limpia", datos_eje(limpia, 1)),
                ("eje_principal", datos_eje(orig, 1))]
    filas = []
    for j, (nombre, e) in enumerate(muestras):
        if e is None:
            filas.append(_nula(nombre))
            continue
        r = costo.eje_con_intervalo(e["caida"], e["ctrl"], e["rumbo"], e["clave"], grupo=e["grupo"], reps=REPS_EJE,
                                    reps_perm=REPS_PERM, semilla=SEMILLA_PLACEBO + 700 + j)
        filas.append(_fila(nombre, e, r))
    return filas


def prueba_bloques(con) -> list[tuple]:
    """Prueba 2: eje de la cuenca con clave de pad y con clave de bloque de 2 y 5 km (misma semilla)."""
    filas = _filas(con, costo.EVENTOS_SQL)
    km = _arr(filas, "km_min")
    f = [x for x, s in zip(filas, (km >= KM_MIN_EJE) & (km < 1)) if s]
    area = np.array([x["area"] for x in f])
    ev = {"km": _arr(f, "km_min"), "edad": _arr(f, "edad_meses"), "lat": _arr(f, "lat")}
    caida = np.clip(_arr(f, "indice_control"), 0, 2) - np.clip(_arr(f, "indice"), 0, 2)
    rumbo = _arr(f, "rumbo_eje")
    clave_pad = np.array([str(x["pad_hijo"]) for x in f])
    grupo = np.unique(area, return_inverse=True)[1]
    blk = bloques_por_pad(con)
    b2 = np.array([blk[p][0] for p in clave_pad], dtype=np.int64)
    b5 = np.array([blk[p][1] for p in clave_pad], dtype=np.int64)
    ctrl = _controles_eje(ev)
    out = []
    for nombre, clave in (("bloques_5km", b5), ("bloques_2km", b2), ("pads", clave_pad)):
        r = costo.eje_con_intervalo(caida, ctrl, rumbo, clave, grupo=grupo)
        out.append(_fila(nombre, {"n": len(f), "clave": clave}, r))
    return out


def p_rotacion(caida, ctrl, rumbo, grupo, clave, n: int = N_ROTACION, semilla: int = costo.SEMILLA + 900) -> float:
    """p de permutacion que rota los rumbos de cada unidad (pad o bloque) por un angulo uniforme propio.

    Diagnostico agregado despues de ver los resultados: la permutacion de la regla (costo._perm_bloques) solo intercambia unidades
    del mismo tamano, y con bloques de 5 km mas de la mitad de los eventos estan en bloques de tamano unico que no se mueven.
    Rotar los rumbos de una unidad conserva su estructura interna y rompe su relacion con la caida si no hay direccion."""
    _t0, amp, _b = costo.ajustar_eje(caida, ctrl, rumbo, grupo)
    u, inv = np.unique(clave, return_inverse=True)
    rng = np.random.default_rng(semilla)
    mayor = 0
    for _ in range(n):
        rot = rng.uniform(0, 180, len(u))[inv]
        mayor += costo.ajustar_eje(caida, ctrl, (rumbo + rot) % 180, grupo)[1] >= amp
    return float((1 + mayor) / (1 + n))


def diagnostico_rotacion(con) -> list[tuple]:
    """Por unidad de remuestreo (pads, bloques de 2 y 5 km): eventos en unidades de tamano unico, p de la regla y p por rotacion."""
    filas = _filas(con, costo.EVENTOS_SQL)
    km = _arr(filas, "km_min")
    f = [x for x, s in zip(filas, (km >= KM_MIN_EJE) & (km < 1)) if s]
    area = np.array([x["area"] for x in f])
    ev = {"km": _arr(f, "km_min"), "edad": _arr(f, "edad_meses"), "lat": _arr(f, "lat")}
    caida = np.clip(_arr(f, "indice_control"), 0, 2) - np.clip(_arr(f, "indice"), 0, 2)
    rumbo = _arr(f, "rumbo_eje")
    pad = np.array([str(x["pad_hijo"]) for x in f])
    grupo = np.unique(area, return_inverse=True)[1]
    blk = bloques_por_pad(con)
    ctrl = _controles_eje(ev)
    p_regla = {r[0]: r[1] for r in con.execute("select prueba, p_perm from mart_eje_controles").fetchall()}
    out = []
    for nombre, clave, prueba in (("pads", pad, "pads"), ("bloques de 2 km", np.array([blk[p][0] for p in pad]), "bloques_2km"),
                                  ("bloques de 5 km", np.array([blk[p][1] for p in pad]), "bloques_5km")):
        _u, cuentas = np.unique(clave, return_counts=True)
        tam, rep = np.unique(cuentas, return_counts=True)
        unicos = int(sum(t * r for t, r in zip(tam, rep) if r == 1))
        out.append((nombre, int(len(cuentas)), unicos, p_regla[prueba], p_rotacion(caida, ctrl, rumbo, grupo, clave)))
    return out


def _t(x: float | None, dec: int = 1) -> str:
    """Numero para la tabla impresa (n/d si falta)."""
    return "n/d" if x is None else f"{x:.{dec}f}"


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    filas = prueba_previa(placebo.cargar(con)) + prueba_bloques(con)
    _escribir(con, "mart_eje_controles", COLS, filas)
    d = {f[0]: dict(zip([c for c, _ in COLS], f)) for f in filas}
    pre, b5 = d["eje_previo_k-1"], d["bloques_5km"]
    v_pre = veredicto_previo(pre["p_perm"], pre["ancho_ic"], pre["dist_93"]) if pre["p_perm"] is not None else ("no definido", False)
    v_b5 = veredicto_bloques(b5["p_perm"], b5["ancho_ic"], b5["unidades"]) if b5["p_perm"] is not None else ("sin veredicto (menos de 30 bloques)", False)
    _escribir(con, "mart_eje_controles_veredicto", COLS_VEREDICTO,
              [("eje_previo_k-1", v_pre[0], v_pre[1]), ("bloques_5km", v_b5[0], v_b5[1])])
    _escribir(con, "mart_eje_controles_rotacion", COLS_ROTACION, diagnostico_rotacion(con))
    for r in con.execute("select * from mart_eje_controles_rotacion").fetchall():
        print(f"[eje_controles] rotacion {r[0]:<16} unidades={r[1]} eventos_en_tamano_unico={r[2]} p_regla={_t(r[3], 3)} p_rotacion={_t(r[4], 3)}")
    for r in con.execute("select * from mart_eje_controles").fetchall():
        p, n, u, ej, lo, hi, an, amp, pp, df, d93, dsh, sh = r
        print(f"[eje_controles] {p:<18} n={n} u={u} eje={_t(ej)} IC {_t(lo)} a {_t(hi)} ancho={_t(an)} "
              f"amp={_t(amp, 3)} p={_t(pp, 3)} def={df} d93={_t(d93)} dsh={_t(dsh)} shmax_en_ic={sh}")
    print(f"[eje_controles] bloques distintos: 5km={b5['unidades']} 2km={d['bloques_2km']['unidades']} pads={d['pads']['unidades']}")
    for p, v, dd in con.execute("select * from mart_eje_controles_veredicto").fetchall():
        print(f"[eje_controles] veredicto {p:<14} {v} (dispara={dd})")
    con.close()


def pagina_eje_controles(con) -> str:
    """Markdown de wiki/hallazgos/eje_controles.md a partir de los marts (no escribe a disco)."""
    filas = [dict(zip([c for c, _ in COLS], r)) for r in con.execute("select * from mart_eje_controles").fetchall()]
    vered = {r[0]: (r[1], r[2]) for r in con.execute("select * from mart_eje_controles_veredicto").fetchall()}
    d = {f["prueba"]: f for f in filas}
    pre, k1, prin = d["eje_previo_k-1"], d["eje_k1_base_limpia"], d["eje_principal"]
    b5, b2, pads = d["bloques_5km"], d["bloques_2km"], d["pads"]
    v_pre, v_b5 = vered["eje_previo_k-1"], vered["bloques_5km"]

    def sn(x) -> str:
        return "n/d" if x is None else ("sí" if x else "no")

    def cont(amp) -> str:
        return "n/d" if amp is None else _pts(2 * amp)

    L = ["# Controles del eje", "",
         "Página generada por `pipeline/eje_controles.py`. Pone al eje de mayor merma (93 grados) dos controles negativos: "
         "el eje en la ventana previa a la fractura del hijo y el eje con remuestreo por bloques espaciales en vez de pads.", "",
         "## Resumen", "",
         f"- Eje previo (mes -1, base de los meses -6 a -4): {_g(pre['eje'])} grados, IC {_g(pre['ic_bajo'])} a "
         f"{_g(pre['ic_alto'])} (ancho {_g(pre['ancho_ic'])}), p {_g(pre['p_perm'], 3)}, a {_g(pre['dist_93'], 1)} grados de 93. "
         f"Veredicto: **{v_pre[0]}**. {'Dispara' if v_pre[1] else 'No dispara'} la regla de parada.",
         f"- Bloques de 5 km ({_g(b5['unidades'])} bloques): {_g(b5['eje'])} grados, IC {_g(b5['ic_bajo'])} a "
         f"{_g(b5['ic_alto'])} (ancho {_g(b5['ancho_ic'])}), p {_g(b5['p_perm'], 3)}. Veredicto: **{v_b5[0]}**. "
         f"{'Dispara' if v_b5[1] else 'No dispara'} la regla de parada.",
         f"- Comparación con la misma base limpia: el eje del mes 1 queda en {_g(k1['eje'])} grados (a {_g(k1['dist_93'], 1)} "
         f"de 93) y el principal reconstruido en {_g(prin['eje'])}.",
         f"- Referencia por pads: eje {_g(pads['eje'])}, IC {_g(pads['ic_bajo'])} a {_g(pads['ic_alto'])}, p "
         f"{_g(pads['p_perm'], 3)}; por bloques de 2 km ({_g(b2['unidades'])} bloques): eje {_g(b2['eje'])}, IC "
         f"{_g(b2['ic_bajo'])} a {_g(b2['ic_alto'])}, p {_g(b2['p_perm'], 3)}.", "",
         "## Resultados", "",
         "Unidades son pads hijo o bloques según la prueba. El contraste es dos veces la amplitud, en puntos de índice.", "",
         "| Prueba | Eventos | Unidades | Eje (grados) | IC 95% (grados) | Ancho IC | Contraste (puntos) | p permutación | Definido | Dist a 93 | Dist a SHmax | SHmax en IC |",
         "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |"]
    for f in filas:
        L.append(f"| `{f['prueba']}` | {_g(f['n'])} | {_g(f['unidades'])} | {_g(f['eje'])} | {_g(f['ic_bajo'])} a {_g(f['ic_alto'])} | "
                 f"{_g(f['ancho_ic'])} | {cont(f['amplitud'])} | {_g(f['p_perm'], 3)} | {sn(f['definido'])} | {_g(f['dist_93'], 1)} | "
                 f"{_g(f['dist_shmax'], 1)} | {sn(f['shmax_en_ic'])} |")
    rot = [dict(zip([c for c, _ in COLS_ROTACION], r)) for r in con.execute("select * from mart_eje_controles_rotacion").fetchall()]
    L += ["", "## Diagnóstico de la permutación por bloques (agregado después de ver los resultados)", "",
          "La permutación de la regla intercambia los rumbos entre unidades del mismo tamaño. Con bloques grandes casi cada bloque "
          "tiene un tamaño propio y no se mueve, así que su p es poco informativo. Como control se rota el conjunto de rumbos de cada "
          "unidad por un ángulo uniforme propio (999 sorteos), que conserva la estructura interna de la unidad y rompe su relación con la "
          "caída. Este diagnóstico no cambia el veredicto de la regla, que se fijó antes de correr; se publica al lado.", "",
          "| Unidad de remuestreo | Unidades | Eventos en unidades de tamaño único | p de la regla (mismo tamaño) | p por rotación |",
          "| --- | ---: | ---: | ---: | ---: |"]
    for r in rot:
        L.append(f"| {r['unidad']} | {_g(r['unidades'])} | {_g(r['eventos_en_bloques_de_tamano_unico'])} | "
                 f"{_g(r['p_permutacion_tamano'], 3)} | {_g(r['p_rotacion'], 3)} |")
    L += ["", "## Regla fijada antes de correr", "",
          "La muestra es la del eje principal (eventos de 0,3 a 1 km, controles de 2 a 5 km del mismo grupo de edad), con el "
          "mismo ajuste axial con efectos fijos de área y las mismas repeticiones (400 de bootstrap y 499 de permutación).",
          "El eje previo usa el índice del mes -1 sobre la base de los meses -6 a -4; se publica junto al eje del mes 1 sobre "
          "esa misma base y al principal con la base original.",
          "Un eje está definido si su p de permutación es menor que 0,10 y su IC mide menos de 90 grados; cerca de 93 es a "
          "menos de 30 grados.",
          "El eje por bloques usa la muestra del resultado principal y remuestrea celdas de 5 km (2 km como referencia) en vez "
          "de pads, con la misma semilla; con menos de 30 bloques de 5 km no hay veredicto.",
          "Para cada eje se informa si el SHmax publicado (67,5 grados) cae dentro de su IC.", "",
          "## Qué no prueba", "",
          "- El eje previo usa la misma muestra que el posterior, así que comparten ruido y no son independientes.",
          "- La ventana previa mezcla pretendencia con selección de padres: un eje previo definido no separa esas dos lecturas.",
          "- Es una condición necesaria, no un test de causa: solo pide que el eje no esté ya antes de la fractura.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
