"""
runtime_engine.py — Agentic loop engine for CrucibAI (FIX 13-16).

Replaces one-shot LLM calls with a while(True) tool-use loop:
- Agent observes workspace, acts with file tools; may run allowlisted shell commands
  (``run_command``) for build/test feedback in the same loop
- Exits via stop_reason == "end_turn" or max_iterations
- Read-only tools run in parallel (asyncio.gather, up to 10)
- Write tools run serially to preserve consistency
- 15 high-stakes agents may use extended thinking on turn 1 when
  CRUCIBAI_ANTHROPIC_EXTENDED_THINKING=1 (Anthropic only)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ....tool_executor import is_allowlisted_run_command
logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_LOOP_ITERATIONS = 12
PARALLEL_READ_LIMIT = 10

# Default max wall time for a single run_command (npm build, tests, etc.)
_DEFAULT_CMD_TIMEOUT_S = float(os.environ.get("CRUCIB_SWARM_CMD_TIMEOUT_S", "600"))

THINKING_AGENTS = frozenset({
    "planner", "architect", "architecture", "security", "security_review",
    "backend_gen", "backend_generation", "frontend_gen", "frontend_generation",
    "backend", "frontend", "api_design", "schema_design", "test_strategy",
    "database", "devops", "performance",
})

THINKING_BUDGET_TOKENS = 8000

# ─── Tool registry ────────────────────────────────────────────────────────────

def _read_file(workspace_path: str, rel: str) -> str:
    full = os.path.join(workspace_path, rel)
    if not os.path.isfile(full):
        return f"[file not found: {rel}]"
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        return f"[error reading {rel}: {e}]"


def _list_files(workspace_path: str, subdir: str = "") -> str:
    base = os.path.join(workspace_path, subdir) if subdir else workspace_path
    if not os.path.isdir(base):
        return f"[directory not found: {subdir or '.'}]"
    lines = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
        for fname in files:
            rel = os.path.relpath(os.path.join(root, fname), workspace_path)
            lines.append(rel.replace("\\", "/"))
    return "\n".join(sorted(lines)) or "[empty directory]"


def _search_files(workspace_path: str, pattern: str) -> str:
    import fnmatch
    results = []
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
        for fname in files:
            rel = os.path.relpath(os.path.join(root, fname), workspace_path)
            if fnmatch.fnmatch(fname, pattern) or fnmatch.fnmatch(rel.replace("\\", "/"), pattern):
                results.append(rel.replace("\\", "/"))
    return "\n".join(sorted(results)) or f"[no files matching {pattern}]"


def _write_file(workspace_path: str, rel: str, content: str) -> str:
    from .executor import _safe_write
    written = _safe_write(workspace_path, rel, content)
    if written:
        return f"[written: {written}]"
    return f"[write rejected or failed: {rel}]"


def _edit_file(workspace_path: str, rel: str, old_str: str, new_str: str) -> str:
    full = os.path.join(workspace_path, rel)
    if not os.path.isfile(full):
        return f"[file not found: {rel}]"
    try:
        with open(full, encoding="utf-8") as f:
            src = f.read()
        if old_str not in src:
            return f"[edit failed: string not found in {rel}]"
        new_src = src.replace(old_str, new_str, 1)
        from .executor import _safe_write
        written = _safe_write(workspace_path, rel, new_src)
        return f"[edited: {written}]" if written else f"[edit rejected: {rel}]"
    except OSError as e:
        return f"[error editing {rel}: {e}]"


def _norm_cwd(rel: str) -> str:
    rel = (rel or "").strip().replace("\\", "/").lstrip("/")
    if rel.startswith(".."):
        return ""
    return rel


def _workspace_subdir(workspace_path: str, cwd_rel: str) -> tuple[Optional[Path], Optional[str]]:
    root = Path(workspace_path).resolve()
    sub = _norm_cwd(cwd_rel)
    target = root if not sub else (root / sub).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, "[run_command rejected: cwd escapes workspace]"
    if not root.is_dir():
        return None, "[run_command: workspace is not a directory]"
    return target, None


async def _execute_run_command(workspace_path: str, tool_input: Dict[str, Any]) -> str:
    raw = tool_input.get("argv") if "argv" in tool_input else tool_input.get("command")
    if raw is None:
        return "[run_command: missing argv]"
    if isinstance(raw, str):
        return '[run_command rejected: pass argv as array e.g. ["npm","run","build"]]'

    argv: List[str] = []
    for item in raw or []:
        s = str(item).strip()
        if s:
            argv.append(s)
    if not argv:
        return "[run_command: empty argv]"
    if not is_allowlisted_run_command(argv):
        return f"[run_command rejected: not allowlisted: {argv!r}]"

    cw_err: Optional[str]
    cwd_slot, cw_err = _workspace_subdir(
        workspace_path, str(tool_input.get("cwd") or tool_input.get("working_directory") or "")
    )
    if cw_err:
        return cw_err
    assert cwd_slot is not None
    cwd_path = cwd_slot.resolve()

    timeout_s = float(os.environ.get("CRUCIB_SWARM_CMD_TIMEOUT_S", str(int(_DEFAULT_CMD_TIMEOUT_S))))
    timeout_s = max(5.0, min(timeout_s, 7200.0))

    def _run_sync() -> str:
        try:
            proc = subprocess.run(
                argv,
                cwd=str(cwd_path),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return f"[run_command subprocess timeout ({timeout_s}s) for {' '.join(argv)}]"
        except OSError as ose:
            return f"[run_command os error: {ose}]"

        hdr = f"exit_code={proc.returncode}\ncwd={cwd_path}\ncmd={' '.join(argv)}\n---\n"
        out = proc.stdout or ""
        err = proc.stderr or ""
        parts = []
        if out.strip():
            parts.append("[stdout]\n" + out[:200_000])
        if err.strip():
            parts.append("[stderr]\n" + err[:200_000])
        body = "\n".join(parts) if parts else "(no stdout/stderr)"
        return hdr + body

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run_sync), timeout=timeout_s + 35.0)
    except asyncio.TimeoutError:
        return f"[run_command asyncio layer timeout (> {timeout_s + 35.0}s) for {' '.join(argv)}]"


# ─── Tool definitions for the LLM ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative file path"}},
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in the workspace or a subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {"subdir": {"type": "string", "description": "Subdirectory to list (optional)"}},
        },
    },
    {
        "name": "search_files",
        "description": "Search for files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string", "description": "Glob pattern e.g. '*.jsx'"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the workspace (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace the first occurrence of old_str with new_str in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"},
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run an allowlisted build/check command inside the workspace (never pass raw shell). "
            "Use argv as a list, e.g. [\"npm\", \"run\", \"build\"] or [\"python\", \"--version\"]. "
            "Optional cwd is a path relative to workspace root (subfolder only)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "argv": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Argv list (no shell), first element is executable",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory relative to workspace (optional)",
                },
            },
            "required": ["argv"],
        },
    },
]

READ_ONLY_TOOLS = {"read_file", "list_files", "search_files"}
WRITE_TOOLS = {"write_file", "edit_file"}


# ─── Tool executor ────────────────────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: Dict[str, Any], workspace_path: str) -> str:
    if tool_name == "read_file":
        return _read_file(workspace_path, tool_input.get("path", ""))
    elif tool_name == "list_files":
        return _list_files(workspace_path, tool_input.get("subdir", ""))
    elif tool_name == "search_files":
        return _search_files(workspace_path, tool_input.get("pattern", "*"))
    elif tool_name == "write_file":
        return _write_file(workspace_path, tool_input.get("path", ""), tool_input.get("content", ""))
    elif tool_name == "edit_file":
        return _edit_file(workspace_path, tool_input.get("path", ""), tool_input.get("old_str", ""), tool_input.get("new_str", ""))
    elif tool_name == "run_command":
        return await _execute_run_command(workspace_path, tool_input)
    else:
        return f"[unknown tool: {tool_name}]"


async def _execute_tools_batch(
    tool_uses: List[Dict[str, Any]],
    workspace_path: str,
) -> List[Dict[str, Any]]:
    """Execute tools. Parallelize only homogeneous read-only batches; otherwise sequential."""

    names = [t["name"] for t in tool_uses]
    if not tool_uses:
        return []

    def _pure_reads() -> bool:
        return names and all(n in READ_ONLY_TOOLS for n in names)

    if _pure_reads():
        semaphore = asyncio.Semaphore(PARALLEL_READ_LIMIT)

        async def _one(tool: Dict[str, Any]):
            async with semaphore:
                return tool["id"], await _execute_tool(tool["name"], tool.get("input", {}), workspace_path)

        pairs = await asyncio.gather(*[_one(t) for t in tool_uses])
        results_map = dict(pairs)
    else:
        results_map = {}
        for t in tool_uses:
            results_map[t["id"]] = await _execute_tool(t["name"], t.get("input", {}) or {}, workspace_path)

    return [
        {"type": "tool_result", "tool_use_id": t["id"], "content": results_map.get(t["id"], "[no result]")}
        for t in tool_uses
    ]


def _accumulate_usage(
    totals: Dict[str, int], usage: Optional[Dict[str, Any]]
) -> None:
    """Sum Anthropic Messages ``usage`` objects across tool-loop turns."""
    if not isinstance(usage, dict):
        return
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        val = usage.get(key)
        if isinstance(val, int):
            totals[key] = totals.get(key, 0) + val


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Parse a provider-neutral JSON tool envelope from plain model text."""

    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = re.sub(r"^(json|javascript|js)\s*", "", raw, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


# ─── Core agentic loop ────────────────────────────────────────────────────────

async def run_agent_loop(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    workspace_path: str,
    call_llm: Callable,  # async fn(messages, system, tools, thinking) -> response dict
    max_iterations: int = MAX_LOOP_ITERATIONS,
) -> Dict[str, Any]:
    """
    Run a while(True) agentic loop for a single agent.
    Agent observes workspace via tools, writes files, exits when stop_reason == end_turn.
    """
    messages = [{"role": "user", "content": user_message}]
    iterations = 0
    files_written: List[str] = []
    usage_totals: Dict[str, int] = {}
    thinking_config = None

    # High-stakes agents may request extended thinking on the first turn (Anthropic only).
    # Off by default — enable with CRUCIBAI_ANTHROPIC_EXTENDED_THINKING=1 when your model supports it.
    _think_env = (os.environ.get("CRUCIBAI_ANTHROPIC_EXTENDED_THINKING") or "").strip().lower()
    if (
        agent_name.lower().replace("-", "_").replace(" ", "_") in THINKING_AGENTS
        and _think_env in ("1", "true", "yes", "on")
    ):
        thinking_config = {"type": "enabled", "budget_tokens": THINKING_BUDGET_TOKENS}
        logger.info(
            "runtime_engine: agent=%s — extended thinking enabled (budget=%d)",
            agent_name,
            THINKING_BUDGET_TOKENS,
        )

    start_time = time.time()

    while iterations < max_iterations:
        iterations += 1
        is_first_turn = iterations == 1

        try:
            response = await call_llm(
                messages=messages,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                thinking=thinking_config if is_first_turn else None,
            )
        except Exception as e:
            logger.warning("runtime_engine: agent=%s LLM error on iter %d: %s", agent_name, iterations, e)
            break

        stop_reason = response.get("stop_reason", "end_turn")
        content_blocks = response.get("content", [])
        _accumulate_usage(usage_totals, response.get("usage"))

        # Collect text output
        text_output = " ".join(
            b.get("text", "") for b in content_blocks if b.get("type") == "text"
        ).strip()

        # Add assistant response to messages
        messages.append({"role": "assistant", "content": content_blocks})

        if stop_reason == "end_turn":
            logger.info(
                "runtime_engine: agent=%s completed in %d iterations (%.1fs)",
                agent_name, iterations, time.time() - start_time,
            )
            break

        if stop_reason == "max_tokens":
            logger.warning(
                "runtime_engine: agent=%s hit max_tokens at iter %d — stopping",
                agent_name,
                iterations,
            )
            break

        if stop_reason == "tool_use":
            tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
            if not tool_uses:
                logger.warning("runtime_engine: agent=%s stop_reason=tool_use but no tool_use blocks", agent_name)
                break

            tool_results = await _execute_tools_batch(tool_uses, workspace_path)

            # Track files written
            for result in tool_results:
                content_str = result.get("content", "")
                if content_str.startswith("[written:"):
                    rel = content_str[len("[written:"):].rstrip("]").strip()
                    if rel not in files_written:
                        files_written.append(rel)

            messages.append({"role": "user", "content": tool_results})
            continue

        # Unknown stop reason
        logger.warning("runtime_engine: agent=%s unexpected stop_reason=%s", agent_name, stop_reason)
        break

    if iterations >= max_iterations:
        logger.warning("runtime_engine: agent=%s hit max_iterations=%d", agent_name, max_iterations)

    return {
        "agent_name": agent_name,
        "iterations": iterations,
        "files_written": files_written,
        "elapsed_seconds": round(time.time() - start_time, 2),
        "messages": messages,
        "usage": usage_totals if usage_totals else None,
    }


async def run_text_agent_loop(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    workspace_path: str,
    call_text_llm: Callable,
    max_iterations: int = 5,
) -> Dict[str, Any]:
    """Provider-neutral tool loop for non-native tool-calling models.

    Models such as Cerebras may only return text through our fallback path. This
    loop gives them a small JSON tool protocol so they can still inspect and
    mutate the workspace over multiple turns.
    """

    protocol = """
You can use workspace tools by returning ONLY valid JSON:
{
  "tool_calls": [
    {"name": "list_files", "input": {"subdir": ""}},
    {"name": "read_file", "input": {"path": "src/App.jsx"}},
    {"name": "write_file", "input": {"path": "src/App.jsx", "content": "..."}},
    {"name": "edit_file", "input": {"path": "src/App.jsx", "old_str": "...", "new_str": "..."}},
    {"name": "run_command", "input": {"argv": ["npm", "run", "build"]}}
  ],
  "continue": true,
  "final": ""
}
When finished, return {"tool_calls": [], "continue": false, "final": "short summary"}.
Do not wrap JSON in markdown.
"""
    messages: List[Dict[str, Any]] = [
        {"role": "user", "content": user_message},
        {"role": "user", "content": "First inspect the workspace, then write or repair files as needed."},
    ]
    files_written: List[str] = []
    iterations = 0
    start_time = time.time()
    final_text = ""

    for index in range(max_iterations):
        iterations = index + 1
        prompt = (
            "\n\n".join(str(m.get("content") or "") for m in messages[-6:])
            + "\n\nReturn the next JSON tool envelope now."
        )
        try:
            response = await call_text_llm(
                message=prompt,
                system_message=(system_prompt or "") + "\n\n" + protocol,
                session_id=f"{agent_name}:provider_neutral_loop",
            )
        except Exception as exc:
            logger.warning("runtime_engine: provider-neutral loop LLM error for %s: %s", agent_name, exc)
            break

        text = response.get("text", "") if isinstance(response, dict) else str(response or "")
        envelope = _extract_json_object(text)
        if not envelope:
            final_text = text.strip()
            messages.append({"role": "assistant", "content": final_text})
            break

        calls = envelope.get("tool_calls") or envelope.get("tools") or []
        if not isinstance(calls, list):
            calls = []
        tool_uses: List[Dict[str, Any]] = []
        for i, call in enumerate(calls):
            if not isinstance(call, dict):
                continue
            name = str(call.get("name") or call.get("tool") or "").strip()
            if not name:
                continue
            tool_uses.append(
                {
                    "id": f"text-loop-{iterations}-{i}",
                    "name": name,
                    "input": call.get("input") if isinstance(call.get("input"), dict) else {},
                }
            )

        final_text = str(envelope.get("final") or "").strip()
        if not tool_uses:
            messages.append({"role": "assistant", "content": final_text})
            if not bool(envelope.get("continue")):
                break
            continue

        results = await _execute_tools_batch(tool_uses, workspace_path)
        for result in results:
            content_str = str(result.get("content") or "")
            if content_str.startswith("[written:") or content_str.startswith("[edited:"):
                rel = content_str.split(":", 1)[1].rstrip("]").strip()
                if rel and rel not in files_written:
                    files_written.append(rel)
        messages.append({"role": "assistant", "content": json.dumps(envelope)})
        messages.append({"role": "user", "content": json.dumps(results)})
        if not bool(envelope.get("continue", True)):
            break

    return {
        "agent_name": agent_name,
        "iterations": iterations,
        "files_written": files_written,
        "elapsed_seconds": round(time.time() - start_time, 2),
        "messages": messages,
        "final_text": final_text,
        "provider_neutral_tool_loop": True,
    }


def extract_final_assistant_text(messages: List[Dict[str, Any]]) -> str:
    """Concatenate text blocks from the last assistant message (tool-loop transcripts)."""
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                (b.get("text") or "").strip()
                for b in content
                if b.get("type") == "text"
            ]
            return " ".join(parts).strip()
    return ""


