from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.orchestration.enterprise_proof import (
    REQUIRED_PROOF_FILES,
    analyze_api_alignment,
    generate_enterprise_proof_artifacts,
)


def test_api_alignment_detects_unwired_frontend_call(tmp_path):
    ws = tmp_path / "workspace"
    (ws / "src").mkdir(parents=True)
    (ws / "backend" / "routes").mkdir(parents=True)
    (ws / "src" / "billing.js").write_text(
        "export async function loadBilling(){ return fetch('/api/billing/overview'); }",
        encoding="utf-8",
    )
    (ws / "backend" / "routes" / "billing.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter(prefix='/api/billing')\n"
        "@router.post('/create-order')\n"
        "async def create_order():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )

    files = {
        "src/billing.js": (ws / "src" / "billing.js").read_text(encoding="utf-8"),
        "backend/routes/billing.py": (ws / "backend" / "routes" / "billing.py").read_text(encoding="utf-8"),
    }
    result = analyze_api_alignment(files)

    assert result["passed"] is False
    assert result["missing"][0]["path"] == "/api/billing/overview"


def test_enterprise_proof_blocks_strict_build_with_mocked_critical_paths(tmp_path):
    ws = tmp_path / "workspace"
    (ws / "src").mkdir(parents=True)
    (ws / "backend" / "routes").mkdir(parents=True)
    (ws / "package.json").write_text(
        json.dumps({"scripts": {"build": "vite"}, "dependencies": {"@vitejs/plugin-react": "latest"}}),
        encoding="utf-8",
    )
    (ws / "src" / "App.jsx").write_text(
        "export default function App(){ return <h1>Dashboard</h1>; }",
        encoding="utf-8",
    )
    (ws / "src" / "billing.js").write_text(
        "export const user = { name: 'demo user' };\n"
        "export async function loadBilling(){ return fetch('/api/billing/overview'); }\n",
        encoding="utf-8",
    )
    (ws / "backend" / "routes" / "billing.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter(prefix='/api/billing')\n"
        "@router.post('/create-order')\n"
        "async def create_order():\n"
        "    return {'mode': 'test'}\n",
        encoding="utf-8",
    )

    result = generate_enterprise_proof_artifacts(
        str(ws),
        {"id": "tsk_enterprise", "goal": "Build a SaaS MVP with authentication, PayPal billing, and user dashboard"},
        plan={"build_command": ["npm", "run", "build"]},
        assemble_result={"success": True},
        verify_result={"passed": True, "returncode": 0, "dist_exists": True},
    )

    gate = result["delivery_gate"]
    assert gate["status"] == "FAILED_DELIVERY_GATE"
    assert gate["blocks_completion"] is True
    assert "api_alignment" in gate["failed_checks"]
    assert "critical_paths_not_fully_implemented" in gate["failed_checks"]
    for rel in REQUIRED_PROOF_FILES:
        assert (ws / rel).exists(), rel
    for rel in (
        "docs/research_notes/DOMAIN_RESEARCH.md",
        "docs/requirements/REQUIREMENTS_FROM_RESEARCH.md",
        "docs/compliance/COMPLIANCE_NOTES.md",
        "docs/technical_spec/DOMAIN_TECHNICAL_SPEC.md",
        "docs/compliance/CONTROL_MATRIX.md",
        "docs/compliance/AUDIT_EVIDENCE_PLAN.md",
    ):
        assert (ws / rel).exists(), rel
    assert (ws / ".crucibai" / "delivery_gate.json").exists()


def test_enterprise_gate_blocks_zip_export_when_not_allowed(tmp_path):
    from backend.orchestration.delivery_gate import assert_workspace_download_allowed

    ws = tmp_path / "workspace"
    (ws / ".crucibai").mkdir(parents=True)
    (ws / ".crucibai" / "delivery_gate.json").write_text(
        json.dumps(
            {
                "status": "FAILED_DELIVERY_GATE",
                "allowed": False,
                "blocks_completion": True,
                "failed_checks": ["critical_paths_not_fully_implemented"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as err:
        assert_workspace_download_allowed(str(ws), {"status": "completed", "goal": "Build auth billing app"})

    assert err.value.status_code == 422
    assert err.value.detail["gate"] == "enterprise_delivery_gate"
