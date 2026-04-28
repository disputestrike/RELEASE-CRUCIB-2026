"""WS-C smoke tests for the repair_loop orchestration."""
import ast
import asyncio

import pytest

from backend.orchestration.repair_loop import is_enabled, run_repair_loop


def _run(coro):
    return asyncio.run(coro)


async def _ast_verify(code: str):
    try:
        ast.parse(code)
    except SyntaxError as e:
        return {"ok": False, "error": str(e), "evidence": {"lineno": e.lineno}}
    return {"ok": True, "error": None, "evidence": None}


def test_feature_flag_default_off(monkeypatch):
    monkeypatch.delenv("FEATURE_REPAIR_V2", raising=False)
    assert is_enabled() is False


def test_feature_flag_on(monkeypatch):
    monkeypatch.setenv("FEATURE_REPAIR_V2", "1")
    assert is_enabled() is True


def test_repair_loop_converges_in_two_rounds():
    async def attempt(code, notes):
        # round 1: still broken; round 2: fix it
        if "round 1" in " ".join(notes):
            return "x = 1\n"
        return "x = 1 =\n"

    res = _run(run_repair_loop("x =\n", attempt, _ast_verify, max_rounds=5))
    assert res.ok
    assert res.rounds == 2
    assert res.final_code.strip() == "x = 1"


def test_repair_loop_gives_up():
    async def attempt(code, notes):
        return "def (:\n"  # permanently broken

    res = _run(run_repair_loop("def (:\n", attempt, _ast_verify, max_rounds=3))
    assert not res.ok
    assert res.rounds == 3
    assert len(res.scratchpad) == 3


def test_events_emitted():
    events = []

    async def emit(name, payload):
        events.append((name, payload))

    async def attempt(code, notes):
        return "a = 1\n"

    res = _run(run_repair_loop("a =\n", attempt, _ast_verify, max_rounds=2, emit=emit))
    assert res.ok
    names = [e[0] for e in events]
    assert "repair.round.start" in names
    assert "repair.round.end" in names
    assert "repair.final" in names
