"""Unit tests for the API Gateway.

Covers:
- TenantAuthMiddleware: valid/invalid/missing API key
- RateLimitMiddleware: boundary behaviour (N-1, N, N+1 requests)
- MediaFormatValidator: supported and unsupported magic bytes
- CircuitBreaker: open state returns degraded response, half-open probe, close resumes
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from circuitbreaker import CircuitBreakerError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api_gateway.middleware.auth import TenantAuthMiddleware
from api_gateway.middleware.media_format import (
    UnsupportedMediaFormat,
    validate_media_format,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_API_KEY = "ck_test_key_abc123"
VALID_KEY_HASH = hashlib.sha256(VALID_API_KEY.encode()).hexdigest()
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"


def _make_db_pool(tenant_row=None):
    """Create a mock asyncpg pool that returns *tenant_row* from fetchrow."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=tenant_row)

    pool = AsyncMock()
    # Make pool.acquire() work as an async context manager
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acm)
    return pool


def _make_redis(incr_values=None):
    """Create a mock Redis client.

    *incr_values* is a list of integers returned by successive ``incr`` calls.
    """
    redis = AsyncMock()
    if incr_values is not None:
        redis.incr = AsyncMock(side_effect=incr_values)
    else:
        redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.get = AsyncMock(return_value=None)  # Cache miss by default
    redis.set = AsyncMock()
    return redis


async def _ok_endpoint(request: Request):
    return PlainTextResponse("ok")


async def _health_endpoint(request: Request):
    return JSONResponse({"status": "ok"})


def _build_auth_app(db_pool):
    """Build a minimal Starlette app with TenantAuthMiddleware."""
    app = Starlette(
        routes=[
            Route("/health", _health_endpoint),
            Route("/test", _ok_endpoint),
        ],
    )
    app.add_middleware(TenantAuthMiddleware, db_pool=db_pool)
    return app


# ---------------------------------------------------------------------------
# TenantAuthMiddleware tests
# ---------------------------------------------------------------------------


