# Fix Circuit Breaker Integration

## Problem / 问题

The API Gateway circuit breaker middleware contains stub implementations that raise `NotImplementedError`:
- `call_llm()` - LLM backend not wired
- `call_tool_service()` - Tool service backend not wired

This is a placeholder that needs to be wired to actual service calls.

## Background / 背景

Circuit breakers in `api_gateway/middleware/circuit_breaker.py`:
- Currently raise `NotImplementedError`
- Should wrap actual LLM and tool service calls
- The real implementations exist in `ai_gateway/client.py`

## Requirements / 需求

1. **Wire LLM Calls**
   - Import and call actual LLM client from ai_gateway
   - Pass through payload and handle response
   - Add proper error handling for LLM-specific errors

2. **Wire Tool Service Calls**
   - Route to actual tool executor
   - Pass tenant_id for proper isolation
   - Add timeout handling

3. **Error Translation**
   - Convert LLM errors to appropriate HTTP status codes
   - Add retry logic before circuit opens
   - Include error details in response (without leaking sensitive info)

4. **Testing**
   - Test circuit opens after threshold failures
   - Test circuit closes after recovery timeout
   - Test degraded response format

## Implementation / 实现方案

```python
# api_gateway/middleware/circuit_breaker.py

from ai_gateway.client import aclient as llm_client
from chat_service.agent.tool_executor import ToolExecutor

tool_executor = ToolExecutor()

@circuit(failure_threshold=50, recovery_timeout=30)
async def call_llm(payload: dict) -> dict:
    try:
        response = await llm_client.chat.completions.create(**payload)
        return response.model_dump()
    except Exception as e:
        log.error("llm_call_failed", error=str(e))
        raise

@circuit(failure_threshold=50, recovery_timeout=30)
async def call_tool_service(tool_name: str, args: dict, tenant_id: str) -> dict:
    try:
        result = await tool_executor.execute(
            tool_name=tool_name,
            args=args,
            tenant_id=tenant_id,
        )
        return result
    except Exception as e:
        log.error("tool_call_failed", tool=tool_name, error=str(e))
        raise
```

## Acceptance Criteria / 验收标准

- [ ] call_llm() makes actual LLM API calls
- [ ] call_tool_service() executes actual tools
- [ ] Circuit opens after 50 failures
- [ ] Circuit recovers after 30 seconds
- [ ] Degraded response returned when circuit open
- [ ] Unit tests pass
- [ ] Integration tests pass