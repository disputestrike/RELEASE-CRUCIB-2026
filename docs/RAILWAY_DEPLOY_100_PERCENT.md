# Railway Deploy — Get All 32 Items to 100%

**Purpose:** Exact steps so every gap (Items 1, 5, 17, 20, 29, 31) hits 100% before the product is truly live.

---

## Item 1 — PostgreSQL (→ 100%)

**Current:** 70% (code uses `DATABASE_URL`; no one-click DB).

**Fix:** Add the **Railway Postgres plugin** to your project. It gives you `DATABASE_URL` automatically. One click, not one line of code.

1. In Railway: open your CrucibAI project.
2. Click **+ New** → **Database** → **PostgreSQL** (or **Add Plugin** → Postgres).
3. Railway creates a Postgres service and sets `DATABASE_URL` in the environment for your app service.
4. Redeploy the app so it picks up the variable.

No code change required. Backend already uses `db_pg` and `DATABASE_URL`.

---

## Item 5 — Anthropic API key (→ 100%)

**Current:** 80% (LLM router needs keys).

**Fix:** Add these **Railway variables** (Settings → Variables) for your app service:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (for Claude). |
| `JWT_SECRET` | A long random string for signing JWTs (e.g. `openssl rand -hex 32`). |
| `ENCRYPTION_KEY` | A long random string for encrypting sensitive data (e.g. `openssl rand -hex 32`). |

Three copy-pastes and everything the LLM router needs is live.

---

## Item 17 — Version history (→ 100%)

**Current:** 70% (data stored; frontend was missing).

**Fix (done in code):**

- Backend already appends each build to `project.build_history` and exposes `GET /projects/{project_id}/build-history`.
- **Workspace:** When opened with a `projectId`, a **History** tab is shown in the right panel. It fetches and displays prior builds; each entry has “View in Agent Monitor”.
- **AgentMonitor:** Build history section already shows past builds.

So the frontend History tab now fetches and displays prior builds; user can click through to Agent Monitor for that project. No further code needed; deploy and verify.

---

## Item 20 — Examples Gallery (→ 100%)

**Current:** 60% (backend has examples + fork; need real content).

**Fix:**

- **Code (done):** Backend has `POST /examples/from-project` (body: `project_id`, `name`). AgentMonitor shows **“Publish as example”** for completed projects. Build 5 real apps on the platform, then for each click “Publish as example” and give a name — they appear in the Examples Gallery.
- **Content:** You personally build 5 real apps on the platform and mark them as examples. That’s content, not more engineering.

---

## Item 29 — 60-second wow moment (→ 100%)

**Current:** 70% (Quick build exists; no hard 60s guarantee).

**Fix:** Not a code problem yet.

1. **Deploy first**, then **time** a few builds (especially with “Quick build” checked).
2. If builds are too slow, **tune the LLM router** (e.g. prefer **Cerebras** or another fast model for simple builds / quick_build). Backend already supports `quick_build` (first 2 phases only) and model selection; add or switch to a fast provider for that path if needed.

No code change required for “100%” on the checklist; it’s deploy → measure → tune.

---

## Item 31 — Bring your code (→ 100%)

**Current:** 65% (import existed; ZIP in workspace was missing).

**Fix (done in code):** In the Workspace left sidebar (Explorer), there is an **Upload** (ZIP) button. User selects a `.zip` file; the app parses it and calls `setFiles()` so all code files load into the workspace. One frontend function: take ZIP → parse → setFiles(). Implemented with JSZip.

Deploy and verify: upload a ZIP from the Explorer and confirm files appear in the editor.

---

## Summary

| Item | Action | Status |
|------|--------|--------|
| **1** | Add Railway Postgres plugin (one click) | Config |
| **5** | Add `ANTHROPIC_API_KEY`, `JWT_SECRET`, `ENCRYPTION_KEY` in Railway | Config |
| **17** | History tab in Workspace + build-history API (done) | Code done |
| **20** | Publish as example (done); you add 5 real app examples | Code done + content |
| **29** | Deploy, time builds, tune LLM router (e.g. Cerebras) if slow | Deploy + tune |
| **31** | ZIP upload in Workspace Explorer (done) | Code done |

**Total time to 100% on all 32:** one Railway deploy today (Postgres + env vars), then one focused day to add 5 examples and verify History + ZIP + timing.

---

## Quick Railway checklist

1. **Database:** + New → PostgreSQL (or Postgres plugin) → `DATABASE_URL` set automatically.
2. **Variables:** `ANTHROPIC_API_KEY`, `JWT_SECRET`, `ENCRYPTION_KEY` (and any other keys your app needs).
3. **Deploy** the app; run a build and open Workspace with a projectId → check **History** tab and **Upload ZIP**.
4. **Examples:** Complete 5 projects → “Publish as example” on each → check Examples Gallery.
5. **Item 29:** Time a Quick build after deploy; if needed, switch quick_build path to a faster model (e.g. Cerebras).
