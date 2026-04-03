"""Database utilities for Cuckoo-Echo.

Provides asyncpg pool creation (PgBouncer-compatible), tenant RLS context
manager, and Redis key-builder helpers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
import structlog

from shared.config import get_settings

log = structlog.get_logger()


async def create_asyncpg_pool() -> asyncpg.Pool:
    """Create an asyncpg connection pool compatible with PgBouncer transaction mode.

    PgBouncer in transaction mode switches backend connections per transaction,
    which causes "prepared statement does not exist" errors when asyncpg's
    default statement cache is enabled. Setting ``statement_cache_size=0``
    disables the cache and is mandatory for PgBouncer transaction-mode DSNs.
    """
    dsn = get_settings().database_url
    log.info("creating_asyncpg_pool", dsn=dsn)
    return await asyncpg.create_pool(dsn=dsn, statement_cache_size=0)


async def create_asyncpg_pool_ro() -> asyncpg.Pool:
    """Create a read-only asyncpg connection pool for Admin queries.

    If ``database_ro_url`` is configured, creates an independent pool pointing
    to the read-replica. Otherwise falls back to the primary pool via
    ``create_asyncpg_pool()``.

    The read-only pool uses a smaller ``max_size`` since Admin queries are
    lower volume than C-end chat traffic.
    """
    settings = get_settings()
    if settings.database_ro_url:
        log.info("creating_asyncpg_pool_ro", dsn=settings.database_ro_url)
        return await asyncpg.create_pool(
            dsn=settings.database_ro_url,
            statement_cache_size=0,
            max_size=10,
        )
    log.info("asyncpg_pool_ro_fallback", hint="No DATABASE_RO_URL configured, using primary pool")
    return await create_asyncpg_pool()


@asynccontextmanager
async def tenant_db_context(
    conn: asyncpg.Connection,
    tenant_id: str,
) -> AsyncIterator[asyncpg.Connection]:
    """Activate PostgreSQL RLS for *tenant_id* within a transaction.

    Opens a transaction on *conn* and executes
    ``SET LOCAL app.current_tenant = $1`` so that all RLS policies filter
    rows to the given tenant.  The ``SET LOCAL`` automatically expires when
    the transaction ends, making the connection safe to return to the pool.

    Requires PgBouncer ``pool_mode = transaction`` so that the same backend
    connection is used for the entire transaction.
    """
    async with conn.transaction():
        await conn.execute("SET LOCAL app.current_tenant = $1", tenant_id)
        yield conn


def lock_key(thread_id: str) -> str:
    """Return the Redis key for a per-thread distributed lock.

    All keys use the ``cuckoo:`` namespace prefix.
    """
    return f"cuckoo:lock:{thread_id}"


def ratelimit_key(tenant_id: str, user_id: str) -> str:
    """Return the Redis key for a per-user fixed-window rate-limit counter.

    All keys use the ``cuckoo:`` namespace prefix.
    """
    return f"cuckoo:ratelimit:{tenant_id}:{user_id}"
