"""
runtime_engine.py — Agentic loop engine for CrucibAI (FIX 13-16).

Replaces one-shot LLM calls with a while(True) tool-use loop:
- Agent observes workspace, acts with file tools, inspects results
- Exits via stop_reason == "end_turn" or max_iterations
- Read-only tools run in parallel (asyncio.gather, up to 10)
- Write tools run serially to preserve consistency
- 15 high-stakes agents get thinking blocks (budget_tokens=8000)
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_LOOP_ITERATIONS = 12
PARALLEL_READ_LIMIT = 10

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
    else:
        return f"[unknown tool: {tool_name}]"


async def _execute_tools_batch(
    tool_uses: List[Dict[str, Any]],
    workspace_path: str,
) -> List[Dict[str, Any]]:
    """Execute tool calls: read-only in parallel (up to PARALLEL_READ_LIMIT), writes serially."""
    read_only = [t for t in tool_uses if t["name"] in READ_ONLY_TOOLS]
    writes = [t for t in tool_uses if t["name"] in WRITE_TOOLS]

    results: Dict[str, str] = {}

    # Parallel read-only tools
    if read_only:
        semaphore = asyncio.Semaphore(PARALLEL_READ_LIMIT)
        async def _bounded(tool):
            async with semaphore:
                return tool["id"], await _execute_tool(tool["name"], tool.get("input", {}), workspace_path)
        pairs = await asyncio.gather(*[_bounded(t) for t in read_only])
        for tid, result in pairs:
            results[tid] = result

    # Serial write tools
    for tool in writes:
        results[tool["id"]] = await _execute_tool(tool["name"], tool.get("input", {}), workspace_path)

    # Return in original order
    return [
        {"type": "tool_result", "tool_use_id": t["id"], "content": results.get(t["id"], "[no result]")}
        for t in tool_uses
    ]


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
    thinking_config = None

    # High-stakes agents get thinking blocks on first turn
    if agent_name.lower().replace("-", "_").replace(" ", "_") in THINKING_AGENTS:
        thinking_config = {"type": "enabled", "budget_tokens": THINKING_BUDGET_TOKENS}
        logger.info("runtime_engine: agent=%s — thinking enabled (budget=%d)", agent_name, THINKING_BUDGET_TOKENS)

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
