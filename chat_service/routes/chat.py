"""Chat service SSE streaming endpoint.

Implements the core SSE event generator with Redis distributed lock
protection and the HTTP endpoints for chat completions and thread history.

Streaming approach: Uses LangGraph ``agent.astream()`` which yields
incremental state updates.  The ``llm_response`` field produced by the
``llm_generate`` node contains the full assistant reply.  We push it as
a single SSE content chunk followed by ``[DONE]``.

Previous implementation used ``astream_events(version="v2")`` and listened
for ``on_chat_model_stream`` events, but those events are only emitted
when a *LangChain* ChatModel is invoked inside the graph.  Because the
LLM call goes through ``litellm.acompletion()`` (not a LangChain model),
no ``on_chat_model_stream`` events were ever fired — resulting in
``ping`` + ``[DONE]`` with zero token content.
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

    Uses ``agent.astream()`` to receive incremental state diffs from
    each graph node.  When the ``llm_response`` key appears (from the
    ``llm_generate`` node) we push it as SSE content.  A ``correction_message``
    from the guardrails/postprocess nodes is also forwarded if present.
    """
    key = lock_key(thread_id)
    lock = redis.lock(key, timeout=LOCK_TTL)
    acquired = await lock.acquire(blocking=False)

    if not acquired:
        yield orjson.dumps({"error": "CONCURRENT_REQUEST", "message": "AI is still processing"}).decode()
        return

    tokens_used = 0
    queue: asyncio.Queue = asyncio.Queue()

    async def _consume_stream():
        """Consume agent state updates in a shielded task so client
        disconnect does not cancel the LLM network IO.

        Sets up a token queue on the stream_chat_completion function
        so llm_generate_node can push tokens for real-time SSE streaming.
        After the graph completes, any remaining llm_response is pushed
        as a fallback (for non-streaming scenarios like tool calls).
        """
        nonlocal tokens_used
        config = {"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}}

        # Attach token queue to stream_chat_completion for real-time token push
        from ai_gateway.client import stream_chat_completion

        stream_chat_completion._token_queue = queue
        tokens_pushed_via_queue = False

        response_sent = False
        try:
            async for state_update in agent.astream(payload, config=config, stream_mode="updates"):
                log.debug(
                    "astream_state_update",
                    thread_id=thread_id,
                    node=list(state_update.keys()),
                    keys={
                        k: list(v.keys()) if isinstance(v, dict) else type(v).__name__ for k, v in state_update.items()
                    },
                )

                for node_name, diff in state_update.items():
                    if not isinstance(diff, dict):
                        continue

                    # If llm_generate pushed tokens via queue, mark as sent
                    # For non-LLM nodes (like hitl_node), push the full response
                    llm_response = diff.get("llm_response")
                    if llm_response and not response_sent:
                        # Check if tokens were already pushed per-token via the queue
                        tokens_pushed_via_queue = not queue.empty() or node_name == "llm_generate"
                        if not tokens_pushed_via_queue:
                            # Non-streaming node (HITL, error) — push full response
                            log.info(
                                "sse_pushing_llm_response",
                                thread_id=thread_id,
                                node=node_name,
                                length=len(llm_response),
                            )
                            await queue.put(orjson.dumps({"content": llm_response}).decode())
                        response_sent = True

                    correction = diff.get("correction_message")
                    if correction:
                        log.info("sse_pushing_correction", thread_id=thread_id, node=node_name)
                        await queue.put(orjson.dumps({"content": correction}).decode())

                    used = diff.get("tokens_used", 0)
                    if used:
                        tokens_used = used

        except Exception as exc:
            log.error("astream_error", thread_id=thread_id, error=str(exc))
            if not response_sent:
                await queue.put(orjson.dumps({"content": "抱歉，系统暂时无法处理您的请求，请稍后重试。"}).decode())
        finally:
            # Clean up the token queue reference
            stream_chat_completion._token_queue = None
            await queue.put(None)  # sentinel

    try:
        task = asyncio.ensure_future(asyncio.shield(_consume_stream()))
        while True:
            item = await queue.get()
            if item is None:
                break
            # If item is a raw token string (from llm_generate per-token push),
            # wrap it in SSE JSON format
            if isinstance(item, str) and not item.startswith("{"):
                yield orjson.dumps({"content": item}).decode()
            else:
                yield item
        # Ensure the shielded task completes
        await task
        yield "[DONE]"

    except asyncio.CancelledError:
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
            payload={"messages": body.get("messages", []), "tenant_id": tenant_id, "thread_id": thread_id},
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
    messages = state.get("messages", [])

    # Get tenant_id and user_id from request.state
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    # If no user_id, return messages without feedback_state
    if not user_id:
        return {
            "thread_id": thread_id,
            "messages": messages,
        }

    # Get feedback service from app.state
    feedback_service = getattr(request.app.state, "feedback_service", None)
    if feedback_service is None:
        return {
            "thread_id": thread_id,
            "messages": messages,
        }

    # Add feedback_state to each message
    import chat_service.services.feedback as feedback_mod

    db_pool = request.app.state.db_pool

    enriched_messages = []
    for msg in messages:
        msg_id = msg.get("id") or msg.get("additional_kwargs", {}).get("id")
        if msg_id and tenant_id:
            feedback_state = await feedback_mod.get_feedback_state(
                db_pool=db_pool,
                thread_id=thread_id,
                message_id=str(msg_id),
                user_id=user_id,
                tenant_id=tenant_id,
            )
            # Create a copy with feedback_state
            enriched_msg = dict(msg)
            enriched_msg["feedback_state"] = feedback_state
            enriched_messages.append(enriched_msg)
        else:
            enriched_messages.append(msg)

    return {
        "thread_id": thread_id,
        "messages": enriched_messages,
    }
