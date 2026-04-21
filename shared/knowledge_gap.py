"""Knowledge gap detection and recommendation service."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

log = structlog.get_logger()


@dataclass
class KnowledgeGap:
    """Represents a knowledge gap - query pattern without matching knowledge."""
    id: str
    query: str
    frequency: int
    first_seen: datetime
    last_seen: datetime
    suggested_title: Optional[str] = None


async def track_gap(
    db_pool,
    tenant_id: str,
    query: str,
    response_context: Optional[str] = None,
) -> None:
    """Track a query that didn't find good RAG results.
    
    In production, call this when RAG confidence is below threshold.
    """
    if not query or len(query) < 3:
        return
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO knowledge_gaps (tenant_id, query, frequency, response_context)
            VALUES ($1, $2, 1, $3)
            ON CONFLICT (tenant_id, query) DO UPDATE SET
                frequency = knowledge_gaps.frequency + 1,
                last_seen = NOW()
            """,
            tenant_id,
            query[:500],
            response_context[:2000] if response_context else None,
        )
    
    log.info("knowledge_gap_tracked", tenant_id=tenant_id, query=query[:50])


async def get_top_gaps(
    db_pool,
    tenant_id: str,
    limit: int = 20,
) -> list[KnowledgeGap]:
    """Get top knowledge gaps for a tenant."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, query, frequency, first_seen, last_seen, suggested_title
            FROM knowledge_gaps
            WHERE tenant_id = $1
            ORDER BY frequency DESC
            LIMIT $2
            """,
            tenant_id,
            limit,
        )
    
    return [
        KnowledgeGap(
            id=str(r["id"]),
            query=r["query"],
            frequency=r["frequency"],
            first_seen=r["first_seen"],
            last_seen=r["last_seen"],
            suggested_title=r["suggested_title"],
        )
        for r in rows
    ]


async def dismiss_gap(
    db_pool,
    gap_id: str,
) -> None:
    """Dismiss a knowledge gap (mark as resolved)."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM knowledge_gaps WHERE id = $1",
            gap_id,
        )
    log.info("knowledge_gap_dismissed", gap_id=gap_id)


def generate_title_suggestion(query: str, frequency: int) -> str:
    """Generate a suggested article title from query pattern."""
    words = query.split()
    if len(words) > 6:
        title = " ".join(words[:6]) + "..."
    else:
        title = query
    
    if frequency > 1:
        title += f" ({frequency} queries)"
    
    return title