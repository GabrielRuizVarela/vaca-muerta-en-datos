"""El lado del hijo dentro del pad: comparar hijos del mismo pad segun el petroleo que ya habian producido los pozos cuya rama pasa a menos de 600 m.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.hijo_pad

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no. Un "no firme" o un "sin
muestra" es un resultado terminado, no un motivo para rediseñar la regla.

Que se habia mirado antes de fijarla
- Publicado en el repo: pipeline.hijo (wiki/hallazgos/hijo.md), el lado del hijo con distancia de superficie de 1 km y tres grupos
  de exposicion, dio "no firme": muy depletado contra virgen -0,2 bbl por metro de rama (IC 95% -12,6 a 12,2) y un control negativo
  que NO es nulo (8,9; IC 2,1 a 15,7), porque las zonas depletadas son tambien las zonas densas y buenas. pipeline.hijo_celdas
  (celdas de 2 km) dio tambien "no firme": -9,2 bbl por metro (IC 95% -28,1 a 9,8), con un control negativo nulo en el grupo que
  decide. Los dos son con distancia de superficie; ninguno uso las ramas.
- Publicado: la pagina de trayectorias (wiki/hallazgos/trayectorias.md) mide la rama de 1.693 de 3.448 pozos del estudio. Cubre
  entre 76 y 98% de los hijos horizontales fracturados de 2016 a 2023, pero solo 39% de los de 2024 y 25% de los de 2025: la
  muestra de esta prueba es sobre todo de 2016 a 2023 y la pagina lo dice junto al veredicto.
- Al fijar esta regla no se habia calculado ninguna exposicion, ningun rendimiento, ninguna dispersion dentro del pad ni ningun
  conteo de pads de este diseno. Es una prueba nueva, no una repeticion: lo nuevo es el contrafactual (hijos del mismo pad, que
  quita el area, el operador, la epoca y casi todo el diseno de la terminacion) y la distancia (entre ramas, no de superficie).
  El resultado de las dos pruebas anteriores era conocido; por eso la pagina lo dice y no cambia el estado de `hijo_depletado`.

Pregunta
- Dos hijos del mismo pad, con la misma terminacion en lo grueso: el que se fracturo cuando ya producian pozos cuya rama pasa a
  menos de 600 m de la suya, produce menos petroleo por metro de rama en sus primeros 12 meses que el que se fracturo con menos
  exposicion?

Unidad y muestra (los pasos se publican con su conteo)
- Pasos 1 a 5: los de pipeline.hijo (hijo.cargar): pozo de mart_pozo_12m (petrolifero de shale con 12 meses publicados) con area,
  pad (pad_id de int_pozo_ubicacion), coordenadas, primer mes de petroleo, rama horizontal mayor que 0, etapas, arena y fecha de
  primera fractura (dim_fractura_pozo), con el primer petroleo entre 0 y 12 meses despues del mes de fractura.
- Paso 6: ano de la primera fractura entre ANIO_MIN (2016) y ANIO_MAX (2023), los dos incluidos.
- Paso 7: el hijo tiene la rama medida (mart_trayectoria_pozo con rama_lon y rama_lat no nulas).
- Paso 8: el pad del hijo tiene al menos MIN_HIJOS_PAD (2) hijos que pasaron el paso 7. La muestra del modelo son los hijos de
  esos pads, tengan o no dispersion de exposicion; los pads sin dispersion no aportan a la pendiente pero si a los controles.
- Pad: pad_id de int_pozo_ubicacion del hijo.

Resultado y exposicion
- Resultado y: petroleo de 12 meses por metro de rama (petroleo_12m_bbl / rama_horizontal_m de mart_pozo_12m), en bbl por metro,
  como en pipeline.hijo. Los metros del denominador son los de la rama horizontal de la fractura, igual que alli; la geometria
  de mart_trayectoria_pozo se usa solo para decir que pozos estan a menos de 600 m.
- Expositores: los pozos de int_pozo_mop (petroliferos de shale) con rama medida en mart_trayectoria_pozo, distintos del hijo, con
  mes de primer petroleo conocido. Un pozo sin rama medida no puede ser expositor: la exposicion cuenta solo lo medido y por eso
  es una cota inferior de la exposicion verdadera (ver "Que NO prueba").
- Cercano: la distancia minima entre la rama del hijo y la del expositor, en metros, es menor que RADIO_RAMA_M (600 m). Se mide
  con trayectorias.distancia_minima sobre las ramas de mart_trayectoria_pozo pasadas a metros con trayectorias.a_metros y
  con el origen en la boca del hijo (la misma que mart_trayectoria_par.m_min).
- Exposicion E (bbl por metro de rama del hijo): la suma, sobre los expositores cercanos, del petroleo acumulado en barriles
  (BBL_POR_M3 de pipeline.hijo) contando solo los meses de produccion ANTERIORES al mes de la primera fractura del hijo (el mes
  de la fractura y los siguientes no cuentan; es hijo.exposicion_real), dividida por la rama horizontal del hijo. Se incluyen
  los pozos del mismo pad que ya producian.
- Dispersion del pad: el maximo menos el minimo de E entre los hijos de la muestra del pad. Pad informativo: dispersion de al
  menos DISPERSION_MIN_BBL_M (50 bbl por metro).
- Control negativo Ec: lo mismo pero con los expositores cercanos cuyo primer mes de petroleo es posterior al ultimo mes de la
  ventana de resultado del hijo (su primer mes de petroleo mas 11 meses; es hijo.exposicion_control: no pudieron depletarlo ni
  interferirlo), con su petroleo acumulado hasta el ultimo mes con datos, por metro de rama del hijo. Misma muestra, mismo
  modelo, mismos radios.

Modelo principal (el unico que decide)
- y = beta (E / ESCALA_EXPOSICION) + gamma' C + alfa_pad + error, con ESCALA_EXPOSICION = 100 bbl por metro, efectos fijos de pad
  del hijo (alfa_pad, que se absorben restando la media del pad) y los controles C:
  * rama_horizontal_m del hijo;
  * la unidad donde navega la rama del hijo (mart_trayectoria_pozo.unidad), como indicadores de las unidades 1 a 6 presentes en
    la muestra, menos la mas frecuente; una unidad fuera de 1 a 6 es la categoria "sin unidad";
  * misma_unidad_frac: la parte de la exposicion E (en barriles) que viene de expositores de la misma unidad que el hijo, de 0 a
    1; vale 0 si E es 0 o si la unidad del hijo o la del expositor no esta en 1 a 6 (es la version por hijo de
    mart_trayectoria_par.misma_unidad).
- Estimacion: minimos cuadrados sobre las desviaciones respecto de la media de cada pad. beta se publica en bbl por metro de rama
  por cada 100 bbl por metro de exposicion. Las columnas de control que no varian dentro de los pads se descartan.
- IC 95% de percentiles (2,5 y 97,5) del bootstrap por pads: REPS_PAD repeticiones (2.000) en las que se remuestrean los pads
  de la muestra con reemplazo y cada copia de un pad es un pad distinto; la estimacion puntual es la de la muestra completa.
  Semilla fija SEMILLA_HIJO_PAD. Las mismas repeticiones sirven para el modelo principal y para el control negativo.
- Rendimiento virgen V: la mediana de y entre los hijos de la muestra con E igual a 0; si son menos de MIN_VIRGENES_REF (50), la
  mediana de y de todos los hijos de la muestra (y la pagina lo dice). "Dentro de 5%" quiere decir un valor de beta entre
  -UMBRAL_SIN_DEGRADACION V y +UMBRAL_SIN_DEGRADACION V (5% de V por cada 100 bbl por metro).
- Se dice "incluye cero" cuando ic_bajo <= 0 <= ic_alto y "excluye cero" en el otro caso.

VEREDICTO (con beta, su IC [lo, hi] y el IC [lo_c, hi_c] de beta en el control negativo; el control negativo es el mismo modelo
con Ec en lugar de E):
  * "sin muestra": menos de MIN_PADS_INFORMATIVOS (100) pads informativos en la muestra del modelo, o una estimacion que no se
    puede calcular (valores no finitos, o V no positivo).
  * "sostiene degradación": hi < 0 (el IC de beta esta por debajo de cero) Y el IC del control negativo incluye cero.
  * "no se ve degradación": el IC de beta incluye cero Y el del control negativo incluye cero Y lo >= -UMBRAL_SIN_DEGRADACION V
    Y hi <= UMBRAL_SIN_DEGRADACION V.
  * "ubicación": el IC del control negativo excluye cero (con cualquier signo de beta; la diferencia dentro del pad no se
    puede leer como depleccion).
  * "no firme": cualquier otro caso.
  Los tres veredictos con resultado son excluyentes: "sostiene" y "no se ve" piden el control negativo nulo y difieren en beta,
  y "ubicación" pide el control negativo no nulo. El orden de aplicacion es el de la lista.
- Cota superior de la perdida (se publica con cualquier veredicto): la mayor perdida compatible con el dato es el extremo bajo
  del IC de beta. Se publica como max(0, -lo) en bbl por metro por cada 100 bbl por metro de exposicion, como porcentaje de V, y
  a la mediana de las exposiciones positivas de la muestra (en bbl por metro). Es una cota superior, no una estimacion, y no
  dice que esa perdida exista. Si lo >= 0 la cota es 0 y la pagina lo dice.

Modelos descriptivos (se publican todos, sin veredicto propio; cada uno con su control negativo hermano)
- sin_controles: solo los efectos fijos de pad.
- radio_300 y radio_1000: el modelo principal con la exposicion de las ramas a menos de 300 m y de 1.000 m.
- otros_pads: el modelo principal con la exposicion que no cuenta a los pozos del pad del hijo (cuenta solo lo que viene de
  otros pads).
- misma_unidad: el modelo principal con la exposicion que cuenta solo a los expositores de la misma unidad que el hijo (con la
  unidad de los dos en 1 a 6); sin el control misma_unidad_frac, que seria constante.
- con_tiempo_pad: el modelo principal mas los meses desde la primera fractura del pad (el mes de fractura del hijo menos el
  menor mes de fractura entre los hijos de la muestra de su pad), para ver cuanto de la pendiente es el orden dentro del pad.

Equilibrio dentro del pad (descriptivo, antes del resultado; no condiciona el veredicto)
- La pendiente dentro del pad de cada variable de diseno (rama_horizontal_m, etapas, arena por metro, meses desde la primera
  fractura del pad) sobre E / ESCALA_EXPOSICION, con efectos fijos de pad y el mismo bootstrap por pads. Dice si la exposicion
  dentro del pad es el orden de las fracturas o el diseno.

Cobertura (descriptiva)
- Pads con 2 o mas hijos, pads informativos, hijos por ano de fractura, dispersion mediana de E de los pads informativos y la
  fraccion de hijos con E igual a 0.

Que NO prueba
- La exposicion cuenta solo pozos con rama medida. Es una cota inferior de la exposicion verdadera: con un error de medicion de
  ese tipo la pendiente por barril medido se atenua hacia cero y la cota superior de la perdida queda corta. Por eso "no se ve
  degradacion" no es "no hay degradacion".
- La rama medida de los expositores cubre 39% de los pozos de 2024 y 25% de los de 2025: el control negativo, que cuenta pozos
  que empiezan despues de la ventana del hijo (muchos de 2024 a 2026), mide menos de lo que hay y es un control menos potente que
  la exposicion real. Un IC del control que incluye cero es menos informativo que el de la exposicion real.
- Dentro del pad, la exposicion de un hijo es sobre todo el orden de las fracturas (los hijos posteriores ven producir a los
  anteriores) y la posicion de cada rama. Los efectos fijos de pad no quitan una tendencia dentro del pad (aprendizaje de la
  terminacion, calidad de la roca por posicion); el control negativo y con_tiempo_pad miran ese riesgo y no lo eliminan.
- Hijos y expositores del mismo pad comparten la roca, pero no la profundidad: la unidad es un control, no una identificacion de
  la zona de aterrizaje.
- La distancia entre ramas es la minima, no el espaciamiento a lo largo de la rama.
- Es una asociacion dentro del pad con controles de diseno, no una afirmacion causal.
- La muestra es de 2016 a 2023 y sobre todo de hijos con la rama medida: no habla de los hijos recientes.
"""
from __future__ import annotations

