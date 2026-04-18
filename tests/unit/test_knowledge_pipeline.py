"""Unit tests for Knowledge Pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from knowledge_pipeline.chunker import split_text
from knowledge_pipeline.parser import parse_document, ParseError


# ---------------------------------------------------------------------------
# TestChunker
# ---------------------------------------------------------------------------


class TestChunker:
    def test_short_text_single_chunk(self):
        chunks = split_text("Hello world")
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_respects_chunk_size(self):
        text = "a" * 1000
        chunks = split_text(text, chunk_size=512)
        assert all(len(c) <= 512 for c in chunks)

    def test_overlap_present(self):
        text = "a" * 1000
        chunks = split_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_empty_text_returns_empty(self):
        assert split_text("") == []
        assert split_text("   ") == []

    def test_chinese_sentence_splitting(self):
        text = "第一段内容。第二段内容。第三段内容。" * 50
        chunks = split_text(text, chunk_size=100)
        assert all(len(c) <= 100 for c in chunks)

    def test_at_least_one_chunk_for_valid_input(self):
        chunks = split_text("Some valid text")
        assert len(chunks) >= 1

    def test_paragraph_splitting(self):
        text = ("Short paragraph.\n\n" * 5).strip()
        chunks = split_text(text, chunk_size=50)
        assert all(len(c) <= 50 for c in chunks)


# ---------------------------------------------------------------------------
# TestParser
# ---------------------------------------------------------------------------


class TestParser:
    @pytest.mark.asyncio
    async def test_txt_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world", encoding="utf-8")
        result = await parse_document(str(f))
        assert "Hello world" in result

    @pytest.mark.asyncio
    async def test_empty_txt_raises(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        with pytest.raises(ParseError):
            await parse_document(str(f))

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            await parse_document("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_latin1_fallback(self, tmp_path):
        f = tmp_path / "latin.txt"
        f.write_bytes(b"caf\xe9 au lait")
        result = await parse_document(str(f))
        assert "caf" in result


# ---------------------------------------------------------------------------
# TestWorker
# ---------------------------------------------------------------------------


class TestWorker:
    @pytest.mark.asyncio
    async def test_process_document_success(self):
        from knowledge_pipeline.worker import KnowledgePipelineWorker

        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        acm = AsyncMock()
        acm.__aenter__ = AsyncMock(return_value=mock_conn)
        acm.__aexit__ = AsyncMock(return_value=False)
        mock_pool.acquire = MagicMock(return_value=acm)

        mock_milvus = MagicMock()
        mock_embed = AsyncMock(return_value=[[0.1] * 1536])

        worker = KnowledgePipelineWorker(
            mock_pool, mock_milvus, MagicMock(embed_batch=mock_embed)
        )

        with patch(
            "knowledge_pipeline.parser.parse_document",
            new_callable=AsyncMock,
            return_value="test content",
        ), patch("knowledge_pipeline.chunker.split_text", return_value=["chunk1"]):
            await worker.process_document("doc1", "t1", "/path/test.txt")

        # Should have called execute at least twice: processing + completed
        assert mock_conn.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_process_document_failure_sets_failed(self):
        from knowledge_pipeline.worker import KnowledgePipelineWorker

        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        acm = AsyncMock()
        acm.__aenter__ = AsyncMock(return_value=mock_conn)
        acm.__aexit__ = AsyncMock(return_value=False)
        mock_pool.acquire = MagicMock(return_value=acm)

        worker = KnowledgePipelineWorker(mock_pool, MagicMock(), MagicMock())

        with patch(
            "knowledge_pipeline.parser.parse_document",
            new_callable=AsyncMock,
            side_effect=Exception("parse failed"),
        ):
            await worker.process_document("doc1", "t1", "/bad/file.pdf")

        # Last execute call should set status=failed
        last_call = mock_conn.execute.call_args_list[-1]
        assert "failed" in str(last_call)
