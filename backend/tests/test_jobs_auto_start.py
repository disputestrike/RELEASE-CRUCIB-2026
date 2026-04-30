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


@pytest.mark.asyncio
async def test_resume_job_uses_project_workspace_path(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import asyncio

    from backend import server
    from backend.orchestration import auto_runner
    from backend.routes import jobs

    workspace = tmp_path / "projects" / "project_1"
    calls = {"resume": [], "state": [], "events": []}

    async def fake_resolve_job(job_id, user):
        assert user == {"id": "user_1"}
        return {"id": job_id, "project_id": "project_1", "user_id": "user_1", "status": "failed"}

    async def fake_prepare(job_id):
        calls["prepare"] = job_id
        return 2

    async def fake_get_pool():
        return SimpleNamespace()

    class FakeRuntimeState:
        def set_pool(self, pool):
            calls["pool"] = pool

        async def update_job_state(self, job_id, status, extra=None):
            calls["state"].append((job_id, status, extra or {}))

        async def append_job_event(self, job_id, event_type, payload=None):
            calls["events"].append((job_id, event_type, payload or {}))

    def fake_project_workspace_path(project_id):
        assert project_id == "project_1"
        return workspace

    def fake_create_task(value):
        calls["task"] = value
        return SimpleNamespace(cancel=lambda: None)

    def fake_resume_runner(job_id, workspace_path, pool):
        calls["resume"].append((job_id, workspace_path, pool))
        return {"success": True}

    monkeypatch.setattr(jobs, "_resolve_job", fake_resolve_job)
    monkeypatch.setattr(jobs, "_get_pool", fake_get_pool)
    monkeypatch.setattr(jobs, "_get_runtime_state", lambda: FakeRuntimeState())
    monkeypatch.setattr(server, "_project_workspace_path", fake_project_workspace_path)
    monkeypatch.setattr(auto_runner, "prepare_failed_job_for_rerun", fake_prepare)
    monkeypatch.setattr(auto_runner, "resume_job", fake_resume_runner)
    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    result = await jobs.resume_job("job_1", user={"id": "user_1"})

    assert result["resumed"] is True
    assert result["workspace_path"] == str(workspace)
    assert calls["resume"][0][0] == "job_1"
    assert calls["resume"][0][1] == str(workspace)
    assert calls["resume"][0][1] != ""
    assert workspace.exists()
    assert calls["state"][0][1] == "running"
    assert calls["events"][0][1] == "job_resume_requested"
