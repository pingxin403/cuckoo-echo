"""Admin Knowledge Management API routes."""
from __future__ import annotations
import asyncio
from uuid import uuid4
import structlog
from fastapi import APIRouter, UploadFile, File, Request, HTTPException, BackgroundTasks
from shared.db import tenant_db_context

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/knowledge")

MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200MB


@router.post("/docs")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """Upload a document for processing. Max 200MB."""
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 200MB)")

    tenant_id = request.state.tenant_id
    doc_id = str(uuid4())
    oss_path = f"{tenant_id}/docs/{doc_id}/{file.filename}"

    # TODO: Upload to OSS in production

    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO knowledge_docs (id, tenant_id, filename, oss_path, status)
               VALUES ($1, $2, $3, $4, 'pending')""",
            doc_id, tenant_id, file.filename, oss_path,
        )

    log.info("document_uploaded", doc_id=doc_id, tenant_id=tenant_id, filename=file.filename)
    return {"doc_id": doc_id, "status": "pending"}


@router.get("/docs")
async def list_documents(request: Request):
    """List all knowledge documents for the tenant."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            rows = await conn.fetch(
                """SELECT id, filename, oss_path, status, chunk_count, error_msg, created_at, updated_at
                   FROM knowledge_docs
                   WHERE tenant_id = $1 AND deleted_at IS NULL
                   ORDER BY created_at DESC
                   LIMIT 100""",
                tenant_id,
            )

    return [
        {
            "doc_id": str(row["id"]),
            "filename": row["filename"],
            "status": row["status"],
            "chunk_count": row["chunk_count"],
            "error_msg": row["error_msg"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


@router.get("/docs/{doc_id}")
async def get_document_progress(doc_id: str, request: Request):
    """Query document processing progress."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            row = await conn.fetchrow(
                "SELECT status, chunk_count, error_msg FROM knowledge_docs WHERE id = $1",
                doc_id,
            )
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "doc_id": doc_id,
        "status": row["status"],
        "chunk_count": row["chunk_count"],
        "error_msg": row["error_msg"],
    }


@router.delete("/docs/{doc_id}")
async def delete_document(doc_id: str, request: Request, background_tasks: BackgroundTasks):
    """Soft-delete a document and enqueue Milvus cleanup."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            result = await conn.execute(
                "UPDATE knowledge_docs SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL",
                doc_id,
            )

    # Enqueue async Milvus cleanup
    background_tasks.add_task(_cleanup_milvus_vectors, doc_id, request.app)

    log.info("document_deleted", doc_id=doc_id, tenant_id=tenant_id)
    return {"doc_id": doc_id, "deleted": True}


async def _cleanup_milvus_vectors(doc_id: str, app, max_retries: int = 3):
    """Delete vectors from Milvus with retry (exponential backoff)."""
    milvus = getattr(app.state, "milvus_client", None)
    if not milvus:
        log.warning("milvus_not_configured", doc_id=doc_id)
        return

    for attempt in range(max_retries):
        try:
            milvus.delete(
                collection_name="knowledge_chunks",
                filter=f'doc_id == "{doc_id}"',
            )
            log.info("milvus_vectors_deleted", doc_id=doc_id)
            return
        except Exception as e:
            wait = 2 ** attempt
            log.warning("milvus_delete_retry", doc_id=doc_id, attempt=attempt, error=str(e))
            await asyncio.sleep(wait)
    log.error("milvus_delete_failed", doc_id=doc_id)


@router.post("/docs/{doc_id}/retry")
async def retry_document(doc_id: str, request: Request):
    """Reset a failed document to pending for reprocessing."""
    db_pool = request.app.state.db_pool
    tenant_id = request.state.tenant_id

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                "UPDATE knowledge_docs SET status = 'pending', error_msg = NULL, updated_at = NOW() WHERE id = $1",
                doc_id,
            )

    log.info("document_retry", doc_id=doc_id, tenant_id=tenant_id)
    return {"doc_id": doc_id, "status": "pending"}
