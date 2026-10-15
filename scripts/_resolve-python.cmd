@echo off
REM Sets PY to a working Python 3 launcher. Prefer `python` on PATH (3.12 ok).
set "PY="

where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PY=python"
    goto :done
  )
)

where py >nul 2>&1
if not errorlevel 1 (
  for %%V in (3.13 3.12 3.11 3.10 3.9 3) do (
    if not defined PY (
      py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
      if not errorlevel 1 set "PY=py -%%V"
    )
  )
)

:done
if not defined PY (
  echo ERROR: Python 3.9+ not found. Install from python.org and tick "Add to PATH".
  echo Tried: python, py -3.13 .. py -3
  exit /b 1
)
echo Using: %PY%
exit /b 0
