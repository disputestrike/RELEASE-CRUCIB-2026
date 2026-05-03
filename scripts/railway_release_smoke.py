#!/usr/bin/env python3
"""Live Railway smoke check after deploy.

Requires a reachable backend URL (APP_URL, BACKEND_PUBLIC_URL, or --app-url).

  python scripts/railway_release_smoke.py --app-url https://your-app.up.railway.app

Exit 0 when public HTTP probes succeed; prints a short manual checklist either way.

Does not submit a full swarm job (needs auth/session); pair this with manual UI QA.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_RAILWAY_URL = "https://vigilant-youth-production-5aa6.up.railway.app"
PUBLIC_PROBES = (
    "/api/health",
    "/api/settings/capabilities",
    "/api/billing/config",
    "/api/cost/governance",
    "/api/trust/enterprise-readiness",
    "/api/trust/public-proof-readiness",
    "/api/trust/summary",
    "/api/doctor/routes",
)


def fetch_json(base_url: str, path: str, timeout: float) -> Tuple[int, Any]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                data = {"raw": raw[:800]}
            return resp.getcode(), data
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else None
        except json.JSONDecodeError:
            data = {"raw": text[:800]}
        return exc.code, data
    except (URLError, TimeoutError, OSError) as exc:
        return 0, {"error": repr(exc)}


def summarize_response(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    summary: Dict[str, Any] = {}
    for key in ("status", "ok", "provider", "configured", "route_count", "summary", "checks", "error", "message"):
        if key in data:
            summary[key] = data[key]
    if not summary:
        summary["keys"] = sorted(list(data.keys()))[:20]
    return summary


def manual_checklist() -> str:
    return """MANUAL ACCEPTANCE (complete after automated smoke passes)
- [ ] Deploy on Railway is the expected git commit (sha / branch).
- [ ] Provider keys, PayPal keys, JWT secret, proof HMAC, and DATABASE_URL are set in Railway variables.
- [ ] Run one agent-swarm build with a real workspace path; verify `tool_loop` on results.
- [ ] Check `anthropic_usage` / `tokens_used` look plausible in agent response metadata.
- [ ] End-to-end user path: signup or guest, goal entry, job completes or clear error.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app-url",
        default=(
            os.environ.get("APP_URL", "").strip()
            or os.environ.get("CRUCIBAI_PUBLIC_BASE_URL", "").strip()
            or os.environ.get("BACKEND_PUBLIC_URL", "").strip()
            or os.environ.get("RAILWAY_PUBLIC_URL", "").strip()
            or DEFAULT_RAILWAY_URL
        ),
    )
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Only probe /api/health and /api/doctor/routes.",
    )
    parser.add_argument("--report-json", action="store_true")
    args = parser.parse_args()

    if not args.app_url:
        print(
            "ERROR: No URL. Set APP_URL / BACKEND_PUBLIC_URL / CRUCIBAI_PUBLIC_BASE_URL "
            "or pass --app-url.",
            file=sys.stderr,
        )
        print(manual_checklist())
        return 2

    paths = ("/api/health", "/api/doctor/routes") if args.core_only else PUBLIC_PROBES
    checks = []
    for path in paths:
        status, data = fetch_json(args.app_url, path, args.timeout)
        ok = 200 <= status < 400 and status != 0
        checks.append(
            {
                "path": path,
                "status_code": status,
                "ok": ok,
                "response": summarize_response(data),
            }
        )

    ok_all = all(c["ok"] for c in checks)
    payload: Dict[str, Any] = {
        "status": "railway_smoke_pass" if ok_all else "railway_smoke_fail",
        "app_url": args.app_url.rstrip("/"),
        "checks": checks,
    }

    if args.report_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"app_url={payload['app_url']} status={payload['status']}")
        for c in checks:
            print(f"  {c['path']}: HTTP {c['status_code']} ok={c['ok']}")
        print(manual_checklist())

    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
