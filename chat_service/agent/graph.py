"""LangGraph agent graph construction."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from chat_service.agent.nodes import (
    guardrails_decision,
    guardrails_node,
    llm_generate_node,
    postprocess_node,
    preprocess_node,
    rag_engine_node,
    route_decision,
    router_node,
    tool_executor_node,
)
from chat_service.agent.nodes.hitl_node import hitl_node
from chat_service.agent.state import AgentState


def build_agent_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Build and compile the LangGraph agent state graph."""
    graph = StateGraph(AgentState)

    graph.add_node("preprocess", preprocess_node)
    graph.add_node("router", router_node)
    graph.add_node("rag_engine", rag_engine_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("llm_generate", llm_generate_node)
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("postprocess", postprocess_node)
    graph.add_node("hitl", hitl_node)

    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "router")
    graph.add_conditional_edges("router", route_decision, {
        "tool": "tool_executor",
        "rag": "rag_engine",
        "hitl": "hitl",
    })
    graph.add_edge("tool_executor", "llm_generate")
    graph.add_edge("rag_engine", "llm_generate")
    graph.add_edge("llm_generate", "guardrails")
    graph.add_conditional_edges("guardrails", guardrails_decision, {
        "pass": "postprocess",
        "hitl": "hitl",
    })
    graph.add_edge("hitl", END)
    graph.add_edge("postprocess", END)

    return graph.compile(checkpointer=checkpointer)
