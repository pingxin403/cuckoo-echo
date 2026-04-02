"""Unit tests for Chat_Service SSE endpoint."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from chat_service.routes.chat import event_generator


@pytest.mark.asyncio
class TestEventGenerator:
    async def test_lock_acquired_yields_tokens(self):
        """When lock is acquired, tokens from agent stream are yielded."""
        redis = AsyncMock()
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        redis.lock = MagicMock(return_value=lock)

        async def mock_stream(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Hello")},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content=" world")},
            }
            yield {
                "event": "on_llm_end",
                "data": {
                    "output": {
                        "usage_metadata": {
                            "input_tokens": 10,
                            "output_tokens": 5,
                        }
                    }
                },
            }

        agent = MagicMock()
        agent.astream_events = mock_stream

        events = []
        async for event in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis
        ):
            events.append(event)

        assert any('"content":"Hello"' in e for e in events)
        assert any('"content":" world"' in e for e in events)
        assert events[-1] == "[DONE]"

    async def test_lock_not_acquired_yields_error(self):
        """When lock is NOT acquired, yield CONCURRENT_REQUEST error."""
        redis = AsyncMock()
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=False)
        redis.lock = MagicMock(return_value=lock)

        agent = MagicMock()

        events = []
        async for event in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis
        ):
            events.append(event)

        assert len(events) == 1
        assert "CONCURRENT_REQUEST" in events[0]

    async def test_done_is_last_event(self):
        """[DONE] must be the last event in a successful stream."""
        redis = AsyncMock()
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        redis.lock = MagicMock(return_value=lock)

        async def mock_stream(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Hi")},
            }

        agent = MagicMock()
        agent.astream_events = mock_stream

        events = []
        async for event in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis
        ):
            events.append(event)

        assert events[-1] == "[DONE]"

    async def test_billing_called_in_finally(self):
        """billing_service.record_usage called when tokens_used > 0."""
        redis = AsyncMock()
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        redis.lock = MagicMock(return_value=lock)

        async def mock_stream(*args, **kwargs):
            yield {
                "event": "on_llm_end",
                "data": {
                    "output": {
                        "usage_metadata": {
                            "input_tokens": 100,
                            "output_tokens": 50,
                        }
                    }
                },
            }

        agent = MagicMock()
        agent.astream_events = mock_stream
        billing = AsyncMock()

        events = []
        async for event in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis, billing_service=billing
        ):
            events.append(event)

        billing.record_usage.assert_awaited_once_with("t1", "tenant-a", 150)

    async def test_lock_released_in_finally(self):
        """Redis lock is always released after streaming."""
        redis = AsyncMock()
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        redis.lock = MagicMock(return_value=lock)

        async def mock_stream(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Hi")},
            }

        agent = MagicMock()
        agent.astream_events = mock_stream

        async for _ in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis
        ):
            pass

        lock.release.assert_awaited_once()