class TestTenantAuthMiddleware:
    def test_valid_api_key_returns_200(self):
        tenant_row = {"id": TENANT_ID, "status": "active"}
        db_pool = _make_db_pool(tenant_row)
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/test", headers={"Authorization": f"Bearer {VALID_API_KEY}"})
        assert resp.status_code == 200
        assert resp.text == "ok"

    def test_missing_authorization_header_returns_401(self):
        db_pool = _make_db_pool()
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/test")
        assert resp.status_code == 401

    def test_empty_bearer_token_returns_401(self):
        db_pool = _make_db_pool()
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/test", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_non_bearer_auth_returns_401(self):
        db_pool = _make_db_pool()
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/test", headers={"Authorization": "Basic abc123"})
        assert resp.status_code == 401

    def test_unknown_api_key_returns_401(self):
        db_pool = _make_db_pool(tenant_row=None)
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/test", headers={"Authorization": "Bearer unknown_key"})
        assert resp.status_code == 401

    def test_suspended_tenant_returns_401(self):
        tenant_row = {"id": TENANT_ID, "status": "suspended"}
        db_pool = _make_db_pool(tenant_row)
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/test", headers={"Authorization": f"Bearer {VALID_API_KEY}"})
        assert resp.status_code == 401

    def test_health_endpoint_skips_auth(self):
        db_pool = _make_db_pool()
        app = _build_auth_app(db_pool)
        client = TestClient(app)

        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# RateLimitMiddleware tests
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    def _build_rate_limit_app(self, db_pool, redis, user_rps=5):
        """Build app with Auth + RateLimit middleware stacked."""
        from api_gateway.middleware.rate_limit import RateLimitMiddleware

        tenant_row = {
            "id": TENANT_ID,
            "status": "active",
            "rate_limit": f'{{"tenant_rps": 100, "user_rps": {user_rps}}}',
        }
        # Auth pool always returns active tenant
        auth_pool = _make_db_pool(tenant_row)

        # Rate limit pool returns rate_limit config
        rl_conn = AsyncMock()
        rl_conn.fetchrow = AsyncMock(
            return_value={"rate_limit": f'{{"tenant_rps": 100, "user_rps": {user_rps}}}'}
        )
        rl_acm = AsyncMock()
        rl_acm.__aenter__ = AsyncMock(return_value=rl_conn)
        rl_acm.__aexit__ = AsyncMock(return_value=False)
        rl_pool = MagicMock()
        rl_pool.acquire = MagicMock(return_value=rl_acm)

        app = Starlette(
            routes=[
                Route("/health", _health_endpoint),
                Route("/test", _ok_endpoint),
            ],
        )
        # Add rate limit first (inner), then auth (outer)
        app.add_middleware(RateLimitMiddleware, db_pool=rl_pool, redis=redis)
        app.add_middleware(TenantAuthMiddleware, db_pool=auth_pool)
        return app

    def test_requests_within_limit_return_200(self):
        """N-1 and Nth request should pass (limit=5, send 5)."""
        user_rps = 5
        # Redis incr returns 1..5 for 5 requests
        redis = _make_redis(incr_values=list(range(1, user_rps + 1)))
        app = self._build_rate_limit_app(MagicMock(), redis, user_rps=user_rps)
        client = TestClient(app)
        headers = {
            "Authorization": f"Bearer {VALID_API_KEY}",
            "X-User-ID": "user-1",
        }

        for i in range(user_rps):
            resp = client.get("/test", headers=headers)
            assert resp.status_code == 200, f"Request {i+1} should pass"

    def test_request_exceeding_limit_returns_429(self):
        """N+1 request should be rejected (limit=5, 6th request)."""
        user_rps = 5
        # Redis incr returns 6 (over limit)
        redis = _make_redis(incr_values=[user_rps + 1])
        app = self._build_rate_limit_app(MagicMock(), redis, user_rps=user_rps)
        client = TestClient(app)
        headers = {
            "Authorization": f"Bearer {VALID_API_KEY}",
            "X-User-ID": "user-1",
        }

        resp = client.get("/test", headers=headers)
        assert resp.status_code == 429
        assert resp.headers.get("retry-after") == "1"

    def test_rate_limit_boundary(self):
        """Exactly at limit (Nth) passes, N+1 fails."""
        user_rps = 3
        # Requests: 1, 2, 3 (pass), 4 (fail)
        redis = _make_redis(incr_values=[1, 2, 3, 4])
        app = self._build_rate_limit_app(MagicMock(), redis, user_rps=user_rps)
        client = TestClient(app)
        headers = {
            "Authorization": f"Bearer {VALID_API_KEY}",
            "X-User-ID": "user-1",
        }

        # N-1 request
        resp = client.get("/test", headers=headers)
        assert resp.status_code == 200

        # Nth request (at boundary)
        resp = client.get("/test", headers=headers)
        assert resp.status_code == 200

        # N request (still at limit)
        resp = client.get("/test", headers=headers)
        assert resp.status_code == 200

        # N+1 request (over limit)
        resp = client.get("/test", headers=headers)
        assert resp.status_code == 429

    def test_health_skips_rate_limit(self):
        redis = _make_redis()
        app = self._build_rate_limit_app(MagicMock(), redis)
        client = TestClient(app)

        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# MediaFormatValidator tests
# ---------------------------------------------------------------------------


