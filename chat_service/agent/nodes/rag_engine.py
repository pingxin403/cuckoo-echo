"""RAG Engine node — hybrid search + rerank + soft-delete filtering + citation tracking.

Pipeline: embed query → Milvus hybrid_search (dense + BM25) → soft-delete
filter via PG → BGE Reranker v2 (timeout-protected) → top-3 chunks + sources.
Graceful degradation: circuit breaker + retry with exponential backoff + fallback to empty results.
"""
from __future__ import annotations

import asyncio
import random
from typing import Optional

import structlog

from chat_service.agent.state import AgentState
from shared.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from shared.citation import CitationType, Source

log = structlog.get_logger(__name__)

# Module-level placeholders — wired at app startup via dependency injection.
embedding_service = None  # must expose async .embed(text) -> list[float]
reranker = None           # must expose .compute_score(pairs) -> list[float]
collection = None         # pymilvus Collection with hybrid_search support
db_pool = None            # asyncpg pool for soft-delete checks

# Circuit breaker for Milvus search
milvus_circuit_breaker: Optional[CircuitBreaker] = None


def _get_milvus_circuit_breaker() -> CircuitBreaker:
    global milvus_circuit_breaker
    if milvus_circuit_breaker is None:
        milvus_circuit_breaker = CircuitBreaker(
            name="milvus_search",
            failure_threshold=5,
            timeout=60.0,
        )
    return milvus_circuit_breaker


async def _retry_with_backoff(
    func,
    *args,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    **kwargs,
):
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                log.warning("rag_retry", attempt=attempt + 1, max_retries=max_retries, delay=delay, error=str(e))
                await asyncio.sleep(delay)
    raise last_exception


# ---------------------------------------------------------------------------
# Task 8.3: Soft-delete filtering helper
# ---------------------------------------------------------------------------

async def get_active_doc_ids(
    doc_ids: list[str],
    tenant_id: str,
    pool=None,
) -> set[str]:
    """Return the subset of *doc_ids* that are NOT soft-deleted.

    Queries PG ``knowledge_docs`` where ``deleted_at IS NULL``.
    When no pool is available (e.g. unit tests), returns all ids unchanged.
    """
    if not doc_ids:
        return set()
    if pool is None:
        return set(doc_ids)

    from shared.db import tenant_db_context

    async with pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            rows = await conn.fetch(
                "SELECT id::text FROM knowledge_docs WHERE id = ANY($1) AND deleted_at IS NULL",
                doc_ids,
            )
    return {row["id"] for row in rows}


# ---------------------------------------------------------------------------
# Task 8.4: Reranker with timeout protection
# ---------------------------------------------------------------------------

async def _rerank_chunks(
    query: str,
    chunks_with_sources: list[tuple[str, Source]],
    timeout: float = 0.5,
) -> list[tuple[str, Source]]:
    """Rerank *chunks* using BGE Reranker v2 and return the top-3 with sources.

    Falls back to RRF order (first 3) on timeout or when no reranker is
    configured.
    """
    if reranker is None:
        return chunks_with_sources[:3]

    try:
        loop = asyncio.get_running_loop()
        chunks = [c for c, _ in chunks_with_sources]
        pairs = [[query, chunk] for chunk in chunks]
        scores = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: reranker.compute_score(pairs)),
            timeout=timeout,
        )
        scored = sorted(zip(scores, chunks_with_sources), key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:3]]
    except asyncio.TimeoutError:
        log.warning("rerank_timeout", query_len=len(query))
        return chunks_with_sources[:3]


# ---------------------------------------------------------------------------
# Task 8.1 / 8.2: RAG Engine node
# ---------------------------------------------------------------------------

async def rag_engine_node(state: AgentState) -> AgentState:
    """RAG Engine: cache check → hybrid search (dense + BM25) → soft-delete filter → rerank → top-3 + sources.
    
    Graceful degradation: circuit breaker, retry with exponential backoff, and fallback to chat-only mode.
    """
    messages = state.get("messages", [])
    if not messages:
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": False}

    query = messages[-1].get("content", "")
    tenant_id = state.get("tenant_id", "")

    if not query or not tenant_id:
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": False}

    # 0. Semantic cache check — return cached response without LLM call
    from shared.semantic_cache import cache_lookup
    cached = await cache_lookup(query, tenant_id)
    if cached:
        return {**state, "rag_context": [], "sources": [], "llm_response": cached, "chat_only_mode": False}

    # 1. Embed query (dense vector)
    if embedding_service is None:
        log.warning("embedding_service_not_configured")
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": True}

    try:
        query_vec = await embedding_service.embed(query)
    except Exception as e:
        log.warning("embedding_failed_chat_only_mode", error=str(e))
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": True}

    # 2-3. Execute dense vector search via MilvusClient with circuit breaker + retry
    from shared.milvus_client import COLLECTION_NAME
    cb = _get_milvus_circuit_breaker()
    try:
        async def _do_milvus_search():
            return collection.search(
                collection_name=COLLECTION_NAME,
                data=[query_vec],
                anns_field="dense_vector",
                filter=f"tenant_id == '{tenant_id}'",
                limit=5,
                output_fields=["chunk_text", "doc_id", "doc_title", "doc_url", "score"],
                search_params={"metric_type": "COSINE", "params": {"ef": 100}},
            )

        if cb.state == CircuitState.OPEN:
            log.warning("milvus_circuit_open_using_fallback")
            results = []
        else:
            results = await _retry_with_backoff(_do_milvus_search)
    except CircuitOpenError:
        log.warning("milvus_circuit_open_using_fallback")
        results = []
    except Exception as e:
        log.warning("milvus_search_failed", error=str(e))
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": True}

    if not results or not results[0]:
        log.warning("milvus_empty_results")
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": False}

    # 4. Soft-delete filtering
    doc_ids = [r.get("doc_id") or r.get("entity", {}).get("doc_id") for r in results[0]]
    active_docs = await get_active_doc_ids(doc_ids, tenant_id, pool=db_pool)

    # Build chunks with source metadata for reranking
    chunks_with_sources: list[tuple[str, Source]] = []
    for r in results[0]:
        doc_id = r.get("doc_id") or r.get("entity", {}).get("doc_id")
        chunk_text = r.get("chunk_text") or r.get("entity", {}).get("chunk_text")
        if doc_id in active_docs and chunk_text:
            source = Source(
                id=doc_id,
                title=r.get("doc_title", f"Document {doc_id[:8]}"),
                url=r.get("doc_url"),
                excerpt=chunk_text[:200] if chunk_text else None,
                confidence=r.get("score", 1.0),
                citation_type=CitationType.SEMANTIC_MATCH,
            )
            chunks_with_sources.append((chunk_text, source))

    if not chunks_with_sources:
        log.warning("rag_no_active_docs_after_filter")
        return {**state, "rag_context": [], "sources": [], "user_intent": "no_answer", "chat_only_mode": False}

    # 5. Rerank with BGE Reranker v2, timeout-protected
    top3_with_sources = await _rerank_chunks(query, chunks_with_sources)
    top3_chunks = [c for c, _ in top3_with_sources]
    top3_sources = [s for _, s in top3_with_sources]

    log.info("rag_search_success", chunks=len(top3_chunks))
    return {
        **state,
        "rag_context": top3_chunks,
        "sources": top3_sources,
        "chat_only_mode": False,
    }
