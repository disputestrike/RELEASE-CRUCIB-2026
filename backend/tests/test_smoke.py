import pytest


@pytest.mark.asyncio
async def test_health_smoke(app_client):
    r = await app_client.get("/api/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "status" in data


@pytest.mark.asyncio
async def test_ai_chat_route_smoke(app_client):
    r = await app_client.post(
        "/api/ai/chat",
        json={"message": "smoke test", "session_id": "smoke-session"},
        timeout=30,
    )
    # Route must exist and return a handled response (not 404/405).
    assert r.status_code in (200, 401, 402, 500, 503)
