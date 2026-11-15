"""Validacion independiente del eje de interferencia este-oeste: otros resultados, eje por ano y datos fuera de tiempo.

Se corre despues de pipeline.costo:  uv run python -m pipeline.validacion

Escribe en data/warehouse.duckdb (create or replace, idempotente, con semilla fija):
  mart_validacion_resultados  eje de la cuenca (efectos fijos de area) con otros resultados, por ano y en entrenamiento y prueba
  mart_validacion_holdout     mejora fuera de muestra de un modelo de un termino angular con distintos ejes

Tres pruebas, todas sobre los mismos eventos cercanos de 0,3 a 1 km que usa pipeline.costo:
  (1) Resultados alternativos. La caida del caudal al mes 1 es el resultado de la estimacion principal. Aqui se repite el
      mismo ajuste (mismo nucleo axial coseno, mismos controles, mismos efectos fijos de area, mismo bootstrap por pads
      hijo y misma permutacion por bloques) con el salto del corte de agua, la caida de la fraccion de dias efectivos,
      la caida del caudal a los meses 2 y 3 y el cierre declarado (probabilidad lineal).
  (2) Eje por ano de fractura del hijo. Los anos con menos de MIN_N_ANIO eventos se juntan con el siguiente.
  (3) Datos fuera de tiempo. El eje se estima solo con los eventos hasta CORTE (entrenamiento). En los eventos posteriores
      (prueba) se ajusta la caida sobre controles (distancia, log de edad, efectos fijos de area) mas un solo termino
      cos(2 * (rumbo - eje)); se mide cuanto baja la suma de cuadrados de los residuos respecto de no usar angulo, con
      el eje de entrenamiento, con el SHmax publicado y con N_ALEATORIOS ejes al azar.

Que NO prueba:
  * No es una replica independiente en datos nuevos: la prueba es posterior en el tiempo, pero sale del mismo
    warehouse, el mismo campo y los mismos padres (un padre puede estar en ambos lados).
  * Los resultados alternativos comparten eventos y controles con el principal; que apunten al mismo eje es consistencia,
    no una prueba aparte. El cierre declarado es una variable 0/1 y el modelo es lineal.
  * El termino angular tiene coeficiente libre: un eje a 90 grados del verdadero tambien reduce la suma de cuadrados
    (con el signo cambiado). Por eso se informa tambien el eje que se ajusta en la prueba y su distancia al de entrenamiento.
"""
from __future__ import annotations

import datetime as dt
import re

import duckdb
import numpy as np

from pipeline import costo
from pipeline.costo import (ANCHO_MAX, KM_MIN_EJE, P_EJE_COSTO, REPS_EJE, REPS_PERM, SEMILLA, _arr, _clusters, _controles_eje,
                            _dif_axial, _escribir, _filas, _g, _remuestra, _rosa, ajustar_eje, eje_con_intervalo)
from pipeline.ingest import DATA
from pipeline.robustez import SHMAX, _gs, ic_contiene

CORTE = dt.date(2023, 6, 1)   # ultimo mes de fractura del hijo que entra en el entrenamiento
MIN_N_HOLDOUT = 500           # eventos minimos de entrenamiento y de prueba
MIN_N_ANIO = 120              # eventos minimos por grupo de anos
MIN_N_SUB = 40                # eventos minimos para estimar un eje
N_ALEATORIOS = 200
REPS_HOLDOUT = 400
REPS_EJE_VAL = REPS_EJE       # las mismas repeticiones y semilla que pipeline.costo
REPS_PERM_VAL = REPS_PERM

COLS_RES = [("bloque", "varchar"), ("nombre", "varchar"), ("n", "integer"), ("eje", "double"), ("ic_bajo", "double"),
            ("ic_alto", "double"), ("ancho_ic", "double"), ("p_perm", "double"), ("dif_eje_principal", "double"),
            ("dif_shmax", "double")]
