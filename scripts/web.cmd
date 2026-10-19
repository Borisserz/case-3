@echo off
setlocal
cd /d "%~dp0..\web"

where node >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Node.js не найден в PATH.
  echo 1^) Скачай LTS: https://nodejs.org/
  echo 2^) Установи с галкой "Add to PATH"
  echo 3^) Закрой ВСЕ окна cmd и открой новые
  echo 4^) Проверка:  node -v   и   npm -v
  echo.
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo ERROR: npm не найден. Переустанови Node.js LTS с https://nodejs.org/
  exit /b 1
)

if not exist node_modules (
  echo npm install…
  call npm.cmd install
  if errorlevel 1 exit /b 1
)

echo UI → http://127.0.0.1:5173  ^(прокси /api → :8000^)
echo Сайт здесь, не на :8000
call npm.cmd run dev
endlocal
