#!/usr/bin/env bash
# Push out/ + logs/ to private repo branch debug/runs for remote debugging.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BRANCH="debug/runs"
DEST="debug-bundle/${STAMP}"

mkdir -p "$DEST"
rsync -a --delete out/ "$DEST/out/" 2>/dev/null || cp -R out "$DEST/out"
rsync -a --delete logs/ "$DEST/logs/" 2>/dev/null || cp -R logs "$DEST/logs"

git fetch origin 2>/dev/null || true
git checkout -B "$BRANCH"
git add -f "$DEST"
git add -f out logs 2>/dev/null || true

if git diff --cached --quiet; then
  echo "Nothing new to push."
  exit 0
fi

git commit -m "debug: upload run ${STAMP} (out+logs)"
git push -u origin "$BRANCH"
echo "Pushed origin/${BRANCH} — share the commit with Cursor for remote debug."
