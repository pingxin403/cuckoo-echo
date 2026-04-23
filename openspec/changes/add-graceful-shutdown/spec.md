# Graceful Shutdown Handler

## Problem / 问题

Currently the services (chat_service, admin_service, asr_service, api_gateway) lack proper graceful shutdown handling. Abrupt shutdown can cause:
- In-flight requests to be dropped
- Redis connections to leak
- Database pools to leave dirty state
- Checkpointer writes to be lost

## Background / 背景

All services use FastAPI with Uvicorn. Uvicorn supports graceful shutdown via lifespan events, but current implementation doesn't handle:
- Pending request completion before shutdown
- Connection pool cleanup
- Redis client graceful closure
- Checkpointer flush

## Requirements / 需求

1. **Shutdown Signal Handling**
   - Catch SIGTERM/SIGINT signals
   - Stop accepting new requests
   - Wait for in-flight requests to complete (with timeout)

2. **Connection Pool Cleanup**
   - Close asyncpg pools gracefully
   - Close Redis connections
   - Close Milvus connections

3. **Resource Cleanup Hooks**
   - Flush checkpointer pending writes
   - Close embeddings service
   - Close LLM gateway connections

4. **Health Check Integration**
   - Report \"shutting_down\" state during graceful shutdown
   - Prevent new traffic during shutdown

## Implementation / 实现方案

```python
# shared/shutdown.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import signal

async def lifespan(app: FastAPI):
    # Startup
    yield
    
    # Graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: request_shutdown())
    
    await wait_for_pending_requests(timeout=30)
    await cleanup_resources()
```

## Acceptance Criteria / 验收标准

- [ ] SIGTERM triggers graceful shutdown within 30s
- [ ] In-flight requests complete or timeout gracefully
- [ ] No connection leaks after shutdown
- [ ] Health endpoint reports \"shutting_down\" state
- [ ] All asyncpg pools closed
- [ ] All Redis clients closed