COLS_HOLD = [("modelo", "varchar"), ("n_train", "integer"), ("n_test", "integer"), ("eje", "double"),
             ("mejora_rss", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]

NOMBRE_PRINCIPAL = "Caída del caudal al mes 1 (estimación principal)"

# Cada consulta devuelve (padre, mes_frac, y) para los eventos cercanos. Ventanas como en int_interferencia_clase:
# base = meses -3 a -1 antes del mes de fractura del hijo, efecto = meses 0 a 1.
_VENTANA_SQL = """
with m as (
    select e.padre, e.mes_frac, date_diff('month', e.mes_frac, x.mes) as k, x.corte_agua, x.tef_frac
    from int_interferencia_evento e
    join int_prod_corte x
      on x.pozo_id = e.padre and x.mes between e.mes_frac - interval 3 month and e.mes_frac + interval 1 month
    where e.banda = 'cercano'
), agg as (
    select padre, mes_frac,
           avg(corte_agua) filter (where k between -3 and -1) as agua_base,
           max(corte_agua) filter (where k between 0 and 1) as agua_max,
           avg(tef_frac) filter (where k between -3 and -1) as tef_base,
           min(tef_frac) filter (where k between 0 and 1) as tef_0
    from m group by padre, mes_frac
)
"""
SQL_AGUA = _VENTANA_SQL + "select padre, mes_frac, agua_max - agua_base as y from agg where agua_max is not null and agua_base is not null"
SQL_TEF = _VENTANA_SQL + ("select padre, mes_frac, 1 - least(greatest(tef_0 / tef_base, 0), 2) as y from agg "
                          "where tef_0 is not null and tef_base is not null and tef_base > 0")


def _sql_caida_k(k: int) -> str:
    return f"""
select e.padre, e.mes_frac,
       least(greatest(b.indice_control, 0), 2) - least(greatest(m.indice, 0), 2) as y
from int_interferencia_evento e
join int_interferencia_mes m on m.padre = e.padre and m.mes_frac = e.mes_frac and m.k = {int(k)}
join mart_interferencia_brecha b on b.grupo_edad = e.grupo_edad and b.k = {int(k)}
where e.banda = 'cercano' and m.indice is not null and b.indice_control is not null
"""


RESULTADOS_ALT = [
    ("Salto del corte de agua (meses 0 a 1 contra 3 previos)", SQL_AGUA),
    ("Caída de la fracción de días efectivos (TEF)", SQL_TEF),
    ("Caída del caudal al mes 2", _sql_caida_k(2)),
    ("Caída del caudal al mes 3", _sql_caida_k(3)),
]
NOMBRE_PARADO = "Cierre declarado en los meses 0 a 1 (probabilidad lineal)"


# ------------------------------------------------------------------ nucleo

def _mes(x) -> dt.date:
    return x.date() if isinstance(x, dt.datetime) else x


def en_banda(filas: list[dict], km_lo: float = KM_MIN_EJE, km_hi: float = 1.0) -> list[dict]:
    return [f for f in filas if km_lo <= f["km_min"] < km_hi]


def _caida(filas: list[dict]) -> np.ndarray:
    return np.clip(_arr(filas, "indice_control"), 0, 2) - np.clip(_arr(filas, "indice"), 0, 2)


def _codigos(f: list[dict]) -> np.ndarray:
    return np.unique(np.array([x["area"] for x in f]), return_inverse=True)[1]


def _ctrl(f: list[dict]) -> np.ndarray:
    return _controles_eje({"km": _arr(f, "km_min"), "edad": _arr(f, "edad_meses")})


def eje_resultado(filas: list[dict], y, reps: int = REPS_EJE_VAL, reps_perm: int = REPS_PERM_VAL,
                  semilla: int = SEMILLA) -> dict | None:
    """Eje de la cuenca (efectos fijos de area) para el resultado `y` (un valor por evento de `filas`).

    Los eventos con y faltante se descartan. Devuelve None si quedan menos de MIN_N_SUB. Claves: n, eje, ic_bajo,
    ic_alto, ancho_ic, p_perm.
    """
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(y)
    f = [x for x, o in zip(filas, ok) if o]
    if len(f) < MIN_N_SUB:
        return None
    clave = np.array([str(x["pad_hijo"]) for x in f])
    r = eje_con_intervalo(y[ok], _ctrl(f), _arr(f, "rumbo_eje"), clave, grupo=_codigos(f), reps=reps,
                          reps_perm=reps_perm, semilla=semilla)
    return {"n": len(f), "eje": r["eje"], "ic_bajo": r["ic_bajo"], "ic_alto": r["ic_alto"], "ancho_ic": r["ancho_ic"],
            "p_perm": r["p_perm"]}


def cargar_eventos(con) -> list[dict]:
    """Eventos cercanos de 0,3 a 1 km de pipeline.costo, con los resultados alternativos pegados como claves y_*."""
    filas = en_banda(_filas(con, costo.EVENTOS_SQL))
    for i, (nombre, sql) in enumerate(RESULTADOS_ALT):
        val = {(r["padre"], r["mes_frac"]): r["y"] for r in _filas(con, sql)}
        for f in filas:
            v = val.get((f["padre"], f["mes_frac"]))
            f[f"y_{i}"] = float("nan") if v is None else float(v)
    for f in filas:
        f["y_parado"] = 1.0 if f["parado"] else 0.0
    return filas


def agrupar_anios(conteo: dict[int, int], minimo: int = MIN_N_ANIO) -> list[tuple[str, list[int]]]:
    """Junta anos consecutivos hasta llegar a `minimo` eventos; un resto final corto se suma al grupo anterior."""
    grupos: list[list[int]] = []
    acum, cur = 0, []
    for a in sorted(conteo):
        cur.append(a)
        acum += conteo[a]
        if acum >= minimo:
            grupos.append(cur)
            cur, acum = [], 0
    if cur:
        if grupos:
            grupos[-1] += cur
        else:
            grupos.append(cur)
    return [(f"{g[0]} a {g[-1]}" if g[0] != g[-1] else f"{g[0]}", g) for g in grupos]


def dividir(filas: list[dict], corte: dt.date = CORTE) -> tuple[list[dict], list[dict]]:
    """(entrenamiento, prueba): mes de fractura del hijo hasta `corte` inclusive contra posteriores. Disjuntos."""
    tr = [f for f in filas if _mes(f["mes_frac"]) <= corte]
    te = [f for f in filas if _mes(f["mes_frac"]) > corte]
    return tr, te


# ------------------------------------------------------------------ tabla de resultados

def tabla_resultados(filas: list[dict], reps: int = REPS_EJE_VAL, reps_perm: int = REPS_PERM_VAL,
                     corte: dt.date = CORTE) -> list[tuple]:
    out = []
    princ = eje_resultado(filas, _caida(filas), reps, reps_perm)
    base = princ["eje"]

    def fila(bloque, nombre, r):
        return (bloque, nombre, int(r["n"]), r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], r["p_perm"],
                float(_dif_axial(r["eje"], base)), float(_dif_axial(r["eje"], SHMAX)))

    out.append(fila("principal", NOMBRE_PRINCIPAL, princ))
    alt = [(n, np.array([f[f"y_{i}"] for f in filas])) for i, (n, _s) in enumerate(RESULTADOS_ALT)]
    alt.append((NOMBRE_PARADO, np.array([f["y_parado"] for f in filas])))
    for nombre, y in alt:
        r = eje_resultado(filas, y, reps, reps_perm)
        if r is not None:
            out.append(fila("resultado", nombre, r))
    conteo: dict[int, int] = {}
    for f in filas:
        conteo[_mes(f["mes_frac"]).year] = conteo.get(_mes(f["mes_frac"]).year, 0) + 1
    for nombre, anios in agrupar_anios(conteo):
        sub = [f for f in filas if _mes(f["mes_frac"]).year in anios]
        r = eje_resultado(sub, _caida(sub), reps, reps_perm)
        if r is not None:
            out.append(fila("anio", nombre, r))
    tr, te = dividir(filas, corte)
    for nombre, sub in ((f"Entrenamiento (hasta {corte.year}-{corte.month:02d})", tr),
                        (f"Prueba (después de {corte.year}-{corte.month:02d})", te)):
        r = eje_resultado(sub, _caida(sub), reps, reps_perm)
        if r is not None:
            out.append(fila("holdout", nombre, r))
    return out


