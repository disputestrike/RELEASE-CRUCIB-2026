"""File-backed task state storage for runtime task control."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from backend.config import WORKSPACE_ROOT
except ImportError:
    from backend.project_state import WORKSPACE_ROOT


TASKS_DIRNAME = "runtime_tasks"


def _tasks_dir(project_id: str) -> Path:
    safe_id = (project_id or "").replace("/", "_").replace("\\", "_")
    root = WORKSPACE_ROOT / safe_id / TASKS_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def task_path(project_id: str, task_id: str) -> Path:
    return _tasks_dir(project_id) / f"{task_id}.json"


def load_task(project_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    p = task_path(project_id, task_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_task(project_id: str, task_id: str, data: Dict[str, Any]) -> None:
    p = task_path(project_id, task_id)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_tasks(project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    root = _tasks_dir(project_id)
    rows: List[Dict[str, Any]] = []
    for f in root.glob("*.json"):
        try:
            rows.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    rows.sort(key=lambda r: float(r.get("updated_at") or r.get("created_at") or 0), reverse=True)
    n = max(1, min(int(limit), 1000))
    return rows[:n]


def delete_task(project_id: str, task_id: str) -> bool:
    p = task_path(project_id, task_id)
    if not p.exists():
        return False
    p.unlink(missing_ok=True)
    return True
