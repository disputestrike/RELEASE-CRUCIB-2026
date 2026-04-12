# CrucibAI Agent System Guide

## Overview

CrucibAI uses **20 specialized AI agents** that run in **parallel phases** (DAG) to generate production-ready code. Each agent has a clear role, dependencies, and error-handling behavior.

---

## Agent Phases (DAG)

Agents are grouped into **phases**. Within a phase, agents run **in parallel**; between phases, they run in order so that later agents can use earlier agents’ outputs.

### Phase 1: Planning
- **Planner** – Decomposes your request into 3–7 executable tasks.
- **Requirements Clarifier** – Asks clarifying questions.
- **Stack Selector** – Recommends tech stack (frontend, backend, DB).

### Phase 2: Code Generation (parallel)
- **Frontend Generation** – React/JSX UI code.
- **Backend Generation** – FastAPI/Express backend code.
- **Database Agent** – Schema and migrations.

### Phase 3: Integration & Tests (parallel)
- **API Integration** – Code that calls external APIs.
- **Test Generation** – Unit/integration tests.
- **Image Generation** – Image prompt for assets.

### Phase 4: Quality
- **Security Checker** – Security checklist (PASS/FAIL).
- **Test Executor** – Test command and checks.
- **UX Auditor** – Accessibility/UX checklist.
- **Performance Analyzer** – Performance tips.

### Phase 5: Deployment & Extras
- **Deployment Agent** – Deploy instructions.
- **Error Recovery** – Failure points and recovery.
- **Memory Agent** – Short project summary for reuse.
- **PDF Export**, **Excel Export**, **Scraping Agent**, **Automation Agent** – Export and automation suggestions.

---

## Output Chaining

Later agents receive **context** from earlier agents:

- **Planner** output → used by Requirements Clarifier and Stack Selector.
- **Stack Selector** output → used by Frontend/Backend/Database generation.
- **Frontend** and **Backend** code (excerpts) → used by Security Checker and Test Generation.

Context is truncated (e.g. 2000 chars per output) to stay within token limits.

---

## When Agents Fail

1. **Retry** – Each agent is retried up to 3 times with exponential backoff.
2. **Criticality** – If a **critical** agent (e.g. Planner, Stack Selector) fails after retries, the **build stops**.
3. **High** – If a high-priority agent fails, the build **continues with fallback** (e.g. default template).
4. **Low/Medium** – Optional agents are **skipped** on failure; build continues.

See `agent_resilience.py` for `AGENT_CRITICALITY`, `AGENT_ERROR_MESSAGES`, and `generate_fallback()`.

---

## Timeouts

Each agent has a timeout (e.g. 120–180 seconds for code generation). If the LLM call exceeds it, the agent is treated as failed and criticality/fallback rules apply.

---

## Monitoring Your Build

- **AgentMonitor** (`/app/projects/:id`) – Shows status per agent, logs, and **BuildProgress** (real-time phase progress when status is “running”).
- **WebSocket** – `ws://<backend>/ws/projects/<project_id>/progress` streams `phase`, `progress`, `tokens_used`.

---

## Quality Score

After a completed build, the project gets a **quality_score** (0–100) with breakdown for frontend, backend, database, and tests. See `code_quality.score_generated_code()` and the **QualityScore** component in the UI.

---

## Token Optimization

To reduce tokens per build (~20K → ~10–12K), CrucibAI supports **short system prompts**:

- Set **`USE_TOKEN_OPTIMIZED_PROMPTS=1`** in the backend environment (or in Settings/workspace env).
- When set, agents use concise one-line instructions instead of longer prompts, with minimal quality loss.
- Context from previous agents is still truncated to `CONTEXT_MAX_CHARS` (default 1200 when optimized) to avoid token overflow.

See `backend/agent_dag.py`: `get_system_prompt_for_agent()` and `OPTIMIZED_SYSTEM_PROMPTS`.

---

## Testing

| Test file | What it covers |
|-----------|----------------|
| `backend/tests/test_agent_dag.py` | DAG structure, topological sort, execution phases, context building |
| `backend/tests/test_agent_resilience.py` | Criticality, timeouts, fallbacks, `AGENT_ERROR_MESSAGES` |
| `backend/tests/test_orchestration_e2e.py` | Full build with mocked LLM, quality score after build, failure recovery (fallback/skip) |

Run all backend tests (backend running optional for contract/smoke). Use `python -m pytest` so the backend is on the path:

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

Run only orchestration E2E (no API keys needed; mocks LLM):

```bash
cd backend
python -m pytest tests/test_orchestration_e2e.py -v
```

---

## Error Recovery (detail)

| Criticality | Agents (examples) | On failure after retries |
|-------------|--------------------|---------------------------|
| **critical** | Planner, Stack Selector | Build **stops**; project status = failed |
| **high** | Frontend Generation, Backend Generation, Database Agent | Build **continues** with fallback template |
| **medium** | API Integration, Test Generation, Security Checker, etc. | Agent **skipped**; build continues |
| **low** | Image Generation, UX Auditor, Performance Analyzer, PDF/Excel Export, etc. | Agent **skipped**; build continues |

User-facing messages for timeout/empty output: `agent_resilience.get_error_message(agent_name, error_code)`.

---

## Files

| File | Purpose |
|------|---------|
| `backend/agent_dag.py` | DAG definition, `topological_sort`, `get_execution_phases`, `build_context_from_previous_agents`, optional short prompts |
| `backend/agent_resilience.py` | Criticality, timeouts, fallbacks, `AGENT_ERROR_MESSAGES` |
| `backend/server.py` | `run_orchestration_v2`, WebSocket `/ws/projects/{id}/progress` |
| `backend/code_quality.py` | `score_generated_code` |
| `frontend/src/components/BuildProgress.jsx` | Real-time phase progress UI |
| `backend/tests/test_orchestration_e2e.py` | E2E: full build (mocked LLM), quality score, failure recovery |

---

## Quick reference

| Agent | Criticality | Timeout (s) | Phase |
|-------|--------------|-------------|-------|
| Planner | critical | 120 | 1 |
| Requirements Clarifier | high | 90 | 1 |
| Stack Selector | critical | 60 | 1 |
| Frontend Generation | high | 180 | 2 |
| Backend Generation | high | 180 | 2 |
| Database Agent | high | 90 | 2 |
| API Integration | medium | 90 | 3 |
| Test Generation | medium | 120 | 3 |
| Image Generation | low | 60 | 3 |
| Security Checker | medium | 90 | 4 |
| Test Executor | medium | 60 | 4 |
| UX Auditor | low | 60 | 4 |
| Performance Analyzer | low | 60 | 4 |
| Deployment Agent | medium | 90 | 5 |
| Error Recovery | low | 60 | 5 |
| Memory Agent | low | 45 | 5 |
| PDF Export, Excel Export, Scraping, Automation | low | 45–90 | 5 |
