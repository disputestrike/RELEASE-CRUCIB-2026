# CrucibAI – Full Audit, Click-Through Test, and #1 Readiness

**Date:** February 9, 2026  
**Scope:** Functionality, features, click-through flows, blockers, and “what would make this #1.”

---

## 1. Click-Through Test (Critical Paths)

### 1.1 Anonymous / Landing
| Step | Action | Expected | Status / Notes |
|------|--------|----------|----------------|
| 1 | Open `/` | Landing page, dark theme, prompt input | ✅ Implemented |
| 2 | Type prompt, submit | Redirect to `/workspace?prompt=...` | ✅ |
| 3 | Click suggestion chips | Same redirect with prefill | ✅ |

### 1.2 Auth
| Step | Action | Expected | Status / Notes |
|------|--------|----------|----------------|
| 1 | Go to `/auth` | Login/Register tabs | ✅ |
| 2 | Register (email, password, name) | JWT stored, redirect | ✅ (needs backend + MongoDB) |
| 3 | Login | JWT, redirect to app or `from` | ✅ |
| 4 | Visit `/app/*` without token | Redirect to `/auth` | ✅ ProtectedRoute |

### 1.3 Workspace (Build Flow)
| Step | Action | Expected | Status / Notes |
|------|--------|----------|----------------|
| 1 | Land on `/workspace` (with or without `?prompt=`) | Monaco + Sandpack + chat, default App.js | ✅ |
| 2 | Submit text prompt (no prior version) | `handleBuild` → POST /api/ai/chat or /stream → code in editor + preview | ⚠️ Depends on LLM (OPENAI_API_KEY / LLM_API_KEY + provider) |
| 3 | Submit modification (with prior version) | `handleModify` → updated App.js | ⚠️ Same dependency |
| 4 | Attach image only, submit | Image-to-code → POST /api/ai/image-to-code | ⚠️ Needs OpenAI vision |
| 5 | Voice record → stop | Transcribe → text in input | ⚠️ Needs Whisper/STT |
| 6 | Export (download) | ZIP/files download | ✅ |
| 7 | Deploy (button) | Deploy ZIP download | ✅ |
| 8 | GitHub (button) | GitHub ZIP download | ✅ |
| 9 | Auto-fix (after error) | POST /api/ai/chat with fix prompt | ⚠️ LLM-dependent |
| 10 | Ctrl+K | Command palette | ✅ |
| 11 | Menu bar (File, View, etc.) | Dropdowns with actions | ✅ |
| 12 | Review tab | N files, Undo All / Keep All | ✅ |
| 13 | Status bar | Project, errors, tokens | ✅ |

### 1.4 App Shell (/app)
| Step | Action | Expected | Status / Notes |
|------|--------|----------|----------------|
| 1 | Dashboard | Stats, recent projects | ✅ |
| 2 | Tokens | Bundles, purchase, history | ✅ (Stripe needs keys for real pay) |
| 3 | Exports | List of exports | ✅ |
| 4 | Patterns | Pattern library | ✅ |
| 5 | Templates | Gallery, “Use template” | ✅ (from-template needs LLM) |
| 6 | Prompt Library | Templates, saved, recent | ✅ |
| 7 | Learn | Tips / docs | ✅ |
| 8 | Env | Workspace env vars | ✅ |
| 9 | Shortcuts | Cheat sheet | ✅ |
| 10 | Add payments wizard | Stripe inject steps | ✅ |
| 11 | Settings | User/settings UI | ✅ |
| 12 | Share view `/share/:token` | Read-only project view | ✅ |

### 1.5 Projects
| Step | Action | Expected | Status / Notes |
|------|--------|----------|----------------|
| 1 | New project | ProjectBuilder flow | ✅ |
| 2 | Project detail `/app/projects/:id` | AgentMonitor | ✅ |
| 3 | Duplicate project | POST /api/projects/:id/duplicate | ✅ Backend |
| 4 | Create share link | POST /api/share/create | ✅ Backend |

---

## 2. Function & Features Analysis

### 2.1 Is the app doing what it’s supposed to do?

**PRD core promise:** “Users describe what they want in natural language; AI agents build it.”

