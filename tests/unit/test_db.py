"""Unit tests for shared.db module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.db import create_asyncpg_pool, lock_key, ratelimit_key, tenant_db_context


# ---------------------------------------------------------------------------
# Key-builder tests (pure functions, no mocking needed)
# ---------------------------------------------------------------------------


class TestLockKey:
    def test_returns_namespaced_key(self):
        assert lock_key("abc-123") == "cuckoo:lock:abc-123"

    def test_starts_with_cuckoo_prefix(self):
        key = lock_key("any-thread-id")
        assert key.startswith("cuckoo:")

    def test_contains_thread_id(self):
        tid = "550e8400-e29b-41d4-a716-446655440000"
        assert tid in lock_key(tid)


class TestRatelimitKey:
    def test_returns_namespaced_key(self):
        assert ratelimit_key("t1", "u1") == "cuckoo:ratelimit:t1:u1"

    def test_starts_with_cuckoo_prefix(self):
        key = ratelimit_key("tenant-x", "user-y")
        assert key.startswith("cuckoo:")

    def test_contains_tenant_and_user(self):
        key = ratelimit_key("tenant-abc", "user-xyz")
        assert "tenant-abc" in key
        assert "user-xyz" in key


# ---------------------------------------------------------------------------
# create_asyncpg_pool tests
# ---------------------------------------------------------------------------


class TestCreateAsyncpgPool:
    @pytest.mark.asyncio
    @patch("shared.db.asyncpg.create_pool", new_callable=AsyncMock)
    @patch("shared.db.get_settings")
    async def test_uses_database_url_from_settings(self, mock_get_settings, mock_create_pool):
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://localhost/test"
        mock_get_settings.return_value = mock_settings
        mock_create_pool.return_value = MagicMock()

        await create_asyncpg_pool()

        mock_create_pool.assert_awaited_once()
        _, kwargs = mock_create_pool.call_args
        assert kwargs["dsn"] == "postgresql://localhost/test"

    @pytest.mark.asyncio
    @patch("shared.db.asyncpg.create_pool", new_callable=AsyncMock)
    @patch("shared.db.get_settings")
    async def test_statement_cache_disabled(self, mock_get_settings, mock_create_pool):
        """statement_cache_size=0 is mandatory for PgBouncer transaction mode."""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://localhost/test"
        mock_get_settings.return_value = mock_settings
        mock_create_pool.return_value = MagicMock()

        await create_asyncpg_pool()

        _, kwargs = mock_create_pool.call_args
        assert kwargs["statement_cache_size"] == 0


# ---------------------------------------------------------------------------
# tenant_db_context tests
# ---------------------------------------------------------------------------


class _FakeTransaction:
    """Minimal async context manager that mimics asyncpg Transaction."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class TestTenantDbContext:
    @pytest.mark.asyncio
    async def test_executes_set_local(self):
        """Must run SET LOCAL app.current_tenant = $1 inside a transaction."""
        conn = AsyncMock()
        conn.transaction = MagicMock(return_value=_FakeTransaction())

        async with tenant_db_context(conn, "tenant-42") as c:
            assert c is conn

        conn.execute.assert_awaited_once_with(
            "SET LOCAL app.current_tenant = 'tenant-42'"
        )

    @pytest.mark.asyncio
    async def test_opens_transaction(self):
        conn = AsyncMock()
        conn.transaction = MagicMock(return_value=_FakeTransaction())

        async with tenant_db_context(conn, "t1"):
            pass

        conn.transaction.assert_called_once()
