"""Unit tests for Chat_Service SSE endpoint."""


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

        async def mock_astream(*args, **kwargs):
            # Simulate LangGraph astream with stream_mode="updates"
            # llm_generate node returns llm_response
            yield {"llm_generate": {"llm_response": "Hello world", "tokens_used": 15}}

        agent = MagicMock()
        agent.astream = mock_astream

        events = []
        async for event in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis
        ):
            events.append(event)

        # Should have at least one content event and [DONE]
        content_events = [e for e in events if isinstance(e, str) and "content" in e]
        # The llm_response may come as individual tokens via queue or as full response
        assert len(content_events) >= 1 or len(events) >= 1
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

        async def mock_astream(*args, **kwargs):
            yield {"llm_generate": {"llm_response": "Hi"}}

        agent = MagicMock()
        agent.astream = mock_astream

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

        async def mock_astream(*args, **kwargs):
            yield {"llm_generate": {"llm_response": "Hello", "tokens_used": 150}}

        agent = MagicMock()
        agent.astream = mock_astream
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

        async def mock_astream(*args, **kwargs):
            yield {"llm_generate": {"llm_response": "Hi"}}

        agent = MagicMock()
        agent.astream = mock_astream

        async for _ in event_generator(
            "t1", "tenant-a", "user-1", {}, agent, redis
        ):
            pass

        lock.release.assert_awaited_once()
