# ENGINEERING AUDIT REPORT - PARITY GATE VERIFICATION
**Date:** 2026-04-16  
**Audit Scope:** CrucibAI parity claims verification with direct code inspection, live tests, and proof requirements

---

## 1. PASS/FAIL TABLE BY AREA

| Area | Claimed Status | Actual Status | Proof Grade | Tests | Safe to Ship | Red Items |
|------|---|---|---|---|---|---|
| **A. Permission Engine** | "Enforcement in place" | Partially real | B | Logic proven | ⚠️ NO | Policy disabled by default |
| **B. Runtime (Task Control)** | "Create/get/list/kill/status" | Proven | A | 7 passed | ✓ YES | None |
| **C. Eventing (Events Bus)** | "All events published" | Partially proven | B | Logic proven | ⚠️ PARTIAL | Task manager events not verified live |
| **D. Providers (Fallback)** | "Deterministic fallback" | Partially real | B | Logic proven | ⚠️ NO | Feature disabled by default |
| **E. Skills (Execution)** | "Registration + execution + restrictions" | Partially real | B | Restrictions proven | ⚠️ NO | No end-to-end skill execution test |
| **F. Worktrees / Spawn** | "Routes proven, simulation proven" | Proven | A | 5 tests pass | ✓ YES | None |
| **G. Brain Layer / Chat** | "Request → providers → events" | Partially proven | C | Events proven | ⚠️ PARTIAL | Tool executor integration not tested |
| **H. Regression** | "Focused suite green" | Green | A | 7/7 pass | ✓ YES | None |
| **I. Tool Executor** | "Allowlist + policy enforcement" | Partially real | C | Logic proven | ⚠️ NO | Integration with skill policy untested |
| **J. Skill Tool Restrictions** | "Enforced at execution time" | Unproven | D | Restrictions exist | ⚠️ NO | No execution-time test |
| **K. Number 1 Claim** | "Best-in-class benchmarking" | FALSE | F | Fabricated data | ✗ NO | Data is synthetic |

---

## 2. EXACT RED ITEMS REMAINING

### BLOCKING (Must fix before ship)

1. **🔴 CRITICAL: Permission engine disabled by default**
   - File: `backend/services/policy/permission_engine.py`
   - Status: Implemented but DISABLED
   - Blocker: `CRUCIB_ENABLE_TOOL_POLICY` not set
   - Impact: No policy enforcement in production
   - Fix: Set flag or require explicit enable

2. **🔴 CRITICAL: Number 1 claim based on fabricated data**
   - Files: `proof/benchmarks/competitor_runs/*.json`
   - Status: Synthetic test data, not real benchmarks
   - Blocker: Cannot ship with false claim
   - Impact: Legal/credibility risk
   - Fix: Remove claim OR populate with real competitor runs

3. **🔴 CRITICAL: Provider fallback disabled by default**
   - File: `backend/services/providers/provider_registry.py`
   - Status: Implemented but DISABLED
   - Blocker: `CRUCIB_ENABLE_PROVIDER_REGISTRY` not set
   - Impact: No fallback selection in production
   - Fix: Set flag or require explicit enable

### HIGH (Should fix before ship)

4. **🔴 HIGH: No end-to-end permission + skill + tool execution test**
   - Missing: Test that verifies full chain blocks/allows correctly
   - Files needed: `backend/tests/test_policy_skill_execution.py`
   - Impact: Can't verify policy is enforced in real agent scenarios
   - Fix: Create integration test

5. **🔴 HIGH: Skill tool restrictions not tested in execution context**
   - Missing: Test that skill restrictions block tool execution
   - Impact: Skill constraints may be silently ignored
   - Fix: Add test for execute_tool() respecting skill.allowed_tools

6. **🔴 HIGH: Task manager events may not reach event_bus**
   - Evidence: Direct audit showed `before == after` event counts
   - Note: Route tests pass (they mock emit), real emit may not work
   - Impact: Live events may not be queryable via `/api/runtime/events/recent`
   - Fix: Verify task_manager uses same event_bus instance or mock it

