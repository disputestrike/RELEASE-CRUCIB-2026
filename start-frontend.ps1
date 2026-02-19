# Start frontend only (port 3000). Run backend separately with start-local.ps1 or:
#   cd backend; python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000

$frontendDir = Join-Path $PSScriptRoot "frontend"
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Set-Location $frontendDir
if (Get-Command yarn -ErrorAction SilentlyContinue) { yarn start } else { npm run start }
