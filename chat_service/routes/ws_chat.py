"""WebSocket chat endpoint — bidirectional real-time chat."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.db import lock_key

log = structlog.get_logger()
router = APIRouter()

LOCK_TTL = 90  # seconds


@router.websocket("/v1/chat/ws")
async def chat_websocket(websocket: WebSocket):
    """Bidirectional WebSocket for real-time chat as alternative to SSE."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            thread_id = data.get("thread_id", "")
            tenant_id = data.get("tenant_id", "")
            messages = data.get("messages", [])

            # Get agent and redis from app state
            agent = websocket.app.state.agent
            redis = websocket.app.state.redis

            # Acquire distributed lock
            key = lock_key(thread_id)
            lock = redis.lock(key, timeout=LOCK_TTL)
            acquired = await lock.acquire(blocking=False)

            if not acquired:
                await websocket.send_json({"error": "CONCURRENT_REQUEST"})
                continue

            try:
                config = {"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}}
                async for chunk in agent.astream_events(
                    {"messages": messages}, config=config, version="v2"
                ):
                    if chunk["event"] == "on_chat_model_stream":
                        token = chunk["data"]["chunk"].content
                        if token:
                            await websocket.send_json({"content": token})
                await websocket.send_json({"done": True})
            finally:
                try:
                    await lock.release()
                except Exception:
                    pass
    except WebSocketDisconnect:
        log.info("ws_chat_disconnected")
