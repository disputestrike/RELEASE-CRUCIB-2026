"""Focused Phase 2 security hardening tests.

These tests are intentionally source-audit style where runtime websocket support is
awkward in the in-process async client. They backstop the generated proof artifacts.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_phase2_audit_module():
    path = REPO_ROOT / "scripts" / "phase2-security-audit.py"
    spec = importlib.util.spec_from_file_location("phase2_security_audit", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_phase2_optional_auth_route_inventory_has_no_unclassified_action_routes():
    """Every remaining optional-auth route must be explicitly classified safe."""
    audit = _load_phase2_audit_module()
    report = audit.build_report()
    assert report["passed"], report["failures"]
    assert report["optional_route_count"] > 0


def test_phase2_websocket_project_progress_requires_token_and_project_owner():
    """Project-progress websocket must reject unauthenticated and cross-tenant subscribers."""
    text = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    start = text.index("async def websocket_project_progress")
    end = text.index("# Add security and performance middleware", start)
    block = text[start:end]
    assert 'websocket.query_params.get("token")' in block
    assert "await websocket.close(code=1008)" in block
    assert "jwt.decode" in block
    assert '{"id": project_id, "user_id": user["id"]}' in block


def test_phase2_blueprint_optional_auth_only_allows_write_only_analytics():
    """Blueprint modules should not leave optional auth on tenant-readable resources."""
    text = (REPO_ROOT / "backend" / "modules_blueprint.py").read_text(encoding="utf-8")
    assert text.count("Depends(_resolve_optional_user)") == 1
    assert '@analytics_router.post("/analytics/event"' in text
