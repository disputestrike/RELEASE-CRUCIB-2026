# Build Evidence Matrix

This file separates implemented, partial, and unproven claims. It is the
evidence companion to `docs/BUILD_CAPABILITY_AUDIT.md`.

## Current Evidence Rule

No capability is considered complete unless it has:

- source file path
- function/class or route name
- test file path
- command run
- sample artifact/result

## Implemented And Tested In This Wave

| Capability | Source | Test | Command | Evidence |
|---|---|---|---|---|
| Build Integrity Validator final gate | `backend/orchestration/build_integrity_validator.py`, `backend/orchestration/auto_runner.py` | `backend/tests/test_build_integrity_validator.py` | `pytest backend/tests/test_build_integrity_validator.py -q` | BIV scores workspaces, emits structured issues/retry targets, and blocks final completion when failed. |
| BIV negative blocking | `validate_workspace_integrity()` | `test_biv_negative_cases_block_common_broken_web_outputs`, `test_biv_blocks_orphan_page_and_weak_design_tokens` | `pytest backend/tests/test_build_integrity_validator.py -q` | Blocks missing entry, missing root app, broken imports, missing build script, missing preview artifact, placeholder UI, orphan page, weak design tokens, exposed client secret. |
| BIV targeted retry routing | `route_retry_targets()`, `validate_workspace_integrity()`, `backend/orchestration/auto_runner.py` | `test_biv_retry_route_maps_categories_to_agent_groups`, `test_biv_final_gate_blocks_completion_and_routes_missing_entrypoint_retry` | `pytest backend/tests/test_build_integrity_validator.py -q` | Maps validator issue categories to concrete DAG agent groups and exposes the route in BIV events/failure payloads. |
| Targeted BIV repair execution | `backend/orchestration/targeted_dag_retry.py`, `backend/orchestration/auto_runner.py` | `test_targeted_dag_retry_plan_turns_biv_targets_into_executable_steps`, `backend/tests/test_platform_1010_readiness.py` | `pytest backend/tests/test_build_integrity_validator.py backend/tests/test_platform_1010_readiness.py -q` | Converts BIV categories into ordered repair step keys (`frontend.styling`, `frontend.scaffold`, `implementation.integration`, etc.) and auto-runner executes the targeted plan before final failure. |
| Route-level visual/product QA | `validate_workspace_integrity()` | `test_saas_workspace_passes_integrity_gate`, `test_website_profile_requires_public_site_sections_and_visual_assets`, `test_thin_placeholder_saas_workspace_fails_with_retry_targets` | `pytest backend/tests/test_build_integrity_validator.py -q` | BIV now checks per-page SaaS contracts and website section/visual-asset contracts, so a thin scaffold with scattered keywords cannot pass. |
| Cross-mode build readiness | `scripts/verify_1010_readiness.py` | `backend/tests/test_platform_1010_readiness.py` | `python scripts/verify_1010_readiness.py` | Local deterministic proof exercises SaaS UI, marketing website, Expo mobile, automation workflow, backend/API, thin-app rejection, and targeted retry planning. |
| Mobile Expo build target | `backend/orchestration/build_targets.py`, `build_target_inference.py`, `generation_contract.py`, `generated_app_template.py` | `test_mobile_expo_target_generates_validator_visible_artifacts` | `pytest backend/tests/test_build_integrity_validator.py -q` | `mobile_expo` target generates `expo-mobile/package.json`, `app.json`, `eas.json`, `App.tsx`, and screens. |
| Import Doctor baseline | `backend/orchestration/import_doctor.py` | `backend/tests/test_import_doctor.py` | `pytest backend/tests/test_import_doctor.py -q` | Detects package manager/framework/entrypoints and rejects unsafe ZIP traversal paths. |
| run_agent safety guard | `backend/automation/executor.py` | `backend/tests/test_automation_run_agent_safety.py` | `pytest backend/tests/test_automation_run_agent_safety.py -q` | Blocks cycles, depth overrun, budget exhaustion, and missing internal token for HTTP bridge. |
| Braintree sandbox proof hook | `scripts/prove_braintree_sandbox.py`, `backend/services/braintree_billing.py` | `test_braintree_sandbox_proof_hook_skips_without_credentials_and_can_require_live` | `python scripts/prove_braintree_sandbox.py`; release proof: `python scripts/prove_braintree_sandbox.py --require-live` | CI proves the hook and safe credential handling. With Braintree sandbox env vars, the same script executes a real `fake-valid-nonce` transaction and returns transaction id/status. |
| Deployment proof hook | `scripts/prove_deployment_readiness.py` | `test_deployment_proof_hook_has_artifact_mode_and_live_required_mode` | `python scripts/prove_deployment_readiness.py`; release proof: `python scripts/prove_deployment_readiness.py --require-live --app-url <APP_URL>` | CI proves deploy artifact readiness. With `APP_URL`, the script checks live health/routes/Braintree status surfaces. |
| Public claim/evidence parity gate | `scripts/verify_claim_evidence_parity.py`, `docs/BUILD_EVIDENCE_MATRIX.md` | CI proof gate | `python scripts/verify_claim_evidence_parity.py` | Blocks public copy classes that the matrix marks partial or not claimable. |
| Public project crash fix | `frontend/src/pages/OurProjectsPage.jsx`, `frontend/src/App.js` | `frontend/src/__tests__/NavAndPagesClickThrough.test.jsx` | `npm test -- --watchAll=false --runInBand NavAndPagesClickThrough.test.jsx` | Malformed `/api/examples` data cannot crash `/our-projects`; project aliases are mounted. |
| Full configured backend smoke suite | backend tests listed in root `pytest.ini` | configured backend smoke suite | `pytest -q --basetemp=C:\Users\benxp\AppData\Local\Temp\crucibai-pytest-full-verified` | 19/19 passed after allowing pytest to use a normal local Temp directory. |
| Full frontend test suite | `frontend/src/__tests__/` | Jest/React tests | `npm test -- --watchAll=false --runInBand` | 27/27 test suites passed; 143/143 tests passed. |
| Frontend production build | `frontend/` | CRA build | `npm run build` | Production build completed successfully; emitted only bundle-size and Node deprecation warnings. |
| Frontend production dependency audit | `frontend/package-lock.json` | npm audit | `npm audit --omit=dev --audit-level=high` | Production dependency audit reports 0 high vulnerabilities. Full dev/build-tool audit is not claimable yet because clean CI reports legacy CRA/Jest/eslint transitive advisories. |

