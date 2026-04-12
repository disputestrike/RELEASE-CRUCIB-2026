#!/usr/bin/env python3
"""
Local runtime evidence pack + pre-push gate.

Default flow uses POST /api/auth/guest (twice if needed) and a minimal paste import
to obtain a project_id without consuming the free-tier "landing-only" POST /projects
rules or spawning run_orchestration_v2 alongside Auto-Runner jobs.

Usage (backend already running, from repo root):

  cd backend
  set PYTHONPATH=.
  set DATABASE_URL=postgresql://crucibai:crucibai@127.0.0.1:5434/crucibai
  set REDIS_URL=redis://127.0.0.1:6381/0
  set JWT_SECRET=test-jwt-secret-for-pytest-minimum-32-characters-long
  set FRONTEND_URL=http://127.0.0.1:3000
  set GOOGLE_CLIENT_ID=test.apps.googleusercontent.com
  set GOOGLE_CLIENT_SECRET=test-google-client-secret
  python ..\\scripts\\run_local_evidence_pack.py --base-url http://127.0.0.1:8000

Env:
  EVIDENCE_JOB_TIMEOUT_SEC   Per-scenario wall clock (default 7200)
  EVIDENCE_SKIP_DOCKER       1 = skip docker compose up
  EVIDENCE_API_TOKEN         Bearer for build scenarios (skip guest A)
  EVIDENCE_IMPORT_TOKEN      Bearer for import-only guest B (optional)
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:
    print("FATAL: install httpx in the active Python (pip install httpx)", file=sys.stderr)
    raise

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"


@dataclass
class Scenario:
    slug: str
    prompt: str


DEFAULT_SCENARIOS = [
    Scenario(
        "01_landing_page",
        "Build a simple one-page marketing landing page for a local coffee shop with hero, menu section, and contact. Static content only.",
    ),
    Scenario(
        "02_fullstack_saas",
        "Build a small full-stack SaaS MVP: React dashboard, FastAPI backend with /health, and SQLite or PostgreSQL notes CRUD. Single-tenant demo.",
    ),
    Scenario(
        "03_internal_dashboard",
        "Build an internal admin dashboard: login shell, table of users, filters, and export to CSV. React + REST API sketch.",
    ),
    Scenario(
        "04_automation_workflow",
        "Build an automation-oriented workspace: cron-style job list UI, webhook receiver stub, and logging page. React + Python.",
    ),
    Scenario(
        "05_mobile_ready",
        "Build a mobile-ready responsive PWA-style marketing site: responsive layout, touch-friendly nav, install prompt placeholder.",
    ),
]


def _tcp_ok(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket

    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False


def ensure_docker_deps(skip: bool) -> List[str]:
    lines: List[str] = []
    if skip or os.environ.get("EVIDENCE_SKIP_DOCKER", "").strip().lower() in ("1", "true", "yes"):
        lines.append("docker: skipped (EVIDENCE_SKIP_DOCKER)")
        return lines
    r = subprocess.run(
        ["docker", "compose", "up", "-d", "postgres", "redis"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    lines.append(f"docker compose up: exit={r.returncode}")
    if r.stdout:
        lines.append(r.stdout.strip()[:4000])
    if r.stderr:
        lines.append(r.stderr.strip()[:4000])
    ps = subprocess.run(
        ["docker", "compose", "ps"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines.append(f"docker compose ps: exit={ps.returncode}")
    if ps.stdout:
        lines.append(ps.stdout.strip()[:4000])
    return lines


def docker_health_detail() -> str:
    lines: List[str] = []
    for svc, script in (
        ("postgres", "pg_isready -U crucibai -d crucibai"),
        ("redis", "redis-cli ping"),
    ):
        r = subprocess.run(
            ["docker", "compose", "exec", "-T", svc, "sh", "-c", script],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines.append(f"{svc}: exit={r.returncode} stdout={r.stdout.strip()!r} stderr={r.stderr.strip()!r}")
    return "\n".join(lines) + "\n"


def wait_ports(max_wait: int = 120) -> List[str]:
    lines: List[str] = []
    deadline = time.time() + max_wait
    while time.time() < deadline:
        pg = _tcp_ok("127.0.0.1", 5434)
        rd = _tcp_ok("127.0.0.1", 6381)
        if pg and rd:
            lines.append("ports: postgres 5434 + redis 6381 reachable")
            return lines
        time.sleep(1)
    lines.append("ports: TIMEOUT waiting for 5434/6381")
    return lines


def tree_dir(root: Path, max_files: int = 1200) -> str:
    if not root.is_dir():
        return "(missing)\n"
    lines: List[str] = []
    n = 0
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            continue
        lines.append(rel)
        n += 1
        if n >= max_files:
            lines.append(f"... truncated after {max_files} files")
            break
    return "\n".join(lines) + "\n"


def _workspace_for_project(project_id: str) -> Path:
    sys.path.insert(0, str(BACKEND_ROOT))
    from project_state import WORKSPACE_ROOT

    safe = str(project_id).replace("/", "_").replace("\\", "_")
    return Path(WORKSPACE_ROOT) / safe


def _summarize_swarm(steps: List[Dict[str, Any]], file_writes: Dict[str, List[str]]) -> Dict[str, Any]:
    agents = [str(s.get("agent_name") or "") for s in steps]
    by_agent: Dict[str, int] = {}
    for a in agents:
        if not a:
            continue
        by_agent[a] = by_agent.get(a, 0) + 1
    completed = [s for s in steps if (s.get("status") or "") == "completed"]
    failed = [s for s in steps if (s.get("status") or "") == "failed"]
    writers = sorted({str(s.get("agent_name") or "") for s in steps if s.get("step_key") in file_writes})
    proofish = sorted(
        {
            str(s.get("agent_name") or "")
            for s in steps
            if any(x in (s.get("step_key") or "").lower() for x in ("proof", "verify", "validation", "seal", "audit"))
        }
    )
    return {
        "step_count": len(steps),
        "completed_steps": len(completed),
        "failed_steps": len(failed),
        "distinct_agents_in_plan": len(by_agent),
        "steps_per_agent": by_agent,
        "agents_with_reported_file_writes": [w for w in writers if w],
        "agents_proof_or_verify_named": [p for p in proofish if p],
    }


def run_scenario(
    client: httpx.Client,
    base: str,
    headers: Dict[str, str],
    project_id: str,
    sc: Scenario,
    out_dir: Path,
    job_timeout: float,
) -> Dict[str, Any]:
    d = out_dir / sc.slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.txt").write_text(sc.prompt + "\n", encoding="utf-8")
    summary: Dict[str, Any] = {"slug": sc.slug, "ok": False, "project_id": project_id}

    rh = client.get(f"{base}/api/orchestrator/runtime-health", headers=headers, timeout=60.0)
    (d / "validation_output.txt").write_text(
        f"GET /api/orchestrator/runtime-health -> {rh.status_code}\n{rh.text[:120_000]}\n",
        encoding="utf-8",
    )

    pl = client.post(
        f"{base}/api/orchestrator/plan",
        headers=headers,
        json={"project_id": project_id, "goal": sc.prompt, "mode": "guided"},
        timeout=180.0,
    )
    if pl.status_code != 200:
        (d / "failure.txt").write_text(
            f"POST /api/orchestrator/plan -> {pl.status_code}\n{pl.text}\n", encoding="utf-8"
        )
        summary["error"] = "plan_failed"
        return summary
    plan_body = pl.json()
    job_id = plan_body.get("job_id")
    if not job_id:
        (d / "failure.txt").write_text(
            f"No job_id in plan response: {json.dumps(plan_body, indent=2)[:8000]}\n", encoding="utf-8"
        )
        summary["error"] = "no_job_id"
        return summary

    (d / "ids.txt").write_text(f"job_id={job_id}\nproject_id={project_id}\n", encoding="utf-8")

    ra = client.post(
        f"{base}/api/orchestrator/run-auto",
        headers=headers,
        json={"job_id": job_id},
        timeout=60.0,
    )
    if ra.status_code != 200:
        (d / "failure.txt").write_text(
            f"POST /api/orchestrator/run-auto -> {ra.status_code}\n{ra.text}\n", encoding="utf-8"
        )
        summary["error"] = "run_auto_failed"
        return summary

    t0 = time.time()
    last_status = ""
    last_job: Dict[str, Any] = {}
    while time.time() - t0 < job_timeout:
        gr = client.get(f"{base}/api/jobs/{job_id}", headers=headers, timeout=30.0)
        if gr.status_code != 200:
            time.sleep(2)
            continue
        last_job = gr.json().get("job") or gr.json()
        last_status = str(last_job.get("status") or "")
        if last_status in ("completed", "failed", "cancelled", "canceled"):
            break
        time.sleep(3)

    if last_status not in ("completed", "failed", "cancelled", "canceled"):
        (d / "failure.txt").write_text(
            f"TIMEOUT after {job_timeout}s last_status={last_status!r}\n",
            encoding="utf-8",
        )

    (d / "final_job.json").write_text(json.dumps(last_job, indent=2, default=str), encoding="utf-8")

    ws = _workspace_for_project(project_id).resolve()
    (d / "workspace_absolute.txt").write_text(str(ws) + "\n", encoding="utf-8")
    (d / "workspace_tree.txt").write_text(tree_dir(ws), encoding="utf-8")

    st_before = client.get(f"{base}/api/projects/{project_id}/state", headers=headers, timeout=30.0)
    (d / "project_state_after_job.json").write_text(st_before.text[:200_000], encoding="utf-8")

    meta = ws / "META"
    for name in ("run_manifest.json", "artifact_manifest.json", "seal.json", "proof_index.json"):
        p = meta / name
        if p.is_file():
            shutil.copy2(p, d / name)
        else:
            (d / f"missing_{name}").write_text("not present at end of run\n", encoding="utf-8")

    sr = client.get(f"{base}/api/jobs/{job_id}/steps", headers=headers, timeout=60.0)
    steps: List[Dict[str, Any]] = []
    if sr.status_code == 200:
        steps = sr.json().get("steps") or []
    agents_lines = [f"{s.get('step_key')}\t{s.get('agent_name')}\t{s.get('status')}" for s in steps]
    (d / "agents_summary.txt").write_text("\n".join(agents_lines) + "\n", encoding="utf-8")

    file_writes: Dict[str, List[str]] = {}
    er = client.get(f"{base}/api/jobs/{job_id}/events", headers=headers, timeout=60.0)
    evs: List[Dict[str, Any]] = []
    if er.status_code == 200:
        evs = er.json().get("events") or []
        fail_ev = [e for e in evs if (e.get("event_type") or "") in ("step_failed", "dag_node_failed", "job_failed")]
        (d / "job_events_failures.json").write_text(
            json.dumps(fail_ev, indent=2, default=str)[:400_000],
            encoding="utf-8",
        )
        for ev in evs:
            if (ev.get("event_type") or "") != "dag_node_completed":
                continue
            payload = ev.get("payload") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    continue
            sk = str(payload.get("step_key") or "")
            for fp in payload.get("output_files") or []:
                if isinstance(fp, str):
                    file_writes.setdefault(sk, []).append(fp)
        (d / "file_writes_from_events.json").write_text(json.dumps(file_writes, indent=2), encoding="utf-8")

    swarm = _summarize_swarm(steps, file_writes)
    (d / "agents_summary.json").write_text(json.dumps(swarm, indent=2), encoding="utf-8")

    proof_r = client.get(f"{base}/api/jobs/{job_id}/proof", headers=headers, timeout=120.0)
    (d / "proof_api.json").write_text(proof_r.text[:500_000], encoding="utf-8")

    zr = client.get(f"{base}/api/jobs/{job_id}/export/full.zip", headers=headers, timeout=600.0)
    zip_ok = zr.status_code == 200 and len(zr.content) >= 4 and zr.content[:2] == b"PK"
    if zip_ok:
        zpath = d / "export_full.zip"
        zpath.write_bytes(zr.content)
        unzip_dir = d / "export_unzipped"
        if unzip_dir.exists():
            shutil.rmtree(unzip_dir)
        unzip_dir.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(zr.content), "r") as zf:
            names = sorted(zf.namelist())
            zf.extractall(unzip_dir)
        (d / "zip_contents.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
        summary["zip_entries"] = len(names)
        meta_ok = any(n.startswith("META/") or n.startswith("META\\") for n in names)
        summary["zip_has_meta"] = meta_ok
        non_meta = [n for n in names if not n.startswith("META/") and not n.startswith("META\\") and not n.endswith("/")]
        summary["zip_non_meta_files"] = len(non_meta)
        if not meta_ok and last_status == "completed":
            with open(d / "failure.txt", "a", encoding="utf-8") as fp:
                fp.write("ZIP missing META/ prefix entries\n")
    else:
        (d / "zip_contents.txt").write_text(f"ZIP failed HTTP {zr.status_code}\n{zr.text[:4000]!s}\n", encoding="utf-8")
        summary["zip_error"] = zr.status_code

    file_count = sum(1 for _ in ws.rglob("*") if _.is_file())
    summary["workspace_file_count"] = file_count
    summary["final_status"] = last_status
    summary["job_id"] = job_id

    manifest_ok = (meta / "artifact_manifest.json").is_file()
    zip_has_meta = bool(summary.get("zip_has_meta"))
    durable_ok = file_count >= 5
    summary["ok"] = (
        last_status == "completed"
        and manifest_ok
        and zip_ok
        and zip_has_meta
        and durable_ok
        and summary.get("zip_non_meta_files", 0) >= 3
    )
    return summary


def _guest_token(client: httpx.Client, base: str) -> str:
    r = client.post(f"{base}/api/auth/guest", timeout=30.0)
    if r.status_code != 200:
        raise RuntimeError(f"guest auth {r.status_code}: {r.text}")
    return str(r.json().get("token") or "")


def _paste_import_project(client: httpx.Client, base: str, headers: Dict[str, str]) -> str:
    r = client.post(
        f"{base}/api/projects/import",
        headers=headers,
        json={
            "name": "evidence-seed",
            "source": "paste",
            "files": [
                {
                    "path": "README.md",
                    "code": "# evidence seed\nminimal import so orchestrator jobs share one project_id.\n",
                }
            ],
        },
        timeout=60.0,
    )
    if r.status_code != 200:
        raise RuntimeError(f"paste import {r.status_code}: {r.text}")
    pid = r.json().get("project_id")
    if not pid:
        raise RuntimeError(f"paste import no project_id: {r.text}")
    return str(pid)


def run_import_flow(
    client: httpx.Client,
    base: str,
    headers: Dict[str, str],
    out: Path,
    name: str,
    body: dict,
    run_followup: bool,
    job_timeout: float,
) -> Dict[str, Any]:
    sub = out / "imports" / name
    sub.mkdir(parents=True, exist_ok=True)
    r = client.post(f"{base}/api/projects/import", headers=headers, json=body, timeout=180.0)
    (sub / "import_response.json").write_text(r.text[:100_000], encoding="utf-8")
    rec: Dict[str, Any] = {"name": name, "http": r.status_code, "ok": r.status_code == 200}
    if r.status_code != 200:
        (sub / "failure.txt").write_text(r.text, encoding="utf-8")
        return rec
    js = r.json()
    pid = js.get("project_id")
    rec["project_id"] = pid
    if pid:
        ws = _workspace_for_project(str(pid))
        (sub / "workspace_tree.txt").write_text(tree_dir(ws), encoding="utf-8")
    if run_followup and pid:
        goal = "Add a small About section file ABOUT.md describing the imported project."
        pl = client.post(
            f"{base}/api/orchestrator/plan",
            headers=headers,
            json={"project_id": str(pid), "goal": goal, "mode": "guided"},
            timeout=120.0,
        )
        (sub / "followup_plan.json").write_text(pl.text[:50_000], encoding="utf-8")
        if pl.status_code != 200:
            rec["followup_status"] = "plan_failed"
            return rec
        job_id = pl.json().get("job_id")
        if not job_id:
            rec["followup_status"] = "no_job_id"
            return rec
        ra = client.post(
            f"{base}/api/orchestrator/run-auto",
            headers=headers,
            json={"job_id": job_id},
            timeout=60.0,
        )
        (sub / "followup_run_auto.json").write_text(ra.text[:20_000], encoding="utf-8")
        if ra.status_code != 200:
            rec["followup_status"] = "run_auto_failed"
            (sub / "failure.txt").write_text(ra.text, encoding="utf-8")
            return rec
        t0 = time.time()
        st = ""
        while time.time() - t0 < min(job_timeout, 900.0):
            gj = client.get(f"{base}/api/jobs/{job_id}", headers=headers, timeout=30.0)
            if gj.status_code == 200:
                st = str((gj.json().get("job") or {}).get("status") or "")
                if st in ("completed", "failed", "cancelled", "canceled"):
                    break
            time.sleep(2)
        rec["followup_job_id"] = job_id
        rec["followup_status"] = st
        ws = _workspace_for_project(str(pid))
        (sub / "workspace_tree_after_followup.txt").write_text(tree_dir(ws), encoding="utf-8")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("EVIDENCE_BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--timeout-per-job", type=float, default=float(os.environ.get("EVIDENCE_JOB_TIMEOUT_SEC", "7200")))
    ap.add_argument("--scenarios", type=str, default="", help="Comma slugs to run subset, e.g. 01_landing_page")
    ap.add_argument("--strict", action="store_true", help="Exit nonzero if any scenario or import failed")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    out = args.out or (REPO_ROOT / "local_evidence_pack" / time.strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)

    cmds = (
        "Commands (this run):\n"
        "  docker compose up -d postgres redis\n"
        "  docker compose ps\n"
        "  docker compose exec -T postgres sh -c \"pg_isready -U crucibai -d crucibai\"\n"
        "  docker compose exec -T redis sh -c \"redis-cli ping\"\n"
        "  cd backend && set PYTHONPATH=. && set DATABASE_URL=... && set REDIS_URL=... && python -m uvicorn server:app --host 127.0.0.1 --port 8000\n"
        f"  python {Path(__file__).resolve()}\n"
    )
    (out / "00_commands.txt").write_text(cmds, encoding="utf-8")

    dock_lines = ensure_docker_deps(False)
    (out / "00_docker_compose.txt").write_text("\n".join(dock_lines) + "\n", encoding="utf-8")
    (out / "00_docker_exec_health.txt").write_text(docker_health_detail(), encoding="utf-8")
    (out / "00_port_wait.txt").write_text("\n".join(wait_ports(120)) + "\n", encoding="utf-8")

    client = httpx.Client(timeout=30.0)
    try:
        hr = client.get(f"{base}/api/health")
        (out / "00_health.txt").write_text(f"GET /api/health -> {hr.status_code}\n{hr.text[:2000]}\n", encoding="utf-8")
        if hr.status_code != 200:
            print("FAIL: health", hr.status_code)
            return 2
    except Exception as e:
        (out / "00_health.txt").write_text(f"FAIL connect: {e}\n", encoding="utf-8")
        print("FAIL: cannot reach API", e)
        return 2

    token_a = os.environ.get("EVIDENCE_API_TOKEN", "").strip()
    if not token_a:
        token_a = _guest_token(client, base)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    (out / "00_token_guest_build.txt").write_text("Using EVIDENCE_API_TOKEN\n" if os.environ.get("EVIDENCE_API_TOKEN") else f"guest token (prefix): {token_a[:16]}...\n", encoding="utf-8")

    try:
        project_id = _paste_import_project(client, base, headers_a)
    except RuntimeError as e:
        (out / "00_seed_project_failure.txt").write_text(str(e), encoding="utf-8")
        print("FAIL seed project", e)
        return 3

    scenarios = DEFAULT_SCENARIOS
    if args.scenarios.strip():
        want = {s.strip() for s in args.scenarios.split(",") if s.strip()}
        scenarios = [s for s in DEFAULT_SCENARIOS if s.slug in want]

    summaries: List[Dict[str, Any]] = []
    for sc in scenarios:
        print("Scenario", sc.slug, "...")
        summaries.append(run_scenario(client, base, headers_a, project_id, sc, out, args.timeout_per_job))

    (out / "99_summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")

    token_b = os.environ.get("EVIDENCE_IMPORT_TOKEN", "").strip()
    if not token_b:
        token_b = _guest_token(client, base)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    imp_records = []
    imp_records.append(
        run_import_flow(
            client,
            base,
            headers_b,
            out,
            "paste_code",
            {
                "name": "paste-code-import",
                "source": "paste",
                "files": [{"path": "src/hello.jsx", "code": "export default function Hello(){return <p>hi</p>}\n"}],
            },
            run_followup=True,
            job_timeout=min(args.timeout_per_job, 900.0),
        )
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app/readme.txt", "zip import test")
    zb64 = base64.b64encode(buf.getvalue()).decode("ascii")
    imp_records.append(
        run_import_flow(
            client,
            base,
            headers_b,
            out,
            "zip_upload",
            {"name": "zip-import", "source": "zip", "zip_base64": zb64},
            run_followup=True,
            job_timeout=min(args.timeout_per_job, 900.0),
        )
    )
    imp_records.append(
        run_import_flow(
            client,
            base,
            headers_b,
            out,
            "git_github",
            {
                "name": "git-import",
                "source": "git",
                "git_url": "https://github.com/octocat/Hello-World",
            },
            run_followup=True,
            job_timeout=min(args.timeout_per_job, 900.0),
        )
    )
    (out / "imports" / "99_import_summary.json").write_text(json.dumps(imp_records, indent=2), encoding="utf-8")

    ui = {
        "routes": [
            "GET /api/health",
            "GET /api/orchestrator/runtime-health",
            "POST /api/orchestrator/plan",
            "POST /api/orchestrator/run-auto",
            "GET /api/jobs/{job_id}",
            "GET /api/jobs/{job_id}/steps",
            "GET /api/jobs/{job_id}/events",
            "GET /api/jobs/{job_id}/proof",
            "GET /api/jobs/{job_id}/export/full.zip",
            "GET /api/projects/{project_id}/state",
            "POST /api/projects/import",
        ],
        "note": "Browser UI not automated here; these are the API surfaces the Unified Workspace uses for plan/run, proof, and exports.",
    }
    (out / "00_ui_api_routes.json").write_text(json.dumps(ui, indent=2), encoding="utf-8")

    scenarios_ok = all(s.get("ok") for s in summaries)

    def _import_gate(rec: Dict[str, Any]) -> bool:
        if not rec.get("ok"):
            return False
        if "followup_status" not in rec:
            return True
        return rec.get("followup_status") == "completed"

    imports_ok = all(_import_gate(x) for x in imp_records)
    ok = scenarios_ok
    if args.strict:
        ok = scenarios_ok and imports_ok

    print("Evidence folder:", out)
    print(
        json.dumps(
            {"scenarios_ok": scenarios_ok, "imports_ok": imports_ok, "strict": args.strict, "exit_ok": ok},
            indent=2,
        )
    )
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
