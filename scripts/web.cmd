@echo off
setlocal EnableExtensions
cd /d "%~dp0..\web"

REM Find node even when PATH is broken (common on Windows / Cursor terminal)
set "NODE_EXE="
if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
if not defined NODE_EXE if exist "%ProgramFiles(x86)%\nodejs\node.exe" set "NODE_EXE=%ProgramFiles(x86)%\nodejs\node.exe"
if not defined NODE_EXE if exist "%LocalAppData%\Programs\node\node.exe" set "NODE_EXE=%LocalAppData%\Programs\node\node.exe"
if not defined NODE_EXE (
  where node >nul 2>&1 && for /f "delims=" %%I in ('where node') do (
    if not defined NODE_EXE set "NODE_EXE=%%I"
  )
)

if not defined NODE_EXE (
  echo.
  echo ERROR: node.exe не найден.
  echo 1^) Поставь: https://nodejs.org/dist/v24.22.0/node-v24.22.0-x64.msi
  echo 2^) Проверь файл:  dir "%%ProgramFiles%%\nodejs\node.exe"
  echo 3^) Полная инструкция: docs\WINDOWS_NODE.md  и README сверху
  echo.
  exit /b 1
)

for %%I in ("%NODE_EXE%") do set "NODE_DIR=%%~dpI"
set "PATH=%NODE_DIR%;%PATH%"
set "NPM_CMD=%NODE_DIR%npm.cmd"

echo Using: %NODE_EXE%
"%NODE_EXE%" -v
if exist "%NPM_CMD%" (
  call "%NPM_CMD%" -v
) else (
  echo ERROR: npm.cmd рядом с node не найден: %NPM_CMD%
  exit /b 1
)

if not exist node_modules (
  echo npm install…
  call "%NPM_CMD%" install
  if errorlevel 1 exit /b 1
)

echo.
echo UI → http://127.0.0.1:5173  ^(прокси /api → :8000^)
echo Сайт здесь. API отдельно: scripts\api.cmd
echo.
call "%NPM_CMD%" run dev
endlocal
