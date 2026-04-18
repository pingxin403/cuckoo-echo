"""Unit tests for Admin JWT Authentication (Task 29)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import jwt
from fastapi import FastAPI
from starlette.requests import Request
from starlette.testclient import TestClient

from admin_service.middleware.jwt_auth import JWTAuthMiddleware
from admin_service.routes.auth import router as auth_router

TEST_SECRET = "test-jwt-secret-key-that-is-long-enough-for-hs256"

_mock_settings = MagicMock()
_mock_settings.admin_jwt_secret = TEST_SECRET


def _build_app(db_pool=None):
    """Build a test FastAPI app with JWT middleware and auth routes."""
    app = FastAPI()
    app.add_middleware(JWTAuthMiddleware)
    app.include_router(auth_router)
    app.state.db_pool = db_pool or MagicMock()

    @app.get("/admin/v1/protected")
    async def protected(request: Request):
        return {
            "tenant_id": request.state.tenant_id,
            "admin_user_id": request.state.admin_user_id,
            "role": request.state.role,
        }

    return app


def _mock_pool(mock_conn=None):
    conn = mock_conn or AsyncMock()
    pool = MagicMock()
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acm)
    return pool, conn


def _make_token(payload: dict, secret: str = TEST_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def _valid_payload(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    base = {
        "admin_user_id": "user-123",
        "tenant_id": "tenant-abc",
        "role": "admin",
        "exp": now + timedelta(hours=24),
        "iat": now,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# JWT Middleware Tests
# ---------------------------------------------------------------------------


@patch("admin_service.middleware.jwt_auth.get_settings", return_value=_mock_settings)
class TestJWTMiddlewareValidToken:
    def test_valid_token_passes_through(self, _patched):
        app = _build_app()
        client = TestClient(app)
        token = _make_token(_valid_payload())

        resp = client.get("/admin/v1/protected", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["tenant_id"] == "tenant-abc"
        assert body["admin_user_id"] == "user-123"
        assert body["role"] == "admin"

    def test_valid_token_with_super_admin_role(self, _patched):
        app = _build_app()
        client = TestClient(app)
        token = _make_token(_valid_payload(role="super_admin"))

        resp = client.get("/admin/v1/protected", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json()["role"] == "super_admin"


@patch("admin_service.middleware.jwt_auth.get_settings", return_value=_mock_settings)
class TestJWTMiddlewareInvalidToken:
    def test_missing_auth_header_returns_401(self, _patched):
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/admin/v1/protected")

        assert resp.status_code == 401
        assert resp.json()["error"] == "Missing token"

    def test_non_bearer_auth_returns_401(self, _patched):
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/admin/v1/protected", headers={"Authorization": "Basic abc123"})

        assert resp.status_code == 401
        assert resp.json()["error"] == "Missing token"

    def test_invalid_token_returns_401(self, _patched):
        app = _build_app()
        client = TestClient(app)

        resp = client.get("/admin/v1/protected", headers={"Authorization": "Bearer garbage.token.here"})

        assert resp.status_code == 401
        assert resp.json()["error"] == "Invalid token"

    def test_wrong_secret_returns_401(self, _patched):
        app = _build_app()
        client = TestClient(app)
        token = _make_token(_valid_payload(), secret="wrong-secret-that-is-also-long-enough-32bytes")

        resp = client.get("/admin/v1/protected", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 401
        assert resp.json()["error"] == "Invalid token"


@patch("admin_service.middleware.jwt_auth.get_settings", return_value=_mock_settings)
class TestJWTMiddlewareExpiredToken:
    def test_expired_token_returns_401(self, _patched):
        app = _build_app()
        client = TestClient(app)
        token = _make_token(_valid_payload(exp=datetime.now(timezone.utc) - timedelta(hours=1)))

        resp = client.get("/admin/v1/protected", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 401
        assert resp.json()["error"] == "Token expired"


class TestJWTMiddlewareExemptPaths:
    def test_health_endpoint_exempt(self):
        app = _build_app()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    @patch("admin_service.routes.auth.get_settings", return_value=_mock_settings)
    def test_login_endpoint_exempt(self, _patched):
        """Login path should be accessible without a token."""
        pool, conn = _mock_pool()
        conn.fetchrow = AsyncMock(return_value=None)
        app = _build_app(db_pool=pool)
        client = TestClient(app)

        # Even though credentials are wrong, we get 401 from the endpoint
        # (not from the middleware), proving the path is exempt
        resp = client.post(
            "/admin/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"


# ---------------------------------------------------------------------------
# Login Endpoint Tests
# ---------------------------------------------------------------------------


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@patch("admin_service.routes.auth.get_settings", return_value=_mock_settings)
class TestLoginEndpoint:
    def test_login_success_returns_jwt(self, _patched):
        hashed = _hash_password("correct-password")
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={
            "id": "user-uuid-1",
            "tenant_id": "tenant-uuid-1",
            "password_hash": hashed,
            "role": "admin",
        })
        pool, _ = _mock_pool(conn)
        app = _build_app(db_pool=pool)
        client = TestClient(app)

        resp = client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@example.com", "password": "correct-password"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 86400

        decoded = jwt.decode(body["access_token"], TEST_SECRET, algorithms=["HS256"])
        assert decoded["admin_user_id"] == "user-uuid-1"
        assert decoded["tenant_id"] == "tenant-uuid-1"
        assert decoded["role"] == "admin"

    def test_login_wrong_password_returns_401(self, _patched):
        hashed = _hash_password("correct-password")
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={
            "id": "user-uuid-1",
            "tenant_id": "tenant-uuid-1",
            "password_hash": hashed,
            "role": "admin",
        })
        pool, _ = _mock_pool(conn)
        app = _build_app(db_pool=pool)
        client = TestClient(app)

        resp = client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    def test_login_unknown_email_returns_401(self, _patched):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        pool, _ = _mock_pool(conn)
        app = _build_app(db_pool=pool)
        client = TestClient(app)

        resp = client.post(
            "/admin/v1/auth/login",
            json={"email": "nobody@example.com", "password": "anything"},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"


# ---------------------------------------------------------------------------
# Refresh Endpoint Tests
# ---------------------------------------------------------------------------


@patch("admin_service.routes.auth.get_settings", return_value=_mock_settings)
@patch("admin_service.middleware.jwt_auth.get_settings", return_value=_mock_settings)
class TestRefreshEndpoint:
    def test_refresh_returns_new_token(self, _p1, _p2):
        app = _build_app()
        client = TestClient(app)
        token = _make_token(_valid_payload())

        resp = client.post(
            "/admin/v1/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 86400

        decoded = jwt.decode(body["access_token"], TEST_SECRET, algorithms=["HS256"])
        assert decoded["tenant_id"] == "tenant-abc"
        assert decoded["admin_user_id"] == "user-123"
        assert decoded["role"] == "admin"
        # Verify expiry is ~24h from now
        exp_dt = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        assert exp_dt > datetime.now(timezone.utc) + timedelta(hours=23)

    def test_refresh_without_token_returns_401(self, _p1, _p2):
        app = _build_app()
        client = TestClient(app)

        resp = client.post("/admin/v1/auth/refresh")

        # Refresh is NOT in EXEMPT_PATHS, so middleware blocks it
        assert resp.status_code == 401
