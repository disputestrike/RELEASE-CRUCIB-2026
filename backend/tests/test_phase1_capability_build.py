"""
tests/test_phase1_capability_build.py
──────────────────────────────────────
Tests for all Phase-1 A-Q capability services.

Branch: engineering/master-list-closeout
Covers:
  - agent_loop.py  (E)
  - memory_store.py  (J)
  - capability_inspector.py  (B / P)
  - migration_engine.py  (C / G)
  - connector_manager.py  (F)
  - image_generation.py  (K)
  - artifact_builder.py  (L)
  - pdf_renderer.py  (L)
  - slides_renderer.py  (L)
  - preview_session.py  (H)
  - operator_runner.py  (H)
  - ui_feedback_mapper.py  (H)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── sys.path setup ────────────────────────────────────────────────────────────
# Add backend root so imports resolve without PYTHONPATH tweaks
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ═══════════════════════════════════════════════════════════════════════════════
# E. agent_loop.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionMode:
    def test_all_eight_modes_defined(self):
        from services.agent_loop import ExecutionMode
        modes = {m.value for m in ExecutionMode}
        assert "analyze_only"   in modes
        assert "plan_first"     in modes
        assert "short_pass"     in modes
        assert "one_pass"       in modes
        assert "phased"         in modes
        assert "migration"      in modes
        assert "build"          in modes
        assert "repair"         in modes
        assert len(modes) == 8

    def test_mode_phase_map_covers_all(self):
        from services.agent_loop import ExecutionMode, MODE_PHASE_MAP
        for mode in ExecutionMode:
            assert mode in MODE_PHASE_MAP, f"Mode {mode} missing from MODE_PHASE_MAP"
            assert len(MODE_PHASE_MAP[mode]) > 0, f"Mode {mode} has empty phase list"

    def test_analyze_only_is_read_only(self):
        from services.agent_loop import ExecutionMode, MODE_PHASE_MAP
        phases = MODE_PHASE_MAP[ExecutionMode.ANALYZE_ONLY]
        assert "execute" not in phases
        assert "inspect" in phases

    def test_migration_mode_has_migrate_phase(self):
        from services.agent_loop import ExecutionMode, MODE_PHASE_MAP
        phases = MODE_PHASE_MAP[ExecutionMode.MIGRATION]
        assert "migrate" in phases


class TestAgentLoopFacade:
    def test_singleton_exists(self):
        from services.agent_loop import agent_loop, AgentLoop
        assert isinstance(agent_loop, AgentLoop)

    def test_run_returns_dict_on_engine_failure(self):
        from services.agent_loop import agent_loop, ExecutionMode
        # Patch engine to raise
        with patch.object(agent_loop, "_get_engine") as mock_engine:
            engine = MagicMock()
            engine.execute_with_control = AsyncMock(side_effect=RuntimeError("boom"))
            mock_engine.return_value = engine
            result = asyncio.get_event_loop().run_until_complete(
                agent_loop.run(mode=ExecutionMode.BUILD, goal="test", user_id="tester")
            )
        assert result["status"] == "failed"
        assert "run_id" in result
        assert "error" in result

    def test_run_unknown_mode_defaults_to_build(self):
        from services.agent_loop import agent_loop
        with patch.object(agent_loop, "_get_engine") as mock_engine:
            engine = MagicMock()
            engine.execute_with_control = AsyncMock(return_value={"ok": True})
            mock_engine.return_value = engine
            result = asyncio.get_event_loop().run_until_complete(
                agent_loop.run(mode="unknown_xyz", goal="test")
            )
        assert result["mode"] == "build"

    def test_cancel_returns_bool(self):
        from services.agent_loop import agent_loop
        result = asyncio.get_event_loop().run_until_complete(agent_loop.cancel("nonexistent-run"))
        assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# J. memory_store.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryScope:
    def test_four_scopes_defined(self):
        from services.memory_store import MemoryScope
        scopes = {s.value for s in MemoryScope}
        assert scopes == {"user", "project", "workflow", "migration"}

    def test_convention_keys_not_empty(self):
        from services.memory_store import CONVENTION_KEYS
        assert len(CONVENTION_KEYS) >= 5


class TestMemoryStore:
    def _make_mock_db(self):
        db = MagicMock()
        db.execute   = AsyncMock(return_value=None)
        db.fetch_one = AsyncMock(return_value={"value": "stored_value"})
        db.fetch_all = AsyncMock(return_value=[
            {"user_id": "u1", "scope": "user", "key": "coding_conventions", "value": "PEP8"}
        ])
        return db

    def test_singleton_exists(self):
        from services.memory_store import memory_store, MemoryStore
        assert isinstance(memory_store, MemoryStore)

    def test_set_calls_db_execute(self):
        from services.memory_store import memory_store, MemoryScope
        db = self._make_mock_db()
        asyncio.get_event_loop().run_until_complete(
            memory_store.set(user_id="u1", scope=MemoryScope.USER, key="test_key", value="test_val", db=db)
        )
        db.execute.assert_called_once()

    def test_get_returns_value(self):
        from services.memory_store import memory_store, MemoryScope
        db = self._make_mock_db()
        val = asyncio.get_event_loop().run_until_complete(
            memory_store.get(user_id="u1", scope=MemoryScope.USER, key="test_key", db=db)
        )
        assert val == "stored_value"

    def test_get_conventions_returns_dict(self):
        from services.memory_store import memory_store
        db = self._make_mock_db()
        result = asyncio.get_event_loop().run_until_complete(
            memory_store.get_conventions(user_id="u1", db=db)
        )
        assert isinstance(result, dict)

    def test_delete_calls_db_execute(self):
        from services.memory_store import memory_store, MemoryScope
        db = self._make_mock_db()
        asyncio.get_event_loop().run_until_complete(
            memory_store.delete(user_id="u1", scope=MemoryScope.PROJECT, key="k", db=db)
        )
        db.execute.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# B/P. capability_inspector.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestCapabilityInspector:
    def test_singleton_exists(self):
        from services.capability_inspector import capability_inspector, CapabilityInspector
        assert isinstance(capability_inspector, CapabilityInspector)

    def test_audit_status_values(self):
        from services.capability_inspector import AuditStatus
        statuses = {s.value for s in AuditStatus}
        assert "exists"     in statuses
        assert "partial"    in statuses
        assert "missing"    in statuses
        assert "wiring"     in statuses
        assert "refactor"   in statuses
        assert "deprecated" in statuses

    def test_feature_audit_row_has_required_fields(self):
        from services.capability_inspector import FeatureAuditRow, AuditStatus
        row = FeatureAuditRow(feature="test", status=AuditStatus.EXISTS, files=[], gaps=[])
        assert row.feature == "test"
        assert row.status  == AuditStatus.EXISTS
        assert isinstance(row.files, list)

    def test_inspect_feature_returns_row(self):
        from services.capability_inspector import capability_inspector
        row = asyncio.get_event_loop().run_until_complete(
            capability_inspector.inspect_feature("agent_loop")
        )
        assert hasattr(row, "status")
        assert hasattr(row, "feature")

    def test_inspect_unknown_returns_row(self):
        from services.capability_inspector import capability_inspector
        row = asyncio.get_event_loop().run_until_complete(
            capability_inspector.inspect_feature("xyz_nonexistent_feature_12345")
        )
        assert row.feature == "xyz_nonexistent_feature_12345"

    def test_inspect_all_covers_all_registered_features(self):
        from services.capability_inspector import capability_inspector
        rows = asyncio.get_event_loop().run_until_complete(capability_inspector.inspect_all())
        assert len(rows) == len(capability_inspector.FEATURE_REGISTRY)


# ═══════════════════════════════════════════════════════════════════════════════
# C/G. migration_engine.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrationEngine:
    def test_singleton_exists(self):
        from services.migration_engine import migration_engine, MigrationEngine
        assert isinstance(migration_engine, MigrationEngine)

    def test_plan_returns_migration_plan(self):
        from services.migration_engine import migration_engine
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            # Create some test files
            Path(src, "service_a.py").write_text("def a(): pass\n")
            Path(src, "service_b.py").write_text("def b(): pass\n")
            plan = migration_engine.plan(source_root=src, target_root=tgt)
            assert plan.source_root == src
            assert plan.target_root == tgt
            assert isinstance(plan.file_actions, list)
            assert isinstance(plan.behavior_checklist, list)
            assert len(plan.behavior_checklist) > 0

    def test_plan_merge_strategy(self):
        from services.migration_engine import migration_engine
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            Path(src, "utils_a.py").write_text("x = 1\n")
            Path(src, "utils_b.py").write_text("y = 2\n")
            plan = migration_engine.plan(source_root=src, target_root=tgt, strategy="merge_many_to_fewer")
            assert plan.strategy == "merge_many_to_fewer"

    def test_execute_plan_dry_run_does_not_write(self):
        from services.migration_engine import migration_engine
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            src_file = Path(src, "foo.py")
            src_file.write_text("x = 1\n")
            plan = migration_engine.plan(source_root=src, target_root=tgt)
            result = migration_engine.execute_plan(plan, dry_run=True)
            assert result.status == "planned"
            # No files written in dry run
            tgt_files = list(Path(tgt).rglob("*"))
            assert len(tgt_files) == 0

    def test_file_action_fields(self):
        from services.migration_engine import FileAction
        fa = FileAction(source_path="/a", target_path="/b", action="copy", notes="test")
        assert fa.source_path == "/a"
        assert fa.action      == "copy"


# ═══════════════════════════════════════════════════════════════════════════════
# F. connector_manager.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorManager:
    def test_singleton_exists(self):
        from services.connector_manager import connector_manager, ConnectorManager
        assert isinstance(connector_manager, ConnectorManager)

    def test_all_connectors_registered(self):
        from services.connector_manager import connector_manager
        status = connector_manager.status()
        assert "github"   in status
        assert "railway"  in status
        assert "vercel"   in status
        assert "slack"    in status
        assert "paypal"   in status

    def test_get_returns_none_for_unknown(self):
        from services.connector_manager import connector_manager
        assert connector_manager.get("nonexistent_xyz") is None

    def test_is_available_false_without_env(self):
        from services.connector_manager import GitHubConnector
        connector = GitHubConnector.__new__(GitHubConnector)
        connector._token = ""
        assert connector.is_available() is False

    def test_list_available_is_subset_of_all(self):
        from services.connector_manager import connector_manager
        available = connector_manager.list_available()
        all_names = list(connector_manager.status().keys())
        for a in available:
            assert a in all_names


# ═══════════════════════════════════════════════════════════════════════════════
# K. image_generation.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageGenerationService:
    def test_singleton_exists(self):
        from services.image_generation import image_generation, ImageGenerationService
        assert isinstance(image_generation, ImageGenerationService)

    def test_generate_returns_image_result(self):
        from services.image_generation import image_generation
        with patch("services.image_generation._generate_together", new=AsyncMock(return_value="https://img.example.com/1.png")):
            result = asyncio.get_event_loop().run_until_complete(
                image_generation.generate(prompt="test prompt")
            )
        assert result.url == "https://img.example.com/1.png"
        assert result.provider == "together"

    def test_generate_returns_error_on_all_providers_fail(self):
        from services.image_generation import image_generation
        with patch("services.image_generation._generate_together", new=AsyncMock(return_value=None)), \
             patch("services.image_generation._generate_openai",   new=AsyncMock(return_value=None)), \
             patch("services.image_generation._generate_stability",new=AsyncMock(return_value=None)):
            result = asyncio.get_event_loop().run_until_complete(
                image_generation.generate(prompt="test prompt")
            )
        assert result.url is None
        assert result.error is not None

    def test_generate_batch_returns_dict(self):
        from services.image_generation import image_generation
        with patch("services.image_generation._generate_together", new=AsyncMock(return_value="https://img.example.com/2.png")):
            results = asyncio.get_event_loop().run_until_complete(
                image_generation.generate_batch(prompts={"hero": "hero image", "feature": "feature"})
            )
        assert isinstance(results, dict)
        assert "hero" in results
        assert "feature" in results


# ═══════════════════════════════════════════════════════════════════════════════
# L. artifact_builder.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestArtifactBuilder:
    def _make_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    def test_singleton_exists(self):
        from services.artifact_builder import artifact_builder, ArtifactBuilder
        assert isinstance(artifact_builder, ArtifactBuilder)

    def test_build_returns_artifact_record(self):
        from services.artifact_builder import artifact_builder
        result = asyncio.get_event_loop().run_until_complete(
            artifact_builder.build(
                artifact_type="product_spec",
                title="Test Spec",
                content="# Test content",
                user_id="user1",
            )
        )
        assert result.id is not None
        assert result.artifact_type == "product_spec"
        assert result.title == "Test Spec"

    def test_build_writes_to_db(self):
        from services.artifact_builder import artifact_builder
        db = self._make_db()
        asyncio.get_event_loop().run_until_complete(
            artifact_builder.build(
                artifact_type="migration_report",
                title="Migration",
                content={"strategy": "merge"},
                user_id="user1",
                db=db,
            )
        )
        assert db.execute.call_count >= 2  # artifacts + artifact_versions

    def test_build_migration_report(self):
        from services.artifact_builder import artifact_builder
        plan = {
            "strategy": "merge_many_to_fewer",
            "source_root": "/src",
            "target_root": "/tgt",
            "summary": "test summary",
            "file_actions": [{"source_path": "/src/a.py", "target_path": "/tgt/a.py", "action": "copy"}],
            "behavior_checklist": ["All routes respond correctly"],
        }
        result = asyncio.get_event_loop().run_until_complete(
            artifact_builder.build_migration_report(migration_plan=plan, user_id="u1")
        )
        assert "migration_report" in result.artifact_type

    def test_format_audit_table(self):
        from services.artifact_builder import artifact_builder
        rows = [{"feature": "agent_loop", "status": "exists", "files": ["a.py"], "decision": "reuse", "action": "wire"}]
        table = artifact_builder._format_audit_table(rows)
        assert "agent_loop" in table
        assert "exists" in table


# ═══════════════════════════════════════════════════════════════════════════════
# L. pdf_renderer.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFRenderer:
    def test_singleton_exists(self):
        from services.pdf_renderer import pdf_renderer, PDFRenderer
        assert isinstance(pdf_renderer, PDFRenderer)

    def test_render_fallback_creates_txt(self):
        from services.pdf_renderer import pdf_renderer
        with tempfile.TemporaryDirectory() as d:
            output = os.path.join(d, "test.pdf")
            result = asyncio.get_event_loop().run_until_complete(
                pdf_renderer.render(content="# Title\n\nBody text.", title="Test", output_path=output)
            )
            assert os.path.exists(result)

    def test_to_html_includes_title(self):
        from services.pdf_renderer import pdf_renderer
        html = pdf_renderer._to_html("# Heading\n- bullet", "My Title")
        assert "My Title" in html
        assert "Heading" in html


# ═══════════════════════════════════════════════════════════════════════════════
# L. slides_renderer.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlidesRenderer:
    def test_singleton_exists(self):
        from services.slides_renderer import slides_renderer, SlidesRenderer
        assert isinstance(slides_renderer, SlidesRenderer)

    def test_render_html_creates_file(self):
        from services.slides_renderer import slides_renderer
        with tempfile.TemporaryDirectory() as d:
            output = os.path.join(d, "test.html")
            result = asyncio.get_event_loop().run_until_complete(
                slides_renderer.render(
                    content="# Slide 1\n- Point 1\n## Slide 2\n- Point A",
                    title="Test Presentation",
                    output_path=output,
                    format="html",
                )
            )
            assert os.path.exists(result)
            html = Path(result).read_text()
            assert "Slide 1" in html

    def test_parse_content_markdown(self):
        from services.slides_renderer import _parse_content
        slides = _parse_content("# Title\n- bullet 1\n- bullet 2\n## Slide 2\n- item")
        assert len(slides) >= 2
        assert slides[0]["title"] == "Title"
        assert "bullet 1" in slides[0]["bullets"]

    def test_parse_content_dict(self):
        from services.slides_renderer import _parse_content
        content = {"slides": [{"title": "A", "bullets": ["x", "y"]}, {"title": "B", "bullets": []}]}
        slides = _parse_content(content)
        assert len(slides) == 2
        assert slides[0]["title"] == "A"


# ═══════════════════════════════════════════════════════════════════════════════
# H. preview_session.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestPreviewSessionService:
    def test_singleton_exists(self):
        from services.preview_session import preview_session_service, PreviewSessionService
        assert isinstance(preview_session_service, PreviewSessionService)

    def test_open_creates_session(self):
        from services.preview_session import preview_session_service
        session = asyncio.get_event_loop().run_until_complete(
            preview_session_service.open(url="https://example.com", thread_id="t1")
        )
        assert session.url == "https://example.com"
        assert session.thread_id == "t1"
        assert session.status == "open"
        assert session.session_id is not None

    def test_get_returns_session(self):
        from services.preview_session import preview_session_service
        session = asyncio.get_event_loop().run_until_complete(
            preview_session_service.open(url="https://test.example.com")
        )
        retrieved = preview_session_service.get(session.session_id)
        assert retrieved is session

    def test_close_updates_status(self):
        from services.preview_session import preview_session_service
        session = asyncio.get_event_loop().run_until_complete(
            preview_session_service.open(url="https://close.example.com")
        )
        closed = asyncio.get_event_loop().run_until_complete(
            preview_session_service.close(session.session_id)
        )
        assert closed is True
        assert session.status == "closed"

    def test_add_comment_appends_to_session(self):
        from services.preview_session import preview_session_service
        session = asyncio.get_event_loop().run_until_complete(
            preview_session_service.open(url="https://comment.example.com")
        )
        comment_id = asyncio.get_event_loop().run_until_complete(
            preview_session_service.add_comment(
                session_id=session.session_id,
                comment="Button is misaligned",
                region={"x": 10, "y": 20, "width": 100, "height": 40},
            )
        )
        assert comment_id is not None
        assert len(session.comments) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# H. operator_runner.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestOperatorRunner:
    def test_singleton_exists(self):
        from services.operator_runner import operator_runner, OperatorRunner
        assert isinstance(operator_runner, OperatorRunner)

    def test_navigate_returns_dict(self):
        from services.operator_runner import operator_runner
        result = asyncio.get_event_loop().run_until_complete(
            operator_runner.navigate("https://example.com")
        )
        assert isinstance(result, dict)
        assert "status" in result

    def test_run_flow_dry_run_skips_all(self):
        from services.operator_runner import operator_runner
        steps = [
            {"action": "navigate", "url": "https://example.com"},
            {"action": "click", "selector": "#btn"},
        ]
        results = asyncio.get_event_loop().run_until_complete(
            operator_runner.run_flow(steps=steps, dry_run=True)
        )
        assert len(results) == 2
        assert all(r["status"] == "dry_run_skipped" for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# H. ui_feedback_mapper.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestUiFeedbackMapper:
    def test_singleton_exists(self):
        from services.ui_feedback_mapper import ui_feedback_mapper, UiFeedbackMapper
        assert isinstance(ui_feedback_mapper, UiFeedbackMapper)

    def test_diff_missing_urls_returns_inconclusive(self):
        from services.ui_feedback_mapper import ui_feedback_mapper
        report = asyncio.get_event_loop().run_until_complete(
            ui_feedback_mapper.diff(before_url=None, after_url=None)
        )
        assert report.verdict == "inconclusive"

    def test_diff_same_data_uri_returns_pass(self):
        """Same base64 image should produce a pass verdict (identical hash)."""
        from services.ui_feedback_mapper import ui_feedback_mapper
        import base64
        # 1x1 white PNG
        b64 = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x11\x00\x01\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82"
        ).decode()
        data_uri = f"data:image/png;base64,{b64}"
        report = asyncio.get_event_loop().run_until_complete(
            ui_feedback_mapper.diff(before_url=data_uri, after_url=data_uri)
        )
        assert report.verdict == "pass"
        assert report.score == 1.0

    def test_map_comments_to_tasks(self):
        from services.ui_feedback_mapper import ui_feedback_mapper
        comments = [
            {"id": "c1", "comment": "Button broken", "status": "open"},
            {"id": "c2", "comment": "Already done", "status": "task_created"},
        ]
        tasks = ui_feedback_mapper.map_comments_to_tasks(comments)
        assert len(tasks) == 1
        assert "Button broken" in tasks[0]["title"]


# ═══════════════════════════════════════════════════════════════════════════════
# Migration 012 SQL sanity check
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigration012SQL:
    def test_file_exists(self):
        migration = _BACKEND / "migrations" / "012_phase1_tables.sql"
        assert migration.exists(), "migrations/012_phase1_tables.sql missing"

    def test_contains_all_required_tables(self):
        migration = _BACKEND / "migrations" / "012_phase1_tables.sql"
        sql = migration.read_text()
        tables = [
            "thread_checkpoints", "agent_runs", "run_steps", "tool_calls",
            "screenshots", "memories", "automations", "automation_runs",
            "artifacts", "artifact_versions", "preview_comments",
            "migration_runs", "migration_file_maps", "source_to_target_mappings",
            "approvals",
        ]
        for table in tables:
            assert table in sql, f"Table {table} missing from migration 012"

    def test_idempotent_if_not_exists(self):
        migration = _BACKEND / "migrations" / "012_phase1_tables.sql"
        sql = migration.read_text()
        # Every CREATE TABLE should use IF NOT EXISTS
        import re
        creates = re.findall(r"CREATE TABLE\b", sql, re.IGNORECASE)
        if_not_exists = re.findall(r"CREATE TABLE IF NOT EXISTS\b", sql, re.IGNORECASE)
        assert len(creates) == len(if_not_exists), (
            "Some CREATE TABLE statements are missing IF NOT EXISTS — migration is not idempotent"
        )
