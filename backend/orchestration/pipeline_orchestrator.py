"""
pipeline_orchestrator.py — 5-stage build pipeline for CrucibAI.

Replaces the 245-step DAG with a single-conversation generate loop:

  Stage 1: PLAN      → Haiku generates a structured JSON build plan + file manifest
  Stage 2: GENERATE  → One-conversation agent builds ALL files with full tool access
                        (run_agent_loop for Anthropic; run_text_agent_loop for Cerebras)
  Stage 3: ASSEMBLE  → npm install, ensure package.json / contract files
  Stage 4: VERIFY    → Run the build ONCE; capture stdout/stderr
  Stage 5: REPAIR    → If failed: ONE repair pass with full error context → re-verify

Architecture principle:
  "Give one smart agent full tools, full context, and the freedom to iterate —
   then verify the output once before delivery."

Enabled by default. Override: CRUCIBAI_USE_PIPELINE=0 to fall back to DAG.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Reliability layer — improves build success rate from 60-80% to 90%+
try:
    from backend.orchestration.build_reliability import (
        extract_app_name,
        write_scaffold_to_workspace,
        npm_install_with_retry,
        post_generate_audit,
        build_repair_hint,
        brand_css_file,
        node_workspace_env,
        resolve_node_command,
    )
    _RELIABILITY_AVAILABLE = True
except ImportError:
    _RELIABILITY_AVAILABLE = False
    logger.warning("build_reliability not available — running without reliability layer")

# ─── Pipeline feature flag ────────────────────────────────────────────────────

if "node_workspace_env" not in globals():
    def node_workspace_env(extra_path: Optional[str] = None) -> Dict[str, str]:
        env = os.environ.copy()
        env["NODE_ENV"] = "development"
        env["NPM_CONFIG_PRODUCTION"] = "false"
        env["npm_config_production"] = "false"
        env["CI"] = "false"
        if extra_path:
            env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
        return env


if "resolve_node_command" not in globals():
    def resolve_node_command(cmd: List[str]) -> List[str]:
        return cmd


def pipeline_enabled() -> bool:
    """The single tool runtime is the only supported build backend."""
    return True


def _command_argv(value: Any, default: List[str]) -> List[str]:
    if isinstance(value, list):
        out = [str(item).strip() for item in value if str(item).strip()]
        return out or list(default)
    if isinstance(value, str) and value.strip():
        try:
            return shlex.split(value)
        except ValueError:
            return value.strip().split()
    return list(default)


def _todo_steps_from_plan(plan: Dict[str, Any]) -> List[Dict[str, str]]:
    manifest = plan.get("file_manifest") if isinstance(plan, dict) else []
    file_count = len(manifest) if isinstance(manifest, list) else 0
    build_cmd = " ".join(_command_argv(plan.get("build_command"), ["npm", "run", "build"]))
    return [
        {"id": "inspect", "label": "Inspect scaffold and existing workspace", "status": "completed"},
        {
            "id": "generate",
            "label": f"Build the requested app files{f' ({file_count} planned)' if file_count else ''}",
            "status": "pending",
        },
        {"id": "install", "label": "Install dependencies from the generated package manifest", "status": "pending"},
        {"id": "verify", "label": f"Run proof check: {build_cmd}", "status": "pending"},
        {"id": "repair", "label": "Patch any failing build output and verify again", "status": "pending"},
        {"id": "deliver", "label": "Expose preview, files, and proof", "status": "pending"},
    ]


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

_CRUCIB_GRADE_DIRECTIVE = """\
CRUCIB-GRADE BUILD STANDARD:
- You are not a chat assistant, UI generator, or prototype generator.
- Convert the user's lawful software request into a complete working system.
- Behavior beats artifacts: a button, route, Dockerfile, auth screen, or billing page is not complete unless it is wired and proven.
- Before and during generation, obey the frozen BuildContract. Do not silently reduce scope.
- Generate full stack structure when the request requires it: frontend, backend, database/migrations, tests, docs, deployment, runtime, and proof.
- Do not fake critical paths: auth, billing, checkout, subscription status, tenant isolation, admin permission, audit logs, file upload, email, webhooks, background jobs, AI actions, data persistence, core CRUD, export, and deployment.
- If credentials or external accounts are unavailable, build the complete test-mode/provider abstraction, persist state, document the blocker, and never pretend live production behavior.
- Every frontend API call must map to a real backend route. Protected routes must enforce auth. Admin routes must enforce role checks. Billing webhooks must verify signatures.
- Security baseline: password hashing/session validation when auth is required, RBAC, input validation, CORS/security headers, rate limiting where applicable, secret redaction, safe errors, audit logging, and env validation.
- Serious/regulated domains require readiness artifacts for security, compliance, control mapping, data flows, risk, retention, incident response, and vendor risk without claiming external certification.
- Run install/build/tests where available, parse failures as data, repair root causes, rerun checks, and leave proof artifacts.
- Final delivery may only be treated as successful when the delivery gate passes. Otherwise classify failed, blocked, mocked, stubbed, or unverified work honestly.
"""

_GENERATE_SYSTEM_PROMPT = """\
You are CrucibAI's master builder agent. You build complete, production-ready applications from scratch.

