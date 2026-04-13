import pytest

from orchestration import brain_policy as bp


@pytest.fixture(autouse=True)
def _clear_policy_cache():
    bp.clear_brain_policy_cache()
    yield
    bp.clear_brain_policy_cache()


def test_load_brain_policy_has_version_and_directive():
    p = bp.load_brain_policy()
    assert p.get("version") == "1.0"
    assert "name" in p
    txt = bp.get_system_directive_text()
    assert "CrucibAI" in txt or "orchestration" in txt.lower()


def test_attach_brain_policy_to_plan_adds_metadata():
    plan = {"acceptance_criteria": ["existing"], "selected_agent_count": 5}
    bp.attach_brain_policy_to_plan(plan)
    assert plan.get("brain_policy", {}).get("version") == "1.0"
    crit = plan["acceptance_criteria"]
    assert "existing" in crit
    assert any("Orchestration brain" in c for c in crit)


def test_attach_warns_when_agent_count_exceeds_threshold():
    plan = {"acceptance_criteria": [], "selected_agent_count": 99}
    bp.attach_brain_policy_to_plan(plan)
    warns = plan.get("governor_warnings") or []
    assert any("exceeds brain_policy threshold" in w for w in warns)


def test_repair_route_for_syntax():
    assert bp.repair_route_for("syntax_error") == "syntax_fixer"


def test_job_started_policy_meta_keys():
    meta = bp.job_started_policy_meta()
    if meta:
        assert "brain_policy_version" in meta


def test_agent_selection_hard_cap_configured():
    from orchestration.brain_policy import agent_selection_hard_cap

    assert agent_selection_hard_cap() == 40
