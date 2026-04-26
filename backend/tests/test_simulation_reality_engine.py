from __future__ import annotations


def _install_fake_auth():
    from backend import deps
    from backend.server import app

    async def _fake_user():
        return {"id": "sim-test-user", "email": "simulation@example.com"}

    app.dependency_overrides[deps.get_current_user] = _fake_user
    return app, deps.get_current_user


async def test_lakers_prompt_is_sports_forecast_not_business_decision(app_client):
    app, dep = _install_fake_auth()
    create = await app_client.post(
        "/api/simulations",
        json={"prompt": "LAKERS WIN NBA"},
        timeout=10,
    )
    assert create.status_code == 200
    simulation_id = create.json()["simulation"]["id"]

    run = await app_client.post(
        "/api/simulations/run",
        json={"simulation_id": simulation_id, "prompt": "LAKERS WIN NBA", "rounds": 5, "agent_count": 8},
        timeout=20,
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["success"] is True
    assert payload["classification"]["domain"] == "sports"
    assert payload["classification"]["scenario_type"] == "forecast"
    assert "sports championship forecast" in payload["classification"]["interpretation"]
    assert payload["outcomes"]
    assert payload["population_model"]["population_size"] >= 100
    assert payload["trust_score"]["components"]["data_completeness"] < 0.7
    rendered = str(payload).lower()
    assert "implementation plan" not in rendered
    assert "no verified live source" in rendered
    app.dependency_overrides.pop(dep, None)


async def test_simulation_run_is_replayable_with_events(app_client):
    app, dep = _install_fake_auth()
    create = await app_client.post(
        "/api/simulations",
        json={"prompt": "Should we raise prices by 30%?", "assumptions": ["Current churn is stable."]},
        timeout=10,
    )
    assert create.status_code == 200
    simulation_id = create.json()["simulation"]["id"]

    run = await app_client.post(
        f"/api/simulations/{simulation_id}/run",
        json={"depth": "deep"},
        timeout=20,
    )
    assert run.status_code == 200
    run_id = run.json()["run"]["id"]

    details = await app_client.get(
        f"/api/simulations/{simulation_id}/runs/{run_id}",
        timeout=10,
    )
    assert details.status_code == 200
    data = details.json()
    assert data["success"] is True
    assert data["agents"]
    assert data["belief_updates"]
    assert data["outcomes"]
    assert data["events"]
    assert data["run"]["depth"] == "deep"
    app.dependency_overrides.pop(dep, None)


async def test_runtime_what_if_compatibility_uses_reality_engine(app_client):
    app, dep = _install_fake_auth()
    response = await app_client.post(
        "/api/runtime/what-if",
        json={"scenario": "Will Brazil win the World Cup?", "population_size": 12, "rounds": 2},
        timeout=20,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["runtime_mode"] == "production"
    assert payload["classification"]["domain"] == "sports"
    assert payload["classification"]["scenario_type"] == "forecast"
    assert payload["engine"] == "Reality Engine V1"
    assert payload["population_model"]["method"] == "core_agents_plus_synthetic_population"
    app.dependency_overrides.pop(dep, None)


async def test_simulation_depth_hides_raw_ui_counts_but_backend_autoscales(app_client):
    app, dep = _install_fake_auth()
    create = await app_client.post(
        "/api/simulations",
        json={"prompt": "Should we migrate off AWS?"},
        timeout=10,
    )
    simulation_id = create.json()["simulation"]["id"]
    run = await app_client.post(
        "/api/simulations/run",
        json={"simulation_id": simulation_id, "depth": "maximum"},
        timeout=20,
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["run"]["depth"] == "maximum"
    assert payload["run"]["agent_count_requested"] == 16
    assert payload["run"]["rounds_requested"] == 8
    assert payload["population_model"]["population_size"] == 10000
    app.dependency_overrides.pop(dep, None)
