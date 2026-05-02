# Fifty-point #10 — require the CI gate on `main` via GitHub API (no web UI required).
# Prerequisites:
#   - GitHub CLI: https://cli.github.com/  (`winget install GitHub.cli`)
#   - `gh auth login` with a token that can change branch protection (repo **Admin** or custom role with **administration**)
#   - At least one successful run of workflow "Verify full stack" on the repo so the check name exists in GitHub's list
#
# Usage (from repo root):
#   .\scripts\enable_branch_protection.ps1
#   .\scripts\enable_branch_protection.ps1 -Branch main -Context "Verify full stack / verify-all-passed"
#
# If the API rejects the context name, list names from the last commit:
#   gh api repos/{owner}/{repo}/commits/HEAD/check-runs -q ".check_runs[].name"

param(
    [string] $Branch = "main",
    # Must match the **required check** name GitHub shows for the job (workflow name / job id is typical for Actions).
    [string] $Context = "Verify full stack / verify-all-passed"
)

$ErrorActionPreference = "Stop"

$repo = $env:GITHUB_REPOSITORY
if (-not $repo -or $repo -notmatch "^[^/]+/[^/]+$") {
    $remote = (git remote get-url origin 2>$null)
    if ($remote -match "[:/]([^/]+)/([^/.]+)") {
        $repo = "$($Matches[1])/$($Matches[2])"
    }
}
if (-not $repo -or $repo -notmatch "^[^/]+/[^/]+$") {
    Write-Host "Set GITHUB_REPOSITORY=owner/repo or run from a git clone with `origin` pointing at GitHub." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI: https://cli.github.com/ then: gh auth login" -ForegroundColor Red
    exit 1
}

$bodyObj = [ordered]@{
    required_status_checks                 = @{
        strict   = $true
        contexts = @($Context)
    }
    enforce_admins                           = $false
    required_pull_request_reviews            = $null
    restrictions                             = $null
    required_linear_history                  = $false
    allow_force_pushes                       = $false
    allow_deletions                          = $false
    block_creations                          = $false
    required_conversation_resolution         = $false
    lock_branch                              = $false
    allow_fork_syncing                       = $false
}
# GitHub API expects nulls for disabled review/restriction; ConvertTo-Json may omit — use -Depth 6
$json = $bodyObj | ConvertTo-Json -Depth 6 -Compress

Write-Host "PUT branch protection: $repo @ $Branch (required check: $Context)" -ForegroundColor Cyan
$json | gh api -X PUT "repos/$repo/branches/$Branch/protection" --input -
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nIf this failed with 404/422, fix the -Context string. List names:" -ForegroundColor Yellow
    Write-Host "  gh api repos/$repo/commits/HEAD/check-runs -q `"check_runs[].name`"" -ForegroundColor Gray
    exit $LASTEXITCODE
}
Write-Host "Done. In GitHub: Settings -> Branches -> verify rule on $Branch shows required check." -ForegroundColor Green
