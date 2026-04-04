"""Agent management routes — stubs that redirect to server.py implementations.
All real agent logic is in /api/agents/* endpoints registered directly in server.py.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/agents", tags=["agents"])

_MSG = {"detail": "Use /api/agents endpoints. These route files are placeholder scaffolds; real implementations are in server.py."}

@router.get("/")
async def list_agents():
    """List all available agents — see GET /api/agents"""
    return JSONResponse(status_code=200, content=_MSG)

@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details — see GET /api/agents/{agent_id}"""
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/{agent_id}/execute")
async def execute_agent(agent_id: str, input_data: dict = None):
    """Execute an agent — see POST /api/agents/{agent_id}/run"""
    return JSONResponse(status_code=200, content=_MSG)

@router.get("/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str):
    """Get agent performance metrics — see GET /api/agents/{agent_id}/runs"""
    return JSONResponse(status_code=200, content=_MSG)
