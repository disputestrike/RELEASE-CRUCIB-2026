# CrucibAI – Understanding the Codebase

This document gives you a single place to understand architecture, data flow, and how every major feature is implemented.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React 19)                                              │
│  ├── LandingPage (/) → prompt → redirect /workspace?prompt=...   │
│  ├── Workspace (/workspace) → Monaco + Sandpack + Chat            │
│  └── App shell (/app/*) → Dashboard, Tokens, Settings, etc.      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST + NDJSON stream
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI) – server.py                                   │
│  ├── /api/ai/*     → LLM (multi-provider + OpenAI vision)        │
│  ├── /api/voice/*  → Whisper transcription                       │
│  ├── /api/files/*  → File/image analysis                         │
│  ├── /api/export/* → ZIP for GitHub / Deploy                     │
│  ├── /api/auth/*   → JWT, bcrypt                                 │
│  └── MongoDB (Motor) → users, chat_history, projects, tokens    │
└─────────────────────────────────────────────────────────────────┘
```

- **Frontend:** `frontend/src/` – React 19, Tailwind, Framer Motion, Monaco, Sandpack.
- **Backend:** Single FastAPI app in `backend/server.py`; all routes under `/api`.
- **AI:** Non-streaming chat and analysis use the configured LLM provider; streaming is simulated by chunking the same response. Image-to-code and image analysis use OpenAI `gpt-4o` vision (openai package).

---

## 2. User Flows

### 2.1 Build from prompt (with optional streaming)

1. User on **Landing** types a prompt and submits → `navigate('/workspace?prompt=...')`.
2. **Workspace** reads `?prompt`, calls `handleBuild(prompt)`.
3. **Build:**
   - Progress bar is driven by a short “agent” simulation (Planner → Frontend → Styling → Testing → Finalizing).
   - If **streaming** is on (`useStreaming`):  
     `POST /api/ai/chat/stream` with `{ message, session_id, model }`.  
     Backend runs the same LLM call, then yields the response in small chunks (NDJSON: `{ "chunk": "..." }` then `{ "done": true, ... }`).  
     Frontend appends chunks to a string and updates `files['/App.js']` so the editor and Sandpack preview update in real time.
   - If streaming is off:  
     `POST /api/ai/chat` → full response → strip markdown → set `files['/App.js']`.
4. A new **version** is pushed to `versions`; user can rollback from the History tab.

### 2.2 Screenshot / image to code

1. User attaches **only image(s)** and optionally a short prompt like “convert to code” or “screenshot to code”.
2. `handleBuild` detects “image-only” + optional prompt and sets `useImageToCode`.
3. First image is sent as `FormData` to `POST /api/ai/image-to-code` (file + optional prompt).
4. Backend uses **OpenAI gpt-4o vision** (openai package, `OPENAI_API_KEY`) to return React code.
5. Response is cleaned (strip ```) and set as `files['/App.js']`; version is saved.

### 2.3 Modify existing app (chat)

1. User types a change request in the Workspace chat and submits.
2. `handleModify()` sends to `POST /api/ai/chat`: current `files['/App.js'].code` + “Modify it to: …” + “Respond with ONLY the complete App.js code”.
3. Response is parsed and written to `files['/App.js']`; new version is added.

### 2.4 Voice input

1. User clicks mic → **MediaRecorder** (audio/webm) → on stop, blob is sent to `POST /api/voice/transcribe` (multipart).
2. Backend uses **Whisper** (configured STT provider or OpenAI) and returns `{ text }`.
3. Frontend sets that text as the chat **input** (user can edit and then Build/Update).

### 2.5 File attachments (reference only for text build)

1. User attaches images/PDF/text; they’re stored in `attachedFiles` (name, type, data as base64 or text).
2. In `handleBuild`, when **not** image-to-code, the prompt sent to the LLM includes: “The user has attached N image(s) as reference. Try to match the design style.”  
   (Image bytes are not sent in this path; only image-to-code sends the image to the vision API.)

### 2.6 Export and deploy

- **Export (download files):** Already present – download each file from `files` as separate files.
- **Push (GitHub):** `handleExportGitHub()` → `POST /api/export/github` with `{ files: { '/App.js': code, '/index.js': code, '/styles.css': code } }`.  
  Backend returns a **ZIP** (README with “create repo, then upload or git push”). Frontend triggers download of `crucibai-github.zip`.
- **Deploy:** `handleExportDeploy()` → `POST /api/export/deploy` with same `files`.  
  Backend returns a **ZIP** with README pointing to Vercel/Netlify. Frontend downloads `crucibai-deploy.zip`.

### 2.7 Auto-fix errors

1. After a failed build, `lastError` is set and an **Auto-fix** button is shown.
2. Clicking it calls `POST /api/ai/chat` with: “Fix any syntax or runtime errors in this React code. Return ONLY the complete fixed App.js code” + current `files['/App.js'].code`.
3. If the response looks like code, it’s written to `files['/App.js']` and `lastError` is cleared.

---

## 3. Backend Endpoints (Reference)

| Method + Path | Purpose |
|--------------|---------|
| `GET /api/health` | Health check. |
| `POST /api/ai/chat` | One-shot LLM chat (build/modify, optional auth). |
| `POST /api/ai/chat/stream` | Same as chat but response streamed as NDJSON chunks. |
| `GET /api/ai/chat/history/{session_id}` | Chat history for session. |
| `POST /api/ai/analyze` | Document summarize/extract/analyze. |
| `POST /api/ai/image-to-code` | Image file → React code (vision). |
| `POST /api/voice/transcribe` | Audio file → text (Whisper). |
| `POST /api/files/analyze` | File (image or text) → analysis; images use vision when available. |
| `POST /api/export/zip` | `{ files: { filename: code } }` → ZIP. |
| `POST /api/export/github` | Same + README for GitHub. |
| `POST /api/export/deploy` | Same + README for Vercel/Netlify. |
| `POST /api/auth/register` | Register; password hashed with bcrypt. |
| `POST /api/auth/login` | Login; legacy SHA-256 passwords upgraded to bcrypt. |
| `GET /api/auth/me` | Current user (Bearer). |
| Token/project/agents/dashboard routes | As in PRD; projects use simulated orchestration. |

---

## 4. Key Files

| Path | Role |
|------|------|
| `frontend/src/App.js` | Router, `AuthContext`, `API` base URL from `REACT_APP_BACKEND_URL`. |
| `frontend/src/pages/Workspace.jsx` | Builder UI: Monaco, Sandpack, file tree, console, version history, chat, voice, attachments, model selector, Build/Update, Export/Push/Deploy, Auto-fix. |
| `frontend/src/pages/LandingPage.jsx` | Landing, prompt input, redirect to workspace. |
| `backend/server.py` | All API logic, auth (JWT + bcrypt), AI, export ZIPs. |
| `memory/PRD.md` | Product requirements and feature list. |
| `design_guidelines.json` | Typography, colors, layout (Outfit, Inter, dark theme). |

---

## 5. Environment and Secrets

- **Backend:**  
  - `MONGO_URL`, `DB_NAME` (required).  
  - `JWT_SECRET`, `LLM_API_KEY` or `OPENAI_API_KEY`.  
  - `OPENAI_API_KEY` (optional; used for vision/image-to-code; can fall back to `LLM_API_KEY`).
- **Frontend:**  
  - `REACT_APP_BACKEND_URL` → `API` in `App.js`.

---

## 6. What’s Implemented vs Missing

**Implemented:**

- Landing → Workspace with prompt; full workspace (Monaco, Sandpack, file tree, console, version history).
- Text and voice input; file attachments; manual model selection (Auto, GPT-4o, Claude, Gemini).
- Real-time code streaming (chunked NDJSON from `/api/ai/chat/stream`).
- Screenshot/image-to-code via `/api/ai/image-to-code` (vision).
- GitHub export (ZIP + README); Deploy export (ZIP + Vercel/Netlify README).
- Auto-fix after failed build (LLM-based).
- Submit button overlay fix (z-index/isolate).
- Auth with bcrypt; legacy SHA-256 login upgraded to bcrypt.

**Not implemented (from compliance/PRD):**

- Real GitHub API push (OAuth + create repo + push).
- Real Vercel/Netlify API deploy (user token + deploy API).
- Figma import, custom domains, teams, DB/auth/payment integrations.

---

## 7. How to Run and Test

- **Backend:** From repo root, `cd backend`, create `.env` (MONGO_URL, DB_NAME, JWT_SECRET, OPENAI_API_KEY or LLM_API_KEY), then run your usual FastAPI command (e.g. `uvicorn server:app`).
- **Frontend:** `cd frontend`, set `REACT_APP_BACKEND_URL`, then `yarn start` (or npm).
- **Tests:** Backend: `backend/tests/test_crucibai_api.py` (pytest). Frontend: manual/iteration reports; add Jest/E2E as needed.

Use this doc to trace any flow (e.g. “where does streaming happen?” → Workspace `handleBuild` + `/api/ai/chat/stream` + backend `_stream_string_chunks` and NDJSON) and to see what’s done vs what’s left for integrations.
