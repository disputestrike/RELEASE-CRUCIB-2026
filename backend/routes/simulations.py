from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.simulation.models import SimulationCreate, SimulationFeedback, SimulationRunRequest
from ..services.simulation.reality_engine import reality_engine
from ..services.simulation.repository import new_id, now_iso, repository

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _user_id(user: dict) -> str:
    return str((user or {}).get("id") or (user or {}).get("user_id") or "guest")


async def _require_owned_simulation(simulation_id: str, user: dict) -> Dict[str, Any]:
    sim = await repository.find_one("simulations", {"id": simulation_id})
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if str(sim.get("user_id") or "") not in {"", _user_id(user)}:
        raise HTTPException(status_code=403, detail="Forbidden")
    return sim


@router.post("")
async def create_simulation(body: SimulationCreate, user: dict = Depends(_get_auth())):
    simulation = await reality_engine.create_simulation(
        user_id=_user_id(user),
        prompt=body.prompt,
        assumptions=body.assumptions,
        attachments=body.attachments,
        metadata=body.metadata,
    )
    return {"success": True, "simulation": simulation}


async def _run_simulation_for_id(simulation_id: str, body: SimulationRunRequest, user: dict) -> Dict[str, Any]:
    sim = await repository.find_one("simulations", {"id": simulation_id})
    if sim and str(sim.get("user_id") or "") not in {"", _user_id(user)}:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not sim:
        if not (body.prompt or "").strip():
            raise HTTPException(status_code=404, detail="Simulation not found")
        sim = {
            "id": simulation_id,
            "user_id": _user_id(user),
            "prompt": body.prompt,
            "assumptions": body.assumptions,
            "attachments": body.attachments,
        }
    prompt = (body.prompt or sim.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Simulation prompt is required")
    result = await reality_engine.run_simulation(
        simulation_id=simulation_id,
        user_id=_user_id(user),
        prompt=prompt,
        assumptions=body.assumptions or sim.get("assumptions") or [],
        attachments=body.attachments or sim.get("attachments") or [],
        depth=body.depth,
        use_live_evidence=body.use_live_evidence,
        population_size=body.population_size,
        evidence_depth=body.evidence_depth,
        rounds=body.rounds,
        agent_count=body.agent_count,
        metadata=body.metadata,
    )
    return {"success": True, **result}


@router.post("/run")
async def run_simulation_flat(body: SimulationRunRequest, user: dict = Depends(_get_auth())):
    simulation_id = (body.simulation_id or "").strip()
    if not simulation_id:
        raise HTTPException(status_code=400, detail="simulation_id is required")
    return await _run_simulation_for_id(simulation_id, body, user)


@router.post("/{simulation_id}/run")
async def run_simulation(simulation_id: str, body: SimulationRunRequest, user: dict = Depends(_get_auth())):
    return await _run_simulation_for_id(simulation_id, body, user)


@router.get("/history")
async def simulation_history(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(_get_auth()),
):
    rows = await repository.list("simulations", {"user_id": _user_id(user)}, limit=limit)
    return {"success": True, "simulations": rows, "count": len(rows)}


@router.get("/{simulation_id}")
async def get_simulation(simulation_id: str, user: dict = Depends(_get_auth())):
    sim = await _require_owned_simulation(simulation_id, user)
    runs = await repository.list("simulation_runs", {"simulation_id": simulation_id}, limit=50)
    return {"success": True, "simulation": sim, "runs": runs}


@router.get("/{simulation_id}/runs/{run_id}")
async def get_simulation_run(simulation_id: str, run_id: str, user: dict = Depends(_get_auth())):
    await _require_owned_simulation(simulation_id, user)
    details = await reality_engine.get_run_details(simulation_id, run_id)
    if not details.get("run"):
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return {"success": True, **details}


@router.get("/{simulation_id}/runs/{run_id}/events")
async def get_simulation_events(
    simulation_id: str,
    run_id: str,
    user: dict = Depends(_get_auth()),
):
    await _require_owned_simulation(simulation_id, user)
    rows = await repository.list("simulation_events", {"run_id": run_id}, limit=500)
    return {"success": True, "events": rows, "count": len(rows), "streaming": "polling"}


@router.post("/{simulation_id}/runs/{run_id}/feedback")
async def simulation_feedback(
    simulation_id: str,
    run_id: str,
    body: SimulationFeedback,
    user: dict = Depends(_get_auth()),
):
    await _require_owned_simulation(simulation_id, user)
    doc = {
        "id": new_id("sim_feedback"),
        "simulation_id": simulation_id,
        "run_id": run_id,
        "user_id": _user_id(user),
        "rating": body.rating,
        "comment": body.comment,
        "metadata": body.metadata,
        "created_at": now_iso(),
    }
    await repository.insert("audit_log", {"id": doc["id"], "event": "simulation_feedback", **doc})
    return {"success": True, "feedback": doc}
