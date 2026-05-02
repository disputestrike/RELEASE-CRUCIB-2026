"""
fast_path_executor.py — Phase 4: <30-second fast path for small changes.

When a goal touches ≤3 files (edit colour, fix typo, add a field, etc.),
skip the full DAG and:
  1. Read the relevant workspace files
  2. Ask Cerebras/Claude for the minimal patch (JSON response)
  3. Write the patched files to disk
  4. Run the build smoke gate
  5. Return a completed result

The fast path is triggered automatically when:
  - A workspace already exists (not a blank-slate build)
  - The goal is classified as "small change" by the keyword heuristic
  - The workspace has ≤300 source files (safety cap)

Env vars:
  CRUCIBAI_DISABLE_FAST_PATH=1   disable entirely
  CRUCIBAI_FAST_PATH_MAX_FILES   how many files to include in context (default 20)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Small-change keyword heuristic ───────────────────────────────────────────

_SMALL_CHANGE_VERBS = (
    "change ", "update ", "fix ", "rename ", "add a ", "add an ",
    "remove ", "delete ", "replace ", "edit ", "modify ", "tweak ",
    "make the ", "set the ", "convert ", "move ", "swap ", "adjust ",
    "correct ", "hide ", "show ", "toggle ", "align ", "resize ",
    "reword ", "rewrite the ", "update the ", "fix the ",
)

_LARGE_CHANGE_SIGNALS = (
    "build ", "create ", "generate ", "implement ", "develop ",
    "add authentication", "add auth", "add payments", "add stripe",
    "database", "from scratch", "entire", "whole ", "full ",
    "new app", "new project", "new feature",
)


def is_small_change_goal(goal: str) -> bool:
    """Return True if this goal looks like a targeted small edit."""
    g = goal.lower().strip()
    if not g:
        return False
    # Hard disqualifiers
    if any(sig in g for sig in _LARGE_CHANGE_SIGNALS):
        return False
    # Positive signals — starts with an edit verb or is short
    has_edit_verb = any(g.startswith(v) or f" {v}" in g for v in _SMALL_CHANGE_VERBS)
    is_short = len(g.split()) <= 12
    return has_edit_verb or is_short


def _collect_workspace_files(
    workspace: str,
    max_files: int = 20,
) -> Dict[str, str]:
    """Collect source files from workspace, truncated for LLM context."""
    out: Dict[str, str] = {}
    skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", ".venv", "venv"}
    skip_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".ttf", ".map", ".lock"}
    count = 0
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in sorted(files):
            if count >= max_files:
                return out
            if Path(name).suffix.lower() in skip_exts:
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, workspace).replace("\\", "/")
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if len(content) > 8000:
                    content = content[:8000] + "\n... [truncated]"
                out[rel] = content
                count += 1
            except OSError:
                continue
    return out


def _build_fast_path_prompt(goal: str, files: Dict[str, str]) -> Tuple[str, str]:
    """Build system + user prompts for the fast-path LLM call."""
    system = """You are a senior full-stack developer making minimal targeted edits.

You will receive:
1. A goal describing a small change to make
2. The current workspace files

Your job:
- Identify ONLY the files that need to change (max 3 files)
- Return the COMPLETE updated content for each changed file
- Do NOT add unnecessary changes

Respond with ONLY valid JSON in this exact format:
{
  "files": {
    "path/to/file.jsx": "complete file content here",
    "path/to/other.css": "complete css here"
  },
  "summary": "one sentence describing what changed"
}

