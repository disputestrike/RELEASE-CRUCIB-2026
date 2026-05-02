# CrucibAI full systems gate.
# Runs the broad release-hardening proof path and writes a PASS/FAIL bundle.
#
# Usage:
#   .\scripts\full-systems-test.ps1
#   .\scripts\full-systems-test.ps1 -SkipDocker -SkipLive

param(
    [string]$ProofDir = "proof/full_systems",
    [string]$BaseUrl = "https://crucibai-production.up.railway.app",
    [switch]$SkipDocker,
    [switch]$SkipLive,
    [switch]$SkipFrontendDocker,
    [switch]$SkipRailwayContainerHealth
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$proofRoot = Join-Path $root $ProofDir
$summaryPath = Join-Path $proofRoot "summary.json"
$matrixPath = Join-Path $proofRoot "PASS_FAIL.md"

New-Item -ItemType Directory -Force -Path $proofRoot | Out-Null

$script:results = @()
$script:hadRequiredFailure = $false

function Format-LogFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    $lines = @(Get-Content -LiteralPath $Path)
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
        if ($lines.Count -eq 1) {
            $lines = @()
        } else {
            $lines = @($lines[0..($lines.Count - 2)])
        }
    }
    if ($null -eq $lines) {
        "" | Set-Content -LiteralPath $Path -Encoding UTF8 -NoNewline
        return
    }
    if ($lines.Count -eq 0) {
        "" | Set-Content -LiteralPath $Path -Encoding UTF8 -NoNewline
        return
    }
    $lines | ForEach-Object { $_.TrimEnd() } | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Invoke-Gate {
    param(
        [string]$Name,
        [string]$Command,
        [scriptblock]$Script,
        [string]$LogName,
        [bool]$Required = $true
    )

    $logPath = Join-Path $proofRoot $LogName
    $started = Get-Date
    $exitCode = 0
    $status = "PASS"
    $errorText = $null

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    Write-Host $Command

    try {
        $global:LASTEXITCODE = 0
        $oldErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & $Script *>&1 | Out-File -FilePath $logPath -Encoding UTF8
        } finally {
            $ErrorActionPreference = $oldErrorActionPreference
        }
        $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($exitCode -ne 0) {
            $status = "FAIL"
        }
    } catch {
        $status = "FAIL"
        $exitCode = 1
        $errorText = $_.Exception.Message
        "`nERROR: $errorText" | Add-Content -Path $logPath -Encoding UTF8
    }

    Format-LogFile -Path $logPath

    $ended = Get-Date
    $duration = [math]::Round(($ended - $started).TotalSeconds, 2)
    if ($Required -and $status -ne "PASS") {
        $script:hadRequiredFailure = $true
    }

    $script:results += [ordered]@{
        name = $Name
        required = $Required
        status = $status
        exit_code = $exitCode
        command = $Command
        log = $logPath
        duration_seconds = $duration
        error = $errorText
    }

    if ($status -eq "PASS") {
        Write-Host "PASS: $Name ($duration sec)" -ForegroundColor Green
    } else {
        Write-Host "FAIL: $Name ($duration sec) - see $logPath" -ForegroundColor Red
    }
}