## Public Marketing Claim Map

Website copy must use this table as the source of truth. If a claim is not in
the first two categories, public copy must state the condition or avoid the
claim entirely.

| Public claim | Status | Evidence / limitation | Copy rule |
|---|---|---|---|
| Build Integrity Validator final gate | Implemented and tested | BIV source, auto-runner wiring, BIV tests | May say builds are validator-gated. |
| BIV blocks bad web outputs | Implemented and tested | Negative tests for missing entry, missing app/router, broken import, missing script, missing preview, placeholder UI, orphan page, weak tokens, exposed client secret | May say bad artifacts are blocked by BIV. |
| Web app build/export flow | Implemented and tested at frontend/build-smoke level | Frontend tests/build and backend smoke suite | May say web artifacts are generated/exported after proof gates pass. |
| Expo/React Native mobile output | Implemented and tested for generated artifacts | `mobile_expo` artifacts and BIV mobile test | May say Expo mobile artifacts/source are generated. Must not say store submission is automatic. |
| Import existing code | Partially implemented | Import Doctor validates ZIP/workspace/package/framework/entrypoints/BIV | Say ZIP/workspace import doctor baseline. Git/paste/dependency repair/preview-after-import are conditional. |
| run_agent automation bridge | Implemented and tested for safety guard | run_agent safety tests | May say guarded run_agent bridge. Schedules/webhooks/templates are configuration-dependent. |
| Automatic repair/self-healing | Partially implemented | Bounded final BIV repair attempt and rerun plus deterministic BIV retry-route mapping | Say bounded repair and targeted retry recommendations; do not claim full live DAG node-level requeue. |
| Cross-mode generated quality gates | Implemented and tested | `scripts/verify_1010_readiness.py` covers SaaS, website, mobile, automation, API, bad-output rejection, and targeted retry planning | May say generated artifacts are checked across supported build modes before completion. |
| Security scan | Partially implemented | BIV client-secret scan plus existing security gates | Say baseline security checks; do not claim comprehensive CORS/auth/tenancy security doctor. |
| Quality score | Partially implemented | Deterministic BIV score tested | Say Build Integrity score. Do not claim complete per-agent historical cost/token accounting. |
| Agent transparency | Partially implemented | Job events, proof bundles, AgentMonitor surfaces | Say available phase/agent events and logs. Do not say every agent/decision is visible unless runtime proof shows it. |
| One-click deploy | Partially implemented | Deploy artifacts plus `scripts/prove_deployment_readiness.py` live hook; provider credentials and `APP_URL` are required for live proof | Say provider deploys are configuration-dependent and must pass the deployment proof hook. |
| Accessibility on every project | Not claimable | WCAG/axe/keyboard/contrast proof not implemented | Say accessibility is roadmap/not yet claimable. |
| App Store / Google Play submission | Not claimable as automatic | Requires credentials, signing, EAS/store metadata, and live proof | Say Expo source plus store submission guidance only. |
| Exact agent count such as 100+ or 241 | Not claimable | Runtime enumeration required | Do not publish exact count unless generated from runtime inventory. |
| Always runnable/deployable guarantee | Not claimable | No system can guarantee every prompt/provider/import | Say completion requires proof gates; failed proof returns issues/retry targets. |

