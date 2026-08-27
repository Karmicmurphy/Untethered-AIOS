@echo off
setlocal
cd /d "%~dp0"
title Twis Holo Workshop Server

echo.
echo ============================================
echo   TWIS HOLO WORKSHOP
echo ============================================
echo.
if not exist "companion\server.py" (
  echo ERROR: companion\server.py is missing.
  echo Keep this file inside the TWIS folder.
  pause
  exit /b 1
)
if not exist "FLASHRIVER.zip" (
  echo ERROR: FLASHRIVER.zip is missing.
  pause
  exit /b 1
)

set "FLASH_PATH=%~dp0FLASHRIVER.zip"
<nul set /p="%FLASH_PATH%" | clip
echo FlashRiver path copied to clipboard:
echo %FLASH_PATH%
echo.
echo Starting Twis Holo at http://127.0.0.1:8787
echo Keep this black window OPEN while using Twis Holo.
echo In Recover, click the path box and press Ctrl+V.
echo.
start "" "http://127.0.0.1:8787"

where py >nul 2>nul
if %errorlevel%==0 (
  py companion\server.py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python companion\server.py
  ) else (
    echo.
    echo ERROR: Python was not found.
    echo Install Python 3, then run START_TWIS.bat again.
    pause
    exit /b 1
  )
)

echo.
echo The server stopped. The error, if any, is shown above.
pause
