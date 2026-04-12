"""
Enhanced structured logging system with correlation IDs for tracing across 123 agents.

Every log entry includes:
- Timestamp (ISO 8601)
- Trace ID (unique per request)
- Agent ID (which agent generated the log)
- Log level
- Message
- Context (request data, user, etc.)
- No secrets (passwords, tokens, etc.)
"""

import contextvars
import json
import logging
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger
from pythonjsonlogger.jsonlogger import JsonFormatter

# Context variables for distributed tracing
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)
agent_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "agent_id", default=""
)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")


class StructuredFormatter(JsonFormatter):
    """Custom JSON formatter with correlation IDs and context."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add trace context
        log_record["trace_id"] = trace_id_var.get() or str(uuid.uuid4())
        log_record["request_id"] = request_id_var.get()
        log_record["agent_id"] = agent_id_var.get()
        log_record["user_id"] = user_id_var.get()

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add function and line number
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exc(),
            }

        # Add duration if available
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms

        # Add status if available
        if hasattr(record, "status"):
            log_record["status"] = record.status

        # Remove unnecessary fields
        log_record.pop("message", None)
        log_record.pop("asctime", None)


class SecureFormatter(StructuredFormatter):
    """Formatter that removes sensitive data from logs."""

    SENSITIVE_KEYS = {
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "x-api-key",
        "credit_card",
        "ssn",
        "private_key",
    }

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add fields while removing sensitive data."""
        # Remove sensitive data from message
        if "msg" in message_dict:
            message_dict["msg"] = self._redact_sensitive(message_dict["msg"])

        super().add_fields(log_record, record, message_dict)

        # Redact any sensitive fields in the log record
        for key in list(log_record.keys()):
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                log_record[key] = "***REDACTED***"

    def _redact_sensitive(self, text: str) -> str:
        """Redact sensitive information from text."""
        import re

        # Redact API keys
        text = re.sub(r"sk_[a-zA-Z0-9]{20,}", "sk_***REDACTED***", text)
        text = re.sub(r"pk_[a-zA-Z0-9]{20,}", "pk_***REDACTED***", text)

        # Redact tokens
        text = re.sub(r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "Bearer ***REDACTED***", text)

        return text


def setup_logging(
    name: str,
    level: str = "INFO",
    secure: bool = True,
) -> logging.Logger:
    """
    Set up structured logging for a module.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        secure: Whether to redact sensitive data

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers = []

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter_class = SecureFormatter if secure else StructuredFormatter
    formatter = formatter_class(fmt="%(timestamp)s %(level)s %(logger)s %(message)s")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def set_trace_context(
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Set context variables for distributed tracing.

    Args:
        trace_id: Unique trace ID for the entire request
        request_id: Unique request ID
        agent_id: ID of the agent processing
        user_id: ID of the user making the request
    """
    if trace_id:
        trace_id_var.set(trace_id)
    if request_id:
        request_id_var.set(request_id)
    if agent_id:
        agent_id_var.set(agent_id)
    if user_id:
        user_id_var.set(user_id)


def get_trace_context() -> Dict[str, str]:
    """Get current trace context."""
    return {
        "trace_id": trace_id_var.get(),
        "request_id": request_id_var.get(),
        "agent_id": agent_id_var.get(),
        "user_id": user_id_var.get(),
    }


def clear_trace_context() -> None:
    """Clear trace context."""
    trace_id_var.set("")
    request_id_var.set("")
    agent_id_var.set("")
    user_id_var.set("")


# Global logger instance
logger = setup_logging(__name__)


# Example usage
if __name__ == "__main__":
    # Set up context
    set_trace_context(
        trace_id="trace-123",
        request_id="req-456",
        agent_id="agent-frontend",
        user_id="user-789",
    )

    # Log examples
    logger.info("Build started", extra={"status": "started"})
    logger.info("Agent processing", extra={"duration_ms": 1250})
    logger.warning("Slow agent detected", extra={"duration_ms": 5000})
    logger.error("Agent failed", extra={"status": "failed"})

    # Clear context
    clear_trace_context()
