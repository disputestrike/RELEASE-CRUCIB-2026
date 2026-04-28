from __future__ import annotations

from backend.services.runtime.cost_tracker import cost_tracker
from backend.services.runtime.memory_graph import add_node
from backend.services.runtime.task_manager import task_manager


def _user_id_from_me_payload(payload: dict) -> str:
    if isinstance(payload, dict):
        if payload.get("id"):
            return str(payload["id"])
        user = payload.get("user")
        if isinstance(user, dict) and user.get("id"):
            return str(user["id"])
    return ""


async def test_runtime_inspect_requires_auth(app_client):
    response = await app_client.get("/api/runtime/inspect")
    assert response.status_code in (401, 403)


async def test_runtime_inspect_payload_for_authenticated_user(app_client, auth_headers):
    me = await app_client.get("/api/auth/me", headers=auth_headers)
    assert me.status_code == 200
    user_id = _user_id_from_me_payload(me.json())
    assert user_id

    project_id = f"runtime-{user_id}"
    task = task_manager.create_task(project_id=project_id, description="runtime inspect production")
    tid = task["task_id"]
    add_node(project_id, task_id=tid, node_type="step_result", payload={"ok": True})
    cost_tracker.record(tid, tokens=42, credits=0.02)

    response = await app_client.get("/api/runtime/inspect?limit=50", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["task_count"] >= 1
    assert tid in payload["cost_ledger"]
    assert payload["memory_graph"]["node_count"] >= 1
    assert "inspect" in payload
    assert "timeline" in payload["inspect"]


async def test_runtime_what_if_for_authenticated_user(app_client, auth_headers):
    response = await app_client.post(
        "/api/runtime/what-if",
        headers=auth_headers,
        json={
            "scenario": "What if we swap providers using canary and fallback?",
            "population_size": 16,
            "rounds": 3,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["runtime_mode"] == "production"
    assert "project_id" in payload
    assert "recommendation" in payload
    assert "updates" in payload


async def test_runtime_benchmark_run_and_latest_endpoints(app_client, auth_headers):
    run_response = await app_client.post(
        "/api/runtime/benchmark/run",
        headers=auth_headers,
        json={
            "execute_live": False,
            "max_runs": 3,
            "output_subdir": "pytest_bench_run",
        },
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["success"] is True
    assert run_payload["mode"] == "simulated"
    assert int(run_payload["total_runs"] or 0) == 3
    assert "aggregate" in run_payload

    latest_response = await app_client.get("/api/runtime/benchmark/latest", headers=auth_headers)
    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload["success"] is True
    assert latest_payload["latest"] is not None
    assert "aggregate" in latest_payload["latest"]
