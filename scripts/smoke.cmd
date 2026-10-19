@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist fixtures\smoke\*.txt (
  echo ERROR: no fixtures\smoke\*.txt
  exit /b 1
)

echo case-3 smoke — fixtures\smoke  ^(format both^)
echo.

set "FAIL=0"
for %%F in (fixtures\smoke\*.txt) do (
  echo ========== %%~nxF ==========
  if /I "%%~nF"=="03_prose_no_numbers" (
    call scripts\run.cmd "%%F" -p "Краткий обзор без графиков и без выдуманных чисел" --format both
  ) else if /I "%%~nF"=="02_wide_table" (
    call scripts\run.cmd "%%F" -p "Отчёт: широкая таблица на всю ширину A4 через tabularx, без landscape" --format both
  ) else (
    call scripts\run.cmd "%%F" -p "Русский отчёт с таблицами и 1-2 графиками по числам из Source" --format both
  )
  if errorlevel 1 (
    echo FAIL %%~nxF
    set "FAIL=1"
  ) else (
    echo OK %%~nxF
  )
  echo.
)

if "!FAIL!"=="1" (
  echo SMOKE FAILED — see runs\logs\ then scripts\push-debug.cmd
  exit /b 1
)
echo SMOKE OK
endlocal
