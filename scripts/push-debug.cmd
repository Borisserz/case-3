@echo off
REM Upload runs\ artifacts to a NEW branch debug/upload-STAMP (no PDF/DOCX).
REM Non-interactive: no pause / no more / no pager.
setlocal EnableExtensions
cd /d "%~dp0.."
if not exist .git (echo Not a git repo. & exit /b 1)

set "GIT_PAGER="
set "PAGER="

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddTHHmmss"') do set STAMP=%%I
set "DEST=debug-bundle\%STAMP%"
set "BRANCH=debug/upload-%STAMP%"

mkdir "%DEST%\out" 2>nul
mkdir "%DEST%\logs" 2>nul
mkdir "%DEST%\work" 2>nul
mkdir "%DEST%\uploads" 2>nul

echo [1/4] Copy runs\out logs work uploads → %DEST%
if exist runs\out xcopy /E /I /Y /Q "runs\out\*" "%DEST%\out\" >nul
if exist runs\logs xcopy /E /I /Y /Q "runs\logs\*" "%DEST%\logs\" >nul
if exist runs\work xcopy /E /I /Y /Q "runs\work\*" "%DEST%\work\" >nul
if exist runs\uploads xcopy /E /I /Y /Q "runs\uploads\*" "%DEST%\uploads\" >nul

REM Drop heavy binaries (comment says no PDF/DOCX; keep tex/logs/raw/png).
del /s /q "%DEST%\*.pdf" 2>nul
del /s /q "%DEST%\*.docx" 2>nul

dir /s /b "%DEST%\*.json" "%DEST%\*.tex" "%DEST%\*.txt" "%DEST%\*.log" 2>nul | findstr /r "." >nul
if errorlevel 1 (
  echo FAIL: runs\ пустой. Сначала сделай генерацию в UI, потом снова этот скрипт.
  exit /b 1
)
echo       files ready.

for /f %%I in ('git rev-parse --abbrev-ref HEAD') do set "CURBRANCH=%%I"
echo [2/4] Branch %BRANCH% from %CURBRANCH%
git --no-pager checkout -B "%BRANCH%"
if errorlevel 1 (echo FAIL: git checkout & exit /b 1)

echo [3/4] Commit
git --no-pager add -f "%DEST%"
git --no-pager status --short "%DEST%"
git --no-pager commit -m "debug: %STAMP% (tex+logs+raw)"
if errorlevel 1 (
  echo FAIL: nothing to commit
  git --no-pager checkout "%CURBRANCH%"
  exit /b 1
)

echo [4/4] Push origin %BRANCH%
git --no-pager push -u origin "%BRANCH%"
if errorlevel 1 (
  echo FAIL: git push — проверь логин GitHub / gh auth login
  git --no-pager checkout "%CURBRANCH%"
  exit /b 1
)

git --no-pager checkout "%CURBRANCH%"
echo.
echo OK. Скажи агенту ветку: %BRANCH%
echo https://github.com/Borisserz/case-3/tree/%BRANCH%
endlocal
