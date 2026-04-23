import pytest
import json
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_all_routes_load_dependencies():
    """Tests that all API routes can be loaded and their dependencies resolved without NameError or ImportError."""
    # This test primarily relies on the FastAPI app successfully starting up
    # and all routes being registered without immediate import/name errors.
    # If the app starts, it implies basic dependency resolution is working.
    # We can extend this by trying to hit each route with a dummy request.

    # A simple GET request to a known working endpoint (like health check) 
    # will confirm the app is running and basic routing works.
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    # Further, we can try to hit some key endpoints that have complex dependencies
    # to ensure they don't immediately fail due to NameError/ImportError.
    # For POST requests, we'll need to provide dummy data.

    # Test orchestrator/build (which previously failed)
    try:
        response = client.post(
            "/api/build", 
            json={
                "goal": "Build a simple static website", 
                "mode": "guided", 
                "build_target": "static_site"
            }
        )
        # Expecting 200 OK or 401 Unauthorized (if auth is required and not provided)
        # or 403 Forbidden (if credit balance is low)
        # or 400 Bad Request (if input is invalid)
        # The key is that it should NOT be a 500 NameError/ImportError
        assert response.status_code in [200, 401, 403, 400], f"Unexpected status code for /api/build: {response.status_code} - {response.text}"
        if response.status_code == 200:
            assert "plan" in response.json()

    except Exception as e:
        pytest.fail(f"/api/build failed with an unexpected exception: {e}")

    # Test orchestrator/estimate
    try:
        response = client.post(
            "/api/orchestrator/estimate", 
            json={
                "goal": "Build a simple static website", 
                "build_target": "static_site"
            }
        )
        assert response.status_code in [200, 401, 403, 400], f"Unexpected status code for /api/orchestrator/estimate: {response.status_code} - {response.text}"
        if response.status_code == 200:
            assert "estimated_tokens" in response.json()["estimate"]

    except Exception as e:
        pytest.fail(f"/api/orchestrator/estimate failed with an unexpected exception: {e}")

    # Test chat/react (to verify ReAct loop and Tavily integration)
    try:
        response = client.post(
            "/api/chat/react",
            json={
                "prompt": "Who is the current US president?",
                "project_id": "test_project_id"
            }
        )
        assert response.status_code in [200, 401, 403, 400], f"Unexpected status code for /api/chat/react: {response.status_code} - {response.text}"
        if response.status_code == 200:
            # For StreamingResponse, we need to read the stream and parse each event
            events = []
            for chunk in response.iter_bytes():
                lines = chunk.decode("utf-8").split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        try:
                            data_str = line[len("data: "):].strip()
                            if data_str:
                                event_data = json.loads(data_str)
                                events.append(event_data)
                        except json.JSONDecodeError:
                            pass
            assert len(events) > 0, "No SSE events received from /api/chat/react"
            # Check if at least one event contains a 'response' key
            assert any("response" in event for event in events), "No 'response' key found in SSE events"

    except Exception as e:
        pytest.fail(f"/api/chat/react failed with an unexpected exception: {e}")

    # Test get_agent_info
    try:
        response = client.get("/api/debug/agent-info")
        assert response.status_code in [200, 401, 403], f"Unexpected status code for /api/debug/agent-info: {response.status_code} - {response.text}"
        if response.status_code == 200:
            assert "total_agents_available" in response.json()
    except Exception as e:
        pytest.fail(f"/api/debug/agent-info failed with an unexpected exception: {e}")

    # Test list_build_targets
    try:
        response = client.get("/api/orchestrator/build-targets")
        assert response.status_code in [200, 401, 403], f"Unexpected status code for /api/orchestrator/build-targets: {response.status_code} - {response.text}"
        if response.status_code == 200:
            assert "targets" in response.json()
    except Exception as e:
        pytest.fail(f"/api/orchestrator/build-targets failed with an unexpected exception: {e}")

    # Test get_token_history (requires auth, expect 401 or 403 if not provided)
    try:
        response = client.get("/api/tokens/history")
        assert response.status_code in [401, 403], f"Unexpected status code for /api/tokens/history: {response.status_code} - {response.text}"
    except Exception as e:
        pytest.fail(f"/api/tokens/history failed with an unexpected exception: {e}")

    # Test get_referral_code (requires auth, expect 401 or 403 if not provided)
    try:
        response = client.get("/api/referrals/code")
        assert response.status_code in [401, 403], f"Unexpected status code for /api/referrals/code: {response.status_code} - {response.text}"
    except Exception as e:
        pytest.fail(f"/api/referrals/code failed with an unexpected exception: {e}")

    print("All critical routes tested for basic dependency resolution and response.")
