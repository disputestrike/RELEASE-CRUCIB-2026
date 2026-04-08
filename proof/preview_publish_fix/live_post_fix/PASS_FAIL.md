# Live Production Golden Path PASS/FAIL

- Generated at: `2026-04-08T18:53:50.835845+00:00`
- Base URL: `https://crucibai-production.up.railway.app`
- Job ID: `7b4cf12c-0903-4e68-8a07-8cf266f0001d`

| Requirement | Status | Evidence |
| --- | --- | --- |
| railway_health | PASS | GET /api/health -> 200 |
| llm_readiness | PASS | GET /api/health/llm -> 200, status=ready |
| autorunner_runtime_health | PASS | GET /api/orchestrator/runtime-health -> 200, ok=True |
| auth_register | PASS | POST /api/auth/register -> 200, token_present=True |
| live_llm_invocation | PASS | POST /api/ai/chat -> 200, model_used=cerebras/llama3.1-8b |
| plan_created | PASS | POST /api/orchestrator/plan -> 200, job_id=7b4cf12c-0903-4e68-8a07-8cf266f0001d, step_count=18 |
| run_auto_started | PASS | POST /api/orchestrator/run-auto -> 200, success=True |
| preview_boot | PASS | verification.preview: completed |
| elite_proof | PASS | verification.elite_builder: completed |
| deploy_build | PASS | deploy.build: completed |
| deploy_publish | PASS | deploy.publish: completed |
| background_runner_stability | PASS | job_status=completed, phase=completed, background_crash_found=False |
| proof_artifacts_available | PASS | proof_item_count=63 |
| generated_workspace_files | PASS | workspace_file_count=40 |
| published_generated_app_url | PASS | GET /published/7b4cf12c-0903-4e68-8a07-8cf266f0001d/ -> 200 |
| published_assets_scoped | PASS | scoped_asset=/published/7b4cf12c-0903-4e68-8a07-8cf266f0001d/assets/index-D-wCuBv4.js, asset_status=200 |

## Blockers
- None recorded.
