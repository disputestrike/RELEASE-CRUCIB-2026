"""Elite execution authority: job context, model block, gate integration."""
from __future__ import annotations

import os
import tempfile

import pytest

from orchestration.elite_builder_gate import verify_elite_builder_workspace
from orchestration.elite_prompt_loader import write_elite_directive_to_workspace
from orchestration.execution_authority import (
    attach_elite_context_to_job,
    elite_context_for_model,
    elite_job_metadata,
    resolve_elite_execution_text,
)


def test_resolve_reads_workspace_file_first():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        with open(os.path.join(d, "proof", "ELITE_EXECUTION_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write("workspace elite body")
        text, src = resolve_elite_execution_text(d)
        assert src == "workspace_file"
        assert "workspace elite" in (text or "")


def test_attach_elite_populates_job_dict():
    with tempfile.TemporaryDirectory() as d:
        raw = "# x\nhello directive"
        write_elite_directive_to_workspace(d, raw)
        job: dict = {"id": "j1"}
        attach_elite_context_to_job(job, d)
        meta = elite_job_metadata(job)
        assert meta["elite_mode_active"] is True
        assert meta["elite_prompt_sha16"]
        block = elite_context_for_model(job)
        assert "sha16=" in block
        assert "hello directive" in block


def test_elite_disabled_env_no_text(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ELITE_SYSTEM_PROMPT", "0")
    with tempfile.TemporaryDirectory() as d:
        text, src = resolve_elite_execution_text(d)
        assert text is None
        assert src == "disabled"
    monkeypatch.delenv("CRUCIBAI_ELITE_SYSTEM_PROMPT", raising=False)


def test_attach_elite_inactive_injects_empty_model_block(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ELITE_SYSTEM_PROMPT", "0")
    with tempfile.TemporaryDirectory() as d:
        write_elite_directive_to_workspace(d, "should be ignored when disabled")
        job: dict = {"id": "j2"}
        attach_elite_context_to_job(job, d)
        assert elite_context_for_model(job) == ""
        assert elite_job_metadata(job)["elite_mode_active"] is False
    monkeypatch.delenv("CRUCIBAI_ELITE_SYSTEM_PROMPT", raising=False)


@pytest.mark.asyncio
async def test_tenancy_goal_gate_fails_when_classification_has_no_runtime_hints():
    """Presence of 'RLS' alone is insufficient for tenancy-tagged goals."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        with open(os.path.join(d, "proof", "ELITE_EXECUTION_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write("elite")
        with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
            f.write(
                "## Implemented\nRLS policies declared in migrations only.\n"
                "## Mocked\nn/a\n## Stubbed\nn/a\n## Unverified\nn/a\n"
            )
        os.environ["CRUCIBAI_ELITE_BUILDER_GATE"] = "strict"
        try:
            r = await verify_elite_builder_workspace(d, job_goal="multi-tenant Postgres RLS")
            assert r["passed"] is False
            assert any("Tenancy-related goal" in i for i in r["issues"])
        finally:
            os.environ.pop("CRUCIBAI_ELITE_BUILDER_GATE", None)


def test_continuation_blueprint_writes_under_workspace():
    from orchestration.continuation_blueprint import write_continuation_blueprint

    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        ok = write_continuation_blueprint(
            d,
            job_id="job-x",
            goal="ship auth",
            reason="verification_failed",
            failed_step_keys=["verification.elite_builder"],
            open_gates=["DELIVERY_CLASSIFICATION depth"],
        )
        assert ok is True
        p = os.path.join(d, "proof", "CONTINUATION_BLUEPRINT.md")
        assert os.path.isfile(p)
        body = open(p, encoding="utf-8").read()
        assert "verification.elite_builder" in body
        assert "ship auth" in body


@pytest.mark.asyncio
async def test_elite_builder_gate_passes_with_manifest_and_directive():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        with open(os.path.join(d, "proof", "ELITE_EXECUTION_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write("elite")
        with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
            f.write(
                "## Implemented\nx\n## Mocked\ny\n## Stubbed\nz\n## Unverified\nw\n"
                "tenancy pytest runtime isolation\n"
            )
        os.makedirs(os.path.join(d, "src"), exist_ok=True)
        with open(os.path.join(d, "src", "App.jsx"), "w", encoding="utf-8") as f:
            f.write(
                "import React from 'react';\n"
                "export class ErrorBoundary extends React.Component {}\n"
                "export const AuthContext = React.createContext(null);\n"
            )
        os.makedirs(os.path.join(d, "backend"), exist_ok=True)
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write(
                "from fastapi import FastAPI, Depends, HTTPException\n"
                "app = FastAPI()\n"
                "@app.get('/health')\n"
                "def health(user=Depends(get_current_user)):\n"
                "    try:\n"
                "        return {'ok': True}\n"
                "    except Exception:\n"
                "        raise HTTPException(status_code=500)\n"
                "SECURITY_HEADERS = ['Content-Security-Policy', 'X-Frame-Options', "
                "'X-Content-Type-Options', 'Strict-Transport-Security']\n"
            )
        os.environ["CRUCIBAI_ELITE_BUILDER_GATE"] = "strict"
        try:
            r = await verify_elite_builder_workspace(d, job_goal="multi-tenant RLS app")
            assert r["passed"] is True
        finally:
            os.environ.pop("CRUCIBAI_ELITE_BUILDER_GATE", None)


@pytest.mark.asyncio
async def test_elite_builder_gate_fails_missing_labels():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        with open(os.path.join(d, "proof", "ELITE_EXECUTION_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write("e")
        with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
            f.write("only implemented section\n## Implemented\n")
        os.environ["CRUCIBAI_ELITE_BUILDER_GATE"] = "strict"
        try:
            r = await verify_elite_builder_workspace(d, job_goal="hello")
            assert r["passed"] is False
            assert any("Mocked" in i or "Stubbed" in i for i in r["issues"])
        finally:
            os.environ.pop("CRUCIBAI_ELITE_BUILDER_GATE", None)


@pytest.mark.asyncio
async def test_elite_builder_gate_advisory_softens():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "proof"), exist_ok=True)
        with open(os.path.join(d, "proof", "ELITE_EXECUTION_DIRECTIVE.md"), "w", encoding="utf-8") as f:
            f.write("e")
        with open(os.path.join(d, "proof", "DELIVERY_CLASSIFICATION.md"), "w", encoding="utf-8") as f:
            f.write("bad")
        os.environ["CRUCIBAI_ELITE_BUILDER_GATE"] = "advisory"
        try:
            r = await verify_elite_builder_workspace(d, job_goal="x")
            assert r["passed"] is True
        finally:
            os.environ.pop("CRUCIBAI_ELITE_BUILDER_GATE", None)
