"""Two-tier rate limiting middleware.

Tier 1 — Local in-memory ``TokenBucket`` per ``(tenant_id, user_id)`` pair
acts as a coarse filter to avoid hitting Redis on every request.

Tier 2 — Redis ``INCR`` + ``EXPIRE 1`` fixed-window counter provides the
precise, cluster-wide rate limit check.

Key format: ``cuckoo:ratelimit:{tenant_id}:{user_id}``
Returns 429 with ``Retry-After: 1`` header when the limit is breached.
Per-tenant thresholds are loaded from ``tenants.rate_limit`` JSONB column
(default: ``{"tenant_rps": 100, "user_rps": 10}``).
"""

from __future__ import annotations

import time
from collections import defaultdict

import orjson
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = structlog.get_logger()

_RATE_LIMIT_RESPONSE = JSONResponse(
    status_code=429,
    content={"error": "Rate limit exceeded"},
    headers={"Retry-After": "1"},
)


class TokenBucket:
    """Simple token-bucket rate limiter for local coarse filtering."""

    __slots__ = ("capacity", "tokens", "last_refill")

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.capacity)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Two-tier rate limiter: local TokenBucket + Redis fixed-window."""

    def __init__(self, app, db_pool, redis):
        super().__init__(app)
        self.db_pool = db_pool
        self.redis = redis
        # Local buckets keyed by (tenant_id, user_id)
        self._buckets: dict[str, TokenBucket] = defaultdict(lambda: TokenBucket(10))

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            # Auth middleware should have set this; pass through
            return await call_next(request)

        user_id = self._extract_user_id(request)

        # Load per-tenant threshold
        user_rps = await self._get_user_rps(tenant_id)

        # Tier 1: Local token bucket coarse filter
        bucket_key = f"{tenant_id}:{user_id}"
        bucket = self._buckets[bucket_key]
        # Adjust capacity if tenant config changed
        if bucket.capacity != user_rps:
            self._buckets[bucket_key] = TokenBucket(user_rps)
            bucket = self._buckets[bucket_key]

        if not bucket.allow():
            log.warning("rate_limit_local", tenant_id=tenant_id, user_id=user_id)
            return _RATE_LIMIT_RESPONSE

        # Tier 2: Redis fixed-window precise check
        redis_key = f"cuckoo:ratelimit:{tenant_id}:{user_id}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, 1)

        if count > user_rps:
            log.warning("rate_limit_redis", tenant_id=tenant_id, user_id=user_id, count=count)
            return _RATE_LIMIT_RESPONSE

        return await call_next(request)

    def _extract_user_id(self, request: Request) -> str:
        """Extract user_id from X-User-ID header, falling back to 'anonymous'."""
        return request.headers.get("X-User-ID", "anonymous")

    async def _get_user_rps(self, tenant_id: str) -> int:
        """Load per-tenant user RPS from the tenants table."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT rate_limit FROM tenants WHERE id = $1",
                tenant_id,
            )
        if row and row["rate_limit"]:
            rl = row["rate_limit"]
            # rate_limit column is JSONB — asyncpg returns it as a string or dict
            if isinstance(rl, str):
                rl = orjson.loads(rl)
            return rl.get("user_rps", 10)
        return 10
