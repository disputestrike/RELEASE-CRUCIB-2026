"""
Audit log: immutable trail of user actions for compliance (enterprise).
"""

from datetime import datetime, timezone
from typing import Optional, Any, Dict, List


class AuditLogger:
    """Log all user actions for compliance and audit trail."""

    def __init__(self, db):
        self.db = db

    async def log(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Append one audit entry (immutable)."""
        now = datetime.now(timezone.utc)
        entry = {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
            "status": status,
            "details": details,
            "timestamp": now.isoformat(),
            "date": now.date().isoformat(),
        }
        result = await self.db.audit_log.insert_one(entry)
        if isinstance(result, dict):
            return result.get("inserted_id") or result.get("id")
        return getattr(result, "inserted_id", None)

    async def get_user_logs(
        self,
        user_id: str,
        limit: int = 100,
        skip: int = 0,
        action_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get audit logs for a user."""
        query = {"user_id": user_id}
        if action_filter:
            query["action"] = action_filter
        cursor = (
            self.db.audit_log.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        )
        logs = await cursor.to_list(length=limit)
        total = await self.db.audit_log.count_documents(query)
        for log in logs:
            if "_id" in log:
                log["id"] = str(log.pop("_id"))
            ts = log.get("timestamp")
            if ts and hasattr(ts, "isoformat"):
                log["timestamp"] = ts.isoformat()
        return {"logs": logs, "total": total, "limit": limit, "skip": skip}

    async def export_logs(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json",
    ) -> str:
        """Export audit logs for compliance (JSON or CSV)."""
        query = {
            "user_id": user_id,
            "timestamp": {"$gte": start_date, "$lte": end_date},
        }
        cursor = self.db.audit_log.find(query).sort("timestamp", -1)
        logs = await cursor.to_list(length=10000)
        if format == "csv":
            import csv
            import io

            out = io.StringIO()
            w = csv.DictWriter(
                out,
                fieldnames=[
                    "timestamp",
                    "action",
                    "resource_type",
                    "resource_id",
                    "status",
                    "ip_address",
                ],
            )
            w.writeheader()
            for log in logs:
                ts = log.get("timestamp")
                w.writerow(
                    {
                        "timestamp": ts.isoformat() if ts else "",
                        "action": log.get("action", ""),
                        "resource_type": log.get("resource_type", ""),
                        "resource_id": log.get("resource_id", ""),
                        "status": log.get("status", ""),
                        "ip_address": log.get("ip_address", ""),
                    }
                )
            return out.getvalue()
        import json

        out_list = []
        for log in logs:
            d = dict(log)
            d["id"] = str(d.pop("_id", ""))
            ts = d.get("timestamp")
            if hasattr(ts, "isoformat"):
                d["timestamp"] = ts.isoformat()
            out_list.append(d)
        return json.dumps(out_list, indent=2)
