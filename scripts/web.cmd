@echo off
setlocal
cd /d "%~dp0..\web"
if not exist node_modules (
  echo npm install…
  call npm install
  if errorlevel 1 exit /b 1
)
echo UI → http://127.0.0.1:5173  (proxy /api → :8000)
call npm run dev
endlocal
