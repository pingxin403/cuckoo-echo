"""Chat service SSE streaming endpoint.

Implements the core SSE event generator with Redis distributed lock
protection and the HTTP endpoints for chat completions and thread history.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import orjson
import structlog
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from shared.db import lock_key

log = structlog.get_logger()

router = APIRouter()

LOCK_TTL = 90  # seconds, covers longest LLM generation


async def event_generator(
    thread_id: str,
    tenant_id: str,
    user_id: str,
    payload: dict,
    agent,
    redis,
    billing_service=None,
):
    """SSE event generator with Redis lock protection.

    Lock is acquired INSIDE the generator because FastAPI returns
    EventSourceResponse before the generator starts executing —
    acquiring in the endpoint's context manager would release the lock
    before any tokens are generated.
    """
    key = lock_key(thread_id)
    lock = redis.lock(key, timeout=LOCK_TTL)
    acquired = await lock.acquire(blocking=False)

    if not acquired:
        yield orjson.dumps(
            {"error": "CONCURRENT_REQUEST", "message": "AI is still processing"}
        ).decode()
        return

    tokens_used = 0
    interrupted = False
    queue: asyncio.Queue = asyncio.Queue()

    async def _consume_stream():
        """Consume agent stream in a shielded task so client disconnect
        does not cancel the LLM network IO."""
        nonlocal tokens_used
        config = {"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}}
        async for chunk in agent.astream_events(payload, config=config, version="v2"):
            if chunk["event"] == "on_chat_model_stream":
                token = chunk["data"]["chunk"].content
                if token:
                    await queue.put(orjson.dumps({"content": token}).decode())
            elif chunk["event"] == "on_llm_end":
                usage = chunk["data"].get("output", {}).get("usage_metadata", {})
                tokens_used = (
                    usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                )
        await queue.put(None)  # sentinel

    try:
        task = asyncio.ensure_future(asyncio.shield(_consume_stream()))
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
        # Ensure the shielded task completes
        await task
        yield "[DONE]"
    except asyncio.CancelledError:
        interrupted = True
        log.warning("client_disconnected", thread_id=thread_id)
        raise
    finally:
        try:
            await lock.release()
        except Exception:
            log.warning("lock_release_failed", thread_id=thread_id)

        if tokens_used > 0 and billing_service:
            try:
                await billing_service.record_usage(thread_id, tenant_id, tokens_used)
            except Exception:
                log.error("billing_record_failed", thread_id=thread_id)


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """SSE streaming chat endpoint."""
    body = await request.json()
    thread_id = body.get("thread_id", str(uuid4()))
    user_id = body.get("user_id", "anonymous")
    tenant_id = request.state.tenant_id

    agent = request.app.state.agent
    redis = request.app.state.redis
    billing = getattr(request.app.state, "billing_service", None)

    return EventSourceResponse(
        event_generator(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            payload={"messages": body.get("messages", [])},
            agent=agent,
            redis=redis,
            billing_service=billing,
        ),
        ping=15,
    )


@router.get("/v1/threads/{thread_id}")
async def get_thread_history(thread_id: str, request: Request):
    """Fetch conversation history via AsyncPostgresSaver."""
    checkpointer = request.app.state.checkpointer
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint = await checkpointer.aget(config)
    if not checkpoint:
        return {"thread_id": thread_id, "messages": []}
    state = checkpoint.get("channel_values", {})
    return {
        "thread_id": thread_id,
        "messages": state.get("messages", []),
    }
