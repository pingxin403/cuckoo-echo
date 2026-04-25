# Fix Bare Exception Handling

## Problem / 问题

The codebase contains bare `except:` and `except Exception:` clauses without proper logging or re-raising. This:
- Silently swallows exceptions
- Makes debugging difficult
- Violates security best practices
- May hide critical errors

## Background / 背景

Found in these locations:
- `chat_service/agent/nodes/llm_generate.py:102` - catches and re-raises but minimal handling
- `shared/prompt_template.py:67,103` - catches silently
- `scripts/manage_services.py:53` - catches and logs but continues silently

## Requirements / 需求

1. **Log All Caught Exceptions**
   - Use structlog to log exception details
   - Include context (tenant_id, user_id, operation)

2. **Specific Exception Types**
   - Replace bare `except:` with specific exceptions
   - Group related exceptions where appropriate

3. **Error Recovery Actions**
   - Define recovery action for each exception type
   - Return sensible defaults or raise appropriate errors

4. **Alerting for Critical Exceptions**
   - Mark exceptions that should trigger alerts
   - Include alerting metadata

## Implementation / 实现方案

Before:
```python
try:
    result = await call_llm(payload)
except Exception:
    pass  # Silently ignored!
```

After:
```python
try:
    result = await call_llm(payload)
except (TimeoutError, ConnectionError) as e:
    log.warning("llm_call_retryable_error", error=str(e), tenant_id=tenant_id)
    raise LLMCallError("LLM service temporarily unavailable") from e
except RateLimitError as e:
    log.warning("llm_rate_limited", error=str(e), tenant_id=tenant_id)
    raise
except Exception as e:
    log.error("llm_call_failed", error=str(e), exc_info=True, tenant_id=tenant_id)
    raise LLMCallError("LLM service failed") from e
```

## Acceptance Criteria / 验收标准

- [ ] No bare `except:` in production code
- [ ] All caught exceptions logged with context
- [ ] Specific exception types caught where possible
- [ ] Critical exceptions trigger alerts
- [ ] Unit tests verify exception handling