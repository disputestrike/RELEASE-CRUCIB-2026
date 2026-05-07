"""Claude Code-style runtime backbone adapter for CrucibAI.

This module turns the generated-workspace runtime into an explicit
Claude Code-style loop: neutral session state, tool start/end events,
permission-aware tool semantics, and provider fallback. The clean-room
ClawSpring files are vendored under ``backend/third_party/clawspring`` and
are used as the architectural source for the event model:

- AgentState
- ToolStart / ToolEnd / TurnDone / PermissionRequest
- Tool registry shape

The adapter deliberately does not import Anthropic leaked/decompiled source.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Awaitable, Callable, Dict, List, Optional

RuntimeEventCallback = Callable[[str, Dict[str, Any]], Awaitable[None] | None]


@dataclass
class AgentState:
    messages: list = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    turn_count: int = 0


@dataclass
class ToolStart:
    name: str
    inputs: dict


@dataclass
class ToolEnd:
    name: str
    result: str
    permitted: bool = True


@dataclass
class TurnDone:
    input_tokens: int
    output_tokens: int


@dataclass
class PermissionRequest:
    description: str
    granted: bool = False


_TOOL_NAME_MAP = {
    "read_file": "Read",
    "list_files": "Glob",
    "search_files": "Grep",
    "write_file": "Write",
    "edit_file": "Edit",
    "run_command": "Bash",
}

_CANONICAL_TOOLS = {
    "Read": "read_file",
    "Glob": "search_files",
    "Grep": "grep_files",
    "Write": "write_file",
    "Edit": "edit_file",
    "Bash": "run_command",
}


def vendored_source_root() -> Path:
    return Path(__file__).resolve().parents[1] / "third_party" / "clawspring"


def backbone_available() -> bool:
    root = vendored_source_root()
    return (
        (root / "agent.py").exists()
        and (root / "tool_registry.py").exists()
        and (root / "LICENSE").exists()
    )


def _load_vendored_tool_registry() -> ModuleType:
    registry_path = vendored_source_root() / "tool_registry.py"
    spec = importlib.util.spec_from_file_location(
        "crucibai_vendored_clawspring_tool_registry",
        registry_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ClawSpring tool registry at {registry_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _workspace_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Read",
            "description": "Read a file from the generated workspace.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        },
        {
            "name": "Write",
            "description": "Create or replace a file in the generated workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "Edit",
            "description": "Replace text in an existing workspace file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["file_path", "old_string", "new_string"],
            },
        },
        {
            "name": "Bash",
            "description": "Run an allowlisted build, install, test, or inspection command.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "description": {"type": "string"},
                    "cwd": {"type": "string"},
                },
                "required": ["command"],
            },
        },
        {
            "name": "Glob",
            "description": "Find files by glob pattern in the workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "Grep",
            "description": "Search workspace file contents for a text pattern.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "include": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    ]


def get_claude_code_tool_definitions() -> List[Dict[str, Any]]:
    """Return schemas from the vendored ClawSpring ToolDef registry."""

    registry = _load_vendored_tool_registry()
    registry.clear_registry()
    for schema in _workspace_tool_schemas():
        # Execution is handled by CrucibAI's workspace sandbox, but the tool
        # catalog is registered through the clean-room ClawSpring registry.
        registry.register_tool(
            registry.ToolDef(
                name=schema["name"],
                schema=schema,
                func=lambda _params, _config: "",
                read_only=schema["name"] in {"Read", "Glob", "Grep"},
                concurrent_safe=schema["name"] in {"Read", "Glob", "Grep"},
            )
        )
    return registry.get_tool_schemas()


def normalize_claude_tool_name(tool_name: str) -> str:
    raw = str(tool_name or "").strip()
    if raw in _CANONICAL_TOOLS:
        return _CANONICAL_TOOLS[raw]
    return raw


def claude_tool_input_to_runtime(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Claude Code tool inputs to CrucibAI runtime tool inputs."""

    name = normalize_claude_tool_name(tool_name)
    raw = dict(tool_input or {})
    if name in {"read_file", "write_file", "edit_file"}:
        if "file_path" in raw and "path" not in raw:
            raw["path"] = raw["file_path"]
        if "old_string" in raw and "old_str" not in raw:
            raw["old_str"] = raw["old_string"]
        if "new_string" in raw and "new_str" not in raw:
            raw["new_str"] = raw["new_string"]
    elif name == "search_files":
        raw.setdefault("pattern", raw.get("glob") or raw.get("file_pattern") or "*")
    elif name == "grep_files":
        raw.setdefault("pattern", raw.get("query") or raw.get("regex") or "")
        raw.setdefault("subdir", raw.get("path") or "")
    elif name == "run_command":
        command = raw.get("command")
        if isinstance(command, list) and "argv" not in raw:
            raw["argv"] = command
        elif isinstance(command, str) and "argv" not in raw:
            import shlex

            raw["argv"] = shlex.split(command, posix=False)
    return raw


