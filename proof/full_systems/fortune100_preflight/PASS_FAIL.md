# Fortune 100 Public Readiness Preflight

Generated: 2026-04-08T17:39:17.619614+00:00
Base URL: https://crucibai-production.up.railway.app

| Check | Status | Detail |
|---|---|---|
| all_required_endpoints_healthy | PASS | All public readiness endpoints/pages must return 2xx/3xx and valid JSON where expected. |
| benchmark_50_prompt_90_percent | PASS | benchmark status=ready prompt_count=50 pass_rate=1.0 |
| full_systems_zero_required_failures | PASS | full_systems status=ready required_failures=0 |
| terminal_public_host_shell_blocked | PASS | terminal public_default=disabled for non-admin users in production |
| generated_code_sandbox_policy_visible | PASS | sandbox generated_code=process-level sandbox executor with timeout, output, file-size, memory, CPU, and process limits interactive_terminal=disabled for non-admin users in production |
| community_templates_curated_and_remixable | PASS | templates=4 moderation=ready case_studies=3 |
| readiness_p95_under_5000ms | PASS | p95_ms=1381.33 |

Failed requests: 0
Overall: PASS