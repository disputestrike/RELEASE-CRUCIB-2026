"""
Integration smoke tests for the added feature modules.

These are valid pytest tests and can also be run directly with Python.
"""

from __future__ import annotations

import asyncio
import json
import sys


async def _broadcast_check() -> None:
    from backend.api.routes.job_progress import broadcast_event

    await broadcast_event("test-1", "agent_start", agent_name="Test")


async def _design_injection_check() -> None:
    from backend.orchestration.executor_wired import WiredExecutor

    executor = WiredExecutor("design-test", "proj")
    context = executor._inject_design_system({})
    assert context.get("design_system_injected") is True


async def _full_flow_check() -> None:
    from backend.api.routes.job_progress import broadcast_event
    from backend.orchestration.executor_wired import WiredExecutor

    executor = WiredExecutor("full-test", "proj")
    executor.set_broadcaster(broadcast_event)

    async def agent(ctx):
        return {"output": "test", "tokens_used": 0}

    result = await executor.execute_agent("Test", agent, {"phase": "test"})
    assert result["output"] == "test"


def test_websocket_module() -> None:
    from backend.api.routes.job_progress import manager

    assert hasattr(manager, "active_connections")


def test_broadcast_function() -> None:
    asyncio.run(_broadcast_check())


def test_executor_wiring() -> None:
    asyncio.run(_design_injection_check())


def test_egress_filter() -> None:
    from backend.sandbox.egress_filter import EgressFilter

    assert EgressFilter.is_whitelisted("https://api.anthropic.com/v1")
    assert not EgressFilter.is_whitelisted("https://evil.com")


def test_secret_detection() -> None:
    from backend.sandbox.egress_filter import EgressFilter

    assert EgressFilter._contains_secret("sk-12345678")
    assert not EgressFilter._contains_secret("normal")


def test_design_json() -> None:
    with open("backend/design_system.json", encoding="utf-8") as fh:
        ds = json.load(fh)
    assert ds["colors"]["primary"] == "#007BFF"


def test_design_injection() -> None:
    asyncio.run(_design_injection_check())


def test_full_flow() -> None:
    asyncio.run(_full_flow_check())


def test_build_endpoint_imports() -> None:
    from backend.routes_wired import build_wired

    assert callable(build_wired)


def main() -> int:
    checks = [
        ("websocket module", test_websocket_module),
        ("broadcast function", test_broadcast_function),
        ("executor wiring", test_executor_wiring),
        ("egress filter", test_egress_filter),
        ("secret detection", test_secret_detection),
        ("design json", test_design_json),
        ("design injection", test_design_injection),
        ("full flow", test_full_flow),
        ("build endpoint imports", test_build_endpoint_imports),
    ]
    failures = []
    print("=" * 70)
    print("INTEGRATION TEST SUITE")
    print("=" * 70)
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
