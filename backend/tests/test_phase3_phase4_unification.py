from __future__ import annotations

import json
import uuid
from pathlib import Path


def test_event_bus_adds_canonical_type():
    from services.events.event_bus import EventBus

    bus = EventBus()
    rec = bus.emit("task_start", {"x": 1})

    assert rec.event_type == "task_start"
    assert rec.payload["canonical_type"] == "task.start"


def test_event_bus_canonical_type_helper():
    from services.events.event_bus import EventBus

    assert EventBus.canonical_type("task_start") == "task.start"
    assert EventBus.canonical_type("task.started") == "task.started"


def test_task_manager_mirrors_runtime_state_files():
    from services.runtime.task_manager import task_manager
    from project_state import WORKSPACE_ROOT

    project_id = f"phase3-{uuid.uuid4().hex[:8]}"
    created = task_manager.create_task(project_id=project_id, description="mirror me")
    task_id = created["task_id"]

    updated = task_manager.complete_task(project_id, task_id, metadata={"ok": True})
    assert updated is not None
    assert updated["status"] == "completed"

    root = WORKSPACE_ROOT / project_id / "runtime_state" / task_id
    events_path = root / "events.json"
    checkpoints_path = root / "checkpoints.json"

    assert events_path.exists()
    assert checkpoints_path.exists()

    events = json.loads(events_path.read_text(encoding="utf-8"))
    assert any(e.get("event_type") == "task_created" for e in events)
    assert any(e.get("event_type") == "task_updated" for e in events)

    checkpoints = json.loads(checkpoints_path.read_text(encoding="utf-8"))
    latest = ((checkpoints.get("task_latest") or {}).get("data") or {})
    assert latest.get("id") == task_id
    assert latest.get("status") == "completed"


def test_runtime_state_adapter_sees_task_manager_job_and_events():
    from services.runtime.task_manager import task_manager
    from orchestration import runtime_state
    import asyncio

    project_id = f"phase3-{uuid.uuid4().hex[:8]}"
    task = task_manager.create_task(project_id=project_id, description="adapter visibility", metadata={"mode": "guided", "goal": "adapter visibility", "user_id": "u-phase3"})
    task_id = task["task_id"]

    # Adapter should read task as a job and include its status.
    job = asyncio.get_event_loop().run_until_complete(runtime_state.get_job(task_id))
    assert job is not None
    assert job["id"] == task_id

    # Adapter events are file-backed; mirror writes should be visible via append/get flow once an adapter event is added.
    asyncio.get_event_loop().run_until_complete(runtime_state.append_job_event(task_id, "phase3_probe", {"ok": True}))
    rows = asyncio.get_event_loop().run_until_complete(runtime_state.get_job_events(task_id, limit=50))
    assert any(r.get("event_type") == "phase3_probe" for r in rows)
