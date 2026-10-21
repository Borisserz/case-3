#!/usr/bin/env bash
# Local Cloudflare Worker for Liber photos (Flux via Workers AI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/workers/case3-image"
if [[ ! -d node_modules ]]; then
  npm install
fi
exec npm run dev
