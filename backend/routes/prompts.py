"""Public endpoints for introspecting loaded system-prompt preambles."""
from fastapi import APIRouter, HTTPException

from backend.prompts.loader import list_available, load_preamble

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("")
async def list_prompts():
    return {"prompts": list_available()}


@router.get("/{name}")
async def get_prompt(name: str):
    body = load_preamble(name)
    if not body:
        raise HTTPException(status_code=404, detail=f"preamble '{name}' not found")
    return {"name": name, "body": body, "bytes": len(body)}
