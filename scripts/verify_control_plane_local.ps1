# Local automated checks for the control-plane program (no Railway).
# Run from repo root: RELEASE-CRUCIB-2026\
#   .\scripts\verify_control_plane_local.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:PYTHONPATH = $Root + $(if ($env:PYTHONPATH) { ";$($env:PYTHONPATH)" } else { "" })
Write-Host "== control plane: pytest (transcript + capabilities) ==" -ForegroundColor Cyan
python -m pytest `
  backend/tests/test_control_plane_transcript.py `
  backend/tests/test_projects_capabilities_endpoint.py `
  -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "== done ==" -ForegroundColor Green
