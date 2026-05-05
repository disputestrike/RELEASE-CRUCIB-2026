from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_runtime_task_lifecycle_routes():
    from routes import runtime as route

    project_id = f"proj-{uuid.uuid4().hex[:8]}"

    created = await route.create_runtime_task(
        route.CreateTaskBody(project_id=project_id, description="run build"),
        user={"id": "user-1"},
    )
    assert created["success"] is True
    task = created["task"]
    task_id = task["task_id"]
    assert task["status"] == "running"

    listed = await route.list_runtime_tasks(project_id=project_id, limit=50, _user={"id": "user-1"})
    assert listed["success"] is True
    assert listed["count"] >= 1
    assert any(t["task_id"] == task_id for t in listed["tasks"])

    got = await route.get_runtime_task(task_id=task_id, project_id=project_id, _user={"id": "user-1"})
    assert got["success"] is True
    assert got["task"]["task_id"] == task_id

    updated = await route.set_runtime_task_status(
        task_id=task_id,
        body=route.UpdateTaskStatusBody(project_id=project_id, status="completed", metadata={"ok": True}),
        _user={"id": "user-1"},
    )
    assert updated["task"]["status"] == "completed"
    assert updated["task"]["metadata"].get("ok") is True

    # Terminal status is enforced; kill should not override completed.
    killed = await route.kill_runtime_task(
        task_id=task_id,
        body=route.KillTaskBody(project_id=project_id, reason="manual"),
        _user={"id": "user-1"},
    )
    assert killed["task"]["status"] == "completed"

    recent = await route.runtime_recent_events(limit=25, _user={"id": "user-1"})
    assert recent["success"] is True
    assert recent["count"] >= 1
    assert any(e["type"].startswith("task.") for e in recent["events"])

    caps = await route.swarm_capabilities(_user={"id": "user-1"})
    assert caps["success"] is True
    assert caps["mode"] == "single_tool_runtime"
    assert "spawn_unbounded" in caps

    deleted = await route.delete_runtime_task(task_id=task_id, project_id=project_id, _user={"id": "user-1"})
    assert deleted["success"] is True
    assert deleted["deleted"] is True


@pytest.mark.asyncio
async def test_task_manager_event_bus_live_propagation_via_recent_events_route():
    from routes import runtime as route
    from services.events import event_bus

    project_id = f"proj-live-{uuid.uuid4().hex[:8]}"

    before_rows = event_bus.recent_events(limit=500)
    before_count = len(before_rows)

    created = await route.create_runtime_task(
        route.CreateTaskBody(project_id=project_id, description="event propagation check"),
        user={"id": "user-1"},
    )
    assert created["success"] is True
    task = created["task"]
    task_id = task["task_id"]

    await route.set_runtime_task_status(
        task_id=task_id,
        body=route.UpdateTaskStatusBody(project_id=project_id, status="completed", metadata={"probe": True}),
        _user={"id": "user-1"},
    )

    await route.delete_runtime_task(task_id=task_id, project_id=project_id, _user={"id": "user-1"})

    after_rows = event_bus.recent_events(limit=500)
    after_count = len(after_rows)
    assert after_count >= before_count + 3

    # Prove exact event names are present in live recent event stream.
    recent = await route.runtime_recent_events(limit=500, _user={"id": "user-1"})
    assert recent["success"] is True
    names = [e["type"] for e in recent["events"]]

    assert "task.started" in names
    assert "task.updated" in names
    assert "task.deleted" in names


@pytest.mark.asyncio
async def test_runtime_task_pause_resume_routes():
    from routes import runtime as route

    project_id = f"proj-pause-{uuid.uuid4().hex[:8]}"
    created = await route.create_runtime_task(
        route.CreateTaskBody(project_id=project_id, description="pause resume test"),
        user={"id": "user-1"},
    )
    task_id = created["task"]["task_id"]

    paused = await route.pause_runtime_task(
        task_id=task_id,
        body=route.PauseTaskBody(project_id=project_id, reason="test pause"),
        _user={"id": "user-1"},
    )
    assert paused["success"] is True
    assert paused["task"]["status"] == "paused"

    resumed = await route.resume_runtime_task(
        task_id=task_id,
        body=route.ResumeTaskBody(project_id=project_id, reason="test resume"),
        _user={"id": "user-1"},
    )
    assert resumed["success"] is True
    assert resumed["task"]["status"] == "running"
