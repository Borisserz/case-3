#!/usr/bin/env bash
# Daily: ./scripts/run.sh notes.txt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/run.sh notes.txt [pdf|docx|both] [--dry-run]"
  exit 1
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

INPUT="$1"
FMT="${2:-both}"
EXTRA=()
if [[ "${2:-}" == "--dry-run" ]]; then
  FMT=both
  EXTRA+=(--dry-run)
fi
if [[ "${3:-}" == "--dry-run" ]]; then
  EXTRA+=(--dry-run)
fi
if [[ "$FMT" == "--dry-run" ]]; then
  FMT=both
  EXTRA+=(--dry-run)
fi

python3 -m case3.cli run "$INPUT" --format "$FMT" "${EXTRA[@]}"
echo "OK → out/"
