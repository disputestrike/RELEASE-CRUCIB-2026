"""Project management routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/")
async def list_projects():
    """List all projects for user"""
    pass

@router.post("/")
async def create_project(name: str, description: str = None):
    """Create new project"""
    pass

@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    pass

@router.put("/{project_id}")
async def update_project(project_id: str, name: str = None, description: str = None):
    """Update project"""
    pass

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project"""
    pass
