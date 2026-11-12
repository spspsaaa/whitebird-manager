@echo off
setlocal
cd /d "%~dp0"
if not exist "accounts.json" (
 echo Create accounts.json from accounts.example.json first.
 pause
 exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
 echo Python launcher not found. Install Python 3.
 pause
 exit /b 1
)
py -3 whitebird_agent.py --inventory accounts.json status
pause
