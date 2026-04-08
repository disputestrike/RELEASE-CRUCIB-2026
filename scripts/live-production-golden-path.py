#!/usr/bin/env python3
"""Replay the production golden path against a live CrucibAI deployment.

This script is intentionally evidence-first: every request/response and the
final PASS/FAIL matrix is written under proof/live_production_golden_path/.
It redacts auth tokens before saving artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled", "canceled", "error"}
TERMINAL_STEP_STATUSES = {"completed", "failed", "blocked", "cancelled", "canceled", "skipped"}
KEY_STEPS = {
    "preview_boot": "verification.preview",
    "elite_proof": "verification.elite_builder",
    "deploy_build": "deploy.build",
    "deploy_publish": "deploy.publish",
}
DEFAULT_GOAL = (
    "Build a tiny production proof app: a Vite React single page product dashboard "
    "with reusable components, localStorage state, clear empty/loading/error states, "
    "a FastAPI health endpoint sketch if backend output is supported, and deploy "
    "readiness proof. Keep dependencies minimal and produce previewable files."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, val in value.items():
            lk = str(key).lower()
            if lk in {"token", "access_token", "authorization", "api_key", "password"}:
                out[key] = "<redacted>"
            elif "token" in lk or "secret" in lk or "api_key" in lk:
                out[key] = "<redacted>"
            else:
                out[key] = redact(val)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(redact(data), indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, data: str) -> None:
    ensure_dir(path.parent)
    path.write_text(data, encoding="utf-8")


class LiveClient:
    def __init__(self, base_url: str, proof_dir: Path, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/") + "/"
        self.proof_dir = proof_dir
        self.timeout = timeout
        self.trace: List[Dict[str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        query: Optional[Dict[str, str]] = None,
        label: str,
    ) -> Tuple[int, Any]:
        rel = path.lstrip("/")
        if query:
            rel = f"{rel}?{urlencode(query)}"
        url = urljoin(self.base_url, rel)
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        started = utc_now()
        entry: Dict[str, Any] = {
            "label": label,
            "method": method.upper(),
            "path": "/" + rel,
            "started_at": started,
            "request_body": body or None,
        }
        try:
            req = Request(url, data=data, headers=headers, method=method.upper())
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                status = resp.getcode()
                text = raw.decode("utf-8", errors="replace")
                try:
                    parsed: Any = json.loads(text) if text else None
                except json.JSONDecodeError:
                    parsed = {"raw_text": text[:4000]}
                entry.update({
                    "finished_at": utc_now(),
                    "status_code": status,
                    "ok": 200 <= status < 300,
                    "response": parsed,
                })
                self.trace.append(entry)
                write_json(self.proof_dir / f"{label}.json", entry)
                return status, parsed
        except HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text) if text else None
            except json.JSONDecodeError:
                parsed = {"raw_text": text[:4000]}
            entry.update({
                "finished_at": utc_now(),
                "status_code": exc.code,
                "ok": False,
                "response": parsed,
                "error": str(exc),
            })
            self.trace.append(entry)
            write_json(self.proof_dir / f"{label}.json", entry)
            return exc.code, parsed
        except (URLError, TimeoutError, OSError) as exc:
            entry.update({
                "finished_at": utc_now(),
                "status_code": None,
                "ok": False,
                "response": None,
                "error": repr(exc),
            })
            self.trace.append(entry)
            write_json(self.proof_dir / f"{label}.json", entry)
            return 0, {"error": repr(exc)}


def extract_token(register_response: Any) -> Optional[str]:
    if isinstance(register_response, dict):
        token = register_response.get("token")
        if isinstance(token, str) and token:
            return token
    return None


def get_job_status(job_response: Any) -> str:
    if isinstance(job_response, dict):
        job = job_response.get("job") if isinstance(job_response.get("job"), dict) else job_response
        status = job.get("status") if isinstance(job, dict) else None
        if isinstance(status, str):
            return status
    return "unknown"


def get_job_phase(job_response: Any) -> str:
    if isinstance(job_response, dict):
        job = job_response.get("job") if isinstance(job_response.get("job"), dict) else job_response
        for key in ("current_phase", "phase", "failure_reason"):
            value = job.get(key) if isinstance(job, dict) else None
            if isinstance(value, str) and value:
                return value
    return ""


def step_map(steps_response: Any) -> Dict[str, Dict[str, Any]]:
    raw_steps: List[Any] = []
    if isinstance(steps_response, dict):
        raw_steps = steps_response.get("steps") or []
    out: Dict[str, Dict[str, Any]] = {}
    for step in raw_steps:
        if isinstance(step, dict) and step.get("step_key"):
            out[str(step["step_key"])] = step
    return out


def step_result(step: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not step:
        return "FAIL", "step missing"
    status = str(step.get("status") or "unknown")
    if status == "completed":
        return "PASS", "completed"
    details = (
        step.get("failure_reason")
        or step.get("error_message")
        or step.get("last_error")
        or step.get("status_message")
        or status
    )
    return "FAIL", str(details)[:500]


def has_background_crash(job_response: Any, events_response: Any) -> bool:
    serialized = json.dumps({"job": job_response, "events": events_response}, default=str).lower()
    return "background_crash" in serialized


def summarize_events(events_response: Any) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if isinstance(events_response, dict):
        events = [e for e in (events_response.get("events") or []) if isinstance(e, dict)]
    summary = []
    for event in events[-80:]:
        payload = event.get("payload")
        if payload is None and event.get("payload_json"):
            try:
                payload = json.loads(event.get("payload_json") or "{}")
            except Exception:
                payload = {"payload_json": event.get("payload_json")}
        summary.append({
            "id": event.get("id"),
            "event_type": event.get("event_type") or event.get("type"),
            "created_at": event.get("created_at"),
            "payload": payload,
        })
    return summary


def pass_fail_mark(status: str) -> str:
    return "PASS" if status == "PASS" else ("PARTIAL" if status == "PARTIAL" else "FAIL")


def write_pass_fail(
    proof_dir: Path,
    *,
    base_url: str,
    job_id: Optional[str],
    matrix: Dict[str, Dict[str, Any]],
    blockers: List[str],
) -> None:
    lines = [
        "# Live Production Golden Path PASS/FAIL",
        "",
        f"- Generated at: `{utc_now()}`",
        f"- Base URL: `{base_url}`",
        f"- Job ID: `{job_id or 'not-created'}`",
        "",
        "| Requirement | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for key, item in matrix.items():
        lines.append(
            f"| {key} | {pass_fail_mark(item.get('status', 'FAIL'))} | "
            f"{str(item.get('evidence', '')).replace('|', '/')} |"
        )
    lines.extend(["", "## Blockers"])
    if blockers:
        lines.extend([f"- {b}" for b in blockers])
    else:
        lines.append("- None recorded.")
    write_text(proof_dir / "PASS_FAIL.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CRUCIBAI_LIVE_BASE_URL", "https://crucibai-production.up.railway.app"),
        help="Live CrucibAI deployment base URL.",
    )
    parser.add_argument(
        "--proof-dir",
        default=os.environ.get("CRUCIBAI_LIVE_PROOF_DIR", "proof/live_production_golden_path"),
        help="Directory for proof artifacts.",
    )
    parser.add_argument("--timeout-sec", type=int, default=int(os.environ.get("CRUCIBAI_LIVE_TIMEOUT_SEC", "900")))
    parser.add_argument("--poll-sec", type=int, default=int(os.environ.get("CRUCIBAI_LIVE_POLL_SEC", "8")))
    parser.add_argument("--request-timeout-sec", type=int, default=90)
    parser.add_argument("--goal", default=os.environ.get("CRUCIBAI_LIVE_GOAL", DEFAULT_GOAL))
    parser.add_argument("--skip-run", action="store_true", help="Only check health/auth/LLM/plan; do not start run-auto.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proof_dir = Path(args.proof_dir).resolve()
    ensure_dir(proof_dir)

    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:10]}"
    client = LiveClient(args.base_url, proof_dir, timeout=float(args.request_timeout_sec))
    metadata = {
        "schema": "crucibai.live_production_golden_path/v1",
        "run_id": run_id,
        "started_at": utc_now(),
        "base_url": args.base_url,
        "goal": args.goal,
        "mode": "fresh_live_replay",
        "notes": [
            "This uses the same backend API calls the browser uses for prompt/plan/run.",
            "Auth tokens and secrets are redacted from proof artifacts.",
        ],
    }
    write_json(proof_dir / "metadata.json", metadata)

    matrix: Dict[str, Dict[str, Any]] = {}
    blockers: List[str] = []
    token: Optional[str] = None
    job_id: Optional[str] = None

    status, health = client.request("GET", "/api/health", label="01_health")
    matrix["railway_health"] = {
        "status": "PASS" if status == 200 else "FAIL",
        "evidence": f"GET /api/health -> {status}",
    }

    status, llm_health = client.request("GET", "/api/health/llm", label="02_llm_health")
    llm_status = (llm_health or {}).get("status") if isinstance(llm_health, dict) else None
    matrix["llm_readiness"] = {
        "status": "PASS" if status == 200 and llm_status in {"ready", "configured"} else "FAIL",
        "evidence": f"GET /api/health/llm -> {status}, status={llm_status}",
    }

    status, runtime_health = client.request("GET", "/api/orchestrator/runtime-health", label="03_runtime_health")
    runtime_ok = isinstance(runtime_health, dict) and runtime_health.get("ok") is True
    matrix["autorunner_runtime_health"] = {
        "status": "PASS" if status == 200 and runtime_ok else "FAIL",
        "evidence": f"GET /api/orchestrator/runtime-health -> {status}, ok={runtime_health.get('ok') if isinstance(runtime_health, dict) else None}",
    }

    email = f"codex-live-proof-{run_id}@example.com"
    status, register = client.request(
        "POST",
        "/api/auth/register",
        body={"email": email, "password": f"LiveProof-{uuid.uuid4().hex[:12]}A!", "name": "Codex Live Proof"},
        label="04_register",
    )
    token = extract_token(register)
    matrix["auth_register"] = {
        "status": "PASS" if status == 200 and token else "FAIL",
        "evidence": f"POST /api/auth/register -> {status}, token_present={bool(token)}",
    }
    if not token:
        blockers.append("Could not register/authenticate a live proof user; protected golden-path routes were not callable.")
        write_json(proof_dir / "trace.json", client.trace)
        write_pass_fail(proof_dir, base_url=args.base_url, job_id=job_id, matrix=matrix, blockers=blockers)
        return 2

    status, chat = client.request(
        "POST",
        "/api/ai/chat",
        token=token,
        body={
            "message": "Reply with exactly this phrase: live-llm-ok",
            "model": "auto",
            "system_message": "Return only the requested phrase. No markdown.",
        },
        label="05_live_llm_chat",
    )
    chat_text = (chat or {}).get("response") if isinstance(chat, dict) else None
    model_used = (chat or {}).get("model_used") if isinstance(chat, dict) else None
    matrix["live_llm_invocation"] = {
        "status": "PASS" if status == 200 and isinstance(chat_text, str) and bool(chat_text.strip()) and model_used else "FAIL",
        "evidence": f"POST /api/ai/chat -> {status}, model_used={model_used}",
    }

    status, plan = client.request(
        "POST",
        "/api/orchestrator/plan",
        token=token,
        body={"goal": args.goal, "mode": "auto", "build_target": "vite_react"},
        label="06_orchestrator_plan",
    )
    if isinstance(plan, dict):
        job_id = plan.get("job_id")
    matrix["plan_created"] = {
        "status": "PASS" if status == 200 and isinstance(job_id, str) and job_id else "FAIL",
        "evidence": f"POST /api/orchestrator/plan -> {status}, job_id={job_id}, step_count={(plan or {}).get('step_count') if isinstance(plan, dict) else None}",
    }
    if not job_id:
        blockers.append("Plan did not create a job id; cannot start Auto-Runner.")
        write_json(proof_dir / "trace.json", client.trace)
        write_pass_fail(proof_dir, base_url=args.base_url, job_id=job_id, matrix=matrix, blockers=blockers)
        return 3

    if args.skip_run:
        matrix["run_auto_started"] = {"status": "PARTIAL", "evidence": "--skip-run supplied"}
        write_json(proof_dir / "trace.json", client.trace)
        write_pass_fail(proof_dir, base_url=args.base_url, job_id=job_id, matrix=matrix, blockers=blockers)
        return 0

    status, run_auto = client.request(
        "POST",
        "/api/orchestrator/run-auto",
        token=token,
        body={"job_id": job_id},
        label="07_run_auto",
    )
    matrix["run_auto_started"] = {
        "status": "PASS" if status == 200 and isinstance(run_auto, dict) and run_auto.get("success") is True else "FAIL",
        "evidence": f"POST /api/orchestrator/run-auto -> {status}, success={(run_auto or {}).get('success') if isinstance(run_auto, dict) else None}",
    }
    if matrix["run_auto_started"]["status"] != "PASS":
        blockers.append("run-auto did not start; late-stage pipeline could not be replayed.")

    poll_log = proof_dir / "poll_log.jsonl"
    poll_log.write_text("", encoding="utf-8")
    final_job: Any = None
    final_steps: Any = None
    final_events: Any = None
    deadline = time.time() + max(30, int(args.timeout_sec))
    poll_index = 0
    stable_terminal_seen = False

    while time.time() < deadline:
        poll_index += 1
        _, final_job = client.request("GET", f"/api/jobs/{job_id}", token=token, label=f"poll_{poll_index:03d}_job")
        _, final_steps = client.request("GET", f"/api/jobs/{job_id}/steps", token=token, label=f"poll_{poll_index:03d}_steps")
        _, final_events = client.request("GET", f"/api/jobs/{job_id}/events", token=token, label=f"poll_{poll_index:03d}_events")
        current_steps = step_map(final_steps)
        job_status = get_job_status(final_job)
        event_summary = summarize_events(final_events)
        poll_entry = {
            "at": utc_now(),
            "poll": poll_index,
            "job_status": job_status,
            "job_phase": get_job_phase(final_job),
            "completed_steps": sum(1 for step in current_steps.values() if step.get("status") == "completed"),
            "total_steps": len(current_steps),
            "key_steps": {name: current_steps.get(key, {}).get("status") for name, key in KEY_STEPS.items()},
            "recent_events": event_summary[-8:],
        }
        with poll_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(redact(poll_entry), sort_keys=True) + "\n")
        all_steps_terminal = bool(current_steps) and all(
            str(step.get("status") or "") in TERMINAL_STEP_STATUSES
            for step in current_steps.values()
        )
        if job_status in TERMINAL_JOB_STATUSES or all_steps_terminal:
            if stable_terminal_seen:
                break
            stable_terminal_seen = True
        time.sleep(max(1, int(args.poll_sec)))

    # Capture final details with stable labels.
    _, final_job = client.request("GET", f"/api/jobs/{job_id}", token=token, label="final_job")
    _, final_steps = client.request("GET", f"/api/jobs/{job_id}/steps", token=token, label="final_steps")
    _, final_events = client.request("GET", f"/api/jobs/{job_id}/events", token=token, label="final_events")
    _, final_proof = client.request("GET", f"/api/jobs/{job_id}/proof", token=token, label="final_proof")
    _, final_files = client.request("GET", f"/api/jobs/{job_id}/workspace/files", token=token, label="final_workspace_files")
    status, published_app = client.request("GET", f"/published/{job_id}/", label="final_published_app")

    current_steps = step_map(final_steps)
    for requirement, step_key in KEY_STEPS.items():
        status_text, evidence = step_result(current_steps.get(step_key))
        matrix[requirement] = {
            "status": status_text,
            "evidence": f"{step_key}: {evidence}",
        }

    job_status = get_job_status(final_job)
    job_phase = get_job_phase(final_job)
    background_crash = has_background_crash(final_job, final_events)
    matrix["background_runner_stability"] = {
        "status": "PASS" if not background_crash and job_status in TERMINAL_JOB_STATUSES else "FAIL",
        "evidence": f"job_status={job_status}, phase={job_phase}, background_crash_found={background_crash}",
    }

    proof_items = 0
    if isinstance(final_proof, dict):
        for value in final_proof.values():
            if isinstance(value, list):
                proof_items += len(value)
            elif isinstance(value, dict):
                proof_items += len(value)
    files_count = len(final_files.get("files") or []) if isinstance(final_files, dict) else 0
    matrix["proof_artifacts_available"] = {
        "status": "PASS" if proof_items > 0 else "FAIL",
        "evidence": f"proof_item_count={proof_items}",
    }
    matrix["generated_workspace_files"] = {
        "status": "PASS" if files_count > 0 else "FAIL",
        "evidence": f"workspace_file_count={files_count}",
    }
    matrix["published_generated_app_url"] = {
        "status": "PASS" if status == 200 else "FAIL",
        "evidence": f"GET /published/{job_id}/ -> {status}",
    }

    all_required = [
        "railway_health",
        "llm_readiness",
        "auth_register",
        "live_llm_invocation",
        "plan_created",
        "run_auto_started",
        "preview_boot",
        "elite_proof",
        "deploy_build",
        "deploy_publish",
        "background_runner_stability",
        "proof_artifacts_available",
        "generated_workspace_files",
        "published_generated_app_url",
    ]
    failed = [key for key in all_required if matrix.get(key, {}).get("status") != "PASS"]
    if failed:
        blockers.append("Failed requirements: " + ", ".join(failed))
    if job_status != "completed":
        blockers.append(f"Live Auto-Runner job did not complete cleanly: status={job_status}, phase={job_phase}")

    write_json(proof_dir / "trace.json", client.trace)
    write_json(proof_dir / "final_summary.json", {
        "metadata": metadata,
        "job_id": job_id,
        "final_job_status": job_status,
        "final_job_phase": job_phase,
        "matrix": matrix,
        "blockers": blockers,
        "key_steps": {name: current_steps.get(step_key) for name, step_key in KEY_STEPS.items()},
    })
    write_pass_fail(proof_dir, base_url=args.base_url, job_id=job_id, matrix=matrix, blockers=blockers)

    if failed or job_status != "completed":
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
