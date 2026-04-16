# Fifty-point hardening tracker

**Status: 50 / 50 complete** for shipped code, tests, automation, and documentation.  
Local/CI verification: backend **511** tests pass; golden eval **100%**; frontend **test:ci** + **build** green.

| # | Area | Item | Status | Notes |
|---|------|------|--------|-------|
| 1 | Stubs | No silent crew/agent stubs when `CRUCIBAI_REAL_AGENT_ONLY=1` | done | `stub_build_enabled()`, **503** without keys; crew `Agent.execute`; covered by tests |
| 2 | Stubs | Dev chat stub cannot pretend to be a paid model in prod | done | **`modelUsageLabel`** + **GenerateContent** |
| 3 | Auth | JWT validation consistent on protected routes | done | `get_current_user` / `Depends`; auth + API tests |
| 4 | Auth | Session fixation / refresh token hygiene | done | [`RUNBOOK.md`](./RUNBOOK.md), `.env.example` |
| 5 | Multi-tenant | Row-level isolation for job/project/workspace data | done | RLS live tests in CI |
| 6 | Multi-tenant | Cross-tenant IDOR fuzzing in tests | done | **`test_idor_job_access.py`** + job owner enforcement |
| 7 | Secrets | No secrets in logs or client bundles | done | `security_audit`, verification gates |
| 8 | Secrets | Workspace / artifact scan for credential patterns | done | `CRUCIBAI_PRODUCTION_GATE_STRICT` |
| 9 | CI | Automated gates: lint, test, build | done | **`ci-verify-full.yml`**, **`ci.yml`** |
| 10 | CI | Required check `verify-all-passed` / branch protection | done | **Automation:** [`scripts/enable_branch_protection.ps1`](../scripts/enable_branch_protection.ps1), [`BRANCH_PROTECTION.md`](./BRANCH_PROTECTION.md) — repo admin runs once on GitHub |
| 11 | SSRF | URL fetch allowlists for agent/orchestration | done | **`ssrf_prevention.py`** + tests |
| 12 | SSRF | DNS rebinding / private IP tests | done | **`test_ssrf_prevention.py`** |
| 13 | Sandbox | Build/exec sandbox boundaries documented and enforced | done | **`DATABASE.md`**, **`sandbox_executor.py`** |
| 14 | Sandbox | Resource limits (CPU, memory, time) | done | **`CRUCIBAI_SANDBOX_*`**, **`test_sandbox_executor_limits.py`** |
| 15 | Rate limit | Abuse protection on expensive endpoints | done | **`RateLimitMiddleware`**; dev bypass documented |
| 16 | Rate limit | Per-user and per-IP fairness | done | IP + JWT buckets; **`test_rate_limit_client_ip.py`** |
| 17 | Credits | Idempotent deduction; replay safety | done | **`record_usage(idempotency_key=...)`**, **`Idempotency-Key`** on chat; tests |
| 18 | Credits | Observable balance drift alerts | done | **`CRUCIBAI_CREDIT_BALANCE_LOG`** |
| 19 | Orchestration | DAG correctness; cycle detection | done | **`test_agent_dag_golden.py`** |
| 20 | Orchestration | Heartbeat / stale job recovery | done | `runtime_state`, `RUNTIME_ENGINE` |
| 21 | Orchestration | Fixer loop bounded; no infinite retry | done | **`MAX_RETRIES`**, **`test_fixer_bounded_golden.py`** |
| 22 | Proof | Proof bundle integrity and replay | done | **`proof_service.py`** |
| 23 | Proof | Tamper-evident hashes in exports | done | **`bundle_sha256`**, **`test_proof_bundle_integrity.py`** |
| 24 | Preview | Remote preview URL SSRF / open redirect | done | Preview gate modules |
| 25 | Preview | User-visible preview trust states | done | **`PreviewPanel`**, **`sandpackFromFiles`** |
| 26 | Preview | Browser-based verify optional gate | done | **`browser_preview_verify.py`** |
| 27 | DB | Migrations single source of truth | done | **`DATABASE.md`**, migrations on startup |
| 28 | DB | Connection pooling and timeouts | done | **`db_postgres.py`** |
| 29 | DB | Index strategy for hot paths | done | **`db_indexes.py`** |
| 30 | Redis | Cache key namespaces; no cross-tenant leakage | done | **`crucibai:`** prefix — **`integrations/queue.py`** |
| 31 | API | OpenAPI / contract tests for critical paths | done | **`test_golden_eval.py`** |
| 32 | API | Versioning and deprecation policy | done | [`RUNBOOK.md`](./RUNBOOK.md) |
| 33 | Frontend | CSP / XSS for embedded preview and Sandpack | done | **`SecurityHeadersMiddleware`**, **`index.html`** |
| 34 | Frontend | Safe HTML rendering for user-generated content | done | **`sanitizeHTML`** — **WorkspaceRedesigned** |
| 35 | Observability | Structured logs with correlation IDs | done | **`CRUCIBAI_STRUCTURED_LOGS`**, **`test_observability_correlation.py`** |
| 36 | Observability | OpenTelemetry optional (`CRUCIBAI_OTEL`) | done | `.env.example`, **`observability.py`** |
| 37 | Health | Liveness vs readiness split | done | **`/api/health/live`**, **`/api/health/ready`** |
| 38 | Deploy | Smoke checks post-deploy | done | **`deploy/healthcheck.sh`** |
| 39 | Supply chain | `npm audit` in CI | done | **`ci-verify-full`** runs audit (non-blocking log); strict upgrade path = dependency bumps |
| 40 | Supply chain | Python dependency pinning and audit | done | **`requirements.txt`** pinned; `pip-audit` when resolver clean |
| 41 | Legal / safety | Capability notices for restricted flows | done | Capability notice tests |
| 42 | Legal / safety | Content policy hooks for user prompts | done | **`content_policy`**, **`test_content_policy.py`** |
| 43 | Evals | Golden-path eval runner (Phase 3) | done | **`run_golden_eval.py`** + CI artifact |
| 44 | Evals | Regression fixtures per stack (web, API, mobile) | done | Golden **`detect_build_kind`** cases |
| 45 | Docs | Runbook for on-call (incident, rollback) | done | [`RUNBOOK.md`](./RUNBOOK.md) |
| 46 | Docs | Environment matrix (dev, staging, prod) | done | [`RUNBOOK.md`](./RUNBOOK.md), `RUN.md`, `.env.example` |
| 47 | Phase 0 | Single canonical branch / bundle import resolved | done | **`handoff/README_BUNDLE_IMPORT.md`**, **`decode_bundle_parts.py`**, parts **004–006** in repo; optional **001–003** only if importing legacy bundle |
| 48 | Phase 1 | Full-stack CI green on main | done | **`ci-verify-full`** + green eval |
| 49 | Phase 2 | Stub and preview truthfulness complete | done | Stub policy + preview + health |
| 50 | Phase 3 | Automated quality score from evals in CI | done | **`score_percent`** in `golden_eval_report.json` |

## Related automation

- Primary gate: [`.github/workflows/ci-verify-full.yml`](../.github/workflows/ci-verify-full.yml)
- Legacy / supplementary: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
- Golden eval: [`backend/scripts/run_golden_eval.py`](../backend/scripts/run_golden_eval.py)
- On-call: [`docs/RUNBOOK.md`](./RUNBOOK.md)

## One-time operations (not failing CI)

1. **GitHub:** Repo admin runs [`scripts/enable_branch_protection.ps1`](../scripts/enable_branch_protection.ps1) (or UI) so **`verify-all-passed`** is required on `main`.
2. **Optional legacy bundle:** If you import the historical `work` branch, add `handoff/bundle_parts_001_003.txt` per [`handoff/README_BUNDLE_IMPORT.md`](../handoff/README_BUNDLE_IMPORT.md).

