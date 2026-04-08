# CrucibAI End-to-End Proof Report

Generated: 2026-04-08

## CURRENT STATE

- Backend security/proof release gate passes locally with PostgreSQL/Redis test services.
- Frontend host runtime is still Node `v24.14.0`, which is outside `frontend/package.json` engines (`>=18 <=22`).
- Repo now pins Node `22` via `.nvmrc`, `frontend/.nvmrc`, Docker frontend stage, and GitHub Actions.
- Docker frontend build under Node 22 passed.
- Full Railway-style Docker image build passed.
- Built Docker image booted locally, ran startup migrations, connected Redis, and returned `GET /api/health` 200.
- Local shell does not expose Anthropic/Cerebras/LLM provider keys; provider readiness proof is therefore wiring proof, not live invocation proof.
- Railway CLI is not available on this machine, so live Railway deployment/log confirmation was not captured from this environment.

## GAP LIST

| Gap | Status | Evidence |
|---|---|---|
| Browser prompt to artifact proof | PARTIAL | `proof/e2e_golden_path/proof_bundle.json` is production-faithful wiring proof, not live browser/LLM proof. |
| Frontend verification under supported Node | PARTIAL | Docker Node 22 build passed; active host Node 24 remains blocked. See `proof/frontend_runtime_gate/PASS_FAIL.md`. |
| Live Anthropic/Cerebras invocation | NOT PROVEN | Local shell has no provider keys. See `proof/provider_readiness/provider_preflight.json`. |
| Railway deploy readiness | PARTIAL | Static config, full Docker build, and local container health passed. Live Railway URL/CLI confirmation not run. |
| Backend router extraction | PARTIAL | Provider readiness was extracted to `backend/provider_readiness.py`; large `backend/server.py` still needs further router extraction. |

## CHANGES MADE

- Added provider readiness module and `/api/health/llm` readiness endpoint.
- Added provider readiness tests and release-gate coverage.
- Pinned frontend runtime path to Node 22 through `.nvmrc`, `frontend/.nvmrc`, Dockerfile, and existing CI Node 22 workflow.
- Added frontend runtime proof script with optional Docker frontend build validation.
- Converted `railway.json` to a Dockerfile-based Railway config with `/api/health` healthcheck.
- Added Railway readiness script with static config checks, full Docker build proof, and local container health proof.
- Added deterministic golden-path proof generator under `proof/e2e_golden_path`.
- Updated local verification to produce runtime proof and continue when the active host Node is unsupported.

## FILES CHANGED

- `.nvmrc`
- `Dockerfile`
- `frontend/.nvmrc`
- `railway.json`
- `run-dev.ps1`
- `scripts/verify-local.ps1`
- `scripts/release-gate.ps1`
- `scripts/frontend-runtime-gate.ps1`
- `scripts/provider-preflight.ps1`
- `scripts/verify-railway-readiness.ps1`
- `scripts/generate-e2e-golden-path-proof.py`
- `backend/provider_readiness.py`
- `backend/server.py`
- `backend/tests/test_provider_readiness.py`
- `backend/tests/test_smoke.py`
- `proof/e2e_golden_path/*`
- `proof/frontend_runtime_gate/*`
- `proof/provider_readiness/*`
- `proof/railway_verification/*`

## COMMANDS RUN

```powershell
python -m py_compile backend\provider_readiness.py backend\server.py scripts\generate-e2e-golden-path-proof.py
python -m pytest backend\tests\test_provider_readiness.py backend\tests\test_smoke.py -k "provider_readiness or health_llm" -q
.\scripts\frontend-runtime-gate.ps1 -RunDockerBuild
.\scripts\provider-preflight.ps1
.\scripts\verify-railway-readiness.ps1 -RunDockerBuild -RunContainerHealth
python scripts\generate-e2e-golden-path-proof.py
.\scripts\verify-local.ps1
.\scripts\release-gate.ps1 -BackendOnly
docker build --target frontend --progress=plain -t crucibai-frontend-runtime-gate .
docker build --progress=plain -t crucibai-railway-readiness .
docker run -d --name crucibai-railway-proof -p 18080:8000 ... crucibai-railway-readiness
Invoke-WebRequest http://127.0.0.1:18080/api/health
```

## TESTS RUN

- Provider readiness focused test: `6 passed, 56 deselected`.
- Backend release gate:
  - Smoke: `33 passed, 24 deselected`.
  - Provider readiness: `5 passed`.
  - Automation bridge: `1 passed, 6 deselected`.
  - LLM routing guard: `8 passed, 18 deselected`.
- Docker frontend build: exit code `0`.
- Railway-style full Docker build: exit code `0`.
- Local Railway-style container health check: `GET /api/health` returned 200.

## PROOF ARTIFACTS CREATED

- `proof/e2e_golden_path/proof_bundle.json`
- `proof/e2e_golden_path/PASS_FAIL.md`
- `proof/e2e_golden_path/preview.html`
- `proof/e2e_golden_path/generated_artifacts/src/App.jsx`
- `proof/frontend_runtime_gate/runtime_gate.json`
- `proof/frontend_runtime_gate/PASS_FAIL.md`
- `proof/frontend_runtime_gate/docker_frontend_build.log`
- `proof/provider_readiness/provider_preflight.json`
- `proof/provider_readiness/PASS_FAIL.md`
- `proof/provider_readiness/provider_preflight.log`
- `proof/railway_verification/railway_readiness.json`
- `proof/railway_verification/PASS_FAIL.md`
- `proof/railway_verification/docker_full_build.log`
- `proof/railway_verification/docker_container_health.json`
- `proof/railway_verification/docker_container_logs.log`
- `proof/railway_verification/railway_cli_status.txt`

## WHAT IS FULLY PROVEN NOW

- Backend release-gate slices still pass after provider readiness changes.
- The repo has a supported Node 22 execution path even though the active host shell is Node 24.
- Frontend build completes inside Docker using Node 22.
- Railway-style Docker image builds successfully.
- The built image boots locally with Postgres/Redis env and returns `/api/health` 200.
- Provider readiness can report exact env var names and selected runtime chain without exposing secret values.

## WHAT IS STILL NOT PROVEN, WITH EXACT REASON

- Live LLM invocation is not proven because this local shell has no `ANTHROPIC_API_KEY`, `CEREBRAS_API_KEY`, `CEREBRAS_API_KEY_1..5`, or `LLAMA_API_KEY`.
- Live Railway deployment is not proven because no Railway URL was supplied to `scripts/verify-railway-readiness.ps1 -BaseUrl ...` and Railway CLI is not on PATH.
- Live browser/Sandpack screenshot proof is not proven because the active host Node is still 24; Docker build is proven, but local interactive browser E2E was not run.
- Full backend router extraction is not complete; only the provider readiness slice was extracted from `backend/server.py`.

## NEXT HIGHEST-VALUE STEP

Run live proof from a connected environment:

```powershell
.\scripts\provider-preflight.ps1
.\scripts\verify-railway-readiness.ps1 -BaseUrl https://your-live-railway-url -RunDockerBuild -RunContainerHealth
```

Then run browser E2E under Node 22:

```powershell
nvm use
cd frontend
npm ci
npm run e2e:workspace-preview
```
