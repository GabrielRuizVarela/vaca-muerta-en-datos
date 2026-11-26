"""Question -> one typed operation, chosen by a local model. The model never writes SQL or numbers.

The model sees the operation catalog (names, descriptions, JSON schemas) and answers with
{"op": ..., "args": {...}}, {"calls": [{"op": ..., "args": {...}}, {"op": ..., "args": {...}}]}
(two calls at most, for a question that needs two different measurements) or
{"op": "abstener", "motivo": ...}. Arguments are validated by pydantic; on a validation or lookup
error the model gets the error once and may correct itself.
The final answer is each operation's own sentence plus its provenance.

Model: any OpenAI-compatible endpoint. Default is the offline llama.cpp router on this machine
(VM_LLM_URL, VM_LLM_MODEL). For a measurement with another model (for example the local free pool proxy)
set VM_LLM_URL, VM_LLM_MODEL and, if the endpoint needs one, VM_LLM_KEY; the eval records the model it used.
Only public-data questions and the operation catalog are sent, never the warehouse.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Callable

from pydantic import ValidationError

from agente.ops import REGISTRO, ErrorOperacion, conectar, ejecutar

LLM = Callable[[list[dict]], str]
URL = os.environ.get("VM_LLM_URL", "http://127.0.0.1:8080/v1")
MODELO = os.environ.get("VM_LLM_MODEL", "qwen3.5-35b-a3b-uncensored")


def _firma(op) -> str:
    props = op.args.model_json_schema().get("properties", {})
    partes = []
    for n, p in props.items():
        tipo = "|".join(x.get("type", "") for x in p["anyOf"]) if "anyOf" in p else p.get("type", "")
        if "enum" in p:
            tipo = "|".join(map(str, p["enum"]))
        rango = f" {p['minimum']}..{p['maximum']}" if "minimum" in p else ""
        desc = f": {p['description']}" if p.get("description") else ""
        partes.append(f"    {n} ({tipo}{rango}, por defecto {json.dumps(p.get('default'), ensure_ascii=False)}){desc}"
                      if "default" in p else f"    {n} ({tipo}{rango}, obligatorio){desc}")
    return f"- {op.nombre}: {op.descripcion}\n" + "\n".join(partes)


MAX_LLAMADAS = 2


def sistema(ultimo_mes: str) -> str:
    ops = "\n".join(_firma(o) for o in REGISTRO.values())
    return f"""Elegís una operación (o dos, si hace falta) para responder preguntas sobre datos públicos de Vaca Muerta (Argentina).
Último mes con datos: {ultimo_mes}. Meses en formato AAAA-MM. Si la pregunta no dice el mes, dejá "mes" vacío.
Operaciones:
{ops}

Respondé SOLO un objeto JSON: {{"op": "<nombre>", "args": {{...}}}}.
Solo si la pregunta necesita de verdad dos mediciones distintas, respondé {{"calls": [{{"op": "<nombre>", "args": {{...}}}}, {{"op": "<nombre>", "args": {{...}}}}]}}.
Máximo dos llamadas; si una operación alcanza, usá una sola.
Si ninguna operación responde la pregunta (precios, costos, pronósticos, salarios, datos que no están), respondé
{{"op": "abstener", "motivo": "<por qué>"}}. No inventes valores ni operaciones.

