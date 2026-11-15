"""Build the DuckDB warehouse from the latest raw files, then run the quality checks.

Every table is rebuilt from the raw layer with `create or replace`, so a rerun on
the same inputs gives the same warehouse (idempotent, no incremental state to drift).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from pipeline import checks
from pipeline.ingest import DATA, ROOT, load_manifest

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


def main() -> int:
    manifest = load_manifest()
    inputs = raw_inputs(manifest) | {"seed_operadores": ROOT / "seeds" / "operadores.csv"}
    db = DATA / "warehouse.duckdb"
    con = duckdb.connect(str(db))
    build(con, inputs)
    report = checks.run(con, inputs=inputs)
    report["fuentes"] = {k: {f: v.get(f) for f in ("url", "sha256", "bytes", "last_modified", "loaded_at")}
                         for k, v in manifest.items()}
    (DATA / "dq_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    for c in report["checks"]:
        print(f"[{c['severidad']:>7}] {'OK ' if c['ok'] else 'NO '} {c['filas']:>7}  {c['nombre']}")
    if report["bloqueantes_fallidos"]:
        print(f"FAILED: {report['bloqueantes_fallidos']} blocking check(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
