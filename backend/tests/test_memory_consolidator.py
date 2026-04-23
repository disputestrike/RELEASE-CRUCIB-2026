"""CF25 — tests for the ported memory consolidator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.memory.consolidator import (
    consolidate_session, MIN_MESSAGES_TO_CONSOLIDATE
)


def _msgs(n: int):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"} for i in range(n)]


def test_short_sessions_skipped():
    assert consolidate_session(_msgs(3)) == []


def test_no_llm_is_noop():
    # Enough messages, but no llm_call → empty
    assert consolidate_session(_msgs(MIN_MESSAGES_TO_CONSOLIDATE + 1)) == []


def test_parses_llm_response_and_saves():
    saved = []
    def llm(sys_prompt, user_msg):
        return json.dumps({"memories": [
            {"name": "prefers_concise", "type": "user", "description": "d",
             "content": "User prefers short replies.", "confidence": 0.85},
            {"name": "uses_postgres", "type": "project", "description": "d",
             "content": "DB is Postgres.", "confidence": 0.9},
        ]})
    def save(mem):
        saved.append(mem.name); return True

    names = consolidate_session(_msgs(MIN_MESSAGES_TO_CONSOLIDATE + 1), llm_call=llm, save=save)
    assert names == ["prefers_concise", "uses_postgres"]
    assert saved == ["prefers_concise", "uses_postgres"]


def test_conflict_check_blocks_lower_confidence():
    def llm(s, u): return json.dumps({"memories": [
        {"name": "x", "type": "user", "description": "d", "content": "c", "confidence": 0.7}
    ]})
    def conflict(mem): return 0.9  # existing is higher
    names = consolidate_session(_msgs(10), llm_call=llm, conflict_check=conflict, save=lambda m: True)
    assert names == []


def test_caps_at_three_memories():
    def llm(s, u): return json.dumps({"memories": [
        {"name": f"m{i}", "type": "user", "description": "d", "content": "c"} for i in range(10)
    ]})
    names = consolidate_session(_msgs(10), llm_call=llm, save=lambda m: True)
    assert len(names) == 3


def test_malformed_llm_response_safe():
    def bad(s, u): return "not json at all"
    assert consolidate_session(_msgs(10), llm_call=bad) == []
