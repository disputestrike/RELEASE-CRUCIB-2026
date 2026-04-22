"""Load versioned honesty-bias preambles and wrap system prompts with them.

Usage at an LLM call site:

    from backend.prompts import wrap_system
    system_prompt = wrap_system(task_specific_system_prompt)

Or, to skip the preamble deliberately:

    wrap_system(task_specific_system_prompt, preamble_name=None)
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent


@functools.lru_cache(maxsize=32)
def load_preamble(name: str = "honesty_bias.v1") -> str:
    """Return the preamble body for `name`, or '' if missing."""
    p = PROMPTS_DIR / f"{name}.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def wrap_system(
    system_prompt: str,
    preamble_name: Optional[str] = "honesty_bias.v1",
) -> str:
    """Prepend the named preamble to `system_prompt`.

    If `preamble_name` is None or the file is missing, returns
    `system_prompt` unchanged.
    """
    if not preamble_name:
        return system_prompt
    preamble = load_preamble(preamble_name)
    if not preamble:
        return system_prompt
    return f"{preamble.strip()}\n\n---\n\n{system_prompt.strip()}"


def list_available() -> list[dict]:
    """Enumerate available preambles in the prompts directory."""
    out = []
    for p in sorted(PROMPTS_DIR.glob("*.md")):
        name = p.stem
        body = p.read_text(encoding="utf-8")
        first_line = body.splitlines()[0] if body else ""
        out.append({
            "name": name,
            "title": first_line.lstrip("# ").strip() or name,
            "bytes": len(body),
        })
    return out
