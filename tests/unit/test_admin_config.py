"""Unit tests for Admin Config & Metrics endpoints."""
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from starlette.testclient import TestClient

from admin_service.routes.config import router as config_router
from admin_service.routes.metrics import router as metrics_router


def _build_app(db_pool=None, redis=None, db_pool_ro=None):
    """Build a test FastAPI app with config + metrics routers and fake auth."""
    app = FastAPI()
    app.include_router(config_router)
    app.include_router(metrics_router)
    app.state.db_pool = db_pool or MagicMock()
    app.state.redis = redis or AsyncMock()
    if db_pool_ro is not None:
        app.state.db_pool_ro = db_pool_ro

    @app.middleware("http")
    async def fake_auth(request, call_next):
        request.state.tenant_id = "test-tenant"
        return await call_next(request)

    return app


def _mock_pool(mock_conn=None):
    """Create a mock db_pool whose acquire() returns an async context manager."""
    conn = mock_conn or AsyncMock()
    pool = MagicMock()
    acm = AsyncMock()
    acm.__aenter__ = AsyncMock(return_value=conn)
    acm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acm)
    return pool, conn


# ---------------------------------------------------------------------------
# Config endpoint tests (Task 14.1)
# ---------------------------------------------------------------------------

class TestUpdatePersona:
    def test_persona_update_persists_to_db(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.put(
            "/admin/v1/config/persona",
            json={"system_prompt": "You are a helpful assistant.", "persona_name": "Echo"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"updated": True}
        conn.execute.assert_awaited_once()
        call_args = conn.execute.await_args
        sql = call_args[0][0]
        assert "UPDATE tenants SET llm_config" in sql
        # Verify orjson-serialized payload contains the prompt
        json_payload = call_args[0][1]
        assert "You are a helpful assistant." in json_payload
        assert "Echo" in json_payload

    def test_persona_update_without_persona_name(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.put(
            "/admin/v1/config/persona",
            json={"system_prompt": "Be concise."},
        )

        assert resp.status_code == 200
        assert resp.json() == {"updated": True}


class TestUpdateModel:
    def test_model_update_persists_to_db(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.put(
            "/admin/v1/config/model",
            json={"model": "gpt-4o", "fallback_model": "deepseek-chat", "temperature": 0.5},
        )

        assert resp.status_code == 200
        assert resp.json() == {"updated": True}
        conn.execute.assert_awaited_once()
        call_args = conn.execute.await_args
        sql = call_args[0][0]
        assert "UPDATE tenants SET llm_config" in sql
        json_payload = call_args[0][1]
        assert "gpt-4o" in json_payload

    def test_model_update_excludes_none_fallback(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.put(
            "/admin/v1/config/model",
            json={"model": "deepseek-chat"},
        )

        assert resp.status_code == 200
        call_args = conn.execute.await_args
        json_payload = call_args[0][1]
        assert "fallback_model" not in json_payload


class TestUpdateRateLimit:
    def test_rate_limit_update_persists_and_invalidates_cache(self):
        pool, conn = _mock_pool()
        mock_redis = AsyncMock()
        app = _build_app(pool, redis=mock_redis)
        client = TestClient(app)

        resp = client.put(
            "/admin/v1/config/rate-limit",
            json={"tenant_rps": 200, "user_rps": 20},
        )

        assert resp.status_code == 200
        assert resp.json() == {"updated": True}

        # Verify DB update
        conn.execute.assert_awaited_once()
        call_args = conn.execute.await_args
        sql = call_args[0][0]
        assert "UPDATE tenants SET rate_limit" in sql

        # Verify Redis cache invalidation
        mock_redis.delete.assert_awaited_once_with("cuckoo:ratelimit_config:test-tenant")

    def test_rate_limit_uses_defaults(self):
        pool, conn = _mock_pool()
        mock_redis = AsyncMock()
        app = _build_app(pool, redis=mock_redis)
        client = TestClient(app)

        resp = client.put("/admin/v1/config/rate-limit", json={})

        assert resp.status_code == 200
        call_args = conn.execute.await_args
        json_payload = call_args[0][1]
        # Default values should be serialized
        assert "100" in json_payload  # tenant_rps default
        assert "10" in json_payload   # user_rps default


# ---------------------------------------------------------------------------
# Metrics endpoint tests (Tasks 14.2, 14.3)
# ---------------------------------------------------------------------------

class TestMetricsOverview:
    def test_overview_returns_aggregated_data(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"total_conversations": 42, "hitl_count": 5})
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.get("/admin/v1/metrics/overview?range=7d")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_conversations"] == 42
        assert body["human_transfer_count"] == 5
        assert body["human_transfer_rate"] == round(5 / 42, 4)
        assert body["range"] == "7d"

    def test_overview_handles_zero_conversations(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"total_conversations": 0, "hitl_count": 0})
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.get("/admin/v1/metrics/overview")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_conversations"] == 0
        assert body["human_transfer_rate"] == 0.0

    def test_overview_uses_read_replica_when_available(self):
        """Metrics should prefer db_pool_ro over db_pool."""
        main_conn = AsyncMock()
        ro_conn = AsyncMock()
        ro_conn.fetchrow = AsyncMock(return_value={"total_conversations": 10, "hitl_count": 2})

        main_pool, _ = _mock_pool(main_conn)
        ro_pool, _ = _mock_pool(ro_conn)
        app = _build_app(main_pool, db_pool_ro=ro_pool)
        client = TestClient(app)

        resp = client.get("/admin/v1/metrics/overview?range=1d")

        assert resp.status_code == 200
        # RO conn should have been used, not main conn
        ro_conn.fetchrow.assert_awaited()
        main_conn.fetchrow.assert_not_awaited()


class TestMetricsTokens:
    def test_tokens_returns_aggregated_data(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"total_tokens": 15000, "message_count": 120})
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.get("/admin/v1/metrics/tokens?range=30d")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_tokens"] == 15000
        assert body["message_count"] == 120
        assert body["range"] == "30d"

    def test_tokens_handles_no_data(self):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"total_tokens": 0, "message_count": 0})
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.get("/admin/v1/metrics/tokens")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_tokens"] == 0
        assert body["message_count"] == 0


class TestMetricsMissedQueries:
    def test_missed_queries_returns_top_20(self):
        conn = AsyncMock()
        # Use plain dicts — dict(dict) returns a copy, which is what the endpoint does
        mock_rows = [
            {"query_prefix": "How do I return an item?", "count": 15},
            {"query_prefix": "Where is my order?", "count": 8},
        ]
        conn.fetch = AsyncMock(return_value=mock_rows)
        pool, _ = _mock_pool(conn)
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.get("/admin/v1/metrics/missed-queries?range=7d")

        assert resp.status_code == 200
        body = resp.json()
        assert "missed_queries" in body
        assert len(body["missed_queries"]) == 2
        assert body["range"] == "7d"


# ---------------------------------------------------------------------------
# Sandbox endpoint test (Task 14.4)
# ---------------------------------------------------------------------------

class TestSandboxRun:
    def test_sandbox_returns_stub_response(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.post(
            "/admin/v1/metrics/sandbox/run",
            json={"test_cases": [{"query": "What is the return policy?", "expected": "30 days"}]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "stub"
        assert body["test_cases_count"] == 1

    def test_sandbox_handles_empty_test_cases(self):
        pool, conn = _mock_pool()
        app = _build_app(pool)
        client = TestClient(app)

        resp = client.post("/admin/v1/metrics/sandbox/run", json={})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"
        assert "No test cases" in body["message"]
