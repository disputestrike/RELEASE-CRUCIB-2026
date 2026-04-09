from orchestration.agent_selection_logic import explain_agent_selection


def test_expansion_agents_are_reachable_from_real_prompts():
    coverage = [
        (
            "Build a marketing site with animations, icon system, image optimization, and responsive polish",
            {
                "Animation & Transitions Agent",
                "Icon System Agent",
                "Image Optimization Agent",
            },
        ),
        (
            "Build enterprise API with environment configuration, CORS, security headers, input validation, and rate limiting",
            {
                "Environment Configuration Agent",
                "CORS & Security Headers Agent",
                "Input Validation Agent",
                "Rate Limiting Agent",
            },
        ),
        (
            "Build realtime collaboration editor with shared presence, websocket sync, architecture decision records, and performance benchmarking",
            {
                "Real-Time Collaboration Agent",
                "Architecture Decision Records Agent",
                "Performance Test Agent",
            },
        ),
        (
            "Build compliance platform with secret management, audit controls, and zero-trust security",
            {
                "Secret Management Agent",
            },
        ),
    ]

    for goal, expected_agents in coverage:
        explanation = explain_agent_selection(goal, {})
        selected = set(explanation["selected_agents"])
        missing = expected_agents - selected
        assert not missing, f"{goal!r} did not select {sorted(missing)}"
