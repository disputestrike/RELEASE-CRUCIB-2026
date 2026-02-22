# CrucibAI Implementation Plan: Connectivity & Functionality

**Source of Truth:** CrucibAI Source Bible V3 + V4 Audit  
**Date:** February 2026  
**Focus:** Fix missing pieces, wire disconnected components, backend connectivity

---

## Executive Summary

The look and feel is now stable (light theme, 4-zone layout, sidebar). This plan focuses on **connectivity** — what's specified but not wired, what's broken, and what must be implemented for full functionality.

---

## 1. Critical Missing Backend Routes

| Gap | V3 Spec | Current State | Action |
|-----|---------|---------------|--------|
| `/api/tasks` | Not in V3 route list | **Does not exist** | Layout.jsx & Workspace.jsx call `GET /tasks` and `POST /tasks` — **404** |
| Admin routes | 20+ admin routes | 9 missing (analytics, etc.) | Add missing admin/analytics routes to server.py |

**Decision for /tasks:**
- **Option A:** Add `GET /api/tasks` and `POST /api/tasks` to server.py (if tasks != projects)
- **Option B:** Remove frontend calls to `/tasks` and use `/projects` only (recommended — task store uses localStorage, projects are API)

**Files to touch:** `backend/server.py`, `frontend/src/components/Layout.jsx`, `frontend/src/stores/useTaskStore.js`

---

## 2. Backend Secrets & Environment

| Issue | Impact | Fix |
|-------|--------|-----|
| `JWT_SECRET` missing | 500 errors on /login | Add to Railway/.env; server must fail fast if missing |
| `MONGO_URL` missing | DB connection fails | Add to Railway/.env |
| Google OAuth | Callback fails | Configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Stripe webhook | Signature bypassed in dev | Enable verification in production; document dev bypass |

**Protocol (V4):** Server MUST NOT start if `JWT_SECRET` or `MONGO_URL` are missing. Add pre-flight check in server startup.

---

## 3. Component Integration Gaps

| Component | Status | Action |
|-----------|--------|--------|
| **VibeCoding** | Exists, not integrated | Import into Workspace.jsx; add as optional voice-first input mode |
| **AdvancedIDEUX** | Exists, not integrated | Import into Workspace.jsx (Developer mode); Minimap, AI Autocomplete, Command Palette |
| **ManusComputer** | Partially wired | Full WebSocket feed for live token counts; wire `agentActivity` → props |
| **CrucibAIComputer** | In Workspace | Verify WebSocket → real agent count, real token count (never zero) |

---

## 4. WebSocket & Real-Time

| Issue | Fix |
|-------|-----|
| No auto-reconnection | Add reconnect logic when WS disconnects; exponential backoff |
| ManusComputer tokens | Ensure WebSocket events include `tokens_used`; pass to component |
| Agent activity feed | Wire `agent_started` / `agent_completed` events to UI |

---

## 5. Agent Tool Runner (Phase 6/7)

V4: "Need real tool-runner logic for Phase 6/7 agents."

- Verify `backend/tool_executor.py` is invoked for Browser, File, API, Database, Deploy tools
- Ensure orchestration calls `tool_executor.execute_tool()` when agent step requires it
- Add state validation: agents must write STATE_WRITERS keys before phase completes

---

## 6. CI Pipeline & E2E Tests

| Layer | Status | Action |
|-------|--------|--------|
| Enterprise 9-layer tests | Some fail | Run full suite; fix failing tests |
| `single-source-of-truth.spec.js` | Referenced | Ensure E2E passes: auth → build → preview → export |
| Pre-commit | — | Run `npm audit`, `pip check` before build |

---

## 7. Implementation Order (Priority)

### Phase 1 — Critical (1–2 days)
1. **Fix /tasks** — Remove or replace frontend calls; add route if tasks ≠ projects
2. **Backend pre-flight** — Fail startup if JWT_SECRET or MONGO_URL missing
3. **Secrets** — Document required env vars; add to Railway

### Phase 2 — High (2–4 days)
4. **VibeCoding** — Embed in Workspace.jsx
5. **AdvancedIDEUX** — Embed in Workspace.jsx (Developer mode)
6. **ManusComputer** — Wire WebSocket → live tokens, agent names

### Phase 3 — Medium
7. **WebSocket reconnection** — Auto-reconnect on disconnect
8. **Quality gate** — Fix parsedFiles/content so quality gate doesn't return 0
9. **CI** — Fix failing E2E tests; achieve green pipeline

### Phase 4 — Integration
10. **Google OAuth** — Configure client secrets
11. **Stripe webhook** — Enable signature verification in prod
12. **Admin routes** — Add missing 9 routes

---

## 8. Files to Modify (Summary)

| File | Changes |
|------|---------|
| `backend/server.py` | Pre-flight check; add /tasks if needed; missing admin routes |
| `frontend/src/pages/Workspace.jsx` | Integrate VibeCoding, AdvancedIDEUX; wire ManusComputer |
| `frontend/src/components/Layout.jsx` | Fix /tasks call → /projects or remove |
| `frontend/src/stores/useTaskStore.js` | Ensure no /tasks dependency if route removed |
| `frontend/e2e/single-source-of-truth.spec.js` | Fix failing assertions |
| `.github/workflows/enterprise-tests.yml` | Ensure all layers pass |

---

## 9. What Is Already Connected (No Action)

- Auth (JWT, MFA)
- Projects CRUD
- Build orchestration (123 agents)
- Workspace Sandpack, multi-file
- AgentMonitor WebSocket progress
- Import (paste/ZIP/Git)
- Deploy (Vercel, Netlify, ZIP, GitHub)
- Content gen (docs/slides/sheets)
- TokenCenter, Settings, Share
- Templates, Patterns, Prompts, Examples
- Voice transcription (VoiceWaveform)
- Dashboard intent detection, auto-start build

---

## 10. Next Steps

1. **Confirm** — Review this plan; approve or adjust priorities  
2. **Phase 1** — Implement critical fixes (/tasks, pre-flight, secrets)  
3. **Phase 2** — Integrate VibeCoding, AdvancedIDEUX, ManusComputer  
4. **Validate** — Run full CI; fix E2E until green  
