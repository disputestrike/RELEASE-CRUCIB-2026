# Full Line-by-Line Code Review — CrucibAI

**Scope:** Entire codebase. Agents (real vs prompt-only), security (auth, validation, SSRF, injection), backend critical paths, frontend safety.  
**No doc update:** This is the review only; RATE_RANK_TOP50.md and other docs are unchanged.

---

## 1. Why “Real” Agents vs “Prompt-Only” — What’s Actually Implemented

### 1.1 Architecture

- **`agent_dag.py`** defines 115+ agents. Each has a `system_prompt` and `depends_on`. They are **all** prompt-only in the build flow: the orchestration calls the LLM with that system prompt and previous outputs. There is **no** code path that runs “Browser Tool Agent” by calling `BrowserAgent.execute()` during a build.
- **`orchestration.py`** defines a smaller set (~30 agents) and `run_orchestration_with_dag`; every agent there is run via `_run_single_agent_with_context` → `_call_llm_with_fallback`. Again, **no** tool execution.
- **`server.run_orchestration_v2`** uses `agent_dag.get_execution_phases(AGENT_DAG)` and for each agent calls `_run_single_agent_with_context`, which does:
  - `system_msg = get_system_prompt_for_agent(agent_name)` (from DAG)
  - `response, _ = await _call_llm_with_fallback(...)`  
  So **every DAG agent in the build is LLM-only**. The only exceptions are:
  - **Image Generation:** LLM output is parsed and `generate_images_for_app` (Together.ai) is called.
  - **Video Generation:** LLM output is parsed and `generate_videos_for_app` (Pexels) is called.

- The **five “real” tool agents** (Browser, File, API, Database, Deployment) are **only** used at:
  - `POST /api/tools/browser`
  - `POST /api/tools/file`
  - `POST /api/tools/api`
  - `POST /api/tools/database`
  - `POST /api/tools/deploy`  
  They are **never** invoked from `run_orchestration_v2` or `run_orchestration_with_dag`. So:
  - In the DAG, “Browser Tool Agent”, “File Tool Agent”, etc. are **prompt-only**: the LLM is asked to “output action plan or results” and returns text.
  - The **executable** implementations live only in `backend/tools/*.py` and are used only when someone calls the `/api/tools/*` endpoints.

**Conclusion:** “Real” implementation exists only for the 5 tool agents (and image/video via external APIs). Everything else in the 115-agent DAG is prompt → LLM → text. Going “full full complete” would mean either: (a) wiring the tool agents into the build (e.g. when DAG runs “Browser Tool Agent”, call `BrowserAgent.execute()` with parsed params), or (b) implementing more “real” agents (e.g. Test Executor actually running tests, Deployment Agent actually calling deploy APIs) instead of only LLM output.

---

## 2. Security — What Was Done vs What’s Missing

### 2.1 What Exists

- **Auth:** JWT with `HTTPBearer`, `get_current_user` / `get_optional_user`; MFA (pyotp, backup codes); password strength in `validators.py` and server.
- **Middleware:** `RateLimitMiddleware`, `SecurityHeadersMiddleware`, `RequestTrackerMiddleware`, `RequestValidationMiddleware` (body size, suspicious headers), `PerformanceMonitoringMiddleware`. Security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS, CSP, Referrer-Policy, Permissions-Policy.
- **Error handling:** `error_handlers.py` with CrucibError, ValidationError, AuthenticationError, etc., and `to_http_exception`.
- **Validation:** Pydantic validators for register, login, chat, project create, build plan, file upload; `validate_password_strength`, `sanitize_string`, `validate_pagination`, etc.
- **Security audit:** `security_audit.py` (env vars, hardcoded secrets scan, auth checklist, dependency guidance). It does **not** call the tool endpoints or enforce SSRF/path-traversal fixes.
- **Frontend:** `sanitization.js` (sanitizeHTML, escapeHTML, sanitizeURL, validatePassword, CSRF token helpers).

### 2.2 Critical Gaps

#### A. Tool endpoints unauthenticated and unvalidated

- **Location:** `server.py` lines 4293–4326.
- **Issue:** `POST /api/tools/browser`, `/api/tools/file`, `/api/tools/api`, `/api/tools/database`, `/api/tools/deploy` take `request: dict` with **no** `Depends(get_current_user)` (or any auth) and **no** Pydantic schema. Any caller can send arbitrary JSON and run:
  - Browser: navigate to any URL, screenshot, scrape.
  - File: read/write/delete/list under `./workspace`.
  - API: HTTP requests to any URL (SSRF).
  - Database: run arbitrary SQL with provided connection info.
  - Deploy: run Vercel/Railway/Netlify CLI with arbitrary `project_path`.
