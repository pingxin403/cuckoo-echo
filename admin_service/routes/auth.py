"""Admin authentication routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from shared.config import get_settings

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24h


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    db_pool = request.app.state.db_pool
    settings = get_settings()

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, tenant_id, password_hash, role FROM admin_users WHERE email = $1",
            body.email,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password (bcrypt)
    if not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT
    now = datetime.now(timezone.utc)
    payload = {
        "admin_user_id": str(row["id"]),
        "tenant_id": str(row["tenant_id"]),
        "role": row["role"],
        "exp": now + timedelta(hours=24),
        "iat": now,
    }
    token = jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")

    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request):
    # Re-issue token with fresh expiry
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "admin_user_id": request.state.admin_user_id,
        "tenant_id": request.state.tenant_id,
        "role": getattr(request.state, "role", "admin"),
        "exp": now + timedelta(hours=24),
        "iat": now,
    }
    token = jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")
    return TokenResponse(access_token=token)
