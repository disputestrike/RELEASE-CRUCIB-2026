# CrucibAI release gate.
# Usage:
#   .\scripts\release-gate.ps1
#   .\scripts\release-gate.ps1 -BackendOnly

param(
    [switch]$BackendOnly
)

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

function Assert-LastExit($label) {
    if ($LASTEXITCODE -ne 0) {
        throw "$label failed with exit code $LASTEXITCODE"
    }
}

Push-Location $root
try {
    Step "Checking tools"
    Require-Command git | Out-Null
    Require-Command python | Out-Null

    Step "Checking backend syntax"
    & python -m py_compile `
        backend\server.py `
        backend\modules_blueprint.py `
        backend\terminal_integration.py `
        backend\provider_readiness.py `
        backend\orchestration\publish_urls.py `
        backend\agents\frontend_agent.py `
        backend\proof\build_contract.py `
        backend\proof\proof_service.py
    Assert-LastExit "py_compile"

    Step "Running backend security and proof smoke"
    if ((-not $env:DATABASE_URL) -or ($env:DATABASE_URL -match "username|password|host|dbname")) {
        $env:DATABASE_URL = "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
    }
    if (-not $env:REDIS_URL) {
        $env:REDIS_URL = "redis://127.0.0.1:6381/0"
    }
    $env:CRUCIBAI_TEST = "1"
    & python -m pytest backend\tests\test_smoke.py `
        -k "phase2 or terminal or job_state or job_proof or run_auto or background_runner or retry_step or app_db or git_sync or railway_deploy or agent_memory or agent_automation or agent_run_generic or agents_from_description or run_agent_action or health_llm or detect_frameworks or deploy" `
        -q
    Assert-LastExit "backend smoke"

    Step "Running late-stage pipeline failure proof tests"
    & python -m pytest backend\tests\test_pipeline_crash_fix.py -q
    Assert-LastExit "pipeline crash fix tests"

    Step "Running repeatability benchmark scorecard"
    & python -m pytest backend\tests\test_repeatability_benchmark.py -q
    Assert-LastExit "repeatability benchmark tests"
    & python scripts\run-repeatability-benchmark.py
    Assert-LastExit "repeatability benchmark scorecard"

    Step "Running Phase 2 route and websocket security audit"
    & python -m pytest backend\tests\test_phase2_security.py -q
    Assert-LastExit "phase 2 security audit tests"
    & python scripts\phase2-security-audit.py --fail-on-unclassified
    Assert-LastExit "phase 2 security audit artifact generation"

    Step "Running provider readiness tests"
    & python -m pytest backend\tests\test_provider_readiness.py -q
    Assert-LastExit "provider readiness tests"

    Step "Running automation bridge tests"
    & python -m pytest backend\tests\test_automation.py -k "run_agent" -q
    Assert-LastExit "automation bridge tests"

    Step "Running LLM routing guard tests"
    & python -m pytest backend\tests\test_tool_agents.py -k "large_cerebras or base_agent" -q
    Assert-LastExit "LLM routing guard tests"

    if (-not $BackendOnly) {
        Step "Checking frontend runtime"
        Require-Command node | Out-Null
        Require-Command npm | Out-Null
        $nodeVersionRaw = (& node --version).Trim()
        $nodeMajor = [int]($nodeVersionRaw.TrimStart("v").Split(".")[0])
        Write-Host "Node: $nodeVersionRaw"
        if ($nodeMajor -lt 18 -or $nodeMajor -gt 22) {
            throw "Unsupported Node version. frontend/package.json supports Node >=18 <=22; use Node 20 or 22."
        }
        if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
            throw "Missing frontend/node_modules. Run: cd frontend; npm install"
        }
        Step "Running frontend tests"
        Push-Location (Join-Path $root "frontend")
        try {
            & npm test -- --watchAll=false --passWithNoTests
            Assert-LastExit "frontend tests"
        } finally {
            Pop-Location
        }
    }

    Step "Checking working tree"
    & git status --short --branch

    Write-Host ""
    Write-Host "Release gate completed." -ForegroundColor Green
} finally {
    Pop-Location
}
