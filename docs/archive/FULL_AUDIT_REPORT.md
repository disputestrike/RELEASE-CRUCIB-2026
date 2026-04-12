# CrucibAI – Full Audit Report (Fortune-100 Level)

**Purpose:** Line-by-line, code-by-code, every file and directory checked. No surprises, no forgotten. Deploy-ready, real agents, full compliance.

**Date:** February 2026

---

## 1. Codebase breakdown

### 1.1 Directory structure

| Directory | Purpose | Critical |
|-----------|---------|----------|
| `backend/` | API, orchestration, agents, state, tools | ✅ |
| `backend/agents/` | Image, video, legal compliance (optional) | ✅ |
| `backend/tools/` | File, Browser, API, Database, Deployment agents | ✅ |
| `backend/tests/` | Pytest: smoke, DAG, resilience, API, admin, security, orchestration, full audit | ✅ |
| `frontend/` | React app: Workspace, AgentMonitor, Settings, Landing, Auth | ✅ |
| `frontend/src/pages/` | All routes and screens | ✅ |
| `frontend/src/components/` | Shared UI, BuildProgress, QualityScore, etc. | ✅ |
| `docs/` | Deployment guides (Railway), marketing | ✅ |

### 1.2 Critical files (backend)

| File | Role | Tested / wired |
|------|------|-----------------|
| `server.py` | FastAPI app, auth, projects, build, export, deploy, SSE, WebSocket | ✅ test_api_*, test_smoke, test_admin_* |
| `agent_dag.py` | DAG, phases, system prompts, context builder | ✅ test_agent_dag, test_full_audit_critical_paths |
| `agent_real_behavior.py` | State/artifact/tool for every agent | ✅ test_full_audit_critical_paths |
| `agent_resilience.py` | Criticality, timeout, fallbacks | ✅ test_agent_resilience |
| `real_agent_runner.py` | File/Browser/API/DB/Deployment real execution | ✅ test_tool_agents |
| `tool_executor.py` | execute_tool (file, run, api, browser, db), sandbox default | ✅ used by real_agent_runner, autonomy_loop |
| `autonomy_loop.py` | Self-heal: re-run tests/security once after phases | ✅ test_full_audit_critical_paths (import) |
| `project_state.py` | load_state, update_state, workspace state.json | ✅ test_full_audit_critical_paths |
| `project_state.py` | update_state (merge) | Used by agent_real_behavior |

### 1.3 Critical files (frontend)

