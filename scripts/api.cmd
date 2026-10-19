@echo off
setlocal
cd /d "%~dp0.."
if not exist .env if exist .env.example copy /Y .env.example .env >nul
if exist .env for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do if not "%%A"=="" set "%%A=%%B"

set "PY="
where python >nul 2>&1 && python -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && for %%V in (3.13 3.12 3.11 3.10 3.9 3) do if not defined PY (
  py -%%V -c "import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set "PY=py -%%V"
)
if not defined PY (echo ERROR: Python 3.9+ not on PATH. & exit /b 1)

echo.
echo API  → http://127.0.0.1:8000/docs
echo Health→ http://127.0.0.1:8000/api/health
echo Сайт → подними вторым окном: scripts\web.cmd  → http://127.0.0.1:5173
echo.
%PY% -m uvicorn case3.api:app --reload --host 127.0.0.1 --port 8000
endlocal
