"""docs/arquitectura.md nombra archivos, módulos y opciones del repositorio. Si uno deja de existir, la página miente."""
from __future__ import annotations

import re

from pipeline.ingest import ROOT

PAGINA = ROOT / "docs" / "arquitectura.md"
BLOQUE = re.compile(r"```.*?```", re.S)


def _texto() -> str:
    return PAGINA.read_text(encoding="utf-8")


def _entre_comillas() -> list[str]:
    return re.findall(r"`([^`]+)`", BLOQUE.sub("", _texto()))


def test_cada_modulo_y_cada_ruta_que_nombra_la_pagina_existe():
    modulos = set(re.findall(r"\bpipeline\.[a-z_]+", _texto()))
    rutas = {r for r in _entre_comillas() if "/" in r and " " not in r}
    assert len(modulos) >= 10 and len(rutas) >= 8                      # la búsqueda encuentra algo que comprobar
    sin_modulo = [m for m in modulos if not ((ROOT / m.replace(".", "/")).with_suffix(".py").exists()
                                             or (ROOT / m.replace(".", "/")).is_dir())]
    sin_ruta = [r for r in rutas if not (ROOT / r).exists()]
    assert sin_modulo == [] and sin_ruta == []


def test_cada_opcion_y_cada_paso_que_nombra_la_pagina_es_de_run_all():
    from pipeline import run_all

    codigo = (ROOT / "pipeline" / "run_all.py").read_text(encoding="utf-8")
    opciones = {o for o in _entre_comillas() if o.startswith("--")}
    assert opciones >= {"--list", "--only", "--skip", "--with-ingest", "--with-colorado"}
    assert [o for o in opciones if f'"{o}"' not in codigo] == []
    pasos = re.search(r"un módulo por pregunta \((.*?) y los demás pasos de run_all\)", _texto()).group(1)
    nombres = {p.nombre for p in run_all.PASOS}
    assert [p for p in re.split(r",\s*", pasos) if p not in nombres] == []
    assert "demo:" in (ROOT / "Makefile").read_text(encoding="utf-8")
