"""Tests for new BIV gates added in biv-hardening-20260427.

Covers:
 - Content-type purity (Markdown-in-JSX detection)
 - Manifest-vs-disk reconciliation
 - Stripe-first payment enforcement
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from backend.orchestration.build_integrity_validator import (
    _check_content_type_purity,
    _check_manifest_vs_disk,
    _check_stripe_first,
)


# ── Content-type purity ───────────────────────────────────────────────────────

def test_content_type_pure_jsx_passes():
    files = {"src/App.jsx": "import React from 'react';\nexport default function App() { return <div/>; }"}
    assert _check_content_type_purity(files) == []


def test_content_type_markdown_in_jsx_fails():
    files = {"src/App.jsx": "#### `server/tsconfig.json` ✓\n\nSome markdown content"}
    result = _check_content_type_purity(files)
    assert len(result) == 1
    assert "src/App.jsx" in result[0]


def test_content_type_agent_prose_in_jsx_fails():
    files = {"src/charts/Dashboard.jsx": "# DATA VISUALIZATION DASHBOARD — PLOTLY + D3.JS\nI am the Data Visualization Agent."}
    result = _check_content_type_purity(files)
    assert len(result) == 1


def test_content_type_non_executable_md_ignored():
    files = {"docs/README.md": "#### Some heading\n\nSome content"}
    assert _check_content_type_purity(files) == []


def test_content_type_bold_prose_in_tsx_fails():
    files = {"src/components/Nav.tsx": "**This component handles navigation**\n\nSome description"}
    result = _check_content_type_purity(files)
    assert len(result) == 1


# ── Manifest-vs-disk reconciliation ──────────────────────────────────────────

def test_manifest_clean_passes():
    with tempfile.TemporaryDirectory() as tmp:
        meta = Path(tmp) / "META"
        meta.mkdir()
        src = Path(tmp) / "src"
        src.mkdir()
        app = src / "App.jsx"
        app.write_text("import React from 'react';\nexport default function App() { return <div/>; }" * 50)
        manifest = {
            "files": [
                {"path": "src/App.jsx", "approx_bytes": 2500},
            ]
        }
        (meta / "merge_map.json").write_text(json.dumps(manifest))
        files = {"src/App.jsx": app.read_text()}
        assert _check_manifest_vs_disk(tmp, files) == []


def test_manifest_missing_file_fails():
    with tempfile.TemporaryDirectory() as tmp:
        meta = Path(tmp) / "META"
        meta.mkdir()
        manifest = {"files": [{"path": "src/App.jsx", "approx_bytes": 10000}]}
        (meta / "merge_map.json").write_text(json.dumps(manifest))
        result = _check_manifest_vs_disk(tmp, {})
        assert any("MANIFEST_MISSING" in r for r in result)


def test_manifest_overwrite_suspected():
    with tempfile.TemporaryDirectory() as tmp:
        meta = Path(tmp) / "META"
        meta.mkdir()
        src = Path(tmp) / "src"
        src.mkdir()
        # Write a tiny file (31 bytes) where manifest claims 10503
        (src / "App.jsx").write_text("#### `server/tsconfig.json` OK\n", encoding="utf-8")  # tiny vs manifest
        manifest = {"files": [{"path": "src/App.jsx", "approx_bytes": 10503}]}
        (meta / "merge_map.json").write_text(json.dumps(manifest), encoding="utf-8")
        files = {"src/App.jsx": "#### `server/tsconfig.json` OK\n"}
        result = _check_manifest_vs_disk(tmp, files)
        assert any("MANIFEST_OVERWRITE_SUSPECTED" in r for r in result), f"Got: {result}"


def test_manifest_no_file_skips():
    with tempfile.TemporaryDirectory() as tmp:
        assert _check_manifest_vs_disk(tmp, {}) == []


# ── Stripe-first payment enforcement ─────────────────────────────────────────

def test_stripe_first_no_payment_passes():
    files = {"src/App.jsx": "import React from 'react';\nexport default function App() {}"}
    assert _check_stripe_first(files) == []


def test_stripe_first_braintree_in_generated_fails():
    files = {
        "src/billing/payment.py": "from braintree import BraintreeGateway\ngateway = BraintreeGateway(...)"
    }
    result = _check_stripe_first(files)
    assert len(result) == 1
    assert "STRIPE_FIRST_VIOLATION" in result[0]


def test_stripe_first_platform_braintree_allowed():
    """CrucibAI's own billing routes are exempt from the stripe-first check."""
    files = {
        "backend/routes/braintree_payments.py": "from braintree import BraintreeGateway",
        "backend/services/braintree_billing.py": "import braintree",
    }
    assert _check_stripe_first(files) == []


def test_stripe_first_user_requested_braintree_allowed():
    files = {
        "src/billing/payment.py": "from braintree import BraintreeGateway\ngateway = BraintreeGateway(...)"
    }
    result = _check_stripe_first(files, user_requested_braintree=True)
    assert result == []
