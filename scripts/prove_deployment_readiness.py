#!/usr/bin/env python3
"""Deployment proof hook.

Local mode proves Railway/deploy artifacts exist. Live mode, enabled by
``APP_URL`` or ``--app-url``, checks the deployed health/status surfaces. Use
``--require-live`` for release verification when provider execution must be
proven rather than just artifact readiness.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def write_report(payload: Dict[str, Any], report_path: str = "") -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
    if report_path:
        path = Path(report_path)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def fetch_json(base_url: str, path: str, timeout: float) -> Tuple[int, Any]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                data = {"raw": raw[:1000]}
            return resp.getcode(), data
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else None
        except json.JSONDecodeError:
            data = {"raw": text[:1000]}
        return exc.code, data
    except (URLError, TimeoutError, OSError) as exc:
        return 0, {"error": repr(exc)}


def local_artifact_checks() -> Dict[str, bool]:
    files = {
        "Dockerfile": ROOT / "Dockerfile",
        "Railway config": ROOT / "railway.json",
        "Deployment guide": ROOT / "DEPLOYMENT_GUIDE.md",
        "Backend server": ROOT / "backend" / "server.py",
        "Frontend package": ROOT / "frontend" / "package.json",
    }
    return {name: path.exists() for name, path in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", default=os.environ.get("APP_URL", ""))
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--report-path", default="")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    artifacts = local_artifact_checks()
    artifact_pass = all(artifacts.values())
    if not args.app_url:
        payload = {
            "status": "artifact_ready" if artifact_pass else "artifact_fail",
            "live_checked": False,
            "required_live": args.require_live,
            "artifacts": artifacts,
            "message": "Set APP_URL or pass --app-url with --require-live to prove provider execution.",
        }
        write_report(payload, args.report_path)
        if args.require_live:
            return 2
        return 0 if artifact_pass else 1

    checks = []
    for path in ("/api/health", "/api/doctor/routes", "/api/billing/config"):
        status, data = fetch_json(args.app_url, path, args.timeout)
        checks.append({"path": path, "status_code": status, "ok": 200 <= status < 500 and status != 404, "response": data})
    live_pass = artifact_pass and all(item["ok"] for item in checks)
    payload = {
        "status": "live_pass" if live_pass else "live_fail",
        "live_checked": True,
        "app_url": args.app_url,
        "artifacts": artifacts,
        "checks": checks,
    }
    write_report(payload, args.report_path)
    return 0 if live_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