import math
import warnings
from collections import Counter

import duckdb
import numpy as np

from pipeline import hijo as hj
from pipeline.costo import SEMILLA
from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g
from pipeline.trayectorias import a_metros, distancia_minima

ANIO_MIN = 2016               # primera fractura del hijo, ano desde el que entra
ANIO_MAX = 2023               # primera fractura del hijo, ano hasta el que entra (incluido)
MIN_HIJOS_PAD = 2             # hijos de la muestra que tiene que tener un pad
RADIO_RAMA_M = 600.0          # m: distancia minima entre ramas que cuenta como exposicion
RADIOS_DESCRIPTIVOS_M = (300.0, 1000.0)   # m: radios de las sensibilidades radio_300 y radio_1000
DISPERSION_MIN_BBL_M = 50.0   # bbl por metro: dispersion de E dentro del pad para que el pad sea informativo
MIN_PADS_INFORMATIVOS = 100   # pads informativos para decidir
ESCALA_EXPOSICION = 100.0     # bbl por metro: unidad de beta
UMBRAL_SIN_DEGRADACION = 0.05  # fraccion de V por cada 100 bbl por metro: ancho del "no se ve degradación"
MIN_VIRGENES_REF = 50         # hijos con E = 0 para que V sea la mediana de ellos y no la de toda la muestra
REPS_PAD = 2000               # repeticiones del bootstrap por pads
SEMILLA_HIJO_PAD = SEMILLA + 90
UNIDADES_VALIDAS = (1, 2, 3, 4, 5, 6)   # las de trayectorias.UNIDADES; cualquier otra es "sin unidad"
VEREDICTOS = ("sostiene degradación", "no se ve degradación", "ubicación", "no firme", "sin muestra")
MODELOS_DESCRIPTIVOS = ("sin_controles", "radio_300", "radio_1000", "otros_pads", "misma_unidad", "con_tiempo_pad")

# ------------------------------------------------------------------ columnas de los marts

COLS_MUESTRA = [("paso", "integer"), ("descripcion", "varchar"), ("hijos", "integer"), ("pads", "integer")]
COLS_COEF = [("modelo", "varchar"), ("exposicion", "varchar"), ("termino", "varchar"), ("coef", "double"),
             ("ic_bajo", "double"), ("ic_alto", "double"), ("n", "integer"), ("pads", "integer"),
             ("pads_informativos", "integer"), ("pct_del_virgen", "double"), ("pct_ic_bajo", "double"),
             ("pct_ic_alto", "double"), ("virgen_mediana_bbl_m", "double"), ("veredicto", "varchar")]
