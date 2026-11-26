"""Bootstrap por bloques espaciales de los resultados principales: la brecha del mes 1, la pendiente de sincronia y las partes de la descomposicion.

Se corre despues de pipeline.sincronia:  uv run python -m pipeline.bloques

REGLA FIJADA ANTES DE CORRER (2026-11-15, antes de calcular ninguna cifra de bloques; no se cambia despues de ver resultados).
Fuente: fase 4 del proyecto, pivote P4 (bloques espaciales).

Pregunta: los intervalos del estudio remuestrean pads hijo como si fueran independientes. Dos pads vecinos comparten geologia,
programa de fractura y pozos padres, asi que su ruido puede estar correlacionado en el espacio y el intervalo por pads quedar
angosto. Si en vez de pads se remuestrean bloques de una grilla espacial, el intervalo mide esa dependencia.

Bloques:
  * Coordenada del pad hijo = promedio de lat y lon de todos los pozos del pad (`int_pozo_ubicacion`, por `pad_id`).
  * Proyeccion equirectangular alrededor de (LAT0, LON0) = (-38,0, -69,0): x = 111,32 * (lon - LON0) * cos(radianes(LAT0)) km,
    y = 111,32 * (lat - LAT0) km (los mismos 111,32 km por grado que usa el resto del pipeline).
  * Bloque = (piso(x / tam), piso(y / tam)) con tam = 2 km y con tam = 5 km: dos grillas, cada una con su intervalo.
  * Cada evento hereda el bloque de su pad hijo (el del hijo mas cercano, el mismo que fija su `clave` en el estudio).
  * Variante de pad dentro de bloque (remuestrear bloques y luego pads): NO se hace. No es trivial y no entra en esta pasada.

Intervalos: bootstrap de percentiles 95% (2,5 y 97,5), REPS_BOOT repeticiones, remuestreando bloques completos con reemplazo
(los eventos de un bloque se mueven juntos). Mismo estimador, mismos eventos y misma semilla por k que el intervalo por pads
de la pagina original (placebo: SEMILLA_PLACEBO + 100 + posicion de k en KS_PRE; sincronia: igual; descomposicion: igual), para
que la unica diferencia sea la unidad de remuestreo. La estimacion puntual no cambia.

Metricas (15 filas en mart_bloques):
  (a) Brecha cercano menos control (medianas del indice, cercanos a menos de 1 km, controles a 2 a 5 km):
      * brecha_mes1_base_original: k = 1 con la base de los meses -3 a -1 (el resultado principal, 23).
      * brecha_mes1_descontada: la brecha del mes 1 menos la del mes -1, base de los meses -6 a -4, sobre los mismos eventos y
        las mismas remuestras (el 19 del resultado principal). Es el otro extremo del rango "19 a 23".
      * brecha_base_limpia: serie k = -3..3 con la base de los meses -6 a -4 (7 filas).
  (b) sincronia_pendiente: pendiente del cercano por f0 en k = 0 y k = -1 (pipeline.sincronia, base limpia, indice acotado).
  (c) parte_dias y parte_tasa: parte de los dias y del caudal por dia en la brecha del logaritmo del volumen, al mes 1, para las
      variantes con_cerrados y sin_cerrados de pipeline.descomposicion. El IC de parte_tasa es el complemento exacto del de
      parte_dias (parte_tasa = 1 - parte_dias en cada remuestra).

Reglas de decision (se publican todos los resultados, favorables o no):
  R1. El IC de la brecha del mes 1 del README y del caso de estudio pasa a ser el IC por bloques de 5 km si tiene al menos 30
      bloques. Si el limite superior de ese IC (brecha_mes1_base_original, k = 1) queda por encima de -0,10 (-10 puntos de
      indice: cruza -10), el rango titular "19 a 23" se reescribe con los IC por bloques de 5 km de sus dos extremos: desde el
      limite superior mas cercano a cero de los dos IC (brecha_mes1_descontada y brecha_mes1_base_original) hasta el limite
      inferior mas lejano de cero de los dos, en puntos y redondeado al entero, y se actualizan todos los textos y claims que
      dependen de ese rango. Si no cruza -10, el rango "19 a 23" queda y solo cambia el IC publicado. Con menos de 30 bloques de
      5 km el IC de la pagina original no cambia y se informa el recuento.
  R2. El veredicto de la pendiente de sincronia ("sostiene") se vuelve a derivar con el IC por bloques de 5 km, con la misma
      regla de pipeline.sincronia: limite superior del IC de k = 0 menor que -0,02 por unidad de f0, y la pendiente de k = -1
      no puede tener IC que excluya cero con signo negativo (con el IC por bloques de 5 km), y el minimo de eventos por grupo.
      Si el limite superior no es menor que -0,02, el veredicto pasa a "no firme" (o "plana" u "opuesta" si el IC incluye cero o
      es positivo, como en sincronia) y el README, la wiki, el libro y el caso de estudio lo dicen.
  R3. Una linea cuenta todas las pruebas estadisticas del proyecto: las hipotesis del libro (6 mas las 2 nuevas de esta pagina,
      brecha_mes1_bloques y sincronia_mes0_bloques), 13 subconjuntos de robustez, 141 intervalos de la descomposicion, mas
      las 13 filas de IC por bloques que no son esas hipotesis (15 filas menos 2). Total: 8 + 13 + 141 + 13 = 175.
      Ampliado en P2 (correccion del juez, sin tocar ninguna estimacion): se suman los intervalos descriptivos del lado del hijo (las
      filas de mart_hijo_coef menos la que es la hipotesis hijo_depletado). Los p de la prueba de equilibrio no se cuentan.
  Hipotesis del libro (ambas con ic_alto del IC por bloques de 5 km, esperando un limite superior que se mantenga bajo el umbral):
      brecha_mes1_bloques: ic_alto_5km de brecha_mes1_base_original en k = 1, expectativa < -0,10.
      sincronia_mes0_bloques: ic_alto_5km de sincronia_pendiente en k = 0, expectativa < -0,02.

Que NO prueba:
  * Un bloque es un proxy grueso de geologia compartida: no mide la correlacion espacial real ni la separa de la causa.
    Un intervalo por bloques mas ancho dice que el intervalo por pads era optimista, no que el efecto sea otro.
  * No hay una unica grilla correcta; por eso se publican dos (2 y 5 km) y la regla R1 usa solo la de 5 km.
  * Es una huella medida de brecha entre padres cercanos y controles, sin afirmacion causal, y sin ajuste por comparaciones
    multiples.
"""
from __future__ import annotations

