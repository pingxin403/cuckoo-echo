"""Billing service for token and multimodal credit tracking."""

from __future__ import annotations

import math

import structlog

from shared.db import tenant_db_context

log = structlog.get_logger()

AUDIO_CREDIT_RATE = 0.1  # credits per 15-second chunk
IMAGE_CREDIT_RATES = {"sd": 0.5, "hd": 1.0, "4k": 2.0}  # by resolution tier


def calculate_audio_credits(audio_seconds: float) -> float:
    """Calculate audio credits: ceil(seconds/15) * rate."""
    if audio_seconds <= 0:
        return 0.0
    chunks = math.ceil(audio_seconds / 15)
    return chunks * AUDIO_CREDIT_RATE


def calculate_image_credits(resolution_tier: str = "sd") -> float:
    """Calculate image credits by resolution tier."""
    return IMAGE_CREDIT_RATES.get(resolution_tier, IMAGE_CREDIT_RATES["sd"])


async def record_usage(
    thread_id: str,
    tenant_id: str,
    tokens_used: int,
    db_pool=None,
    audio_seconds: float = 0.0,
    image_count: int = 0,
    image_resolution: str = "sd",
) -> None:
    """Record token usage and multimodal credits for billing.

    Updates the latest assistant message in the thread with token count.
    Also records multimodal credits if applicable.
    """
    # Calculate multimodal credits
    audio_credits = calculate_audio_credits(audio_seconds)
    image_credits = calculate_image_credits(image_resolution) * image_count
    total_credits = audio_credits + image_credits

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
        audio_credits=audio_credits,
        image_count=image_count,
        image_credits=image_credits,
        total_credits=total_credits,
    )
