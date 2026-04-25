$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"

Push-Location $frontend
try {
  if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    npm ci
  }
  $env:GENERATE_SOURCEMAP = "false"
  npm run build
  npm run test:ci
}
finally {
  Pop-Location
}