import duckdb
import numpy as np

from pipeline import descomposicion, placebo, sincronia
from pipeline import hallazgos as hz
from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, BASE_ORIGINAL, KS_PRE, REPS_BOOT, SEMILLA_PLACEBO, _g

LAT0, LON0 = -38.0, -69.0
KM_POR_GRADO = 111.32
TAMANOS_KM = (2.0, 5.0)         # las dos grillas; la regla R1 usa solo la de 5 km
MIN_BLOQUES = 30                # R1 y R2: bloques minimos de 5 km para que el IC por bloques reemplace al de pads
CRUCE_R1 = -0.10                # R1: limite superior del IC de la brecha del mes 1 que dispara la reescritura (-10 puntos)
UMBRAL_DOSIS = sincronia.UMBRAL_DOSIS
K_TITULAR = 1
OFFSET_CELDA = 10_000           # las celdas de la grilla se codifican como enteros no negativos: (ix + OFFSET) * 100_000 + iy + OFFSET

COLS_BLOQUES = [("metrica", "varchar"), ("k", "integer"), ("estimador", "varchar"), ("estimacion", "double"),
                ("ic_bajo_pad", "double"), ("ic_alto_pad", "double"), ("ic_bajo_2km", "double"), ("ic_alto_2km", "double"),
                ("ic_bajo_5km", "double"), ("ic_alto_5km", "double"), ("pads", "integer"), ("bloques_2km", "integer"),
                ("bloques_5km", "integer"), ("ratio_2km", "double"), ("ratio_5km", "double")]
