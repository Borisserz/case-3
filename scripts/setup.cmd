@echo off
setlocal
cd /d "%~dp0.."
echo === case-3 setup (one-time) ===

where docker >nul 2>&1 || (echo ERROR: Docker not installed. & exit /b 1)
docker info >nul 2>&1 || (
  echo ERROR: Docker Engine not running. Open Docker Desktop.
  exit /b 1
)

set "PY="
where python >nul 2>&1 && python -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && for %%V in (3.13 3.12 3.11 3.10 3.9 3) do if not defined PY (
  py -%%V -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=py -%%V"
)
if not defined PY (echo ERROR: Python 3.9+ not on PATH. & exit /b 1)
echo Using: %PY%

if not exist .env (
  copy /Y .env.example .env >nul
  echo Created .env — set VISION_API_BASE_URL
)

%PY% -m pip install -e .
if errorlevel 1 exit /b 1

echo Installing Playwright Chromium (HTML charts)...
%PY% -m playwright install chromium
if errorlevel 1 (
  echo WARNING: playwright chromium install failed — charts will be skipped until fixed.
)

echo Building case-3:tex ...
docker compose build
if errorlevel 1 exit /b 1

echo.
echo OK. Next:
echo   CLI:  scripts\run.cmd notes.txt -p "отчёт" --dry-run
echo   UI:   scripts\api.cmd   then   scripts\web.cmd
echo         ^(Node 18+ needed for web^)  → http://127.0.0.1:5173
echo   Edit .env: VISION_API_BASE_URL, CASE3_MAX_CHARTS
endlocal
