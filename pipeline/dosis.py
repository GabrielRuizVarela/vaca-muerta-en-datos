"""Dosis y respuesta: la caida del padre crece con el tamano del trabajo del hijo y con la depleccion del padre?

Se corre despues de pipeline.costo y pipeline.descomposicion:  uv run python -m pipeline.dosis

REGLA FIJADA ANTES DE CORRER (2026-11-16, antes de calcular ningun coeficiente ni ningun promedio por quintil; no se cambia despues
de ver resultados). Fuente: docs/proceso/investigacion-fase3.md, seccion 3.8. Solo se miro la cobertura de las variables (cuantos
eventos tienen cada una), nunca la caida.

Pregunta: una respuesta que crece con la dosis (trabajos de fractura mas grandes del hijo, padre mas depletado) es lo que la fisica
de los golpes de fractura predice; si el dato publico no la muestra, la huella es compatible con gestion (cierre preventivo) o con
variables no observadas (espaciamiento real). Resultado en escala libre: indice y caudal por dia, no barriles.

Unidad: los eventos 'cercano' de int_interferencia_evento (padre a menos de 1 km del hijo mas cercano, 2.077 eventos), SIN exigir
rumbo (aqui no se usa direccion). Dos resultados, cada uno con su propia familia de pruebas:
  A (principal, decide el veredicto): caida = indice de control menos indice del padre al mes 1, igual que pipeline.costo
     (EVENTOS_SQL: int_interferencia_mes k = 1, mart_interferencia_brecha por grupo de edad, los dos acotados a [0, 2]).
  B (parte de caudal por dia, seccion 3.1): caida = menos el logaritmo del indice de caudal por dia efectivo al mes 1
     (pipeline.descomposicion._logs, variante sin cerrados: entran los eventos con base positiva y con caudal por dia positivo
     en el mes 1). No cambia el veredicto de A; ver "Texto".

Las cuatro variables (todas con el signo esperado POSITIVO: mas dosis, mas caida):
  1. arena por etapa del hijo (tn por etapa);
  2. arena por metro de rama del hijo (tn por m);
  3. presion maxima de tratamiento del hijo (presion_maxima_psi);
  4. depleccion: petroleo acumulado del padre por metro de rama del padre hasta la fecha de fractura (suma de petroleo_m3 de
     fct_produccion en los meses anteriores a mes_frac, sobre dim_fractura_pozo.rama_horizontal_m del padre).
El trabajo del hijo son las filas de stg_fractura de hijo_cercano cuya fecha_inicio es la primera del pozo (la que fija mes_frac):
arena y etapas se suman, rama y presion toman el maximo. Una variable queda faltante (el evento sale de ese analisis) si: arena,
etapas o rama no son positivas donde se usan; la presion no cumple 0 < presion < 20.000 psi (un cero es dato faltante, no una
presion); la rama del padre no es positiva o el padre no tiene produccion previa. Entran como logaritmo natural la arena por
etapa, la arena por metro y la depleccion; la presion entra en psi sin transformar. Cada variable se estandariza (media 0, desvio
1) dentro de la muestra del analisis, de modo que cada coeficiente es el cambio de la caida por un desvio de la variable.

Controles (los mismos en todos los modelos): km_min, log de la edad del padre (meses, minimo 1), caudal base (base_m3_d / 10),
hijos_1km, el tipo de terminacion del hijo (dummies; categoria base 'Tapon disparo', las que tengan menos de 20 eventos en la
muestra se juntan en 'otras') y efectos fijos de area por ano de mes_frac (las celdas con menos de 5 eventos se juntan en una sola
por area).

Primero, quintiles (una variable a la vez): para cada variable, los cortes en quintiles de los eventos que la tienen; en cada
quintil, el promedio de la caida ajustada (residuo de la caida contra los controles y los efectos fijos, mas la media general)
con IC 95% de percentiles por pads hijo. Hay "orden" en una variable si el promedio sube de Q1 a Q5 con correlacion de rango (Spearman) de
los cinco promedios con el numero de quintil >= 0,7 Y la diferencia Q5 menos Q1 tiene p ajustado por Holm (sobre las cuatro
variables) < 0,05 con signo positivo.

Despues, UN modelo con las cuatro a la vez (minimos cuadrados con los controles y efectos fijos), sobre los eventos con las cuatro
variables completas (caso completo). Inferencia: bootstrap de pads hijo (pad_id del hijo; sin pad, el pozo hijo es su propio
conglomerado), B = 2.000 remuestras con semilla fija derivada de costo.SEMILLA; IC 95% de percentiles; p de dos colas =
min(1, 2 * (1 + min(#b <= 0, #b >= 0)) / (B + 1)). Holm sobre las cuatro variables, alfa = 0,05: una variable "tiene IC que
excluye cero tras Holm" si su p ajustado es < 0,05. Se publica tambien el IC 95% sin ajustar, el coeficiente en desvios de la
caida, el numero de eventos y de pads, y el FIV de cada variable.

Si hay menos de 1.000 eventos de caso completo, o menos de 150 pads hijo, el modelo conjunto se publica pero el veredicto es "no
concluyente por muestra" (salvo que se cumpla la regla positiva de abajo, que no se debilita por ser una muestra chica).

Sensibilidades (se informan, NO entran en el veredicto): sin las dummies de terminacion; solo terminacion 'Tapon disparo'; las
cuatro variables como rangos (percentil) en vez de log y psi; cada variable sola con los controles (un modelo por variable).
Cualquier otro diagnostico agregado despues de ver los resultados se rotula "agregado despues de ver los resultados" y no cambia el
veredicto.

Veredicto (con el resultado A y el modelo conjunto; se publican todos los resultados, favorables o no):
  * "dosis y respuesta": dos o mas variables con signo positivo y p ajustado por Holm < 0,05. Se escribe "la caida crece con X y Y,
    como se espera de un golpe de fractura", con las variables que cumplen.
  * "una sola variable": exactamente una cumple. No alcanza la regla; se informa cual y NO se escribe que la caida crece con la
    dosis; el mecanismo no queda falsado ni confirmado.
  * "sin dosis y respuesta": ninguna cumple Y ninguna tiene orden en los quintiles. Se escribe que el dato publico no muestra dosis
    y respuesta, lo que es compatible con cierre preventivo o con variables no observadas (espaciamiento real), con el semiancho
    de los IC (en desvios de la caida) para que se lea cuanto efecto queda descartado. Esto es lo que el plan llama falsar el
    mecanismo con datos publicos: no dice que no haya golpes de fractura.
  * "orden sin coeficiente": ninguna cumple en el modelo conjunto pero alguna variable tiene orden en los quintiles. No se afirma ni
    se descarta.
  * Una variable con signo NEGATIVO y p ajustado < 0,05 se informa aparte ("signo contrario") y nunca cuenta como cumplida.

Texto: el resultado B se corre igual (cuatro variables, quintiles, modelo conjunto, Holm propio) y no cambia el veredicto de A. Si A
da "dosis y respuesta" y B tiene menos de dos variables que cumplan, la frase se completa con "pero la parte de caudal por dia no
lo muestra por separado"; si B tiene dos o mas, con "y la parte de caudal por dia lo confirma". Un golpe de fractura baja el
caudal por dia producido; si la dosis solo mueve los dias (cierres), la regla lo deja dicho.

CORRECCION DE REDACCION (2026-11-17, despues de ver los resultados, revision de Opus; no cambia ningun codigo ni la regla): el semiancho
del IC mide la precision, no cuanto efecto queda descartado; lo descartado es lo que supera la cota superior del IC (limite alto en
desvios de la caida), y el texto del veredicto la publica. "Falsar el mecanismo" se lee como "no se detecto dosis y respuesta".

Que NO prueba:
  * Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometria de la fractura no estan en el
    dato publico, y el hijo mas cercano puede no ser el que golpeo al padre.
  * Un coeficiente positivo no separa el golpe de un cierre preventivo mas largo cuanto mas grande es el trabajo: la dosis puede
    mover la decision del operador. La respuesta crece con la dosis bajo las dos lecturas; la frase dice solo eso.
  * Los eventos de un mismo hijo comparten pad y calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.
  * Los datos de presion de la base publica tienen ceros y valores atipicos; se tratan como se dijo arriba.
"""
from __future__ import annotations

