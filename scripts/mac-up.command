#!/bin/bash
# Double-click or: open scripts/mac-up.command
# Starts Liber on Mac outside Cursor sandbox (Docker + API + Vite + image worker).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== case-3 Mac up ==="
echo "root: $ROOT"

# Docker Desktop
if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop..."
  open -a "Docker Desktop" 2>/dev/null || open "/Applications/Docker.app/Contents/MacOS/Docker Desktop.app" 2>/dev/null || true
  for i in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      echo "Docker ready ($i)"
      break
    fi
    sleep 2
  done
fi
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker not ready. Open Docker Desktop manually, then re-run."
  read -r -p "Press Enter to close..."
  exit 1
fi

if ! docker image inspect case-3:tex >/dev/null 2>&1; then
  echo "Building case-3:tex..."
  docker compose build
fi

export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
if [[ -f .env ]]; then set -a; # shellcheck disable=SC1091
  source .env
  set +a
fi
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy || true

# Playwright chromium if missing
if ! "$ROOT/.venv/bin/python" -c "from playwright.sync_api import sync_playwright
with sync_playwright() as p:
  b=p.chromium.launch(headless=True); b.close()" 2>/dev/null; then
  echo "Installing Playwright Chromium..."
  "$ROOT/.venv/bin/playwright" install chromium || true
fi

# Free ports
for p in 8000 5173 8787; do
  PIDS=$(lsof -tiTCP:$p -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "${PIDS:-}" ]]; then
    echo "Free :$p ($PIDS)"
    kill -9 $PIDS 2>/dev/null || true
  fi
done
sleep 1

mkdir -p /tmp/case3-mac
LOG=/tmp/case3-mac

echo "API :8000..."
nohup "$ROOT/.venv/bin/uvicorn" case3.api:app --host 127.0.0.1 --port 8000 >"$LOG/api.log" 2>&1 &
echo $! >"$LOG/api.pid"

echo "Vite :5173..."
(cd "$ROOT/web" && nohup npm run dev -- --host 127.0.0.1 --port 5173 >"$LOG/web.log" 2>&1 & echo $! >"$LOG/web.pid")

if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "Image worker :8787..."
  (cd "$ROOT/workers/case3-image" && nohup npm run dev >"$LOG/image.log" 2>&1 & echo $! >"$LOG/image.pid")
else
  echo "SKIP image worker — set CLOUDFLARE_API_TOKEN in .env for local Flux photos"
fi

sleep 3
echo
echo "--- health ---"
curl -sS -m 5 http://127.0.0.1:8000/api/health | python3 -m json.tool | head -40 || true
echo
echo "UI:  http://127.0.0.1:5173"
echo "API: http://127.0.0.1:8000/docs"
echo "logs: $LOG/"
echo
read -r -p "Press Enter to close this window (services keep running)..."
