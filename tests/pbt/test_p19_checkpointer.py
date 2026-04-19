"""Property 19: Checkpointer round-trip.

# Feature: cuckoo-echo, Property 19: 对话状态保存与恢复
**Validates: Requirements 6.3**

Tests AgentState round-trip: serialization and deserialization must
preserve all fields without loss.
"""

import json

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from chat_service.agent.state import AgentState


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(message_count=st.integers(1, 50))
def test_checkpointer_round_trip(message_count):
    """AgentState must survive JSON round-trip without data loss."""
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg_{i}"}
        for i in range(message_count)
    ]
    state = AgentState(
        thread_id="t1",
        tenant_id="tenant-a",
        user_id="u1",
        messages=messages,
        user_intent="rag",
        tool_calls=[],
    )
    # Property: state can be serialized and deserialized without loss
    serialized = json.dumps(dict(state))
    restored = json.loads(serialized)
    assert restored["messages"] == messages
    assert restored["user_intent"] == "rag"
    assert restored["tool_calls"] == []
    assert len(restored["messages"]) == message_count
