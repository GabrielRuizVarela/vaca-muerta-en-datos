#!/usr/bin/env bash
# Corre scripts/contraste_honestdid.R en un contenedor con limites: contraste_honestdid.sh <entradas.json> <salida.json>
# <entradas.json> va dentro del repositorio (se monta de solo lectura); <salida.json> se escribe en su directorio (lectura y escritura).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGEN="vm-honestdid:0.2.8"
[ "$#" -eq 2 ] || { echo "uso: $0 <entradas.json> <salida.json>" >&2; exit 2; }
ENT="$(realpath "$1")"
SAL_DIR="$(realpath -m "$(dirname "$2")")"
SAL_NOMBRE="$(basename "$2")"
case "$ENT" in "$ROOT"/*) ;; *) echo "las entradas tienen que estar dentro del repositorio" >&2; exit 2;; esac
mkdir -p "$SAL_DIR"
if ! docker image inspect "$IMAGEN" >/dev/null 2>&1; then
  docker build -t "$IMAGEN" -f "$ROOT/scripts/contraste_honestdid.Dockerfile" "$ROOT/scripts"
fi
docker run --rm --network none --cpus 4 --memory 8g --user "$(id -u):$(id -g)" \
  -v "$ROOT:/repo:ro" -v "$SAL_DIR:/out" \
  "$IMAGEN" Rscript /repo/scripts/contraste_honestdid.R "/repo/${ENT#"$ROOT"/}" "/out/$SAL_NOMBRE"
