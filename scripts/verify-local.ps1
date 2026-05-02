# Verify the local CrucibAI checkout has the basics needed to run.
# Usage: .\scripts\verify-local.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Require-Command($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Missing required command: $name"
    }
    return $cmd
}

Step "Checking required commands"
Require-Command git | Out-Null
Require-Command python | Out-Null
Require-Command node | Out-Null
Require-Command npm | Out-Null

Step "Checking Node version"
$nodeVersionRaw = (& node --version).Trim()
$nodeMajor = [int]($nodeVersionRaw.TrimStart("v").Split(".")[0])
Write-Host "Node: $nodeVersionRaw"
$frontendRuntimeSupported = $true
if ($nodeMajor -lt 18 -or $nodeMajor -gt 22) {
    $frontendRuntimeSupported = $false
    & (Join-Path $root "scripts\frontend-runtime-gate.ps1")
    Write-Warning "Active Node is unsupported for local frontend execution. Use 'nvm use' from the repo root, or run the Docker/GitHub Actions Node 22 path."
}

Step "Checking Python version"
& python --version

Step "Checking frontend dependencies"
$nodeModules = Join-Path $root "frontend\node_modules"
if (-not $frontendRuntimeSupported) {
    Write-Warning "Skipping frontend/node_modules check because active Node is unsupported."
} elseif (-not (Test-Path $nodeModules)) {
    throw "Missing frontend/node_modules. Run: cd frontend; npm install"
} else {
    Write-Host "frontend/node_modules found"
}

Step "Checking backend import in dev mode"
$env:CRUCIBAI_DEV = "1"
$env:JWT_SECRET = "dev-secret-do-not-use-in-production-123456"
$env:GOOGLE_CLIENT_ID = "test.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "test-google-client-secret"
$env:FRONTEND_URL = "http://localhost:3000"
Push-Location $root
try {
    & python -c "import sys; sys.path.insert(0, 'backend'); import server; print('backend import ok')"
} finally {
    Pop-Location
}

Step "Checking git status"
Push-Location $root
try {
    & git status --short --branch
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Local verification completed." -ForegroundColor Green
