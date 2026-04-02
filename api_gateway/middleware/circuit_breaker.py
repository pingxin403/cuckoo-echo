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

from circuitbreaker import CircuitBreakerError, circuit

import structlog

log = structlog.get_logger()

# Degraded response payload returned when the circuit is open
DEGRADED_RESPONSE = {
    "error": "service_unavailable",
    "message": "系统繁忙，请稍后重试",
}


@circuit(failure_threshold=50, recovery_timeout=30)
async def call_llm(payload: dict) -> dict:
    """Call the LLM backend, protected by a circuit breaker.

    The actual LLM invocation should be injected or replaced in production.
    This stub raises ``NotImplementedError`` — downstream integration
    (ai_gateway) will provide the real implementation.
    """
    raise NotImplementedError("LLM backend not wired yet")


@circuit(failure_threshold=50, recovery_timeout=30)
async def call_tool_service(tool_name: str, args: dict, tenant_id: str) -> dict:
    """Call an external tool/service, protected by a circuit breaker.

    The actual tool invocation should be injected or replaced in production.
    """
    raise NotImplementedError("Tool service backend not wired yet")


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
