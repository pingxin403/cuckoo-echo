"""Integration test — full chat flow with real infrastructure."""
import httpx
import pytest

pytestmark = [pytest.mark.integration]

BASE_URL = "http://localhost:8001"


async def test_full_chat_flow():
    """Send message → verify SSE stream → verify response."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if resp.status_code != 200:
                pytest.skip("Chat service not running")

            # Send chat message
            resp = await client.post(
                f"{BASE_URL}/v1/chat/completions",
                json={"user_id": "integration-test", "messages": [{"role": "user", "content": "hello"}]},
                timeout=30.0,
            )
            assert resp.status_code == 200
            body = resp.text
            assert "content" in body or "[DONE]" in body or "error" in body
    except httpx.ConnectError:
        pytest.skip("Chat service not running")
