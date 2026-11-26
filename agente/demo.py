"""Demo del agente sin servidor de modelo: 5 preguntas, una por tipo, con operación, argumentos, respuesta y cita.

  uv run python -m agente.demo            # enrutado según la evaluación registrada, sin modelo
  uv run python -m agente.demo --modelo   # enruta con VM_LLM_URL y VM_LLM_MODEL (si están definidos)

El enrutado (qué operación y qué argumentos) sale de la última evaluación registrada en
agente/eval/resultados/holdout.json, solo para preguntas que el modelo enrutó bien; la operación se ejecuta
en vivo contra el warehouse, así que las cifras y la cita son las de hoy. La salida no tiene marcas de hora
y es idéntica entre corridas.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from agente.eval.run import PREGUNTAS, RESULTADOS, cargar
from agente.ops import REGISTRO, conectar, ejecutar

# Una pregunta reservada por tipo. Todas fueron enrutadas bien en la evaluación registrada.
SELECCION = [
    ("producción", "holdout-02"),
    ("consulta de eventos", "holdout-17"),
    ("costo de interferencia", "holdout-24"),
    ("robustez", "holdout-26"),
    ("abstención", "holdout-16"),
]

# Lo que los datos no contienen, para la pregunta de abstención (la evaluación solo registra que abstuvo).
NO_CONTIENEN = ("Los datos son históricos (producción mensual declarada, fracturas y eventos de pozo) "
                "y no incluyen pronósticos, precios, tarifas ni datos laborales.")

AYUDA_MODELO = "Falta definir VM_LLM_URL y VM_LLM_MODEL para usar --modelo; sin ellas, corré el demo sin la opción."


def _registrado() -> dict:
    """Recorded routing by question id, only for rows the model got right."""
    f = RESULTADOS / "holdout.json"
    if not f.exists():
        return {}
    return {x["id"]: x for x in json.loads(f.read_text())["filas"] if x["correcto"]}


def _ruta_esperada(item: dict) -> dict:
    e = item["esperado"]
    return {"op": e["op"], "args": e.get("args", {})}


def _cita(r: dict) -> str:
    f = r["fuente"]
    sha = ", ".join(f"{k} {f['sha'][k]}" for k in sorted(f["sha"]))
    return f"tablas {', '.join(sorted(f['tablas']))}; datos a {f['datos_a']}; hash del crudo {sha}"


def _primera_frase(texto: str) -> str:
    """The operation's text up to its first sentence; the full text is what the agent returns."""
    return texto.split(". ")[0].rstrip(".") + "."


def _bloque(n: int, tipo: str, pregunta: str, resultados: list[dict] | None, motivo: str) -> str:
    lineas = [f"[{n}] {tipo}", f"Pregunta: {pregunta}"]
    if resultados is None:
        lineas += ["Operación: abstener (ninguna operación del catálogo responde esto)",
                   "Argumentos: {}",
                   f"Respuesta: No puedo responder eso con estos datos. {motivo}",
                   "Cita: ninguna, no se ejecutó ninguna operación y no se informa ninguna cifra"]
    else:
        for r in resultados:
            assert r["op"] in REGISTRO
            lineas += [f"Operación: {r['op']}",
                       f"Argumentos: {json.dumps(r['args'], ensure_ascii=False, sort_keys=True)}",
                       f"Respuesta: {_primera_frase(r['texto'])}",
                       f"Cita: {_cita(r)}"]
    return "\n".join(lineas)


def demo(con, modelo: bool = False) -> str:
    items = {i["id"]: i for i in cargar("todo")}
    registrado = _registrado()
    desde_eval = False
    bloques = []
    for n, (tipo, id_) in enumerate(SELECCION, 1):
        item = items[id_]
        if modelo:
            from agente.router import elegir, llm_local
            e = elegir(con, item["pregunta"], llm_local(os.environ["VM_LLM_URL"], os.environ["VM_LLM_MODEL"]))
            if e["op"] in ("abstener", "error"):
                bloques.append(_bloque(n, tipo, item["pregunta"], None, e.get("motivo", "")))
            else:
                bloques.append(_bloque(n, tipo, item["pregunta"], e["resultados"], ""))
            continue
        ruta = registrado.get(id_)
        if ruta is None:
            ruta, desde_eval = _ruta_esperada(item), True
        if ruta["op"] == "abstener":
            bloques.append(_bloque(n, tipo, item["pregunta"], None, NO_CONTIENEN))
        else:
            bloques.append(_bloque(n, tipo, item["pregunta"], [ejecutar(con, ruta["op"], ruta["args"])], ""))
    if modelo:
        enrutado = f"enrutado por el modelo {os.environ['VM_LLM_MODEL']}"
    elif desde_eval:
        enrutado = "enrutado según la evaluación registrada, sin modelo (operación y argumentos esperados de las preguntas)"
    else:
        enrutado = "enrutado según la evaluación registrada, sin modelo"
    datos = con.execute("select strftime(mes, '%Y-%m') from ultimo_mes").fetchall()[0][0]
    cabecera = (f"Demo del agente de Vaca Muerta: 5 preguntas, una por tipo\n"
                f"Datos a {datos}; {enrutado}; la operación se ejecuta en vivo contra el warehouse\n"
                f"Preguntas de agente/eval/{PREGUNTAS.name}, rutas de agente/eval/resultados/holdout.json")
    return cabecera + "\n\n" + "\n\n".join(bloques)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modelo", action="store_true", help="enrutar con VM_LLM_URL y VM_LLM_MODEL")
    a = ap.parse_args()
    if a.modelo and not (os.environ.get("VM_LLM_URL") and os.environ.get("VM_LLM_MODEL")):
        print(AYUDA_MODELO)
        return 2
    print(demo(conectar(), a.modelo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
