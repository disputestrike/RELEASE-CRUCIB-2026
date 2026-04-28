class TestCapabilityFoundationContracts:
    async def test_computer_use_contract_lists_all_declared_safe_actions(self, app_client):
        response = await app_client.get("/api/capabilities/computer-use/actions", timeout=10)

        assert response.status_code == 200
        data = response.json()
        actions = {item["action"] for item in data["actions"]}
        assert {"see", "click", "type", "wait", "screenshot", "navigate"}.issubset(actions)
        assert data["execution_status"] == "disabled"

    async def test_computer_use_queue_validates_and_persists_disabled_contract(self, app_client):
        response = await app_client.post(
            "/api/capabilities/computer-use/queue/validate",
            json={
                "actions": [
                    {"action": "see", "target": "preview"},
                    {"action": "click", "target": "preview", "selector": "#submit"},
                ]
            },
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_status"] == "disabled"
        assert data["can_execute_now"] is False
        assert data["queue_id"].startswith("cuq_")
        assert len(data["queue"]) == 2
        assert all(item["execution_status"] == "not_executed" for item in data["queue"])
        assert all(blocker["reason"] == "computer_use_execution_disabled" for blocker in data["blockers"])
        assert set(data["persisted"]) == {"computer_use_tasks", "computer_use_actions", "audit_log"}

    async def test_asset_request_validation_does_not_return_fake_artifact(self, app_client):
        response = await app_client.post(
            "/api/capabilities/assets/requests/validate",
            json={
                "prompt": "hero image for a logistics dashboard",
                "asset_type": "image",
                "provider": "together_ai",
                "metadata": {"job_id": "job_test"},
            },
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"].startswith("asset_req_")
        assert data["execution_status"] == "validated_not_executed"
        assert data["request"]["prompt"] == "hero image for a logistics dashboard"
        assert data["artifact"] is None
        assert "artifact_contract" in data
        assert set(data["persisted"]) == {"asset_generation_requests", "audit_log"}

    async def test_scheduled_task_validation_records_disabled_future_contract(self, app_client):
        response = await app_client.post(
            "/api/capabilities/scheduled-tasks/validate",
            json={
                "name": "Morning brief",
                "schedule": {
                    "type": "cron",
                    "cron_expression": "0 8 * * 1-5",
                    "timezone": "America/New_York",
                    "enabled": True,
                },
                "task": {"template": "chief_of_staff_morning_brief"},
            },
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"].startswith("sched_")
        assert data["execution_status"] == "validated_not_scheduled"
        assert data["worker_required"] is True
        assert data["requested_enabled"] is True
        assert data["enabled"] is False
        assert data["schedule"]["next_run_time"] is None
        assert "validation_endpoint_does_not_start_scheduler" in data["blockers"]
        assert set(data["persisted"]) == {"scheduled_tasks", "audit_log"}
