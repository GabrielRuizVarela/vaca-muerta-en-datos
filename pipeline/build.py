"""Build the DuckDB warehouse from the latest raw files, then run the quality checks.

Every table is rebuilt from the raw layer with `create or replace`, so a rerun on
the same inputs gives the same warehouse (idempotent, no incremental state to drift).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

from pipeline import checks
from pipeline.ingest import DATA, MANIFEST, ROOT, load_manifest

SQL_DIR = Path(__file__).parent / "sql"


def build(con: duckdb.DuckDBPyConnection, inputs: dict[str, Path]) -> None:
    params = {k: str(v).replace("'", "''") for k, v in inputs.items()}
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        con.execute(sql_file.read_text().format(**params))


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
    build(con, inputs)
    report = checks.run(con, inputs=inputs)
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