# ------------------------------------------------------------------ fuera de tiempo

def _centrar(M: np.ndarray, grupo: np.ndarray) -> np.ndarray:
    n_g = int(grupo.max()) + 1
    D = np.zeros((len(grupo), n_g))
    D[np.arange(len(grupo)), grupo] = 1.0
    cnt = np.maximum(D.sum(axis=0), 1.0)
    return M - D @ ((D.T @ M) / (cnt[:, None] if M.ndim == 2 else cnt))


def mejoras(y, ctrl, grupo, rumbo, ejes) -> np.ndarray:
    """Fraccion de la suma de cuadrados de los residuos que se elimina al sumar cos(2 * (rumbo - eje)) a los controles.

    Controles y efectos fijos de area se absorben primero (Frisch-Waugh). Un valor por eje; la linea base es el modelo
    con controles y sin angulo.
    """
    y = np.asarray(y, dtype=float)
    ejes = np.asarray(ejes, dtype=float)
    Y = _centrar(y, grupo)
    C = _centrar(np.asarray(ctrl, dtype=float), grupo)
    Z = _centrar(np.cos(2 * np.radians(np.asarray(rumbo, dtype=float)[:, None] - ejes[None, :])), grupo)
    Yr = Y - C @ np.linalg.lstsq(C, Y, rcond=None)[0]
    Zr = Z - C @ np.linalg.lstsq(C, Z, rcond=None)[0]
    rss0 = float(Yr @ Yr)
    zz = np.maximum((Zr ** 2).sum(axis=0), 1e-12)
    return ((Zr.T @ Yr) ** 2 / zz) / max(rss0, 1e-12)


