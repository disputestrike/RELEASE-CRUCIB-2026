"""
WebSocket /ws/events — incremental job_events feed in PDF-normalized envelope.
Auth: ?token= JWT (same pattern as preview-watch).

The in-app workspace (`CrucibAIWorkspace`) subscribes via SSE (`useJobStream` →
`/api/jobs/{id}/stream`). This socket is for external or native clients that want
the same normalized envelope over WebSocket without duplicating that stream in React.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspace-ws"])


def _normalize_row(job_id: str, row: dict) -> dict:
    payload_raw = row.get("payload_json") or "{}"
    if isinstance(payload_raw, str):
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            payload = {"raw": payload_raw}
    else:
        payload = payload_raw or {}
    ts = row.get("created_at")
    try:
        ms = int(ts.timestamp() * 1000) if ts is not None and hasattr(ts, "timestamp") else int(__import__("time").time() * 1000)
    except Exception:
        ms = int(__import__("time").time() * 1000)
    et = row.get("event_type") or "event"
    return {"type": et, "jobId": job_id, "timestamp": ms, "payload": payload, "id": row.get("id")}


@router.websocket("/ws/events")
async def workspace_events_ws(websocket: WebSocket):
    import jwt

    from ....db_pg import get_pg_pool    from ....server import JWT_ALGORITHM, JWT_SECRET, _assert_job_owner_match, _get_orchestration, db
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0}) if db is not None else None
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, TypeError):
        user = None
    if not user or user.get("suspended"):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    job_id: Optional[str] = None
    last_since_id: Optional[str] = None
    seen_ids: set[str] = set()

    try:
        while True:
            recv_task = asyncio.create_task(websocket.receive_text())
            wait_task = asyncio.create_task(asyncio.sleep(1.25))
            done, pending = await asyncio.wait({recv_task, wait_task}, return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
            if recv_task in done and not recv_task.cancelled():
                try:
                    raw = recv_task.result()
                    data = json.loads(raw)
                    if data.get("action") == "subscribe" and data.get("jobId"):
                        job_id = str(data["jobId"])
                        last_since_id = None
                        seen_ids.clear()
                    elif data.get("action") == "unsubscribe":
                        job_id = None
                except (json.JSONDecodeError, WebSocketDisconnect):
                    raise
                except Exception as exc:
                    logger.debug("ws/events client message: %s", exc)

            if not job_id:
                continue

            runtime_state, *_ = _get_orchestration()
            pool = await get_pg_pool()
            runtime_state.set_pool(pool)
            job = await runtime_state.get_job(job_id)
            if not job:
                await websocket.send_json({"type": "error", "jobId": job_id, "payload": {"detail": "job_not_found"}})
                job_id = None
                continue
            try:
                _assert_job_owner_match(job.get("user_id"), user)
            except HTTPException:
                await websocket.send_json({"type": "error", "jobId": job_id, "payload": {"detail": "forbidden"}})
                job_id = None
                continue

            rows = await runtime_state.get_job_events(job_id, since_id=last_since_id, limit=100)
            for row in rows:
                rid = row.get("id")
                if not rid or rid in seen_ids:
                    continue
                seen_ids.add(rid)
                last_since_id = rid
                await websocket.send_json(_normalize_row(job_id, row))
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.warning("ws/events closed: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
