from __future__ import annotations

import pytest

from orchestration import runtime_state


@pytest.mark.asyncio
async def test_runtime_state_create_and_get_job():
    job = await runtime_state.create_job(
        project_id="rs-proj-1",
        mode="guided",
        goal="build api",
        user_id="user-rs-1",
    )
    assert job["id"]
    fetched = await runtime_state.get_job(job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]
    assert fetched["project_id"] == "rs-proj-1"


@pytest.mark.asyncio
async def test_runtime_state_steps_events_checkpoint_flow():
    job = await runtime_state.create_job(
        project_id="rs-proj-2",
        mode="guided",
        goal="run checks",
        user_id="user-rs-2",
    )

    step = await runtime_state.create_step(
        job_id=job["id"],
        step_key="lint",
        agent_name="LintAgent",
        phase="build",
        depends_on=[],
        order_index=0,
    )
    assert step["job_id"] == job["id"]

    updated_step = await runtime_state.update_step_state(step["id"], "failed", extra={"error_message": "lint failed"})
    assert updated_step is not None
    assert updated_step["status"] == "failed"

    steps = await runtime_state.get_steps(job["id"])
    assert len(steps) >= 1
    assert any(s["id"] == step["id"] for s in steps)

    await runtime_state.append_job_event(job["id"], "custom_event", {"value": 42})
    events = await runtime_state.get_job_events(job["id"], limit=50)
    assert len(events) >= 2  # includes step-created/step-status-changed + custom_event
    assert any(e["event_type"] == "custom_event" for e in events)

    await runtime_state.save_checkpoint(job["id"], "latest_failure", {"reason": "lint"})
    cp = await runtime_state.load_checkpoint(job["id"], "latest_failure")
    assert cp is not None
    assert cp["reason"] == "lint"


@pytest.mark.asyncio
async def test_runtime_state_since_id_filter():
    job = await runtime_state.create_job(
        project_id="rs-proj-3",
        mode="guided",
        goal="events",
        user_id="user-rs-3",
    )
    e1 = await runtime_state.append_job_event(job["id"], "a", {"x": 1})
    await runtime_state.append_job_event(job["id"], "b", {"x": 2})

    rows = await runtime_state.get_job_events(job["id"], since_id=e1["id"], limit=20)
    assert len(rows) >= 1
    assert all(r["id"] != e1["id"] for r in rows)


def test_coerce_json_text_updates():
    assert runtime_state._coerce_json_text_updates({"a": 1}) == {"a": 1}
    assert runtime_state._coerce_json_text_updates('{"a":1}') == {"a": 1}
    assert runtime_state._coerce_json_text_updates("raw") == {"value": "raw"}
    assert runtime_state._coerce_json_text_updates(None) == {}
