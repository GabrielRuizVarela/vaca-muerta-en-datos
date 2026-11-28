#!/usr/bin/env bash
set -euo pipefail
# Append one curated commit to the public copy of this repo.
#
#   scripts/publicar_copia.sh --message-file FILE [--ref REF] [--dry-run] [--verify]
#
# 1. git archive REF (default origin/main) into a temp dir.
# 2. Remove everything listed in scripts/no_publicar.txt.
# 3. Set `runs-on: ubuntu-latest` in .github/workflows/ci.yml (the box's runner label must not leak).
# 4. Scan every text file for private addresses, paths and keys. Any hit: exit 3, push nothing.
# 5. Clone the public repo over SSH, replace its tree with the sanitized one. No change: "nothing to publish".
# 6. Commit as the owner with the GitHub noreply address and the Spanish message from FILE; normal push.
# 7. Print the new public SHA. With --verify, wait for the public CI run and check the repo's homepage.
#
# Env: PUBLIC_REMOTE overrides the SSH URL (the tests use a local bare repo).
# Exit codes: 1 usage, 2 missing tool or bad message, 3 scan or sanitize failure, 4 --verify failed.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PUBLIC_REPO="GabrielRuizVarela/vaca-muerta-en-datos"
PUBLIC_REMOTE="${PUBLIC_REMOTE:-git@github.com:${PUBLIC_REPO}.git}"
SITE_URL="https://vaca-muerta-en-datos.gabrielruizvarela.workers.dev"
AUTHOR_NAME="Gabriel Ruiz Varela"
AUTHOR_EMAIL="54688063+GabrielRuizVarela@users.noreply.github.com"
# Each bracket keeps the pattern from matching its own source line when this script is scanned.
SCAN_PATTERN='100\.[0-9]+\.[0-9]+\.[0-9]+|/home/v[g]|ts\.[n]et|BEGIN [A-Z ]*PRIVATE KEY|gh[p]_'

usage() {
  echo "Usage: scripts/publicar_copia.sh --message-file FILE [--ref REF] [--dry-run] [--verify]" >&2
  exit 1
}

REF="origin/main"
MESSAGE_FILE=""
DRY_RUN=0
VERIFY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --ref) [ "$#" -ge 2 ] || usage; REF="$2"; shift 2 ;;
    --message-file) [ "$#" -ge 2 ] || usage; MESSAGE_FILE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --verify) VERIFY=1; shift ;;
    *) usage ;;
  esac
done

if [ "$DRY_RUN" -eq 0 ] && [ -z "$MESSAGE_FILE" ]; then
  echo "--message-file FILE is required (a Spanish commit message written by the caller)." >&2
  usage
fi

if [ -n "$MESSAGE_FILE" ]; then
  if [ ! -s "$MESSAGE_FILE" ]; then
    echo "Message file is missing or empty: $MESSAGE_FILE" >&2
    exit 2
  fi
  if grep -qiE '@gmail' "$MESSAGE_FILE"; then
    echo "Refusing: the commit message contains a personal email address (@gmail)." >&2
    exit 2
  fi
  if grep -qE "$SCAN_PATTERN" "$MESSAGE_FILE"; then
    echo "Refusing: the commit message matches a private pattern:" >&2
    grep -nE "$SCAN_PATTERN" "$MESSAGE_FILE" >&2
    exit 3
  fi
  # The commit runs inside the clone: make the path absolute so a relative one still resolves.
  MESSAGE_FILE="$(cd "$(dirname "$MESSAGE_FILE")" && pwd)/$(basename "$MESSAGE_FILE")"
fi

for tool in git tar; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool." >&2; exit 2; }
done
if [ "$VERIFY" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  command -v gh >/dev/null 2>&1 || { echo "Missing gh (needed by --verify)." >&2; exit 2; }
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
TREE="$WORK/tree"
PUB="$WORK/public"
mkdir -p "$TREE"

# 1. The tree of REF.
if ! git -C "$ROOT" rev-parse --verify -q "$REF^{commit}" >/dev/null; then
  echo "Unknown ref: $REF" >&2
  exit 1
fi
git -C "$ROOT" archive "$REF" | tar -x -C "$TREE"

# 2. Remove what is never published. Use the list that REF carries; fall back to this checkout's copy.
if [ -f "$TREE/scripts/no_publicar.txt" ]; then
  LIST="$TREE/scripts/no_publicar.txt"
else
  LIST="$ROOT/scripts/no_publicar.txt"
fi
[ -f "$LIST" ] || { echo "Missing scripts/no_publicar.txt." >&2; exit 2; }

ENTRIES=()
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  case "$line" in /*|*..*) echo "Bad entry in no_publicar.txt: $line" >&2; exit 3 ;; esac
  ENTRIES+=("$line")
done < "$LIST"
[ "${#ENTRIES[@]}" -gt 0 ] || { echo "no_publicar.txt lists nothing." >&2; exit 3; }

for entry in "${ENTRIES[@]}"; do
  case "$entry" in
    */) rm -rf "${TREE:?}/${entry%/}" ;;
    *) rm -f "${TREE:?}/$entry" ;;
  esac
