"""Unit tests for the LangGraph agent graph."""

from chat_service.agent.graph import build_agent_graph
from chat_service.agent.nodes import guardrails_decision, route_decision
from chat_service.agent.state import AgentState


class TestAgentState:
    def test_all_fields_defined(self):
        expected = {
            "thread_id",
            "tenant_id",
            "user_id",
            "messages",
            "summary",
            "user_intent",
            "rag_context",
            "tool_calls",
            "media_urls",
            "hitl_requested",
            "tokens_used",
            "llm_response",
            "guardrails_passed",
            "correction_message",
            "unresolved_turns",
            "feedback_state",
        }
        assert set(AgentState.__annotations__.keys()) == expected

    def test_total_false_allows_partial_construction(self):
        state = AgentState()
        assert isinstance(state, dict)

    def test_can_set_individual_fields(self):
        state = AgentState(thread_id="t1", tenant_id="tenant-a")
        assert state["thread_id"] == "t1"
        assert state["tenant_id"] == "tenant-a"


class TestBuildAgentGraph:
    def test_compiles_without_checkpointer(self):
        graph = build_agent_graph(checkpointer=None)
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_agent_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected_nodes = {
            "preprocess",
            "router",
            "rag_engine",
            "tool_executor",
            "llm_generate",
            "guardrails",
            "postprocess",
            "__start__",
            "__end__",
        }
        assert expected_nodes.issubset(node_names)

    def test_graph_has_entry_point(self):
        graph = build_agent_graph()
        # If it compiled with set_entry_point, the graph is valid
        assert graph is not None


class TestRouteDecision:
    def test_tool_intent(self):
        state = AgentState(user_intent="tool:get_order_status")
        assert route_decision(state) == "tool"

    def test_rag_intent(self):
        state = AgentState(user_intent="rag")
        assert route_decision(state) == "rag"

    def test_hitl_requested(self):
        state = AgentState(hitl_requested=True, user_intent="rag")
        assert route_decision(state) == "hitl"

    def test_default_is_rag(self):
        state = AgentState()
        assert route_decision(state) == "rag"

    def test_tool_prefix_variations(self):
        state = AgentState(user_intent="tool:update_shipping_address")
        assert route_decision(state) == "tool"


class TestGuardrailsDecision:
    def test_pass_when_not_hitl(self):
        state = AgentState(hitl_requested=False)
        assert guardrails_decision(state) == "pass"

    def test_hitl_when_requested(self):
        state = AgentState(hitl_requested=True)
        assert guardrails_decision(state) == "hitl"

    def test_default_is_pass(self):
        state = AgentState()
        assert guardrails_decision(state) == "pass"
