"""Lightweight in-process event bus for backend lifecycle events."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, DefaultDict, Dict, List, Optional


@dataclass
class EventRecord:
    event_type: str
    payload: Dict[str, Any]
    ts: float


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: DefaultDict[str, List[Callable[[EventRecord], None]]] = defaultdict(list)
        self._recent: List[EventRecord] = []
        self._max_recent = 500

    def subscribe(self, event_type: str, callback: Callable[[EventRecord], None]) -> None:
        with self._lock:
            self._subscribers[event_type].append(callback)

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> EventRecord:
        rec = EventRecord(event_type=event_type, payload=payload or {}, ts=time.time())
        with self._lock:
            self._recent.append(rec)
            if len(self._recent) > self._max_recent:
                self._recent = self._recent[-self._max_recent :]
            callbacks = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))
        for cb in callbacks:
            try:
                cb(rec)
            except Exception:
                # Subscribers must not break request flow.
                pass
        return rec

    def recent_events(self, limit: int = 100) -> List[EventRecord]:
        n = max(1, min(int(limit), self._max_recent))
        with self._lock:
            return list(self._recent[-n:])


event_bus = EventBus()
