@echo off
chcp 65001 >nul
title GitHub 自動上傳工具
echo ==========================================
echo       GitHub 自動上傳工具 (一鍵更新 Vercel)
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/3] 正在加入變更檔案...
git add .

echo [2/3] 正在提交變更...
set "commit_msg=Auto update %date% %time%"
set /p msg="請輸入更新說明 (直接按 Enter 或等待則使用預設時間): " 

if not "%msg%"=="" (
    set "commit_msg=%msg%"
)

git commit -m "%commit_msg%"

echo.
echo [3/3] 正在上傳至 GitHub 並觸發 Vercel 自動部署...
git push

echo.
echo ==========================================
echo        上傳完成！Vercel 正在自動部署
echo ==========================================
pause
