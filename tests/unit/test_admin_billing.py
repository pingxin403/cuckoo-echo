"""Unit tests for admin billing API."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from admin_service.routes.billing import (
    list_plans,
    create_plan,
    update_plan,
    delete_plan,
    seed_plans,
    get_usage,
    list_invoices,
    create_invoice,
)
from admin_service.routes.billing import PlanCreate, PlanUpdate, InvoiceCreate


class TestListPlans:
    @pytest.mark.asyncio
    async def test_list_plans_empty(self):
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        request = MagicMock()
        request.app.state.db_pool = mock_pool

        result = await list_plans(request)
        assert result == []


class TestSeedPlans:
    @pytest.mark.asyncio
    async def test_seed_plans_creates_defaults(self):
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        request = MagicMock()
        request.app.state.db_pool = mock_pool

        result = await seed_plans(request)
        assert result["seeded"] == 4


class TestGetUsage:
    @pytest.mark.asyncio
    async def test_get_usage_returns_history(self):
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "period": "2026-04",
                "messages_used": 100,
                "tokens_used": 5000,
                "tools_used": 10,
                "storage_mb": 50,
            }
        ])
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        request = MagicMock()
        request.app.state.db_pool = mock_pool

        result = await get_usage("tenant-123", request)
        assert len(result) == 1
        assert result[0]["period"] == "2026-04"
        assert result[0]["messages_used"] == 100