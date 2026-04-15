"""Spawn routes — parallel agent execution."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
router = APIRouter()

def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous"}
        return noop

class SpawnRequest(BaseModel):
    jobId: str
    task: str
    config: dict = {}
    context: dict = {}

class ScenarioRequest(BaseModel):
    jobId: str
    scenario: str
    populationSize: int = 32

@router.post("/api/spawn/run")
async def spawn_run(req: SpawnRequest, user: dict = Depends(_get_auth())):
    from adapter.services.spawn_engine import SpawnEngine
    engine = SpawnEngine(req.jobId)
    ctx = {**req.context, "user_id": user.get("id", ""), "project_id": req.jobId}
    return await engine.spawn(req.task, req.config, ctx)

@router.post("/api/spawn/scenario")
async def spawn_scenario(req: ScenarioRequest, user: dict = Depends(_get_auth())):
    from adapter.services.spawn_engine import SpawnEngine
    engine = SpawnEngine(req.jobId)
    return await engine.inject_scenario(req.scenario, req.populationSize)
