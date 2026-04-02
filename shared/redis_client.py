"""Redis client utilities for Cuckoo-Echo.

Provides async Redis client creation with automatic environment-based
configuration: reads ``REDIS_URL`` via pydantic-settings for production
(supports Cluster DSN), falls back to ``redis://localhost:6379/0`` for
local development.
"""

from __future__ import annotations

import redis.asyncio as aioredis
import structlog

from shared.config import get_settings

log = structlog.get_logger()

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a shared async Redis client.

    Reads ``REDIS_URL`` from pydantic-settings; defaults to
    ``redis://localhost:6379/0`` for local development.
    """
    global _client
    if _client is not None:
        return _client

    url = get_settings().redis_url
    log.info("connecting_to_redis", url=url)
    _client = aioredis.from_url(url)
    return _client


async def close_redis() -> None:
    """Close the shared Redis client and release resources."""
    global _client
    if _client is not None:
        log.info("closing_redis_connection")
        await _client.aclose()
        _client = None
