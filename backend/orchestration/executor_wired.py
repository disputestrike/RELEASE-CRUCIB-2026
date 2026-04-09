"""
Compatibility executor shim for older wiring tests and scripts.

This module is intentionally thin. It does not define an alternate production
runtime; it delegates to the live memory, preview, and schema-planning modules
so callers that still import ``executor_wired`` stay aligned with the main path.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, Tuple

try:  # pragma: no cover - import style depends on PYTHONPATH
    from agents.database_architect_agent import heuristic_schema_from_requirements
    from agents.preview_validator_agent import PreviewValidatorAgent
    from memory.vector_db import get_vector_memory
except ImportError:  # pragma: no cover
    from backend.agents.database_architect_agent import heuristic_schema_from_requirements
    from backend.agents.preview_validator_agent import PreviewValidatorAgent
    from backend.memory.vector_db import get_vector_memory

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[1]
_DESIGN_SYSTEM_PATH = _ROOT / "design_system.json"
_DESIGN_PROMPT_PATH = _ROOT / "prompts" / "design_system_injection.txt"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("wired executor could not read %s: %s", path, exc)
        return {}


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("wired executor could not read %s: %s", path, exc)
        return ""


class WiredExecutor:
    """
    Legacy-compatible wrapper that uses the live helper modules.

    Supported features:
    - design system injection from committed artifacts
    - optional broadcast hooks for the live job-progress UI
    - heuristic schema planning for downstream database-aware work
    - vector-memory capture with safe in-memory fallback
    - preview preflight using PreviewValidatorAgent when a workspace exists
    """

    def __init__(self, job_id: str, project_id: str):
        self.job_id = job_id
        self.project_id = project_id
        self.broadcast_fn: Callable[..., Awaitable[None]] | None = None

    def set_broadcaster(self, broadcast_fn: Callable[..., Awaitable[None]]) -> None:
        self.broadcast_fn = broadcast_fn

    async def _broadcast(self, event_type: str, **payload: Any) -> None:
        if not self.broadcast_fn:
            return
        try:
            await self.broadcast_fn(self.job_id, event_type, **payload)
        except Exception:
            logger.debug("wired executor broadcast failed", exc_info=True)

    def _inject_design_system(self, context: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(context or {})
        enriched["design_system_injected"] = True
        enriched["design_system"] = _load_json(_DESIGN_SYSTEM_PATH)
        enriched["design_rules"] = enriched["design_system"]
        enriched["design_system_prompt"] = _load_text(_DESIGN_PROMPT_PATH)
        return enriched

    async def _store_memory(self, agent_name: str, result: Dict[str, Any], phase: str) -> None:
        text = (
            result.get("generated_code")
            or result.get("output")
            or result.get("summary")
            or ""
        )
        if not text:
            return
        try:
            vm = await get_vector_memory()
            await vm.add_memory(
                project_id=self.project_id,
                text=str(text)[:2000],
                memory_type="output",
                agent_name=agent_name,
                phase=phase,
                tokens=int(result.get("tokens_used") or 0),
            )
        except Exception:
            logger.debug("wired executor memory store failed", exc_info=True)

    async def _preview_preflight(self, workspace_path: str | None) -> Dict[str, Any] | None:
        if not workspace_path:
            return None
        workspace = Path(workspace_path)
        if not workspace.exists():
            return None
        validator = PreviewValidatorAgent()
        return await validator.execute({"workspace_path": str(workspace)})

    async def execute_agent(
        self,
        agent_name: str,
        agent_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        working_context = self._inject_design_system(context)
        phase_name = str(working_context.get("phase") or "unknown")
        await self._broadcast("agent_start", agent_name=agent_name, phase_id=phase_name)
        try:
            result = await agent_func(working_context)
            if not isinstance(result, dict):
                result = {"output": result}
            await self._store_memory(agent_name, result, phase_name)
            await self._broadcast(
                "agent_complete",
                agent_name=agent_name,
                phase_id=phase_name,
                summary=str(result.get("summary") or result.get("output") or "")[:200],
            )
            return result
        except Exception as exc:
            await self._broadcast(
                "agent_error",
                agent_name=agent_name,
                phase_id=phase_name,
                error=str(exc),
            )
            raise

    async def execute_build(
        self,
        agents_by_phase: Dict[str, Iterable[Tuple[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]]]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        start = datetime.utcnow()
        working_context = self._inject_design_system(context)
        requirements = (
            working_context.get("requirements")
            or working_context.get("user_requirements")
            or ""
        )
        if requirements and not working_context.get("database_schema"):
            working_context["database_schema"] = heuristic_schema_from_requirements(str(requirements)).dict()

        results: Dict[str, Dict[str, Any]] = {}
        for phase_name, phase_agents in agents_by_phase.items():
            working_context["phase"] = phase_name
            for agent_name, agent_func in phase_agents:
                results[agent_name] = await self.execute_agent(agent_name, agent_func, working_context)

        preview = await self._preview_preflight(working_context.get("workspace_path"))
        elapsed = (datetime.utcnow() - start).total_seconds()
        return {
            "status": "success",
            "results": results,
            "elapsed": elapsed,
            "database_schema": working_context.get("database_schema"),
            "preview_preflight": preview,
        }


_executors: Dict[str, WiredExecutor] = {}


def get_wired_executor(job_id: str, project_id: str) -> WiredExecutor:
    if job_id not in _executors:
        _executors[job_id] = WiredExecutor(job_id, project_id)
    return _executors[job_id]
