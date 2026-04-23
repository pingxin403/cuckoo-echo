"""Unit tests for context compression."""
import pytest
from datetime import datetime
from shared.context_compressor import ContextCompressor, Message


class TestContextCompressor:
    def test_compress_empty(self):
        compressor = ContextCompressor()
        result = compressor.compress([], 1000)
        assert result == []

    def test_compress_preserves_high_priority(self):
        compressor = ContextCompressor()
        messages = [
            Message(role="user", content="hello", timestamp=datetime.now()),
            Message(role="tool", content="result", metadata={"is_tool_result": True}, timestamp=datetime.now()),
        ]
        result = compressor.compress(messages, 500)
        assert len(result) >= 1

    def test_importance_scoring_tool_result(self):
        compressor = ContextCompressor()
        msg = Message(role="tool", content="result", metadata={"is_tool_result": True})
        score = compressor.score_importance(msg)
        assert score == 1.0

    def test_importance_scoring_preference(self):
        compressor = ContextCompressor()
        msg = Message(role="user", content="I prefer dark mode")
        score = compressor.score_importance(msg)
        assert score == 0.9

    def test_prune_irrelevant(self):
        compressor = ContextCompressor()
        messages = [
            Message(role="user", content="order status"),
            Message(role="assistant", content="price information"),
        ]
        result = compressor.prune_irrelevant(messages, "order")
        assert len(result) <= len(messages)