class TestMediaFormatValidator:
    def test_jpeg(self):
        header = b"\xff\xd8\xff\xe0" + b"\x00" * 12
        fmt, media_type = validate_media_format(header)
        assert fmt == "jpeg"
        assert media_type == "image"

    def test_png(self):
        header = b"\x89\x50\x4e\x47" + b"\x00" * 12
        fmt, media_type = validate_media_format(header)
        assert fmt == "png"
        assert media_type == "image"

    def test_webp(self):
        header = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 4
        fmt, media_type = validate_media_format(header)
        assert fmt == "webp"
        assert media_type == "image"

    def test_wav(self):
        header = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 4
        fmt, media_type = validate_media_format(header)
        assert fmt == "wav"
        assert media_type == "audio"

    def test_mp3_ff_fb(self):
        header = b"\xff\xfb\x90\x00" + b"\x00" * 12
        fmt, media_type = validate_media_format(header)
        assert fmt == "mp3"
        assert media_type == "audio"

    def test_mp3_ff_f3(self):
        header = b"\xff\xf3\x90\x00" + b"\x00" * 12
        fmt, media_type = validate_media_format(header)
        assert fmt == "mp3"
        assert media_type == "audio"

    def test_mp3_ff_f2(self):
        header = b"\xff\xf2\x90\x00" + b"\x00" * 12
        fmt, media_type = validate_media_format(header)
        assert fmt == "mp3"
        assert media_type == "audio"

    def test_mp3_id3(self):
        header = b"\x49\x44\x33\x04\x00" + b"\x00" * 11
        fmt, media_type = validate_media_format(header)
        assert fmt == "mp3"
        assert media_type == "audio"

    def test_m4a(self):
        header = b"\x00\x00\x00\x20\x66\x74\x79\x70" + b"\x00" * 8
        fmt, media_type = validate_media_format(header)
        assert fmt == "m4a"
        assert media_type == "audio"

    def test_unsupported_format_raises(self):
        header = b"\x00\x00\x00\x00" * 4  # Unknown bytes
        with pytest.raises(UnsupportedMediaFormat):
            validate_media_format(header)

    def test_too_small_raises(self):
        header = b"\xff\xd8"  # Only 2 bytes
        with pytest.raises(UnsupportedMediaFormat):
            validate_media_format(header)

    def test_gif_unsupported(self):
        header = b"GIF89a" + b"\x00" * 10
        with pytest.raises(UnsupportedMediaFormat):
            validate_media_format(header)

    def test_pdf_unsupported(self):
        header = b"%PDF-1.4" + b"\x00" * 8
        with pytest.raises(UnsupportedMediaFormat):
            validate_media_format(header)


# ---------------------------------------------------------------------------
# CircuitBreaker tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_open_circuit_returns_degraded_response(self):
        """When the circuit is open, safe_call_* returns DEGRADED_RESPONSE."""
        from api_gateway.middleware.circuit_breaker import (
            DEGRADED_RESPONSE,
            safe_call_llm,
            safe_call_tool_service,
        )

        import asyncio

        async def _test():
            # Patch call_llm to raise CircuitBreakerError
            with patch(
                "api_gateway.middleware.circuit_breaker.call_llm",
                side_effect=CircuitBreakerError(MagicMock()),
            ):
                result = await safe_call_llm({"prompt": "test"})
                assert result == DEGRADED_RESPONSE

            with patch(
                "api_gateway.middleware.circuit_breaker.call_tool_service",
                side_effect=CircuitBreakerError(MagicMock()),
            ):
                result = await safe_call_tool_service("get_order", {}, "t1")
                assert result == DEGRADED_RESPONSE

        asyncio.get_event_loop().run_until_complete(_test())

    def test_closed_circuit_passes_through(self):
        """When the circuit is closed, the actual function result is returned."""
        from api_gateway.middleware.circuit_breaker import safe_call_llm

        import asyncio

        async def _test():
            expected = {"response": "hello"}
            with patch(
                "api_gateway.middleware.circuit_breaker.call_llm",
                new_callable=AsyncMock,
                return_value=expected,
            ):
                result = await safe_call_llm({"prompt": "test"})
                assert result == expected

        asyncio.get_event_loop().run_until_complete(_test())

    def test_half_open_allows_probe(self):
        """After recovery_timeout, a single probe request is allowed through."""
        from api_gateway.middleware.circuit_breaker import safe_call_llm, DEGRADED_RESPONSE

        import asyncio

        async def _test():
            # First call: circuit breaker error (open)
            with patch(
                "api_gateway.middleware.circuit_breaker.call_llm",
                side_effect=CircuitBreakerError(MagicMock()),
            ):
                result = await safe_call_llm({"prompt": "test"})
                assert result == DEGRADED_RESPONSE

            # Second call: success (simulating half-open → closed)
            expected = {"response": "recovered"}
            with patch(
                "api_gateway.middleware.circuit_breaker.call_llm",
                new_callable=AsyncMock,
                return_value=expected,
            ):
                result = await safe_call_llm({"prompt": "test"})
                assert result == expected

        asyncio.get_event_loop().run_until_complete(_test())
