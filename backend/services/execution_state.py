"""
Execution State — links a conversation session to its live execution context.

Every CrucibAI conversation that runs code gets an ExecutionState object.
It records:
  - which files are loaded into context (file_context)
  - every command that ran and its result (executed_commands)
  - the last error encountered (last_error)
  - every file modification made during this session (modifications)

ExecutionStateManager is a process-level singleton that maps
conversation_id → ExecutionState so the RepairEngine and RuntimeEngine
can always pick up where the last step left off without re-scanning disk.

Usage::

    from backend.services.execution_state import state_manager

    state = await state_manager.get_or_create(conversation_id, project_root)
    await state.apply_command("npm run build", result)
    await state.sync_from_disk()
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max files loaded into context (prevents huge memory usage on large projects).
_MAX_CONTEXT_FILES = 150
# Max bytes per file held in context (truncate larger files).
_MAX_FILE_BYTES = 64 * 1024  # 64 KB


class ExecutionState:
    """Mutable execution context for one conversation."""

    def __init__(self, conversation_id: str, project_root: str) -> None:
        self.conversation_id = conversation_id
        self.state_id = str(uuid.uuid4())[:8]
        self.project_root = project_root

        # {relative_path: str_content}
        self.file_context: Dict[str, str] = {}

        # List of {command, success, return_code, stdout, stderr, timestamp}
        self.executed_commands: List[Dict[str, Any]] = []

        # Last failed command result (or None)
        self.last_error: Optional[Dict[str, Any]] = None
        self.last_command: Optional[str] = None

        # {file, old_content, new_content, timestamp}
        self.modifications: List[Dict[str, Any]] = []

        self._created_at = time.time()
        self._updated_at = time.time()

    # ------------------------------------------------------------------ #
    #  Sync helpers                                                        #
    # ------------------------------------------------------------------ #

    async def sync_from_disk(self) -> None:
        """Reload file_context by walking project_root on disk."""
        if not os.path.isdir(self.project_root):
            logger.warning("sync_from_disk: project_root not found: %s", self.project_root)
            return

        loaded: Dict[str, str] = {}
        _skip_dirs = {"node_modules", ".git", "dist", "build", ".next",
                      "__pycache__", ".venv", "venv", ".cache"}

        for dirpath, dirnames, filenames in os.walk(self.project_root):
            # Prune skip-dirs in-place so os.walk won't descend
            dirnames[:] = [d for d in dirnames if d not in _skip_dirs]

            for fname in filenames:
                if fname.startswith("."):
                    continue
                full = os.path.join(dirpath, fname)
                rel  = os.path.relpath(full, self.project_root)
                if len(loaded) >= _MAX_CONTEXT_FILES:
                    break
                try:
                    size = os.path.getsize(full)
                    if size > _MAX_FILE_BYTES:
                        loaded[rel] = f"[truncated — {size} bytes]"
                    else:
                        with open(full, "r", encoding="utf-8", errors="replace") as fh:
                            loaded[rel] = fh.read()
                except OSError:
                    pass

        self.file_context = loaded
        self._updated_at = time.time()
        logger.debug("sync_from_disk: %d files loaded for conversation %s",
                     len(loaded), self.conversation_id)

    # ------------------------------------------------------------------ #
    #  Mutation helpers                                                    #
    # ------------------------------------------------------------------ #

    def apply_command(self, command: str, result: Dict[str, Any]) -> None:
        """Record a completed command execution."""
        record = {
            "command":     command,
            "success":     result.get("success", False),
            "return_code": result.get("return_code", -1),
            "stdout":      (result.get("stdout") or "")[:4096],
            "stderr":      (result.get("stderr") or "")[:4096],
            "duration_ms": result.get("duration_ms", 0.0),
            "timestamp":   time.time(),
        }
        self.executed_commands.append(record)
        self.last_command = command
        if not result.get("success"):
            self.last_error = record
        self._updated_at = time.time()

    def record_file_modification(
        self,
        relative_path: str,
        old_content: str,
        new_content: str,
    ) -> None:
        """Record a file change made by the repair or generation engine."""
        self.modifications.append({
            "file":        relative_path,
            "old_content": old_content[:2048],   # store truncated old for diffing
            "new_content": new_content[:2048],
            "timestamp":   time.time(),
        })
        self.file_context[relative_path] = new_content
        self._updated_at = time.time()

    def get_error_context(self) -> Dict[str, Any]:
        """Return a compact dict the RepairEngine can include in its prompt."""
        if not self.last_error:
            return {}
        return {
            "last_command":  self.last_error.get("command"),
            "return_code":   self.last_error.get("return_code"),
            "stderr":        self.last_error.get("stderr", "")[:2000],
            "stdout":        self.last_error.get("stdout", "")[:2000],
            "attempt_count": sum(
                1 for c in self.executed_commands
                if c["command"] == self.last_error.get("command") and not c["success"]
            ),
        }

    def summary(self) -> Dict[str, Any]:
        """Return a lightweight summary for logging / debug endpoints."""
        return {
            "conversation_id": self.conversation_id,
            "state_id":        self.state_id,
            "project_root":    self.project_root,
            "files_in_context": len(self.file_context),
            "commands_run":    len(self.executed_commands),
            "modifications":   len(self.modifications),
            "has_last_error":  self.last_error is not None,
            "age_s":           round(time.time() - self._created_at, 1),
        }


# --------------------------------------------------------------------------- #
#  Manager                                                                     #
# --------------------------------------------------------------------------- #

class ExecutionStateManager:
    """Process-level registry of ExecutionState objects, keyed by conversation_id."""

    def __init__(self) -> None:
        self._states: Dict[str, ExecutionState] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        conversation_id: str,
        project_root: str,
        *,
        sync_disk: bool = False,
    ) -> ExecutionState:
        """Return existing state or create a fresh one.

        If *sync_disk* is True the file context is refreshed from disk
        before returning (useful at the start of a new build run).
        """
        async with self._lock:
            if conversation_id not in self._states:
                state = ExecutionState(conversation_id, project_root)
                self._states[conversation_id] = state
                logger.info("ExecutionState created for conversation %s", conversation_id)
            else:
                state = self._states[conversation_id]
                # Update project root if it changed (project switch)
                if state.project_root != project_root:
                    state.project_root = project_root
                    state.file_context = {}

        if sync_disk:
            await state.sync_from_disk()
        return state

    def get(self, conversation_id: str) -> Optional[ExecutionState]:
        """Return state if it exists, else None (non-async, for hot paths)."""
        return self._states.get(conversation_id)

    async def evict(self, conversation_id: str) -> None:
        """Remove state for a conversation (e.g., when session ends)."""
        async with self._lock:
            self._states.pop(conversation_id, None)

    async def evict_stale(self, max_age_s: float = 3600.0) -> int:
        """Remove states older than *max_age_s* seconds. Returns count evicted."""
        now = time.time()
        async with self._lock:
            stale = [
                cid for cid, s in self._states.items()
                if (now - s._updated_at) > max_age_s
            ]
            for cid in stale:
                del self._states[cid]
        if stale:
            logger.info("ExecutionStateManager: evicted %d stale states", len(stale))
        return len(stale)

    def all_summaries(self) -> List[Dict[str, Any]]:
        return [s.summary() for s in self._states.values()]


# Module-level singleton.
state_manager = ExecutionStateManager()
