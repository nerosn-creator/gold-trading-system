@echo off
title Gold Trading System Launcher (Port 8084)

echo ===================================================
echo   黃金自動化技術指標與買賣訊號系統 (Port 8084)
echo ===================================================
echo.
echo [1/3] 清理舊有的 8084 埠位與背景通道進程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8084 "') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /F /IM cloudflared_clean.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1

echo [2/3] 啟動後端 API 伺服器 (0.0.0.0:8084)...
cd /d "%~dp0"
if exist tunnel.log del /f /q tunnel.log
start /b py backend/main.py

echo [3/3] 啟動 Ngrok 固定網址通道中...
start /b ngrok.exe http --url https://rethink-guacamole-curve.ngrok-free.dev 8084 --log=stdout > tunnel.log 2>&1

timeout /t 5 /nobreak >nul

echo.
echo ===================================================
echo  黃金交易系統與 Ngrok 專屬通道已成功啟動！
echo  局域網內網網址 (同 WiFi 手機): http://192.168.100.33:8084
echo.
echo  【您的專屬固定外網網址 (永久不變)】:
echo  https://rethink-guacamole-curve.ngrok-free.dev
echo ===================================================
pause
