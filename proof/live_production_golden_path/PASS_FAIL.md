# Live Production Golden Path PASS/FAIL

- Generated at: `2026-05-01T17:57:50.672421+00:00`
- Base URL: `https://crucibai-production.up.railway.app`
- Job ID: `not-created`

| Requirement | Status | Evidence |
| --- | --- | --- |
| railway_health | FAIL | GET /api/health -> 404 |
| llm_readiness | FAIL | GET /api/health/llm -> 404, status=error |
| autorunner_runtime_health | FAIL | GET /api/orchestrator/runtime-health -> 404, ok=None |
| auth_register | FAIL | POST /api/auth/register -> 404, token_present=False |

## Blockers
- Could not register/authenticate a live proof user; protected golden-path routes were not callable.