- **Fix:** Add `user: dict = Depends(get_current_user)` (or at least `get_optional_user` and then require auth for sensitive tools). Add Pydantic request bodies and validate all inputs (path, url, query, etc.).

#### B. FileAgent — path traversal

- **Location:** `backend/tools/file_agent.py`.
- **Issue:** `filepath = self.workspace / context.get("path")`. No resolution or check that the result stays under `self.workspace`. A path like `../../etc/passwd` can escape.
- **Fix:** Resolve with `Path.resolve()`, then assert `resolved.is_relative_to(self.workspace.resolve())` (or equivalent). Reject `..` and absolute paths outside workspace.

#### C. BrowserAgent — path traversal and SSRF

- **Location:** `backend/tools/browser_agent.py`.
- **Issue 1:** `screenshot_path` is used in `self.page.screenshot(path=path)` and then `open(path, 'rb')`. Path is not restricted; can write/read outside workspace.
- **Issue 2:** `url = context.get("url")` — browser navigates to user-controlled URL (SSRF: internal networks, cloud metadata, etc.).
- **Fix:** Restrict screenshot path to a temp dir or workspace; validate/normalize and restrict URLs (e.g. block private IPs, file:, localhost, or allowlist).

#### D. APIAgent — SSRF

- **Location:** `backend/tools/api_agent.py`.
- **Issue:** Comment says “URL allowlisting or blocklisting” and “block internal networks” but no code does it. User-provided `url` is passed to `httpx` as-is.
- **Fix:** Implement URL validation: block private IPs (127.0.0.0/8, 10.0.0.0/8, 169.254.0.0/16, etc.), block `file:` and `localhost`; optionally allowlist hostnames or schemes.

#### E. DatabaseOperationsAgent — arbitrary SQL and connection

- **Location:** `backend/tools/database_operations_agent.py`.
- **Issue:** Accepts arbitrary `query` and `connection`. Parameterized execution is used, but the **query string** itself is user-controlled (e.g. multiple statements, dangerous ops). Connection params (host, user, password) are user-controlled — so anyone with access to the endpoint can run SQL against any reachable DB.
- **Fix:** Restrict to a single app-controlled DB (or per-user sandbox). Restrict query type (e.g. read-only for arbitrary callers). Do not accept full connection dict from client in production.

#### F. DeploymentOperationsAgent — path and command safety

- **Location:** `backend/tools/deployment_operations_agent.py`.
- **Issue:** `project_path = context.get("project_path")` passed to `subprocess.run(cmd, cwd=project_path, ...)`. Path not validated; can point outside intended dir. CLI tools may interpret options from path if not careful.
- **Fix:** Validate and resolve `project_path`; ensure it is under an allowed base path (e.g. user workspace). Use list form of `subprocess.run` (already used) and avoid shell=True.

#### G. JWT_SECRET / logger order (fixed in this pass)

- **Location:** `server.py` (previously lines 109–114).
- **Issue:** `logger.warning(...)` was called before `logger = logging.getLogger(__name__)`, causing NameError when `JWT_SECRET` was unset.
- **Fix applied:** Logger is defined before the JWT_SECRET block so the warning runs correctly.

#### H. CORS

- **Location:** `server.py` app middleware: `allow_origins=os.environ.get("CORS_ORIGINS", "*").split(",")`.
- **Issue:** Default `*` with `allow_credentials=True` is invalid and can be ignored by browsers; in any case, wide-open CORS is unsafe for production.
- **Fix:** Set `CORS_ORIGINS` to explicit origins in production; avoid `*` when credentials are used.

### 2.3 Frontend

- **AdminAnalytics.jsx** (e.g. line 138): `win.document.write(html)` — if `html` is ever user-controlled or includes unsanitized data, this is XSS. Prefer safe rendering (e.g. React or sanitized HTML).
- **sanitization.js** is present and used in places; ensure all user-derived content rendered in the app goes through it (or equivalent) and that `document.write` is not used with dynamic content.

---

## 3. Backend Critical Paths — Line-by-Line Notes

### 3.1 server.py

