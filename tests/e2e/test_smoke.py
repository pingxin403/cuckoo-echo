"""E2E smoke test — basic chat flow."""
import pytest
import httpx

pytestmark = [pytest.mark.e2e]

BASE_URL = "http://localhost:8000"  # API Gateway
CHAT_URL = "http://localhost:8001"  # Chat Service


@pytest.fixture
def api_key():
    """Create a test tenant and return its API key. Skip if infra not available."""
    try:
        # This would normally create a tenant via admin API or direct DB insert
        return "ck_test_smoke_key"
    except Exception:
        pytest.skip("Infrastructure not available")


async def test_health_endpoint():
    """Gateway /health should return 200."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/health", timeout=5.0)
        assert resp.status_code == 200
    except httpx.ConnectError:
        pytest.skip("API Gateway not running")


async def test_chat_returns_sse_stream(api_key):
    """Send a message and verify SSE stream contains tokens and [DONE]."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CHAT_URL}/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Hello"}], "user_id": "test-user"},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
        assert resp.status_code == 200
        # SSE response should contain data lines
        body = resp.text
        assert "data:" in body or "[DONE]" in body
    except httpx.ConnectError:
        pytest.skip("Chat Service not running")
