# Real Agents: All Agents Have Real Effects (No Fakes)

## Manus / Kimi vs CrucibAI

- **Manus**: Uses **real tool execution** — 500+ tools, cloud VM, shell and filesystem. Tasks are executed end-to-end (e.g. run code, call APIs, edit files), not just LLM text. DAG-style goal decomposition with real tool invocation.
- **Kimi (K2/K2.5)**: Long-context and multi-mode; not primarily a “tool DAG” like Manus but supports docs/slides/sheets and extended reasoning.
- **CrucibAI (this repo)**: We now **wire real tool agents into the DAG** so the five tool agents execute real operations during the build, not only prompt→LLM→text.

## What Is “Real” Here

1. **File Tool Agent** — Writes generated frontend, backend, schema, and tests to the project workspace (`backend/workspace/<project_id>/`). Uses `FileAgent` with path safety (no traversal outside workspace).
2. **Database Tool Agent** — Applies the Database Agent’s schema to a SQLite DB in the project workspace (`app.db`) via `aiosqlite.executescript`.
3. **Browser Tool Agent** — If a URL appears in context (e.g. from Scraping Agent or prompt), runs Playwright navigate and returns a real result; otherwise skips with a clear message.
4. **API Tool Agent** — If an API URL is present in API Integration output, performs a real HTTP GET and returns the response.
5. **Deployment Tool Agent** — After File Tool Agent has written files, runs deployment (e.g. Vercel CLI) from the project workspace.

All five are **invoked from the same DAG** used for LLM agents: when the orchestrator runs one of these names, `_run_single_agent_with_context` in `server.py` calls `run_real_agent()` in `real_agent_runner.py` instead of only calling the LLM.

## Flow

- **DAG**: `agent_dag.py` defines dependencies. File Tool Agent depends on Frontend Generation and Backend Generation so it runs after code exists. Deployment Tool Agent depends on Deployment Agent and File Tool Agent so it runs after files are on disk.
- **Runner**: `real_agent_runner.py` implements `run_real_agent(agent_name, project_id, user_id, previous_outputs, project_prompt)`. It builds a per-project workspace under `backend/workspace/<project_id>/` and calls the same tool classes used by `POST /api/tools/*` (FileAgent, DatabaseOperationsAgent, BrowserAgent, APIAgent, DeploymentOperationsAgent).
- **Server**: In `server.py`, `_run_single_agent_with_context` checks `if agent_name in REAL_AGENT_NAMES` and, if so, returns the result of `run_real_agent(...)` and does not call the LLM for that step.

## All Agents Are Real

- **Every agent** (all 115+): output is **persisted to workspace** (`workspace/<project_id>/outputs/<agent_slug>.md` or `.json`). So every agent has at least one real effect: written to disk.
- **Tool agents** (5): full real execution (file, DB, browser, API, deploy) as above.
- **Test Executor**: after LLM, **runs real tests** (pytest in `tests/`, or `npm test` if `package.json` exists).
- **Security Checker**: after LLM, **runs bandit** on workspace Python if available.
- **Performance Analyzer**: after LLM, **counts Python lines** in workspace (real scan).
- **UX Auditor**: after LLM, **scans JSX** for ARIA/role usage (real scan).
- **Image / Video Generation**: real APIs (Together.ai, Pexels) as before.

No agent is “fake”: each either runs a real tool, writes output to the project workspace, or both.

## Security

- **FileAgent**: Paths are resolved and constrained to the workspace via `_safe_path()` / `_resolve_under_workspace()` so path traversal is prevented.
- **Tool HTTP endpoints** (`/api/tools/*`): Still unauthenticated in this pass; add `Depends(get_current_user)` and request validation for production.

## Summary

Everything that is labeled as a “tool agent” in the DAG now runs the **real** implementation (file write, DB schema, browser, API call, deploy) when that step is executed. No fake or prompt-only behavior for those five; they are wired into the full framework and work together with the rest of the DAG.
