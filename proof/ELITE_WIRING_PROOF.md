# Elite wiring — file and execution-path evidence

This document ties the **elite execution directive** to concrete code paths (not only `proof/ELITE_EXECUTION_DIRECTIVE.md` on disk).

## 1. Resolution and job attachment

| Item | Location |
|------|----------|
| Load order | `backend/orchestration/execution_authority.py` — `resolve_elite_execution_text()` reads `proof/ELITE_EXECUTION_DIRECTIVE.md` first, else `load_elite_autonomous_prompt()`; disabled when `CRUCIBAI_ELITE_SYSTEM_PROMPT` ∈ `{0,false,no,off}` |
| Job mutation | `attach_elite_context_to_job()` stores `_elite_execution_context` (active, source, sha16, excerpt) |
| Model fragment | `elite_context_for_model(job)` → block with `sha16=`, rules, excerpt |
| Run start event | `backend/orchestration/auto_runner.py` — after `job_started`, `append_job_event(..., "execution_authority", {"kind": "execution_authority.json", **elite_job_metadata(job)})` |

## 2. Every step: executor

| Item | Location |
|------|----------|
| Per-step attach | `backend/orchestration/executor.py` — `execute_step()` calls `attach_elite_context_to_job(job, workspace_path)` before handlers |
| Verifier sees goal | `verification_input` includes `job_goal` and `job_id` for gates that depend on goal text |

## 3. Planning / crew path (software generation sketch)

| Item | Location |
|------|----------|
| Combined system prompt | `handle_planning_step` for `planning.requirements`: `attach_elite_context_to_job`, `load_elite_autonomous_prompt()` + `elite_context_for_model(job)` → `job["elite_system_prompt"]`, passed to `run_crew_for_goal(..., system_prompt=combined)` |
| Crew kickoff | `backend/orchestration/agent_orchestrator.py` — `run_crew_for_goal` sets both `system_prompt` and `elite_system_prompt` on kickoff inputs |
| `Agent.execute` | Same file — reads `context["elite_system_prompt"]` or `context["system_prompt"]`, includes first 900 chars in returned `content` as **Execution authority digest** (proves payload reached the agent entrypoint) |

## 4. What is not wired here

The **Auto-Runner `Agent` class is still a stub** (no HTTP call to an LLM). Wiring ensures the **same string** that would be sent as a system appendage is present on the execution entrypoint and in job metadata. Replacing `Agent.execute` with a real `call_llm(system_prompt=...)` should consume the same `elite_system_prompt` / combined `system_prompt` keys.

## 5. Tests proving non-decorative behavior

| Test | File |
|------|------|
| Workspace resolution, attach, model block, hash | `test_execution_authority_wiring.py` |
| Env-off → empty model block | `test_attach_elite_inactive_injects_empty_model_block` |
| Crew → digest contains directive marker | `test_run_crew_system_prompt_reaches_agent_execute_digest` |

**Command:** `python -m pytest tests/test_execution_authority_wiring.py tests/test_agent_orchestrator.py -q` (run from `backend/`).
