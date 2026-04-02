"""Unit tests for shared.redis_client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import shared.redis_client as redis_client_mod
from shared.redis_client import close_redis, get_redis


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the module-level singleton before each test."""
    redis_client_mod._client = None
    yield
    redis_client_mod._client = None


class TestGetRedis:
    @patch("shared.redis_client.get_settings")
    def test_uses_redis_url_from_settings(self, mock_get_settings) -> None:
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://prod:6379/1"
        mock_get_settings.return_value = mock_settings
        with patch("shared.redis_client.aioredis.from_url") as mock_from_url:
            get_redis()
            mock_from_url.assert_called_once_with("redis://prod:6379/1")

    @patch("shared.redis_client.get_settings")
    def test_default_url_when_env_missing(self, mock_get_settings) -> None:
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_get_settings.return_value = mock_settings
        with patch("shared.redis_client.aioredis.from_url") as mock_from_url:
            get_redis()
            mock_from_url.assert_called_once_with("redis://localhost:6379/0")

    def test_returns_same_client_on_subsequent_calls(self) -> None:
        with patch("shared.redis_client.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_get_settings.return_value = mock_settings
            with patch("shared.redis_client.aioredis.from_url") as mock_from_url:
                first = get_redis()
                second = get_redis()
                assert first is second
                mock_from_url.assert_called_once()


class TestCloseRedis:
    @pytest.mark.asyncio
    async def test_calls_aclose_on_client(self) -> None:
        mock_client = AsyncMock()
        redis_client_mod._client = mock_client

        await close_redis()

        mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resets_client_to_none(self) -> None:
        mock_client = AsyncMock()
        redis_client_mod._client = mock_client

        await close_redis()

        assert redis_client_mod._client is None

    @pytest.mark.asyncio
    async def test_noop_when_no_client(self) -> None:
        # Should not raise when _client is already None
        await close_redis()
        assert redis_client_mod._client is None
