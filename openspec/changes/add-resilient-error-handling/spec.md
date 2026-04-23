# Resilient Error Handling Specification

## Overview

Add resilient error handling with graceful degradation, circuit breakers, and retry logic for external service dependencies (Milvus, AI Gateway, Redis, embedding service).

## Background

Current issues identified:

- RAG returns early on failure with no fallback logic
- No circuit breaker for failing external services
- Module-level globals with no graceful degradation
- No retry logic for transient failures

## Technical Approach

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0
        self.timeout = timeout
    
    async def call(self, func):
        if self.circuit_state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.circuit_state = "HALF_OPEN"
            else:
                raise CircuitOpenError()
        
        try:
            result = await func()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
```

### Error Handling Strategy

| Service | Failure Mode | Fallback Behavior |
|---------|-------------|-------------------|
| Milvus | Search fails | Return empty, log warning |
| AI Gateway | LLM fails | Return apology message |
| Redis | Cache fails | Skip cache, continue |
| Embedding | Embed fails | Skip RAG, chat-only |
| Reranker | Timeout | Skip rerank, use RRF order |

## Files to Update

1. `chat_service/agent/nodes/rag_engine.py` - Add circuit breaker, fallback
2. `chat_service/agent/nodes/llm_generate.py` - Add circuit breaker
3. `shared/redis_client.py` - Add circuit breaker
4. `shared/embedding_service.py` - Add circuit breaker

## Acceptance Criteria

- [ ] Add CircuitBreaker class
- [ ] Add fallback behavior for each external service
- [ ] Add retry with exponential backoff
- [ ] Add error metrics logging
- [ ] Add health endpoint showing service status