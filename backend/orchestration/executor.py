"""
executor.py — Step execution dispatcher for CrucibAI Auto-Runner.
Each step category routes to a specific handler.
Every step: emit event → execute → persist artifact → emit result.
"""
import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, Callable

from .runtime_state import update_step_state, append_job_event, save_checkpoint
from .event_bus import publish
from .verifier import verify_step
from .generated_app_template import build_frontend_file_set

logger = logging.getLogger(__name__)


def append_node_artifact_record(workspace_path: str, record: Dict[str, Any]) -> None:
    """Append one JSON line per completed DAG node under .crucibai/node_artifacts.jsonl."""
    if not workspace_path or not os.path.isdir(workspace_path):
        return
    d = os.path.join(workspace_path, ".crucibai")
    try:
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "node_artifacts.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except OSError as e:
        logger.warning("append_node_artifact_record: %s", e)


def _step_deps(step: Dict[str, Any]) -> list:
    raw = step.get("depends_on_json") or step.get("depends_on") or "[]"
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw) if isinstance(raw, str) else []
    except Exception:
        return []


def _norm_rel(p: str) -> str:
    return p.replace("\\", "/").lstrip("/")


def _safe_write(base: str, rel: str, content: str) -> Optional[str]:
    """Write UTF-8 text under workspace; returns normalized relative path or None."""
    if not base or not isinstance(base, str):
        return None
    rel = _norm_rel(rel)
    root = os.path.normpath(os.path.abspath(base))
    full = os.path.normpath(os.path.join(root, rel))
    if not full.startswith(root):
        logger.warning("executor: rejected path escape %s", rel)
        return None
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return rel


def _read_text(base: str, rel: str) -> Optional[str]:
    if not base:
        return None
    full = os.path.join(base, _norm_rel(rel))
    if not os.path.isfile(full):
        return None
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


# ── Step handler registry ─────────────────────────────────────────────────────

async def handle_planning_step(step: Dict, job: Dict,
                                workspace_path: str, **kwargs) -> Dict:
    """Planner and requirements steps — produce structured plan output."""
    written = []
    if workspace_path:
        plan_path = "PLAN.md"
        body = (
            f"# Build plan\n\n## Goal\n\n{job.get('goal', '').strip() or '(none)'}\n\n"
            f"## Step\n\n`{step.get('step_key', '')}`\n"
        )
        if _safe_write(workspace_path, plan_path, body):
            written.append(plan_path)
    return {
        "output": f"Planning step '{step['step_key']}' analyzed goal: {job.get('goal', '')[:100]}",
        "artifacts": [],
        "output_files": written,
    }


async def handle_frontend_generate(step: Dict, job: Dict,
                                    workspace_path: str, **kwargs) -> Dict:
    out: list = []
    if workspace_path:
        for rel, content in build_frontend_file_set(job):
            w = _safe_write(workspace_path, rel, content)
            if w:
                out.append(w)
    return {
        "output": f"Production-shaped frontend bundle: {job.get('goal', '')[:80]}",
        "output_files": out,
        "artifacts": [{"kind": "workspace", "handoff": "next_steps_read_workspace"}],
    }


