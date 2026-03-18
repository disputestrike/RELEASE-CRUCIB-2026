# CrucibAI Repo — What Is What (Explorer Guide)

When you open this repo in Cursor (or any IDE), you see many folders and files. This doc explains **what each part is** and **where to find things**, so everyone knows what is what and where it lives. Everything described here is in the repo and saved; we organize it like a full product codebase (similar to how Cursor’s own project is structured).

---

## Root-level folders (top of Explorer)

| Folder | What it is |
|--------|------------|
| **backend** | Python/FastAPI server: API routes, orchestration, agents, DB, auth, payments, build logic. The “engine” that runs builds, credits, and deploy. |
| **frontend** | React app (Craco, Tailwind): landing, dashboard, workspace, pricing, auth. The UI users see. |
| **docs** | All product and technical documentation: build types, deploy, pricing, legal, guides. **Start here** to understand how things work. |
| **scripts** | One-off and automation scripts (e.g. deploy, env, DB helpers). |
| **migrations** | DB schema migrations (e.g. versions/) used by the app. |
| **k8s** | Kubernetes manifests (e.g. deployment.yaml) if you deploy to K8s. |
| **terraform** | Infrastructure-as-code for cloud (if used). |
| **monitoring** | Observability / monitoring config or scripts. |
| **incidents** | Incident playbooks (e.g. high error rate, runbooks). |
| **pull_requests** | PR templates or notes (e.g. 01_ready_for_review.md). |
| **memory** | Product/PRD memory (e.g. PRD.md) for context. |
| **extracted_content** | Extracted reference content (e.g. from Manus, strategies). |
| **ide-extensions** | IDE integrations (e.g. VSCode, Sublime) for CrucibAI. |
| **tests** / **test_reports** | Test suites and test run outputs. |
| **.github** | GitHub config (actions, workflows). |
| **.vscode** | VS Code / Cursor workspace settings. |

---

## Backend (backend/)

| Folder / file | What it is |
|---------------|------------|
| **server.py** | Main FastAPI app: routes, orchestration trigger, credits, Stripe, health. Very large; core entry point. |
| **agent_dag.py** | DAG of agents (Planner, Frontend Generation, Backend Generation, etc.) and execution order. |
| **routers/** | Route modules: auth, AI chat, projects, deploy, voice, billing, etc. |
| **routes/** | Legacy or alternate route definitions. |
| **agents/** | Agent implementations (e.g. registry, stack selector, database agent, image generator). |
| **automation/** | Automation/executor logic (e.g. executor.py). |
| **tools/** | Tools used by agents (e.g. deployment_operations_agent). |
| **migrations/** | SQL migrations (e.g. 001_full_schema.sql) for PostgreSQL. |
| **db_pg.py** | PostgreSQL layer (Motor-like API, migrations). |
| **services/** | Business logic services. |
| **utils/** | Shared backend utilities. |
| **observability/** | Logging, metrics, tracing. |
| **workers/** | Background workers (if any). |
| **workspace/** | Workspace-related backend (files, deploy files). |
| **tests/** | Backend tests (pytest). |
| **generated_*** | Example/generated outputs (e.g. generated_saas, generated_math_platform). |

---

## Frontend (frontend/)

| Folder / file | What it is |
|---------------|------------|
| **src/App.js** | Root React app: routes, auth provider, API base. |
| **src/pages/** | All main pages: LandingPage, Dashboard, Workspace, Pricing, TokenCenter, Contact, GetHelp, Enterprise, Settings, etc. |
| **src/components/** | Reusable UI: Sidebar, Layout, Monaco/Sandpack wrappers, VoiceWaveform, forms, ui (buttons, etc.). |
| **src/stores/** | Global state (e.g. layout, tasks). |
| **src/contexts/** | React contexts. |
| **src/hooks/** | Custom hooks. |
| **src/utils/** | Frontend helpers (API errors, sanitization, etc.). |
| **src/lib/** | Third-party or shared lib setup. |
| **src/styles/** | Extra CSS if any. |
| **public/** | Static assets (favicon, index.html). |
| **craco.config.js** | Craco config (e.g. proxy to backend). |
| **package.json** | Dependencies and scripts. |

---

## Docs (docs/) — “Where do I read about X?”

| Topic | Doc (in docs/ or root) |
|-------|------------------------|
| Build types, full app/mobile, deploy | **docs/BUILD_TYPES_AND_DEPLOY.md** |
| What each folder is (this file) | **docs/EXPLORER_WHAT_IS_WHAT.md** |
| Run locally (frontend + backend) | **RUN_LOCAL.md** |
| Railway deploy, Git, migrations | **docs/RAILWAY_AND_GIT_DEPLOY.md** |
| API reference | **backend/API_DOCUMENTATION.md** |
| Pricing, credits, linear pricing | **docs/PRICING_*.md**, **docs/LLM_AND_PRICING.md** |
| Sidebar, theme, UI proof | **docs/PROOF_SIDEBAR_AND_THEME.md** |
| Legal, compliance | **docs/LEGAL_*.md** |
| Rate/rank, comparisons | **docs/RATE_RANK_*.md**, **docs/PLAYGROUND_COMPARE.md** |

---

## Summary

- **Yes, we created and saved all of this** in the repo. The many folders you see in Cursor’s Explorer are the full CrucibAI product: backend, frontend, docs, scripts, infra, tests, and references.
- **Organization**: Backend = API + agents + DB + orchestration. Frontend = pages + components + state. Docs = how-to and reference. Scripts/infra = runbooks and deploy.
- **“What is what and where”**: Use this file (**docs/EXPLORER_WHAT_IS_WHAT.md**) and **docs/BUILD_TYPES_AND_DEPLOY.md** as the main maps. Everything described here lives in the repo so anyone can know what each part is for.
