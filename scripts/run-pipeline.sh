#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

JOB="${1:-in/jobs/demo}"
EXTRA=()
if [[ "${2:-}" == "--dry-run" ]]; then
  EXTRA+=(--dry-run)
fi

python -m case3.cli run "$JOB" --format both "${EXTRA[@]}"
echo "OK → out/ and logs/"
