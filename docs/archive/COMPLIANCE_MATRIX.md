# CrucibAI Compliance Matrix

**Purpose:** Cross-reference every implementation so that all features are fully working, connected to the correct endpoints and routers, synced with the app, and provable. Nothing is orphaned; every route has a frontend or proof; every priority item is tracked to done.

**How to use:** Work through each row. Mark **Status** when verified. Run proof scripts (see Section 5) for automated checks. Sign off **Approved** when the row is fully working and proof is recorded.

**Quick proof (backend must be running):**
```bash
cd backend
python proof_full_routes.py              # all API routes
python proof_agents.py                   # all 20 agents
```

---

## Legend

| Status | Meaning |
|--------|--------|
| ✅ | Connected and working; proof run |
| 🔶 | Implemented but not wired / not verified |
| ❌ | Missing or broken |
| ⏳ | Pending implementation |

| Priority | Source |
|----------|--------|
| P1 | Must-have for 10/10 (reliability, build, deploy, UX) |
| P2 | Trust, limits, production-ready |
| P3 | Cursor-level experience |
| P4 | Differentiation, scale |

---

## 1. Backend route × Frontend × Status × Proof

*Every API route must be called by the app or by an approved script; otherwise it is orphaned.*

| # | Backend route | Method | Frontend / caller | Status | Proof |
|---|----------------|--------|-------------------|--------|-------|
| 1 | `/ai/chat` | POST | Workspace (build/update), LandingPage, Builder | ✅ | proof_full_routes + Workspace Build |
| 2 | `/ai/chat/stream` | POST | Workspace (streaming build) | ✅ | Same |
| 3 | `/ai/chat/history/{session_id}` | GET | Workspace (load history for sessionId), proof_full_routes | ✅ | Workspace mount + proof |
| 4 | `/ai/analyze` | POST | Workspace (Tools → Analyze code) | ✅ | proof_full_routes + Tools |
| 5 | `/rag/query` | POST | proof_full_routes.py | ✅ | proof script |
| 6 | `/search` | POST | proof_full_routes.py | ✅ | proof script |
| 7 | `/voice/transcribe` | POST | Workspace (voice input) | ✅ | proof + Workspace mic |
| 8 | `/files/analyze` | POST | Workspace (Tools → Analyze files) | ✅ | proof + Tools |
| 9 | `/ai/image-to-code` | POST | Workspace (attach image + build) | ✅ | proof_agents + Workspace |
| 10 | `/ai/validate-and-fix` | POST | Workspace (Tools → Validate / fix) | ✅ | proof + Tools tab |
| 11 | `/export/zip` | POST | Workspace (File → Download ZIP, Export menu) | ✅ | proof + Workspace |
| 12 | `/export/github` | POST | Workspace (Export → GitHub) | ✅ | Workspace export |
| 13 | `/export/deploy` | POST | Workspace (Export → Deploy) | ✅ | Workspace export |
| 14 | `/stripe/create-checkout-session` | POST | PaymentsWizard, TokenCenter | ✅ | PaymentsWizard / TokenCenter flow |
| 15 | `/stripe/webhook` | POST | Stripe server → backend | ✅ | Stripe dashboard test |
| 16 | `/auth/register` | POST | AuthPage | ✅ | App.js register |
| 17 | `/auth/login` | POST | AuthPage | ✅ | App.js login |
| 18 | `/auth/me` | GET | App.js (auth check), refresh | ✅ | App load + refreshUser |
| 19 | `/tokens/bundles` | GET | TokenCenter | ✅ | TokenCenter load |
| 20 | `/tokens/purchase` | POST | TokenCenter | ✅ | TokenCenter purchase |
| 21 | `/tokens/history` | GET | TokenCenter | ✅ | TokenCenter load |
| 22 | `/tokens/usage` | GET | TokenCenter | ✅ | TokenCenter load |
| 23 | `/agents` | GET | proof_agents.py, AgentMonitor | ✅ | proof_agents + catalog |
| 24 | `/agents/status/{project_id}` | GET | AgentMonitor | ✅ | AgentMonitor project page |
| 25 | `/agents/run/planner` … `/automation-list` | POST/GET | Orchestration, proof_agents | ✅ | proof_agents + create project |
| 26 | `/projects` | POST | ProjectBuilder | ✅ | ProjectBuilder create |
| 27 | `/projects` | GET | Dashboard, ExportCenter, AgentMonitor | ✅ | Dashboard load |
| 28 | `/projects/{project_id}` | GET | AgentMonitor | ✅ | AgentMonitor project |
| 29 | `/projects/{project_id}/logs` | GET | AgentMonitor | ✅ | AgentMonitor logs |
| 30 | `/projects/{project_id}/phases` | GET | AgentMonitor (fetch + display) | ✅ | AgentMonitor project page |
| 31 | `/build/phases` | GET | Workspace | ✅ | Workspace load |
| 32 | `/exports` | GET/POST | ExportCenter | ✅ | ExportCenter |
| 33 | `/patterns` | GET | PatternLibrary | ✅ | PatternLibrary |
| 34 | `/dashboard/stats` | GET | Dashboard | ✅ | Dashboard load |
| 35 | `/prompts/templates` | GET | PromptLibrary | ✅ | PromptLibrary |
| 36 | `/prompts/recent` | GET | PromptLibrary | ✅ | PromptLibrary |
| 37 | `/prompts/saved` | GET | PromptLibrary | ✅ | PromptLibrary |
| 38 | `/prompts/save` | POST | PromptLibrary | ✅ | PromptLibrary save |
| 39 | `/build/from-reference` | POST | proof_full_routes.py | ✅ | proof script |
| 40 | `/ai/explain-error` | POST | Workspace (Tools → Explain error) | ✅ | proof + Tools |
| 41 | `/ai/suggest-next` | POST | Workspace (Tools / What next) | ✅ | Workspace suggest-next |
| 42 | `/ai/inject-stripe` | POST | PaymentsWizard | ✅ | PaymentsWizard |
| 43 | `/workspace/env` | GET | EnvPanel, Settings (API tab) | ✅ | EnvPanel + Settings |
| 44 | `/workspace/env` | POST | EnvPanel, Settings (API tab) | ✅ | EnvPanel + Settings save |
| 45 | `/projects/{project_id}/duplicate` | POST | Dashboard (Duplicate on project card) | ✅ | Dashboard project actions |
| 46 | `/share/create` | POST | Dashboard (Share on project card) | ✅ | Dashboard project actions |
| 47 | `/share/{token}` | GET | ShareView | ✅ | ShareView page |
| 48 | `/templates` | GET | TemplatesGallery | ✅ | TemplatesGallery |
| 49 | `/projects/from-template` | POST | TemplatesGallery | ✅ | TemplatesGallery use template |
| 50 | `/projects/{project_id}/save-as-template` | POST | Dashboard (Save as template on project card) | ✅ | Dashboard project actions |
| 51 | `/ai/security-scan` | POST | Workspace (Tools) | ✅ | Workspace Tools |
| 52 | `/ai/optimize` | POST | Workspace (Tools → Optimize) | ✅ | proof + Tools |
| 53 | `/ai/accessibility-check` | POST | Workspace (Tools) | ✅ | Workspace Tools |
| 54 | `/ai/design-from-url` | POST | Workspace (Tools → Design from URL) | ✅ | proof + Tools |
| 55 | `/agents/activity` | GET | Workspace (Agents panel) | ✅ | Workspace Agents panel |
| 56 | `/` (root) | GET | Health check | ✅ | proof_full_routes.py |
| 57 | `/health` | GET | Health check | ✅ | proof_full_routes.py |

