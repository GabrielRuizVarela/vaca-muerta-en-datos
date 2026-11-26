"""Download the three raw Secretaria de Energia files from this project's release and check them against data/manifest.json.

For a reader outside Argentina, where datos.energia.gob.ar does not answer. The files are byte for byte the ones the manifest
names (same size, same sha256); a file that does not match is never kept. After it, run the chain without --with-ingest:

    uv run python scripts/bajar_datos_crudos.py
    uv run python -m pipeline.run_all

Standard library only. `--base` points to another folder or URL with the same files (the tests use a local folder).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://github.com/GabrielRuizVarela/vaca-muerta-en-datos/releases/download/datos-crudos-2026-11-23"
CORE = ("produccion_no_convencional", "fractura_adjunto_iv", "trayectorias_pozo")


def sha256_de(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def abrir(base: str, nombre: str):
    if "://" in base:
        return urllib.request.urlopen(urllib.request.Request(f"{base.rstrip('/')}/{nombre}",
                                                             headers={"User-Agent": "vaca-muerta-data/0.1"}), timeout=600)
    return (Path(base) / nombre).open("rb")


def bajar(base: str = BASE, raiz: Path = ROOT) -> int:
    manifest = json.loads((raiz / "data" / "manifest.json").read_text())
    faltan = [n for n in CORE if n not in manifest]
    if faltan:
        print(f"data/manifest.json no trae {faltan}", file=sys.stderr)
        return 2
    malos = 0
    for nombre in CORE:
        e = manifest[nombre]
        destino = raiz / "data" / "raw" / e["path"]
        if destino.exists() and sha256_de(destino) == e["sha256"]:
            print(f"{nombre}: ya esta ({e['sha256'][:12]})")
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as out:
            tmp = Path(out.name)
            with abrir(base, Path(e["path"]).name) as src:
                shutil.copyfileobj(src, out, 1 << 20)
        if tmp.stat().st_size != e["bytes"] or sha256_de(tmp) != e["sha256"]:
            tmp.unlink()
            print(f"{nombre}: el archivo bajado no coincide con el manifest (tamano o sha256); no se guarda", file=sys.stderr)
            malos += 1
            continue
        tmp.replace(destino)
        print(f"{nombre}: ok ({e['bytes']} bytes, sha256 {e['sha256'][:12]})")
    return 1 if malos else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=BASE, help="URL or folder with the three files (default: the project's release)")
    return bajar(ap.parse_args(argv).base)


if __name__ == "__main__":
    raise SystemExit(main())
