@echo off
REM One-time: Python + Docker image. Daily = run.cmd + push-debug.cmd
setlocal
cd /d "%~dp0.."
echo === case-3 setup ===

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker not installed.
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker Desktop Engine not running.
  echo Open Docker Desktop. If "Virtualization support not detected" — see README.
  exit /b 1
)

call "%~dp0_resolve-python.cmd"
if errorlevel 1 exit /b 1

if not exist .env (
  copy /Y .env.example .env >nul
  echo Created .env — set VISION_API_BASE_URL to your Qwen host
)

%PY% -m pip install -e .
if errorlevel 1 exit /b 1

echo Building case-3:tex ...
docker compose build
if errorlevel 1 exit /b 1

echo.
echo OK. Daily:
echo   1. put notes.txt in project root
echo   2. scripts\run.cmd notes.txt
echo   3. scripts\push-debug.cmd
endlocal
