"""Content fingerprinting and retrieval timestamps for auditable evidence rows."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fingerprint_text(text: str) -> str:
    raw = (text or "").encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()
