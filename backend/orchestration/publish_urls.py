"""Published generated-app URL helpers."""

from __future__ import annotations

import os
import re
from typing import Optional


def safe_publish_id(value: str) -> str:
    """Return a URL-safe id for published build paths."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", (value or "").strip())
    return safe[:120]


def public_base_url_from_env() -> Optional[str]:
    """Resolve the public CrucibAI base URL without exposing secrets."""
    for key in (
        "CRUCIBAI_PUBLIC_BASE_URL",
        "PUBLIC_BASE_URL",
        "API_BASE_URL",
        "FRONTEND_URL",
    ):
        value = (os.environ.get(key) or "").strip().rstrip("/")
        if (
            value
            and not value.startswith("http://localhost")
            and not value.startswith("http://127.0.0.1")
        ):
            return value
    railway_domain = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip().strip("/")
    if railway_domain:
        return "https://" + railway_domain.removeprefix("https://").removeprefix(
            "http://"
        )
    railway_static = (os.environ.get("RAILWAY_STATIC_URL") or "").strip().rstrip("/")
    if railway_static:
        return (
            railway_static
            if railway_static.startswith("http")
            else "https://" + railway_static
        )
    return None


def published_app_url(
    job_id: str, public_base_url: Optional[str] = None
) -> Optional[str]:
    """Return the public in-platform generated-app URL, if a base URL is configured."""
    base = (public_base_url or public_base_url_from_env() or "").strip().rstrip("/")
    safe_id = safe_publish_id(job_id)
    if not base or not safe_id:
        return None
    return f"{base}/published/{safe_id}/"
