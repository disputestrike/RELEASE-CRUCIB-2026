"""Fixer retry cap (fifty-point #21)."""
import pytest

from orchestration.fixer import MAX_RETRIES


@pytest.mark.golden
def test_fixer_max_retries_is_bounded():
    assert isinstance(MAX_RETRIES, int)
    assert 1 <= MAX_RETRIES <= 10
