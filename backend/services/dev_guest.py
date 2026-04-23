"""
In-process guest users when CRUCIBAI_DEV=1 and PostgreSQL is unavailable.

Allows local UI validation (e.g. /app/workspace) without Docker; not for production.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_users: Dict[str, Dict[str, Any]] = {}


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    u = _users.get(user_id)
    if not u:
        return None
    return dict(u)


def update_user(user_id: str, fields: Dict[str, Any]) -> bool:
    if user_id not in _users:
        return False
    _users[user_id].update(fields)
    return True


async def create_guest_user(
    *,
    create_token,
    guest_tier_credits: int,
    credits_per_token: int,
) -> dict:
    user_id = str(uuid.uuid4())
    email = f"guest-{user_id[:8]}@crucibai.guest"
    user = {
        "id": user_id,
        "email": email,
        "password": "",
        "name": "Guest",
        "token_balance": guest_tier_credits * credits_per_token,
        "credit_balance": guest_tier_credits,
        "plan": "free",
        "auth_provider": "guest",
        "workspace_mode": "simple",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users[user_id] = user
    token = create_token(user_id)
    return {"token": token, "user": {k: v for k, v in user.items() if k not in ("password", "_id")}}
