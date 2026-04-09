# Anthropic 404 Fix

## Root Cause

Production still hard-coded retired Anthropic model IDs, especially:

- `claude-3-5-haiku-20241022`
- `claude-3-5-sonnet-20241022`

Anthropic retired `claude-3-5-haiku-20241022` on February 19, 2026, and requests to that model now return an error.

## Fix

- Added centralized model normalization in `backend/anthropic_models.py`
- Replaced live runtime defaults with:
  - `claude-haiku-4-5-20251001`
  - `claude-sonnet-4-6`
- Normalized stale env/config values before Anthropic calls
- Fixed the server's Cerebras helper default so it no longer defaults to an Anthropic model ID

## PASS / FAIL

- Database Agent hard-coded retired model removed: PASS
- Base agent Anthropic fallback normalizes retired IDs: PASS
- LLM client normalizes `ANTHROPIC_MODEL`: PASS
- Provider readiness reports normalized Anthropic model: PASS
- Server Anthropic paths use current Haiku default: PASS
- Server Cerebras helper default corrected to `llama3.1-8b`: PASS

## Commands Run

```powershell
python -m py_compile backend/anthropic_models.py backend/llm_client.py backend/llm_router.py backend/provider_readiness.py backend/agents/base_agent.py backend/routes/agents.py backend/orchestration/executor.py backend/modules_blueprint.py backend/server.py backend/agents/backend_agent.py backend/agents/builder_agent.py backend/agents/database_agent.py backend/agents/deployment_agent.py backend/agents/design_agent.py backend/agents/documentation_agent.py backend/agents/frontend_agent.py backend/agents/planner_agent.py backend/agents/security_agent.py backend/agents/stack_selector_agent.py backend/agents/test_generation_agent.py backend/tests/test_anthropic_model_fix.py
$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_anthropic_model_fix.py backend/tests/test_provider_readiness.py backend/tests/test_tool_agents.py backend/tests/test_builder_agent.py -q --noconftest
```

## Artifacts

- `proof/anthropic_model_fix/active_model_scan.txt`
- `proof/anthropic_model_fix/retired_model_scan.txt`
- `proof/anthropic_model_fix/runtime_retired_model_scan.txt` (empty = no retired Anthropic model IDs left in runtime source)
- `proof/anthropic_model_fix/pytest.log`
