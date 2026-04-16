# Phase Crosswalk Tracker

Date started: 2026-04-16
Program: CrucibAI Full Dominance Track
Status legend: Not Started | In Progress | Blocked | Complete

## 1) Requirement to Phase Crosswalk

| Req ID | Requirement | Phase(s) | Build Owner | QA Owner | Evidence | Status |
|---|---|---|---|---|---|---|
| FR-001 | Single canonical workspace route and surface | 0,1 | FE Lead | QA Lead | Route tests, screenshots | In Progress |
| FR-002 | Stable 3-pane architecture for Simple and Dev | 0,1,5 | FE Lead | QA Lead | Layout tests | In Progress |
| FR-003 | Backend as source of truth for lifecycle state | 0,2 | BE Lead | QA Lead | Stream integration tests | In Progress |
| FR-004 | Center pane single narrative workflow | 3 | FE Lead | QA Lead | E2E flow test | Not Started |
| FR-005 | Right pane modes: Preview, Code, Files, Publish | 4 | FE Lead | QA Lead | Mode test suite | Not Started |
| FR-006 | Advanced controls only in Dev capability envelope | 5 | FE Lead | QA Lead | Mode policy tests | In Progress |
| FR-007 | Differentiated power features beyond Manus parity | 6 | FE+BE | QA Lead | Scenario demos | Not Started |
| NFR-001 | Stream reliability and reconnect correctness | 2,7,8 | BE Lead | QA Lead | Reconnect tests | Not Started |
| NFR-002 | Security and permission guardrails for risky actions | 7 | BE Lead | Security QA | Policy tests, audit logs | Not Started |
| NFR-003 | Regression net for critical paths in CI | 8 | QA Lead | QA Lead | CI reports | In Progress |
| NFR-004 | Legacy architecture retirement | 9 | FE Lead | QA Lead | Dead-path scan | Not Started |
| NFR-005 | Staged rollout with KPI tracking | 10 | Product+Eng | QA Lead | KPI dashboard | Not Started |

## 2) API Contract Crosswalk

| API ID | Endpoint Family | UI Consumer | Contract Need | Test Need | Status |
|---|---|---|---|---|---|
| API-001 | /jobs lifecycle | Center timeline | canonical status model | lifecycle integration | In Progress |
| API-002 | /jobs stream | Center + right live updates | deterministic event ordering | reconnect replay test | In Progress |
| API-003 | /jobs steps/events/proof/trust | Center milestones + right diagnostics | consistent payload schema | schema + e2e assertions | Not Started |
| API-004 | /workspace files/file | Right code/files modes | file integrity and latency handling | file open/edit tests | Not Started |
| API-005 | /projects deploy | Right publish mode | deploy lifecycle and status | deploy flow test | Not Started |

## 3) Compliance Checklist Crosswalk

| Compliance ID | Control | Applied In Phase(s) | Evidence | Status |
|---|---|---|---|---|
| C-001 | Route canonicalization control | 1,9 | route map and tests | In Progress |
| C-002 | Layout non-duplication control | 1 | component map and runtime checks | In Progress |
| C-003 | Backend-truth state control | 2 | stream consistency reports | In Progress |
| C-004 | Mode capability gating control | 5 | policy matrix tests | In Progress |
| C-005 | Risk action authorization control | 7 | permission logs | Not Started |
| C-006 | CI regression gate control | 8 | CI pass records | In Progress |
| C-007 | Rollout safety control | 10 | flag and rollback logs | Not Started |

## 4) Corrective Action Register

| CAR ID | Trigger | Severity | Containment | Root Cause | Fix | Prevention | Owner | ETA | Status |
|---|---|---|---|---|---|---|---|---|---|
| CAR-2026-04-16-001 | Baseline cycle opened | P3 | N/A | N/A | Replaced placeholder with tracked cycle entry | Keep CAR table populated only with real findings | Program lead | 2026-04-16 | Closed |
| CAR-2026-04-16-002 | Targeted lint on `WorkspaceManusV2.jsx` exposed 16 existing lint errors (`no-undef`, missing imports) | P2 | Kept canonicalization changes minimal and excluded this legacy file from release lint gate for current slice | Legacy variant contained unresolved code debt unrelated to prior canonical-link edits | Added missing component imports/state setters and replaced invalid preview refresh self-assignment in `WorkspaceManusV2.jsx`; re-ran lint and regression tests | Add explicit legacy-file lint debt checklist and avoid broad lint targets when touching one-line legacy links | FE Lead | 2026-04-16 | Closed |

