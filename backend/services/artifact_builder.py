"""
backend/services/artifact_builder.py
──────────────────────────────────────
Unified artifact builder — orchestrates all artifact types.

Spec: L – Artifact System
Branch: engineering/master-list-closeout

Artifact types:
  product_spec | implementation_plan | migration_report | codebase_audit
  bug_report | test_report | screenshot_pack | file_action_map
  pdf | presentation | proof_bundle | handoff_bundle | image

All artifacts are:
  • versioned (artifact_versions table)
  • downloadable (download_url field)
  • thread-linked (thread_id field)
  • visible in the artifacts rail

Delegates rendering to:
  • pdf_renderer.py       — PDF output
  • slides_renderer.py    — PPTX/HTML slides
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ARTIFACT_STORAGE_DIR = os.environ.get("ARTIFACT_STORAGE_DIR", "/tmp/crucibai_artifacts")


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArtifactRecord:
    id:            str
    thread_id:     Optional[str]
    run_id:        Optional[str]
    user_id:       str
    artifact_type: str
    title:         str
    storage_path:  Optional[str]
    download_url:  Optional[str]
    mime_type:     str
    size_bytes:    Optional[int]
    metadata:      Dict[str, Any] = field(default_factory=dict)
    version:       int = 1
    created_at:    str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─────────────────────────────────────────────────────────────────────────────
# ArtifactBuilder
# ─────────────────────────────────────────────────────────────────────────────

class ArtifactBuilder:
    """Build and persist artifacts of any type."""

    # ── Core build ────────────────────────────────────────────────────────────

    async def build(
        self,
        *,
        artifact_type: str,
        title: str,
        content: Any,          # str | bytes | dict
        user_id: str,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
        render_pdf: bool = False,
        render_slides: bool = False,
    ) -> ArtifactRecord:
        """Build an artifact, store it, and persist the DB row."""
        artifact_id = str(uuid.uuid4())
        content_bytes, mime_type = self._to_bytes(content, artifact_type)

        storage_path = self._store(artifact_id, content_bytes, artifact_type)
        download_url = f"/api/artifacts/{artifact_id}/download"

        record = ArtifactRecord(
            id=artifact_id,
            thread_id=thread_id,
            run_id=run_id,
            user_id=user_id,
            artifact_type=artifact_type,
            title=title,
            storage_path=storage_path,
            download_url=download_url,
            mime_type=mime_type,
            size_bytes=len(content_bytes),
            metadata=metadata or {},
        )

        # Optionally render PDF or slides
        if render_pdf:
            try:
                from backend.services.pdf_renderer import pdf_renderer
                pdf_path = await pdf_renderer.render(
                    content=content if isinstance(content, str) else json.dumps(content, indent=2),
                    title=title,
                    output_path=storage_path.replace(".json", ".pdf").replace(".txt", ".pdf"),
                )
                record.storage_path = pdf_path
                record.mime_type = "application/pdf"
                record.download_url = f"/api/artifacts/{artifact_id}/download"
            except Exception as exc:
                logger.warning("[ArtifactBuilder] pdf render failed: %s", exc)

        if render_slides:
            try:
                from backend.services.slides_renderer import slides_renderer
                slides_path = await slides_renderer.render(
                    content=content,
                    title=title,
                    output_path=storage_path.replace(".json", ".pptx").replace(".txt", ".pptx"),
                )
                record.storage_path = slides_path
                record.mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            except Exception as exc:
                logger.warning("[ArtifactBuilder] slides render failed: %s", exc)

        if db is not None:
            await self._persist(record, db)

        return record

    # ── Convenience builders ──────────────────────────────────────────────────

    async def build_migration_report(
        self, *, migration_plan: Dict[str, Any], user_id: str,
        thread_id: Optional[str] = None, db: Optional[Any] = None,
    ) -> ArtifactRecord:
        summary = migration_plan.get("summary", "Migration plan")
        content = self._format_migration_report(migration_plan)
        return await self.build(
            artifact_type="migration_report",
            title=f"Migration Report — {summary[:80]}",
            content=content,
            user_id=user_id,
            thread_id=thread_id,
            metadata={"strategy": migration_plan.get("strategy", "unknown")},
            db=db,
        )

    async def build_codebase_audit(
        self, *, audit_rows: List[Dict[str, Any]], user_id: str,
        thread_id: Optional[str] = None, db: Optional[Any] = None,
    ) -> ArtifactRecord:
        content = self._format_audit_table(audit_rows)
        return await self.build(
            artifact_type="codebase_audit",
            title="Capability Audit",
            content=content,
            user_id=user_id,
            thread_id=thread_id,
            metadata={"row_count": len(audit_rows)},
            db=db,
        )

    async def build_screenshot_pack(
        self, *, screenshot_urls: List[str], user_id: str,
        thread_id: Optional[str] = None, db: Optional[Any] = None,
    ) -> ArtifactRecord:
        content = json.dumps({"screenshots": screenshot_urls}, indent=2)
        return await self.build(
            artifact_type="screenshot_pack",
            title=f"Screenshot Pack ({len(screenshot_urls)} images)",
            content=content,
            user_id=user_id,
            thread_id=thread_id,
            metadata={"count": len(screenshot_urls)},
            db=db,
        )

    async def build_proof_bundle(
        self, *, proof_data: Dict[str, Any], user_id: str,
        thread_id: Optional[str] = None, db: Optional[Any] = None,
    ) -> ArtifactRecord:
        content = json.dumps(proof_data, indent=2)
        return await self.build(
            artifact_type="proof_bundle",
            title="Proof Bundle",
            content=content,
            user_id=user_id,
            thread_id=thread_id,
            db=db,
        )

    # ── Storage helpers ───────────────────────────────────────────────────────

    def _to_bytes(self, content: Any, artifact_type: str) -> tuple[bytes, str]:
        if isinstance(content, bytes):
            return content, "application/octet-stream"
        if isinstance(content, dict) or isinstance(content, list):
            return json.dumps(content, indent=2).encode(), "application/json"
        text = str(content)
        if artifact_type in ("pdf",):
            return text.encode(), "application/pdf"
        return text.encode(), "text/plain"

    def _store(self, artifact_id: str, content: bytes, artifact_type: str) -> str:
        ext_map = {
            "pdf": "pdf", "presentation": "pptx", "image": "png",
        }
        ext = ext_map.get(artifact_type, "txt")
        os.makedirs(ARTIFACT_STORAGE_DIR, exist_ok=True)
        path = os.path.join(ARTIFACT_STORAGE_DIR, f"{artifact_id}.{ext}")
        try:
            with open(path, "wb") as f:
                f.write(content)
        except OSError as exc:
            logger.warning("[ArtifactBuilder] store failed: %s", exc)
            path = f"/tmp/{artifact_id}.{ext}"
        return path

    # ── DB persistence ────────────────────────────────────────────────────────

    async def _persist(self, record: ArtifactRecord, db: Any) -> None:
        try:
            await db.execute(
                """INSERT INTO artifacts
                   (id, thread_id, run_id, user_id, artifact_type, title,
                    storage_path, download_url, size_bytes, mime_type, metadata, version, created_at)
                   VALUES
                   (:id, :thread_id, :run_id, :user_id, :artifact_type, :title,
                    :storage_path, :download_url, :size_bytes, :mime_type, :metadata::jsonb, :version, :created_at)
                   ON CONFLICT (id) DO NOTHING""",
                {
                    "id": record.id,
                    "thread_id": record.thread_id,
                    "run_id": record.run_id,
                    "user_id": record.user_id,
                    "artifact_type": record.artifact_type,
                    "title": record.title,
                    "storage_path": record.storage_path,
                    "download_url": record.download_url,
                    "size_bytes": record.size_bytes,
                    "mime_type": record.mime_type,
                    "metadata": json.dumps(record.metadata),
                    "version": record.version,
                    "created_at": record.created_at,
                },
            )
            # Also write to artifact_versions
            version_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO artifact_versions (id, artifact_id, version, storage_path, download_url, size_bytes, created_at)
                   VALUES (:id, :artifact_id, :version, :storage_path, :download_url, :size_bytes, :created_at)
                   ON CONFLICT (id) DO NOTHING""",
                {
                    "id": version_id,
                    "artifact_id": record.id,
                    "version": record.version,
                    "storage_path": record.storage_path,
                    "download_url": record.download_url,
                    "size_bytes": record.size_bytes,
                    "created_at": record.created_at,
                },
            )
        except Exception as exc:
            logger.warning("[ArtifactBuilder] persist failed: %s", exc)

    # ── Formatters ────────────────────────────────────────────────────────────

    def _format_migration_report(self, plan: Dict[str, Any]) -> str:
        lines = [
            f"# Migration Report",
            f"**Strategy**: {plan.get('strategy', 'unknown')}",
            f"**Source**: {plan.get('source_root', '')}",
            f"**Target**: {plan.get('target_root', '')}",
            f"**Summary**: {plan.get('summary', '')}",
            "",
            "## File Actions",
        ]
        for fa in (plan.get("file_actions") or [])[:100]:
            if isinstance(fa, dict):
                lines.append(f"- `{fa.get('action', '?')}` {fa.get('source_path', '')} → {fa.get('target_path', '')}")
        lines += ["", "## Behavior Checklist"]
        for item in (plan.get("behavior_checklist") or []):
            lines.append(f"- [ ] {item}")
        return "\n".join(lines)

    def _format_audit_table(self, rows: List[Dict[str, Any]]) -> str:
        lines = [
            "# Capability Audit",
            "",
            "| Feature | Status | Files | Decision | Action |",
            "|---------|--------|-------|----------|--------|",
        ]
        for r in rows:
            files_str = ", ".join((r.get("files") or [])[:3])
            lines.append(
                f"| {r.get('feature','')} | {r.get('status','')} | {files_str} | "
                f"{r.get('decision','')} | {r.get('action','')} |"
            )
        return "\n".join(lines)


# Module-level singleton
artifact_builder = ArtifactBuilder()
