#!/usr/bin/env bash
# Weekly refresh: ingest, build with quality checks, wiki + graph, eval (if the local model is up), render, commit.
# Run from a network that reaches datos.energia.gob.ar. Cron example (Mondays 06:00):
#   0 6 * * 1 cd ~/dev/vaca-muerta-data && ./refresh.sh >> data/refresh.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"
uv run pytest -q
uv run python -m pipeline.ingest
# build, costo, robustez, [validacion], placebo, wiki. report and replay run after the eval because report reads its results.
uv run python -m pipeline.run_all --skip report,replay,claims
# Held-out accuracy against the new data, only when the offline model is reachable.
if curl -sf -m 3 "${VM_LLM_URL:-http://127.0.0.1:8080/v1}/models" >/dev/null; then
  uv run python -m agente.eval.run --split holdout || true
fi
uv run python -m pipeline.run_all --only report,replay
# Numbers quoted in README.md and docs/para-projectA.md against the new data: a warning, never blocks the commit.
uv run python -m pipeline.claims || echo "AVISO: hay cifras del README que ya no coinciden con el warehouse (ver tabla arriba)" >&2
git add data/manifest.json data/dq_report.json site/index.html site/replay.html wiki agente/eval/resultados
if ! git diff --cached --quiet; then
  git commit -m "data: refresh $(date -u +%F)"
  git push
fi
