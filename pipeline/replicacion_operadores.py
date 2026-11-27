"""Replicacion por operador dentro de Vaca Muerta: la brecha del mes 1 medida operador por operador (ronda 3, S5).

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla, y el plan que
nombra (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto de la regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-27, ronda 3 de docs/plan-siguiente-nivel.md). Este commit trae la regla, las constantes y
las firmas; no se calculo ninguna brecha de un operador medida solo con sus eventos antes de fijarla. Si algo resulta ambiguo al
calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocen la brecha del mes 1 de la muestra completa (unos 23 puntos menos), las 7 salidas de
pipeline.robustez_operador (sacando de a un operador, la brecha puntual queda entre -24,1 y -22,2 puntos) y que esos 7 operadores
tienen al menos 50 eventos cercanos. Tambien se conoce el veredicto de la familia de cuencas (se replica en 1 de 2).

Pregunta. pipeline.robustez_operador prueba que ningun operador produce la brecha por si solo (sacar de a uno). Esta prueba es la
otra mitad: si la brecha aparece dentro de cada operador, con sus padres cercanos contra sus padres de control. Es la lectura de
pipeline.familia (cuenca por cuenca, sin efecto comun) aplicada a los operadores de una misma cuenca.

Datos y marco (los de pipeline.robustez_operador, sin cambios):
  * d = placebo.cargar(con); m = placebo.marco(d, d["hijo_mes"], ks=(1,), base=placebo.BASE_ORIGINAL). El operador de cada
    evento es el de su PADRE, como en robustez_operador.cargar_eventos (operador de int_pozo_ubicacion ordenada por pozo_id,
    indexado por m["padre"]).
  * Brecha previa limpia: mp = placebo.marco(d, d["hijo_mes"], ks=(-1,), base=placebo.BASE_LIMPIA), con el operador del padre
    por el mismo camino.
  * Placebo de fechas: mf = placebo.marco(d, d["hijo_mes"] + DESPLAZAMIENTO_PLACEBO, solo_reales=True), como lo arma
    placebo.tabla_fechas para ese desplazamiento, con el operador del padre por el mismo camino.
  * Operadores medidos: robustez_operador.grupos_a_sacar(m, operador), es decir los que tienen al menos MIN_CERCANOS = 50 eventos
    cercanos con indice del mes 1 observado. Es el mismo conjunto fijo de la prueba de sacar de a uno, elegido por conteo y no
    por resultado. Los operadores mas chicos no se leen solos.

Por operador X, con los eventos cuyo padre es de X en las dos bandas (cercanos a menos de 1 km, control a 2 a 5 km):
  * brecha del mes 1 y su IC 95%: placebo.brecha_ic(m["idx"][1][mk], m["banda"][mk], m["clave"][mk], placebo.REPS_BOOT,
    placebo.SEMILLA_PLACEBO), con mk = (operador == X);
  * brecha previa: placebo.brecha_ic(mp["idx"][-1][mkp], mp["banda"][mkp], mp["clave"][mkp], placebo.REPS_BOOT,
    placebo.SEMILLA_PLACEBO)["brecha"];
  * placebo: placebo.brecha_ic(mf["idx"][1][mkf], mf["banda"][mkf], mf["clave"][mkf], placebo.REPS_BOOT, SEMILLA_FECHAS), con
    SEMILLA_FECHAS la que usa placebo.tabla_fechas para el desplazamiento -12 (placebo.SEMILLA_PLACEBO + 201);
  * lectura: (se_replica, valor) = replicacion.lectura(brecha, ic_alto, brecha_previa), es decir que se replica si el IC 95%
    queda entero bajo cero y la brecha previa es menor, en valor absoluto, que la del mes 1. Ademas el placebo tiene que estar
    limpio: su ic_alto es mayor o igual que cero. Un placebo que tambien da una brecha entera bajo cero anula la replicacion de X
    ("no se replica: el placebo de fechas tambien da brecha").
  * No se pudo medir: menos de MIN_CONTROLES = 50 eventos de control con indice del mes 1 observado, o la brecha, su IC, la
    brecha previa o el ic_alto del placebo sin valor (placebo.brecha_ic no da IC con menos de 5 eventos en una banda). Cuenta en
    n con su motivo escrito, como una cuenca que no se pudo medir en pipeline.familia.

Lectura de la familia: "Se replica en k de n operadores: <operador> (<lectura>); ...", con n todos los operadores medidos (los que
no se pudieron medir incluidos) y k los que se replican, en el orden de grupos_a_sacar. No hay promedio, peso ni estimacion
conjunta. Se publica cualquiera sea k, tambien k = 0.

Que se publica:
  * mart_replicacion_operadores: una fila por operador (COLS_REP_OP) y una fila de familia (COLS_FAM_OP: k, n, frase);
  * la pagina wiki/hallazgos/replicacion_operadores.md, con la tabla, la frase y lo que no prueba;
  * en un PR de texto aparte, una frase en la pregunta de validez externa del README y de la portada ("Dentro de Vaca Muerta,
    con la misma regla, ..."), con sus claims.

Validacion fijada antes de leer cifras reales (tests/test_replicacion_operadores.py, con eventos sinteticos):
  * una brecha plantada de BRECHA_PLANTADA puntos en los cercanos de un operador sintetico, con la de los otros en cero, da "se
    replica" en ese y "no se replica" en los otros;
  * un operador cuyo placebo de fechas tambien da brecha queda en "no se replica" aunque su brecha del mes 1 pase;
  * k y n cuentan a los que no se pudieron medir como en pipeline.familia.

Que no prueba: dentro de un operador cambian el area y el ano, asi que la brecha por operador no separa al operador de su area.
k de n es un recuento, no una prueba conjunta: cada operador se lee a 95% por separado. Un mismo padre puede estar en varios
eventos; la clave de pad hijo no separa esa dependencia.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np

from pipeline import placebo, replicacion, robustez_operador
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g, _pts

SEMILLA_FECHAS = placebo.SEMILLA_PLACEBO + 201   # la de placebo.tabla_fechas para el desplazamiento -12

# ---- regla fijada (no cambiar despues de ver cifras) ----
MIN_CERCANOS = 50             # el piso de pipeline.robustez_operador; los grupos salen de robustez_operador.grupos_a_sacar
MIN_CONTROLES = 50            # eventos de control con indice del mes 1 observado para que un operador se pueda medir
DESPLAZAMIENTO_PLACEBO = -12  # meses que se corre la fecha del hijo en el placebo de fechas
BRECHA_PLANTADA = -0.20       # brecha plantada en la validacion sintetica (fraccion del indice, -20 puntos)
LECTURAS_OP = ("se replica", "no se replica", "no se pudo medir")

COLS_REP_OP = [("operador", "varchar"), ("n_cercanos", "integer"), ("n_control", "integer"), ("brecha", "double"),
               ("ic_bajo", "double"), ("ic_alto", "double"), ("brecha_previa", "double"), ("placebo_brecha", "double"),
               ("placebo_ic_alto", "double"), ("placebo_limpio", "boolean"), ("valor", "double"),
               ("se_replica", "boolean"), ("lectura", "varchar")]
COLS_FAM_OP = [("k", "integer"), ("n", "integer"), ("frase", "varchar")]
PAGINA = Path("wiki/hallazgos/replicacion_operadores.md")


def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and np.isnan(x)) or bool(np.isnan(x))


def lectura_operador(brecha: float, ic_alto: float, brecha_previa: float, placebo_ic_alto: float,
                     n_control: int) -> tuple[bool | None, float, str]:
    """(se_replica o None si no se pudo medir, valor, lectura) segun la regla de arriba."""
    if n_control < MIN_CONTROLES:
        return None, float("nan"), f"no se pudo medir: {_g(n_control)} eventos de control con índice del mes 1 observado, menos de {MIN_CONTROLES}"
    for nombre, x in (("la brecha", brecha), ("su IC", ic_alto), ("la brecha previa", brecha_previa), ("el IC del placebo de fechas", placebo_ic_alto)):
        if _nan(x):
            return None, float("nan"), f"no se pudo medir: {nombre} no tiene valor"
    se_replica, valor = replicacion.lectura(brecha, ic_alto, brecha_previa)
    if se_replica and placebo_ic_alto < 0:
        return False, valor, "no se replica: el placebo de fechas también da brecha"
    if se_replica:
        return True, valor, "se replica"
    if ic_alto >= 0:
        return False, valor, "no se replica: el IC 95% no queda entero bajo cero"
    return False, valor, "no se replica: la brecha previa no es menor que la del mes 1"


def lectura_familia_op(resultados: list[tuple[str, bool | None, str]]) -> dict:
    """`resultados`: (operador, se_replica o None, lectura) en el orden de grupos_a_sacar. Devuelve k, n y la frase."""
    k = sum(1 for _, r, _ in resultados if r is True)
    n = len(resultados)
    frase = f"Se replica en {k} de {n} operadores" + (": " + "; ".join(f"{op} ({lec})" for op, _, lec in resultados) if n else "") + "."
    return {"k": k, "n": n, "frase": frase}


def medir_operadores(m: dict, mp: dict, mf: dict, ops_m, ops_mp, ops_mf, reps: int = placebo.REPS_BOOT) -> tuple[list[tuple], tuple]:
    """Filas de COLS_REP_OP y la fila de COLS_FAM_OP a partir de los tres marcos y el operador del padre de cada evento."""
    ops_m, ops_mp, ops_mf = np.asarray(ops_m), np.asarray(ops_mp), np.asarray(ops_mf)
    filas, resultados = [], []
    for op in robustez_operador.grupos_a_sacar(m, ops_m, MIN_CERCANOS):
        mk, mkp, mkf = ops_m == op, ops_mp == op, ops_mf == op
        r = placebo.brecha_ic(m["idx"][1][mk], m["banda"][mk], m["clave"][mk], reps, placebo.SEMILLA_PLACEBO)
        previa = placebo.brecha_ic(mp["idx"][-1][mkp], mp["banda"][mkp], mp["clave"][mkp], reps, placebo.SEMILLA_PLACEBO)["brecha"]
        pl = placebo.brecha_ic(mf["idx"][1][mkf], mf["banda"][mkf], mf["clave"][mkf], reps, SEMILLA_FECHAS)
        se_replica, valor, lec = lectura_operador(r["brecha"], r["ic_alto"], previa, pl["ic_alto"], r["n_ctrl"])
        limpio = None if _nan(pl["ic_alto"]) else bool(pl["ic_alto"] >= 0)
        filas.append((op, r["n_near"], r["n_ctrl"], r["brecha"], r["ic_bajo"], r["ic_alto"], previa, pl["brecha"], pl["ic_alto"],
                      limpio, valor, se_replica, lec))
        resultados.append((op, se_replica, lec))
    fam = lectura_familia_op(resultados)
    return filas, (fam["k"], fam["n"], fam["frase"])


def calcular(con) -> tuple[list[tuple], tuple]:
    """Filas de COLS_REP_OP y la fila de COLS_FAM_OP, con los datos y el marco de arriba."""
    d = placebo.cargar(con)
    m = placebo.marco(d, d["hijo_mes"], ks=(1,), base=placebo.BASE_ORIGINAL)
    mp = placebo.marco(d, d["hijo_mes"], ks=(-1,), base=placebo.BASE_LIMPIA)
    mf = placebo.marco(d, d["hijo_mes"] + DESPLAZAMIENTO_PLACEBO, solo_reales=True)
    ops = np.array([r[0] or "" for r in con.execute("select operador from int_pozo_ubicacion order by pozo_id").fetchall()])
    return medir_operadores(m, mp, mf, ops[m["padre"]], ops[mp["padre"]], ops[mf["padre"]])


def pagina_replicacion_operadores(filas: list[tuple], fam: tuple) -> str:
    k, n, frase = fam
    L = ["# Replicación por operador dentro de Vaca Muerta", "",
         "Se mide la brecha del mes 1 (eventos cercanos a menos de 1 km menos controles a 2 a 5 km, mediana del índice) operador por operador, "
         "con los eventos cuyo padre es de ese operador en las dos bandas. Es la otra mitad de la prueba de sacar de a uno "
         "([robustez_operador.md](robustez_operador.md)): allá se prueba que ningún operador produce la brecha por sí solo; acá, si la brecha "
         "aparece dentro de cada uno.", "",
         f"**{frase}**", "",
         "| Operador | Eventos cercanos | Eventos control | Brecha mes 1 (puntos) | IC 95% | Brecha previa (puntos) | Placebo de fechas (puntos) | Placebo, IC alto | Lectura |",
         "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    for op, nn, nc, g, lo, hi, previa, pb, pih, _lim, _val, _rep, lec in filas:
        L.append(f"| {op} | {_g(nn)} | {_g(nc)} | {_pts(g)} | {_pts(lo)} a {_pts(hi)} | {_pts(previa)} | {_pts(pb)} | {_pts(pih)} | {lec} |")
    L += ["", "## Regla fijada antes de calcular", "",
          "Fijada en el commit `de19052` (2026-11-27), antes de calcular ninguna brecha de un operador medido solo con sus eventos; el texto y las "
          "constantes están en `pipeline/replicacion_operadores.py` y en `docs/reglas-fijadas.md`.", "",
          f"- Se miden los operadores con al menos {MIN_CERCANOS} eventos cercanos con índice del mes 1 observado (el conjunto de `pipeline.robustez_operador`, "
          "elegido por conteo y no por resultado).",
          "- Un operador se replica si el IC 95% de su brecha del mes 1 queda entero bajo cero, su brecha previa limpia es menor en valor absoluto "
          "y su placebo de fechas (hijo corrido 12 meses antes) no da una brecha entera bajo cero.",
          f"- No se pudo medir con menos de {MIN_CONTROLES} eventos de control con índice del mes 1 observado, o sin valor en la brecha, su IC, "
          "la brecha previa o el IC del placebo; cuenta en n con su motivo.",
          "- La lectura de la familia es un recuento: no hay promedio, peso ni estimación conjunta, y se publica cualquiera sea k.", "",
          "## Qué no prueba", "",
          "- Dentro de un operador cambian el área y el año, así que la brecha por operador no separa al operador de su área.",
          "- k de n es un recuento, no una prueba conjunta: cada operador se lee a 95% por separado.",
          "- Un mismo padre puede estar en varios eventos; la clave de pad hijo no separa esa dependencia.",
          "- El placebo de fechas se lee de una cola, como dice la regla: una brecha del placebo entera sobre cero no anula la "
          "réplica. La lectura con dos colas, fijada después de ver estas cifras, está en "
          "[replicacion_operadores_agua.md](replicacion_operadores_agua.md), con su etiqueta post hoc.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    """Escribe mart_replicacion_operadores y la pagina."""
    con = duckdb.connect(str(path))
    filas, fam = calcular(con)
    _escribir(con, "mart_replicacion_operadores", COLS_REP_OP, filas)
    _escribir(con, "mart_replicacion_operadores_familia", COLS_FAM_OP, [fam])
    PAGINA.parent.mkdir(parents=True, exist_ok=True)
    PAGINA.write_text(pagina_replicacion_operadores(filas, fam), encoding="utf-8")
    for r in filas:
        print(f"[replicacion_operadores] {r[0]:<28} n={r[1]}/{r[2]} brecha={100 * r[3]:+.1f} IC {100 * r[4]:+.1f} a {100 * r[5]:+.1f} "
              f"previa={100 * r[6]:+.1f} placebo_ic_alto={100 * r[8]:+.1f} -> {r[12]}")
    print(f"[replicacion_operadores] {fam[2]}")
    print(f"escrito mart_replicacion_operadores ({len(filas)} filas) y {PAGINA}")


if __name__ == "__main__":
    main()
