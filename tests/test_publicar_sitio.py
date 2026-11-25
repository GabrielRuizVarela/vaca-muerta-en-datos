"""Build the public deploy tree and check the required outputs."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "publicar_sitio.sh"
HREF = re.compile(r'href="([^"]*)"')


def _relative_md_hrefs(text):
    found = []
    for m in HREF.finditer(text):
        v = m.group(1)
        low = v.lower()
        if low.startswith(("http:", "https:", "mailto:")) or "://" in v:
            continue
        if re.match(r"^.*\.md(#[^\"]*)?$", v):
            found.append(v)
    return found


def _resolve_clamped(root, page, href_path):
    # Mirror how browsers resolve links when the tree is served: ".." clamps
    # at the site root instead of escaping it.
    if href_path.startswith("/"):
        parts = []
    else:
        parts = list(page.parent.relative_to(root).parts)
    for seg in href_path.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return root.joinpath(*parts)


def test_publicar_sitio_builds_tree(tmp_path):
    if shutil.which("npx") is None:
        pytest.skip("npx is missing")
    out = tmp_path / "t1"
    proc = subprocess.run(
        [str(SCRIPT), str(out)], cwd=REPO, capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert (out / "index.html").is_file()
    readme_html = out / "README.html"
    assert readme_html.is_file()
    assert "<h1" in readme_html.read_text(encoding="utf-8")
    assert (out / "ATRIBUCION.html").is_file()
    assert (out / "README.md").is_file()
    assert (out / "LICENSE").is_file()
    assert (out / "docs" / "caso-interferencia.html").is_file()
    assert list((out / "wiki").rglob("*.html")), "wiki pages were not rendered"
    assert list(out.rglob("deslop-review.*")) == []
    assert list(out.rglob("revision-independiente.*")) == []
    bad = []
    for p in sorted(out.rglob("*.html")):
        for v in _relative_md_hrefs(p.read_text(encoding="utf-8")):
            bad.append(f"{p}: {v}")
    assert bad == []
    dangling = []
    for p in sorted(out.rglob("*.html")):
        for v in HREF.findall(p.read_text(encoding="utf-8")):
            if "${" in v:
                continue
            if v.startswith(("http:", "https:", "mailto:", "//", "#")) or "://" in v:
                continue
            path = v.split("#", 1)[0].split("?", 1)[0]
            if path.lower().endswith(".html") and not _resolve_clamped(out, p, path).is_file():
                dangling.append(f"{p}: {v}")
    assert dangling == []
    index = (out / "index.html").read_text(encoding="utf-8")
    assert index.count('href="../README.html#') >= 1
    # site/ is copied to the root, so no published href may keep the prefix.
    stale_site = []
    for p in sorted(out.rglob("*.html")):
        for v in HREF.findall(p.read_text(encoding="utf-8")):
            base = v.split("#", 1)[0].split("?", 1)[0]
            if base.startswith("site/"):
                stale_site.append(f"{p}: {v}")
    assert stale_site == []
    assert 'href="index.html"' in readme_html.read_text(encoding="utf-8")


def test_publicar_sitio_refuses_nonempty_dir(tmp_path):
    if shutil.which("npx") is None:
        pytest.skip("npx is missing")
    out = tmp_path / "t1"
    out.mkdir()
    (out / "existing.txt").write_text("x", encoding="utf-8")
    proc = subprocess.run(
        [str(SCRIPT), str(out)], cwd=REPO, capture_output=True, text=True
    )
    assert proc.returncode == 1
    assert "refusing" in proc.stderr.lower() or "not empty" in proc.stderr.lower()
    assert (out / "existing.txt").read_text(encoding="utf-8") == "x"


def test_publicar_sitio_exit_2_when_marked_fails(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    npx = fake / "npx"
    npx.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    npx.chmod(0o755)
    out = tmp_path / "t2"
    env = {"PATH": f"{fake}:/usr/bin:/bin"}
    proc = subprocess.run(
        ["/bin/bash", str(SCRIPT), str(out)],
        cwd=REPO, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 2
    assert "marked" in proc.stderr
    assert not out.exists()
