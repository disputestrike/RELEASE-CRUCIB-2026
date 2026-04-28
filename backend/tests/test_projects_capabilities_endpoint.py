"""GET /api/projects/settings/capabilities — extended flags + honest integration map."""

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


@pytest.mark.asyncio
async def test_capabilities_includes_connectors_and_mcp_shape():
    from httpx import ASGITransport, AsyncClient

    from backend.server import app

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
        timeout=30.0,
    ) as client:
        r = await client.get("/api/settings/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert data.get("llm") is True
    assert data.get("terminal") is True
    assert "connectors_configured" in data
    assert isinstance(data["connectors_configured"], dict)
    assert "mcp" in data
    assert data["mcp"].get("mode") == "in_process_adapters"
    assert "servers" in data["mcp"]
    assert isinstance(data["mcp"]["servers"], list)
