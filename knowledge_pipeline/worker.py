"""Knowledge Pipeline Worker — polls PG for pending docs and processes them."""
from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import structlog

log = structlog.get_logger()


class KnowledgePipelineWorker:
    def __init__(self, db_pool, milvus_client, embedding_service):
        self.db_pool = db_pool
        self.milvus_client = milvus_client
        self.embedding_service = embedding_service

    async def run(self):
        """Poll loop: SELECT FOR UPDATE SKIP LOCKED, sleep 2s when idle."""
        log.info("knowledge_pipeline_started")
        while True:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, tenant_id, oss_path FROM knowledge_docs "
                    "WHERE status = 'pending' ORDER BY created_at LIMIT 1 "
                    "FOR UPDATE SKIP LOCKED"
                )
            if row:
                await self.process_document(
                    str(row["id"]), str(row["tenant_id"]), row["oss_path"]
                )
            else:
                await asyncio.sleep(2)

    async def process_document(self, doc_id: str, tenant_id: str, file_path: str):
        """Process a single document with automatic retry (max 3 attempts)."""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await self._do_process(doc_id, tenant_id, file_path, attempt)
                return  # Success
            except Exception as e:
                if attempt < max_retries:
                    wait = 2 ** attempt  # 2s, 4s
                    log.warning("doc_processing_retry", doc_id=doc_id, attempt=attempt, error=str(e), wait=wait)
                    await self._update_status(doc_id, "processing", stage=f"retry {attempt}/{max_retries} in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    log.error("doc_processing_failed", doc_id=doc_id, error=str(e), attempts=max_retries)
                    await self._update_status(doc_id, "failed", error_msg=f"[{max_retries} attempts] {str(e)[:500]}")

    async def _do_process(self, doc_id: str, tenant_id: str, file_path: str, attempt: int):
        """Single processing attempt: parse → chunk → embed → store."""
        from knowledge_pipeline.parser import parse_document, ParseError
        from knowledge_pipeline.chunker import split_text

        await self._update_status(doc_id, "processing", stage=f"parsing (attempt {attempt})")

        # Parse
        text = await parse_document(file_path)
        log.info("doc_parsed", doc_id=doc_id, text_len=len(text))

        # Chunk
        await self._update_status(doc_id, "processing", stage="chunking")
        chunks = split_text(text)
        log.info("doc_chunked", doc_id=doc_id, chunks=len(chunks))

        # Embed
        await self._update_status(doc_id, "processing", stage=f"embedding ({len(chunks)} chunks)")
        vectors = await self.embedding_service.embed_batch(
            [c for c in chunks]
        )
        log.info("doc_embedded", doc_id=doc_id, vectors=len(vectors))

        # Store in Milvus
        await self._update_status(doc_id, "processing", stage="storing")
        data = [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "doc_id": doc_id,
                    "chunk_text": chunk,
                    "dense_vector": vec,
                    "created_at": int(time.time()),
                }
                for chunk, vec in zip(chunks, vectors)
            ]
            self.milvus_client.insert(
                collection_name="knowledge_chunks",
                data=data,
            )

            await self._update_status(doc_id, "completed", chunk_count=len(chunks))
            log.info("doc_processed", doc_id=doc_id, chunks=len(chunks))

    async def _update_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int | None = None,
        error_msg: str | None = None,
        stage: str | None = None,
    ):
        async with self.db_pool.acquire() as conn:
            if chunk_count is not None:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, chunk_count=$2, error_msg=NULL, updated_at=NOW() WHERE id=$3",
                    status, chunk_count, doc_id,
                )
            elif error_msg is not None:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, error_msg=$2, updated_at=NOW() WHERE id=$3",
                    status, error_msg, doc_id,
                )
            elif stage is not None:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, error_msg=$2, updated_at=NOW() WHERE id=$3",
                    status, f"stage:{stage}", doc_id,
                )
            else:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, updated_at=NOW() WHERE id=$2",
                    status, doc_id,
                )


# ── Entry point ──────────────────────────────────────────────────

async def main():
    """Initialize dependencies and start the poll loop."""
    from shared.db import create_asyncpg_pool
    from shared.embedding_service import get_embedding_service
    from shared.milvus_client import get_milvus_client
    from shared.logging import setup_logging
    from shared.config import get_settings

    settings = get_settings()
    setup_logging(settings.log_level)

    db_pool = await create_asyncpg_pool()
    milvus_client = get_milvus_client()
    embedding_service = get_embedding_service()

    worker = KnowledgePipelineWorker(db_pool, milvus_client, embedding_service)
    try:
        await worker.run()
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
