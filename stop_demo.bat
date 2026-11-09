@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\stop_demo.py
) else (
  where py >nul 2>nul
  if not errorlevel 1 (py scripts\stop_demo.py) else (python scripts\stop_demo.py)
)
exit /b %ERRORLEVEL%
