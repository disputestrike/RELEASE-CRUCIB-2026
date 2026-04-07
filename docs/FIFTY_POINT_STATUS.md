# Fifty-point hardening tracker

Single place to track the **50** production-hardening targets for the general auto-builder. Status: **done** | **partial** | **todo**. Update this file when behavior or CI changes.

| # | Area | Item | Status | Notes |
|---|------|------|--------|-------|
| 1 | Stubs | No silent crew/agent stubs when `CRUCIBAI_REAL_AGENT_ONLY=1` | partial | `stub_build_enabled()` + **503** without keys; crew `Agent.execute` |
| 2 | Stubs | Dev chat stub cannot pretend to be a paid model in prod | partial | **`modelUsageLabel`** + **GenerateContent** |
| 3 | Auth | JWT validation consistent on all protected routes | partial | Ongoing audit |
| 4 | Auth | Session fixation / refresh token hygiene | partial | [`RUNBOOK.md`](./RUNBOOK.md), `.env.example` |
| 5 | Multi-tenant | Row-level isolation for job/project/workspace data | partial | RLS tests in CI |
| 6 | Multi-tenant | Cross-tenant IDOR fuzzing in tests | partial | **`test_idor_job_access.py`** (UUID + string mismatches) |
| 7 | Secrets | No secrets in logs or client bundles | partial | `security_audit`, deploy gates |
| 8 | Secrets | Workspace / artifact scan for credential patterns | partial | `CRUCIBAI_PRODUCTION_GATE_STRICT` |
| 9 | CI | Automated gates: lint, test, build | done | `ci-verify-full.yml`, `ci.yml` |
| 10 | CI | Required check `verify-all-passed` / branch protection | partial | **Requires human with repo admin:** run [`scripts/enable_branch_protection.ps1`](../scripts/enable_branch_protection.ps1) or [`scripts/enable_branch_protection.sh`](../scripts/enable_branch_protection.sh), or GitHub UI — see [`BRANCH_PROTECTION.md`](./BRANCH_PROTECTION.md) |
| 11 | SSRF | URL fetch allowlists for agent/orchestration | partial | `ssrf_prevention.py` |
| 12 | SSRF | DNS rebinding / private IP tests | partial | `test_ssrf_prevention.py` |
| 13 | Sandbox | Build/exec sandbox boundaries documented and enforced | partial | **`DATABASE.md`** → **`sandbox_executor.py`**; subprocess + timeouts |
| 14 | Sandbox | Resource limits (CPU, memory, time) | partial | **`CRUCIBAI_SANDBOX_*`**; **`test_sandbox_executor_limits.py`** |
| 15 | Rate limit | Abuse protection on expensive endpoints | partial | `CRUCIBAI_DEV` bypass |
| 16 | Rate limit | Per-user and per-IP fairness | partial | **`RateLimitMiddleware`** |
| 17 | Credits | Idempotent deduction; replay safety | partial | **`record_usage(idempotency_key=...)`**; **`Idempotency-Key`** on **`/api/ai/chat`** + **`/api/ai/chat/stream`** → **`_call_llm_with_fallback`**; tests |
| 18 | Credits | Observable balance drift alerts | partial | **`CRUCIBAI_CREDIT_BALANCE_LOG`** |
| 19 | Orchestration | DAG correctness; cycle detection | partial | **`test_agent_dag_golden.py`** |
| 20 | Orchestration | Heartbeat / stale job recovery | partial | `runtime_state`, `auto_runner` |
| 21 | Orchestration | Fixer loop bounded; no infinite retry | partial | **`MAX_RETRIES`** in **`fixer.py`**; **`test_fixer_bounded_golden.py`** |
| 22 | Proof | Proof bundle integrity and replay | partial | `proof_service.py` |
| 23 | Proof | Tamper-evident hashes in exports | partial | **`bundle_sha256`**; **`test_proof_bundle_integrity.py`** |
| 24 | Preview | Remote preview URL SSRF / open redirect | partial | Preview gate modules |
| 25 | Preview | User-visible preview trust states | partial | `PreviewPanel`, `sandpackFromFiles` |
| 26 | Preview | Browser-based verify optional gate | partial | `browser_preview_verify.py` |
| 27 | DB | Migrations single source of truth | partial | **`DATABASE.md`** |
| 28 | DB | Connection pooling and timeouts | partial | `db_postgres.py` |
| 29 | DB | Index strategy for hot paths | partial | `db_indexes.py` |
| 30 | Redis | Cache key namespaces; no cross-tenant leakage | partial | **`crucibai:`** prefix (`integrations/queue.py`) |
| 31 | API | OpenAPI / contract tests for critical paths | partial | **`test_golden_eval.py`** (health, `/api/`, chat) |
| 32 | API | Versioning and deprecation policy | partial | [`RUNBOOK.md`](./RUNBOOK.md) |
| 33 | Frontend | CSP / XSS for embedded preview and Sandpack | partial | **`SecurityHeadersMiddleware`**, **`index.html`** |
| 34 | Frontend | Safe HTML rendering for user-generated content | partial | **`WorkspaceRedesigned`** + **`sanitizeHTML`** |
| 35 | Observability | Structured logs with correlation IDs | partial | **`CRUCIBAI_STRUCTURED_LOGS`**; **`test_observability_correlation.py`** |
| 36 | Observability | OpenTelemetry optional (`CRUCIBAI_OTEL`) | partial | `.env.example` |
| 37 | Health | Liveness vs readiness split | partial | **`/api/health/live`**, **`/api/health/ready`** |
| 38 | Deploy | Smoke checks post-deploy | partial | **`deploy/healthcheck.sh`** |
| 39 | Supply chain | `npm audit` in CI | partial | **`ci-verify-full`**: `npm audit \|\| true`; `ci.yml` |
| 40 | Supply chain | Python dependency pinning and audit | partial | **`requirements.txt`**; **`pip-audit`** resolver issues possible |
| 41 | Legal / safety | Capability notices for restricted flows | partial | capability notice tests |
| 42 | Legal / safety | Content policy hooks for user prompts | partial | **`content_policy`**; **`test_content_policy.py`** |
| 43 | Evals | Golden-path eval runner (Phase 3) | partial | **`run_golden_eval.py`** + CI artifact |
| 44 | Evals | Regression fixtures per stack (web, API, mobile) | partial | Golden **`detect_build_kind`**: landing, saas, mobile, **ai_agent**, **game**, **fullstack** |
| 45 | Docs | Runbook for on-call (incident, rollback) | partial | [`RUNBOOK.md`](./RUNBOOK.md) |
| 46 | Docs | Environment matrix (dev, staging, prod) | partial | [`RUNBOOK.md`](./RUNBOOK.md), `RUN.md`, `.env.example` |
| 47 | Phase 0 | Single canonical branch / bundle import resolved | todo | **Blocked on you:** create [`handoff/bundle_parts_001_003.txt`](../handoff/README_BUNDLE_IMPORT.md) from your Codex paste (parts 001–003 only you have); then decode + `git fetch` per README |
| 48 | Phase 1 | Full-stack CI green on main | partial | `ci-verify-full` + golden eval artifact |
| 49 | Phase 2 | Stub and preview truthfulness complete | partial | Stub policy + preview fallback |
| 50 | Phase 3 | Automated quality score from evals in CI | partial | **`score_percent`** in `golden_eval_report.json` |

## Related automation

- Primary gate: [`.github/workflows/ci-verify-full.yml`](../.github/workflows/ci-verify-full.yml)
- Legacy / supplementary: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- Golden eval: [`backend/scripts/run_golden_eval.py`](../backend/scripts/run_golden_eval.py) (`pytest -m golden`)
- On-call: [`docs/RUNBOOK.md`](./RUNBOOK.md)
