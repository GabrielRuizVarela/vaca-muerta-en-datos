"""scripts/bajar_datos_crudos.py: puts each file where the manifest says, and keeps nothing that does not match."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bajar_datos_crudos", ROOT / "scripts" / "bajar_datos_crudos.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _armar(tmp_path, corrupto=None):
    fuente, raiz = tmp_path / "release", tmp_path / "clon"
    fuente.mkdir()
    (raiz / "data").mkdir(parents=True)
    manifest = {}
    for i, n in enumerate(mod.CORE):
        cuerpo = f"col\n{n},{i}\n".encode()
        sha = hashlib.sha256(cuerpo).hexdigest()
        ruta = f"{n}/2026-11-23_{sha[:12]}.csv"
        manifest[n] = {"path": ruta, "sha256": sha, "bytes": len(cuerpo)}
        (fuente / Path(ruta).name).write_bytes(b"roto\n" if n == corrupto else cuerpo)
    (raiz / "data" / "manifest.json").write_text(json.dumps(manifest))
    return fuente, raiz, manifest


def test_baja_y_verifica(tmp_path, capsys):
    fuente, raiz, manifest = _armar(tmp_path)
    assert mod.bajar(str(fuente), raiz) == 0
    for e in manifest.values():
        assert mod.sha256_de(raiz / "data" / "raw" / e["path"]) == e["sha256"]
    assert mod.bajar(str(fuente), raiz) == 0  # second run: nothing to do
    assert "ya esta" in capsys.readouterr().out


def test_no_guarda_un_archivo_que_no_coincide(tmp_path):
    fuente, raiz, manifest = _armar(tmp_path, corrupto="fractura_adjunto_iv")
    assert mod.bajar(str(fuente), raiz) == 1
    malo = raiz / "data" / "raw" / manifest["fractura_adjunto_iv"]["path"]
    assert not malo.exists()
    assert list(malo.parent.iterdir()) == []  # no temporary file left behind
    assert (raiz / "data" / "raw" / manifest["produccion_no_convencional"]["path"]).exists()
