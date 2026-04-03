"""Cuckoo-Echo Admin Service — FastAPI app entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from starlette.responses import Response

from shared.config import get_settings
from shared.logging import setup_logging
from shared.db import create_asyncpg_pool
from shared.redis_client import get_redis, close_redis
from admin_service.routes import knowledge_router, hitl_router, config_router, metrics_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    log.info("admin_service_starting")

    app.state.db_pool = await create_asyncpg_pool()
    app.state.db_pool_ro = app.state.db_pool  # TODO: separate read-replica pool
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


# Auth middleware for admin (simplified — production would use JWT/session)
@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next) -> Response:
    # TODO: implement proper admin auth
    request.state.tenant_id = request.headers.get("X-Tenant-ID", "")
    request.state.admin_user_id = request.headers.get("X-Admin-User-ID", "")
    return await call_next(request)


app.include_router(knowledge_router)
app.include_router(hitl_router)
app.include_router(config_router)
app.include_router(metrics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
