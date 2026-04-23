"""JWT authentication middleware for Admin Service."""
from __future__ import annotations

import jwt
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.config import get_settings

log = structlog.get_logger()

EXEMPT_PATHS = {"/health", "/admin/v1/auth/login", "/docs", "/openapi.json"}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Missing token"})

        token = auth[7:] if auth.startswith("Bearer ") else auth
        settings = get_settings()
        secret = settings.admin_jwt_secret

        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            request.state.tenant_id = payload.get("tenant_id", "")
            request.state.admin_user_id = payload.get("admin_user_id", "")
            request.state.role = payload.get("role", "admin")
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"error": "Token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})

        return await call_next(request)
