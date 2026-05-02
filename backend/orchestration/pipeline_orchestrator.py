"""
pipeline_orchestrator.py — 5-stage build pipeline for CrucibAI.

Replaces the 245-step DAG with a single-conversation generate loop:

  Stage 1: PLAN      → Haiku generates a structured JSON build plan + file manifest
  Stage 2: GENERATE  → One-conversation agent builds ALL files with full tool access
                        (run_agent_loop for Anthropic; run_text_agent_loop for Cerebras)
  Stage 3: ASSEMBLE  → npm install, ensure package.json / contract files
  Stage 4: VERIFY    → Run the build ONCE; capture stdout/stderr
  Stage 5: REPAIR    → If failed: ONE repair pass with full error context → re-verify

Architecture principle (from Claude Code analysis):
  "Give one smart agent full tools, full context, and the freedom to iterate —
   then verify the output once before delivery."

Enabled by default. Override: CRUCIBAI_USE_PIPELINE=0 to fall back to DAG.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Pipeline feature flag ────────────────────────────────────────────────────

def pipeline_enabled() -> bool:
    """Return True unless explicitly disabled via env var."""
    val = os.environ.get("CRUCIBAI_USE_PIPELINE", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


# ─── Stage timeouts ───────────────────────────────────────────────────────────

PLAN_TIMEOUT_S   = float(os.environ.get("CRUCIBAI_PLAN_TIMEOUT_S",     "60"))
GEN_TIMEOUT_S    = float(os.environ.get("CRUCIBAI_GEN_TIMEOUT_S",      "900"))   # 15 min
ASSEMBLE_TIMEOUT = float(os.environ.get("CRUCIBAI_ASSEMBLE_TIMEOUT_S", "300"))
VERIFY_TIMEOUT_S = float(os.environ.get("CRUCIBAI_VERIFY_TIMEOUT_S",   "180"))
REPAIR_TIMEOUT_S = float(os.environ.get("CRUCIBAI_REPAIR_TIMEOUT_S",   "600"))   # 10 min

# Max tool-use iterations for the generate agent (each = one LLM call)
GEN_MAX_ITER     = int(os.environ.get("CRUCIBAI_GEN_MAX_ITER",    "50"))
REPAIR_MAX_ITER  = int(os.environ.get("CRUCIBAI_REPAIR_MAX_ITER", "20"))


# ─── System prompt for the generate agent ────────────────────────────────────

_GENERATE_SYSTEM_PROMPT = """\
You are CrucibAI's master builder agent. You build complete, production-ready applications from scratch.

YOUR MISSION:
Build the entire application described in the goal. Do not stop until ALL of the following are true:
1. Every file in the build plan manifest is written to disk
2. `npm run build` (or equivalent) exits with code 0
3. The application is functionally complete — no TODOs, no placeholders, no stub implementations

TOOLS AVAILABLE:
- write_file: Write any file to the workspace (creates or overwrites)
- read_file: Read a file to understand its current state
- edit_file: Make targeted string-replacement edits to existing files
- run_command: Run build commands, npm install, tests, etc.
- list_files: See what files exist in the workspace
- search_files: Find files matching a pattern

BUILD APPROACH:
1. Write package.json and config files first (vite.config.ts, tsconfig.json, tailwind.config.ts)
2. Write the main entry point (src/main.tsx or index.ts)
3. Build out components, pages, hooks — one complete file at a time
4. Write backend routes, services, models
5. Run `npm install` once all package.json dependencies are defined
6. Run `npm run build` to find errors
7. Read the error output carefully and fix each issue
8. Repeat steps 6-7 until the build passes with exit code 0

CODE QUALITY RULES:
- Every TypeScript file must have proper types (no `any` unless absolutely necessary)
- Every React component must be complete and functional — no empty render methods
- Every API route must have real implementation — no `res.json({ message: "TODO" })`
- Imports must match what actually exists on disk
- package.json must include every dependency the code imports

YOU HAVE FULL ITERATION FREEDOM:
- Take as many turns as needed — a complete app typically takes 20-40 tool calls
- If npm run build fails, read the error, fix it, run again
- If an import is missing, write the missing file
- If a type error exists, fix the type
- Never declare "done" until the build actually passes

The user is counting on getting a working application, not just code files. Build it right.
"""

_REPAIR_SYSTEM_PROMPT = """\
You are CrucibAI's repair agent. The build failed and you need to fix it.

