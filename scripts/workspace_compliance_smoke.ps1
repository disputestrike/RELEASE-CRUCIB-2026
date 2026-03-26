# Workspace / API smoke checks (PowerShell). Requires backend running; optional $env:CRUCIB_SMOKE_TOKEN for authed routes.
# Usage: .\scripts\workspace_compliance_smoke.ps1
#        $env:CRUCIB_SMOKE_TOKEN = '<jwt>'; .\scripts\workspace_compliance_smoke.ps1

$ErrorActionPreference = 'Stop'
$base = if ($env:CRUCIB_API_BASE) { $env:CRUCIB_API_BASE.TrimEnd('/') } else { 'http://localhost:8000' }
$api = "$base/api"

function Test-Get([string]$Url, [string]$Label, [hashtable]$Headers = $null) {
  try {
    $params = @{ Uri = $Url; Method = 'GET'; UseBasicParsing = $true; TimeoutSec = 15 }
    if ($Headers) { $params.Headers = $Headers }
    $r = Invoke-WebRequest @params
    Write-Host "[OK] $Label -> $($r.StatusCode)"
  } catch {
    Write-Host "[FAIL] $Label -> $($_.Exception.Message)"
  }
}

Write-Host "=== Crucib workspace compliance smoke (API=$api) ==="
Test-Get "$api/health" "GET /api/health"

if ($env:CRUCIB_SMOKE_TOKEN) {
  $h = @{ Authorization = "Bearer $($env:CRUCIB_SMOKE_TOKEN)" }
  Test-Get "$api/jobs" "GET /api/jobs (auth)" $h
  if ($env:CRUCIB_SMOKE_PROJECT_ID) {
    $projId = $env:CRUCIB_SMOKE_PROJECT_ID
    Test-Get "$api/projects/$projId/build-history" "GET build-history" $h
    Test-Get "$api/agents/status/$projId" "GET agents/status" $h
    Test-Get "$api/projects/$projId/logs" "GET project logs" $h
  }
} else {
  Write-Host "[SKIP] Set CRUCIB_SMOKE_TOKEN (and optionally CRUCIB_SMOKE_PROJECT_ID) for authed route checks."
}

Write-Host "Frontend build proof: run 'npm run build' in frontend/ (see PHASE0 Q-02)."
