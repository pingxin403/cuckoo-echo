# Add Redis Coupling Fix Specification

## Overview

Remove Redis dependency coupling in SharedContext using dependency injection and interface abstraction.

## Background

Current issue: SharedContext has direct Redis client import causing tight coupling. If Redis is unavailable, entire context layer fails.

## Technical Approach

### Interface Abstraction

```python
from abc import ABC, abstractmethod

class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]: ...
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = 300) -> None: ...
    @abstractmethod
    async def delete(self, key: str) -> None: ...

class RedisCache(CacheBackend):
    def __init__(self, redis_client):
        self.redis = redis_client
    ...

class InMemoryCache(CacheBackend):
    def __init__(self):
        self.store = {}
    ...
```

### Dependency Injection

SharedContext accepts cache_backend in constructor instead of creating Redis client directly.

## Files to Update

1. `chat_service/agent/shared_context.py` - Use CacheBackend interface
2. `shared/cache_backend.py` - New abstraction layer
3. `shared/redis_client.py` - Implement CacheBackend
4. `shared/memory_cache.py` - In-memory fallback implementation

## Acceptance Criteria

- [ ] CacheBackend interface created
- [ ] In-memory fallback for testing/development
- [ ] SharedContext uses dependency injection
- [ ] No direct Redis import in SharedContext