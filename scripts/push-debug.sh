#!/usr/bin/env bash
# Upload tex + logs only (no PDF/DOCX) to debug/runs
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BRANCH="debug/runs"
DEST="debug-bundle/${STAMP}"

mkdir -p "$DEST/out" "$DEST/logs"
find out -type f \( -name '*.tex' -o -name '*.json' -o -name '*.txt' \) -exec cp -n {} "$DEST/out/" \; 2>/dev/null || true
find logs -type f \( -name '*.log' -o -name '*.json' -o -name '*.txt' \) -exec cp -n {} "$DEST/logs/" \; 2>/dev/null || true

git fetch origin 2>/dev/null || true
git checkout -B "$BRANCH"
git add -f "$DEST"

if git diff --cached --quiet; then
  echo "Nothing new to push."
  exit 0
fi

git commit -m "debug: ${STAMP} (tex+logs)"
git push -u origin "$BRANCH"
echo "Pushed origin/${BRANCH}"
