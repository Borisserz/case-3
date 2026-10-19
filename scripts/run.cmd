@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

set "HTTP_PROXY="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="
set "ALL_PROXY="
set "all_proxy="

if "%~1"=="" (
  echo Usage:
  echo   scripts\run.cmd notes.txt
  echo   scripts\run.cmd notes.txt -p "сделай PDF с таблицами"
  echo   scripts\run.cmd notes.txt --dry-run
  echo   scripts\run.cmd notes.txt -p "..." --format both
  exit /b 1
)

if not exist .env if exist .env.example copy /Y .env.example .env >nul
if exist .env for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do if not "%%A"=="" set "%%A=%%B"

set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

set "PY="
where python >nul 2>&1 && python -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && for %%V in (3.13 3.12 3.11 3.10 3.9 3) do if not defined PY (
  py -%%V -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=py -%%V"
)
if not defined PY (echo ERROR: Python 3.9+ not on PATH. Run scripts\setup.cmd & exit /b 1)

REM Forward all args to Python CLI
%PY% -m case3.cli run %*
if errorlevel 1 (
  echo FAILED. See runs\logs\ then scripts\push-debug.cmd
  exit /b 1
)
echo OK → runs\out\
endlocal
