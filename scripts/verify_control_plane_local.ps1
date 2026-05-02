# Local automated checks for the control-plane program (no Railway).
# Run from repo root: RELEASE-CRUCIB-2026\
#   .\scripts\verify_control_plane_local.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:PYTHONPATH = $Root + $(if ($env:PYTHONPATH) { ";$($env:PYTHONPATH)" } else { "" })
$env:CRUCIB_TEST_SQLITE = "1"
$env:CRUCIBAI_TEST_DB_UNAVAILABLE = "1"
Write-Host "== pre_release_sanity: app + route smoke ==" -ForegroundColor Cyan
python scripts/pre_release_sanity.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "== control plane: pytest (transcript + capabilities + import hygiene) ==" -ForegroundColor Cyan
Set-Location (Join-Path $Root "backend")
python -m pytest `
  tests/test_control_plane_transcript.py `
  tests/test_projects_capabilities_endpoint.py `
  tests/test_cors_policy.py `
  tests/test_route_loading.py `
  tests/test_repair_loop.py `
  tests/test_idempotency_header_golden.py `
  -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Set-Location $Root
Write-Host "== done ==" -ForegroundColor Green
