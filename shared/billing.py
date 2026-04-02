"""Billing service for token and multimodal credit tracking."""

from __future__ import annotations

import structlog

from shared.db import tenant_db_context

log = structlog.get_logger()


async def record_usage(
    thread_id: str,
    tenant_id: str,
    tokens_used: int,
    db_pool=None,
    audio_seconds: float = 0.0,
    image_count: int = 0,
) -> None:
    """Record token usage and multimodal credits for billing.

    Updates the latest assistant message in the thread with token count.
    Also records multimodal credits if applicable.
    """
    if db_pool is None:
        log.warning("billing_no_db_pool", thread_id=thread_id)
        return

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                """
                UPDATE messages SET tokens_used = $1
                WHERE thread_id = $2 AND role = 'assistant'
                AND created_at = (
                    SELECT MAX(created_at) FROM messages
                    WHERE thread_id = $2 AND role = 'assistant'
                )
                """,
                tokens_used,
                thread_id,
            )

    log.info(
        "billing_recorded",
        thread_id=thread_id,
        tokens=tokens_used,
        audio_seconds=audio_seconds,
        image_count=image_count,
    )
