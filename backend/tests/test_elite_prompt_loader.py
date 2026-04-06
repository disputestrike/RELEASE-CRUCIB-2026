"""Elite execution prompt: repo path, env gate, fingerprint."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from orchestration.elite_prompt_loader import (
    elite_prompt_fingerprint,
    elite_prompt_path,
    load_elite_autonomous_prompt,
    write_elite_directive_to_workspace,
)


def test_elite_prompt_path_points_at_repo_config():
    p = elite_prompt_path()
    assert p.name == "ELITE_AUTONOMOUS_PROMPT.md"
    assert "config" in p.parts and "agent_prompts" in p.parts


def test_load_returns_content_when_file_present():
    assert elite_prompt_path().is_file(), "fixture file should exist in repo"
    prev = os.environ.pop("CRUCIBAI_ELITE_SYSTEM_PROMPT", None)
    try:
        text = load_elite_autonomous_prompt()
        assert text is not None
        assert "Elite autonomous agent" in text or "elite autonomous" in text.lower()
    finally:
        if prev is not None:
            os.environ["CRUCIBAI_ELITE_SYSTEM_PROMPT"] = prev


def test_load_respects_disable_env():
    os.environ["CRUCIBAI_ELITE_SYSTEM_PROMPT"] = "0"
    try:
        assert load_elite_autonomous_prompt() is None
    finally:
        os.environ.pop("CRUCIBAI_ELITE_SYSTEM_PROMPT", None)


def test_fingerprint_stable():
    a = elite_prompt_fingerprint("hello")
    b = elite_prompt_fingerprint("hello")
    assert a == b
    assert len(a) == 16


def test_write_elite_directive_to_workspace():
    with tempfile.TemporaryDirectory() as d:
        ok = write_elite_directive_to_workspace(d, "# Test elite\n\nbody")
        assert ok is True
        p = Path(d) / "proof" / "ELITE_EXECUTION_DIRECTIVE.md"
        assert p.is_file()
        text = p.read_text(encoding="utf-8")
        assert "Test elite" in text
        assert "SHA256 prefix" in text
