"""Admin Metrics API routes."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Query

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/metrics")

RANGE_MAP = {"1d": "1 day", "7d": "7 days", "30d": "30 days"}


async def _get_ro_pool(request: Request):
    """Get read-only pool (falls back to main pool if RO not configured)."""
    return getattr(request.app.state, "db_pool_ro", request.app.state.db_pool)


@router.get("/overview")
async def metrics_overview(request: Request, range: str = Query("7d")):
    interval = RANGE_MAP.get(range, "7 days")
    tenant_id = request.state.tenant_id
    pool = await _get_ro_pool(request)
    async with pool.acquire() as conn:
        # Total conversations
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM threads WHERE tenant_id = $1 AND created_at >= NOW() - INTERVAL '{interval}'",
            tenant_id,
        )
        # Human transfer rate
        hitl_count = await conn.fetchval(
            f"SELECT COUNT(*) FROM hitl_sessions WHERE tenant_id = $1 AND started_at >= NOW() - INTERVAL '{interval}'",
            tenant_id,
        )
    return {
        "total_conversations": total or 0,
        "human_transfer_count": hitl_count or 0,
        "human_transfer_rate": round((hitl_count or 0) / max(total or 1, 1), 4),
        "range": range,
    }


@router.get("/tokens")
async def metrics_tokens(request: Request, range: str = Query("7d")):
    interval = RANGE_MAP.get(range, "7 days")
    tenant_id = request.state.tenant_id
    pool = await _get_ro_pool(request)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""SELECT COALESCE(SUM(tokens_used), 0) as total_tokens,
                       COUNT(*) as message_count
                FROM messages WHERE tenant_id = $1 AND role = 'assistant'
                AND created_at >= NOW() - INTERVAL '{interval}'""",
            tenant_id,
        )
    return {
        "total_tokens": row["total_tokens"] if row else 0,
        "message_count": row["message_count"] if row else 0,
        "range": range,
    }


@router.get("/missed-queries")
async def metrics_missed_queries(request: Request, range: str = Query("7d")):
    interval = RANGE_MAP.get(range, "7 days")
    tenant_id = request.state.tenant_id
    pool = await _get_ro_pool(request)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT LEFT(content, 50) as query_prefix, COUNT(*) as count
                FROM messages
                WHERE tenant_id = $1 AND role = 'user'
                AND created_at >= NOW() - INTERVAL '{interval}'
                AND (
                    thread_id IN (SELECT thread_id FROM hitl_sessions WHERE tenant_id = $1)
                )
                GROUP BY query_prefix
                ORDER BY count DESC
                LIMIT 20""",
            tenant_id,
        )
    return {"missed_queries": [dict(r) for r in rows], "range": range}


@router.post("/sandbox/run")
async def sandbox_run(request: Request):
    """Run RAG quality gate with Ragas metrics."""
    body = await request.json()
    tenant_id = request.state.tenant_id
    test_cases = body.get("test_cases", [])
    # Stub — actual Ragas integration requires running LLM
    log.info("sandbox_run", tenant_id=tenant_id, test_cases_count=len(test_cases))
    return {
        "status": "stub",
        "message": "Ragas quality gate not yet wired to live LLM",
        "test_cases_count": len(test_cases),
    }
