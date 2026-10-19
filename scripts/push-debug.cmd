@echo off
REM Upload runs artifacts to origin/debug/runs (no PDF/DOCX)
setlocal EnableExtensions
cd /d "%~dp0.."
if not exist .git (echo Not a git repo. & exit /b 1)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddTHHmmss"') do set STAMP=%%I
set "DEST=debug-bundle\%STAMP%"
mkdir "%DEST%\out" 2>nul
mkdir "%DEST%\logs" 2>nul
mkdir "%DEST%\work" 2>nul

echo Collecting runs\ ...
if exist runs\out xcopy /E /I /Y /Q "runs\out\*" "%DEST%\out\" >nul
if exist runs\logs xcopy /E /I /Y /Q "runs\logs\*" "%DEST%\logs\" >nul
if exist runs\work xcopy /E /I /Y /Q "runs\work\*" "%DEST%\work\" >nul

dir /s /b "%DEST%\*.json" "%DEST%\*.tex" "%DEST%\*.txt" "%DEST%\*.log" 2>nul | findstr /r "." >nul
if errorlevel 1 (
  echo Nothing to upload under runs\out logs work.
  echo Generate a document first, then run this again.
  exit /b 1
)

for /f %%I in ('git rev-parse --abbrev-ref HEAD') do set "CURBRANCH=%%I"

git fetch origin 2>nul
git stash push -u -m "push-debug-%STAMP%" --quiet 2>nul

git checkout -B debug/runs origin/debug/runs 2>nul
if errorlevel 1 git checkout -B debug/runs

git stash pop --quiet 2>nul

git add -f "%DEST%"
git commit -m "debug: %STAMP% (tex+logs+raw)"
if errorlevel 1 (
  echo Nothing new to commit — maybe already uploaded?
) else (
  git push -u origin debug/runs
  if errorlevel 1 (echo PUSH FAILED) else (echo OK pushed %DEST% → origin/debug/runs)
)

git checkout "%CURBRANCH%" --quiet 2>nul
git stash pop --quiet 2>nul
echo Back on branch %CURBRANCH%
endlocal
