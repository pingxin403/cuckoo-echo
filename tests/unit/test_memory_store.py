"""Unit tests for cross-thread memory store.

Covers:
- put + get round-trip
- get_all returns all memories for a user
- get returns None for missing key
- put overwrites existing value (upsert)
- delete removes a memory
- tenant isolation (different tenants don't see each other's memories)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.memory_store import MemoryStore


def _mock_pool():
    """Create a mock db_pool with in-memory storage."""
    storage: dict[tuple, dict] = {}

    async def mock_fetchrow(query, *args):
        if "SELECT value" in query:
            tenant_id, user_id, key = args
            val = storage.get((tenant_id, user_id, key))
            if val:
                return {"value": val["value"]}
            return None
        return None

    async def mock_fetch(query, *args):
        if "SELECT key, value" in query:
            tenant_id, user_id = args
            return [
                {"key": k[2], "value": v["value"]}
                for k, v in storage.items()
                if k[0] == tenant_id and k[1] == user_id
            ]
        return []

    async def mock_execute(query, *args):
        if "INSERT INTO thread_memories" in query:
            tenant_id, user_id, key, value, updated_at = args
            storage[(tenant_id, user_id, key)] = {"value": value, "updated_at": updated_at}
        elif "DELETE FROM thread_memories" in query:
            tenant_id, user_id, key = args
            storage.pop((tenant_id, user_id, key), None)

    conn = AsyncMock()
    conn.fetchrow = mock_fetchrow
    conn.fetch = mock_fetch
    conn.execute = mock_execute

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    return pool, storage


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_put_and_get(self):
        pool, _ = _mock_pool()
        store = MemoryStore(pool)

        await store.put("t1", "u1", "language", "zh-CN")
        result = await store.get("t1", "u1", "language")
        assert result == "zh-CN"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        pool, _ = _mock_pool()
        store = MemoryStore(pool)

        result = await store.get("t1", "u1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self):
        pool, _ = _mock_pool()
        store = MemoryStore(pool)

        await store.put("t1", "u1", "language", "zh-CN")
        await store.put("t1", "u1", "timezone", "Asia/Shanghai")

        all_memories = await store.get_all("t1", "u1")
        assert all_memories == {"language": "zh-CN", "timezone": "Asia/Shanghai"}

    @pytest.mark.asyncio
    async def test_put_overwrites(self):
        pool, _ = _mock_pool()
        store = MemoryStore(pool)

        await store.put("t1", "u1", "language", "en-US")
        await store.put("t1", "u1", "language", "zh-CN")
        result = await store.get("t1", "u1", "language")
        assert result == "zh-CN"

    @pytest.mark.asyncio
    async def test_delete(self):
        pool, _ = _mock_pool()
        store = MemoryStore(pool)

        await store.put("t1", "u1", "language", "zh-CN")
        await store.delete("t1", "u1", "language")
        result = await store.get("t1", "u1", "language")
        assert result is None

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        pool, _ = _mock_pool()
        store = MemoryStore(pool)

        await store.put("t1", "u1", "language", "zh-CN")
        await store.put("t2", "u1", "language", "en-US")

        assert await store.get("t1", "u1", "language") == "zh-CN"
        assert await store.get("t2", "u1", "language") == "en-US"

        t1_all = await store.get_all("t1", "u1")
        assert "en-US" not in t1_all.values()
