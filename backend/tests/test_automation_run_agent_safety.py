import pytest

from backend.automation.executor import run_actions


@pytest.mark.asyncio
async def test_run_agent_blocks_cycles_before_callback():
    called = False

    async def callback(user_id, agent_name, prompt):
        nonlocal called
        called = True
        return {"ok": True}

    status, output, logs, waiting = await run_actions(
        {
            "run_agent_lineage": ["Builder"],
            "actions": [{"type": "run_agent", "agent_name": "Builder", "prompt": "continue"}],
        },
        user_id="u1",
        run_id="r1",
        steps_context=[],
        run_agent_callback=callback,
    )

    assert status == "failed"
    assert not called
    assert "cycle detected" in output["error"]
    assert waiting is None
    assert any("[ERROR]" in line for line in logs)


@pytest.mark.asyncio
async def test_run_agent_requires_internal_token_without_callback(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_INTERNAL_TOKEN", raising=False)

    status, output, logs, waiting = await run_actions(
        {"actions": [{"type": "run_agent", "agent_name": "Builder", "prompt": "continue"}]},
        user_id="u1",
        run_id="r1",
        steps_context=[],
    )

    assert status == "failed"
    assert "CRUCIBAI_INTERNAL_TOKEN is required" in output["error"]
    assert waiting is None


@pytest.mark.asyncio
async def test_run_agent_depth_and_budget_limits(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_RUN_AGENT_MAX_DEPTH", "1")

    status, output, _logs, _waiting = await run_actions(
        {
            "run_agent_depth": 1,
            "actions": [{"type": "run_agent", "agent_name": "Builder", "prompt": "continue"}],
        },
        user_id="u1",
        run_id="r1",
        steps_context=[],
        run_agent_callback=lambda *_args: {"ok": True},
    )
    assert status == "failed"
    assert "depth limit" in output["error"]

    status, output, _logs, _waiting = await run_actions(
        {
            "run_agent_budget": 0,
            "actions": [{"type": "run_agent", "agent_name": "Builder", "prompt": "continue"}],
        },
        user_id="u1",
        run_id="r2",
        steps_context=[],
        run_agent_callback=lambda *_args: {"ok": True},
    )
    assert status == "failed"
    assert "budget exhausted" in output["error"]
