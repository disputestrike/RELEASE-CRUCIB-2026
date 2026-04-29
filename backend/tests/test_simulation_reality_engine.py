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
    assert payload["final_verdict"]["verdict"] in {"Yes", "No", "Unclear", "Insufficient Evidence"}
    assert payload["final_verdict"]["verdict"] == "Insufficient Evidence"
    assert payload["final_verdict"]["official_gate_failed"] is True
    assert payload["claims"]
    assert payload["population_model"]["population_size"] >= 100
    assert payload["trust_score"]["components"]["data_completeness"] < 0.7
    assert "unsupported_consensus_penalty" in payload["trust_score"]["components"]
    assert "evidence_policy" in payload["report"]["evidence_summary"]
    policy = payload["report"]["evidence_summary"]["evidence_policy"]
    assert policy["source_precedence"][0] == "official_api_fetcher"
    assert policy["terminal_states"] == ["Yes", "No", "Unclear", "Insufficient Evidence"]
    assert "next_best_action" in policy["output_contract"]
    assert payload["final_verdict"]["next_best_action"]
    rendered = str(payload).lower()
    assert "implementation plan" not in rendered
    oa = payload.get("output_answer") or {}
    assert oa.get("direct_answer") and len(str(oa["direct_answer"])) > 80
    assert oa.get("evidence_status")
    assert "tavily attempted" in str(oa.get("evidence_status", "")).lower()
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
    assert data["claims"]
    assert data["replay_events"]
    assert data["trust_snapshots"]
    assert data["population_models"]
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
    assert isinstance(payload.get("simulation_pulse"), list)
    assert len(payload["simulation_pulse"]) >= 1
    assert payload["final_verdict"]["contract"].startswith("Every run resolves")
    app.dependency_overrides.pop(dep, None)


async def test_flat_simulation_run_accepts_prompt_without_existing_id(app_client):
    app, dep = _install_fake_auth()
    run = await app_client.post(
        "/api/simulations/run",
        json={"prompt": "Will Brazil win the World Cup?", "depth": "fast"},
        timeout=20,
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["success"] is True
    assert payload["simulation"]["id"]
    assert payload["classification"]["domain"] == "sports"
    assert payload["classification"]["scenario_type"] == "forecast"
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
    assert sum(cluster["size"] for cluster in payload["population_model"]["clusters"]) == 10000
    app.dependency_overrides.pop(dep, None)


async def test_simulation_contract_covers_research_qa_scenarios(app_client):
    app, dep = _install_fake_auth()
    scenarios = [
        ("Will the Lakers win the NBA championship?", "sports", "forecast"),
        ("Will Brazil win the World Cup?", "sports", "forecast"),
        ("Should we raise prices by 30%?", "business", "decision"),
        ("Should we migrate off AWS?", "engineering", "decision"),
        ("Will customers hate this redesign?", "business", "market_reaction"),
    ]
    for prompt, domain, scenario_type in scenarios:
        create = await app_client.post("/api/simulations", json={"prompt": prompt}, timeout=10)
        assert create.status_code == 200
        simulation_id = create.json()["simulation"]["id"]
        run = await app_client.post(
            "/api/simulations/run",
            json={"simulation_id": simulation_id, "prompt": prompt, "depth": "fast", "use_live_evidence": False},
            timeout=20,
        )
        assert run.status_code == 200
        payload = run.json()
        assert payload["classification"]["domain"] == domain
        assert payload["classification"]["scenario_type"] == scenario_type
        assert payload["final_verdict"]["verdict"] in {"Yes", "No", "Unclear", "Insufficient Evidence"}
        assert payload["final_verdict"]["lower_bound"] <= payload["final_verdict"]["upper_bound"]
        assert payload["report"]["evidence_summary"]["claims_created"] == len(payload["claims"])
        assert payload["population_model"]["method"] == "core_agents_plus_synthetic_population"
        assert payload["trust_score"]["formula"] == "0.25Q + 0.15F + 0.15C + 0.15T + 0.10D + 0.10K + 0.10(1-P)"
        assert payload["report"]["replay_metadata"]["replay_scope"] == "core-agent transcript plus aggregated population cohorts"
        assert payload["report"]["evidence_summary"]["evidence_policy"]["output_contract"]
    app.dependency_overrides.pop(dep, None)


async def test_cancer_cure_prompt_routes_biomedical_research_discovery(app_client):
    app, dep = _install_fake_auth()
    create = await app_client.post(
        "/api/simulations",
        json={"prompt": "How do we cure cancer?"},
        timeout=10,
    )
    assert create.status_code == 200
    simulation_id = create.json()["simulation"]["id"]
    run = await app_client.post(
        "/api/simulations/run",
        json={
            "simulation_id": simulation_id,
            "prompt": "How do we cure cancer?",
            "depth": "fast",
            "use_live_evidence": False,
            "agent_count": 6,
            "rounds": 3,
        },
        timeout=20,
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["classification"]["domain"] == "biomedical"
    assert payload["classification"]["scenario_type"] == "research_discovery"
    assert payload["classification"]["output_style"] == "research_roadmap"
    roles = [a["role"] for a in payload["agents"]]
    assert any("Oncology" in r for r in roles)
    assert all("Scenario Analyst" not in r for r in roles)
    assert payload["recommendation"]["type"] == "research_roadmap"
    assert "State of science" in payload["outcomes"][0]["label"]
    app.dependency_overrides.pop(dep, None)


async def test_stock_short_horizon_recommendation_is_evidence_gated_scan(app_client):
    app, dep = _install_fake_auth()
    create = await app_client.post(
        "/api/simulations",
        json={"prompt": "What stock will go up the most next week?"},
        timeout=10,
    )
    assert create.status_code == 200
    simulation_id = create.json()["simulation"]["id"]
    run = await app_client.post(
        "/api/simulations/run",
        json={"simulation_id": simulation_id, "prompt": "What stock will go up the most next week?", "depth": "fast", "use_live_evidence": False},
        timeout=20,
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["classification"]["domain"] == "finance"
    assert payload["classification"]["scenario_type"] == "short_horizon_forecast"
    assert payload["recommendation"]["type"] == "evidence_gated_market_scan"
    app.dependency_overrides.pop(dep, None)


async def test_weekly_options_scan_routes_specialists_and_output_answer(app_client):
    app, dep = _install_fake_auth()
    create = await app_client.post(
        "/api/simulations",
        json={"prompt": "give me the best option trade for this week"},
        timeout=10,
    )
    assert create.status_code == 200
    simulation_id = create.json()["simulation"]["id"]
    run = await app_client.post(
        "/api/simulations/run",
        json={
            "simulation_id": simulation_id,
            "prompt": "give me the best option trade for this week",
            "depth": "fast",
            "use_live_evidence": False,
        },
        timeout=20,
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["classification"]["domain"] == "finance"
    roles = [a["role"] for a in payload["agents"]]
    assert any("Options" in r or "Volatility" in r for r in roles)
    oa = payload.get("output_answer") or {}
    assert oa.get("direct_answer")
    assert "not" in oa["direct_answer"].lower() and "advice" in oa["direct_answer"].lower()
    app.dependency_overrides.pop(dep, None)
