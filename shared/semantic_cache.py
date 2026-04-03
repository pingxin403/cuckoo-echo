"""Semantic cache using Milvus for query-response caching."""
from __future__ import annotations

import time
from uuid import uuid4

import structlog

log = structlog.get_logger()

CACHE_COLLECTION = "semantic_cache"
SIMILARITY_THRESHOLD = 0.95
CACHE_TTL_HOURS = 24

# Module-level placeholders — wired at startup
milvus_client = None
embedding_service = None


async def cache_lookup(query: str, tenant_id: str) -> str | None:
    """Look up a cached response for a semantically similar query.

    Returns the cached response text if similarity >= 0.95, else None.
    """
    if not milvus_client or not embedding_service:
        return None

    try:
        query_vec = await embedding_service.embed(query)
        results = milvus_client.search(
            collection_name=CACHE_COLLECTION,
            data=[query_vec],
            filter=f'tenant_id == "{tenant_id}"',
            limit=1,
            output_fields=["response_text", "created_at"],
            anns_field="query_vector",
        )

        if results and results[0]:
            hit = results[0][0]
            score = hit.get("distance", 0)
            # COSINE similarity: 1.0 = identical, check >= threshold
            if score >= SIMILARITY_THRESHOLD:
                response = hit.get("entity", {}).get("response_text", "")
                if response:
                    log.info("semantic_cache_hit", tenant_id=tenant_id, score=score)
                    return response

        return None
    except Exception as e:
        log.warning("semantic_cache_lookup_failed", error=str(e))
        return None


async def cache_store(query: str, response: str, tenant_id: str) -> None:
    """Store a query-response pair in the semantic cache."""
    if not milvus_client or not embedding_service:
        return

    try:
        query_vec = await embedding_service.embed(query)
        milvus_client.insert(
            collection_name=CACHE_COLLECTION,
            data=[{
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "query_text": query,
                "response_text": response,
                "query_vector": query_vec,
                "created_at": int(time.time()),
            }],
        )
        log.info("semantic_cache_stored", tenant_id=tenant_id)
    except Exception as e:
        log.warning("semantic_cache_store_failed", error=str(e))


async def cache_invalidate(tenant_id: str) -> None:
    """Invalidate all cache entries for a tenant."""
    if not milvus_client:
        return
    try:
        milvus_client.delete(
            collection_name=CACHE_COLLECTION,
            filter=f'tenant_id == "{tenant_id}"',
        )
        log.info("semantic_cache_invalidated", tenant_id=tenant_id)
    except Exception as e:
        log.warning("semantic_cache_invalidate_failed", error=str(e))