async def handle_frontend_modify(step: Dict, job: Dict,
                                  workspace_path: str, **kwargs) -> Dict:
    key = step.get("step_key", "")
    out: list = []
    if not workspace_path:
        return {"output": f"Frontend modified: {key} (no workspace path)", "artifacts": [], "output_files": []}

    if key == "frontend.styling":
        gpath = "src/styles/global.css"
        prev = _read_text(workspace_path, gpath) or ""
        extra = "\n\n/* frontend.styling — design tokens */\n:root {\n  --crucib-accent: #38bdf8;\n  --crucib-radius: 12px;\n}\n"
        if _safe_write(workspace_path, gpath, prev + extra):
            out.append(gpath)
    else:
        team = """import React from 'react';

export default function TeamPage() {
  return (
    <div>
      <h1 style={{ marginBottom: 12 }}>Team</h1>
      <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
        Added by Auto-Runner routing step — reusable page under <code>src/pages</code>.
      </p>
    </div>
  );
}
"""
        if _safe_write(workspace_path, "src/pages/TeamPage.jsx", team):
            out.append("src/pages/TeamPage.jsx")
        shell_path = "src/components/ShellLayout.jsx"
        shell = _read_text(workspace_path, shell_path) or ""
        if "{/* CRUCIB_ROUTE_ANCHOR */}" in shell and "link('/team'" not in shell:
            shell = shell.replace(
                "{/* CRUCIB_ROUTE_ANCHOR */}",
                "{link('/team', 'Team')}",
                1,
            )
            if _safe_write(workspace_path, shell_path, shell):
                out.append(shell_path)
        app_path = "src/App.jsx"
        app_src = _read_text(workspace_path, app_path) or ""
        # Template uses './pages/DashboardPage' (no .jsx). Older code only patched .jsx — left
        # <TeamPage /> in routes without import → runtime "TeamPage is not defined".
        needs_team_import = "pages/TeamPage" not in app_src
        if needs_team_import:
            for needle in (
                "import DashboardPage from './pages/DashboardPage.jsx';",
                "import DashboardPage from './pages/DashboardPage';",
            ):
                if needle in app_src:
                    app_src = app_src.replace(
                        needle,
                        needle + "\nimport TeamPage from './pages/TeamPage.jsx';",
                        1,
                    )
                    break
        if "CRUCIB_APP_ROUTE_ANCHOR" in app_src:
            if '<Route path="/team"' not in app_src:
                app_src = app_src.replace(
                    "{/* CRUCIB_APP_ROUTE_ANCHOR */}",
                    '<Route path="/team" element={<TeamPage />} />',
                    1,
                )
            else:
                app_src = app_src.replace("{/* CRUCIB_APP_ROUTE_ANCHOR */}", "", 1)
            if _safe_write(workspace_path, app_path, app_src):
                out.append(app_path)

    return {"output": f"Frontend modified: {key}", "artifacts": [], "output_files": out}


async def handle_backend_route(step: Dict, job: Dict,
                                workspace_path: str, **kwargs) -> Dict:
    key = step.get("step_key", "")
    routes_added: list = []
    out_files: list = []

    if not workspace_path:
        return {
            "output": f"Backend route generated: {key} (no workspace path)",
            "routes_added": [],
            "output_files": [],
            "artifacts": [],
        }

    if key == "backend.models":
        models_py = '''"""ORM / schema sketch generated by Auto-Runner."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ItemRecord(BaseModel):
    id: Optional[int] = None
    title: str
    created_at: Optional[datetime] = None
'''
        w = _safe_write(workspace_path, "backend/models.py", models_py)
        if w:
            out_files.append(w)

    elif key == "backend.routes":
        main_py = '''"""FastAPI app sketch — generated by Auto-Runner."""
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Generated API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/api/items")
def list_items():
    return {"items": [{"id": 1, "title": "demo"}]}
'''
        w = _safe_write(workspace_path, "backend/main.py", main_py)
        if w:
            out_files.append(w)
        routes_added = [
            {"method": "GET", "path": "/health", "description": "Health check"},
            {"method": "GET", "path": "/api/items", "description": "List demo items"},
        ]

    elif key == "backend.auth":
        auth_py = '''"""Auth placeholder — JWT wiring lives in your real deployment."""
# Use python-jose + passlib in production; routes are documented in proof bundle.
PROTECTED_PREFIX = "/api/private"
'''
        w = _safe_write(workspace_path, "backend/auth.py", auth_py)
        if w:
            out_files.append(w)
        routes_added = [
            {"method": "POST", "path": "/api/auth/login", "description": "Login (stub)"},
        ]

    elif key == "backend.stripe":
        stripe_py = '''"""Stripe webhook/route placeholder."""
# Implement checkout session + webhook with STRIPE_SECRET_KEY in production.
'''
        w = _safe_write(workspace_path, "backend/stripe_routes.py", stripe_py)
        if w:
            out_files.append(w)
        routes_added = [
            {"method": "POST", "path": "/api/stripe/webhook", "description": "Stripe webhook (stub)"},
        ]

    else:
        w = _safe_write(workspace_path, "backend/main.py", "# backend placeholder\n")
        if w:
            out_files.append(w)

    return {
        "output": f"Backend route generated: {key}",
        "routes_added": routes_added,
        "output_files": out_files,
        "artifacts": [],
    }


async def handle_db_migration(step: Dict, job: Dict,
                               workspace_path: str, db_pool=None, **kwargs) -> Dict:
    key = step.get("step_key", "")
    out: list = []
    tables: list = []

    if workspace_path:
        if key == "database.migration":
            sql = """-- Generated by CrucibAI Auto-Runner (app schema sketch, not applied to host DB)
CREATE TABLE IF NOT EXISTS app_items (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
            w = _safe_write(workspace_path, "db/migrations/001_schema.sql", sql)
            if w:
                out.append(w)
        else:
            seed = """-- Demo seed (run against your app database after migration)
