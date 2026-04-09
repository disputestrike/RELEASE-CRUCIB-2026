# Industry Gap Crosswalk

This proof artifact maps the approved industry analysis to concrete engineering work.

## Competitive Themes

1. One brain
2. One runtime
3. One memory strategy
4. One visible execution flow
5. One deterministic verification contract

## Repo Crosswalk

| Theme | Current Fix Direction | Files |
| --- | --- | --- |
| One brain | tighten planner/controller reachability and decision metadata | `backend/orchestration/planner.py`, `backend/orchestration/agent_selection_logic.py` |
| One runtime | mount the real progress route and bridge event bus to WebSocket flow | `backend/server.py`, `backend/orchestration/event_bus.py`, `backend/api/routes/job_progress.py` |
| One memory strategy | use provider fallback instead of hard-crashing on missing Pinecone/OpenAI | `backend/memory/vector_db.py` |
| One visible execution flow | expose both SSE and WebSocket job progress from the main server | `backend/server.py`, `backend/api/routes/job_progress.py` |
| One verification contract | run preview preflight before browser preview | `backend/orchestration/preview_gate.py`, `backend/agents/preview_validator_agent.py` |

## Proof Standard

Each row should eventually have:
- code wired into the main runtime
- a focused automated test
- a production-visible outcome or debug signal
