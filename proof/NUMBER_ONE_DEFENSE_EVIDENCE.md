# Number One Defense Evidence

Date: 2026-04-09

This pass focused on turning the repo from "strong but split-brain" into a
cleaner, evidence-backed runtime story.

## What Changed

### Runtime compatibility cleanup
- [backend/routes_wired.py](C:/Users/benxp/OneDrive/Documents/New%20project/backend/routes_wired.py)
  - now delegates to the live planner/controller path instead of a toy executor
- [backend/orchestration/executor_wired.py](C:/Users/benxp/OneDrive/Documents/New%20project/backend/orchestration/executor_wired.py)
  - now acts as a compatibility shim over live modules:
    - `heuristic_schema_from_requirements`
    - `PreviewValidatorAgent`
    - `get_vector_memory`
    - design system artifacts
- [backend/orchestration/executor_with_features.py](C:/Users/benxp/OneDrive/Documents/New%20project/backend/orchestration/executor_with_features.py)
  - now aliases the compatibility executor instead of maintaining a second executor story

### Test truthfulness cleanup
- [test_wiring.py](C:/Users/benxp/OneDrive/Documents/New%20project/test_wiring.py)
- [test_all_integrated.py](C:/Users/benxp/OneDrive/Documents/New%20project/test_all_integrated.py)
- [tests/test_all_features.py](C:/Users/benxp/OneDrive/Documents/New%20project/tests/test_all_features.py)

These now validate the current runtime/controller/memory/preview stack rather
than legacy demo-only wiring.

### Reachability proof
- added [backend/tests/test_expansion_agent_reachability.py](C:/Users/benxp/OneDrive/Documents/New%20project/backend/tests/test_expansion_agent_reachability.py)
  - proves real prompts select the newer expansion agents

## Local Verification

### Syntax
Command:

```powershell
python -m py_compile backend\routes_wired.py backend\orchestration\executor_wired.py backend\orchestration\executor_with_features.py test_wiring.py test_all_integrated.py tests\test_all_features.py backend\tests\test_expansion_agent_reachability.py
```

Result:
- passed

### Backend / integration proof band
Command:

```powershell
python -m pytest backend\tests\test_controller_brain.py backend\tests\test_runtime_unification.py backend\tests\test_expansion_agent_reachability.py backend\tests\test_agent_swarm_autorunner.py backend\tests\test_job_progress_router.py backend\tests\test_orchestration_ui_contract.py backend\tests\test_verification_api_smoke.py backend\tests\test_verification_security.py backend\tests\test_publish_preview_fix.py backend\tests\test_real_server_endpoints.py backend\tests\test_security.py test_wiring.py test_all_integrated.py tests\test_all_features.py -q
```

Result:
- `73 passed`
- `1 warning`

Warning honesty:
- local Postgres was not reachable on `127.0.0.1:5434`
- the test harness continued so non-database tests could run

### Frontend proof band
Command:

```powershell
$env:CI='true'; npx craco test --runInBand
```

Result:
- `12 passed test suites`
- `53 passed tests`

Note:
- React emitted `act(...)` warnings in one suite, but the suite passed

## Production Spot Checks

### Health
Command:

```powershell
Invoke-RestMethod -Uri 'https://crucibai-production.up.railway.app/api/health' | ConvertTo-Json -Depth 6
```

Result:
- `status: healthy`
- `service: crucibai`

### Live DAG / debug state
Command:

```powershell
Invoke-RestMethod -Uri 'https://crucibai-production.up.railway.app/api/debug/agent-info' | ConvertTo-Json -Depth 8
```

Result:
- `total_agents_available: 237`
- `selection_logic_working: true`
- live `last_build` showed:
  - `selected_agent_count: 36`
  - `phase_count: 10`
  - `orchestration_mode: agent_swarm`

### Production planner probe: realtime + validation
Goal:

```text
Build realtime collaboration editor with sockets, shared presence, rate limiting, and import validation
```

Result:
- `success: true`
- `orchestration_mode: agent_swarm`
- `selected_agent_count: 36`
- controller summary:
  - `controller_mode: selective_parallel_swarm`
  - `has_parallel_phases: true`

Specialized agents selected included:
- `Real-Time Collaboration Agent`
- `WebSocket Agent`
- `Rate Limiting Agent`
- `Build Validator Agent`
- `Import Path Validator Agent`
- `Compilation Dry-Run Agent`

### Production planner probe: enterprise / ops / security
Goal:

```text
Build enterprise platform with architecture decision records, secret management, environment configuration, CORS security headers, input validation, rate limiting, and performance benchmarking
```

Result:
- `success: true`
- `orchestration_mode: agent_swarm`
- `selected_agent_count: 53`

Specialized agents selected included:
- `Architecture Decision Records Agent`
- `Secret Management Agent`
- `Environment Configuration Agent`
- `CORS & Security Headers Agent`
- `Input Validation Agent`
- `Rate Limiting Agent`
- `Performance Test Agent`
- `GitHub Actions CI Agent`

## What This Proves

1. The deployed production DAG is live at **237 agents**
2. The live planner is selecting newer expansion agents from real prompts
3. The controller summary and swarm metadata are present in production
4. The repo no longer needs the legacy "wired" files to tell a separate runtime story
5. The local backend + frontend verification bands are green

## Honest Boundary

This is strong evidence, but it is not the same thing as claiming every
strategic program is permanently complete forever.

What this pass proves well:
- runtime compatibility cleanup
- controller/progress/runtime integration band
- expansion-agent reachability from real prompts
- preview/security/runtime verification band
- production planner health and specialized routing

What this pass did not prove end-to-end:
- a fresh authenticated production build-job run through the full private job
  execution path
- full external-service-backed database/infrastructure execution in local tests

That said, this is now a much stronger position to defend CrucibAI with
evidence instead of aspiration.
