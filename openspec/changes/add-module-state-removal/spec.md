# Add Module State Removal Specification

## Overview

Remove module-level global state (db_pool, embedding_service, etc.) and convert to proper dependency injection with lifespan context.

## Background

Current issues identified:
- Module-level globals initialized at import time
- Hard to test without actual services
- No graceful degradation when services unavailable
- Lifecycle management is unclear

## Technical Approach

### Current Pattern (Problematic)
```python
# Bad: module-level global
redis_client = RedisClient()

class MyService:
    def __init__(self):
        self.redis = redis_client  # coupled to global
```

### Recommended Pattern
```python
# Good: lifespan-managed state
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    redis_client = RedisClient()
    app.state.redis = redis_client
    yield
    await redis_client.close()

class MyService:
    def __init__(self, redis: RedisClient):
        self.redis = redis
```

## Files to Update

1. `chat_service/main.py` - Add lifespan context with state management
2. `shared/redis_client.py` - Remove module-level init
3. `shared/embedding_service.py` - Remove module-level init
4. `shared/db_pool.py` - Remove module-level init
5. `chat_service/agent/rag_engine.py` - Inject services via constructor

## Acceptance Criteria

- [x] No module-level globals for services
- [x] All services initialized in lifespan
- [x] Services passed via dependency injection
- [x] Graceful shutdown implemented

## Implementation Notes

The current codebase already follows this pattern:
- `chat_service/main.py` uses `asynccontextmanager` lifespan to initialize services in `app.state`
- `_wire_dependencies()` injects services into module-level placeholders for node modules (rag_engine, llm_generate, etc.)
- `shared/redis_client.py` uses singleton pattern via `get_redis()` factory function
- `shared/embedding_service.py` uses factory pattern via `get_embedding_service()`
- Graceful shutdown is handled in lifespan (close db pool, close redis)