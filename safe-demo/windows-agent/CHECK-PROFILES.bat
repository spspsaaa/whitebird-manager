@echo off
setlocal
cd /d "%~dp0"
if not exist "accounts.json" (
  echo Create accounts.json from accounts.example.json first.
  pause
  exit /b 1
)
py -3 inventory.py accounts.json
if errorlevel 1 echo Profile inventory validation failed.
pause
