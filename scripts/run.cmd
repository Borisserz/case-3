@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if "%~1"=="" (
  echo Usage: scripts\run.cmd notes.txt [pdf^|docx^|both] [--dry-run]
  exit /b 1
)

if not exist .env if exist .env.example copy /Y .env.example .env >nul
if exist .env for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do if not "%%A"=="" set "%%A=%%B"

set "PY="
where python >nul 2>&1 && python -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && for %%V in (3.13 3.12 3.11 3.10 3.9 3) do if not defined PY (
  py -%%V -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=py -%%V"
)
if not defined PY (echo ERROR: Python 3.9+ not on PATH. & exit /b 1)

set "INPUT=%~1"
set "FMT=both"
set "EXTRA="
if not "%~2"=="" if /I not "%~2"=="--dry-run" set "FMT=%~2"
if /I "%~2"=="--dry-run" set "EXTRA=--dry-run"
if /I "%~3"=="--dry-run" set "EXTRA=--dry-run"

echo === %INPUT% → %FMT% ===
%PY% -m case3.cli run "%INPUT%" --format %FMT% %EXTRA%
if errorlevel 1 (
  echo FAILED. See logs\ then scripts\push-debug.cmd
  exit /b 1
)
echo OK → out\
endlocal
