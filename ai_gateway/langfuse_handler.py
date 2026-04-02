"""Langfuse callback handler for LLM observability."""

from __future__ import annotations

import structlog

from shared.config import get_settings

log = structlog.get_logger()


def get_langfuse_handler(thread_id: str | None = None, span_name: str | None = None):
    """Create a Langfuse callback handler for LLM call tracing.

    Returns ``None`` if Langfuse is not configured (empty keys).

    Supports both Langfuse v2 (``langfuse.callback.CallbackHandler``) and
    Langfuse v4+ (``langfuse.Langfuse`` client).  When neither is available
    the function returns ``None`` so callers can safely skip tracing.
    """
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return client
    except ImportError:
        log.warning("langfuse_not_installed")
        return None
