#!/usr/bin/env bash
# Fifty-point #10 — same as enable_branch_protection.ps1 (POSIX).
set -euo pipefail
BRANCH="${1:-main}"
CONTEXT="${2:-Verify full stack / verify-all-passed}"

REPO="${GITHUB_REPOSITORY:-}"
if [[ -z "$REPO" || "$REPO" != *"/"* ]]; then
  REPO="$(git remote get-url origin 2>/dev/null | sed -E 's/.*[:/]([^/]+\/[^/.]+)(\.git)?$/\1/')"
fi
if [[ -z "$REPO" || "$REPO" != *"/"* ]]; then
  echo "Set GITHUB_REPOSITORY=owner/repo or run from a git repo with github origin." >&2
  exit 1
fi

command -v gh >/dev/null || { echo "Install gh: https://cli.github.com/"; exit 1; }

BODY=$(jq -n \
  --arg ctx "$CONTEXT" \
  '{
    required_status_checks: { strict: true, contexts: [$ctx] },
    enforce_admins: false,
    required_pull_request_reviews: null,
    restrictions: null,
    required_linear_history: false,
    allow_force_pushes: false,
    allow_deletions: false,
    block_creations: false,
    required_conversation_resolution: false,
    lock_branch: false,
    allow_fork_syncing: false
  }')

echo "PUT repos/$REPO/branches/$BRANCH/protection (check: $CONTEXT)"
echo "$BODY" | gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" --input -
echo "Done."