Your job:
1. Read the build error output provided
2. Identify the root cause(s) — missing files, bad imports, type errors, etc.
3. Fix each issue using write_file, edit_file, or run_command
4. Run `npm run build` again to verify the fix
5. Repeat until the build passes with exit code 0

Do NOT rewrite working files. Make surgical fixes only.
Prioritize: missing imports → type errors → missing files → config issues.
When the build passes, output a short summary of what you fixed.
"""


# ─── LLM caller factories ─────────────────────────────────────────────────────

def _make_anthropic_caller(api_key: str, model: str):
    """Return an async callable compatible with run_agent_loop."""
    async def _call(messages, system, tools, thinking=None):
        from backend.services.llm_service import _call_anthropic_messages_with_tools
        return await _call_anthropic_messages_with_tools(
            api_key=api_key,
            model=model,
            system_message=system,
            messages=messages,
            tools=tools,
            max_tokens=8192,
            thinking=thinking,
        )
    return _call


def _make_cerebras_text_caller():
    """Return an async callable compatible with run_text_agent_loop."""
    from backend.llm_client import call_llm

    async def _call(message: str, system_message: str, session_id: str = "") -> dict:
        response = await call_llm(
            system_prompt=system_message,
            user_prompt=message,
            task_type="code_generate",
            temperature=0.3,
        )
        return {"text": response or ""}
    return _call


def _pick_generate_caller(use_anthropic: bool):
    """Return (caller, loop_type) where loop_type is 'native' or 'text'."""
    if use_anthropic:
        claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if claude_key:
            from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
            model = normalize_anthropic_model(
                os.environ.get("ANTHROPIC_MODEL"), default=ANTHROPIC_HAIKU_MODEL
            )
            return _make_anthropic_caller(claude_key, model), "native"

    # Cerebras / text-mode fallback
    return _make_cerebras_text_caller(), "text"


# ─── Stage 1: Plan ────────────────────────────────────────────────────────────

_PLAN_SYSTEM = """\
You are a software architect. Given a product goal, output a structured JSON build plan.

Return ONLY valid JSON — no markdown, no explanation.

Schema:
{
  "build_type": "saas_app|dashboard|ecommerce|api_backend|fullstack_web|other",
  "stack": "react+vite+ts|nextjs|node+express|...",
  "file_manifest": ["src/App.tsx", "src/main.tsx", ...],
  "install_command": ["npm", "install"],
  "build_command": ["npm", "run", "build"],
  "dev_command": ["npm", "run", "dev"],
  "entry_point": "src/main.tsx",
  "summary": "one-sentence description of what will be built"
}

The file_manifest must be COMPLETE — every source file, config, and asset needed.
For a typical SaaS app this is 20-60 files. Do not truncate.
"""

async def _stage_plan(goal: str) -> Dict[str, Any]:
    """Stage 1: Ask Haiku to produce a structured build plan."""
    from backend.llm_client import call_llm
    from backend.llm_client import parse_json_response

    user_prompt = f"Product goal: {goal}\n\nGenerate the build plan JSON now."
    response = await asyncio.wait_for(
        call_llm(_PLAN_SYSTEM, user_prompt, temperature=0.2, task_type="build_plan"),
        timeout=PLAN_TIMEOUT_S,
    )
    if not response:
        raise RuntimeError("Planner returned empty response")

    plan = await parse_json_response(response, required_keys=["file_manifest"])
    if not plan:
        # Fallback: minimal plan
        logger.warning("pipeline: planner JSON parse failed; using minimal plan")
        plan = {
            "build_type": "fullstack_web",
            "stack": "react+vite+ts",
            "file_manifest": [],
            "install_command": ["npm", "install"],
            "build_command": ["npm", "run", "build"],
            "dev_command": ["npm", "run", "dev"],
            "entry_point": "src/main.tsx",
            "summary": goal[:200],
        }
    return plan


# ─── Stage 2: Generate ────────────────────────────────────────────────────────

async def _stage_generate(
    goal: str,
    plan: Dict[str, Any],
    workspace_path: str,
    on_progress=None,
) -> Dict[str, Any]:
    """Stage 2: Run a single-conversation agent to build the entire app."""
    from backend.orchestration.runtime_engine import run_agent_loop, run_text_agent_loop

    manifest_text = "\n".join(plan.get("file_manifest") or [])
    build_cmd = " ".join(plan.get("build_command") or ["npm", "run", "build"])
    install_cmd = " ".join(plan.get("install_command") or ["npm", "install"])

    user_message = f"""Goal: {goal}

