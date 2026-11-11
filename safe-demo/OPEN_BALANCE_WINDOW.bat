@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 local_balance_window.py
  if errorlevel 1 pause
  exit /b
)
where python >nul 2>nul
if %errorlevel%==0 (
  python local_balance_window.py
  if errorlevel 1 pause
  exit /b
)
echo Python not found. Install Python from python.org.
pause
