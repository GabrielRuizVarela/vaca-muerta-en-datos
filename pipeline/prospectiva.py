"""Prueba prospectiva del estudio de eventos de interferencia: predicciones congeladas con los datos hasta ultimo_mes y puntuadas
cuando se publiquen meses nuevos.

Se corre despues de pipeline.build:
  uv run python -m pipeline.prospectiva             puntua contra el warehouse actual y escribe wiki/hallazgos/prospectiva.md
  uv run python -m pipeline.prospectiva congelar    una sola vez; se niega si el archivo congelado ya existe

REGLA FIJADA ANTES DE CONGELAR (2026-11-18, antes de escribir el archivo congelado; no se cambia despues de ver resultados). Lo unico
que se miro antes de fijarla: el conteo de hijos por mes de fractura (int_frac_hijo) y de eventos por banda y mes de fractura
(int_interferencia_evento) de 2025-07 a 2026-09, y la fila brecha_mes1_base_original de mart_bloques, que ya esta publicada. La carga
de fracturas viene atrasada: hay 9, 7 y 3 hijos con ubicacion fracturados en julio, agosto y septiembre de 2026, contra unos 35 por
mes antes, y ningun evento cercano con fractura en septiembre de 2026. Los meses que se predicen no estan publicados: no hay ningun
indice que mirar.

Pregunta: el resultado principal (un mes despues de la fractura de un hijo, los padres a menos de 1 km rinden unos 23 puntos menos de
su caudal previo que los controles a 2 a 5 km, y al mes 6 la brecha queda a menos de 5 puntos) se midio sobre datos ya publicados.
Se sostiene en meses que todavia no estaban publicados cuando se fijo la prediccion?

Lo congelado (data/prospectiva_congelada.json, escrito una sola vez con el warehouse de los datos hasta ultimo_mes = U):
  * U, la fecha de congelado, el sha256 de data/manifest.json y los sha256 de los CSV de produccion y de fractura que nombra.
  * P1 y P2 (abajo) con sus numeros leidos del warehouse de U, los parametros de esta regla, y el conteo por banda de los eventos
    ya conocidos al congelar que entran en cada prediccion (solo el conteo; la lista no se guarda).
  * El sha256 del archivo va al lado (data/prospectiva_congelada.json.sha256) y en SHA_CONGELADA en este modulo. La puntuacion se
    niega (sale con error) si el sha256 del archivo no coincide con los dos.

Eventos que se puntuan. Se recalculan con el warehouse nuevo con las reglas del resultado principal (placebo.marco con la base de los
meses -3 a -1: edad del padre de al menos 6 meses, base mayor que 1 m3/d, el hijo mas cercano fija la banda, cercano a menos de 1 km,
control de 2 a 5 km; los de 1 a 2 km no entran):
  * P1: eventos con mes de fractura del hijo mayor o igual que U (su mes 1 es posterior a U).
  * P2: eventos con mes de fractura del hijo mayor o igual que U menos 5 meses (su mes 6 es posterior a U).
  Entran tambien los hijos que la carga de fracturas agregue despues de congelar: la prediccion es sobre la regla, no sobre una lista,
  y lo que la hace prospectiva es que el mes que se mide no estaba publicado al congelar. Base, edad, banda e indice salen del
  warehouse nuevo; si una publicacion corrige un mes viejo, se usa el valor corregido.

Faltantes (regla conservadora): un evento sin dato en el mes k (sin fila, mes no publicado o caudal nulo) no entra al conteo de ese k
y no se imputa. Si el IC no se puede calcular, el resultado no pasa: "no firme". Un warehouse con ultimo_mes menor o igual que U da
"pendiente" sin calcular nada.

Medida: brecha = mediana del indice de los cercanos menos mediana del de los controles en el mes k (placebo.brecha), con IC 95% de
percentiles por bootstrap de bloques de 5 km del pad hijo (bloques.clave_bloque sobre el promedio de lat y lon de los pozos del pad,
como el IC titular), REPS_BOOT repeticiones y semilla SEMILLA_PLACEBO + DESPLAZAMIENTO_SEMILLA + k.

Minimos (si no se cumplen, "sin muestra"): MIN_CERCANOS = 100 eventos cercanos y MIN_CONTROLES = 100 controles con dato en el mes k, y
MIN_BLOQUES = 15 bloques de 5 km con eventos con dato (cercanos o controles).

P1, brecha del mes 1. Prediccion: la estimacion de brecha_mes1_base_original de mart_bloques (-22,9 puntos con los datos hasta 2026-09)
y como intervalo predicho su IC 95% por bloques de 5 km (-28,7 a -16,8). Veredicto:
  * sostiene: el limite superior del IC nuevo es menor que cero y el IC nuevo se superpone con el intervalo predicho.
  * no se sostiene: el IC nuevo queda entero fuera del intervalo predicho. Por arriba: la brecha es menor que la predicha o nula; por
    abajo: es mayor que la predicha. El texto dice de que lado.
  * no firme: cualquier otro caso (por ejemplo, un IC que toca el intervalo predicho y tambien cruza cero).
  * sin muestra: no se cumplen los minimos.
P2, cierre al mes 6. Prediccion: la brecha del mes 6 queda a menos de UMBRAL_CHICO = 0,05 de cero (la hipotesis recuperacion_mes6 del
libro); se congela tambien su valor con los datos hasta U, calculado con placebo.marco sobre todos los eventos. Veredicto:
  * sostiene: el valor absoluto de la brecha nueva es menor que 0,05 y el IC nuevo queda entero entre -CIERRE_MAX y CIERRE_MAX (0,10).
  * no se sostiene: el IC nuevo excluye cero y el valor absoluto de la brecha es de 0,05 o mas (queda una brecha al mes 6).
  * no firme: cualquier otro caso.
  * sin muestra: no se cumplen los minimos.
Gas: el estudio del padre gasifero (pipeline.gas) dio "no firme" por pretendencia; no se predice nada del gas.

Que NO prueba:
  * Repite el diseno sobre meses nuevos, no prueba causa: una prediccion que se sostiene dice que la huella vuelve a aparecer en eventos
    cuyo resultado no se conocia, no que la fractura sea la causa.
  * Con la carga al dia entran unos 30 eventos cercanos por mes de fractura, y la carga viene atrasada, asi que pasan varias
    publicaciones antes de salir de "sin muestra"; con poca muestra el IC es ancho y lo esperable es "no firme".
  * Cada publicacion vuelve a puntuar con mas eventos: son miradas repetidas sobre datos que se acumulan, sin ajuste por eso. La pagina
    publica el veredicto de cada puntuacion con el mes de los datos.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

from pipeline import placebo
from pipeline.bloques import clave_bloque
from pipeline.ingest import DATA, ROOT
from pipeline.placebo import REPS_BOOT, SEMILLA_PLACEBO

MIN_CERCANOS = 100
MIN_CONTROLES = 100
MIN_BLOQUES = 15
UMBRAL_CHICO = 0.05
CIERRE_MAX = 0.10
K_P1 = 1
K_P2 = 6
DESPLAZAMIENTO_SEMILLA = 1000
SEMILLA = SEMILLA_PLACEBO + DESPLAZAMIENTO_SEMILLA
REPS = REPS_BOOT
RUTA_CONGELADA = DATA / "prospectiva_congelada.json"
SHA_CONGELADA: str | None = "7a49f4135d042ff064e77914cab0d0c2997b4ae1d1d022aabacf58c2fab83e6c"  # fijado al congelar, en el mismo commit que el archivo

SQL_CENTROIDES = """
select h.hijo, c.lat, c.lon
from int_frac_hijo h
join int_pozo_ubicacion u on u.pozo_id = h.hijo
join (select pad_id, avg(lat) as lat, avg(lon) as lon from int_pozo_ubicacion group by pad_id) c
  on c.pad_id = u.pad_id
