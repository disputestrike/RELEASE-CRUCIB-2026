# Start CrucibAI backend (port 8000). Run frontend in a second terminal with start-frontend.ps1
# Run from repo root: .\start-local.ps1

$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot "backend"

function Test-Port($port) {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect("127.0.0.1", $port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(750, $false)) { return $false }
        $client.EndConnect($iar)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: run start-frontend.ps1 in another terminal (from $(Join-Path $PSScriptRoot 'frontend')), then open http://localhost:3000" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Port 5434) -or -not (Test-Port 6381)) {
    Write-Host "Starting local Postgres/Redis dependencies via docker compose..." -ForegroundColor Cyan
    Push-Location $PSScriptRoot
    try {
        docker compose up -d postgres redis
    } catch {
        Write-Warning "Local Docker deps unavailable; falling back to no-DB dev mode for SPA smoke flows."
    } finally {
        Pop-Location
    }
}

Set-Location $backendDir

# Pin local runtime defaults so the backend never inherits stale DATABASE_URL/REDIS_URL
# values from the parent shell. If local deps are unavailable, deliberately run
# without DATABASE_URL so CRUCIBAI_DEV uses the in-memory guest path.
$env:CRUCIBAI_DEV = '1'
$env:CRUCIBAI_SKIP_NODE_VERIFY = '1'
$env:JWT_SECRET = 'dev-secret-do-not-use-in-production-123456'
$env:GOOGLE_CLIENT_ID = 'test.apps.googleusercontent.com'
$env:GOOGLE_CLIENT_SECRET = 'test-google-client-secret'
$env:FRONTEND_URL = 'http://localhost:3000'

if (Test-Port 5434) {
    $env:DATABASE_URL = 'postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'
} else {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
}

if (Test-Port 6381) {
    $env:REDIS_URL = 'redis://127.0.0.1:6381/0'
} else {
    Remove-Item Env:REDIS_URL -ErrorAction SilentlyContinue
}

# run_local.py loads .env from backend dir, but these explicit local defaults remain in
# effect when backend/.env is absent or incomplete.
if (Test-Path "run_local.py") {
    python run_local.py
} else {
    python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
}
