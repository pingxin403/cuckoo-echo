"""In-memory cache fallback for unit tests and Redis failures."""

from __future__ import annotations

import time
from typing import Any

from shared.cache_backend import CacheBackend


class MemoryCache(CacheBackend):
    """In-memory cache backend for testing and fallback."""

    def __init__(self, default_ttl: int = 3600):
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.time() + (ttl or self._default_ttl)
        self._store[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        if key not in self._store:
            return False
        _, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return False
        return True

    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result

    async def set_many(
        self, mapping: dict[str, Any], ttl: int | None = None
    ) -> None:
        for key, value in mapping.items():
            await self.set(key, value, ttl)

    async def clear(self) -> None:
        self._store.clear()

    async def ping(self) -> bool:
        return True


memory_cache = MemoryCache()