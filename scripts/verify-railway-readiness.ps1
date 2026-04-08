# Railway deployment readiness verifier for CrucibAI.
# It performs static deploy config checks and optionally probes a live URL.
#
# Usage:
#   .\scripts\verify-railway-readiness.ps1
#   .\scripts\verify-railway-readiness.ps1 -BaseUrl https://your-app.up.railway.app

param(
    [string]$ProofDir = "proof/railway_verification",
    [string]$BaseUrl = "",
    [switch]$RunDockerBuild,
    [switch]$RunContainerHealth,
    [int]$ContainerPort = 18080
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$proofRoot = Join-Path $root $ProofDir
$jsonPath = Join-Path $proofRoot "railway_readiness.json"
$matrixPath = Join-Path $proofRoot "PASS_FAIL.md"
$healthPath = Join-Path $proofRoot "health_check.json"
$dockerBuildLogPath = Join-Path $proofRoot "docker_full_build.log"
$containerLogPath = Join-Path $proofRoot "docker_container_logs.log"
$containerHealthPath = Join-Path $proofRoot "docker_container_health.json"

function Read-Text($path) {
    if (Test-Path $path) { return (Get-Content $path -Raw) }
    return ""
}

New-Item -ItemType Directory -Force -Path $proofRoot | Out-Null

$railwayPath = Join-Path $root "railway.json"
$dockerPath = Join-Path $root "Dockerfile"
$procfilePath = Join-Path $root "Procfile"
$railwayJson = Get-Content $railwayPath -Raw | ConvertFrom-Json
$dockerfile = Read-Text $dockerPath
$procfile = Read-Text $procfilePath

$checks = [ordered]@{
    railway_json_exists = Test-Path $railwayPath
    railway_uses_dockerfile = ($railwayJson.build.builder -eq "DOCKERFILE" -and $railwayJson.build.dockerfilePath -eq "Dockerfile")
    railway_health_path_api_health = ($railwayJson.deploy.healthcheckPath -eq "/api/health")
    dockerfile_exists = Test-Path $dockerPath
    dockerfile_frontend_node22 = ($dockerfile -match "FROM\s+node:22")
    dockerfile_python311_runtime = ($dockerfile -match "FROM\s+python:3\.11")
    dockerfile_static_frontend_copy = ($dockerfile -match "COPY --from=frontend /app/build ./static")
    dockerfile_uvicorn_cmd_uses_port = ($dockerfile -match "uvicorn server:app" -and $dockerfile -match 'PORT')
    dockerfile_healthcheck_api_health = ($dockerfile -match "/api/health")
    dockerfile_copies_full_systems_proof = ($dockerfile -match "proof/full_systems/summary.json" -and $dockerfile -match "proof/full_systems/PASS_FAIL.md")
    procfile_uvicorn_fallback = ($procfile -match "uvicorn server:app")
}

$requiredEnv = @("DATABASE_URL", "JWT_SECRET")
$optionalEnv = @("REDIS_URL", "ANTHROPIC_API_KEY", "CEREBRAS_API_KEY", "FRONTEND_URL", "CORS_ORIGINS", "BACKEND_PUBLIC_URL")
$envMatrix = @{}
foreach ($name in ($requiredEnv + $optionalEnv)) {
    $value = [Environment]::GetEnvironmentVariable($name)
    $envMatrix[$name] = @{
        required = $requiredEnv -contains $name
        set_in_current_shell = -not [string]::IsNullOrWhiteSpace($value)
    }
}

$live = @{
    requested = [bool]$BaseUrl
    status = "not_run"
    url = $BaseUrl
    health_status_code = $null
    health_output = $healthPath
}

$dockerBuild = @{
    requested = [bool]$RunDockerBuild
    status = "not_run"
    exit_code = $null
    log = $dockerBuildLogPath
    command = "docker build --progress=plain -t crucibai-railway-readiness ."
}

$containerHealth = @{
    requested = [bool]$RunContainerHealth
    status = "not_run"
    health_url = "http://127.0.0.1:$ContainerPort/api/health"
    health_output = $containerHealthPath
    log = $containerLogPath
    container_name = "crucibai-railway-proof"
    image = "crucibai-railway-readiness"
}

if ($RunDockerBuild) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $dockerBuild.status = "blocked_missing_docker"
        "Docker not found on PATH." | Set-Content -Path $dockerBuildLogPath -Encoding UTF8
    } else {
        Push-Location $root
        try {
            $command = "docker build --progress=plain -t crucibai-railway-readiness . > `"$dockerBuildLogPath`" 2>&1"
            & cmd.exe /c $command
            $dockerBuild.exit_code = $LASTEXITCODE
            $dockerBuild.status = if ($LASTEXITCODE -eq 0) { "passed" } else { "failed" }
        } finally {
            Pop-Location
        }
    }
}

if ($RunContainerHealth) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $containerHealth.status = "blocked_missing_docker"
        "Docker not found on PATH." | Set-Content -Path $containerLogPath -Encoding UTF8
    } else {
        Push-Location $root
        try {
            & cmd.exe /c "docker rm -f crucibai-railway-proof > NUL 2>&1"
            $dbUrl = "postgresql://crucibai:crucibai@host.docker.internal:5434/crucibai"
            $cid = & docker run -d `
                --name crucibai-railway-proof `
                -p "$ContainerPort`:8000" `
                -e "DATABASE_URL=$dbUrl" `
                -e "REDIS_URL=redis://host.docker.internal:6381/0" `
                -e "JWT_SECRET=docker-proof-jwt-secret-at-least-32-characters-long" `
                -e "FRONTEND_URL=http://localhost:$ContainerPort" `
                -e "GOOGLE_CLIENT_ID=test.apps.googleusercontent.com" `
                -e "GOOGLE_CLIENT_SECRET=test-google-client-secret" `
                -e "CRUCIBAI_TERMINAL_ENABLED=0" `
                crucibai-railway-readiness
            if ($LASTEXITCODE -ne 0) {
                $containerHealth.status = "failed_to_start"
                "docker run failed" | Set-Content -Path $containerLogPath -Encoding UTF8
            } else {
                $containerHealth["container_id"] = "$cid"
                $ok = $false
                $body = ""
                for ($i = 0; $i -lt 60; $i++) {
                    Start-Sleep -Seconds 2
                    try {
                        $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri $containerHealth.health_url
                        $body = $response.Content
                        if ($response.StatusCode -eq 200) {
                            $ok = $true
                            break
                        }
                    } catch {
                        $body = $_.Exception.Message
                    }
                }
                $body | Set-Content -Path $containerHealthPath -Encoding UTF8
                $logsCommand = "docker logs crucibai-railway-proof --tail 220 > `"$containerLogPath`" 2>&1"
                & cmd.exe /c $logsCommand
                $containerHealth.status = if ($ok) { "passed" } else { "failed" }
            }
        } finally {
            & cmd.exe /c "docker rm -f crucibai-railway-proof > NUL 2>&1"
            Pop-Location
        }
    }
}

