from __future__ import annotations

import subprocess

import pytest


@pytest.mark.asyncio
async def test_policy_allow_ask_deny_and_no_silent_run(monkeypatch):
    from services.runtime.runtime_engine import runtime_engine

    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    monkeypatch.setenv("RUN_IN_SANDBOX", "0")

    # Deny path
    denied = runtime_engine.execute_tool_for_task(
        project_id="proj-pol-1",
        task_id="tsk-pol-1",
        tool_name="run",
        params={"command": ["rm -rf /"]},
        skill_hint="commit",
    )
    assert denied["success"] is False
    assert denied.get("policy", {}).get("mode") == "deny"

    # Ask path
    asked = runtime_engine.execute_tool_for_task(
        project_id="proj-pol-1",
        task_id="tsk-pol-2",
        tool_name="run",
        params={"command": ["vercel", "--version"]},
        skill_hint="commit",
    )
    assert asked["success"] is False
    assert asked.get("policy", {}).get("mode") == "ask"
    assert asked.get("policy", {}).get("approval_required") is True

    # No silent run when denied: subprocess.run must not be called
    def _boom(*_args, **_kwargs):
        raise AssertionError("subprocess.run should not execute on denied policy")

    monkeypatch.setattr(subprocess, "run", _boom)
    denied_again = runtime_engine.execute_tool_for_task(
        project_id="proj-pol-1",
        task_id="tsk-pol-3",
        tool_name="run",
        params={"command": ["rm -rf /"]},
        skill_hint="commit",
    )
    assert denied_again["success"] is False


@pytest.mark.asyncio
async def test_skill_restriction_and_permitted_metadata(monkeypatch):
    from services.runtime.runtime_engine import runtime_engine

    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    monkeypatch.setenv("RUN_IN_SANDBOX", "0")

    # Skill restriction denies api/browser for review skill
    blocked = runtime_engine.execute_tool_for_task(
        project_id="proj-pol-2",
        task_id="tsk-pol-skill-1",
        tool_name="api",
        params={"url": "https://example.com", "skill": "/review"},
        skill_hint="review",
    )
    assert blocked["success"] is False
    assert "Skill denied tool" in blocked.get("error", "")
    assert blocked.get("skill", {}).get("name") == "review"

    # Permitted path returns policy metadata and skill metadata
    allowed = runtime_engine.execute_tool_for_task(
        project_id="proj-pol-2",
        task_id="tsk-pol-skill-2",
        tool_name="run",
        params={"command": ["python", "--version"], "skill": "/commit"},
        skill_hint="commit",
    )
    assert allowed["success"] is True
    assert "policy" in allowed
    assert allowed["policy"].get("mode") in {"allow", "disabled", "fallback"}
    assert allowed.get("skill", {}).get("matched") is True
    assert allowed.get("skill", {}).get("name") == "commit"
