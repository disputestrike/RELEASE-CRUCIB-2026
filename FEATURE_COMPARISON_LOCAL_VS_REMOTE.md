# Feature-by-Feature Comparison: Local vs Remote

**Purpose:** Ensure we don’t leave anything behind when merging. Answer: *Can the remote do everything the local (and frontend) can do? What else must we move from local into remote?*

**Summary:** The **remote does not yet have feature parity** with local. The remote is a **subset**: modular structure and Postgres, but fewer API endpoints. The **frontend** (your current React app) calls many routes that **only exist on local**. So we must **port or re-implement** those endpoints on the remote (Postgres) codebase. Below is the full comparison and the list of “what else to move.”

---

## 1. API shape (prefix)

| | Local | Remote |
|---|--------|--------|
| **Prefix** | `/api` (e.g. `/api/auth/login`) | No prefix (e.g. `/auth/login`) |
| **Frontend** | Uses `API = BACKEND_URL + '/api'` | Would need either `API = BACKEND_URL` or remote adds `prefix="/api"` when mounting routers |

**Action:** Decide once: either (a) add `prefix="/api"` when mounting `api_router` on remote so all paths stay `/api/...`, or (b) keep remote paths without `/api` and change frontend to use `BACKEND_URL` with no `/api`. Recommendation: **add `/api` on remote** so the existing frontend keeps working without changing every call.

---

## 2. Auth (frontend calls these)

| Endpoint (frontend uses) | Local | Remote | Action |
|-------------------------|-------|--------|--------|
| `POST /api/auth/register` | ✅ | Has `/auth/signup` (different path/body?) | Alias or unify: support both or map register → signup. |
| `POST /api/auth/login` | ✅ | ✅ `/auth/login` | Ensure same request/response (JWT, user). |
| `POST /api/auth/verify-mfa` | ✅ | ❓ | Add on remote if MFA exists. |
| `GET /api/auth/me` | ✅ | ✅ `/auth/me` | Ensure same response shape (user, plan, tokens). |
| `GET /api/auth/google` | ✅ (works) | Has `/auth/google/login` (broken?) | **Port local’s working Google OAuth** to remote (same flow, Postgres). |
| `GET /api/auth/google/callback` | ✅ | Has `/auth/google/callback` | Replace with local’s callback logic (find-or-create user, JWT, redirect). |

**Action:** Unify auth paths (and body shapes) with frontend; **bring local’s working Google OAuth** into remote; add MFA verify if remote has MFA.

---

## 3. User / workspace / settings (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `POST /api/user/workspace-mode` or `POST /api/users/me/workspace-mode` | ✅ | ❌ | Add on remote (store in users or prefs table). |
| `GET /api/workspace/env` | ✅ | ❌ | Add on remote (Postgres table + env encryption). |
| `POST /api/workspace/env` | ✅ | ❌ | Add on remote. |
| `GET /api/users/me/deploy-tokens` | ✅ | ❌ | Add on remote. |
| `PATCH /api/users/me/deploy-tokens` | ✅ | ❌ | Add on remote. |
| `GET /api/mfa/status` | ✅ | ❌ | Add on remote if MFA is supported. |
| `POST /api/mfa/setup` | ✅ | ❌ | Add on remote. |
| `POST /api/mfa/verify` | ✅ | ❌ | Add on remote. |
| `POST /api/mfa/disable` | ✅ | ❌ | Add on remote. |
| `GET /api/settings/capabilities` | ✅ | ❌ | Add on remote. |
| `POST /api/users/me/delete` | ✅ | ❌ | Add on remote (with password, delete user + related data). |

**Action:** Implement every row above on remote (Postgres + same contract as local).

---

