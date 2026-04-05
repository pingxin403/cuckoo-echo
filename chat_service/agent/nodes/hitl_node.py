"""HITL node — creates a HITL session and notifies admin WebSocket."""
from __future__ import annotations

import structlog

from chat_service.agent.state import AgentState

log = structlog.get_logger()

# Module-level placeholder — wired at app startup
db_pool = None


async def hitl_node(state: AgentState) -> AgentState:
    """Create a HITL session and notify admin via WebSocket.

    Called when the router or guardrails determines human intervention is needed.
    """
    thread_id = state.get("thread_id", "")
    tenant_id = state.get("tenant_id", "")
    reason = "explicit_request" if state.get("user_intent") == "hitl" else "guardrails_triggered"

    if not db_pool or not tenant_id:
        log.warning("hitl_node_skipped", reason="missing db_pool or tenant_id")
        return {
            **state,
            "llm_response": "正在为您转接人工客服，请稍候…",
        }

    try:
        from admin_service.routes.hitl import notify_hitl_request

        log.info("hitl_node_calling_notify", db_pool_type=type(pool).__name__, tenant_id=tenant_id, thread_id=thread_id)
        session_id = await notify_hitl_request(
            db_pool=db_pool,
            tenant_id=tenant_id,
            thread_id=thread_id,
            reason=reason,
        )
        log.info("hitl_session_created", session_id=session_id, thread_id=thread_id)
        return {
            **state,
            "llm_response": "正在为您转接人工客服，请稍候…",
        }
    except Exception as e:
        import traceback
        log.error("hitl_node_failed", error=str(e), traceback=traceback.format_exc())
        return {
            **state,
            "llm_response": "正在为您转接人工客服，请稍候…",
        }