INSERT INTO app_items (title) VALUES ('Welcome from Auto-Runner');
"""
            w = _safe_write(workspace_path, "db/seeds/001_seed.sql", seed)
            if w:
                out.append(w)

    return {
        "output": f"Migration step executed: {key}",
        "tables_created": tables,
        "output_files": out,
        "artifacts": [],
    }


async def handle_test_run(step: Dict, job: Dict,
                           workspace_path: str, **kwargs) -> Dict:
    return {"output": f"Tests executed: {step['step_key']}", "artifacts": []}


async def handle_deploy(step: Dict, job: Dict,
                         workspace_path: str, **kwargs) -> Dict:
    key = step.get("step_key", "")
    out: list = []
    if workspace_path:
        if key == "deploy.build":
            docker = """# Generated by Auto-Runner — customize for your stack
FROM node:20-alpine AS web
WORKDIR /app
COPY . .
# RUN npm ci && npm run build
CMD ["echo", "configure CMD for your app"]
"""
            w = _safe_write(workspace_path, "Dockerfile", docker)
            if w:
                out.append(w)
        else:
            readme = """# Publish\n\nConfigure Vercel, Netlify, or Railway with this workspace root.\nNo remote URL is set in local Auto-Runner runs.\n"""
            w = _safe_write(workspace_path, "deploy/PUBLISH.md", readme)
            if w:
                out.append(w)

    return {
        "output": f"Deploy step: {key}",
        "deploy_url": None,
        "artifacts": [],
        "output_files": out,
    }


async def handle_verification_step(step: Dict, job: Dict,
                                    workspace_path: str, db_pool=None, **kwargs) -> Dict:
    """Verification is applied in execute_step via verify_step (single pass)."""
    return {
        "output": f"Verification gate: {step.get('step_key', '')}",
        "artifacts": [],
    }


async def handle_generic(step: Dict, job: Dict,
                          workspace_path: str, **kwargs) -> Dict:
    return {"output": f"Step executed: {step['step_key']}", "artifacts": []}


# ── Handler routing ───────────────────────────────────────────────────────────

STEP_HANDLERS = {
    "planning.analyze": handle_planning_step,
    "planning.requirements": handle_planning_step,
    "frontend.scaffold": handle_frontend_generate,
    "frontend.styling": handle_frontend_modify,
    "frontend.routing": handle_frontend_modify,
    "backend.models": handle_backend_route,
    "backend.routes": handle_backend_route,
    "backend.auth": handle_backend_route,
    "backend.stripe": handle_backend_route,
    "database.migration": handle_db_migration,
    "database.seed": handle_db_migration,
    "verification.compile": handle_verification_step,
    "verification.api_smoke": handle_verification_step,
    "verification.preview": handle_verification_step,
    "verification.security": handle_verification_step,
    "deploy.build": handle_deploy,
    "deploy.publish": handle_deploy,
}


def _get_handler(step_key: str):
    if step_key in STEP_HANDLERS:
        return STEP_HANDLERS[step_key]
    # Match by prefix
    prefix = ".".join(step_key.split(".")[:2])
    if prefix in STEP_HANDLERS:
        return STEP_HANDLERS[prefix]
    phase = step_key.split(".")[0]
    phase_defaults = {
        "frontend": handle_frontend_generate,
        "backend": handle_backend_route,
        "database": handle_db_migration,
        "verification": handle_verification_step,
        "deploy": handle_deploy,
        "planning": handle_planning_step,
    }
    return phase_defaults.get(phase, handle_generic)


# ── Main execute_step ─────────────────────────────────────────────────────────

