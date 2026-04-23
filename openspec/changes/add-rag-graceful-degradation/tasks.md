# Tasks

## Phase 1: RAG Engine Resilience
- [ ] 1.1 Add circuit breaker to RAG search
- [ ] 1.2 Replace all return None with return []
- [ ] 1.3 Add warning logs for empty results
- [ ] 1.4 Add retry with exponential backoff

## Phase 2: LLM Context Handling
- [ ] 2.1 Handle empty context in prompt building
- [ ] 2.2 Add chat-only mode indicator
- [ ] 2.3 Update response to indicate context unavailable

## Phase 3: Integration
- [ ] 3.1 Verify end-to-end graceful degradation
- [ ] 3.2 Add integration test simulating RAG failure
- [ ] 3.3 Verify system returns helpful response