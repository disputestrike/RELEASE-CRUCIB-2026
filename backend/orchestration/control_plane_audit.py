"""
Minimal Claude-parity audit hook: structured logs for gated writes and policy-adjacent decisions.

Full task_manager / tool_policy lives in docs; this module gives one auditable choke point.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def log_write_gate_violation(
    *,
    rel: str,
    reasons: List[str],
    job_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "audit": "write_gate_blocked",
        "path": rel.replace("\\", "/"),
        "reasons": [str(r) for r in (reasons or [])[:12]],
        "job_id": job_id,
    }
    if extra:
        payload["extra"] = extra
    try:
        logger.warning("control_plane_audit %s", json.dumps(payload, default=str)[:8000])
    except Exception:
        logger.warning("control_plane_audit write_gate_blocked path=%s job=%s", rel, job_id)
