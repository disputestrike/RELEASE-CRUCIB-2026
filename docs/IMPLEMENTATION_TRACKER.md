# CrucibAI Implementation Tracker

This document tracks the approved seven-phase execution plan against the live codebase.

## Phase Checklist

- [x] Phase 1: Runtime unification kickoff
- [x] Phase 2: Controller brain integration (`GET /api/jobs/{job_id}` includes `controller_progress` when DB pool is available; brain module `backend/orchestration/controller_brain.py`)
- [x] Phase 3: Routing completion for all reachable expansion agents (`select_agents_for_goal` resolves only `AGENT_DAG` vertices; proof tests vary goals)
- [x] Phase 4: Preview/build/security preflight hardening (`verify_preview_workspace` deterministic contract; exercised in proof suite)
- [x] Phase 5: Memory strategy finalized in live runtime (`VectorMemory` falls back cleanly; `pytest tests/test_vector_memory_fallback.py`)
- [x] Phase 6: Honest green verification suite (gates below)
- [x] Phase 7: Product-surface orchestration polish (Simulation/`WhatIfPage.jsx`; simulations + jobs routes registered)

## Verification command (deterministic regression)

From `RELEASE-CRUCIB-2026/backend`:

```bash
python -m pytest tests/test_implementation_phases_proof.py tests/test_vector_memory_fallback.py tests/test_simulation_reality_engine.py tests/test_runtime_routes.py tests/test_runtime_product_endpoints.py -q
```

## Current Crosswalk

| Gap | Status | Primary Files |
| --- | --- | --- |
| Live progress path mounted in main server | **Verified** (`ROUTE_REGISTRATION_REPORT` loads `jobs`; job detail merged with controller) | `backend/server.py`, `backend/routes/jobs.py`, `backend/services/job_service.py`, `backend/orchestration/event_bus.py` |
| Underwired expansion agents reachable from real prompts | **Verified** (selection ⊆ `AGENT_DAG`) | `backend/orchestration/planner.py`, `backend/orchestration/agent_selection_logic.py` |
| Preview verifier runs preflight before browser gate | **Verified** (async preview gate returns structured payloads) | `backend/orchestration/preview_gate.py`, `backend/agents/preview_validator_agent.py` |
| Memory layer no longer crashes when Pinecone/OpenAI are absent | **Verified offline (full CRUD fallback)** — run `pytest tests/test_vector_memory_fallback.py` | `backend/memory/vector_db.py`, `backend/tests/test_vector_memory_fallback.py` |
| Feature-suite reflects live runtime honestly | **Verified** via implementation proof + simulation/runtime tests above | `tests/test_implementation_phases_proof.py`, `tests/test_simulation_reality_engine.py`, `tests/test_runtime_*` |

## Notes

- The goal is one authoritative runtime, not sidecar feature islands.
- Every completed item maps to code paths plus the regression command above.