def ejes_aleatorios(n: int = N_ALEATORIOS, semilla: int = SEMILLA + 1) -> np.ndarray:
    return np.random.default_rng(semilla).uniform(0, 180, n)


def tabla_holdout(filas: list[dict], corte: dt.date = CORTE, reps: int = REPS_HOLDOUT, n_aleatorios: int = N_ALEATORIOS,
                  semilla: int = SEMILLA) -> list[tuple]:
    tr, te = dividir(filas, corte)
    n_tr, n_te = len(tr), len(te)
    eje_tr = float(ajustar_eje(_caida(tr), _ctrl(tr), _arr(tr, "rumbo_eje"), _codigos(tr))[0])
    y, ctrl, grupo, rumbo = _caida(te), _ctrl(te), _codigos(te), _arr(te, "rumbo_eje")
    aleat = ejes_aleatorios(n_aleatorios)
    ejes = np.concatenate([[eje_tr, SHMAX], aleat])
    punto = mejoras(y, ctrl, grupo, rumbo, ejes)
    m_tr, m_sh, m_al = float(punto[0]), float(punto[1]), punto[2:]
    eje_te = float(ajustar_eje(y, ctrl, rumbo, grupo)[0])
    m_te = float(mejoras(y, ctrl, grupo, rumbo, [eje_te])[0])

    rng = np.random.default_rng(semilla)
    cl = _clusters(np.array([str(x["pad_hijo"]) for x in te]))
    bt, bs, bd_sh, bd_al, ba_med = [], [], [], [], []
    for _ in range(reps):
        i = _remuestra(rng, cl)
        g = np.unique(grupo[i], return_inverse=True)[1]
        mj = mejoras(y[i], ctrl[i], g, rumbo[i], ejes)
        bt.append(mj[0])
        bs.append(mj[1])
        bd_sh.append(mj[0] - mj[1])
        med = float(np.median(mj[2:]))
        ba_med.append(med)
        bd_al.append(mj[0] - med)

    def ic(v):
        lo, hi = np.percentile(v, [2.5, 97.5])
        return float(lo), float(hi)

    out = []
    lo, hi = ic(bt)
    out.append(("Eje de entrenamiento", n_tr, n_te, eje_tr, m_tr, lo, hi))
    lo, hi = ic(bs)
    out.append(("SHmax publicado", n_tr, n_te, float(SHMAX), m_sh, lo, hi))
    lo, hi = np.percentile(m_al, [2.5, 97.5])
    out.append((f"Eje aleatorio (mediana de {len(aleat)})", n_tr, n_te, None, float(np.median(m_al)), float(lo), float(hi)))
    lo, hi = ic(bd_sh)
    out.append(("Entrenamiento menos SHmax", n_tr, n_te, None, m_tr - m_sh, lo, hi))
    lo, hi = ic(bd_al)
    out.append(("Entrenamiento menos la mediana de los ejes aleatorios", n_tr, n_te, None, m_tr - float(np.median(m_al)), lo, hi))
    out.append(("Proporción de ejes aleatorios con mejora igual o mayor que el de entrenamiento", n_tr, n_te, None,
                float(np.mean(m_al >= m_tr)), None, None))
    out.append(("Eje ajustado en la prueba (cota, dentro de muestra)", n_tr, n_te, eje_te, m_te, None, None))
    return out


