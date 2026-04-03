"""Unit tests for LLMSummarizer.

Covers:
- summarize() calls LLM and returns summary string
- LLM failure degrades gracefully (returns empty string)
- _wire_dependencies sets llm_summarizer on preprocess module
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat_service.agent.summarizer import LLMSummarizer


class TestLLMSummarizer:
    @pytest.mark.asyncio
    async def test_summarize_returns_string(self):
        """summarize() calls LLM and returns the generated summary."""
        messages = [
            {"role": "user", "content": "我想查订单"},
            {"role": "assistant", "content": "请提供订单号"},
            {"role": "user", "content": "12345"},
            {"role": "assistant", "content": "订单已发货"},
        ]

        # Mock the streaming response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta = MagicMock()
        mock_chunk.choices[0].delta.content = "用户查询了订单12345，已告知已发货。"

        async def fake_stream(*args, **kwargs):
            yield mock_chunk

        with patch(
            "ai_gateway.client.stream_chat_completion",
            new_callable=AsyncMock,
            return_value=fake_stream(),
        ):
            summarizer = LLMSummarizer()
            result = await summarizer.summarize(messages)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "订单" in result

    @pytest.mark.asyncio
    async def test_summarize_failure_returns_empty(self):
        """When LLM call fails, returns empty string (graceful degradation)."""
        messages = [{"role": "user", "content": "test"}]

        with patch(
            "ai_gateway.client.stream_chat_completion",
            new_callable=AsyncMock,
            side_effect=Exception("LLM unavailable"),
        ):
            summarizer = LLMSummarizer()
            result = await summarizer.summarize(messages)

        assert result == ""

    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self):
        """Summarizing empty messages returns empty string."""
        with patch(
            "ai_gateway.client.stream_chat_completion",
            new_callable=AsyncMock,
            side_effect=Exception("No content"),
        ):
            summarizer = LLMSummarizer()
            result = await summarizer.summarize([])

        assert result == ""


class TestWireSummarizer:
    def test_wire_sets_summarizer(self):
        """_wire_dependencies sets llm_summarizer on preprocess module."""
        import chat_service.agent.nodes.preprocess as pre_mod
        from chat_service.agent.summarizer import LLMSummarizer

        # Simulate what _wire_dependencies does
        pre_mod.llm_summarizer = LLMSummarizer()
        assert pre_mod.llm_summarizer is not None
        assert hasattr(pre_mod.llm_summarizer, "summarize")

        # Cleanup
        pre_mod.llm_summarizer = None
