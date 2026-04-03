"""Property 8: Routing determinism for clear intents.

# Feature: cuckoo-echo, Property 8: Agent 路由确定性
**Validates: Requirements 4, Acceptance Criterion 1**

For any message with clear tool intent, Router must route to tool_executor.
For any message with clear knowledge intent, Router must route to rag.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from hypothesis import given, settings, assume, HealthCheck, strategies as st

from chat_service.agent.nodes.router import router_node


def _make_state(text: str) -> dict:
    return {
        "thread_id": "t-1",
        "tenant_id": "tenant-1",
        "user_id": "u-1",
        "messages": [{"role": "user", "content": text}],
        "summary": None,
        "user_intent": None,
        "rag_context": [],
        "tool_calls": [],
        "media_urls": [],
        "hitl_requested": False,
        "tokens_used": 0,
        "llm_response": "",
        "guardrails_passed": True,
        "correction_message": None,
        "unresolved_turns": 0,
    }


def _run_async(coro):
    """Run an async coroutine in a new event loop, properly closing it after."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    order_id=st.text(
        min_size=4,
        max_size=10,
        alphabet=st.characters(whitelist_categories=("N",)),
    ),
    prefix=st.sampled_from(["查订单 ", "查询订单 ", "我的订单 ", "order status "]),
)
def test_order_status_routes_to_tool(order_id, prefix):
    """Messages with clear order-query intent always route to tool:get_order_status."""
    text = f"{prefix}{order_id}"
    state = _make_state(text)

    async def _run():
        with patch(
            "chat_service.agent.nodes.router.llm_classify_intent",
            new_callable=AsyncMock,
            side_effect=AssertionError("LLM should not be called for rule-matched intent"),
        ):
            return await router_node(state)

    result = _run_async(_run())
    assert result["user_intent"] == "tool:get_order_status", (
        f"Expected tool:get_order_status, got {result['user_intent']} for '{text}'"
    )


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    address=st.text(
        min_size=2,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    ),
    prefix=st.sampled_from(["改地址 ", "修改收货地址 ", "更换地址 ", "change address "]),
)
def test_address_update_routes_to_tool(address, prefix):
    """Messages with clear address-update intent always route to tool:update_shipping_address."""
    text = f"{prefix}{address}"
    state = _make_state(text)

    async def _run():
        with patch(
            "chat_service.agent.nodes.router.llm_classify_intent",
            new_callable=AsyncMock,
            side_effect=AssertionError("LLM should not be called for rule-matched intent"),
        ):
            return await router_node(state)

    result = _run_async(_run())
    assert result["user_intent"] == "tool:update_shipping_address", (
        f"Expected tool:update_shipping_address, got {result['user_intent']} for '{text}'"
    )


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    topic=st.sampled_from([
        "退货政策是什么",
        "如何申请发票",
        "你们的营业时间",
        "配送范围有哪些",
        "会员权益说明",
    ]),
)
def test_knowledge_question_routes_to_rag(topic):
    """Knowledge questions (no tool pattern match, no negative sentiment) route to rag via LLM."""
    state = _make_state(topic)

    async def _run():
        with patch(
            "chat_service.agent.nodes.router.llm_classify_intent",
            new_callable=AsyncMock,
            return_value="rag",
        ):
            return await router_node(state)

    result = _run_async(_run())
    assert result["user_intent"] == "rag", (
        f"Expected rag, got {result['user_intent']} for '{topic}'"
    )
