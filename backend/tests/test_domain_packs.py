import os
import tempfile

import pytest
from orchestration.domain_packs import multitenant_intent, stripe_intent
from orchestration.planner import generate_plan
from orchestration.production_gate import scan_workspace_for_credential_patterns


def test_multitenant_intent():
    assert multitenant_intent("Multi-tenant SaaS with RLS")
    assert not multitenant_intent("simple todo list")


def test_stripe_intent():
    assert stripe_intent("Stripe billing and webhooks")
    assert not stripe_intent("no payments here")


def test_secret_scan_clean():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "app.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        assert scan_workspace_for_credential_patterns(d) == []


def test_secret_scan_detects_stripe_live():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "bad.py"), "w", encoding="utf-8") as f:
            # Build at runtime — do not embed sk_live_ + 20+ alnum in source (GitHub push protection).
            token = "sk_live_" + ("a" * 24)
            f.write(f'k = "{token}"\n')
        hits = scan_workspace_for_credential_patterns(d)
        assert hits and any("Stripe" in h for h in hits)


@pytest.mark.asyncio
async def test_planner_adds_compliance_acceptance_when_hipaa_goal():
    plan = await generate_plan(
        "HIPAA-compliant patient portal with Postgres",
        project_state={
            "env_vars": {"STRIPE_SECRET_KEY": "x", "ANTHROPIC_API_KEY": "y"},
        },
    )
    assert "compliance_sensitive" in (plan.get("required_integrations") or [])
    ac = plan.get("acceptance_criteria") or []
    assert any("COMPLIANCE_SKETCH" in c for c in ac)