# ------------------------------------------------------------------ pagina del wiki

def _pct(x: float, dec: int = 1) -> str:
    return _g(100 * x, dec) + "%"


def _define(r: dict) -> bool:
    return r["ancho_ic"] < ANCHO_MAX and r["p_perm"] < P_EJE_COSTO


def _apunta(r: dict, base: dict) -> bool:
    return ic_contiene(r["eje"], r["ic_bajo"], r["ic_alto"], r["ancho_ic"], base["eje"])


def tendencia_anios(filas: list[dict]) -> tuple[float, int] | None:
    """Pendiente (grados por ano) de la diferencia con el eje principal contra el ano medio del grupo.

    Minimos cuadrados ponderados por 1 / ancho_ic ** 2 con los grupos de anos; devuelve (pendiente, grupos usados)."""
    x, d, w = [], [], []
    for r in filas:
        if r["bloque"] != "anio":
            continue
        a = [int(v) for v in re.findall(r"\d{4}", r["nombre"])]
        x.append(sum(a) / len(a))
        d.append(r["dif_eje_principal"])
        w.append(1.0 / max(r["ancho_ic"], 1.0) ** 2)
    if len(x) < 3:
        return None
    x, d, w = np.array(x), np.array(d), np.array(w)
    xm = float(np.average(x, weights=w))
    dm = float(np.average(d, weights=w))
    den = float(np.sum(w * (x - xm) ** 2))
    if den <= 0:
        return None
    return float(np.sum(w * (x - xm) * (d - dm)) / den), len(x)


def veredicto_resultados(filas: list[dict]) -> str:
    base = next(r for r in filas if r["bloque"] == "principal")
    alt = [r for r in filas if r["bloque"] == "resultado"]
    if not alt:
        return "No hubo resultados alternativos con eventos suficientes."
    mismo = [r for r in alt if _apunta(r, base)]
    defi = [r for r in alt if _define(r)]
    t = (f"El IC contiene el eje principal ({_g(base['eje'])} grados) en {len(mismo)} de {len(alt)} resultados alternativos "
         f"y el eje queda definido (IC de menos de {_g(ANCHO_MAX)} grados y p de permutación menor que {_g(P_EJE_COSTO, 2)}) "
         f"en {len(defi)}")
    if defi:
        t += ": " + "; ".join(f"{r['nombre']} ({_g(r['eje'])} grados)" for r in defi)
    t += ". "
    defi_mismo = [r for r in defi if _apunta(r, base)]
    if not defi:
        t += ("Ningún resultado alternativo tiene un eje definido: no confirman ni contradicen el eje principal. "
              "Que sus IC lo contengan se debe sobre todo a que son anchos.")
    elif len(defi_mismo) == len(defi):
        quien = (f"Los {len(defi)} que tienen un eje definido apuntan" if len(defi) > 1
                 else "El único que tiene un eje definido apunta")
        t += (f"{quien} al mismo eje que el principal; los demás no permiten decir nada porque su IC es ancho "
              f"o su p no baja de {_g(P_EJE_COSTO, 2)}.")
    else:
        t += "Entre los que tienen un eje definido, no todos coinciden con el principal."
    fuera = [r["nombre"] for r in alt if not _apunta(r, base)]
    if fuera:
        t += " El IC no contiene el eje principal en: " + "; ".join(fuera) + "."
    return t


