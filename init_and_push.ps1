# yueji-fl-bridge one-click git init + add + commit + push (v3 fix: UTF-8 BOM + ASCII)
# 拍板 (2026-07-27 02:57 冬生 'B' = Blueprint 流程)
# v3 fix: (1) add UTF-8 BOM for PowerShell 5.1 GBK decoder bug
#         (2) all message in ASCII to avoid CJK decode failure
# Usage: double-click or PowerShell `.\init_and_push.ps1`

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== yueji-fl-bridge one-click init + push (v3) ===" -ForegroundColor Cyan
Write-Host "[cwd] $ScriptDir"

# 1. git init
Write-Host ""
Write-Host "[1/5] git init" -ForegroundColor Yellow
if (-not (Test-Path ".git")) {
    git init | Out-Null
    git branch -M main
    Write-Host "  [ok] .git init done" -ForegroundColor Green
} else {
    Write-Host "  [skip] .git already exists" -ForegroundColor Yellow
}

# 2. CRLF off
Write-Host ""
Write-Host "[2/5] git config core.autocrlf false" -ForegroundColor Yellow
git config core.autocrlf false 2>&1 | Out-Null
git config core.safecrlf false 2>&1 | Out-Null
Write-Host "  [ok] autocrlf=false, safecrlf=false" -ForegroundColor Green

# 3. git add
Write-Host ""
Write-Host "[3/5] git add ." -ForegroundColor Yellow
git add . 2>&1 | Out-Null
$stagedCount = (git diff --cached --name-only 2>$null | Measure-Object -Line).Lines
Write-Host "  [ok] staged $stagedCount files" -ForegroundColor Green

# 4. git commit (use rev-parse --verify HEAD to detect existing commit)
Write-Host ""
Write-Host "[4/5] git commit" -ForegroundColor Yellow
$hasCommit = $false
$null = git rev-parse --verify HEAD 2>&1
if ($LASTEXITCODE -eq 0) {
    $hasCommit = $true
}

if (-not $hasCommit) {
    git commit -m "yueji-fl-bridge v1.0.0: 5 endpoints + FedAvg + Render Blueprint" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [ok] commit done" -ForegroundColor Green
        git log --oneline
    } else {
        Write-Host "  [err] commit failed, please screenshot" -ForegroundColor Red
        git commit -m "yueji-fl-bridge v1.0.0: 5 endpoints + FedAvg + Render Blueprint"
        exit 1
    }
} else {
    Write-Host "  [skip] commit already exists" -ForegroundColor Yellow
    git log --oneline
}

# 5. git remote + push
Write-Host ""
Write-Host "[5/5] git remote + push" -ForegroundColor Yellow
$remoteUrl = "https://github.com/dechang64/yueji-fl-bridge.git"
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote -ne $remoteUrl) {
    if ($existingRemote) {
        Write-Host "  [remote] existing origin = $existingRemote, changing to $remoteUrl" -ForegroundColor Yellow
        git remote set-url origin $remoteUrl
    } else {
        Write-Host "  [remote] adding origin = $remoteUrl" -ForegroundColor Yellow
        git remote add origin $remoteUrl
    }
} else {
    Write-Host "  [remote] origin is already $remoteUrl, skip" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[push] pushing to origin main (will popup GitHub credential dialog)" -ForegroundColor Green
Write-Host "        PAT: https://github.com/settings/tokens/new > tick 'repo' scope > Generate" -ForegroundColor Gray
Write-Host ""
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== DONE ===" -ForegroundColor Green
    Write-Host "Next: Render Dashboard > + New > Blueprint > pick dechang64/yueji-fl-bridge" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[err] push failed, please screenshot" -ForegroundColor Red
}
