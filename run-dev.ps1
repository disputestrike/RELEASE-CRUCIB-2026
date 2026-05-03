# Run CrucibAI backend + frontend on Windows PowerShell.
# Usage: .\run-dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

function Require-Command($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Missing required command: $name"
    }
    return $cmd
}

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

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

Write-Step "Checking toolchain"
Require-Command git | Out-Null
Require-Command python | Out-Null
Require-Command node | Out-Null
Require-Command npm | Out-Null

$nodeVersionRaw = (& node --version).Trim()
$nodeMajor = [int]($nodeVersionRaw.TrimStart("v").Split(".")[0])
Write-Host "Node: $nodeVersionRaw"
if ($nodeMajor -lt 18 -or $nodeMajor -gt 22) {
    throw "Unsupported Node version. Run 'nvm use' from the repo root (repo pins Node 22) or use Docker; frontend/package.json supports Node >=18 <=22."
}

Write-Step "Ensuring Postgres and Redis are available"
if (-not (Test-Port 5434) -or -not (Test-Port 6381)) {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        throw "Postgres/Redis are not reachable on 5434/6381 and Docker is not available. Run Docker Desktop or start Postgres/Redis manually."
    }
    Push-Location $root
    try {
        & docker compose up -d postgres redis
    } finally {
        Pop-Location
    }
}

Write-Step "Ensuring frontend dependencies"
$nodeModules = Join-Path $frontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Push-Location $frontendDir
    try {
        & npm install
    } finally {
        Pop-Location
    }
} else {
    Write-Host "frontend/node_modules found"
}

Write-Step "Starting backend on http://127.0.0.1:8000"
$backendScript = @"
`$ErrorActionPreference = 'Stop'
Set-Location '$backendDir'
`$env:CRUCIBAI_DEV = '1'
`$env:CRUCIBAI_SKIP_NODE_VERIFY = '1'
`$env:DATABASE_URL = 'postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai'
`$env:REDIS_URL = 'redis://127.0.0.1:6381/0'
`$env:JWT_SECRET = 'dev-secret-do-not-use-in-production-123456'
`$env:GOOGLE_CLIENT_ID = 'test.apps.googleusercontent.com'
`$env:GOOGLE_CLIENT_SECRET = 'test-google-client-secret'
`$env:FRONTEND_URL = 'http://localhost:3000'
python -m uvicorn server:app --host 127.0.0.1 --port 8000
"@
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendScript -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Step "Starting frontend on http://localhost:3000"
Set-Location $frontendDir
$env:REACT_APP_BACKEND_URL = "http://127.0.0.1:8000"
$env:DISABLE_ESLINT_PLUGIN = "true"
& npm start
