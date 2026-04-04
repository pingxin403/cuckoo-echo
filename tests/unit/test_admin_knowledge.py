"""Unit tests for Admin Knowledge Management."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from fastapi import FastAPI
from admin_service.routes.knowledge import router, _cleanup_milvus_vectors


def _build_app(db_pool=None):
    """Build a test FastAPI app with the knowledge router and fake auth middleware."""
    app = FastAPI()
    app.include_router(router)
    app.state.db_pool = db_pool or MagicMock()

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.tenant_id = "test-tenant"
        return await call_next(request)

    return app


def _mock_pool(mock_conn=None):
    """Create a mock db_pool whose acquire() returns an async context manager."""
    conn = mock_conn or AsyncMock()
    pool = MagicMock()
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acm)
    return pool, conn


class TestUploadDocument:
    def test_upload_creates_pending_row(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.post(
            "/admin/v1/knowledge/docs",
            files={"file": ("test.pdf", b"content", "application/pdf")},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert "doc_id" in body
        conn.execute.assert_awaited_once()
        # Verify the SQL contains INSERT and 'pending'
        call_args = conn.execute.await_args
        assert "INSERT INTO knowledge_docs" in call_args[0][0]
        assert call_args[0][4].endswith("/test.pdf")

    def test_upload_rejects_oversized_file(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        big_content = b"x" * (200 * 1024 * 1024 + 1)
        resp = client.post(
            "/admin/v1/knowledge/docs",
            files={"file": ("big.pdf", big_content, "application/pdf")},
        )

        assert resp.status_code == 413
        conn.execute.assert_not_awaited()


class TestGetDocumentProgress:
    def test_returns_progress(self):
        mock_row = {"status": "completed", "chunk_count": 42, "error_msg": None}
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=mock_row)
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.knowledge.tenant_db_context") as mock_ctx:
            # Make tenant_db_context a passthrough async context manager
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.get("/admin/v1/knowledge/docs/some-doc-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["chunk_count"] == 42
        assert body["error_msg"] is None

    def test_returns_404_when_not_found(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.knowledge.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.get("/admin/v1/knowledge/docs/nonexistent")

        assert resp.status_code == 404


class TestDeleteDocument:
    def test_delete_sets_deleted_at(self):
        conn = AsyncMock()
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        # Attach a mock milvus_client so background task doesn't warn
        app.state.milvus_client = None
        client = TestClient(app)

        with patch("admin_service.routes.knowledge.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.delete("/admin/v1/knowledge/docs/doc-123")

        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert body["doc_id"] == "doc-123"
        # Verify the SQL sets deleted_at
        call_args = conn.execute.await_args
        assert "deleted_at = NOW()" in call_args[0][0]


class TestRetryDocument:
    def test_retry_resets_status(self):
        conn = AsyncMock()
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        with patch("admin_service.routes.knowledge.tenant_db_context") as mock_ctx:
            ctx_cm = AsyncMock()
            ctx_cm.__aenter__ = AsyncMock(return_value=conn)
            ctx_cm.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx_cm

            resp = client.post("/admin/v1/knowledge/docs/doc-456/retry")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert body["doc_id"] == "doc-456"
        # Verify the SQL resets status and clears error_msg
        call_args = conn.execute.await_args
        sql = call_args[0][0]
        assert "status = 'pending'" in sql
        assert "error_msg = NULL" in sql


class TestCleanupMilvusVectors:
    @pytest.mark.asyncio
    async def test_deletes_vectors_on_success(self):
        mock_milvus = MagicMock()
        mock_app = MagicMock()
        mock_app.state.milvus_client = mock_milvus

        await _cleanup_milvus_vectors("doc-789", mock_app)

        mock_milvus.delete.assert_called_once_with(
            collection_name="knowledge_chunks",
            filter='doc_id == "doc-789"',
        )

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        mock_milvus = MagicMock()
        mock_milvus.delete.side_effect = [Exception("fail"), Exception("fail"), None]
        mock_app = MagicMock()
        mock_app.state.milvus_client = mock_milvus

        with patch("admin_service.routes.knowledge.asyncio.sleep", new_callable=AsyncMock):
            await _cleanup_milvus_vectors("doc-retry", mock_app, max_retries=3)

        assert mock_milvus.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_when_milvus_not_configured(self):
        mock_app = MagicMock()
        mock_app.state.milvus_client = None

        # Should not raise
        await _cleanup_milvus_vectors("doc-no-milvus", mock_app)
