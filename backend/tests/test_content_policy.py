"""Content policy screening (Fifty-point #42)."""

import pytest
from content_policy import screen_user_content


@pytest.mark.golden
def test_screen_allows_by_default():
    assert screen_user_content("hello build a landing page") is None


@pytest.mark.golden
def test_screen_blocks_oversized_prompt(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_MAX_USER_PROMPT_CHARS", "10")
    assert screen_user_content("x" * 11) is not None


@pytest.mark.golden
def test_screen_strict_blocks_configured_substrings(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_CONTENT_POLICY_STRICT", "1")
    monkeypatch.setenv("CRUCIBAI_CONTENT_BLOCK_SUBSTRINGS", "blockedphrase,other")
    assert screen_user_content("prefix BLOCKEDPHRASE suffix") is not None
    assert screen_user_content("clean prompt") is None