def build_backbone_system_prompt(base_prompt: str) -> str:
    """Fuse the existing build prompt into the Claude Code runtime contract."""

    return (
        f"{base_prompt.rstrip()}\n\n"
        "CLAUDE CODE BACKBONE RUNTIME\n"
        "- Operate as a tool-driven coding agent, not a one-shot generator.\n"
        "- Inspect the workspace before edits.\n"
        "- Use Read/Glob/Grep semantics for understanding, Write/Edit for code changes, "
        "and Bash for build/test proof.\n"
        "- Continue the loop through failures: collect command output, identify root cause, "
        "patch files, rerun proof.\n"
        "- The preview pane is CrucibAI-specific: generated apps must build into a real preview "
        "artifact or a live dev/serve URL.\n"
        "- Do not default to SaaS, billing, PayPal, or subscriptions unless the user request "
        "or BuildContract explicitly requires them.\n"
    )


async def _emit(
    callback: Optional[RuntimeEventCallback],
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    if callback is None:
        return
    result = callback(event_type, payload)
    if asyncio.iscoroutine(result):
        await result


def _mapped_tool_name(payload: Dict[str, Any]) -> str:
    raw = str(payload.get("tool_name") or payload.get("name") or payload.get("tool") or "")
    return _TOOL_NAME_MAP.get(raw, raw or "Tool")


def make_backbone_event_callback(
    downstream: Optional[RuntimeEventCallback],
    state: Optional[AgentState] = None,
) -> RuntimeEventCallback:
    """Forward normal UI events and add Claude Code-style transcript events."""

    state = state or AgentState()

    async def _callback(event_type: str, payload: Dict[str, Any]) -> None:
        await _emit(downstream, event_type, payload)

        if event_type == "tool_call":
            event = ToolStart(_mapped_tool_name(payload), dict(payload or {}))
            state.messages.append({"role": "tool_start", **asdict(event)})
            await _emit(
                downstream,
                "claude_code_tool_start",
                {
                    "backbone": "clawspring_clean_room",
                    "event": "ToolStart",
                    "name": event.name,
                    "inputs": event.inputs,
                },
            )
        elif event_type == "tool_result":
            output = str(payload.get("output") or "")
            event = ToolEnd(
                _mapped_tool_name(payload),
                output,
                permitted=bool(payload.get("success", True)),
            )
            state.messages.append({"role": "tool_end", **asdict(event)})
            await _emit(
                downstream,
                "claude_code_tool_end",
                {
                    "backbone": "clawspring_clean_room",
                    "event": "ToolEnd",
                    "name": event.name,
                    "result": event.result,
                    "permitted": event.permitted,
                },
            )

    return _callback


async def write_backbone_proof(workspace_path: str, payload: Dict[str, Any]) -> str:
    root = Path(workspace_path)
    proof_dir = root / ".crucibai"
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / "claude_code_backbone.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path.relative_to(root)).replace("\\", "/")


async def run_generation_with_backbone(
    *,
    agent_name: str,
    system_prompt: str,
    user_message: str,
    workspace_path: str,
    loop_type: str,
    caller: Callable,
    run_agent_loop: Callable,
    run_text_agent_loop: Callable,
    has_text_fallback: Callable[[], bool],
    make_text_fallback: Callable[[], Callable],
    max_iterations: int,
    text_max_iterations: int,
    timeout_seconds: float,
    on_event: Optional[RuntimeEventCallback] = None,
) -> Dict[str, Any]:
    """Run generation through the Claude Code-style backbone adapter."""

    state = AgentState(messages=[{"role": "user", "content": user_message}])
    backbone_events = make_backbone_event_callback(on_event, state)
    fused_prompt = build_backbone_system_prompt(system_prompt)
    start = time.time()

    await _emit(
        on_event,
        "claude_code_backbone_started",
        {
            "source": "clawspring_clean_room",
            "vendored": backbone_available(),
            "vendored_path": str(vendored_source_root()),
            "loop_type": loop_type,
            "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        },
    )

    async def _run_text(reason: str) -> Dict[str, Any]:
        await _emit(
            on_event,
            "provider_fallback",
            {"from": "native_tool_loop", "to": "provider_neutral_text_loop", "reason": reason},
        )
        result = await asyncio.wait_for(
            run_text_agent_loop(
                agent_name=agent_name,
                system_prompt=fused_prompt,
                user_message=user_message,
                workspace_path=workspace_path,
                call_text_llm=make_text_fallback(),
                max_iterations=text_max_iterations,
                on_event=backbone_events,
            ),
            timeout=timeout_seconds,
        )
        result["provider_fallback"] = {
            "from": "native_tool_loop",
            "to": "provider_neutral_text_loop",
            "reason": reason,
        }
        return result

    if loop_type == "native":
        try:
            result = await asyncio.wait_for(
                run_agent_loop(
                    agent_name=agent_name,
                    system_prompt=fused_prompt,
                    user_message=user_message,
                    workspace_path=workspace_path,
                    call_llm=caller,
                    max_iterations=max_iterations,
                    on_event=backbone_events,
                ),
                timeout=timeout_seconds,
            )
        except Exception as exc:
            if not has_text_fallback():
                raise
            result = await _run_text(str(exc)[:240])
        else:
            if not (result.get("files_written") or []) and has_text_fallback():
                fallback = await _run_text("native_returned_no_files")
                if fallback.get("files_written") or not result:
                    result = fallback
    else:
        result = await asyncio.wait_for(
            run_text_agent_loop(
                agent_name=agent_name,
                system_prompt=fused_prompt,
                user_message=user_message,
                workspace_path=workspace_path,
                call_text_llm=caller,
                max_iterations=text_max_iterations,
                on_event=backbone_events,
            ),
            timeout=timeout_seconds,
        )

    state.turn_count = int(result.get("iterations") or 0)
    usage = result.get("usage") or {}
    state.total_input_tokens = int(usage.get("input_tokens") or 0)
    state.total_output_tokens = int(usage.get("output_tokens") or 0)
    done = TurnDone(state.total_input_tokens, state.total_output_tokens)
    state.messages.append({"role": "turn_done", **asdict(done)})
    result["claude_code_backbone"] = {
        "source": "clawspring_clean_room",
        "vendored": backbone_available(),
        "event_count": len(state.messages),
        "turn_count": state.turn_count,
        "elapsed_seconds": round(time.time() - start, 2),
    }
    proof_path = await write_backbone_proof(workspace_path, result["claude_code_backbone"])
    result["claude_code_backbone"]["proof_path"] = proof_path
    await _emit(on_event, "claude_code_backbone_done", result["claude_code_backbone"])
    return result
