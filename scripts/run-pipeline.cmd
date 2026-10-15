@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist .env (
  echo Missing .env — run scripts\setup-windows.cmd first
  exit /b 1
)

for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
  if not "%%A"=="" set "%%A=%%B"
)

set "JOB=%~1"
if "%JOB%"=="" set "JOB=in\jobs\demo"

set "EXTRA="
if /I "%~2"=="--dry-run" set "EXTRA=--dry-run"

call "%~dp0_resolve-python.cmd"
if errorlevel 1 exit /b 1

echo Running pipeline: %JOB% %EXTRA%
%PY% -m case3.cli run "%JOB%" --format both %EXTRA%
set ERR=!ERRORLEVEL!
if not !ERR!==0 (
  echo FAILED — see logs\  then scripts\push-debug.cmd
  exit /b !ERR!
)
echo OK. Check out\ and logs\
endlocal
