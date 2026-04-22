"""Inter-agent shared context via Redis."""

from __future__ import annotations

import json
import structlog
from typing import Any

logger = structlog.get_logger(__name__)

GLOBAL_PREFIX = "ctx:global:"
ROLE_PREFIX = "ctx:role:"


class SharedContext:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def set_global(self, key: str, value: Any, ttl: int = 3600) -> None:
        redis_key = f"{GLOBAL_PREFIX}{key}"
        await self.redis.set(redis_key, json.dumps(value), ex=ttl)
        logger.debug("context_set_global", key=key, ttl=ttl)

    async def get_global(self, key: str) -> Any | None:
        redis_key = f"{GLOBAL_PREFIX}{key}"
        val = await self.redis.get(redis_key)
        if val:
            return json.loads(val)
        return None

    async def set_role(self, role: str, key: str, value: Any, ttl: int = 1800) -> None:
        redis_key = f"{ROLE_PREFIX}{role}:{key}"
        await self.redis.set(redis_key, json.dumps(value), ex=ttl)
        logger.debug("context_set_role", role=role, key=key, ttl=ttl)

    async def get_role(self, role: str, key: str) -> Any | None:
        redis_key = f"{ROLE_PREFIX}{role}:{key}"
        val = await self.redis.get(redis_key)
        if val:
            return json.loads(val)
        return None

    async def clear_role(self, role: str) -> None:
        pattern = f"{ROLE_PREFIX}{role}:*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)
            logger.info("context_cleared_role", role=role, count=len(keys))