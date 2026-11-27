"""One command for the whole chain, with timings.

  uv run python -m pipeline.run_all                  # build, carga, costo, robustez, [validacion], placebo, descomposicion, diferido, sincronia, bloques, dia_inicio, carga_anual, potencia, eje_controles, eje_exposicion, eje_parada, dosis, dosis_meses, dosis_pad, potencia_dosis, robustez_operador, dias_perdidos, golpes_mismo_mes, golpes_mismo_padre, calendario_golpes, anillo, inyeccion, hijo, hijo_celdas, gas, decision, trayectorias, alcance_rama, riesgo, dosis_geometria, mecanismo, hijo_pad, causal, causal_profundo, causal_exposicion, apilado, cota_rr, [causal_profundo_colorado], [causal_profundo_wyoming], [replicacion_wyoming], inferencia, figuras, wiki, informe, report, replay, mundo, [globo], claims
  uv run python -m pipeline.run_all --with-ingest    # also download first (needs the Secretaria server)
  uv run python -m pipeline.run_all --with-colorado  # also download and build the Colorado (DJ basin) warehouse and run its replication, dia_inicio, dias_perdidos, golpes_mismo_mes and golpes_mismo_padre there; opt-in, needs the network
  uv run python -m pipeline.run_all --only build,wiki
  uv run python -m pipeline.run_all --skip report,replay
  uv run python -m pipeline.run_all --list
  uv run python -m pipeline.run_all --muestra        # demo: build + report sobre data/muestra (sin descargas)

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
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Paso:
    nombre: str
    modulo: str
    opcional: bool = False      # left out when the module is not importable
    solo_con_flag: bool = False  # only with --with-ingest
    solo_con_colorado: bool = False  # only with --with-colorado (the Colorado replication is opt-in)
    args: tuple[str, ...] = ()   # extra command-line arguments for the module
    requiere: str = ""           # path (relative to ROOT) that must exist, or the step is left out


COLORADO_DB = "data/colorado/warehouse.duckdb"   # written by colorado_build

PASOS: list[Paso] = [
    Paso("ingest", "pipeline.ingest", solo_con_flag=True),
    Paso("build", "pipeline.build"),
    Paso("carga", "pipeline.carga"),
    Paso("costo", "pipeline.costo"),
    Paso("robustez", "pipeline.robustez"),
    Paso("validacion", "pipeline.validacion", opcional=True),
    Paso("placebo", "pipeline.placebo"),
    Paso("descomposicion", "pipeline.descomposicion"),
    Paso("diferido", "pipeline.diferido"),
    Paso("sincronia", "pipeline.sincronia"),
    Paso("bloques", "pipeline.bloques"),
    Paso("dia_inicio", "pipeline.dia_inicio"),
    Paso("carga_anual", "pipeline.carga_anual"),
    Paso("potencia", "pipeline.potencia"),
    Paso("eje_controles", "pipeline.eje_controles"),
    Paso("eje_exposicion", "pipeline.eje_exposicion"),
    Paso("eje_parada", "pipeline.eje_parada"),
    Paso("dosis", "pipeline.dosis"),
    Paso("dosis_meses", "pipeline.dosis_meses"),
    Paso("dosis_pad", "pipeline.dosis_pad"),
    Paso("potencia_dosis", "pipeline.potencia_dosis"),
    Paso("robustez_operador", "pipeline.robustez_operador"),
    Paso("replicacion_operadores", "pipeline.replicacion_operadores"),
    Paso("dias_perdidos", "pipeline.dias_perdidos"),
    Paso("golpes_mismo_mes", "pipeline.golpes_mismo_mes"),
    Paso("golpes_mismo_padre", "pipeline.golpes_mismo_padre"),
    Paso("calendario_golpes", "pipeline.calendario_golpes"),
    Paso("anillo", "pipeline.anillo"),
    Paso("inyeccion", "pipeline.inyeccion"),
    Paso("hijo", "pipeline.hijo"),
    Paso("hijo_celdas", "pipeline.hijo_celdas"),
    Paso("gas", "pipeline.gas"),
    Paso("decision", "pipeline.decision"),
    Paso("trayectorias", "pipeline.trayectorias"),
    Paso("alcance_rama", "pipeline.alcance_rama"),
    Paso("riesgo", "pipeline.riesgo"),
    Paso("dosis_geometria", "pipeline.dosis_geometria"),
    Paso("mecanismo", "pipeline.mecanismo"),
    Paso("hijo_pad", "pipeline.hijo_pad"),
    # The causal pages: wiki.py deletes causal.md / causal_profundo.md when their marts are absent, so they must run before "wiki".
    Paso("causal", "pipeline.causal"),
    Paso("causal_profundo", "pipeline.causal_profundo"),
    # Water by operator: reads causal's design and replicacion_operadores' rows (it recomputes them; it does not read their marts)
    Paso("replicacion_operadores_agua", "pipeline.replicacion_operadores_agua"),
    # D10 to D12 read causal_profundo's D4 to D6 and the trajectory pairs; the Rambachan-Roth bound reads mart_causal_veredicto
    Paso("causal_exposicion", "pipeline.causal_exposicion"),
    Paso("apilado", "pipeline.stacked"),
    Paso("cota_rr", "pipeline.cota_rr"),   # its page reads E's bound from mart_apilado
    Paso("cota_rr_condicional", "pipeline.cota_rr_condicional"),   # reads mart_cota_rr for the union side
    # Colorado warehouse first: every step below that reads it comes after colorado_build.
    Paso("colorado_ingest", "pipeline.colorado.ingest", solo_con_colorado=True),
    Paso("colorado_build", "pipeline.colorado.build", solo_con_colorado=True),
    Paso("causal_profundo_colorado", "pipeline.causal_profundo", args=("--cuenca", "colorado"),
         requiere="data/colorado/warehouse.duckdb"),
    # Wyoming: its warehouse is not built by this chain (pipeline.wyoming.ingest and .build, data/wyoming/raw); without it D9,
    # its replication and the globe are left out. The replication mart is read by inferencia (the basin family), wiki and globo.
    Paso("causal_profundo_wyoming", "pipeline.causal_profundo", args=("--cuenca", "wyoming"),
         requiere="data/wyoming/warehouse.duckdb"),
    Paso("replicacion_wyoming", "pipeline.replicacion", args=("--cuenca", "wyoming"),
         requiere="data/wyoming/warehouse.duckdb"),
    Paso("replicacion", "pipeline.replicacion", requiere="data/colorado/warehouse.duckdb"),
    Paso("dia_inicio_colorado", "pipeline.dia_inicio", args=("--cuenca", "colorado"),
         requiere="data/colorado/warehouse.duckdb"),
    Paso("dias_perdidos_colorado", "pipeline.dias_perdidos", args=("--cuenca", "colorado"),
         requiere="data/colorado/warehouse.duckdb"),
    Paso("golpes_mismo_mes_colorado", "pipeline.golpes_mismo_mes", args=("--cuenca", "colorado"),
         requiere="data/colorado/warehouse.duckdb"),
    Paso("golpes_mismo_padre_colorado", "pipeline.golpes_mismo_padre", args=("--cuenca", "colorado"),
         requiere="data/colorado/warehouse.duckdb"),
    # Holm over every verdict mart, D7 (Colorado) and D9 (Wyoming) included, so after the basin steps
    Paso("inferencia", "pipeline.inferencia"),
    Paso("figuras", "pipeline.figuras"),
    Paso("wiki", "pipeline.wiki"),
    Paso("informe", "pipeline.informe"),
    Paso("report", "pipeline.report"),
    Paso("replay", "pipeline.replay"),
    Paso("mundo", "pipeline.mundo"),
    Paso("globo", "pipeline.globo", solo_con_colorado=True,   # needs the Colorado warehouse too, built earlier with --with-colorado
         requiere="data/wyoming/warehouse.duckdb"),
    Paso("claims", "pipeline.claims"),
]


MUESTRA_DIR = ROOT / "data" / "muestra"
MUESTRA_DB = ROOT / "data" / "muestra.duckdb"
MUESTRA_SITE = ROOT / "site" / "muestra"
# Pasos que corren sobre la muestra (con sus argumentos) y los que no, con el motivo.
MUESTRA_ARGS = {
    "build": ("--raw-dir", str(MUESTRA_DIR), "--db", str(MUESTRA_DB)),
    "report": ("--db", str(MUESTRA_DB), "--out", str(MUESTRA_SITE), "--banner"),
}
MUESTRA_MOTIVO = "necesita la cuenca completa (modelos y mapas sobre miles de pozos); la muestra no los reproduce"


def pasos_muestra(pasos: list[Paso] = PASOS) -> tuple[list[Paso], dict[str, str]]:
    """(steps of the demo chain with sample arguments, {skipped step: reason})."""
    corren = [replace(p, args=MUESTRA_ARGS[p.nombre]) for p in pasos if p.nombre in MUESTRA_ARGS]
    omitidos = {p.nombre: MUESTRA_MOTIVO for p in pasos if p.nombre not in MUESTRA_ARGS and not p.solo_con_flag and not p.solo_con_colorado}
    return corren, omitidos


def disponible(p: Paso) -> bool:
    try:
        return importlib.util.find_spec(p.modulo) is not None
    except (ImportError, ValueError):
        return False


def falta_requisito(p: Paso) -> bool:
    return bool(p.requiere) and not (ROOT / p.requiere).exists()


def seleccionar(pasos: list[Paso], con_ingest: bool = False, solo: list[str] | None = None,
                omitir: list[str] | None = None, con_colorado: bool = False,
                fuera: dict[str, str] | None = None) -> list[Paso]:
    """The steps to run, in chain order. Raises SystemExit for an unknown name in solo / omitir.
    A step whose `requiere` file is missing is left out; if `fuera` is given it receives {name: reason}."""
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
        elif p.solo_con_colorado and not con_colorado:
            continue
        if omitir and p.nombre in omitir:
            continue
        if p.opcional and not disponible(p):
            continue
        # --with-colorado builds that file before these steps, unless --only leaves colorado_build out
        se_arma = con_colorado and p.requiere == COLORADO_DB and (solo is None or "colorado_build" in solo)
        if falta_requisito(p) and not se_arma:
            if fuera is not None:
                fuera[p.nombre] = f"falta {p.requiere}"
            continue
        out.append(p)
    return out


def ejecutar(p: Paso) -> int:
    return subprocess.run([sys.executable, "-m", p.modulo, *p.args], cwd=ROOT).returncode


def correr(pasos: list[Paso], ejecutor=None) -> list[tuple[str, float, str]]:
    """Runs steps in order, stops at the first non-zero exit. Returns (nombre, segundos, estado) per step run."""
    ejecutor = ejecutor or ejecutar
    filas = []
    for p in pasos:
        print(f"\n=== {p.nombre} ({p.modulo}) ===", flush=True)
        t0 = time.perf_counter()
        if falta_requisito(p):   # a step that required a file another step was to build
            print(f"[run_all] se omite {p.nombre}: falta {p.requiere}", flush=True)
            filas.append((p.nombre, 0.0, "omitido"))
            continue
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
    ap.add_argument("--with-colorado", action="store_true",
                    help="also run the Colorado steps (pipeline.colorado.ingest, .build and pipeline.replicacion; downloads from the network)")
    ap.add_argument("--only", help="comma-separated steps to run (chain order is kept)")
    ap.add_argument("--skip", help="comma-separated steps to leave out")
    ap.add_argument("--muestra", action="store_true",
                    help="demo: build y report sobre data/muestra (base data/muestra.duckdb, pagina site/muestra/index.html)")
    ap.add_argument("--list", action="store_true", help="print the steps and exit")
    a = ap.parse_args(argv)
    solo = [s for s in a.only.split(",") if s] if a.only else None
    omitir = [s for s in a.skip.split(",") if s] if a.skip else None
    if a.list:
        for p in PASOS:
            nota = ("con --with-ingest" if p.solo_con_flag else "con --with-colorado" if p.solo_con_colorado
                    else (f"si existe {p.requiere}" if p.requiere else "si el modulo existe" if p.opcional else ""))
            estado = "disponible" if disponible(p) and not falta_requisito(p) else "no disponible"
            print(f"{p.nombre:<15} {p.modulo:<26} {estado:<14} {nota}")
        return 0
    if a.muestra:
        if a.with_ingest or a.with_colorado or solo or omitir:
            ap.error("--muestra no se combina con --with-ingest, --with-colorado, --only ni --skip")
        if not (MUESTRA_DIR / "manifest.json").exists():
            ap.error(f"falta {MUESTRA_DIR}: generala con `uv run python -m pipeline.muestra` (necesita data/raw)")
        pasos, omitidos = pasos_muestra()
        for n, motivo in omitidos.items():
            print(f"[muestra] se omite {n}: {motivo}")
    else:
        fuera: dict[str, str] = {}
        pasos = seleccionar(PASOS, a.with_ingest, solo, omitir, a.with_colorado, fuera)
        for n, motivo in fuera.items():
            print(f"[run_all] se omite {n}: {motivo}")
        pedidos = [n for n in (solo or []) if n in fuera]
        if pedidos:   # a step asked for by name that cannot run is an error, not "nada que correr"
            print(f"[run_all] --only pide pasos que no pueden correr: {', '.join(pedidos)}", file=sys.stderr)
            return 2
    if not pasos:
        print("nada que correr")
        return 0
    filas = correr(pasos)
    pendientes = [p.nombre for p in pasos[len(filas):]]
    print("\n" + tabla(filas, pendientes))
    if any(e not in ("OK", "omitido") for _, _, e in filas):
        print(f"\nCadena detenida en el paso '{filas[-1][0]}'. Corregir y reanudar con --only {','.join([filas[-1][0]] + pendientes)}",
              file=sys.stderr)
        return 1
    if a.muestra:
        print(f"\nDemo lista: {MUESTRA_SITE / 'index.html'} (MUESTRA: no son las cifras de la cuenca)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
