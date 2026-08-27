@echo off
setlocal
cd /d "%~dp0"
python -B companion\showcase_control.py stop
echo.
pause
