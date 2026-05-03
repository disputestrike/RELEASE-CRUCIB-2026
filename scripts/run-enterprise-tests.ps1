# Enterprise test suite runner (all automated layers)
# Run from repo root. Backend and frontend deps must be installed.
$ErrorActionPreference = "Stop"
$failed = $false

Write-Host "=== Layer 1.1: Lint ===" -ForegroundColor Cyan
Set-Location frontend; npm run lint; if (-not $?) { $failed = $true }; Set-Location ..

Write-Host "`n=== Layer 1.2: Security audit ===" -ForegroundColor Cyan
Set-Location frontend; npm audit --audit-level=high 2>$null; Set-Location ..

Write-Host "`n=== Layer 2: Frontend unit tests ===" -ForegroundColor Cyan
Set-Location frontend; npm run test:coverage 2>$null; if (-not $?) { npm test -- --watchAll=false }; if (-not $?) { $failed = $true }; Set-Location ..

Write-Host "`n=== Layer 3 & 9: Backend integration + smoke ===" -ForegroundColor Cyan
Set-Location backend; $env:BASE_URL = "http://localhost:8000"; pytest tests -v --tb=short; if (-not $?) { $failed = $true }; Set-Location ..

if ($failed) {
  Write-Host "`nOne or more layers failed. See above." -ForegroundColor Red
  exit 1
}
Write-Host "`nAll automated layers passed." -ForegroundColor Green
exit 0
