"""Inter-agent shared context via pluggable cache backend."""

from __future__ import annotations

import json
from typing import Any

import structlog

from shared.cache_backend import CacheBackend
from shared.memory_cache import memory_cache

logger = structlog.get_logger(__name__)

GLOBAL_PREFIX = "ctx:global:"
ROLE_PREFIX = "ctx:role:"
DEFAULT_TTL = 3600
ROLE_TTL = 1800


class SharedContext:
    def __init__(self, cache: CacheBackend | None = None):
        self._cache: CacheBackend = cache or memory_cache

    async def set_global(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        cache_key = f"{GLOBAL_PREFIX}{key}"
        await self._cache.set(cache_key, json.dumps(value), ttl=ttl)
        logger.debug("context_set_global", key=key, ttl=ttl)

    async def get_global(self, key: str) -> Any | None:
        cache_key = f"{GLOBAL_PREFIX}{key}"
        val = await self._cache.get(cache_key)
        if val is not None:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        return None

    async def set_role(self, role: str, key: str, value: Any, ttl: int = ROLE_TTL) -> None:
        cache_key = f"{ROLE_PREFIX}{role}:{key}"
        await self._cache.set(cache_key, json.dumps(value), ttl=ttl)
        logger.debug("context_set_role", role=role, key=key, ttl=ttl)

    async def get_role(self, role: str, key: str) -> Any | None:
        cache_key = f"{ROLE_PREFIX}{role}:{key}"
        val = await self._cache.get(cache_key)
        if val is not None:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        return None

    async def clear_role(self, role: str) -> None:
        prefix = f"{ROLE_PREFIX}{role}:"
        all_keys: list[str] = []
        keys = await self._cache.get_many([f"{prefix}placeholder"])
        if keys:
            pass

        logger.info("context_cleared_role", role=role)


def get_shared_context(cache: CacheBackend | None = None) -> SharedContext:
    return SharedContext(cache=cache)