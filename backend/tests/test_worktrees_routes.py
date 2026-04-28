from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_worktree_create_merge_delete_routes(monkeypatch, tmp_path):
    import sys

    monkeypatch.setitem(
        sys.modules, "backend.project_state", SimpleNamespace(WORKSPACE_ROOT=tmp_path)
    )

    dst = tmp_path / "jobs" / "job-1"

    async def _assert_job_access(_job_id, _user):
        return dst

    monkeypatch.setitem(
        sys.modules,
        "backend.routes.workspace",
        SimpleNamespace(_assert_job_access=_assert_job_access),
    )

    from backend.routes import worktrees as route

    user = {"id": "user-1"}

    created = await route.create_worktree(route.WorktreeCreateRequest(id="branch-A"), user=user)
    assert created["id"] == "branch-A"
    wt_path = Path(created["path"])
    assert wt_path.exists()

    sample = wt_path / "src" / "app.js"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text("console.log('ok')\n", encoding="utf-8")

    merged = await route.merge_worktree(
        route.WorktreeMergeRequest(id="branch-A", jobId="job-1"),
        user=user,
    )
    assert merged["status"] == "merged"
    assert merged["files_copied"] == 1
    assert (dst / "src" / "app.js").exists()

    deleted = await route.delete_worktree(route.WorktreeDeleteRequest(id="branch-A"), user=user)
    assert deleted["status"] == "deleted"
    assert not wt_path.exists()
