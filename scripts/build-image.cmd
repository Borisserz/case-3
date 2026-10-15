@echo off
setlocal
cd /d "%~dp0.."
echo Building case-3:tex ...
docker compose build
if errorlevel 1 exit /b 1
echo OK: image case-3:tex
endlocal