Rules:
- Include the FULL file content (not diffs or snippets)
- Maximum 3 files
- Paths must exactly match the input paths
- If no change is needed, return {"files": {}, "summary": "no change needed"}
"""

    file_listing = "\n".join(
        f"### {path}\n```\n{content}\n```" for path, content in list(files.items())[:20]
    )
    user = f"Goal: {goal}\n\nWorkspace files:\n{file_listing}"
    return system, user


async def _call_llm_for_patch(
    system: str,
    user: str,
    max_tokens: int = 8192,
) -> Optional[str]:
    """Call Cerebras (primary) then Anthropic (fallback) for the patch."""
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        try:
            from backend.llm_cerebras import invoke_cerebras_stream
            content = ""
            async for chunk in invoke_cerebras_stream(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.15,
            ):
                content += chunk
            if content.strip():
                return content
        except Exception as e:
            logger.warning("[FAST PATH] Cerebras failed: %s", e)

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        return None
    try:
        import anthropic as _anthropic
        from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model

        model = normalize_anthropic_model(
            os.environ.get("ANTHROPIC_MODEL"), default=ANTHROPIC_HAIKU_MODEL
        )
        client = _anthropic.AsyncAnthropic(api_key=anthropic_key)
        msg = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.15,
        )
        return msg.content[0].text if msg.content else None
    except Exception as e:
        logger.error("[FAST PATH] Anthropic call failed: %s", e)
        return None


def _extract_json(raw: str) -> Optional[dict]:
    """Extract JSON from LLM response, handling markdown fences."""
    raw = raw.strip()
    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()
    # Find first { ... }
    start = raw.find("{")
    if start == -1:
        return None
    # Find matching close brace
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


async def run_fast_path(
    job_id: str,
    goal: str,
    workspace_path: str,
    *,
    append_event_fn=None,
) -> Dict[str, Any]:
    """
    Execute the fast path. Returns:
    {
        "success": bool,
        "fast_path": True,
        "files_changed": [str],
        "summary": str,
        "duration_ms": int,
        "error": str|None,
    }
    """
    t0 = time.monotonic()

    async def _emit(event_type: str, payload: dict):
        if append_event_fn:
            try:
                await append_event_fn(job_id, event_type, payload)
            except Exception:
                pass

    await _emit("fast_path_started", {"goal": goal, "workspace": workspace_path})

    max_ctx_files = int(os.environ.get("CRUCIBAI_FAST_PATH_MAX_FILES", "20"))
    files = _collect_workspace_files(workspace_path, max_files=max_ctx_files)
    if not files:
        return _fail("No source files found in workspace", t0)

    logger.info("[FAST PATH] job=%s goal=%r files_in_ctx=%d", job_id, goal[:60], len(files))

    system, user = _build_fast_path_prompt(goal, files)

    await _emit("fast_path_llm_call", {"model": "cerebras/haiku", "files_in_context": len(files)})

    raw = await _call_llm_for_patch(system, user)
    if not raw:
        return _fail("LLM returned no response", t0)

    patch = _extract_json(raw)
    if patch is None:
        return _fail(f"Could not parse JSON from LLM response: {raw[:200]}", t0)

    changed_files = patch.get("files", {})
    summary = patch.get("summary", "changes applied")

    if not changed_files:
        return {
            "success": True,
            "fast_path": True,
            "files_changed": [],
            "summary": summary or "no change needed",
            "duration_ms": int((time.monotonic() - t0) * 1000),
            "error": None,
        }

    if len(changed_files) > 3:
        # Trim to first 3 — enforce the fast-path contract
        changed_files = dict(list(changed_files.items())[:3])

    # Write patched files
    written: List[str] = []
    for rel_path, content in changed_files.items():
        # Security: no path traversal
        safe = os.path.normpath(rel_path).lstrip("/\\")
        if ".." in safe:
            logger.warning("[FAST PATH] Skipping unsafe path: %s", rel_path)
            continue
        full = os.path.join(workspace_path, safe)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            written.append(safe)
            logger.info("[FAST PATH] Wrote %s (%d chars)", safe, len(content))
        except OSError as e:
            logger.warning("[FAST PATH] Could not write %s: %s", safe, e)

    await _emit("fast_path_files_written", {"files": written, "summary": summary})

    # Run build smoke gate on the patched workspace
    try:
        from backend.orchestration.build_smoke_gate import run_build_smoke
        smoke = await run_build_smoke(workspace_path, job_id=job_id)
        await _emit("build_smoke", {
            "passed": smoke.get("passed"),
            "skipped": smoke.get("skipped"),
            "dist_dir": smoke.get("dist_dir"),
            "file_count": smoke.get("file_count", 0),
            "has_index_html": smoke.get("has_index_html", False),
            "duration_ms": smoke.get("duration_ms", 0),
            "warning": smoke.get("warning"),
        })
    except Exception as se:
        logger.warning("[FAST PATH] Smoke gate error: %s", se)

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.info("[FAST PATH] DONE job=%s files=%d duration=%dms", job_id, len(written), duration_ms)

    return {
        "success": True,
        "fast_path": True,
        "files_changed": written,
        "summary": summary,
        "duration_ms": duration_ms,
        "error": None,
    }


def _fail(error: str, t0: float) -> Dict[str, Any]:
    logger.warning("[FAST PATH] FAIL: %s", error)
    return {
        "success": False,
        "fast_path": True,
        "files_changed": [],
        "summary": "",
        "duration_ms": int((time.monotonic() - t0) * 1000),
        "error": error,
    }
