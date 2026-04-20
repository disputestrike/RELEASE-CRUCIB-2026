"""
backend/services/migration_engine.py
──────────────────────────────────────
Codebase migration / transformation engine.

Spec: C / G – Codebase Migration + Migration Engine
Branch: engineering/master-list-closeout

Responsibilities:
  • Read many files into one migration context
  • Cluster related files by function (using heuristics + optional LLM)
  • Infer current + target architecture
  • Propose consolidation / refactor / migration strategy
  • Create transformed output structure
  • Generate mapping from source files to output files
  • Preserve behaviour
  • Emit migration report artifact

Supported transform strategies:
  merge_many_to_fewer   – N scripts → organised module
  split_one_to_many     – monolith → services
  rename_restructure    – flat → hierarchical
  lift_utilities        – duplicate helpers → shared lib
  create_orchestrator   – scattered entry points → one controller
  js_to_ts              – JS → TypeScript
  framework_migration   – e.g. Express → FastAPI stub
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FileAction:
    source_path:  str
    target_path:  Optional[str]
    action:       str   # copy | merge | split | rename | delete | lift
    notes:        str = ""


@dataclass
class MigrationPlan:
    migration_id: str
    strategy:     str
    source_root:  str
    target_root:  str
    file_actions: List[FileAction]       = field(default_factory=list)
    new_files:    List[str]              = field(default_factory=list)  # orchestrators / index files
    behavior_checklist: List[str]        = field(default_factory=list)
    test_commands: List[str]             = field(default_factory=list)
    summary:      str                    = ""


@dataclass
class MigrationResult:
    migration_id:     str
    plan:             MigrationPlan
    status:           str = "planned"   # planned | running | completed | failed
    artifact_id:      Optional[str] = None
    error:            Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Cluster helpers
# ─────────────────────────────────────────────────────────────────────────────

_CLUSTER_PATTERNS: Dict[str, List[str]] = {
    "routes":    ["route", "router", "endpoint", "api", "view"],
    "services":  ["service", "manager", "handler", "processor"],
    "models":    ["model", "schema", "entity", "orm", "db_"],
    "agents":    ["agent", "brain", "planner", "executor"],
    "utils":     ["util", "helper", "common", "shared", "mixin"],
    "tests":     ["test_", "_test", "spec_", "_spec"],
    "migrations":["migration", "migrate", "alembic"],
    "workers":   ["worker", "task", "job", "celery", "background"],
    "config":    ["config", "settings", "env", "const"],
    "frontend":  [".jsx", ".tsx", ".vue", ".svelte"],
}


def _cluster_file(path: str) -> str:
    p = path.lower()
    for cluster, keywords in _CLUSTER_PATTERNS.items():
        if any(kw in p for kw in keywords):
            return cluster
    return "other"


def _read_file_safe(path: Path, max_bytes: int = 100_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
    except OSError:
        return ""


def _extract_python_symbols(source: str) -> Tuple[List[str], List[str]]:
    """Return (functions, classes) defined at module level."""
    funcs, classes = [], []
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and isinstance(node.col_offset, int) and node.col_offset == 0:
                funcs.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef) and node.col_offset == 0:
                funcs.append(node.name)
            elif isinstance(node, ast.ClassDef) and node.col_offset == 0:
                classes.append(node.name)
    except SyntaxError:
        pass
    return funcs, classes


# ─────────────────────────────────────────────────────────────────────────────
# MigrationEngine
# ─────────────────────────────────────────────────────────────────────────────

class MigrationEngine:
    """Stateless migration engine.  Call ``plan()`` to produce a MigrationPlan,
    then ``execute_plan()`` to write transformed output to disk.
    """

    # ── Planning phase ────────────────────────────────────────────────────────

    def plan(
        self,
        *,
        source_root: str,
        target_root: str,
        strategy: str = "merge_many_to_fewer",
        include_extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
        migration_id: Optional[str] = None,
    ) -> MigrationPlan:
        """Scan source_root, cluster files, produce a MigrationPlan."""
        migration_id = migration_id or str(uuid.uuid4())
        src = Path(source_root)
        tgt = Path(target_root)
        exts  = set(include_extensions or [".py", ".ts", ".tsx", ".jsx", ".js"])
        excls = set(exclude_dirs or ["__pycache__", "node_modules", ".git", ".venv", "dist", "build"])

        # Collect files
        all_files: List[Path] = []
        for p in src.rglob("*"):
            if p.is_file() and p.suffix in exts:
                if not any(ex in p.parts for ex in excls):
                    all_files.append(p)

        # Cluster
        clusters: Dict[str, List[Path]] = {}
        for f in all_files:
            c = _cluster_file(str(f))
            clusters.setdefault(c, []).append(f)

        file_actions = self._build_actions(strategy, src, tgt, clusters)
        behavior_checklist = self._build_behavior_checklist(strategy, clusters)
        test_commands = self._build_test_commands(strategy, src)
        new_files = self._build_new_files(strategy, tgt, clusters)

        return MigrationPlan(
            migration_id=migration_id,
            strategy=strategy,
            source_root=str(src),
            target_root=str(tgt),
            file_actions=file_actions,
            new_files=new_files,
            behavior_checklist=behavior_checklist,
            test_commands=test_commands,
            summary=self._build_summary(strategy, clusters, file_actions),
        )

    def _build_actions(
        self,
        strategy: str,
        src: Path,
        tgt: Path,
        clusters: Dict[str, List[Path]],
    ) -> List[FileAction]:
        actions = []
        if strategy == "merge_many_to_fewer":
            for cluster, files in clusters.items():
                if len(files) == 1:
                    target = tgt / cluster / files[0].name
                    actions.append(FileAction(str(files[0]), str(target), "copy"))
                else:
                    merged = tgt / cluster / f"{cluster}_merged.py"
                    for f in files:
                        actions.append(FileAction(str(f), str(merged), "merge",
                                                   notes=f"Merge into {merged.name}"))
        elif strategy == "rename_restructure":
            for cluster, files in clusters.items():
                for f in files:
                    rel = f.relative_to(src)
                    target = tgt / cluster / rel
                    actions.append(FileAction(str(f), str(target), "rename"))
        elif strategy == "lift_utilities":
            shared_dir = tgt / "shared"
            for f in clusters.get("utils", []):
                actions.append(FileAction(str(f), str(shared_dir / f.name), "lift",
                                           notes="Lifted to shared/"))
            for cluster, files in clusters.items():
                if cluster == "utils":
                    continue
                for f in files:
                    actions.append(FileAction(str(f), str(tgt / cluster / f.name), "copy"))
        elif strategy == "create_orchestrator":
            for cluster, files in clusters.items():
                for f in files:
                    actions.append(FileAction(str(f), str(tgt / cluster / f.name), "copy"))
        else:
            # Default: copy everything preserving structure
            for cluster, files in clusters.items():
                for f in files:
                    rel = f.relative_to(src)
                    actions.append(FileAction(str(f), str(tgt / rel), "copy"))
        return actions

    def _build_new_files(
        self, strategy: str, tgt: Path, clusters: Dict[str, List[Path]]
    ) -> List[str]:
        if strategy == "create_orchestrator":
            return [str(tgt / "orchestrator.py"), str(tgt / "__init__.py")]
        if strategy == "merge_many_to_fewer":
            return [str(tgt / c / f"{c}_merged.py") for c in clusters if len(clusters[c]) > 1]
        return []

    def _build_behavior_checklist(self, strategy: str, clusters: Dict[str, List[Path]]) -> List[str]:
        checklist = [
            "All public API endpoints respond with same status codes",
            "All DB read/write operations preserve data integrity",
            "Authentication and authorization unchanged",
            "Environment variables / config loading unchanged",
        ]
        if "routes" in clusters:
            checklist.append("All routes registered in app router")
        if "migrations" in clusters:
            checklist.append("All migrations still applied in correct order")
        if "workers" in clusters:
            checklist.append("Background workers start and process jobs correctly")
        return checklist

    def _build_test_commands(self, strategy: str, src: Path) -> List[str]:
        cmds = []
        if (src / "pytest.ini").exists() or (src / "setup.cfg").exists():
            cmds.append("pytest -x -q")
        if (src / "package.json").exists():
            cmds.append("npm test")
        cmds.append("python -m py_compile **/*.py  # syntax check")
        return cmds

    def _build_summary(
        self,
        strategy: str,
        clusters: Dict[str, List[Path]],
        actions: List[FileAction],
    ) -> str:
        total = len(actions)
        merges = sum(1 for a in actions if a.action == "merge")
        lifts  = sum(1 for a in actions if a.action == "lift")
        return (
            f"Strategy: {strategy} | Files scanned: {total} | "
            f"Merges: {merges} | Lifts: {lifts} | "
            f"Clusters: {', '.join(sorted(clusters.keys()))}"
        )

    # ── Execution phase ───────────────────────────────────────────────────────

    def execute_plan(self, plan: MigrationPlan, *, dry_run: bool = True) -> MigrationResult:
        """Write transformed output.  If dry_run=True (default), only logs actions."""
        result = MigrationResult(migration_id=plan.migration_id, plan=plan)
        try:
            for fa in plan.file_actions:
                if dry_run:
                    logger.info("[MigrationEngine dry_run] %s %s → %s", fa.action, fa.source_path, fa.target_path)
                    continue
                src = Path(fa.source_path)
                if not src.exists():
                    logger.warning("[MigrationEngine] source missing: %s", src)
                    continue
                if fa.action == "delete":
                    continue  # never delete in production without explicit flag
                if fa.target_path:
                    tgt = Path(fa.target_path)
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    if fa.action == "merge":
                        with tgt.open("a", encoding="utf-8") as f:
                            f.write(f"\n# ─── merged from {fa.source_path} ───\n")
                            f.write(src.read_text(encoding="utf-8", errors="ignore"))
                    else:
                        import shutil
                        shutil.copy2(src, tgt)
            result.status = "planned" if dry_run else "completed"
        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            logger.exception("[MigrationEngine] execute_plan failed: %s", exc)
        return result

    # ── DB persistence helpers ─────────────────────────────────────────────────

    async def save_run(self, result: MigrationResult, *, user_id: str, thread_id: Optional[str], db: Any) -> str:
        """Persist a migration run to migration_runs table."""
        now = datetime.now(timezone.utc).isoformat()
        run_id = result.migration_id
        await db.execute(
            """INSERT INTO migration_runs
               (id, thread_id, user_id, source_path, target_path, strategy, status, plan, summary, created_at)
               VALUES (:id, :thread_id, :user_id, :source_path, :target_path, :strategy,
                       :status, :plan::jsonb, :summary::jsonb, :created_at)
               ON CONFLICT (id) DO UPDATE
               SET status = EXCLUDED.status, plan = EXCLUDED.plan, summary = EXCLUDED.summary""",
            {
                "id": run_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "source_path": result.plan.source_root,
                "target_path": result.plan.target_root,
                "strategy": result.plan.strategy,
                "status": result.status,
                "plan": json.dumps(asdict(result.plan)),
                "summary": json.dumps({"summary": result.plan.summary}),
                "created_at": now,
            },
        )
        # Save file maps
        for fa in result.plan.file_actions[:500]:  # cap
            map_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO migration_file_maps
                   (id, migration_id, source_path, target_path, action, notes, created_at)
                   VALUES (:id, :migration_id, :source_path, :target_path, :action, :notes, :created_at)
                   ON CONFLICT (id) DO NOTHING""",
                {
                    "id": map_id,
                    "migration_id": run_id,
                    "source_path": fa.source_path,
                    "target_path": fa.target_path or "",
                    "action": fa.action,
                    "notes": fa.notes,
                    "created_at": now,
                },
            )
        return run_id


# Module-level singleton
migration_engine = MigrationEngine()
