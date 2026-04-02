"""Cuckoo-Echo API Gateway.

Wires authentication, rate-limiting middleware and exposes the ``/health``
endpoint.  Circuit breaking is applied at the function-call level (see
``circuit_breaker.py``), not as HTTP middleware.

Production: ``granian --interface asgi api_gateway.main:app``
Development: ``uvicorn api_gateway.main:app --reload``
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from shared.config import get_settings
from shared.db import create_asyncpg_pool
from shared.logging import setup_logging
from shared.redis_client import get_redis

from api_gateway.middleware.auth import TenantAuthMiddleware
from api_gateway.middleware.rate_limit import RateLimitMiddleware

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    log.info("gateway_starting", environment=settings.environment)

    app.state.db_pool = await create_asyncpg_pool()
    app.state.redis = get_redis()
    yield
    await app.state.db_pool.close()
    log.info("gateway_stopped")


app = FastAPI(title="Cuckoo-Echo API Gateway", lifespan=lifespan)


# Middleware ordering in Starlette: last added wraps outermost.
# We want request flow: Auth → RateLimit → handler
# So add RateLimit first, then Auth (Auth wraps RateLimit).
def configure_middleware(app: FastAPI, db_pool, redis) -> None:
    """Attach middleware after the lifespan has initialised resources."""
    app.add_middleware(RateLimitMiddleware, db_pool=db_pool, redis=redis)
    app.add_middleware(TenantAuthMiddleware, db_pool=db_pool)


@app.on_event("startup")
async def _wire_middleware():
    """Wire middleware once db_pool and redis are available."""
    configure_middleware(app, app.state.db_pool, app.state.redis)


@app.get("/health")
async def health():
    return {"status": "ok"}
