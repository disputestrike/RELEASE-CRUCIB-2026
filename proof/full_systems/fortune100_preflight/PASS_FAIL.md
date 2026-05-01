# Fortune 100 Public Readiness Preflight

Generated: 2026-05-01T17:57:50.017595+00:00
Base URL: https://crucibai-production.up.railway.app

| Check | Status | Detail |
|---|---|---|
| all_required_endpoints_healthy | FAIL | All public readiness endpoints/pages must return 2xx/3xx and valid JSON where expected. |
| payment_provider_is_braintree | FAIL | provider=None configured=None |
| benchmark_50_prompt_90_percent | FAIL | benchmark status=None prompt_count=0 pass_rate=0 |
| full_systems_zero_required_failures | FAIL | full_systems status=None required_failures=None |
| terminal_public_host_shell_blocked | FAIL | terminal public_default=None |
| generated_code_sandbox_policy_visible | FAIL | sandbox generated_code=None interactive_terminal=None |
| community_templates_curated_and_remixable | FAIL | templates=0 moderation=None case_studies=0 |
| readiness_p95_under_5000ms | PASS | p95_ms=1452.05 |

Failed requests: 28
Overall: FAIL