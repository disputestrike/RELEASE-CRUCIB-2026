# CrucibAI Implementation Tracker

This document tracks the approved seven-phase execution plan against the live codebase.

## Phase Checklist

- [x] Phase 1: Runtime unification kickoff
- [ ] Phase 2: Controller brain integration
- [ ] Phase 3: Routing completion for all reachable expansion agents
- [ ] Phase 4: Preview/build/security preflight hardening
- [ ] Phase 5: Memory strategy finalized in live runtime
- [ ] Phase 6: Honest green verification suite
- [ ] Phase 7: Product-surface orchestration polish

## Current Crosswalk

| Gap | Status | Primary Files |
| --- | --- | --- |
| Live progress path mounted in main server | In progress | `backend/server.py`, `backend/api/routes/job_progress.py`, `backend/orchestration/event_bus.py` |
| Underwired expansion agents reachable from real prompts | In progress | `backend/orchestration/planner.py`, `backend/orchestration/agent_selection_logic.py` |
| Preview verifier runs preflight before browser gate | In progress | `backend/orchestration/preview_gate.py`, `backend/agents/preview_validator_agent.py` |
| Memory layer no longer crashes when Pinecone/OpenAI are absent | **Verified offline (full CRUD fallback)** — run `pytest tests/test_vector_memory_fallback.py` | `backend/memory/vector_db.py`, `backend/tests/test_vector_memory_fallback.py` |
| Feature-suite reflects live runtime honestly | Pending | `test_wiring.py`, `test_all_integrated.py`, `tests/test_all_features.py` |

## Notes

- The goal is one authoritative runtime, not sidecar feature islands.
- Every completed item should map to a code path, a test, and a proof artifact.
