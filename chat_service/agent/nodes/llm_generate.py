"""LLM Generate node — calls AI Gateway for streaming completion with citations."""
from __future__ import annotations

import structlog

from ai_gateway.client import stream_chat_completion
from chat_service.agent.state import AgentState
from shared.citation import format_inline_citations, create_source_card

log = structlog.get_logger()

# Module-level placeholder for tenant LLM config loader
db_pool = None


async def llm_generate_node(state: AgentState) -> AgentState:
    """Generate LLM response using AI Gateway with tenant config."""
    messages = state.get("messages", [])
    tenant_id = state.get("tenant_id", "")
    rag_context = state.get("rag_context", [])
    tool_calls = state.get("tool_calls", [])

    # Build LLM messages
    llm_messages = []

    # System prompt (from tenant config or default)
    llm_messages.append({"role": "system", "content": "You are a helpful customer service assistant."})

    # Add RAG context with citations if available
    sources = state.get("sources", [])
    if rag_context:
        context_text = "\n\n".join(rag_context)
        citation_text = format_inline_citations(sources) if sources else ""
        context_with_citation = f"Reference information:\n{context_text}"
        if citation_text:
            context_with_citation += f"\n\nSources: {citation_text}"
        llm_messages.append({"role": "system", "content": context_with_citation})

    # Add tool results if available
    if tool_calls:
        last_tool = tool_calls[-1]
        llm_messages.append({"role": "system", "content": f"Tool result: {last_tool.get('result', {})}"})

    # Add conversation history (last 10 messages for context window)
    for msg in messages[-10:]:
        llm_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    # Get tenant LLM config
    tenant_config = None
    if db_pool and tenant_id:
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT llm_config FROM tenants WHERE id = $1", tenant_id)
                if row:
                    import orjson
                    raw = row["llm_config"]
                    tenant_config = orjson.loads(raw) if isinstance(raw, (str, bytes)) else raw
        except Exception as e:
            log.warning("tenant_config_load_failed", error=str(e))

    # Call LLM
    try:
        # Get the token streaming queue from config (if available)
        # This allows the event_generator to push tokens to SSE in real-time
        token_queue = None
        if hasattr(stream_chat_completion, '_token_queue'):
            token_queue = stream_chat_completion._token_queue

        response_stream = await stream_chat_completion(
            messages=llm_messages,
            tenant_llm_config=tenant_config,
            thread_id=state.get("thread_id"),
        )
        # Collect full response while also pushing tokens to queue
        full_response = ""
        tokens_used = 0
        async for chunk in response_stream:
            if hasattr(chunk, "choices") and chunk.choices:
                delta = chunk.choices[0].delta
                if delta:
                    content = getattr(delta, "content", None) or ""
                    if not content:
                        extra = getattr(delta, "additional_kwargs", None) or {}
                        content = extra.get("reasoning_content", "")
                    if content:
                        full_response += content
                        # Push token to SSE queue for real-time streaming
                        if token_queue:
                            try:
                                token_queue.put_nowait(content)
                            except Exception:
                                pass
            if hasattr(chunk, "usage") and chunk.usage:
                tokens_used = getattr(chunk.usage, "total_tokens", 0)

        # Cache the response for RAG queries (semantic cache)
        if rag_context and full_response:
            try:
                from shared.semantic_cache import cache_store
                query = messages[-1].get("content", "") if messages else ""
                if query:
                    await cache_store(query, full_response, tenant_id)
            except Exception as cache_err:
                log.warning("semantic_cache_store_skipped", error=str(cache_err))

        source_card = create_source_card(sources) if sources else None
        return {
            **state,
            "llm_response": full_response,
            "tokens_used": tokens_used,
            "guardrails_passed": True,
            "citations": [s.to_dict() for s in sources] if sources else [],
        }
    except Exception as e:
        log.error("llm_generate_failed", error=str(e))
        return {
            **state,
            "llm_response": "抱歉，系统暂时无法处理您的请求，请稍后重试。",
            "guardrails_passed": True,
            "citations": [],
        }
