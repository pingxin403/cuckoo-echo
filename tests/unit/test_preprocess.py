"""Unit tests for preprocess node."""
from unittest.mock import AsyncMock, patch

import pytest

from chat_service.agent.nodes.preprocess import preprocess_node


class TestPreprocessNode:
    @pytest.mark.asyncio
    async def test_passthrough_no_media(self):
        state = {"messages": [{"role": "user", "content": "hello"}], "media_urls": []}
        result = await preprocess_node(state)
        assert result["messages"][0]["content"] == "hello"
        assert result["media_urls"] == []

    @pytest.mark.asyncio
    async def test_audio_triggers_asr(self):
        mock_asr = AsyncMock()
        mock_asr.transcribe.return_value = {"text": "transcribed text"}

        state = {
            "messages": [
                {
                    "role": "user",
                    "content": "",
                    "media": [{"type": "audio", "oss_url": "oss://audio.wav"}],
                }
            ],
            "media_urls": [],
        }
        with patch("chat_service.agent.nodes.preprocess.asr_client", mock_asr):
            result = await preprocess_node(state)
        assert result["messages"][-1]["content"] == "transcribed text"
        assert any(m["type"] == "audio" for m in result["media_urls"])

    @pytest.mark.asyncio
    async def test_image_without_oss_client(self):
        """Without oss_client, image URL is passed through as-is."""
        state = {
            "messages": [
                {
                    "role": "user",
                    "content": "look at this",
                    "media": [{"type": "image", "oss_url": "oss://img.png"}],
                }
            ],
            "media_urls": [],
        }
        result = await preprocess_node(state)
        assert any(m["type"] == "image" and m["url"] == "oss://img.png" for m in result["media_urls"])

    @pytest.mark.asyncio
    async def test_image_with_oss_client(self):
        """With oss_client, image gets a signed URL."""
        mock_oss = AsyncMock()
        mock_oss.get_signed_url.return_value = "https://signed.url/img.png"

        state = {
            "messages": [
                {
                    "role": "user",
                    "content": "look at this",
                    "media": [{"type": "image", "oss_url": "oss://img.png"}],
                }
            ],
            "media_urls": [],
        }
        with patch("chat_service.agent.nodes.preprocess.oss_client", mock_oss):
            result = await preprocess_node(state)
        assert any(m["url"] == "https://signed.url/img.png" for m in result["media_urls"])

    @pytest.mark.asyncio
    async def test_no_messages_passthrough(self):
        state = {"messages": [], "media_urls": []}
        result = await preprocess_node(state)
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_asr_failure_does_not_crash(self):
        """If ASR client raises, the node should not crash."""
        mock_asr = AsyncMock()
        mock_asr.transcribe.side_effect = RuntimeError("ASR down")

        state = {
            "messages": [
                {
                    "role": "user",
                    "content": "",
                    "media": [{"type": "audio", "oss_url": "oss://audio.wav"}],
                }
            ],
            "media_urls": [],
        }
        with patch("chat_service.agent.nodes.preprocess.asr_client", mock_asr):
            result = await preprocess_node(state)
        # Should not crash; content stays empty since ASR failed
        assert result["messages"][-1]["content"] == ""
