@echo off
REM One-time setup (Python + Docker image). Daily work = run.cmd + push-debug.cmd
setlocal
cd /d "%~dp0.."
echo === case-3 one-time setup ===

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker not found / not running.
  exit /b 1
)

call "%~dp0_resolve-python.cmd"
if errorlevel 1 exit /b 1

if not exist .env (
  copy /Y .env.example .env >nul
  echo Created .env — set VISION_API_BASE_URL
)

%PY% -m pip install -e . -r requirements.txt
if errorlevel 1 exit /b 1

echo Building Docker image case-3:tex ...
docker compose build
if errorlevel 1 exit /b 1

echo.
echo Setup OK. Daily:
echo   1. put notes.txt in project root
echo   2. scripts\run.cmd notes.txt
echo   3. scripts\push-debug.cmd
endlocal
