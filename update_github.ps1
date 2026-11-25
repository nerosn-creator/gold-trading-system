[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "GitHub 自動上傳工具"

Set-Location -LiteralPath $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "      GitHub 自動上傳工具 (一鍵更新 Vercel)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] 正在加入變更檔案..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[錯誤] git add 執行失敗。" -ForegroundColor Red
    Read-Host "按 Enter 鍵結束"
    exit 1
}

Write-Host ""
Write-Host "[2/3] 正在提交變更..." -ForegroundColor Yellow
$defaultMsg = "Auto update $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$userMsg = Read-Host "請輸入更新說明 (直接按 Enter 則使用預設時間)"
$commitMsg = if ([string]::IsNullOrWhiteSpace($userMsg)) { $defaultMsg } else { $userMsg.Trim() }

$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "目前沒有任何需要提交的新變更。" -ForegroundColor Green
} else {
    git commit -m $commitMsg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[錯誤] git commit 執行失敗。" -ForegroundColor Red
        Read-Host "按 Enter 鍵結束"
        exit 1
    }
}

Write-Host ""
Write-Host "[3/3] 正在上傳至 GitHub 並觸發 Vercel 自動部署..." -ForegroundColor Yellow
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "[錯誤] git push 執行失敗，請檢查網路連線或 GitHub 登入狀態。" -ForegroundColor Red
    Read-Host "按 Enter 鍵結束"
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "       上傳完成！Vercel 正在自動部署" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Read-Host "按 Enter 鍵關閉視窗"