if ($BaseUrl) {
    $healthUrl = $BaseUrl.TrimEnd("/") + "/api/health"
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 30
        $live.health_status_code = [int]$response.StatusCode
        $live.status = if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { "passed" } else { "failed" }
        $response.Content | Set-Content -Path $healthPath -Encoding UTF8
    } catch {
        $live.status = "failed"
        $_.Exception.Message | Set-Content -Path $healthPath -Encoding UTF8
    }
} else {
    "Live Railway URL not provided; run scripts/verify-railway-readiness.ps1 -BaseUrl https://your-app.up.railway.app" | Set-Content -Path $healthPath -Encoding UTF8
}

$allStaticPass = -not (($checks.GetEnumerator() | Where-Object { -not $_.Value }) | Select-Object -First 1)
$proof = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    static_readiness = if ($allStaticPass) { "passed" } else { "failed" }
    live_confirmation = $live.status
    checks = $checks
    required_env = $requiredEnv
    optional_env = $optionalEnv
    env_matrix = $envMatrix
    docker_build = $dockerBuild
    container_health = $containerHealth
    live = $live
}
$proof | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

$rows = @(
    "| Check | Status | Evidence |",
    "|---|---|---|"
)
foreach ($item in $checks.GetEnumerator()) {
    $rows += "| $($item.Key) | $(if ($item.Value) { 'PASS' } else { 'FAIL' }) | static config |"
}
$rows += "| Live health check | $($live.status) | $($live.health_output) |"
$rows += "| Full Docker image build | $($dockerBuild.status) | $($dockerBuild.log) |"
$rows += "| Local Railway image health check | $($containerHealth.status) | $($containerHealth.health_output); $($containerHealth.log) |"
$rows -join "`n" | Set-Content -Path $matrixPath -Encoding UTF8

Write-Host "Railway readiness proof: $jsonPath"
Write-Host "Railway readiness matrix: $matrixPath"
if (-not $allStaticPass) {
    throw "Railway static readiness failed. See $matrixPath"
}
if ($BaseUrl -and $live.status -ne "passed") {
    throw "Railway live health check failed. See $healthPath"
}
if ($RunDockerBuild -and $dockerBuild.status -ne "passed") {
    throw "Railway Docker build failed. See $dockerBuildLogPath"
}
if ($RunContainerHealth -and $containerHealth.status -ne "passed") {
    throw "Railway image health check failed. See $containerHealthPath and $containerLogPath"
}
