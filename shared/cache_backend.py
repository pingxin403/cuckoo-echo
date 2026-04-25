"""Cache backend interface for Redis decoupling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import orjson
import structlog
from shared.redis_client import get_redis

log = structlog.get_logger()


class CacheBackend(ABC):
    """Abstract interface for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        raise NotImplementedError

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """Set a value in cache with optional TTL."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        raise NotImplementedError

    @abstractmethod
    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        """Get multiple values from cache."""
        raise NotImplementedError

    @abstractmethod
    async def set_many(
        self, mapping: dict[str, Any], ttl: int | None = None
    ) -> None:
        """Set multiple values in cache."""
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        """Clear all keys from cache."""
        raise NotImplementedError

    @abstractmethod
    async def ping(self) -> bool:
        """Health check for cache backend."""
        raise NotImplementedError


class RedisCacheBackend(CacheBackend):
    """Redis implementation of CacheBackend."""

    def __init__(self, prefix: str = "cache:"):
        self.prefix = prefix
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def get(self, key: str) -> Any | None:
        redis = await self._get_redis()
        value = await redis.get(f"{self.prefix}{key}")
        if value is None:
            return None
        return orjson.loads(value)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        redis = await self._get_redis()
        serialized = orjson.dumps(value)
        if ttl:
            await redis.setex(f"{self.prefix}{key}", ttl, serialized)
        else:
            await redis.set(f"{self.prefix}{key}", serialized)

    async def delete(self, key: str) -> None:
        redis = await self._get_redis()
        await redis.delete(f"{self.prefix}{key}")

    async def exists(self, key: str) -> bool:
        redis = await self._get_redis()
        return await redis.exists(f"{self.prefix}{key}") > 0

    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        redis = await self._get_redis()
        full_keys = [f"{self.prefix}{k}" for k in keys]
        values = await redis.mget(full_keys)
        result = {}
        for k, v in zip(keys, values):
            if v is not None:
                result[k] = orjson.loads(v)
            else:
                result[k] = None
        return result

    async def set_many(
        self, mapping: dict[str, Any], ttl: int | None = None
    ) -> None:
        redis = await self._get_redis()
        pipeline = redis.pipeline()
        for key, value in mapping.items():
            serialized = orjson.dumps(value)
            if ttl:
                pipeline.setex(f"{self.prefix}{key}", ttl, serialized)
            else:
                pipeline.set(f"{self.prefix}{key}", serialized)
        await pipeline.execute()

    async def clear(self) -> None:
        redis = await self._get_redis()
        keys = await redis.keys(f"{self.prefix}*")
        if keys:
            await redis.delete(*keys)

    async def ping(self) -> bool:
        try:
            redis = await self._get_redis()
            return await redis.ping()
        except Exception:
            return False


__all__ = ["CacheBackend", "RedisCacheBackend"]