{crucib_grade_directive}

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

TYPESCRIPT RULES (prevents 80% of build failures):
- Set "strict": false in tsconfig.json to avoid unnecessary errors
- Use `as any` when you need to bypass type checking temporarily
- Never use `.ts` extensions in import paths — use just `./Component` not `./Component.ts`
- All React components must have an explicit return type or no return type annotation
- Use `React.FC` only if you know the prop types; otherwise use plain `function`
- event handlers: use `(e: React.ChangeEvent<HTMLInputElement>)` not just `(e)`

REACT RULES:
- useState type: `const [x, setX] = useState<string>('')` not `useState('')`
- All useEffect dependencies must be in the array
- Components in separate files must be default exports
- CSS modules: if you import `./App.css`, the file must exist

PACKAGE.JSON RULES:
- Every `import X from 'Y'` for a non-relative path needs Y in dependencies
- Use exact versions for stability (e.g. "react": "18.3.1" not "^18")
- Include both `react` and `react-dom` always
- Include `@types/react` and `@types/react-dom` in devDependencies

A scaffold has already been written to the workspace with a working package.json, vite.config.ts, and entry point. Start by reading these files, then build on top of them.
""".replace("{crucib_grade_directive}", _CRUCIB_GRADE_DIRECTIVE)

_REPAIR_SYSTEM_PROMPT = """\
You are CrucibAI's repair agent. The build failed and you need to fix it.

{crucib_grade_directive}

Your job:
1. Read the build error output provided
2. Identify the root cause(s) — missing files, bad imports, type errors, etc.
3. Fix each issue using write_file, edit_file, or run_command
4. Run `npm run build` again to verify the fix
5. Repeat until the build passes with exit code 0

