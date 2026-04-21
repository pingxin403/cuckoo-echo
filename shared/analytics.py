"""Analytics service for conversation and business metrics."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

log = structlog.get_logger()


@dataclass
class ConversationMetrics:
    """Metrics for a conversation."""
    tenant_id: str
    total_conversations: int
    active_conversations: int
    resolved_conversations: int
    avg_response_time_ms: float
    avg_messages_per_conversation: float
    sentiment_positive: int
    sentiment_neutral: int
    sentiment_negative: int


@dataclass
class AgentMetrics:
    """Metrics for agent performance."""
    tenant_id: str
    agent_type: str
    total_conversations: int
    escalated_conversations: int
    avg_handling_time_ms: float
    hitl_takeover_count: int


@dataclass
class CostMetrics:
    """Cost-related metrics."""
    tenant_id: str
    period: str
    total_tokens: int
    total_messages: int
    total_cost: float
    avg_cost_per_conversation: float


async def track_conversation_event(
    db_pool,
    tenant_id: str,
    event_type: str,
    metadata: Optional[dict] = None,
) -> None:
    """Track a conversation event for analytics."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO analytics_events (tenant_id, event_type, metadata)
            VALUES ($1, $2, $3)
            """,
            tenant_id,
            event_type,
            metadata,
        )
    log.info("analytics_event_tracked", tenant_id=tenant_id, event_type=event_type)


async def get_conversation_metrics(
    db_pool,
    tenant_id: str,
    days: int = 30,
) -> ConversationMetrics:
    """Get conversation metrics for a tenant."""
    start_date = datetime.now() - timedelta(days=days)

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as total_conversations,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_conversations,
                COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_conversations,
                AVG(EXTRACT(EPOCH FROM (ended_at - started_at)) * 1000) as avg_response_time_ms,
                AVG(message_count) as avg_messages_per_conversation
            FROM conversations
            WHERE tenant_id = $1 AND started_at > $2
            """,
            tenant_id,
            start_date,
        )

        sentiment = await conn.fetchrow(
            """
            SELECT
                COUNT(CASE WHEN sentiment > 0.3 THEN 1 END) as positive,
                COUNT(CASE WHEN sentiment BETWEEN -0.3 AND 0.3 THEN 1 END) as neutral,
                COUNT(CASE WHEN sentiment < -0.3 THEN 1 END) as negative
            FROM conversations
            WHERE tenant_id = $1 AND started_at > $2
            """,
            tenant_id,
            start_date,
        )

    return ConversationMetrics(
        tenant_id=tenant_id,
        total_conversations=row["total_conversations"] or 0,
        active_conversations=row["active_conversations"] or 0,
        resolved_conversations=row["resolved_conversations"] or 0,
        avg_response_time_ms=row["avg_response_time_ms"] or 0.0,
        avg_messages_per_conversation=row["avg_messages_per_conversation"] or 0.0,
        sentiment_positive=sentiment["positive"] or 0,
        sentiment_neutral=sentiment["neutral"] or 0,
        sentiment_negative=sentiment["negative"] or 0,
    )


async def get_cost_metrics(
    db_pool,
    tenant_id: str,
    period: str = "month",
) -> CostMetrics:
    """Get cost metrics for a tenant."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(tokens_used), 0) as total_tokens,
                COUNT(*) as total_messages,
                COALESCE(SUM(tokens_used), 0) * 0.001 as total_cost
            FROM messages
            WHERE tenant_id = $1
            AND created_at > NOW() - INTERVAL '1 month'
            """,
            tenant_id,
        )

        total_conversations = await conn.fetchval(
            """
            SELECT COUNT(*) FROM conversations
            WHERE tenant_id = $1
            AND started_at > NOW() - INTERVAL '1 month'
            """,
            tenant_id,
        )

    avg_cost = row["total_cost"] / total_conversations if total_conversations > 0 else 0.0

    return CostMetrics(
        tenant_id=tenant_id,
        period=period,
        total_tokens=row["total_tokens"] or 0,
        total_messages=row["total_messages"] or 0,
        total_cost=row["total_cost"] or 0.0,
        avg_cost_per_conversation=avg_cost,
    )


async def aggregate_daily_metrics(db_pool, tenant_id: str) -> None:
    """Aggregate daily metrics from events."""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO daily_aggregates (tenant_id, date, conversation_count, message_count, token_count)
            SELECT
                tenant_id,
                $1 as date,
                COUNT(DISTINCT thread_id) as conversation_count,
                COUNT(*) as message_count,
                COALESCE(SUM(tokens_used), 0) as token_count
            FROM messages
            WHERE tenant_id = $2
            AND created_at >= $3 AND created_at < $4
            GROUP BY tenant_id
            ON CONFLICT (tenant_id, date) DO UPDATE SET
                conversation_count = EXCLUDED.conversation_count,
                message_count = EXCLUDED.message_count,
                token_count = EXCLUDED.token_count
            """,
            date_str,
            tenant_id,
            yesterday.replace(hour=0, minute=0, second=0),
            yesterday.replace(hour=23, minute=59, second=59),
        )

    log.info("daily_metrics_aggregated", tenant_id=tenant_id, date=date_str)