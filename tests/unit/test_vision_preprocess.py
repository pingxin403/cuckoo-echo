"""Unit tests for Vision LLM integration in preprocess node.

Covers:
- Image message triggers Vision LLM call and augments content
- Text-only message does not trigger Vision LLM
- Vision LLM failure degrades gracefully to text-only
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import chat_service.agent.nodes.preprocess as pre_mod
from chat_service.agent.nodes.preprocess import preprocess_node


def _base_state(**overrides):
    state = {
        "thread_id": "t-1",
        "tenant_id": "tenant-1",
        "user_id": "u-1",
        "messages": [{"role": "user", "content": "Hello"}],
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
    state.update(overrides)
    return state


class TestVisionPreprocess:
    @pytest.mark.asyncio
    async def test_image_triggers_vision_llm(self):
        """Image in media triggers Vision LLM and augments message content."""
        mock_vision = AsyncMock()
        mock_vision.vision_completion = AsyncMock(return_value="一张产品图片，显示红色运动鞋")
        mock_oss = AsyncMock()
        mock_oss.get_signed_url = AsyncMock(return_value="https://oss.example.com/signed/img.jpg")

        original_vision = pre_mod.vision_client
        original_oss = pre_mod.oss_client
        try:
            pre_mod.vision_client = mock_vision
            pre_mod.oss_client = mock_oss

            state = _base_state(
                messages=[{
                    "role": "user",
                    "content": "这个鞋子有什么颜色？",
                    "media": [{"type": "image", "oss_url": "tenant-1/img/shoe.jpg"}],
                }]
            )

            result = await preprocess_node(state)

            mock_vision.vision_completion.assert_called_once()
            assert "图片内容" in result["messages"][-1]["content"]
            assert "红色运动鞋" in result["messages"][-1]["content"]
            assert len(result["media_urls"]) == 1
            assert result["media_urls"][0]["type"] == "image"
        finally:
            pre_mod.vision_client = original_vision
            pre_mod.oss_client = original_oss

    @pytest.mark.asyncio
    async def test_text_only_no_vision_call(self):
        """Text-only message does not trigger Vision LLM."""
        mock_vision = AsyncMock()
        mock_vision.vision_completion = AsyncMock()

        original_vision = pre_mod.vision_client
        try:
            pre_mod.vision_client = mock_vision

            state = _base_state(
                messages=[{"role": "user", "content": "你好，请问退货政策是什么？"}]
            )

            result = await preprocess_node(state)

            mock_vision.vision_completion.assert_not_called()
            assert result["messages"][-1]["content"] == "你好，请问退货政策是什么？"
        finally:
            pre_mod.vision_client = original_vision

    @pytest.mark.asyncio
    async def test_vision_failure_degrades_gracefully(self):
        """When Vision LLM fails, message content is unchanged (no crash)."""
        mock_vision = AsyncMock()
        mock_vision.vision_completion = AsyncMock(side_effect=Exception("Vision API down"))
        mock_oss = AsyncMock()
        mock_oss.get_signed_url = AsyncMock(return_value="https://oss.example.com/signed/img.jpg")

        original_vision = pre_mod.vision_client
        original_oss = pre_mod.oss_client
        try:
            pre_mod.vision_client = mock_vision
            pre_mod.oss_client = mock_oss

            state = _base_state(
                messages=[{
                    "role": "user",
                    "content": "这是什么？",
                    "media": [{"type": "image", "oss_url": "tenant-1/img/unknown.jpg"}],
                }]
            )

            result = await preprocess_node(state)

            # Should not crash, content unchanged (no augmentation)
            assert "图片内容" not in result["messages"][-1]["content"]
            # Image URL still recorded
            assert len(result["media_urls"]) == 1
        finally:
            pre_mod.vision_client = original_vision
            pre_mod.oss_client = original_oss

    @pytest.mark.asyncio
    async def test_no_vision_client_skips_description(self):
        """When vision_client is None, image is uploaded but no description generated."""
        mock_oss = AsyncMock()
        mock_oss.get_signed_url = AsyncMock(return_value="https://oss.example.com/signed/img.jpg")

        original_vision = pre_mod.vision_client
        original_oss = pre_mod.oss_client
        try:
            pre_mod.vision_client = None
            pre_mod.oss_client = mock_oss

            state = _base_state(
                messages=[{
                    "role": "user",
                    "content": "看看这个",
                    "media": [{"type": "image", "oss_url": "tenant-1/img/item.jpg"}],
                }]
            )

            result = await preprocess_node(state)

            assert result["messages"][-1]["content"] == "看看这个"
            assert len(result["media_urls"]) == 1
        finally:
            pre_mod.vision_client = original_vision
            pre_mod.oss_client = original_oss