Do NOT rewrite working files. Make surgical fixes only.
Prioritize: missing imports → type errors → missing files → config issues.
When the build passes, output a short summary of what you fixed.
""".replace("{crucib_grade_directive}", _CRUCIB_GRADE_DIRECTIVE)


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


def _pick_generate_caller(use_anthropic: bool = True):
    """Return (caller, loop_type) where loop_type is 'native' or 'text'."""
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if use_anthropic and claude_key:
        from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
        model = normalize_anthropic_model(
            os.environ.get("ANTHROPIC_MODEL"), default=ANTHROPIC_HAIKU_MODEL
        )
        return _make_anthropic_caller(claude_key, model), "native"

    # Cerebras / text-mode default
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
        # Use intent classifier for smart defaults
        try:
            from backend.orchestration.intent_to_build_type import classify_goal
            classified = classify_goal(goal)
        except Exception:
            classified = {}
        plan = {
            "build_type": classified.get("type", "fullstack_web"),
            "stack": classified.get("stack", "react+vite+ts"),
            "file_manifest": [],
            "install_command": classified.get("install_command", ["npm", "install"]),
            "build_command": classified.get("build_command", ["npm", "run", "build"]),
            "dev_command": classified.get("dev_command", ["npm", "run", "dev"]),
            "entry_point": classified.get("entry_point", "src/main.tsx"),
            "summary": goal[:200],
        }
    else:
        # Enrich LLM plan with classified timeouts if missing
        try:
            from backend.orchestration.intent_to_build_type import classify_goal
            classified = classify_goal(goal)
            plan.setdefault("install_command", classified.get("install_command", ["npm", "install"]))
            plan.setdefault("build_command", classified.get("build_command", ["npm", "run", "build"]))
            # Apply adaptive timeout based on complexity
            if classified.get("is_complex") and not os.environ.get("CRUCIBAI_GEN_TIMEOUT_S"):
                adaptive_timeout = classified.get("timeout_seconds", GEN_TIMEOUT_S)
                logger.info("pipeline: adaptive timeout %.0fs for %s", adaptive_timeout, classified.get("type"))
        except Exception:
            pass
    return plan


def _materialize_pre_generation_contract(
    workspace_path: str,
    *,
    job_id: str,
    goal: str,
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """Freeze the BuildContract before the runtime writes product files."""

    from backend.orchestration.contract_artifacts import persist_contract_artifacts

    contract_result = persist_contract_artifacts(
        workspace_path,
        {
            "id": job_id,
            "goal": goal,
            "build_target": plan.get("crucib_build_target") or plan.get("build_target"),
        },
    )
    contract = contract_result.get("contract_dict") or {}
    plan["build_contract"] = contract
    plan["contract_missing"] = contract_result.get("missing") or {}
    plan["contract_satisfied"] = bool(contract_result.get("satisfied"))
    return contract


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
    build_cmd = " ".join(_command_argv(plan.get("build_command"), ["npm", "run", "build"]))
    install_cmd = " ".join(_command_argv(plan.get("install_command"), ["npm", "install"]))
    contract_text = json.dumps(
        plan.get("build_contract") or {},
        indent=2,
        sort_keys=True,
    )

    # Enrich goal with detected intent + requirements before passing to agent
    enriched_goal = goal
    try:
        from backend.orchestration.goal_enricher import enrich_goal
        enrichment = enrich_goal(goal)
        enriched_goal = enrichment["enriched_goal"]
        logger.info("pipeline: goal enriched for type=%s app=%s",
                    enrichment.get("build_type"), enrichment.get("app_name"))
    except Exception as e:
        logger.warning("pipeline: goal enrichment failed (%s) — using raw goal", e)

    user_message = f"""{enriched_goal}

## Build Plan
Stack: {plan.get("stack", "react+vite+ts")}
Build command: {build_cmd}
Install command: {install_cmd}

## Frozen BuildContract (mandatory)
Build to satisfy this contract. If the contract requires auth, billing, database,
backend, compliance, deployment, or proof, generate real wired subsystems or a
clearly blocked/test-mode structure with proof. Do not silently downgrade to a
static placeholder site.

```json
{contract_text}
```

## File Manifest (every file you must write)
{manifest_text}

