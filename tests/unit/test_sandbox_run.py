"""Unit tests for admin_service/routes/metrics.py sandbox_run endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from admin_service.routes.metrics import sandbox_run


@pytest.mark.asyncio
class TestSandboxRun:
    async def _make_request(self, body: dict):
        """Helper to create a mock request with given body."""
        request = AsyncMock()
        request.json = AsyncMock(return_value=body)
        request.state = MagicMock()
        request.state.tenant_id = "tenant-test"
        return request

    async def test_empty_test_cases_returns_error(self):
        request = await self._make_request({"test_cases": []})
        result = await sandbox_run(request)
        assert result["status"] == "error"
        assert "No test cases" in result["message"]

    async def test_no_test_cases_key_returns_error(self):
        request = await self._make_request({})
        result = await sandbox_run(request)
        assert result["status"] == "error"

    async def test_ragas_not_installed_returns_stub(self):
        """When ragas is not installed, returns stub status."""
        request = await self._make_request({
            "test_cases": [{"query": "test", "contexts": ["ctx"], "response": "resp", "reference": "ref"}]
        })
        # ragas is not installed in test env, so ImportError path is taken
        result = await sandbox_run(request)
        assert result["status"] == "stub"
        assert result["test_cases_count"] == 1
