"""Auth routes — stubs that redirect to server.py implementations.
All real auth logic is in /api/auth/* endpoints registered directly in server.py.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_MSG = {"detail": "Use /api/auth endpoints. Real implementations are in server.py."}

@router.post("/login")
async def login():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/logout")
async def logout():
    return JSONResponse(status_code=200, content=_MSG)

@router.get("/me")
async def get_current_user():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/refresh")
async def refresh_token():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/mfa/setup")
async def setup_mfa():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/mfa/verify")
async def verify_mfa():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/forgot-password")
async def forgot_password():
    return JSONResponse(status_code=200, content=_MSG)

@router.post("/reset-password")
async def reset_password():
    return JSONResponse(status_code=200, content=_MSG)
