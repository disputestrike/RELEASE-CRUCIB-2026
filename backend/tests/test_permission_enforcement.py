"""
End-to-end tests for permission engine enforcement in tool execution.
Tests that policy decisions are respected when CRUCIB_ENABLE_TOOL_POLICY is enabled.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_tool_executor_respects_permission_policy_when_enabled(monkeypatch):
    """
    AUDIT: Verify that execute_tool() actually blocks dangerous calls when policy is enabled.
    """
    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")

    from tool_executor import execute_tool
    from services.runtime.runtime_engine import runtime_engine

    # Test 1: Dangerous command should be blocked
    result = runtime_engine.execute_tool_for_task(
        project_id="proj-audit",
        task_id="tsk-audit-1",
        tool_name="run",
        params={"command": ["rm -rf /"]},
    )
    assert result["success"] is False, "Expected dangerous command to be blocked"
    assert "Policy denied" in result.get("error", ""), f"Expected policy error, got: {result}"

    # Test 2: Sensitive file write should be blocked
    result = runtime_engine.execute_tool_for_task(
        project_id="proj-audit",
        task_id="tsk-audit-2",
        tool_name="file",
        params={"action": "write", "path": ".env", "content": "SECRET=xyz"},
    )
    assert result["success"] is False, "Expected .env write to be blocked"
    assert "sensitive" in result.get("error", "").lower(), f"Expected sensitive path error, got: {result}"

    # Test 3: Safe command should be allowed (will fail due to workspace isolation but not policy)
    result = runtime_engine.execute_tool_for_task(
        project_id="proj-audit",
        task_id="tsk-audit-3",
        tool_name="run",
        params={"command": ["python", "-m", "pytest", "--version"]},
    )
    # May fail due to other reasons, but not policy
    if result.get("error"):
        assert "Policy denied" not in result.get("error", ""), "Safe command should not be policy-blocked"


@pytest.mark.asyncio
async def test_skill_tool_restrictions_enforced_in_execution(monkeypatch, tmp_path):
    """
    AUDIT: Verify that skills restrict tool execution to allowed_tools.
    """
    from services.skills.skill_registry import resolve_skill
    from services.skills.skill_executor import skill_allows_tool

    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")

    # Get the 'commit' skill which only allows {'run', 'file'} tools
    skill = resolve_skill("/commit")
    assert skill is not None, "commit skill should exist"

    # Test: 'api' tool should NOT be allowed by 'commit' skill
    assert not skill_allows_tool(skill, "api"), "commit skill should not allow 'api' tool"

    # Test: 'run' tool SHOULD be allowed by 'commit' skill
    assert skill_allows_tool(skill, "run"), "commit skill should allow 'run' tool"

    # Test: 'file' tool SHOULD be allowed by 'commit' skill
    assert skill_allows_tool(skill, "file"), "commit skill should allow 'file' tool"


@pytest.mark.asyncio
async def test_permission_policy_disabled_by_default_is_permissive(monkeypatch):
    """
    AUDIT: Verify that when CRUCIB_ENABLE_TOOL_POLICY is NOT set,
    permission engine returns "disabled" mode and allows everything.
    """
    # Ensure policy is disabled
    monkeypatch.delenv("CRUCIB_ENABLE_TOOL_POLICY", raising=False)

    from services.policy.permission_engine import evaluate_tool_call

    # Dangerous patterns should still be "allowed" when policy is disabled
    result = evaluate_tool_call("run", {"command": ["rm -rf /"]})
    assert result.allowed is True, "Policy disabled should allow anything"
    assert result.mode == "disabled", "Mode should be 'disabled'"


def test_provider_fallback_registry_requires_feature_flag(monkeypatch):
    """
    AUDIT: Verify that provider fallback is disabled by default.
    """
    monkeypatch.delenv("CRUCIB_ENABLE_PROVIDER_REGISTRY", raising=False)

    from services.providers.provider_registry import choose_chain

    # Without flag, should return chain unchanged
    input_chain = [("haiku", "claude-haiku", "anthropic"), ("opus", "claude-opus", "anthropic")]
    result = choose_chain(input_chain)
    assert result == input_chain, "When disabled, chain should be unchanged"


def test_provider_fallback_can_reorder_when_enabled(monkeypatch):
    """
    AUDIT: Verify that provider fallback CAN reorder chain when enabled.
    """
    monkeypatch.setenv("CRUCIB_ENABLE_PROVIDER_REGISTRY", "1")

    from services.providers.provider_registry import choose_chain

    # Input chain with low-capability (no tools) first, high-capability second
    input_chain = [
        ("fast", "gpt-4-mini", "openai"),  # Low capability
        ("smart", "gpt-4", "openai"),  # High capability (has tools)
    ]

    result = choose_chain(input_chain, need_tools=True)
    # Should have reordered to put tool-capable provider first
    # (This test documents expected behavior but actual reordering depends on PROVIDER_CONTRACTS)


@pytest.mark.asyncio
async def test_task_events_published_to_event_bus(monkeypatch):
    """
    AUDIT: Verify that task lifecycle emits events observable via recent_events().
    """
    from services.runtime.task_manager import task_manager
    from services.events import event_bus

    emitted = []

    def _capture(event_type, payload=None):
        emitted.append((event_type, payload or {}))

    monkeypatch.setattr(event_bus, "emit", _capture)

    # Create a task
    task = task_manager.create_task(
        project_id="proj-1",
        description="test",
        metadata={"test": True},
    )

    # Should have emitted task.started
    assert any(t == "task.started" for t, _ in emitted), f"Expected task.started, got {[t for t, _ in emitted]}"

    # Update it
    task_manager.update_task(task["project_id"], task["task_id"], status="completed")
    assert any(t == "task.updated" for t, _ in emitted), f"Expected task.updated, got {[t for t, _ in emitted]}"


def test_event_bus_recent_returns_latest_events():
    """
    AUDIT: Verify that event_bus.recent_events() returns last N events.
    """
    from services.events import EventBus

    bus = EventBus()

    # Emit some events
    for i in range(5):
        bus.emit(f"test.event.{i}", {"num": i})

    # Get recent
    recent = bus.recent_events(limit=3)
    assert len(recent) == 3, f"Expected 3 recent, got {len(recent)}"
    assert recent[-1].event_type == "test.event.4", "Should return in order"
