# Smart Context Compression Specification

## Overview

Implement intelligent context compression strategies that preserve critical information while reducing token usage.

## Background

Context window is expensive (tokens = money). Current approaches:
- Simple truncation loses important context
- Fixed-size windows are inefficient
- Best practice: Selective retention + importance scoring

## Goals

1. Reduce token usage without quality loss
2. Preserve critical context (tool results, user preferences)
3. Importance-based message selection
4. Relevance-weighted context retrieval

## Technical Approach

### Compression Strategies

```python
class ContextCompressor:
    def compress(self, messages: list[Message], budget: int) -> list[Message]:
    def score_importance(self, msg: Message) -> float:
    def prune_irrelevant(self, messages: list[Message]) -> list[Message]:
```

### Strategies

1. **Importance Scoring**
   - Tool results: High priority
   - User preferences: High priority
   - System messages: Medium priority
   - Simple turns: Low priority

2. **Relevance-Based Pruning**
   - Semantic similarity to current query
   - Recency weighting
   - Topic relevance

3. **Selective Retention**
   - Always keep last N messages
   - Keep tool calls and results
   - Keep preference signals

## Files

1. `shared/context_compressor.py` - ContextCompressor
2. `chat_service/agent/context_manager.py` - Budget management

## Acceptance Criteria

- [ ] Importance scoring for messages
- [ ] Token budget management
- [ ] Preserve tool results
- [ ] Relevance-based pruning