# Tasks

## Implementation Checklist

### Phase 1: Core Infrastructure
- [x] 1.1 Create shared/circuit_breaker.py - CircuitBreaker class
- [x] 1.2 Create shared/retry.py - Retry decorator with exponential backoff
- [x] 1.3 Create shared/resilience.py - Combined resilience utilities

### Phase 2: RAG Engine Resilience
- [x] 2.1 Add circuit breaker around Milvus search
- [x] 2.2 Add fallback to empty RAG on failure
- [x] 2.3 Add retry for embedding service calls
- [x] 2.4 Add error metrics logging

### Phase 3: LLM Generate Resilience
- [x] 3.1 Add circuit breaker around AI Gateway calls
- [x] 3.2 Add fallback apology message on LLM failure
- [x] 3.3 Add request timeout handling

### Phase 4: Redis Resilience
- [x] 4.1 Add circuit breaker around Redis operations
- [x] 4.2 Add fallback (skip cache) on Redis failure
- [x] 4.3 Add connection pool health check

### Phase 5: Health Endpoint
- [x] 5.1 Add /health/detailed endpoint showing service status
- [x] 5.2 Add circuit breaker states to health response
- [x] 5.3 Add error rate metrics

### Phase 6: Tests
- [x] 6.1 Add unit tests for CircuitBreaker
- [x] 6.2 Add unit tests for retry logic
- [x] 6.3 Add integration tests for fallback behavior

## Implementation Files

### New Files (shared/)
- circuit_breaker.py - CircuitBreaker class
- retry.py - Retry decorator
- resilience.py - Combined utilities

### Updated Files
- chat_service/agent/nodes/rag_engine.py
- chat_service/agent/nodes/llm_generate.py
- shared/redis_client.py
- shared/embedding_service.py
- chat_service/main.py - Add /health/detailed endpoint