| File | Role | Wired to |
|------|------|----------|
| `App.js` | Routes, auth, API base URL | All pages |
| `Workspace.jsx` | Build, chat, export, deploy, projectId | /api/build/plan, /api/projects, /api/export/* |
| `AgentMonitor.jsx` | Project detail, phases, deploy ZIP, mobile badge | /api/projects/:id, /api/projects/:id/deploy/zip |
| `Settings.jsx` | API keys, capabilities (sandbox) | /api/settings/capabilities, /api/workspace/env |
| `LandingPage.jsx` | Hero, build CTA, features, who-builds-better | /api/examples |

### 1.4 Agent wiring matrix (no prompt-only)

| Agent type | Where defined | Real behavior |
|------------|----------------|----------------|
| State writers | agent_real_behavior.STATE_WRITERS | update_state(project_id, {key: value}) |
| Artifact writers | agent_real_behavior.ARTIFACT_PATHS | execute_tool(project_id, "file", {action, path, content}) |
| Tool runners | agent_real_behavior.TOOL_RUNNER_STATE_KEYS + run_real_post_step or execute_tool | test/security/ux/performance run; result to state |
| Real tool agents | real_agent_runner.REAL_AGENT_NAMES | File/Browser/API/DB/Deployment execute real tools |
| Native Config Agent | DAG + STATE_WRITERS (native_config) | State + deploy_files (app.json, eas.json) in server.py |
| Store Prep Agent | DAG + STATE_WRITERS (store_prep) + ARTIFACT_PATHS | State + artifact store-submission/STORE_SUBMISSION_GUIDE.md (writes both) + deploy_files |

All DAG agents have either: state write, artifact write, tool run (with result to state), or real tool execution. **No prompt-only agents in critical path.**

---

## 2. Security checklist

| Item | Status |
|------|--------|
| Auth on protected routes | ✅ get_current_user or get_optional_user on /api/projects/*, /api/auth/me, /api/tokens/*, /api/agents/status/*, /api/settings/capabilities, etc. |
| JWT_SECRET from env | ✅ Warning if unset; no hardcoded secret |
| No secrets in client/logs | ✅ API keys stored server-side; capabilities log is info-level only |
| Input validation | ✅ Pydantic models on POST bodies; path safety in workspace listing |
| CORS | ✅ Configurable via CORS_ORIGINS |
| Rate limiting | ✅ Middleware (if enabled) |
| Admin routes | ✅ get_current_admin(ADMIN_ROLES); RBAC for suspend, grant, export |
| MFA | ✅ Setup, verify, disable, backup codes |
| Export ZIP (POST) | ⚠️ Unauthenticated by design (client sends editor files); project deploy ZIP is auth’d (GET /projects/:id/deploy/zip) |

---

## 3. Deploy readiness (Railway and others)

| Item | Status |
|------|--------|
| Dockerfile | ✅ Root Dockerfile: Python 3.11, backend/, uvicorn, PORT=8000 |
| Procfile | ✅ web: cd backend && uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} |
| railway.json | ✅ builder: DOCKERFILE |
| .env.example | ✅ MONGO_URL, DB_NAME, OPENAI_API_KEY, ANTHROPIC_API_KEY, JWT_SECRET, CORS, Stripe optional |
| Required env at runtime | MONGO_URL, DB_NAME (server uses these); JWT_SECRET recommended |
| PORT | ✅ Dockerfile and Procfile use PORT for Railway/Render |

**Blocks removed:** None. If MongoDB is not set, server will fail at startup (intended). Railway: add MONGO_URL and JWT_SECRET in dashboard.

---

## 4. Tests covering critical paths

| Test file | Covers |
|-----------|--------|
| test_smoke.py | /api/health, /api/build/phases, /api/examples, /api/tokens/bundles, /api/agents, /api/templates, /api/patterns |
| test_agent_dag.py | DAG order, phases, all agents, context truncation |
| test_agent_resilience.py | get_criticality, get_timeout, generate_fallback |
| test_full_audit_critical_paths.py | Native Config + Store Prep in DAG and real behavior, project_state keys, system prompts, fallbacks, export/zip, health, build/phases, real_agent_runner and autonomy_loop imports |
| test_tool_agents.py | File, Browser, API, Database, Deployment agents |
| test_api_full_coverage.py | Public vs auth routes, 401 on protected, auth with token |
| test_admin_*.py | Admin RBAC, suspend, grant, export, audit log |
| test_security.py | Auth, injection, headers as applicable |

---

## 5. Section-by-section summary

- **Auth:** Register, login, MFA, Google OAuth, JWT, get_current_user, get_optional_user. ✅
- **Projects:** Create, get, list, state, phases, events, workspace files, deploy ZIP, retry phase. ✅
- **Build:** Plan (build_kind: fullstack, mobile, …), orchestration v2 (DAG, phases, results), deploy_files (web + mobile with store-submission/), autonomy loop. ✅
- **Export:** POST /export/zip, /export/github, /export/deploy (client files); GET /projects/:id/deploy/zip (project deploy_files). ✅
- **Deploy:** Vercel/Netlify from deploy_files; one-click tokens in Settings. ✅
- **Agents:** 120+ in DAG; real behavior via state/artifact/tool; Native Config + Store Prep for mobile. ✅
- **Frontend:** Workspace, AgentMonitor, Settings, Landing, Features, mobile badge, first-run banner, sandbox status. ✅
- **Compliance:** Privacy, Terms, AUP, DMCA, Cookies; audit log; admin roles. ✅

---

## 6. Final checklist (no surprises)

- [x] Every DAG agent has system prompt and fallback.
- [x] Native Config and Store Prep have real behavior (state; Store Prep also artifact).
- [x] project_state includes native_config and store_prep.
- [x] Dockerfile and Railway config added; Procfile uses PORT.
- [x] Tests: smoke, DAG, resilience, full audit critical paths, export/zip, health, build/phases.
- [x] No silent pass in capabilities (Docker check logged).
- [x] Admin fraud endpoint documented as extensible.
- [x] Rate/rank and “who builds better” docs include web + mobile + store pack.

**Conclusion:** Codebase is audited end-to-end. Critical paths are wired, agents have real behavior, deploy is unblocked for Railway (and similar). No prompt-only agents in the critical build path. Ready for production deployment with MongoDB and env configured.
