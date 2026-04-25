param(
  [string]$DatabaseUrl = "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
)

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot

Write-Host "[1/3] Backend smoke"
& (Join-Path $scriptDir "smoke-backend.ps1") -DatabaseUrl $DatabaseUrl

Write-Host "[2/3] Frontend smoke"
& (Join-Path $scriptDir "smoke-frontend.ps1")

Write-Host "[3/3] Integration smoke"
& (Join-Path $scriptDir "smoke-integration.ps1") -DatabaseUrl $DatabaseUrl

Write-Host "All validations passed."
