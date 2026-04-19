"""Property 4: Invalid API key rejected.

# Feature: cuckoo-echo, Property 4: 无效 API Key 拒绝
**Validates: Requirements 1.2**
"""

from unittest.mock import AsyncMock, MagicMock

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api_gateway.middleware.auth import TenantAuthMiddleware


async def _ok(request):
    return PlainTextResponse("ok")


def _build_app():
    db_pool = MagicMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)  # No tenant found
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    db_pool.acquire = MagicMock(return_value=acm)
    app = Starlette(routes=[Route("/test", _ok)])
    app.add_middleware(TenantAuthMiddleware, db_pool=db_pool)
    return app


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    api_key=st.one_of(
        st.just(""),
        st.text(
            min_size=1,
            max_size=64,
            alphabet=st.characters(whitelist_categories=("L", "N", "P"), max_codepoint=127),
        ),
        st.binary(min_size=1).map(lambda b: b.hex()),
    )
)
def test_invalid_api_key_rejected(api_key):
    """Any unregistered API key must be rejected with HTTP 401."""
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/test", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 401
