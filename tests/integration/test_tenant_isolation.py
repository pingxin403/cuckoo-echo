"""Integration tests for PostgreSQL RLS multi-tenant data isolation.

Verifies that Row-Level Security policies correctly prevent cross-tenant
data leakage across users, threads, and messages tables.

Requires a running PostgreSQL instance with the Cuckoo-Echo schema applied.
Run with: pytest -m integration
"""

from __future__ import annotations

from uuid import uuid4

import pytest

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]

from shared.db import tenant_db_context

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
async def db_pool():
    """Create a test database pool. Skip if PostgreSQL is not available."""
    if asyncpg is None:
        pytest.skip("asyncpg not installed")
    try:
        pool = await asyncpg.create_pool(
            dsn="postgresql://postgres:postgres@localhost:5432/cuckoo",
            statement_cache_size=0,
        )
    except Exception:
        pytest.skip("PostgreSQL not available")
    yield pool
    await pool.close()


@pytest.fixture
async def two_tenants(db_pool):
    """Insert two test tenants and clean up after the test."""
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    async with db_pool.acquire() as conn:
        for tid in (tenant_a, tenant_b):
            await conn.execute(
                """
                INSERT INTO tenants (id, name, api_key_prefix, api_key_hash)
                VALUES ($1, $2, $3, $4)
                """,
                tid,
                f"test-tenant-{tid[:8]}",
                f"ck_{tid[:8]}",
                f"hash_{tid}",
            )

    yield tenant_a, tenant_b

    # Cleanup: delete in reverse FK order, bypassing RLS via direct connection
    async with db_pool.acquire() as conn:
        for tid in (tenant_a, tenant_b):
            # Must set tenant context to see rows protected by RLS
            async with conn.transaction():
                await conn.execute("SET LOCAL app.current_tenant = $1", tid)
                await conn.execute("DELETE FROM messages WHERE tenant_id = $1", tid)
                await conn.execute("DELETE FROM threads WHERE tenant_id = $1", tid)
                await conn.execute("DELETE FROM users WHERE tenant_id = $1", tid)
        # tenants table has no RLS
        for tid in (tenant_a, tenant_b):
            await conn.execute("DELETE FROM tenants WHERE id = $1", tid)


async def _seed_tenant_data(pool, tenant_id: str) -> dict:
    """Insert a user, thread, and message for the given tenant. Returns created IDs."""
    user_id = str(uuid4())
    thread_id = str(uuid4())
    message_id = str(uuid4())

    async with pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                "INSERT INTO users (id, tenant_id, external_uid) VALUES ($1, $2, $3)",
                user_id,
                tenant_id,
                f"ext-{user_id[:8]}",
            )
            await conn.execute(
                "INSERT INTO threads (id, tenant_id, user_id) VALUES ($1, $2, $3)",
                thread_id,
                tenant_id,
                user_id,
            )
            await conn.execute(
                """
                INSERT INTO messages (id, tenant_id, thread_id, role, content)
                VALUES ($1, $2, $3, $4, $5)
                """,
                message_id,
                tenant_id,
                thread_id,
                "user",
                f"Hello from {tenant_id[:8]}",
            )

    return {"user_id": user_id, "thread_id": thread_id, "message_id": message_id}


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


async def test_rls_users_isolation(db_pool, two_tenants):
    """Users table: each tenant sees only its own rows."""
    tenant_a, tenant_b = two_tenants
    await _seed_tenant_data(db_pool, tenant_a)
    await _seed_tenant_data(db_pool, tenant_b)

    async with db_pool.acquire() as conn:
        # Query as tenant_a
        async with tenant_db_context(conn, tenant_a):
            rows = await conn.fetch("SELECT tenant_id FROM users")
            assert len(rows) > 0
            assert all(str(r["tenant_id"]) == tenant_a for r in rows)

    async with db_pool.acquire() as conn:
        # Query as tenant_b
        async with tenant_db_context(conn, tenant_b):
            rows = await conn.fetch("SELECT tenant_id FROM users")
            assert len(rows) > 0
            assert all(str(r["tenant_id"]) == tenant_b for r in rows)


async def test_rls_threads_isolation(db_pool, two_tenants):
    """Threads table: each tenant sees only its own rows."""
    tenant_a, tenant_b = two_tenants
    await _seed_tenant_data(db_pool, tenant_a)
    await _seed_tenant_data(db_pool, tenant_b)

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_a):
            rows = await conn.fetch("SELECT tenant_id FROM threads")
            assert len(rows) > 0
            assert all(str(r["tenant_id"]) == tenant_a for r in rows)

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_b):
            rows = await conn.fetch("SELECT tenant_id FROM threads")
            assert len(rows) > 0
            assert all(str(r["tenant_id"]) == tenant_b for r in rows)


async def test_rls_messages_isolation(db_pool, two_tenants):
    """Messages table: each tenant sees only its own rows."""
    tenant_a, tenant_b = two_tenants
    await _seed_tenant_data(db_pool, tenant_a)
    await _seed_tenant_data(db_pool, tenant_b)

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_a):
            rows = await conn.fetch("SELECT tenant_id FROM messages")
            assert len(rows) > 0
            assert all(str(r["tenant_id"]) == tenant_a for r in rows)

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_b):
            rows = await conn.fetch("SELECT tenant_id FROM messages")
            assert len(rows) > 0
            assert all(str(r["tenant_id"]) == tenant_b for r in rows)


async def test_cross_tenant_insert_blocked(db_pool, two_tenants):
    """Inserting a row with a mismatched tenant_id should be blocked by RLS.

    When RLS is active for tenant_a, inserting a user row with tenant_b's ID
    should either raise an error or the row should be invisible to tenant_a.
    """
    tenant_a, tenant_b = two_tenants
    rogue_user_id = str(uuid4())

    async with db_pool.acquire() as conn:
        # Set context to tenant_a but try to insert a row for tenant_b
        try:
            async with tenant_db_context(conn, tenant_a):
                await conn.execute(
                    "INSERT INTO users (id, tenant_id, external_uid) VALUES ($1, $2, $3)",
                    rogue_user_id,
                    tenant_b,  # mismatched tenant_id
                    f"rogue-{rogue_user_id[:8]}",
                )
                # If insert succeeds, the row should NOT be visible under tenant_a context
                rows = await conn.fetch(
                    "SELECT id FROM users WHERE id = $1", rogue_user_id
                )
                # RLS hides the row from tenant_a's view
                assert len(rows) == 0, "Cross-tenant row should be invisible under RLS"
        except asyncpg.exceptions.InsufficientPrivilegeError:
            # Some RLS configurations raise an error on cross-tenant insert — also valid
            pass