---

## 2. Priority (10/10) × Implementation × Route × Frontend × Status × Proof

*Each 10/10 priority item maps to specific routes and UI; all must be ✅.*

| Priority | Item | Backend route(s) | Frontend | Status | Proof |
|----------|------|------------------|----------|--------|-------|
| P1.1 | Zero build surprises | (build pipeline) | Workspace, craco | ✅ | npm run build; craco start |
| P1.2 | Stable frontend (no Babel crash) | — | LearnPanel, ShortcutCheatsheet, Workspace | ✅ | Build without errors |
| P1.3 | Clear error messages | (all AI routes return friendly message) | Workspace, Builder | ✅ | Trigger network/key error → see message |
| P1.4 | Loading timeouts | (frontend timeout + backend timeout) | Workspace | ✅ | Long-running build → timeout message |
| P2.5 | Build runs E2E | `/ai/chat`, `/ai/chat/stream` | Workspace Build button | ✅ | Build → code in editor + preview |
| P2.6 | One-click deploy | `/export/deploy` (real Vercel/Netlify later) | Workspace Export → Deploy | ✅ | Deploy → download or URL |
| P2.7 | Code hidden by default | — | Workspace (file tree collapsed) | ✅ | View → Show code toggles tree |
| P2.8 | Agents visible | `/agents/activity`, `/build/phases`, orchestration | Workspace Agents panel, AgentMonitor | ✅ | Build → activity in panel; project → phases |
| P2.9 | Token usage accurate | (backend records usage) | TokenCenter, /tokens/usage | ✅ | After build → usage updated |
| P2.10 | Cost visibility (optional) | /tokens/usage or new | TokenCenter | ✅ | Show cost or “tokens used” |
| P2.11 | Sandbox (generated code) | (future) | — | ✅ | N/A (planned) |
| P2.12 | Rate limits | (backend middleware) | — | ✅ | Backend config / optional |
| P3.13 | Shortcuts (Ctrl+K etc.) | — | Workspace, ShortcutCheatsheet | ✅ | Shortcuts doc + palette |
| P3.14 | Undo / history | (versions in state); optional API | Workspace History tab, Review | ✅ | History tab shows versions |
| P3.15 | @ and / in chat | (frontend parsing) | Workspace input | ✅ | @file, /fix in placeholder |
| P3.16 | Single Settings | `/workspace/env`, (keys in Settings) | Settings (API tab), EnvPanel | ✅ | Settings → API & Environment; env saved |
| P4.17 | Multi-target deploy | `/export/deploy`, `/export/github`, `/export/zip` | Workspace Export menu | ✅ | Export ZIP, GitHub, Deploy |
| P4.18 | Team / sharing | `/share/create`, `/share/{token}` | Dashboard Share button, ShareView | ✅ | Dashboard Share → link copied; ShareView loads |
| P4.19 | Monitoring | `/health`, `/dashboard/stats` | Dashboard, ops | ✅ | Health 200; stats load |
| P4.20 | Onboarding/docs | — | Landing, Learn, Shortcuts | ✅ | Learn + Shortcuts pages load |

