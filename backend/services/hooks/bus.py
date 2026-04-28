"""
Typed hook bus.

Gives runtime/tool/skill/session code a lifecycle API with named phases
instead of ad-hoc event-bus subscriptions.

Design goals:
  * Typed phases — callers use constants, not strings that drift.
  * Backward compatible with services.events.event_bus — every fired hook is
    also re-emitted onto the event bus under a canonical event_type so existing
    subscribers (session journal, persistent sink, telemetry, SSE streams)
    keep working unchanged.
  * Ordered synchronous dispatch — hooks inside the request path should be
    predictable. If a hook raises, the error is logged and swallowed so the
    caller isn't broken; the HookError is recorded via _hook_errors() for
    tests.
  * Safe default — unknown phases raise ValueError so typos don't silently
    no-op.

Integration:
  * ``register_hook(phase, callback)`` — any module can subscribe.
  * ``fire(phase, payload)`` — called by tool_executor, runtime_engine,
    task_manager at their lifecycle points.
  * The raw services.events.event_bus remains the underlying transport; the
    hook name is translated to an event_type like "hook.tool.pre" etc.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)


# ── Phase constants ──────────────────────────────────────────────────────────
# Tool lifecycle
HOOK_TOOL_PRE = "tool.pre"
HOOK_TOOL_POST = "tool.post"
HOOK_TOOL_ERROR = "tool.error"

# Task lifecycle
HOOK_TASK_PRE = "task.pre"
HOOK_TASK_POST = "task.post"
HOOK_TASK_ERROR = "task.error"

# Step lifecycle (sub-unit of a task in RuntimeEngine)
HOOK_STEP_PRE = "step.pre"
HOOK_STEP_POST = "step.post"
HOOK_STEP_ERROR = "step.error"

# Session lifecycle
HOOK_SESSION_START = "session.start"
HOOK_SESSION_END = "session.end"

VALID_PHASES = frozenset(
    {
        HOOK_TOOL_PRE,
        HOOK_TOOL_POST,
        HOOK_TOOL_ERROR,
        HOOK_TASK_PRE,
        HOOK_TASK_POST,
        HOOK_TASK_ERROR,
        HOOK_STEP_PRE,
        HOOK_STEP_POST,
        HOOK_STEP_ERROR,
        HOOK_SESSION_START,
        HOOK_SESSION_END,
    }
)


HookCallback = Callable[[Dict[str, Any]], None]


@dataclass
class HookError:
    phase: str
    callback_name: str
    error: str
    payload: Dict[str, Any] = field(default_factory=dict)


class HookBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hooks: Dict[str, List[Tuple[int, HookCallback]]] = {p: [] for p in VALID_PHASES}
        self._errors: List[HookError] = []
        self._max_errors = 100

    # ── Registration ────────────────────────────────────────────────────────
    def register(self, phase: str, callback: HookCallback, priority: int = 100) -> None:
        """
        Register a callback for a phase. Lower priority number fires first.
        Default priority 100 keeps library-level hooks ahead of app-level ones
        (0–99) or after them (101+).
        """
        if phase not in VALID_PHASES:
            raise ValueError(
                f"Unknown hook phase '{phase}'. Valid: {sorted(VALID_PHASES)}"
            )
        with self._lock:
            bucket = self._hooks[phase]
            bucket.append((priority, callback))
            bucket.sort(key=lambda item: item[0])

    def unregister(self, phase: str, callback: HookCallback) -> bool:
        """Remove the first matching callback; return True if removed."""
        if phase not in VALID_PHASES:
            return False
        with self._lock:
            bucket = self._hooks[phase]
            for i, (_, cb) in enumerate(bucket):
                if cb is callback:
                    bucket.pop(i)
                    return True
            return False

    def clear_phase(self, phase: str) -> None:
        if phase in VALID_PHASES:
            with self._lock:
                self._hooks[phase] = []

    # ── Dispatch ────────────────────────────────────────────────────────────
    def fire(self, phase: str, payload: Dict[str, Any]) -> None:
        """
        Dispatch a hook synchronously in priority order. Exceptions are
        recorded into self._errors (bounded) and swallowed so the calling
        request path isn't broken.

        Also re-emits the hook onto the underlying event_bus under the
        canonical event_type 'hook.<phase>' so existing event subscribers
        (session journal, persistent sink, telemetry) keep receiving it.
        """
        if phase not in VALID_PHASES:
            raise ValueError(
                f"Unknown hook phase '{phase}'. Valid: {sorted(VALID_PHASES)}"
            )
        with self._lock:
            callbacks = list(self._hooks[phase])

        data = dict(payload or {})
        data["_hook_phase"] = phase

        for _priority, cb in callbacks:
            try:
                cb(data)
            except Exception as exc:  # noqa: BLE001 — intentional broad catch
                name = getattr(cb, "__name__", repr(cb))
                err = HookError(
                    phase=phase,
                    callback_name=name,
                    error=str(exc),
                    payload={k: v for k, v in data.items() if k != "_hook_phase"},
                )
                self._record_error(err)
                logger.warning("hook callback %s failed on %s: %s", name, phase, exc)

        # Bridge to existing event bus for backward compat. Prefer services.events first
        # so tests that subscribe on services.events see the emission; dedupe singletons.
        bridge_payload = {k: v for k, v in data.items() if k != "_hook_phase"}
        event_type = f"hook.{phase}"
        buses_seen: List[Any] = []
        for mod_name in ("services.events", "backend.services.events"):
            try:
                m = __import__(mod_name, fromlist=["event_bus"])
                b = getattr(m, "event_bus", None)
                if b is None:
                    continue
                if any(b is x for x in buses_seen):
                    continue
                buses_seen.append(b)
                b.emit(event_type, bridge_payload)
            except Exception:  # noqa: BLE001 — best-effort
                continue

    # ── Introspection (primarily for tests) ─────────────────────────────────
    def _record_error(self, err: HookError) -> None:
        with self._lock:
            self._errors.append(err)
            if len(self._errors) > self._max_errors:
                self._errors = self._errors[-self._max_errors :]

    def recent_errors(self, limit: int = 20) -> List[HookError]:
        with self._lock:
            return list(self._errors[-limit:])

    def clear_errors(self) -> None:
        with self._lock:
            self._errors = []

    def listeners(self, phase: str) -> int:
        if phase not in VALID_PHASES:
            return 0
        with self._lock:
            return len(self._hooks[phase])


# Singleton used across backend.
hook_bus = HookBus()


# Convenience top-level API so callers don't have to import the instance.
def register_hook(phase: str, callback: HookCallback, priority: int = 100) -> None:
    hook_bus.register(phase, callback, priority=priority)


def unregister_hook(phase: str, callback: HookCallback) -> bool:
    return hook_bus.unregister(phase, callback)


def fire(phase: str, payload: Dict[str, Any]) -> None:
    hook_bus.fire(phase, payload)


__all__ = [
    "HookBus",
    "HookCallback",
    "HookError",
    "VALID_PHASES",
    "HOOK_TOOL_PRE",
    "HOOK_TOOL_POST",
    "HOOK_TOOL_ERROR",
    "HOOK_TASK_PRE",
    "HOOK_TASK_POST",
    "HOOK_TASK_ERROR",
    "HOOK_STEP_PRE",
    "HOOK_STEP_POST",
    "HOOK_STEP_ERROR",
    "HOOK_SESSION_START",
    "HOOK_SESSION_END",
    "hook_bus",
    "register_hook",
    "unregister_hook",
    "fire",
]