## Partially Implemented

| Capability | What exists | What remains |
|---|---|---|
| Automatic BIV retry | Final BIV failure now creates an executable targeted retry plan, runs the repair brain against target-specific step keys, reruns BIV, and exposes the plan/attempts in job events. | Live proof still depends on a failing job exercising the path with provider/model configuration. |
| Import system | Import Doctor validates reconstructed workspaces, package manager/framework/entrypoints, and ZIP safety. | Git clone orchestration, dependency installation repair, preview-after-import repair, and UI import doctor surfacing still need end-to-end tests. |
| Security | BIV now blocks likely client-exposed secrets; existing production/security gates still run elsewhere. | Full security doctor for dependencies, CORS, auth, tenancy, and route-level policy. |
| Mobile | Expo/React Native artifacts are generated and validator-gated; cross-mode readiness script exercises mobile artifacts. | Live EAS build, signing credentials, App Store/Google Play submission automation, and TestFlight/internal testing proof. |
| Quality scoring | BIV score formula is deterministic and tested. | Full UI AgentMonitor score display and historical per-agent cost/token accounting need broader proof. |

## Not Yet Claimable As Complete

- Universal "always produces runnable deployable product."
- Accessibility check on every project.
- One-click deploy for every provider without configured credentials and live proof.
- Automatic App Store / Google Play submission.
- Exact public agent count such as "241 agents" unless runtime enumerates it.
- Complete per-agent provider cost accounting.

## Latest Verification Commands

These are the commands that must be rerun before calling a release verified:

```bash
python -m py_compile backend/orchestration/build_integrity_validator.py backend/orchestration/targeted_dag_retry.py backend/orchestration/import_doctor.py backend/automation/executor.py backend/orchestration/auto_runner.py scripts/verify_claim_evidence_parity.py scripts/verify_1010_readiness.py scripts/prove_braintree_sandbox.py scripts/prove_deployment_readiness.py
python scripts/verify_claim_evidence_parity.py
python scripts/verify_1010_readiness.py
python scripts/prove_braintree_sandbox.py
python scripts/prove_deployment_readiness.py
pytest backend/tests/test_build_integrity_validator.py backend/tests/test_import_doctor.py backend/tests/test_automation_run_agent_safety.py backend/tests/test_platform_1010_readiness.py -q
npm test -- --watchAll=false --runInBand
npm run build
```

Broader suites are required for full release proof:

```bash
pytest -q --basetemp=<local-temp-dir>
npm audit --omit=dev --audit-level=high
```

If either broad suite fails due pre-existing unrelated tests, record the failing
tests and do not convert that failure into a marketing claim.
