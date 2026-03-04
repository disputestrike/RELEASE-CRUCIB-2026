# Stack wiring: Database, API, LLM

Everything is wired so that when you have a valid session (guest or login), you can create projects, run builds, and persist data.

## Flow

1. **Session**  
   Frontend gets a token from `POST /api/auth/guest` (or login). It sends `Authorization: Bearer <token>` on all API calls.

2. **Database (Postgres)**  
   Backend uses `db` (db_pg) for:
   - **users** – auth, credits, workspace_mode  
   - **projects** – created projects, status, requirements  
   - **token_ledger** – credits, purchases  
   - **chat_history** – chat sessions  
   - **workspace files** – project file contents (via project storage)

3. **API**  
   Protected routes use `get_current_user` (JWT). Frontend sends the token for:
   - `POST /api/build/plan` – plan from LLM  
   - `POST /api/projects` – create project, deduct credits, start orchestration  
   - `GET /api/projects` – list projects  
   - `GET /api/projects/:id/workspace/files` – workspace files  
   - `POST /api/ai/chat` / `POST /api/ai/chat/stream` – chat with LLM  
   - Voice, validate-and-fix, suggest-next, etc.

4. **LLM**  
   Backend calls LLM for plans and code generation via:
   - `_call_llm_with_fallback` / `_call_anthropic_direct` / Cerebras  
   - Uses **ANTHROPIC_API_KEY** or **CEREBRAS_API_KEY** (env or user API keys in Settings)  
   - Credits are checked and deducted from the user (db) before LLM calls.

## What you need for it to work

| Component   | Requirement |
|------------|-------------|
| **Database** | `DATABASE_URL` set (Postgres). Backend initializes `db` at startup. |
| **Guest session** | Backend must be deployed with `POST /api/auth/guest` so the frontend can get a token. |
| **LLM** | At least one of `ANTHROPIC_API_KEY` or `CEREBRAS_API_KEY` set (or user adds keys in app Settings). |
| **Frontend** | Same origin as API (e.g. Railway single deploy) so `API = '/api'` and requests include credentials. |

If any of these are missing, the chain breaks (e.g. "Could not start session" when guest fails, or 402/503 when credits or LLM keys are missing). Once guest succeeds and keys/credits are set, database, API, and LLM are all connected end-to-end.
