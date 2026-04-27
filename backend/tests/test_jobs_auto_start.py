from fastapi import BackgroundTasks
import pytest


@pytest.mark.asyncio
async def test_auto_mode_job_schedules_runner(monkeypatch):
    from backend.routes import jobs, orchestrator

    calls = []

    async def fake_create_job_service(**kwargs):
        return {"success": True, "job": {"id": "job_auto_1", "status": "running"}}

    async def fake_run_auto(body, background_tasks, user):
        calls.append(
            {
                "job_id": body.job_id,
                "background_tasks": background_tasks,
                "user": user,
            }
        )
        return {"success": True, "job_id": body.job_id}

    monkeypatch.setattr(jobs, "create_job_service", fake_create_job_service)
    monkeypatch.setattr(orchestrator, "run_auto", fake_run_auto)

    result = await jobs.create_job(
        jobs.JobCreateRequest(goal="Build a todo app", mode="auto"),
        BackgroundTasks(),
        user={"id": "user_1"},
    )

    assert result["auto_run"]["success"] is True
    assert len(calls) == 1
    assert calls[0]["job_id"] == "job_auto_1"
    assert isinstance(calls[0]["background_tasks"], BackgroundTasks)
    assert calls[0]["user"] == {"id": "user_1"}


@pytest.mark.asyncio
async def test_guided_job_does_not_schedule_runner(monkeypatch):
    from backend.routes import jobs, orchestrator

    async def fake_create_job_service(**kwargs):
        return {"success": True, "job": {"id": "job_guided_1", "status": "planned"}}

    async def fake_run_auto(body, background_tasks, user):
        raise AssertionError("guided jobs should not auto-start")

    monkeypatch.setattr(jobs, "create_job_service", fake_create_job_service)
    monkeypatch.setattr(orchestrator, "run_auto", fake_run_auto)

    result = await jobs.create_job(
        jobs.JobCreateRequest(goal="Plan a todo app", mode="guided"),
        BackgroundTasks(),
        user={"id": "user_1"},
    )

    assert "auto_run" not in result