Build plan summary: {plan.get("summary", "")}
Stack: {plan.get("stack", "react+vite+ts")}
Build command: {build_cmd}
Install command: {install_cmd}

File manifest (every file you must create):
{manifest_text}

Start building now. Write every file, run npm install, run the build, fix errors, and stop only when the build passes."""

    use_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    caller, loop_type = _pick_generate_caller(use_anthropic)

    if on_progress:
        await on_progress("generate_started", {
            "loop_type": loop_type,
            "file_count": len(plan.get("file_manifest") or []),
        })

    if loop_type == "native":
        result = await asyncio.wait_for(
            run_agent_loop(
                agent_name="GenerateAgent",
                system_prompt=_GENERATE_SYSTEM_PROMPT,
                user_message=user_message,
                workspace_path=workspace_path,
                call_llm=caller,
                max_iterations=GEN_MAX_ITER,
            ),
            timeout=GEN_TIMEOUT_S,
        )
    else:
        result = await asyncio.wait_for(
            run_text_agent_loop(
                agent_name="GenerateAgent",
                system_prompt=_GENERATE_SYSTEM_PROMPT,
                user_message=user_message,
                workspace_path=workspace_path,
                call_text_llm=caller,
                max_iterations=min(GEN_MAX_ITER, 20),  # text loop has higher per-iter overhead
            ),
            timeout=GEN_TIMEOUT_S,
        )

    logger.info(
        "pipeline generate: iterations=%d, files_written=%d, elapsed=%.1fs",
        result.get("iterations", 0),
        len(result.get("files_written") or []),
        result.get("elapsed_seconds", 0),
    )
    return result


# ─── Stage 3: Assemble ────────────────────────────────────────────────────────

def _run_command_sync(argv: List[str], cwd: str, timeout: float = 120.0) -> tuple:
    """Run a command synchronously. Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"[timeout after {timeout}s]"
    except OSError as e:
        return -1, "", str(e)


async def _stage_assemble(
    workspace_path: str,
    plan: Dict[str, Any],
    on_progress=None,
) -> Dict[str, Any]:
    """Stage 3: Run npm install and ensure the workspace is ready to build."""
    install_cmd = plan.get("install_command") or ["npm", "install"]

    if on_progress:
        await on_progress("assemble_started", {"install_command": install_cmd})

    # Check if package.json exists
    pkg_json = Path(workspace_path) / "package.json"
    client_pkg = Path(workspace_path) / "client" / "package.json"
    actual_ws = workspace_path
    if not pkg_json.exists() and client_pkg.exists():
        actual_ws = str(client_pkg.parent)
        logger.info("pipeline assemble: using client/ subdirectory for npm")

    rc, stdout, stderr = await asyncio.to_thread(
        _run_command_sync, install_cmd, actual_ws, ASSEMBLE_TIMEOUT
    )

    success = rc == 0
    if not success:
        logger.warning("pipeline assemble: npm install exit=%d: %s", rc, stderr[:500])

    return {
        "success": success,
        "returncode": rc,
        "stdout": stdout[:2000],
        "stderr": stderr[:2000],
        "workspace": actual_ws,
    }


# ─── Stage 4: Verify ─────────────────────────────────────────────────────────

async def _stage_verify(
    workspace_path: str,
    plan: Dict[str, Any],
    on_progress=None,
) -> Dict[str, Any]:
    """Stage 4: Run the build once and capture the result."""
    build_cmd = plan.get("build_command") or ["npm", "run", "build"]

    if on_progress:
        await on_progress("verify_started", {"build_command": build_cmd})

    rc, stdout, stderr = await asyncio.to_thread(
        _run_command_sync, build_cmd, workspace_path, VERIFY_TIMEOUT_S
    )

    passed = rc == 0
    dist_path = Path(workspace_path) / "dist"
    dist_exists = dist_path.is_dir() and any(dist_path.iterdir())

    logger.info(
        "pipeline verify: exit=%d, dist_exists=%s, passed=%s",
        rc, dist_exists, passed,
    )

    return {
        "passed": passed,
        "returncode": rc,
        "stdout": stdout[:4000],
        "stderr": stderr[:4000],
        "dist_exists": dist_exists,
        "build_command": build_cmd,
    }


