import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from backend.app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects for structured log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        # Custom extra attributes if provided
        if hasattr(record, "request_id"):
            log_obj["request_id"] = getattr(record, "request_id")
        if hasattr(record, "client_ip"):
            log_obj["client_ip"] = getattr(record, "client_ip")
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = getattr(record, "duration_ms")
        return json.dumps(log_obj)


class StandardFormatter(logging.Formatter):
    """Readable color/styled standard formatter for local development console."""

    def format(self, record: logging.LogRecord) -> str:
        req_part = f" [req:{record.request_id}]" if hasattr(record, "request_id") else ""
        dur_part = f" ({record.duration_ms:.1f}ms)" if hasattr(record, "duration_ms") else ""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"{ts} [{record.levelname:<5}] [{record.name}]{req_part}: {record.getMessage()}{dur_part}"


def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Use JSON formatter if configured or in production
    if getattr(settings, "LOG_FORMAT", "text").lower() == "json" or settings.ENVIRONMENT == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(StandardFormatter())

    root_logger.addHandler(handler)

    # Suppress overly chatty external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


logger = logging.getLogger("mineguard")
