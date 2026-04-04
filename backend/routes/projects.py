"""Project management routes — stubs that redirect to server.py implementations.
All real project logic is in /api/projects/* endpoints registered directly in server.py.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/projects", tags=["projects"])

_MSG = {"detail": "Use /api/projects endpoints. Real implementations are in server.py."}

@router.get("/")
async def list_projects():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/")
async def create_project():
    return JSONResponse(status_code=200, content=_MSG)

@router.get("/{project_id}")
async def get_project(project_id: str):
    return JSONResponse(status_code=200, content=_MSG)

@router.put("/{project_id}")
async def update_project(project_id: str):
    return JSONResponse(status_code=200, content=_MSG)

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    return JSONResponse(status_code=200, content=_MSG)
