from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.trust import create_trust_router
from backend.services.enterprise_readiness import build_enterprise_readiness


def test_enterprise_readiness_keeps_local_secret_visibility_as_observation(monkeypatch):
    for key in (
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_MODE",
        "WORKOS_API_KEY",
        "WORKOS_CLIENT_ID",
        "WORKOS_CLIENT_SECRET",
        "CRUCIB_PROOF_HMAC_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)

    payload = build_enterprise_readiness(Path(__file__).resolve().parents[1])
    items = {item["key"]: item for item in payload["readiness_items"]}

    assert payload["status"] == "ready"
    assert payload["blockers"] == []
    assert items["payments"]["status"] == "available"
    assert items["sso"]["status"] == "available"
    assert items["cost_controls"]["status"] == "available"
    assert payload["runtime_configuration"]["paypal_configured_in_current_runtime"] is False
    assert payload["principle"].startswith("Readiness")


def test_enterprise_readiness_route_returns_json(monkeypatch):
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "client-id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("PAYPAL_MODE", "sandbox")

    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    response = client.get("/api/trust/enterprise-readiness")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    items = {item["key"]: item for item in data["readiness_items"]}
    assert items["payments"]["status"] == "available"
    assert "/api/billing/config" in items["payments"]["routes"]
    assert data["runtime_configuration"]["paypal_configured_in_current_runtime"] is True


def test_trust_summary_includes_enterprise_readiness():
    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    response = client.get("/api/trust/summary")

    assert response.status_code == 200
    data = response.json()
    assert "enterprise" in data
    assert "enterprise_ready" in data["checks"]
