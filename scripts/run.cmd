@echo off
REM Daily use: scripts\run.cmd notes.txt
REM Optional: scripts\run.cmd notes.txt pdf
REM Optional: scripts\run.cmd notes.txt both --dry-run
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if "%~1"=="" (
  echo Usage: scripts\run.cmd notes.txt [pdf^|docx^|both] [--dry-run]
  echo Put a .txt in the project root, then run this.
  exit /b 1
)

if not exist .env (
  if exist .env.example copy /Y .env.example .env >nul
  echo Created .env — set VISION_API_BASE_URL then re-run.
)

if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)

call "%~dp0_resolve-python.cmd"
if errorlevel 1 exit /b 1

set "INPUT=%~1"
set "FMT=both"
set "EXTRA="
if not "%~2"=="" if /I not "%~2"=="--dry-run" set "FMT=%~2"
if /I "%~2"=="--dry-run" set "EXTRA=--dry-run"
if /I "%~3"=="--dry-run" set "EXTRA=--dry-run"

echo === case-3: %INPUT% → %FMT% ===
%PY% -m case3.cli run "%INPUT%" --format %FMT% %EXTRA%
set ERR=!ERRORLEVEL!
if not !ERR!==0 (
  echo FAILED. See logs\ then: scripts\push-debug.cmd
  exit /b !ERR!
)
echo OK → out\
endlocal
