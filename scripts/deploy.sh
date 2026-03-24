#!/bin/bash
# ============================================================
# CrucibAI Deploy — Shell Wrapper
# Usage: ./scripts/deploy.sh
# ============================================================

set -e

BOLD="\033[1m"
GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}CrucibAI Railway Deploy${RESET}"
echo "============================================================"

# ── Check RAILWAY_TOKEN ───────────────────────────────────────
if [ -z "$RAILWAY_TOKEN" ]; then
    echo ""
    echo -e "${YELLOW}RAILWAY_TOKEN not set.${RESET}"
    echo ""
    echo "Get your token:"
    echo "  1. Go to: https://railway.app/account/tokens"
    echo "  2. Click 'New Token' → copy it"
    echo "  3. Paste it here:"
    echo ""
    read -p "  RAILWAY_TOKEN: " RAILWAY_TOKEN
    if [ -z "$RAILWAY_TOKEN" ]; then
        echo -e "${RED}No token provided. Exiting.${RESET}"
        exit 1
    fi
    export RAILWAY_TOKEN
fi

echo -e "${GREEN}✓ Token set${RESET}"

# ── Run the Python deploy script ─────────────────────────────
python3 "$(dirname "$0")/deploy.py"
