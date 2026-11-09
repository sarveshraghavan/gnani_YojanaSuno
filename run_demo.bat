@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=mock"
if /i not "%MODE%"=="mock" if /i not "%MODE%"=="live" (
  echo Usage: run_demo.bat [mock^|live]
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  set "PYTHON_LAUNCHER="
  where py >nul 2>nul
  if not errorlevel 1 (
    py -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_LAUNCHER=py"
  )
  if not defined PYTHON_LAUNCHER (
    where python >nul 2>nul
    if not errorlevel 1 (
      python -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
      if not errorlevel 1 set "PYTHON_LAUNCHER=python"
    )
  )
  if not defined PYTHON_LAUNCHER (echo Python 3.11+ is required. Install Python and retry.& exit /b 2)
  if "!PYTHON_LAUNCHER!"=="py" (py -m venv .venv) else (python -m venv .venv)
  if errorlevel 1 exit /b 2
  call ".venv\Scripts\activate.bat"
  python -m pip install -r requirements-demo.txt
  if errorlevel 1 exit /b 2
) else (
  call ".venv\Scripts\activate.bat"
)
python -c "import fastapi,uvicorn,httpx,yaml,pydantic_settings,multipart,dotenv,pytest" >nul 2>nul
if errorlevel 1 (
  echo Installing the pinned demo dependencies...
  python -m pip install -r requirements-demo.txt
  if errorlevel 1 exit /b 2
)
python scripts\demo.py %MODE%
exit /b %ERRORLEVEL%
