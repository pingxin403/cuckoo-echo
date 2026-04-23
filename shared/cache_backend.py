"""Cache backend interface for Redis decoupling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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