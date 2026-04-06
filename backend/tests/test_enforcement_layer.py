"""Elite enforcement layer: registry, gates, reports."""
from __future__ import annotations

import os
import tempfile

import pytest

from orchestration.enforcement.critical_registry import CRITICAL_FEATURES, matching_features
from orchestration.enforcement.enforcement_engine import (
    evaluate_enforcement,
    write_enforcement_artifacts,
)
from orchestration.enforcement.proof_hierarchy import RANK, strength_for_flat_item


def test_import_enforcement_package():
    from orchestration import enforcement  # noqa: F401

    assert enforcement.CRITICAL_REGISTRY_VERSION


def test_matching_features_empty_goal():
    assert matching_features("", [], {}) == []


def test_evaluate_enforcement_no_critical_scope_passes():
    with tempfile.TemporaryDirectory() as d:
        r = evaluate_enforcement(d, "hello static page", [], {})
        assert r["blocked"] is False
        assert r["advisory_would_block"] is False
        assert r["features_in_scope"] == []


def test_evaluate_enforcement_strict_blocks_auth_without_proof(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ENFORCEMENT_GATE", "strict")
    try:
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "proof"), exist_ok=True)
            with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
                f.write("## Implemented\nx\n## Mocked\ny\n## Stubbed\nz\n## Unverified\nw\n")
            r = evaluate_enforcement(d, "JWT auth login API", [], {})
            assert r["advisory_would_block"] is True
            assert r["blocked"] is True
            assert any("Authentication" in i or "auth" in i.lower() for i in r["issues"])
    finally:
        monkeypatch.delenv("CRUCIBAI_ENFORCEMENT_GATE", raising=False)


def test_evaluate_enforcement_advisory_does_not_block(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_ENFORCEMENT_GATE", raising=False)
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
            f.write("## Implemented\nx\n## Mocked\ny\n## Stubbed\nz\n## Unverified\nw\n")
        r = evaluate_enforcement(d, "JWT auth login API", [], {})
        assert r["advisory_would_block"] is True
        assert r["blocked"] is False


def test_presence_only_routes_fail_api_gate_strict(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ENFORCEMENT_GATE", "strict")
    try:
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "proof"), exist_ok=True)
            with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
                f.write("## Implemented\nx\n## Mocked\ny\n## Stubbed\nz\n## Unverified\nw\n")
            bundle = {"routes": [{"path": "/x"}], "files": [], "database": [], "verification": [], "deploy": [], "generic": []}
            flat = [
                {
                    "proof_type": "route",
                    "title": "route declared",
                    "payload": {"path": "/api", "verification_class": "presence"},
                }
            ]
            r = evaluate_enforcement(d, "FastAPI REST backend", flat, bundle)
            assert r["blocked"] is True
            assert any("health" in i.lower() or "core_api" in i.lower() for i in r["issues"])
    finally:
        monkeypatch.delenv("CRUCIBAI_ENFORCEMENT_GATE", raising=False)


def test_rbac_negative_proof_passes_auth_feature(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ENFORCEMENT_GATE", "strict")
    try:
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "proof"), exist_ok=True)
            with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
                f.write("## Implemented\nx\n## Mocked\ny\n## Stubbed\nz\n## Unverified\nw\n")
            flat = [
                {
                    "proof_type": "api",
                    "title": "rbac anonymous blocked",
                    "payload": {"check": "rbac_anonymous_blocked", "status": 403},
                }
            ]
            r = evaluate_enforcement(d, "JWT auth for users", flat, {})
            auth_pf = next((x for x in r["per_feature"] if x["id"] == "auth"), None)
            assert auth_pf is not None
            assert auth_pf["passed"] is True
            assert r["blocked"] is False
    finally:
        monkeypatch.delenv("CRUCIBAI_ENFORCEMENT_GATE", raising=False)


def test_skipped_rbac_signal_strict(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ENFORCEMENT_GATE", "strict")
    try:
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "proof"), exist_ok=True)
            with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
                f.write("## Implemented\nx\n## Mocked\ny\n## Stubbed\nz\n## Unverified\nw\n")
            flat = [{"proof_type": "generic", "title": "skip", "payload": {"check": "rbac_smoke_skipped"}}]
            r = evaluate_enforcement(d, "RBAC admin roles", flat, {})
            assert r["blocked"] is True
            assert any("skip" in i.lower() for i in r["issues"])
    finally:
        monkeypatch.delenv("CRUCIBAI_ENFORCEMENT_GATE", raising=False)


def test_write_enforcement_artifacts_creates_files():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        r = evaluate_enforcement(d, "trivial", [], {})
        write_enforcement_artifacts(d, r)
        assert os.path.isfile(os.path.join(d, "proof", "ENFORCEMENT_REPORT.md"))
        assert os.path.isfile(os.path.join(d, "proof", "ENFORCEMENT_REPORT.json"))


def test_strength_health_endpoint_is_runtime():
    item = {"proof_type": "api", "title": "health", "payload": {"check": "health_endpoint"}}
    name, rank = strength_for_flat_item(item)
    assert name == "runtime"
    assert rank == RANK["runtime"]


def test_registry_has_ten_classes():
    assert len(CRITICAL_FEATURES) == 10
