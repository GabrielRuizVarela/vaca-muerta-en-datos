"""Question -> one typed operation, chosen by a local model. The model never writes SQL or numbers.

The model sees the operation catalog (names, descriptions, JSON schemas) and answers with
{"op": ..., "args": {...}} or {"op": "abstener", "motivo": ...}. Arguments are validated by
pydantic; on a validation or lookup error the model gets the error once and may correct itself.
The final answer is the operation's own sentence plus its provenance.

Model: any OpenAI-compatible endpoint. Default is the offline llama.cpp router on this machine
(VM_LLM_URL, VM_LLM_MODEL). No cloud inference.
"""
from __future__ import annotations

import json
import os
import re
import sys
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


def sistema(ultimo_mes: str) -> str:
    ops = "\n".join(_firma(o) for o in REGISTRO.values())
    return f"""Elegís UNA operación para responder preguntas sobre datos públicos de Vaca Muerta (Argentina).
Último mes con datos: {ultimo_mes}. Meses en formato AAAA-MM. Si la pregunta no dice el mes, dejá "mes" vacío.
Operaciones:
{ops}

Respondé SOLO un objeto JSON: {{"op": "<nombre>", "args": {{...}}}}.
Si ninguna operación responde la pregunta (precios, costos, pronósticos, salarios, datos que no están), respondé
{{"op": "abstener", "motivo": "<por qué>"}}. No inventes valores ni operaciones.

Ejemplos:
P: ¿Cuántos pozos activos tenía Shell en marzo de 2024?
{{"op": "produccion_vm", "args": {{"operador": "Shell", "mes": "2024-03"}}}}
P: ¿Qué tan rápido declinan los pozos de Tecpetrol según el clima?
{{"op": "abstener", "motivo": "No hay datos de clima."}}"""


def llm_local(url: str = URL, modelo: str = MODELO, timeout: int = 180) -> LLM:
    def llamar(mensajes: list[dict]) -> str:
        body = {"model": modelo, "messages": mensajes, "temperature": 0, "max_tokens": 300,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False}}  # routing needs no chain of thought
        req = urllib.request.Request(f"{url}/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    return llamar


def _json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError("la respuesta no contiene JSON")
    d = json.loads(m.group(0))
    if not isinstance(d, dict) or "op" not in d:
        raise ValueError("falta 'op'")
    d.setdefault("args", {})
    return d


def elegir(con, pregunta: str, llm: LLM, reintentos: int = 1) -> dict:
    """Returns {"op", "args"} that validated and ran, or {"op": "abstener"} / {"op": "error"}, plus "resultado"."""
    ultimo = con.execute("select strftime(mes, '%Y-%m') from ultimo_mes").fetchall()[0][0]
    msgs = [{"role": "system", "content": sistema(ultimo)}, {"role": "user", "content": pregunta}]
    for intento in range(reintentos + 1):
        crudo = llm(msgs)
        try:
            d = _json(crudo)
            if d["op"] == "abstener":
                return {"op": "abstener", "args": {}, "motivo": d.get("motivo", ""), "intentos": intento + 1}
            if d["op"] not in REGISTRO:
                raise ErrorOperacion(f"La operación '{d['op']}' no existe.")
            res = ejecutar(con, d["op"], d["args"])
            return {"op": d["op"], "args": res["args"], "resultado": res, "intentos": intento + 1}
        except (ValueError, ValidationError, ErrorOperacion, KeyError) as e:
            error = str(e)[:600]
            msgs += [{"role": "assistant", "content": crudo},
                     {"role": "user", "content": f"Error: {error}\nCorregí la operación o abstenete. Solo JSON."}]
    return {"op": "error", "args": {}, "motivo": error, "intentos": reintentos + 1}


def responder(con, pregunta: str, llm: LLM) -> str:
    e = elegir(con, pregunta, llm)
    if e["op"] in ("abstener", "error"):
        return f"No puedo responder eso con estos datos. {e.get('motivo', '')}".strip()
    r = e["resultado"]
    f = r["fuente"]
    sha = ", ".join(f"{k} {v}" for k, v in f["sha"].items())
    return f"{r['texto']}\n\nFuente: {', '.join(f['tablas'])}; datos a {f['datos_a']}; archivos {sha}. Operación: {e['op']} {json.dumps(e['args'], ensure_ascii=False)}"


if __name__ == "__main__":
    print(responder(conectar(), " ".join(sys.argv[1:]) or "¿Cuánto petróleo produce Vaca Muerta?", llm_local()))
