"""Robustez por operador y por area del resultado del estudio de eventos: sacar de a uno, y ver si la brecha y el cierre se sostienen.

Se corre despues de pipeline.placebo:  uv run python -m pipeline.robustez_operador

REGLA FIJADA ANTES DE CORRER (2026-11-17, antes de calcular ninguna cifra de este modulo; no se cambia despues de ver resultados).
Solo se miraron conteos de eventos por operador y por area (cuantos eventos cercanos y control tiene cada grupo) para fijar el piso de
grupo de abajo; ninguna brecha por grupo. Los dos numeros que se ponen a prueba ya estan publicados con la muestra completa: la brecha
del mes 1 (cercanos a menos de 1 km menos controles a 2 a 5 km, todas las edades, mediana del indice, unos 23 puntos menos) y la brecha
del mes 6 (cerca de cero: el cierre). El umbral CIERRE_PUNTOS se fijo conociendo el valor completo del mes 6 (-2,1 puntos); se dice en
la pagina. Se publican todos los resultados, favorables o no.

Datos y marco (sin cambios respecto de pipeline.placebo): placebo.cargar(con), placebo.marco(D, D["hijo_mes"], ks=(1, 6),
base=placebo.BASE_ORIGINAL). El operador y el area son los del PADRE del evento: operador de int_pozo_ubicacion ordenada por pozo_id
(el mismo orden que placebo.cargar) indexada por m["padre"]; el area es m["area"]. La brecha y su IC 95% son
placebo.brecha_ic(m["idx"][k], banda, clave, REPS_BOOT, placebo.SEMILLA_PLACEBO), con la clave de pad hijo del marco completo y el
mismo conjunto de eventos menos el grupo sacado.

Que se saca: cada operador (y por separado cada area) con al menos MIN_CERCANOS = 50 eventos cercanos con indice del mes 1 observado en
la muestra completa. Se saca un grupo por vez (leave-one-out) y se recalcula la brecha del mes 1 y la del mes 6. Es un conjunto fijo
de grupos por conteo, no elegido por resultado. Los grupos chicos no se sacan solos (con menos de 50 eventos cercanos la brecha propia
no se estima bien) pero siguen dentro de la muestra de los demas.

Reglas de veredicto (cada eje por separado, operador y area):
  * La brecha del mes 1 "se sostiene" si en TODAS las salidas de grupo el IC 95% excluye el cero (ic_alto < 0) y la brecha puntual
    sigue siendo al menos la mitad de la completa en valor absoluto. Si no, "no se sostiene en la salida de <grupo>" y se nombra el peor.
  * El cierre del mes 6 "se sostiene" si en TODAS las salidas de grupo la brecha puntual del mes 6 queda por encima de -CIERRE_PUNTOS
    (CIERRE_PUNTOS = 5 puntos). Si no, se nombra el grupo que lo rompe.
  * Se publican: la brecha completa, para cada grupo sacado la brecha con IC, el rango (minimo y maximo de la brecha puntual) y el peor
    caso (la salida que deja la brecha del mes 1 mas cerca de cero; la que deja la del mes 6 mas lejos de cero) con su cota superior
    (ic_alto). Nunca se escribe que un efecto queda "descartado": el rango es sobre estas salidas, no una cota de todas las posibles.

Colorado: el replicador de la dosis en el Colorado necesita arena, etapas o presion de tratamiento. pipeline/colorado/sql/02_core.sql
declara etapas, arena_tn y presion_maxima_psi como nulos (el dato publico del Colorado no los trae). Si es asi no se replica el nulo de
dosis en el Colorado y la pagina lo dice, sin simular ni imputar nada.

Que NO prueba:
  * Sacar un operador no es una prueba de que otro operador de otra cuenca o de otra practica de pad tenga la misma brecha: es una
    prueba de que ninguno de estos grupos, por si solo, produce el resultado.
  * La dependencia entre eventos del mismo pad hijo se conserva con la clave de pad hijo, pero un mismo padre puede aparecer en varios
    eventos; los IC no la separan.
  * Los grupos chicos no se prueban solos. No hay correccion por comparaciones multiples entre las salidas.
  * El operador es el del padre del evento y no el del hijo; en los eventos control el hijo puede ser de otro operador (se miro despues de
    correr, sin cambiar la regla), asi que sacar un operador saca sus padres, no necesariamente sus hijos.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import placebo
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g, _pts

MIN_CERCANOS = 50        # eventos cercanos con indice del mes 1 observado para que un grupo se saque solo
CIERRE_PUNTOS = 5.0      # el cierre se sostiene si la brecha del mes 6 queda por encima de -CIERRE_PUNTOS puntos
MITAD = 0.5              # la brecha del mes 1 se sostiene si queda al menos en esta fraccion de la completa
KS = (1, 6)
EJES = ("operador", "area")
COMPLETA = "(muestra completa)"
NOMBRE = {"operador": "operador", "area": "área"}

COLS_ROB_OP = [("eje", "varchar"), ("salida", "varchar"), ("k", "integer"), ("n_cercanos", "integer"), ("n_control", "integer"),
               ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_VER_OP = [("eje", "varchar"), ("gap1_sostiene", "boolean"), ("cierre_sostiene", "boolean"), ("peor_gap1", "varchar"),
               ("peor_cierre", "varchar"), ("texto", "varchar")]


def cargar_eventos(con) -> tuple[dict, dict]:
    """Marco del estudio (k = 1 y 6) y, por evento, operador y area del padre."""
    d = placebo.cargar(con)
    m = placebo.marco(d, d["hijo_mes"], ks=KS, base=placebo.BASE_ORIGINAL)
    ops = np.array([r[0] or "" for r in con.execute("select operador from int_pozo_ubicacion order by pozo_id").fetchall()])
    return m, {"operador": ops[m["padre"]], "area": np.asarray(m["area"])}


def grupos_a_sacar(m: dict, etiqueta: np.ndarray, minimo: int = MIN_CERCANOS) -> list[str]:
    """Grupos con al menos `minimo` eventos cercanos con indice del mes 1 observado, de mayor a menor (desempate por nombre)."""
    ok = ~np.isnan(m["idx"][1]) & (m["banda"] == 0)
    cuenta = {g: int((ok & (etiqueta == g)).sum()) for g in np.unique(etiqueta[ok])}
    return [g for g, c in sorted(cuenta.items(), key=lambda x: (-x[1], x[0])) if c >= minimo and g != ""]


def tabla_salidas(m: dict, por_eje: dict, reps: int = placebo.REPS_BOOT) -> list[tuple]:
    """Filas (eje, salida, k, n_cercanos, n_control, brecha, ic_bajo, ic_alto): la completa y cada salida de un grupo."""
    filas = []
    for eje in EJES:
        et = por_eje[eje]
        for salida in [COMPLETA] + grupos_a_sacar(m, et):
            mk = np.ones(len(et), dtype=bool) if salida == COMPLETA else et != salida
            for k in KS:
                r = placebo.brecha_ic(m["idx"][k][mk], m["banda"][mk], m["clave"][mk], reps, placebo.SEMILLA_PLACEBO)
                filas.append((eje, salida, k, r["n_near"], r["n_ctrl"], r["brecha"], r["ic_bajo"], r["ic_alto"]))
    return filas


def veredicto_eje(filas: list[tuple], eje: str) -> dict:
    """Aplica la regla fijada a las filas de un eje; devuelve los codigos, el peor caso de cada resultado y el texto."""
    f = [x for x in filas if x[0] == eje]
    comp = {x[2]: x for x in f if x[1] == COMPLETA}
    sal = [x for x in f if x[1] != COMPLETA]
    g1 = [x for x in sal if x[2] == 1]
    g6 = [x for x in sal if x[2] == 6]
    if not g1 or 1 not in comp:
        return {"eje": eje, "gap1": False, "cierre": False, "peor1": None, "peor6": None, "texto": f"No hay grupos con al menos {MIN_CERCANOS} eventos cercanos por {NOMBRE[eje]}."}
    umbral = MITAD * abs(comp[1][5])
    peor1 = max(g1, key=lambda x: x[5])   # la brecha del mes 1 mas cerca de cero
    peor6 = min(g6, key=lambda x: x[5])   # la del mes 6 mas lejos de cero (mas negativa)
    gap1 = all(x[7] < 0 and abs(x[5]) >= umbral for x in g1)
    cierre = all(x[5] > -CIERRE_PUNTOS / 100 for x in g6)
    return {"eje": eje, "gap1": gap1, "cierre": cierre, "peor1": peor1, "peor6": peor6,
            "min1": min(x[5] for x in g1), "max1": max(x[5] for x in g1), "min6": min(x[5] for x in g6), "max6": max(x[5] for x in g6),
            "n_grupos": len(g1), "texto": ""}


def _frase(v: dict) -> str:
    eje = NOMBRE[v["eje"]]
    if v["peor1"] is None:
        return v["texto"]
    p1, p6 = v["peor1"], v["peor6"]
    a = (f"La brecha del mes 1 se sostiene al sacar de a un {eje}: en las {v['n_grupos']} salidas el IC 95% excluye el cero y la brecha puntual "
         f"queda entre {_pts(v['min1'])} y {_pts(v['max1'])} puntos; el peor caso es sin {p1[1]} ({_pts(p1[5])} puntos, IC 95% {_pts(p1[6])} a "
         f"{_pts(p1[7])}, cota superior {_pts(p1[7])})." if v["gap1"] else
         f"La brecha del mes 1 no se sostiene al sacar de a un {eje} con la regla fijada: el peor caso es sin {p1[1]} ({_pts(p1[5])} puntos, "
         f"IC 95% {_pts(p1[6])} a {_pts(p1[7])}).")
    b = (f"El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre {_pts(v['min6'])} y {_pts(v['max6'])} puntos, sin pasar de "
         f"-{_g(CIERRE_PUNTOS, 1)}; el peor caso es sin {p6[1]} ({_pts(p6[5])} puntos)." if v["cierre"] else
         f"El cierre del mes 6 no se sostiene con la regla fijada: sin {p6[1]} la brecha puntual del mes 6 es de {_pts(p6[5])} puntos "
         f"(IC 95% {_pts(p6[6])} a {_pts(p6[7])}).")
    return a + " " + b


def colorado_sin_dosis(con_colorado=None) -> bool:
    """Verdadero si el Colorado declara arena, etapas y presion como nulos (no hay con que replicar el nulo de dosis)."""
    sql = (DATA.parent / "pipeline" / "colorado" / "sql" / "02_core.sql")
    if not sql.exists():
        return True
    t = sql.read_text(encoding="utf-8")
    return all(f"null::{tp}" in t and f"as {c}" in t for tp, c in (("integer", "etapas"), ("double", "arena_tn"), ("double", "presion_maxima_psi")))


def pagina_robustez_operador(con) -> str:
    filas = con.execute("select * from mart_robustez_operador order by eje, salida, k").fetchall()
    ver = {r[0]: r for r in con.execute("select * from mart_robustez_operador_veredicto").fetchall()}
    L = ["# Robustez por operador y por área: sacar de a uno", "",
         "Se saca de a un grupo (el operador o el área del pozo padre) y se vuelve a medir la brecha del mes 1 (cercanos a menos de 1 km menos "
         "controles a 2 a 5 km, todas las edades, mediana del índice) y la del mes 6. Es una prueba de que ningún grupo grande produce el "
         "resultado por sí solo; no mueve el veredicto del estudio de eventos.", ""]
    for eje in EJES:
        v = ver.get(eje)
        L += [f"## Sacando de a un {NOMBRE[eje]}", "", v[5] if v else "Sin datos.", "",
              "| Sin | Eventos cercanos (mes 1) | Eventos control (mes 1) | Brecha mes 1 (puntos) | IC 95% | Brecha mes 6 (puntos) | IC 95% |",
              "| --- | ---: | ---: | ---: | --- | ---: | --- |"]
        por = {}
        for e, s, k, nn, nc, g, lo, hi in filas:
            if e == eje:
                por.setdefault(s, {})[k] = (nn, nc, g, lo, hi)
        for s, d in por.items():
            a, b = d.get(1), d.get(6)
            if not a or not b:
                continue
            L.append(f"| {s} | {_g(a[0])} | {_g(a[1])} | {_pts(a[2])} | {_pts(a[3])} a {_pts(a[4])} | {_pts(b[2])} | {_pts(b[3])} a {_pts(b[4])} |")
        L.append("")
        if v and v[3] is not None:
            sub = [x for x in filas if x[0] == eje and x[1] != COMPLETA and x[2] == 1]
            alto = max(sub, key=lambda x: x[7])
            L += [f"Agregado después de ver los resultados (no cambia el veredicto): la cota superior más alta del IC 95% de la brecha del mes 1 "
                  f"entre las salidas es {_pts(alto[7])} puntos, sin {alto[1]}.", ""]
    L += ["## Regla fijada antes de correr", "",
          f"- Se saca de a uno cada operador y cada área con al menos {MIN_CERCANOS} eventos cercanos con índice del mes 1 observado "
          "(un conteo, no un resultado).",
          "- La brecha del mes 1 se sostiene si en todas las salidas el IC 95% excluye el cero y la brecha puntual queda al menos en la mitad de la completa.",
          f"- El cierre del mes 6 se sostiene si en todas las salidas la brecha del mes 6 queda por encima de -{_g(CIERRE_PUNTOS, 1)} puntos; "
          "ese umbral se fijó conociendo la brecha completa del mes 6.",
          "- Mismo marco, mismas repeticiones y misma semilla que el estudio de placebo.", "",
          "## Colorado", ""]
    if colorado_sin_dosis():
        L += ["El nulo de dosis no se replica en el Colorado: el dato público de esa cuenca no trae arena, etapas ni presión de tratamiento "
              "(las tres columnas quedan nulas en `pipeline/colorado/sql/02_core.sql`), y sin esas variables no hay con qué repetir el modelo. "
              "No se simula ni se imputa nada.", ""]
    else:
        L += ["El Colorado trae variables de dosis; la réplica del nulo de dosis queda fuera de este módulo.", ""]
    L += ["## Qué no prueba", "",
          "- No prueba que otro operador u otra práctica de pad tenga la misma brecha; prueba que ninguno de estos grupos por sí solo la produce.",
          "- Los grupos con menos de 50 eventos cercanos no se sacan solos y no hay corrección por comparaciones múltiples entre las salidas.",
          "- Los IC conservan la dependencia por pad hijo pero no la de un mismo padre en varios eventos.",
          "- El operador es el del padre del evento, no el del hijo: en una parte de los eventos control el hijo es de otro operador, así que sacar un "
          "operador saca sus padres y no necesariamente sus hijos.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    m, por_eje = cargar_eventos(con)
    filas = tabla_salidas(m, por_eje)
    _escribir(con, "mart_robustez_operador", COLS_ROB_OP, filas)
    vers = []
    for eje in EJES:
        v = veredicto_eje(filas, eje)
        p1 = v["peor1"][1] if v["peor1"] else None
        p6 = v["peor6"][1] if v["peor6"] else None
        vers.append((eje, v["gap1"], v["cierre"], p1, p6, _frase(v)))
    _escribir(con, "mart_robustez_operador_veredicto", COLS_VER_OP, vers)
    for r in filas:
        print(f"[robustez_operador] {r[0]:<8} {r[1]:<34} k={r[2]} n={r[3]}/{r[4]} brecha={100 * r[5]:+.1f} IC {100 * r[6]:+.1f} a {100 * r[7]:+.1f}")
    for r in vers:
        print(f"[robustez_operador] {r[0]}: {r[5]}")


if __name__ == "__main__":
    main()
