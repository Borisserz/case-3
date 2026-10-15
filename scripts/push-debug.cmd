@echo off
setlocal
cd /d "%~dp0.."

if not exist .git (
  echo Not a git repo.
  exit /b 1
)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddTHHmmss"') do set STAMP=%%I
set BRANCH=debug/runs

echo Collecting out\ and logs\ into debug-bundle\%STAMP%\ ...
if not exist debug-bundle mkdir debug-bundle
mkdir "debug-bundle\%STAMP%" 2>nul
xcopy /E /I /Y /Q out "debug-bundle\%STAMP%\out" >nul
xcopy /E /I /Y /Q logs "debug-bundle\%STAMP%\logs" >nul

git fetch origin 2>nul
git checkout -B %BRANCH%
git add -f "debug-bundle\%STAMP%"
git add -f out logs 2>nul
git status --short

git commit -m "debug: upload run %STAMP% (out+logs)"
if errorlevel 1 (
  echo Nothing to commit or commit failed.
) else (
  git push -u origin %BRANCH%
  echo Pushed to origin/%BRANCH% — open on GitHub for remote debug.
)

endlocal
