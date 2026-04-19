"""Unit tests for semantic cache (Task 31.4)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import shared.semantic_cache as sc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_module():
    """Reset module-level placeholders."""
    sc.milvus_client = None
    sc.embedding_service = None


# ---------------------------------------------------------------------------
# cache_lookup tests
# ---------------------------------------------------------------------------

class TestCacheLookup:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self):
        _reset_module()
        result = await sc.cache_lookup("hello", "t1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_response_on_hit(self):
        mock_embed = AsyncMock(return_value=[0.1] * 128)
        mock_client = MagicMock()
        hit = {"distance": 0.98, "entity": {"response_text": "cached answer", "created_at": 100}}
        mock_client.search.return_value = [[hit]]

        sc.milvus_client = mock_client
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            result = await sc.cache_lookup("test query", "t1")
            assert result == "cached answer"
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args
            assert call_kwargs[1]["collection_name"] == sc.CACHE_COLLECTION
            assert 't1' in call_kwargs[1]["filter"]
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_returns_none_on_miss_below_threshold(self):
        mock_embed = AsyncMock(return_value=[0.1] * 128)
        mock_client = MagicMock()
        hit = {"distance": 0.80, "entity": {"response_text": "low score", "created_at": 100}}
        mock_client.search.return_value = [[hit]]

        sc.milvus_client = mock_client
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            result = await sc.cache_lookup("test query", "t1")
            assert result is None
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_results(self):
        mock_embed = AsyncMock(return_value=[0.1] * 128)
        mock_client = MagicMock()
        mock_client.search.return_value = [[]]

        sc.milvus_client = mock_client
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            result = await sc.cache_lookup("test query", "t1")
            assert result is None
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        mock_embed = AsyncMock(side_effect=RuntimeError("embed failed"))
        sc.milvus_client = MagicMock()
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            result = await sc.cache_lookup("test query", "t1")
            assert result is None
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_returns_none_when_response_text_empty(self):
        mock_embed = AsyncMock(return_value=[0.1] * 128)
        mock_client = MagicMock()
        hit = {"distance": 0.99, "entity": {"response_text": "", "created_at": 100}}
        mock_client.search.return_value = [[hit]]

        sc.milvus_client = mock_client
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            result = await sc.cache_lookup("test query", "t1")
            assert result is None
        finally:
            _reset_module()


# ---------------------------------------------------------------------------
# cache_store tests
# ---------------------------------------------------------------------------

class TestCacheStore:
    @pytest.mark.asyncio
    async def test_does_nothing_when_not_configured(self):
        _reset_module()
        await sc.cache_store("q", "r", "t1")  # should not raise

    @pytest.mark.asyncio
    async def test_stores_query_response_pair(self):
        mock_embed = AsyncMock(return_value=[0.2] * 128)
        mock_client = MagicMock()

        sc.milvus_client = mock_client
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            await sc.cache_store("my question", "my answer", "t1")
            mock_client.insert.assert_called_once()
            call_kwargs = mock_client.insert.call_args
            assert call_kwargs[1]["collection_name"] == sc.CACHE_COLLECTION
            data = call_kwargs[1]["data"][0]
            assert data["tenant_id"] == "t1"
            assert data["query_text"] == "my question"
            assert data["response_text"] == "my answer"
            assert data["query_vector"] == [0.2] * 128
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        mock_embed = AsyncMock(side_effect=RuntimeError("embed failed"))
        sc.milvus_client = MagicMock()
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            await sc.cache_store("q", "r", "t1")  # should not raise
        finally:
            _reset_module()


# ---------------------------------------------------------------------------
# cache_invalidate tests
# ---------------------------------------------------------------------------

class TestCacheInvalidate:
    @pytest.mark.asyncio
    async def test_does_nothing_when_not_configured(self):
        _reset_module()
        await sc.cache_invalidate("t1")  # should not raise

    @pytest.mark.asyncio
    async def test_deletes_tenant_entries(self):
        mock_client = MagicMock()
        sc.milvus_client = mock_client
        try:
            await sc.cache_invalidate("t1")
            mock_client.delete.assert_called_once()
            call_kwargs = mock_client.delete.call_args
            assert call_kwargs[1]["collection_name"] == sc.CACHE_COLLECTION
            assert 't1' in call_kwargs[1]["filter"]
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        mock_client = MagicMock()
        mock_client.delete.side_effect = RuntimeError("milvus down")
        sc.milvus_client = mock_client
        try:
            await sc.cache_invalidate("t1")  # should not raise
        finally:
            _reset_module()


# ---------------------------------------------------------------------------
# Tenant isolation in cache
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_lookup_filters_by_tenant_id(self):
        """cache_lookup passes tenant_id filter to Milvus search."""
        mock_embed = AsyncMock(return_value=[0.1] * 128)
        mock_client = MagicMock()
        mock_client.search.return_value = [[]]

        sc.milvus_client = mock_client
        sc.embedding_service = MagicMock(embed=mock_embed)
        try:
            await sc.cache_lookup("query", "tenant_abc")
            call_kwargs = mock_client.search.call_args[1]
            assert 'tenant_abc' in call_kwargs["filter"]
        finally:
            _reset_module()

    @pytest.mark.asyncio
    async def test_invalidate_filters_by_tenant_id(self):
        """cache_invalidate only deletes entries for the specified tenant."""
        mock_client = MagicMock()
        sc.milvus_client = mock_client
        try:
            await sc.cache_invalidate("tenant_xyz")
            call_kwargs = mock_client.delete.call_args[1]
            assert 'tenant_xyz' in call_kwargs["filter"]
        finally:
            _reset_module()


# ---------------------------------------------------------------------------
# RAG engine integration tests
# ---------------------------------------------------------------------------

class TestRagEngineCacheIntegration:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_response_without_search(self):
        """When semantic cache hits, rag_engine_node returns cached response directly."""
        from chat_service.agent.nodes.rag_engine import rag_engine_node
        from chat_service.agent.state import AgentState

        state = AgentState(
            messages=[{"role": "user", "content": "test query"}],
            tenant_id="t1",
        )
        with patch(
            "shared.semantic_cache.cache_lookup",
            new_callable=AsyncMock,
            return_value="cached response",
        ) as mock_lookup, patch.multiple(
            "chat_service.agent.nodes.rag_engine",
            embedding_service=MagicMock(),
            collection=MagicMock(),
        ):
            result = await rag_engine_node(state)

        assert result["llm_response"] == "cached response"
        assert result["rag_context"] == []
        mock_lookup.assert_awaited_once_with("test query", "t1")

    @pytest.mark.asyncio
    async def test_cache_miss_proceeds_with_normal_rag(self):
        """When semantic cache misses, rag_engine_node proceeds with normal search."""
        from chat_service.agent.nodes.rag_engine import rag_engine_node
        from chat_service.agent.state import AgentState

        mock_embed = AsyncMock(return_value=[0.1] * 4096)
        mock_collection = MagicMock()
        mock_collection.search.return_value = [[{"chunk_text": "chunk_1", "doc_id": "doc_1"}]]

        state = AgentState(
            messages=[{"role": "user", "content": "test query"}],
            tenant_id="t1",
        )
        with patch(
            "shared.semantic_cache.cache_lookup",
            new_callable=AsyncMock,
            return_value=None,
        ), patch.multiple(
            "chat_service.agent.nodes.rag_engine",
            embedding_service=MagicMock(embed=mock_embed),
            collection=mock_collection,
            db_pool=None,
            reranker=None,
        ):
            result = await rag_engine_node(state)

        assert result["rag_context"] == ["chunk_1"]


# ---------------------------------------------------------------------------
# Admin cache clear endpoint test
# ---------------------------------------------------------------------------

class TestCacheClearEndpoint:
    def test_clear_cache_endpoint(self):
        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from admin_service.routes.config import router as config_router

        app = FastAPI()
        app.include_router(config_router)
        app.state.db_pool = MagicMock()
        app.state.redis = AsyncMock()

        @app.middleware("http")
        async def fake_auth(request, call_next):
            request.state.tenant_id = "test-tenant"
            return await call_next(request)

        client = TestClient(app)

        with patch("shared.semantic_cache.cache_invalidate", new_callable=AsyncMock) as mock_inv:
            resp = client.post("/admin/v1/config/cache/clear")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cleared"
        assert body["tenant_id"] == "test-tenant"
        mock_inv.assert_awaited_once_with("test-tenant")