# ─── Task status helpers (FIX 16) ─────────────────────────────────────────────

async def get_task_status(job_id: str) -> Dict[str, Any]:
    """Get current task/job status from runtime state."""
    try:
        from .runtime_state_adapter import get_job_status
        return await get_job_status(job_id)
    except Exception as e:
        logger.debug("runtime_engine: get_task_status failed: %s", e)
        return {"job_id": job_id, "status": "unknown"}


async def update_task_status(job_id: str, status: str, **kwargs: Any) -> None:
    """Update task status in runtime state."""
    try:
        from .runtime_state_adapter import update_job_status
        await update_job_status(job_id, status, **kwargs)
    except Exception as e:
        logger.debug("runtime_engine: update_task_status failed: %s", e)


def select_agents(goal: str, build_profile: str) -> List[str]:
    """Select agent roster based on goal and build profile."""
    base = ["planner", "architect", "backend", "frontend", "security", "qa"]
    profile_agents = {
        "saas_ui": ["backend", "frontend", "auth", "payments", "deploy"],
        "automation": ["planner", "backend", "integrations", "deploy"],
        "api_backend": ["architect", "backend", "security", "deploy"],
        "mobile": ["planner", "frontend", "backend", "deploy"],
        "web_site": ["planner", "frontend", "deploy"],
    }
    return profile_agents.get(build_profile, base)


async def spawn_agent(
    agent_name: str,
    system_prompt: str,
    task: str,
    workspace_path: str,
    call_llm: Callable,
) -> Dict[str, Any]:
    """Spawn a single agent and run its agentic loop."""
    logger.info("runtime_engine: spawning agent=%s", agent_name)
    return await run_agent_loop(
        agent_name=agent_name,
        system_prompt=system_prompt,
        user_message=task,
        workspace_path=workspace_path,
        call_llm=call_llm,
    )
