@echo off
setlocal
cd /d "%~dp0"
python -B companion\showcase_control.py start
if errorlevel 1 (
  echo.
  echo The showcase did not start. Review the message above.
) else (
  echo.
  echo Share only the trycloudflare.com URL shown above.
)
echo.
pause
