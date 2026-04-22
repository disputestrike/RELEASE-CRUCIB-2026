#!/usr/bin/env python3
"""
benchmarks/throughput_v1/run.py
--------------------------------

Measures the CrucibAI build pipeline against 10 representative prompts by
hitting ``POST /api/jobs/`` and polling ``GET /api/jobs/{id}`` until the job
terminates (or times out). Writes ``results.json`` (per-prompt raw data) and
``summary.md`` (human-readable table + aggregates) next to this script.

Endpoint shapes (derived from backend/routes/jobs.py and services/job_service.py
on origin/main at branch time):

    POST /api/jobs/   body: {
        "goal": str, "project_id": str|null, "mode": "guided"|...,
        "priority": "normal"|..., "timeout": int
    }
    -> 201 { "success": true, "job": {"id", "status", ...},
             "plan": {...}, "websocket_url": ... }

    GET /api/jobs/{id} -> { "success": true,
                            "job": {"id", "status", "current_phase", ...},
                            "latest_failure": ... }

Auth: if ``CRUCIBAI_TOKEN`` env is set we send ``Authorization: Bearer <token>``.
Otherwise we try ``POST /api/auth/guest`` to obtain a guest JWT (the backend's
official no-signup flow, see backend/routes/auth.py ``auth_guest``).

Config (env):
    CRUCIBAI_API            default http://localhost:8000
    CRUCIBAI_TOKEN          optional bearer JWT (skips the guest call)
    CRUCIBAI_TIMEOUT_SEC    default 600 (per-prompt wall clock)
    CRUCIBAI_PROMPT_LIMIT   default 10 (use 3 for smoke runs)
    CRUCIBAI_POLL_SEC       default 2.0

Outputs:
    benchmarks/throughput_v1/results.json
    benchmarks/throughput_v1/summary.md
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
RESULTS_PATH = HERE / "results.json"
SUMMARY_PATH = HERE / "summary.md"

PROMPTS: List[Tuple[str, str]] = [
    ("todo_app",          "Build a todo app with add, complete, and delete; persist to localStorage."),
    ("landing_page",      "Build a modern SaaS landing page with hero, features, pricing, and footer."),
    ("rest_api_blog",     "Build a REST API for a blog with posts and comments, CRUD routes, JSON."),
    ("dashboard_charts",  "Build a dashboard with 3 charts (line, bar, pie) showing mock analytics data."),
    ("markdown_editor",   "Build a split-pane markdown editor with live preview and export to HTML."),
    ("auth_flow",         "Build a sign-up / sign-in flow with email+password and a protected route."),
    ("file_upload_page",  "Build a file upload page with drag-and-drop, progress bar, and a file list."),
    ("form_validation",   "Build a form with required, email, min-length, and match-password validation."),
    ("data_viz",          "Build a data-viz page that loads a CSV and renders a scatter plot with filters."),
    ("contact_form",      "Build a contact form page with name, email, subject, message and a submit toast."),
]

API_BASE      = os.environ.get("CRUCIBAI_API", "http://localhost:8000").rstrip("/")
TOKEN         = os.environ.get("CRUCIBAI_TOKEN", "").strip()
TIMEOUT_SEC   = int(os.environ.get("CRUCIBAI_TIMEOUT_SEC", "600"))
PROMPT_LIMIT  = int(os.environ.get("CRUCIBAI_PROMPT_LIMIT", str(len(PROMPTS))))
POLL_SEC      = float(os.environ.get("CRUCIBAI_POLL_SEC", "2.0"))

TERMINAL_OK_STATES   = {"completed", "succeeded", "success", "done"}
TERMINAL_FAIL_STATES = {"failed", "error", "cancelled", "canceled"}


# ── HTTP helpers (stdlib only so this runs anywhere) ─────────────────────────
def _request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Tuple[int, Dict[str, Any]]:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, (json.loads(raw) if raw else {})
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, (json.loads(raw) if raw else {"error": str(e)})
        except json.JSONDecodeError:
            return e.code, {"_raw": raw, "error": str(e)}
    except Exception as e:
        return 0, {"error": f"{type(e).__name__}: {e}"}


def _acquire_guest_token() -> Optional[str]:
    status, payload = _request("POST", "/api/auth/guest", body={}, timeout=15.0)
    if status in (200, 201):
        for key in ("token", "access_token", "jwt"):
            if key in payload and payload[key]:
                return str(payload[key])
        if isinstance(payload.get("user"), dict) and payload.get("token"):
            return str(payload["token"])
    print(f"[warn] guest auth failed: status={status} body={str(payload)[:200]}",
          file=sys.stderr)
    return None


# ── Plan / file extraction from the job payload ──────────────────────────────
def _extract_step_count(job_payload: Dict[str, Any]) -> int:
    job = job_payload.get("job") or {}
    for key in ("total_steps", "step_count"):
        val = job.get(key)
        if isinstance(val, int):
            return val
    return 0


def _extract_file_count(job_payload: Dict[str, Any]) -> int:
    """Best-effort: look for artifacts/files in common locations."""
    job = job_payload.get("job") or {}
    for key in ("file_count", "final_file_count", "files_generated"):
        val = job.get(key)
        if isinstance(val, int):
            return val
    artifacts = job.get("artifacts")
    if isinstance(artifacts, list):
        return len(artifacts)
    output = job.get("output") or {}
    files = output.get("files") if isinstance(output, dict) else None
    if isinstance(files, list):
        return len(files)
    return 0


def _job_has_plan(create_payload: Dict[str, Any], job_payload: Dict[str, Any]) -> bool:
    if isinstance(create_payload.get("plan"), (dict, list)) and create_payload.get("plan"):
        return True
    job = job_payload.get("job") or {}
    return bool(job.get("current_phase") or job.get("total_steps"))


def _job_has_first_file(job_payload: Dict[str, Any]) -> bool:
    return _extract_file_count(job_payload) > 0


def _terminal_status(job_payload: Dict[str, Any]) -> Optional[str]:
    job = job_payload.get("job") or {}
    status = (job.get("status") or "").lower()
    if status in TERMINAL_OK_STATES:
        return "success"
    if status in TERMINAL_FAIL_STATES:
        return "failed"
    return None


# ── Core per-prompt run ──────────────────────────────────────────────────────
def run_prompt(prompt_id: str, goal: str, token: Optional[str]) -> Dict[str, Any]:
    started = time.monotonic()
    result: Dict[str, Any] = {
        "prompt_id": prompt_id,
        "goal": goal,
        "t_plan": None,
        "t_first_file": None,
        "t_total": None,
        "step_count": 0,
        "final_file_count": 0,
        "success": False,
        "error": None,
        "job_id": None,
        "final_status": None,
    }

    body = {
        "goal": goal,
        "project_id": None,
        "mode": "guided",
        "priority": "normal",
        "timeout": TIMEOUT_SEC,
    }
    create_status, create_payload = _request(
        "POST", "/api/jobs/", token=token, body=body, timeout=60.0
    )
    if create_status not in (200, 201):
        result["error"] = f"create_failed: status={create_status} body={str(create_payload)[:200]}"
        result["t_total"] = round(time.monotonic() - started, 3)
        return result

    job = create_payload.get("job") or {}
    job_id = job.get("id") or create_payload.get("id")
    if not job_id:
        result["error"] = f"create_no_job_id: body={str(create_payload)[:200]}"
        result["t_total"] = round(time.monotonic() - started, 3)
        return result
    result["job_id"] = job_id

    if _job_has_plan(create_payload, {"job": job}):
        result["t_plan"] = round(time.monotonic() - started, 3)

    while True:
        elapsed = time.monotonic() - started
        if elapsed > TIMEOUT_SEC:
            result["error"] = f"timeout after {TIMEOUT_SEC}s"
            result["t_total"] = round(elapsed, 3)
            result["final_status"] = "timeout"
            return result

        status, payload = _request(
            "GET", f"/api/jobs/{job_id}", token=token, timeout=30.0
        )
        if status != 200:
            result["error"] = f"poll_failed: status={status} body={str(payload)[:200]}"
            result["t_total"] = round(time.monotonic() - started, 3)
            return result

        if result["t_plan"] is None and _job_has_plan({}, payload):
            result["t_plan"] = round(time.monotonic() - started, 3)
        if result["t_first_file"] is None and _job_has_first_file(payload):
            result["t_first_file"] = round(time.monotonic() - started, 3)

        result["step_count"] = max(result["step_count"], _extract_step_count(payload))
        result["final_file_count"] = max(
            result["final_file_count"], _extract_file_count(payload)
        )

        terminal = _terminal_status(payload)
        if terminal is not None:
            result["final_status"] = terminal
            result["success"] = terminal == "success"
            if not result["success"]:
                job_obj = payload.get("job") or {}
                err = (
                    job_obj.get("error_message")
                    or job_obj.get("failure_reason")
                    or (payload.get("latest_failure") or {}).get("summary")
                    or f"job_{terminal}"
                )
                result["error"] = str(err)[:300]
            result["t_total"] = round(time.monotonic() - started, 3)
            return result

        time.sleep(POLL_SEC)


# ── Summary assembly ─────────────────────────────────────────────────────────
def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _pct(xs: List[float], q: float) -> Optional[float]:
    if not xs:
        return None
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round((q / 100.0) * (len(xs) - 1)))))
    return xs[k]


def _failure_taxonomy(results: List[Dict[str, Any]]) -> Counter:
    c: Counter = Counter()
    for r in results:
        if r.get("success"):
            continue
        err = (r.get("error") or "unknown").strip()
        prefix = err.split(":", 1)[0][:40] if ":" in err else err[:40]
        c[prefix] += 1
    return c


def write_summary(results: List[Dict[str, Any]], run_notes: List[str]) -> None:
    successes = [r for r in results if r.get("success")]
    totals = [r["t_total"] for r in successes if isinstance(r.get("t_total"), (int, float))]
    p50 = _pct(totals, 50)
    p95 = _pct(totals, 95)
    success_rate = (len(successes) / len(results)) if results else 0.0
    tax = _failure_taxonomy(results)

    lines: List[str] = []
    lines.append("# Throughput v1 — Build-pipeline benchmark")
    lines.append("")
    lines.append(f"- Prompts attempted: **{len(results)}** (limit={PROMPT_LIMIT})")
    lines.append(f"- API base: `{API_BASE}`")
    lines.append(f"- Per-prompt timeout: {TIMEOUT_SEC}s, poll every {POLL_SEC}s")
    lines.append(f"- Success rate: **{success_rate*100:.1f}%** ({len(successes)}/{len(results)})")
    lines.append(f"- t_total p50: **{_fmt(p50)}**, p95: **{_fmt(p95)}** (successes only)")
    lines.append("")
    lines.append("## Per-prompt results")
    lines.append("")
    lines.append("| Prompt | t_plan (s) | t_total (s) | files | success |")
    lines.append("|---|---:|---:|---:|:---:|")
    for r in results:
        lines.append(
            f"| {r['prompt_id']} | {_fmt(r.get('t_plan'))} | {_fmt(r.get('t_total'))} "
            f"| {r.get('final_file_count', 0)} | {'yes' if r.get('success') else 'no'} |"
        )
    lines.append("")
    lines.append("## Failure taxonomy")
    lines.append("")
    if not tax:
        lines.append("_No failures recorded._")
    else:
        lines.append("| Error prefix | Count |")
        lines.append("|---|---:|")
        for prefix, count in tax.most_common():
            lines.append(f"| `{prefix}` | {count} |")
    lines.append("")
    lines.append("## How to run locally")
    lines.append("")
    lines.append("```bash")
    lines.append("# 1. Install backend deps")
    lines.append("pip install -r backend/requirements.txt")
    lines.append("")
    lines.append("# 2. Start the API (requires Postgres configured via env)")
    lines.append("PYTHONPATH=backend python3 -m uvicorn server:app \\")
    lines.append("    --host 127.0.0.1 --port 8000 --app-dir backend")
    lines.append("")
    lines.append("# 3. Smoke run (3 prompts)")
    lines.append("CRUCIBAI_API=http://127.0.0.1:8000 CRUCIBAI_PROMPT_LIMIT=3 \\")
    lines.append("    python3 benchmarks/throughput_v1/run.py")
    lines.append("")
    lines.append("# 4. Full run (all 10)")
    lines.append("CRUCIBAI_API=http://127.0.0.1:8000 \\")
    lines.append("    python3 benchmarks/throughput_v1/run.py")
    lines.append("```")
    lines.append("")
    lines.append("If you already have a JWT, set `CRUCIBAI_TOKEN=<jwt>` to skip the")
    lines.append("`POST /api/auth/guest` fallback.")
    lines.append("")
    lines.append("## How to run against prod")
    lines.append("")
    lines.append("```bash")
    lines.append("CRUCIBAI_API=https://crucibai-production.up.railway.app \\")
    lines.append("    CRUCIBAI_TOKEN=<jwt> \\")
    lines.append("    python3 benchmarks/throughput_v1/run.py")
    lines.append("```")
    lines.append("")
    lines.append("Obtain a JWT by signing in via the web app and copying the token")
    lines.append("from localStorage / the `/auth?token=` redirect, or by calling")
    lines.append("`POST /api/auth/login` with credentials.")
    lines.append("")
    lines.append("## Next steps")
    lines.append("")
    lines.append("- **v2**: add Lovable / Bolt / v0 comparison columns (same 10 prompts,")
    lines.append("  same t_plan / t_total / files metrics, side-by-side in summary.md).")
    lines.append("- Add a `--runs=N` flag to measure variance, not just point estimates.")
    lines.append("- Capture per-step timings from `/api/jobs/{id}/steps` so we can")
    lines.append("  break down plan vs. codegen vs. verify latency.")
    lines.append("")
    lines.append("## Run notes")
    lines.append("")
    if run_notes:
        for note in run_notes:
            lines.append(f"- {note}")
    else:
        lines.append("- Run completed without operator-recorded blockers.")
    lines.append("")

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


# ── Entrypoint ───────────────────────────────────────────────────────────────
def main() -> int:
    run_notes: List[str] = []
    token = TOKEN or None
    if not token:
        print(f"[info] no CRUCIBAI_TOKEN set — requesting guest token from {API_BASE}")
        token = _acquire_guest_token()
        if not token:
            run_notes.append(
                "Guest token request to `POST /api/auth/guest` failed; jobs endpoints "
                "require authentication so all prompts will error as `create_failed`."
            )

    prompts = PROMPTS[: max(0, min(PROMPT_LIMIT, len(PROMPTS)))]
    print(f"[info] running {len(prompts)} prompts against {API_BASE}")

    results: List[Dict[str, Any]] = []
    for i, (pid, goal) in enumerate(prompts, 1):
        print(f"[run] ({i}/{len(prompts)}) {pid} — {goal[:60]}...")
        try:
            res = run_prompt(pid, goal, token)
        except Exception as e:
            res = {
                "prompt_id": pid,
                "goal": goal,
                "t_plan": None,
                "t_first_file": None,
                "t_total": None,
                "step_count": 0,
                "final_file_count": 0,
                "success": False,
                "error": f"exception: {type(e).__name__}: {e}",
                "job_id": None,
                "final_status": "exception",
            }
        results.append(res)
        flag = "ok" if res.get("success") else "FAIL"
        print(f"       [{flag}] t_total={res.get('t_total')} err={res.get('error')}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_summary(results, run_notes)
    print(f"[done] wrote {RESULTS_PATH}")
    print(f"[done] wrote {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
