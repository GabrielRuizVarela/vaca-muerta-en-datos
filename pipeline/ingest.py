"""Download the public datasets into an immutable raw layer.

Idempotent: a conditional GET (ETag / Last-Modified) skips unchanged files, and a
file whose bytes hash the same as the latest stored copy is not stored twice.
Each stored copy is named by date and content hash, so earlier loads stay
reproducible. data/manifest.json records source, hash, size and load time.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANIFEST = DATA / "manifest.json"

# Secretaría de Energía, datos.energia.gob.ar (CKAN). Public open data.
SOURCES = {
    "produccion_no_convencional": "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv",
    "fractura_adjunto_iv": "http://datos.energia.gob.ar/dataset/71fa2e84-0316-4a1b-af68-7f35e41f58d7/resource/2280ad92-6ed3-403e-a095-50139863ab0d/download/datos-de-fractura-de-pozos-de-hidrocarburos-adjunto-iv-actualizacin-diaria.csv",
}


def load_manifest(path: Path = MANIFEST) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_manifest(manifest: dict, path: Path = MANIFEST) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)  # atomic: a crash never leaves a half-written manifest


def store(name: str, tmp_file: Path, sha: str, meta: dict, manifest: dict, raw_dir: Path) -> bool:
    """Store a downloaded file under its hash. Returns False when unchanged."""
    entry = manifest.get(name, {})
    if entry.get("sha256") == sha and (raw_dir / entry["path"]).exists():
        entry["checked_at"] = meta["loaded_at"]
        manifest[name] = entry
        return False
    rel = Path(name) / f"{meta['loaded_at'][:10]}_{sha[:12]}.csv"
    (raw_dir / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(tmp_file, raw_dir / rel)
    manifest[name] = {**meta, "sha256": sha, "path": str(rel), "checked_at": meta["loaded_at"]}
    return True


def fetch(name: str, url: str, manifest: dict, raw_dir: Path = DATA / "raw") -> str:
    entry = manifest.get(name, {})
    req = urllib.request.Request(url, headers={"User-Agent": "vaca-muerta-data/0.1"})
    # Only ask for a 304 when the stored copy is really on disk (a fresh CI runner has none).
    have_copy = bool(entry.get("path")) and (raw_dir / entry["path"]).exists()
    if have_copy and entry.get("etag"):
        req.add_header("If-None-Match", entry["etag"])
    if have_copy and entry.get("last_modified"):
        req.add_header("If-Modified-Since", entry["last_modified"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        resp = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as err:
        if err.code == 304:
            entry["checked_at"] = now
            return "not-modified"
        raise
    sha = hashlib.sha256()
    size = 0
    with resp, tempfile.NamedTemporaryFile(dir=DATA, delete=False) as out:
        while chunk := resp.read(1 << 20):
            sha.update(chunk)
            size += len(chunk)
            out.write(chunk)
    if size == 0:
        Path(out.name).unlink()
        raise RuntimeError(f"{name}: empty download")
    meta = {
        "url": url,
        "etag": resp.headers.get("ETag"),
        "last_modified": resp.headers.get("Last-Modified"),
        "bytes": size,
        "loaded_at": now,
    }
    changed = store(name, Path(out.name), sha.hexdigest(), meta, manifest, raw_dir)
    if not changed:
        Path(out.name).unlink(missing_ok=True)
    return "stored" if changed else "unchanged"


def main() -> int:
    DATA.mkdir(exist_ok=True)
    manifest = load_manifest()
    for name, url in SOURCES.items():
        status = fetch(name, url, manifest)
        print(f"{name}: {status}")
        save_manifest(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
