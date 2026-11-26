#!/usr/bin/env bash
set -euo pipefail
# Build the public deploy tree for the Cloudflare copy.
# Copies site docs wiki plus top level files, renders Markdown, rewrites links.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/publicar_sitio.sh OUT_DIR" >&2
  exit 1
fi

OUT_DIR="$1"

if [ -e "$OUT_DIR" ] && [ ! -d "$OUT_DIR" ]; then
  echo "Refusing: OUT_DIR exists and is not a directory: $OUT_DIR" >&2
  exit 1
fi

if [ -d "$OUT_DIR" ] && [ -n "$(ls -A "$OUT_DIR" 2>/dev/null)" ]; then
  echo "Refusing: OUT_DIR exists and is not empty: $OUT_DIR" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "Missing npx. Install Node.js so Markdown can be rendered." >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Missing python3. It rewrites Markdown links to HTML links." >&2
  exit 2
fi

# Probe marked before copying anything, so a missing renderer exits early.
PROBE_MD="$(mktemp --suffix=.md)"
PROBE_HTML="$(mktemp --suffix=.html)"
printf '# probe\n' > "$PROBE_MD"
if ! npx -y marked@15.0.12 -i "$PROBE_MD" -o "$PROBE_HTML" >/dev/null 2>&1; then
  rm -f "$PROBE_MD" "$PROBE_HTML"
  echo "Missing marked. npx could not run marked@15.0.12." >&2
  exit 2
fi
rm -f "$PROBE_MD" "$PROBE_HTML"

mkdir -p "$OUT_DIR"

cp -a "$ROOT/site/." "$OUT_DIR/"
mkdir -p "$OUT_DIR/docs" "$OUT_DIR/wiki"
cp -a "$ROOT/docs/." "$OUT_DIR/docs/"
cp -a "$ROOT/wiki/." "$OUT_DIR/wiki/"
# Internal working documents (review notes, plans, the scoring baseline) are not published.
rm -f "$OUT_DIR/docs/deslop-review.md" "$OUT_DIR/docs/revision-independiente.md" \
      "$OUT_DIR/docs/plan-nueva-entrada.md" "$OUT_DIR/docs/plan-siguiente-nivel.md" \
      "$OUT_DIR/docs/proceso/fable-base-2026-11-26.md" "$OUT_DIR/docs/proceso/fable-factual-verificacion-2026-11-26.md" \
      "$OUT_DIR/docs/proceso/auditoria-P-2026-11-26.md" "$OUT_DIR/docs/proceso/fable-P-2026-11-26.md" \
      "$OUT_DIR/docs/proceso/ronda1-2026-11-26.md" "$OUT_DIR/docs/proceso/fable-R1-2026-11-26.md" \
      "$OUT_DIR/docs/proceso/ronda2-2026-11-26.md" "$OUT_DIR/docs/proceso/fable-R2-2026-11-26.md" \
      "$OUT_DIR/docs/proceso/fable-final-2026-11-26.md"

cp -a "$ROOT/README.md" "$ROOT/ATRIBUCION.md" "$ROOT/LICENSE" "$OUT_DIR/"