A working scaffold has already been written to the workspace. Read the existing files first,
then build the complete application on top of them. Run npm install, then npm run build.
Fix every error. Stop only when the build exits with code 0."""

    caller, loop_type = _pick_generate_caller(True)

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
                on_event=on_progress,
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
                on_event=on_progress,
            ),
            timeout=GEN_TIMEOUT_S,
        )

    logger.info(
        "pipeline generate: iterations=%d, files_written=%d, elapsed=%.1fs",
        result.get("iterations", 0),
        len(result.get("files_written") or []),
        result.get("elapsed_seconds", 0),
    )

    # Post-generate quality audit
    if _RELIABILITY_AVAILABLE:
        audit = post_generate_audit(workspace_path)
        result["audit"] = audit
        if audit["critical_count"] > 0:
            logger.warning(
                "pipeline generate: %d critical issues found (empty/stub files): %s",
                audit["critical_count"],
                [i["file"] for i in audit["issues"] if i["level"] == "critical"][:5],
            )
        else:
            logger.info("pipeline generate: audit passed (%d files, %d warnings)",
                        audit["total_files_scanned"], audit["warning_count"])

    return result


# ─── Stage 3: Assemble ────────────────────────────────────────────────────────

def _plan_build_target(plan: Dict[str, Any]) -> str:
    raw = (
        plan.get("crucib_build_target")
        or plan.get("build_target")
        or plan.get("target")
        or plan.get("build_type")
        or "vite_react"
    )
    target = str(raw or "vite_react").strip().lower()
    if target in {"saas_app", "dashboard", "ecommerce", "fullstack_web", "other"}:
        return "vite_react"
    return target or "vite_react"


async def _write_deterministic_workspace(
    workspace_path: str,
    goal: str,
    plan: Dict[str, Any],
    on_progress=None,
) -> List[str]:
    """Write a complete local app when the model provider returns no files."""
    try:
        from backend.orchestration.generated_app_template import build_frontend_file_set
    except Exception as exc:
        logger.warning("pipeline deterministic workspace template unavailable: %s", exc)
        return []

    ws = Path(workspace_path)
    ws.mkdir(parents=True, exist_ok=True)
    job_like = {
        "id": "deterministic",
        "goal": goal,
        "prompt": goal,
        "build_target": _plan_build_target(plan),
        "requirements": {"prompt": goal},
    }
    files = build_frontend_file_set(job_like)
    written: List[str] = []
    for rel_path, content in files:
        rel = str(rel_path).replace("\\", "/").lstrip("/")
        if not rel or rel.startswith("../"):
            continue
        full_path = ws / rel
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(str(content), encoding="utf-8")
        written.append(rel)
        if on_progress and len(written) <= 40:
            await on_progress("file_written", {
                "path": rel,
                "summary": "Workspace file saved.",
            })

    if written and on_progress:
        await on_progress("workspace_files_updated", {
            "files": written[:120],
            "count": len(written),
            "summary": "Generated a complete workspace from the request so preview and proof can continue.",
        })
    logger.info("pipeline deterministic workspace wrote %d files", len(written))
    return written


def _run_command_sync(argv: List[str], cwd: str, timeout: float = 120.0) -> tuple:
    """Run a command synchronously. Returns (returncode, stdout, stderr)."""
    try:
        bin_path = str(Path(cwd) / "node_modules" / ".bin")
        proc = subprocess.run(
            resolve_node_command(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=node_workspace_env(bin_path),
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
    install_cmd = _command_argv(plan.get("install_command"), ["npm", "install"])

    if on_progress:
        await on_progress("tool_call", {
            "name": "Checks",
            "tool": "Checks",
            "tool_name": "run_command",
            "command": " ".join(str(x) for x in install_cmd),
            "input": " ".join(str(x) for x in install_cmd),
            "title": "Install dependencies",
        })

    # Check if package.json exists
    pkg_json = Path(workspace_path) / "package.json"
    client_pkg = Path(workspace_path) / "client" / "package.json"
    actual_ws = workspace_path
    if not pkg_json.exists() and client_pkg.exists():
        actual_ws = str(client_pkg.parent)
        logger.info("pipeline assemble: using client/ subdirectory for npm")

    if _RELIABILITY_AVAILABLE:
        rc, stdout, stderr = await asyncio.to_thread(
            npm_install_with_retry, actual_ws, ASSEMBLE_TIMEOUT
        )
    else:
        rc, stdout, stderr = await asyncio.to_thread(
            _run_command_sync, install_cmd, actual_ws, ASSEMBLE_TIMEOUT
        )

    success = rc == 0
    if not success:
        logger.warning("pipeline assemble: npm install exit=%d: %s", rc, stderr[:500])

    if on_progress:
        await on_progress("tool_result", {
            "name": "Checks",
            "tool": "Checks",
            "tool_name": "run_command",
            "command": " ".join(str(x) for x in install_cmd),
            "input": " ".join(str(x) for x in install_cmd),
            "title": "Install dependencies",
            "success": success,
            "returncode": rc,
            "output": ((stdout or "") + ("\n" if stdout and stderr else "") + (stderr or ""))[:4000],
        })

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
    build_cmd = _command_argv(plan.get("build_command"), ["npm", "run", "build"])

    command_text = " ".join(str(x) for x in build_cmd)
    if on_progress:
        await on_progress("verifier_started", {
            "check_id": command_text,
            "command": command_text,
            "title": "Run proof checks",
        })

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

    if on_progress:
        event_name = "verifier_passed" if passed else "verifier_failed"
        await on_progress(event_name, {
            "check_id": command_text,
            "command": command_text,
            "returncode": rc,
            "dist_exists": dist_exists,
            "summary": "Build completed and preview files are present." if passed else "Build check returned errors.",
            "stdout": stdout[:4000],
            "stderr": stderr[:4000],
        })

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
    build_cmd = _command_argv(plan.get("build_command"), ["npm", "run", "build"])
    build_cmd_str = " ".join(build_cmd)

    # Build an actionable repair hint
    repair_hint = ""
    if _RELIABILITY_AVAILABLE:
        repair_hint = build_repair_hint(
            verify_result.get("stderr", ""),
            verify_result.get("stdout", ""),
            workspace_path,
        )

    user_message = f"""The build failed. Fix it.

