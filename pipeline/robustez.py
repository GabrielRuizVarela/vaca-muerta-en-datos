"""Robustez del eje de interferencia y del costo: re-estimaciones en subconjuntos y especificaciones alternativas.

Se corre despues de pipeline.costo:  uv run python -m pipeline.robustez

Escribe en data/warehouse.duckdb (create or replace, idempotente, con semilla fija):
  mart_robustez_eje    eje de la cuenca (con efectos fijos de area) en subconjuntos de eventos
  mart_robustez_costo  coeficiente desvio_eje_10 del modelo de costo en especificaciones alternativas

Eje: se reusa el estimador de pipeline.costo (nucleo axial coseno, bootstrap por pads hijo, permutacion por bloques)
sobre (a) tres periodos de fractura del hijo con igual cantidad de eventos, (b) padres de YPF contra el resto de los
operadores, (c) la cuenca sin cada una de las 5 areas mas grandes, (d) dos bandas de distancia, (e) la muestra sin el
5% de eventos con mayor caida absoluta. Costo: se reajusta tabla_costo con el resultado winsorizado al 1% y 99%, sin
padres parados, sin cada una de las 3 areas mas grandes y solo entre 0,3 y 1 km. Se usan las mismas repeticiones y
semilla que pipeline.costo (REPS_EJE_ROB, REPS_PERM_ROB, REPS_COSTO_ROB), asi que la fila completa reproduce los
numeros publicados.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import costo
from pipeline.costo import (ANCHO_MAX, KM_MIN_EJE, P_EJE_COSTO, REPS_COSTO, REPS_EJE, REPS_PERM, SEMILLA, _arr, _controles_eje, _dif_axial, _escribir,
                            _filas, _g, _rosa, eje_con_intervalo, tabla_costo)
from pipeline.ingest import DATA

SHMAX = 67.5             # eje del SHmax publicado (OSO-ENE) en la convencion de rumbo de esta pagina
REPS_EJE_ROB = REPS_EJE      # las mismas repeticiones y semilla que pipeline.costo: la fila completa reproduce esas paginas
REPS_PERM_ROB = REPS_PERM
REPS_COSTO_ROB = REPS_COSTO
MIN_N_SUB = 40           # eventos minimos para estimar un eje en un subconjunto
N_AREAS_EJE = 5
N_AREAS_COSTO = 3
RECORTE = 0.05           # fraccion de eventos con mayor caida absoluta que se descarta en la muestra recortada
PERIODOS = 3

COLS_EJE = [("grupo", "varchar"), ("subconjunto", "varchar"), ("n", "integer"), ("eje", "double"),
            ("ic_bajo", "double"), ("ic_alto", "double"), ("ancho_ic", "double"), ("p_perm", "double"),
            ("dif_eje_completo", "double"), ("dif_shmax", "double")]
COLS_COSTO = [("especificacion", "varchar"), ("n", "integer"), ("coef", "double"), ("ic_bajo", "double"),
              ("ic_alto", "double"), ("mismo_signo", "boolean"), ("ic_excluye_cero", "boolean")]

EVENTO_OPERADOR_SQL = "select padre, mes_frac, operador from int_interferencia_evento where banda = 'cercano'"


# ------------------------------------------------------------------ eje

def _gs(x: float) -> str:
    """Entero con signo de menos solo si no se redondea a cero."""
    return _g(0.0) if round(x) == 0 else _g(x)


def _caida(filas: list[dict]) -> np.ndarray:
    return np.clip(_arr(filas, "indice_control"), 0, 2) - np.clip(_arr(filas, "indice"), 0, 2)


def en_banda(filas: list[dict], km_lo: float = KM_MIN_EJE, km_hi: float = 1.0) -> list[dict]:
    return [f for f in filas if km_lo <= f["km_min"] < km_hi]


def eje_subconjunto(filas: list[dict], km_lo: float = KM_MIN_EJE, km_hi: float = 1.0,
                    reps: int = REPS_EJE_ROB, reps_perm: int = REPS_PERM_ROB, semilla: int = SEMILLA) -> dict | None:
    """Eje de la cuenca (efectos fijos de area, como en tabla_anisotropia) con los eventos de `filas` entre km_lo y km_hi.

    Devuelve None si quedan menos de MIN_N_SUB eventos. Las claves son n, eje, ic_bajo, ic_alto, ancho_ic y p_perm.
    """
    f = en_banda(filas, km_lo, km_hi)
    if len(f) < MIN_N_SUB:
        return None
    area = np.array([x["area"] for x in f])
    cod = np.unique(area, return_inverse=True)[1]
    ev = {"km": _arr(f, "km_min"), "edad": _arr(f, "edad_meses")}
    clave = np.array([str(x["pad_hijo"]) for x in f])
    r = eje_con_intervalo(_caida(f), _controles_eje(ev), _arr(f, "rumbo_eje"), clave, grupo=cod,
                          reps=reps, reps_perm=reps_perm, semilla=semilla)
    return {"n": len(f), "eje": r["eje"], "ic_bajo": r["ic_bajo"], "ic_alto": r["ic_alto"], "ancho_ic": r["ancho_ic"],
            "p_perm": r["p_perm"]}


def _por_periodo(f: list[dict]) -> list[tuple[str, list[dict]]]:
    orden = sorted(range(len(f)), key=lambda i: (f[i]["mes_frac"], i))
    out = []
    for k in range(PERIODOS):
        idx = orden[k * len(f) // PERIODOS:(k + 1) * len(f) // PERIODOS]
        sub = [f[i] for i in idx]
        a, b = sub[0]["mes_frac"].year, sub[-1]["mes_frac"].year
        out.append((f"Fractura del hijo {a} a {b}" if a != b else f"Fractura del hijo {a}", sub))
    return out


def definir_subconjuntos(filas: list[dict]) -> list[tuple[str, str, list[dict], float, float]]:
    """(grupo, nombre, eventos, km_lo, km_hi) de cada subconjunto del eje. Los periodos se parten sobre eventos de 0,3 a 1 km."""
    f = en_banda(filas)
    out = [("periodo", n, s, KM_MIN_EJE, 1.0) for n, s in _por_periodo(f)]
    out.append(("operador", "Padre YPF", [x for x in f if x["operador"] == "YPF"], KM_MIN_EJE, 1.0))
    out.append(("operador", "Padre de otros operadores", [x for x in f if x["operador"] != "YPF"], KM_MIN_EJE, 1.0))
    cuenta: dict[str, int] = {}
    for x in f:
        cuenta[x["area"]] = cuenta.get(x["area"], 0) + 1
    for a in sorted(cuenta, key=lambda k: (-cuenta[k], k))[:N_AREAS_EJE]:
        out.append(("area", f"Sin {a}", [x for x in f if x["area"] != a], KM_MIN_EJE, 1.0))
    out.append(("distancia", "0,3 a 0,6 km", f, 0.3, 0.6))
    out.append(("distancia", "0,6 a 1 km", f, 0.6, 1.0))
    ca = np.abs(_caida(f))
    corte = float(np.percentile(ca, 100 * (1 - RECORTE)))
    out.append(("recortada", "Sin el 5% de mayor caída absoluta", [x for x, c in zip(f, ca) if c <= corte],
                KM_MIN_EJE, 1.0))
    return out


def tabla_robustez_eje(filas: list[dict], reps: int = REPS_EJE_ROB, reps_perm: int = REPS_PERM_ROB) -> list[tuple]:
    completo = eje_subconjunto(filas, reps=reps, reps_perm=reps_perm)
    out = []

    def fila(grupo, nombre, r):
        return (grupo, nombre, int(r["n"]), r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], r["p_perm"],
                float(_dif_axial(r["eje"], completo["eje"])), float(_dif_axial(r["eje"], SHMAX)))

    out.append(fila("completa", "Muestra completa", completo))
    for grupo, nombre, sub, lo, hi in definir_subconjuntos(filas):
        r = eje_subconjunto(sub, lo, hi, reps=reps, reps_perm=reps_perm)
        if r is not None:
            out.append(fila(grupo, nombre, r))
    return out


def ic_contiene(eje: float, ic_bajo: float, ic_alto: float, ancho_ic: float, punto: float) -> bool:
    """True si el IC circular [ic_bajo, ic_alto] alrededor de `eje` contiene `punto` (ejes en grados, modulo 180)."""
    if ancho_ic >= 180 - 1e-9:
        return True
    d = float(_dif_axial(punto, eje))
    return float(_dif_axial(ic_bajo, eje)) - 1e-9 <= d <= float(_dif_axial(ic_alto, eje)) + 1e-9


def veredicto_eje(filas: list[dict]) -> str:
    """Frase de veredicto a partir de las filas de mart_robustez_eje (diccionarios). La de grupo 'completa' es la base."""
    base = next(r for r in filas if r["grupo"] == "completa")
    sub = [r for r in filas if r["grupo"] != "completa"]
    if not sub:
        return "No hubo subconjuntos con eventos suficientes para evaluar la estabilidad del eje."
    indef = [r for r in sub if r["ancho_ic"] >= ANCHO_MAX]
    defin = [r for r in sub if r["ancho_ic"] < ANCHO_MAX]
    cont = [r for r in sub if ic_contiene(r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], base["eje"])]
    cont_def = [r for r in defin if r in cont]
    fuera = [r["subconjunto"] for r in sub if r not in cont]
    sig = [r for r in defin if r["p_perm"] < P_EJE_COSTO]
    t = (f"El IC de {len(cont)} de {len(sub)} subconjuntos contiene el eje de la muestra completa "
         f"({_g(base['eje'])} grados). ")
    if indef:
        t += (f"En {len(indef)} el IC mide {_g(ANCHO_MAX)} grados o más, así que el eje no está definido ahí "
              f"({'; '.join(r['subconjunto'] for r in indef)}); de los {len(defin)} restantes, {len(cont_def)} lo contienen. ")
    else:
        t += f"Todos tienen un IC de menos de {_g(ANCHO_MAX)} grados. "
    t += f"En {len(sig)} de los {len(defin)} con eje definido el p de permutación es menor que {_g(P_EJE_COSTO, 2)}. "
    if fuera:
        t += "El IC no contiene el eje completo en: " + "; ".join(fuera) + ". "
    sin_p = [r["subconjunto"] for r in sub if r["p_perm"] >= P_EJE_COSTO]
    if sin_p:
        t += (f"Con p de permutación de {_g(P_EJE_COSTO, 2)} o más, o sea sin evidencia de anisotropía en ese corte, quedan "
              f"{len(sin_p)} subconjuntos: " + "; ".join(sin_p) + ". ")
    sh = [r for r in defin if ic_contiene(r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], SHMAX)]
    base_sh = ic_contiene(base["eje"], base["ic_bajo"], base["ic_alto"], base["ancho_ic"], SHMAX)
    t += (f"El IC incluye el SHmax publicado ({_g(SHMAX, 1)} grados) en {len(sh)} de los {len(defin)} con eje definido "
          f"y {'sí' if base_sh else 'no'} en la muestra completa. ")
    if not defin:
        t += "Ningún subconjunto tiene un eje definido: no se puede afirmar estabilidad."
    elif fuera:
        t += "El eje no es estable ante todos los cortes: la conclusión depende del subconjunto."
    elif indef:
        t += "Donde el eje está definido, el IC no lo separa del completo; donde no está definido, el corte no permite decir nada."
    else:
        t += "El eje es estable ante estos cortes."
    return t


# ------------------------------------------------------------------ costo

def _winsorizar(filas: list[dict], p: float = 1.0) -> list[dict]:
    y = np.array([f["petroleo_diferido_bbl"] for f in filas if f["petroleo_diferido_bbl"] is not None], dtype=float)
    lo, hi = np.percentile(y, [p, 100 - p])
    out = []
    for f in filas:
        g = dict(f)
        if g["petroleo_diferido_bbl"] is not None:
            g["petroleo_diferido_bbl"] = float(min(max(g["petroleo_diferido_bbl"], lo), hi))
        out.append(g)
    return out


def definir_especificaciones(filas: list[dict]) -> list[tuple[str, list[dict]]]:
    out = [("Muestra completa", filas),
           ("Resultado winsorizado al 1% y 99%", _winsorizar(filas)),
           ("Sin padres parados", [f for f in filas if not f["parado"]])]
    cuenta: dict[str, int] = {}
    for f in filas:
        cuenta[f["area"]] = cuenta.get(f["area"], 0) + 1
    for a in sorted(cuenta, key=lambda k: (-cuenta[k], k))[:N_AREAS_COSTO]:
        out.append((f"Sin {a}", [f for f in filas if f["area"] != a]))
    out.append(("Solo eventos de 0,3 a 1 km", en_banda(filas)))
    return out


def tabla_robustez_costo(filas: list[dict], ejes: dict, reps: int = REPS_COSTO_ROB) -> list[tuple]:
    out, base = [], None
    for nombre, sub in definir_especificaciones(filas):
        r = next(x for x in tabla_costo(sub, ejes, reps=reps) if x[0] == "desvio_eje_10")
        coef, lo, hi, n = float(r[1]), float(r[3]), float(r[4]), int(r[6])
        if base is None:
            base = coef
        out.append((nombre, n, coef, lo, hi, bool(np.sign(coef) == np.sign(base)), bool(lo > 0 or hi < 0)))
    return out


def veredicto_costo(filas: list[dict]) -> str:
    base, otras = filas[0], filas[1:]
    mismo = [r for r in otras if r["mismo_signo"]]
    excl = [r for r in otras if r["ic_excluye_cero"]]
    t = (f"El coeficiente de la muestra completa es {_g(base['coef'])} bbl por 10 grados "
         f"(IC {_g(base['ic_bajo'])} a {_g(base['ic_alto'])}); "
         f"{'excluye' if base['ic_excluye_cero'] else 'no excluye'} el cero. "
         f"El signo se repite en {len(mismo)} de {len(otras)} especificaciones alternativas y el IC excluye el cero en "
         f"{len(excl)}")
    if excl:
        t += " (" + "; ".join(r["especificacion"] for r in excl) + ")"
    t += ". "
    if not base["ic_excluye_cero"] and not excl:
        t += "Ninguna especificación permite afirmar el efecto: sigue siendo una tendencia, no una conclusión."
    elif excl and len(excl) < len(otras):
        t += "El efecto no es robusto: solo aparece en algunas especificaciones."
    elif excl:
        t += "El efecto aparece en todas las especificaciones alternativas."
    else:
        t += "El efecto del modelo base se sostiene en signo pero no en significancia."
    return t


# ------------------------------------------------------------------ pagina del wiki

def pagina_robustez(con) -> str:
    """Pagina de wiki a partir de las tablas de robustez. Texto en espanol, sin rayas largas."""
    ej = _filas(con, "select * from mart_robustez_eje")
    co = _filas(con, "select * from mart_robustez_costo")
    base = next(r for r in ej if r["grupo"] == "completa")
    L = ["# Robustez del eje y del costo", "",
         "Página generada por `pipeline/robustez.py`. Repite la estimación de `pipeline/costo.py` en subconjuntos de "
         "eventos y con especificaciones alternativas, para ver si el eje de mayor merma y el coeficiente de desvío "
         "respecto del eje dependen de una parte de la muestra. Usa las mismas repeticiones y semilla que la página de anisotropía "
         f"({REPS_EJE_ROB} de bootstrap y {REPS_PERM_ROB} permutaciones para el eje, {REPS_COSTO_ROB} de bootstrap para el costo), "
         "así que la muestra completa reproduce los números de aquella página.", "",
         "## Estabilidad del eje", "",
         f"Eje de la cuenca con efectos fijos de área en eventos de 0,3 a 1 km: {_g(base['eje'])} grados "
         f"({_rosa(base['eje'])}), IC de {_g(base['ic_bajo'])} a {_g(base['ic_alto'])} grados, n = {_g(base['n'])}, "
         f"p de permutación {_g(base['p_perm'], 3)}. El SHmax publicado es unos {_g(SHMAX, 1)} grados.", "",
         "| Grupo | Subconjunto | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Diferencia con el eje completo | Diferencia con SHmax |",
         "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |"]
    for r in ej:
        L.append(f"| {r['grupo']} | {r['subconjunto']} | {_g(r['n'])} | {_g(r['eje'])} | {_g(r['ic_bajo'])} a {_g(r['ic_alto'])} | "
                 f"{_g(r['ancho_ic'])} | {_g(r['p_perm'], 3)} | {_gs(r['dif_eje_completo'])} | {_gs(r['dif_shmax'])} |")
    L += ["", veredicto_eje(ej), "",
          "Las diferencias son con signo, en grados, módulo 180 y en el rango de menos 90 a 90. Un IC que mide "
          f"{_g(ANCHO_MAX)} grados o más no define un eje. Un subconjunto más chico tiene un IC más ancho solo por tener "
          "menos pads hijo, así que un IC ancho no es evidencia contra el eje completo.", "",
          "## Estabilidad del coeficiente de desvío respecto del eje", "",
          "Coeficiente `desvio_eje_10` (bbl diferidos en los meses 0 a 6 por cada 10 grados que el padre se aparta del eje "
          "de mayor merma, con el eje estimado fuera de muestra), reajustado con el mismo modelo de costo.", "",
          "| Especificación | n | Coeficiente (bbl) | IC 95% | Mismo signo que la muestra completa | IC excluye cero |",
          "| --- | ---: | ---: | --- | --- | --- |"]
    for r in co:
        L.append(f"| {r['especificacion']} | {_g(r['n'])} | {_g(r['coef'])} | {_g(r['ic_bajo'])} a {_g(r['ic_alto'])} | "
                 f"{'sí' if r['mismo_signo'] else 'no'} | {'sí' if r['ic_excluye_cero'] else 'no'} |")
    L += ["", veredicto_costo(co), "",
          "## Límites", "",
          "- Los subconjuntos no son independientes de la muestra completa: comparten eventos, así que coincidir con ella no es una réplica.",
          "- Cortar por período, operador o distancia reduce la cantidad de pads hijo, y con pocos pads el bootstrap es poco fiable.",
          "- Es un análisis de sensibilidad, no una prueba causal: el eje es la dirección de la merma observada, no del esfuerzo.",
          "- Las especificaciones de costo no prueban que el modelo lineal esté bien especificado."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main

def cargar_eventos(con) -> list[dict]:
    filas = _filas(con, costo.EVENTOS_SQL)
    op = {(r["padre"], r["mes_frac"]): r["operador"] for r in _filas(con, EVENTO_OPERADOR_SQL)}
    for f in filas:
        f["operador"] = op.get((f["padre"], f["mes_frac"]))
    return filas


def ejes_en_costo(con) -> dict:
    return {r[0]: float(r[1]) for r in con.execute(
        "select area, eje_grados from mart_anisotropia_area where usa_en_costo or area = 'Cuenca'").fetchall()}


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    filas = cargar_eventos(con)
    _escribir(con, "mart_robustez_eje", COLS_EJE, tabla_robustez_eje(filas))
    _escribir(con, "mart_robustez_costo", COLS_COSTO, tabla_robustez_costo(filas, ejes_en_costo(con)))
    for r in con.execute("select * from mart_robustez_eje").fetchall():
        print(f"[robustez] eje {r[0]:<10} {r[1]:<40} n={r[2]:>4} eje={r[3]:6.1f} IC {r[4]:6.1f} a {r[5]:6.1f} "
              f"ancho={r[6]:6.1f} p={r[7]:.3f} dif={r[8]:6.1f} shmax={r[9]:6.1f}")
    for r in con.execute("select * from mart_robustez_costo").fetchall():
        print(f"[robustez] costo {r[0]:<38} n={r[1]:>4} coef={r[2]:9.1f} IC {r[3]:9.1f} a {r[4]:9.1f} signo={r[5]} excl0={r[6]}")
    con.close()


if __name__ == "__main__":
    main()
