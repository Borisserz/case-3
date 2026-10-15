@echo off
setlocal
cd /d "%~dp0.."
echo === case-3 Windows setup ===

where docker >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker not found. Install Docker Desktop and restart.
  exit /b 1
)

set "PY=python"
where py >nul 2>&1 && set "PY=py -3.11"
where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ and add to PATH.
    exit /b 1
  )
)

if not exist .env (
  copy /Y .env.example .env >nul
  echo Created .env — set VISION_API_BASE_URL to your Qwen host.
)

%PY% -m pip install -e . -r requirements.txt
if errorlevel 1 exit /b 1

call scripts\build-image.cmd
if errorlevel 1 exit /b 1

echo.
echo Setup done. Next:
echo   1. Edit .env  ^(VISION_API_BASE_URL^)
echo   2. scripts\run-pipeline.cmd in\jobs\demo
echo   3. scripts\push-debug.cmd
endlocal
