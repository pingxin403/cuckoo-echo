"""Property 30: Rate limit window invariant.

# Feature: cuckoo-echo, Property 30: 限流滑动窗口不变量
**Validates: Requirements 11.1, 11.2, 11.3**

Tests that the first `limit` requests pass (200) and subsequent requests
are rejected (429) with Retry-After header.
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings, HealthCheck, strategies as st
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import PlainTextResponse

from api_gateway.middleware.auth import TenantAuthMiddleware
from api_gateway.middleware.rate_limit import RateLimitMiddleware

VALID_KEY = "ck_test_key"
VALID_HASH = hashlib.sha256(VALID_KEY.encode()).hexdigest()
TENANT_ID = "tenant-1"


async def _ok(request):
    return PlainTextResponse("ok")


@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@given(limit=st.integers(1, 10), extra=st.integers(1, 5))
def test_rate_limit_window(limit, extra):
    """First `limit` requests return 200; next `extra` return 429 with Retry-After."""
    # Build counters: 1..limit pass, limit+1..limit+extra fail
    counters = list(range(1, limit + extra + 1))

    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=counters)
    redis.expire = AsyncMock()

    # Auth pool returns valid tenant
    auth_conn = AsyncMock()
    auth_conn.fetchrow = AsyncMock(
        return_value={"id": TENANT_ID, "status": "active"}
    )
    auth_acm = AsyncMock()
    auth_acm.__aenter__ = AsyncMock(return_value=auth_conn)
    auth_acm.__aexit__ = AsyncMock(return_value=False)
    auth_pool = MagicMock()
    auth_pool.acquire = MagicMock(return_value=auth_acm)

    # Rate limit pool returns config
    rl_conn = AsyncMock()
    rl_conn.fetchrow = AsyncMock(
        return_value={"rate_limit": f'{{"user_rps": {limit}}}'}
    )
    rl_acm = AsyncMock()
    rl_acm.__aenter__ = AsyncMock(return_value=rl_conn)
    rl_acm.__aexit__ = AsyncMock(return_value=False)
    rl_pool = MagicMock()
    rl_pool.acquire = MagicMock(return_value=rl_acm)

    app = Starlette(routes=[Route("/test", _ok)])
    app.add_middleware(RateLimitMiddleware, db_pool=rl_pool, redis=redis)
    app.add_middleware(TenantAuthMiddleware, db_pool=auth_pool)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {VALID_KEY}", "X-User-ID": "u1"}

    # Property: first `limit` requests return 200
    for i in range(limit):
        resp = client.get("/test", headers=headers)
        assert resp.status_code == 200, f"Request {i + 1}/{limit} should pass"

    # Property: next `extra` requests return 429
    for i in range(extra):
        resp = client.get("/test", headers=headers)
        assert resp.status_code == 429, f"Request {limit + i + 1} should be rate-limited"
        assert resp.headers.get("retry-after") == "1"
