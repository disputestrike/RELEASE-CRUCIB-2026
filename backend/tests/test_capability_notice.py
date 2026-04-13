"""capability_notice_lines: target-aligned mega-spec and preview hints."""

from __future__ import annotations

import pytest
from orchestration.capability_notice import (
    _long_goal_line,
    _preview_workspace_hint,
    capability_notice_lines,
)


def test_long_goal_line_vite_default():
    s = _long_goal_line("vite_react")
    assert "Vite + React (JS)" in s
    assert "runs to completion" in s


def test_long_goal_line_api_backend_no_vite_frontend_lead():
    s = _long_goal_line("api_backend")
    assert "API sketch" in s or "FastAPI" in s
    assert "Vite + React (JS) frontend sketch" not in s


def test_long_goal_line_next_mentions_stub():
    s = _long_goal_line("next_app_router")
    assert "next-app-stub" in s


def test_preview_hint_api_backend():
    h = _preview_workspace_hint("api_backend")
    assert "Sync" in h
    assert "API sketch" in h


def test_preview_hint_default_mentions_refresh():
    h = _preview_workspace_hint("vite_react")
    assert "Sandpack" in h
    assert "Sync" in h
    assert "Refresh" in h


@pytest.mark.parametrize(
    "target,needle_forbidden",
    [
        ("api_backend", "Vite + React (JS) frontend sketch"),
    ],
)
def test_mega_goal_notice_respects_target(target: str, needle_forbidden: str):
    goal = "x" * 3600
    lines = capability_notice_lines(goal, build_target=target)
    joined = " ".join(lines)
    assert needle_forbidden not in joined
    assert _long_goal_line(target) in lines or any(
        _long_goal_line(target) in ln for ln in lines
    )


def test_short_goal_still_has_platform_line():
    lines = capability_notice_lines("hello", build_target="vite_react")
    assert any("execution target" in ln.lower() or "CrucibAI" in ln for ln in lines)