import math

import duckdb
import numpy as np

from pipeline import descomposicion, placebo
from pipeline.costo import SEMILLA, _clusters, _escribir, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import _g

B_MAIN = 2000
B_SENS = 1000
SEMILLA_DOSIS = SEMILLA + 8_000_000
# Offsets fijos de semilla por (resultado, analisis); semilla = SEMILLA_DOSIS + offset.
# Resultado A suma 0 y B suma 50; analisis: quintiles v1..v4 = 1..4, conjunto = 10,
# sensibilidades sin_terminacion = 20, solo_tapon = 21, rangos = 22, sola v1..v4 = 23..26.
RES_OFFSET = {"A": 0, "B": 50}
ANA_QUINTIL = {"arena_etapa": 1, "arena_rama": 2, "presion": 3, "deplecion": 4}
ANA_CONJUNTO = 10
ANA_SENS = {"sin_terminacion": 20, "solo_tapon": 21, "rangos": 22}
ANA_SOLA = {"arena_etapa": 23, "arena_rama": 24, "presion": 25, "deplecion": 26}

VARIABLES = ("arena_etapa", "arena_rama", "presion", "deplecion")
NOMBRES = {
    "arena_etapa": "arena por etapa",
    "arena_rama": "arena por metro de rama",
    "presion": "presión máxima de tratamiento",
    "deplecion": "depleción del padre",
}
NOM_SENS = {
    "sin_terminacion": "sin dummies de terminación",
    "solo_tapon": "solo Tapón disparo",
    "rangos": "variables como rangos percentil",
    "sola": "cada variable sola",
}

EVENTOS_A_SQL = """
select e.padre, e.mes_frac, h.pad_id as pad_hijo, trim(e.area) as area, e.km_min, e.edad_meses, e.base_m3_d, e.hijos_1km,
       e.hijo_cercano, m.indice, b.indice_control
from int_interferencia_evento e
left join int_pozo_ubicacion h on h.pozo_id = e.hijo_cercano
join int_interferencia_mes m on m.padre = e.padre and m.mes_frac = e.mes_frac and m.k = 1
join mart_interferencia_brecha b on b.grupo_edad = e.grupo_edad and b.k = 1
where e.banda = 'cercano'
order by e.padre, e.mes_frac
"""


def _demean(a, grupo, n_g=None):
    """Centra cada columna por grupo (efectos fijos absorbidos, como costo.ajustar_eje con `grupo`)."""
    a = np.asarray(a, dtype=float)
    grupo = np.asarray(grupo, dtype=int)
    n_g = int(grupo.max()) + 1 if n_g is None else int(n_g)
    cnt = np.maximum(np.bincount(grupo, minlength=n_g), 1)
    if a.ndim == 1:
        return a - (np.bincount(grupo, a, n_g) / cnt)[grupo]
    if a.shape[1] == 0:
        return a.copy()
    return np.column_stack([a[:, j] - (np.bincount(grupo, a[:, j], n_g) / cnt)[grupo] for j in range(a.shape[1])])


