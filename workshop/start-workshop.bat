@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Twis Holo Workshop Launcher

echo ==============================================
echo  TWIS HOLO WORKSHOP - STARTUP CHECK
echo ==============================================
echo.

set "PYEXE="
where py.exe >nul 2>nul
if not errorlevel 1 set "PYEXE=py.exe"
if not defined PYEXE (
  where python.exe >nul 2>nul
  if not errorlevel 1 set "PYEXE=python.exe"
)

if not defined PYEXE (
  echo Python 3 was not found on this computer.
  echo.
  echo Twis Holo's FlashRiver import requires Python 3.
  echo The browser-only screen can open, but Import FlashRiver will not work.
  echo.
  echo Opening the browser-only screen now...
  start "" "%~dp0app\index.html"
  echo.
  echo Install Python 3, then run this file again.
  echo During installation, check: Add python.exe to PATH
  echo.
  pause
  exit /b 2
)

echo Found Python: %PYEXE%
%PYEXE% --version
if errorlevel 1 (
  echo.
  echo Python was found but could not run.
  echo Repair or reinstall Python 3, then try again.
  pause
  exit /b 3
)

echo.
echo Starting the local Twis Holo server...
start "Twis Holo Local Server" /min cmd /c "cd /d ""%~dp0"" && %PYEXE% companion\server.py"

rem Give the server a moment to bind before opening the browser.
>nul 2>nul ping 127.0.0.1 -n 3
start "" "http://127.0.0.1:8787"

echo.
echo Twis Holo should now open in your browser.
echo Keep the server window running while you use the Workshop.
echo.
echo If the browser says it cannot connect, run:
echo   %PYEXE% "%~dp0companion\server.py"
echo and read the error shown.
echo.
pause
