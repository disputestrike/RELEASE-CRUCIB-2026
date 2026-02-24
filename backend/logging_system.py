"""
Structured logging system for CrucibAI.

Provides JSON-formatted logs with trace IDs, agent context, and performance metrics.
"""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import structlog


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace ID if available
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id

        # Add agent context if available
        if hasattr(record, "agent_name"):
            log_data["agent"] = record.agent_name
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id

        # Add performance metrics if available
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "tokens_used"):
            log_data["tokens_used"] = record.tokens_used

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Wrapper around Python logging with structured fields."""

    def __init__(self, name: str, level: str = "INFO"):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))

        # Remove existing handlers
        self.logger.handlers = []

        # Add JSON handler to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

        # Add file handler
        file_handler = logging.FileHandler(f"logs/{name}.log")
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

        self.trace_id = str(uuid.uuid4())

    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add trace ID and other context to log record."""
        context = {"trace_id": self.trace_id}
        if extra:
            context.update(extra)
        return context

    def info(self, message: str, **kwargs):
        """Log info level message."""
        extra = self._add_context(kwargs)
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        self.logger.handle(record)

    def error(self, message: str, **kwargs):
        """Log error level message."""
        extra = self._add_context(kwargs)
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        self.logger.handle(record)

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        extra = self._add_context(kwargs)
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        self.logger.handle(record)

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        extra = self._add_context(kwargs)
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        self.logger.handle(record)

    @contextmanager
    def timer(self, operation: str, **kwargs):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"{operation} completed",
                duration_ms=duration_ms,
                **kwargs,
            )


class AgentLogger(StructuredLogger):
    """Logger for agent operations."""

    def __init__(self, agent_name: str, agent_id: str):
        """Initialize agent logger."""
        super().__init__(f"agent.{agent_name}")
        self.agent_name = agent_name
        self.agent_id = agent_id

    def log_execution(self, status: str, **kwargs):
        """Log agent execution."""
        self.info(
            f"Agent {self.agent_name} execution: {status}",
            agent_name=self.agent_name,
            agent_id=self.agent_id,
            **kwargs,
        )

    def log_error(self, error: Exception, **kwargs):
        """Log agent error."""
        self.error(
            f"Agent {self.agent_name} error: {str(error)}",
            agent_name=self.agent_name,
            agent_id=self.agent_id,
            error_type=type(error).__name__,
            **kwargs,
        )


class BuildLogger(StructuredLogger):
    """Logger for build operations."""

    def __init__(self, build_id: str):
        """Initialize build logger."""
        super().__init__(f"build.{build_id}")
        self.build_id = build_id

    def log_phase(self, phase: str, status: str, **kwargs):
        """Log build phase."""
        self.info(
            f"Build phase {phase}: {status}",
            build_id=self.build_id,
            phase=phase,
            **kwargs,
        )

    def log_agent_execution(self, agent_name: str, duration_ms: float, **kwargs):
        """Log agent execution within build."""
        self.info(
            f"Agent {agent_name} executed",
            build_id=self.build_id,
            agent_name=agent_name,
            duration_ms=duration_ms,
            **kwargs,
        )


# Global logger instances
app_logger = StructuredLogger("crucibai.app")
agent_logger = StructuredLogger("crucibai.agent")
build_logger = StructuredLogger("crucibai.build")
database_logger = StructuredLogger("crucibai.database")
api_logger = StructuredLogger("crucibai.api")
