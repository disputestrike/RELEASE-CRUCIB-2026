import pytest

from orchestration.generation_policy import (
    fixed_planner_skip_auth,
    fixed_planner_skip_database,
    goal_suggests_database,
)


@pytest.mark.parametrize(
    "build_kind,integrations,expect_skip",
    [
        ("frontend", [], True),
        ("fullstack", [], True),
        ("fullstack", ["database"], False),
    ],
)
def test_fixed_planner_skip_database(build_kind, integrations, expect_skip):
    assert fixed_planner_skip_database(build_kind, integrations) is expect_skip


def test_goal_suggests_database_adds_signal():
    assert goal_suggests_database("Use PostgreSQL with Prisma for users")
    assert not goal_suggests_database("Paint the landing page blue")


def test_fixed_planner_skip_auth():
    assert fixed_planner_skip_auth([]) is True
    assert fixed_planner_skip_auth(["auth"]) is False