# Render every Markdown file with a single renderer start: install marked once
# into a temp dir, then one node process renders the whole tree.
RENDER_TMP="$(mktemp -d)"
RENDER_JS="$(mktemp --suffix=.js)"
cat > "$RENDER_JS" <<'JS'
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const outDir = process.argv[2];
const files = [];
(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.isFile() && e.name.endsWith(".md")) files.push(p);
  }
})(outDir);
files.sort();
const HEAD1 = '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>';
const HEAD2 = '</title><style>body{max-width:52em;margin:2em auto;padding:0 16px;font:16px/1.55 system-ui,sans-serif;color:#1a1a1a}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow-x:auto}td,th{border:1px solid #ccc;padding:4px 6px;vertical-align:top}</style></head><body>';
for (const md of files) {
  const src = fs.readFileSync(md, "utf8");
  const m = src.match(/^# (.*)$/m);
  const title = m ? m[1] : path.basename(md);
  const esc = title.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  fs.writeFileSync(md.slice(0, -3) + ".html", HEAD1 + esc + HEAD2 + marked.parse(src) + "</body></html>");
}
JS
if ! npm install --prefix "$RENDER_TMP" --no-audit --no-fund --loglevel=error marked@15.0.12 >/dev/null 2>&1; then
  rm -rf "$RENDER_TMP" "$RENDER_JS"
  echo "Missing marked. npm could not install marked@15.0.12." >&2
  exit 2
fi
if ! NODE_PATH="$RENDER_TMP/node_modules" node "$RENDER_JS" "$OUT_DIR" >/dev/null 2>&1; then
  rm -rf "$RENDER_TMP" "$RENDER_JS"
  echo "Missing marked. node could not render with marked@15.0.12." >&2
  exit 2
fi
rm -rf "$RENDER_TMP" "$RENDER_JS"

# Rewrite relative Markdown links to HTML links in every HTML file. Links to the
# excluded internal files are unwrapped to plain text first, so no link points
# at a page that was not published. Then every relative .html link must resolve.
python3 - "$OUT_DIR" <<'PY'
import os, re, sys, pathlib
root = pathlib.Path(sys.argv[1])
EXCLUDED = ("deslop-review.md", "revision-independiente.md", "plan-nueva-entrada.md",
            "plan-siguiente-nivel.md", "fable-base-2026-11-26.md", "fable-factual-verificacion-2026-11-26.md")
anchor = re.compile(r'<a\s+href="([^"]*)"[^>]*>(.*?)</a>', re.S | re.I)
href = re.compile(r'href="([^"]*)"')
md_link = re.compile(r"^(.*)\.md((?:\?[^#\"]*)?(?:#[^\"]*)?)$", re.I)

def is_absolute(v):
    return v.startswith(("//", "mailto:", "#")) or re.match(r"^[a-z][a-z0-9+.-]*:", v, re.I) is not None

def unwrap(m):
    v = m.group(1)
    if is_absolute(v):
        return m.group(0)
    path = v.split("#", 1)[0].split("?", 1)[0]
    if os.path.basename(path).lower() in EXCLUDED:
        return m.group(2)
    return m.group(0)

def fix(m):
    v = m.group(1)
    if is_absolute(v):
        return m.group(0)
    orig = v
    m2 = md_link.match(v)
    if m2:
        v = m2.group(1) + ".html" + m2.group(2)
    # site/ is copied to the root of the published tree, so a leading site/
    # is rewritten to the root path when that target exists at root.
    base = v.split("#", 1)[0].split("?", 1)[0]
    if base.startswith("site/") and (root / base[len("site/"):]).exists():
        v = v[len("site/"):]
    if v == orig:
        return m.group(0)
    return 'href="' + v + '"'

def resolve_clamped(page, href_path):
    # Browsers clamp ".." at the site root when the tree is served, so a link
    # like ../README.html from a root page resolves to /README.html. Mirror
    # that: join, then clamp at the root instead of escaping OUT_DIR.
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

pages = sorted(root.rglob("*.html"))
for p in pages:
    t = p.read_text(encoding="utf-8")
    n = href.sub(fix, anchor.sub(unwrap, t))
    if n != t:
        p.write_text(n, encoding="utf-8")

dangling = []
for p in pages:
    for v in href.findall(p.read_text(encoding="utf-8")):
        if "${" in v:
            continue
        if is_absolute(v):
            continue
        path = v.split("#", 1)[0].split("?", 1)[0]
        if not path.lower().endswith(".html"):
            continue
        if not resolve_clamped(p, path).is_file():
            dangling.append(f"{p.relative_to(root)} -> {v}")
if dangling:
    print("Dangling relative links after the rewrite:", file=sys.stderr)
    for d in dangling:
        print("  " + d, file=sys.stderr)
    sys.exit(3)
PY

find "$OUT_DIR" -type f | sort
