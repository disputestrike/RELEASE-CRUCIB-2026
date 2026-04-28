#!/usr/bin/env python3
"""Live Railway smoke check after deploy.

Requires a reachable backend URL (APP_URL, BACKEND_PUBLIC_URL, or --app-url).

  python scripts/railway_release_smoke.py --app-url https://your-app.up.railway.app

Exit 0 when core HTTP probes succeed; prints a short manual checklist either way.

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


def manual_checklist() -> str:
    return """MANUAL ACCEPTANCE (complete after automated smoke passes)
- [ ] Deploy on Railway is the expected git commit (sha / branch).
- [ ] ANTHROPIC_API_KEY (or workspace key mapping) is set in the service.
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
        ),
    )
    parser.add_argument("--timeout", type=float, default=25.0)
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

    paths = ("/api/health", "/api/doctor/routes")
    checks = []
    for path in paths:
        status, data = fetch_json(args.app_url, path, args.timeout)
        ok = 200 <= status < 400 and status != 0
        checks.append({"path": path, "status_code": status, "ok": ok, "response": data})

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
