"""One command for the whole chain, with timings.

  uv run python -m pipeline.run_all                  # build, costo, robustez, [validacion], placebo, wiki, report, replay, claims
  uv run python -m pipeline.run_all --with-ingest    # also download first (needs the Secretaria server)
  uv run python -m pipeline.run_all --only build,wiki
  uv run python -m pipeline.run_all --skip report,replay
  uv run python -m pipeline.run_all --list

Each step runs as `python -m pipeline.<modulo>` in its own process. The chain stops at the first failure,
prints a table of step, seconds and status, and exits 1. A step whose module cannot be imported (for
example pipeline.validacion before it exists) is left out of the chain.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Paso:
    nombre: str
    modulo: str
    opcional: bool = False      # left out when the module is not importable
    solo_con_flag: bool = False  # only with --with-ingest


PASOS: list[Paso] = [
    Paso("ingest", "pipeline.ingest", solo_con_flag=True),
    Paso("build", "pipeline.build"),
    Paso("costo", "pipeline.costo"),
    Paso("robustez", "pipeline.robustez"),
    Paso("validacion", "pipeline.validacion", opcional=True),
    Paso("placebo", "pipeline.placebo"),
    Paso("wiki", "pipeline.wiki"),
    Paso("report", "pipeline.report"),
    Paso("replay", "pipeline.replay"),
    Paso("claims", "pipeline.claims"),
]


def disponible(p: Paso) -> bool:
    try:
        return importlib.util.find_spec(p.modulo) is not None
    except (ImportError, ValueError):
        return False


def seleccionar(pasos: list[Paso], con_ingest: bool = False, solo: list[str] | None = None,
                omitir: list[str] | None = None) -> list[Paso]:
    """The steps to run, in chain order. Raises SystemExit for an unknown name in solo / omitir."""
    nombres = {p.nombre for p in pasos}
    for n in (solo or []) + (omitir or []):
        if n not in nombres:
            raise SystemExit(f"paso desconocido: {n} (disponibles: {', '.join(sorted(nombres))})")
    out = []
    for p in pasos:
        if solo is not None:
            if p.nombre not in solo:
                continue
        elif p.solo_con_flag and not con_ingest:
            continue
        if omitir and p.nombre in omitir:
            continue
        if p.opcional and not disponible(p):
            continue
        out.append(p)
    return out


def ejecutar(p: Paso) -> int:
    return subprocess.run([sys.executable, "-m", p.modulo], cwd=ROOT).returncode


def correr(pasos: list[Paso], ejecutor=None) -> list[tuple[str, float, str]]:
    """Runs steps in order, stops at the first non-zero exit. Returns (nombre, segundos, estado) per step run."""
    ejecutor = ejecutor or ejecutar
    filas = []
    for p in pasos:
        print(f"\n=== {p.nombre} ({p.modulo}) ===", flush=True)
        t0 = time.perf_counter()
        rc = ejecutor(p)
        dt = time.perf_counter() - t0
        filas.append((p.nombre, dt, "OK" if rc == 0 else f"FALLO (exit {rc})"))
        if rc != 0:
            break
    return filas


def tabla(filas: list[tuple[str, float, str]], pendientes: list[str]) -> str:
    w = max([len(f[0]) for f in filas] + [len(n) for n in pendientes] + [5])
    out = [f"{'paso':<{w}}  {'segundos':>8}  estado"]
    out += [f"{n:<{w}}  {s:>8.1f}  {e}" for n, s, e in filas]
    out += [f"{n:<{w}}  {'-':>8}  no corrio" for n in pendientes]
    out.append(f"{'total':<{w}}  {sum(f[1] for f in filas):>8.1f}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.run_all", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-ingest", action="store_true", help="also run pipeline.ingest first")
    ap.add_argument("--only", help="comma-separated steps to run (chain order is kept)")
    ap.add_argument("--skip", help="comma-separated steps to leave out")
    ap.add_argument("--list", action="store_true", help="print the steps and exit")
    a = ap.parse_args(argv)
    solo = [s for s in a.only.split(",") if s] if a.only else None
    omitir = [s for s in a.skip.split(",") if s] if a.skip else None
    if a.list:
        for p in PASOS:
            nota = "con --with-ingest" if p.solo_con_flag else ("si el modulo existe" if p.opcional else "")
            estado = "disponible" if disponible(p) else "no disponible"
            print(f"{p.nombre:<12} {p.modulo:<22} {estado:<14} {nota}")
        return 0
    pasos = seleccionar(PASOS, a.with_ingest, solo, omitir)
    if not pasos:
        print("nada que correr")
        return 0
    filas = correr(pasos)
    pendientes = [p.nombre for p in pasos[len(filas):]]
    print("\n" + tabla(filas, pendientes))
    if any(e != "OK" for _, _, e in filas):
        print(f"\nCadena detenida en el paso '{filas[-1][0]}'. Corregir y reanudar con --only {','.join([filas[-1][0]] + pendientes)}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
