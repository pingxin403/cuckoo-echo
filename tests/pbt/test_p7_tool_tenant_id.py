"""Property 7: Tool call tenant_id passthrough.

# Feature: cuckoo-echo, Property 7: 工具调用 tenant_id 透传不变量
**Validates: Requirements 4, Acceptance Criterion 3**

For any tool call triggered by tenant_t, every outbound request carries tenant_id == tenant_t.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from hypothesis import given, settings, HealthCheck, strategies as st

from chat_service.agent.nodes.tool_executor import tool_executor_node


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    tenant_id=st.uuids(),
    order_id=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("N",)),
    ),
)
def test_tool_tenant_id_passthrough(tenant_id, order_id):
    """tenant_id passed to tool_executor_node is forwarded to the tool function."""
    tid = str(tenant_id)
    captured_tenant_ids: list[str] = []

    async def mock_get_order_status(tenant_id: str, **kwargs):
        captured_tenant_ids.append(tenant_id)
        return {"order_id": kwargs.get("order_id", ""), "status": "shipped"}

    state = {
        "thread_id": "t-1",
        "tenant_id": tid,
        "user_id": "u-1",
        "messages": [{"role": "user", "content": f"查订单 {order_id}"}],
        "summary": None,
        "user_intent": "tool:get_order_status",
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

    async def _run():
        with patch(
            "chat_service.agent.nodes.tool_executor.get_tool",
            return_value=mock_get_order_status,
        ):
            result = await tool_executor_node(state)
            return result

    result = asyncio.new_event_loop().run_until_complete(_run())

    # Assert tenant_id was passed through to the tool
    assert len(captured_tenant_ids) == 1, "Tool should be called exactly once"
    assert captured_tenant_ids[0] == tid, (
        f"Tool received tenant_id={captured_tenant_ids[0]}, expected {tid}"
    )
    # Assert tool call was recorded in state
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "get_order_status"
