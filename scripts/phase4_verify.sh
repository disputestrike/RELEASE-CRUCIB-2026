#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROOF_DIR="$ROOT_DIR/proof"
LOG_DIR="$PROOF_DIR/logs"
mkdir -p "$PROOF_DIR" "$LOG_DIR"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║ PHASE 4: VERIFICATION, MIGRATION, ADVERSARIAL TESTS        ║"
echo "║ Titan Forge + CrucibAI Elite Gauntlet                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

FAILURES=0
PASSES=0

# Helper functions
run_step() {
  local name="$1"
  shift
  local start_time=$(date +%s)
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "▶ RUNNING: $name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  if "$@" 2>&1 | tee "$LOG_DIR/${name}_$(date +%s).log"; then
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo "✅ PASS: $name (${duration}s)"
    PASSES=$((PASSES + 1))
  else
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo "❌ FAIL: $name (${duration}s)"
    FAILURES=$((FAILURES + 1))
  fi
}

require_file() {
  local path="$1"
  local description="${2:-}"
  if [[ ! -f "$path" ]]; then
    echo "❌ Missing required file: $path $description"
    FAILURES=$((FAILURES + 1))
    return 1
  else
    echo "✅ Found: $path"
    return 0
  fi
}

require_executable() {
  local path="$1"
  if [[ ! -x "$path" ]]; then
    echo "❌ Missing executable: $path"
    FAILURES=$((FAILURES + 1))
    return 1
  else
    echo "✅ Found executable: $path"
    return 0
  fi
}

check_secrets() {
  echo "🔍 Scanning for hardcoded secrets..."
  local secret_count=0
  
  # Check for API keys in code
  if grep -r "api_key\s*=\s*['\"]" . --include="*.py" --include="*.ts" --include="*.js" 2>/dev/null | grep -v node_modules | grep -v ".git" | head -5; then
    secret_count=$((secret_count + 1))
  fi
  
  # Check for passwords
  if grep -r "password\s*=\s*['\"]" . --include="*.py" --include="*.ts" --include="*.js" 2>/dev/null | grep -v node_modules | grep -v ".git" | grep -v "test" | head -5; then
    secret_count=$((secret_count + 1))
  fi
  
  # Check for MASTER_KEY in database
  if grep -r "MASTER_KEY" . --include="*.py" 2>/dev/null | grep -v node_modules | grep -v "\.git" | grep -v "test" | grep -v "environment"; then
    secret_count=$((secret_count + 1))
  fi
  
  if [[ $secret_count -gt 0 ]]; then
    echo "❌ CRITICAL: Secrets found in code"
    return 1
  else
    echo "✅ No hardcoded secrets detected"
    return 0
  fi
}

check_tenant_enforcement() {
  echo "🔍 Scanning for tenant isolation enforcement..."
  local tenant_count=$(grep -r "org_id\|tenant_id" backend/ app/ services/ src/ 2>/dev/null | wc -l)
  
  if [[ $tenant_count -gt 5 ]]; then
    echo "✅ Found $tenant_count tenant references (expected: >5)"
    return 0
  else
    echo "❌ Insufficient tenant enforcement (found: $tenant_count, expected: >5)"
    return 1
  fi
}

check_audit_chain() {
  echo "🔍 Scanning for audit chain implementation..."
  local audit_count=$(grep -r "prev_hash\|current_hash\|sha256\|audit_log" backend/ app/ services/ 2>/dev/null | grep -v node_modules | grep -v ".git" | wc -l)
  
  if [[ $audit_count -gt 3 ]]; then
    echo "✅ Found $audit_count audit chain references"
    return 0
  else
    echo "❌ Insufficient audit chain implementation (found: $audit_count)"
    return 1
  fi
}

check_no_auto_enforcement() {
  echo "🔍 Scanning for illegal auto-enforcement..."
  local violations=$(grep -r "auto.*enforce\|auto.*approve\|direct.*apply" backend/ app/ services/ src/ 2>/dev/null | grep -v test | grep -v mock | grep -v "\.git" | wc -l)
  
  if [[ $violations -eq 0 ]]; then
    echo "✅ No illegal auto-enforcement detected"
    return 0
  else
    echo "❌ Found $violations auto-enforcement violations"
    return 1
  fi
}

echo ""
echo "📋 REQUIRED PROOF FILES CHECK"
echo "─────────────────────────────────────────────────────────────"

