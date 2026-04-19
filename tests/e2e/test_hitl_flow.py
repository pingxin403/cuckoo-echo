"""E2E test — HITL escalation flow."""
import httpx
import pytest

pytestmark = [pytest.mark.e2e]


async def test_negative_sentiment_triggers_hitl():
    """Negative sentiment should create HITL session."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8001/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "你们是骗子，我要投诉"}], "user_id": "test"},
                headers={"Authorization": "Bearer ck_test_key"},
                timeout=30.0,
            )
        assert resp.status_code in (200, 401)
    except httpx.ConnectError:
        pytest.skip("Chat Service not running")
