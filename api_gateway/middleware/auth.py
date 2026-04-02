"""Tenant authentication middleware.

Extracts Bearer token from Authorization header, computes SHA-256 hash,
and looks up the tenant in PostgreSQL. Attaches ``request.state.tenant_id``
on success; returns 401 on any authentication failure.
"""

from __future__ import annotations

import hashlib

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = structlog.get_logger()


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests via API key hash lookup against the tenants table."""

    def __init__(self, app, db_pool):
        super().__init__(app)
        self.db_pool = db_pool

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        api_key = auth.removeprefix("Bearer ")
        if not api_key:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        async with self.db_pool.acquire() as conn:
            tenant = await conn.fetchrow(
                "SELECT id, status FROM tenants WHERE api_key_hash = $1",
                key_hash,
            )

        if not tenant or tenant["status"] != "active":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        request.state.tenant_id = str(tenant["id"])
        log.info("tenant_authenticated", tenant_id=request.state.tenant_id)
        return await call_next(request)