{repair_hint}

## Full error output
{error_output[:4000]}

Build command: {build_cmd_str}

Fix every error above and run `{build_cmd_str}` again. Stop only when exit code is 0."""

    if on_progress:
        await on_progress("repair_started", {"errors_preview": error_output[:200]})

    caller, loop_type = _pick_generate_caller(True)

    if loop_type == "native":
        repair_result = await asyncio.wait_for(
            run_agent_loop(
                agent_name="RepairAgent",
                system_prompt=_REPAIR_SYSTEM_PROMPT,
                user_message=user_message,
                workspace_path=workspace_path,
                call_llm=caller,
                max_iterations=REPAIR_MAX_ITER,
                on_event=on_progress,
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
                on_event=on_progress,
            ),
            timeout=REPAIR_TIMEOUT_S,
        )

    # Re-verify after repair
    re_verify = await _stage_verify(workspace_path, plan, on_progress=on_progress)

    logger.info(
        "pipeline repair: iterations=%d, files_written=%d, re_verify_passed=%s",
        repair_result.get("iterations", 0),
        len(repair_result.get("files_written") or []),
        re_verify.get("passed"),
    )

    if on_progress:
        await on_progress("repair_completed", {
            "passed": re_verify.get("passed", False),
            "files_changed": repair_result.get("files_written") or [],
            "summary": "Repair pass finished and proof was rerun.",
        })

    return {
        "repair_result": repair_result,
        "re_verify": re_verify,
        "passed": re_verify.get("passed", False),
    }


# ─── Main pipeline entry point ────────────────────────────────────────────────

async def _pause_cancel_status(job_id: str) -> Optional[str]:
    try:
        from backend.orchestration.runtime_state import get_job as _gj

        job = await _gj(job_id)
        status = ((job or {}).get("status") or "").lower()
        if status in ("cancelled", "canceled"):
            return "cancelled"
        if status == "paused":
            return "paused"
    except Exception:
        pass
    return None


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
        clear_steps,
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

    # ── Resolve workspace path if missing ────────────────────────────────────
    if not workspace_path or not workspace_path.strip():
        try:
            from backend.orchestration.runtime_state import get_job as _get_job_state
            _job_meta = await _get_job_state(job_id)
            _project_id = (_job_meta or {}).get("project_id")
            if _project_id:
                from backend.config import WORKSPACE_ROOT
                workspace_path = str(WORKSPACE_ROOT / "projects" / _project_id)
                import pathlib as _pl
                _pl.Path(workspace_path).mkdir(parents=True, exist_ok=True)
                logger.info("pipeline[%s] workspace_path resolved from project_id: %s", job_id, workspace_path)
        except Exception as _wpe:
            logger.warning("pipeline[%s] could not resolve workspace_path: %s", job_id, _wpe)

    try:
        await clear_steps(job_id, reason="single_tool_runtime")
        await _emit("pipeline_started", {
            "goal": goal[:200],
            "workspace": workspace_path,
            "engine": "single_tool_runtime",
            "legacy_dag": False,
        })
        await update_job_state(
            job_id,
            "running",
            extra={"current_phase": "runtime_build", "engine": "single_tool_runtime"},
        )

        # ── Stage 1: Plan ────────────────────────────────────────────────────
        await _emit("stage_started", {"stage": "plan", "label": "Reading the request"})
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
        await _emit("plan_created", {
            "summary": plan.get("summary") or goal[:200],
            "build_type": plan.get("build_type"),
            "stack": plan.get("stack"),
            "file_manifest": (plan.get("file_manifest") or [])[:120],
            "steps": _todo_steps_from_plan(plan),
        })
        await _emit("stage_completed", {
            "stage": "plan",
            "file_count": len(plan.get("file_manifest") or []),
            "build_type": plan.get("build_type"),
            "stack": plan.get("stack"),
        })

        # Cancel/pause gate between stages
        abort_status = await _pause_cancel_status(job_id)
        if abort_status:
            await update_job_state(job_id, abort_status)
            return {"status": abort_status, "stages_completed": stages_completed}

        # ── Stage 2: Generate ────────────────────────────────────────────────
        # Inject working scaffold BEFORE agent runs — prevents cold-start failures
        if _RELIABILITY_AVAILABLE and workspace_path:
            try:
                import pathlib as _pl
                _pl.Path(workspace_path).mkdir(parents=True, exist_ok=True)
                app_name = extract_app_name(goal)
                scaffold_files = write_scaffold_to_workspace(workspace_path, app_name)
                logger.info("pipeline[%s] scaffold injected: %d files (app=%s)", job_id, len(scaffold_files), app_name)
                await _emit("workspace_foundation_ready", {"app_name": app_name, "files": len(scaffold_files)})
            except Exception as _se:
                logger.warning("pipeline[%s] scaffold injection failed (non-fatal): %s", job_id, _se)

        try:
            contract = _materialize_pre_generation_contract(
                workspace_path,
                job_id=job_id,
                goal=goal,
                plan=plan,
            )
            await _emit("build_contract_ready", {
                "build_class": contract.get("build_class"),
                "required_routes": contract.get("required_routes") or [],
                "required_api_endpoints": contract.get("required_api_endpoints") or [],
                "required_database_tables": contract.get("required_database_tables") or [],
                "required_proof_types": contract.get("required_proof_types") or [],
                "status": contract.get("status"),
            })
        except Exception as contract_error:
            logger.exception("pipeline[%s] pre-generation contract failed: %s", job_id, contract_error)
            await _emit("build_contract_failed", {"error": str(contract_error)[:500]})

        await _emit("stage_started", {"stage": "generate", "label": "Writing files"})
        logger.info("pipeline[%s] stage=2/generate (%d files)", job_id, len(plan.get("file_manifest") or []))
        gen_result = await _stage_generate(goal, plan, workspace_path, on_progress=_progress)
        if not (gen_result.get("files_written") or []):
            local_files = await _write_deterministic_workspace(
                workspace_path,
                goal,
                plan,
                on_progress=_progress,
            )
            if local_files:
                gen_result["files_written"] = local_files
                gen_result["local_generation"] = True
                gen_result["local_generation_reason"] = "model_provider_returned_no_files"
        stages_completed.append("generate")
        await _emit("stage_completed", {
            "stage": "generate",
            "iterations": gen_result.get("iterations"),
            "files_written": len(gen_result.get("files_written") or []),
            "local_generation": bool(gen_result.get("local_generation")),
        })

        # Cancel/pause gate
        abort_status = await _pause_cancel_status(job_id)
        if abort_status:
            await update_job_state(job_id, abort_status)
            return {"status": abort_status, "stages_completed": stages_completed}

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

        # Cancel/pause gate
        abort_status = await _pause_cancel_status(job_id)
        if abort_status:
            await update_job_state(job_id, abort_status)
            return {"status": abort_status, "stages_completed": stages_completed}

        # ── Stage 4: Verify ──────────────────────────────────────────────────
        await _emit("stage_started", {"stage": "verify", "label": "Running proof"})
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
        enterprise_proof: Dict[str, Any] = {}
        delivery_gate: Dict[str, Any] = {}

        try:
            from backend.orchestration.enterprise_proof import generate_enterprise_proof_artifacts

            enterprise_proof = generate_enterprise_proof_artifacts(
                workspace_path,
                {"id": job_id, "goal": goal},
                plan=plan,
                generation_result=gen_result,
                assemble_result=assemble_result,
                verify_result=verify_result,
                repair_result=repair_result,
            )
            delivery_gate = enterprise_proof.get("delivery_gate") or {}
            await _emit("proof_bundle_ready", {
                "proof_files": enterprise_proof.get("proof_files") or [],
                "delivery_gate": delivery_gate,
                "api_alignment_passed": (enterprise_proof.get("api_alignment") or {}).get("passed"),
            })
        except Exception as proof_error:
            logger.exception("pipeline[%s] enterprise proof generation failed: %s", job_id, proof_error)
            delivery_gate = {
                "status": "FAILED_DELIVERY_GATE",
                "allowed": False,
                "blocks_completion": True,
                "failed_checks": ["proof_generation"],
                "error": str(proof_error)[:500],
            }
            await _emit("proof_bundle_failed", {"error": str(proof_error)[:500]})

        gate_blocks_completion = bool(delivery_gate.get("blocks_completion"))

        if build_passed and not gate_blocks_completion:
            final_status = "completed"
            await update_job_state(job_id, "completed", extra={
                "delivery_gate": delivery_gate,
                "proof_files": enterprise_proof.get("proof_files") or [],
            })
            await _emit("job_completed", {
                "stages": stages_completed,
                "elapsed_seconds": elapsed,
                "files_written": len(gen_result.get("files_written") or []),
                "dist_exists": verify_result.get("dist_exists"),
                "delivery_gate": delivery_gate,
                "proof_files": enterprise_proof.get("proof_files") or [],
            })
        elif build_passed and gate_blocks_completion:
            final_status = "blocked"
            await update_job_state(job_id, "blocked", extra={
                "delivery_gate": delivery_gate,
                "proof_files": enterprise_proof.get("proof_files") or [],
            })
            await _emit("job_failed", {
                "stages": stages_completed,
                "elapsed_seconds": elapsed,
                "failure_reason": "FAILED_DELIVERY_GATE",
                "message": "The app builds, but the delivery contract gate found critical unimplemented, mocked, or unwired paths.",
                "delivery_gate": delivery_gate,
            })
        else:
            final_status = "failed"
            await update_job_state(job_id, "failed", extra={
                "delivery_gate": delivery_gate,
                "proof_files": enterprise_proof.get("proof_files") or [],
            })
            error_excerpt = (
                verify_result.get("stderr")
                or verify_result.get("stdout")
                or "The build command exited without a usable error message."
            )
            await _emit("job_failed", {
                "stages": stages_completed,
                "elapsed_seconds": elapsed,
                "failure_reason": "Proof failed on the build command.",
                "message": "The generated app did not build yet. Details include the exact command output.",
                "build_stderr": str(error_excerpt)[:1200],
                "delivery_gate": delivery_gate,
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
            "enterprise_proof": enterprise_proof,
            "delivery_gate": delivery_gate,
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