Push-Location $root
try {
    if ((-not $env:DATABASE_URL) -or ($env:DATABASE_URL -match "username|password|host|dbname")) {
        $env:DATABASE_URL = "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
    }
    if (-not $env:REDIS_URL) {
        $env:REDIS_URL = "redis://127.0.0.1:6381/0"
    }
    if (-not $env:JWT_SECRET) {
        $env:JWT_SECRET = "full-systems-jwt-secret-at-least-32-characters-long"
    }
    $env:CRUCIBAI_TEST = "1"
    $env:CRUCIBAI_DEV = "1"

    Invoke-Gate `
        -Name "Git diff whitespace check" `
        -Command "git diff --check" `
        -LogName "git_diff_check.log" `
        -Script { & git diff --check }

    Invoke-Gate `
        -Name "Backend syntax compile" `
        -Command "python -m py_compile critical backend/scripts" `
        -LogName "py_compile.log" `
        -Script {
            & python -m py_compile `
                backend\server.py `
                backend\modules_blueprint.py `
                backend\terminal_integration.py `
                backend\provider_readiness.py `
                backend\orchestration\publish_urls.py `
                backend\routes\trust.py `
                backend\routes\community.py `
                backend\agents\frontend_agent.py `
                backend\proof\build_contract.py `
                backend\proof\proof_service.py `
                scripts\live-production-golden-path.py `
                scripts\run-repeatability-benchmark.py `
                scripts\golden-path-ux-audit.py `
                scripts\fortune100-preflight.py
        }

    Invoke-Gate `
        -Name "Backend full pytest suite" `
        -Command "python -m pytest backend\tests -q --tb=short" `
        -LogName "backend_all_pytest.log" `
        -Script { & python -m pytest backend\tests -q --tb=short }

    Invoke-Gate `
        -Name "Backend release gate" `
        -Command ".\scripts\release-gate.ps1 -BackendOnly" `
        -LogName "release_gate_backend.log" `
        -Script { & .\scripts\release-gate.ps1 -BackendOnly }

    Invoke-Gate `
        -Name "Golden path UX source audit" `
        -Command "python scripts\golden-path-ux-audit.py --proof-dir proof\full_systems\golden_path_ux" `
        -LogName "golden_path_ux_audit.log" `
        -Required $false `
        -Script { & python scripts\golden-path-ux-audit.py --proof-dir (Join-Path $ProofDir "golden_path_ux") }

    if (-not $SkipFrontendDocker) {
        Invoke-Gate `
            -Name "Frontend Node 22 Docker runtime gate" `
            -Command ".\scripts\frontend-runtime-gate.ps1 -RunDockerBuild" `
            -LogName "frontend_runtime_gate.log" `
            -Script { & .\scripts\frontend-runtime-gate.ps1 -RunDockerBuild }
    }

    $railwayCommand = ".\scripts\verify-railway-readiness.ps1"
    if (-not $SkipLive) {
        $railwayCommand += " -BaseUrl $BaseUrl"
    }
    if (-not $SkipDocker) {
        $railwayCommand += " -RunDockerBuild"
        if (-not $SkipRailwayContainerHealth) {
            $railwayCommand += " -RunContainerHealth"
        }
    }
    Invoke-Gate `
        -Name "Railway readiness and smoke" `
        -Command $railwayCommand `
        -LogName "railway_readiness.log" `
        -Required $false `
        -Script {
            $railwayArgs = @{
                ProofDir = Join-Path $ProofDir "railway_verification"
            }
            if (-not $SkipLive) {
                $railwayArgs.BaseUrl = $BaseUrl
            }
            if (-not $SkipDocker) {
                $railwayArgs.RunDockerBuild = $true
                if (-not $SkipRailwayContainerHealth) {
                    $railwayArgs.RunContainerHealth = $true
                }
            }
            & .\scripts\verify-railway-readiness.ps1 @railwayArgs
        }

    if (-not $SkipLive) {
        Invoke-Gate `
            -Name "Fortune 100 public trust preflight" `
            -Command "python scripts\fortune100-preflight.py --base-url $BaseUrl --proof-dir proof\full_systems\fortune100_preflight" `
            -LogName "fortune100_preflight.log" `
            -Script {
                & python scripts\fortune100-preflight.py --base-url $BaseUrl --proof-dir (Join-Path $ProofDir "fortune100_preflight")
                $preflightExit = $LASTEXITCODE
                $preflightMatrix = Join-Path $root (Join-Path $ProofDir "fortune100_preflight\PASS_FAIL.md")
                if (Test-Path $preflightMatrix) {
                    Get-Content -Path $preflightMatrix
                }
                $global:LASTEXITCODE = $preflightExit
            }

        Invoke-Gate `
            -Name "Live production golden path" `
            -Command "python scripts\live-production-golden-path.py --base-url $BaseUrl --timeout-sec 1200 --poll-sec 8 --request-timeout-sec 90" `
            -LogName "live_production_golden_path.log" `
            -Script {
                & python scripts\live-production-golden-path.py --base-url $BaseUrl --timeout-sec 1200 --poll-sec 8 --request-timeout-sec 90
                $liveExit = $LASTEXITCODE
                $liveMatrix = Join-Path $root "proof\live_production_golden_path\PASS_FAIL.md"
                if (Test-Path $liveMatrix) {
                    Get-Content -Path $liveMatrix
                }
                $global:LASTEXITCODE = $liveExit
            }
    }
} finally {
    Pop-Location
}

$summary = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    base_url = if ($SkipLive) { $null } else { $BaseUrl }
    required_failures = @($script:results | Where-Object { $_.required -and $_.status -ne "PASS" }).Count
    results = $script:results
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

$rows = @(
    "# Full Systems Gate",
    "",
    "Generated: $($summary.generated_at)",
    "",
    "| Gate | Required | Status | Log |",
    "|---|---:|---|---|"
)
foreach ($item in $script:results) {
    $rows += "| $($item.name) | $($item.required) | $($item.status) | $($item.log) |"
}
$rows += ""
$rows += "Required failures: $($summary.required_failures)"
$rows -join "`n" | Set-Content -Path $matrixPath -Encoding UTF8

Write-Host ""
Write-Host "Full systems summary: $summaryPath"
Write-Host "Full systems matrix: $matrixPath"

if ($script:hadRequiredFailure) {
    throw "Full systems gate failed. See $matrixPath"
}

Write-Host "Full systems gate passed." -ForegroundColor Green
