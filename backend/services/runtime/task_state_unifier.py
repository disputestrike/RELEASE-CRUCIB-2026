"""Phase 3 task-state unification helpers.

Mirrors TaskManager lifecycle records into runtime_state-compatible files so
legacy job/event consumers and runtime task consumers observe one task model.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

try:
    from backend.config import WORKSPACE_ROOT
except ImportError:
    from backend.project_state import WORKSPACE_ROOT


def _runtime_state_dir(project_id: str, task_id: str) -> Path:
    safe_project = (project_id or "runtime_compat").replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe_project / "runtime_state" / task_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def mirror_task_event(project_id: str, task_id: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Append lifecycle event into runtime_state/events.json."""
    root = _runtime_state_dir(project_id, task_id)
    events_path = root / "events.json"
    rows: List[Dict[str, Any]] = _load_json(events_path, [])
    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "job_id": task_id,
        "event_type": event_type,
        "payload_json": json.dumps(payload or {}, ensure_ascii=True),
        "created_at": time.time(),
    }
    rows.append(event)
    if len(rows) > 5000:
        rows = rows[-5000:]
    _save_json(events_path, rows)
    return event


def mirror_task_snapshot(project_id: str, task_id: str, task: Dict[str, Any]) -> None:
    """Write latest unified task snapshot into runtime_state/checkpoints.json."""
    root = _runtime_state_dir(project_id, task_id)
    checkpoints_path = root / "checkpoints.json"
    checkpoints = _load_json(checkpoints_path, {})
    checkpoints["task_latest"] = {
        "data": {
            "id": task.get("task_id"),
            "project_id": task.get("project_id"),
            "status": task.get("status"),
            "description": task.get("description"),
            "metadata": task.get("metadata") or {},
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
        },
        "updated_at": time.time(),
    }
    _save_json(checkpoints_path, checkpoints)
