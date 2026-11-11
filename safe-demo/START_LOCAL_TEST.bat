@echo off
setlocal
cd /d "%~dp0"
title WhiteBird Manager - Local Test
echo WhiteBird Manager - local offline checks
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m unittest test_secure_auth test_session_manager test_browser_adapter test_cloud_preflight
  goto done
)
where python >nul 2>nul
if %errorlevel%==0 (
  python -m unittest test_secure_auth test_session_manager test_browser_adapter test_cloud_preflight
  goto done
)
echo Python is not installed or not found.
echo Install Python from python.org, then double-click this file again.
:done
echo.
echo This checks demo code only. It does not open Octo or read WhiteBird balances.
pause