order by h.hijo
"""


def cargar(con) -> dict:
    """Lo mismo que placebo.cargar mas el bloque de 5 km de cada pad hijo."""
    d = placebo.cargar(con)
    cent = con.execute(SQL_CENTROIDES).fetchall()
    cc = {r[0]: (r[1], r[2]) for r in cent}
    lat = np.array([cc[int(h)][0] for h in d["hijo_id"]], dtype=float)
    lon = np.array([cc[int(h)][1] for h in d["hijo_id"]], dtype=float)
    por_pad = np.zeros(int(d["hijo_pad"].max()) + 1, dtype=np.int64)
    por_pad[d["hijo_pad"]] = clave_bloque(lat, lon, 5.0)
    d["bloque_5km"] = por_pad
    return d


def mes_iso(idx: int) -> str:
    """Indice de mes (0 = 2000-01) a fecha ISO del primer dia."""
    return f"{2000 + idx // 12:04d}-{idx % 12 + 1:02d}-01"


def mes_idx(iso: str) -> int:
    """Fecha ISO a indice de mes (inversa de mes_iso)."""
    return int(placebo._mes_idx([date.fromisoformat(iso)])[0])


def medir(D: dict, desde: int, k: int, reps: int = REPS, semilla: int | None = None) -> dict:
    """Brecha con IC por bloques de 5 km sobre eventos con mes de fractura mayor o igual que `desde`."""
    m = placebo.marco(D, D["hijo_mes"], ks=(k,))
    sel = m["mes"] >= desde
    vals = m["idx"][k][sel]
    banda = m["banda"][sel]
    clave5 = D["bloque_5km"][m["clave"][sel]]
    r = placebo.brecha_ic(vals, banda, clave5, reps, SEMILLA + k if semilla is None else semilla)
    ok = ~np.isnan(vals) & (banda != 1)
    return {"n_near": r["n_near"], "n_ctrl": r["n_ctrl"], "bloques": int(np.unique(clave5[ok]).size),
            "brecha": r["brecha"], "ic_bajo": r["ic_bajo"], "ic_alto": r["ic_alto"]}


def _corto(r: dict, min_cercanos: int, min_controles: int, min_bloques: int) -> str | None:
    if r["n_near"] < min_cercanos or r["n_ctrl"] < min_controles or r["bloques"] < min_bloques:
        n, m, b = r["n_near"], r["n_ctrl"], r["bloques"]
        return f"muestra bajo los minimos: {n} cercanos, {m} controles, {b} bloques de 5 km"
    return None


def _sin_ic(r: dict) -> bool:
    return bool(np.isnan(r["brecha"]) or np.isnan(r["ic_bajo"]) or np.isnan(r["ic_alto"]))


def veredicto_p1(r: dict, pred_bajo: float, pred_alto: float, min_cercanos: int = MIN_CERCANOS,
                 min_controles: int = MIN_CONTROLES, min_bloques: int = MIN_BLOQUES) -> tuple[str, str]:
    """Veredicto P1: la brecha del mes 1 cae dentro de lo predicho y bajo cero."""
    t = _corto(r, min_cercanos, min_controles, min_bloques)
    if t is not None:
        return "sin muestra", t
    if _sin_ic(r):
        return "no firme", "sin IC calculable: no pasa"
    g, lo, hi = r["brecha"], r["ic_bajo"], r["ic_alto"]
    if lo > pred_alto:
        return "no se sostiene", (f"brecha {g:.3f} con IC 5km entero por arriba del intervalo predicho: "
                                  "menor que la predicha o nula")
    if hi < pred_bajo:
        return "no se sostiene", (f"brecha {g:.3f} con IC 5km entero por abajo del intervalo predicho: "
                                  "mayor que la predicha")
    if hi < 0:
        return "sostiene", f"brecha {g:.3f} con IC 5km bajo cero que se superpone con el intervalo predicho"
    return "no firme", f"brecha {g:.3f} con IC 5km que toca el intervalo predicho pero no queda bajo cero"


def veredicto_p2(r: dict, umbral: float = UMBRAL_CHICO, cierre_max: float = CIERRE_MAX,
                 min_cercanos: int = MIN_CERCANOS, min_controles: int = MIN_CONTROLES,
                 min_bloques: int = MIN_BLOQUES) -> tuple[str, str]:
    """Veredicto P2: la brecha del mes 6 se cierra cerca de cero."""
    t = _corto(r, min_cercanos, min_controles, min_bloques)
    if t is not None:
        return "sin muestra", t
    if _sin_ic(r):
        return "no firme", "sin IC calculable: no pasa"
    g, lo, hi = r["brecha"], r["ic_bajo"], r["ic_alto"]
    if abs(g) < umbral and -cierre_max < lo and hi < cierre_max:
        return "sostiene", f"brecha {g:.3f} a menos de 0,05 de cero con IC 5km entre -0,10 y 0,10"
    if (hi < 0 or lo > 0) and abs(g) >= umbral:
        return "no se sostiene", f"brecha {g:.3f} con IC 5km que excluye cero: queda una brecha al mes 6"
    return "no firme", f"brecha {g:.3f} sin forma de cierre ni de brecha que queda"


def congelar(D: dict, fecha: str, p1: tuple[float, float, float], manifest_path) -> dict:
    """Arma el dict congelado con los datos hasta U = ultimo mes de D (no lo escribe)."""
    U = D["n_mes"] - 1
    m1 = placebo.marco(D, D["hijo_mes"], ks=(1,))
    m6 = placebo.marco(D, D["hijo_mes"], ks=(6,))
    p2_val = placebo.brecha(m6["idx"][6], m6["banda"])[2]
    s1 = m1["mes"] >= U
    s6 = m6["mes"] >= U - 5
    raw = Path(manifest_path).read_bytes()
    man = json.loads(raw)
    est, lo, hi = p1
    return {
        "version": 1,
        "fecha_congelado": fecha,
        "ultimo_mes": mes_iso(U),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "produccion_sha256": man["produccion_no_convencional"]["sha256"],
        "fractura_sha256": man["fractura_adjunto_iv"]["sha256"],
        "parametros": {"min_cercanos": MIN_CERCANOS, "min_controles": MIN_CONTROLES, "min_bloques": MIN_BLOQUES,
                       "umbral_chico": UMBRAL_CHICO, "cierre_max": CIERRE_MAX, "reps": REPS, "semilla": SEMILLA},
        "p1": {"k": 1, "desde": mes_iso(U), "prediccion": round(float(est), 6),
               "intervalo_bajo": round(float(lo), 6), "intervalo_alto": round(float(hi), 6),
               "fuente": "mart_bloques brecha_mes1_base_original, IC 95% por bloques de 5 km",
               "conocidos_cercanos": int(((m1["banda"] == 0) & s1).sum()),
               "conocidos_controles": int(((m1["banda"] == 2) & s1).sum())},
        "p2": {"k": 6, "desde": mes_iso(U - 5), "prediccion": round(float(p2_val), 6), "umbral": UMBRAL_CHICO,
               "fuente": "placebo.marco, todos los eventos hasta ultimo_mes",
               "conocidos_cercanos": int(((m6["banda"] == 0) & s6).sum()),
               "conocidos_controles": int(((m6["banda"] == 2) & s6).sum())},
    }


def serializar(d: dict) -> bytes:
    """El dict congelado a bytes JSON canonicos."""
    return (json.dumps(d, sort_keys=True, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


class CongeladaAlterada(RuntimeError):
    """El archivo congelado no coincide con el sha esperado."""


def escribir_congelada(d: dict, path) -> str:
    """Escribe el congelado y su lado .sha256 una sola vez; devuelve el sha."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"ya existe, no se pisa: {path}")
    raw = serializar(d)
    sha = hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw)
    path.with_name(path.name + ".sha256").write_text(f"{sha}  {path.name}\n", encoding="utf-8")
    return sha


