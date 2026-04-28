from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.trust import create_trust_router
from backend.services.enterprise_readiness import build_enterprise_readiness


def test_enterprise_readiness_reports_unconfigured_braintree_and_sso(monkeypatch):
    for key in (
        "BRAINTREE_MERCHANT_ID",
        "BRAINTREE_PUBLIC_KEY",
        "BRAINTREE_PRIVATE_KEY",
        "BRAINTREE_ENVIRONMENT",
        "WORKOS_API_KEY",
        "WORKOS_CLIENT_ID",
        "WORKOS_CLIENT_SECRET",
        "CRUCIB_PROOF_HMAC_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)

    payload = build_enterprise_readiness(Path(__file__).resolve().parents[1])
    items = {item["key"]: item for item in payload["readiness_items"]}

    assert payload["status"] == "partial"
    assert items["payments"]["status"] == "requires_config"
    assert items["payments"]["required_config"] == [
        "BRAINTREE_MERCHANT_ID",
        "BRAINTREE_PUBLIC_KEY",
        "BRAINTREE_PRIVATE_KEY",
        "BRAINTREE_ENVIRONMENT",
    ]
    assert items["sso"]["status"] == "requires_config"
    assert items["cost_controls"]["status"] in {"available", "foundation"}
    assert payload["principle"].startswith("No enterprise")


def test_enterprise_readiness_route_returns_json(monkeypatch):
    monkeypatch.setenv("BRAINTREE_MERCHANT_ID", "mid")
    monkeypatch.setenv("BRAINTREE_PUBLIC_KEY", "pub")
    monkeypatch.setenv("BRAINTREE_PRIVATE_KEY", "priv")
    monkeypatch.setenv("BRAINTREE_ENVIRONMENT", "sandbox")

    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    response = client.get("/api/trust/enterprise-readiness")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    items = {item["key"]: item for item in data["readiness_items"]}
    assert items["payments"]["status"] == "available"
    assert "/api/payments/braintree/status" in items["payments"]["routes"]


def test_trust_summary_includes_enterprise_readiness():
    app = FastAPI()
    app.include_router(create_trust_router(Path(__file__).resolve().parents[1]))
    client = TestClient(app)

    response = client.get("/api/trust/summary")

    assert response.status_code == 200
    data = response.json()
    assert "enterprise" in data
    assert "enterprise_ready" in data["checks"]
