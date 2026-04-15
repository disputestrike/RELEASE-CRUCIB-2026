from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse


RuntimeStateGetter = Callable[[], Any]
PoolGetter = Callable[[], Awaitable[Any]]
AssertOwner = Callable[[Optional[str], Optional[dict]], None]
ProofGetter = Callable[[], Any]
SubscribeCallable = Callable[[str], Awaitable[Any]]
UnsubscribeCallable = Callable[[str, Any], Awaitable[None]]
StoredEventsCallable = Callable[..., Awaitable[list]]


async def _load_job(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: AssertOwner,
):
    runtime_state = runtime_state_getter()
    pool = await pool_getter()
    runtime_state.set_pool(pool)
    job = await runtime_state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    assert_owner(job.get("user_id"), user)
    return runtime_state, pool, job


async def get_job_steps_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: AssertOwner,
) -> Dict[str, Any]:
    runtime_state, _pool, _job = await _load_job(
        job_id=job_id,
        user=user,
        runtime_state_getter=runtime_state_getter,
        pool_getter=pool_getter,
        assert_owner=assert_owner,
    )
    steps = await runtime_state.get_steps(job_id)
    return {"success": True, "steps": steps, "count": len(steps)}


async def get_job_plan_draft_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: AssertOwner,
) -> Dict[str, Any]:
    _runtime_state, pool, _job = await _load_job(
        job_id=job_id,
        user=user,
        runtime_state_getter=runtime_state_getter,
        pool_getter=pool_getter,
        assert_owner=assert_owner,
    )
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT plan_json FROM build_plans WHERE job_id = $1 ORDER BY created_at DESC LIMIT 1",
            job_id,
        )
    if not row or not row.get("plan_json"):
        return {"success": True, "plan": None}
    raw = row["plan_json"]
    plan = json.loads(raw) if isinstance(raw, str) else raw
    return {"success": True, "plan": plan}


async def get_job_events_service(
    *,
    job_id: str,
    user: dict,
    since_id: Optional[str],
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: AssertOwner,
) -> Dict[str, Any]:
    runtime_state, _pool, _job = await _load_job(
        job_id=job_id,
        user=user,
        runtime_state_getter=runtime_state_getter,
        pool_getter=pool_getter,
        assert_owner=assert_owner,
    )
    events = await runtime_state.get_job_events(job_id, since_id=since_id)
    for event in events:
        try:
            event["payload"] = json.loads(event.get("payload_json") or "{}")
        except Exception:
            event["payload"] = {}
    return {"success": True, "events": events, "count": len(events)}


async def get_job_proof_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: AssertOwner,
    proof_service_getter: ProofGetter,
) -> Dict[str, Any]:
    _runtime_state, pool, _job = await _load_job(
        job_id=job_id,
        user=user,
        runtime_state_getter=runtime_state_getter,
        pool_getter=pool_getter,
        assert_owner=assert_owner,
    )
    proof_service = proof_service_getter()
    proof_service.set_pool(pool)
    proof = await proof_service.get_proof(job_id)
    return {"success": True, **proof}


async def build_job_stream_response_service(
    *,
    job_id: str,
    user: dict,
    runtime_state_getter: RuntimeStateGetter,
    pool_getter: PoolGetter,
    assert_owner: AssertOwner,
    subscribe: SubscribeCallable,
    unsubscribe: UnsubscribeCallable,
    get_stored_events: StoredEventsCallable,
    heartbeat_seconds: float = 30.0,
) -> StreamingResponse:
    runtime_state, pool, _job = await _load_job(
        job_id=job_id,
        user=user,
        runtime_state_getter=runtime_state_getter,
        pool_getter=pool_getter,
        assert_owner=assert_owner,
    )

    async def event_generator():
        queue = await subscribe(job_id)
        try:
            stored = await get_stored_events(job_id, limit=50)
            for ev in stored:
                payload_str = json.dumps(
                    {
                        "type": ev.get("event_type"),
                        "job_id": ev.get("job_id"),
                        "step_id": ev.get("step_id"),
                        "payload": _safe_payload(ev.get("payload_json")),
                        "ts": str(ev.get("created_at", "")),
                    }
                )
                yield f"data: {payload_str}\n\n"

            yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("job_completed", "job_failed", "job_cancelled"):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id})}\n\n"
        finally:
            await unsubscribe(job_id, queue)

    # keep runtime_state/pool referenced for parity with existing wiring
    _ = runtime_state, pool
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _safe_payload(payload_json: Any) -> Dict[str, Any]:
    try:
        return json.loads(payload_json or "{}")
    except Exception:
        return {}
