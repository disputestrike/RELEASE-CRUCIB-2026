# Root Cause

CrucibAI had two orchestration systems in the repo:

1. the relational Auto-Runner used by `/api/orchestrator/run-auto`
2. the larger `AGENT_DAG` swarm used by `run_orchestration_v2`

The product was still planning complex jobs into a small fixed Auto-Runner phase list:

- `planning.*`
- `frontend.scaffold`
- `frontend.styling`
- `backend.*`
- `database.*`
- `verification.*`
- `deploy.*`

That meant the build path could bypass the larger agent swarm entirely and fall back to packs or deterministic rescue files.

# Fix

- Planner now detects complex / enterprise / multi-stack prompts and emits the full `AGENT_DAG` as `agents.*` job steps.
- Executor now routes `agents.*` steps through the existing swarm runtime, not through pack handlers.
- Swarm step execution now loads prior completed swarm outputs from job checkpoints so downstream agents receive real context.
- Core swarm agents now raise hard failures if the server runtime returns fallback/skipped output, instead of quietly continuing.

# Result

Auto-Runner and the existing 123-agent swarm are now connected for complex jobs. The user-facing build path no longer has to choose between “real DAG” and “preview-friendly scaffold” for the same request.