Ejemplos:
P: ¿Cuántos pozos activos tenía Shell en marzo de 2024?
{{"op": "produccion_vm", "args": {{"operador": "Shell", "mes": "2024-03"}}}}
P: ¿Cuántos eventos registra el pozo YPF.Nq.LLL-586 y qué dice el libro sobre la brecha al mes 1?
{{"calls": [{{"op": "eventos_pozo", "args": {{"sigla": "YPF.Nq.LLL-586"}}}}, {{"op": "libro_hallazgos", "args": {{"id": "brecha_mes1"}}}}]}}
P: ¿Qué tan rápido declinan los pozos de Tecpetrol según el clima?
{{"op": "abstener", "motivo": "No hay datos de clima."}}"""


def llm_local(url: str = URL, modelo: str = MODELO, timeout: int = 180) -> LLM:
    def llamar(mensajes: list[dict]) -> str:
        body = {"model": modelo, "messages": mensajes, "temperature": 0, "max_tokens": 400,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False}}  # routing needs no chain of thought
        cabeceras = {"Content-Type": "application/json"}
        if os.environ.get("VM_LLM_KEY"):
            cabeceras["Authorization"] = f"Bearer {os.environ['VM_LLM_KEY']}"
        req = urllib.request.Request(f"{url}/chat/completions", data=json.dumps(body).encode(), headers=cabeceras)
        for espera in (5, 10, 20, 30, 30, 45, 60, None):  # a shared endpoint can answer 429 or 5xx for a moment
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read())["choices"][0]["message"]["content"]
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                if isinstance(e, urllib.error.HTTPError) and b"empty answer" in e.read():
                    return ""  # the model answered nothing (a model failure, scored as such), not an outage
                if espera is None or getattr(e, "code", 503) not in (429, 499, 500, 502, 503, 504):
                    raise
                time.sleep(espera)
    return llamar


def _json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError("la respuesta no contiene JSON")
    d = json.loads(m.group(0))
    if not isinstance(d, dict) or ("op" not in d and "calls" not in d):
        raise ValueError("falta 'op' o 'calls'")
    if "op" in d:
        d.setdefault("args", {})
    return d


def _llamadas(d: dict) -> list[dict]:
    """The calls of an answer: the single form {"op", "args"} or {"calls": [...]} with at most MAX_LLAMADAS."""
    if "calls" not in d:
        return [d]
    calls = d["calls"]
    if not isinstance(calls, list) or not calls:
        raise ValueError("'calls' tiene que ser una lista con al menos una llamada")
    if len(calls) > MAX_LLAMADAS:
        raise ErrorOperacion(f"Hay {len(calls)} llamadas y el máximo es {MAX_LLAMADAS}. "
                             "Quedate con las dos mediciones que la pregunta necesita.")
    for c in calls:
        if not isinstance(c, dict) or "op" not in c:
            raise ValueError("cada llamada necesita 'op'")
        c.setdefault("args", {})
    return calls


def _ejecutar_llamada(con, c: dict, donde: str) -> dict:
    if c["op"] == "abstener":
        raise ErrorOperacion(f"{donde}abstener va solo, no dentro de 'calls'.")
    if c["op"] not in REGISTRO:
        raise ErrorOperacion(f"{donde}La operación '{c['op']}' no existe.")
    try:
        return ejecutar(con, c["op"], c["args"])
    except (ValueError, ValidationError, KeyError) as e:
        if not donde:
            raise
        raise ErrorOperacion(f"{donde}{e}") from e


def elegir(con, pregunta: str, llm: LLM, reintentos: int = 1) -> dict:
    """Returns {"op", "args", "resultado"} for one call that validated and ran, or {"op": "abstener"} / {"op": "error"}.

    With two calls, "op" and "args" are lists and "resultado" is absent. Either way "resultados" lists every result."""
    ultimo = con.execute("select strftime(mes, '%Y-%m') from ultimo_mes").fetchall()[0][0]
    msgs = [{"role": "system", "content": sistema(ultimo)}, {"role": "user", "content": pregunta}]
    for intento in range(reintentos + 1):
        crudo = llm(msgs)
        try:
            d = _json(crudo)
            if d.get("op") == "abstener":
                return {"op": "abstener", "args": {}, "motivo": d.get("motivo", ""), "intentos": intento + 1}
            llamadas = _llamadas(d)
            resultados = [_ejecutar_llamada(con, c, f"Llamada {i}: " if len(llamadas) > 1 else "")
                          for i, c in enumerate(llamadas, 1)]
            if len(resultados) == 1:
                r = resultados[0]
                return {"op": r["op"], "args": r["args"], "resultado": r, "resultados": resultados, "intentos": intento + 1}
            return {"op": [r["op"] for r in resultados], "args": [r["args"] for r in resultados],
                    "resultados": resultados, "intentos": intento + 1}
        except (ValueError, ValidationError, ErrorOperacion, KeyError) as e:
            error = str(e)[:600]
            msgs += [{"role": "assistant", "content": crudo},
                     {"role": "user", "content": f"Error: {error}\nCorregí la operación o abstenete. Solo JSON."}]
    return {"op": "error", "args": {}, "motivo": error, "intentos": reintentos + 1}


def _con_fuente(r: dict) -> str:
    f = r["fuente"]
    sha = ", ".join(f"{k} {v}" for k, v in f["sha"].items())
    return (f"{r['texto']}\n\nFuente: {', '.join(f['tablas'])}; datos a {f['datos_a']}; archivos {sha}. "
            f"Operación: {r['op']} {json.dumps(r['args'], ensure_ascii=False)}")


def responder(con, pregunta: str, llm: LLM) -> str:
    e = elegir(con, pregunta, llm)
    if e["op"] in ("abstener", "error"):
        return f"No puedo responder eso con estos datos. {e.get('motivo', '')}".strip()
    return "\n\n".join(_con_fuente(r) for r in e["resultados"])


if __name__ == "__main__":
    print(responder(conectar(), " ".join(sys.argv[1:]) or "¿Cuánto petróleo produce Vaca Muerta?", llm_local()))