done

# 3. The box's runner label must not leak.
CI="$TREE/.github/workflows/ci.yml"
if [ -f "$CI" ]; then
  sed -i 's/runs-on: .*/runs-on: ubuntu-latest/' "$CI"
  if grep -rnE 'runs-on:.*self-hosted' "$TREE/.github" >&2; then
    echo "Refusing: a workflow still names the self-hosted runner." >&2
    exit 3
  fi
fi

# 4. Scan every text file (-I skips binaries). Any hit stops the run before anything is cloned.
# grep exits 1 for "no hits", 0 for hits and 2 for a read error: only 1 passes.
HITS="$(cd "$TREE" && grep -rInE "$SCAN_PATTERN" . 2>&1)" && rc=0 || rc=$?
if [ "$rc" -ne 1 ]; then
  echo "Refusing: private patterns in the tree to publish, or the scan failed (rc=$rc) (file:line:text):" >&2
  echo "$HITS" >&2
  echo "Nothing was pushed." >&2
  exit 3
fi

# 5. Replace the public repo's tree with the sanitized one.
git clone -q "$PUBLIC_REMOTE" "$PUB"
BRANCH="$(git -C "$PUB" symbolic-ref --short HEAD)"
if git -C "$PUB" rev-parse -q --verify HEAD >/dev/null; then
  git -C "$PUB" rm -rqf .
fi
cp -a "$TREE/." "$PUB/"
git -C "$PUB" add -A

# Last guard: nothing from the list may be staged.
for entry in "${ENTRIES[@]}"; do
  if [ -n "$(git -C "$PUB" ls-files -- "${entry%/}")" ]; then
    echo "Refusing: $entry is staged in the public tree." >&2
    exit 3
  fi
done

if git -C "$PUB" diff --cached --quiet; then
  echo "nothing to publish"
  exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry run: would commit to $BRANCH of $PUBLIC_REMOTE, nothing pushed. Changes:"
  git -C "$PUB" diff --cached --stat
  exit 0
fi

# 6. Commit as the owner with the noreply address, then a normal push.
git -C "$PUB" -c user.name="$AUTHOR_NAME" -c user.email="$AUTHOR_EMAIL" -c commit.gpgsign=false \
  commit -q -F "$MESSAGE_FILE"
git -C "$PUB" push -q origin "HEAD:$BRANCH"

# 7. Report, and optionally wait for the public CI.
SHA="$(git -C "$PUB" rev-parse HEAD)"
echo "public: $SHA"

if [ "$VERIFY" -eq 1 ]; then
  deadline=$(( $(date +%s) + ${VERIFY_TIMEOUT:-1800} ))
  state=""
  while [ "$(date +%s)" -lt "$deadline" ]; do
    runs="$(gh run list -R "$PUBLIC_REPO" --commit "$SHA" --json workflowName,status,conclusion \
      --jq '[.[] | select(.workflowName != "rerun-afuera")] | .[0] | "\(.status // "") \(.conclusion // "")"' 2>/dev/null || true)"
    case "$runs" in
      "completed success") state=success; break ;;
      completed*) state=failure; break ;;
    esac
    sleep 20
  done
  if [ "$state" != "success" ]; then
    echo "verify: public CI for $SHA did not succeed (${state:-timed out}); last state: ${runs:-none}" >&2
    exit 4
  fi
  echo "verify: public CI success"
  homepage="$(gh repo view "$PUBLIC_REPO" --json homepageUrl --jq .homepageUrl)"
  if [ "$homepage" != "$SITE_URL" ]; then
    echo "verify: homepageUrl is '$homepage', expected '$SITE_URL'" >&2
    exit 4
  fi
  echo "verify: homepageUrl ok"
fi