- **Imports and app setup:** Correct use of middleware order; error_handlers and validators imported.
- **JWT:** Now safe: logger defined before JWT_SECRET fallback. Env fallback is per-process; document that tokens invalidate on restart if JWT_SECRET is not set.
- **Auth:** `get_current_user` decodes JWT and loads user from DB; `get_optional_user` returns None if no/invalid token. Used consistently on protected routes; **not** used on `/api/tools/*`.
- **Orchestration:** `run_orchestration_v2` uses `get_execution_phases(AGENT_DAG)`, then for each agent only `_run_single_agent_with_context` → `_call_llm_with_fallback`. No branching to tool agents.
- **Tool routes (4293–4326):** As above — no auth, no schema, raw `request: dict` passed to each tool agent’s `run()`.

### 3.2 orchestration.py

- All agents in `ORCHESTRATION_AGENTS_CONFIG` and `PARALLEL_PHASES` are run via `_run_single_agent_with_context` (in server) / `call_llm` (here). No tool execution.

### 3.3 agent_dag.py

- Single source of agent definitions; 115+ entries. “Browser Tool Agent”, “File Tool Agent”, etc. have only `system_prompt`; they are not wired to `tools.browser_agent.BrowserAgent` or others in the build pipeline.

### 3.4 tools/*.py

- **base_agent.py:** Abstract `execute()`, `run()` wraps with try/except. Fine.
- **file_agent.py:** Path traversal as above; no schema on `context`.
- **browser_agent.py:** Path and URL issues as above.
- **api_agent.py:** SSRF as above; no timeout or size limits on response.
- **database_operations_agent.py:** Arbitrary SQL and connection as above.
- **deployment_operations_agent.py:** Path and subprocess as above.

### 3.5 middleware.py

- Rate limit uses Bearer token or IP; SecurityHeadersMiddleware sets headers; RequestValidationMiddleware checks body size and suspicious headers. None of these validate or protect the **body** of `/api/tools/*`; they only run before the route handler.

### 3.6 error_handlers.py / validators.py

- Structured errors and validators are in place. Tool endpoints do not use them because they don’t use Pydantic bodies or auth dependencies.

---

## 4. What “Full Security” Would Require (No Shortcuts)

1. **Auth on tools:** Require `Depends(get_current_user)` (or strict optional) on all `/api/tools/*` and validate scope (e.g. project_id or workspace) where relevant.
2. **Request schemas for tools:** Pydantic models for each tool (action, path, url, query, connection, project_path, etc.) with max lengths and allowlists/blocklists.
3. **FileAgent:** Resolve path and enforce containment under workspace; reject `..` and absolute outside.
4. **BrowserAgent:** Restrict screenshot path; restrict URL (no private IPs, no file:, optional allowlist).
5. **APIAgent:** Block internal IPs and dangerous schemes; optional allowlist; timeouts and response size limits.
6. **DatabaseOperationsAgent:** Do not accept full connection from client; use app-controlled or per-user DB; restrict to read-only or allowlist of operations if needed.
7. **DeploymentOperationsAgent:** Validate and confine `project_path` to an allowed base; no shell, list-only subprocess.
8. **CORS:** Explicit origins in production; no `*` with credentials.
9. **Frontend:** Remove or isolate `document.write(html)`; ensure all dynamic content is sanitized.

---

## 5. Why This State Exists (Limits and Priorities)

- **“Why only prompt for most agents?”** The design is “DAG of LLM agents” that produce text/code; the 5 tool agents were added as **separate** capabilities (Manus-style tools) and were not integrated into the build DAG. So the build is still “orchestrate 115 prompt agents”; the tools are an extra API surface.
- **“Why didn’t you go all the security?”** The security_audit module and middleware focus on env, secrets, headers, and generic auth. The **tool endpoints** were added without applying the same auth and validation patterns used elsewhere (e.g. no Depends, no Pydantic on body). So the gap is inconsistent application of existing patterns to the new routes, not absence of security tooling.
- **“Are you limited?”** This review is a full pass over the repo: agents (real vs prompt), auth, validation, SSRF, path traversal, SQL/connection, deployment path, CORS, and frontend XSS. The limitations are in the **codebase** (tool routes and tool implementations), not in the depth of review.

Going forward, “full full complete everything” means: (1) wire real tool execution into the DAG where intended, and (2) apply the full security checklist above to every tool endpoint and tool implementation, line by line.
