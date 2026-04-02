"""Node functions for the LangGraph agent graph."""

from __future__ import annotations

import structlog

from chat_service.agent.nodes.rag_engine import rag_engine_node
from chat_service.agent.nodes.router import (
    detect_negative_sentiment,
    llm_classify_intent,
    route_decision,
    router_node,
)
from chat_service.agent.state import AgentState

log = structlog.get_logger()

__all__ = [
    "preprocess_node",
    "router_node",
    "rag_engine_node",
    "tool_executor_node",
    "llm_generate_node",
    "guardrails_node",
    "postprocess_node",
    "route_decision",
    "guardrails_decision",
    "detect_negative_sentiment",
    "llm_classify_intent",
]


async def preprocess_node(state: AgentState) -> AgentState:
    log.debug("preprocess_node", thread_id=state.get("thread_id"))
    return state


async def tool_executor_node(state: AgentState) -> AgentState:
    log.debug("tool_executor_node")
    return state


async def llm_generate_node(state: AgentState) -> AgentState:
    log.debug("llm_generate_node")
    return {**state, "llm_response": "stub response", "guardrails_passed": True}


async def guardrails_node(state: AgentState) -> AgentState:
    log.debug("guardrails_node")
    return {**state, "guardrails_passed": True}


async def postprocess_node(state: AgentState) -> AgentState:
    log.debug("postprocess_node")
    return state


def guardrails_decision(state: AgentState) -> str:
    return "hitl" if state.get("hitl_requested") else "pass"
