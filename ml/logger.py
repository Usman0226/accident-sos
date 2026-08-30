"""
Structured JSON logger for production-grade audit trails.

Every log entry includes timestamp, actor, action, resource_id per the
project's auditability requirements. No print() in production paths.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "actor": getattr(record, "actor", "system"),
            "action": getattr(record, "action", record.funcName or "unknown"),
            "resource_id": getattr(record, "resource_id", None),
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
            entry["error_type"] = type(record.exc_info[1]).__name__
        return json.dumps(entry, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger with structured JSON output on stdout.
    Idempotent — safe to call multiple times with the same name.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(
    logger: logging.Logger,
    action: str,
    resource_id: Optional[str] = None,
    actor: str = "system",
    **kwargs: object,
) -> None:
    """Convenience wrapper for structured event logging with extra fields."""
    extra = {"actor": actor, "action": action, "resource_id": resource_id}
    message_parts = [f"{k}={v}" for k, v in kwargs.items()]
    logger.info(" ".join(message_parts) if message_parts else action, extra=extra)
