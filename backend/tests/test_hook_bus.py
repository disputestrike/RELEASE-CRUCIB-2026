"""Tests for services.hooks.bus — typed lifecycle hooks."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.hooks import (  # noqa: E402
    HOOK_STEP_POST,
    HOOK_STEP_PRE,
    HOOK_TASK_POST,
    HOOK_TASK_PRE,
    HOOK_TOOL_ERROR,
    HOOK_TOOL_POST,
    HOOK_TOOL_PRE,
    HookBus,
    VALID_PHASES,
    fire,
    hook_bus,
    register_hook,
    unregister_hook,
)


@pytest.fixture(autouse=True)
def _clean_bus():
    """Reset the global hook_bus between tests."""
    for phase in list(VALID_PHASES):
        hook_bus.clear_phase(phase)
    hook_bus.clear_errors()
    yield
    for phase in list(VALID_PHASES):
        hook_bus.clear_phase(phase)
    hook_bus.clear_errors()


def test_register_and_fire_single_hook():
    seen = []

    def cb(payload):
        seen.append(payload["tool"])

    register_hook(HOOK_TOOL_PRE, cb)
    fire(HOOK_TOOL_PRE, {"tool": "run"})
    assert seen == ["run"]


def test_unknown_phase_raises_on_register():
    with pytest.raises(ValueError, match="Unknown hook phase"):
        register_hook("not.a.phase", lambda p: None)


def test_unknown_phase_raises_on_fire():
    with pytest.raises(ValueError, match="Unknown hook phase"):
        fire("not.a.phase", {})


def test_priority_ordering_is_lowest_first():
    seen = []

    def high(p):  # priority 10 (higher priority = earlier)
        seen.append("high")

    def low(p):  # priority 200 (lower priority = later)
        seen.append("low")

    register_hook(HOOK_TOOL_POST, low, priority=200)
    register_hook(HOOK_TOOL_POST, high, priority=10)
    fire(HOOK_TOOL_POST, {})
    assert seen == ["high", "low"]


def test_multiple_hooks_same_phase_all_fire():
    seen = []
    for i in range(3):
        register_hook(HOOK_TASK_PRE, lambda p, idx=i: seen.append(idx))
    fire(HOOK_TASK_PRE, {})
    assert sorted(seen) == [0, 1, 2]


def test_exception_in_hook_is_swallowed_and_recorded():
    reached = []

    def broken(p):
        raise RuntimeError("kaboom")

    def good(p):
        reached.append(p.get("tool"))

    register_hook(HOOK_TOOL_ERROR, broken, priority=10)
    register_hook(HOOK_TOOL_ERROR, good, priority=20)

    fire(HOOK_TOOL_ERROR, {"tool": "run"})

    # good hook must still have run even though broken raised
    assert reached == ["run"]

    errs = hook_bus.recent_errors()
    assert len(errs) == 1
    assert errs[0].phase == HOOK_TOOL_ERROR
    assert "kaboom" in errs[0].error


def test_unregister_removes_hook():
    seen = []

    def cb(p):
        seen.append(1)

    register_hook(HOOK_STEP_PRE, cb)
    assert unregister_hook(HOOK_STEP_PRE, cb) is True
    fire(HOOK_STEP_PRE, {})
    assert seen == []

    # second unregister call returns False
    assert unregister_hook(HOOK_STEP_PRE, cb) is False


def test_listeners_count_reflects_registrations():
    assert hook_bus.listeners(HOOK_STEP_POST) == 0
    register_hook(HOOK_STEP_POST, lambda p: None)
    register_hook(HOOK_STEP_POST, lambda p: None)
    assert hook_bus.listeners(HOOK_STEP_POST) == 2


def test_payload_gets_phase_annotation():
    captured = {}

    def cb(p):
        captured.update(p)

    register_hook(HOOK_TASK_POST, cb)
    fire(HOOK_TASK_POST, {"task_id": "t1"})
    assert captured.get("_hook_phase") == HOOK_TASK_POST
    assert captured.get("task_id") == "t1"


def test_bridges_to_event_bus_backward_compat():
    """Hook fires should re-emit on event_bus under 'hook.<phase>'."""
    from services.events import event_bus

    seen_events = []

    def sub(record):
        seen_events.append((record.event_type, dict(record.payload)))

    event_bus.subscribe(f"hook.{HOOK_TOOL_PRE}", sub)

    fire(HOOK_TOOL_PRE, {"tool": "file"})

    found = [e for e in seen_events if e[0] == f"hook.{HOOK_TOOL_PRE}"]
    assert found, "hook should bridge to event bus"
    assert found[-1][1].get("tool") == "file"
    # _hook_phase is stripped before bridging
    assert "_hook_phase" not in found[-1][1]


def test_isolated_HookBus_does_not_share_state():
    """Non-singleton instances should not see global registrations."""
    local = HookBus()
    seen = []
    local.register(HOOK_TOOL_PRE, lambda p: seen.append(1))
    # Fire on global — local bus should not react
    fire(HOOK_TOOL_PRE, {})
    assert seen == []
    # Fire on local — global should not react
    local_called = []
    register_hook(HOOK_TOOL_PRE, lambda p: local_called.append(1))
    local.fire(HOOK_TOOL_PRE, {})
    assert local_called == []
