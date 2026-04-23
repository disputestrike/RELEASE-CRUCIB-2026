"""Event services package.

On import, activates the persistent event sink so all bus events are
written to a bounded JSONL log for historical querying.
"""

from .event_bus import event_bus, EventBus, EventRecord
from . import persistent_sink as _sink

_sink.setup(event_bus)

__all__ = ["event_bus", "EventBus", "EventRecord"]
