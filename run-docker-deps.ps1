# Start Postgres + Redis in Docker for local dev (backend/frontend still run on the host).
# Usage: .\run-docker-deps.ps1
# Then:  .\run-dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "Starting Postgres (host :5434) + Redis (host :6381)..." -ForegroundColor Cyan
docker compose up -d postgres redis

if ($LASTEXITCODE -ne 0) {
    Write-Host "docker compose failed. Is Docker Desktop running?" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Use these in backend/.env (already set if you use the Docker template):" -ForegroundColor Green
Write-Host "  DATABASE_URL=postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
Write-Host "  REDIS_URL=redis://127.0.0.1:6381/0"
Write-Host ""
Write-Host "Next: .\run-dev.ps1  then open http://localhost:3000" -ForegroundColor Green
