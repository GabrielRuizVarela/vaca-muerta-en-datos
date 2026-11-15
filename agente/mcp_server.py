"""MCP server: one read-only tool per typed operation.

Run: `uv run python -m agente.mcp_server` (stdio). Any MCP client (Claude Desktop, Claude Code,
an IDE) can then ask questions about Vaca Muerta; it only ever sees the typed tools, never SQL.
"""
from __future__ import annotations

import inspect
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from agente.ops import REGISTRO, conectar, ejecutar

INSTRUCCIONES = (
    "Datos abiertos de la Secretaría de Energía sobre Vaca Muerta: producción por pozo y fracturas. "
    "Cada herramienta devuelve 'texto' (respuesta lista para citar), 'filas' y 'fuente' (tablas, mes de datos, sha del "
    "archivo crudo). Citá la fuente. Si ninguna herramienta responde la pregunta, decilo: no estimes."
)


def _tipo(f):
    # Keep description and constraints (ge/le/pattern) in the tool's JSON schema.
    meta = [m for m in f.metadata] + ([Field(description=f.description)] if f.description else [])
    return Annotated[(f.annotation, *meta)] if meta else f.annotation


def _herramienta(nombre: str):
    op = REGISTRO[nombre]

    def fn(**kwargs) -> dict:
        con = conectar()
        try:
            return ejecutar(con, nombre, {k: v for k, v in kwargs.items() if v is not None})
        finally:
            con.close()

    # Expose the pydantic fields as the tool's typed parameters.
    params = [inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, default=f.default if not f.is_required() else inspect.Parameter.empty,
                                annotation=_tipo(f))
              for n, f in op.args.model_fields.items()]
    fn.__signature__ = inspect.Signature(params, return_annotation=dict)
    fn.__annotations__ = {**{n: _tipo(f) for n, f in op.args.model_fields.items()}, "return": dict}
    fn.__name__ = nombre
    return fn, op.descripcion


def crear_servidor() -> MCPServer:
    srv = MCPServer("vaca-muerta-datos", instructions=INSTRUCCIONES)
    for nombre in REGISTRO:
        fn, desc = _herramienta(nombre)
        srv.add_tool(fn, name=nombre, description=desc,
                     annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    return srv


if __name__ == "__main__":
    crear_servidor().run()
