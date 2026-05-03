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


@functools.lru_cache(maxsize=32)
def load_design_system_injection() -> str:
    """Return the design system injection prompt for frontend code generation agents."""
    p = PROMPTS_DIR / "design_system_injection.txt"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


@functools.lru_cache(maxsize=32)
def load_payment_default_injection() -> str:
    """Return the payment default injection prompt for any agent that may generate billing code.
    
    This enforces the PayPal-only rule: generated customer apps use PayPal for billing.
    Legacy Stripe or Braintree code should be rejected by build integrity checks.
    """
    p = PROMPTS_DIR / "payment_default_injection.txt"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def wrap_with_design_and_payment(system_prompt: str) -> str:
    """Wrap a frontend/fullstack agent system prompt with design system + payment rules.
    
    Use this for any agent that generates UI components, pages, or backend billing code.
    """
    design = load_design_system_injection()
    payment = load_payment_default_injection()
    parts = []
    if design:
        parts.append(f"## DESIGN SYSTEM REQUIREMENTS\n\n{design.strip()}")
    if payment:
        parts.append(f"## PAYMENT INTEGRATION REQUIREMENTS\n\n{payment.strip()}")
    if parts:
        injection = "\n\n---\n\n".join(parts)
        return f"{injection}\n\n---\n\n{system_prompt.strip()}"
    return system_prompt
