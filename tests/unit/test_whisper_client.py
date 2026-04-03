"""Unit tests for shared/whisper_client.py."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.whisper_client import WhisperClient


class TestWhisperClientRemote:
    @pytest.mark.asyncio
    async def test_remote_transcribe_success(self):
        client = WhisperClient(mode="remote", api_url="http://whisper:9000")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "hello world", "language": "en"}
        mock_resp.raise_for_status = MagicMock()

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("httpx.AsyncClient") as mock_httpx, \
             patch("builtins.open", return_value=mock_file):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=mock_resp)
            mock_httpx.return_value = mock_ctx

            result = await client.transcribe("/tmp/test.wav")

        assert result["text"] == "hello world"

    @pytest.mark.asyncio
    async def test_remote_transcribe_failure(self):
        client = WhisperClient(mode="remote", api_url="http://whisper:9000")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(side_effect=Exception("connection refused"))
            mock_httpx.return_value = mock_ctx

            with pytest.raises(Exception):
                await client.transcribe("/tmp/test.wav")


class TestWhisperClientLocal:
    @pytest.mark.asyncio
    async def test_local_raises_when_not_installed(self):
        client = WhisperClient(mode="local", model="tiny")

        with patch.dict("sys.modules", {"faster_whisper": None}):
            with pytest.raises(Exception):
                await client.transcribe("/tmp/test.wav")


class TestGetWhisperClient:
    def test_creates_client_from_settings(self):
        from shared.whisper_client import get_whisper_client

        client = get_whisper_client()
        assert isinstance(client, WhisperClient)
        assert client.mode in ("local", "remote")
