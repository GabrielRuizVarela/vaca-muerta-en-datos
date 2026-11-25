#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAPER_MD="$ROOT/docs/paper/paper.md"
PAGE_HTML="$ROOT/docs/paper/vaca-muerta-paper.html"
OUT_PDF="$ROOT/docs/paper/vaca-muerta-paper.pdf"
BODY_HTML="$(mktemp)"
trap 'rm -f "$BODY_HTML"' EXIT
if ! command -v npx >/dev/null 2>&1; then
  echo "build_paper_pdf: npx no encontrado. Instale Node para continuar." >&2
  exit 2
fi
if ! command -v google-chrome >/dev/null 2>&1; then
  echo "build_paper_pdf: google-chrome no encontrado. Instale Chrome para continuar." >&2
  exit 2
fi
npx -y marked@15.0.12 -i "$PAPER_MD" -o "$BODY_HTML"
BODY_INNER="$(mktemp)"
trap 'rm -f "$BODY_HTML" "$BODY_INNER"' EXIT
if grep -qi "<body" "$BODY_HTML"; then
  sed -n '/<body[^>]*>/,/<\/body>/p' "$BODY_HTML" | sed '1s/.*<body[^>]*>//; $s|</body>.*||' > "$BODY_INNER"
else
  cp "$BODY_HTML" "$BODY_INNER"
fi
{
cat <<'HTMLHEAD'
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vaca Muerta en datos: paper</title>
<style>
@page { size: A4; margin: 22mm 20mm; }
html, body { margin: 0; padding: 0; }
body { font-family: Georgia, "Times New Roman", serif; font-size: 11pt; line-height: 1.45; max-width: none; color: #111; }
main { max-width: none; }
h1 { font-size: 21pt; line-height: 1.2; margin: 0 0 0.5em; }
h2 { font-size: 13pt; line-height: 1.3; margin: 1.5em 0 0.4em; border-bottom: 1px solid #888; padding-bottom: 0.2em; }
h3 { font-size: 11.5pt; margin: 1.2em 0 0.3em; }
p, li { orphans: 3; widows: 3; }
a { color: #111; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 9.5pt; background: none; }
th, td { text-align: left; vertical-align: top; padding: 6px 8px; border-top: 1px solid #666; border-bottom: 1px solid #666; background: none; }
th { border-bottom: 1px solid #111; }
figure { width: 100%; margin: 1em 0; break-inside: avoid; }
img, svg { width: 100%; max-width: 100%; height: auto; break-inside: avoid; }
pre, code { font-size: 9pt; line-height: 1.4; }
pre { white-space: pre-wrap; }
blockquote { margin: 1em 0; padding-left: 1em; border-left: 2px solid #999; }
</style>
</head>
<body>
<main>
HTMLHEAD
cat "$BODY_INNER"
cat <<'HTMLFOOT'
</main>
</body>
</html>
HTMLFOOT
} > "$PAGE_HTML"
google-chrome --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf="$OUT_PDF" "file://$PAGE_HTML"
if command -v pdfinfo >/dev/null 2>&1; then
  pdfinfo "$OUT_PDF"
  PAGES=$(pdfinfo "$OUT_PDF" | awk '/^Pages:/ {print $2}')
  echo "pages: $PAGES"
else
  MAGIC=$(head -c 4 "$OUT_PDF")
  if [ "$MAGIC" != "%PDF" ]; then
    echo "build_paper_pdf: el archivo no empieza con %PDF" >&2
    exit 1
  fi
  echo "pdf magic ok: %PDF"
fi
if command -v pdftoppm >/dev/null 2>&1; then
  pdftoppm -png -f 1 -l 1 "$OUT_PDF" /tmp/vaca-muerta-paper-preview
  echo "preview: /tmp/vaca-muerta-paper-preview-1.png"
fi
