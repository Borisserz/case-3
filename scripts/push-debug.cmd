@echo off
REM Upload tex + logs (not huge PDFs) to branch debug/runs for remote debug
setlocal
cd /d "%~dp0.."

if not exist .git (
  echo Not a git repo.
  exit /b 1
)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddTHHmmss"') do set STAMP=%%I
set BRANCH=debug/runs
set DEST=debug-bundle\%STAMP%

echo Packing debug bundle %DEST% ...
mkdir "%DEST%\out" 2>nul
mkdir "%DEST%\logs" 2>nul

REM only small debug artifacts
for /r out %%F in (*.tex *.json *.txt) do (
  xcopy /Y /Q "%%F" "%DEST%\out\" >nul 2>&1
)
for /r logs %%F in (*.log *.json *.txt) do (
  xcopy /Y /Q "%%F" "%DEST%\logs\" >nul 2>&1
)

git fetch origin 2>nul
git checkout -B %BRANCH%
git add -f "%DEST%"
git status --short

git commit -m "debug: %STAMP% (tex+logs)"
if errorlevel 1 (
  echo Nothing to commit.
) else (
  git push -u origin %BRANCH%
  echo Pushed origin/%BRANCH%
)

endlocal
