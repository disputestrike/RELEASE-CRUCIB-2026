from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict


STRICT_RATE_LIMITS = {
    "/api/auth/login": 10,
    "/api/auth/register": 10,
}


class RateLimitMiddleware:
    """
    Lightweight compatibility middleware helper used by legacy tests.
    The active API stack currently relies on route-level auth guards.
    """

    def __init__(self):
        self._window_seconds = 60
        self._default_limit = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _check_limit(self, key: str, limit: int | None = None) -> bool:
        now = time.time()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self._window_seconds:
            bucket.popleft()
        cap = limit or self._default_limit
        if len(bucket) >= cap:
            return False
        bucket.append(now)
        return True
