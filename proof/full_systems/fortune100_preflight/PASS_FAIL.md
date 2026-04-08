# Fortune 100 Public Readiness Preflight

Generated: 2026-04-08T16:49:33.651024+00:00
Base URL: https://crucibai-production.up.railway.app

| Check | Status | Detail |
|---|---|---|
| all_required_endpoints_healthy | PASS | All public readiness endpoints/pages must return 2xx/3xx and valid JSON where expected. |
| benchmark_50_prompt_90_percent | PASS | benchmark status=ready prompt_count=50 pass_rate=1.0 |
| full_systems_zero_required_failures | PASS | full_systems status=ready required_failures=0 |
| terminal_public_host_shell_blocked | PASS | terminal public_default=disabled for non-admin users in production |
| readiness_p95_under_5000ms | PASS | p95_ms=886.82 |

Failed requests: 0
Overall: PASS