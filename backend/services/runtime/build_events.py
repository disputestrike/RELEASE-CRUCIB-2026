"""
build_events.py — Event system for real-time build progress reporting
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class BuildEventType(str, Enum):
    """Build event types for progress tracking."""
    BUILD_STARTED = "build_started"
    BUILD_PHASE_STARTED = "build_phase_started"
    BUILD_PHASE_COMPLETED = "build_phase_completed"
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    FILE_GENERATED = "file_generated"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"


class BuildEvent:
    """Represents a single build event."""
    
    def __init__(
        self,
        event_type: BuildEventType,
        project_id: str,
        message: str,
        data: Dict[str, Any] = None,
    ):
        self.event_type = event_type
        self.project_id = project_id
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "project_id": self.project_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class BuildEventBus:
    """Manages build events and subscribers."""
    
    def __init__(self):
        # Key: project_id, Value: list of subscriber callbacks
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.event_history: Dict[str, List[BuildEvent]] = {}
        self._lock = asyncio.Lock()
    
    async def subscribe(self, project_id: str, callback: Callable) -> None:
        """Subscribe to events for a specific project."""
        async with self._lock:
            if project_id not in self.subscribers:
                self.subscribers[project_id] = set()
            self.subscribers[project_id].add(callback)
            logger.debug(f"Subscriber added for project {project_id}")
    
    async def unsubscribe(self, project_id: str, callback: Callable) -> None:
        """Unsubscribe from events."""
        async with self._lock:
            if project_id in self.subscribers:
                self.subscribers[project_id].discard(callback)
                if not self.subscribers[project_id]:
                    del self.subscribers[project_id]
            logger.debug(f"Subscriber removed for project {project_id}")
    
    async def emit(self, event: BuildEvent) -> None:
        """Emit an event to all subscribers."""
        async with self._lock:
            # Store in history
            if event.project_id not in self.event_history:
                self.event_history[event.project_id] = []
            self.event_history[event.project_id].append(event)
            
            # Keep history limited to last 1000 events per project
            if len(self.event_history[event.project_id]) > 1000:
                self.event_history[event.project_id] = self.event_history[event.project_id][-1000:]
            
            # Notify subscribers
            subscribers = self.subscribers.get(event.project_id, set()).copy()
        
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event subscriber: {e}")
    
    async def get_history(self, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get event history for a project."""
        async with self._lock:
            events = self.event_history.get(project_id, [])
            # Return most recent events
            events_subset = events[-limit:]
            return [e.to_dict() for e in events_subset]
    
    async def clear_history(self, project_id: str) -> None:
        """Clear event history for a project."""
        async with self._lock:
            if project_id in self.event_history:
                del self.event_history[project_id]


# Global event bus instance
_event_bus: Optional[BuildEventBus] = None


def get_build_event_bus() -> BuildEventBus:
    """Get or create the global build event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = BuildEventBus()
    return _event_bus


async def emit_build_started(project_id: str, prompt: str) -> None:
    """Emit build started event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.BUILD_STARTED,
        project_id,
        f"Build started for project {project_id}",
        {"prompt": prompt[:200]},
    )
    await bus.emit(event)


async def emit_phase_started(project_id: str, phase_name: str, phase_number: int, total_phases: int) -> None:
    """Emit phase started event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.BUILD_PHASE_STARTED,
        project_id,
        f"Phase {phase_number}/{total_phases}: {phase_name}",
        {
            "phase_name": phase_name,
            "phase_number": phase_number,
            "total_phases": total_phases,
            "progress": (phase_number - 1) / total_phases,
        },
    )
    await bus.emit(event)


async def emit_agent_started(project_id: str, agent_name: str) -> None:
    """Emit agent started event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.AGENT_STARTED,
        project_id,
        f"Agent {agent_name} started",
        {"agent_name": agent_name},
    )
    await bus.emit(event)


async def emit_agent_completed(project_id: str, agent_name: str, duration_sec: float) -> None:
    """Emit agent completed event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.AGENT_COMPLETED,
        project_id,
        f"Agent {agent_name} completed in {duration_sec:.1f}s",
        {"agent_name": agent_name, "duration_seconds": duration_sec},
    )
    await bus.emit(event)


async def emit_file_generated(project_id: str, file_path: str, file_size: int) -> None:
    """Emit file generated event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.FILE_GENERATED,
        project_id,
        f"Generated file: {file_path} ({file_size} bytes)",
        {"file_path": file_path, "file_size": file_size},
    )
    await bus.emit(event)


async def emit_validation_completed(project_id: str, is_valid: bool, confidence: float) -> None:
    """Emit validation completed event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.VALIDATION_COMPLETED,
        project_id,
        f"Validation completed: {'✅ Valid' if is_valid else '❌ Invalid'} ({confidence:.0%} confidence)",
        {"is_valid": is_valid, "confidence": confidence},
    )
    await bus.emit(event)


async def emit_build_completed(project_id: str, duration_sec: float) -> None:
    """Emit build completed event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.BUILD_COMPLETED,
        project_id,
        f"Build completed in {duration_sec:.1f}s",
        {"duration_seconds": duration_sec},
    )
    await bus.emit(event)


async def emit_build_failed(project_id: str, error_message: str) -> None:
    """Emit build failed event."""
    bus = get_build_event_bus()
    event = BuildEvent(
        BuildEventType.BUILD_FAILED,
        project_id,
        f"Build failed: {error_message}",
        {"error_message": error_message},
    )
    await bus.emit(event)
