"""Unit tests for RAG Engine node."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from chat_service.agent.nodes.rag_engine import (
    _rerank_chunks,
    get_active_doc_ids,
    rag_engine_node,
)
from chat_service.agent.state import AgentState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hit(chunk_text: str, doc_id: str) -> dict:
    """Create a mock Milvus MilvusClient search result dict."""
    return {"chunk_text": chunk_text, "doc_id": doc_id}


# ---------------------------------------------------------------------------
# TestRagEngineNode
# ---------------------------------------------------------------------------

class TestRagEngineNode:
    @pytest.mark.asyncio
    async def test_returns_no_answer_when_no_messages(self):
        state = AgentState(messages=[], tenant_id="t1")
        result = await rag_engine_node(state)
        assert result["user_intent"] == "no_answer"
        assert result["rag_context"] == []

    @pytest.mark.asyncio
    async def test_returns_no_answer_when_empty_query(self):
        state = AgentState(messages=[{"role": "user", "content": ""}], tenant_id="t1")
        result = await rag_engine_node(state)
        assert result["user_intent"] == "no_answer"

    @pytest.mark.asyncio
    async def test_returns_no_answer_when_no_tenant(self):
        state = AgentState(messages=[{"role": "user", "content": "hello"}], tenant_id="")
        result = await rag_engine_node(state)
        assert result["user_intent"] == "no_answer"

    @pytest.mark.asyncio
    async def test_returns_no_answer_when_embedding_not_configured(self):
        state = AgentState(messages=[{"role": "user", "content": "test"}], tenant_id="t1")
        with patch("chat_service.agent.nodes.rag_engine.embedding_service", None):
            result = await rag_engine_node(state)
        assert result["user_intent"] == "no_answer"

    @pytest.mark.asyncio
    async def test_returns_no_answer_on_empty_search_results(self):
        mock_embed = AsyncMock(return_value=[0.1] * 1536)
        mock_collection = MagicMock()
        mock_collection.search.return_value = [[]]  # empty results

        state = AgentState(messages=[{"role": "user", "content": "test"}], tenant_id="t1")
        with patch.multiple(
            "chat_service.agent.nodes.rag_engine",
            embedding_service=MagicMock(embed=mock_embed),
            collection=mock_collection,
            db_pool=None,
            reranker=None,
        ):
            result = await rag_engine_node(state)
        assert result["rag_context"] == []
        assert result["user_intent"] == "no_answer"

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_top3_after_rerank(self):
        """Milvus returns up to 5 hits; after rerank we get ≤ 3."""
        mock_embed = AsyncMock(return_value=[0.1] * 1536)
        mock_collection = MagicMock()
        hits = [_make_hit(f"chunk_{i}", f"doc_{i}") for i in range(5)]
        mock_collection.search.return_value = [hits]

        state = AgentState(
            messages=[{"role": "user", "content": "test query"}],
            tenant_id="t1",
        )
        with patch.multiple(
            "chat_service.agent.nodes.rag_engine",
            embedding_service=MagicMock(embed=mock_embed),
            collection=mock_collection,
            db_pool=None,   # skip soft-delete → all docs active
            reranker=None,  # no reranker → first 3
        ):
            result = await rag_engine_node(state)

        assert len(result["rag_context"]) == 3
        assert result["rag_context"] == ["chunk_0", "chunk_1", "chunk_2"]

    @pytest.mark.asyncio
    async def test_soft_deleted_docs_filtered(self):
        """Chunks belonging to soft-deleted docs must be excluded."""
        mock_embed = AsyncMock(return_value=[0.1] * 1536)
        mock_collection = MagicMock()
        hits = [
            _make_hit("active_1", "doc_1"),
            _make_hit("deleted", "doc_2"),
            _make_hit("active_2", "doc_3"),
        ]
        mock_collection.search.return_value = [hits]

        state = AgentState(
            messages=[{"role": "user", "content": "test"}],
            tenant_id="t1",
        )
        with patch.multiple(
            "chat_service.agent.nodes.rag_engine",
            embedding_service=MagicMock(embed=mock_embed),
            collection=mock_collection,
            reranker=None,
        ), patch(
            "chat_service.agent.nodes.rag_engine.get_active_doc_ids",
            new_callable=AsyncMock,
            return_value={"doc_1", "doc_3"},
        ):
            result = await rag_engine_node(state)

        assert "deleted" not in result["rag_context"]
        assert result["rag_context"] == ["active_1", "active_2"]

    @pytest.mark.asyncio
    async def test_all_docs_soft_deleted_returns_no_answer(self):
        mock_embed = AsyncMock(return_value=[0.1] * 1536)
        mock_collection = MagicMock()
        hits = [_make_hit("gone", "doc_1")]
        mock_collection.search.return_value = [hits]

        state = AgentState(
            messages=[{"role": "user", "content": "test"}],
            tenant_id="t1",
        )
        with patch.multiple(
            "chat_service.agent.nodes.rag_engine",
            embedding_service=MagicMock(embed=mock_embed),
            collection=mock_collection,
            reranker=None,
        ), patch(
            "chat_service.agent.nodes.rag_engine.get_active_doc_ids",
            new_callable=AsyncMock,
            return_value=set(),  # all deleted
        ):
            result = await rag_engine_node(state)

        assert result["rag_context"] == []
        assert result["user_intent"] == "no_answer"


# ---------------------------------------------------------------------------
# TestRerank
# ---------------------------------------------------------------------------

class TestRerank:
    @pytest.mark.asyncio
    async def test_returns_top3_sorted_by_score(self):
        chunks = ["a", "b", "c", "d", "e"]
        mock_reranker = MagicMock()
        mock_reranker.compute_score.return_value = [0.9, 0.1, 0.8, 0.3, 0.7]

        with patch("chat_service.agent.nodes.rag_engine.reranker", mock_reranker):
            result = await _rerank_chunks("query", chunks)

        assert len(result) == 3
        assert result[0] == "a"   # score 0.9
        assert result[1] == "c"   # score 0.8
        assert result[2] == "e"   # score 0.7

    @pytest.mark.asyncio
    async def test_timeout_falls_back_to_rrf_order(self):
        chunks = ["a", "b", "c", "d", "e"]
        mock_reranker = MagicMock()

        def slow_compute(pairs):
            import time
            time.sleep(10)
            return [1.0] * len(pairs)

        mock_reranker.compute_score.side_effect = slow_compute

        with patch("chat_service.agent.nodes.rag_engine.reranker", mock_reranker):
            result = await _rerank_chunks("query", chunks, timeout=0.01)

        assert result == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_no_reranker_returns_first3(self):
        chunks = ["a", "b", "c", "d", "e"]
        with patch("chat_service.agent.nodes.rag_engine.reranker", None):
            result = await _rerank_chunks("query", chunks)
        assert result == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_fewer_than_3_chunks(self):
        chunks = ["only_one"]
        with patch("chat_service.agent.nodes.rag_engine.reranker", None):
            result = await _rerank_chunks("query", chunks)
        assert result == ["only_one"]


# ---------------------------------------------------------------------------
# TestGetActiveDocIds
# ---------------------------------------------------------------------------

class TestGetActiveDocIds:
    @pytest.mark.asyncio
    async def test_returns_all_when_no_pool(self):
        result = await get_active_doc_ids(["d1", "d2"], "t1", pool=None)
        assert result == {"d1", "d2"}

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self):
        result = await get_active_doc_ids([], "t1")
        assert result == set()

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input_with_pool(self):
        mock_pool = MagicMock()
        result = await get_active_doc_ids([], "t1", pool=mock_pool)
        assert result == set()
