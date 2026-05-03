# CrucibAI – Run backend, then run proof scripts and report
# Usage: .\run-and-proof.ps1
# Prereqs: MongoDB running, backend/.env with MONGO_URL, DB_NAME, OPENAI_API_KEY or ANTHROPIC_API_KEY

$ErrorActionPreference = "Continue"
$backendDir = Join-Path $PSScriptRoot "backend"

Write-Host "=== CrucibAI Run & Proof ===" -ForegroundColor Cyan
Write-Host ""

# 1. Start backend in background (if not already listening on 8000)
$listening = $null
try {
    $listening = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).Count -gt 0
} catch {}
if (-not $listening) {
    Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Yellow
    $job = Start-Job -ScriptBlock {
        Set-Location $using:backendDir
        python -m uvicorn server:app --host 127.0.0.1 --port 8000
    }
    Start-Sleep -Seconds 4
} else {
    Write-Host "Backend already running on port 8000." -ForegroundColor Green
}

# 2. Run full route proof
Write-Host ""
Write-Host "--- proof_full_routes.py ---" -ForegroundColor Cyan
Set-Location $backendDir
python proof_full_routes.py
$routesExit = $LASTEXITCODE

# 3. Run agent proof
Write-Host ""
Write-Host "--- proof_agents.py ---" -ForegroundColor Cyan
python proof_agents.py
$agentsExit = $LASTEXITCODE

Write-Host ""
if ($routesExit -eq 0 -and $agentsExit -eq 0) {
    Write-Host "All proofs PASSED." -ForegroundColor Green
} else {
    Write-Host "Some proofs failed. Ensure MongoDB is running and backend .env has API keys." -ForegroundColor Yellow
}
Write-Host "See RATE_RANK_COMPARE.md for rate, rank, and comparison."

# Stop the background backend job if we started it
if ($job) {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
}