def leer_congelada(path=RUTA_CONGELADA, sha_esperado: str | None = SHA_CONGELADA) -> dict:
    """Lee el congelado verificando el sha contra el lado .sha256 y el esperado."""
    path = Path(path)
    if not path.exists():
        raise CongeladaAlterada(f"falta el archivo congelado: {path}")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha_esperado is None:
        raise CongeladaAlterada(f"sin sha esperado para verificar el archivo con sha {sha}")
    lado = path.with_name(path.name + ".sha256")
    if not lado.exists():
        raise CongeladaAlterada(f"falta el lado .sha256: archivo {sha}, esperado {sha_esperado}")
    partes = lado.read_text(encoding="utf-8").split()
    token = partes[0] if partes else ""
    if token != sha:
        raise CongeladaAlterada(f"lado .sha256 distinto: archivo {sha}, lado {token}, esperado {sha_esperado}")
    if sha != sha_esperado:
        raise CongeladaAlterada(f"congelada alterada: archivo {sha}, esperado {sha_esperado}")
    return json.loads(raw)


def puntuar(D: dict, congelada: dict, reps: int | None = None) -> dict:
    """Puntua P1 y P2 con el warehouse nuevo, o pendiente si no hay meses nuevos."""
    U = mes_idx(congelada["ultimo_mes"])
    ultimo = D["n_mes"] - 1
    if ultimo <= U:
        return {"estado": "pendiente", "ultimo_mes": mes_iso(ultimo)}
    par = congelada["parametros"]
    reps = par["reps"] if reps is None else reps
    p1, p2 = congelada["p1"], congelada["p2"]
    r1 = medir(D, mes_idx(p1["desde"]), p1["k"], reps, par["semilla"] + p1["k"])
    r2 = medir(D, mes_idx(p2["desde"]), p2["k"], reps, par["semilla"] + p2["k"])
    v1, t1 = veredicto_p1(r1, congelada["p1"]["intervalo_bajo"], congelada["p1"]["intervalo_alto"],
                          par["min_cercanos"], par["min_controles"], par["min_bloques"])
    v2, t2 = veredicto_p2(r2, par["umbral_chico"], par["cierre_max"],
                          par["min_cercanos"], par["min_controles"], par["min_bloques"])
    return {"estado": "puntuado", "ultimo_mes": mes_iso(ultimo),
            "p1": {**r1, "veredicto": v1, "texto": t1}, "p2": {**r2, "veredicto": v2, "texto": t2}}


