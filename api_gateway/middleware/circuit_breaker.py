"""Circuit breaker wrappers for downstream service calls.

Uses the ``circuitbreaker`` library to protect ``call_llm`` and
``call_tool_service`` with ``failure_threshold=50`` and
``recovery_timeout=30``.  When the circuit is open, callers receive a
``CircuitBreakerError`` which the gateway translates into a 503 degraded
response.

This module exposes decorated async functions rather than HTTP middleware —
circuit breaking is applied at the function call level, not per-request.
"""

from __future__ import annotations

import structlog
from circuitbreaker import CircuitBreakerError, circuit

from ai_gateway import client as ai_client
from chat_service.agent.tool_executor import ToolExecutor

log = structlog.get_logger()
tool_executor = ToolExecutor()

# Degraded response payload returned when the circuit is open
DEGRADED_RESPONSE = {
    "error": "service_unavailable",
    "message": "系统繁忙，请稍后重试",
}


@circuit(failure_threshold=50, recovery_timeout=30)
async def call_llm(payload: dict) -> dict:
    """Call the LLM backend, protected by a circuit breaker."""
    try:
        response = await ai_client.stream_chat_completion(
            messages=payload.get("messages", []),
            tenant_llm_config=payload.get("tenant_llm_config"),
            thread_id=payload.get("thread_id"),
        )
        collected = []
        async for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices:
                delta = getattr(chunk.choices[0], "delta", None)
                if delta and hasattr(delta, "content"):
                    collected.append(delta.content)
        return {"content": "".join(collected), "raw": payload}
    except Exception as e:
        log.error("llm_call_failed", error=str(e))
        raise


@circuit(failure_threshold=50, recovery_timeout=30)
async def call_tool_service(tool_name: str, args: dict, tenant_id: str) -> dict:
    """Call an external tool/service, protected by a circuit breaker."""
    try:
        exec_record = await tool_executor.execute_tool(
            tool_name=tool_name,
            parameters=args,
        )
        if exec_record.error:
            raise RuntimeError(exec_record.error)
        return {"result": exec_record.result, "duration_ms": exec_record.duration_ms}
    except Exception as e:
        log.error("tool_call_failed", tool=tool_name, error=str(e))
        raise


async def safe_call_llm(payload: dict) -> dict:
    """Wrapper that catches ``CircuitBreakerError`` and returns a degraded response."""
    try:
        return await call_llm(payload)
    except CircuitBreakerError:
        log.warning("circuit_breaker_open", service="llm")
        return DEGRADED_RESPONSE


async def safe_call_tool_service(tool_name: str, args: dict, tenant_id: str) -> dict:
    """Wrapper that catches ``CircuitBreakerError`` and returns a degraded response."""
    try:
        return await call_tool_service(tool_name, args, tenant_id)
    except CircuitBreakerError:
        log.warning("circuit_breaker_open", service="tool", tool_name=tool_name)
        return DEGRADED_RESPONSE
