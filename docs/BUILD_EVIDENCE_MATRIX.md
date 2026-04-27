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