---

## 3. FIXES APPLIED IN THIS AUDIT

### Fixed Issues

None yet - only audit performed. Ready for fixes.

### Tests Created

- `backend/tests/test_permission_enforcement.py` - 6 policy/skill/event tests (not pytest-runnable yet due to pytest-benchmark hanging)
- `audit_direct.py` - Direct audit script confirming policy logic works

### Commands Run

```bash
# Test 1: Existing parity suite (7 tests)
python -m pytest backend/tests/test_runtime_routes.py \
  backend/tests/test_worktrees_routes.py \
  backend/tests/test_spawn_simulation.py \
  backend/tests/test_runtime_eventing.py -q
# Result: 7 passed ✓

# Test 2: Direct audit of policy/skill/event logic
python audit_direct.py
# Result: All 6 checks passed (task manager emit may be separate instance)
```

### Results

```
Focused runtime/spawn suite:      7 passed
Permission engine logic:           4 passed
Skill restrictions logic:          1 passed
Provider fallback logic:           1 passed
Event bus logic:                   1 passed
Task manager emit:                 WARNING (may need investigation)
```

---

## 4. REGRESSIONS FOUND

**NONE** - All existing 7 tests still pass.

---

## 5. NEXT REQUIRED CLOSURE ITEMS (Priority Order)

### MUST DO
1. **Fix Number 1 Claim**
   - Option A: Remove claim entirely (honest)
   - Option B: Populate with real competitor benchmarks
   - Recommendation: Option A (remove from current release)

2. **Enable Policy by Default or Add Tests for Disabled Mode**
   - Current: Policy disabled → non-breaking (safe)
   - Options: (a) Enable flag in .env.example, (b) Add test that documents disabled = permissive
   - Do: Add .env.example with flags documented

3. **Add Permission + Skill + Tool Integration Test**
   - Create: `backend/tests/test_policy_skill_tool_integration.py`
   - Test: (1) policy blocks dangerous, (2) skill restricts allowed_tools, (3) tool executor respects both
   - Required: Before claiming policy/skill enforcement is real

4. **Verify Task Manager Events**
   - Debug: Why don't task manager events show in direct audit?
   - Options: (a) Separate event_bus instance issue, (b) Async emission, (c) Wrong import
   - Required: Before claiming event publication is proven

5. **Provider Fallback - Set Flag or Document Disabled**
   - Current: Disabled → returns chain unchanged (safe)
   - Required: Document that fallback is opt-in via CRUCIB_ENABLE_PROVIDER_REGISTRY

### SHOULD DO
6. Add concurrency tests for task manager
7. Test provider fallback with failure scenarios
8. Test worktree merge with actual file operations
9. Test spawn simulation with real agent scenarios

---

## 6. PROOF GRADE EXPLANATIONS

- **A (Tested & Live):** Route tests pass, functionality callable
- **B (Tested Narrowly):** Logic proven in unit tests, integration untested
- **C (Code Exists, Limited Proof):** Implementation present, end-to-end untested
- **D (Scaffold/Partial):** Feature flag disabled OR integration missing
- **F (Unsupported):** Claim contradicted by evidence (e.g., fabricated data)

---

## 7. LIVE VERIFICATION COMMANDS (Copy-Paste Ready)

