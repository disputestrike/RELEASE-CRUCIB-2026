# CrucibAI — Run All Tests
# Backend: pytest | Frontend: Jest | E2E: Playwright (optional)

$ErrorActionPreference = "Continue"
$backendOk = $false
$frontendOk = $false

Write-Host "`n=== CrucibAI Full Test Suite ===`n" -ForegroundColor Cyan

# 1. Backend
Write-Host "[1/2] Backend pytest..." -ForegroundColor Yellow
Push-Location backend
$r = python -m pytest tests/ -v --tb=short 2>&1
Pop-Location
if ($LASTEXITCODE -eq 0) {
  $backendOk = $true
  Write-Host "Backend: PASSED`n" -ForegroundColor Green
} else {
  Write-Host "Backend: FAILED`n" -ForegroundColor Red
  $r | Select-Object -Last 20
}

# 2. Frontend
Write-Host "[2/2] Frontend Jest..." -ForegroundColor Yellow
Push-Location frontend
$r2 = npm test -- --watchAll=false --passWithNoTests 2>&1
Pop-Location
if ($LASTEXITCODE -eq 0) {
  $frontendOk = $true
  Write-Host "Frontend: PASSED`n" -ForegroundColor Green
} else {
  Write-Host "Frontend: FAILED`n" -ForegroundColor Red
  $r2 | Select-Object -Last 15
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Backend:  $(if ($backendOk) { 'PASS' } else { 'FAIL' })"
Write-Host "Frontend: $(if ($frontendOk) { 'PASS' } else { 'FAIL' })"
Write-Host "`nE2E (Playwright): Run manually with backend + frontend started:"
Write-Host "  cd frontend; npm run start   # Terminal 1"
Write-Host "  cd backend; uvicorn server:app --port 8000  # Terminal 2"
Write-Host "  cd frontend; npx playwright test  # Terminal 3`n"

$code = if ($backendOk -and $frontendOk) { 0 } else { 1 }; exit $code
