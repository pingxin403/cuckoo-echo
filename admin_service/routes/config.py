"""Admin Config API routes — persona, model, rate-limit."""
from __future__ import annotations

import orjson
import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/config")


class PersonaUpdate(BaseModel):
    system_prompt: str
    persona_name: str | None = None


class ModelUpdate(BaseModel):
    model: str
    fallback_model: str | None = None
    temperature: float = 0.7


class RateLimitUpdate(BaseModel):
    tenant_rps: int = 100
    user_rps: int = 10


@router.put("/persona")
async def update_persona(body: PersonaUpdate, request: Request):
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id
    config = {"system_prompt": body.system_prompt, "persona_name": body.persona_name}
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE tenants SET llm_config = llm_config || $1::jsonb WHERE id = $2",
            orjson.dumps(config).decode(),
            tenant_id,
        )
    log.info("persona_updated", tenant_id=tenant_id)
    return {"updated": True}


@router.put("/model")
async def update_model(body: ModelUpdate, request: Request):
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id
    config = body.model_dump(exclude_none=True)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE tenants SET llm_config = llm_config || $1::jsonb WHERE id = $2",
            orjson.dumps(config).decode(),
            tenant_id,
        )
    log.info("model_updated", tenant_id=tenant_id)
    return {"updated": True}


@router.put("/rate-limit")
async def update_rate_limit(body: RateLimitUpdate, request: Request):
    db_pool = request.app.state.db_pool
    redis = request.app.state.redis
    tenant_id = request.state.tenant_id
    config = body.model_dump()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE tenants SET rate_limit = $1::jsonb WHERE id = $2",
            orjson.dumps(config).decode(),
            tenant_id,
        )
    # Invalidate cached rate-limit in Redis
    await redis.delete(f"cuckoo:ratelimit_config:{tenant_id}")
    log.info("rate_limit_updated", tenant_id=tenant_id)
    return {"updated": True}
