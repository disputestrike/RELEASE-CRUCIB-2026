# Live Production Golden Path PASS/FAIL

- Generated at: `2026-04-08T18:44:47.376018+00:00`
- Base URL: `https://crucibai-production.up.railway.app`
- Job ID: `0dad4df3-cc3d-4ea3-843b-d215961ae82d`

| Requirement | Status | Evidence |
| --- | --- | --- |
| railway_health | PASS | GET /api/health -> 200 |
| llm_readiness | PASS | GET /api/health/llm -> 200, status=ready |
| autorunner_runtime_health | PASS | GET /api/orchestrator/runtime-health -> 200, ok=True |
| auth_register | PASS | POST /api/auth/register -> 200, token_present=True |
| live_llm_invocation | PASS | POST /api/ai/chat -> 200, model_used=cerebras/llama3.1-8b |
| plan_created | PASS | POST /api/orchestrator/plan -> 200, job_id=0dad4df3-cc3d-4ea3-843b-d215961ae82d, step_count=18 |
| run_auto_started | PARTIAL | --skip-run supplied |

## Blockers
- None recorded.
