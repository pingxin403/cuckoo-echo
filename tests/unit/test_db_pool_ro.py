"""Unit tests for read-only database pool.

Covers:
- database_ro_url empty → fallback to primary pool
- database_ro_url set → creates independent pool
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.db import create_asyncpg_pool_ro


class TestCreateAsyncpgPoolRo:
    @pytest.mark.asyncio
    async def test_fallback_when_ro_url_empty(self):
        """When database_ro_url is empty, falls back to primary pool."""
        mock_settings = MagicMock()
        mock_settings.database_ro_url = ""
        mock_settings.database_url = "postgresql://localhost/cuckoo"

        mock_pool = AsyncMock()

        with (
            patch("shared.db.get_settings", return_value=mock_settings),
            patch("shared.db.asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool) as mock_create,
        ):
            pool = await create_asyncpg_pool_ro()

        assert pool is mock_pool
        # Should use the primary DSN
        mock_create.assert_called_once_with(
            dsn="postgresql://localhost/cuckoo",
            statement_cache_size=0,
        )

    @pytest.mark.asyncio
    async def test_independent_pool_when_ro_url_set(self):
        """When database_ro_url is set, creates an independent read-only pool."""
        mock_settings = MagicMock()
        mock_settings.database_ro_url = "postgresql://readonly@replica:5432/cuckoo"
        mock_settings.database_url = "postgresql://localhost/cuckoo"

        mock_pool = AsyncMock()

        with (
            patch("shared.db.get_settings", return_value=mock_settings),
            patch("shared.db.asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool) as mock_create,
        ):
            pool = await create_asyncpg_pool_ro()

        assert pool is mock_pool
        # Should use the RO DSN with smaller max_size
        mock_create.assert_called_once_with(
            dsn="postgresql://readonly@replica:5432/cuckoo",
            statement_cache_size=0,
            max_size=10,
        )
