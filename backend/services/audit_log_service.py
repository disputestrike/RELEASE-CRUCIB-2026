from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from fastapi.responses import Response


async def get_audit_logs_service(*, user: dict, audit_logger: Any, limit: int, skip: int, action: str | None):
    if not audit_logger:
        return {"logs": [], "total": 0, "limit": limit, "skip": skip}
    return await audit_logger.get_user_logs(user["id"], limit=limit, skip=skip, action_filter=action)


async def export_audit_logs_service(*, user: dict, audit_logger: Any, start_date: str, end_date: str, format: str):
    if not audit_logger:
        raise HTTPException(status_code=503, detail="Audit log not available")
    try:
        start = datetime.strptime(start_date.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date.strip()[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    result = await audit_logger.export_logs(user["id"], start, end, format=format)
    if format == "json":
        return Response(content=result, media_type="application/json")
    return Response(
        content=result,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit-log-{start_date}-{end_date}.csv"},
    )
