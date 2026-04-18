"""Unit tests for the AI Gateway client and Langfuse handler.

Covers:
- Primary backend success — returns stream response
- Primary timeout triggers fallback within 3s
- stream_options includes usage tracking
- Langfuse handler created when keys configured, None when not
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_gateway.client import stream_chat_completion
from ai_gateway.langfuse_handler import get_langfuse_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MESSAGES = [{"role": "user", "content": "Hello"}]


def _fake_settings(**overrides):
    """Return a mock Settings object with sensible defaults."""
    defaults = {
        "llm_primary_model": "deepseek-chat",
        "llm_fallback_model": "qwen-plus",
        "llm_fallback_timeout": 3.0,
        "langfuse_public_key": "",
        "langfuse_secret_key": "",
        "langfuse_host": "http://localhost:3000",
    }
    defaults.update(overrides)
    settings = MagicMock()
    for k, v in defaults.items():
        setattr(settings, k, v)
    return settings


# ---------------------------------------------------------------------------
# stream_chat_completion tests
# ---------------------------------------------------------------------------


class TestStreamChatCompletion:
    @pytest.mark.asyncio
    async def test_primary_success_returns_stream(self):
        """Primary backend succeeds — returns the stream response directly."""
        mock_stream = MagicMock()

        async def fake_acompletion(**kwargs):
            return mock_stream

        with (
            patch("ai_gateway.client.get_settings", return_value=_fake_settings()),
            patch("ai_gateway.client.acompletion", side_effect=fake_acompletion),
        ):
            result = await stream_chat_completion(MESSAGES)
            assert result is mock_stream

    @pytest.mark.asyncio
    async def test_primary_timeout_triggers_fallback(self):
        """When primary times out, fallback model is called."""
        fallback_stream = AsyncMock()

        async def _slow_primary(**kwargs):
            await asyncio.sleep(10)  # Will be cancelled by wait_for

        with (
            patch("ai_gateway.client.get_settings", return_value=_fake_settings()),
            patch("ai_gateway.client.acompletion", new_callable=AsyncMock) as mock_acompletion,
        ):
            # First call (primary) raises TimeoutError via wait_for,
            # second call (fallback) succeeds.
            mock_acompletion.side_effect = [asyncio.TimeoutError(), fallback_stream]

            call_count = 0

            async def patched_wait_for(coro, *, timeout):
                nonlocal call_count
                call_count += 1
                # The coroutine from acompletion already raises TimeoutError
                # via side_effect, so just await it
                return await coro

            with patch("ai_gateway.client.asyncio.wait_for", side_effect=patched_wait_for):
                result = await stream_chat_completion(MESSAGES)

            assert result is fallback_stream
            # acompletion called twice: primary + fallback
            assert mock_acompletion.call_count == 2
            # Fallback call should use the fallback model
            fallback_call_kwargs = mock_acompletion.call_args_list[1]
            assert fallback_call_kwargs.kwargs.get("model") == "qwen-plus"

    @pytest.mark.asyncio
    async def test_primary_exception_triggers_fallback(self):
        """When primary raises a non-timeout exception, fallback is used."""
        fallback_stream = AsyncMock()

        with (
            patch("ai_gateway.client.get_settings", return_value=_fake_settings()),
            patch("ai_gateway.client.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("ai_gateway.client.asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for,
        ):
            mock_wait_for.side_effect = ConnectionError("LLM unreachable")
            mock_acompletion.return_value = fallback_stream

            result = await stream_chat_completion(MESSAGES)

            assert result is fallback_stream

    @pytest.mark.asyncio
    async def test_stream_options_include_usage(self):
        """stream_options={'include_usage': True} is passed to acompletion."""
        mock_stream = MagicMock()

        async def fake_acompletion(**kwargs):
            return mock_stream

        with (
            patch("ai_gateway.client.get_settings", return_value=_fake_settings()),
            patch("ai_gateway.client.acompletion", side_effect=fake_acompletion) as mock_ac,
        ):
            await stream_chat_completion(MESSAGES)
            mock_ac.assert_called_once()
            call_kwargs = mock_ac.call_args
            assert call_kwargs.kwargs["stream"] is True
            assert call_kwargs.kwargs["stream_options"] == {"include_usage": True}

    @pytest.mark.asyncio
    async def test_tenant_config_overrides_defaults(self):
        """Per-tenant LLM config overrides default model and temperature."""
        mock_stream = MagicMock()
        tenant_config = {
            "model": "gpt-4o",
            "fallback_model": "claude-3",
            "temperature": 0.3,
        }

        # Use a regular coroutine function to avoid unawaited coroutine warning
        # from AsyncMock. asyncio.wait_for expects a coroutine, so we provide one.
        async def fake_acompletion(**kwargs):
            return mock_stream

        with (
            patch("ai_gateway.client.get_settings", return_value=_fake_settings()),
            patch("ai_gateway.client.acompletion", side_effect=fake_acompletion) as mock_ac,
        ):
            await stream_chat_completion(MESSAGES, tenant_llm_config=tenant_config)
            call_kwargs = mock_ac.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["temperature"] == 0.3


# ---------------------------------------------------------------------------
# Langfuse handler tests
# ---------------------------------------------------------------------------


class TestLangfuseHandler:
    def test_returns_none_when_keys_not_configured(self):
        """When langfuse keys are empty, returns None."""
        with patch("ai_gateway.langfuse_handler.get_settings", return_value=_fake_settings()):
            handler = get_langfuse_handler(thread_id="t-123")
            assert handler is None

    def test_returns_none_when_only_public_key_set(self):
        """When only public key is set (no secret), returns None."""
        with patch(
            "ai_gateway.langfuse_handler.get_settings",
            return_value=_fake_settings(langfuse_public_key="pk-test"),
        ):
            handler = get_langfuse_handler()
            assert handler is None

    def test_returns_handler_when_keys_configured(self):
        """When both keys are set, returns a Langfuse client."""
        settings = _fake_settings(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )

        mock_client = MagicMock()

        with (
            patch("ai_gateway.langfuse_handler.get_settings", return_value=settings),
            patch("langfuse.Langfuse", return_value=mock_client) as mock_cls,
        ):
            handler = get_langfuse_handler(thread_id="t-456", span_name="test_span")

            assert handler is mock_client
            mock_cls.assert_called_once_with(
                public_key="pk-test",
                secret_key="sk-test",
                host="http://localhost:3000",
            )

    def test_returns_none_when_langfuse_not_installed(self):
        """When langfuse package is not installed, returns None gracefully."""
        settings = _fake_settings(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )

        with (
            patch("ai_gateway.langfuse_handler.get_settings", return_value=settings),
            patch.dict("sys.modules", {"langfuse": None, "langfuse.callback": None}),
        ):
            # Force re-import to trigger ImportError
            import importlib
            import ai_gateway.langfuse_handler as lf_mod

            importlib.reload(lf_mod)
            handler = lf_mod.get_langfuse_handler(thread_id="t-789")
            assert handler is None

            # Reload again to restore normal state
            importlib.reload(lf_mod)
