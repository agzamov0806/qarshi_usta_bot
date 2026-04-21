# Git o'rnatilgan bo'lishi kerak: https://git-scm.com/download/win
# Keyin PowerShell (Administrator shart emas):  cd d:\bot ; .\push_to_github.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git topilmadi. Avval o'rnating: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

$origin = "https://github.com/agzamov0806/qarshi_usta_bot.git"

if (-not (Test-Path .git)) {
    git init
    git branch -M main
}

$hasOrigin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    git remote set-url origin $origin
} else {
    git remote add origin $origin
}

git add .
git status
$st = git status --porcelain
if ($st) {
    git commit -m "Initial commit: Usta bot"
} else {
    Write-Host "O'zgarish yo'q (allaqachon commit qilingan bo'lishi mumkin)." -ForegroundColor Yellow
}

git push -u origin main
Write-Host "Tayyor." -ForegroundColor Green
