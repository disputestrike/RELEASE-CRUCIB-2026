#!/usr/bin/env python3
"""
Pre-release smoke: import the FastAPI app, enumerate routes, hit safe public checks.
Run from repo root:  python scripts/pre_release_sanity.py
Exits 0 on success, 1 if any check fails.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Repo root on path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("JWT_SECRET", "pre-release-sanity-32-chars-minimum-ok")
os.environ.setdefault("CRUCIBAI_DEV", "1")
os.environ.setdefault("CRUCIBAI_TEST", "1")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")


def main() -> int:
    from backend.server import app

    routes = [getattr(r, "path", None) for r in app.routes]
    routes = [p for p in routes if p]
    print(f"ok: app loaded, {len(routes)} route paths registered")

    if len(routes) < 20:
        print("fail: unexpected route count (too few)", file=sys.stderr)
        return 1

    from fastapi.testclient import TestClient

    client = TestClient(app)
    failed: list[str] = []

    def check(method: str, path: str, accept: set[int] | None = None) -> None:
        accept = accept or {200, 401, 403, 404, 405, 422}
        try:
            if method == "GET":
                r = client.get(path)
            else:
                r = client.post(path, json={})
            if r.status_code not in accept:
                failed.append(f"{method} {path} -> {r.status_code} (body head: {r.text[:120]!r})")
        except Exception as e:  # noqa: BLE001
            failed.append(f"{method} {path} -> exception: {e!r}")

    # Public / health-style endpoints (tolerate unconfigured subsystems)
    for p in ("/api/health", "/health", "/api/debug/routes/health", "/api/settings/capabilities"):
        if any(p == x or (x and p in str(x)) for x in routes):
            pass
    check("GET", "/api/health", {200})
    check("GET", "/api/settings/capabilities", {200, 401, 404, 500})
    check("GET", "/api/billing/config", {200})
    check("GET", "/api/cost/governance", {200})
    check("GET", "/api/trust/enterprise-readiness", {200})
    check("GET", "/api/trust/public-proof-readiness", {200})

    if failed:
        print("failures:", file=sys.stderr)
        for f in failed:
            print(" ", f, file=sys.stderr)
        return 1
    print("ok: sample HTTP probes completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
