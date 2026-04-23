"""Tool Executor node — safe tool calling with timeout and record keeping."""
from __future__ import annotations

import asyncio
import re

import structlog

# Ensure tools are registered by importing the module
import chat_service.agent.tools.order_tools  # noqa: F401
from chat_service.agent.state import AgentState
from chat_service.agent.tools.registry import get_tool

log = structlog.get_logger()

TOOL_TIMEOUT = 5.0


def _parse_tool_intent(user_intent: str, last_message: str) -> tuple[str, dict]:
    """Extract tool name and args from user_intent and message text."""
    tool_name = user_intent[5:] if user_intent.startswith("tool:") else user_intent
    args: dict = {}

    if tool_name == "get_order_status":
        match = re.search(r"(\d{4,})", last_message)
        if match:
            args["order_id"] = match.group(1)
        else:
            args["order_id"] = "unknown"
    elif tool_name == "update_shipping_address":
        match = re.search(r"(?:地址|address)[：:\s]*(.+)", last_message, re.IGNORECASE)
        if match:
            args["address"] = match.group(1).strip()
            args["order_id"] = "latest"
        else:
            args["address"] = last_message
            args["order_id"] = "latest"

    return tool_name, args


async def safe_tool_call(tool_name: str, args: dict, tenant_id: str) -> dict:
    """Call a tool with timeout protection. Uses dynamic registry."""
    tool_fn = get_tool(tool_name)
    if not tool_fn:
        return {"error": "UNKNOWN_TOOL", "message": f"Unknown tool: {tool_name}"}

    try:
        return await asyncio.wait_for(
            tool_fn(tenant_id=tenant_id, **args),
            timeout=TOOL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        log.warning("tool_timeout", tool=tool_name, tenant_id=tenant_id)
        return {"error": "TOOL_TIMEOUT", "message": "查询超时，请稍后重试"}
    except Exception as e:
        log.error("tool_error", tool=tool_name, error=str(e))
        return {"error": "TOOL_ERROR", "message": "工具调用失败"}


async def tool_executor_node(state: AgentState) -> AgentState:
    """Execute tool call based on user_intent, record result in state."""
    user_intent = state.get("user_intent", "")
    tenant_id = state.get("tenant_id", "")
    messages = state.get("messages", [])
    last_message = messages[-1].get("content", "") if messages else ""

    tool_name, args = _parse_tool_intent(user_intent, last_message)
    result = await safe_tool_call(tool_name, args, tenant_id)

    # Append tool call record to state
    tool_calls = list(state.get("tool_calls", []))
    tool_calls.append({"name": tool_name, "args": args, "result": result})

    return {**state, "tool_calls": tool_calls, "llm_response": str(result)}
