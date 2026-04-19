# Requirements: Agent Memory Optimization

## Functional

1. **Auto-summarization**
   - Trigger after N messages (configurable)
   - Preserve key facts
   - Replace old messages with summary

2. **Token Budget**
   - Max context tokens: configurable
   - Budget exceeded triggers compression

3. **Memory Policies**
   - FIFO (keep N recent)
   - Importance-based retention
   - Hybrid (summarize + keep recent)

## Non-Functional

- Latency impact: < 100ms
- Accuracy: preserve key info

## Out of Scope

- Semantic memory (future)
- User preferences (future)