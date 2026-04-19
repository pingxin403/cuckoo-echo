"""E2E test — login flow."""
import httpx
import pytest

pytestmark = [pytest.mark.e2e]

BASE_URL = "http://localhost:8000"  # API Gateway


async def test_login_success():
    """Login with valid credentials should redirect to dashboard."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.post(
                f"{BASE_URL}/auth/v1/login",
                json={"email": "admin@example.com", "password": "admin123"},
                timeout=10.0,
            )
        assert resp.status_code == 200
        # Should redirect to dashboard or return token
        assert "token" in resp.json() or "/dashboard" in resp.text
    except httpx.ConnectError:
        pytest.skip("API Gateway not running")


async def test_login_invalid_credentials():
    """Login with invalid credentials should return error."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/auth/v1/login",
                json={"email": "admin@example.com", "password": "wrongpassword"},
                timeout=10.0,
            )
        assert resp.status_code == 401
    except httpx.ConnectError:
        pytest.skip("API Gateway not running")