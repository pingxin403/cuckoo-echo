"""Unit tests for Tool Executor node."""
import asyncio
import pytest
from unittest.mock import patch
from chat_service.agent.nodes.tool_executor import (
    tool_executor_node, safe_tool_call, _parse_tool_intent,
)
from chat_service.agent.state import AgentState


class TestParseToolIntent:
    def test_order_status_extracts_id(self):
        name, args = _parse_tool_intent("tool:get_order_status", "查订单 12345")
        assert name == "get_order_status"
        assert args["order_id"] == "12345"

    def test_order_status_no_id_defaults_unknown(self):
        name, args = _parse_tool_intent("tool:get_order_status", "查订单")
        assert name == "get_order_status"
        assert args["order_id"] == "unknown"

    def test_address_extracts_text(self):
        name, args = _parse_tool_intent("tool:update_shipping_address", "改地址：北京市朝阳区")
        assert name == "update_shipping_address"
        assert "北京" in args["address"]

    def test_address_fallback_uses_full_message(self):
        name, args = _parse_tool_intent("tool:update_shipping_address", "上海市浦东新区")
        assert name == "update_shipping_address"
        assert "上海" in args["address"]


class TestSafeToolCall:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        result = await safe_tool_call("get_order_status", {"order_id": "123"}, "t1")
        assert result["order_id"] == "123"
        assert result["tenant_id"] == "t1"

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await safe_tool_call("nonexistent", {}, "t1")
        assert result["error"] == "UNKNOWN_TOOL"

    @pytest.mark.asyncio
    async def test_tenant_id_in_result(self):
        result = await safe_tool_call("get_order_status", {"order_id": "1"}, "tenant-abc")
        assert result["tenant_id"] == "tenant-abc"

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        async def slow_tool(**kwargs):
            await asyncio.sleep(10)

        with patch(
            "chat_service.agent.tools.registry._registry",
            {"slow": {"fn": slow_tool, "name": "slow", "description": ""}},
        ), patch(
            "chat_service.agent.nodes.tool_executor.TOOL_TIMEOUT",
            0.1,
        ):
            result = await safe_tool_call("slow", {}, "t1")
        assert result["error"] == "TOOL_TIMEOUT"

    @pytest.mark.asyncio
    async def test_exception_returns_error(self):
        async def broken_tool(**kwargs):
            raise RuntimeError("boom")

        with patch(
            "chat_service.agent.tools.registry._registry",
            {"broken": {"fn": broken_tool, "name": "broken", "description": ""}},
        ):
            result = await safe_tool_call("broken", {}, "t1")
        assert result["error"] == "TOOL_ERROR"

    @pytest.mark.asyncio
    async def test_update_address_includes_tenant_id(self):
        result = await safe_tool_call(
            "update_shipping_address",
            {"order_id": "1", "address": "北京"},
            "tenant-xyz",
        )
        assert result["tenant_id"] == "tenant-xyz"


class TestToolExecutorNode:
    @pytest.mark.asyncio
    async def test_appends_tool_call_record(self):
        state = AgentState(
            user_intent="tool:get_order_status",
            tenant_id="t1",
            messages=[{"role": "user", "content": "查订单 99999"}],
            tool_calls=[],
        )
        result = await tool_executor_node(state)
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "get_order_status"
        assert "result" in result["tool_calls"][0]
        assert result["tool_calls"][0]["result"]["tenant_id"] == "t1"

    @pytest.mark.asyncio
    async def test_preserves_existing_tool_calls(self):
        existing = [{"name": "prev", "args": {}, "result": {}}]
        state = AgentState(
            user_intent="tool:get_order_status",
            tenant_id="t1",
            messages=[{"role": "user", "content": "查订单 11111"}],
            tool_calls=existing,
        )
        result = await tool_executor_node(state)
        assert len(result["tool_calls"]) == 2
        assert result["tool_calls"][0]["name"] == "prev"
        assert result["tool_calls"][1]["name"] == "get_order_status"

    @pytest.mark.asyncio
    async def test_sets_llm_response(self):
        state = AgentState(
            user_intent="tool:get_order_status",
            tenant_id="t1",
            messages=[{"role": "user", "content": "查订单 55555"}],
        )
        result = await tool_executor_node(state)
        assert result["llm_response"]  # non-empty string
