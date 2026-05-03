from __future__ import annotations

from typing import Any

from .paypal_billing import user_has_access


async def userHasAccess(user_id: str, product_id: str, db: Any | None = None) -> bool:
    """Compatibility helper for product access checks across routes.

    Accepts an optional db for tests/routes; otherwise reads the initialized app db.
    """
    if db is None:
        from ..deps import get_db

        db = get_db()
    if db is None:
        return False
    return await user_has_access(db, user_id, product_id)

