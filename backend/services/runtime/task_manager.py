"""Task lifecycle manager with cancellation and persisted state."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional
from ...backend.agents.clarification_agent import IntentSchema

from ..events import event_bus
from .task_store import delete_task, list_tasks, load_task, save_task
from .task_state_unifier import mirror_task_event, mirror_task_snapshot


TERMINAL_STATUSES = {"completed", "failed", "killed"}


@dataclass
class TaskStatus:
    task_id: str
    project_id: str
    status: str
    description: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any]


class TaskManager:
    def __init__(self) -> None:
        self._lock = Lock()

    def create_task(self, project_id: str, description: str, metadata: Optional[Dict[str, Any]] = None, intent_schema: Optional[IntentSchema] = None) -> Dict[str, Any]:
        now = time.time()
        task_id = f"tsk_{uuid.uuid4().hex[:12]}"
        task = {
            "task_id": task_id,
            "project_id": project_id,
            "status": "running",
            "description": description,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {},
            "intent_schema": intent_schema.model_dump() if intent_schema else None,
        }
        with self._lock:
            save_task(project_id, task_id, task)
            mirror_task_snapshot(project_id, task_id, task)
            mirror_task_event(project_id, task_id, "task_created", task)
        event_bus.emit("task.started", task)
        event_bus.emit("task_start", task)
        return task

    def get_task(self, project_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        return load_task(project_id, task_id)

    def update_task(self, project_id: str, task_id: str, *, status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = load_task(project_id, task_id)
            if not task:
                return None
            if task.get("status") in TERMINAL_STATUSES:
                return task
            if status:
                task["status"] = status
            if metadata:
                merged = dict(task.get("metadata") or {})
                merged.update(metadata)
                task["metadata"] = merged
            task["updated_at"] = time.time()
            save_task(project_id, task_id, task)
            mirror_task_snapshot(project_id, task_id, task)
            mirror_task_event(project_id, task_id, "task_updated", task)
        event_bus.emit("task.updated", task)
        event_bus.emit("task_update", task)
        if task.get("status") in TERMINAL_STATUSES:
            event_bus.emit("task_end", task)
            if task.get("status") == "killed":
                event_bus.emit("task_cancelled", task)
        return task

    def kill_task(self, project_id: str, task_id: str, reason: str = "manual_kill") -> Optional[Dict[str, Any]]:
        return self.update_task(project_id, task_id, status="killed", metadata={"kill_reason": reason})

    def pause_task(self, project_id: str, task_id: str, reason: str = "manual_pause") -> Optional[Dict[str, Any]]:
        return self.update_task(project_id, task_id, status="paused", metadata={"pause_reason": reason})

    def resume_task(self, project_id: str, task_id: str, reason: str = "manual_resume") -> Optional[Dict[str, Any]]:
        return self.update_task(project_id, task_id, status="running", metadata={"resume_reason": reason})

    def list_project_tasks(self, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return list_tasks(project_id, limit=limit)

    def complete_task(self, project_id: str, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        return self.update_task(project_id, task_id, status="completed", metadata=metadata)

    def fail_task(self, project_id: str, task_id: str, error: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        m = dict(metadata or {})
        m["error"] = error
        return self.update_task(project_id, task_id, status="failed", metadata=m)

    def delete_task(self, project_id: str, task_id: str) -> bool:
        with self._lock:
            ok = delete_task(project_id, task_id)
        if ok:
            mirror_task_event(project_id, task_id, "task_deleted", {"project_id": project_id, "task_id": task_id})
            event_bus.emit("task.deleted", {"project_id": project_id, "task_id": task_id})
        return ok


# Shared singleton for now; can be replaced with DI later.
task_manager = TaskManager()