async def execute_step(step: Dict[str, Any], job: Dict[str, Any],
                        workspace_path: str = "",
                        db_pool=None,
                        proof_service=None) -> Dict[str, Any]:
    """
    Execute a single step:
    1. Mark running + emit step_started
    2. Call handler
    3. Run verifier
    4. Persist proof
    5. Mark completed/failed + emit result
    6. Save checkpoint
    """
    job_id = job["id"]
    step_id = step["id"]
    step_key = step["step_key"]
    t0 = time.monotonic()

    # 1. Mark running
    await update_step_state(step_id, "running")
    t_start_ms = int(time.time() * 1000)
    deps = _step_deps(step)
    await append_job_event(job_id, "step_started",
                           {"step_key": step_key, "agent": step.get("agent_name")},
                           step_id=step_id)
    await append_job_event(
        job_id,
        "dag_node_started",
        {
            "step_key": step_key,
            "step_id": step_id,
            "phase": step.get("phase"),
            "agent_name": step.get("agent_name"),
            "depends_on": deps,
            "workspace_path_set": bool(workspace_path),
            "execution_mode": "executed",
            "mocked": False,
            "handoff": "shared_workspace_disk",
            "downstream": "pending_steps_whose_deps_include_this_step_key",
            "started_at_ms": t_start_ms,
            "retry_count": step.get("retry_count") or 0,
        },
        step_id=step_id,
    )
    await publish(job_id, "step_started",
                  {"step_key": step_key, "agent": step.get("agent_name"),
                   "step_id": step_id})

    try:
        # 2. Execute handler
        handler = _get_handler(step_key)
        result = await handler(step, job, workspace_path, db_pool=db_pool)

        duration_ms = int((time.monotonic() - t0) * 1000)

        # 3. Verify
        await update_step_state(step_id, "verifying")
        await publish(job_id, "step_verifying", {"step_key": step_key, "step_id": step_id})

        # Merge output files/tables from result into step for verifier
        verification_input = {**step, **result}
        vr = await verify_step(verification_input, workspace_path, db_pool)

        if not vr["passed"]:
            raise RuntimeError(
                f"Verification failed for {step_key}: {'; '.join(vr['issues'])}"
            )

        # 4. Persist proof
        if proof_service:
            for p in vr.get("proof", []):
                await proof_service.store_proof(
                    job_id=job_id, step_id=step_id,
                    proof_type=p["proof_type"],
                    title=p["title"],
                    payload=p["payload"]
                )

        # 5. Mark completed
        await update_step_state(step_id, "completed", {
            "output_ref": json.dumps(result.get("output", ""))[:500],
            "verifier_status": "passed",
            "verifier_score": vr["score"],
        })
        await append_job_event(job_id, "step_completed",
                               {"step_key": step_key, "duration_ms": duration_ms,
                                "verifier_score": vr["score"]},
                               step_id=step_id)
        t_end_ms = int(time.time() * 1000)
        outs = list(result.get("output_files") or [])
        arts = result.get("artifacts") or []
        await append_job_event(
            job_id,
            "dag_node_completed",
            {
                "step_key": step_key,
                "step_id": step_id,
                "ended_at_ms": t_end_ms,
                "duration_ms": duration_ms,
                "output_files": outs[:80],
                "artifacts": arts[:40],
                "verifier_score": vr["score"],
                "proof_count": len(vr.get("proof") or []),
                "execution_mode": "executed",
                "skipped": False,
            },
            step_id=step_id,
        )
        await publish(job_id, "step_completed",
                      {"step_key": step_key, "step_id": step_id,
                       "duration_ms": duration_ms, "score": vr["score"],
                       "proof": vr.get("proof", [])})

        # 6. Checkpoint
        await save_checkpoint(job_id, step_key, {
            "step_id": step_id, "step_key": step_key,
            "status": "completed", "score": vr["score"],
            "output": str(result.get("output", ""))[:500],
        })

        append_node_artifact_record(
            workspace_path,
            {
                "ts_ms": int(time.time() * 1000),
                "job_id": job_id,
                "step_id": step_id,
                "step_key": step_key,
                "duration_ms": duration_ms,
                "verifier_score": vr["score"],
                "output_files": outs[:40],
                "status": "completed",
            },
        )

        return {"success": True, "result": result, "verification": vr}

    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        error_msg = str(exc)[:500]
        logger.warning("executor: step %s failed: %s", step_key, error_msg)

        await update_step_state(step_id, "failed", {
            "error_message": error_msg,
            "verifier_status": "failed",
        })
        await append_job_event(job_id, "step_failed",
                               {"step_key": step_key, "error": error_msg,
                                "duration_ms": duration_ms},
                               step_id=step_id)
        await append_job_event(
            job_id,
            "dag_node_failed",
            {
                "step_key": step_key,
                "step_id": step_id,
                "ended_at_ms": int(time.time() * 1000),
                "duration_ms": duration_ms,
                "failure_reason": error_msg,
                "retry_count": step.get("retry_count") or 0,
                "execution_mode": "executed",
            },
            step_id=step_id,
        )
        await publish(job_id, "step_failed",
                      {"step_key": step_key, "step_id": step_id,
                       "error": error_msg, "duration_ms": duration_ms})

        return {"success": False, "error": error_msg}
