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
| Mobile Expo build target | `backend/orchestration/build_targets.py`, `build_target_inference.py`, `generation_contract.py`, `generated_app_template.py` | `test_mobile_expo_target_generates_validator_visible_artifacts` | `pytest backend/tests/test_build_integrity_validator.py -q` | `mobile_expo` target generates `expo-mobile/package.json`, `app.json`, `eas.json`, `App.tsx`, and screens. |
| Import Doctor baseline | `backend/orchestration/import_doctor.py` | `backend/tests/test_import_doctor.py` | `pytest backend/tests/test_import_doctor.py -q` | Detects package manager/framework/entrypoints and rejects unsafe ZIP traversal paths. |
| run_agent safety guard | `backend/automation/executor.py` | `backend/tests/test_automation_run_agent_safety.py` | `pytest backend/tests/test_automation_run_agent_safety.py -q` | Blocks cycles, depth overrun, budget exhaustion, and missing internal token for HTTP bridge. |
| Public project crash fix | `frontend/src/pages/OurProjectsPage.jsx`, `frontend/src/App.js` | `frontend/src/__tests__/NavAndPagesClickThrough.test.jsx` | `npm test -- --watchAll=false --runInBand NavAndPagesClickThrough.test.jsx` | Malformed `/api/examples` data cannot crash `/our-projects`; project aliases are mounted. |
| Full configured backend smoke suite | backend tests listed in root `pytest.ini` | configured backend smoke suite | `pytest -q --basetemp=C:\Users\benxp\AppData\Local\Temp\crucibai-pytest-full-verified` | 19/19 passed after allowing pytest to use a normal local Temp directory. |
| Full frontend test suite | `frontend/src/__tests__/` | Jest/React tests | `npm test -- --watchAll=false --runInBand` | 27/27 test suites passed; 143/143 tests passed. |
| Frontend production build | `frontend/` | CRA build | `npm run build` | Production build completed successfully; emitted only bundle-size and Node deprecation warnings. |
| Frontend dependency audit | `frontend/package-lock.json` | npm audit | `npm audit --audit-level=high` | Audit command reported 0 vulnerabilities. `npm install` separately printed an engine warning for Node v24 vs supported <=22. |

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
| Automatic repair/self-healing | Partially implemented | Bounded final BIV repair attempt and rerun | Say bounded repair; do not claim full DAG node-level retry. |
| Security scan | Partially implemented | BIV client-secret scan plus existing security gates | Say baseline security checks; do not claim comprehensive CORS/auth/tenancy security doctor. |
| Quality score | Partially implemented | Deterministic BIV score tested | Say Build Integrity score. Do not claim complete per-agent historical cost/token accounting. |
| Agent transparency | Partially implemented | Job events, proof bundles, AgentMonitor surfaces | Say available phase/agent events and logs. Do not say every agent/decision is visible unless runtime proof shows it. |
| One-click deploy | Not claimable as universal | Provider integration must be configured and verified | Say provider deploys are configuration-dependent. |
| Accessibility on every project | Not claimable | WCAG/axe/keyboard/contrast proof not implemented | Say accessibility is roadmap/not yet claimable. |
| App Store / Google Play submission | Not claimable as automatic | Requires credentials, signing, EAS/store metadata, and live proof | Say Expo source plus store submission guidance only. |
| Exact agent count such as 100+ or 241 | Not claimable | Runtime enumeration required | Do not publish exact count unless generated from runtime inventory. |
| Always runnable/deployable guarantee | Not claimable | No system can guarantee every prompt/provider/import | Say completion requires proof gates; failed proof returns issues/retry targets. |

## Partially Implemented

| Capability | What exists | What remains |
|---|---|---|
| Automatic BIV retry | Final BIV failure now triggers a bounded `build_integrity_validator_repair_attempt` using the existing repair brain, then reruns BIV. | Full DAG node-level retry routing by category is still deeper work. |
| Import system | Import Doctor validates reconstructed workspaces, package manager/framework/entrypoints, and ZIP safety. | Git clone orchestration, dependency installation repair, preview-after-import repair, and UI import doctor surfacing still need end-to-end tests. |
| Security | BIV now blocks likely client-exposed secrets; existing production/security gates still run elsewhere. | Full security doctor for dependencies, CORS, auth, tenancy, and route-level policy. |
| Mobile | Expo/React Native artifacts are generated and validator-gated. | Live EAS build, signing credentials, App Store/Google Play submission automation, and TestFlight/internal testing proof. |
| Quality scoring | BIV score formula is deterministic and tested. | Full UI AgentMonitor score display and historical per-agent cost/token accounting need broader proof. |

## Not Yet Claimable As Complete

- Universal "always produces runnable deployable product."
- Accessibility check on every project.
- One-click deploy for every provider.
- Automatic App Store / Google Play submission.
- Exact public agent count such as "241 agents" unless runtime enumerates it.
- Complete per-agent provider cost accounting.

## Latest Verification Commands

These are the commands that must be rerun before calling a release verified:

```bash
python -m py_compile backend/orchestration/build_integrity_validator.py backend/orchestration/import_doctor.py backend/automation/executor.py backend/orchestration/auto_runner.py
pytest backend/tests/test_build_integrity_validator.py backend/tests/test_import_doctor.py backend/tests/test_automation_run_agent_safety.py -q
npm test -- --watchAll=false --runInBand
npm run build
```

Broader suites are required for full release proof:

```bash
pytest -q --basetemp=<local-temp-dir>
npm audit --audit-level=high
```

If either broad suite fails due pre-existing unrelated tests, record the failing
tests and do not convert that failure into a marketing claim.
