"""Modo local con agua y tarjeta del operador (porcion D).

Se corre desde el modo local:  uv run python -m pipeline.local --dir CARPETA  (escribe tarjeta.json y tarjeta.md junto a su
salida). Este modulo arma la tarjeta y su prueba de privacidad; pipeline.local lee las tablas.

REGLA FIJADA ANTES DE CORRER (2026-11-26, porcion D de docs/plan-siguiente-nivel.md). Este commit trae la regla, la
validacion y los campos permitidos; no se corrio D2 sobre tablas locales. Si algo resulta ambiguo al construirlo, se corrige
en un commit nuevo que lo diga, nunca despues de ver una cifra de la validacion.

Entrada. `mensual.csv` acepta `agua_m3` opcional (m3 del mes, mayor o igual a cero), en la lista de opcionales de
pipeline.local junto a `dias_produccion`. Sin `agua_m3`, el modo local hace lo de hoy y la tarjeta dice "sin dato de agua".
Con `agua_m3`, corre D2 de pipeline.causal sobre las tablas locales: W, base de W, dW = max(W(g), W(g+1)) - base, celdas,
placebos previo, fecha falsa y distancia falsa, bootstrap por bloques, la misma semilla y REPS. El placebo de cierre necesita
dias producidos: sin `dias_produccion` no se corre, el veredicto se calcula sin esa prueba y la tarjeta lo dice ("sin prueba
de cierre"). Las ubicaciones y los meses de fractura salen de `pozos.csv` como hoy.

Validacion, fijada antes de correr: el warehouse publico exportado a `pozos.csv` y `mensual.csv` (con `agua_m3`, y
`dias_produccion` desde `dias_efectivos`) y corrido por el modo local da D2 con VALIDACION_D2_TRATADOS tratados y ATT_W de
VALIDACION_D2_PP (a un decimal), igual con la misma semilla y repeticiones. Si no da igual, el commit de construccion dice
por que y la diferencia tiene que ser TOLERANCIA_VALIDACION_PP o menos en el valor y en los dos extremos del IC; si no,
la porcion no esta lista. La exportacion y la comparacion son una prueba que se corre con el warehouse (lenta, opcional
sin el).

Tarjeta (`tarjeta.json` y `tarjeta.md`, en espanol con voseo en el .md). Solo cifras agrupadas, de CAMPOS_TARJETA:
eventos (tratados con dato), brecha del mes 1 con IC, dW con IC, veredictos, y la version del codigo (SHA corto). Ningun
pozo_id, pad, coordenada, nombre de pozo ni fecha (mes o dia; el anio tampoco). Una cifra que sale de menos de
MIN_POZOS_CIFRA pozos se suprime ("menos de N pozos"). La prueba de privacidad: con tablas sinteticas, ningun pozo_id ni
nombre de la entrada aparece en la tarjeta, ninguna clave fuera de CAMPOS_TARJETA, ningun numero con forma de coordenada de
la entrada y ningun texto con forma de fecha (AAAA-MM, AAAA-MM-DD, DD/MM/AAAA).

Lo que no dice: la tarjeta de un operador no es una replicacion independiente del estudio publico si el operador ya esta en
el dato publico; lo dice la tarjeta.
"""
from __future__ import annotations

# ---- regla fijada (no cambiar despues de ver cifras) ----
VALIDACION_D2_TRATADOS = 447
VALIDACION_D2_PP = 13.8
TOLERANCIA_VALIDACION_PP = 0.1
MIN_POZOS_CIFRA = 10
CAMPOS_TARJETA = ("version", "eventos", "brecha_mes1", "brecha_mes1_ic", "dw_pp", "dw_ic", "veredicto_petroleo",
                  "veredicto_agua", "notas")
SIN_AGUA = "sin dato de agua"
SIN_CIERRE = "sin prueba de cierre"


# ---- construccion (aplica la regla de arriba; no cambia ninguna constante) ----
import json
import subprocess
from pathlib import Path

import numpy as np

_COLS_PAR_RAMA = ("hijo", "padre", "posicion")