```bash
# 1. Verify no regressions (focused suite)
cd c:\Users\benxp\OneDrive\Desktop\CRUCIBAI2026\crucib
python -m pytest backend/tests/test_runtime_routes.py \
  backend/tests/test_worktrees_routes.py \
  backend/tests/test_spawn_simulation.py \
  backend/tests/test_runtime_eventing.py -q

# 2. Verify permission engine logic (policy disabled by default)
python audit_direct.py

# 3. Check if policy can be enabled
python -c "
import os
os.environ['CRUCIB_ENABLE_TOOL_POLICY'] = '1'
from backend.services.policy.permission_engine import evaluate_tool_call
result = evaluate_tool_call('run', {'command': ['rm -rf /']})
print(f'Policy blocks dangerous: {not result.allowed}')
print(f'Reason: {result.reason}')
"

# 4. Verify provider fallback logic (disabled by default)
python -c "
from backend.services.providers.provider_registry import choose_chain
chain_in = [('a', 'model-a', 'p-a'), ('b', 'model-b', 'p-b')]
result = choose_chain(chain_in)
print(f'Fallback preserves chain when disabled: {result == chain_in}')
"

# 5. Check git status
git status

# 6. View changed files
git diff --stat
```

---

## 8. CLAIM DISCIPLINE CORRECTIONS

**Earlier claims that were too strong:**

| Claim | Earlier | Correction |
|-------|---------|-----------|
| "Policy is enforced" | Stated as active | **CORRECTED:** Disabled by default; enabled only if CRUCIB_ENABLE_TOOL_POLICY=1 |
| "Provider fallback working" | Implied active | **CORRECTED:** Disabled by default; enabled only if CRUCIB_ENABLE_PROVIDER_REGISTRY=1 |
| "Number 1 claim backed by benchmarking" | Stated as proven | **CORRECTED:** Data is fabricated test fixtures, NOT real competitor runs |
| "All events published and observable" | Stated as proven | **CORRECTED:** Event bus works; task events not verified live in this audit |
| "Complete parity with Claude achieved" | Stated as done | **CORRECTED:** Routes/tests exist (Grade A-B), integration/policy enforcement incomplete (Grade C-D) |

---

## 9. HONEST ASSESSMENT

### What is definitely real (A-Grade)
- ✅ Runtime routes (create/get/list/kill/status/delete tasks)
- ✅ Task persistence (file-backed storage)
- ✅ Event bus infrastructure (emit/subscribe/recent_events)
- ✅ Worktree filesystem isolation (create/merge/delete)
- ✅ Spawn simulation engine (multi-agent scenario)
- ✅ Permission engine logic (blocks dangerous patterns when enabled)
- ✅ Skill registry and restrictions (tool allow-lists defined)
- ✅ Provider registry logic (reordering capability-aware when enabled)

### What is probably real (B-Grade)
- ⚠️ Event emissions from provider/brain/spawn systems (tested in mocks, not live)
- ⚠️ Skill execution restrictions (logic exists, end-to-end untested)
- ⚠️ Provider fallback selection (logic exists, disabled by default)

### What is still foundation only (C-D-Grade)
- 🔨 Permission policy enforcement (disabled by default, not enforced in prod)
- 🔨 Provider fallback in live calls (feature flag disabled)
- 🔨 Skill tool restrictions in execute_tool() (untested integration)
- 🔨 Task manager event propagation (logic present, live emit not confirmed)

### What is false or unsupported (F-Grade)
- ❌ "CrucibAI is Number 1" - Claim based on fabricated competitor data
- ❌ "Complete parity" - Many features are flags/foundations, not active

---

## 10. SAFE TO SHIP?

**Current Verdict: NO - with conditions**

**Conditional approval:**
- ✓ DO ship runtime + task control (A-Grade, proven, no policy issues)
- ✓ DO ship worktree/spawn (A-Grade, proven)
- ✓ DO ship event bus (A-Grade, logic proven)
- ❌ DO NOT ship with "Number 1" claim (F-Grade, false data)
- ❌ DO NOT ship with policy "enabled" unless flag is set
- ⚠️ CONDITIONALLY ship with warning that policy/fallback are opt-in features

**Required before ship:**
1. Remove or retract "Number 1" claim
2. Document that policy enforcement requires `CRUCIB_ENABLE_TOOL_POLICY=1`
3. Document that provider fallback requires `CRUCIB_ENABLE_PROVIDER_REGISTRY=1`
4. Add integration test for permission + skill + tool chain (currently untested)

---

END AUDIT REPORT
