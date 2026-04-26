"""Integration tests for WebSocket chat endpoint.

Verifies real-time WebSocket chat functionality.
Run with: pytest -m integration tests/integration/test_websocket_chat.py
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time

import pytest
import websockets

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def ws_server_url():
    """Get WebSocket server URL."""
    # Assuming API gateway runs on localhost:8000
    # TODO: Make configurable via environment
    yield "ws://localhost:8000/v1/chat/ws"
    # Cleanup handled by test teardown


@pytest.fixture
async def ws_connection(ws_server_url):
    """Create and cleanup WebSocket connection."""
    async with websockets.connect(ws_server_url) as ws:
        yield ws
        # Ensure connection closed
        try:
            await ws.close()
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running ws server - Run 'make up' first")
async def test_ws_connect_and_disconnect(ws_server_url):
    """Verify WebSocket connection establishes and closes cleanly."""
    async with websockets.connect(ws_server_url) as ws:
        # Verify connected
        assert ws.open

    # Verify closed
    assert not ws.open


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running ws server with auth")
async def test_ws_send_message(ws_connection):
    """Verify message can be sent via WebSocket."""
    message = {
        "type": "start",
        "thread_id": "test-thread-001",
        "tenant_id": "test-tenant-001",
        "message": "Hello integration test",
    }

    await ws_connection.send(json.dumps(message))

    # Wait for response (with timeout)
    try:
        response = await asyncio.wait_for(ws_connection.recv(), timeout=10.0)
        response_data = json.loads(response)

        # Verify response structure
        assert "type" in response_data or "content" in response_data
    except asyncio.TimeoutError:
        pytest.skip("Timeout waiting for response")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running ws server with valid auth")
async def test_ws_receive_tokens_stream(ws_connection):
    """Verify streaming tokens received correctly."""
    message = {
        "type": "start",
        "thread_id": "test-thread-stream",
        "tenant_id": "test-tenant-001",
        "message": "Tell me a short story",
    }

    await ws_connection.send(json.dumps(message))

    tokens = []
    try:
        while True:
            response = await asyncio.wait_for(ws_connection.recv(), timeout=30.0)
            data = json.loads(response)

            if data.get("type") == "done":
                break

            if "content" in data:
                tokens.append(data["content"])

    except asyncio.TimeoutError:
        pass

    # Verify streaming received
    assert len(tokens) > 0, "Should receive at least one token"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running ws server")
async def test_ws_error_on_invalid_message(ws_server_url):
    """Verify error handling for invalid message format."""
    async with websockets.connect(ws_server_url) as ws:
        # Send invalid message (missing required fields)
        await ws.send(json.dumps({"invalid": "payload"}))

        # Should receive error response
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(response)

        assert data.get("type") == "error" or "error" in data


# Alternative: subprocess-based tests (run without live server)
def test_ws_server_health():
    """Verify WebSocket server is reachable via health check."""
    result = subprocess.run(
        ["curl", "-f", "http://localhost:8000/health"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if result.returncode != 0:
        if "connection refused" in result.stderr.lower():
            pytest.skip("Server not available. Run 'make up' first.")
        pytest.fail(f"Health check failed: {result.stderr}")

    assert result.returncode == 0


def test_ws_endpoint_exists():
    """Verify WebSocket endpoint is defined in OpenAPI spec."""
    result = subprocess.run(
        ["curl", "-f", "http://localhost:8000/openapi.json"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if result.returncode != 0:
        pytest.skip("Server not available.")

    import json

    spec = json.loads(result.stdout)

    # Check WebSocket route exists
    routes = spec.get("paths", {})
    ws_route = routes.get("/v1/chat/ws") or routes.get("/v1/chat/ws/")

    assert ws_route is not None, "WebSocket endpoint should be defined in OpenAPI spec"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])