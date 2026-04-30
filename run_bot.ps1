# Botni ishga tushirish. Avval .env da haqiqiy BOT_TOKEN va ADMIN_CHAT_ID bo'lishi kerak.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "XATO: .env yo'q. .env.example dan nusxa oling." -ForegroundColor Red
    exit 1
}

$raw = Get-Content $envFile -Raw
if ($raw -match '(?m)^BOT_TOKEN=(.+)$') {
    $tok = $Matches[1].Trim().Trim('"')
    if ($tok -match '^123456789:' -or $tok -like '*ABCdef*' -or $tok.Length -lt 40) {
        Write-Host @"

XATO: .env dagi BOT_TOKEN namuna yoki noto'g'ri ko'rinadi.
1) Telegramda @BotFather -> /newbot yoki mavjud bot -> API token
2) Loyiha ildizidagi .env ichida BOT_TOKEN=... ni haqiqiy qiymat bilan yozing
3) ADMIN_CHAT_ID=@userinfobot dan olingan raqamingiz bo'lsin

"@ -ForegroundColor Red
        exit 1
    }
}
if ($raw -match '(?m)^ADMIN_CHAT_ID=(\d+)\s*$') {
    if ($Matches[1] -eq "123456789") {
        Write-Host "OGohlantirish: ADMIN_CHAT_ID hali namuna — /admin faqat o'z ID ingizni .env ga yozgach ishlaydi (@userinfobot)." -ForegroundColor Yellow
    }
}

$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "Bot ishga tushmoqda..." -ForegroundColor Cyan
& $py main.py
