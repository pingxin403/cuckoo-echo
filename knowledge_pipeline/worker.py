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
        """Process a single document: parse → chunk → embed → store."""
        from knowledge_pipeline.parser import parse_document, ParseError
        from knowledge_pipeline.chunker import split_text

        try:
            await self._update_status(doc_id, "processing")

            # Parse
            text = await parse_document(file_path)

            # Chunk
            chunks = split_text(text)

            # Embed
            vectors = await self.embedding_service.embed_batch(
                [c for c in chunks]
            )

            # Store in Milvus
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
        except Exception as e:
            log.error("doc_processing_failed", doc_id=doc_id, error=str(e))
            await self._update_status(doc_id, "failed", error_msg=str(e))

    async def _update_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int | None = None,
        error_msg: str | None = None,
    ):
        async with self.db_pool.acquire() as conn:
            if chunk_count is not None:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, chunk_count=$2, updated_at=NOW() WHERE id=$3",
                    status,
                    chunk_count,
                    doc_id,
                )
            elif error_msg is not None:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, error_msg=$2, updated_at=NOW() WHERE id=$3",
                    status,
                    error_msg,
                    doc_id,
                )
            else:
                await conn.execute(
                    "UPDATE knowledge_docs SET status=$1, updated_at=NOW() WHERE id=$2",
                    status,
                    doc_id,
                )
