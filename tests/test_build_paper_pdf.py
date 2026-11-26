"""Build del paper en PDF con Chrome headless."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_paper_pdf.sh"
PDF = ROOT / "docs" / "paper" / "vaca-muerta-paper.pdf"

needs_chrome = pytest.mark.skipif(
    shutil.which("google-chrome") is None, reason="google-chrome no disponible"
)
needs_npx = pytest.mark.skipif(
    shutil.which("npx") is None, reason="npx no disponible"
)


@needs_chrome
@needs_npx
def test_build_paper_pdf(tmp_path):
    antes = PDF.read_bytes() if PDF.exists() else None
    out = tmp_path / "paper.pdf"
    r = subprocess.run(["bash", str(SCRIPT), str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert out.read_bytes()[:4] == b"%PDF"
    # a clone stays clean after the tests: the tracked PDF is untouched and the intermediate page is gone
    assert (PDF.read_bytes() if PDF.exists() else None) == antes
    assert not (PDF.parent / "vaca-muerta-paper.html").exists()
