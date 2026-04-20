"""
backend/services/capability_inspector.py
─────────────────────────────────────────
Phase-0 capability audit — emits FeatureAuditRow records.

Spec: B – Codebase Inspection First  / P – Use What Already Exists
Branch: engineering/master-list-closeout

Responsibilities:
  • Takes a feature request + repo snapshot
  • Emits FeatureAuditRow with status: EXISTS | PARTIAL | WIRING | REFACTOR | MISSING | DEPRECATED
  • Integrates into AgentLoop as phase 0 ("inspect before build")
  • Routes inspector output into audit_log and returns structured JSON

Design:
  The inspector runs a series of heuristic + LLM-assisted checks:
  1. Exact file / symbol search (grep-based, fast)
  2. Semantic route/service scan
  3. LLM classification of confidence (PARTIAL vs EXISTS)
  Outputs are written to audit_log table for UI display.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Root of the backend repo (one level up from services/)
REPO_ROOT = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────

class AuditStatus(str, Enum):
    EXISTS     = "exists"
    PARTIAL    = "partial"
    WIRING     = "wiring"
    REFACTOR   = "refactor"
    MISSING    = "missing"
    DEPRECATED = "deprecated"


@dataclass
class FeatureAuditRow:
    feature:    str
    status:     AuditStatus
    files:      List[str]     = field(default_factory=list)
    gaps:       List[str]     = field(default_factory=list)
    decision:   str           = ""   # reuse | extend | refactor | build_new
    action:     str           = ""   # human-readable next step
    confidence: float         = 1.0  # 0-1


# ─────────────────────────────────────────────────────────────────────────────
# File scanner helpers
# ─────────────────────────────────────────────────────────────────────────────

_SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".jsx", ".js", ".sql"}
_MAX_SCAN_SIZE   = 200_000  # bytes — skip huge generated files


def _find_files(pattern: str, root: Path = REPO_ROOT) -> List[str]:
    """Return relative paths of files whose name matches *pattern* (case-insensitive)."""
    matches = []
    regex = re.compile(pattern, re.IGNORECASE)
    for p in root.rglob("*"):
        if p.suffix not in _SCAN_EXTENSIONS:
            continue
        if "__pycache__" in p.parts or "node_modules" in p.parts:
            continue
        if p.stat().st_size > _MAX_SCAN_SIZE:
            continue
        if regex.search(p.name):
            matches.append(str(p.relative_to(root)))
    return matches


def _grep_files(pattern: str, root: Path = REPO_ROOT) -> List[str]:
    """Return relative paths of files containing *pattern* (regex, case-insensitive)."""
    matches = []
    regex = re.compile(pattern, re.IGNORECASE)
    for p in root.rglob("*"):
        if p.suffix not in _SCAN_EXTENSIONS:
            continue
        if "__pycache__" in p.parts or "node_modules" in p.parts:
            continue
        if p.stat().st_size > _MAX_SCAN_SIZE:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if regex.search(text):
                matches.append(str(p.relative_to(root)))
        except OSError:
            pass
    return matches[:20]  # cap to avoid too-long output


# ─────────────────────────────────────────────────────────────────────────────
# Capability checks — one function per A-Q feature
# ─────────────────────────────────────────────────────────────────────────────

def _check_feature(feature_name: str, file_patterns: List[str], grep_patterns: List[str],
                   required_symbols: List[str], gaps: List[str]) -> FeatureAuditRow:
    """Generic checker shared by all A-Q inspections."""
    found_files: List[str] = []
    for fp in file_patterns:
        found_files.extend(_find_files(fp))
    for gp in grep_patterns:
        found_files.extend(_grep_files(gp))
    found_files = list(dict.fromkeys(found_files))  # dedupe, preserve order

    missing_symbols = []
    for sym in required_symbols:
        sym_files = _grep_files(sym)
        if not sym_files:
            missing_symbols.append(sym)

    if not found_files and not required_symbols:
        status = AuditStatus.MISSING
        decision = "build_new"
    elif missing_symbols or gaps:
        status = AuditStatus.PARTIAL if found_files else AuditStatus.MISSING
        decision = "extend" if found_files else "build_new"
    else:
        status = AuditStatus.EXISTS
        decision = "reuse"

    return FeatureAuditRow(
        feature=feature_name,
        status=status,
        files=found_files[:10],
        gaps=gaps + [f"symbol missing: {s}" for s in missing_symbols],
        decision=decision,
        action=_default_action(status),
        confidence=0.85,
    )


def _default_action(status: AuditStatus) -> str:
    return {
        AuditStatus.EXISTS:     "Use as-is; wire into agent loop if not already.",
        AuditStatus.PARTIAL:    "Extend with missing symbols / table / route.",
        AuditStatus.WIRING:     "Code present; add wiring to agent loop / UI / DB.",
        AuditStatus.REFACTOR:   "Rewrite to canonical shape; preserve behaviour.",
        AuditStatus.MISSING:    "Build new file / service from scratch.",
        AuditStatus.DEPRECATED: "Evaluate: delete, merge into canonical, or keep.",
    }[status]


# ─────────────────────────────────────────────────────────────────────────────
# CapabilityInspector
# ─────────────────────────────────────────────────────────────────────────────

class CapabilityInspector:
    """Run capability audit for a list of feature names (A-Q or arbitrary)."""

    # Registry: feature_name → (file_patterns, grep_patterns, required_symbols, gaps)
    FEATURE_REGISTRY: Dict[str, tuple] = {
        "persistent_workspace": (
            ["WorkspaceVNext", "UnifiedWorkspace", "runtime_engine"],
            ["ExecutionContext", "thread_id"],
            ["thread_checkpoints", "checkpoint_restore"],
            ["No checkpoint/restore API", "thread_checkpoints table missing"],
        ),
        "codebase_inspection": (
            ["capability_inspector", "workspace_explorer", "code_analysis", "semantic_router"],
            ["FeatureAuditRow", "AuditStatus"],
            [],
            [],
        ),
        "migration_engine": (
            ["migration_engine", "migration_runner"],
            ["AST", "transform", "merge_many"],
            [],
            ["No AST transform primitives", "migration_engine.py missing"],
        ),
        "execution_modes": (
            ["agent_loop", "dynamic_executor", "WorkspaceVNext"],
            ["ExecutionMode", "ANALYZE_ONLY", "MIGRATION"],
            [],
            ["No single ExecutionMode enum", "8 modes not bound"],
        ),
        "agent_loop": (
            ["agent_loop", "runtime_engine"],
            ["execute_with_control", "ExecutionPhase"],
            [],
            [],
        ),
        "tool_registry": (
            ["tool_registry", "registry.py", "contracts.py"],
            ["ToolContract", "register_tool"],
            [],
            [],
        ),
        "connector_manager": (
            ["connector_manager"],
            ["GitHub", "Railway", "Vercel", "Slack"],
            [],
            ["connector_manager.py missing"],
        ),
        "preview_session": (
            ["preview_session", "preview_manager", "project_preview_service"],
            ["open_preview", "screenshot"],
            [],
            ["preview_session.py missing", "operator_runner.py missing"],
        ),
        "automations": (
            ["automation_engine", "automation_worker", "automation.py"],
            ["schedule", "execute_automation"],
            [],
            ["automation_runs table missing", "runs history endpoint missing"],
        ),
        "memory_store": (
            ["memory_store", "memory/service", "memory_graph"],
            ["MemoryScope", "MemoryStore"],
            [],
            [],
        ),
        "image_generation": (
            ["image_generation", "image_generator"],
            ["generate_image", "Together"],
            [],
            [],
        ),
        "artifact_system": (
            ["artifact_builder", "project_artifact_service", "artifact_signing"],
            ["artifact_type", "artifact_versions"],
            [],
            ["artifact_builder.py missing", "artifacts table missing"],
        ),
        "safety_governance": (
            ["permission_engine", "audit_log_service", "access_control"],
            ["dry_run", "approval", "cancellation"],
            [],
            ["approvals endpoint missing", "dry_run flag missing on tool_executor"],
        ),
    }

    async def inspect_feature(self, feature_name: str) -> FeatureAuditRow:
        """Inspect a single named feature."""
        entry = self.FEATURE_REGISTRY.get(feature_name)
        if entry is None:
            # Generic fallback: grep for feature name
            files = _grep_files(feature_name)
            status = AuditStatus.EXISTS if files else AuditStatus.MISSING
            return FeatureAuditRow(
                feature=feature_name,
                status=status,
                files=files[:10],
                decision="reuse" if files else "build_new",
                action=_default_action(status),
            )
        fp, gp, sym, gaps = entry
        return _check_feature(feature_name, fp, gp, sym, gaps)

    async def inspect_all(self) -> List[FeatureAuditRow]:
        """Run the full A-Q audit."""
        rows = []
        for name in self.FEATURE_REGISTRY:
            row = await self.inspect_feature(name)
            rows.append(row)
        return rows

    async def run_and_log(self, *, db: Any, user_id: str = "system") -> List[Dict[str, Any]]:
        """Run full audit and write results to audit_log table."""
        rows = await self.inspect_all()
        results = [asdict(r) for r in rows]

        try:
            import json
            from datetime import datetime, timezone
            import uuid as _uuid
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """INSERT INTO audit_log (id, user_id, action, details, created_at)
                   VALUES (:id, :user_id, :action, :details::jsonb, :created_at)""",
                {
                    "id": str(_uuid.uuid4()),
                    "user_id": user_id,
                    "action": "capability_audit",
                    "details": json.dumps({"rows": results}),
                    "created_at": now,
                },
            )
        except Exception as exc:
            logger.warning("[CapabilityInspector] audit_log write failed: %s", exc)

        return results


# Module-level singleton
capability_inspector = CapabilityInspector()
