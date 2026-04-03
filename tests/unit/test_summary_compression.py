"""Unit tests for preprocess summary compression.

Covers:
- Messages < 50 do not trigger summarization
- Messages >= 50 trigger summarization and compress messages
- Summary result stored in state["summary"]
- No summarizer configured: skip even when threshold exceeded
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import chat_service.agent.nodes.preprocess as pre_mod
from chat_service.agent.nodes.preprocess import preprocess_node, SUMMARIZE_THRESHOLD


def _base_state(num_messages: int = 1):
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(num_messages)
    ]
    return {
        "thread_id": "t-1",
        "tenant_id": "tenant-1",
        "user_id": "u-1",
        "messages": messages,
        "summary": None,
        "user_intent": None,
        "rag_context": [],
        "tool_calls": [],
        "media_urls": [],
        "hitl_requested": False,
        "tokens_used": 0,
        "llm_response": "",
        "guardrails_passed": True,
        "correction_message": None,
        "unresolved_turns": 0,
    }


class TestSummaryCompression:
    @pytest.mark.asyncio
    async def test_below_threshold_no_summary(self):
        """Messages below SUMMARIZE_THRESHOLD do not trigger summarization."""
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize = AsyncMock(return_value="summary text")

        original = pre_mod.llm_summarizer
        try:
            pre_mod.llm_summarizer = mock_summarizer
            state = _base_state(num_messages=SUMMARIZE_THRESHOLD - 1)

            result = await preprocess_node(state)

            mock_summarizer.summarize.assert_not_called()
            assert len(result["messages"]) == SUMMARIZE_THRESHOLD - 1
            assert result["summary"] is None
        finally:
            pre_mod.llm_summarizer = original

    @pytest.mark.asyncio
    async def test_at_threshold_triggers_summary(self):
        """Messages at SUMMARIZE_THRESHOLD trigger summarization."""
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize = AsyncMock(return_value="Compressed summary of 50 messages")

        original = pre_mod.llm_summarizer
        try:
            pre_mod.llm_summarizer = mock_summarizer
            state = _base_state(num_messages=SUMMARIZE_THRESHOLD)

            result = await preprocess_node(state)

            mock_summarizer.summarize.assert_called_once()
            assert result["messages"] == []
            assert result["summary"] == "Compressed summary of 50 messages"
        finally:
            pre_mod.llm_summarizer = original

    @pytest.mark.asyncio
    async def test_above_threshold_triggers_summary(self):
        """Messages above SUMMARIZE_THRESHOLD trigger summarization."""
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize = AsyncMock(return_value="Long conversation summary")

        original = pre_mod.llm_summarizer
        try:
            pre_mod.llm_summarizer = mock_summarizer
            state = _base_state(num_messages=SUMMARIZE_THRESHOLD + 10)

            result = await preprocess_node(state)

            mock_summarizer.summarize.assert_called_once()
            assert result["messages"] == []
            assert result["summary"] == "Long conversation summary"
        finally:
            pre_mod.llm_summarizer = original

    @pytest.mark.asyncio
    async def test_no_summarizer_skips(self):
        """When llm_summarizer is None, skip even if threshold exceeded."""
        original = pre_mod.llm_summarizer
        try:
            pre_mod.llm_summarizer = None
            state = _base_state(num_messages=SUMMARIZE_THRESHOLD + 5)

            result = await preprocess_node(state)

            # Messages unchanged
            assert len(result["messages"]) == SUMMARIZE_THRESHOLD + 5
            assert result["summary"] is None
        finally:
            pre_mod.llm_summarizer = original

    def test_threshold_value(self):
        """SUMMARIZE_THRESHOLD is 50 as specified in design."""
        assert SUMMARIZE_THRESHOLD == 50