COLS_RESUMEN = [("clave", "varchar"), ("valor", "double")]
COLS_EQUILIBRIO = [("variable", "varchar"), ("coef", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
                   ("n", "integer"), ("pads", "integer")]
COLS_ANIO = [("anio", "integer"), ("hijos", "integer"), ("pads", "integer"),
             ("hijos_en_pads_informativos", "integer")]

M_POR_GRADO = 111_320.0     # metros por grado, la misma escala de trayectorias.a_metros
TERMINO = "exposicion_por_100_bbl_m"


# ------------------------------------------------------------------ utilidades

def _texto_pad(pad) -> str:
    """El pad como texto: los nulos son un grupo propio (sin pad)."""
    return "" if pad is None else str(pad)


def _texto_pad_array(pad) -> np.ndarray:
    """Vector de pads como texto, para agrupar sin mezclar nulos con cadenas."""
    return np.array([_texto_pad(p) for p in np.asarray(pad, dtype=object)], dtype=object)


def _codigos(pad) -> tuple[np.ndarray, int]:
    """Codigos enteros de los grupos (pads) y cantidad de grupos."""
    unicos, cod = np.unique(_texto_pad_array(pad), return_inverse=True)
    return np.asarray(cod, dtype=int), len(unicos)


def _centrar(a: np.ndarray, cod: np.ndarray, g: int) -> np.ndarray:
    """Resta la media de cada grupo (los efectos fijos del pad se absorben asi)."""
    cnt = np.maximum(np.bincount(cod, minlength=g), 1)
    if a.ndim == 1:
        return a - (np.bincount(cod, a, minlength=g) / cnt)[cod]
    return a - np.column_stack([np.bincount(cod, a[:, k], minlength=g) / cnt for k in range(a.shape[1])])[cod]


def _unidad_de(ramas: dict, pozo_id) -> int | None:
    """Unidad de navegacion del pozo, o None si no esta medida."""
    r = ramas.get(int(pozo_id))
    if r is None:
        return None
    u = r.get("unidad")
    return int(u) if u is not None else None


def _pad_de(ramas: dict, pozo_id) -> str:
    """Pad del pozo como texto."""
    r = ramas.get(int(pozo_id))
    return "" if r is None else _texto_pad(r.get("pad"))


def _unidad_valida(u) -> bool:
    """Si la unidad esta en la lista valida de 1 a 6."""
    return u is not None and int(u) in UNIDADES_VALIDAS


# ------------------------------------------------------------------ carga de las ramas medidas

def cargar_ramas(con) -> dict[int, dict]:
    """Ramas medidas de mart_trayectoria_pozo con la unidad y el pad de cada pozo.

    Cada entrada es {"lon": array, "lat": array, "unidad": int o None, "pad": str o None}."""
    filas = con.execute("""
        select t.pozo_id, t.rama_lon, t.rama_lat, t.unidad, u.pad_id
        from mart_trayectoria_pozo t
        left join int_pozo_ubicacion u using (pozo_id)
        where t.pozo_id is not null and t.rama_lon is not null and t.rama_lat is not null
        order by t.pozo_id""").fetchall()
    out: dict[int, dict] = {}
    for pid, lon, lat, unidad, pad in filas:
        out[int(pid)] = {"lon": np.asarray(lon, dtype=float), "lat": np.asarray(lat, dtype=float),
                         "unidad": int(unidad) if unidad is not None else None,
                         "pad": _texto_pad(pad) if pad is not None else ""}
    return out


# ------------------------------------------------------------------ muestra de hijos

def muestra(D: dict, ramas: dict) -> tuple[dict, list[tuple]]:
    """Hijos de la muestra (pasos 6 a 8 sobre los de pipeline.hijo) y el conteo de los ocho pasos.

    Devuelve (H, pasos) con H filtrado (todos los vectores alineados) y pasos como
    (paso, descripcion, hijos, pads). Para los pasos 1 a 5 solo se conoce el conteo de
    pipeline.hijo: el conteo de pads de esos pasos queda sin dato (None)."""
    H0 = D["H"]
    pads0 = _texto_pad_array(H0["pad"])
    pasos = [(k, desc, int(cnt), None) for k, (desc, cnt) in enumerate(D["pasos"][:5], start=1)]
    anios = np.asarray(H0["mes_frac"], dtype=int) // 12
    m6 = (anios >= ANIO_MIN) & (anios <= ANIO_MAX)
    m7 = m6 & np.array([int(p) in ramas for p in H0["pozo_id"]], dtype=bool)
    conteo = Counter(pads0[m7])
    pads_ok = {p for p, c in conteo.items() if c >= MIN_HIJOS_PAD}
    m8 = m7 & np.array([p in pads_ok for p in pads0], dtype=bool)
    pasos.append((6, f"primera fractura entre {ANIO_MIN} y {ANIO_MAX}", int(m6.sum()),
                  int(len(np.unique(pads0[m6])))))
    pasos.append((7, "con la rama horizontal medida", int(m7.sum()), int(len(np.unique(pads0[m7])))))
    pasos.append((8, f"pad con al menos {MIN_HIJOS_PAD} hijos con la rama medida", int(m8.sum()),
                  int(len(np.unique(pads0[m8])))))
    H = {k: v[m8] for k, v in H0.items()}
    return H, pasos


# ------------------------------------------------------------------ geometria entre ramas

def _puntos_globales(lon, lat, cos_ref: float) -> np.ndarray:
    """Puntos de una rama en una referencia global en metros (solo para preseleccionar)."""
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    return np.column_stack([lon * M_POR_GRADO * cos_ref, lat * M_POR_GRADO])


def _bbox(p: np.ndarray) -> tuple[float, float, float, float]:
    """Caja envolvente de una polilinea en metros: (xmin, xmax, ymin, ymax)."""
    return (float(p[:, 0].min()), float(p[:, 0].max()), float(p[:, 1].min()), float(p[:, 1].max()))


def _pares_con_distancia(H: dict, Pr: dict, ramas: dict, radio_max: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pares (hijo, expositor) con la distancia entre ramas menor que radio_max, con la distancia.

    Preselecciona con la distancia entre cajas envolventes en una referencia global y calcula
    la distancia minima entre las ramas con trayectorias.distancia_minima, con el origen en la
    boca del hijo. Devuelve (i, j, d) con j indexes de Pr (los pozos con rama medida)."""
    n_h, n_p = len(H["pozo_id"]), len(Pr["pozo_id"])
    if n_h == 0 or n_p == 0:
        return np.zeros(0, dtype=int), np.zeros(0, dtype=int), np.zeros(0)
    lat_ref = float(np.mean(np.asarray(H["lat"], dtype=float)))
    cos_ref = math.cos(math.radians(lat_ref))
    ramas_exp = []
    for pid in Pr["pozo_id"]:
        r = ramas[int(pid)]
        p = _puntos_globales(r["lon"], r["lat"], cos_ref)
        ramas_exp.append(p if len(p) >= 2 else None)
    validos = [k for k, p in enumerate(ramas_exp) if p is not None]
    if not validos:
        return np.zeros(0, dtype=int), np.zeros(0, dtype=int), np.zeros(0)
    ebox = np.array([_bbox(ramas_exp[k]) for k in validos])
    cajas_hijo, locales = [], []
    for i in range(n_h):
        r = ramas.get(int(H["pozo_id"][i]))
        if r is None:
            cajas_hijo.append(None)
            locales.append(None)
            continue
        g = _puntos_globales(r["lon"], r["lat"], cos_ref)
        cajas_hijo.append(_bbox(g) if len(g) >= 2 else None)
        locales.append(a_metros(r["lon"], r["lat"], float(H["lon"][i]), float(H["lat"][i])))
    margen = radio_max * 1.05 + 100.0
    i_out, j_out, d_out = [], [], []
    bloque = 400
    for s in range(0, n_h, bloque):
        idx = [i for i in range(s, min(s + bloque, n_h)) if cajas_hijo[i] is not None]
        if not idx:
            continue
        cbox = np.array([cajas_hijo[i] for i in idx])
        dx = np.maximum(0.0, np.maximum(cbox[:, None, 0] - ebox[None, :, 1], ebox[None, :, 0] - cbox[:, None, 1]))
        dy = np.maximum(0.0, np.maximum(cbox[:, None, 2] - ebox[None, :, 3], ebox[None, :, 2] - cbox[:, None, 3]))
        cerca = np.nonzero(np.sqrt(dx ** 2 + dy ** 2) <= margen)
        for bi, ei in zip(cerca[0], cerca[1]):
            i = idx[bi]
            k = validos[ei]
            if int(H["pozo_id"][i]) == int(Pr["pozo_id"][k]):
                continue                      # el pozo no puede ser expositor de si mismo
            r = ramas[int(Pr["pozo_id"][k])]
            q = a_metros(r["lon"], r["lat"], float(H["lon"][i]), float(H["lat"][i]))
            d = distancia_minima(locales[i], q)
            if d < radio_max:
                i_out.append(i)
                j_out.append(k)
                d_out.append(d)
    return (np.array(i_out, dtype=int), np.array(j_out, dtype=int), np.array(d_out, dtype=float))


def p_con_rama(P: dict, ramas: dict) -> dict:
    """P reducido a los pozos con rama medida (los unicos que pueden ser expositores)."""
    keep = [k for k in range(len(P["pozo_id"])) if int(P["pozo_id"][k]) in ramas]
    return {"pozo_id": P["pozo_id"][keep], "lat": P["lat"][keep], "lon": P["lon"][keep],
            "mes_pp": P["mes_pp"][keep], "meses": [P["meses"][k] for k in keep],
            "cum": [P["cum"][k] for k in keep]}


def pares_rama(H: dict, P: dict, ramas: dict, radio_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Pares (hijo, expositor) con la distancia entre ramas menor que radio_m (estricta).

    j indexes de P restringido a los pozos con rama medida (helper p_con_rama)."""
    Pr = p_con_rama(P, ramas)
    i, j, _ = _pares_con_distancia(H, Pr, ramas, radio_m)
    return i, j


# ------------------------------------------------------------------ exposicion

def exposiciones(H: dict, P: dict, ramas: dict, i: np.ndarray, j: np.ndarray) -> dict:
    """Exposicion de cada hijo (bbl por metro de rama del hijo) para los pares dados.

    E es el petroleo acumulado antes de la fractura del hijo y Ec el de los expositores que
    empiezan despues de la ventana de resultado del hijo. Las variantes E_otros y E_unidad
    dejan fuera, respectivamente, a los expositores del propio pad y a los de otra unidad."""
    n = len(H["pozo_id"])
    rama = np.asarray(H["rama"], dtype=float).copy()
    rama[rama <= 0] = 1.0
    bbl = hj.exposicion_real(H, P, i, j)
    bbl_c = hj.exposicion_control(H, P, i, j)
    unit_hijo = np.array([_unidad_de(ramas, p) for p in H["pozo_id"]], dtype=object)
    unit_exp = np.array([_unidad_de(ramas, p) for p in P["pozo_id"]], dtype=object)
    pad_hijo = np.array([_texto_pad(p) for p in np.asarray(H["pad"], dtype=object)], dtype=object)
    pad_exp = np.array([_pad_de(ramas, p) for p in P["pozo_id"]], dtype=object)
    if len(i):
        otros = pad_exp[j] != pad_hijo[i]
        misma = np.array([_unidad_valida(u) and _unidad_valida(uh) and int(u) == int(uh)
                          for u, uh in zip(unit_exp[j], unit_hijo[i])], dtype=bool)
    else:
        otros = np.zeros(0, dtype=bool)
        misma = np.zeros(0, dtype=bool)
    bbl_otros = hj.exposicion_real(H, P, i[otros], j[otros])
    bbl_c_otros = hj.exposicion_control(H, P, i[otros], j[otros])
    bbl_unidad = hj.exposicion_real(H, P, i[misma], j[misma])
    bbl_c_unidad = hj.exposicion_control(H, P, i[misma], j[misma])
    E, Ec = bbl / rama, bbl_c / rama
    muf = np.where(bbl > 0, bbl_unidad / np.where(bbl > 0, bbl, 1.0), 0.0)
    return {"E": E, "Ec": Ec, "E_otros": bbl_otros / rama, "Ec_otros": bbl_c_otros / rama,
            "E_unidad": bbl_unidad / rama, "Ec_unidad": bbl_c_unidad / rama,
            "misma_unidad_frac": muf,
            "bbl": bbl, "bbl_control": bbl_c, "n": np.array([n])}


# ------------------------------------------------------------------ diseno y modelo

def _meses_desde_frac_pad(H: dict) -> np.ndarray:
    """Meses desde la primera fractura del pad (el mes del hijo menos el menor mes del pad)."""
    mes = np.asarray(H["mes_frac"], dtype=int)
    pad = _texto_pad_array(H["pad"])
    mins: dict[str, int] = {}
    for m, p in zip(mes, pad):
        if p not in mins or m < mins[p]:
            mins[p] = int(m)
    return np.array([float(m - mins[p]) for m, p in zip(mes, pad)])


def diseno(H: dict, ramas: dict, extra: dict | None = None) -> tuple[np.ndarray, list[str]]:
    """Matriz de controles C y nombres de las columnas.

    Trae la rama horizontal del hijo, los indicadores de las unidades 1 a 6 presentes en la
    muestra (menos la mas frecuente) mas el indicador "sin unidad" si hace falta, la fraccion
    de la exposicion que viene de la misma unidad (misma_unidad_frac) y los meses desde la
    primera fractura del pad. extra puede traer "misma_unidad_frac" y otras columnas."""
    extra = dict(extra or {})
    n = len(H["pozo_id"])
    cols: list[np.ndarray] = [np.asarray(H["rama"], dtype=float)]
    names = ["rama_horizontal_m"]
    unidades = [_unidad_de(ramas, p) for p in H["pozo_id"]]
    validas = [u if _unidad_valida(u) else None for u in unidades]
    conteo = Counter(u for u in validas if u is not None)
    if conteo:
        tope = max(conteo.values())
        mas_frecuente = min(u for u, c in conteo.items() if c == tope)
        for u in UNIDADES_VALIDAS:
            if u in conteo and u != mas_frecuente:
                cols.append(np.array([1.0 if v == u else 0.0 for v in validas]))
                names.append(f"unidad_{u}")
    if any(v is None for v in validas):
        cols.append(np.array([1.0 if v is None else 0.0 for v in validas]))
        names.append("sin_unidad")
    muf = extra.pop("misma_unidad_frac", None)
    cols.append(np.zeros(n) if muf is None else np.asarray(muf, dtype=float))
    names.append("misma_unidad_frac")
    cols.append(_meses_desde_frac_pad(H))
    names.append("meses_desde_primera_fractura_pad")
    for nombre, valores in extra.items():
        cols.append(np.asarray(valores, dtype=float))
        names.append(nombre)
    return np.column_stack(cols), names


def _X(exposicion: np.ndarray, C: np.ndarray, keep: list[int]) -> np.ndarray:
    """Matriz del modelo: la exposicion en unidades de 100 bbl por metro y los controles."""
    cols = [np.asarray(exposicion, dtype=float) / ESCALA_EXPOSICION]
    cols.extend(C[:, k] for k in keep)
    return np.column_stack(cols)


def _columnas_variantes(Xc: np.ndarray) -> list[int]:
    """Columnas con variacion dentro del pad: la 0 (la exposicion) siempre entra."""
    var = (Xc ** 2).sum(0)
    return [0] + [k for k in range(1, Xc.shape[1]) if var[k] > 0]


def ajuste_pad(y: np.ndarray, X: np.ndarray, pad) -> dict:
    """Minimos cuadrados sobre las desviaciones dentro del pad.

    La columna 0 de X es la exposicion (en 100 bbl por metro) y las otras son controles.
    Las columnas sin variacion dentro del pad se descartan; si la exposicion no varia
    dentro de los pads, la pendiente no esta definida y sale nan."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    cod, g = _codigos(pad)
    yc = _centrar(y, cod, g)
    Xc = _centrar(X, cod, g)
    n = len(y)
    keep = _columnas_variantes(Xc)
    if (Xc[:, 0] ** 2).sum() <= 0:
        return {"beta": float("nan"), "n": n, "pads": int(g)}
    Z = Xc[:, keep]
    escala = np.sqrt((Z ** 2).sum(0) / max(n, 1))
    escala[escala == 0] = 1.0
    theta = np.linalg.lstsq(Z / escala, yc, rcond=None)[0]
    beta = theta / escala
    return {"beta": float(beta[0]), "n": n, "pads": int(g)}


def bootstrap_pads(y: np.ndarray, Xs: dict[str, np.ndarray], pad, reps: int, semilla: int) -> dict[str, np.ndarray]:
    """Bootstrap por pads: para cada modelo, la pendiente de la columna 0 en cada repeticion.

    Se remuestrean los pads con reemplazo y cada copia cuenta como un pad distinto. Las
    repeticiones (los mismos sorteos) sirven para todos los modelos del diccionario."""
    y = np.asarray(y, dtype=float)
    cod, g = _codigos(pad)
    rng = np.random.default_rng(semilla)
    draws = rng.integers(0, g, (reps, g))
    yc = _centrar(y, cod, g)
    prep: dict[str, tuple] = {}
    for nombre, X in Xs.items():
        X = np.asarray(X, dtype=float)
        Xc = _centrar(X, cod, g)
        keep = _columnas_variantes(Xc)
        k = len(keep)
        A = np.zeros((g, k, k))
        b = np.zeros((g, k))
        for gi in range(g):
            m = cod == gi
            Z = Xc[m][:, keep]
            A[gi] = Z.T @ Z
            b[gi] = Z.T @ yc[m]
        prep[nombre] = (A, b, k, float((Xc[:, 0] ** 2).sum()))
    out = {nombre: np.full(reps, np.nan) for nombre in Xs}
    bloque = 250
    for ini in range(0, reps, bloque):
        fin = min(ini + bloque, reps)
        cnt = np.zeros((fin - ini, g))
        for r in range(ini, fin):
            cnt[r - ini] = np.bincount(draws[r], minlength=g)
        for nombre, (A, b, k, var0) in prep.items():
            if var0 <= 0:
                continue
            XtX = (A.reshape(g, -1).T @ cnt.T).T.reshape(fin - ini, k, k)
            Xty = (b.T @ cnt.T).T
            sol = np.linalg.pinv(XtX) @ Xty[..., None]
            out[nombre][ini:fin] = sol[:, 0, 0]
    return out


def ic95(boot: np.ndarray) -> tuple[float, float]:
    """IC 95% por percentiles 2,5 y 97,5 del bootstrap."""
    b = np.asarray(boot, dtype=float)
    if b.size == 0 or not np.isfinite(b).any():
        return (float("nan"), float("nan"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (float(np.nanpercentile(b, 2.5)), float(np.nanpercentile(b, 97.5)))


# ------------------------------------------------------------------ veredicto

def nulo(lo: float, hi: float) -> bool:
    """Si el intervalo incluye el cero."""
    return bool(lo <= 0 <= hi)


def veredicto(beta: float, lo: float, hi: float, lo_c: float, hi_c: float,
              virgen: float, pads_informativos: int) -> str:
    """Veredicto de la regla, en el orden del encabezado.

    "sin muestra" si no hay pads informativos suficientes o si algo no se puede calcular;
    "sostiene degradación" si el IC de beta esta bajo cero y el del control incluye cero;
    "no se ve degradación" si los dos intervalos incluyen cero y beta esta dentro del
    umbral; "ubicación" si el control negativo excluye el cero; "no firme" en el resto."""
    entradas = [beta, lo, hi, lo_c, hi_c, virgen]
    if (pads_informativos < MIN_PADS_INFORMATIVOS or not all(np.isfinite(v) for v in entradas)
            or virgen <= 0):
        return VEREDICTOS[4]
    if hi < 0 and nulo(lo_c, hi_c):
        return VEREDICTOS[0]
    if (nulo(lo, hi) and nulo(lo_c, hi_c) and lo >= -UMBRAL_SIN_DEGRADACION * virgen
            and hi <= UMBRAL_SIN_DEGRADACION * virgen):
        return VEREDICTOS[1]
    if not nulo(lo_c, hi_c):
        return VEREDICTOS[2]
    return VEREDICTOS[3]


def pads_informativos(E: np.ndarray, pad) -> int:
    """Pads con dispersion de E de al menos DISPERSION_MIN_BBL_M entre sus hijos de la muestra."""
    E = np.asarray(E, dtype=float)
    cod, g = _codigos(pad)
    n = 0
    for gi in range(g):
        v = E[cod == gi]
        if len(v) and (float(v.max()) - float(v.min())) >= DISPERSION_MIN_BBL_M:
            n += 1
    return int(n)


def virgin(y: np.ndarray, E: np.ndarray) -> tuple[float, int, str]:
    """Rendimiento virgen: mediana de y entre los hijos con E igual a 0, o de toda la muestra.

    Devuelve (V, cantidad de hijos con E igual a 0, "virgen" o "toda la muestra")."""
    y = np.asarray(y, dtype=float)
    E = np.asarray(E, dtype=float)
    cero = E == 0
    n = int(cero.sum())
    if n >= MIN_VIRGENES_REF:
        return float(np.median(y[cero])), n, "virgen"
    return float(np.median(y)) if len(y) else float("nan"), n, "toda la muestra"


def cota(lo: float, V: float, expo_pos_mediana: float) -> dict:
    """Cota superior de la perdida compatible con el dato: max(0, -lo)."""
    if not np.isfinite(lo):
        nan = float("nan")
        return {"cota_bbl_m": nan, "cota_pct": nan, "cota_a_mediana_bbl_m": nan}
    perdida = max(0.0, -float(lo))
    pct = 100.0 * perdida / V if V else float("nan")
    return {"cota_bbl_m": perdida, "cota_pct": pct,
            "cota_a_mediana_bbl_m": perdida * float(expo_pos_mediana) / ESCALA_EXPOSICION}


# ------------------------------------------------------------------ calculo

def calcular(D: dict, ramas: dict) -> dict:
    """Las cinco tablas del lado del hijo dentro del pad."""
    H, pasos = muestra(D, ramas)
    y = np.asarray(H["y_bbl"], dtype=float) / np.asarray(H["rama"], dtype=float)
    pad = _texto_pad_array(H["pad"])
    n_pads = int(len(np.unique(pad)))
    if len(H["pozo_id"]) == 0:
        return {"mart_hijo_pad_muestra": [(p[0], p[1], p[2], p[3]) for p in pasos],
                "mart_hijo_pad_coef": [], "mart_hijo_pad_resumen": [],
                "mart_hijo_pad_equilibrio": [], "mart_hijo_pad_anio": []}
    Pr = p_con_rama(D["P"], ramas)
    radio_max = max(RADIO_RAMA_M, max(RADIOS_DESCRIPTIVOS_M))
    i_max, j_max, d_max = _pares_con_distancia(H, Pr, ramas, radio_max)
    pares = {}
    for nombre, radio in (("300", RADIOS_DESCRIPTIVOS_M[0]), ("600", RADIO_RAMA_M),
                           ("1000", RADIOS_DESCRIPTIVOS_M[1])):
        m = d_max < radio
        pares[nombre] = (i_max[m], j_max[m])
    expo = {k: exposiciones(H, Pr, ramas, pares[k][0], pares[k][1]) for k in pares}
    principal = expo["600"]
    E, Ec = principal["E"], principal["Ec"]
    # el control negativo es el mismo modelo con Ec en lugar de E: los controles C (incluida misma_unidad_frac, que sale de E)
    # son los mismos, como dice la regla
    C_real, nombres = diseno(H, ramas, {"misma_unidad_frac": principal["misma_unidad_frac"]})
    pos = {n: k for k, n in enumerate(nombres)}
    base = [pos["rama_horizontal_m"]] + [k for k, n in enumerate(nombres)
                                         if n.startswith("unidad_") or n == "sin_unidad"]
    keep_principal = base + [pos["misma_unidad_frac"]]
    keep_sin_unidad = base
    keep_tiempo = keep_principal + [pos["meses_desde_primera_fractura_pad"]]
    modelos = {
        "principal": (E, Ec, keep_principal),
        "sin_controles": (E, Ec, []),
        "radio_300": (expo["300"]["E"], expo["300"]["Ec"], keep_principal),
        "radio_1000": (expo["1000"]["E"], expo["1000"]["Ec"], keep_principal),
        "otros_pads": (principal["E_otros"], principal["Ec_otros"], keep_principal),
        "misma_unidad": (principal["E_unidad"], principal["Ec_unidad"], keep_sin_unidad),
        "con_tiempo_pad": (E, Ec, keep_tiempo),
    }
    Xs: dict[str, np.ndarray] = {}
    for nombre, (e, ec, keep) in modelos.items():
        Xs[f"{nombre}|real"] = _X(e, C_real, keep)
        Xs[f"{nombre}|control"] = _X(ec, C_real, keep)
    boot = bootstrap_pads(y, Xs, pad, REPS_PAD, SEMILLA_HIJO_PAD)
    beta_p = ajuste_pad(y, Xs["principal|real"], pad)["beta"]
    lo_p, hi_p = ic95(boot["principal|real"])
    lo_c, hi_c = ic95(boot["principal|control"])
    V, n_virgenes, ref = virgin(y, E)
    pads_inf = pads_informativos(E, pad)
    ver = veredicto(beta_p, lo_p, hi_p, lo_c, hi_c, V, pads_inf)
    filas_coef = []
    for nombre in ["principal"] + list(MODELOS_DESCRIPTIVOS):
        e_real, e_ctrl, _ = modelos[nombre]
        V_m, _, _ = virgin(y, e_real)
        for tipo in ("real", "control"):
            pads_m = pads_informativos(e_real if tipo == "real" else e_ctrl, pad)
            clave = f"{nombre}|{tipo}"
            aj = ajuste_pad(y, Xs[clave], pad)
            lo, hi = ic95(boot[clave])
            filas_coef.append((nombre, tipo, TERMINO, aj["beta"], lo, hi, aj["n"], aj["pads"], pads_m,
                               100.0 * aj["beta"] / V_m if V_m else float("nan"),
                               100.0 * lo / V_m if V_m else float("nan"),
                               100.0 * hi / V_m if V_m else float("nan"),
                               V_m, ver if (nombre == "principal" and tipo == "real") else None))
    expo_pos = E[E > 0]
    expo_pos_mediana = float(np.median(expo_pos)) if len(expo_pos) else 0.0
    c = cota(lo_p, V, expo_pos_mediana)
    cod, g = _codigos(pad)
    dispersiones = []
    pads_info = set()
    for gi in range(g):
        v = E[cod == gi]
        if len(v) and (float(v.max()) - float(v.min())) >= DISPERSION_MIN_BBL_M:
            dispersiones.append(float(v.max() - v.min()))
            pads_info.add(str(pad[cod == gi][0]))
    resumen = [
        ("virgen_mediana_bbl_m", float(V)),
        ("virgenes_n", float(n_virgenes)),
        ("virgen_referencia_toda_muestra", 1.0 if ref == "toda la muestra" else 0.0),
        ("hijos", float(len(H["pozo_id"]))),
        ("pads", float(n_pads)),
        ("pads_informativos", float(pads_inf)),
        ("dispersion_mediana_bbl_m", float(np.median(dispersiones)) if dispersiones else float("nan")),
        ("parte_E_cero", float((E == 0).mean()) if len(E) else float("nan")),
        ("expo_positiva_mediana_bbl_m", expo_pos_mediana),
        ("cota_bbl_m", c["cota_bbl_m"]),
        ("cota_pct", c["cota_pct"]),
        ("cota_a_mediana_bbl_m", c["cota_a_mediana_bbl_m"]),
        ("reps", float(REPS_PAD)),
        ("semilla", float(SEMILLA_HIJO_PAD)),
    ]
    variables = {"rama_horizontal_m": np.asarray(H["rama"], dtype=float),
                 "etapas": np.asarray(H["etapas"], dtype=float),
                 "arena_tn_por_m": np.asarray(H["arena"], dtype=float) / np.asarray(H["rama"], dtype=float),
                 "meses_desde_primera_fractura_pad": C_real[:, pos["meses_desde_primera_fractura_pad"]]}
    filas_eq = []
    Xeq = (E / ESCALA_EXPOSICION).reshape(-1, 1)
    for nombre, yvar in variables.items():
        aj = ajuste_pad(yvar, Xeq, pad)
        b = bootstrap_pads(yvar, {"v": Xeq}, pad, REPS_PAD, SEMILLA_HIJO_PAD)
        lo, hi = ic95(b["v"])
        filas_eq.append((nombre, aj["beta"], lo, hi, aj["n"], aj["pads"]))
    anios = np.asarray(H["mes_frac"], dtype=int) // 12
    filas_anio = []
    for a in sorted(set(anios.tolist())):
        m = anios == a
        filas_anio.append((int(a), int(m.sum()), int(len(np.unique(pad[m]))),
                           int(sum(1 for p in pad[m] if str(p) in pads_info))))
    return {"mart_hijo_pad_muestra": [(int(p[0]), str(p[1]), int(p[2]), None if p[3] is None else int(p[3])) for p in pasos],
            "mart_hijo_pad_coef": filas_coef,
            "mart_hijo_pad_resumen": resumen,
            "mart_hijo_pad_equilibrio": filas_eq,
            "mart_hijo_pad_anio": filas_anio}


# ------------------------------------------------------------------ pagina

MODELOS_TXT = {
    "principal": "Principal (decide el veredicto)",
    "sin_controles": "Sin controles, solo efectos fijos de pad",
    "radio_300": "Ramas a menos de 300 m",
    "radio_1000": "Ramas a menos de 1.000 m",
    "otros_pads": "Solo exposición de otros pads",
    "misma_unidad": "Solo exposición de la misma unidad",
    "con_tiempo_pad": "Con los meses desde la primera fractura del pad",
}
EQUILIBRIO_TXT = [("rama_horizontal_m", "Rama horizontal (m)", 1), ("etapas", "Etapas", 2),
                  ("arena_tn_por_m", "Arena por metro (tn/m)", 3),
                  ("meses_desde_primera_fractura_pad", "Meses desde la primera fractura del pad", 2)]


def cobertura_rama(con) -> tuple[float, float, float, float]:
    """Parte de los hijos horizontales con la rama medida: (minimo, maximo) de 2016 a 2023 y la de 2024 y la de 2025, en %."""
    f = {a: (m, h) for a, h, m in con.execute(
        "select anio, horizontales, horizontales_medidos from mart_trayectoria_cobertura where nivel = 'hijo'").fetchall()}
    de = [100.0 * f[a][0] / f[a][1] for a in range(ANIO_MIN, ANIO_MAX + 1) if a in f and f[a][1]]
    return min(de), max(de), 100.0 * f[2024][0] / f[2024][1], 100.0 * f[2025][0] / f[2025][1]


def _texto_veredicto(v: str, b: float, lo: float, hi: float, lo_c: float, hi_c: float, V: float) -> str:
    if v == "no se ve degradación":
        return ("Dentro del pad, el hijo que se fracturó con más petróleo ya producido por ramas a menos de 600 m no se ve que "
                "rinda menos que el que se fracturó con menos: el IC de la pendiente incluye cero y está dentro de 5% del rendimiento virgen "
                "por cada 100 bbl por metro de exposición, y el control negativo también incluye cero. Es lo que se ve con esta "
                "medición, y no es que no haya degradación (ver Límites).")
    if v == "sostiene degradación":
        return ("Dentro del pad, el hijo que se fracturó con más petróleo ya producido por ramas a menos de 600 m rinde menos, con "
                "un IC que queda por debajo de cero, y el control negativo incluye cero. Es una asociación dentro del pad, no una "
                "afirmación causal.")
    if v == "ubicación":
        return ("El IC del control negativo excluye cero: la exposición de pozos que empezaron después de la ventana del hijo también "
                "se asocia con su rendimiento dentro del pad, así que la diferencia no se lee como depleción sino como orden o "
                "posición dentro del pad.")
    if v == "sin muestra":
        return "No hay pads con dispersión de exposición suficientes, o la estimación no se puede calcular, y no se da veredicto."
    return ("La regla no permite concluir en ningún sentido: el IC de la pendiente y el del control negativo no cumplen a la vez las "
            "condiciones de ningún veredicto.")


def pagina_hijo_pad(con) -> str:
    cf = {(r[0], r[1]): r for r in con.execute("select * from mart_hijo_pad_coef").fetchall()}
    R = dict(con.execute("select clave, valor from mart_hijo_pad_resumen").fetchall())
    eq = {r[0]: r for r in con.execute("select * from mart_hijo_pad_equilibrio").fetchall()}
    mu = con.execute("select * from mart_hijo_pad_muestra order by paso").fetchall()
    an = con.execute("select * from mart_hijo_pad_anio order by anio").fetchall()
    p, c = cf[("principal", "real")], cf[("principal", "control")]
    v = p[13]
    V = R["virgen_mediana_bbl_m"]
    cmin, cmax, c24, c25 = cobertura_rama(con)
    mu_c = cf[("misma_unidad", "control")]
    cota_txt = ("no se puede calcular: el IC no tiene extremo bajo finito" if not np.isfinite(R["cota_bbl_m"]) else
                "la cota superior es cero: todo el IC está por encima de cero" if R["cota_bbl_m"] == 0.0 else
                f"{_g(R['cota_bbl_m'], 1)} bbl por metro de rama por cada 100 bbl por metro de exposición, o "
                f"{_g(R['cota_pct'], 1)}% del rendimiento virgen")
    L = ["# El hijo contra sus hermanos del mismo pad", "",
         "Página generada por `pipeline/hijo_pad.py`. Pregunta si, dentro de un mismo pad, el hijo que se fracturó cuando ya "
         "producían pozos cuya rama pasa a menos de 600 m de la suya rinde menos petróleo por metro de rama en sus primeros 12 "
         "meses que su hermano fracturado con menos exposición. Compara hijos del mismo pad, así que el área, el operador, la "
         "época y casi todo el diseño de la terminación quedan fijos. Complementa [Hijos cerca de pozos depletados](hijo.md) y "
         "[Hijos dentro de celdas de 2 km](hijo_celdas.md), que miden la distancia en superficie y dieron no firme. La regla se fijó "
         "antes de correr: está en el encabezado de `pipeline/hijo_pad.py`, en el commit que solo trae las constantes.", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada: **{v}**. {_texto_veredicto(v, p[3], p[4], p[5], c[4], c[5], V)}", "",
         (f"- Rendimiento de referencia a 12 meses: mediana de {_g(V, 1)} bbl por metro de rama de toda la muestra, porque hay "
          f"solo {_g(R['virgenes_n'])} hijos sin exposición, menos de {MIN_VIRGENES_REF}."
          if R.get("virgen_referencia_toda_muestra") else
          f"- Rendimiento de los hijos sin exposición a 12 meses: mediana de {_g(V, 1)} bbl por metro de rama, sobre "
          f"{_g(R['virgenes_n'])} hijos."),
         f"- Pendiente dentro del pad: {_g(p[3], 1)} bbl por metro de rama por cada 100 bbl por metro de exposición (IC 95%: "
         f"{_g(p[4], 1)} a {_g(p[5], 1)}), o sea {_g(p[9], 1)}% del rendimiento virgen (IC 95%: {_g(p[10], 1)}% a "
         f"{_g(p[11], 1)}%), sobre {_g(p[6])} hijos de {_g(p[7])} pads.",
         f"- Control negativo, la misma pendiente con la exposición de pozos posteriores a la ventana del hijo: {_g(c[3], 1)} bbl "
         f"por metro de rama (IC 95%: {_g(c[4], 1)} a {_g(c[5], 1)}). "
         + ("Incluye cero." if c[4] <= 0 <= c[5] else "Excluye cero."),
         f"- Cota superior de la pérdida (el extremo bajo del IC, no una estimación): {cota_txt}; a la mediana de las exposiciones "
         f"positivas, {_g(R['expo_positiva_mediana_bbl_m'])} bbl por metro, son {_g(R['cota_a_mediana_bbl_m'], 1)} bbl por metro de rama.",
         f"- Pads que informan: {_g(R['pads_informativos'])} de {_g(R['pads'])} tienen una dispersión de la exposición de al menos 50 "
         f"bbl por metro entre sus hijos (mediana de la dispersión: {_g(R['dispersion_mediana_bbl_m'])} bbl por metro); "
         f"{_g(100 * R['parte_E_cero'])}% de los hijos no tienen exposición.",
         "- Se publican todos los modelos calculados; el veredicto sale solo del modelo principal y su control negativo.", "",
         "## Muestra y cobertura", "",
         f"Las ramas medidas cubren entre {_g(cmin)}% y {_g(cmax)}% de los hijos horizontales fracturados de {ANIO_MIN} a {ANIO_MAX}, "
         f"pero solo {_g(c24)}% de los de 2024 y {_g(c25)}% de los de 2025: la muestra es toda de {ANIO_MIN} a {ANIO_MAX} y no "
         "habla de los hijos recientes. La exposición cuenta solo pozos con la rama medida, así que es una cota inferior de la "
         "exposición verdadera.", ""]
    for paso, d, n, pads in mu:
        L.append(f"- Paso {paso}, {d}: {_g(n)} hijos" + (f" en {_g(pads)} pads." if pads is not None else "."))
    L += ["", "| Año de la primera fractura | Hijos | Pads | Hijos en pads con dispersión |", "| --- | ---: | ---: | ---: |"]
    for a, h, pd, hi in an:
        L.append(f"| {a} | {_g(h)} | {_g(pd)} | {_g(hi)} |")
    L += ["", "## Regla fijada antes de correr", "",
          "La unidad es el hijo con 12 meses publicados, con rama, etapas, arena y fecha de primera fractura, cuyo primer petróleo "
          "llega entre 0 y 12 meses después de la fractura, fracturado de 2016 a 2023, con la rama medida y en un pad con al menos "
          "2 hijos así. El resultado es el petróleo de 12 meses por metro de rama. La exposición es el petróleo acumulado, hasta el "
          "mes anterior a la fractura del hijo, de los pozos de shale con la rama medida cuya rama pasa a menos de 600 m de la "
          "suya (distancia mínima entre ramas), por metro de rama del hijo.", "",
          "El modelo es de mínimos cuadrados con efectos fijos de pad, la rama del hijo, la unidad donde navega y la parte de la "
          "exposición que viene de la misma unidad. El IC 95% es de percentiles de un bootstrap por pads, con 2.000 repeticiones y "
          "la misma semilla para el modelo y su control negativo. El control negativo es el mismo modelo con la exposición de los "
          "pozos cuyo primer petróleo es posterior a la ventana de 12 meses del hijo: no pudieron depletarlo ni interferirlo. El "
          "rendimiento virgen es la mediana del resultado entre los hijos sin exposición.", "",
          "- Sostiene degradación: el IC de la pendiente queda por debajo de cero y el del control negativo incluye cero.",
          "- No se ve degradación: los dos IC incluyen cero y los extremos del IC de la pendiente están dentro de 5% del rendimiento "
          "virgen por cada 100 bbl por metro de exposición.",
          "- Ubicación: el IC del control negativo excluye cero.",
          "- No firme: cualquier otro caso. Sin muestra: menos de 100 pads con dispersión de exposición de al menos 50 bbl por metro, o "
          "una estimación que no se puede calcular.", "",
          "## Coeficientes", "",
          "Pendiente dentro del pad en bbl por metro de rama por cada 100 bbl por metro de exposición. Cada modelo tiene su control "
          "negativo con la exposición de pozos posteriores. El porcentaje es contra el rendimiento virgen del modelo. Solo el "
          "modelo principal tiene veredicto.", "",
          "| Modelo | Exposición | Pendiente | IC 95% | % del virgen | Hijos | Pads | Pads con dispersión |",
          "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |"]
    for (modelo, tipo), r in cf.items():
        L.append(f"| {MODELOS_TXT[modelo]} | {'real' if tipo == 'real' else 'control negativo'} | {_g(r[3], 2)} | "
                 f"{_g(r[4], 2)} a {_g(r[5], 2)} | {_g(r[9], 1)}% | {_g(r[6])} | {_g(r[7])} | {_g(r[8])} |")
    L += ["", "## Equilibrio dentro del pad, antes del resultado", "",
          "Pendiente dentro del pad de cada variable de diseño sobre la exposición (por cada 100 bbl por metro), con el mismo "
          "bootstrap. Dice cuánto de la exposición dentro del pad es el orden de las fracturas o el diseño.", "",
          "| Variable | Pendiente | IC 95% |", "| --- | ---: | --- |"]
    for nombre, rot, dec in EQUILIBRIO_TXT:
        r = eq[nombre]
        L.append(f"| {rot} | {_g(r[1], dec)} | {_g(r[2], dec)} a {_g(r[3], dec)} |")
    varia = [rot for nombre, rot, _ in EQUILIBRIO_TXT if eq[nombre][2] > 0 or eq[nombre][3] < 0]
    L += ["", ("Variables que cambian con la exposición dentro del pad, con IC que excluye cero: " + ", ".join(varia) + "."
               if varia else "Ninguna variable de diseño cambia con la exposición dentro del pad, con IC que excluya cero."), ""]
    L += ["## Límites", "",
          "- La exposición cuenta solo ramas medidas: es una cota inferior de la exposición verdadera. Con un error de medición de ese "
          "tipo la pendiente por barril medido se atenúa hacia cero y la cota superior de la pérdida queda corta. Por eso "
          "\"no se ve degradación\" no es \"no hay degradación\".",
          "- El control negativo es menos potente que la exposición real: cuenta pozos posteriores a la ventana del hijo, muchos de "
          "2024 a 2026, y la fuente cubre pocos de 2024 y 2025. Un IC del control que incluye cero informa menos que el de la "
          "exposición real, y que el control del modelo principal incluya cero no lo vuelve una prueba fuerte."
          + (" En el modelo de la misma unidad el control excluye cero, y ese modelo no se lee como nulo." if mu_c[4] > 0 or mu_c[5] < 0 else ""),
          "- Dentro del pad, la exposición es sobre todo el orden de las fracturas y la posición de cada rama, no solo la depleción: "
          "los efectos fijos de pad no quitan una tendencia dentro del pad. El equilibrio de arriba muestra cuánto cambia el "
          "diseño con la exposición, y el modelo con los meses desde la primera fractura del pad mira el orden; ninguno lo elimina. Por lo mismo, el control "
          "negativo se mueve en sentido contrario a la exposición real (el hijo fracturado primero tiene la menor exposición real y "
          "la mayor de control, por los hermanos que vienen después): no es una prueba independiente del orden.",
          "- El resultado es por metro de rama de la fractura, y la exposición también: los dos comparten el denominador, así que "
          "un hijo de rama corta tiene a la vez un rendimiento y una exposición por metro más altos.",
          "- Hijos y expositores del mismo pad comparten la roca, pero no la profundidad: la unidad es un control, no la zona de "
          "aterrizaje.",
          "- La distancia entre ramas es la mínima, no el espaciamiento a lo largo de la rama.",
          "- Es una asociación dentro del pad con controles de diseño, no una afirmación causal.",
          "- Los intervalos no tienen ajuste por comparaciones múltiples: se publican todos los modelos calculados, favorables o no.",
          ""]
    return "\n".join(L)


# ------------------------------------------------------------------ principal

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    D = hj.cargar(con)
    ramas = cargar_ramas(con)
    R = calcular(D, ramas)
    _escribir(con, "mart_hijo_pad_muestra", COLS_MUESTRA, R["mart_hijo_pad_muestra"])
    _escribir(con, "mart_hijo_pad_coef", COLS_COEF, R["mart_hijo_pad_coef"])
    _escribir(con, "mart_hijo_pad_resumen", COLS_RESUMEN, R["mart_hijo_pad_resumen"])
    _escribir(con, "mart_hijo_pad_equilibrio", COLS_EQUILIBRIO, R["mart_hijo_pad_equilibrio"])
    _escribir(con, "mart_hijo_pad_anio", COLS_ANIO, R["mart_hijo_pad_anio"])
    for clave, valor in R["mart_hijo_pad_resumen"]:
        print(f"[hijo_pad] {clave:<34} {valor:12.4f}")
    for r in R["mart_hijo_pad_coef"]:
        if r[0] == "principal":
            print(f"[hijo_pad] {r[0]:<8} {r[1]:<8} coef={r[3]:8.3f} IC {r[4]:8.3f} a {r[5]:8.3f} "
                  f"n={r[6]:>5} pads={r[7]:>5} veredicto={r[13]}")
    con.close()


if __name__ == "__main__":
    main()