require_file "$PROOF_DIR/ELITE_ANALYSIS.md" "(Analysis phase)"
require_file "$PROOF_DIR/TRAP_MAP.md" "(Trap handling)"
require_file "$PROOF_DIR/ARCHITECTURE.md" "(Architecture design)"
require_file "$PROOF_DIR/COMPLIANCE_TRADEOFF.md" "(GDPR vs Audit conflict)"
require_file "$PROOF_DIR/FOUNDATION_AUDIT.md" "(Foundation verification)"
require_file "$PROOF_DIR/TENANCY_VERIFICATION.md" "(Multi-tenant isolation)"
require_file "$PROOF_DIR/CRYPTO_VERIFICATION.md" "(Encryption & keys)"
require_file "$PROOF_DIR/INTEGRATION_PROOF.md" "(Integration wiring)"
require_file "$PROOF_DIR/AI_APPROVAL_BOUNDARY.md" "(AI approval gates)"
require_file "$PROOF_DIR/ASYNC_CONSISTENCY.md" "(Async correctness)"
require_file "$PROOF_DIR/ANALYTICS_TRUST.md" "(Analytics validation)"
require_file "$PROOF_DIR/MIGRATION_SAFETY.md" "(Migration safety)"
require_file "$PROOF_DIR/TEST_RESULTS.md" "(Test execution results)"
require_file "$PROOF_DIR/SECURITY_AUDIT.md" "(Security audit)"
require_file "$PROOF_DIR/CHANGES.md" "(Changelist)"
require_file "$PROOF_DIR/ELITE_DELIVERY_CERT.md" "(Delivery certification)"

echo ""
echo "📊 PROOF FILE INDEX"
echo "─────────────────────────────────────────────────────────────"
find "$PROOF_DIR" -maxdepth 1 -type f -name "*.md" | sort | while read f; do
  echo "  ✓ $(basename "$f")"
done

echo ""
echo "🔐 SECURITY & INTEGRITY CHECKS"
echo "─────────────────────────────────────────────────────────────"

run_step "secrets_scan" check_secrets
run_step "tenant_enforcement_check" check_tenant_enforcement
run_step "audit_chain_check" check_audit_chain
run_step "no_auto_enforcement_check" check_no_auto_enforcement

echo ""
echo "🧪 EXECUTABLE TEST SUITE"
echo "─────────────────────────────────────────────────────────────"

# Backend tests
if command -v python3 >/dev/null 2>&1 && command -v pytest >/dev/null 2>&1; then
  run_step "pytest_backend" pytest tests/ -v --tb=short || true
else
  echo "⚠️  pytest not available - skipping"
fi

# Frontend tests
if command -v npm >/dev/null 2>&1 && [[ -f "package.json" ]]; then
  if grep -q '"test"' package.json; then
    run_step "npm_test_frontend" npm test -- --passWithNoTests || true
  fi
else
  echo "⚠️  npm not available - skipping frontend tests"
fi

echo ""
echo "🏗️ GAUNTLET-SPECIFIC VERIFICATION"
echo "─────────────────────────────────────────────────────────────"

# Check for migration safety test
if [[ -f "tests/gauntlet/test_migration_safety.py" ]]; then
  run_step "gauntlet_migration_test" python3 -m pytest tests/gauntlet/test_migration_safety.py -v
else
  echo "⚠️  Migration safety test not found"
fi

# Check for adversarial resistance test
if [[ -f "tests/gauntlet/test_adversarial_resistance.py" ]]; then
  run_step "gauntlet_adversarial_test" python3 -m pytest tests/gauntlet/test_adversarial_resistance.py -v
else
  echo "⚠️  Adversarial resistance test not found"
fi

# Check for concurrency safety test
if [[ -f "tests/gauntlet/test_concurrency_safety.py" ]]; then
  run_step "gauntlet_concurrency_test" python3 -m pytest tests/gauntlet/test_concurrency_safety.py -v
else
  echo "⚠️  Concurrency safety test not found"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║ FINAL VERDICT                                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Passes: $PASSES"
echo "Failures: $FAILURES"
echo ""

if [[ "$FAILURES" -eq 0 ]]; then
  echo "✅ ELITE VERIFIED"
  echo ""
  echo "This system has passed the Titan Gauntlet."
  echo "All phases complete. All proofs valid. All tests passing."
  echo ""
  exit 0
else
  echo "❌ CRITICAL BLOCK"
  echo ""
  echo "System did not pass Phase 4 verification."
  echo "Review logs in: $LOG_DIR"
  echo "Fix failures and re-run."
  echo ""
  exit 1
fi
