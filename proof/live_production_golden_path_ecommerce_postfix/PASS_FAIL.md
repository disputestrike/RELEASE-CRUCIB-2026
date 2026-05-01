# Live Production Golden Path PASS/FAIL

- Generated at: `2026-05-01T14:00:44.918851+00:00`
- Base URL: `https://www.crucibai.com`
- Job ID: `tsk_ca67025fc15a`

| Requirement | Status | Evidence |
| --- | --- | --- |
| railway_health | PASS | GET /api/health -> 200 |
| llm_readiness | PASS | GET /api/health/llm -> 200, status=ready |
| autorunner_runtime_health | PASS | GET /api/orchestrator/runtime-health -> 200, ok=True |
| auth_register | PASS | POST /api/auth/register -> 200, token_present=True |
| live_llm_invocation | FAIL | POST /api/ai/chat -> 500, model_used=None |
| plan_created | PASS | POST /api/orchestrator/plan -> 200, job_id=tsk_ca67025fc15a, step_count=25 |
| run_auto_started | PASS | POST /api/orchestrator/run-auto -> 200, success=True |
| preview_boot | PASS | verification.preview: completed |
| elite_proof | FAIL | verification.elite_builder: verification.elite_builder / elite_checks_failed / failed_checks=error_boundaries,api_error_handling,authentication,security_headers / No Error Boundary component found; API routes lack error handling (try-catch); No authentication/authorization patterns found; Only 0/5 security headers configured |
| deploy_build | PASS | deploy.build: completed |
| deploy_publish | PASS | deploy.publish: completed |
| background_runner_stability | PASS | job_status=failed, phase=, background_crash_found=False |
| proof_artifacts_available | PASS | proof_item_count=72 |
| generated_workspace_files | PASS | workspace_file_count=60 |
| published_generated_app_url | PASS | GET /published/tsk_ca67025fc15a/ -> 200 |
| published_assets_scoped | FAIL | published HTML did not reference a job-scoped asset path |

## Blockers
- Failed requirements: live_llm_invocation, elite_proof, published_assets_scoped
- Live Auto-Runner job did not complete cleanly: status=failed, phase=
