@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_github.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Script exited with error code %errorlevel%.
    pause
)