# ------------------------------------------------------------------ pagina y linea de comandos

RUTA_PAGINA = ROOT / "wiki" / "hallazgos" / "prospectiva.md"
NOMBRE_P = {"p1": "P1, brecha del mes 1", "p2": "P2, cierre al mes 6"}


def _pts(x: float) -> str:
    return placebo._g(100 * x, 1)


def _mes(iso: str) -> str:
    return iso[:7]


def _texto(t: str) -> str:
    """Texto del veredicto para la pagina: coma decimal, tildes y mayuscula inicial."""
    t = re.sub(r"(\d)\.(\d)", r"\1,\2", t).replace("minimos", "mínimos")
    return t[0].upper() + t[1:]


def pagina(congelada: dict, sha: str, res: dict) -> str:
    """Pagina wiki/hallazgos/prospectiva.md: estado de la puntuacion, lo congelado, la regla y los limites."""
    g = placebo._g
    c, p1, p2 = congelada, congelada["p1"], congelada["p2"]
    par = c["parametros"]
    U = _mes(c["ultimo_mes"])
    L = ["# Prueba prospectiva", "",
         "Página generada por `pipeline/prospectiva.py`. El resultado principal se midió sobre datos ya publicados; esta página congela "
         f"dos predicciones con los datos hasta {U} y las puntúa cuando se publican los meses siguientes, para un operador de Vaca Muerta "
         "que quiere saber si la huella vuelve a aparecer en meses que nadie había visto. La regla, los mínimos y el veredicto se fijaron "
         "en el código antes de congelar. Complementa [Interferencia entre fracturas](interferencia.md), las "
         "[pruebas de falsación](placebo.md) y los [bloques espaciales](bloques.md).", "",
         "## Estado", ""]
    if res["estado"] == "pendiente":
        L += [f"- **Pendiente.** El warehouse llega a {_mes(res['ultimo_mes'])}, sin meses posteriores a los congelados ({U}): no hay "
              "nada que puntuar. Se puntúa cuando se publique un mes nuevo.", ""]
    else:
        L += [f"Puntuado con los datos hasta {_mes(res['ultimo_mes'])}.", ""]
        for clave in ("p1", "p2"):
            r = res[clave]
            L.append(f"- **{NOMBRE_P[clave]}: {r['veredicto']}.** {_texto(r['texto'])}.")
        L += ["", "| Predicción | Mes | Cercanos | Controles | Bloques de 5 km | Brecha | IC 95% por bloques de 5 km | Veredicto |",
              "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
        for clave, k in (("p1", K_P1), ("p2", K_P2)):
            r = res[clave]
            L.append(f"| {NOMBRE_P[clave]} | {k} | {g(r['n_near'])} | {g(r['n_ctrl'])} | {g(r['bloques'])} | {_pts(r['brecha'])} | "
                     f"{_pts(r['ic_bajo'])} a {_pts(r['ic_alto'])} | {r['veredicto']} |")
        L.append("")
    L += ["## Lo congelado", "",
          f"- Fecha de congelado: {c['fecha_congelado']}. Datos hasta {U}.",
          f"- sha256 del archivo congelado (`data/prospectiva_congelada.json`): `{sha}`.",
          f"- sha256 de `data/manifest.json` al congelar: `{c['manifest_sha256']}`; CSV de producción: `{c['produccion_sha256'][:12]}`; "
          f"CSV de fractura: `{c['fractura_sha256'][:12]}`.",
          f"- P1: brecha del mes 1 de {_pts(p1['prediccion'])} puntos de índice, con intervalo predicho de {_pts(p1['intervalo_bajo'])} a "
          f"{_pts(p1['intervalo_alto'])} (IC 95% por bloques de 5 km del resultado principal). Entran los eventos con fractura del hijo "
          f"desde {_mes(p1['desde'])}; al congelar se conocían {g(p1['conocidos_cercanos'])} cercanos y {g(p1['conocidos_controles'])} "
          "controles.",
          f"- P2: brecha del mes 6 a menos de {_pts(p2['umbral'])} puntos de cero ({_pts(p2['prediccion'])} puntos con los datos hasta {U}). "
          f"Entran los eventos con fractura del hijo desde {_mes(p2['desde'])}; al congelar se conocían {g(p2['conocidos_cercanos'])} "
          f"cercanos y {g(p2['conocidos_controles'])} controles.",
          "- Del gas no se predice nada: el estudio del padre gasífero dio \"no firme\" por pretendencia.", "",
          "## Regla de puntuación", "",
          "- Los eventos se recalculan con el warehouse nuevo con las reglas del resultado principal (base de los meses -3 a -1, padre de "
          "al menos 6 meses, el hijo más cercano fija la banda: cercano a menos de 1 km, control de 2 a 5 km). Entran también los hijos "
          "que la carga de fracturas agregue después de congelar: la predicción es sobre la regla, y lo que la hace prospectiva es que el "
          "mes medido no estaba publicado.",
          "- Brecha: mediana del índice de los cercanos menos la de los controles, con IC 95% por bootstrap de bloques de 5 km del pad hijo.",
          f"- Mínimos: {g(par['min_cercanos'])} cercanos y {g(par['min_controles'])} controles con dato en el mes, y {g(par['min_bloques'])} "
          "bloques de 5 km; debajo, \"sin muestra\". Un evento sin dato en el mes no cuenta y no se imputa; sin IC calculable, \"no firme\".",
          "- P1. Sostiene: IC bajo cero que se superpone con el intervalo predicho. No se sostiene: IC entero fuera del intervalo predicho "
          "(por arriba, brecha menor o nula; por abajo, mayor). No firme: cualquier otro caso.",
          f"- P2. Sostiene: brecha a menos de {_pts(par['umbral_chico'])} puntos con IC entero entre -{_pts(par['cierre_max'])} y "
          f"{_pts(par['cierre_max'])}. No se sostiene: IC que excluye cero con brecha de {_pts(par['umbral_chico'])} puntos o más. No firme: "
          "cualquier otro caso.",
          "- La puntuación se niega si el sha256 del archivo congelado no coincide con el de al lado y con el del código.", "",
          "## Límites", "",
          "- Repite el diseño sobre meses nuevos, no prueba causa.",
          "- Entran unos 30 eventos cercanos por mes de fractura con la carga al día, y la carga de fracturas viene atrasada: pasan varias "
          "publicaciones antes de salir de \"sin muestra\", y con poca muestra lo esperable es \"no firme\".",
          "- Cada publicación vuelve a puntuar con más eventos: son miradas repetidas sin ajuste por eso; cada veredicto va con el mes de "
          "sus datos.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None, path=DATA / "warehouse.duckdb") -> None:
    """Sin argumentos: puntua y escribe la pagina. Con `congelar`: escribe el archivo congelado (una sola vez)."""
    args = sys.argv[1:] if argv is None else argv
    con = duckdb.connect(str(path), read_only=True)
    D = cargar(con)
    if args[:1] == ["congelar"]:
        fila = con.execute("select estimacion, ic_bajo_5km, ic_alto_5km from mart_bloques "
                           "where metrica = 'brecha_mes1_base_original'").fetchone()
        con.close()
        d = congelar(D, date.today().isoformat(), tuple(float(x) for x in fila), DATA / "manifest.json")
        sha = escribir_congelada(d, RUTA_CONGELADA)
        print(f"[prospectiva] congelado {RUTA_CONGELADA.name} con datos hasta {d['ultimo_mes']}: sha256 {sha}")
        print("[prospectiva] fija SHA_CONGELADA en pipeline/prospectiva.py con ese valor")
        return
    con.close()
    try:
        c = leer_congelada()
    except CongeladaAlterada as e:
        raise SystemExit(f"[prospectiva] se niega a puntuar: {e}")
    res = puntuar(D, c)
    RUTA_PAGINA.write_text(pagina(c, SHA_CONGELADA, res), encoding="utf-8")
    if res["estado"] == "pendiente":
        print(f"[prospectiva] pendiente: datos hasta {res['ultimo_mes']}, congelado con {c['ultimo_mes']}")
    else:
        print(f"[prospectiva] P1 {res['p1']['veredicto']} ({res['p1']['texto']}); P2 {res['p2']['veredicto']} ({res['p2']['texto']})")


if __name__ == "__main__":
    main()