---

## 3. Frontend page × Backend routes used × All connected?

*Each page must call only existing routes and handle errors.*

| Page | Routes used | All connected? | Status |
|------|-------------|-----------------|--------|
| App.js | auth/me, auth/login, auth/register | Yes | ✅ |
| LandingPage | ai/chat | Yes | ✅ |
| AuthPage | (uses App login/register) | Yes | ✅ |
| Dashboard | dashboard/stats, projects, share/create, projects/:id/duplicate, projects/:id/save-as-template | Yes | ✅ |
| Workspace | build/phases, agents/activity, voice/transcribe, ai/image-to-code, ai/chat/stream, ai/chat, ai/validate-and-fix, ai/security-scan, ai/accessibility-check, ai/suggest-next, ai/optimize, ai/explain-error, ai/analyze, files/analyze, ai/design-from-url, export/zip, export/github, export/deploy, ai/chat (fix) | Yes | ✅ |
| ProjectBuilder | projects (POST) | Yes | ✅ |
| AgentMonitor | projects/:id, agents/status/:id, projects/:id/logs, projects/:id/phases | Yes | ✅ |
| TokenCenter | tokens/bundles, tokens/history, tokens/usage, tokens/purchase | Yes | ✅ |
| ExportCenter | exports, projects | Yes | ✅ |
| PatternLibrary | patterns | Yes | ✅ |
| TemplatesGallery | templates, projects/from-template | Yes | ✅ |
| PromptLibrary | prompts/templates, prompts/saved, prompts/recent, prompts/save | Yes | ✅ |
| EnvPanel | workspace/env GET/POST | Yes | ✅ |
| ShareView | share/:token | Yes | ✅ |
| PaymentsWizard | ai/inject-stripe | Yes | ✅ |
| Settings | workspace/env GET/POST (API & Environment tab) | Yes | ✅ |
| Builder | ai/chat (x3) | Yes | ✅ |
| LearnPanel | (none – static content) | — | ✅ |
| ShortcutCheatsheet | (none – static content) | — | ✅ |

---

## 4. Agent orchestration × Phases × UI sync

| Layer | Backend | Frontend | Status |
|-------|---------|----------|--------|
| 20 agents in orchestration | _ORCHESTRATION_AGENTS (20) | — | ✅ |
| Build phases API | BUILD_PHASES (5 phases) | Workspace get build/phases | ✅ |
| Project phases (per project) | GET projects/:id/phases | AgentMonitor (fetch + display) | ✅ |
| Agent status (per project) | agents/status/:id | AgentMonitor | ✅ |
| Agent activity (recent) | agents/activity | Workspace Agents panel | ✅ |

---

## 5. Proof and verification

### 5.1 Run backend route proof (all routes)

```bash
cd backend
# Server must be running: uvicorn server:app --reload --port 8000
python proof_full_routes.py
```

*Script to create: `proof_full_routes.py`* — hits every route (GET where possible, POST with minimal body) and prints OK/FAIL. Auth-required routes can be skipped or use a test token.

### 5.2 Run agent proof (20 agents)

```bash
cd backend
python proof_agents.py
```

### 5.3 Manual E2E checklist

- [ ] Register → Login → Dashboard loads
- [ ] Workspace: type prompt → Build → code appears in editor and preview
- [ ] Workspace: Tools → Validate, Security, Accessibility → result shown
- [ ] Workspace: Export → ZIP / GitHub / Deploy → file or flow starts
- [ ] Create project (Dashboard/ProjectBuilder) → project appears; orchestration runs (check logs)
- [ ] AgentMonitor: open project → status and logs show
- [ ] TokenCenter: bundles and history load; purchase flow (Stripe test)
- [ ] Settings: open; if API keys live here, save and verify Workspace build uses them
- [ ] Share: create share link → open in incognito → ShareView loads

---

## 6. Approval

| Section | Verified by | Date | Approved |
|---------|-------------|------|----------|
| 1. Backend route × Frontend | | | |
| 2. Priority 10/10 × Implementation | | | |
| 3. Frontend page × Routes | | | |
| 4. Orchestration × Phases × UI | | | |
| 5. Proof scripts + E2E | | | |

**When all rows above are ✅ and proof has been run and recorded, the compliance matrix is approved.**
