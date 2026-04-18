"""Unit tests for chat_service/routes/ws_chat.py WebSocket endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from chat_service.routes.ws_chat import chat_websocket


@pytest.mark.asyncio
class TestChatWebSocket:
    async def test_sends_tokens_on_stream(self):
        """WebSocket sends token chunks from agent stream."""
        ws = AsyncMock()
        ws.app = MagicMock()

        # Mock receive_json to return one message then disconnect
        call_count = 0

        async def mock_receive():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"thread_id": "t1", "tenant_id": "tenant-a", "messages": []}
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect()

        ws.receive_json = mock_receive

        # Mock redis lock
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        redis = AsyncMock()
        redis.lock = MagicMock(return_value=lock)
        ws.app.state.redis = redis

        # Mock agent stream
        async def mock_stream(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello")}}
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content=" world")}}

        agent = MagicMock()
        agent.astream_events = mock_stream
        ws.app.state.agent = agent

        await chat_websocket(ws)

        ws.accept.assert_awaited_once()
        # Check tokens were sent
        calls = ws.send_json.call_args_list
        assert any(c.args[0] == {"content": "Hello"} for c in calls)
        assert any(c.args[0] == {"content": " world"} for c in calls)
        assert any(c.args[0] == {"done": True} for c in calls)

    async def test_concurrent_request_error(self):
        """WebSocket sends CONCURRENT_REQUEST when lock not acquired."""
        ws = AsyncMock()
        ws.app = MagicMock()

        call_count = 0

        async def mock_receive():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"thread_id": "t1", "tenant_id": "tenant-a", "messages": []}
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect()

        ws.receive_json = mock_receive

        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=False)
        redis = AsyncMock()
        redis.lock = MagicMock(return_value=lock)
        ws.app.state.redis = redis
        ws.app.state.agent = MagicMock()

        await chat_websocket(ws)

        calls = ws.send_json.call_args_list
        assert any(c.args[0] == {"error": "CONCURRENT_REQUEST"} for c in calls)

    async def test_lock_released_after_stream(self):
        """Redis lock is released after streaming completes."""
        ws = AsyncMock()
        ws.app = MagicMock()

        call_count = 0

        async def mock_receive():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"thread_id": "t1", "tenant_id": "tenant-a", "messages": []}
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect()

        ws.receive_json = mock_receive

        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        redis = AsyncMock()
        redis.lock = MagicMock(return_value=lock)
        ws.app.state.redis = redis

        async def mock_stream(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hi")}}

        agent = MagicMock()
        agent.astream_events = mock_stream
        ws.app.state.agent = agent

        await chat_websocket(ws)

        lock.release.assert_awaited_once()
