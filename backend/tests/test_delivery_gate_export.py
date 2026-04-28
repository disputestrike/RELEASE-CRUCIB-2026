"""Delivery gate — ZIP download and published preview share BIV/reconciliation/live-proof."""

from __future__ import annotations

import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path

import importlib

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_download_blocked_when_job_not_completed(monkeypatch):
    from backend.routes import workspace

    rs = importlib.import_module("backend.orchestration.runtime_state")

    scratch = Path(".tmp_delivery_gate_tests") / uuid.uuid4().hex
    root = scratch / "ws"
    root.mkdir(parents=True)

    async def fake_assert_job_access(job_id, user):
        return root

    async def fake_get_job(jid):
        return {"id": jid, "status": "running", "goal": "x", "project_id": "p1"}

    monkeypatch.setattr(workspace, "_assert_job_access", fake_assert_job_access)
    monkeypatch.setattr(rs, "get_job", fake_get_job)
    monkeypatch.setenv("CRUCIBAI_DOWNLOAD_GATE", "1")

    with pytest.raises(HTTPException) as ei:
        await workspace.download_job_workspace_zip(
            "job-incomplete",
            draft=False,
            user={"id": "user-1"},
        )
    assert ei.value.status_code == 409
    shutil.rmtree(scratch, ignore_errors=True)


@pytest.mark.asyncio
async def test_download_draft_skips_gate(monkeypatch):
    from backend.routes import workspace

    rs = importlib.import_module("backend.orchestration.runtime_state")

    scratch = Path(".tmp_delivery_gate_tests") / uuid.uuid4().hex
    root = scratch / "ws"
    (root / "src").mkdir(parents=True)
    (root / "package.json").write_text("{}", encoding="utf-8")

    async def fake_assert_job_access(job_id, user):
        return root

    async def fake_get_job(jid):
        return {"id": jid, "status": "running", "goal": "x"}

    monkeypatch.setattr(workspace, "_assert_job_access", fake_assert_job_access)
    monkeypatch.setattr(rs, "get_job", fake_get_job)

    resp = await workspace.download_job_workspace_zip(
        "job-draft",
        draft=True,
        user={"id": "user-1"},
    )
    payload = io.BytesIO()
    async for chunk in resp.body_iterator:
        payload.write(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
    assert zipfile.ZipFile(payload).namelist()
    shutil.rmtree(scratch, ignore_errors=True)


def test_assert_publish_allowed_passes_with_marker(tmp_path):
    from backend.orchestration.delivery_gate import assert_workspace_publish_allowed

    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / ".crucibai").mkdir()
    (ws / ".crucibai" / "biv_final.json").write_text(
        json.dumps({"passed": True, "score": 92, "profile": "web_site", "issues": []}),
        encoding="utf-8",
    )
    assert_workspace_publish_allowed(
        str(ws),
        {"status": "completed", "goal": "landing", "project_id": "p1"},
    )
