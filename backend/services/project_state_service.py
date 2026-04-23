from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse


async def get_project_service(*, db, project_id: str, user_id: str) -> dict:
    project = await db.projects.find_one({"id": project_id, "user_id": user_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


async def delete_project_service(*, db, project_id: str, user_id: str, build_events: dict, project_workspace_path: Callable[[str], Path], logger) -> Response:
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.project_logs.delete_many({"project_id": project_id})
    await db.agent_status.delete_many({"project_id": project_id})
    await db.shares.delete_many({"project_id": project_id})
    await db.projects.delete_one({"id": project_id, "user_id": user_id})
    if project_id in build_events:
        del build_events[project_id]
    try:
        workspace_path = project_workspace_path(project_id)
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)
    except Exception as e:
        logger.warning("Could not remove project workspace dir %s: %s", project_id, e)
    return Response(status_code=204)


async def get_project_state_service(*, db, project_id: str, user_id: str, load_state: Callable[[str], dict], quality_verdict: Callable[[float], str], quality_badge: Callable[[float], str]) -> dict:
    project = await db.projects.find_one({"id": project_id, "user_id": user_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = load_state(project_id)
    quality_score = project.get("quality_score")
    if quality_score and isinstance(quality_score, dict):
        overall = quality_score.get("overall_score", 0)
        breakdown = quality_score.get("breakdown") or {}
        state["quality"] = {
            "overall_score": overall,
            "display": f"{round(overall / 10, 1)}/10",
            "verdict": quality_verdict(overall),
            "breakdown": breakdown,
            "badge": quality_badge(overall),
            "deploy_gated": overall < 60,
        }
    elif quality_score is not None:
        state["quality"] = {
            "overall_score": quality_score,
            "display": f"{round(float(quality_score) / 10, 1)}/10",
        }
    return {"state": state}


async def get_build_events_snapshot_service(*, db, project_id: str, user_id: str, build_events: dict) -> dict:
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    events = build_events.get(project_id, [])
    if not events and project.get("build_events"):
        events = project.get("build_events", [])
        build_events[project_id] = list(events)
    return {"project_id": project_id, "events": events, "count": len(events)}


async def stream_build_events_service(*, db, project_id: str, user_id: str, last_id: int, build_events: Mapping[str, list], sleep_fn: Callable[[float], Any] | None = None) -> StreamingResponse:
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    sleep = sleep_fn or asyncio.sleep

    async def event_generator():
        seen = last_id
        while True:
            events = build_events.get(project_id, [])
            for ev in events:
                if ev.get("id", 0) >= seen:
                    yield f"data: {json.dumps(ev)}\n\n"
                    seen = ev.get("id", 0) + 1
            project_doc = await db.projects.find_one({"id": project_id, "user_id": user_id}, {"status": 1})
            if project_doc and project_doc.get("status") in ("completed", "failed"):
                yield f"data: {json.dumps({'type': 'stream_end', 'status': project_doc['status']})}\n\n"
                break
            await sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
