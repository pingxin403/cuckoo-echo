"""Feedback service for user feedback loop (👍/👎)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import structlog

from ai_gateway.langfuse_handler import get_langfuse_handler
from shared.config import get_settings
from shared.db import tenant_db_context
from shared.redis_client import get_redis

log = structlog.get_logger()


async def store_feedback(
    db_pool,
    thread_id: str,
    message_id: str,
    user_id: str,
    tenant_id: str,
    feedback_type: str,
) -> Optional[str]:
    """Store or update feedback for a message.
    
    Implements upsert logic: if feedback already exists for the same
    (thread_id, message_id, user_id, tenant_id), update the feedback_type.
    If the same feedback_type is provided, return None to indicate toggle-off.
    
    Args:
        db_pool: AsyncPG connection pool
        thread_id: Thread identifier
        message_id: Message identifier
        user_id: User identifier
        tenant_id: Tenant identifier
        feedback_type: "thumbs_up" or "thumbs_down"
    
    Returns:
        The feedback_state after operation, or None if feedback was removed (toggle-off)
    """
    partition_key = f"tenant_{tenant_id}"
    
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            # Check if feedback already exists
            existing = await conn.fetchrow(
                """
                SELECT id, feedback_type, created_at
                FROM feedback
                WHERE thread_id = $1
                  AND message_id = $2
                  AND user_id = $3
                  AND tenant_id = $4
                """,
                uuid.UUID(thread_id),
                uuid.UUID(message_id),
                uuid.UUID(user_id),
                uuid.UUID(tenant_id),
            )
            
            if existing:
                # If same feedback_type, toggle off (remove feedback)
                if existing["feedback_type"] == feedback_type:
                    await conn.execute(
                        """
                        DELETE FROM feedback
                        WHERE id = $1
                        """,
                        existing["id"],
                    )
                    log.info(
                        "feedback_toggled_off",
                        thread_id=thread_id,
                        message_id=message_id,
                        user_id=user_id,
                    )
                    
                    # Invalidate cache
                    await _invalidate_feedback_cache(tenant_id, thread_id, message_id)
                    
                    return None
                
                # Otherwise, update the feedback_type
                await conn.execute(
                    """
                    UPDATE feedback
                    SET feedback_type = $1,
                        updated_at = NOW(),
                        langfuse_trace_id = NULL,
                        langfuse_span_id = NULL
                    WHERE id = $2
                    """,
                    feedback_type,
                    existing["id"],
                )
                log.info(
                    "feedback_updated",
                    thread_id=thread_id,
                    message_id=message_id,
                    user_id=user_id,
                    feedback_type=feedback_type,
                )
            else:
                # Insert new feedback
                await conn.execute(
                    """
                    INSERT INTO feedback 
                    (thread_id, message_id, user_id, tenant_id, feedback_type, 
                     partition_key, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    """,
                    uuid.UUID(thread_id),
                    uuid.UUID(message_id),
                    uuid.UUID(user_id),
                    uuid.UUID(tenant_id),
                    feedback_type,
                    partition_key,
                )
                log.info(
                    "feedback_stored",
                    thread_id=thread_id,
                    message_id=message_id,
                    user_id=user_id,
                    feedback_type=feedback_type,
                )
    
    # Invalidate cache
    await _invalidate_feedback_cache(tenant_id, thread_id, message_id)
    
    return feedback_type


async def get_feedback_state(
    db_pool,
    thread_id: str,
    message_id: str,
    user_id: str,
    tenant_id: str,
) -> Optional[str]:
    """Get the current feedback state for a message.
    
    Args:
        db_pool: AsyncPG connection pool
        thread_id: Thread identifier
        message_id: Message identifier
        user_id: User identifier
        tenant_id: Tenant identifier
    
    Returns:
        "thumbs_up", "thumbs_down", or None if no feedback exists
    """
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            result = await conn.fetchrow(
                """
                SELECT feedback_type
                FROM feedback
                WHERE thread_id = $1
                  AND message_id = $2
                  AND user_id = $3
                  AND tenant_id = $4
                """,
                uuid.UUID(thread_id),
                uuid.UUID(message_id),
                uuid.UUID(user_id),
                uuid.UUID(tenant_id),
            )
            
            if result:
                return result["feedback_type"]
            return None


async def get_feedback_stats(
    db_pool,
    tenant_id: str,
    thread_id: Optional[str] = None,
    message_id: Optional[str] = None,
) -> dict:
    """Get feedback statistics for a scope.
    
    Args:
        db_pool: AsyncPG connection pool
        tenant_id: Tenant identifier
        thread_id: Optional thread identifier to filter
        message_id: Optional message identifier to filter
    
    Returns:
        Dictionary with total, thumbs_up, thumbs_down, and percentages
    """
    # Try to get from cache first
    redis = get_redis()
    if redis:
        cache_key = _build_cache_key(tenant_id, thread_id, message_id)
        cached = await redis.get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                log.debug(
                    "feedback_stats_cache_hit",
                    cache_key=cache_key,
                )
                return cached_data
            except json.JSONDecodeError:
                log.warning(
                    "feedback_stats_cache_invalid",
                    cache_key=cache_key,
                )
    
    # Cache miss - query database
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            # Build query with optional filters
            where_clauses = ["tenant_id = $1"]
            params = [uuid.UUID(tenant_id)]
            
            if thread_id:
                where_clauses.append("thread_id = $" + str(len(params) + 1))
                params.append(uuid.UUID(thread_id))
            
            if message_id:
                where_clauses.append("message_id = $" + str(len(params) + 1))
                params.append(uuid.UUID(message_id))
            
            where_clause = " AND ".join(where_clauses)
            
            # Get counts
            result = await conn.fetchrow(
                f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE feedback_type = 'thumbs_up') as thumbs_up,
                    COUNT(*) FILTER (WHERE feedback_type = 'thumbs_down') as thumbs_down
                FROM feedback
                WHERE {where_clause}
                """,
                *params,
            )
            
            total = result["total"] or 0
            thumbs_up = result["thumbs_up"] or 0
            thumbs_down = result["thumbs_down"] or 0
            
            # Calculate percentages
            thumbs_up_percentage = None
            thumbs_down_percentage = None
            
            if total > 0:
                thumbs_up_percentage = round((thumbs_up / total) * 100, 2)
                thumbs_down_percentage = round((thumbs_down / total) * 100, 2)
            
            stats = {
                "total": total,
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "thumbs_up_percentage": thumbs_up_percentage,
                "thumbs_down_percentage": thumbs_down_percentage,
            }
            
            # Cache the result for 60 seconds
            if redis:
                cache_key = _build_cache_key(tenant_id, thread_id, message_id)
                await redis.setex(
                    cache_key,
                    60,  # TTL: 60 seconds
                    json.dumps(stats),
                )
                log.debug(
                    "feedback_stats_cache_set",
                    cache_key=cache_key,
                    ttl=60,
                )
            
            return stats


