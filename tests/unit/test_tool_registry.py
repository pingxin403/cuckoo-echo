"""Unit tests for the dynamic tool registry."""
from __future__ import annotations

import pytest

from chat_service.agent.tools.registry import (
    _registry,
    get_tool,
    list_tools,
    register_tool,
)


class TestRegisterTool:
    def test_decorator_registers_function(self):
        @register_tool("test_tool_1", description="A test tool")
        async def my_tool():
            return "ok"

        assert "test_tool_1" in _registry
        assert _registry["test_tool_1"]["description"] == "A test tool"
        # Cleanup
        del _registry["test_tool_1"]

    def test_decorator_preserves_function(self):
        @register_tool("test_tool_2")
        async def my_tool():
            return 42

        assert my_tool is not None
        del _registry["test_tool_2"]


class TestGetTool:
    def test_returns_registered_function(self):
        fn = get_tool("get_order_status")
        assert fn is not None
        assert callable(fn)

    def test_returns_none_for_unknown(self):
        assert get_tool("nonexistent_tool") is None


class TestListTools:
    def test_lists_registered_tools(self):
        tools = list_tools()
        names = [t["name"] for t in tools]
        assert "get_order_status" in names
        assert "update_shipping_address" in names

    def test_includes_descriptions(self):
        tools = list_tools()
        order_tool = next(t for t in tools if t["name"] == "get_order_status")
        assert order_tool["description"]  # non-empty


class TestOrderServiceClient:
    @pytest.mark.asyncio
    async def test_mock_mode_returns_data(self):
        from chat_service.agent.tools.order_tools import OrderServiceClient

        client = OrderServiceClient(mock_mode=True)
        result = await client.get_order_status("123", "t1")
        assert result["order_id"] == "123"
        assert result["tenant_id"] == "t1"

    @pytest.mark.asyncio
    async def test_mock_update_address(self):
        from chat_service.agent.tools.order_tools import OrderServiceClient

        client = OrderServiceClient(mock_mode=True)
        result = await client.update_shipping_address("123", "北京", "t1")
        assert result["updated"] is True
        assert result["tenant_id"] == "t1"
