"""
verification.api_smoke — static API contract sketch + optional live ping.

- Discovers FastAPI-style routes under backend/*.py
- Requires GET /health on `app` (or any discovered router) for a pass
- Runs py_compile on backend Python entrypoints when present
- If CRUCIBAI_API_SMOKE_URL is set, GET that URL (e.g. http://127.0.0.1:8000/health)
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

from .verifier import _scan_workspace_for_route_declarations


def _py_compile_sync(path: str) -> Tuple[int, str]:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", path],
            capture_output=True,
            text=True,
            timeout=25,
        )
        return r.returncode, (r.stderr or "")[:400]
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)[:400]


def _pi(
    proof_type: str,
    title: str,
    payload: Dict[str, Any],
    *,
    verification_class: str = "runtime",
) -> Dict[str, Any]:
    p = {**payload, "verification_class": verification_class}
    return {"proof_type": proof_type, "title": title, "payload": p}


def _vr(passed: bool, score: int, issues: List[str], proof: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"passed": passed, "score": score, "issues": issues, "proof": proof}


def _backend_routes(workspace_path: str) -> List[Dict[str, str]]:
    all_r = _scan_workspace_for_route_declarations(workspace_path, max_files=36, max_matches=64)
    return [r for r in all_r if r.get("file", "").startswith("backend/")]


async def verify_api_smoke_workspace(workspace_path: str) -> Dict[str, Any]:
    issues: List[str] = []
    proof: List[Dict[str, Any]] = []

    if not workspace_path or not os.path.isdir(workspace_path):
        return _vr(False, 0, ["No workspace for API smoke verification"], proof)

    main_path = os.path.join(workspace_path, "backend", "main.py")
    if not os.path.isfile(main_path):
        issues.append("backend/main.py missing — cannot smoke-check API sketch")
        return _vr(False, 35, issues, proof)

    routes = _backend_routes(workspace_path)
    for r in routes[:40]:
        proof.append(
            _pi(
                "api",
                f"API smoke: declared {r['method']} {r['path']}",
                {"method": r["method"], "path": r["path"], "file": r["file"]},
                verification_class="presence",
            ),
        )

    paths_upper = {(x["method"].upper(), x["path"]) for x in routes}
    health_ok = ("GET", "/health") in paths_upper
    if not health_ok:
        # Fallback: substring (decorator spacing variants)
        try:
            with open(main_path, encoding="utf-8", errors="replace") as fh:
                main_txt = fh.read()
        except OSError:
            main_txt = ""
        if '"/health"' in main_txt or "'/health'" in main_txt:
            health_ok = True
            proof.append(
                _pi(
                    "api",
                    "API smoke: /health referenced in main.py",
                    {"check": "health_path_literal"},
                ),
            )
    if health_ok:
        proof.append(
            _pi(
                "api",
                "API smoke: GET /health present in route scan",
                {"check": "health_endpoint"},
            ),
        )
    else:
        issues.append("No GET /health route found in backend Python sources")

    backend_files = [
        "backend/main.py",
        "backend/models.py",
        "backend/auth.py",
        "backend/stripe_routes.py",
    ]
    for rel in backend_files:
        full = os.path.normpath(os.path.join(workspace_path, rel.replace("/", os.sep)))
        if not os.path.isfile(full):
            continue
        try:
            code, err = await asyncio.to_thread(_py_compile_sync, full)
            if code != 0:
                issues.append(f"py_compile failed {rel}: {err}")
            else:
                proof.append(
                    _pi(
                        "compile",
                        f"API smoke: py_compile OK {rel}",
                        {"file": rel},
                        verification_class="syntax",
                    ),
                )
        except Exception as e:
            issues.append(f"py_compile error {rel}: {str(e)[:200]}")

    ping_url = os.environ.get("CRUCIBAI_API_SMOKE_URL", "").strip()
    if ping_url:
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    ping_url,
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    body = await resp.text()
                    if resp.status < 400:
                        proof.append(
                            _pi(
                                "api",
                                f"API smoke: live GET {ping_url} → {resp.status}",
                                {"url": ping_url, "status": resp.status, "body_len": len(body)},
                            ),
                        )
                    else:
                        issues.append(f"Live API smoke returned HTTP {resp.status} for {ping_url}")
        except Exception as e:
            issues.append(f"Live API smoke failed ({ping_url}): {str(e)[:200]}")

    score = 100 if not issues else max(40, 100 - len(issues) * 18)
    return _vr(len(issues) == 0, score, issues, proof)


def healthcheck_sh_script() -> str:
    return r"""#!/bin/sh
# CrucibAI — minimal HTTP health probe (run from repo / CI after API is up)
set -e
API_URL="${API_URL:-http://127.0.0.1:8000}"
curl -sf "${API_URL}/health" >/dev/null
echo "ok ${API_URL}/health"
"""