M_HEADLINE = "brecha_mes1_base_original"
M_DESCONTADA = "brecha_mes1_descontada"
M_LIMPIA = "brecha_base_limpia"
M_PEND = "sincronia_pendiente"
M_DIAS, M_TASA = "parte_dias", "parte_tasa"


# ------------------------------------------------------------------ bloques

def proyectar(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Proyeccion equirectangular alrededor de (LAT0, LON0), en km."""
    x = KM_POR_GRADO * (np.asarray(lon, dtype=float) - LON0) * np.cos(np.radians(LAT0))
    y = KM_POR_GRADO * (np.asarray(lat, dtype=float) - LAT0)
    return x, y


def clave_bloque(lat: np.ndarray, lon: np.ndarray, tam_km: float) -> np.ndarray:
    """Codigo entero de la celda de la grilla de `tam_km` km que contiene cada punto: dos puntos tienen el mismo codigo si y solo si
    caen en la misma celda (piso de x / tam, piso de y / tam)."""
    x, y = proyectar(lat, lon)
    ix = np.floor(x / tam_km).astype(np.int64)
    iy = np.floor(y / tam_km).astype(np.int64)
    assert np.abs(ix).max(initial=0) < OFFSET_CELDA and np.abs(iy).max(initial=0) < OFFSET_CELDA
    return (ix + OFFSET_CELDA) * 100_000 + iy + OFFSET_CELDA


def _nombre(tam: float) -> str:
    return f"bloque_{int(tam)}km"


def cargar(con) -> dict:
    """Datos de sincronia (placebo mas f0) y, por pad hijo, su bloque en cada grilla (`bloque_<tam>km` indexado por `clave`)."""
    D = sincronia.cargar(con)
    q = con.execute("select h.hijo, c.lat, c.lon from int_frac_hijo h join int_pozo_ubicacion u on u.pozo_id = h.hijo "
                    "join (select pad_id, avg(lat) as lat, avg(lon) as lon from int_pozo_ubicacion group by pad_id) c "
                    "on c.pad_id = u.pad_id order by h.hijo").fetchall()
    assert [int(r[0]) for r in q] == [int(v) for v in D["hijo_id"]]
    lat, lon = np.array([r[1] for r in q], dtype=float), np.array([r[2] for r in q], dtype=float)
    n_pad = int(D["hijo_pad"].max()) + 1
    for tam in TAMANOS_KM:
        por_pad = np.zeros(n_pad, dtype=np.int64)
        por_pad[D["hijo_pad"]] = clave_bloque(lat, lon, tam)
        D[_nombre(tam)] = por_pad
    return D


def claves(D: dict, clave: np.ndarray) -> dict[str, np.ndarray]:
    """Clave de remuestreo de cada evento por unidad: pad hijo, bloque de 2 km y bloque de 5 km."""
    return {"pad": clave, "2km": D[_nombre(2.0)][clave], "5km": D[_nombre(5.0)][clave]}


# ------------------------------------------------------------------ intervalos

def brecha_descontada_ic(v1: np.ndarray, vm1: np.ndarray, banda: np.ndarray, clave: np.ndarray, reps: int, semilla: int) -> dict:
    """Brecha cercano menos control del mes 1 menos la del mes -1 (medianas, mismos eventos y mismas remuestras), IC 95% por
    bootstrap de percentiles por conglomerados de `clave`."""
    ok = banda != 1
    v1, vm1, bd, cl = v1[ok], vm1[ok], banda[ok], clave[ok]

    def dif(i):
        return placebo.brecha(v1[i], bd[i])[2] - placebo.brecha(vm1[i], bd[i])[2]

    out = {"estimacion": float(dif(np.arange(len(bd)))), "ic_bajo": float("nan"), "ic_alto": float("nan")}
    grupos = _clusters(cl)
    rng = np.random.default_rng(semilla)
    gs = np.array([dif(_remuestra(rng, grupos)) for _ in range(reps)])
    gs = gs[~np.isnan(gs)]
    if len(gs):
        out["ic_bajo"], out["ic_alto"] = (float(x) for x in np.percentile(gs, [2.5, 97.5]))
    return out


def _fila(metrica: str, k: int, estimador: str, est: float, ic: dict[str, tuple[float, float]], pads: int, b2: int, b5: int) -> tuple:
    a = {u: ic[u][1] - ic[u][0] for u in ic}
    with np.errstate(divide="ignore", invalid="ignore"):
        r2, r5 = a["2km"] / a["pad"], a["5km"] / a["pad"]
    return (metrica, int(k), estimador, float(est), *ic["pad"], *ic["2km"], *ic["5km"], int(pads), int(b2), int(b5), float(r2), float(r5))


def _n(x: np.ndarray) -> int:
    return int(len(np.unique(x)))


def filas_brecha(D: dict) -> list[tuple]:
    """Brecha del mes 1 con la base original, su version descontada y la serie k = -3..3 con la base limpia."""
    filas = []
    ml = placebo.marco(D, D["hijo_mes"], ks=KS_PRE, base=BASE_LIMPIA)
    mo = placebo.marco(D, D["hijo_mes"], ks=(K_TITULAR,), base=BASE_ORIGINAL)

    def una(metrica, k, m, vals, semilla):
        cl = claves(D, m["clave"])
        r = {u: placebo.brecha_ic(vals, m["banda"], cl[u], REPS_BOOT, semilla) for u in cl}
        ok = ~np.isnan(vals) & (m["banda"] != 1)
        ic = {u: (r[u]["ic_bajo"], r[u]["ic_alto"]) for u in r}
        return _fila(metrica, k, "mediana", r["pad"]["brecha"], ic, _n(cl["pad"][ok]), _n(cl["2km"][ok]), _n(cl["5km"][ok]))

    semilla = SEMILLA_PLACEBO + 100 + (K_TITULAR - KS_PRE[0])
    filas.append(una(M_HEADLINE, K_TITULAR, mo, mo["idx"][K_TITULAR], semilla))
    cl = claves(D, ml["clave"])
    v1, vm1 = ml["idx"][K_TITULAR], ml["idx"][-1]
    r = {u: brecha_descontada_ic(v1, vm1, ml["banda"], cl[u], REPS_BOOT, semilla) for u in cl}
    ok = ~np.isnan(v1) & (ml["banda"] != 1)
    filas.append(_fila(M_DESCONTADA, K_TITULAR, "mediana", r["pad"]["estimacion"], {u: (r[u]["ic_bajo"], r[u]["ic_alto"]) for u in r},
                       _n(cl["pad"][ok]), _n(cl["2km"][ok]), _n(cl["5km"][ok])))
    for j, k in enumerate(KS_PRE):
        filas.append(una(M_LIMPIA, k, ml, ml["idx"][k], SEMILLA_PLACEBO + 100 + j))
    return filas


def filas_sincronia(D: dict) -> list[tuple]:
    filas = []
    for k in (0, -1):
        e = sincronia.eventos(D, k)
        cl = claves(D, e["clave"])
        r = {u: sincronia.pendiente_ic(dict(e, clave=cl[u]), k, REPS_BOOT) for u in cl}
        ic = {u: (r[u]["ic_bajo"], r[u]["ic_alto"]) for u in r}
        filas.append(_fila(M_PEND, k, "pendiente", r["pad"]["pendiente"], ic, _n(cl["pad"]), _n(cl["2km"]), _n(cl["5km"])))
    return filas


def filas_partes(D: dict, Dext: dict) -> list[tuple]:
    """Partes de los dias y del caudal por dia en la brecha del log del volumen al mes 1, por variante de cerrados."""
    m = placebo.marco(D, D["hijo_mes"], ks=(K_TITULAR,), base=BASE_LIMPIA)
    cl = claves(D, m["clave"])
    semilla = descomposicion._semilla(K_TITULAR)
    dias, tasa = [], []
    for var in descomposicion.VARIANTES:
        ld, lr = descomposicion._logs(Dext, m, K_TITULAR, var == "con_cerrados")
        r = {u: descomposicion._brecha_logs_ic(ld, lr, m["banda"], cl[u], REPS_BOOT, semilla) for u in cl}
        ok = ~np.isnan(ld) & ~np.isnan(lr) & (m["banda"] != 1)
        n = (_n(cl["pad"][ok]), _n(cl["2km"][ok]), _n(cl["5km"][ok]))
        ic_d = {u: r[u]["parte_ic"] for u in r}
        ic_t = {u: (1 - ic_d[u][1], 1 - ic_d[u][0]) for u in r}
        dias.append(_fila(M_DIAS, K_TITULAR, var, r["pad"]["parte_dias"], ic_d, *n))
        tasa.append(_fila(M_TASA, K_TITULAR, var, r["pad"]["parte_tasa"], ic_t, *n))
    return dias + tasa


def calcular(D: dict, Dext: dict) -> list[tuple]:
    return filas_brecha(D) + filas_sincronia(D) + filas_partes(D, Dext)


# ------------------------------------------------------------------ reglas

def _fila_mart(filas: list[dict], metrica: str, k: int, estimador: str | None = None) -> dict:
    for f in filas:
        if f["metrica"] == metrica and f["k"] == k and (estimador is None or f["estimador"] == estimador):
            return f
    raise KeyError((metrica, k, estimador))


def leer(con) -> list[dict]:
    cols = [c for c, _ in COLS_BLOQUES]
    return [dict(zip(cols, r)) for r in con.execute(f"select {', '.join(cols)} from mart_bloques order by rowid").fetchall()]


def veredicto_r1(filas: list[dict]) -> dict:
    """R1: IC por bloques de 5 km de la brecha del mes 1 (base -3 a -1). `cruza` si su limite superior queda sobre -0,10; en ese
    caso `rango` es (puntos desde, puntos hasta) con los dos extremos 19 y 23 re-estimados por bloques de 5 km."""
    h = _fila_mart(filas, M_HEADLINE, K_TITULAR)
    d = _fila_mart(filas, M_DESCONTADA, K_TITULAR)
    if h["bloques_5km"] < MIN_BLOQUES:
        return {"estado": "sin bloques", "cruza": False, "rango": None}
    cruza = h["ic_alto_5km"] > CRUCE_R1
    rango = None
    if cruza:
        rango = (round(-100 * max(h["ic_alto_5km"], d["ic_alto_5km"])), round(-100 * min(h["ic_bajo_5km"], d["ic_bajo_5km"])))
    return {"estado": "cruza" if cruza else "no cruza", "cruza": cruza, "rango": rango}


def veredicto_r2(filas: list[dict], grupos: list[tuple]) -> str:
    """R2: el veredicto de pipeline.sincronia con el IC por bloques de 5 km (o 'sin bloques' si hay menos de MIN_BLOQUES)."""
    p0 = _fila_mart(filas, M_PEND, 0)
    pm1 = _fila_mart(filas, M_PEND, -1)
    if p0["bloques_5km"] < MIN_BLOQUES:
        return "sin bloques"
    return sincronia.veredicto({"ic_bajo": p0["ic_bajo_5km"], "ic_alto": p0["ic_alto_5km"]}, {"ic_alto": pm1["ic_alto_5km"]}, grupos)


def conteo_pruebas(con) -> dict:
    """R3: pruebas estadisticas del proyecto con los numeros ya publicados mas las filas de bloques que no son hipotesis."""
    hip = len(hz.HIPOTESIS)
    rob = con.execute("select count(*) from mart_robustez_eje where grupo <> 'completa'").fetchone()[0]
    desc = sum(con.execute(f"select count(*) from {t}").fetchone()[0]
               for t in ("mart_descomposicion_k", "mart_descomposicion_aditiva", "mart_descomposicion_distancia"))
    otras = con.execute("select count(*) from mart_bloques").fetchone()[0] - 2
    # intervalos descriptivos del lado del hijo (pipeline.hijo): las filas de coeficientes menos la que es la hipotesis del libro
    hijo = 0
    if con.execute("select count(*) from information_schema.tables where table_name = 'mart_hijo_coef'").fetchone()[0]:
        hijo = con.execute("select count(*) from mart_hijo_coef").fetchone()[0] - 1
    return {"hipotesis": hip, "robustez": rob, "descomposicion": desc, "hijo": hijo, "bloques": otras,
            "total": hip + rob + desc + hijo + otras}


def linea_pruebas(c: dict) -> str:
    return (f"Pruebas estadísticas del libro: {_g(c['total'])} ({_g(c['hipotesis'])} hipótesis del libro, "
            f"{_g(c['robustez'])} subconjuntos de robustez, {_g(c['descomposicion'])} intervalos de la descomposición, "
            f"{_g(c['hijo'])} intervalos descriptivos del lado del hijo y {_g(c['bloques'])} intervalos por bloques que no son hipótesis), sin ajuste por comparaciones múltiples. No cuenta los diseños causales, con sus placebos y cortes, ni las escalas de bloques ni las permutaciones de D2: esas se cuentan aparte en `inferencia.md`.")


# ------------------------------------------------------------------ pagina

FACTOR = {M_HEADLINE: 100, M_DESCONTADA: 100, M_LIMPIA: 100, M_PEND: 10, M_DIAS: 100, M_TASA: 100}
NOMBRE_METRICA = {M_HEADLINE: "Brecha del mes 1 con la base de los meses -3 a -1 (puntos)",
                  M_DESCONTADA: "Brecha del mes 1 menos la del mes -1, base -6 a -4 (puntos)",
                  M_LIMPIA: "Brecha con la base de los meses -6 a -4 (puntos)",
                  M_PEND: "Pendiente de la brecha por f0 (puntos por 0,1 de f0)",
                  M_DIAS: "Parte de los días en la brecha del volumen al mes 1 (%)",
                  M_TASA: "Parte del caudal por día en la brecha del volumen al mes 1 (%)"}
TEXTO_R1 = {
    "no cruza": "El límite superior del IC por bloques de 5 km queda por debajo de -10 puntos: no cruza el umbral fijado. El rango "
                "titular de 19 a 23 puntos se mantiene; lo que cambia es el IC publicado, que pasa a ser el de bloques de 5 km.",
    "cruza": "El límite superior del IC por bloques de 5 km queda por encima de -10 puntos: cruza el umbral fijado. El rango titular "
             "se reescribe con los IC por bloques de 5 km de sus dos extremos.",
    "sin bloques": "El IC por bloques de 5 km tiene menos de 30 bloques: no reemplaza al IC por pads y se informa el recuento.",
}
TEXTO_R2 = {
    "sostiene": "Con bloques de 5 km el límite superior del IC de la pendiente del mes 0 sigue por debajo de -0,02 y el del mes -1 no "
                "excluye cero: el veredicto se mantiene.",
    "no firme": "Con bloques de 5 km la pendiente no pasa el umbral fijado, o la del mes -1 excluye cero con el mismo signo: el veredicto "
                "pasa a no firme.",
    "plana": "Con bloques de 5 km el IC de la pendiente del mes 0 incluye cero: el veredicto pasa a plana, que debilita el vínculo "
             "temporal con la fractura.",
    "opuesta": "Con bloques de 5 km la pendiente tiene el signo contrario al de una dosis: el veredicto pasa a opuesta.",
    "sin bloques": "El IC por bloques de 5 km tiene menos de 30 bloques: el veredicto de sincronía no cambia y se informa el recuento.",
    "sin muestra": "Algún grupo de terciles tiene menos de 30 eventos y no se calcula veredicto.",
}


def _v(f: dict, col: str) -> str:
    """Valor de una fila en la unidad de su metrica, con un decimal."""
    return _g(FACTOR[f["metrica"]] * f[col], 1)


def _ic(f: dict, u: str) -> str:
    return f"{_v(f, 'ic_bajo_' + u)} a {_v(f, 'ic_alto_' + u)}"


def pagina_bloques(con) -> str:
    filas = leer(con)
    grupos = con.execute("select * from mart_sincronia order by bin").fetchall()
    h = _fila_mart(filas, M_HEADLINE, K_TITULAR)
    p0, pm1 = _fila_mart(filas, M_PEND, 0), _fila_mart(filas, M_PEND, -1)
    d_c = _fila_mart(filas, M_DIAS, K_TITULAR, "con_cerrados")
    t_c = _fila_mart(filas, M_TASA, K_TITULAR, "con_cerrados")
    r1 = veredicto_r1(filas)
    r2 = veredicto_r2(filas, grupos)
    anchos = [f["ratio_5km"] for f in filas]
    L = ["# Bloques espaciales", "",
         "Página generada por `pipeline/bloques.py`. Repite los intervalos de los resultados principales remuestreando bloques de una "
         "grilla espacial en vez de pads hijo, para ver si el intervalo por pads era optimista cuando pads vecinos comparten "
         "geología y programa de fractura. Complementa [Interferencia entre fracturas](interferencia.md), la "
         "[sincronía](sincronia.md) y la [descomposición](descomposicion.md); las reglas se fijaron antes de correr y están en el "
         "libro de hallazgos como `brecha_mes1_bloques` y `sincronia_mes0_bloques`.", "",
         "## Resumen", "",
         "Veredictos contra las reglas fijadas antes de correr (las estimaciones puntuales no cambian; solo cambia la unidad que se "
         "remuestrea):", "",
         f"- **R1, brecha del mes 1: {r1['estado']}.** {TEXTO_R1[r1['estado']]}",
         f"- Brecha del mes 1 con la base de los meses -3 a -1: {_v(h, 'estimacion')} puntos. IC 95% por pads: {_ic(h, 'pad')}; por "
         f"bloques de 2 km: {_ic(h, '2km')} ({_g(h['bloques_2km'])} bloques); por bloques de 5 km: {_ic(h, '5km')} "
         f"({_g(h['bloques_5km'])} bloques).",
         f"- **R2, sincronía: {r2}.** {TEXTO_R2[r2]}",
         f"- Pendiente del mes 0: {_v(p0, 'estimacion')} puntos por cada 0,1 de f0. IC 95% por pads: {_ic(p0, 'pad')}; por bloques de "
         f"2 km: {_ic(p0, '2km')}; por bloques de 5 km: {_ic(p0, '5km')} ({_g(p0['bloques_5km'])} bloques). Mes -1, por bloques de "
         f"5 km: {_ic(pm1, '5km')}.",
         f"- Partes al mes 1 con los meses cerrados: los días explican el {_v(d_c, 'estimacion')}% de la brecha del volumen (IC 95% por "
         f"bloques de 5 km: {_ic(d_c, '5km')}) y el caudal por día el {_v(t_c, 'estimacion')}% ({_ic(t_c, '5km')}).",
         f"- Ancho del IC por bloques de 5 km sobre el de pads: de {_g(min(anchos), 2)} a {_g(max(anchos), 2)} veces en las "
         f"{_g(len(filas))} filas.",
         f"- {linea_pruebas(conteo_pruebas(con))}", "",
         "## Regla fijada antes de correr", "",
         "El pad hijo de cada evento se ubica en el promedio de las coordenadas de superficie de sus pozos y se proyecta a kilómetros "
         "con una proyección equirectangular alrededor de (-38,0, -69,0). El bloque es la celda de una grilla de 2 km o de 5 km. Cada "
         "IC es bootstrap de percentiles (2,5 y 97,5) con "
         f"{_g(REPS_BOOT)} repeticiones que remuestrean bloques completos, con el mismo estimador, los mismos eventos y la misma "
         "semilla por k que el intervalo por pads.", "",
         "- R1: el IC del mes 1 del README y del caso pasa a ser el de bloques de 5 km si tiene 30 bloques o más. Si su límite "
         "superior queda por encima de -10 puntos, el rango 19 a 23 se reescribe con los IC por bloques de 5 km de sus dos extremos.",
         "- R2: el veredicto de la pendiente de sincronía se vuelve a derivar con el IC de bloques de 5 km y la regla de la página de "
         "sincronía (límite superior menor que -0,02 por unidad de f0, y el mes -1 sin pendiente negativa que excluya cero).",
         "- R3: se cuentan todas las pruebas estadísticas del proyecto en una línea (arriba).", "",
         "## Resultados", "",
         "Brechas en puntos de índice, pendientes en puntos por cada 0,1 de f0, partes en %. La estimación puntual es la de la página "
         "original.", "",
         "| Métrica | k | Estimador | Estimación | IC 95% por pads | IC 95% por bloques de 2 km | IC 95% por bloques de 5 km |",
         "| --- | ---: | --- | ---: | --- | --- | --- |"]
    for f in filas:
        L.append(f"| `{f['metrica']}` | {f['k']} | {f['estimador']} | {_v(f, 'estimacion')} | {_ic(f, 'pad')} | {_ic(f, '2km')} | "
                 f"{_ic(f, '5km')} |")
    L += ["", "Pads y bloques con eventos, y el ancho de cada IC por bloques sobre el de pads:", "",
          "| Métrica | k | Estimador | Pads hijo | Bloques de 2 km | Bloques de 5 km | Ancho de 2 km sobre pads | Ancho de 5 km sobre pads |",
          "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
    for f in filas:
        L.append(f"| `{f['metrica']}` | {f['k']} | {f['estimador']} | {_g(f['pads'])} | {_g(f['bloques_2km'])} | {_g(f['bloques_5km'])} | "
                 f"{_g(f['ratio_2km'], 2)} | {_g(f['ratio_5km'], 2)} |")
    L += ["", "Las métricas, por nombre:", ""]
    L += [f"- `{m}`: {n}." for m, n in NOMBRE_METRICA.items()]
    L += ["",
          "## Límites", "",
          "- Un bloque es un proxy grueso de geología compartida: no mide la correlación espacial real ni la separa de otras fuentes de "
          "dependencia. Un IC por bloques más ancho dice que el intervalo por pads era optimista, no que el efecto sea otro.",
          "- No hay una única grilla correcta: por eso se publican dos y la regla R1 usa solo la de 5 km.",
          "- No se hizo la variante de pads dentro de bloques (remuestrear bloques y luego pads).",
          "- Es una huella medida de la brecha entre padres cercanos y controles, no una prueba de causa, y los intervalos no se ajustan "
          "por comparaciones múltiples.", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ principal

def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    D = cargar(con)
    filas = calcular(D, descomposicion.cargar_ext(con, D))
    _escribir(con, "mart_bloques", COLS_BLOQUES, filas)
    for r in con.execute("select * from mart_bloques order by rowid").fetchall():
        print("[bloques]", tuple(round(x, 4) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
