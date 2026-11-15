"""Accuracy eval for the question router.

Each item has a question and the expected operation call (or an expected abstention). The
expected *answer* is never stored: it is computed by running the expected call on the current
warehouse, so the eval stays valid after every weekly data refresh. A model answer is correct
when its own call runs and returns the same value. Equivalent spellings ("ypf", "YPF") count.

  uv run python -m agente.eval.run --split dev        # iterate on prompts here
  uv run python -m agente.eval.run --split holdout    # report this one, do not tune on it
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

from agente.ops import conectar, ejecutar
from agente.router import LLM, MODELO, elegir, llm_local

PREGUNTAS = Path(__file__).parent / "preguntas.jsonl"
RESULTADOS = Path(__file__).parent / "resultados"


def cargar(split: str | None = None) -> list[dict]:
    items = [json.loads(l) for l in PREGUNTAS.read_text().splitlines() if l.strip()]
    return [i for i in items if split in (None, "todo", i["split"])]


def iguales(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return a == b


def puntuar(con, item: dict, elegido: dict) -> dict:
    esperado = item["esperado"]
    abstuvo = elegido["op"] in ("abstener", "error")
    if esperado["op"] == "abstener":
        return {"correcto": elegido["op"] == "abstener", "tipo": "abstencion"}
    if abstuvo:
        return {"correcto": False, "tipo": "respuesta", "fallo": f"no respondió ({elegido['op']})"}
    verdad = ejecutar(con, esperado["op"], esperado["args"])["valor"]
    ok = iguales(elegido["resultado"]["valor"], verdad)
    return {"correcto": ok, "tipo": "respuesta",
            **({} if ok else {"fallo": f"esperado {esperado['op']} {esperado['args']}, eligió {elegido['op']} {elegido['args']}"})}


def evaluar(con, items: list[dict], llm: LLM) -> dict:
    filas = []
    for it in items:
        t = time.monotonic()
        e = elegir(con, it["pregunta"], llm)
        p = puntuar(con, it, e)
        filas.append({"id": it["id"], "pregunta": it["pregunta"], "op": e["op"], "args": e["args"],
                      "intentos": e["intentos"], "segundos": round(time.monotonic() - t, 1), **p})
    resp = [f for f in filas if f["tipo"] == "respuesta"]
    abst = [f for f in filas if f["tipo"] == "abstencion"]
    falsas_abst = sum(1 for f in resp if f["op"] in ("abstener", "error"))
    return {
        "n": len(filas),
        "exactitud": sum(f["correcto"] for f in filas) / len(filas),
        "exactitud_respuestas": sum(f["correcto"] for f in resp) / len(resp) if resp else None,
        "abstencion_correcta": sum(f["correcto"] for f in abst) / len(abst) if abst else None,
        "abstenciones_indebidas": falsas_abst,
        "corregidas_en_reintento": sum(1 for f in filas if f["correcto"] and f["intentos"] > 1),
        "filas": filas,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "holdout", "todo"])
    a = ap.parse_args()
    con = conectar()
    r = evaluar(con, cargar(a.split), llm_local())
    datos = con.execute("select strftime(mes, '%Y-%m') from ultimo_mes").fetchall()[0][0]
    r = {"split": a.split, "modelo": MODELO, "datos_a": datos, **r}
    RESULTADOS.mkdir(exist_ok=True)
    (RESULTADOS / f"{a.split}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str) + "\n")
    for f in r["filas"]:
        if not f["correcto"]:
            print(f"FALLA {f['id']}: {f['pregunta']} -> {f.get('fallo', f['op'])}")
    print(f"{a.split}: exactitud {r['exactitud']:.0%} ({r['n']} preguntas), respuestas {r['exactitud_respuestas']:.0%}, "
          f"abstención correcta {r['abstencion_correcta']:.0%}, abstenciones indebidas {r['abstenciones_indebidas']}, "
          f"corregidas en reintento {r['corregidas_en_reintento']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
