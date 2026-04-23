from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import WORKSPACE_ROOT


def _safe_project_id(project_id: str) -> str:
    return (project_id or "unknown").replace("/", "_").replace("\\", "_")


def _journal_path(project_id: str) -> Path:
    root = WORKSPACE_ROOT / _safe_project_id(project_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "session_journal.jsonl"


def _max_entries() -> int:
    raw = (os.environ.get("CRUCIB_SESSION_JOURNAL_MAX_ENTRIES") or "5000").strip()
    try:
        value = int(raw)
    except Exception:
        return 5000
    return max(100, value)


def _enforce_retention(path: Path) -> None:
    max_entries = _max_entries()
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]
    if len(lines) <= max_entries:
        return
    kept = lines[-max_entries:]
    with path.open("w", encoding="utf-8") as f:
        f.writelines(kept)


def append_entry(
    project_id: str,
    *,
    entry_type: str,
    payload: Dict[str, Any],
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    entry = {
        "ts": int(time.time() * 1000),
        "project_id": project_id,
        "task_id": task_id,
        "session_id": session_id,
        "entry_type": entry_type,
        "payload": payload or {},
    }
    path = _journal_path(project_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")
    _enforce_retention(path)
    return entry


def list_entries(project_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
    path = _journal_path(project_id)
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    if limit <= 0:
        return entries
    return entries[-limit:]
