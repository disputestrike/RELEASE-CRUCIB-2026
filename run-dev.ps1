# Run CrucibAI backend + frontend (Windows PowerShell)
# Usage: .\run-dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Start backend in background
$backendDir = Join-Path $root "backend"
Write-Host "Starting backend on http://127.0.0.1:8000 (CRUCIBAI_DEV=1, rate limits off) ..." -ForegroundColor Cyan
# CRUCIBAI_DEV=1: rate limits off + Auto-Runner preflight does not block on Node/npm PATH
# CRUCIBAI_SKIP_NODE_VERIFY=1: verification.compile skips node --check (install Node to enable)
$backendCmd = "set CRUCIBAI_DEV=1&& set CRUCIBAI_SKIP_NODE_VERIFY=1&& cd /d `"$backendDir`" && python -m uvicorn server:app --host 127.0.0.1 --port 8000"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $backendCmd -WindowStyle Normal

Start-Sleep -Seconds 2

# Start frontend (foreground so you see logs)
$frontendDir = Join-Path $root "frontend"
Write-Host "Starting frontend on http://localhost:3000 ..." -ForegroundColor Cyan
Set-Location $frontendDir
& npm start
