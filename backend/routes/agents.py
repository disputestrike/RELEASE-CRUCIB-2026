"""Agent management routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/")
async def list_agents():
    """List all available agents"""
    pass

@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    pass

@router.post("/{agent_id}/execute")
async def execute_agent(agent_id: str, input_data: dict):
    """Execute an agent"""
    pass

@router.get("/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str):
    """Get agent performance metrics"""
    pass
