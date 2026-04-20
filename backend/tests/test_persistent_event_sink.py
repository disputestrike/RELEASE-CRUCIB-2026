from __future__ import annotations

import json
import time
import uuid

import pytest

from services.events.event_bus import EventBus
from services.events.persistent_sink import read_events, setup


def test_setup_and_emit_persists_event(tmp_path, monkeypatch):
    import services.events.persistent_sink as sink_mod

    monkeypatch.setattr(sink_mod, "_event_log_path", lambda: tmp_path / "events.jsonl")

    bus = EventBus()
    setup(bus)

    bus.emit("test.event", {"key": "value"})
    time.sleep(0.05)  # allow sync write

    events = read_events()
    # read_events uses the real path, but we need to read from tmp_path
    log_path = tmp_path / "events.jsonl"
    assert log_path.exists()
    lines = [l for l in log_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_type"] == "test.event"
    assert record["payload"]["key"] == "value"


def test_multiple_events_all_persisted(tmp_path, monkeypatch):
    import services.events.persistent_sink as sink_mod

    monkeypatch.setattr(sink_mod, "_event_log_path", lambda: tmp_path / "events.jsonl")

    bus = EventBus()
    setup(bus)

    for i in range(5):
        bus.emit(f"event.{i}", {"index": i})
    time.sleep(0.05)

    log_path = tmp_path / "events.jsonl"
    lines = [l for l in log_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 5


def test_retention_enforced(tmp_path, monkeypatch):
    import services.events.persistent_sink as sink_mod

    monkeypatch.setattr(sink_mod, "_event_log_path", lambda: tmp_path / "events.jsonl")
    monkeypatch.setattr(sink_mod, "_MAX_EVENTS", 3)

    # Pre-fill the file with 4 entries to trigger retention on next write.
    log_path = tmp_path / "events.jsonl"
    for i in range(4):
        entry = json.dumps({"event_type": "old", "ts": time.time(), "payload": {"i": i}})
        log_path.open("a").write(entry + "\n")

    # Trigger retention by calling _enforce_retention directly.
    sink_mod._enforce_retention(log_path)

    lines = [l for l in log_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 3


def test_sink_does_not_break_bus_on_error(tmp_path, monkeypatch):
    """Even if the sink write fails, the event bus must continue."""
    import services.events.persistent_sink as sink_mod

    def _bad_path():
        raise RuntimeError("disk full")

    monkeypatch.setattr(sink_mod, "_event_log_path", _bad_path)

    bus = EventBus()
    setup(bus)

    # This must not raise.
    rec = bus.emit("safe.event", {"ok": True})
    assert rec.event_type == "safe.event"
