"""
logger.py
=========

Structured JSON logging configuration for the Agentic Lending Platform.

Responsibilities
----------------
- Provide a ``get_logger(name)`` factory that returns a pre-configured logger.
- Output structured JSON logs (one JSON object per line) for easy ingestion
  by log aggregators (ELK, Datadog, CloudWatch).
- Support a **correlation ID** that can be injected per-request via
  middleware, enabling end-to-end request tracing.

Usage
-----
::

    from backend.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Processing loan application", extra={"session_id": "abc-123"})

Configuration
-------------
Log level and JSON format toggle are sourced from ``config.settings``.
"""

from __future__ import annotations

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Optional

# Lazy import to avoid circular dependency at module level
_settings_cache = None


def _get_settings():
    global _settings_cache
    if _settings_cache is None:
        from backend.config import settings
        _settings_cache = settings
    return _settings_cache


class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that outputs one JSON object per log line.

    Fields
    ------
    - ``timestamp`` — ISO 8601 UTC timestamp.
    - ``level``     — Log level name.
    - ``logger``    — Logger name (usually module path).
    - ``message``   — Formatted log message.
    - ``correlation_id`` — Request-scoped trace ID (if present).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach correlation ID if present
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Attach any extra fields
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def get_logger(name: str, correlation_id: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger instance.

    Parameters
    ----------
    name : str
        Logger name — typically ``__name__`` of the calling module.
    correlation_id : str or None
        Optional correlation ID to attach to all messages from this logger.

    Returns
    -------
    logging.Logger
        Configured logger ready for use.
    """
    settings = _get_settings()
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        if settings.LOG_JSON_FORMAT:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    return logger