# ─── Stage 5: Repair ─────────────────────────────────────────────────────────

async def _stage_repair(
    workspace_path: str,
    plan: Dict[str, Any],
    verify_result: Dict[str, Any],
    on_progress=None,
) -> Dict[str, Any]:
    """Stage 5: One repair pass with full error context, then re-verify."""
    from backend.orchestration.runtime_engine import run_agent_loop, run_text_agent_loop

    error_output = (verify_result.get("stderr") or "") + "\n" + (verify_result.get("stdout") or "")
    build_cmd_str = " ".join(plan.get("build_command") or ["npm", "run", "build"])

    user_message = f"""The build failed. Here is the error output:

{error_output[:6000]}

Build command: {build_cmd_str}
Workspace: {workspace_path}

Fix all errors and run the build again. Stop when it passes."""

    if on_progress:
        await on_progress("repair_started", {"errors_preview": error_output[:200]})

    use_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    caller, loop_type = _pick_generate_caller(use_anthropic)

    if loop_type == "native":
        repair_result = await asyncio.wait_for(
            run_agent_loop(
                agent_name="RepairAgent",
                system_prompt=_REPAIR_SYSTEM_PROMPT,
                user_message=user_message,
                workspace_path=workspace_path,
                call_llm=caller,
                max_iterations=REPAIR_MAX_ITER,
            ),
            timeout=REPAIR_TIMEOUT_S,
        )
    else:
        repair_result = await asyncio.wait_for(
            run_text_agent_loop(
                agent_name="RepairAgent",
                system_prompt=_REPAIR_SYSTEM_PROMPT,
                user_message=user_message,
                workspace_path=workspace_path,
                call_text_llm=caller,
                max_iterations=min(REPAIR_MAX_ITER, 10),
            ),
            timeout=REPAIR_TIMEOUT_S,
        )

    # Re-verify after repair
    re_verify = await _stage_verify(workspace_path, plan)

    logger.info(
        "pipeline repair: iterations=%d, files_written=%d, re_verify_passed=%s",
        repair_result.get("iterations", 0),
        len(repair_result.get("files_written") or []),
        re_verify.get("passed"),
    )

    return {
        "repair_result": repair_result,
        "re_verify": re_verify,
        "passed": re_verify.get("passed", False),
    }


# ─── Main pipeline entry point ────────────────────────────────────────────────

