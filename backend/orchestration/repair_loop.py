"""
WS-C: Repair v2 — scratchpad + runtime feedback loop.

Iterates up to 5 rounds:
  1. attempt_fn(code, scratchpad) -> new_code
  2. verify_fn(new_code) -> {"ok": bool, "error": str | None, "evidence": dict | None}
  3. if ok: emit repair.final and return; else append to scratchpad and continue

Emits events via an optional async-friendly event callback:
  - repair.round.start {round, scratchpad_lines}
  - repair.round.end {round, ok, error}
  - repair.final {ok, rounds, final_code}

Feature-flag: honors env var FEATURE_REPAIR_V2=1 via `is_enabled()`.
No hard dependency — caller decides when to use it.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

AttemptFn = Callable[[str, List[str]], Awaitable[str]]
VerifyFn = Callable[[str], Awaitable[Dict[str, Any]]]
EmitFn = Callable[[str, Dict[str, Any]], Awaitable[None]]


def is_enabled() -> bool:
    """Return True when FEATURE_REPAIR_V2 env var is set to a truthy value."""
    return os.environ.get("FEATURE_REPAIR_V2", "").lower() in ("1", "true", "yes", "on")


@dataclass
class RepairResult:
    ok: bool
    rounds: int
    final_code: str
    scratchpad: List[str] = field(default_factory=list)
    error: Optional[str] = None
    elapsed_ms: int = 0


async def _noop_emit(event: str, payload: Dict[str, Any]) -> None:
    return None


async def run_repair_loop(
    initial_code: str,
    attempt_fn: AttemptFn,
    verify_fn: VerifyFn,
    *,
    max_rounds: int = 5,
    emit: Optional[EmitFn] = None,
) -> RepairResult:
    """Run up to `max_rounds` repair iterations with an accumulating scratchpad."""
    emit = emit or _noop_emit
    scratchpad: List[str] = []
    current = initial_code
    t0 = time.monotonic()

    for r in range(1, max_rounds + 1):
        await emit("repair.round.start", {"round": r, "scratchpad_lines": len(scratchpad)})

        # Let the fixer see prior failure notes and produce a new attempt.
        try:
            current = await attempt_fn(current, list(scratchpad))
        except Exception as exc:  # repair itself exploded
            err = f"attempt_fn raised: {exc!r}"
            scratchpad.append(f"round {r}: {err}")
            await emit("repair.round.end", {"round": r, "ok": False, "error": err})
            continue

        verdict = await verify_fn(current)
        ok = bool(verdict.get("ok"))
        err = verdict.get("error")

        await emit("repair.round.end", {"round": r, "ok": ok, "error": err})

        if ok:
            result = RepairResult(
                ok=True,
                rounds=r,
                final_code=current,
                scratchpad=scratchpad,
                error=None,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )
            await emit("repair.final", {"ok": True, "rounds": r, "final_code": current})
            return result

        # Remember what went wrong so the next round can read it.
        entry = f"round {r}: {err or 'verification failed'}"
        ev = verdict.get("evidence")
        if ev:
            entry += f" | evidence={ev}"
        scratchpad.append(entry)

    result = RepairResult(
        ok=False,
        rounds=max_rounds,
        final_code=current,
        scratchpad=scratchpad,
        error=scratchpad[-1] if scratchpad else "max rounds reached",
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
    await emit("repair.final", {"ok": False, "rounds": max_rounds, "final_code": current})
    return result
