"""Monitoring routes — stubs that redirect to server.py implementations."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

_MSG = {"detail": "Use /api/monitoring endpoints. Real implementations are in server.py."}

@router.get("/health")
async def health():
    return JSONResponse(status_code=200, content={"status": "ok"})

@router.get("/metrics")
async def metrics():
    return JSONResponse(status_code=200, content=_MSG)
