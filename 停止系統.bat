@echo off
title 停止黃金交易系統

echo ===================================================
echo   正在停止黃金交易系統與背景連線...
echo ===================================================
echo.

echo [1/1] 清理 8084 埠位與通道進程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8084 "') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM cloudflared_clean.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1

echo.
echo ===================================================
echo   系統與背景連線已完全關閉！
echo ===================================================
pause
