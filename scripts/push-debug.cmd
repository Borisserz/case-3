@echo off
REM Push .tex + logs to branch debug/runs (no PDF/DOCX)
setlocal
cd /d "%~dp0.."
if not exist .git (echo Not a git repo. & exit /b 1)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddTHHmmss"') do set STAMP=%%I
set DEST=debug-bundle\%STAMP%
mkdir "%DEST%\out" 2>nul
mkdir "%DEST%\logs" 2>nul
for /r runs\out %%F in (*.tex *.json *.txt) do xcopy /Y /Q "%%F" "%DEST%\out\" >nul 2>&1
for /r runs\logs %%F in (*.log *.json *.txt) do xcopy /Y /Q "%%F" "%DEST%\logs\" >nul 2>&1

git fetch origin 2>nul
git checkout -B debug/runs
git add -f "%DEST%"
git commit -m "debug: %STAMP% (tex+logs)"
if errorlevel 1 (echo Nothing to commit.) else (
  git push -u origin debug/runs
  echo Pushed origin/debug/runs
)
endlocal
