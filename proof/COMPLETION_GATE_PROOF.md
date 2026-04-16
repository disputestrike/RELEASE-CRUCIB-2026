# Completion gates — builder classifications and critical heuristics

## 1. DAG placement

| Item | Location |
|------|----------|
| Plan | `backend/orchestration/planner.py` — `implementation.delivery_manifest` writes manifest intent; `verification.compile` depends on it; `verification.elite_builder` after `verification.security`; `deploy.build` depends on `verification.elite_builder` |
| Handler | `backend/orchestration/executor.py` — `handle_delivery_manifest` writes `proof/DELIVERY_CLASSIFICATION.md` with **Implemented / Mocked / Stubbed / Unverified** sections |
| Verification step | `backend/orchestration/verifier.py` — `verification.elite_builder` → `verify_elite_builder_workspace(..., job_goal=step["job_goal"])` |

## 2. Gate implementation

| Item | Location |
|------|----------|
| Module | `backend/orchestration/elite_builder_gate.py` |
| Mode | `CRUCIBAI_ELITE_BUILDER_GATE`: `strict` (default), `advisory` (logs would-fail), `off` |
| Four labels | `_delivery_classification_ok()` — all of Implemented, Mocked, Stubbed, Unverified must appear as substrings |
| Production claim | If text matches `production-ready` (regex) and `Unverified` is absent → fail |
| Critical goals | `_goal_suggests_critical()` tags tenancy / payments / auth / crypto from `job_goal` |
| Tenancy depth | `_critical_runtime_evidence()` — for tenancy tag, classification (or joined check) must mention hints such as `pytest`, `test_`, `runtime`, `smoke`, `isolation`, `tenancy_isolation` — **RLS-only prose is insufficient** |

## 3. Failure behavior

- In **strict** mode, `verify_elite_builder_workspace` returns `passed=False` with `issues` list; `executor.execute_step` raises `VerificationFailed` after inner repair loop exhausts.
- **Deploy** does not run until `verification.elite_builder` succeeds (DAG edge).

## 4. Continuation blueprint

| Item | Location |
|------|----------|
| Writer | `backend/orchestration/continuation_blueprint.py` — `write_continuation_blueprint()` → `proof/CONTINUATION_BLUEPRINT.md` |
| Triggers | `backend/orchestration/runtime_engine.py` — `_write_blueprint` on failure paths (e.g. blocked steps, max retries, incomplete DAG) |

### Example structure (emitted in job workspace)

```markdown
# Continuation blueprint
## Status
**Reason run did not fully complete:** …
## What to do next
1. Fix blockers…
## Failed or blocked steps
- …
## Open gates / verification
- …
```

## 5. Tests

| Test | Proves |
|------|--------|
| `test_elite_builder_gate_passes_with_manifest_and_directive` | Strict pass when labels + tenancy hints present |
| `test_elite_builder_gate_fails_missing_labels` | Missing Mocked/Stubbed etc. fails |
| `test_elite_builder_gate_advisory_softens` | Advisory forces pass with proof note |
| `test_tenancy_goal_gate_fails_when_classification_has_no_runtime_hints` | RLS-only text fails tenancy-tagged goal |
| `test_continuation_blueprint_writes_under_workspace` | Blueprint file created with step keys |

**Command:** `python -m pytest tests/test_execution_authority_wiring.py -q` (from `backend/`).

