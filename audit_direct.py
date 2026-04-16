#!/usr/bin/env python
"""Runtime-fusion compliance audit (direct execution guards + integration invariants)."""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _run(name: str, fn: Callable[[], str]) -> CheckResult:
    try:
        detail = fn()
        return CheckResult(name=name, passed=True, detail=detail)
    except Exception as exc:
        return CheckResult(name=name, passed=False, detail=str(exc))


def check_permission_engine_default_disabled() -> str:
    os.environ.pop("CRUCIB_ENABLE_TOOL_POLICY", None)
    import services.policy.permission_engine as pe_mod

    importlib.reload(pe_mod)
    result = pe_mod.evaluate_tool_call("run", {"command": ["rm -rf /"]})
    assert result.allowed is True
    assert result.mode == "disabled"
    return "policy disabled mode allows calls by default"


def check_permission_engine_enabled_blocks() -> str:
    os.environ["CRUCIB_ENABLE_TOOL_POLICY"] = "1"
    import services.policy.permission_engine as pe_mod

    importlib.reload(pe_mod)

    denied = pe_mod.evaluate_tool_call("run", {"command": ["rm", "-rf", "/"]})
    assert denied.allowed is False
    assert "dangerous" in denied.reason.lower()

    denied_env = pe_mod.evaluate_tool_call("file", {"action": "write", "path": ".env"})
    assert denied_env.allowed is False

    safe = pe_mod.evaluate_tool_call("run", {"command": ["python", "-m", "pytest"]})
    assert safe.allowed is True
    return "dangerous command and sensitive file writes are blocked when enabled"


def check_skill_restrictions() -> str:
    from services.skills.skill_executor import skill_allows_tool
    from services.skills.skill_registry import resolve_skill

    skill = resolve_skill("/commit")
    assert skill is not None
    assert skill_allows_tool(skill, "run") is True
    assert skill_allows_tool(skill, "file") is True
    assert skill_allows_tool(skill, "api") is False
    return "commit skill allows run/file and blocks api"


def check_provider_registry_mode() -> str:
    os.environ["CRUCIB_ENABLE_PROVIDER_REGISTRY"] = "1"
    import services.providers.provider_registry as pr_mod

    importlib.reload(pr_mod)
    chain = [("haiku", "claude-haiku", "anthropic"), ("llama", "llama3.1-8b", "cerebras")]
    out = pr_mod.choose_chain(chain, need_tools=False, need_vision=False)
    assert isinstance(out, list)
    assert len(out) == len(chain)
    return f"provider registry enabled mode returned ordered chain of {len(out)} models"


def check_runtime_guard_tool_executor() -> str:
    from tool_executor import execute_tool

    r = execute_tool("proj-audit", "run", {"command": ["python", "-V"]})
    assert r.get("success") is False
    reason = (r.get("policy") or {}).get("reason", "")
    assert "runtime_engine_required" in reason
    return "direct tool execution blocked outside runtime scope"


def check_runtime_guard_llm() -> str:
    import asyncio

    from services import llm_service

    async def _call() -> None:
        await llm_service._call_llm_with_fallback(
            message="hi",
            system_message="sys",
            session_id="sess-audit",
            model_chain=[],
            agent_name="Planner",
        )

    try:
        asyncio.run(_call())
    except PermissionError:
        return "direct llm execution blocked outside runtime scope"
    raise AssertionError("expected PermissionError for direct llm execution")


def check_task_manager_events() -> str:
    from services.events import event_bus
    from services.runtime.task_manager import task_manager

    project_id = "proj-audit-events"
    task = task_manager.create_task(project_id=project_id, description="audit")
    task_manager.complete_task(project_id, task["task_id"])

    recent = event_bus.recent_events(limit=200)
    names = [e.event_type for e in recent]
    assert "task_start" in names
    assert "task_end" in names

    matching = [e for e in recent if (e.payload or {}).get("task_id") == task["task_id"]]
    assert matching
    return f"task lifecycle events emitted for {task['task_id']}"


def check_runtime_engine_exists() -> str:
    from services.runtime.runtime_engine import runtime_engine

    assert hasattr(runtime_engine, "run_task_loop")
    assert hasattr(runtime_engine, "start_task")
    assert hasattr(runtime_engine, "spawn_agent")
    return "runtime engine exposes run/start/spawn control APIs"


def main() -> int:
    print("\n=== RUNTIME FUSION COMPLIANCE AUDIT ===\n")

    checks: List[CheckResult] = [
        _run("permission_default_mode", check_permission_engine_default_disabled),
        _run("permission_enabled_blocking", check_permission_engine_enabled_blocks),
        _run("skill_restrictions", check_skill_restrictions),
        _run("provider_registry_mode", check_provider_registry_mode),
        _run("runtime_guard_tool_executor", check_runtime_guard_tool_executor),
        _run("runtime_guard_llm", check_runtime_guard_llm),
        _run("task_manager_events", check_task_manager_events),
        _run("runtime_engine_contract", check_runtime_engine_exists),
    ]

    for r in checks:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.name}: {r.detail}")

    failed = [r for r in checks if not r.passed]
    print("\n=== AUDIT SUMMARY ===")
    print(f"Total checks: {len(checks)}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\n=== CORRECTIVE ACTION REQUIRED ===")
        for r in failed:
            print(f"- {r.name}: {r.detail}")
        return 1

    print("\nAll runtime-fusion compliance checks are green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
