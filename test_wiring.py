"""
Compatibility wiring smoke tests.

These focus on the current authoritative runtime story:
- job progress transport is importable
- legacy compatibility shims delegate to the real planner/controller path
- design system artifacts exist and are injected
"""

from __future__ import annotations

import asyncio
import json
import sys


async def _websocket_endpoint_check() -> None:
    from backend.api.routes.job_progress import broadcast_event, manager

    assert hasattr(manager, "active_connections")
    await broadcast_event("test-job", "agent_start", agent_name="Test Agent")


async def _wired_executor_check() -> None:
    from backend.orchestration.executor_wired import get_wired_executor

    executor = get_wired_executor("job-123", "proj-123")
    context = executor._inject_design_system({})
    assert context.get("design_system_injected") is True
    assert context["design_system"]["colors"]["primary"] == "#007BFF"
    assert "Tailwind" in context["design_system_prompt"]


async def _build_endpoint_check() -> None:
    from backend.routes_wired import build_wired

    result = await build_wired("Build realtime collaboration editor with sockets and rate limiting")
    assert result["status"] == "success"
    assert result["plan"]["orchestration_mode"] == "agent_swarm"
    assert result["controller_summary"]["controller_mode"] == "selective_parallel_swarm"


def test_sandbox_security() -> None:
    from backend.sandbox.egress_filter import EgressFilter

    assert EgressFilter.is_whitelisted("https://api.anthropic.com/v1/messages")
    assert EgressFilter._contains_secret("api_key: \"sk-abc123\"")


def test_design_system_json() -> None:
    with open("backend/design_system.json", encoding="utf-8") as fh:
        design_system = json.load(fh)

    assert "colors" in design_system
    assert design_system["colors"]["primary"] == "#007BFF"


def test_websocket_endpoint() -> None:
    asyncio.run(_websocket_endpoint_check())


def test_wired_executor() -> None:
    asyncio.run(_wired_executor_check())


def test_build_endpoint_imports() -> None:
    asyncio.run(_build_endpoint_check())


def main() -> int:
    checks = [
        ("websocket endpoint", test_websocket_endpoint),
        ("wired executor", test_wired_executor),
        ("build endpoint", test_build_endpoint_imports),
        ("sandbox security", test_sandbox_security),
        ("design system json", test_design_system_json),
    ]
    failures = []
    print("=" * 60)
    print("WIRING TEST SUITE")
    print("=" * 60)
    for name, fn in checks:
        try:
            fn()
            print(f"PASS - {name}")
        except Exception as exc:
            failures.append((name, exc))
            print(f"FAIL - {name}: {exc}")
    print(f"\nResult: {len(checks) - len(failures)}/{len(checks)} passed")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