def _version() -> str:
    """SHA corto del codigo que corrio, o 'desconocida' fuera de un checkout."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent, capture_output=True,
                           text=True, timeout=30)
        return r.stdout.strip() or "desconocida"
    except Exception:
        return "desconocida"


def d2_local(con, con_cierre: bool = True, reps: int | None = None) -> dict:
    """D2 de pipeline.causal sobre las tablas de una base armada por pipeline.local.armar_base (con agua_m3).

    Copia el orden de causal.main hasta D2 (cargar, cohortes, la misma semilla, las mismas celdas, W con REPS repeticiones, diseno_d2,
    placebo_cierre y veredicto_d2) para que las mismas tablas den las mismas cifras. Sin dias_produccion
    (con_cierre = False) el placebo de cierre no se corre y el veredicto se calcula sin esa prueba. `reps` solo lo usan
    las pruebas rapidas; el modo local lo pasa solo si el usuario pidio --reps."""
    from pipeline import causal as c

    if not con.execute("select count(*) from information_schema.tables where table_name = 'mart_par_rama'").fetchone()[0]:
        con.execute("create table mart_par_rama (hijo integer, padre integer, posicion varchar)")
    D = c.cargar(con)
    coh = c.cohortes(D)
    rng = np.random.default_rng(c.SEMILLA_CAUSAL)
    cel_pri = c.celdas(D, coh, c.H_CORTO, False)
    cel_s1 = c.celdas(D, coh, c.H_CORTO, True)
    trat_ff, g_ff = c._cohorte_falsa_fecha(D, coh)
    cel_ff = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_ff, g_por_tratado=g_ff)
    trat_fd, g_fd = c._cohorte_falsa_distancia(D, coh, c.H_CORTO)
    cel_fd = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_fd, g_por_tratado=g_fd)
    trat_nt, g_nt = c._cohorte_nunca_tratados(D, coh)
    cel_nt = c.celdas(D, coh, c.H_CORTO, False, tratados=trat_nt, g_por_tratado=g_nt)
    cel_d1b = c.celdas_d1b(D, coh)
    wells = []
    for grupo in [cel_pri, cel_s1, cel_ff, cel_fd, cel_nt, cel_d1b]:
        for ce in grupo:
            wells.append(ce["tratados"])
            wells.append(ce["controles"])
    wells = np.unique(np.concatenate(wells)) if wells else np.zeros(0, dtype=np.int64)
    W = c._pesos_bloques(D, wells, c.REPS if reps is None else reps, rng)

    d2 = c.diseno_d2(D, W, cel_pri, cel_ff, cel_fd)
    plac = {"previo": d2["previo"], "fecha_falsa": d2["fecha_falsa"], "distancia_falsa": d2["distancia_falsa"]}
    rotos = [n for n, rr in plac.items()
             if c.rompe(float(rr["est"]), float(rr["ic_bajo"]), float(rr["ic_alto"]), c.UMBRAL_ROTURA_AGUA)]
    r = d2["r"]
    if con_cierre:
        cierre = c.placebo_cierre(D, W)
        ce, cb, ca = float(cierre["est"]), float(cierre["ic_bajo"]), float(cierre["ic_alto"])
    else:
        cierre, ce, cb, ca = None, 0.0, 0.0, 0.0
    ver = c.veredicto_d2(int(r["n_tratados"]), bool(rotos), ce, cb, ca, float(r["est"]), float(r["ic_bajo"]))
    return {"n_tratados": int(r["n_tratados"]), "att": float(r["est"]), "ic_bajo": float(r["ic_bajo"]),
            "ic_alto": float(r["ic_alto"]), "placebos_rotos": rotos, "con_cierre": bool(con_cierre),
            "cierre": None if cierre is None else {"est": ce, "ic_bajo": cb, "ic_alto": ca},
            "veredicto": ver}


def _cifra(x, n_pozos: int, dec: int = 1):
    """Una cifra agrupada, o el texto de supresion si sale de menos de MIN_POZOS_CIFRA pozos."""
    if n_pozos < MIN_POZOS_CIFRA:
        return f"menos de {MIN_POZOS_CIFRA} pozos"
    x = float(x)
    if not np.isfinite(x):
        return None
    return int(round(x)) if dec == 0 else round(x, dec)


def armar_tarjeta(res: dict) -> dict:
    """Tarjeta del operador: un dict cuyas claves son exactamente CAMPOS_TARJETA y cuyos valores son cifras agrupadas.

    `res` trae "brecha" (el resultado de pipeline.local.brecha) y "d2" (el de d2_local, o None si el mensual no trae
    agua_m3). Sin agua la tarjeta dice SIN_AGUA en las cifras de agua. Ningun id, coordenada, nombre ni fecha entra."""
    br = res["brecha"]["k1"]
    d2 = res.get("d2")
    notas = []
    pozos_br = min(int(br["n_cercanos"]), int(br["n_controles"]), int(br["pads_hijo_cercanos"]))
    if pozos_br < MIN_POZOS_CIFRA:
        b, bic = _cifra(0, pozos_br), _cifra(0, pozos_br)
    else:
        b = _cifra(br["brecha"] * 100, pozos_br)
        bic = [_cifra(br["ic_bajo"] * 100, pozos_br), _cifra(br["ic_alto"] * 100, pozos_br)]
    if d2 is None:
        eventos, dw, dic, ver_agua = SIN_AGUA, SIN_AGUA, SIN_AGUA, SIN_AGUA
        notas.append("El mensual no trae agua_m3: no se calculó el corte de agua.")
    else:
        eventos = _cifra(d2["n_tratados"], d2["n_tratados"], 0)
        dw = _cifra(d2["att"], d2["n_tratados"])
        dic = (dw if isinstance(dw, str) else [_cifra(d2["ic_bajo"], d2["n_tratados"]),
                                               _cifra(d2["ic_alto"], d2["n_tratados"])])
        ver_agua = d2["veredicto"]
        if not d2["con_cierre"]:
            notas.append(f"{SIN_CIERRE}: el mensual no trae dias_produccion, así que el veredicto se calculó sin ella.")
        if d2["placebos_rotos"]:
            notas.append("Placebos rotos: " + ", ".join(n.replace("_", " ") for n in d2["placebos_rotos"]) + ".")
    notas.append("Cifras agrupadas: ningún pozo, pad, coordenada ni fecha sale en esta tarjeta; una cifra de menos de "
                 f"{MIN_POZOS_CIFRA} pozos se suprime.")
    notas.append("Si el operador ya figura en el dato público del estudio, esta tarjeta no es una replicación "
                 "independiente del estudio público.")
    return {"version": _version(), "eventos": eventos, "brecha_mes1": b, "brecha_mes1_ic": bic, "dw_pp": dw,
            "dw_ic": dic, "veredicto_petroleo": "descriptivo", "veredicto_agua": ver_agua, "notas": notas}


def _txt(x) -> str:
    if isinstance(x, list):
        return " a ".join(_txt(v) for v in x)
    if x is None:
        return "sin cifra"
    return str(x).replace(".", ",") if isinstance(x, float) else str(x)


def tarjeta_md(t: dict) -> str:
    """La tarjeta en Markdown, en español con voseo al lector. Solo muestra lo que trae el dict."""
    lin = ["# Tarjeta del operador", "",
           "Esta tarjeta resume, con cifras agrupadas, lo que el estudio mide sobre las tablas que pasaste. "
           "Podés compartirla sin compartir los datos.", "",
           f"- Versión del código: {t['version']}",
           f"- Eventos con dato de agua: {_txt(t['eventos'])}",
           f"- Brecha del mes 1 en petróleo, en puntos: {_txt(t['brecha_mes1'])} (IC 95%: {_txt(t['brecha_mes1_ic'])}). "
           f"Lectura: {t['veredicto_petroleo']}.",
           f"- Cambio del corte de agua (dW), en puntos porcentuales: {_txt(t['dw_pp'])} (IC 95%: {_txt(t['dw_ic'])}).",
           f"- Veredicto del corte de agua: {t['veredicto_agua']}.", "", "## Notas"]
    lin += [f"- {n}" for n in t["notas"]]
    return "\n".join(lin) + "\n"


def escribir_tarjeta(out, t: dict) -> None:
    """Escribe tarjeta.json y tarjeta.md en la carpeta de salida."""
    out = Path(out)
    (out / "tarjeta.json").write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
    (out / "tarjeta.md").write_text(tarjeta_md(t))
