"""Structured logging configuration via structlog."""

from __future__ import annotations

import logging

import structlog


def setup_logging(log_level: str = "INFO", service_name: str = "") -> None:
    """Configure structlog with JSON rendering and context variable support."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Bind service name globally
    if service_name:
        structlog.contextvars.bind_contextvars(service_name=service_name)


def bind_request_context(tenant_id: str = "", thread_id: str = "", trace_id: str = ""):
    """Bind request-scoped context variables for structured logging."""
    structlog.contextvars.bind_contextvars(
        tenant_id=tenant_id,
        thread_id=thread_id,
        trace_id=trace_id,
    )
