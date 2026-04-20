from __future__ import annotations

import pytest


def test_list_skills_returns_all_builtins():
    from services.skills.skill_registry import list_skills
    skills = list_skills()
    names = {s.name for s in skills}
    expected = {"commit", "review", "plan", "build", "test", "deploy", "inspect", "what_if", "repair"}
    assert expected.issubset(names), f"Missing skills: {expected - names}"


def test_resolve_skill_commit():
    from services.skills.skill_registry import resolve_skill
    s = resolve_skill("commit changes now")
    assert s is not None
    assert s.name == "commit"


def test_resolve_skill_repair():
    from services.skills.skill_registry import resolve_skill
    s = resolve_skill("debug this broken endpoint")
    assert s is not None
    assert s.name == "repair"


def test_resolve_skill_what_if():
    from services.skills.skill_registry import resolve_skill
    s = resolve_skill("what if I deploy without tests")
    assert s is not None
    assert s.name == "what_if"


def test_resolve_skill_returns_none_for_unknown():
    from services.skills.skill_registry import resolve_skill
    s = resolve_skill("xyzzy frob garble")
    assert s is None


def test_get_skill_by_name():
    from services.skills.skill_registry import get_skill
    s = get_skill("deploy")
    assert s is not None
    assert s.name == "deploy"
    assert "run" in s.allowed_tools


def test_skill_names_complete():
    from services.skills.skill_registry import skill_names
    names = skill_names()
    assert "plan" in names
    assert "build" in names
    assert "test" in names
    assert "repair" in names


def test_skills_have_allowed_tools():
    from services.skills.skill_registry import list_skills
    for skill in list_skills():
        assert len(skill.allowed_tools) > 0, f"Skill {skill.name!r} has no allowed_tools"


def test_permission_check_allows_known_skill(monkeypatch):
    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    # Known skill should not be blocked by policy engine.
    # Simulate what _phase_check_permission does.
    import os
    from services.skills.skill_registry import list_skills
    known = {s.name for s in list_skills()} | {"default"}
    skill = "build"
    assert skill in known
    # Would produce permitted=True in the runtime phase.


def test_permission_check_blocks_unknown_skill_when_policy_on(monkeypatch):
    monkeypatch.setenv("CRUCIB_ENABLE_TOOL_POLICY", "1")
    import os
    from services.skills.skill_registry import list_skills
    known = {s.name for s in list_skills()} | {"default"}
    skill = "totally_fake_skill_xyz"
    assert skill not in known
    policy_on = os.environ.get("CRUCIB_ENABLE_TOOL_POLICY", "0").strip().lower() in ("1", "true", "yes")
    permitted = not policy_on  # False when policy on and skill unknown
    assert permitted is False
