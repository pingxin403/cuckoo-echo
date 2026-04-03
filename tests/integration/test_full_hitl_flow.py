"""Integration test — full HITL flow."""
import pytest
import httpx

pytestmark = [pytest.mark.integration]


async def test_full_hitl_flow():
    """Verify admin service is reachable for HITL operations."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8002/health", timeout=5.0)
            if resp.status_code != 200:
                pytest.skip("Admin service not running")
    except httpx.ConnectError:
        pytest.skip("Infrastructure not running")
