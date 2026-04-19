# Requirements: Agent Tooling

## Functional

1. **State Inspection**
   - GET /debug/agent/state/{thread_id}
   - Returns full agent state
   - Includes context, memory, tools

2. **History**
   - GET /debug/agent/history/{thread_id}
   - Returns node execution history
   - Includes timing, inputs/outputs

3. **Node Control**
   - POST /debug/node/{node_id}/execute
   - POST /debug/node/{node_id}/skip

## Non-Functional

- Debug endpoints: admin-only
- Performance: < 100ms overhead
- Retention: 7 days

## Out of Scope

- Real-time debugging (future)
- Breakpoints (future)