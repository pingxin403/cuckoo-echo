"""LangGraph Agent state definition."""

from __future__ import annotations

from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    thread_id: str
    tenant_id: str
    user_id: str
    messages: list[dict]
    summary: str | None
    user_intent: str | None
    rag_context: list[str]
    sources: list[Any]
    tool_calls: list[dict]
    media_urls: list[str]
    hitl_requested: bool
    tokens_used: int
    llm_response: str
    guardrails_passed: bool
    correction_message: str | None
    unresolved_turns: int
    feedback_state: str | None
    reasoning_trace: dict | None
    citations: list[Any]
