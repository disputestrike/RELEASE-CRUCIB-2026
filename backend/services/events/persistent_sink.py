"""Persistent JSONL event sink.

Subscribes to all events on the global event_bus and appends them to a
bounded JSONL file so the event stream is queryable historically without
requiring a DB connection.

Activate by calling ``setup(bus)``.  ``events/__init__.py`` does this
automatically on package import.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.events.event_bus import EventBus, EventRecord

_MAX_EVENTS = int(os.environ.get("CRUCIB_EVENT_LOG_MAX_ENTRIES", "10000"))


def _event_log_path() -> Path:
    from project_state import WORKSPACE_ROOT

    root = WORKSPACE_ROOT / "_events"
    root.mkdir(parents=True, exist_ok=True)
    return root / "events.jsonl"


def _enforce_retention(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]
    if len(lines) <= _MAX_EVENTS:
        return
    kept = lines[-_MAX_EVENTS:]
    with path.open("w", encoding="utf-8") as f:
        f.writelines(kept)


def _handle(record: "EventRecord") -> None:
    """Append a single event record to the persistent log."""
    try:
        entry: dict[str, Any] = {
            "event_type": record.event_type,
            "ts": record.ts,
            "payload": record.payload,
        }
        path = _event_log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")
        # Only check retention every 500 entries to avoid per-write overhead.
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        if size > 1_000_000:  # ~1 MB — run retention pass
            _enforce_retention(path)
    except Exception:
        # Sink must never break the event bus.
        pass


def setup(bus: "EventBus") -> None:
    """Subscribe the persistent sink to all events on ``bus``."""
    bus.subscribe("*", _handle)


def read_events(*, limit: int = 200, event_type: str | None = None) -> list[dict[str, Any]]:
    """Read recent events from the persistent log.

    Args:
        limit: Maximum number of events to return (most-recent first).
        event_type: Optional filter by event type.

    Returns:
        List of event dicts.
    """
    path = _event_log_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        records = []
        for ln in lines:
            try:
                records.append(json.loads(ln))
            except Exception:
                continue
        if event_type:
            records = [r for r in records if r.get("event_type") == event_type]
        records.reverse()  # most recent first
        return records[: max(1, int(limit))]
    except Exception:
        return []
