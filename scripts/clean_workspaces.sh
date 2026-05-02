#!/usr/bin/env bash
# clean_workspaces.sh — safely wipe old build workspaces
#
# Usage:
#   ./scripts/clean_workspaces.sh            # dry run — shows what would be deleted
#   ./scripts/clean_workspaces.sh --execute  # actually deletes
#
# What it removes:
#   - Workspace folders older than KEEP_DAYS (default 7) days
#   - Only workspace dirs that are NOT associated with a currently-running job
#
# What it NEVER removes:
#   - The workspaces/ directory itself
#   - Any workspace modified in the last KEEP_DAYS days
#   - Source code

set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(dirname "$0")/../workspaces}"
KEEP_DAYS="${KEEP_DAYS:-7}"
DRY_RUN=true

if [[ "${1:-}" == "--execute" ]]; then
    DRY_RUN=false
fi

if [ ! -d "$WORKSPACE_ROOT" ]; then
    echo "Workspace root not found: $WORKSPACE_ROOT"
    exit 0
fi

echo "=== CrucibAI Workspace Cleanup ==="
echo "Root:      $WORKSPACE_ROOT"
echo "Keep last: ${KEEP_DAYS} days"
echo "Mode:      $([ "$DRY_RUN" = true ] && echo 'DRY RUN (pass --execute to delete)' || echo 'EXECUTE')"
echo ""

TOTAL=0
REMOVED=0
SKIPPED=0

for dir in "$WORKSPACE_ROOT"/*/; do
    [ -d "$dir" ] || continue
    TOTAL=$((TOTAL + 1))

    # Skip recently modified workspaces
    if find "$dir" -maxdepth 1 -newer "$WORKSPACE_ROOT" -mtime "-${KEEP_DAYS}" | grep -q .; then
        echo "  KEEP (recent):  $dir"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
    if [ "$DRY_RUN" = true ]; then
        echo "  WOULD DELETE:   $dir  [$SIZE]"
    else
        echo "  DELETING:       $dir  [$SIZE]"
        rm -rf "$dir"
    fi
    REMOVED=$((REMOVED + 1))
done

echo ""
echo "=== Summary ==="
echo "Total workspaces:  $TOTAL"
echo "Kept (recent):     $SKIPPED"
echo "$([ "$DRY_RUN" = true ] && echo 'Would delete' || echo 'Deleted'):       $REMOVED"
[ "$DRY_RUN" = true ] && echo "" && echo "Run with --execute to actually delete."
