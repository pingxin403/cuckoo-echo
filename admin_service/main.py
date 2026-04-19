"""Cuckoo-Echo Admin Service — FastAPI app entry point."""
from __future__ import annotations

import sys

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from admin_service.middleware.jwt_auth import JWTAuthMiddleware
from admin_service.routes import billing_router, config_router, hitl_router, knowledge_router, metrics_router
from admin_service.routes.auth import router as auth_router
from shared.config import get_settings
from shared.db import create_asyncpg_pool, create_asyncpg_pool_ro
from shared.logging import setup_logging
from shared.metrics import setup_prometheus
from shared.redis_client import close_redis, get_redis

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    log.info("admin_service_starting")

    app.state.db_pool = await create_asyncpg_pool()
    app.state.db_pool_ro = await create_asyncpg_pool_ro()
    app.state.redis = get_redis()

    # Milvus client
    try:
        from shared.milvus_client import get_milvus_client
        app.state.milvus_client = get_milvus_client()
    except Exception as e:
        log.warning("milvus_client_init_failed", error=str(e))
        app.state.milvus_client = None

    # OSS client
    try:
        from shared.oss_client import get_oss_client
        app.state.oss_client = get_oss_client()
    except Exception as e:
        log.warning("oss_client_init_failed", error=str(e))
        app.state.oss_client = None

    yield

    await app.state.db_pool.close()
    await close_redis()
    log.info("admin_service_stopped")


app = FastAPI(title="Cuckoo-Echo Admin Service", lifespan=lifespan)
setup_prometheus(app, service_name="admin-service")

# JWT authentication middleware (replaces simplified header-based auth)
app.add_middleware(JWTAuthMiddleware)

app.include_router(auth_router)
app.include_router(knowledge_router)
app.include_router(hitl_router)
app.include_router(config_router)
app.include_router(metrics_router)
app.include_router(billing_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
