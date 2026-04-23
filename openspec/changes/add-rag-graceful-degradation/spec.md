# Add RAG Graceful Degradation Specification

## Overview

RAG engine should return empty results on failure with warning log, not return early without any data. Add proper fallback behavior and resilience.

## Background

Current issue: RAG returns early on failure with no fallback logic. This causes responses without retrieved context even when the system is partially degraded.

## Technical Approach

### Current Problem
```python
# Problematic: returns None, causing downstream issues
def search(self, query):
    try:
        results = self.milvus.search(query)
        return results
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return None  # Returns None!
```

### Recommended Pattern
```python
# Better: return empty list with proper handling
async def search(self, query):
    try:
        results = await self.circuit_breaker.call(
            self._do_search, query
        )
        return results
    except CircuitOpenError:
        logger.warning("RAG circuit open, returning empty results")
        return []
    except Exception as e:
        logger.warning(f"RAG search failed, using fallback: {e}")
        return []
```

### Fallback Behavior Matrix

| Failure Type | Fallback Behavior |
|--------------|-------------------|
| Milvus connection | Return empty list, log warning |
| Embedding timeout | Skip RAG, chat-only mode |
| Reranker timeout | Use original RRF order |
| Network timeout | Retry with exponential backoff |
| Circuit breaker open | Return empty list |

## Files to Update

1. `chat_service/agent/nodes/rag_engine.py` - Add fallback logic
2. `chat_service/agent/nodes/llm_generate.py` - Handle empty context
3. `chat_service/agent/nodes/context_optimizer.py` - Handle empty context

## Acceptance Criteria

- [ ] RAG never returns None on failure
- [ ] Circuit breaker protection added
- [ ] Empty results logged as warning, not silent
- [ ] Retry with exponential backoff for transient failures
- [ ] Graceful degradation to chat-only mode