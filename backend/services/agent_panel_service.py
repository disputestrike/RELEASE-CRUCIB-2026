from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from fastapi import HTTPException


async def get_agents_service(*, agent_definitions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {"agents": list(agent_definitions)}


async def get_agent_status_service(*, db: Any, project_id: str, user: Dict[str, Any], agent_definitions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    statuses = await db.agent_status.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    if not statuses:
        return {
            "statuses": [
                {
                    "agent_name": a["name"],
                    "status": "idle",
                    "progress": 0,
                    "tokens_used": 0,
                }
                for a in agent_definitions
            ]
        }
    return {"statuses": statuses}


async def get_agents_activity_service(*, db: Any, user: Optional[Dict[str, Any]], limit: int = 20, fetch_limit: int = 30) -> Dict[str, Any]:
    if not user:
        return {"activities": []}
    cursor = (
        db.chat_history.find(
            {"user_id": user["id"]},
            {
                "session_id": 1,
                "message": 1,
                "model": 1,
                "tokens_used": 1,
                "created_at": 1,
            },
        )
        .sort("created_at", -1)
        .limit(fetch_limit)
    )
    activities = []
    seen = set()
    async for row in cursor:
        sid = row.get("session_id") or "default"
        key = (sid, (row.get("created_at") or "")[:19])
        if key in seen:
            continue
        seen.add(key)
        activities.append(
            {
                "session_id": sid,
                "message": (row.get("message") or "")[:80],
                "model": row.get("model"),
                "tokens_used": row.get("tokens_used", 0),
                "created_at": row.get("created_at"),
            }
        )
    return {"activities": activities[:limit]}
