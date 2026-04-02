"""RAG Engine node — hybrid search + rerank + soft-delete filtering.

Pipeline: embed query → Milvus hybrid_search (dense + BM25) → soft-delete
filter via PG → BGE Reranker v2 (timeout-protected) → top-3 chunks.
"""
from __future__ import annotations

import asyncio

import structlog
from pymilvus import AnnSearchRequest, RRFRanker

from chat_service.agent.state import AgentState

log = structlog.get_logger()

# Module-level placeholders — wired at app startup via dependency injection.
embedding_service = None  # must expose async .embed(text) -> list[float]
reranker = None           # must expose .compute_score(pairs) -> list[float]
collection = None         # pymilvus Collection with hybrid_search support
db_pool = None            # asyncpg pool for soft-delete checks


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
    chunks: list[str],
    timeout: float = 0.5,
) -> list[str]:
    """Rerank *chunks* using BGE Reranker v2 and return the top-3.

    Falls back to RRF order (first 3) on timeout or when no reranker is
    configured.
    """
    if reranker is None:
        return chunks[:3]

    try:
        loop = asyncio.get_running_loop()
        pairs = [[query, chunk] for chunk in chunks]
        scores = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: reranker.compute_score(pairs)),
            timeout=timeout,
        )
        # Sort by score descending, take top 3
        scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:3]]
    except asyncio.TimeoutError:
        log.warning("rerank_timeout", query_len=len(query))
        return chunks[:3]


# ---------------------------------------------------------------------------
# Task 8.1 / 8.2: RAG Engine node
# ---------------------------------------------------------------------------

async def rag_engine_node(state: AgentState) -> AgentState:
    """RAG Engine: hybrid search (dense + BM25) → soft-delete filter → rerank → top-3."""
    messages = state.get("messages", [])
    if not messages:
        return {**state, "rag_context": [], "user_intent": "no_answer"}

    query = messages[-1].get("content", "")
    tenant_id = state.get("tenant_id", "")

    if not query or not tenant_id:
        return {**state, "rag_context": [], "user_intent": "no_answer"}

    # 1. Embed query (dense vector)
    if embedding_service is None:
        log.warning("embedding_service_not_configured")
        return {**state, "rag_context": [], "user_intent": "no_answer"}

    query_vec = await embedding_service.embed(query)

    # 2. Build hybrid search requests (Task 8.1)
    dense_req = AnnSearchRequest(
        data=[query_vec],
        anns_field="dense_vector",
        param={"metric_type": "COSINE", "params": {"ef": 100}},
        limit=10,
        expr=f"tenant_id == '{tenant_id}'",
    )
    sparse_req = AnnSearchRequest(
        data=[query],
        anns_field="sparse_vector",
        param={"metric_type": "BM25"},
        limit=10,
        expr=f"tenant_id == '{tenant_id}'",
    )

    # 3. Execute hybrid search with RRF fusion (Task 8.2)
    results = collection.hybrid_search(
        reqs=[dense_req, sparse_req],
        rerank=RRFRanker(k=60),
        limit=5,
        output_fields=["chunk_text", "doc_id"],
        partition_names=[tenant_id],
    )

    if not results or not results[0]:
        return {**state, "rag_context": [], "user_intent": "no_answer"}

    # 4. Soft-delete filtering (Task 8.3)
    doc_ids = [r.entity.get("doc_id") for r in results[0]]
    active_docs = await get_active_doc_ids(doc_ids, tenant_id, pool=db_pool)
    chunks = [
        r.entity.get("chunk_text")
        for r in results[0]
        if r.entity.get("doc_id") in active_docs
    ]

    if not chunks:
        return {**state, "rag_context": [], "user_intent": "no_answer"}

    # 5. Rerank with BGE Reranker v2, timeout-protected (Task 8.4)
    top3 = await _rerank_chunks(query, chunks)

    return {**state, "rag_context": top3}
