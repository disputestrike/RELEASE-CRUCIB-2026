$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = Split-Path -Parent $PSScriptRoot
$reportDir = Join-Path $repoRoot "artifacts\validation"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $reportDir "unified-workspace-validation-$stamp.txt"

function Write-Section([string]$title) {
  $line = "=" * 78
  $msg = "`n$line`n$title`n$line"
  Write-Host $msg -ForegroundColor Cyan
  Add-Content -Path $reportPath -Value $msg
}

function Invoke-Step([string]$name, [scriptblock]$block) {
  Write-Section $name
  try {
    $oldPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & $block 2>&1 | Out-String
    $ErrorActionPreference = $oldPref
    if ($LASTEXITCODE -ne 0) {
      throw "Command exited with code $LASTEXITCODE"
    }
    Add-Content -Path $reportPath -Value $output
    Add-Content -Path $reportPath -Value "STATUS: PASS`n"
    Write-Host "PASS: $name" -ForegroundColor Green
  } catch {
    $ErrorActionPreference = "Stop"
    $err = $_ | Out-String
    Add-Content -Path $reportPath -Value $err
    Add-Content -Path $reportPath -Value "STATUS: FAIL`n"
    Write-Host "FAIL: $name" -ForegroundColor Red
    throw
  }
}

Set-Location $repoRoot
"Unified Workspace patch validation" | Set-Content -Path $reportPath
"Started: $(Get-Date -Format o)" | Add-Content -Path $reportPath
"Repo: $repoRoot" | Add-Content -Path $reportPath

Invoke-Step "Git status (sanity)" { git status --short }
Invoke-Step "Frontend unit tests (canonical identity + surface mode)" {
  Set-Location (Join-Path $repoRoot "frontend")
  cmd /c "npm test -- --runInBand src/pages/__tests__/UnifiedWorkspaceCanonicalIdentity.test.js src/pages/__tests__/UnifiedWorkspaceSurfaceMode.test.js"
}
Invoke-Step "Frontend production build" {
  Set-Location (Join-Path $repoRoot "frontend")
  cmd /c "npm run build"
}
Invoke-Step "Backend acceptance invariants (truth/proof contracts)" {
  Set-Location (Join-Path $repoRoot "backend")
  cmd /c "python -m pytest tests/test_system_acceptance_invariants.py -q --tb=short"
}
Invoke-Step "Backend workspace session/preview resolver tests" {
  Set-Location (Join-Path $repoRoot "backend")
  cmd /c "python -m pytest tests/test_workspace_session_resolve.py -q --tb=short"
}

Set-Location $repoRoot
Write-Section "Validation Complete"
"Finished: $(Get-Date -Format o)" | Add-Content -Path $reportPath
"Report: $reportPath" | Add-Content -Path $reportPath
Write-Host "`nValidation report written to:`n$reportPath" -ForegroundColor Yellow
