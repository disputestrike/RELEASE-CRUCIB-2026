from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.trust import create_trust_router
from backend.services.public_proof_readiness import build_public_proof_readiness


def test_public_proof_readiness_has_required_launch_items():
    payload = build_public_proof_readiness(Path(__file__).resolve().parents[1])
    items = {item["key"]: item for item in payload["proof_items"]}

    expected = {
        "public_benchmark_page",
        "fifty_apps_gallery",
        "reality_predictions_board",
        "side_by_side_comparison",
        "shareable_simulation_reports",
        "shareable_app_previews",
        "public_proof_bundles",
        "pricing_proof",
        "agency_founder_templates",
        "enterprise_defense_page",
    }

    assert expected.issubset(items)
    assert payload["status"] in {"ready", "partial"}
    assert payload["rule"].startswith("No public claim")
    assert "/api/cost/governance" in items["pricing_proof"]["routes"]
    assert "/api/trust/enterprise-readiness" in items["enterprise_defense_page"]["routes"]


def test_public_proof_readiness_route_returns_json():
    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    response = client.get("/api/trust/public-proof-readiness")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert "proof_items" in data
    assert any(item["key"] == "public_proof_bundles" for item in data["proof_items"])
