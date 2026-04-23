"""
CrucibAI workspace 10/10 adapter — REST endpoints expected by the integrated workspace UI.
Folds PDF "adapter" concepts into the existing FastAPI app (no second ASGI app).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workspace-ui"])


def _get_auth():
    from deps import get_current_user

    return get_current_user


def _assert_owner(job_owner_id: Optional[str], user: Optional[dict]) -> None:
    uid = str((user or {}).get("id") or "").strip()
    owner = str(job_owner_id or "").strip()
    if owner and uid and owner != uid:
        raise HTTPException(status_code=403, detail="Forbidden")


async def _load_job_with_fallback(job_id: str, user: dict) -> Dict[str, Any]:
    """Prefer orchestration runtime if available; fall back to DB jobs table."""
    runtime_state = None
    try:
        from db_pg import get_pg_pool
        from server import _get_orchestration

        candidate = _get_orchestration()
        if isinstance(candidate, tuple) and candidate and hasattr(candidate[0], "get_job"):
            runtime_state = candidate[0]
            pool = await get_pg_pool()
            runtime_state.set_pool(pool)
            job = await runtime_state.get_job(job_id)
            if job:
                _assert_owner(job.get("user_id"), user)
                return job
    except Exception:
        runtime_state = None

    from db_pg import get_db

    db = await get_db()
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_owner(job.get("user_id"), user)
    return job


async def _persist_spawn_log(job_id: str, user_id: str, kind: str, payload: Dict[str, Any]) -> None:
    try:
        from db_pg import get_db

        db = await get_db()
        await db.project_logs.insert_one(
            {
                "id": str(uuid.uuid4()),
                "project_id": job_id,
                "job_id": job_id,
                "user_id": user_id,
                "kind": kind,
                "payload": payload,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        return None


class SpawnRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    task: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class SkillGenerateBody(BaseModel):
    description: str = Field(..., min_length=3, max_length=8000)


class SpawnSimulateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    scenario: str = Field(..., min_length=3, max_length=4000)
    population_size: int = Field(default=24, ge=3, le=256)
    rounds: int = Field(default=3, ge=1, le=8)
    agent_roles: List[str] = Field(default_factory=list)
    priors: Dict[str, float] = Field(default_factory=dict)


@router.post("/spawn/run")
async def spawn_run(body: SpawnRunBody, user: dict = Depends(_get_auth())):
    from services.events import event_bus
    from services.runtime.subagent_orchestrator import SubagentOrchestrator

    job = await _load_job_with_fallback(body.job_id, user)
    job_id = body.job_id
    uid = str((user or {}).get("id") or job.get("user_id") or "")

    event_bus.emit(
        "swarm.started",
        {
            "job_id": job_id,
            "config": body.config,
            "task": (body.task or "")[:180],
        },
    )

    orchestrator = SubagentOrchestrator(job_id=job_id, user_id=uid)
    out = await orchestrator.run(
        task=body.task or "parallel workspace probe",
        config=body.config,
        context=body.context,
    )

    result = {
        "consensus": out.get("consensus") or {},
        "confidence": out.get("confidence") or 0.0,
        "disagreements": [],
        "recommendedAction": out.get("recommendedAction") or "Proceed",
        "subagentResults": out.get("subagentResults") or [],
        "swarm": {
            "mode": str((body.config or {}).get("mode") or "swan"),
            "strategy": str((body.config or {}).get("strategy") or "") or None,
            "requested_branches": out.get("requestedBranches"),
            "actual_branches": out.get("actualBranches"),
            "hard_limit": out.get("hardLimit"),
            "unbounded": out.get("hardLimit") is None,
        },
    }

    event_bus.emit(
        "swarm.completed",
        {
            "job_id": job_id,
            "requested_branches": out.get("requestedBranches"),
            "actual_branches": out.get("actualBranches"),
            "subagent_count": len(result["subagentResults"]),
        },
    )
    await _persist_spawn_log(job_id, uid, "swarm.completed", result)
    return result


@router.post("/spawn/simulate")
async def spawn_simulate(body: SpawnSimulateBody, user: dict = Depends(_get_auth())):
    """Run scenario simulation and return updates + recommendation + personas."""
    from services.events import event_bus
    from services.runtime.simulation_orchestrator import SimulationOrchestrator

    job = await _load_job_with_fallback(body.job_id, user)
    uid = str((user or {}).get("id") or job.get("user_id") or "")

    orchestrator = SimulationOrchestrator(job_id=body.job_id, user_id=uid)
    event_bus.emit(
        "simulation.started",
        {
            "job_id": body.job_id,
            "scenario": body.scenario,
            "population_size": body.population_size,
            "rounds": body.rounds,
        },
    )
    out = await orchestrator.run(
        scenario=body.scenario,
        population_size=body.population_size,
        rounds=body.rounds,
        agent_roles=body.agent_roles,
        priors=body.priors,
    )

    for update in out.get("updates") or []:
        event_bus.emit(
            "simulation.update",
            {
                "job_id": body.job_id,
                "simulation_id": out.get("simulationId"),
                **update,
            },
        )

    event_bus.emit(
        "simulation.completed",
        {
            "job_id": body.job_id,
            "simulation_id": out.get("simulationId"),
            "recommendation": out.get("recommendation"),
            "consensus_reached": out.get("consensus_reached"),
        },
    )

    return {
        "success": True,
        "jobId": body.job_id,
        **out,
    }


@router.post("/spawn/simulate/stream")
async def spawn_simulate_stream(body: SpawnSimulateBody, user: dict = Depends(_get_auth())):
    """Stream simulation updates as NDJSON lines for progressive UI rendering."""
    from services.events import event_bus
    from services.runtime.simulation_orchestrator import SimulationOrchestrator

    job = await _load_job_with_fallback(body.job_id, user)
    uid = str((user or {}).get("id") or job.get("user_id") or "")
    orchestrator = SimulationOrchestrator(job_id=body.job_id, user_id=uid)

    async def _gen():
        async for line in orchestrator.stream_ndjson(
            scenario=body.scenario,
            population_size=body.population_size,
            rounds=body.rounds,
            agent_roles=body.agent_roles,
            priors=body.priors,
        ):
            try:
                payload = json.loads(line)
                event_bus.emit(payload.get("type") or "simulation.update", payload)
            except Exception:
                pass
            yield line
            await asyncio.sleep(0.05)

    return StreamingResponse(_gen(), media_type="application/x-ndjson")


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s[:48] or "skill")[:48]


@router.post("/skills/generate")
async def skills_generate(body: SkillGenerateBody, user: dict = Depends(_get_auth())):
    """
    Deterministic structured skill from natural language (no external LLM required).
    Stored client-side; optional server persistence can be added later.
    """
    desc = body.description.strip()
    tokens = [t.lower() for t in re.split(r"\W+", desc) if len(t) > 2][:8]
    skill_id = _slugify(desc[:60])
    return {
        "id": skill_id,
        "name": desc[:80],
        "description": desc,
        "trigger": tokens[:5],
        "context": ["prompt"],
        "steps": [
            {"id": "1", "action": "analyze", "agent": "architect", "timeout": 30000, "retry": 2},
            {"id": "2", "action": "execute", "agent": "orchestrator", "timeout": 600000, "retry": 0},
        ],
        "successCriteria": ["build_complete"],
        "artifacts": [],
        "followUp": [],
        "owner": str(user.get("id")),
    }
