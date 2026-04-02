"""Stub node functions for the LangGraph agent graph."""

from __future__ import annotations

import structlog

from chat_service.agent.state import AgentState

log = structlog.get_logger()


async def preprocess_node(state: AgentState) -> AgentState:
    log.debug("preprocess_node", thread_id=state.get("thread_id"))
    return state


async def router_node(state: AgentState) -> AgentState:
    log.debug("router_node", thread_id=state.get("thread_id"))
    return {**state, "user_intent": "rag"}  # default to RAG for stub


async def rag_engine_node(state: AgentState) -> AgentState:
    log.debug("rag_engine_node")
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


def route_decision(state: AgentState) -> str:
    intent = state.get("user_intent", "rag")
    if intent and intent.startswith("tool:"):
        return "tool"
    if state.get("hitl_requested"):
        return "hitl"
    return "rag"


def guardrails_decision(state: AgentState) -> str:
    return "hitl" if state.get("hitl_requested") else "pass"
