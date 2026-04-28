from __future__ import annotations

from backend import server
from services.runtime.task_manager import task_manager
from services.runtime.memory_graph import add_node
from services.runtime.cost_tracker import cost_tracker


async def test_debug_routes_require_admin(app_client, auth_headers, monkeypatch):
    monkeypatch.setattr(server, "_is_admin_user", lambda _user: False)
    r = await app_client.get("/api/debug/routes", headers=auth_headers)
    assert r.status_code == 403


async def test_debug_routes_allow_admin(app_client, auth_headers, monkeypatch):
    monkeypatch.setattr(server, "_is_admin_user", lambda _user: True)
    r = await app_client.get("/api/debug/routes", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "registered" in body
    assert "loaded_count" in body


async def test_debug_session_journal_endpoint_authz(app_client, auth_headers, monkeypatch):
    monkeypatch.setattr(server, "_is_admin_user", lambda _user: False)
    denied = await app_client.get("/api/debug/session-journal/test-project", headers=auth_headers)
    assert denied.status_code == 403

    monkeypatch.setattr(server, "_is_admin_user", lambda _user: True)
    allowed = await app_client.get("/api/debug/session-journal/test-project", headers=auth_headers)
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload["project_id"] == "test-project"
    assert "entries" in payload


async def test_debug_runtime_state_endpoint_authz(app_client, auth_headers, monkeypatch):
    monkeypatch.setattr(server, "_is_admin_user", lambda _user: False)
    denied = await app_client.get("/api/debug/runtime-state/test-project", headers=auth_headers)
    assert denied.status_code == 403


async def test_debug_runtime_state_endpoint_payload(app_client, auth_headers, monkeypatch):
    monkeypatch.setattr(server, "_is_admin_user", lambda _user: True)

    project_id = "test-project-runtime-state"
    task = task_manager.create_task(project_id=project_id, description="state test", metadata={"user_id": "u1"})
    tid = task["task_id"]
    add_node(project_id, task_id=tid, node_type="step_result", payload={"ok": True})
    cost_tracker.record(tid, tokens=25, credits=0.01)

    allowed = await app_client.get(f"/api/debug/runtime-state/{project_id}", headers=auth_headers)
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload["project_id"] == project_id
    assert payload["task_count"] >= 1
    assert tid in payload["cost_ledger"]
    assert payload["memory_graph"]["node_count"] >= 1
    assert "inspect" in payload
    assert "timeline" in payload["inspect"]
    assert "phase_summary" in payload["inspect"]


async def test_debug_runtime_what_if_endpoint(app_client, auth_headers, monkeypatch):
    monkeypatch.setattr(server, "_is_admin_user", lambda _user: True)

    project_id = "test-project-what-if"
    body = {
        "scenario": "What if we migrate the billing provider and keep canary rollback?",
        "population_size": 12,
        "rounds": 2,
    }

    response = await app_client.post(
        f"/api/debug/runtime-state/{project_id}/what-if",
        headers=auth_headers,
        json=body,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["project_id"] == project_id
    assert "recommendation" in payload
    assert "updates" in payload