## 5) Weekly Gate Decision Log

| Week | Phase Gate | Decision | Reason | Follow-up Actions |
|---|---|---|---|---|
| 2026-W16 | Program kickoff | Approved | Full dominance track confirmed | Begin Phase 0 and 1 implementation |

## 6) Execution Evidence Log

| Date | Scope | Evidence | Result | Notes |
|---|---|---|---|---|
| 2026-04-16 | Phase 1 + Phase 5 slice | Added workspace mode capability policy and gated advanced controls in canonical workspace UI | Pass | Simple mode hides debug logs, terminal, live stream, advanced orchestration controls |
| 2026-04-16 | Phase 2 slice | Added periodic backend task reconciliation in workspace (`/jobs` sync every 20s) | Pass | Task status alignment improves after refresh and during long sessions |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false modePolicy.test.js` | Pass | 1 suite, 4 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/pages/CrucibAIWorkspace.jsx src/lib/modePolicy.js src/lib/modePolicy.test.js` | Pass | No lint findings |
| 2026-04-16 | Phase 1 slice | Normalized authenticated entry points, onboarding flow, shell logos, and sidebar home/new actions to `/app/workspace` | Pass | Canonical workspace is now the default re-entry path across core authenticated surfaces |
| 2026-04-16 | Phase 1 slice | Removed shell-level right-panel ownership and outlet context from `Layout` so the canonical workspace owns right-pane behavior | Pass | No `useOutletContext` consumers remain; shell now passes `rightPanel={null}` |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js modePolicy.test.js` | Pass | 2 suites, 14 tests passed |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js modePolicy.test.js` after shell cleanup | Pass | 2 suites, 15 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/App.js src/components/Sidebar.jsx src/pages/OnboardingPage.jsx src/components/Layout.jsx src/components/Layout3Column.jsx src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings |
| 2026-04-16 | Phase 8 slice | `npx eslint src/components/Layout.jsx src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after shell cleanup |
| 2026-04-16 | Phase 2 slice | Extracted job-state normalization and deterministic stream event ID helpers into shared contract utilities | Pass | Workspace task sync and stream dedup now rely on explicit tested helpers |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false jobState.test.js SingleSourceOfTruth.test.js modePolicy.test.js` | Pass | 3 suites, 19 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/lib/jobState.js src/lib/jobState.test.js src/hooks/useJobStream.js src/pages/CrucibAIWorkspace.jsx` | Pass | No lint findings after Phase 2 helper extraction |
| 2026-04-16 | Phase 1 slice | Preserved query strings when `/app` index redirects to `/app/workspace` | Pass | Canonical redirect now keeps search-based intent instead of dropping it |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js jobState.test.js modePolicy.test.js` after redirect preservation | Pass | 3 suites, 19 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/App.js src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after redirect preservation |
| 2026-04-16 | Phase 1 + Phase 2 slice | Normalized workspace handoff so prompt-bearing links and onboarding suggestions seed the canonical composer even without auto-start | Pass | Canonical workspace now preserves more launch intent instead of dropping non-auto-start prompts |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false workspaceEntry.test.js jobState.test.js SingleSourceOfTruth.test.js modePolicy.test.js` | Pass | 4 suites, 23 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/utils/workspaceEntry.js src/utils/workspaceEntry.test.js src/pages/CrucibAIWorkspace.jsx` | Pass | No lint findings after handoff normalization |
| 2026-04-16 | Phase 1 + Phase 2 slice | Canonicalized chat/query history handoff into `/app/workspace` and seeded workspace composer from chat task history | Pass | Sidebar history links no longer rely on legacy `/app` semantics for chat task recall |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after chat canonicalization | Pass | 4 suites, 23 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/components/Sidebar.jsx src/pages/CrucibAIWorkspace.jsx src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after chat canonicalization |
| 2026-04-16 | Phase 1 slice | Preserved location `state` across `/app` to `/app/workspace` redirects | Pass | Legacy stateful `navigate('/app', { state })` calls now survive canonical index redirect |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after redirect state preservation | Pass | 4 suites, 23 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/App.js src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after redirect state preservation |
| 2026-04-16 | Phase 1 slice | Canonicalized public dashboard links in shared nav and key marketing pages to `/app/workspace` | Pass | Public entry points now hit canonical workspace directly instead of relying on `/app` redirect |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after public entry canonicalization | Pass | 4 suites, 24 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/components/PublicNav.jsx src/pages/LandingPage.jsx src/pages/OurProjectsPage.jsx src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after public entry canonicalization |
| 2026-04-16 | Phase 1 slice | Preserved location state across all canonical redirect helpers (`/workspace`, `/app`, `/app/auto-runner`) | Pass | Redirected workspace navigation now keeps query and state payloads |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after redirect helper hardening | Pass | 4 suites, 23 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/App.js src/__tests__/SingleSourceOfTruth.test.js` after redirect helper hardening | Pass | No lint findings |
| 2026-04-16 | Phase 1 slice | Canonicalized additional CTA entry points (Pricing, Learn, Payments) to `/app/workspace` | Pass | More public and auth edge CTAs now hit canonical workspace directly |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after CTA canonicalization | Pass | 4 suites, 25 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/pages/Pricing.jsx src/pages/LearnPublic.jsx src/pages/PaymentsWizard.jsx src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after CTA canonicalization |
| 2026-04-16 | Phase 1 slice | Canonicalized remaining active-page `/app` links (Agent Monitor, Examples, Templates, Share, Builder) to `/app/workspace` | Pass | Reduced dependence on `/app` redirect fallback in user-facing surfaces |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after active-page canonicalization | Pass | 4 suites, 26 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/pages/AgentMonitor.jsx src/pages/ExamplesGallery.jsx src/pages/TemplatesGallery.jsx src/pages/ShareView.jsx src/pages/Builder.jsx src/__tests__/SingleSourceOfTruth.test.js` | Pass | No lint findings after active-page canonicalization |
| 2026-04-16 | Phase 1 slice | Canonicalized legacy `Workspace` and `WorkspaceManusV2` home/back links to `/app/workspace` | Pass | Legacy variants now align with canonical route contract for home/back actions |
| 2026-04-16 | Phase 8 slice | `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` after legacy alignment | Pass | 4 suites, 27 tests passed |
| 2026-04-16 | Phase 8 slice | `npx eslint src/pages/WorkspaceManusV2.jsx src/pages/Workspace.jsx src/__tests__/SingleSourceOfTruth.test.js` | Blocked | Revealed 16 pre-existing lint errors in `WorkspaceManusV2.jsx` unrelated to current edits; tracked in CAR-2026-04-16-002 |
| 2026-04-16 | Phase 1 + Phase 5 corrective slice | Restored `WorkspaceManusV2.jsx` lint baseline by adding missing imports/state wiring and fixing dead refresh handler | Pass | Legacy variant now aligns with canonical workspace lint baseline without route regressions |
| 2026-04-16 | Phase 8 corrective validation | `npx eslint src/pages/WorkspaceManusV2.jsx src/pages/Workspace.jsx src/__tests__/SingleSourceOfTruth.test.js` and `npm run test -- --watchAll=false SingleSourceOfTruth.test.js workspaceEntry.test.js jobState.test.js modePolicy.test.js` | Pass | 4 suites, 27 tests passed; prior CAR-2026-04-16-002 closed |
| 2026-04-16 | Phase 2 + Phase 7 slice | Normalized fetched job events with deterministic IDs, deduplication, and capped buffer size in `useJobStream` + `jobState` helpers | Pass | Reconnect/poll refresh now re-enters with stable event identity and bounded client memory growth |
| 2026-04-16 | Phase 8 slice | `npx eslint src/lib/jobState.js src/lib/jobState.test.js src/hooks/useJobStream.js` and `npm run test -- --watchAll=false jobState.test.js SingleSourceOfTruth.test.js workspaceEntry.test.js modePolicy.test.js` | Pass | 4 suites, 29 tests passed after reconnect guardrail hardening |
| 2026-04-16 | Phase 1 + Phase 3 slice | Restored distinct app-shell routes for `Dashboard` and `Live View` (`/app/dashboard`, `/app/live`) while keeping canonical workspace route | Pass | Users now have explicit Dashboard, Workspace, and Live View destinations in sidebar navigation |
| 2026-04-16 | Phase 8 slice | `npx eslint src/App.js src/components/Sidebar.jsx` and `npm run test -- --watchAll=false SingleSourceOfTruth.test.js` | Pass | Route/nav changes validated; source-contract suite remains green (15 tests) |
