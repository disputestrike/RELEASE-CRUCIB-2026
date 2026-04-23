from __future__ import annotations

import subprocess

import pytest


@pytest.mark.asyncio
async def test_permission_skill_tool_full_chain(monkeypatch):
    """
    Full integration test for permission + skill + tool execution path.

    Proves:
    - permission engine is called during execute_tool
    - skill restriction is enforced during execute_tool
    - allowed tool call succeeds
    - denied tool call is blocked
    - returned metadata includes policy outcome
    """
    from tool_executor import execute_tool
    from services.runtime.runtime_engine import runtime_engine

    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    monkeypatch.setenv("RUN_IN_SANDBOX", "0")

    # Track permission engine invocation while preserving real behavior.
    from services.policy import permission_engine as pe

    original_eval = pe.evaluate_tool_call
    calls = []

    def _wrapped_eval(tool_name, params, **kwargs):
        calls.append((tool_name, dict(params or {})))
        return original_eval(tool_name, params, **kwargs)

    monkeypatch.setattr(pe, "evaluate_tool_call", _wrapped_eval)

    # 0) Direct execution is blocked outside runtime engine via structured denial.
    direct = execute_tool(
        project_id="proj-integ-1",
        tool_name="run",
        params={"command": ["python", "--version"], "skill": "/commit"},
    )
    assert direct["success"] is False
    assert direct["policy"]["reason"] == "runtime_engine_required"
    assert "runtime_engine" in direct["error"]

    # 1) Allowed call succeeds with policy metadata via runtime engine.
    allowed = runtime_engine.execute_tool_for_task(
        project_id="proj-integ-1",
        task_id="tsk-integ-allow",
        tool_name="run",
        params={"command": ["python", "--version"], "skill": "/commit"},
        skill_hint="commit",
    )
    assert allowed["success"] is True
    assert "policy" in allowed
    assert allowed["policy"]["mode"] in {"allow", "disabled", "fallback"}
    assert allowed.get("skill", {}).get("name") == "commit"

    # 2) Denied by skill restriction (review skill does not allow api tool)
    blocked_skill = runtime_engine.execute_tool_for_task(
        project_id="proj-integ-1",
        task_id="tsk-integ-skill",
        tool_name="api",
        params={"url": "https://example.com", "skill": "/review"},
        skill_hint="review",
    )
    assert blocked_skill["success"] is False
    assert "Skill denied tool" in blocked_skill.get("error", "")

    # 3) Denied by permission policy
    blocked_policy = runtime_engine.execute_tool_for_task(
        project_id="proj-integ-1",
        task_id="tsk-integ-policy",
        tool_name="run",
        params={"command": ["rm -rf /"]},
        skill_hint="commit",
    )
    assert blocked_policy["success"] is False
    assert blocked_policy.get("policy", {}).get("mode") == "deny"

    # 4) Prove blocked call cannot silently run
    def _boom(*_args, **_kwargs):
        raise AssertionError("subprocess.run should not execute for denied policy path")

    monkeypatch.setattr(subprocess, "run", _boom)
    blocked_again = runtime_engine.execute_tool_for_task(
        project_id="proj-integ-1",
        task_id="tsk-integ-policy2",
        tool_name="run",
        params={"command": ["rm -rf /"]},
        skill_hint="commit",
    )
    assert blocked_again["success"] is False

    # 5) Permission engine invocation proof
    assert len(calls) >= 2
    assert any(tool == "run" for tool, _ in calls)
