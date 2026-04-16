from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_direct_tool_execution_is_forbidden_outside_runtime_scope():
    from tool_executor import execute_tool

    with pytest.raises(PermissionError, match="runtime_engine context"):
        execute_tool(
            project_id="proj-guard-1",
            tool_name="run",
            params={"command": ["python", "--version"]},
        )


@pytest.mark.asyncio
async def test_direct_agent_run_is_forbidden_outside_runtime_scope():
    from agents.base_agent import BaseAgent

    class _DummyAgent(BaseAgent):
        async def execute(self, context):
            return {"ok": True}

    agent = _DummyAgent()

    with pytest.raises(PermissionError, match="runtime_engine"):
        await agent.run({"input": "test"})
