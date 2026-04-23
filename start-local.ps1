# Start CrucibAI backend (port 8000). Run frontend in a second terminal with start-frontend.ps1
# Run from repo root: .\start-local.ps1

$backendDir = Join-Path $PSScriptRoot "backend"
Set-Location $backendDir

Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: run start-frontend.ps1 in another terminal (from $(Join-Path $PSScriptRoot 'frontend')), then open http://localhost:3000" -ForegroundColor Cyan
Write-Host ""

# run_local.py loads .env from backend dir then starts uvicorn (so env is always correct)
if (Test-Path "run_local.py") {
    python run_local.py
} else {
    python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
}