async def run_pipeline_job(
    job_id: str,
    workspace_path: str,
    goal: str,
    db_pool=None,
    proof_service=None,
) -> Dict[str, Any]:
    """
    Execute the full 5-stage build pipeline for a job.

    Emits job events compatible with auto_runner's event stream so the
    frontend requires no changes.
    """
    from backend.orchestration.runtime_state import (
        append_job_event,
        update_job_state,
    )
    from backend.orchestration.event_bus import publish

    t0 = time.monotonic()
    stages_completed: List[str] = []
    final_status = "failed"

    async def _emit(event_type: str, data: dict = None):
        data = data or {}
        await append_job_event(job_id, event_type, data)
        await publish(job_id, event_type, data)

    async def _progress(stage_event: str, data: dict = None):
        await _emit(stage_event, data or {})

    try:
        await _emit("pipeline_started", {"goal": goal[:200], "workspace": workspace_path})
        await update_job_state(job_id, "running")

        # ── Stage 1: Plan ────────────────────────────────────────────────────
        await _emit("stage_started", {"stage": "plan", "label": "Planning your build"})
        logger.info("pipeline[%s] stage=1/plan", job_id)
        try:
            plan = await _stage_plan(goal)
        except Exception as e:
            logger.exception("pipeline[%s] plan stage failed: %s", job_id, e)
            plan = {
                "build_type": "fullstack_web",
                "stack": "react+vite+ts",
                "file_manifest": [],
                "install_command": ["npm", "install"],
                "build_command": ["npm", "run", "build"],
                "dev_command": ["npm", "run", "dev"],
                "entry_point": "src/main.tsx",
                "summary": goal[:200],
            }
        stages_completed.append("plan")
        await _emit("stage_completed", {
            "stage": "plan",
            "file_count": len(plan.get("file_manifest") or []),
            "build_type": plan.get("build_type"),
            "stack": plan.get("stack"),
        })

        # ── Stage 2: Generate ────────────────────────────────────────────────
        await _emit("stage_started", {"stage": "generate", "label": "Building your application"})
        logger.info("pipeline[%s] stage=2/generate (%d files)", job_id, len(plan.get("file_manifest") or []))
        gen_result = await _stage_generate(goal, plan, workspace_path, on_progress=_progress)
        stages_completed.append("generate")
        await _emit("stage_completed", {
            "stage": "generate",
            "iterations": gen_result.get("iterations"),
            "files_written": len(gen_result.get("files_written") or []),
        })

        # ── Stage 3: Assemble ────────────────────────────────────────────────
        await _emit("stage_started", {"stage": "assemble", "label": "Installing dependencies"})
        logger.info("pipeline[%s] stage=3/assemble", job_id)
        assemble_result = await _stage_assemble(workspace_path, plan, on_progress=_progress)
        # Use corrected workspace path if assemble found a subdirectory
        if assemble_result.get("workspace") and assemble_result["workspace"] != workspace_path:
            workspace_path = assemble_result["workspace"]
            logger.info("pipeline[%s] workspace adjusted to: %s", job_id, workspace_path)
        stages_completed.append("assemble")
        await _emit("stage_completed", {"stage": "assemble", "npm_success": assemble_result.get("success")})

        # ── Stage 4: Verify ──────────────────────────────────────────────────
        await _emit("stage_started", {"stage": "verify", "label": "Running the build"})
        logger.info("pipeline[%s] stage=4/verify", job_id)
        verify_result = await _stage_verify(workspace_path, plan, on_progress=_progress)
        stages_completed.append("verify")
        await _emit("stage_completed", {
            "stage": "verify",
            "passed": verify_result.get("passed"),
            "dist_exists": verify_result.get("dist_exists"),
            "returncode": verify_result.get("returncode"),
        })

        # ── Stage 5: Repair (only if verify failed) ──────────────────────────
        repair_result = None
        if not verify_result.get("passed"):
            await _emit("stage_started", {"stage": "repair", "label": "Fixing build errors"})
            logger.info("pipeline[%s] stage=5/repair (build failed, rc=%d)", job_id, verify_result.get("returncode", -1))
            try:
                repair_result = await _stage_repair(workspace_path, plan, verify_result, on_progress=_progress)
                stages_completed.append("repair")
                verify_result = repair_result.get("re_verify", verify_result)
                await _emit("stage_completed", {
                    "stage": "repair",
                    "passed": repair_result.get("passed"),
                    "repair_iterations": (repair_result.get("repair_result") or {}).get("iterations"),
                })
            except Exception as e:
                logger.exception("pipeline[%s] repair stage failed: %s", job_id, e)
                await _emit("stage_failed", {"stage": "repair", "error": str(e)[:300]})

        # ── Finalize ─────────────────────────────────────────────────────────
        build_passed = verify_result.get("passed", False)
        elapsed = round(time.monotonic() - t0, 2)

        if build_passed:
            final_status = "completed"
            await update_job_state(job_id, "completed")
            await _emit("job_completed", {
                "stages": stages_completed,
                "elapsed_seconds": elapsed,
                "files_written": len(gen_result.get("files_written") or []),
                "dist_exists": verify_result.get("dist_exists"),
            })
        else:
            final_status = "failed"
            await update_job_state(job_id, "failed")
            await _emit("job_failed", {
                "stages": stages_completed,
                "elapsed_seconds": elapsed,
                "failure_reason": "Build did not pass after generate + repair",
                "build_stderr": (verify_result.get("stderr") or "")[:500],
            })

        return {
            "status": final_status,
            "stages_completed": stages_completed,
            "elapsed_seconds": elapsed,
            "plan": plan,
            "generate": gen_result,
            "assemble": assemble_result,
            "verify": verify_result,
            "repair": repair_result,
        }

    except asyncio.TimeoutError as e:
        logger.exception("pipeline[%s] timeout: %s", job_id, e)
        await update_job_state(job_id, "failed")
        await _emit("job_failed", {"failure_reason": f"Pipeline timeout: {e}"})
        return {"status": "failed", "error": str(e)}

    except Exception as e:
        logger.exception("pipeline[%s] unexpected error: %s", job_id, e)
        await update_job_state(job_id, "failed")
        await _emit("job_failed", {"failure_reason": str(e)[:500]})
        return {"status": "failed", "error": str(e)}