def _build_cache_key(tenant_id: str, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> str:
    """Build Redis cache key for feedback statistics."""
    if thread_id and message_id:
        return f"feedback:stats:{tenant_id}:{thread_id}:{message_id}"
    elif thread_id:
        return f"feedback:stats:{tenant_id}:{thread_id}"
    else:
        return f"feedback:stats:{tenant_id}"


async def _invalidate_feedback_cache(tenant_id: str, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> None:
    """Invalidate Redis cache for feedback statistics."""
    redis = get_redis()
    if not redis:
        return
    
    # Invalidate specific cache key
    cache_key = _build_cache_key(tenant_id, thread_id, message_id)
    try:
        await redis.delete(cache_key)
        log.debug(
            "feedback_stats_cache_invalidated",
            cache_key=cache_key,
        )
    except Exception as e:
        log.warning(
            "feedback_stats_cache_invalidate_failed",
            cache_key=cache_key,
            error=str(e),
        )


async def send_feedback_to_langfuse(
    thread_id: str,
    message_id: str,
    feedback_type: str,
    prompt: str,
    response: str,
    metadata: Optional[dict] = None,
) -> None:
    """Send feedback event to Langfuse asynchronously.
    
    This is a fire-and-forget operation that does not block the response.
    If Langfuse is unavailable, logs the error but continues processing.
    
    Args:
        thread_id: Thread identifier for metadata
        message_id: Message identifier for metadata
        feedback_type: "thumbs_up" or "thumbs_down"
        prompt: Original prompt that generated the response
        response: LLM response that was rated
        metadata: Additional metadata to include
    """
    settings = get_settings()
    
    # Check if Langfuse is configured
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        log.debug("langfuse_not_configured", skip_feedback_event=True)
        return
    
    # Build metadata
    event_metadata = metadata or {}
    event_metadata["thread_id"] = thread_id
    event_metadata["message_id"] = message_id
    
    # Get Langfuse handler
    langfuse = get_langfuse_handler()
    
    if langfuse is None:
        log.debug("langfuse_handler_unavailable", skip_feedback_event=True)
        return
    
    try:
        # Send feedback event asynchronously (non-blocking)
        asyncio.create_task(
            _send_langfuse_feedback_async(
                langfuse, feedback_type, prompt, response, event_metadata
            )
        )
        log.info(
            "langfuse_feedback_event_sent",
            thread_id=thread_id,
            message_id=message_id,
            feedback_type=feedback_type,
        )
    except Exception as e:
        log.error(
            "langfuse_feedback_event_failed",
            thread_id=thread_id,
            message_id=message_id,
            error=str(e),
            hint="Feedback recorded but not sent to Langfuse",
        )


async def _send_langfuse_feedback_async(
    langfuse,
    feedback_type: str,
    prompt: str,
    response: str,
    metadata: dict,
) -> None:
    """Internal async function to send feedback to Langfuse.
    
    This function is called in a separate task to avoid blocking.
    """
    try:
        # Create a new trace for the feedback event
        trace = langfuse.trace(
            name="user_feedback",
            metadata=metadata,
        )
        
        # Create a span for the feedback
        span = trace.span(
            name="feedback_event",
            input={
                "prompt": prompt,
                "response": response,
                "feedback_type": feedback_type,
            },
            metadata=metadata,
        )
        
        # End the span
        span.end()
        
        log.debug(
            "langfuse_feedback_trace_created",
            feedback_type=feedback_type,
        )
    except Exception as e:
        log.error(
            "langfuse_feedback_async_failed",
            error=str(e),
            hint="Failed to send feedback to Langfuse",
        )