## 4. Tokens, billing, referrals (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `GET /api/tokens/bundles` | ✅ | ❌ | Add on remote. |
| `POST /api/tokens/purchase` | ✅ | ❌ | Add on remote. |
| `GET /api/tokens/history` | ✅ | ❌ | Add on remote. |
| `GET /api/tokens/usage` | ✅ | ❌ | Add on remote. |
| `GET /api/referrals/code` | ✅ | ❌ | Add on remote. |
| `GET /api/referrals/stats` | ✅ | ❌ | Add on remote. |
| `POST /api/stripe/create-checkout-session` | ✅ | ❌ | Add on remote if you use Stripe. |
| `POST /api/stripe/webhook` | ✅ | ❌ | Add on remote. |

**Action:** Add all token/referral/Stripe endpoints on remote (Postgres-backed).

---

## 5. Projects (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `POST /api/projects` | ✅ | ✅ `POST /projects` | Same; ensure free-tier landing rule and input limits. |
| `GET /api/projects` | ✅ | ✅ `GET /projects` | Same. |
| `GET /api/projects/{id}` | ✅ | ✅ `GET /projects/{id}` | Same. |
| `DELETE /api/projects/{id}` | ✅ | ✅ `DELETE /projects/{id}` | Same; ensure ownership check. |
| `POST /api/projects/import` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/state` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/events` | ✅ | ❌ | Add on remote (or events/snapshot). |
| `GET /api/projects/{id}/events/snapshot` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/logs` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/phases` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/preview-token` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/preview` (and `.../preview/{path}`) | ✅ | ❌ | Add on remote. |
| `POST /api/projects/{id}/retry-phase` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/workspace/files` | ✅ | ✅ `GET /projects/{id}/workspace/files` | Same. |
| `GET /api/projects/{id}/workspace/file` | ✅ | ✅ `GET /projects/{id}/workspace/file` | Same. |
| `GET /api/projects/{id}/dependency-audit` | ✅ | ❌ | Add on remote. |
| `GET /api/projects/{id}/deploy/files` | ✅ | ✅ `GET /projects/{id}/deploy/files` | Same. |
| `GET /api/projects/{id}/deploy/zip` | ✅ | ❌ | Add if frontend uses it. |
| `GET /api/projects/{id}/export/deploy` | ✅ | ❌ | Add if used. |
| `POST /api/projects/{id}/deploy/vercel` | ✅ | ❌ | Add on remote. |
| `POST /api/projects/{id}/deploy/netlify` | ✅ | ❌ | Add on remote. |
| `POST /api/projects/{id}/duplicate` | ✅ | ❌ | Add on remote. |
| `POST /api/projects/from-template` | ✅ | ❌ | Add on remote. |
| `POST /api/projects/{id}/save-as-template` | ✅ | ❌ | Add on remote. |

**Action:** Add every missing project endpoint on remote; keep behavior (including free-tier and ownership).

---

## 6. Build / tasks (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `GET /api/build/phases` | ✅ | ❌ | Add on remote. |
| `POST /api/build/plan` | ✅ | ❌ | Add on remote (or under projects). |
| `POST /api/build/from-reference` | ✅ | ❌ | Add on remote if used. |
| `POST /api/tasks` | ✅ | ❌ | Add on remote. |

**Action:** Add on remote. Remote has `POST /projects/{id}/build`; ensure it (or a separate build/plan) supports the same flow as local.

---

## 7. Agents (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `GET /api/agents` | ✅ | ✅ `GET /agents` | Same. |
| `GET /api/agents/{id}` | ✅ | ❌ (only webhook/activity?) | Add GET by id on remote. |
| `GET /api/agents/{id}/runs` | ✅ | ❌ | Add on remote. |
| `DELETE /api/agents/{id}` | ✅ | ✅ `DELETE /agents/{id}` | Same. |
| `POST /api/agents/{id}/webhook-rotate-secret` | ✅ | ❌ | Add on remote. |
| `GET /api/agents/runs/{runId}/logs` | ✅ | ❌ | Add on remote. |
| `GET /api/agents/status/{projectId}` | ✅ | ❌ | Add on remote. |
| `GET /api/agents/activity` | ✅ | ✅ `GET /agents/activity` | Same. |
| `POST /api/agents/from-description` | ✅ | ❌ | Add on remote. |

**Action:** Add missing agent endpoints (get by id, runs, logs, status, webhook-rotate, from-description).

---

## 8. AI / chat / tools (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `POST /api/ai/chat` | ✅ | ✅ `POST /ai/chat` | Same. |
| `GET /api/ai/chat/history/{sessionId}` | ✅ | ✅ `GET /ai/chat/history/{session_id}` | Same. |
| `POST /api/ai/chat/stream` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/explain-error` | ✅ | ✅ `POST /ai/explain-error` | Same. |
| `POST /api/ai/quality-gate` | ✅ | ✅ `POST /ai/quality-gate` | Same. |
| `POST /api/ai/analyze` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/validate-and-fix` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/security-scan` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/accessibility-check` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/suggest-next` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/optimize` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/image-to-code` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/design-from-url` | ✅ | ❌ | Add on remote. |
| `POST /api/ai/inject-stripe` | ✅ | ❌ | Add on remote if used. |
| `POST /api/voice/transcribe` | ✅ | ❌ | Add on remote. |
| `POST /api/files/analyze` | ✅ | ❌ | Add on remote. |

**Action:** Add every missing AI/voice/files endpoint on remote.

---

## 9. Export / share / examples / templates / patterns (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `POST /api/export/zip` | ✅ | ❌ | Add on remote. |
| `POST /api/export/github` | ✅ | ❌ | Add on remote. |
| `POST /api/export/deploy` | ✅ | ❌ | Add on remote. |
| `POST /api/share/create` | ✅ | ❌ | Add on remote. |
| `GET /api/share/{token}` | ✅ | ❌ | Add on remote. |
| `GET /api/examples` | ✅ | ❌ | Add on remote. |
| `GET /api/examples/{name}` | ✅ | ❌ | Add on remote. |
| `POST /api/examples/{name}/fork` | ✅ | ❌ | Add on remote. |
| `GET /api/templates` | ✅ | ❌ | Add on remote. |
| `POST /api/projects/from-template` | ✅ | ❌ | Add on remote (see Projects). |
| `GET /api/patterns` | ✅ | ❌ | Add on remote. |
| `POST /api/exports` | ✅ | ❌ | Add on remote if used. |
| `GET /api/exports` | ✅ | ❌ | Add on remote if used. |

**Action:** Add all of these on remote.

---

## 10. Prompts (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `GET /api/prompts/templates` | ✅ | ❌ | Add on remote. |
| `GET /api/prompts/recent` | ✅ | ❌ | Add on remote. |
| `POST /api/prompts/save` | ✅ | ❌ | Add on remote. |
| `GET /api/prompts/saved` | ✅ | ❌ | Add on remote. |

**Action:** Add on remote.

---

## 11. Audit / admin (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `GET /api/audit/logs` | ✅ | ❌ | Add on remote (or map to admin audit-logs). |
| `GET /api/audit/logs/export` | ✅ | ❌ | Add on remote. |
| `GET /api/admin/dashboard` | ✅ | ✅ `GET /admin/dashboard` | Same. |
| `GET /api/admin/users` | ✅ | ✅ `GET /admin/users` | Same. |
| `GET /api/admin/users/{id}` | ✅ | ✅ `GET /admin/users/{id}` (or PUT) | Ensure same. |
| `POST /api/admin/users/{id}/grant-credits` | ✅ | ✅ `POST /admin/users/{id}/credits` | Alias or same path. |
| `POST /api/admin/users/{id}/suspend` | ✅ | ❓ | Add if missing. |
| `GET /api/admin/billing/transactions` | ✅ | ❌ | Add on remote. |
| `GET /api/admin/legal/blocked-requests` | ✅ | ❌ | Add on remote. |
| `POST /api/admin/legal/review/{id}` | ✅ | ❌ | Add on remote. |
| `GET /api/admin/analytics/daily` | ✅ | ❌ | Add on remote. |
| `GET /api/admin/analytics/weekly` | ✅ | ❌ | Add on remote. |
| `GET /api/admin/analytics/report` | ✅ | ❌ | Add on remote. |

**Action:** Add missing admin/audit endpoints; align path names with frontend (e.g. grant-credits vs credits).

---

## 12. Dashboard / brand / health / errors (frontend)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `GET /api/dashboard/stats` | ✅ | ❌ | Add on remote. |
| `GET /api/brand` | ✅ | ❌ | Add on remote. |
| `GET /api/health` | ✅ | ❌ (or root /health) | Ensure frontend can call it (e.g. /api/health). |
| `POST /api/errors/log` | ✅ | ❌ | Add on remote (client error reporting). |

**Action:** Add dashboard, brand, health (with optional `?deps=1`), and errors/log on remote.

---

## 13. Generate (frontend: GenerateContent)

| Endpoint | Local | Remote | Action |
|----------|-------|--------|--------|
| `POST /api/generate/doc` | ✅ | ❌ | Add on remote. |
| `POST /api/generate/slides` | ✅ | ❌ | Add on remote. |
| `POST /api/generate/sheets` | ✅ | ❌ | Add on remote. |

**Action:** Add on remote if you use GenerateContent.

---

## 14. Backend-only (local has; frontend may not call directly)

These are used by other backend logic or by build flow; remote may need them for parity:

- Many **agent run** endpoints (e.g. `/api/agents/run/planner`, `/api/agents/run/backend-generate`, …): local has dozens; remote’s orchestration may call different entry points. **Action:** Ensure remote’s build/orchestration can do the same work (same or equivalent routes, or single entry that runs the DAG).
- **Webhook:** `POST /api/agents/webhook/{agent_id}` — remote has `POST /agents/webhook/{agent_id}`. **Action:** Keep; align path with `/api` if we add prefix.
- **Build phases** (internal), **project state**, **events** — needed for AgentMonitor and Workspace. **Action:** Already listed above under Projects/Build.

---

## 15. Direct answer to your questions

**Can the remote do everything the local can do?**  
**No.** Today the remote is a **subset**: auth (different paths), projects (basic CRUD + workspace/deploy files), agents (basic + activity), ai (chat, explain-error, quality-gate). Everything else the frontend and local backend do (tokens, referrals, MFA, workspace env, deploy tokens, settings/capabilities, account/project deletion, build/plan, tasks, phases, logs, events, preview, dependency-audit, retry-phase, export/share/examples/templates/patterns, prompts, audit logs, admin analytics/billing/legal, dashboard, brand, health deps, all other AI/voice/files endpoints, generate doc/slides/sheets, etc.) must be **added or ported** to the remote.

**What else do we need to move from local into remote?**  
Everything in the tables above where **Action** says “Add on remote” or “Port local’s …”. That is the full list of features/endpoints to move or re-implement so that:

1. The **frontend** keeps working without changing its API base or path list (once we fix prefix and auth paths).
2. The **remote** can do everything the local app can do (same capabilities, on Postgres).

**So we’re not leaving anything behind?**  
Only if we:  
- Add the **/api** prefix (or switch frontend to no prefix) and align **auth** paths and bodies.  
- Port **local’s working Google OAuth** to remote.  
- Implement every endpoint in the “Action” columns above on the remote (Postgres) codebase.  
- Re-apply all **security/audit** and **logApiError** work from the merge plan.

This doc is the **feature checklist** for the merge; the **MERGE_PLAN_REMOTE_BASE_WITH_LOCAL_IMPROVEMENTS.md** is the **how** (order of operations, Google OAuth first, then indexes, encryption, deletion, frontend logApiError, tests, docs). Together they define “everything from local that must exist on remote.”
