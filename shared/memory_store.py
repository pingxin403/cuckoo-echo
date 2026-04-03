"""Cross-thread long-term memory store using PostgreSQL.

Lightweight alternative to langgraph-store-postgres (not yet published).
Stores user preferences and long-term memory per tenant+user, accessible
across all threads for that user.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog

log = structlog.get_logger()


class MemoryStore:
    """PostgreSQL-backed cross-thread memory store."""

    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def get(self, tenant_id: str, user_id: str, key: str) -> str | None:
        """Retrieve a memory value by key."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM thread_memories "
                "WHERE tenant_id = $1 AND user_id = $2 AND key = $3",
                tenant_id, user_id, key,
            )
            return row["value"] if row else None

    async def get_all(self, tenant_id: str, user_id: str) -> dict[str, str]:
        """Retrieve all memories for a user."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value FROM thread_memories "
                "WHERE tenant_id = $1 AND user_id = $2",
                tenant_id, user_id,
            )
            return {row["key"]: row["value"] for row in rows}

    async def put(self, tenant_id: str, user_id: str, key: str, value: str) -> None:
        """Store or update a memory value."""
        now = datetime.now(timezone.utc)
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO thread_memories (tenant_id, user_id, key, value, updated_at) "
                "VALUES ($1, $2, $3, $4, $5) "
                "ON CONFLICT (tenant_id, user_id, key) "
                "DO UPDATE SET value = $4, updated_at = $5",
                tenant_id, user_id, key, value, now,
            )
        log.debug("memory_stored", tenant_id=tenant_id, user_id=user_id, key=key)

    async def delete(self, tenant_id: str, user_id: str, key: str) -> None:
        """Delete a specific memory."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM thread_memories "
                "WHERE tenant_id = $1 AND user_id = $2 AND key = $3",
                tenant_id, user_id, key,
            )