| Capability | Intended | Actual | Gap |
|------------|----------|--------|-----|
| Text → app | User types prompt → full React app | Backend calls LLM; returns code; editor + preview update | ✅ When LLM and keys are configured |
| Iterate via chat | “Add a button” etc. | handleModify sends current code + request to LLM | ✅ Same dependency |
| Image → code | Screenshot/reference → code | POST /api/ai/image-to-code (OpenAI vision) | ✅ With OPENAI_API_KEY |
| Voice input | Speak → text in box | Transcribe endpoint → set input | ✅ With STT configured |
| Multi-model | Auto / GPT-4o / Claude / Gemini | Model chain + fallback in backend | ✅ With provider lib + keys |
| Export / Deploy | Download, GitHub, Deploy ZIPs | Endpoints and UI present | ✅ |
| Tokens & paywall | Consume tokens, buy more | Balance, deduct, Stripe (needs keys) | ✅ Logic in place |
| Auth | Register, login, JWT | Implemented | ✅ |
| Workspace UX | Cursor-style menus, agents panel, review, status bar, palette | Implemented | ✅ |

**Verdict:** Yes, for the scope of the PRD, the app does what it’s supposed to do **provided** the AI stack (LLM + optional Whisper/vision) and MongoDB (and optionally Stripe) are configured and working.

### 2.2 Can it be better?

| Area | Current | Improvement |
|------|---------|-------------|
| **Streaming** | Chunked string simulation | True token/SSE streaming from provider |
| **Errors** | lastError + Auto-fix button | Inline error under editor, “Explain error” + fix |
| **Files** | Mostly single-file App.js | Multi-file generation (components, CSS) |
| **Preview** | Sandpack | Optional “Open in new tab” / real deploy preview URL |
| **Agents panel** | Activity from chat history | Real task queue, steps, tokens per step |
| **@ and / in chat** | Placeholder text only | Real @file / @docs and /fix, /explain commands |
| **Validate-and-fix** | Backend endpoint exists | Wire to “Validate” button and show report in UI |
| **Templates from API** | From-template generates code via LLM | Cache seed code per template to avoid LLM on every use |
| **Security scan / a11y** | Backend endpoints | Buttons in workspace + report panel |
| **Offline / demo** | Needs backend + DB | Optional “demo mode” with canned responses |
| **Performance** | Full re-renders on code change | Throttle Sandpack refresh, virtualize long lists |
| **Mobile** | Responsive layout | Dedicated mobile preview toggle and touch UX |

---

## 3. Blockers for “Working” (Production-Ready)

1. **LLM / API keys**
   - Backend expects `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` (and optionally `GEMINI_API_KEY`). No third-party integration package; all LLM and voice use direct APIs.
   - Without valid keys, build, modify, image-to-code, auto-fix, and voice fail.

2. **MongoDB**
   - Auth, tokens, projects, chat history, exports require MongoDB.
   - `MONGO_URL` and `DB_NAME` must be set and reachable.

3. **Stripe (optional but for real payments)**
   - Token purchase and webhook need Stripe keys and webhook URL.
   - Without them, “buy tokens” doesn’t complete real payments.

4. **Frontend build**
   - Visual-edits Babel plugin was removed to fix build; `npm run start` uses craco without that plugin.
   - Port 3000 must be free; backend typically on 8000.

5. **CORS**
   - Backend `.env`: `CORS_ORIGINS` must include the frontend origin (e.g. `http://localhost:3000`).

6. **LLM and voice**
   - Backend uses only direct APIs: OpenAI (chat + Whisper), Anthropic, and optionally Google Gemini via `google-generativeai`. No third-party LLM wrappers.

---

## 4. Blockers for Being “#1” (Competitive Edge)

1. **Reliability**
   - Single backend, single DB; no health checks in UI, no graceful degradation when API is down.
   - Need: health checks, retries, and “AI temporarily unavailable” messaging.

2. **Speed / UX**
   - Perceived speed depends on LLM latency; no streaming UI for “thinking” or partial code.
   - Need: real streaming, progress phases, and optional “fast mode” (e.g. smaller model).

3. **Quality of generated code**
   - No automated quality gate (lint, tests, a11y) before “done.”
   - Need: validate-and-fix in the main flow, optional security/a11y checks, and “confidence” or score.

4. **Discoverability and retention**
   - Templates and prompt library exist but aren’t highlighted on landing or first workspace load.
   - Need: onboarding, “Try these” prompts, and saved projects front and center.

5. **Collaboration and sharing**
   - Share link is read-only; no real-time collab or comments.
   - Need: share with edit permission, optional presence/comments.

6. **Production deployment**
   - Deploy is “download ZIP” for Vercel/Netlify; no one-click deploy or live URL in product.
   - Need: one-click deploy and stable “live app” URL.

