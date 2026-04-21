"""Admin Analytics API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel

from shared.analytics import (
    get_conversation_metrics,
    get_cost_metrics,
    track_conversation_event,
)

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/analytics")


class AnalyticsOverview(BaseModel):
    total_conversations: int
    active_conversations: int
    resolved_conversations: int
    resolution_rate: float
    avg_response_time_ms: float
    sentiment_positive: int
    sentiment_neutral: int
    sentiment_negative: int
    total_tokens: int
    total_cost: float


@router.get("/overview")
async def get_analytics_overview(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get analytics overview for the current tenant."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    conv_metrics = await get_conversation_metrics(db_pool, tenant_id, days)
    cost_metrics = await get_cost_metrics(db_pool, tenant_id, "month")

    resolution_rate = (
        conv_metrics.resolved_conversations / conv_metrics.total_conversations * 100
        if conv_metrics.total_conversations > 0
        else 0.0
    )

    return AnalyticsOverview(
        total_conversations=conv_metrics.total_conversations,
        active_conversations=conv_metrics.active_conversations,
        resolved_conversations=conv_metrics.resolved_conversations,
        resolution_rate=round(resolution_rate, 2),
        avg_response_time_ms=round(conv_metrics.avg_response_time_ms, 2),
        sentiment_positive=conv_metrics.sentiment_positive,
        sentiment_neutral=conv_metrics.sentiment_neutral,
        sentiment_negative=conv_metrics.sentiment_negative,
        total_tokens=cost_metrics.total_tokens,
        total_cost=round(cost_metrics.total_cost, 4),
    )


@router.get("/conversations")
async def get_conversation_analytics(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get detailed conversation analytics."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    metrics = await get_conversation_metrics(db_pool, tenant_id, days)

    return {
        "period_days": days,
        "total_conversations": metrics.total_conversations,
        "active_conversations": metrics.active_conversations,
        "resolved_conversations": metrics.resolved_conversations,
        "avg_response_time_ms": round(metrics.avg_response_time_ms, 2),
        "avg_messages_per_conversation": round(metrics.avg_messages_per_conversation, 2),
        "sentiment": {
            "positive": metrics.sentiment_positive,
            "neutral": metrics.sentiment_neutral,
            "negative": metrics.sentiment_negative,
        },
    }


@router.get("/costs")
async def get_cost_analytics(
    request: Request,
    period: str = Query(default="month", pattern="^(day|week|month)$"),
):
    """Get cost analytics."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    metrics = await get_cost_metrics(db_pool, tenant_id, period)

    return {
        "period": period,
        "total_tokens": metrics.total_tokens,
        "total_messages": metrics.total_messages,
        "total_cost": round(metrics.total_cost, 4),
        "avg_cost_per_conversation": round(metrics.avg_cost_per_conversation, 4),
    }


@router.post("/track")
async def track_event(
    request: Request,
    event_type: str,
    metadata: dict | None = None,
):
    """Track a custom analytics event."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    await track_conversation_event(db_pool, tenant_id, event_type, metadata)

    return {"tracked": True}