def veredicto_anios(filas: list[dict]) -> str:
    base = next(r for r in filas if r["bloque"] == "principal")
    an = [r for r in filas if r["bloque"] == "anio"]
    if not an:
        return "No hubo grupos de años con eventos suficientes."
    defi = [r for r in an if _define(r)]
    cont = [r for r in an if _apunta(r, base)]
    t = (f"El IC contiene el eje principal en {len(cont)} de {len(an)} grupos de años y el eje queda definido en {len(defi)}")
    if defi:
        t += " (" + "; ".join(r["nombre"] for r in defi) + ")"
    t += ". "
    fuera = [r["nombre"] for r in an if not _apunta(r, base)]
    if fuera:
        t += "El IC no contiene el eje principal en: " + "; ".join(fuera) + ". "
    if not defi:
        t += "Que los IC contengan el eje principal se debe sobre todo a que son anchos (cada grupo tiene pocos pads hijo). "
    tend = tendencia_anios(filas)
    if tend is not None:
        pend, k = tend
        t += (f"La diferencia con el eje principal, ponderada por 1 sobre el ancho del IC al cuadrado, tiene una pendiente de "
              f"{_g(pend, 1)} grados por año en {k} grupos. Con tan pocos grupos y los IC anchos es una descripción, "
              "no una tendencia demostrada.")
    return t


def veredicto_holdout(res: list[dict], hold: list[dict]) -> str:
    h = {r["modelo"]: r for r in hold}
    tr = h["Eje de entrenamiento"]
    sh = h["SHmax publicado"]
    al = next(r for r in hold if r["modelo"].startswith("Eje aleatorio"))
    d_sh = h["Entrenamiento menos SHmax"]
    d_al = next(r for r in hold if r["modelo"].startswith("Entrenamiento menos la mediana"))
    prop = next(r for r in hold if r["modelo"].startswith("Proporción"))
    hte = next((r for r in res if r["bloque"] == "holdout" and r["nombre"].startswith("Prueba")), None)
    htr = next((r for r in res if r["bloque"] == "holdout" and r["nombre"].startswith("Entrenamiento")), None)
    t = (f"El eje estimado solo con el entrenamiento ({_g(tr['n_train'])} eventos) es {_g(tr['eje'])} grados. En la prueba "
         f"({_g(tr['n_test'])} eventos) reduce la suma de cuadrados de los residuos en {_pct(tr['mejora_rss'], 2)} "
         f"(IC {_pct(tr['ic_bajo'], 2)} a {_pct(tr['ic_alto'], 2)}); el SHmax publicado, en {_pct(sh['mejora_rss'], 2)}; "
         f"la mediana de {N_ALEATORIOS} ejes al azar, en {_pct(al['mejora_rss'], 2)}. "
         f"{_pct(prop['mejora_rss'], 1)} de los ejes al azar mejora tanto o más que el de entrenamiento. ")
    gana_sh = d_sh["ic_bajo"] > 0
    pierde_sh = d_sh["ic_alto"] < 0
    t += (f"La mejora del eje de entrenamiento menos la del SHmax es {_pct(d_sh['mejora_rss'], 2)} "
          f"(IC {_pct(d_sh['ic_bajo'], 2)} a {_pct(d_sh['ic_alto'], 2)}); "
          f"menos la mediana de los ejes al azar, {_pct(d_al['mejora_rss'], 2)} "
          f"(IC {_pct(d_al['ic_bajo'], 2)} a {_pct(d_al['ic_alto'], 2)}). ")
    if hte is not None and htr is not None:
        dist = float(_dif_axial(hte["eje"], htr["eje"]))
        t += (f"Ajustado en la prueba, el eje queda en {_g(hte['eje'])} grados (IC {_g(hte['ic_bajo'])} a {_g(hte['ic_alto'])}, "
              f"p de permutación {_g(hte['p_perm'], 3)}), a {_g(abs(dist))} grados del de entrenamiento"
              f"{'' if _define(hte) else '; en la prueba el eje no está definido'}. ")
    mejor_al = prop["mejora_rss"] < 0.05 and d_al["ic_bajo"] > 0
    if gana_sh and mejor_al:
        t += "El eje de entrenamiento generaliza mejor que el SHmax y que los ejes al azar."
    elif mejor_al and not gana_sh and not pierde_sh:
        t += ("El eje de entrenamiento generaliza mejor que los ejes al azar, pero no se puede separar del SHmax: "
              "la diferencia entre ambos tiene un IC que incluye cero.")
    elif pierde_sh:
        t += "El eje de entrenamiento generaliza peor que el SHmax publicado."
    elif d_al["ic_bajo"] > 0:
        t += ("El eje de entrenamiento mejora sobre la mediana de los ejes al azar, pero una parte de ellos lo iguala "
              "(la proporción de arriba), así que la evidencia fuera de tiempo es débil.")
    elif gana_sh:
        t += ("El eje de entrenamiento mejora sobre el SHmax, pero no se separa de los ejes al azar: "
              "el IC de esa diferencia incluye cero.")
    else:
        t += ("No se puede afirmar que el eje de entrenamiento generalice mejor que el SHmax ni que los ejes al azar: "
              "los IC de ambas diferencias incluyen cero.")
    if max(tr["mejora_rss"], sh["mejora_rss"]) < 0.01:
        t += (" En todos los casos la mejora es chica, de menos del 1% de la suma de cuadrados de los residuos del modelo "
              "sin ángulo: el ángulo explica poco de la caída.")
    return t


