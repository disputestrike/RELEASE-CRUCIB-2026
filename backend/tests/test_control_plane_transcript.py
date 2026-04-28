"""E6: durable workspace lines via append_job_event workspace_transcript."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

# `orchestration.runtime_state` imports `backend.*` — repo root must be on sys.path during collection.
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

runtime_state = importlib.import_module("orchestration.runtime_state")


@pytest.mark.asyncio
async def test_workspace_transcript_persisted_on_job_events():
    job = await runtime_state.create_job(
        project_id="cp-tr-1",
        mode="auto",
        goal="control plane",
        user_id="user-cp-1",
    )
    jid = job["id"]
    await runtime_state.append_job_event(
        jid,
        "workspace_transcript",
        {"role": "user", "text": "Hello run", "source": "test"},
    )
    await runtime_state.append_job_event(
        jid,
        "workspace_transcript",
        {"role": "assistant", "text": "Steer reply", "source": "test"},
    )
    events = await runtime_state.get_job_events(jid, limit=100)
    wt = [e for e in events if e.get("event_type") == "workspace_transcript"]
    assert len(wt) >= 2
    roles = []
    for e in wt:
        p = json.loads(e.get("payload_json") or "{}")
        roles.append(p.get("role"))
    assert "user" in roles
    assert "assistant" in roles