def _ols(y, X):
    """MCO sin constante, para columnas ya centradas por celda de efectos fijos."""
    beta, *_ = np.linalg.lstsq(np.asarray(X, dtype=float), np.asarray(y, dtype=float), rcond=None)
    return np.asarray(beta, dtype=float)


def _p_boot(b):
    """p de dos colas de la regla: min(1, 2 * (1 + min(#b <= 0, #b >= 0)) / (B + 1))."""
    b = np.asarray(b, dtype=float)
    # AMBIGUO: un remuestreo con un quintil vacio da nan y no cuenta ni de un lado ni del otro; B es la cuenta efectiva.
    b = b[~np.isnan(b)]
    if len(b) == 0:
        return 1.0
    return min(1.0, 2.0 * (1 + min(int((b <= 0).sum()), int((b >= 0).sum()))) / (len(b) + 1))


def _holm(pvals):
    """p ajustados por Holm (step-down, monotonos, originales en su orden)."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    orden = np.argsort(p, kind="stable")
    adj = np.empty(m)
    techo = 0.0
    for rango, j in enumerate(orden):
        techo = max(techo, (m - rango) * p[j])
        adj[j] = techo
    return np.minimum(adj, 1.0)


def _rangos_medios(x):
    """Rangos 1..n con promedio en los empates."""
    x = np.asarray(x, dtype=float)
    orden = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[orden[j + 1]] == x[orden[i]]:
            j += 1
        r[orden[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def _spearman(a, b):
    """Correlacion de Spearman por rangos (sin scipy); nan si alguna de las dos es constante."""
    ra, rb = _rangos_medios(a), _rangos_medios(b)
    sa, sb = ra.std(), rb.std()
    if sa == 0 or sb == 0:
        return float("nan")
    return float(((ra - ra.mean()) * (rb - rb.mean())).mean() / (sa * sb))


def _unir(nombres):
    """Une con ', ' y ' y ': X; X y Y; X, Y y Z."""
    ns = list(nombres)
    if len(ns) <= 1:
        return "".join(ns)
    return ", ".join(ns[:-1]) + " y " + ns[-1]


def _es_base(term) -> bool:
    # La regla fija la base en 'Tapon disparo' y el warehouse guarda 'Tapón disparo': se compara por prefijo.
    return isinstance(term, str) and term.startswith("Tap")


def veredicto(cumplen: list[str], contrarias: list[str], ordenes: list[str], n_caso_completo: int, pads: int,
              semiancho: float | None = None, cota: float | None = None) -> tuple[str, str]:
    """Codigo y texto del veredicto de la regla. `cumplen`, `contrarias` y `ordenes` llevan nombres para mostrar.

    `semiancho` es el semiancho del IC sin ajustar por Holm mas ancho, en desvios de la caida, y solo se usa
    en el texto de 'sin dosis y respuesta'. Las de signo contrario se informan aparte y nunca cambian el codigo.
    """
    if len(cumplen) >= 2:
        codigo = "dosis y respuesta"
    elif len(cumplen) == 1:
        codigo = "una sola variable"
    elif ordenes:
        codigo = "orden sin coeficiente"
    else:
        codigo = "sin dosis y respuesta"
    # La muestra chica degrada todo veredicto salvo la regla positiva (dos o mas variables), que no se debilita.
    if codigo != "dosis y respuesta" and (n_caso_completo < 1000 or pads < 150):
        codigo = "no concluyente por muestra"
    if codigo == "dosis y respuesta":
        texto = f"la caída crece con {_unir(cumplen)}, como se espera de un golpe de fractura"
    elif codigo == "una sola variable":
        texto = (f"solo {cumplen[0]} cumple con signo positivo y p ajustado menor que 0,05: no alcanza la regla de dos "
                 "o más; el mecanismo no queda falsado ni confirmado")
    elif codigo == "sin dosis y respuesta":
        texto = ("el dato público no muestra dosis y respuesta: ninguna variable cumple en el modelo conjunto y ninguna "
                 "tiene orden en los quintiles, lo que es compatible con cierre preventivo o con variables no observadas "
                 "(espaciamiento real)")
        if cota is not None:
            texto += (f"; la cota superior mayor de los IC sin ajustar por Holm es de {_g(cota, 2)} desvíos de la "
                      "caída: el efecto positivo compatible con los datos llega, como mucho, a eso")
            if semiancho is not None:
                texto += f" (el semiancho mayor, {_g(semiancho, 2)}, mide la precisión y no el efecto descartado)"
        elif semiancho is not None:
            texto += (f"; el semiancho mayor de los IC sin ajustar por Holm es de {_g(semiancho, 2)} desvíos de la "
                      "caída (mide la precisión, no el efecto descartado)")
        texto += ". No se detectó dosis y respuesta con datos públicos; eso no dice que no haya golpes de fractura"
    elif codigo == "orden sin coeficiente":
        texto = (f"ninguna variable cumple en el modelo conjunto pero hay orden en los quintiles en {_unir(ordenes)}: "
                 "no se afirma ni se descarta")
    else:
        texto = (f"muestra chica para juzgar (n = {_g(n_caso_completo)} eventos de caso completo, {_g(pads)} pads hijo; "
                 "la regla pide 1.000 eventos y 150 pads): el modelo conjunto se publica pero el veredicto queda no "
                 "concluyente por muestra")
    return codigo, texto


def _filas(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _trabajos_hijo(con, hijos) -> dict:
    """Trabajo de cada hijo: filas de stg_fractura con la primera fecha_inicio del pozo.

    Arena y etapas se suman, rama y presion toman el maximo, terminacion es la de la fila con mas arena
    (desempate alfabetico). Las filas sin fecha no fijan mes_frac y quedan fuera del trabajo.
    """
    por_pozo: dict = {}
    for f in _filas(con, "select pozo_id, fecha_inicio, rama_horizontal_m, etapas, arena_tn, terminacion, "
                         "presion_maxima_psi from stg_fractura"):
        por_pozo.setdefault(f["pozo_id"], []).append(f)
    out = {}
    for h in set(hijos):
        cand = [f for f in por_pozo.get(h, []) if f["fecha_inicio"] is not None]
        if not cand:
            continue
        job = [f for f in cand if f["fecha_inicio"] == min(f["fecha_inicio"] for f in cand)]
        arenas = [f["arena_tn"] for f in job if f["arena_tn"] is not None]
        etapas = [f["etapas"] for f in job if f["etapas"] is not None]
        ramas = [f["rama_horizontal_m"] for f in job if f["rama_horizontal_m"] is not None]
        pres = [f["presion_maxima_psi"] for f in job if f["presion_maxima_psi"] is not None]
        # AMBIGUO: para elegir la terminacion, una arena nula cuenta como menos que cualquier valor.
        top = min(job, key=lambda f: (-(f["arena_tn"] if f["arena_tn"] is not None else float("-inf")),
                                      f["terminacion"] or ""))
        out[h] = {"arena": sum(arenas) if arenas else None, "etapas": sum(etapas) if etapas else None,
                  "rama": max(ramas) if ramas else None, "presion": max(pres) if pres else None,
                  "terminacion": top["terminacion"]}
    return out


def _deplecion(con) -> dict:
    """Petroleo acumulado del padre antes de mes_frac por metro de rama del padre, por (padre, mes_frac).

    None si la rama del padre no es positiva o el acumulado no es positivo.
    """
    acum = {(r["padre"], r["mes_frac"]): r["acum"] for r in _filas(con,
            "select e.padre, e.mes_frac, coalesce(sum(x.petroleo_m3), 0) as acum "
            "from (select distinct padre, mes_frac from int_interferencia_evento where banda = 'cercano') e "
            "left join fct_produccion x on x.pozo_id = e.padre and x.mes < e.mes_frac "
            "group by e.padre, e.mes_frac")}
    lat = {r["pozo_id"]: r["rama_horizontal_m"] for r in _filas(con, "select pozo_id, rama_horizontal_m "
                                                                     "from dim_fractura_pozo")}
    out = {}
    for clave, a in acum.items():
        rama = lat.get(clave[0])
        out[clave] = a / rama if (a is not None and rama is not None and a > 0 and rama > 0) else None
    return out


def _recorta(x):
    return min(max(x, 0.0), 2.0)


def _dataset_a(con) -> dict:
    """Eventos 'cercano' con caida A, las cuatro variables en bruto y los controles en bruto.

    Devuelve arreglos alineados por evento; lo faltante es nan (numericos) o None (textos).
    """
    ev = _filas(con, EVENTOS_A_SQL)
    trab = _trabajos_hijo(con, [e["hijo_cercano"] for e in ev])
    dep = _deplecion(con)
    n = len(ev)
    d = {"caida": np.full(n, np.nan), "padre": np.zeros(n, dtype=np.int64), "hijo": np.zeros(n, dtype=np.int64),
         "km": np.full(n, np.nan), "edad": np.full(n, np.nan), "base": np.full(n, np.nan),
         "hijos": np.full(n, np.nan), "term": np.full(n, None, dtype=object),
         "area": np.full(n, None, dtype=object), "anio": np.zeros(n, dtype=int),
         "cluster": np.full(n, None, dtype=object), "mes": [None] * n}
    for j in range(4):
        d[f"v{j + 1}"] = np.full(n, np.nan)
    for i, e in enumerate(ev):
        t = trab.get(e["hijo_cercano"], {})
        arena, etapas, rama, pres = t.get("arena"), t.get("etapas"), t.get("rama"), t.get("presion")
        if arena is not None and etapas is not None and arena > 0 and etapas > 0:
            d["v1"][i] = math.log(arena / etapas)
        if arena is not None and rama is not None and arena > 0 and rama > 0:
            d["v2"][i] = math.log(arena / rama)
        if pres is not None and 0 < pres < 20000:
            d["v3"][i] = pres
        depad = dep.get((e["padre"], e["mes_frac"]))
        if depad is not None and depad > 0:
            d["v4"][i] = math.log(depad)
        if e["indice"] is not None and e["indice_control"] is not None:
            d["caida"][i] = _recorta(e["indice_control"]) - _recorta(e["indice"])
        d["padre"][i], d["hijo"][i] = e["padre"], e["hijo_cercano"]
        for col, val in (("km", e["km_min"]), ("edad", e["edad_meses"]), ("base", e["base_m3_d"]),
                          ("hijos", e["hijos_1km"])):
            if val is not None:
                d[col][i] = val
        d["term"][i] = t.get("terminacion")
        d["area"][i] = e["area"]
        d["anio"][i] = e["mes_frac"].year
        d["mes"][i] = e["mes_frac"]
        d["cluster"][i] = str(e["pad_hijo"]) if e["pad_hijo"] is not None else f"hijo:{e['hijo_cercano']}"
    return d


def _caida_b(con, d: dict, k: int = 1) -> np.ndarray:
    """Caida B (menos el log del indice de caudal por dia al mes 1, variante sin cerrados) alineada con _dataset_a.

    Solo banda cercana; nan donde el evento no entra en el marco del placebo o no aparece en ambas tablas.
    """
    D = descomposicion.cargar_ext(con, placebo.cargar(con))
    m = placebo.marco(D, D["hijo_mes"], ks=(k,), base=placebo.BASE_LIMPIA)
    _ld, lr = descomposicion._logs(D, m, k, False)
    ids = [r[0] for r in con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall()]
    M0 = 2000 * 12  # mismo origen que placebo._mes_idx
    vals = {}
    for i in range(len(m["mes"])):
        if m["banda"][i] != 0 or not np.isfinite(lr[i]):
            continue
        v = int(m["mes"][i]) + M0
        vals[(ids[int(m["padre"][i])], int(D["hijo_id"][int(m["hijo"][i])]), v // 12, v % 12 + 1)] = -float(lr[i])
    out = np.full(len(d["padre"]), np.nan)
    for i in range(len(out)):
        mf = d["mes"][i]
        out[i] = vals.get((int(d["padre"][i]), int(d["hijo"][i]), mf.year, mf.month), np.nan)
    return out


def _controles(d, idx, sin_term=False):
    """Matriz de controles y codigos de celda de EF, definidos dentro de la muestra `idx`.

    Numericos: km, ln(edad con minimo 1), base/10, hijos. Dummies de terminacion con base Tapón
    (niveles con menos de 20 eventos en 'otras'). Celdas de area por año (celdas con menos de 5
    eventos en una sola por area).
    """
    from collections import Counter

    idx = np.asarray(idx)
    C = np.column_stack([d["km"][idx], np.log(np.maximum(d["edad"][idx], 1)), d["base"][idx] / 10, d["hijos"][idx]])
    if not sin_term:
        term = list(d["term"][idx])
        chicos = {t for t, c in Counter(term).items() if c < 20}
        mape = ["otras" if t in chicos else t for t in term]
        bases = {m for t, m in zip(term, mape) if _es_base(t)}
        base = next(iter(bases)) if bases else None
        for niv in sorted(set(mape)):
            if niv != base:
                C = np.column_stack([C, (np.array(mape) == niv).astype(float)])
    celda = list(zip(list(d["area"][idx]), [int(a) for a in d["anio"][idx]]))
    cuenta = Counter(celda)
    fin = [(a, None if cuenta[(a, y)] < 5 else y) for a, y in celda]
    cod = {}
    grupo = np.array([cod.setdefault(c, len(cod)) for c in fin], dtype=int)
    return C, grupo


def _std(x):
    x = np.asarray(x, dtype=float)
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else np.zeros_like(x)


def _quintil_idx(x):
    """Quintil 0..4 por rango (empates por orden estable), en quintos parejos."""
    orden = np.argsort(np.asarray(x, dtype=float), kind="stable")
    r = np.empty(len(orden), dtype=int)
    r[orden] = np.arange(len(orden))
    return r * 5 // len(orden)


def analisis_quintil(y, x, C, grupo, clusters, semilla, reps=B_MAIN):
    """Medias de la caida ajustada por quintil con IC por pads, diferencia Q5-Q1 y Spearman de las medias."""
    import warnings

    y = np.asarray(y, dtype=float)
    ajust = (_demean(y, grupo) - _demean(C, grupo) @ _ols(_demean(y, grupo), _demean(C, grupo))) + y.mean()
    q = _quintil_idx(x)
    medias = np.array([ajust[q == k].mean() for k in range(5)])
    ns = np.array([(q == k).sum() for k in range(5)])
    cl = _clusters(np.asarray(clusters))
    rng = np.random.default_rng(semilla)
    bm = np.full((reps, 5), np.nan)
    for b in range(reps):
        i = _remuestra(rng, cl)
        a, qq = ajust[i], q[i]
        for k in range(5):
            sel = a[qq == k]
            if len(sel):
                bm[b, k] = sel.mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        ics = np.nanpercentile(bm, [2.5, 97.5], axis=0).T
        dif = bm[:, 4] - bm[:, 0]
        ic_dif = np.nanpercentile(dif, [2.5, 97.5])
    return {"medias": medias, "ics": ics, "ns": ns, "dif": float(medias[4] - medias[0]),
            "ic_dif": (float(ic_dif[0]), float(ic_dif[1])), "p": _p_boot(dif),
            "spearman": _spearman(medias, np.arange(1, 6))}


def _ajuste(y, Xvars, C, grupo, clusters, semilla, reps):
    """MCO de y contra dosis + controles (centrados por celda) con bootstrap por pads hijo.

    Devuelve (coeficientes de las dosis, IC 95% de percentiles, p sin ajustar por Holm).
    """
    Xvars = np.asarray(Xvars, dtype=float)
    C = np.asarray(C, dtype=float)
    k = Xvars.shape[1]
    X = np.column_stack([Xvars, C]) if C.shape[1] else Xvars
    beta = _ols(_demean(y, grupo), _demean(X, grupo))
    cl = _clusters(np.asarray(clusters))
    n_g = int(np.asarray(grupo).max()) + 1
    rng = np.random.default_rng(semilla)
    boots = np.empty((reps, k))
    for b in range(reps):
        i = _remuestra(rng, cl)
        # AMBIGUO: lo estandarizado en la muestra original no se re-estandariza por remuestreo; los indices de
        # celda de EF son los originales y el centrado se rehace dentro de cada remuestreo.
        boots[b] = _ols(_demean(y[i], grupo[i], n_g), _demean(X[i], grupo[i], n_g))[:k]
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    return beta[:k], np.column_stack([lo, hi]), np.array([_p_boot(boots[:, j]) for j in range(k)])


def _vif(X_std, C, grupo):
    """FIV por dosis: 1/(1-R2) de cada dosis contra las demas mas controles y EF."""
    X_std = np.asarray(X_std, dtype=float)
    C = np.asarray(C, dtype=float)
    out = []
    for j in range(X_std.shape[1]):
        resto = np.delete(X_std, j, axis=1)
        resto = np.column_stack([resto, C]) if C.shape[1] else resto
        yd = _demean(X_std[:, j], grupo)
        ss_res = float(((yd - _demean(resto, grupo) @ _ols(yd, _demean(resto, grupo))) ** 2).sum())
        ss_tot = float((yd ** 2).sum())  # la media es 0 por construccion
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        out.append(1.0 / (1.0 - r2) if r2 < 1 else float("inf"))
    return np.array(out)


def _rango_pct(x):
    # AMBIGUO: percentil como (rango medio - 1) / (n - 1) en [0, 1]; despues se estandariza como las demas.
    x = np.asarray(x, dtype=float)
    return (_rangos_medios(x) - 1) / max(len(x) - 1, 1)


def _mascara_controles(d, idx):
    idx = np.asarray(idx)
    ok = np.isfinite(d["km"][idx]) & np.isfinite(d["edad"][idx]) & np.isfinite(d["base"][idx])
    ok &= np.isfinite(d["hijos"][idx])
    ok &= np.array([t is not None for t in d["term"][idx]])
    ok &= np.array([a is not None for a in d["area"][idx]])
    return ok


def analizar(res, y, d):
    """Quintiles, modelo conjunto y sensibilidades de un resultado. Devuelve filas de marts e insumos del veredicto."""
    y = np.asarray(y, dtype=float)
    base = np.flatnonzero(np.isfinite(y))
    ib = base[_mascara_controles(d, base)]
    fmod, fq, ford, fsens = [], [], [], []
    difs, ps, sps, ics_d, ns = {}, {}, {}, {}, {}
    for j, var in enumerate(VARIABLES):
        idx = ib[np.isfinite(d[f"v{j + 1}"][ib])]
        C, grupo = _controles(d, idx)
        r = analisis_quintil(y[idx], d[f"v{j + 1}"][idx], C, grupo, d["cluster"][idx],
                             SEMILLA_DOSIS + RES_OFFSET[res] + ANA_QUINTIL[var])
        for k in range(5):
            fq.append((res, var, k + 1, int(r["ns"][k]), float(r["medias"][k]),
                       float(r["ics"][k][0]), float(r["ics"][k][1])))
        difs[var], ps[var], sps[var], ics_d[var], ns[var] = r["dif"], r["p"], r["spearman"], r["ic_dif"], len(idx)
    ph_ord = dict(zip(VARIABLES, _holm([ps[v] for v in VARIABLES])))
    ordenes = []
    for var in VARIABLES:
        orden = bool(sps[var] >= 0.7 and difs[var] > 0 and ph_ord[var] < 0.05)
        if orden:
            ordenes.append(NOMBRES[var])
        ford.append((res, var, ns[var], float(sps[var]), float(difs[var]), float(ics_d[var][0]), float(ics_d[var][1]),
                     float(ps[var]), float(ph_ord[var]), orden))
    cc = ib[np.all([np.isfinite(d[f"v{j + 1}"][ib]) for j in range(4)], axis=0)]
    X = np.column_stack([_std(d[f"v{j + 1}"][cc]) for j in range(4)])
    C, grupo = _controles(d, cc)
    coefs, ics, ps = _ajuste(y[cc], X, C, grupo, d["cluster"][cc],
                             SEMILLA_DOSIS + RES_OFFSET[res] + ANA_CONJUNTO, B_MAIN)
    ph = _holm(ps)
    vif = _vif(X, C, grupo)
    n, pads = len(cc), len(set(d["cluster"][cc]))
    cumplen, contrarias = [], []
    for j, var in enumerate(VARIABLES):
        cumple = bool(coefs[j] > 0 and ph[j] < 0.05)
        contra = bool(coefs[j] < 0 and ph[j] < 0.05)
        if cumple:
            cumplen.append(NOMBRES[var])
        if contra:
            contrarias.append(NOMBRES[var])
        fmod.append((res, var, float(coefs[j]), float(ics[j][0]), float(ics[j][1]), float(ps[j]), float(ph[j]),
                     n, pads, float(vif[j]), cumple, contra))
    sd_y = float(y[cc].std())
    # AMBIGUO: los "desvios de la caida" usan ddof = 0, igual que la estandarizacion de las dosis.
    semiancho = max((ics[j][1] - ics[j][0]) / 2 for j in range(4)) / sd_y if sd_y > 0 else float("nan")
    # Cota superior: el mayor limite alto de los IC sin ajustar, en desvios de la caida (efecto positivo mas grande compatible).
    cota = max(ics[j][1] for j in range(4)) / sd_y if sd_y > 0 else float("nan")
    # Sensibilidades (B = 1000): varian el modelo sobre la muestra de caso completo, salvo 'solo_tapon'.
    # AMBIGUO: 'sola' y 'rangos' usan caso completo (la sensibilidad varia el modelo, no la muestra).
    C0, g0 = _controles(d, cc, sin_term=True)
    c, ic, _p = _ajuste(y[cc], X, C0, g0, d["cluster"][cc],
                        SEMILLA_DOSIS + RES_OFFSET[res] + ANA_SENS["sin_terminacion"], B_SENS)
    for j, var in enumerate(VARIABLES):
        fsens.append((res, "sin_terminacion", var, float(c[j]), float(ic[j][0]), float(ic[j][1]), n))
    sub = cc[np.array([_es_base(t) for t in d["term"][cc]])]
    if len(sub):
        Xs = np.column_stack([_std(d[f"v{j + 1}"][sub]) for j in range(4)])
        Cs, gs = _controles(d, sub)
        c, ic, _p = _ajuste(y[sub], Xs, Cs, gs, d["cluster"][sub],
                            SEMILLA_DOSIS + RES_OFFSET[res] + ANA_SENS["solo_tapon"], B_SENS)
        for j, var in enumerate(VARIABLES):
            fsens.append((res, "solo_tapon", var, float(c[j]), float(ic[j][0]), float(ic[j][1]), len(sub)))
    Xr = np.column_stack([_std(_rango_pct(d[f"v{j + 1}"][cc])) for j in range(4)])
    c, ic, _p = _ajuste(y[cc], Xr, C, grupo, d["cluster"][cc],
                        SEMILLA_DOSIS + RES_OFFSET[res] + ANA_SENS["rangos"], B_SENS)
    for j, var in enumerate(VARIABLES):
        fsens.append((res, "rangos", var, float(c[j]), float(ic[j][0]), float(ic[j][1]), n))
    for j, var in enumerate(VARIABLES):
        c, ic, _p = _ajuste(y[cc], X[:, [j]], C, grupo, d["cluster"][cc],
                            SEMILLA_DOSIS + RES_OFFSET[res] + ANA_SOLA[var], B_SENS)
        fsens.append((res, "sola", var, float(c[0]), float(ic[0][0]), float(ic[0][1]), n))
    return {"modelo": fmod, "quintiles": fq, "orden": ford, "sens": fsens, "cumplen": cumplen,
            "contrarias": contrarias, "ordenes": ordenes, "n": n, "pads": pads, "semiancho": semiancho, "cota": cota}


COLS_MODELO = [("resultado", "varchar"), ("variable", "varchar"), ("coef_sd", "double"), ("ic_bajo", "double"),
               ("ic_alto", "double"), ("p", "double"), ("p_holm", "double"), ("n", "integer"), ("pads", "integer"),
               ("vif", "double"), ("cumple", "boolean"), ("signo_contrario", "boolean")]
COLS_QUINTILES = [("resultado", "varchar"), ("variable", "varchar"), ("quintil", "integer"), ("n", "integer"),
                  ("media_ajustada", "double"), ("ic_bajo", "double"), ("ic_alto", "double")]
COLS_ORDEN = [("resultado", "varchar"), ("variable", "varchar"), ("n", "integer"), ("spearman", "double"),
              ("q5_menos_q1", "double"), ("ic_bajo", "double"), ("ic_alto", "double"), ("p", "double"),
              ("p_holm", "double"), ("orden", "boolean")]
COLS_SENS = [("resultado", "varchar"), ("sensibilidad", "varchar"), ("variable", "varchar"), ("coef_sd", "double"),
             ("ic_bajo", "double"), ("ic_alto", "double"), ("n", "integer")]
COLS_VEREDICTO = [("resultado", "varchar"), ("codigo", "varchar"), ("texto", "varchar")]


def pagina_dosis(con) -> str:
    """Pagina de wiki a partir de los marts de dosis.py. Texto en espanol, sin rayas largas."""
    mod = {(r[0], r[1]): r for r in con.execute("select resultado, variable, coef_sd, ic_bajo, ic_alto, p_holm, n, "
                                               "pads, vif, cumple from mart_dosis_modelo").fetchall()}
    quint = {(r[0], r[1], r[2]): r for r in con.execute("select resultado, variable, quintil, n, media_ajustada "
                                                       "from mart_dosis_quintiles").fetchall()}
    nq = {(r[0], r[1]): r[2] for r in con.execute("select resultado, variable, sum(n) from mart_dosis_quintiles "
                                                 "group by resultado, variable").fetchall()}
    orde = {(r[0], r[1]): r for r in con.execute("select resultado, variable, spearman, q5_menos_q1, ic_bajo, ic_alto, "
                                                "p_holm, orden from mart_dosis_orden").fetchall()}
    sens = con.execute("select resultado, sensibilidad, variable, coef_sd, ic_bajo, ic_alto, n from mart_dosis_sens "
                       "order by resultado, sensibilidad, variable").fetchall()
    ver = {r[0]: (r[1], r[2]) for r in con.execute("select resultado, codigo, texto from mart_dosis_veredicto").fetchall()}
    L = ["# Dosis y respuesta: trabajos más grandes, ¿más caída?", "",
         "Página generada por `pipeline/dosis.py`. Pregunta si la caída del padre al mes 1 crece con el tamaño del trabajo "
         "del hijo (arena por etapa, arena por metro de rama, presión máxima) y con la depleción del padre: eso es lo que "
         "predice la física de los golpes de fractura. Resultado A, caída del índice al mes 1 (principal, decide el veredicto). "
         "Resultado B, caída del caudal por día efectivo (se informa aparte y no cambia el veredicto de A).", "",
         "## Veredicto (resultado A)", "",
         f"**{ver['A'][0]}**: {ver['A'][1]}.", "",
         "Regla fijada antes de correr: dos o más variables cumplen (signo positivo y p ajustado por Holm sobre las cuatro "
         "menor que 0,05) con el modelo conjunto, controles y efectos fijos de área por año, e inferencia por bootstrap de "
         f"pads hijo (B = {_g(B_MAIN)}). Resultado B: **{ver['B'][0]}**: {ver['B'][1]}.", "",
         "## Modelo conjunto (las cuatro variables a la vez)", ""]
    for res, titulo in (("A", "Resultado A, caída del índice"), ("B", "Resultado B, caída del caudal por día")):
        r0 = mod[(res, VARIABLES[0])]
        L += [f"### {titulo} (n = {_g(r0[6])}, pads = {_g(r0[7])})", "",
              "| Variable | Coef por desvío | IC 95% | p Holm | FIV | Cumple |", "| --- | ---: | --- | ---: | ---: | --- |"]
        for var in VARIABLES:
            _re, _va, c, lo, hi, ph, _n, _pa, vif, cu = mod[(res, var)]
            L.append(f"| {NOMBRES[var]} | {_g(c, 3)} | {_g(lo, 3)} a {_g(hi, 3)} | {_g(ph, 3)} | {_g(vif, 1)} | "
                     f"{'sí' if cu else 'no'} |")
        L.append("")
    L += ["## Quintiles de cada variable (caída ajustada media por quintil)", "",
          "La caída ajustada es el residuo de la caída contra los controles y efectos fijos más la media general.", ""]
    for res, titulo in (("A", "Resultado A"), ("B", "Resultado B")):
        L += [f"### {titulo}", "", "| Variable | Q1 | Q2 | Q3 | Q4 | Q5 | n |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for var in VARIABLES:
            ms = " | ".join(_g(quint[(res, var, k)][4], 3) for k in range(1, 6))
            L.append(f"| {NOMBRES[var]} | {ms} | {_g(nq[(res, var)])} |")
        L.append("")
    L += ["## Orden en los quintiles", "",
          "| Resultado | Variable | Spearman | Q5 menos Q1 (IC 95%) | p Holm | Orden |",
          "| --- | --- | ---: | --- | ---: | --- |"]
    for res in ("A", "B"):
        for var in VARIABLES:
            _re, _va, sp, d, lo, hi, ph, od = orde[(res, var)]
            L.append(f"| {res} | {NOMBRES[var]} | {_g(sp, 2)} | {_g(d, 3)} ({_g(lo, 3)} a {_g(hi, 3)}) | {_g(ph, 3)} | "
                     f"{'sí' if od else 'no'} |")
    L += ["", 'Hay "orden" si el Spearman de las cinco medias con el número de quintil es al menos 0,7 y Q5 menos Q1 es '
          "positiva con p Holm menor que 0,05.", "",
          "## Sensibilidades (se informan, no entran en el veredicto)", "",
          f"Modelo conjunto con cambios (B = {_g(B_SENS)} remuestreos): sin las dummies de terminación, solo terminación "
          "Tapón disparo, las cuatro variables como rangos percentil, y cada variable sola con los controles.", "",
          "| Resultado | Sensibilidad | Variable | Coef por desvío | IC 95% | n |",
          "| --- | --- | --- | ---: | --- | ---: |"]
    for res, sen, var, c, lo, hi, n in sens:
        L.append(f"| {res} | {NOM_SENS.get(sen, sen)} | {NOMBRES.get(var, var)} | {_g(c, 3)} | {_g(lo, 3)} a {_g(hi, 3)} "
                 f"| {_g(n)} |")
    L += ["", "## Qué no prueba", "",
          "- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometría de la fractura "
          "no están en el dato público, y el hijo más cercano puede no ser el que golpeó al padre.",
          "- Un coeficiente positivo no separa el golpe de un cierre preventivo más largo cuanto más grande es el trabajo: la "
          "dosis puede mover la decisión del operador. Si hubiera una respuesta que crece con la dosis, crecería bajo las dos lecturas.",
          "- Los eventos de un mismo hijo comparten pad y calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.",
          "- Los datos de presión de la base pública tienen ceros y valores atípicos: los ceros cuentan como faltantes y solo "
          "entran presiones entre 0 y 20.000 psi.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    d = _dataset_a(con)
    yb = _caida_b(con, d)
    print(f"[dosis] eventos con caida: A {int(np.isfinite(d['caida']).sum())} de {len(d['caida'])}, "
          f"B {int(np.isfinite(yb).sum())}")
    rA = analizar("A", d["caida"], d)
    rB = analizar("B", yb, d)
    _escribir(con, "mart_dosis_modelo", COLS_MODELO, rA["modelo"] + rB["modelo"])
    _escribir(con, "mart_dosis_quintiles", COLS_QUINTILES, rA["quintiles"] + rB["quintiles"])
    _escribir(con, "mart_dosis_orden", COLS_ORDEN, rA["orden"] + rB["orden"])
    _escribir(con, "mart_dosis_sens", COLS_SENS, rA["sens"] + rB["sens"])
    codA, texA = veredicto(rA["cumplen"], rA["contrarias"], rA["ordenes"], rA["n"], rA["pads"], rA["semiancho"], rA["cota"])
    codB, texB = veredicto(rB["cumplen"], rB["contrarias"], rB["ordenes"], rB["n"], rB["pads"], rB["semiancho"], rB["cota"])
    if codA == "dosis y respuesta":
        texA += ", " + ("y la parte de caudal por día lo confirma" if len(rB["cumplen"]) >= 2
                        else "pero la parte de caudal por día no lo muestra por separado")
    _escribir(con, "mart_dosis_veredicto", COLS_VEREDICTO, [("A", codA, texA), ("B", codB, texB)])
    for r in rA["modelo"] + rB["modelo"]:
        print(f"[dosis] modelo {r[0]} {r[1]:<12} coef={r[2]:+.4f} IC {r[3]:+.4f} a {r[4]:+.4f} p={r[5]:.4f} "
              f"p_holm={r[6]:.4f} n={r[7]} pads={r[8]} vif={r[9]:.2f} cumple={r[10]} contraria={r[11]}")
    for r in rA["orden"] + rB["orden"]:
        print(f"[dosis] orden {r[0]} {r[1]:<12} n={r[2]} spearman={r[3]:.2f} q5_q1={r[4]:+.4f} p_holm={r[8]:.4f} "
              f"orden={r[9]}")
    print(f"[dosis] veredicto A: {codA}: {texA}")
    print(f"[dosis] veredicto B: {codB}: {texB}")
    if rA["contrarias"] or rB["contrarias"]:
        print(f"[dosis] signo contrario A={rA['contrarias']} B={rB['contrarias']}")
    con.close()


if __name__ == "__main__":
    main()
