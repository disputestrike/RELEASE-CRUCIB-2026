# CrucibAI vs Kimi – Implementation proof (code & features)

This document ties each approved item to **file:location**, **what was implemented**, and **how to test**. Focus: **real code and new features**, not only docs/landing.

---

## B1 – Quick mode
- **Location:** `frontend/src/pages/Workspace.jsx` (state `buildMode === 'quick'`, mode selector ~line 1695).
- **Implemented:** Quick mode skips plan step; single-shot generation. Logic: `isBigBuild` is false when `buildMode === 'quick'`.
- **Test:** Open Workspace → set Mode to "Quick" → send a build prompt → no "Planning..." step; goes straight to "Building...".

## B2 – Thinking mode
- **Location:** Backend `server.py` ~line 564: `mode: "thinking"` → different system prompt. Frontend sends `mode: buildMode === 'thinking' ? 'thinking' : undefined` in chat/stream (Workspace.jsx ~639, ~734).
- **Implemented:** Step-by-step reasoning system prompt in `/api/ai/chat/stream`; frontend mode selector "Thinking".
- **Test:** Set Mode to "Thinking" → send a coding prompt → response should show reasoning then code.

## B3 – Agent/Build mode
- **Location:** `Workspace.jsx` – mode "Agent" (~1697); plan → build flow when `isBigBuild` is true.
- **Implemented:** Full plan + build flow; mode selector label "Agent".
- **Test:** Set Mode to "Agent" → prompt "Build me a todo app" → see Planning then Building.

## A2 / B4 – Swarm (Beta)
- **Location:** Backend `server.py`: `POST /api/build/plan` accepts `swarm: true`, runs plan + suggestions in parallel (`asyncio.gather`). Frontend `Workspace.jsx`: mode "Swarm (Beta)" (~1700); plan request sends `swarm: useSwarm` when logged in (~560).
- **Implemented:** Parallel plan + suggestions when `swarm: true`; UI mode "Swarm (Beta)" (requires login for swarm).
- **Test:** Log in → Workspace → Mode "Swarm (Beta)" → "Build me a dashboard" → plan and suggestions should appear faster (parallel).

## C1 – CrucibAI for Docs
- **Location:** Backend `server.py`: `POST /api/generate/doc` (GenerateContentRequest). Frontend `frontend/src/pages/GenerateContent.jsx` – "Docs" tab.
- **Implemented:** LLM generates document from prompt; returns markdown or plain text; frontend page with prompt + format + Generate + Download.
- **Test:** App → Docs / Slides / Sheets → Docs tab → enter prompt → Generate → Download.

## C2 – CrucibAI for Slides
- **Location:** Backend `server.py`: `POST /api/generate/slides`. Frontend `GenerateContent.jsx` – "Slides" tab.
- **Implemented:** LLM generates slide content with `---` separators; format markdown or outline.
- **Test:** Same page → Slides tab → prompt "5-slide pitch deck for a SaaS" → Generate → Download.

## C3 – CrucibAI for Sheets
- **Location:** Backend `server.py`: `POST /api/generate/sheets`. Frontend `GenerateContent.jsx` – "Sheets" tab.
- **Implemented:** LLM generates CSV or JSON array of objects from prompt.
- **Test:** Same page → Sheets tab → prompt "Sales by region for Q1–Q3" → Generate → Download CSV/JSON.

## E1 – Public API (key-based)
- **Location:** Backend `server.py`: `get_optional_user()` now resolves user from **X-API-Key** header when Bearer is missing. Keys: env `CRUCIBAI_PUBLIC_API_KEYS` (comma-separated) or `db.api_keys` (key, active).
- **Implemented:** Any endpoint using `get_optional_user` (chat, plan, build, generate, etc.) accepts `X-API-Key` for API-only clients.
- **Test:** `curl -X POST http://localhost:8000/api/ai/chat -H "Content-Type: application/json" -H "X-API-Key: YOUR_KEY" -d '{"message":"Hello","session_id":"s1"}'` (after setting CRUCIBAI_PUBLIC_API_KEYS).

---

## Summary

| Item | Code / feature | Where | Status |
|------|----------------|-------|--------|
| B1 Quick | Skip plan, single-shot | Workspace.jsx | Done |
| B2 Thinking | Reasoning system prompt + UI | server.py, Workspace.jsx | Done |
| B3 Agent | Plan → build + label | Workspace.jsx | Done |
| A2/B4 Swarm | Parallel plan+suggestions + UI | server.py, Workspace.jsx | Done |
| C1 Docs | /api/generate/doc + page | server.py, GenerateContent.jsx | Done |
| C2 Slides | /api/generate/slides + page | server.py, GenerateContent.jsx | Done |
| C3 Sheets | /api/generate/sheets + page | server.py, GenerateContent.jsx | Done |
| E1 Public API | X-API-Key in get_optional_user | server.py | Done |

---

## How to run and click-through

1. **Backend:** `cd backend && python -m uvicorn server:app --reload`
2. **Frontend:** `cd frontend && npm start`
3. **Workspace modes:** Go to `/workspace` or `/app/workspace` → use Mode buttons (Quick, Plan, Agent, Thinking, Swarm (Beta)).
4. **Docs/Slides/Sheets:** Log in → sidebar "Docs / Slides / Sheets" → `/app/generate` → choose tab, prompt, Generate, Download.
5. **Public API:** Set `CRUCIBAI_PUBLIC_API_KEYS=your-secret-key` in backend `.env`, then call `/api/ai/chat` or `/api/build/plan` with header `X-API-Key: your-secret-key`.

This is **functional code and new product features** that go beyond documentation and landing copy.

---

## Extra (5th) – Quality gate, one-click deploy, per-step tokens

### Quality gate
- **Location:** Backend `server.py`: `POST /api/ai/quality-gate` (QualityGateBody: code or files). Uses `score_generated_code` from `code_quality.py`; returns `passed` (score ≥ 60), `score`, `verdict`, `breakdown`. Frontend `Workspace.jsx`: after build completes (streaming and non-streaming), calls `/ai/quality-gate` with generated code and sets `qualityGateResult`; status bar shows "Quality: 72% ✓" or "Quality: 60% (review)".
- **Test:** Run a build → when "Done!" appears, wait a moment → status bar shows "Quality: X% ✓" or "(review)".

### One-click deploy
- **Location:** Workspace: "One-click deploy" button (when `files['/App.js']?.code` exists) triggers `handleExportDeploy()` and opens deploy modal. Modal: "Deploy your app", links to Vercel (vercel.com/new) and Netlify (app.netlify.com/drop). Command palette "Deploy" also opens modal after download.
- **Test:** Build an app → click "One-click deploy" → ZIP downloads and modal opens with Vercel/Netlify links.

### Per-step tokens
- **Location:** Backend `server.py`: `build/plan` response includes `plan_tokens` (tokens_estimate). Frontend `Workspace.jsx`: `tokensPerStep` state `{ plan: 0, generate: 0 }`; plan response sets `plan`, stream/chat done sets `generate`. Status bar shows "Plan: ~1.2k · Generate: ~3k" when non-zero.
- **Test:** Run a plan+build (Agent or Swarm) → after build, status bar shows Plan and Generate token estimates.
