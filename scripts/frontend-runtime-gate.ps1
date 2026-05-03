# Frontend runtime gate for CrucibAI.
# Writes proof under proof/frontend_runtime_gate and optionally runs frontend tests
# when the active Node version is supported.
#
# Usage:
#   .\scripts\frontend-runtime-gate.ps1
#   .\scripts\frontend-runtime-gate.ps1 -RunFrontendTests

param(
    [string]$ProofDir = "proof/frontend_runtime_gate",
    [switch]$RunFrontendTests,
    [switch]$RunDockerBuild
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$proofRoot = Join-Path $root $ProofDir
$jsonPath = Join-Path $proofRoot "runtime_gate.json"
$matrixPath = Join-Path $proofRoot "PASS_FAIL.md"
$logPath = Join-Path $proofRoot "frontend_test.log"
$dockerLogPath = Join-Path $proofRoot "docker_frontend_build.log"

function Read-Text($path) {
    if (Test-Path $path) {
        return ((Get-Content $path -Raw).Trim())
    }
    return ""
}

function Command-Exists($name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Node-Major($versionRaw) {
    if (-not $versionRaw) { return $null }
    return [int]($versionRaw.TrimStart("v").Split(".")[0])
}

New-Item -ItemType Directory -Force -Path $proofRoot | Out-Null

$nodeVersion = ""
$nodeMajor = $null
if (Command-Exists "node") {
    $nodeVersion = (& node --version).Trim()
    $nodeMajor = Node-Major $nodeVersion
}

$npmVersion = ""
if (Command-Exists "npm") {
    $npmVersion = (& npm --version).Trim()
}

$rootNvmrc = Read-Text (Join-Path $root ".nvmrc")
$frontendNvmrc = Read-Text (Join-Path $root "frontend\.nvmrc")
$frontendPackage = Get-Content (Join-Path $root "frontend\package.json") -Raw | ConvertFrom-Json
$dockerfile = Read-Text (Join-Path $root "Dockerfile")
$ciFiles = Get-ChildItem (Join-Path $root ".github\workflows\*") -Include *.yml,*.yaml -File -ErrorAction SilentlyContinue
$ciNode22 = $false
foreach ($file in $ciFiles) {
    $content = Get-Content $file.FullName -Raw
    if ($content -match "node-version:\s*['""]?22['""]?") {
        $ciNode22 = $true
        break
    }
}

$activeNodeSupported = $false
if ($nodeMajor -ne $null) {
    $activeNodeSupported = ($nodeMajor -ge 18 -and $nodeMajor -le 22)
}
$dockerNode22 = $dockerfile -match "FROM\s+node:22"
$repoHasSupportedPath = ($rootNvmrc -match "^22" -and $frontendNvmrc -match "^22" -and $dockerNode22 -and $ciNode22)

$frontendTest = @{
    requested = [bool]$RunFrontendTests
    status = "not_run"
    exit_code = $null
    log = $logPath
}

$dockerBuild = @{
    requested = [bool]$RunDockerBuild
    status = "not_run"
    exit_code = $null
    log = $dockerLogPath
    command = "docker build --target frontend --progress=plain -t crucibai-frontend-runtime-gate ."
}

if ($RunFrontendTests) {
    if (-not $activeNodeSupported) {
        $frontendTest.status = "blocked_by_active_node"
        "Frontend test not run. Active Node '$nodeVersion' is outside frontend engines '$($frontendPackage.engines.node)'." | Set-Content -Path $logPath -Encoding UTF8
    } elseif (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
        $frontendTest.status = "blocked_missing_node_modules"
        "Frontend test not run. Missing frontend/node_modules. Run: cd frontend; npm ci" | Set-Content -Path $logPath -Encoding UTF8
    } else {
        Push-Location (Join-Path $root "frontend")
        try {
            $env:CI = "true"
            & npm test -- --watchAll=false --passWithNoTests *> $logPath
            $frontendTest.exit_code = $LASTEXITCODE
            $frontendTest.status = if ($LASTEXITCODE -eq 0) { "passed" } else { "failed" }
        } finally {
            Pop-Location
        }
    }
}

if ($RunDockerBuild) {
    if (-not (Command-Exists "docker")) {
        $dockerBuild.status = "blocked_missing_docker"
        "Docker not found on PATH." | Set-Content -Path $dockerLogPath -Encoding UTF8
    } else {
        Push-Location $root
        try {
            $command = "docker build --target frontend --progress=plain -t crucibai-frontend-runtime-gate . > `"$dockerLogPath`" 2>&1"
            & cmd.exe /c $command
            $dockerBuild.exit_code = $LASTEXITCODE
            $dockerBuild.status = if ($LASTEXITCODE -eq 0) { "passed" } else { "failed" }
        } finally {
            Pop-Location
        }
    }
}

$proof = @{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    active_node = @{
        found = [bool]$nodeVersion
        version = $nodeVersion
        major = $nodeMajor
        supported_by_package_engines = $activeNodeSupported
    }
    npm = @{
        found = [bool]$npmVersion
        version = $npmVersion
    }
    frontend_package = @{
        engines_node = $frontendPackage.engines.node
        package_manager = $frontendPackage.packageManager
    }
    supported_execution_paths = @{
        root_nvmrc = $rootNvmrc
        frontend_nvmrc = $frontendNvmrc
        dockerfile_frontend_node22 = $dockerNode22
        github_actions_node22 = $ciNode22
        repo_has_supported_node_path = $repoHasSupportedPath
    }
    frontend_test = $frontendTest
    docker_frontend_build = $dockerBuild
    conclusion = if ($activeNodeSupported) {
        "active_node_supported"
    } elseif ($repoHasSupportedPath) {
        "host_node_blocked_but_repo_has_node22_paths"
    } else {
        "no_supported_node_path_found"
    }
}

$proof | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

$rows = @(
    "| Check | Status | Evidence |",
    "|---|---|---|",
    "| Active Node version | $(if ($activeNodeSupported) { 'PASS' } else { 'FAIL' }) | $nodeVersion vs engines $($frontendPackage.engines.node) |",
    "| Root .nvmrc pins Node 22 | $(if ($rootNvmrc -match '^22') { 'PASS' } else { 'FAIL' }) | .nvmrc=$rootNvmrc |",
    "| Frontend .nvmrc pins Node 22 | $(if ($frontendNvmrc -match '^22') { 'PASS' } else { 'FAIL' }) | frontend/.nvmrc=$frontendNvmrc |",
    "| Docker frontend build uses Node 22 | $(if ($dockerNode22) { 'PASS' } else { 'FAIL' }) | Dockerfile frontend stage |",
    "| GitHub Actions uses Node 22 | $(if ($ciNode22) { 'PASS' } else { 'FAIL' }) | .github/workflows |",
    "| Repo has compliant path despite host Node | $(if ($repoHasSupportedPath) { 'PASS' } else { 'FAIL' }) | nvmrc + Docker + CI |",
    "| Frontend tests | $($frontendTest.status) | $logPath |",
    "| Docker frontend build under Node 22 | $($dockerBuild.status) | $dockerLogPath |"
)
$rows -join "`n" | Set-Content -Path $matrixPath -Encoding UTF8

Write-Host "Frontend runtime gate proof: $jsonPath"
Write-Host "Frontend runtime matrix: $matrixPath"
if (-not $activeNodeSupported -and $repoHasSupportedPath) {
    Write-Host "Active host Node is blocked, but repo now has Node 22 paths (.nvmrc, Dockerfile, CI)." -ForegroundColor Yellow
}
if (-not $repoHasSupportedPath) {
    throw "No complete supported Node execution path found."
}
if ($RunFrontendTests -and $frontendTest.status -eq "failed") {
    throw "Frontend tests failed. See $logPath"
}
if ($RunDockerBuild -and $dockerBuild.status -ne "passed") {
    throw "Docker frontend build failed. See $dockerLogPath"
}
