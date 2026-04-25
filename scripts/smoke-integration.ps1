param(
  [string]$DatabaseUrl = "postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"

Push-Location $backend
try {
  $env:DATABASE_URL = $DatabaseUrl
  python -m pytest tests/test_phase2_runtime_wiring.py tests/test_runtime_product_endpoints.py tests/test_integration.py tests/test_orchestration_ui_contract.py -q --tb=short
}
finally {
  Pop-Location
}
