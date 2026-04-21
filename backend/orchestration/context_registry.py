"""
Lightweight workspace context registry (disk) — tracks which steps last touched paths.

Full symbol/contract validation belongs in later phases; this is durable metadata for
resume, debugging, and future governor checks without rewriting agents.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

REGISTRY_REL_DIR = ".crucibai"
REGISTRY_FILENAME = "context_registry.json"


def _safe_rel_path(p: str) -> str:
    s = str(p or "").strip().replace("\\", "/")
    if not s or ".." in s:
        return ""
    return s if s.startswith("/") else f"/{s.lstrip('/')}"


def _ext_for(path: str) -> str:
    try:
        return Path(path).suffix.lower()
    except Exception:
        return ""


def merge_file_ownership(
    workspace_path: str,
    *,
    job_id: str,
    step_key: str,
    paths: List[str],
    verification_status: str = "verified",
) -> None:
    """Upsert path entries under workspace/.crucibai/context_registry.json (best-effort)."""
    root = (workspace_path or "").strip()
    if not root or not paths:
        return
    base = Path(root)
    reg_dir = base / REGISTRY_REL_DIR
    reg_path = reg_dir / REGISTRY_FILENAME
    try:
        reg_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.debug("context_registry: mkdir skipped %s", e)
        return

    data: Dict[str, Any]
    if reg_path.is_file():
        try:
            raw = reg_path.read_text(encoding="utf-8", errors="replace")
            parsed = json.loads(raw)
            data = parsed if isinstance(parsed, dict) else {}
        except Exception:
            data = {}
    else:
        data = {}

    data.setdefault("version", 1)
    files = data.get("files")
    if not isinstance(files, dict):
        files = {}
    data["files"] = files

    base_resolved = base.resolve()

    now = datetime.now(timezone.utc).isoformat()
    data["updated_at"] = now
    data["job_id"] = job_id

    for raw in paths:
        rel = _safe_rel_path(raw)
        if not rel:
            continue
        try:
            rel_path = (base / rel.lstrip("/")).resolve()
            rel_path.relative_to(base_resolved)
        except (ValueError, OSError):
            continue
        files[rel] = {
            "last_step": step_key,
            "verification_status": verification_status,
            "ext": _ext_for(rel),
            "updated_at": now,
        }

    try:
        reg_path.write_text(
            json.dumps(data, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug("context_registry: write skipped %s", e)
