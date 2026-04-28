from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_direct_tool_execution_is_forbidden_outside_runtime_scope():
    from tool_executor import execute_tool

    result = execute_tool(
        project_id="proj-guard-1",
        tool_name="run",
        params={"command": ["python", "--version"]},
    )

    assert result["success"] is False
    assert result["policy"]["reason"] == "runtime_engine_required"
    assert "runtime_engine" in result["error"]


@pytest.mark.asyncio
async def test_direct_agent_run_is_forbidden_outside_runtime_scope():
    from backend.agents.base_agent import BaseAgent

    class _DummyAgent(BaseAgent):
        async def execute(self, context):
            return {"ok": True}

    agent = _DummyAgent()

    with pytest.raises(PermissionError, match="runtime_engine"):
        run_fn = getattr(agent, "run")
        await run_fn({"input": "test"})
