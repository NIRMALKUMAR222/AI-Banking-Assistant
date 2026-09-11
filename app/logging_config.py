"""
app/logging_config.py - Structured JSON logging for the SecureBank API.

Features
--------
- JSON-formatted log lines (compatible with Datadog, CloudWatch, GCP Logging)
- Request/response audit middleware
- Correlation IDs per request (X-Request-ID header)
- Separate audit logger for security-sensitive events
- Configurable log level via LOG_LEVEL env var
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }
        # Merge any extra fields passed via `extra={...}`
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            ):
                base[key] = val
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        return json.dumps(base, default=str)


def setup_logging():
    """
    Configure the root logger and named loggers.
    Call once at application startup.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    formatter = JsonFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Named loggers (import these in other modules)
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Dedicated audit logger for security events
audit_logger = logging.getLogger("securebank.audit")


def log_auth_event(
    event: str,
    username: str | None,
    success: bool,
    extra: dict | None = None,
):
    """Emit a structured auth audit event."""
    audit_logger.info(
        event,
        extra={
            "audit_event": event,
            "username":    username,
            "success":     success,
            **(extra or {}),
        },
    )


def log_chat_event(
    account_id_prefix: str | None,
    intent: str,
    query_length: int,
    risk_score: int,
    latency_ms: int,
):
    """Emit a structured chat audit event (no raw PII)."""
    audit_logger.info(
        "chat_request",
        extra={
            "audit_event":        "chat_request",
            "account_id_prefix":  account_id_prefix,
            "intent":             intent,
            "query_length":       query_length,
            "risk_score":         risk_score,
            "latency_ms":         latency_ms,
        },
    )


# ---------------------------------------------------------------------------
# Request/response logging middleware
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with:
    - method, path, status code, duration
    - X-Request-ID (generated if not provided)
    - client IP (as reported by the server)
    """

    _logger = logging.getLogger("securebank.http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Assign or inherit a correlation ID
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        start  = time.perf_counter()

        response = await call_next(request)

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = req_id

        self._logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "request_id": req_id,
                "method":     request.method,
                "path":       request.url.path,
                "status":     response.status_code,
                "duration_ms": duration_ms,
                "client":     request.client.host if request.client else "unknown",
            },
        )
        return response