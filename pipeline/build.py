"""Build the DuckDB warehouse from the latest raw files, then run the quality checks.

Every table is rebuilt from the raw layer with `create or replace`, so a rerun on
the same inputs gives the same tables, bit by bit (idempotent, no incremental state to drift).
The two things that could make a rerun differ are fixed in `build`: the date that decides which
fracture jobs are in the future comes from the manifest, and the SQL runs on one thread.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import duckdb

from pipeline import checks
from pipeline.ingest import DATA, MANIFEST, ROOT, load_manifest

SQL_DIR = Path(__file__).parent / "sql"


def fecha_extraccion(manifest: dict) -> date | None:
    """Day (UTC) on which the local copy of the fracture file was last verified against the source: `checked_at`, or
    `loaded_at` in a manifest written before that field existed. None when the manifest carries no date (the sample
    in data/muestra, files that did not come through pipeline.ingest)."""
    m = manifest.get("fractura_adjunto_iv") or {}
    sello = m.get("checked_at") or m.get("loaded_at")
    return date.fromisoformat(str(sello)[:10]) if sello else None


def build(con: duckdb.DuckDBPyConnection, inputs: dict[str, Path], extraccion: date | None = None) -> None:
    """Run every SQL file in order. `extraccion` is the extraction date of the fracture file: a job that starts after
    it is left out of the model and reported by the checks. Without it the day of the run is used, which is the only
    case where the result depends on when the build runs."""
    params = {k: str(v).replace("'", "''") for k, v in inputs.items()}
    params["fecha_extraccion"] = (extraccion or date.today()).isoformat()
    # One thread while the model is built. With several, DuckDB adds floats in the order its threads finish and a sum
    # changes in its last bit from one run to the next; with one, two builds of the same files are equal bit by bit.
    # On the full data it costs about half a second.
    hilos = con.execute("select current_setting('threads')").fetchall()[0][0]
    con.execute("set threads = 1")
    try:
        for sql_file in sorted(SQL_DIR.glob("*.sql")):
            con.execute(sql_file.read_text().format(**params))
    finally:
        con.execute(f"set threads = {int(hilos)}")


def raw_inputs(manifest: dict, raw_dir: Path = DATA / "raw") -> dict[str, Path]:
    missing = [n for n in ("produccion_no_convencional", "fractura_adjunto_iv") if n not in manifest]
    if missing:
        raise SystemExit(f"missing raw data for {missing}: run `python -m pipeline.ingest` first")
    return {name: raw_dir / entry["path"] for name, entry in manifest.items()}


def rutas(raw_dir: str | Path | None = None, db: str | Path | None = None) -> tuple[Path, Path, Path, Path]:
    """(raw_dir, manifest, db, dq_report). Argument, then env VM_RAW_DIR / VM_DB_PATH, then the default.

    With the default raw dir everything is as always (data/manifest.json, data/warehouse.duckdb,
    data/dq_report.json). With another raw dir the manifest is the one inside it, and a non-default
    database gets its own dq report next to it (<db sin extension>_dq_report.json)."""
    raw_dir = Path(raw_dir or os.environ.get("VM_RAW_DIR") or DATA / "raw")
    db = Path(db or os.environ.get("VM_DB_PATH") or DATA / "warehouse.duckdb")
    manifest = raw_dir / "manifest.json" if raw_dir != DATA / "raw" and (raw_dir / "manifest.json").exists() else MANIFEST
    dq = DATA / "dq_report.json" if db == DATA / "warehouse.duckdb" else db.with_name(db.stem + "_dq_report.json")
    return raw_dir, manifest, db, dq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.build", description=__doc__)
    ap.add_argument("--raw-dir", help="directorio con los CSV (por defecto VM_RAW_DIR o data/raw)")
    ap.add_argument("--db", help="archivo DuckDB de salida (por defecto VM_DB_PATH o data/warehouse.duckdb)")
    a = ap.parse_args(argv)
    raw_dir, manifest_path, db, dq_path = rutas(a.raw_dir, a.db)
    manifest = load_manifest(manifest_path)
    inputs = raw_inputs(manifest, raw_dir) | {"seed_operadores": ROOT / "seeds" / "operadores.csv"}
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    extraccion = fecha_extraccion(manifest)
    build(con, inputs, extraccion)
    # freshness is measured on the day the data was extracted, so the report of the same files reads the same on any day
    report = checks.run(con, inputs=inputs, hoy=extraccion)
    report["fuentes"] = {k: {f: v.get(f) for f in ("url", "sha256", "bytes", "last_modified", "loaded_at")}
                         for k, v in manifest.items()}
    dq_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    for c in report["checks"]:
        print(f"[{c['severidad']:>7}] {'OK ' if c['ok'] else 'NO '} {c['filas']:>7}  {c['nombre']}")
    if report["bloqueantes_fallidos"]:
        print(f"FAILED: {report['bloqueantes_fallidos']} blocking check(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