def pagina_validacion(con) -> str:
    """Pagina de wiki a partir de las tablas de validacion. Texto en espanol, sin rayas largas."""
    res = _filas(con, "select * from mart_validacion_resultados")
    hold = _filas(con, "select * from mart_validacion_holdout")
    base = next(r for r in res if r["bloque"] == "principal")
    n_tr, n_te = hold[0]["n_train"], hold[0]["n_test"]

    def tabla(bloques):
        L = ["| Resultado | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Dif. con el eje principal | Dif. con SHmax | Apunta al eje principal | Definido |",
             "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |"]
        for r in res:
            if r["bloque"] in bloques:
                L.append(f"| {r['nombre']} | {_g(r['n'])} | {_g(r['eje'])} | {_g(r['ic_bajo'])} a {_g(r['ic_alto'])} | "
                         f"{_g(r['ancho_ic'])} | {_g(r['p_perm'], 3)} | {_gs(r['dif_eje_principal'])} | {_gs(r['dif_shmax'])} | "
                         f"{'sí' if _apunta(r, base) else 'no'} | {'sí' if _define(r) else 'no'} |")
        return L

    L = ["# Validación del eje este-oeste", "",
         "Página generada por `pipeline/validacion.py`. Somete el eje de mayor merma de `pipeline/costo.py` a tres pruebas: "
         "otros resultados medidos sobre los mismos eventos, el eje año por año y una prueba fuera de tiempo en la que el eje "
         "se estima con los eventos viejos y se evalúa en los nuevos. Usa las mismas repeticiones y semilla que la página de "
         f"anisotropía ({REPS_EJE_VAL} de bootstrap por pads hijo y {REPS_PERM_VAL} permutaciones por bloques).", "",
         "## Resultados alternativos", "",
         f"Eje principal (caída del caudal al mes 1, efectos fijos de área, eventos de 0,3 a 1 km): {_g(base['eje'])} grados "
         f"({_rosa(base['eje'])}), IC de {_g(base['ic_bajo'])} a {_g(base['ic_alto'])} grados, n = {_g(base['n'])}, "
         f"p de permutación {_g(base['p_perm'], 3)}. El SHmax publicado es unos {_g(SHMAX, 1)} grados. "
         "Cada fila repite el mismo ajuste con otra variable de resultado, en los mismos eventos (se descartan los que no "
         "tienen el dato).", ""]
    L += tabla({"principal", "resultado"})
    L += ["", veredicto_resultados(res), "",
          f"Un eje se considera definido si el IC mide menos de {_g(ANCHO_MAX)} grados y el p de permutación es menor que "
          f"{_g(P_EJE_COSTO, 2)}. Las diferencias son con signo, en grados, módulo 180 y en el rango de menos 90 a 90. "
          "El salto del corte de agua y el cierre declarado miden cosas distintas de la caída del caudal (un golpe de agua "
          "o una decisión operativa), así que que apunten o no al mismo eje es información, no un error.", "",
          "## Eje por año de fractura del hijo", "",
          f"Se usan los años con al menos {MIN_N_ANIO} eventos; los años con menos se juntan con los siguientes hasta llegar a ese "
          "mínimo y un resto final corto se suma al grupo anterior.", ""]
    L += tabla({"anio"})
    L += ["", veredicto_anios(res), "",
          "## Fuera de tiempo", "",
          f"Entrenamiento: eventos cuyo hijo se fractura hasta {CORTE.year}-{CORTE.month:02d} ({_g(n_tr)} eventos). Prueba: "
          f"los posteriores ({_g(n_te)}). El corte deja al menos {MIN_N_HOLDOUT} eventos de cada lado y se fijó "
          "antes de ver el resultado. El eje de entrenamiento sale de `ajustar_eje` con los mismos controles y efectos fijos de área.", ""]
    L += tabla({"holdout"})
    L += ["",
          "En la prueba se ajusta la caída sobre distancia, log de la edad, efectos fijos de área y un solo término "
          "cos(2 * (rumbo - eje)). La mejora es la fracción de la suma de cuadrados de los residuos que se elimina respecto "
          f"del modelo sin ángulo, para el eje de entrenamiento, el SHmax y {N_ALEATORIOS} ejes al azar. "
          "El IC de las filas con eje es un bootstrap por pads hijo de la prueba; el de la fila de ejes al azar son "
          "los percentiles 2,5 y 97,5 de esa distribución. La mejora de un eje nunca es negativa, así que el límite inferior "
          "de esos IC queda en 0 y la comparación informativa es la de las diferencias.", "",
          "| Modelo | n entrenamiento | n prueba | Eje (grados) | Mejora de la suma de cuadrados | IC 95% |",
          "| --- | ---: | ---: | ---: | ---: | --- |"]
    for r in hold:
        eje = "" if r["eje"] is None else _g(r["eje"])
        ic = "" if r["ic_bajo"] is None else f"{_pct(r['ic_bajo'], 2)} a {_pct(r['ic_alto'], 2)}"
        L.append(f"| {r['modelo']} | {_g(r['n_train'])} | {_g(r['n_test'])} | {eje} | {_pct(r['mejora_rss'], 2)} | {ic} |")
    L += ["", veredicto_holdout(res, hold), "",
          "## Límites", "",
          "- La prueba fuera de tiempo no es una réplica independiente: sale del mismo warehouse, el mismo campo y los mismos "
          "padres, y un padre puede aparecer a ambos lados del corte.",
          "- En la prueba fuera de tiempo solo el eje sale de los datos de entrenamiento: los coeficientes de distancia y edad, "
          "los efectos fijos de área y el índice de los controles (que se construye con todos los períodos) se calculan con los "
          "eventos de la prueba. Es fuera de muestra para el eje, no para el modelo completo.",
          "- Se prueban cinco resultados alternativos y ocho grupos de años sin corregir por comparaciones múltiples; solo uno de "
          "los resultados alternativos llega a p de permutación menor que 0,10. El corte de la prueba es una sola elección y no se varió.",
          "- Un IC que cruza los 180 grados se lee como un intervalo que da la vuelta: por ejemplo, de 176 a 155 es de 176 pasando por 0 hasta 155.",
          "- Los resultados alternativos comparten eventos y controles con el principal: que apunten al mismo eje es consistencia, no una prueba aparte.",
          "- El término angular tiene coeficiente libre: un eje a 90 grados del verdadero también reduce la suma de cuadrados. Por eso se informa el eje ajustado en la prueba.",
          "- Con grupos chicos el bootstrap por pads hijo es poco fiable, y los IC anchos no son evidencia contra el eje principal.",
          "- Es una comparación estadística: el eje es la dirección de la merma observada, no una medición de esfuerzos."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    filas = cargar_eventos(con)
    _escribir(con, "mart_validacion_resultados", COLS_RES, tabla_resultados(filas))
    _escribir(con, "mart_validacion_holdout", COLS_HOLD, tabla_holdout(filas))
    for r in con.execute("select * from mart_validacion_resultados").fetchall():
        print(f"[validacion] {r[0]:<9} {r[1]:<56} n={r[2]:>4} eje={r[3]:6.1f} IC {r[4]:6.1f} a {r[5]:6.1f} "
              f"ancho={r[6]:6.1f} p={r[7]:.3f} dif={r[8]:6.1f} shmax={r[9]:6.1f}")
    for r in con.execute("select * from mart_validacion_holdout").fetchall():
        eje = "  -  " if r[3] is None else f"{r[3]:5.1f}"
        ic = "" if r[5] is None else f"IC {100 * r[5]:6.2f}% a {100 * r[6]:6.2f}%"
        print(f"[validacion] holdout {r[0]:<70} eje={eje} mejora={100 * r[4]:7.3f}% {ic}")
    con.close()


if __name__ == "__main__":
    main()
