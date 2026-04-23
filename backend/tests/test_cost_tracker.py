from __future__ import annotations

import pytest

from services.runtime.cost_tracker import CostTracker


def test_record_and_get():
    ct = CostTracker()
    ct.record("task-1", tokens=100, credits=0.02)
    totals = ct.get("task-1")
    assert totals["tokens"] == 100
    assert abs(totals["credits"] - 0.02) < 1e-9


def test_accumulates_across_calls():
    ct = CostTracker()
    ct.record("task-2", tokens=50, credits=0.01)
    ct.record("task-2", tokens=50, credits=0.01)
    totals = ct.get("task-2")
    assert totals["tokens"] == 100
    assert abs(totals["credits"] - 0.02) < 1e-9


def test_get_unknown_task_returns_zeros():
    ct = CostTracker()
    totals = ct.get("never-recorded")
    assert totals["tokens"] == 0.0
    assert totals["credits"] == 0.0


def test_check_limit_within():
    ct = CostTracker()
    ct.record("task-3", credits=5.0)
    assert ct.check_limit("task-3", limit=10.0) is True


def test_check_limit_exceeded():
    ct = CostTracker()
    ct.record("task-4", credits=11.0)
    assert ct.check_limit("task-4", limit=10.0) is False


def test_reset_clears_task():
    ct = CostTracker()
    ct.record("task-5", tokens=99, credits=0.5)
    ct.reset("task-5")
    totals = ct.get("task-5")
    assert totals["tokens"] == 0.0
    assert totals["credits"] == 0.0


def test_tasks_are_isolated():
    ct = CostTracker()
    ct.record("task-a", credits=1.0)
    ct.record("task-b", credits=2.0)
    assert ct.get("task-a")["credits"] == 1.0
    assert ct.get("task-b")["credits"] == 2.0


def test_default_limit_from_env(monkeypatch):
    monkeypatch.setenv("CRUCIB_TASK_COST_LIMIT", "5.0")
    import importlib
    import services.runtime.cost_tracker as _mod
    importlib.reload(_mod)
    ct = _mod.CostTracker()
    ct.record("task-env", credits=4.9)
    assert ct.check_limit("task-env") is True
    ct.record("task-env", credits=0.2)
    assert ct.check_limit("task-env") is False
