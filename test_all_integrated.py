"""
Integration smoke tests for the compatibility feature layer.

These keep the original intent of the "all integrated" checks, but they now
verify the live planner/controller/memory path instead of demo-only modules.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


async def _broadcast_check() -> None:
    from backend.api.routes.job_progress import broadcast_event

    await broadcast_event("test-1", "agent_start", agent_name="Test")


async def _design_injection_check() -> None:
    from backend.orchestration.executor_wired import WiredExecutor

    executor = WiredExecutor("design-test", "proj")
    context = executor._inject_design_system({})
    assert context.get("design_system_injected") is True
    assert "Tailwind" in context["design_system_prompt"]


async def _full_flow_check() -> None:
    from backend.api.routes.job_progress import broadcast_event
    from backend.orchestration.executor_wired import WiredExecutor

    executor = WiredExecutor("full-test", "proj")
    executor.set_broadcaster(broadcast_event)

    async def agent(ctx):
        return {"output": "test", "tokens_used": 0}

    result = await executor.execute_agent("Test", agent, {"phase": "test"})
    assert result["output"] == "test"


async def _build_endpoint_check() -> None:
    from backend.routes_wired import build_wired

    result = await build_wired(
        "Build enterprise API with CORS, security headers, input validation, and rate limiting"
    )
    assert result["status"] == "success"
    selected = set(result["plan"]["selected_agents"])
    assert "CORS & Security Headers Agent" in selected
    assert "Input Validation Agent" in selected
    assert "Rate Limiting Agent" in selected


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


def test_prompt_artifact_exists() -> None:
    path = Path("backend/prompts/design_system_injection.txt")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "WCAG" in text


def test_design_injection() -> None:
    asyncio.run(_design_injection_check())


def test_full_flow() -> None:
    asyncio.run(_full_flow_check())


def test_build_endpoint_imports() -> None:
    asyncio.run(_build_endpoint_check())


def main() -> int:
    checks = [
        ("websocket module", test_websocket_module),
        ("broadcast function", test_broadcast_function),
        ("executor wiring", test_executor_wiring),
        ("egress filter", test_egress_filter),
        ("secret detection", test_secret_detection),
        ("design json", test_design_json),
        ("prompt artifact", test_prompt_artifact_exists),
        ("design injection", test_design_injection),
        ("full flow", test_full_flow),
        ("build endpoint", test_build_endpoint_imports),
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
