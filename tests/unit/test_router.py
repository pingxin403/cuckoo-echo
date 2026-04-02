"""Unit tests for the Router node."""

import pytest
from unittest.mock import AsyncMock, patch

from chat_service.agent.nodes.router import (
    RULE_PATTERNS,
    UNRESOLVED_THRESHOLD,
    detect_negative_sentiment,
    llm_classify_intent,
    route_decision,
    router_node,
)
from chat_service.agent.state import AgentState


class TestRulePatterns:
    def test_order_status_chinese(self):
        for text in ["查订单 12345", "帮我查一下订单", "我的订单到哪了", "订单状态查询"]:
            matched = any(p.search(text) for p in RULE_PATTERNS["get_order_status"])
            assert matched, f"Should match: {text}"

    def test_order_status_english(self):
        for text in ["order status", "track my order", "where is my order"]:
            matched = any(p.search(text) for p in RULE_PATTERNS["get_order_status"])
            assert matched, f"Should match: {text}"

    def test_update_address_chinese(self):
        for text in ["改地址", "修改收货地址", "更换地址"]:
            matched = any(p.search(text) for p in RULE_PATTERNS["update_shipping_address"])
            assert matched, f"Should match: {text}"

    def test_update_address_english(self):
        for text in ["change address", "update my address", "modify shipping address"]:
            matched = any(p.search(text) for p in RULE_PATTERNS["update_shipping_address"])
            assert matched, f"Should match: {text}"

    def test_no_match_for_general_question(self):
        text = "退货政策是什么"
        for patterns in RULE_PATTERNS.values():
            assert not any(p.search(text) for p in patterns)


class TestDetectNegativeSentiment:
    def test_negative_keyword_detected(self):
        state = AgentState(messages=[{"role": "user", "content": "你们太差了，我要投诉"}])
        assert detect_negative_sentiment(state) is True

    def test_unresolved_turns_threshold(self):
        state = AgentState(
            messages=[{"role": "user", "content": "hello"}],
            unresolved_turns=UNRESOLVED_THRESHOLD,
        )
        assert detect_negative_sentiment(state) is True

    def test_below_threshold(self):
        state = AgentState(
            messages=[{"role": "user", "content": "hello"}],
            unresolved_turns=UNRESOLVED_THRESHOLD - 1,
        )
        assert detect_negative_sentiment(state) is False

    def test_no_messages(self):
        state = AgentState(messages=[])
        assert detect_negative_sentiment(state) is False

    def test_english_negative_keyword(self):
        state = AgentState(messages=[{"role": "user", "content": "this is terrible service"}])
        assert detect_negative_sentiment(state) is True


class TestRouterNode:
    @pytest.mark.asyncio
    async def test_rule_engine_hit(self):
        state = AgentState(messages=[{"role": "user", "content": "查订单 12345"}], tenant_id="t1")
        result = await router_node(state)
        assert result["user_intent"] == "tool:get_order_status"

    @pytest.mark.asyncio
    async def test_hitl_on_negative_sentiment(self):
        state = AgentState(messages=[{"role": "user", "content": "你们是骗子"}], tenant_id="t1")
        result = await router_node(state)
        assert result["user_intent"] == "hitl"
        assert result["hitl_requested"] is True

    @pytest.mark.asyncio
    async def test_hitl_on_unresolved_turns(self):
        state = AgentState(
            messages=[{"role": "user", "content": "还是不行"}],
            tenant_id="t1",
            unresolved_turns=UNRESOLVED_THRESHOLD,
        )
        result = await router_node(state)
        assert result["user_intent"] == "hitl"

    @pytest.mark.asyncio
    async def test_llm_fallback_called(self):
        state = AgentState(messages=[{"role": "user", "content": "退货政策是什么"}], tenant_id="t1")
        with patch(
            "chat_service.agent.nodes.router.llm_classify_intent",
            new_callable=AsyncMock,
            return_value="rag",
        ):
            result = await router_node(state)
        assert result["user_intent"] == "rag"

    @pytest.mark.asyncio
    async def test_empty_messages_defaults_to_rag(self):
        state = AgentState(messages=[], tenant_id="t1")
        result = await router_node(state)
        assert result["user_intent"] == "rag"

    @pytest.mark.asyncio
    async def test_llm_fallback_hitl(self):
        state = AgentState(messages=[{"role": "user", "content": "我要找人工客服"}], tenant_id="t1")
        with patch(
            "chat_service.agent.nodes.router.llm_classify_intent",
            new_callable=AsyncMock,
            return_value="hitl",
        ):
            result = await router_node(state)
        assert result["user_intent"] == "hitl"
        assert result["hitl_requested"] is True


class TestRouteDecision:
    def test_tool(self):
        assert route_decision(AgentState(user_intent="tool:get_order_status")) == "tool"

    def test_rag(self):
        assert route_decision(AgentState(user_intent="rag")) == "rag"

    def test_hitl_via_flag(self):
        assert route_decision(AgentState(hitl_requested=True)) == "hitl"

    def test_hitl_via_intent(self):
        assert route_decision(AgentState(user_intent="hitl")) == "hitl"

    def test_default(self):
        assert route_decision(AgentState()) == "rag"