7. **Pricing and limits**
   - Token bundles and paywall exist; no clear pricing page or usage dashboard.
   - Need: public pricing, usage trends, and predictable limits.

8. **Trust and compliance**
   - No explicit terms, privacy, or data handling.
   - Need: privacy policy, terms of use, and clarity on data retention (chat, code, logs).

9. **Mobile and accessibility**
   - No mobile-specific flow or a11y audit in UI.
   - Need: mobile preview, keyboard/screen-reader support, and a11y report in workspace.

10. **Observability**
    - Logs and errors are server-side; no client-side error reporting or funnel metrics.
    - Need: client errors to backend or 3rd party, and key funnel events (signup, first build, first deploy).

---

## 5. Master Lists

### 5.1 Implemented Features (Working or UI-Ready)
- Landing page with prompt and suggestions  
- Auth (register, login, JWT, protected routes)  
- Workspace: Monaco editor, Sandpack preview, file tree, tabs  
- Chat: text prompt, build, modify, streaming simulation  
- Model selector (Auto, GPT-4o, Claude, Gemini)  
- Auto level (Quick / Balanced / Deep)  
- Voice input (record → transcribe)  
- File attachments (images, PDF, text)  
- Image-to-code endpoint and flow  
- Export (download files), GitHub ZIP, Deploy ZIP  
- Auto-fix button (on error)  
- Validate-and-fix endpoint  
- Token balance, paywall banner, Token Center  
- Stripe checkout + webhook (when keys set)  
- Build phases API and phase label in workspace  
- Command palette (Ctrl+K)  
- Menu bar (File, Edit, Selection, View, Go, Run, Terminal, Help)  
- Agents panel (activity from history)  
- Review tab (N files, Undo All, Keep All)  
- Status bar (project, version, errors, tokens)  
- File search (Ctrl+P), New Agent (Ctrl+Shift+L)  
- Prompt Library (templates, saved, recent)  
- Templates gallery, from-template, save-as-template  
- Share (create link, view by token)  
- Duplicate project  
- Env panel (workspace env vars)  
- Learn panel, Shortcut cheat sheet  
- Add payments (Stripe) wizard  
- Explain error, suggest next, inject Stripe, reference build (backend)  
- Security scan, optimize, a11y check, design-from-url (backend)  
- Dashboard, Projects, Exports, Patterns, Settings  
- All Emergent branding removed; CrucibAI title and meta  

### 5.2 Partially Implemented / Needs Wiring
- @ and / in chat (placeholder only; no real parsing)  
- Validate-and-fix (backend only; no “Validate” button in UI)  
- Security scan / a11y (endpoints only; no workspace buttons)  
- Suggest-next (backend only; no “What next?” in UI)  
- Design-from-URL (backend only; no UI input)  
- Thought/planning blocks in chat (no explicit “plan” step in UI)  
- Split editor (state exists; no second pane)  
- Mobile preview toggle (not implemented)  

### 5.3 Not Implemented / Missing
- Real-time collaboration  
- One-click deploy with live URL  
- Public pricing page and usage dashboard  
- Terms of use and privacy policy  
- Client-side error reporting and funnel analytics  
- Demo mode (offline/canned responses)  
- Multi-file generation (beyond App.js)  
- Inline “Explain error” in editor  
- Cached template code (no LLM for known templates)  

### 5.4 Blocking Issues (Must Fix to “Work”)
1. Configure `OPENAI_API_KEY` (required for chat and voice transcription) and/or `ANTHROPIC_API_KEY`, optionally `GEMINI_API_KEY` or `GOOGLE_API_KEY`.  
2. Configure MongoDB (`MONGO_URL`, `DB_NAME`).  
3. No third-party LLM package required; backend uses OpenAI, Anthropic, and Gemini SDKs directly.  
4. Ensure frontend build succeeds (`npm run start`) and backend runs (e.g. `uvicorn server:app`).  
5. Set CORS and (if needed) Stripe for production payments.  

### 5.5 Top 10 to Move Toward “#1”
1. Real streaming from LLM and “thinking” / progress in UI.  
2. Validate-and-fix and optional security/a11y in the main build flow.  
3. One-click deploy with a stable live app URL.  
4. Health checks and “AI unavailable” handling.  
5. Onboarding + “Try these” prompts and better template discovery.  
6. Public pricing and usage dashboard.  
7. Privacy policy and terms of use.  
8. Multi-file generation (at least one extra component or CSS file).  
9. Mobile preview and a11y report in workspace.  
10. Client-side error reporting and funnel metrics.  

---

*End of audit. All changes saved.*
