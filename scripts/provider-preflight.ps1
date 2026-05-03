# Write LLM provider readiness proof without calling providers.
#
# Usage:
#   .\scripts\provider-preflight.ps1

param(
    [string]$ProofDir = "proof/provider_readiness",
    [string]$Prompt = "Build a full-stack todo app with auth and deploy proof."
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$proofRoot = Join-Path $root $ProofDir
$jsonPath = Join-Path $proofRoot "provider_preflight.json"
$logPath = Join-Path $proofRoot "provider_preflight.log"
$matrixPath = Join-Path $proofRoot "PASS_FAIL.md"

New-Item -ItemType Directory -Force -Path $proofRoot | Out-Null

Push-Location $root
try {
    $output = & python backend\provider_readiness.py --prompt $Prompt --output $jsonPath 2>&1
    $code = $LASTEXITCODE
    $output | Set-Content -Path $logPath -Encoding UTF8
    if ($code -ne 0) {
        throw "provider readiness script failed with exit code $code"
    }
} finally {
    Pop-Location
}

$data = Get-Content $jsonPath -Raw | ConvertFrom-Json
$hasProvider = $data.status -eq "ready"
$warnings = if ($data.warnings) { ($data.warnings -join ", ") } else { "" }
$selected = if ($data.selected_chain) {
    (($data.selected_chain | ForEach-Object { "$($_.provider)/$($_.model)" }) -join " -> ")
} else {
    "(none)"
}

$rows = @(
    "| Check | Status | Evidence |",
    "|---|---|---|",
    "| Provider contract generated | PASS | $jsonPath |",
    "| Secret values redacted | $(if (-not $data.secret_values_included) { 'PASS' } else { 'FAIL' }) | secret_values_included=$($data.secret_values_included) |",
    "| At least one live provider configured in this shell | $(if ($hasProvider) { 'PASS' } else { 'FAIL' }) | status=$($data.status) |",
    "| Runtime provider selection produced | $(if ($data.selected_chain.Count -gt 0) { 'PASS' } else { 'FAIL' }) | $selected |",
    "| Live invocation executed | NOT RUN | This preflight is zero-call readiness proof. |",
    "| Warnings | INFO | $warnings |"
)
$rows -join "`n" | Set-Content -Path $matrixPath -Encoding UTF8

Write-Host "Provider readiness proof: $jsonPath"
Write-Host "Provider readiness log: $logPath"
Write-Host "Provider readiness matrix: $matrixPath"
