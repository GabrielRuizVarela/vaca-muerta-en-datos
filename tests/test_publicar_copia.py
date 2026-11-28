"""scripts/publicar_copia.sh: the public copy as one command that refuses to publish a bad tree.

Hermetic: each test builds a small git repo that holds a copy of the script and the never-publish list, and uses a
local bare repo as PUBLIC_REMOTE. No network.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT_SRC = REPO / "scripts" / "publicar_copia.sh"
LIST_SRC = REPO / "scripts" / "no_publicar.txt"
NOREPLY = "54688063+GabrielRuizVarela@users.noreply.github.com"

# Built from pieces so this file never contains a string the script's scan would flag.
HOME_PATH = "/home/" + "vg/dev/x"

CI_YML = (
    "name: ci\n# Runs on a self-hosted runner.\njobs:\n  lint:\n    runs-on: [self-hosted, vaca-muerta]\n"
    "  test:\n    runs-on: [self-hosted, vaca-muerta]\n"
)


def _git(cwd, *args, check=True):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check, env=env)


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def env(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _git(src, "init", "-q", "-b", "main")
    _git(src, "config", "user.name", "Someone Else")
    _git(src, "config", "user.email", "someone@example.com")
    (src / "scripts").mkdir()
    shutil.copy(SCRIPT_SRC, src / "scripts" / "publicar_copia.sh")
    shutil.copy(LIST_SRC, src / "scripts" / "no_publicar.txt")
    os.chmod(src / "scripts" / "publicar_copia.sh", 0o755)
    _write(src, "README.md", "# Public\n")
    _write(src, "docs/caso.md", "# Caso\n")
    _write(src, "AGENTS.md", "internal rules\n")
    _write(src, "REVIEW.md", "internal review\n")
    _write(src, "docs/orquestacion/chief.md", "internal\n")
    _write(src, "docs/plan-siguiente-nivel.md", "internal plan\n")
    _write(src, "docs/proceso/fable-final-2026-11-26.md", "internal\n")
    _write(src, ".github/workflows/ci.yml", CI_YML)
    _git(src, "add", "-A")
    _git(src, "commit", "-q", "-m", "initial")

    bare = tmp_path / "public.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    msg = tmp_path / "msg.txt"
    msg.write_text("Agrega el caso de interferencia\n", encoding="utf-8")
    return {"src": src, "bare": bare, "msg": msg, "tmp": tmp_path}


def _run(env, *args, message=True, extra_env=None):
    cmd = ["bash", str(env["src"] / "scripts" / "publicar_copia.sh"), "--ref", "HEAD", *args]
    if message:
        cmd += ["--message-file", str(env["msg"])]
    full_env = {**os.environ, "PUBLIC_REMOTE": str(env["bare"]), **(extra_env or {})}
    return subprocess.run(cmd, cwd=env["src"], capture_output=True, text=True, env=full_env, timeout=50)


def _public_files(env):
    out = _git(env["bare"], "ls-tree", "-r", "--name-only", "main").stdout
    return set(out.split())


def _public_commits(env):
    r = _git(env["bare"], "rev-list", "--count", "main", check=False)
    return int(r.stdout.strip()) if r.returncode == 0 else 0


def test_sanitized_tree_has_none_of_the_listed_files(env):
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    files = _public_files(env)
    assert {"README.md", "docs/caso.md", ".github/workflows/ci.yml"} <= files
    for gone in ("AGENTS.md", "REVIEW.md", "docs/plan-siguiente-nivel.md", "docs/proceso/fable-final-2026-11-26.md"):
        assert gone not in files
    assert not [f for f in files if f.startswith("docs/orquestacion/")]
    ci = _git(env["bare"], "show", "main:.github/workflows/ci.yml").stdout
    assert "runs-on: ubuntu-latest" in ci
    assert "runs-on: [self-hosted" not in ci


def test_every_entry_of_the_real_list_is_removed(env):
    for line in LIST_SRC.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            _write(env["src"], line + "x.md" if line.endswith("/") else line, "internal\n")
    _git(env["src"], "add", "-A")
    _git(env["src"], "commit", "-q", "-m", "all internal files")
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    files = _public_files(env)
    for line in LIST_SRC.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            assert not any(f == line.rstrip("/") or f.startswith(line.rstrip("/") + "/") for f in files), line


PLANTED = {
    "home": HOME_PATH,
    "tailnet": "host.tail" + "scale.ts" + ".net",
    "ip": "100." + "64.1.2",
    "key": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "token": "gh" + "p_abcdef",
}


def test_every_planted_private_string_exits_3_and_pushes_nothing(env):
    # One file per pattern, one run: the scan must name every file.
    for name, text in PLANTED.items():
        _write(env["src"], f"docs/nota-{name}.md", f"see {text}\n")
    _git(env["src"], "add", "-A")
    _git(env["src"], "commit", "-q", "-m", "plant")
    proc = _run(env)
    assert proc.returncode == 3
    for name in PLANTED:
        assert f"docs/nota-{name}.md:1" in proc.stderr
    assert _public_commits(env) == 0


def test_planted_string_inside_an_unpublished_file_does_not_block(env):
    _write(env["src"], "AGENTS.md", f"see {HOME_PATH}\n")
    _git(env["src"], "add", "-A")
    _git(env["src"], "commit", "-q", "-m", "internal path in an internal file")
    assert _run(env).returncode == 0


def test_commit_author_and_committer_are_the_noreply_address(env):
    assert _run(env).returncode == 0
    fmt = _git(env["bare"], "log", "-1", "--format=%an|%ae|%cn|%ce", "main").stdout.strip()
    assert fmt == f"Gabriel Ruiz Varela|{NOREPLY}|Gabriel Ruiz Varela|{NOREPLY}"
    assert _git(env["bare"], "log", "-1", "--format=%s", "main").stdout.strip() == "Agrega el caso de interferencia"


def test_second_run_with_no_change_creates_no_commit(env):
    assert _run(env).returncode == 0
    assert _public_commits(env) == 1
    proc = _run(env)
    assert proc.returncode == 0
    assert "nothing to publish" in proc.stdout
    assert _public_commits(env) == 1


def test_a_change_adds_exactly_one_commit_without_rewriting_history(env):
    assert _run(env).returncode == 0
    first = _git(env["bare"], "rev-parse", "main").stdout.strip()
    _write(env["src"], "docs/caso.md", "# Caso\n\nmas\n")
    _git(env["src"], "add", "-A")
    _git(env["src"], "commit", "-q", "-m", "change")
    assert _run(env).returncode == 0
    assert _public_commits(env) == 2
    assert _git(env["bare"], "rev-parse", "main~1").stdout.strip() == first


def test_dry_run_pushes_nothing_and_needs_no_message(env):
    proc = _run(env, "--dry-run", message=False)
    assert proc.returncode == 0, proc.stderr
    assert "README.md" in proc.stdout
    assert _public_commits(env) == 0


def test_message_is_required_without_dry_run(env):
    proc = _run(env, message=False)
    assert proc.returncode != 0
    assert "--message-file" in proc.stderr
    assert _public_commits(env) == 0


def test_relative_message_file_resolves_from_the_callers_directory(env):
    # The commit runs inside the clone, so a relative path must be made absolute first.
    rel = os.path.relpath(env["msg"], env["src"])
    assert not os.path.isabs(rel)
    proc = _run(env, "--message-file", rel, message=False)
    assert proc.returncode == 0, proc.stderr
    assert _public_commits(env) == 1


def test_message_with_personal_email_is_refused(env):
    env["msg"].write_text("Cambio de " + "yo@" + "gmail.com\n", encoding="utf-8")
    proc = _run(env)
    assert proc.returncode != 0
    assert _public_commits(env) == 0


def test_script_never_passes_force():
    text = SCRIPT_SRC.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "--force" not in code
    assert "push -f" not in code
    assert "--force-with-lease" not in code


def test_sitio_script_reads_the_shared_list():
    text = (REPO / "scripts" / "publicar_sitio.sh").read_text(encoding="utf-8")
    assert "no_publicar.txt" in text
    assert "docs/deslop-review.md" not in text
